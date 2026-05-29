#!/bin/bash
# KG densification — kg-extract on bench DB copies.
# Parallel across 5 batches. Increases --limit from 500 (sparse) to 2500 (dense, 5×).
#
# Pre-state: each $RUN_DIR/nox-mem.db is a clone of phaseH-v2 batch DB (~10k chunks)
#            with kg_entities + kg_relations EMPTY (already wiped pre-extract).
# Post-state: ~2500 chunks processed -> expected 2500-3000 entities + 7000-9000 relations
#             per batch (5× current sparse density).
#
# Usage: KG_LIMIT=2500 bash run-kg-dense-extract.sh
set -uo pipefail

KG_LIMIT="${KG_LIMIT:-2500}"
RUNDIRS=(
  /root/.openclaw/evermembench-runs/phaseKG-dense-004-1780063771
  /root/.openclaw/evermembench-runs/phaseKG-dense-005-1780063771
  /root/.openclaw/evermembench-runs/phaseKG-dense-010-1780063771
  /root/.openclaw/evermembench-runs/phaseKG-dense-011-1780063771
  /root/.openclaw/evermembench-runs/phaseKG-dense-016-1780063771
)
BATCHES=(004 005 010 011 016)

set -a; source /root/.openclaw/.env; set +a

echo "[DENSE-EXTRACT] === Launching kg-extract --limit $KG_LIMIT across 5 batches ==="
PIDS=()
T_START=$(date +%s)
for i in "${!RUNDIRS[@]}"; do
  B="${BATCHES[$i]}"
  RD="${RUNDIRS[$i]}"
  if [ ! -f "$RD/nox-mem.db" ]; then
    echo "[DENSE-EXTRACT] WARN batch=$B db missing — skip"
    continue
  fi
  PRE_E=$(sqlite3 "$RD/nox-mem.db" "SELECT COUNT(*) FROM kg_entities;" 2>/dev/null || echo 0)
  PRE_R=$(sqlite3 "$RD/nox-mem.db" "SELECT COUNT(*) FROM kg_relations;" 2>/dev/null || echo 0)
  echo "[DENSE-EXTRACT] batch=$B pre: entities=$PRE_E relations=$PRE_R run=$RD"
  (
    cd /root/.openclaw/workspace/tools/nox-mem
    export NOX_DB_PATH="$RD/nox-mem.db"
    nox-mem kg-extract --limit "$KG_LIMIT" > "$RD/kg-extract-dense.log" 2>&1
  ) &
  PIDS+=($!)
  sleep 5 # stagger to avoid Gemini concurrent-burst rate-limit
done

echo "[DENSE-EXTRACT] === ${#PIDS[@]} extracts launched — waiting (this may take 30-60min) ==="
RC=0
for idx in "${!PIDS[@]}"; do
  pid="${PIDS[$idx]}"
  wait "$pid"
  rc=$?
  echo "[DENSE-EXTRACT] batch=${BATCHES[$idx]} pid=$pid rc=$rc"
  [ "$rc" -ne 0 ] && RC=1
done

T_END=$(date +%s)
echo "[DENSE-EXTRACT] === all done in $((T_END - T_START))s (rc=$RC) ==="
echo "[DENSE-EXTRACT] === POST counts ==="
for i in "${!RUNDIRS[@]}"; do
  B="${BATCHES[$i]}"
  RD="${RUNDIRS[$i]}"
  E=$(sqlite3 "$RD/nox-mem.db" "SELECT COUNT(*) FROM kg_entities;" 2>/dev/null || echo 0)
  R=$(sqlite3 "$RD/nox-mem.db" "SELECT COUNT(*) FROM kg_relations;" 2>/dev/null || echo 0)
  echo "[DENSE-EXTRACT] batch=$B post: entities=$E relations=$R"
done

exit $RC
