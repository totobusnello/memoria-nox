#!/bin/bash
# Phase KGMAP (Wave B composability) — KG-anchored MA-protection 5-batch.
#
# Combines:
#   - Phase F cross-encoder rerank (PR #366)
#   - Phase KG 1-hop entity boost (PR #379)
#   - Phase MAP bypass-entity (PR #386)
#   - NEW Wave B: bypass extends to KG-evidence chunks for query entities
#     → fires on chat-only corpora where pure section-based bypass was empty
#
# Reference patterns:
#   - run-batch-phaseMAP.sh (PR #386, MAP standalone)
#   - run-batch-phaseKG.sh (PR #379, KG standalone)
#
# Lesson refs:
#   - [[reindex-bypasses-openclaw-workspace-hits-main]] → explicit NOX_DB_PATH
#   - [[evermembench-eval-gotchas-2026-05-28]] → fresh harness (purge stale)
#   - [[preflight-must-exercise-billing-path]] → preflight before ingest
#   - [[5-parallel-rerank-api-servers-oom-vps]] → SEQUENTIAL per-batch
#   - [[empirical-set-e-empty-confirms-mechanism-not-corpus]] → INSTRUMENT
#     ma_set_e_count + ma_set_e_kg_count + ma_total_protected_count
#
# Usage:
#   WORK=/root/.openclaw/wave-B-KGMAP-<id> \
#   RUN_DIR=/root/.openclaw/evermembench-runs/phaseKGMAP-<batch>-<ts> \
#   PIPELINE_YAML=/path/to/pipeline-phaseH-v2.yaml \
#   bash run-batch-phaseKGMAP.sh <BATCH> <PORT>
#
# Prereqs:
#   - $RUN_DIR/nox-mem.db present (copy from phaseH-v2 batch dir, 10k+ chunks
#     including kg_entities + kg_relations populated)
#   - $WORK/venv has sentence-transformers + aiohttp + harness deps
#   - $WORK/everos/benchmarks/EverMemBench harness wired with phaseKGMAP adapter
#   - /root/.openclaw/.env exports OPENAI_API_KEY + GEMINI_API_KEY
set -uo pipefail

BATCH="${1:?usage: $0 <BATCH> <PORT>}"
PORT="${2:?usage: $0 <BATCH> <PORT>}"
WORK="${WORK:?WORK env var must be set}"
RUN_DIR="${RUN_DIR:?RUN_DIR env var must be set}"
PIPELINE_YAML="${PIPELINE_YAML:?PIPELINE_YAML env var must be set (path to phaseH v2 yaml)}"

source "$WORK/venv/bin/activate"
EVAL="$WORK/everos/benchmarks/EverMemBench"
LIB_DIR="$WORK/eval-lib"

echo "[PHASEKGMAP BATCH $BATCH PORT $PORT] RUN_DIR=$RUN_DIR"

# ── Step 0: source prod env, THEN re-export overrides (env var ordering matters) ──
set -a
source /root/.openclaw/.env
set +a

# Lesson [[reindex-bypasses-openclaw-workspace-hits-main]]:
# .env override risk → re-export ALL critical vars AFTER source.
export OPENAI_API_KEY="${OPENAI_API_KEY:?OPENAI_API_KEY missing from .env}"

# Harness top-level needs LLM_API_KEY even when pipeline.yaml has per-block keys.
# Use Gemini key (judge stage) — answer stage overrides via api_key in pipeline.
export LLM_API_KEY="$GEMINI_API_KEY"
export LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
export GEMINI_API_KEY="${GEMINI_API_KEY:?GEMINI_API_KEY missing from .env}"

# Phase KGMAP overrides — must come AFTER .env (which may carry stale defaults)
export NOX_DB_PATH="$RUN_DIR/nox-mem.db"
export NOX_API_PORT="$PORT"
export NOX_API_BASE="http://127.0.0.1:$PORT"

# Reranker = MiniLM-L-6-v2 (CPU-friendly, Phase G winning config)
export NOX_ADAPTER_MODE="phaseKGMAP"
export NOX_RERANKER_ENABLED=1
export NOX_RERANKER_MODEL="cross-encoder/ms-marco-MiniLM-L-6-v2"
export NOX_RERANKER_OVERFETCH=50
export NOX_RERANKER_BATCH_SIZE=32

# KG path ON — provides KG entity extraction + evidence chunks for MA anchor
export NOX_KG_PATH_ENABLED=1

# MA-protection ON — Phase MAP signature flag
export NOX_MA_PROTECTION_ENABLED=1

# Wave B composability — extend bypass with KG-evidence chunks
export NOX_MA_PROTECTION_KG_ANCHOR=1

export NOX_MEM_BIN="$(which nox-mem)"

# ── Step 1: verify pre-warmed DB ─────────────────────────────────────────────
EXISTING_CHUNKS=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM chunks;" 2>/dev/null || echo 0)
echo "[PHASEKGMAP] pre-loaded DB chunks=$EXISTING_CHUNKS"
if [ "$EXISTING_CHUNKS" -lt 5000 ]; then
    echo "[PHASEKGMAP] ERROR: DB not pre-warmed (chunks=$EXISTING_CHUNKS, expected >5000)"
    exit 1
fi

# Confirm KG tables present
KG_ENTS=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM kg_entities;" 2>/dev/null || echo 0)
KG_RELS=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM kg_relations;" 2>/dev/null || echo 0)
echo "[PHASEKGMAP] KG: entities=$KG_ENTS relations=$KG_RELS"
if [ "$KG_ENTS" -lt 50 ] || [ "$KG_RELS" -lt 50 ]; then
    echo "[PHASEKGMAP] WARN: KG sparse (entities=$KG_ENTS relations=$KG_RELS) — KG anchor may be ineffective"
fi

# ── Step 2: preflight billing path (lesson [[preflight-must-exercise-billing-path]]) ──
echo "[PHASEKGMAP] === preflight billing path (OpenAI gpt-4.1-mini) ==="
if [ -f "$LIB_DIR/preflight.sh" ]; then
    source "$LIB_DIR/preflight.sh"
    preflight_billing "https://api.openai.com/v1" "$OPENAI_API_KEY" "gpt-4.1-mini" \
        || { echo "[PHASEKGMAP] ERROR: preflight billing failed for OpenAI"; exit 1; }
    preflight_billing "https://generativelanguage.googleapis.com/v1beta/openai" \
        "$GEMINI_API_KEY" "gemini-2.5-flash" \
        || { echo "[PHASEKGMAP] ERROR: preflight billing failed for Gemini judge"; exit 1; }
else
    echo "[PHASEKGMAP] WARN: $LIB_DIR/preflight.sh not found — skipping (acceptable for VPS)"
fi

# ── Step 3: cleanup hook ─────────────────────────────────────────────────────
API_PID=""
cleanup() {
    if [ -n "$API_PID" ]; then
        kill "$API_PID" 2>/dev/null || true
        wait "$API_PID" 2>/dev/null || true
        echo "[PHASEKGMAP] killed api server pid=$API_PID"
    fi
}
trap cleanup EXIT

# ── Step 4: spawn isolated nox-mem api-server ────────────────────────────────
echo "[PHASEKGMAP] === spawn isolated api-server on port $PORT ==="
cd $WORK/nox-mem
nohup node --no-warnings dist/api-server.js > "$RUN_DIR/api.log" 2>&1 &
API_PID=$!
echo "[PHASEKGMAP] api pid=$API_PID, waiting 5s for boot..."
sleep 5

HEALTH=$(curl -s --max-time 10 "$NOX_API_BASE/api/health" || true)
if ! echo "$HEALTH" | grep -q "\"chunks\""; then
    echo "[PHASEKGMAP] ERROR: api not responding"
    echo "$HEALTH" | head -c 300
    exit 1
fi
TOTAL=$(echo "$HEALTH" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['chunks']['total'])")
COV=$(echo "$HEALTH" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['vectorCoverage'])")
echo "[PHASEKGMAP] api health: chunks=$TOTAL coverage=$COV"

# ── Step 5: harness_fresh purge + eval.cli ───────────────────────────────────
# Lesson [[evermembench-eval-gotchas-2026-05-28]] — delete answer_results
# + evaluation_results + search_results unconditionally to avoid silent resume.
RESULTS_BASE="$EVAL/eval/results/nox_mem"
for f in answer_results_${BATCH}.json evaluation_results_${BATCH}.json search_results_${BATCH}.json; do
    rm -f "$RESULTS_BASE/$f" && echo "[PHASEKGMAP] purged stale $f"
done

# Replace harness pipeline.yaml with phaseH v2 (gpt-4.1-mini backbone)
HARNESS_PIPELINE="$EVAL/eval/config/pipeline.yaml"
if [ -f "$PIPELINE_YAML" ]; then
    cp "$PIPELINE_YAML" "$HARNESS_PIPELINE"
    echo "[PHASEKGMAP] installed pipeline.yaml = $PIPELINE_YAML"
else
    echo "[PHASEKGMAP] ERROR: PIPELINE_YAML not found at $PIPELINE_YAML"
    exit 1
fi

cd "$EVAL"
echo "[PHASEKGMAP] === Search + Answer + Evaluate ==="
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
echo "[PHASEKGMAP] === Analyze ==="
RESULTS_FILE="$RESULTS_BASE/evaluation_results_$BATCH.json"
SEARCH_FILE="$RESULTS_BASE/search_results_$BATCH.json"

if [ -f "$RESULTS_FILE" ]; then
    python tools/analyze_results.py "$RESULTS_FILE" > "$RUN_DIR/analysis.txt" 2>&1 || true
    # Lesson [[concurrent-agent-results-dir-race]] — write to per-agent scoped path
    cp "$RESULTS_FILE" "$RUN_DIR/wave-B-KGMAP-${BATCH}.json"
    [ -f "$SEARCH_FILE" ] && cp "$SEARCH_FILE" "$RUN_DIR/search-wave-B-KGMAP-${BATCH}.json"
    echo "[PHASEKGMAP] results -> $RUN_DIR/wave-B-KGMAP-${BATCH}.json"
else
    echo "[PHASEKGMAP] ERROR: no results file at $RESULTS_FILE (eval_rc=$EVAL_RC)"
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
    echo "[PHASEKGMAP] search error rate = ${SEARCH_ERR_PCT}%"
    EXCESS=$(python3 -c "print(1 if float('$SEARCH_ERR_PCT') > 5.0 else 0)")
    if [ "$EXCESS" = "1" ]; then
        echo "[PHASEKGMAP] WARN: search error rate >5% — investigate before trusting result"
    fi
fi

# Phase KGMAP telemetry summary — Set E (section) + Set E (KG) + total protected
# Lesson [[empirical-set-e-empty-confirms-mechanism-not-corpus]] — these counts
# are THE evidence of mechanism firing. If ALL zero, KG anchor was inert on
# this corpus and we report a clean diagnose.
if [ -f "$SEARCH_FILE" ]; then
    KGMAP_STATS=$(python3 - <<PY 2>/dev/null
import json
with open("$SEARCH_FILE") as fp:
    d = json.load(fp)
items = d if isinstance(d, list) else d.get("results", [])
applied_total = 0
kg_anchor_active = 0
set_e_section_sum = 0
set_e_kg_sum = 0
total_protected_sum = 0
kg_pool_sum = 0
queries_with_protection = 0
queries_with_kg_pool = 0
n = 0
for it in items:
    if not isinstance(it, dict):
        continue
    meta = it.get("metadata") or {}
    n += 1
    if meta.get("ma_protection_enabled"):
        applied_total += 1 if meta.get("ma_protection_applied") else 0
        if meta.get("ma_protection_kg_anchor"):
            kg_anchor_active += 1
        s_e = int(meta.get("ma_set_e_count") or 0)
        s_kg = int(meta.get("ma_set_e_kg_count") or 0)
        tot = int(meta.get("ma_total_protected_count") or 0)
        pool = int(meta.get("ma_kg_evidence_pool_size") or 0)
        set_e_section_sum += s_e
        set_e_kg_sum += s_kg
        total_protected_sum += tot
        kg_pool_sum += pool
        if tot > 0:
            queries_with_protection += 1
        if pool > 0:
            queries_with_kg_pool += 1
n_safe = max(n, 1)
print(
    f"queries={n} kgmap_applied={applied_total} kg_anchor_active={kg_anchor_active} "
    f"set_e_section_total={set_e_section_sum} set_e_kg_total={set_e_kg_sum} "
    f"total_protected={total_protected_sum} kg_pool_total={kg_pool_sum} "
    f"queries_with_protection={queries_with_protection} "
    f"queries_with_kg_pool={queries_with_kg_pool} "
    f"avg_protected_per_q={round(total_protected_sum/n_safe,2)} "
    f"avg_kg_pool_per_q={round(kg_pool_sum/n_safe,2)}"
)
PY
    )
    echo "[PHASEKGMAP] KGMAP telemetry: $KGMAP_STATS"
fi

echo "[PHASEKGMAP] === DONE batch=$BATCH ==="
ls -la "$RUN_DIR/"
