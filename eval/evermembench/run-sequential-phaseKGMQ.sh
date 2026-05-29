#!/bin/bash
# Phase KGMQ (Wave B composability) 5-batch SEQUENTIAL launcher.
# Mirrors run-sequential-phaseMQ.sh shape; runs batches SERIALLY per task
# constraints (LLM decomposer + paralelo Wave B agent on port 18847 mean
# we keep cost surface contained).
#
# Strategy:
#   - Source Phase H v2 winning DBs (pre-warmed + vectorized + KG-extracted)
#   - Clone each into $RUN_DIR
#   - Run batches 004, 005, 010, 011, 016 SEQUENTIALLY
#   - Port 18846 (isolated from paralelo Wave B KG+MAP agent @ 18847)
#
# Usage:
#   WORK=/tmp/wave-B-KG-MQ-<uuid> bash run-sequential-phaseKGMQ.sh
set -uo pipefail

WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
PIPELINE_CFG="$EVAL/eval/config/pipeline.yaml"
PIPELINE_BAK="$WORK/pipeline.yaml.bak.sequential"

BATCHES=(004 005 010 011 016)
PORT=18846

# Source DBs: phaseKG sparse-canonical (PR #379 result baseline). These have
# KG entities + relations pre-extracted so phaseKGMQ KG boost can fire.
# Phase H v2 DBs have chunks+vectors but no KG (KG extract is a separate step).
# Per `[[kg-density-refuted-sparse-canonical]]` we use sparse-canonical, NOT dense.
declare -A PHASE_H_DBS=(
  [004]=/root/.openclaw/evermembench-runs/phaseKG-004-1780026247/nox-mem.db
  [005]=/root/.openclaw/evermembench-runs/phaseKG-005-1780026253/nox-mem.db
  [010]=/root/.openclaw/evermembench-runs/phaseKG-010-1780026258/nox-mem.db
  [011]=/root/.openclaw/evermembench-runs/phaseKG-011-1780026263/nox-mem.db
  [016]=/root/.openclaw/evermembench-runs/phaseKG-016-1780026268/nox-mem.db
)

echo "[SEQ-KGMQ] === installing pipeline.yaml (gpt-4.1-mini backbone) ==="
if [ ! -f "$PIPELINE_CFG" ]; then
    echo "[SEQ-KGMQ] ERROR: $PIPELINE_CFG missing — harness not installed?"
    exit 1
fi
cp "$PIPELINE_CFG" "$PIPELINE_BAK"
cp "$WORK/phaseH-pipeline-v2.yaml" "$PIPELINE_CFG"
echo "[SEQ-KGMQ] backed up original -> $PIPELINE_BAK"
echo "[SEQ-KGMQ] active answer.model = $(grep -A1 '^answer:' $PIPELINE_CFG | tail -1 | tr -d ' ')"

restore_pipeline() {
    if [ -f "$PIPELINE_BAK" ]; then
        cp "$PIPELINE_BAK" "$PIPELINE_CFG"
        echo "[SEQ-KGMQ] restored original pipeline.yaml"
    fi
}
trap restore_pipeline EXIT

# Also install our updated adapter at harness path (CRITICAL: phaseKGMQ mode logic)
ADAPTER_DST="$EVAL/eval/src/adapters/nox_mem_adapter.py"
echo "[SEQ-KGMQ] installing adapter -> $ADAPTER_DST"
cp "$WORK/adapter_nox_mem.py" "$ADAPTER_DST"

RUN_DIRS=()
RC_TOTAL=0
for BATCH in "${BATCHES[@]}"; do
  SRC_DB="${PHASE_H_DBS[$BATCH]}"
  if [ ! -f "$SRC_DB" ]; then
    echo "[SEQ-KGMQ] WARN: $SRC_DB missing — skipping batch $BATCH"
    continue
  fi
  RUN_DIR="/root/.openclaw/evermembench-runs/phaseKGMQ-$BATCH-$(date +%s)"
  mkdir -p "$RUN_DIR"
  cp "$SRC_DB" "$RUN_DIR/nox-mem.db"
  [ -f "${SRC_DB}-wal" ] && cp "${SRC_DB}-wal" "$RUN_DIR/nox-mem.db-wal" || true
  [ -f "${SRC_DB}-shm" ] && cp "${SRC_DB}-shm" "$RUN_DIR/nox-mem.db-shm" || true
  echo "[SEQ-KGMQ] === starting batch=$BATCH port=$PORT run=$RUN_DIR ==="
  RUN_DIR="$RUN_DIR" WORK="$WORK" bash "$WORK/run-batch-phaseKGMQ.sh" "$BATCH" "$PORT" \
    > "$RUN_DIR/stream.log" 2>&1
  rc=$?
  echo "[SEQ-KGMQ] batch=$BATCH exited rc=$rc"
  if [ "$rc" -ne 0 ]; then
    echo "[SEQ-KGMQ] tail of stream.log:"
    tail -30 "$RUN_DIR/stream.log" 2>/dev/null || true
    RC_TOTAL=1
  fi
  RUN_DIRS+=("$RUN_DIR")
done

echo "[SEQ-KGMQ] === aggregate per-batch analysis tails ==="
for RUN_DIR in "${RUN_DIRS[@]}"; do
  echo "--- $RUN_DIR ---"
  tail -10 "$RUN_DIR/analysis.txt" 2>/dev/null || echo "  (no analysis.txt)"
done

echo "[SEQ-KGMQ] === DONE (rc=$RC_TOTAL) ==="
exit $RC_TOTAL
