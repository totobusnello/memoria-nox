"""
Mem0 adapter — Python SDK (mem0ai).

Repo: https://github.com/mem0ai/mem0  (Apache-2.0, 53k+ stars as of 2026-05-21)
Install: pip install mem0ai==0.1.114 (pinned 2026-05-18; bump if newer minor)

Mem0's default config requires OPENAI_API_KEY for embeddings + LLM extraction.
For a fair comparison we keep defaults (per spec §5: "each system uses native
defaults"). Vector store: Chroma in-process (no external daemon).

Per-query call uses `Memory.search(query, user_id=<id>)` — Mem0 returns
ranked memories with a relevance score.
"""

from __future__ import annotations

import os
from typing import Any

NAME = "mem0"
VERSION_PIN = "mem0ai==0.1.114"  # confirm latest stable at install time
REQUIRES_ENV = ["OPENAI_API_KEY"]
INSTALL_HINT = "pip install 'mem0ai==0.1.114'"

_USER_ID_DEFAULT = "q4-comparison-user"
_client = None  # singleton, initialized in setup()


def validate() -> dict:
    try:
        import mem0  # noqa: F401
    except ImportError as exc:
        return {
            "ok": False,
            "error": f"mem0 not installed: {exc}",
            "version": None,
            "notes": INSTALL_HINT,
        }
    missing = [v for v in REQUIRES_ENV if not os.environ.get(v)]
    if missing:
        return {
            "ok": False,
            "error": f"missing env: {', '.join(missing)}",
            "version": getattr(__import__("mem0"), "__version__", "unknown"),
            "notes": "export OPENAI_API_KEY=...",
        }
    return {
        "ok": True,
        "error": None,
        "version": getattr(__import__("mem0"), "__version__", "unknown"),
        "notes": "Mem0 defaults: Chroma vector store + OpenAI embeddings",
    }


def setup() -> None:
    """Initialize Mem0 client (singleton)."""
    global _client
    if _client is not None:
        return
    from mem0 import Memory

    _client = Memory()  # defaults: Chroma + OpenAI


def teardown() -> None:
    """Mem0's in-process Chroma is GC'd with the process."""
    global _client
    _client = None


def search(query: str, k: int = 10) -> list[dict]:
    """Mem0 returns a list of memory dicts with text + score."""
    if _client is None:
        setup()

    user_id = os.environ.get("MEM0_USER_ID", _USER_ID_DEFAULT)
    raw: list[dict[str, Any]] = _client.search(query=query, user_id=user_id, limit=k)  # type: ignore[union-attr]

    # Mem0 0.1.x returns: [{'id', 'memory', 'score', 'metadata', ...}]
    return [
        {
            "id": str(item.get("id") or ""),
            "score": float(item.get("score") or 0.0),
            "text": item.get("memory") or item.get("text") or "",
            "source": (item.get("metadata") or {}).get("source"),
        }
        for item in (raw or [])[:k]
    ]
