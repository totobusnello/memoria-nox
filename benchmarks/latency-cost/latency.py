#!/usr/bin/env python3
"""
latency.py — nox-mem production latency benchmark

Measures p50/p95/p99 across 4 search configurations via the live HTTP API
on the production VPS. Uses the real 69k-chunk corpus.

Configs measured:
  1. standard_hybrid   — FTS5 + Gemini embed + RRF (baseline)
  2. short_queries     — 1-5 word queries (minimal tokenization overhead)
  3. long_queries      — 10+ word NL queries (full pipeline)
  4. entity_queries    — Named-entity queries (KG-heavy path)
  5. kg_path_only      — KG walk only (no embed, pure SQLite)
  6. kg_plus_hybrid    — KG walk + hybrid search (sequential)

Usage:
    python benchmarks/latency-cost/latency.py [--api-url URL] [--n N] [--output FILE]

Environment:
    NOX_API_URL — defaults to http://127.0.0.1:18802 (production port)
    NOX_BENCH_N — number of measured iterations (default: 100)

Output:
    JSON to --output path (default: benchmarks/latency-cost/results/latency_raw.json)
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from statistics import mean, stdev
from typing import Optional

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_API_URL = os.environ.get("NOX_API_URL", "http://127.0.0.1:18802")
DEFAULT_N = int(os.environ.get("NOX_BENCH_N", "100"))
DEFAULT_WARMUP = 10

# Benchmark query sets
QUERIES_SHORT = [
    "nox-mem", "salience", "hybrid search", "chunk", "embeddings",
    "knowledge graph", "FTS5", "pain score", "retention days", "vectorize",
    "crystallize", "withOpAudit", "section boost", "reindex", "ingest",
]

QUERIES_MEDIUM = [
    "como funciona a busca híbrida no nox-mem",
    "qual é a diferença entre BM25 e busca semântica",
    "o que é pain score e como afeta o ranking",
    "como funciona o withOpAudit para operações destrutivas",
    "como configurar embeddings com gemini flash lite",
    "what is the salience formula in nox-mem",
    "how does KG path retrieval work in nox-mem",
    "explain hybrid search with FTS5 and Gemini",
    "how are retention days calculated per chunk type",
    "what happens when vectorize fails with API error",
]

QUERIES_LONG = [
    "como funciona o processo completo de ingestão de arquivos de entidade no nox-mem",
    "qual é a diferença entre BM25 e busca semântica no pipeline híbrido de search",
    "por que o campo pain foi adicionado ao schema e como ele afeta o ranking",
    "como o withOpAudit protege operações destrutivas e quais são seus limites",
    "o que acontece quando o processo de vectorize encontra um erro de API do Gemini",
    "como configurar o nox-mem para usar um modelo diferente do gemini-2.5-flash-lite",
    "quais são as diferenças entre os modos cold cache e warm cache para benchmark",
    "como o RRF combina scores do BM25 e da busca semântica no resultado final",
    "qual é o processo correto para adicionar novos tipos de entidade ao knowledge graph",
    "como funciona o mecanismo de retenção diferenciada por tipo de chunk no schema v10",
]

QUERIES_ENTITY = [
    "Atlas agent capabilities knowledge graph integration",
    "Boris agent nox-mem integration role",
    "Forge code review tool platform integration",
    "nox-mem-api port 18802 configuration setup",
    "Gemini embedding model migration flash lite",
    "OpenClaw gateway monkey-patch configuration",
    "Hostinger VPS nox-mem deployment setup",
    "FII Treviso project memory knowledge graph",
    "Galapagos Capital AI advisor role",
    "Granix co-founder project integration",
]

KG_PAIRS = [
    ("nox-mem", "Atlas"),
    ("Atlas", "Boris"),
    ("OpenClaw", "gateway"),
    ("Gemini", "embeddings"),
    ("retention", "chunks"),
    ("withOpAudit", "snapshot"),
    ("ingest", "vectorize"),
    ("BM25", "RRF"),
]


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def search(api_url: str, query: str, limit: int = 10, timeout: float = 30.0) -> Optional[float]:
    """Run one search query. Returns elapsed ms or None on error."""
    try:
        req = urllib.request.Request(
            f"{api_url}/api/search",
            data=json.dumps({"query": query, "limit": limit}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read()
        return (time.perf_counter() - t0) * 1000
    except Exception:
        return None


def kg_path(api_url: str, from_entity: str, to_entity: str, timeout: float = 10.0) -> Optional[float]:
    """Run one KG path walk. Returns elapsed ms or None on error."""
    try:
        url = (
            f"{api_url}/api/kg/path"
            f"?from={urllib.parse.quote(from_entity)}"
            f"&to={urllib.parse.quote(to_entity)}"
        )
        req = urllib.request.Request(url, method="GET")
        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read()
        return (time.perf_counter() - t0) * 1000
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def percentile(samples: list[float], p: float) -> float:
    s = sorted(samples)
    idx = max(0, int(p / 100 * len(s)) - 1)
    return round(s[idx], 2)


def compute_stats(samples: list[float], errors: int, label: str) -> dict:
    if not samples:
        return {"label": label, "n": 0, "errors": errors, "note": "no samples"}
    s = sorted(samples)
    avg = sum(s) / len(s)
    sd = stdev(s) if len(s) > 1 else 0.0
    return {
        "label": label,
        "n": len(s),
        "errors": errors,
        "p50_ms": percentile(s, 50),
        "p75_ms": percentile(s, 75),
        "p90_ms": percentile(s, 90),
        "p95_ms": percentile(s, 95),
        "p99_ms": percentile(s, 99),
        "min_ms": round(s[0], 2),
        "max_ms": round(s[-1], 2),
        "mean_ms": round(avg, 2),
        "stddev_ms": round(sd, 2),
    }


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

def run_search_bench(
    api_url: str,
    queries: list[str],
    n: int,
    warmup: int,
    label: str,
) -> dict:
    print(f"  [{label}] warmup={warmup} n={n}...", end="", flush=True)
    # Warmup
    for i in range(warmup):
        search(api_url, queries[i % len(queries)])
    # Measured
    samples = []
    errors = 0
    for i in range(n):
        q = queries[i % len(queries)]
        ms = search(api_url, q)
        if ms is None:
            errors += 1
        else:
            samples.append(ms)
        if (i + 1) % 20 == 0:
            print(f" {i+1}", end="", flush=True)
    print(" done")
    return compute_stats(samples, errors, label)


def run_kg_bench(
    api_url: str,
    pairs: list[tuple[str, str]],
    n: int,
    warmup: int,
    label: str,
) -> dict:
    print(f"  [{label}] warmup={warmup} n={n}...", end="", flush=True)
    flat = pairs * (n // len(pairs) + 1)
    for i in range(warmup):
        from_e, to_e = flat[i % len(flat)]
        kg_path(api_url, from_e, to_e)
    samples = []
    errors = 0
    for i in range(n):
        from_e, to_e = flat[i % len(flat)]
        ms = kg_path(api_url, from_e, to_e)
        if ms is None:
            errors += 1
        else:
            samples.append(ms)
        if (i + 1) % 20 == 0:
            print(f" {i+1}", end="", flush=True)
    print(" done")
    return compute_stats(samples, errors, label)


def run_kg_plus_hybrid_bench(
    api_url: str,
    queries: list[str],
    pairs: list[tuple[str, str]],
    n: int,
    warmup: int,
    label: str,
) -> dict:
    """Sequential: KG walk then hybrid search. Worst-case combined latency."""
    print(f"  [{label}] warmup={warmup} n={n}...", end="", flush=True)
    for i in range(warmup):
        from_e, to_e = pairs[i % len(pairs)]
        kg_path(api_url, from_e, to_e)
        search(api_url, queries[i % len(queries)])
    samples = []
    errors = 0
    for i in range(n):
        from_e, to_e = pairs[i % len(pairs)]
        q = queries[i % len(queries)]
        t0 = time.perf_counter()
        kg_ms = kg_path(api_url, from_e, to_e)
        search_ms = search(api_url, q)
        total = (time.perf_counter() - t0) * 1000
        if kg_ms is None or search_ms is None:
            errors += 1
        else:
            samples.append(total)
        if (i + 1) % 20 == 0:
            print(f" {i+1}", end="", flush=True)
    print(" done")
    return compute_stats(samples, errors, label)


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------

def preflight(api_url: str) -> bool:
    print(f"  Checking {api_url}/api/health ...", end="", flush=True)
    try:
        req = urllib.request.Request(f"{api_url}/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        chunks = data.get("chunks", {}).get("total", 0)
        vec = data.get("vectorCoverage", {})
        print(f" OK — {chunks} chunks, vec {vec.get('embedded')}/{vec.get('total')}")
        return chunks > 0
    except Exception as e:
        print(f" FAILED: {e}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="nox-mem latency benchmark")
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--n", type=int, default=DEFAULT_N, help="measured iterations per config")
    parser.add_argument("--warmup", type=int, default=DEFAULT_WARMUP)
    parser.add_argument("--output", default="benchmarks/latency-cost/results/latency_raw.json")
    parser.add_argument("--skip-preflight", action="store_true")
    args = parser.parse_args()

    print(f"\n=== nox-mem Latency Benchmark ===")
    print(f"API: {args.api_url} | n={args.n} | warmup={args.warmup}")
    print()

    if not args.skip_preflight:
        print("Preflight:")
        if not preflight(args.api_url):
            print("ERROR: preflight failed. API not reachable or empty corpus.")
            sys.exit(1)
        print()

    results = {}
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    print("Running search benchmarks:")
    results["standard_hybrid"] = run_search_bench(
        args.api_url, QUERIES_SHORT + QUERIES_MEDIUM, args.n, args.warmup, "standard_hybrid"
    )
    results["short_queries"] = run_search_bench(
        args.api_url, QUERIES_SHORT, args.n, args.warmup, "short_queries"
    )
    results["long_queries"] = run_search_bench(
        args.api_url, QUERIES_LONG, min(args.n, 80), args.warmup, "long_queries"
    )
    results["entity_queries"] = run_search_bench(
        args.api_url, QUERIES_ENTITY, min(args.n, 60), args.warmup, "entity_queries"
    )

    print("\nRunning KG path benchmarks:")
    results["kg_path_only"] = run_kg_bench(
        args.api_url, KG_PAIRS, min(args.n, 120), args.warmup, "kg_path_only"
    )
    results["kg_plus_hybrid"] = run_kg_plus_hybrid_bench(
        args.api_url, QUERIES_MEDIUM, KG_PAIRS, min(args.n, 50), args.warmup, "kg_plus_hybrid"
    )

    output = {
        "timestamp": timestamp,
        "api_url": args.api_url,
        "config": {"n": args.n, "warmup": args.warmup},
        "results": results,
    }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nWrote results to {args.output}")

    # Print summary table
    print("\n=== Summary ===")
    print(f"{'Config':<25} {'p50':>8} {'p95':>8} {'p99':>8} {'mean':>8} {'n':>6}")
    print("-" * 65)
    for k, v in results.items():
        if "p50_ms" in v:
            print(f"{k:<25} {v['p50_ms']:>8.1f} {v['p95_ms']:>8.1f} {v['p99_ms']:>8.1f} {v['mean_ms']:>8.1f} {v['n']:>6}")

    return output


if __name__ == "__main__":
    main()
