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
  6. _load_locomo_corpus() parses the expected chunk format.
  7. _load_longmemeval_corpus() parses the expected chunk format.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
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
    mod_name = "adapters.mem0"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    return importlib.import_module(mod_name)


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
        # Simulate corpus files absent so expected == 0, but existing == 0 too.
        # For the "count matches" path, patch _estimate_corpus_size to return N
        # and get_all to return N items.
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
        # existing = 0, expected = 1000 → triggers ingest
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
# Corpus loader unit tests (file-based, no network)
# ---------------------------------------------------------------------------


SAMPLE_LOCOMO = {
    "sample_id": "conv-48",
    "session_1": [
        {"dia_id": "D1:1", "speaker": "Alice", "text": "I love the beach."},
        {"dia_id": "D1:2", "speaker": "Bob", "text": "Me too, it is peaceful."},
    ],
    "session_2": [
        {"dia_id": "D2:13", "speaker": "Alice", "text": "The garden gives me peace too."},
    ],
}

SAMPLE_LONGMEMEVAL = [
    {
        "question_id": "6aeb4375",
        "question_type": "knowledge-update",
        "question": "How many Korean restaurants have I tried?",
        "answer": "four",
        "haystack_session_ids": ["answer_3f9693b7_1", "answer_3f9693b7_2"],
        "haystack_dates": ["2023/10/01", "2023/10/05"],
        "haystack_sessions": [
            [
                {"role": "user", "content": "I tried a new Korean place today."},
                {"role": "assistant", "content": "How was it?"},
            ],
            [
                {"role": "user", "content": "Fourth Korean restaurant this month!"},
            ],
        ],
        "answer_session_ids": ["answer_3f9693b7_1", "answer_3f9693b7_2"],
    }
]


class TestLocomotCorpusLoader:
    def test_loads_turns_correctly(self, tmp_path):
        """_load_locomo_corpus() produces per-turn chunks with correct IDs."""
        mod = _import_fresh()

        data_file = tmp_path / "locomo10.json"
        data_file.write_text(json.dumps([SAMPLE_LOCOMO]))

        with mock.patch.object(mod, "_LOCOMO_DATA", data_file):
            chunks = mod._load_locomo_corpus()

        assert len(chunks) == 3
        ids = [c["id"] for c in chunks]
        assert "conv-48::D1:1" in ids
        assert "conv-48::D1:2" in ids
        assert "conv-48::D2:13" in ids

        # Check text format: "speaker: text"
        c = next(c for c in chunks if c["id"] == "conv-48::D1:1")
        assert c["text"] == "Alice: I love the beach."
        assert c["dataset"] == "locomo"

    def test_returns_empty_when_file_missing(self):
        """_load_locomo_corpus() returns [] when data file doesn't exist."""
        mod = _import_fresh()
        missing = Path("/nonexistent/path/locomo10.json")
        with mock.patch.object(mod, "_LOCOMO_DATA", missing):
            chunks = mod._load_locomo_corpus()
        assert chunks == []

    def test_skips_turns_with_empty_text(self, tmp_path):
        """_load_locomo_corpus() skips turns where text is empty."""
        mod = _import_fresh()

        conv = {
            "sample_id": "conv-1",
            "session_1": [
                {"dia_id": "D1:1", "speaker": "Alice", "text": ""},
                {"dia_id": "D1:2", "speaker": "Bob", "text": "Hello."},
            ],
        }
        data_file = tmp_path / "locomo10.json"
        data_file.write_text(json.dumps([conv]))

        with mock.patch.object(mod, "_LOCOMO_DATA", data_file):
            chunks = mod._load_locomo_corpus()

        assert len(chunks) == 1
        assert chunks[0]["id"] == "conv-1::D1:2"


class TestLongMemEvalCorpusLoader:
    def test_loads_sessions_correctly(self, tmp_path):
        """_load_longmemeval_corpus() produces per-session chunks with correct IDs."""
        mod = _import_fresh()

        data_file = tmp_path / "longmemeval_oracle.json"
        data_file.write_text(json.dumps(SAMPLE_LONGMEMEVAL))

        with mock.patch.object(mod, "_LONGMEMEVAL_DATA", data_file):
            chunks = mod._load_longmemeval_corpus()

        assert len(chunks) == 2
        ids = [c["id"] for c in chunks]
        assert "answer_3f9693b7_1" in ids
        assert "answer_3f9693b7_2" in ids

        # Text should have header + content
        c = next(c for c in chunks if c["id"] == "answer_3f9693b7_1")
        assert "[session_id=answer_3f9693b7_1" in c["text"]
        assert "Korean" in c["text"]
        assert c["dataset"] == "longmemeval"

    def test_returns_empty_when_file_missing(self):
        """_load_longmemeval_corpus() returns [] when data file doesn't exist."""
        mod = _import_fresh()
        missing = Path("/nonexistent/path/longmemeval_oracle.json")
        with mock.patch.object(mod, "_LONGMEMEVAL_DATA", missing):
            chunks = mod._load_longmemeval_corpus()
        assert chunks == []

    def test_deduplicates_sessions(self, tmp_path):
        """_load_longmemeval_corpus() deduplicates sessions shared across questions."""
        mod = _import_fresh()

        # Two questions sharing the same session_id
        data = [
            {
                "question_id": "q1",
                "haystack_session_ids": ["shared-session"],
                "haystack_dates": ["2023/10/01"],
                "haystack_sessions": [
                    [{"role": "user", "content": "Shared content."}]
                ],
                "answer_session_ids": ["shared-session"],
            },
            {
                "question_id": "q2",
                "haystack_session_ids": ["shared-session"],
                "haystack_dates": ["2023/10/01"],
                "haystack_sessions": [
                    [{"role": "user", "content": "Shared content."}]
                ],
                "answer_session_ids": ["shared-session"],
            },
        ]
        data_file = tmp_path / "longmemeval_oracle.json"
        data_file.write_text(json.dumps(data))

        with mock.patch.object(mod, "_LONGMEMEVAL_DATA", data_file):
            chunks = mod._load_longmemeval_corpus()

        # shared-session appears only once
        assert len(chunks) == 1
        assert chunks[0]["id"] == "shared-session"


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
