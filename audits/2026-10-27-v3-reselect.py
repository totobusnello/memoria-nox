"""v3 of the PT-BR ruler: re-select the CHUNK, not the span.

The correction that makes this the right fix. The 2026-10-27 audit said the
anchors "landed on a mention of the term". But what the judge judged was the
CHUNK, and Q51's chunk was the frontmatter tags line of the right file. So the
anchor did not pick the wrong span inside a chunk — it RESOLVED TO THE WRONG
CHUNK inside the right file. The repair is therefore re-selection, not re-cutting:
for each rejected gold entry, judge every chunk of its source_file and anchor on
one that answers. Cheaper, and it fixes what is actually broken.

CONTROLS ARE RECOMPUTED IN THIS BATCH, not inherited. The judge was calibrated an
hour ago (1.8% on random chunks, 100% on gold built today) and that is a fact
about that batch; this repository has measured the same data giving 0.700 /
0.833 / 0.913 under three readings of a verification predicate.

Read-only on the database (mode=ro). Writes only the proposal file.
"""
import json, os, random, re, sqlite3, sys, time, unicodedata, urllib.error, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

DB = "file:/root/.openclaw/workspace/tools/nox-mem/nox-mem.db?mode=ro"
GOLD = "/root/medicoes/golden-queries-v2.jsonl"
AUDIT = "/root/medicoes/gold-audit-2026-10-27.json"
OUT = "/root/medicoes/v3-reselect-2026-10-27.json"
OKEY = os.environ["OPENAI_API_KEY"]
JMODEL = os.environ.get("JUDGE_MODEL", "gpt-6-luna")
WORKERS = int(os.environ.get("WORKERS", "8"))
CUT, THR, SEED = 6000, 0.5, 20261027
ANCHOR_LEN = 200

con = sqlite3.connect(DB, uri=True)
rows = {r["query_id"]: r for r in
        (json.loads(l) for l in open(GOLD, encoding="utf-8") if l.strip())}
audit = json.load(open(AUDIT))

rejected = [r for r in audit
            if r["kind"] == "gold" and (r.get("responde") or 0) <= THR]
accepted = [r for r in audit
            if r["kind"] == "gold" and (r.get("responde") or 0) > THR]
print(f"rejected gold entries to repair: {len(rejected)} · accepted: {len(accepted)}")

# ---- PHASE 1, SERIAL: read every candidate chunk before any thread starts.
# A shared sqlite connection across threads raises, and on 2026-10-27 that
# exception was being swallowed into an empty pool — i.e. into the very answer
# being measured.
cands = []
for r in rejected:
    chunks = con.execute(
        "SELECT id, section, chunk_text FROM chunks WHERE source_file = ? ORDER BY id",
        (r["source_file"],)).fetchall()
    for cid, sec, txt in chunks:
        cands.append({"query_id": r["query_id"], "query": r["query"],
                      "category": r.get("category"), "source_file": r["source_file"],
                      "chunk_id": cid, "section": sec, "text": txt,
                      "old_chunk_id": r["chunk_id"], "kind": "candidate"})
print(f"candidate chunks read serially: {len(cands)} "
      f"({len(cands)/max(len(rejected),1):.1f} per rejected entry)")

# ---- controls, recomputed here
rng = random.Random(SEED)
allids = [i for (i,) in con.execute("SELECT id FROM chunks ORDER BY id")]
seen = set()
for r in rejected:
    if r["query_id"] in seen:
        continue
    seen.add(r["query_id"])
    cid = rng.choice(allids)
    txt, sf = con.execute(
        "SELECT chunk_text, source_file FROM chunks WHERE id = ?", (cid,)).fetchone()
    cands.append({"query_id": r["query_id"], "query": r["query"], "category": "ctl",
                  "source_file": sf, "chunk_id": cid, "section": None, "text": txt,
                  "old_chunk_id": None, "kind": "random"})
for r in rng.sample(accepted, min(12, len(accepted))):
    txt = con.execute("SELECT chunk_text FROM chunks WHERE id = ?",
                      (r["chunk_id"],)).fetchone()
    if txt:
        cands.append({"query_id": r["query_id"], "query": r["query"], "category": "ctl",
                      "source_file": r["source_file"], "chunk_id": r["chunk_id"],
                      "section": None, "text": txt[0], "old_chunk_id": r["chunk_id"],
                      "kind": "accepted_again"})
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
        prob, t = judge(c["query"], c["text"])
        return {**c, "responde": prob, "tok": t,
                "anchor": c["text"][:ANCHOR_LEN]}
    except Exception as e:
        return {**c, "erro": str(e)[:120]}
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for i, r in enumerate(ex.map(work, cands), 1):
        r.pop("text", None)
        res.append(r); toks += r.get("tok", 0)
        if i % 40 == 0 or i == len(cands):
            print(f"  {i}/{len(cands)}  {time.time()-t0:.0f}s", flush=True)
json.dump(res, open(OUT, "w"), ensure_ascii=False)
errs = sum(1 for r in res if "erro" in r)
print(f"\n{len(res)} judged · {errs} errors · {toks} tokens "
      f"(~US$ {toks/1e6*0.10:.4f}) · {time.time()-t0:.0f}s")

def rate(kind):
    g = [r for r in res if r["kind"] == kind and "responde" in r]
    return (sum(1 for r in g if (r["responde"] or 0) > THR) / len(g), len(g)) if g else (None, 0)

print("\nCONTROLS, recomputed in THIS batch")
nc, nn = rate("random")
pc, pn = rate("accepted_again")
print(f"  negative (random chunk)      {nc:.1%} of {nn}  "
      f"{'PASS' if nc < 0.15 else 'FAIL — the judge accepts noise'}")
print(f"  positive (accepted re-judged) {pc:.1%} of {pn}  "
      f"{'PASS' if pc > 0.85 else 'FAIL — the judge drifted since the audit'}")
if nc >= 0.15 or pc <= 0.85:
    sys.exit(3)

# ---- the repair
byq = {}
for r in res:
    if r["kind"] != "candidate" or "responde" not in r:
        continue
    byq.setdefault(r["query_id"], []).append(r)
repaired, unrepairable = {}, []
for qid, cs in byq.items():
    best = max(cs, key=lambda x: x["responde"] or 0)
    if (best["responde"] or 0) > THR:
        repaired.setdefault(qid, []).append(best)
    else:
        unrepairable.append((qid, cs[0]["source_file"], max(
            (c["responde"] or 0) for c in cs)))
print(f"\nREPAIR of the {len(rejected)} rejected entries, over {len(byq)} queries")
print(f"  repaired  : {sum(len(v) for v in repaired.values())} entries "
      f"in {len(repaired)} queries")
print(f"  unrepairable: {len(unrepairable)} — no chunk in the source_file answers")
for qid, sf, mx in sorted(unrepairable)[:10]:
    print(f"    Q{qid:<4d} {sf[:56]:56s} best p={mx:.2f}")

# did re-selection move the chunk, or confirm the old one?
moved = sum(1 for v in repaired.values() for b in v if b["chunk_id"] != b["old_chunk_id"])
print(f"\n  of the repaired, {moved} point at a DIFFERENT chunk of the same file "
      f"(re-selection, which is the whole point) and "
      f"{sum(len(v) for v in repaired.values())-moved} at the same one")

# which queries end up with NO valid gold at all
allq = {}
for r in audit:
    if r["kind"] == "gold":
        allq.setdefault(r["query_id"], []).append((r.get("responde") or 0) > THR)
dead_before = {q for q, v in allq.items() if not any(v)}
dead_after = {q for q in dead_before if q not in repaired}
print(f"\nqueries with no valid gold: {len(dead_before)} before -> "
      f"{len(dead_after)} after  (recovered {len(dead_before)-len(dead_after)})")
print(f"  still dead: {sorted(dead_after)}")
print(f"\nstrict nDCG, if the recovered queries become scorable again:")
print(f"  published 0.2428 over 55 · {len(dead_after)} unanswerable instead of "
      f"{len(dead_before)} ⇒ the forced-zero share falls from "
      f"{len(dead_before)/55:.1%} to {len(dead_after)/55:.1%}")
