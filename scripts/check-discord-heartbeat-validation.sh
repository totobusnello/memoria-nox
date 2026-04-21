#!/bin/bash
# check-discord-heartbeat-validation.sh
# Criado em 2026-04-20 como handoff pra validar Discord heartbeat + fixes pós cost reduction pass
# Uso: bash scripts/check-discord-heartbeat-validation.sh
# Roda 2026-04-21 manhã após rotina 07h-12h

VPS_HOST="root@100.87.8.44"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  Validação pós cost reduction pass — 2026-04-21                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
date
echo ""

echo "━━━ 1. Gateway está vivo? ━━━"
ssh "$VPS_HOST" 'systemctl is-active openclaw-gateway && echo "PID: $(systemctl show openclaw-gateway -p MainPID --value)" && echo "Uptime: $(systemctl show openclaw-gateway -p ActiveEnterTimestamp --value)"'
echo ""

echo "━━━ 2. Crons Discord — entregaram? ━━━"
echo "Boris LinkedIn (08:15 L-V):"
ssh "$VPS_HOST" 'openclaw cron runs --id b1592ecb-e512-428e-81df-93d68147d5ca 2>&1 | jq ".entries[0] | {ts: (.ts|todate), status, deliveryStatus, delivered, durationMs, error: .error[0:100]}"' 2>&1 | head -10
echo ""
echo "weekly-team-status (Seg 12:00):"
ssh "$VPS_HOST" 'openclaw cron runs --id ec44dd9b-af29-4468-8bf8-08d34917fcc9 2>&1 | jq ".entries[0] | {ts: (.ts|todate), status, deliveryStatus, delivered, durationMs, error: .error[0:100]}"' 2>&1 | head -10
echo ""

echo "━━━ 3. Heartbeat events 12h (sent/failed count) ━━━"
ssh "$VPS_HOST" 'journalctl -u openclaw-gateway --since "12 hours ago" --no-pager 2>/dev/null | grep -iE "heartbeat.*(sent|failed|delivered|skipped)" | grep -oE "heartbeat.*(sent|failed|delivered|skipped)[a-z: -]*" | sort | uniq -c | sort -rn | head -10'
echo ""

echo "━━━ 4. Erros 429 / model_not_found (deveria ser 0) ━━━"
ssh "$VPS_HOST" 'journalctl -u openclaw-gateway --since "12 hours ago" --no-pager 2>/dev/null | grep -cE "429|model_not_found|no longer available"'
echo ""

echo "━━━ 5. Modelos chamados (distribuição) ━━━"
ssh "$VPS_HOST" 'journalctl -u openclaw-gateway --since "12 hours ago" --no-pager 2>/dev/null | grep -oE "model=[a-z0-9.-]+ provider=[a-z]+" | sort | uniq -c | sort -rn | head -10'
echo ""

echo "━━━ 6. Fallback chain ativada alguma vez? ━━━"
ssh "$VPS_HOST" 'journalctl -u openclaw-gateway --since "12 hours ago" --no-pager 2>/dev/null | grep -E "failover decision" | grep -oE "decision=[a-z_]+|from=[a-z/0-9.-]+" | sort | uniq -c | head -10'
echo ""

echo "━━━ 7. Crons que rodaram 24h (último status) ━━━"
ssh "$VPS_HOST" 'openclaw cron list 2>&1 | grep -E "ok|error|min ago|h ago" | head -15'
echo ""

echo "━━━ 8. Gemini quota (via log — se algum 429 aparecer, quota acabou) ━━━"
ssh "$VPS_HOST" 'journalctl -u openclaw-gateway --since "24 hours ago" --no-pager 2>/dev/null | grep -cE "gemini.*429|gemini.*rate limit|gemini.*quota" || echo "0"'
echo ""

echo "━━━ 9. RelayPlane — ainda zumbi? ━━━"
ssh "$VPS_HOST" 'echo -n "Service: "; systemctl is-active relayplane-proxy; echo -n "ANTHROPIC_BASE_URL no env do gateway: "; tr "\0" "\n" < /proc/$(systemctl show openclaw-gateway -p MainPID --value)/environ 2>/dev/null | grep -c "ANTHROPIC_BASE_URL" || echo "0"; echo -n "Runs em data.db 24h: "; sqlite3 /root/.relayplane/data.db "SELECT COUNT(*) FROM runs WHERE created_at > datetime(\"now\",\"-1 day\");" 2>/dev/null'
echo ""

echo "━━━ 10. nox-mem-api health ━━━"
ssh "$VPS_HOST" 'curl -sf http://127.0.0.1:18802/api/health | jq "{status, vectorCoverage: .vectorCoverage.embedded, total: .vectorCoverage.total, agents: (.agents|length)}"' 2>&1 | head -10
echo ""

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  Fim da validação. Reporte os resultados pro Claude.             ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
