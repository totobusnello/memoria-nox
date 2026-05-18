#!/usr/bin/env bash
# benchmark/scripts/collect-results.sh — scp VPS results → local, validate, prep commit
#
# Usage (run on Mac, NOT on VPS):
#   bash benchmark/scripts/collect-results.sh --vps root@<vps-ip> [--q1] [--q2] [--q3] [--all]
#
# Description:
#   Copies result JSON files from VPS to repo local directories,
#   validates JSON schema, checks required fields, prints gate readiness.
#   Does NOT commit — leaves that for human review.
#
# After collect, run:
#   GATE_VERIFIED=1 npx tsx benchmark/generate-comparison.ts

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
VPS_NM="/root/.openclaw/workspace/tools/nox-mem"
VPS_HOST=""
COLLECT_Q1=0
COLLECT_Q2=0
COLLECT_Q3=0
DRY_RUN=0

# ── Parse args ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --vps)     VPS_HOST="$2"; shift 2 ;;
    --q1)      COLLECT_Q1=1; shift ;;
    --q2)      COLLECT_Q2=1; shift ;;
    --q3)      COLLECT_Q3=1; shift ;;
    --all)     COLLECT_Q1=1; COLLECT_Q2=1; COLLECT_Q3=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --help|-h)
      echo "Usage: bash benchmark/scripts/collect-results.sh --vps root@<ip> [--q1] [--q2] [--q3] [--all]"
      echo ""
      echo "  --vps <host>   SSH target (e.g. root@45.67.89.12)"
      echo "  --q1           Collect Q1 LoCoMo results"
      echo "  --q2           Collect Q2 LongMemEval results"
      echo "  --q3           Collect Q3 latency results"
      echo "  --all          Collect all three"
      echo "  --dry-run      Print plan, do not scp"
      echo ""
      echo "After collecting, run:"
      echo "  GATE_VERIFIED=1 npx tsx benchmark/generate-comparison.ts"
      exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

# Default to all if none specified
if [[ "${COLLECT_Q1}" -eq 0 ]] && [[ "${COLLECT_Q2}" -eq 0 ]] && [[ "${COLLECT_Q3}" -eq 0 ]]; then
  COLLECT_Q1=1; COLLECT_Q2=1; COLLECT_Q3=1
fi

echo "═══════════════════════════════════════════════════════════"
echo "collect-results.sh — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "═══════════════════════════════════════════════════════════"

# ── VPS required ──────────────────────────────────────────────────────────────
if [[ -z "${VPS_HOST}" ]]; then
  echo "FATAL: --vps <host> required" >&2
  echo "       e.g. bash benchmark/scripts/collect-results.sh --vps root@45.67.89.12 --all" >&2
  exit 1
fi
echo "INFO  VPS: ${VPS_HOST}"

# ── Helpers ───────────────────────────────────────────────────────────────────
validate_json() {
  local file="$1"
  local desc="$2"
  shift 2
  local required_fields=("$@")
  echo -n "  VALIDATE ${desc} ... "
  if [[ ! -f "${file}" ]]; then
    echo "MISSING: ${file}"
    return 1
  fi
  # Check JSON valid
  if ! python3 -c "import json; json.load(open('${file}'))" 2>/dev/null; then
    echo "INVALID JSON: ${file}"
    return 1
  fi
  # Check required fields
  for field in "${required_fields[@]}"; do
    local val
    val=$(python3 -c "
import json, sys
d = json.load(open('${file}'))
parts = '${field}'.split('.')
for p in parts:
    if isinstance(d, dict): d = d.get(p)
    else: d = None
if d is None or d == 'null':
    sys.exit(1)
" 2>/dev/null) || {
      echo "NULL field '${field}': ${file}"
      return 1
    }
  done
  echo "OK ($(du -sh "${file}" | cut -f1))"
  return 0
}

scp_dir() {
  local src="$1"
  local dst="$2"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "  [dry-run] would scp -r ${VPS_HOST}:${src} ${dst}"
    return 0
  fi
  mkdir -p "$(dirname "${dst}")"
  scp -r "${VPS_HOST}:${src}" "${dst}" 2>&1 | tail -5 || {
    echo "WARN: scp may have had issues — check output above"
    return 1
  }
}

scp_file() {
  local src="$1"
  local dst="$2"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "  [dry-run] would scp ${VPS_HOST}:${src} ${dst}"
    return 0
  fi
  mkdir -p "$(dirname "${dst}")"
  scp "${VPS_HOST}:${src}" "${dst}" 2>&1 || {
    echo "WARN: scp failed for ${src}"
    return 1
  }
}

# ── SSH connectivity check ─────────────────────────────────────────────────────
if [[ "${DRY_RUN}" -eq 0 ]]; then
  echo ""
  echo "── SSH check ───────────────────────────────────────────────"
  if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "${VPS_HOST}" "echo OK" 2>/dev/null; then
    echo "FATAL: cannot SSH to ${VPS_HOST}" >&2
    echo "       Check VPS IP, SSH key, and that VPS is running" >&2
    exit 1
  fi
  echo "OK  SSH reachable"
fi

# ── Q3 collection ─────────────────────────────────────────────────────────────
if [[ "${COLLECT_Q3}" -eq 1 ]]; then
  echo ""
  echo "── Q3 Latency results ──────────────────────────────────────"
  LOCAL_Q3="${REPO_ROOT}/eval/latency/results"

  # Find latest Q3 run on VPS
  LATEST_Q3_SUMMARY=""
  if [[ "${DRY_RUN}" -eq 0 ]]; then
    LATEST_Q3_SUMMARY=$(ssh "${VPS_HOST}" \
      "ls -t ${VPS_NM}/benchmark/results/q3-summary-*.json 2>/dev/null | head -1" 2>/dev/null || echo "")
    LATEST_Q3_FULL=$(ssh "${VPS_HOST}" \
      "ls -t ${VPS_NM}/benchmark/results/q3-latency-*.json 2>/dev/null | head -1" 2>/dev/null || echo "")
  fi

  if [[ -n "${LATEST_Q3_SUMMARY}" ]]; then
    echo "INFO  latest Q3 summary on VPS: ${LATEST_Q3_SUMMARY}"
    scp_file "${LATEST_Q3_SUMMARY}" "${LOCAL_Q3}/summary.json"
    scp_file "${LATEST_Q3_FULL}"    "${LOCAL_Q3}/full-run.json"

    # Also collect workload-level JSONs if they exist separately
    scp_dir "${VPS_NM}/eval/latency/results/" "${LOCAL_Q3}/" || true
  else
    # Fallback: collect eval/latency/results/ directory
    echo "INFO  collecting eval/latency/results/ directory"
    scp_dir "${VPS_NM}/eval/latency/results/" "${LOCAL_Q3}/"
  fi

  # Validate
  if [[ "${DRY_RUN}" -eq 0 ]]; then
    validate_json "${LOCAL_Q3}/summary.json" "Q3 summary" \
      "workloads" || echo "WARN: Q3 summary validation failed"
  fi
fi

# ── Q1 collection ─────────────────────────────────────────────────────────────
if [[ "${COLLECT_Q1}" -eq 1 ]]; then
  echo ""
  echo "── Q1 LoCoMo results ───────────────────────────────────────"
  LOCAL_Q1="${REPO_ROOT}/eval/locomo/results"
  mkdir -p "${LOCAL_Q1}"

  LATEST_Q1=""
  if [[ "${DRY_RUN}" -eq 0 ]]; then
    LATEST_Q1=$(ssh "${VPS_HOST}" \
      "ls -t ${VPS_NM}/benchmark/results/q1-locomo-*.json 2>/dev/null | head -1" 2>/dev/null || echo "")
    # Fallback to old path
    if [[ -z "${LATEST_Q1}" ]]; then
      LATEST_Q1=$(ssh "${VPS_HOST}" \
        "ls -t ${VPS_NM}/eval/locomo/results/full-run.json 2>/dev/null | head -1" 2>/dev/null || echo "")
    fi
  fi

  if [[ -n "${LATEST_Q1}" ]] || [[ "${DRY_RUN}" -eq 1 ]]; then
    DST="${LOCAL_Q1}/full-run.json"
    if [[ "${DRY_RUN}" -eq 0 ]]; then
      scp_file "${LATEST_Q1}" "${DST}"
    else
      echo "  [dry-run] would collect Q1 result → ${DST}"
    fi
    validate_json "${DST}" "Q1 full-run" "metrics.r5" "metrics.ndcg10" "seed" 2>/dev/null || \
      echo "WARN: Q1 validation (run dry-run 0 first)"
  else
    echo "WARN: no Q1 result found on VPS — run-q1.sh first"
  fi
fi

# ── Q2 collection ─────────────────────────────────────────────────────────────
if [[ "${COLLECT_Q2}" -eq 1 ]]; then
  echo ""
  echo "── Q2 LongMemEval results ──────────────────────────────────"
  LOCAL_Q2="${REPO_ROOT}/eval/longmemeval"
  mkdir -p "${LOCAL_Q2}"

  if [[ "${DRY_RUN}" -eq 0 ]]; then
    # Collect both judge result files
    for JUDGE_TAG in "gpt4o" "gemini25pro"; do
      LATEST=$(ssh "${VPS_HOST}" \
        "ls -t ${VPS_NM}/benchmark/results/q2-longmemeval-${JUDGE_TAG}-*.json 2>/dev/null | head -1" \
        2>/dev/null || echo "")
      # Fallback to old path
      if [[ -z "${LATEST}" ]]; then
        JUDGE_MODEL="gpt4o"
        if [[ "${JUDGE_TAG}" == "gemini25pro" ]]; then JUDGE_MODEL="gemini-2.5-pro"; fi
        LATEST=$(ssh "${VPS_HOST}" \
          "ls -t ${VPS_NM}/eval/longmemeval/full-run.${JUDGE_MODEL//-2.5-pro/25pro}.json 2>/dev/null | head -1" \
          2>/dev/null || echo "")
      fi

      if [[ -n "${LATEST}" ]]; then
        DST_NAME="full-run.${JUDGE_TAG}.json"
        scp_file "${LATEST}" "${LOCAL_Q2}/${DST_NAME}"
        validate_json "${LOCAL_Q2}/${DST_NAME}" "Q2 ${JUDGE_TAG}" \
          "metrics.overall_accuracy" "judge_model" || \
          echo "WARN: Q2 ${JUDGE_TAG} validation issues"
      else
        echo "WARN: no Q2 ${JUDGE_TAG} result found on VPS"
      fi
    done
  else
    echo "  [dry-run] would collect Q2 gpt4o + gemini25pro → ${LOCAL_Q2}/"
  fi
fi

# ── Gate readiness check ──────────────────────────────────────────────────────
echo ""
echo "── Gate readiness ──────────────────────────────────────────"

GATE_READY=1

check_file() {
  local file="$1"
  local label="$2"
  if [[ -f "${file}" ]]; then
    echo "  OK  ${label}: $(du -sh "${file}" | cut -f1)"
  else
    echo "  MISS ${label}: not found at ${file}"
    GATE_READY=0
  fi
}

check_file "${REPO_ROOT}/eval/latency/results/summary.json"  "Q3 latency summary"
check_file "${REPO_ROOT}/eval/locomo/results/full-run.json"  "Q1 LoCoMo full-run"
check_file "${REPO_ROOT}/eval/longmemeval/full-run.gpt4o.json"     "Q2 LME gpt4o"
check_file "${REPO_ROOT}/eval/longmemeval/full-run.gemini25pro.json" "Q2 LME gemini25pro"

echo ""
if [[ "${GATE_READY}" -eq 1 ]]; then
  echo "STATUS: All results present — ready to run generate-comparison.ts"
  echo ""
  echo "Next steps:"
  echo "  1. Review numbers manually:"
  echo "     jq '.metrics.r5' ${REPO_ROOT}/eval/locomo/results/full-run.json"
  echo "     jq '.metrics.overall_accuracy' ${REPO_ROOT}/eval/longmemeval/full-run.gpt4o.json"
  echo "     jq '.workloads[\"search.medium\"].p95_ms' ${REPO_ROOT}/eval/latency/results/summary.json"
  echo ""
  echo "  2. Run gate update (only after manual review):"
  echo "     cd ${REPO_ROOT}"
  echo "     GATE_VERIFIED=1 \\"
  echo "       LOCOMO_RESULTS_DIR=eval/locomo/results \\"
  echo "       LONGMEMEVAL_RESULTS_DIR=eval/longmemeval \\"
  echo "       LATENCY_RESULTS_DIR=eval/latency/results \\"
  echo "       npx tsx benchmark/generate-comparison.ts"
  echo ""
  echo "  3. Verify no 'pending' cells remain:"
  echo "     grep 'pending' ${REPO_ROOT}/benchmark/COMPARISON.md"
  echo ""
  echo "  4. Commit:"
  echo "     git add eval/locomo/results/full-run.json \\"
  echo "       eval/longmemeval/full-run.gpt4o.json \\"
  echo "       eval/longmemeval/full-run.gemini25pro.json \\"
  echo "       eval/latency/results/ \\"
  echo "       benchmark/COMPARISON.md"
  echo "     git commit -m \"data(Q4-gate): Q1+Q2+Q3 VPS results + COMPARISON.md gate opened \$(date +%Y-%m-%d)\""
else
  echo "STATUS: Gate NOT ready — missing result files (see above)"
  echo "        Run the missing benchmarks first, then re-run collect-results.sh"
fi

echo "═══════════════════════════════════════════════════════════"
