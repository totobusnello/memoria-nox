#!/usr/bin/env python3
"""Read-only answer probe for the FTS5 leg: records the exact result list of
src/search.ts:410 for 12 PT-BR queries, so the answer can be compared verbatim
before and after 'optimize'. Writes nothing: opens the DB with mode=ro and never
touches the API (an API search would write telemetry and access counts, i.e. feed
the ranking signals it is supposed to be measuring)."""
import sqlite3, sys, json, hashlib

DB = sys.argv[1]
OUT = sys.argv[2]
QUERIES = ["memoria", "brief agente", "vetor embedding", "incidente producao",
           "paper latencia", "chunk salience", "sqlite indice", "decisao roadmap",
           "gemini quota", "worktree branch", "telemetria custo", "kg entidade"]

SQL = """
      SELECT c.id, bm25(chunks_fts, 1.0, 0.5, 0.5) as rank
      FROM chunks_fts
      JOIN chunks c ON c.id = chunks_fts.rowid
      WHERE chunks_fts MATCH ?
      ORDER BY rank LIMIT 20
"""

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
con.execute("PRAGMA cache_size=-64000")
con.execute("PRAGMA mmap_size=268435456")

res = {}
for q in QUERIES:
    rows = con.execute(SQL, (q,)).fetchall()
    # round the rank: bm25 is a float, and a bit-level diff would be noise, not a
    # changed answer. The id order is the answer.
    res[q] = {"n": len(rows),
              "ids": [r[0] for r in rows],
              "ranks": [round(r[1], 6) for r in rows]}

blob = json.dumps(res, sort_keys=True)
out = {"sha256": hashlib.sha256(blob.encode()).hexdigest(), "queries": res}
with open(OUT, "w") as f:
    json.dump(out, f, indent=1, sort_keys=True)
print(out["sha256"])
for q in QUERIES:
    print(f"  {q:24s} n={res[q]['n']:3d}")
