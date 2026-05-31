#!/bin/bash
# Wave 2 Phase 2 Capstone — IterB + Wave C Triple — 5-batch sequential
set -uo pipefail

WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
PIPELINE_CFG="$EVAL/eval/config/pipeline.yaml"
PIPELINE_BAK="$WORK/pipeline.yaml.bak.capstone"

BATCHES=(004 005 010 011 016)
PORT=18981  # Distinct from IterB (18980) to avoid stale state if leftover

declare -A PHASE_H_DBS=(
  [004]=/root/.openclaw/evermembench-runs/phaseKG-004-1780026247/nox-mem.db
  [005]=/root/.openclaw/evermembench-runs/phaseKG-005-1780026253/nox-mem.db
  [010]=/root/.openclaw/evermembench-runs/phaseKG-010-1780026258/nox-mem.db
  [011]=/root/.openclaw/evermembench-runs/phaseKG-011-1780026263/nox-mem.db
  [016]=/root/.openclaw/evermembench-runs/phaseKG-016-1780026268/nox-mem.db
)

# Swap pipeline.yaml ONCE — Gemini-3-flash as answer
echo "[CAPSTONE-SEQ] === installing pipeline.yaml (gemini-3-flash-preview backbone) ==="
if [ ! -f "$PIPELINE_CFG" ]; then
    echo "[CAPSTONE-SEQ] ERROR: $PIPELINE_CFG missing"
    exit 1
fi
cp "$PIPELINE_CFG" "$PIPELINE_BAK"
cp "$WORK/pipeline-gemini3flash.yaml" "$PIPELINE_CFG"
echo "[CAPSTONE-SEQ] backup -> $PIPELINE_BAK"
echo "[CAPSTONE-SEQ] active answer.model = $(grep -A1 '^answer:' $PIPELINE_CFG | tail -1 | tr -d ' ')"

restore_pipeline() {
    if [ -f "$PIPELINE_BAK" ]; then
        cp "$PIPELINE_BAK" "$PIPELINE_CFG"
        echo "[CAPSTONE-SEQ] restored original pipeline.yaml"
    fi
}
trap restore_pipeline EXIT

# Run sequentially
RUN_DIRS=()
RC_TOTAL=0
TOTAL_COST=0
COST_FILE="$WORK/cost-tracking.json"
echo "{\"batches\": []}" > "$COST_FILE"

for BATCH in "${BATCHES[@]}"; do
  SRC_DB="${PHASE_H_DBS[$BATCH]}"
  if [ ! -f "$SRC_DB" ]; then
    echo "[CAPSTONE-SEQ] WARN: $SRC_DB missing — skipping batch $BATCH"
    continue
  fi
  RUN_DIR="/root/.openclaw/evermembench-runs/capstone-iterB-triple-$BATCH-$(date +%s)"
  mkdir -p "$RUN_DIR"
  cp "$SRC_DB" "$RUN_DIR/nox-mem.db"
  [ -f "${SRC_DB}-wal" ] && cp "${SRC_DB}-wal" "$RUN_DIR/nox-mem.db-wal" || true
  [ -f "${SRC_DB}-shm" ] && cp "${SRC_DB}-shm" "$RUN_DIR/nox-mem.db-shm" || true
  echo "[CAPSTONE-SEQ] === starting batch=$BATCH port=$PORT run=$RUN_DIR ==="
  RUN_DIR="$RUN_DIR" WORK="$WORK" bash "$WORK/run-batch-capstone.sh" "$BATCH" "$PORT" \
    > "$RUN_DIR/stream.log" 2>&1
  rc=$?
  echo "[CAPSTONE-SEQ] batch=$BATCH exited rc=$rc"
  if [ "$rc" -ne 0 ]; then
    echo "[CAPSTONE-SEQ] tail of stream.log:"
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
    TOTAL_COST=$(python3 -c "print(round($TOTAL_COST + $BATCH_COST, 4))")
    echo "[CAPSTONE-SEQ] batch=$BATCH cost=\$$BATCH_COST cumulative=\$$TOTAL_COST"
    python3 -c "
import json
with open('$COST_FILE') as f: d = json.load(f)
d['batches'].append({'batch': '$BATCH', 'cost': float('$BATCH_COST'), 'cumulative': float('$TOTAL_COST')})
with open('$COST_FILE', 'w') as f: json.dump(d, f, indent=2)
"
    # Halt if projecting > $30
    PROJECTED=$(python3 -c "print(round($TOTAL_COST * 5 / ${#RUN_DIRS[@]:-1}, 2))" 2>/dev/null || echo "0")
    if (( $(echo "$TOTAL_COST > 30" | bc -l 2>/dev/null || echo 0) )); then
      echo "[CAPSTONE-SEQ] !!! BUDGET HALT — cumulative cost \$$TOTAL_COST > \$30 !!!"
      break
    fi
  fi

  RUN_DIRS+=("$RUN_DIR")
done

echo "[CAPSTONE-SEQ] === aggregate per-batch analysis tails ==="
for RUN_DIR in "${RUN_DIRS[@]}"; do
  echo "--- $RUN_DIR ---"
  tail -5 "$RUN_DIR/analysis.txt" 2>/dev/null || echo "  (no analysis.txt)"
done

# Save run dirs to a file for later aggregation
echo "${RUN_DIRS[*]}" > "$WORK/run-dirs.txt"

echo "[CAPSTONE-SEQ] === TOTAL COST: \$$TOTAL_COST ==="
echo "[CAPSTONE-SEQ] === DONE (rc=$RC_TOTAL) ==="
exit $RC_TOTAL
