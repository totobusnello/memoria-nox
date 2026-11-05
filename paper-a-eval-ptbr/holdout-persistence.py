#!/usr/bin/env python3
"""Paper A, H-A2 (PREREGISTRATION.md §4): does a gold reference still reach its evidence later?

  python3 -I holdout-persistence.py --frozen-db <2026-11-04 snapshot.db> \
      --later-db <first daily snapshot dated 2026-11-18 or later, decompressed> \
      --holdout <holdout.jsonl> --commitment <HOLDOUT-COMMITMENT.json>

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
import hashlib
import json
import re
import sqlite3
import sys

CHURN_MIN, ANCHOR_MIN, GAP_MIN = 0.05, 0.95, 0.10


def ws(t):
    return re.sub(r"\s+", " ", t).strip()


def ro(p):
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True)


def main():
    ap = argparse.ArgumentParser()
    for k in ("--frozen-db", "--later-db", "--holdout", "--commitment"):
        ap.add_argument(k, required=True)
    a = ap.parse_args()
    hb = open(a.holdout, "rb").read()
    if hashlib.sha256(hb).hexdigest() != json.load(open(a.commitment))["holdout_sha256"]:
        sys.exit("holdout does not match the commitment")
    hold = [json.loads(l) for l in hb.decode("utf-8").splitlines()]
    fz, lt = ro(a.frozen_db), ro(a.later_db)
    files = sorted({h["gold"][0]["source_file"] for h in hold})
    same = total = 0
    for f in files:
        for cid, text in fz.execute("SELECT id, chunk_text FROM chunks WHERE source_file = ? "
                                    "AND superseded_by IS NULL", (f,)):
            total += 1
            r = lt.execute("SELECT chunk_text FROM chunks WHERE id = ? AND superseded_by IS NULL",
                           (cid,)).fetchone()
            same += r is not None and r[0] == text
    churn = 1 - same / total if total else 0.0
    print(f"precondition: churn over the {len(files)} drawn source files = {churn:.1%} "
          f"({total - same} of {total} chunks changed id or text); required >= {CHURN_MIN:.0%}")
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
    pi, pa = by_id / n, by_anchor / n
    print(f"persists by id {by_id}/{n} = {pi:.1%} · by anchor {by_anchor}/{n} = {pa:.1%} "
          f"(ambiguous {ambiguous}) · evidence unreachable by either {gone}")
    if churn < CHURN_MIN:
        print("H-A2: not tested (no re-ingest reached the drawn files in the window)")
    else:
        holds = pa >= ANCHOR_MIN and pa - pi >= GAP_MIN
        print(f"H-A2: anchor >= {ANCHOR_MIN:.0%} and anchor - id >= {GAP_MIN * 100:.0f} points -> "
              f"{'holds' if holds else 'does not hold'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
