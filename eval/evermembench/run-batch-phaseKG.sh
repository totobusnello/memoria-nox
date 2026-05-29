#!/bin/bash
# Phase KG — pre-warmed batch (5-batch parallel variant).
# Lab Q1 #4 — KG path retrieval Approach A (1-hop boost, regex entity extract).
#
# Differs from run-batch-phaseH-v2-prewarmed.sh:
#   - NOX_ADAPTER_MODE=phaseKG (KG boost enabled by default)
#   - NOX_KG_PATH_ENABLED=1 (explicit override after .env source)
#   - NOX_RERANKER_ENABLED=0 (no rerank stacking — KG isolated study)
#   - Pre-condition: DB MUST have kg_entities + kg_relations populated.
#     Caller must run `nox-mem kg-extract --limit N` before launching.
#
# Methodology preserved from Phase H v2:
#   - Backbone: gpt-4.1-mini via OpenAI direct
#   - Judge: gemini-2.5-flash
#   - top_k=20
#   - Pipeline.yaml swap done ONCE by parent launcher
#
# Usage (called by run-parallel-phaseKG.sh):
#   WORK=/tmp/phaseKG-5batch-<uuid> \
#   RUN_DIR=/root/.openclaw/evermembench-runs/phaseKG-<batch>-<ts> \
#   bash run-batch-phaseKG.sh <BATCH> <PORT>
#
# Prereqs (caller must satisfy):
#   - $RUN_DIR/nox-mem.db pre-populated (cloned from phaseH-v2 winning DB)
#     AND has kg_entities/kg_relations populated via kg-extract.
#   - $WORK/venv contains harness deps
#   - $WORK/everos/benchmarks/EverMemBench installed
#   - pipeline.yaml already swapped to phaseH v2 config by caller
set -uo pipefail

BATCH="${1:?usage: $0 <BATCH> <PORT>}"
PORT="${2:?usage: $0 <BATCH> <PORT>}"
WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
RUN_DIR="${RUN_DIR:?RUN_DIR env var must be set}"
mkdir -p "$RUN_DIR"
echo "[PHASE-KG BATCH $BATCH PORT $PORT] RUN_DIR=$RUN_DIR"

# Source prod env to get OPENAI_API_KEY + GEMINI_API_KEY (but DO NOT clobber NOX_DB_PATH)
set -a; source /root/.openclaw/.env; set +a

# Activate venv (reuse Phase B venv)
source /root/.openclaw/evermembench-phaseB-1779978778/venv/bin/activate
echo "[PHASE-KG] venv python: $(which python)"

# Re-export AFTER source per [[evermembench-eval-gotchas-2026-05-28]]:
# Isolate Phase KG from rerank + force KG path on.
export NOX_RERANKER_ENABLED=0
unset NOX_RERANKER_MODEL || true
export NOX_KG_PATH_ENABLED=1

# cli.py routing
export LLM_API_KEY="$GEMINI_API_KEY"
export LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"

# Verify keys
if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "[PHASE-KG BATCH $BATCH] ERROR: OPENAI_API_KEY not present"
    exit 1
fi
if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "[PHASE-KG BATCH $BATCH] ERROR: GEMINI_API_KEY not present"
    exit 1
fi
echo "[PHASE-KG BATCH $BATCH] OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}...${OPENAI_API_KEY: -4} (len ${#OPENAI_API_KEY})"

# Live preflight: REAL completion (billing path)
echo "[PHASE-KG BATCH $BATCH] === Preflight: gpt-4.1-mini completion ==="
PREFLIGHT=$(curl -s --max-time 30 https://api.openai.com/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -d '{"model":"gpt-4.1-mini","messages":[{"role":"user","content":"Reply only OK"}],"max_tokens":5,"temperature":0}')
if ! echo "$PREFLIGHT" | grep -q '"OK"'; then
    echo "[PHASE-KG BATCH $BATCH] ERROR: OpenAI preflight failed (auth OR billing)"
    echo "$PREFLIGHT" | head -c 600
    exit 1
fi
PREFLIGHT_TOKENS=$(echo "$PREFLIGHT" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("usage",{}).get("total_tokens","?"))')
echo "[PHASE-KG BATCH $BATCH] preflight OK (total_tokens=$PREFLIGHT_TOKENS)"

# Isolated DB + isolated port
export NOX_DB_PATH="$RUN_DIR/nox-mem.db"
export NOX_API_PORT="$PORT"
export NOX_API_BASE="http://127.0.0.1:$PORT"
export NOX_ADAPTER_MODE="phaseKG"
export NOX_MEM_BIN="$(which nox-mem)"

echo "[PHASE-KG BATCH $BATCH] NOX_DB_PATH=$NOX_DB_PATH"
echo "[PHASE-KG BATCH $BATCH] NOX_ADAPTER_MODE=$NOX_ADAPTER_MODE"
echo "[PHASE-KG BATCH $BATCH] NOX_KG_PATH_ENABLED=$NOX_KG_PATH_ENABLED"
echo "[PHASE-KG BATCH $BATCH] NOX_RERANKER_ENABLED=$NOX_RERANKER_ENABLED"

# Verify DB pre-warmed AND has KG populated
if [ ! -f "$NOX_DB_PATH" ]; then
    echo "[PHASE-KG BATCH $BATCH] ERROR: pre-warmed DB missing at $NOX_DB_PATH"
    exit 1
fi
EXISTING_CHUNKS=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM chunks;" 2>/dev/null || echo 0)
KG_ENTITIES=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM kg_entities;" 2>/dev/null || echo 0)
KG_RELATIONS=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM kg_relations;" 2>/dev/null || echo 0)
echo "[PHASE-KG BATCH $BATCH] pre-loaded DB chunks=$EXISTING_CHUNKS kg_entities=$KG_ENTITIES kg_relations=$KG_RELATIONS"
if [ "$EXISTING_CHUNKS" -lt 5000 ]; then
    echo "[PHASE-KG BATCH $BATCH] ERROR: DB not pre-warmed (chunks=$EXISTING_CHUNKS)"
    exit 1
fi
if [ "$KG_ENTITIES" -lt 50 ] || [ "$KG_RELATIONS" -lt 50 ]; then
    echo "[PHASE-KG BATCH $BATCH] WARNING: KG very sparse (entities=$KG_ENTITIES relations=$KG_RELATIONS) — boost coverage will be low"
fi

# Cleanup hook
API_PID=""
cleanup() {
    if [ -n "$API_PID" ]; then
        kill "$API_PID" 2>/dev/null || true
        wait "$API_PID" 2>/dev/null || true
        echo "[PHASE-KG BATCH $BATCH] killed api server pid=$API_PID"
    fi
}
trap cleanup EXIT

echo "[PHASE-KG BATCH $BATCH] === Step 1: spawn isolated api-server ==="
cd /root/.openclaw/workspace/tools/nox-mem
nohup node --no-warnings dist/api-server.js > "$RUN_DIR/api.log" 2>&1 &
API_PID=$!
echo "[PHASE-KG BATCH $BATCH] api pid=$API_PID, waiting 5s for boot..."
sleep 5

HEALTH=$(curl -s --max-time 10 "$NOX_API_BASE/api/health" || true)
if ! echo "$HEALTH" | grep -q "\"chunks\""; then
    echo "[PHASE-KG BATCH $BATCH] ERROR: api not responding"
    echo "$HEALTH" | head -c 300
    exit 1
fi
TOTAL=$(echo "$HEALTH" | python3 -c "import json,sys;d=json.load(sys.stdin);c=d['chunks'];print(c.get('total') if isinstance(c,dict) else c)")
echo "[PHASE-KG BATCH $BATCH] api health: chunks=$TOTAL"

echo "[PHASE-KG BATCH $BATCH] === Step 1b: clear stale harness results ==="
RESULTS_DIR="$EVAL/eval/results/nox_mem"
rm -f "$RESULTS_DIR/answer_results_$BATCH.json" "$RESULTS_DIR/evaluation_results_$BATCH.json" "$RESULTS_DIR/search_results_$BATCH.json"
echo "[PHASE-KG BATCH $BATCH] cleared stale files in $RESULTS_DIR"

echo "[PHASE-KG BATCH $BATCH] === Step 2: Search + Answer + Evaluate ==="
cd "$EVAL"
python -m eval.cli \
    --dataset "dataset/$BATCH/dialogue.json" \
    --qa "dataset/$BATCH/qa_$BATCH.json" \
    --system nox_mem \
    --user-id "$BATCH" \
    --stages search answer evaluate \
    --top-k 20 \
    > "$RUN_DIR/eval.log" 2>&1

echo "[PHASE-KG BATCH $BATCH] === Step 3: Analyze ==="
RESULTS_FILE="$RESULTS_DIR/evaluation_results_$BATCH.json"
if [ -f "$RESULTS_FILE" ]; then
    python tools/analyze_results.py "$RESULTS_FILE" > "$RUN_DIR/analysis.txt" 2>&1 || true
    cp "$RESULTS_FILE" "$RUN_DIR/results-batch-$BATCH.json"
    cp "$RESULTS_DIR/answer_results_$BATCH.json" "$RUN_DIR/answer-results-batch-$BATCH.json" 2>/dev/null || true
    # Also archive search_results so we can audit KG metadata per question
    cp "$RESULTS_DIR/search_results_$BATCH.json" "$RUN_DIR/search-results-batch-$BATCH.json" 2>/dev/null || true
    echo "[PHASE-KG BATCH $BATCH] results -> $RUN_DIR/results-batch-$BATCH.json"
else
    echo "[PHASE-KG BATCH $BATCH] ERROR: no results file at $RESULTS_FILE"
    ls "$RESULTS_DIR" 2>&1 || true
fi

echo "[PHASE-KG BATCH $BATCH] === DONE ==="
ls -la "$RUN_DIR/"
