#!/usr/bin/env bash
# eval/hotpotqa/run-bench.sh — HotPotQA bench orchestrator for nox-mem.
#
# Phases (controlled by env vars / flags):
#   1. Dataset acquisition  → downloads hotpot_dev_distractor_v1.json
#   2. Preflight            → OpenAI + Gemini billing-path 5-token completions
#   3. Smoke n=200          → quick verification (target ≥50% F1)
#   4. Full bench n=7405    → dev-distractor full set (budget-conscious abort
#                             at $9 spend if --budget-cap=12 set)
#   5. Aggregate + report   → RESULTS-HOTPOTQA.{md,json}
#
# Workdir convention: /root/.openclaw/hotpotqa-bench-<short-uuid>/
# API port:           18900 (not prod 18802)
#
# Required env (sourced from /root/.openclaw/.env):
#   OPENAI_API_KEY   — gpt-4.1-mini generation
#   GEMINI_API_KEY   — embeddings for nox-mem vectorize
#
# Usage:
#   ./run-bench.sh smoke           # n=200, ~30min
#   ./run-bench.sh full            # n=7405 (full dev), ~5-7h
#   ./run-bench.sh full --n 3000   # mid-scale
#
# Critical reminders (per memoria-nox CLAUDE.md):
#   - sources .env BEFORE any nox-mem CLI invocation (else vectorize silently fails)
#   - never touches prod DB at /root/.openclaw/workspace/tools/nox-mem/nox-mem.db
#   - API port is 18900 (not 18802)
#   - all temp DBs under /root/.openclaw/hotpotqa-bench-*/ (op-audit ALLOWED_PREFIXES)

set -euo pipefail

# ---------------------------------------------------------------------------
# Locate scripts
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVAL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_DIR="$(cd "${EVAL_DIR}/.." && pwd)"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
MODE="${1:-smoke}"
shift || true

WORK_ROOT="${HOTPOT_WORK_ROOT:-/root/.openclaw}"
RUN_UUID="${HOTPOT_RUN_UUID:-$(uuidgen 2>/dev/null | tr 'A-Z' 'a-z' | cut -c1-8 || date +%s)}"
WORKDIR="${HOTPOT_WORKDIR:-${WORK_ROOT}/hotpotqa-bench-${RUN_UUID}}"
DATA_DIR="${WORKDIR}/data"
RESULTS_DIR="${SCRIPT_DIR}/results"
API_PORT="${HOTPOT_API_PORT:-18900}"
DATASET_URL="${HOTPOT_DATASET_URL:-http://curtis.ml.cmu.edu/datasets/hotpot/hotpot_dev_distractor_v1.json}"
DATASET_FILE="${HOTPOT_DATASET_FILE:-${DATA_DIR}/hotpot_dev_distractor_v1.json}"

# Cost cap (USD) — default $12 per task spec
BUDGET_CAP="${HOTPOT_BUDGET_CAP:-12}"

# Per-mode question count (override with --n <N>)
case "${MODE}" in
  smoke)  N_DEFAULT=200 ;;
  full)   N_DEFAULT=0   ;;  # 0 = all 7405
  dry)    N_DEFAULT=5   ;;
  *)
    echo "[run-bench] unknown MODE='${MODE}' (expected: smoke | full | dry)" >&2
    exit 2
    ;;
esac

N_QUESTIONS=$N_DEFAULT
GENERATOR_MODEL="${HOTPOT_GENERATOR:-gpt-4.1-mini}"
TOP_K="${HOTPOT_TOP_K:-5}"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --n)        N_QUESTIONS="$2"; shift 2 ;;
    --top-k)    TOP_K="$2"; shift 2 ;;
    --port)     API_PORT="$2"; shift 2 ;;
    --workdir)  WORKDIR="$2"; shift 2 ;;
    --resume)   EXTRA_ARGS+=("--resume"); shift ;;
    --skip-generation) EXTRA_ARGS+=("--skip-generation"); shift ;;
    --generator) GENERATOR_MODEL="$2"; shift 2 ;;
    --budget-cap) BUDGET_CAP="$2"; shift 2 ;;
    *) EXTRA_ARGS+=("$1"); shift ;;
  esac
done

echo "[run-bench] MODE=${MODE} N=${N_QUESTIONS} top_k=${TOP_K} workdir=${WORKDIR} port=${API_PORT}"
mkdir -p "${WORKDIR}" "${DATA_DIR}" "${RESULTS_DIR}"

# ---------------------------------------------------------------------------
# Env source (CRITICAL — without this vectorize fails silently)
# ---------------------------------------------------------------------------
if [[ -f /root/.openclaw/.env ]]; then
  set -a
  # shellcheck disable=SC1091
  source /root/.openclaw/.env
  set +a
else
  echo "[run-bench] WARN: /root/.openclaw/.env not found; assuming env already exported" >&2
fi

: "${OPENAI_API_KEY:?OPENAI_API_KEY required (sourced from .env or exported)}"
: "${GEMINI_API_KEY:?GEMINI_API_KEY required (sourced from .env or exported)}"

# ---------------------------------------------------------------------------
# Preflight: billing-path exercise (avoids Phase H v1 "auth-OK billing-fail" trap)
# ---------------------------------------------------------------------------
echo "[run-bench] preflight: OpenAI gpt-4.1-mini"
# shellcheck disable=SC1091
source "${EVAL_DIR}/lib/preflight.sh"
preflight_billing "https://api.openai.com/v1" "${OPENAI_API_KEY}" "gpt-4.1-mini" \
  || { echo "[run-bench] OpenAI preflight FAILED; aborting" >&2; exit 1; }

echo "[run-bench] preflight: Gemini gemini-2.5-flash-lite"
preflight_billing "https://generativelanguage.googleapis.com/v1beta/openai" \
  "${GEMINI_API_KEY}" "gemini-2.5-flash-lite" \
  || { echo "[run-bench] Gemini preflight FAILED; aborting" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Dataset acquisition
# ---------------------------------------------------------------------------
if [[ ! -f "${DATASET_FILE}" ]]; then
  echo "[run-bench] downloading dataset: ${DATASET_URL}"
  if command -v curl >/dev/null 2>&1; then
    curl --fail --max-time 600 -sSL -o "${DATASET_FILE}.partial" "${DATASET_URL}"
  elif command -v wget >/dev/null 2>&1; then
    wget --timeout=600 -qO "${DATASET_FILE}.partial" "${DATASET_URL}"
  else
    echo "[run-bench] need curl or wget to download dataset" >&2
    exit 1
  fi
  mv "${DATASET_FILE}.partial" "${DATASET_FILE}"
fi
echo "[run-bench] dataset: ${DATASET_FILE} ($(wc -c <"${DATASET_FILE}") bytes)"

# ---------------------------------------------------------------------------
# Bench output paths
# ---------------------------------------------------------------------------
case "${MODE}" in
  smoke) OUT_JSONL="${RESULTS_DIR}/smoke-200.jsonl"; OUT_SUMMARY="${RESULTS_DIR}/RESULTS-SMOKE-200.json" ;;
  full)  OUT_JSONL="${RESULTS_DIR}/RESULTS-FULL-7K-DEV.jsonl"; OUT_SUMMARY="${RESULTS_DIR}/RESULTS-FULL-7K-DEV.json" ;;
  dry)   OUT_JSONL="${RESULTS_DIR}/dry.jsonl"; OUT_SUMMARY="${RESULTS_DIR}/RESULTS-DRY.json" ;;
esac

# ---------------------------------------------------------------------------
# Run adapter
# ---------------------------------------------------------------------------
echo "[run-bench] starting adapter (mode=${MODE} n=${N_QUESTIONS} out=${OUT_JSONL})"
python3 "${SCRIPT_DIR}/adapter_nox_mem.py" \
  --dataset "${DATASET_FILE}" \
  --workdir "${WORKDIR}/work" \
  --out "${OUT_JSONL}" \
  --top-k "${TOP_K}" \
  --api-port "${API_PORT}" \
  --generator "${GENERATOR_MODEL}" \
  --n "${N_QUESTIONS}" \
  --shuffle --seed 42 \
  "${EXTRA_ARGS[@]}"

# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------
echo "[run-bench] aggregating → ${OUT_SUMMARY}"
CONFIG_JSON=$(printf '{"mode":"%s","n":%d,"top_k":%d,"generator":"%s","api_port":%d,"adapter_mode":"phaseH_v2_baseline","reranker_enabled":false,"setting":"distractor"}' \
  "${MODE}" "${N_QUESTIONS}" "${TOP_K}" "${GENERATOR_MODEL}" "${API_PORT}")
python3 "${SCRIPT_DIR}/lib/aggregate.py" \
  --in "${OUT_JSONL}" \
  --out-json "${OUT_SUMMARY}" \
  --config "${CONFIG_JSON}"

echo "[run-bench] DONE — results at ${OUT_SUMMARY}"
