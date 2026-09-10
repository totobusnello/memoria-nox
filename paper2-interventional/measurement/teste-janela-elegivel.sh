#!/bin/bash
# Prende os invariantes do `janela-elegivel.py` que a errata de 2026-09-10 criou.
#
# ⚠️ O defeito consertado NÃO era um valor errado: era uma classe atribuída na AUSÊNCIA
# do dado (`2026-09-02` = `inteiro, 24.0 h` com 0 briefs servidos). Logo os invariantes
# que importam são de fail-closed, e cada um tem par sim/nao — prever qual mutante mata
# qual caso é hipótese, e é a mutação que a testa.
set -uo pipefail
cd "$(dirname "$0")"
SCRIPT=janela-elegivel.py
CENSO=out/CENSO-SERVIDO-2026-09-10.json
TMP="$(mktemp -d "${TMPDIR:-/tmp}/tje.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
ok=0; ruim=0
val() { if [ "$2" = "$3" ]; then echo "  ok   $1"; ok=$((ok+1));
        else echo "  RUIM $1 -> esperado=[$3] obtido=[$2]"; ruim=$((ruim+1)); fi; }

J="$TMP/j.json"
P2_CENSO="$CENSO" python3 "$SCRIPT" > "$J" 2>"$TMP/err" || { echo "RED corrida-base-falhou"; cat "$TMP/err"; exit 1; }
q() { python3 -c "import json,sys;d=json.load(open('$J'));print($1)"; }

# T1-T5: o estado medido, e o 09-02 é o caso que prova (ausente do censo)
val "T1 09-02 e' unidade VAZIA" \
  "$(q "[e['unidade'] for e in d['epochs'] if e['epoch']=='2026-09-02'][0]")" "vazia"
val "T2 09-02 tem servidos=0" \
  "$(q "[e['servidos'] for e in d['epochs'] if e['epoch']=='2026-09-02'][0]")" "0"
val "T3 09-02 tem classe_janela=inteiro (o relogio SEMPRE disse inteiro)" \
  "$(q "[e['classe_janela'] for e in d['epochs'] if e['epoch']=='2026-09-02'][0]")" "inteiro"
val "T4 09-03 e' parcial SO por VOLUME (relogio inteiro)" \
  "$(q "[x['motivos'] for x in d['unidades_de_analise']['parciais'] if x['epoch']=='2026-09-03'][0]")" "['volume']"
val "T5 09-01 e' parcial por relogio E por volume, nunca por um so" \
  "$(q "'relogio' in [x['motivos'] for x in d['unidades_de_analise']['parciais'] if x['epoch']=='2026-09-01'][0]")" "True"

# T6: nenhuma unidade inteira pode ter servidos < esperado. É a invariante central.
val "T6 toda unidade INTEIRA tem servidos>=esperado" \
  "$(q "all(e['servidos']>=e['esperado'] for e in d['epochs'] if e['unidade']=='inteira')")" "True"

# T7: o artefato carrega a procedência do censo (sem ela é transcrição)
val "T7 artefato traz log_sha256 do censo" \
  "$(q "len(d['censo_de_entrega']['log_sha256'])")" "64"
val "T8 artefato traz a semantica do censo" \
  "$(q "'briefs-REGISTRADOS' in d['censo_de_entrega']['semantica']")" "True"

# T9: epoch cujo fim ainda nao chegou e' em_curso, nao parcial
val "T9 epoch de hoje e' em_curso" \
  "$(q "len(d['unidades_de_analise']['em_curso'])>=0 and all(e['unidade']!='parcial' for e in d['epochs'] if e['unidade']=='em_curso')")" "True"

# T10: FAIL-CLOSED — sem censo o script aborta em vez de classificar
if P2_CENSO="$TMP/nao-existe.json" python3 "$SCRIPT" >/dev/null 2>"$TMP/e10"; then
  echo "  RUIM T10 rodou SEM censo (deveria abortar)"; ruim=$((ruim+1))
else
  grep -q "RED censo-de-entrega-ausente" "$TMP/e10" && { echo "  ok   T10 aborta sem censo"; ok=$((ok+1)); } \
    || { echo "  RUIM T10 abortou por outro motivo: $(head -1 "$TMP/e10")"; ruim=$((ruim+1)); }
fi

# T11: censo com chave divergente e' recusado
python3 -c "
import json;d=json.load(open('$CENSO'));d['divergencia_campo_vs_ts']=7
json.dump(d,open('$TMP/div.json','w'))"
if P2_CENSO="$TMP/div.json" python3 "$SCRIPT" >/dev/null 2>"$TMP/e11"; then
  echo "  RUIM T11 aceitou censo divergente"; ruim=$((ruim+1))
else
  grep -q "censo-com-chave-de-epoch-divergente" "$TMP/e11" && { echo "  ok   T11 recusa censo divergente"; ok=$((ok+1)); } \
    || { echo "  RUIM T11 abortou por outro motivo"; ruim=$((ruim+1)); }
fi

# T12-T15: a perna de ENTREGA no unico epoch de modo MISTO. Ela nao aparece em
# `unidade` porque o relogio ja decide `parcial` — perna correta encoberta por outra
# perna correta nao tem teste que a alcance, entao asserta-se o campo direto.
val "T12 09-01 classe_entrega=parcial (630 active, nao 672 total)" \
  "$(q "[e['classe_entrega'] for e in d['epochs'] if e['epoch']=='2026-09-01'][0]")" "parcial"
val "T13 09-01 servidos conta so o active" \
  "$(q "[e['servidos'] for e in d['epochs'] if e['epoch']=='2026-09-01'][0]")" "630"
val "T14 09-01 preserva o total separado" \
  "$(q "[e['servidos_total'] for e in d['epochs'] if e['epoch']=='2026-09-01'][0]")" "672"
val "T15 09-01 e' o UNICO de modo misto" \
  "$(q "[x['epoch'] for x in d['unidades_de_analise']['modo_misto']]")" "['2026-09-01']"
val "T16 09-01 e' parcial pelas DUAS pernas" \
  "$(q "[x['motivos'] for x in d['unidades_de_analise']['parciais'] if x['epoch']=='2026-09-01'][0]")" "['relogio', 'volume']"

# T17: censo com registro sem `modo` e' recusado (impede separar active de shadow)
python3 -c "
import json;d=json.load(open('$CENSO'));d['sem_modo']=3
json.dump(d,open('$TMP/sm.json','w'))"
if P2_CENSO="$TMP/sm.json" python3 "$SCRIPT" >/dev/null 2>"$TMP/e17"; then
  echo "  RUIM T17 aceitou censo com registro sem modo"; ruim=$((ruim+1))
else
  grep -q "censo-com-registro-sem-modo" "$TMP/e17" && { echo "  ok   T17 recusa censo sem modo"; ok=$((ok+1)); } \
    || { echo "  RUIM T17 abortou por outro motivo"; ruim=$((ruim+1)); }
fi

# ── MUTAÇÕES ────────────────────────────────────────────────────────────────────
# Troca de EXPRESSÃO, nunca apagar faixa de linha: mutante que não compila mata todo
# caso e não é evidência sobre perna nenhuma (variante (c) da lição de mutação).
mut() {
  local nome="$1" velho="$2" novo="$3" espera="$4" sonda="${5:-2026-09-02}" campo="${6:-unidade}"
  python3 - "$SCRIPT" "$TMP/m.py" "$velho" "$novo" <<'PYM'
import sys
src,dst,velho,novo=sys.argv[1:5]
s=open(src).read()
n=s.count(velho)
if n!=1:
    print(f"ANCORA_NAO_UNICA n={n}");sys.exit(3)
open(dst,'w').write(s.replace(velho,novo))
PYM
  [ $? -eq 0 ] || { echo "  RUIM $nome ancora invalida"; ruim=$((ruim+1)); return; }
  python3 -c "import ast,sys;ast.parse(open('$TMP/m.py').read())" 2>/dev/null \
    || { echo "  RUIM $nome mutante nao compila"; ruim=$((ruim+1)); return; }
  local got
  got="$(P2_CENSO="$CENSO" python3 "$TMP/m.py" 2>/dev/null \
        | python3 -c "import json,sys;d=json.load(sys.stdin);print([e['$campo'] for e in d['epochs'] if e['epoch']=='$sonda'][0])" 2>/dev/null)"
  got="${got:-ABORTOU}"
  if [ "$got" = "$espera" ]; then echo "  ok   $nome mata ($sonda -> $got)"; ok=$((ok+1));
  else echo "  RUIM $nome NAO mata -> $sonda=[$got] esperado=[$espera]"; ruim=$((ruim+1)); fi
}

# M1: default do censo passa a ser "cheio" — reintroduz exatamente o defeito de origem
mut "M1 default-do-censo-vira-esperado" \
    'n = int(modos.get("active", 0))' \
    'n = int(modos.get("active", ESPERADO_POR_EPOCH))' "inteira"
# M2: a composição deixa de exigir entrega cheia
# M2 sonda 09-03 (relogio INTEIRO, entrega PARCIAL): com `or` a composicao promoveria a
# inteira um epoch que entregou 441 de 672.
#
# ⚠️ Esta mutacao trocou de sonda DUAS vezes, por motivos distintos:
#   1a) sondava 09-02 esperando `vazia` -- que e' o veredito do ORIGINAL, logo absolvia-se;
#       e a perna de `vazio` precede a composicao, tornando o ramo inalcancavel.
#   2a) passou a 09-01 (relogio parcial + entrega `cheia`) e mordeu -- mas so porque a
#       entrega estava ERRADA ali (contava 672 total). Consertado o filtro por modo,
#       09-01 ficou parcial nas duas metades e o `or` deixou de promover.
# Licao: a sonda de uma mutacao esta acoplada aos DADOS, e consertar um defeito pode
# fazer uma mutacao parar de morder sem ninguem tocar nela. E' por isso que a suite
# roda, em vez de se confiar no relatorio da ultima vez.
mut "M2 unidade-ignora-entrega" \
    'elif j["classe_janela"] == "inteiro" and e["classe_entrega"] == "cheio":' \
    'elif j["classe_janela"] == "inteiro" or e["classe_entrega"] == "cheio":' \
    "inteira" "2026-09-03"
# M3: a perna de vazio some da composição
mut "M3 perna-de-vazio-desligada" \
    'elif e["classe_entrega"] == "vazio":' \
    'elif False and e["classe_entrega"] == "vazio":' "parcial"

# M4: a perna de entrega volta a contar o TOTAL (o defeito que a sessao par achou).
# Sondada em `classe_entrega` de 09-01: em `unidade` o mutante seria INVISIVEL, porque o
# relogio decide `parcial` de qualquer forma.
mut "M4 entrega-conta-o-total-em-vez-do-active" \
    'n = int(modos.get("active", 0))' \
    'n = int(sum(modos.values()))' \
    "cheio" "2026-09-01" "classe_entrega"

echo "── ok=$ok ruim=$ruim"
[ "$ruim" -eq 0 ]
