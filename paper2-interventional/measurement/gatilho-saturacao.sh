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
# ─── `--modo active`: a dose NÃO vem mais de uma flag (2026-08-28) ───────────
#
# Em `shadow` a dose é global e vem de `NOX_P2_SHADOW_W`. Em `active` ela é
# **por epoch**, sorteada, e vem do `ASSIGNMENT.json`. Vigiar `active` com a dose
# de shadow reportaria GREEN sobre outra grandeza — pior que não vigiar. Até
# 27/08 o wrapper simplesmente se recusava a rodar em `active`; isto é a
# implementação que a recusa prometia.
#
# Três consequências que o modo `active` força, e que não são detalhe:
#
# 1. **A janela deixa de ser o dia UTC.** O epoch vira às 09:00Z
#    (`epochInicioISO`: `d.getUTCHours() < 9 ? ontem : hoje`), então um dia UTC
#    atravessa DOIS epochs — e portanto, possivelmente, dois braços. A janela
#    passa a ser `[E 09:00Z, E+1 09:00Z)`, e só de epoch JÁ FECHADO.
# 2. **Epoch de controle não tem dose para saturar.** A pergunta é indefinida ali,
#    e responder GREEN sem dizer por quê é o mesmo defeito do guarda que fica
#    calado por não ter o dado. Sai GREEN com `motivo=epoch-de-controle`.
# 3. **`resolverBraco` devolve CONTROLE em toda falha** (`ok:false`) — por desenho,
#    porque enviesa para o nulo em vez de servir tratamento não verificado. Logo
#    "controle no log" é ambíguo: pode ser sorteio, pode ser ASSIGNMENT ilegível.
#    Por isso o gatilho lê o ASSIGNMENT ELE MESMO e **cruza com o log**: braço
#    designado × braço servido, dose designada × dose no log, epoch × epoch.
#    Divergência é RED, e é o alarme mais valioso deste script — é a única coisa
#    aqui que compara o que devia ser servido com o que foi.
#
# Uso:
#   # shadow (dose global, janela = dia UTC anterior):
#   gatilho-saturacao.sh --raiz <nox-mem> --harness <replay-oportunidade.mjs> \
#     --log <p2-serving.ndjson> \
#     --corpus <snapshot.db> --vivo <nox-mem.db> --designacao <json> \
#     --designacao-sha256 <hex> --w-servido 2 \
#     [--inicio ISO --fim ISO] [--status <arq>] [--ndjson <arq>] [--tmp <dir>]
#
#   # active (dose por epoch, janela = último epoch FECHADO):
#   gatilho-saturacao.sh ... --modo active \
#     --assignment <ASSIGNMENT.json> --assignment-sha256 <hex> [--epoch YYYY-MM-DD]
#
# Sem --inicio/--fim: shadow usa o dia UTC anterior INTEIRO [ontem 00:00Z, hoje
# 00:00Z); active usa o último epoch fechado. `--w-servido` e `--assignment` são
# mutuamente exclusivos — passar os dois é erro, não precedência silenciosa.
# Exit 0 sempre; o estado vive na linha, para o cron não virar alarme.

set -uo pipefail

RAIZ=""; HARNESS=""; LOG=""; CORPUS=""; VIVO=""; DESIG=""; DESIG_SHA=""; W_SERV=""
INICIO=""; FIM=""; STATUS=""; NDJSON=""; TMPBASE="/var/tmp"
MODO="shadow"; ASSIGN=""; ASSIGN_SHA=""; EPOCH=""
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
    --modo) MODO="$2"; shift 2;;
    --assignment) ASSIGN="$2"; shift 2;;
    --assignment-sha256) ASSIGN_SHA="$2"; shift 2;;
    --epoch) EPOCH="$2"; shift 2;;
    --inicio) INICIO="$2"; shift 2;;
    --fim) FIM="$2"; shift 2;;
    --status) STATUS="$2"; shift 2;;
    --ndjson) NDJSON="$2"; shift 2;;
    --tmp) TMPBASE="$2"; shift 2;;
    *) echo "argumento desconhecido: $1" >&2; exit 2;;
  esac
done
for v in RAIZ HARNESS LOG CORPUS VIVO DESIG DESIG_SHA; do
  eval "x=\${$v}"
  [ -n "$x" ] || { echo "FALTA --$(echo "$v" | tr 'A-Z_' 'a-z-')" >&2; exit 2; }
done
case "$MODO" in
  shadow)
    [ -n "$W_SERV" ] || { echo "FALTA --w-servido (obrigatório em shadow)" >&2; exit 2; }
    [ -z "$ASSIGN" ] || { echo "--assignment não se aplica a shadow" >&2; exit 2; }
    ;;
  active)
    # Exclusão mútua explícita: se os dois vierem, alguém tem uma crença errada
    # sobre qual manda. Recusar é mais barato que descobrir depois qual venceu.
    [ -z "$W_SERV" ] || { echo "em active a dose vem do ASSIGNMENT; remova --w-servido" >&2; exit 2; }
    [ -n "$ASSIGN" ] || { echo "FALTA --assignment (obrigatório em active)" >&2; exit 2; }
    [ -n "$ASSIGN_SHA" ] || { echo "FALTA --assignment-sha256 (obrigatório em active)" >&2; exit 2; }
    ;;
  *) echo "--modo deve ser shadow ou active (veio: $MODO)" >&2; exit 2;;
esac

# Janela FECHADA. `date -u -d` para não herdar o fuso da máquina: o log é UTC.
# Em `active` os defaults são recalculados abaixo, a partir do epoch — precisam do
# `emitir()`, porque ali a resolução pode falhar e falha tem de virar status.
[ -n "$INICIO" ] || INICIO="$(date -u -d 'yesterday 00:00' +%Y-%m-%dT%H:%M:%SZ)"
[ -n "$FIM" ]    || FIM="$(date -u -d 'today 00:00' +%Y-%m-%dT%H:%M:%SZ)"

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
# `T0` existe porque `TS` é o instante de INÍCIO e o status é escrito no FIM: a
# rodada de 2026-08-27 começou 18:07:30 e gravou 18:22:40 (911 s de replay). Um
# `ts=` sozinho rotula um intervalo de 15 min pelo seu começo — a mesma forma de
# defeito de "série viva citada como instante". Daqui em diante a linha carrega
# início, fim e duração, e a duração é o que avisa que a janela está crescendo
# ANTES de o `timeout` do wrapper matar a rodada e virar RED por capacidade.
T0="$(date -u +%s)"
# `/var/tmp`, nunca `/tmp`: cópia descartável em tmpfs come RAM.
TMP="$(mktemp -d "$TMPBASE/p2-gatilho-saturacao-XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

# Um gatilho morto por SIGTERM/SIGINT (tipicamente o `timeout` do wrapper) fica
# SILENCIOSO — e status ausente é indistinguível de status verde para quem não
# checar frescura. O morning report checa, mas depender disso é deixar a mensagem
# certa para o lugar errado. Aqui o gatilho reporta a própria morte.
morte_por_sinal() {
  local l="RED p2-saturacao-da-dose motivo=interrompido-por-sinal:$1 (provavel timeout do wrapper; a janela pode ter crescido) janela=[$INICIO,$FIM) ts_inicio=$TS ts_fim=$(date -u +%Y-%m-%dT%H:%M:%SZ) duracao_s=$(( $(date -u +%s) - T0 ))"
  echo "$l"
  [ -n "$STATUS" ] && printf '%s\n' "$l" > "$STATUS"
  rm -rf "$TMP"
  exit 0
}
trap 'morte_por_sinal TERM' TERM
trap 'morte_por_sinal INT' INT

emitir() {  # $1=estado $2=resto da linha
  local linha="$1 p2-saturacao-da-dose $2 janela=[$INICIO,$FIM) ts_inicio=$TS ts_fim=$(date -u +%Y-%m-%dT%H:%M:%SZ) duracao_s=$(( $(date -u +%s) - T0 ))"
  echo "$linha"
  [ -n "$STATUS" ] && printf '%s\n' "$linha" > "$STATUS"
  return 0
}

[ -s "$LOG" ] || { emitir YELLOW "motivo=log-de-serving-ausente-ou-vazio log=$LOG"; exit 0; }

# ─── active: epoch, braço e dose vêm do ASSIGNMENT, não de flag ──────────────
ARM=""; EPOCH_ALVO=""
if [ "$MODO" = "active" ]; then
  [ -f "$ASSIGN" ] || { emitir RED "motivo=assignment-nao-existe-no-disco caminho=$ASSIGN"; exit 0; }
  SHA_ASSIGN="$(sha256sum "$ASSIGN" | cut -d' ' -f1)"
  # Mesma disciplina do `resolverBraco`: sha divergente ⇒ recusa. Vigiar a partir
  # de uma sequência não verificada é servir o mesmo defeito que ele evita.
  if [ "$SHA_ASSIGN" != "$ASSIGN_SHA" ]; then
    emitir RED "motivo=assignment-sha256-divergente esperado=${ASSIGN_SHA:0:12} obtido=${SHA_ASSIGN:0:12}"
    exit 0
  fi
  RES="$(python3 - "$ASSIGN" "${EPOCH:-}" <<'PY'
import datetime as dt, json, sys
caminho, epoch_pedido = sys.argv[1], sys.argv[2]
doc = json.load(open(caminho))
linhas = {l["epoch_inicio"]: l for l in doc.get("epochs", [])}
if not linhas:
    print("ERRO|assignment-sem-epochs"); raise SystemExit
agora = dt.datetime.now(dt.timezone.utc)

def janela(e):
    """[E 09:00Z, E+1 09:00Z) — a fronteira do `epochInicioISO` em brief-outcome.ts."""
    d = dt.date.fromisoformat(e)
    ini = dt.datetime.combine(d, dt.time(9, 0), dt.timezone.utc)
    return ini, ini + dt.timedelta(days=1)

if epoch_pedido:
    alvo = epoch_pedido
    if alvo not in linhas:
        print(f"ERRO|epoch-pedido-ausente-do-assignment:{alvo}"); raise SystemExit
else:
    # O ÚLTIMO epoch já FECHADO. Aberto não se mede: a janela ainda cresce, e é
    # exatamente assim que uma série viva vira um número falso.
    fechados = [e for e in sorted(linhas) if janela(e)[1] <= agora]
    if not fechados:
        print("ERRO|nenhum-epoch-fechado-ainda"); raise SystemExit
    alvo = fechados[-1]
l = linhas[alvo]
ini, fim = janela(alvo)
arm = l.get("arm")
w = l.get("w")
if arm not in ("control", "treatment"):
    print(f"ERRO|arm-invalido-no-assignment:{arm!r}"); raise SystemExit
if arm == "treatment" and not (isinstance(w, (int, float)) and w > 0):
    print(f"ERRO|w-invalido-para-tratamento:{w!r}"); raise SystemExit
print("OK|%s|%s|%s|%s|%s" % (alvo, arm, (0 if arm == "control" else w),
                             ini.strftime("%Y-%m-%dT%H:%M:%SZ"),
                             fim.strftime("%Y-%m-%dT%H:%M:%SZ")))
PY
)"
  case "$RES" in
    OK\|*) IFS='|' read -r _ EPOCH_ALVO ARM W_SERV INICIO FIM <<<"$RES" ;;
    *) emitir RED "motivo=assignment-${RES#ERRO|}"; exit 0 ;;
  esac
fi

# Recorte fechado + sha256 do recorte (procedência do item 8).
JAN="$TMP/janela.ndjson"
python3 - "$LOG" "$INICIO" "$FIM" "$JAN" "$TMP/perfil.json" <<'PY'
import json, sys
src, ini, fim, dst, perfil = sys.argv[1:6]
n = 0
# O que o log DIZ que foi servido na janela. Serve à conferência cruzada do modo
# `active`: designado × servido. Conjuntos, não o primeiro valor visto — uma
# janela que atravessa troca de configuração tem de aparecer como duas coisas.
visto = {"modo": set(), "w": set(), "epoch": set(), "servido": set()}
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
            for k in visto:
                visto[k].add(d.get(k))
json.dump({k: sorted(v, key=lambda x: (x is None, str(x))) for k, v in visto.items()},
          open(perfil, "w"))
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

# ─── active: o log concorda com o ASSIGNMENT? ────────────────────────────────
# Este é o alarme mais valioso do script: é a única coisa aqui que compara o que
# DEVIA ser servido com o que FOI. E é necessário porque `resolverBraco` devolve
# controle em toda falha — logo "controle no log" sozinho é ambíguo entre sorteio
# e ASSIGNMENT ilegível, e a segunda hipótese enviesa o estudo para o nulo.
if [ "$MODO" = "active" ]; then
  CRUZ="$(python3 - "$TMP/perfil.json" "$EPOCH_ALVO" "$ARM" "$W_SERV" <<'PY'
import json, sys
p = json.load(open(sys.argv[1]))
epoch, arm, w = sys.argv[2], sys.argv[3], float(sys.argv[4])
def um(k):
    v = p[k]
    return v[0] if len(v) == 1 else None
probs = []
if p["epoch"] != [epoch]:
    probs.append(f'epoch-no-log={p["epoch"]}!=designado:{epoch}')
if p["modo"] != ["active"]:
    probs.append(f'modo-no-log={p["modo"]}!=active')
if arm == "treatment":
    if um("w") is None or float(um("w")) != w:
        probs.append(f'w-no-log={p["w"]}!=designado:{w:g}')
    # `servido` distingue tratamento realmente entregue de degeneração para
    # controle. Um epoch de tratamento em que nada foi servido tratado é o modo
    # de falha que enviesa para o nulo — e é silencioso sem esta linha.
    if "tratado" not in p["servido"]:
        probs.append(f'epoch-de-tratamento-mas-servido={p["servido"]}')
print("|".join(probs))
PY
)"
  if [ -n "$CRUZ" ]; then
    emitir RED "motivo=log-diverge-do-assignment detalhe=$(printf '%s' "$CRUZ" | tr '|' ' ') epoch=$EPOCH_ALVO arm=$ARM w_designado=$W_SERV n_janela=$N_JAN sha256=$SHA_JAN"
    exit 0
  fi
  if [ "$ARM" = "control" ]; then
    # Não há dose, logo não há dose para saturar: a pergunta do item 7(a) é
    # indefinida aqui. GREEN — mas com o motivo escrito, porque GREEN mudo sobre
    # pergunta não feita é indistinguível de GREEN sobre pergunta respondida.
    emitir GREEN "motivo=epoch-de-controle-sem-dose-a-saturar semantica=pergunta-indefinida-nao-verificada epoch=$EPOCH_ALVO arm=control n_janela=$N_JAN sha256=$SHA_JAN"
    exit 0
  fi
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
# Em `active` a linha carrega o epoch e o braço: sem eles, duas linhas de dias
# diferentes são indistinguíveis, e a dose varia POR EPOCH — ler a folga sem saber
# de qual epoch ela é não significa nada.
[ "$MODO" = "active" ] && RESTO="$RESTO modo=active epoch=$EPOCH_ALVO arm=$ARM"
emitir "$EST" "$RESTO"
exit 0
