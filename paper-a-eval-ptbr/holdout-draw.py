#!/usr/bin/env python3
"""Paper A, prospective part: draw the holdout passages (PREREGISTRATION.md §3). No API call.

  python3 -I holdout-draw.py --db <snapshot.db> --out <private dir>/draw.json

The output names source files and chunk ids of a private corpus, so the script refuses to write it
inside the repository. What it prints (counts and the sha256 of the output) is safe to commit.

Frame: chunks with superseded_by IS NULL and at least MIN_CHARS characters of text, in six strata
by source directory. Stratum F is limited to the kinds of source the 57 accepted v3 queries drew
on (sessions, agents, docs, root files); the private document vault and the nox-mem source tree
are outside the frame because no v3 query has gold there.

Draw: one RNG, seeded once; strata in fixed order A..F; within a stratum, the eligible source
files sorted by name and shuffled, then for each file one eligible chunk uniformly at random
(chunks sorted by id). Every file of the stratum gets a position in the list: the generator takes
them in order until the stratum's quota is filled, so a replacement is always the next draw.
"""
import argparse
import hashlib
import json
import pathlib
import random
import sqlite3
import subprocess
import sys

SEED = 20261105
MIN_CHARS = 200
HERE = pathlib.Path(__file__).resolve().parent
# quotas derived from the v3 gold by derive-quotas.py, never typed by hand (PREREGISTRATION.md §3)
QUOTA = json.loads((HERE / "quotas.json").read_text())["quota"]
# sha256 of the DECOMPRESSED snapshot the draw and the generator read (the .gz is pinned in
# score-holdout.sh); a draw from any other database is refused
SNAPSHOT_DB_SHA = "4ab1a94f7245c272177e184e0b465eeb795ab90813c91fb9afc1b6cf273a58ad"


def file_sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def stratum(f):
    if f.startswith("shared/imports/"):
        return "A"
    if f.startswith("memory/entities/"):
        return "D"
    if f.startswith("memory/lessons/") or (f.startswith("memory/") and "/" not in f[7:]):
        return "B"
    if f.startswith("events/mac/"):
        return "C"
    if f.startswith("shared/"):
        return "E"
    if "/" not in f or f.startswith(("sessions/", "agents/", "../agents/", "docs/")):
        return "F"
    return None          # outside the frame


def inside_repo(p):
    r = subprocess.run(["git", "-C", str(pathlib.Path(p).resolve().parent), "rev-parse",
                        "--show-toplevel"], capture_output=True, text=True)
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--smoke-seed", type=int, default=None,
                    help="test the script with a seed other than the registered one; the registered "
                         "draw runs only after the tag paper-a-prereg-v1.0 (PREREGISTRATION.md §5)")
    a = ap.parse_args()
    seed = SEED if a.smoke_seed is None else a.smoke_seed
    if a.smoke_seed == SEED:
        sys.exit("refusing: --smoke-seed must differ from the registered seed")
    if inside_repo(a.out):
        sys.exit("refusing: --out is inside a git repository; the draw names private files")
    if file_sha(a.db) != SNAPSHOT_DB_SHA:
        sys.exit("refusing: --db is not the registered snapshot (sha256 mismatch)")
    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    rows = con.execute("SELECT id, source_file FROM chunks WHERE superseded_by IS NULL "
                       "AND length(chunk_text) >= ?", (MIN_CHARS,)).fetchall()
    by = {}
    for cid, f in rows:
        s = stratum(f)
        if s:
            by.setdefault(s, {}).setdefault(f, []).append(cid)
    rng = random.Random(seed)
    out = {"seed": seed, "smoke": a.smoke_seed is not None, "min_chars": MIN_CHARS, "quota": QUOTA, "strata": {}}
    for s in sorted(QUOTA):
        files = sorted(by.get(s, {}))
        rng.shuffle(files)
        out["strata"][s] = [{"chunk_id": rng.choice(sorted(by[s][f])), "source_file": f}
                            for f in files]
    out["snapshot_db_sha256"] = SNAPSHOT_DB_SHA
    blob = json.dumps(out, ensure_ascii=False, sort_keys=True).encode()
    pathlib.Path(a.out).write_bytes(blob)
    print(f"draw sha256 {hashlib.sha256(blob).hexdigest()}")
    for s in sorted(QUOTA):
        print(f"  {s}: quota {QUOTA[s]}, {len(out['strata'][s])} files in the frame")
    return 0


if __name__ == "__main__":
    sys.exit(main())
