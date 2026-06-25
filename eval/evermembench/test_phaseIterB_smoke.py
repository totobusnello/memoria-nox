#!/usr/bin/env python3
"""Phase IterB (Q3 POC) smoke test — verify ReAct multi-round loop structure
on a small set of representative queries.

Two layers of tests:

1. Pure unit tests (no network): exercise the JSON parser shape contract for
   _iterb_orchestrator_step + _iterb_per_round_overlap math + cost estimator
   on known inputs. These run in CI without secrets.

2. Optional end-to-end smoke (requires OPENAI_API_KEY or GEMINI_API_KEY +
   pre-warmed nox-mem.db + running api-server on NOX_API_PORT). Skipped if
   prerequisites missing. Walks ~3 multi-hop queries end-to-end through the
   ReAct loop and prints rounds + actions + cost.

Usage (on VPS, post-prewarming):
    set -a; source /root/.openclaw/.env; set +a
    source /root/.openclaw/evermembench-phaseB-1779978778/venv/bin/activate
    cd /tmp/<IterB-work-dir>/eval/evermembench
    NOX_DB_PATH=/root/.openclaw/evermembench-runs/phaseH-v2-004-1780019268/nox-mem.db \
    NOX_API_PORT=18980 NOX_ITERB_DEBUG=1 \
        python test_phaseIterB_smoke.py
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
class IterBUnitTests(unittest.TestCase):
    """Pure-Python sanity tests — no API keys, no nox-mem, no network."""

    def test_per_round_overlap_empty(self) -> None:
        from adapter_nox_mem import _iterb_per_round_overlap
        self.assertEqual(_iterb_per_round_overlap([]), [])

    def test_per_round_overlap_single_round(self) -> None:
        from adapter_nox_mem import _iterb_per_round_overlap
        # Round 1 always has overlap 0.0 (no prior)
        result = _iterb_per_round_overlap([[1, 2, 3]])
        self.assertEqual(result, [0.0])

    def test_per_round_overlap_disjoint(self) -> None:
        from adapter_nox_mem import _iterb_per_round_overlap
        # 3 rounds, fully disjoint: r1 overlap = 0 (no prior), r2 = 0
        # (no overlap with r1), r3 = 0 (no overlap with r1∪r2)
        result = _iterb_per_round_overlap([[1, 2], [3, 4], [5, 6]])
        self.assertEqual(result, [0.0, 0.0, 0.0])

    def test_per_round_overlap_identical(self) -> None:
        from adapter_nox_mem import _iterb_per_round_overlap
        # 3 rounds, identical: r1=0, r2=1.0 (r2 ∩ r1 == r2 ∪ r1),
        # r3=1.0 (r3 ∩ (r1∪r2) == r3 ∪ (r1∪r2))
        result = _iterb_per_round_overlap([[1, 2, 3], [1, 2, 3], [1, 2, 3]])
        self.assertEqual(result, [0.0, 1.0, 1.0])

    def test_per_round_overlap_partial_progress(self) -> None:
        from adapter_nox_mem import _iterb_per_round_overlap
        # r1=[1,2], r2=[2,3]
        # r2 ∩ r1 = {2}, r2 ∪ r1 = {1,2,3} → 1/3 ≈ 0.333
        result = _iterb_per_round_overlap([[1, 2], [2, 3]])
        self.assertAlmostEqual(result[0], 0.0, places=3)
        self.assertAlmostEqual(result[1], 1.0 / 3.0, places=3)

    def test_per_round_overlap_empty_round(self) -> None:
        from adapter_nox_mem import _iterb_per_round_overlap
        # r1=[1,2], r2=[] (LLM emitted answer right away after retrieve)
        # → r2 overlap = 0 (no chunks intersected)
        result = _iterb_per_round_overlap([[1, 2], []])
        self.assertEqual(result[0], 0.0)
        self.assertEqual(result[1], 0.0)

    def test_cost_estimator_zero(self) -> None:
        from adapter_nox_mem import _iterb_estimate_cost
        self.assertEqual(_iterb_estimate_cost(0, 0, 0.40, 1.60), 0.0)

    def test_cost_estimator_known(self) -> None:
        from adapter_nox_mem import _iterb_estimate_cost
        # 1000 input @ $0.40/1M + 500 output @ $1.60/1M
        # = 0.001 * 0.40 + 0.0005 * 1.60 = 0.0004 + 0.0008 = 0.0012
        cost = _iterb_estimate_cost(1000, 500, 0.40, 1.60)
        self.assertAlmostEqual(cost, 0.0012, places=5)

    def test_cost_estimator_gemini_rates(self) -> None:
        from adapter_nox_mem import _iterb_estimate_cost
        # Gemini-3-flash: $0.30 input, $2.50 output
        cost = _iterb_estimate_cost(1_000_000, 100_000, 0.30, 2.50)
        # = 1.0 * 0.30 + 0.1 * 2.50 = 0.30 + 0.25 = 0.55
        self.assertAlmostEqual(cost, 0.55, places=3)

    def test_constants_exist(self) -> None:
        import adapter_nox_mem as m
        self.assertEqual(m.DEFAULT_ITERB_MAX_ROUNDS, 5)
        self.assertEqual(m.DEFAULT_ITERB_PER_ROUND_TOPK, 10)
        self.assertEqual(m.DEFAULT_ITERB_RRF_K, 60)
        self.assertIn("gpt-4.1-mini", m.DEFAULT_ITERB_ORCHESTRATOR_LLM)
        self.assertEqual(m.DEFAULT_ITERB_COST_CEILING_USD, 0.01)
        self.assertGreater(m.DEFAULT_ITERB_INPUT_COST_PER_1M, 0)
        self.assertGreater(m.DEFAULT_ITERB_OUTPUT_COST_PER_1M, 0)

    def test_orchestrator_prompt_react_hallmarks(self) -> None:
        import adapter_nox_mem as m
        # ReAct distinguishing markers vs Self-Ask / MQ
        prompt = m.PHASE_ITERB_ORCHESTRATOR_PROMPT
        self.assertIn("ReAct", prompt)
        self.assertIn("retrieve", prompt)
        self.assertIn("answer", prompt)
        self.assertIn("scratchpad", prompt.lower())
        self.assertIn("max_rounds", prompt)
        # Termination rule on last round
        self.assertIn("last round", prompt)

    def test_adapter_mode_recognized(self) -> None:
        # Ensure phaseIterB mode resolution doesn't crash.
        from adapter_nox_mem import NoxMemAdapter
        os.environ["NOX_ADAPTER_MODE"] = "phaseIterB"
        try:
            adapter = NoxMemAdapter(
                {
                    "api_base": "http://127.0.0.1:65535",  # unreachable, never called
                    "nox_mem_bin": "/usr/bin/false",
                    "search_top_k": 10,
                }
            )
            self.assertEqual(adapter.adapter_mode, "phaseIterB")
            self.assertTrue(adapter.iterb_enabled)
            # IterB isolates from other knobs
            self.assertFalse(adapter.iterc_enabled)
            self.assertFalse(adapter.mq_enabled)
            self.assertFalse(adapter.kg_enabled)
            self.assertFalse(adapter.reranker_enabled)
            self.assertFalse(adapter.ma_protection_enabled)
        finally:
            del os.environ["NOX_ADAPTER_MODE"]

    def test_adapter_env_override_enables_iterb(self) -> None:
        from adapter_nox_mem import NoxMemAdapter
        os.environ["NOX_ITERB_ENABLED"] = "1"
        try:
            adapter = NoxMemAdapter(
                {
                    "api_base": "http://127.0.0.1:65535",
                    "nox_mem_bin": "/usr/bin/false",
                    "search_top_k": 10,
                }
            )
            self.assertTrue(adapter.iterb_enabled)
        finally:
            del os.environ["NOX_ITERB_ENABLED"]

    def test_adapter_env_override_disables_iterb(self) -> None:
        from adapter_nox_mem import NoxMemAdapter
        os.environ["NOX_ADAPTER_MODE"] = "phaseIterB"
        os.environ["NOX_ITERB_ENABLED"] = "0"
        try:
            adapter = NoxMemAdapter(
                {
                    "api_base": "http://127.0.0.1:65535",
                    "nox_mem_bin": "/usr/bin/false",
                    "search_top_k": 10,
                }
            )
            self.assertFalse(adapter.iterb_enabled)
        finally:
            del os.environ["NOX_ADAPTER_MODE"]
            del os.environ["NOX_ITERB_ENABLED"]


# ---------------------------------------------------------------------------
# Optional end-to-end smoke (skipped if env not configured)
# ---------------------------------------------------------------------------
async def _e2e_smoke() -> int:
    """End-to-end smoke against a live api-server. Returns exit code."""
    db = os.environ.get("NOX_DB_PATH", "")
    port = os.environ.get("NOX_API_PORT", "18980")
    api_base = os.environ.get("NOX_API_BASE", f"http://127.0.0.1:{port}")
    if not db:
        print("[iterb-smoke] SKIP: NOX_DB_PATH not set")
        return 0
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    has_gemini = bool(os.environ.get("GEMINI_API_KEY"))
    if not has_openai and not has_gemini:
        print("[iterb-smoke] SKIP: neither OPENAI_API_KEY nor GEMINI_API_KEY set")
        return 0

    import urllib.request

    try:
        with urllib.request.urlopen(
            f"{api_base}/api/health", timeout=10
        ) as r:
            health = json.loads(r.read().decode())
    except Exception as exc:
        print(f"[iterb-smoke] SKIP: api not responding at {api_base}: {exc}")
        return 0
    chunks = health.get("chunks", {})
    total = chunks.get("total") if isinstance(chunks, dict) else chunks
    print(f"[iterb-smoke] api health: chunks={total}")

    from adapter_nox_mem import (
        _iterb_orchestrator_step,
        _iterb_per_round_overlap,
        _iterb_estimate_cost,
        DEFAULT_ITERB_ORCHESTRATOR_LLM,
        DEFAULT_ITERB_ORCHESTRATOR_BASE_URL,
        DEFAULT_ITERB_MAX_ROUNDS,
        DEFAULT_ITERB_ORCHESTRATOR_MAX_TOKENS,
        DEFAULT_ITERB_INPUT_COST_PER_1M,
        DEFAULT_ITERB_OUTPUT_COST_PER_1M,
    )
    import aiohttp

    orchestrator_model = os.environ.get(
        "NOX_ITERB_ORCHESTRATOR_LLM", DEFAULT_ITERB_ORCHESTRATOR_LLM
    )
    orchestrator_base = os.environ.get(
        "NOX_ITERB_ORCHESTRATOR_BASE_URL", DEFAULT_ITERB_ORCHESTRATOR_BASE_URL
    )
    if "gemini" in orchestrator_model.lower():
        orchestrator_key = (
            os.environ.get("NOX_ITERB_ORCHESTRATOR_API_KEY")
            or os.environ.get("GEMINI_API_KEY", "")
        )
    else:
        orchestrator_key = (
            os.environ.get("NOX_ITERB_ORCHESTRATOR_API_KEY")
            or os.environ.get("OPENAI_API_KEY", "")
        )
    if not orchestrator_key:
        print(f"[iterb-smoke] SKIP: no key for {orchestrator_model}")
        return 0

    print(f"[iterb-smoke] orchestrator: {orchestrator_model} @ {orchestrator_base}")

    sample_queries = [
        # Multi-hop (ReAct sweet spot — chain inference)
        "How did Weihua Zhang and Mingzhi Li collaborate on the Q4 project?",
        # Temporal multi-hop
        "When did the team last discuss the LongMemEval benchmark and who led it?",
        # Single-hop (ReAct should answer round 1 ideally)
        "What did Weihua Zhang say about the project?",
    ]

    max_rounds = DEFAULT_ITERB_MAX_ROUNDS
    timeout = aiohttp.ClientTimeout(total=90)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        rc = 0
        for q in sample_queries:
            print(f"\n[iterb-smoke] === query: {q[:90]} ===")

            scratchpad_parts: List[str] = []
            per_round_chunk_ids: List[List[Any]] = []
            total_input = 0
            total_output = 0
            t_start = time.monotonic() * 1000

            for round_idx in range(1, max_rounds + 1):
                t0 = time.monotonic() * 1000
                scratchpad = "\n\n".join(scratchpad_parts)
                parsed, err, usage = await _iterb_orchestrator_step(
                    query=q,
                    scratchpad=scratchpad,
                    round_idx=round_idx,
                    max_rounds=max_rounds,
                    model=orchestrator_model,
                    base_url=orchestrator_base,
                    api_key=orchestrator_key,
                    timeout_s=45.0,
                    max_tokens=DEFAULT_ITERB_ORCHESTRATOR_MAX_TOKENS,
                    session=session,
                )
                t1 = time.monotonic() * 1000
                total_input += usage.get("input_tokens", 0)
                total_output += usage.get("output_tokens", 0)
                action = parsed.get("action", "answer")
                thought = parsed.get("thought", "")
                print(f"[iterb-smoke]   R{round_idx} ({t1-t0:.0f}ms) action={action}")
                if thought:
                    print(f"[iterb-smoke]     thought: {thought[:150]}")
                if err:
                    print(f"[iterb-smoke]     ERR: {err[:200]}")
                    rc = 1

                if action == "answer":
                    ans = parsed.get("answer", "")
                    print(f"[iterb-smoke]     answer: {ans[:200]}")
                    scratchpad_parts.append(
                        f"### Round {round_idx} (final)\n"
                        f"Thought: {thought}\nAnswer: {ans}"
                    )
                    break

                # retrieve
                sub_q = parsed.get("query", q)
                print(f"[iterb-smoke]     sub-query: {sub_q[:200]}")
                # Issue retrieve
                try:
                    async with session.post(
                        f"{api_base}/api/search",
                        json={"query": sub_q, "limit": 10, "hybrid": True},
                        headers={"Content-Type": "application/json"},
                    ) as r:
                        r.raise_for_status()
                        d = await r.json()
                except Exception as exc:
                    print(f"[iterb-smoke]     retrieve fail: {exc}")
                    rc = 1
                    break
                rr = d.get("results", []) if isinstance(d, dict) else d
                chunks_round: List[str] = []
                ids_round: List[Any] = []
                for it in rr:
                    if isinstance(it, dict):
                        c = it.get("chunk_text") or it.get("content") or ""
                        if c:
                            chunks_round.append(c)
                            cid = it.get("id") or it.get("chunk_id") or it.get("rowid")
                            if cid is not None:
                                ids_round.append(cid)
                per_round_chunk_ids.append(ids_round)
                print(f"[iterb-smoke]     retrieved {len(chunks_round)} chunks")
                # Build observation
                obs = "\n".join(
                    f"  [{i+1}] {c[:200]}" for i, c in enumerate(chunks_round[:3])
                ) or "  (no results)"
                scratchpad_parts.append(
                    f"### Round {round_idx}\nThought: {thought}\n"
                    f"Action: retrieve(\"{sub_q[:150]}\")\nObservation:\n{obs}"
                )

            t_total = time.monotonic() * 1000 - t_start
            cost = _iterb_estimate_cost(
                total_input,
                total_output,
                DEFAULT_ITERB_INPUT_COST_PER_1M,
                DEFAULT_ITERB_OUTPUT_COST_PER_1M,
            )
            overlap = _iterb_per_round_overlap(per_round_chunk_ids)
            print(
                f"[iterb-smoke]   TOTAL: {len(per_round_chunk_ids)} retrieve rounds, "
                f"{t_total:.0f}ms wall, ${cost:.5f} cost, "
                f"in={total_input} out={total_output}"
            )
            if overlap:
                print(
                    f"[iterb-smoke]   per-round overlap with priors: "
                    f"{[round(o, 3) for o in overlap]}"
                )

    return rc


def main() -> int:
    # Run unit tests first
    print("[iterb-smoke] === unit tests ===")
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(IterBUnitTests)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    unit_rc = 0 if result.wasSuccessful() else 1
    if unit_rc != 0:
        return unit_rc

    # Optional E2E
    print("\n[iterb-smoke] === e2e smoke (optional) ===")
    e2e_rc = asyncio.run(_e2e_smoke())
    return e2e_rc


if __name__ == "__main__":
    sys.exit(main())
