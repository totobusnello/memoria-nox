"""nDCG for ruler v3 under three arms, with the ideal built the SAME way.

The three arms answer different questions and the published pair quotes two of
them, so all three are printed with what each can and cannot see:

  strict   relevant = in the pre-registered gold. ideal = |gold| capped at K.
           An unjudged result counts as a miss, which is why it is the lower bound.
  pooled   relevant = in the gold OR judged relevant. ideal = |gold union judged
           relevants| capped at K. Upper bound.
  bounded  relevant = judged relevant INSIDE the ranking; ideal = |relevants
           inside the ranking|. ⚠️ It cannot see a relevant document the system
           failed to retrieve, so it measures ORDERING, not ordering plus recall.
           Printed for continuity with 2026-10-26, never as the headline.

CONTROL, and the script exits 1 without it: the strict arm must reproduce the
0.2567 already measured by run-gold-eval.mjs. A recomputation that cannot
reproduce the number it extends is reading different data.

The threshold is an input, not a constant — on v2 p>0.3/0.5/0.7 gave
0.5085/0.4764/0.4406 — so every arm is printed at all three and whatever gets
published says which one it used.

And the JUDGED FRACTION of the top-10 is printed BEFORE any metric: the first
scoring run reported 0.2428 with 9.1% of the top-10 ever judged, and a metric
over mostly-unjudged results is not a measurement of the system.
"""
import json, math, sys
from collections import defaultdict

SCORE, JUDGED, EXPECT_STRICT = sys.argv[1], sys.argv[2], float(sys.argv[3])
K = 10

d = json.load(open(SCORE))
rows = [r for r in d["rows"] if r.get("ndcg") is not None]
lab = json.load(open(JUDGED))
# The label file from eval/judge-relevance.py is {"meta", "rows"} and the
# probability field is `prob_contem_resposta`. Guessing at "pairs" with a
# fallback to the dict itself iterated its KEYS, i.e. strings — a fallback that
# turns a wrong field name into a type error two frames away. Read the shape.
assert isinstance(lab, dict) and "rows" in lab, f"unexpected label file: {list(lab)[:6]}"
P = {}
for row in lab["rows"]:
    pr = row.get("prob_contem_resposta")
    if pr is not None:
        P[(int(row["query_id"]), int(row["chunk_id"]))] = pr
assert P, "no probabilities parsed — the field name changed"

def dcg(rels):
    return sum(r / math.log2(i + 2) for i, r in enumerate(rels))

# judged fraction FIRST
tot = jud = 0
for r in rows:
    for cid in r["ranked"][:K]:
        tot += 1
        jud += (r["query_id"], cid) in P
print(f"judged fraction of the top-{K}: {jud}/{tot} = {jud/tot:.1%}"
      f"  (the first v2 run had 9.1%)")
print(f"labels available: {len(P)} pairs · {sum(1 for v in P.values() if v > 0.5)} "
      f"relevant at p>0.5")

def arms(thresh):
    out = {}
    for name in ("strict", "pooled", "bounded"):
        vals = []
        for r in rows:
            q, gold = r["query_id"], set(r["gold_ids"])
            ranked = r["ranked"][:K]
            jrel = {cid for cid in ranked if P.get((q, cid), 0) > thresh}
            if name == "strict":
                rels = [1 if c in gold else 0 for c in ranked]
                ideal = min(len(gold), K)
            elif name == "pooled":
                relset = gold | {c for (qq, c), v in P.items() if qq == q and v > thresh}
                rels = [1 if c in relset else 0 for c in ranked]
                ideal = min(len(relset), K)
            else:
                relset = gold | jrel
                rels = [1 if c in relset else 0 for c in ranked]
                ideal = min(len(relset & set(ranked)), K)
            if ideal <= 0:
                continue
            vals.append(dcg(rels) / dcg([1] * ideal))
        out[name] = sum(vals) / len(vals)
    return out

base = arms(0.5)
print(f"\nCONTROL strict={base['strict']:.4f} vs run-gold-eval {EXPECT_STRICT:.4f} "
      f"-> {'PASS' if abs(base['strict']-EXPECT_STRICT) < 0.002 else 'FAIL'}")
if abs(base["strict"] - EXPECT_STRICT) >= 0.002:
    print("  the recomputation is reading different data; no number below is usable")
    sys.exit(1)

print(f"\n{'threshold':10s} {'strict':>8s} {'pooled':>8s} {'bounded':>9s}")
for t in (0.3, 0.5, 0.7):
    a = arms(t)
    print(f"  p>{t:<6.1f} {a['strict']:8.4f} {a['pooled']:8.4f} {a['bounded']:9.4f}")

a = arms(0.5)
print(f"\nv3 at the registered threshold p>0.5:")
print(f"  honest interval [{a['strict']:.4f} · {a['pooled']:.4f}]")
print(f"  v2 was          [0.2428 · 0.5114]")
print(f"  bounded {a['bounded']:.4f} — ORDERING only, not comparable to the two above")

zh = sum(1 for r in rows if not (set(r['ranked'][:K]) & set(r['gold_ids'])))
zp = sum(1 for r in rows if not (set(r['ranked'][:K]) &
        (set(r['gold_ids']) | {c for (q, c), v in P.items()
                               if q == r['query_id'] and v > 0.5})))
print(f"\nzero-hit: strict {zh}/{len(rows)} = {zh/len(rows):.1%} · "
      f"pooled {zp}/{len(rows)} = {zp/len(rows):.1%}")
