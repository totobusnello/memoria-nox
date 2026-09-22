#!/usr/bin/env bash
# Teste hermetico das guardas do roda-sham.sh.
#
# Existe porque a versao anterior do roda-sham.sh PROMETIA no comentario
# ("se o REAL falhar nada do resto vale") o que nao implementava, e a promessa
# so ficou visivel depois de 12 horas de CPU e zero medidas. Uma guarda sem
# teste e uma frase.
#
# O replay real e substituido por um stub que sai com o codigo que o PLANO
# mandar. Nada aqui toca a VPS, o corpus ou a rede.
#
# O ultimo caso e uma MUTACAO: remove as guardas do script e exige que o teste
# passe a falhar. Um teste que passa com e sem a correcao nao esta a testar a
# correcao.
set -uo pipefail
cd "$(dirname "$0")"

ALVO=$PWD/roda-sham.sh
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
FALHAS=0

cat > "$T/stub-node" <<'STUB'
#!/usr/bin/env bash
d=""; out=""
while [ $# -gt 0 ]; do
  case "$1" in
    --designacao) d="$2"; shift 2;;
    --out) out="$2"; shift 2;;
    *) shift;;
  esac
done
n=$(basename "$d" .json)
case "$n" in SHAM-*) rot=$n;; *) rot=REAL;; esac
c=$(grep "^$rot=" "$STUB_PLANO" 2>/dev/null | cut -d= -f2)
case "${c:-ok}" in
  timeout) exit 124;;
  vazio)   exit 0;;            # sai 0 e NAO escreve a saida
  *)       printf '{"stub":true}\n' > "$out"; exit 0;;
esac
STUB
chmod +x "$T/stub-node"

# cenario: 3 shams, uma designacao real
prepara() {
  rm -rf "$T/out" "$T/shams"; mkdir -p "$T/out" "$T/shams"
  for i in 000 001 002; do printf '[]' > "$T/shams/SHAM-$i.json"; done
  printf '[]' > "$T/desig-real.json"
  : > "$T/excluir.txt"
  : > "$T/plano"
}

roda_alvo() {   # $1 = script a exercitar (alvo ou mutante)
  SHAM_TETO_S=5 \
  SHAM_REPLAY=/dev/null \
  SHAM_OUT="$T/out" \
  SHAM_DESIG_REAL="$T/desig-real.json" \
  SHAM_DIR="$T/shams" \
  SHAM_NODE="$T/stub-node" \
  SHAM_NICE= \
  SHAM_EXCLUIR="$T/excluir.txt" \
  SHAM_LOG_CAMPO=/dev/null \
  STUB_PLANO="$T/plano" \
  bash "$1" > "$T/saida.txt" 2>&1
  echo $?
}

ok() { printf '  ok   %s\n' "$1"; }
falha() { printf '  FALHA %s\n  %s\n' "$1" "${2:-}"; FALHAS=$((FALHAS+1)); }

echo "== 1. sem SHAM_TETO_S o script recusa =="
prepara
rc=$(SHAM_OUT="$T/out" bash "$ALVO" > "$T/saida.txt" 2>&1; echo $?)
if [ "$rc" != 0 ] && grep -q "SHAM_TETO_S" "$T/saida.txt"; then
  ok "recusou sem teto (rc=$rc)"
else
  falha "aceitou rodar sem teto declarado" "rc=$rc"
fi

echo "== 2. REAL em 124 PARA o script; nenhum sham roda =="
prepara; echo "REAL=timeout" > "$T/plano"
rc=$(roda_alvo "$ALVO")
n_sham=$(ls "$T/out"/SHAM-*.log 2>/dev/null | wc -l | tr -d ' ')
if [ "$rc" != 0 ] && grep -q "^ABORTADO" "$T/out/RECIBO.txt" && [ "$n_sham" = 0 ]; then
  ok "parou no REAL, 0 shams rodados"
else
  falha "seguiu depois do REAL falhar" "rc=$rc shams_rodados=$n_sham"
fi

echo "== 3. REAL sai 0 mas SEM saida tambem para =="
prepara; echo "REAL=vazio" > "$T/plano"
rc=$(roda_alvo "$ALVO")
if [ "$rc" != 0 ] && grep -q "sem-saida" "$T/out/RECIBO.txt"; then
  ok "exit 0 sem .json nao passa por sucesso"
else
  falha "aceitou REAL sem saida" "rc=$rc"
fi

echo "== 4. um sham em 124 para o conjunto =="
prepara; printf 'REAL=ok\nSHAM-001=timeout\n' > "$T/plano"
rc=$(roda_alvo "$ALVO")
if [ "$rc" != 0 ] && grep -q "^ABORTADO" "$T/out/RECIBO.txt" \
   && grep -q "SHAM-001 exit=124" "$T/out/RECIBO.txt" \
   && ! grep -q "SHAM-002 exit" "$T/out/RECIBO.txt"; then
  ok "parou na SHAM-001, nao correu a 002"
else
  falha "distribuicao nula incompleta passaria" "rc=$rc"
fi

echo "== 5. caminho feliz fecha com contagem =="
prepara; echo "REAL=ok" > "$T/plano"
rc=$(roda_alvo "$ALVO")
n_json=$(ls "$T/out"/*.json 2>/dev/null | wc -l | tr -d ' ')
if [ "$rc" = 0 ] && grep -q "^fim" "$T/out/RECIBO.txt" && [ "$n_json" = 4 ]; then
  ok "4 saidas (REAL + 3 shams), recibo fechado"
else
  falha "caminho feliz nao fechou" "rc=$rc jsons=$n_json"
fi

echo "== 6. as duas guardas do REAL sao REDUNDANTES de proposito =="
# Remover SO a guarda de exit nao muda o caso 2: um 124 tambem nao escreve
# .json, logo a segunda guarda apanha-o. A redundancia e deliberada — uma
# corrida pode sair !=0 DEPOIS de escrever saida parcial, e ai so a guarda de
# exit a apanha. Este caso documenta isso; o 7 e que prova o poder do teste.
sed -e 's/ || para REAL "\$?"//' -e 's/ || para "\$n" "\$?"//' "$ALVO" > "$T/meio-mutante.sh"
prepara; echo "REAL=timeout" > "$T/plano"
rc=$(roda_alvo "$T/meio-mutante.sh")
n_sham=$(ls "$T/out"/SHAM-*.log 2>/dev/null | wc -l | tr -d ' ')
if [ "$n_sham" = 0 ] && grep -q "sem-saida" "$T/out/RECIBO.txt"; then
  ok "sem a guarda de exit, a de saida ainda para (por 'sem-saida')"
else
  falha "removida uma guarda, as duas classes passaram" "shams=$n_sham"
fi

echo "== 7. MUTACAO: sem NENHUMA guarda, o caso 2 tem de FALHAR =="
sed -e 's/ || para REAL "\$?"//' -e 's/ || para "\$n" "\$?"//' \
    -e '/^\[ -s "\$OUT\/REAL.json" \]/d' \
    -e '/^  \[ -s "\$OUT\/\$n.json" \]/d' "$ALVO" > "$T/mutante.sh"
if diff -q "$ALVO" "$T/mutante.sh" >/dev/null; then
  falha "a mutacao nao alterou nada — o sed nao casou as guardas" ""
else
  prepara; echo "REAL=timeout" > "$T/plano"
  rc=$(roda_alvo "$T/mutante.sh")
  n_sham=$(ls "$T/out"/SHAM-*.log 2>/dev/null | wc -l | tr -d ' ')
  if [ "$n_sham" -gt 0 ]; then
    ok "mutante seguiu apos o REAL falhar ($n_sham shams) — o teste tem poder"
  else
    falha "mutante tambem parou: o caso 2 nao prova a guarda" "shams=$n_sham"
  fi
fi

echo
printf 'falhas: %s\n' "$FALHAS"
exit "$FALHAS"
