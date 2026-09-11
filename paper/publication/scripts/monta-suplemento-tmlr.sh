#!/usr/bin/env bash
# =============================================================================
# Monta o supplementary material ANONIMO do TMLR (ZIP).
#
# O que vai, e por que só isto:
#
#   supplement/  as seções que o manuscrito cita como §S* — é o buraco que o
#                double blind cria, porque o ponteiro `paper/publication/...`
#                é inalcançável para o revisor;
#   results/     os agregados das duas corridas do §6 — os números por trás
#                das tabelas, em JSON e na tabela legível;
#   guards/      o aparato de guardas do §6.9, como evidência de MÉTODO.
#
# O que NÃO vai, e por que:
#
#   O source tree (`staged/`, 605 arquivos) e o harness (`eval/q4-comparison/`)
#   carregam 497 sítios de identidade medidos em 2026-09-11 — endereço de host
#   em adapters, apelido do operador em READMEs, caminho local em docs de
#   deploy. Anonimizá-los significa reescrever endereços DENTRO de código
#   oferecido como reproduzível, o que troca um risco (vazar identidade) por
#   outro (publicar código que não roda). Fica para o camera-ready, com o
#   repositório identificado.
#
#   `refs.bib` e o caso de mutação que o usa: a entrada de auto-citação carrega
#   nome do autor, usuário do GitHub e o DOI do depósito. Por isso a suíte vai
#   como LEITURA de método, não executável — e o README diz isso, em vez de a
#   embrulhar num bib adulterado que divergiria em silêncio.
#
# GATE: nenhum arquivo entra no ZIP sem passar o `anonimiza-para-tmlr.py
# --check`, que tem controle positivo (8/8 na sentinela com vazamento) e
# controle negativo (0 na sentinela limpa). Sem as duas pernas, "0 vazamentos"
# não se distingue de "não consegui procurar".
#
# Exit: 0 ok · 2 peça ausente · 3 falha ao montar · 4 vazamento de identidade
# =============================================================================
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ANONIMIZA="${RAIZ}/paper/publication/scripts/anonimiza-para-tmlr.py"
DESTINO="${RAIZ}/paper/build/tmlr"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

log() { echo "[suplemento] $*"; }
err() { echo "[suplemento:erro] $*" >&2; }

command -v zip >/dev/null || { err "zip ausente"; exit 2; }
[[ -f "$ANONIMIZA" ]] || { err "auditor ausente: $ANONIMIZA"; exit 2; }

# (destino-no-zip, origem-no-repo)
PECAS=(
  "supplement/S-wave2-and-cross-backbone.md|paper/publication/supplement-wave2-and-cross-backbone.md"
  "supplement/S-operational-appendices.md|paper/publication/supplement-operational-appendices.md"
  "results/q4-2026-06-15/_aggregate.json|eval/q4-comparison/output/_aggregate.json"
  "results/q4-2026-06-15/_aggregate.md|eval/q4-comparison/output/_aggregate.md"
  "results/q4-2026-09-10/_aggregate.json|eval/q4-comparison/output-2026-09-10/_aggregate.json"
  "results/q4-2026-09-10/_aggregate.md|eval/q4-comparison/output-2026-09-10/_aggregate.md"
  "guards/claims_check.py|paper/claims_check.py"
  "guards/bibitem-census.json|paper/bibitem-census.json"
)

log "1/3 juntando ${#PECAS[@]} peças ..."
for par in "${PECAS[@]}"; do
  dst="${par%%|*}"; src="${par##*|}"
  [[ -f "${RAIZ}/${src}" ]] || { err "peça ausente: ${src}"; exit 2; }
  mkdir -p "${STAGE}/$(dirname "$dst")"
  cp "${RAIZ}/${src}" "${STAGE}/${dst}"
done

cat > "${STAGE}/README.md" <<'MD'
# Supplementary material (anonymized)

## `supplement/`

The sections the manuscript cites as `§S*`. They hold the per-backbone and
per-knob matrices, the Wave 2 closure detail, and the operational appendices
A–G. None of them is load-bearing for a claim in the main text: each is the
*detail behind* a result whose headline and caveat are already stated there.

## `results/`

Aggregate artifacts for the two §6 runs — the 2026-06-15 canonical run and the
2026-09-10 run that added the two competitors measured later. Each directory
holds the machine-readable aggregate and the rendered table. These are the
numbers behind §6.3, §6.3.2, §6.3.3, §6.3.4 and §6.4.

The per-query outputs are not included: §6.3.2 already states that they are not
distributed and names the three scripts the run is reproducible from.

## `guards/`

The claim-guard apparatus described in §6.9, as evidence of **method**.
`claims_check.py` carries 21 guards; `bibitem-census.json` is the reference
census the density and count guards read.

**This copy is for reading, not for running.** The suite's fixtures are the
manuscript and its bibliography, and the bibliography's self-citation entry
carries the authors' names, a personal repository handle and the deposit DOI.
Shipping a doctored bibliography so that the suite would execute would mean
shipping a fixture that diverges from the real one — which is the class of
defect the suite exists to catch. The mutation suite (48 cases, each asserted to
fail with its own marker, plus a silent negative control) is reported in §6.9
and will be released, executable, with the camera-ready.

## What is not here, and why

The source tree and the evaluation harness are withheld for double-blind
review. A measurement on 2026-09-11 found 497 identity sites across them: host
addresses inside adapters, an operator nickname across READMEs, local paths in
deployment notes. Rewriting addresses inside code that is offered as
reproducible trades one risk for another, so the identified repository is cited
in the camera-ready version instead.
MD

log "2/3 GATE de anonimato sobre cada arquivo ..."
# `mapfile` e' bash 4+; o macOS traz 3.2 e falharia com "command not found",
# que e' exit 127 e nao um dos codigos declarados no cabecalho.
TEXTOS=()
while IFS= read -r f; do TEXTOS+=("$f"); done < <(
  find "$STAGE" -type f \( -name '*.md' -o -name '*.py' -o -name '*.json' \) | sort)
if [[ ${#TEXTOS[@]} -eq 0 ]]; then
  err "nenhum arquivo de texto para auditar — o gate leria 0 vazamentos por não ter lido nada"
  exit 4
fi
if ! python3 "$ANONIMIZA" --check "${TEXTOS[@]}"; then
  err "VAZAMENTO DE IDENTIDADE no supplementary material — não submeter"
  exit 4
fi
log "      ${#TEXTOS[@]} arquivos auditados, 0 vazamentos"

log "3/3 empacotando ..."
mkdir -p "$DESTINO"
ZIP="${DESTINO}/tmlr-supplementary.zip"
rm -f "$ZIP"
( cd "$STAGE" && zip -q -r -X "$ZIP" . ) || { err "zip falhou"; exit 3; }
[[ -s "$ZIP" ]] || { err "ZIP vazio"; exit 3; }

N=$(unzip -Z1 "$ZIP" | grep -cv '/$' || true)
KB=$(( $(wc -c < "$ZIP") / 1024 ))
log "ZIP: ${ZIP}"
log "  ${N} arquivos · ${KB} KB (limite do TMLR: 100 MB)"
