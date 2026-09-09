#!/bin/bash
# Cadência horária. READ-ONLY (só le /proc e stat). Vigia §10.10.
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
