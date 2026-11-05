#!/usr/bin/env bash
# Paper A, H-A1 step 2 of 2 (PREREGISTRATION.md §5 step 4): READ H-A1, after the human sample.
#
#   read-h-a1.sh <workdir of score-holdout.sh> <holdout.jsonl> <commitment-commit> <human-commit>
#
# Keyless. Runs the analysis from the tag tree that score-holdout.sh extracted into the workdir.
# <human-commit> is the commit that pushed paper-a-eval-ptbr/HUMAN-COMMITMENT.json (the graded
# sheet's sha256 and the agreement counts); it must descend from <commitment-commit>, so the order
# tag -> holdout commitment -> human commitment -> reading is checked by git, not by memory.
# SMOKE=1 with <commitment-commit> = a *.smoke.json path skips the commitments.
set -euo pipefail
W="$1"; HOLDOUT="$2"; REF="$3"; HREF="${4:-}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
P="$W/code/paper-a-eval-ptbr"
EXPECT=$(python3 -c "import json;print(json.load(open('$W/score.json'))['summary']['ndcg_at_10'])")
python3 "$W/code/audits/2026-10-27-v3-rescore.py" "$W/score.json" "$W/labels.json" "$EXPECT" > "$W/rescore.txt"
if [ "${SMOKE:-0}" = 1 ]; then
  python3 "$P/holdout-analyze.py" "$W/score.json" "$W/labels.json" "$HOLDOUT" "$W/commitment.json" \
    "$W/rescore.txt" --smoke | tee "$W/h-a1.txt"
  exit 0
fi
git -C "$REPO" merge-base --is-ancestor "$REF" "$HREF" || { echo "$HREF does not descend from $REF" >&2; exit 1; }
git -C "$REPO" show "$HREF:paper-a-eval-ptbr/HUMAN-COMMITMENT.json" > "$W/human.json"
python3 "$P/holdout-analyze.py" "$W/score.json" "$W/labels.json" "$HOLDOUT" "$W/commitment.json" \
  "$W/rescore.txt" --human "$W/human.json" | tee "$W/h-a1.txt"
