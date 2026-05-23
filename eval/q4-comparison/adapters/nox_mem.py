"""
nox-mem adapter — HTTP /api/search on port 18802.

Reference implementation: this is the system being benchmarked. Uses the
production HTTP endpoint so the measurement matches what real callers hit.

Setup expectation: nox-mem-api running on $NOX_API_PORT (default 18802) with
production corpus loaded. Set NOX_API_BASE to point elsewhere for a remote run.

The adapter does NOT ingest — Q4 assumes the corpus is already indexed in
the target nox-mem DB (per spec §5: "competitors get IDENTICAL chunk corpus
that nox-mem uses"). Ingest happens out-of-band before runner.py starts.
"""

from __future__ import annotations

import os
from typing import Any

NAME = "nox-mem"
VERSION_PIN = "git-sha (resolve at runtime via `git rev-parse HEAD`)"
REQUIRES_ENV: list[str] = []  # NOX_API_BASE/NOX_API_PORT optional, defaults exist
INSTALL_HINT = (
    "Already in this repo. Run `npm run build && node dist/index.js api` "
    "on the VPS, or set NOX_API_BASE to an existing endpoint."
)

_DEFAULT_BASE = "http://127.0.0.1"
_DEFAULT_PORT = "18802"
_TIMEOUT_S = 30


def _base_url() -> str:
    base = os.environ.get("NOX_API_BASE")
    if base:
        return base.rstrip("/")
    port = os.environ.get("NOX_API_PORT", _DEFAULT_PORT)
    return f"{_DEFAULT_BASE}:{port}"


def validate() -> dict:
    """Static validation — module import + endpoint URL construction only."""
    try:
        import requests  # noqa: F401
    except ImportError as exc:  # pragma: no cover — exercised at smoke time
        return {
            "ok": False,
            "error": f"requests not installed: {exc}",
            "version": None,
            "notes": "pip install requests",
        }
    return {
        "ok": True,
        "error": None,
        "version": VERSION_PIN,
        "notes": f"endpoint resolves to {_base_url()}/api/search",
    }


def setup() -> None:
    """No-op — nox-mem-api is expected to be running externally."""
    return None


def teardown() -> None:
    """No-op."""
    return None


def search(query: str, k: int = 10) -> list[dict]:
    """Hit /api/search and normalize to the adapter contract."""
    import requests

    resp = requests.get(
        f"{_base_url()}/api/search",
        params={"q": query, "limit": k, "format": "json"},
        timeout=_TIMEOUT_S,
    )
    resp.raise_for_status()
    payload = resp.json()

    # /api/search returns array directly (verified 2026-05-24 via tunnel against prod VPS).
    # Defensive fallback for dict-wrapped variants kept for forward-compat.
    if isinstance(payload, list):
        items_raw: list[dict[str, Any]] = payload
    elif isinstance(payload, dict):
        items_raw = payload.get("results") or payload.get("items") or []
    else:
        items_raw = []

    return [
        {
            "id": str(item.get("id") or item.get("chunk_id") or ""),
            "score": float(item.get("score") or item.get("rrf_score") or 0.0),
            "text": item.get("chunk_text") or item.get("text") or "",
            "source": item.get("source_file") or item.get("source") or None,
        }
        for item in items_raw[:k]
    ]
