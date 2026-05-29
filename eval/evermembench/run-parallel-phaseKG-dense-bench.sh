#!/bin/bash
# Phase KG DENSE 5-batch parallel launcher.
# Reuses phaseKG-dense-<batch>-<ts>/ run dirs (densified via dense kg-extract).
# Uses ports 18843-18847 to avoid conflicts with paralel Phase MAP (18841) /
# Phase MQ (18842) per task spec constraint #4.
set -uo pipefail

WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
PIPELINE_CFG="$EVAL/eval/config/pipeline.yaml"
PIPELINE_BAK="$WORK/pipeline.yaml.bak.dense-bench"

declare -A RUN_DIRS=(
  [004]=/root/.openclaw/evermembench-runs/phaseKG-dense-004-1780063771
  [005]=/root/.openclaw/evermembench-runs/phaseKG-dense-005-1780063771
  [010]=/root/.openclaw/evermembench-runs/phaseKG-dense-010-1780063771
  [011]=/root/.openclaw/evermembench-runs/phaseKG-dense-011-1780063771
  [016]=/root/.openclaw/evermembench-runs/phaseKG-dense-016-1780063771
)
BATCHES=(004 005 010 011 016)
PORTS=(18843 18844 18845 18846 18847)

echo "[PARALLEL-KG-DENSE] === installing pipeline.yaml (gpt-4.1-mini) ==="
if [ ! -f "$PIPELINE_CFG" ]; then
    echo "[PARALLEL-KG-DENSE] ERROR: $PIPELINE_CFG missing"
    exit 1
fi
cp "$PIPELINE_CFG" "$PIPELINE_BAK"
cp "$WORK/phaseH-pipeline-v2.yaml" "$PIPELINE_CFG"

restore_pipeline() {
    if [ -f "$PIPELINE_BAK" ]; then
        cp "$PIPELINE_BAK" "$PIPELINE_CFG"
        echo "[PARALLEL-KG-DENSE] restored original pipeline.yaml"
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
    echo "[PARALLEL-KG-DENSE] WARN: $RUN_DIR/nox-mem.db missing — skip $BATCH"
    continue
  fi
  KGE=$(sqlite3 "$RUN_DIR/nox-mem.db" "SELECT COUNT(*) FROM kg_entities;" 2>/dev/null || echo 0)
  KGR=$(sqlite3 "$RUN_DIR/nox-mem.db" "SELECT COUNT(*) FROM kg_relations;" 2>/dev/null || echo 0)
  echo "[PARALLEL-KG-DENSE] batch=$BATCH port=$PORT entities=$KGE relations=$KGR run=$RUN_DIR"
  RUN_DIR="$RUN_DIR" WORK="$WORK" nohup bash "$WORK/run-batch-phaseKG.sh" "$BATCH" "$PORT" \
    > "$RUN_DIR/stream-dense-bench.log" 2>&1 &
  PIDS+=($!)
  LAUNCHED+=("$BATCH")
  sleep 3
done

echo "[PARALLEL-KG-DENSE] all ${#PIDS[@]} launched — waiting..."
RC=0
for idx in "${!PIDS[@]}"; do
  pid="${PIDS[$idx]}"
  wait "$pid"
  rc=$?
  echo "[PARALLEL-KG-DENSE] pid=$pid (batch ${LAUNCHED[$idx]}) exited rc=$rc"
  [ "$rc" -ne 0 ] && RC=1
done

echo "[PARALLEL-KG-DENSE] === aggregate ==="
for BATCH in "${LAUNCHED[@]}"; do
  RUN_DIR="${RUN_DIRS[$BATCH]}"
  echo "--- $RUN_DIR ---"
  tail -5 "$RUN_DIR/analysis.txt" 2>/dev/null || echo "  no analysis.txt"
done
echo "[PARALLEL-KG-DENSE] === DONE (rc=$RC) ==="
exit $RC
