#!/bin/bash
# Classificador de FALHA no log de uma busca. READ-ONLY, exit 0 sempre.
#
# 🔴 O predicado anterior era "existe /error/i no log" e casava o `(0 errors)`
# de CADA linha de progresso -- um alarme vermelho por marco, todos sobre
# sucesso. Mesma classe do contador que lia `501 relations` como HTTP 5xx.
#
# ⚠️ `error:` de sessao (`[zep search] session=... error: timed out`) e'
# TOLERADO por desenho (limiar de 1% em ZEP_MAX_ERRO_SESSAO). Ele e' contado e
# reportado, nao alarmado -- alarmar o que o desenho tolera ensina a ignorar
# alarme, que e' o dano de segunda ordem.
set -uo pipefail
LOG="${1:?uso: $0 <log> [PREFIXO]}"
# 🔴 O prefixo e' PARAMETRO, nao renomeacao posterior. Medido 2026-09-10: o vigia
# fazia `sed "s/^BUSCA_/EVB_/"` sobre a saida, e como os tres campos saem NUMA
# LINHA SO, o `^` renomeava apenas o primeiro. Os outros dois ficavam
# `BUSCA_ERRO_SESSAO=` e `BUSCA_PROG=` e o `tail -1` do vigia colhia os valores
# do EverOS como se fossem do Zep -- com numeros PLAUSIVEIS, logo invisiveis.
# Renomear na origem elimina a classe: nao ha o que um ancora possa nao alcancar.
P="${2:-BUSCA}"
[ -r "$LOG" ] || { echo "${P}_SEM_LOG=$LOG"; exit 0; }
RE_FALHA='Traceback|FATAL|\([1-9][0-9]* errors\)'
RE_SESSAO='session=[^ ]+ error:'
FALHA=$(grep -acE "$RE_FALHA" "$LOG" || true)
SESSAO=$(grep -acE "$RE_SESSAO" "$LOG" || true)
PROG=$(grep -aoE '[0-9]+/[0-9]+ \(0 errors\)' "$LOG" | tail -1 || true)
echo "${P}_FALHA=$FALHA ${P}_ERRO_SESSAO=$SESSAO ${P}_PROG=${PROG:-nenhum}"
if [ "${FALHA:-0}" -gt 0 ]; then
  grep -aE "$RE_FALHA" "$LOG" | tail -2 | sed "s/^/${P}_LINHA_FALHA=/"
fi
exit 0
