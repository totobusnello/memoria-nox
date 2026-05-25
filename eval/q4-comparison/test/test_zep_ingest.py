"""
Tests for the Zep adapter ingestion pipeline.

Two test tiers:
  1. UNIT  — no Zep daemon needed. Tests pure-Python logic (ID mapping,
             session naming, conv_id derivation, validate() static checks).
  2. INTEGRATION — requires Zep OSS running at ZEP_API_URL (default
             http://127.0.0.1:8000). Skipped automatically if not reachable.

Run unit only (fast, CI-safe):
    pytest test/test_zep_ingest.py -m "not integration" -v

Run all (after docker compose up):
    pytest test/test_zep_ingest.py -v

Environment:
    ZEP_API_URL  — override Zep base URL (default http://127.0.0.1:8000)

Adapter API (updated 2026-05-24 for zep-python==1.5.0 + Zep OSS 0.27.2):
    - ZepClient(base_url, api_key)
    - client.memory.add_session(Session(session_id, metadata))
    - client.memory.add_memory(session_id, Memory(messages=[Message,...]))
    - client.memory.search_memory(session_id, MemorySearchPayload(text), limit)
      ^ scoped per session; adapter fans out across all _sessions
    - r.message comes back as dict, r.dist is cosine similarity (higher=closer)
"""

from __future__ import annotations

import importlib
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Make sure adapters/ is importable regardless of cwd.
HERE = Path(__file__).parent
ADAPTERS_DIR = HERE.parent
sys.path.insert(0, str(ADAPTERS_DIR))

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _zep_reachable() -> bool:
    """Return True if Zep /healthz responds 200."""
    try:
        import requests

        base = os.environ.get("ZEP_API_URL", "http://127.0.0.1:8000").rstrip("/")
        resp = requests.get(f"{base}/healthz", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False


ZEP_UP = _zep_reachable()
integration = pytest.mark.skipif(not ZEP_UP, reason="Zep OSS not running — skipping integration")


# ---------------------------------------------------------------------------
# Fresh adapter import (clears module-level state between tests)
# ---------------------------------------------------------------------------


def _fresh_adapter() -> types.ModuleType:
    """Import (or re-import) adapters.zep with clean module-level state."""
    if "adapters.zep" in sys.modules:
        del sys.modules["adapters.zep"]
    mod = importlib.import_module("adapters.zep")
    # Reset mutable module globals
    mod._client = None
    mod._sessions.clear()
    return mod


def _mock_message(content: str, metadata: dict | None = None, uuid: str = "u-1") -> dict:
    """Build a dict-shaped message matching zep-python==1.5.0 search response."""
    return {
        "uuid": uuid,
        "role": "user",
        "content": content,
        "metadata": metadata or {},
    }


def _mock_search_result(message_dict: dict, dist: float = 0.9) -> MagicMock:
    """Build a MemorySearchResult-shaped mock matching the 1.5.0 SDK."""
    r = MagicMock()
    r.message = message_dict
    r.dist = dist
    return r


# ---------------------------------------------------------------------------
# Unit tests — no daemon required
# ---------------------------------------------------------------------------


class TestConvIdDerivation(unittest.TestCase):
    """_conv_id_from_gold_id pure-function tests."""

    def setUp(self):
        self.zep = _fresh_adapter()

    def test_locomo_standard(self):
        self.assertEqual(self.zep._conv_id_from_gold_id("conv-48::D2:13"), "conv-48")

    def test_locomo_deeper(self):
        self.assertEqual(
            self.zep._conv_id_from_gold_id("locomo::conv-50::chunk-7"),
            "locomo::conv-50",
        )

    def test_no_separator(self):
        """Single-segment IDs return themselves as the conversation group."""
        self.assertEqual(self.zep._conv_id_from_gold_id("flat-chunk-01"), "flat-chunk-01")

    def test_longmemeval_format(self):
        self.assertEqual(
            self.zep._conv_id_from_gold_id("conv-26::q6::answer-chunk-3"),
            "conv-26::q6",
        )


class TestSafeSessionId(unittest.TestCase):
    """Session IDs must be alphanum + _- only; deterministic from conv_id."""

    def test_simple_pass_through(self):
        zep = _fresh_adapter()
        self.assertEqual(zep._safe_session_id("conv-48"), "q4-conv-48")

    def test_special_chars_sanitised(self):
        zep = _fresh_adapter()
        # "::" must collapse to "__"
        self.assertEqual(zep._safe_session_id("locomo::conv-50"), "q4-locomo__conv-50")


class TestSessionNaming(unittest.TestCase):
    """Session IDs must be deterministic from conv_id."""

    def test_session_name_prefix(self):
        """Ensure naming convention: q4-<conv_id> for LoCoMo-style ids."""
        zep = _fresh_adapter()
        zep._wait_for_embeddings = lambda *a, **kw: None  # skip docker poll in unit test

        mock_client = MagicMock()
        # get_session raises to simulate "not found" -> triggers add_session
        mock_client.memory.get_session.side_effect = Exception("not found")
        mock_client.memory.add_session.return_value = MagicMock()
        mock_client.memory.add_memory.return_value = MagicMock()
        zep._client = mock_client

        chunks = [
            {"id": "conv-48::D2:13", "text": "Deborah finds peace in nature."},
            {"id": "conv-48::D4:34", "text": "Mountains give her serenity."},
        ]
        result = zep.ingest_corpus(chunks)

        calls = mock_client.memory.add_session.call_args_list
        self.assertEqual(len(calls), 1)
        # add_session takes a Session positional arg in 1.5.0
        session_arg = calls[0].args[0]
        self.assertEqual(session_arg.session_id, "q4-conv-48")

        self.assertEqual(result["sessions_created"], 1)
        self.assertEqual(result["messages_added"], 2)
        self.assertEqual(result["errors"], 0)


class TestIdempotentSessionCreation(unittest.TestCase):
    """ingest_corpus must not recreate sessions that already exist."""

    def test_existing_session_not_recreated(self):
        """If get_session succeeds, add_session should NOT be called."""
        zep = _fresh_adapter()
        zep._wait_for_embeddings = lambda *a, **kw: None

        mock_client = MagicMock()
        mock_client.memory.get_session.return_value = MagicMock()
        mock_client.memory.add_memory.return_value = MagicMock()
        zep._client = mock_client

        chunks = [{"id": "conv-48::D2:13", "text": "Deborah finds peace in nature."}]
        zep.ingest_corpus(chunks)

        mock_client.memory.add_session.assert_not_called()
        mock_client.memory.add_memory.assert_called_once()


class TestGoldIdRoundTrip(unittest.TestCase):
    """Gold IDs stored in metadata must survive the ingest round-trip."""

    def test_metadata_contains_gold_id(self):
        """Messages added to Zep must include gold_id in metadata."""
        zep = _fresh_adapter()
        zep._wait_for_embeddings = lambda *a, **kw: None

        mock_client = MagicMock()
        mock_client.memory.get_session.side_effect = Exception("not found")
        mock_client.memory.add_session.return_value = MagicMock()
        mock_client.memory.add_memory.return_value = MagicMock()
        zep._client = mock_client

        gold_id = "conv-48::D2:13"
        chunks = [{"id": gold_id, "text": "Deborah finds peace in nature."}]
        zep.ingest_corpus(chunks)

        add_calls = mock_client.memory.add_memory.call_args_list
        self.assertEqual(len(add_calls), 1)
        # signature: (session_id, Memory(messages=...))
        memory_arg = add_calls[0].args[1]
        self.assertTrue(len(memory_arg.messages) > 0, "Expected at least one message")
        msg = memory_arg.messages[0]
        meta = msg.metadata
        self.assertIn("gold_id", meta)
        self.assertEqual(meta["gold_id"], gold_id)


class TestMultipleConversationGroups(unittest.TestCase):
    """Chunks from different conversations must land in separate sessions."""

    def test_two_convs_two_sessions(self):
        zep = _fresh_adapter()
        zep._wait_for_embeddings = lambda *a, **kw: None

        mock_client = MagicMock()
        mock_client.memory.get_session.side_effect = Exception("not found")
        mock_client.memory.add_session.return_value = MagicMock()
        mock_client.memory.add_memory.return_value = MagicMock()
        zep._client = mock_client

        chunks = [
            {"id": "conv-48::D2:13", "text": "Alpha text."},
            {"id": "conv-48::D4:34", "text": "Alpha text 2."},
            {"id": "conv-50::D12:2", "text": "Beta text."},
        ]
        result = zep.ingest_corpus(chunks)
        self.assertEqual(result["sessions_created"], 2)

        all_add_calls = mock_client.memory.add_memory.call_args_list
        total_msgs = sum(len(c.args[1].messages) for c in all_add_calls)
        self.assertEqual(total_msgs, 3)


class TestExplicitConvId(unittest.TestCase):
    """Explicit conv_id field overrides the derived grouping."""

    def test_explicit_conv_id_used(self):
        zep = _fresh_adapter()
        zep._wait_for_embeddings = lambda *a, **kw: None

        mock_client = MagicMock()
        mock_client.memory.get_session.side_effect = Exception("not found")
        mock_client.memory.add_session.return_value = MagicMock()
        mock_client.memory.add_memory.return_value = MagicMock()
        zep._client = mock_client

        chunks = [
            {"id": "some-id-1", "text": "Text A.", "conv_id": "custom-session"},
            {"id": "some-id-2", "text": "Text B.", "conv_id": "custom-session"},
        ]
        zep.ingest_corpus(chunks)

        calls = mock_client.memory.add_session.call_args_list
        session_ids = [c.args[0].session_id for c in calls]
        self.assertIn("q4-custom-session", session_ids)
        self.assertEqual(len(set(session_ids)), 1, "Both chunks should land in the same session")


class TestSearchMapsGoldId(unittest.TestCase):
    """search() must map message metadata gold_id -> result id field."""

    def test_gold_id_extracted_when_present(self):
        zep = _fresh_adapter()
        mock_client = MagicMock()
        zep._client = mock_client
        zep._sessions = ["q4-conv-48"]

        msg = _mock_message(
            "Deborah finds peace in nature.",
            metadata={"gold_id": "conv-48::D2:13"},
            uuid="zep-uuid-xyz",
        )
        result = _mock_search_result(msg, dist=0.95)
        mock_client.memory.search_memory.return_value = [result]

        results = zep.search("peace", k=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "conv-48::D2:13")
        self.assertAlmostEqual(results[0]["score"], 0.95)
        self.assertEqual(results[0]["source"], "q4-conv-48")

    def test_fallback_to_zep_uuid_when_no_gold_id(self):
        """When metadata has no gold_id, result id falls back to Zep message UUID."""
        zep = _fresh_adapter()
        mock_client = MagicMock()
        zep._client = mock_client
        zep._sessions = ["q4-conv-48"]

        msg = _mock_message("Some text", metadata={}, uuid="zep-uuid-abc123")
        result = _mock_search_result(msg, dist=0.9)
        mock_client.memory.search_memory.return_value = [result]

        results = zep.search("test query", k=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "zep-uuid-abc123")


class TestSearchDeduplication(unittest.TestCase):
    """Duplicate results from multiple sessions must be collapsed."""

    def test_dedup_same_gold_id(self):
        zep = _fresh_adapter()
        mock_client = MagicMock()
        zep._client = mock_client
        zep._sessions = ["q4-conv-48", "q4-conv-50"]

        # Session 1 returns gold_id D2:13 with high score
        # Session 2 returns same gold_id D2:13 with lower score + a new gold_id D12:2
        def side_effect(session_id, payload, limit=None):
            if session_id == "q4-conv-48":
                return [
                    _mock_search_result(
                        _mock_message("Text", {"gold_id": "conv-48::D2:13"}), dist=0.95
                    )
                ]
            return [
                _mock_search_result(
                    _mock_message("Text", {"gold_id": "conv-48::D2:13"}), dist=0.80
                ),
                _mock_search_result(
                    _mock_message("Text", {"gold_id": "conv-50::D12:2"}), dist=0.70
                ),
            ]

        mock_client.memory.search_memory.side_effect = side_effect
        results = zep.search("peace", k=10)
        ids = [r["id"] for r in results]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate IDs must be collapsed")
        self.assertEqual(len(results), 2)
        # higher-scoring D2:13 wins
        self.assertEqual(results[0]["id"], "conv-48::D2:13")
        self.assertAlmostEqual(results[0]["score"], 0.95)


class TestValidateStaticChecks(unittest.TestCase):
    """validate() must not crash and must return the correct shape."""

    def test_validate_ok_when_sdk_installed_and_key_set(self):
        """If zep_python is importable and OPENAI_API_KEY set, ok=True even when Zep daemon is down."""
        zep = _fresh_adapter()
        env_patch = {"OPENAI_API_KEY": "sk-test"}
        with patch.dict(os.environ, env_patch, clear=False):
            with patch("requests.get", side_effect=Exception("connection refused")):
                result = zep.validate()
        self.assertIn("ok", result)
        self.assertIn("version", result)
        self.assertIn("error", result)
        self.assertIn("notes", result)
        self.assertTrue(result["ok"])

    def test_validate_missing_openai_key(self):
        """OPENAI_API_KEY missing → ok=False (required for embeddings)."""
        zep = _fresh_adapter()
        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)
        with patch.dict(os.environ, env, clear=True):
            with patch("requests.get", side_effect=Exception("offline")):
                result = zep.validate()
        self.assertFalse(result["ok"])
        self.assertIn("OPENAI_API_KEY", result["error"])

    def test_validate_returns_all_required_keys(self):
        """validate() result must always have ok/error/version/notes."""
        zep = _fresh_adapter()
        with patch("requests.get", side_effect=Exception("offline")):
            result = zep.validate()
        for key in ("ok", "error", "version", "notes"):
            self.assertIn(key, result, f"Missing key: {key}")


class TestSearchFallbackSingleSession(unittest.TestCase):
    """When no sessions are ingested, search falls back to ZEP_SESSION_ID env."""

    def test_fallback_uses_env_session_id(self):
        zep = _fresh_adapter()
        mock_client = MagicMock()
        zep._client = mock_client
        # _sessions is empty — triggers fallback
        mock_client.memory.search_memory.return_value = []

        with patch.dict(os.environ, {"ZEP_SESSION_ID": "my-custom-session"}):
            results = zep.search("test", k=5)

        # search_memory called with the env-provided session
        args, _ = mock_client.memory.search_memory.call_args
        self.assertEqual(args[0], "my-custom-session")
        self.assertIsInstance(results, list)

    def test_fallback_returns_empty_when_no_env(self):
        zep = _fresh_adapter()
        mock_client = MagicMock()
        zep._client = mock_client

        env = os.environ.copy()
        env.pop("ZEP_SESSION_ID", None)
        with patch.dict(os.environ, env, clear=True):
            results = zep.search("test", k=5)
        self.assertEqual(results, [])


# ---------------------------------------------------------------------------
# Integration tests — require live Zep OSS
# ---------------------------------------------------------------------------


@integration
class TestIntegrationSetup(unittest.TestCase):
    """validate() + setup() + teardown() work against live Zep."""

    def test_validate_reports_healthy(self):
        zep = _fresh_adapter()
        result = zep.validate()
        self.assertTrue(result["ok"], f"validate() failed: {result}")
        self.assertIn("healthy", result["notes"])

    def test_setup_teardown_idempotent(self):
        zep = _fresh_adapter()
        zep.setup()
        zep.setup()  # second call is a no-op
        zep.teardown()
        zep.teardown()  # double teardown is safe


@integration
class TestIntegrationIngestAndSearch(unittest.TestCase):
    """End-to-end: ingest chunks -> search returns mapped gold IDs."""

    _CONV_ID = "integration-test-conv"

    def setUp(self):
        self.zep = _fresh_adapter()
        # Skip docker exec poll in tests — we wait manually below
        self.zep._wait_for_embeddings = lambda *a, **kw: __import__("time").sleep(6)
        self.zep.setup()

    def tearDown(self):
        self.zep.teardown()

    def test_ingest_creates_sessions(self):
        chunks = [
            {"id": f"{self._CONV_ID}::chunk-1", "text": "Deborah finds peace in mountains."},
            {"id": f"{self._CONV_ID}::chunk-2", "text": "She meditates at dawn each day."},
        ]
        result = self.zep.ingest_corpus(chunks)
        self.assertEqual(result["errors"], 0, f"Ingest errors: {result['errors']}")
        self.assertGreater(result["messages_added"], 0)
        self.assertGreater(result["sessions_created"], 0)

    def test_search_returns_valid_items(self):
        """search() returns list[dict] with required id/score/text/source keys."""
        chunks = [
            {"id": f"{self._CONV_ID}::chunk-3", "text": "The lake at sunset fills her with calm."},
        ]
        self.zep.ingest_corpus(chunks)
        results = self.zep.search("lake sunset calm", k=5)

        self.assertIsInstance(results, list)
        for item in results:
            for key in ("id", "score", "text", "source"):
                self.assertIn(key, item, f"Missing key {key!r} in result")
            self.assertIsInstance(item["id"], str)
            self.assertTrue(len(item["id"]) > 0, "id must be non-empty")


if __name__ == "__main__":
    unittest.main()
