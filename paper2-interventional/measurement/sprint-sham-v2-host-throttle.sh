#!/usr/bin/env bash
# sprint-sham-v2-host-throttle.sh — hipótese (c) do diagnóstico do aborto do sham v2
# (2026-10-04): o host está entregando CPU REAL? Roda na VPS de pesquisa ($NOX_LASTRO_HOST).
#
# Três pernas, porque nenhuma sozinha basta neste guest:
#   1. Histórico (sysstat, 10 min): CPUs REAIS entregues = (user+nice+sys)·8/100 e CPUs
#      roubadas = steal·8/100. Os arquivos /var/log/sysstat/saDD são por dia LOCAL (UTC-3).
#   2. Agora (mpstat): steal por vCPU.
#   3. Microbenchmark de trabalho FIXO sob `perf stat`: ciclos:u (CPU real recebido) contra
#      parede. Razão parede/ciclos = fator de lentidão do host.
#
# ⚠️ Por que não basta olhar CPU do processo: `CONFIG_PARAVIRT_TIME_ACCOUNTING` está
# desligado aqui, então utime/stime do processo INCLUEM o steal. Um processo throttled mostra
# cpu ≈ parede e parece "CPU-bound" — foi a leitura que mascarou o throttling no aborto.
#
# Uso: bash sprint-sham-v2-host-throttle.sh [DD ...]   (default: ontem e hoje, hora local)
set -uo pipefail
DIAS=("$@"); [ "${#DIAS[@]}" -gt 0 ] || DIAS=("$(date -d yesterday +%d)" "$(date +%d)")
NCPU=$(nproc)
echo "host=$(hostname) ncpu=$NCPU agora=$(date -u +%FT%TZ) tz_local=$(date +%Z)"
for d in "${DIAS[@]}"; do
  f=/var/log/sysstat/sa$d
  [ -r "$f" ] || { echo "sem $f"; continue; }
  echo "== $f (hora LOCAL) — cpus_reais = (user+nice+sys)*$NCPU/100 ; cpus_roubadas = steal*$NCPU/100"
  LC_ALL=C sar -u -f "$f" | awk -v n="$NCPU" '$2=="all" && $1 ~ /^[0-9]/ {
      printf "%s cpus_reais=%.2f cpus_roubadas=%.2f cpus_ociosas=%.2f\n", $1, ($3+$4+$5)*n/100, $7*n/100, $8*n/100 }'
done
echo "== mpstat por vCPU (5 s)"
mpstat -P ALL 5 1 | awk '/^Average/'
echo "== microbenchmark fixo (python, 2e6 iteracoes) sob perf: parede vs ciclos reais"
for i in 1 2 3; do
  t0=$(date +%s.%N)
  c=$(perf stat -x, -e cycles:u nice -n 10 python3 -c "sum(i*i for i in range(2_000_000))" 2>&1 >/dev/null | awk -F, '/cycles/{print $1}')
  t1=$(date +%s.%N)
  awk -v a="$t0" -v b="$t1" -v c="$c" 'BEGIN{p=b-a; r=c/3.25e9; printf "parede=%.2fs cpu_real=%.3fs (ciclos:u/3.25GHz) fator_lentidao=%.1fx\n", p, r, p/r}'
done
