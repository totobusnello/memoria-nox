#!/usr/bin/env bash
# Teste hermetico das guardas do sprint-roda-sham-v2.sh (adaptado de testa-roda-sham.sh).
#
# O replay real e substituido por um stub que faz o que o PLANO mandar. Nada aqui toca
# banco, corpus, rede ou producao. Precisa de GNU-like `timeout`, `sha256sum`, `pgrep`
# e bash >= 4 (arrays associativos): roda na VPS de pesquisa, onde o job roda.
#
# Casos 1-5 sao os da v1, adaptados. 6-12 cobrem o que a v2 acrescenta: saida PARCIAL
# nao vira resultado, prazo de parede, sinal no orquestrador, instrumento que muda no
# meio, paralelismo <= 3, recusa a sobrescrever, e o leitor que so aceita CONCLUIDO.
# 13 e a MUTACAO: sem as guardas, os casos 2 e 6 tem de passar a falhar.
# 14 (2026-10-04) e o MODO COMPLETAR (SHAM_CORRIDAS + SHAM_JOB_REF): roda so a lista,
# herda o resto do job abortado e fecha as K+1; recusa lista que repete validada, lista
# que deixa buraco, instrumento diferente do de referencia e lista sem referencia.
set -uo pipefail
cd "$(dirname "$0")"

ALVO=$PWD/sprint-roda-sham-v2.sh
T=$(mktemp -d /var/tmp/testa-roda-sham-v2.XXXXXX 2>/dev/null || mktemp -d)
trap 'pkill -f "$T/stub-node" 2>/dev/null; rm -rf "$T"' EXIT
FALHAS=0

cat > "$T/stub-node" <<'STUB'
#!/usr/bin/env bash
d=""; out=""; tsf=""
while [ $# -gt 0 ]; do
  case "$1" in
    --designacao) d="$2"; shift 2;;
    --out) out="$2"; shift 2;;
    --so-ts-file) tsf="$2"; shift 2;;
    *) shift;;
  esac
done
n=$(basename "$d" .json)
case "$n" in SHAM-*) rot=$n;; *) rot=REAL;; esac
echo "$rot inicio $(date +%s.%N)" >> "$STUB_TRACO"
c=$(grep "^$rot=" "$STUB_PLANO" 2>/dev/null | cut -d= -f2)
N=$(grep -cv '^\s*$' "$tsf")
escreve() {  # $1 = numero de estados na saida
  printf '{"dose":{"estados":%s,"tabela":[{"w":4,"estados":%s},{"w":100000,"estados":%s}],"detalhe":[]}}\n' "$1" "$1" "$1" > "$out"
}
case "${c:-ok}" in
  timeout) sleep 30;;                    # o teto/prazo do orquestrador mata
  vazio)   exit 0;;                      # sai 0 e NAO escreve
  parcial) escreve $((N-1));;            # sai 0 com saida PARCIAL
  erro)    exit 3;;
  lento)   sleep 2; escreve "$N";;
  muta)    echo x >> "$STUB_MUTA"; escreve "$N";;
  *)       escreve "$N";;
esac
echo "$rot fim $(date +%s.%N)" >> "$STUB_TRACO"
STUB
chmod +x "$T/stub-node"

prepara() {   # $1 = numero de shams (default 3)
  local k=${1:-3} i
  rm -rf "$T/out" "$T/shams" "$T/raiz"; mkdir -p "$T/shams" "$T/raiz/dist/api" "$T/raiz/dist/paper2" "$T/raiz/src/api"
  for i in $(seq 0 $((k-1))); do printf '{"designados":{}}' > "$T/shams/SHAM-$(printf %03d "$i").json"; done
  for f in dist/api/brief.js dist/api/brief-diversity.js dist/paper2/brief-outcome.js src/api/brief.ts; do echo "// $f" > "$T/raiz/$f"; done
  printf '{"designados":{}}' > "$T/desig-real.json"
  printf '2026-09-12T09:22:02.000Z\n2026-09-12T09:37:02.000Z\n' > "$T/ts.txt"
  echo corpus > "$T/corpus.db"; echo vivo > "$T/vivo.db"; echo log > "$T/log.ndjson"
  : > "$T/excluir.txt"; : > "$T/plano"; : > "$T/traco"
  K=$k
}

roda_alvo() {   # $1 = script ; extra env via ENV_EXTRA
  env SHAM_TETO_S="${TETO:-10}" SHAM_PRAZO_S="${PRAZO:-60}" SHAM_TS_FILE="$T/ts.txt" SHAM_ESTADOS_ESPERADOS=2 \
      SHAM_REPLAY="$T/replay.mjs" SHAM_RAIZ="$T/raiz" SHAM_CORPUS="$T/corpus.db" SHAM_VIVO="$T/vivo.db" \
      SHAM_OUT="${OUT_DIR:-$T/out}" SHAM_CORRIDAS="${CORR:-}" SHAM_JOB_REF="${JREF:-}" SHAM_DESIG_REAL="$T/desig-real.json" SHAM_DIR="$T/shams" SHAM_LOG_CAMPO="$T/log.ndjson" \
      SHAM_EXCLUIR="$T/excluir.txt" SHAM_TMP_BASE="$T/tmp" SHAM_NODE="$T/stub-node" SHAM_NICE= \
      SHAM_PARALELO="${PAR:-1}" SHAM_K_ESPERADO="$K" SHAM_AMOSTRA_S=1 \
      STUB_PLANO="$T/plano" STUB_TRACO="$T/traco" STUB_MUTA="${MUTA:-/dev/null}" \
      bash "$1" > "$T/saida.txt" 2>&1
  echo $?
}
echo '// replay' > "$T/replay.mjs"

ok() { printf '  ok    %s\n' "$1"; }
falha() { printf '  FALHA %s\n        %s\n' "$1" "${2:-}"; FALHAS=$((FALHAS+1)); }
validadas() { ls "$T/out/runs/"*.json 2>/dev/null | grep -vc '\.tmp\.json$'; }
status() { cut -d' ' -f1 "$T/out/STATUS" 2>/dev/null; }

echo "== 1. sem SHAM_TETO_S / SHAM_PRAZO_S o script recusa =="
prepara
rc=$(SHAM_OUT="$T/out" bash "$ALVO" > "$T/saida.txt" 2>&1; echo $?)
rc2=$(SHAM_TETO_S=5 SHAM_OUT="$T/out" bash "$ALVO" > "$T/saida2.txt" 2>&1; echo $?)
if [ "$rc" != 0 ] && grep -q SHAM_TETO_S "$T/saida.txt" && [ "$rc2" != 0 ] && grep -q SHAM_PRAZO_S "$T/saida2.txt"; then
  ok "recusou sem teto (rc=$rc) e sem prazo (rc=$rc2)"
else falha "aceitou rodar sem teto/prazo" "rc=$rc rc2=$rc2"; fi

echo "== 2. REAL em 124 PARA o script; nenhum sham roda =="
prepara; echo "REAL=timeout" > "$T/plano"
rc=$(TETO=2 roda_alvo "$ALVO")
n_sham=$(ls "$T/out/runs/"SHAM-*.log 2>/dev/null | wc -l | tr -d ' ')
if [ "$rc" != 0 ] && grep -q "^ABORTADO" "$T/out/RECIBO.txt" && [ "$n_sham" = 0 ] && [ "$(status)" = ABORTADO ] \
   && grep -q "REAL saiu exit=124" "$T/out/RECIBO.txt"; then
  ok "parou no REAL (exit 124 do timeout real), 0 shams, STATUS=ABORTADO"
else falha "seguiu depois do REAL falhar" "rc=$rc shams=$n_sham status=$(status)"; fi

echo "== 3. REAL sai 0 mas SEM saida tambem para =="
prepara; echo "REAL=vazio" > "$T/plano"
rc=$(roda_alvo "$ALVO")
if [ "$rc" != 0 ] && grep -q "sem-saida" "$T/out/RECIBO.txt" && [ "$(status)" = ABORTADO ]; then
  ok "exit 0 sem .json nao passa por sucesso"
else falha "aceitou REAL sem saida" "rc=$rc"; fi

echo "== 4. um sham em 124 para o conjunto (sequencial) =="
prepara; printf 'SHAM-001=timeout\n' > "$T/plano"
rc=$(TETO=2 roda_alvo "$ALVO")
if [ "$rc" != 0 ] && grep -q "SHAM-001 exit=124" "$T/out/RECIBO.txt" && ! grep -q "SHAM-002 lancada" "$T/out/RECIBO.txt" \
   && [ ! -e "$T/out/CONCLUIDO" ]; then
  ok "parou na SHAM-001, nao lancou a 002, sem CONCLUIDO"
else falha "distribuicao nula incompleta passaria" "rc=$rc"; fi

echo "== 5. caminho feliz fecha com contagem, CONCLUIDO e hashes =="
prepara
rc=$(roda_alvo "$ALVO")
if [ "$rc" = 0 ] && [ "$(validadas)" = 4 ] && grep -q "^fim" "$T/out/RECIBO.txt" && [ "$(status)" = CONCLUIDO ] \
   && [ "$(wc -l < "$T/out/CONCLUIDO" | tr -d ' ')" = 4 ] && (cd "$T/out/runs" && sha256sum --quiet -c ../CONCLUIDO); then
  ok "4 saidas validadas (REAL + 3), STATUS=CONCLUIDO, CONCLUIDO confere"
else falha "caminho feliz nao fechou" "rc=$rc validadas=$(validadas) status=$(status)"; fi

echo "== 6. saida PARCIAL (estados < esperado) NAO vira resultado =="
prepara; printf 'SHAM-001=parcial\n' > "$T/plano"
rc=$(roda_alvo "$ALVO")
if [ "$rc" != 0 ] && grep -q "SHAM-001 saida invalida" "$T/out/RECIBO.txt" && [ ! -e "$T/out/runs/SHAM-001.json" ] \
   && [ ! -e "$T/out/CONCLUIDO" ] && [ "$(status)" = ABORTADO ]; then
  ok "parcial rejeitada: sem runs/SHAM-001.json, sem CONCLUIDO, STATUS=ABORTADO"
else falha "saida parcial passou por resultado" "rc=$rc status=$(status)"; fi

echo "== 7. prazo de parede corta e o corte e ABORTADO, nao resultado =="
prepara; printf 'SHAM-000=timeout\n' > "$T/plano"
rc=$(TETO=30 PRAZO=15 roda_alvo "$ALVO")   # 15 s, nao 3: sob o throttling de 2026-10-04 o stub do REAL levou 3 s e o prazo vencia ANTES de lancar a SHAM-000 (guarda certa, caso errado)
if [ "$rc" != 0 ] && grep -q "SHAM-000 saiu exit=124" "$T/out/RECIBO.txt" && [ "$(status)" = ABORTADO ] \
   && [ ! -e "$T/out/CONCLUIDO" ]; then
  ok "teto efetivo = prazo restante; 124 -> ABORTADO"
else falha "prazo nao cortou ou corte virou resultado" "rc=$rc status=$(status)"; fi

echo "== 8. SIGTERM no orquestrador: mata o que esta em curso e marca ABORTADO =="
prepara; printf 'SHAM-000=timeout\n' > "$T/plano"
( TETO=30 PRAZO=60 roda_alvo "$ALVO" > "$T/rc8" ) &
bgp=$!
for _ in $(seq 1 50); do grep -q "SHAM-000 inicio" "$T/traco" 2>/dev/null && break; sleep 0.2; done
orq=$(pgrep -f "bash $ALVO" | head -1)
kill -TERM "$orq" 2>/dev/null; wait "$bgp" 2>/dev/null
sleep 1
vivo=$(pgrep -f "$T/stub-node" | wc -l | tr -d ' ')
if [ "$(status)" = ABORTADO ] && grep -q "INTERROMPIDA" "$T/out/RECIBO.txt" && [ "$vivo" = 0 ] && [ ! -e "$T/out/runs/SHAM-000.json" ]; then
  ok "sinal -> ABORTADO, corrida em curso morta e marcada NAO MEDIDA"
else falha "sinal deixou estado ambiguo" "status=$(status) stubs_vivos=$vivo"; fi

echo "== 9. instrumento que muda no meio aborta antes da proxima corrida =="
prepara; printf 'SHAM-000=muta\n' > "$T/plano"
rc=$(MUTA="$T/shams/SHAM-002.json" roda_alvo "$ALVO")
if [ "$rc" != 0 ] && grep -q "instrumento mudou antes de lancar SHAM-001" "$T/out/RECIBO.txt"; then
  ok "drift de instrumento detectado antes de gastar CPU"
else falha "rodou com instrumento alterado" "rc=$rc"; fi

echo "== 10. paralelismo: 3 em curso no maximo; 4 recusado =="
prepara 6; printf 'SHAM-000=lento\nSHAM-001=lento\nSHAM-002=lento\nSHAM-003=lento\nSHAM-004=lento\nSHAM-005=lento\n' > "$T/plano"
rc=$(PAR=3 roda_alvo "$ALVO")
maxc=$(python3 - "$T/traco" <<'PY'
import sys
ev=[]
for l in open(sys.argv[1]):
    r,k,t=l.split(); ev.append((float(t), 1 if k=="inicio" else -1))
c=m=0
for _,d in sorted(ev): c+=d; m=max(m,c)
print(m)
PY
)
rc4=$(PAR=4 roda_alvo "$ALVO")
if [ "$rc" = 0 ] && [ "$(validadas)" = 7 ] && [ "$maxc" -le 3 ] && [ "$maxc" -ge 2 ] && [ "$rc4" != 0 ] && grep -q "recusado" "$T/saida.txt"; then
  ok "7 validadas com concorrencia maxima $maxc (<=3); PARALELO=4 recusado"
else falha "paralelismo fora do limite" "rc=$rc validadas=$(validadas) max=$maxc rc4=$rc4"; fi

echo "== 11. recusa sobrescrever um OUT que ja tem RECIBO =="
prepara; rc=$(roda_alvo "$ALVO"); rc2=$(roda_alvo "$ALVO")
if [ "$rc" = 0 ] && [ "$rc2" != 0 ] && grep -q "recuso sobrescrever" "$T/saida.txt" && [ "$(status)" = CONCLUIDO ]; then
  ok "segunda corrida no mesmo OUT recusada; o CONCLUIDO anterior ficou intacto"
else falha "sobrescreveu resultado anterior" "rc=$rc rc2=$rc2"; fi

echo "== 12. leitor: so CONCLUIDO conta (SIGKILL deixa RODANDO e nenhum CONCLUIDO) =="
prepara; printf 'SHAM-000=timeout\n' > "$T/plano"
( TETO=30 PRAZO=60 roda_alvo "$ALVO" > /dev/null ) &
bgp=$!
for _ in $(seq 1 50); do grep -q "SHAM-000 inicio" "$T/traco" 2>/dev/null && break; sleep 0.2; done
orq=$(pgrep -f "bash $ALVO" | head -1); kill -KILL "$orq" 2>/dev/null; wait "$bgp" 2>/dev/null
pkill -f "$T/stub-node" 2>/dev/null; sleep 0.5
if [ "$(status)" = RODANDO ] && [ ! -e "$T/out/CONCLUIDO" ] && [ "$(validadas)" = 1 ]; then
  ok "SIGKILL: STATUS=RODANDO (heartbeat para), sem CONCLUIDO, 1/4 validada — o leitor trata como INCOMPLETO"
else falha "SIGKILL produziu algo que se le como fim" "status=$(status) validadas=$(validadas)"; fi

echo "== 13. MUTACAO: sem as guardas, os casos 2 e 6 tem de FALHAR =="
sed -e '/\[ "\$rc" != 0 \]; then/,/^  fi$/d' \
    -e '/sem-saida"$/d' \
    -e '/\[ "\$motivo" = ok \] || aborta/d' \
    -e '/REAL sem saida validada/d' "$ALVO" > "$T/mutante.sh"
if diff -q "$ALVO" "$T/mutante.sh" >/dev/null; then
  falha "a mutacao nao alterou nada — o sed nao casou as guardas" ""
else
  prepara; echo "REAL=timeout" > "$T/plano"
  rc=$(TETO=2 roda_alvo "$T/mutante.sh"); n2=$(ls "$T/out/runs/"SHAM-*.log 2>/dev/null | wc -l | tr -d ' ')
  prepara; printf 'SHAM-001=parcial\n' > "$T/plano"
  rc6=$(roda_alvo "$T/mutante.sh")
  if [ "$n2" -gt 0 ] && [ -e "$T/out/runs/SHAM-001.json" ]; then
    ok "mutante seguiu apos o REAL falhar ($n2 shams) e promoveu a parcial — o teste tem poder"
  else falha "mutante tambem parou: os casos 2/6 nao provam as guardas" "shams=$n2 rc6=$rc6"; fi
fi

echo "== 14. MODO COMPLETAR: lista de corridas sobre um job abortado =="
prepara; printf 'SHAM-001=timeout\n' > "$T/plano"
rc1=$(TETO=2 roda_alvo "$ALVO")      # job 1 aborta: REAL e SHAM-000 validadas, 001 em 124, 002 nunca
: > "$T/plano"; : > "$T/traco"
rcA=$(OUT_DIR="$T/c-sem-ref" CORR="SHAM-001 SHAM-002" roda_alvo "$ALVO"); okA=$(grep -c "exige SHAM_JOB_REF" "$T/c-sem-ref/RECIBO.txt")
rcB=$(OUT_DIR="$T/c-repete" CORR="SHAM-000 SHAM-001 SHAM-002" JREF="$T/out" roda_alvo "$ALVO"); okB=$(grep -c "SHAM-000 ja esta validada" "$T/c-repete/RECIBO.txt")
rcC=$(OUT_DIR="$T/c-buraco" CORR="SHAM-001" JREF="$T/out" roda_alvo "$ALVO"); okC=$(grep -c "SHAM-002 nem pedida nem validada" "$T/c-buraco/RECIBO.txt")
nB=$(grep -c . "$T/traco")    # nenhum dos tres recusados pode ter gasto CPU
cp "$T/shams/SHAM-002.json" "$T/sham2.bak"; echo ' ' >> "$T/shams/SHAM-002.json"
rcD=$(OUT_DIR="$T/c-instr" CORR="SHAM-001 SHAM-002" JREF="$T/out" roda_alvo "$ALVO"); okD=$(grep -c "instrumento difere" "$T/c-instr/RECIBO.txt")
cp "$T/sham2.bak" "$T/shams/SHAM-002.json"; : > "$T/traco"
rcE=$(OUT_DIR="$T/c-ok" CORR="SHAM-001 SHAM-002" JREF="$T/out" roda_alvo "$ALVO")
rodou=$(awk '$2=="inicio"{print $1}' "$T/traco" | sort | tr '\n' ' ')
nconc=$(wc -l < "$T/c-ok/CONCLUIDO" 2>/dev/null | tr -d ' ')
if [ "$rc1" != 0 ] && [ "$rcA" != 0 ] && [ "$okA" -ge 1 ] && [ "$rcB" != 0 ] && [ "$okB" = 1 ] \
   && [ "$rcC" != 0 ] && [ "$okC" = 1 ] && [ "$nB" = 0 ] && [ "$rcD" != 0 ] && [ "$okD" = 1 ] \
   && [ "$rcE" = 0 ] && [ "$rodou" = "SHAM-001 SHAM-002 " ] && [ "$(cut -d' ' -f1 "$T/c-ok/STATUS")" = CONCLUIDO ] \
   && [ "$nconc" = 4 ] && (cd "$T/c-ok/runs" && sha256sum --quiet -c ../CONCLUIDO) \
   && cmp -s "$T/out/runs/REAL.json" "$T/c-ok/runs/REAL.json" && [ "$(grep -c HERDADA "$T/c-ok/RECIBO.txt")" = 2 ]; then
  ok "completou so SHAM-001/002 (REAL e 000 herdadas por hash), CONCLUIDO com 4; recusou sem ref, repetida, buraco e instrumento alterado sem gastar CPU"
else falha "modo completar" "rc1=$rc1 A=$rcA/$okA B=$rcB/$okB C=$rcC/$okC nB=$nB D=$rcD/$okD E=$rcE rodou='$rodou' nconc=$nconc"; fi

echo
printf 'falhas: %s\n' "$FALHAS"
exit "$FALHAS"
