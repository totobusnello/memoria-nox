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

# Segunda copia, off-machine. O host vem do ambiente e NUNCA fica escrito aqui:
# este arquivo e versionado num repositorio publico.
#   export NOX_LASTRO_HOST=root@<host-de-armazenamento>
#   export NOX_LASTRO_DIR=/var/backups/nox-mem/paper1-lastro-rc4
# Ausente a variavel, a perna remota e DECLARADA COMO NAO VERIFICADA, nunca
# silenciosamente omitida -- "nao verifiquei" e "verifiquei e esta bem" nao podem
# ter a mesma saida.
REMOTO_HOST="${NOX_LASTRO_HOST:-}"
REMOTO_DIR="${NOX_LASTRO_DIR:-/var/backups/nox-mem/paper1-lastro-rc4}"
RECIBOS="$BACKUP/recibos"
mkdir -p "$RECIBOS" 2>/dev/null

# ---- perna remota: hashes calculados NO DESTINO, nao na origem
REMOTO_SHA=""
if [ -n "$REMOTO_HOST" ]; then
  REMOTO_SHA=$(mktemp /var/tmp/lastro-remoto.XXXXXX)
  # ⚠️ Sem `timeout`: no macOS ele vem do Homebrew e o PATH do launchd e minimo
  # (/usr/bin:/bin:/usr/sbin:/sbin). Usar `timeout` aqui fazia a perna remota
  # sair "host inalcancavel" num agendamento onde o ssh funciona perfeitamente --
  # falha do agendador lida como falha do host. Mesma familia do "cron nao tem
  # /sbin". O limite de tempo vem das opcoes do proprio ssh.
  if ! /usr/bin/ssh -o ConnectTimeout=15 -o BatchMode=yes \
       -o ServerAliveInterval=10 -o ServerAliveCountMax=6 "$REMOTO_HOST" \
       "cd '$REMOTO_DIR' 2>/dev/null && find . -type f -print0 | xargs -0 sha256sum" \
       > "$REMOTO_SHA" 2>/dev/null; then
    echo "⚠️ perna remota NAO verificada: falha ao consultar $REMOTO_HOST" >&2
    rm -f "$REMOTO_SHA"; REMOTO_SHA="INDISPONIVEL"
  fi
fi

python3 - "$REPO" "$BACKUP" "$RECIBOS" "${REMOTO_SHA:-SEM_HOST}" <<'PY'
import hashlib, json, os, sys, tempfile
from datetime import datetime, timezone

repo, backup, recibos, remoto_sha = sys.argv[1:5]
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

# hashes da copia remota, se a perna correu
remoto = {}
perna_remota = "sem host configurado (NOX_LASTRO_HOST)"
if remoto_sha == "INDISPONIVEL":
    perna_remota = "NAO VERIFICADA -- host inalcancavel"
elif remoto_sha not in ("SEM_HOST", ""):
    try:
        with open(remoto_sha, encoding="utf-8") as fh:
            for linha in fh:
                h, _, cam = linha.strip().partition("  ")
                remoto[cam.lstrip("./")] = h
        perna_remota = f"verificada: {len(remoto)} arquivo(s) lidos no destino"
    except OSError:
        perna_remota = "NAO VERIFICADA -- nao consegui ler os hashes remotos"

perdidos_origem, perdidos_backup, divergentes, ok = [], [], [], []
rem_ok, rem_div, rem_falta = [], [], []
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
    if remoto:
        g = remoto.get(rel)
        if g is None:
            rem_falta.append(rel)
        elif g != esperado:
            rem_div.append(rel)
        else:
            rem_ok.append(rel)

recibo = {
    "quando_utc": agora,
    "backup": backup,
    "sentinela": "passou — o comparador acusa 1 bit de diferenca",
    "ok": len(ok),
    "divergentes": divergentes,
    "perdidos_na_origem": perdidos_origem,
    "perdidos_no_backup": perdidos_backup,
    "copia_remota": {
        "estado": perna_remota,
        "ok": len(rem_ok),
        "divergentes": rem_div,
        "faltando": rem_falta,
    },
}
with open(os.path.join(recibos, f"recibo-{agora}.json"), "w", encoding="utf-8") as fh:
    json.dump(recibo, fh, indent=2, ensure_ascii=False)

print(f"sentinela: passou  ·  integros no backup local: {len(ok)}")
print(f"copia remota: {perna_remota}"
      + (f"  ·  integros: {len(rem_ok)}" if remoto else ""))
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
if rem_div or rem_falta:
    print(f"🔴 COPIA REMOTA: {len(rem_div)} divergente(s), {len(rem_falta)} faltando",
          file=sys.stderr)
    for r in rem_div + rem_falta:
        print("   " + r, file=sys.stderr)
sys.exit(1 if (perdidos_backup or divergentes or rem_div or rem_falta) else 0)
PY

ec=$?
[ -f "${REMOTO_SHA:-}" ] && rm -f "$REMOTO_SHA"
exit $ec
