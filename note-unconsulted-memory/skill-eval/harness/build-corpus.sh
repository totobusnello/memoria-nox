#!/usr/bin/env bash
# Build the frozen eval DB for the skill evaluation (PROTOCOL.md section 4).
#
# Usage: build-corpus.sh <memoria-nox clone> <commit> [eval dir, default ~/nox-skill-eval]
# Writes <eval>/corpus/<commit>/ (the files exactly as at that commit), <eval>/db/eval-<commit>.db
# and <eval>/db/eval-<commit>.manifest.json. Never touches any other database: NOX_DB_PATH is set
# explicitly, and cwd is a scratch dir so anything a module writes next to itself lands there.
set -euo pipefail
REPO="${1:?memoria-nox clone}"; COMMIT="${2:?commit}"; EVAL="${3:-$HOME/nox-skill-eval}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
NOXMEM="${NOXMEM_DIR:-$HERE/../../../nox-mem}"   # the package source in this repo, built (dist/)
[ -f "$NOXMEM/dist/index.js" ] || { echo "nox-mem not built at $NOXMEM" >&2; exit 2; }
KEYFILE="${GEMINI_KEY_FILE:-$HOME/.config/secrets/GEMINI_API_KEY}"
[ -r "$KEYFILE" ] || { echo "no Gemini key file at $KEYFILE" >&2; exit 2; }

SHORT="$(git -C "$REPO" rev-parse --short=7 "$COMMIT")"
CORPUS="$EVAL/corpus/$SHORT"; DB="$EVAL/db/eval-$SHORT.db"; WORK="$EVAL/work/build-$SHORT"
[ -e "$DB" ] && { echo "refusing: $DB exists (frozen DBs are never rebuilt in place)" >&2; exit 3; }
mkdir -p "$CORPUS" "$EVAL/db" "$WORK"

# The files exactly as committed, not the working tree.
git -C "$REPO" archive "$COMMIT" docs/DECISIONS.md docs/INCIDENTS.md CLAUDE.md audits \
  | tar -x -C "$CORPUS"
find "$CORPUS" -type f ! -name '*.md' -delete
NFILES="$(find "$CORPUS" -type f -name '*.md' | wc -l | tr -d ' ')"

cd "$WORK"
export NOX_DB_PATH="$DB" GEMINI_API_KEY="$(cat "$KEYFILE")"
find "$CORPUS" -type f -name '*.md' -print0 | sort -z | xargs -0 node "$NOXMEM/dist/index.js" ingest
node "$NOXMEM/dist/index.js" vectorize
unset GEMINI_API_KEY

python3 - "$DB" "$REPO" "$COMMIT" "$NFILES" "$NOXMEM" <<'EOF'
import sqlite3, sys, json, hashlib, subprocess
db, repo, commit, nfiles, noxmem = sys.argv[1:]
c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
chunks = c.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
try:
    vec = c.execute("SELECT COUNT(*) FROM vec_chunk_map").fetchone()[0]
except Exception as e:
    vec = f"unreadable: {e}"
c.close()
h = hashlib.sha256(open(db, "rb").read()).hexdigest()
full = subprocess.check_output(["git", "-C", repo, "rev-parse", commit], text=True).strip()
ver = json.load(open(f"{noxmem}/package.json"))["version"]
m = {"corpus_repo": "totobusnello/memoria-nox", "commit": full, "files": int(nfiles),
     "chunks": chunks, "vectors": vec, "db_sha256": h, "nox_mem_version": ver,
     "embedding": "gemini (package default provider; model recorded by nox-mem in the DB)"}
json.dump(m, open(db.replace(".db", ".manifest.json"), "w"), indent=2)
print(json.dumps(m, indent=2))
if not isinstance(vec, int) or vec != chunks:
    print(f"WARNING: vectors ({vec}) != chunks ({chunks})", file=sys.stderr); sys.exit(4)
EOF
chmod 0444 "$DB"
# The extracted files go: chunk sources carry their absolute path, and an agent that sees it in a
# search result tries to read the file directly (seen in the first smoke run, denied by dontAsk).
# The DB is self-contained; `git archive` at the pinned commit rebuilds the files.
rm -rf "$CORPUS"
echo "stray files written by the build (should be only logs):"; find "$WORK" -type f | head
