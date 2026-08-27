#!/usr/bin/env bash
# gatilho-saturacao.sh — item 7(a) do PROTOCOL-CALIBRATION-2026-08-27.
#
# ─── O que este gatilho mede, e por que o registrado não servia ──────────────
#
# O item 7 do protocolo foi registrado assim: dispara "se aparecer gap intragrupo
# acima da magnitude escolhida", calibrado com `0,031808734967844865` e "margem
# 1,35x contra Δ_cut". Medido em 27/08: essa grandeza NÃO cota o mecanismo. O
# maior limiar por estado (`w_min = 4,4`) vale boost 0,0946 em S1 — 1,79x o maior
# passo adjacente do pool inteiro. O designado atravessa VÁRIAS posições até os 2
# slots de cobertura, e a grandeza que governa é distância acumulada, não passo.
# Um gatilho sobre passo adjacente pode ficar VERDE enquanto o canal satura.
#
# A operacionalização correta é uma identidade, não um limiar arbitrário:
#
#     saturado  <=>  churn(w_servido) == churn(w_absurdo)
#
# Se a dose servida já produz tudo que qualquer dose produziria, a dose não está
# identificada — é o modo de falha que o item 7 existe para pegar. E isso custa
# DUAS doses de replay, não 23: não é preciso localizar `w_min`, só comparar as
# duas pontas.
#
# Reporta também a folga: `mexem(servido) / mexem(absurdo)`. Em 27/08 era
# 11/17 = 64,7% — a dose servida usava dois terços da capacidade do canal, o que
# é justamente o regime em que a dose informa.
#
# ─── Três disciplinas herdadas de erro já cometido ──────────────────────────
#
# 1. NÃO sonda `/api/brief` (item 2): o endpoint escreve o estado que mede. Este
#    gatilho lê o log NDJSON de serving e o corpus, e nada mais.
# 2. Janela FECHADA nos dois extremos, com sha256 do recorte (item 8). Uma janela
#    aberta por cima já fez um `11/310` publicado envelhecer para 359.
# 3. Chama a harness canônica `replay-oportunidade.mjs` em vez de reimplementar
#    qualquer pedaço do pipeline — que é a lição inteira de 27/08.
#
# Uso:
#   gatilho-saturacao.sh --raiz <nox-mem> --harness <replay-oportunidade.mjs> \
#     --log <p2-serving.ndjson> \
#     --corpus <snapshot.db> --vivo <nox-mem.db> --designacao <json> \
#     --designacao-sha256 <hex> --w-servido 2 \
#     [--inicio ISO --fim ISO] [--status <arq>] [--ndjson <arq>] [--tmp <dir>]
#
# Sem --inicio/--fim usa o dia UTC anterior INTEIRO: [ontem 00:00Z, hoje 00:00Z).
# Exit 0 sempre; o estado vive na linha, para o cron não virar alarme.

set -uo pipefail

RAIZ=""; HARNESS=""; LOG=""; CORPUS=""; VIVO=""; DESIG=""; DESIG_SHA=""; W_SERV=""
INICIO=""; FIM=""; STATUS=""; NDJSON=""; TMPBASE="/var/tmp"
while [ $# -gt 0 ]; do
  case "$1" in
    --raiz) RAIZ="$2"; shift 2;;
    --harness) HARNESS="$2"; shift 2;;
    --log) LOG="$2"; shift 2;;
    --corpus) CORPUS="$2"; shift 2;;
    --vivo) VIVO="$2"; shift 2;;
    --designacao) DESIG="$2"; shift 2;;
    --designacao-sha256) DESIG_SHA="$2"; shift 2;;
    --w-servido) W_SERV="$2"; shift 2;;
    --inicio) INICIO="$2"; shift 2;;
    --fim) FIM="$2"; shift 2;;
    --status) STATUS="$2"; shift 2;;
    --ndjson) NDJSON="$2"; shift 2;;
    --tmp) TMPBASE="$2"; shift 2;;
    *) echo "argumento desconhecido: $1" >&2; exit 2;;
  esac
done
for v in RAIZ HARNESS LOG CORPUS VIVO DESIG DESIG_SHA W_SERV; do
  eval "x=\${$v}"
  [ -n "$x" ] || { echo "FALTA --$(echo "$v" | tr 'A-Z_' 'a-z-')" >&2; exit 2; }
done

# Janela FECHADA. `date -u -d` para não herdar o fuso da máquina: o log é UTC.
[ -n "$INICIO" ] || INICIO="$(date -u -d 'yesterday 00:00' +%Y-%m-%dT%H:%M:%SZ)"
[ -n "$FIM" ]    || FIM="$(date -u -d 'today 00:00' +%Y-%m-%dT%H:%M:%SZ)"

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
# `/var/tmp`, nunca `/tmp`: cópia descartável em tmpfs come RAM.
TMP="$(mktemp -d "$TMPBASE/p2-gatilho-saturacao-XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

# Um gatilho morto por SIGTERM/SIGINT (tipicamente o `timeout` do wrapper) fica
# SILENCIOSO — e status ausente é indistinguível de status verde para quem não
# checar frescura. O morning report checa, mas depender disso é deixar a mensagem
# certa para o lugar errado. Aqui o gatilho reporta a própria morte.
morte_por_sinal() {
  local l="RED p2-saturacao-da-dose motivo=interrompido-por-sinal:$1 (provavel timeout do wrapper; a janela pode ter crescido) janela=[$INICIO,$FIM) ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "$l"
  [ -n "$STATUS" ] && printf '%s\n' "$l" > "$STATUS"
  rm -rf "$TMP"
  exit 0
}
trap 'morte_por_sinal TERM' TERM
trap 'morte_por_sinal INT' INT

emitir() {  # $1=estado $2=resto da linha
  local linha="$1 p2-saturacao-da-dose $2 janela=[$INICIO,$FIM) ts=$TS"
  echo "$linha"
  [ -n "$STATUS" ] && printf '%s\n' "$linha" > "$STATUS"
  return 0
}

[ -s "$LOG" ] || { emitir YELLOW "motivo=log-de-serving-ausente-ou-vazio log=$LOG"; exit 0; }

# Recorte fechado + sha256 do recorte (procedência do item 8).
JAN="$TMP/janela.ndjson"
python3 - "$LOG" "$INICIO" "$FIM" "$JAN" <<'PY'
import json, sys
src, ini, fim, dst = sys.argv[1:5]
n = 0
with open(dst, "w") as o:
    for l in open(src, errors="replace"):
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
        if ini <= ts < fim:          # FECHADA nos dois extremos
            o.write(l + "\n")
            n += 1
# nada em stdout: a única linha que sai deste gatilho é a de status, para quem
# fizer parse não ter de adivinhar qual linha é o veredito.
print(n, file=sys.stderr)
PY
N_JAN=$(python3 -c "print(sum(1 for _ in open('$JAN')))" 2>/dev/null || echo 0)
SHA_JAN=$(sha256sum "$JAN" | cut -d' ' -f1)

if [ "$N_JAN" -lt 30 ]; then
  emitir YELLOW "motivo=janela-com-n-insuficiente n=$N_JAN minimo=30 sha256=$SHA_JAN"
  exit 0
fi

# Duas doses e só duas: a servida e uma absurda. Ver cabeçalho.
OUT="$TMP/dose.json"
( cd "$TMP" && node "$HARNESS" --modo dose \
    --raiz "$RAIZ" --vivo "$VIVO" --corpus "$CORPUS" \
    --log-campo "$JAN" --excluir-briefs /dev/null \
    --designacao "$DESIG" --designacao-sha256 "$DESIG_SHA" \
    --corte rowid --sem-assert --tmp-base "$TMPBASE" \
    --w "$W_SERV" --w 100000 --out "$OUT" >/dev/null 2>"$TMP/err" ) || true

if [ ! -s "$OUT" ]; then
  emitir RED "motivo=replay-falhou detalhe=$(tr -d '\n' < "$TMP/err" | tail -c 200 | tr '|' '/') sha256=$SHA_JAN"
  exit 0
fi

python3 - "$OUT" "$W_SERV" "$N_JAN" "$SHA_JAN" "${NDJSON:-}" "$TS" "$INICIO" "$FIM" <<'PY' > "$TMP/veredito"
import json, sys
out, wserv, njan, sha, ndjson, ts, ini, fim = sys.argv[1:9]
wserv = float(wserv)
d = json.load(open(out))["dose"]
tab = {r["w"]: r for r in d["tabela"]}
s, a = tab.get(wserv), tab.get(100000.0) or tab.get(100000)
if s is None or a is None:
    print(f'RED|motivo=dose-ausente-na-tabela doses={sorted(tab)} sha256={sha}')
    raise SystemExit
# `saturado` é a identidade, não um limiar: a dose servida já produz tudo.
saturado = s["churn_total"] == a["churn_total"] and s["mexeu"] == a["mexeu"]
inerte = s["mexeu"] == 0
folga = (s["mexeu"] / a["mexeu"]) if a["mexeu"] else None
if a["mexeu"] == 0:
    estado, motivo = "RED", "canal-sem-capacidade: dose absurda nao move nada"
elif inerte:
    estado, motivo = "RED", "dose-servida-inerte: nenhum estado se move"
elif saturado:
    estado, motivo = "RED", "SATURADO: dose servida == dose absurda; a dose nao esta identificada"
elif folga is not None and folga >= 0.9:
    estado, motivo = "YELLOW", "folga<=10%: a dose servida esta perto de saturar"
else:
    estado, motivo = "GREEN", "dose dentro da faixa responsiva"
# `semantica` existe para impedir uma leitura errada previsível: `mexem_servido` NÃO
# é "quantas oportunidades ocorreram na janela". O replay aplica a designação ATUAL
# aos estados de ontem, então é "quantos estados MOVERIAM sob a regra de hoje". Numa
# janela que atravessa uma troca de regra (26/08 atravessa a de 20:28Z), os dois
# números divergem — e um deles seria lido como o outro.
campos = (f'{estado}|motivo={motivo} semantica=contrafactual-sob-a-designacao-ATUAL w_servido={wserv} '
          f'mexem_servido={s["mexeu"]} mexem_absurdo={a["mexeu"]} '
          f'churn_servido={s["churn_total"]} churn_absurdo={a["churn_total"]} '
          f'estados={s["estados"]} folga={"" if folga is None else round(folga,4)} '
          f'n_janela={njan} sha256={sha}')
print(campos)
if ndjson:
    with open(ndjson, "a") as f:
        f.write(json.dumps({
            "ts": ts, "tag": "p2_gatilho_saturacao", "estado": estado, "motivo": motivo,
            "janela": [ini, fim], "n_janela": int(njan), "sha256_janela": sha,
            "w_servido": wserv, "servido": s, "absurdo": a, "folga": folga,
            "semantica": "contrafactual sob a designacao ATUAL, nao taxa historica da janela",
        }) + "\n")
PY

VER="$(cat "$TMP/veredito")"
# Formato do veredito: `ESTADO|resto`. Separador explícito, não heurística de sed —
# extrair estado por regex frouxa é como um gatilho passa a reportar GREEN por
# acidente de formatação.
EST="${VER%%|*}"
RESTO="${VER#*|}"
case "$EST" in GREEN|YELLOW|RED) ;; *) EST=RED; RESTO="motivo=veredito-ilegivel bruto=$(printf '%s' "$VER" | tr -d '\n' | tail -c 120)";; esac
emitir "$EST" "$RESTO"
exit 0
