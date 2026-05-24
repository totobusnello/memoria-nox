#!/usr/bin/env bash
# Path A2 — full pipeline runner.
#
# Steps:
#   1. (idempotent) summarize the LoCoMo + LongMemEval corpus via Gemini Flash Lite.
#   2. Setup the nox_mem_a2 adapter (ingest summarized corpus into hybrid DB).
#   3. Run capped@500 benchmark on dry-run-sample queries.
#   4. Compare A2 vs baseline #338 (hybrid full) vs mem0@500 and write
#      staged-q4-a2/RESULTS.md.
#
# Pre-reqs (one-time):
#   python3 -m venv .venv && source .venv/bin/activate
#   pip install requests google-generativeai sqlite-vec PyYAML
#   set -a; source /tmp/q4-gemini-env.sh; set +a
#
# Usage:
#   bash eval/q4-comparison/run-a2-summarizer.sh [TEMPLATE]
#
# TEMPLATE defaults to "A" (atomic facts). Other choices: "B" or "C".
#
# Cost guardrail: chunk_summarizer enforces a $5 hard cap internally.
# For Toto: the full corpus run consumes ~$0.43 worst case (6830 chunks).

set -euo pipefail
shopt -s nullglob

TEMPLATE="${1:-A}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

if [[ -z "${GEMINI_API_KEY:-}" ]]; then
  echo "ERROR: GEMINI_API_KEY not set. Run:"
  echo "  set -a; source /tmp/q4-gemini-env.sh; set +a"
  exit 1
fi

SUMM_OUT="cache/summarized-${TEMPLATE}.jsonl"
SUMM_COST="cache/summarized-${TEMPLATE}-cost.jsonl"
A2_DB="cache/nox-mem-a2-${TEMPLATE}.db"

export NOX_A2_SUMMARIZED_PATH="$HERE/$SUMM_OUT"
export NOX_A2_DB_PATH="$HERE/$A2_DB"

echo "[run-a2] template=${TEMPLATE}"
echo "[run-a2] summarized JSONL: $SUMM_OUT"
echo "[run-a2] A2 DB:           $A2_DB"

# ---------------------------------------------------------------------------
# Step 1 — summarize (idempotent; resumes from prior state if interrupted)
# ---------------------------------------------------------------------------

echo "[run-a2] step 1/3 — summarize (resumable)..."
python3 -m lib.chunk_summarizer summarize \
  --template "$TEMPLATE" \
  --output "$SUMM_OUT" \
  --cost-log "$SUMM_COST" \
  --concurrency 15

echo "[run-a2] summarization done. cost log:"
tail -5 "$SUMM_COST" || true

# ---------------------------------------------------------------------------
# Step 2 — run capped@500 + full benchmark
# ---------------------------------------------------------------------------

echo "[run-a2] step 2/3 — benchmark adapter nox_mem_a2..."
python3 run-a2-benchmark.py --template "$TEMPLATE"

# ---------------------------------------------------------------------------
# Step 3 — already done by step 2 (writes staged-q4-a2/RESULTS.md)
# ---------------------------------------------------------------------------

echo "[run-a2] done. See staged-q4-a2/RESULTS.md"
