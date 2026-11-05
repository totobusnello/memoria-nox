#!/usr/bin/env python3
"""Paper A, H-A2 (PREREGISTRATION.md §4): does a gold reference still reach its evidence later?

  python3 -I holdout-persistence.py --frozen-db <2026-11-04 snapshot.db> \
      --later-gz <daily-main-main-YYYYMMDD…db.gz, the first dated 2026-11-18 or later> \
      --listing <file listing the daily-main directory when the later snapshot was taken> \
      --workdir <private directory outside the repository> \
      --holdout <holdout.jsonl> --commitment <HOLDOUT-COMMITMENT.json>

The frozen database must have the registered sha256. The later snapshot is given as the .gz the
host wrote: its date is read from the file name and must be 2026-11-18 or later, and the listing
must show no daily-main file dated 2026-11-18 or later that is OLDER than it (it must be the first).
Its sha256 is printed with the result. All shares are compared as integer counts (the second review
found 114/120 - 102/120 = 0.0999… rejecting a gap of exactly ten points).

Keyless, read-only. Both references are judged by the SAME criterion, which is what the first
draft lacked (an id had to match the whole text, an anchor only its prefix): a reference persists
if it leads to an ACTIVE chunk (superseded_by IS NULL) of the later snapshot whose text,
whitespace-normalised, still contains the query's evidence span.

  by id      the chunk with the gold chunk id
  by anchor  any active chunk of the same source file containing the evidence span
             (more than one such chunk is reported as ambiguous and still counts as reached)

Precondition, printed first: churn = share of the chunks of the drawn SOURCE FILES (not the whole
corpus: most churn happens in directories outside the frame) whose id no longer names an active
chunk with identical text. Churn below 5% means no re-ingest reached these files in the window,
and H-A2 is reported as not tested.

Prediction: persists by anchor >= 95% of queries, and by anchor minus by id >= 10 points.
"""
import argparse
import gzip
import hashlib
import importlib.util
import pathlib
import shutil
import subprocess
import json
import re
import sqlite3
import sys

FIRST_DATE = "20261118"
NAME = re.compile(r"daily-main-main-(\d{8})\d{6}-.*\.db\.gz$")


def ws(t):
    return re.sub(r"\s+", " ", t).strip()


def ro(p):
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True)


def main():
    ap = argparse.ArgumentParser()
    for k in ("--frozen-db", "--later-gz", "--listing", "--workdir", "--holdout", "--commitment"):
        ap.add_argument(k, required=True)
    a = ap.parse_args()
    here = pathlib.Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("draw", here / "holdout-draw.py")
    dr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dr)
    if dr.file_sha(a.frozen_db) != dr.SNAPSHOT_DB_SHA:
        sys.exit("refusing: --frozen-db is not the registered snapshot")
    m = NAME.search(pathlib.Path(a.later_gz).name)
    if not m or m.group(1) < FIRST_DATE:
        sys.exit(f"refusing: {pathlib.Path(a.later_gz).name} is not a daily snapshot dated {FIRST_DATE} or later")
    earlier = sorted(x.group(1) for x in (NAME.search(l.strip().split("/")[-1])
                                          for l in open(a.listing)) if x and FIRST_DATE <= x.group(1) < m.group(1))
    if earlier:
        sys.exit(f"refusing: the listing has an eligible snapshot dated {earlier[0]}, earlier than the one given")
    if subprocess.run(["git", "-C", a.workdir, "rev-parse"], capture_output=True).returncode == 0:
        sys.exit("refusing: --workdir is inside a git repository")
    later_db = pathlib.Path(a.workdir) / "later.db"
    with gzip.open(a.later_gz, "rb") as src, open(later_db, "wb") as dst:
        shutil.copyfileobj(src, dst, 1 << 20)
    print(f"later snapshot {pathlib.Path(a.later_gz).name}, gz sha256 {dr.file_sha(a.later_gz)}")
    hb = open(a.holdout, "rb").read()
    if hashlib.sha256(hb).hexdigest() != json.load(open(a.commitment))["holdout_sha256"]:
        sys.exit("holdout does not match the commitment")
    hold = [json.loads(l) for l in hb.decode("utf-8").splitlines()]
    fz, lt = ro(a.frozen_db), ro(str(later_db))
    files = sorted({h["gold"][0]["source_file"] for h in hold})
    same = total = 0
    for f in files:
        for cid, text in fz.execute("SELECT id, chunk_text FROM chunks WHERE source_file = ? "
                                    "AND superseded_by IS NULL", (f,)):
            total += 1
            r = lt.execute("SELECT chunk_text FROM chunks WHERE id = ? AND superseded_by IS NULL",
                           (cid,)).fetchone()
            same += r is not None and r[0] == text
    changed = total - same
    print(f"precondition: churn over the {len(files)} drawn source files = {changed}/{total} chunks "
          f"changed id or text; required >= 5%")
    by_id = by_anchor = ambiguous = gone = 0
    for h in hold:
        g = h["gold"][0]
        ev = ws(g["anchor"])
        r = lt.execute("SELECT chunk_text FROM chunks WHERE id = ? AND superseded_by IS NULL",
                       (g["chunk_id"],)).fetchone()
        by_id += r is not None and ev in ws(r[0])
        hits = [cid for cid, t in lt.execute(
            "SELECT id, chunk_text FROM chunks WHERE source_file = ? AND superseded_by IS NULL",
            (g["source_file"],)) if ev in ws(t)]
        by_anchor += bool(hits)
        ambiguous += len(hits) > 1
        gone += not hits and not (r is not None and ev in ws(r[0]))
    n = len(hold)
    print(f"persists by id {by_id}/{n} = {by_id / n:.1%} · by anchor {by_anchor}/{n} = "
          f"{by_anchor / n:.1%} (ambiguous {ambiguous}) · evidence unreachable by either {gone}")
    # integers only: churn >= 5%  <=>  20*changed >= total;  anchor >= 95%  <=>  20*by_anchor >= 19*n;
    # anchor - id >= 10 points  <=>  10*(by_anchor - by_id) >= n
    if total == 0 or 20 * changed < total:
        print("H-A2: not tested (no re-ingest reached the drawn files in the window)")
    else:
        holds = 20 * by_anchor >= 19 * n and 10 * (by_anchor - by_id) >= n
        print(f"H-A2: anchor >= 95% and anchor - id >= 10 points -> "
              f"{'holds' if holds else 'does not hold'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
