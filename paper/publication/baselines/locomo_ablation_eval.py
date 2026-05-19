#!/usr/bin/env python3
"""Q1 LoCoMo ablation harness — runs the same n=100 stratified eval against the
TS production pipeline at :18803, with feature toggles controlled by env vars
on the API process (started separately).

Outputs BOTH nDCG@10 formulas in one pass:
- D1 (sorted-rel IDCG)   — the locomo_production_path_eval.py legacy formula
- D2 (full ideal IDCG)   — the locomo_eval.py / locomo_hybrid_eval.py canonical formula

Designed to be invoked once per ablation config:
    python3 locomo_ablation_eval.py --label B0_pure_hybrid --out results/ablation_B0.json

The API process running on :18803 picks up the toggle env vars (NOX_DISABLE_BOOSTS,
NOX_DISABLE_EXPANSION, NOX_SEMANTIC_POOL_SIZE) at startup. This script does NOT
restart the API — orchestration is handled by the shell driver.

Mirrors the eval set (stratified seed=42 n=100) of locomo_production_path_eval.py
EXACTLY — same algorithm, same per_cat target — so numbers are directly comparable.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

EVAL_API_DEFAULT = "http://127.0.0.1:18803/api/search"
LOCOMO_DATA = Path("/tmp/locomo10.json")
DEFAULT_N = 100
DEFAULT_SEED = 42
SUBSET_PER_CATEGORY = 20  # 5 cats × 20 = 100
CATEGORY_NAMES = {
    1: "single-hop",
    2: "multi-hop",
    3: "temporal",
    4: "open-domain",
    5: "adversarial",
}
TOP_K = 20  # retrieve top-20, score top-10

# Pre-computed reference numbers — locked from the canonical eval set.
FTS5_BASELINE_NDCG = 0.2810
PYTHON_HYBRID_NDCG = 0.3338

CHUNK_ID_RE = re.compile(r'chunk_id:\s*"([^"]+)"')


def extract_chunk_id_from_chunk_text(chunk_text: str) -> str | None:
    m = CHUNK_ID_RE.search(chunk_text)
    return m.group(1) if m else None


def fallback_chunk_id_from_path(source_file: str) -> str | None:
    parts = source_file.replace("\\", "/").split("/")
    if len(parts) < 2 or not parts[-1].endswith(".md"):
        return None
    sample_id = parts[-2]
    dia_safe = parts[-1].replace(".md", "")
    dia_id = dia_safe.replace("_", ":", 1)
    return f"{sample_id}::{dia_id}"


def stratified_subset(corpus: list, seed: int = DEFAULT_SEED, per_cat: int = SUBSET_PER_CATEGORY) -> list[dict]:
    """EXACT same algorithm as locomo_production_path_eval.py — deterministic."""
    import random
    by_cat: dict[int, list] = {1: [], 2: [], 3: [], 4: [], 5: []}
    for conv in corpus:
        sample_id = conv.get("sample_id", "?")
        for idx, q in enumerate(conv.get("qa", [])):
            cat = q.get("category", 0)
            if cat not in by_cat:
                continue
            evidence = q.get("evidence", [])
            if not evidence:
                continue
            gold_chunk_ids = [f"{sample_id}::{ev}" for ev in evidence]
            by_cat[cat].append({
                "question_id": f"{sample_id}::q{idx}",
                "sample_id": sample_id,
                "category": cat,
                "category_name": CATEGORY_NAMES[cat],
                "question": q["question"],
                "answer": q.get("answer", ""),
                "gold_chunk_ids": gold_chunk_ids,
            })
    rng = random.Random(seed)
    selected = []
    for cat in sorted(by_cat.keys()):
        pool = by_cat[cat]
        rng.shuffle(pool)
        selected.extend(pool[:per_cat])
    return selected


def search_via_api(endpoint: str, query: str, top_k: int = TOP_K, timeout: float = 30.0) -> tuple[list[dict], float]:
    body = json.dumps({"q": query, "limit": top_k}).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return [], 0.0
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    if isinstance(data, list):
        hits = data
    elif isinstance(data, dict):
        hits = data.get("results", data.get("hits", []))
    else:
        hits = []
    return hits, elapsed_ms


# ─── nDCG — two formulas, computed side by side ─────────────────────────────
def _dcg(rel: list[int], k: int = 10) -> float:
    return sum((2**r - 1) / math.log2(i + 2) for i, r in enumerate(rel[:k]))


def ndcg_at_k_D1(retrieved: list[str], gold: set[str], k: int = 10) -> float:
    """Sorted-rel IDCG (max possible from retrieved set) — locomo_production_path_eval legacy."""
    rel = [1 if r in gold else 0 for r in retrieved[:k]]
    dcg = _dcg(rel, k)
    ideal = sorted(rel, reverse=True)
    idcg = _dcg(ideal, k)
    return dcg / idcg if idcg > 0 else 0.0


def ndcg_at_k_D2(retrieved: list[str], gold: set[str], k: int = 10) -> float:
    """Full-ideal IDCG (locomo_eval / locomo_hybrid_eval canonical formula).
    idcg = sum 1/log2(i+2) for i in range(min(|gold|, k))
    """
    rel = [1 if r in gold else 0 for r in retrieved[:k]]
    dcg = _dcg(rel, k)
    ideal_hits = min(len(gold), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    return dcg / idcg if idcg > 0 else 0.0


def mrr(retrieved: list[str], gold: set[str]) -> float:
    for i, r in enumerate(retrieved):
        if r in gold:
            return 1.0 / (i + 1)
    return 0.0


def recall_at_k(retrieved: list[str], gold: set[str], k: int = 10) -> float:
    if not gold:
        return 0.0
    hits = sum(1 for r in retrieved[:k] if r in gold)
    return hits / len(gold)


def precision_at_k(retrieved: list[str], gold: set[str], k: int = 5) -> float:
    if k == 0:
        return 0.0
    hits = sum(1 for r in retrieved[:k] if r in gold)
    return hits / k


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--label", required=True, help="ablation label (e.g. B0_pure_hybrid)")
    p.add_argument("--n", type=int, default=DEFAULT_N)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--out", required=True, help="output JSON path")
    p.add_argument("--endpoint", default=EVAL_API_DEFAULT)
    p.add_argument("--toggles", default="",
                   help="comma-separated key=val list, just for recording in JSON (e.g. NOX_DISABLE_BOOSTS=1,NOX_SEMANTIC_POOL_SIZE=20)")
    args = p.parse_args()

    if not LOCOMO_DATA.exists():
        print(f"[FATAL] LoCoMo data not found: {LOCOMO_DATA}", file=sys.stderr)
        return 1

    corpus = json.loads(LOCOMO_DATA.read_text())
    queries = stratified_subset(corpus, seed=args.seed, per_cat=args.n // 5)
    print(f"[ablation:{args.label}] selected {len(queries)} queries (per-cat target {args.n // 5})")

    toggles_dict: dict[str, str] = {}
    for kv in args.toggles.split(","):
        kv = kv.strip()
        if "=" in kv:
            k, v = kv.split("=", 1)
            toggles_dict[k.strip()] = v.strip()

    per_q = []
    t0_total = time.perf_counter()
    for i, q in enumerate(queries, 1):
        hits, ms = search_via_api(args.endpoint, q["question"], top_k=TOP_K)
        retrieved_ids: list[str] = []
        for h in hits:
            cid = extract_chunk_id_from_chunk_text(h.get("chunk_text", ""))
            if not cid:
                cid = fallback_chunk_id_from_path(h.get("source_file", ""))
            if cid:
                retrieved_ids.append(cid)

        gold = set(q["gold_chunk_ids"])
        rec = {
            "question_id": q["question_id"],
            "category": q["category"],
            "category_name": q["category_name"],
            "question": q["question"],
            "gold_chunk_ids": q["gold_chunk_ids"],
            "retrieved_chunk_ids": retrieved_ids[:TOP_K],
            "retrieval_ms": round(ms, 2),
            "ndcg_at_10_D1": ndcg_at_k_D1(retrieved_ids, gold, 10),
            "ndcg_at_10_D2": ndcg_at_k_D2(retrieved_ids, gold, 10),
            "mrr": mrr(retrieved_ids, gold),
            "recall_at_10": recall_at_k(retrieved_ids, gold, 10),
            "precision_at_5": precision_at_k(retrieved_ids, gold, 5),
        }
        per_q.append(rec)
        if i % 10 == 0:
            elapsed = time.perf_counter() - t0_total
            print(f"[ablation:{args.label}] {i}/{len(queries)} ({elapsed:.1f}s)")

    def agg(metric: str) -> float:
        vals = [r[metric] for r in per_q]
        return sum(vals) / len(vals) if vals else 0.0

    summary = {
        "label": args.label,
        "toggles": toggles_dict,
        "system": "production_path_ts_pipeline",
        "n_queries": len(per_q),
        "endpoint": args.endpoint,
        "ndcg_at_10_D1": agg("ndcg_at_10_D1"),
        "ndcg_at_10_D2": agg("ndcg_at_10_D2"),
        "mrr": agg("mrr"),
        "recall_at_10": agg("recall_at_10"),
        "precision_at_5": agg("precision_at_5"),
        "mean_latency_ms": statistics.mean([r["retrieval_ms"] for r in per_q]),
        "p95_latency_ms": sorted([r["retrieval_ms"] for r in per_q])[int(len(per_q) * 0.95)] if per_q else 0,
        "wallclock_s": round(time.perf_counter() - t0_total, 2),
    }
    per_cat = {}
    for cat in [1, 2, 3, 4, 5]:
        cat_recs = [r for r in per_q if r["category"] == cat]
        if cat_recs:
            per_cat[CATEGORY_NAMES[cat]] = {
                "n": len(cat_recs),
                "ndcg_at_10_D1": sum(r["ndcg_at_10_D1"] for r in cat_recs) / len(cat_recs),
                "ndcg_at_10_D2": sum(r["ndcg_at_10_D2"] for r in cat_recs) / len(cat_recs),
                "mrr": sum(r["mrr"] for r in cat_recs) / len(cat_recs),
                "recall_at_10": sum(r["recall_at_10"] for r in cat_recs) / len(cat_recs),
                "precision_at_5": sum(r["precision_at_5"] for r in cat_recs) / len(cat_recs),
            }

    out = {"summary": summary, "per_category": per_cat, "per_query": per_q}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"\n[ablation:{args.label}] wrote {args.out}")

    d2 = summary["ndcg_at_10_D2"]
    d1 = summary["ndcg_at_10_D1"]
    delta_fts_d2 = (d2 - FTS5_BASELINE_NDCG) / FTS5_BASELINE_NDCG * 100
    delta_fts_d1 = (d1 - FTS5_BASELINE_NDCG) / FTS5_BASELINE_NDCG * 100
    print(f"\n{'='*72}")
    print(f"ABLATION {args.label} (n={len(per_q)})")
    print(f"toggles: {toggles_dict or '(default prod)'}")
    print(f"{'='*72}")
    print(f"nDCG@10 (D2 ideal/canonical) {d2:.4f}   Δ vs FTS5 {delta_fts_d2:+.1f}%")
    print(f"nDCG@10 (D1 sorted-rel)      {d1:.4f}   Δ vs FTS5 {delta_fts_d1:+.1f}%")
    print(f"MRR                          {summary['mrr']:.4f}")
    print(f"Recall@10                    {summary['recall_at_10']:.4f}")
    print(f"Precision@5                  {summary['precision_at_5']:.4f}")
    print(f"Mean latency                 {summary['mean_latency_ms']:.0f}ms")
    print(f"P95 latency                  {summary['p95_latency_ms']:.0f}ms")
    print(f"Wallclock                    {summary['wallclock_s']:.1f}s")
    print(f"{'='*72}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
