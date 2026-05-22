"""
Letta (ex-MemGPT) adapter — Python SDK + local server.

Repo: https://github.com/letta-ai/letta  (Apache-2.0, 14k+ stars)
Install: pip install letta==0.6.6 + `letta server` (or Docker compose)

Letta is a full agent runtime; we bench RECALL-ONLY mode (archival_memory_search)
to keep the comparison about retrieval quality, not about agent loop quality.

The runner pre-creates a Letta agent, ingests chunks via insert_archival_memory,
then per query calls `client.agents.archival_memory_search(agent_id, query, k)`.
"""

from __future__ import annotations

import os
from typing import Any

NAME = "letta"
VERSION_PIN = "letta==0.6.6"  # confirm latest stable at install time
REQUIRES_ENV = ["OPENAI_API_KEY"]  # Letta defaults to OpenAI embeddings
INSTALL_HINT = (
    "pip install 'letta==0.6.6' && "
    "letta server --port 8283   # OR docker compose up letta (see compose/)"
)

_DEFAULT_BASE = "http://127.0.0.1:8283"
_client = None
_agent_id: str | None = None


def _base_url() -> str:
    return (os.environ.get("LETTA_BASE_URL") or _DEFAULT_BASE).rstrip("/")


def validate() -> dict:
    try:
        import letta  # noqa: F401
    except ImportError as exc:
        return {
            "ok": False,
            "error": f"letta not installed: {exc}",
            "version": None,
            "notes": INSTALL_HINT,
        }
    missing = [v for v in REQUIRES_ENV if not os.environ.get(v)]
    if missing:
        return {
            "ok": False,
            "error": f"missing env: {', '.join(missing)}",
            "version": getattr(__import__("letta"), "__version__", "unknown"),
            "notes": "export OPENAI_API_KEY=...",
        }
    return {
        "ok": True,
        "error": None,
        "version": getattr(__import__("letta"), "__version__", "unknown"),
        "notes": (
            "Letta server expected at "
            + _base_url()
            + " — start with `letta server` or docker compose."
        ),
    }


def setup() -> None:
    """Initialize Letta client + create or attach Q4 agent."""
    global _client, _agent_id
    if _client is not None:
        return
    from letta_client import Letta

    _client = Letta(base_url=_base_url())

    # Reuse existing Q4 agent if present, else create one
    agent_name = os.environ.get("LETTA_AGENT_NAME", "q4-comparison-agent")
    existing = _client.agents.list(name=agent_name)
    if existing:
        _agent_id = existing[0].id
    else:
        created = _client.agents.create(
            name=agent_name,
            embedding_config={"embedding_endpoint_type": "openai"},
        )
        _agent_id = created.id


def teardown() -> None:
    global _client, _agent_id
    _client = None
    _agent_id = None


def search(query: str, k: int = 10) -> list[dict]:
    if _client is None or _agent_id is None:
        setup()

    # archival_memory_search returns ranked passages
    results = _client.agents.archival_memory_search(  # type: ignore[union-attr]
        agent_id=_agent_id,
        query=query,
        limit=k,
    )

    items: list[dict[str, Any]] = []
    for r in results or []:
        items.append(
            {
                "id": str(getattr(r, "id", "") or ""),
                "score": float(getattr(r, "score", 0.0) or 0.0),
                "text": getattr(r, "text", "") or getattr(r, "content", "") or "",
                "source": getattr(r, "source", None),
            }
        )
    return items[:k]
