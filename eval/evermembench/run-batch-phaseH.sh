#!/bin/bash
# Phase H — EverMemBench GPT-4.1-mini parity batch 004.
#
# Differs from run-batch-phaseD.sh:
#   - LLM_API_KEY routes to GEMINI for the LLM_API_KEY-presence cli check, but
#     actual answer/evaluate calls use the per-stage YAML api_key (answer ->
#     OPENAI_API_KEY, evaluate -> GEMINI_API_KEY).
#   - NOX_RERANKER_ENABLED=0 + unset NOX_RERANKER_MODEL: isolate from Phase G.
#   - Port 18820 (Phase G used 18816-18819).
#
# Usage:
#   WORK=/tmp/phaseH-batch004-<uuid> ./run-batch-phaseH.sh 004 18820
set -uo pipefail

BATCH="${1:?usage: $0 <BATCH> <PORT>}"
PORT="${2:?usage: $0 <BATCH> <PORT>}"
WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
RUN_DIR="/root/.openclaw/evermembench-runs/phaseH-$BATCH-$(date +%s)"
mkdir -p "$RUN_DIR"
echo "[PHASE-H BATCH $BATCH PORT $PORT] RUN_DIR=$RUN_DIR"

# Source prod env to get GEMINI_API_KEY + OPENAI_API_KEY (but DO NOT clobber NOX_DB_PATH)
set -a; source /root/.openclaw/.env; set +a

# Re-export AFTER source per [[evermembench-eval-gotchas-2026-05-28]]:
# Isolate Phase H from Phase G rerank state.
export NOX_RERANKER_ENABLED=0
unset NOX_RERANKER_MODEL || true

# LLM_API_KEY just satisfies cli.py presence check (line 379). Actual
# OpenAI/Gemini routing is done via per-stage api_key in pipeline.yaml.
export LLM_API_KEY="$GEMINI_API_KEY"
export LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"

# Verify both keys are present
# NOTE: Direct OPENAI_API_KEY in .env is invalid (401 from api.openai.com); routing via
# OPENROUTER_API_KEY -> openai/gpt-4.1-mini (Azure provider) per MemOS paper methodology.
if [ -z "${OPENROUTER_API_KEY:-}" ]; then
    echo "[PHASE-H] ERROR: OPENROUTER_API_KEY not present in /root/.openclaw/.env"
    exit 1
fi
if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "[PHASE-H] ERROR: GEMINI_API_KEY not present in /root/.openclaw/.env"
    exit 1
fi
echo "[PHASE-H] OPENROUTER_API_KEY: ${OPENROUTER_API_KEY:0:10}...${OPENROUTER_API_KEY: -4} (len ${#OPENROUTER_API_KEY})"
echo "[PHASE-H] GEMINI_API_KEY: present (len ${#GEMINI_API_KEY})"

# Live preflight: confirm OpenRouter routing for gpt-4.1-mini works (sanity, ~$0.00001)
PREFLIGHT=$(curl -s --max-time 30 https://openrouter.ai/api/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENROUTER_API_KEY" \
    -d '{"model":"openai/gpt-4.1-mini","messages":[{"role":"user","content":"Reply only OK"}],"max_tokens":20}')
if ! echo "$PREFLIGHT" | grep -q '"OK"'; then
    echo "[PHASE-H] ERROR: OpenRouter preflight failed"
    echo "$PREFLIGHT" | head -c 600
    exit 1
fi
echo "[PHASE-H] OpenRouter preflight OK"

# Isolated DB path (op-audit allows /root/.openclaw/ prefix)
export NOX_DB_PATH="$RUN_DIR/nox-mem.db"
export NOX_API_PORT="$PORT"
export NOX_API_BASE="http://127.0.0.1:$PORT"
export NOX_ADAPTER_MODE="${NOX_ADAPTER_MODE:-phaseB}"
export NOX_MEM_BIN="$(which nox-mem)"

echo "[PHASE-H] NOX_DB_PATH=$NOX_DB_PATH"
echo "[PHASE-H] NOX_ADAPTER_MODE=$NOX_ADAPTER_MODE"
echo "[PHASE-H] NOX_RERANKER_ENABLED=$NOX_RERANKER_ENABLED (unset=$(env | grep -c NOX_RERANKER_MODEL))"

# Cleanup hook
API_PID=""
cleanup() {
    if [ -n "$API_PID" ]; then
        kill "$API_PID" 2>/dev/null || true
        wait "$API_PID" 2>/dev/null || true
        echo "[PHASE-H BATCH $BATCH] killed api server pid=$API_PID"
    fi
}
trap cleanup EXIT

echo "[PHASE-H BATCH $BATCH] === Step 1: init fresh DB schema ==="
"$NOX_MEM_BIN" stats > "$RUN_DIR/init-stats.log" 2>&1 || true

# Apply v18 + KG schema patch (RUN-VPS gotcha #3)
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

echo "[PHASE-H BATCH $BATCH] === Step 2: spawn isolated nox-mem api-server ==="
cd /root/.openclaw/workspace/tools/nox-mem
nohup node --no-warnings dist/api-server.js > "$RUN_DIR/api.log" 2>&1 &
API_PID=$!
echo "[PHASE-H BATCH $BATCH] api pid=$API_PID, waiting 5s for boot..."
sleep 5

# Verify api alive + pointing at isolated DB
HEALTH=$(curl -s --max-time 10 "$NOX_API_BASE/api/health" || true)
if ! echo "$HEALTH" | grep -q '"chunks"'; then
    echo "[PHASE-H BATCH $BATCH] ERROR: api not responding"
    echo "$HEALTH" | head -c 300
    exit 1
fi
INITIAL_CHUNKS=$(echo "$HEALTH" | python3 -c 'import json,sys;d=json.load(sys.stdin);c=d.get("chunks",{});print(c.get("total") if isinstance(c,dict) else c)')
echo "[PHASE-H BATCH $BATCH] api health: chunks=$INITIAL_CHUNKS"
if [ "$INITIAL_CHUNKS" != "0" ]; then
    echo "[PHASE-H BATCH $BATCH] ERROR: expected empty DB, got chunks=$INITIAL_CHUNKS — wrong DB?"
    exit 1
fi

echo "[PHASE-H BATCH $BATCH] === Step 2b: preflight verify rerank OFF + smoke /api/search ==="
SEARCH_TEST=$(curl -s --max-time 10 "$NOX_API_BASE/api/search?q=test&topK=3" || true)
echo "[PHASE-H BATCH $BATCH] preflight search: $(echo "$SEARCH_TEST" | head -c 200)"

echo "[PHASE-H BATCH $BATCH] === Step 3: run Add stage ==="
cd "$EVAL"
python -m eval.cli \
    --dataset "dataset/$BATCH/dialogue.json" \
    --system nox_mem \
    --user-id "$BATCH" \
    --stages add \
    > "$RUN_DIR/add.log" 2>&1

ADD_HEALTH=$(curl -s "$NOX_API_BASE/api/health")
echo "[PHASE-H BATCH $BATCH] post-add: $(echo "$ADD_HEALTH" | head -c 300)"

echo "[PHASE-H BATCH $BATCH] === Step 4: vectorize ==="
NOX_DB_PATH="$NOX_DB_PATH" "$NOX_MEM_BIN" vectorize > "$RUN_DIR/vectorize.log" 2>&1 || true
VEC_HEALTH=$(curl -s "$NOX_API_BASE/api/health")
echo "[PHASE-H BATCH $BATCH] post-vectorize coverage: $(echo "$VEC_HEALTH" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("vectorCoverage",{}))')"

# Clear any leftover Phase D/F/G results that would short-circuit the harness
RESULTS_DIR="$EVAL/eval/results/nox_mem"
rm -f "$RESULTS_DIR/answer_results_$BATCH.json" "$RESULTS_DIR/evaluation_results_$BATCH.json" "$RESULTS_DIR/search_results_$BATCH.json"
echo "[PHASE-H BATCH $BATCH] cleared stale results files in $RESULTS_DIR"

echo "[PHASE-H BATCH $BATCH] === Step 5: Search + Answer + Evaluate ==="
python -m eval.cli \
    --dataset "dataset/$BATCH/dialogue.json" \
    --qa "dataset/$BATCH/qa_$BATCH.json" \
    --system nox_mem \
    --user-id "$BATCH" \
    --stages search answer evaluate \
    --top-k 20 \
    > "$RUN_DIR/eval.log" 2>&1

echo "[PHASE-H BATCH $BATCH] === Step 6: Analyze ==="
RESULTS_FILE="$RESULTS_DIR/evaluation_results_$BATCH.json"
if [ -f "$RESULTS_FILE" ]; then
    python tools/analyze_results.py "$RESULTS_FILE" > "$RUN_DIR/analysis.txt" 2>&1 || true
    cp "$RESULTS_FILE" "$RUN_DIR/results-batch-$BATCH.json"
    cp "$RESULTS_DIR/answer_results_$BATCH.json" "$RUN_DIR/answer-results-batch-$BATCH.json" 2>/dev/null || true
    echo "[PHASE-H BATCH $BATCH] results -> $RUN_DIR/results-batch-$BATCH.json"
else
    echo "[PHASE-H BATCH $BATCH] ERROR: no results file at $RESULTS_FILE"
    ls "$RESULTS_DIR" 2>&1 || true
fi

echo "[PHASE-H BATCH $BATCH] === DONE ==="
ls -la "$RUN_DIR/"
