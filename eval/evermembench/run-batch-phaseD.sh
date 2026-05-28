#!/bin/bash
# Run one EverMemBench batch with Phase B adapter against isolated nox-mem.
#
# Usage:
#   ./run-batch.sh <BATCH> <PORT>   # e.g. ./run-batch.sh 004 18810
#
# Prereqs (caller must satisfy):
#   - GEMINI_API_KEY exported (sourced from /root/.openclaw/.env)
#   - WORK env var = run root (e.g. /root/.openclaw/evermembench-phaseB-<TS>)
#   - venv at $WORK/venv activated
#   - dataset/<BATCH>/{dialogue,qa_BATCH}.json staged in $EVAL
#   - nox-mem CLI on PATH; adapter + cli.py + config installed in $EVAL
#
# Side effects:
#   - Creates isolated DB at $RUN_DIR/nox-mem.db (op-audit-compliant path)
#   - Spawns nox-mem api-server on $PORT pointing at isolated DB
#   - Runs Add + Search + Answer + Evaluate stages
#   - Kills the spawned api-server on exit
#   - Logs to $RUN_DIR/*.log
set -uo pipefail   # no -e: per-stage errors should not abort the whole pipeline

BATCH="${1:?usage: $0 <BATCH> <PORT>}"
PORT="${2:?usage: $0 <BATCH> <PORT>}"
WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
RUN_DIR="/root/.openclaw/evermembench-runs/phaseB-$BATCH-$(date +%s)"
mkdir -p "$RUN_DIR"
echo "[BATCH $BATCH PORT $PORT] RUN_DIR=$RUN_DIR"

# Source prod env to get GEMINI_API_KEY (but DO NOT clobber NOX_DB_PATH)
set -a; source /root/.openclaw/.env; set +a
export LLM_API_KEY="$GEMINI_API_KEY"
export LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"

# Isolated DB path (op-audit allows /root/.openclaw/ prefix)
export NOX_DB_PATH="$RUN_DIR/nox-mem.db"
export NOX_API_PORT="$PORT"
export NOX_API_BASE="http://127.0.0.1:$PORT"
export NOX_ADAPTER_MODE="${NOX_ADAPTER_MODE:-phaseB}"
export NOX_MEM_BIN="$(which nox-mem)"

# Cleanup hook
API_PID=""
cleanup() {
    if [ -n "$API_PID" ]; then
        kill "$API_PID" 2>/dev/null || true
        wait "$API_PID" 2>/dev/null || true
        echo "[BATCH $BATCH] killed api server pid=$API_PID"
    fi
}
trap cleanup EXIT

echo "[BATCH $BATCH] === Step 1: init fresh DB schema ==="
# Initialize empty DB with v18 schema
"$NOX_MEM_BIN" stats > "$RUN_DIR/init-stats.log" 2>&1 || true

# Apply v18 + KG schema patch (per RUN-VPS gotcha #3)
sqlite3 "$NOX_DB_PATH" >> "$RUN_DIR/schema-patch.log" 2>&1 <<'SQL'
ALTER TABLE chunks ADD COLUMN retention_days INTEGER;
ALTER TABLE chunks ADD COLUMN pain REAL DEFAULT 0.2;
ALTER TABLE chunks ADD COLUMN section TEXT;
ALTER TABLE chunks ADD COLUMN section_boost REAL DEFAULT 1.0;
PRAGMA user_version = 18;
CREATE TABLE IF NOT EXISTS kg_entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, entity_type TEXT NOT NULL,
    first_seen TEXT DEFAULT (datetime('now')),
    last_seen TEXT DEFAULT (datetime('now')),
    mention_count INTEGER DEFAULT 1, attributes TEXT,
    UNIQUE(name, entity_type));
CREATE INDEX IF NOT EXISTS idx_kg_entities_name ON kg_entities(name);
CREATE INDEX IF NOT EXISTS idx_kg_entities_type ON kg_entities(entity_type);
CREATE TABLE IF NOT EXISTS kg_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_entity_id INTEGER NOT NULL, relation_type TEXT NOT NULL,
    target_entity_id INTEGER NOT NULL, evidence_chunk_id INTEGER,
    confidence REAL DEFAULT 0.8, created_at TEXT DEFAULT (datetime('now')),
    expires_at TEXT, last_confirmed TEXT,
    relation_reason TEXT DEFAULT 'unknown',
    superseded_by_relation_id INTEGER, superseded_at INTEGER,
    superseded_reason TEXT, extraction_method TEXT,
    FOREIGN KEY (source_entity_id) REFERENCES kg_entities(id),
    FOREIGN KEY (target_entity_id) REFERENCES kg_entities(id));
SQL

echo "[BATCH $BATCH] === Step 2: spawn isolated nox-mem api-server ==="
cd /root/.openclaw/workspace/tools/nox-mem
nohup node --no-warnings dist/api-server.js > "$RUN_DIR/api.log" 2>&1 &
API_PID=$!
echo "[BATCH $BATCH] api pid=$API_PID, waiting 5s for boot..."
sleep 5

# Verify api alive + pointing at isolated DB
HEALTH=$(curl -s --max-time 10 "$NOX_API_BASE/api/health" || true)
if ! echo "$HEALTH" | grep -q '"chunks"'; then
    echo "[BATCH $BATCH] ERROR: api not responding"
    echo "$HEALTH" | head -c 300
    exit 1
fi
echo "[BATCH $BATCH] api health: $(echo "$HEALTH" | head -c 200)"

echo "[BATCH $BATCH] === Step 3: run Add stage ==="
cd "$EVAL"
python -m eval.cli \
    --dataset "dataset/$BATCH/dialogue.json" \
    --system nox_mem \
    --user-id "$BATCH" \
    --stages add \
    > "$RUN_DIR/add.log" 2>&1

ADD_HEALTH=$(curl -s "$NOX_API_BASE/api/health")
echo "[BATCH $BATCH] post-add health: $(echo "$ADD_HEALTH" | head -c 300)"

echo "[BATCH $BATCH] === Step 4: vectorize ==="
NOX_DB_PATH="$NOX_DB_PATH" "$NOX_MEM_BIN" vectorize > "$RUN_DIR/vectorize.log" 2>&1 || true
VEC_HEALTH=$(curl -s "$NOX_API_BASE/api/health")
echo "[BATCH $BATCH] post-vectorize coverage: $(echo "$VEC_HEALTH" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("vectorCoverage",{}))')"

echo "[BATCH $BATCH] === Step 5: Search + Answer + Evaluate ==="
python -m eval.cli \
    --dataset "dataset/$BATCH/dialogue.json" \
    --qa "dataset/$BATCH/qa_$BATCH.json" \
    --system nox_mem \
    --user-id "$BATCH" \
    --stages search answer evaluate \
    --top-k 20 \
    > "$RUN_DIR/eval.log" 2>&1

echo "[BATCH $BATCH] === Step 6: Analyze ==="
RESULTS_FILE="eval/results/nox_mem/evaluation_results_$BATCH.json"
if [ -f "$RESULTS_FILE" ]; then
    python tools/analyze_results.py "$RESULTS_FILE" > "$RUN_DIR/analysis.txt" 2>&1 || true
    cp "$RESULTS_FILE" "$RUN_DIR/results-batch-$BATCH.json"
    echo "[BATCH $BATCH] results -> $RUN_DIR/results-batch-$BATCH.json"
else
    echo "[BATCH $BATCH] ERROR: no results file at $RESULTS_FILE"
    ls eval/results/ 2>&1 || true
fi

echo "[BATCH $BATCH] === DONE ==="
ls -la "$RUN_DIR/"
