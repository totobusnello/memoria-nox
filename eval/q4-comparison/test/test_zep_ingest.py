"""
Tests for the Zep adapter ingestion pipeline.

Two test tiers:
  1. UNIT  — no Zep daemon needed. Tests pure-Python logic (ID mapping,
             session naming, conv_id derivation, validate() static checks).
  2. INTEGRATION — requires Zep OSS running at ZEP_API_URL (default
             http://127.0.0.1:8000). Skipped automatically if not reachable.

Run unit only (fast, CI-safe):
    pytest test/test_zep_ingest.py -m "not integration" -v

Run all (Saturday morning after docker compose up):
    pytest test/test_zep_ingest.py -v

Environment:
    ZEP_API_URL  — override Zep base URL (default http://127.0.0.1:8000)
    ZEP_USER_ID  — override user namespace (default q4-comparison)
"""

from __future__ import annotations

import importlib
import os
import sys
import types
import unittest
from pathlib import Path
from typing import Any
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
    mod._id_map.clear()
    return mod


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


class TestSessionNaming(unittest.TestCase):
    """Session IDs must be deterministic from conv_id."""

    def test_session_name_prefix(self):
        """Ensure naming convention: q4-<conv_id>."""
        zep = _fresh_adapter()
        mock_client = MagicMock()
        # get_session raises to simulate "not found" -> triggers add_session
        mock_client.memory.get_session.side_effect = Exception("not found")
        mock_client.memory.add_session.return_value = MagicMock()
        mock_client.memory.add.return_value = MagicMock()
        mock_client.user.get.return_value = MagicMock()
        zep._client = mock_client

        chunks = [
            {"id": "conv-48::D2:13", "text": "Deborah finds peace in nature."},
            {"id": "conv-48::D4:34", "text": "Mountains give her serenity."},
        ]
        result = zep.ingest_corpus(chunks)

        calls = mock_client.memory.add_session.call_args_list
        self.assertEqual(len(calls), 1)
        kwargs = calls[0].kwargs
        self.assertEqual(kwargs["session_id"], "q4-conv-48")

        self.assertEqual(result["sessions_created"], 1)
        self.assertEqual(result["messages_added"], 2)
        self.assertEqual(result["errors"], 0)


class TestIdempotentSessionCreation(unittest.TestCase):
    """ingest_corpus must not recreate sessions that already exist."""

    def test_existing_session_not_recreated(self):
        """If get_session succeeds, add_session should NOT be called."""
        zep = _fresh_adapter()
        mock_client = MagicMock()
        mock_client.memory.get_session.return_value = MagicMock()
        mock_client.memory.add.return_value = MagicMock()
        mock_client.user.get.return_value = MagicMock()
        zep._client = mock_client

        chunks = [{"id": "conv-48::D2:13", "text": "Deborah finds peace in nature."}]
        zep.ingest_corpus(chunks)

        mock_client.memory.add_session.assert_not_called()
        mock_client.memory.add.assert_called_once()


class TestGoldIdRoundTrip(unittest.TestCase):
    """Gold IDs stored in metadata must survive the ingest round-trip."""

    def test_metadata_contains_gold_id(self):
        """Messages added to Zep must include gold_id in metadata."""
        zep = _fresh_adapter()
        mock_client = MagicMock()
        mock_client.memory.get_session.side_effect = Exception("not found")
        mock_client.memory.add_session.return_value = MagicMock()
        mock_client.memory.add.return_value = MagicMock()
        mock_client.user.get.return_value = MagicMock()
        zep._client = mock_client

        gold_id = "conv-48::D2:13"
        chunks = [{"id": gold_id, "text": "Deborah finds peace in nature."}]
        zep.ingest_corpus(chunks)

        add_calls = mock_client.memory.add.call_args_list
        self.assertEqual(len(add_calls), 1)
        # messages is passed as keyword arg
        kwargs = add_calls[0].kwargs
        messages_arg = kwargs.get("messages")
        if messages_arg is None and add_calls[0].args:
            messages_arg = add_calls[0].args[-1]
        self.assertIsNotNone(messages_arg, "Expected messages keyword arg")
        self.assertTrue(len(messages_arg) > 0, "Expected at least one message")
        msg = messages_arg[0]
        meta = msg.metadata
        self.assertIn("gold_id", meta)
        self.assertEqual(meta["gold_id"], gold_id)


class TestMultipleConversationGroups(unittest.TestCase):
    """Chunks from different conversations must land in separate sessions."""

    def test_two_convs_two_sessions(self):
        zep = _fresh_adapter()
        mock_client = MagicMock()
        mock_client.memory.get_session.side_effect = Exception("not found")
        mock_client.memory.add_session.return_value = MagicMock()
        mock_client.memory.add.return_value = MagicMock()
        mock_client.user.get.return_value = MagicMock()
        zep._client = mock_client

        chunks = [
            {"id": "conv-48::D2:13", "text": "Alpha text."},
            {"id": "conv-48::D4:34", "text": "Alpha text 2."},
            {"id": "conv-50::D12:2", "text": "Beta text."},
        ]
        result = zep.ingest_corpus(chunks)
        self.assertEqual(result["sessions_created"], 2)

        all_add_calls = mock_client.memory.add.call_args_list
        total_msgs = 0
        for c in all_add_calls:
            msgs = c.kwargs.get("messages") or (c.args[-1] if c.args else [])
            total_msgs += len(msgs)
        self.assertEqual(total_msgs, 3)


class TestExplicitConvId(unittest.TestCase):
    """Explicit conv_id field overrides the derived grouping."""

    def test_explicit_conv_id_used(self):
        zep = _fresh_adapter()
        mock_client = MagicMock()
        mock_client.memory.get_session.side_effect = Exception("not found")
        mock_client.memory.add_session.return_value = MagicMock()
        mock_client.memory.add.return_value = MagicMock()
        mock_client.user.get.return_value = MagicMock()
        zep._client = mock_client

        chunks = [
            {"id": "some-id-1", "text": "Text A.", "conv_id": "custom-session"},
            {"id": "some-id-2", "text": "Text B.", "conv_id": "custom-session"},
        ]
        zep.ingest_corpus(chunks)

        calls = mock_client.memory.add_session.call_args_list
        session_ids = [c.kwargs["session_id"] for c in calls]
        self.assertIn("q4-custom-session", session_ids)
        self.assertEqual(len(set(session_ids)), 1, "Both chunks should land in the same session")


class TestSearchMapsGoldId(unittest.TestCase):
    """search() must map message metadata gold_id -> result id field."""

    def test_gold_id_extracted_when_present(self):
        zep = _fresh_adapter()
        mock_client = MagicMock()
        zep._client = mock_client
        zep._sessions = ["q4-conv-48"]

        mock_msg = MagicMock()
        mock_msg.content = "Deborah finds peace in nature."
        mock_msg.metadata = {"gold_id": "conv-48::D2:13"}
        mock_msg.uuid_ = "zep-uuid-xyz"
        mock_msg.uuid = "zep-uuid-xyz"

        mock_result = MagicMock()
        mock_result.message = mock_msg
        mock_result.score = 0.95
        mock_result.session_id = "q4-conv-48"
        mock_result.fact = None

        mock_resp = MagicMock()
        mock_resp.results = [mock_result]
        mock_client.memory.search_sessions.return_value = mock_resp

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

        mock_msg = MagicMock()
        mock_msg.content = "Some text"
        mock_msg.metadata = {}  # no gold_id
        mock_msg.uuid_ = "zep-uuid-abc123"
        mock_msg.uuid = "zep-uuid-abc123"

        mock_result = MagicMock()
        mock_result.message = mock_msg
        mock_result.score = 0.9
        mock_result.session_id = "q4-conv-48"
        mock_result.fact = None

        mock_resp = MagicMock()
        mock_resp.results = [mock_result]
        mock_client.memory.search_sessions.return_value = mock_resp

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

        def make_result(gold_id, score, session):
            mock_msg = MagicMock()
            mock_msg.content = "Text"
            mock_msg.metadata = {"gold_id": gold_id}
            mock_msg.uuid_ = f"uuid-{gold_id}"
            mock_msg.uuid = f"uuid-{gold_id}"
            r = MagicMock()
            r.message = mock_msg
            r.score = score
            r.session_id = session
            r.fact = None
            return r

        mock_resp = MagicMock()
        mock_resp.results = [
            make_result("conv-48::D2:13", 0.95, "q4-conv-48"),
            make_result("conv-48::D2:13", 0.80, "q4-conv-50"),  # duplicate
            make_result("conv-50::D12:2", 0.70, "q4-conv-50"),
        ]
        mock_client.memory.search_sessions.return_value = mock_resp

        results = zep.search("peace", k=10)
        ids = [r["id"] for r in results]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate IDs must be collapsed")
        self.assertEqual(len(results), 2)


class TestValidateStaticChecks(unittest.TestCase):
    """validate() must not crash and must return the correct shape."""

    def test_validate_ok_when_sdk_installed(self):
        """If zep_python is importable, ok=True even when Zep daemon is down."""
        zep = _fresh_adapter()
        with patch("requests.get", side_effect=Exception("connection refused")):
            result = zep.validate()
        self.assertIn("ok", result)
        self.assertIn("version", result)
        self.assertIn("error", result)
        self.assertIn("notes", result)
        self.assertTrue(result["ok"])  # zep_python IS importable in test env

    def test_validate_cloud_missing_key(self):
        """ZEP_USE_CLOUD=1 without ZEP_API_KEY must return ok=False."""
        zep = _fresh_adapter()
        env_patch = {"ZEP_USE_CLOUD": "1"}
        # Ensure ZEP_API_KEY is absent
        with patch.dict(os.environ, env_patch, clear=False):
            os.environ.pop("ZEP_API_KEY", None)
            result = zep.validate()
        self.assertFalse(result["ok"])
        self.assertIn("ZEP_API_KEY", result["error"])

    def test_validate_returns_all_required_keys(self):
        """validate() result must always have ok/error/version/notes."""
        zep = _fresh_adapter()
        with patch("requests.get", side_effect=Exception("offline")):
            result = zep.validate()
        for key in ("ok", "error", "version", "notes"):
            self.assertIn(key, result, f"Missing key: {key}")


class TestSearchFallbackSingleSession(unittest.TestCase):
    """When no sessions are ingested, search falls back to single-session mode."""

    def test_fallback_uses_env_session_id(self):
        zep = _fresh_adapter()
        mock_client = MagicMock()
        zep._client = mock_client
        # _sessions is empty — triggers fallback

        mock_resp = MagicMock()
        mock_resp.results = []
        mock_client.memory.search_sessions.return_value = mock_resp

        with patch.dict(os.environ, {"ZEP_SESSION_ID": "my-custom-session"}):
            results = zep.search("test", k=5)

        call_kwargs = mock_client.memory.search_sessions.call_args.kwargs
        self.assertIn("session_ids", call_kwargs)
        self.assertEqual(call_kwargs["session_ids"], ["my-custom-session"])
        self.assertIsInstance(results, list)


# ---------------------------------------------------------------------------
# Integration tests — require live Zep OSS
# ---------------------------------------------------------------------------


@integration
class TestIntegrationSetup(unittest.TestCase):
    """validate() + setup() + teardown() work against live Zep."""

    def test_validate_reports_healthy(self):
        zep = _fresh_adapter()
        result = zep.validate()
        self.assertTrue(result["ok"])
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

    _TEST_USER = "q4-integration-test"
    _CONV_ID = "integration-test-conv"

    def setUp(self):
        self.zep = _fresh_adapter()
        with patch.dict(os.environ, {"ZEP_USER_ID": self._TEST_USER}):
            self.zep.setup()

    def tearDown(self):
        self.zep.teardown()

    def test_ingest_creates_sessions(self):
        chunks = [
            {"id": f"{self._CONV_ID}::chunk-1", "text": "Deborah finds peace in mountains."},
            {"id": f"{self._CONV_ID}::chunk-2", "text": "She meditates at dawn each day."},
        ]
        with patch.dict(os.environ, {"ZEP_USER_ID": self._TEST_USER}):
            result = self.zep.ingest_corpus(chunks)
        self.assertEqual(result["errors"], 0, f"Ingest errors: {result['errors']}")
        self.assertGreater(result["messages_added"], 0)
        self.assertGreater(result["sessions_created"], 0)

    def test_search_returns_valid_items(self):
        """search() returns list[dict] with required id/score/text/source keys."""
        chunks = [
            {"id": f"{self._CONV_ID}::chunk-3", "text": "The lake at sunset fills her with calm."},
        ]
        with patch.dict(os.environ, {"ZEP_USER_ID": self._TEST_USER}):
            self.zep.ingest_corpus(chunks)
            # Brief wait for Zep's async fact extraction pipeline.
            import time

            time.sleep(3)
            results = self.zep.search("lake sunset calm", k=5)

        self.assertIsInstance(results, list)
        for item in results:
            for key in ("id", "score", "text", "source"):
                self.assertIn(key, item, f"Missing key {key!r} in result")
            self.assertIsInstance(item["id"], str)
            self.assertTrue(len(item["id"]) > 0, "id must be non-empty")

    def test_idempotent_ingest_no_errors(self):
        """Ingesting the same chunks twice must not raise errors."""
        chunks = [{"id": f"{self._CONV_ID}::chunk-4", "text": "Peace in repetition."}]
        with patch.dict(os.environ, {"ZEP_USER_ID": self._TEST_USER}):
            r1 = self.zep.ingest_corpus(chunks)
            r2 = self.zep.ingest_corpus(chunks)
        self.assertEqual(r1["errors"], 0)
        self.assertEqual(r2["errors"], 0)


if __name__ == "__main__":
    unittest.main()
