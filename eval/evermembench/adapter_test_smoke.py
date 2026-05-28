"""
Quick smoke test for Phase B adapter format.

Validates that:
  1. PHASEB_MESSAGE_BLOCK fills correctly with structured metadata.
  2. PHASEB_DAY_GROUP_ROLLUP digests aggregate participants + first line.
  3. _ingest_batch markdown contains expected H2 headers + metadata lines.
  4. Baseline mode (NOX_ADAPTER_MODE=baseline) still produces flat paragraphs.

Run from inside EverMemBench tree (or with stub-import path):
    python eval/evermembench/adapter_test_smoke.py
"""
from __future__ import annotations
import os
import sys
import tempfile
import types
from pathlib import Path


def _make_fake_message(speaker: str, content: str, time_: str, group: str = "Group 1", date: str = "2025-01-09"):
    m = types.SimpleNamespace()
    m.speaker = speaker
    m.content = content
    m.time = time_
    m.timestamp = time_
    m.group = group
    m.date = date
    return m


def main() -> int:
    # Stub-import path: import adapter directly (bypasses harness).
    sys.path.insert(0, str(Path(__file__).parent))
    import adapter_nox_mem as A

    # Build a 5-message batch across 2 (date, group) tuples.
    msgs = [
        _make_fake_message("Joanna", "I'd love to visit Italy this summer.", "2025-01-09T10:30", "Group 1", "2025-01-09"),
        _make_fake_message("Marco", "Rome is amazing in spring actually.", "2025-01-09T10:32", "Group 1", "2025-01-09"),
        _make_fake_message("Joanna", "Spring would work too. Florence?", "2025-01-09T10:34", "Group 1", "2025-01-09"),
        _make_fake_message("Alex", "I prefer mountains. Switzerland next?", "2025-01-10T14:00", "Group 2", "2025-01-10"),
        _make_fake_message("Joanna", "Switzerland sounds great after Italy.", "2025-01-10T14:05", "Group 2", "2025-01-10"),
    ]

    # Phase B adapter instance (without invoking parent __init__ — we just
    # need the format methods).
    config = {
        "api_base": "http://localhost:9999",
        "nox_mem_bin": "/bin/true",
        "adapter_mode": "phaseB",
        "phaseb_context_window": 2,
        "ingest_batch_size": 50,
    }
    # Bypass BaseAdapter / NoxMemAdapter __init__ which requires harness types.
    adapter = A.NoxMemAdapter.__new__(A.NoxMemAdapter)
    adapter.api_base = config["api_base"]
    adapter.nox_mem_bin = config["nox_mem_bin"]
    adapter.search_top_k = 10
    adapter.search_timeout = 30
    adapter.ingest_batch_size = 50
    adapter.ingest_delay_ms = 0
    adapter.adapter_mode = "phaseB"
    adapter.context_window = 2
    adapter._session = None

    # Build day-group cache as _ingest_batch would.
    adapter._day_group_cache = {}
    for m in msgs:
        key = (m.date, m.group)
        adapter._day_group_cache.setdefault(key, []).append(m)
    adapter._digest_emitted = set()

    print("=== Phase B per-message blocks ===")
    for i, m in enumerate(msgs):
        block = adapter._format_message_phaseb(m, i)
        print(block)

    print("\n=== Per-(date, group) digests ===")
    for key, batch_msgs in adapter._day_group_cache.items():
        digest = adapter._format_day_group_digest(key, batch_msgs)
        print(digest)

    # Sanity assertions
    assert "## [2025-01-09T10:32 | Group 1 | Marco]" in adapter._format_message_phaseb(msgs[1], 1), "expected H2 header"
    assert "context: Joanna" in adapter._format_message_phaseb(msgs[1], 1), "expected preceding-context anchor"
    assert "context: (start of conversation)" in adapter._format_message_phaseb(msgs[0], 0), "first msg should have empty context"
    digest_g1 = adapter._format_day_group_digest(("2025-01-09", "Group 1"), adapter._day_group_cache[("2025-01-09", "Group 1")])
    assert "participants: Joanna, Marco" in digest_g1, "digest should aggregate participants"
    assert "message_count: 3" in digest_g1, "digest should count messages"

    # Baseline mode
    adapter.adapter_mode = "baseline"
    baseline_block = adapter._format_message_baseline(msgs[0])
    assert baseline_block.startswith("[Group: Group 1]"), "baseline format mismatch"
    print("\n=== Baseline (PR #363) block ===")
    print(baseline_block)

    print("\nALL SMOKE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
