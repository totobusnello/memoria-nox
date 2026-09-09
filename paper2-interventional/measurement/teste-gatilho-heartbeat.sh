#!/usr/bin/env bash
# teste-gatilho-heartbeat.sh — mutação do guarda de heartbeat do serving.
#
# Cada caso constrói o estado do mundo que deveria produzir o veredito, e falha
# se o veredito for outro — inclusive quando o veredito "errado" seria o
# otimista. Um guarda não testado é uma crença sobre um guarda.
#
# ⚠️ O bloco de MUTAÇÃO no fim não confia no `sed`: verifica que o arquivo
# mutado existe, não está vazio e difere do original ANTES de rodar o caso.
# Lição de 2026-09-08: um `sed` que produziu arquivo vazio passou por mutação
# válida porque o comparador só olhava se algo mudou.
set -uo pipefail
GAT="${1:-$(dirname "$0")/gatilho-heartbeat.sh}"
[ -f "$GAT" ] || { echo "ERRO: gatilho inexistente: $GAT" >&2; exit 2; }
T="$(mktemp -d /var/tmp/teste-heartbeat-XXXXXX)"
trap 'rm -rf "$T"' EXIT
FALHAS=0

# Relógio congelado. `epoch corrente` = [09-09 09:00Z, agora);
#                    `epoch fechado`  = [09-08 09:00Z, 09-09 09:00Z).
AGORA="2026-09-09T10:00:00Z"

# Gera um ndjson de serving sintético.
#   $1=arquivo  $2=n no epoch fechado  $3=n no epoch corrente  $4=ts do ultimo (ou "")
mklog() {
  python3 - "$1" "$2" "$3" "${4:-}" <<'PY'
import json, sys, datetime as dt
arq, nf, nc, ultimo = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
fech = dt.datetime(2026, 9, 8, 9, 0, tzinfo=dt.timezone.utc)
corr = dt.datetime(2026, 9, 9, 9, 0, tzinfo=dt.timezone.utc)
def z(t): return t.strftime("%Y-%m-%dT%H:%M:%S.000Z")
linhas = []
# Ruído com outra tag: o guarda não pode contá-lo como serving.
linhas.append(json.dumps({"ts": z(fech), "tag": "p2_designacao", "nota": "nao e serving"}))
for i in range(nf):
    linhas.append(json.dumps({"ts": z(fech + dt.timedelta(seconds=60 * i)),
                              "tag": "p2_outcome", "brief_id": f"f{i}",
                              "ids_controle": list(range(10))}))
for i in range(nc):
    linhas.append(json.dumps({"ts": z(corr + dt.timedelta(seconds=60 * i)),
                              "tag": "p2_outcome", "brief_id": f"c{i}",
                              "ids_controle": list(range(10))}))
if ultimo:
    linhas.append(json.dumps({"ts": ultimo, "tag": "p2_outcome", "brief_id": "ultimo",
                              "ids_controle": list(range(10))}))
open(arq, "w").write("\n".join(linhas) + "\n")
PY
}

roda() {  # $@ = args extra
  bash "$GAT" --log "$T/serving.ndjson" --agora "$AGORA" --teto-s 3600 --esperado 672 \
    --ndjson "$T/nd.ndjson" "$@" 2>&1
}
espera() {  # $1=rot $2=estado $3=substring
  local rot="$1" est="$2" sub="$3"; shift 3
  local l; l="$(roda "$@")"
  if [ "${l%% *}" = "$est" ] && [[ "$l" == *"$sub"* ]]; then echo "ok   $rot"
  else echo "FALHA $rot"; echo "      esperado: $est ... $sub"; echo "      obtido:   $l"; FALHAS=$((FALHAS+1)); fi
}
nd_linhas() { [ -f "$T/nd.ndjson" ] && grep -c . "$T/nd.ndjson" || echo 0; }

# ── T1: serving vivo, unidade fechada inteira ⇒ GREEN.
#        O ultimo registro fica 60 s atras: idade muito abaixo do teto.
mklog "$T/serving.ndjson" 672 0 "2026-09-09T09:59:00.000Z"
espera "T1 vivo e unidade inteira" GREEN "motivo=serving-vivo-e-unidade-inteira"

# ── T2: silencio de 40 h ⇒ RED. ESTE e o caso do epoch 2026-09-02, o defeito
#        que motivou o guarda: 32,53 h sem nenhum registro, e nada disparou.
mklog "$T/serving.ndjson" 0 0 "2026-09-07T18:00:00.000Z"
espera "T2 serving parado ha 40h" RED "motivo=serving-parado"

# ── T3: log inexistente ⇒ RED. Nao GREEN por falta de dado.
rm -f "$T/serving.ndjson"
espera "T3 log inexistente" RED "motivo=log-ausente"

# ── T4: log abre e nao tem NENHUM p2_outcome (so a tag de ruido) ⇒ RED.
printf '%s\n' '{"ts":"2026-09-09T09:30:00.000Z","tag":"p2_designacao"}' > "$T/serving.ndjson"
espera "T4 log sem nenhum registro de serving" RED "motivo=sem-registro"

# ── T5: um ts no FUTURO sobre um serving realmente parado ha 40 h.
#        Sem a perna 3 a idade fica NEGATIVA, a perna 4 nunca morde e o guarda
#        diria que esta tudo bem. E o unico caso em que uma linha corrompida
#        compra silencio sobre a falha mais grave.
mklog "$T/serving.ndjson" 0 0 "2026-09-09T23:00:00.000Z"
espera "T5 ts no futuro cega a perna de silencio" RED "motivo=ts-no-futuro"

# ── T6: epoch fechado com 441 de 672 ⇒ RED. E o caso do 2026-09-03, que o
#        gatilho de saturacao deixa passar (ele so alarma abaixo de n=30).
mklog "$T/serving.ndjson" 441 0 "2026-09-09T09:59:00.000Z"
espera "T6 unidade fechada parcial (441/672)" RED "faltam=231"

# ── T7: incoerencia na direcao OPOSTA — mais registros do que o desenho preve.
#        A comparacao e `!=`, nao `<`, pela mesma razao que no gatilho de
#        saturacao: um excesso tambem e desvio, e o `>` o deixaria calado.
mklog "$T/serving.ndjson" 673 0 "2026-09-09T09:59:00.000Z"
espera "T7 unidade fechada com excesso" RED "excedem=1"

# ── T8: nada fechado ainda no log ⇒ YELLOW, nao GREEN. Afirmar que a unidade
#        esta inteira sem ter unidade e afirmar sem dado.
mklog "$T/serving.ndjson" 0 30 "2026-09-09T09:59:00.000Z"
espera "T8 sem epoch fechado ⇒ pergunta nao se aplica" YELLOW "sem-epoch-fechado-no-log"

# ── T9: a fronteira do teto. Exatamente no teto passa; um segundo acima morde.
#        Sem os dois lados, um `>=` trocado por `>` (ou o inverso) nao apareceria.
mklog "$T/serving.ndjson" 672 0 "2026-09-09T09:00:00.000Z"   # idade = 3600 s
espera "T9a idade exatamente no teto ⇒ GREEN" GREEN "idade_s=3600.0"
mklog "$T/serving.ndjson" 672 0 "2026-09-09T08:59:59.000Z"   # idade = 3601 s
espera "T9b um segundo acima do teto ⇒ RED" RED "motivo=serving-parado"

# ── T10: TODO caminho de saida grava NDJSON, inclusive o de log ausente.
#         Licao de 2026-09-08 (§10.8): veredito por atalho que so vai para o
#         status e perda permanente, porque a execucao seguinte sobrescreve.
rm -f "$T/nd.ndjson" "$T/serving.ndjson"
bash "$GAT" --log "$T/serving.ndjson" --agora "$AGORA" --ndjson "$T/nd.ndjson" >/dev/null 2>&1
N10="$(nd_linhas)"
V10="$(python3 -c "
import json
ls=[json.loads(l) for l in open('$T/nd.ndjson') if l.strip()]
print(f'n={len(ls)} tag={ls[0][\"tag\"] if ls else None} estado={ls[0][\"estado\"] if ls else None}')
" 2>/dev/null)"
if [ "$N10" = 1 ] && [[ "$V10" == "n=1 tag=p2_gatilho_heartbeat estado=RED" ]]; then
  echo "ok   T10 caminho de log-ausente tambem grava NDJSON"
else echo "FALHA T10 caminho de recusa sem NDJSON"; echo "      obtido: n=$N10 $V10"; FALHAS=$((FALHAS+1)); fi

# ── T11: a tag de ruido nao entra na contagem. Se entrasse, um epoch fechado
#         com 671 registros de serving + 1 de outra tag passaria por inteiro.
mklog "$T/serving.ndjson" 671 0 "2026-09-09T09:59:00.000Z"
espera "T11 tag alheia nao conta como serving" RED "n_fechado=671"

# ─── MUTAÇÃO ────────────────────────────────────────────────────────────────
# Cada mutação remove UMA perna e o caso correspondente tem de MORRER. Antes de
# rodar, confere-se que o arquivo mutado nao esta vazio e difere do original.
echo
echo "── mutacao"
mutar() {  # $1=rot $2=expressao sed $3..=comando de checagem
  local rot="$1" expr="$2"; shift 2
  local M="$T/mut.sh"
  sed "$expr" "$GAT" > "$M" 2>/dev/null
  if [ ! -s "$M" ]; then
    echo "FALHA $rot: sed produziu arquivo VAZIO — a mutacao nao foi aplicada"
    FALHAS=$((FALHAS+1)); return
  fi
  if cmp -s "$M" "$GAT"; then
    echo "FALHA $rot: sed nao mudou nada — a mutacao nao casou"
    FALHAS=$((FALHAS+1)); return
  fi
  "$@" "$M" "$rot"
}
# Roda um caso contra o gatilho MUTADO e exige que o veredito NÃO seja mais o
# esperado pelo original.
#
# ⚠️ Exige tambem que o mutante RODE. Um mutante que morre de erro de sintaxe
# "mata" todos os casos e nao prova nada sobre perna nenhuma — foi o que a
# primeira versao deste bloco fez com M3 e M4, apagando linhas no meio de uma
# f-string de varias linhas. Por isso toda mutacao aqui e uma TROCA de
# expressao, nunca um `d` de faixa, e o veredito tem de ser uma linha de status
# reconhecivel.
morre() {  # $1=n_fech $2=n_corr $3=ultimo $4=estado_orig $5=sub_orig $6=agora $7=arquivo $8=rot
  mklog "$T/serving.ndjson" "$1" "$2" "$3"
  local l; l="$(bash "$7" --log "$T/serving.ndjson" --agora "$6" --teto-s 3600 --esperado 672 2>&1)"
  case "${l%% *}" in
    GREEN|YELLOW|RED) ;;
    *) echo "FALHA $8: o mutante NAO RODOU (sem linha de status) — mutacao invalida"
       echo "      obtido: $(printf '%s' "$l" | head -3)"; FALHAS=$((FALHAS+1)); return;;
  esac
  if [ "${l%% *}" = "$4" ] && [[ "$l" == *"$5"* ]]; then
    echo "FALHA $8: o caso SOBREVIVEU a mutacao (veredito inalterado)"
    echo "      obtido: $l"; FALHAS=$((FALHAS+1))
  else
    echo "ok   $8 mata o caso  ⇒ $(printf '%s' "$l" | cut -c1-78)"
  fi
}

# M1 — sem a perna do futuro, um serving parado com ts corrompido deixa de ser RED.
mutar "M1 (neutraliza perna ts-no-futuro)" 's/^if idade < -tol:/if False and idade < -tol:/' \
  morre 0 0 "2026-09-09T23:00:00.000Z" RED "motivo=ts-no-futuro" "$AGORA"
# M2 — sem a perna de silencio, o silencio fica TOTALMENTE invisivel. O mundo
#      deste caso e o que prova isso: a unidade fechada esta INTEIRA (672) e o
#      silencio comecou dentro do epoch corrente, entao nenhuma outra perna
#      pega. Com `agora` = 20:00Z o ultimo registro tem 5 h.
mutar "M2 (neutraliza perna serving-parado)" 's/^if idade > teto:/if False and idade > teto:/' \
  morre 672 0 "2026-09-09T15:00:00.000Z" RED "motivo=serving-parado" "2026-09-09T20:00:00Z"
# M3 — sem a perna de unidade, 441/672 passa por inteiro.
mutar "M3 (neutraliza perna unidade-incompleta)" 's/^if n_fechado != esperado:/if False and n_fechado != esperado:/' \
  morre 441 0 "2026-09-09T09:59:00.000Z" RED "faltam=231" "$AGORA"
# M4 — a perna de log vazio virando GREEN: o guarda passa a afirmar que esta
#      tudo bem sobre um log que nao tem nenhum registro de serving.
mutar "M4 (perna sem-registro devolve GREEN)" 's/saida("RED", "sem-registro"/saida("GREEN", "sem-registro"/' \
  morre 0 0 "" RED "motivo=sem-registro" "$AGORA"
# M5 — trocar `!=` por `<` na perna 5 deixa o EXCESSO calado.
mutar "M5 (troca != por < na unidade)" 's/^if n_fechado != esperado:/if n_fechado < esperado:/' \
  morre 673 0 "2026-09-09T09:59:00.000Z" RED "excedem=1" "$AGORA"

echo
[ "$FALHAS" -eq 0 ] && echo "TODOS OS CASOS PASSARAM" || echo "$FALHAS CASO(S) FALHARAM"
exit 0
