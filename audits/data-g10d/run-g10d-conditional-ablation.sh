#!/bin/bash
# G10d Conditional Hard Mutex ablation — 4 configs on g9.db
set -euo pipefail
EVAL_DIR=/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20
ISO_DIR=/root/.openclaw/workspace/tools/nox-mem-isolated
# Source env for harness (NOX_EVAL_DB_PATH check)
source ${EVAL_DIR}/eval-env.sh
HARNESS="python3 ${EVAL_DIR}/entity_ablation_eval.py"
ENDPOINT=http://127.0.0.1:18803/api/search
N=100
RESULTS=${EVAL_DIR}/results/g10d
mkdir -p $RESULTS

stop_api() {
    tmux kill-session -t g10d-api 2>/dev/null || true
    sleep 2
}

start_api() {
    local envs="$1"
    stop_api
    tmux new-session -d -s g10d-api "source ${EVAL_DIR}/eval-env.sh; export ${envs}; cd ${ISO_DIR}; node dist/api-server.js 2>&1 | tee /tmp/g10d-api.log"
    sleep 5
    for i in 1 2 3 4 5 6 7 8; do
        if curl -s --max-time 3 http://127.0.0.1:18803/api/health > /tmp/g10d-health.json 2>&1; then
            CHUNKS=$(python3 -c "import json; d=json.load(open('/tmp/g10d-health.json')); print(d.get('chunks',{}).get('total','?'))" 2>/dev/null || echo "?")
            echo "  [api up] chunks=$CHUNKS env=$envs"
            return 0
        fi
        sleep 2
    done
    echo "  ERROR: health probe failed after 8 tries"
    cat /tmp/g10d-api.log | tail -30
    return 1
}

run_eval() {
    local label="$1"
    echo "=========================================="
    echo "Running: $label"
    echo "=========================================="
    $HARNESS --label "$label" --n $N \
        --fixture-dir "${EVAL_DIR}/" \
        --endpoint "$ENDPOINT" \
        --out "${RESULTS}/${label}.json" 2>&1 | tail -15
}

echo "===== Run 1: A8' baseline (mutex ACTIVE always, G10 prod default) ====="
start_api "NOX_SALIENCE_MODE=active NOX_DISABLE_CONDITIONAL_MUTEX=1"
run_eval a8_prime_baseline

echo "===== Run 2: A8d-1 (conditional threshold=1) ====="
start_api "NOX_SALIENCE_MODE=active NOX_MUTEX_QUERY_ENTITY_THRESHOLD=1"
run_eval a8d_t1

echo "===== Run 3: A8d-2 (conditional threshold=2) ====="
start_api "NOX_SALIENCE_MODE=active NOX_MUTEX_QUERY_ENTITY_THRESHOLD=2"
run_eval a8d_t2

echo "===== Run 4: A8' off (mutex fully DISABLED — control) ====="
start_api "NOX_SALIENCE_MODE=active NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1"
run_eval a8_off_control

stop_api
echo "===== ALL DONE ====="
ls -la ${RESULTS}/
