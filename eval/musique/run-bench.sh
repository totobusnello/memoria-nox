#!/usr/bin/env bash
# run-bench.sh — orchestrate MuSiQue bench evaluation on the VPS.
#
# Steps:
#   1. Ensure dataset present (download via gdown to /tmp/musique-repo/data/).
#   2. Validate corpus_loader self-test (verifies ~2417 musique_ans dev qs).
#   3. Source /root/.openclaw/.env (mandatory per CLAUDE.md rule).
#   4. Preflight OpenAI billing + Gemini embed paths.
#   5. Run adapter (default: 100 q stratified smoke).
#   6. Aggregate + write RESULTS-MUSIQUE.{md,json}.
#
# Usage:
#   bash eval/musique/run-bench.sh smoke         # 100 q stratified
#   bash eval/musique/run-bench.sh full          # full musique_ans dev (~2417)
#   bash eval/musique/run-bench.sh subset 500    # custom N stratified
#   bash eval/musique/run-bench.sh resume        # resume previous run
#
# Env overrides:
#   API_PORT=18890  (default; >18802 prod port)
#   WORKDIR=/root/.openclaw/musique-bench-<uuid>/work (default: auto)
#   GENERATOR=gpt-4.1-mini (default)
#   TOP_K=20 (default)
#   NO_VECTORIZE=1  (FTS5-only — debug)
#   NO_GENERATOR=1  (retrieval-only — no OpenAI billing)
#   DATASET=ans     (ans = musique_ans, full = musique_full; default ans)

set -euo pipefail

MODE="${1:-smoke}"
shift || true

# ---- Config (defaults; env can override) ------------------------------------

API_PORT="${API_PORT:-18890}"
GENERATOR="${GENERATOR:-gpt-4.1-mini}"
TOP_K="${TOP_K:-20}"
DATASET="${DATASET:-ans}"
NO_VECTORIZE_FLAG=""
if [ "${NO_VECTORIZE:-0}" = "1" ]; then
    NO_VECTORIZE_FLAG="--no-vectorize"
fi
NO_GENERATOR_FLAG=""
if [ "${NO_GENERATOR:-0}" = "1" ]; then
    NO_GENERATOR_FLAG="--no-generator"
    echo "[run-bench] NO_GENERATOR=1 — retrieval-only mode (no OpenAI calls)"
fi

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MUSIQUE_REPO="${MUSIQUE_REPO:-/tmp/musique-repo}"
case "${DATASET}" in
    ans)  MUSIQUE_JSONL="${MUSIQUE_JSONL:-${MUSIQUE_REPO}/data/musique_ans_v1.0_dev.jsonl}" ;;
    full) MUSIQUE_JSONL="${MUSIQUE_JSONL:-${MUSIQUE_REPO}/data/musique_full_v1.0_dev.jsonl}" ;;
    *)    echo "[run-bench] unknown DATASET=${DATASET} (use ans|full)" >&2; exit 2 ;;
esac

# Workdir auto-generated under /root/.openclaw/ (op-audit ALLOWED_PREFIXES)
if [ -z "${WORKDIR:-}" ]; then
    SHORT=$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')
    WORKDIR="/root/.openclaw/musique-bench-${SHORT}/work"
fi
mkdir -p "${WORKDIR}"
RESULTS_DIR="$(dirname "${WORKDIR}")/results"
mkdir -p "${RESULTS_DIR}"

OUT_JSONL="${RESULTS_DIR}/results-${MODE}.jsonl"
OUT_JSON="${HERE}/RESULTS-MUSIQUE.json"
OUT_MD="${HERE}/RESULTS-MUSIQUE.md"
RUN_META_JSON="${RESULTS_DIR}/run-meta.json"

echo "[run-bench] MODE=${MODE} DATASET=${DATASET} API_PORT=${API_PORT} WORKDIR=${WORKDIR}"
echo "[run-bench] OUT_JSONL=${OUT_JSONL}"
echo "[run-bench] OUT_MD=${OUT_MD}"

# ---- 1. Dataset ------------------------------------------------------------

if [ ! -f "${MUSIQUE_JSONL}" ]; then
    echo "[run-bench] MuSiQue JSONL missing at ${MUSIQUE_JSONL}; downloading..."
    if [ ! -d "${MUSIQUE_REPO}" ]; then
        git clone --depth 1 https://github.com/StonyBrookNLP/musique.git "${MUSIQUE_REPO}"
    fi
    pushd "${MUSIQUE_REPO}" > /dev/null
    if ! command -v gdown > /dev/null 2>&1; then
        python3 -m pip install --quiet --user gdown
    fi
    python3 -m gdown -O musique_v1.0.zip "https://drive.google.com/uc?id=1tGdADlNjWFaHLeZZGShh2IRcpO6Lv24h"
    unzip -q -o musique_v1.0.zip
    rm -f musique_v1.0.zip
    rm -rf __MACOSX
    popd > /dev/null
fi
ls -la "${MUSIQUE_JSONL}"

# ---- 2. Self-tests --------------------------------------------------------

echo "[run-bench] corpus_loader self-test..."
python3 "${HERE}/lib/corpus_loader.py" --jsonl "${MUSIQUE_JSONL}"
echo "[run-bench] scorer self-test..."
python3 "${HERE}/lib/scorer.py"

# ---- 3. Env load ----------------------------------------------------------

if [ ! -f /root/.openclaw/.env ]; then
    echo "[run-bench] FATAL: /root/.openclaw/.env missing" >&2
    exit 2
fi
set -a
# shellcheck disable=SC1091
source /root/.openclaw/.env
set +a
: "${OPENAI_API_KEY:?OPENAI_API_KEY must be set}"
: "${GEMINI_API_KEY:?GEMINI_API_KEY must be set}"

# Phase H v2 baseline — explicit disables
export NOX_RERANKER_ENABLED=0
export NOX_TEMPORAL_PATH="${NOX_TEMPORAL_PATH:-shadow}"
export NOX_SALIENCE_MODE="${NOX_SALIENCE_MODE:-shadow}"
export NOX_API_PORT="${API_PORT}"

# ---- 4. Mode selection ----------------------------------------------------

case "${MODE}" in
    smoke)
        MAX_Q=100
        EXTRA_FLAGS=""
        ;;
    full)
        MAX_Q=0       # 0 = full dev (~2417 for ans, ~4834 for full)
        EXTRA_FLAGS=""
        ;;
    subset)
        MAX_Q="${1:-500}"
        EXTRA_FLAGS=""
        ;;
    resume)
        MAX_Q="${MAX_Q:-100}"
        EXTRA_FLAGS="--resume"
        ;;
    *)
        echo "[run-bench] unknown mode: ${MODE} (use smoke|full|subset|resume)" >&2
        exit 2
        ;;
esac

# Write run meta for aggregate
cat > "${RUN_META_JSON}" <<EOF
{
  "mode": "${MODE}",
  "dataset": "${DATASET}",
  "max_questions": ${MAX_Q},
  "api_port": ${API_PORT},
  "top_k": ${TOP_K},
  "generator": "${GENERATOR}",
  "workdir": "${WORKDIR}",
  "phase": "Phase H v2 baseline (rerank=off, hybrid=on, single-shot)",
  "timestamp_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "git_sha": "$(git -C "${HERE}/../.." rev-parse --short HEAD 2>/dev/null || echo unknown)"
}
EOF

# ---- 5. Adapter run -------------------------------------------------------

START_TS=$(date +%s)
echo "[run-bench] starting adapter at $(date -u)"
# shellcheck disable=SC2086
python3 "${HERE}/adapter_nox_mem.py" \
    --musique-jsonl "${MUSIQUE_JSONL}" \
    --workdir "${WORKDIR}" \
    --out "${OUT_JSONL}" \
    --api-port "${API_PORT}" \
    --top-k "${TOP_K}" \
    --max-questions "${MAX_Q}" \
    --generator "${GENERATOR}" \
    ${NO_VECTORIZE_FLAG} ${NO_GENERATOR_FLAG} ${EXTRA_FLAGS} 2>&1 | tee "${RESULTS_DIR}/adapter-stderr.log"
ADAPTER_RC=${PIPESTATUS[0]}
END_TS=$(date +%s)
ELAPSED=$((END_TS - START_TS))
echo "[run-bench] adapter finished rc=${ADAPTER_RC} elapsed=${ELAPSED}s"

# ---- 6. Aggregate ---------------------------------------------------------

if [ -s "${OUT_JSONL}" ]; then
    python3 "${HERE}/lib/aggregate.py" "${OUT_JSONL}" \
        --json-out "${OUT_JSON}" \
        --md-out "${OUT_MD}" \
        --run-meta-json "${RUN_META_JSON}"
    echo "[run-bench] aggregate written:"
    echo "  ${OUT_JSON}"
    echo "  ${OUT_MD}"
    # Also stash the full-bench JSON snapshot if mode=full
    if [ "${MODE}" = "full" ]; then
        N=$(wc -l < "${OUT_JSONL}" | tr -d ' ')
        cp "${OUT_JSON}" "${HERE}/results/RESULTS-FULL-${N}q.json"
        echo "  ${HERE}/results/RESULTS-FULL-${N}q.json"
    fi
else
    echo "[run-bench] WARN: empty results jsonl" >&2
fi

exit "${ADAPTER_RC}"
