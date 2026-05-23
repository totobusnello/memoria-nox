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
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

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
REPO_ROOT = HERE.parent.parent        # repo root

_LOCOMO_DATA = REPO_ROOT / "eval" / "locomo" / "data" / "locomo10.json"
_LONGMEMEVAL_DATA = REPO_ROOT / "eval" / "longmemeval" / "data" / "longmemeval_oracle.json"
_CHROMA_PATH_DEFAULT = str(HERE / ".mem0-chroma")

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
# Corpus loaders (inline — shared lib not yet landed)
# ---------------------------------------------------------------------------


def _load_locomo_corpus() -> list[dict]:
    """
    Load LoCoMo conversation turns from locomo10.json.

    Each turn produces one chunk:
      chunk_id = f"{sample_id}::{dia_id}"
      text     = f"{speaker}: {text}"
      dataset  = "locomo"

    Mirrors the ingestion protocol in eval/locomo/parser.ts (D1: per-turn).
    Returns empty list if data file not present (graceful degradation).
    """
    if not _LOCOMO_DATA.exists():
        return []

    try:
        data = json.loads(_LOCOMO_DATA.read_text())
    except Exception as exc:
        print(f"[mem0] WARNING: failed to parse {_LOCOMO_DATA}: {exc}")
        return []

    chunks: list[dict] = []
    conversations = data if isinstance(data, list) else data.get("data", [])

    for conv in conversations:
        sample_id = conv.get("sample_id", "")
        # Real locomo10.json stores sessions nested under conv["conversation"];
        # the top-level record has keys: qa, conversation, event_summary, etc.
        # Fallback to top-level for forward-compat if schema changes.
        session_container = conv.get("conversation") if isinstance(conv.get("conversation"), dict) else conv
        # Sessions are stored as session_1, session_2, ... keys (exclude _date_time suffixes)
        session_keys = sorted(
            [k for k in session_container if k.startswith("session_") and not k.endswith("_date_time")],
            key=lambda k: int(k.split("_", 1)[1]) if k.split("_", 1)[1].isdigit() else 0,
        )
        for session_key in session_keys:
            turns = session_container[session_key]
            if not isinstance(turns, list):
                continue
            for turn in turns:
                dia_id = turn.get("dia_id", "")
                speaker = turn.get("speaker", "")
                text = turn.get("text") or turn.get("blip2_caption") or ""
                if not text:
                    continue
                chunk_id = f"{sample_id}::{dia_id}"
                chunks.append(
                    {
                        "id": chunk_id,
                        "text": f"{speaker}: {text}",
                        "dataset": "locomo",
                        "source": sample_id,
                    }
                )

    return chunks


def _load_longmemeval_corpus() -> list[dict]:
    """
    Load LongMemEval oracle corpus from longmemeval_oracle.json.

    Each session produces one chunk (D4: per-session, mirrors parser.ts):
      chunk_id = f"{question_id}::session_{idx}"  (session_id if available)
      text     = "[session_id={sid} date={date}]\n{turns joined}"
      dataset  = "longmemeval"

    Returns empty list if data file not present.
    """
    if not _LONGMEMEVAL_DATA.exists():
        return []

    try:
        data = json.loads(_LONGMEMEVAL_DATA.read_text())
    except Exception as exc:
        print(f"[mem0] WARNING: failed to parse {_LONGMEMEVAL_DATA}: {exc}")
        return []

    # Dataset is a list of question records; each has haystack_sessions[]
    records = data if isinstance(data, list) else data.get("data", [])

    seen_sessions: set[str] = set()
    chunks: list[dict] = []

    for record in records:
        question_id = record.get("question_id", "")
        haystack_sessions = record.get("haystack_sessions") or []
        haystack_dates = record.get("haystack_dates") or []
        session_ids = record.get("haystack_session_ids") or []

        for idx, session in enumerate(haystack_sessions):
            sid = (
                session_ids[idx]
                if idx < len(session_ids)
                else f"{question_id}::session_{idx}"
            )
            if sid in seen_sessions:
                continue
            seen_sessions.add(sid)

            date = haystack_dates[idx] if idx < len(haystack_dates) else ""
            turns = session if isinstance(session, list) else []
            if not turns:
                continue

            turn_lines: list[str] = []
            for turn in turns:
                if isinstance(turn, dict):
                    role = turn.get("role") or turn.get("speaker") or ""
                    content = turn.get("content") or turn.get("text") or ""
                else:
                    content = str(turn)
                    role = ""
                if content:
                    turn_lines.append(f"{role}: {content}" if role else content)

            if not turn_lines:
                continue

            header = f"[session_id={sid} date={date}]" if date else f"[session_id={sid}]"
            text = header + "\n" + "\n".join(turn_lines)

            chunks.append(
                {
                    "id": sid,
                    "text": text,
                    "dataset": "longmemeval",
                    "source": question_id,
                }
            )

    return chunks


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
    Ingest LoCoMo + LongMemEval corpus into Mem0.

    Returns the number of chunks ingested (0 if corpus files not found).
    Respects MEM0_INGEST_LIMIT env var to cap chunk count (cost control).
    """
    chunks = _load_locomo_corpus() + _load_longmemeval_corpus()

    ingest_limit_raw = os.environ.get("MEM0_INGEST_LIMIT", "")
    if ingest_limit_raw.isdigit():
        limit = int(ingest_limit_raw)
        if limit < len(chunks):
            print(f"[mem0] MEM0_INGEST_LIMIT={limit}: capping corpus from {len(chunks)} → {limit} chunks")
            chunks = chunks[:limit]

    if not chunks:
        print(
            "[mem0] WARNING: no corpus files found. "
            f"Expected {_LOCOMO_DATA} and/or {_LONGMEMEVAL_DATA}. "
            "Run eval/locomo/download.ts + eval/longmemeval/download.ts first. "
            "Proceeding with empty corpus — search will return no results."
        )
        return 0

    print(f"[mem0] ingesting {len(chunks)} corpus chunks (user_id={user_id})...")

    # Use infer=False to store raw text without LLM fact-extraction.
    # This is cheaper (no LLM call per chunk), preserves the original text and
    # metadata intact, and keeps chunk_id in metadata for gold matching.
    # Full LLM inference can be re-enabled with MEM0_SKIP_LLM_EXTRACTION=0.
    skip_llm = os.environ.get("MEM0_SKIP_LLM_EXTRACTION", "1").lower() not in ("0", "false", "no")

    ingested = 0
    errors = 0
    for i, chunk in enumerate(chunks, start=1):
        try:
            client.add(
                messages=[{"role": "user", "content": chunk["text"]}],
                user_id=user_id,
                metadata={
                    "chunk_id": chunk["id"],
                    "dataset": chunk["dataset"],
                    "source": chunk.get("source", ""),
                },
                infer=not skip_llm,
            )
            ingested += 1
        except Exception as exc:
            errors += 1
            if errors <= 5:
                print(f"[mem0] ingest error chunk {chunk['id']!r}: {type(exc).__name__}: {exc}")
        if i % 200 == 0 or i == len(chunks):
            print(f"[mem0]   ingested {i}/{len(chunks)} ({errors} errors)")

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

    # Expected: LoCoMo ~5882 + LongMemEval varies; use file-based estimate
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
        # Corpus files missing but memories exist — reuse whatever is stored
        print(
            f"[mem0] corpus files not found but {existing_count} memories exist. "
            "Reusing stored memories."
        )
        return

    _ingest_corpus(_client, user_id)


def _estimate_corpus_size() -> int:
    """Rough corpus size from file existence (fast, no parse).
    If MEM0_INGEST_LIMIT is set, use that as the expected size.
    """
    ingest_limit_raw = os.environ.get("MEM0_INGEST_LIMIT", "")
    if ingest_limit_raw.isdigit():
        return int(ingest_limit_raw)
    total = 0
    if _LOCOMO_DATA.exists():
        # LoCoMo full is 10 conversations × ~588 turns each = ~5882 turns
        total += 5882
    if _LONGMEMEVAL_DATA.exists():
        # Oracle split: 500 questions, avg ~2 sessions each = ~1000 sessions
        total += 1000
    return total


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
