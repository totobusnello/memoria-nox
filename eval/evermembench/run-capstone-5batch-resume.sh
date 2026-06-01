#!/bin/bash
# Wave 2 Phase 2 Capstone — IterB + Wave C Triple — RESUME 4-batch (post-reboot)
# Reuses batch 004 analysis.txt (pre-reboot, persisted on disk).
set -uo pipefail

WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
PIPELINE_CFG="$EVAL/eval/config/pipeline.yaml"
PIPELINE_BAK="$WORK/pipeline.yaml.bak.capstone"

# RESUME: only 4 remaining batches; batch 004 analysis.txt already on disk
BATCHES=(005 010 011 016)
PORT=18981

declare -A PHASE_H_DBS=(
  [005]=/root/.openclaw/evermembench-runs/phaseKG-005-1780026253/nox-mem.db
  [010]=/root/.openclaw/evermembench-runs/phaseKG-010-1780026258/nox-mem.db
  [011]=/root/.openclaw/evermembench-runs/phaseKG-011-1780026263/nox-mem.db
  [016]=/root/.openclaw/evermembench-runs/phaseKG-016-1780026268/nox-mem.db
)

# Persisted batch 004 analysis dir (preserved across reboot)
BATCH_004_DIR="/root/.openclaw/evermembench-runs/capstone-iterB-triple-004-1780260019"
if [ ! -f "$BATCH_004_DIR/analysis.txt" ]; then
    echo "[CAPSTONE-RESUME] ERROR: batch 004 analysis.txt missing — resume invalidated"
    exit 1
fi
echo "[CAPSTONE-RESUME] === batch 004 analysis.txt preserved at $BATCH_004_DIR ==="

# Pipeline.yaml already at gemini-3-flash-preview (left from pre-reboot run);
# install only if not already there.
if grep -q "gemini-3-flash-preview" "$PIPELINE_CFG"; then
    echo "[CAPSTONE-RESUME] pipeline.yaml already at gemini-3-flash-preview — keeping"
    [ ! -f "$PIPELINE_BAK" ] && cp "$PIPELINE_CFG" "$PIPELINE_BAK"
else
    if [ ! -f "$WORK/pipeline-gemini3flash.yaml" ]; then
        echo "[CAPSTONE-RESUME] ERROR: pipeline-gemini3flash.yaml missing in WORK"
        exit 1
    fi
    cp "$PIPELINE_CFG" "$PIPELINE_BAK"
    cp "$WORK/pipeline-gemini3flash.yaml" "$PIPELINE_CFG"
fi
echo "[CAPSTONE-RESUME] active answer.model = $(grep -A1 '^answer:' $PIPELINE_CFG | tail -1 | tr -d ' ')"

restore_pipeline() {
    if [ -f "$PIPELINE_BAK" ]; then
        cp "$PIPELINE_BAK" "$PIPELINE_CFG"
        echo "[CAPSTONE-RESUME] restored original pipeline.yaml"
    fi
}
trap restore_pipeline EXIT

# Pre-seed RUN_DIRS with batch 004 (for aggregation)
RUN_DIRS=("$BATCH_004_DIR")
RC_TOTAL=0
TOTAL_COST=0
COST_FILE="$WORK/cost-tracking.json"
echo "{\"batches\": [{\"batch\": \"004\", \"cost\": 0.0, \"cumulative\": 0.0, \"note\": \"pre-reboot, cost not tracked\"}]}" > "$COST_FILE"

# Budget cap raised to $55 per user authorization (resume)
BUDGET_CAP=55

for BATCH in "${BATCHES[@]}"; do
  SRC_DB="${PHASE_H_DBS[$BATCH]}"
  if [ ! -f "$SRC_DB" ]; then
    echo "[CAPSTONE-RESUME] WARN: $SRC_DB missing — skipping batch $BATCH"
    continue
  fi
  RUN_DIR="/root/.openclaw/evermembench-runs/capstone-iterB-triple-$BATCH-$(date +%s)"
  mkdir -p "$RUN_DIR"
  cp "$SRC_DB" "$RUN_DIR/nox-mem.db"
  [ -f "${SRC_DB}-wal" ] && cp "${SRC_DB}-wal" "$RUN_DIR/nox-mem.db-wal" || true
  [ -f "${SRC_DB}-shm" ] && cp "${SRC_DB}-shm" "$RUN_DIR/nox-mem.db-shm" || true
  echo "[CAPSTONE-RESUME] === starting batch=$BATCH port=$PORT run=$RUN_DIR ==="
  RUN_DIR="$RUN_DIR" WORK="$WORK" bash "$WORK/run-batch-capstone.sh" "$BATCH" "$PORT" \
    > "$RUN_DIR/stream.log" 2>&1
  rc=$?
  echo "[CAPSTONE-RESUME] batch=$BATCH exited rc=$rc"
  if [ "$rc" -ne 0 ]; then
    echo "[CAPSTONE-RESUME] tail of stream.log:"
    tail -30 "$RUN_DIR/stream.log" 2>/dev/null || true
    RC_TOTAL=1
  fi

  # Cost tracking — extract iterb_total_cost_usd from search_results
  SEARCH_FILE="$RUN_DIR/search-results-batch-$BATCH.json"
  if [ -f "$SEARCH_FILE" ]; then
    BATCH_COST=$(python3 -c "
import json
with open('$SEARCH_FILE') as f:
    data = json.load(f)
results = data if isinstance(data, list) else data.get('results', [])
total = sum(float(r.get('iterb_total_cost_usd') or 0) for r in results)
print(f'{total:.4f}')
" 2>/dev/null || echo "0")
    TOTAL_COST=$(awk "BEGIN {printf \"%.4f\", $TOTAL_COST + $BATCH_COST}")
    echo "[CAPSTONE-RESUME] batch=$BATCH cost=\$$BATCH_COST cumulative=\$$TOTAL_COST"
    python3 -c "
import json
with open('$COST_FILE') as f: d = json.load(f)
d['batches'].append({'batch': '$BATCH', 'cost': float('$BATCH_COST'), 'cumulative': float('$TOTAL_COST')})
with open('$COST_FILE', 'w') as f: json.dump(d, f, indent=2)
"
    # FIXED bash projection: use ${#arr[@]} directly (cannot apply :- to array length form);
    # safe because RUN_DIRS pre-seeded with batch 004 → never zero.
    COMPLETED=${#RUN_DIRS[@]}
    PROJECTED=$(awk "BEGIN {printf \"%.2f\", $TOTAL_COST * 5 / $COMPLETED}")
    echo "[CAPSTONE-RESUME] projected 5-batch total at current pace: \$$PROJECTED (cap \$$BUDGET_CAP)"
    if awk "BEGIN {exit ($TOTAL_COST > $BUDGET_CAP) ? 0 : 1}"; then
      echo "[CAPSTONE-RESUME] !!! BUDGET HALT — cumulative cost \$$TOTAL_COST > \$$BUDGET_CAP !!!"
      break
    fi
  fi

  RUN_DIRS+=("$RUN_DIR")
done

echo "[CAPSTONE-RESUME] === aggregate per-batch analysis tails ==="
for RUN_DIR in "${RUN_DIRS[@]}"; do
  echo "--- $RUN_DIR ---"
  tail -5 "$RUN_DIR/analysis.txt" 2>/dev/null || echo "  (no analysis.txt)"
done

echo "${RUN_DIRS[*]}" > "$WORK/run-dirs.txt"

echo "[CAPSTONE-RESUME] === TOTAL COST (excl. batch 004): \$$TOTAL_COST ==="
echo "[CAPSTONE-RESUME] === DONE (rc=$RC_TOTAL) ==="
exit $RC_TOTAL
