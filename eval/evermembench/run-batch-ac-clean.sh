#!/bin/bash
# Phase AC CLEAN rerun — threshold=5, sequential dispatch (Lab Q1 #1)
#
# Differs from run-batch-phaseAC-prewarmed.sh:
#   - NOX_ADAPTIVE_THRESHOLD=5 (raised from 4 to reduce activation 75%→40-55%)
#   - api-server runs from isolated $WORK/nox-mem (not /root/.openclaw/workspace/tools/nox-mem)
#   - RUN_DIR is auto-created under /root/.openclaw/evermembench-runs/ac-clean-<batch>-<ts>
#   - PORT fixed to 18840 (isolated, sequential — one batch at a time)
#
# Methodology:
#   - Backbone: gpt-4.1-mini via OpenAI direct
#   - Judge: gemini-2.5-flash
#   - Adapter: phaseAC (installed at EverMemBench eval/src/adapters/nox_mem_adapter.py)
#   - top_k=20
#   - Rerank model: cross-encoder/ms-marco-MiniLM-L-6-v2 (Phase G)
#   - Threshold: 5 (clean rerun target)
#
# Usage:
#   bash run-batch-ac-clean.sh <BATCH>

set -uo pipefail

BATCH="${1:?usage: $0 <BATCH>}"
PORT=18840
WORK=/root/.openclaw/lab-q1-1-AC-clean-7f62f006
TS=$(date +%s)
RUN_DIR="/root/.openclaw/evermembench-runs/ac-clean-${BATCH}-${TS}"
EVAL=/root/.openclaw/evermembench-phaseB-1779978778/everos/benchmarks/EverMemBench
mkdir -p "$RUN_DIR"
echo "[AC-CLEAN BATCH $BATCH PORT $PORT] RUN_DIR=$RUN_DIR"

# Source prod env to get OPENAI_API_KEY + GEMINI_API_KEY
set -a; source /root/.openclaw/.env; set +a

# Activate Phase B venv (has sentence-transformers + harness deps + MiniLM access)
PHASEB_VENV=/root/.openclaw/evermembench-phaseB-1779978778/venv
if [ -d "$PHASEB_VENV" ]; then
    source "$PHASEB_VENV/bin/activate"
else
    echo "[AC-CLEAN BATCH $BATCH] ERROR: no Phase B venv found at $PHASEB_VENV"
    exit 1
fi
echo "[AC-CLEAN] venv python: $(which python)"

# Re-export AFTER source per [[evermembench-eval-gotchas-2026-05-28]]:
# .env carries NOX_RERANKER_MODEL=Xenova/bge-reranker-base which would silently
# override our MiniLM default. Force MiniLM HERE after source.
export NOX_ADAPTER_MODE="phaseAC"
export NOX_ADAPTIVE_CLASSIFIER=1
export NOX_ADAPTIVE_THRESHOLD=5
export NOX_ADAPTIVE_DEBUG=1
# Reranker config — model needs to be set so classifier can fire it when
# decision=multi_hop. Don't pin NOX_RERANKER_ENABLED here: the adaptive
# classifier path takes precedence in the adapter when adaptive_enabled=true.
export NOX_RERANKER_MODEL="cross-encoder/ms-marco-MiniLM-L-6-v2"
export NOX_RERANKER_OVERFETCH=50
export NOX_RERANKER_BATCH_SIZE=32
unset NOX_RERANKER_ENABLED || true

# Per-stage routing via pipeline.yaml api_key (gpt-4.1-mini answer, gemini judge)
export LLM_API_KEY="$GEMINI_API_KEY"
export LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"

# Verify both keys are present
if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "[AC-CLEAN BATCH $BATCH] ERROR: OPENAI_API_KEY not present"
    exit 1
fi
if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "[AC-CLEAN BATCH $BATCH] ERROR: GEMINI_API_KEY not present"
    exit 1
fi
echo "[AC-CLEAN BATCH $BATCH] OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}...${OPENAI_API_KEY: -4} (len ${#OPENAI_API_KEY})"

# Live preflight: REAL completion (billing path), NOT just /v1/models list.
echo "[AC-CLEAN BATCH $BATCH] === Preflight: gpt-4.1-mini completion (billing path) ==="
PREFLIGHT=$(curl -s --max-time 30 https://api.openai.com/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -d '{"model":"gpt-4.1-mini","messages":[{"role":"user","content":"Reply only OK"}],"max_tokens":5,"temperature":0}')
if ! echo "$PREFLIGHT" | grep -q '"OK"'; then
    echo "[AC-CLEAN BATCH $BATCH] ERROR: OpenAI preflight failed"
    echo "$PREFLIGHT" | head -c 600
    exit 1
fi
PREFLIGHT_TOKENS=$(echo "$PREFLIGHT" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("usage",{}).get("total_tokens","?"))')
echo "[AC-CLEAN BATCH $BATCH] preflight OK (total_tokens=$PREFLIGHT_TOKENS)"

# Copy pre-warmed DB from prior phaseAC run
PRE_WARMED_DB=$(ls -dt /root/.openclaw/evermembench-runs/phaseAC-${BATCH}-* 2>/dev/null | head -1)/nox-mem.db
if [ ! -f "$PRE_WARMED_DB" ]; then
    echo "[AC-CLEAN BATCH $BATCH] ERROR: no pre-warmed DB at $PRE_WARMED_DB"
    exit 1
fi
cp "$PRE_WARMED_DB" "$RUN_DIR/nox-mem.db"
EXISTING_CHUNKS=$(sqlite3 "$RUN_DIR/nox-mem.db" "SELECT COUNT(*) FROM chunks;" 2>/dev/null || echo 0)
echo "[AC-CLEAN BATCH $BATCH] pre-warmed DB chunks=$EXISTING_CHUNKS (from $PRE_WARMED_DB)"
if [ "$EXISTING_CHUNKS" -lt 5000 ]; then
    echo "[AC-CLEAN BATCH $BATCH] ERROR: DB not pre-warmed (chunks=$EXISTING_CHUNKS)"
    exit 1
fi

# Isolated DB + isolated port
export NOX_DB_PATH="$RUN_DIR/nox-mem.db"
export NOX_API_PORT="$PORT"
export NOX_API_BASE="http://127.0.0.1:$PORT"
export NOX_MEM_BIN="$(which nox-mem)"

echo "[AC-CLEAN BATCH $BATCH] NOX_DB_PATH=$NOX_DB_PATH"
echo "[AC-CLEAN BATCH $BATCH] NOX_ADAPTER_MODE=$NOX_ADAPTER_MODE"
echo "[AC-CLEAN BATCH $BATCH] NOX_ADAPTIVE_CLASSIFIER=$NOX_ADAPTIVE_CLASSIFIER threshold=$NOX_ADAPTIVE_THRESHOLD"
echo "[AC-CLEAN BATCH $BATCH] NOX_RERANKER_MODEL=$NOX_RERANKER_MODEL (will fire conditional on classifier=multi_hop)"

# Cleanup hook
API_PID=""
cleanup() {
    if [ -n "$API_PID" ]; then
        kill "$API_PID" 2>/dev/null || true
        wait "$API_PID" 2>/dev/null || true
        echo "[AC-CLEAN BATCH $BATCH] killed api server pid=$API_PID"
    fi
}
trap cleanup EXIT

# Verify port is free (sequential — should not have prior api on 18840)
EXISTING=$(ss -tlnp 2>/dev/null | grep ":$PORT " || true)
if [ -n "$EXISTING" ]; then
    echo "[AC-CLEAN BATCH $BATCH] WARN: port $PORT in use:"
    echo "$EXISTING"
    # Kill any prior nox-mem-api on 18840
    pkill -f "NOX_API_PORT=$PORT" 2>/dev/null || true
    sleep 3
fi

echo "[AC-CLEAN BATCH $BATCH] === Step 1: spawn isolated api-server (from $WORK/nox-mem) ==="
cd "$WORK/nox-mem"
nohup node --no-warnings dist/api-server.js > "$RUN_DIR/api.log" 2>&1 &
API_PID=$!
echo "[AC-CLEAN BATCH $BATCH] api pid=$API_PID, waiting 8s for boot..."
sleep 8

HEALTH=$(curl -s --max-time 10 "$NOX_API_BASE/api/health" || true)
if ! echo "$HEALTH" | grep -q "\"chunks\""; then
    echo "[AC-CLEAN BATCH $BATCH] ERROR: api not responding"
    echo "$HEALTH" | head -c 300
    echo "--- api.log tail ---"
    tail -50 "$RUN_DIR/api.log"
    exit 1
fi
TOTAL=$(echo "$HEALTH" | python3 -c "import json,sys;d=json.load(sys.stdin);c=d['chunks'];print(c.get('total') if isinstance(c,dict) else c)")
echo "[AC-CLEAN BATCH $BATCH] api health: chunks=$TOTAL"

echo "[AC-CLEAN BATCH $BATCH] === Step 1b: clear stale harness results (resume short-circuit) ==="
RESULTS_DIR="$EVAL/eval/results/nox_mem"
rm -f "$RESULTS_DIR/answer_results_$BATCH.json" "$RESULTS_DIR/evaluation_results_$BATCH.json" "$RESULTS_DIR/search_results_$BATCH.json"
echo "[AC-CLEAN BATCH $BATCH] cleared stale files in $RESULTS_DIR"

echo "[AC-CLEAN BATCH $BATCH] === Step 2: Search + Answer + Evaluate ==="
cd "$EVAL"
python -m eval.cli \
    --dataset "dataset/$BATCH/dialogue.json" \
    --qa "dataset/$BATCH/qa_$BATCH.json" \
    --system nox_mem \
    --user-id "$BATCH" \
    --stages search answer evaluate \
    --top-k 20 \
    > "$RUN_DIR/eval.log" 2>&1

echo "[AC-CLEAN BATCH $BATCH] === Step 3: Analyze ==="
RESULTS_FILE="$RESULTS_DIR/evaluation_results_$BATCH.json"
if [ -f "$RESULTS_FILE" ]; then
    python tools/analyze_results.py "$RESULTS_FILE" > "$RUN_DIR/analysis.txt" 2>&1 || true
    cp "$RESULTS_FILE" "$RUN_DIR/results-batch-$BATCH.json"
    cp "$RESULTS_DIR/answer_results_$BATCH.json" "$RUN_DIR/answer-results-batch-$BATCH.json" 2>/dev/null || true
    cp "$RESULTS_DIR/search_results_$BATCH.json" "$RUN_DIR/search-results-batch-$BATCH.json" 2>/dev/null || true
    echo "[AC-CLEAN BATCH $BATCH] results -> $RUN_DIR/results-batch-$BATCH.json"

    # Audit classifier routing — count multi_hop vs factual decisions
    echo "[AC-CLEAN BATCH $BATCH] === Step 4: Routing audit ==="
    python3 -c "
import json
from pathlib import Path
sf = Path('$RUN_DIR/search-results-batch-$BATCH.json')
if not sf.exists():
    print('  (no search_results to audit)')
else:
    data = json.loads(sf.read_text())
    mh = fa = un = unk = 0
    rerank_applied = rerank_skipped = 0
    items = data if isinstance(data, list) else data.get('results', [])
    for item in items:
        meta = item.get('metadata', {}) if isinstance(item, dict) else {}
        cls = meta.get('classification') or {}
        dec = cls.get('decision')
        if dec == 'multi_hop':
            mh += 1
        elif dec == 'factual':
            fa += 1
        elif cls and not cls.get('available'):
            un += 1
        else:
            unk += 1
        if meta.get('rerank_applied'):
            rerank_applied += 1
        else:
            rerank_skipped += 1
    total = mh + fa + un + unk
    if total == 0:
        print('  no items with classification meta')
    else:
        print(f'  total queries: {total}')
        print(f'  multi_hop: {mh} ({100*mh/total:.1f}%)')
        print(f'  factual:   {fa} ({100*fa/total:.1f}%)')
        print(f'  unavailable: {un}')
        print(f'  unknown:   {unk}')
        print(f'  rerank applied: {rerank_applied}')
        print(f'  rerank skipped: {rerank_skipped}')
" 2>&1 | tee "$RUN_DIR/routing-audit.txt"

    # Search error rate check (lesson [[search-disconnect-bypasses-classifier-code-path]])
    echo "[AC-CLEAN BATCH $BATCH] === Step 5: Search error rate check ==="
    SEARCH_ERRORS=$(grep -cE "search error|HTTP 5|connection reset|connection refused|Read timed out" "$RUN_DIR/api.log" "$RUN_DIR/eval.log" 2>/dev/null | awk -F: '{s+=$2} END {print s+0}')
    TOTAL_QUERIES=$(jq 'length' "$RUN_DIR/answer-results-batch-$BATCH.json" 2>/dev/null || echo 0)
    if [ "$TOTAL_QUERIES" -gt 0 ]; then
        ERROR_RATE=$(python3 -c "print($SEARCH_ERRORS / $TOTAL_QUERIES)")
        printf "[AC-CLEAN BATCH $BATCH] search error count=%s / total queries=%s = %.4f\n" "$SEARCH_ERRORS" "$TOTAL_QUERIES" "$ERROR_RATE" | tee -a "$RUN_DIR/routing-audit.txt"
        ABOVE=$(python3 -c "print(1 if $ERROR_RATE > 0.05 else 0)")
        if [ "$ABOVE" = "1" ]; then
            echo "[AC-CLEAN BATCH $BATCH] WARN: error rate >5% — batch may be contaminated" | tee -a "$RUN_DIR/routing-audit.txt"
        else
            echo "[AC-CLEAN BATCH $BATCH] OK: error rate <=5%" | tee -a "$RUN_DIR/routing-audit.txt"
        fi
    fi
else
    echo "[AC-CLEAN BATCH $BATCH] ERROR: no results file at $RESULTS_FILE"
    ls "$RESULTS_DIR" 2>&1 || true
    exit 1
fi

echo "[AC-CLEAN BATCH $BATCH] === DONE ==="
ls -la "$RUN_DIR/"
