#!/usr/bin/env bash
# Depósito da v1.12 no Zenodo — DUAS FASES, e a segunda é a irreversível.
#
#   ./deposit-v1.12.sh prepare   → cria o draft, sobe arquivos, grava metadados. PARA.
#   ./deposit-v1.12.sh metadata  → regrava e reconfere os metadados do draft existente.
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

# Grava os metadados e reconfere. Separado de `prepare` para poder repetir sem
# criar draft novo: `POST /versions` é idempotente enquanto o draft não publica,
# mas repetir prepare re-importaria e re-subiria 15 arquivos por nada.
metadata() {
  [ -f "$STATE" ] || { echo "✗ sem draft: rode 'prepare' primeiro"; exit 1; }
  DRAFT=$(cat "$STATE")

  echo "▸ grava os metadados no draft $DRAFT (envia forma InvenioRDM)"
  curl -sf -X PUT "${AUTH[@]}" -H "Content-Type: application/json" \
    -d "@$DIR/zenodo-v1.12-metadata.json" "$API/records/$DRAFT/draft" >/dev/null

  echo "▸ relê e confere campo a campo o que o PUT legado apagava"
  curl -sf "${AUTH[@]}" "$API/records/$DRAFT/draft" > "$DIR/.draft-readback.json"
  # ⚠️ O PUT aceita InvenioRDM, mas o GET do draft devolve a serialização
  # LEGADA (`creators: [{name, affiliation}]`, `license`, `keywords`, `language`,
  # `access_right`, `files` como lista). A primeira versão deste bloco leu
  # `person_or_org` no readback e estourou KeyError — a asserção tem de falar a
  # língua da RESPOSTA, não a do pedido. Ler a forma legada é o que prova que o
  # servidor guardou o que se quis, e não que o payload voltou ecoado.
  python3 - "$DIR/.draft-readback.json" "$DIR" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); m = d["metadata"]; DIR = sys.argv[2]
def chk(nome, obtido, esperado):
    ok = obtido == esperado
    print(f"     {'ok  ' if ok else '✗✗  '}{nome:16} {obtido!r}"
          + ("" if ok else f"   ESPERADO {esperado!r}"))
    return 0 if ok else 1
lic = m.get("license")
f  = chk("version",       m.get("version"), "1.12")
f += chk("creators",      [c.get("name") for c in m.get("creators", [])], ["Busnello, Luiz Antonio"])
f += chk("affiliation",   [c.get("affiliation") for c in m.get("creators", [])], ["Independent Researcher"])
f += chk("license",       lic.get("id") if isinstance(lic, dict) else lic, "cc-by-4.0")
f += chk("resource_type", (m.get("resource_type") or {}).get("subtype"), "preprint")
f += chk("language",      m.get("language"), "eng")
f += chk("access_right",  m.get("access_right"), "open")
f += chk("keywords",      len(m.get("keywords") or []), 10)
f += chk("publication",   m.get("publication_date"), "2026-08-26")
f += chk("files",         len(d.get("files", [])), 54)
# Igualdade de BYTES contra a fonte local. Exceção conhecida é asserção fraca:
# o `<hr>` que o sanitizador do Zenodo descartava foi removido da fonte para
# que esta comparação possa ser exata.
local = (open(f"{DIR}/zenodo-v1.12-description-new-block.html", encoding="utf-8").read()
         + open(f"{DIR}/_v111-description.html", encoding="utf-8").read())
f += chk("description",   len(m.get("description", "")), len(local))
if m.get("description") != local:
    import difflib
    print("     ✗✗  description difere byte a byte:")
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
            None, local, m.get("description", ""), autojunk=False).get_opcodes():
        if tag != "equal":
            print(f"         {tag} local[{i1}:{i2}]={local[i1:i2]!r} -> remoto={m['description'][j1:j2]!r}")
    f += 1
else:
    print("     ok  description      idêntica byte a byte")
print()
if f:
    print(f"✗ {f} divergência(s) — NÃO publicar. Corrigir e repetir: $0 metadata")
    sys.exit(1)
print("✓ draft íntegro — 0 divergências.")
PY
}

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

  metadata
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
  prepare)  prepare ;;
  metadata) metadata ;;   # regrava + reconfere, sem recriar o draft
  publish)  publish ;;
  *) echo "uso: $0 {prepare|metadata|publish}"; exit 2 ;;
esac
