#!/usr/bin/env bash
# Paper A, H-A1 step 1 of 2 (PREREGISTRATION.md §5 step 3): SCORE and JUDGE, print no reading.
# Runs on the host that serves nox-mem, with the production search build, against a FRESH copy of
# the frozen snapshot: the path audits/2026-10-27-score-v3.sh scored ruler v3 on.
#
#   score-holdout.sh <snapshot.db.gz> <holdout.jsonl> <commitment-commit>
#
# The code that runs is extracted from the tag into the workdir (git archive), never the working
# tree, so a local edit cannot change what executes. The commitment is read from the commit that
# pushed it, which must descend from the tag; the commitment's prompt and generator hashes must be
# the tag's. H-A1 is NOT read here: the blind human sample is graded first, then read-h-a1.sh.
#
# SMOKE=1, with <commitment-commit> = a path ending in .smoke.json, archives HEAD instead of the
# tag and skips the git checks. A smoke result is never a result.
set -euo pipefail
TAG=paper-a-prereg-v1.0
SNAP_SHA=e04dfee9d7e0674cb043dc3362fefc24b7ec235acf6868365569106a322560a7
# sha256 over the sorted per-file sha256 of the production dist/, as served when this was fixed
DIST_SHA=cd75e48d7e9517a7b2548f4d50feb1a381f9ea6de1d8686ae67d5303f532f07e
# sha256 of the sorted NOX_* settings of the production .env (secrets and NOX_DB_PATH excluded):
# the build hash does not freeze the switches it reads at run time
ENV_SHA=cd157cc97987f6fdd9b38a663ccfb47d872fa46869c79358cf1f9c6be3ec0f9a
GZ="$1"; HOLDOUT="$2"; REF="$3"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
N=/root/.openclaw/workspace/tools/nox-mem
dist_sha() { (cd "$N/dist" && find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1); }
env_sha() { env | grep '^NOX_' | grep -vE 'TOKEN|KEY|SECRET|PASS|^NOX_DB_PATH=' | sort | sha256sum | cut -d' ' -f1; }

umask 077
W=$(mktemp -d /var/tmp/paper-a-score.XXXXXX)
echo "workdir $W"
mkdir "$W/code"
if [ "${SMOKE:-0}" = 1 ]; then
  case "$REF" in *.smoke.json) cp "$REF" "$W/commitment.json" ;; *) echo "SMOKE needs a *.smoke.json" >&2; exit 2 ;; esac
  git -C "$REPO" archive HEAD | tar -x -C "$W/code"
else
  # a full clone of the public repository: the tag and both commitments must be published
  git -C "$REPO" fetch -q --tags origin main
  git -C "$REPO" rev-parse -q --verify "refs/tags/$TAG" >/dev/null || { echo "tag $TAG not found" >&2; exit 1; }
  git -C "$REPO" merge-base --is-ancestor "$TAG" "$REF" || { echo "$REF does not descend from $TAG" >&2; exit 1; }
  git -C "$REPO" merge-base --is-ancestor "$REF" origin/main || { echo "$REF is not on origin/main" >&2; exit 1; }
  # the commitment comes after the tag (fourth review: the tag's own commit was accepted as REF)
  [ "$(git -C "$REPO" rev-parse "$TAG^{commit}")" != "$(git -C "$REPO" rev-parse "$REF^{commit}")" ] \
    || { echo "the holdout commitment is the tag's own commit" >&2; exit 1; }
  if git -C "$REPO" cat-file -e "$TAG:paper-a-eval-ptbr/HOLDOUT-COMMITMENT.json" 2>/dev/null; then
    echo "the tag already carries a HOLDOUT-COMMITMENT.json" >&2; exit 1
  fi
  # the holdout commitment is written once: the only commit on origin/main that ever touched it
  # is REF (fifth review: a second holdout published later, with consistent hashes, passed)
  HIST=$(git -C "$REPO" log --full-history --format=%H origin/main -- paper-a-eval-ptbr/HOLDOUT-COMMITMENT.json)
  [ "$HIST" = "$(git -C "$REPO" rev-parse "$REF^{commit}")" ] \
    || { echo "HOLDOUT-COMMITMENT.json on origin/main was not written once, by $REF" >&2; exit 1; }
  git -C "$REPO" rev-parse "$REF^{commit}" > "$W/ref.txt"
  git -C "$REPO" archive "$TAG" | tar -x -C "$W/code"
  git -C "$REPO" show "$REF:paper-a-eval-ptbr/HOLDOUT-COMMITMENT.json" > "$W/commitment.json"
fi
C="$W/code"; P="$C/paper-a-eval-ptbr"

echo "== commitment"
python3 - "$W/commitment.json" "$HOLDOUT" "$P" "${SMOKE:-0}" <<'PY'
import hashlib, json, sys
c = json.load(open(sys.argv[1])); smoke = sys.argv[4] == "1"
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
if c.get("smoke") is not smoke:
    sys.exit(f"commitment smoke={c.get('smoke')} in a {'smoke' if smoke else 'registered'} run")
if sha(sys.argv[2]) != c["holdout_sha256"]:
    sys.exit("holdout does not match the commitment")
reg = json.load(open(f"{sys.argv[3]}/quotas.json"))
if not smoke and (c["n"], c["per_stratum"]) != (reg["n"], reg["quota"]):
    # fourth review: refuse before paying the judge, not only in the analysis
    sys.exit(f"commitment n {c['n']} / {c['per_stratum']} is not the registered sample")
for key, f in (("prompt_sha256", "holdout-prompt.txt"), ("script_sha256", "holdout-generate.py")):
    if c[key] != sha(f"{sys.argv[3]}/{f}"):
        sys.exit(f"commitment {key} is not the hash of {f} at the tag")
print(f"   n {c['n']} · strata {c['per_stratum']} · smoke {c['smoke']} · hashes match")
PY

echo "== snapshot, build and settings"
[ "$(sha256sum "$GZ" | cut -d' ' -f1)" = "$SNAP_SHA" ] || { echo "snapshot is not the registered one" >&2; exit 1; }
got=$(dist_sha); echo "dist $got" | tee "$W/dist.sha256"
[ "$got" = "$DIST_SHA" ] || { echo "production build differs from the registered one: stop and report" >&2; exit 1; }
set -a; . /root/.openclaw/.env; set +a
got=$(env_sha); echo "settings $got" | tee "$W/env.sha256"
[ "$got" = "$ENV_SHA" ] || { echo "production NOX_* settings differ from the registered ones: stop and report" >&2; exit 1; }

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

export NOX_DB_PATH="$DB" NOX_DIST="$N/dist" GOLD_K_EVAL=10 \
       JUDGE_MODE=full JUDGE_MODEL=gpt-6-luna JUDGE_THRESHOLD=0.5 JUDGE_CHUNK_CHARS=6000
echo "== strict ranking (production search path; nothing printed)"
node "$C/eval/run-gold-eval.mjs" "$HOLDOUT" "$W/gold-map.json" "$W/score.json" > "$W/score.log" 2>&1
echo "== judge the whole top-10 (nothing printed)"
python3 "$C/eval/judge-relevance.py" "$W/score.json" "$HOLDOUT" "$W/labels.json" > "$W/judge.log" 2>&1
python3 -c "import json;m=json.load(open('$W/labels.json'))['meta'];print('   judged', m['n_judged'], 'pairs, errors', m['n_errors'])"
(cd "$W" && sha256sum score.json labels.json | tee outputs.sha256)
echo "scored. Next: human-sample.py make from $W/labels.json; grade blind; human-sample.py commit"
echo "with --score $W/score.json; push HUMAN-COMMITMENT.json; then read-h-a1.sh $W <holdout> <human-commit>."
