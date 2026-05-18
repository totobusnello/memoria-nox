#!/usr/bin/env python3
"""
Q3 latency benchmark — measure /api/search p50/p95/p99 on production nox-mem.

This script issues HTTP POST requests against the nox-mem hybrid search endpoint
and records wall-clock latency per query. It is intentionally self-contained
(stdlib + ``requests`` only) so it can be dropped onto the VPS and executed
without a build step.

-----------------------------------------------------------------------------
HOW TO RUN
-----------------------------------------------------------------------------

The /api/search endpoint binds to 127.0.0.1:18802 on the VPS, so the script
must execute on the VPS itself (or via SSH tunnel) — there is no public route.

1. SSH into the VPS::

     ssh root@<vps>
     cd /root/.openclaw/workspace/tools/nox-mem

2. Copy this script + the 100-query file to the VPS (one option)::

     scp paper/publication/baselines/latency_benchmark.py \\
         paper/publication/data/latency-queries-100.jsonl \\
         root@<vps>:/tmp/

3. Load nox-mem .env (Gemini key + port), then execute::

     set -a; source /root/.openclaw/.env; set +a
     python3 /tmp/latency_benchmark.py \\
       --queries  /tmp/latency-queries-100.jsonl \\
       --endpoint "http://127.0.0.1:${NOX_API_PORT:-18802}/api/search" \\
       --output   /tmp/latency-benchmark-results.jsonl \\
       --summary  /tmp/latency-benchmark-summary.json

4. Pull results back::

     scp root@<vps>:/tmp/latency-benchmark-results.jsonl \\
         paper/publication/results/
     scp root@<vps>:/tmp/latency-benchmark-summary.json \\
         paper/publication/results/

Alternative — SSH tunnel from laptop::

     ssh -L 18802:127.0.0.1:18802 root@<vps>
     # in another shell, on the laptop
     NOX_API_ENDPOINT=http://127.0.0.1:18802/api/search \\
       python3 paper/publication/baselines/latency_benchmark.py

-----------------------------------------------------------------------------
METHODOLOGY NOTES
-----------------------------------------------------------------------------

* Wall-clock timing via ``time.perf_counter()`` covers full request lifecycle
  (TCP connect + TLS where applicable + server compute + body transfer).
  Network overhead on localhost is sub-millisecond, so reported numbers are a
  faithful proxy for server-side latency.

* No warm-up phase is performed by default. The first query in each category
  may therefore reflect cold-cache behavior (semantic embedding cache, FTS5
  index pages, sqlite-vec mmap). Pass ``--warmup N`` to discard the first N
  queries from summary stats while keeping them in the raw JSONL.

* Concurrency is 1 by default (serial requests). The realistic load profile
  for nox-mem is single-user / single-agent today; raising this would test a
  scenario we do not currently serve and would distort p99.

* Percentiles use the nearest-rank method (NIST recommended for n=100):
  p_k = sorted_values[ceil(k * n / 100) - 1].

* The script writes per-query JSONL while running so a kill -INT mid-run
  still yields partial data.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    sys.stderr.write(
        "ERROR: `requests` is required. Install with `pip install requests`.\n"
    )
    sys.exit(2)


DEFAULT_ENDPOINT = os.environ.get(
    "NOX_API_ENDPOINT", "http://127.0.0.1:18802/api/search"
)
DEFAULT_QUERIES = "paper/publication/data/latency-queries-100.jsonl"
DEFAULT_OUTPUT = "paper/publication/results/latency-benchmark-results.jsonl"
DEFAULT_SUMMARY = "paper/publication/results/latency-benchmark-summary.json"


def load_queries(path: Path) -> list[dict[str, Any]]:
    """Load JSONL queries with shape ``{id, query, category}``."""
    queries: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{lineno}: invalid JSON ({exc})"
                ) from exc
            for required in ("id", "query", "category"):
                if required not in obj:
                    raise ValueError(
                        f"{path}:{lineno}: missing field '{required}'"
                    )
            queries.append(obj)
    return queries


def percentile_nearest_rank(sorted_values: list[float], pct: float) -> float:
    """NIST nearest-rank percentile. ``pct`` in [0, 100]."""
    if not sorted_values:
        return float("nan")
    rank = max(1, math.ceil(pct / 100.0 * len(sorted_values)))
    return sorted_values[rank - 1]


def run_benchmark(
    queries: list[dict[str, Any]],
    endpoint: str,
    output_path: Path,
    timeout: float,
    limit: int,
    sleep_between: float,
) -> list[dict[str, Any]]:
    """Issue one POST per query, stream results to JSONL, return in-memory list."""
    results: list[dict[str, Any]] = []
    session = requests.Session()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as out_fh:
        for i, q in enumerate(queries, 1):
            payload = {"query": q["query"], "limit": limit}
            entry: dict[str, Any] = {
                "query_id": q["id"],
                "query": q["query"],
                "category": q["category"],
            }
            t0 = time.perf_counter()
            try:
                resp = session.post(endpoint, json=payload, timeout=timeout)
                latency_ms = (time.perf_counter() - t0) * 1000.0
                entry["latency_ms"] = round(latency_ms, 3)
                entry["status_code"] = resp.status_code
                try:
                    body = resp.json()
                    hits = body.get("results") or body.get("hits") or []
                    entry["hits_count"] = len(hits)
                    if hits and isinstance(hits[0], dict):
                        top = hits[0]
                        entry["match_type_top1"] = top.get(
                            "match_type"
                        ) or top.get("matchType")
                        entry["score_top1"] = top.get("score") or top.get(
                            "rrf_score"
                        )
                except (json.JSONDecodeError, ValueError):
                    entry["hits_count"] = None
                    entry["body_parse_error"] = True
            except requests.exceptions.RequestException as exc:
                latency_ms = (time.perf_counter() - t0) * 1000.0
                entry["latency_ms"] = round(latency_ms, 3)
                entry["error"] = type(exc).__name__
                entry["error_msg"] = str(exc)[:200]

            results.append(entry)
            out_fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            out_fh.flush()

            if i % 10 == 0 or i == len(queries):
                sys.stderr.write(
                    f"  [{i:3d}/{len(queries)}] last={entry.get('latency_ms', 'NA')}ms "
                    f"cat={entry['category']}\n"
                )

            if sleep_between > 0 and i < len(queries):
                time.sleep(sleep_between)

    return results


def summarize(
    results: list[dict[str, Any]],
    endpoint: str,
    warmup: int,
) -> dict[str, Any]:
    """Compute aggregate + per-category stats. Excludes first ``warmup`` rows."""
    valid_rows = [
        r for r in results[warmup:] if "latency_ms" in r and "error" not in r
    ]
    error_rows = [r for r in results[warmup:] if "error" in r]
    latencies = sorted(r["latency_ms"] for r in valid_rows)

    def stats_block(values: list[float]) -> dict[str, Any]:
        if not values:
            return {"n": 0}
        s = sorted(values)
        return {
            "n": len(s),
            "mean_ms": round(statistics.mean(s), 3),
            "median_ms": round(statistics.median(s), 3),
            "p50_ms": round(percentile_nearest_rank(s, 50), 3),
            "p95_ms": round(percentile_nearest_rank(s, 95), 3),
            "p99_ms": round(percentile_nearest_rank(s, 99), 3),
            "max_ms": round(s[-1], 3),
            "min_ms": round(s[0], 3),
            "stdev_ms": round(statistics.pstdev(s), 3) if len(s) > 1 else 0.0,
        }

    by_category: dict[str, dict[str, Any]] = {}
    for r in valid_rows:
        by_category.setdefault(r["category"], []).append(r["latency_ms"])
    cat_stats = {cat: stats_block(vals) for cat, vals in by_category.items()}

    summary: dict[str, Any] = {
        "endpoint": endpoint,
        "generated_at_unix": int(time.time()),
        "warmup_excluded": warmup,
        "total_rows": len(results),
        "errors": len(error_rows),
        "valid": len(valid_rows),
        "aggregate": stats_block(latencies),
        "by_category": cat_stats,
        "error_types": _error_breakdown(error_rows),
    }
    return summary


def _error_breakdown(error_rows: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in error_rows:
        key = r.get("error", "unknown")
        out[key] = out.get(key, 0) + 1
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--queries", default=DEFAULT_QUERIES, help="JSONL query file")
    p.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help="Full /api/search URL (default: env NOX_API_ENDPOINT or localhost:18802)",
    )
    p.add_argument("--output", default=DEFAULT_OUTPUT, help="Per-query JSONL output")
    p.add_argument("--summary", default=DEFAULT_SUMMARY, help="Aggregate JSON summary")
    p.add_argument(
        "--limit", type=int, default=10, help="Hit limit per search (default 10)"
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Per-request timeout seconds (default 30)",
    )
    p.add_argument(
        "--warmup",
        type=int,
        default=0,
        help="Discard first N queries from summary (still written to JSONL)",
    )
    p.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Sleep seconds between requests (default 0)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    queries_path = Path(args.queries)
    output_path = Path(args.output)
    summary_path = Path(args.summary)

    if not queries_path.exists():
        sys.stderr.write(f"ERROR: queries file not found: {queries_path}\n")
        return 2

    queries = load_queries(queries_path)
    sys.stderr.write(
        f"Loaded {len(queries)} queries from {queries_path}\n"
        f"Endpoint: {args.endpoint}\n"
        f"Output:   {output_path}\n"
        f"Summary:  {summary_path}\n"
        f"Warmup discarded from summary: {args.warmup}\n\n"
    )

    results = run_benchmark(
        queries=queries,
        endpoint=args.endpoint,
        output_path=output_path,
        timeout=args.timeout,
        limit=args.limit,
        sleep_between=args.sleep,
    )

    summary = summarize(results, endpoint=args.endpoint, warmup=args.warmup)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)

    agg = summary["aggregate"]
    sys.stderr.write("\n=== Aggregate ===\n")
    if agg.get("n"):
        sys.stderr.write(
            f"  n={agg['n']}  errors={summary['errors']}\n"
            f"  p50={agg['p50_ms']}ms  p95={agg['p95_ms']}ms  p99={agg['p99_ms']}ms\n"
            f"  mean={agg['mean_ms']}ms  max={agg['max_ms']}ms  stdev={agg['stdev_ms']}ms\n"
        )
    else:
        sys.stderr.write("  no valid measurements — check endpoint and errors block\n")
    sys.stderr.write(f"\nFull summary written to {summary_path}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
