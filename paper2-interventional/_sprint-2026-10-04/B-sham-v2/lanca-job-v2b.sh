#!/usr/bin/env bash
# Lancador do sham v2b (sprint 2026-10-04): COMPLETA as 8 corridas que o job `job/` nao
# validou (SHAM-012..019), no modo completar do runner (item 11 de sprint-roda-sham-v2.sh).
# Roda dentro do tmux `sprint-sham-v2b`.
#
# Por que o job anterior abortou (medido, ver o relatorio do diagnostico): o host passou a
# ser estrangulado pelo hipervisor a partir de ~07:10Z (CPUs reais entregues ao guest:
# ~6,3 -> 5,8 -> 3,8 -> 1,9 -> ~0,37, degraus de ~1 h; steal ~92% em cada vCPU ocupada).
# Nao e o instrumento (hashes conferem, sem -wal/-shm, bancos readonly) nem a designacao.
#
# Teto e prazo vem da PROJECAO SOB O THROTTLING MEDIDO, nao do custo sem throttling:
#   custo real por corrida ~3.400 s de CPU (job anterior, ondas 1-4, descontado o steal;
#   confirmado em ciclos pela amostra de 50 estados);
#   CPU real do guest hoje ~0,37 dividida por 4 kissat + N lanes -> 0,053 por lane com N=3;
#   => ~64.000 s (17,8 h) por corrida; 3 ondas (3+3+2) => ~51 h.
# Teto = 2x a corrida projetada; prazo = 2x o job projetado. Se o throttling sair, o job
# termina em ~3,5 h (3 ondas de ~1,1 h) e os limites so ficam folgados.
W=/var/tmp/sprint-sham-v2-w
cd "$W" || exit 2
export SHAM_TETO_S=${SHAM_TETO_S:-128000} SHAM_PRAZO_S=${SHAM_PRAZO_S:-370000} SHAM_PARALELO=${SHAM_PARALELO:-3} \
       SHAM_TS_FILE=$W/cal/ts-w4.txt SHAM_ESTADOS_ESPERADOS=2646 \
       SHAM_OUT=$W/job-v2b SHAM_DIR=$W/shams-impulsionavel \
       SHAM_JOB_REF=$W/job \
       SHAM_CORRIDAS="SHAM-012 SHAM-013 SHAM-014 SHAM-015 SHAM-016 SHAM-017 SHAM-018 SHAM-019"
{
  echo "lancado $(date -u +%FT%TZ) pid=$$ teto=$SHAM_TETO_S prazo=$SHAM_PRAZO_S paralelo=$SHAM_PARALELO"
  echo "runner sha256=$(sha256sum "$W/raiz/sprint-roda-sham-v2.sh" | cut -d' ' -f1)"
  echo "corridas=$SHAM_CORRIDAS ref=$SHAM_JOB_REF"
} >> "$W/job-v2b-console.log"
bash "$W/raiz/sprint-roda-sham-v2.sh" >> "$W/job-v2b-console.log" 2>&1
echo "orquestrador saiu exit=$? $(date -u +%FT%TZ)" >> "$W/job-v2b-console.log"
