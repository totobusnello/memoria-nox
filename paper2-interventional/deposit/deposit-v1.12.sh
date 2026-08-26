#!/usr/bin/env bash
# Depósito da v1.12 no Zenodo — DUAS FASES, e a segunda é a irreversível.
#
#   ./deposit-v1.12.sh prepare   → cria o draft, sobe arquivos, grava metadados. PARA.
#   ./deposit-v1.12.sh publish   → PUBLICA. Imutável a partir daqui.
#
# Token: export ZENODO_TOKEN=... (escopos deposit:write + deposit:actions)
#        criar em https://zenodo.org/account/settings/applications/tokens/new
#
# Caminho: API InvenioRDM (/api/records), NÃO a legada (/api/deposit/depositions).
# Razão: o PUT legado aceita forma legada e apaga campos em silêncio — foi assim
# que autor e licença desapareceram uma vez. O RDM exige a forma nova, e recusa
# a antiga em vez de a engolir.

set -euo pipefail

REC=21978476                       # v1.11 — id da ÚLTIMA versão, não o do conceito
API=https://zenodo.org/api
DIR="$(cd "$(dirname "$0")" && pwd)"
PKG="$(cd "$DIR/.." && pwd)"       # paper2-interventional/
STATE="$DIR/.draft-id"

: "${ZENODO_TOKEN:?falta ZENODO_TOKEN — ver cabeçalho}"
AUTH=(-H "Authorization: Bearer $ZENODO_TOKEN")

# Arquivos já no depósito que MUDARAM no repo desde 17/08 (conferido por md5).
# Precisam de delete + reupload; files-import traz a versão velha.
SUBSTITUIR=(
  PREREG-DRAFT.md          # + bloco do registro OSF (que se declara fora da cópia registrada)
  claims_check.py          # + cross_check do DOSES do reachable_share_fila.py
  run_panel.py             # fix d09b3cb: marcador do prompt restaurado, hash travado morde
)

# Novos nesta versão.
NOVOS=(
  AMENDMENT-v1.12.md
  DECISION-designacao-2026-08-25.md
  LAMBDA-RESULTS-2026-08-21.md
  LAMBDA-SEED-2026-08-21.md
  PILOT-WINDOW-2026-08-25.json
  pilot_window_stats.mjs
  p2-serving-WINDOW-2026-08-25.ndjson
  CUTS-MEASURED-2026-08-18.json
  cuts_measure.mjs
  AUDIT-SECTION2-SERVING-2026-08-18.md
  SHARES-PROVENANCE-2026-08-19.md
  reachable_share_fila.py
)

jqr() { python3 -c "import sys,json; print(json.load(sys.stdin)$1)"; }

prepare() {
  echo "▸ gate: claims_check.py precisa passar antes de qualquer coisa"
  ( cd "$PKG" && python3 claims_check.py ) || { echo "✗ claims_check FALHOU — abortado"; exit 1; }

  echo "▸ gate: a janela congelada precisa reproduzir o snapshot"
  ( cd "$PKG" && node pilot_window_stats.mjs p2-serving-WINDOW-2026-08-25.ndjson \
      --assert-json PILOT-WINDOW-2026-08-25.json >/dev/null ) \
    || { echo "✗ a janela não reproduz o snapshot — abortado"; exit 1; }

  echo "▸ 1/6 cria a nova versão a partir de $REC"
  DRAFT=$(curl -sf -X POST "${AUTH[@]}" "$API/records/$REC/versions" | jqr "['id']")
  echo "$DRAFT" > "$STATE"
  echo "     draft = $DRAFT"

  echo "▸ 2/6 importa os 42 arquivos da v1.11 (sem isto o draft nasce vazio)"
  curl -sf -X POST "${AUTH[@]}" \
    "$API/records/$DRAFT/draft/actions/files-import" >/dev/null
  echo "     importados: $(curl -sf "${AUTH[@]}" "$API/records/$DRAFT/draft/files" | jqr "['entries'].__len__()")"

  echo "▸ 3/6 remove os ${#SUBSTITUIR[@]} que serão substituídos"
  for f in "${SUBSTITUIR[@]}"; do
    curl -sf -X DELETE "${AUTH[@]}" "$API/records/$DRAFT/draft/files/$f" >/dev/null
    echo "     - $f"
  done

  echo "▸ 4/6 sobe ${#SUBSTITUIR[@]} substituídos + ${#NOVOS[@]} novos"
  for f in "${SUBSTITUIR[@]}" "${NOVOS[@]}"; do
    [ -f "$PKG/$f" ] || { echo "✗ não existe: $PKG/$f"; exit 1; }
    curl -sf -X POST "${AUTH[@]}" -H "Content-Type: application/json" \
      -d "[{\"key\": \"$f\"}]" "$API/records/$DRAFT/draft/files" >/dev/null
    curl -sf -X PUT "${AUTH[@]}" -H "Content-Type: application/octet-stream" \
      --data-binary "@$PKG/$f" "$API/records/$DRAFT/draft/files/$f/content" >/dev/null
    curl -sf -X POST "${AUTH[@]}" \
      "$API/records/$DRAFT/draft/files/$f/commit" >/dev/null
    echo "     + $f ($(wc -c <"$PKG/$f" | tr -d ' ') B)"
  done

  echo "▸ 5/6 grava os metadados (forma InvenioRDM)"
  curl -sf -X PUT "${AUTH[@]}" -H "Content-Type: application/json" \
    -d "@$DIR/zenodo-v1.12-metadata.json" "$API/records/$DRAFT/draft" >/dev/null

  echo "▸ 6/6 relê o draft e confere campo a campo o que o PUT legado apagava"
  curl -sf "${AUTH[@]}" "$API/records/$DRAFT/draft" > "$DIR/.draft-readback.json"
  python3 - "$DIR/.draft-readback.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); m = d["metadata"]
def chk(nome, obtido, esperado):
    ok = obtido == esperado
    print(f"     {'ok ' if ok else '✗✗ '} {nome:16} {obtido!r}")
    return ok
falhas = 0
falhas += not chk("version", m.get("version"), "1.12")
falhas += not chk("creators", [c["person_or_org"]["name"] for c in m.get("creators", [])],
                  ["Busnello, Luiz Antonio"])
falhas += not chk("affiliation", [a["name"] for c in m.get("creators", []) for a in c.get("affiliations", [])],
                  ["Independent Researcher"])
falhas += not chk("rights", [r.get("id") for r in m.get("rights", [])], ["cc-by-4.0"])
falhas += not chk("resource_type", m.get("resource_type", {}).get("id"), "publication-preprint")
falhas += not chk("languages", [l.get("id") for l in m.get("languages", [])], ["eng"])
falhas += not chk("subjects", len(m.get("subjects", [])), 10)
falhas += not chk("files", len(d.get("files", {}).get("entries", {})), 54)
if m.get("description", "").startswith("<p><strong>VERSION 1.12"):
    print("     ok  description começa no bloco da 1.12")
else:
    print("     ✗✗  description NÃO começa no bloco da 1.12"); falhas += 1
print()
if falhas:
    print(f"✗ {falhas} campo(s) divergem — NÃO publicar. Corrigir e repetir o passo 5.")
    sys.exit(1)
print("✓ draft íntegro.")
PY

  echo
  echo "══ PARADO ANTES DO IRREVERSÍVEL ══"
  echo "  Revisar no navegador: https://zenodo.org/uploads/$DRAFT"
  echo "  Publicar:            $0 publish"
  echo "  Descartar:           curl -X DELETE -H 'Authorization: Bearer \$ZENODO_TOKEN' $API/records/$DRAFT/draft"
}

publish() {
  [ -f "$STATE" ] || { echo "✗ sem draft: rode 'prepare' primeiro"; exit 1; }
  DRAFT=$(cat "$STATE")
  echo "▸ publicando o draft $DRAFT — IMUTÁVEL a partir daqui"
  OUT=$(curl -sf -X POST "${AUTH[@]}" "$API/records/$DRAFT/draft/actions/publish")
  echo "$OUT" > "$DIR/.published.json"
  python3 - "$DIR/.published.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print("  DOI de versão :", d.get("doi") or d.get("pids", {}).get("doi", {}).get("identifier"))
print("  version       :", d["metadata"].get("version"))
print("  arquivos      :", len(d.get("files", {}).get("entries", {})))
print("  URL           :", d["links"].get("self_html"))
PY
}

case "${1:-}" in
  prepare) prepare ;;
  publish) publish ;;
  *) echo "uso: $0 {prepare|publish}"; exit 2 ;;
esac
