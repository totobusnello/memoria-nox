#!/bin/bash
# Wave 2 Phase 2 Capstone — IterB + Wave C triple (KG+MQ+MAP) composability
# Per-batch runner. Same shape as run-batch-phaseIterB.sh but with:
#   - NOX_ADAPTER_MODE=phaseTriple (KG + MQ + MAP composition)
#   - NOX_ITERB_ENABLED=1 (force ReAct on top)
#   - Gemini-3-flash-preview as final-answer backbone
#   - gemini-2.5-flash-lite as IterB orchestrator (per spec)
#   - Adapter PATCHED to remove iterb_used_path guards at KG boost + rerank
set -uo pipefail

BATCH="${1:?usage: $0 <BATCH> <PORT>}"
PORT="${2:?usage: $0 <BATCH> <PORT>}"
WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
RUN_DIR="${RUN_DIR:?RUN_DIR env var must be set}"
mkdir -p "$RUN_DIR"
echo "[CAPSTONE BATCH $BATCH PORT $PORT] RUN_DIR=$RUN_DIR"

set -a; source /root/.openclaw/.env; set +a
source /root/.openclaw/evermembench-phaseB-1779978778/venv/bin/activate
echo "[CAPSTONE] venv python: $(which python)"

# === Composability env flags (patched adapter) ===
export NOX_RERANKER_ENABLED=1
export NOX_RERANKER_MODEL="BAAI/bge-reranker-v2-m3"  # WAVE2-CAPSTONE force
export NOX_KG_PATH_ENABLED=1
export NOX_MQ_ENABLED=0   # IterB subsumes MQ's role (per-round retrieve is itself sub-query decomp)
export NOX_MA_PROTECTION_ENABLED=1
export NOX_ITERC_ENABLED=0
export NOX_ITERB_ENABLED=1

# === IterB orchestrator (per spec: gemini-2.5-flash-lite, NOT gpt-4.1-mini) ===
export NOX_ITERB_ORCHESTRATOR_LLM="gemini-2.5-flash-lite"
export NOX_ITERB_ORCHESTRATOR_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai"
export NOX_ITERB_ORCHESTRATOR_API_KEY="$GEMINI_API_KEY"
export NOX_ITERB_INPUT_COST_PER_1M="0.30"   # Gemini-flash-lite estimate
export NOX_ITERB_OUTPUT_COST_PER_1M="2.50"
export NOX_ITERB_MAX_ROUNDS=5
export NOX_ITERB_PER_ROUND_TOPK=10
export NOX_ITERB_RRF_K=60
export NOX_ITERB_ORCHESTRATOR_TIMEOUT_S=45
export NOX_ITERB_ORCHESTRATOR_MAX_TOKENS=400
export NOX_ITERB_COST_CEILING_USD=0.01

# === MAP-protection bypass-entity (KG anchor mode) ===
export NOX_MA_PROTECTION_KG_ANCHOR=1
export NOX_MA_PROTECTION_MAX=15

# === cli.py routing (Gemini for harness) ===
export LLM_API_KEY="$GEMINI_API_KEY"
export LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"

# === Keys check ===
if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "[CAPSTONE BATCH $BATCH] ERROR: GEMINI_API_KEY not present"
    exit 1
fi
echo "[CAPSTONE BATCH $BATCH] GEMINI_API_KEY: ${GEMINI_API_KEY:0:10}...${GEMINI_API_KEY: -4}"

# === Preflight 1: harness final-answer backbone (gemini-3-flash-preview) ===
echo "[CAPSTONE BATCH $BATCH] === Preflight 1: gemini-3-flash-preview (final answer) ==="
PREFLIGHT_A=$(curl -s --max-time 30 https://generativelanguage.googleapis.com/v1beta/openai/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $GEMINI_API_KEY" \
    -d '{"model":"gemini-3-flash-preview","messages":[{"role":"user","content":"Reply only OK"}],"max_tokens":10,"temperature":0}')
if ! echo "$PREFLIGHT_A" | python3 -c 'import json,sys;d=json.load(sys.stdin);sys.exit(0 if d.get("choices") else 1)' 2>/dev/null; then
    echo "[CAPSTONE BATCH $BATCH] ERROR: gemini-3-flash-preview preflight failed"
    echo "$PREFLIGHT_A" | head -c 600
    exit 1
fi
echo "[CAPSTONE BATCH $BATCH] gemini-3-flash-preview preflight OK"

# === Preflight 2: IterB orchestrator (gemini-2.5-flash-lite) ===
echo "[CAPSTONE BATCH $BATCH] === Preflight 2: gemini-2.5-flash-lite (orchestrator + MQ) ==="
PREFLIGHT_B=$(curl -s --max-time 30 https://generativelanguage.googleapis.com/v1beta/openai/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $GEMINI_API_KEY" \
    -d '{"model":"gemini-2.5-flash-lite","messages":[{"role":"user","content":"Reply only OK"}],"max_tokens":10,"temperature":0}')
if ! echo "$PREFLIGHT_B" | python3 -c 'import json,sys;d=json.load(sys.stdin);sys.exit(0 if d.get("choices") else 1)' 2>/dev/null; then
    echo "[CAPSTONE BATCH $BATCH] ERROR: gemini-2.5-flash-lite preflight failed"
    echo "$PREFLIGHT_B" | head -c 600
    exit 1
fi
echo "[CAPSTONE BATCH $BATCH] gemini-2.5-flash-lite preflight OK"

# === Preflight 3: judge (gemini-2.5-flash) ===
echo "[CAPSTONE BATCH $BATCH] === Preflight 3: gemini-2.5-flash (judge) ==="
PREFLIGHT_C=$(curl -s --max-time 30 https://generativelanguage.googleapis.com/v1beta/openai/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $GEMINI_API_KEY" \
    -d '{"model":"gemini-2.5-flash","messages":[{"role":"user","content":"Reply only OK"}],"max_tokens":10,"temperature":0}')
if ! echo "$PREFLIGHT_C" | python3 -c 'import json,sys;d=json.load(sys.stdin);sys.exit(0 if d.get("choices") else 1)' 2>/dev/null; then
    echo "[CAPSTONE BATCH $BATCH] ERROR: gemini-2.5-flash preflight failed"
    echo "$PREFLIGHT_C" | head -c 600
    exit 1
fi
echo "[CAPSTONE BATCH $BATCH] gemini-2.5-flash preflight OK"

# === Isolated DB + isolated port ===
export NOX_DB_PATH="$RUN_DIR/nox-mem.db"
export NOX_API_PORT="$PORT"
export NOX_API_BASE="http://127.0.0.1:$PORT"
export NOX_ADAPTER_MODE="phaseTriple"
export NOX_MEM_BIN="$(which nox-mem)"

echo "[CAPSTONE BATCH $BATCH] NOX_DB_PATH=$NOX_DB_PATH"
echo "[CAPSTONE BATCH $BATCH] NOX_ADAPTER_MODE=$NOX_ADAPTER_MODE + NOX_ITERB_ENABLED=$NOX_ITERB_ENABLED"
echo "[CAPSTONE BATCH $BATCH] composition: rerank=$NOX_RERANKER_ENABLED kg=$NOX_KG_PATH_ENABLED map=$NOX_MA_PROTECTION_ENABLED mq=$NOX_MQ_ENABLED"
echo "[CAPSTONE BATCH $BATCH] orchestrator=$NOX_ITERB_ORCHESTRATOR_LLM max_rounds=$NOX_ITERB_MAX_ROUNDS"

# === Verify DB pre-warmed ===
if [ ! -f "$NOX_DB_PATH" ]; then
    echo "[CAPSTONE BATCH $BATCH] ERROR: pre-warmed DB missing at $NOX_DB_PATH"
    exit 1
fi
EXISTING_CHUNKS=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM chunks;" 2>/dev/null || echo 0)
echo "[CAPSTONE BATCH $BATCH] pre-loaded DB chunks=$EXISTING_CHUNKS"
if [ "$EXISTING_CHUNKS" -lt 5000 ]; then
    echo "[CAPSTONE BATCH $BATCH] ERROR: DB not pre-warmed (chunks=$EXISTING_CHUNKS)"
    exit 1
fi

# Cleanup
API_PID=""
cleanup() {
    if [ -n "$API_PID" ]; then
        kill "$API_PID" 2>/dev/null || true
        wait "$API_PID" 2>/dev/null || true
        echo "[CAPSTONE BATCH $BATCH] killed api server pid=$API_PID"
    fi
}
trap cleanup EXIT

echo "[CAPSTONE BATCH $BATCH] === Step 1: spawn isolated api-server ==="
cd /root/.openclaw/workspace/tools/nox-mem
nohup node --no-warnings dist/api-server.js > "$RUN_DIR/api.log" 2>&1 &
API_PID=$!
echo "[CAPSTONE BATCH $BATCH] api pid=$API_PID, waiting 5s for boot..."
sleep 5

HEALTH=$(curl -s --max-time 10 "$NOX_API_BASE/api/health" || true)
if ! echo "$HEALTH" | grep -q "\"chunks\""; then
    echo "[CAPSTONE BATCH $BATCH] ERROR: api not responding"
    echo "$HEALTH" | head -c 300
    exit 1
fi
TOTAL=$(echo "$HEALTH" | python3 -c "import json,sys;d=json.load(sys.stdin);c=d['chunks'];print(c.get('total') if isinstance(c,dict) else c)")
echo "[CAPSTONE BATCH $BATCH] api health: chunks=$TOTAL"

echo "[CAPSTONE BATCH $BATCH] === Step 1b: clear stale harness results ==="
RESULTS_DIR="$EVAL/eval/results/nox_mem"
rm -f "$RESULTS_DIR/answer_results_$BATCH.json" "$RESULTS_DIR/evaluation_results_$BATCH.json" "$RESULTS_DIR/search_results_$BATCH.json"

echo "[CAPSTONE BATCH $BATCH] === Step 2: Search + Answer + Evaluate ==="
cd "$EVAL"
python -m eval.cli \
    --dataset "dataset/$BATCH/dialogue.json" \
    --qa "dataset/$BATCH/qa_$BATCH.json" \
    --system nox_mem \
    --user-id "$BATCH" \
    --stages search answer evaluate \
    --top-k 20 \
    > "$RUN_DIR/eval.log" 2>&1
EVAL_RC=$?
echo "[CAPSTONE BATCH $BATCH] eval rc=$EVAL_RC"

echo "[CAPSTONE BATCH $BATCH] === Step 3: Analyze ==="
RESULTS_FILE="$RESULTS_DIR/evaluation_results_$BATCH.json"
if [ -f "$RESULTS_FILE" ]; then
    python tools/analyze_results.py "$RESULTS_FILE" > "$RUN_DIR/analysis.txt" 2>&1 || true
    cp "$RESULTS_FILE" "$RUN_DIR/results-batch-$BATCH.json"
    cp "$RESULTS_DIR/answer_results_$BATCH.json" "$RUN_DIR/answer-results-batch-$BATCH.json" 2>/dev/null || true
    cp "$RESULTS_DIR/search_results_$BATCH.json" "$RUN_DIR/search-results-batch-$BATCH.json" 2>/dev/null || true
    echo "[CAPSTONE BATCH $BATCH] results -> $RUN_DIR/results-batch-$BATCH.json"
else
    echo "[CAPSTONE BATCH $BATCH] ERROR: no results file at $RESULTS_FILE"
    tail -50 "$RUN_DIR/eval.log" 2>/dev/null
    ls "$RESULTS_DIR" 2>&1 || true
fi

echo "[CAPSTONE BATCH $BATCH] === DONE ==="
ls -la "$RUN_DIR/"
