#!/usr/bin/env python3
"""
Apples-to-apples corpus-cap comparison — H1/H2 concentration paradox test.

Runs nox_mem FTS5 eval at 4 corpus caps (500, 1000, 2000, 6822/full) on
the 20 dry-run queries (10 LoCoMo + 10 LongMemEval) and computes nDCG@10,
MRR, R@10, hit_rate, p50 latency.

Usage:
    cd eval/q4-comparison
    python3 run_cap_comparison.py
    # Output goes to output/cap_comparison_results.json
    # Summary table printed to stdout

Reference sat run (PR #306):
    nox_mem full (6830 chunks): nDCG@10 = 0.3753 (FTS5-only, 20 queries)
    mem0 (500-cap, 7.3%):       nDCG@10 = 0.1315
    agentmemory (1401-cap):     nDCG@10 = 0.1376

H1: mem0 advantage is corpus-size artifact → nox_mem dominates at same cap
H2: mem0 concentration is architecturally real → mem0 still higher at same cap
"""

from __future__ import annotations

import importlib
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

# Caps to test (matches mem0 Sat run + progressive fills)
CAPS: list[int | None] = [500, 1000, 2000, None]  # None = full corpus

OUTPUT_DIR = HERE / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Sat run reference values (PR #306 cross-system run)
SAT_MEM0_NDCG = 0.1315
SAT_AGENTMEM_NDCG = 0.1376
SAT_NOXMEM_FULL_NDCG = 0.3753


# ---------------------------------------------------------------------------
# Dataset loader (mirrors runner.py)
# ---------------------------------------------------------------------------

DATASET_PATHS = {
    "locomo": HERE.parent.parent / "eval" / "locomo" / "dry-run-sample.json",
    "longmemeval": HERE.parent.parent / "eval" / "longmemeval" / "dry-run-sample.json",
}


def load_all_queries(limit: int | None = None) -> list[dict]:
    """Load up to `limit` queries per dataset from dry-run samples."""
    records = []
    for ds_name, path in DATASET_PATHS.items():
        if not path.exists():
            print(f"[cap_cmp] WARNING: {path} not found, skipping {ds_name}", file=sys.stderr)
            continue
        payload = json.loads(path.read_text())
        rows = payload.get("records", [])
        if limit:
            rows = rows[:limit]
        for row in rows:
            records.append(
                {
                    "dataset": ds_name,
                    "question_id": str(row.get("question_id") or row.get("id") or ""),
                    "query": row.get("question") or row.get("query") or "",
                    "gold_chunk_ids": list(
                        row.get("gold_chunk_ids") or row.get("answer_session_ids") or []
                    ),
                    "category": row.get("category_name") or row.get("question_type") or None,
                }
            )
    return records


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def dcg(relevances: list[float]) -> float:
    """Discounted cumulative gain."""
    return sum(
        rel / math.log2(rank + 1)
        for rank, rel in enumerate(relevances, start=1)
        if rel > 0
    )


def ndcg_at_k(retrieved_ids: list[str], gold_ids: list[str], k: int = 10) -> float:
    """nDCG@k — binary relevance."""
    gold_set = set(gold_ids)
    if not gold_set:
        return 0.0
    top_k = retrieved_ids[:k]
    rels = [1.0 if rid in gold_set else 0.0 for rid in top_k]
    ideal = [1.0] * min(len(gold_set), k)
    ideal_dcg = dcg(ideal)
    if ideal_dcg == 0:
        return 0.0
    return dcg(rels) / ideal_dcg


def mrr(retrieved_ids: list[str], gold_ids: list[str]) -> float:
    """Mean Reciprocal Rank (single query)."""
    gold_set = set(gold_ids)
    if not gold_set:
        return 0.0
    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid in gold_set:
            return 1.0 / rank
    return 0.0


def recall_at_k(retrieved_ids: list[str], gold_ids: list[str], k: int = 10) -> float:
    """R@k — fraction of gold ids found in top-k."""
    gold_set = set(gold_ids)
    if not gold_set:
        return 0.0
    top_k = set(retrieved_ids[:k])
    return len(top_k & gold_set) / len(gold_set)


def hit_rate(retrieved_ids: list[str], gold_ids: list[str]) -> float:
    """1 if any gold id appears in retrieved, else 0."""
    gold_set = set(gold_ids)
    if not gold_set:
        return 0.0
    return 1.0 if any(rid in gold_set for rid in retrieved_ids) else 0.0


def compute_metrics(results: list[dict]) -> dict:
    """Aggregate per-query results into mean metrics."""
    ndcgs, mrrs, r10s, hits, latencies = [], [], [], [], []
    skipped = 0
    for r in results:
        gold = r.get("gold_chunk_ids") or []
        retrieved = [item["id"] for item in r.get("results") or []]
        if not gold:
            skipped += 1
            continue
        ndcgs.append(ndcg_at_k(retrieved, gold, k=10))
        mrrs.append(mrr(retrieved, gold))
        r10s.append(recall_at_k(retrieved, gold, k=10))
        hits.append(hit_rate(retrieved, gold))
        latencies.append(r.get("latency_ms") or 0.0)

    n = len(ndcgs)
    if n == 0:
        return {
            "n_queries": len(results),
            "n_scored": 0,
            "n_skipped_no_gold": skipped,
            "ndcg@10": None,
            "mrr": None,
            "r@10": None,
            "hit_rate": None,
            "p50_latency_ms": None,
        }

    latencies_sorted = sorted(latencies)
    p50_idx = int(len(latencies_sorted) * 0.50)
    return {
        "n_queries": len(results),
        "n_scored": n,
        "n_skipped_no_gold": skipped,
        "ndcg@10": round(statistics.mean(ndcgs), 4),
        "mrr": round(statistics.mean(mrrs), 4),
        "r@10": round(statistics.mean(r10s), 4),
        "hit_rate": round(statistics.mean(hits), 4),
        "p50_latency_ms": round(latencies_sorted[p50_idx], 1),
    }


# ---------------------------------------------------------------------------
# Run a single cap
# ---------------------------------------------------------------------------


def run_one_cap(
    cap: int | None,
    queries: list[dict],
    k: int = 10,
) -> dict[str, Any]:
    """Setup nox_mem with cap, run all queries, teardown. Returns results dict."""
    cap_label = str(cap) if cap is not None else "full"
    cap_pct = f"{(cap / 6822 * 100):.1f}%" if cap is not None else "100%"

    print(f"\n[cap_cmp] ===== cap={cap_label} ({cap_pct} of corpus) =====", file=sys.stderr)

    # Set or clear the env var before importing/reloading
    if cap is not None:
        os.environ["NOX_MEM_INGEST_LIMIT"] = str(cap)
    else:
        os.environ.pop("NOX_MEM_INGEST_LIMIT", None)

    # Always reload so the module picks up the new env var
    if "adapters.nox_mem" in sys.modules:
        nm = importlib.reload(sys.modules["adapters.nox_mem"])
    else:
        nm = importlib.import_module("adapters.nox_mem")

    # Ensure connection state is cleared (teardown may have been called)
    nm._eval_con = None
    nm._eval_db_path = None

    nm.setup()

    results = []
    for q in queries:
        t0 = time.perf_counter()
        try:
            ranked = nm.search(q["query"], k=k)
            latency_ms = (time.perf_counter() - t0) * 1000
            results.append(
                {
                    **q,
                    "results": ranked,
                    "latency_ms": round(latency_ms, 2),
                    "error": None,
                }
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - t0) * 1000
            results.append(
                {
                    **q,
                    "results": [],
                    "latency_ms": round(latency_ms, 2),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    nm.teardown()

    metrics = compute_metrics(results)
    print(
        f"[cap_cmp] cap={cap_label}: nDCG@10={metrics['ndcg@10']} | "
        f"MRR={metrics['mrr']} | R@10={metrics['r@10']} | "
        f"hit_rate={metrics['hit_rate']} | p50={metrics['p50_latency_ms']}ms",
        file=sys.stderr,
    )

    return {
        "cap": cap_label,
        "cap_int": cap,
        "cap_pct": cap_pct,
        "metrics": metrics,
        "queries": results,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("[cap_cmp] Loading queries...", file=sys.stderr)
    queries = load_all_queries()
    print(
        f"[cap_cmp] {len(queries)} queries total "
        f"({sum(1 for q in queries if q['dataset']=='locomo')} locomo + "
        f"{sum(1 for q in queries if q['dataset']=='longmemeval')} longmemeval)",
        file=sys.stderr,
    )

    all_results = []
    for cap in CAPS:
        cap_result = run_one_cap(cap, queries)
        all_results.append(cap_result)

    # Print summary table
    print("\n" + "=" * 80)
    print("APPLES-TO-APPLES CORPUS-CAP COMPARISON — nox_mem FTS5")
    print("=" * 80)
    header = f"{'Cap':>8}  {'N chunks':>10}  {'nDCG@10':>9}  {'MRR':>7}  {'R@10':>7}  {'hit_rate':>9}  {'p50(ms)':>8}"
    print(header)
    print("-" * 80)

    # Full corpus chunk count
    FULL_CHUNKS = 6822
    for r in all_results:
        cap_int = r["cap_int"]
        n_chunks = cap_int if cap_int is not None else FULL_CHUNKS
        m = r["metrics"]
        row = (
            f"{r['cap']:>8}  {n_chunks:>10,}  "
            f"{m['ndcg@10']:>9.4f}  {m['mrr']:>7.4f}  {m['r@10']:>7.4f}  "
            f"{m['hit_rate']:>9.4f}  {m['p50_latency_ms']:>8.1f}"
        )
        print(row)

    print("-" * 80)
    print(f"\nSat reference (PR #306):")
    print(f"  mem0        500 chunks  nDCG@10={SAT_MEM0_NDCG:.4f}")
    print(f"  agentmemory 1401 chunks nDCG@10={SAT_AGENTMEM_NDCG:.4f}")
    print(f"  nox_mem     full(6830)  nDCG@10={SAT_NOXMEM_FULL_NDCG:.4f}  (FTS5-only)")

    # Hypothesis verdict
    nox_500_ndcg = next(
        (r["metrics"]["ndcg@10"] for r in all_results if r["cap"] == "500"), None
    )
    print("\n" + "=" * 80)
    print("HYPOTHESIS VERDICT")
    print("=" * 80)
    if nox_500_ndcg is not None:
        if nox_500_ndcg >= SAT_MEM0_NDCG:
            delta = nox_500_ndcg - SAT_MEM0_NDCG
            print(
                f"H1 CONFIRMED: nox_mem@500 ({nox_500_ndcg:.4f}) >= mem0@500 ({SAT_MEM0_NDCG:.4f}) "
                f"(delta={delta:+.4f})"
            )
            print(
                "  → mem0 nDCG advantage was a corpus-size artifact (7.3% cap vs full)."
            )
            print(
                "  → COVERAGE IS THE MOAT. nox_mem wider recall wins even at same corpus."
            )
        else:
            delta = SAT_MEM0_NDCG - nox_500_ndcg
            print(
                f"H2 CONFIRMED: mem0@500 ({SAT_MEM0_NDCG:.4f}) > nox_mem@500 ({nox_500_ndcg:.4f}) "
                f"(delta={delta:+.4f})"
            )
            print(
                "  → Concentration is architecturally real. mem0 higher nDCG at same corpus."
            )
            print(
                "  → Lab Q1 P1: investigate mem0's summarization/extraction for density gains."
            )
    else:
        print("INCONCLUSIVE: cap=500 result not available.")

    print("=" * 80)

    # Save full output
    output = {
        "meta": {
            "description": "Apples-to-apples corpus-cap comparison (H1/H2 test)",
            "system": "nox_mem FTS5",
            "caps_tested": [str(c) if c is not None else "full" for c in CAPS],
            "n_queries_total": len(queries),
            "full_corpus_chunks": FULL_CHUNKS,
            "sat_reference": {
                "mem0_500_cap_ndcg": SAT_MEM0_NDCG,
                "agentmemory_1401_cap_ndcg": SAT_AGENTMEM_NDCG,
                "nox_mem_full_ndcg": SAT_NOXMEM_FULL_NDCG,
                "pr_reference": "PR #306",
            },
            "hypothesis_verdict": (
                "H1_confirmed"
                if nox_500_ndcg is not None and nox_500_ndcg >= SAT_MEM0_NDCG
                else "H2_confirmed"
                if nox_500_ndcg is not None
                else "inconclusive"
            ),
            "nox_mem_500_cap_ndcg": nox_500_ndcg,
        },
        "results": [
            {
                "cap": r["cap"],
                "cap_int": r["cap_int"],
                "cap_pct": r["cap_pct"],
                "metrics": r["metrics"],
            }
            for r in all_results
        ],
        "raw_queries": [
            {k: v for k, v in r.items() if k != "queries"}
            for r in all_results
        ],
    }

    out_path = OUTPUT_DIR / "cap_comparison_results.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\n[cap_cmp] Full results saved to: {out_path}")


if __name__ == "__main__":
    main()
