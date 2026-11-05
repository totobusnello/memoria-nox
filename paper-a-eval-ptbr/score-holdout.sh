#!/usr/bin/env bash
# Paper A, H-A1 scoring (PREREGISTRATION.md §5 step 3). Runs on the host that serves nox-mem,
# from a checkout of the tag paper-a-prereg-v1.0, with the production search build, against a
# FRESH copy of the frozen snapshot: the path audits/2026-10-27-score-v3.sh scored ruler v3 on.
#
#   score-holdout.sh <snapshot.db.gz> <holdout.jsonl> <commitment-ref>
#
# <commitment-ref> is the commit that pushed HOLDOUT-COMMITMENT.json (after the tag). The script
# reads the commitment from that commit, checks that the commit descends from the tag and that no
# file the run executes changed between the two, and refuses otherwise.
# SMOKE=1 with <commitment-ref> = a path ending in .smoke.json skips the git checks; a smoke result
# is never a result.
#
# Isolation: a new private workdir from mktemp; every write lands in the copy (NOX_DB_PATH);
# run-gold-eval calls searchHybrid with trackAccess=false; judge-relevance opens the copy
# read-only. /var/tmp, never /tmp (tmpfs). The configuration that could change the run is set
# AFTER the production .env is read, so the .env cannot override it.
set -euo pipefail
TAG=paper-a-prereg-v1.0
SNAP_SHA=e04dfee9d7e0674cb043dc3362fefc24b7ec235acf6868365569106a322560a7
# sha256 over the sorted list of sha256 of every file in the production dist/ (see dist_sha below),
# as served when this pre-registration was fixed; a different build stops the run
DIST_SHA=cd75e48d7e9517a7b2548f4d50feb1a381f9ea6de1d8686ae67d5303f532f07e
GZ="$1"; HOLDOUT="$2"; REF="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
N=/root/.openclaw/workspace/tools/nox-mem
dist_sha() { (cd "$N/dist" && find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1); }

umask 077
W=$(mktemp -d /var/tmp/paper-a-score.XXXXXX)
echo "workdir $W"

echo "== commitment"
if [ "${SMOKE:-0}" = 1 ]; then
  case "$REF" in *.smoke.json) cp "$REF" "$W/commitment.json" ;; *) echo "SMOKE needs a *.smoke.json" >&2; exit 2 ;; esac
else
  git -C "$REPO" merge-base --is-ancestor "$TAG" "$REF" || { echo "$REF does not descend from $TAG" >&2; exit 1; }
  git -C "$REPO" diff --quiet "$TAG" "$REF" -- paper-a-eval-ptbr/*.py paper-a-eval-ptbr/*.sh \
      paper-a-eval-ptbr/holdout-prompt.txt paper-a-eval-ptbr/quotas.json eval/run-gold-eval.mjs \
      eval/judge-relevance.py audits/2026-10-27-v3-rescore.py \
    || { echo "executed files changed between $TAG and $REF" >&2; exit 1; }
  git -C "$REPO" show "$REF:paper-a-eval-ptbr/HOLDOUT-COMMITMENT.json" > "$W/commitment.json"
fi
want=$(python3 -c "import json;print(json.load(open('$W/commitment.json'))['holdout_sha256'])")
[ "$(sha256sum "$HOLDOUT" | cut -d' ' -f1)" = "$want" ] || { echo "holdout does not match the commitment" >&2; exit 1; }

echo "== snapshot and build"
[ "$(sha256sum "$GZ" | cut -d' ' -f1)" = "$SNAP_SHA" ] || { echo "snapshot is not the registered one" >&2; exit 1; }
got=$(dist_sha); echo "dist sha256 $got" | tee "$W/dist.sha256"
[ "$got" = "$DIST_SHA" ] || { echo "production build differs from the registered one: stop and report" >&2; exit 1; }

DB="$W/eval.db"
gunzip -c "$GZ" > "$DB"

echo "== gold = the drawn chunk, checked by the sha256 of its text in the copy"
python3 - "$DB" "$HOLDOUT" "$W/gold-map.json" <<'PY'
import hashlib, json, sqlite3, sys
con = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
m = {}
for l in open(sys.argv[2], encoding="utf-8"):
    h = json.loads(l)
    g = h["gold"][0]
    t = con.execute("SELECT chunk_text FROM chunks WHERE id = ?", (g["chunk_id"],)).fetchone()
    if t is None or hashlib.sha256(t[0].encode("utf-8")).hexdigest() != g["chunk_text_sha256"]:
        sys.exit(f"query {h['query_id']}: drawn chunk missing or changed in the copy")
    m[str(h["query_id"])] = [g["chunk_id"]]
json.dump(m, open(sys.argv[3], "w"))
print(f"   {len(m)} queries, gold verified")
PY

set -a; . /root/.openclaw/.env; set +a
export NOX_DB_PATH="$DB" NOX_DIST="$N/dist" GOLD_K_EVAL=10 \
       JUDGE_MODE=full JUDGE_MODEL=gpt-6-luna JUDGE_THRESHOLD=0.5 JUDGE_CHUNK_CHARS=6000
echo "== strict (production search path)"
node "$REPO/eval/run-gold-eval.mjs" "$HOLDOUT" "$W/gold-map.json" "$W/score.json" > "$W/score.log" 2>&1
echo "== judge the whole top-10"
python3 "$REPO/eval/judge-relevance.py" "$W/score.json" "$HOLDOUT" "$W/labels.json" > "$W/judge.log" 2>&1
EXPECT=$(python3 -c "import json;print(json.load(open('$W/score.json'))['summary']['ndcg_at_10'])")
python3 "$REPO/audits/2026-10-27-v3-rescore.py" "$W/score.json" "$W/labels.json" "$EXPECT" > "$W/rescore.txt"
echo "== H-A1"
python3 "$HERE/holdout-analyze.py" "$W/score.json" "$W/labels.json" "$HOLDOUT" "$W/commitment.json" \
  "$W/rescore.txt" | tee "$W/h-a1.txt"
echo "results in $W (private: copy only h-a1.txt, dist.sha256 and the label meta out of it)"
