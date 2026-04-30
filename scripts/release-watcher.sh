#!/usr/bin/env bash
# release-watcher — daily 12:00 BRT cron
# - Checks GitHub for new STABLE openclaw release vs installed version
# - Runs daily improvements audit (drift detection)
# - On NEW release OR critical drift: sends direct alert via WhatsApp + Discord #forge-dev
#
# Source-of-truth: ~/Claude/Projetos/memoria-nox/scripts/release-watcher.sh
# Deployed to:     /root/.openclaw/upgrade-watcher/check.sh
#
# Notes:
# - Direct alert (no agent spawn) — keeps watcher fast, reliable, zero LLM cost
# - User can ask Forge interactively for deeper analysis after receiving alert
# - State in $STATE_FILE prevents duplicate alerts for same release version

set -euo pipefail

WATCHER_DIR=/root/.openclaw/upgrade-watcher
STATE_FILE="$WATCHER_DIR/state.json"
LOG_FILE=/var/log/release-watcher.log

WHATSAPP_TO="+5511982022121"
DISCORD_FORGE_CHANNEL="1480060616021643336"
GITHUB_REPO="openclaw/openclaw"

mkdir -p "$WATCHER_DIR"
exec >>"$LOG_FILE" 2>&1
echo ""
echo "=== release-watcher run $(date -Is) ==="

# Load env so openclaw CLI authenticates
set -a
source /root/.openclaw/.env 2>/dev/null || true
set +a

# 1. Current version
CURRENT_VERSION=$(openclaw --version 2>&1 | awk '{print $2}')
echo "current_version: $CURRENT_VERSION"

# 2. Latest STABLE on GitHub (excludes pre-releases / betas)
LATEST_STABLE=$(gh release list --repo "$GITHUB_REPO" \
  --exclude-pre-releases --limit 1 \
  --json tagName --jq '.[0].tagName' 2>/dev/null | sed 's/^v//')

if [[ -z "$LATEST_STABLE" ]]; then
  echo "WARN: failed to fetch latest stable release; aborting alert logic"
  exit 0
fi
echo "latest_stable: $LATEST_STABLE"

# 3. Previous notification state
PREV_NOTIFIED=""
if [[ -f "$STATE_FILE" ]]; then
  PREV_NOTIFIED=$(jq -r '.last_notified_version // ""' "$STATE_FILE" 2>/dev/null || echo "")
fi
echo "previously_notified_about: ${PREV_NOTIFIED:-<none>}"

# 4. Improvements audit — capture critical/warn drift
# Note: `improvements check --json` emits 2 JSON arrays concatenated (binary bug).
# Using jq -s '.[0]' slurps both and takes only the first (the real result).
IMPROV_OUTPUT=$(/root/bin/improvements check --json 2>/dev/null || echo '[]')
IMPROV_TOTAL=$(echo "$IMPROV_OUTPUT" | jq -sr '.[0] | length' 2>/dev/null); IMPROV_TOTAL=${IMPROV_TOTAL:-0}
IMPROV_PASS=$(echo "$IMPROV_OUTPUT" | jq -sr '.[0] | [.[] | select(.pass == true)] | length' 2>/dev/null); IMPROV_PASS=${IMPROV_PASS:-0}
IMPROV_FAIL=$(echo "$IMPROV_OUTPUT" | jq -sr '.[0] | [.[] | select(.pass == false)] | length' 2>/dev/null); IMPROV_FAIL=${IMPROV_FAIL:-0}
IMPROV_CRIT_FAIL=$(echo "$IMPROV_OUTPUT" | jq -sr '.[0] | [.[] | select(.pass == false and .category == "critical")] | length' 2>/dev/null); IMPROV_CRIT_FAIL=${IMPROV_CRIT_FAIL:-0}
echo "improvements: pass=$IMPROV_PASS/$IMPROV_TOTAL, critical_fails=$IMPROV_CRIT_FAIL"

# 5. Should we alert?
NEW_RELEASE=false
DRIFT_DETECTED=false
[[ "$LATEST_STABLE" != "$CURRENT_VERSION" && "$LATEST_STABLE" != "$PREV_NOTIFIED" ]] && NEW_RELEASE=true
[[ "$IMPROV_CRIT_FAIL" -gt 0 ]] && DRIFT_DETECTED=true

if ! $NEW_RELEASE && ! $DRIFT_DETECTED; then
  echo "no alert needed (no new stable release, no critical drift)"
  cat > "$STATE_FILE" <<EOF
{
  "last_run": "$(date -Is)",
  "current_version": "$CURRENT_VERSION",
  "latest_stable_seen": "$LATEST_STABLE",
  "last_notified_version": "$PREV_NOTIFIED",
  "improvements_pass": $IMPROV_PASS,
  "improvements_total": $IMPROV_TOTAL
}
EOF
  chmod 0600 "$STATE_FILE"
  exit 0
fi

# 6. Build alert message
ALERT=""
ALERT+="🚨 *OpenClaw Release Watch* — $(date '+%d/%m %H:%M' )"$'\n'$'\n'

if $NEW_RELEASE; then
  # Fetch release notes summary (top 600 chars of body)
  RELEASE_NOTES=$(gh release view "v$LATEST_STABLE" --repo "$GITHUB_REPO" \
    --json body --jq '.body' 2>/dev/null | head -c 800 || echo "")

  ALERT+="🆕 *Versão nova stable:* \`$CURRENT_VERSION\` → \`$LATEST_STABLE\`"$'\n'$'\n'

  # First non-empty highlight from release notes
  HIGHLIGHTS=$(echo "$RELEASE_NOTES" | grep -E "^- " | head -3 | sed 's/^/   /')
  if [[ -n "$HIGHLIGHTS" ]]; then
    ALERT+="*Highlights:*"$'\n'"$HIGHLIGHTS"$'\n'$'\n'
  fi

  # Compatibility pre-check: if v29-deltas.sh exists, run --pre and surface D1-D4 results
  # Auto-skips if script absent (e.g., older VPS provisioned before 2026-04-30)
  if [[ -x /root/upgrade-v29-deltas.sh ]]; then
    DELTA_LOG=$(timeout 90 bash /root/upgrade-v29-deltas.sh --pre 2>&1 || true)
    DELTA_SUMMARY=$(echo "$DELTA_LOG" | grep -E "^\s+(PASS|FAIL|WARN):" | head -8 | sed 's/^/   /')
    DELTA_VERDICT=$(echo "$DELTA_LOG" | grep -E "ALL PASS|FAILURES" | tail -1)
    DELTA_FAILS=$(echo "$DELTA_LOG" | grep -cE "^[[:space:]]+FAIL:" 2>/dev/null || true); DELTA_FAILS=${DELTA_FAILS:-0}
    if [[ -n "$DELTA_SUMMARY" ]]; then
      ALERT+="*Compat pre-check:*"$'\n'"$DELTA_SUMMARY"$'\n'
      [[ -n "$DELTA_VERDICT" ]] && ALERT+="   ${DELTA_VERDICT}"$'\n'
      if [[ "$DELTA_FAILS" -gt 0 ]]; then
        ALERT+="   🔴 *P0:* fix necessário antes do upgrade — review reapply-monkey-patch.sh"$'\n'
      fi
      ALERT+=$'\n'
    fi
  fi

  ALERT+="*Próximo passo:* responda \`go\` pra rodar o orchestrator (ckpt → staging → smoke → swap → watch)."$'\n'
  ALERT+="Detalhes do release: https://github.com/$GITHUB_REPO/releases/tag/v$LATEST_STABLE"$'\n'$'\n'
fi

if $DRIFT_DETECTED; then
  ALERT+="⚠️ *Improvements drift detectado:*"$'\n'
  ALERT+="$(echo "$IMPROV_OUTPUT" | jq -sr '.[0] |
    [.[] | select(.pass == false and .category == "critical")]
    | .[]
    | "   • [crit] " + .id + ": " + (.failures | join("; "))' | head -10)"$'\n'$'\n'
fi

ALERT+="📊 *Audit:* $IMPROV_PASS/$IMPROV_TOTAL OK"
if [[ "$IMPROV_FAIL" -gt 0 ]]; then
  ALERT+=" ($IMPROV_FAIL violations: $IMPROV_CRIT_FAIL critical)"
fi
ALERT+=$'\n'

echo "alert_built (len=${#ALERT})"

# 7. Send via WhatsApp
echo "sending WhatsApp alert..."
if openclaw message send \
    --channel whatsapp \
    --target "$WHATSAPP_TO" \
    --message "$ALERT" 2>&1 | tail -3; then
  echo "  whatsapp: ok"
else
  echo "  whatsapp: FAILED (continuing to discord)"
fi

# 8. Send via Discord forge-dev channel
echo "sending Discord alert..."
if openclaw message send \
    --channel discord \
    --target "$DISCORD_FORGE_CHANNEL" \
    --message "$ALERT" 2>&1 | tail -3; then
  echo "  discord: ok"
else
  echo "  discord: FAILED"
fi

# 9. Update state
NEW_NOTIFIED="$PREV_NOTIFIED"
$NEW_RELEASE && NEW_NOTIFIED="$LATEST_STABLE"

cat > "$STATE_FILE" <<EOF
{
  "last_run": "$(date -Is)",
  "current_version": "$CURRENT_VERSION",
  "latest_stable_seen": "$LATEST_STABLE",
  "last_notified_version": "$NEW_NOTIFIED",
  "improvements_pass": $IMPROV_PASS,
  "improvements_total": $IMPROV_TOTAL,
  "improvements_critical_fails": $IMPROV_CRIT_FAIL,
  "last_alert_sent": $(if $NEW_RELEASE || $DRIFT_DETECTED; then echo "true"; else echo "false"; fi),
  "alert_reason": "$( $NEW_RELEASE && echo -n "new_stable_release"; $NEW_RELEASE && $DRIFT_DETECTED && echo -n "+"; $DRIFT_DETECTED && echo -n "critical_drift" )"
}
EOF
chmod 0600 "$STATE_FILE"

echo "state updated. done."
