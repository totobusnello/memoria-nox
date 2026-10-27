"""How much of the corpus is byte-identical duplication, and does it cap nDCG@10?

Q71's gold anchor matched two chunks with sha1 721d225e2539c37e, and its file
holds 93 chunks with 46 distinct texts. If duplication is widespread, a top-10
can spend slots on copies of one fact, which depresses nDCG@10 BY CONSTRUCTION
and is a property of the corpus, not of the retriever. That changes how the
published interval must be read, so it is measured.

Read-only (mode=ro).
"""
import sqlite3
from collections import Counter

con = sqlite3.connect("file:/root/.openclaw/workspace/tools/nox-mem/nox-mem.db?mode=ro",
                      uri=True)
tot, uniq = con.execute(
    "SELECT COUNT(*), COUNT(DISTINCT chunk_text) FROM chunks").fetchone()
print(f"corpus: {tot:,} chunks · {uniq:,} distinct texts · "
      f"{tot-uniq:,} duplicate rows = {(tot-uniq)/tot:.1%}")

# how the duplication is distributed: a few huge clusters, or many small ones?
rows = con.execute(
    "SELECT COUNT(*) n FROM chunks GROUP BY chunk_text HAVING n > 1 ORDER BY n DESC"
).fetchall()
sizes = [r[0] for r in rows]
print(f"\nduplicate clusters: {len(sizes):,} · largest {max(sizes) if sizes else 0} copies "
      f"· median {sorted(sizes)[len(sizes)//2] if sizes else 0}")
print(f"  clusters of size 2: {sum(1 for s in sizes if s == 2):,} · "
      f">=5: {sum(1 for s in sizes if s >= 5):,} · >=20: {sum(1 for s in sizes if s >= 20):,}")

# within a file vs across files — they mean different things
same_file = con.execute(
    "SELECT COUNT(*) FROM (SELECT chunk_text FROM chunks GROUP BY chunk_text, source_file "
    "HAVING COUNT(*) > 1)").fetchone()[0]
print(f"\nclusters that are duplication WITHIN one file: {same_file:,} "
      f"(the rest is the same text in different files)")

print("\nworst files by duplication:")
for sf, n, u in con.execute(
        "SELECT source_file, COUNT(*) n, COUNT(DISTINCT chunk_text) u FROM chunks "
        "GROUP BY source_file HAVING n - u > 10 ORDER BY (n-u) DESC LIMIT 8"):
    print(f"  {n-u:4d} dupes of {n:4d}  ({(n-u)/n:4.0%})  {sf[:60]}")

# the ceiling this puts on a top-10: for a query, how many of the top-10 could
# be copies? Bound it by the duplication rate of the files gold lives in.
print("\nthe cap, stated as a bound rather than a simulation:")
print(f"  {(tot-uniq)/tot:.1%} of rows are copies, so a top-10 drawn uniformly would")
print(f"  waste ~{10*(tot-uniq)/tot:.1f} slots. BM25 does not draw uniformly — copies")
print("  score identically, so they tend to arrive ADJACENT, which is worse than")
print("  uniform for a cut-off at 10. This is a bound, not an estimate: measuring")
print("  the real waste needs the actual top-10s, which is a scoring run.")
