#!/usr/bin/env bash
# sync-obsidian-vault.sh — pull ObsidianVault from VPS via Tailscale.
# Run manually or via launchd (~/Library/LaunchAgents/com.toto.nox.obsidian-sync.plist).
#
# Behavior:
#   - rsync VPS:/root/ObsidianVault-build/ → ~/ObsidianVault/
#   - --delete to keep parity for content (Entities/, Knowledge Graph/, README.md)
#   - PRESERVE local-only customizations (themes, plugins, snippets, settings)
#
# Read-only safeguard: rsync --delete só toca o conteúdo gerado pela VPS.
# Source files on VPS em /root/.openclaw/workspace/memory/entities/ NUNCA são tocados.
#
# Excludes (sobrevivem ao --delete):
#   .obsidian/workspace*.json    — UI state (open tabs, sidebar layout) local-only
#   .obsidian/cache              — Obsidian internal cache
#   .obsidian/themes/            — themes instalados localmente (Things, AnuPpuccin, etc)
#   .obsidian/plugins/           — community plugins (Dataview, Juggl, BRAT, 3D Graph, etc)
#   .obsidian/snippets/          — CSS snippets (galaxy-nox, cyberpunk, retrowave, etc)
#   .obsidian/community-plugins.json  — lista de plugins habilitados
#   .obsidian/appearance.json    — theme + dark mode + snippets enabled
#   .obsidian/hotkeys.json       — custom keybindings
#   .obsidian/types.json         — frontmatter type customizations
#   .obsidian/graph.json         — color groups + graph view settings
#   .obsidian/plugins/3d-graph/data.json  — 3d graph config
#
# IMPORTANTE: VPS gera só o CONTEÚDO (.md). Configs visuais, plugins, themes vivem
# 100% no Mac. Esse design preserva customização visual entre re-syncs diários.

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
    --exclude='.obsidian/themes/' \
    --exclude='.obsidian/plugins/' \
    --exclude='.obsidian/snippets/' \
    --exclude='.obsidian/community-plugins.json' \
    --exclude='.obsidian/appearance.json' \
    --exclude='.obsidian/hotkeys.json' \
    --exclude='.obsidian/types.json' \
    --exclude='.obsidian/graph.json' \
    --exclude='.obsidian/types/' \
    --exclude='00-Toto/' \
    --exclude='TaskNotes/Views/' \
    --exclude='.obsidian/daily-notes.json' \
    --exclude='.obsidian/core-plugins.json' \
    "$VPS_HOST:$REMOTE_VAULT" "$LOCAL_VAULT"

  COUNT=$(find "$LOCAL_VAULT" -name '*.md' | wc -l | tr -d ' ')
  THEMES=$(ls "$LOCAL_VAULT/.obsidian/themes" 2>/dev/null | wc -l | tr -d ' ')
  PLUGINS=$(ls "$LOCAL_VAULT/.obsidian/plugins" 2>/dev/null | wc -l | tr -d ' ')
  SNIPPETS=$(ls "$LOCAL_VAULT/.obsidian/snippets" 2>/dev/null | wc -l | tr -d ' ')
  echo "[$(ts)] sync OK — $COUNT .md files | themes=$THEMES plugins=$PLUGINS snippets=$SNIPPETS"
} 2>&1 | tee -a "$LOG"
