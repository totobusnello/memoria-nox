#!/usr/bin/env python3
"""Analysis for 2026-11-03-one-ranking-two-golds.sh. Reads <workdir> on the host; no network, no DB writes.

(a) duplication per query — on the official K=10 ranking:
    dup slots  = slots whose normalised text equals an EARLIER slot's (the copy, not the first)
    nDCG_dedup = nDCG@10 after removing those copies and refilling from the K=20 run, skipping copies
                 again; gold credit counts once per distinct text (a copy of a gold chunk is not a second hit)
    reported per query, and the aggregate shift with its concentration
(b) one ranking, two golds — strict nDCG@10 (the harness's formula) of the SAME K=10 lists under the v2
    gold and the v3 gold, on the queries both golds score. Any difference is the gold.

Controls, printed and required:
  - the K=20 run's top-10 must equal the K=10 run's on most queries (it is used only for refill);
    the agreement is reported, and refill is not used for a query whose top-10 differs
  - recomputing the v3 strict nDCG from `ranked` + gold must reproduce the harness's own per-row nDCG
"""
import json
import math
import re
import sys
from collections import Counter

W = sys.argv[1]
K = 10


def dcg(rels):
    return sum(r / math.log2(i + 2) for i, r in enumerate(rels))


def ndcg(ranked, want, k=K):
    rels = [1 if x in want else 0 for x in ranked[:k]]
    ideal = [1] * min(len(want), k)
    return dcg(rels) / dcg(ideal) if ideal else None


def norm(t):
    return re.sub(r"\s+", " ", (t or "")).strip().lower()


o10 = {str(r["query_id"]): r for r in json.load(open(f"{W}/out-k10.json"))["rows"] if r.get("ranked") is not None}
o20 = {str(r["query_id"]): r for r in json.load(open(f"{W}/out-k20.json"))["rows"] if r.get("ranked") is not None}
texts = json.load(open(f"{W}/texts.json"))
g2 = {k: set(v) for k, v in json.load(open(f"{W}/map-v2.json")).items()}
g3 = {k: set(v) for k, v in json.load(open(f"{W}/map-v3.json")).items()}
txt = {int(k): norm(v["text"]) for k, v in texts.items()}

# control: harness reproduction
mism = [q for q, r in o10.items() if r.get("ndcg") is not None
        and abs(ndcg(r["ranked"], g3.get(q, set())) - r["ndcg"]) > 1e-3]
print(f"control · recomputed v3 strict nDCG matches the harness on {len(o10) - len(mism)}/{len(o10)} rows"
      + (f" — MISMATCH {mism[:5]}" if mism else ""))
same_top = {q for q in o10 if q in o20 and o20[q]["ranked"][:K] == o10[q]["ranked"][:K]}
print(f"control · K=20 top-10 equals K=10 top-10 on {len(same_top)}/{len(o10)} queries "
      f"(refill used only on those)")

# (a) duplication
print("\n(a) DUPLICATION PER QUERY (official K=10 ranking, v3 gold)")
per = []
for q, r in sorted(o10.items(), key=lambda x: int(x[0])):
    want = g3.get(q, set())
    if not want or r.get("ndcg") is None:
        continue
    seen, dup = set(), 0
    for x in r["ranked"][:K]:
        t = txt.get(x)
        if t is not None and t in seen:
            dup += 1
        seen.add(t)
    base = ndcg(r["ranked"], want)
    if q in same_top:
        pool, out, seen_t, want_t = o20[q]["ranked"], [], set(), {txt.get(w) for w in want}
        credited = set()
        rels = []
        for x in pool:
            t = txt.get(x)
            if t in seen_t:
                continue
            seen_t.add(t)
            hit = 1 if (x in want or t in want_t) and t not in credited else 0
            if hit:
                credited.add(t)
            rels.append(hit)
            if len(rels) == K:
                break
        distinct_gold = len({txt.get(w) for w in want})
        ideal = [1] * min(distinct_gold, K)
        dd = dcg(rels) / dcg(ideal) if ideal else None
    else:
        dd = None
    per.append((q, dup, base, dd, len(want), len({txt.get(w) for w in want})))
dups = Counter(p[1] for p in per)
print(f"   queries {len(per)} · duplicate slots per query: {dict(sorted(dups.items()))}")
print(f"   mean duplicate slots {sum(p[1] for p in per)/len(per):.2f} of 10 "
      f"(the corpus-wide arithmetic predicted ~0.19)")
heavy = [p for p in per if p[1] >= 3]
print(f"   queries with >= 3 duplicate slots: {len(heavy)}")
for q, d, b, dd, ng, ngd in sorted(per, key=lambda p: -p[1])[:8]:
    print(f"     Q{q:>4s} dup {d} · nDCG {b:.4f} -> dedup {('%.4f' % dd) if dd is not None else 'n/a':>6s} "
          f"· gold ids {ng} / distinct texts {ngd}")
both = [p for p in per if p[3] is not None]
if both:
    mb = sum(p[2] for p in both) / len(both)
    md = sum(p[3] for p in both) / len(both)
    moved = [p for p in both if abs(p[3] - p[2]) > 1e-9]
    print(f"   aggregate on the {len(both)} queries with a usable refill: {mb:.4f} -> {md:.4f} "
          f"({(md - mb):+.4f}, {(md / mb - 1) * 100 if mb else float('nan'):+.1f}%) · queries that move: {len(moved)}")
    if moved:
        share = sorted((abs(p[3] - p[2]) for p in moved), reverse=True)
        tot = sum(share)
        print(f"   concentration: the top 3 movers carry {sum(share[:3]) / tot * 100:.0f}% of the absolute shift")

# (b) one ranking, two golds
print("\n(b) ONE RANKING, TWO GOLDS (strict nDCG@10 on the same K=10 lists)")
common = sorted((q for q in o10 if q in g2 and q in g3 and o10[q].get("ndcg") is not None), key=int)
only2 = sorted(set(g2) - set(g3), key=int)
only3 = sorted(set(g3) - set(g2), key=int)
s2 = [ndcg(o10[q]["ranked"], g2[q]) for q in common]
s3 = [ndcg(o10[q]["ranked"], g3[q]) for q in common]
print(f"   queries scored by both golds: {len(common)} · only v2 {len(only2)} · only v3 {len(only3)}")
print(f"   v2 gold {sum(s2)/len(s2):.4f} · v3 gold {sum(s3)/len(s3):.4f} · difference "
      f"{(sum(s3) - sum(s2))/len(common):+.4f} — the gold, ranking held fixed")
chg = [(q, a, b) for q, a, b in zip(common, s2, s3) if abs(a - b) > 1e-9]
print(f"   queries whose score changes with the gold alone: {len(chg)} "
      f"(up {sum(1 for _, a, b in chg if b > a)}, down {sum(1 for _, a, b in chg if b < a)})")
same_gold = sum(1 for q in common if g2[q] == g3[q])
print(f"   queries whose resolved gold is identical in v2 and v3: {same_gold}")
all3 = [o10[q]["ndcg"] for q in o10 if q in g3 and o10[q].get("ndcg") is not None]
print(f"   today's v3 strict nDCG on all {len(all3)} scored queries: {sum(all3)/len(all3):.4f} "
      f"(27/10 published 0.2567 on the corpus of that day)")
