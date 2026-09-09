#!/bin/bash
# Cadência horária. READ-ONLY (só le o ndjson do serving e o relógio).
# Vigia a perna que faltava: "o serving parou" e "a unidade que fechou está
# inteira" — as duas coisas que nenhum outro gatilho deste ensaio pode ver,
# porque todos leem O ÚLTIMO EPOCH e ficam calados quando não há epoch nenhum.
#
# ⚠️ A configuração vem do UNIT DO SYSTEMD, não do `.env`: o caminho do log é o
# que a produção realmente escreve. Mesma disciplina do run-saturacao.sh.
#
# ⚠️ TETO = 3600 s, calibrado por medição em 2026-09-09 sobre 11.396 registros:
# maior intervalo normal 936 s (0,26 h, a cadência do brief-refresh), e só 2
# intervalos acima de 1 h em 19 dias — os dois incidentes conhecidos. Folga de
# 3,85x. Se a cadência do brief-refresh mudar, este teto tem de ser remedido:
# ele é 4x o intervalo entre rajadas, não um número redondo.
#
# ⚠️ ESPERADO = 672 registros por epoch = 4 rajadas/h x 24 h x 7 BRIEFS POR
# RAJADA. Sao 6 agentes, nao 7: medido no epoch 2026-09-08, nox=192 e
# atlas/boris/cipher/forge/lex=96 cada (28 briefs/h). O `nox` entra DUAS vezes
# por rajada. O 672 estava certo e a derivacao atribuia a populacao errada --
# mesma classe do caso `au[0]`; corrigido 2026-09-09 apos contar por agente.
# Vale na era `active` e valeu em todo epoch completo medido (08-29 a 09-01,
# 09-05 a 09-08). O `677` de 27/08 é pré-active, de outro regime.
#
# ⚠️ MINUTO :54, escolhido para não colidir com os outros gatilhos (:9 composição,
# :24 designados, :39 corpus-alinhado) nem com o brief-refresh (:7,:22,:37,:52).
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
  L_P2="GREEN p2-heartbeat-do-serving motivo=ensaio-encerrado-dose-desligada outcome=${OUT_P2:-vazio} ts=$TS_P2"
  echo "$L_P2"
  printf '%s\n' "$L_P2" > /var/lib/nox-mem/p2/status-heartbeat.txt
  printf '{"ts":"%s","tag":"p2_gatilho_heartbeat","estado":"GREEN","motivo":"ensaio-encerrado-dose-desligada","outcome":"%s"}\n' \
    "$TS_P2" "${OUT_P2:-vazio}" >> /var/lib/nox-mem/p2/gatilhos.ndjson
  exit 0
fi
exec /root/.openclaw/scripts/p2/gatilho-heartbeat.sh \
  --teto-s 3600 \
  --esperado 672 \
  --status /var/lib/nox-mem/p2/status-heartbeat.txt \
  --ndjson /var/lib/nox-mem/p2/gatilhos.ndjson
