"""
Tests for nox_mem adapter corpus ingestion.

Tests:
  1. Ingestion populates the eval DB with LoCoMo chunks.
  2. Ingestion is idempotent (re-run does not duplicate rows).
  3. Search after ingest returns gold-format IDs (e.g. "conv-48::D2:13").
  4. Smoke test: setup() + search() run without errors.
  5. teardown() closes connection cleanly.

All tests use a temp DB path (via tmp_path fixture) so they are fully
isolated from any cached eval DB. The LoCoMo corpus is downloaded if not
already cached at the default cache path; subsequent runs reuse the cache.

CRITICAL: tests NEVER touch the prod nox-mem.db. NOX_EVAL_MODE is forced
to "eval" and NOX_EVAL_DB_PATH points to a temp file for every test.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup: make adapters/ and lib/ importable from the test directory.
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent          # test/
_Q4_DIR = _HERE.parent                           # eval/q4-comparison/
sys.path.insert(0, str(_Q4_DIR))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_adapter(tmp_db: Path, monkeypatch: pytest.MonkeyPatch):
    """Return the nox_mem adapter module wired to a temp DB."""
    import importlib

    # Force eval mode + temp DB path for isolation
    monkeypatch.setenv("NOX_EVAL_MODE", "eval")
    monkeypatch.setenv("NOX_EVAL_DB_PATH", str(tmp_db))

    # Reset module state so each test starts fresh
    import adapters.nox_mem as mod
    mod._eval_con = None
    mod._eval_db_path = None

    # Reload to pick up monkeypatched env vars at import time
    importlib.reload(mod)
    return mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def locomo_only_adapter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Adapter with only LoCoMo ingested (faster for most tests)."""
    db = tmp_path / "nox-eval-test.db"
    mod = _make_adapter(db, monkeypatch)
    # Setup with locomo only (avoids downloading LongMemEval in unit tests)
    mod.setup(datasets=["locomo"])
    yield mod
    mod.teardown()


@pytest.fixture()
def both_datasets_adapter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Adapter with both datasets — use for integration tests."""
    db = tmp_path / "nox-eval-both.db"
    mod = _make_adapter(db, monkeypatch)
    mod.setup(datasets=["locomo", "longmemeval"])
    yield mod
    mod.teardown()


# ---------------------------------------------------------------------------
# Test: basic ingestion
# ---------------------------------------------------------------------------


class TestIngestion:
    def test_locomo_chunks_present(self, locomo_only_adapter) -> None:
        """Eval DB must contain LoCoMo chunks after setup."""
        mod = locomo_only_adapter
        assert mod._eval_con is not None, "eval_con not set after setup()"
        con = mod._eval_con
        count = con.execute(
            "SELECT COUNT(*) FROM eval_chunks WHERE dataset='locomo'"
        ).fetchone()[0]
        # LoCoMo10 has ~9k–10k turns; anything < 5k or > 20k indicates drift
        assert count >= 5_000, f"LoCoMo chunk count too low: {count}"
        assert count <= 20_000, f"LoCoMo chunk count suspiciously high: {count}"

    def test_chunk_ids_are_gold_format(self, locomo_only_adapter) -> None:
        """All LoCoMo chunk IDs must match the 'conv-XX::DY:Z' gold format."""
        mod = locomo_only_adapter
        con = mod._eval_con
        rows = con.execute(
            "SELECT id FROM eval_chunks WHERE dataset='locomo' LIMIT 100"
        ).fetchall()
        assert len(rows) > 0, "No rows in eval_chunks"
        import re
        pattern = re.compile(r"^conv-\d+::[A-Z]\d+:\d+$")
        # At least 90% of sampled IDs should match the standard pattern
        matching = sum(1 for (r,) in rows if pattern.match(r))
        assert matching / len(rows) >= 0.9, (
            f"Only {matching}/{len(rows)} IDs match gold format. "
            f"Sample: {[r[0] for r in rows[:5]]}"
        )

    def test_specific_gold_id_present(self, locomo_only_adapter) -> None:
        """The chunk 'conv-48::D2:13' (gold for 'What places give Deborah peace?')
        must be findable in the eval DB."""
        mod = locomo_only_adapter
        con = mod._eval_con
        row = con.execute(
            "SELECT id, text FROM eval_chunks WHERE id=?",
            ("conv-48::D2:13",),
        ).fetchone()
        assert row is not None, (
            "Gold chunk 'conv-48::D2:13' not found in eval DB. "
            "LoCoMo download or parsing may be broken."
        )
        chunk_id, text = row
        assert chunk_id == "conv-48::D2:13"
        assert len(text) > 0, "Gold chunk text is empty"


# ---------------------------------------------------------------------------
# Test: idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_double_setup_does_not_duplicate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Running setup() twice on the same DB must not duplicate rows."""
        db = tmp_path / "nox-idempotent.db"
        monkeypatch.setenv("NOX_EVAL_MODE", "eval")
        monkeypatch.setenv("NOX_EVAL_DB_PATH", str(db))

        import importlib
        import adapters.nox_mem as mod
        mod._eval_con = None
        mod._eval_db_path = None
        importlib.reload(mod)

        mod.setup(datasets=["locomo"])
        count_after_first = mod._eval_con.execute(
            "SELECT COUNT(*) FROM eval_chunks"
        ).fetchone()[0]

        # Close + reopen to simulate a second runner invocation
        mod.teardown()
        mod._eval_con = None
        mod._eval_db_path = None
        importlib.reload(mod)
        monkeypatch.setenv("NOX_EVAL_DB_PATH", str(db))
        mod._eval_db_path = None
        mod._eval_con = None

        mod.setup(datasets=["locomo"])
        count_after_second = mod._eval_con.execute(
            "SELECT COUNT(*) FROM eval_chunks"
        ).fetchone()[0]

        mod.teardown()

        assert count_after_first == count_after_second, (
            f"Row count changed after second setup: "
            f"{count_after_first} → {count_after_second}. "
            "INSERT OR IGNORE idempotency broken."
        )


# ---------------------------------------------------------------------------
# Test: search returns gold-format IDs
# ---------------------------------------------------------------------------


class TestSearch:
    def test_search_returns_list(self, locomo_only_adapter) -> None:
        """search() must return a list (possibly empty, but a list)."""
        mod = locomo_only_adapter
        results = mod.search("peace", k=5)
        assert isinstance(results, list)

    def test_search_item_schema(self, locomo_only_adapter) -> None:
        """Each search result must have id, score, text, source keys."""
        mod = locomo_only_adapter
        results = mod.search("peace nature outdoors", k=3)
        for item in results:
            assert "id" in item, f"Missing 'id' in item: {item}"
            assert "score" in item, f"Missing 'score' in item: {item}"
            assert "text" in item, f"Missing 'text' in item: {item}"
            assert "source" in item, f"Missing 'source' in item: {item}"
            assert isinstance(item["id"], str), f"id not str: {item['id']}"
            assert isinstance(item["score"], float), f"score not float: {item['score']}"

    def test_deborah_peace_query_hits_gold(self, locomo_only_adapter) -> None:
        """'What places give Deborah peace?' must return >= 1 gold chunk ID
        from {conv-48::D2:13, conv-48::D4:34, conv-48::D6:10, conv-48::D19:17}."""
        mod = locomo_only_adapter
        gold_ids = {"conv-48::D2:13", "conv-48::D4:34", "conv-48::D6:10", "conv-48::D19:17"}
        results = mod.search("What places give Deborah peace?", k=10)
        returned_ids = {r["id"] for r in results}
        gold_hits = returned_ids & gold_ids
        assert len(gold_hits) >= 1, (
            f"Expected >= 1 gold hit for Deborah peace query. "
            f"Gold: {gold_ids}. Returned: {returned_ids}"
        )

    def test_search_ids_are_locomo_format(self, locomo_only_adapter) -> None:
        """After locomo-only ingestion, all returned IDs must be locomo-format."""
        import re
        mod = locomo_only_adapter
        results = mod.search("conversation memory", k=10)
        pattern = re.compile(r"^conv-\d+::[A-Z]\d+:\d+$")
        for item in results:
            assert pattern.match(item["id"]), (
                f"Result ID not in gold format: {item['id']}"
            )

    def test_scores_are_positive(self, locomo_only_adapter) -> None:
        """FTS5 bm25 scores are negated to positive. All scores >= 0."""
        mod = locomo_only_adapter
        results = mod.search("talked about cooking recipes food", k=10)
        for item in results:
            assert item["score"] >= 0.0, f"Negative score: {item['score']}"


# ---------------------------------------------------------------------------
# Test: smoke — no errors end-to-end
# ---------------------------------------------------------------------------


class TestSmoke:
    def test_validate_returns_ok(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """validate() must return ok=True in eval mode."""
        monkeypatch.setenv("NOX_EVAL_MODE", "eval")
        import importlib
        import adapters.nox_mem as mod
        importlib.reload(mod)
        result = mod.validate()
        assert result["ok"] is True, f"validate() returned not-ok: {result}"

    def test_teardown_is_safe_to_call_multiple_times(
        self, locomo_only_adapter
    ) -> None:
        """teardown() must be idempotent."""
        mod = locomo_only_adapter
        mod.teardown()  # first call (fixture's yield will call again)
        mod.teardown()  # second call — must not raise

    def test_setup_locomo_then_search_five_queries(
        self, locomo_only_adapter
    ) -> None:
        """Smoke: run 5 representative queries without errors."""
        mod = locomo_only_adapter
        queries = [
            "What places give Deborah peace?",
            "When Dave was a child what did he and his father do",
            "music instruments guitar piano",
            "work job career promotion",
            "family children siblings",
        ]
        for q in queries:
            results = mod.search(q, k=5)
            assert isinstance(results, list), f"search({q!r}) returned non-list"
