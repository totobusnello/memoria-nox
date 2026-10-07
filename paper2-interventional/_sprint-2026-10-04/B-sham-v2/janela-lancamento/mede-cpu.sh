#!/usr/bin/env bash
# mede-cpu.sh [segundos=300] [passo=10] — CPU total do host via /proc/stat.
# usado = user+nice+system+irq+softirq (o que o guest EXECUTOU); steal a parte.
# pct = usado / (parede * ncpu). Imprime uma linha por passo e o agregado no fim.
DUR=${1:-300}; PASSO=${2:-10}; N=$(nproc); HZ=$(getconf CLK_TCK)
le() { awk '/^cpu /{print $2+$3+$4+$7+$8, $9, $5+$6}' /proc/stat; }   # usado steal ocioso
read u0 s0 i0 < <(le); t0=$(date +%s.%N); ua=$u0; sa=$s0; ta=$t0
fim=$(( $(date +%s) + DUR )); max=0
while [ "$(date +%s)" -lt "$fim" ]; do
  sleep "$PASSO"
  read u s i < <(le); t=$(date +%s.%N)
  p=$(awk -v du=$((u-ua)) -v ds=$((s-sa)) -v dt="$(echo "$t - $ta" | bc)" -v n=$N -v hz=$HZ \
      'BEGIN{printf "%.1f %.1f", 100*du/(dt*n*hz), 100*ds/(dt*n*hz)}')
  echo "$(date -u +%T) usado=${p% *}% steal=${p#* }% nodes=$(pgrep -x node.real | wc -l) quota_kissat=$(cut -d' ' -f1 /sys/fs/cgroup/kissat_lim/cpu.max)"
  ua=$u; sa=$s; ta=$t
done
awk -v du=$((u-u0)) -v ds=$((s-s0)) -v dt="$(echo "$t - $t0" | bc)" -v n=$N -v hz=$HZ \
  'BEGIN{printf "AGREGADO %.0fs: usado=%.1f%% (%.2f de %d CPUs) steal=%.1f%%\n", dt, 100*du/(dt*n*hz), du/(dt*hz), n, 100*ds/(dt*n*hz)}'
