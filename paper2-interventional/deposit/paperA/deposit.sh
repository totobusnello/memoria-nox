#!/usr/bin/env bash
# deposit.sh — cria o rascunho do Paper A no Zenodo, sobe o pacote e roda os gates.
#
# DOI NOVO, registro separado: `POST /api/records`, e não `/records/<id>/versions`.
# O 10.5281/zenodo.22110203 é o pré-registro de um estudo que não começou; este é um
# estudo observacional concluído. Como nova versão, o Paper A herdaria o título
# "A Pre-Registered Randomised Crossover".
#
# Caminho: API InvenioRDM (/api/records), NUNCA a legada (/api/deposit/depositions).
# Razão, que já custou caro: o PUT legado aceita forma legada e APAGA campos em
# silêncio devolvendo HTTP 200 — foi assim que autor e licença desapareceram uma vez.
#
# Herdado do deposit-v1.12.sh, tudo já pago em erro:
#   · readback DUPLO (legado + InvenioRDM) — `publisher` não existe na forma legada;
#   · `POST /files` uma chave por vez — em lote com 2 dá 400;
#   · `publish` SEM `-sf`, para que um erro apareça em vez de virar silêncio.
#
# ⚠️ Este script NÃO publica. Ele para com o rascunho pronto e conferido. Publicar é
# um passo separado, manual, e irreversível: um DOI publicado não se apaga.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"
API=https://zenodo.org/api

SECRET_FILE="$HOME/.config/secrets/ZENODO_TOKEN"
if [ -z "${ZENODO_TOKEN:-}" ] && [ -r "$SECRET_FILE" ]; then
  ZENODO_TOKEN="$(tr -d '\r\n' < "$SECRET_FILE")"
fi
: "${ZENODO_TOKEN:?sem token — grave em ~/.config/secrets/ZENODO_TOKEN (chmod 600)}"
AUTH=(-H "Authorization: Bearer $ZENODO_TOKEN")

jqr() { python3 -c "import json,sys;d=json.load(sys.stdin);print(eval('d'+sys.argv[1]))" "$1"; }
say() { printf '\n\033[1m%s\033[0m\n' "$*"; }

MANIFEST="$DIR/MANIFEST.json"
[ -r "$MANIFEST" ] || { echo "manifesto ausente — rode a montagem do pacote"; exit 1; }

# --- 0. gate local: o pacote no disco é o que o manifesto diz? ------------------
say "0. conferindo o pacote contra o manifesto"
python3 - "$MANIFEST" "$ROOT" <<'PY'
import hashlib, json, pathlib, sys
man = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
root = pathlib.Path(sys.argv[2])
ruim = 0
for it in man["itens"]:
    p = root / it["path"]
    if not p.exists():
        print(f"  AUSENTE  {it['path']}"); ruim += 1; continue
    b = p.read_bytes()
    if hashlib.sha256(b).hexdigest() != it["sha256"]:
        print(f"  MUDOU    {it['path']}"); ruim += 1
if ruim:
    raise SystemExit(f"{ruim} divergência(s) — o pacote mudou desde a montagem; remonte")
print(f"  ok  {len(man['itens'])} arquivos, sha256 conferido um a um")
PY

# --- 1. rascunho novo ----------------------------------------------------------
if [ -r "$DIR/.draft-id" ]; then
  DRAFT="$(cat "$DIR/.draft-id")"
  say "1. reusando rascunho $DRAFT"
else
  say "1. criando rascunho novo (DOI novo)"
  DRAFT=$(curl -sf -X POST "${AUTH[@]}" -H "Content-Type: application/json" \
    -d '{"metadata":{}}' "$API/records" | jqr "['id']")
  echo "$DRAFT" > "$DIR/.draft-id"
  echo "  rascunho: $DRAFT"
fi

# --- 2. metadata, na forma InvenioRDM, com a description do arquivo -------------
say "2. gravando metadata"
python3 - "$DIR" > "$DIR/.metadata-final.json" <<'PY'
import json, pathlib, sys
d = pathlib.Path(sys.argv[1])
meta = json.loads((d / "zenodo-metadata.json").read_text(encoding="utf-8"))
meta["metadata"]["description"] = (d / "description.html").read_text(encoding="utf-8")
print(json.dumps(meta, ensure_ascii=False))
PY
curl -sf -X PUT "${AUTH[@]}" -H "Content-Type: application/json" \
  -d "@$DIR/.metadata-final.json" "$API/records/$DRAFT/draft" > /dev/null
echo "  metadata gravada"

# --- 3. arquivos: soltos + dois zips. Uma chave por vez (em lote com 2 dá 400). ---
# ⚠️ O Zenodo limita 100 arquivos por REGISTRO. O pacote tem 120, e a primeira
# tentativa morreu no 101º com "Uploading selected files will result in exceeding the
# max amount per record" — silenciada por `curl -sf`. Artefatos e scripts vão
# compactados; o MANIFEST guarda o sha256 de CADA arquivo, não do zip.
say "3. subindo o pacote"
n=0
while IFS= read -r rel; do
  key="$(basename "$rel")"
  # ⚠️ pular por STATUS não basta: um arquivo alterado localmente ficaria
  # "completed" no Zenodo para sempre e nunca seria reenviado. O gate do passo 4
  # pegou exatamente isso. Compara-se o md5; divergindo, a chave é apagada e refeita.
  loc=$(md5 -q "$rel" 2>/dev/null || md5sum "$rel" | cut -d" " -f1)
  rem=$(curl -s "${AUTH[@]}" "$API/records/$DRAFT/draft/files/$key" \
        | python3 -c "import json,sys
try:
    d=json.load(sys.stdin)
    print(d.get('checksum','').replace('md5:','') if d.get('status')=='completed' else '')
except Exception: print('')")
  [ -n "$rem" ] && [ "$rem" = "$loc" ] && continue
  if [ -n "$rem" ]; then
    curl -sf -X DELETE "${AUTH[@]}" "$API/records/$DRAFT/draft/files/$key" > /dev/null
    echo "  substituindo: $key"
  fi
  curl -sf -X POST "${AUTH[@]}" -H "Content-Type: application/json" \
    -d "[{\"key\":\"$key\"}]" "$API/records/$DRAFT/draft/files" > /dev/null
  curl -sf -X PUT "${AUTH[@]}" -H "Content-Type: application/octet-stream" \
    --upload-file "$rel" "$API/records/$DRAFT/draft/files/$key/content" > /dev/null
  curl -sf -X POST "${AUTH[@]}" "$API/records/$DRAFT/draft/files/$key/commit" > /dev/null
  n=$((n+1)); echo "  enviado: $key"
done < <(python3 - "$MANIFEST" "$ROOT" "$DIR" <<'PYX'
import json, sys, pathlib
man = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
root, dep = pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
for i in man["itens"]:
    if i["no_deposito"] == "solto": print(root / i["path"])
print(dep / "artefatos.zip"); print(dep / "scripts.zip")
print(dep / "MANIFEST.json")
PYX
)
echo "  $n arquivo(s) novo(s)"

# --- 4. readback DUPLO, cada forma pedida EXPLICITAMENTE -----------------------
# 🔴 `curl` sem `Accept` devolve a forma LEGADA: `files` vira lista e `rights` não
# existe (lá chama-se `license`). Ler a forma errada faria o gate concluir que a
# licença sumiu — ou, pior, aceitar um depósito sem ela. Cada campo é conferido na
# serialização em que ele existe.
say "4. readback (as duas formas, pedidas explicitamente)"
curl -sf -H "Accept: application/vnd.inveniordm.v1+json" "${AUTH[@]}" \
  "$API/records/$DRAFT/draft" > "$DIR/.readback-rdm.json"
curl -sf -H "Accept: application/json" "${AUTH[@]}" \
  "$API/records/$DRAFT/draft" > "$DIR/.readback-legacy.json"

python3 - "$DIR" "$ROOT" "$MANIFEST" <<'PY_GATE'
import hashlib, json, pathlib, sys, zipfile
d, root = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
man = json.loads(pathlib.Path(sys.argv[3]).read_text(encoding="utf-8"))
rdm = json.loads((d / ".readback-rdm.json").read_text(encoding="utf-8"))
leg = json.loads((d / ".readback-legacy.json").read_text(encoding="utf-8"))
falhas = []

# forma InvenioRDM: é onde `rights` e `publisher` existem
m = rdm.get("metadata", {})
if not isinstance(rdm.get("files", {}), dict):
    falhas.append("readback RDM veio na forma legada — o Accept não foi respeitado")
if not m.get("creators"):     falhas.append("creators VAZIO (forma RDM)")
if not m.get("rights"):       falhas.append("rights (licença) VAZIO (forma RDM)")
if not m.get("title"):        falhas.append("title vazio")
if m.get("version") != "1.0": falhas.append(f"version = {m.get('version')!r}, esperado '1.0'")
if not m.get("related_identifiers"): falhas.append("related_identifiers VAZIO")
# 🔴 `publisher` é obrigatório para REGISTRAR O DOI e só existe na forma RDM. Ele
# não aparece na legada, então um gate que lesse a legada nunca o veria — e o
# publish falharia depois de todos os checks passarem, que foi o que aconteceu.
if not m.get("publisher"):    falhas.append("publisher AUSENTE — bloqueia o publish")

# forma legada: confirma que o mesmo registro é visto pelos dois caminhos
if str(leg.get("id")) != str(rdm.get("id")):
    falhas.append(f"as duas formas veem registros diferentes: {leg.get('id')} vs {rdm.get('id')}")

# description byte a byte contra a fonte local
local = (d / "description.html").read_text(encoding="utf-8")
remoto = m.get("description", "")
# ⚠️ O Zenodo remove o newline FINAL. Toleramos exatamente isso e nada mais:
# `rstrip("\n")` não perdoa truncamento, só a quebra de linha terminal.
if local.rstrip("\n") != remoto.rstrip("\n"):
    falhas.append(f"description DIVERGE (local {len(local)}B, remoto {len(remoto)}B)")
if "PLACEHOLDER" in remoto:
    falhas.append("description ainda é o PLACEHOLDER — o gate de description falhou")

# arquivos: nas DUAS direções
ent = rdm.get("files", {}).get("entries") if isinstance(rdm.get("files"), dict) else None
ent = {e["key"]: e for e in (ent.values() if isinstance(ent, dict) else (ent or []))}
esperado = {pathlib.Path(i["path"]).name: root / i["path"]
            for i in man["itens"] if i["no_deposito"] == "solto"}
for z in ("artefatos.zip", "scripts.zip", "MANIFEST.json"):
    esperado[z] = d / z
for k in sorted(set(esperado) - set(ent)): falhas.append(f"FALTA no depósito: {k}")
for k in sorted(set(ent) - set(esperado)): falhas.append(f"SOBRA no depósito: {k}")
for k in sorted(set(esperado) & set(ent)):
    cs = str(ent[k].get("checksum", ""))
    if cs.startswith("md5:") and cs[4:] != hashlib.md5(esperado[k].read_bytes()).hexdigest():
        falhas.append(f"checksum diverge: {k}")

# ⚠️ os zips escondem 111 arquivos do readback. Sem isto, um zip truncado passaria: o
# checksum do zip bateria com o zip local, e o zip local é que estaria errado.
for nome in ("artefatos.zip", "scripts.zip"):
    dentro = {i["path"]: i["sha256"] for i in man["itens"] if i["no_deposito"] == nome}
    with zipfile.ZipFile(d / nome) as z:
        if set(z.namelist()) != set(dentro):
            falhas.append(f"{nome}: conteúdo difere do manifesto")
        for caminho, sha in dentro.items():
            if caminho in set(z.namelist()) and \
               hashlib.sha256(z.read(caminho)).hexdigest() != sha:
                falhas.append(f"{nome}: sha256 diverge em {caminho}")

if falhas:
    print("\n".join("  🔴 " + f for f in falhas))
    raise SystemExit(f"\n{len(falhas)} divergência(s) — NÃO publicar")
print(f"  ok  {len(ent)} arquivos no depósito, checksums nas duas direções")
print(f"  ok  {sum(1 for i in man['itens'] if i['no_deposito'] != 'solto')} arquivos "
      f"dentro dos zips, sha256 conferido um a um")
print("  ok  creators, rights, title, version e related_identifiers presentes (forma RDM)")
print("  ok  description idêntica byte a byte à fonte local")
PY_GATE

say "rascunho pronto e conferido"
echo "  ver:      https://zenodo.org/uploads/$DRAFT"
echo "  publicar: curl -X POST -H 'Authorization: Bearer \$ZENODO_TOKEN' $API/records/$DRAFT/draft/actions/publish"
echo "  descartar: curl -X DELETE -H 'Authorization: Bearer \$ZENODO_TOKEN' $API/records/$DRAFT/draft"
echo
echo "  ⚠️ este script NÃO publica. Publicar cria um DOI que não se apaga."
