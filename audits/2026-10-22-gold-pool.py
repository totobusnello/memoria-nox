#!/usr/bin/env python3
"""Stage 1 of the PT-BR golden-set repair: build a DEEP candidate pool per query.

Read-only on the served database (mode=ro) and never through /api/search or the
CLI: a search through those writes search_telemetry and bumps access_count, i.e.
it feeds the very ranking signals the golden set is meant to score.

Pool = BM25 top-K union vector-KNN top-K, K=40 by default. The depth is the
point: the set is evaluated at rank 10, so drawing gold from a top-10 pool would
guarantee a high score by construction. A deep pool keeps that bias bounded, and
the bias that remains is stated in the report: a query whose answer this index
cannot surface at all within 40 ranks on either leg will find no gold here.

Writes: one NDJSON line per query into the output file. Nothing into the database.
"""
import json, os, sqlite3, struct, sys, time, urllib.request, re

DB      = os.environ.get("GOLD_DB", "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db")
QUERIES = sys.argv[1]
OUT     = sys.argv[2]
K       = int(os.environ.get("GOLD_K", "40"))
KEY     = os.environ.get("GEMINI_API_KEY")
EMB     = "gemini-embedding-001"
API     = "https://generativelanguage.googleapis.com/v1beta"

STOP = set("o a os as de do da das dos e em no na nos nas um uma para por com que qual quais "
           "como quando onde se eh sao ser esta estao ao aos foi era mais menos sobre entre".split())

def fts_expr(q):
    """FTS5 MATCH expression. Every term is quoted: '-' is an operator in FTS5, so
    an unquoted `nox-mem` is a syntax error — and a syntax error here comes back as
    an empty result set, which reads exactly like 'no hits'."""
    terms = [t for t in re.findall(r"[\w-]{3,}", q.lower()) if t not in STOP]
    terms = [t.replace('"', "") for t in terms][:12]
    return " OR ".join(f'"{t}"' for t in terms) if terms else None

def embed_query(text):
    body = json.dumps({"model": f"models/{EMB}",
                       "content": {"parts": [{"text": text[:8000]}]},
                       "taskType": "RETRIEVAL_QUERY"}).encode()
    req = urllib.request.Request(f"{API}/models/{EMB}:embedContent?key={KEY}",
                                 data=body, headers={"Content-Type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)["embedding"]["values"]
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
con.execute("PRAGMA cache_size=-64000")
con.enable_load_extension(True)
for p in ("/root/.openclaw/workspace/tools/nox-mem/node_modules/sqlite-vec/vec0",
          "/usr/local/lib/vec0", "vec0"):
    try:
        con.load_extension(p)
        VEC = True
        break
    except Exception:
        VEC = False

rows = [json.loads(l) for l in open(QUERIES, encoding="utf-8") if l.strip()]
done = set()
if os.path.exists(OUT):
    for l in open(OUT, encoding="utf-8"):
        try:
            done.add(json.loads(l)["query_id"])
        except Exception:
            pass

out = open(OUT, "a", encoding="utf-8")
n_ok = 0
for r in rows:
    qid, q = r["query_id"], r["query"]
    if qid in done:
        continue
    bm25, knn, err = [], [], None
    expr = fts_expr(q)
    if expr:
        try:
            bm25 = [x[0] for x in con.execute(
                "SELECT c.id FROM chunks_fts JOIN chunks c ON c.id=chunks_fts.rowid "
                "WHERE chunks_fts MATCH ? ORDER BY bm25(chunks_fts,1.0,0.5,0.5) LIMIT ?",
                (expr, K)).fetchall()]
        except sqlite3.OperationalError as e:
            err = f"fts: {e}"
    if VEC and KEY:
        try:
            v = embed_query(q)
            blob = struct.pack(f"{len(v)}f", *v)
            knn = [x[0] for x in con.execute(
                "SELECT m.chunk_id FROM (SELECT rowid, distance FROM vec_chunks "
                "WHERE embedding MATCH ? AND k = ?) v JOIN vec_chunk_map m ON m.rowid = v.rowid "
                "ORDER BY v.distance", (blob, K)).fetchall()]
        except Exception as e:
            err = (err + " | " if err else "") + f"knn: {type(e).__name__}: {e}"
    pool, seen = [], set()
    for i in (bm25 + knn):                      # ordem: BM25 primeiro, depois KNN
        if i not in seen:
            seen.add(i); pool.append(i)
    out.write(json.dumps({"query_id": qid, "query": q,
                          "category": r.get("category"), "difficulty": r.get("difficulty"),
                          "old_expected": r.get("expected_chunk_ids") or [],
                          "n_bm25": len(bm25), "n_knn": len(knn), "pool": pool,
                          "error": err}, ensure_ascii=False) + "\n")
    out.flush()
    n_ok += 1
    print(f"Q{qid:<4} bm25={len(bm25):<3} knn={len(knn):<3} pool={len(pool):<3} {'ERR '+err if err else ''}",
          flush=True)
out.close()
print(f"\nCOMPLETO: {n_ok} queries novas, {len(done)} já estavam no arquivo, total esperado {len(rows)}")
