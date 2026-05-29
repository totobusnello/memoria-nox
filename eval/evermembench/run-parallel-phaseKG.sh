#!/bin/bash
# Phase KG (Lab Q1 #4) 5-batch parallel launcher.
# Mirrors run-parallel-phaseH-v2.sh but for KG path retrieval Approach A.
#
# Strategy:
#   - Source Phase H v2 winning DBs (already pre-warmed + vectorized)
#   - Clone each into $RUN_DIR, run kg-extract first (BLOCKING, serial-per-batch
#     but parallel across batches), THEN launch bench batch
#   - Ports 18825-18829
#
# Usage:
#   WORK=/tmp/phaseKG-5batch-<uuid> bash run-parallel-phaseKG.sh
#
# Prereqs:
#   - $WORK/run-batch-phaseKG.sh present + executable
#   - $WORK/phaseH-pipeline-v2.yaml present (reused — same model config as Phase H v2)
#   - $WORK/everos/benchmarks/EverMemBench symlinked from existing phaseB install
#   - NOX_KG_EXTRACT_LIMIT env (optional, default 500) — chunks per kg-extract
set -uo pipefail

WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
PIPELINE_CFG="$EVAL/eval/config/pipeline.yaml"
PIPELINE_BAK="$WORK/pipeline.yaml.bak.parallel"
KG_EXTRACT_LIMIT="${NOX_KG_EXTRACT_LIMIT:-500}"

# Per-batch config: ports + source Phase H v2 DB (pre-warmed + vectorized)
BATCHES=(004 005 010 011 016)
PORTS=(18825 18826 18827 18828 18829)
declare -A PHASE_H_DBS=(
  [004]=/root/.openclaw/evermembench-runs/phaseH-v2-004-1780019268/nox-mem.db
  [005]=/root/.openclaw/evermembench-runs/phaseH-v2-005-1780022478/nox-mem.db
  [010]=/root/.openclaw/evermembench-runs/phaseH-v2-010-1780022481/nox-mem.db
  [011]=/root/.openclaw/evermembench-runs/phaseH-v2-011-1780022485/nox-mem.db
  [016]=/root/.openclaw/evermembench-runs/phaseH-v2-016-1780022490/nox-mem.db
)

# Swap pipeline.yaml ONCE
echo "[PARALLEL-KG] === installing pipeline.yaml (gpt-4.1-mini backbone) ==="
if [ ! -f "$PIPELINE_CFG" ]; then
    echo "[PARALLEL-KG] ERROR: $PIPELINE_CFG missing — harness not installed?"
    exit 1
fi
cp "$PIPELINE_CFG" "$PIPELINE_BAK"
cp "$WORK/phaseH-pipeline-v2.yaml" "$PIPELINE_CFG"
echo "[PARALLEL-KG] backed up original -> $PIPELINE_BAK"
echo "[PARALLEL-KG] active answer.model = $(grep -A1 '^answer:' $PIPELINE_CFG | tail -1 | tr -d ' ')"

restore_pipeline() {
    if [ -f "$PIPELINE_BAK" ]; then
        cp "$PIPELINE_BAK" "$PIPELINE_CFG"
        echo "[PARALLEL-KG] restored original pipeline.yaml"
    fi
}
trap restore_pipeline EXIT

# Fan-out
PIDS=()
RUN_DIRS=()
for i in "${!BATCHES[@]}"; do
  BATCH="${BATCHES[$i]}"
  PORT="${PORTS[$i]}"
  SRC_DB="${PHASE_H_DBS[$BATCH]}"
  if [ ! -f "$SRC_DB" ]; then
    echo "[PARALLEL-KG] WARN: $SRC_DB missing — skipping batch $BATCH"
    continue
  fi
  RUN_DIR="/root/.openclaw/evermembench-runs/phaseKG-$BATCH-$(date +%s)"
  mkdir -p "$RUN_DIR"
  cp "$SRC_DB" "$RUN_DIR/nox-mem.db"
  [ -f "${SRC_DB}-wal" ] && cp "${SRC_DB}-wal" "$RUN_DIR/nox-mem.db-wal" || true
  [ -f "${SRC_DB}-shm" ] && cp "${SRC_DB}-shm" "$RUN_DIR/nox-mem.db-shm" || true
  echo "[PARALLEL-KG] launch batch=$BATCH port=$PORT run=$RUN_DIR kg_extract_limit=$KG_EXTRACT_LIMIT"
  RUN_DIR="$RUN_DIR" WORK="$WORK" NOX_KG_EXTRACT_LIMIT="$KG_EXTRACT_LIMIT" \
    nohup bash "$WORK/run-batch-phaseKG-with-kg-extract.sh" "$BATCH" "$PORT" \
    > "$RUN_DIR/stream.log" 2>&1 &
  PIDS+=($!)
  RUN_DIRS+=("$RUN_DIR")
  # Stagger 5s so kg-extract subprocs don't all hit Gemini at the exact same instant
  sleep 5
done

echo "[PARALLEL-KG] all ${#PIDS[@]} launched — waiting..."
RC_TOTAL=0
for idx in "${!PIDS[@]}"; do
  pid="${PIDS[$idx]}"
  wait "$pid"
  rc=$?
  echo "[PARALLEL-KG] pid=$pid (batch ${BATCHES[$idx]}) exited rc=$rc"
  [ "$rc" -ne 0 ] && RC_TOTAL=1
done

echo "[PARALLEL-KG] === aggregate per-batch analysis tails ==="
for RUN_DIR in "${RUN_DIRS[@]}"; do
  echo "--- $RUN_DIR ---"
  tail -5 "$RUN_DIR/analysis.txt" 2>/dev/null || echo "  (no analysis.txt)"
done

echo "[PARALLEL-KG] === DONE (rc=$RC_TOTAL) ==="
exit $RC_TOTAL
