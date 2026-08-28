#!/bin/bash
# Cadência diária, sobre o dia UTC anterior INTEIRO. READ-ONLY.
#
# ⚠️ A configuração vem do UNIT DO SYSTEMD, não do `.env` nem de cópia local.
# `NOX_P2_DESIGNATION`, `NOX_P2_SHADOW_W`, `NOX_P2_OUTCOME` e `NOX_P2_SERVING_LOG`
# são declarados no drop-in do serviço — é isso que a produção realmente serve. Ler
# de outro lugar seria vigiar uma configuração que ninguém está usando, que é o
# defeito exato que o item 7 original tinha.
#
# ⚠️ APROXIMAÇÃO DECLARADA: `current.db` roda às 06:00Z, então um dia UTC inteiro
# atravessa DOIS corpora e este replay usa um só. Medido em 27/08: para os 11
# eventos de churn da janela conhecida, o snapshot de 26/08 e o de 27/08 deram
# resultado IDÊNTICO — a escolha de corpus foi inerte. Inerte não é garantido, e a
# aproximação fica em cada linha do NDJSON em vez de silenciosa.
set -uo pipefail

STATUS=/var/lib/nox-mem/p2/status-saturacao.txt
morre() {  # status YELLOW/RED sem rodar nada, para o morning report ver o motivo
  local l="$1 p2-saturacao-da-dose motivo=$2 ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "$l"; printf '%s\n' "$l" > "$STATUS"; exit 0
}

# Environment do unit, uma var por linha. `--value` devolve tudo numa linha
# separada por espaço; valores desta unidade não contêm espaço (são caminhos e
# números), e se passarem a conter isto quebra ALTO em vez de silenciosamente.
UNIT_ENV="$(systemctl show nox-mem-api -p Environment --value 2>/dev/null | tr ' ' '\n')"
pega() { printf '%s\n' "$UNIT_ENV" | sed -n "s/^$1=//p" | tail -1; }

DESIG="$(pega NOX_P2_DESIGNATION)"
DESIG_SHA="$(pega NOX_P2_DESIGNATION_SHA256)"
MODO="$(pega NOX_P2_OUTCOME)"
W="$(pega NOX_P2_SHADOW_W)"
LOGP="$(pega NOX_P2_SERVING_LOG)"
[ -n "$LOGP" ] || LOGP=/root/.openclaw/logs/p2-serving.ndjson

[ -n "$DESIG" ] || morre RED designacao-ausente-no-unit
[ -n "$DESIG_SHA" ] || morre RED designacao-sha256-ausente-no-unit
[ -f "$DESIG" ] || morre RED designacao-nao-existe-no-disco:"$DESIG"
case "$MODO" in
  shadow|active) ;;
  *) morre YELLOW "p2-outcome=${MODO:-vazio}-nada-a-vigiar" ;;
esac
# Em `active` a dose vem do braço resolvido, não de NOX_P2_SHADOW_W. Implementado
# em 28/08 (antes disto o wrapper se recusava a rodar em active, e a recusa era
# certa: vigiar com a dose errada reportaria GREEN sobre outra grandeza).
ASSIGN=""; ASSIGN_SHA=""
if [ "$MODO" = "active" ]; then
  ASSIGN="$(pega NOX_P2_ASSIGNMENT)"
  ASSIGN_SHA="$(pega NOX_P2_ASSIGNMENT_SHA256)"
  [ -n "$ASSIGN" ] || morre RED assignment-ausente-no-unit
  [ -n "$ASSIGN_SHA" ] || morre RED assignment-sha256-ausente-no-unit
  [ -f "$ASSIGN" ] || morre RED assignment-nao-existe-no-disco:"$ASSIGN"
else
  [ -n "$W" ] || morre RED shadow-w-ausente-no-unit
fi

# ⚠️ HORÁRIO: 09:12Z, movido de 05:41Z em 2026-08-28. A janela muda com o modo.
# Em active ela é o epoch [E 09:00Z, E+1 09:00Z), e às 05:41Z o último epoch
# FECHADO terminava às 09:00Z de ONTEM — ~21 h de latência de alarme. Às 09:12Z o
# gatilho reporta o epoch que acabou de fechar 12 min antes.
#
# 🔴 E o horário antigo tinha um segundo defeito, achado ao conferir o guarda: o
# `morning-report.sh` (06:30Z) YELLOWa status com mais de 30 h, mas às 05:41Z uma
# rodada PULADA envelhece só até 24,8 h ⇒ passava despercebida. Às 09:12Z a idade
# normal é 21,3 h e a de uma rodada pulada é 45,3 h ⇒ o guarda morde. O orçamento
# de 30 h ficou como está: 8,7 h de folga para atraso legítimo.
#
# ⚠️ Em `shadow` o efeito colateral é que o report descreve uma janela ~24 h mais
# velha. Aceito: o destino é `active`, a linha carrega `janela=[...]` explícita, e
# um alarme que detecta rodada pulada vale mais que um número recente.

if [ "$MODO" = "active" ]; then
  exec timeout 2700 /root/.openclaw/scripts/p2/gatilho-saturacao.sh \
    --raiz /root/.openclaw/workspace/tools/nox-mem \
    --harness /root/.openclaw/scripts/p2/replay-oportunidade.mjs \
    --log "$LOGP" \
    --corpus /var/lib/nox-mem/epochs/current.db \
    --vivo /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
    --designacao "$DESIG" --designacao-sha256 "$DESIG_SHA" \
    --modo active --assignment "$ASSIGN" --assignment-sha256 "$ASSIGN_SHA" \
    --status "$STATUS" \
    --ndjson /var/lib/nox-mem/p2/gatilhos.ndjson
fi

# `timeout` (min) : o job roda 05:41 e o morning-report le o status as 06:30.
# Sem teto, uma janela grande atrasaria o report em vez de so atrasar a si mesma —
# e um job que estoura o horario reporta o dia anterior como se fosse o de hoje.
#
# 1500 s era folga de apenas 1,65x: a rodada de 2026-08-27 levou 911 s medidos
# (677 estados de um dia). Estourar o teto faz o gatilho reportar RED por
# `interrompido-por-sinal` — RED por CAPACIDADE, nao por defeito do mecanismo, que
# e a especie de alarme que ensina a ignorar alarme. 2700 s da 2,96x sobre o
# medido e ainda cabe entre 05:41 e 06:30. `duracao_s` na linha de status e o que
# avisa antes: se ela passar de ~1800 s, subir o teto ANTES de virar RED.
exec timeout 2700 /root/.openclaw/scripts/p2/gatilho-saturacao.sh \
  --raiz /root/.openclaw/workspace/tools/nox-mem \
  --harness /root/.openclaw/scripts/p2/replay-oportunidade.mjs \
  --log "$LOGP" \
  --corpus /var/lib/nox-mem/epochs/current.db \
  --vivo /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  --designacao "$DESIG" --designacao-sha256 "$DESIG_SHA" \
  --w-servido "$W" \
  --status "$STATUS" \
  --ndjson /var/lib/nox-mem/p2/gatilhos.ndjson
