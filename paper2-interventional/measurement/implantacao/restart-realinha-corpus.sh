#!/usr/bin/env bash
# restart-realinha-corpus.sh — realinha o corpus do serving na FRONTEIRA de epoch.
#
# Autorizado pelo Toto em 2026-09-08. Contexto no §10.10 do DEVIATIONS-FOR-PAPER.md:
# o `nox-mem-api` resolveu `current.db` uma vez, em 03/09 17:30, e serve de um
# snapshot já podado do disco. Só um restart realinha — e o restart é MUDANÇA DE
# REGIME, não conserto rotineiro.
#
# ─── Por que 2026-09-15 09:00Z, e não hoje ─────────────────────────────────
#
# Medido em 08/09, com as janelas que o código realmente usa
# (`freshMaxAgeDays = 7` para o agente, `freshGlobalMaxAgeDays = 30` para o global):
#
#   corpus do serving (03/09):  agentFresh   0  ·  globalFresh 108  ·  designados 19/19
#   corpus atual      (08/09):  agentFresh 253  ·  globalFresh 115  ·  designados 19/19
#
# Reiniciar HOJE levaria o canal de `interleaveFresh([], 108)` para
# `interleaveFresh(253, 115)`: `interleaveFresh` deixa de ser função-zero e cada
# designado global sai da posição `i` para `2i + 1` — a distância até os
# `freshSlots` DOBRA, e a calibração de dose de 27/08 (medida com o canal do agente
# vazio) deixa de valer para o resto do ensaio.
#
# Os 253 chunks de sessão têm todos `source_date = 2026-09-08` e saem da janela de
# 7 dias em **2026-09-15 00:00:00Z**. A partir dali `agentFresh` volta a 0 por
# expiração, e o restart passa a ser só ATUALIZAÇÃO DE CORPUS — a forma do canal
# fica idêntica (`interleaveFresh([], 115)`), a calibração continua válida, e
# nenhum epoch entra em regime diferente. Nove horas depois abre o epoch `09-15`,
# que é a primeira fronteira limpa após a expiração.
#
# ─── As pré-condições ABORTAM. Nenhuma delas é decorativa. ─────────────────
set -uo pipefail
STATUS=/var/lib/nox-mem/p2/status-restart-realinha.txt
NDJSON=/var/lib/nox-mem/p2/gatilhos.ndjson
SVC=nox-mem-api
LINK=/var/lib/nox-mem/epochs/current.db
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

reg() {  # $1=estado $2=resto
  local l="$1 p2-restart-realinha $2 ts=$TS"
  echo "$l"; printf '%s\n' "$l" > "$STATUS"
  python3 - "$NDJSON" "$1" "$2" "$TS" <<'PYND' 2>/dev/null || true
import json, sys
nd, estado, resto, ts = sys.argv[1:5]
try:
    with open(nd, "a") as f:
        f.write(json.dumps({"ts": ts, "tag": "p2_restart_realinha",
                            "estado": estado, "linha_status": resto}) + "\n")
except Exception:
    pass
PYND
}
abortar() { reg RED "motivo=ABORTADO-$1 acao=nao-reiniciei"; exit 0; }

# (1) FRONTEIRA DE EPOCH. Os epochs viram às 09:00Z (`epochInicioISO`); reiniciar
#     no meio faz um epoch ser servido com DOIS corpora — heterogeneidade interna,
#     que é o defeito do Epoch 1 (§10.1) e não se conserta depois.
HH="$(date -u +%H)"; MM="$(date -u +%M)"
[ "$HH" = "09" ] && [ "$MM" -lt 6 ] || abortar "fora-da-fronteira-de-epoch hora=${HH}:${MM}Z esperado=09:00-09:05Z"

# (2) HÁ O QUE REALINHAR? Se já está alinhado, reiniciar é custo sem benefício.
AL="$(/root/.openclaw/scripts/p2/gatilho-corpus-alinhado.sh 2>/dev/null | head -1)"
case "$AL" in
  GREEN*) reg GREEN "motivo=nada-a-fazer-ja-alinhado detalhe=$(printf '%s' "$AL" | tr '|' '/')"; exit 0;;
  RED*) : ;;
  *) abortar "guarda-de-alinhamento-inconclusivo detalhe=$(printf '%s' "$AL" | tr '|' '/')";;
esac

# (3) A PRÉ-CONDIÇÃO QUE DEFINE A DATA: `agentFresh` tem de estar VAZIO no corpus
#     que o processo vai passar a ler. É isto que faz o restart não mudar a forma
#     do canal. Se alguém rodar o `session-distill` à mão antes desta data, o pool
#     reenche e a condição falha — de propósito.
ALVO="$(readlink -f "$LINK")"
AF="$(sqlite3 "$ALVO" "SELECT COUNT(*) FROM chunks WHERE source_file LIKE 'sessions/%' AND (COALESCE(importance,0)>=0.7 OR COALESCE(pain,0)>=0.7) AND julianday('now')-julianday(COALESCE(source_date,created_at))<=7;" 2>/dev/null)"
case "$AF" in ''|*[!0-9]*) abortar "nao-medi-agentFresh alvo=$ALVO";; esac
[ "$AF" -eq 0 ] || abortar "agentFresh-nao-esta-vazio n=$AF alvo=$(basename "$ALVO") ACAO=reiniciar agora mudaria a forma do canal e invalidaria a calibracao de 27/08"

GF="$(sqlite3 "$ALVO" "SELECT COUNT(*) FROM chunks WHERE (source_file LIKE 'memory/entities/%' OR source_file='memory/lessons.md') AND (COALESCE(importance,0)>=0.7 OR COALESCE(pain,0)>=0.7) AND julianday('now')-julianday(COALESCE(source_date,created_at))<=30;" 2>/dev/null)"
DES="$(sqlite3 "$ALVO" "SELECT COUNT(*) FROM chunks WHERE id IN (308216,308218,308222,308230,308238,308240,308256,308264,308270,308274,308280,308284,308286,308292,308296,308300,308306,308312,308316);" 2>/dev/null)"
# (4) Os 19 designados TÊM de estar no corpus novo. Sem eles a intervenção não
#     tem alvo, e a designação não se refaz.
[ "$DES" = "19" ] || abortar "designados-incompletos-no-corpus-novo n=$DES/19 alvo=$(basename "$ALVO")"

# (5) RECUPERAR o corpus antigo antes de mexer: ele vive só pelo fd, e o restart
#     o apaga para sempre. É a única cópia do que serviu o ensaio até aqui.
PID="$(systemctl show "$SVC" -p MainPID --value)"
FDNUM="$(ls -l "/proc/$PID/fd" 2>/dev/null | grep -F "/var/lib/nox-mem/epochs/" | grep -v -- "-wal\|-shm" | head -1 | awk '{for(i=1;i<=NF;i++) if($i=="->") {print $(i-1); exit}}')"
[ -n "$FDNUM" ] || abortar "nao-achei-o-fd-do-corpus pid=$PID"
BKP="/var/lib/nox-mem/p2/corpus-SERVING-pre-restart-$(date -u +%Y%m%dT%H%M%SZ).db"
cat "/proc/$PID/fd/$FDNUM" > "$BKP" || abortar "falha-ao-recuperar-o-corpus-antigo"
QC="$(sqlite3 "$BKP" "PRAGMA quick_check;" 2>/dev/null | head -1)"
[ "$QC" = "ok" ] || abortar "copia-do-corpus-antigo-corrompida quick_check=$QC arquivo=$BKP"

# ─── ação ──────────────────────────────────────────────────────────────────
systemctl restart "$SVC" || abortar "restart-falhou"
for i in $(seq 1 30); do
  curl -s -m 3 -o /dev/null -w "" http://127.0.0.1:18802/api/health && break
  sleep 2
done
COD="$(curl -s -m 5 -o /dev/null -w "%{http_code}" http://127.0.0.1:18802/api/health)"
[ "$COD" = "200" ] || { reg RED "motivo=servico-nao-voltou http=$COD backup=$BKP ACAO=investigar AGORA"; exit 0; }

# (6) Confirmar por ESTADO OBSERVÁVEL, não por "o restart não deu erro".
AL2="$(/root/.openclaw/scripts/p2/gatilho-corpus-alinhado.sh 2>/dev/null | head -1)"
case "$AL2" in
  GREEN*) reg GREEN "motivo=REALINHADO corpus=$(basename "$ALVO") agentFresh=$AF globalFresh=$GF designados=$DES/19 backup_antigo=$BKP verificacao=$(printf '%s' "$AL2" | tr '|' '/')";;
  *) reg RED "motivo=reiniciei-e-SEGUE-desalinhado detalhe=$(printf '%s' "$AL2" | tr '|' '/') backup=$BKP";;
esac
