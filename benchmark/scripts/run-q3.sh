#!/usr/bin/env bash
# benchmark/scripts/run-q3.sh — Q3 Latency baseline run (~45 min, $0)
#
# Usage:
#   bash benchmark/scripts/run-q3.sh [--workload <name>] [--resume] [--dry-run]
#
# Description:
#   Runs latency benchmark against the VPS real nox-mem.db (~62k chunks).
#   100 queries × 5 workloads (short/medium/long/kg-heavy/ingest.entity-file).
#   Output: benchmark/results/q3-latency-${TS}.json
#
# Cost: $0 — no Gemini API calls during run (embeddings already in DB).
# Requires: eval/latency/ harness built and nox-mem dist/ compiled.
#
# CLAUDE.md rule #1: always source .env before any nox-mem CLI call.

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
NM_ROOT="${OPENCLAW_WORKSPACE:-/root/.openclaw/workspace/tools/nox-mem}"
BENCH_LOG_DIR="/var/log/nox-mem/bench"
RESULTS_DIR="${NM_ROOT}/benchmark/results"
EVAL_DIR="${NM_ROOT}/eval/latency"
EVAL_DB="${EVAL_DIR}/eval.db"
TS="$(date +%Y%m%d-%H%M%S)"
CHECKPOINT_FILE="${RESULTS_DIR}/q3-checkpoint-${TS}.json"
FULL_RUN_FILE="${RESULTS_DIR}/q3-latency-${TS}.json"
SUMMARY_FILE="${RESULTS_DIR}/q3-summary-${TS}.json"
LOG_FILE="${BENCH_LOG_DIR}/q3-${TS}.log"
WORKLOAD=""
DRY_RUN=0
RESUME=0

# ── Parse args ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --workload)   WORKLOAD="$2"; shift 2 ;;
    --dry-run)    DRY_RUN=1; shift ;;
    --resume)     RESUME=1; shift ;;
    --help|-h)
      echo "Usage: bash benchmark/scripts/run-q3.sh [--workload <name>] [--resume] [--dry-run]"
      echo "  --workload  Run only a single workload (search.short|search.medium|search.long|search.kg-heavy|ingest.entity-file)"
      echo "  --resume    Skip eval.db snapshot if it already exists"
      echo "  --dry-run   Validate env + print plan, do not execute"
      exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

# ── Setup logging ─────────────────────────────────────────────────────────────
mkdir -p "${BENCH_LOG_DIR}" && chmod 700 "${BENCH_LOG_DIR}"
mkdir -p "${RESULTS_DIR}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "═══════════════════════════════════════════════════════════"
echo "Q3 Latency Benchmark — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "═══════════════════════════════════════════════════════════"

# ── Source env (CLAUDE.md regra #1) ───────────────────────────────────────────
if [[ -f /root/.openclaw/.env ]]; then
  set -a; source /root/.openclaw/.env; set +a
  echo "OK  sourced /root/.openclaw/.env"
else
  echo "WARN: /root/.openclaw/.env not found — relying on exported env"
fi

# ── Cost cap (mandatory — spec §7) ────────────────────────────────────────────
export NOX_PROVIDER_DAILY_USD_CAP="${NOX_PROVIDER_DAILY_USD_CAP:-20}"
echo "INFO cost cap: \$${NOX_PROVIDER_DAILY_USD_CAP}/dia"

# ── Pre-flight checks ─────────────────────────────────────────────────────────
echo ""
echo "── Pre-flight ──────────────────────────────────────────────"

cd "${NM_ROOT}"

# 1. nox-mem-api health
API_PORT="${NOX_API_PORT:-18802}"
HEALTH=$(curl -sf "http://127.0.0.1:${API_PORT}/api/health" 2>/dev/null || echo '{"status":"err"}')
API_STATUS=$(echo "${HEALTH}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))" 2>/dev/null || echo "?")
if [[ "${API_STATUS}" != "ok" ]]; then
  echo "WARN: nox-mem-api not healthy (status=${API_STATUS}). Q3 uses snapshot DB — proceeding."
else
  echo "OK  nox-mem-api healthy"
fi

# 2. Disk space (need >= 3 GB for eval.db snapshot)
DISK_AVAIL=$(df -BG "${NM_ROOT}" | tail -1 | awk '{print $4}' | tr -d 'G')
if [[ "${DISK_AVAIL:-0}" -lt 3 ]]; then
  echo "FATAL: insufficient disk space (${DISK_AVAIL}G available, need >= 3G)" >&2
  exit 1
fi
echo "OK  disk: ${DISK_AVAIL}G available"

# 3. nox-mem dist compiled
if [[ ! -f "${NM_ROOT}/dist/index.js" ]]; then
  echo "FATAL: dist/index.js not found — run 'npm run build' first" >&2
  exit 1
fi
echo "OK  dist/index.js present"

# 4. Latency harness built
if [[ ! -f "${EVAL_DIR}/dist/runner.js" ]]; then
  echo "INFO building latency harness..."
  cd "${EVAL_DIR}" && npm install --quiet && npm run build
  cd "${NM_ROOT}"
  echo "OK  latency harness built"
else
  echo "OK  latency harness already built"
fi

# ── Dry-run exit ──────────────────────────────────────────────────────────────
if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo ""
  echo "── Dry-run plan ────────────────────────────────────────────"
  echo "  eval.db snapshot : ${EVAL_DB}"
  echo "  full run output  : ${FULL_RUN_FILE}"
  echo "  summary output   : ${SUMMARY_FILE}"
  echo "  log              : ${LOG_FILE}"
  if [[ -n "${WORKLOAD}" ]]; then
    echo "  single workload  : ${WORKLOAD}"
  else
    echo "  workloads        : search.short search.medium search.long search.kg-heavy ingest.entity-file"
  fi
  echo "  cost             : \$0.00 (no API calls)"
  echo ""
  echo "[--dry-run] validation passed — not executing"
  exit 0
fi

# ── Snapshot prod DB (not modifying nox-mem.db) ───────────────────────────────
echo ""
echo "── DB Snapshot ─────────────────────────────────────────────"
if [[ "${RESUME}" -eq 1 ]] && [[ -f "${EVAL_DB}" ]]; then
  echo "OK  resuming — reusing existing eval.db ($(du -sh "${EVAL_DB}" | cut -f1))"
else
  PROD_DB="${NM_ROOT}/nox-mem.db"
  if [[ ! -f "${PROD_DB}" ]]; then
    echo "FATAL: prod DB not found at ${PROD_DB}" >&2
    exit 1
  fi
  echo "INFO snapshotting ${PROD_DB} → ${EVAL_DB}"
  cp "${PROD_DB}" "${EVAL_DB}"
  echo "OK  eval.db created: $(du -sh "${EVAL_DB}" | cut -f1)"

  # Validate integrity
  INTEGRITY=$(sqlite3 "${EVAL_DB}" "PRAGMA integrity_check;" 2>/dev/null | head -1)
  if [[ "${INTEGRITY}" != "ok" ]]; then
    echo "FATAL: eval.db integrity check failed: ${INTEGRITY}" >&2
    exit 1
  fi
  echo "OK  integrity check: ${INTEGRITY}"
fi

# ── Run latency benchmark ─────────────────────────────────────────────────────
echo ""
echo "── Latency Run ─────────────────────────────────────────────"
echo "INFO start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

cd "${EVAL_DIR}"

RUNNER_ARGS=(
  "--output" "${FULL_RUN_FILE}"
  "--db" "${EVAL_DB}"
)
if [[ -n "${WORKLOAD}" ]]; then
  RUNNER_ARGS+=("--workload" "${WORKLOAD}")
  echo "INFO single workload: ${WORKLOAD}"
else
  RUNNER_ARGS+=("--all")
  echo "INFO running all workloads"
fi

node dist/runner.js "${RUNNER_ARGS[@]}"

echo "INFO runner done: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ── Aggregate ─────────────────────────────────────────────────────────────────
echo ""
echo "── Aggregate ───────────────────────────────────────────────"
node dist/aggregator.js --input "${FULL_RUN_FILE}" --output "${SUMMARY_FILE}"
echo "OK  summary: ${SUMMARY_FILE}"

# ── Spot-check output ─────────────────────────────────────────────────────────
echo ""
echo "── Results spot-check ──────────────────────────────────────"
python3 -c "
import json, sys
with open('${SUMMARY_FILE}') as f:
    d = json.load(f)
wl = d.get('workloads', {})
for k, v in wl.items():
    p95 = v.get('p95_ms', '?')
    n   = v.get('n', '?')
    print(f'  {k:<30} p95={p95}ms  n={n}')
" || echo "WARN: could not parse summary JSON"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "Q3 DONE"
echo "  full run : ${FULL_RUN_FILE}"
echo "  summary  : ${SUMMARY_FILE}"
echo "  log      : ${LOG_FILE}"
echo ""
echo "Next step:"
echo "  Validate: jq '.workloads[\"search.medium\"].p95_ms' ${SUMMARY_FILE}"
echo "  Collect : bash benchmark/scripts/collect-results.sh"
echo "═══════════════════════════════════════════════════════════"
