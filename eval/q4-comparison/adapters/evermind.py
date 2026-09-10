"""
EverOS adapter — `everos.service.knowledge` surface (document provenance).

Repo: https://github.com/EverMind-AI/EverOS   (org EverMind-AI, repo EverOS)
Install: pip install everos==1.3.1

⚠️ ERRATA 2026-09-10. This file previously targeted a CLI (`evermind retrieve`)
and a module path (`EVERMIND_PYTHON_MODULE`) that DO NOT EXIST, and cited the
repo as `EverOS-AI/EverMind-AI` — org and repo swapped. `REQUIREMENTS.md` §6
declared the repo nonexistent for 3.5 months because all five probes queried the
swapped name; `EverMind-AI/EverOS` was never tried. The package is on PyPI as
`everos`; the CLI commands are `init · demo · server · cascade · config` — no
`add`, no `retrieve`. Everything below is measured against v1.3.1, not assumed.

WHICH SURFACE, AND WHY IT MATTERS FOR FAIRNESS
──────────────────────────────────────────────
EverOS exposes two retrieval surfaces, and they are NOT interchangeable for a
chunk-id nDCG comparison:

  1. `service.memorize` + `service.search` — the *memory* surface. Ingest is a
     conversation (`session_id` + `messages`); what comes back are DERIVED
     episodes. There is no mapping from a hit back to the corpus chunk that
     produced it, so `gold_chunk_ids` matching is undefined. Not usable here.

  2. `service.knowledge` — the *knowledge* surface. `create_document()` accepts
     `doc_id=`, and `search_knowledge()` returns `SearchHit.document.doc_id`.
     The corpus chunk id therefore ROUND-TRIPS, and nDCG@k over
     `gold_chunk_ids` is well defined.

This adapter uses (2). That choice is a limitation to declare, not a silent
default: we are benchmarking EverOS's knowledge retrieval, not its episodic
memory. Same class of disclosure as the mem0 corpus-cap framing already
documented in the paper.

GRANULARITY ASYMMETRY — the reason for over-fetch
─────────────────────────────────────────────────
`search_knowledge` ranks TOPICS, not documents. One document is extracted into
`CreateDocumentResult.topic_count` topics, so `top_k=k` topics can collapse to
FEWER than k distinct doc_ids — which would penalise EverOS for a granularity
difference rather than for retrieval quality. The adapter therefore requests
`k * EVEROS_OVERFETCH` topics (default 5), dedupes by `doc_id` keeping the best
rank, and truncates to k. `search()` reports `topics_seen` per call so the
write-up can state the realised collapse factor instead of guessing it.

This mirrors mem0's `threshold=0.0` decision already in this harness: remove a
system-specific cutoff that would drop gold items BEFORE scoring.

COST — THIS INGEST IS PAID, AND IT IS GATED
───────────────────────────────────────────
`create_document()` runs an LLM extraction per document (`AlgoKnowledgeExtractor
(llm=get_llm_client())`), and `search_knowledge()` needs an embedding provider.
Measured corpus, 2026-09-10:

    cache/locomo.jsonl        5.882 chunks     767.654 chars   ~191.9k tokens
    cache/longmemeval.jsonl     948 chunks  13.372.109 chars  ~3.343k tokens
    ────────────────────────────────────────────────────────────────────────
    total                     6.830 chunks  14.139.763 chars  ~3.535k tokens

⚠️ Do NOT quote "~2.482 chunks" for this run: 2.482 is the QUERY count
(`cache/queries-rc4-all.jsonl`), not the corpus. And note the cost is dominated
by LongMemEval — 14% of the documents carry 95% of the tokens.

`ingest_corpus()` REFUSES to run without `EVEROS_ALLOW_PAID_INGEST=1` and
returns the estimate instead. No paid call happens by accident.

CONFIGURATION (measured env bindings, prefix EVEROS_, delimiter __)
───────────────────────────────────────────────────────────────────
    EVEROS_ROOT                  memory root (this adapter pins its own)
    EVEROS_LLM__MODEL            extraction model
    EVEROS_LLM__API_KEY          required, else LLMNotConfiguredError
    EVEROS_LLM__BASE_URL         required — OpenAI-compatible endpoint
    EVEROS_EMBEDDING__MODEL      embedding model
    EVEROS_EMBEDDING__API_KEY
    EVEROS_EMBEDDING__BASE_URL
    EVEROS_EMBEDDING__DIMENSIONS

Both are OpenAI-compatible endpoints, so Gemini is reachable via its
OpenAI-compat base_url — which keeps this comparable to the rc4 all-Gemini
variant instead of introducing a second provider.

ISOLATION
─────────
`setup()` pins `EVEROS_ROOT` to `EVEROS_EVAL_ROOT` (default
`eval/q4-comparison/.everos-eval`) BEFORE any everos import that reads
settings, so the harness never writes into the user's `~/.everos`. Same rule as
the nox_mem adapter's explicit `NOX_DB_PATH`.

ASYNC
─────
Both service calls are `async`. The adapter contract is synchronous, so
`setup()` creates ONE event loop and every call reuses it. A fresh
`asyncio.run()` per query would put loop construction inside the timed region
and inflate the latency numbers.
"""

from __future__ import annotations

import asyncio
import importlib
import os
import sys
from pathlib import Path
from typing import Any, Iterable

NAME = "evermind"  # registry key kept: ALL_ADAPTERS and output/<system>.json use it
VERSION_PIN = "everos==1.3.1"  # PyPI, resolved 2026-09-10
REQUIRES_ENV: list[str] = [
    "EVEROS_LLM__API_KEY",
    "EVEROS_LLM__BASE_URL",
    "EVEROS_EMBEDDING__API_KEY",
    "EVEROS_EMBEDDING__BASE_URL",
]
INSTALL_HINT = "pip install everos==1.3.1  # repo: EverMind-AI/EverOS"

_HERE = Path(__file__).resolve().parent.parent
_DEFAULT_EVAL_ROOT = _HERE / ".everos-eval"
_APP_ID = "q4eval"
_PROJECT_ID = "default"

# Set by setup(); None means setup() has not run.
_loop: asyncio.AbstractEventLoop | None = None
_knowledge_dir: Path | None = None
_extractor: Any = None
_topics_ingested = 0


def _eval_root() -> Path:
    return Path(os.environ.get("EVEROS_EVAL_ROOT") or _DEFAULT_EVAL_ROOT)


def _overfetch() -> int:
    try:
        return max(1, int(os.environ.get("EVEROS_OVERFETCH", "5")))
    except ValueError:
        return 5


def validate() -> dict:
    """Imports + env checks ONLY. Makes no network call (no quota burn)."""
    notes: list[str] = []
    try:
        import everos  # noqa: F401
        from everos.service import knowledge as _k  # noqa: F401
    except Exception as exc:
        return {
            "ok": False,
            "error": f"everos not importable: {type(exc).__name__}: {exc}",
            "version": None,
            "notes": INSTALL_HINT,
        }

    try:
        from importlib.metadata import version as _v

        resolved = _v("everos")
    except Exception:
        resolved = None

    # Every symbol setup()/ingest_corpus()/search() import LATE is resolved here,
    # and this leg runs BEFORE the env leg on purpose.
    #
    # ⚠️ 2026-09-10: two of these paths were originally GUESSED from proximity in
    # everos's own API route (`MemoryRoot` from everos.config.settings,
    # `ParsedContent` from everos.component.parser). Both were wrong —
    # MemoryRoot lives in everos.core.persistence and ParsedContent is in
    # `everalgo`, a different distribution. validate() returned ok:false for the
    # RIGHT reason (missing env) and the wrong import paths stayed invisible,
    # because they are only reached inside setup(). A guard whose failing leg
    # decides first hides every leg behind it: the import leg must therefore run
    # first, and it must name every module the adapter actually needs.
    for _mod, _sym in (
        ("everos.core.persistence", "MemoryRoot"),
        ("everos.service.knowledge", "create_document"),
        ("everos.service.knowledge", "search_knowledge"),
        ("everos.component.llm.client", "get_llm_client"),
        ("everalgo.types", "ParsedContent"),
        ("everalgo.knowledge", "KnowledgeExtractor"),
    ):
        try:
            getattr(importlib.import_module(_mod), _sym)
        except Exception as exc:
            return {
                "ok": False,
                "error": f"{_mod}.{_sym} unresolvable: {type(exc).__name__}: {exc}",
                "version": resolved,
                "notes": "adapter targets everos 1.3.1 internals; a version bump can move these",
            }

    missing = [v for v in REQUIRES_ENV if not os.environ.get(v)]
    if missing:
        return {
            "ok": False,
            "error": f"missing env: {', '.join(missing)}",
            "version": resolved,
            "notes": (
                "everos search instantiates an LLM client and an embedding client; "
                "both are OpenAI-compatible, so Gemini works via its openai-compat base_url"
            ),
        }

    notes.append("surface=service.knowledge (doc_id round-trips; memory surface has no chunk provenance)")
    notes.append(f"overfetch={_overfetch()}x (hits are topics, not documents)")
    if not os.environ.get("EVEROS_ALLOW_PAID_INGEST"):
        notes.append("ingest GATED: set EVEROS_ALLOW_PAID_INGEST=1 (6.830 docs x 1 LLM extraction)")
    return {"ok": True, "error": None, "version": resolved, "notes": "; ".join(notes)}


def setup() -> None:
    """Idempotent. Pins EVEROS_ROOT, builds the loop, extractor and knowledge_dir."""
    global _loop, _knowledge_dir, _extractor
    if _loop is not None and not _loop.is_closed():
        return

    root = _eval_root()
    root.mkdir(parents=True, exist_ok=True)
    # Pin BEFORE importing anything that resolves settings.
    os.environ["EVEROS_ROOT"] = str(root)

    from everos.core.persistence import MemoryRoot

    _knowledge_dir = MemoryRoot.resolve().knowledge_dir(_APP_ID, _PROJECT_ID)
    _knowledge_dir.mkdir(parents=True, exist_ok=True)

    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)

    # Extractor is only needed for ingest; building it here surfaces a bad LLM
    # config at setup time instead of after the first paid call.
    if os.environ.get("EVEROS_ALLOW_PAID_INGEST"):
        from everalgo.knowledge import KnowledgeExtractor as _Extractor
        from everos.component.llm.client import get_llm_client

        _extractor = _Extractor(llm=get_llm_client())


def ingest_corpus(chunks: Iterable[dict]) -> dict:
    """
    Create one EverOS knowledge document per corpus chunk, with doc_id = chunk id.

    PAID: one LLM extraction call per document. Refuses unless
    EVEROS_ALLOW_PAID_INGEST=1, returning the estimate so the runner records
    the gap honestly instead of reporting an empty index as a result.
    """
    global _topics_ingested
    items = [c for c in chunks if c.get("id") and c.get("text")]
    chars = sum(len(c["text"]) for c in items)
    estimate = {
        "documents": len(items),
        "chars": chars,
        "approx_input_tokens": chars // 4,
        "llm_calls": len(items),
    }

    if not os.environ.get("EVEROS_ALLOW_PAID_INGEST"):
        return {
            "ingested": 0,
            "skipped": len(items),
            "reason": "paid-ingest-gated",
            "gate": "EVEROS_ALLOW_PAID_INGEST=1",
            "estimate": estimate,
        }

    setup()
    assert _loop is not None and _knowledge_dir is not None
    if _extractor is None:  # gate flipped after setup() already ran
        from everalgo.knowledge import KnowledgeExtractor as _Extractor
        from everos.component.llm.client import get_llm_client

        globals()["_extractor"] = _Extractor(llm=get_llm_client())

    from everalgo.types import ParsedContent
    from everos.service.knowledge import create_document

    ok = 0
    failed: list[str] = []
    topics = 0
    for c in items:
        try:
            result = _loop.run_until_complete(
                create_document(
                    extractor=_extractor,
                    parsed=ParsedContent(text=c["text"]),
                    title=str(c["id"]),
                    knowledge_dir=_knowledge_dir,
                    source_name=str(c.get("dataset") or "q4"),
                    source_type="text",
                    doc_id=str(c["id"]),
                )
            )
            ok += 1
            topics += int(getattr(result, "topic_count", 0) or 0)
        except Exception as exc:  # keep going; report the tail
            if len(failed) < 10:
                failed.append(f"{c['id']}: {type(exc).__name__}: {exc}")

    _topics_ingested = topics
    return {
        "ingested": ok,
        "failed": len(items) - ok,
        "topics": topics,
        "topics_per_doc": round(topics / ok, 2) if ok else None,
        "first_errors": failed,
        "estimate": estimate,
    }


def search(query: str, k: int = 10) -> list[dict]:
    """
    Search the knowledge surface and map hits back to corpus chunk ids.

    Hits are TOPICS; several can share one doc_id. We over-fetch, dedupe by
    doc_id keeping the best-ranked topic, and truncate to k — otherwise a
    granularity difference, not retrieval quality, would set the ceiling.
    """
    setup()
    assert _loop is not None

    from everos.service.knowledge import search_knowledge

    want = k * _overfetch()
    try:
        res = _loop.run_until_complete(
            search_knowledge(
                query=query,
                method=os.environ.get("EVEROS_SEARCH_METHOD", "hybrid"),
                top_k=want,
                include_content=True,
                app_id=_APP_ID,
                project_id=_PROJECT_ID,
            )
        )
    except Exception as exc:
        raise RuntimeError(f"everos search_knowledge failed: {exc}") from exc

    hits = list(getattr(res, "hits", None) or [])
    out: list[dict] = []
    seen: set[str] = set()
    for h in hits:
        doc = getattr(h, "document", None)
        doc_id = getattr(doc, "doc_id", None) if doc is not None else None
        if not doc_id or doc_id in seen:
            continue
        seen.add(str(doc_id))
        out.append(
            {
                "id": str(doc_id),
                "score": float(getattr(h, "score", 0.0) or 0.0),
                "text": getattr(h, "content", None) or getattr(h, "summary", "") or "",
                "source": "everos:knowledge",
                # Provenance of the collapse, per call — so the write-up states
                # the realised factor instead of assuming EVEROS_OVERFETCH held.
                "topics_seen": len(hits),
                "topic_name": getattr(h, "topic_name", None),
                "retrieval_method": getattr(h, "retrieval_method", None),
            }
        )
        if len(out) >= k:
            break
    return out


def teardown() -> None:
    """Idempotent. Closes the loop; leaves the knowledge dir for reuse."""
    global _loop
    if _loop is not None and not _loop.is_closed():
        try:
            _loop.close()
        except Exception:
            pass
    _loop = None


if __name__ == "__main__":
    import json

    print(json.dumps(validate(), indent=2, ensure_ascii=False))
    sys.exit(0)
