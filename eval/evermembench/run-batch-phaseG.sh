#!/bin/bash
# Phase G — re-use Phase D ingest DB + add MiniLM cross-encoder rerank.
# Skips Add + Vectorize (DB pre-warmed from Phase D winning run).
#
# Replaces Phase F bge-reranker-v2-m3 (568M, CPU-killing on VPS) with
# cross-encoder/ms-marco-MiniLM-L-6-v2 (~22M, ~30x faster predict).
#
# Usage:
#   WORK=/tmp/evermembench-phaseG-<id> \
#   RUN_DIR=/root/.openclaw/evermembench-runs/phaseG-<batch>-<ts> \
#   bash run-batch-phaseG.sh <BATCH> <PORT>
#
# Prereqs (caller must satisfy):
#   - $RUN_DIR/nox-mem.db exists (copy of phaseD/phaseB winning DB, 10k+ chunks)
#   - $WORK/venv contains sentence-transformers + torch + harness deps
#   - $WORK/everos/benchmarks/EverMemBench/ harness installed + nox-mem adapter wired
#   - /root/.openclaw/.env exports GEMINI_API_KEY
#   - /tmp/preflight_phaseG.py present (rerank fire verification)
set -uo pipefail

BATCH="${1:?usage: $0 <BATCH> <PORT>}"
PORT="${2:?usage: $0 <BATCH> <PORT>}"
WORK="${WORK:?WORK env var must be set}"
source "$WORK/venv/bin/activate"
EVAL="$WORK/everos/benchmarks/EverMemBench"
RUN_DIR="${RUN_DIR:?RUN_DIR env var must be set}"
echo "[PHASEG BATCH $BATCH PORT $PORT] RUN_DIR=$RUN_DIR"

# Source prod env to get GEMINI_API_KEY
set -a; source /root/.openclaw/.env; set +a

# ==== PHASE G OVERRIDES — MUST come AFTER .env source ====
# (.env carries NOX_RERANKER_MODEL=Xenova/bge-reranker-base which would silently
#  override sentence-transformers default; we force MiniLM here AFTER source.)
export LLM_API_KEY="$GEMINI_API_KEY"
export LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"

# Isolated DB (pre-loaded from Phase D)
export NOX_DB_PATH="$RUN_DIR/nox-mem.db"
export NOX_API_PORT="$PORT"
export NOX_API_BASE="http://127.0.0.1:$PORT"

# Phase G: phaseF adapter mode + MiniLM (CPU-friendly cross-encoder)
export NOX_ADAPTER_MODE="phaseF"
export NOX_RERANKER_ENABLED=1
export NOX_RERANKER_MODEL="cross-encoder/ms-marco-MiniLM-L-6-v2"
export NOX_RERANKER_OVERFETCH=50
export NOX_RERANKER_BATCH_SIZE=32
export NOX_MEM_BIN="$(which nox-mem)"

# Verify DB pre-warmed (refuses to run on empty DB — Phase F hard lesson)
EXISTING_CHUNKS=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM chunks;" 2>/dev/null || echo 0)
echo "[PHASEG] pre-loaded DB chunks=$EXISTING_CHUNKS"
if [ "$EXISTING_CHUNKS" -lt 10000 ]; then
    echo "[PHASEG] ERROR: DB not pre-warmed (chunks=$EXISTING_CHUNKS)"
    exit 1
fi

# Cleanup hook
API_PID=""
cleanup() {
    if [ -n "$API_PID" ]; then
        kill "$API_PID" 2>/dev/null || true
        wait "$API_PID" 2>/dev/null || true
        echo "[PHASEG] killed api server pid=$API_PID"
    fi
}
trap cleanup EXIT

echo "[PHASEG] === Step 1: spawn isolated nox-mem api-server ==="
cd /root/.openclaw/workspace/tools/nox-mem
nohup node --no-warnings dist/api-server.js > "$RUN_DIR/api.log" 2>&1 &
API_PID=$!
echo "[PHASEG] api pid=$API_PID, waiting 5s for boot..."
sleep 5

HEALTH=$(curl -s --max-time 10 "$NOX_API_BASE/api/health" || true)
if ! echo "$HEALTH" | grep -q "\"chunks\""; then
    echo "[PHASEG] ERROR: api not responding"
    echo "$HEALTH" | head -c 300
    exit 1
fi
TOTAL=$(echo "$HEALTH" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['chunks']['total'])")
COV=$(echo "$HEALTH" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['vectorCoverage'])")
echo "[PHASEG] api health: chunks=$TOTAL coverage=$COV"

echo "[PHASEG] === Step 2: PRE-FLIGHT — verify rerank actually fires ==="
# Phase F lesson: env var presence != rerank firing. Run 3 real queries
# through the adapter and confirm metadata.rerank_applied=True before
# paying for the full eval batch.
cd "$EVAL" && python /tmp/preflight_phaseG.py
PREFLIGHT_RC=$?
if [ $PREFLIGHT_RC -ne 0 ]; then
    echo "[PHASEG] ERROR: pre-flight failed"
    exit 1
fi

echo "[PHASEG] === Step 3: Search + Answer + Evaluate ==="
python -m eval.cli \
    --dataset "dataset/$BATCH/dialogue.json" \
    --qa "dataset/$BATCH/qa_$BATCH.json" \
    --system nox_mem \
    --user-id "$BATCH" \
    --stages search answer evaluate \
    --top-k 20 \
    > "$RUN_DIR/eval.log" 2>&1

echo "[PHASEG] === Step 4: Analyze ==="
RESULTS_FILE="eval/results/nox_mem/evaluation_results_$BATCH.json"
if [ -f "$RESULTS_FILE" ]; then
    python tools/analyze_results.py "$RESULTS_FILE" > "$RUN_DIR/analysis.txt" 2>&1 || true
    cp "$RESULTS_FILE" "$RUN_DIR/results-batch-$BATCH.json"
    echo "[PHASEG] results -> $RUN_DIR/results-batch-$BATCH.json"
else
    echo "[PHASEG] ERROR: no results file at $RESULTS_FILE"
fi
echo "[PHASEG] === DONE ==="
ls -la "$RUN_DIR/"
