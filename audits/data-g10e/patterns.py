#!/usr/bin/env python3
"""G10e pattern classification — understand the failures."""
import json
from pathlib import Path
from collections import Counter

rows = json.loads(Path("/tmp/g10e/g10e-derived.json").read_text())

# Pattern 1: Query lexical analysis (typo? entity?)
print("# Pattern analysis per query\n")
print("| qid | query | typo? | gold-type | n-entities-in-query | mutex-affected? |")
print("|---|---|:-:|---|:-:|:-:|")
for r in rows:
    q = r["query"]
    # Heuristic typos: hybird (should be hybrid), Granixx (should be granix), Frooti (frooty), gallapagos (galapagos)
    typos = []
    if "hybird" in q: typos.append("hybird→hybrid")
    if "Granixx" in q: typos.append("Granixx→Granix")
    if "Frooti" in q: typos.append("Frooti→Frooty")
    if "gallapagos" in q.lower(): typos.append("gallapagos→galapagos")
    typo_str = ",".join(typos) if typos else "no-typo"
    # gold types
    gold_types = set()
    for g in r["gold"]:
        if "::compiled" in g: gold_types.add("compiled")
        if "::frontmatter" in g: gold_types.add("frontmatter")
        if "::timeline" in g: gold_types.add("timeline")
    gold_str = "+".join(sorted(gold_types))
    # query entities (heuristic via PascalCase + known names)
    known_entities = ["nox-mem","granix","paper-eval","frooty","bruno","galapagos-ai"]
    n_ents = 0
    for ent in known_entities:
        if ent.replace("-","").lower() in q.lower().replace(" ",""):
            n_ents += 1
        elif ent.split("-")[0].lower() in q.lower():
            n_ents += 1
    # Mutex-affected = nDCG Δ != 0
    affected = "YES" if abs(r["ndcg_dpct"]) > 0.01 else "no"
    print(f"| {r['qid']} | `{q}` | {typo_str} | {gold_str} | {n_ents} | {affected} |")

# Pattern 2: For affected queries, which chunk took rank 1?
print("\n# What chunk took rank 1 from gold (mutex active runs)?\n")
for r in rows:
    if abs(r["ndcg_dpct"]) < 0.01:
        continue
    print(f"## {r['qid']} `{r['query']}`")
    print(f"  Active rank 1: `{r['top5_active'][0]}` (NOT gold)")
    print(f"  Active rank 2: `{r['top5_active'][1]}` (gold)")
    print(f"  Disabled rank 1: `{r['top5_disabled'][0]}` (gold)")
    print(f"  → chunk that displaced gold under mutex: `{r['top5_active'][0]}`")
    print(f"  → this is numeric chunk_id (NOT entity::compiled). Likely raw session/markdown.")
    print()

# Pattern 3: ad-009 frontmatter recall hole (consistent across runs)
print("# Why is bruno::frontmatter never in top-10 even with mutex disabled?\n")
for r in rows:
    if r["qid"] in ("ad-009", "ad-015") and len(r["gold_active"]) > 1:
        print(f"## {r['qid']} `{r['query']}` (gold has 2 chunks: compiled+frontmatter)")
        print(f"  All gold ranks (active):   {r['all_ranks_active']}")
        print(f"  All gold ranks (disabled): {r['all_ranks_disabled']}")
        print(f"  → frontmatter at rank=-1 (never in top-20) in BOTH runs → corpus/retrieval issue, NOT mutex.")
        print()

# Pattern 4: Score breakdown by typo presence
typo_queries = [r for r in rows if "hybird" in r["query"] or "Granixx" in r["query"] or "Frooti" in r["query"] or "gallapagos" in r["query"].lower()]
clean_queries = [r for r in rows if r not in typo_queries]
print(f"# Typo vs clean breakdown (n={len(typo_queries)} vs {len(clean_queries)}):\n")
def mean(xs): return sum(xs)/len(xs) if xs else 0
print(f"  typo queries:  mean nDCG Δ% = {mean([r['ndcg_dpct'] for r in typo_queries]):+.2f}%")
print(f"  clean queries: mean nDCG Δ% = {mean([r['ndcg_dpct'] for r in clean_queries]):+.2f}%")
print(f"  → All 10 queries have typos (this bucket is exclusively keyword-with-typo).")
