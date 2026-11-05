#!/usr/bin/env bash
# Paper A, H-A1 step 2 of 2 (PREREGISTRATION.md §5 step 5): READ H-A1, after the human sample.
#
#   read-h-a1.sh <workdir of score-holdout.sh> <holdout.jsonl> <human-commit>
#
# Keyless. Runs the analysis from the tag tree that score-holdout.sh extracted into the workdir.
# The holdout commitment is the one score-holdout.sh scored against (its commit is in the workdir,
# not given again). <human-commit> pushed paper-a-eval-ptbr/HUMAN-COMMITMENT.json. Every check of
# the order tag -> holdout commitment -> human commitment -> reading runs BEFORE anything is
# computed (third review: the control's output, with strict and pooled, was written first):
#   * the human commit is a different, later commit: it descends from the holdout commitment's
#     commit, is on origin/main, and HUMAN-COMMITMENT.json does not exist at the holdout commit;
#   * HOLDOUT-COMMITMENT.json at the human commit is the one that was scored;
#   * the human commitment is the registered sample (not smoke, n 60) of this holdout, made from
#     exactly this workdir's score.json and labels.json.
# SMOKE=1 (no <human-commit>) reads only a smoke commitment; holdout-analyze.py checks that too.
set -euo pipefail
W="$1"; HOLDOUT="$2"; HREF="${3:-}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
P="$W/code/paper-a-eval-ptbr"
sha() { sha256sum "$1" | cut -d' ' -f1; }
if [ "${SMOKE:-0}" = 1 ]; then
  python3 -c "import json,sys;sys.exit(json.load(open('$W/commitment.json')).get('smoke') is not True)" \
    || { echo "SMOKE reads only a smoke commitment" >&2; exit 1; }
else
  REF=$(cat "$W/ref.txt")
  git -C "$REPO" fetch -q origin main
  HREF=$(git -C "$REPO" rev-parse "$HREF^{commit}")
  [ "$HREF" != "$REF" ] || { echo "the human commit is the holdout commit" >&2; exit 1; }
  git -C "$REPO" merge-base --is-ancestor "$REF" "$HREF" || { echo "$HREF does not descend from $REF" >&2; exit 1; }
  git -C "$REPO" merge-base --is-ancestor "$HREF" origin/main || { echo "$HREF is not on origin/main" >&2; exit 1; }
  if git -C "$REPO" cat-file -e "$REF:paper-a-eval-ptbr/HUMAN-COMMITMENT.json" 2>/dev/null; then
    echo "HUMAN-COMMITMENT.json already exists at the holdout commit" >&2; exit 1
  fi
  git -C "$REPO" show "$HREF:paper-a-eval-ptbr/HOLDOUT-COMMITMENT.json" | cmp -s - "$W/commitment.json" \
    || { echo "HOLDOUT-COMMITMENT.json at $HREF is not the one scored" >&2; exit 1; }
  git -C "$REPO" show "$HREF:paper-a-eval-ptbr/HUMAN-COMMITMENT.json" > "$W/human.json"
  python3 - "$W/human.json" "$W/commitment.json" "$(sha "$W/score.json")" "$(sha "$W/labels.json")" <<'PY'
import json, sys
h, c = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
if (h.get("smoke"), h.get("n"), h.get("holdout_sha256"), h.get("score_sha256"), h.get("labels_sha256")) \
        != (False, 60, c["holdout_sha256"], sys.argv[3], sys.argv[4]):
    sys.exit("the human commitment is not the registered sample made from this workdir's score and labels")
PY
fi
EXPECT=$(python3 -c "import json;print(json.load(open('$W/score.json'))['summary']['ndcg_at_10'])")
# the control script stops on a division by zero when a threshold (0.3, 0.5 or 0.7) leaves its
# `bounded` arm with no query; that failure is recorded, not fatal, and holdout-analyze.py then
# applies the rule of PREREGISTRATION.md §5 (fourth review)
rc=0
python3 "$W/code/audits/2026-10-27-v3-rescore.py" "$W/score.json" "$W/labels.json" "$EXPECT" \
  > "$W/rescore.txt" 2> "$W/rescore.err" || rc=$?
[ "$rc" = 0 ] || echo "CONTROL SCRIPT FAILED rc=$rc: $(tail -1 "$W/rescore.err")" >> "$W/rescore.txt"
if [ "${SMOKE:-0}" = 1 ]; then
  python3 "$P/holdout-analyze.py" "$W/score.json" "$W/labels.json" "$HOLDOUT" "$W/commitment.json" \
    "$W/rescore.txt" --smoke | tee "$W/h-a1.txt"
else
  python3 "$P/holdout-analyze.py" "$W/score.json" "$W/labels.json" "$HOLDOUT" "$W/commitment.json" \
    "$W/rescore.txt" --human "$W/human.json" | tee "$W/h-a1.txt"
fi
