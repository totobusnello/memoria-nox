#!/bin/bash
# Phase Triple (Wave C composability) — KG + MQ + MAP triple-stage 5-batch.
#
# Combines THREE distinct pipeline stages on a single adapter mode:
#   - stage 1 (retrieval expansion): MQ sub-query decomposition + RRF union (PR #385)
#   - stage 2 (retrieval entity-walk): KG 1-hop entity boost (PR #379)
#   - stage 3 (rerank protection): cross-encoder rerank with bypass-entity
#     (PR #366 rerank + PR #386 MAP) extended with KG-evidence anchor (PR #390)
#
# Composability hypothesis (D68 dual finding):
#   - KG+MQ (PR #389): same-stage overlap, 1/4 gates, residual additivity -1.61pp
#     vs perfect additive prediction (90.8% chunk co-fire at retrieval).
#   - KG+MAP (PR #390): different-stage additivity on F_MH, 3/4 gates ship opt-in,
#     observed F_MH +4.04pp ≈ standalone MAP +4.02pp + KG protection at rerank.
#   - Wave C Triple: prediction = MQ-expanded retrieval pool is RICHER than
#     single-query retrieval, so MAP at rerank protects MORE entity-derived
#     chunks. KG/MQ overlap at retrieval is unchanged but MAP layer adds a
#     near-orthogonal rerank-side boost. Triple F_MH ~8.5-9.5pp expected.
#
# Reference patterns:
#   - run-batch-phaseKGMAP.sh (PR #390, KG+MAP triple-minus-MQ)
#   - run-batch-phaseKGMQ.sh (PR #389, KG+MQ triple-minus-MAP)
#
# Lesson refs:
#   - [[reindex-bypasses-openclaw-workspace-hits-main]] → explicit NOX_DB_PATH
#   - [[evermembench-eval-gotchas-2026-05-28]] → fresh harness (purge stale)
#   - [[preflight-must-exercise-billing-path]] → preflight before ingest
#   - [[5-parallel-rerank-api-servers-oom-vps]] → SEQUENTIAL per-batch
#   - [[concurrent-agent-adapter-file-race]] → SEQUENTIAL bench batches
#   - [[empirical-set-e-empty-confirms-mechanism-not-corpus]] → INSTRUMENT
#     ma_set_e_count + ma_set_e_kg_count + ma_total_protected_count
#
# Usage:
#   WORK=/root/.openclaw/wave-C-triple-<id> \
#   RUN_DIR=/root/.openclaw/evermembench-runs/phaseTriple-<batch>-<ts> \
#   PIPELINE_YAML=/path/to/pipeline-phaseH-v2.yaml \
#   bash run-batch-phaseTriple.sh <BATCH> <PORT>
#
# Prereqs:
#   - $RUN_DIR/nox-mem.db present (copy from phaseH-v2 batch dir, 10k+ chunks
#     including kg_entities + kg_relations populated)
#   - $WORK/venv has sentence-transformers + aiohttp + harness deps
#   - $WORK/everos/benchmarks/EverMemBench harness wired with phaseTriple adapter
#   - /root/.openclaw/.env exports OPENAI_API_KEY + GEMINI_API_KEY (MQ LLM)
set -uo pipefail

BATCH="${1:?usage: $0 <BATCH> <PORT>}"
PORT="${2:?usage: $0 <BATCH> <PORT>}"
WORK="${WORK:?WORK env var must be set}"
RUN_DIR="${RUN_DIR:?RUN_DIR env var must be set}"
PIPELINE_YAML="${PIPELINE_YAML:?PIPELINE_YAML env var must be set (path to phaseH v2 yaml)}"

source "$WORK/venv/bin/activate"
EVAL="$WORK/everos/benchmarks/EverMemBench"
LIB_DIR="$WORK/eval-lib"

echo "[PHASETRIPLE BATCH $BATCH PORT $PORT] RUN_DIR=$RUN_DIR"

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

# Phase Triple overrides — must come AFTER .env (which may carry stale defaults)
export NOX_DB_PATH="$RUN_DIR/nox-mem.db"
export NOX_API_PORT="$PORT"
export NOX_API_BASE="http://127.0.0.1:$PORT"

# Adapter mode = Triple (KG + MQ + rerank + MAP + KG-anchor by default)
export NOX_ADAPTER_MODE="phaseTriple"

# Reranker = MiniLM-L-6-v2 (CPU-friendly, Phase G winning config)
export NOX_RERANKER_ENABLED=1
export NOX_RERANKER_MODEL="cross-encoder/ms-marco-MiniLM-L-6-v2"
export NOX_RERANKER_OVERFETCH=50
export NOX_RERANKER_BATCH_SIZE=32

# KG path ON — provides KG entity extraction + evidence chunks for MA anchor
export NOX_KG_PATH_ENABLED=1

# MA-protection ON — bypass-entity protects KG-anchored chunks at rerank
export NOX_MA_PROTECTION_ENABLED=1

# Wave B composability — extend bypass with KG-evidence chunks
export NOX_MA_PROTECTION_KG_ANCHOR=1

# Wave C composability — MQ sub-query decomposition + RRF union (stage 1)
# (uses GEMINI_API_KEY by default — matches DEFAULT_MQ_LLM=gemini-flash-lite)
export NOX_MQ_ENABLED=1

export NOX_MEM_BIN="$(which nox-mem)"

# ── Step 1: verify pre-warmed DB ─────────────────────────────────────────────
EXISTING_CHUNKS=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM chunks;" 2>/dev/null || echo 0)
echo "[PHASETRIPLE] pre-loaded DB chunks=$EXISTING_CHUNKS"
if [ "$EXISTING_CHUNKS" -lt 5000 ]; then
    echo "[PHASETRIPLE] ERROR: DB not pre-warmed (chunks=$EXISTING_CHUNKS, expected >5000)"
    exit 1
fi

# Confirm KG tables present (required for both retrieval boost AND map anchor)
KG_ENTS=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM kg_entities;" 2>/dev/null || echo 0)
KG_RELS=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM kg_relations;" 2>/dev/null || echo 0)
echo "[PHASETRIPLE] KG: entities=$KG_ENTS relations=$KG_RELS"
if [ "$KG_ENTS" -lt 50 ] || [ "$KG_RELS" -lt 50 ]; then
    echo "[PHASETRIPLE] WARN: KG sparse (entities=$KG_ENTS relations=$KG_RELS) — KG boost + anchor may be ineffective"
fi

# ── Step 2: preflight billing path (lesson [[preflight-must-exercise-billing-path]]) ──
echo "[PHASETRIPLE] === preflight billing path (OpenAI gpt-4.1-mini + Gemini judge + MQ LLM) ==="
if [ -f "$LIB_DIR/preflight.sh" ]; then
    source "$LIB_DIR/preflight.sh"
    preflight_billing "https://api.openai.com/v1" "$OPENAI_API_KEY" "gpt-4.1-mini" \
        || { echo "[PHASETRIPLE] ERROR: preflight billing failed for OpenAI (answer)"; exit 1; }
    preflight_billing "https://generativelanguage.googleapis.com/v1beta/openai" \
        "$GEMINI_API_KEY" "gemini-2.5-flash" \
        || { echo "[PHASETRIPLE] ERROR: preflight billing failed for Gemini judge"; exit 1; }
    # MQ LLM is gemini-2.5-flash-lite by default (free tier) — same key as judge,
    # so the Gemini billing check above covers it.
else
    echo "[PHASETRIPLE] WARN: $LIB_DIR/preflight.sh not found — skipping (acceptable for VPS)"
fi

# ── Step 3: cleanup hook ─────────────────────────────────────────────────────
API_PID=""
cleanup() {
    if [ -n "$API_PID" ]; then
        kill "$API_PID" 2>/dev/null || true
        wait "$API_PID" 2>/dev/null || true
        echo "[PHASETRIPLE] killed api server pid=$API_PID"
    fi
}
trap cleanup EXIT

# ── Step 4: spawn isolated nox-mem api-server ────────────────────────────────
echo "[PHASETRIPLE] === spawn isolated api-server on port $PORT ==="
cd $WORK/nox-mem
nohup node --no-warnings dist/api-server.js > "$RUN_DIR/api.log" 2>&1 &
API_PID=$!
echo "[PHASETRIPLE] api pid=$API_PID, waiting 5s for boot..."
sleep 5

HEALTH=$(curl -s --max-time 10 "$NOX_API_BASE/api/health" || true)
if ! echo "$HEALTH" | grep -q "\"chunks\""; then
    echo "[PHASETRIPLE] ERROR: api not responding"
    echo "$HEALTH" | head -c 300
    exit 1
fi
TOTAL=$(echo "$HEALTH" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['chunks']['total'])")
COV=$(echo "$HEALTH" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['vectorCoverage'])")
echo "[PHASETRIPLE] api health: chunks=$TOTAL coverage=$COV"

# ── Step 5: harness_fresh purge + eval.cli ───────────────────────────────────
# Lesson [[evermembench-eval-gotchas-2026-05-28]] — delete answer_results
# + evaluation_results + search_results unconditionally to avoid silent resume.
RESULTS_BASE="$EVAL/eval/results/nox_mem"
for f in answer_results_${BATCH}.json evaluation_results_${BATCH}.json search_results_${BATCH}.json; do
    rm -f "$RESULTS_BASE/$f" && echo "[PHASETRIPLE] purged stale $f"
done

# Replace harness pipeline.yaml with phaseH v2 (gpt-4.1-mini backbone)
HARNESS_PIPELINE="$EVAL/eval/config/pipeline.yaml"
if [ -f "$PIPELINE_YAML" ]; then
    cp "$PIPELINE_YAML" "$HARNESS_PIPELINE"
    echo "[PHASETRIPLE] installed pipeline.yaml = $PIPELINE_YAML"
else
    echo "[PHASETRIPLE] ERROR: PIPELINE_YAML not found at $PIPELINE_YAML"
    exit 1
fi

cd "$EVAL"
echo "[PHASETRIPLE] === Search + Answer + Evaluate ==="
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
echo "[PHASETRIPLE] === Analyze ==="
RESULTS_FILE="$RESULTS_BASE/evaluation_results_$BATCH.json"
SEARCH_FILE="$RESULTS_BASE/search_results_$BATCH.json"

if [ -f "$RESULTS_FILE" ]; then
    python tools/analyze_results.py "$RESULTS_FILE" > "$RUN_DIR/analysis.txt" 2>&1 || true
    # Lesson [[concurrent-agent-results-dir-race]] — write to per-agent scoped path
    cp "$RESULTS_FILE" "$RUN_DIR/wave-C-Triple-${BATCH}.json"
    [ -f "$SEARCH_FILE" ] && cp "$SEARCH_FILE" "$RUN_DIR/search-wave-C-Triple-${BATCH}.json"
    echo "[PHASETRIPLE] results -> $RUN_DIR/wave-C-Triple-${BATCH}.json"
else
    echo "[PHASETRIPLE] ERROR: no results file at $RESULTS_FILE (eval_rc=$EVAL_RC)"
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
    echo "[PHASETRIPLE] search error rate = ${SEARCH_ERR_PCT}%"
    EXCESS=$(python3 -c "print(1 if float('$SEARCH_ERR_PCT') > 5.0 else 0)")
    if [ "$EXCESS" = "1" ]; then
        echo "[PHASETRIPLE] WARN: search error rate >5% — investigate before trusting result"
    fi
fi

# Phase Triple telemetry summary — Set E (section) + Set E (KG) + MQ firing
# per-query stage counts so additivity decomposition has empirical evidence.
if [ -f "$SEARCH_FILE" ]; then
    TRIPLE_STATS=$(python3 - <<PY 2>/dev/null
import json
with open("$SEARCH_FILE") as fp:
    d = json.load(fp)
items = d if isinstance(d, list) else d.get("results", [])

# Stage 1: MQ
mq_status_counter = {}
mq_subqueries_sum = 0
mq_fired_queries = 0

# Stage 2: KG
kg_pool_sum = 0
kg_pool_queries = 0

# Stage 3: MAP
applied_total = 0
kg_anchor_active = 0
set_e_section_sum = 0
set_e_kg_sum = 0
total_protected_sum = 0
queries_with_protection = 0

n = 0
for it in items:
    if not isinstance(it, dict):
        continue
    meta = it.get("metadata") or {}
    n += 1

    # MQ telemetry
    mq_status = meta.get("mq_status", "off")
    mq_status_counter[mq_status] = mq_status_counter.get(mq_status, 0) + 1
    sub_n = int(meta.get("mq_sub_query_count") or 0)
    if sub_n > 0:
        mq_subqueries_sum += sub_n
        mq_fired_queries += 1

    # KG telemetry (pool size = candidates retrieved via 1-hop)
    pool = int(meta.get("kg_neighbor_chunk_pool_size") or meta.get("kg_pool_size") or 0)
    if pool > 0:
        kg_pool_sum += pool
        kg_pool_queries += 1

    # MAP telemetry
    if meta.get("ma_protection_enabled"):
        applied_total += 1 if meta.get("ma_protection_applied") else 0
        if meta.get("ma_protection_kg_anchor"):
            kg_anchor_active += 1
        s_e = int(meta.get("ma_set_e_count") or 0)
        s_kg = int(meta.get("ma_set_e_kg_count") or 0)
        tot = int(meta.get("ma_total_protected_count") or 0)
        set_e_section_sum += s_e
        set_e_kg_sum += s_kg
        total_protected_sum += tot
        if tot > 0:
            queries_with_protection += 1

n_safe = max(n, 1)
print(
    "STAGE1_MQ: "
    f"queries={n} mq_status={dict(sorted(mq_status_counter.items()))} "
    f"mq_subqueries_total={mq_subqueries_sum} mq_fired={mq_fired_queries} "
    f"avg_subqueries_per_q={round(mq_subqueries_sum/n_safe,2)}"
)
print(
    "STAGE2_KG: "
    f"kg_pool_total={kg_pool_sum} kg_pool_queries={kg_pool_queries} "
    f"avg_kg_pool_per_q={round(kg_pool_sum/n_safe,2)}"
)
print(
    "STAGE3_MAP: "
    f"map_applied={applied_total} kg_anchor_active={kg_anchor_active} "
    f"set_e_section_total={set_e_section_sum} set_e_kg_total={set_e_kg_sum} "
    f"total_protected={total_protected_sum} "
    f"queries_with_protection={queries_with_protection} "
    f"avg_protected_per_q={round(total_protected_sum/n_safe,2)}"
)
PY
    )
    echo "[PHASETRIPLE] triple telemetry:"
    echo "$TRIPLE_STATS"
fi

echo "[PHASETRIPLE] === DONE batch=$BATCH ==="
ls -la "$RUN_DIR/"
