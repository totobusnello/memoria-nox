#!/usr/bin/env bash
# gatilho-coorte.sh — o canal está ALCANÇÁVEL neste epoch, ou há uma coorte
#                     nunca-servida na frente dele?
#
# ─── Por que existe (2026-09-09) ────────────────────────────────────────────
#
# O `gatilho-saturacao.sh` responde "a dose morde?" rodando o replay: 931 s
# medidos. Mas em 09/09 ele devolveu `mexem_absurdo = 0` e o veredito
# `"canal-sem-capacidade: dose absurda nao move nada"` — verdadeiro no número e
# ERRADO na causa. A causa, medida no mesmo dia:
#
#   `memory/lessons.md` foi reingerido em 07/09 ⇒ 60 chunks novos, e os 60 têm
#   `last_served` NULL (nunca servidos) contra 19/19 designados JÁ servidos. O
#   comparador de cobertura é lexicográfico em `(last_served, −salience)` e o
#   boost do ensaio é ADITIVO ⇒ só desempata DENTRO de um estrato. 60
#   nunca-servidos disputando `freshSlots = 2` ⇒ nenhum `w` promove designado.
#   Nem 100.000.
#
# ⇒ "dose absurda não move nada" e "não existe canal" NÃO são a mesma coisa. A
#   segunda é uma propriedade do mecanismo; a primeira pode ser só o estado do
#   estrato. Este guarda separa as duas, e separa em UMA CONSULTA em vez de um
#   replay — porque a distinção não precisa de contrafactual, precisa de
#   `last_served`.
#
# ─── Por que a perna de PERSISTÊNCIA conta tráfego, não parede ──────────────
#
# 🔴 Esta é a perna que o meu próprio caso de 09/09 exige, e a versão ingênua
# erra o motivo. Precedente medido: a coorte de `lessons.md` de 22/08 (53
# chunks) estreou entre 19:23:13 e 20:37:18 — 1,2 h, com produção normal — e
# depois dela o canal VOLTOU a responder (série GREEN de 27/08 a 01/09, `mexeu`
# 25/15/11/30/20/11). Chegada, bloqueio, dreno e recuperação, todos no registro.
# Logo bloqueio por reingestão é TRANSITÓRIO e não deve gerar RED.
#
# Mas os 60 de 07/09 estão NULL há DOIS DIAS — e isso não é bloqueio estrutural:
# eles estão AUSENTES do corpus que o serving tem aberto (0 de 60), e nada drena
# de um corpus que não é servido. Zero estreias em todo o `brief_log` desde
# 26/08, com 141 chunks distintos girando por dia.
#
# ⇒ Um guarda que medisse "horas desde a chegada" chamaria o caso de hoje de
#   estrutural, pelo motivo errado. O denominador certo é OPORTUNIDADE DE SLOT
#   servida do corpus que contém a coorte — e a primeira pergunta não é
#   "quanto tempo", é "a coorte é alcançável?".
#
# ─── Pernas, nesta ordem ────────────────────────────────────────────────────
#
#   1. corpus-ilegivel      YELLOW  não dá para responder
#   2. vivo-ilegivel        YELLOW  idem (brief_log vive no banco vivo)
#   3. canal-alcancavel     GREEN   nunca-servidos < freshSlots
#   4. serving-indeterminado YELLOW não deu para ler o fd do serving
#   5. coorte-inalcancavel  RED     coorte não está no corpus ABERTO pelo
#                                   serving ⇒ não pode drenar, e o corpus
#                                   analisado não é o que serve (§10.13)
#   6. bloqueio-de-reingestao YELLOW coorte alcançável, orçamento de dreno
#                                   ainda não gasto ⇒ transitório esperado
#   7. bloqueio-estrutural  RED     alcançável, orçamento gasto e ainda NULL
#
# A perna 4 vem ANTES da 5 pela mesma razão que `ts-no-futuro` vem antes de
# `serving-parado` no heartbeat: sem o dado do serving, a 5 responderia "não
# está no corpus aberto" quando o que houve foi não ter lido corpus aberto
# nenhum — afirmação positiva sobre dado ausente, que é o agravante da regra 9
# do CLAUDE.md e o defeito M6 que achei no gatilho de saturação hoje.
#
# ⚠️ RELÓGIO: a janela de elegibilidade em produção é `julianday('now')` — tempo
# de PAREDE, lido dentro do SQLite (defeito documentado, `brief.ts:645`). Aqui
# o predicado usa `--agora` (default: agora) como o mesmo lado da subtração,
# então casa com produção quando não injetado e fica testável quando injetado.
#
# ⚠️ Não substitui o `gatilho-saturacao.sh`: ele mede se a dose morde, este mede
# se ela TEM COMO morder. GREEN aqui com RED lá é informação, não contradição.
set -uo pipefail

CORPUS=""; VIVO=""; STATUS=""; NDJSON=""; AGORA=""
FRESH_SLOTS=2; JANELA_D=30; PISO_IMP=0.7; PISO_PAIN=0.7
ORCAMENTO_OP=10
FD_PREFIX="${FD_PREFIX:-/var/lib/nox-mem/epochs/}"
SERVICO="nox-mem-api"

while [ $# -gt 0 ]; do
  case "$1" in
    --corpus) CORPUS="$2"; shift 2;;
    --vivo) VIVO="$2"; shift 2;;
    --status) STATUS="$2"; shift 2;;
    --ndjson) NDJSON="$2"; shift 2;;
    --agora) AGORA="$2"; shift 2;;
    --fresh-slots) FRESH_SLOTS="$2"; shift 2;;
    --janela-global-d) JANELA_D="$2"; shift 2;;
    --piso-imp) PISO_IMP="$2"; shift 2;;
    --piso-pain) PISO_PAIN="$2"; shift 2;;
    --orcamento-op) ORCAMENTO_OP="$2"; shift 2;;
    --fd-prefix) FD_PREFIX="$2"; shift 2;;
    --servico) SERVICO="$2"; shift 2;;
    *) echo "argumento desconhecido: $1" >&2; exit 2;;
  esac
done
[ -n "$CORPUS" ] || { echo "FALTA --corpus" >&2; exit 2; }
[ -n "$VIVO" ]   || { echo "FALTA --vivo" >&2; exit 2; }
[ -n "$AGORA" ]  || AGORA="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

emitir() {  # $1=estado $2=resto
  local linha="$1 p2-coorte-nunca-servida $2 ts=$AGORA"
  echo "$linha"
  [ -n "$STATUS" ] && printf '%s\n' "$linha" > "$STATUS"
  if [ -n "$NDJSON" ]; then
    python3 - "$NDJSON" "$1" "$2" "$AGORA" <<'PYND' 2>/dev/null || true
import json, sys
nd, estado, resto, ts = sys.argv[1:5]
try:
    with open(nd, "a") as f:
        f.write(json.dumps({"ts": ts, "tag": "p2_gatilho_coorte",
                            "estado": estado, "linha_status": resto}) + "\n")
except Exception:
    pass
PYND
  fi
  exit 0
}

# ─── Qual corpus o serving tem ABERTO? Por BYTES, nunca por caminho: o corpus
#     recuperado de 03/09 tem caminho diferente do fd e é byte-idêntico a ele.
#     Coleta TODOS os fds que casam o prefixo (o §10.10 nasceu de fd acumulado,
#     e "o primeiro" é arbitrário: `ls /proc/PID/fd` ordena LEXICOGRAFICAMENTE
#     — medido, `0 1 10 11 12 13`, o 10 antes do 2).
SERV_ABERTOS=""; SERV_N=0; SERV_ERRO=""
SERV_PID="$(systemctl show -p MainPID --value "$SERVICO" 2>/dev/null)"
case "$SERV_PID" in
  ''|0|*[!0-9]*) SERV_ERRO="sem-pid" ;;
  *)
    # 🔴 Coleta o NÚMERO do fd, não o caminho — e é o defeito que a própria
    # suíte pegou (T9). O caso que este guarda existe para cobrir é o corpus
    # DELETADO vivo só pelo fd (§10.10): ali o caminho que o `ls -l` mostra
    # NÃO EXISTE MAIS no disco, e abrir por caminho devolve zero. Só
    # `/proc/PID/fd/N` alcança o inode. Fixture com arquivo apagado de verdade
    # é o que expôs isso; `ls` stubado teria passado.
    #
    # ` (deleted)` é OPCIONAL no fim: ancorar `$` logo depois de `\.db`
    # excluiria exatamente o fd deletado.
    SERV_ABERTOS="$(ls -l "/proc/$SERV_PID/fd" 2>/dev/null \
      | sed -nE "s#^.* ([0-9]+) -> ${FD_PREFIX}[^ ]+\.db( \(deleted\))?\$#\1#p" \
      | sort -n -u)"
    if [ -z "$SERV_ABERTOS" ]; then
      SERV_ERRO="nenhum-fd-no-prefixo"
    else
      SERV_N="$(printf '%s\n' "$SERV_ABERTOS" | grep -c .)"
    fi
    ;;
esac

python3 - "$CORPUS" "$VIVO" "$AGORA" "$FRESH_SLOTS" "$JANELA_D" "$PISO_IMP" \
         "$PISO_PAIN" "$ORCAMENTO_OP" "$SERV_ERRO" "$SERV_PID" <<'PY' > /tmp/.coorte.$$ 2>/dev/null
import json, sqlite3, sys
(corpus, vivo, agora, fslots, janela, pimp, ppain, orc, serverro, servpid) = sys.argv[1:11]
fslots = int(fslots); janela = float(janela); orc = float(orc)
inst = agora.replace("T", " ").replace("Z", "")

def ro(p):
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True)

def falha(motivo, extra=""):
    print(json.dumps({"perna": motivo, "extra": extra})); sys.exit(0)

try:
    c = ro(corpus)
    c.execute("SELECT 1 FROM chunks LIMIT 1").fetchone()
except Exception as e:
    falha("corpus-ilegivel", str(e)[:120])
try:
    v = ro(vivo)
    v.execute("SELECT 1 FROM brief_log LIMIT 1").fetchone()
except Exception as e:
    falha("vivo-ilegivel", str(e)[:120])

# Pool GLOBAL de freshness, predicado LITERAL do fetchFreshCandidates
# (serving-brief.ts:636-645, com o override de :809 trocando freshMaxAgeDays
# por freshGlobalMaxAgeDays no sub-pool global).
pool = c.execute("""
  SELECT id, COALESCE(source_date, created_at) AS dt FROM chunks
   WHERE (source_file LIKE 'memory/entities/%' OR source_file LIKE 'memory/lessons.md')
     AND (COALESCE(importance,0) >= ? OR COALESCE(pain,0) >= ?)
     AND julianday(?) - julianday(COALESCE(source_date, created_at)) <= ?
""", (float(pimp), float(ppain), inst, janela)).fetchall()
ids = [r[0] for r in pool]
if not ids:
    falha("pool-vazio", "0 chunks elegiveis no globalFresh")

servidos = set()
CH = 500
for i in range(0, len(ids), CH):
    lote = ids[i:i + CH]
    q = ",".join("?" * len(lote))
    for (cid,) in v.execute(
            f"SELECT DISTINCT chunk_id FROM brief_log WHERE chunk_id IN ({q})", lote):
        servidos.add(cid)
nunca = [r for r in pool if r[0] not in servidos]
out = {"pool": len(ids), "nunca": len(nunca), "fslots": fslots,
       "serv_erro": serverro, "serv_pid": servpid}
if len(nunca) < fslots:
    out["perna"] = "canal-alcancavel"
    print(json.dumps(out)); sys.exit(0)

# A coorte chegou quando? Menor dt entre os nunca-servidos.
chegada = min(r[1] for r in nunca)
out["chegada"] = chegada
out["coorte"] = len(nunca)
# Oportunidades de slot GASTAS desde a chegada = briefs distintos servidos x freshSlots.
briefs = v.execute(
    "SELECT COUNT(DISTINCT brief_id) FROM brief_log WHERE served_at >= ?",
    (chegada,)).fetchone()[0] or 0
out["briefs_desde_chegada"] = briefs
out["oportunidades"] = briefs * fslots
out["orcamento"] = int(len(nunca) * orc)
out["ids_coorte_amostra"] = [r[0] for r in nunca[:5]]
print(json.dumps(out))
PY
J="$(cat /tmp/.coorte.$$ 2>/dev/null)"; rm -f /tmp/.coorte.$$
[ -n "$J" ] || emitir YELLOW "motivo=consulta-falhou detalhe=python-sem-saida corpus=$(basename "$CORPUS")"

le() { printf '%s' "$J" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get(sys.argv[1],''))" "$1" 2>/dev/null; }
PERNA="$(le perna)"; POOL="$(le pool)"; NUNCA="$(le nunca)"
BASE="corpus=$(basename "$CORPUS") pool_global=$POOL nunca_servidos=$NUNCA fresh_slots=$FRESH_SLOTS"

case "$PERNA" in
  corpus-ilegivel|vivo-ilegivel|pool-vazio)
    # `basename` de um caminho /proc/PID/fd/N é só o número, inútil num guarda
    # de proveniência — nesta perna vale o argumento inteiro.
    emitir YELLOW "motivo=$PERNA detalhe=$(le extra) corpus=$CORPUS" ;;
  canal-alcancavel)
    emitir GREEN "motivo=canal-alcancavel semantica=nunca-servidos-abaixo-dos-slots-logo-a-dose-tem-como-morder $BASE" ;;
esac

COORTE="$(le coorte)"; CHEGADA="$(le chegada)"
OPS="$(le oportunidades)"; ORC_V="$(le orcamento)"; BR="$(le briefs_desde_chegada)"
AMOSTRA="$(le ids_coorte_amostra | tr -d ' []')"
BASE="$BASE coorte=$COORTE chegada=$CHEGADA ids_amostra=$AMOSTRA"

# ─── Perna 4: sem o dado do serving, NÃO afirmar sobre alcançabilidade.
if [ -n "$SERV_ERRO" ]; then
  emitir YELLOW "motivo=serving-indeterminado detalhe=$SERV_ERRO semantica=ausencia-de-dado-nao-e-alcancabilidade $BASE"
fi

# ─── Perna 5: o corpus ANALISADO é, byte a byte, um dos que o serving tem
#     aberto? Comparação por SHA, não por consulta de conteúdo.
#
# 🔴 Por que por bytes e não por `SELECT`: medido em 2026-09-09, o **SQLite não
# consegue abrir banco por `/proc/PID/fd/N`** — `mode=ro` e `mode=ro&immutable=1`
# falham os dois com "unable to open database file", enquanto `sha256sum` no
# mesmo caminho lê sem erro. Ou seja: o conteúdo do corpus deletado é
# inalcançável por query sem copiar o arquivo inteiro (1,2 GB), o que um guarda
# que roda por hora não pode fazer.
#
# ⇒ A pergunta muda de forma e fica mais honesta: em vez de "a coorte está no
#   corpus servido?" (indecidível para fd deletado), pergunta-se "o corpus que
#   eu analisei É o servido?". Se for, a coorte medida É a coorte servida, por
#   construção. Se não for, a medição não fala sobre produção — e dizer isso é
#   informação, não desistência.
#
# Comparar por bytes e não por caminho é obrigatório aqui: o corpus recuperado
# de 03/09 tem caminho diferente do fd e é byte-idêntico a ele (sha256
# 23378a9e…, conferido nos dois).
CORPUS_REAL="$(readlink -f "$CORPUS" 2>/dev/null || printf '%s' "$CORPUS")"
CORPUS_SHA="$(sha256sum "$CORPUS_REAL" 2>/dev/null | cut -d' ' -f1)"
[ -n "$CORPUS_SHA" ] || CORPUS_SHA="nao-calculado"

ALCANCAVEL="nao"
FD_SHAS=""
while IFS= read -r fdnum; do
  [ -n "$fdnum" ] || continue
  FSHA="$(sha256sum "/proc/$SERV_PID/fd/$fdnum" 2>/dev/null | cut -d' ' -f1)"
  [ -n "$FSHA" ] || continue
  FD_SHAS="$FD_SHAS${FD_SHAS:+,}$(printf '%.12s' "$FSHA")"
  [ "$FSHA" = "$CORPUS_SHA" ] && ALCANCAVEL="sim"
done <<< "$SERV_ABERTOS"

# Sem sha do corpus não se afirma divergência: simétrico à perna 4. Afirmação
# positiva sobre dado ausente é o agravante da regra 9, não o silêncio dela.
if [ "$CORPUS_SHA" = "nao-calculado" ]; then
  emitir YELLOW "motivo=corpus-sem-sha semantica=sem-ler-os-bytes-do-corpus-nao-se-afirma-divergencia $BASE fds_abertos=$SERV_N"
fi

BASE="$BASE fds_abertos=$SERV_N corpus_sha256=$(printf '%.12s' "$CORPUS_SHA") fd_sha256s=$FD_SHAS corpus_e_o_servido=$ALCANCAVEL"

if [ "$ALCANCAVEL" = "nao" ]; then
  emitir RED "motivo=corpus-nao-e-o-servido semantica=nenhum-fd-aberto-tem-estes-bytes-logo-esta-medicao-de-coorte-NAO-fala-sobre-producao $BASE"
fi

# ─── Pernas 6 e 7: transitório esperado contra estrutural. Orçamento em
#     OPORTUNIDADE DE SLOT, não em horas de parede — ver cabeçalho.
if [ "${OPS:-0}" -lt "${ORC_V:-1}" ] 2>/dev/null; then
  emitir YELLOW "motivo=bloqueio-de-reingestao semantica=transitorio-esperado-o-precedente-de-22-08-drenou-53-em-1h12 briefs_desde_chegada=$BR oportunidades=$OPS orcamento=$ORC_V $BASE"
fi
emitir RED "motivo=bloqueio-estrutural semantica=orcamento-de-dreno-gasto-e-a-coorte-segue-nunca-servida briefs_desde_chegada=$BR oportunidades=$OPS orcamento=$ORC_V $BASE"
