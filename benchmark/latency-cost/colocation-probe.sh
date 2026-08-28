#!/usr/bin/env bash
# colocation-probe.sh — mede latência de query dentro vs fora da janela de
# construction LLM, para testar em produção a predição central do paper de
# Stanford (arXiv 2606.06448): "construction é embedding/prefill-dominated e
# entra em tensão direta com tráfego de QA latency-sensitive quando co-locada
# no mesmo serving".
#
# POR QUE UM PROBE: o tráfego orgânico de query é ~6/hora. Uma janela de
# kg-build conteria ~12 queries — n insuficiente para comparar distribuições.
# O probe amostra em cadência fixa para dar n decente ao redor da janela.
#
# DESENHO: baseline (antes) → tratamento (durante kg-build) → recuperação
# (depois). Cada amostra registra se o kg-build estava ativo NAQUELE instante
# (via pgrep), então a atribuição não depende de adivinhar horários — o
# nightly pode atrasar e a análise continua correta.
#
# CUIDADOS (cada um é uma lição já paga):
#   - `?track=false` obrigatório: probe que alimenta ranking infla access_count
#     e contamina a salience que estamos medindo.
#   - Deadline de PAREDE, não contagem de iterações: um loop por contagem sai
#     com exit 0 tendo feito metade do trabalho se cada passo demorar mais que
#     o previsto.
#   - `curl -m` explícito: operação bloqueante sem timeout trava o loop inteiro.
#   - PATH completo: cron/systemd não herdam /sbin.
#   - loadavg gravado como covariável — sem ela, "latência subiu" confunde
#     efeito do kg-build com qualquer outra coisa pesada no host.
#   - As linhas que este probe gera em `provider_telemetry` são identificáveis
#     por timestamp: o JSONL guarda `ts_ms` de cada chamada, então a análise
#     casa ±1s e separa probe de tráfego orgânico de forma determinística.
#
# Uso:
#   ./colocation-probe.sh [--minutes N] [--interval S] [--out FILE]
# Saída: JSONL, uma linha por amostra.

export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
set -uo pipefail

MINUTES=240        # 4h: cobre baseline + janela + recuperação
INTERVAL=30        # amostra a cada 30s
PORT="${NOX_API_PORT:-18802}"
OUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --minutes)  MINUTES="$2"; shift 2 ;;
    --interval) INTERVAL="$2"; shift 2 ;;
    --out)      OUT="$2"; shift 2 ;;
    *) echo "opção desconhecida: $1" >&2; exit 1 ;;
  esac
done

mkdir -p /var/log/nox-mem
[[ -z "$OUT" ]] && OUT="/var/log/nox-mem/colocation-probe-$(date +%Y%m%d-%H%M).jsonl"

# Queries rotativas: repetir a mesma string mediria cache, não latência real.
QUERIES=(
  "custo do write path construction"
  "politica de retention e decay do grafo"
  "gate de diversidade do brief"
  "adjudicacao multi-modelo do painel"
  "telemetria de provider por fase"
  "snapshot pre-operacao e recovery"
  "cobertura de vetores e orfaos"
  "fallback chain remoto e local"
)

# Deadline via awk, não via $(( )): a aritmética do bash é só inteira e um
# --minutes fracionário (útil em smoke test) deixaria DEADLINE unbound sob set -u.
DEADLINE=$(awk -v n="$(date +%s)" -v m="$MINUTES" 'BEGIN{printf "%d", n + m*60}')
echo "[probe] out=$OUT deadline=$(date -d "@$DEADLINE" '+%H:%M:%S') interval=${INTERVAL}s" >&2

i=0
while [[ $(date +%s) -lt $DEADLINE ]]; do
  q="${QUERIES[$(( i % ${#QUERIES[@]} ))]}"

  # kg-build ativo NESTE instante? É o marcador de tratamento.
  if pgrep -f "index.js kg-build" >/dev/null 2>&1; then KG=1; else KG=0; fi
  # Qualquer phase do nightly rodando (construction/maintenance mais ampla).
  if pgrep -f "nightly-maintenance.sh" >/dev/null 2>&1; then NIGHTLY=1; else NIGHTLY=0; fi

  LOAD=$(awk '{print $1}' /proc/loadavg 2>/dev/null || echo "null")
  # %3N não truncou nesta build de date (saiu epoch+9 dígitos = ns), então corta
  # em 13 dígitos à mão. Isso precisa ser ms de verdade: é a chave que casa cada
  # amostra com sua linha em provider_telemetry.timestamp_ms.
  TS_NS=$(date +%s%N); TS_MS=${TS_NS:0:13}

  # -m 20: teto explícito. track=false: NUNCA alimentar o ranking com probe.
  T=$(curl -s -o /dev/null -m 20 \
        -w '%{time_total} %{http_code}' \
        --get "http://127.0.0.1:${PORT}/api/search" \
        --data-urlencode "q=${q}" \
        --data-urlencode "limit=5" \
        --data-urlencode "track=false" 2>/dev/null || echo "0 000")
  SECS=$(echo "$T" | awk '{print $1}')
  CODE=$(echo "$T" | awk '{print $2}')
  MS=$(awk -v s="$SECS" 'BEGIN{printf "%d", s*1000}')

  printf '{"ts_ms":%s,"iso":"%s","kg_build":%s,"nightly":%s,"load1":%s,"latency_ms":%s,"http":%s,"q":"%s"}\n' \
    "$TS_MS" "$(date -Is)" "$KG" "$NIGHTLY" "${LOAD:-null}" "$MS" "$CODE" "$q" >> "$OUT"

  i=$(( i + 1 ))
  # Dorme só o que sobra do intervalo, para a cadência não derivar com a
  # latência da própria chamada.
  SLEEP=$(awk -v iv="$INTERVAL" -v s="$SECS" 'BEGIN{d=iv-s; print (d>0)?d:0}')
  sleep "$SLEEP"
done

TOTAL=$(wc -l < "$OUT" | tr -d ' ')
# `grep -c` já devolve 0 quando não casa; o `|| echo 0` antigo somava um segundo
# zero e quebrava o sumário em duas linhas.
KGN=$(grep -c '"kg_build":1' "$OUT" 2>/dev/null | head -1)
ERRS=$(grep -vc '"http":200' "$OUT" 2>/dev/null | head -1)
echo "[probe] fim: $TOTAL amostras ($KGN durante kg-build, $ERRS não-200) → $OUT" >&2
