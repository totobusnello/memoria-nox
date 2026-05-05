#!/usr/bin/env bash
# pre-flight-smoke-tests.sh — NOX-Supermem arXiv submission pre-flight
# Executar a partir da raiz do repo: bash paper/publication/scripts/pre-flight-smoke-tests.sh
# Saída: ✓/✗/⚠ por check; exit 0 se pronto, exit 1 se há bloqueio.
#
# NOTA: -e desativado intencionalmente — queremos continuar após falhas.
set -uo pipefail

# ---------------------------------------------------------------------------
# Cores e símbolos
# ---------------------------------------------------------------------------
GREEN='\033[32m'
RED='\033[31m'
YELLOW='\033[33m'
BOLD='\033[1m'
RESET='\033[0m'

OK="${GREEN}✓${RESET}"
FAIL="${RED}✗${RESET}"
WARN="${YELLOW}⚠${RESET}"

# ---------------------------------------------------------------------------
# Estado global
# ---------------------------------------------------------------------------
FAILURES=0
WARNINGS=0
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PUB_DIR="${REPO_ROOT}/paper/publication"
LATEX_DIR="${PUB_DIR}/latex"
FIGS_DIR="${LATEX_DIR}/figures"
TINYTEX_BIN="/Users/lab/Library/TinyTeX/bin/universal-darwin"
PDF_TARGET="${LATEX_DIR}/pain-shadow-memory-2026.pdf"

# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------
pad_label() {
  # Imprime label com padding fixo de 40 chars
  printf "%-40s" "$1"
}

mark_fail() {
  FAILURES=$((FAILURES + 1))
}

mark_warn() {
  WARNINGS=$((WARNINGS + 1))
}

# ---------------------------------------------------------------------------
# Cabeçalho
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}=== NOX-Supermem Pre-flight Smoke Tests ===${RESET}"
echo "Submission target: arXiv cs.IR 2026-06-02"
echo "Repo root: ${REPO_ROOT}"
echo ""

# ---------------------------------------------------------------------------
# [1/10] Git state
# ---------------------------------------------------------------------------
check_git_state() {
  local label="[1/10] Git state"
  local branch clean tag_ok
  local notes=()
  local status=ok

  branch="$(git -C "${REPO_ROOT}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo UNKNOWN)"
  if [[ "${branch}" != "main" ]]; then
    notes+=("branch=${branch} (esperado: main)")
    status=fail
  fi

  local dirty
  dirty="$(git -C "${REPO_ROOT}" status --porcelain 2>/dev/null)"
  if [[ -n "${dirty}" ]]; then
    local n
    n=$(echo "${dirty}" | wc -l | tr -d ' ')
    notes+=("${n} arquivo(s) com mudanças não commitadas")
    status=fail
  fi

  if ! git -C "${REPO_ROOT}" tag --contains HEAD 2>/dev/null | grep -qE "^v1\.0\.0$"; then
    notes+=("tag v1.0.0 ausente em HEAD")
    status=fail
  fi

  printf "%s " "$(pad_label "${label}")"
  if [[ "${status}" == "ok" ]]; then
    echo -e "${OK} on main, clean, tag v1.0.0"
  else
    echo -e "${FAIL} $(IFS='; '; echo "${notes[*]}")"
    mark_fail
  fi
}
check_git_state

# ---------------------------------------------------------------------------
# [2/10] File existence
# ---------------------------------------------------------------------------
check_file_existence() {
  local label="[2/10] File existence"
  local missing=()

  local required_files=(
    "${LATEX_DIR}/main.tex"
    "${LATEX_DIR}/sec_abstract.tex"
    "${LATEX_DIR}/sec_1_3.tex"
    "${LATEX_DIR}/sec_4_7.tex"
    "${LATEX_DIR}/neurips_2024.sty"
    "${PUB_DIR}/refs.bib"
    "${FIGS_DIR}/figure1.pdf"
    "${FIGS_DIR}/figure2.pdf"
    "${FIGS_DIR}/figure3.pdf"
    "${FIGS_DIR}/figure4.pdf"
    "${PUB_DIR}/paper-abstract.md"
    "${REPO_ROOT}/eval/golden-queries.jsonl"
    "${REPO_ROOT}/CITATION.cff"
    "${REPO_ROOT}/LICENSE"
  )

  for f in "${required_files[@]}"; do
    if [[ ! -f "${f}" ]]; then
      missing+=("$(basename "${f}")")
    fi
  done

  printf "%s " "$(pad_label "${label}")"
  if [[ ${#missing[@]} -eq 0 ]]; then
    echo -e "${OK} todos os 14 arquivos obrigatórios presentes"
  else
    echo -e "${FAIL} ausentes: $(IFS=', '; echo "${missing[*]}")"
    mark_fail
  fi
}
check_file_existence

# ---------------------------------------------------------------------------
# [3/10] LaTeX compile clean
# ---------------------------------------------------------------------------
check_latex_compile() {
  local label="[3/10] LaTeX compile clean"

  # Verificar se TinyTeX está disponível
  if [[ ! -d "${TINYTEX_BIN}" ]]; then
    printf "%s " "$(pad_label "${label}")"
    echo -e "${WARN} TinyTeX não encontrado em ${TINYTEX_BIN} — pulando compilação"
    mark_warn
    return
  fi

  local PDFLATEX="${TINYTEX_BIN}/pdflatex"
  local BIBTEX="${TINYTEX_BIN}/bibtex"

  if [[ ! -x "${PDFLATEX}" ]] || [[ ! -x "${BIBTEX}" ]]; then
    printf "%s " "$(pad_label "${label}")"
    echo -e "${WARN} pdflatex/bibtex não executáveis — pulando compilação"
    mark_warn
    return
  fi

  local tmpdir
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "${tmpdir}"' RETURN

  # Espelha a estrutura real do repo: paper/publication/refs.bib + paper/publication/latex/*.tex
  # main.aux gera \bibdata{../refs} — refs.bib precisa estar no parent do diretório de compilação.
  mkdir -p "${tmpdir}/latex"
  cp -r "${LATEX_DIR}/." "${tmpdir}/latex/"
  cp "${PUB_DIR}/refs.bib" "${tmpdir}/" 2>/dev/null || true

  local log1 log2 log3 log_bib
  local errors=0 undef_cit=0 questionmarks=0 overfull_big=0 pages=0 kb_size=0

  (
    cd "${tmpdir}/latex"
    # Passo 1
    "${PDFLATEX}" -interaction=nonstopmode -halt-on-error main.tex >"${tmpdir}/run1.log" 2>&1 || true
    # BibTeX
    "${BIBTEX}" main >"${tmpdir}/bib.log" 2>&1 || true
    # Passo 2
    "${PDFLATEX}" -interaction=nonstopmode -halt-on-error main.tex >"${tmpdir}/run2.log" 2>&1 || true
    # Passo 3
    "${PDFLATEX}" -interaction=nonstopmode -halt-on-error main.tex >"${tmpdir}/run3.log" 2>&1 || true
  )

  local final_log="${tmpdir}/run3.log"

  # Contar erros do LaTeX (linhas com "! " no início)
  errors=$(grep -c "^! " "${final_log}" 2>/dev/null || true)

  # Citações indefinidas
  undef_cit=$(grep -c "Citation .* undefined" "${final_log}" 2>/dev/null || true)

  # Marcadores ??
  questionmarks=$(grep -c "??" "${final_log}" 2>/dev/null || true)

  # Overfull boxes > 50pt
  overfull_big=$(grep -oE "Overfull \\\\hbox \([0-9]+(\.[0-9]+)?pt too wide\)" "${final_log}" 2>/dev/null \
    | grep -oE "[0-9]+(\.[0-9]+)?pt" \
    | awk -F'pt' '{if ($1+0 > 50) count++} END {print count+0}' || echo 0)

  # Páginas
  pages=$(grep -oE "[0-9]+ page" "${final_log}" 2>/dev/null | tail -1 | grep -oE "^[0-9]+" || echo 0)

  # Tamanho do PDF gerado
  if [[ -f "${tmpdir}/latex/main.pdf" ]]; then
    kb_size=$(du -k "${tmpdir}/latex/main.pdf" | cut -f1)
  fi

  local notes=()
  local status=ok

  if [[ "${errors}" -gt 0 ]]; then
    notes+=("${errors} erro(s) LaTeX")
    status=fail
  fi
  if [[ "${undef_cit}" -gt 0 ]]; then
    notes+=("${undef_cit} citação(ões) indefinida(s)")
    status=fail
  fi
  # ?? markers em PDFs LaTeX — se muitos, é bloqueio
  if [[ "${questionmarks}" -gt 10 ]]; then
    notes+=("${questionmarks} marcadores ?? (refs quebradas)")
    status=fail
  elif [[ "${questionmarks}" -gt 0 ]]; then
    notes+=("${questionmarks} marcador(es) ?? (aviso)")
    [[ "${status}" == "ok" ]] && status=warn
  fi

  if [[ "${overfull_big}" -gt 0 ]]; then
    notes+=("${overfull_big} overfull >50pt")
    [[ "${status}" == "ok" ]] && status=warn
  fi

  printf "%s " "$(pad_label "${label}")"
  if [[ "${status}" == "ok" ]]; then
    echo -e "${OK} ${pages} páginas, 0 erros, 0 orphans, ${overfull_big} overfull big — ${kb_size}KB"
  elif [[ "${status}" == "warn" ]]; then
    echo -e "${WARN} ${pages} páginas — $(IFS='; '; echo "${notes[*]}")"
    mark_warn
  else
    echo -e "${FAIL} $(IFS='; '; echo "${notes[*]}")"
    mark_fail
  fi
}
check_latex_compile

# ---------------------------------------------------------------------------
# [4/10] PDF integrity
# ---------------------------------------------------------------------------
check_pdf_integrity() {
  local label="[4/10] PDF integrity"
  local notes=()
  local status=ok

  if [[ ! -f "${PDF_TARGET}" ]]; then
    printf "%s " "$(pad_label "${label}")"
    echo -e "${FAIL} ${PDF_TARGET} não encontrado"
    mark_fail
    return
  fi

  # Tamanho em bytes
  local size_bytes
  size_bytes=$(wc -c < "${PDF_TARGET}" | tr -d ' ')
  local size_kb=$(( size_bytes / 1024 ))
  local min_bytes=$(( 100 * 1024 ))
  local max_bytes=$(( 50 * 1024 * 1024 ))

  if [[ "${size_bytes}" -lt "${min_bytes}" ]]; then
    notes+=("PDF muito pequeno: ${size_kb}KB (min 100KB)")
    status=fail
  elif [[ "${size_bytes}" -gt "${max_bytes}" ]]; then
    notes+=("PDF muito grande: ${size_kb}KB (max 50MB)")
    status=fail
  fi

  # Contagem de páginas via strings (fallback sem pdfinfo)
  local pages=0
  if command -v pdfinfo >/dev/null 2>&1; then
    pages=$(pdfinfo "${PDF_TARGET}" 2>/dev/null | grep "^Pages:" | awk '{print $2}' || echo 0)
  else
    # Heurística: contar ocorrências de /Page no PDF
    pages=$(strings "${PDF_TARGET}" 2>/dev/null | grep -c "^/Page$" || echo 0)
  fi

  if [[ "${pages}" -gt 0 ]]; then
    if [[ "${pages}" -lt 18 ]]; then
      notes+=("${pages} páginas (min 18)")
      status=fail
    elif [[ "${pages}" -gt 32 ]]; then
      notes+=("${pages} páginas (max 32)")
      status=warn
      [[ "${status}" == "ok" ]] && status=warn
    fi
  fi

  # Contagem de palavras extraídas
  local words=0
  if command -v pdftotext >/dev/null 2>&1; then
    words=$(pdftotext "${PDF_TARGET}" - 2>/dev/null | wc -w | tr -d ' ')
    if [[ "${words}" -lt 5000 ]]; then
      notes+=("apenas ${words} palavras extraídas (min 5000)")
      status=fail
    fi
  else
    notes+=("pdftotext não disponível — contagem de palavras pulada")
    [[ "${status}" == "ok" ]] && status=warn
  fi

  printf "%s " "$(pad_label "${label}")"
  if [[ "${status}" == "ok" ]]; then
    echo -e "${OK} ${size_kb}KB, ${pages} páginas, ${words} palavras extraídas"
  elif [[ "${status}" == "warn" ]]; then
    echo -e "${WARN} ${size_kb}KB, ${pages} páginas, ${words} palavras — $(IFS='; '; echo "${notes[*]}")"
    mark_warn
  else
    echo -e "${FAIL} $(IFS='; '; echo "${notes[*]}")"
    mark_fail
  fi
}
check_pdf_integrity

# ---------------------------------------------------------------------------
# [5/10] Citation graph
# ---------------------------------------------------------------------------
check_citation_graph() {
  local label="[5/10] Citation graph"

  local validate_script="${LATEX_DIR}/validate-tex.py"
  if [[ ! -f "${validate_script}" ]]; then
    printf "%s " "$(pad_label "${label}")"
    echo -e "${WARN} validate-tex.py não encontrado em ${validate_script}"
    mark_warn
    return
  fi

  if ! command -v python3 >/dev/null 2>&1; then
    printf "%s " "$(pad_label "${label}")"
    echo -e "${WARN} python3 não disponível — pulando validate-tex.py"
    mark_warn
    return
  fi

  local out
  out=$(cd "${REPO_ROOT}" && python3 "${validate_script}" 2>&1) || true

  local orphans=0
  # Captura padrão "N orphan" ou "orphans: N"
  orphans=$(echo "${out}" | grep -oiE "[0-9]+ orphan" | grep -oE "^[0-9]+" || true)
  orphans=${orphans:-0}

  # Cited/defined counts se o script os reportar
  local cited defined
  cited=$(echo "${out}" | grep -oiE "cited: [0-9]+" | grep -oE "[0-9]+" | tail -1 || echo "?")
  defined=$(echo "${out}" | grep -oiE "defined: [0-9]+" | grep -oE "[0-9]+" | tail -1 || echo "?")

  printf "%s " "$(pad_label "${label}")"
  if echo "${out}" | grep -qi "error\|FAIL\|orphan"; then
    if [[ "${orphans}" -gt 0 ]]; then
      echo -e "${FAIL} ${orphans} orphan(s) detectado(s)"
      mark_fail
    else
      echo -e "${WARN} saída do script contém avisos: $(echo "${out}" | tail -3)"
      mark_warn
    fi
  else
    echo -e "${OK} cited=${cited}, defined=${defined}, 0 orphans"
  fi
}
check_citation_graph

# ---------------------------------------------------------------------------
# [6/10] Abstract metadata
# ---------------------------------------------------------------------------
check_abstract_metadata() {
  local label="[6/10] Abstract metadata"
  local notes=()
  local status=ok

  local abstract_file="${PUB_DIR}/paper-abstract.md"
  local golden_file="${REPO_ROOT}/eval/golden-queries.jsonl"
  local EXPECTED_SHA="9bff8ee7b9056eff6a1af22305cae762aa4b98e682578faffb4c22cdd0a2cd7d"

  if [[ ! -f "${abstract_file}" ]]; then
    printf "%s " "$(pad_label "${label}")"
    echo -e "${FAIL} paper-abstract.md não encontrado"
    mark_fail
    return
  fi

  # Contagem de palavras — ignorar linhas que começam com # (cabeçalhos MD)
  local words
  words=$(grep -v "^#" "${abstract_file}" | tr -s ' \t\n' '\n' | grep -c '[a-zA-Z]' || echo 0)

  if [[ "${words}" -lt 250 ]]; then
    notes+=("${words} palavras no abstract (min 250)")
    status=fail
  elif [[ "${words}" -gt 300 ]]; then
    notes+=("${words} palavras no abstract (max 300)")
    status=warn
    [[ "${status}" == "ok" ]] && status=warn
  fi

  # Contagem de chars sem markup LaTeX, cabeçalhos MD, blockquotes (metadata),
  # separadores (---) e linhas word-count finais (**Word count:**...).
  local chars
  chars=$(grep -vE "^(#|>|---|\*\*Word count:)" "${abstract_file}" \
    | sed 's/\\[a-zA-Z]*{[^}]*}//g' \
    | sed 's/\\[a-zA-Z]*//g' \
    | sed 's/[{}]//g' \
    | tr -d '\n' \
    | wc -c | tr -d ' ')

  if [[ "${chars}" -gt 1920 ]]; then
    notes+=("${chars} chars stripped (limite arXiv: 1920)")
    status=fail
  fi

  # SHA-256 do golden-queries.jsonl
  local sha_actual=""
  if command -v shasum >/dev/null 2>&1; then
    sha_actual=$(shasum -a 256 "${golden_file}" 2>/dev/null | awk '{print $1}')
  elif command -v sha256sum >/dev/null 2>&1; then
    sha_actual=$(sha256sum "${golden_file}" 2>/dev/null | awk '{print $1}')
  fi

  if [[ -z "${sha_actual}" ]]; then
    notes+=("sha256 não calculável")
    [[ "${status}" == "ok" ]] && status=warn
  elif [[ "${sha_actual}" != "${EXPECTED_SHA}" ]]; then
    notes+=("SHA mismatch: ${sha_actual:0:16}... (esperado: ${EXPECTED_SHA:0:16}...)")
    status=fail
  fi

  printf "%s " "$(pad_label "${label}")"
  if [[ "${status}" == "ok" ]]; then
    echo -e "${OK} ${words} palavras, ${chars} chars (limite 1920), SHA confere"
  elif [[ "${status}" == "warn" ]]; then
    echo -e "${WARN} ${words} palavras, ${chars} chars — $(IFS='; '; echo "${notes[*]}")"
    mark_warn
  else
    echo -e "${FAIL} $(IFS='; '; echo "${notes[*]}")"
    mark_fail
  fi
}
check_abstract_metadata

# ---------------------------------------------------------------------------
# [7/10] Forbidden artifacts
# ---------------------------------------------------------------------------
check_forbidden_artifacts() {
  local label="[7/10] Forbidden artifacts"
  local notes=()
  local status=ok

  # Arquivos temporários LaTeX em latex/ (exceto .sty)
  local aux_files
  aux_files=$(find "${LATEX_DIR}" -maxdepth 1 \
    -name "*.aux" -o -name "*.log" -o -name "*.bbl" -o -name "*.blg" \
    -o -name "*.out" -o -name "*.toc" 2>/dev/null | wc -l | tr -d ' ')

  if [[ "${aux_files}" -gt 0 ]]; then
    notes+=("${aux_files} arquivo(s) temporários LaTeX presentes")
    status=fail
  fi

  # TODO/NEEDS VALIDATION em drafts markdown
  local todo_hits
  todo_hits=$(grep -rli "\[NEEDS VALIDATION\|\[TODO" \
    "${PUB_DIR}"/*.md "${REPO_ROOT}/paper/"*.md 2>/dev/null \
    | grep -v "_archive" | wc -l | tr -d ' ')

  if [[ "${todo_hits}" -gt 0 ]]; then
    notes+=("${todo_hits} arquivo(s) com marcadores [TODO ou [NEEDS VALIDATION")
    status=warn
    [[ "${status}" == "ok" ]] && status=warn
  fi

  # Lorem ipsum em latex/
  if grep -rli "lorem ipsum" "${LATEX_DIR}/" 2>/dev/null | grep -qv "_archive"; then
    notes+=("texto placeholder 'lorem ipsum' encontrado em latex/")
    status=fail
  fi

  # TBD-arXiv em CITATION.cff só é bloqueio se status for post-submit
  if [[ -f "${REPO_ROOT}/CITATION.cff" ]]; then
    if grep -q "TBD-arXiv" "${REPO_ROOT}/CITATION.cff"; then
      local cff_status
      cff_status=$(grep "status:" "${REPO_ROOT}/CITATION.cff" 2>/dev/null | head -1 || echo "")
      if echo "${cff_status}" | grep -qi "post-submit"; then
        notes+=("TBD-arXiv em CITATION.cff com status post-submit")
        status=fail
      else
        notes+=("TBD-arXiv em CITATION.cff (OK — status não é post-submit)")
        [[ "${status}" == "ok" ]] && status=warn
      fi
    fi
  fi

  printf "%s " "$(pad_label "${label}")"
  if [[ "${status}" == "ok" ]]; then
    echo -e "${OK} sem aux/log/bbl, sem marcadores TODO/PENDING"
  elif [[ "${status}" == "warn" ]]; then
    echo -e "${WARN} $(IFS='; '; echo "${notes[*]}")"
    mark_warn
  else
    echo -e "${FAIL} $(IFS='; '; echo "${notes[*]}")"
    mark_fail
  fi
}
check_forbidden_artifacts

# ---------------------------------------------------------------------------
# [8/10] Tar packaging dry-run
# ---------------------------------------------------------------------------
check_tar_packaging() {
  local label="[8/10] Tar packaging dry-run"

  local pkg_script="${LATEX_DIR}/arxiv-package.sh"
  if [[ ! -f "${pkg_script}" ]]; then
    printf "%s " "$(pad_label "${label}")"
    echo -e "${WARN} arxiv-package.sh não encontrado em ${pkg_script}"
    mark_warn
    return
  fi

  # arxiv-package.sh sempre grava o tarball em SCRIPT_DIR (latex/), independente
  # do argumento ser absoluto. Passamos só o filename; depois localizamos em latex/.
  local tar_name="test-preflight-$$.tar.gz"
  local tar_expected="${LATEX_DIR}/${tar_name}"

  # Executar o script de empacotamento com saída de teste
  local pack_ok=true
  (cd "${LATEX_DIR}" && bash "${pkg_script}" "${tar_name}" 2>&1) || pack_ok=false

  printf "%s " "$(pad_label "${label}")"

  if [[ ! -f "${tar_expected}" ]]; then
    echo -e "${FAIL} arxiv-package.sh não gerou tarball (pack_ok=${pack_ok})"
    mark_fail
    return
  fi

  local tar_size_bytes
  tar_size_bytes=$(wc -c < "${tar_expected}" | tr -d ' ')
  local tar_size_kb=$(( tar_size_bytes / 1024 ))
  local max_tar_bytes=$(( 50 * 1024 * 1024 ))

  # Contar apenas arquivos (entradas sem "/" no final = não são diretórios)
  local file_count
  file_count=$(tar -tzf "${tar_expected}" 2>/dev/null | grep -v '/$' | wc -l | tr -d ' ')

  rm -f "${tar_expected}"

  local notes=()
  local status=ok

  if [[ "${tar_size_bytes}" -gt "${max_tar_bytes}" ]]; then
    notes+=("tarball ${tar_size_kb}KB > 50MB")
    status=fail
  fi

  if [[ "${file_count}" -ne 14 ]]; then
    notes+=("${file_count} arquivos no tarball (esperado: 14 — main.tex + 3 sec_*.tex + sty + bib + 8 figures)")
    # Aviso, não bloqueio, pois o número pode variar com sty adicionais
    [[ "${status}" == "ok" ]] && status=warn
  fi

  if [[ "${status}" == "ok" ]]; then
    echo -e "${OK} ${tar_size_kb}KB, ${file_count} arquivos no tarball"
  elif [[ "${status}" == "warn" ]]; then
    echo -e "${WARN} ${tar_size_kb}KB, ${file_count} arquivos — $(IFS='; '; echo "${notes[*]}")"
    mark_warn
  else
    echo -e "${FAIL} $(IFS='; '; echo "${notes[*]}")"
    mark_fail
  fi
}
check_tar_packaging

# ---------------------------------------------------------------------------
# [9/10] Hard secrets scan
# ---------------------------------------------------------------------------
check_secrets_scan() {
  local label="[9/10] Hard secrets scan"

  # Padrões regex que indicam segredos reais — suficientemente específicos para
  # evitar falsos positivos em texto acadêmico (ex: "sk-learn", "expected=[]").
  # Cada padrão requer caracteres alfanuméricos após o prefixo para ser um token real.
  local hits=()

  # AIzaSy... — chave Google/Gemini (39 chars típicos)
  local aizia_found
  aizia_found=$(git -C "${REPO_ROOT}" grep -rlE 'AIzaSy[A-Za-z0-9_-]{20,}' -- paper/ 'paper/publication/refs.bib' 2>/dev/null || true)
  [[ -n "${aizia_found}" ]] && hits+=("AIzaSy (Google key) em: $(echo "${aizia_found}" | head -2 | tr '\n' ' ')")

  # sk-... — chave OpenAI (min 20 alfanum após sk-)
  local sk_found
  sk_found=$(git -C "${REPO_ROOT}" grep -rlE 'sk-[A-Za-z0-9]{20,}' -- paper/ 'paper/publication/refs.bib' 2>/dev/null || true)
  [[ -n "${sk_found}" ]] && hits+=("sk- (OpenAI key) em: $(echo "${sk_found}" | head -2 | tr '\n' ' ')")

  # Slack tokens
  local slack_found
  slack_found=$(git -C "${REPO_ROOT}" grep -rlE 'xox[abp]-[A-Za-z0-9-]{10,}' -- paper/ 'paper/publication/refs.bib' 2>/dev/null || true)
  [[ -n "${slack_found}" ]] && hits+=("xox* (Slack token) em: $(echo "${slack_found}" | head -2 | tr '\n' ' ')")

  # GitHub tokens — prefixos oficiais
  local gh_found
  gh_found=$(git -C "${REPO_ROOT}" grep -rlE '(ghp_|ghs_|ghu_|gho_)[A-Za-z0-9]{20,}' -- paper/ 'paper/publication/refs.bib' 2>/dev/null || true)
  [[ -n "${gh_found}" ]] && hits+=("gh* (GitHub token) em: $(echo "${gh_found}" | head -2 | tr '\n' ' ')")

  # JWT completo (header.payload.signature)
  local jwt_found
  jwt_found=$(git -C "${REPO_ROOT}" grep -rlE 'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}' -- paper/ 'paper/publication/refs.bib' 2>/dev/null || true)
  [[ -n "${jwt_found}" ]] && hits+=("JWT token em: $(echo "${jwt_found}" | head -2 | tr '\n' ' ')")

  printf "%s " "$(pad_label "${label}")"
  if [[ ${#hits[@]} -eq 0 ]]; then
    echo -e "${OK} nenhuma API key/token detectada"
  else
    echo -e "${FAIL} SEGREDO DETECTADO:"
    for h in "${hits[@]}"; do
      echo "       ${RED}  → ${h}${RESET}"
    done
    mark_fail
  fi
}
check_secrets_scan

# ---------------------------------------------------------------------------
# [10/10] arXiv compatibility checks
# ---------------------------------------------------------------------------
check_arxiv_compat() {
  local label="[10/10] arXiv compatibility"
  local notes=()
  local status=ok

  # Título — extrair de main.tex
  local title_raw
  title_raw=$(grep -oE '\\title\{[^}]+\}' "${LATEX_DIR}/main.tex" 2>/dev/null \
    | head -1 \
    | sed 's/\\title{//;s/}$//' \
    | sed 's/\\\\//g' \
    | tr -s ' ' \
    | tr -d '\n')

  # Remover comandos LaTeX simples do título para contagem
  local title_plain
  title_plain=$(echo "${title_raw}" | sed 's/\\[a-zA-Z]*//g' | sed 's/[{}]//g')
  local title_len=${#title_plain}

  if [[ "${title_len}" -gt 250 ]]; then
    notes+=("título ${title_len} chars (limite 250)")
    status=fail
  fi

  # Comments field — lido de arxiv-submit-metadata.md §4
  local comments_file="${PUB_DIR}/arxiv-submit-metadata.md"
  local comments_len=0
  if [[ -f "${comments_file}" ]]; then
    # Captura bloco de backtick entre ## 4. COMMENTS e próximo ## heading
    local comments_block
    comments_block=$(awk '/^## 4\. COMMENTS/{found=1;next} found && /^## [0-9]/{exit} found' \
      "${comments_file}" \
      | sed -n '/^```$/,/^```$/p' | sed '1d;/^```$/d' | tr -d '\n')
    comments_len=${#comments_block}
    if [[ "${comments_len}" -gt 1024 ]]; then
      notes+=("comments ${comments_len} chars (limite 1024)")
      status=fail
    fi
  fi

  # Figuras — todas < 5MB
  local large_figs=()
  for i in 1 2 3 4; do
    local fig="${FIGS_DIR}/figure${i}.pdf"
    if [[ -f "${fig}" ]]; then
      local fig_size
      fig_size=$(wc -c < "${fig}" | tr -d ' ')
      local fig_kb=$(( fig_size / 1024 ))
      local max_fig=$(( 5 * 1024 * 1024 ))
      if [[ "${fig_size}" -gt "${max_fig}" ]]; then
        large_figs+=("figure${i}.pdf: ${fig_kb}KB")
        status=fail
      elif [[ "${fig_size}" -gt $(( 2 * 1024 * 1024 )) ]]; then
        notes+=("figure${i}.pdf: ${fig_kb}KB (>2MB, arXiv avisa)")
        [[ "${status}" == "ok" ]] && status=warn
      fi
    else
      notes+=("figure${i}.pdf ausente")
      status=fail
    fi
  done

  if [[ ${#large_figs[@]} -gt 0 ]]; then
    notes+=("figuras >5MB: $(IFS=', '; echo "${large_figs[*]}")")
  fi

  printf "%s " "$(pad_label "${label}")"
  if [[ "${status}" == "ok" ]]; then
    echo -e "${OK} título ${title_len} chars, comments ${comments_len} chars, todas figuras <2MB"
  elif [[ "${status}" == "warn" ]]; then
    echo -e "${WARN} título ${title_len} chars, comments ${comments_len} chars — $(IFS='; '; echo "${notes[*]}")"
    mark_warn
  else
    echo -e "${FAIL} $(IFS='; '; echo "${notes[*]}")"
    mark_fail
  fi
}
check_arxiv_compat

# ---------------------------------------------------------------------------
# Resumo final
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}-------------------------------------------${RESET}"

if [[ "${FAILURES}" -eq 0 && "${WARNINGS}" -eq 0 ]]; then
  echo -e "${GREEN}${BOLD}OVERALL: ✓ READY TO SUBMIT${RESET}"
elif [[ "${FAILURES}" -eq 0 ]]; then
  echo -e "${YELLOW}${BOLD}OVERALL: ⚠ PRONTO COM AVISOS — ${WARNINGS} warning(s), revisar antes de submeter${RESET}"
else
  echo -e "${RED}${BOLD}OVERALL: ✗ BLOQUEADO — veja falhas acima${RESET}"
  echo -e "Failed checks: ${FAILURES} | Warnings: ${WARNINGS}"
fi
echo ""

exit $(( FAILURES > 0 ? 1 : 0 ))
