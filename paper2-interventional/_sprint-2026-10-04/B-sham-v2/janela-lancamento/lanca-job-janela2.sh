#!/usr/bin/env bash
# Relancamento 2026-10-05: a 1a tentativa (job-janela-abortado-1) abortou porque 53 estados
# (52 do agente nox em 2026-09-21, 1 em 2026-09-06) nao tem brief localizavel no brief_log por
# (agent, segundo, 10 ids): corte rowid impossivel, para QUALQUER designacao (propriedade do dado,
# nao do resultado). Lista de estados = cal/ts-janela-reconstruivel.txt (11.812; sha 956e712e…);
# excluidos em cal/ts-janela-excluidos-53.txt (sha fd0bb5cd…). Resto identico ao lanca-job-janela.sh.
W=/var/tmp/sprint-sham-v2-janela-w
cd "$W" || exit 2
export SHAM_W=$W \
       SHAM_TETO_S=${SHAM_TETO_S:-56000} SHAM_PRAZO_S=${SHAM_PRAZO_S:-297000} SHAM_PARALELO=${SHAM_PARALELO:-3} \
       SHAM_TS_FILE=$W/cal/ts-janela-reconstruivel.txt SHAM_ESTADOS_ESPERADOS=11812 \
       SHAM_OUT=$W/job-janela2 SHAM_DIR=$W/shams-impulsionavel
{
  echo "lancado $(date -u +%FT%TZ) pid=$$ teto=$SHAM_TETO_S prazo=$SHAM_PRAZO_S paralelo=$SHAM_PARALELO estados=$SHAM_ESTADOS_ESPERADOS"
  echo "runner sha256=$(sha256sum "$W/raiz/sprint-roda-sham-v2.sh" | cut -d" " -f1)"
} >> "$W/job-janela2-console.log"
bash "$W/raiz/sprint-roda-sham-v2.sh" >> "$W/job-janela2-console.log" 2>&1
echo "orquestrador saiu exit=$? $(date -u +%FT%TZ)" >> "$W/job-janela2-console.log"
