"""Why did the positive control fail on Q99? Two hypotheses, and they need
different fixes: the gold chunk never entered the pool (a recall problem in my
FTS expression), or it entered and the judge rejected it (a judge problem).
"""
import json, re, sqlite3, unicodedata

con = sqlite3.connect("file:/root/.openclaw/workspace/tools/nox-mem/nox-mem.db?mode=ro",
                      uri=True)
rows = {r["query_id"]: r for r in
        (json.loads(l) for l in open("/root/medicoes/golden-queries-v2.jsonl") if l.strip())}
r = rows[99]
print("Q99:", r["query"])
want = r["gold"][0]["source_file"]
print("  gold src:", want)
print("  anchor  :", r["gold"][0]["anchor"][:120].replace("\n", " "))

STOP = {"como", "qual", "quais", "que", "the", "de", "do", "da", "em", "no", "na",
        "para", "por", "com", "sem", "um", "uma", "os", "as", "e", "o", "a", "se",
        "faz", "funciona", "atual", "entre"}
t = unicodedata.normalize("NFKD", r["query"].lower())
t = "".join(c for c in t if not unicodedata.combining(c))
ws = [w for w in re.findall(r"[a-z0-9_]{3,}", t) if w not in STOP]
print("  termos  :", ws)
expr = " OR ".join('"' + w + '"' for w in ws)

for lim in (40, 200, 2000):
    cand = con.execute(
        "SELECT c.id, c.source_file FROM chunks_fts JOIN chunks c ON c.id=chunks_fts.rowid "
        "WHERE chunks_fts MATCH ? ORDER BY bm25(chunks_fts) LIMIT ?", (expr, lim)).fetchall()
    pos = [i for i, b in enumerate(cand, 1) if b[1] == want]
    print(f"  pool {lim:5d}: total {len(cand):5d} · gold at rank {pos[:3] if pos else 'ABSENT'}")

# does the gold chunk even match the expression at all?
ids = [i for (i,) in con.execute(
    "SELECT id FROM chunks WHERE source_file = ?", (want,)).fetchall()]
print(f"\n  chunks in that source_file: {ids}")
for cid in ids:
    hit = con.execute(
        "SELECT COUNT(*) FROM chunks_fts WHERE chunks_fts MATCH ? AND rowid = ?",
        (expr, cid)).fetchone()[0]
    txt = con.execute("SELECT substr(chunk_text,1,100) FROM chunks WHERE id=?",
                      (cid,)).fetchone()[0]
    print(f"    id={cid} matches_expr={bool(hit)}  {txt.replace(chr(10),' ')[:80]!r}")

# which terms does it actually contain?
full = con.execute("SELECT group_concat(chunk_text, ' ') FROM chunks WHERE source_file = ?",
                   (want,)).fetchone()[0] or ""
nf = unicodedata.normalize("NFKD", full.lower())
nf = "".join(c for c in nf if not unicodedata.combining(c))
print(f"\n  terms present in the gold source: "
      f"{ {w: (w in nf) for w in ws} }")
