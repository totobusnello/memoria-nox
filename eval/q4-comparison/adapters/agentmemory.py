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
  - /agentmemory/stats → 404; count via GET /agentmemory/memories (len of .memories list).
  - POST /agentmemory/search → dict with .results key (not bare list).

DAEMON LIFECYCLE:
  The daemon must be running before validate() / ingest_corpus() / search() are called.
  Start it externally:
      agentmemory &
      sleep 5 && curl http://localhost:3111/agentmemory/livez

  validate() hits /livez to confirm the daemon is up. If not, it returns ok=False with
  a clear error so the runner can skip agentmemory from the Q4 run (per spec §4).

INGESTION MODEL (setup()):
  setup() ingests the Q4 corpus from eval/q4-comparison/cache/{locomo,longmemeval}.jsonl
  using lib.corpus_loader. Corpus is loaded via shared JSONL cache (downloaded on first
  use by corpus_loader). setup() is idempotent: skips re-ingest if
  GET /agentmemory/memories count >= expected corpus size.

  AGENTMEMORY_INGEST_LIMIT=N  — limit chunks to N (useful for smoke/unit tests)
  AGENTMEMORY_FORCE_REINGEST=1 — skip idempotency check and always ingest

  Content format: "[nox_id:<id>] <text>" so search() can parse the nox-mem id back.

SEARCH MODEL:
  POST /agentmemory/search with {query, limit}. Returns dict with .results list.
  Each item has .observation.narrative or .observation.facts[0]. The nox-mem id is
  parsed from the content prefix "[nox_id:<id>]". Falls back to mem_xxx if prefix not found.

SMOKE VALIDATION (2026-05-24):
  Bug found: pre-fix setup() was a no-op — corpus never ingested → 0 search results.
  Fix: setup() now calls _ingest_from_corpus_cache() using lib.corpus_loader.
  Verified: gold_hits > 0 on locomo dry-run-sample.json with --limit 5 post-fix.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
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

HERE = Path(__file__).resolve().parent.parent  # eval/q4-comparison/
sys.path.insert(0, str(HERE))

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


def _count_existing() -> int | None:
    """Return the number of memories currently stored in agentmemory.

    Uses GET /agentmemory/memories — the only reliable count endpoint.
    /agentmemory/stats → 404 in v0.9.21.
    Returns None if the endpoint is unreachable.
    """
    try:
        data = _get("/agentmemory/memories", timeout=10)
        mems = data.get("memories")
        if isinstance(mems, list):
            return len(mems)
    except Exception:
        pass
    return None


def _ingest_from_corpus_cache(datasets: list[str] = ("locomo", "longmemeval")) -> dict:
    """
    Ingest Q4 corpus chunks from the shared JSONL cache into agentmemory.

    Reads from eval/q4-comparison/cache/{dataset}.jsonl (built by lib.corpus_loader).
    Content format: "[nox_id:<id>] <text>" for ID round-trip in search().

    Env overrides:
      AGENTMEMORY_INGEST_LIMIT=N       — stop after N chunks (smoke/unit tests)
      AGENTMEMORY_FORCE_REINGEST=1     — bypass idempotency check
    """
    from lib.corpus_loader import CACHE_DIR, load_locomo_corpus, load_longmemeval_corpus  # type: ignore[import]

    force = os.environ.get("AGENTMEMORY_FORCE_REINGEST", "").lower() in ("1", "true", "yes")
    limit_raw = os.environ.get("AGENTMEMORY_INGEST_LIMIT", "")
    limit: int | None = int(limit_raw) if limit_raw.isdigit() else None

    # Count expected chunks
    total_expected = 0
    for ds in datasets:
        cache_path = CACHE_DIR / f"{ds}.jsonl"
        if cache_path.exists():
            total_expected += sum(1 for _ in cache_path.open())
    if limit is not None:
        total_expected = min(total_expected, limit)

    # Idempotency check
    if not force and total_expected > 0:
        existing = _count_existing()
        if existing is not None and existing >= total_expected:
            print(
                f"[agentmemory] corpus already ingested ({existing} memories, "
                f"expected ~{total_expected}). Skipping. Set AGENTMEMORY_FORCE_REINGEST=1 to override."
            )
            return {
                "ingested": 0,
                "skipped": total_expected,
                "total": total_expected,
                "errors": 0,
                "mode": "idempotent-skip",
                "existing_count": existing,
            }

    print(f"[agentmemory] ingesting corpus (expected ~{total_expected} chunks, limit={limit})...")
    ingested = 0
    errors = 0
    done = False

    for ds in datasets:
        if done:
            break
        cache_path = CACHE_DIR / f"{ds}.jsonl"
        if not cache_path.exists():
            # Trigger download via corpus_loader
            print(f"[agentmemory] cache miss for {ds} — triggering corpus_loader download...")
            if ds == "locomo":
                list(load_locomo_corpus())
            else:
                list(load_longmemeval_corpus())

        if not cache_path.exists():
            print(f"[agentmemory] WARNING: {cache_path} still missing after download attempt, skipping {ds}")
            continue

        with cache_path.open() as fh:
            for i, line in enumerate(fh, 1):
                if limit is not None and (ingested + errors) >= limit:
                    done = True
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    errors += 1
                    continue
                nox_id = str(row.get("id") or "")
                text = row.get("text") or ""
                if not nox_id or not text:
                    errors += 1
                    continue
                content = f"[nox_id:{nox_id}] {text}"
                try:
                    resp = _post(
                        "/agentmemory/remember",
                        {"content": content, "type": "observation"},
                        timeout=30,
                    )
                    if resp.get("success"):
                        ingested += 1
                    else:
                        errors += 1
                except Exception as exc:
                    errors += 1
                    if errors <= 3:
                        print(f"[agentmemory] ingest error chunk {nox_id!r}: {exc}")

                if ingested % 100 == 0 and ingested > 0:
                    print(f"[agentmemory]   ingested {ingested} / ~{total_expected} ({errors} errors)")

    print(f"[agentmemory] ingestion complete: {ingested} ok, {errors} errors")
    return {
        "ingested": ingested,
        "skipped": 0,
        "total": ingested + errors,
        "errors": errors,
        "mode": "rest",
    }


def setup() -> None:
    """
    Validate daemon + ingest Q4 corpus from shared JSONL cache.

    Idempotent: skips re-ingest if memory count >= expected corpus size.
    Env: AGENTMEMORY_INGEST_LIMIT=N  (smoke: small N); AGENTMEMORY_FORCE_REINGEST=1.
    """
    v = validate()
    if not v["ok"]:
        print(f"[agentmemory] setup: daemon not available — {v['error']}")
        print("[agentmemory] Start daemon: agentmemory & ; sleep 5")
        return

    _ingest_from_corpus_cache()


def teardown() -> None:
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
