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
