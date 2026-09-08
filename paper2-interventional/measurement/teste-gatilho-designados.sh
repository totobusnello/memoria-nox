#!/usr/bin/env bash
# teste-gatilho-designados.sh — mutação do gatilho de integridade dos designados.
#
# Cada caso constrói o estado do mundo que deveria produzir o veredito, e falha se
# o veredito for outro — inclusive quando o veredito "errado" seria o otimista.
# Um guarda não testado é uma crença sobre um guarda.
set -uo pipefail
GAT="${1:-$(dirname "$0")/gatilho-designados.mjs}"
[ -f "$GAT" ] || { echo "ERRO: gatilho inexistente: $GAT" >&2; exit 2; }
T="$(mktemp -d /var/tmp/teste-designados-XXXXXX)"
trap 'rm -rf "$T"' EXIT
FALHAS=0

# DB sintético: 3 designados + 1 não-designado (para provar que o guarda olha só os seus)
mkdb() {  # $1=arquivo
  rm -f "$1"
  node -e '
    const Database = require("better-sqlite3");
    const d = new Database(process.argv[1]);
    d.exec("CREATE TABLE chunks (id INTEGER PRIMARY KEY, source_file TEXT, chunk_text TEXT)");
    const ins = d.prepare("INSERT INTO chunks (id, source_file, chunk_text) VALUES (?,?,?)");
    ins.run(101, "memory/entities/lessons/aaa.md", "texto do designado 101");
    ins.run(102, "memory/entities/lessons/bbb.md", "texto do designado 102");
    ins.run(103, "memory/entities/lessons/ccc.md", "texto do designado 103");
    ins.run(999, "memory/lessons.md", "nao designado");
    d.close();
  ' "$1"
}
desig() { printf '{"designados_ids":[101,102,103],"grupos":3}\n' > "$1"; }

roda() {  # $@ = args extra
  node "$GAT" --vivo "$T/vivo.db" --designacao "$T/d.json" \
    --designacao-sha256 "$SHA" --baseline "$T/base.json" \
    --ndjson "$T/nd.ndjson" "$@" 2>&1
}
espera() {  # $1=rot $2=estado $3=substring
  local rot="$1" est="$2" sub="$3"; shift 3
  local l; l="$(roda "$@")"
  if [ "${l%% *}" = "$est" ] && [[ "$l" == *"$sub"* ]]; then echo "ok   $rot"
  else echo "FALHA $rot"; echo "      esperado: $est ... $sub"; echo "      obtido:   $l"; FALHAS=$((FALHAS+1)); fi
}
nd_linhas() { [ -f "$T/nd.ndjson" ] && grep -c . "$T/nd.ndjson" || echo 0; }

desig "$T/d.json"; SHA="$(sha256sum "$T/d.json" | cut -d' ' -f1)"

# ── T1: estado íntegro sem baseline ⇒ cria e diz que criou.
mkdb "$T/vivo.db"; rm -f "$T/base.json" "$T/nd.ndjson"
espera "T1 baseline criado no primeiro contato" GREEN "motivo=baseline-criado"
[ -f "$T/base.json" ] || { echo "FALHA T1b baseline nao foi escrito"; FALHAS=$((FALHAS+1)); }

# ── T2: segunda execução, nada mudou ⇒ GREEN por comparação, não por criação.
espera "T2 integro compara com baseline" GREEN "motivo=todos-integros"

# ── T3: designado DELETADO ⇒ RED, com o id na linha.
#        É o que a reingestão por arquivo produz, e é o caso que motivou o guarda.
BASE_ANTES="$(sha256sum "$T/base.json" | cut -d' ' -f1)"
node -e 'const D=require("better-sqlite3");const d=new D(process.argv[1]);d.exec("DELETE FROM chunks WHERE id=102");d.close();' "$T/vivo.db"
espera "T3 designado ausente ⇒ RED com o id" RED "ausentes=102"
BASE_DEPOIS="$(sha256sum "$T/base.json" | cut -d' ' -f1)"
if [ "$BASE_ANTES" = "$BASE_DEPOIS" ]; then echo "ok   T3b baseline NAO foi sobrescrito sobre estado quebrado"
else echo "FALHA T3b baseline mudou — guarda se conserta e cala"; FALHAS=$((FALHAS+1)); fi

# ── T4: id vive, texto muda ⇒ YELLOW. A perna de ausência fica calada aqui, e é
#        exatamente por isso que existem duas pernas.
mkdb "$T/vivo.db"
node -e 'const D=require("better-sqlite3");const d=new D(process.argv[1]);d.prepare("UPDATE chunks SET chunk_text = ? WHERE id = ?").run("OUTRO TEXTO",103);d.close();' "$T/vivo.db"
espera "T4 deriva de conteudo com id vivo ⇒ YELLOW" YELLOW "103:texto"

# ── T5: mesmo id e mesmo texto, ARQUIVO diferente ⇒ YELLOW.
mkdb "$T/vivo.db"
node -e 'const D=require("better-sqlite3");const d=new D(process.argv[1]);d.prepare("UPDATE chunks SET source_file = ? WHERE id = ?").run("memory/entities/lessons/OUTRO.md",101);d.close();' "$T/vivo.db"
espera "T5 designado mudou de arquivo ⇒ YELLOW" YELLOW "101:arquivo"

# ── T6: sha do DESIGNATION divergente ⇒ recusa medir. Vigiar a partir de uma
#        designação não verificada é servir o defeito que o guarda evita.
mkdb "$T/vivo.db"
L6="$(node "$GAT" --vivo "$T/vivo.db" --designacao "$T/d.json" --designacao-sha256 0000000000 \
      --baseline "$T/base.json" --ndjson "$T/nd.ndjson" 2>&1)"
if [ "${L6%% *}" = RED ] && [[ "$L6" == *"designacao-sha256-divergente"* ]]; then
  echo "ok   T6 sha divergente ⇒ RED sem medir"
else echo "FALHA T6"; echo "      obtido: $L6"; FALHAS=$((FALHAS+1)); fi

# ── T7: baseline ausente E designado já faltando ⇒ RED, e NÃO cria baseline.
#        Criar baseline sobre estado quebrado congelaria a quebra como referência
#        e o guarda diria GREEN para sempre depois.
mkdb "$T/vivo.db"; rm -f "$T/base.json"
node -e 'const D=require("better-sqlite3");const d=new D(process.argv[1]);d.exec("DELETE FROM chunks WHERE id=101");d.close();' "$T/vivo.db"
espera "T7 sem baseline e ja quebrado ⇒ RED sem criar" RED "baseline-ausente-e-designados-ja-faltam"
if [ ! -f "$T/base.json" ]; then echo "ok   T7b baseline NAO foi criado sobre estado quebrado"
else echo "FALHA T7b criou baseline sobre quebra"; FALHAS=$((FALHAS+1)); fi

# ── T8: o guarda olha SÓ os designados. Mexer no não-designado 999 é inerte.
#        Sem isto, um guarda que vigiasse a tabela toda passaria T1-T7 e daria
#        RED em toda reingestao de lessons.md — alarme que ensina a ignorar alarme.
mkdb "$T/vivo.db"; rm -f "$T/base.json"; roda >/dev/null
node -e 'const D=require("better-sqlite3");const d=new D(process.argv[1]);d.exec("DELETE FROM chunks WHERE id=999");d.close();' "$T/vivo.db"
espera "T8 nao-designado removido e inerte" GREEN "motivo=todos-integros"

# ── T9: TODO caminho de saída grava NDJSON, inclusive os de recusa.
#        Lição de 2026-09-08: no gatilho de saturacao os vereditos por atalho iam
#        só para um status que a execução seguinte sobrescreve (§10.8).
rm -f "$T/nd.ndjson"
node "$GAT" --vivo "$T/vivo.db" --designacao "$T/d.json" --designacao-sha256 0000 \
  --baseline "$T/base.json" --ndjson "$T/nd.ndjson" >/dev/null 2>&1
N9="$(nd_linhas)"
V9="$(python3 -c "
import json,sys
ls=[json.loads(l) for l in open('$T/nd.ndjson') if l.strip()]
print(f'n={len(ls)} tag={ls[0][\"tag\"] if ls else None} estado={ls[0][\"estado\"] if ls else None}')
" 2>/dev/null)"
if [ "$N9" = 1 ] && [[ "$V9" == "n=1 tag=p2_gatilho_designados estado=RED" ]]; then
  echo "ok   T9 recusa por sha tambem grava NDJSON"
else echo "FALHA T9 caminho de recusa sem NDJSON"; echo "      obtido: n=$N9 $V9"; FALHAS=$((FALHAS+1)); fi

# ── T10: uma deriva detectada NÃO contamina o baseline ⇒ a segunda execução
#        continua YELLOW. Este é o caso que prova a imutabilidade de verdade.
#        T3b e T7b NÃO provam: neles há ausência, e o bloco de criação recusa
#        criar sobre estado quebrado — logo o baseline fica intacto mesmo se a
#        imutabilidade for removida (medido: a mutação "baseline sobrescrito"
#        deixa T3b e T7b VERDES). Um guarda que reescrevesse a referência ao
#        detectar deriva diria YELLOW uma vez e GREEN para sempre depois.
mkdb "$T/vivo.db"; rm -f "$T/base.json"; roda >/dev/null
BASE_T10="$(sha256sum "$T/base.json" | cut -d" " -f1)"
node -e 'const D=require("better-sqlite3");const d=new D(process.argv[1]);d.prepare("UPDATE chunks SET chunk_text = ? WHERE id = ?").run("DERIVOU",102);d.close();' "$T/vivo.db"
L10a="$(roda)"; L10b="$(roda)"
BASE_T10_DEPOIS="$(sha256sum "$T/base.json" | cut -d" " -f1)"
if [ "${L10a%% *}" = YELLOW ] && [ "${L10b%% *}" = YELLOW ] \
   && [[ "$L10b" == *"102:texto"* ]] && [ "$BASE_T10" = "$BASE_T10_DEPOIS" ]; then
  echo "ok   T10 deriva persiste na 2a execucao (baseline nao contaminado)"
else
  echo "FALHA T10 deriva sumiu ou baseline mudou"
  echo "      1a: ${L10a%% *}  2a: ${L10b%% *}  baseline igual: $([ "$BASE_T10" = "$BASE_T10_DEPOIS" ] && echo sim || echo NAO)"
  FALHAS=$((FALHAS+1))
fi

echo
[ "$FALHAS" -eq 0 ] && echo "TODOS OS CASOS PASSARAM" || echo "$FALHAS CASO(S) FALHARAM"
exit 0
