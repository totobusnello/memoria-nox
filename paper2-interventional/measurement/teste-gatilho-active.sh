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
# Alvo inexistente faz TODO caso sair com corpo VAZIO — 11 falhas idênticas que
# parecem defeito do gatilho e são defeito de invocação. Aconteceu 2026-09-06, ao
# rodar este arquivo copiado para /var/tmp sem argumento: o default `dirname "$0"`
# apontou para um diretório sem gatilho e a suíte inteira "reprovou" o alvo errado.
# É a mesma família que o dia inteiro tratou — guarda que fica calado por não ter o
# que precisa —, aqui do lado do teste. Falhar alto separa "o alvo está quebrado"
# de "você não passou o alvo".
[ -x "$GAT" ] || { echo "ERRO: gatilho inexistente ou não executável: $GAT" >&2; exit 2; }
T="$(mktemp -d /var/tmp/teste-gatilho-XXXXXX)"
trap 'rm -rf "$T"' EXIT
FALHAS=0

# Stub de harness: devolve uma tabela de dose plausível, com as duas doses que o
# gatilho pediu. Grava os argumentos recebidos para o T5 poder conferir a dose.
cat > "$T/harness-stub.mjs" <<'EOF'
import { writeFileSync, readFileSync } from "node:fs";
const a = process.argv.slice(2);
const ws = a.map((x, i) => (x === "--w" ? Number(a[i + 1]) : null)).filter((x) => x !== null);
const out = a[a.indexOf("--out") + 1];
writeFileSync(process.env.STUB_ARGS || "/dev/null", JSON.stringify({ ws }));
// `estados` sai do TAMANHO DA JANELA que o gatilho passou, não de uma constante.
// Antes era `672` fixo, e com log sintético de 40 linhas isso é um replay que
// afirma ter respondido 672 estados sobre 40 registros — incoerência que a perna
// `erros-no-replay` (2026-09-06) passou a pegar, quebrando T5 e T9. O stub é que
// estava errado: um replay fiel responde a janela que recebeu. `STUB_FALTAM`
// permite a um caso PEDIR a incoerência, que é o que T10 exercita.
const jan = a[a.indexOf("--log-campo") + 1];
const n = readFileSync(jan, "utf8").split("\n").filter((l) => l.trim()).length;
const estados = n - Number(process.env.STUB_FALTAM || 0);
writeFileSync(out, JSON.stringify({ dose: { tabela: ws.map((w) => ({
  w, mexeu: w >= 100000 ? 52 : 25, churn_total: w >= 100000 ? 90 : 40, estados,
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

# ── T10: o replay não respondeu a janela inteira ⇒ RED com o motivo CERTO.
#        É o caso que os dois RED de 05-06/09 deviam ter produzido e não produziram:
#        o gatilho carregava `n_janela` e `estados` na mesma linha e não os comparava.
#        Exige a mensagem específica E os três números — casar só por "RED" deixaria
#        passar um RED de inércia, que é justamente o veredito errado que motivou a perna.
log_sintetico "$T/log10.ndjson" "$E" active 4 tratado 100
L10="$(STUB_FALTAM=32 roda --modo active --log "$T/log10.ndjson" \
        --assignment "$T/a.json" --assignment-sha256 "$SHA")"
if [ "${L10%% *}" = RED ] && [[ "$L10" == *"erros-no-replay"* ]] \
   && [[ "$L10" == *"faltam=32"* ]] && [[ "$L10" == *"estados=68"* ]] \
   && [[ "$L10" == *"n_janela=100"* ]]; then
  echo "ok   T10 janela incompleta ⇒ RED erros-no-replay com faltam/estados/n_janela certos"
else
  echo "FALHA T10 janela incompleta"; echo "      obtido: $L10"; FALHAS=$((FALHAS + 1))
fi

# ── T11: controle de T10 — janela respondida INTEIRA não dispara a perna.
#        Sem isto, um predicado que disparasse sempre passaria em T10.
L11="$(roda --modo active --log "$T/log10.ndjson" \
        --assignment "$T/a.json" --assignment-sha256 "$SHA")"
if [[ "$L11" != *"erros-no-replay"* ]] && [ "${L11%% *}" = GREEN ]; then
  echo "ok   T11 janela completa não dispara erros-no-replay"
else
  echo "FALHA T11 janela completa"; echo "      obtido: $L11"; FALHAS=$((FALHAS + 1))
fi

# ── T12: veredito por ATALHO grava linha no NDJSON (§10.8, achado 2026-09-08).
#        Antes do patch este caso produzia ZERO linhas: `emitir()` escrevia
#        `stdout` e o `--status`, nunca o `--ndjson`. Exige a linha E o `via`, E
#        que `servido/absurdo/folga` sejam `null` — preenchê-los com zero
#        fabricaria `mexeu = 0`, isto é `dose-servida-inerte`, que é o veredito
#        errado que o §10.4 documenta ter custado dois dias de RED trocado.
assign "$T/c12.json" "$E" control 0
SHA_C12="$(sha256sum "$T/c12.json" | cut -d' ' -f1)"
log_sintetico "$T/log12.ndjson" "$E" active 0 controle 40
: > "$T/nd12.ndjson"
L12="$(roda --modo active --log "$T/log12.ndjson" --assignment "$T/c12.json" \
        --assignment-sha256 "$SHA_C12" --ndjson "$T/nd12.ndjson")"
V12="$(python3 - "$T/nd12.ndjson" <<'PYT'
import json, sys
ls = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
if len(ls) != 1: print(f"n={len(ls)}"); raise SystemExit
o = ls[0]
nulos = all(o.get(k) is None for k in ("servido", "absurdo", "folga"))
print(f'n=1 via={o.get("via")} motivo={o.get("motivo")} arm={o.get("arm")} nulos={nulos}')
PYT
)"
if [[ "$L12" == GREEN* ]] && [[ "$V12" == "n=1 via=atalho motivo=epoch-de-controle-sem-dose-a-saturar arm=control nulos=True" ]]; then
  echo "ok   T12 atalho grava NDJSON com via=atalho e sem campos de dose fabricados"
else
  echo "FALHA T12 atalho no NDJSON"; echo "      status: $L12"; echo "      ndjson: $V12"
  FALHAS=$((FALHAS + 1))
fi

# ── T13: controle de T12 — o caminho NORMAL grava UMA linha, não duas.
#        `emitir()` é chamado depois do bloco de veredito, que já gravou; sem a
#        sentinela em `$TMP` o caminho normal sairia duplicado, uma vez
#        estruturado e uma vez com `servido: null`. Casar só por "existe linha"
#        deixaria a duplicação passar, e um NDJSON com dois registros do mesmo
#        instante é pior que um registro faltando: os dois discordam.
: > "$T/nd13.ndjson"
L13="$(roda --modo active --log "$T/log10.ndjson" --assignment "$T/a.json" \
        --assignment-sha256 "$SHA" --ndjson "$T/nd13.ndjson")"
V13="$(python3 - "$T/nd13.ndjson" <<'PYT'
import json, sys
ls = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
if len(ls) != 1: print(f"n={len(ls)} vias={[x.get('via') for x in ls]}"); raise SystemExit
o = ls[0]
print(f'n=1 via={o.get("via")} tem_servido={o.get("servido") is not None} folga={o.get("folga") is not None}')
PYT
)"
if [[ "$L13" == GREEN* ]] && [[ "$V13" == "n=1 via=veredito-de-dose tem_servido=True folga=True" ]]; then
  echo "ok   T13 caminho normal grava UMA linha, com os campos de dose reais"
else
  echo "FALHA T13 escrita dupla ou campos ausentes"; echo "      status: $L13"; echo "      ndjson: $V13"
  FALHAS=$((FALHAS + 1))
fi

# ── T14: o atalho mais valioso do script é o que tem de deixar rastro.
#        `log-diverge-do-assignment` é, pelas palavras do cabeçalho do gatilho,
#        "a única coisa aqui que compara o que devia ser servido com o que foi" —
#        e era um dos que só existiam no log de texto. T3 já cobre o veredito;
#        este cobre a PERSISTÊNCIA dele.
: > "$T/nd14.ndjson"
log_sintetico "$T/log14.ndjson" "$E" active 4 controle 40
L14="$(roda --modo active --log "$T/log14.ndjson" --assignment "$T/a.json" \
        --assignment-sha256 "$SHA" --ndjson "$T/nd14.ndjson")"
V14="$(python3 - "$T/nd14.ndjson" <<'PYT'
import json, sys
ls = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
print(f'n={len(ls)} estado={ls[0].get("estado") if ls else None} motivo={ls[0].get("motivo") if ls else None}')
PYT
)"
if [[ "$L14" == RED* ]] && [[ "$V14" == "n=1 estado=RED motivo=log-diverge-do-assignment" ]]; then
  echo "ok   T14 log-diverge-do-assignment persiste no NDJSON"
else
  echo "FALHA T14 alarme mais valioso sem rastro"; echo "      status: $L14"; echo "      ndjson: $V14"
  FALHAS=$((FALHAS + 1))
fi


# ══ (a) IDENTIDADE DO CORPUS NO RECIBO — consertos de 2026-09-09 ══════════════
#
# O critério destes casos é o PAR DE FIXTURES de 09/09: duas corridas com vereditos
# OPOSTOS (GREEN 20/37/0.5405 e RED 0/0), `sha256_janela` idêntico, `estados=672`
# idêntico, mesmo epoch e mesma janela — e recibos indistinguíveis, porque nenhum
# dos 13 campos dizia sobre QUAL corpus o replay correu. Os casos abaixo passam se,
# e somente se, esse par se torna distinguível.
#
# ⚠️ Exigem a LINHA DE STATUS, não só o código de saída: o veredito que o morning
#    report lê é a linha. Um campo que só existisse no NDJSON deixaria o report
#    exatamente tão cego quanto era.

# ── T15: corpora com BYTES diferentes ⇒ recibos distinguíveis (status e NDJSON).
cp "$T/corpus.db" "$T/corpusA.db"; printf 'A' >> "$T/corpusA.db"
cp "$T/corpus.db" "$T/corpusB.db"; printf 'BB' >> "$T/corpusB.db"
SHA_A="$(sha256sum "$T/corpusA.db" | cut -d' ' -f1)"
SHA_B="$(sha256sum "$T/corpusB.db" | cut -d' ' -f1)"
roda_corpus() {  # $1=corpus $2=ndjson $3...=args
  local c="$1" nd="$2"; shift 2
  "$GAT" --raiz "$T" --harness "$T/harness-stub.mjs" \
    --corpus "$c" --vivo "$T/vivo.db" \
    --designacao "$T/desig.json" --designacao-sha256 deadbeef \
    --tmp "$T" --ndjson "$nd" "$@" 2>/dev/null
}
: > "$T/ndA.ndjson"; : > "$T/ndB.ndjson"
LA="$(roda_corpus "$T/corpusA.db" "$T/ndA.ndjson" --modo active --log "$T/log.ndjson" \
       --assignment "$T/a.json" --assignment-sha256 "$SHA")"
LB="$(roda_corpus "$T/corpusB.db" "$T/ndB.ndjson" --modo active --log "$T/log.ndjson" \
       --assignment "$T/a.json" --assignment-sha256 "$SHA")"
VA="$(python3 -c 'import json,sys;print(json.loads(open(sys.argv[1]).readline())["corpus_sha256"])' "$T/ndA.ndjson" 2>/dev/null)"
VB="$(python3 -c 'import json,sys;print(json.loads(open(sys.argv[1]).readline())["corpus_sha256"])' "$T/ndB.ndjson" 2>/dev/null)"
if [ "$VA" = "$SHA_A" ] && [ "$VB" = "$SHA_B" ] && [ "$VA" != "$VB" ] \
   && [[ "$LA" == *"corpus_sha256=${SHA_A:0:12}"* ]] \
   && [[ "$LB" == *"corpus_sha256=${SHA_B:0:12}"* ]] \
   && [[ "$LA" == *"corpus=corpusA.db"* ]]; then
  echo "ok   T15 corpora diferentes ⇒ recibos distinguíveis no status E no NDJSON"
else
  echo "FALHA T15 o par de fixtures segue indistinguível"
  echo "      ndjson: A=$VA B=$VB (esperado A=$SHA_A B=$SHA_B)"
  echo "      statusA: $LA"; FALHAS=$((FALHAS + 1))
fi

# ── T16: controle de T15 — o MESMO corpus tem de dar o MESMO sha. Sem este caso,
#        um campo que sorteasse valor a cada corrida passaria em T15 e o campo
#        seria ruído com cara de proveniência.
: > "$T/ndA2.ndjson"
roda_corpus "$T/corpusA.db" "$T/ndA2.ndjson" --modo active --log "$T/log.ndjson" \
  --assignment "$T/a.json" --assignment-sha256 "$SHA" >/dev/null
VA2="$(python3 -c 'import json,sys;print(json.loads(open(sys.argv[1]).readline())["corpus_sha256"])' "$T/ndA2.ndjson" 2>/dev/null)"
if [ -n "$VA2" ] && [ "$VA2" = "$VA" ]; then
  echo "ok   T16 mesmo corpus ⇒ mesmo sha (o campo é proveniência, não ruído)"
else
  echo "FALHA T16 sha instável para o mesmo corpus: $VA vs $VA2"; FALHAS=$((FALHAS + 1))
fi

# ── T17: o sha é dos BYTES, não do caminho. `current.db` é symlink e às 06:02 passa
#        a apontar para outros bytes sem que arquivo nenhum mude de nome — gravar o
#        caminho e chamar aquilo de proveniência é o defeito que a lição
#        `a_commit_hash_is_not_a_stable_pin` descreve, na versão do corpus.
ln -sf "$T/corpusB.db" "$T/andarilho.db"
: > "$T/ndLink.ndjson"
LL="$(roda_corpus "$T/andarilho.db" "$T/ndLink.ndjson" --modo active --log "$T/log.ndjson" \
       --assignment "$T/a.json" --assignment-sha256 "$SHA")"
VL="$(python3 -c 'import json,sys;o=json.loads(open(sys.argv[1]).readline());print(o["corpus_sha256"],o["corpus_path"])' "$T/ndLink.ndjson" 2>/dev/null)"
if [[ "$VL" == "$SHA_B "*"corpusB.db" ]] && [[ "$LL" == *"corpus=corpusB.db"* ]]; then
  echo "ok   T17 symlink é resolvido: grava os bytes apontados, não o nome do link"
else
  echo "FALHA T17 symlink não resolvido: $VL"; echo "      status: $LL"; FALHAS=$((FALHAS + 1))
fi

# ══ (b) A APROXIMAÇÃO DECLARADA É VÁLIDA HOJE? ════════════════════════════════
#
# O cabeçalho do wrapper diz, desde 27/08, que a escolha de corpus "foi inerte" e
# que "inerte não é garantido". Nada media quando deixara de ser. Desde 03/09 17:30
# o serving lê um inode já apagado do disco enquanto `current.db` seguiu relinkando
# (§10.10) — o estado em que a aproximação é FALSA, sem alarme.
#
# `systemctl` e o prefixo do fd são substituídos pelo teste. O que está sob teste é
# a COMPARAÇÃO POR BYTES: caminho diferente com bytes iguais tem de dar `sim`.
mkdir -p "$T/bin" "$T/epocas"
cat > "$T/bin/systemctl" <<'EOF'
#!/bin/sh
cat "$FAKE_MAINPID"
EOF
chmod +x "$T/bin/systemctl"

cp "$T/corpusA.db" "$T/epocas/servido.db"        # bytes iguais a corpusA, nome outro
sleep 300 < "$T/epocas/servido.db" &
SLEEP_PID=$!
trap 'kill "$SLEEP_PID" 2>/dev/null; rm -rf "$T"' EXIT
echo "$SLEEP_PID" > "$T/mainpid"

roda_serving() {  # $1=corpus $2=ndjson $3...=args
  local c="$1" nd="$2"; shift 2
  PATH="$T/bin:$PATH" FAKE_MAINPID="$T/mainpid" FD_PREFIX="$T/epocas/" \
  "$GAT" --raiz "$T" --harness "$T/harness-stub.mjs" \
    --corpus "$c" --vivo "$T/vivo.db" \
    --designacao "$T/desig.json" --designacao-sha256 deadbeef \
    --tmp "$T" --ndjson "$nd" "$@" 2>/dev/null
}

# T18: corpus com os MESMOS bytes que o fd, caminho DIFERENTE ⇒ `sim`.
: > "$T/ndOk.ndjson"
LO="$(roda_serving "$T/corpusA.db" "$T/ndOk.ndjson" --modo active --log "$T/log.ndjson" \
       --assignment "$T/a.json" --assignment-sha256 "$SHA")"
VO="$(python3 -c 'import json,sys;o=json.loads(open(sys.argv[1]).readline());print(o["aproximacao_valida"])' "$T/ndOk.ndjson" 2>/dev/null)"
if [ "$VO" = sim ] && [[ "$LO" == *"aproximacao_valida=sim"* ]]; then
  echo "ok   T18 bytes iguais em caminho diferente ⇒ aproximacao_valida=sim"
else
  echo "FALHA T18 comparação por caminho, não por bytes: ndjson=$VO"
  echo "      status: $LO"; FALHAS=$((FALHAS + 1))
fi

# T19: corpus com bytes DIFERENTES do que o serving tem aberto ⇒ `nao`.
#      É o estado de produção em 09/09. Sem este caso, um campo fixo em "sim"
#      passaria em T18 e a perna inteira seria decoração.
: > "$T/ndNao.ndjson"
LN="$(roda_serving "$T/corpusB.db" "$T/ndNao.ndjson" --modo active --log "$T/log.ndjson" \
       --assignment "$T/a.json" --assignment-sha256 "$SHA")"
VN="$(python3 -c 'import json,sys;o=json.loads(open(sys.argv[1]).readline());print(o["aproximacao_valida"],",".join(o["serving_fd_sha256s"]) if isinstance(o["serving_fd_sha256s"],list) else o["serving_fd_sha256s"])' "$T/ndNao.ndjson" 2>/dev/null)"
if [[ "$VN" == "nao $SHA_A" ]] && [[ "$LN" == *"aproximacao_valida=nao"* ]]; then
  echo "ok   T19 bytes divergentes ⇒ aproximacao_valida=nao, com o sha do fd no recibo"
else
  echo "FALHA T19 divergência não detectada: $VN"; echo "      status: $LN"; FALHAS=$((FALHAS + 1))
fi

# T20: sem serving vivo ⇒ `indeterminada`, NUNCA `sim`. Ausência de dado não é
#      evidência de concordância — é a família de defeito do dia inteiro. Um
#      default otimista aqui reproduziria o silêncio que se está consertando.
echo 0 > "$T/mainpid-morto"
: > "$T/ndInd.ndjson"
LI="$(PATH="$T/bin:$PATH" FAKE_MAINPID="$T/mainpid-morto" FD_PREFIX="$T/epocas/" \
      "$GAT" --raiz "$T" --harness "$T/harness-stub.mjs" \
        --corpus "$T/corpusA.db" --vivo "$T/vivo.db" \
        --designacao "$T/desig.json" --designacao-sha256 deadbeef \
        --tmp "$T" --ndjson "$T/ndInd.ndjson" --modo active --log "$T/log.ndjson" \
        --assignment "$T/a.json" --assignment-sha256 "$SHA" 2>/dev/null)"
VI="$(python3 -c 'import json,sys;o=json.loads(open(sys.argv[1]).readline());print(o["aproximacao_valida"],",".join(o["serving_fd_sha256s"]) if isinstance(o["serving_fd_sha256s"],list) else o["serving_fd_sha256s"])' "$T/ndInd.ndjson" 2>/dev/null)"
if [[ "$VI" == "indeterminada sem-pid" ]] && [[ "$LI" == *"aproximacao_valida=indeterminada"* ]]; then
  echo "ok   T20 serving ausente ⇒ indeterminada (não 'sim' por omissão)"
else
  echo "FALHA T20 ausência de dado tratada como concordância: $VI"
  echo "      status: $LI"; FALHAS=$((FALHAS + 1))
fi

# ── T21: os campos novos aparecem também no recibo de ATALHO. T12 provou que o
#        atalho grava linha; se a proveniência só existisse no caminho normal, todo
#        epoch de controle (117 dos 234 do ensaio, metade) sairia sem ela.
: > "$T/ndAtalho.ndjson"
LT="$(roda_corpus "$T/corpusB.db" "$T/ndAtalho.ndjson" --modo active --log "$T/log12.ndjson" \
       --assignment "$T/c12.json" --assignment-sha256 "$SHA_C12")"
VT="$(python3 -c 'import json,sys;o=json.loads(open(sys.argv[1]).readline());print(o["via"],o["corpus_sha256"],o["aproximacao_valida"])' "$T/ndAtalho.ndjson" 2>/dev/null)"
if [[ "$VT" == "atalho $SHA_B "* ]] && [[ "$LT" == *"corpus_sha256=${SHA_B:0:12}"* ]]; then
  echo "ok   T21 atalho também carrega corpus_sha256 e aproximacao_valida"
else
  echo "FALHA T21 atalho sem proveniência: $VT"; echo "      status: $LT"; FALHAS=$((FALHAS + 1))
fi

# ══ OS TRÊS MUTANTES QUE OS 7 CASOS NÃO ALCANÇAVAM ═══════════════════════════
#
# Achados pela sessão par horas depois do deploy, por análise estática, e os três
# CONFIRMADOS sobreviventes rodando a suíte (21/21 com cada mutante aplicado). Um
# deles não era só mutante sobrevivente: era defeito.
#
# ⚠️ A nota de método que ficou: num predicado de TRÊS valores, o caso que prova a
#    perna é o que espera o valor MENOS acessível por acidente. `nao` é o default de
#    qualquer coisa quebrada; `sim` exige que a comparação acerte. T18 cobria M2 por
#    isso, e T19 sozinho não cobriria.

# ── T22: fd marcado `(deleted)` TEM de ser lido. É o estado de produção desde
#        03/09 17:30 — o único fd que a perna existe para enxergar. Escrevi a
#        primeira versão do filtro com `$` ancorado logo após `.db`, o que o
#        excluiria; a versão com `grep -oE` não ancorava e não tinha o defeito.
#        Trocar de ferramenta trouxe um defeito que não existia.
cp "$T/corpusA.db" "$T/epocas/apagado.db"
exec 7< "$T/epocas/apagado.db"
rm -f "$T/epocas/apagado.db"          # inode vivo só pelo fd, como em produção
# `7<&-` fecha o fd herdado NO FILHO: sem isso o sleep recebe 0 e 7 sobre o mesmo
# inode e o recibo diz `serving_fd_n=2` — dois fds, um inode. Defeito da fixture,
# não do gatilho, mas mostra que a contagem conta FDS e não INODES distintos.
sleep 300 < /proc/self/fd/7 7<&- &
SLEEP_DEL=$!
echo "$SLEEP_DEL" > "$T/mainpid-del"
exec 7<&-
: > "$T/ndDel.ndjson"
LD="$(PATH="$T/bin:$PATH" FAKE_MAINPID="$T/mainpid-del" FD_PREFIX="$T/epocas/" \
      "$GAT" --raiz "$T" --harness "$T/harness-stub.mjs" --corpus "$T/corpusA.db" \
        --vivo "$T/vivo.db" --designacao "$T/desig.json" --designacao-sha256 deadbeef \
        --tmp "$T" --ndjson "$T/ndDel.ndjson" --modo active --log "$T/log.ndjson" \
        --assignment "$T/a.json" --assignment-sha256 "$SHA" 2>/dev/null)"
VD="$(python3 -c 'import json,sys;o=json.loads(open(sys.argv[1]).readline());print(o["aproximacao_valida"],o["serving_fd_n"])' "$T/ndDel.ndjson" 2>/dev/null)"
kill "$SLEEP_DEL" 2>/dev/null
if [[ "$VD" == "sim 1" ]] && [[ "$LD" == *"aproximacao_valida=sim"* ]]; then
  echo "ok   T22 fd (deleted) é lido — o único fd que importa em produção"
else
  echo "FALHA T22 fd (deleted) ignorado: $VD"; echo "      status: $LD"; FALHAS=$((FALHAS + 1))
fi

# ── T23: mata M5 (`head -1` → `tail -1`). DOIS `.db` distintos abertos pelo mesmo
#        pid ⇒ os dois shas no recibo, e `sim` se o corpus está ENTRE eles.
#        Nenhum caso anterior montava dois fds, então `head` e `tail` eram
#        behaviouralmente idênticos em toda a suíte. E `ls -l /proc/PID/fd` ordena
#        LEXICOGRAFICAMENTE (`10` antes de `2`, medido na VPS): "o primeiro" não é
#        o menor fd, é acidente. A perna passou a coletar todos — o `head`/`tail`
#        deixa de existir em vez de ser escolhido certo.
cp "$T/corpusB.db" "$T/epocas/outro.db"
sleep 300 < "$T/epocas/servido.db" 9< "$T/epocas/outro.db" &
SLEEP_2=$!
echo "$SLEEP_2" > "$T/mainpid-2"
: > "$T/nd2fd.ndjson"
L2="$(PATH="$T/bin:$PATH" FAKE_MAINPID="$T/mainpid-2" FD_PREFIX="$T/epocas/" \
      "$GAT" --raiz "$T" --harness "$T/harness-stub.mjs" --corpus "$T/corpusB.db" \
        --vivo "$T/vivo.db" --designacao "$T/desig.json" --designacao-sha256 deadbeef \
        --tmp "$T" --ndjson "$T/nd2fd.ndjson" --modo active --log "$T/log.ndjson" \
        --assignment "$T/a.json" --assignment-sha256 "$SHA" 2>/dev/null)"
V2="$(python3 -c '
import json,sys
o=json.loads(open(sys.argv[1]).readline())
l=o["serving_fd_sha256s"]
print(o["aproximacao_valida"], o["serving_fd_n"], len(l) if isinstance(l,list) else -1, sorted(l)==sorted(sys.argv[2:]) if isinstance(l,list) else False)
' "$T/nd2fd.ndjson" "$SHA_A" "$SHA_B" 2>/dev/null)"
kill "$SLEEP_2" 2>/dev/null
if [[ "$V2" == "sim 2 2 True" ]] && [[ "$L2" == *"serving_fd_n=2"* ]]; then
  echo "ok   T23 dois fds ⇒ os dois shas no recibo; sim porque o corpus está entre eles"
else
  echo "FALHA T23 escolha arbitrária de fd: $V2"; echo "      status: $L2"; FALHAS=$((FALHAS + 1))
fi

# ── T24: mata M7 (tirar o `\.db` do filtro). Um `.json` aberto junto de um `.db`.
#        `[^ ]+` é guloso, então com ou sem o sufixo o resultado é idêntico em
#        qualquer fixture que só tenha `.db` — o mutante era indistinguível. O
#        diretório real dos epochs tem 4 `.db` contra 17 `.json` (manifests): sem
#        o sufixo, a perna compararia o corpus com um manifest.
printf '{"manifest":true}' > "$T/epocas/manifesto.json"
sleep 300 < "$T/epocas/servido.db" 9< "$T/epocas/manifesto.json" &
SLEEP_J=$!
echo "$SLEEP_J" > "$T/mainpid-j"
: > "$T/ndJson.ndjson"
LJ="$(PATH="$T/bin:$PATH" FAKE_MAINPID="$T/mainpid-j" FD_PREFIX="$T/epocas/" \
      "$GAT" --raiz "$T" --harness "$T/harness-stub.mjs" --corpus "$T/corpusA.db" \
        --vivo "$T/vivo.db" --designacao "$T/desig.json" --designacao-sha256 deadbeef \
        --tmp "$T" --ndjson "$T/ndJson.ndjson" --modo active --log "$T/log.ndjson" \
        --assignment "$T/a.json" --assignment-sha256 "$SHA" 2>/dev/null)"
VJ="$(python3 -c '
import json,sys
o=json.loads(open(sys.argv[1]).readline())
l=o["serving_fd_sha256s"]
print(o["aproximacao_valida"], o["serving_fd_n"], l==[sys.argv[2]] if isinstance(l,list) else False)
' "$T/ndJson.ndjson" "$SHA_A" 2>/dev/null)"
kill "$SLEEP_J" 2>/dev/null
if [[ "$VJ" == "sim 1 True" ]] && [[ "$LJ" == *"serving_fd_n=1"* ]]; then
  echo "ok   T24 manifest .json é ignorado — só o .db entra na comparação"
else
  echo "FALHA T24 .json entrou na comparação: $VJ"; echo "      status: $LJ"; FALHAS=$((FALHAS + 1))
fi

# ── T25: mata M6, que era DEFEITO, não só mutante sobrevivente. Corpus ILEGÍVEL
#        (symlink pendurado) com serving VIVO caía no `else` e o recibo AFIRMAVA
#        `aproximacao_valida=nao` — afirmação positiva de divergência sem ter lido
#        um dos dois operandos. Não é o silêncio da regra 9 do CLAUDE.md; é o
#        agravante dela, e no campo que o morning report lê. Cenário banal:
#        `current.db` relinkado às 06:02 para arquivo ainda não criado.
#        Simétrico a T20: sem corpus lido dá `indeterminada`, NUNCA `nao`.
ln -sf "$T/nao-existe-nenhum.db" "$T/pendurado.db"
sleep 300 < "$T/epocas/servido.db" &
SLEEP_P=$!
echo "$SLEEP_P" > "$T/mainpid-p"
: > "$T/ndPend.ndjson"
LP="$(PATH="$T/bin:$PATH" FAKE_MAINPID="$T/mainpid-p" FD_PREFIX="$T/epocas/" \
      "$GAT" --raiz "$T" --harness "$T/harness-stub.mjs" --corpus "$T/pendurado.db" \
        --vivo "$T/vivo.db" --designacao "$T/desig.json" --designacao-sha256 deadbeef \
        --tmp "$T" --ndjson "$T/ndPend.ndjson" --modo active --log "$T/log.ndjson" \
        --assignment "$T/a.json" --assignment-sha256 "$SHA" 2>/dev/null)"
VP="$(python3 -c 'import json,sys;o=json.loads(open(sys.argv[1]).readline());print(o["aproximacao_valida"],o["corpus_sha256"])' "$T/ndPend.ndjson" 2>/dev/null)"
kill "$SLEEP_P" 2>/dev/null
if [[ "$VP" == "indeterminada nao-calculado" ]] && [[ "$LP" == *"aproximacao_valida=indeterminada"* ]]; then
  echo "ok   T25 corpus ilegível ⇒ indeterminada (não afirma 'nao' sem ler o operando)"
else
  echo "FALHA T25 afirmou divergência sem ler o corpus: $VP"; echo "      status: $LP"
  FALHAS=$((FALHAS + 1))
fi

# ── T26: `--corpus` apontando para um fd DELETADO tem sha calculado, não
#        `nao-calculado`. `readlink -f` devolve o nome original com ` (deleted)`, e
#        esse caminho não existe; hashear o resultado do readlink degradaria a
#        leitura a `indeterminada` num caso em que o dado está disponível. O rótulo
#        continua vindo do readlink (é informativo: `orig.db (deleted)`), o hash vem
#        do argumento. Para symlink comum os dois coincidem — T17 é esse controle, e
#        precisa seguir passando.
cp "$T/corpusA.db" "$T/epocas/paraofd.db"
exec 8< "$T/epocas/paraofd.db"
rm -f "$T/epocas/paraofd.db"
sleep 300 < /proc/self/fd/8 8<&- &
SLEEP_FD=$!
exec 8<&-
FDN="$(ls -l "/proc/$SLEEP_FD/fd" 2>/dev/null | sed -nE 's#^.* ([0-9]+) -> .*paraofd\.db( \(deleted\))?$#\1#p' | head -1)"
if [ -z "$FDN" ]; then
  echo "FALHA T26 fixture quebrada: nenhum fd para paraofd.db"; FALHAS=$((FALHAS + 1))
else
  echo "$SLEEP_FD" > "$T/mainpid-fdcorpus"
  : > "$T/ndFdC.ndjson"
  LFC="$(PATH="$T/bin:$PATH" FAKE_MAINPID="$T/mainpid-fdcorpus" FD_PREFIX="$T/epocas/" \
        "$GAT" --raiz "$T" --harness "$T/harness-stub.mjs" \
          --corpus "/proc/$SLEEP_FD/fd/$FDN" --vivo "$T/vivo.db" \
          --designacao "$T/desig.json" --designacao-sha256 deadbeef \
          --tmp "$T" --ndjson "$T/ndFdC.ndjson" --modo active --log "$T/log.ndjson" \
          --assignment "$T/a.json" --assignment-sha256 "$SHA" 2>/dev/null)"
  VFC="$(python3 -c 'import json,sys;o=json.loads(open(sys.argv[1]).readline());print(o["corpus_sha256"])' "$T/ndFdC.ndjson" 2>/dev/null)"
  if [ "$VFC" = "$SHA_A" ] && [[ "$LFC" == *"corpus_sha256=${SHA_A:0:12}"* ]]; then
    echo "ok   T26 corpus vindo de fd deletado tem sha do ARGUMENTO, não nao-calculado"
  else
    echo "FALHA T26 sha degradado: $VFC (esperado $SHA_A)"; echo "      status: $LFC"
    FALHAS=$((FALHAS + 1))
  fi
fi
kill "$SLEEP_FD" 2>/dev/null

echo
[ "$FALHAS" -eq 0 ] && echo "TODOS OS CASOS PASSARAM" || echo "$FALHAS CASO(S) FALHARAM"
exit 0
