#!/bin/bash
# Phase KGMQ (Wave B composability, 2026-05-29) — KG + MQ combined.
# Combines Phase KG 1-hop entity boost + Phase MQ sub-query decomposition.
# Wave B 4-gate composability test: validates additive hypothesis
# `[[mq-kg-mechanically-additive-prediction-6-42pp]]`.
#
# Key differences from run-batch-phaseMQ.sh:
#   - NOX_ADAPTER_MODE=phaseKGMQ (both KG + MQ enabled by default)
#   - NOX_KG_PATH_ENABLED=1 (explicit override after .env source)
#   - NOX_MQ_ENABLED=1 (explicit override after .env source)
#   - NOX_RERANKER_ENABLED=0 (isolate composability — no rerank stacking)
#   - Port 18846 (isolated from MAP @ 18847 paralelo Wave B + KG @ ... + MQ @ ...)
#
# Methodology preserved from Phase H v2:
#   - Backbone (answer): gpt-4.1-mini via OpenAI direct
#   - Backbone (decomposer): gemini-2.5-flash-lite (free under quota)
#   - Judge: gemini-2.5-flash
#   - top_k=20 (harness final)
#
# Usage (called by run-sequential-phaseKGMQ.sh):
#   WORK=/tmp/wave-B-KG-MQ-<uuid> \
#   RUN_DIR=/root/.openclaw/evermembench-runs/phaseKGMQ-<batch>-<ts> \
#   bash run-batch-phaseKGMQ.sh <BATCH> <PORT>
set -uo pipefail

BATCH="${1:?usage: $0 <BATCH> <PORT>}"
PORT="${2:?usage: $0 <BATCH> <PORT>}"
WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
RUN_DIR="${RUN_DIR:?RUN_DIR env var must be set}"
mkdir -p "$RUN_DIR"
echo "[PHASE-KGMQ BATCH $BATCH PORT $PORT] RUN_DIR=$RUN_DIR"

# Source prod env to get OPENAI_API_KEY + GEMINI_API_KEY
set -a; source /root/.openclaw/.env; set +a

# Activate venv (reuse Phase B venv with harness deps)
source /root/.openclaw/evermembench-phaseB-1779978778/venv/bin/activate
echo "[PHASE-KGMQ] venv python: $(which python)"

# Re-export AFTER source per [[evermembench-eval-gotchas-2026-05-28]]:
# Activate BOTH KG path + MQ expansion. Isolate from rerank.
export NOX_RERANKER_ENABLED=0
unset NOX_RERANKER_MODEL || true
export NOX_KG_PATH_ENABLED=1
export NOX_MQ_ENABLED=1

# KG tunables (spec defaults preserved)
export NOX_KG_BOOST_MAGNITUDE="${NOX_KG_BOOST_MAGNITUDE:-0.05}"
export NOX_KG_DIRECT_MULTIPLIER="${NOX_KG_DIRECT_MULTIPLIER:-1.5}"
export NOX_KG_MAX_NEIGHBORS="${NOX_KG_MAX_NEIGHBORS:-20}"
export NOX_KG_MIN_NAME_LEN="${NOX_KG_MIN_NAME_LEN:-3}"
export NOX_KG_OVERFETCH="${NOX_KG_OVERFETCH:-50}"

# MQ tunables (spec defaults preserved)
export NOX_MQ_LLM="${NOX_MQ_LLM:-gemini-2.5-flash-lite}"
export NOX_MQ_LLM_BASE_URL="${NOX_MQ_LLM_BASE_URL:-https://generativelanguage.googleapis.com/v1beta/openai}"
export NOX_MQ_LLM_API_KEY="${NOX_MQ_LLM_API_KEY:-$GEMINI_API_KEY}"
export NOX_MQ_N="${NOX_MQ_N:-4}"
export NOX_MQ_PER_QUERY_TOPK="${NOX_MQ_PER_QUERY_TOPK:-10}"
export NOX_MQ_RRF_K="${NOX_MQ_RRF_K:-60}"
export NOX_MQ_TIMEOUT_S="${NOX_MQ_TIMEOUT_S:-30}"

# cli.py judge routing (Gemini)
export LLM_API_KEY="$GEMINI_API_KEY"
export LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"

# Verify keys
if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "[PHASE-KGMQ BATCH $BATCH] ERROR: OPENAI_API_KEY not present"
    exit 1
fi
if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "[PHASE-KGMQ BATCH $BATCH] ERROR: GEMINI_API_KEY not present"
    exit 1
fi
echo "[PHASE-KGMQ BATCH $BATCH] OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}...${OPENAI_API_KEY: -4} (len ${#OPENAI_API_KEY})"
echo "[PHASE-KGMQ BATCH $BATCH] GEMINI_API_KEY: ${GEMINI_API_KEY:0:10}...${GEMINI_API_KEY: -4} (len ${#GEMINI_API_KEY})"

# Live preflight 1: REAL gpt-4.1-mini completion (answer backbone billing path)
echo "[PHASE-KGMQ BATCH $BATCH] === Preflight 1: gpt-4.1-mini (answer) ==="
PREFLIGHT=$(curl -s --max-time 30 https://api.openai.com/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -d '{"model":"gpt-4.1-mini","messages":[{"role":"user","content":"Reply only OK"}],"max_tokens":5,"temperature":0}')
if ! echo "$PREFLIGHT" | grep -q '"OK"'; then
    echo "[PHASE-KGMQ BATCH $BATCH] ERROR: OpenAI preflight failed"
    echo "$PREFLIGHT" | head -c 600
    exit 1
fi
PREFLIGHT_TOKENS=$(echo "$PREFLIGHT" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("usage",{}).get("total_tokens","?"))')
echo "[PHASE-KGMQ BATCH $BATCH] preflight OK (total_tokens=$PREFLIGHT_TOKENS)"

# Live preflight 2: REAL gemini-flash-lite (decomposer billing path)
echo "[PHASE-KGMQ BATCH $BATCH] === Preflight 2: gemini-2.5-flash-lite (decomposer) ==="
PREFLIGHT_MQ=$(curl -s --max-time 30 "${NOX_MQ_LLM_BASE_URL}/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $NOX_MQ_LLM_API_KEY" \
    -d "{\"model\":\"${NOX_MQ_LLM}\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply only OK\"}],\"max_tokens\":5,\"temperature\":0}")
if ! echo "$PREFLIGHT_MQ" | python3 -c 'import json,sys;d=json.load(sys.stdin);sys.exit(0 if d.get("choices") else 1)' 2>/dev/null; then
    echo "[PHASE-KGMQ BATCH $BATCH] ERROR: Gemini decomposer preflight failed"
    echo "$PREFLIGHT_MQ" | head -c 600
    exit 1
fi
echo "[PHASE-KGMQ BATCH $BATCH] decomposer preflight OK"

# Isolated DB + isolated port
export NOX_DB_PATH="$RUN_DIR/nox-mem.db"
export NOX_API_PORT="$PORT"
export NOX_API_BASE="http://127.0.0.1:$PORT"
export NOX_ADAPTER_MODE="phaseKGMQ"
export NOX_MEM_BIN="$(which nox-mem)"

echo "[PHASE-KGMQ BATCH $BATCH] NOX_DB_PATH=$NOX_DB_PATH"
echo "[PHASE-KGMQ BATCH $BATCH] NOX_ADAPTER_MODE=$NOX_ADAPTER_MODE"
echo "[PHASE-KGMQ BATCH $BATCH] KG: enabled=$NOX_KG_PATH_ENABLED boost=$NOX_KG_BOOST_MAGNITUDE direct_mult=$NOX_KG_DIRECT_MULTIPLIER max_neighbors=$NOX_KG_MAX_NEIGHBORS"
echo "[PHASE-KGMQ BATCH $BATCH] MQ: enabled=$NOX_MQ_ENABLED N=$NOX_MQ_N per_topk=$NOX_MQ_PER_QUERY_TOPK rrf_k=$NOX_MQ_RRF_K"
echo "[PHASE-KGMQ BATCH $BATCH] RERANK: enabled=$NOX_RERANKER_ENABLED"

# Verify DB pre-warmed
if [ ! -f "$NOX_DB_PATH" ]; then
    echo "[PHASE-KGMQ BATCH $BATCH] ERROR: pre-warmed DB missing at $NOX_DB_PATH"
    exit 1
fi
EXISTING_CHUNKS=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM chunks;" 2>/dev/null || echo 0)
EXISTING_KG_ENT=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM kg_entities;" 2>/dev/null || echo 0)
EXISTING_KG_REL=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM kg_relations;" 2>/dev/null || echo 0)
echo "[PHASE-KGMQ BATCH $BATCH] pre-loaded DB chunks=$EXISTING_CHUNKS kg_entities=$EXISTING_KG_ENT kg_relations=$EXISTING_KG_REL"
if [ "$EXISTING_CHUNKS" -lt 5000 ]; then
    echo "[PHASE-KGMQ BATCH $BATCH] ERROR: DB not pre-warmed (chunks=$EXISTING_CHUNKS)"
    exit 1
fi
if [ "$EXISTING_KG_ENT" -lt 100 ]; then
    echo "[PHASE-KGMQ BATCH $BATCH] WARN: KG sparse (entities=$EXISTING_KG_ENT) — KG boost may be limited"
fi

# Cleanup hook
API_PID=""
cleanup() {
    if [ -n "$API_PID" ]; then
        kill "$API_PID" 2>/dev/null || true
        wait "$API_PID" 2>/dev/null || true
        echo "[PHASE-KGMQ BATCH $BATCH] killed api server pid=$API_PID"
    fi
}
trap cleanup EXIT

echo "[PHASE-KGMQ BATCH $BATCH] === Step 1: spawn isolated api-server ==="
cd /root/.openclaw/workspace/tools/nox-mem
nohup node --no-warnings dist/api-server.js > "$RUN_DIR/api.log" 2>&1 &
API_PID=$!
echo "[PHASE-KGMQ BATCH $BATCH] api pid=$API_PID, waiting 5s for boot..."
sleep 5

HEALTH=$(curl -s --max-time 10 "$NOX_API_BASE/api/health" || true)
if ! echo "$HEALTH" | grep -q "\"chunks\""; then
    echo "[PHASE-KGMQ BATCH $BATCH] ERROR: api not responding"
    echo "$HEALTH" | head -c 300
    exit 1
fi
TOTAL=$(echo "$HEALTH" | python3 -c "import json,sys;d=json.load(sys.stdin);c=d['chunks'];print(c.get('total') if isinstance(c,dict) else c)")
echo "[PHASE-KGMQ BATCH $BATCH] api health: chunks=$TOTAL"

echo "[PHASE-KGMQ BATCH $BATCH] === Step 1b: clear stale harness results ==="
RESULTS_DIR="$EVAL/eval/results/nox_mem"
rm -f "$RESULTS_DIR/answer_results_$BATCH.json" "$RESULTS_DIR/evaluation_results_$BATCH.json" "$RESULTS_DIR/search_results_$BATCH.json"
echo "[PHASE-KGMQ BATCH $BATCH] cleared stale files in $RESULTS_DIR"

echo "[PHASE-KGMQ BATCH $BATCH] === Step 2: Search + Answer + Evaluate ==="
cd "$EVAL"
python -m eval.cli \
    --dataset "dataset/$BATCH/dialogue.json" \
    --qa "dataset/$BATCH/qa_$BATCH.json" \
    --system nox_mem \
    --user-id "$BATCH" \
    --stages search answer evaluate \
    --top-k 20 \
    > "$RUN_DIR/eval.log" 2>&1

echo "[PHASE-KGMQ BATCH $BATCH] === Step 3: Analyze ==="
RESULTS_FILE="$RESULTS_DIR/evaluation_results_$BATCH.json"
if [ -f "$RESULTS_FILE" ]; then
    python tools/analyze_results.py "$RESULTS_FILE" > "$RUN_DIR/analysis.txt" 2>&1 || true
    cp "$RESULTS_FILE" "$RUN_DIR/results-batch-$BATCH.json"
    cp "$RESULTS_DIR/answer_results_$BATCH.json" "$RUN_DIR/answer-results-batch-$BATCH.json" 2>/dev/null || true
    cp "$RESULTS_DIR/search_results_$BATCH.json" "$RUN_DIR/search-results-batch-$BATCH.json" 2>/dev/null || true
    echo "[PHASE-KGMQ BATCH $BATCH] results -> $RUN_DIR/results-batch-$BATCH.json"
else
    echo "[PHASE-KGMQ BATCH $BATCH] ERROR: no results file at $RESULTS_FILE"
    ls "$RESULTS_DIR" 2>&1 || true
fi

echo "[PHASE-KGMQ BATCH $BATCH] === DONE ==="
ls -la "$RUN_DIR/"
