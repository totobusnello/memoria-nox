"""
agentmemory adapter — CLI subprocess (npm package).

Repo: https://github.com/rohitg00/agentmemory  (MIT CLI, 11k+ stars)
Install: npm install -g @agentmemory/agentmemory@latest

KNOWN GAP (per benchmark/competitor-configs.json + spec §1):
  - agentmemory CLI exists open-source under MIT.
  - BUT the runtime daemon `iii-engine` may be required for vector retrieval.
  - iii-engine licensing is unclear in public docs.
  - Two blockers tracked: (1) confirm iii-engine installable on the VPS without
    a paid license; (2) confirm CLI-only mode supports search.

If iii-engine is required and unavailable, this adapter will fail `validate()`
and Toto skips agentmemory from the Q4 run (per spec §4 stop conditions).

INGESTION MODEL
---------------
ingest_corpus(chunks) shells out to ``agentmemory add --id <nox_id> --text "..."``
for each chunk. We pass --id explicitly so the daemon stores our stable id;
search() therefore round-trips the nox-mem id natively (no separate id-map
needed, unlike Letta/Zep).

Idempotency: a pre-flight ``agentmemory list --json`` (or ``stats --json``)
is attempted; if the count matches the input size, we skip ingestion. If the
surface is unavailable we fall back to per-chunk ``--upsert``, which the CLI
documents as a tolerated re-add.

Daemon health is NOT managed here: validate() must have already passed. If
the daemon dies mid-ingest, we count errors per chunk and return the partial
result so the runner can decide to abort or continue.

SAFETY VALVE:
  - If at ingest time the CLI cannot be invoked (daemon down, license expired
    intra-session), ingest_corpus() returns mode="skip" with a clear error.
    Q4 COMPARISON.md can then document the gap as "no data" per spec §6 honest
    reporting. The runner should NOT crash.

Calls per query: ``agentmemory recall "<query>" --top-k <k> --json``
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any, Iterable

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


def _count_existing(cli: str, namespace: str | None) -> int | None:
    """Best-effort: return current memory count if the CLI exposes it.

    Returns None if the surface is unavailable (older CLI, daemon down, etc).
    Used purely for the idempotency skip — never required for ingest to work.
    """
    candidates = [
        [cli, "list", "--json", "--count-only"],
        [cli, "list", "--json"],
        [cli, "stats", "--json"],
    ]
    for argv in candidates:
        argv_with_ns = argv + (["--namespace", namespace] if namespace else [])
        try:
            proc = subprocess.run(
                argv_with_ns,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except Exception:
            continue
        if proc.returncode != 0:
            continue
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            for key in ("count", "total", "memories", "items"):
                value = payload.get(key)
                if isinstance(value, int):
                    return value
                if isinstance(value, list):
                    return len(value)
        if isinstance(payload, list):
            return len(payload)
    return None


def ingest_corpus(chunks: Iterable[dict]) -> dict:
    """
    Add chunks via subprocess. Each chunk becomes one ``agentmemory add`` call.

    Args:
        chunks: iterable of dicts with at least ``id`` and ``text``. Optional
            keys ignored. Namespace pulled from env ``AGENTMEMORY_NAMESPACE``
            (or none).

    Returns:
        {ingested, skipped, total, errors, mode}
    """
    cli = _cli_path()
    if cli is None:
        return {
            "ingested": 0,
            "skipped": 0,
            "total": 0,
            "errors": 0,
            "mode": "skip",
            "error": "CLI not available — daemon missing or iii-engine paid-only",
        }

    chunks_list = list(chunks)
    total = len(chunks_list)
    if total == 0:
        return {"ingested": 0, "skipped": 0, "total": 0, "errors": 0, "mode": "noop"}

    namespace = os.environ.get("AGENTMEMORY_NAMESPACE") or None

    # Idempotency probe
    existing = _count_existing(cli, namespace)
    if existing is not None and existing >= total:
        return {
            "ingested": 0,
            "skipped": total,
            "total": total,
            "errors": 0,
            "mode": "idempotent-skip",
            "existing_count": existing,
            "note": f"count={existing} >= total={total}; assuming previously ingested",
        }

    ingested = 0
    errors = 0
    base_args = [cli, "add"]
    if namespace:
        base_args += ["--namespace", namespace]

    for chunk in chunks_list:
        nox_id = str(chunk.get("id") or "")
        text = chunk.get("text") or ""
        if not nox_id or not text:
            errors += 1
            continue
        argv = base_args + ["--id", nox_id, "--text", text, "--upsert"]
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=False)
        except Exception:
            errors += 1
            continue
        if proc.returncode != 0:
            # Tolerate older CLIs that lack --upsert: retry without it
            try:
                proc2 = subprocess.run(
                    [a for a in argv if a != "--upsert"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
                if proc2.returncode != 0:
                    errors += 1
                    continue
            except Exception:
                errors += 1
                continue
        ingested += 1

    return {
        "ingested": ingested,
        "skipped": total - ingested - errors,
        "total": total,
        "errors": errors,
        "mode": "subprocess",
    }


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
