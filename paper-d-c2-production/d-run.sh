#!/usr/bin/env bash
# Paper D, step 4 (PREREGISTRATION.md §6): run every arm from the code of the tag.
#
#   d-run.sh <private dir> <freeze commit> <questions commit> [--yes]
#   SMOKE=1 d-run.sh <private dir> [--yes]          (archives HEAD; never a result)
#
# The code that runs is extracted from the tag into <private dir>/run/code (git archive), never
# the working tree, so a local edit cannot change what executes. d-run.py, from that tree, checks
# the public order and every hash before the first paid call. Keys come from files, never from
# the command line: GEMINI_API_KEY and OPENAI_API_KEY must be in the environment.
set -euo pipefail
TAG=paper-d-prereg-v1.0
REPO="$(cd "$(dirname "$0")/.." && pwd)"
P="$1"; shift
case "$P" in "$REPO"/*) echo "the private dir is inside the repository" >&2; exit 2 ;; esac
umask 077
mkdir -p "$P/run"
rm -rf "$P/run/code"; mkdir "$P/run/code"
if [ "${SMOKE:-0}" = 1 ]; then
  git -C "$REPO" archive HEAD paper-d-c2-production paper3-construction/lme-run.py \
    paper-a-eval-ptbr/holdout-generate.py | tar -x -C "$P/run/code"
  exec python3 -I "$P/run/code/paper-d-c2-production/d-run.py" --repo "$REPO" --private "$P" --smoke "$@"
fi
FREF="$1"; QREF="$2"; shift 2
git -C "$REPO" fetch -q --tags origin main
git -C "$REPO" rev-parse -q --verify "refs/tags/$TAG" >/dev/null || { echo "tag $TAG not found" >&2; exit 1; }
git -C "$REPO" archive "$TAG" paper-d-c2-production paper3-construction/lme-run.py \
  paper-a-eval-ptbr/holdout-generate.py | tar -x -C "$P/run/code"
exec python3 -I "$P/run/code/paper-d-c2-production/d-run.py" --repo "$REPO" --private "$P" \
  --freeze-ref "$FREF" --questions-ref "$QREF" "$@"
