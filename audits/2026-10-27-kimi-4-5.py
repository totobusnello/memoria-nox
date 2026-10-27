"""Kimi findings 4 and 5, both measurable for free.

FINDING 5 — `ambiguous_duplicate` needs an equivalence CONTRACT, not just bytes.
The resolver exempts the ambiguity; it does not follow that the SCORER credits
every id of the cluster. If it credits one arbitrary id, a system returning the
other byte-identical chunk is scored wrong for returning the same text, which
would be the 8-word citation check all over again. Measured here against the
actual resolved map and the actual rankings.

FINDING 4 — reproducing strict is a weak control over the NEW part. Strict needs
no LLM, so it is unchanged by definition when labels change; the novelty is the
pooled arm. The control Kimi asks for is a PERTURBATION: flip a label and require
the metric to move. Run here.
"""
import json, math, sys
from collections import Counter, defaultdict

W = sys.argv[1]
d = json.load(open(f"{W}/out.json"))
rows = [r for r in d["rows"] if r.get("ndcg") is not None]
rmap = json.load(open(f"{W}/resolved-map.json"))
res = json.load(open(f"{W}/resolve.json"))
lab = json.load(open(f"{W}/judged-full.json"))
P = {(int(x["query_id"]), int(x["chunk_id"])): x["prob_contem_resposta"]
     for x in lab["rows"] if x.get("prob_contem_resposta") is not None}
K = 10

print("=== FINDING 5: does the SCORER credit every id of a duplicate cluster?")
dup = [e for e in res["entries"] if e["state"] == "ambiguous_duplicate"]
print(f"entries the resolver marked ambiguous_duplicate: {len(dup)}")
for e in dup:
    q = str(e["query_id"])
    ids = e["resolved_ids"]
    credited = [i for i in ids if i in (rmap.get(q) or [])]
    print(f"  Q{e['query_id']}: resolver found {ids}, scorer credits {credited}")
    print(f"    -> {'ALL credited (contract holds)' if len(credited) == len(ids) else 'ONLY SOME CREDITED — the scorer can punish the same text'}")
    row = next((r for r in rows if r["query_id"] == e["query_id"]), None)
    if row:
        got = [i for i in row["ranked"][:K] if i in ids]
        print(f"    the run returned {got or 'neither'} of the cluster in its top-{K}; "
              f"nDCG for this query = {row['ndcg']}")

# the same question for the structural entity pair
st = [e for e in res["entries"] if e["state"] == "ambiguous_structural"]
for e in st:
    q = str(e["query_id"])
    credited = [i for i in e["resolved_ids"] if i in (rmap.get(q) or [])]
    print(f"  Q{e['query_id']} (structural): resolver {e['resolved_ids']}, "
          f"credited {credited} -> "
          f"{'ALL' if len(credited) == len(e['resolved_ids']) else 'PARTIAL'}")

print("\n=== FINDING 4: perturbation control — flip a label, require the metric to move")
def dcg(r):
    return sum(x / math.log2(i + 2) for i, x in enumerate(r))

def pooled(Pdict, thresh=0.5):
    vals = []
    for r in rows:
        q, gold = r["query_id"], set(r["gold_ids"])
        relset = gold | {c for (qq, c), v in Pdict.items() if qq == q and v > thresh}
        rels = [1 if c in relset else 0 for c in r["ranked"][:K]]
        ideal = min(len(relset), K)
        if ideal > 0:
            vals.append(dcg(rels) / dcg([1] * ideal))
    return sum(vals) / len(vals)

def strict():
    vals = []
    for r in rows:
        gold = set(r["gold_ids"])
        rels = [1 if c in gold else 0 for c in r["ranked"][:K]]
        ideal = min(len(gold), K)
        if ideal > 0:
            vals.append(dcg(rels) / dcg([1] * ideal))
    return sum(vals) / len(vals)

base_p, base_s = pooled(P), strict()
print(f"baseline: strict {base_s:.4f} · pooled {base_p:.4f}")

# flip the single most influential label: a relevant one that is IN a top-10
inflip = [(k, v) for k, v in P.items() if v > 0.5
          and any(r["query_id"] == k[0] and k[1] in r["ranked"][:K] for r in rows)]
print(f"labels that are relevant AND inside a top-10: {len(inflip)}")
Q = dict(P)
k0 = inflip[0][0]
Q[k0] = 0.0
p1 = pooled(Q)
print(f"  flip ONE such label to 0.0 -> pooled {base_p:.4f} -> {p1:.4f} "
      f"(delta {p1-base_p:+.4f}) {'MOVED' if abs(p1-base_p) > 1e-9 else 'DID NOT MOVE — the control is blind'}")

# flip all of them: the metric must move a lot
Q2 = {k: (0.0 if v > 0.5 else v) for k, v in P.items()}
p2 = pooled(Q2)
print(f"  flip ALL {len(inflip)} relevant labels to 0.0 -> pooled {p2:.4f} "
      f"(delta {p2-base_p:+.4f})")
s2 = strict()
print(f"  strict under the same perturbation: {s2:.4f} "
      f"(delta {s2-base_s:+.4f}) <- unchanged BY DESIGN, which is exactly why")
print(f"     reproducing strict is a weak control over the pooled arm")

# and a label OUTSIDE every top-10 must NOT move pooled
out = [(k, v) for k, v in P.items() if v > 0.5
       and not any(r["query_id"] == k[0] and k[1] in r["ranked"][:K] for r in rows)]
if out:
    Q3 = dict(P); Q3[out[0][0]] = 0.0
    p3 = pooled(Q3)
    print(f"  flip a relevant label OUTSIDE every top-10 -> pooled {p3:.4f} "
          f"(delta {p3-base_p:+.4f})")
    print(f"     ⚠️ it DOES move: pooled's ideal counts relevants anywhere, so a label "
          f"outside\n     the ranking still changes the denominator. That is the pooled "
          f"contract, not a bug —\n     but it means pooled is sensitive to judgements on "
          f"chunks the system never returned.")
