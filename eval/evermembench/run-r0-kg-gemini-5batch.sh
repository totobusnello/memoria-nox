#!/bin/bash
# Wave 2 R0 KG path Gemini-3-flash — 5-batch SEQUENTIAL launcher.
# Mirrors run-phaseIterB-5batch.sh sequential pattern.
#
# Strategy:
#   - Source Phase KG winning DBs (pre-warmed + vectorized + KG-extracted)
#     so we have entities + relations + chunks all ready.
#   - Clone each into $RUN_DIR
#   - Run batches 004, 005, 010, 011, 016 SEQUENTIALLY
#   - Port 18984+ (isolated)
#
# Usage:
#   WORK=/tmp/r0-kg-gemini-<short-uuid> bash run-r0-kg-gemini-5batch.sh
#
# Prereqs:
#   - $WORK/run-batch-r0-kg-gemini.sh present + executable
#   - $WORK/pipeline-backbone-gemini3flash.yaml present
#   - $WORK/everos/benchmarks/EverMemBench symlinked from existing phaseB install
set -uo pipefail

WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
PIPELINE_CFG="$EVAL/eval/config/pipeline.yaml"
PIPELINE_BAK="$WORK/pipeline.yaml.bak.r0-kg-gemini"

# Per-batch config: source Phase KG winning DBs (pre-warmed + vectorized + KG)
BATCHES=(004 005 010 011 016)
PORT=18984

declare -A PHASE_KG_DBS=(
  [004]=/root/.openclaw/evermembench-runs/phaseKG-004-1780026247/nox-mem.db
  [005]=/root/.openclaw/evermembench-runs/phaseKG-005-1780026253/nox-mem.db
  [010]=/root/.openclaw/evermembench-runs/phaseKG-010-1780026258/nox-mem.db
  [011]=/root/.openclaw/evermembench-runs/phaseKG-011-1780026263/nox-mem.db
  [016]=/root/.openclaw/evermembench-runs/phaseKG-016-1780026268/nox-mem.db
)

# Swap pipeline.yaml ONCE to gemini-3-flash backbone config
echo "[SEQ-R0-KG-GEMINI] === installing pipeline.yaml (gemini-3-flash-preview backbone) ==="
if [ ! -f "$PIPELINE_CFG" ]; then
    echo "[SEQ-R0-KG-GEMINI] ERROR: $PIPELINE_CFG missing — harness not installed?"
    exit 1
fi
cp "$PIPELINE_CFG" "$PIPELINE_BAK"
cp "$WORK/pipeline-backbone-gemini3flash.yaml" "$PIPELINE_CFG"
echo "[SEQ-R0-KG-GEMINI] backed up original -> $PIPELINE_BAK"
echo "[SEQ-R0-KG-GEMINI] active answer.model = $(grep -A1 '^answer:' $PIPELINE_CFG | tail -1 | tr -d ' ')"

restore_pipeline() {
    if [ -f "$PIPELINE_BAK" ]; then
        cp "$PIPELINE_BAK" "$PIPELINE_CFG"
        echo "[SEQ-R0-KG-GEMINI] restored original pipeline.yaml"
    fi
}
trap restore_pipeline EXIT

# Run sequentially
RUN_DIRS=()
RC_TOTAL=0
for BATCH in "${BATCHES[@]}"; do
  SRC_DB="${PHASE_KG_DBS[$BATCH]}"
  if [ ! -f "$SRC_DB" ]; then
    echo "[SEQ-R0-KG-GEMINI] WARN: $SRC_DB missing — skipping batch $BATCH"
    continue
  fi
  RUN_DIR="/root/.openclaw/evermembench-runs/r0-kg-gemini-$BATCH-$(date +%s)"
  mkdir -p "$RUN_DIR"
  cp "$SRC_DB" "$RUN_DIR/nox-mem.db"
  [ -f "${SRC_DB}-wal" ] && cp "${SRC_DB}-wal" "$RUN_DIR/nox-mem.db-wal" || true
  [ -f "${SRC_DB}-shm" ] && cp "${SRC_DB}-shm" "$RUN_DIR/nox-mem.db-shm" || true
  echo "[SEQ-R0-KG-GEMINI] === starting batch=$BATCH port=$PORT run=$RUN_DIR ==="
  RUN_DIR="$RUN_DIR" WORK="$WORK" bash "$WORK/run-batch-r0-kg-gemini.sh" "$BATCH" "$PORT" \
    > "$RUN_DIR/stream.log" 2>&1
  rc=$?
  echo "[SEQ-R0-KG-GEMINI] batch=$BATCH exited rc=$rc"
  if [ "$rc" -ne 0 ]; then
    echo "[SEQ-R0-KG-GEMINI] tail of stream.log:"
    tail -30 "$RUN_DIR/stream.log" 2>/dev/null || true
    RC_TOTAL=1
  fi
  RUN_DIRS+=("$RUN_DIR")
done

echo "[SEQ-R0-KG-GEMINI] === aggregate per-batch analysis tails ==="
for RUN_DIR in "${RUN_DIRS[@]}"; do
  echo "--- $RUN_DIR ---"
  tail -8 "$RUN_DIR/analysis.txt" 2>/dev/null || echo "  (no analysis.txt)"
done

echo "[SEQ-R0-KG-GEMINI] === DONE (rc=$RC_TOTAL) ==="
exit $RC_TOTAL
