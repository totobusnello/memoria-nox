#!/bin/bash
# Phase AC (Lab Q1 #1) 5-batch parallel launcher.
#
# Adaptive query classifier (Option A heuristic, spec PR #373):
#   - Per-query routes to MiniLM rerank ON (multi_hop) or OFF (factual)
#   - Backbone: gpt-4.1-mini (Phase H v2 methodology)
#   - Judge: gemini-2.5-flash
#   - Reuses Phase B winning DBs (skip add+vectorize)
#   - 5 parallel batches (004/005/010/011/016)
#   - Ports 18830-18834 (isolated from prod 18802 and Phase H v2 18820-18824)
#
# Pipeline.yaml swapped ONCE here (avoid 5-way race) to Phase H v2 config
# (gpt-4.1-mini answer / gemini judge), restored ONCE after all batches complete.
#
# Usage:
#   WORK=/tmp/phaseAC-5batch-<uuid> bash run-parallel-phaseAC.sh
#
# Prereqs:
#   - $WORK/run-batch-phaseAC-prewarmed.sh present + executable
#   - $WORK/pipeline-phaseH-v2.yaml present (will be installed as pipeline.yaml)
#   - $WORK/everos/benchmarks/EverMemBench symlinked from existing phaseB install
#   - eval/evermembench/query_classifier.py + adapter_nox_mem.py with phaseAC
#     wired into harness install (NoxMemAdapter import path resolves)
set -uo pipefail

WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
PIPELINE_CFG="$EVAL/eval/config/pipeline.yaml"
PIPELINE_BAK="$WORK/pipeline.yaml.bak.parallel"

# Per-batch config: ports + source Phase B DB (5 batches per spec §5.1 + prompt §3)
BATCHES=(004 005 010 011 016)
PORTS=(18830 18831 18832 18833 18834)
declare -A PHASEB_DBS=(
  [004]=/root/.openclaw/evermembench-runs/phaseB-004-1779979927/nox-mem.db
  [005]=/root/.openclaw/evermembench-runs/phaseB-005-1779990311/nox-mem.db
  [010]=/root/.openclaw/evermembench-runs/phaseB-010-1779990316/nox-mem.db
  [011]=/root/.openclaw/evermembench-runs/phaseB-011-1779990322/nox-mem.db
  [016]=/root/.openclaw/evermembench-runs/phaseB-016-1779990327/nox-mem.db
)

# Fallback: if expected phaseB-004 path doesn't exist, scan for it
if [ ! -f "${PHASEB_DBS[004]}" ]; then
    CAND_004=$(ls -d /root/.openclaw/evermembench-runs/phaseB-004-* 2>/dev/null | head -1)
    [ -n "$CAND_004" ] && PHASEB_DBS[004]="$CAND_004/nox-mem.db"
fi

# ── Deploy updated adapter + query_classifier to harness adapter dir ──
ADAPTER_DIR="$EVAL/eval/src/adapters"
ADAPTER_BAK="$WORK/nox_mem_adapter.py.bak"
echo "[PARALLEL-AC] === deploying phaseAC adapter + query_classifier ==="
if [ ! -d "$ADAPTER_DIR" ]; then
    echo "[PARALLEL-AC] ERROR: adapter dir missing: $ADAPTER_DIR"
    exit 1
fi
if [ ! -f "$WORK/adapter_nox_mem.py" ] || [ ! -f "$WORK/query_classifier.py" ]; then
    echo "[PARALLEL-AC] ERROR: $WORK/adapter_nox_mem.py or $WORK/query_classifier.py missing"
    exit 1
fi
cp "$ADAPTER_DIR/nox_mem_adapter.py" "$ADAPTER_BAK"
cp "$WORK/adapter_nox_mem.py" "$ADAPTER_DIR/nox_mem_adapter.py"
cp "$WORK/query_classifier.py" "$ADAPTER_DIR/query_classifier.py"
echo "[PARALLEL-AC] adapter deployed (backup at $ADAPTER_BAK)"
# Clear bytecode cache so the new adapter loads fresh
find "$ADAPTER_DIR/__pycache__" -name "nox_mem_adapter*" -delete 2>/dev/null || true
find "$ADAPTER_DIR/__pycache__" -name "query_classifier*" -delete 2>/dev/null || true

# Swap pipeline.yaml ONCE
echo "[PARALLEL-AC] === installing phaseH v2 pipeline.yaml (gpt-4.1-mini answer / gemini judge) ==="
if [ ! -f "$PIPELINE_CFG" ]; then
    echo "[PARALLEL-AC] ERROR: $PIPELINE_CFG missing — harness not installed?"
    exit 1
fi
cp "$PIPELINE_CFG" "$PIPELINE_BAK"
cp "$WORK/pipeline-phaseH-v2.yaml" "$PIPELINE_CFG"
echo "[PARALLEL-AC] backed up original -> $PIPELINE_BAK"
echo "[PARALLEL-AC] active answer.model = $(grep -A1 '^answer:' $PIPELINE_CFG | tail -1 | tr -d ' ')"

restore_pipeline() {
    if [ -f "$PIPELINE_BAK" ]; then
        cp "$PIPELINE_BAK" "$PIPELINE_CFG"
        echo "[PARALLEL-AC] restored original pipeline.yaml"
    fi
    if [ -f "$ADAPTER_BAK" ]; then
        cp "$ADAPTER_BAK" "$ADAPTER_DIR/nox_mem_adapter.py"
        rm -f "$ADAPTER_DIR/query_classifier.py"
        find "$ADAPTER_DIR/__pycache__" -name "nox_mem_adapter*" -delete 2>/dev/null || true
        find "$ADAPTER_DIR/__pycache__" -name "query_classifier*" -delete 2>/dev/null || true
        echo "[PARALLEL-AC] restored original nox_mem_adapter.py"
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
    echo "[PARALLEL-AC] WARN: $SRC_DB missing — skipping batch $BATCH"
    continue
  fi
  RUN_DIR="/root/.openclaw/evermembench-runs/phaseAC-$BATCH-$(date +%s)"
  mkdir -p "$RUN_DIR"
  cp "$SRC_DB" "$RUN_DIR/nox-mem.db"
  [ -f "${SRC_DB}-wal" ] && cp "${SRC_DB}-wal" "$RUN_DIR/nox-mem.db-wal" || true
  [ -f "${SRC_DB}-shm" ] && cp "${SRC_DB}-shm" "$RUN_DIR/nox-mem.db-shm" || true
  echo "[PARALLEL-AC] launch batch=$BATCH port=$PORT run=$RUN_DIR"
  RUN_DIR="$RUN_DIR" WORK="$WORK" nohup bash "$WORK/run-batch-phaseAC-prewarmed.sh" "$BATCH" "$PORT" \
    > "$RUN_DIR/stream.log" 2>&1 &
  PIDS+=($!)
  RUN_DIRS+=("$RUN_DIR")
  # Stagger 3s so api-servers don't race on port-init
  sleep 3
done

echo "[PARALLEL-AC] all ${#PIDS[@]} launched — waiting..."
RC_TOTAL=0
for idx in "${!PIDS[@]}"; do
  pid="${PIDS[$idx]}"
  wait "$pid"
  rc=$?
  echo "[PARALLEL-AC] pid=$pid (batch ${BATCHES[$idx]}) exited rc=$rc"
  [ "$rc" -ne 0 ] && RC_TOTAL=1
done

echo "[PARALLEL-AC] === aggregate per-batch analysis tails ==="
for RUN_DIR in "${RUN_DIRS[@]}"; do
  echo "--- $RUN_DIR ---"
  tail -5 "$RUN_DIR/analysis.txt" 2>/dev/null || echo "  (no analysis.txt)"
done

echo "[PARALLEL-AC] === routing audits ==="
for RUN_DIR in "${RUN_DIRS[@]}"; do
  echo "--- $RUN_DIR routing ---"
  cat "$RUN_DIR/routing-audit.txt" 2>/dev/null || echo "  (no audit)"
done

echo "[PARALLEL-AC] === DONE (rc=$RC_TOTAL) ==="
exit $RC_TOTAL
