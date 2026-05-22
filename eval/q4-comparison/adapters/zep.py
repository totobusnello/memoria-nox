"""
Zep adapter — local self-hosted Zep Open Source via Docker Compose.

Repo: https://github.com/getzep/zep  (Apache-2.0, 1.8k+ stars)
Install: docker compose -f compose/docker-compose.yml up -d
Python client: pip install zep-python==2.4.0 (Zep OSS API surface)

Zep stores "messages" inside "sessions". For LongMemEval / LoCoMo we map
each conversation session → Zep session_id, ingest messages, then call
`zep.memory.search_session(session_id, query, limit=k)` per query.

NOTE: Zep Cloud (SaaS) needs ZEP_API_KEY. We bench OSS (self-hosted) only
for the fair comparison; document SaaS variant separately if measured.
"""

from __future__ import annotations

import os
from typing import Any

NAME = "zep"
VERSION_PIN = "zep-python==2.4.0 + ghcr.io/getzep/zep:0.27.2 (OSS, Docker)"
# OSS Zep does NOT require an API key in default config. Cloud variant does.
REQUIRES_ENV: list[str] = []
INSTALL_HINT = (
    "pip install 'zep-python==2.4.0' && "
    "docker compose -f compose/docker-compose.yml up -d zep postgres"
)

_DEFAULT_BASE = "http://127.0.0.1:8000"
_TIMEOUT_S = 30
_client = None


def _base_url() -> str:
    return (os.environ.get("ZEP_API_URL") or _DEFAULT_BASE).rstrip("/")


def validate() -> dict:
    try:
        import zep_python  # noqa: F401
    except ImportError as exc:
        return {
            "ok": False,
            "error": f"zep-python not installed: {exc}",
            "version": None,
            "notes": INSTALL_HINT,
        }
    # Cloud needs ZEP_API_KEY; OSS does not. We only flag if user explicitly
    # asked for cloud (env var ZEP_USE_CLOUD=1).
    if os.environ.get("ZEP_USE_CLOUD") == "1" and not os.environ.get("ZEP_API_KEY"):
        return {
            "ok": False,
            "error": "ZEP_USE_CLOUD=1 but ZEP_API_KEY not set",
            "version": None,
            "notes": "Either unset ZEP_USE_CLOUD or export ZEP_API_KEY",
        }
    return {
        "ok": True,
        "error": None,
        "version": getattr(__import__("zep_python"), "__version__", "unknown"),
        "notes": (
            "Zep OSS expected at "
            + _base_url()
            + " — run `docker compose -f compose/docker-compose.yml up -d` first"
        ),
    }


def setup() -> None:
    """Initialize Zep client + ping /healthz."""
    global _client
    if _client is not None:
        return
    from zep_python.client import Zep

    _client = Zep(base_url=_base_url(), api_key=os.environ.get("ZEP_API_KEY", "no-auth"))


def teardown() -> None:
    global _client
    _client = None


def search(query: str, k: int = 10) -> list[dict]:
    if _client is None:
        setup()

    # Q4 runner is expected to pre-create a session_id per LongMemEval/LoCoMo
    # conversation and seed it via zep.memory.add(...). For pure search across
    # all ingested data, use memory.search_session with a shared/default session
    # OR iterate sessions. Default: ZEP_SESSION_ID from env (single big session).
    session_id = os.environ.get("ZEP_SESSION_ID", "q4-default-session")

    # zep_python 2.x: client.memory.search_sessions OR per-session search
    results = _client.memory.search_session(  # type: ignore[union-attr]
        session_id=session_id,
        text=query,
        limit=k,
        search_scope="messages",
    )

    items: list[dict[str, Any]] = []
    for r in results or []:
        # Zep returns MessageSearchResult { message: {content, ...}, score, ... }
        msg = getattr(r, "message", None) or {}
        items.append(
            {
                "id": str(getattr(msg, "uuid", "") or getattr(msg, "id", "") or ""),
                "score": float(getattr(r, "score", 0.0) or 0.0),
                "text": getattr(msg, "content", "") or "",
                "source": session_id,
            }
        )
    return items[:k]
