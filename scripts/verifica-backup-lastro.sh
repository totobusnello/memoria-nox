#!/usr/bin/env bash
# Verifica periodicamente que (1) o lastro segue na origem e (2) a copia de
# backup continua integra -- e grava RECIBO DATADO de cada passagem.
#
# Por que o recibo e a sentinela: sem eles, "verifiquei e esta tudo bem" e "nao
# rodou" tem a mesma saida -- silencio. Neste projeto isso ja custou 3,3 meses de
# guarda verde sobre falha real. Entao:
#
#   sentinela -- a cada ciclo, o script fabrica um par de arquivos identicos,
#                corrompe um byte de um deles, e EXIGE que o comparador acuse. Se
#                o comparador nao acusar, ele esta cego e o ciclo sai 2 sem nem
#                olhar o lastro.
#   recibo    -- arquivo datado por passagem. Recibo velho e a prova de que nao
#                rodou; ausencia de alarme nao e.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP="${1:-$HOME/Backups/memoria-nox-lastro-2026-09-12}"
RECIBOS="$BACKUP/recibos"
mkdir -p "$RECIBOS" 2>/dev/null

python3 - "$REPO" "$BACKUP" "$RECIBOS" <<'PY'
import hashlib, json, os, sys, tempfile
from datetime import datetime, timezone

repo, backup, recibos = sys.argv[1:4]
agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

# ---- SENTINELA: prova, neste ciclo, que o comparador ve divergencia
with tempfile.TemporaryDirectory(dir="/var/tmp") as t:
    a, b = os.path.join(t, "a"), os.path.join(t, "b")
    dados = os.urandom(4096)
    open(a, "wb").write(dados)
    open(b, "wb").write(dados[:-1] + bytes([dados[-1] ^ 0x01]))  # 1 bit trocado
    if sha(a) == sha(b):
        print("SENTINELA FALHOU: o comparador nao ve 1 bit de diferenca ⇒ cego",
              file=sys.stderr)
        sys.exit(2)
    if sha(a) != sha(a):
        print("SENTINELA FALHOU: comparador instavel", file=sys.stderr)
        sys.exit(2)

mp = os.path.join(repo, "eval/q4-comparison/MANIFESTO-LASTRO.json")
if not os.path.exists(mp):
    print(f"manifesto ausente: {mp}", file=sys.stderr); sys.exit(2)
with open(mp, encoding="utf-8") as fh:
    arte = json.load(fh)["artefatos"]

perdidos_origem, perdidos_backup, divergentes, ok = [], [], [], []
for rel, e in sorted(arte.items()):
    if e.get("estado") != "presente":
        continue
    esperado = e.get("sha256")
    o = os.path.join(repo, rel)
    c = os.path.join(backup, rel)
    if not os.path.exists(o):
        perdidos_origem.append(rel)
    if not os.path.exists(c):
        perdidos_backup.append(rel); continue
    obtido = sha(c)
    (ok if obtido == esperado else divergentes).append(rel)

recibo = {
    "quando_utc": agora,
    "backup": backup,
    "sentinela": "passou — o comparador acusa 1 bit de diferenca",
    "ok": len(ok),
    "divergentes": divergentes,
    "perdidos_na_origem": perdidos_origem,
    "perdidos_no_backup": perdidos_backup,
}
with open(os.path.join(recibos, f"recibo-{agora}.json"), "w", encoding="utf-8") as fh:
    json.dump(recibo, fh, indent=2, ensure_ascii=False)

print(f"sentinela: passou  ·  integros no backup: {len(ok)}")
if perdidos_origem:
    print(f"⚠️ AUSENTES NA ORIGEM ({len(perdidos_origem)}) — o backup e a unica copia:",
          file=sys.stderr)
    for r in perdidos_origem: print("   " + r, file=sys.stderr)
if perdidos_backup:
    print(f"🔴 AUSENTES NO BACKUP ({len(perdidos_backup)}):", file=sys.stderr)
    for r in perdidos_backup: print("   " + r, file=sys.stderr)
if divergentes:
    print(f"🔴 DIVERGEM DO MANIFESTO ({len(divergentes)}):", file=sys.stderr)
    for r in divergentes: print("   " + r, file=sys.stderr)
sys.exit(1 if (perdidos_backup or divergentes) else 0)
PY
