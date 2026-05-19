#!/usr/bin/env python3
"""Q1 LoCoMo production-path eval — hits TS pipeline via HTTP :18803.

Mirrors `locomo_hybrid_eval.py` (Python re-impl) but routes through the REAL
nox-mem TS pipeline running on :18803 (with NOX_DB_PATH=eval.db). Tests
whether the +18.8% nDCG@10 gain from Python re-impl reproduces in production.

Setup REQUIRED before running:
1. Markdown corpus on VPS: /tmp/locomo-md/ (5882 turns from locomo_to_markdown.py)
2. Ingested + vectorized to /root/.openclaw/eval/locomo-prod-path/eval.db
3. 2nd nox-mem-api running: NOX_DB_PATH=$EVAL_ROOT/eval.db NOX_API_PORT=18803
4. Verified: `curl -s http://127.0.0.1:18803/api/health | jq .chunks.total` returns ~5882

Usage:
    python3 locomo_production_path_eval.py [--n 100] [--seed 42]
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

# ─── Constants ──────────────────────────────────────────────────────────────
EVAL_API = "http://127.0.0.1:18803/api/search"
LOCOMO_DATA = Path("/tmp/locomo10.json")
RESULTS_OUT = Path("paper/publication/results/locomo-production-path-results.json")
SUMMARY_OUT = Path("paper/publication/results/locomo-production-path-summary.md")
DEFAULT_N = 100
DEFAULT_SEED = 42
SUBSET_PER_CATEGORY = 20  # 5 cats × 20 = 100, same as E04 + Python re-impl
CATEGORY_NAMES = {
    1: "single-hop",
    2: "multi-hop",
    3: "temporal",
    4: "open-domain",
    5: "adversarial",
}
TOP_K = 20  # retrieve top-20, score top-10

# Pre-computed FTS5 + Python-hybrid numbers (E04 + locomo_hybrid_eval) — for comparison.
FTS5_BASELINE_NDCG = 0.2810
PYTHON_HYBRID_NDCG = 0.3338

# ─── Frontmatter parser ─────────────────────────────────────────────────────
CHUNK_ID_RE = re.compile(r'chunk_id:\s*"([^"]+)"')


def extract_chunk_id_from_chunk_text(chunk_text: str) -> str | None:
    """Parse `chunk_id: "conv-26::D9:14"` from frontmatter in chunk_text."""
    m = CHUNK_ID_RE.search(chunk_text)
    return m.group(1) if m else None


def fallback_chunk_id_from_path(source_file: str) -> str | None:
    """Fallback: parse from path like '../tmp/locomo-md/conv-26/D9_14.md'."""
    parts = source_file.replace("\\", "/").split("/")
    if len(parts) < 2 or not parts[-1].endswith(".md"):
        return None
    sample_id = parts[-2]
    dia_safe = parts[-1].replace(".md", "")
    dia_id = dia_safe.replace("_", ":", 1)  # First "_" → ":"
    return f"{sample_id}::{dia_id}"


# ─── Stratified sampling (same algo as E04 + Python re-impl) ────────────────
def stratified_subset(corpus: list, seed: int = DEFAULT_SEED, per_cat: int = SUBSET_PER_CATEGORY) -> list[dict]:
    """Stratified sample, per_cat questions per category. Deterministic with seed."""
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


# ─── Retrieval via /api/search ──────────────────────────────────────────────
def search_via_api(query: str, top_k: int = TOP_K, timeout: float = 30.0) -> tuple[list[dict], float]:
    body = json.dumps({"q": query, "limit": top_k}).encode("utf-8")
    req = urllib.request.Request(
        EVAL_API,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        return [], 0.0
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    # Response is either a list directly OR a dict with "results"
    if isinstance(data, list):
        hits = data
    elif isinstance(data, dict):
        hits = data.get("results", data.get("hits", []))
    else:
        hits = []
    return hits, elapsed_ms


# ─── Metrics (same defs as locomo_hybrid_eval.py) ───────────────────────────
def dcg_at_k(rel: list[int], k: int = 10) -> float:
    return sum((2**r - 1) / math.log2(i + 2) for i, r in enumerate(rel[:k]))


def ndcg_at_k(retrieved: list[str], gold: set[str], k: int = 10) -> float:
    rel = [1 if r in gold else 0 for r in retrieved[:k]]
    dcg = dcg_at_k(rel, k)
    ideal = sorted(rel, reverse=True)
    idcg = dcg_at_k(ideal, k)
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


# ─── Main loop ──────────────────────────────────────────────────────────────
def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=DEFAULT_N)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--out", type=str, default=str(RESULTS_OUT))
    args = p.parse_args()

    if not LOCOMO_DATA.exists():
        print(f"[FATAL] LoCoMo data not found: {LOCOMO_DATA}", file=sys.stderr)
        return 1

    corpus = json.loads(LOCOMO_DATA.read_text())
    queries = stratified_subset(corpus, seed=args.seed, per_cat=args.n // 5)
    print(f"[eval] selected {len(queries)} queries (per-cat target {args.n // 5})")

    per_q = []
    t0_total = time.perf_counter()
    for i, q in enumerate(queries, 1):
        hits, ms = search_via_api(q["question"], top_k=TOP_K)
        # Map hits to canonical chunk_ids via frontmatter (preferred) or path
        retrieved_ids = []
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
            "ndcg_at_10": ndcg_at_k(retrieved_ids, gold, 10),
            "mrr": mrr(retrieved_ids, gold),
            "recall_at_10": recall_at_k(retrieved_ids, gold, 10),
            "precision_at_5": precision_at_k(retrieved_ids, gold, 5),
        }
        per_q.append(rec)
        if i % 10 == 0:
            elapsed = time.perf_counter() - t0_total
            print(f"[eval] {i}/{len(queries)} ({elapsed:.1f}s)")

    # Aggregate
    def agg(metric: str) -> float:
        vals = [r[metric] for r in per_q]
        return sum(vals) / len(vals) if vals else 0.0

    summary = {
        "system": "production_path_ts_pipeline",
        "n_queries": len(per_q),
        "endpoint": EVAL_API,
        "ndcg_at_10": agg("ndcg_at_10"),
        "mrr": agg("mrr"),
        "recall_at_10": agg("recall_at_10"),
        "precision_at_5": agg("precision_at_5"),
        "mean_latency_ms": statistics.mean([r["retrieval_ms"] for r in per_q]),
        "p95_latency_ms": sorted([r["retrieval_ms"] for r in per_q])[int(len(per_q) * 0.95)] if per_q else 0,
    }
    per_cat = {}
    for cat in [1, 2, 3, 4, 5]:
        cat_recs = [r for r in per_q if r["category"] == cat]
        if cat_recs:
            per_cat[CATEGORY_NAMES[cat]] = {
                "n": len(cat_recs),
                "ndcg_at_10": sum(r["ndcg_at_10"] for r in cat_recs) / len(cat_recs),
                "mrr": sum(r["mrr"] for r in cat_recs) / len(cat_recs),
                "recall_at_10": sum(r["recall_at_10"] for r in cat_recs) / len(cat_recs),
                "precision_at_5": sum(r["precision_at_5"] for r in cat_recs) / len(cat_recs),
            }

    out = {
        "summary": summary,
        "per_category": per_cat,
        "per_query": per_q,
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"\n[eval] wrote {args.out}")

    # Print comparison table
    delta_vs_fts = (summary["ndcg_at_10"] - FTS5_BASELINE_NDCG) / FTS5_BASELINE_NDCG * 100
    delta_vs_python = (summary["ndcg_at_10"] - PYTHON_HYBRID_NDCG) / PYTHON_HYBRID_NDCG * 100
    print(f"\n{'='*72}")
    print(f"PRODUCTION-PATH Q1 RESULTS (n={len(per_q)}, TS pipeline via :18803)")
    print(f"{'='*72}")
    print(f"Metric              Value")
    print(f"nDCG@10           {summary['ndcg_at_10']:.4f}")
    print(f"MRR               {summary['mrr']:.4f}")
    print(f"Recall@10         {summary['recall_at_10']:.4f}")
    print(f"Precision@5       {summary['precision_at_5']:.4f}")
    print(f"")
    print(f"Mean latency      {summary['mean_latency_ms']:.0f}ms")
    print(f"P95 latency       {summary['p95_latency_ms']:.0f}ms")
    print(f"")
    print(f"vs FTS5 baseline  {delta_vs_fts:+.1f}%  (FTS5 was {FTS5_BASELINE_NDCG:.4f})")
    print(f"vs Python re-impl {delta_vs_python:+.1f}%  (Python was {PYTHON_HYBRID_NDCG:.4f})")
    print(f"{'='*72}")
    print(f"")
    if summary["ndcg_at_10"] / FTS5_BASELINE_NDCG - 1 >= 0.15:
        print(f"✅ D43 Tier 2 GATE PASSED — ≥+15% rel vs FTS5, prod TS pipeline reproduces.")
    else:
        print(f"⚠️ D43 Tier 2 GATE NOT MET — <+15% rel vs FTS5. Phase 2 scale-up paused; investigate.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
