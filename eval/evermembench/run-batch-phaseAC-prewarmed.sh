#!/bin/bash
# Phase AC (Lab Q1 #1) — adaptive query classifier 5-batch (pre-warmed batch).
#
# Branches off Phase H v2 (cross-backbone gpt-4.1-mini) and Phase G (MiniLM rerank).
# Per-query the classifier (Option A heuristic, spec PR #373) decides rerank
# ON for multi_hop queries and OFF for factual queries.
#
# Differs from run-batch-phaseH-v2-prewarmed.sh:
#   - NOX_ADAPTER_MODE=phaseAC          (was phaseB)
#   - NOX_ADAPTIVE_CLASSIFIER=1          (NEW — enables classifier gate)
#   - NOX_ADAPTIVE_THRESHOLD=4          (default per spec §2 Option A)
#   - NOX_RERANKER_MODEL set (MiniLM)   (Phase G config; classifier conditionally fires it)
#   - NOX_RERANKER_ENABLED unset        (classifier replaces global gate)
#
# Methodology:
#   - Backbone: gpt-4.1-mini via OpenAI direct
#   - Judge: gemini-2.5-flash
#   - Adapter: phaseAC
#   - top_k=20
#   - Rerank model: cross-encoder/ms-marco-MiniLM-L-6-v2 (Phase G)
#
# Usage (called by run-parallel-phaseAC.sh):
#   WORK=/tmp/phaseAC-5batch-<uuid> \
#   RUN_DIR=/root/.openclaw/evermembench-runs/phaseAC-<batch>-<ts> \
#   bash run-batch-phaseAC-prewarmed.sh <BATCH> <PORT>
#
# Prereqs (caller must satisfy):
#   - $RUN_DIR/nox-mem.db pre-populated from Phase B winning run
#   - $WORK/venv contains harness deps + sentence-transformers (Phase G's venv works)
#   - $WORK/everos/benchmarks/EverMemBench installed
#   - pipeline.yaml already swapped to phaseH v2 config by caller
set -uo pipefail

BATCH="${1:?usage: $0 <BATCH> <PORT>}"
PORT="${2:?usage: $0 <BATCH> <PORT>}"
WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
RUN_DIR="${RUN_DIR:?RUN_DIR env var must be set}"
mkdir -p "$RUN_DIR"
echo "[PHASE-AC BATCH $BATCH PORT $PORT] RUN_DIR=$RUN_DIR"

# Source prod env to get OPENAI_API_KEY + GEMINI_API_KEY
set -a; source /root/.openclaw/.env; set +a

# Activate Phase B venv (has sentence-transformers + harness deps + MiniLM access)
PHASEB_VENV=$(ls -d /root/.openclaw/evermembench-phaseB-*/venv 2>/dev/null | head -1)
if [ -n "$PHASEB_VENV" ]; then
    source "$PHASEB_VENV/bin/activate"
else
    echo "[PHASE-AC BATCH $BATCH] ERROR: no Phase B venv found"
    exit 1
fi
echo "[PHASE-AC] venv python: $(which python)"

# Re-export AFTER source per [[evermembench-eval-gotchas-2026-05-28]]:
# .env carries NOX_RERANKER_MODEL=Xenova/bge-reranker-base which would silently
# override our MiniLM default. Force MiniLM HERE after source.
export NOX_ADAPTER_MODE="phaseAC"
export NOX_ADAPTIVE_CLASSIFIER=1
export NOX_ADAPTIVE_THRESHOLD="${NOX_ADAPTIVE_THRESHOLD:-4}"
export NOX_ADAPTIVE_DEBUG="${NOX_ADAPTIVE_DEBUG:-0}"
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
    echo "[PHASE-AC BATCH $BATCH] ERROR: OPENAI_API_KEY not present in /root/.openclaw/.env"
    exit 1
fi
if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "[PHASE-AC BATCH $BATCH] ERROR: GEMINI_API_KEY not present in /root/.openclaw/.env"
    exit 1
fi
echo "[PHASE-AC BATCH $BATCH] OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}...${OPENAI_API_KEY: -4} (len ${#OPENAI_API_KEY})"

# Live preflight: REAL completion (billing path), NOT just /v1/models list.
echo "[PHASE-AC BATCH $BATCH] === Preflight: gpt-4.1-mini completion (billing path) ==="
PREFLIGHT=$(curl -s --max-time 30 https://api.openai.com/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -d '{"model":"gpt-4.1-mini","messages":[{"role":"user","content":"Reply only OK"}],"max_tokens":5,"temperature":0}')
if ! echo "$PREFLIGHT" | grep -q '"OK"'; then
    echo "[PHASE-AC BATCH $BATCH] ERROR: OpenAI preflight failed (auth OR billing)"
    echo "$PREFLIGHT" | head -c 600
    exit 1
fi
PREFLIGHT_TOKENS=$(echo "$PREFLIGHT" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("usage",{}).get("total_tokens","?"))')
echo "[PHASE-AC BATCH $BATCH] preflight OK (total_tokens=$PREFLIGHT_TOKENS)"

# Isolated DB + isolated port
export NOX_DB_PATH="$RUN_DIR/nox-mem.db"
export NOX_API_PORT="$PORT"
export NOX_API_BASE="http://127.0.0.1:$PORT"
export NOX_MEM_BIN="$(which nox-mem)"

echo "[PHASE-AC BATCH $BATCH] NOX_DB_PATH=$NOX_DB_PATH"
echo "[PHASE-AC BATCH $BATCH] NOX_ADAPTER_MODE=$NOX_ADAPTER_MODE"
echo "[PHASE-AC BATCH $BATCH] NOX_ADAPTIVE_CLASSIFIER=$NOX_ADAPTIVE_CLASSIFIER threshold=$NOX_ADAPTIVE_THRESHOLD"
echo "[PHASE-AC BATCH $BATCH] NOX_RERANKER_MODEL=$NOX_RERANKER_MODEL (will fire conditional on classifier=multi_hop)"

# Verify DB pre-warmed
if [ ! -f "$NOX_DB_PATH" ]; then
    echo "[PHASE-AC BATCH $BATCH] ERROR: pre-warmed DB missing at $NOX_DB_PATH"
    exit 1
fi
EXISTING_CHUNKS=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM chunks;" 2>/dev/null || echo 0)
echo "[PHASE-AC BATCH $BATCH] pre-loaded DB chunks=$EXISTING_CHUNKS"
if [ "$EXISTING_CHUNKS" -lt 5000 ]; then
    echo "[PHASE-AC BATCH $BATCH] ERROR: DB not pre-warmed (chunks=$EXISTING_CHUNKS)"
    exit 1
fi

# Cleanup hook
API_PID=""
cleanup() {
    if [ -n "$API_PID" ]; then
        kill "$API_PID" 2>/dev/null || true
        wait "$API_PID" 2>/dev/null || true
        echo "[PHASE-AC BATCH $BATCH] killed api server pid=$API_PID"
    fi
}
trap cleanup EXIT

echo "[PHASE-AC BATCH $BATCH] === Step 1: spawn isolated api-server ==="
cd /root/.openclaw/workspace/tools/nox-mem
nohup node --no-warnings dist/api-server.js > "$RUN_DIR/api.log" 2>&1 &
API_PID=$!
echo "[PHASE-AC BATCH $BATCH] api pid=$API_PID, waiting 5s for boot..."
sleep 5

HEALTH=$(curl -s --max-time 10 "$NOX_API_BASE/api/health" || true)
if ! echo "$HEALTH" | grep -q "\"chunks\""; then
    echo "[PHASE-AC BATCH $BATCH] ERROR: api not responding"
    echo "$HEALTH" | head -c 300
    exit 1
fi
TOTAL=$(echo "$HEALTH" | python3 -c "import json,sys;d=json.load(sys.stdin);c=d['chunks'];print(c.get('total') if isinstance(c,dict) else c)")
echo "[PHASE-AC BATCH $BATCH] api health: chunks=$TOTAL"

echo "[PHASE-AC BATCH $BATCH] === Step 1b: clear stale harness results (resume short-circuit) ==="
RESULTS_DIR="$EVAL/eval/results/nox_mem"
rm -f "$RESULTS_DIR/answer_results_$BATCH.json" "$RESULTS_DIR/evaluation_results_$BATCH.json" "$RESULTS_DIR/search_results_$BATCH.json"
echo "[PHASE-AC BATCH $BATCH] cleared stale files in $RESULTS_DIR"

echo "[PHASE-AC BATCH $BATCH] === Step 2: Search + Answer + Evaluate ==="
cd "$EVAL"
python -m eval.cli \
    --dataset "dataset/$BATCH/dialogue.json" \
    --qa "dataset/$BATCH/qa_$BATCH.json" \
    --system nox_mem \
    --user-id "$BATCH" \
    --stages search answer evaluate \
    --top-k 20 \
    > "$RUN_DIR/eval.log" 2>&1

echo "[PHASE-AC BATCH $BATCH] === Step 3: Analyze ==="
RESULTS_FILE="$RESULTS_DIR/evaluation_results_$BATCH.json"
if [ -f "$RESULTS_FILE" ]; then
    python tools/analyze_results.py "$RESULTS_FILE" > "$RUN_DIR/analysis.txt" 2>&1 || true
    cp "$RESULTS_FILE" "$RUN_DIR/results-batch-$BATCH.json"
    cp "$RESULTS_DIR/answer_results_$BATCH.json" "$RUN_DIR/answer-results-batch-$BATCH.json" 2>/dev/null || true
    cp "$RESULTS_DIR/search_results_$BATCH.json" "$RUN_DIR/search-results-batch-$BATCH.json" 2>/dev/null || true
    echo "[PHASE-AC BATCH $BATCH] results -> $RUN_DIR/results-batch-$BATCH.json"

    # Audit classifier routing — count multi_hop vs factual decisions
    echo "[PHASE-AC BATCH $BATCH] === Step 4: Routing audit ==="
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
else
    echo "[PHASE-AC BATCH $BATCH] ERROR: no results file at $RESULTS_FILE"
    ls "$RESULTS_DIR" 2>&1 || true
fi

echo "[PHASE-AC BATCH $BATCH] === DONE ==="
ls -la "$RUN_DIR/"
