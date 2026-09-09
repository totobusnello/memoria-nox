#!/bin/bash
# Cadência horária. READ-ONLY (só le /proc e stat). Vigia §10.10.
set -uo pipefail

# ══ AUTO-APOSENTADORIA — ordenada pelo Toto em 2026-09-09 ═════════════════════
# Este guarda vigia o ensaio do Paper 2, que encerra em 2026-09-20 22:51:23Z. Com a
# dose desligada a pergunta dele fica VAZIA, e guarda que responde vermelho a
# pergunta encerrada e' o alarme cronicamente vermelho -- o que ensina a ignorar
# alarme, que e' o defeito tratado no §10.17.
#
# A PERNA E' A PRIMEIRA COISA DO SCRIPT: qualquer pre-condicao que possa disparar
# antes dela transforma um estado-final-ESPERADO em alarme. Custa nada e e' defensivo.
#
# ⚠️ ERRATA 2026-09-09, e a razao original estava ERRADA. Eu escrevi aqui que o
# `desliga-dose-p2.sh` faria as vars `NOX_P2_*` desaparecerem do unit, e que sem esta
# ordenacao o `run-designados.sh` sairia `RED designacao-ausente-no-unit` para sempre.
# MEDIDO nos drop-ins, apos a sessao par contestar:
#
#   p2-designation.conf   NOX_P2_DESIGNATION, NOX_P2_DESIGNATION_SHA256
#   p2s2-shadow.conf      NOX_P2_OUTCOME=shadow, NOX_P2_SERVING_LOG, NOX_P2_SHADOW_W
#   zz-p2-active.conf     NOX_P2_ASSIGNMENT, NOX_P2_ASSIGNMENT_SHA256, NOX_P2_OUTCOME=active
#
# O desliga arquiva SO o `zz-`. `DESIGNATION` sobrevive e `OUTCOME` sobrevive como
# `shadow` -- que e' justamente o que faz esta perna disparar. Nenhum dos 4 wrappers
# fica falsamente RED por var ausente.
#
# O `RED` que a minha mutacao mostrou era ARTEFATO DA FIXTURE: o `systemctl` stubado
# devolvia so `OUTRA=1`, sem nenhuma `NOX_P2_*`. Ela provou "unit sem a variavel =>
# RED", que e' verdadeiro e NAO e' o estado sobre o qual eu concluia. O cenario
# testado nao reproduzia o estado da conclusao -- e um mutante pode matar o caso pelo
# motivo errado. A perna e a ordenacao continuam certas; a justificativa e' que era
# falsa, e ficar sem correcao seria mecanismo falso documentado em producao.
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
  L_P2="GREEN p2-corpus-alinhado motivo=ensaio-encerrado-dose-desligada outcome=${OUT_P2:-vazio} ts=$TS_P2"
  echo "$L_P2"
  printf '%s\n' "$L_P2" > /var/lib/nox-mem/p2/status-corpus-alinhado.txt
  printf '{"ts":"%s","tag":"p2_gatilho_corpus_alinhado","estado":"GREEN","motivo":"ensaio-encerrado-dose-desligada","outcome":"%s"}\n' \
    "$TS_P2" "${OUT_P2:-vazio}" >> /var/lib/nox-mem/p2/gatilhos.ndjson
  exit 0
fi
exec /root/.openclaw/scripts/p2/gatilho-corpus-alinhado.sh \
  --status /var/lib/nox-mem/p2/status-corpus-alinhado.txt \
  --ndjson /var/lib/nox-mem/p2/gatilhos.ndjson
