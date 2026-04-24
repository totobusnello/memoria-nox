#!/bin/bash
# activate-salience.sh — enable NOX_SALIENCE_MODE=active.
#
# Safe to run AFTER ≥7d of baseline observation (shadow-mode).
# Baseline started 2026-04-23. Earliest safe activation: 2026-04-30.
#
# Usage:
#   bash activate-salience.sh             # check only (dry-run)
#   bash activate-salience.sh --apply     # actually flip the flag
#   bash activate-salience.sh --rollback  # revert to shadow
#
# Validates baseline duration, updates .env, restarts nox-mem-api, health check.

set -o pipefail

BASELINE_START="2026-04-23"
MIN_DAYS=7
ENV_FILE=/root/.openclaw/.env
BRT_TODAY=$(date +%Y-%m-%d)
DAYS_ELAPSED=$(( ( $(date -d "$BRT_TODAY" +%s) - $(date -d "$BASELINE_START" +%s) ) / 86400 ))

ACTION="${1:-check}"

echo "=== Salience activation helper ==="
echo "Baseline start: $BASELINE_START"
echo "Today: $BRT_TODAY"
echo "Days elapsed: $DAYS_ELAPSED (min required: $MIN_DAYS)"
echo

CURRENT_MODE=$(grep -E "^NOX_SALIENCE_MODE=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo "unset (default shadow)")
echo "Current NOX_SALIENCE_MODE: $CURRENT_MODE"
echo

case "$ACTION" in
  check)
    if [ $DAYS_ELAPSED -lt $MIN_DAYS ]; then
      echo "⏸️  NOT READY: wait $(( MIN_DAYS - DAYS_ELAPSED )) more days before activation"
    else
      echo "✅ READY: baseline has enough data. Run with --apply to activate."
    fi
    ;;
  --apply)
    if [ $DAYS_ELAPSED -lt $MIN_DAYS ]; then
      echo "❌ REFUSE: baseline only $DAYS_ELAPSED days. Override with EXPLICIT_OVERRIDE=1 if really sure."
      [ -z "$EXPLICIT_OVERRIDE" ] && exit 1
    fi
    echo "→ Pre-activation snapshot of /api/health.salience..."
    curl -s http://127.0.0.1:18802/api/health | python3 -c "import sys,json;d=json.load(sys.stdin);print(json.dumps(d.get('salience',{}),indent=2))" \
      > "/var/log/nox-salience-preactivation-$(date +%Y%m%d-%H%M%S).json"

    if grep -q "^NOX_SALIENCE_MODE=" "$ENV_FILE"; then
      sed -i 's/^NOX_SALIENCE_MODE=.*/NOX_SALIENCE_MODE=active/' "$ENV_FILE"
    else
      echo "NOX_SALIENCE_MODE=active" >> "$ENV_FILE"
    fi
    echo "→ Flag set to active in $ENV_FILE"

    systemctl restart nox-mem-api
    sleep 3
    systemctl is-active nox-mem-api
    echo "→ nox-mem-api restarted"

    echo "→ Post-activation /api/health.salience:"
    curl -s http://127.0.0.1:18802/api/health | python3 -c "import sys,json;d=json.load(sys.stdin);print(json.dumps(d.get('salience',{}),indent=2))"
    echo
    echo "✅ ACTIVATED. Monitor /api/health.salience + search telemetry for 48h."
    echo "Rollback: bash activate-salience.sh --rollback"
    ;;
  --rollback)
    if grep -q "^NOX_SALIENCE_MODE=" "$ENV_FILE"; then
      sed -i 's/^NOX_SALIENCE_MODE=.*/NOX_SALIENCE_MODE=shadow/' "$ENV_FILE"
      echo "→ Flag reverted to shadow"
    else
      echo "NOX_SALIENCE_MODE=shadow" >> "$ENV_FILE"
    fi
    systemctl restart nox-mem-api
    sleep 3
    systemctl is-active nox-mem-api
    echo "✅ ROLLED BACK to shadow"
    ;;
  *)
    echo "Usage: $0 [check|--apply|--rollback]"
    exit 1
    ;;
esac
