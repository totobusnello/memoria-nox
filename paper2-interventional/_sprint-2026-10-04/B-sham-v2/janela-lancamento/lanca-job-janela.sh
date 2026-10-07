#!/usr/bin/env bash
# Lancador do sham v2 na JANELA INTEIRA do ensaio (sprint 2026-10-04, decisao do Toto:
# «rodar antes de depositar»). Roda dentro do tmux `sprint-sham-janela` na VPS de Pesquisa.
#
# Mesmo instrumento do job-v2b (29/29 hashes de INSTRUMENTO.sha256 iguais com cal/ts-w4.txt;
# BANCOS.sha256 igual), mesma designacao REAL, mesmos 20 shams. Muda SO a lista de estados:
# cal/ts-janela.txt (11.865 estados, 2026-09-03T17:23:39Z..2026-09-21T08:52:05Z, 18 epocas,
# todas servidas pelo corpus 23378a9e… provado por fd). NAO inclui a epoca 09-01 (630 estados
# w=4 do job-v2b), cujo corpus nao tem prova por hash.
#
# Teto e prazo vem do custo MEDIDO hoje (cal/TRI*-amostra200: 3 lanes simultaneas + 6 kissat
# sob o guarda de CPU, 314,5 s / 200 estados = 1,572 s/estado):
#   corrida projetada = 11.865 x 1,572 = 18.652 s (5,2 h);
#   teto = 2x a corrida x 1,5 de folga para throttling do host = 56.000 s (15,6 h);
#   job projetado = REAL sozinha + 7 ondas (3+3+3+3+3+3+2) = 8 x 5,2 h = 41,5 h;
#   prazo = ~2x o job projetado = 297.000 s (82,5 h).
# Um 124 (teto ou prazo) e o NOSSO limite, nunca um veredito: o job aborta e e retomado pelo
# modo completar do runner (SHAM_CORRIDAS + SHAM_JOB_REF), nunca recalculado sobre parcial.
W=/var/tmp/sprint-sham-v2-janela-w
cd "$W" || exit 2
export SHAM_W=$W \
       SHAM_TETO_S=${SHAM_TETO_S:-56000} SHAM_PRAZO_S=${SHAM_PRAZO_S:-297000} SHAM_PARALELO=${SHAM_PARALELO:-3} \
       SHAM_TS_FILE=$W/cal/ts-janela.txt SHAM_ESTADOS_ESPERADOS=11865 \
       SHAM_OUT=$W/job-janela SHAM_DIR=$W/shams-impulsionavel
{
  echo "lancado $(date -u +%FT%TZ) pid=$$ teto=$SHAM_TETO_S prazo=$SHAM_PRAZO_S paralelo=$SHAM_PARALELO estados=$SHAM_ESTADOS_ESPERADOS"
  echo "runner sha256=$(sha256sum "$W/raiz/sprint-roda-sham-v2.sh" | cut -d' ' -f1)"
} >> "$W/job-janela-console.log"
bash "$W/raiz/sprint-roda-sham-v2.sh" >> "$W/job-janela-console.log" 2>&1
echo "orquestrador saiu exit=$? $(date -u +%FT%TZ)" >> "$W/job-janela-console.log"
