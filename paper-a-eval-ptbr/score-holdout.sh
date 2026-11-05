#!/usr/bin/env bash
# Paper A, H-A1 scoring (PREREGISTRATION.md §5 step 3). Runs on the host that serves nox-mem,
# with the production search code, against a FRESH copy of the frozen snapshot — the same path
# audits/2026-10-27-score-v3.sh scored ruler v3 on.
#
#   score-holdout.sh <snapshot.db.gz> <holdout.jsonl> <workdir under /var/tmp>
#
# Isolation: every write lands in the copy (NOX_DB_PATH), run-gold-eval calls searchHybrid with
# trackAccess=false, and judge-relevance opens the copy read-only. /var/tmp, never /tmp (tmpfs).
# Refuses a snapshot whose sha256 is not the registered one, and refuses to run if HOLDOUT
# does not match the hash committed in HOLDOUT-COMMITMENT.json.
set -euo pipefail
SNAP_SHA=e04dfee9d7e0674cb043dc3362fefc24b7ec235acf6868365569106a322560a7
GZ="$1"; HOLDOUT="$2"; W="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
N=/root/.openclaw/workspace/tools/nox-mem
case "$W" in /var/tmp/*) ;; *) echo "workdir must be under /var/tmp" >&2; exit 2 ;; esac
mkdir -p "$W"

echo "== snapshot hash"
got=$(sha256sum "$GZ" | cut -d' ' -f1)
[ "$got" = "$SNAP_SHA" ] || { echo "snapshot sha256 $got is not the registered one" >&2; exit 1; }
echo "== holdout hash against the commitment"
# HOLDOUT_COMMITMENT overrides the file only for a smoke run (*.smoke.json); the registered run uses
# the commitment that was pushed before any ranking.
C="${HOLDOUT_COMMITMENT:-$HERE/HOLDOUT-COMMITMENT.json}"
case "$C" in "$HERE/HOLDOUT-COMMITMENT.json"|*.smoke.json) ;; *) echo "commitment must be the pushed one or *.smoke.json" >&2; exit 2 ;; esac
want=$(python3 -c "import json;print(json.load(open('$C'))['holdout_sha256'])")
[ "$(sha256sum "$HOLDOUT" | cut -d' ' -f1)" = "$want" ] || { echo "holdout does not match the commitment" >&2; exit 1; }

echo "== fresh copy"
DB="$W/eval.db"
gunzip -c "$GZ" > "$DB"
echo "== production search code in use"
sha256sum "$N/dist/search.js" | tee "$W/search-js.sha256"

echo "== resolve anchors on the copy"
GOLD_DB="$DB" python3 "$REPO/eval/resolve-gold-anchors.py" "$HOLDOUT" "$W/resolve.json" > "$W/resolve.log" 2>&1
python3 - "$W/resolve.json" "$W/resolved-map.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
m = {}
for e in d["entries"]:
    if e["state"] in ("resolved", "moved", "ambiguous_structural", "ambiguous_duplicate"):
        m.setdefault(str(e["query_id"]), []).extend(e["resolved_ids"])
json.dump({k: sorted(set(v)) for k, v in m.items()}, open(sys.argv[2], "w"))
print(f"   gold resolved for {len(m)} queries")
PY

echo "== strict (production search path)"
( set -a; . /root/.openclaw/.env; set +a
  NOX_DB_PATH="$DB" node "$REPO/eval/run-gold-eval.mjs" "$HOLDOUT" "$W/resolved-map.json" "$W/score.json" \
    > "$W/score.log" 2>&1 )
echo "== judge the whole top-10 (bounded judge, registered threshold p>0.5)"
( set -a; . /root/.openclaw/.env; set +a
  NOX_DB_PATH="$DB" JUDGE_MODE=full JUDGE_THRESHOLD=0.5 \
    python3 "$REPO/eval/judge-relevance.py" "$W/score.json" "$HOLDOUT" "$W/labels.json" > "$W/judge.log" 2>&1 )
EXPECT=$(python3 -c "import json;print(json.load(open('$W/score.json'))['summary']['ndcg_at_10'])")
python3 "$REPO/audits/2026-10-27-v3-rescore.py" "$W/score.json" "$W/labels.json" "$EXPECT" | tee "$W/rescore.txt"
echo "== H-A1"
python3 "$HERE/holdout-analyze.py" "$W/score.json" "$W/labels.json" "$HOLDOUT" "$W/rescore.txt" | tee "$W/h-a1.txt"
