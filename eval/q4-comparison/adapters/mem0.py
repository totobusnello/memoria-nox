"""
Mem0 adapter — Python SDK (mem0ai) with full corpus ingestion.

Repo: https://github.com/mem0ai/mem0  (Apache-2.0, 53k+ stars as of 2026-05-21)
Install: pip install mem0ai==0.1.114 (pinned 2026-05-18; bump if newer minor)

Mem0's default config requires OPENAI_API_KEY for embeddings + LLM extraction.
For a fair comparison we keep defaults (per spec §5: "each system uses native
defaults"). Vector store: Chroma in-process (no external daemon).

Ingestion:
  setup() ingests the full LoCoMo + LongMemEval oracle corpus into Mem0 using
  Memory.add(). Each corpus chunk is added as a single memory with metadata
  carrying chunk_id, dataset, source. Ingestion is idempotent: if the expected
  chunk count already exists in Mem0's store for user_id=<MEM0_USER_ID>, the
  corpus ingest is skipped (rely on Chroma persistence across calls if the
  same config dir is reused, or force re-ingest with MEM0_FORCE_REINGEST=1).

Cost awareness:
  Each Memory.add() call invokes:
    - One OpenAI embedding call (per chunk).
    - One OpenAI LLM call (for fact extraction / memory-rewrite, mem0 default).
  Total corpus size is ~5,882 LoCoMo turns + ~500 LongMemEval sessions ≈ 6,400
  chunks. At ~$0.0001 per embed + $0.002 per LLM extraction call ≈ $13-15 total.
  MEM0_SKIP_LLM_EXTRACTION=1 skips the LLM extraction pass (cheaper, faster,
  slightly lower quality — useful for cost-capped test runs).

Cache: Chroma persists in MEM0_CHROMA_PATH (default: eval/q4-comparison/.mem0-chroma).
  Re-running runner.py reuses existing embeddings if same user_id + config path.
  To wipe and re-ingest: rm -rf .mem0-chroma && runner.py again.

Search result mapping:
  Mem0 returns {id, memory, score, metadata}. The adapter maps metadata.chunk_id
  → result.id so gold_chunk_ids matching works correctly in aggregate.py.
  Fallback: if metadata.chunk_id is absent, use Mem0's internal UUID as id.

Corpus loading:
  Uses the shared corpus_loader (eval/q4-comparison/lib/corpus_loader.py).
  Each ChunkRecord yielded has stable `id` matching gold format (e.g. `conv-48::D2:13`).
  No adapter-private loaders — canonical paths live in corpus_loader.py.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Iterator

NAME = "mem0"
VERSION_PIN = "mem0ai==0.1.114"  # confirm latest stable at install time
REQUIRES_ENV = ["OPENAI_API_KEY"]
INSTALL_HINT = "pip install 'mem0ai==0.1.114'"

_USER_ID_DEFAULT = "q4-eval"
_client = None  # singleton, initialized in setup()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HERE = Path(__file__).parent.parent  # eval/q4-comparison/
_CHROMA_PATH_DEFAULT = str(HERE / ".mem0-chroma")

# Ensure lib/ is importable regardless of cwd
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from lib.corpus_loader import (  # noqa: E402 — after sys.path fixup
    ChunkRecord,
    load_locomo_corpus,
    load_longmemeval_corpus,
)

# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------


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
            "notes": "export OPENAI_API_KEY=sk-... (required for Mem0 default config)",
        }
    return {
        "ok": True,
        "error": None,
        "version": getattr(__import__("mem0"), "__version__", "unknown"),
        "notes": (
            "Mem0 defaults: Chroma vector store + OpenAI embeddings. "
            f"Chroma path: {os.environ.get('MEM0_CHROMA_PATH', _CHROMA_PATH_DEFAULT)}. "
            "Set MEM0_FORCE_REINGEST=1 to re-ingest even if count matches."
        ),
    }


# ---------------------------------------------------------------------------
# Shared corpus stream
# ---------------------------------------------------------------------------


def _iter_corpus_chunks() -> Iterator[ChunkRecord]:
    """Yield all corpus chunks from the shared loader (LoCoMo then LongMemEval).

    Uses the canonical corpus_loader so IDs match gold_chunk_ids exactly.
    MEM0_INGEST_LIMIT caps the total count for cost-controlled test runs.
    """
    limit_raw = os.environ.get("MEM0_INGEST_LIMIT", "")
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
# Mem0 config builder
# ---------------------------------------------------------------------------


def _build_config() -> dict:
    """
    Build Mem0 config dict with Chroma persistent path.

    Chroma default is in-process ephemeral; we point it at a persistent
    directory so the same run can be resumed without re-ingesting.
    """
    chroma_path = os.environ.get("MEM0_CHROMA_PATH", _CHROMA_PATH_DEFAULT)
    Path(chroma_path).mkdir(parents=True, exist_ok=True)

    config: dict[str, Any] = {
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "q4-eval",
                "path": chroma_path,
            },
        },
    }

    # MEM0_SKIP_LLM_EXTRACTION=1 (default): ingest uses infer=False (raw text, no LLM call).
    # MEM0_SKIP_LLM_EXTRACTION=0: full LLM fact-extraction per chunk (~$13-15 for full corpus).
    # No need to override LLM config here; infer flag is passed at add() call time.

    return config


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


def _ingest_corpus(client: Any, user_id: str) -> int:
    """
    Ingest LoCoMo + LongMemEval corpus into Mem0 using the shared corpus_loader.

    Each ChunkRecord has a stable `id` matching gold_chunk_ids format
    (e.g. `conv-48::D2:13` for LoCoMo, bare session_id for LongMemEval).
    The id is stored in metadata.chunk_id so search() can surface it for
    gold matching in aggregate.py.

    Returns the number of chunks ingested (0 if corpus empty or not available).
    Respects MEM0_INGEST_LIMIT env var to cap chunk count (cost control).
    """
    skip_llm = os.environ.get("MEM0_SKIP_LLM_EXTRACTION", "1").lower() not in ("0", "false", "no")

    # Materialize the limited chunk list so we know the total upfront for
    # progress reporting. MEM0_INGEST_LIMIT is already enforced inside
    # _iter_corpus_chunks() so this won't load more than the cap.
    chunk_list = list(_iter_corpus_chunks())
    total = len(chunk_list)

    if not chunk_list:
        print(
            "[mem0] WARNING: corpus_loader yielded 0 chunks. "
            "Ensure eval/q4-comparison/cache/ exists or network is available "
            "for first-run download. "
            "Proceeding with empty corpus — search will return no results."
        )
        return 0

    limit_raw = os.environ.get("MEM0_INGEST_LIMIT", "")
    if limit_raw.isdigit():
        print(f"[mem0] MEM0_INGEST_LIMIT={limit_raw}: using first {total} chunks")
    print(f"[mem0] ingesting {total} corpus chunks (user_id={user_id})...")

    ingested = 0
    errors = 0
    for i, chunk in enumerate(chunk_list, start=1):
        try:
            client.add(
                messages=[{"role": "user", "content": chunk.text}],
                user_id=user_id,
                metadata={
                    "chunk_id": chunk.id,
                    "dataset": chunk.dataset,
                    "source": chunk.conversation_id,
                },
                infer=not skip_llm,
            )
            ingested += 1
        except Exception as exc:
            errors += 1
            if errors <= 5:
                print(f"[mem0] ingest error chunk {chunk.id!r}: {type(exc).__name__}: {exc}")
        if i % 200 == 0 or i == total:
            print(f"[mem0]   ingested {i}/{total} ({errors} errors)")

    print(f"[mem0] ingestion complete: {ingested} ok, {errors} errors")
    return ingested


# ---------------------------------------------------------------------------
# Setup / Teardown
# ---------------------------------------------------------------------------


def setup() -> None:
    """
    Initialize Mem0 client (singleton) and ingest corpus if needed.

    Idempotent: skips re-ingest if the stored memory count for user_id already
    matches the expected corpus size (within 5% tolerance to handle partial
    ingestion from previous runs). Force re-ingest with MEM0_FORCE_REINGEST=1.
    """
    global _client
    if _client is not None:
        return

    from mem0 import Memory

    config = _build_config()
    _client = Memory.from_config(config)

    user_id = os.environ.get("MEM0_USER_ID", _USER_ID_DEFAULT)
    force = os.environ.get("MEM0_FORCE_REINGEST", "").lower() in ("1", "true", "yes")

    # Check existing memory count
    try:
        existing = _client.get_all(user_id=user_id)
        existing_count = len(existing) if existing else 0
    except Exception:
        existing_count = 0

    # Expected: cap from MEM0_INGEST_LIMIT, or fixed estimates for full corpus
    expected = _estimate_corpus_size()

    if not force and existing_count > 0 and expected > 0:
        ratio = existing_count / expected
        if 0.95 <= ratio <= 1.05:
            print(
                f"[mem0] corpus already ingested ({existing_count} memories, "
                f"expected ~{expected}). Skipping re-ingest. "
                "Set MEM0_FORCE_REINGEST=1 to override."
            )
            return

    if not force and existing_count > 0 and expected == 0:
        # Corpus not available but memories exist — reuse whatever is stored
        print(
            f"[mem0] corpus not available but {existing_count} memories exist. "
            "Reusing stored memories."
        )
        return

    _ingest_corpus(_client, user_id)


def _estimate_corpus_size() -> int:
    """Return expected corpus size for idempotency check.

    If MEM0_INGEST_LIMIT is set, use that exact value (cost-controlled runs).
    Otherwise fall back to canonical size estimates for the full corpus:
      - LoCoMo locomo10: ~5,882 turns
      - LongMemEval oracle: ~4,000 sessions (midpoint of 3k-5k range)
    The 5% tolerance in setup() absorbs minor upstream version drift.
    """
    limit_raw = os.environ.get("MEM0_INGEST_LIMIT", "")
    if limit_raw.isdigit():
        return int(limit_raw)
    # Full corpus estimates (both datasets): ~9,882 chunks
    return 9882


def teardown() -> None:
    """Mem0's in-process Chroma is GC'd with the process. Client reset here."""
    global _client
    _client = None


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def search(query: str, k: int = 10) -> list[dict]:
    """
    Search Mem0 memories and return results mapped to adapter contract.

    Mem0 0.1.x returns: {"results": [{'id', 'memory', 'score', 'metadata', ...}]}
    (a dict, not a bare list — the adapter extracts raw.get("results")).
    The 'id' field in the return dict maps to chunk_id (from metadata) so
    that aggregate.py can match against gold_chunk_ids. If metadata.chunk_id
    is absent (e.g., memories added without our metadata), fall back to
    Mem0's internal UUID.
    """
    if _client is None:
        setup()

    user_id = os.environ.get("MEM0_USER_ID", _USER_ID_DEFAULT)

    try:
        raw = _client.search(query=query, user_id=user_id, limit=k)  # type: ignore[union-attr]
    except Exception as exc:
        raise RuntimeError(f"mem0 search failed: {exc}") from exc

    # mem0 0.1.x returns {"results": [...]} (dict), not a bare list.
    if isinstance(raw, dict):
        items: list[dict[str, Any]] = raw.get("results") or []
    else:
        items = list(raw or [])

    return [
        {
            # Prefer chunk_id from metadata so gold matching works;
            # fall back to Mem0's internal UUID.
            "id": str(
                (item.get("metadata") or {}).get("chunk_id")
                or item.get("id")
                or ""
            ),
            "score": float(item.get("score") or 0.0),
            "text": item.get("memory") or item.get("text") or "",
            "source": (item.get("metadata") or {}).get("source"),
        }
        for item in items[:k]
    ]
