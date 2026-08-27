#!/usr/bin/env bash
# Depósito da v1.13 no Zenodo — QUATRO fases, e só a última é irreversível.
#
#   ./deposit-v1.13.sh prepare   → cria o draft, importa, sobe 45, grava metadados. PARA.
#   ./deposit-v1.13.sh sync      → reenvia arquivos alterados + regrava metadados. PARA.
#   ./deposit-v1.13.sh check     → readback DUPLO + md5 dos 99. NÃO ESCREVE NADA.
#   ./deposit-v1.13.sh publish   → PUBLICA. Imutável a partir daqui.
#
# Token: export ZENODO_TOKEN=... (escopos deposit:write + deposit:actions)
#
# Caminho: API InvenioRDM (/api/records), NÃO a legada (/api/deposit/depositions).
# Razão: o PUT legado aceita forma legada e apaga campos em silêncio com HTTP 200 —
# foi assim que autor e licença desapareceram uma vez. O RDM exige a forma nova.
#
# Herda do `deposit-v1.12.sh` tudo o que já custou caro: readback duplo (legado +
# InvenioRDM, porque `publisher` NÃO existe na forma legada e bloqueia o publish),
# `POST /files` uma chave por vez (em lote com 2 dá 400), e publish SEM `-sf`.

set -euo pipefail

REC=22110203                       # v1.12 — id da ÚLTIMA versão, não o do conceito
VER=1.13
NFILES=99                          # 60 herdados + 39 novos, 0 removidos
API=https://zenodo.org/api
DIR="$(cd "$(dirname "$0")" && pwd)"
PKG="$(cd "$DIR/.." && pwd)"       # paper2-interventional/
STATE="$DIR/.draft-id-v113"

# Token: env var tem precedência; senão, o store por-arquivo do Mac, que é o padrão
# já instalado (~/.config/secrets/<NOME>, 10 segredos lá). Guardar ali tira o token da
# conversa e do histórico de shell, e sobrevive à sessão — em 26/08 ele foi passado à
# mão e não ficou em lugar nenhum, o que obrigou a refazer o passo hoje.
SECRET_FILE="$HOME/.config/secrets/ZENODO_TOKEN"
if [ -z "${ZENODO_TOKEN:-}" ] && [ -r "$SECRET_FILE" ]; then
  ZENODO_TOKEN="$(tr -d '\r\n' < "$SECRET_FILE")"
fi
: "${ZENODO_TOKEN:?sem token — grave em ~/.config/secrets/ZENODO_TOKEN (chmod 600) ou exporte ZENODO_TOKEN}"
AUTH=(-H "Authorization: Bearer $ZENODO_TOKEN")

# Já no depósito e MUDARAM no repo desde 26/08 (conferido por md5 contra
# .published.json). Precisam de delete + reupload: `files-import` traz a versão velha.
SUBSTITUIR=(
  "DEPOSIT-README.md"                 # → README.md; ganhou o mapa de chaves planas
  "claims_check.py"
  "SERVING-CODE-MANIFEST.md"
  "serving-brief.ts"
  "serving-brief-outcome.ts"
  "DECISION-designacao-2026-08-25.md"
)

# Novos nesta versão. Cada um está aqui porque a emenda o CITA como sustentação —
# ver deposit/PLAN-v1.13.md para o porquê de cada bloco.
NOVOS=(
  # a emenda e a cadeia que a sustenta
  "AMENDMENT-DRAFT-band-collapse-2026-08-26.md"   # → AMENDMENT-v1.13.md
  "REMEDIATION-2026-08-27.md"
  "REMEDIATION-2026-08-27.json"
  "MEASUREMENT-delta-cut-2026-08-26.md"
  "DELTA-CUT-MEASUREMENT-2026-08-26.json"
  "DESIGNATION-SEED-2026-08-26.md"
  "DESIGNATION-2026-08-26.json"
  "p2-verdict-frame-2026-08-26.csv"
  "designation_verify.py"
  "REVIEWS-PREREG.md"
  # blobs e o dado da janela
  "serving-p2-outcome-test.ts"
  "p2-serving-CLOSED-WINDOW-2026-08-26T2028-2026-08-27T0900.ndjson"
  # measurement/ (20) → prefixo measurement-
  "measurement/README.md"
  "measurement/asof-sonda-vs-tempo.py"
  "measurement/autoextincao.py"
  "measurement/baseline.py"
  "measurement/controle-positivo.mjs"
  "measurement/descontamina.py"
  "measurement/dose-response.mjs"
  "measurement/dose2.mjs"
  "measurement/gap-defs.mjs"
  "measurement/mede-delta.mjs"
  "measurement/ordem.mjs"
  "measurement/p2-designation-crosscheck.mjs"
  "measurement/pos-regra.py"
  "measurement/rebase.py"
  "measurement/remedia-descontamina.py"
  "measurement/remedia-serie.py"
  "measurement/serie.py"
  "measurement/tendencia.py"
  "measurement/verifica.py"
  "measurement/verifica2.py"
  # receipts/ (7) → prefixo receipts-
  "receipts/README.md"
  "receipts/adversary-output-codex-2026-08-27T103048.txt"
  "receipts/adversary-receipt-codex-2026-08-26T231314-92025.txt"
  "receipts/adversary-receipt-codex-2026-08-27T103048-REAL.txt"
  "receipts/adversary-receipt-deepseek-2026-08-27T095240-78994.txt"
  "receipts/adversary-receipt-glm-2026-08-26T231155-90950.txt"
  "receipts/adversary-receipt-kimi-2026-08-27T095238-78960.txt"
)

# Chaves são PLANAS no depósito — convenção que o SERVING-CODE-MANIFEST.md já usa
# (`src/api/brief.ts` → `serving-brief.ts`). Sem este mapeamento o DELETE erra a chave
# e o upload criaria um arquivo com nome errado, silenciosamente.
chave() {
  case "$1" in
    DEPOSIT-README.md)                            echo "README.md" ;;
    AMENDMENT-DRAFT-band-collapse-2026-08-26.md)  echo "AMENDMENT-v$VER.md" ;;
    measurement/*)                                echo "measurement-${1#measurement/}" ;;
    receipts/*)                                   echo "receipts-${1#receipts/}" ;;
    *)                                            echo "$1" ;;
  esac
}

jqr() { python3 -c "import sys,json; print(json.load(sys.stdin)$1)"; }

# ── readback duplo + conferência. Não escreve nada; pode rodar quantas vezes quiser.
verifica() {
  [ -f "$STATE" ] || { echo "✗ sem draft: rode 'prepare' primeiro"; exit 1; }
  DRAFT=$(cat "$STATE")
  echo "▸ readback LEGADO (pega apagamento de creators/rights/subjects)"
  curl -sf "${AUTH[@]}" "$API/records/$DRAFT/draft" > "$DIR/.readback-v113.json"
  echo "▸ readback INVENIORDM (pega publisher, ausente da forma legada)"
  curl -sf -H "Accept: application/vnd.inveniordm.v1+json" "${AUTH[@]}" \
    "$API/records/$DRAFT/draft" > "$DIR/.readback-v113-rdm.json"

  python3 - "$DIR" "$PKG" "$VER" "$NFILES" <<'PY'
import json, sys, hashlib, pathlib
DIR, PKG, VER, NF = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
leg = json.load(open(f"{DIR}/.readback-v113.json")); m = leg["metadata"]
rdm = json.load(open(f"{DIR}/.readback-v113-rdm.json")).get("metadata", {})
f = 0
def chk(nome, obtido, esperado):
    global f
    ok = obtido == esperado
    print(f"     {'ok  ' if ok else '✗✗  '}{nome:18} {obtido!r}" + ("" if ok else f"   ESPERADO {esperado!r}"))
    f += 0 if ok else 1

# --- forma LEGADA: os campos que o PUT já apagou uma vez, com 200 ---
lic = m.get("license")
chk("version",        m.get("version"), VER)
chk("creators",       [c.get("name") for c in m.get("creators", [])], ["Busnello, Luiz Antonio"])
chk("affiliation",    [c.get("affiliation") for c in m.get("creators", [])], ["Independent Researcher"])
chk("license",        lic.get("id") if isinstance(lic, dict) else lic, "cc-by-4.0")
chk("resource_type",  (m.get("resource_type") or {}).get("subtype"), "preprint")
chk("language",       m.get("language"), "eng")
chk("access_right",   m.get("access_right"), "open")
chk("keywords(n)",    len(m.get("keywords") or []), 10)
chk("publication",    m.get("publication_date"), "2026-08-27")
chk("files(n)",       len(leg.get("files", [])), NF)
rel = m.get("related_identifiers") or []
def par(r):
    rt = r.get("relation") or (r.get("relation_type") or {}).get("id") or ""
    return (rt.lower().replace("_", ""), r.get("identifier"))
pares = {par(r) for r in rel}
chk("related(n)",     len(rel), 2)
chk("rel OSF",        ("issupplementto", "https://osf.io/yf7d2/") in pares, True)
chk("rel repo(tag)",  ("issupplementedby",
    f"https://github.com/totobusnello/memoria-nox/tree/paper2-v{VER}/paper2-interventional") in pares, True)

# --- forma INVENIORDM: os campos que SÓ existem aqui ---
chk("publisher",      rdm.get("publisher"), "Zenodo")
chk("rdm version",    rdm.get("version"), VER)
# A contagem de chaves é o detector de apagamento em massa: a v1.12 publicada tem 11.
chk("rdm metadata(n)", len(rdm), 11)

# --- description byte a byte contra a fonte local ---
local = (open(f"{DIR}/zenodo-v{VER}-description-new-block.html", encoding="utf-8").read()
         + open(f"{DIR}/_v112-description.html", encoding="utf-8").read())
if m.get("description") == local:
    print("     ok  description        idêntica byte a byte")
else:
    import difflib
    print("     ✗✗  description difere byte a byte:")
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
            None, local, m.get("description", ""), autojunk=False).get_opcodes():
        if tag != "equal":
            print(f"         {tag} local[{i1}:{i2}]={local[i1:i2]!r} -> remoto={m['description'][j1:j2]!r}")
    f += 1

# --- md5 de TODO arquivo contra o local, e ausências nas DUAS direções ---
# ⚠️ Toda função de diff precisa das duas direções: divergente E ausente. Na v1.12 a
# versão que só olhava o que já estava no draft reportava "sem divergências" enquanto
# faltava arquivo.
mapa = {}
for l in open(f"{DIR}/keymap-v113.tsv", encoding="utf-8"):
    k, v = l.rstrip("\n").split("\t"); mapa[k] = v
draft = {e["key"]: e for e in leg.get("files", [])}
faltando = [k for k in mapa if k not in draft]
divergente = []
for k, local_rel in mapa.items():
    if k not in draft: continue
    p = pathlib.Path(PKG) / local_rel
    if not p.exists(): divergente.append((k, "fonte local ausente")); continue
    ck = (draft[k].get("checksum") or "").replace("md5:", "")
    got = hashlib.md5(p.read_bytes()).hexdigest()
    if ck and got != ck: divergente.append((k, f"md5 {got[:8]} != {ck[:8]}"))
extra = [k for k in draft if k not in mapa]
print()
print(f"     arquivos no draft: {len(draft)} (esperado {NF})")
for k in faltando:   print(f"     ✗✗  AUSENTE no draft: {k}");            f += 1
for k, r in divergente: print(f"     ✗✗  DIVERGENTE: {k} — {r}");        f += 1
if extra: print(f"     ·   {len(extra)} no draft e fora do mapa (herdados da v1.12, esperado)")
print()
if f:
    print(f"✗ {f} divergência(s) — NÃO publicar."); sys.exit(1)
print("✓ draft íntegro — 0 divergências nas DUAS serializações.")
PY
}

# Mapa chave-no-depósito → caminho local. Materializado em arquivo para o Python
# conferir os 99 sem reimplementar `chave()`.
keymap() {
  : > "$DIR/keymap-v113.tsv"
  for f in "${SUBSTITUIR[@]}" "${NOVOS[@]}"; do printf '%s\t%s\n' "$(chave "$f")" "$f" >> "$DIR/keymap-v113.tsv"; done
}

metadata() {
  [ -f "$STATE" ] || { echo "✗ sem draft: rode 'prepare' primeiro"; exit 1; }
  DRAFT=$(cat "$STATE")
  echo "▸ grava metadados no draft $DRAFT (forma InvenioRDM, 11 campos)"
  curl -sf -X PUT "${AUTH[@]}" -H "Content-Type: application/json" \
    -d "@$DIR/zenodo-v$VER-metadata.json" "$API/records/$DRAFT/draft" >/dev/null
  keymap; verifica
}

prepare() {
  echo "▸ gate 1: claims_check.py tem de passar antes de qualquer coisa"
  ( cd "$PKG" && python3 claims_check.py ) || { echo "✗ claims_check FALHOU — abortado"; exit 1; }

  echo "▸ gate 2: a janela FECHADA tem de reproduzir 11/350 do próprio arquivo"
  ( cd "$PKG" && python3 - <<'PY'
import json
rows=[json.loads(l) for l in open("p2-serving-CLOSED-WINDOW-2026-08-26T2028-2026-08-27T0900.ndjson",encoding="utf-8") if l.strip()]
limpo=[r for r in rows if r.get("agent")]
k=sum(1 for r in limpo if r.get("churn",0)>0)
assert (k,len(limpo))==(11,350), f"esperado 11/350, obtido {k}/{len(limpo)}"
assert all(len(r.get("designated_ids",[]))==19 for r in limpo), "designated_ids != 19 em alguma decisão"
PY
  ) || { echo "✗ a janela não reproduz — abortado"; exit 1; }

  echo "▸ gate 3: nenhum arquivo a subir pode conter IP/hostname/token"
  for f in "${SUBSTITUIR[@]}" "${NOVOS[@]}"; do
    # ⚠️ O range CGNAT INTEIRO (100.64/10), nao um /24 especifico. A versao anterior
    # deste detector codificava o /24 da tailnet — num repo PUBLICO, e a caminho de um
    # deposito IMUTAVEL, isso reduzia o endereco a 10 candidatos. O detector generico e
    # estritamente melhor: pega qualquer tailnet, e nao divulga a nossa.
    if LC_ALL=C grep -qEi '(ghp_|sk-[A-Za-z0-9]{20}|AIza[0-9A-Za-z_-]{35}|BEGIN [A-Z ]*PRIVATE KEY|100\.(6[4-9]|[7-9][0-9]|1[0-1][0-9]|12[0-7])\.[0-9]+\.[0-9]+|srv1[0-9]{6}|\.ts\.net)' "$PKG/$f"; then
      echo "✗ segredo/endereço em $f — abortado"; exit 1
    fi
  done
  echo "     varredura limpa em $(( ${#SUBSTITUIR[@]} + ${#NOVOS[@]} )) arquivos"

  echo "▸ 1/5 cria a nova versão a partir de $REC (v1.12)"
  DRAFT=$(curl -sf -X POST "${AUTH[@]}" "$API/records/$REC/versions" | jqr "['id']")
  echo "$DRAFT" > "$STATE"; echo "     draft = $DRAFT"

  echo "▸ 2/5 importa os 60 arquivos da v1.12 (sem isto o draft nasce vazio)"
  curl -sf -X POST "${AUTH[@]}" "$API/records/$DRAFT/draft/actions/files-import" >/dev/null
  echo "     importados: $(curl -sf "${AUTH[@]}" "$API/records/$DRAFT/draft/files" | jqr "['entries'].__len__()")"

  echo "▸ 3/5 remove os ${#SUBSTITUIR[@]} substituídos"
  for f in "${SUBSTITUIR[@]}"; do
    K=$(chave "$f")
    curl -sf -X DELETE "${AUTH[@]}" "$API/records/$DRAFT/draft/files/$K" >/dev/null
    echo "     - $K"
  done

  echo "▸ 4/5 sobe ${#SUBSTITUIR[@]} substituídos + ${#NOVOS[@]} novos (uma chave por POST)"
  for f in "${SUBSTITUIR[@]}" "${NOVOS[@]}"; do
    [ -f "$PKG/$f" ] || { echo "✗ não existe: $PKG/$f"; exit 1; }
    K=$(chave "$f")
    # ⚠️ POST em LOTE com 2 chaves devolve 400; uma por vez devolve 201.
    curl -sf -X POST "${AUTH[@]}" -H "Content-Type: application/json" \
      -d "[{\"key\": \"$K\"}]" "$API/records/$DRAFT/draft/files" >/dev/null
    curl -sf -X PUT "${AUTH[@]}" -H "Content-Type: application/octet-stream" \
      --data-binary "@$PKG/$f" "$API/records/$DRAFT/draft/files/$K/content" >/dev/null
    curl -sf -X POST "${AUTH[@]}" "$API/records/$DRAFT/draft/files/$K/commit" >/dev/null
    echo "     + $K ($(wc -c <"$PKG/$f" | tr -d ' ') B)"
  done

  echo "▸ 5/5 metadados + readback duplo"
  metadata
  echo
  echo "══ PARADO ANTES DO IRREVERSÍVEL ══"
  echo "  Revisar no navegador: https://zenodo.org/uploads/$DRAFT"
  echo "  Reconferir:           $0 check"
  echo "  Publicar:             $0 publish"
  echo "  Descartar:            curl -X DELETE -H 'Authorization: Bearer \$ZENODO_TOKEN' $API/records/$DRAFT/draft"
}

# Reenvia todo arquivo cujo md5 local difere do que está no draft, e sobe o que falta.
sync_files() {
  [ -f "$STATE" ] || { echo "✗ sem draft"; exit 1; }
  DRAFT=$(cat "$STATE"); keymap
  curl -sf "${AUTH[@]}" "$API/records/$DRAFT/draft/files" > "$DIR/.draft-files-v113.json"
  PLAN=$(python3 - "$DIR" "$PKG" <<'PY'
import json, sys, hashlib, pathlib
DIR, PKG = sys.argv[1], sys.argv[2]
draft = {e["key"]: e for e in json.load(open(f"{DIR}/.draft-files-v113.json"))["entries"]}
for l in open(f"{DIR}/keymap-v113.tsv", encoding="utf-8"):
    k, rel = l.rstrip("\n").split("\t")
    p = pathlib.Path(PKG) / rel
    if not p.exists(): continue
    if k not in draft: print("A", k, rel); continue
    ck = (draft[k].get("checksum") or "").replace("md5:", "")
    if ck and hashlib.md5(p.read_bytes()).hexdigest() != ck: print("R", k, rel)
PY
)
  if [ -z "$PLAN" ]; then echo "▸ draft espelha o local — nada a fazer"; else
    echo "$PLAN" | while read -r acao K rel; do
      [ "$acao" = "R" ] && curl -sf -X DELETE "${AUTH[@]}" "$API/records/$DRAFT/draft/files/$K" >/dev/null
      curl -sf -X POST "${AUTH[@]}" -H "Content-Type: application/json" -d "[{\"key\": \"$K\"}]" \
        "$API/records/$DRAFT/draft/files" >/dev/null
      curl -sf -X PUT "${AUTH[@]}" -H "Content-Type: application/octet-stream" \
        --data-binary "@$PKG/$rel" "$API/records/$DRAFT/draft/files/$K/content" >/dev/null
      curl -sf -X POST "${AUTH[@]}" "$API/records/$DRAFT/draft/files/$K/commit" >/dev/null
      [ "$acao" = "R" ] && echo "     ↻ $K" || echo "     + $K"
    done
  fi
}

publish() {
  [ -f "$STATE" ] || { echo "✗ sem draft: rode 'prepare' primeiro"; exit 1; }
  DRAFT=$(cat "$STATE")

  echo "▸ reconferindo antes do irreversível (o publish não é o lugar de descobrir)"
  keymap; verifica || { echo "✗ readback com divergência — publish abortado"; exit 1; }

  echo "▸ publicando o draft $DRAFT — IMUTÁVEL a partir daqui"
  # ⚠️ NUNCA `-sf` aqui. `-f` descarta o corpo do erro e, com `set -e` dentro de
  # `$(...)`, a saída fica indistinguível de sucesso: na v1.12 o script imprimiu
  # "publicando", voltou ao prompt, e só um GET público revelou o 404.
  BODY=$(mktemp)
  CODE=$(curl -s -o "$BODY" -w '%{http_code}' \
    -X POST "${AUTH[@]}" "$API/records/$DRAFT/draft/actions/publish" || echo 000)

  if [ "${CODE:0:1}" != "2" ]; then
    echo "✗ NÃO publicado — HTTP $CODE. O draft segue intacto."
    python3 - "$BODY" <<'PY' || cat "$BODY"
import json, sys
d = json.load(open(sys.argv[1]))
print("   ", d.get("message") or d.get("status") or "(sem mensagem)")
for e in d.get("errors", []):
    print(f"    · campo {e.get('field')!r}: {e.get('messages') or e.get('message')}")
PY
    rm -f "$BODY"; return 1
  fi

  mv "$BODY" "$DIR/.published-v113.json"
  python3 - "$DIR/.published-v113.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print("  DOI de versão :", d.get("doi") or (d.get("pids") or {}).get("doi", {}).get("identifier"))
print("  version       :", (d.get("metadata") or {}).get("version"))
fs = d.get("files"); print("  arquivos      :", len(fs.get("entries", {})) if isinstance(fs, dict) else len(fs or []))
print("  URL           :", (d.get("links") or {}).get("self_html"))
PY
  # ⚠️ Estado por consulta INDEPENDENTE, nunca pela ausência de erro. Na v1.12 foi um
  # GET público sem token que revelou, em 2 s, o que a saída do script não dizia.
  echo "▸ confirmação por GET público, SEM token:"
  DOI=$(python3 -c "import json;d=json.load(open('$DIR/.published-v113.json'));print(d.get('doi') or d['pids']['doi']['identifier'])")
  curl -s "$API/records/$DRAFT" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print('     is_published:', d.get('is_published'), '| version:', (d.get('metadata') or {}).get('version'))
" || echo "     ✗ GET público falhou — CONFERIR À MÃO antes de anunciar"
  echo "     DOI: $DOI"
}

case "${1:-}" in
  prepare)  prepare ;;
  sync)     sync_files; metadata ;;
  check)    keymap; verifica ;;
  metadata) metadata ;;
  publish)  publish ;;
  *) echo "uso: $0 {prepare|sync|check|metadata|publish}"; exit 2 ;;
esac
