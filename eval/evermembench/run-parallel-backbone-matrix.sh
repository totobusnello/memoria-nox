#!/bin/bash
# Backbone Matrix bench — 5-batch parallel launcher (2026-05-29).
#
# Mirrors run-parallel-phaseH-v2.sh structure but:
#   - Generic over BACKBONE (1st arg) — gpt-5 / gpt-5-mini / gemini-3-flash-preview
#   - Pipeline.yaml swap: pipeline-backbone-<BACKBONE>.yaml
#   - Run dir naming includes backbone for cross-backbone aggregation
#
# Strategy: 5 batches in parallel (one per port 18830-18834). VPS 16GB cap
# means 2-3 concurrent api-servers; per [[5-parallel-rerank-api-servers-oom-vps]]
# avoid 5-concurrent ON DIFFERENT BACKBONES. WITHIN one backbone, 5-parallel
# Phase H v2 worked (no rerank model loaded).
#
# Usage:
#   WORK=/root/.openclaw/backbone-matrix-<uuid> \
#   BACKBONE=gpt-5-mini \
#   bash run-parallel-backbone-matrix.sh

set -uo pipefail

WORK="${WORK:?WORK env var must be set}"
BACKBONE="${BACKBONE:?BACKBONE env var must be set (gpt-5|gpt-5-mini|gemini-3-flash-preview|gpt-4.1-mini)}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
PIPELINE_CFG="$EVAL/eval/config/pipeline.yaml"
PIPELINE_BAK="$WORK/pipeline.yaml.bak.bb-matrix-$BACKBONE"

# Normalize backbone -> pipeline filename slug
case "$BACKBONE" in
  gpt-5) SLUG=gpt5 ;;
  gpt-5-mini) SLUG=gpt5-mini ;;
  gemini-3-flash-preview) SLUG=gemini3flash ;;
  gemini-3.1-flash-lite-preview) SLUG=gemini31flashlite ;;
  gemini-2.5-pro) SLUG=gemini25pro ;;
  gpt-4.1-mini) SLUG=gpt41mini ;;
  *) echo "[BB-MATRIX] ERROR: unknown BACKBONE=$BACKBONE"; exit 1 ;;
esac

PIPELINE_SRC="$WORK/pipeline-backbone-$SLUG.yaml"
if [ ! -f "$PIPELINE_SRC" ]; then
  echo "[BB-MATRIX] ERROR: pipeline source missing at $PIPELINE_SRC"
  exit 1
fi

# Per-batch config: 5 batches × 1 port each (18830-18834 reserved for backbone matrix)
BATCHES=(004 005 010 011 016)
PORTS=(18830 18831 18832 18833 18834)
declare -A PHASEB_DBS=(
  [004]=/root/.openclaw/evermembench-runs/phaseB-004-1779988559/nox-mem.db
  [005]=/root/.openclaw/evermembench-runs/phaseB-005-1779990311/nox-mem.db
  [010]=/root/.openclaw/evermembench-runs/phaseB-010-1779990316/nox-mem.db
  [011]=/root/.openclaw/evermembench-runs/phaseB-011-1779990322/nox-mem.db
  [016]=/root/.openclaw/evermembench-runs/phaseB-016-1779990327/nox-mem.db
)

# Swap pipeline.yaml ONCE
echo "[BB-MATRIX $BACKBONE] === installing pipeline.yaml (from $PIPELINE_SRC) ==="
if [ ! -f "$PIPELINE_CFG" ]; then
    echo "[BB-MATRIX $BACKBONE] ERROR: $PIPELINE_CFG missing — harness not installed?"
    exit 1
fi
cp "$PIPELINE_CFG" "$PIPELINE_BAK"
cp "$PIPELINE_SRC" "$PIPELINE_CFG"
echo "[BB-MATRIX $BACKBONE] backed up original -> $PIPELINE_BAK"
echo "[BB-MATRIX $BACKBONE] active answer.model = $(grep -A1 '^answer:' $PIPELINE_CFG | tail -1 | tr -d ' ')"

restore_pipeline() {
    if [ -f "$PIPELINE_BAK" ]; then
        cp "$PIPELINE_BAK" "$PIPELINE_CFG"
        echo "[BB-MATRIX $BACKBONE] restored original pipeline.yaml"
    fi
}
trap restore_pipeline EXIT

# Optional: limit to subset via BATCHES_ENV (used for gpt-5 single-batch sample)
if [ -n "${BATCHES_ENV:-}" ]; then
    IFS=',' read -r -a BATCHES <<< "$BATCHES_ENV"
    echo "[BB-MATRIX $BACKBONE] BATCHES_ENV override: ${BATCHES[*]}"
fi

PIDS=()
RUN_DIRS=()
TS=$(date +%s)
for i in "${!BATCHES[@]}"; do
  BATCH="${BATCHES[$i]}"
  PORT="${PORTS[$i]}"
  # Defensive: if BATCHES_ENV truncates, ensure PORT still indexable
  if [ -z "$PORT" ]; then PORT=$((18830 + i)); fi
  SRC_DB="${PHASEB_DBS[$BATCH]}"
  if [ ! -f "$SRC_DB" ]; then
    echo "[BB-MATRIX $BACKBONE] WARN: $SRC_DB missing — skipping batch $BATCH"
    continue
  fi
  RUN_DIR="/root/.openclaw/evermembench-runs/backbone-matrix-$SLUG-$BATCH-$TS"
  mkdir -p "$RUN_DIR"
  cp "$SRC_DB" "$RUN_DIR/nox-mem.db"
  [ -f "${SRC_DB}-wal" ] && cp "${SRC_DB}-wal" "$RUN_DIR/nox-mem.db-wal" || true
  [ -f "${SRC_DB}-shm" ] && cp "${SRC_DB}-shm" "$RUN_DIR/nox-mem.db-shm" || true
  echo "[BB-MATRIX $BACKBONE] launch batch=$BATCH port=$PORT run=$RUN_DIR"
  RUN_DIR="$RUN_DIR" WORK="$WORK" BACKBONE="$BACKBONE" \
    nohup bash "$WORK/run-batch-backbone-matrix.sh" "$BATCH" "$PORT" \
    > "$RUN_DIR/stream.log" 2>&1 &
  PIDS+=($!)
  RUN_DIRS+=("$RUN_DIR")
  # Stagger 3s
  sleep 3
done

echo "[BB-MATRIX $BACKBONE] all ${#PIDS[@]} launched — waiting..."
RC_TOTAL=0
for idx in "${!PIDS[@]}"; do
  pid="${PIDS[$idx]}"
  wait "$pid"
  rc=$?
  echo "[BB-MATRIX $BACKBONE] pid=$pid (batch ${BATCHES[$idx]}) exited rc=$rc"
  [ "$rc" -ne 0 ] && RC_TOTAL=1
done

echo "[BB-MATRIX $BACKBONE] === aggregate per-batch analysis tails ==="
for RUN_DIR in "${RUN_DIRS[@]}"; do
  echo "--- $RUN_DIR ---"
  tail -5 "$RUN_DIR/analysis.txt" 2>/dev/null || echo "  (no analysis.txt)"
done

echo "[BB-MATRIX $BACKBONE] === DONE (rc=$RC_TOTAL) ==="
exit $RC_TOTAL
