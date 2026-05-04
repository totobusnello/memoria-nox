#!/usr/bin/env bash
# Kill-switch: terminate beir-trec tmux session if 15min load avg > 5.0
# Cron entry (added by beir_full_run.sh launch):
#   */30 * * * * root /usr/local/bin/beir-kill-if-overload.sh >> /var/log/nox-mem/beir-killswitch.log 2>&1

set -euo pipefail

LOAD_THRESHOLD="5.0"
TMUX_SESSION="beir-trec"
LOG="/var/log/nox-mem/beir-killswitch.log"

mkdir -p /var/log/nox-mem

ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }

# Read 15min load average (field 3 of /proc/loadavg)
LOAD15=$(awk '{print $3}' /proc/loadavg)

# Use awk for float comparison (bash can't compare floats)
SHOULD_KILL=$(awk -v load="${LOAD15}" -v thresh="${LOAD_THRESHOLD}" \
    'BEGIN { print (load+0 > thresh+0) ? "yes" : "no" }')

echo "$(ts) | load15=${LOAD15} threshold=${LOAD_THRESHOLD} should_kill=${SHOULD_KILL}"

if [[ "${SHOULD_KILL}" == "yes" ]]; then
    # Check if session actually exists before killing
    if tmux has-session -t "${TMUX_SESSION}" 2>/dev/null; then
        echo "$(ts) | KILLING tmux session ${TMUX_SESSION} (load15=${LOAD15} > ${LOAD_THRESHOLD})"
        tmux kill-session -t "${TMUX_SESSION}"
        echo "$(ts) | Session killed."
    else
        echo "$(ts) | Session ${TMUX_SESSION} not running — nothing to kill."
    fi
else
    echo "$(ts) | Load OK — no action."
fi
