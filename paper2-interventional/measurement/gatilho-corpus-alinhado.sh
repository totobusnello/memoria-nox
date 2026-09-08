#!/usr/bin/env bash
# gatilho-corpus-alinhado.sh — o corpus que o SERVING lê é o que o symlink aponta?
#
# ─── Por que existe (2026-09-08, §10.10 do DEVIATIONS-FOR-PAPER.md) ─────────
#
# `nox-mem-api` roda com `NOX_EPOCH_SNAPSHOT=active` e abre
# `/var/lib/nox-mem/epochs/current.db` — um SYMLINK que o cron reaponta às 06:00Z.
# O processo resolve o symlink UMA VEZ, no `open()`, e mantém o descriptor. Medido:
# subiu em `03/09 17:30` e cinco viradas depois ainda lia
# `e20260903T060001Z.db`, já podado do disco — inode 553124 contra 524930 do
# snapshot vigente. O corpus do ensaio ficou congelado em `MAX(created_at) =
# 2026-08-24` por cinco dias, e nada denunciava: o caminho continuava existindo e
# apontando para o lugar certo.
#
# ⚠️ Todo instrumento resolvia o symlink por conta própria e media OUTRO arquivo.
# Enquanto o banco esteve congelado por outro defeito, os dois coincidiram — e no
# dia em que descongelou, o gatilho de composição reportou `agentFresh = 219`
# enquanto o canal servido tinha 0. `RED` verdadeiro sobre o corpus errado.
#
# A pergunta certa não é "o symlink está certo?" nem "o snapshot de hoje existe?".
# É **de qual inode o processo está lendo**, e isso só o `/proc/<pid>/fd` responde.
#
# ─── Duas pernas ───────────────────────────────────────────────────────────
#
# 1. `RED corpus-desalinhado`  — o fd aponta para inode != o de `current.db`.
# 2. `RED corpus-deletado`     — o fd aponta para arquivo já removido do disco.
#    Vem primeiro na mensagem porque é o caso em que o arquivo lido é
#    IRRECUPERÁVEL após um restart: recuperar com
#    `cat /proc/<pid>/fd/<n> > copia.db` ANTES de mexer no serviço.
#
# Exit 0 sempre: o estado vive na linha.
set -uo pipefail
SVC="${SVC:-nox-mem-api}"
LINK="${LINK:-/var/lib/nox-mem/epochs/current.db}"
STATUS=""; NDJSON=""
while [ $# -gt 0 ]; do
  case "$1" in
    --status) STATUS="$2"; shift 2;;
    --ndjson) NDJSON="$2"; shift 2;;
    --servico) SVC="$2"; shift 2;;
    --link) LINK="$2"; shift 2;;
    *) echo "argumento desconhecido: $1" >&2; exit 2;;
  esac
done
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

emitir() {  # $1=estado $2=resto
  local linha="$1 p2-corpus-alinhado $2 ts=$TS"
  echo "$linha"
  [ -n "$STATUS" ] && printf '%s\n' "$linha" > "$STATUS"
  if [ -n "$NDJSON" ]; then
    python3 - "$NDJSON" "$1" "$2" "$TS" <<'PYND' 2>/dev/null || true
import json, sys
nd, estado, resto, ts = sys.argv[1:5]
try:
    with open(nd, "a") as f:
        f.write(json.dumps({"ts": ts, "tag": "p2_gatilho_corpus_alinhado",
                            "estado": estado, "linha_status": resto}) + "\n")
except Exception:
    pass
PYND
  fi
  exit 0
}

PID="$(systemctl show "$SVC" -p MainPID --value 2>/dev/null)"
case "$PID" in ''|0) emitir RED "motivo=servico-sem-pid servico=$SVC";; esac

# Só se aplica quando o serving usa snapshot de epoch. Com o modo desligado, o
# alinhamento não é a grandeza a vigiar — e dizer GREEN sem explicar por quê é o
# guarda que fica calado por não ter o dado.
MODO="$(systemctl show "$SVC" -p Environment --value 2>/dev/null | tr ' ' '\n' | sed -n 's/^NOX_EPOCH_SNAPSHOT=//p' | tail -1)"
[ "$MODO" = "active" ] || emitir GREEN "motivo=snapshot-de-epoch-desligado semantica=pergunta-nao-se-aplica NOX_EPOCH_SNAPSHOT=${MODO:-vazio}"

[ -e "$LINK" ] || emitir RED "motivo=symlink-nao-existe link=$LINK"
ALVO="$(readlink -f "$LINK")"
INODE_LINK="$(stat -c %i "$ALVO" 2>/dev/null)"
[ -n "$INODE_LINK" ] || emitir RED "motivo=nao-resolvi-o-symlink link=$LINK"

# O fd do processo que aponta para o diretório de epochs. `ls -l` mostra o nome
# original mesmo quando o arquivo foi removido, com o sufixo " (deleted)".
DIR="$(dirname "$ALVO")"
FDLINE="$(ls -l "/proc/$PID/fd" 2>/dev/null | grep -F "$DIR/" | grep -v "\-wal\|\-shm" | head -1)"
[ -n "$FDLINE" ] || emitir YELLOW "motivo=nenhum-fd-para-o-diretorio-de-epochs dir=$DIR pid=$PID semantica=o-processo-pode-nao-ter-aberto-ainda"

FDNUM="$(printf '%s' "$FDLINE" | awk '{for(i=1;i<=NF;i++) if($i=="->") {print $(i-1); exit}}')"
FDALVO="$(printf '%s' "$FDLINE" | sed 's/.* -> //')"
INODE_FD="$(stat -L -c %i "/proc/$PID/fd/$FDNUM" 2>/dev/null)"

case "$FDALVO" in
  *"(deleted)") emitir RED "motivo=corpus-DELETADO-e-vivo-so-pelo-fd fd=$FDNUM lido=${FDALVO% (deleted)} inode_fd=$INODE_FD inode_link=$INODE_LINK ACAO=recuperar com 'cat /proc/$PID/fd/$FDNUM > copia.db' ANTES de qualquer restart";;
esac
if [ "$INODE_FD" != "$INODE_LINK" ]; then
  emitir RED "motivo=corpus-desalinhado fd=$FDNUM lido=$FDALVO inode_fd=$INODE_FD esperado=$ALVO inode_link=$INODE_LINK ACAO=o serving le um snapshot antigo; realinhar exige restart e o restart e mudanca de regime"
fi
emitir GREEN "motivo=alinhado fd=$FDNUM inode=$INODE_FD alvo=$(basename "$ALVO")"
