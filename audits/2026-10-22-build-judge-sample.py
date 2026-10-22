#!/usr/bin/env python3
"""Blind sample for measuring judge-human agreement.

Every number produced on 2026-10-22 — KG fidelity 0.833, the nDCG interval
[0.24, 0.51], the abstention 0.696/0.200 — was labelled by
`gemini-2.5-flash-lite`, and that judge's agreement with a human has never been
measured. So all three carry an unquantified error.

Design:
  - Two label families, the two that decide a number: KG faithfulness
    (`sustenta`) and pooled relevance (`relevante`).
  - STRATIFIED by the judge's own label, 10 per cell, because the rare class is
    the one that sets precision: a simple random sample of 20 would land ~17
    positives and estimate the negative cell on 3 items.
  - The judge's label is NOT shown, and the items are shuffled, so the human
    cannot be anchored by it. Agreement is computed per stratum afterwards,
    which is what lets the precision be corrected.
  - Evidence is included in full (truncated for display only), because judging
    faithfulness against the quoted span alone would check the quote, not the
    claim — the distinction that moved S1 from 0.700 to 0.833.
"""
import json, random, sqlite3, sys

S1 = "/root/medicoes/2026-10-22-kg-s1/s1-rows-recheck.json"
POOL = "/root/medicoes/2026-10-22-gold/pooling.json"
GOLD = "/root/medicoes/2026-10-22-gold/golden-queries-v2.jsonl"
DB = "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db"
PER_CELL = 10
SEED = 20261022

rnd = random.Random(SEED)
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

def chunk_text(cid, limit=2600):
    r = con.execute("SELECT chunk_text, source_file FROM chunks WHERE id=?", (cid,)).fetchone()
    if not r:
        return None, None
    t = r[0] or ""
    return (t[:limit] + ("\n[…corte de exibição…]" if len(t) > limit else "")), r[1]

items = []

# ── KG faithfulness ──────────────────────────────────────────────────────────
s1 = json.load(open(S1))
for label in (True, False):
    pool = [r for r in s1 if bool(r.get("sustenta")) is label and r.get("evidence_chunk_id")]
    for r in rnd.sample(pool, min(PER_CELL, len(pool))):
        txt, sf = chunk_text(r["evidence_chunk_id"])
        if txt is None:
            continue
        items.append({
            "id": f"kg-{r['relation_id']}",
            "family": "kg",
            "question": "Este trecho sustenta a afirmação abaixo?",
            "claim": f"{r['source']} — {r['relation']} — {r['target']}",
            "evidence": txt,
            "source_file": sf,
            "_judge": bool(r.get("sustenta")),
        })

# ── pooled relevance ─────────────────────────────────────────────────────────
queries = {}
for line in open(GOLD):
    d = json.loads(line)
    queries[d["query_id"]] = d["query"]

pool_rows = json.load(open(POOL))
for label in (True, False):
    cand = [r for r in pool_rows if bool(r.get("relevante")) is label and r.get("chunk_id")]
    for r in rnd.sample(cand, min(PER_CELL, len(cand))):
        txt, sf = chunk_text(r["chunk_id"])
        if txt is None:
            continue
        items.append({
            "id": f"pool-{r['query_id']}-{r['chunk_id']}",
            "family": "pool",
            "question": "Este trecho é relevante para a pergunta abaixo?",
            "claim": queries.get(r["query_id"], f"(query {r['query_id']} não encontrada)"),
            "evidence": txt,
            "source_file": sf,
            "_judge": bool(r.get("relevante")),
        })

rnd.shuffle(items)
json.dump({
    "generated": "2026-10-22",
    "seed": SEED,
    "per_cell": PER_CELL,
    "n": len(items),
    "by_family": {f: sum(1 for i in items if i["family"] == f) for f in ("kg", "pool")},
    "items": items,
}, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
print(f"{len(items)} itens", {f: sum(1 for i in items if i['family']==f) for f in ('kg','pool')})
print("rotulos do juiz (ocultos no arquivo da pessoa):",
      {str(v): sum(1 for i in items if i['_judge'] is v) for v in (True, False)})
