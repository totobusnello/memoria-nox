#!/usr/bin/env python3
"""Paper A, H-A2: exploratory diagnosis, NOT registered (written 2026-11-18, after the reading).

The registered run (holdout-persistence.py) found by id 119/120 and by anchor 117/120, the reverse
of the prediction, with 1 query exposed. This script asks why, for the queries that matter to that
reading only: the exposed ones (gold id gone or changed) and the ones reached by id but not by
anchor. It prints source paths, ids, strata and counts. It prints no chunk text, no question and
no evidence span.

  python3 -I h-a2-anchor-diagnosis.py --frozen-db <2026-11-04 snapshot.db> \
      --later-db <the 2026-11-18 snapshot, decompressed by holdout-persistence.py into its workdir> \
      --holdout <holdout.jsonl>

Same criterion as holdout-persistence.py: a reference persists if it leads to an ACTIVE chunk
(superseded_by IS NULL) whose whitespace-normalised text contains the evidence span; the anchor
looks only in chunks whose source_file equals the gold's.

Keyless, read-only.
"""
import argparse
import json
import re
import sqlite3


def ws(t):
    return re.sub(r"\s+", " ", t).strip()


def ro(p):
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True)


def main():
    ap = argparse.ArgumentParser()
    for k in ("--frozen-db", "--later-db", "--holdout"):
        ap.add_argument(k, required=True)
    a = ap.parse_args()
    fz, lt = ro(a.frozen_db), ro(a.later_db)
    hold = [json.loads(l) for l in open(a.holdout, encoding="utf-8")]
    for h in hold:
        g = h["gold"][0]
        ev, sf = ws(g["anchor"]), g["source_file"]
        r = lt.execute("SELECT chunk_text, source_file FROM chunks WHERE id = ? AND superseded_by IS NULL",
                       (g["chunk_id"],)).fetchone()
        by_id = r is not None and ev in ws(r[0])
        frozen = fz.execute("SELECT chunk_text FROM chunks WHERE id = ?", (g["chunk_id"],)).fetchone()[0]
        exposed = r is None or r[0] != frozen
        hits = [c for c, t in lt.execute(
            "SELECT id, chunk_text FROM chunks WHERE source_file = ? AND superseded_by IS NULL", (sf,))
            if ev in ws(t)]
        if not (exposed or (by_id and not hits)):
            continue
        count = lambda db, extra: db.execute(
            f"SELECT COUNT(*) FROM chunks WHERE source_file = ?{extra}", (sf,)).fetchone()[0]
        print(json.dumps({
            "query_id": h["query_id"], "stratum": h["stratum"],
            "kind": "exposed" if exposed else "reached by id only",
            "gold_source_file": sf,
            "later_source_file_of_gold_id": r[1] if r else None,
            "active_chunks_at_gold_path_frozen": count(fz, " AND superseded_by IS NULL"),
            "active_chunks_at_gold_path_later": count(lt, " AND superseded_by IS NULL"),
            "any_chunks_at_gold_path_later": count(lt, ""),
            "by_id": by_id, "anchor_hits": len(hits)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
