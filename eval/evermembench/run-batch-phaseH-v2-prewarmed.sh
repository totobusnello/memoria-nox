#!/bin/bash
# Phase H v2 — pre-warmed batch (5-batch parallel variant).
#
# Differs from run-batch-phaseH-v2.sh (batch 004 single-shot):
#   - Skips Add + Vectorize (DB pre-warmed from Phase B winning run, mirrors Phase G pattern)
#   - Honors RUN_DIR from env (allows parent launcher to control per-batch dir)
#   - Does NOT swap pipeline.yaml (launcher is expected to swap once before fan-out
#     and restore once after — see run-parallel-phaseH-v2.sh)
#
# Methodology preserved from batch 004 v2:
#   - Backbone: gpt-4.1-mini via OpenAI direct (rotated key in /root/.openclaw/.env)
#   - Judge: gemini-2.5-flash
#   - Adapter: phaseB
#   - top_k=20
#   - Rerank OFF (NOX_RERANKER_ENABLED=0, NOX_RERANKER_MODEL unset after env source)
#   - Preflight: real gpt-4.1-mini completion (billing path), NOT just /v1/models
#
# Usage (called by run-parallel-phaseH-v2.sh):
#   WORK=/tmp/phaseH-v2-5batch-<uuid> \
#   RUN_DIR=/root/.openclaw/evermembench-runs/phaseH-v2-<batch>-<ts> \
#   bash run-batch-phaseH-v2-prewarmed.sh <BATCH> <PORT>
#
# Prereqs (caller must satisfy):
#   - $RUN_DIR/nox-mem.db pre-populated from Phase B winning run
#   - $WORK/venv contains harness deps (or path to existing phaseB venv works)
#   - $WORK/everos/benchmarks/EverMemBench installed
#   - pipeline.yaml already swapped to phaseH v2 config by caller
set -uo pipefail

BATCH="${1:?usage: $0 <BATCH> <PORT>}"
PORT="${2:?usage: $0 <BATCH> <PORT>}"
WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
RUN_DIR="${RUN_DIR:?RUN_DIR env var must be set}"
mkdir -p "$RUN_DIR"
echo "[PHASE-H-v2-pw BATCH $BATCH PORT $PORT] RUN_DIR=$RUN_DIR"

# Source prod env to get OPENAI_API_KEY + GEMINI_API_KEY (but DO NOT clobber NOX_DB_PATH)
set -a; source /root/.openclaw/.env; set +a

# Activate venv
source /root/.openclaw/evermembench-phaseB-1779978778/venv/bin/activate
echo "[PHASE-H-v2-pw] venv python: $(which python)"

# Re-export AFTER source per [[evermembench-eval-gotchas-2026-05-28]]:
# Isolate Phase H from Phase G rerank state.
export NOX_RERANKER_ENABLED=0
unset NOX_RERANKER_MODEL || true

# cli.py presence check (line 379) — actual routing via per-stage api_key in pipeline.yaml
export LLM_API_KEY="$GEMINI_API_KEY"
export LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"

# Verify both keys are present
if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "[PHASE-H-v2-pw BATCH $BATCH] ERROR: OPENAI_API_KEY not present in /root/.openclaw/.env"
    exit 1
fi
if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "[PHASE-H-v2-pw BATCH $BATCH] ERROR: GEMINI_API_KEY not present in /root/.openclaw/.env"
    exit 1
fi
echo "[PHASE-H-v2-pw BATCH $BATCH] OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}...${OPENAI_API_KEY: -4} (len ${#OPENAI_API_KEY})"

# Live preflight: REAL completion (billing path), NOT just /v1/models list.
echo "[PHASE-H-v2-pw BATCH $BATCH] === Preflight: gpt-4.1-mini completion ==="
PREFLIGHT=$(curl -s --max-time 30 https://api.openai.com/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -d '{"model":"gpt-4.1-mini","messages":[{"role":"user","content":"Reply only OK"}],"max_tokens":5,"temperature":0}')
if ! echo "$PREFLIGHT" | grep -q '"OK"'; then
    echo "[PHASE-H-v2-pw BATCH $BATCH] ERROR: OpenAI preflight failed (auth OR billing)"
    echo "$PREFLIGHT" | head -c 600
    exit 1
fi
PREFLIGHT_TOKENS=$(echo "$PREFLIGHT" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("usage",{}).get("total_tokens","?"))')
echo "[PHASE-H-v2-pw BATCH $BATCH] preflight OK (total_tokens=$PREFLIGHT_TOKENS)"

# Isolated DB + isolated port
export NOX_DB_PATH="$RUN_DIR/nox-mem.db"
export NOX_API_PORT="$PORT"
export NOX_API_BASE="http://127.0.0.1:$PORT"
export NOX_ADAPTER_MODE="${NOX_ADAPTER_MODE:-phaseB}"
export NOX_MEM_BIN="$(which nox-mem)"

echo "[PHASE-H-v2-pw BATCH $BATCH] NOX_DB_PATH=$NOX_DB_PATH"
echo "[PHASE-H-v2-pw BATCH $BATCH] NOX_ADAPTER_MODE=$NOX_ADAPTER_MODE"
echo "[PHASE-H-v2-pw BATCH $BATCH] NOX_RERANKER_ENABLED=$NOX_RERANKER_ENABLED (MODEL set=$(env | grep -c NOX_RERANKER_MODEL))"

# Verify DB pre-warmed (Phase F lesson: refuse to run on empty DB)
if [ ! -f "$NOX_DB_PATH" ]; then
    echo "[PHASE-H-v2-pw BATCH $BATCH] ERROR: pre-warmed DB missing at $NOX_DB_PATH"
    exit 1
fi
EXISTING_CHUNKS=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM chunks;" 2>/dev/null || echo 0)
echo "[PHASE-H-v2-pw BATCH $BATCH] pre-loaded DB chunks=$EXISTING_CHUNKS"
if [ "$EXISTING_CHUNKS" -lt 5000 ]; then
    echo "[PHASE-H-v2-pw BATCH $BATCH] ERROR: DB not pre-warmed (chunks=$EXISTING_CHUNKS)"
    exit 1
fi

# Cleanup hook
API_PID=""
cleanup() {
    if [ -n "$API_PID" ]; then
        kill "$API_PID" 2>/dev/null || true
        wait "$API_PID" 2>/dev/null || true
        echo "[PHASE-H-v2-pw BATCH $BATCH] killed api server pid=$API_PID"
    fi
}
trap cleanup EXIT

echo "[PHASE-H-v2-pw BATCH $BATCH] === Step 1: spawn isolated api-server ==="
cd /root/.openclaw/workspace/tools/nox-mem
nohup node --no-warnings dist/api-server.js > "$RUN_DIR/api.log" 2>&1 &
API_PID=$!
echo "[PHASE-H-v2-pw BATCH $BATCH] api pid=$API_PID, waiting 5s for boot..."
sleep 5

HEALTH=$(curl -s --max-time 10 "$NOX_API_BASE/api/health" || true)
if ! echo "$HEALTH" | grep -q "\"chunks\""; then
    echo "[PHASE-H-v2-pw BATCH $BATCH] ERROR: api not responding"
    echo "$HEALTH" | head -c 300
    exit 1
fi
TOTAL=$(echo "$HEALTH" | python3 -c "import json,sys;d=json.load(sys.stdin);c=d['chunks'];print(c.get('total') if isinstance(c,dict) else c)")
echo "[PHASE-H-v2-pw BATCH $BATCH] api health: chunks=$TOTAL"

echo "[PHASE-H-v2-pw BATCH $BATCH] === Step 1b: clear stale harness results (resume short-circuit) ==="
RESULTS_DIR="$EVAL/eval/results/nox_mem"
rm -f "$RESULTS_DIR/answer_results_$BATCH.json" "$RESULTS_DIR/evaluation_results_$BATCH.json" "$RESULTS_DIR/search_results_$BATCH.json"
echo "[PHASE-H-v2-pw BATCH $BATCH] cleared stale files in $RESULTS_DIR"

echo "[PHASE-H-v2-pw BATCH $BATCH] === Step 2: Search + Answer + Evaluate ==="
cd "$EVAL"
python -m eval.cli \
    --dataset "dataset/$BATCH/dialogue.json" \
    --qa "dataset/$BATCH/qa_$BATCH.json" \
    --system nox_mem \
    --user-id "$BATCH" \
    --stages search answer evaluate \
    --top-k 20 \
    > "$RUN_DIR/eval.log" 2>&1

echo "[PHASE-H-v2-pw BATCH $BATCH] === Step 3: Analyze ==="
RESULTS_FILE="$RESULTS_DIR/evaluation_results_$BATCH.json"
if [ -f "$RESULTS_FILE" ]; then
    python tools/analyze_results.py "$RESULTS_FILE" > "$RUN_DIR/analysis.txt" 2>&1 || true
    cp "$RESULTS_FILE" "$RUN_DIR/results-batch-$BATCH.json"
    cp "$RESULTS_DIR/answer_results_$BATCH.json" "$RUN_DIR/answer-results-batch-$BATCH.json" 2>/dev/null || true
    echo "[PHASE-H-v2-pw BATCH $BATCH] results -> $RUN_DIR/results-batch-$BATCH.json"
else
    echo "[PHASE-H-v2-pw BATCH $BATCH] ERROR: no results file at $RESULTS_FILE"
    ls "$RESULTS_DIR" 2>&1 || true
fi

echo "[PHASE-H-v2-pw BATCH $BATCH] === DONE ==="
ls -la "$RUN_DIR/"
