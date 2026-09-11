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
#   ./scripts/build-paper.sh --tmlr           # PDF ANÔNIMO no template do TMLR
#   ./scripts/build-paper.sh --clean          # Remove artefatos de build
#   ./scripts/build-paper.sh --verbose        # Modo debug (pandoc + xelatex verbose)
#
# Exit codes:
#   0  — sucesso
#   1  — ferramenta ausente (pandoc ou xelatex)
#   2  — arquivo fonte não encontrado
#   3  — falha no build
#   4  — vazamento de identidade no PDF do TMLR (modo --tmlr)
#
# Sobre --tmlr: produz a variante de SUBMISSÃO ANÔNIMA (double blind). O
# pipeline é
#   anonimiza-para-tmlr.py --write   (tira nome/email/repo/apelido/DOI/host)
#   monta-tmlr.py --write            (reparte título/abstract/corpo no YAML)
#   pandoc -H preamble-tmlr.tex      (carrega paper/tmlr/tmlr.sty, sem opção)
#   xelatex ×2
#   pdftotext | anonimiza --check    ← GATE, exit 4 se achar qualquer sítio
#
# O gate roda sobre o TEXTO DO PDF, não sobre o .tex: o \author{} do .tex leva
# o nome real de propósito (o tmlr.sty sem [accepted] o suprime) e é o PDF que
# vai para o revisor. Checar o .tex acusaria a autoria declarada e deixaria
# passar qualquer coisa que o LaTeX compusesse por outro caminho.
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
MODE="pdf"      # pdf | tex | tmlr | clean
VERBOSE=false

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
for arg in "$@"; do
  case "$arg" in
    --pdf-only)  MODE="pdf" ;;
    --tex-only)  MODE="tex" ;;
    --tmlr)      MODE="tmlr" ;;
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

if [[ "$MODE" == "pdf" || "$MODE" == "tmlr" ]] && ! command -v xelatex &>/dev/null; then
  MISSING_TOOLS+=("xelatex (instale via TeX Live: tlmgr install xetex)")
fi

if [[ "$MODE" == "tmlr" ]]; then
  command -v python3  &>/dev/null || MISSING_TOOLS+=("python3 (anonimiza/monta)")
  # sem pdftotext o gate de vazamento não roda, e um gate que não roda é
  # indistinguível de um gate que passou — por isso é ferramenta obrigatória
  command -v pdftotext &>/dev/null || MISSING_TOOLS+=("pdftotext (poppler) — sem ele o gate de anonimato não roda")
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

  # ------ TMLR mode (submissão anônima, double blind) --------------------
  tmlr)
    TMLR_DIR="${BUILD_DIR}/tmlr"
    TMLR_STY_DIR="${REPO_ROOT}/paper/tmlr"
    TMLR_PREAMBLE="${REPO_ROOT}/paper/preamble-tmlr.tex"
    SCRIPTS_DIR="${REPO_ROOT}/paper/publication/scripts"
    ANONIMIZA="${SCRIPTS_DIR}/anonimiza-para-tmlr.py"
    MONTA="${SCRIPTS_DIR}/monta-tmlr.py"

    for f in "${TMLR_STY_DIR}/tmlr.sty" "${TMLR_PREAMBLE}" "${ANONIMIZA}" "${MONTA}"; do
      [[ -f "$f" ]] || { err "peça ausente: $f"; exit 2; }
    done

    # o shasum das peças vendoradas é parte da reprodutibilidade
    if command -v shasum &>/dev/null && [[ -f "${TMLR_STY_DIR}/SHA256SUMS" ]]; then
      ( cd "${TMLR_STY_DIR}" && shasum -a 256 -c SHA256SUMS >/dev/null 2>&1 ) \
        || { err "tmlr.sty/tmlr.bst divergem do SHA256SUMS vendorado"; exit 3; }
      vlog "SHA256SUMS do tmlr confere"
    fi

    mkdir -p "${TMLR_DIR}"

    log "1/5 anonimizando (nome, email, repo, apelido, DOI, afiliação, host) ..."
    if ! python3 "${ANONIMIZA}" --write "${TMLR_DIR}/paper-anon.md"; then
      err "o filtro de anonimização abortou — NÃO seguir com o build"
      exit 4
    fi

    log "2/5 repartindo título / abstract / corpo ..."
    if ! python3 "${MONTA}" --write "${TMLR_DIR}" --fonte "${TMLR_DIR}/paper-anon.md"; then
      err "o corte para o template do TMLR abortou"
      exit 3
    fi

    log "3/5 pandoc → LaTeX (template do pandoc + tmlr.sty) ..."
    cp "${TMLR_PREAMBLE}" "${TMLR_DIR}/preamble-tmlr.tex"
    PANDOC_TMLR_FLAGS=(
      --from=markdown+smart
      --standalone
      --to=latex
      -V documentclass=article
      -V classoption=10pt
      --include-in-header="${TMLR_DIR}/preamble-tmlr.tex"
      --output="${TMLR_DIR}/tmlr.tex"
    )
    $VERBOSE && PANDOC_TMLR_FLAGS+=(--verbose)
    if ! pandoc "${PANDOC_TMLR_FLAGS[@]}" "${TMLR_DIR}/tmlr-full.md"; then
      err "pandoc falhou na variante TMLR"
      exit 3
    fi

    log "4/5 xelatex (2 passadas) ..."
    (
      cd "${TMLR_DIR}"
      export TEXINPUTS="${TMLR_STY_DIR}:"
      xelatex -interaction=nonstopmode tmlr.tex > tmlr-pass1.log 2>&1 || true
      xelatex -interaction=nonstopmode tmlr.tex > tmlr-pass2.log 2>&1 || true
    )

    # ⚠️ conferir que SAIU PDF antes de contar qualquer coisa: um build que
    # parou dá 0 overfull e 0 vazamentos, e os dois zeros leem-se como
    # "está limpo" quando significam "não medi". Aconteceu em 2026-09-11
    # com um \usepackage ausente.
    TMLR_PAGES=$(grep -o 'Output written on tmlr.pdf ([0-9]* page' "${TMLR_DIR}/tmlr-pass2.log" 2>/dev/null | grep -o '[0-9]*' || true)
    if [[ ! -f "${TMLR_DIR}/tmlr.pdf" || -z "${TMLR_PAGES}" ]]; then
      err "xelatex não produziu PDF. Erros:"
      grep -n -A4 '^!' "${TMLR_DIR}/tmlr-pass2.log" 2>/dev/null | head -30 >&2 || true
      exit 3
    fi
    TMLR_ERRORS=$(grep -c '^!' "${TMLR_DIR}/tmlr-pass2.log" || true)
    if [[ "${TMLR_ERRORS}" -gt 0 ]]; then
      err "xelatex produziu PDF com ${TMLR_ERRORS} erro(s):"
      grep -n -A4 '^!' "${TMLR_DIR}/tmlr-pass2.log" | head -30 >&2
      exit 3
    fi

    log "5/5 GATE de anonimato sobre o TEXTO DO PDF ..."
    if ! pdftotext "${TMLR_DIR}/tmlr.pdf" "${TMLR_DIR}/tmlr.txt"; then
      err "pdftotext falhou — o gate não rodou, portanto o build NÃO passou"
      exit 4
    fi
    if [[ ! -s "${TMLR_DIR}/tmlr.txt" ]]; then
      err "o texto extraído do PDF está vazio — o gate leria 0 vazamentos por não ter lido nada"
      exit 4
    fi
    if ! python3 "${ANONIMIZA}" --check "${TMLR_DIR}/tmlr.txt"; then
      err "VAZAMENTO DE IDENTIDADE no PDF do TMLR — não submeter"
      exit 4
    fi

    TMLR_OVERFULL=$(grep -c 'Overfull \\hbox' "${TMLR_DIR}/tmlr-pass2.log" || true)
    PDF_SIZE=$(wc -c < "${TMLR_DIR}/tmlr.pdf")
    log "PDF anônimo do TMLR: ${TMLR_DIR}/tmlr.pdf"
    log "  ${TMLR_PAGES} páginas · $(( PDF_SIZE / 1024 )) KB · 0 erros · ${TMLR_OVERFULL} overfull \\hbox"
    log "  autoria fica em \\author{} no .tex e é suprimida pelo tmlr.sty sem [accepted]"
    log "  camera-ready: trocar por \\usepackage[accepted]{tmlr} e definir \\month/\\year/\\openreview"
    ;;
esac

exit 0
