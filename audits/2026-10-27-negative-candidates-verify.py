"""Triple verification for two negative candidates, matching golden-negatives-v1's
own criterion: raw substring, FTS5 phrase, and KG entity name all zero.

Both came out of the PT-BR golden set as `no_source_in_pool` with no gold, and
the mechanical check says the corpus has no such token at all — while the stems
DO exist (`reclassify` in 10 chunks, `RELATION_TYPE` in 7). That makes them the
provoking kind of negative: a plausible neighbour is present and pulls.
"""
import sqlite3

con = sqlite3.connect("file:/root/.openclaw/workspace/tools/nox-mem/nox-mem.db?mode=ro",
                      uri=True)
tot = con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
print(f"corpus_chunks = {tot}")
for t, stem in (("kg-reclassify", "reclassify"),
                ("RELATION_TYPE_TO_REASON", "RELATION_TYPE")):
    raw = con.execute("SELECT COUNT(*) FROM chunks WHERE chunk_text LIKE ?",
                      ("%" + t + "%",)).fetchone()[0]
    try:
        fts = con.execute("SELECT COUNT(*) FROM chunks_fts WHERE chunks_fts MATCH ?",
                          ('"' + t + '"',)).fetchone()[0]
    except Exception as e:
        fts = f"ERR:{type(e).__name__}"
    kg = con.execute("SELECT COUNT(*) FROM kg_entities WHERE name LIKE ?",
                     ("%" + t + "%",)).fetchone()[0]
    sraw = con.execute("SELECT COUNT(*) FROM chunks WHERE chunk_text LIKE ?",
                       ("%" + stem + "%",)).fetchone()[0]
    print(f"  {t:26s} raw={raw} fts={fts} kg={kg}   | stem '{stem}' raw={sraw}")

# control: the criterion must NOT pass for something that does exist
for t in ("kg-build", "reindex"):
    raw = con.execute("SELECT COUNT(*) FROM chunks WHERE chunk_text LIKE ?",
                      ("%" + t + "%",)).fetchone()[0]
    try:
        fts = con.execute("SELECT COUNT(*) FROM chunks_fts WHERE chunks_fts MATCH ?",
                          ('"' + t + '"',)).fetchone()[0]
    except Exception as e:
        fts = f"ERR:{type(e).__name__}"
    print(f"  CONTROL {t:18s} raw={raw} fts={fts}  "
          f"{'ok (criterion correctly rejects it as a negative)' if raw > 0 else 'PROBLEM'}")
