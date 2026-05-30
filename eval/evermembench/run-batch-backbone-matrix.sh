#!/bin/bash
# Backbone Matrix bench — per-batch runner (2026-05-29).
#
# Generic over BACKBONE env var. Caller (run-parallel-backbone-matrix.sh)
# swaps pipeline.yaml ONCE before fan-out (avoids race).
#
# Methodology preserved from Phase H v2 (5-batch baseline PR #377):
#   - Pre-warmed Phase B DB (skip Add + Vectorize)
#   - top_k=20
#   - Rerank OFF (NOX_RERANKER_ENABLED=0)
#   - Adapter mode: phaseB (baseline; no Wave A/B/C knobs)
#   - Judge constant: gemini-2.5-flash (only ANSWER backbone changes)
#   - Preflight: real ANSWER backbone billing path (NOT just /v1/models)
#
# Usage (called by run-parallel-backbone-matrix.sh):
#   WORK=/root/.openclaw/backbone-matrix-<uuid> \
#   RUN_DIR=/root/.openclaw/evermembench-runs/backbone-matrix-<backbone>-<batch>-<ts> \
#   BACKBONE=<gpt-5|gpt-5-mini|gemini-3-flash-preview> \
#   bash run-batch-backbone-matrix.sh <BATCH> <PORT>
set -uo pipefail

BATCH="${1:?usage: $0 <BATCH> <PORT>}"
PORT="${2:?usage: $0 <BATCH> <PORT>}"
BACKBONE="${BACKBONE:?BACKBONE env var must be set}"
WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
RUN_DIR="${RUN_DIR:?RUN_DIR env var must be set}"
mkdir -p "$RUN_DIR"

LABEL="[BB-MATRIX $BACKBONE B$BATCH P$PORT]"
echo "$LABEL RUN_DIR=$RUN_DIR"

# Source prod env (OPENAI_API_KEY + GEMINI_API_KEY) — but do NOT clobber NOX_DB_PATH
set -a; source /root/.openclaw/.env; set +a

# Activate venv (reuse phaseB harness install)
source /root/.openclaw/evermembench-phaseB-1779978778/venv/bin/activate
echo "$LABEL venv python: $(which python)"

# Re-export AFTER source (Phase H v2 lesson: env source can re-load stale vars).
# Isolate from Wave A/B/C + Phase G rerank state.
export NOX_RERANKER_ENABLED=0
unset NOX_RERANKER_MODEL || true

# cli.py presence check expects LLM_API_KEY (routing actually via per-stage api_key in pipeline.yaml)
export LLM_API_KEY="$GEMINI_API_KEY"
export LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"

# Verify keys
if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "$LABEL ERROR: OPENAI_API_KEY missing"; exit 1
fi
if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "$LABEL ERROR: GEMINI_API_KEY missing"; exit 1
fi

# Backbone-specific preflight: REAL completion (billing path).
# Per [[preflight-must-exercise-billing-path]] — /v1/models 200OK ≠ billing OK.
echo "$LABEL === Preflight: $BACKBONE completion ==="
case "$BACKBONE" in
  gpt-5|gpt-5-mini)
    PREFLIGHT=$(curl -s --max-time 30 https://api.openai.com/v1/chat/completions \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $OPENAI_API_KEY" \
        -d "{\"model\":\"$BACKBONE\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply only OK\"}],\"max_completion_tokens\":20,\"reasoning_effort\":\"minimal\"}")
    ;;
  gpt-4.1-mini)
    PREFLIGHT=$(curl -s --max-time 30 https://api.openai.com/v1/chat/completions \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $OPENAI_API_KEY" \
        -d "{\"model\":\"$BACKBONE\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply only OK\"}],\"max_tokens\":5,\"temperature\":0}")
    ;;
  gemini-*)
    PREFLIGHT=$(curl -s --max-time 30 "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $GEMINI_API_KEY" \
        -d "{\"model\":\"$BACKBONE\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply only OK\"}],\"max_tokens\":500,\"temperature\":0}")
    ;;
  *)
    echo "$LABEL ERROR: unknown BACKBONE=$BACKBONE"; exit 1
    ;;
esac

if ! echo "$PREFLIGHT" | grep -qi 'OK\|"content"'; then
    echo "$LABEL ERROR: preflight failed"
    echo "$PREFLIGHT" | head -c 600
    exit 1
fi
PREFLIGHT_TOKENS=$(echo "$PREFLIGHT" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("usage",{}).get("total_tokens","?"))' 2>/dev/null || echo "?")
echo "$LABEL preflight OK (total_tokens=$PREFLIGHT_TOKENS)"

# Isolated DB + port
export NOX_DB_PATH="$RUN_DIR/nox-mem.db"
export NOX_API_PORT="$PORT"
export NOX_API_BASE="http://127.0.0.1:$PORT"
export NOX_ADAPTER_MODE="${NOX_ADAPTER_MODE:-phaseB}"
export NOX_MEM_BIN="$(which nox-mem)"

echo "$LABEL NOX_DB_PATH=$NOX_DB_PATH"
echo "$LABEL NOX_ADAPTER_MODE=$NOX_ADAPTER_MODE"

# Verify DB pre-warmed
if [ ! -f "$NOX_DB_PATH" ]; then
    echo "$LABEL ERROR: pre-warmed DB missing"; exit 1
fi
EXISTING_CHUNKS=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM chunks;" 2>/dev/null || echo 0)
echo "$LABEL pre-loaded DB chunks=$EXISTING_CHUNKS"
if [ "$EXISTING_CHUNKS" -lt 5000 ]; then
    echo "$LABEL ERROR: DB not pre-warmed (chunks=$EXISTING_CHUNKS)"; exit 1
fi

# Cleanup
API_PID=""
cleanup() {
    if [ -n "$API_PID" ]; then
        kill "$API_PID" 2>/dev/null || true
        wait "$API_PID" 2>/dev/null || true
        echo "$LABEL killed api server pid=$API_PID"
    fi
}
trap cleanup EXIT

echo "$LABEL === Step 1: spawn isolated api-server ==="
cd /root/.openclaw/workspace/tools/nox-mem
nohup node --no-warnings dist/api-server.js > "$RUN_DIR/api.log" 2>&1 &
API_PID=$!
echo "$LABEL api pid=$API_PID, waiting 5s..."
sleep 5

HEALTH=$(curl -s --max-time 10 "$NOX_API_BASE/api/health" || true)
if ! echo "$HEALTH" | grep -q "\"chunks\""; then
    echo "$LABEL ERROR: api not responding"
    echo "$HEALTH" | head -c 300
    exit 1
fi
TOTAL=$(echo "$HEALTH" | python3 -c "import json,sys;d=json.load(sys.stdin);c=d['chunks'];print(c.get('total') if isinstance(c,dict) else c)")
echo "$LABEL api health: chunks=$TOTAL"

echo "$LABEL === Step 1b: clear stale harness results (resume short-circuit) ==="
RESULTS_DIR="$EVAL/eval/results/nox_mem"
rm -f "$RESULTS_DIR/answer_results_$BATCH.json" "$RESULTS_DIR/evaluation_results_$BATCH.json" "$RESULTS_DIR/search_results_$BATCH.json"

echo "$LABEL === Step 2: Search + Answer + Evaluate ==="
cd "$EVAL"
python -m eval.cli \
    --dataset "dataset/$BATCH/dialogue.json" \
    --qa "dataset/$BATCH/qa_$BATCH.json" \
    --system nox_mem \
    --user-id "$BATCH" \
    --stages search answer evaluate \
    --top-k 20 \
    > "$RUN_DIR/eval.log" 2>&1

echo "$LABEL === Step 3: Analyze ==="
RESULTS_FILE="$RESULTS_DIR/evaluation_results_$BATCH.json"
if [ -f "$RESULTS_FILE" ]; then
    python tools/analyze_results.py "$RESULTS_FILE" > "$RUN_DIR/analysis.txt" 2>&1 || true
    cp "$RESULTS_FILE" "$RUN_DIR/results-batch-$BATCH.json"
    cp "$RESULTS_DIR/answer_results_$BATCH.json" "$RUN_DIR/answer-results-batch-$BATCH.json" 2>/dev/null || true
    echo "$LABEL results -> $RUN_DIR/results-batch-$BATCH.json"
else
    echo "$LABEL ERROR: no results file at $RESULTS_FILE"
    ls "$RESULTS_DIR" 2>&1 || true
fi

echo "$LABEL === DONE ==="
ls -la "$RUN_DIR/"
