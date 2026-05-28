#!/bin/bash
# Phase G 5-batch parallel launcher — mirrors Phase D `run-parallel-phase3.sh`
# but uses MiniLM cross-encoder via run-batch-phaseG.sh.
#
# Each batch:
#   - copies its own Phase B/D winning DB into an isolated RUN_DIR
#   - runs on its own port (18815-18819)
#   - background, captures into RUN_DIR/stream.log
#
# Wait + aggregate after all 5 finish.
#
# Usage:
#   WORK=/tmp/evermembench-phaseG-<id> \
#   bash run-parallel-phaseG.sh
set -uo pipefail

WORK="${WORK:?WORK env var must be set}"
BATCHES=(004 005 010 011 016)
PORTS=(18815 18816 18817 18818 18819)
# Phase B/D winning DBs per batch (copy from Phase B 5-batch run)
declare -A PHASEB_DBS=(
  [004]=/root/.openclaw/evermembench-runs/phaseB-004-1779988559/nox-mem.db
  [005]=/root/.openclaw/evermembench-runs/phaseB-005-1779990311/nox-mem.db
  [010]=/root/.openclaw/evermembench-runs/phaseB-010-1779990316/nox-mem.db
  [011]=/root/.openclaw/evermembench-runs/phaseB-011-1779990322/nox-mem.db
  [016]=/root/.openclaw/evermembench-runs/phaseB-016-1779990327/nox-mem.db
)

PIDS=()
RUN_DIRS=()
for i in "${!BATCHES[@]}"; do
  BATCH="${BATCHES[$i]}"
  PORT="${PORTS[$i]}"
  SRC_DB="${PHASEB_DBS[$BATCH]}"
  if [ ! -f "$SRC_DB" ]; then
    echo "[PARALLEL] WARN: $SRC_DB missing — skipping batch $BATCH"
    continue
  fi
  RUN_DIR="/root/.openclaw/evermembench-runs/phaseG-$BATCH-$(date +%s)"
  mkdir -p "$RUN_DIR"
  cp "$SRC_DB" "$RUN_DIR/nox-mem.db"
  echo "[PARALLEL] launch batch=$BATCH port=$PORT run=$RUN_DIR"
  RUN_DIR="$RUN_DIR" WORK="$WORK" nohup bash "$WORK/run-batch-phaseG.sh" "$BATCH" "$PORT" \
    > "$RUN_DIR/stream.log" 2>&1 &
  PIDS+=($!)
  RUN_DIRS+=("$RUN_DIR")
  # Stagger 2s so api-servers don't race on port-init
  sleep 2
done

echo "[PARALLEL] all 5 launched, waiting..."
for pid in "${PIDS[@]}"; do
  wait "$pid"
  echo "[PARALLEL] pid=$pid exited rc=$?"
done

echo "[PARALLEL] === aggregate ==="
for RUN_DIR in "${RUN_DIRS[@]}"; do
  echo "--- $RUN_DIR ---"
  tail -3 "$RUN_DIR/analysis.txt" 2>/dev/null
done
