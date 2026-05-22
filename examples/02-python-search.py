#!/usr/bin/env python3
"""
30-second search example against the nox-mem public demo.
Stdlib only — no pip install required.

Usage:
    ./examples/02-python-search.py [query]
    BASE_URL=http://localhost:18802 ./examples/02-python-search.py "my query"
"""

import json
import os
import sys
from urllib.request import urlopen
from urllib.parse import urlencode

BASE_URL = os.environ.get("BASE_URL", "http://187.77.234.79:18802").rstrip("/")


def health() -> dict:
    """GET /api/health — returns DB stats and coverage."""
    with urlopen(f"{BASE_URL}/api/health", timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def search(query: str, limit: int = 5) -> list[dict]:
    """GET /api/search — hybrid BM25 + semantic search."""
    params = urlencode({"q": query, "limit": limit})
    with urlopen(f"{BASE_URL}/api/search?{params}", timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("results", [])


def main() -> None:
    h = health()
    vec = h.get("vec_coverage", 0)
    if isinstance(vec, (int, float)):
        vec_str = f"{vec:.2%}"
    else:
        vec_str = str(vec)
    print(f"DB: {h.get('chunks_total', '?')} chunks, vec_coverage={vec_str}")
    print(f"KG: {h.get('kg_entities', '?')} entities / {h.get('kg_relations', '?')} relations")
    print()

    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "pain-weighted hybrid memory"
    print(f"Query: {query!r}")
    print("-" * 60)

    results = search(query, limit=3)
    if not results:
        print("No results returned.")
        return

    for i, r in enumerate(results, 1):
        score = r.get("score", 0)
        score_str = f"{float(score):.3f}" if score is not None else "?"
        source = r.get("source_file", r.get("source", "?"))
        snippet = (r.get("snippet") or "").strip()[:160]
        print(f"\n  {i}. score={score_str}")
        print(f"     source={source}")
        if snippet:
            print(f"     {snippet}...")


if __name__ == "__main__":
    main()
