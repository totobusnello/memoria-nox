#!/usr/bin/env bash
# Teste de especificidade por designação-sham — SPEC-ANALISE §5, o terceiro
# controlo pré-comprometido, que estava declarado NÃO EXECUTADO no Paper B.
#
# A pergunta: com 19 chunks NÃO designados e o mesmo `w`, o mecanismo move
# tanto quanto com os 19 reais? Se sim, o que medimos não é a designação — é
# churn de fundo.
#
# ⚠️ SEQUENCIAL e com `nice -n 19 ionice -c3`, de propósito. A VPS tem 2 vCPU e
# serve o OpenClaw em produção; 21 corridas são ~5 h de CPU. Paralelizar ou
# competir em prioridade degradaria o que a limpeza de hoje existiu para consertar.
#
# K = 20 shams não é arbitrário: com 21 corridas o p-valor mínimo por
# randomização é 1/21 = 4,8%, o menor K que permite rejeitar a 5%.
#
# ⚠️ O teto é 3600 s por corrida, não 900: a primeira tentativa foi morta a
# 900 s sem terminar, e `exit 124` é o NOSSO teto de tempo, nunca um veredito.
# O recibo grava `exit` e `dur` de cada corrida para que 124 seja legível como
# o que é.
set -uo pipefail

R=/root/.openclaw/scripts/p2/replay-oportunidade.mjs
OUT=/tmp/sham-out
mkdir -p "$OUT"

COMUM=(--modo dose
       --raiz /root/.openclaw/workspace/tools/nox-mem
       --corpus /var/lib/nox-mem/p2/corpus-preservado-20260908.db
       --vivo /root/.openclaw/workspace/tools/nox-mem/nox-mem.db
       --corte inclusivo
       --t-ref 2026-09-08T12:00:00Z
       --excluir-briefs /tmp/sham-sem-exclusao.txt
       --log-campo /root/.openclaw/logs/p2-serving.ndjson
       --w 4)

roda() {   # $1 = rótulo, $2 = caminho da designação
  local t0=$SECONDS sha
  sha=$(sha256sum "$2" | cut -d' ' -f1)
  # nice+ionice: a VPS serve o OpenClaw em producao e este teste e' 5h de CPU.
  # Ceder prioridade e' a diferenca entre um teste e um incidente.
  timeout 3600 nice -n 19 ionice -c3 node "$R" "${COMUM[@]}" \
    --designacao "$2" --designacao-sha256 "$sha" \
    --out "$OUT/$1.json" > "$OUT/$1.log" 2>&1
  local rc=$?
  printf '%s exit=%s dur=%ss sha_designacao=%s\n' \
    "$1" "$rc" "$((SECONDS-t0))" "${sha:0:16}" >> "$OUT/RECIBO.txt"
}

: > "$OUT/RECIBO.txt"
printf 'inicio %s\n' "$(date -u +%FT%TZ)" >> "$OUT/RECIBO.txt"

# a corrida REAL primeiro: é o baseline, e se ela falhar nada do resto vale
roda REAL /root/.openclaw/paper2/DESIGNATION-2026-08-26.json

for f in /tmp/shams/SHAM-*.json; do
  roda "$(basename "$f" .json)" "$f"
done

printf 'fim %s\n' "$(date -u +%FT%TZ)" >> "$OUT/RECIBO.txt"
