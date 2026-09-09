#!/bin/bash
# Cadência horária. READ-ONLY sobre o banco. Vigia a EXISTÊNCIA e a IDENTIDADE
# dos chunks designados — o único ativo insubstituível do ensaio (a designação foi
# sorteada uma vez, com semente pública, e não se refaz).
#
# ⚠️ A configuração vem do UNIT DO SYSTEMD, não do `.env`: é isso que a produção
# realmente serve. Mesma disciplina do run-saturacao.sh.
#
# ⚠️ TETO DE IDADE no morning-report: cron horário no minuto :24, report às 06:30Z
#   ⇒ idade normal 0,1 h. Com teto 3 h: rodadas_toleradas = (3 − 0,1)/1 = 2,9 ⇒
#   tolera 2 rodadas puladas e dispara na 3ª. (Cego seria rodadas_toleradas ≥ 1
#   com cron DIÁRIO — ver a correção da regra no morning-report.sh.)
set -uo pipefail

# ══ AUTO-APOSENTADORIA — ordenada pelo Toto em 2026-09-09 ═════════════════════
# Este guarda vigia o ensaio do Paper 2, que encerra em 2026-09-20 22:51:23Z. Com a
# dose desligada a pergunta dele fica VAZIA, e guarda que responde vermelho a
# pergunta encerrada e' o alarme cronicamente vermelho -- o que ensina a ignorar
# alarme, que e' o defeito tratado no §10.17.
#
# ⚠️ ESTA PERNA E' A PRIMEIRA COISA DO SCRIPT, DE PROPOSITO. O `desliga-dose-p2.sh`
# ARQUIVA o drop-in `zz-p2-active.conf`, e com ele desaparecem do unit as vars
# `NOX_P2_*`. Qualquer checagem posta antes desta veria a var ausente e emitiria o
# seu proprio erro -- no `run-designados.sh`, literalmente
# `RED designacao-ausente-no-unit`, para sempre. Guarda posterior ao uso que ele
# protege nao e' guarda.
#
# ⚠️ E ela e' INERTE enquanto o ensaio corre: so dispara com `outcome != active`.
# Instalada 11 dias antes do encerramento sem alterar comportamento nenhum hoje.
#
# GREEN aqui NAO afirma que esta tudo bem -- afirma que a pergunta nao se aplica
# mais, e o motivo diz isso. Silencio seria pior: ausencia do que era vigiado tem de
# APARECER (§10.10 custou seis dias por isso). Segunda camada, nao substituta: a
# aposentadoria tira a linha do cron; esta perna cala o alarme se alguem a rearmar.
OUT_P2="$(systemctl show nox-mem-api -p Environment --value 2>/dev/null | tr ' ' '\n' | sed -n 's/^NOX_P2_OUTCOME=//p' | tail -1)"
if [ "$OUT_P2" != active ]; then
  TS_P2="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  L_P2="GREEN p2-designados-integros motivo=ensaio-encerrado-dose-desligada outcome=${OUT_P2:-vazio} ts=$TS_P2"
  echo "$L_P2"
  printf '%s\n' "$L_P2" > /var/lib/nox-mem/p2/status-designados.txt
  printf '{"ts":"%s","tag":"p2_gatilho_designados","estado":"GREEN","motivo":"ensaio-encerrado-dose-desligada","outcome":"%s"}\n' \
    "$TS_P2" "${OUT_P2:-vazio}" >> /var/lib/nox-mem/p2/gatilhos.ndjson
  exit 0
fi
STATUS=/var/lib/nox-mem/p2/status-designados.txt
morre() { local l="$1 p2-designados-integros motivo=$2 ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
          echo "$l"; printf '%s\n' "$l" > "$STATUS"; exit 0; }

UNIT_ENV="$(systemctl show nox-mem-api -p Environment --value 2>/dev/null | tr ' ' '\n')"
pega() { printf '%s\n' "$UNIT_ENV" | sed -n "s/^$1=//p" | tail -1; }
DESIG="$(pega NOX_P2_DESIGNATION)"
DESIG_SHA="$(pega NOX_P2_DESIGNATION_SHA256)"
[ -n "$DESIG" ] || morre RED designacao-ausente-no-unit
[ -n "$DESIG_SHA" ] || morre RED designacao-sha256-ausente-no-unit

exec timeout 120 node /root/.openclaw/scripts/p2/gatilho-designados.mjs \
  --vivo /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  --designacao "$DESIG" --designacao-sha256 "$DESIG_SHA" \
  --baseline /var/lib/nox-mem/p2/designados-baseline.json \
  --status "$STATUS" \
  --ndjson /var/lib/nox-mem/p2/gatilhos.ndjson
