"""Does the RECORDED gold answer the RECORDED question? All 95 entries.

Why. On 2026-10-27 the positive control of the oracle pass failed on Q99 — gold
anchor "229 chunks = ~52k tokens excede o limite do Groq" against the question
"qual o limite máximo de chunks armazenáveis". Diagnosis showed the gold chunk at
ranks 5 and 8 of the pool, so recall was fine: the judge saw it and rejected it,
correctly, because that is a per-call API limit and not a storage capacity. Q99
is one of the 55 ACCEPTED queries producing the published nDCG interval. And on
2026-10-26 a second judge confirmed only 19 of 30 pre-registered gold pairs.

So the question is how many more there are. This judges every gold entry against
its own query, with the bounded judge (Decisions API, no free-text field, so the
prose-contradicts-the-field defect cannot occur).

THREE CONTROLS, because a rejection rate on its own is a fact about the judge:

  positive  the 2 gold entries BUILT today from an oracle pass (Q108, Q72) were
            accepted at p=1.00 by this same judge on this same predicate. They
            must come back accepted; if they do not, the judge drifted.
  negative  each query is also paired with a RANDOM chunk from the corpus. The
            rejection rate there is the judge's floor — a judge that rejects
            everything scores high on the real pairs for the wrong reason.
  anchor    the judged text is the CHUNK the anchor resolves to, not the anchor
            string, because the ruler scores whole chunks. Judging the 160-char
            anchor would measure the anchor's wording, not the gold.

Read-only; the resolver runs the same behavioural classification shipped today.
"""
import json, os, random, re, sqlite3, sys, time, unicodedata, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

DB = "file:/root/.openclaw/workspace/tools/nox-mem/nox-mem.db?mode=ro"
GOLD = "/root/medicoes/golden-queries-v2.jsonl"
OUT = "/root/medicoes/gold-audit-2026-10-27.json"
OKEY = os.environ["OPENAI_API_KEY"]
JMODEL = os.environ.get("JUDGE_MODEL", "gpt-6-luna")
WORKERS = int(os.environ.get("WORKERS", "8"))
CUT = 6000
SEED = 20261027
SMOKE = int(os.environ.get("SMOKE_N", "0"))

con = sqlite3.connect(DB, uri=True)

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()

rows = [json.loads(l) for l in open(GOLD, encoding="utf-8") if l.strip()]
accepted = [r for r in rows if r.get("status") == "accepted"]
print(f"queries accepted: {len(accepted)} · gold entries: "
      f"{sum(len(r['gold']) for r in accepted)}")

# ---- PHASE 1, SERIAL: resolve every anchor to its chunk text.
pairs = []
unresolved = []
for r in accepted:
    for g in r["gold"]:
        needle = norm(g["anchor"])[:160]
        hits = [(cid, sec, txt) for (cid, sec, txt) in con.execute(
                    "SELECT id, section, chunk_text FROM chunks WHERE source_file = ?",
                    (g["source_file"],)).fetchall()
                if needle and needle in norm(txt)]
        if not hits:
            unresolved.append((r["query_id"], g["source_file"]))
            continue
        # structural ambiguity: judge the `compiled` half, which carries the truth
        pick = hits[0]
        if len(hits) == 2 and {h[1] for h in hits} == {"frontmatter", "compiled"}:
            pick = next(h for h in hits if h[1] == "compiled")
        pairs.append({"query_id": r["query_id"], "query": r["query"],
                      "category": r.get("category"), "source_file": g["source_file"],
                      "chunk_id": pick[0], "section": pick[1], "text": pick[2],
                      "anchor": g["anchor"][:120], "kind": "gold"})
print(f"resolved {len(pairs)} · unresolved {len(unresolved)} {unresolved[:3]}")

# ---- negative control: each query against a random chunk
rng = random.Random(SEED)
allids = [i for (i,) in con.execute(
    "SELECT id FROM chunks ORDER BY id").fetchall()]
seen = set()
for p in list(pairs):
    if p["query_id"] in seen:
        continue
    seen.add(p["query_id"])
    while True:
        cid = rng.choice(allids)
        if cid != p["chunk_id"]:
            break
    txt = con.execute("SELECT chunk_text, source_file FROM chunks WHERE id = ?",
                      (cid,)).fetchone()
    pairs.append({"query_id": p["query_id"], "query": p["query"],
                  "category": p.get("category"), "source_file": txt[1],
                  "chunk_id": cid, "section": None, "text": txt[0],
                  "anchor": None, "kind": "random"})

# ---- positive control: the two gold entries built today
POS = [(108, "memory/entities/systems/nox-mem.md",
        "**2026-04-27** — [milestone] Corpus tripled: 20.831"),
       (72, "events/mac/memoria-nox/cmem-memoria-nox-2026-03-20.md",
        "cross-search.ts (7-database search)")]
qtext = {r["query_id"]: r["query"] for r in rows}
for qid, sf, nd in POS:
    hits = [(cid, txt) for (cid, txt) in con.execute(
                "SELECT id, chunk_text FROM chunks WHERE source_file = ?", (sf,)).fetchall()
            if norm(nd) in norm(txt)]
    if hits:
        pairs.append({"query_id": qid, "query": qtext[qid], "category": "control",
                      "source_file": sf, "chunk_id": hits[0][0], "section": None,
                      "text": hits[0][1], "anchor": nd, "kind": "built_today"})
    else:
        print(f"! positive control for Q{qid} did not resolve — control unavailable")

from collections import Counter
print(f"pairs to judge: {len(pairs)} {dict(Counter(p['kind'] for p in pairs))}", flush=True)
if SMOKE:
    pairs = pairs[:SMOKE] + [p for p in pairs if p["kind"] != "gold"][:4]

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
def work(p):
    try:
        prob, t = judge(p["query"], p["text"])
        return {**{k: v for k, v in p.items() if k != "text"}, "responde": prob, "tok": t}
    except Exception as e:
        return {**{k: v for k, v in p.items() if k != "text"}, "erro": str(e)[:120]}
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for i, r in enumerate(ex.map(work, pairs), 1):
        res.append(r)
        toks += r.get("tok", 0)
        if i % 30 == 0 or i == len(pairs):
            print(f"  {i}/{len(pairs)}  {time.time()-t0:.0f}s", flush=True)
json.dump(res, open(OUT, "w"), ensure_ascii=False)
print(f"\n{len(res)} judged · {sum(1 for r in res if 'erro' in r)} errors · "
      f"{toks} tokens (~US$ {toks/1e6*0.10:.4f}) · {time.time()-t0:.0f}s")

THR = 0.5
def rate(kind):
    g = [r for r in res if r["kind"] == kind and "responde" in r]
    if not g:
        return None, 0
    return sum(1 for r in g if (r["responde"] or 0) > THR) / len(g), len(g)

print("\nCONTROLS")
pc, npc = rate("built_today")
nc, nnc = rate("random")
print(f"  positive (gold built today) accepted {pc*100 if pc is not None else 0:.1f}% "
      f"of {npc}  {'PASS' if pc and pc > 0.99 else 'CHECK'}")
print(f"  negative (random chunk)     accepted {nc*100:.1f}% of {nnc}  "
      f"{'PASS' if nc < 0.15 else 'FAIL — the judge accepts noise, nothing below is readable'}")
if nc >= 0.15:
    sys.exit(3)

gr, ng = rate("gold")
print(f"\nRECORDED GOLD: {gr*100:.1f}% accepted of {ng} entries "
      f"({int(gr*ng)} accepted, {ng-int(gr*ng)} rejected)")
print(f"  the judge's floor is {nc*100:.1f}%, so the signal is "
      f"{(gr-nc)*100:.1f} pp above noise")

byq = {}
for r in res:
    if r["kind"] != "gold" or "responde" not in r:
        continue
    byq.setdefault(r["query_id"], []).append((r["responde"] or 0) > THR)
allbad = [q for q, v in byq.items() if not any(v)]
print(f"\nqueries whose EVERY gold entry is rejected: {len(allbad)} of {len(byq)} "
      f"= {len(allbad)/len(byq)*100:.1f}%  -> {sorted(allbad)}")
print("  (these score 0 by construction in the strict arm, whatever the system returns)")

print(f"\nif those {len(allbad)} are invalid, the strict arm's n of 55 holds but "
      f"{len(allbad)} of its queries\n  are unanswerable by any system: "
      f"0.2428 is then computed over {55-len(allbad)} real queries plus "
      f"{len(allbad)} forced zeros.")
print(f"  excluding them: 0.2428 -> {0.2428*55/(55-len(allbad)):.4f} "
      f"(+{(55/(55-len(allbad))-1)*100:.1f}%)")

print("\nby category, share of gold entries rejected:")
cat = {}
for r in res:
    if r["kind"] != "gold" or "responde" not in r:
        continue
    c = cat.setdefault(r["category"] or "?", [0, 0])
    c[1] += 1
    if (r["responde"] or 0) <= THR:
        c[0] += 1
for c, (bad, tot) in sorted(cat.items(), key=lambda x: -x[1][0] / max(x[1][1], 1)):
    print(f"  {c:12s} {bad:3d}/{tot:3d} = {bad/tot*100:5.1f}%")
