#!/usr/bin/env python3
"""
/api/answer concurrent smoke test — validate behavior under parallel load.

Dispatches N concurrent threads against the /api/answer endpoint and collects
latency, status distribution, and error information. Designed to be dropped on
the VPS and run directly after PR #114 correction.

-----------------------------------------------------------------------------
COST ESTIMATE
-----------------------------------------------------------------------------

Each /api/answer call invokes Gemini (embedding + generation). Approximate:

  30 requests × $0.0005/answer ≈ $0.015   (cheap — run freely)
  50 requests × $0.0005/answer ≈ $0.025
 100 requests × $0.0005/answer ≈ $0.050   (still fine)

⚠  Do NOT run with --concurrent > 10 without checking Gemini quota.
   The retry_count field in answer.metadata reveals fallback pressure.

-----------------------------------------------------------------------------
HOW TO RUN (on VPS — endpoint is 127.0.0.1 only)
-----------------------------------------------------------------------------

1. SSH into the VPS::

     ssh root@<vps>

2. Create destination dirs if they don't exist yet::

     mkdir -p /root/.openclaw/eval/paper/baselines
     mkdir -p /root/.openclaw/eval/paper/results

3. Copy script + queries::

     scp paper/publication/baselines/answer_concurrent_smoke.py \\
         paper/publication/data/latency-queries-100.jsonl \\
         root@<vps>:/root/.openclaw/eval/paper/

4. Load env vars and run::

     set -a; source /root/.openclaw/.env; set +a
     cd /root/.openclaw/eval/paper
     python3 baselines/answer_concurrent_smoke.py \\
       --total 30 --concurrent 5

   Full run (default 50 total, 10 concurrent)::

     python3 baselines/answer_concurrent_smoke.py

5. Pull results::

     scp root@<vps>:/root/.openclaw/eval/paper/results/answer-concurrent-smoke.json \\
         paper/publication/results/

-----------------------------------------------------------------------------
OUTPUT SHAPE
-----------------------------------------------------------------------------

{
  "meta": {
    "endpoint": "http://127.0.0.1:18802/api/answer",
    "concurrent": 10,
    "total_requests": 50,
    "queries_pool_size": 20,
    "timeout_sec": 30,
    "ran_at": "2026-05-18T..."
  },
  "wall_clock_sec": 12.34,
  "throughput_rps": 4.06,
  "latency_per_request": {
    "p50": 1.80,
    "p95": 2.65,
    "p99": 2.90,
    "max": 3.10,
    "min": 1.40,
    "mean": 1.85,
    "n": 50
  },
  "status_distribution": {"200": 48, "500": 2},
  "errors": [
    {"query": "...", "error": "HTTP 500", "latency_sec": 2.1}
  ],
  "answer_metadata": {
    "retry_count_p50": 0,
    "retry_count_max": 1,
    "sources_count_p50": 5
  }
}
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Optional dependency: requests (stdlib fallback via urllib)
# ---------------------------------------------------------------------------
try:
    import requests as _requests_lib

    _USE_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error

    _USE_REQUESTS = False


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_ENDPOINT = "http://127.0.0.1:18802/api/answer"
DEFAULT_CONCURRENT = 10
DEFAULT_TOTAL = 50
DEFAULT_QUERIES = "paper/publication/data/latency-queries-100.jsonl"
DEFAULT_OUTPUT = "paper/publication/results/answer-concurrent-smoke.json"
DEFAULT_TIMEOUT = 30  # seconds per request
QUERIES_POOL_SIZE = 20  # first N queries from file


# ---------------------------------------------------------------------------
# HTTP helper — works with requests OR stdlib urllib
# ---------------------------------------------------------------------------


def _post_json(endpoint: str, payload: dict, timeout: int) -> tuple[int, dict]:
    """POST JSON to endpoint. Returns (status_code, response_body_dict)."""
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    if _USE_REQUESTS:
        resp = _requests_lib.post(
            endpoint, data=body, headers=headers, timeout=timeout
        )
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text[:500]}
        return resp.status_code, data
    else:
        req = urllib.request.Request(
            endpoint, data=body, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                try:
                    data = json.loads(raw)
                except Exception:
                    data = {"raw": raw[:500].decode(errors="replace")}
                return resp.status, data
        except urllib.error.HTTPError as exc:
            try:
                data = json.loads(exc.read())
            except Exception:
                data = {"error": str(exc)}
            return exc.code, data


# ---------------------------------------------------------------------------
# Single-request worker
# ---------------------------------------------------------------------------


def _fire_one(
    endpoint: str, query: str, timeout: int, request_index: int
) -> dict[str, Any]:
    """Execute one /api/answer request. Returns result dict."""
    t0 = time.perf_counter()
    error_msg: str | None = None
    status_code = 0
    response: dict = {}

    try:
        status_code, response = _post_json(
            endpoint, {"question": query}, timeout
        )
    except Exception as exc:  # network error, timeout, etc.
        error_msg = f"{type(exc).__name__}: {exc}"

    latency = time.perf_counter() - t0

    result: dict[str, Any] = {
        "request_index": request_index,
        "query": query,
        "status_code": status_code,
        "latency_sec": round(latency, 4),
        "error": error_msg,
    }

    # Extract answer metadata if present
    if isinstance(response, dict):
        answer_meta = response.get("metadata", response.get("meta", {}))
        if isinstance(answer_meta, dict):
            result["retry_count"] = answer_meta.get("retry_count", 0)
            result["sources_count"] = answer_meta.get("sources_count", None)
        # Top-level answer text length (sanity check)
        answer_text = response.get("answer", response.get("text", ""))
        result["answer_length"] = len(answer_text) if isinstance(answer_text, str) else 0

    return result


# ---------------------------------------------------------------------------
# Percentile helper
# ---------------------------------------------------------------------------


def _percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    k = (len(sorted_v) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(sorted_v) - 1)
    frac = k - lo
    return round(sorted_v[lo] + frac * (sorted_v[hi] - sorted_v[lo]), 4)


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------


def run_smoke_test(
    endpoint: str,
    concurrent: int,
    total: int,
    queries_pool: list[str],
    timeout: int,
    output_path: Path | None,
    verbose: bool,
) -> dict[str, Any]:
    print(
        f"[smoke] endpoint={endpoint}  concurrent={concurrent}  total={total}  "
        f"pool={len(queries_pool)}  timeout={timeout}s",
        flush=True,
    )
    print(
        f"[smoke] ⚠  Cost estimate: {total} × $0.0005 ≈ ${total * 0.0005:.3f}",
        flush=True,
    )

    if concurrent > 10:
        print(
            f"[smoke] ⚠  concurrent={concurrent} > 10 — check Gemini quota before proceeding.",
            flush=True,
        )

    started_at = datetime.now(tz=timezone.utc).isoformat()
    wall_t0 = time.perf_counter()

    results: list[dict] = []
    futures_map = {}

    with ThreadPoolExecutor(max_workers=concurrent) as pool:
        for i in range(total):
            q = random.choice(queries_pool)
            fut = pool.submit(_fire_one, endpoint, q, timeout, i)
            futures_map[fut] = i

        for fut in as_completed(futures_map):
            res = fut.result()
            results.append(res)
            status = res["status_code"] or "ERR"
            tag = "OK " if res["status_code"] == 200 else "ERR"
            if verbose or res["status_code"] != 200:
                print(
                    f"[{tag}] #{res['request_index']:03d}  "
                    f"status={status}  latency={res['latency_sec']:.3f}s  "
                    f"q={res['query'][:40]!r}",
                    flush=True,
                )

    wall_elapsed = time.perf_counter() - wall_t0

    # --- Stats ---
    latencies = [r["latency_sec"] for r in results if r["error"] is None and r["status_code"] > 0]
    errors = [r for r in results if r["error"] is not None or r["status_code"] not in (200,)]

    status_dist: dict[str, int] = {}
    for r in results:
        key = str(r["status_code"]) if r["status_code"] else "network_error"
        status_dist[key] = status_dist.get(key, 0) + 1

    retry_counts = [r.get("retry_count", 0) for r in results if r.get("retry_count") is not None]
    sources_counts = [r.get("sources_count", 0) for r in results if r.get("sources_count") is not None]

    summary: dict[str, Any] = {
        "meta": {
            "endpoint": endpoint,
            "concurrent": concurrent,
            "total_requests": total,
            "queries_pool_size": len(queries_pool),
            "timeout_sec": timeout,
            "ran_at": started_at,
        },
        "wall_clock_sec": round(wall_elapsed, 4),
        "throughput_rps": round(total / wall_elapsed, 4) if wall_elapsed > 0 else 0,
        "latency_per_request": {
            "p50": _percentile(latencies, 50),
            "p95": _percentile(latencies, 95),
            "p99": _percentile(latencies, 99),
            "max": round(max(latencies), 4) if latencies else 0,
            "min": round(min(latencies), 4) if latencies else 0,
            "mean": round(sum(latencies) / len(latencies), 4) if latencies else 0,
            "n": len(latencies),
        },
        "status_distribution": status_dist,
        "error_count": len(errors),
        "errors": [
            {
                "query": r["query"],
                "status_code": r["status_code"],
                "error": r["error"],
                "latency_sec": r["latency_sec"],
            }
            for r in errors
        ],
        "answer_metadata": {
            "retry_count_p50": _percentile([float(x) for x in retry_counts], 50) if retry_counts else None,
            "retry_count_max": max(retry_counts) if retry_counts else None,
            "sources_count_p50": _percentile([float(x) for x in sources_counts], 50) if sources_counts else None,
        },
    }

    # --- Print summary ---
    print("\n" + "=" * 60)
    print(f"  CONCURRENT SMOKE TEST SUMMARY")
    print("=" * 60)
    print(f"  Endpoint   : {endpoint}")
    print(f"  Concurrent : {concurrent}  |  Total: {total}")
    print(f"  Wall clock : {wall_elapsed:.2f}s")
    print(f"  Throughput : {summary['throughput_rps']:.2f} req/s")
    print(f"  Latency    : p50={summary['latency_per_request']['p50']:.3f}s  "
          f"p95={summary['latency_per_request']['p95']:.3f}s  "
          f"p99={summary['latency_per_request']['p99']:.3f}s  "
          f"max={summary['latency_per_request']['max']:.3f}s")
    print(f"  Status     : {status_dist}")
    print(f"  Errors     : {len(errors)}/{total}")
    if retry_counts:
        print(f"  Retry p50  : {summary['answer_metadata']['retry_count_p50']}  "
              f"max={summary['answer_metadata']['retry_count_max']}")
    print("=" * 60 + "\n")

    # --- Write output ---
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
        print(f"[smoke] Output written to: {output_path}", flush=True)

    return summary


# ---------------------------------------------------------------------------
# Load queries
# ---------------------------------------------------------------------------


def load_queries(path: Path, n: int) -> list[str]:
    queries: list[str] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                q = obj.get("query") or obj.get("question") or obj.get("text") or ""
                if q:
                    queries.append(q)
            except json.JSONDecodeError:
                continue
            if len(queries) >= n:
                break
    if not queries:
        raise ValueError(f"No valid queries found in {path}")
    return queries


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="/api/answer concurrent smoke test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--endpoint",
        default=os.environ.get("NOX_API_ENDPOINT", DEFAULT_ENDPOINT),
        help=f"API endpoint (default: {DEFAULT_ENDPOINT})",
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=DEFAULT_CONCURRENT,
        help=f"Number of concurrent threads (default: {DEFAULT_CONCURRENT}, max recommended: 10)",
    )
    parser.add_argument(
        "--total",
        type=int,
        default=DEFAULT_TOTAL,
        help=f"Total number of requests to fire (default: {DEFAULT_TOTAL})",
    )
    parser.add_argument(
        "--queries",
        type=Path,
        default=Path(DEFAULT_QUERIES),
        help=f"Path to JSONL query file (default: {DEFAULT_QUERIES})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(DEFAULT_OUTPUT),
        help=f"Output JSON summary path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--pool-size",
        type=int,
        default=QUERIES_POOL_SIZE,
        help=f"Number of queries to load from file (default: {QUERIES_POOL_SIZE})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Per-request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every request result (default: only errors)",
    )
    parser.add_argument(
        "--no-output",
        action="store_true",
        help="Skip writing output file (print summary only)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible query selection",
    )

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    # Safety guard
    if args.concurrent > 10:
        print(
            f"WARNING: --concurrent {args.concurrent} exceeds recommended max of 10.\n"
            f"         This may trigger Gemini rate limiting (429) or exhaust quota.\n"
            f"         Proceed? [y/N] ",
            end="",
            flush=True,
        )
        answer = sys.stdin.readline().strip().lower()
        if answer not in ("y", "yes"):
            print("Aborted.")
            sys.exit(0)

    # Load queries
    if not args.queries.exists():
        # Try relative to script location
        alt = Path(__file__).parent.parent / "data" / "latency-queries-100.jsonl"
        if alt.exists():
            args.queries = alt
        else:
            print(f"ERROR: queries file not found: {args.queries}", file=sys.stderr)
            sys.exit(1)

    queries_pool = load_queries(args.queries, args.pool_size)
    print(f"[smoke] Loaded {len(queries_pool)} queries from {args.queries}", flush=True)

    output_path = None if args.no_output else args.output

    run_smoke_test(
        endpoint=args.endpoint,
        concurrent=args.concurrent,
        total=args.total,
        queries_pool=queries_pool,
        timeout=args.timeout,
        output_path=output_path,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
