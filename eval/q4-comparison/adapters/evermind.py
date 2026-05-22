"""
EverMind-AI adapter — repo CLI (Python).

Repo: https://github.com/EverOS-AI/EverMind-AI  (license tracked in REQUIREMENTS.md, ~5k stars)
Note: EverOS publishes EverMemBench + papers + their own benchmark numbers,
which makes them the most-explicit "benchmark publisher competitor" of the
five (see memory: `[[everos-benchmark-publisher-competitor]]`).

Install: git clone + pip install -e . (no PyPI package as of 2026-05-21).
Pinned commit recorded in REQUIREMENTS.md once Toto clones Saturday.

Invocation: as of 2026-05-21 the public EverMind-AI repo exposes
`evermind` CLI with `evermind retrieve --query "<q>" --k <k> --json`. If
the surface differs at Saturday clone-time, this adapter switches to the
Python module path via env var EVERMIND_PYTHON_MODULE.

KNOWN GAP: EverMind-AI's retrieval surface is less stable than Mem0/Letta;
this adapter has TWO call paths (CLI subprocess + Python module) and falls
back automatically. If neither works, validate() returns ok=False and Toto
skips per spec §4 stop conditions.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from typing import Any

NAME = "evermind"
VERSION_PIN = "EverMind-AI@git-sha-pinned-saturday (no PyPI as of 2026-05-21)"
REQUIRES_ENV: list[str] = []  # EverMind defaults to local embeddings (sentence-transformers)
INSTALL_HINT = (
    "git clone https://github.com/EverOS-AI/EverMind-AI && "
    "cd EverMind-AI && pip install -e . && evermind --version"
)


def _cli_path() -> str | None:
    return shutil.which(os.environ.get("EVERMIND_BIN") or "evermind")


def _python_module() -> str | None:
    return os.environ.get("EVERMIND_PYTHON_MODULE")  # e.g., "evermind.retrieval"


def validate() -> dict:
    cli = _cli_path()
    module = _python_module()

    if cli is None and module is None:
        return {
            "ok": False,
            "error": "neither `evermind` CLI nor EVERMIND_PYTHON_MODULE configured",
            "version": None,
            "notes": INSTALL_HINT,
        }

    if cli is not None:
        try:
            proc = subprocess.run(
                [cli, "--version"], capture_output=True, text=True, timeout=10, check=False
            )
            if proc.returncode == 0:
                version = (proc.stdout.strip() or proc.stderr.strip()).splitlines()[0]
                return {
                    "ok": True,
                    "error": None,
                    "version": version,
                    "notes": "CLI mode — verify Saturday commit pinned in REQUIREMENTS.md",
                }
            error_note = proc.stderr.strip()[:200]
        except Exception as exc:  # pragma: no cover
            error_note = str(exc)
        # Fall through to module check if CLI broken
    else:
        error_note = "no CLI on PATH"

    if module is not None:
        try:
            __import__(module)
            return {
                "ok": True,
                "error": None,
                "version": "module:" + module,
                "notes": "Python module mode — confirm retrieve() signature",
            }
        except ImportError as exc:
            return {
                "ok": False,
                "error": f"EVERMIND_PYTHON_MODULE={module} import failed: {exc}",
                "version": None,
                "notes": "Set EVERMIND_PYTHON_MODULE to the importable path",
            }

    return {
        "ok": False,
        "error": f"evermind CLI present but unusable: {error_note}",
        "version": None,
        "notes": "Pin EVERMIND_BIN or EVERMIND_PYTHON_MODULE explicitly",
    }


def setup() -> None:
    return None


def teardown() -> None:
    return None


def search(query: str, k: int = 10) -> list[dict]:
    cli = _cli_path()
    if cli is not None:
        return _search_cli(cli, query, k)
    module = _python_module()
    if module is not None:
        return _search_module(module, query, k)
    raise RuntimeError("EverMind-AI not configured — run smoke_test.py")


def _search_cli(cli: str, query: str, k: int) -> list[dict]:
    proc = subprocess.run(
        [cli, "retrieve", "--query", query, "--k", str(k), "--json"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"evermind retrieve exit {proc.returncode}: {proc.stderr.strip()}")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"evermind output not JSON: {exc}") from exc
    raw: list[dict[str, Any]] = payload if isinstance(payload, list) else payload.get("results", [])
    return _normalize(raw, k)


def _search_module(module: str, query: str, k: int) -> list[dict]:
    mod = __import__(module, fromlist=["retrieve"])
    retrieve = getattr(mod, "retrieve", None)
    if retrieve is None:
        raise RuntimeError(f"{module}.retrieve not found")
    raw = retrieve(query=query, k=k)
    return _normalize(raw, k)


def _normalize(raw: list[dict[str, Any]], k: int) -> list[dict]:
    return [
        {
            "id": str(item.get("id") or item.get("doc_id") or ""),
            "score": float(item.get("score") or item.get("similarity") or 0.0),
            "text": item.get("text") or item.get("content") or "",
            "source": item.get("source") or None,
        }
        for item in (raw or [])[:k]
    ]
