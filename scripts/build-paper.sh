#!/usr/bin/env bash
# =============================================================================
# build-paper.sh — Compila paper-tecnico-nox-mem.md → PDF ou .tex via xelatex
#
# Contexto: pdflatex rejeita chars Unicode (Δ Σ ∈ ≈ − ≤ ≥) no segundo pass.
# xelatex resolve nativamente. Diagnóstico: audits/2026-05-22-pandoc-latex-conversion-test.md
# Cross-ref: PR #234 (finding), PR #226 (paper source — NÃO alterar)
#
# USAGE:
#   ./scripts/build-paper.sh                  # Compila PDF (padrão)
#   ./scripts/build-paper.sh --tex-only       # Gera .tex para submissão arXiv
#   ./scripts/build-paper.sh --pdf-only       # Compila PDF local (explícito)
#   ./scripts/build-paper.sh --clean          # Remove artefatos de build
#   ./scripts/build-paper.sh --verbose        # Modo debug (pandoc + xelatex verbose)
#
# Exit codes:
#   0  — sucesso
#   1  — ferramenta ausente (pandoc ou xelatex)
#   2  — arquivo fonte não encontrado
#   3  — falha no build
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Paths (relative to repo root)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PAPER_SRC="${REPO_ROOT}/paper/paper-tecnico-nox-mem.md"
REFS_BIB="${REPO_ROOT}/paper/refs.bib"
BUILD_DIR="${REPO_ROOT}/paper/build"
OUTPUT_PDF="${BUILD_DIR}/paper-tecnico-nox-mem.pdf"
OUTPUT_TEX="${BUILD_DIR}/paper-tecnico-nox-mem.tex"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
MODE="pdf"      # pdf | tex | clean
VERBOSE=false

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
for arg in "$@"; do
  case "$arg" in
    --pdf-only)  MODE="pdf" ;;
    --tex-only)  MODE="tex" ;;
    --clean)     MODE="clean" ;;
    --verbose)   VERBOSE=true ;;
    -h|--help)
      grep '^#' "${BASH_SOURCE[0]}" | head -22 | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "build-paper: opção desconhecida: $arg (use --help)" >&2
      exit 1
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log()  { echo "[build-paper] $*"; }
vlog() { $VERBOSE && echo "[build-paper:verbose] $*" || true; }
err()  { echo "[build-paper:erro] $*" >&2; }

# ---------------------------------------------------------------------------
# Clean mode
# ---------------------------------------------------------------------------
if [[ "$MODE" == "clean" ]]; then
  log "Removendo artefatos em ${BUILD_DIR}/ ..."
  find "${BUILD_DIR}" -not -name ".gitignore" -not -path "${BUILD_DIR}" \
    -type f -delete 2>/dev/null || true
  log "Limpeza concluída."
  exit 0
fi

# ---------------------------------------------------------------------------
# Tool check — exit 1 if missing
# ---------------------------------------------------------------------------
MISSING_TOOLS=()

if ! command -v pandoc &>/dev/null; then
  MISSING_TOOLS+=("pandoc")
fi

if [[ "$MODE" == "pdf" ]] && ! command -v xelatex &>/dev/null; then
  MISSING_TOOLS+=("xelatex (instale via TeX Live: tlmgr install xetex)")
fi

if [[ ${#MISSING_TOOLS[@]} -gt 0 ]]; then
  err "Ferramentas ausentes:"
  for t in "${MISSING_TOOLS[@]}"; do
    err "  - $t"
  done
  err "Instale as dependências e tente novamente."
  exit 1
fi

log "Ferramentas OK: pandoc $(pandoc --version | head -1 | awk '{print $2}')${MODE:+ / xelatex}"

# ---------------------------------------------------------------------------
# Source verification — exit 2 if missing
# ---------------------------------------------------------------------------
if [[ ! -f "$PAPER_SRC" ]]; then
  err "Fonte não encontrada: ${PAPER_SRC}"
  err "Verifique se PR #226 foi mergeado ou se o arquivo existe localmente."
  exit 2
fi

REFS_FLAG=""
if [[ -f "$REFS_BIB" ]]; then
  REFS_FLAG="--bibliography=${REFS_BIB}"
  vlog "Bibliography: ${REFS_BIB}"
else
  log "Aviso: refs.bib não encontrado — compilando sem bibliography."
fi

# ---------------------------------------------------------------------------
# Ensure build dir exists
# ---------------------------------------------------------------------------
mkdir -p "${BUILD_DIR}"

# ---------------------------------------------------------------------------
# LaTeX preamble for Unicode monospace font (fix for xelatex warnings)
# ---------------------------------------------------------------------------
PREAMBLE_FILE="${REPO_ROOT}/paper/preamble.tex"
if [[ ! -f "$PREAMBLE_FILE" ]]; then
  err "Arquivo preamble não encontrado: ${PREAMBLE_FILE}"
  exit 2
fi

# ---------------------------------------------------------------------------
# Pandoc common flags
# ---------------------------------------------------------------------------
PANDOC_BASE_FLAGS=(
  --from=markdown+smart
  --standalone
  --citeproc
  --include-in-header="${PREAMBLE_FILE}"
)

if [[ -n "$REFS_FLAG" ]]; then
  PANDOC_BASE_FLAGS+=("$REFS_FLAG")
fi

if $VERBOSE; then
  PANDOC_BASE_FLAGS+=(--verbose)
fi

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
case "$MODE" in
  # ------ PDF mode --------------------------------------------------------
  pdf)
    log "Compilando PDF via xelatex (bypass Unicode math — PR #234) ..."
    vlog "Saída: ${OUTPUT_PDF}"

    PANDOC_PDF_FLAGS=(
      "${PANDOC_BASE_FLAGS[@]}"
      --pdf-engine=xelatex
      --output="${OUTPUT_PDF}"
    )

    if ! pandoc "${PANDOC_PDF_FLAGS[@]}" "${PAPER_SRC}" 2>&1; then
      err "Falha na compilação PDF. Verifique o log acima."
      exit 3
    fi

    if [[ ! -f "$OUTPUT_PDF" ]]; then
      err "PDF não gerado (pandoc não reportou erro mas arquivo ausente)."
      exit 3
    fi

    PDF_SIZE=$(wc -c < "$OUTPUT_PDF")
    log "PDF gerado com sucesso: ${OUTPUT_PDF} ($(( PDF_SIZE / 1024 )) KB)"
    ;;

  # ------ TeX mode (arXiv upload) ----------------------------------------
  tex)
    log "Gerando .tex para submissão arXiv ..."
    vlog "Saída: ${OUTPUT_TEX}"

    PANDOC_TEX_FLAGS=(
      "${PANDOC_BASE_FLAGS[@]}"
      --to=latex
      --output="${OUTPUT_TEX}"
    )

    if ! pandoc "${PANDOC_TEX_FLAGS[@]}" "${PAPER_SRC}" 2>&1; then
      err "Falha na geração .tex. Verifique o log acima."
      exit 3
    fi

    if [[ ! -f "$OUTPUT_TEX" ]]; then
      err ".tex não gerado (pandoc não reportou erro mas arquivo ausente)."
      exit 3
    fi

    TEX_SIZE=$(wc -c < "$OUTPUT_TEX")
    log ".tex gerado com sucesso: ${OUTPUT_TEX} ($(( TEX_SIZE / 1024 )) KB)"
    log "Nota arXiv: faça upload de ${OUTPUT_TEX} + ${REFS_BIB} juntos."
    ;;
esac

exit 0
