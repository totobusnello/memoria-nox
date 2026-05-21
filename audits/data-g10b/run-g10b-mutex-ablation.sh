#!/bin/bash
# G10b — per-category mutex ablation on g9.db
# Compares mutex active (PR #182 default) vs disabled (rollback flag).
set -euo pipefail
EVAL_DIR=/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20
source ${EVAL_DIR}/eval-env.sh
HARNESS="python3 ${EVAL_DIR}/entity_ablation_eval.py"
ENDPOINT=http://127.0.0.1:18803/api/search
N=100
RESULTS=${EVAL_DIR}/results/g10b
mkdir -p $RESULTS

stop_api() {
    tmux kill-session -t g10b-api 2>/dev/null || true
    sleep 2
}

start_api() {
    local envs="$1"
    stop_api
    tmux new-session -d -s g10b-api "source ${EVAL_DIR}/eval-env.sh; export ${envs}; cd /root/.openclaw/workspace/tools/nox-mem; node dist/api-server.js 2>&1 | tee /tmp/g10b-api.log"
    sleep 5
    for i in 1 2 3 4 5 6 7 8; do
        if curl -s --max-time 3 http://127.0.0.1:18803/api/health > /tmp/g10b-health.json 2>&1; then
            CHUNKS=$(python3 -c "import json; d=json.load(open('/tmp/g10b-health.json')); print(d.get('chunks',{}).get('total','?'))" 2>/dev/null || echo "?")
            echo "  [api up] chunks=$CHUNKS env=$envs"
            return 0
        fi
        sleep 2
    done
    echo "  ERROR: health probe failed after 8 tries"
    cat /tmp/g10b-api.log | tail -30
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

# ─── Run 1: A8 canonical with mutex ACTIVE (post PR #182 default) ────
echo "===== Run 1: mutex ACTIVE (default) ====="
start_api "NOX_SALIENCE_MODE=active"
run_eval mutex_active

# ─── Run 2: A8 canonical with mutex DISABLED (rollback flag) ─────────
echo "===== Run 2: mutex DISABLED (NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1) ====="
start_api "NOX_SALIENCE_MODE=active NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1"
run_eval mutex_disabled

# ─── Cleanup ─────────────────────────────────────────────────────────
stop_api
echo "===== ALL DONE ====="
ls -la ${RESULTS}/
