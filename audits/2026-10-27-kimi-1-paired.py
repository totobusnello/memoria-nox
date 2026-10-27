"""Kimi finding 1: is the ceiling drop attributable to judging coverage?

Kimi is right that the v2 -> v3 contrast confounds four things at once (queries
55->57, gold 95->85, 27 repaired, Q52 added) and does not isolate coverage. But
the controlled contrast he asks for already exists in this repo and I did not use
it: on 2026-10-26, eval/judge-relevance.py labelled the FULL top-10 of the
UNCHANGED v2 — same rankings, same gold, same 55 queries. Only the labelling
coverage differs.

So the isolation is: v2 ceiling under partial labels vs v2 ceiling under full
labels. Anything left over is gold + composition.
"""
import json, math, sys
from collections import Counter

V2 = "/root/medicoes/2026-10-22-gold/eval-result.json"
V2LAB = "/root/medicoes/2026-10-26-judge/canonical-full.json"
K, THR = 10, 0.5

d2 = json.load(open(V2))
rows2 = [r for r in d2["rows"] if r.get("ndcg") is not None]
print(f"v2 scoring artifact: {len(rows2)} scored queries "
      f"(summary strict {d2['summary'].get('ndcg_at_10')})")

lab = json.load(open(V2LAB))
lr = lab["rows"] if isinstance(lab, dict) and "rows" in lab else lab
assert isinstance(lr, list), f"unexpected label shape: {type(lab)}"
field = next((f for f in ("prob_contem_resposta", "relevante_prob", "prob")
              if f in lr[0]), None)
assert field, f"no probability field in {sorted(lr[0])}"
P = {(int(x["query_id"]), int(x["chunk_id"])): x[field]
     for x in lr if x.get(field) is not None}
print(f"v2 canonical labels: {len(P)} pairs (field `{field}`)")

tot = jud = 0
for r in rows2:
    for c in r["ranked"][:K]:
        tot += 1
        jud += (r["query_id"], c) in P
print(f"judged fraction of v2's top-10 under these labels: {jud}/{tot} = {jud/tot:.1%}")

def dcg(x):
    return sum(v / math.log2(i + 2) for i, v in enumerate(x))

def pooled(rows, Pd):
    vals = []
    for r in rows:
        q, gold = r["query_id"], set(r["gold_ids"])
        relset = gold | {c for (qq, c), v in Pd.items() if qq == q and v > THR}
        rels = [1 if c in relset else 0 for c in r["ranked"][:K]]
        ideal = min(len(relset), K)
        if ideal > 0:
            vals.append(dcg(rels) / dcg([1] * ideal))
    return sum(vals) / len(vals), len(vals)

p_full, n = pooled(rows2, P)
print(f"\n--- THE ISOLATED CONTRAST (same rankings, same gold, same {n} queries) ---")
print(f"v2 ceiling, PARTIAL labels (published 2026-10-22): 0.5114")
print(f"v2 ceiling, FULL labels    (this computation)    : {p_full:.4f}")
print(f"  attributable to judging coverage alone: {p_full-0.5114:+.4f}")
print(f"\nv3 ceiling, full labels: 0.4394")
print(f"  residual, i.e. gold + query composition: {0.4394-p_full:+.4f}")
print(f"\n⇒ coverage accounts for {abs(p_full-0.5114)/abs(0.4394-0.5114)*100:.0f}% "
      f"of the total ceiling drop of {0.4394-0.5114:+.4f};")
print(f"  the rest is the gold repair and the two added queries.")
