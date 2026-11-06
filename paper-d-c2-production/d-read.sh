#!/usr/bin/env bash
# Paper D, step 6 (PREREGISTRATION.md §6): read the result, after the human commitment is pushed.
#
#   d-read.sh <private dir> <freeze commit> <questions commit> <human commit>
#   SMOKE=1 d-read.sh <private dir>
#
# Keyless. Runs d-read.py from the tag tree that d-run.sh extracted into <private dir>/run/code,
# never from the working tree. d-read.py checks the order and every hash before computing.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
P="$1"; shift
R="$P/run/code/paper-d-c2-production/d-read.py"
[ -f "$R" ] || { echo "no tag tree at $P/run/code: run d-run.sh first" >&2; exit 1; }
if [ "${SMOKE:-0}" = 1 ]; then
  exec python3 -I "$R" --repo "$REPO" --private "$P" --smoke
fi
exec python3 -I "$R" --repo "$REPO" --private "$P" --freeze-ref "$1" --questions-ref "$2" --human-ref "$3"
