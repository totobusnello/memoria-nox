"""
Letta (ex-MemGPT) adapter — Python SDK + local server.

Repo: https://github.com/letta-ai/letta  (Apache-2.0, 14k+ stars)
Install: pip install letta==0.6.6 + `letta server` (or Docker compose)

Letta is a full agent runtime; we bench RECALL-ONLY mode (archival_memory_search)
to keep the comparison about retrieval quality, not about agent loop quality.

INGESTION MODEL
---------------
Letta stores ranked passages inside an "archival memory" attached to an
agent. We insert each chunk via ``client.agents.archival_memory_insert(
agent_id, content=text)`` which returns a server-side passage_id (uuid).

Round-tripping the gold chunk id back from search results requires a local
``_id_map``: nox_id -> passage_id. The reverse map is built incrementally
during ingest and persisted to ``output/_state/letta-id-map.json`` so the
runner can call ingest once and search() many times across processes.

If a passage_id returned by search is not in the reverse map (e.g., manual
insert before ingest_corpus, or partial ingest), we fall back to using the
passage_id as the result id. The aggregator will score it 0 against the
gold set, which is the honest outcome.

INGEST FLOW (called by ``ingest_corpus`` before queries):
  for chunk in chunks:
      passage = client.agents.archival_memory_insert(agent_id, content=chunk["text"])
      _id_map[chunk["id"]] = passage.id

SEARCH FLOW:
  results = client.agents.archival_memory_search(agent_id, query, limit=k)
  for r in results:
      gold_id = _reverse_id_map.get(r.id, r.id)
      yield {"id": gold_id, "score": r.score, "text": r.text, ...}

Idempotency: if ``archival_memory_list`` returns count >= len(chunks) AND
the id-map already covers every input id, ingest_corpus() is a no-op.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

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

# id-map: nox_id -> passage_id (Letta's archival memory id). Loaded from disk
# at setup() and rewritten on every ingest_corpus() call.
_id_map: dict[str, str] = {}
_reverse_id_map: dict[str, str] = {}  # passage_id -> nox_id


def _base_url() -> str:
    return (os.environ.get("LETTA_BASE_URL") or _DEFAULT_BASE).rstrip("/")


def _state_path() -> Path:
    """Persistence path for the id-map across runner invocations."""
    here = Path(__file__).parent.parent  # adapters/ -> q4-comparison/
    return here / "output" / "_state" / "letta-id-map.json"


def _load_id_map() -> None:
    global _id_map, _reverse_id_map
    p = _state_path()
    if p.exists():
        try:
            _id_map = json.loads(p.read_text())
            _reverse_id_map = {v: k for k, v in _id_map.items()}
            return
        except (json.JSONDecodeError, OSError):
            pass
    _id_map = {}
    _reverse_id_map = {}


def _save_id_map() -> None:
    p = _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(_id_map, indent=2, sort_keys=True))


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
    """Initialize Letta client + create or attach Q4 agent (idempotent).

    Does NOT ingest the corpus — call ``ingest_corpus(chunks)`` separately
    (zep-parity contract). The agent is created or reused; the id-map is
    loaded from disk so previous ingestions remain addressable.
    """
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

    _load_id_map()


def teardown() -> None:
    global _client, _agent_id
    _client = None
    _agent_id = None


def ingest_corpus(chunks: Iterable[dict]) -> dict:
    """
    Insert each chunk into Letta's archival memory.

    Args:
        chunks: iterable of dicts with at least ``id`` and ``text``. Other keys
            (``dataset``, ``source``, ``conv_id``) are ignored — Letta has no
            metadata channel on archival passages in the public 0.6.x API.

    Returns:
        {ingested, skipped, total, errors, agent_id, mode}
    """
    if _client is None or _agent_id is None:
        setup()

    chunks_list = list(chunks)
    total = len(chunks_list)
    if total == 0:
        return {
            "ingested": 0,
            "skipped": 0,
            "total": 0,
            "errors": 0,
            "agent_id": _agent_id,
            "mode": "noop",
        }

    # Idempotency probe: count existing archival passages for this agent.
    # If count >= input total AND id-map already covers every input id, skip.
    try:
        existing_passages = _client.agents.archival_memory_list(  # type: ignore[union-attr]
            agent_id=_agent_id,
            limit=10000,
        )
        existing_count = len(list(existing_passages or []))
    except Exception:
        existing_count = 0

    input_ids = {str(c.get("id") or "") for c in chunks_list if c.get("id")}
    mapped = set(_id_map.keys()) & input_ids
    if existing_count >= total and len(mapped) == len(input_ids):
        return {
            "ingested": 0,
            "skipped": total,
            "total": total,
            "errors": 0,
            "agent_id": _agent_id,
            "mode": "idempotent-skip",
            "existing_count": existing_count,
        }

    ingested = 0
    errors = 0
    for chunk in chunks_list:
        nox_id = str(chunk.get("id") or "")
        text = chunk.get("text") or ""
        if not nox_id or not text:
            errors += 1
            continue
        if nox_id in _id_map:
            # Already inserted in a previous (partial) ingest
            continue
        try:
            passage = _client.agents.archival_memory_insert(  # type: ignore[union-attr]
                agent_id=_agent_id,
                content=text,
            )
            passage_id = (
                getattr(passage, "id", None)
                or (passage.get("id") if isinstance(passage, dict) else None)
                or ""
            )
            if passage_id:
                _id_map[nox_id] = str(passage_id)
                _reverse_id_map[str(passage_id)] = nox_id
            ingested += 1
        except Exception:
            errors += 1

    _save_id_map()

    return {
        "ingested": ingested,
        "skipped": total - ingested - errors,
        "total": total,
        "errors": errors,
        "agent_id": _agent_id,
        "mode": "fresh",
    }


def search(query: str, k: int = 10) -> list[dict]:
    if _client is None or _agent_id is None:
        setup()

    results = _client.agents.archival_memory_search(  # type: ignore[union-attr]
        agent_id=_agent_id,
        query=query,
        limit=k,
    )

    items: list[dict[str, Any]] = []
    for r in results or []:
        passage_id = str(getattr(r, "id", "") or "")
        # Round-trip to nox-mem id if the map knows the passage
        nox_id = _reverse_id_map.get(passage_id, passage_id)
        items.append(
            {
                "id": nox_id,
                "score": float(getattr(r, "score", 0.0) or 0.0),
                "text": getattr(r, "text", "") or getattr(r, "content", "") or "",
                "source": getattr(r, "source", None),
            }
        )
    return items[:k]
