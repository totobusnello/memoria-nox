"""
Zep adapter — local self-hosted Zep Open Source via Docker Compose.

Repo: https://github.com/getzep/zep  (Apache-2.0)
Install: docker compose -f compose/docker-compose.yml up -d zep postgres
Python client: pip install zep-python==1.5.0  (matches Zep OSS 0.27.2 API)

VERSION PIN NOTE (2026-05-24)
-----------------------------
The original spec listed `zep-python==2.0.2`. That SDK targets Zep Cloud
(new `/api/v2/*` surface + `Users`/`Threads`/`Graph` resources). Zep OSS 0.27.2
exposes the older `/api/v1/*` Sessions+Memory surface that the **1.x** SDK
talks to. Mismatch → 404 on every request. The 1.5.0 SDK is the last release
before the Cloud refactor and is the right match for OSS 0.27.2.

API surface summary (1.5.0 ↔ OSS 0.27.2)
----------------------------------------
- `ZepClient(base_url, api_key)`                — top-level client
- `client.memory.add_session(Session(...))`     — POST /api/v1/sessions
- `client.memory.add_memory(sid, Memory(messages=[...]))` — POST /api/v1/sessions/<sid>/memory
- `client.memory.search_memory(sid, MemorySearchPayload(text=q), limit=k)`
  — POST /api/v1/sessions/<sid>/search  (SCOPED PER SESSION)
- `r.message` is a dict (not pydantic), `r.dist` is cosine similarity
  (higher = more similar)

INGESTION MODEL
---------------
Zep stores "messages" inside "sessions". For LongMemEval / LoCoMo we map
each conversation (chunks sharing the same conversation prefix in their ID)
to one Zep session, ingest chunks as messages, and store the original
gold chunk ID in message metadata so search results can be mapped back.

Zep assigns its own UUIDs to messages. The round-trip through metadata is
the ONLY way to recover our gold IDs — the adapter carries that mapping
internally via message metadata["gold_id"].

SEARCH MODEL
------------
Zep OSS 1.5 search is **per-session**. To answer a query across the whole
benchmark corpus we fan the query out to every ingested session, collect
results, sort by similarity (dist), and dedupe by gold_id. This is O(S*k)
per query where S = number of conversations (~720 for LoCoMo+LongMemEval).
At k=10 that is ~7,200 result rows merged per query — Zep handles each
session search in ~50-150ms so total per-query latency lands ~5-15s in
the worst case. We measure this honestly.

EMBEDDINGS
----------
Zep config `compose/zep-config.yaml` has Extractors.Messages.Embeddings
enabled with Service="openai", Dimensions=1536, Model implicit
text-embedding-3-small. Requires real OPENAI_API_KEY in the environment;
docker-compose.yml forwards it as ZEP_OPENAI_API_KEY. Cost: ~$0.02 for
the full LoCoMo+LongMemEval corpus (~1M tokens × $0.02/1M).
"""

from __future__ import annotations

import os
from typing import Any

NAME = "zep"
VERSION_PIN = "zep-python==1.5.0 + ghcr.io/getzep/zep:0.27.2 (OSS, Docker)"
# Cross-system mode requires OpenAI embeddings; OPENAI_API_KEY mandatory.
REQUIRES_ENV: list[str] = ["OPENAI_API_KEY"]
INSTALL_HINT = (
    "pip install 'zep-python==1.5.0' && "
    "OPENAI_API_KEY=sk-... docker compose -f compose/docker-compose.yml up -d zep postgres"
)

_DEFAULT_BASE = "http://127.0.0.1:8000"

_client = None
# All session_ids created during ingest_corpus (for scoping search).
_sessions: list[str] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_url() -> str:
    return (os.environ.get("ZEP_API_URL") or _DEFAULT_BASE).rstrip("/")


def _get_client():
    """Return cached Zep client, creating it if necessary."""
    global _client
    if _client is None:
        from zep_python import ZepClient

        _client = ZepClient(
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

    import zep_python

    zep_version = getattr(zep_python, "__version__", "1.5.0")
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

    if not os.environ.get("OPENAI_API_KEY"):
        return {
            "ok": False,
            "error": "OPENAI_API_KEY not set — required for Zep embeddings extractor",
            "version": zep_version,
            "notes": notes + " | export OPENAI_API_KEY=sk-... before docker compose up",
        }

    return {
        "ok": True,
        "error": None,
        "version": zep_version,
        "notes": notes,
    }


def setup() -> None:
    """
    Initialize Zep client. Idempotent; safe to call multiple times.

    Lightweight — does NOT ingest the corpus. Call ``ingest_corpus(chunks)``
    separately before running queries when doing a fresh benchmark run.

    Optional: NOX_ZEP_RESCAN_SESSIONS=1 fetches all "q4-*" session_ids from
    the running Zep server into the in-process _sessions list. Used when
    re-running benchmarks against an already-populated Zep DB
    (`runner.py --skip-ingest`) so the fan-out search still works.
    """
    _get_client()
    if os.environ.get("NOX_ZEP_RESCAN_SESSIONS") == "1":
        _rescan_sessions_from_zep()


def _rescan_sessions_from_zep() -> None:
    """Populate _sessions by listing q4-* sessions already in the Zep server."""
    global _sessions
    try:
        import requests

        base = _base_url()
        # Zep OSS 0.27 returns up to ~100 by default; paginate via ?limit + cursor
        # but in practice <1000 sessions total. Use ?limit=10000 single-shot.
        resp = requests.get(f"{base}/api/v1/sessions?limit=10000", timeout=10)
        resp.raise_for_status()
        data = resp.json() or []
        q4_sessions = [
            s.get("session_id")
            for s in data
            if isinstance(s, dict) and str(s.get("session_id", "")).startswith("q4-")
        ]
        _sessions = [s for s in q4_sessions if s]
        print(f"[zep rescan] loaded {len(_sessions)} q4-* sessions from server")
    except Exception as exc:
        print(f"[zep rescan] failed: {exc} — _sessions left empty")


def teardown() -> None:
    """Release client reference. Zep sessions + data persist across runs."""
    global _client
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
        _client = None


def ingest_corpus(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Ingest a flat list of chunk dicts into Zep sessions.

    Each chunk dict must have at minimum:
        id   (str) — gold chunk ID, e.g. "conv-48::D2:13"
        text (str) — chunk content

    Optional fields:
        conv_id  (str)  — grouping key; derived from id prefix when absent
        conversation_id (str) — corpus_loader uses this field
        metadata (dict) — extra fields stored on the Zep message

    Chunks sharing the same conv_id land in one Zep session named
    "q4-<conv_id>". This is deterministic — repeated calls are idempotent
    (existing sessions are reused, messages are re-added; Zep deduplicates
    nothing message-level so re-running CAN multiply data — wipe DB between
    fresh runs via `docker compose down -v`).

    Returns: {"sessions_created": int, "messages_added": int, "errors": int}
    """
    global _sessions

    client = _get_client()

    # Group chunks by conversation.
    from collections import defaultdict

    conv_groups: dict[str, list[dict]] = defaultdict(list)
    for chunk in chunks:
        cid = (
            chunk.get("conv_id")
            or chunk.get("conversation_id")
            or _conv_id_from_gold_id(str(chunk.get("id", "")))
        )
        conv_groups[cid].append(chunk)

    sessions_created = 0
    messages_added = 0
    errors = 0

    from zep_python import Memory, Message, Session

    for conv_id, conv_chunks in conv_groups.items():
        session_id = _safe_session_id(conv_id)
        _ensure_session(client, session_id, Session)
        if session_id not in _sessions:
            _sessions.append(session_id)
        sessions_created += 1

        # Zep OSS 0.27 accepts batches but bounded by request size; keep modest.
        batch_size = 30
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
                client.memory.add_memory(session_id, Memory(messages=msgs))
                messages_added += len(msgs)
            except Exception as exc:
                errors += 1
                print(
                    f"[zep ingest] session={session_id} batch={i // batch_size} error: {exc}"
                )

    # Zep computes embeddings asynchronously via a watermill consumer. Block
    # here until every ingested message has its embedding row, so search()
    # does not race a half-embedded corpus and return artificially low recall.
    wait_secs = int(os.environ.get("ZEP_EMBED_WAIT_SECS", "600"))
    _wait_for_embeddings(messages_added, wait_secs)

    return {
        "sessions_created": sessions_created,
        "messages_added": messages_added,
        "errors": errors,
    }


def _wait_for_embeddings(expected: int, max_secs: int) -> None:
    """Poll postgres until message_embedding.count >= expected (or timeout)."""
    if expected <= 0:
        return
    import subprocess
    import time

    deadline = time.time() + max_secs
    last_count = -1
    stagnant_polls = 0
    while time.time() < deadline:
        try:
            out = subprocess.run(
                [
                    "docker",
                    "exec",
                    "q4-postgres",
                    "psql",
                    "-U",
                    "zep",
                    "-d",
                    "zep",
                    "-t",
                    "-A",
                    "-c",
                    "SELECT count(*) FROM message_embedding;",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            count = int(out.stdout.strip() or "0")
        except Exception as exc:
            print(f"[zep wait] poll error: {exc}")
            time.sleep(5)
            continue
        if count >= expected:
            print(f"[zep wait] embeddings ready: {count}/{expected}")
            return
        if count == last_count:
            stagnant_polls += 1
        else:
            stagnant_polls = 0
        last_count = count
        # Print every 30s-ish
        print(f"[zep wait] embeddings: {count}/{expected}")
        if stagnant_polls >= 6:  # 6 polls × 10s = 60s no progress
            print("[zep wait] no progress for 60s — proceeding with partial embeddings")
            return
        time.sleep(10)
    print(f"[zep wait] timeout after {max_secs}s; proceeding with partial embeddings")


def search(query: str, k: int = 10) -> list[dict]:
    """
    Search all ingested Zep sessions for ``query``.

    Zep OSS 1.5 search is scoped per-session. We fan the query out to all
    sessions populated by ``ingest_corpus`` and merge by similarity score
    (``r.dist`` — higher = more similar in this SDK), then dedupe on gold_id.

    Performance note: with ~500-720 sessions and ~400ms/search serial, a
    sequential fan-out takes ~3-5 min per query (unacceptable for n=100
    benchmark). We parallelize via ThreadPoolExecutor — `requests` releases
    the GIL during HTTP I/O so threading scales linearly until either Zep
    server or the network saturates. NOX_ZEP_SEARCH_WORKERS overrides the
    default (16 — empirically the sweet spot for the OSS server's bounded
    handler pool).

    Falls back to `ZEP_SESSION_ID` env var when no ingest happened in-process
    (cold benchmarks driven manually).
    """
    client = _get_client()

    if not _sessions:
        fallback = os.environ.get("ZEP_SESSION_ID")
        if not fallback:
            return []
        return _search_one(client, fallback, query, k)

    from concurrent.futures import ThreadPoolExecutor, as_completed

    from zep_python import MemorySearchPayload

    payload = MemorySearchPayload(text=query)
    workers = int(os.environ.get("NOX_ZEP_SEARCH_WORKERS", "16"))

    def _one(sid: str):
        try:
            return sid, client.memory.search_memory(sid, payload, limit=k)
        except Exception as exc:  # noqa: BLE001
            return sid, exc

    all_results: list[tuple[float, dict]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_one, sid) for sid in _sessions]
        for fut in as_completed(futures):
            sid, results = fut.result()
            if isinstance(results, Exception):
                # Log + skip; do not let one bad session kill the whole query
                print(f"[zep search] session={sid} error: {results}")
                continue
            for r in results:
                msg = getattr(r, "message", None)
                if msg is None:
                    continue
                # message comes back as dict in 1.5
                if isinstance(msg, dict):
                    meta = msg.get("metadata") or {}
                    content = msg.get("content", "")
                    msg_uuid = msg.get("uuid", "")
                else:
                    meta = getattr(msg, "metadata", None) or {}
                    content = getattr(msg, "content", "") or ""
                    msg_uuid = getattr(msg, "uuid", "") or ""
                gold_id = str((meta or {}).get("gold_id") or "") or msg_uuid
                score = float(getattr(r, "dist", 0.0) or 0.0)
                all_results.append(
                    (
                        score,
                        {
                            "id": gold_id,
                            "score": score,
                            "text": content,
                            "source": sid,
                        },
                    )
                )

    # Sort by similarity (higher = closer) and dedupe by id.
    all_results.sort(key=lambda x: x[0], reverse=True)
    seen: set[str] = set()
    deduped: list[dict] = []
    for _, item in all_results:
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        deduped.append(item)
        if len(deduped) >= k:
            break
    return deduped


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _search_one(client, session_id: str, query: str, k: int) -> list[dict]:
    """Single-session fallback search."""
    from zep_python import MemorySearchPayload

    try:
        results = client.memory.search_memory(
            session_id, MemorySearchPayload(text=query), limit=k
        )
    except Exception as exc:
        print(f"[zep search-single] error: {exc}")
        return []
    items: list[dict] = []
    for r in results:
        msg = getattr(r, "message", None) or {}
        if isinstance(msg, dict):
            meta = msg.get("metadata") or {}
            content = msg.get("content", "")
            uuid = msg.get("uuid", "")
        else:
            meta = getattr(msg, "metadata", None) or {}
            content = getattr(msg, "content", "")
            uuid = getattr(msg, "uuid", "")
        items.append(
            {
                "id": str((meta or {}).get("gold_id") or "") or uuid,
                "score": float(getattr(r, "dist", 0.0) or 0.0),
                "text": content,
                "source": session_id,
            }
        )
    return items[:k]


def _conv_id_from_gold_id(gold_id: str) -> str:
    """
    Derive conversation ID from a gold chunk ID.

    LoCoMo:       "conv-48::D2:13"  -> "conv-48"
    LongMemEval:  bare session_id  -> session_id   (each chunk = own conv)
    """
    if "::" in gold_id:
        parts = gold_id.split("::")
        return "::".join(parts[:-1])
    return gold_id


def _safe_session_id(raw: str) -> str:
    """
    Zep 0.27 only accepts session_id matching /^[a-zA-Z0-9_-]+$/ish (alphanum + _-).
    Sanitize while keeping reversibility for debugging.
    """
    safe = "".join(c if (c.isalnum() or c in "_-") else "_" for c in raw)
    return f"q4-{safe[:120]}"  # keep within typical column limits


def _ensure_session(client, session_id: str, Session) -> None:
    """Create Zep session if it does not already exist (idempotent)."""
    try:
        client.memory.get_session(session_id)
        return  # exists
    except Exception:
        pass

    try:
        client.memory.add_session(
            Session(session_id=session_id, metadata={"source": "q4-comparison"})
        )
    except Exception as exc:
        # Concurrent / already-exists — log + continue.
        print(f"[zep] add_session({session_id}) warning: {exc}")
