#!/usr/bin/env bash
# teste-gatilho-composicao.sh — mutação do rebaixamento por corpus não servido.
#
# O gatilho conta sobre o corpus que recebe em `--corpus`; o serving pode estar
# lendo OUTRO inode (§10.10). Cada caso aqui constrói o par (contagem, alinhamento)
# e exige o veredito — inclusive quando o veredito errado seria o otimista, que
# neste guarda é rebaixar um RED que ninguém autorizou a rebaixar.
#
# A perna do TIMEOUT do `execFileSync` cai no MESMO `catch` do script ausente (T5):
# é a mesma saída `INDETERMINADO:nao-rodou`. Não há caso próprio para ela, e isso
# está declarado em vez de presumido.
set -uo pipefail
GAT="${1:-$(dirname "$0")/gatilho-composicao.mjs}"
[ -f "$GAT" ] || { echo "ERRO: gatilho inexistente: $GAT" >&2; exit 2; }
T="$(mktemp -d /var/tmp/teste-composicao-XXXXXX)"
trap 'rm -rf "$T"' EXIT
FALHAS=0

# ── Raiz sintética: o gatilho confere as cláusulas no FONTE e lê os limiares do
#    `dist`. Os dois têm de existir, senão ele aborta com exit 2 e todo caso passa
#    a testar o abort, não o rebaixamento.
mkdir -p "$T/src/api" "$T/dist/api"
cat > "$T/src/api/brief.ts" <<'TS'
// fixture: as duas cláusulas que o gatilho exige encontrar
const _a = "(COALESCE(importance, 0) >= ? OR COALESCE(pain, 0) >= ?)";
const _b = "julianday('now') - julianday(COALESCE(source_date, created_at)) <= ?";
TS
cat > "$T/dist/api/brief.js" <<'JS'
export function scopePatterns(_escopo, agente) { return [`sessions/${agente}/%`]; }
JS
cat > "$T/dist/api/brief-diversity.js" <<'JS'
export const DIVERSITY_DEFAULTS = { freshMinImp: 0.7, freshMinPain: 0.7, freshMaxAgeDays: 7 };
JS

# ── Corpus sintético. `n` = quantos chunks FRESCOS de sessions/boris/ entram.
mkdb() {  # $1=arquivo $2=n_frescos
  rm -f "$1"
  node -e '
    const Database = require("better-sqlite3");
    const d = new Database(process.argv[1]);
    d.exec("CREATE TABLE chunks (id INTEGER PRIMARY KEY, source_file TEXT, importance REAL, pain REAL, source_date TEXT, created_at TEXT)");
    const ins = d.prepare("INSERT INTO chunks (source_file, importance, pain, source_date, created_at) VALUES (?,?,?,?,?)");
    const hoje = new Date().toISOString().slice(0,10);
    for (let i = 0; i < Number(process.argv[2]); i++) ins.run("sessions/boris/x" + i + ".md", 0.9, 0.1, hoje, hoje);
    // ruído que NÃO pode contar: velho demais, e fora do escopo dos agentes
    ins.run("sessions/boris/velho.md", 0.9, 0.1, "2020-01-01", "2020-01-01");
    ins.run("memory/entities/lessons/aaa.md", 0.9, 0.1, hoje, hoje);
    d.close();
  ' "$1" "$2"
}

stub() {  # $1=linha que o gatilho-corpus-alinhado.sh deve imprimir
  printf '#!/bin/sh\nprintf "%%s\\n" %s\n' "$(printf '%q' "$1")" > "$T/alin.sh"
  chmod +x "$T/alin.sh"
}

roda() {  # $@ = args extra
  node "$GAT" --raiz "$T" --corpus "$T/corpus.db" --agentes boris,nox \
    --ndjson "$T/nd.ndjson" "$@" 2>&1
}
espera() {  # $1=rot $2=estado $3=substring
  local rot="$1" est="$2" sub="$3"; shift 3
  local l; l="$(roda "$@")"
  if [ "${l%% *}" = "$est" ] && [[ "$l" == *"$sub"* ]]; then echo "ok   $rot"
  else echo "FALHA $rot"; echo "      esperado: $est ... $sub"; echo "      obtido:   $l"; FALHAS=$((FALHAS+1)); fi
}

# ── T1: canal mudou E o serving lê o mesmo corpus ⇒ RED de verdade.
mkdb "$T/corpus.db" 3
stub "GREEN p2-corpus-alinhado motivo=alinhado fd=26 inode=123 alvo=e1.db"
espera "T1 contagem>0 + alinhado ⇒ RED" RED "alinhamento_do_serving=GREEN:alinhado" --alinhamento-script "$T/alin.sh"

# ── T2: mesma contagem, serving lendo outro inode ⇒ YELLOW, e a contagem SOBREVIVE
#        na linha. Rebaixar não é apagar o número.
stub "RED p2-corpus-alinhado motivo=corpus-DELETADO-e-vivo-so-pelo-fd fd=26 inode_fd=1 inode_link=2"
espera "T2 contagem>0 + desalinhado ⇒ YELLOW" YELLOW "rebaixado=RED->YELLOW" --alinhamento-script "$T/alin.sh"
L="$(roda --alinhamento-script "$T/alin.sh")"
case "$L" in *agent_fresh_elegiveis=3*) echo "ok   T2b contagem preservada no rebaixamento";;
  *) echo "FALHA T2b a contagem sumiu da linha rebaixada"; echo "      obtido: $L"; FALHAS=$((FALHAS+1));; esac

# ── T3: sem contagem, desalinhado ⇒ GREEN. O rebaixamento só toca RED; um GREEN
#        que virasse YELLOW por desalinhamento inventaria alarme.
mkdb "$T/corpus.db" 0
espera "T3 contagem=0 + desalinhado ⇒ GREEN" GREEN "agent_fresh_elegiveis=0" --alinhamento-script "$T/alin.sh"

# ── T4: alinhamento YELLOW (processo sem fd aberto ainda) NÃO rebaixa.
mkdb "$T/corpus.db" 3
stub "YELLOW p2-corpus-alinhado motivo=nenhum-fd-para-o-diretorio-de-epochs dir=/x pid=1"
espera "T4 alinhamento YELLOW nao rebaixa" RED "alinhamento_do_serving=YELLOW:" --alinhamento-script "$T/alin.sh"

# ── T5: script de alinhamento ausente ⇒ RED preservado e INDETERMINADO declarado.
#        "nao consegui medir" nao pode ter a mesma saida que "medi e esta alinhado".
espera "T5 script ausente ⇒ RED + INDETERMINADO" RED "alinhamento_do_serving=INDETERMINADO:nao-rodou" \
  --alinhamento-script "$T/nao-existe.sh"

# ── T6: script responde lixo ⇒ RED preservado, ilegivel declarado.
stub "isto nao e um veredito"
espera "T6 linha ilegivel ⇒ RED + INDETERMINADO" RED "INDETERMINADO:linha-ilegivel" --alinhamento-script "$T/alin.sh"

# ── T7: o NDJSON carrega o estado BRUTO e o rebaixamento. Sem isso, a serie
#        historica perde a distincao entre "o canal nao mudou" e "mudou no corpus
#        que ninguem serve" — que e a leitura inteira deste patch.
rm -f "$T/nd.ndjson"
stub "RED p2-corpus-alinhado motivo=corpus-DELETADO-e-vivo-so-pelo-fd fd=26"
roda --alinhamento-script "$T/alin.sh" > /dev/null
if grep -q '"estado_bruto":"RED"' "$T/nd.ndjson" && grep -q '"rebaixado":true' "$T/nd.ndjson" \
   && grep -q '"estado":"YELLOW"' "$T/nd.ndjson"; then echo "ok   T7 ndjson carrega bruto+rebaixado"
else echo "FALHA T7 ndjson sem o par bruto/rebaixado"; echo "      $(tail -1 "$T/nd.ndjson")"; FALHAS=$((FALHAS+1)); fi

echo
if [ "$FALHAS" -eq 0 ]; then echo "TODOS OS CASOS PASSARAM"; else echo "$FALHAS CASO(S) FALHARAM"; fi
exit "$FALHAS"
