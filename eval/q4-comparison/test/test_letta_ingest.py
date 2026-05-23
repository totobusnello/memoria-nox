"""
Tests for Letta adapter ingestion + search contract.

Run:
    python -m pytest eval/q4-comparison/test/test_letta_ingest.py -v

These tests mock the Letta SDK so they don't require a running letta server
or OPENAI_API_KEY. Focus areas:
  1. validate() — env + import check
  2. setup() — agent reuse vs create
  3. ingest_corpus() — id-map built, idempotent skip, error counting
  4. search() — passage_id -> nox_id round-trip via reverse map
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

HERE = Path(__file__).parent.parent
sys.path.insert(0, str(HERE))


def _import_fresh():
    """Import (or reimport) letta adapter with clean global state."""
    mod_name = "adapters.letta"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    return importlib.import_module(mod_name)


# ---------------------------------------------------------------------------
# validate()
# ---------------------------------------------------------------------------


class TestValidate:
    def test_fail_when_letta_not_installed(self):
        mod = _import_fresh()
        with mock.patch.dict(sys.modules, {"letta": None}):
            result = mod.validate()
        assert result["ok"] is False
        assert "not installed" in (result["error"] or "")

    def test_fail_when_openai_key_missing(self):
        mod = _import_fresh()
        fake_letta = mock.MagicMock()
        fake_letta.__version__ = "0.6.6"
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with (
            mock.patch.dict(os.environ, env, clear=True),
            mock.patch.dict(sys.modules, {"letta": fake_letta}),
        ):
            result = mod.validate()
        assert result["ok"] is False
        assert "OPENAI_API_KEY" in (result["error"] or "")

    def test_ok_when_installed_and_key_set(self):
        mod = _import_fresh()
        fake_letta = mock.MagicMock()
        fake_letta.__version__ = "0.6.6"
        with (
            mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}),
            mock.patch.dict(sys.modules, {"letta": fake_letta}),
        ):
            result = mod.validate()
        assert result["ok"] is True
        assert result["version"] == "0.6.6"


# ---------------------------------------------------------------------------
# setup()
# ---------------------------------------------------------------------------


def _make_mock_letta_client(existing_agents: list | None = None, archival_count: int = 0):
    """Build a mock letta_client.Letta() instance."""
    client = mock.MagicMock()
    if existing_agents is None:
        existing_agents = []
    client.agents.list.return_value = existing_agents
    new_agent = mock.MagicMock()
    new_agent.id = "agent-new-uuid"
    client.agents.create.return_value = new_agent
    client.agents.archival_memory_list.return_value = [
        mock.MagicMock(id=f"passage-{i}") for i in range(archival_count)
    ]
    return client


class TestSetup:
    def test_reuses_existing_agent(self, tmp_path):
        mod = _import_fresh()
        existing = mock.MagicMock()
        existing.id = "agent-existing"
        client = _make_mock_letta_client(existing_agents=[existing])

        fake_letta_client_mod = mock.MagicMock()
        fake_letta_client_mod.Letta = mock.MagicMock(return_value=client)

        with (
            mock.patch.dict(sys.modules, {"letta_client": fake_letta_client_mod}),
            mock.patch.object(mod, "_state_path", return_value=tmp_path / "id-map.json"),
        ):
            mod.setup()

        assert mod._agent_id == "agent-existing"
        client.agents.create.assert_not_called()

    def test_creates_new_agent_when_absent(self, tmp_path):
        mod = _import_fresh()
        client = _make_mock_letta_client(existing_agents=[])
        fake_letta_client_mod = mock.MagicMock()
        fake_letta_client_mod.Letta = mock.MagicMock(return_value=client)

        with (
            mock.patch.dict(sys.modules, {"letta_client": fake_letta_client_mod}),
            mock.patch.object(mod, "_state_path", return_value=tmp_path / "id-map.json"),
        ):
            mod.setup()

        assert mod._agent_id == "agent-new-uuid"
        client.agents.create.assert_called_once()

    def test_setup_is_singleton(self, tmp_path):
        mod = _import_fresh()
        client = _make_mock_letta_client()
        fake_letta_client_mod = mock.MagicMock()
        fake_letta_client_mod.Letta = mock.MagicMock(return_value=client)

        with (
            mock.patch.dict(sys.modules, {"letta_client": fake_letta_client_mod}),
            mock.patch.object(mod, "_state_path", return_value=tmp_path / "id-map.json"),
        ):
            mod.setup()
            mod.setup()  # second call

        assert fake_letta_client_mod.Letta.call_count == 1


# ---------------------------------------------------------------------------
# ingest_corpus()
# ---------------------------------------------------------------------------


class TestIngestCorpus:
    def _setup_client(self, mod, tmp_path, archival_count: int = 0):
        """Helper: install a mock client into the adapter module."""
        client = _make_mock_letta_client(archival_count=archival_count)
        passage = mock.MagicMock()
        passage.id = "passage-new-uuid"
        client.agents.archival_memory_insert.return_value = passage
        mod._client = client
        mod._agent_id = "agent-test"
        mod._id_map = {}
        mod._reverse_id_map = {}
        with mock.patch.object(mod, "_state_path", return_value=tmp_path / "id-map.json"):
            yield client

    def test_empty_chunks_returns_noop(self, tmp_path):
        mod = _import_fresh()
        gen = self._setup_client(mod, tmp_path)
        client = next(gen)
        result = mod.ingest_corpus([])
        assert result["total"] == 0
        assert result["ingested"] == 0
        client.agents.archival_memory_insert.assert_not_called()

    def test_inserts_chunks_and_builds_id_map(self, tmp_path):
        mod = _import_fresh()
        gen = self._setup_client(mod, tmp_path)
        client = next(gen)

        # Each insert returns an incrementing passage id
        passages = [mock.MagicMock(id=f"passage-{i}") for i in range(3)]
        client.agents.archival_memory_insert.side_effect = passages

        chunks = [
            {"id": "conv-1::D1:1", "text": "Alice: hello"},
            {"id": "conv-1::D1:2", "text": "Bob: hi"},
            {"id": "conv-1::D1:3", "text": "Alice: how are you"},
        ]
        with mock.patch.object(mod, "_state_path", return_value=tmp_path / "id-map.json"):
            result = mod.ingest_corpus(chunks)

        assert result["ingested"] == 3
        assert result["errors"] == 0
        assert mod._id_map["conv-1::D1:1"] == "passage-0"
        assert mod._reverse_id_map["passage-0"] == "conv-1::D1:1"
        assert mod._reverse_id_map["passage-2"] == "conv-1::D1:3"

    def test_idempotent_skip_when_count_and_map_match(self, tmp_path):
        mod = _import_fresh()
        gen = self._setup_client(mod, tmp_path, archival_count=3)
        client = next(gen)
        # Pre-populate id-map matching the input ids
        mod._id_map = {
            "conv-1::D1:1": "passage-0",
            "conv-1::D1:2": "passage-1",
            "conv-1::D1:3": "passage-2",
        }
        mod._reverse_id_map = {v: k for k, v in mod._id_map.items()}

        chunks = [
            {"id": "conv-1::D1:1", "text": "Alice: hello"},
            {"id": "conv-1::D1:2", "text": "Bob: hi"},
            {"id": "conv-1::D1:3", "text": "Alice: how are you"},
        ]
        with mock.patch.object(mod, "_state_path", return_value=tmp_path / "id-map.json"):
            result = mod.ingest_corpus(chunks)

        assert result["ingested"] == 0
        assert result["skipped"] == 3
        assert result["mode"] == "idempotent-skip"
        client.agents.archival_memory_insert.assert_not_called()

    def test_counts_errors_on_insert_failure(self, tmp_path):
        mod = _import_fresh()
        gen = self._setup_client(mod, tmp_path)
        client = next(gen)
        # First insert succeeds, second raises
        client.agents.archival_memory_insert.side_effect = [
            mock.MagicMock(id="passage-0"),
            RuntimeError("server returned 500"),
        ]

        chunks = [
            {"id": "conv-1::D1:1", "text": "ok"},
            {"id": "conv-1::D1:2", "text": "fail"},
        ]
        with mock.patch.object(mod, "_state_path", return_value=tmp_path / "id-map.json"):
            result = mod.ingest_corpus(chunks)

        assert result["ingested"] == 1
        assert result["errors"] == 1

    def test_skips_chunks_with_empty_text(self, tmp_path):
        mod = _import_fresh()
        gen = self._setup_client(mod, tmp_path)
        client = next(gen)
        client.agents.archival_memory_insert.return_value = mock.MagicMock(id="passage-0")

        chunks = [
            {"id": "c1", "text": ""},
            {"id": "", "text": "no id"},
            {"id": "c3", "text": "valid"},
        ]
        with mock.patch.object(mod, "_state_path", return_value=tmp_path / "id-map.json"):
            result = mod.ingest_corpus(chunks)

        assert result["ingested"] == 1
        assert result["errors"] == 2

    def test_id_map_persists_to_disk(self, tmp_path):
        mod = _import_fresh()
        state_file = tmp_path / "id-map.json"
        gen = self._setup_client(mod, tmp_path)
        client = next(gen)
        client.agents.archival_memory_insert.return_value = mock.MagicMock(id="passage-X")

        chunks = [{"id": "nox-1", "text": "hello"}]
        with mock.patch.object(mod, "_state_path", return_value=state_file):
            mod.ingest_corpus(chunks)

        assert state_file.exists()
        on_disk = json.loads(state_file.read_text())
        assert on_disk["nox-1"] == "passage-X"


# ---------------------------------------------------------------------------
# search()
# ---------------------------------------------------------------------------


class TestSearchRoundTrip:
    def test_passage_id_mapped_back_to_nox_id(self):
        mod = _import_fresh()
        client = mock.MagicMock()
        # archival_memory_search returns passages with server uuids
        client.agents.archival_memory_search.return_value = [
            mock.MagicMock(id="passage-abc", score=0.91, text="Deborah: beach gives me peace"),
            mock.MagicMock(id="passage-xyz", score=0.45, text="Bob: walks too"),
        ]
        mod._client = client
        mod._agent_id = "agent-test"
        mod._id_map = {"conv-48::D2:13": "passage-abc"}
        mod._reverse_id_map = {"passage-abc": "conv-48::D2:13"}

        results = mod.search("places that give peace", k=10)
        assert results[0]["id"] == "conv-48::D2:13"  # round-tripped
        assert results[0]["score"] == 0.91
        assert results[1]["id"] == "passage-xyz"  # not in map, fallback

    def test_search_respects_k(self):
        mod = _import_fresh()
        client = mock.MagicMock()
        client.agents.archival_memory_search.return_value = [
            mock.MagicMock(id=f"p-{i}", score=1.0 - i * 0.1, text=f"t{i}")
            for i in range(20)
        ]
        mod._client = client
        mod._agent_id = "agent-test"
        mod._reverse_id_map = {}
        results = mod.search("q", k=5)
        assert len(results) == 5

    def test_search_handles_empty_or_none(self):
        mod = _import_fresh()
        client = mock.MagicMock()
        client.agents.archival_memory_search.return_value = None
        mod._client = client
        mod._agent_id = "agent-test"
        mod._reverse_id_map = {}
        assert mod.search("q", k=10) == []


# ---------------------------------------------------------------------------
# teardown
# ---------------------------------------------------------------------------


class TestTeardown:
    def test_resets_client_and_agent(self):
        mod = _import_fresh()
        mod._client = mock.MagicMock()
        mod._agent_id = "x"
        mod.teardown()
        assert mod._client is None
        assert mod._agent_id is None
