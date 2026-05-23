"""
Tests for mem0 adapter ingestion + search contract.

Run:
    python -m pytest eval/q4-comparison/test/test_mem0_ingest.py -v

These tests use unittest.mock to avoid hitting the real Mem0/OpenAI APIs.
The goal is to verify:
  1. setup() calls ingest when expected memory count doesn't match.
  2. setup() skips ingest when count matches (idempotency).
  3. search() maps chunk_id from metadata into result.id.
  4. validate() returns ok=False when OPENAI_API_KEY is missing.
  5. validate() returns ok=False when mem0 is not installed.
  6. _iter_corpus_chunks() delegates to shared corpus_loader (locomo + longmemeval).
  7. _ingest_corpus() calls client.add() with gold-format chunk_id in metadata.
  8. _ingest_corpus() respects MEM0_INGEST_LIMIT cap.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

# Ensure the adapters directory is on the path
HERE = Path(__file__).parent.parent
sys.path.insert(0, str(HERE))


# ---------------------------------------------------------------------------
# Helpers to import the adapter fresh (reset module state between tests)
# ---------------------------------------------------------------------------


def _import_fresh():
    """Import (or reimport) mem0 adapter with clean global state."""
    # Remove cached adapter and corpus_loader modules so patches are fresh
    for mod_name in list(sys.modules.keys()):
        if mod_name in ("adapters.mem0", "lib.corpus_loader"):
            del sys.modules[mod_name]
    return importlib.import_module("adapters.mem0")


def _make_chunk_record(
    chunk_id: str = "conv-48::D2:13",
    text: str = "Alice: I love the beach.",
    dataset: str = "locomo",
    conversation_id: str = "conv-48",
    day: int = 1,
):
    """Return a minimal ChunkRecord for testing."""
    from lib.corpus_loader import ChunkRecord
    return ChunkRecord(
        id=chunk_id,
        text=text,
        dataset=dataset,
        conversation_id=conversation_id,
        day=day,
        metadata={},
    )


# ---------------------------------------------------------------------------
# validate() tests (no external calls — import check + env check only)
# ---------------------------------------------------------------------------


class TestValidate:
    def test_ok_when_installed_and_key_set(self):
        """validate() returns ok=True when mem0 importable + OPENAI_API_KEY set."""
        mod = _import_fresh()
        fake_mem0 = mock.MagicMock()
        fake_mem0.__version__ = "0.1.114"
        with (
            mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}),
            mock.patch.dict(sys.modules, {"mem0": fake_mem0}),
        ):
            result = mod.validate()
        assert result["ok"] is True
        assert result["error"] is None
        assert result["version"] == "0.1.114"

    def test_fail_when_mem0_not_installed(self):
        """validate() returns ok=False when mem0 import raises ImportError."""
        mod = _import_fresh()
        with mock.patch.dict(sys.modules, {"mem0": None}):
            result = mod.validate()
        assert result["ok"] is False
        assert "not installed" in (result["error"] or "")

    def test_fail_when_openai_key_missing(self):
        """validate() returns ok=False when OPENAI_API_KEY env not set."""
        mod = _import_fresh()
        fake_mem0 = mock.MagicMock()
        fake_mem0.__version__ = "0.1.114"
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with (
            mock.patch.dict(os.environ, env, clear=True),
            mock.patch.dict(sys.modules, {"mem0": fake_mem0}),
        ):
            result = mod.validate()
        assert result["ok"] is False
        assert "OPENAI_API_KEY" in (result["error"] or "")


# ---------------------------------------------------------------------------
# setup() idempotency tests
# ---------------------------------------------------------------------------


class TestSetupIdempotency:
    def _make_mock_client(self, existing_count: int):
        """Return a mock Memory() instance with get_all returning N items."""
        client = mock.MagicMock()
        client.get_all.return_value = [{"id": str(i)} for i in range(existing_count)]
        client.add.return_value = {"id": "mem-new"}
        client.search.return_value = []
        return client

    def test_skips_ingest_when_count_matches(self):
        """setup() does NOT call client.add() when existing count matches expected."""
        mod = _import_fresh()
        N = 100
        mock_client = self._make_mock_client(existing_count=N)

        fake_memory_cls = mock.MagicMock(return_value=mock_client)
        fake_memory_cls.from_config = mock.MagicMock(return_value=mock_client)
        fake_mem0 = mock.MagicMock()
        fake_mem0.Memory = fake_memory_cls

        with (
            mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}),
            mock.patch.dict(sys.modules, {"mem0": fake_mem0}),
            mock.patch.object(mod, "_estimate_corpus_size", return_value=N),
            mock.patch.object(mod, "_ingest_corpus") as mock_ingest,
        ):
            mod.setup()

        mock_ingest.assert_not_called()

    def test_ingests_when_count_mismatch(self):
        """setup() calls _ingest_corpus() when existing count doesn't match expected."""
        mod = _import_fresh()
        mock_client = self._make_mock_client(existing_count=0)

        fake_memory_cls = mock.MagicMock(return_value=mock_client)
        fake_memory_cls.from_config = mock.MagicMock(return_value=mock_client)
        fake_mem0 = mock.MagicMock()
        fake_mem0.Memory = fake_memory_cls

        with (
            mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}),
            mock.patch.dict(sys.modules, {"mem0": fake_mem0}),
            mock.patch.object(mod, "_estimate_corpus_size", return_value=1000),
            mock.patch.object(mod, "_ingest_corpus", return_value=1000) as mock_ingest,
        ):
            mod.setup()

        mock_ingest.assert_called_once()

    def test_force_reingest_bypasses_count_check(self):
        """setup() calls _ingest_corpus() even when count matches if MEM0_FORCE_REINGEST=1."""
        mod = _import_fresh()
        N = 100
        mock_client = self._make_mock_client(existing_count=N)

        fake_memory_cls = mock.MagicMock(return_value=mock_client)
        fake_memory_cls.from_config = mock.MagicMock(return_value=mock_client)
        fake_mem0 = mock.MagicMock()
        fake_mem0.Memory = fake_memory_cls

        with (
            mock.patch.dict(
                os.environ,
                {"OPENAI_API_KEY": "sk-test", "MEM0_FORCE_REINGEST": "1"},
            ),
            mock.patch.dict(sys.modules, {"mem0": fake_mem0}),
            mock.patch.object(mod, "_estimate_corpus_size", return_value=N),
            mock.patch.object(mod, "_ingest_corpus", return_value=N) as mock_ingest,
        ):
            mod.setup()

        mock_ingest.assert_called_once()

    def test_setup_singleton(self):
        """setup() is a no-op on second call (singleton guard)."""
        mod = _import_fresh()
        mock_client = self._make_mock_client(existing_count=0)

        fake_memory_cls = mock.MagicMock(return_value=mock_client)
        fake_memory_cls.from_config = mock.MagicMock(return_value=mock_client)
        fake_mem0 = mock.MagicMock()
        fake_mem0.Memory = fake_memory_cls

        with (
            mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}),
            mock.patch.dict(sys.modules, {"mem0": fake_mem0}),
            mock.patch.object(mod, "_estimate_corpus_size", return_value=0),
            mock.patch.object(mod, "_ingest_corpus", return_value=0),
        ):
            mod.setup()
            mod.setup()  # second call

        # from_config should only be called once
        assert fake_memory_cls.from_config.call_count == 1


# ---------------------------------------------------------------------------
# search() result mapping tests
# ---------------------------------------------------------------------------


class TestSearchMapping:
    def test_id_mapped_from_metadata_chunk_id(self):
        """search() uses metadata.chunk_id as the returned id (not Mem0 internal UUID)."""
        mod = _import_fresh()

        raw_mem0_result = [
            {
                "id": "internal-uuid-abc123",
                "memory": "Deborah finds peace at the beach and in her garden.",
                "score": 0.91,
                "metadata": {
                    "chunk_id": "conv-48::D2:13",
                    "dataset": "locomo",
                    "source": "conv-48",
                },
            }
        ]

        mock_client = mock.MagicMock()
        mock_client.search.return_value = raw_mem0_result
        mod._client = mock_client

        results = mod.search("What places give Deborah peace?", k=10)

        assert len(results) == 1
        r = results[0]
        # id must be the chunk_id from metadata, not the Mem0 internal UUID
        assert r["id"] == "conv-48::D2:13"
        assert r["score"] == 0.91
        assert "Deborah" in r["text"]
        assert r["source"] == "conv-48"

    def test_id_falls_back_to_mem0_uuid_when_no_chunk_id(self):
        """search() falls back to Mem0's internal id when metadata.chunk_id absent."""
        mod = _import_fresh()

        raw_mem0_result = [
            {
                "id": "internal-uuid-xyz",
                "memory": "Some memory text.",
                "score": 0.75,
                "metadata": {},  # no chunk_id
            }
        ]

        mock_client = mock.MagicMock()
        mock_client.search.return_value = raw_mem0_result
        mod._client = mock_client

        results = mod.search("test query", k=10)

        assert len(results) == 1
        assert results[0]["id"] == "internal-uuid-xyz"

    def test_search_respects_k_limit(self):
        """search() returns at most k results."""
        mod = _import_fresh()

        raw = [
            {
                "id": f"uuid-{i}",
                "memory": f"memory {i}",
                "score": 1.0 - i * 0.1,
                "metadata": {"chunk_id": f"chunk-{i}"},
            }
            for i in range(20)
        ]

        mock_client = mock.MagicMock()
        mock_client.search.return_value = raw
        mod._client = mock_client

        results = mod.search("query", k=5)
        assert len(results) == 5

    def test_search_empty_result(self):
        """search() handles empty result list gracefully."""
        mod = _import_fresh()

        mock_client = mock.MagicMock()
        mock_client.search.return_value = []
        mod._client = mock_client

        results = mod.search("query", k=10)
        assert results == []

    def test_search_none_result(self):
        """search() handles None from client.search() without crashing."""
        mod = _import_fresh()

        mock_client = mock.MagicMock()
        mock_client.search.return_value = None
        mod._client = mock_client

        results = mod.search("query", k=10)
        assert results == []


# ---------------------------------------------------------------------------
# _iter_corpus_chunks() — shared loader delegation tests
# ---------------------------------------------------------------------------


class TestIterCorpusChunks:
    def test_delegates_to_shared_loaders(self):
        """_iter_corpus_chunks() yields chunks from load_locomo_corpus + load_longmemeval_corpus."""
        mod = _import_fresh()

        locomo_chunk = _make_chunk_record("conv-1::D1:1", dataset="locomo")
        lme_chunk = _make_chunk_record("session-abc", dataset="longmemeval")

        env_clean = {k: v for k, v in os.environ.items() if k != "MEM0_INGEST_LIMIT"}
        with (
            mock.patch.object(mod, "load_locomo_corpus", return_value=iter([locomo_chunk])),
            mock.patch.object(mod, "load_longmemeval_corpus", return_value=iter([lme_chunk])),
            mock.patch.dict(os.environ, env_clean, clear=True),
        ):
            chunks = list(mod._iter_corpus_chunks())

        assert len(chunks) == 2
        assert chunks[0].id == "conv-1::D1:1"
        assert chunks[1].id == "session-abc"

    def test_respects_ingest_limit_within_locomo(self):
        """_iter_corpus_chunks() stops after MEM0_INGEST_LIMIT chunks (all from first dataset)."""
        mod = _import_fresh()

        locomo_chunks = [
            _make_chunk_record(f"conv-1::D1:{i}", dataset="locomo") for i in range(5)
        ]
        lme_chunks = [
            _make_chunk_record(f"session-{i}", dataset="longmemeval") for i in range(5)
        ]

        with (
            mock.patch.object(mod, "load_locomo_corpus", return_value=iter(locomo_chunks)),
            mock.patch.object(mod, "load_longmemeval_corpus", return_value=iter(lme_chunks)),
            mock.patch.dict(os.environ, {"MEM0_INGEST_LIMIT": "3"}),
        ):
            chunks = list(mod._iter_corpus_chunks())

        assert len(chunks) == 3
        assert all(c.dataset == "locomo" for c in chunks)

    def test_limit_spans_both_datasets(self):
        """_iter_corpus_chunks() limit spans across both loaders."""
        mod = _import_fresh()

        locomo_chunks = [_make_chunk_record(f"conv-1::D1:{i}", dataset="locomo") for i in range(2)]
        lme_chunks = [_make_chunk_record(f"session-{i}", dataset="longmemeval") for i in range(5)]

        with (
            mock.patch.object(mod, "load_locomo_corpus", return_value=iter(locomo_chunks)),
            mock.patch.object(mod, "load_longmemeval_corpus", return_value=iter(lme_chunks)),
            mock.patch.dict(os.environ, {"MEM0_INGEST_LIMIT": "4"}),
        ):
            chunks = list(mod._iter_corpus_chunks())

        assert len(chunks) == 4
        locomo_count = sum(1 for c in chunks if c.dataset == "locomo")
        lme_count = sum(1 for c in chunks if c.dataset == "longmemeval")
        assert locomo_count == 2
        assert lme_count == 2


# ---------------------------------------------------------------------------
# _ingest_corpus() — gold-format chunk_id in metadata + skip_llm flag
# ---------------------------------------------------------------------------


class TestIngestCorpus:
    def test_ingest_calls_add_with_gold_format_chunk_id(self):
        """_ingest_corpus() stores chunk.id as metadata.chunk_id in client.add()."""
        mod = _import_fresh()

        chunks = [
            _make_chunk_record(
                "conv-48::D2:13", text="Alice: Beach peace.",
                dataset="locomo", conversation_id="conv-48",
            ),
            _make_chunk_record(
                "session-xyz", text="user: Korean food.",
                dataset="longmemeval", conversation_id="q1",
            ),
        ]

        mock_client = mock.MagicMock()
        mock_client.add.return_value = {"id": "mem-1"}

        with (
            mock.patch.object(mod, "_iter_corpus_chunks", return_value=iter(chunks)),
            mock.patch.dict(os.environ, {"MEM0_SKIP_LLM_EXTRACTION": "1"}, clear=False),
        ):
            count = mod._ingest_corpus(mock_client, "q4-eval")

        assert count == 2
        assert mock_client.add.call_count == 2

        # First call: gold-format locomo chunk_id
        first_kwargs = mock_client.add.call_args_list[0][1]
        assert first_kwargs["metadata"]["chunk_id"] == "conv-48::D2:13"
        assert first_kwargs["metadata"]["source"] == "conv-48"
        assert first_kwargs["infer"] is False  # MEM0_SKIP_LLM_EXTRACTION=1

        # Second call: longmemeval session_id format
        second_kwargs = mock_client.add.call_args_list[1][1]
        assert second_kwargs["metadata"]["chunk_id"] == "session-xyz"
        assert second_kwargs["metadata"]["dataset"] == "longmemeval"

    def test_ingest_uses_infer_true_when_skip_disabled(self):
        """_ingest_corpus() passes infer=True when MEM0_SKIP_LLM_EXTRACTION=0."""
        mod = _import_fresh()

        chunks = [_make_chunk_record("conv-1::D1:1")]
        mock_client = mock.MagicMock()
        mock_client.add.return_value = {"id": "mem-1"}

        with (
            mock.patch.object(mod, "_iter_corpus_chunks", return_value=iter(chunks)),
            mock.patch.dict(os.environ, {"MEM0_SKIP_LLM_EXTRACTION": "0"}, clear=False),
        ):
            mod._ingest_corpus(mock_client, "q4-eval")

        call_kwargs = mock_client.add.call_args_list[0][1]
        assert call_kwargs["infer"] is True

    def test_ingest_returns_zero_on_empty_corpus(self):
        """_ingest_corpus() returns 0 when corpus_loader yields nothing."""
        mod = _import_fresh()

        mock_client = mock.MagicMock()

        with mock.patch.object(mod, "_iter_corpus_chunks", return_value=iter([])):
            count = mod._ingest_corpus(mock_client, "q4-eval")

        assert count == 0
        mock_client.add.assert_not_called()

    def test_ingest_tolerates_partial_errors(self):
        """_ingest_corpus() counts only successful adds; continues on error."""
        mod = _import_fresh()

        chunks = [_make_chunk_record(f"conv-1::D1:{i}") for i in range(5)]
        mock_client = mock.MagicMock()
        mock_client.add.side_effect = [
            {"id": "ok"},
            RuntimeError("embed fail"),
            {"id": "ok"},
            RuntimeError("embed fail"),
            {"id": "ok"},
        ]

        with mock.patch.object(mod, "_iter_corpus_chunks", return_value=iter(chunks)):
            count = mod._ingest_corpus(mock_client, "q4-eval")

        assert count == 3  # 5 attempts, 2 errors

    def test_ingest_chunk_id_matches_gold_format(self):
        """chunk_id stored in metadata must match gold_chunk_ids format from dry-run-sample.json."""
        mod = _import_fresh()

        # The gold ID format for LoCoMo is `{sample_id}::{dia_id}` — verify exact string preserved
        gold_id = "conv-48::D2:13"
        chunks = [_make_chunk_record(gold_id, dataset="locomo")]

        mock_client = mock.MagicMock()
        mock_client.add.return_value = {"id": "mem-1"}

        with mock.patch.object(mod, "_iter_corpus_chunks", return_value=iter(chunks)):
            mod._ingest_corpus(mock_client, "q4-eval")

        stored_chunk_id = mock_client.add.call_args_list[0][1]["metadata"]["chunk_id"]
        assert stored_chunk_id == gold_id, (
            f"chunk_id stored in mem0 metadata ({stored_chunk_id!r}) "
            f"must match gold format ({gold_id!r})"
        )


# ---------------------------------------------------------------------------
# teardown test
# ---------------------------------------------------------------------------


class TestTeardown:
    def test_teardown_resets_client(self):
        """teardown() sets _client back to None."""
        mod = _import_fresh()
        mod._client = mock.MagicMock()
        mod.teardown()
        assert mod._client is None
