#!/bin/bash
# Wave 2 R0 — KG path sanity check on Gemini-3-flash backbone.
#
# Backbone-portability validation for KG path retrieval (PR #379 Lab Q1 #4).
# PR #379 measured +2.81pp F_MH lift on gpt-4.1-mini; this R0 validates the
# same mechanism replicates on Gemini-3-flash-preview (D70 SOTA primary).
#
# Mechanism (frozen from PR #379):
#   - NOX_ADAPTER_MODE=phaseKG (KG boost enabled by default)
#   - NOX_KG_PATH_ENABLED=1 (explicit override after .env source)
#   - All other knobs OFF (no IterB, no AC, no MQ, no MA-protection, no rerank)
#   - Pre-condition: DB MUST have kg_entities + kg_relations populated
#
# Differs from run-batch-phaseKG.sh:
#   - Final-answer backbone: gemini-3-flash-preview (was gpt-4.1-mini)
#   - Pipeline.yaml: pipeline-backbone-gemini3flash.yaml (already exists)
#   - Preflight TWO Gemini paths: gemini-3-flash-preview + gemini-2.5-flash judge
#     (per [[preflight-must-exercise-billing-path]] + [[preflight-must-validate-both-backbones]])
#
# Methodology preserved from PR #379 + D70 backbone matrix:
#   - Backbone (final answer via harness): gemini-3-flash-preview
#   - Judge: gemini-2.5-flash (convention unchanged)
#   - Embed: gemini-embedding-001 (3072d)
#   - top_k=20
#   - 5-batch sequential: 004, 005, 010, 011, 016 (SAME as PR #419 / D70)
#
# Usage (called by run-r0-kg-gemini-5batch.sh):
#   WORK=/tmp/r0-kg-gemini-<short-uuid> \
#   RUN_DIR=/root/.openclaw/evermembench-runs/r0-kg-gemini-<batch>-<ts> \
#   bash run-batch-r0-kg-gemini.sh <BATCH> <PORT>
#
# Prereqs (caller must satisfy):
#   - $RUN_DIR/nox-mem.db pre-populated (cloned from Phase KG winning DBs
#     which already have kg_entities + kg_relations + vectors)
#   - $WORK/venv contains harness deps
#   - $WORK/everos/benchmarks/EverMemBench installed
#   - pipeline.yaml already swapped to gemini-3-flash config by caller
set -uo pipefail

BATCH="${1:?usage: $0 <BATCH> <PORT>}"
PORT="${2:?usage: $0 <BATCH> <PORT>}"
WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
RUN_DIR="${RUN_DIR:?RUN_DIR env var must be set}"
mkdir -p "$RUN_DIR"
echo "[R0-KG-GEMINI BATCH $BATCH PORT $PORT] RUN_DIR=$RUN_DIR"

# Source prod env to get OPENAI_API_KEY + GEMINI_API_KEY (but DO NOT clobber NOX_DB_PATH)
set -a; source /root/.openclaw/.env; set +a

# Activate venv (reuse Phase B venv)
source /root/.openclaw/evermembench-phaseB-1779978778/venv/bin/activate
echo "[R0-KG-GEMINI] venv python: $(which python)"

# Re-export AFTER source per [[evermembench-eval-gotchas-2026-05-28]]:
# Isolate KG path from all other mechanisms (study KG effect alone on Gemini backbone).
export NOX_RERANKER_ENABLED=0
unset NOX_RERANKER_MODEL || true
export NOX_KG_PATH_ENABLED=1
export NOX_MQ_ENABLED=0
export NOX_MA_PROTECTION_ENABLED=0
export NOX_ITERB_ENABLED=0
export NOX_ITERC_ENABLED=0

# cli.py routing — harness uses Gemini family for answer + judge
export LLM_API_KEY="$GEMINI_API_KEY"
export LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"

# Verify keys
if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "[R0-KG-GEMINI BATCH $BATCH] ERROR: GEMINI_API_KEY not present (backbone + judge need it)"
    exit 1
fi
echo "[R0-KG-GEMINI BATCH $BATCH] GEMINI_API_KEY: ${GEMINI_API_KEY:0:10}...${GEMINI_API_KEY: -4} (len ${#GEMINI_API_KEY})"

# Live preflight 1: harness final-answer backbone (gemini-3-flash-preview)
# CRITICAL: per [[preflight-must-exercise-billing-path]], /v1/models 200OK != billing OK.
# Small chat completion 5 tokens REAL billing path test.
echo "[R0-KG-GEMINI BATCH $BATCH] === Preflight 1: gemini-3-flash-preview (harness final answer, billing path) ==="
PREFLIGHT=$(curl -s --max-time 30 "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $GEMINI_API_KEY" \
    -d '{"model":"gemini-3-flash-preview","messages":[{"role":"user","content":"Reply only OK"}],"max_tokens":5,"temperature":0}')
if ! echo "$PREFLIGHT" | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("choices") else 1)' 2>/dev/null; then
    echo "[R0-KG-GEMINI BATCH $BATCH] ERROR: gemini-3-flash-preview preflight failed (auth OR billing)"
    echo "$PREFLIGHT" | head -c 600
    exit 1
fi
PREFLIGHT_TOKENS=$(echo "$PREFLIGHT" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("usage",{}).get("total_tokens","?"))' 2>/dev/null || echo "?")
echo "[R0-KG-GEMINI BATCH $BATCH] gemini-3-flash-preview preflight OK (total_tokens=$PREFLIGHT_TOKENS)"

# Live preflight 2: judge backbone (gemini-2.5-flash)
echo "[R0-KG-GEMINI BATCH $BATCH] === Preflight 2: gemini-2.5-flash (judge, billing path) ==="
PREFLIGHT_J=$(curl -s --max-time 30 "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $GEMINI_API_KEY" \
    -d '{"model":"gemini-2.5-flash","messages":[{"role":"user","content":"Reply only OK"}],"max_tokens":5,"temperature":0}')
if ! echo "$PREFLIGHT_J" | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("choices") else 1)' 2>/dev/null; then
    echo "[R0-KG-GEMINI BATCH $BATCH] ERROR: gemini-2.5-flash preflight failed (auth OR billing)"
    echo "$PREFLIGHT_J" | head -c 600
    exit 1
fi
echo "[R0-KG-GEMINI BATCH $BATCH] gemini-2.5-flash judge preflight OK"

# Isolated DB + isolated port
export NOX_DB_PATH="$RUN_DIR/nox-mem.db"
export NOX_API_PORT="$PORT"
export NOX_API_BASE="http://127.0.0.1:$PORT"
export NOX_ADAPTER_MODE="phaseKG"
export NOX_MEM_BIN="$(which nox-mem)"
# Defensive: confirm sandbox-eval allowed (per PR #145)
export NOX_ALLOW_PROD_INGEST=1

echo "[R0-KG-GEMINI BATCH $BATCH] NOX_DB_PATH=$NOX_DB_PATH"
echo "[R0-KG-GEMINI BATCH $BATCH] NOX_ADAPTER_MODE=$NOX_ADAPTER_MODE"
echo "[R0-KG-GEMINI BATCH $BATCH] isolation: rerank=$NOX_RERANKER_ENABLED kg=$NOX_KG_PATH_ENABLED mq=$NOX_MQ_ENABLED iterb=$NOX_ITERB_ENABLED iterc=$NOX_ITERC_ENABLED ma_prot=$NOX_MA_PROTECTION_ENABLED"

# Verify DB pre-warmed AND has KG populated (KG path needs entities + relations)
if [ ! -f "$NOX_DB_PATH" ]; then
    echo "[R0-KG-GEMINI BATCH $BATCH] ERROR: pre-warmed DB missing at $NOX_DB_PATH"
    exit 1
fi
EXISTING_CHUNKS=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM chunks;" 2>/dev/null || echo 0)
EXISTING_KGE=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM kg_entities;" 2>/dev/null || echo 0)
EXISTING_KGR=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM kg_relations;" 2>/dev/null || echo 0)
echo "[R0-KG-GEMINI BATCH $BATCH] pre-loaded DB chunks=$EXISTING_CHUNKS kg_entities=$EXISTING_KGE kg_relations=$EXISTING_KGR"
if [ "$EXISTING_CHUNKS" -lt 5000 ]; then
    echo "[R0-KG-GEMINI BATCH $BATCH] ERROR: DB not pre-warmed (chunks=$EXISTING_CHUNKS)"
    exit 1
fi
if [ "$EXISTING_KGE" -lt 100 ] || [ "$EXISTING_KGR" -lt 100 ]; then
    echo "[R0-KG-GEMINI BATCH $BATCH] ERROR: KG not populated (kg_entities=$EXISTING_KGE kg_relations=$EXISTING_KGR) — KG path retrieval requires both"
    exit 1
fi

# Cleanup hook
API_PID=""
cleanup() {
    if [ -n "$API_PID" ]; then
        kill "$API_PID" 2>/dev/null || true
        wait "$API_PID" 2>/dev/null || true
        echo "[R0-KG-GEMINI BATCH $BATCH] killed api server pid=$API_PID"
    fi
}
trap cleanup EXIT

echo "[R0-KG-GEMINI BATCH $BATCH] === Step 1: spawn isolated api-server ==="
cd /root/.openclaw/workspace/tools/nox-mem
nohup node --no-warnings dist/api-server.js > "$RUN_DIR/api.log" 2>&1 &
API_PID=$!
echo "[R0-KG-GEMINI BATCH $BATCH] api pid=$API_PID, waiting 5s for boot..."
sleep 5

HEALTH=$(curl -s --max-time 10 "$NOX_API_BASE/api/health" || true)
if ! echo "$HEALTH" | grep -q "\"chunks\""; then
    echo "[R0-KG-GEMINI BATCH $BATCH] ERROR: api not responding"
    echo "$HEALTH" | head -c 300
    exit 1
fi
TOTAL=$(echo "$HEALTH" | python3 -c "import json,sys;d=json.load(sys.stdin);c=d['chunks'];print(c.get('total') if isinstance(c,dict) else c)")
echo "[R0-KG-GEMINI BATCH $BATCH] api health: chunks=$TOTAL"

echo "[R0-KG-GEMINI BATCH $BATCH] === Step 1b: clear stale harness results ==="
RESULTS_DIR="$EVAL/eval/results/nox_mem"
rm -f "$RESULTS_DIR/answer_results_$BATCH.json" "$RESULTS_DIR/evaluation_results_$BATCH.json" "$RESULTS_DIR/search_results_$BATCH.json"
echo "[R0-KG-GEMINI BATCH $BATCH] cleared stale files in $RESULTS_DIR"

echo "[R0-KG-GEMINI BATCH $BATCH] === Step 2: Search + Answer + Evaluate ==="
cd "$EVAL"
python -m eval.cli \
    --dataset "dataset/$BATCH/dialogue.json" \
    --qa "dataset/$BATCH/qa_$BATCH.json" \
    --system nox_mem \
    --user-id "$BATCH" \
    --stages search answer evaluate \
    --top-k 20 \
    > "$RUN_DIR/eval.log" 2>&1

echo "[R0-KG-GEMINI BATCH $BATCH] === Step 3: Analyze ==="
RESULTS_FILE="$RESULTS_DIR/evaluation_results_$BATCH.json"
if [ -f "$RESULTS_FILE" ]; then
    python tools/analyze_results.py "$RESULTS_FILE" > "$RUN_DIR/analysis.txt" 2>&1 || true
    cp "$RESULTS_FILE" "$RUN_DIR/results-batch-$BATCH.json"
    cp "$RESULTS_DIR/answer_results_$BATCH.json" "$RUN_DIR/answer-results-batch-$BATCH.json" 2>/dev/null || true
    cp "$RESULTS_DIR/search_results_$BATCH.json" "$RUN_DIR/search-results-batch-$BATCH.json" 2>/dev/null || true
    echo "[R0-KG-GEMINI BATCH $BATCH] results -> $RUN_DIR/results-batch-$BATCH.json"
else
    echo "[R0-KG-GEMINI BATCH $BATCH] ERROR: no results file at $RESULTS_FILE"
    ls "$RESULTS_DIR" 2>&1 || true
fi

echo "[R0-KG-GEMINI BATCH $BATCH] === DONE ==="
ls -la "$RUN_DIR/"
