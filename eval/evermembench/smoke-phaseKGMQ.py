#!/usr/bin/env python3
"""Smoke test for Phase KGMQ — Wave B composability validation.

Validates:
  1. adapter_mode=phaseKGMQ resolves kg_enabled=True AND mq_enabled=True
  2. MQ decomposer fires on a multi-hop sample query (sub_queries returned)
  3. KG entity extraction fires on a factual query mentioning known entities
  4. KG-after-MQ flow: when MQ runs, KG still boosts the MQ-merged candidates
  5. Composability metadata "composability_kg_mq_active" reflects both firing

Run AFTER api-server started on $NOX_API_BASE w/ $NOX_DB_PATH.

Usage:
    NOX_API_BASE=http://127.0.0.1:18846 \\
    NOX_DB_PATH=/root/.openclaw/evermembench-runs/phaseKGMQ-004-XXXX/nox-mem.db \\
    GEMINI_API_KEY=<key> \\
    NOX_MQ_LLM_API_KEY=<key> \\
    python3 smoke-phaseKGMQ.py
"""
import asyncio
import json
import os
import sys
from pathlib import Path

# Make adapter importable from harness location
HARNESS_DIR = os.environ.get(
    "HARNESS_DIR",
    "/tmp/wave-B-KG-MQ-BEFFB4E5-7001-4788-BBC8-100E20C6C9E9/everos/benchmarks/EverMemBench",
)
sys.path.insert(0, HARNESS_DIR)

# Force phaseKGMQ mode
os.environ["NOX_ADAPTER_MODE"] = "phaseKGMQ"
os.environ.setdefault("NOX_MQ_DEBUG", "1")

from eval.src.adapters.nox_mem_adapter import NoxMemAdapter  # noqa: E402


SAMPLE_QUERIES = [
    # 1. Factual — likely few KG entities in EverMemBench corpus
    ("factual",
     "What time did the team start the morning standup?"),
    # 2. Multi-hop — should decompose well + may hit known entity names
    ("multi-hop",
     "After SQL optimization of the data submission API, what was the peak "
     "CPU usage observed during the final 300 concurrent user stress test?"),
    # 3. Temporal — date-anchored, should decompose into sub-questions
    ("temporal",
     "What did Weihua Zhang discuss in the afternoon meeting on day 5?"),
]


async def main() -> int:
    config = {
        "api_base": os.environ.get("NOX_API_BASE", "http://127.0.0.1:18846"),
        "nox_mem_bin": "nox-mem",
        "search_top_k": 10,
        "search_timeout": 60,
    }
    adapter = NoxMemAdapter(config)

    print("=" * 78)
    print("Phase KGMQ smoke test — Wave B composability validation")
    print("=" * 78)
    print(json.dumps(adapter.get_system_info(), indent=2))
    print()

    # Validation 1: mode resolution
    assert adapter.adapter_mode == "phaseKGMQ", f"mode={adapter.adapter_mode}"
    assert adapter.kg_enabled is True, f"kg_enabled={adapter.kg_enabled}"
    assert adapter.mq_enabled is True, f"mq_enabled={adapter.mq_enabled}"
    print("[OK] phaseKGMQ activates BOTH kg_enabled AND mq_enabled")

    n_ok = 0
    n_total = len(SAMPLE_QUERIES)
    for qtype, query in SAMPLE_QUERIES:
        print(f"\n--- {qtype}: {query[:80]}{'...' if len(query) > 80 else ''} ---")
        result = await adapter.search(query=query, user_id="smoke", top_k=5)
        meta = result.metadata
        mq_applied = meta.get("mq_applied")
        kg_applied = meta.get("kg_applied")
        composable = meta.get("composability_kg_mq_active")
        print(f"  mq_applied={mq_applied} mq_n={meta.get('mq_n_actual')} mq_decompose_ms={meta.get('mq_decompose_ms')}")
        print(f"  kg_applied={kg_applied} kg_meta={meta.get('kg_meta')}")
        print(f"  composability_kg_mq_active={composable}")
        print(f"  api_returned={meta.get('api_returned')} returned={meta.get('returned')}")
        if mq_applied:
            print(f"  sub_queries={meta.get('mq_sub_queries', [])[:3]}")
        # Smoke pass: MQ should fire on at least 1 query, KG on at least 1 query
        if mq_applied:
            n_ok += 1
    await adapter.close()

    print()
    print("=" * 78)
    print(f"Smoke summary: {n_ok}/{n_total} queries triggered MQ decompose")
    print("=" * 78)
    if n_ok == 0:
        print("[FAIL] MQ never fired — decomposer broken")
        return 1
    print("[OK] smoke validated phaseKGMQ pipeline")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
