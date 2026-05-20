#!/usr/bin/env python3
"""G5 ablation eval — compute nDCG@10/MRR/R@10 against entity-flavored queries.

Mirror of g4-eval.py with same chunk_id extraction logic (regex on chunk_text)
because API returns integer id but golden set uses string slugs like
'fundo-lombardia::compiled'.

Usage:
    python3 g5-eval.py <API_BASE> <QUERIES_JSONL> <CFG_LABEL>
"""

import json
import math
import re
import sys

import requests

API = sys.argv[1]
QUERIES_FILE = sys.argv[2]
CFG = sys.argv[3]

queries = [json.loads(line) for line in open(QUERIES_FILE) if line.strip()]
total_ndcg, total_mrr, total_r10, n = 0.0, 0.0, 0.0, 0
per_cat: dict[str, list] = {}


def extract_chunk_id(text: str | None) -> str | None:
    if not text:
        return None
    m = re.search(r'chunk_id:\s*"([^"]+)"', text)
    return m.group(1) if m else None


for q in queries[:100]:
    try:
        r = requests.post(
            f"{API}/api/search",
            json={"query": q["query"], "limit": 10},
            timeout=15,
        ).json()
        res = r if isinstance(r, list) else r.get("results", [])
    except Exception as e:
        print(f"  WARN: {e}", file=sys.stderr)
        continue

    gold = set(q.get("gold_chunk_ids", []))
    if not gold:
        continue
    n += 1
    cat = q.get("category", "?")
    per_cat.setdefault(cat, [0, 0.0])
    per_cat[cat][0] += 1

    dcg = 0.0
    found_rank = None
    for i, h in enumerate(res[:10]):
        cid = extract_chunk_id(h.get("chunk_text", ""))
        if cid in gold:
            dcg += 1.0 / math.log2(i + 2)
            if found_rank is None:
                found_rank = i + 1

    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(gold), 10)))
    ndcg = dcg / idcg if idcg else 0.0
    total_ndcg += ndcg
    per_cat[cat][1] += ndcg
    if found_rank:
        total_mrr += 1.0 / found_rank
    hits = sum(1 for h in res[:10] if extract_chunk_id(h.get("chunk_text", "")) in gold)
    total_r10 += hits / len(gold)

if n == 0:
    print(f"CFG={CFG} n=0 nDCG@10=N/A MRR=N/A R@10=N/A")
else:
    print(
        f"CFG={CFG} n={n} "
        f"nDCG@10={total_ndcg / n:.4f} "
        f"MRR={total_mrr / n:.4f} "
        f"R@10={total_r10 / n:.4f}"
    )
    for cat in sorted(per_cat):
        cn, cndcg = per_cat[cat]
        print(f"  cat={cat} n={cn} ndcg={cndcg / cn:.4f}")
