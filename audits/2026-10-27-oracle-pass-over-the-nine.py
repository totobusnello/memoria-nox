"""The oracle pass over the 9 PT-BR queries that were excluded with no gold.

Why it matters. On 2026-10-27 the nine were shown to ask about topics the corpus
HOLDS (`cross-search` in 11 chunks, `kg-build` in 17, `reindex` in 128, ...)
while carrying `gold = []` and status `no_source_in_pool`. Excluding them raises
the published score: strict nDCG@10 0.2428 -> 0.2087 and pooled 0.5114 -> 0.4395
if they enter as zero-hit, i.e. both ends of the published interval are up to
14% optimistic. Topic coverage is not answer coverage, so that was a bound, not
a correction. This pass is what turns it into one.

Per query: a deliberately WIDE pool (FTS5/BM25 over OR of the query's terms,
top-40), then the bounded judge on every candidate. Three outcomes:

  gold built   -- some chunk answers it. The query joins the ruler, and its
                  zero-hit is then a real retrieval failure, because production's
                  own deep pool did not bring that chunk.
  negative     -- nothing answers it. It joins golden-negatives.
  bad question -- the closed-book oracle answers it without any context, so it
                  tests general knowledge rather than this corpus.

The pool is wider than production's ON PURPOSE. If a wider pool finds the source,
the conclusion "it exists and production missed it" gets stronger, not weaker.

NO SEARCH PATH IS CALLED. The pool is built with FTS5 MATCH over a read-only
connection, so no telemetry row is written and no access_count is bumped —
`searchHybrid` would have done both, and a probe that writes the state it
measures is a defect this repository has already paid for.

CONTROL: three already-accepted queries go through the same pipeline and their
KNOWN gold must come back. If the pipeline cannot rediscover gold that is on
record, it cannot be trusted to report its absence.
"""
import json, os, re, sqlite3, sys, time, unicodedata, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

DB = "file:/root/.openclaw/workspace/tools/nox-mem/nox-mem.db?mode=ro"
GOLD = "/root/medicoes/golden-queries-v2.jsonl"
OUT = "/root/medicoes/oracle-nine-2026-10-27.json"
OKEY = os.environ["OPENAI_API_KEY"]
GKEY = os.environ["GEMINI_API_KEY"]
JMODEL = os.environ.get("JUDGE_MODEL", "gpt-6-luna")
GMODEL = "gemini-2.5-flash-lite"
POOL = int(os.environ.get("POOL", "40"))
CUT = 6000
WORKERS = int(os.environ.get("WORKERS", "8"))
SMOKE = os.environ.get("SMOKE", "")

TARGET = [72, 83, 85, 89, 49, 52, 79, 108, 68]      # the 9 (68 is the unvalidated negative)
# Six accepted queries with gold on record. A control that fails is reported as a
# SUSPECT GOLD rather than as a broken pipeline, because on 2026-10-27 Q99's control
# failure turned out to be a mis-attributed gold: the query asks for the maximum
# number of storable chunks and its gold says "229 chunks = ~52k tokens excede o
# limite do Groq", which is a per-call API limit. The gold was at ranks 5 and 8 of
# the pool, so recall was fine and the judge was right to reject it. The bar is a
# MAJORITY of controls rediscovering their gold; each failure is named.
CONTROL = [45, 92, 99, 101, 103, 105]

con = sqlite3.connect(DB, uri=True)
rows = {r["query_id"]: r for r in
        (json.loads(l) for l in open(GOLD, encoding="utf-8") if l.strip())}

STOP = {"como", "qual", "quais", "que", "the", "de", "do", "da", "em", "no", "na",
        "para", "por", "com", "sem", "um", "uma", "os", "as", "e", "o", "a", "se",
        "faz", "funciona", "atual", "entre"}
def terms(q):
    t = unicodedata.normalize("NFKD", q.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    ws = [w for w in re.findall(r"[a-z0-9_]{3,}", t) if w not in STOP]
    return ws

def pool_for(q):
    ws = terms(q)
    if not ws:
        return []
    expr = " OR ".join(f'"{w}"' for w in ws)
    try:
        return con.execute(
            "SELECT c.id, c.source_file, c.chunk_text, bm25(chunks_fts) s "
            "FROM chunks_fts JOIN chunks c ON c.id = chunks_fts.rowid "
            "WHERE chunks_fts MATCH ? ORDER BY s LIMIT ?", (expr, POOL)).fetchall()
    except Exception as e:
        print(f"  ! pool failed for {q[:40]!r}: {type(e).__name__}: {e}")
        return []

def post(url, body, hdr, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=hdr)
    last = None
    for a in range(5):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode()[:160]}"
            if e.code in (400, 401, 403, 404):
                break
            time.sleep(2 * (a + 1))
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:140]}"
            time.sleep(2 * (a + 1))
    raise RuntimeError(str(last))

# ---- closed-book oracle: can the question be answered with no corpus at all?
CLOSED = ("Responda a pergunta usando APENAS conhecimento proprio. Se a resposta depende "
          "de documentos internos de um sistema especifico que voce nao conhece, responda "
          "exatamente: NAO SEI. Maximo 25 palavras.")
def closed_book(q):
    d = post(f"https://generativelanguage.googleapis.com/v1beta/models/{GMODEL}"
             f":generateContent?key={GKEY}",
             {"systemInstruction": {"parts": [{"text": CLOSED}]},
              "contents": [{"parts": [{"text": q}]}],
              "generationConfig": {"temperature": 0.0, "maxOutputTokens": 120}},
             {"Content-Type": "application/json"})
    c = (d.get("candidates") or [{}])[0]
    return "".join(p.get("text", "") for p in
                   (c.get("content") or {}).get("parts") or []).strip()

# ---- the bounded judge, same shape as 2026-10-26-bounded-judge.py
RESPONDE = ("O TRECHO contem informacao que responde, total ou parcialmente, a esta "
            "PERGUNTA: {q}\nConta como responder trazer o dado pedido, ainda que com "
            "outra redacao. NAO conta mencionar apenas o assunto sem o dado.")
def judge(q, txt):
    d = post("https://api.openai.com/v1/decisions",
             {"model": JMODEL, "input": f"TRECHO:\n---\n{txt[:CUT]}\n---",
              "questions": [{"type": "predicate", "name": "responde",
                             "instructions": RESPONDE.format(q=q)}]},
             {"Content-Type": "application/json", "Authorization": f"Bearer {OKEY}"})
    ans = {a["name"]: a for a in d.get("answers", [])}
    if "responde" not in ans:
        raise RuntimeError(f"judge envelope without the predicate: keys={list(d)[:6]}")
    return (ans["responde"].get("probability"),
            (d.get("usage") or {}).get("input_tokens", 0))

def anchor_of(text, q):
    """A 160-char verbatim span, preferring a line that carries a query term."""
    ws = set(terms(q))
    best, score = None, -1
    for line in (l.strip() for l in text.split("\n")):
        if len(line) < 20:
            continue
        lw = set(terms(line))
        sc = len(ws & lw)
        if sc > score:
            best, score = line, sc
    base = best or text.strip()
    return base[:160]

todo = TARGET + CONTROL
if SMOKE:
    todo = [TARGET[0], CONTROL[0]]
print(f"queries: {len(todo)} ({len(TARGET)} target + {len(CONTROL)} control) · "
      f"pool {POOL} · judge {JMODEL}", flush=True)

# ---- PHASE 1, SERIAL: every pool is read before any thread starts.
# A single sqlite3 connection cannot be used from another thread, and the
# failure is a ProgrammingError that this script was swallowing into `pool = []`
# -- i.e. into "the corpus has no source", which is the answer being measured.
# The same defect killed the bounded judge on 2026-10-26 at pair ~300 of 516,
# after passing a 30-pair smoke. The phases are unrelated, so the fix is not a
# per-thread connection: reading is done up front and only the network fans out.
POOLS = {}
for qid in todo:
    POOLS[qid] = pool_for(rows[qid]["query"])
print(f"pools read serially: {len(POOLS)} · sizes "
      f"{sorted(len(v) for v in POOLS.values())}", flush=True)
empty = [q for q, v in POOLS.items() if not v]
if empty:
    print(f"! EMPTY POOLS for {empty} — these cannot be distinguished from "
          f"'no source exists' and are reported as such, not as negatives")

def work(qid):
    r = rows[qid]
    q = r["query"]
    out = {"query_id": qid, "query": q, "status_v2": r.get("status"),
           "is_control": qid in CONTROL,
           "known_gold": [g["source_file"] for g in r.get("gold", [])]}
    try:
        out["closed_book"] = closed_book(q)
    except Exception as e:
        out["closed_book"] = f"__ERR__ {str(e)[:80]}"
    cands = POOLS[qid]
    out["pool_size"] = len(cands)
    judged = []
    toks = 0
    for cid, sf, txt, s in cands:
        try:
            p, t = judge(q, txt)
            toks += t
        except Exception as e:
            judged.append({"id": cid, "source_file": sf, "erro": str(e)[:80]})
            continue
        judged.append({"id": cid, "source_file": sf, "bm25": s, "responde": p,
                       "anchor": anchor_of(txt, q) if (p or 0) > 0.5 else None})
    out["tokens"] = toks
    hits = [j for j in judged if (j.get("responde") or 0) > 0.5]
    out["n_judged"] = len([j for j in judged if "responde" in j])
    out["n_hits"] = len(hits)
    out["hits"] = sorted(hits, key=lambda j: -(j["responde"] or 0))[:5]
    return out

res, t0 = [], time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for i, r in enumerate(ex.map(work, todo), 1):
        res.append(r)
        print(f"  [{i}/{len(todo)}] Q{r['query_id']} pool={r['pool_size']} "
              f"hits={r['n_hits']} closed={r['closed_book'][:28]!r}", flush=True)
json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
toks = sum(r["tokens"] for r in res)
print(f"\n{len(res)} queries · {toks} input tokens (~US$ {toks/1e6*0.10:.4f}) "
      f"· {time.time()-t0:.0f}s")

print("\nCONTROL · a MAJORITY of accepted queries must rediscover their recorded gold")
ctl = [r for r in res if r["is_control"]]
passed = []
for r in ctl:
    found = {h["source_file"] for h in r["hits"]}
    known = set(r["known_gold"])
    hit = bool(found & known)
    passed.append(hit)
    print(f"  Q{r['query_id']:<4d} {'PASS' if hit else 'SUSPECT GOLD'} · "
          f"pool={r['pool_size']} hits={r['n_hits']}")
    if not hit:
        print(f"        known={[k[:46] for k in known]}")
        print(f"        found={[f[:46] for f in found][:3]}")
rate = sum(passed) / max(len(passed), 1)
print(f"  control: {sum(passed)}/{len(passed)} = {rate:.0%} "
      f"{'PASS' if rate > 0.5 else 'FAIL — absence below is not interpretable'}")
print("  A control failure here means the RECORDED gold is suspect, not that the")
print("  pipeline is broken — provided recall is fine, which the Q99 diagnosis showed.")
if rate <= 0.5:
    sys.exit(3)

def verdict(r):
    """Mutually exclusive, in precedence order.

    The closed-book oracle is INFORMATIVE, not decisive, and that is a correction
    made on 2026-10-27. Treating "the model produced text" as "the model knows"
    marked 7 of these 9 as bad questions — while the text it produced was
    fabrication: *"A versão atual do OpenClaw é a 7.6"* for an internal system
    with no such version, and a generic gloss of `cross-search` and of how "o KG
    é populado". This corpus's own abstention baseline already measured the model
    fabricating on 17.4% of verified negatives, with citations attached. A
    closed-book filter is only valid where the model abstains when it does not
    know, and here it does not. So the pool decides, and the closed-book answer is
    reported beside it for the reader to weigh.
    """
    if r["closed_book"].startswith("__ERR__"):
        return "closed_book_error"
    if r["pool_size"] == 0:
        return "undecidable"
    return "gold" if r["n_hits"] > 0 else "negative"

print(f"\n{'query':7s} {'status v2':20s} {'pool':>5s} {'hits':>5s}  verdict")
print("\nclosed-book answers in full (the bad-question call rests on these):")
for r in sorted(res, key=lambda x: x["query_id"]):
    if not r["is_control"]:
        print(f"  Q{r['query_id']:<4d} {r['closed_book'][:150]!r}")
print()
for r in sorted(res, key=lambda x: x["query_id"]):
    if r["is_control"]:
        continue
    cb = r["closed_book"].upper()
    if verdict(r) == "gold":
        v = f"GOLD BUILDABLE from {r['hits'][0]['source_file'][:38]}"
    elif r["pool_size"] == 0:
        v = "UNDECIDABLE (empty pool — not the same as no source)"
    else:
        v = f"NEGATIVE (none of {r['pool_size']} candidates answers it)"
    cbflag = "" if ("NAO SEI" in r["closed_book"].upper()
                    or "NÃO SEI" in r["closed_book"].upper()) else "  [closed-book answered: weigh it]"
    v += cbflag
    print(f"Q{r['query_id']:<6d} {str(r['status_v2'])[:20]:20s} {r['pool_size']:5d} "
          f"{r['n_hits']:5d}  {v}")

tg = [r for r in res if not r["is_control"]]
from collections import Counter
vc = Counter(verdict(r) for r in tg)
assert sum(vc.values()) == len(tg), "verdicts are not a partition"
print(f"\nof {len(tg)}, as a PARTITION: " +
      " · ".join(f"{k} {v}" for k, v in sorted(vc.items())))
gb = vc["gold"]
print(f"\nIf the {gb} join the ruler as REAL zero-hits, n goes 55 -> {55+gb} and the")
print(f"published strict 0.2428 becomes {0.2428*55/(55+gb):.4f}, pooled 0.5114 becomes "
      f"{0.5114*55/(55+gb):.4f}.")
