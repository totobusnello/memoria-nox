#!/usr/bin/env bash
# Teste de especificidade por designação-sham — SPEC-ANALISE §5, o terceiro
# controlo pré-comprometido, que estava declarado NÃO EXECUTADO no Paper B.
#
# A pergunta: com 19 chunks NÃO designados e o mesmo `w`, o mecanismo move
# tanto quanto com os 19 reais? Se sim, o que medimos não é a designação — é
# churn de fundo.
#
# ⚠️ SEQUENCIAL e com `nice -n 19 ionice -c3`, de propósito. A VPS tem 2 vCPU e
# serve o OpenClaw em produção. Paralelizar ou competir em prioridade degradaria
# o que a limpeza existiu para consertar.
#
# K = 20 shams não é arbitrário: com 21 corridas o p-valor mínimo por
# randomização é 1/21 = 4,8%, o menor K que permite rejeitar a 5%.
#
# ─────────────────────────────────────────────────────────────────────────────
# REVISÃO 2026-09-22, depois de a versão anterior queimar 12h e medir ZERO.
#
# O que deu errado: 12 corridas, 12 × `exit=124`, nenhum `.json`. A versão
# anterior dizia no comentário «a corrida REAL primeiro: se ela falhar nada do
# resto vale» — e não implementava a parada. O REAL saiu 124 na primeira hora e
# o loop seguiu por mais onze. Promessa no cabeçalho não é implementação.
#
# Três mudanças, cada uma fechando um modo de falha observado:
#
#   1. O REAL agora PARA o script se não produzir saída. A frase virou código.
#   2. QUALQUER corrida em 124 para o script. Um sham não medido não é um sham
#      que «não moveu» — contá-lo como zero inverteria o resultado na direção
#      confortável, e prosseguir produz um `p` sobre uma distribuição nula
#      incompleta, que é pior do que não ter `p` nenhum.
#   3. O teto deixou de ter default. `SHAM_TETO_S` é OBRIGATÓRIO e quem lança
#      tem de declarar de onde veio o número. O 3600 anterior veio de uma
#      projeção («~14 min por corrida») que nunca foi medida; o medido é ≥60 min.
#      Calibração: `/root/calibra-real.sh` → `/tmp/calibra-real/RECIBO.txt`.
#
# ⚠️ Otimizar o replay é legítimo AQUI, mas a condição é dura: as 21 corridas
# têm de usar a MESMA versão do instrumento. `p` compara o REAL contra os shams
# desta mesma corrida, não contra nenhum número publicado antes. Rodar shams
# numa versão e o REAL noutra destrói o teste em silêncio.
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

: "${SHAM_TETO_S:?defina SHAM_TETO_S (segundos por corrida). Sem numero MEDIDO em /tmp/calibra-real/RECIBO.txt, qualquer teto sera chute — e foi um chute que custou 12h}"

# Caminhos parametrizados para que as guardas acima sejam TESTAVEIS. Sem isto
# a correcao de hoje seria outra promessa nao verificada — exactamente a classe
# de defeito que ela existe para consertar. Os defaults sao os da VPS; o teste
# (`testa-roda-sham.sh`) injecta stubs por estas variaveis.
R=${SHAM_REPLAY:-/root/.openclaw/scripts/p2/replay-oportunidade.mjs}
OUT=${SHAM_OUT:-/tmp/sham-out}
DESIG_REAL=${SHAM_DESIG_REAL:-/root/.openclaw/paper2/DESIGNATION-2026-08-26.json}
SHAMS_DIR=${SHAM_DIR:-/tmp/shams}
NODE=${SHAM_NODE:-node}
# nice+ionice: a VPS serve o OpenClaw em producao e este teste e de horas de CPU.
# Ceder prioridade e a diferenca entre um teste e um incidente. Vazio so no
# harness de teste, onde `ionice` nem existe.
NICE=${SHAM_NICE-nice -n 19 ionice -c3}

COMUM=(--modo dose
       --raiz /root/.openclaw/workspace/tools/nox-mem
       --corpus /var/lib/nox-mem/p2/corpus-preservado-20260908.db
       --vivo /root/.openclaw/workspace/tools/nox-mem/nox-mem.db
       --corte inclusivo
       --t-ref 2026-09-08T12:00:00Z
       --excluir-briefs ${SHAM_EXCLUIR:-/tmp/sham-sem-exclusao.txt}
       --log-campo ${SHAM_LOG_CAMPO:-/root/.openclaw/logs/p2-serving.ndjson}
       --w 4)

# amostrador: o replay nao emite nada ate o fim, e foi por isso que 12h de 124
# foram ilegiveis — "morreu a 5%" e "morreu a 95%" tinham saida identica.
# Amostra o filho do `timeout` por PPID; `pgrep -f` casaria a propria linha de
# comando de quem o executa.
amostra() {   # $1 = rotulo, $2 = pid do timeout
  local npid st ut rss rb t0=$SECONDS
  while kill -0 "$2" 2>/dev/null; do
    npid=$(pgrep -P "$2" | head -1)
    if [ -n "${npid:-}" ] && [ -r "/proc/$npid/stat" ]; then
      read -r -a st < "/proc/$npid/stat"
      ut=$(( (${st[13]:-0} + ${st[14]:-0}) / 100 ))
      rss=$(awk '/^VmRSS/{print $2}' "/proc/$npid/status" 2>/dev/null)
      rb=$(awk '/^read_bytes/{print $2}' "/proc/$npid/io" 2>/dev/null)
      printf '{"corrida":"%s","ts":"%s","parede_s":%s,"cpu_s":%s,"rss_kb":%s,"read_bytes":%s}\n' \
        "$1" "$(date -u +%FT%TZ)" "$((SECONDS-t0))" "$ut" "${rss:-0}" "${rb:-0}" >> "$OUT/PROGRESSO.ndjson"
    fi
    sleep 300
  done
}

roda() {   # $1 = rótulo, $2 = caminho da designação; devolve o exit da corrida
  local t0=$SECONDS sha rc tpid
  sha=$(sha256sum "$2" | cut -d' ' -f1)
  # nice+ionice: a VPS serve o OpenClaw em producao. Ceder prioridade e' a
  # diferenca entre um teste e um incidente.
  timeout "$SHAM_TETO_S" $NICE $NODE "$R" "${COMUM[@]}" \
    --designacao "$2" --designacao-sha256 "$sha" \
    --out "$OUT/$1.json" > "$OUT/$1.log" 2>&1 &
  tpid=$!
  amostra "$1" "$tpid" &
  wait "$tpid"; rc=$?
  printf '%s exit=%s dur=%ss sha_designacao=%s out=%s\n' \
    "$1" "$rc" "$((SECONDS-t0))" "${sha:0:16}" \
    "$([ -s "$OUT/$1.json" ] && stat -c %s "$OUT/$1.json" || echo AUSENTE)" >> "$OUT/RECIBO.txt"
  return "$rc"
}

para() {   # $1 = rotulo da corrida que falhou, $2 = exit
  printf 'ABORTADO %s -- %s saiu exit=%s. Uma corrida em 124 e o NOSSO teto de tempo, nunca um veredito: e NAO MEDIDA, nao "nao moveu". Prosseguir daria um p sobre distribuicao nula incompleta.\n' \
    "$(date -u +%FT%TZ)" "$1" "$2" >> "$OUT/RECIBO.txt"
  exit 1
}

mkdir -p "$OUT"
: > "$OUT/RECIBO.txt"
: > "$OUT/PROGRESSO.ndjson"
printf 'inicio %s teto=%ss\n' "$(date -u +%FT%TZ)" "$SHAM_TETO_S" >> "$OUT/RECIBO.txt"

# a corrida REAL primeiro: e' o baseline, e se ela falhar nada do resto vale.
# Esta linha e' a promessa; as duas seguintes sao o cumprimento dela.
roda REAL "$DESIG_REAL" || para REAL "$?"
[ -s "$OUT/REAL.json" ] || para REAL "0-sem-saida"

for f in "$SHAMS_DIR"/SHAM-*.json; do
  n=$(basename "$f" .json)
  roda "$n" "$f" || para "$n" "$?"
  [ -s "$OUT/$n.json" ] || para "$n" "0-sem-saida"
done

printf 'fim %s -- %s corridas com saida\n' "$(date -u +%FT%TZ)" "$(ls "$OUT"/*.json 2>/dev/null | wc -l)" >> "$OUT/RECIBO.txt"
