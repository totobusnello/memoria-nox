#!/usr/bin/env python3
"""
Q4 COMPARISON aggregator — cross-system table generator.

Reads `output/<system>.json` (written by runner.py) and computes:
  - nDCG@10
  - Recall@10
  - MRR
  - latency p50 / p95 / p99
  - per-category breakdown (single-hop, multi-hop, temporal, open-domain,
    adversarial, numeric, knowledge-update, ...)

Emits:
  - output/_aggregate.json  — machine-readable cross-system summary
  - output/_aggregate.md    — markdown tables ready for docs/COMPARISON.md

Skeleton — full ranked-list scoring requires the gold-relevance mapping
(question_id → list of relevant chunk ids/scores). Q1/Q2 already store
`gold_chunk_ids` in dry-run-sample.json, so the minimal scoring uses
binary relevance (chunk in gold = 1, else 0). For graded relevance,
plug in `gold_relevance.json` via --gold flag Saturday.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent
OUTPUT_DEFAULT = HERE / "output"


# ---------------------------------------------------------------------------
# Metric primitives
# ---------------------------------------------------------------------------


def _binary_relevance(retrieved_ids: list[str], gold_ids: set[str]) -> list[int]:
    return [1 if r in gold_ids else 0 for r in retrieved_ids]


def dcg(rels: list[int]) -> float:
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(rels))


def ndcg_at_k(retrieved_ids: list[str], gold_ids: set[str], k: int) -> float:
    rels = _binary_relevance(retrieved_ids[:k], gold_ids)
    ideal = [1] * min(len(gold_ids), k) + [0] * max(0, k - len(gold_ids))
    idcg = dcg(ideal)
    return dcg(rels) / idcg if idcg > 0 else 0.0


def recall_at_k(retrieved_ids: list[str], gold_ids: set[str], k: int) -> float:
    if not gold_ids:
        return 0.0
    hits = sum(1 for r in retrieved_ids[:k] if r in gold_ids)
    return hits / len(gold_ids)


def reciprocal_rank(retrieved_ids: list[str], gold_ids: set[str]) -> float:
    for i, r in enumerate(retrieved_ids):
        if r in gold_ids:
            return 1.0 / (i + 1)
    return 0.0


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * (pct / 100)
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return s[int(k)]
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------


def score_system(payload: dict[str, Any], k: int) -> dict[str, Any]:
    """Compute metrics for a single system's output payload."""
    queries = payload.get("queries") or []
    overall_ndcg: list[float] = []
    overall_recall: list[float] = []
    overall_rr: list[float] = []
    latencies: list[float] = []           # all queries (including errored), if latency_ms present
    latencies_scored: list[float] = []    # only scored queries (for comparison clarity)
    n_queries_with_gold = 0
    per_category: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {"ndcg": [], "recall": [], "rr": []}
    )
    per_dataset: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {"ndcg": [], "recall": [], "rr": []}
    )

    for q in queries:
        # Always collect latency — errored queries still consumed wall-clock time
        if q.get("latency_ms") is not None:
            latencies.append(float(q["latency_ms"]))

        if q.get("error"):
            continue

        gold = set(q.get("gold_chunk_ids") or [])
        if not gold:
            # No gold for this query — skip ranking metrics
            continue

        n_queries_with_gold += 1
        retrieved = [str(r.get("id") or "") for r in (q.get("results") or [])]
        ndcg = ndcg_at_k(retrieved, gold, k)
        rec = recall_at_k(retrieved, gold, k)
        rr = reciprocal_rank(retrieved, gold)

        overall_ndcg.append(ndcg)
        overall_recall.append(rec)
        overall_rr.append(rr)

        category = q.get("category") or "uncategorized"
        per_category[category]["ndcg"].append(ndcg)
        per_category[category]["recall"].append(rec)
        per_category[category]["rr"].append(rr)

        ds = q.get("dataset") or "unknown"
        per_dataset[ds]["ndcg"].append(ndcg)
        per_dataset[ds]["recall"].append(rec)
        per_dataset[ds]["rr"].append(rr)

        if q.get("latency_ms") is not None:
            latencies_scored.append(float(q["latency_ms"]))

    def _mean(xs: list[float]) -> float:
        return statistics.fmean(xs) if xs else 0.0

    n_queries = len(queries)
    n_errors = payload.get("meta", {}).get("n_errors") or 0
    n_scored = len(overall_ndcg)

    # Derive status:
    #   SKIP    = adapter not installed (all queries errored)
    #   PARTIAL = ran but corpus not ingested (0 hits across all scored queries)
    #             OR mix of errors and successes
    #   OK      = scored ≥1 query, at least 1 non-zero metric, no errors
    all_zero_hits = n_scored > 0 and sum(overall_ndcg) == 0.0 and sum(overall_recall) == 0.0
    if n_scored == 0 and n_errors == n_queries and n_queries > 0:
        status = "SKIP"
    elif n_scored == 0 or all_zero_hits:
        status = "PARTIAL"  # ran but no actual matches (e.g. corpus not ingested)
    elif n_errors > 0:
        status = "PARTIAL"
    else:
        status = "OK"

    return {
        "system": payload.get("meta", {}).get("system"),
        "version": payload.get("meta", {}).get("version"),
        "n_queries": n_queries,
        "n_queries_with_gold": n_queries_with_gold,
        "n_scored": n_scored,
        "n_errors": n_errors,
        "status": status,
        "overall": {
            "ndcg@k": _mean(overall_ndcg),
            "recall@k": _mean(overall_recall),
            "mrr": _mean(overall_rr),
        },
        "latency_ms": {
            "p50": percentile(latencies, 50),
            "p95": percentile(latencies, 95),
            "p99": percentile(latencies, 99),
            "mean": _mean(latencies),
            "n": len(latencies),
        },
        "per_category": {
            cat: {
                "ndcg@k": _mean(vals["ndcg"]),
                "recall@k": _mean(vals["recall"]),
                "mrr": _mean(vals["rr"]),
                "n": len(vals["ndcg"]),
            }
            for cat, vals in per_category.items()
        },
        "per_dataset": {
            ds: {
                "ndcg@k": _mean(vals["ndcg"]),
                "recall@k": _mean(vals["recall"]),
                "mrr": _mean(vals["rr"]),
                "n": len(vals["ndcg"]),
            }
            for ds, vals in per_dataset.items()
        },
    }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_markdown(summary: list[dict[str, Any]], k: int) -> str:
    out: list[str] = []
    out.append(f"# Q4 COMPARISON — aggregated results (k={k})\n")
    out.append(
        "Generated by `eval/q4-comparison/aggregate.py`. "
        "Re-run after every fresh `runner.py` execution.\n"
    )
    out.append(
        "**Status legend:** OK = scored ≥1 query no errors; "
        "PARTIAL = 0 scored (corpus not ingested) or mixed errors; "
        "SKIP = adapter not installed (all errors).\n"
    )

    # Headline table
    out.append("## Headline\n")
    out.append(
        "| System | Status | nDCG@10 | R@10 | MRR | p50 (ms) | p95 (ms) | p99 (ms) | n scored | Errors |"
    )
    out.append("|---|:---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for s in summary:
        o = s["overall"]
        lat = s["latency_ms"]
        status = s.get("status", "?")
        # Only show latency when there were actual timed queries
        p50 = f"{lat['p50']:.1f}" if lat["n"] > 0 else "—"
        p95 = f"{lat['p95']:.1f}" if lat["n"] > 0 else "—"
        p99 = f"{lat['p99']:.1f}" if lat["n"] > 0 else "—"
        ndcg = f"{o['ndcg@k']:.4f}" if s["n_scored"] > 0 else "—"
        rec = f"{o['recall@k']:.4f}" if s["n_scored"] > 0 else "—"
        mrr = f"{o['mrr']:.4f}" if s["n_scored"] > 0 else "—"
        out.append(
            f"| **{s['system']}** | {status} | {ndcg} | {rec} | "
            f"{mrr} | {p50} | {p95} | "
            f"{p99} | {s['n_scored']}/{s['n_queries']} | {s['n_errors']} |"
        )

    # Per-dataset
    out.append("\n## Per-dataset\n")
    datasets = sorted({d for s in summary for d in s["per_dataset"]})
    for ds in datasets:
        out.append(f"\n### {ds}\n")
        out.append("| System | nDCG@10 | R@10 | MRR | n |")
        out.append("|---|---:|---:|---:|---:|")
        for s in summary:
            cell = s["per_dataset"].get(ds)
            if not cell:
                out.append(f"| {s['system']} | — | — | — | 0 |")
                continue
            out.append(
                f"| {s['system']} | {cell['ndcg@k']:.4f} | "
                f"{cell['recall@k']:.4f} | {cell['mrr']:.4f} | {cell['n']} |"
            )

    # Per-category
    out.append("\n## Per-category\n")
    categories = sorted({c for s in summary for c in s["per_category"]})
    out.append("| Category | " + " | ".join(s["system"] for s in summary) + " |")
    out.append("|---" * (len(summary) + 1) + "|")
    for cat in categories:
        cells = []
        for s in summary:
            v = s["per_category"].get(cat)
            cells.append(f"{v['ndcg@k']:.4f} (n={v['n']})" if v else "—")
        out.append(f"| **{cat}** | " + " | ".join(cells) + " |")

    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Q4 COMPARISON aggregator")
    p.add_argument(
        "--output-dir",
        default=str(OUTPUT_DEFAULT),
        help="directory containing per-system <name>.json (default: ./output)",
    )
    p.add_argument("--k", type=int, default=10, help="ranking cutoff for metrics")
    args = p.parse_args(argv)

    out_dir = Path(args.output_dir)
    if not out_dir.exists():
        print(f"output dir {out_dir} does not exist — run runner.py first", file=sys.stderr)
        return 1

    summary: list[dict[str, Any]] = []
    for json_path in sorted(out_dir.glob("*.json")):
        if json_path.name.startswith("_") or json_path.name.endswith(".dry-run.json"):
            continue
        try:
            payload = json.loads(json_path.read_text())
        except json.JSONDecodeError as exc:
            print(f"[skip] {json_path.name}: {exc}")
            continue
        summary.append(score_system(payload, args.k))

    summary.sort(key=lambda s: s["overall"]["ndcg@k"], reverse=True)

    agg_json = out_dir / "_aggregate.json"
    agg_md = out_dir / "_aggregate.md"
    agg_json.write_text(json.dumps({"k": args.k, "systems": summary}, indent=2))
    agg_md.write_text(render_markdown(summary, args.k))
    print(f"wrote {agg_json}")
    print(f"wrote {agg_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
