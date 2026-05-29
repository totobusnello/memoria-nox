#!/bin/bash
# Phase MAP (Lab Q1 #2) — MA-protection bypass-entity 5-batch.
#
# Reuses Phase H v2 corpus DBs (per-batch pre-warmed, chunks ~10k each) and
# layers cross-encoder rerank + bypass-entity protection on top of the same
# adapter + answer pipeline that produced Phase H v2 baseline (51.68%).
#
# Reference patterns:
#   - run-batch-phaseG.sh (rerank ON, no protection — Phase G control)
#   - pipeline-phaseH-v2.yaml (gpt-4.1-mini backbone + Gemini judge)
#
# Lesson refs:
#   - [[reindex-bypasses-openclaw-workspace-hits-main]] → explicit NOX_DB_PATH
#   - [[evermembench-eval-gotchas-2026-05-28]] → fresh harness (purge stale)
#   - [[preflight-must-exercise-billing-path]] → preflight before ingest
#   - [[5-parallel-rerank-api-servers-oom-vps]] → SEQUENTIAL per-batch
#   - [[search-disconnect-bypasses-classifier-code-path]] → check error rate
#
# Usage:
#   WORK=/tmp/evermembench-phaseMAP-<id> \
#   RUN_DIR=/root/.openclaw/evermembench-runs/phaseMAP-<batch>-<ts> \
#   PIPELINE_YAML=/path/to/pipeline-phaseH-v2.yaml \
#   bash run-batch-phaseMAP.sh <BATCH> <PORT>
#
# Prereqs:
#   - $RUN_DIR/nox-mem.db present (copy from phaseH-v2 batch dir, 10k+ chunks)
#   - $WORK/venv has sentence-transformers + aiohttp + harness deps
#   - $WORK/everos/benchmarks/EverMemBench harness wired with phaseMAP adapter
#   - /root/.openclaw/.env exports OPENAI_API_KEY + GEMINI_API_KEY
set -uo pipefail

BATCH="${1:?usage: $0 <BATCH> <PORT>}"
PORT="${2:?usage: $0 <BATCH> <PORT>}"
WORK="${WORK:?WORK env var must be set}"
RUN_DIR="${RUN_DIR:?RUN_DIR env var must be set}"
PIPELINE_YAML="${PIPELINE_YAML:?PIPELINE_YAML env var must be set (path to phaseH v2 yaml)}"

source "$WORK/venv/bin/activate"
EVAL="$WORK/everos/benchmarks/EverMemBench"
LIB_DIR="$WORK/memoria-nox/eval/lib"

echo "[PHASEMAP BATCH $BATCH PORT $PORT] RUN_DIR=$RUN_DIR"

# ── Step 0: source prod env, THEN re-export overrides (env var ordering matters) ──
set -a
source /root/.openclaw/.env
set +a

# Lesson [[reindex-bypasses-openclaw-workspace-hits-main]]:
# .env override risk → re-export ALL critical vars AFTER source.
export OPENAI_API_KEY="${OPENAI_API_KEY:?OPENAI_API_KEY missing from .env}"
export GEMINI_API_KEY="${GEMINI_API_KEY:?GEMINI_API_KEY missing from .env}"

# Phase MAP overrides — must come AFTER .env (which may carry stale defaults)
export NOX_DB_PATH="$RUN_DIR/nox-mem.db"
export NOX_API_PORT="$PORT"
export NOX_API_BASE="http://127.0.0.1:$PORT"

# Reranker = MiniLM-L-6-v2 (CPU-friendly, Phase G winning config)
export NOX_ADAPTER_MODE="phaseMAP"
export NOX_RERANKER_ENABLED=1
export NOX_RERANKER_MODEL="cross-encoder/ms-marco-MiniLM-L-6-v2"
export NOX_RERANKER_OVERFETCH=50
export NOX_RERANKER_BATCH_SIZE=32

# MA-protection ON — Phase MAP signature flag
export NOX_MA_PROTECTION_ENABLED=1

export NOX_MEM_BIN="$(which nox-mem)"

# ── Step 1: verify pre-warmed DB ─────────────────────────────────────────────
EXISTING_CHUNKS=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM chunks;" 2>/dev/null || echo 0)
echo "[PHASEMAP] pre-loaded DB chunks=$EXISTING_CHUNKS"
if [ "$EXISTING_CHUNKS" -lt 5000 ]; then
    echo "[PHASEMAP] ERROR: DB not pre-warmed (chunks=$EXISTING_CHUNKS, expected >5000)"
    exit 1
fi

# ── Step 2: preflight billing path (lesson [[preflight-must-exercise-billing-path]]) ──
echo "[PHASEMAP] === preflight billing path (OpenAI gpt-4.1-mini) ==="
if [ -f "$LIB_DIR/preflight.sh" ]; then
    source "$LIB_DIR/preflight.sh"
    preflight_billing "https://api.openai.com/v1" "$OPENAI_API_KEY" "gpt-4.1-mini" \
        || { echo "[PHASEMAP] ERROR: preflight billing failed for OpenAI"; exit 1; }
    preflight_billing "https://generativelanguage.googleapis.com/v1beta/openai" \
        "$GEMINI_API_KEY" "gemini-2.5-flash" \
        || { echo "[PHASEMAP] ERROR: preflight billing failed for Gemini judge"; exit 1; }
else
    echo "[PHASEMAP] WARN: $LIB_DIR/preflight.sh not found — skipping (acceptable for VPS)"
fi

# ── Step 3: cleanup hook ─────────────────────────────────────────────────────
API_PID=""
cleanup() {
    if [ -n "$API_PID" ]; then
        kill "$API_PID" 2>/dev/null || true
        wait "$API_PID" 2>/dev/null || true
        echo "[PHASEMAP] killed api server pid=$API_PID"
    fi
}
trap cleanup EXIT

# ── Step 4: spawn isolated nox-mem api-server ────────────────────────────────
echo "[PHASEMAP] === spawn isolated api-server on port $PORT ==="
cd /root/.openclaw/workspace/tools/nox-mem
nohup node --no-warnings dist/api-server.js > "$RUN_DIR/api.log" 2>&1 &
API_PID=$!
echo "[PHASEMAP] api pid=$API_PID, waiting 5s for boot..."
sleep 5

HEALTH=$(curl -s --max-time 10 "$NOX_API_BASE/api/health" || true)
if ! echo "$HEALTH" | grep -q "\"chunks\""; then
    echo "[PHASEMAP] ERROR: api not responding"
    echo "$HEALTH" | head -c 300
    exit 1
fi
TOTAL=$(echo "$HEALTH" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['chunks']['total'])")
COV=$(echo "$HEALTH" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['vectorCoverage'])")
echo "[PHASEMAP] api health: chunks=$TOTAL coverage=$COV"

# ── Step 5: harness_fresh purge + eval.cli ───────────────────────────────────
# Lesson [[evermembench-eval-gotchas-2026-05-28]] — delete answer_results
# + evaluation_results + search_results unconditionally to avoid silent resume.
RESULTS_BASE="$EVAL/eval/results/nox_mem"
for f in answer_results_${BATCH}.json evaluation_results_${BATCH}.json search_results_${BATCH}.json; do
    rm -f "$RESULTS_BASE/$f" && echo "[PHASEMAP] purged stale $f"
done

# Replace harness pipeline.yaml with phaseH v2 (gpt-4.1-mini backbone)
HARNESS_PIPELINE="$EVAL/eval/config/pipeline.yaml"
if [ -f "$PIPELINE_YAML" ]; then
    cp "$PIPELINE_YAML" "$HARNESS_PIPELINE"
    echo "[PHASEMAP] installed pipeline.yaml = $PIPELINE_YAML"
else
    echo "[PHASEMAP] ERROR: PIPELINE_YAML not found at $PIPELINE_YAML"
    exit 1
fi

cd "$EVAL"
echo "[PHASEMAP] === Search + Answer + Evaluate ==="
python -m eval.cli \
    --dataset "dataset/$BATCH/dialogue.json" \
    --qa "dataset/$BATCH/qa_$BATCH.json" \
    --system nox_mem \
    --user-id "$BATCH" \
    --stages search answer evaluate \
    --top-k 20 \
    > "$RUN_DIR/eval.log" 2>&1
EVAL_RC=$?

# ── Step 6: analyze + check search error rate ────────────────────────────────
echo "[PHASEMAP] === Analyze ==="
RESULTS_FILE="$RESULTS_BASE/evaluation_results_$BATCH.json"
SEARCH_FILE="$RESULTS_BASE/search_results_$BATCH.json"

if [ -f "$RESULTS_FILE" ]; then
    python tools/analyze_results.py "$RESULTS_FILE" > "$RUN_DIR/analysis.txt" 2>&1 || true
    cp "$RESULTS_FILE" "$RUN_DIR/results-batch-$BATCH.json"
    [ -f "$SEARCH_FILE" ] && cp "$SEARCH_FILE" "$RUN_DIR/search-batch-$BATCH.json"
    echo "[PHASEMAP] results -> $RUN_DIR/results-batch-$BATCH.json"
else
    echo "[PHASEMAP] ERROR: no results file at $RESULTS_FILE (eval_rc=$EVAL_RC)"
    exit 1
fi

# Search error rate check (lesson [[search-disconnect-bypasses-classifier-code-path]])
if [ -f "$SEARCH_FILE" ]; then
    SEARCH_ERR_PCT=$(python3 - <<PY 2>/dev/null
import json
with open("$SEARCH_FILE") as fp:
    d = json.load(fp)
items = d if isinstance(d, list) else d.get("results", [])
total = len(items)
errs = sum(
    1 for it in items
    if isinstance(it, dict)
    and (
        (it.get("metadata") or {}).get("error")
        or not it.get("retrieved_memories")
    )
)
print(round(100.0 * errs / max(total, 1), 2))
PY
    )
    echo "[PHASEMAP] search error rate = ${SEARCH_ERR_PCT}%"
    # Tolerate up to 5% (some queries genuinely return zero — not a failure)
    EXCESS=$(python3 -c "print(1 if float('$SEARCH_ERR_PCT') > 5.0 else 0)")
    if [ "$EXCESS" = "1" ]; then
        echo "[PHASEMAP] WARN: search error rate >5% — investigate before trusting result"
    fi
fi

# Phase MAP telemetry summary: how many queries actually had entities to protect?
if [ -f "$SEARCH_FILE" ]; then
    MAP_STATS=$(python3 - <<PY 2>/dev/null
import json
with open("$SEARCH_FILE") as fp:
    d = json.load(fp)
items = d if isinstance(d, list) else d.get("results", [])
applied = 0
ent_total = 0
reg_total = 0
n = 0
for it in items:
    if not isinstance(it, dict):
        continue
    meta = it.get("metadata") or {}
    if meta.get("ma_protection_applied"):
        applied += 1
        ent_total += int(meta.get("ma_protection_entity_count") or 0)
        reg_total += int(meta.get("ma_protection_regular_count") or 0)
    n += 1
n = max(n, 1)
print(f"queries={n} map_applied={applied} entity_chunks_total={ent_total} regular_chunks_total={reg_total}")
PY
    )
    echo "[PHASEMAP] MAP telemetry: $MAP_STATS"
fi

echo "[PHASEMAP] === DONE batch=$BATCH ==="
ls -la "$RUN_DIR/"
