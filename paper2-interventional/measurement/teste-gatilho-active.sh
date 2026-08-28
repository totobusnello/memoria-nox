#!/usr/bin/env bash
# teste-gatilho-active.sh — mutação do caminho `--modo active` do item 7(a).
#
# Um gatilho não testado é uma crença sobre um gatilho. Aqui cada caso constrói o
# estado do mundo que deveria produzir o veredito, e o teste falha se o veredito
# for outro — inclusive quando o veredito "errado" seria o otimista.
#
# A harness real leva ~15 min sobre um dia de log. Nos casos que só exercitam o
# encanamento de `active` (sha, epoch, cruzamento log × assignment) ela é
# substituída por um STUB — o que está sob teste ali é a decisão, não o replay.
# O caso T5 usa o stub justamente para provar que o caminho de tratamento CHEGA
# ao replay com a dose do ASSIGNMENT, que é a obrigação inteira.
#
# Uso: teste-gatilho-active.sh [caminho-do-gatilho]
set -uo pipefail
GAT="${1:-$(dirname "$0")/gatilho-saturacao.sh}"
T="$(mktemp -d /var/tmp/teste-gatilho-XXXXXX)"
trap 'rm -rf "$T"' EXIT
FALHAS=0

# Stub de harness: devolve uma tabela de dose plausível, com as duas doses que o
# gatilho pediu. Grava os argumentos recebidos para o T5 poder conferir a dose.
cat > "$T/harness-stub.mjs" <<'EOF'
import { writeFileSync } from "node:fs";
const a = process.argv.slice(2);
const ws = a.map((x, i) => (x === "--w" ? Number(a[i + 1]) : null)).filter((x) => x !== null);
const out = a[a.indexOf("--out") + 1];
writeFileSync(process.env.STUB_ARGS || "/dev/null", JSON.stringify({ ws }));
writeFileSync(out, JSON.stringify({ dose: { tabela: ws.map((w) => ({
  w, mexeu: w >= 100000 ? 52 : 25, churn_total: w >= 100000 ? 90 : 40, estados: 672,
})) } }));
EOF

# Log sintético: n linhas p2_outcome dentro do epoch alvo.
log_sintetico() {  # $1=arquivo $2=epoch $3=modo $4=w $5=servido $6=n
  : > "$1"
  for i in $(seq 1 "$6"); do
    printf '{"ts":"%sT12:%02d:00.000Z","tag":"p2_outcome","epoch":"%s","modo":"%s","w":%s,"servido":"%s","churn":0}\n' \
      "$2" $((i % 60)) "$2" "$3" "$4" "$5" >> "$1"
  done
}

assign() {  # $1=arquivo $2=epoch $3=arm $4=w
  printf '{"epochs":[{"epoch_inicio":"%s","arm":"%s","w":%s}]}\n' "$2" "$3" "$4" > "$1"
}

roda() {  # imprime a linha de status
  "$GAT" --raiz "$T" --harness "$T/harness-stub.mjs" \
    --corpus "$T/corpus.db" --vivo "$T/vivo.db" \
    --designacao "$T/desig.json" --designacao-sha256 deadbeef \
    --tmp "$T" "$@" 2>/dev/null
}

espera() {  # $1=rótulo $2=estado esperado $3=substring esperada $4...=args
  local rot="$1" est="$2" sub="$3"; shift 3
  local linha; linha="$(roda "$@")"
  if [ "${linha%% *}" = "$est" ] && [[ "$linha" == *"$sub"* ]]; then
    echo "ok   $rot"
  else
    echo "FALHA $rot"; echo "      esperado: $est ... $sub"; echo "      obtido:   $linha"
    FALHAS=$((FALHAS + 1))
  fi
}

echo '{}' > "$T/desig.json"; : > "$T/corpus.db"; : > "$T/vivo.db"

# Epoch cujo fim (E+1 09:00Z) já passou, com folga.
E="$(date -u -d '3 days ago' +%Y-%m-%d)"
ABERTO="$(date -u +%Y-%m-%d)"   # o epoch de hoje ainda não fechou

# ── T1: sha256 do ASSIGNMENT diverge ⇒ RED, e não mede nada.
assign "$T/a.json" "$E" treatment 4
log_sintetico "$T/log.ndjson" "$E" active 4 tratado 40
espera "T1 sha do assignment diverge" RED "assignment-sha256-divergente" \
  --modo active --log "$T/log.ndjson" --assignment "$T/a.json" --assignment-sha256 0000

SHA="$(sha256sum "$T/a.json" | cut -d' ' -f1)"

# ── T2: só existe epoch ainda ABERTO ⇒ RED. Medir janela que cresce é o defeito
#        de "série viva citada como instante".
assign "$T/aberto.json" "$ABERTO" treatment 4
SHA_AB="$(sha256sum "$T/aberto.json" | cut -d' ' -f1)"
espera "T2 recusa epoch ainda aberto" RED "nenhum-epoch-fechado" \
  --modo active --log "$T/log.ndjson" --assignment "$T/aberto.json" --assignment-sha256 "$SHA_AB"

# ── T3: o ASSIGNMENT diz tratamento, o log diz que serviu controle ⇒ RED.
#        É o modo de falha que enviesa para o nulo, e o único jeito de vê-lo.
log_sintetico "$T/log3.ndjson" "$E" active 4 controle 40
espera "T3 tratamento designado, controle servido" RED "epoch-de-tratamento-mas-servido" \
  --modo active --log "$T/log3.ndjson" --assignment "$T/a.json" --assignment-sha256 "$SHA"

# ── T4: a dose no log diverge da designada ⇒ RED.
log_sintetico "$T/log4.ndjson" "$E" active 7.5 tratado 40
espera "T4 dose no log != dose designada" RED "w-no-log" \
  --modo active --log "$T/log4.ndjson" --assignment "$T/a.json" --assignment-sha256 "$SHA"

# ── T5: caminho feliz de TRATAMENTO — chega ao replay com a dose do ASSIGNMENT.
export STUB_ARGS="$T/stub-args.json"
espera "T5 tratamento roda e reporta folga" GREEN "arm=treatment" \
  --modo active --log "$T/log.ndjson" --assignment "$T/a.json" --assignment-sha256 "$SHA"
if [ -s "$STUB_ARGS" ] && grep -q '"ws":\[4,100000\]' "$STUB_ARGS"; then
  echo "ok   T5b a dose passada ao replay é a do ASSIGNMENT (4), não uma flag"
else
  echo "FALHA T5b dose errada no replay: $(cat "$STUB_ARGS" 2>/dev/null)"; FALHAS=$((FALHAS + 1))
fi
unset STUB_ARGS

# ── T6: epoch de CONTROLE ⇒ GREEN, mas com o motivo escrito. GREEN mudo sobre
#        pergunta não feita é indistinguível de GREEN sobre pergunta respondida.
assign "$T/c.json" "$E" control 0
SHA_C="$(sha256sum "$T/c.json" | cut -d' ' -f1)"
log_sintetico "$T/log6.ndjson" "$E" active 0 controle 40
espera "T6 controle diz por que está verde" GREEN "epoch-de-controle-sem-dose-a-saturar" \
  --modo active --log "$T/log6.ndjson" --assignment "$T/c.json" --assignment-sha256 "$SHA_C"

# ── T7: log ainda em `shadow` enquanto o unit já diz `active` ⇒ RED.
#        É o estado real durante uma ativação mal-feita.
log_sintetico "$T/log7.ndjson" "$E" shadow 2 controle 40
espera "T7 log em shadow sob modo active" RED "modo-no-log" \
  --modo active --log "$T/log7.ndjson" --assignment "$T/a.json" --assignment-sha256 "$SHA"

# ── T8: exclusão mútua das duas fontes de dose ⇒ recusa (exit 2), não precedência.
if "$GAT" --raiz "$T" --harness "$T/harness-stub.mjs" --log "$T/log.ndjson" \
     --corpus "$T/corpus.db" --vivo "$T/vivo.db" --designacao "$T/desig.json" \
     --designacao-sha256 deadbeef --modo active --assignment "$T/a.json" \
     --assignment-sha256 "$SHA" --w-servido 2 >/dev/null 2>&1; then
  echo "FALHA T8 aceitou --w-servido junto com --assignment"; FALHAS=$((FALHAS + 1))
else
  echo "ok   T8 recusa --w-servido em active"
fi

# ── T9: shadow segue funcionando como antes (não-regressão).
log_sintetico "$T/log9.ndjson" "$(date -u -d yesterday +%Y-%m-%d)" shadow 2 controle 40
espera "T9 shadow inalterado" GREEN "w_servido=2.0" \
  --modo shadow --log "$T/log9.ndjson" --w-servido 2

echo
[ "$FALHAS" -eq 0 ] && echo "TODOS OS CASOS PASSARAM" || echo "$FALHAS CASO(S) FALHARAM"
exit 0
