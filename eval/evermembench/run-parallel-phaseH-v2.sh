#!/bin/bash
# Phase H v2 5-batch parallel launcher — mirrors Phase G `run-parallel-phaseG.sh`
# but routes answer stage via OpenAI direct (gpt-4.1-mini) and judge via Gemini.
#
# Strategy:
#   - Reuses Phase B winning DBs (skip add+vectorize per Phase G pattern)
#   - 4 parallel batches (005/010/011/016); batch 004 already done in PR #372
#   - Ports 18821-18824 (18820 already used by batch 004 single-shot)
#   - Pipeline.yaml swapped ONCE here (avoid 4-way race vs batch-script swap),
#     restored ONCE after all batches complete
#
# Usage:
#   WORK=/tmp/phaseH-v2-5batch-<uuid> bash run-parallel-phaseH-v2.sh
#
# Prereqs:
#   - $WORK/run-batch-phaseH-v2-prewarmed.sh present + executable
#   - $WORK/phaseH-pipeline-v2.yaml present (will be installed as pipeline.yaml)
#   - $WORK/everos/benchmarks/EverMemBench symlinked from existing phaseB install
set -uo pipefail

WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
PIPELINE_CFG="$EVAL/eval/config/pipeline.yaml"
PIPELINE_BAK="$WORK/pipeline.yaml.bak.parallel"

# Per-batch config: ports + source Phase B DB
BATCHES=(005 010 011 016)
PORTS=(18821 18822 18823 18824)
declare -A PHASEB_DBS=(
  [005]=/root/.openclaw/evermembench-runs/phaseB-005-1779990311/nox-mem.db
  [010]=/root/.openclaw/evermembench-runs/phaseB-010-1779990316/nox-mem.db
  [011]=/root/.openclaw/evermembench-runs/phaseB-011-1779990322/nox-mem.db
  [016]=/root/.openclaw/evermembench-runs/phaseB-016-1779990327/nox-mem.db
)

# Swap pipeline.yaml ONCE
echo "[PARALLEL-Hv2] === installing phaseH v2 pipeline.yaml ==="
if [ ! -f "$PIPELINE_CFG" ]; then
    echo "[PARALLEL-Hv2] ERROR: $PIPELINE_CFG missing — harness not installed?"
    exit 1
fi
cp "$PIPELINE_CFG" "$PIPELINE_BAK"
cp "$WORK/phaseH-pipeline-v2.yaml" "$PIPELINE_CFG"
echo "[PARALLEL-Hv2] backed up original -> $PIPELINE_BAK"
echo "[PARALLEL-Hv2] active answer.model = $(grep -A1 '^answer:' $PIPELINE_CFG | tail -1 | tr -d ' ')"

restore_pipeline() {
    if [ -f "$PIPELINE_BAK" ]; then
        cp "$PIPELINE_BAK" "$PIPELINE_CFG"
        echo "[PARALLEL-Hv2] restored original pipeline.yaml"
    fi
}
trap restore_pipeline EXIT

# Fan-out
PIDS=()
RUN_DIRS=()
for i in "${!BATCHES[@]}"; do
  BATCH="${BATCHES[$i]}"
  PORT="${PORTS[$i]}"
  SRC_DB="${PHASEB_DBS[$BATCH]}"
  if [ ! -f "$SRC_DB" ]; then
    echo "[PARALLEL-Hv2] WARN: $SRC_DB missing — skipping batch $BATCH"
    continue
  fi
  RUN_DIR="/root/.openclaw/evermembench-runs/phaseH-v2-$BATCH-$(date +%s)"
  mkdir -p "$RUN_DIR"
  cp "$SRC_DB" "$RUN_DIR/nox-mem.db"
  # If WAL/SHM exist, copy too so SQLite sees consistent state
  [ -f "${SRC_DB}-wal" ] && cp "${SRC_DB}-wal" "$RUN_DIR/nox-mem.db-wal" || true
  [ -f "${SRC_DB}-shm" ] && cp "${SRC_DB}-shm" "$RUN_DIR/nox-mem.db-shm" || true
  echo "[PARALLEL-Hv2] launch batch=$BATCH port=$PORT run=$RUN_DIR"
  RUN_DIR="$RUN_DIR" WORK="$WORK" nohup bash "$WORK/run-batch-phaseH-v2-prewarmed.sh" "$BATCH" "$PORT" \
    > "$RUN_DIR/stream.log" 2>&1 &
  PIDS+=($!)
  RUN_DIRS+=("$RUN_DIR")
  # Stagger 3s so api-servers don't race on port-init
  sleep 3
done

echo "[PARALLEL-Hv2] all ${#PIDS[@]} launched — waiting..."
RC_TOTAL=0
for idx in "${!PIDS[@]}"; do
  pid="${PIDS[$idx]}"
  wait "$pid"
  rc=$?
  echo "[PARALLEL-Hv2] pid=$pid (batch ${BATCHES[$idx]}) exited rc=$rc"
  [ "$rc" -ne 0 ] && RC_TOTAL=1
done

echo "[PARALLEL-Hv2] === aggregate per-batch analysis tails ==="
for RUN_DIR in "${RUN_DIRS[@]}"; do
  echo "--- $RUN_DIR ---"
  tail -5 "$RUN_DIR/analysis.txt" 2>/dev/null || echo "  (no analysis.txt)"
done

echo "[PARALLEL-Hv2] === DONE (rc=$RC_TOTAL) ==="
exit $RC_TOTAL
