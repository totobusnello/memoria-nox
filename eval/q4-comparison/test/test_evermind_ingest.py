"""
Tests for EverMind-AI adapter — dual-path (CLI + Python module).

Run:
    python -m pytest eval/q4-comparison/test/test_evermind_ingest.py -v

Focus areas:
  1. validate() — fails when neither path configured
  2. setup() / _resolve_path() — picks CLI when available, falls back to module
  3. ingest_corpus() — CLI path mode subprocess flow
  4. ingest_corpus() — Python module path via fake module
  5. ingest_corpus() — returns mode=skip when neither path available
  6. search() — round-trips ids natively (no map needed)
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import types
from pathlib import Path
from unittest import mock

import pytest

HERE = Path(__file__).parent.parent
sys.path.insert(0, str(HERE))


def _import_fresh():
    mod_name = "adapters.evermind"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    return importlib.import_module(mod_name)


def _proc(returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


# ---------------------------------------------------------------------------
# validate()
# ---------------------------------------------------------------------------


class TestValidate:
    def test_fail_when_no_cli_and_no_module(self):
        mod = _import_fresh()
        env = {k: v for k, v in os.environ.items() if k != "EVERMIND_PYTHON_MODULE"}
        with (
            mock.patch.dict(os.environ, env, clear=True),
            mock.patch.object(mod.shutil, "which", return_value=None),
        ):
            result = mod.validate()
        assert result["ok"] is False
        assert "neither" in (result["error"] or "")

    def test_ok_when_cli_works(self):
        mod = _import_fresh()
        with (
            mock.patch.object(mod.shutil, "which", return_value="/usr/local/bin/evermind"),
            mock.patch.object(
                mod.subprocess,
                "run",
                return_value=_proc(returncode=0, stdout="evermind 0.3.1"),
            ),
        ):
            result = mod.validate()
        assert result["ok"] is True
        assert "0.3.1" in result["version"]

    def test_fallback_to_module_when_cli_fails(self, tmp_path):
        mod = _import_fresh()
        # Create a fake python module
        fake_mod = types.ModuleType("fake_evermind")
        fake_mod.retrieve = lambda **_kw: []  # type: ignore[attr-defined]

        with (
            mock.patch.dict(os.environ, {"EVERMIND_PYTHON_MODULE": "fake_evermind"}),
            mock.patch.object(mod.shutil, "which", return_value=None),
            mock.patch.dict(sys.modules, {"fake_evermind": fake_mod}),
        ):
            result = mod.validate()
        assert result["ok"] is True
        assert "module:" in result["version"]


# ---------------------------------------------------------------------------
# _resolve_path / setup
# ---------------------------------------------------------------------------


class TestResolvePath:
    def test_prefers_cli_when_both_available(self):
        mod = _import_fresh()
        fake_mod = types.ModuleType("fake_evermind")
        with (
            mock.patch.dict(os.environ, {"EVERMIND_PYTHON_MODULE": "fake_evermind"}),
            mock.patch.object(mod.shutil, "which", return_value="/usr/local/bin/evermind"),
            mock.patch.object(mod.subprocess, "run", return_value=_proc(returncode=0)),
            mock.patch.dict(sys.modules, {"fake_evermind": fake_mod}),
        ):
            mod._resolve_path()
        assert mod._path_mode == "cli"

    def test_falls_back_to_python_when_cli_broken(self):
        mod = _import_fresh()
        fake_mod = types.ModuleType("fake_evermind")
        with (
            mock.patch.dict(os.environ, {"EVERMIND_PYTHON_MODULE": "fake_evermind"}),
            mock.patch.object(mod.shutil, "which", return_value=None),
            mock.patch.dict(sys.modules, {"fake_evermind": fake_mod}),
        ):
            mod._resolve_path()
        assert mod._path_mode == "python"

    def test_none_when_neither_available(self):
        mod = _import_fresh()
        env = {k: v for k, v in os.environ.items() if k != "EVERMIND_PYTHON_MODULE"}
        with (
            mock.patch.dict(os.environ, env, clear=True),
            mock.patch.object(mod.shutil, "which", return_value=None),
        ):
            mod._resolve_path()
        assert mod._path_mode == "none"


# ---------------------------------------------------------------------------
# ingest_corpus() — CLI path
# ---------------------------------------------------------------------------


class TestIngestCorpusCLI:
    def test_skip_when_neither_path(self):
        mod = _import_fresh()
        env = {k: v for k, v in os.environ.items() if k != "EVERMIND_PYTHON_MODULE"}
        with (
            mock.patch.dict(os.environ, env, clear=True),
            mock.patch.object(mod.shutil, "which", return_value=None),
        ):
            mod._resolve_path()
            result = mod.ingest_corpus([{"id": "c1", "text": "x"}])
        assert result["mode"] == "skip"
        assert result["path_used"] == "none"
        assert "error" in result

    def test_cli_inserts_chunks(self):
        mod = _import_fresh()
        mod._path_mode = "cli"
        calls: list[list[str]] = []

        def run_stub(argv, **_kw):
            calls.append(list(argv))
            if "list" in argv:  # idempotency probe
                return _proc(returncode=1)
            return _proc(returncode=0)

        with (
            mock.patch.object(mod.shutil, "which", return_value="/usr/local/bin/evermind"),
            mock.patch.object(mod.subprocess, "run", side_effect=run_stub),
        ):
            result = mod.ingest_corpus(
                [
                    {"id": "c1", "text": "alpha"},
                    {"id": "c2", "text": "beta"},
                ]
            )

        assert result["path_used"] == "cli"
        assert result["ingested"] == 2
        assert result["errors"] == 0
        add_calls = [c for c in calls if "add" in c]
        assert any("c1" in c for c in add_calls)

    def test_cli_idempotent_when_count_matches(self):
        mod = _import_fresh()
        mod._path_mode = "cli"

        def run_stub(argv, **_kw):
            if "list" in argv:
                return _proc(returncode=0, stdout=json.dumps([{"id": "x"}, {"id": "y"}]))
            return _proc(returncode=0)

        with (
            mock.patch.object(mod.shutil, "which", return_value="/usr/local/bin/evermind"),
            mock.patch.object(mod.subprocess, "run", side_effect=run_stub),
        ):
            result = mod.ingest_corpus(
                [{"id": "c1", "text": "a"}, {"id": "c2", "text": "b"}]
            )

        assert result["mode"] == "idempotent-skip"
        assert result["skipped"] == 2


# ---------------------------------------------------------------------------
# ingest_corpus() — Python module path
# ---------------------------------------------------------------------------


class TestIngestCorpusPython:
    def test_python_module_add_called(self):
        mod = _import_fresh()
        mod._path_mode = "python"

        # Build a fake module with an `add` function
        fake = types.ModuleType("fake_evermind")
        records: list[dict] = []

        def add(**kwargs):
            records.append(kwargs)
            return {"id": kwargs["id"]}

        fake.add = add  # type: ignore[attr-defined]
        # No list_fn → idempotency probe disabled, ingest proceeds

        with (
            mock.patch.dict(os.environ, {"EVERMIND_PYTHON_MODULE": "fake_evermind"}),
            mock.patch.dict(sys.modules, {"fake_evermind": fake}),
        ):
            result = mod.ingest_corpus(
                [
                    {"id": "c1", "text": "alpha"},
                    {"id": "c2", "text": "beta"},
                ]
            )

        assert result["path_used"] == "python"
        assert result["ingested"] == 2
        assert {r["id"] for r in records} == {"c1", "c2"}

    def test_python_idempotent_via_list(self):
        mod = _import_fresh()
        mod._path_mode = "python"

        fake = types.ModuleType("fake_evermind")
        fake.add = lambda **_kw: None  # type: ignore[attr-defined]
        fake.list = lambda: [{"id": "x"}, {"id": "y"}]  # type: ignore[attr-defined]

        with (
            mock.patch.dict(os.environ, {"EVERMIND_PYTHON_MODULE": "fake_evermind"}),
            mock.patch.dict(sys.modules, {"fake_evermind": fake}),
        ):
            result = mod.ingest_corpus(
                [{"id": "c1", "text": "a"}, {"id": "c2", "text": "b"}]
            )

        assert result["mode"] == "idempotent-skip"

    def test_python_module_missing_add_returns_error(self):
        mod = _import_fresh()
        mod._path_mode = "python"
        fake = types.ModuleType("fake_evermind")
        # No add/upsert/insert
        with (
            mock.patch.dict(os.environ, {"EVERMIND_PYTHON_MODULE": "fake_evermind"}),
            mock.patch.dict(sys.modules, {"fake_evermind": fake}),
        ):
            result = mod.ingest_corpus([{"id": "c1", "text": "x"}])
        assert result["errors"] == 1
        assert "no add/upsert/insert" in (result.get("error") or "")

    def test_python_handles_legacy_positional_signature(self):
        mod = _import_fresh()
        mod._path_mode = "python"

        called: list[tuple] = []

        def legacy_add(*args, **kwargs):
            if kwargs:
                raise TypeError("legacy expects positional")
            called.append(args)

        fake = types.ModuleType("fake_evermind")
        fake.add = legacy_add  # type: ignore[attr-defined]

        with (
            mock.patch.dict(os.environ, {"EVERMIND_PYTHON_MODULE": "fake_evermind"}),
            mock.patch.dict(sys.modules, {"fake_evermind": fake}),
        ):
            result = mod.ingest_corpus([{"id": "c1", "text": "alpha"}])

        assert result["ingested"] == 1
        assert called == [("c1", "alpha")]


# ---------------------------------------------------------------------------
# search()
# ---------------------------------------------------------------------------


class TestSearch:
    def test_cli_search_round_trips_id(self):
        mod = _import_fresh()
        mod._path_mode = "cli"
        payload = [
            {"id": "conv-48::D2:13", "score": 0.91, "text": "beach text"},
            {"id": "conv-48::D2:14", "score": 0.85, "text": "garden text"},
        ]
        with (
            mock.patch.object(mod.shutil, "which", return_value="/usr/local/bin/evermind"),
            mock.patch.object(
                mod.subprocess,
                "run",
                return_value=_proc(returncode=0, stdout=json.dumps(payload)),
            ),
        ):
            results = mod.search("places of peace", k=10)

        assert results[0]["id"] == "conv-48::D2:13"
        assert results[0]["score"] == 0.91

    def test_python_search(self):
        mod = _import_fresh()
        mod._path_mode = "python"

        fake = types.ModuleType("fake_evermind")
        fake.retrieve = lambda **kw: [  # type: ignore[attr-defined]
            {"id": "c1", "score": 0.7, "text": "alpha"}
        ]
        with (
            mock.patch.dict(os.environ, {"EVERMIND_PYTHON_MODULE": "fake_evermind"}),
            mock.patch.dict(sys.modules, {"fake_evermind": fake}),
        ):
            results = mod.search("q", k=10)

        assert len(results) == 1
        assert results[0]["id"] == "c1"

    def test_raises_when_no_path(self):
        mod = _import_fresh()
        env = {k: v for k, v in os.environ.items() if k != "EVERMIND_PYTHON_MODULE"}
        with (
            mock.patch.dict(os.environ, env, clear=True),
            mock.patch.object(mod.shutil, "which", return_value=None),
        ):
            mod._path_mode = "none"
            with pytest.raises(RuntimeError, match="not configured"):
                mod.search("q", k=10)


# ---------------------------------------------------------------------------
# teardown
# ---------------------------------------------------------------------------


class TestTeardown:
    def test_resets_path_mode(self):
        mod = _import_fresh()
        mod._path_mode = "cli"
        mod.teardown()
        assert mod._path_mode == "none"
