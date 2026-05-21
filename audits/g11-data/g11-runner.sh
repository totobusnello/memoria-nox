#!/bin/bash
# G11 ablation runner — trim SOURCE_TYPE_BOOST (entity 2.0->1.3, lesson 1.8->1.2)
# vs current canonical values, all on g9.db with mutex active (default).
#
# Outputs:
#   /root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20/results/G11_baseline_A8.json
#   /root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20/results/G11_trim_A8.json
#
# Restores dist/search.js after run regardless of failure.

set -euo pipefail

EVAL_DIR=/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20
DIST_DIR=/root/.openclaw/workspace/tools/nox-mem/dist
SEARCH_JS=${DIST_DIR}/search.js
BACKUP=/tmp/g11-search.js.original-1779330411
TRIM=/tmp/g11-search.js.trim
HARNESS="python3 ${EVAL_DIR}/entity_ablation_eval.py"
ENDPOINT=http://127.0.0.1:18803/api/search
N=100

source ${EVAL_DIR}/eval-env.sh

mkdir -p ${EVAL_DIR}/results

# Safety: ensure backup matches current dist/search.js before any swap
if ! diff -q "${BACKUP}" "${SEARCH_JS}" >/dev/null 2>&1; then
    echo "FATAL: backup drift — refresh backup before running G11"
    exit 1
fi

cleanup() {
    echo "[cleanup] restoring dist/search.js from backup"
    cp "${BACKUP}" "${SEARCH_JS}"
    tmux kill-session -t g11-api 2>/dev/null || true
}
trap cleanup EXIT

stop_api() {
    tmux kill-session -t g11-api 2>/dev/null || true
    sleep 2
}

start_api() {
    local envs="$1"
    stop_api
    tmux new-session -d -s g11-api "source ${EVAL_DIR}/eval-env.sh; export ${envs}; cd /root/.openclaw/workspace/tools/nox-mem; node dist/api-server.js 2>&1 | tee /tmp/g11-api.log"
    sleep 5
    for i in 1 2 3 4 5 6; do
        if curl -s --max-time 3 http://127.0.0.1:18803/api/health > /tmp/g11-health.json 2>&1; then
            local CHUNKS
            CHUNKS=$(cat /tmp/g11-health.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('chunks',{}).get('total','?'))" 2>/dev/null || echo "?")
            local EMBEDDED
            EMBEDDED=$(cat /tmp/g11-health.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('vectorCoverage',{}).get('embedded','?'))" 2>/dev/null || echo "?")
            echo "  [api up] chunks=$CHUNKS embedded=$EMBEDDED"
            return 0
        fi
        sleep 2
    done
    echo "  WARN: health probe failed after 6 tries — dumping log"
    tail -30 /tmp/g11-api.log
    return 1
}

run_ablation() {
    local label="$1"
    local desc="$2"
    echo "=========================================="
    echo "G11 ablation: $label"
    echo "Desc: $desc"
    echo "=========================================="
    $HARNESS --label "$label" --n $N \
        --fixture-dir "${EVAL_DIR}/" \
        --endpoint "$ENDPOINT" \
        --out "${EVAL_DIR}/results/${label}.json" 2>&1 | tail -15
}

verify_search_js() {
    local tag="$1"
    local entity_val
    entity_val=$(grep -o 'entity: [0-9.]*' "${SEARCH_JS}" | head -1)
    local lesson_val
    lesson_val=$(grep -o 'lesson: [0-9.]*' "${SEARCH_JS}" | head -1)
    echo "[verify ${tag}] ${entity_val} / ${lesson_val}"
}

# ─── G11 BASELINE (current canonical, mutex active, A8 config) ─────────
echo "===== G11_baseline_A8: canonical values (entity=2.0, lesson=1.8), mutex active ====="
verify_search_js "baseline-pre"
start_api "NOX_SALIENCE_MODE=active"
run_ablation G11_baseline_A8 "canonical SOURCE_TYPE_BOOST, mutex ON, salience active"
stop_api

# ─── G11 TRIM (entity=1.3, lesson=1.2, mutex active, A8 config) ────────
echo "===== G11_trim_A8: trim values (entity=1.3, lesson=1.2), mutex active ====="
cp "${TRIM}" "${SEARCH_JS}"
verify_search_js "trim-applied"
start_api "NOX_SALIENCE_MODE=active"
run_ablation G11_trim_A8 "trim SOURCE_TYPE_BOOST, mutex ON, salience active"
stop_api

echo "===== ALL DONE ====="
ls -la ${EVAL_DIR}/results/G11_*
