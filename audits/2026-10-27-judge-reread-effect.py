"""What does a 20% label flip rate do to the ceiling I published?

The interval [0.2567 · 0.4394] was reported as honest. Its ceiling rests on
judge labels whose flip rate on repeated independent calls is 20.0% (12 of 60,
stratified). This substitutes the SECOND reading for the first on exactly those
60 pairs and recomputes, so the movement is measured rather than extrapolated —
and the 60 are 9.7% of the 620 labels, which bounds how much of the ceiling this
re-reading can touch.
"""
import json, math, sys

W = sys.argv[1]
d = json.load(open(f"{W}/out.json"))
rows = [r for r in d["rows"] if r.get("ndcg") is not None]
lab = json.load(open(f"{W}/judged-full.json"))
st = json.load(open(f"{W}/judge-stability-full.json"))
K, THR = 10, 0.5

P1 = {(int(x["query_id"]), int(x["chunk_id"])): x["prob_contem_resposta"]
      for x in lab["rows"] if x.get("prob_contem_resposta") is not None}
P2 = dict(P1)
rejudged = 0
for r in st:
    if "p2" in r:
        P2[(int(r["query_id"]), int(r["chunk_id"]))] = r["p2"]
        rejudged += 1
print(f"labels total {len(P1)} · re-read {rejudged} = {rejudged/len(P1):.1%}")

def dcg(x):
    return sum(v / math.log2(i + 2) for i, v in enumerate(x))

def pooled(Pd, thresh=THR):
    vals = []
    for r in rows:
        q, gold = r["query_id"], set(r["gold_ids"])
        relset = gold | {c for (qq, c), v in Pd.items() if qq == q and v > thresh}
        rels = [1 if c in relset else 0 for c in r["ranked"][:K]]
        ideal = min(len(relset), K)
        if ideal > 0:
            vals.append(dcg(rels) / dcg([1] * ideal))
    return sum(vals) / len(vals)

a, b = pooled(P1), pooled(P2)
print(f"\npooled, first reading : {a:.4f}   <- the published ceiling")
print(f"pooled, second reading: {b:.4f}   (delta {b-a:+.4f}, {(b/a-1)*100:+.1f}%)")
print(f"  {rejudged/len(P1):.1%} of the labels re-read — this is the CENSUS, not a sample")

# how many queries changed at all
def per_query(Pd):
    out = {}
    for r in rows:
        q, gold = r["query_id"], set(r["gold_ids"])
        relset = gold | {c for (qq, c), v in Pd.items() if qq == q and v > THR}
        rels = [1 if c in relset else 0 for c in r["ranked"][:K]]
        ideal = min(len(relset), K)
        if ideal > 0:
            out[q] = dcg(rels) / dcg([1] * ideal)
    return out
q1, q2 = per_query(P1), per_query(P2)
moved = {q: (q1[q], q2[q]) for q in q1 if abs(q1[q] - q2[q]) > 1e-9}
print(f"\nqueries whose pooled nDCG changed: {len(moved)} of {len(q1)}")
for q, (x, y) in sorted(moved.items(), key=lambda kv: -abs(kv[1][0] - kv[1][1]))[:6]:
    print(f"  Q{q:<4d} {x:.4f} -> {y:.4f} ({y-x:+.4f})")

# bound: if the flip rate applies uniformly, what is the plausible spread?
flips = sum(1 for r in st if "p2" in r
            and (r["prob_contem_resposta"] > THR) != (r["p2"] > THR))
print(f"\nflip rate, FULL re-read: {flips}/{rejudged} = {flips/rejudged:.1%}")
print(f"  (the stratified sample of 60 gave 20.0% — it over-represented the")
print(f"   unstable bands, which hold only 54 of 620 pairs)")
print(f"\n⇒ the ceiling under a second independent reading of EVERY label:")
print(f"   {a:.4f} -> {b:.4f}, i.e. {abs(b-a):.4f} of labelling noise.")
lo, hi = min(a, b), max(a, b)
print(f"   The defensible statement is the ceiling in [{lo:.3f} .. {hi:.3f}],")
print(f"   so [0.26 . 0.44] stands and the fourth decimal does not.")
