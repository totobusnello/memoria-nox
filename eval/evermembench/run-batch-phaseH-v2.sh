#!/bin/bash
# Phase H v2 — EverMemBench GPT-4.1-mini parity batch 004 (OpenAI direct route).
#
# Differs from v1 (PR #368):
#   - Uses OPENAI_API_KEY direct (NOT OpenRouter — credit zero em v1)
#   - Toto rotated key, verified working (curl /v1/models + /v1/chat/completions both pass)
#   - Preflight: actual gpt-4.1-mini completion (1 token, ~$0.0001) NOT just /v1/models list
#     Lesson v1: auth check ≠ billing check; v1 OpenRouter passed auth but 402 on real batch
#
# Usage:
#   WORK=/tmp/phaseH-batch004-v2-<uuid> ./run-batch-phaseH-v2.sh 004 18820
set -uo pipefail

BATCH="${1:?usage: $0 <BATCH> <PORT>}"
PORT="${2:?usage: $0 <BATCH> <PORT>}"
WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
RUN_DIR="/root/.openclaw/evermembench-runs/phaseH-v2-$BATCH-$(date +%s)"
mkdir -p "$RUN_DIR"
echo "[PHASE-H-v2 BATCH $BATCH PORT $PORT] RUN_DIR=$RUN_DIR"

# Source prod env to get OPENAI_API_KEY + GEMINI_API_KEY (but DO NOT clobber NOX_DB_PATH)
set -a; source /root/.openclaw/.env; set +a

# Activate venv (python deps)
source /root/.openclaw/evermembench-phaseB-1779978778/venv/bin/activate
echo "[PHASE-H-v2] venv python: $(which python)"

# Re-export AFTER source per [[evermembench-eval-gotchas-2026-05-28]]:
# Isolate Phase H from Phase G rerank state.
export NOX_RERANKER_ENABLED=0
unset NOX_RERANKER_MODEL || true

# LLM_API_KEY just satisfies cli.py presence check (line 379). Actual
# OpenAI/Gemini routing is done via per-stage api_key in pipeline.yaml.
export LLM_API_KEY="$GEMINI_API_KEY"
export LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"

# Verify both keys are present
if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "[PHASE-H-v2] ERROR: OPENAI_API_KEY not present in /root/.openclaw/.env"
    exit 1
fi
if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "[PHASE-H-v2] ERROR: GEMINI_API_KEY not present in /root/.openclaw/.env"
    exit 1
fi
echo "[PHASE-H-v2] OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}...${OPENAI_API_KEY: -4} (len ${#OPENAI_API_KEY})"
echo "[PHASE-H-v2] GEMINI_API_KEY: present (len ${#GEMINI_API_KEY})"

# Live preflight: REAL completion (not just /v1/models list).
# v1 lesson: OpenRouter /v1/models returned auth OK but real chat call 402'd on credits.
# A small completion (1 token, ~$0.0001) exercises the billing path end-to-end.
echo "[PHASE-H-v2] === Preflight: gpt-4.1-mini completion (verify billing path) ==="
PREFLIGHT=$(curl -s --max-time 30 https://api.openai.com/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -d '{"model":"gpt-4.1-mini","messages":[{"role":"user","content":"Reply only OK"}],"max_tokens":5,"temperature":0}')
if ! echo "$PREFLIGHT" | grep -q '"OK"'; then
    echo "[PHASE-H-v2] ERROR: OpenAI preflight failed (auth OR billing)"
    echo "$PREFLIGHT" | head -c 600
    exit 1
fi
PREFLIGHT_TOKENS=$(echo "$PREFLIGHT" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("usage",{}).get("total_tokens","?"))')
echo "[PHASE-H-v2] OpenAI preflight OK (gpt-4.1-mini billing path verified, total_tokens=$PREFLIGHT_TOKENS)"

# Isolated DB path (op-audit allows /root/.openclaw/ prefix)
export NOX_DB_PATH="$RUN_DIR/nox-mem.db"
export NOX_API_PORT="$PORT"
export NOX_API_BASE="http://127.0.0.1:$PORT"
export NOX_ADAPTER_MODE="${NOX_ADAPTER_MODE:-phaseB}"
export NOX_MEM_BIN="$(which nox-mem)"

echo "[PHASE-H-v2] NOX_DB_PATH=$NOX_DB_PATH"
echo "[PHASE-H-v2] NOX_ADAPTER_MODE=$NOX_ADAPTER_MODE"
echo "[PHASE-H-v2] NOX_RERANKER_ENABLED=$NOX_RERANKER_ENABLED (NOX_RERANKER_MODEL set=$(env | grep -c NOX_RERANKER_MODEL))"

# Cleanup hook (cleanup_v2 set after pipeline swap below)
API_PID=""

echo "[PHASE-H-v2 BATCH $BATCH] === Step 1: init fresh DB schema ==="
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

echo "[PHASE-H-v2 BATCH $BATCH] === Step 2: spawn isolated nox-mem api-server ==="
cd /root/.openclaw/workspace/tools/nox-mem
nohup node --no-warnings dist/api-server.js > "$RUN_DIR/api.log" 2>&1 &
API_PID=$!
echo "[PHASE-H-v2 BATCH $BATCH] api pid=$API_PID, waiting 5s for boot..."
sleep 5

# Verify api alive + pointing at isolated DB
HEALTH=$(curl -s --max-time 10 "$NOX_API_BASE/api/health" || true)
if ! echo "$HEALTH" | grep -q '"chunks"'; then
    echo "[PHASE-H-v2 BATCH $BATCH] ERROR: api not responding"
    echo "$HEALTH" | head -c 300
    exit 1
fi
INITIAL_CHUNKS=$(echo "$HEALTH" | python3 -c 'import json,sys;d=json.load(sys.stdin);c=d.get("chunks",{});print(c.get("total") if isinstance(c,dict) else c)')
echo "[PHASE-H-v2 BATCH $BATCH] api health: chunks=$INITIAL_CHUNKS"
if [ "$INITIAL_CHUNKS" != "0" ]; then
    echo "[PHASE-H-v2 BATCH $BATCH] ERROR: expected empty DB, got chunks=$INITIAL_CHUNKS — wrong DB?"
    exit 1
fi

echo "[PHASE-H-v2 BATCH $BATCH] === Step 2b: preflight verify rerank OFF + smoke /api/search ==="
SEARCH_TEST=$(curl -s --max-time 10 "$NOX_API_BASE/api/search?q=test&topK=3" || true)
echo "[PHASE-H-v2 BATCH $BATCH] preflight search: $(echo "$SEARCH_TEST" | head -c 200)"

echo "[PHASE-H-v2 BATCH $BATCH] === Step 2c: swap pipeline.yaml -> phaseH v2 (OpenAI direct) ==="
PIPELINE_CFG="$EVAL/eval/config/pipeline.yaml"
PIPELINE_BAK="$RUN_DIR/pipeline.yaml.bak"
cp "$PIPELINE_CFG" "$PIPELINE_BAK"
cp "$WORK/phaseH-pipeline-v2.yaml" "$PIPELINE_CFG"
echo "[PHASE-H-v2 BATCH $BATCH] backed up original -> $PIPELINE_BAK"
echo "[PHASE-H-v2 BATCH $BATCH] active pipeline.yaml answer.model = $(grep -A1 '^answer:' $PIPELINE_CFG | tail -1 | tr -d ' ')"

# Restore hook (extends cleanup)
restore_pipeline() {
    if [ -f "$PIPELINE_BAK" ]; then
        cp "$PIPELINE_BAK" "$PIPELINE_CFG"
        echo "[PHASE-H-v2 BATCH $BATCH] restored original pipeline.yaml"
    fi
}
cleanup_v2() {
    restore_pipeline
    if [ -n "$API_PID" ]; then
        kill "$API_PID" 2>/dev/null || true
        wait "$API_PID" 2>/dev/null || true
        echo "[PHASE-H-v2 BATCH $BATCH] killed api server pid=$API_PID"
    fi
}
trap cleanup_v2 EXIT

echo "[PHASE-H-v2 BATCH $BATCH] === Step 3: run Add stage ==="
cd "$EVAL"
python -m eval.cli \
    --dataset "dataset/$BATCH/dialogue.json" \
    --system nox_mem \
    --user-id "$BATCH" \
    --stages add \
    > "$RUN_DIR/add.log" 2>&1

ADD_HEALTH=$(curl -s "$NOX_API_BASE/api/health")
echo "[PHASE-H-v2 BATCH $BATCH] post-add: $(echo "$ADD_HEALTH" | head -c 300)"

echo "[PHASE-H-v2 BATCH $BATCH] === Step 4: vectorize ==="
NOX_DB_PATH="$NOX_DB_PATH" "$NOX_MEM_BIN" vectorize > "$RUN_DIR/vectorize.log" 2>&1 || true
VEC_HEALTH=$(curl -s "$NOX_API_BASE/api/health")
echo "[PHASE-H-v2 BATCH $BATCH] post-vectorize coverage: $(echo "$VEC_HEALTH" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("vectorCoverage",{}))')"

# Clear any leftover Phase D/F/G/H-v1 results that would short-circuit the harness
RESULTS_DIR="$EVAL/eval/results/nox_mem"
rm -f "$RESULTS_DIR/answer_results_$BATCH.json" "$RESULTS_DIR/evaluation_results_$BATCH.json" "$RESULTS_DIR/search_results_$BATCH.json"
echo "[PHASE-H-v2 BATCH $BATCH] cleared stale results files in $RESULTS_DIR"

echo "[PHASE-H-v2 BATCH $BATCH] === Step 5: Search + Answer + Evaluate ==="
python -m eval.cli \
    --dataset "dataset/$BATCH/dialogue.json" \
    --qa "dataset/$BATCH/qa_$BATCH.json" \
    --system nox_mem \
    --user-id "$BATCH" \
    --stages search answer evaluate \
    --top-k 20 \
    > "$RUN_DIR/eval.log" 2>&1

echo "[PHASE-H-v2 BATCH $BATCH] === Step 6: Analyze ==="
RESULTS_FILE="$RESULTS_DIR/evaluation_results_$BATCH.json"
if [ -f "$RESULTS_FILE" ]; then
    python tools/analyze_results.py "$RESULTS_FILE" > "$RUN_DIR/analysis.txt" 2>&1 || true
    cp "$RESULTS_FILE" "$RUN_DIR/results-batch-$BATCH.json"
    cp "$RESULTS_DIR/answer_results_$BATCH.json" "$RUN_DIR/answer-results-batch-$BATCH.json" 2>/dev/null || true
    echo "[PHASE-H-v2 BATCH $BATCH] results -> $RUN_DIR/results-batch-$BATCH.json"
else
    echo "[PHASE-H-v2 BATCH $BATCH] ERROR: no results file at $RESULTS_FILE"
    ls "$RESULTS_DIR" 2>&1 || true
fi

echo "[PHASE-H-v2 BATCH $BATCH] === DONE ==="
ls -la "$RUN_DIR/"
