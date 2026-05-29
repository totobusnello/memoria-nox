#!/bin/bash
# Phase KG (Lab Q1 #4) 5-batch BENCH-ONLY parallel launcher.
# Reuses existing phaseKG-<batch>-<ts>/ run dirs (KG already populated by
# prior kg-extract). Skip kg-extract, only run bench.
#
# Usage: WORK=<work> bash run-parallel-phaseKG-bench-only.sh
set -uo pipefail

WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
PIPELINE_CFG="$EVAL/eval/config/pipeline.yaml"
PIPELINE_BAK="$WORK/pipeline.yaml.bak.bench-only"

# Per-batch config: existing run dirs (most recent per batch)
declare -A RUN_DIRS=(
  [004]=/root/.openclaw/evermembench-runs/phaseKG-004-1780026247
  [005]=/root/.openclaw/evermembench-runs/phaseKG-005-1780026253
  [010]=/root/.openclaw/evermembench-runs/phaseKG-010-1780026258
  [011]=/root/.openclaw/evermembench-runs/phaseKG-011-1780026263
  [016]=/root/.openclaw/evermembench-runs/phaseKG-016-1780026268
)
BATCHES=(004 005 010 011 016)
# Use ports 18835-18839 to avoid conflicts with phaseAC (18830-18831) AND
# any leftover from prior attempt (18825-18829).
PORTS=(18835 18836 18837 18838 18839)

# Swap pipeline.yaml ONCE (in case other agents tweak it; ensures gpt-4.1-mini)
echo "[PARALLEL-KG-BENCH] === installing pipeline.yaml ==="
if [ ! -f "$PIPELINE_CFG" ]; then
    echo "[PARALLEL-KG-BENCH] ERROR: $PIPELINE_CFG missing"
    exit 1
fi
cp "$PIPELINE_CFG" "$PIPELINE_BAK"
cp "$WORK/phaseH-pipeline-v2.yaml" "$PIPELINE_CFG"
echo "[PARALLEL-KG-BENCH] backed up -> $PIPELINE_BAK"

restore_pipeline() {
    if [ -f "$PIPELINE_BAK" ]; then
        cp "$PIPELINE_BAK" "$PIPELINE_CFG"
        echo "[PARALLEL-KG-BENCH] restored original pipeline.yaml"
    fi
}
trap restore_pipeline EXIT

PIDS=()
LAUNCHED=()
for i in "${!BATCHES[@]}"; do
  BATCH="${BATCHES[$i]}"
  PORT="${PORTS[$i]}"
  RUN_DIR="${RUN_DIRS[$BATCH]}"
  if [ ! -f "$RUN_DIR/nox-mem.db" ]; then
    echo "[PARALLEL-KG-BENCH] WARN: $RUN_DIR/nox-mem.db missing — skipping $BATCH"
    continue
  fi
  KGR=$(sqlite3 "$RUN_DIR/nox-mem.db" "SELECT COUNT(*) FROM kg_relations;" 2>/dev/null || echo 0)
  echo "[PARALLEL-KG-BENCH] launch batch=$BATCH port=$PORT run=$RUN_DIR kg_relations=$KGR"
  RUN_DIR="$RUN_DIR" WORK="$WORK" nohup bash "$WORK/run-batch-phaseKG.sh" "$BATCH" "$PORT" \
    > "$RUN_DIR/stream-bench.log" 2>&1 &
  PIDS+=($!)
  LAUNCHED+=("$BATCH")
  sleep 3
done

echo "[PARALLEL-KG-BENCH] all ${#PIDS[@]} launched — waiting..."
RC=0
for idx in "${!PIDS[@]}"; do
  pid="${PIDS[$idx]}"
  wait "$pid"
  rc=$?
  echo "[PARALLEL-KG-BENCH] pid=$pid (batch ${LAUNCHED[$idx]}) exited rc=$rc"
  [ "$rc" -ne 0 ] && RC=1
done

echo "[PARALLEL-KG-BENCH] === aggregate ==="
for BATCH in "${LAUNCHED[@]}"; do
  RUN_DIR="${RUN_DIRS[$BATCH]}"
  echo "--- $RUN_DIR ---"
  tail -5 "$RUN_DIR/analysis.txt" 2>/dev/null || echo "  no analysis.txt"
done
echo "[PARALLEL-KG-BENCH] === DONE (rc=$RC) ==="
exit $RC
