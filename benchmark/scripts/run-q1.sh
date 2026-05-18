#!/usr/bin/env bash
# benchmark/scripts/run-q1.sh — Q1 LoCoMo benchmark (~1.5h, ~$0.05)
#
# Usage:
#   bash benchmark/scripts/run-q1.sh [--resume <checkpoint>] [--n <int>] [--dry-run]
#
# Description:
#   Downloads LoCoMo dataset, ingests 5.882 turns into eval.db,
#   runs hybrid search against n=100 stratified QA pairs (seed=42),
#   scores R@5 / R@1 / MRR / nDCG@10 with 95% CI.
#   Output: benchmark/results/q1-locomo-${TS}.json
#
# Cost: ~$0.05 (Gemini embedding ~5.882 turns × 3072d, no LLM judge)
# Cost cap: NOX_PROVIDER_DAILY_USD_CAP=1 (override via env)
#
# CLAUDE.md rule #1: always source .env before any nox-mem CLI call.

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
NM_ROOT="${OPENCLAW_WORKSPACE:-/root/.openclaw/workspace/tools/nox-mem}"
BENCH_LOG_DIR="/var/log/nox-mem/bench"
RESULTS_DIR="${NM_ROOT}/benchmark/results"
EVAL_DIR="${NM_ROOT}/eval/locomo"
TS="$(date +%Y%m%d-%H%M%S)"
FULL_RUN_FILE="${RESULTS_DIR}/q1-locomo-${TS}.json"
LOG_FILE="${BENCH_LOG_DIR}/q1-${TS}.log"
N=100
SEED=42
DRY_RUN=0
RESUME_CHECKPOINT=""

# ── Parse args ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --n)          N="$2"; shift 2 ;;
    --seed)       SEED="$2"; shift 2 ;;
    --resume)     RESUME_CHECKPOINT="$2"; shift 2 ;;
    --dry-run)    DRY_RUN=1; shift ;;
    --help|-h)
      echo "Usage: bash benchmark/scripts/run-q1.sh [options]"
      echo "  --n <int>          Number of QA pairs to evaluate (default: 100)"
      echo "  --seed <int>       Random seed for stratified sampling (default: 42)"
      echo "  --resume <path>    Resume from checkpoint file (partial-*.json)"
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
echo "Q1 LoCoMo Benchmark — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "═══════════════════════════════════════════════════════════"

# ── Source env (CLAUDE.md regra #1) ───────────────────────────────────────────
if [[ -f /root/.openclaw/.env ]]; then
  set -a; source /root/.openclaw/.env; set +a
  echo "OK  sourced /root/.openclaw/.env"
else
  echo "WARN: /root/.openclaw/.env not found — relying on exported env"
fi

# ── Cost cap (mandatory — spec §7) ────────────────────────────────────────────
# Override: NOX_PROVIDER_DAILY_USD_CAP=1 (safe for Q1 ~$0.05 expected)
export NOX_PROVIDER_DAILY_USD_CAP="${NOX_PROVIDER_DAILY_USD_CAP:-1}"
echo "INFO cost cap: \$${NOX_PROVIDER_DAILY_USD_CAP}/dia"

# ── Pre-flight checks ─────────────────────────────────────────────────────────
echo ""
echo "── Pre-flight ──────────────────────────────────────────────"

cd "${NM_ROOT}"

# 1. GEMINI_API_KEY present
if [[ -z "${GEMINI_API_KEY:-}" ]]; then
  echo "FATAL: GEMINI_API_KEY not set — required for embedding" >&2
  exit 1
fi
echo "OK  GEMINI_API_KEY: ${GEMINI_API_KEY:0:12}..."

# 2. Gemini quota check
QUOTA_CHECK=$(curl -s \
  "https://generativelanguage.googleapis.com/v1beta/models?key=${GEMINI_API_KEY}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',{}).get('code','OK'))" 2>/dev/null || echo "CURL_ERR")
if [[ "${QUOTA_CHECK}" != "OK" ]]; then
  echo "FATAL: Gemini API check failed: ${QUOTA_CHECK}" >&2
  echo "       Check quota at https://console.cloud.google.com — may need to wait for midnight UTC reset" >&2
  exit 1
fi
echo "OK  Gemini quota: active"

# 3. Disk space (eval.db ~200 MB for Q1)
DISK_AVAIL=$(df -BG "${NM_ROOT}" | tail -1 | awk '{print $4}' | tr -d 'G')
if [[ "${DISK_AVAIL:-0}" -lt 2 ]]; then
  echo "FATAL: insufficient disk space (${DISK_AVAIL}G available, need >= 2G)" >&2
  exit 1
fi
echo "OK  disk: ${DISK_AVAIL}G available"

# 4. dist/index.js present
if [[ ! -f "${NM_ROOT}/dist/index.js" ]]; then
  echo "FATAL: dist/index.js not found — run 'npm run build' first" >&2
  exit 1
fi
echo "OK  dist/index.js present"

# 5. eval/locomo scripts present
for f in download.ts parser.ts run.ts score.ts; do
  if [[ ! -f "${EVAL_DIR}/${f}" ]]; then
    echo "FATAL: eval/locomo/${f} not found — harness not scaffolded" >&2
    exit 1
  fi
done
echo "OK  eval/locomo harness scripts present"

# ── Dry-run exit ──────────────────────────────────────────────────────────────
if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo ""
  echo "── Dry-run plan ────────────────────────────────────────────"
  echo "  eval dir       : ${EVAL_DIR}"
  echo "  n              : ${N} (seed=${SEED})"
  echo "  output         : ${FULL_RUN_FILE}"
  echo "  log            : ${LOG_FILE}"
  echo "  cost cap       : \$${NOX_PROVIDER_DAILY_USD_CAP}/dia"
  echo "  expected cost  : ~\$0.05 (embedding only, no judge)"
  echo "  expected time  : ~1–1.5h"
  if [[ -n "${RESUME_CHECKPOINT}" ]]; then
    echo "  resume from    : ${RESUME_CHECKPOINT}"
  fi
  echo ""
  echo "[--dry-run] validation passed — not executing"
  exit 0
fi

mkdir -p "${EVAL_DIR}/results"

# ── Phase 1: Download dataset ─────────────────────────────────────────────────
echo ""
echo "── Phase 1: Download LoCoMo dataset ────────────────────────"
echo "INFO: CC BY-NC 4.0 license — research use only, do not distribute via nox-supermem"
cd "${NM_ROOT}"
timeout 300 npx tsx "${EVAL_DIR}/download.ts" 2>&1 || {
  echo "WARN: download.ts exited non-zero — data may already exist, continuing"
}
echo "OK  dataset download step complete"

# ── Phase 2: Ingest corpus ────────────────────────────────────────────────────
echo ""
echo "── Phase 2: Ingest + embed corpus (~30–45 min) ─────────────"
echo "INFO: ~5.882 turns × Gemini gemini-embedding-001 (3072d)"
echo "INFO: start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
timeout 3600 npx tsx "${EVAL_DIR}/parser.ts" --ingest 2>&1 || {
  echo "WARN: parser.ts --ingest exited non-zero — may be partially complete"
}
echo "INFO: ingest done: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ── Phase 3: Run evaluation ───────────────────────────────────────────────────
echo ""
echo "── Phase 3: Evaluate n=${N} QA pairs (seed=${SEED}) ────────"
echo "INFO: checkpoints saved every 10 queries at ${EVAL_DIR}/results/partial-*.json"
echo "INFO: start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [[ -n "${RESUME_CHECKPOINT}" ]]; then
  echo "INFO: resuming from checkpoint: ${RESUME_CHECKPOINT}"
  timeout 1800 npx tsx "${EVAL_DIR}/run.ts" \
    --n "${N}" \
    --seed "${SEED}" \
    --cli \
    --full \
    --resume \
    --checkpoint "${RESUME_CHECKPOINT}" \
    > "${FULL_RUN_FILE}" 2>&1 || {
    echo "WARN: run.ts exited non-zero — check ${LOG_FILE}" >&2
    echo "TIP:  resume from latest checkpoint: ls ${EVAL_DIR}/results/partial-*.json | tail -1" >&2
    exit 1
  }
else
  timeout 1800 npx tsx "${EVAL_DIR}/run.ts" \
    --n "${N}" \
    --seed "${SEED}" \
    --cli \
    --full \
    > "${FULL_RUN_FILE}" 2>&1 || {
    echo "ERROR: run.ts failed — check ${LOG_FILE}" >&2
    echo "TIP:   resume: bash benchmark/scripts/run-q1.sh --resume \$(ls ${EVAL_DIR}/results/partial-*.json | tail -1)" >&2
    exit 1
  }
fi
echo "INFO: evaluation done: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ── Phase 4: Score ────────────────────────────────────────────────────────────
echo ""
echo "── Phase 4: Score + 95% CI ─────────────────────────────────"
npx tsx "${EVAL_DIR}/score.ts" "${FULL_RUN_FILE}" --ci 2>&1 || {
  echo "WARN: score.ts exited non-zero — metrics may not be in result file"
}

# ── Spot-check output ─────────────────────────────────────────────────────────
echo ""
echo "── Results spot-check ──────────────────────────────────────"
python3 -c "
import json, sys
with open('${FULL_RUN_FILE}') as f:
    d = json.load(f)
m = d.get('metrics', {})
print(f'  n_questions : {len(d.get(\"results\", []))}')
print(f'  R@5         : {m.get(\"r5\", \"?\")}')
print(f'  R@1         : {m.get(\"r1\", \"?\")}')
print(f'  MRR         : {m.get(\"mrr\", \"?\")}')
print(f'  nDCG@10     : {m.get(\"ndcg10\", \"?\")}')
print(f'  seed        : {d.get(\"seed\", \"?\")}')
" || echo "WARN: could not parse result JSON — check ${FULL_RUN_FILE}"

# ── Cost accum check (prod DB telemetry) ──────────────────────────────────────
echo ""
echo "── Cost check (telemetry) ──────────────────────────────────"
PROD_DB="${NM_ROOT}/nox-mem.db"
if [[ -f "${PROD_DB}" ]]; then
  sqlite3 "${PROD_DB}" \
    "SELECT ROUND(SUM(cost_usd),4) || ' USD (' || COUNT(*) || ' calls)' FROM provider_telemetry WHERE created_at >= date('now');" \
    2>/dev/null || echo "WARN: could not query telemetry (ok if using eval.db separate)"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "Q1 DONE"
echo "  output : ${FULL_RUN_FILE}"
echo "  log    : ${LOG_FILE}"
echo ""
echo "Validate:"
echo "  jq '{r5:.metrics.r5, ndcg10:.metrics.ndcg10}' ${FULL_RUN_FILE}"
echo ""
echo "Next step (if Q3 already done):"
echo "  bash benchmark/scripts/run-q2.sh"
echo "  # or collect results if skipping Q2:"
echo "  bash benchmark/scripts/collect-results.sh"
echo "═══════════════════════════════════════════════════════════"
