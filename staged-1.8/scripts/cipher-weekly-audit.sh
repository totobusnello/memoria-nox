#!/bin/bash
# cipher-weekly-audit.sh — Cipher weekly system audit
# Runs Sunday 04:30 BRT via crontab
# Posts structured summary to Discord #agents-hub; escalates Nox on red flags.
#
# Phase 1.8 deliverable. Zero destructive operations.
# Idempotent and dry-run safe.

set -uo pipefail

if [ -f /root/.openclaw/.env ]; then
  set -a; . /root/.openclaw/.env; set +a
fi

REPORT="/tmp/cipher-audit-$(date +%Y%m%d).md"
LOG="/var/log/cipher-audit.log"
DB="/root/.openclaw/workspace/tools/nox-mem/nox-mem.db"
RED=0
YELLOW=0

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; }

log "=== Cipher weekly audit starting ==="

{
  echo "# 🛡️ Cipher Weekly Audit — $(date '+%A, %Y-%m-%d %H:%M %Z')"
  echo
  echo "---"
  echo
  echo "## 💾 Disco e Recursos"
  DISK_PCT=$(df -h / | awk 'NR==2 {gsub("%",""); print $5}')
  DISK_FREE=$(df -h / | awk 'NR==2 {print $4}')
  MEM_PCT=$(free | awk '/Mem:/ {printf "%.0f", $3*100/$2}')
  echo "- Disco root: ${DISK_FREE} livre (${DISK_PCT}% usado)"
  echo "- RAM: ${MEM_PCT}% usado"
  if [ "$DISK_PCT" -gt 85 ] 2>/dev/null; then RED=$((RED+1)); echo "  🔴 disco >85%"; fi
  if [ "$MEM_PCT" -gt 90 ] 2>/dev/null; then YELLOW=$((YELLOW+1)); echo "  🟡 RAM >90%"; fi
  echo

  echo "## 🔥 Firewall & SSH"
  UFW_STATUS=$(ufw status 2>/dev/null | head -1 | awk '{print $2}')
  echo "- ufw: ${UFW_STATUS}"
  if [ "$UFW_STATUS" != "active" ]; then RED=$((RED+1)); fi

  if command -v fail2ban-client >/dev/null 2>&1; then
    BANNED=$(fail2ban-client status sshd 2>/dev/null | grep -oP 'Currently banned:\s+\K\d+' || echo 0)
    TOTAL_BANNED=$(fail2ban-client status sshd 2>/dev/null | grep -oP 'Total banned:\s+\K\d+' || echo 0)
    echo "- fail2ban: ${BANNED} IPs banidos agora (${TOTAL_BANNED} total histórico)"
  fi

  FAILED_AUTH=$(journalctl -u ssh --since '7 days ago' 2>/dev/null | grep -c 'Failed password' || echo 0)
  echo "- SSH auth failures (7d): ${FAILED_AUTH}"
  if [ "$FAILED_AUTH" -gt 200 ] 2>/dev/null; then YELLOW=$((YELLOW+1)); echo "  🟡 tráfego de ataques alto"; fi
  echo

  echo "## 🌐 Rede"
  TS_STATUS=$(tailscale status 2>/dev/null | head -1 | awk '{print $1}' || echo "offline")
  echo "- Tailscale: ${TS_STATUS}"
  if [ -z "$TS_STATUS" ] || [ "$TS_STATUS" = "offline" ]; then RED=$((RED+1)); fi
  echo

  echo "## 📦 Backups"
  BACKUP_DIR="/root/.openclaw/workspace/backups"
  if [ -d "$BACKUP_DIR" ]; then
    LAST_BACKUP=$(ls -t "$BACKUP_DIR" 2>/dev/null | head -1)
    LAST_BACKUP_AGE=$(find "$BACKUP_DIR" -maxdepth 1 -printf '%T@\n' 2>/dev/null | sort -rn | head -1 | awk -v now="$(date +%s)" '{printf "%.0f", (now - $1)/3600}')
    echo "- Último backup: ${LAST_BACKUP} (${LAST_BACKUP_AGE}h atrás)"
    if [ "$LAST_BACKUP_AGE" -gt 48 ] 2>/dev/null; then
      RED=$((RED+1)); echo "  🔴 backup stale >48h"
    elif [ "$LAST_BACKUP_AGE" -gt 30 ] 2>/dev/null; then
      YELLOW=$((YELLOW+1)); echo "  🟡 backup >30h"
    fi
  else
    RED=$((RED+1)); echo "- 🔴 diretório de backup não existe"
  fi
  echo

  echo "## 🧠 nox-mem Integrity"
  if [ -f "$DB" ]; then
    DB_SIZE_MB=$(du -m "$DB" | awk '{print $1}')
    INTEGRITY=$(sqlite3 "$DB" "PRAGMA integrity_check;" 2>&1 | head -1)
    echo "- Tamanho: ${DB_SIZE_MB} MB"
    echo "- Integrity: ${INTEGRITY}"
    if [ "$INTEGRITY" != "ok" ]; then RED=$((RED+1)); fi

    # Growth anomaly: compare com backup mais recente
    LAST_DB_BACKUP=$(ls -t "$BACKUP_DIR"/nox-mem*.db 2>/dev/null | head -1)
    if [ -n "$LAST_DB_BACKUP" ]; then
      PREV_SIZE_MB=$(du -m "$LAST_DB_BACKUP" | awk '{print $1}')
      if [ "$PREV_SIZE_MB" -gt 0 ] && [ "$(echo "$DB_SIZE_MB > $PREV_SIZE_MB * 2" | bc -l 2>/dev/null)" = "1" ]; then
        YELLOW=$((YELLOW+1)); echo "  🟡 DB cresceu >2× desde último backup (${PREV_SIZE_MB}→${DB_SIZE_MB}MB)"
      fi
    fi

    # Vector coverage via API
    EMB=$(curl -sf --max-time 3 "http://127.0.0.1:${NOX_API_PORT:-18800}/api/health" 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); v=d.get("vectorCoverage",{}); print(f"{v.get(\"embedded\",\"?\")}/{v.get(\"total\",\"?\")} (orphans={v.get(\"orphans\",\"?\")})")' 2>/dev/null || echo "api offline")
    echo "- Vector coverage: ${EMB}"
  else
    RED=$((RED+1)); echo "- 🔴 DB não encontrado"
  fi
  echo

  echo "## 🔐 Auth Profiles (cooldowns)"
  COOLDOWN_CT=$(find /root/.openclaw/workspace/agents -name 'auth-profiles.json' -exec grep -l 'cooldownUntil' {} \; 2>/dev/null | wc -l)
  echo "- Profiles com cooldown ativo: ${COOLDOWN_CT}"
  if [ "$COOLDOWN_CT" -gt 0 ] 2>/dev/null; then YELLOW=$((YELLOW+1)); fi
  echo

  echo "## 🔑 Secrets (idade)"
  ENV_MODIFIED=$(find /root/.openclaw/.env -printf '%T@\n' 2>/dev/null | awk -v now="$(date +%s)" '{printf "%.0f", (now - $1)/86400}')
  echo "- /root/.openclaw/.env: modificado há ${ENV_MODIFIED} dias"
  if [ "$ENV_MODIFIED" -gt 90 ] 2>/dev/null; then YELLOW=$((YELLOW+1)); echo "  🟡 secrets >90d (considere rotacionar)"; fi
  echo

  echo "---"
  echo
  echo "**Resultado:** 🔴 ${RED} red · 🟡 ${YELLOW} yellow"

  if [ "$RED" -gt 0 ]; then
    echo
    echo "⚠️ **Escalando pro Nox** — red flags detectados."
  fi

} > "$REPORT"

log "audit complete: red=$RED yellow=$YELLOW"

# Post to Discord #agents-hub (Cipher persona via gateway)
if [ -n "${DISCORD_WEBHOOK:-}" ]; then
  # Discord message body: use file content, truncate if needed
  BODY=$(cat "$REPORT")
  # Discord limit 2000 chars; truncar preservando footer
  if [ "${#BODY}" -gt 1900 ]; then
    BODY=$(echo "$BODY" | head -c 1800)
    BODY="${BODY}

... (truncated, full report: ${REPORT})"
  fi
  JSON=$(python3 -c "
import json, sys
print(json.dumps({'content': sys.argv[1], 'username': 'Cipher 🛡️', 'avatar_url': ''}))
" "$BODY" 2>/dev/null)
  if [ -n "$JSON" ]; then
    curl -s -X POST "${DISCORD_WEBHOOK}" -H "Content-Type: application/json" -d "$JSON" >> "$LOG" 2>&1
    log "posted to Discord"
  fi
fi

# Escalate to Nox via openclaw message send se red flags
if [ "$RED" -gt 0 ]; then
  openclaw message send --channel whatsapp --target "+5511982022121" \
    --message "🔴 Cipher audit: ${RED} red flags detectados. Ver Discord #agents-hub ou ${REPORT}" \
    2>> "$LOG" || log "escalation failed"
fi

log "=== done ==="
exit 0
