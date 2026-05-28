#!/bin/bash
# Phase 3 — launch batches 005, 010, 011, 016 in parallel with Phase D variant
# (top-k=20, NOX_ADAPTER_MODE=phaseB).
#
# Usage:
#   WORK=/root/.openclaw/evermembench-phaseB-1779978778 ./run-parallel-phase3.sh
#
# Each batch:
#   - Has its own RUN_DIR + isolated DB
#   - Uses a unique port (18811-18814)
#   - Activates venv before subprocess invocation
set -uo pipefail

WORK="${WORK:?must set WORK env}"
declare -A PORTS=( [005]=18811 [010]=18812 [011]=18813 [016]=18814 )

LOGFILE_BASE="/tmp/phase3-parallel"
PIDS=()
for BATCH in 005 010 011 016; do
    PORT="${PORTS[$BATCH]}"
    LOG="${LOGFILE_BASE}-${BATCH}.log"
    echo "[phase3] launching batch $BATCH on port $PORT, log=$LOG"
    # Run launcher that activates venv first, then invokes phaseD script
    nohup bash -c "
        export WORK=$WORK
        export NOX_ADAPTER_MODE=phaseB
        cd \$WORK
        source \$WORK/venv/bin/activate
        bash \$WORK/run-batch-phaseD.sh $BATCH $PORT
    " > "$LOG" 2>&1 &
    PIDS+=($!)
    sleep 5   # tiny stagger to avoid spawn races
done

echo "[phase3] launched PIDs: ${PIDS[@]}"
echo "${PIDS[@]}" > /tmp/phase3-pids.txt
echo "[phase3] PIDs logged to /tmp/phase3-pids.txt"
