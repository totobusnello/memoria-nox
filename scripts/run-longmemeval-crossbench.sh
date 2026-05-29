#!/usr/bin/env bash
# run-longmemeval-crossbench.sh — orchestrate LongMemEval n=300 cross-bench
# validation on the VPS, fully isolated from production.
#
# Constraints (enforced):
#   - NEVER touches prod nox-mem.db (port 18802)
#   - Uses /tmp/longmemeval-<uuid> as workdir
#   - Isolated port 18835 for the eval API server
#   - Phase D config: top_k=20, rerank OFF, hybrid ON
#   - Re-exports NOX_RERANKER_ENABLED=0 AFTER .env source (anti-rerank-ON regression)
#   - Preflight: OpenAI gpt-4.1-mini + Gemini gemini-2.5-flash auth check
#   - Budget: $5 cap (~$2-4 expected for n=300)
#
# Usage (VPS):
#   bash run-longmemeval-crossbench.sh [n=300] [split=oracle]
#
# Output files (in WORKDIR):
#   data/longmemeval_<split>.json       (downloaded once, sha256-pinned)
#   work/                                (per-q DB scratch, auto-cleaned)
#   results.jsonl                        (per-q retrieval + optional gen output)
#   aggregate.json                       (full metrics aggregate)
#   summary.md                           (human-readable table)

set -euo pipefail

# Defaults
N="${1:-300}"
SPLIT="${2:-oracle}"
TOP_K="${TOP_K:-20}"
PORT="${PORT:-18835}"
TASK_ACC="${TASK_ACC:-1}"   # 1=on (cross-backbone gpt-4.1-mini), 0=off
GENERATOR="${GENERATOR:-gpt-4.1-mini}"
JUDGE="${JUDGE:-gemini-2.5-flash}"

# Bootstrap env: source .env, then RE-EXPORT the overrides
set -a
# shellcheck disable=SC1091
source /root/.openclaw/.env
set +a
export NOX_RERANKER_ENABLED=0
export NOX_API_PORT="$PORT"
export NOX_MEM_BIN="${NOX_MEM_BIN:-nox-mem}"

# Sanity
test -n "${GEMINI_API_KEY:-}" || { echo "FATAL: GEMINI_API_KEY missing" >&2; exit 1; }
if [[ "$TASK_ACC" == "1" ]]; then
    test -n "${OPENAI_API_KEY:-}" || { echo "FATAL: OPENAI_API_KEY missing for --task-accuracy" >&2; exit 1; }
fi
if [[ "$PORT" == "18802" ]]; then
    echo "FATAL: refuse to use prod port 18802" >&2; exit 1
fi

# Workdir — must be under /root/.openclaw/ to satisfy op-audit ALLOWED_PREFIXES
# (P1 safety guard, dist/lib/op-audit.js line 75 — NOX_DB_PATH allowlist).
RUN_UUID="$(cat /proc/sys/kernel/random/uuid)"
WORKDIR_ROOT="${WORKDIR_ROOT:-/root/.openclaw/eval}"
WORKDIR="${WORKDIR_ROOT}/longmemeval-${RUN_UUID}"
mkdir -p "$WORKDIR/data" "$WORKDIR/work"
echo "[run] WORKDIR=$WORKDIR"
echo "[run] N=$N SPLIT=$SPLIT TOP_K=$TOP_K PORT=$PORT TASK_ACC=$TASK_ACC GEN=$GENERATOR JUDGE=$JUDGE"

# Locate harness files (must be in same dir as this script's parent)
HARNESS_DIR="${HARNESS_DIR:-/root/.openclaw/workspace/tools/nox-mem/eval/longmemeval}"
test -f "$HARNESS_DIR/run_crossbench.py" || {
    echo "FATAL: harness not found at $HARNESS_DIR — set HARNESS_DIR env var" >&2
    exit 1
}

# 1) Dataset (download once)
DATA_FILE="$WORKDIR/data/longmemeval_${SPLIT}.json"
if [[ ! -f "$DATA_FILE" ]]; then
    echo "[run] downloading $SPLIT split..."
    cd "$HARNESS_DIR"
    # Use the existing TS downloader; it writes to $HARNESS_DIR/data/
    npx --yes tsx download.ts --split "$SPLIT" 2>&1 | tail -10
    cp "$HARNESS_DIR/data/longmemeval_${SPLIT}.json" "$DATA_FILE" 2>/dev/null || {
        # Direct HF download as fallback
        echo "[run] tsx download failed; trying direct HF download" >&2
        python3 -c "
import urllib.request, json
url='https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/98d7416c24c778c2fee6e6f3006e7a073259d48f/longmemeval_${SPLIT}.json'
urllib.request.urlretrieve(url, '$DATA_FILE')
print('downloaded:', len(json.load(open('$DATA_FILE'))), 'records')
"
    }
fi
test -f "$DATA_FILE" || { echo "FATAL: dataset $DATA_FILE missing" >&2; exit 1; }
RECORD_COUNT="$(python3 -c "import json; print(len(json.load(open('$DATA_FILE'))))")"
echo "[run] dataset records: $RECORD_COUNT"

# 2) Preflight billing
echo "[preflight] OpenAI gpt-4.1-mini..."
curl -sS -m 30 https://api.openai.com/v1/chat/completions \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"model":"gpt-4.1-mini","max_tokens":3,"messages":[{"role":"user","content":"ok"}]}' \
    | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('choices'), d; print('  ok:', d['choices'][0]['message']['content'])" \
    || { echo "FATAL: OpenAI preflight failed" >&2; exit 1; }

echo "[preflight] Gemini ${JUDGE}..."
curl -sS -m 30 "https://generativelanguage.googleapis.com/v1beta/models/${JUDGE}:generateContent?key=${GEMINI_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"contents":[{"role":"user","parts":[{"text":"ok"}]}],"generationConfig":{"maxOutputTokens":3}}' \
    | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('candidates'), d; print('  ok')" \
    || { echo "FATAL: Gemini preflight failed" >&2; exit 1; }

# 3) Ensure no stale process on $PORT
if ss -lnt | awk '{print $4}' | grep -qE ":${PORT}\$"; then
    echo "[run] WARN: port $PORT busy; attempting cleanup..."
    pkill -f "NOX_API_PORT=${PORT}" 2>/dev/null || true
    sleep 2
    if ss -lnt | awk '{print $4}' | grep -qE ":${PORT}\$"; then
        echo "FATAL: port $PORT still busy after cleanup" >&2; exit 1
    fi
fi

# 4) Run harness
RESULTS="$WORKDIR/results.jsonl"
echo "[run] launching harness → $RESULTS"
TASK_FLAGS=()
if [[ "$TASK_ACC" == "1" ]]; then
    TASK_FLAGS=(--task-accuracy --generator "$GENERATOR")
fi
python3 "$HARNESS_DIR/run_crossbench.py" \
    --split-path "$DATA_FILE" \
    --n "$N" \
    --seed 42 \
    --top-k "$TOP_K" \
    --api-port "$PORT" \
    --workdir "$WORKDIR/work" \
    --out "$RESULTS" \
    "${TASK_FLAGS[@]}" \
    2>&1 | tee "$WORKDIR/run.log" | tail -200

# 5) Score
echo "[score] computing aggregate..."
SCORE_FLAGS=()
if [[ "$TASK_ACC" == "1" ]]; then
    SCORE_FLAGS=(--task-accuracy --judge-model "$JUDGE")
fi
python3 "$HARNESS_DIR/score_crossbench.py" \
    "$RESULTS" \
    --top-k 10 \
    --out "$WORKDIR/aggregate.json" \
    --md-out "$WORKDIR/summary.md" \
    "${SCORE_FLAGS[@]}"

echo ""
echo "===================="
echo "[done] artifacts at $WORKDIR:"
ls -la "$WORKDIR"
echo "===================="
cat "$WORKDIR/summary.md"
