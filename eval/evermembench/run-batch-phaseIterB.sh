#!/bin/bash
# Phase IterB (Q3 POC) — pre-warmed batch runner (5-batch sequential variant).
# ReAct multi-round orchestration: per-query loop of (orchestrator LLM →
# retrieve OR answer → observation feedback) up to max_rounds.
#
# Differs from run-batch-phaseIterC.sh:
#   - NOX_ADAPTER_MODE=phaseIterB (ReAct enabled by default)
#   - NOX_ITERB_ENABLED=1 (explicit override after .env source)
#   - NOX_ITERC_ENABLED=0 (no Self-Ask stacking — clean isolation)
#   - NOX_MQ_ENABLED=0 (no MQ stacking)
#   - NOX_RERANKER_ENABLED=0 (no rerank stacking)
#   - NOX_KG_PATH_ENABLED=0 (no KG stacking)
#   - Single orchestrator backbone (default gpt-4.1-mini) — preflight tests
#     billing path with small chat completion (per
#     [[preflight-must-exercise-billing-path]]).
#
# Methodology preserved from Phase H v2 + Phase IterC:
#   - Backbone (final answer via harness): gpt-4.1-mini
#   - Backbone (per-round orchestrator): default gpt-4.1-mini (cheap-ish,
#     ~$0.001/round × 3-5 rounds = $0.003-0.005/q expected)
#   - Optional cheap variant: NOX_ITERB_ORCHESTRATOR_LLM=gemini-2.5-flash-lite
#     (or gemini-3-flash if billing path validated)
#   - Judge: gemini-2.5-flash
#   - top_k=20 (harness final)
#   - top_k=10 per round (NOX_ITERB_PER_ROUND_TOPK default)
#   - max_rounds=5 (NOX_ITERB_MAX_ROUNDS default)
#   - cost_ceiling=$0.01/query (NOX_ITERB_COST_CEILING_USD default)
#
# Usage (called by run-phaseIterB-5batch.sh):
#   WORK=/tmp/q3-iterB-poc-<short-uuid> \
#   RUN_DIR=/root/.openclaw/evermembench-runs/phaseIterB-<batch>-<ts> \
#   bash run-batch-phaseIterB.sh <BATCH> <PORT>
#
# Prereqs (caller must satisfy):
#   - $RUN_DIR/nox-mem.db pre-populated (cloned from Phase H v2 winning DB)
#   - phaseB venv available
#   - $WORK/everos/benchmarks/EverMemBench installed
#   - pipeline.yaml already swapped to Phase H v2 config by caller
set -uo pipefail

BATCH="${1:?usage: $0 <BATCH> <PORT>}"
PORT="${2:?usage: $0 <BATCH> <PORT>}"
WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
RUN_DIR="${RUN_DIR:?RUN_DIR env var must be set}"
mkdir -p "$RUN_DIR"
echo "[PHASE-ITERB BATCH $BATCH PORT $PORT] RUN_DIR=$RUN_DIR"

# Source prod env to get OPENAI_API_KEY + GEMINI_API_KEY (but DO NOT clobber NOX_DB_PATH)
set -a; source /root/.openclaw/.env; set +a

# Activate venv (reuse Phase B venv)
source /root/.openclaw/evermembench-phaseB-1779978778/venv/bin/activate
echo "[PHASE-ITERB] venv python: $(which python)"

# Re-export AFTER source per [[evermembench-eval-gotchas-2026-05-28]]:
# Isolate Phase IterB from rerank + KG + MQ + IterC (study ReAct effect alone).
export NOX_RERANKER_ENABLED=0
unset NOX_RERANKER_MODEL || true
export NOX_KG_PATH_ENABLED=0
export NOX_MQ_ENABLED=0
export NOX_MA_PROTECTION_ENABLED=0
export NOX_ITERC_ENABLED=0
export NOX_ITERB_ENABLED=1

# Optional IterB tunables (default to spec values if unset)
export NOX_ITERB_ORCHESTRATOR_LLM="${NOX_ITERB_ORCHESTRATOR_LLM:-gpt-4.1-mini}"
# Resolve base URL + API key based on model family
if [[ "$NOX_ITERB_ORCHESTRATOR_LLM" == *"gemini"* ]]; then
    export NOX_ITERB_ORCHESTRATOR_BASE_URL="${NOX_ITERB_ORCHESTRATOR_BASE_URL:-https://generativelanguage.googleapis.com/v1beta/openai}"
    export NOX_ITERB_ORCHESTRATOR_API_KEY="${NOX_ITERB_ORCHESTRATOR_API_KEY:-$GEMINI_API_KEY}"
    # Gemini-3-flash pricing 2026 estimate
    export NOX_ITERB_INPUT_COST_PER_1M="${NOX_ITERB_INPUT_COST_PER_1M:-0.30}"
    export NOX_ITERB_OUTPUT_COST_PER_1M="${NOX_ITERB_OUTPUT_COST_PER_1M:-2.50}"
else
    export NOX_ITERB_ORCHESTRATOR_BASE_URL="${NOX_ITERB_ORCHESTRATOR_BASE_URL:-https://api.openai.com/v1}"
    export NOX_ITERB_ORCHESTRATOR_API_KEY="${NOX_ITERB_ORCHESTRATOR_API_KEY:-$OPENAI_API_KEY}"
    # gpt-4.1-mini pricing
    export NOX_ITERB_INPUT_COST_PER_1M="${NOX_ITERB_INPUT_COST_PER_1M:-0.40}"
    export NOX_ITERB_OUTPUT_COST_PER_1M="${NOX_ITERB_OUTPUT_COST_PER_1M:-1.60}"
fi
export NOX_ITERB_MAX_ROUNDS="${NOX_ITERB_MAX_ROUNDS:-5}"
export NOX_ITERB_PER_ROUND_TOPK="${NOX_ITERB_PER_ROUND_TOPK:-10}"
export NOX_ITERB_RRF_K="${NOX_ITERB_RRF_K:-60}"
export NOX_ITERB_ORCHESTRATOR_TIMEOUT_S="${NOX_ITERB_ORCHESTRATOR_TIMEOUT_S:-45}"
export NOX_ITERB_ORCHESTRATOR_MAX_TOKENS="${NOX_ITERB_ORCHESTRATOR_MAX_TOKENS:-400}"
export NOX_ITERB_COST_CEILING_USD="${NOX_ITERB_COST_CEILING_USD:-0.01}"

# cli.py routing (used by harness too)
export LLM_API_KEY="$GEMINI_API_KEY"
export LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"

# Verify keys
if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "[PHASE-ITERB BATCH $BATCH] ERROR: OPENAI_API_KEY not present (harness backbone needs it)"
    exit 1
fi
if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "[PHASE-ITERB BATCH $BATCH] ERROR: GEMINI_API_KEY not present (judge needs it)"
    exit 1
fi
echo "[PHASE-ITERB BATCH $BATCH] OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}...${OPENAI_API_KEY: -4} (len ${#OPENAI_API_KEY})"
echo "[PHASE-ITERB BATCH $BATCH] GEMINI_API_KEY: ${GEMINI_API_KEY:0:10}...${GEMINI_API_KEY: -4} (len ${#GEMINI_API_KEY})"

# Live preflight 1: harness final-answer backbone (gpt-4.1-mini)
echo "[PHASE-ITERB BATCH $BATCH] === Preflight 1: gpt-4.1-mini (harness final answer) ==="
PREFLIGHT=$(curl -s --max-time 30 https://api.openai.com/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -d '{"model":"gpt-4.1-mini","messages":[{"role":"user","content":"Reply only OK"}],"max_tokens":5,"temperature":0}')
if ! echo "$PREFLIGHT" | grep -q '"OK"'; then
    echo "[PHASE-ITERB BATCH $BATCH] ERROR: OpenAI preflight failed (auth OR billing)"
    echo "$PREFLIGHT" | head -c 600
    exit 1
fi
PREFLIGHT_TOKENS=$(echo "$PREFLIGHT" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("usage",{}).get("total_tokens","?"))')
echo "[PHASE-ITERB BATCH $BATCH] OpenAI preflight OK (total_tokens=$PREFLIGHT_TOKENS)"

# Live preflight 2: ReAct orchestrator (independent — may be Gemini cheap variant)
echo "[PHASE-ITERB BATCH $BATCH] === Preflight 2: $NOX_ITERB_ORCHESTRATOR_LLM (ReAct orchestrator) ==="
PREFLIGHT_ORC=$(curl -s --max-time 30 "${NOX_ITERB_ORCHESTRATOR_BASE_URL}/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $NOX_ITERB_ORCHESTRATOR_API_KEY" \
    -d "{\"model\":\"${NOX_ITERB_ORCHESTRATOR_LLM}\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply only OK\"}],\"max_tokens\":5,\"temperature\":0}")
if ! echo "$PREFLIGHT_ORC" | python3 -c 'import json,sys;d=json.load(sys.stdin);sys.exit(0 if d.get("choices") else 1)' 2>/dev/null; then
    echo "[PHASE-ITERB BATCH $BATCH] ERROR: orchestrator preflight failed"
    echo "$PREFLIGHT_ORC" | head -c 600
    exit 1
fi
echo "[PHASE-ITERB BATCH $BATCH] orchestrator preflight OK"

# Isolated DB + isolated port
export NOX_DB_PATH="$RUN_DIR/nox-mem.db"
export NOX_API_PORT="$PORT"
export NOX_API_BASE="http://127.0.0.1:$PORT"
export NOX_ADAPTER_MODE="phaseIterB"
export NOX_MEM_BIN="$(which nox-mem)"

echo "[PHASE-ITERB BATCH $BATCH] NOX_DB_PATH=$NOX_DB_PATH"
echo "[PHASE-ITERB BATCH $BATCH] NOX_ADAPTER_MODE=$NOX_ADAPTER_MODE"
echo "[PHASE-ITERB BATCH $BATCH] orchestrator=$NOX_ITERB_ORCHESTRATOR_LLM max_rounds=$NOX_ITERB_MAX_ROUNDS topk=$NOX_ITERB_PER_ROUND_TOPK ceiling=\$$NOX_ITERB_COST_CEILING_USD"
echo "[PHASE-ITERB BATCH $BATCH] isolation: rerank=$NOX_RERANKER_ENABLED kg=$NOX_KG_PATH_ENABLED mq=$NOX_MQ_ENABLED iterc=$NOX_ITERC_ENABLED"

# Verify DB pre-warmed
if [ ! -f "$NOX_DB_PATH" ]; then
    echo "[PHASE-ITERB BATCH $BATCH] ERROR: pre-warmed DB missing at $NOX_DB_PATH"
    exit 1
fi
EXISTING_CHUNKS=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM chunks;" 2>/dev/null || echo 0)
echo "[PHASE-ITERB BATCH $BATCH] pre-loaded DB chunks=$EXISTING_CHUNKS"
if [ "$EXISTING_CHUNKS" -lt 5000 ]; then
    echo "[PHASE-ITERB BATCH $BATCH] ERROR: DB not pre-warmed (chunks=$EXISTING_CHUNKS)"
    exit 1
fi

# Cleanup hook
API_PID=""
cleanup() {
    if [ -n "$API_PID" ]; then
        kill "$API_PID" 2>/dev/null || true
        wait "$API_PID" 2>/dev/null || true
        echo "[PHASE-ITERB BATCH $BATCH] killed api server pid=$API_PID"
    fi
}
trap cleanup EXIT

echo "[PHASE-ITERB BATCH $BATCH] === Step 1: spawn isolated api-server ==="
cd /root/.openclaw/workspace/tools/nox-mem
nohup node --no-warnings dist/api-server.js > "$RUN_DIR/api.log" 2>&1 &
API_PID=$!
echo "[PHASE-ITERB BATCH $BATCH] api pid=$API_PID, waiting 5s for boot..."
sleep 5

HEALTH=$(curl -s --max-time 10 "$NOX_API_BASE/api/health" || true)
if ! echo "$HEALTH" | grep -q "\"chunks\""; then
    echo "[PHASE-ITERB BATCH $BATCH] ERROR: api not responding"
    echo "$HEALTH" | head -c 300
    exit 1
fi
TOTAL=$(echo "$HEALTH" | python3 -c "import json,sys;d=json.load(sys.stdin);c=d['chunks'];print(c.get('total') if isinstance(c,dict) else c)")
echo "[PHASE-ITERB BATCH $BATCH] api health: chunks=$TOTAL"

echo "[PHASE-ITERB BATCH $BATCH] === Step 1b: clear stale harness results ==="
RESULTS_DIR="$EVAL/eval/results/nox_mem"
rm -f "$RESULTS_DIR/answer_results_$BATCH.json" "$RESULTS_DIR/evaluation_results_$BATCH.json" "$RESULTS_DIR/search_results_$BATCH.json"
echo "[PHASE-ITERB BATCH $BATCH] cleared stale files in $RESULTS_DIR"

echo "[PHASE-ITERB BATCH $BATCH] === Step 2: Search + Answer + Evaluate ==="
cd "$EVAL"
python -m eval.cli \
    --dataset "dataset/$BATCH/dialogue.json" \
    --qa "dataset/$BATCH/qa_$BATCH.json" \
    --system nox_mem \
    --user-id "$BATCH" \
    --stages search answer evaluate \
    --top-k 20 \
    > "$RUN_DIR/eval.log" 2>&1

echo "[PHASE-ITERB BATCH $BATCH] === Step 3: Analyze ==="
RESULTS_FILE="$RESULTS_DIR/evaluation_results_$BATCH.json"
if [ -f "$RESULTS_FILE" ]; then
    python tools/analyze_results.py "$RESULTS_FILE" > "$RUN_DIR/analysis.txt" 2>&1 || true
    cp "$RESULTS_FILE" "$RUN_DIR/results-batch-$BATCH.json"
    cp "$RESULTS_DIR/answer_results_$BATCH.json" "$RUN_DIR/answer-results-batch-$BATCH.json" 2>/dev/null || true
    # Archive search_results so we can audit Set E IterB metadata per question
    cp "$RESULTS_DIR/search_results_$BATCH.json" "$RUN_DIR/search-results-batch-$BATCH.json" 2>/dev/null || true
    echo "[PHASE-ITERB BATCH $BATCH] results -> $RUN_DIR/results-batch-$BATCH.json"
else
    echo "[PHASE-ITERB BATCH $BATCH] ERROR: no results file at $RESULTS_FILE"
    ls "$RESULTS_DIR" 2>&1 || true
fi

echo "[PHASE-ITERB BATCH $BATCH] === DONE ==="
ls -la "$RUN_DIR/"
