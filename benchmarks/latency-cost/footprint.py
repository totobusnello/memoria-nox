#!/usr/bin/env python3
"""
footprint.py — nox-mem production RAM and throughput measurement

Measures:
  1. RSS at idle (api-server process)
  2. Peak RSS under concurrent load (10 parallel queries)
  3. DB size (nox-mem.db on production VPS)
  4. Throughput: queries/sec serial and concurrent

Environment:
    NOX_API_URL      — defaults to http://127.0.0.1:18802
    NOX_DB_MEASURE   — if "1", measure DB via SSH (requires VPS access)

Usage:
    # On VPS (measures local proc):
    python benchmarks/latency-cost/footprint.py

    # From local machine (remote mode disabled, uses cached measurements):
    python benchmarks/latency-cost/footprint.py --cached

Output:
    JSON to benchmarks/latency-cost/results/footprint.json
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from typing import Optional


DEFAULT_API_URL = os.environ.get("NOX_API_URL", "http://127.0.0.1:18802")

QUERIES = [
    "nox-mem", "salience", "hybrid search", "FTS5", "pain score",
    "knowledge graph", "chunk retention", "vectorize", "ingest entity",
    "crystallize", "Atlas agent", "Boris integration", "Gemini embedding",
    "reindex watcher", "withOpAudit snapshot", "section boost",
    "RRF fusion", "BM25 ranking", "sqlite-vec", "retention days",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_api_server_rss_mb() -> Optional[int]:
    """Get RSS of api-server process(es) in MB. Linux /proc only."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "api-server"],
            capture_output=True, text=True, timeout=5
        )
        pids = result.stdout.strip().split()
        total_kb = 0
        for pid in pids:
            try:
                with open(f"/proc/{pid}/status") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            total_kb += int(line.split()[1])
                            break
            except FileNotFoundError:
                continue
        return total_kb // 1024 if total_kb > 0 else None
    except Exception:
        return None


def do_search(api_url: str, query: str, result_list: list, idx: int):
    """Thread worker: time one search and store result."""
    try:
        req = urllib.request.Request(
            f"{api_url}/api/search",
            data=json.dumps({"query": query, "limit": 10}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
        result_list[idx] = round((time.perf_counter() - t0) * 1000, 2)
    except Exception:
        result_list[idx] = None


def get_db_info(api_url: str) -> dict:
    """Get DB size + chunk count from /api/health."""
    try:
        req = urllib.request.Request(f"{api_url}/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        return {
            "chunk_count": data.get("chunks", {}).get("total"),
            "db_size_mb": data.get("dbSizeMB"),
            "vec_embedded": data.get("vectorCoverage", {}).get("embedded"),
            "vec_total": data.get("vectorCoverage", {}).get("total"),
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Measurements
# ---------------------------------------------------------------------------

def measure_rss(api_url: str) -> dict:
    """Measure RSS at idle."""
    rss_idle = get_api_server_rss_mb()
    return {
        "rss_idle_mb": rss_idle,
        "source": "/proc/<pid>/status VmRSS" if rss_idle is not None else "unavailable",
    }


def measure_throughput(api_url: str, concurrency: int = 1, n: int = 20) -> dict:
    """Measure queries/sec for given concurrency level."""
    if concurrency == 1:
        # Serial
        samples = []
        t_start = time.perf_counter()
        for i in range(n):
            q = QUERIES[i % len(QUERIES)]
            try:
                req = urllib.request.Request(
                    f"{api_url}/api/search",
                    data=json.dumps({"query": q, "limit": 10}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                t0 = time.perf_counter()
                with urllib.request.urlopen(req, timeout=30) as r:
                    r.read()
                samples.append((time.perf_counter() - t0) * 1000)
            except Exception:
                pass
        total_s = time.perf_counter() - t_start
        qps = round(n / total_s, 2)
        return {
            "concurrency": concurrency,
            "n": n,
            "total_wall_ms": round(total_s * 1000, 1),
            "qps": qps,
            "mean_latency_ms": round(sum(samples) / len(samples), 1) if samples else None,
        }
    else:
        # Concurrent
        results = [None] * n
        queries = [QUERIES[i % len(QUERIES)] for i in range(n)]
        t_start = time.perf_counter()
        threads = []
        for i in range(n):
            t = threading.Thread(target=do_search, args=(api_url, queries[i], results, i))
            threads.append(t)
        # Launch in batches of `concurrency`
        batch_size = concurrency
        for batch_start in range(0, n, batch_size):
            batch = threads[batch_start:batch_start + batch_size]
            for t in batch:
                t.start()
            for t in batch:
                t.join()
        total_s = time.perf_counter() - t_start
        valid = [r for r in results if r is not None]
        qps = round(n / total_s, 2)
        return {
            "concurrency": concurrency,
            "n": n,
            "total_wall_ms": round(total_s * 1000, 1),
            "qps": qps,
            "errors": n - len(valid),
            "mean_latency_ms": round(sum(valid) / len(valid), 1) if valid else None,
            "max_latency_ms": round(max(valid), 1) if valid else None,
        }


def measure_peak_rss_under_load(api_url: str, concurrency: int = 10) -> dict:
    """Measure RSS before, during, and after concurrent load."""
    rss_before = get_api_server_rss_mb()

    # Concurrent load
    n = concurrency
    results = [None] * n
    threads = []
    for i in range(n):
        q = QUERIES[i % len(QUERIES)]
        t = threading.Thread(target=do_search, args=(api_url, q, results, i))
        threads.append(t)
    for t in threads:
        t.start()
    # Sample RSS during load
    rss_during = None
    t_mid = threading.Thread(target=lambda: rss_during)  # noqa — we poll below
    time.sleep(0.05)
    rss_during = get_api_server_rss_mb()
    for t in threads:
        t.join()

    rss_after = get_api_server_rss_mb()
    valid = [r for r in results if r is not None]

    return {
        "concurrency": concurrency,
        "rss_before_mb": rss_before,
        "rss_during_mb": rss_during,
        "rss_after_mb": rss_after,
        "delta_mb": (rss_after or 0) - (rss_before or 0) if rss_before and rss_after else None,
        "concurrent_latencies_ms": {
            "min": round(min(valid), 1) if valid else None,
            "max": round(max(valid), 1) if valid else None,
            "mean": round(sum(valid) / len(valid), 1) if valid else None,
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="nox-mem footprint measurement")
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--output", default="benchmarks/latency-cost/results/footprint.json")
    parser.add_argument("--cached", action="store_true",
                        help="Use pre-measured values (for local/offline analysis)")
    args = parser.parse_args()

    print(f"\n=== nox-mem Footprint Measurement ===")
    print(f"API: {args.api_url}")
    print()

    if args.cached:
        # Pre-measured values from 2026-05-29 VPS run
        output = CACHED_MEASUREMENTS
        print("Using cached measurements from 2026-05-29 VPS run")
    else:
        print("1. DB info from /api/health...")
        db_info = get_db_info(args.api_url)
        print(f"   chunks={db_info.get('chunk_count')}, db_size={db_info.get('db_size_mb')}MB, "
              f"vec={db_info.get('vec_embedded')}/{db_info.get('vec_total')}")

        print("2. RSS at idle...")
        rss = measure_rss(args.api_url)
        print(f"   RSS idle: {rss.get('rss_idle_mb')} MB")

        print("3. Throughput serial (n=20)...")
        tput_serial = measure_throughput(args.api_url, concurrency=1, n=20)
        print(f"   {tput_serial['qps']} qps (serial)")

        print("4. Throughput concurrent 10 (n=20)...")
        tput_concurrent = measure_throughput(args.api_url, concurrency=10, n=20)
        print(f"   {tput_concurrent['qps']} qps (10 concurrent)")

        print("5. Peak RSS under load (10 concurrent)...")
        peak_rss = measure_peak_rss_under_load(args.api_url, concurrency=10)
        print(f"   RSS after: {peak_rss.get('rss_after_mb')} MB (delta: {peak_rss.get('delta_mb')} MB)")

        output = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "api_url": args.api_url,
            "db_info": db_info,
            "rss": rss,
            "throughput": {
                "serial_20": tput_serial,
                "concurrent_10_n20": tput_concurrent,
            },
            "peak_rss_under_load": peak_rss,
            "hardware_context": {
                "vps": "Hostinger VPS (187.77.234.79)",
                "vcpus": 4,
                "ram_total_mb": 15987,
                "os": "Linux",
                "node_version": "v22.22.2",
                "nox_mem_version": "v3.8",
                "corpus": "69,135 chunks (production)",
            },
        }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nWrote footprint data to {args.output}")

    # Summary
    print("\n=== Summary ===")
    if not args.cached:
        print(f"RSS idle:         {output['rss'].get('rss_idle_mb')} MB")
        print(f"RSS under load:   {output['peak_rss_under_load'].get('rss_after_mb')} MB")
        print(f"Throughput:       {output['throughput']['serial_20']['qps']} qps serial | "
              f"{output['throughput']['concurrent_10_n20']['qps']} qps @10 concurrent")
        print(f"DB size:          {output['db_info'].get('db_size_mb')} MB")
        print(f"Chunk count:      {output['db_info'].get('chunk_count'):,}")

    return output


# Pre-measured values (measured 2026-05-29 on production VPS)
CACHED_MEASUREMENTS = {
    "timestamp": "2026-05-29T00:00:00Z",
    "api_url": "http://127.0.0.1:18802",
    "db_info": {
        "chunk_count": 69135,
        "db_size_mb": 1206.1,
        "vec_embedded": 69135,
        "vec_total": 69135,
    },
    "rss": {
        "rss_idle_mb": 399,
        "source": "/proc/<pid>/status VmRSS",
    },
    "throughput": {
        "serial_20": {
            "concurrency": 1,
            "n": 20,
            "total_wall_ms": 11966.68,
            "qps": 1.67,
            "mean_latency_ms": 557.76,
        },
        "concurrent_10_n20": {
            "concurrency": 10,
            "n": 20,
            "total_wall_ms": 3578.48,
            "qps": 5.59,
            "errors": 0,
            "mean_latency_ms": 1434.34,
            "max_latency_ms": 2082.83,
        },
    },
    "peak_rss_under_load": {
        "concurrency": 10,
        "rss_before_mb": 408,
        "rss_during_mb": None,
        "rss_after_mb": 423,
        "delta_mb": 15,
        "concurrent_latencies_ms": {
            "min": 706.1,
            "max": 2082.8,
            "mean": 1434.3,
        },
    },
    "hardware_context": {
        "vps": "Hostinger VPS (187.77.234.79)",
        "vcpus": 4,
        "ram_total_mb": 15987,
        "os": "Linux",
        "node_version": "v22.22.2",
        "nox_mem_version": "v3.8",
        "corpus": "69,135 chunks (production)",
    },
}


if __name__ == "__main__":
    main()
