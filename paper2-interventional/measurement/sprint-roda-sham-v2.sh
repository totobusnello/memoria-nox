#!/usr/bin/env bash
# sprint-roda-sham-v2.sh — teste de especificidade por designação-sham (SPEC-ANALISE §5),
# versão 2 (sprint 2026-10-04, tarefa B-sham-v2). NÃO substitui `roda-sham.sh`, que fica
# como registro do que foi configurado em 2026-09-21.
#
# O que muda contra a v1 (cada item fecha um defeito MEDIDO em
# `_sprint-2026-10-04/B-replay-fidelity.md` ou nesta tarefa):
#
#   1. CORPUS: o que SERVIU o ensaio (`corpus-SERVING-REAL-e20260903-recuperado.db`,
#      sha256 23378a9e…, igual ao `serving_fd_sha256s` que o próprio gatilho registrou
#      todo dia de 09-10 a 09-21), não o `corpus-preservado-20260908.db`.
#   2. CORTE: `rowid` (o único exato), não `inclusivo`.
#   3. SERVE-STATE: `--vivo` = export do `brief_log` inteiro (até 2026-10-04) + `p2_verdict`,
#      não o banco vivo de produção (que este script nunca toca).
#   4. SHAMS: de `sprint-gera-shams-v2.py` (pool servido de 108, impulsionáveis,
#      severidade pareada), não de `gera-shams.py` (pool de 115).
#   5. DOSES: `--w 4 --w 100000`. `--w 4` sozinho SUBSTITUI o default e desliga o
#      controle positivo — foi o que tornou a calibração de 3h55 ininterpretável.
#   6. ESTADOS: lista explícita (`SHAM_TS_FILE`) e contagem esperada
#      (`SHAM_ESTADOS_ESPERADOS`) — a v1 rodava o log inteiro sem dizer quantos.
#   7. PARALELISMO limitado a 3 (a VPS de pesquisa tem 8 vCPU e 4 já estão em `kissat`
#      de outro projeto, que este script nunca toca) e `nice -n 10`.
#   8. PRAZO DE PAREDE obrigatório (`SHAM_PRAZO_S`), além do teto por corrida.
#   9. SAÍDA QUE DISTINGUE "TERMINOU" DE "PAROU NO MEIO":
#        - cada corrida escreve em `runs/<rot>.tmp.json`; só vira `runs/<rot>.json`
#          depois de VALIDADA (estados == esperado nas duas doses, zero `erro`);
#        - `STATUS` é uma linha só: RODANDO | CONCLUIDO | ABORTADO, reescrita atômica;
#        - `CONCLUIDO` (arquivo) só existe se as 21 corridas validaram, e carrega os sha256;
#        - morte por SIGKILL/reboot deixa `STATUS=RODANDO` com `HEARTBEAT` velho:
#          leitor trata tudo que não for CONCLUIDO como INCOMPLETO, nunca como "não moveu".
#  10. INSTRUMENTO PRESO: sha256 de script, dist, fonte, corpus, vivo, designações e lista
#      de estados no início; reconferido antes de cada corrida (e o corpus no fim).
#      Rodar shams numa versão e o REAL noutra destrói o teste em silêncio.
#  11. MODO COMPLETAR (2026-10-04, depois do aborto por throttling do host às 10:04Z):
#      `SHAM_CORRIDAS="SHAM-012 ... SHAM-019"` + `SHAM_JOB_REF=<job anterior>` roda SÓ as
#      corridas listadas num job NOVO. Antes de gastar CPU: o INSTRUMENTO.sha256 e o
#      BANCOS.sha256 calculados agora têm de ser IGUAIS byte a byte aos do job de referência
#      (mesmo replay, dist, fonte, estados, log, designações e bancos); nenhuma corrida
#      listada pode já estar validada lá; e cada corrida NÃO listada tem de estar validada
#      lá — é revalidada (mesma `valida`) e copiada para `runs/` com o hash conferido, para
#      que o job novo feche as 21 sozinho e o `CONCLUIDO` (e o leitor) não mudem de forma.
#      Sem o REAL na lista, o REAL herdado é o baseline; a guarda "REAL validado antes de
#      qualquer sham" continua valendo.
#
# Guardas herdadas da v1 (testadas em `sprint-testa-roda-sham-v2.sh`, inclusive por
# mutação): o REAL roda primeiro e sozinho e, se falhar ou sair sem saída válida, PARA
# tudo; qualquer corrida em 124 (teto ou prazo) PARA o conjunto, porque um sham não
# medido não é um sham que "não moveu".
set -uo pipefail

: "${SHAM_TETO_S:?defina SHAM_TETO_S (segundos por corrida), a partir de um numero MEDIDO (calibracao do REAL) — chute ja custou 12h}"
: "${SHAM_PRAZO_S:?defina SHAM_PRAZO_S (prazo de parede TOTAL, segundos)}"
: "${SHAM_TS_FILE:?defina SHAM_TS_FILE (lista explicita de ts dos estados)}"
: "${SHAM_ESTADOS_ESPERADOS:?defina SHAM_ESTADOS_ESPERADOS (numero de estados da lista)}"

W=${SHAM_W:-/var/tmp/sprint-sham-v2-w}
R=${SHAM_REPLAY:-$W/raiz/replay-oportunidade.mjs}
RAIZ=${SHAM_RAIZ:-$W/raiz}
CORPUS=${SHAM_CORPUS:-$W/db/corpus-SERVING-REAL-e20260903-recuperado.db}
VIVO=${SHAM_VIVO:-$W/db/vivo-v2.db}
OUT=${SHAM_OUT:-$W/job}
DESIG_REAL=${SHAM_DESIG_REAL:-$W/in/DESIGNATION-2026-08-26.json}
SHAMS_DIR=${SHAM_DIR:-$W/shams-impulsionavel}
LOG_CAMPO=${SHAM_LOG_CAMPO:-$W/in/p2-serving.ndjson}
EXCLUIR=${SHAM_EXCLUIR:-$W/in/excluir-vazio.txt}
TMPB=${SHAM_TMP_BASE:-$W/tmp}
NODE=${SHAM_NODE:-node}
NICE=${SHAM_NICE-nice -n 10}
PARALELO=${SHAM_PARALELO:-1}
K_ESPERADO=${SHAM_K_ESPERADO:-20}
AMOSTRA_S=${SHAM_AMOSTRA_S:-60}
DOSES=(4 100000)

case "$PARALELO" in 1|2|3) ;; *) echo "SHAM_PARALELO=$PARALELO recusado: maximo 3 (4 nucleos ja ocupados por outro projeto)" >&2; exit 2;; esac

ts_now() { date -u +%FT%TZ; }
escreve_status() { printf '%s\n' "$*" > "$OUT/STATUS.tmp" && mv -f "$OUT/STATUS.tmp" "$OUT/STATUS"; }
recibo() { printf '%s\n' "$*" >> "$OUT/RECIBO.txt"; }

mkdir -p "$OUT/runs" "$TMPB"
if [ -e "$OUT/CONCLUIDO" ] || [ -e "$OUT/RECIBO.txt" ]; then
  echo "OUT=$OUT ja tem RECIBO/CONCLUIDO de outra corrida: recuso sobrescrever (apague ou use outro SHAM_OUT)" >&2; exit 2
fi
: > "$OUT/RECIBO.txt"; : > "$OUT/PROGRESSO.ndjson"
T0=$(date +%s); PRAZO_FIM=$((T0 + SHAM_PRAZO_S))
escreve_status "RODANDO $(ts_now) concluidas=0/$((K_ESPERADO+1))"

# --- o que roda: REAL + K shams, conferidos ANTES de gastar CPU ------------------------
SHAMS=()
for f in "$SHAMS_DIR"/SHAM-*.json; do [ -e "$f" ] && SHAMS+=("$f"); done
TOTAL=$((${#SHAMS[@]} + 1))
nts=$(grep -cv '^\s*$' "$SHAM_TS_FILE" 2>/dev/null || true)

aborta() {   # $1 = motivo ; mata o que estiver em curso
  local p
  for p in "${!EM_CURSO[@]}"; do kill -TERM "$p" 2>/dev/null; done
  for p in "${!EM_CURSO[@]}"; do wait "$p" 2>/dev/null; recibo "$(ts_now) ${EM_CURSO[$p]} INTERROMPIDA pelo aborto -- NAO MEDIDA"; done
  recibo "ABORTADO $(ts_now) -- $1. Corridas validadas: $(ls "$OUT"/runs/*.json 2>/dev/null | grep -vc '\.tmp\.json$')/$TOTAL. Um 124 e o NOSSO teto/prazo, nunca um veredito: corrida nao validada e NAO MEDIDA, nao 'nao moveu'. Nao calcular p sobre isto."
  escreve_status "ABORTADO $(ts_now) motivo=$1"
  exit 1
}
declare -A EM_CURSO=()
trap 'aborta "sinal recebido pelo orquestrador"' TERM INT HUP

[ "${#SHAMS[@]}" = "$K_ESPERADO" ] || aborta "achei ${#SHAMS[@]} shams em $SHAMS_DIR, esperado $K_ESPERADO"
[ "$nts" = "$SHAM_ESTADOS_ESPERADOS" ] || aborta "SHAM_TS_FILE tem $nts ts, esperado $SHAM_ESTADOS_ESPERADOS"

# --- instrumento preso --------------------------------------------------------------------
PEQUENOS=("$R" "$RAIZ/dist/api/brief.js" "$RAIZ/dist/api/brief-diversity.js" "$RAIZ/dist/paper2/brief-outcome.js"
          "$RAIZ/src/api/brief.ts" "$SHAM_TS_FILE" "$LOG_CAMPO" "$EXCLUIR" "$DESIG_REAL" "${SHAMS[@]}")
for f in "${PEQUENOS[@]}" "$CORPUS" "$VIVO"; do [ -r "$f" ] || aborta "instrumento ilegivel: $f"; done
sha256sum "${PEQUENOS[@]}" > "$OUT/INSTRUMENTO.sha256"
sha256sum "$CORPUS" "$VIVO" > "$OUT/BANCOS.sha256"
confere_instrumento() { sha256sum --quiet -c "$OUT/INSTRUMENTO.sha256" >/dev/null 2>&1; }

recibo "inicio $(ts_now) teto=${SHAM_TETO_S}s prazo=${SHAM_PRAZO_S}s (ate $(date -u -d @"$PRAZO_FIM" +%FT%TZ 2>/dev/null || echo "$PRAZO_FIM")) paralelo=$PARALELO corridas=$TOTAL estados=$SHAM_ESTADOS_ESPERADOS doses=${DOSES[*]}"
recibo "instrumento: $(sha256sum "$OUT/INSTRUMENTO.sha256" | cut -c1-16) bancos: $(cut -c1-16 "$OUT/BANCOS.sha256" | tr '\n' ' ')"

# --- validação: uma saída só conta se cobre TODOS os estados nas DUAS doses, sem erro ---
valida() {   # $1 = json ; imprime motivo e sai !=0 se invalido
  python3 - "$1" "$SHAM_ESTADOS_ESPERADOS" "${DOSES[@]}" <<'PY'
import json, sys
p, n, doses = sys.argv[1], int(sys.argv[2]), [float(x) for x in sys.argv[3:]]
try:
    d = json.load(open(p))["dose"]
except Exception as e:
    print(f"ilegivel: {e}"); sys.exit(1)
if d.get("estados") != n:
    print(f"estados={d.get('estados')} esperado={n}"); sys.exit(1)
tab = {float(t["w"]): t for t in d.get("tabela", [])}
for w in doses:
    if w not in tab or tab[w].get("estados") != n:
        print(f"dose w={w}: {tab.get(w, {}).get('estados')} estados de {n}"); sys.exit(1)
err = sum(1 for x in d.get("detalhe", []) if x.get("erro"))
if err:
    print(f"{err} itens com erro"); sys.exit(1)
print("ok")
PY
}

amostra() {   # $1 rotulo, $2 pid do timeout — progresso + heartbeat
  local npid st ut rss t0=$SECONDS
  while kill -0 "$2" 2>/dev/null; do
    npid=$(pgrep -P "$2" | head -1)
    if [ -n "${npid:-}" ] && [ -r "/proc/$npid/stat" ]; then
      read -r -a st < "/proc/$npid/stat"
      ut=$(( (${st[13]:-0} + ${st[14]:-0}) / 100 ))
      rss=$(awk '/^VmRSS/{print $2}' "/proc/$npid/status" 2>/dev/null)
      printf '{"corrida":"%s","ts":"%s","parede_s":%s,"cpu_s":%s,"rss_kb":%s}\n' \
        "$1" "$(ts_now)" "$((SECONDS-t0))" "$ut" "${rss:-0}" >> "$OUT/PROGRESSO.ndjson"
    fi
    ts_now > "$OUT/HEARTBEAT"
    sleep "$AMOSTRA_S"
  done
}

declare -A INICIO=() SHA_DE=()
lanca() {   # $1 rotulo, $2 designacao
  local agora restante teto sha tpid
  confere_instrumento || aborta "instrumento mudou antes de lancar $1 (INSTRUMENTO.sha256 nao confere)"
  agora=$(date +%s); restante=$((PRAZO_FIM - agora))
  [ "$restante" -gt 0 ] || aborta "prazo de parede esgotado antes de lancar $1"
  teto=$SHAM_TETO_S; [ "$restante" -lt "$teto" ] && teto=$restante
  sha=$(sha256sum "$2" | cut -d' ' -f1)
  timeout "$teto" $NICE $NODE "$R" --modo dose --raiz "$RAIZ" --corpus "$CORPUS" --vivo "$VIVO" \
    --corte rowid --t-ref 2026-09-01T00:00:00Z --excluir-briefs "$EXCLUIR" --log-campo "$LOG_CAMPO" \
    --so-ts-file "$SHAM_TS_FILE" --w "${DOSES[0]}" --w "${DOSES[1]}" --tmp-base "$TMPB" --sem-assert \
    --designacao "$2" --designacao-sha256 "$sha" \
    --out "$OUT/runs/$1.tmp.json" > "$OUT/runs/$1.log" 2>&1 &
  tpid=$!
  EM_CURSO[$tpid]=$1; INICIO[$tpid]=$SECONDS; SHA_DE[$tpid]=${sha:0:16}
  amostra "$1" "$tpid" &
  recibo "$(ts_now) $1 lancada teto=${teto}s"
}

concluidas=0
fecha() {   # $1 pid ; espera, valida, promove ou aborta
  local p=$1 rot=${EM_CURSO[$1]} rc motivo
  wait "$p"; rc=$?
  unset "EM_CURSO[$p]"
  recibo "$(ts_now) $rot exit=$rc dur=$((SECONDS - ${INICIO[$p]}))s sha_designacao=${SHA_DE[$p]}"
  if [ "$rc" != 0 ]; then
    [ "$rc" = 124 ] && aborta "$rot saiu exit=124 (teto ou prazo)"
    aborta "$rot saiu exit=$rc"
  fi
  [ -s "$OUT/runs/$rot.tmp.json" ] || aborta "$rot saiu 0-sem-saida"
  motivo=$(valida "$OUT/runs/$rot.tmp.json")
  [ "$motivo" = ok ] || aborta "$rot saida invalida ($motivo) -- parcial nao e resultado"
  mv -f "$OUT/runs/$rot.tmp.json" "$OUT/runs/$rot.json"
  concluidas=$((concluidas + 1))
  escreve_status "RODANDO $(ts_now) concluidas=$concluidas/$TOTAL em_curso=${#EM_CURSO[@]}"
  recibo "$(ts_now) $rot VALIDADA ($concluidas/$TOTAL)"
}

espera_uma() {   # bloqueia ate alguma corrida em curso terminar e a fecha
  local p
  while :; do
    for p in "${!EM_CURSO[@]}"; do
      if ! kill -0 "$p" 2>/dev/null; then fecha "$p"; return; fi
    done
    sleep 2
  done
}

# --- o que este job roda: tudo (default) ou so a lista (modo completar, item 11) -----------
RODAR=(REAL); for f in "${SHAMS[@]}"; do RODAR+=("$(basename "$f" .json)"); done
if [ -n "${SHAM_CORRIDAS:-}" ]; then
  REF=${SHAM_JOB_REF:-}
  { [ -n "$REF" ] && [ -d "$REF/runs" ]; } || aborta "SHAM_CORRIDAS exige SHAM_JOB_REF apontando para o job anterior"
  cmp -s "$OUT/INSTRUMENTO.sha256" "$REF/INSTRUMENTO.sha256" || aborta "instrumento difere do job de referencia ($REF/INSTRUMENTO.sha256)"
  cmp -s "$OUT/BANCOS.sha256" "$REF/BANCOS.sha256" || aborta "bancos diferem do job de referencia ($REF/BANCOS.sha256)"
  declare -A PEDIDA=()
  for r in $SHAM_CORRIDAS; do
    printf '%s\n' "${RODAR[@]}" | grep -qx -- "$r" || aborta "corrida pedida desconhecida: $r"
    [ -z "${PEDIDA[$r]:-}" ] || aborta "corrida pedida duas vezes: $r"
    [ ! -e "$REF/runs/$r.json" ] || aborta "$r ja esta validada em $REF: recuso rodar de novo"
    PEDIDA[$r]=1
  done
  NOVAS=()
  for r in "${RODAR[@]}"; do
    if [ -n "${PEDIDA[$r]:-}" ]; then NOVAS+=("$r"); continue; fi
    [ -s "$REF/runs/$r.json" ] || aborta "$r nem pedida nem validada em $REF: a uniao nao fecharia $TOTAL"
    motivo=$(valida "$REF/runs/$r.json")
    [ "$motivo" = ok ] || aborta "herdada $r invalida em $REF ($motivo)"
    cp "$REF/runs/$r.json" "$OUT/runs/$r.herdando" && mv -f "$OUT/runs/$r.herdando" "$OUT/runs/$r.json"
    cmp -s "$REF/runs/$r.json" "$OUT/runs/$r.json" || aborta "copia herdada de $r nao confere"
    concluidas=$((concluidas + 1))
    recibo "$(ts_now) $r HERDADA de $REF sha256=$(sha256sum "$OUT/runs/$r.json" | cut -c1-16) ($concluidas/$TOTAL)"
  done
  RODAR=("${NOVAS[@]}")
  recibo "modo completar: herdadas=$concluidas a_rodar=${#RODAR[@]} (${RODAR[*]}) ref=$REF"
  escreve_status "RODANDO $(ts_now) concluidas=$concluidas/$TOTAL"
fi

# a corrida REAL primeiro e SOZINHA: e o baseline; se ela falhar nada do resto vale.
if [ "${RODAR[0]:-}" = REAL ]; then
  lanca REAL "$DESIG_REAL"
  espera_uma
  RODAR=("${RODAR[@]:1}")
fi
[ -s "$OUT/runs/REAL.json" ] || aborta "REAL sem saida validada"

for r in "${RODAR[@]}"; do
  while [ "${#EM_CURSO[@]}" -ge "$PARALELO" ]; do espera_uma; done
  lanca "$r" "$SHAMS_DIR/$r.json"
done
while [ "${#EM_CURSO[@]}" -gt 0 ]; do espera_uma; done

# --- fecho: tudo validado, instrumento e bancos intactos -----------------------------------
n=$(ls "$OUT"/runs/*.json 2>/dev/null | grep -vc '\.tmp\.json$')
[ "$n" = "$TOTAL" ] || aborta "fim do laco com $n/$TOTAL saidas validadas"
confere_instrumento || aborta "instrumento mudou durante a corrida"
sha256sum --quiet -c "$OUT/BANCOS.sha256" >/dev/null 2>&1 || aborta "corpus ou vivo mudaram durante a corrida"
( cd "$OUT/runs" && sha256sum REAL.json SHAM-*.json ) > "$OUT/CONCLUIDO.tmp" && mv -f "$OUT/CONCLUIDO.tmp" "$OUT/CONCLUIDO"
recibo "fim $(ts_now) -- $n/$TOTAL corridas validadas em $((SECONDS))s"
escreve_status "CONCLUIDO $(ts_now) $n/$TOTAL validadas"
exit 0
