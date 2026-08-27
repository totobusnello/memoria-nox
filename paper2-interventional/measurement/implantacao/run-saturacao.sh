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
# Em `active` a dose vem do braço resolvido, não de NOX_P2_SHADOW_W. Vigiar com a
# dose errada é pior que não vigiar: reportaria GREEN sobre outra grandeza.
if [ "$MODO" = "active" ]; then
  morre YELLOW "modo=active-dose-vem-do-ASSIGNMENT-nao-de-SHADOW_W:reimplementar-antes-de-ativar"
fi
[ -n "$W" ] || morre RED shadow-w-ausente-no-unit

# `timeout 1500` (25 min): o job roda 05:41 e o morning-report le o status as 06:30.
# Sem teto, uma janela grande atrasaria o report em vez de so atrasar a si mesma —
# e um job que estoura o horario reporta o dia anterior como se fosse o de hoje.
exec timeout 1500 /root/.openclaw/scripts/p2/gatilho-saturacao.sh \
  --raiz /root/.openclaw/workspace/tools/nox-mem \
  --harness /root/.openclaw/scripts/p2/replay-oportunidade.mjs \
  --log "$LOGP" \
  --corpus /var/lib/nox-mem/epochs/current.db \
  --vivo /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  --designacao "$DESIG" --designacao-sha256 "$DESIG_SHA" \
  --w-servido "$W" \
  --status "$STATUS" \
  --ndjson /var/lib/nox-mem/p2/gatilhos.ndjson
