#!/usr/bin/env bash
# benchmark/scripts/run-q2.sh — Q2 LongMemEval benchmark (~3h, ~$1.08)
#
# Usage:
#   bash benchmark/scripts/run-q2.sh [--judge <gpt-4o|gemini-2.5-pro>] [--resume <hypotheses.jsonl>] [--n <int>] [--dry-run]
#
# Description:
#   Downloads LongMemEval s_cleaned split, ingests ~4k sessions per question
#   into eval.db, runs generator + judge evaluation on n=100 stratified questions.
#   Runs BOTH judges if OPENAI_API_KEY is available; falls back to gemini-2.5-pro only.
#   Output: benchmark/results/q2-longmemeval-{gpt4o,gemini25pro}-${TS}.json
#
# Cost: ~$1.08 (embedding + generator gemini-flash + judge gpt-4o + judge gemini-pro)
# Cost cap: NOX_PROVIDER_DAILY_USD_CAP=5 (override via env)
#
# CLAUDE.md rule #1: always source .env before any nox-mem CLI call.

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
NM_ROOT="${OPENCLAW_WORKSPACE:-/root/.openclaw/workspace/tools/nox-mem}"
BENCH_LOG_DIR="/var/log/nox-mem/bench"
RESULTS_DIR="${NM_ROOT}/benchmark/results"
EVAL_DIR="${NM_ROOT}/eval/longmemeval"
TS="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="${BENCH_LOG_DIR}/q2-${TS}.log"
N=100
SEED=42
SPLIT="s_cleaned"
DRY_RUN=0
RESUME_HYPOTHESES=""
JUDGE_OVERRIDE=""

# ── Parse args ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --n)           N="$2"; shift 2 ;;
    --seed)        SEED="$2"; shift 2 ;;
    --split)       SPLIT="$2"; shift 2 ;;
    --judge)       JUDGE_OVERRIDE="$2"; shift 2 ;;
    --resume)      RESUME_HYPOTHESES="$2"; shift 2 ;;
    --dry-run)     DRY_RUN=1; shift ;;
    --help|-h)
      echo "Usage: bash benchmark/scripts/run-q2.sh [options]"
      echo "  --n <int>          Number of questions to evaluate (default: 100)"
      echo "  --seed <int>       Random seed for stratified sampling (default: 42)"
      echo "  --split <name>     Dataset split (default: s_cleaned)"
      echo "  --judge <model>    Force judge: gpt-4o | gemini-2.5-pro (default: auto)"
      echo "  --resume <path>    Resume from partial hypotheses JSONL"
      echo "  --dry-run          Validate env + print plan, do not execute"
      exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

# ── Setup logging ─────────────────────────────────────────────────────────────
mkdir -p "${BENCH_LOG_DIR}" && chmod 700 "${BENCH_LOG_DIR}"
mkdir -p "${RESULTS_DIR}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "═══════════════════════════════════════════════════════════"
echo "Q2 LongMemEval Benchmark — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "═══════════════════════════════════════════════════════════"

# ── Source env (CLAUDE.md regra #1) ───────────────────────────────────────────
if [[ -f /root/.openclaw/.env ]]; then
  set -a; source /root/.openclaw/.env; set +a
  echo "OK  sourced /root/.openclaw/.env"
else
  echo "WARN: /root/.openclaw/.env not found — relying on exported env"
fi

# ── Cost cap (mandatory — spec §7) ────────────────────────────────────────────
# Override: NOX_PROVIDER_DAILY_USD_CAP=5 (expected cost ~$1.08; cap provides 5× headroom)
export NOX_PROVIDER_DAILY_USD_CAP="${NOX_PROVIDER_DAILY_USD_CAP:-5}"
echo "INFO cost cap: \$${NOX_PROVIDER_DAILY_USD_CAP}/dia"

# ── Pre-flight checks ─────────────────────────────────────────────────────────
echo ""
echo "── Pre-flight ──────────────────────────────────────────────"

cd "${NM_ROOT}"

# 1. GEMINI_API_KEY (mandatory — embedding + generator + gemini judge)
if [[ -z "${GEMINI_API_KEY:-}" ]]; then
  echo "FATAL: GEMINI_API_KEY not set — required for embedding + generator + gemini-2.5-pro judge" >&2
  exit 1
fi
echo "OK  GEMINI_API_KEY: ${GEMINI_API_KEY:0:12}..."

# 2. OPENAI_API_KEY (optional — gpt-4o judge fallback to gemini if absent)
HAS_OPENAI=0
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  HAS_OPENAI=1
  echo "OK  OPENAI_API_KEY: ${OPENAI_API_KEY:0:12}... (gpt-4o judge enabled)"
else
  echo "WARN: OPENAI_API_KEY not set — will run gemini-2.5-pro judge only (spec §8 fallback)"
  echo "      Document in result JSON that gpt-4o judge is pending."
fi

# 3. Determine judges
if [[ -n "${JUDGE_OVERRIDE}" ]]; then
  JUDGES=("${JUDGE_OVERRIDE}")
  echo "INFO judge override: ${JUDGE_OVERRIDE}"
elif [[ "${HAS_OPENAI}" -eq 1 ]]; then
  JUDGES=("gpt-4o" "gemini-2.5-pro")
  echo "INFO judges: gpt-4o + gemini-2.5-pro (both; will compute Cohen's-κ inter-judge agreement)"
else
  JUDGES=("gemini-2.5-pro")
  echo "INFO judges: gemini-2.5-pro only (gpt-4o pending OPENAI_API_KEY)"
fi

# 4. Gemini quota check
QUOTA_CHECK=$(curl -s \
  "https://generativelanguage.googleapis.com/v1beta/models?key=${GEMINI_API_KEY}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',{}).get('code','OK'))" 2>/dev/null || echo "CURL_ERR")
if [[ "${QUOTA_CHECK}" != "OK" ]]; then
  echo "FATAL: Gemini API check failed: ${QUOTA_CHECK}" >&2
  exit 1
fi
echo "OK  Gemini quota: active"

# 5. Disk space (eval.db ~1.5 GB for Q2)
DISK_AVAIL=$(df -BG "${NM_ROOT}" | tail -1 | awk '{print $4}' | tr -d 'G')
if [[ "${DISK_AVAIL:-0}" -lt 5 ]]; then
  echo "FATAL: insufficient disk space (${DISK_AVAIL}G available, need >= 5G for Q2 eval.db)" >&2
  exit 1
fi
echo "OK  disk: ${DISK_AVAIL}G available"

# 6. dist/index.js present
if [[ ! -f "${NM_ROOT}/dist/index.js" ]]; then
  echo "FATAL: dist/index.js not found — run 'npm run build' first" >&2
  exit 1
fi
echo "OK  dist/index.js present"

# 7. eval/longmemeval scripts present
for f in download.ts parser.ts run.ts score.ts; do
  if [[ ! -f "${EVAL_DIR}/${f}" ]]; then
    echo "FATAL: eval/longmemeval/${f} not found — harness not scaffolded" >&2
    exit 1
  fi
done
echo "OK  eval/longmemeval harness scripts present"

# ── Dry-run exit ──────────────────────────────────────────────────────────────
if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo ""
  echo "── Dry-run plan ────────────────────────────────────────────"
  echo "  eval dir       : ${EVAL_DIR}"
  echo "  split          : ${SPLIT}"
  echo "  n              : ${N} (seed=${SEED})"
  echo "  judges         : ${JUDGES[*]}"
  echo "  generator      : gemini-2.5-flash"
  echo "  cost cap       : \$${NOX_PROVIDER_DAILY_USD_CAP}/dia"
  echo "  expected cost  : ~\$1.08 (embedding + generator + judges)"
  echo "  expected time  : ~3h"
  if [[ -n "${RESUME_HYPOTHESES}" ]]; then
    echo "  resume from    : ${RESUME_HYPOTHESES}"
  fi
  echo ""
  echo "[--dry-run] validation passed — not executing"
  exit 0
fi

mkdir -p "${EVAL_DIR}/hypotheses"

# ── Phase 1: Download splits ───────────────────────────────────────────────────
echo ""
echo "── Phase 1: Download LongMemEval splits ────────────────────"
echo "INFO: MIT license (xiaowu0162/longmemeval-cleaned)"
cd "${NM_ROOT}"

# Download oracle split (used for dry-run validation reference)
echo "INFO: downloading oracle split..."
timeout 600 npx tsx "${EVAL_DIR}/download.ts" --split oracle 2>&1 || {
  echo "WARN: oracle split download issue — may already exist, continuing"
}

# Download s_cleaned split (the one we evaluate on)
echo "INFO: downloading ${SPLIT} split..."
timeout 600 npx tsx "${EVAL_DIR}/download.ts" --split "${SPLIT}" 2>&1 || {
  echo "WARN: ${SPLIT} split download issue — check network or HuggingFace access"
  exit 1
}
echo "OK  splits downloaded"

# ── Phase 2: Ingest s_cleaned ─────────────────────────────────────────────────
echo ""
echo "── Phase 2: Ingest + embed corpus (~60–90 min) ─────────────"
echo "INFO: ~4k sessions × Gemini gemini-embedding-001 (3072d)"
echo "INFO: DB isolation: ${EVAL_DIR}/eval.db (never touches nox-mem.db)"
echo "INFO: start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Flush eval.db for clean run (eval.db is disposable by design)
if [[ -f "${EVAL_DIR}/eval.db" ]] && [[ -z "${RESUME_HYPOTHESES}" ]]; then
  echo "INFO: removing stale eval.db before fresh ingest"
  rm -f "${EVAL_DIR}/eval.db" "${EVAL_DIR}/eval.db-wal" "${EVAL_DIR}/eval.db-shm"
fi

timeout 7200 npx tsx "${EVAL_DIR}/parser.ts" \
  --split "${SPLIT}" \
  --ingest 2>&1 || {
  echo "ERROR: parser.ts --ingest failed" >&2
  exit 1
}
echo "INFO: ingest done: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ── Phase 3: Run with each judge ─────────────────────────────────────────────
echo ""
echo "── Phase 3: Evaluate n=${N} questions per judge ────────────"
echo "INFO: generator: gemini-2.5-flash"
echo "INFO: hypotheses saved incrementally (one append per question)"

for JUDGE in "${JUDGES[@]}"; do
  RESULT_SUFFIX="${JUDGE//\./-}"
  RESULT_SUFFIX="${RESULT_SUFFIX//-2-5-pro/25pro}"
  RESULT_SUFFIX="${RESULT_SUFFIX//-4o/4o}"
  RESULT_FILE="${RESULTS_DIR}/q2-longmemeval-${RESULT_SUFFIX}-${TS}.json"

  # Partial hypotheses path for this judge
  if [[ -n "${RESUME_HYPOTHESES}" ]] && [[ "${JUDGE}" == "${JUDGES[0]}" ]]; then
    HYPOTHESES_ARG="--resume --hypotheses ${RESUME_HYPOTHESES}"
    echo "INFO: [${JUDGE}] resuming from ${RESUME_HYPOTHESES}"
  else
    HYPOTHESES_ARG=""
  fi

  echo ""
  echo "INFO [${JUDGE}] start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

  # Monitor cost mid-run in background (advisory only)
  PROD_DB="${NM_ROOT}/nox-mem.db"

  LONGMEMEVAL_JUDGE="${JUDGE}" \
  LONGMEMEVAL_GENERATOR="gemini-2.5-flash" \
  timeout 10800 npx tsx "${EVAL_DIR}/run.ts" \
    --split "${SPLIT}" \
    --n "${N}" \
    --seed "${SEED}" \
    --cli \
    --full \
    ${HYPOTHESES_ARG} \
    > "${RESULT_FILE}" 2>&1 || {
    echo "ERROR: run.ts failed for judge ${JUDGE}" >&2
    echo "TIP:   resume from latest hypotheses:" >&2
    echo "         ls ${EVAL_DIR}/hypotheses/*.jsonl | tail -1" >&2
    echo "         bash benchmark/scripts/run-q2.sh --judge ${JUDGE} --resume <path>" >&2
    exit 1
  }

  echo "INFO [${JUDGE}] done: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

  # Score
  echo "INFO [${JUDGE}] scoring..."
  npx tsx "${EVAL_DIR}/score.ts" "${RESULT_FILE}" --ci 2>&1 || {
    echo "WARN: score.ts exited non-zero for ${JUDGE}"
  }

  # Spot-check
  python3 -c "
import json
with open('${RESULT_FILE}') as f:
    d = json.load(f)
m = d.get('metrics', {})
print(f'  [{\"${JUDGE}\"}] n={len(d.get(\"results\",[]))} accuracy={m.get(\"overall_accuracy\",\"?\")} judge={d.get(\"judge_model\",\"?\")}')
" || echo "WARN: could not parse ${RESULT_FILE}"

  echo "OK  [${JUDGE}] result: ${RESULT_FILE}"
done

# ── Inter-judge agreement (if both judges ran) ────────────────────────────────
if [[ "${#JUDGES[@]}" -ge 2 ]]; then
  echo ""
  echo "── Inter-judge agreement (Cohen's-κ) ───────────────────────"
  GPT4O_FILE="${RESULTS_DIR}/q2-longmemeval-gpt4o-${TS}.json"
  GEMINI_FILE="${RESULTS_DIR}/q2-longmemeval-gemini25pro-${TS}.json"
  if [[ -f "${GPT4O_FILE}" ]] && [[ -f "${GEMINI_FILE}" ]]; then
    python3 -c "
import json, sys

def kappa(y1, y2):
    n = len(y1)
    if n == 0: return None
    po = sum(a==b for a,b in zip(y1,y2)) / n
    p1 = (sum(y1)/n)*(sum(y2)/n)
    p0 = ((n-sum(y1))/n)*((n-sum(y2))/n)
    pe = p1 + p0
    if abs(1 - pe) < 1e-9: return 1.0
    return (po - pe) / (1 - pe)

with open('${GPT4O_FILE}') as f: d1 = json.load(f)
with open('${GEMINI_FILE}') as f: d2 = json.load(f)

# Build aligned lists by question_id
r1 = {r['question_id']: r.get('judge_label', 0) for r in d1.get('results', [])}
r2 = {r['question_id']: r.get('judge_label', 0) for r in d2.get('results', [])}
common = sorted(set(r1) & set(r2))
y1 = [r1[q] for q in common]
y2 = [r2[q] for q in common]
k = kappa(y1, y2)
print(f'  inter-judge kappa: {k:.3f} (n={len(common)} common questions)')
print(f'  threshold >0.6 = substantial agreement')
" || echo "WARN: could not compute inter-judge agreement"
  fi
fi

# ── Cost summary ──────────────────────────────────────────────────────────────
echo ""
echo "── Cost check (telemetry) ──────────────────────────────────"
if [[ -f "${NM_ROOT}/nox-mem.db" ]]; then
  sqlite3 "${NM_ROOT}/nox-mem.db" \
    "SELECT ROUND(SUM(cost_usd),4) || ' USD (' || COUNT(*) || ' calls)' FROM provider_telemetry WHERE created_at >= date('now');" \
    2>/dev/null || echo "WARN: could not query telemetry"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "Q2 DONE"
for JUDGE in "${JUDGES[@]}"; do
  RESULT_SUFFIX="${JUDGE//\./-}"
  RESULT_SUFFIX="${RESULT_SUFFIX//-2-5-pro/25pro}"
  RESULT_SUFFIX="${RESULT_SUFFIX//-4o/4o}"
  echo "  ${JUDGE} result : ${RESULTS_DIR}/q2-longmemeval-${RESULT_SUFFIX}-${TS}.json"
done
echo "  log            : ${LOG_FILE}"
echo ""
echo "Validate:"
echo "  jq '{acc:.metrics.overall_accuracy,judge:.judge_model}' ${RESULTS_DIR}/q2-longmemeval-*-${TS}.json"
echo ""
echo "Next step:"
echo "  bash benchmark/scripts/collect-results.sh"
echo "═══════════════════════════════════════════════════════════"
