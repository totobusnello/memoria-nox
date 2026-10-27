"""Answer the same 99 questions from naive RAG over the raw transcript, so the
52.3% gets a ceiling instead of only a floor.

Four new arms, because two choices are not measurements and both have to be
shown:

  retriever  BM25 (the system's layer 1, deterministic, free)
             dense (gemini-embedding-001 3072d, the system's layer 2)
  budget     iso -- k = ceil(memory_chars / 2000), so the retrieved context is
                    the SAME SIZE as the memory units arm B received. This is
                    the comparison the net-value question actually asks: what
                    does the representation buy at equal context cost.
             k10 -- a flat top-10 (about 20k chars), the budget a RAG system
                    would spend without reference to the memory's size.

Arm B is NOT re-run. The judge was shown to be deterministic on this corpus on
2026-10-26 (540 pairs, zero label changes, max |delta p| 0.000), so re-running
it would spend money to reproduce a stored number.

THE CONTROL THAT MATTERS. For every arm, whether the verbatim citation the
question was generated from appears in the retrieved chunks. Without it, a low
score cannot be told apart from a retriever that never found the evidence, and
the whole arm would be a fact about BM25 rather than about naive RAG. Reported
as retrieval recall beside every accuracy.
"""
import json, math, os, re, time, unicodedata, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

BASE = "/root/medicoes/2026-10-26-memory-tax"
IDX = json.load(open(f"{BASE}/rag-index.json"))
JUD = json.load(open(f"{BASE}/replay-judged.json"))
ANS = {(a["uuid"], a["question"]): a
       for a in json.load(open(f"{BASE}/replay-answers.json"))}
OUT = f"{BASE}/rag-answers.json"
GKEY = os.environ["GEMINI_API_KEY"]
GMODEL = "gemini-2.5-flash-lite"
EMODEL = IDX["model"]
WORKERS = int(os.environ.get("WORKERS", "6"))
SMOKE = int(os.environ.get("SMOKE_N", "0"))

# verbatim from 2026-10-26-replay-answer.py
ANSWER_SYSTEM = """Você responde perguntas usando APENAS o material fornecido.

Regras:
- Se o material contém a resposta, responda em no máximo 25 palavras.
- Se o material NÃO contém a resposta, responda exatamente: NAO SEI
- Nunca use conhecimento próprio. Nunca especule. Nunca complete lacuna.
- Se o material trouxer duas informações conflitantes, responda com a que o
  material indicar como final e diga que houve mudança. Se não houver como
  saber qual é a final, responda as duas e diga que o material não resolve."""

# verbatim from eval/run-abstention.mjs, via 2026-10-26-replay-answer.py
CANON = "i have no memory matches for this question"
def abstained(t):
    s = (t or "").lower()
    return (CANON in s or "nao sei" in s or "não sei" in s or "não tenho" in s
            or "nao tenho" in s or "não há informação" in s or "nao ha informacao" in s)

GURL = (f"https://generativelanguage.googleapis.com/v1beta/models/{GMODEL}"
        f":generateContent?key={GKEY}")
EURL = (f"https://generativelanguage.googleapis.com/v1beta/models/{EMODEL}"
        f":embedContent?key={GKEY}")

def post(url, body, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    last = None
    for a in range(5):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:160]}"
            time.sleep(2 * (a + 1))
    raise RuntimeError(last)

def answer(material, question):
    d = post(GURL, {
        "systemInstruction": {"parts": [{"text": ANSWER_SYSTEM}]},
        "contents": [{"parts": [{"text": f"MATERIAL:\n{material}\n\nPERGUNTA: {question}"}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 200}})
    c = (d.get("candidates") or [{}])[0]
    txt = "".join(p.get("text", "") for p in (c.get("content") or {}).get("parts") or [])
    return txt.strip(), (d.get("usageMetadata") or {}).get("promptTokenCount", 0)

def embed_query(q):
    d = post(EURL, {"model": f"models/{EMODEL}",
                    "content": {"parts": [{"text": q}]},
                    "taskType": "RETRIEVAL_QUERY"})
    return d["embedding"]["values"]

# ---- BM25 per session
WORD = re.compile(r"\w+", re.U)
def tok(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return WORD.findall(s)

class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.toks = [tok(d) for d in docs]
        self.len = [len(t) for t in self.toks]
        self.avg = sum(self.len) / max(len(self.len), 1)
        self.tf = [Counter(t) for t in self.toks]
        df = Counter()
        for t in self.tf:
            df.update(t.keys())
        n = len(docs)
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}
    def scores(self, q):
        qt = tok(q)
        out = []
        for i, tf in enumerate(self.tf):
            s = 0.0
            for w in qt:
                f = tf.get(w, 0)
                if not f:
                    continue
                s += self.idf.get(w, 0) * f * (self.k1 + 1) / (
                    f + self.k1 * (1 - self.b + self.b * self.len[i] / max(self.avg, 1e-9)))
            out.append(s)
        return out

def cosine(a, b):
    num = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(x * x for x in b)) or 1e-9
    return num / (na * nb)

sess = IDX["sessions"]
bm = {u: BM25(v["chunks"]) for u, v in sess.items()}
print(f"BM25 built for {len(bm)} sessions", flush=True)

def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip().lower()

tasks = JUD[:SMOKE] if SMOKE else JUD
print(f"pairs to answer: {len(tasks)} x 4 arms", flush=True)

def do(j):
    u, q = j["uuid"], j["question"]
    v = sess[u]
    chunks = v["chunks"]
    cites = [c for c in (ANS.get((u, q), {}).get("citations") or []) if c]
    k_iso = max(1, math.ceil((j.get("memory_chars") or 2000) / IDX["chunk_size"]))
    out = {k: j[k] for k in ("uuid", "stratum", "scope", "category", "question",
                             "answer", "span_chars", "memory_units", "memory_chars")}
    out["k_iso"] = k_iso
    out["n_chunks"] = len(chunks)
    try:
        qv = embed_query(q)
    except Exception as e:
        out["erro"] = f"embed_query: {str(e)[:120]}"
        return out
    bs = bm[u].scores(q)
    ds = [cosine(qv, vec) for vec in v["vecs"]]
    order = {"bm25": sorted(range(len(chunks)), key=lambda i: -bs[i]),
             "dense": sorted(range(len(chunks)), key=lambda i: -ds[i])}
    for ret in ("bm25", "dense"):
        for blab, k in (("iso", k_iso), ("k10", 10)):
            if blab == "iso":
                # EQUAL BUDGET, not equal k. The first smoke gave the retrieval
                # arm 3.56x the memory arm's characters, because one 2000-char
                # chunk is larger than most memory units and k>=1 is a floor.
                # An arm with more context wins on the context, so chunks are
                # taken in score order only while they FIT, and the top one is
                # truncated when none does.
                budget = max(1, j.get("memory_chars") or 2000)
                pick, used = [], 0
                for i in order[ret]:
                    if used + len(chunks[i]) > budget:
                        continue
                    pick.append(i)
                    used += len(chunks[i])
                    if used >= budget * 0.95:
                        break
                if not pick:
                    pick = order[ret][:1]
                    mat = chunks[pick[0]][:budget]
                else:
                    mat = "\n\n---\n\n".join(chunks[i] for i in pick)
            else:
                pick = order[ret][:k]
                mat = "\n\n---\n\n".join(chunks[i] for i in pick)
            # control: did the retriever actually bring the evidence?
            got = any(norm(c) in norm(mat) for c in cites) if cites else None
            arm = f"{ret}_{blab}"
            try:
                txt, toks = answer(mat, q)
            except Exception as e:
                out[f"{arm}_erro"] = str(e)[:120]
                continue
            out[f"{arm}_text"] = txt
            out[f"{arm}_abstained"] = abstained(txt)
            out[f"{arm}_recall"] = got
            out[f"{arm}_chars"] = len(mat)
            out[f"{arm}_tokens"] = toks
    return out

res, t0 = [], time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for i, r in enumerate(ex.map(do, tasks), 1):
        res.append(r)
        if i % 10 == 0 or i == len(tasks):
            print(f"  {i}/{len(tasks)}  {time.time()-t0:.0f}s", flush=True)
json.dump(res, open(OUT, "w"), ensure_ascii=False)

toks = sum(r.get(f"{a}_tokens", 0) for r in res
           for a in ("bm25_iso", "bm25_k10", "dense_iso", "dense_k10"))
print(f"\n{len(res)} pairs · {toks} input tokens (~US$ {toks/1e6*0.10:.4f}) "
      f"· {time.time()-t0:.0f}s")

print("\nCONTROL · budget: retrieved chars against the memory units' chars")
for a in ("bm25_iso", "dense_iso"):
    rr = [r for r in res if r.get(f"{a}_chars")]
    if rr:
        ratio = sum(r[f"{a}_chars"] for r in rr) / sum(r["memory_chars"] for r in rr)
        over = [r["uuid"][:8] for r in rr if r[f"{a}_chars"] > r["memory_chars"]]
        print(f"  {a:10s} retrieved/memory = {ratio:.2f} · arms over budget: {len(over)}")
        # Tolerance covers the "\n\n---\n\n" separators only: measured on the
        # full run, 2 of 99 pairs exceeded the budget, by 4 and 6 characters,
        # and the aggregate ratio came out at 0.954. Formatting overhead is not
        # evidence. Anything larger means a chunk was admitted that did not fit,
        # and then the arm's score is the budget's.
        worst = max((r[f"{a}_chars"] - r["memory_chars"] for r in over), default=0)
        assert ratio <= 1.02 and worst <= 64, (
            f"{a} received more context than arm B did (worst +{worst} chars) -- "
            f"its score would be the budget's")
for a in ("bm25_k10", "dense_k10"):
    rr = [r for r in res if r.get(f"{a}_chars")]
    if rr:
        print(f"  {a:10s} mean retrieved chars = "
              f"{sum(r[f'{a}_chars'] for r in rr)/len(rr):.0f}")

print("\nCONTROL · retrieval recall of the evidence (verbatim citation present)")
for a in ("bm25_iso", "bm25_k10", "dense_iso", "dense_k10"):
    rr = [r for r in res if r.get(f"{a}_recall") is not None]
    if rr:
        print(f"  {a:10s} {sum(1 for r in rr if r[f'{a}_recall'])}/{len(rr)} = "
              f"{sum(1 for r in rr if r[f'{a}_recall'])/len(rr)*100:.1f}%")

print("\nabstention per arm (pre-judge)")
for a in ("bm25_iso", "bm25_k10", "dense_iso", "dense_k10"):
    rr = [r for r in res if f"{a}_abstained" in r]
    if rr:
        print(f"  {a:10s} silent {sum(1 for r in rr if r[f'{a}_abstained'])}/{len(rr)}")
