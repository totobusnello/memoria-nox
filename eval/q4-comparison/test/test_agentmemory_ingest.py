"""
Tests for agentmemory adapter ingestion + search contract.

Run:
    python -m pytest eval/q4-comparison/test/test_agentmemory_ingest.py -v

These tests mock subprocess.run so they exercise the adapter logic without
requiring the npm CLI or iii-engine daemon. Focus areas:
  1. validate() — CLI on path + --version exit codes
  2. ingest_corpus() — subprocess invocation, idempotent skip, error counting,
     graceful skip when CLI missing (paid-only daemon scenario)
  3. search() — JSON parsing, k limit, error propagation
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

HERE = Path(__file__).parent.parent
sys.path.insert(0, str(HERE))


def _import_fresh():
    mod_name = "adapters.agentmemory"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    return importlib.import_module(mod_name)


def _proc(returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


# ---------------------------------------------------------------------------
# validate()
# ---------------------------------------------------------------------------


class TestValidate:
    def test_fail_when_cli_not_on_path(self):
        mod = _import_fresh()
        with mock.patch.object(mod.shutil, "which", return_value=None):
            result = mod.validate()
        assert result["ok"] is False
        assert "not found" in (result["error"] or "")

    def test_fail_when_version_exits_nonzero(self):
        mod = _import_fresh()
        with (
            mock.patch.object(mod.shutil, "which", return_value="/usr/local/bin/agentmemory"),
            mock.patch.object(
                mod.subprocess,
                "run",
                return_value=_proc(returncode=1, stderr="daemon offline"),
            ),
        ):
            result = mod.validate()
        assert result["ok"] is False
        assert "daemon" in (result["notes"] or "").lower()

    def test_ok_when_cli_and_daemon_up(self):
        mod = _import_fresh()
        with (
            mock.patch.object(mod.shutil, "which", return_value="/usr/local/bin/agentmemory"),
            mock.patch.object(
                mod.subprocess,
                "run",
                return_value=_proc(returncode=0, stdout="agentmemory 1.2.3"),
            ),
        ):
            result = mod.validate()
        assert result["ok"] is True
        assert result["version"] == "agentmemory 1.2.3"


# ---------------------------------------------------------------------------
# ingest_corpus()
# ---------------------------------------------------------------------------


class TestIngestCorpus:
    def test_skip_when_cli_missing(self):
        """The iii-engine paid-only scenario: graceful skip, no exception."""
        mod = _import_fresh()
        with mock.patch.object(mod.shutil, "which", return_value=None):
            result = mod.ingest_corpus([{"id": "x", "text": "y"}])
        assert result["mode"] == "skip"
        assert result["ingested"] == 0
        assert "error" in result

    def test_empty_chunks_noop(self):
        mod = _import_fresh()
        with mock.patch.object(mod.shutil, "which", return_value="/usr/local/bin/agentmemory"):
            result = mod.ingest_corpus([])
        assert result["total"] == 0
        assert result["mode"] == "noop"

    def test_inserts_each_chunk(self):
        mod = _import_fresh()
        calls: list[list[str]] = []

        def run_stub(argv, **_kwargs):
            calls.append(list(argv))
            # The count probe (list --json --count-only / list --json / stats --json)
            # should return non-zero or no parseable count so ingest proceeds.
            if any("list" in a or "stats" in a for a in argv):
                return _proc(returncode=1, stderr="no such command")
            return _proc(returncode=0, stdout="")

        with (
            mock.patch.object(mod.shutil, "which", return_value="/usr/local/bin/agentmemory"),
            mock.patch.object(mod.subprocess, "run", side_effect=run_stub),
        ):
            result = mod.ingest_corpus(
                [
                    {"id": "c1", "text": "hello"},
                    {"id": "c2", "text": "world"},
                ]
            )

        assert result["ingested"] == 2
        assert result["errors"] == 0
        # Verify --id and --text propagated for each add
        add_calls = [c for c in calls if "add" in c]
        assert any("c1" in c and "hello" in c for c in add_calls)
        assert any("c2" in c and "world" in c for c in add_calls)

    def test_idempotent_skip_when_count_matches(self):
        mod = _import_fresh()

        def run_stub(argv, **_kwargs):
            # Return JSON count from "list --json" indicating 2 existing
            if "list" in argv:
                return _proc(returncode=0, stdout=json.dumps([{"id": "a"}, {"id": "b"}]))
            return _proc(returncode=0, stdout="")

        with (
            mock.patch.object(mod.shutil, "which", return_value="/usr/local/bin/agentmemory"),
            mock.patch.object(mod.subprocess, "run", side_effect=run_stub),
        ):
            result = mod.ingest_corpus(
                [
                    {"id": "c1", "text": "hello"},
                    {"id": "c2", "text": "world"},
                ]
            )

        assert result["mode"] == "idempotent-skip"
        assert result["skipped"] == 2

    def test_skips_chunks_with_empty_text(self):
        mod = _import_fresh()

        def run_stub(argv, **_kwargs):
            if "list" in argv or "stats" in argv:
                return _proc(returncode=1)
            return _proc(returncode=0)

        with (
            mock.patch.object(mod.shutil, "which", return_value="/usr/local/bin/agentmemory"),
            mock.patch.object(mod.subprocess, "run", side_effect=run_stub),
        ):
            result = mod.ingest_corpus(
                [
                    {"id": "c1", "text": ""},
                    {"id": "", "text": "no id"},
                    {"id": "c3", "text": "ok"},
                ]
            )

        assert result["ingested"] == 1
        assert result["errors"] == 2

    def test_retries_without_upsert_on_failure(self):
        mod = _import_fresh()
        seen: list[list[str]] = []

        def run_stub(argv, **_kwargs):
            if "list" in argv or "stats" in argv:
                return _proc(returncode=1)
            seen.append(list(argv))
            # First "add ... --upsert" fails; retry without --upsert succeeds
            if "--upsert" in argv:
                return _proc(returncode=1, stderr="unknown flag --upsert")
            return _proc(returncode=0)

        with (
            mock.patch.object(mod.shutil, "which", return_value="/usr/local/bin/agentmemory"),
            mock.patch.object(mod.subprocess, "run", side_effect=run_stub),
        ):
            result = mod.ingest_corpus([{"id": "c1", "text": "hello"}])

        assert result["ingested"] == 1
        # Two invocations were attempted: with then without --upsert
        assert any("--upsert" in c for c in seen)
        assert any("--upsert" not in c for c in seen)

    def test_counts_errors_when_both_retries_fail(self):
        mod = _import_fresh()

        def run_stub(argv, **_kwargs):
            if "list" in argv or "stats" in argv:
                return _proc(returncode=1)
            return _proc(returncode=1, stderr="hard fail")

        with (
            mock.patch.object(mod.shutil, "which", return_value="/usr/local/bin/agentmemory"),
            mock.patch.object(mod.subprocess, "run", side_effect=run_stub),
        ):
            result = mod.ingest_corpus(
                [{"id": "c1", "text": "x"}, {"id": "c2", "text": "y"}]
            )

        assert result["ingested"] == 0
        assert result["errors"] == 2


# ---------------------------------------------------------------------------
# search()
# ---------------------------------------------------------------------------


class TestSearch:
    def test_parses_json_list(self):
        mod = _import_fresh()
        payload = [
            {"id": "c1", "score": 0.9, "text": "alpha", "session": "s1"},
            {"id": "c2", "score": 0.5, "text": "beta", "session": "s2"},
        ]
        with (
            mock.patch.object(mod.shutil, "which", return_value="/usr/local/bin/agentmemory"),
            mock.patch.object(
                mod.subprocess,
                "run",
                return_value=_proc(returncode=0, stdout=json.dumps(payload)),
            ),
        ):
            results = mod.search("query", k=10)

        assert len(results) == 2
        assert results[0]["id"] == "c1"
        assert results[0]["score"] == 0.9
        assert results[0]["source"] == "s1"

    def test_parses_dict_with_results_key(self):
        mod = _import_fresh()
        payload = {"results": [{"id": "c1", "score": 0.8, "text": "alpha"}]}
        with (
            mock.patch.object(mod.shutil, "which", return_value="/usr/local/bin/agentmemory"),
            mock.patch.object(
                mod.subprocess,
                "run",
                return_value=_proc(returncode=0, stdout=json.dumps(payload)),
            ),
        ):
            results = mod.search("q", k=10)
        assert len(results) == 1
        assert results[0]["id"] == "c1"

    def test_search_respects_k(self):
        mod = _import_fresh()
        payload = [
            {"id": f"c{i}", "score": 1.0 - i * 0.1, "text": f"t{i}"} for i in range(20)
        ]
        with (
            mock.patch.object(mod.shutil, "which", return_value="/usr/local/bin/agentmemory"),
            mock.patch.object(
                mod.subprocess,
                "run",
                return_value=_proc(returncode=0, stdout=json.dumps(payload)),
            ),
        ):
            results = mod.search("q", k=5)
        assert len(results) == 5

    def test_raises_on_nonzero_exit(self):
        mod = _import_fresh()
        with (
            mock.patch.object(mod.shutil, "which", return_value="/usr/local/bin/agentmemory"),
            mock.patch.object(
                mod.subprocess,
                "run",
                return_value=_proc(returncode=1, stderr="daemon down"),
            ),
        ):
            with pytest.raises(RuntimeError, match="recall failed"):
                mod.search("q", k=10)

    def test_raises_on_bad_json(self):
        mod = _import_fresh()
        with (
            mock.patch.object(mod.shutil, "which", return_value="/usr/local/bin/agentmemory"),
            mock.patch.object(
                mod.subprocess,
                "run",
                return_value=_proc(returncode=0, stdout="not json {"),
            ),
        ):
            with pytest.raises(RuntimeError, match="did not return JSON"):
                mod.search("q", k=10)

    def test_raises_when_cli_missing(self):
        mod = _import_fresh()
        with mock.patch.object(mod.shutil, "which", return_value=None):
            with pytest.raises(RuntimeError, match="not installed"):
                mod.search("q", k=10)
