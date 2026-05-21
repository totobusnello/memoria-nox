"""G12 — compute rank of each frontmatter gold chunk in both runs."""
import csv

queries = {}
with open("/tmp/g12-frontmatter-gold-queries.tsv") as f:
    for row in csv.reader(f, delimiter="\t"):
        qid, cat, style, query, gold = row
        queries[qid] = {"qid": qid, "cat": cat, "style": style, "query": query, "gold": gold}

for fname, label in [("/tmp/g12-active-retrieved.tsv", "active"), ("/tmp/g12-disabled-retrieved.tsv", "disabled")]:
    with open(fname) as f:
        for row in csv.reader(f, delimiter="\t"):
            if fname.endswith("active-retrieved.tsv"):
                qid, query, gold_list, retrieved = row
            else:
                qid, query, retrieved = row
            retrieved_ids = retrieved.split(";")
            q = queries.get(qid)
            if not q:
                continue
            gold_chunk = q["gold"]  # e.g., "nox-mem::frontmatter"
            try:
                rank = retrieved_ids.index(gold_chunk) + 1
            except ValueError:
                rank = "OOT"
            q[f"rank_{label}"] = rank
            q[f"top5_{label}"] = retrieved_ids[:5]

print(f"{'qid':<7}{'category':<14}{'style':<18}{'query':<40}{'gold':<28}{'r_active':<10}{'r_disabled':<10}")
print("-" * 130)
for q in queries.values():
    print(f"{q['qid']:<7}{q['cat']:<14}{q['style']:<18}{q['query']:<40}{q['gold']:<28}{str(q.get('rank_active','-')):<10}{str(q.get('rank_disabled','-')):<10}")
print()
print("=== Top-5 per query (mutex active) ===")
for q in queries.values():
    print(f"\n{q['qid']} ({q['query']}) — gold={q['gold']}")
    for i, cid in enumerate(q.get("top5_active", [])):
        marker = " ← GOLD" if cid == q["gold"] else ""
        print(f"  {i+1}. {cid}{marker}")
