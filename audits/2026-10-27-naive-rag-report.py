"""Final report: net value of memory against naive RAG, decomposed against the
see-once rule, with the damage predicate calibrated on the arm that cannot fail.

Reprints from the stored JSON. No API calls, no cost.
"""
import json, re, statistics
from collections import Counter

BASE = "/root/medicoes/2026-10-26-memory-tax"
OUT = json.load(open(f"{BASE}/rag-judged.json"))
DEC = {(r["uuid"], r["question"]): r["available"]
       for r in json.load(open(f"{BASE}/decomposed.json"))}
SEE = {r["uuid"]: r for r in json.load(open(f"{BASE}/see-once.json"))["rows"]}
IDX = json.load(open(f"{BASE}/rag-index.json"))["sessions"]
ARMS = ("b", "bm25_iso", "dense_iso", "bm25_k10", "dense_k10")
THR = 0.5

def hit(r, k):
    return ((r.get(k) or {}).get("contem") or 0) > THR
def contra(r, k):
    return ((r.get(k) or {}).get("contradiz") or 0) > THR

a_all = sum(1 for r in OUT if hit(r, "a")) / len(OUT)
print("=" * 78)
print(f"POPULATION {len(OUT)} judged pairs · arm A (oracle window) {a_all*100:.1f}%")
print("=" * 78)

print(f"\n{'':24s} {'n':>4s} {'correct':>8s} {'vs B':>8s} {'silent':>8s} {'contra':>8s}")
b_all = sum(1 for r in OUT if hit(r, "b")) / len(OUT)
for k in ARMS:
    g = [r for r in OUT if r.get(k)]
    v = sum(1 for r in g if hit(r, k)) / len(g)
    sil = sum(1 for r in g if r.get(f"{k}_abstained")
              or (r.get(k) or {}).get("nivel_probs", {}).get("nao_responde", 0) > 0.5) / len(g)
    d = "" if k == "b" else f"{(v-b_all)*100:+7.1f}"
    print(f"{k:24s} {len(g):4d} {v*100:7.1f}% {d:>8s} {sil*100:7.1f}% "
          f"{sum(1 for r in g if contra(r,k))/len(g)*100:7.1f}%")

print("\n" + "-" * 78)
print("DECOMPOSED against the see-once rule (session-distill.ts:141-144)")
print("-" * 78)
sub = [r for r in OUT if (r["uuid"], r["question"]) in DEC]
vis = [r for r in sub if DEC[(r["uuid"], r["question"])]]
aft = [r for r in sub if not DEC[(r["uuid"], r["question"])]]
print(f"placed {len(sub)} of {len(OUT)} · evidence visible to the builder {len(vis)} "
      f"· arrived after {len(aft)}")
print(f"\n{'':24s} {'ALL':>14s} {'VISIBLE':>14s} {'AFTER':>14s}")
for k in ("a",) + ARMS:
    def r_(g):
        gg = [x for x in g if x.get(k)]
        return f"{sum(1 for x in gg if hit(x,k))/len(gg)*100:5.1f}% (n={len(gg)})" if gg else "--"
    print(f"{k:24s} {r_(sub):>14s} {r_(vis):>14s} {r_(aft):>14s}")

print("\nnet value of memory, on the population the builder could actually serve:")
bv = sum(1 for r in vis if hit(r, "b")) / len(vis)
av = sum(1 for r in vis if hit(r, "a")) / len(vis)
for k in ("bm25_iso", "dense_iso"):
    g = [r for r in vis if r.get(k)]
    v = sum(1 for x in g if hit(x, k)) / len(g)
    print(f"  B {bv*100:.1f}% vs {k} {v*100:.1f}%  -> {(bv-v)*100:+.1f} pp  "
          f"(oracle {av*100:.1f}%, so memory tax {(av-bv)/av*100:.1f}% "
          f"and RAG tax {(av-v)/av*100:.1f}%)")

print("\n" + "-" * 78)
print("CALIBRATION of the damage predicate · arm A read the window the reference")
print("came from, so it CANNOT contradict it. Its rate is the false-positive floor.")
print("-" * 78)
floor = sum(1 for r in OUT if contra(r, "a")) / len(OUT)
print(f"  floor (arm A)            {floor*100:5.1f}%")
for k in ARMS:
    g = [r for r in OUT if r.get(k)]
    v = sum(1 for r in g if contra(r, k)) / len(g)
    verdict = "ABOVE the floor" if v > floor else "at or below the floor -> no evidence of damage"
    print(f"  {k:24s} {v*100:5.1f}%  {verdict}")
both = [r for r in OUT if hit(r, "a") and contra(r, "a")]
print(f"\n  and {len(both)} of {sum(1 for r in OUT if contra(r,'a'))} of arm A's flags carry "
      f"contem AND contradiz together: the predicates are not exclusive.")

print("\n" + "-" * 78)
print("BY CATEGORY on the visible population (the honest faithfulness cell)")
print("-" * 78)
print(f"{'category':12s} {'n':>4s} {'A':>7s} {'B':>7s} {'bm25_iso':>9s} {'dense_iso':>10s} "
      f"{'B tax':>7s}")
for cat in ("context", "decision", "lesson", "preference"):
    g = [r for r in vis if r["category"] == cat]
    if not g:
        continue
    a = sum(1 for r in g if hit(r, "a")) / len(g)
    b = sum(1 for r in g if hit(r, "b")) / len(g)
    q1 = sum(1 for r in g if hit(r, "bm25_iso")) / len(g)
    q2 = sum(1 for r in g if hit(r, "dense_iso")) / len(g)
    print(f"{cat:12s} {len(g):4d} {a*100:6.1f}% {b*100:6.1f}% {q1*100:8.1f}% {q2*100:9.1f}% "
          f"{((a-b)/a*100 if a else 0):6.1f}%")

print("\n" + "-" * 78)
print("WHERE THE RAG ARMS LOSE · retrieval recall, by final transcript size")
print("-" * 78)
size = {u: v["prose_chars"] for u, v in IDX.items()}
BANDS = [("<50k", 0, 50_000), ("50-200k", 50_000, 200_000), ("200k-1M", 200_000, 1 << 40)]
print(f"{'band':9s} {'n':>4s} " + " ".join(f"{a:>11s}" for a in ARMS[1:]))
for nm, lo, hi in BANDS:
    g = [r for r in OUT if lo <= size.get(r["uuid"], 0) < hi]
    if not g:
        continue
    cells = []
    for a in ARMS[1:]:
        rc = [r for r in g if r.get(f"{a}_recall") is not None]
        cells.append(f"{sum(1 for r in rc if r[f'{a}_recall'])/len(rc)*100:10.1f}%" if rc else "         --")
    print(f"{nm:9s} {len(g):4d} " + " ".join(cells))
print("\naccuracy in the same bands (correct answers, not recall):")
print(f"{'band':9s} {'n':>4s} {'A':>7s} " + " ".join(f"{a:>11s}" for a in ARMS))
for nm, lo, hi in BANDS:
    g = [r for r in OUT if lo <= size.get(r["uuid"], 0) < hi]
    if not g:
        continue
    cells = [f"{sum(1 for r in g if hit(r,'a'))/len(g)*100:6.1f}%"]
    for a in ARMS:
        gg = [r for r in g if r.get(a)]
        cells.append(f"{sum(1 for r in gg if hit(r,a))/len(gg)*100:10.1f}%" if gg else "         --")
    print(f"{nm:9s} {len(g):4d} " + " ".join(cells))
