#!/bin/bash
# Phase IterC (Q3 POC) — pre-warmed batch runner (5-batch sequential variant).
# Self-Ask orchestration-stage: sub-Q decompose + per-sub-Q retrieve + per-sub-Q
# intermediate answer + chunk RRF union + context augmentation.
#
# Differs from run-batch-phaseMQ.sh:
#   - NOX_ADAPTER_MODE=phaseIterC (Self-Ask enabled by default)
#   - NOX_ITERC_ENABLED=1 (explicit override after .env source)
#   - NOX_MQ_ENABLED=0 (no MQ stacking — clean isolation of Self-Ask signal)
#   - NOX_RERANKER_ENABLED=0 (no rerank stacking)
#   - NOX_KG_PATH_ENABLED=0 (no KG stacking)
#   - Two preflights: gpt-4.1-mini (answerer + harness) + gemini-flash-lite
#     (decomposer)
#
# Methodology preserved from Phase H v2 + Phase MQ:
#   - Backbone (final answer via harness): gpt-4.1-mini
#   - Backbone (per-sub-Q intermediate): gpt-4.1-mini (same; cost doubles
#     vs Phase H v2 — single decomposer call + N=3 sub-answer calls + 1 final)
#   - Backbone (decomposer): gemini-2.5-flash-lite (cheap, fast)
#   - Judge: gemini-2.5-flash
#   - top_k=20 (harness final)
#   - top_k=10 per sub-question (NOX_ITERC_PER_QUERY_TOPK default)
#   - N=3 sub-questions (NOX_ITERC_N default — Self-Ask sweet spot)
#
# Usage (called by run-phaseIterC-5batch.sh):
#   WORK=/tmp/q3-iterC-poc-<short-uuid> \
#   RUN_DIR=/root/.openclaw/evermembench-runs/phaseIterC-<batch>-<ts> \
#   bash run-batch-phaseIterC.sh <BATCH> <PORT>
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
echo "[PHASE-ITERC BATCH $BATCH PORT $PORT] RUN_DIR=$RUN_DIR"

# Source prod env to get OPENAI_API_KEY + GEMINI_API_KEY (but DO NOT clobber NOX_DB_PATH)
set -a; source /root/.openclaw/.env; set +a

# Activate venv (reuse Phase B venv)
source /root/.openclaw/evermembench-phaseB-1779978778/venv/bin/activate
echo "[PHASE-ITERC] venv python: $(which python)"

# Re-export AFTER source per [[evermembench-eval-gotchas-2026-05-28]]:
# Isolate Phase IterC from rerank + KG + MQ (study Self-Ask effect in isolation).
export NOX_RERANKER_ENABLED=0
unset NOX_RERANKER_MODEL || true
export NOX_KG_PATH_ENABLED=0
export NOX_MQ_ENABLED=0
export NOX_MA_PROTECTION_ENABLED=0
export NOX_ITERC_ENABLED=1

# Optional IterC tunables (default to spec values if unset)
export NOX_ITERC_DECOMPOSER_LLM="${NOX_ITERC_DECOMPOSER_LLM:-gemini-2.5-flash-lite}"
export NOX_ITERC_DECOMPOSER_BASE_URL="${NOX_ITERC_DECOMPOSER_BASE_URL:-https://generativelanguage.googleapis.com/v1beta/openai}"
export NOX_ITERC_DECOMPOSER_API_KEY="${NOX_ITERC_DECOMPOSER_API_KEY:-$GEMINI_API_KEY}"
export NOX_ITERC_ANSWERER_LLM="${NOX_ITERC_ANSWERER_LLM:-gpt-4.1-mini}"
export NOX_ITERC_ANSWERER_BASE_URL="${NOX_ITERC_ANSWERER_BASE_URL:-https://api.openai.com/v1}"
export NOX_ITERC_ANSWERER_API_KEY="${NOX_ITERC_ANSWERER_API_KEY:-$OPENAI_API_KEY}"
export NOX_ITERC_N="${NOX_ITERC_N:-3}"
export NOX_ITERC_PER_QUERY_TOPK="${NOX_ITERC_PER_QUERY_TOPK:-10}"
export NOX_ITERC_RRF_K="${NOX_ITERC_RRF_K:-60}"
export NOX_ITERC_DECOMPOSER_TIMEOUT_S="${NOX_ITERC_DECOMPOSER_TIMEOUT_S:-30}"
export NOX_ITERC_ANSWERER_TIMEOUT_S="${NOX_ITERC_ANSWERER_TIMEOUT_S:-45}"
export NOX_ITERC_ANSWERER_MAX_TOKENS="${NOX_ITERC_ANSWERER_MAX_TOKENS:-160}"

# cli.py routing (used by harness too; matches Phase MQ pattern)
export LLM_API_KEY="$GEMINI_API_KEY"
export LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"

# Verify keys
if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "[PHASE-ITERC BATCH $BATCH] ERROR: OPENAI_API_KEY not present"
    exit 1
fi
if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "[PHASE-ITERC BATCH $BATCH] ERROR: GEMINI_API_KEY not present"
    exit 1
fi
echo "[PHASE-ITERC BATCH $BATCH] OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}...${OPENAI_API_KEY: -4} (len ${#OPENAI_API_KEY})"
echo "[PHASE-ITERC BATCH $BATCH] GEMINI_API_KEY: ${GEMINI_API_KEY:0:10}...${GEMINI_API_KEY: -4} (len ${#GEMINI_API_KEY})"

# Live preflight 1: REAL gpt-4.1-mini completion (answer backbone billing path
# — this is ALSO the per-sub-Q answerer, so a single preflight covers both)
echo "[PHASE-ITERC BATCH $BATCH] === Preflight 1: gpt-4.1-mini (final answer + sub-Q answerer) ==="
PREFLIGHT=$(curl -s --max-time 30 https://api.openai.com/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -d '{"model":"gpt-4.1-mini","messages":[{"role":"user","content":"Reply only OK"}],"max_tokens":5,"temperature":0}')
if ! echo "$PREFLIGHT" | grep -q '"OK"'; then
    echo "[PHASE-ITERC BATCH $BATCH] ERROR: OpenAI preflight failed (auth OR billing)"
    echo "$PREFLIGHT" | head -c 600
    exit 1
fi
PREFLIGHT_TOKENS=$(echo "$PREFLIGHT" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("usage",{}).get("total_tokens","?"))')
echo "[PHASE-ITERC BATCH $BATCH] OpenAI preflight OK (total_tokens=$PREFLIGHT_TOKENS)"

# Live preflight 2: REAL gemini-flash-lite completion (decomposer billing path)
echo "[PHASE-ITERC BATCH $BATCH] === Preflight 2: gemini-2.5-flash-lite (decomposer) ==="
PREFLIGHT_DEC=$(curl -s --max-time 30 "${NOX_ITERC_DECOMPOSER_BASE_URL}/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $NOX_ITERC_DECOMPOSER_API_KEY" \
    -d "{\"model\":\"${NOX_ITERC_DECOMPOSER_LLM}\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply only OK\"}],\"max_tokens\":5,\"temperature\":0}")
if ! echo "$PREFLIGHT_DEC" | python3 -c 'import json,sys;d=json.load(sys.stdin);sys.exit(0 if d.get("choices") else 1)' 2>/dev/null; then
    echo "[PHASE-ITERC BATCH $BATCH] ERROR: Gemini decomposer preflight failed"
    echo "$PREFLIGHT_DEC" | head -c 600
    exit 1
fi
echo "[PHASE-ITERC BATCH $BATCH] decomposer preflight OK"

# Isolated DB + isolated port
export NOX_DB_PATH="$RUN_DIR/nox-mem.db"
export NOX_API_PORT="$PORT"
export NOX_API_BASE="http://127.0.0.1:$PORT"
export NOX_ADAPTER_MODE="phaseIterC"
export NOX_MEM_BIN="$(which nox-mem)"

echo "[PHASE-ITERC BATCH $BATCH] NOX_DB_PATH=$NOX_DB_PATH"
echo "[PHASE-ITERC BATCH $BATCH] NOX_ADAPTER_MODE=$NOX_ADAPTER_MODE"
echo "[PHASE-ITERC BATCH $BATCH] NOX_ITERC_ENABLED=$NOX_ITERC_ENABLED N=$NOX_ITERC_N PER_TOPK=$NOX_ITERC_PER_QUERY_TOPK RRF_K=$NOX_ITERC_RRF_K"
echo "[PHASE-ITERC BATCH $BATCH] NOX_RERANKER_ENABLED=$NOX_RERANKER_ENABLED NOX_KG_PATH_ENABLED=$NOX_KG_PATH_ENABLED NOX_MQ_ENABLED=$NOX_MQ_ENABLED"

# Verify DB pre-warmed
if [ ! -f "$NOX_DB_PATH" ]; then
    echo "[PHASE-ITERC BATCH $BATCH] ERROR: pre-warmed DB missing at $NOX_DB_PATH"
    exit 1
fi
EXISTING_CHUNKS=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM chunks;" 2>/dev/null || echo 0)
echo "[PHASE-ITERC BATCH $BATCH] pre-loaded DB chunks=$EXISTING_CHUNKS"
if [ "$EXISTING_CHUNKS" -lt 5000 ]; then
    echo "[PHASE-ITERC BATCH $BATCH] ERROR: DB not pre-warmed (chunks=$EXISTING_CHUNKS)"
    exit 1
fi

# Cleanup hook
API_PID=""
cleanup() {
    if [ -n "$API_PID" ]; then
        kill "$API_PID" 2>/dev/null || true
        wait "$API_PID" 2>/dev/null || true
        echo "[PHASE-ITERC BATCH $BATCH] killed api server pid=$API_PID"
    fi
}
trap cleanup EXIT

echo "[PHASE-ITERC BATCH $BATCH] === Step 1: spawn isolated api-server ==="
cd /root/.openclaw/workspace/tools/nox-mem
nohup node --no-warnings dist/api-server.js > "$RUN_DIR/api.log" 2>&1 &
API_PID=$!
echo "[PHASE-ITERC BATCH $BATCH] api pid=$API_PID, waiting 5s for boot..."
sleep 5

HEALTH=$(curl -s --max-time 10 "$NOX_API_BASE/api/health" || true)
if ! echo "$HEALTH" | grep -q "\"chunks\""; then
    echo "[PHASE-ITERC BATCH $BATCH] ERROR: api not responding"
    echo "$HEALTH" | head -c 300
    exit 1
fi
TOTAL=$(echo "$HEALTH" | python3 -c "import json,sys;d=json.load(sys.stdin);c=d['chunks'];print(c.get('total') if isinstance(c,dict) else c)")
echo "[PHASE-ITERC BATCH $BATCH] api health: chunks=$TOTAL"

echo "[PHASE-ITERC BATCH $BATCH] === Step 1b: clear stale harness results ==="
RESULTS_DIR="$EVAL/eval/results/nox_mem"
rm -f "$RESULTS_DIR/answer_results_$BATCH.json" "$RESULTS_DIR/evaluation_results_$BATCH.json" "$RESULTS_DIR/search_results_$BATCH.json"
echo "[PHASE-ITERC BATCH $BATCH] cleared stale files in $RESULTS_DIR"

echo "[PHASE-ITERC BATCH $BATCH] === Step 2: Search + Answer + Evaluate ==="
cd "$EVAL"
python -m eval.cli \
    --dataset "dataset/$BATCH/dialogue.json" \
    --qa "dataset/$BATCH/qa_$BATCH.json" \
    --system nox_mem \
    --user-id "$BATCH" \
    --stages search answer evaluate \
    --top-k 20 \
    > "$RUN_DIR/eval.log" 2>&1

echo "[PHASE-ITERC BATCH $BATCH] === Step 3: Analyze ==="
RESULTS_FILE="$RESULTS_DIR/evaluation_results_$BATCH.json"
if [ -f "$RESULTS_FILE" ]; then
    python tools/analyze_results.py "$RESULTS_FILE" > "$RUN_DIR/analysis.txt" 2>&1 || true
    cp "$RESULTS_FILE" "$RUN_DIR/results-batch-$BATCH.json"
    cp "$RESULTS_DIR/answer_results_$BATCH.json" "$RUN_DIR/answer-results-batch-$BATCH.json" 2>/dev/null || true
    # Archive search_results so we can audit Set E IterC metadata per question
    cp "$RESULTS_DIR/search_results_$BATCH.json" "$RUN_DIR/search-results-batch-$BATCH.json" 2>/dev/null || true
    echo "[PHASE-ITERC BATCH $BATCH] results -> $RUN_DIR/results-batch-$BATCH.json"
else
    echo "[PHASE-ITERC BATCH $BATCH] ERROR: no results file at $RESULTS_FILE"
    ls "$RESULTS_DIR" 2>&1 || true
fi

echo "[PHASE-ITERC BATCH $BATCH] === DONE ==="
ls -la "$RUN_DIR/"
