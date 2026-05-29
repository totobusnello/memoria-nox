#!/bin/bash
# Phase MQ (Lab Q1 #3) 5-batch SEQUENTIAL launcher.
# Mirrors run-parallel-phaseH-v2.sh shape but runs batches SERIALLY per task
# constraints — conservative (LLM decomposer adds shared cost surface; no
# parallel agents in this experiment).
#
# Strategy:
#   - Source Phase H v2 winning DBs (pre-warmed + vectorized)
#   - Clone each into $RUN_DIR
#   - Run batches 004, 005, 010, 011, 016 SEQUENTIALLY
#   - Port 18842 (isolated from MAP @ 18841, KG-dense @ 18843)
#
# Usage:
#   WORK=/tmp/phaseMQ-5batch-<uuid> bash run-sequential-phaseMQ.sh
#
# Prereqs:
#   - $WORK/run-batch-phaseMQ.sh present + executable
#   - $WORK/phaseH-pipeline-v2.yaml present (reused gpt-4.1-mini config)
#   - $WORK/everos/benchmarks/EverMemBench symlinked from existing phaseB install
set -uo pipefail

WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
PIPELINE_CFG="$EVAL/eval/config/pipeline.yaml"
PIPELINE_BAK="$WORK/pipeline.yaml.bak.sequential"

# Per-batch config: source Phase H v2 DBs (pre-warmed + vectorized)
BATCHES=(004 005 010 011 016)
PORT=18842

declare -A PHASE_H_DBS=(
  [004]=/root/.openclaw/evermembench-runs/phaseH-v2-004-1780019268/nox-mem.db
  [005]=/root/.openclaw/evermembench-runs/phaseH-v2-005-1780022478/nox-mem.db
  [010]=/root/.openclaw/evermembench-runs/phaseH-v2-010-1780022481/nox-mem.db
  [011]=/root/.openclaw/evermembench-runs/phaseH-v2-011-1780022485/nox-mem.db
  [016]=/root/.openclaw/evermembench-runs/phaseH-v2-016-1780022490/nox-mem.db
)

# Swap pipeline.yaml ONCE
echo "[SEQ-MQ] === installing pipeline.yaml (gpt-4.1-mini backbone) ==="
if [ ! -f "$PIPELINE_CFG" ]; then
    echo "[SEQ-MQ] ERROR: $PIPELINE_CFG missing — harness not installed?"
    exit 1
fi
cp "$PIPELINE_CFG" "$PIPELINE_BAK"
cp "$WORK/phaseH-pipeline-v2.yaml" "$PIPELINE_CFG"
echo "[SEQ-MQ] backed up original -> $PIPELINE_BAK"
echo "[SEQ-MQ] active answer.model = $(grep -A1 '^answer:' $PIPELINE_CFG | tail -1 | tr -d ' ')"

restore_pipeline() {
    if [ -f "$PIPELINE_BAK" ]; then
        cp "$PIPELINE_BAK" "$PIPELINE_CFG"
        echo "[SEQ-MQ] restored original pipeline.yaml"
    fi
}
trap restore_pipeline EXIT

# Run sequentially
RUN_DIRS=()
RC_TOTAL=0
for BATCH in "${BATCHES[@]}"; do
  SRC_DB="${PHASE_H_DBS[$BATCH]}"
  if [ ! -f "$SRC_DB" ]; then
    echo "[SEQ-MQ] WARN: $SRC_DB missing — skipping batch $BATCH"
    continue
  fi
  RUN_DIR="/root/.openclaw/evermembench-runs/phaseMQ-$BATCH-$(date +%s)"
  mkdir -p "$RUN_DIR"
  cp "$SRC_DB" "$RUN_DIR/nox-mem.db"
  [ -f "${SRC_DB}-wal" ] && cp "${SRC_DB}-wal" "$RUN_DIR/nox-mem.db-wal" || true
  [ -f "${SRC_DB}-shm" ] && cp "${SRC_DB}-shm" "$RUN_DIR/nox-mem.db-shm" || true
  echo "[SEQ-MQ] === starting batch=$BATCH port=$PORT run=$RUN_DIR ==="
  RUN_DIR="$RUN_DIR" WORK="$WORK" bash "$WORK/run-batch-phaseMQ.sh" "$BATCH" "$PORT" \
    > "$RUN_DIR/stream.log" 2>&1
  rc=$?
  echo "[SEQ-MQ] batch=$BATCH exited rc=$rc"
  if [ "$rc" -ne 0 ]; then
    echo "[SEQ-MQ] tail of stream.log:"
    tail -30 "$RUN_DIR/stream.log" 2>/dev/null || true
    RC_TOTAL=1
  fi
  RUN_DIRS+=("$RUN_DIR")
done

echo "[SEQ-MQ] === aggregate per-batch analysis tails ==="
for RUN_DIR in "${RUN_DIRS[@]}"; do
  echo "--- $RUN_DIR ---"
  tail -5 "$RUN_DIR/analysis.txt" 2>/dev/null || echo "  (no analysis.txt)"
done

echo "[SEQ-MQ] === DONE (rc=$RC_TOTAL) ==="
exit $RC_TOTAL
