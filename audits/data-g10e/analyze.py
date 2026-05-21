#!/usr/bin/env python3
"""G10e per-query rank delta analysis for KW × adversarial bucket."""
import json
from pathlib import Path

active = json.loads(Path("/tmp/g10e/kw-adv-active.json").read_text())
disabled = json.loads(Path("/tmp/g10e/kw-adv-disabled.json").read_text())

# Per-query rank of FIRST gold hit in retrieved list
def rank_of_first_gold(retrieved, gold_set):
    for i, cid in enumerate(retrieved, start=1):
        if cid in gold_set:
            return i
    return -1  # not found

# Per-query rank of EACH gold hit
def ranks_of_all_gold(retrieved, gold_set):
    ranks = {g: -1 for g in gold_set}
    for i, cid in enumerate(retrieved, start=1):
        if cid in gold_set and ranks[cid] == -1:
            ranks[cid] = i
    return ranks

print("# Per-query rank comparison (KW × adversarial, n=10)\n")
print("| qid | query | gold | rank_active | rank_disabled | Δ_rank | nDCG_active | nDCG_disabled | nDCG Δ% |")
print("|---|---|---|---:|---:|---:|---:|---:|---:|")

rows = []
for a, d in zip(active, disabled):
    assert a["qid"] == d["qid"]
    gold_a = set(a["gold_chunk_ids"])
    gold_d = set(d["gold_chunk_ids"])
    # use union or active gold? use active gold for symmetry (same eval same query)
    gold = gold_a | gold_d
    rank_a = rank_of_first_gold(a["retrieved_chunk_ids"], gold)
    rank_d = rank_of_first_gold(d["retrieved_chunk_ids"], gold)
    drank = rank_a - rank_d if (rank_a > 0 and rank_d > 0) else None
    ndcg_a = a["ndcg_at_10"]
    ndcg_d = d["ndcg_at_10"]
    ndcg_dpct = 100*(ndcg_a - ndcg_d)/ndcg_d if ndcg_d > 0 else 0
    gold_str = ",".join(sorted(gold))
    drank_str = f"{drank:+d}" if drank is not None else "n/a"
    print(f"| {a['qid']} | `{a['query']}` | {gold_str} | {rank_a} | {rank_d} | {drank_str} | {ndcg_a:.4f} | {ndcg_d:.4f} | {ndcg_dpct:+.2f}% |")
    rows.append({
        "qid": a["qid"], "query": a["query"], "gold": sorted(gold),
        "rank_active": rank_a, "rank_disabled": rank_d, "drank": drank,
        "ndcg_active": ndcg_a, "ndcg_disabled": ndcg_d, "ndcg_dpct": ndcg_dpct,
        "gold_active": sorted(gold_a), "gold_disabled": sorted(gold_d),
        "all_ranks_active": ranks_of_all_gold(a["retrieved_chunk_ids"], gold_a),
        "all_ranks_disabled": ranks_of_all_gold(d["retrieved_chunk_ids"], gold_d),
        "top5_active": a["retrieved_chunk_ids"][:5],
        "top5_disabled": d["retrieved_chunk_ids"][:5],
    })

# Worst regressions
print("\n# Worst regressions (sorted by ndcg_dpct ascending)\n")
sorted_rows = sorted(rows, key=lambda r: r["ndcg_dpct"])
for r in sorted_rows[:5]:
    print(f"- **{r['qid']}** `{r['query']}` — ndcg Δ {r['ndcg_dpct']:+.2f}% (active {r['ndcg_active']:.4f} vs disabled {r['ndcg_disabled']:.4f})")
    print(f"  - Gold (active eval): {r['gold_active']}")
    print(f"  - Gold (disabled eval): {r['gold_disabled']}")
    print(f"  - All gold ranks active: {r['all_ranks_active']}")
    print(f"  - All gold ranks disabled: {r['all_ranks_disabled']}")
    print(f"  - Top-5 active: {r['top5_active']}")
    print(f"  - Top-5 disabled: {r['top5_disabled']}")
    print()

# Aggregate gold-set analysis
print("\n# Gold-set composition analysis\n")
print("| qid | gold_active | gold_disabled | symmetric? | gold-count_active | gold-count_disabled |")
print("|---|---|---|:-:|---:|---:|")
for r in rows:
    sym = "✓" if r['gold_active'] == r['gold_disabled'] else "✗"
    print(f"| {r['qid']} | {r['gold_active']} | {r['gold_disabled']} | {sym} | {len(r['gold_active'])} | {len(r['gold_disabled'])} |")

# Save full data
out = Path("/tmp/g10e/g10e-derived.json")
out.write_text(json.dumps(rows, indent=2, default=str))
print(f"\nDerived: {out}")
