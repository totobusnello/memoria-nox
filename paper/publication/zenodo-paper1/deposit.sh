#!/usr/bin/env bash
# deposit.sh — cria o rascunho do Paper 1 no Zenodo e para. NÃO publica.
#
# Por que Zenodo, e não TechRxiv: em 2026-09-07 o TechRxiv está com submissões
# FECHADAS ("preparing a transition to a new platform"), sem prazo, e o preprint mais
# recente listado é de 6 de março de 2026. Ver `../techrxiv-submission-runbook.md`.
# Por que não o arXiv: não aceitou este manuscrito em 2026-09-03 e a condição que
# invocou (endosso de journal) NÃO é satisfeita por DOI de repositório.
#
# DOI NOVO, registro separado: `POST /api/records`. Não é versão de nada — o
# 10.5281/zenodo.22110203 é o pré-registro do Paper 2 e o 10.5281/zenodo.22181415 é o
# Paper A. Como nova versão, este herdaria o título do outro estudo.
#
# Caminho: API InvenioRDM (`/api/records`), NUNCA a legada
# (`/api/deposit/depositions`). Razão já paga em erro: o PUT legado aceita forma
# legada e APAGA campos em silêncio devolvendo HTTP 200 — autor e licença
# desapareceram assim uma vez.
#
# Herdado do `paper2-interventional/deposit/paperA/deposit.sh`, tudo já pago em erro:
#   · readback DUPLO (legado + InvenioRDM) — `publisher` não existe na forma legada,
#     e sem ele o publish falha DEPOIS de todos os checks passarem;
#   · `POST /files` uma chave por vez;
#   · description conferida byte a byte contra a fonte local.
#
# ⚠️ Este script NÃO publica. Ele para com o rascunho pronto e conferido. Publicar é
# um passo separado, manual e irreversível: um DOI publicado não se apaga.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/../../.." && pwd)"
API=https://zenodo.org/api

PDF="$ROOT/paper/build/paper-tecnico-nox-mem.pdf"
# Pino do artefato conferido em 2026-09-07: 77 páginas, 353.686 B, reconstruído após a
# honesty pass de 03–04/09 e o abstract reescrito em 07/09. O PDF anterior era de 12 de
# julho e NÃO tinha nenhum dos dois.
PDF_SHA256=a984c18782f36c7e852e0d61df7c8af526087f76e07abf45168aa92dfc34de9e

SECRET_FILE="$HOME/.config/secrets/ZENODO_TOKEN"
if [ -z "${ZENODO_TOKEN:-}" ] && [ -r "$SECRET_FILE" ]; then
  ZENODO_TOKEN="$(tr -d '\r\n' < "$SECRET_FILE")"
fi
: "${ZENODO_TOKEN:?sem token — grave em ~/.config/secrets/ZENODO_TOKEN (chmod 600)}"
AUTH=(-H "Authorization: Bearer $ZENODO_TOKEN")

jqr() { python3 -c "import json,sys;d=json.load(sys.stdin);print(eval('d'+sys.argv[1]))" "$1"; }
say() { printf '\n\033[1m%s\033[0m\n' "$*"; }

# --- 0. gate local: o PDF no disco é o PDF conferido? --------------------------
# ⚠️ Sem este gate o risco concreto é subir o PDF de julho, que afirma SOTA duplo —
# alegação retratada em 03/09. Pino por sha256 dos BYTES, não por mtime: mtime muda
# num `touch` e não muda num `cp -p`.
say "0. conferindo o PDF contra o pino"
[ -r "$PDF" ] || { echo "  PDF ausente — rode ./scripts/build-paper.sh"; exit 1; }
GOT=$(shasum -a 256 "$PDF" | cut -d' ' -f1)
if [ "$GOT" != "$PDF_SHA256" ]; then
  echo "  🔴 sha256 diverge"
  echo "     esperado $PDF_SHA256"
  echo "     obtido   $GOT"
  echo "     O PDF mudou desde a conferência. Reconfira o conteúdo e atualize o pino"
  echo "     DELIBERADAMENTE — não atualize o pino só para o gate passar."
  exit 1
fi
echo "  ok  sha256 confere ($(wc -c < "$PDF" | tr -d ' ') bytes)"

# --- 0b. gate de conteúdo: as retratações de 03–04/09 sobreviveram ao build? ----
# O sha256 prova que o arquivo não mudou; ele NÃO prova que o arquivo é o certo. Este
# gate lê o texto e exige o abstract novo E a ausência das duas alegações retratadas.
say "0b. conferindo o texto extraído do PDF"
if command -v pdftotext > /dev/null 2>&1; then
  python3 - "$PDF" <<'PY'
import subprocess, sys
t = subprocess.run(["pdftotext", sys.argv[1], "-"],
                   capture_output=True, text=True, check=True).stdout
falhas = []
# ⚠️ o `pdftotext` quebra linhas, então frase longa não serve de sonda. Estas três
# cabem numa linha no layout atual; se o layout mudar, o gate falha ALTO em vez de
# passar em silêncio — que é a direção certa do erro.
if "Three findings cut against our own headline" not in t:
    falhas.append("abstract novo AUSENTE — o PDF é anterior a 07/09")
for retratada in ("state-of-the-art on both",
                  "above every published MemOS number"):
    if retratada in t:
        falhas.append(f"alegação RETRATADA presente: {retratada!r}")
if falhas:
    print("\n".join("  🔴 " + f for f in falhas)); raise SystemExit(1)
print("  ok  abstract novo presente; nenhuma alegação retratada no texto")
PY
else
  echo "  ⚠️ pdftotext ausente — gate de conteúdo NÃO rodou. O gate de sha256 rodou."
fi

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

# --- 2. metadata, forma InvenioRDM, com a description do arquivo ---------------
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

# --- 3. o arquivo --------------------------------------------------------------
# ⚠️ pular por STATUS não basta: um arquivo trocado localmente ficaria "completed" no
# Zenodo para sempre e nunca seria reenviado. Compara-se o md5; divergindo, apaga e
# refaz a chave.
say "3. subindo o PDF"
KEY=paper-tecnico-nox-mem.pdf
LOC=$(md5 -q "$PDF" 2>/dev/null || md5sum "$PDF" | cut -d' ' -f1)
REM=$(curl -s "${AUTH[@]}" "$API/records/$DRAFT/draft/files/$KEY" \
      | python3 -c "import json,sys
try:
    d=json.load(sys.stdin)
    print(d.get('checksum','').replace('md5:','') if d.get('status')=='completed' else '')
except Exception: print('')")
if [ -n "$REM" ] && [ "$REM" = "$LOC" ]; then
  echo "  já no depósito, md5 confere"
else
  if [ -n "$REM" ]; then
    curl -sf -X DELETE "${AUTH[@]}" "$API/records/$DRAFT/draft/files/$KEY" > /dev/null
    echo "  substituindo chave existente"
  fi
  curl -sf -X POST "${AUTH[@]}" -H "Content-Type: application/json" \
    -d "[{\"key\":\"$KEY\"}]" "$API/records/$DRAFT/draft/files" > /dev/null
  curl -sf -X PUT "${AUTH[@]}" -H "Content-Type: application/octet-stream" \
    --upload-file "$PDF" "$API/records/$DRAFT/draft/files/$KEY/content" > /dev/null
  curl -sf -X POST "${AUTH[@]}" "$API/records/$DRAFT/draft/files/$KEY/commit" > /dev/null
  echo "  enviado: $KEY"
fi

# --- 4. readback DUPLO, cada forma pedida EXPLICITAMENTE -----------------------
# 🔴 `curl` sem `Accept` devolve a forma LEGADA: `files` vira lista e `rights` não
# existe (lá chama-se `license`). Ler a forma errada faria o gate concluir que a
# licença sumiu — ou, pior, aceitar um depósito sem ela.
say "4. readback (as duas formas, pedidas explicitamente)"
curl -sf -H "Accept: application/vnd.inveniordm.v1+json" "${AUTH[@]}" \
  "$API/records/$DRAFT/draft" > "$DIR/.readback-rdm.json"
curl -sf -H "Accept: application/json" "${AUTH[@]}" \
  "$API/records/$DRAFT/draft" > "$DIR/.readback-legacy.json"

python3 - "$DIR" "$PDF" "$PDF_SHA256" <<'PY_GATE'
import hashlib, json, pathlib, sys
d = pathlib.Path(sys.argv[1]); pdf = pathlib.Path(sys.argv[2]); pino = sys.argv[3]
rdm = json.loads((d / ".readback-rdm.json").read_text(encoding="utf-8"))
leg = json.loads((d / ".readback-legacy.json").read_text(encoding="utf-8"))
falhas = []

m = rdm.get("metadata", {})
if not isinstance(rdm.get("files", {}), dict):
    falhas.append("readback RDM veio na forma legada — o Accept não foi respeitado")
if not m.get("creators"):            falhas.append("creators VAZIO (forma RDM)")
if not m.get("rights"):              falhas.append("rights (licença) VAZIO (forma RDM)")
if not m.get("title"):               falhas.append("title vazio")
if m.get("version") != "1.0":        falhas.append(f"version = {m.get('version')!r}")
if not m.get("related_identifiers"): falhas.append("related_identifiers VAZIO")
# 🔴 `publisher` é obrigatório para REGISTRAR O DOI e só existe na forma RDM. Um gate
# que lesse só a legada nunca o veria, e o publish falharia depois de tudo passar.
if not m.get("publisher"):           falhas.append("publisher AUSENTE — bloqueia o publish")
if [l.get("id") for l in m.get("languages") or []] != ["eng"]:
    falhas.append(f"languages = {m.get('languages')!r}, esperado eng (o paper é em inglês)")

if str(leg.get("id")) != str(rdm.get("id")):
    falhas.append(f"as duas formas veem registros diferentes: "
                  f"{leg.get('id')} vs {rdm.get('id')}")

# description byte a byte contra a fonte local
local = (d / "description.html").read_text(encoding="utf-8")
remoto = m.get("description", "")
# ⚠️ O Zenodo remove o newline FINAL. Toleramos exatamente isso e nada mais:
# `rstrip("\n")` não perdoa truncamento, só a quebra terminal.
if local.rstrip("\n") != remoto.rstrip("\n"):
    falhas.append(f"description DIVERGE (local {len(local)}B, remoto {len(remoto)}B)")
# a description carrega os limitadores; se um sumir, o campo mente sozinho
for exigido in ("not statistically significant", "has not been peer reviewed",
                "not accepted", "3-7%"):
    if exigido not in remoto:
        falhas.append(f"limitador AUSENTE da description remota: {exigido!r}")

# arquivos: nas DUAS direções, e contra o pino — não só contra o disco
ent = rdm.get("files", {}).get("entries") if isinstance(rdm.get("files"), dict) else None
ent = {e["key"]: e for e in (ent.values() if isinstance(ent, dict) else (ent or []))}
esperado = {"paper-tecnico-nox-mem.pdf": pdf}
for k in sorted(set(esperado) - set(ent)): falhas.append(f"FALTA no depósito: {k}")
for k in sorted(set(ent) - set(esperado)): falhas.append(f"SOBRA no depósito: {k}")
for k in sorted(set(esperado) & set(ent)):
    cs = str(ent[k].get("checksum", ""))
    if cs.startswith("md5:") and \
       cs[4:] != hashlib.md5(esperado[k].read_bytes()).hexdigest():
        falhas.append(f"md5 diverge no depósito: {k}")
if hashlib.sha256(pdf.read_bytes()).hexdigest() != pino:
    falhas.append("o PDF mudou DURANTE o depósito")

if falhas:
    print("\n".join("  🔴 " + f for f in falhas))
    raise SystemExit(f"\n{len(falhas)} divergência(s) — NÃO publicar")
print(f"  ok  {len(ent)} arquivo no depósito, md5 nas duas direções + sha256 do pino")
print("  ok  creators, rights, title, version, publisher, languages, "
      "related_identifiers (forma RDM)")
print("  ok  description idêntica byte a byte à fonte local, com os 4 limitadores")
PY_GATE

say "rascunho pronto e conferido"
echo "  ver:       https://zenodo.org/uploads/$DRAFT"
echo "  descartar: curl -X DELETE -H 'Authorization: Bearer \$ZENODO_TOKEN' $API/records/$DRAFT/draft"
echo
echo "  ⚠️ este script NÃO publica. Publicar cria um DOI que não se apaga, e é do Toto:"
echo "     abra a página acima, confira, e clique em Publish."
