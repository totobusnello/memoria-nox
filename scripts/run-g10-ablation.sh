#!/usr/bin/env bash
# ============================================================================
# G10 — Hard Mutex (section ↔ source_type) validation contra G9 baseline
# ============================================================================
#
# Mede o efeito do Hard Mutex (PR #182, env NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE)
# em três configs sobre o mesmo fixture g5.db / queries.jsonl que G9 rodou
# (2026-05-20), produzindo números comparable diretamente.
#
# CONFIGS:
#   A8'   (mutex ATIVO)        — default no código pós-PR #182      → esperado ≥ 0.5530
#   A8    (mutex DESATIVADO)   — NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1 → sanity ≈ 0.5387
#   A10   (full minus src_type) NOX_DISABLE_SOURCE_TYPE_BOOST=1     → sanity ≈ 0.5530
#
# PRECONDIÇÕES (verificar antes de rodar):
#   1. SSH ativo pra root@187.77.234.79
#   2. PR #182 (Hard Mutex) deployed em prod: /root/.openclaw/workspace/tools/nox-mem/dist/
#   3. g5.db existe íntegro em /root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20/g5.db (~1.2GB)
#   4. queries.jsonl + corpus.jsonl no mesmo fixture dir
#   5. Porta 18803 LIVRE (NÃO 18802 prod)
#
# REGRA DE OURO: NUNCA tocar /api/health prod (porta 18802). O eval roda em
# instância separada na porta 18803 com NOX_DB_PATH apontando pra g5.db.
#
# REPRO G9 BASELINE (sanity check antes de G10):
#   - Rodar A0 só (sem boosts) e conferir nDCG@10 ≈ 0.4108 (±0.005)
#   - Se DIFERENTE: G9 numbers eram artifact ou fixture mudou → ABORT
#
# USO:
#   # Sanity check primeiro (~3min):
#   bash run-g10-ablation.sh --sanity
#
#   # Full G10 (~12min serial, ~3min per config):
#   bash run-g10-ablation.sh --full
#
#   # Single config:
#   bash run-g10-ablation.sh --config A8-prime
# ============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Config — paths VPS (todos absolutos)
# ---------------------------------------------------------------------------
FIXTURE_DIR="/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20"
G5_DB="${FIXTURE_DIR}/g5.db"
NOX_MEM_DIR="/root/.openclaw/workspace/tools/nox-mem"
EVAL_PORT=18803
EVAL_ENDPOINT="http://127.0.0.1:${EVAL_PORT}/api/search"
EVAL_HARNESS="${NOX_MEM_DIR}/paper/publication/baselines/entity_ablation_eval.py"

# Resultados locais (na VPS) — depois rsync pra repo
OUT_DIR="${FIXTURE_DIR}/g10-results-$(date +%Y-%m-%dT%H%M%S)"
mkdir -p "${OUT_DIR}"
LOG="${OUT_DIR}/g10-ablations.log"

# Defesa em camadas — isolation guards (postmortem 2026-05-19)
export NOX_EVAL_DB_PATH="${G5_DB}"
export NOX_ALLOW_PROD_INGEST=0  # never ingest in eval mode
unset NOX_EVAL_ISOLATION_OVERRIDE  # never bypass

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------
preflight() {
  echo "[preflight] checking g5.db" | tee -a "${LOG}"
  [[ -f "${G5_DB}" ]] || { echo "FATAL: g5.db not at ${G5_DB}"; exit 1; }
  local size
  size=$(stat -c%s "${G5_DB}")
  if [[ "${size}" -lt $((100 * 1024 * 1024)) ]]; then
    echo "FATAL: g5.db is ${size} bytes (<100MB) — looks like stub, not real DB" | tee -a "${LOG}"
    echo "        check /root/.openclaw/workspace/eval-data/g5-2026-05-20/g5.db (1.2GB) instead" | tee -a "${LOG}"
    exit 1
  fi
  echo "[preflight] g5.db size: $((size / 1024 / 1024))MB OK" | tee -a "${LOG}"

  # Verify chunks + vec_chunks populated
  local chunks vec_chunks
  chunks=$(sqlite3 "${G5_DB}" "SELECT COUNT(*) FROM chunks;" 2>/dev/null || echo 0)
  vec_chunks=$(sqlite3 "${G5_DB}" "SELECT COUNT(*) FROM vec_chunks;" 2>/dev/null || echo 0)
  echo "[preflight] chunks=${chunks} vec_chunks=${vec_chunks}" | tee -a "${LOG}"
  [[ "${chunks}" -gt 1000 ]] || { echo "FATAL: chunks=${chunks} (expected ~69k)"; exit 1; }
  [[ "${vec_chunks}" -gt 1000 ]] || {
    echo "WARN: vec_chunks=${vec_chunks} — semantic layer will fall back to FTS-only" | tee -a "${LOG}"
    echo "      consider re-vectorize: nox-mem vectorize --db=${G5_DB}" | tee -a "${LOG}"
  }

  # Verify harness exists
  [[ -f "${EVAL_HARNESS}" ]] || { echo "FATAL: harness missing ${EVAL_HARNESS}"; exit 1; }

  # Verify mutex code is deployed (look for the env-var string in dist)
  if ! grep -q "DISABLE_MUTEX_SECTION_SOURCE_TYPE" "${NOX_MEM_DIR}/dist/search.js" 2>/dev/null; then
    echo "FATAL: Hard Mutex not in dist/search.js — PR #182 not deployed?" | tee -a "${LOG}"
    echo "       rebuild: cd ${NOX_MEM_DIR} && npm run build" | tee -a "${LOG}"
    exit 1
  fi
  echo "[preflight] Hard Mutex code present in dist OK" | tee -a "${LOG}"
}

# ---------------------------------------------------------------------------
# Start eval API on port 18803 with given env overrides
# ---------------------------------------------------------------------------
start_eval_api() {
  local config_name="$1"
  shift  # remaining args are KEY=VAL pairs

  # Kill any prior instance on 18803
  pkill -f "NOX_API_PORT=${EVAL_PORT}" 2>/dev/null || true
  sleep 2

  echo "[api:${config_name}] starting on :${EVAL_PORT} with overrides: $*" | tee -a "${LOG}"
  local extra_env=""
  for kv in "$@"; do
    extra_env="${extra_env} ${kv}"
  done

  # Source prod .env for Gemini key (CLAUDE.md §1), then override DB + port + ablation flags
  (
    set -a; source /root/.openclaw/.env; set +a
    export NOX_DB_PATH="${G5_DB}"
    export NOX_API_PORT="${EVAL_PORT}"
    export OPENCLAW_WORKSPACE="/tmp/g10-isolated-$$"  # belt-and-suspenders
    mkdir -p "${OPENCLAW_WORKSPACE}/tools/nox-mem"
    # eval-only ablation flags
    for kv in "$@"; do
      export "${kv?}"
    done
    cd "${NOX_MEM_DIR}"
    nohup node dist/api-server.js \
      > "${OUT_DIR}/api-${config_name}.log" 2>&1 &
    echo $! > "${OUT_DIR}/api-${config_name}.pid"
  )

  # Wait for /api/health
  local deadline=$((SECONDS + 60))
  while (( SECONDS < deadline )); do
    if curl -sf "http://127.0.0.1:${EVAL_PORT}/api/health" \
         | jq -e '.status == "ok"' >/dev/null 2>&1; then
      local chunks
      chunks=$(curl -sf "http://127.0.0.1:${EVAL_PORT}/api/health" | jq -r '.chunks // "?"')
      echo "[api:${config_name}] up — chunks=${chunks}" | tee -a "${LOG}"
      return 0
    fi
    sleep 2
  done
  echo "[api:${config_name}] FAILED to come up in 60s" | tee -a "${LOG}"
  tail -50 "${OUT_DIR}/api-${config_name}.log" | tee -a "${LOG}"
  return 1
}

stop_eval_api() {
  local config_name="$1"
  local pidfile="${OUT_DIR}/api-${config_name}.pid"
  [[ -f "${pidfile}" ]] || return 0
  local pid
  pid=$(cat "${pidfile}")
  kill "${pid}" 2>/dev/null || true
  sleep 2
  kill -9 "${pid}" 2>/dev/null || true
  rm -f "${pidfile}"
}

# ---------------------------------------------------------------------------
# Run one ablation config
# ---------------------------------------------------------------------------
run_config() {
  local label="$1"
  local desc="$2"
  shift 2
  # remaining args = KEY=VAL pairs for the API process

  echo "============================================================" | tee -a "${LOG}"
  echo "CONFIG: ${label} — ${desc}" | tee -a "${LOG}"
  echo "  env overrides: $*" | tee -a "${LOG}"
  echo "============================================================" | tee -a "${LOG}"

  start_eval_api "${label}" "$@" || { echo "[${label}] api start failed"; return 1; }

  # Run the harness — endpoint hard-coded to :18803, isolation guard active
  python3 "${EVAL_HARNESS}" \
    --label "${label}" \
    --out "${OUT_DIR}/${label}.json" \
    --fixture-dir "${FIXTURE_DIR}" \
    --endpoint "${EVAL_ENDPOINT}" \
    --n 100 \
    --toggles "$(IFS=,; echo "$*")" \
    2>&1 | tee -a "${LOG}"

  stop_eval_api "${label}"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
mode="${1:-}"

case "${mode}" in
  --sanity)
    preflight
    # Reproduce G9 A0 only — must match 0.4108 ± 0.005
    run_config "A0_sanity" "no boosts (sanity vs G9=0.4108)" \
      "NOX_DISABLE_BOOSTS=1" "NOX_SALIENCE_MODE=off"
    ;;

  --full)
    preflight

    # 1. A8' — mutex ACTIVE (default pós-PR #182, no env flag)
    run_config "A8_prime_mutex_active" \
      "full canonical + Hard Mutex active (default pós-PR #182)"

    # 2. A8 — mutex DISABLED (sanity vs G9=0.5387)
    run_config "A8_mutex_disabled" \
      "full canonical, mutex OFF (sanity vs G9 A8=0.5387)" \
      "NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1"

    # 3. A10 — full minus source_type (sanity vs G9=0.5530)
    run_config "A10_full_minus_source_type" \
      "full canonical, source_type OFF (sanity vs G9 A10=0.5530)" \
      "NOX_DISABLE_SOURCE_TYPE_BOOST=1"
    ;;

  --config)
    config="${2:-}"
    preflight
    case "${config}" in
      A8-prime)
        run_config "A8_prime_mutex_active" "full + mutex active (default)"
        ;;
      A8)
        run_config "A8_mutex_disabled" "full + mutex OFF" \
          "NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1"
        ;;
      A10)
        run_config "A10_full_minus_source_type" "full minus source_type" \
          "NOX_DISABLE_SOURCE_TYPE_BOOST=1"
        ;;
      *) echo "unknown config: ${config}"; exit 1 ;;
    esac
    ;;

  *)
    cat <<USAGE
Usage:
  $0 --sanity              # reproduce G9 A0=0.4108 baseline (~3min)
  $0 --full                # run A8' + A8 + A10 serial (~12min)
  $0 --config A8-prime     # single config

Output: ${OUT_DIR}/
Log:    ${LOG}
USAGE
    exit 1
    ;;
esac

# Compact summary at end
echo "" | tee -a "${LOG}"
echo "===== FINAL SUMMARY =====" | tee -a "${LOG}"
for f in "${OUT_DIR}"/*.json; do
  [[ -f "${f}" ]] || continue
  label=$(basename "${f}" .json)
  ndcg=$(jq -r '.summary.ndcg_at_10' "${f}")
  mrr=$(jq -r '.summary.mrr' "${f}")
  r10=$(jq -r '.summary.recall_at_10' "${f}")
  printf "%-35s nDCG@10=%.4f  MRR=%.4f  R@10=%.4f\n" \
    "${label}" "${ndcg}" "${mrr}" "${r10}" | tee -a "${LOG}"
done

echo "" | tee -a "${LOG}"
echo "Results dir: ${OUT_DIR}" | tee -a "${LOG}"
echo "Pull back to repo with:" | tee -a "${LOG}"
echo "  rsync -av root@187.77.234.79:${OUT_DIR}/ docs/RESEARCH/g10-mutex-2026-05-20/" | tee -a "${LOG}"
