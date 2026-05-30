#!/usr/bin/env python3
"""Phase IterC (Q3 POC) smoke test — verify Self-Ask decomposition + per-sub-Q
answering pipeline on a small set of representative queries.

Two layers of tests:

1. Pure unit tests (no network): exercise the JSON parser shape contract for
   _iterc_decompose_query response handling + _iterc_per_subquery_overlap
   math on known inputs. These run in CI without secrets.

2. Optional end-to-end smoke (requires GEMINI_API_KEY + OPENAI_API_KEY +
   pre-warmed nox-mem.db + running api-server on NOX_API_PORT). Skipped if
   prerequisites missing.

Usage (on VPS, post-prewarming):
    set -a; source /root/.openclaw/.env; set +a
    source /root/.openclaw/evermembench-phaseB-1779978778/venv/bin/activate
    cd /tmp/<IterC-work-dir>/eval/evermembench
    NOX_DB_PATH=/root/.openclaw/evermembench-runs/phaseH-v2-004-1780019268/nox-mem.db \\
    NOX_API_PORT=18880 NOX_ITERC_DEBUG=1 \\
        python test_phaseIterC_smoke.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


# ---------------------------------------------------------------------------
# Unit tests (no network)
# ---------------------------------------------------------------------------
class IterCUnitTests(unittest.TestCase):
    """Pure-Python sanity tests — no API keys, no nox-mem, no network."""

    def test_per_subquery_overlap_disjoint(self) -> None:
        from adapter_nox_mem import _iterc_per_subquery_overlap
        # Three sub-queries that retrieved fully disjoint chunk sets
        result = _iterc_per_subquery_overlap([[1, 2], [3, 4], [5, 6]])
        self.assertEqual(result, 0.0)

    def test_per_subquery_overlap_identical(self) -> None:
        from adapter_nox_mem import _iterc_per_subquery_overlap
        # Three sub-queries that retrieved identical chunk sets
        result = _iterc_per_subquery_overlap([[1, 2, 3], [1, 2, 3], [1, 2, 3]])
        self.assertEqual(result, 1.0)

    def test_per_subquery_overlap_partial(self) -> None:
        from adapter_nox_mem import _iterc_per_subquery_overlap
        # Two sub-queries with 2/3 overlap: Jaccard({1,2,3}, {1,2,4}) = 2/4 = 0.5
        result = _iterc_per_subquery_overlap([[1, 2, 3], [1, 2, 4]])
        self.assertAlmostEqual(result, 0.5, places=3)

    def test_per_subquery_overlap_single_subq(self) -> None:
        from adapter_nox_mem import _iterc_per_subquery_overlap
        # One sub-query → no pairs, overlap=0.0 by convention
        result = _iterc_per_subquery_overlap([[1, 2, 3]])
        self.assertEqual(result, 0.0)

    def test_per_subquery_overlap_empty(self) -> None:
        from adapter_nox_mem import _iterc_per_subquery_overlap
        result = _iterc_per_subquery_overlap([])
        self.assertEqual(result, 0.0)

    def test_per_subquery_overlap_mixed_empty(self) -> None:
        from adapter_nox_mem import _iterc_per_subquery_overlap
        # One sub-query empty + two with full overlap
        result = _iterc_per_subquery_overlap([[], [1, 2], [1, 2]])
        self.assertEqual(result, 1.0)

    def test_constants_exist(self) -> None:
        import adapter_nox_mem as m
        self.assertEqual(m.DEFAULT_ITERC_N, 3)
        self.assertEqual(m.DEFAULT_ITERC_PER_QUERY_TOPK, 10)
        self.assertEqual(m.DEFAULT_ITERC_RRF_K, 60)
        self.assertIn("gemini", m.DEFAULT_ITERC_DECOMPOSER_LLM)
        self.assertIn("gpt-4.1-mini", m.DEFAULT_ITERC_ANSWERER_LLM)

    def test_decompose_prompt_contains_self_ask_framing(self) -> None:
        import adapter_nox_mem as m
        # Self-Ask hallmark: "follow-up" framing distinguishes from MQ's
        # "atomic coverage" framing.
        self.assertIn("follow-up", m.PHASE_ITERC_DECOMPOSE_PROMPT)
        self.assertIn("JSON array", m.PHASE_ITERC_DECOMPOSE_PROMPT)

    def test_answerer_prompt_grounded(self) -> None:
        import adapter_nox_mem as m
        # Hallucination guard: explicit UNKNOWN fallback.
        self.assertIn("UNKNOWN", m.PHASE_ITERC_ANSWERER_PROMPT)
        self.assertIn("retrieved memory chunks", m.PHASE_ITERC_ANSWERER_PROMPT.lower())

    def test_adapter_mode_recognized(self) -> None:
        # Ensure phaseIterC mode resolution doesn't crash.
        from adapter_nox_mem import NoxMemAdapter
        os.environ["NOX_ADAPTER_MODE"] = "phaseIterC"
        try:
            adapter = NoxMemAdapter(
                {
                    "api_base": "http://127.0.0.1:65535",  # unreachable, never called in unit test
                    "nox_mem_bin": "/usr/bin/false",
                    "search_top_k": 10,
                }
            )
            self.assertEqual(adapter.adapter_mode, "phaseIterC")
            self.assertTrue(adapter.iterc_enabled)
            # MQ should still respect its own env when phaseIterC is on
            # (we only auto-enable MQ for phaseMQ/KGMQ/Triple modes)
            self.assertFalse(adapter.mq_enabled)
            self.assertFalse(adapter.kg_enabled)
            self.assertFalse(adapter.reranker_enabled)
            self.assertFalse(adapter.ma_protection_enabled)
        finally:
            del os.environ["NOX_ADAPTER_MODE"]


# ---------------------------------------------------------------------------
# Optional end-to-end smoke (skipped if env not configured)
# ---------------------------------------------------------------------------
async def _e2e_smoke() -> int:
    """End-to-end smoke against a live api-server. Returns exit code."""
    db = os.environ.get("NOX_DB_PATH", "")
    port = os.environ.get("NOX_API_PORT", "18880")
    api_base = os.environ.get("NOX_API_BASE", f"http://127.0.0.1:{port}")
    if not db:
        print("[iterc-smoke] SKIP: NOX_DB_PATH not set")
        return 0
    if not os.environ.get("GEMINI_API_KEY"):
        print("[iterc-smoke] SKIP: GEMINI_API_KEY missing")
        return 0
    if not os.environ.get("OPENAI_API_KEY"):
        print("[iterc-smoke] SKIP: OPENAI_API_KEY missing")
        return 0

    import urllib.request

    try:
        with urllib.request.urlopen(
            f"{api_base}/api/health", timeout=10
        ) as r:
            health = json.loads(r.read().decode())
    except Exception as exc:
        print(f"[iterc-smoke] SKIP: api not responding at {api_base}: {exc}")
        return 0
    chunks = health.get("chunks", {})
    total = chunks.get("total") if isinstance(chunks, dict) else chunks
    print(f"[iterc-smoke] api health: chunks={total}")

    from adapter_nox_mem import (
        _iterc_decompose_query,
        _iterc_answer_subquestion,
        _iterc_per_subquery_overlap,
        DEFAULT_ITERC_DECOMPOSER_LLM,
        DEFAULT_ITERC_DECOMPOSER_BASE_URL,
        DEFAULT_ITERC_ANSWERER_LLM,
        DEFAULT_ITERC_ANSWERER_BASE_URL,
        DEFAULT_ITERC_N,
        DEFAULT_ITERC_RRF_K,
        DEFAULT_ITERC_ANSWERER_MAX_TOKENS,
    )
    import aiohttp

    decomposer_model = os.environ.get(
        "NOX_ITERC_DECOMPOSER_LLM", DEFAULT_ITERC_DECOMPOSER_LLM
    )
    decomposer_base = os.environ.get(
        "NOX_ITERC_DECOMPOSER_BASE_URL", DEFAULT_ITERC_DECOMPOSER_BASE_URL
    )
    decomposer_key = (
        os.environ.get("NOX_ITERC_DECOMPOSER_API_KEY")
        or os.environ["GEMINI_API_KEY"]
    )
    answerer_model = os.environ.get(
        "NOX_ITERC_ANSWERER_LLM", DEFAULT_ITERC_ANSWERER_LLM
    )
    answerer_base = os.environ.get(
        "NOX_ITERC_ANSWERER_BASE_URL", DEFAULT_ITERC_ANSWERER_BASE_URL
    )
    answerer_key = (
        os.environ.get("NOX_ITERC_ANSWERER_API_KEY")
        or os.environ["OPENAI_API_KEY"]
    )

    sample_queries = [
        # Multi-hop (should decompose well — Self-Ask sweet spot)
        "How did Weihua Zhang and Mingzhi Li collaborate on the Q4 project?",
        # Temporal (decomposition should produce date sub-Q)
        "When did the team last discuss the LongMemEval benchmark?",
        # Single-hop (Self-Ask should still work; sub-Qs become ~1-2)
        "What did Weihua Zhang say about the project?",
    ]

    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        rc = 0
        for q in sample_queries:
            print(f"\n[iterc-smoke] === query: {q[:80]} ===")
            t0 = time.monotonic() * 1000
            sub_qs, err = await _iterc_decompose_query(
                q,
                n=DEFAULT_ITERC_N,
                model=decomposer_model,
                base_url=decomposer_base,
                api_key=decomposer_key,
                timeout_s=30,
                session=session,
            )
            t1 = time.monotonic() * 1000
            if err:
                print(f"[iterc-smoke]   decompose ERROR: {err}")
                rc = 1
                continue
            print(f"[iterc-smoke]   decomposed in {t1-t0:.0f}ms -> {len(sub_qs)} sub-Qs:")
            for i, sq in enumerate(sub_qs):
                print(f"[iterc-smoke]     {i+1}. {sq}")

            # Retrieve chunks for each sub-Q
            per_sub_results: List[List[Tuple[str, Dict[str, Any]]]] = []
            for sq in sub_qs:
                try:
                    async with session.post(
                        f"{api_base}/api/search",
                        json={"query": sq, "limit": 10, "hybrid": True},
                        headers={"Content-Type": "application/json"},
                    ) as r:
                        r.raise_for_status()
                        d = await r.json()
                except Exception as exc:
                    print(f"[iterc-smoke]   sub-Q retrieve fail: {exc}")
                    per_sub_results.append([])
                    continue
                rr = d.get("results", []) if isinstance(d, dict) else d
                out: List[Tuple[str, Dict[str, Any]]] = []
                for it in rr:
                    if isinstance(it, dict):
                        c = it.get("chunk_text") or it.get("content") or ""
                        if c:
                            out.append((c, it))
                per_sub_results.append(out)

            print("[iterc-smoke]   per-sub-Q retrieved counts:", [
                len(r) for r in per_sub_results
            ])

            # Overlap
            per_sub_ids = [
                [it.get("id") or it.get("chunk_id") for _c, it in res]
                for res in per_sub_results
            ]
            overlap = _iterc_per_subquery_overlap(per_sub_ids)
            print(f"[iterc-smoke]   per-sub-Q overlap: {overlap:.3f}")

            # Per-sub-Q intermediate answer
            for i, (sq, res) in enumerate(zip(sub_qs, per_sub_results)):
                chunks_only = [c for c, _ in res]
                t2 = time.monotonic() * 1000
                ans, aerr = await _iterc_answer_subquestion(
                    subq=sq,
                    chunks=chunks_only,
                    model=answerer_model,
                    base_url=answerer_base,
                    api_key=answerer_key,
                    timeout_s=30,
                    max_tokens=DEFAULT_ITERC_ANSWERER_MAX_TOKENS,
                    session=session,
                )
                t3 = time.monotonic() * 1000
                if aerr:
                    print(f"[iterc-smoke]   sub-A {i+1} ERR ({t3-t2:.0f}ms): {aerr[:200]}")
                    rc = 1
                else:
                    print(f"[iterc-smoke]   sub-A {i+1} ({t3-t2:.0f}ms): {ans[:200]}")

    return rc


def main() -> int:
    # Run unit tests first
    print("[iterc-smoke] === unit tests ===")
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(IterCUnitTests)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    unit_rc = 0 if result.wasSuccessful() else 1
    if unit_rc != 0:
        return unit_rc

    # Optional E2E
    print("\n[iterc-smoke] === e2e smoke (optional) ===")
    e2e_rc = asyncio.run(_e2e_smoke())
    return e2e_rc


if __name__ == "__main__":
    sys.exit(main())
