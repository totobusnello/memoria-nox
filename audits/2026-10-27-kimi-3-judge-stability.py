"""Kimi finding 3: is the judge stable on the SAME pair across independent calls?

The 21/21 verification tested provenance — whether the repaired file was one the
file-level pass had tested. It says nothing about whether the same (query, chunk)
would be labelled the same way twice. The batch controls do not close it either:
re-judging ACCEPTED positives is one-sided and selected, and there is no flip
rate anywhere.

So: re-judge a stratified sample of the same pairs, blind to the first label, and
report the flip rate. Stratified deliberately across the probability range,
because stability at the extremes says nothing about the borderline, and the
borderline is where a threshold at 0.5 does its work.
"""
import json, os, random, sys, time, urllib.error, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

W = sys.argv[1]
N_PER_BAND = int(os.environ.get("N_PER_BAND", "12"))
OKEY = os.environ["OPENAI_API_KEY"]
JMODEL = os.environ.get("JUDGE_MODEL", "gpt-6-luna")
import sqlite3
con = sqlite3.connect(f"file:{W}/eval.db?mode=ro", uri=True)

lab = json.load(open(f"{W}/judged-full.json"))
rows = [r for r in lab["rows"] if r.get("prob_contem_resposta") is not None]
BANDS = [(0.0, 0.1, "very low"), (0.1, 0.4, "low"), (0.4, 0.6, "BORDERLINE"),
         (0.6, 0.9, "high"), (0.9, 1.01, "very high")]
rng = random.Random(20261027)
pick = []
for lo, hi, name in BANDS:
    pool = [r for r in rows if lo <= r["prob_contem_resposta"] < hi]
    s = rng.sample(pool, min(N_PER_BAND, len(pool)))
    for r in s:
        pick.append({**r, "band": name})
    print(f"band {name:11s} [{lo},{hi}): pool {len(pool):3d} · sampled {len(s)}")
print(f"total to re-judge: {len(pick)}")

# PHASE 1 SERIAL: every chunk text read before any thread exists.
qtext = {}
for r in json.load(open(f"{W}/out.json"))["rows"]:
    qtext[r["query_id"]] = r.get("query")
for p in pick:
    t = con.execute("SELECT chunk_text FROM chunks WHERE id=?", (p["chunk_id"],)).fetchone()
    p["text"] = t[0] if t else ""
missing = sum(1 for p in pick if not p["text"])
print(f"chunk texts read serially · missing {missing}")

PRED = ("O TRECHO contem a resposta para esta PERGUNTA: {q}\n"
        "Nao basta tratar do mesmo assunto: tem de conter a resposta.")

def judge(q, txt):
    body = {"model": JMODEL, "input": f"TRECHO:\n---\n{txt[:6000]}\n---",
            "questions": [{"type": "predicate", "name": "relevante",
                           "instructions": PRED.format(q=q)}]}
    req = urllib.request.Request("https://api.openai.com/v1/decisions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {OKEY}"})
    for a in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            ans = {x["name"]: x for x in d.get("answers", [])}
            if "relevante" not in ans:
                raise RuntimeError("envelope without the predicate")
            return ans["relevante"].get("probability"), (d.get("usage") or {}).get("input_tokens", 0)
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:100]}"
            time.sleep(2 * (a + 1))
    raise RuntimeError(last)

out, toks = [], 0
def work(p):
    try:
        pr, t = judge(qtext.get(p["query_id"]) or "", p["text"])
        return {**{k: v for k, v in p.items() if k != "text"}, "p2": pr, "tok": t}
    except Exception as e:
        return {**{k: v for k, v in p.items() if k != "text"}, "erro": str(e)[:100]}
with ThreadPoolExecutor(max_workers=6) as ex:
    for r in ex.map(work, pick):
        out.append(r); toks += r.get("tok", 0)
json.dump(out, open(f"{W}/judge-stability.json", "w"), ensure_ascii=False)
ok = [r for r in out if "p2" in r]
print(f"\nre-judged {len(ok)} of {len(pick)} · {toks} tokens "
      f"(~US$ {toks/1e6*0.10:.4f})")

THR = 0.5
flips = [r for r in ok if (r["prob_contem_resposta"] > THR) != (r["p2"] > THR)]
print(f"\nLABEL FLIPS at p>{THR}: {len(flips)} of {len(ok)} = {len(flips)/len(ok):.1%}")
print(f"{'band':12s} {'n':>3s} {'flips':>6s} {'mean |dp|':>10s}")
for lo, hi, name in BANDS:
    g = [r for r in ok if r["band"] == name]
    if not g:
        continue
    f = sum(1 for r in g if (r["prob_contem_resposta"] > THR) != (r["p2"] > THR))
    md = sum(abs(r["p2"] - r["prob_contem_resposta"]) for r in g) / len(g)
    print(f"{name:12s} {len(g):3d} {f:6d} {md:10.3f}")
for r in flips[:8]:
    print(f"  Q{r['query_id']:<4d} chunk {r['chunk_id']:<8d} {r['band']:11s} "
          f"{r['prob_contem_resposta']:.2f} -> {r['p2']:.2f}")
print(f"\n⇒ the 21/21 provenance check is silent on this; the flip rate is the "
      f"number it could not give.")
