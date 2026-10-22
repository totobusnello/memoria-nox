#!/usr/bin/env python3
"""Resolve the PT-BR golden set's stable anchors to today's chunk ids.

Why anchors instead of ids: v1 of this set keyed gold by `expected_chunk_ids`,
and re-ingest mints new ids. On 2026-10-22, 61 of its 85 ids no longer existed
and 33 of 66 queries pointed at nothing at all — while the file still looked
perfectly valid. An id-keyed ruler decays in silence at every re-ingest.

An anchor is (source_file, verbatim span). This resolver maps it to the current
id and FAILS LOUDLY when it cannot: `unresolved` and `ambiguous` are reported
per entry and the exit code is non-zero if any gold fails to resolve. The point
is not that anchors never break — it is that when they break, the ruler says so
instead of scoring against ghosts.

Read-only: opens the database with mode=ro and writes nothing to it.
"""
import json, os, re, sqlite3, sys, unicodedata

DB   = os.environ.get("GOLD_DB", "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db")
GOLD = sys.argv[1] if len(sys.argv) > 1 else "eval/golden-queries-v2.jsonl"
OUT  = sys.argv[2] if len(sys.argv) > 2 else None
PREFIX = int(os.environ.get("ANCHOR_PREFIX", "160"))   # chars do início da âncora exigidos

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
rows = [json.loads(l) for l in open(GOLD, encoding="utf-8") if l.strip()]

tally = {"resolved": 0, "moved": 0, "ambiguous": 0, "unresolved": 0}
report = []
for r in rows:
    for g in r.get("gold", []):
        needle = norm(g["anchor"])[:PREFIX]
        hits = [cid for (cid, txt) in con.execute(
                    "SELECT id, chunk_text FROM chunks WHERE source_file = ?",
                    (g["source_file"],)).fetchall()
                if needle and needle in norm(txt)]
        was = g.get("chunk_id")
        if not hits:
            state = "unresolved"
        elif len(hits) > 1:
            state = "ambiguous"
        elif hits[0] == was:
            state = "resolved"
        else:
            state = "moved"
        tally[state] += 1
        report.append({"query_id": r["query_id"], "source_file": g["source_file"],
                       "state": state, "recorded_id": was, "resolved_ids": hits,
                       "anchor_head": g["anchor"][:80]})

print(f"gold entries: {sum(tally.values())}")
for k in ("resolved", "moved", "ambiguous", "unresolved"):
    print(f"  {k:12s} {tally[k]:3d}")
bad = [x for x in report if x["state"] in ("unresolved", "ambiguous")]
for x in bad[:20]:
    print(f"  ! Q{x['query_id']} {x['state']:10s} {x['source_file'][:58]}  -> {x['resolved_ids']}")
if OUT:
    json.dump({"tally": tally, "entries": report}, open(OUT, "w"), indent=1, ensure_ascii=False)
sys.exit(1 if bad else 0)
