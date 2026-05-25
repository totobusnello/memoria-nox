"""
LightRAG adapter — Python SDK (lightrag-hku) with Gemini-backed LLM + embeddings.

Repo: https://github.com/HKUDS/LightRAG  (MIT, ~35k stars as of 2026-05-23)
Paper: arXiv:2410.05779 (EMNLP 2025)
Install: pip install lightrag-hku==1.4.10  # pinned 2026-05-24

WHY LIGHTRAG MATTERS FOR Q4
---------------------------
LightRAG's differentiator is **LLM-summarized incremental KG merge**:
when a new document brings in an entity/relation that already exists,
LightRAG asks the LLM to fuse the descriptions into a single coherent
summary instead of deterministically deduping (nox-mem's pattern).
This trades latency + cost during ingest for denser entity context at
query time. Worth measuring head-to-head for the paper.

Provider-agnostic stack (OpenAI / Anthropic / Gemini / Ollama / xAI / etc.).
We pick **Gemini** for Autonomy parity with nox-mem so the comparison is
"same LLM + same embed model, different memory architecture" rather than
"LightRAG-OpenAI vs nox-mem-Gemini" (confound).

CONFIGURATION
-------------
LLM:         gemini-2.5-flash      (LightRAG default for KG extract + summarize)
Embeddings:  gemini-embedding-001  (3072d, same as nox-mem prod)
Storage:     networkx (default, in-process) — graph + KV + vector all on disk.
Working dir: eval/q4-comparison/cache/lightrag/ (gitignored, regenerable).

LIGHTRAG MODES (set via LIGHTRAG_MODE env)
------------------------------------------
LightRAG exposes 4 query modes via QueryParam(mode=...):
  - "naive"  : pure vector RAG, no KG (baseline)
  - "local"  : entity-centric — pulls neighborhood of best-matched entities
  - "global" : community-centric — uses high-level relations across KG
  - "hybrid" : local + global fused (LightRAG's flagship mode)
  - "mix"    : hybrid + vector chunks (full surface area, highest recall)

**Default: "mix"** — matches LightRAG's published-paper headline number.
Spec §5 ("each system uses native defaults") + LightRAG README §"Query
Modes" both reference mix as the canonical surface. Override per run:
  LIGHTRAG_MODE=local   # entity-centric, faster, smaller context
  LIGHTRAG_MODE=hybrid  # KG-only, no raw chunks

COST ESTIMATE — GEMINI 2.5 FLASH (full corpus ingest, no cache)
----------------------------------------------------------------
Corpus: ~5,882 LoCoMo turns + ~4,000 LongMemEval sessions ≈ 9,882 chunks.

LightRAG's ingest pipeline per chunk (default config):
  1. Embedding call (3072d): ~$0.000015 per chunk @ gemini-embedding-001
  2. Entity+relation extraction LLM: ~1.5k tok in / 800 tok out
  3. Incremental merge LLM (only when entity description collides):
     ~500 tok in / 200 tok out × ~1.4 collisions avg per new entity
  4. Community report LLM (one per detected community, batched at end)

Per-chunk LLM cost @ gemini-2.5-flash ($0.075/1M in, $0.30/1M out):
  - Extract:  1500 × 0.075/1M + 800 × 0.30/1M = $0.000113 + $0.00024 = $0.000353
  - Merge avg: 0.000063 (amortized)
  - Embed:    0.000015
  → ~$0.00043 per chunk

Full corpus: 9,882 × $0.00043 ≈ **$4.25 ingest** (+ ~$0.50 community batch)
Total ingest budget: **~$5 one-time** (cached on disk; reused across runs).

Search cost: 1 embedding + 1 LLM rerank ≈ $0.0002/query → 350 queries ≈ $0.07.

LIGHTRAG_INGEST_LIMIT=N        cap chunks (smoke/cost-controlled runs)
LIGHTRAG_FORCE_REINGEST=1      bypass idempotency, re-ingest into fresh working dir
LIGHTRAG_USE_OPENAI_FALLBACK=1 fall back to OpenAI if Gemini integration breaks

ID ROUND-TRIP
-------------
LightRAG's insert() takes raw text; chunks are id'd by content hash internally.
For Q4 gold matching we use the same `[nox_id:<id>] <text>` prefix trick as
agentmemory: insert content prefixed, parse back from query() result.

REFERENCES
----------
  - https://github.com/HKUDS/LightRAG#quickstart
  - https://github.com/HKUDS/LightRAG/blob/main/lightrag/llm/gemini.py
  - arXiv:2410.05779 §4 (incremental KG merge)
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterator

NAME = "lightrag"
VERSION_PIN = "lightrag-hku==1.4.10"  # confirm latest at install time
REQUIRES_ENV = ["GEMINI_API_KEY"]
INSTALL_HINT = (
    "pip install 'lightrag-hku==1.4.10'  "
    "# Gemini-backed; set GEMINI_API_KEY. Working dir: eval/q4-comparison/cache/lightrag/"
)

# ---------------------------------------------------------------------------
# Paths + shared corpus loader
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent.parent  # eval/q4-comparison/
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from lib.corpus_loader import (  # noqa: E402 — after sys.path fixup
    ChunkRecord,
    load_locomo_corpus,
    load_longmemeval_corpus,
)

_WORKING_DIR_DEFAULT = HERE / "cache" / "lightrag"
_NOX_ID_RE = re.compile(r"^\[nox_id:([^\]]+)\]\s*")

# Singleton — initialized lazily by setup() to avoid network in validate().
_rag: Any = None
_event_loop: asyncio.AbstractEventLoop | None = None


def _working_dir() -> Path:
    return Path(os.environ.get("LIGHTRAG_WORKING_DIR", str(_WORKING_DIR_DEFAULT)))


def _query_mode() -> str:
    """Default 'mix' (paper headline). Override via LIGHTRAG_MODE env."""
    mode = (os.environ.get("LIGHTRAG_MODE") or "mix").lower().strip()
    if mode not in ("naive", "local", "global", "hybrid", "mix"):
        raise ValueError(
            f"LIGHTRAG_MODE={mode!r} invalid; must be one of: "
            "naive|local|global|hybrid|mix"
        )
    return mode


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------


def validate() -> dict:
    """Import-only check + env var validation. No network calls."""
    try:
        import lightrag  # noqa: F401
    except ImportError as exc:
        return {
            "ok": False,
            "error": f"lightrag-hku not installed: {exc}",
            "version": None,
            "notes": INSTALL_HINT,
        }

    # Gemini LLM integration may live in lightrag.llm.gemini; check it exists.
    fallback_used = os.environ.get("LIGHTRAG_USE_OPENAI_FALLBACK", "").lower() in (
        "1",
        "true",
        "yes",
    )
    required_env = ["OPENAI_API_KEY"] if fallback_used else REQUIRES_ENV
    missing = [v for v in required_env if not os.environ.get(v)]
    if missing:
        return {
            "ok": False,
            "error": f"missing env: {', '.join(missing)}",
            "version": getattr(__import__("lightrag"), "__version__", "unknown"),
            "notes": (
                "export GEMINI_API_KEY=... (Autonomy parity with nox-mem). "
                "Set LIGHTRAG_USE_OPENAI_FALLBACK=1 to use OpenAI instead "
                "if Gemini integration breaks."
            ),
        }

    return {
        "ok": True,
        "error": None,
        "version": getattr(__import__("lightrag"), "__version__", "unknown"),
        "notes": (
            f"LightRAG ready. Backend: {'OpenAI fallback' if fallback_used else 'Gemini'}. "
            f"Mode default: {_query_mode()}. "
            f"Working dir: {_working_dir()} (idempotent). "
            "Set LIGHTRAG_INGEST_LIMIT=N for smoke runs; LIGHTRAG_FORCE_REINGEST=1 to wipe."
        ),
    }


# ---------------------------------------------------------------------------
# Corpus stream
# ---------------------------------------------------------------------------


def _iter_corpus_chunks() -> Iterator[ChunkRecord]:
    """Yield LoCoMo then LongMemEval chunks via shared canonical loader.

    LIGHTRAG_INGEST_LIMIT caps total chunks for cost-controlled smoke runs.
    """
    limit_raw = os.environ.get("LIGHTRAG_INGEST_LIMIT", "")
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


# ---------------------------------------------------------------------------
# Backend factory — Gemini primary, OpenAI fallback
# ---------------------------------------------------------------------------


def _build_gemini_funcs() -> tuple[Any, Any, int]:
    """
    Return (llm_model_func, embedding_func, embedding_dim) for Gemini.

    Tries lightrag.llm.gemini first (upstream integration). Falls back to a
    minimal handcrafted wrapper using `google-generativeai` if that module is
    not yet shipped in the pinned version (defensive — LightRAG's Gemini
    integration landed mid-2025 and may not be in every minor).
    """
    try:
        from lightrag.llm.gemini import gemini_complete, gemini_embed  # type: ignore

        # gemini_embed is typically wrapped via EmbeddingFunc; if so use directly.
        from lightrag.utils import EmbeddingFunc  # type: ignore

        embedding = EmbeddingFunc(
            embedding_dim=3072,
            max_token_size=2048,
            func=gemini_embed,
        )
        return gemini_complete, embedding, 3072
    except ImportError:
        pass

    # Defensive fallback: roll a thin wrapper using google-generativeai.
    try:
        import google.generativeai as genai  # type: ignore
        from lightrag.utils import EmbeddingFunc  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Neither lightrag.llm.gemini nor google-generativeai available. "
            "Either upgrade lightrag-hku or set LIGHTRAG_USE_OPENAI_FALLBACK=1. "
            f"Underlying error: {exc}"
        ) from exc

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    async def _llm_complete(
        prompt: str,
        system_prompt: str | None = None,
        history_messages: list[dict] | None = None,
        **kwargs: Any,
    ) -> str:
        model_name = os.environ.get("LIGHTRAG_GEMINI_LLM", "gemini-2.5-flash")
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt,
        )
        chat_history = []
        for m in history_messages or []:
            role = "user" if m.get("role") == "user" else "model"
            chat_history.append({"role": role, "parts": [m.get("content", "")]})
        chat = model.start_chat(history=chat_history)
        resp = await asyncio.to_thread(chat.send_message, prompt)
        return resp.text or ""

    async def _embed(texts: list[str]) -> list[list[float]]:
        model_name = os.environ.get(
            "LIGHTRAG_GEMINI_EMBED", "models/gemini-embedding-001"
        )

        def _sync_embed() -> list[list[float]]:
            out: list[list[float]] = []
            for t in texts:
                r = genai.embed_content(model=model_name, content=t)
                out.append(r["embedding"])
            return out

        return await asyncio.to_thread(_sync_embed)

    embedding = EmbeddingFunc(embedding_dim=3072, max_token_size=2048, func=_embed)
    return _llm_complete, embedding, 3072


def _build_openai_funcs() -> tuple[Any, Any, int]:
    """OpenAI fallback (LIGHTRAG_USE_OPENAI_FALLBACK=1)."""
    from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed  # type: ignore
    from lightrag.utils import EmbeddingFunc  # type: ignore

    embedding = EmbeddingFunc(
        embedding_dim=1536,
        max_token_size=8192,
        func=openai_embed,
    )
    return gpt_4o_mini_complete, embedding, 1536


def _get_loop() -> asyncio.AbstractEventLoop:
    """Adapter is sync but LightRAG is async-first; persist a dedicated loop."""
    global _event_loop
    if _event_loop is None or _event_loop.is_closed():
        _event_loop = asyncio.new_event_loop()
    return _event_loop


# ---------------------------------------------------------------------------
# Setup / Teardown
# ---------------------------------------------------------------------------


def setup() -> None:
    """
    Build LightRAG instance (singleton) and ingest corpus if needed.

    Idempotent: skips re-ingest if the working dir already contains a
    LightRAG state (kv_store_full_docs.json existing + non-empty). Force
    re-ingest with LIGHTRAG_FORCE_REINGEST=1 (wipes working dir).
    """
    global _rag
    if _rag is not None:
        return

    from lightrag import LightRAG  # type: ignore

    working_dir = _working_dir()
    force = os.environ.get("LIGHTRAG_FORCE_REINGEST", "").lower() in ("1", "true", "yes")

    if force and working_dir.exists():
        import shutil

        shutil.rmtree(working_dir)
    working_dir.mkdir(parents=True, exist_ok=True)

    fallback_used = os.environ.get("LIGHTRAG_USE_OPENAI_FALLBACK", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if fallback_used:
        llm_func, embed_func, _dim = _build_openai_funcs()
    else:
        llm_func, embed_func, _dim = _build_gemini_funcs()

    _rag = LightRAG(
        working_dir=str(working_dir),
        llm_model_func=llm_func,
        embedding_func=embed_func,
    )

    # Some lightrag versions require explicit init (storages + pipeline status).
    loop = _get_loop()
    for init_attr in ("initialize_storages", "initialize_pipeline_status"):
        fn = getattr(_rag, init_attr, None)
        if fn is None:
            continue
        try:
            res = fn()
            if asyncio.iscoroutine(res):
                loop.run_until_complete(res)
        except Exception as exc:
            print(f"[lightrag] {init_attr} skipped/failed: {exc}")

    _maybe_ingest(_rag)


def _state_marker(working_dir: Path) -> Path:
    return working_dir / "kv_store_full_docs.json"


def _maybe_ingest(rag: Any) -> None:
    """Ingest corpus once. Skip if working dir already populated."""
    working_dir = _working_dir()
    marker = _state_marker(working_dir)
    force = os.environ.get("LIGHTRAG_FORCE_REINGEST", "").lower() in ("1", "true", "yes")

    if not force and marker.exists() and marker.stat().st_size > 16:
        try:
            data = json.loads(marker.read_text())
            doc_count = len(data) if isinstance(data, dict) else 0
        except Exception:
            doc_count = 0
        if doc_count > 0:
            print(
                f"[lightrag] working dir already populated ({doc_count} docs in "
                f"{marker.name}). Skipping re-ingest. "
                "Set LIGHTRAG_FORCE_REINGEST=1 to override."
            )
            return

    chunks = list(_iter_corpus_chunks())
    total = len(chunks)
    if total == 0:
        print(
            "[lightrag] WARNING: corpus_loader yielded 0 chunks. "
            "Run lib/corpus_loader.py prefetch first, or ensure network access "
            "for first-run download."
        )
        return

    print(f"[lightrag] ingesting {total} chunks into {working_dir}...")
    loop = _get_loop()
    ingested = 0
    errors = 0

    # LightRAG batches better with one insert per call when document is small;
    # for the Q4 corpus, batch 32 at a time for throughput.
    BATCH = 32
    batch: list[str] = []
    batch_ids: list[str] = []

    def _flush() -> None:
        nonlocal ingested, errors
        if not batch:
            return
        try:
            # ainsert(texts) → coroutine; fallback to .insert() for older builds.
            insert_fn = getattr(rag, "ainsert", None) or getattr(rag, "insert", None)
            if insert_fn is None:
                raise RuntimeError("LightRAG instance has neither ainsert nor insert")
            res = insert_fn(batch, ids=batch_ids) if "ids" in insert_fn.__code__.co_varnames else insert_fn(batch)
            if asyncio.iscoroutine(res):
                loop.run_until_complete(res)
            ingested += len(batch)
        except Exception as exc:
            errors += len(batch)
            if errors <= 6:
                print(
                    f"[lightrag] ingest batch failed ({len(batch)} chunks): "
                    f"{type(exc).__name__}: {exc}"
                )
        batch.clear()
        batch_ids.clear()

    for i, chunk in enumerate(chunks, start=1):
        # Prefix with nox_id for search-time round-trip.
        content = f"[nox_id:{chunk.id}] {chunk.text}"
        batch.append(content)
        batch_ids.append(chunk.id)
        if len(batch) >= BATCH:
            _flush()
        if i % 200 == 0 or i == total:
            print(f"[lightrag]   processed {i}/{total} ({errors} errors)")

    _flush()
    print(f"[lightrag] ingestion complete: {ingested} ok, {errors} errors")


def teardown() -> None:
    """Close async resources held by LightRAG; reset singleton."""
    global _rag, _event_loop
    if _rag is not None:
        finalize = getattr(_rag, "finalize_storages", None)
        if finalize is not None:
            try:
                loop = _get_loop()
                res = finalize()
                if asyncio.iscoroutine(res):
                    loop.run_until_complete(res)
            except Exception as exc:
                print(f"[lightrag] finalize_storages: {exc}")
        _rag = None
    if _event_loop is not None and not _event_loop.is_closed():
        try:
            _event_loop.close()
        except Exception:
            pass
        _event_loop = None


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def search(query: str, k: int = 10) -> list[dict]:
    """
    Query LightRAG and normalize results to the adapter contract.

    LightRAG's `aquery(query, param=QueryParam(mode=...))` returns either a
    string (default response) or a structured object depending on settings.
    For Q4 we use `only_need_context=True` to get a list of retrieved chunks
    rather than the LLM-synthesized answer, which is what gold_chunk_ids
    matching needs.
    """
    if _rag is None:
        setup()

    from lightrag import QueryParam  # type: ignore

    mode = _query_mode()
    param = QueryParam(mode=mode, only_need_context=True, top_k=k)

    loop = _get_loop()
    query_fn = getattr(_rag, "aquery", None) or getattr(_rag, "query", None)
    if query_fn is None:
        raise RuntimeError("LightRAG instance has neither aquery nor query")

    try:
        raw = query_fn(query, param=param)
        if asyncio.iscoroutine(raw):
            raw = loop.run_until_complete(raw)
    except Exception as exc:
        raise RuntimeError(f"lightrag search failed (mode={mode}): {exc}") from exc

    return _normalize_results(raw, k)


def _normalize_results(raw: Any, k: int) -> list[dict]:
    """
    LightRAG return shapes vary by version + mode:
      - List[dict] with {id, content/text, score?, distance?}
      - dict with .chunks / .context / .entities lists
      - bare str (context as text — only happens if only_need_context flag missed)
    Normalize into [{id, score, text, source}] with nox-mem id parsed from the
    [nox_id:...] prefix when present.
    """
    items: list[Any]
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        for key in ("chunks", "context", "results", "entities"):
            v = raw.get(key)
            if isinstance(v, list):
                items = v
                break
        else:
            items = []
    elif isinstance(raw, str):
        # Best-effort: split by chunk markers if any; otherwise treat as one
        # big context blob (which won't match individual gold ids but at least
        # surfaces a result the runner can count as non-empty).
        items = [{"content": raw, "score": 0.0}]
    else:
        items = []

    normalized: list[dict] = []
    for item in items[:k]:
        if not isinstance(item, dict):
            continue
        text = (
            item.get("content")
            or item.get("text")
            or item.get("description")
            or item.get("entity_description")
            or ""
        )
        if not isinstance(text, str):
            text = str(text)

        # Parse nox-mem id from prefix; fall back to LightRAG's internal id.
        m = _NOX_ID_RE.match(text)
        if m:
            nox_id = m.group(1)
            text = text[m.end() :]
        else:
            nox_id = str(item.get("id") or item.get("chunk_id") or item.get("entity_name") or "")

        # LightRAG returns 'distance' (lower=better) or 'score' (higher=better)
        # depending on storage backend. Convert distance → score.
        if "score" in item and item["score"] is not None:
            score = float(item["score"])
        elif "distance" in item and item["distance"] is not None:
            score = 1.0 - float(item["distance"])
        else:
            score = 0.0

        normalized.append(
            {
                "id": nox_id,
                "score": score,
                "text": text,
                "source": item.get("source") or item.get("file_path") or None,
            }
        )

    return normalized


# ---------------------------------------------------------------------------
# Smoke entrypoint (manual: python -m adapters.lightrag)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(json.dumps(validate(), indent=2))
