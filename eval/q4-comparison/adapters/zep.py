"""
Zep adapter — local self-hosted Zep Open Source via Docker Compose.

Repo: https://github.com/getzep/zep  (Apache-2.0)
Install: docker compose -f compose/docker-compose.yml up -d zep postgres
Python client: pip install zep-python==2.0.2  (latest available; pinned)

INGESTION MODEL
---------------
Zep stores "messages" inside "sessions". For LongMemEval / LoCoMo we map
each conversation (chunks sharing the same conversation prefix in their ID)
to one Zep session, ingest chunks as messages, and store the original
gold chunk ID in message metadata so search results can be mapped back.

Zep assigns its own UUIDs to messages. The round-trip through metadata is
the ONLY way to recover our gold IDs — the adapter carries that mapping
internally via message metadata["gold_id"].

INGEST FLOW (``ingest_corpus`` → call before first ``search``):
  for conv_id, chunks in grouped_by_conv.items():
      session_id = "q4-" + conv_id          # deterministic, idempotent
      create or reuse session
      for chunk in chunks:
          msg = Message(role="user", content=chunk["text"],
                        metadata={"gold_id": chunk["id"], ...})
          client.memory.add(session_id, messages=[msg])

SEARCH FLOW (``search``):
  client.memory.search_sessions(user_id=ZEP_USER_ID, text=query, limit=k)
  map result.message.metadata["gold_id"] -> returned id field

NOTE: Zep OSS (Community Edition) always searches "facts" regardless of the
``search_scope`` parameter — that param is Cloud-only. For the benchmark we
log this as a known constraint (Zep's fact extraction is its retrieval unit).

NOTE on version pin: zep-python==2.4.0 does not exist on PyPI (latest 2.x is
2.0.2). requirements.txt should use 2.0.2; see REQUIREMENTS.md for the note.
"""

from __future__ import annotations

import os
from typing import Any

NAME = "zep"
VERSION_PIN = "zep-python==2.0.2 + ghcr.io/getzep/zep:0.27.2 (OSS, Docker)"
# OSS Zep does NOT require an API key in default config (ZEP_AUTH_REQUIRED=false).
REQUIRES_ENV: list[str] = []
INSTALL_HINT = (
    "pip install 'zep-python==2.0.2' && "
    "docker compose -f compose/docker-compose.yml up -d zep postgres"
)

_DEFAULT_BASE = "http://127.0.0.1:8000"
# A single Zep "user" groups all Q4 sessions so search_sessions can be
# scoped by user_id — in OSS this is effectively global but forward-compat.
_DEFAULT_USER_ID = "q4-comparison"

_client = None
# All session_ids created during ingest_corpus (for scoping search).
_sessions: list[str] = []
# (unused reserve — Zep metadata carries the round-trip, not an in-process map)
_id_map: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_url() -> str:
    return (os.environ.get("ZEP_API_URL") or _DEFAULT_BASE).rstrip("/")


def _user_id() -> str:
    return os.environ.get("ZEP_USER_ID", _DEFAULT_USER_ID)


def _get_client():
    """Return cached Zep client, creating it if necessary."""
    global _client
    if _client is None:
        from zep_python.client import Zep

        _client = Zep(
            base_url=_base_url(),
            api_key=os.environ.get("ZEP_API_KEY", "no-auth"),
        )
    return _client


# ---------------------------------------------------------------------------
# Public adapter interface
# ---------------------------------------------------------------------------


def validate() -> dict:
    """
    Static validation — import check + optional /healthz probe.

    Does NOT burn API quota. Probes /healthz with a short timeout so
    smoke_test.py shows "healthy" or "not reachable" without crashing.
    """
    try:
        import zep_python  # noqa: F401
    except ImportError as exc:
        return {
            "ok": False,
            "error": f"zep-python not installed: {exc}",
            "version": None,
            "notes": INSTALL_HINT,
        }

    # Cloud mode: only flag if explicitly requested.
    if os.environ.get("ZEP_USE_CLOUD") == "1" and not os.environ.get("ZEP_API_KEY"):
        return {
            "ok": False,
            "error": "ZEP_USE_CLOUD=1 but ZEP_API_KEY not set",
            "version": None,
            "notes": "Either unset ZEP_USE_CLOUD or export ZEP_API_KEY",
        }

    import zep_python

    zep_version = getattr(zep_python, "__version__", "unknown")
    base = _base_url()
    try:
        import requests

        resp = requests.get(f"{base}/healthz", timeout=3)
        if resp.status_code == 200:
            notes = f"Zep OSS healthy at {base}"
        else:
            notes = (
                f"Zep at {base} returned HTTP {resp.status_code} — "
                "run `docker compose -f compose/docker-compose.yml up -d zep postgres`"
            )
    except Exception as exc:
        notes = (
            f"Zep not reachable at {base} ({exc}) — "
            "run `docker compose -f compose/docker-compose.yml up -d zep postgres`"
        )

    return {
        "ok": True,
        "error": None,
        "version": zep_version,
        "notes": notes,
    }


def setup() -> None:
    """
    Initialize Zep client and ensure the Q4 user exists in Zep.

    Lightweight — does NOT ingest the corpus. Call ``ingest_corpus(chunks)``
    separately before running queries when doing a fresh benchmark run.
    """
    client = _get_client()
    uid = _user_id()
    try:
        client.user.get(uid)
    except Exception:
        try:
            client.user.add(user_id=uid)
        except Exception:
            pass  # OSS may not require explicit user creation


def teardown() -> None:
    """Release client reference. Zep sessions + data persist across runs."""
    global _client
    _client = None


def ingest_corpus(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Ingest a flat list of chunk dicts into Zep sessions.

    Each chunk dict must have at minimum:
        id   (str) — gold chunk ID, e.g. "conv-48::D2:13"
        text (str) — chunk content

    Optional fields:
        conv_id  (str)  — grouping key; derived from id prefix when absent
        metadata (dict) — extra fields stored on the Zep message

    Chunks sharing the same conv_id land in one Zep session named
    "q4-<conv_id>". This is deterministic — repeated calls are idempotent
    (existing sessions are reused, messages are re-added but Zep deduplicates
    at the fact level).

    Returns: {"sessions_created": int, "messages_added": int, "errors": int}
    """
    global _sessions

    client = _get_client()
    uid = _user_id()

    # Group chunks by conversation.
    from collections import defaultdict

    conv_groups: dict[str, list[dict]] = defaultdict(list)
    for chunk in chunks:
        cid = chunk.get("conv_id") or _conv_id_from_gold_id(str(chunk.get("id", "")))
        conv_groups[cid].append(chunk)

    sessions_created = 0
    messages_added = 0
    errors = 0

    for conv_id, conv_chunks in conv_groups.items():
        session_id = f"q4-{conv_id}"
        _ensure_session(client, session_id, uid)
        if session_id not in _sessions:
            _sessions.append(session_id)
        sessions_created += 1

        from zep_python import Message

        batch_size = 50  # Zep OSS handles batches up to ~100 comfortably
        for i in range(0, len(conv_chunks), batch_size):
            batch = conv_chunks[i : i + batch_size]
            msgs: list[Message] = []
            for chunk in batch:
                gold_id = str(chunk.get("id", ""))
                extra_meta = chunk.get("metadata") or {}
                meta: dict[str, Any] = {
                    "gold_id": gold_id,
                    "conv_id": conv_id,
                    **{k: v for k, v in extra_meta.items() if k != "gold_id"},
                }
                msgs.append(
                    Message(
                        role="user",
                        content=str(chunk.get("text", "")),
                        metadata=meta,
                    )
                )
            try:
                client.memory.add(session_id, messages=msgs)
                messages_added += len(msgs)
            except Exception as exc:
                errors += 1
                print(f"[zep ingest] session={session_id} batch={i // batch_size} error: {exc}")

    return {
        "sessions_created": sessions_created,
        "messages_added": messages_added,
        "errors": errors,
    }


def search(query: str, k: int = 10) -> list[dict]:
    """
    Search all ingested Zep sessions for ``query``.

    Uses ``memory.search_sessions`` scoped to the Q4 user. Zep OSS returns
    facts derived from ingested messages (search_scope param is Cloud-only
    and ignored in OSS — OSS always searches facts).

    Gold IDs are recovered from message metadata["gold_id"]. When absent
    (e.g., a synthesized fact with no source message), we fall back to the
    Zep message UUID so the result is still surfaced to the aggregator
    (it will score 0 against the gold set but keeps the list intact).

    If ``ingest_corpus`` has not been called (cold start), falls back to the
    single-session mode using ZEP_SESSION_ID env var (backward compat).
    """
    client = _get_client()

    if not _sessions:
        return _search_single_session(client, query, k)
    return _search_all_sessions(client, query, k)


# ---------------------------------------------------------------------------
# Internal search helpers
# ---------------------------------------------------------------------------


def _search_all_sessions(client, query: str, k: int) -> list[dict]:
    """Search across all Q4 sessions via search_sessions API."""
    uid = _user_id()
    try:
        resp = client.memory.search_sessions(
            text=query,
            user_id=uid,
            limit=k,
            # Omit search_scope: Cloud-only param causes 400 on some OSS builds
        )
    except Exception as exc:
        print(f"[zep search] search_sessions error: {exc}")
        return []

    results_raw = getattr(resp, "results", None) or []
    items: list[dict[str, Any]] = []
    for r in results_raw:
        msg = getattr(r, "message", None)
        score = float(getattr(r, "score", 0.0) or 0.0)
        session_id = getattr(r, "session_id", "") or ""

        if msg is not None:
            gold_id = _extract_gold_id(msg)
            text = getattr(msg, "content", "") or ""
        else:
            # Fact-only result (OSS default path)
            fact = getattr(r, "fact", None)
            gold_id = _extract_gold_id_from_fact(fact)
            text = getattr(fact, "fact", "") if fact else ""

        items.append(
            {
                "id": gold_id or _zep_uuid(msg),
                "score": score,
                "text": text,
                "source": session_id,
            }
        )

    # Deduplicate by id (same fact may surface from multiple sessions).
    seen: set[str] = set()
    deduped: list[dict] = []
    for item in items:
        if item["id"] not in seen:
            seen.add(item["id"])
            deduped.append(item)
    return deduped[:k]


def _search_single_session(client, query: str, k: int) -> list[dict]:
    """
    Fallback single-session search (legacy stub behaviour).

    Used when ingest_corpus has not been called (cold benchmarks or
    manually-loaded sessions via ZEP_SESSION_ID env var).
    """
    session_id = os.environ.get("ZEP_SESSION_ID", "q4-default-session")
    try:
        resp = client.memory.search_sessions(
            text=query,
            session_ids=[session_id],
            limit=k,
        )
    except Exception as exc:
        print(f"[zep search-single] error: {exc}")
        return []

    results_raw = getattr(resp, "results", None) or []
    items: list[dict[str, Any]] = []
    for r in results_raw:
        msg = getattr(r, "message", None)
        score = float(getattr(r, "score", 0.0) or 0.0)
        gold_id = _extract_gold_id(msg) if msg else ""
        text = getattr(msg, "content", "") if msg else ""
        items.append(
            {
                "id": gold_id or _zep_uuid(msg),
                "score": score,
                "text": text,
                "source": session_id,
            }
        )
    return items[:k]


# ---------------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------------


def _conv_id_from_gold_id(gold_id: str) -> str:
    """
    Derive conversation ID from a gold chunk ID.

    Convention (LongMemEval + LoCoMo):
        "conv-48::D2:13"            -> "conv-48"
        "locomo::conv-50::chunk-7"  -> "locomo::conv-50"

    Splits on "::" and takes all but the last segment. If the ID has no
    "::", returns the whole ID as the conversation group.
    """
    if "::" in gold_id:
        parts = gold_id.split("::")
        return "::".join(parts[:-1])
    return gold_id


def _ensure_session(client, session_id: str, user_id: str) -> None:
    """Create Zep session if it does not already exist (idempotent)."""
    try:
        client.memory.get_session(session_id)
        return  # already exists
    except Exception:
        pass  # NotFoundError or connection issue — attempt creation

    try:
        client.memory.add_session(
            session_id=session_id,
            user_id=user_id,
            metadata={"source": "q4-comparison"},
        )
    except Exception as exc:
        # Concurrent creation race — log, don't crash.
        print(f"[zep] add_session({session_id}) warning: {exc}")


def _extract_gold_id(msg) -> str:
    """Pull gold_id from message metadata; return empty string if absent."""
    if msg is None:
        return ""
    meta = getattr(msg, "metadata", None)
    if isinstance(meta, dict):
        return str(meta.get("gold_id", ""))
    return ""


def _extract_gold_id_from_fact(fact) -> str:
    """Pull gold_id from fact metadata (Cloud surface, may be None in OSS)."""
    if fact is None:
        return ""
    meta = getattr(fact, "metadata", None)
    if isinstance(meta, dict):
        return str(meta.get("gold_id", ""))
    return ""


def _zep_uuid(msg) -> str:
    """Extract Zep's internal message UUID as fallback identifier."""
    if msg is None:
        return ""
    return str(getattr(msg, "uuid_", None) or getattr(msg, "uuid", "") or "")
