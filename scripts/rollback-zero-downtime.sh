#!/usr/bin/env bash
# =============================================================================
# OpenClaw rollback — called by upgrade-zero-downtime.sh or manually
# Usage: bash rollback-zero-downtime.sh <target_version> <rollback_dir> <backup_dir>
# Example: bash rollback-zero-downtime.sh 2026.4.25 \
#            /usr/lib/node_modules/openclaw.bak-pre-2026.4.25 \
#            /root/backups/openclaw-pre-2026.4.25
# =============================================================================
set -euo pipefail

TARGET=${1:?usage: $0 <target_version> <rollback_dir> <backup_dir>}
ROLLBACK_DIR=${2:?}
BACKUP_DIR=${3:?}
LOG=/var/log/openclaw-rollback-$(date +%Y%m%d-%H%M%S).log

exec > >(tee -a "$LOG") 2>&1
echo "=== OpenClaw rollback FROM $TARGET — $(date -Is) ==="

[[ -d "$ROLLBACK_DIR" ]] || { echo "ERROR: no snapshot at $ROLLBACK_DIR — cannot rollback"; exit 1; }

echo "[1/5] Stopping gateway..."
systemctl stop openclaw-gateway 2>/dev/null || true
sleep 2

echo "[2/5] Restoring node_modules from snapshot..."
rm -rf /usr/lib/node_modules/openclaw
mv "$ROLLBACK_DIR" /usr/lib/node_modules/openclaw

echo "[3/5] Restoring openclaw.json config..."
if [[ -f "$BACKUP_DIR/openclaw.json.bak" ]]; then
  cp "$BACKUP_DIR/openclaw.json.bak" /root/.openclaw/openclaw.json
  echo "    restored from backup"
else
  echo "    WARN: no config backup — keeping current openclaw.json"
fi

echo "[4/5] Restoring sessions.json (clear stuck fallback models)..."
if [[ -f "$BACKUP_DIR/sessions.json.bak" ]]; then
  cp "$BACKUP_DIR/sessions.json.bak" /root/.openclaw/agents/main/sessions/sessions.json
  echo "    sessions restored from backup"
else
  echo "    clearing sessions.json to prevent fallback stickiness..."
  echo '{}' > /root/.openclaw/agents/main/sessions/sessions.json 2>/dev/null || true
fi

echo "[5/5] Starting gateway..."
systemctl daemon-reload
systemctl start openclaw-gateway
sleep 8

CURRENT=$(openclaw --version 2>&1 | awk '{print $2}')
ACTIVE=$(systemctl is-active openclaw-gateway)

echo ""
echo "=== ROLLBACK COMPLETE ==="
echo "    version: $CURRENT"
echo "    gateway: $ACTIVE"
echo "    log: $LOG"

# Confirm rollback by checking harness in journals
sleep 10
HARNESS_CHECK=$(journalctl -u openclaw-gateway --since "1 min ago" --no-pager 2>/dev/null \
  | grep -ciE "harness.*not registered|PI fallback" || echo "0")
if [[ $HARNESS_CHECK -gt 0 ]]; then
  echo ""
  echo "    WARN: harness errors detected even after rollback — investigate manually"
  echo "    journalctl -u openclaw-gateway -f"
else
  echo "    harness errors: 0 — rollback appears clean"
fi
