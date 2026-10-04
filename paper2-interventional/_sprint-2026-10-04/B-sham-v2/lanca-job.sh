#!/usr/bin/env bash
# Lancador do sham v2 (sprint 2026-10-04, B-sham-v2). Roda dentro do tmux `sprint-sham-v2`.
# Teto por corrida = 2x a corrida REAL completa MEDIDA (cal/REAL-w4.time: 1:00:31 = 3631 s).
# Prazo de parede total = 12 h. 3 nucleos no maximo; os 4 do kissat nao sao tocados.
W=/var/tmp/sprint-sham-v2-w
cd "$W" || exit 2
export SHAM_TETO_S=7200 SHAM_PRAZO_S=43200 SHAM_PARALELO=3 \
       SHAM_TS_FILE=$W/cal/ts-w4.txt SHAM_ESTADOS_ESPERADOS=2646 \
       SHAM_OUT=$W/job SHAM_DIR=$W/shams-impulsionavel
echo "lancado $(date -u +%FT%TZ) pid=$$" >> "$W/job-console.log"
bash "$W/raiz/sprint-roda-sham-v2.sh" >> "$W/job-console.log" 2>&1
echo "orquestrador saiu exit=$? $(date -u +%FT%TZ)" >> "$W/job-console.log"
