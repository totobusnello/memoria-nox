"""
agentmemory adapter — CLI subprocess (npm package).

Repo: https://github.com/rohitg00/agentmemory  (MIT CLI, 11k+ stars)
Install: npm install -g @agentmemory/agentmemory@latest

KNOWN GAP (per benchmark/competitor-configs.json + spec §1):
  - agentmemory CLI exists open-source under MIT
  - BUT the runtime daemon `iii-engine` may be required for vector retrieval
  - iii-engine licensing is unclear in public docs
  - Two blockers tracked: (1) confirm iii-engine installable on the VPS without
    a paid license; (2) confirm CLI-only mode supports search.

If iii-engine is required and unavailable, this adapter will fail `validate()`
and Toto skips agentmemory from the Q4 run (per spec §4 stop conditions).

Calls per query: `agentmemory recall "<query>" --top-k <k> --json`
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any

NAME = "agentmemory"
VERSION_PIN = "@agentmemory/agentmemory@npm-latest-on-2026-05-21 (resolve via `agentmemory --version`)"
REQUIRES_ENV: list[str] = []  # CLI may need iii-engine running; checked in validate
INSTALL_HINT = (
    "npm install -g '@agentmemory/agentmemory'   "
    "# also requires iii-engine daemon — see BLOCKED.md / competitor-configs.json"
)


def _cli_path() -> str | None:
    return shutil.which(os.environ.get("AGENTMEMORY_BIN") or "agentmemory")


def validate() -> dict:
    cli = _cli_path()
    if cli is None:
        return {
            "ok": False,
            "error": "agentmemory CLI not found on $PATH",
            "version": None,
            "notes": INSTALL_HINT,
        }
    # `agentmemory --version` (no network)
    try:
        proc = subprocess.run(
            [cli, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except Exception as exc:  # pragma: no cover
        return {
            "ok": False,
            "error": f"failed to invoke {cli}: {exc}",
            "version": None,
            "notes": None,
        }
    if proc.returncode != 0:
        return {
            "ok": False,
            "error": f"{cli} --version exited {proc.returncode}: {proc.stderr.strip()}",
            "version": None,
            "notes": "Check iii-engine daemon — agentmemory CLI may require it",
        }
    version = (proc.stdout.strip() or proc.stderr.strip()).splitlines()[0]
    return {
        "ok": True,
        "error": None,
        "version": version,
        "notes": (
            "CLI present. Saturday runtime: ensure iii-engine daemon is up "
            "before runner.py — see blockers in competitor-configs.json."
        ),
    }


def setup() -> None:
    return None


def teardown() -> None:
    return None


def search(query: str, k: int = 10) -> list[dict]:
    cli = _cli_path()
    if cli is None:
        raise RuntimeError("agentmemory CLI not installed — run smoke_test.py first")

    proc = subprocess.run(
        [cli, "recall", query, "--top-k", str(k), "--json"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"agentmemory recall failed (exit {proc.returncode}): {proc.stderr.strip()}"
        )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"agentmemory recall did not return JSON: {exc}") from exc

    raw: list[dict[str, Any]] = (
        payload if isinstance(payload, list) else payload.get("results") or []
    )
    return [
        {
            "id": str(item.get("id") or item.get("memory_id") or ""),
            "score": float(item.get("score") or item.get("relevance") or 0.0),
            "text": item.get("text") or item.get("content") or "",
            "source": item.get("session") or item.get("source") or None,
        }
        for item in raw[:k]
    ]
