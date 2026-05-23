"""
agentmemory adapter — REST API (npm package, server mode).

Repo: https://github.com/rohitg00/agentmemory  (Apache-2.0 CLI; iii-engine ELv2 self-host OK)
Install: npm install -g @agentmemory/agentmemory   # v0.9.21 verified 2026-05-23
Version: v0.9.21 (latest as of 2026-05-23 probe)

PROBE FINDINGS (2026-05-23):
  - npm install succeeds, iii-engine auto-downloads (not paid-only).
  - CLI has NO `add`/`recall` subcommands — it is server-only (REST on :3111).
  - `POST /agentmemory/remember` does not accept custom IDs; issues `mem_xxx` system IDs.
  - ID round-trip: nox-mem chunk id embedded as `[nox_id:<id>]` prefix in content,
    parsed back from search results. Not ideal but the only option without patching upstream.
  - Smoke test passed: 5 chunks ingested, search returned 5 hits, scores ~0.68.
  - `agentmemory --version` hangs (daemon mode); version confirmed via npm view / package.json.

DAEMON LIFECYCLE:
  The daemon must be running before validate() / ingest_corpus() / search() are called.
  Start it externally:
      agentmemory &
      sleep 5 && curl http://localhost:3111/agentmemory/livez

  validate() hits /livez to confirm the daemon is up. If not, it returns ok=False with
  a clear error so the runner can skip agentmemory from the Q4 run (per spec §4).

INGESTION MODEL:
  ingest_corpus(chunks) posts each chunk to POST /agentmemory/remember.
  Idempotency: best-effort skip if /stats endpoint returns count >= input size.
  Content format: "[nox_id:<id>] <text>" so search() can parse the nox-mem id back.

SEARCH MODEL:
  POST /agentmemory/search with {query, limit}. Returns list with .observation.id (mem_xxx)
  and .observation.narrative or .observation.facts. The nox-mem id is parsed from the content
  prefix "[nox_id:<id>]". Falls back to mem_xxx if prefix not found.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Iterable

try:
    import requests as _requests
    _requests_available = True
except ImportError:
    _requests_available = False

NAME = "agentmemory"
VERSION_PIN = "@agentmemory/agentmemory@0.9.21 (verified 2026-05-23)"
REQUIRES_ENV: list[str] = []  # No API keys needed for local run
INSTALL_HINT = (
    "npm install -g '@agentmemory/agentmemory'   "
    "# then: agentmemory & (start daemon); curl http://localhost:3111/agentmemory/livez"
)

_NOX_ID_RE = re.compile(r"^\[nox_id:([^\]]+)\]\s*")


def _base_url() -> str:
    return os.environ.get("AGENTMEMORY_URL", "http://localhost:3111")


def _get(path: str, timeout: int = 10) -> dict:
    if not _requests_available:
        raise RuntimeError("requests not installed — pip install requests")
    url = _base_url() + path
    resp = _requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _post(path: str, body: dict, timeout: int = 60) -> dict:
    if not _requests_available:
        raise RuntimeError("requests not installed — pip install requests")
    url = _base_url() + path
    resp = _requests.post(url, json=body, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def validate() -> dict:
    if not _requests_available:
        return {
            "ok": False,
            "error": "requests library not installed (pip install requests)",
            "version": None,
            "notes": INSTALL_HINT,
        }
    try:
        data = _get("/agentmemory/livez", timeout=5)
    except Exception as exc:
        return {
            "ok": False,
            "error": f"daemon not reachable at {_base_url()}: {exc}",
            "version": None,
            "notes": (
                "Start daemon first: `agentmemory &` then `sleep 5`. "
                "Check AGENTMEMORY_URL env if using non-default port."
            ),
        }
    if data.get("status") != "ok":
        return {
            "ok": False,
            "error": f"livez returned unexpected body: {data}",
            "version": None,
            "notes": "Daemon running but unhealthy",
        }
    return {
        "ok": True,
        "error": None,
        "version": VERSION_PIN,
        "notes": (
            f"Daemon live at {_base_url()}. "
            "ID round-trip via [nox_id:...] prefix in content. "
            "iii-engine ELv2: self-host OK for benchmark."
        ),
    }


def setup() -> None:
    return None


def teardown() -> None:
    return None


def _count_existing() -> int | None:
    """Best-effort count of existing memories via stats endpoint."""
    for path in ["/agentmemory/stats", "/agentmemory/health"]:
        try:
            data = _get(path, timeout=5)
            for key in ("total", "count", "memories", "totalMemories"):
                val = data.get(key)
                if isinstance(val, int):
                    return val
        except Exception:
            continue
    return None


def ingest_corpus(chunks: Iterable[dict]) -> dict:
    """
    Add chunks via POST /agentmemory/remember.

    Content is prefixed with `[nox_id:<id>]` so search() can parse the
    nox-mem id back from results (agentmemory doesn't support custom IDs).

    Args:
        chunks: iterable of dicts with at least ``id`` and ``text``.

    Returns:
        {ingested, skipped, total, errors, mode}
    """
    chunks_list = list(chunks)
    total = len(chunks_list)
    if total == 0:
        return {"ingested": 0, "skipped": 0, "total": 0, "errors": 0, "mode": "noop"}

    # Idempotency probe
    existing = _count_existing()
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

    for chunk in chunks_list:
        nox_id = str(chunk.get("id") or "")
        text = chunk.get("text") or ""
        if not nox_id or not text:
            errors += 1
            continue
        # Embed nox-mem id as parseable prefix
        content = f"[nox_id:{nox_id}] {text}"
        try:
            resp = _post("/agentmemory/remember", {"content": content, "type": "observation"})
            if resp.get("success"):
                ingested += 1
            else:
                errors += 1
        except Exception:
            errors += 1

    return {
        "ingested": ingested,
        "skipped": total - ingested - errors,
        "total": total,
        "errors": errors,
        "mode": "rest",
    }


def search(query: str, k: int = 10) -> list[dict]:
    """
    POST /agentmemory/search and normalize results.

    Returns list of {id, score, text, source} dicts.
    id is parsed from [nox_id:...] prefix if present; falls back to mem_xxx.
    """
    payload: dict[str, Any] = {"query": query, "limit": k, "format": "full"}
    data = _post("/agentmemory/search", payload)

    results = data if isinstance(data, list) else data.get("results", [])
    normalized: list[dict] = []
    for item in results[:k]:
        obs = item.get("observation") or {}
        score = float(item.get("score") or 0.0)
        mem_id = str(obs.get("id") or "")
        # Extract content from narrative or facts list
        narrative = obs.get("narrative") or ""
        facts = obs.get("facts") or []
        content = narrative or (facts[0] if facts else "")
        # Parse nox-mem id from prefix
        m = _NOX_ID_RE.match(content)
        if m:
            nox_id = m.group(1)
            text = content[m.end():]
        else:
            nox_id = mem_id
            text = content
        normalized.append({
            "id": nox_id,
            "score": score,
            "text": text,
            "source": obs.get("sessionId") or None,
        })
    return normalized
