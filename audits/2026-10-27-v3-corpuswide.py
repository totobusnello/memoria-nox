"""v3, second pass: search the WHOLE corpus for the 22 the file-level pass could not fix.

The attribution went wrong twice today and only measurement settled it:

  1st audit  "the anchor landed on a MENTION of the term"      -> about the span
  2nd (mine) "it resolved to the wrong CHUNK of the right file" -> about the chunk
  measured   22 of 28 queries have NO chunk in their source_file that answers
             -> the FILE is wrong, and the first two readings were both too local

So this pass does what the file-level one could not: a deep pool over the entire
corpus (BM25 over the OR of the query's terms, top-40, mode=ro), the bounded
judge on each candidate, and gold built where something answers. It is the same
instrument that worked on the nine — applied to the twenty-two.

Controls again in this batch, because a calibration is a fact about its batch.
"""
import json, os, random, re, sqlite3, sys, time, unicodedata, urllib.error, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

DB = "file:/root/.openclaw/workspace/tools/nox-mem/nox-mem.db?mode=ro"
GOLD = "/root/medicoes/golden-queries-v2.jsonl"
PREV = "/root/medicoes/v3-reselect-2026-10-27.json"
OUT = "/root/medicoes/v3-corpuswide-2026-10-27.json"
OKEY = os.environ["OPENAI_API_KEY"]
JMODEL = os.environ.get("JUDGE_MODEL", "gpt-6-luna")
WORKERS = int(os.environ.get("WORKERS", "8"))
CUT, THR, SEED, POOL = 6000, 0.5, 20261027, 40
STOP = {"como", "qual", "quais", "que", "the", "de", "do", "da", "em", "no", "na",
        "para", "por", "com", "sem", "um", "uma", "os", "as", "e", "o", "a", "se",
        "faz", "funciona", "atual", "entre", "ser", "tem", "ha", "mais", "sobre"}

con = sqlite3.connect(DB, uri=True)
rows = {r["query_id"]: r for r in
        (json.loads(l) for l in open(GOLD, encoding="utf-8") if l.strip())}
prev = json.load(open(PREV))

# the queries the file-level pass could not repair
byq = {}
for r in prev:
    if r["kind"] != "candidate" or "responde" not in r:
        continue
    byq.setdefault(r["query_id"], []).append(r["responde"] or 0)
TARGET = sorted(q for q, v in byq.items() if max(v) <= THR)
print(f"targets (file-level pass found nothing): {len(TARGET)} -> {TARGET}")

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()

def pool_for(q):
    ws = [w for w in re.findall(r"[a-z0-9_]{3,}", norm(q)) if w not in STOP]
    if not ws:
        return []
    expr = " OR ".join('"' + w + '"' for w in ws)
    return con.execute(
        "SELECT c.id, c.source_file, c.chunk_text FROM chunks_fts "
        "JOIN chunks c ON c.id = chunks_fts.rowid WHERE chunks_fts MATCH ? "
        "ORDER BY bm25(chunks_fts) LIMIT ?", (expr, POOL)).fetchall()

# ---- PHASE 1, SERIAL
pools = {q: pool_for(rows[q]["query"]) for q in TARGET}
print(f"pools read serially · sizes {sorted(len(v) for v in pools.values())}")
empty = [q for q, v in pools.items() if not v]
if empty:
    print(f"! EMPTY POOLS {empty} — undecidable, not negative")

cands = []
for q, ps in pools.items():
    for cid, sf, txt in ps:
        cands.append({"query_id": q, "query": rows[q]["query"],
                      "category": rows[q].get("category"), "source_file": sf,
                      "chunk_id": cid, "text": txt, "kind": "candidate"})
rng = random.Random(SEED)
allids = [i for (i,) in con.execute("SELECT id FROM chunks ORDER BY id")]
for q in TARGET:
    cid = rng.choice(allids)
    txt, sf = con.execute("SELECT chunk_text, source_file FROM chunks WHERE id=?",
                          (cid,)).fetchone()
    cands.append({"query_id": q, "query": rows[q]["query"], "category": "ctl",
                  "source_file": sf, "chunk_id": cid, "text": txt, "kind": "random"})
# positive control: the 6 repaired by the file-level pass must still be accepted
rep = {}
for r in prev:
    if r["kind"] == "candidate" and (r.get("responde") or 0) > THR:
        rep.setdefault(r["query_id"], r)
for q, r in list(rep.items())[:6]:
    txt = con.execute("SELECT chunk_text FROM chunks WHERE id=?", (r["chunk_id"],)).fetchone()
    if txt:
        cands.append({"query_id": q, "query": r["query"], "category": "ctl",
                      "source_file": r["source_file"], "chunk_id": r["chunk_id"],
                      "text": txt[0], "kind": "repaired_again"})
print(f"to judge: {len(cands)} {dict(Counter(c['kind'] for c in cands))}", flush=True)

RESPONDE = ("O TRECHO contem informacao que responde, total ou parcialmente, a esta "
            "PERGUNTA: {q}\nConta como responder trazer o dado pedido, ainda que com "
            "outra redacao. NAO conta mencionar apenas o assunto sem o dado.")

def judge(q, txt):
    body = {"model": JMODEL, "input": f"TRECHO:\n---\n{txt[:CUT]}\n---",
            "questions": [{"type": "predicate", "name": "responde",
                           "instructions": RESPONDE.format(q=q)}]}
    req = urllib.request.Request("https://api.openai.com/v1/decisions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {OKEY}"})
    last = None
    for a in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            ans = {x["name"]: x for x in d.get("answers", [])}
            if "responde" not in ans:
                raise RuntimeError(f"envelope without the predicate: {list(d)[:6]}")
            return (ans["responde"].get("probability"),
                    (d.get("usage") or {}).get("input_tokens", 0))
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode()[:160]}"
            if e.code in (400, 401, 403, 404):
                break
            time.sleep(2 * (a + 1))
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:140]}"
            time.sleep(2 * (a + 1))
    raise RuntimeError(str(last))

res, t0, toks = [], time.time(), 0
def work(c):
    try:
        p, t = judge(c["query"], c["text"])
        return {**c, "responde": p, "tok": t, "anchor": c["text"][:200]}
    except Exception as e:
        return {**c, "erro": str(e)[:120]}
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for i, r in enumerate(ex.map(work, cands), 1):
        r.pop("text", None)
        res.append(r); toks += r.get("tok", 0)
        if i % 100 == 0 or i == len(cands):
            print(f"  {i}/{len(cands)}  {time.time()-t0:.0f}s", flush=True)
json.dump(res, open(OUT, "w"), ensure_ascii=False)
print(f"\n{len(res)} judged · {sum(1 for r in res if 'erro' in r)} errors · "
      f"{toks} tokens (~US$ {toks/1e6*0.10:.4f}) · {time.time()-t0:.0f}s")

def rate(k):
    g = [r for r in res if r["kind"] == k and "responde" in r]
    return (sum(1 for r in g if (r["responde"] or 0) > THR)/len(g), len(g)) if g else (None, 0)
nc, nn = rate("random"); pc, pn = rate("repaired_again")
print(f"\nCONTROLS\n  negative {nc:.1%} of {nn}  {'PASS' if nc < 0.15 else 'FAIL'}")
print(f"  positive {pc:.1%} of {pn}  {'PASS' if pc > 0.85 else 'FAIL'}")
if nc >= 0.15 or (pn and pc <= 0.85):
    sys.exit(3)

found, still = {}, []
for r in res:
    if r["kind"] != "candidate" or "responde" not in r:
        continue
    if (r["responde"] or 0) > THR:
        found.setdefault(r["query_id"], []).append(r)
for q in TARGET:
    if q not in found:
        still.append(q)
print(f"\nCORPUS-WIDE REPAIR of {len(TARGET)}:")
print(f"  gold found elsewhere in the corpus: {len(found)} queries")
for q, hs in sorted(found.items()):
    b = max(hs, key=lambda x: x["responde"])
    old = rows[q]["gold"][0]["source_file"]
    print(f"    Q{q:<4d} p={b['responde']:.2f}  {b['source_file'][:50]}")
    print(f"           was: {old[:50]}")
print(f"  genuinely unanswerable (0 of {POOL} anywhere): {len(still)} -> {still}")
print(f"\nqueries with no valid gold: 15 -> {len(still)}  "
      f"(zeros forçados {15/55:.1%} -> {len(still)/55:.1%})")
