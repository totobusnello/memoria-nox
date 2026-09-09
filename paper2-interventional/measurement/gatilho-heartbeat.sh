#!/usr/bin/env bash
# gatilho-heartbeat.sh — o serving PAROU? E a unidade que fechou está inteira?
#
# ─── Por que existe (2026-09-09) ────────────────────────────────────────────
#
# O epoch 2026-09-02 do ensaio NUNCA foi servido — zero registros `p2_outcome` —
# e o 2026-09-03 saiu parcial (441 de 672). A lacuna mediu 32,53 h com a API
# respondendo 200. Nenhum alarme disparou, e a razão é estrutural: todo monitor
# deste ensaio LÊ O ÚLTIMO EPOCH e confere a dose sobre ele. Um monitor cujo
# predicado precisa de um epoch para avaliar **não dispara quando não há epoch
# nenhum** — ele fica calado, e o silêncio é indistinguível de "está tudo bem".
# É a regra 9 do `CLAUDE.md`, e a perna que falta é esta: *nenhuma linha nova em
# N horas, medido contra o relógio de parede*, sem depender de epoch, de dose,
# de designação ou de corpus.
#
# ─── O teto vem de medição, não de chute ────────────────────────────────────
#
# Medido em 2026-09-09 sobre os 11.396 registros `p2_outcome` de
# `p2-serving.ndjson` (2026-08-21T22:57Z → 2026-09-09T09:52Z), intervalos entre
# instantes distintos consecutivos:
#
#   mediana 0,7 s · p90 894,8 s · p99 897,4 s · p999 899,2 s
#   3º maior intervalo = 0,26 h (936 s) ⇐ a cadência do `brief-refresh` (:7,:22,:37,:52)
#   2 únicos intervalos acima de 1 h em 19 dias: 4,24 h e 32,53 h — os dois incidentes
#   na era `active` (>= 2026-09-01T09:00Z): 1 único intervalo acima de 1 h, o de 32,53 h
#
# ⇒ TETO = 3600 s. Dá 3,85x de folga sobre o maior intervalo normal observado e
# tolera 3 rajadas consecutivas perdidas. Com ele, a lacuna de 32,5 h teria sido
# denunciada na primeira hora em vez de descoberta seis dias depois, por acidente,
# ao medir outra coisa. Não usei um teto mais frouxo porque a separação medida
# entre normal (<= 0,26 h) e patológico (>= 4,24 h) é de mais de uma ordem de
# grandeza: qualquer valor em (0,3 h; 4 h) separa as duas populações, e 1 h é o
# ponto dessa faixa que mais cedo denuncia sem tocar em nada normal.
#
# ─── Cinco pernas, e três delas existem porque a perna 4 pode ficar cega ────
#
# 1. `RED log-ausente`        — o arquivo não existe ou não abre.
# 2. `RED sem-registro`       — abre, mas não há nenhum `p2_outcome`.
# 3. `RED ts-no-futuro`       — o último instante está à frente do relógio além da
#    tolerância. Sem esta perna a 4 fica CEGA: idade negativa nunca excede teto.
# 4. `RED serving-parado`     — idade do último registro > teto.
# 5. `RED unidade-incompleta` — o último epoch FECHADO tem contagem != esperado.
#    Não é redundante com a 4: um epoch pode fechar curto sem nunca ter ficado
#    uma hora em silêncio, e a contagem da unidade de randomização é o que a
#    análise consome. O `gatilho-saturacao.sh` carrega `n_janela`, mas só alarma
#    abaixo de n=30 — 441 de 672 passa calado por lá.
#
# As pernas 1, 2 e 3 são o caso "o guarda não tem o dado". Nenhuma delas devolve
# GREEN por ausência de evidência.
#
# READ-ONLY: só lê o ndjson do serving e o relógio. Exit 0 sempre — o estado vive
# na linha, e um exit != 0 faria o cron mandar mail em vez de o painel ver.
set -uo pipefail

SVC="${SVC:-nox-mem-api}"
LOG=""; STATUS=""; NDJSON=""; TETO_S=3600; ESPERADO=672; AGORA=""; TOL_FUTURO_S=120
while [ $# -gt 0 ]; do
  case "$1" in
    --log) LOG="$2"; shift 2;;
    --status) STATUS="$2"; shift 2;;
    --ndjson) NDJSON="$2"; shift 2;;
    --teto-s) TETO_S="$2"; shift 2;;
    --esperado) ESPERADO="$2"; shift 2;;
    --tolerancia-futuro-s) TOL_FUTURO_S="$2"; shift 2;;
    # `--agora` existe para o teste poder construir "faz 40 h que não chega nada"
    # sem esperar 40 h. Em produção fica vazio e o relógio é o do sistema.
    # ⚠️ TODA leitura de tempo deste gatilho passa por esta variável. Um caminho
    # que lesse o relógio por dentro tornaria o teste uma crença sobre o teste.
    --agora) AGORA="$2"; shift 2;;
    --servico) SVC="$2"; shift 2;;
    *) echo "argumento desconhecido: $1" >&2; exit 2;;
  esac
done

# O caminho do log é configuração de PRODUÇÃO: vem do unit do systemd, que é o
# que o serviço realmente usa. Ler do `.env` seria vigiar uma configuração que
# ninguém está servindo — o defeito exato que o item 7 original tinha.
if [ -z "$LOG" ]; then
  LOG="$(systemctl show "$SVC" -p Environment --value 2>/dev/null | tr ' ' '\n' | sed -n 's/^NOX_P2_SERVING_LOG=//p' | tail -1)"
fi
MODO="$(systemctl show "$SVC" -p Environment --value 2>/dev/null | tr ' ' '\n' | sed -n 's/^NOX_P2_OUTCOME=//p' | tail -1)"
[ -n "$AGORA" ] || AGORA="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

emitir() {  # $1=estado $2=resto
  local linha="$1 p2-heartbeat-do-serving $2 ts=$AGORA"
  echo "$linha"
  [ -n "$STATUS" ] && printf '%s\n' "$linha" > "$STATUS"
  if [ -n "$NDJSON" ]; then
    python3 - "$NDJSON" "$1" "$2" "$AGORA" <<'PYND' 2>/dev/null || true
import json, sys
nd, estado, resto, ts = sys.argv[1:5]
try:
    with open(nd, "a") as f:
        f.write(json.dumps({"ts": ts, "tag": "p2_gatilho_heartbeat",
                            "estado": estado, "linha_status": resto}) + "\n")
except Exception:
    pass
PYND
  fi
  exit 0
}

[ -n "$LOG" ] || emitir RED "motivo=log-ausente detalhe=NOX_P2_SERVING_LOG-vazio-no-unit servico=$SVC"
[ -r "$LOG" ] || emitir RED "motivo=log-ausente detalhe=nao-existe-ou-nao-e-legivel log=$LOG"

# O corpo da medição. O predicado do registro é COPIADO do `gatilho-saturacao.sh`
# (`tag == "p2_outcome"`, janela fechada à esquerda e aberta à direita), não
# reconstruído: reconstruir predicado deste ensaio já modelou cinco vezes uma
# regra que o código não aplica.
VEREDITO="$(python3 - "$LOG" "$AGORA" "$TETO_S" "$ESPERADO" "$TOL_FUTURO_S" <<'PY'
import json, sys, datetime as dt

log, agora_s, teto_s, esperado_s, tol_s = sys.argv[1:6]
teto = float(teto_s); esperado = int(esperado_s); tol = float(tol_s)

def P(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))

agora = P(agora_s)

# Fronteira de epoch = 09:00 UTC (`epochInicioISO`, `brief-outcome.ts`). O epoch
# CORRENTE começou hoje às 09:00Z se já passou disso, senão ontem às 09:00Z.
h9 = agora.replace(hour=9, minute=0, second=0, microsecond=0)
ini_corrente = h9 if agora >= h9 else h9 - dt.timedelta(days=1)
ini_fechado = ini_corrente - dt.timedelta(days=1)

ultimo = None
n_corrente = 0
n_fechado = 0
total = 0
for l in open(log, errors="replace"):
    l = l.strip()
    if not l:
        continue
    try:
        d = json.loads(l)
    except Exception:
        continue
    if d.get("tag") != "p2_outcome":
        continue
    ts = d.get("ts", "")
    if not ts:
        continue
    total += 1
    if ultimo is None or ts > ultimo:
        ultimo = ts
    try:
        t = P(ts)
    except Exception:
        continue
    if ini_corrente <= t:
        n_corrente += 1
    elif ini_fechado <= t < ini_corrente:
        n_fechado += 1

def saida(estado, motivo, extra=""):
    print(f"{estado}|motivo={motivo} {extra}".rstrip())
    sys.exit(0)

fech = ini_fechado.strftime("%Y-%m-%d")
janelas = (f"epoch_corrente={ini_corrente.strftime('%Y-%m-%d')} n_corrente={n_corrente} "
           f"epoch_fechado={fech} n_fechado={n_fechado} esperado={esperado} total_no_log={total}")

if total == 0:
    saida("RED", "sem-registro", f"detalhe=log-abre-mas-nao-tem-nenhum-p2_outcome log={log} {janelas}")

idade = (agora - P(ultimo)).total_seconds()

# Perna 3 ANTES da 4, e a ordem é o ponto: com `idade` negativa a perna 4 nunca
# morde, então um instante no futuro (relógio torto, ts escrito errado) cega
# exatamente o alarme mais importante.
if idade < -tol:
    saida("RED", "ts-no-futuro",
          f"detalhe=o-ultimo-registro-esta-a-frente-do-relogio ultimo={ultimo} "
          f"adiantado_s={round(-idade,1)} tolerancia_s={tol} {janelas}")

if idade > teto:
    saida("RED", "serving-parado",
          f"ultimo={ultimo} idade_s={round(idade,1)} idade_h={round(idade/3600,2)} "
          f"teto_s={teto} {janelas} "
          f"ACAO=nenhum brief foi servido desde o ultimo; epoch em curso vira unidade parcial ou perdida")

# Perna 5: a unidade que FECHOU. Só se aplica quando há epoch fechado no log —
# antes do primeiro fechamento a pergunta não existe, e dizer GREEN sobre ela
# seria afirmar sem dado.
if n_fechado != esperado:
    if total > 0 and n_fechado == 0 and n_corrente == total:
        saida("YELLOW", "sem-epoch-fechado-no-log",
              f"semantica=pergunta-nao-se-aplica-ainda ultimo={ultimo} idade_s={round(idade,1)} {janelas}")
    falta = esperado - n_fechado
    quanto = f"faltam={falta}" if falta > 0 else f"excedem={-falta}"
    saida("RED", "unidade-incompleta",
          f"detalhe=o-epoch-que-fechou-nao-tem-a-contagem-esperada {quanto} "
          f"ultimo={ultimo} idade_s={round(idade,1)} {janelas} "
          f"ACAO=dado faltante em unidade de randomizacao; a regra de tratamento tem de estar no DEVIATIONS antes da analise")

saida("GREEN", "serving-vivo-e-unidade-inteira",
      f"ultimo={ultimo} idade_s={round(idade,1)} teto_s={teto} {janelas}")
PY
)"
RC=$?
[ $RC -eq 0 ] && [ -n "$VEREDITO" ] || emitir RED "motivo=medicao-falhou detalhe=python-saiu-rc=$RC-ou-sem-saida log=$LOG"

ESTADO="${VEREDITO%%|*}"
RESTO="${VEREDITO#*|}"
emitir "$ESTADO" "$RESTO modo=${MODO:-vazio} log=$LOG"
