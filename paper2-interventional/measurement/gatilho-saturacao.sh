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
# ─── (a) IDENTIDADE DO CORPUS — o cabeçalho do wrapper promete que a aproximação
#     "fica em cada linha do NDJSON em vez de silenciosa", e até 2026-09-09 ela NÃO
#     ficava: os 13 campos do recibo não traziam nada de corpus. Consequência medida
#     nesse dia: duas corridas com `sha256_janela` IDÊNTICO, `estados=672` idêntico,
#     mesma janela e mesmo epoch produziram GREEN 20/37 e RED 0/0 — vereditos opostos
#     com recibos indistinguíveis. Isto cumpre a promessa que já estava escrita.
#
#     É o SHA DOS BYTES, não o caminho: `current.db` é symlink e às 06:02 aponta para
#     outros bytes sem que arquivo nenhum mude. Em 2026-09-09 ele era `084bef6c…`.
FD_PREFIX="${FD_PREFIX:-/var/lib/nox-mem/epochs/}"
# `readlink -f` serve ao RÓTULO; o hash lê o ARGUMENTO. Achado 09/09 ao medir o
# instrumento contra um fd deletado: `readlink -f /proc/PID/fd/N` devolve o nome
# original com o sufixo — `/…/orig.db (deleted)` — e esse caminho NÃO existe, então
# hashear o resultado dá `nao-calculado` enquanto o argumento é perfeitamente
# legível. Para `current.db` (symlink comum) os dois são idênticos; a diferença só
# aparece no caso que o instrumento existe para cobrir. Hashear o argumento é
# estritamente melhor: se ele resolve, ler dele lê o alvo.
CORPUS_REAL="$(readlink -f "$CORPUS" 2>/dev/null || printf '%s' "$CORPUS")"
CORPUS_SHA="$(sha256sum "$CORPUS" 2>/dev/null | cut -d' ' -f1)"
[ -n "$CORPUS_SHA" ] || CORPUS_SHA="nao-calculado"

# ─── (b) A APROXIMAÇÃO É VÁLIDA HOJE? — o cabeçalho do wrapper diz "inerte não é
#     garantido", e não havia nada medindo quando deixou de ser. O serving resolve
#     `current.db` UMA vez, no open(); desde 2026-09-03 17:30 ele lê um inode já
#     podado do disco (§10.10) enquanto o symlink seguiu relinkando. Compara-se por
#     BYTES, não por caminho: o corpus recuperado tem caminho diferente do fd e é
#     byte-idêntico a ele.
#     O prefixo é PARÂMETRO com default de produção: sem isso a perna só poderia
#     ser exercitada escrevendo arquivo de teste dentro de `/var/lib/nox-mem/epochs/`,
#     que é o diretório do ensaio em curso. Um teste que precisa sujar produção para
#     rodar não roda — e perna não exercitada é crença, não guarda.
#     ⚠️ TODOS os fds, não o primeiro. A primeira versão desta perna (implantada e
#     revista no mesmo dia, 09/09) fazia `head -1` sobre `ls -l /proc/PID/fd`, e
#     `ls` ali ordena LEXICOGRAFICAMENTE — `10` vem antes de `2`, medido na VPS. Com
#     os fds 26 e 9 abertos, `head -1` pega o 26: escolha arbitrária e não
#     declarada. Pior, o cenário de N fds não é hipotético — foi o acúmulo de
#     snapshot por epoch sem fechar o velho que produziu o §10.10. Um
#     `serving_fd_sha256` singular sobre N fds seria número certo atribuído a
#     população errada. Então: coleta todos, ordena por número de fd, e a
#     aproximação vale se o corpus está ENTRE os que o serving tem abertos.
SERV_PID="$(systemctl show -p MainPID --value nox-mem-api 2>/dev/null)"
SERV_SHAS=""; SERV_N=0
case "$SERV_PID" in
  ''|0|*[!0-9]*) SERV_SHAS="sem-pid" ;;
  *)
    # `\.db` é obrigatório: o diretório dos epochs tem 4 `.db` e 17 `.json`
    # (manifests). Sem o sufixo, `[^ ]+` guloso casaria um manifest e a perna
    # compararia coisas de tipos diferentes, reportando divergência.
    #
    # ⚠️ ` (deleted)` OPCIONAL, e é o caso que importa: desde 03/09 17:30 o fd que
    # o serving mantém aberto é justamente de um inode apagado, e `ls -l` o
    # anota com esse sufixo. Ancorar `$` logo depois de `.db` — que foi o que eu
    # escrevi na primeira tentativa — excluiria exatamente o único fd que a perna
    # existe para enxergar. A versão anterior com `grep -oE` não ancorava e por
    # isso não tinha o problema; trocar de ferramenta trouxe o defeito de volta.
    while read -r n alvo; do
      [ -n "$n" ] || continue
      s="$(sha256sum "/proc/$SERV_PID/fd/$n" 2>/dev/null | cut -d' ' -f1)"
      [ -n "$s" ] || s="fd-$n-nao-lido"
      SERV_SHAS="${SERV_SHAS:+$SERV_SHAS,}$s"
      SERV_N=$((SERV_N + 1))
    done <<EOFFD
$(ls -l "/proc/$SERV_PID/fd" 2>/dev/null \
  | sed -nE "s#^.* ([0-9]+) -> (${FD_PREFIX}[^ ]+\.db)( \(deleted\))?\$#\1 \2#p" | sort -n)
EOFFD
    [ "$SERV_N" -gt 0 ] || SERV_SHAS="fd-nao-lido"
    ;;
esac

# ⚠️ ORDEM DAS PERNAS: a de "não li o corpus" vem PRIMEIRO. Achada pela sessão par
# horas depois do deploy: sem ela, corpus ilegível (`sha256sum` falha ⇒
# `nao-calculado`) com serving vivo caía no `else` e o recibo AFIRMAVA
# `aproximacao_valida=nao` — afirmação positiva de divergência sem ter lido um dos
# dois operandos. Não é o silêncio da regra 9 do CLAUDE.md; é o agravante dela. E o
# cenário é banal: `current.db` relinkado às 06:02 para arquivo ainda não criado.
# Simétrica à regra do serving: sem corpus lido dá `indeterminada`, nunca `nao`.
if [ "$CORPUS_SHA" = "nao-calculado" ]; then APROX="indeterminada"
elif [ "$SERV_SHAS" = "sem-pid" ] || [ "$SERV_SHAS" = "fd-nao-lido" ]; then APROX="indeterminada"
elif printf '%s' ",$SERV_SHAS," | grep -qF ",$CORPUS_SHA,"; then APROX="sim"
else APROX="nao"; fi

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

# ─── Registro estruturado dos vereditos que NÃO passam pelo bloco de dose ────
#
# Achado em 2026-09-08 (§10.8 do DEVIATIONS-FOR-PAPER.md): `emitir()` gravava
# `stdout` e o arquivo de `--status`, e NUNCA o `--ndjson`. Só o caminho normal
# persistia linha, porque quem gravava era o bloco `python3` do veredito. Logo
# todo veredito por atalho — `log-de-serving-ausente`, `assignment-*`,
# `janela-com-n-insuficiente`, `log-diverge-do-assignment`, `epoch-de-controle`,
# `replay-falhou`, `dose-ausente-na-tabela`, `interrompido-por-sinal` — ficava
# APENAS no arquivo de status, que a execução seguinte SOBRESCREVE. É perda
# permanente, não atraso: medido, 12 execuções no log de texto contra 9 linhas
# `p2_gatilho_saturacao` no NDJSON, e nenhuma linha de 09-07 nem de 09-08.
#
# E entre os motivos que só existiam no log de texto estava
# `log-diverge-do-assignment` — o que o cabeçalho deste arquivo chama de "o
# alarme mais valioso deste script … a única coisa aqui que compara o que devia
# ser servido com o que foi". O mais valioso era o que não deixava rastro
# analisável.
#
# ⚠️ Duas disciplinas de construção:
#
# 1. **Sentinela, não contagem de linhas.** A escrita dupla no caminho normal é
#    impedida por um arquivo em `$TMP` que o bloco de veredito cria DEPOIS de
#    gravar. Comparar a contagem de linhas antes/depois seria frágil: o
#    `gatilho-composicao.mjs` escreve no MESMO NDJSON a cada hora, e uma rodada
#    de saturação leva ~15 min — a linha de outro gatilho entraria no meio e
#    seria lida como "já gravei".
# 2. **O registro de atalho NÃO finge ter os campos do veredito.** `servido`,
#    `absurdo` e `folga` só existem se o bloco de dose rodou; aqui saem `null`,
#    com `via: "atalho"` dizendo por quê. Preencher com zero fabricaria
#    `mexeu = 0`, isto é `dose-servida-inerte` — exatamente o veredito errado que
#    o §10.4 documenta ter custado dois dias de RED com o motivo trocado.
gravar_ndjson_atalho() {  # $1=estado $2=resto da linha
  [ -n "$NDJSON" ] || return 0
  [ -e "$TMP/.ndjson-gravado" ] && return 0
  python3 - "$NDJSON" "$1" "$2" "$TS" "$INICIO" "$FIM" "$MODO" "${EPOCH_ALVO:-}" "${ARM:-}" \
    "${CORPUS_REAL:-$CORPUS}" "${CORPUS_SHA:-?}" "${APROX:-indeterminada}" "${SERV_SHAS:-?}" "${SERV_N:-0}" <<'PYND' 2>/dev/null || true
import json, re, sys
nd, estado, resto, ts, ini, fim, modo, epoch, arm, cpath, csha, aprox, sshas, sn = sys.argv[1:15]
m = re.match(r'motivo=(.*?)(?=\s+[a-z_0-9]+=|$)', resto)
try:
    with open(nd, "a") as f:
        f.write(json.dumps({
            "ts": ts, "tag": "p2_gatilho_saturacao", "estado": estado,
            "motivo": m.group(1) if m else None,
            "janela": [ini or None, fim or None],
            "modo": modo, "epoch": epoch or None, "arm": arm or None,
            "corpus_path": cpath or None, "corpus_sha256": csha,
            "aproximacao_valida": aprox,
            "serving_fd_sha256s": sshas.split(",") if sshas not in ("sem-pid", "fd-nao-lido", "?") else sshas,
            "serving_fd_n": int(sn),
            "servido": None, "absurdo": None, "folga": None,
            "via": "atalho",
            "nota": "veredito por atalho: o bloco de dose nao rodou, logo servido/absurdo/folga nao existem",
            "linha_status": resto,
        }, ensure_ascii=False) + "\n")
except Exception:
    pass
PYND
  return 0
}


# Um gatilho morto por SIGTERM/SIGINT (tipicamente o `timeout` do wrapper) fica
# SILENCIOSO — e status ausente é indistinguível de status verde para quem não
# checar frescura. O morning report checa, mas depender disso é deixar a mensagem
# certa para o lugar errado. Aqui o gatilho reporta a própria morte.
morte_por_sinal() {
  local l="RED p2-saturacao-da-dose motivo=interrompido-por-sinal:$1 (provavel timeout do wrapper; a janela pode ter crescido) janela=[$INICIO,$FIM) ts_inicio=$TS ts_fim=$(date -u +%Y-%m-%dT%H:%M:%SZ) duracao_s=$(( $(date -u +%s) - T0 ))"
  echo "$l"
  [ -n "$STATUS" ] && printf '%s\n' "$l" > "$STATUS"
  # Antes do `rm -rf`: a sentinela e o NDJSON de atalho vivem em $TMP.
  gravar_ndjson_atalho RED "motivo=interrompido-por-sinal:$1"
  rm -rf "$TMP"
  exit 0
}
trap 'morte_por_sinal TERM' TERM
trap 'morte_por_sinal INT' INT

emitir() {  # $1=estado $2=resto da linha
  local linha="$1 p2-saturacao-da-dose $2 janela=[$INICIO,$FIM) corpus=$(basename "${CORPUS_REAL:-$CORPUS}") corpus_sha256=$(printf '%.12s' "${CORPUS_SHA:-?}") aproximacao_valida=${APROX:-indeterminada} serving_fd_n=${SERV_N:-0} ts_inicio=$TS ts_fim=$(date -u +%Y-%m-%dT%H:%M:%SZ) duracao_s=$(( $(date -u +%s) - T0 ))"
  echo "$linha"
  [ -n "$STATUS" ] && printf '%s\n' "$linha" > "$STATUS"
  gravar_ndjson_atalho "$1" "$2"
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

python3 - "$OUT" "$W_SERV" "$N_JAN" "$SHA_JAN" "${NDJSON:-}" "$TS" "$INICIO" "$FIM" "$TMP" \
  "${CORPUS_REAL:-$CORPUS}" "${CORPUS_SHA:-?}" "${APROX:-indeterminada}" "${SERV_SHAS:-?}" "${SERV_N:-0}" <<'PY' > "$TMP/veredito"
import json, sys
out, wserv, njan, sha, ndjson, ts, ini, fim, tmpdir, cpath, csha, aprox, sshas, sn = sys.argv[1:15]
wserv = float(wserv)
d = json.load(open(out))["dose"]
tab = {r["w"]: r for r in d["tabela"]}
s, a = tab.get(wserv), tab.get(100000.0) or tab.get(100000)
if s is None or a is None:
    print(f'RED|motivo=dose-ausente-na-tabela doses={sorted(tab)} sha256={sha}')
    raise SystemExit
# ─── O replay respondeu sobre a janela INTEIRA? ──────────────────────────────
# Perna acrescentada em 2026-09-06. Este gatilho carregava `n_janela` e `estados`
# lado a lado na própria linha de status e NENHUM predicado os comparava — e foi
# por isso que dois dias de RED saíram com o motivo errado. Não é a família
# "guarda calado por não ter o dado" (regra 9 do CLAUDE.md): é o agravante dela,
# guarda que TEM o dado e não pergunta.
#
# Um brief que o replay não consegue localizar vira `erro` e sai da população
# ANTES do laço de doses, então `mexeu` passa a ser medido sobre os
# sobreviventes. O defeito que motivou esta perna descartava precisamente os
# briefs em que a dose mordeu (§10.4 do DEVIATIONS-FOR-PAPER.md), o que torna o
# viés anticorrelacionado com o efeito: perda silenciosa aqui empurra o veredito
# para "inerte". Por isso vem ANTES de `inerte` — inércia é o sintoma.
# ⚠️ O predicado é `!=`, não `<`, e isto é deliberado. Um replay que afirma ter
# respondido MAIS estados do que a janela tem também é incoerente, e não é
# hipotético: o stub do `teste-gatilho-active.sh` devolvia `estados: 672` fixo
# sobre janelas de 40 registros, e foi esta perna que o pegou (2 dos 9 casos
# existentes falharam ao ela entrar — o stub mentia, a perna estava certa).
# Trocar por `<` cegaria justamente essa direção. Em produção o excesso é
# latente: `briefs` é filtrado por `ids_controle.length === 10`, subconjunto dos
# `p2_outcome` que o `n_janela` conta, logo `estados <= n_janela`.
njan_i = int(njan)
faltantes = njan_i - s["estados"]
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

# ─── Janela incompleta: ALARMA e PRESERVA o veredito ─────────────────────────
#
# ⚠️ CAUSA DO `faltam=1` — MEDIDA 2026-09-09, e NÃO é o que este comentário dizia
# antes ("escrita incompleta no brief_log, 1 linha de 10"). O brief tem as DEZ
# linhas. O que se espalha é o `served_at` delas:
#
#     647955 | 2026-09-06 23:07:02 | 116467      <- 1 linha
#     647956 | 2026-09-06 23:07:09 | 112241      <- e 9 linhas SETE SEGUNDOS depois
#     ...
#
# `idDoBrief()` em `replay-oportunidade.mjs` casa por
# `served_at IN (t, t+1s, t+2s)`; as nove de `:09` ficam fora, o `GROUP_CONCAT`
# devolve UM id, não casa com os 10 do ndjson, e `cands.length === 0` ⇒ descarte.
# "1 linha de 10" é o que se VÊ de dentro da janela de 3 s — sintoma lido como causa.
#
# Span por brief na janela de 09-06: 670 com span 0 s, 1 com 1 s, **1 com 7 s**.
# ⇒ Esta perna descarta briefs LENTOS, não briefs aleatórios. Latência de escrita
# não é independente de carga, logo o descarte é potencialmente CORRELACIONADO ao
# que se mede. Com n=1 e `churn=0` o dano neste epoch é nulo; a CLASSE é o problema,
# e é a mesma do `estados=640` (`672 − 32`): regra que EXCLUI em vez de atribuir.
#
# Não é conserto de casar por `brief_id`: o `p2_outcome` do ndjson não tem esse
# campo (medido: 0/672). Ver §10.12 do DEVIATIONS-FOR-PAPER.md.
# A primeira versão desta perna (2026-09-06) abortava aqui, e no dia seguinte isso
# custou caro: UM brief descartado pelo replay (`ts=2026-09-06T23:07:02.425Z`)
# suprimiu um veredito substantivo — no epoch 09-06,
# `w=7,5` e `w=100000` deram resultado IDÊNTICO (`mexeu=38`, `churn_total=44`), isto
# é `saturado`, na dose mais alta do desenho.
#
# A lição que motivou a perna era "não medir sobre população reduzida EM SILÊNCIO",
# não "nunca medir". Com a redução declarada e quantificada, o veredito é
# utilizável — e jogá-lo fora por 1 em 672 transforma o guarda em ruído que suprime
# sinal. Então: o estado continua RED (o morning report tem de ver), e o veredito de
# dose viaja junto, com a população sobre a qual foi computado explícita.
#
# ⚠️ A comparação é `!= 0`, não `> 0`, e isto é deliberado: um replay que afirma ter
# respondido MAIS estados do que a janela tem também é incoerente, e não é
# hipotético — o stub do `teste-gatilho-active.sh` devolvia `estados: 672` fixo sobre
# janelas de 40 registros, e foi esta perna que o pegou. Em produção o excesso é
# latente, porque `briefs` é filtrado por `ids_controle.length === 10`, subconjunto
# dos `p2_outcome` que o `n_janela` conta.
if faltantes != 0:
    quanto = f"faltam={faltantes}" if faltantes > 0 else f"excedem={-faltantes}"
    motivo = (f'erros-no-replay: a janela nao foi respondida inteira {quanto}; '
              f'veredito_dose={estado}:{motivo} '
              f'populacao_do_veredito={s["estados"]}/{njan_i}')
    estado = "RED"
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
            "corpus_path": cpath, "corpus_sha256": csha,
            "aproximacao_valida": aprox,
            "serving_fd_sha256s": sshas.split(",") if sshas not in ("sem-pid", "fd-nao-lido", "?") else sshas,
            "serving_fd_n": int(sn),
            "w_servido": wserv, "servido": s, "absurdo": a, "folga": folga,
            "semantica": "contrafactual sob a designacao ATUAL, nao taxa historica da janela",
            "via": "veredito-de-dose",
        }) + "\n")
    # Sentinela: `emitir()` grava o NDJSON de ATALHO, e sem isto o caminho normal
    # sairia duas vezes — uma estruturada, uma com `servido: null`.
    open(tmpdir + "/.ndjson-gravado", "w").close()
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
