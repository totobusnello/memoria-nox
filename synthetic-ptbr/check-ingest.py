#!/usr/bin/env python3
"""Gate «S: pós-ingest» (PLANO.md): what the nox-mem package made of the corpus is what the
method tests assume.

  python3 -I synthetic-ptbr/check-ingest.py --db <isolated nox-mem db> [--plan <plan.json>]

Exit 0 only if all hold; every failure is listed, then exit 1:
  1. every planted item lies WHOLE inside chunks: a count-1 item in exactly one chunk, a duplicated
     primary in exactly two chunks whose texts are byte-identical (no sentence cut by a chunk
     boundary, no duplicate merged into one chunk);
  2. every operation-target file has two or more chunks and its primary in exactly one, so an edit
     outside the planted sentence can leave that sentence's chunk untouched;
  3. no chunk holding a context negative also holds a positive of the same fact;
  4. every chunk belongs to a planned file, and every planned file has chunks.
The database is opened read-only.
"""
import argparse
import collections
import pathlib
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import s_common as C  # noqa: E402


def load_chunks(db):
    if not pathlib.Path(db).is_file():
        raise SystemExit("check-ingest: ERROR no database at the given path")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = con.execute("SELECT id, source_file, section, chunk_text FROM chunks").fetchall()
    con.close()
    return [{"id": r[0], "source_file": r[1], "section": r[2], "text": r[3] or ""} for r in rows]


def check(plan, chunks):
    fails = []
    by_file = collections.defaultdict(list)
    for c in chunks:
        by_file[c["source_file"]].append(c)
    planned = {f["path"] for f in plan["files"]}
    for p in sorted(set(by_file) - planned):
        fails.append(f"chunks of a file not in the plan: {p}")
    for p in sorted(planned - set(by_file)):
        fails.append(f"planned file with no chunk: {p}")

    holders = {}
    for f in plan["files"]:
        for it in f["items"]:
            hs = [c for c in chunks if it["text"] in c["text"]]
            holders[it["id"]] = hs
            if it["count"] == 1 and len(hs) != 1:
                fails.append(f"{it['id']}: whole in {len(hs)} chunk(s), want 1")
            if it["count"] == 2:
                if len(hs) != 2:
                    fails.append(f"{it['id']}: duplicated primary whole in {len(hs)} chunk(s), want 2")
                elif hs[0]["text"] != hs[1]["text"]:
                    fails.append(f"{it['id']}: the two chunks of a duplicate differ")
            for c in hs:
                if c["source_file"] != f["path"]:
                    fails.append(f"{it['id']}: found in a chunk of another file ({c['source_file']})")

    for fact in plan["facts"]:
        if fact["operation"]:
            cs = by_file.get(fact["primary"]["path"], [])
            if len(cs) < 2:
                fails.append(f"{fact['id']} ({fact['operation']}): its file has {len(cs)} chunk(s), want 2+")
        positives = {fact["primary"]["id"]} | {a["id"] for a in fact["paraphrases"]}
        pos_ids = {c["id"] for iid in positives for c in holders.get(iid, [])}
        for n in fact["negatives"]:
            if {c["id"] for c in holders.get(n["id"], [])} & pos_ids:
                fails.append(f"{n['id']}: shares a chunk with a positive of {fact['id']}")
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--plan", default=str(C.PLAN_FILE))
    a = ap.parse_args()
    chunks = load_chunks(a.db)
    fails = check(C.load_plan(a.plan), chunks)
    for x in fails[:40]:
        print(f"  ! {x}")
    print(f"check-ingest: {len(chunks)} chunks; {'FAIL, ' + str(len(fails)) + ' problem(s)' if fails else 'ok'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
