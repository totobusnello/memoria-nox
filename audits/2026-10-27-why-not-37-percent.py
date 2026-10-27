"""Why did repairing the gold move the score 5.7% and not the 25-37.5% I published?

My arithmetic was 0.2428 x 55/40 — it assumed the 15 queries with invalid gold
were being UNFAIRLY zeroed, so that removing them would lift the mean. Repairing
them instead of removing them tests that assumption directly: if they were
unfairly zeroed, they now score; if the system simply does not retrieve their
answer either, they stay at zero and the mean barely moves.
"""
import json, sys

W = sys.argv[1]
d = json.load(open(f"{W}/out.json"))
rows = {r["query_id"]: r for r in d["rows"] if r.get("ndcg") is not None}

# the 15 that had no valid gold in v2, per the gold audit
DEAD15 = [51, 55, 57, 58, 61, 64, 67, 71, 74, 82, 96, 99, 101, 102, 109]
v3 = [json.loads(l) for l in open("/root/medicoes/golden-queries-v3.jsonl", encoding="utf-8") if l.strip()]
status = {r["query_id"]: r.get("status") for r in v3}
repaired = [q for q in DEAD15 if status.get(q) in ("accepted", "accepted_marginal")]

print(f"of the 15 queries whose gold was wholly invalid in v2, {len(repaired)} "
      f"now carry repaired gold")
sc = [rows[q]["ndcg"] for q in repaired if q in rows]
print(f"  their nDCG@10 now: {[round(x,3) for x in sc]}")
print(f"  mean {sum(sc)/len(sc):.4f} · zero {sum(1 for x in sc if x == 0)} of {len(sc)}")

others = [r["ndcg"] for q, r in rows.items() if q not in repaired]
print(f"\nthe other {len(others)} queries: mean {sum(others)/len(others):.4f} · "
      f"zero {sum(1 for x in others if x == 0)}")

print(f"\n⇒ the repaired queries score {sum(sc)/len(sc):.4f} against "
      f"{sum(others)/len(others):.4f} for the rest.")
print("  So they were NOT being unfairly zeroed: the retriever misses their real")
print("  answer too. The invalid gold was measuring the wrong thing, not")
print("  depressing a score the system deserved.")

# and what my published arithmetic would have predicted
pub = 0.2428
print(f"\npublished prediction: {pub:.4f} x 55/40 = {pub*55/40:.4f} (+37.5%)")
print(f"measured v3:          {d['summary']['ndcg_at_10']:.4f} "
      f"({(d['summary']['ndcg_at_10']/pub-1)*100:+.1f}%)")
print(f"zero-hit: v2 29/55 = 52.7%  ->  v3 "
      f"{len(d['summary']['zero_hit_queries'])}/{d['summary']['n_scored']} = "
      f"{len(d['summary']['zero_hit_queries'])/d['summary']['n_scored']:.1%}  (it ROSE)")
