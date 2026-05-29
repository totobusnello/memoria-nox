#!/bin/bash
# Phase AC re-run Wave 1 only — for batches that failed due to system load
# tail from a previous 5-parallel attempt.
#
# Usage: WORK=/tmp/phaseAC-5batch-<uuid> bash run-parallel-phaseAC-rerun-wave1.sh
#
# This is a stripped-down version of the pair runner that only runs 004 + 005.
# It does NOT re-deploy the adapter (assume the pair runner already deployed it).
# It does NOT swap pipeline.yaml (assume the pair runner already swapped it).
set -uo pipefail

WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"

declare -A PHASEB_DBS=(
  [004]=/root/.openclaw/evermembench-runs/phaseB-004-1779979927/nox-mem.db
  [005]=/root/.openclaw/evermembench-runs/phaseB-005-1779990311/nox-mem.db
)

declare -a BATCHES=(004 005)
declare -a PORTS=(18832 18833)

PIDS=()
RUN_DIRS=()
for i in "${!BATCHES[@]}"; do
  BATCH="${BATCHES[$i]}"
  PORT="${PORTS[$i]}"
  SRC_DB="${PHASEB_DBS[$BATCH]}"
  if [ ! -f "$SRC_DB" ]; then
    echo "[RERUN] WARN: $SRC_DB missing — skipping batch $BATCH"
    continue
  fi
  RUN_DIR="/root/.openclaw/evermembench-runs/phaseAC-$BATCH-$(date +%s)"
  mkdir -p "$RUN_DIR"
  cp "$SRC_DB" "$RUN_DIR/nox-mem.db"
  [ -f "${SRC_DB}-wal" ] && cp "${SRC_DB}-wal" "$RUN_DIR/nox-mem.db-wal" || true
  [ -f "${SRC_DB}-shm" ] && cp "${SRC_DB}-shm" "$RUN_DIR/nox-mem.db-shm" || true
  echo "[RERUN] launch batch=$BATCH port=$PORT run=$RUN_DIR"
  RUN_DIR="$RUN_DIR" WORK="$WORK" nohup bash "$WORK/run-batch-phaseAC-prewarmed.sh" "$BATCH" "$PORT" \
    > "$RUN_DIR/stream.log" 2>&1 &
  PIDS+=($!)
  RUN_DIRS+=("$RUN_DIR")
  sleep 5
done

echo "[RERUN] ${#PIDS[@]} launched — waiting..."
RC_TOTAL=0
for idx in "${!PIDS[@]}"; do
    pid="${PIDS[$idx]}"
    wait "$pid"
    rc=$?
    echo "[RERUN] pid=$pid (batch ${BATCHES[$idx]}) exited rc=$rc"
    [ "$rc" -ne 0 ] && RC_TOTAL=1
done

for RUN_DIR in "${RUN_DIRS[@]}"; do
    echo "--- $RUN_DIR ---"
    tail -5 "$RUN_DIR/analysis.txt" 2>/dev/null || echo "  (no analysis.txt)"
    cat "$RUN_DIR/routing-audit.txt" 2>/dev/null || true
done

echo "[RERUN] === DONE (rc=$RC_TOTAL) ==="
exit $RC_TOTAL
