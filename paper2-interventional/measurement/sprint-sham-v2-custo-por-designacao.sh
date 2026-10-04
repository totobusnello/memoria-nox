#!/usr/bin/env bash
# sprint-sham-v2-custo-por-designacao.sh — hipótese (b) do diagnóstico do aborto do sham v2
# (SHAM-012 exit=124, 2026-10-04T10:04Z): o custo depende da designação?
#
# Roda o MESMO replay, com os MESMOS argumentos do runner (`sprint-roda-sham-v2.sh`), numa
# amostra fixa de estados, SEQUENCIALMENTE, para várias designações, e mede o custo em
# INSTRUÇÕES (perf, `instructions:u` + `instructions:k`) além de parede e CPU do processo.
#
# Por que instruções e não CPU: neste guest (`CONFIG_PARAVIRT_TIME_ACCOUNTING` desligado,
# `VIRT_CPU_ACCOUNTING_GEN`) o tempo de CPU do PROCESSO inclui o tempo roubado pelo
# hipervisor (steal). Medido em 2026-10-04 10:31Z: um kissat acumulou 1010 ticks em 10 s
# enquanto /proc/stat dava ao host inteiro 398 ticks de nice e 4250 de steal. Logo
# "cpu ≈ parede" NÃO prova "sem espera": sob throttling as duas crescem juntas. Instruções
# retiradas são o trabalho, independente de steal; ciclos:u/k são o CPU REAL recebido.
#
# Não lê resultado de designado-vs-sham: só confere que a saída cobre os estados pedidos
# (contagem) e descarta o resto. Não altera nada do job; escreve só em $SAIDA.
#
# Uso (na VPS de pesquisa): bash sprint-sham-v2-custo-por-designacao.sh [N_ESTADOS] [rotulos...]
#   default: 50 estados (1 a cada 53 linhas de cal/ts-w4.txt) e REAL SHAM-012 SHAM-000 REAL
set -uo pipefail
W=${SHAM_W:-/var/tmp/sprint-sham-v2-w}
SAIDA=${SAIDA:-$W/diag-b}
N=${1:-50}; shift || true
ROTULOS=("$@"); [ "${#ROTULOS[@]}" -gt 0 ] || ROTULOS=(REAL SHAM-012 SHAM-000 REAL)
mkdir -p "$SAIDA" "$W/tmp-diag"
TOTAL=$(grep -cv '^\s*$' "$W/cal/ts-w4.txt")
PASSO=$(( TOTAL / N ))
awk -v p="$PASSO" -v n="$N" 'NF && (NR-1)%p==0 && c<n {print; c++}' "$W/cal/ts-w4.txt" > "$SAIDA/ts-amostra.txt"
NA=$(wc -l < "$SAIDA/ts-amostra.txt")
echo "amostra: $NA estados (passo $PASSO de $TOTAL) sha=$(sha256sum "$SAIDA/ts-amostra.txt" | cut -c1-16)" | tee "$SAIDA/RESUMO.txt"

stat_cpu() { awk '/^cpu /{print $2+$3+$4, $9}' /proc/stat; }   # busy(user+nice+sys) steal, em ticks
i=0
for rot in "${ROTULOS[@]}"; do
  i=$((i+1))
  if [ "$rot" = REAL ]; then D=$W/in/DESIGNATION-2026-08-26.json; else D=$W/shams-impulsionavel/$rot.json; fi
  SHA=$(sha256sum "$D" | cut -d' ' -f1)
  P="$SAIDA/$i-$rot"
  read -r b0 s0 < <(stat_cpu); t0=$(date +%s.%N)
  perf stat -x, -o "$P.perf" -e instructions:u,instructions:k,cycles:u,cycles:k,task-clock \
    /usr/bin/time -v -o "$P.time" nice -n 10 node "$W/raiz/replay-oportunidade.mjs" --modo dose --raiz "$W/raiz" \
      --corpus "$W/db/corpus-SERVING-REAL-e20260903-recuperado.db" --vivo "$W/db/vivo-v2.db" --corte rowid \
      --t-ref 2026-09-01T00:00:00Z --excluir-briefs "$W/in/excluir-vazio.txt" --log-campo "$W/in/p2-serving.ndjson" \
      --so-ts-file "$SAIDA/ts-amostra.txt" --w 4 --w 100000 --designacao "$D" --designacao-sha256 "$SHA" \
      --tmp-base "$W/tmp-diag" --sem-assert --out "$P.json" > "$P.stdout" 2> "$P.stderr"
  rc=$?
  t1=$(date +%s.%N); read -r b1 s1 < <(stat_cpu)
  est=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1]))['dose']; print(d.get('estados'), sum(1 for x in d.get('detalhe',[]) if x.get('erro')))" "$P.json" 2>/dev/null || echo "? ?")
  python3 - "$P" "$rot" "$rc" "$t0" "$t1" "$b0" "$b1" "$s0" "$s1" "$NA" "$est" <<'PY' | tee -a "$SAIDA/RESUMO.txt"
import sys, csv
P, rot, rc, t0, t1, b0, b1, s0, s1, na = sys.argv[1:11]
est, err = sys.argv[11].split()
v = {}
for row in csv.reader(open(P + ".perf")):
    if len(row) > 3 and row[0] and not row[0].startswith("#"):
        try: v[row[2]] = float(row[0])
        except ValueError: pass
tm = {}
for l in open(P + ".time"):
    k, _, val = l.strip().partition(": ")
    tm[k] = val
parede = float(t1) - float(t0)
n = int(na)
iu, ik = v.get("instructions:u", 0), v.get("instructions:k", 0)
cu, ck = v.get("cycles:u", 0), v.get("cycles:k", 0)
print(f"{rot:9s} rc={rc} estados={est}/{n} erros={err} parede={parede:8.1f}s "
      f"proc_cpu={float(tm.get('User time (seconds)',0))+float(tm.get('System time (seconds)',0)):8.1f}s "
      f"instr_u={iu/1e9:8.2f}G instr_k={ik/1e9:7.2f}G ciclos_reais={(cu+ck)/3.25e9:7.1f}s@3.25GHz "
      f"host_busy={(int(b1)-int(b0))/100:7.1f}s host_steal={(int(s1)-int(s0))/100:7.1f}s "
      f"rss_max={int(tm.get('Maximum resident set size (kbytes)',0))//1024}MB")
PY
done
rm -rf "$W/tmp-diag"
echo "fim $(date -u +%FT%TZ)" >> "$SAIDA/RESUMO.txt"
