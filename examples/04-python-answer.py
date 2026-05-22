#!/usr/bin/env python3
"""
Call /api/answer — the flagship endpoint that returns a direct answer
synthesized from the memory store (not just ranked chunks).

Stdlib only — no pip install required.

Usage:
    ./examples/04-python-answer.py [question]
    BASE_URL=http://localhost:18802 ./examples/04-python-answer.py "What is pain weight?"
"""

import json
import os
import sys
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError

BASE_URL = os.environ.get("BASE_URL", "http://187.77.234.79:18802").rstrip("/")


def answer(question: str, limit: int = 5) -> dict:
    """
    POST /api/answer — returns a synthesized answer + supporting chunks.

    Body: { "q": "<question>", "limit": N }
    """
    payload = json.dumps({"q": question, "limit": limit}).encode("utf-8")
    req = Request(
        f"{BASE_URL}/api/answer",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e


def main() -> None:
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What is the salience formula?"
    print(f"Question: {question!r}")
    print(f"Endpoint: POST {BASE_URL}/api/answer")
    print("-" * 60)

    result = answer(question, limit=5)

    # The answer field (may be 'answer', 'response', or 'text' depending on version)
    ans = result.get("answer") or result.get("response") or result.get("text") or "(no answer field)"
    print(f"\nAnswer:\n{ans}\n")

    # Supporting chunks
    chunks = result.get("chunks") or result.get("results") or []
    if chunks:
        print(f"Supporting chunks ({len(chunks)}):")
        for i, c in enumerate(chunks[:3], 1):
            score = c.get("score")
            score_str = f"{float(score):.3f}" if score is not None else "?"
            source = c.get("source_file") or c.get("source") or "?"
            snippet = (c.get("snippet") or "").strip()[:120]
            print(f"  {i}. score={score_str} | {source}")
            if snippet:
                print(f"     {snippet}...")

    # Latency if reported
    latency = result.get("latency_ms") or result.get("duration_ms")
    if latency is not None:
        print(f"\nLatency: {latency:.0f}ms")


if __name__ == "__main__":
    main()
