#!/bin/bash
# Wrapper that:
#   1. Runs `nox-mem kg-extract --limit $NOX_KG_EXTRACT_LIMIT` on the
#      pre-warmed batch DB (populates kg_entities + kg_relations).
#   2. Then chains into run-batch-phaseKG.sh for the bench itself.
#
# Why a separate wrapper: kg-extract requires NOX_DB_PATH bound BEFORE the
# CLI starts (op-audit checks path on import). Bench then runs against the
# now-populated DB. Splitting into two stages keeps each stage's logging
# clean and allows easy retry of bench alone if kg-extract succeeded.
#
# Usage (called by run-parallel-phaseKG.sh):
#   WORK=... RUN_DIR=... NOX_KG_EXTRACT_LIMIT=500 \
#   bash run-batch-phaseKG-with-kg-extract.sh <BATCH> <PORT>
set -uo pipefail

BATCH="${1:?usage: $0 <BATCH> <PORT>}"
PORT="${2:?usage: $0 <BATCH> <PORT>}"
WORK="${WORK:?WORK env var must be set}"
RUN_DIR="${RUN_DIR:?RUN_DIR env var must be set}"
KG_LIMIT="${NOX_KG_EXTRACT_LIMIT:-500}"

set -a; source /root/.openclaw/.env; set +a
source /root/.openclaw/evermembench-phaseB-1779978778/venv/bin/activate

export NOX_DB_PATH="$RUN_DIR/nox-mem.db"

if [ ! -f "$NOX_DB_PATH" ]; then
    echo "[KG-EXTRACT-PRE BATCH $BATCH] ERROR: DB missing at $NOX_DB_PATH"
    exit 1
fi

PRE_E=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM kg_entities;" 2>/dev/null || echo 0)
PRE_R=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM kg_relations;" 2>/dev/null || echo 0)
echo "[KG-EXTRACT-PRE BATCH $BATCH] pre kg state: entities=$PRE_E relations=$PRE_R limit=$KG_LIMIT"

if [ "$PRE_R" -lt 50 ]; then
    echo "[KG-EXTRACT-PRE BATCH $BATCH] === Running kg-extract --limit $KG_LIMIT ==="
    cd /root/.openclaw/workspace/tools/nox-mem
    T0=$(date +%s)
    nox-mem kg-extract --limit "$KG_LIMIT" > "$RUN_DIR/kg-extract.log" 2>&1 || {
        echo "[KG-EXTRACT-PRE BATCH $BATCH] WARN: kg-extract exited non-zero (continuing)"
    }
    T1=$(date +%s)
    POST_E=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM kg_entities;" 2>/dev/null || echo 0)
    POST_R=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM kg_relations;" 2>/dev/null || echo 0)
    echo "[KG-EXTRACT-PRE BATCH $BATCH] kg-extract done in $((T1-T0))s — entities=$POST_E relations=$POST_R"
else
    echo "[KG-EXTRACT-PRE BATCH $BATCH] KG already populated, skipping kg-extract"
fi

echo "[KG-EXTRACT-PRE BATCH $BATCH] === Chaining into run-batch-phaseKG.sh ==="
exec bash "$WORK/run-batch-phaseKG.sh" "$BATCH" "$PORT"
