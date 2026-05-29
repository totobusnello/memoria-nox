#!/bin/bash
# Phase AC (Lab Q1 #1) 5-batch — 2-at-a-time wave runner.
#
# Phase AC 5-parallel run failed (2026-05-29) due to memory pressure: 5×
# Python harness processes + 5× api-server processes + per-query MiniLM rerank
# OOM'd on 15GB VPS. Symptom: 80-90% search queries returned "Server
# disconnected" error.
#
# This script runs the 5 batches in 3 sequential waves of 2 (with 016 alone
# in wave 3) to fit comfortably in 15GB RAM budget.
#
# Per-wave parallelism: 2.  Total wallclock: ~3-4× single-batch (~30 min each)
# ≈ 90-120 min total wallclock.
#
# Usage:
#   WORK=/tmp/phaseAC-5batch-<uuid> bash run-parallel-phaseAC-pair.sh
set -uo pipefail

WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
PIPELINE_CFG="$EVAL/eval/config/pipeline.yaml"
PIPELINE_BAK="$WORK/pipeline.yaml.bak.pair"
ADAPTER_DIR="$EVAL/eval/src/adapters"
ADAPTER_BAK="$WORK/nox_mem_adapter.py.bak.pair"

# Per-wave config — 2-batch parallel waves
declare -a WAVE1_BATCHES=(004 005)
declare -a WAVE1_PORTS=(18830 18831)
declare -a WAVE2_BATCHES=(010 011)
declare -a WAVE2_PORTS=(18830 18831)
declare -a WAVE3_BATCHES=(016)
declare -a WAVE3_PORTS=(18830)

declare -A PHASEB_DBS=(
  [004]=/root/.openclaw/evermembench-runs/phaseB-004-1779979927/nox-mem.db
  [005]=/root/.openclaw/evermembench-runs/phaseB-005-1779990311/nox-mem.db
  [010]=/root/.openclaw/evermembench-runs/phaseB-010-1779990316/nox-mem.db
  [011]=/root/.openclaw/evermembench-runs/phaseB-011-1779990322/nox-mem.db
  [016]=/root/.openclaw/evermembench-runs/phaseB-016-1779990327/nox-mem.db
)

# ── Deploy updated adapter + query_classifier to harness adapter dir ──
echo "[PAIR-AC] === deploying phaseAC adapter + query_classifier ==="
if [ ! -d "$ADAPTER_DIR" ]; then
    echo "[PAIR-AC] ERROR: adapter dir missing: $ADAPTER_DIR"
    exit 1
fi
if [ ! -f "$WORK/adapter_nox_mem.py" ] || [ ! -f "$WORK/query_classifier.py" ]; then
    echo "[PAIR-AC] ERROR: $WORK/adapter_nox_mem.py or $WORK/query_classifier.py missing"
    exit 1
fi
cp "$ADAPTER_DIR/nox_mem_adapter.py" "$ADAPTER_BAK"
cp "$WORK/adapter_nox_mem.py" "$ADAPTER_DIR/nox_mem_adapter.py"
cp "$WORK/query_classifier.py" "$ADAPTER_DIR/query_classifier.py"
echo "[PAIR-AC] adapter deployed (backup at $ADAPTER_BAK)"
find "$ADAPTER_DIR/__pycache__" -name "nox_mem_adapter*" -delete 2>/dev/null || true
find "$ADAPTER_DIR/__pycache__" -name "query_classifier*" -delete 2>/dev/null || true

# Swap pipeline.yaml ONCE
echo "[PAIR-AC] === installing phaseH v2 pipeline.yaml ==="
if [ ! -f "$PIPELINE_CFG" ]; then
    echo "[PAIR-AC] ERROR: $PIPELINE_CFG missing"
    exit 1
fi
cp "$PIPELINE_CFG" "$PIPELINE_BAK"
cp "$WORK/pipeline-phaseH-v2.yaml" "$PIPELINE_CFG"

restore_state() {
    if [ -f "$PIPELINE_BAK" ]; then
        cp "$PIPELINE_BAK" "$PIPELINE_CFG"
        echo "[PAIR-AC] restored original pipeline.yaml"
    fi
    if [ -f "$ADAPTER_BAK" ]; then
        cp "$ADAPTER_BAK" "$ADAPTER_DIR/nox_mem_adapter.py"
        rm -f "$ADAPTER_DIR/query_classifier.py"
        find "$ADAPTER_DIR/__pycache__" -name "nox_mem_adapter*" -delete 2>/dev/null || true
        find "$ADAPTER_DIR/__pycache__" -name "query_classifier*" -delete 2>/dev/null || true
        echo "[PAIR-AC] restored original nox_mem_adapter.py"
    fi
}
trap restore_state EXIT

run_wave() {
    local wave_num="$1"
    shift
    local -a batches=("$@")
    local mid=$((${#batches[@]} / 2))
    local -a ports=()
    # First half of args is batches, second half is ports — we use a different layout below
    # Simpler: pass batches and ports via referenced arrays
    return
}

run_wave_pair() {
    local wave_num="$1"
    shift
    local -a items=("$@")
    # items is parallel array: batch1, port1, batch2, port2 (or just batch1, port1 for single)
    local -a PIDS=()
    local -a RUN_DIRS=()
    local i=0
    while [ $i -lt ${#items[@]} ]; do
        local BATCH="${items[$i]}"
        local PORT="${items[$((i+1))]}"
        local SRC_DB="${PHASEB_DBS[$BATCH]}"
        if [ ! -f "$SRC_DB" ]; then
            echo "[PAIR-AC W$wave_num] WARN: $SRC_DB missing — skipping batch $BATCH"
            i=$((i + 2))
            continue
        fi
        local RUN_DIR="/root/.openclaw/evermembench-runs/phaseAC-$BATCH-$(date +%s)"
        mkdir -p "$RUN_DIR"
        cp "$SRC_DB" "$RUN_DIR/nox-mem.db"
        [ -f "${SRC_DB}-wal" ] && cp "${SRC_DB}-wal" "$RUN_DIR/nox-mem.db-wal" || true
        [ -f "${SRC_DB}-shm" ] && cp "${SRC_DB}-shm" "$RUN_DIR/nox-mem.db-shm" || true
        echo "[PAIR-AC W$wave_num] launch batch=$BATCH port=$PORT run=$RUN_DIR"
        RUN_DIR="$RUN_DIR" WORK="$WORK" nohup bash "$WORK/run-batch-phaseAC-prewarmed.sh" "$BATCH" "$PORT" \
            > "$RUN_DIR/stream.log" 2>&1 &
        PIDS+=($!)
        RUN_DIRS+=("$RUN_DIR")
        sleep 5
        i=$((i + 2))
    done

    echo "[PAIR-AC W$wave_num] ${#PIDS[@]} launched — waiting..."
    local RC_WAVE=0
    local idx=0
    for pid in "${PIDS[@]}"; do
        wait "$pid"
        local rc=$?
        echo "[PAIR-AC W$wave_num] pid=$pid exited rc=$rc"
        [ "$rc" -ne 0 ] && RC_WAVE=1
        idx=$((idx + 1))
    done

    # Summarise wave
    for RUN_DIR in "${RUN_DIRS[@]}"; do
        echo "--- $RUN_DIR ---"
        tail -5 "$RUN_DIR/analysis.txt" 2>/dev/null || echo "  (no analysis.txt)"
        cat "$RUN_DIR/routing-audit.txt" 2>/dev/null || true
    done
    return $RC_WAVE
}

RC_TOTAL=0
echo "[PAIR-AC] === Wave 1: 004 + 005 ==="
run_wave_pair 1 004 18830 005 18831 || RC_TOTAL=1
echo
echo "[PAIR-AC] === Wave 2: 010 + 011 ==="
run_wave_pair 2 010 18830 011 18831 || RC_TOTAL=1
echo
echo "[PAIR-AC] === Wave 3: 016 (solo) ==="
run_wave_pair 3 016 18830 || RC_TOTAL=1

echo "[PAIR-AC] === DONE (rc=$RC_TOTAL) ==="
exit $RC_TOTAL
