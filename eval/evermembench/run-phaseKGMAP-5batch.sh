#!/bin/bash
# Phase KGMAP 5-batch master runner — sequential dispatch per
# [[5-parallel-rerank-api-servers-oom-vps]] lesson.
#
# Runs batches 004 / 005 / 010 / 011 / 016 in series on PORT 18847 (isolated
# from MAP=18841 and KG+MQ paralelo agent=18846).
# Each batch re-uses Phase H v2 corpus DB (pre-warmed, ~10k chunks/batch).

set -uo pipefail

WORK=${WORK:-/root/.openclaw/wave-B-KGMAP-8bb23b09}
PORT=${PORT:-18847}
TS_MASTER=$(date +%s)
MASTER_LOG=$WORK/master-${TS_MASTER}.log

# Path to phaseH v2 pipeline yaml (symlinked from MAP workdir)
PIPELINE_YAML=$WORK/pipeline-phaseH-v2.yaml

# Source the run-batch script as a function so we can sequence batches.
RUN_SCRIPT=$WORK/run-batch-phaseKGMAP.sh
if [ ! -x "$RUN_SCRIPT" ]; then
    echo "ERROR: $RUN_SCRIPT not executable" | tee -a "$MASTER_LOG"
    exit 1
fi

BATCHES=(004 005 010 011 016)
SUMMARY_FILE=$WORK/5batch-summary.txt
: > "$SUMMARY_FILE"

echo "[MASTER] starting 5-batch Phase KGMAP run at $(date)" | tee -a "$MASTER_LOG"
echo "[MASTER] batches: ${BATCHES[*]}" | tee -a "$MASTER_LOG"
echo "[MASTER] port: $PORT (isolated)" | tee -a "$MASTER_LOG"
echo "[MASTER] WORK: $WORK" | tee -a "$MASTER_LOG"
echo "[MASTER] mode: phaseKGMAP (KG path + rerank + MA-protection + KG anchor)" | tee -a "$MASTER_LOG"

for B in "${BATCHES[@]}"; do
    # Each batch needs a fresh per-batch DB copy. We SOURCE from phaseKG runs
    # (PR #379) because those DBs have kg_entities + kg_relations populated
    # (~550 ents / ~1800 rels per batch). The Phase H v2 source DBs do NOT
    # have KG built — using them would make the KG anchor inert (empirically
    # verified 2026-05-29: KG=0,0 in phaseH-v2-004 → mechanism dead).
    SRC_DB=$(ls -dt /root/.openclaw/evermembench-runs/phaseKG-${B}-*/nox-mem.db 2>/dev/null | head -1)
    if [ -z "$SRC_DB" ] || [ ! -f "$SRC_DB" ]; then
        echo "[MASTER] ERROR: no Phase KG source DB for batch=$B" | tee -a "$MASTER_LOG"
        continue
    fi

    TS=$(date +%s)
    RUN_DIR=/root/.openclaw/evermembench-runs/phaseKGMAP-${B}-${TS}
    mkdir -p "$RUN_DIR"
    cp "$SRC_DB" "$RUN_DIR/nox-mem.db"
    SRC_CHUNKS=$(sqlite3 "$RUN_DIR/nox-mem.db" "SELECT COUNT(*) FROM chunks" 2>/dev/null || echo 0)
    SRC_KG_E=$(sqlite3 "$RUN_DIR/nox-mem.db" "SELECT COUNT(*) FROM kg_entities" 2>/dev/null || echo 0)
    SRC_KG_R=$(sqlite3 "$RUN_DIR/nox-mem.db" "SELECT COUNT(*) FROM kg_relations" 2>/dev/null || echo 0)
    echo "[MASTER] === batch=$B RUN_DIR=$RUN_DIR src_db=$SRC_DB chunks=$SRC_CHUNKS kg_e=$SRC_KG_E kg_r=$SRC_KG_R ===" | tee -a "$MASTER_LOG"
    echo "[MASTER] === batch=$B ===" >> "$SUMMARY_FILE"

    # Run the batch (the script handles api-server lifecycle + cleanup trap)
    BATCH_LOG=$WORK/run-${B}-${TS}.log
    PIPELINE_YAML="$PIPELINE_YAML" WORK="$WORK" RUN_DIR="$RUN_DIR" \
        bash "$RUN_SCRIPT" "$B" "$PORT" > "$BATCH_LOG" 2>&1
    RC=$?

    if [ $RC -ne 0 ]; then
        echo "[MASTER] batch=$B FAILED rc=$RC — see $BATCH_LOG" | tee -a "$MASTER_LOG"
        tail -30 "$BATCH_LOG" | tee -a "$MASTER_LOG"
    else
        echo "[MASTER] batch=$B OK" | tee -a "$MASTER_LOG"
        ANA="$RUN_DIR/analysis.txt"
        if [ -f "$ANA" ]; then
            grep -E "overall|F_MH|F_SH|F_TP|F_HL|MA_C|MA_P|MA_U|P_Style|P_Skill|P_Title" "$ANA" >> "$SUMMARY_FILE" || true
            echo "" >> "$SUMMARY_FILE"
        fi
        # Pull KGMAP-specific telemetry from batch log
        grep "KGMAP telemetry:" "$BATCH_LOG" >> "$SUMMARY_FILE" || true
        echo "" >> "$SUMMARY_FILE"
    fi
    # Brief pause between batches to let api-server fully release port
    sleep 5
done

echo "[MASTER] DONE at $(date)" | tee -a "$MASTER_LOG"
echo "[MASTER] summary:" | tee -a "$MASTER_LOG"
cat "$SUMMARY_FILE" | tee -a "$MASTER_LOG"
