"""
Letta (ex-MemGPT) adapter — Python SDK + local server.

Repo: https://github.com/letta-ai/letta  (Apache-2.0, 14k+ stars)
Install: pip install letta==0.6.6 letta-client==0.1.46
         docker compose -f compose/docker-compose.yml --profile letta up -d

Letta is a full agent runtime; we bench RECALL-ONLY mode (archival_memory_search)
to keep the comparison about retrieval quality, not about agent loop quality.

API NOTES (letta-client 0.1.46 + letta/letta:0.6.6 Docker)
------------------------------------------------------------
The SDK's passages.create() calls the wrong URL (/archival-memory instead of
/archival). We bypass the SDK for archival operations and use direct REST calls
via urllib.request.

Agent creation requires (in 0.6.6):
  - memory_blocks (list of CreateBlock) — human + persona required
  - llm_config (LlmConfig) — model/endpoint/context_window
  - embedding_config (EmbeddingConfig) — model/dim/chunk_size

Semantic search is done via agent message loop: we send a user message, the
agent calls its built-in archival_memory_search tool, and returns results in
the tool_return field as a Python repr string:
  "([{'timestamp': ..., 'content': ...}, ...], total_count)"
We parse that with ast.literal_eval and assign rank-based scores (1/(1+rank))
since Letta does not expose numeric relevance scores in the tool_return.

CORPUS INGESTION
----------------
setup() triggers corpus ingest (like mem0 adapter). Controlled via:
  LETTA_INGEST_LIMIT  — cap total chunks (default: full corpus)
  LETTA_FORCE_REINGEST=1 — force re-ingest even if count matches
  LETTA_AGENT_NAME    — agent name (default: q4-comparison-agent)

ID ROUND-TRIP
-------------
Letta's archival_memory_search returns text, not passage_id. We maintain a
text -> nox_id reverse map (_reverse_text_map) populated during ingest.
Match is exact; if a chunk is truncated by Letta we fall back to a prefix key.
Unmatched passages get an "unknown::" prefix ID and score 0 against gold.
"""

from __future__ import annotations

import ast
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable

NAME = "letta"
VERSION_PIN = "letta==0.6.6 letta-client==0.1.46"
REQUIRES_ENV = ["OPENAI_API_KEY"]  # Letta defaults to OpenAI embeddings
INSTALL_HINT = (
    "pip install 'letta==0.6.6' 'letta-client==0.1.46' && "
    "docker compose -f compose/docker-compose.yml --profile letta up -d"
)

_DEFAULT_BASE = "http://127.0.0.1:8283"
_client = None
_agent_id: str | None = None

# Paths
HERE = Path(__file__).parent.parent  # adapters/ -> q4-comparison/

# Ensure lib/ is importable
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

# Text-keyed maps (letta archival search returns text not passage ids)
# nox_id -> chunk_text  (persisted to disk)
_text_map: dict[str, str] = {}
# chunk_text -> nox_id  (in-memory reverse map, rebuilt from _text_map)
_reverse_text_map: dict[str, str] = {}


def _base_url() -> str:
    return (os.environ.get("LETTA_BASE_URL") or _DEFAULT_BASE).rstrip("/")


def _state_path() -> Path:
    """Persistence path for the id-map across runner invocations."""
    return HERE / "output" / "_state" / "letta-id-map.json"


def _load_id_map() -> None:
    global _text_map, _reverse_text_map
    p = _state_path()
    if p.exists():
        try:
            _text_map = json.loads(p.read_text())
            _reverse_text_map = {v: k for k, v in _text_map.items()}
            return
        except (json.JSONDecodeError, OSError):
            pass
    _text_map = {}
    _reverse_text_map = {}


def _save_id_map() -> None:
    p = _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(_text_map, indent=2, sort_keys=True))


# ---------------------------------------------------------------------------
# REST helpers (bypass SDK for archival ops due to SDK URL bug in 0.1.46)
# ---------------------------------------------------------------------------


def _rest(
    path: str,
    method: str = "GET",
    body: dict | None = None,
    timeout: int = 30,
) -> Any:
    """Minimal REST helper — urllib only, no extra deps."""
    url = f"{_base_url()}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _archival_insert(agent_id: str, text: str) -> str:
    """Insert a passage into archival memory; return passage id."""
    resp = _rest(f"/v1/agents/{agent_id}/archival", method="POST", body={"text": text})
    if isinstance(resp, list) and resp:
        return str(resp[0].get("id", ""))
    return ""


def _archival_count(agent_id: str) -> int:
    """Return number of archival passages for this agent."""
    try:
        resp = _rest(f"/v1/agents/{agent_id}/archival?limit=10000")
        return len(resp) if isinstance(resp, list) else 0
    except Exception:
        return 0


def _archival_search_via_message(agent_id: str, query: str, k: int) -> list[dict]:
    """
    Trigger archival_memory_search via agent message loop.

    Letta's agent has a built-in archival_memory_search tool. We ask it to
    search and parse the tool_return message.

    Returns list of {content, timestamp} dicts. No relevance score from Letta
    — caller assigns 1/(1+rank) as proxy.
    """
    payload = {
        "messages": [
            {"role": "user", "text": f"Search archival memory for: {query}"}
        ]
    }
    try:
        resp = _rest(
            f"/v1/agents/{agent_id}/messages",
            method="POST",
            body=payload,
            timeout=60,
        )
    except Exception:
        return []

    messages = resp.get("messages", []) if isinstance(resp, dict) else []

    # Parse the first archival_memory_search tool_return
    for msg in messages:
        if msg.get("message_type") != "tool_return_message":
            continue
        tool_return = msg.get("tool_return", "")
        if not tool_return or tool_return == "None":
            continue
        # Format: ([{'timestamp': '...', 'content': '...'}, ...], N)
        try:
            parsed = ast.literal_eval(tool_return)
            if isinstance(parsed, tuple) and len(parsed) == 2:
                items, _total = parsed
            elif isinstance(parsed, list):
                items = parsed
            else:
                continue
            if isinstance(items, list) and items and isinstance(items[0], dict):
                return items[:k]
        except (ValueError, SyntaxError):
            continue

    return []


# ---------------------------------------------------------------------------
# Corpus ingestion (mirrors mem0 adapter pattern)
# ---------------------------------------------------------------------------


def _iter_corpus_chunks():
    """Yield corpus chunks from the shared loader. Respects LETTA_INGEST_LIMIT."""
    from lib.corpus_loader import load_locomo_corpus, load_longmemeval_corpus

    limit_raw = os.environ.get("LETTA_INGEST_LIMIT", "")
    limit = int(limit_raw) if limit_raw.isdigit() else None
    count = 0
    for chunk in load_locomo_corpus():
        yield chunk
        count += 1
        if limit is not None and count >= limit:
            return
    for chunk in load_longmemeval_corpus():
        yield chunk
        count += 1
        if limit is not None and count >= limit:
            return


def _ingest_corpus(agent_id: str) -> dict:
    """
    Ingest corpus into Letta archival memory.

    Idempotent: skips if archival count >= corpus size AND id-map covers all IDs.
    LETTA_FORCE_REINGEST=1 overrides idempotency.

    Returns ingest summary dict.
    """
    chunk_list = list(_iter_corpus_chunks())
    total = len(chunk_list)

    if not chunk_list:
        print(
            "[letta] WARNING: corpus_loader yielded 0 chunks. "
            "Search will return no results."
        )
        return {"ingested": 0, "skipped": 0, "total": 0, "errors": 0, "mode": "noop"}

    limit_raw = os.environ.get("LETTA_INGEST_LIMIT", "")
    if limit_raw.isdigit():
        print(f"[letta] LETTA_INGEST_LIMIT={limit_raw}: capped at {total} chunks")

    force = os.environ.get("LETTA_FORCE_REINGEST", "").lower() in ("1", "true", "yes")

    if not force:
        existing_count = _archival_count(agent_id)
        input_ids = {str(c.id) for c in chunk_list}
        mapped = set(_text_map.keys()) & input_ids
        if existing_count >= total and len(mapped) == len(input_ids):
            print(
                f"[letta] corpus already ingested ({existing_count} passages). "
                "Skipping. Set LETTA_FORCE_REINGEST=1 to re-ingest."
            )
            return {
                "ingested": 0,
                "skipped": total,
                "total": total,
                "errors": 0,
                "mode": "idempotent-skip",
                "existing_count": existing_count,
            }

    print(f"[letta] ingesting {total} corpus chunks into archival memory...")
    ingested = 0
    errors = 0
    for i, chunk in enumerate(chunk_list, start=1):
        nox_id = str(chunk.id)
        text = chunk.text or ""
        if not nox_id or not text:
            errors += 1
            continue
        if nox_id in _text_map and not force:
            continue
        try:
            _archival_insert(agent_id, text)
            _text_map[nox_id] = text
            _reverse_text_map[text] = nox_id
            ingested += 1
        except Exception as exc:
            errors += 1
            if errors <= 5:
                print(f"[letta] ingest error chunk {nox_id!r}: {type(exc).__name__}: {exc}")
        if i % 200 == 0 or i == total:
            print(f"[letta]   ingested {i}/{total} ({errors} errors)")

    _save_id_map()
    print(f"[letta] ingestion complete: {ingested} ok, {errors} errors")
    return {
        "ingested": ingested,
        "skipped": total - ingested - errors,
        "total": total,
        "errors": errors,
        "mode": "fresh",
    }


# ---------------------------------------------------------------------------
# Public adapter interface
# ---------------------------------------------------------------------------


def validate() -> dict:
    missing = [v for v in REQUIRES_ENV if not os.environ.get(v)]
    if missing:
        return {
            "ok": False,
            "error": f"missing env: {', '.join(missing)}",
            "version": "0.6.6",
            "notes": "export OPENAI_API_KEY=...",
        }

    try:
        health = _rest("/v1/health", timeout=5)
        server_version = health.get("version", "unknown")
    except Exception as exc:
        return {
            "ok": False,
            "error": f"Letta server unreachable at {_base_url()}: {exc}",
            "version": "0.6.6",
            "notes": INSTALL_HINT,
        }

    return {
        "ok": True,
        "error": None,
        "version": server_version,
        "notes": (
            f"Letta server {server_version} at {_base_url()}. "
            f"LETTA_INGEST_LIMIT={os.environ.get('LETTA_INGEST_LIMIT', 'unset')} "
            f"(unset = full corpus)"
        ),
    }


def setup() -> None:
    """
    Initialize Letta client, create/reuse agent, ingest corpus.

    Idempotent: re-entrant calls skip init + ingest if already done.
    Controls:
      LETTA_AGENT_NAME    — agent name (default: q4-comparison-agent)
      LETTA_INGEST_LIMIT  — cap total chunks ingested
      LETTA_FORCE_REINGEST=1 — force re-ingest
    """
    global _client, _agent_id
    if _client is not None:
        return

    from letta_client import Letta
    from letta_client.types import CreateBlock, EmbeddingConfig, LlmConfig

    _client = Letta(base_url=_base_url())

    agent_name = os.environ.get("LETTA_AGENT_NAME", "q4-comparison-agent")
    existing = _client.agents.list(name=agent_name)
    if existing:
        _agent_id = existing[0].id
        print(f"[letta] reusing existing agent {_agent_id} ({agent_name})")
    else:
        created = _client.agents.create(
            name=agent_name,
            memory_blocks=[
                CreateBlock(
                    value="Q4 benchmark comparison user context.",
                    label="human",
                ),
                CreateBlock(
                    value=(
                        "I am a memory retrieval agent for the Q4 benchmark. "
                        "I search archival memory for relevant passages."
                    ),
                    label="persona",
                ),
            ],
            llm_config=LlmConfig(
                model="gpt-4o-mini",
                model_endpoint_type="openai",
                model_endpoint="https://api.openai.com/v1",
                context_window=16384,
            ),
            embedding_config=EmbeddingConfig(
                embedding_endpoint_type="openai",
                embedding_endpoint="https://api.openai.com/v1",
                embedding_model="text-embedding-ada-002",
                embedding_dim=1536,
                embedding_chunk_size=300,
            ),
        )
        _agent_id = created.id
        print(f"[letta] created new agent {_agent_id} ({agent_name})")

    _load_id_map()
    _ingest_corpus(_agent_id)


def teardown() -> None:
    global _client, _agent_id
    _client = None
    _agent_id = None


def ingest_corpus(chunks: Iterable[dict]) -> dict:
    """
    External corpus ingest (called by external harnesses, not the runner).

    The runner calls setup() which triggers corpus ingest internally.
    This method handles external chunk dicts with 'id' and 'text' keys.
    """
    if _client is None or _agent_id is None:
        setup()

    chunks_list = list(chunks)
    total = len(chunks_list)
    if total == 0:
        return {
            "ingested": 0, "skipped": 0, "total": 0,
            "errors": 0, "agent_id": _agent_id, "mode": "noop",
        }

    existing_count = _archival_count(_agent_id)  # type: ignore[arg-type]
    input_ids = {str(c.get("id") or "") for c in chunks_list if c.get("id")}
    mapped = set(_text_map.keys()) & input_ids
    if existing_count >= total and len(mapped) == len(input_ids):
        return {
            "ingested": 0, "skipped": total, "total": total,
            "errors": 0, "agent_id": _agent_id, "mode": "idempotent-skip",
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
        if nox_id in _text_map:
            continue
        try:
            _archival_insert(_agent_id, text)  # type: ignore[arg-type]
            _text_map[nox_id] = text
            _reverse_text_map[text] = nox_id
            ingested += 1
        except Exception:
            errors += 1

    _save_id_map()
    return {
        "ingested": ingested, "skipped": total - ingested - errors,
        "total": total, "errors": errors,
        "agent_id": _agent_id, "mode": "fresh",
    }


def search(query: str, k: int = 10) -> list[dict]:
    if _client is None or _agent_id is None:
        setup()

    raw_results = _archival_search_via_message(
        _agent_id, query, k  # type: ignore[arg-type]
    )

    items: list[dict[str, Any]] = []
    for rank, r in enumerate(raw_results):
        content = r.get("content", "")
        # Exact match in reverse map to recover nox_id
        nox_id = _reverse_text_map.get(content, "")
        if not nox_id:
            # Fallback: unknown passage — will score 0 against gold
            nox_id = f"unknown::{content[:40]}"
        items.append(
            {
                "id": nox_id,
                # Letta returns no relevance score; rank-based proxy
                "score": 1.0 / (1 + rank),
                "text": content,
                "source": "letta-archival",
            }
        )
    return items[:k]
