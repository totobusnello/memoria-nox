#!/usr/bin/env bash
# =============================================================================
# build-paper.test.sh — Smoke tests para scripts/build-paper.sh
#
# Testa:
#   1. --tex-only  : .tex gerado e não-vazio
#   2. --pdf-only  : PDF gerado >= 50 KB (detecta falhas óbvias)
#   3. --clean     : artefatos removidos após testes
#
# USAGE:
#   ./scripts/build-paper.test.sh
#
# Exit codes:
#   0  — todos os testes passaram
#   1  — um ou mais testes falharam
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUILD_DIR="${REPO_ROOT}/paper/build"
BUILD_SCRIPT="${SCRIPT_DIR}/build-paper.sh"

PASS=0
FAIL=0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
ok()   { echo "[PASS] $*"; (( PASS++ )) || true; }
fail() { echo "[FAIL] $*"; (( FAIL++ )) || true; }
log()  { echo "[test]  $*"; }

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------
if [[ ! -x "$BUILD_SCRIPT" ]]; then
  echo "[test:erro] build-paper.sh não encontrado ou não executável: ${BUILD_SCRIPT}" >&2
  exit 1
fi

log "Iniciando smoke tests: build-paper.sh"
log "Repo: ${REPO_ROOT}"
echo ""

# ---------------------------------------------------------------------------
# Test 1 — --tex-only: .tex gerado
# ---------------------------------------------------------------------------
log "Test 1: --tex-only gera .tex ..."

OUTPUT_TEX="${BUILD_DIR}/paper-tecnico-nox-mem.tex"

if "${BUILD_SCRIPT}" --tex-only 2>&1; then
  if [[ -f "$OUTPUT_TEX" && -s "$OUTPUT_TEX" ]]; then
    TEX_SIZE=$(wc -c < "$OUTPUT_TEX")
    ok "Test 1: .tex gerado (${TEX_SIZE} bytes)"
  else
    fail "Test 1: .tex ausente ou vazio após --tex-only"
  fi
else
  fail "Test 1: build-paper.sh --tex-only saiu com erro"
fi

echo ""

# ---------------------------------------------------------------------------
# Test 2 — --pdf-only: PDF gerado >= 50 KB
# ---------------------------------------------------------------------------
log "Test 2: --pdf-only gera PDF >= 50 KB ..."

OUTPUT_PDF="${BUILD_DIR}/paper-tecnico-nox-mem.pdf"
MIN_PDF_BYTES=51200  # 50 KB

if "${BUILD_SCRIPT}" --pdf-only 2>&1; then
  if [[ -f "$OUTPUT_PDF" ]]; then
    PDF_SIZE=$(wc -c < "$OUTPUT_PDF")
    if (( PDF_SIZE >= MIN_PDF_BYTES )); then
      ok "Test 2: PDF gerado ($(( PDF_SIZE / 1024 )) KB >= 50 KB mínimo)"
    else
      fail "Test 2: PDF muito pequeno — ${PDF_SIZE} bytes (< ${MIN_PDF_BYTES}) — provável falha silenciosa"
    fi
  else
    fail "Test 2: PDF ausente após --pdf-only"
  fi
else
  fail "Test 2: build-paper.sh --pdf-only saiu com erro"
fi

echo ""

# ---------------------------------------------------------------------------
# Test 3 — --clean: artefatos removidos
# ---------------------------------------------------------------------------
log "Test 3: --clean remove artefatos ..."

if "${BUILD_SCRIPT}" --clean 2>&1; then
  LEFTOVER_FILES=$(find "${BUILD_DIR}" -not -name ".gitignore" -not -path "${BUILD_DIR}" -type f 2>/dev/null | wc -l | tr -d ' ')
  if (( LEFTOVER_FILES == 0 )); then
    ok "Test 3: --clean removeu todos os artefatos"
  else
    fail "Test 3: --clean deixou ${LEFTOVER_FILES} arquivo(s) em paper/build/"
  fi
else
  fail "Test 3: build-paper.sh --clean saiu com erro"
fi

echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
TOTAL=$(( PASS + FAIL ))
echo "========================================"
echo "Resultado: ${PASS}/${TOTAL} testes passaram"
echo "========================================"

if (( FAIL > 0 )); then
  exit 1
fi

exit 0
