#!/usr/bin/env bash
# rc4 all-Gemini fair comparison — FULL run (n=2482: locomo 1982 + lme 500).
# Both systems on gemini-embedding-001 @ 3072d. One process per system
# (thread-leak isolation for mem0); each ingests the full corpus once and
# answers BOTH datasets in a single pass (dataset comes from each query row).
set -uo pipefail
cd "$(dirname "$0")"

OUT="${1:-output/rc4}"
QUERIES="cache/queries-rc4-all.jsonl"
PY=.venv/bin/python

# --- env (key loaded from gitignored .env.local; never printed) ---
set -a; . ./.env.local; set +a
export GOOGLE_API_KEY="${GEMINI_API_KEY:?GEMINI_API_KEY missing in .env.local}"
export NOX_EVAL_MODE=hybrid
export NOX_HYBRID_DB_PATH="$PWD/cache/rc4-nox-hybrid.db"
export MEM0_CHROMA_PATH="$PWD/.mem0-chroma-rc4"
export MEM0_SKIP_LLM_EXTRACTION=1 MEM0_TELEMETRY=False ANONYMIZED_TELEMETRY=False

echo "[rc4] $(date '+%F %T') START — n_queries=$(wc -l < "$QUERIES" | tr -d ' '), dim=3072"

# --- fresh state (reproducible run) ---
rm -rf "$OUT"; mkdir -p "$OUT"
rm -f cache/rc4-nox-hybrid.db cache/rc4-nox-hybrid.db-wal cache/rc4-nox-hybrid.db-shm
rm -rf "$MEM0_CHROMA_PATH"

# --- nox-mem (hybrid: FTS5 + Gemini dense + RRF) ---
echo "[rc4] === NOX-MEM $(date '+%T') (ingest both + answer both) ==="
$PY runner_rc4.py --systems nox_mem --datasets all \
  --queries-file "$QUERIES" --output "$OUT" --limit 100000 --k 10
echo "[rc4] nox-mem exit=$?  $(date '+%T')"

# --- mem0 (Gemini embedder, chroma, separate process) ---
echo "[rc4] === MEM0 $(date '+%T') (ingest both + answer both) ==="
$PY runner_rc4.py --systems mem0 --datasets all \
  --queries-file "$QUERIES" --output "$OUT" --limit 100000 --k 10
echo "[rc4] mem0 exit=$?  $(date '+%T')"

# --- aggregate (per-dataset + per-category from row dataset/category) ---
echo "[rc4] === AGGREGATE $(date '+%T') ==="
$PY aggregate.py --output-dir "$OUT" --k 10

echo "[rc4] $(date '+%F %T') DONE — outputs in $OUT/ (_aggregate.json/.md)"
