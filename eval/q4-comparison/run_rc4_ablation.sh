#!/usr/bin/env bash
# rc4 task-type ablation (§6.3.2 confound (d)).
# Re-runs nox-mem with a GENERIC Gemini embedding (no RETRIEVAL_DOCUMENT/QUERY
# task_type), matching how mem0's embedder is called. If nox-mem still beats
# mem0 here, the task-type asymmetry does not explain the rc4 inversion.
# nox-mem (generic) is compared against the SAME mem0 run from rc4 (which also
# does not set task_type) — a symmetric "neither sets task_type" comparison.
set -uo pipefail
cd "$(dirname "$0")"

OUT="${1:-output/rc4-ablation}"
QUERIES="cache/queries-rc4-all.jsonl"
PY=.venv/bin/python

set -a; . ./.env.local; set +a
export GOOGLE_API_KEY="${GEMINI_API_KEY:?GEMINI_API_KEY missing in .env.local}"
export NOX_EVAL_MODE=hybrid
export NOX_EMBED_GENERIC_TASKTYPE=1                      # the ablation switch
export NOX_HYBRID_DB_PATH="$PWD/cache/rc4-nox-generic.db"
export MEM0_SKIP_LLM_EXTRACTION=1 MEM0_TELEMETRY=False ANONYMIZED_TELEMETRY=False

echo "[ablation] $(date '+%F %T') START — nox-mem GENERIC task-type, n=$(wc -l < "$QUERIES" | tr -d ' ')"

rm -rf "$OUT"; mkdir -p "$OUT"
rm -f cache/rc4-nox-generic.db cache/rc4-nox-generic.db-wal cache/rc4-nox-generic.db-shm

# nox-mem with generic embedding (fresh ingest at 3072d, then answer both datasets)
$PY runner_rc4.py --systems nox_mem --datasets all \
  --queries-file "$QUERIES" --output "$OUT" --limit 100000 --k 10
echo "[ablation] nox-mem (generic) exit=$?  $(date '+%T')"

# Reuse the rc4 mem0 result (mem0 likewise sets no task_type) as the baseline.
if [ -f output/rc4/mem0.json ]; then cp output/rc4/mem0.json "$OUT/mem0.json"; fi

$PY aggregate.py --output-dir "$OUT" --k 10
echo "[ablation] $(date '+%F %T') DONE — $OUT/ (nox generic vs mem0)"
