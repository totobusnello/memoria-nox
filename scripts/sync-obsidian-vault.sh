#!/usr/bin/env bash
# sync-obsidian-vault.sh — pull ObsidianVault from VPS via Tailscale.
# Run manually or via launchd (~/Library/LaunchAgents/com.toto.nox.obsidian-sync.plist).
#
# Behavior:
#   - rsync VPS:/root/ObsidianVault-build/ → ~/ObsidianVault/
#   - --delete to keep parity (vault is view-only, edits get overwritten)
#   - .obsidian/workspace*.json EXCLUDED from delete to preserve local UI state
#
# Read-only safeguard: this only runs `rsync --recursive --delete` on the VPS-built dir.
# Source files on VPS in /root/.openclaw/workspace/memory/entities/ are NEVER touched.

set -euo pipefail

VPS_HOST="${VPS_HOST:-root@100.87.8.44}"
REMOTE_VAULT="${REMOTE_VAULT:-/root/ObsidianVault-build/}"
LOCAL_VAULT="${LOCAL_VAULT:-$HOME/ObsidianVault/}"
LOG="${LOG:-/tmp/nox-obsidian-sync.log}"

mkdir -p "$LOCAL_VAULT"

ts() { date '+%Y-%m-%d %H:%M:%S'; }

{
  echo ""
  echo "=== [$(ts)] sync-obsidian-vault start ==="
  echo "Remote: $VPS_HOST:$REMOTE_VAULT"
  echo "Local:  $LOCAL_VAULT"

  # Check VPS reachable via Tailscale
  if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$VPS_HOST" 'true' 2>/dev/null; then
    echo "ERROR: VPS unreachable at $VPS_HOST (Tailscale up?)"
    exit 1
  fi

  rsync -av --delete \
    --exclude='.obsidian/workspace*.json' \
    --exclude='.obsidian/cache' \
    "$VPS_HOST:$REMOTE_VAULT" "$LOCAL_VAULT"

  COUNT=$(find "$LOCAL_VAULT" -name '*.md' | wc -l | tr -d ' ')
  echo "[$(ts)] sync OK — $COUNT .md files in $LOCAL_VAULT"
} 2>&1 | tee -a "$LOG"
