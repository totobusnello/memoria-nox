"""LOCOMO Benchmark Adapter for nox-mem Conversational Memory Evaluation (W2).

WHAT THIS SCRIPT DOES
---------------------
Bridges the LOCOMO benchmark (Maharana et al., 2024, arXiv:2402.17753) and the
nox-mem hybrid retrieval system to produce the "Conversational long-context
memory" results required for paper §5.2 Table 5.

LOCOMO is a long-horizon conversational memory benchmark where sessions consist
of multi-turn dialogues spanning months, and questions require retrieving
relevant memory from those past conversations.  Unlike BEIR (static document
retrieval), LOCOMO tests episodic memory: the corpus IS the conversation history.

Dataset source: snap-stanford/locomo (HuggingFace Hub)
  - 10 sessions, each with 30-60 turns
  - 4 question types: single-hop, multi-hop, temporal, open-domain
  - Gold answers + supporting evidence spans per question

Pipeline (5 stages):
  1. Download LOCOMO from HuggingFace (snap-stanford/locomo, ~10 MB).
  2. Chunk each session's conversation history into ~2000-char segments
     (paragraph-boundary preferred, matching nox-mem chunking strategy).
  3. Index chunks into a TEMP SQLite DB with FTS5 (CPU-only; no vectors needed
     for dry-run and BM25 baseline; vectorize separately before full eval).
  4. Select 100-query stratified subset: first 25 per question type (single-hop,
     multi-hop, temporal, open-domain).  Skips types with <25 examples to
     prevent imbalance.
  5. Compute nDCG@10, MRR, Recall@10, Precision@5 via nox-mem HTTP API
     and write results JSON compatible with existing aggregator.

LOCOMO data quirks
------------------
- Sessions are Python dicts keyed by session_id (string int like "0", "1", ...).
- Each session has a "conversation" list of turn dicts:
    {"speaker": "...", "text": "...", "time": "...", "observation": [...]}
  where "observation" contains sub-events (activities, photos, etc.).
- QA pairs are in session["qa"] — list of dicts:
    {"question": str, "answer": str, "type": str, "evidence": list[str]}
  Types: "single_hop", "multi_hop", "temporal_reasoning", "open_domain" (4 types).
  Note: HuggingFace may use underscore or space-separated variants; normalise.
- Evidence spans are substrings of conversation turns (not doc IDs).
  Ground truth retrieval: a chunk is relevant if it contains >=1 evidence span
  (substring match, case-insensitive, >=20 chars to avoid trivial matches).
- The full dataset has ~10 sessions × ~35 QA pairs each ≈ 350 questions total;
  stratified 100-subset is well-supported.
- Conversation turns have ISO timestamps in "time" field (UTC).

HOW TO RUN
----------
# 0. Create venv (separate from nox-mem TypeScript toolchain):
python3.11 -m venv /tmp/locomo-adapter-venv
source /tmp/locomo-adapter-venv/bin/activate
pip install "datasets>=2.19" "requests>=2.31"

# 1. Download dataset only (smoke test, <30 s, writes manifest):
python locomo_adapter.py --download-only \
    --cache-dir ~/.cache/locomo \
    --manifest /tmp/locomo-manifest.json

# 2. Build TEMP DB (chunk + FTS5 index all sessions, ~30 s):
python locomo_adapter.py build-db \
    --cache-dir ~/.cache/locomo \
    --db /tmp/nox-mem-locomo.db

# 3. Convert to eval queries JSONL (100-query stratified subset):
python locomo_adapter.py convert-queries \
    --cache-dir ~/.cache/locomo \
    --output /tmp/locomo-eval-queries.jsonl

# 4. Start nox-mem API pointing at TEMP DB (separate shell):
#    NOX_DB_PATH=/tmp/nox-mem-locomo.db nox-mem vectorize --all
#    NOX_DB_PATH=/tmp/nox-mem-locomo.db node dist/index.js serve

# 5. Run evaluation (100 queries → per-query JSONL, <3 min):
python locomo_adapter.py eval \
    --queries /tmp/locomo-eval-queries.jsonl \
    --output /tmp/locomo-results.jsonl \
    --api-url http://localhost:18802

# 6. Compare with baselines:
python locomo_adapter.py compare \
    --nox /tmp/locomo-results.jsonl \
    --bm25 /tmp/locomo-bm25-results.jsonl \
    --csv /tmp/locomo-comparison.csv

# Dry run (download + 3 queries against FTS5 only, no API needed):
python locomo_adapter.py dry-run \
    --cache-dir ~/.cache/locomo \
    --db /tmp/nox-mem-locomo.db \
    --n 3

EXPECTED OUTPUTS
----------------
- /tmp/nox-mem-locomo.db              — TEMP SQLite DB (chunks + FTS5)
- /tmp/locomo-manifest.json           — Dataset manifest (session count, QA stats)
- /tmp/locomo-eval-queries.jsonl      — 100-query stratified eval set
- /tmp/locomo-results.jsonl           — nox-mem per-query results
- /tmp/locomo-comparison.csv          — Cross-system table

INTEGRATION WITH PAPER §5.2 TABLE 5
-------------------------------------
The CSV produced by ``compare`` maps directly to Table 5:

  System          | nDCG@10 | MRR   | R@10  | P@5
  BM25 (Pyserini) |  ?.???  | ?.??? | ?.??? | ?.???
  nox-mem hybrid  |  ?.???  | ?.??? | ?.??? | ?.???

Citation: "n=100 LOCOMO questions (25 per type), session-chunked corpus
(2000-char segments, paragraph-boundary), evidence-span relevance, seed=42."
Reference: Maharana et al. (2024). LOCoMo: Long Context Modular Memory
for LLMs. arXiv:2402.17753.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Iterator

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("locomo_adapter")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOCOMO_HF_DATASET = "snap-stanford/locomo"
_LOCOMO_HF_SPLIT = "test"  # LOCOMO exposes data under the "test" split

# Chunking: ~2000-char target, matching nox-mem default chunk size
_CHUNK_TARGET_CHARS = 2_000
_CHUNK_OVERLAP_CHARS = 200  # small overlap to avoid cutting evidence spans

# Stratified subset: 25 per question type × 4 types = 100 queries
_SUBSET_PER_TYPE = 25
_TOTAL_SUBSET = 100

# Question type normalisations (HuggingFace may vary snake_case / spaces)
_QUESTION_TYPE_MAP: dict[str, str] = {
    "single_hop": "single_hop",
    "single-hop": "single_hop",
    "single hop": "single_hop",
    "multi_hop": "multi_hop",
    "multi-hop": "multi_hop",
    "multi hop": "multi_hop",
    "temporal_reasoning": "temporal",
    "temporal reasoning": "temporal",
    "temporal": "temporal",
    "open_domain": "open_domain",
    "open-domain": "open_domain",
    "open domain": "open_domain",
}
_CANONICAL_TYPES: list[str] = ["single_hop", "multi_hop", "temporal", "open_domain"]

# Evidence span relevance: substring must be >=20 chars to be non-trivial
_MIN_EVIDENCE_LEN = 20

# HTTP API
_DEFAULT_API_URL = "http://localhost:18802"
_DEFAULT_TEMP_DB = "/tmp/nox-mem-locomo.db"
_DEFAULT_CACHE_DIR = str(Path.home() / ".cache" / "locomo")
_DEFAULT_MANIFEST = "/tmp/locomo-manifest.json"
_DEFAULT_K = 10
_DEFAULT_SEED = 42

# nox-mem API search payload keys (matches beir_trec_covid_adapter.py convention)
_NOX_SEARCH_PAYLOAD_QUERY = "query"
_NOX_SEARCH_PAYLOAD_LIMIT = "limit"
_NOX_SEARCH_PAYLOAD_HYBRID = "hybrid"

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

QARecord = dict[str, Any]       # {question, answer, type, evidence, session_id, qa_id}
ChunkRecord = dict[str, Any]    # {chunk_id, session_id, chunk_index, chunk_text, turn_indices}
SearchHit = tuple[str, float]   # (chunk_id_str, score)
EvalQuery = dict[str, Any]      # {query_id, query_text, expected_chunk_ids, type, ...}

# ---------------------------------------------------------------------------
# Helper: HuggingFace datasets lazy import
# ---------------------------------------------------------------------------


def _require_datasets() -> Any:
    """Import and return the ``datasets`` module, raising ImportError with hint.

    Returns:
        The imported ``datasets`` package.

    Raises:
        ImportError: If ``datasets`` is not installed.
    """
    try:
        import datasets  # type: ignore[import-untyped]
        return datasets
    except ImportError as exc:
        raise ImportError(
            "datasets is not installed. Run:\n"
            "  pip install 'datasets>=2.19'"
        ) from exc


# ---------------------------------------------------------------------------
# Stage 1 — Download LOCOMO
# ---------------------------------------------------------------------------


def download_locomo(
    cache_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Download LOCOMO from HuggingFace and return sessions as a list of dicts.

    Loads ``snap-stanford/locomo`` via the HuggingFace datasets library.
    The dataset is cached to ``cache_dir`` (default ``~/.cache/locomo``).
    Subsequent calls hit the HuggingFace cache and skip re-downloading.

    LOCOMO dataset structure (each row is one session):
      - session_id: int or str
      - conversation: list of turn dicts (speaker, text, time, observation)
      - qa: list of QA dicts (question, answer, type, evidence)

    Args:
        cache_dir: Directory for the HuggingFace dataset cache.

    Returns:
        List of session dicts, each with keys: session_id (str), conversation
        (list), qa (list).

    Raises:
        ImportError: If ``datasets`` is not installed.
        RuntimeError: If loading fails or the dataset is unexpectedly empty.
    """
    if cache_dir is None:
        cache_dir = Path(_DEFAULT_CACHE_DIR)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    datasets = _require_datasets()

    logger.info(
        "Loading LOCOMO from HuggingFace (%s) — cache: %s",
        _LOCOMO_HF_DATASET, cache_dir,
    )
    t0 = time.monotonic()

    try:
        ds = datasets.load_dataset(
            _LOCOMO_HF_DATASET,
            split=_LOCOMO_HF_SPLIT,
            cache_dir=str(cache_dir),
            trust_remote_code=False,
        )
    except Exception as exc:
        # Fallback: some versions expose only "train" split or no split argument
        logger.warning(
            "Failed to load split='%s': %s — retrying without split.", _LOCOMO_HF_SPLIT, exc
        )
        try:
            ds_dict = datasets.load_dataset(
                _LOCOMO_HF_DATASET,
                cache_dir=str(cache_dir),
                trust_remote_code=False,
            )
            # Pick first available split
            split_name = list(ds_dict.keys())[0]
            ds = ds_dict[split_name]
            logger.info("Loaded split '%s' with %d sessions", split_name, len(ds))
        except Exception as exc2:
            raise RuntimeError(
                f"LOCOMO download failed: {exc2}\n"
                "Check network access and that 'snap-stanford/locomo' is public.\n"
                "Alternative: git clone https://github.com/snap-stanford/locomo "
                "and pass --cache-dir pointing to the cloned data/."
            ) from exc2

    elapsed = time.monotonic() - t0
    logger.info(
        "LOCOMO loaded: %d sessions in %.1f s", len(ds), elapsed
    )

    if len(ds) == 0:
        raise RuntimeError(
            "LOCOMO dataset is empty — unexpected; check dataset version."
        )

    # Normalise to list of plain dicts for downstream processing
    sessions: list[dict[str, Any]] = []
    for idx, row in enumerate(ds):
        session: dict[str, Any] = dict(row)
        # Ensure session_id is a string
        if "session_id" not in session:
            session["session_id"] = str(idx)
        else:
            session["session_id"] = str(session["session_id"])
        sessions.append(session)

    return sessions


# ---------------------------------------------------------------------------
# Stage 2 — Chunk conversation sessions
# ---------------------------------------------------------------------------


def _extract_turn_text(turn: dict[str, Any]) -> str:
    """Extract flat text from a single conversation turn.

    Concatenates speaker, text, and any observation sub-events into a single
    string.  Observations (activities, locations, photos) are included because
    they contain factual content that may be evidence for QA pairs.

    Args:
        turn: LOCOMO turn dict with at minimum a "text" key.

    Returns:
        Flat string representation of the turn and its observations.
    """
    parts: list[str] = []

    speaker: str = (turn.get("speaker") or "").strip()
    text: str = (turn.get("text") or "").strip()
    time_str: str = (turn.get("time") or "").strip()

    if speaker and text:
        prefix = f"[{time_str}] {speaker}: " if time_str else f"{speaker}: "
        parts.append(f"{prefix}{text}")
    elif text:
        parts.append(text)

    # Observations: list of dicts with "description" or free text
    observations = turn.get("observation") or []
    if isinstance(observations, list):
        for obs in observations:
            if isinstance(obs, dict):
                desc = (obs.get("description") or obs.get("text") or "").strip()
                if desc:
                    parts.append(f"  [obs] {desc}")
            elif isinstance(obs, str) and obs.strip():
                parts.append(f"  [obs] {obs.strip()}")

    return "\n".join(parts)


def _chunk_session(
    session_id: str,
    conversation: list[dict[str, Any]],
    target_chars: int = _CHUNK_TARGET_CHARS,
    overlap_chars: int = _CHUNK_OVERLAP_CHARS,
) -> list[ChunkRecord]:
    """Chunk a session's conversation into overlapping text segments.

    Chunking strategy:
    1. Extract flat text from each turn (speaker + text + observations).
    2. Accumulate turns into a chunk until target_chars is reached or a
       paragraph boundary (double newline) is found near the limit.
    3. Each chunk records the indices of turns it covers (for evidence linking).
    4. Overlap: the last ``overlap_chars`` of a chunk seed the next chunk to
       avoid cutting evidence spans at boundaries.

    Args:
        session_id: String session identifier.
        conversation: List of turn dicts from the LOCOMO session.
        target_chars: Target character length per chunk.
        overlap_chars: Overlap character count between consecutive chunks.

    Returns:
        List of ChunkRecord dicts with keys:
        - chunk_id: str (f"{session_id}_c{chunk_index:04d}")
        - session_id: str
        - chunk_index: int (0-based)
        - chunk_text: str
        - turn_start: int (first turn index in this chunk)
        - turn_end: int (last turn index in this chunk, inclusive)
    """
    if not conversation:
        return []

    # Pre-compute turn texts
    turn_texts: list[str] = [_extract_turn_text(t) for t in conversation]

    chunks: list[ChunkRecord] = []
    chunk_index = 0
    i = 0
    overlap_seed: str = ""

    while i < len(turn_texts):
        buf: list[str] = []
        turn_start = i

        if overlap_seed:
            buf.append(overlap_seed)

        while i < len(turn_texts):
            turn_text = turn_texts[i]
            candidate = "\n\n".join(buf + [turn_text])
            if len(candidate) > target_chars and buf:
                # Prefer to break at paragraph boundary: check if there's a
                # natural double-newline within the last ~200 chars of buffer
                current_text = "\n\n".join(buf)
                break_pos = current_text.rfind("\n\n", max(0, len(current_text) - 300))
                if break_pos > len(current_text) // 2:
                    # Split at natural boundary — remainder seeds overlap
                    chunk_text = current_text[:break_pos].strip()
                    overlap_seed = current_text[break_pos:].strip()[-overlap_chars:]
                    if chunk_text:
                        chunks.append({
                            "chunk_id": f"{session_id}_c{chunk_index:04d}",
                            "session_id": session_id,
                            "chunk_index": chunk_index,
                            "chunk_text": chunk_text,
                            "turn_start": turn_start,
                            "turn_end": max(i - 1, turn_start),
                        })
                        chunk_index += 1
                    break
                else:
                    # No natural boundary — break at turn boundary
                    break
            buf.append(turn_text)
            i += 1

        if buf and i == len(turn_texts):
            # Last batch — flush remaining turns
            chunk_text = ("\n\n".join(buf)).strip()
            if chunk_text:
                chunks.append({
                    "chunk_id": f"{session_id}_c{chunk_index:04d}",
                    "session_id": session_id,
                    "chunk_index": chunk_index,
                    "chunk_text": chunk_text,
                    "turn_start": turn_start,
                    "turn_end": len(turn_texts) - 1,
                })
                chunk_index += 1
            break
        elif buf:
            # Mid-stream flush
            chunk_text = ("\n\n".join(buf)).strip()
            overlap_seed = chunk_text[-overlap_chars:] if chunk_text else ""
            if chunk_text:
                chunks.append({
                    "chunk_id": f"{session_id}_c{chunk_index:04d}",
                    "session_id": session_id,
                    "chunk_index": chunk_index,
                    "chunk_text": chunk_text,
                    "turn_start": turn_start,
                    "turn_end": max(i - 1, turn_start),
                })
                chunk_index += 1

    return chunks


def chunk_all_sessions(
    sessions: list[dict[str, Any]],
    target_chars: int = _CHUNK_TARGET_CHARS,
    overlap_chars: int = _CHUNK_OVERLAP_CHARS,
) -> list[ChunkRecord]:
    """Chunk all LOCOMO sessions and return a flat list of ChunkRecords.

    Args:
        sessions: List of LOCOMO session dicts (from :func:`download_locomo`).
        target_chars: Target chunk size in characters.
        overlap_chars: Overlap between consecutive chunks.

    Returns:
        Flat list of ChunkRecord dicts across all sessions.
    """
    all_chunks: list[ChunkRecord] = []
    for session in sessions:
        sid = session.get("session_id", "0")
        conv = session.get("conversation") or []
        if not isinstance(conv, list):
            conv = list(conv)
        chunks = _chunk_session(sid, conv, target_chars, overlap_chars)
        all_chunks.extend(chunks)
        logger.debug(
            "Session %s: %d turns → %d chunks (avg %.0f chars)",
            sid, len(conv), len(chunks),
            sum(len(c["chunk_text"]) for c in chunks) / max(len(chunks), 1),
        )
    logger.info(
        "Total chunks across %d sessions: %d", len(sessions), len(all_chunks)
    )
    return all_chunks


# ---------------------------------------------------------------------------
# Stage 3 — Build TEMP SQLite DB
# ---------------------------------------------------------------------------


def build_temp_db(
    chunks: list[ChunkRecord],
    db_path: str | Path,
    force: bool = False,
) -> Path:
    """Write chunks to a nox-mem–compatible SQLite TEMP DB with FTS5 index.

    Schema is compatible with the nox-mem chunks table (same columns, same
    defaults) so the existing nox-mem API and vectorize pipeline can operate
    on this DB with ``NOX_DB_PATH`` override.

    The ``doc_id`` column stores the string ``chunk_id`` (e.g. "0_c0002") so
    that metric computation can use it directly without integer PK remapping.

    Idempotent: if the DB exists and row count matches, returns early.
    Pass ``force=True`` to force recreation.

    Args:
        chunks: Flat list of ChunkRecord dicts (from :func:`chunk_all_sessions`).
        db_path: Path for the output SQLite DB.
        force: If True, delete and recreate even if DB exists.

    Returns:
        Path to the created (or existing) SQLite DB.

    Raises:
        AssertionError: If no chunks are written.
    """
    db_path = Path(db_path)

    if db_path.exists() and not force:
        try:
            with sqlite3.connect(str(db_path)) as conn_check:
                (existing,) = conn_check.execute("SELECT COUNT(*) FROM chunks").fetchone()
            if existing == len(chunks):
                logger.info(
                    "TEMP DB already exists with %d rows — skipping recreate.", existing
                )
                return db_path
            else:
                logger.info(
                    "TEMP DB exists but has %d rows (expected %d) — recreating.",
                    existing, len(chunks),
                )
        except sqlite3.OperationalError:
            logger.info("TEMP DB exists but lacks chunks table — recreating.")

    if db_path.exists():
        db_path.unlink()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Creating TEMP DB: %s (%d chunks)", db_path, len(chunks))

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    # Schema compatible with nox-mem search machinery (v10 schema subset).
    # doc_id stores the string chunk_id for direct evidence matching.
    # source_file carries JSON provenance (session_id, turn range).
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id          TEXT    NOT NULL,
            chunk_text      TEXT    NOT NULL,
            source_file     TEXT,
            chunk_index     INTEGER DEFAULT 0,
            importance      REAL    DEFAULT 0.5,
            pain            REAL    DEFAULT 0.2,
            section         TEXT    DEFAULT NULL,
            section_boost   REAL    DEFAULT 1.0,
            retention_days  INTEGER DEFAULT 90,
            created_at      TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            updated_at      TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);

        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            chunk_text,
            content='chunks',
            content_rowid='id'
        );
        """
    )

    BATCH_SIZE = 500
    count = 0
    batch: list[tuple[str, str, str, int]] = []

    for chunk in chunks:
        provenance = json.dumps(
            {
                "session_id": chunk["session_id"],
                "turn_start": chunk["turn_start"],
                "turn_end": chunk["turn_end"],
                "corpus": "locomo",
            },
            ensure_ascii=False,
        )
        batch.append(
            (chunk["chunk_id"], chunk["chunk_text"], provenance, chunk["chunk_index"])
        )
        count += 1

        if len(batch) >= BATCH_SIZE:
            conn.executemany(
                "INSERT INTO chunks (doc_id, chunk_text, source_file, chunk_index) "
                "VALUES (?, ?, ?, ?)",
                batch,
            )
            conn.commit()
            batch = []

    if batch:
        conn.executemany(
            "INSERT INTO chunks (doc_id, chunk_text, source_file, chunk_index) "
            "VALUES (?, ?, ?, ?)",
            batch,
        )
        conn.commit()

    logger.info("Building FTS5 index on %d chunks…", count)
    conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
    conn.commit()
    conn.close()

    assert count > 0, f"No chunks written to TEMP DB {db_path}."
    logger.info("TEMP DB created: %d chunks → %s", count, db_path)
    return db_path


# ---------------------------------------------------------------------------
# Stage 4 — QA extraction + stratified subset selection
# ---------------------------------------------------------------------------


def _normalise_type(raw_type: str) -> str:
    """Normalise a raw LOCOMO question type string to a canonical key.

    Args:
        raw_type: Raw type string from the LOCOMO dataset.

    Returns:
        Canonical type string (one of: single_hop, multi_hop, temporal,
        open_domain) or the lowercased input if no match is found.
    """
    normalised = raw_type.strip().lower().replace(" ", "_").replace("-", "_")
    return _QUESTION_TYPE_MAP.get(normalised, normalised)


def extract_qa_records(
    sessions: list[dict[str, Any]],
    chunks: list[ChunkRecord],
) -> list[QARecord]:
    """Extract all QA pairs from LOCOMO sessions with evidence-linked chunk IDs.

    For each QA pair, resolves which chunks contain the evidence spans
    (substring match, case-insensitive, length >= _MIN_EVIDENCE_LEN).
    Chunks with at least one evidence span are tagged as relevant.

    Args:
        sessions: List of LOCOMO session dicts.
        chunks: Flat list of ChunkRecord dicts (from :func:`chunk_all_sessions`).

    Returns:
        List of QARecord dicts with keys:
        - qa_id: str (f"{session_id}_q{qa_index:04d}")
        - session_id: str
        - question: str
        - answer: str
        - type: str (normalised canonical type)
        - evidence: list[str] (raw evidence spans from LOCOMO)
        - relevant_chunk_ids: list[str] (chunks containing evidence)
        - n_relevant: int
    """
    # Build a lookup: session_id → list of chunks in that session
    session_chunks: dict[str, list[ChunkRecord]] = {}
    for chunk in chunks:
        sid = chunk["session_id"]
        session_chunks.setdefault(sid, []).append(chunk)

    qa_records: list[QARecord] = []
    total_qa = 0
    zero_evidence = 0

    for session in sessions:
        sid = session.get("session_id", "0")
        qa_list = session.get("qa") or []
        if not isinstance(qa_list, list):
            qa_list = list(qa_list)

        s_chunks = session_chunks.get(sid, [])

        for q_idx, qa in enumerate(qa_list):
            if not isinstance(qa, dict):
                continue

            question = (qa.get("question") or "").strip()
            if not question:
                continue

            answer = (qa.get("answer") or "").strip()
            raw_type = (qa.get("type") or "").strip()
            q_type = _normalise_type(raw_type) if raw_type else "unknown"

            # Evidence: list of strings (substrings of conversation turns)
            evidence_raw = qa.get("evidence") or []
            if not isinstance(evidence_raw, list):
                evidence_raw = [str(evidence_raw)] if evidence_raw else []

            # Filter trivially short evidence spans
            evidence_spans: list[str] = [
                e.strip() for e in evidence_raw
                if isinstance(e, str) and len(e.strip()) >= _MIN_EVIDENCE_LEN
            ]

            # Find relevant chunks: contains at least one evidence span
            relevant_chunk_ids: list[str] = []
            if evidence_spans and s_chunks:
                for chunk in s_chunks:
                    chunk_lower = chunk["chunk_text"].lower()
                    for span in evidence_spans:
                        if span.lower() in chunk_lower:
                            relevant_chunk_ids.append(chunk["chunk_id"])
                            break  # one span match per chunk is sufficient

            total_qa += 1
            if not relevant_chunk_ids:
                zero_evidence += 1

            qa_records.append({
                "qa_id": f"{sid}_q{q_idx:04d}",
                "session_id": sid,
                "question": question,
                "answer": answer,
                "type": q_type,
                "evidence": evidence_spans,
                "relevant_chunk_ids": relevant_chunk_ids,
                "n_relevant": len(relevant_chunk_ids),
            })

    logger.info(
        "Extracted %d QA records (%d with zero evidence chunks)",
        total_qa, zero_evidence,
    )
    if zero_evidence > total_qa * 0.3:
        logger.warning(
            "%.0f%% QA records have no evidence-linked chunks — "
            "evidence spans may not match chunk boundaries. "
            "Consider loosening _MIN_EVIDENCE_LEN (currently %d).",
            100 * zero_evidence / total_qa,
            _MIN_EVIDENCE_LEN,
        )
    return qa_records


def select_stratified_subset(
    qa_records: list[QARecord],
    n_per_type: int = _SUBSET_PER_TYPE,
    seed: int = _DEFAULT_SEED,
    require_evidence: bool = False,
) -> list[QARecord]:
    """Select a stratified 100-query subset: first n_per_type per question type.

    Selection strategy:
    - For each of the 4 canonical types (single_hop, multi_hop, temporal,
      open_domain): take the first n_per_type records in dataset order (not
      random), which preserves determinism without needing a seed.
    - If a type has fewer than n_per_type examples, include all available.
    - If ``require_evidence`` is True, skip records with no relevant chunks
      (useful for upper-bound analysis but reduces subset size).

    Rationale for "first n" vs random: LOCOMO sessions are ordered by session_id
    which is effectively random across sessions.  First-n is reproducible, avoids
    seed dependency for the subset itself, and is standard in QA benchmark papers.

    Args:
        qa_records: Full list of extracted QARecords.
        n_per_type: Target count per question type.
        seed: Unused (kept for API consistency with BEIR adapter).
        require_evidence: If True, skip QA pairs with zero evidence chunks.

    Returns:
        Stratified subset of QARecords, length <= n_per_type * len(CANONICAL_TYPES).
    """
    _ = seed  # deterministic by position; seed parameter kept for API parity

    by_type: dict[str, list[QARecord]] = {t: [] for t in _CANONICAL_TYPES}

    for qa in qa_records:
        q_type = qa["type"]
        if q_type not in by_type:
            # Map unknown types to "open_domain" as catch-all
            q_type = "open_domain"
        if require_evidence and qa["n_relevant"] == 0:
            continue
        if len(by_type[q_type]) < n_per_type:
            by_type[q_type].append(qa)

    subset: list[QARecord] = []
    for q_type in _CANONICAL_TYPES:
        bucket = by_type[q_type]
        subset.extend(bucket)
        logger.info("Type '%s': %d/%d selected", q_type, len(bucket), n_per_type)

    logger.info("Stratified subset: %d queries total", len(subset))
    return subset


def write_eval_queries(
    qa_subset: list[QARecord],
    output_path: str | Path,
) -> Path:
    """Write the stratified subset to a JSONL eval queries file.

    Output format (one JSON object per line):

    .. code-block:: json

        {
          "query_id": "0_q0003",
          "query_text": "Where did Alice go last Tuesday?",
          "session_id": "0",
          "type": "temporal",
          "expected_chunk_ids": ["0_c0002", "0_c0003"],
          "n_relevant": 2,
          "evidence": ["Alice went to the market on Tuesday"]
        }

    Args:
        qa_subset: Selected QA records (from :func:`select_stratified_subset`).
        output_path: Destination path for the output JSONL file.

    Returns:
        Path to the written JSONL file.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", encoding="utf-8") as fh:
        for qa in qa_subset:
            record: dict[str, Any] = {
                "query_id": qa["qa_id"],
                "query_text": qa["question"],
                "session_id": qa["session_id"],
                "type": qa["type"],
                "expected_chunk_ids": qa["relevant_chunk_ids"],
                "n_relevant": qa["n_relevant"],
                "evidence": qa["evidence"],
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info("Eval queries written: %d → %s", len(qa_subset), out)
    return out


# ---------------------------------------------------------------------------
# Stage 5 — nox-mem search via HTTP API
# ---------------------------------------------------------------------------


def run_nox_mem_search(
    query_text: str,
    k: int = _DEFAULT_K,
    api_url: str = _DEFAULT_API_URL,
) -> list[SearchHit]:
    """Search nox-mem via the HTTP API and return ranked (doc_id, score) pairs.

    The nox-mem HTTP API must be running on ``api_url`` with ``NOX_DB_PATH``
    pointing at the LOCOMO TEMP DB (not the production DB).

    Setup before calling:
      1. Vectorize: ``NOX_DB_PATH=/tmp/nox-mem-locomo.db nox-mem vectorize --all``
      2. Start API: ``NOX_DB_PATH=/tmp/nox-mem-locomo.db node dist/index.js serve``
      3. Verify: ``curl http://localhost:18802/api/health | jq .vectorCoverage``

    Args:
        query_text: Natural-language question from LOCOMO QA pair.
        k: Number of results to retrieve.
        api_url: Base URL of the nox-mem HTTP API.

    Returns:
        List of (doc_id_str, score) tuples sorted by score descending, length <= k.
        doc_id_str is the LOCOMO chunk_id string (e.g. "0_c0002").

    Raises:
        RuntimeError: If the HTTP request fails.
        ImportError: If ``requests`` is not installed.
    """
    try:
        import requests  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError("requests is not installed. Run: pip install requests") from exc

    payload: dict[str, Any] = {
        _NOX_SEARCH_PAYLOAD_QUERY: query_text,
        _NOX_SEARCH_PAYLOAD_LIMIT: k,
        _NOX_SEARCH_PAYLOAD_HYBRID: True,
    }

    try:
        response = requests.post(
            f"{api_url.rstrip('/')}/api/search",
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
    except Exception as exc:
        raise RuntimeError(
            f"nox-mem API request failed for query '{query_text[:60]}…': {exc}\n"
            f"Is the API running at {api_url} with NOX_DB_PATH=/tmp/nox-mem-locomo.db?"
        ) from exc

    data: dict[str, Any] = response.json()
    results: list[dict[str, Any]] = data.get("results", [])

    hits: list[SearchHit] = []
    for item in results[:k]:
        # Prefer LOCOMO string chunk_id (stored in doc_id) over integer PK
        doc_id_str: str = str(item.get("doc_id") or item.get("id", ""))
        score: float = float(item.get("score", 0.0))
        if doc_id_str:
            hits.append((doc_id_str, score))

    return hits


# ---------------------------------------------------------------------------
# Dry-run FTS5 search (CPU-only, no API needed)
# ---------------------------------------------------------------------------


def run_fts5_search(
    query_text: str,
    db_path: str | Path,
    k: int = _DEFAULT_K,
) -> list[SearchHit]:
    """Search the TEMP DB via FTS5 BM25 directly (no API, no vectors required).

    Used for the dry-run smoke test.  Mirrors the FTS5 query used by nox-mem's
    BM25 path: tokenises the query, applies FTS5 MATCH syntax.

    Args:
        query_text: Natural-language query string.
        db_path: Path to the LOCOMO TEMP SQLite DB.
        k: Number of results to return.

    Returns:
        List of (chunk_id_str, bm25_score) tuples, sorted by score descending.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"TEMP DB not found: {db_path}")

    # Build FTS5 MATCH query: quote each token, join with OR for recall
    tokens = re.findall(r'\w+', query_text.lower())
    if not tokens:
        return []

    # FTS5 implicit AND is strict; use phrase OR for higher recall on QA queries
    fts_query = " OR ".join(f'"{t}"' for t in tokens[:10])

    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        try:
            rows = conn.execute(
                """
                SELECT c.doc_id, bm25(chunks_fts) AS score
                FROM chunks_fts
                JOIN chunks c ON c.id = chunks_fts.rowid
                WHERE chunks_fts MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (fts_query, k),
            ).fetchall()
        except sqlite3.OperationalError as exc:
            logger.warning("FTS5 query failed (%s) — retrying with simpler form", exc)
            # Fallback: single-token query
            simple_query = tokens[0] if tokens else "*"
            rows = conn.execute(
                """
                SELECT c.doc_id, bm25(chunks_fts) AS score
                FROM chunks_fts
                JOIN chunks c ON c.id = chunks_fts.rowid
                WHERE chunks_fts MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (simple_query, k),
            ).fetchall()

    # bm25() returns negative values (lower = better match); negate for ranking
    return [(row[0], -row[1]) for row in rows]


# ---------------------------------------------------------------------------
# Metric helpers (binary relevance — same formulae as beir_trec_covid_adapter)
# ---------------------------------------------------------------------------


def _ndcg_at_k(retrieved: list[str], gold: set[str], k: int = 10) -> float:
    """Compute nDCG@k with binary relevance.

    Args:
        retrieved: Ordered list of retrieved chunk IDs (rank 1 = index 0).
        gold: Set of relevant chunk IDs.
        k: Cutoff rank.

    Returns:
        nDCG@k in [0.0, 1.0].
    """
    if not gold:
        return 0.0
    dcg = sum(
        1.0 / math.log2(rank + 2)
        for rank, cid in enumerate(retrieved[:k])
        if cid in gold
    )
    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(gold), k)))
    return dcg / idcg if idcg > 0.0 else 0.0


def _mrr(retrieved: list[str], gold: set[str]) -> float:
    """Compute MRR for a single query.

    Args:
        retrieved: Ordered list of retrieved chunk IDs.
        gold: Set of relevant chunk IDs.

    Returns:
        Reciprocal rank of first relevant result, or 0.0 if none.
    """
    for rank, cid in enumerate(retrieved, start=1):
        if cid in gold:
            return 1.0 / rank
    return 0.0


def _recall_at_k(retrieved: list[str], gold: set[str], k: int = 10) -> float:
    """Compute Recall@k.

    Args:
        retrieved: Ordered list of retrieved chunk IDs.
        gold: Set of relevant chunk IDs.
        k: Cutoff rank.

    Returns:
        Fraction of gold chunks found in top-k.
    """
    if not gold:
        return 0.0
    return sum(1 for cid in retrieved[:k] if cid in gold) / len(gold)


def _precision_at_k(retrieved: list[str], gold: set[str], k: int = 5) -> float:
    """Compute Precision@k.

    Args:
        retrieved: Ordered list of retrieved chunk IDs.
        gold: Set of relevant chunk IDs.
        k: Cutoff rank.

    Returns:
        Fraction of top-k results that are relevant.
    """
    if k == 0:
        return 0.0
    return sum(1 for cid in retrieved[:k] if cid in gold) / k


# ---------------------------------------------------------------------------
# Stage 5 — Full evaluation loop
# ---------------------------------------------------------------------------


def evaluate_all(
    eval_queries_jsonl: str | Path,
    output_results_jsonl: str | Path,
    k: int = _DEFAULT_K,
    api_url: str = _DEFAULT_API_URL,
) -> dict[str, float]:
    """Run nox-mem search over all eval queries and compute aggregate metrics.

    Output format (per-query, compatible with results/ aggregator):

    .. code-block:: json

        {
          "query_id": "0_q0003",
          "query_text": "Where did Alice go last Tuesday?",
          "session_id": "0",
          "type": "temporal",
          "variant": "nox-hybrid-locomo",
          "retrieved_chunk_ids": ["0_c0002", "0_c0003"],
          "retrieved_scores": [0.834, 0.711],
          "ndcg_at_10": 0.631,
          "mrr": 1.000,
          "recall_at_10": 0.500,
          "precision_at_5": 0.400,
          "n_relevant": 2,
          "duration_ms": 87
        }

    Args:
        eval_queries_jsonl: Path to eval queries JSONL (from write_eval_queries).
        output_results_jsonl: Destination path for per-query results JSONL.
        k: Number of results per query.
        api_url: nox-mem HTTP API base URL.

    Returns:
        Dict with aggregate metrics: ndcg_at_10, mrr, recall_at_10, precision_at_5.

    Raises:
        FileNotFoundError: If eval_queries_jsonl does not exist.
        AssertionError: If zero queries are evaluated.
    """
    eval_path = Path(eval_queries_jsonl)
    if not eval_path.exists():
        raise FileNotFoundError(f"Eval queries JSONL not found: {eval_path}")

    output_path = Path(output_results_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ndcg_sum = mrr_sum = recall_sum = prec_sum = 0.0
    n_queries = 0
    type_metrics: dict[str, dict[str, list[float]]] = {}

    with (
        eval_path.open(encoding="utf-8") as qfh,
        output_path.open("w", encoding="utf-8") as ofh,
    ):
        for raw in qfh:
            raw = raw.strip()
            if not raw:
                continue
            q: EvalQuery = json.loads(raw)

            query_id: str = str(q["query_id"])
            query_text: str = q["query_text"]
            gold: set[str] = set(str(c) for c in q.get("expected_chunk_ids", []))
            q_type: str = q.get("type", "unknown")

            t0 = time.monotonic()
            try:
                hits = run_nox_mem_search(query_text, k=k, api_url=api_url)
            except RuntimeError as exc:
                logger.error("Search failed for query %s: %s", query_id, exc)
                hits = []
            duration_ms = int((time.monotonic() - t0) * 1_000)

            retrieved_ids = [doc_id for doc_id, _ in hits]
            retrieved_scores = [score for _, score in hits]

            ndcg = _ndcg_at_k(retrieved_ids, gold, k=10)
            mrr_ = _mrr(retrieved_ids, gold)
            recall = _recall_at_k(retrieved_ids, gold, k=10)
            prec5 = _precision_at_k(retrieved_ids, gold, k=5)

            ndcg_sum += ndcg
            mrr_sum += mrr_
            recall_sum += recall
            prec_sum += prec5
            n_queries += 1

            # Per-type metric tracking
            type_metrics.setdefault(q_type, {
                "ndcg": [], "mrr": [], "recall": [], "prec": [],
            })
            type_metrics[q_type]["ndcg"].append(ndcg)
            type_metrics[q_type]["mrr"].append(mrr_)
            type_metrics[q_type]["recall"].append(recall)
            type_metrics[q_type]["prec"].append(prec5)

            record: dict[str, Any] = {
                "query_id": query_id,
                "query_text": query_text,
                "session_id": q.get("session_id", ""),
                "type": q_type,
                "variant": "nox-hybrid-locomo",
                "retrieved_chunk_ids": retrieved_ids,
                "retrieved_scores": [round(s, 6) for s in retrieved_scores],
                "ndcg_at_10": round(ndcg, 6),
                "mrr": round(mrr_, 6),
                "recall_at_10": round(recall, 6),
                "precision_at_5": round(prec5, 6),
                "n_relevant": len(gold),
                "duration_ms": duration_ms,
            }
            ofh.write(json.dumps(record, ensure_ascii=False) + "\n")

            if n_queries % 25 == 0:
                logger.info(
                    "Progress: %d queries — nDCG@10=%.3f MRR=%.3f",
                    n_queries, ndcg_sum / n_queries, mrr_sum / n_queries,
                )

    assert n_queries > 0, "No queries evaluated — check eval_queries_jsonl."

    aggregates: dict[str, float] = {
        "ndcg_at_10": round(ndcg_sum / n_queries, 6),
        "mrr": round(mrr_sum / n_queries, 6),
        "recall_at_10": round(recall_sum / n_queries, 6),
        "precision_at_5": round(prec_sum / n_queries, 6),
        "n_queries": float(n_queries),
    }

    # Per-type breakdown
    for q_type, m in type_metrics.items():
        n_t = len(m["ndcg"])
        if n_t:
            aggregates[f"ndcg_{q_type}"] = round(sum(m["ndcg"]) / n_t, 6)

    logger.info(
        "Eval complete — %d queries | nDCG@10=%.4f | MRR=%.4f | "
        "Recall@10=%.4f | Prec@5=%.4f",
        n_queries,
        aggregates["ndcg_at_10"],
        aggregates["mrr"],
        aggregates["recall_at_10"],
        aggregates["precision_at_5"],
    )
    logger.info("Results written → %s", output_path)
    return aggregates


# ---------------------------------------------------------------------------
# Comparison table (mirrors beir_trec_covid_adapter.compare_with_baselines)
# ---------------------------------------------------------------------------


def compare_with_baselines(
    nox_results_jsonl: str | Path,
    bm25_results_jsonl: str | Path | None = None,
    output_csv: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Generate cross-system comparison table for paper §5.2 Table 5.

    Args:
        nox_results_jsonl: Path to nox-mem hybrid results.
        bm25_results_jsonl: Optional path to BM25 results on same subset.
        output_csv: Optional path to write comparison CSV.

    Returns:
        List of per-system metric dicts.
    """
    def _load(path: Path) -> dict[str, Any]:
        metrics: dict[str, list[float]] = {
            "ndcg_at_10": [], "mrr": [], "recall_at_10": [], "precision_at_5": [],
        }
        variant = path.stem
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if "variant" in rec:
                    variant = rec["variant"]
                for key in metrics:
                    metrics[key].append(float(rec.get(key, 0.0)))
        n = len(metrics["ndcg_at_10"])
        return {
            "variant": variant,
            "ndcg_at_10": round(sum(metrics["ndcg_at_10"]) / n, 4) if n else 0.0,
            "mrr": round(sum(metrics["mrr"]) / n, 4) if n else 0.0,
            "recall_at_10": round(sum(metrics["recall_at_10"]) / n, 4) if n else 0.0,
            "precision_at_5": round(sum(metrics["precision_at_5"]) / n, 4) if n else 0.0,
            "n_queries": n,
        }

    rows: list[dict[str, Any]] = [_load(Path(nox_results_jsonl))]

    if bm25_results_jsonl is not None:
        p = Path(bm25_results_jsonl)
        if p.exists():
            rows.append(_load(p))
        else:
            logger.warning("BM25 results not found at %s — skipping.", p)

    rows.sort(key=lambda r: r["ndcg_at_10"], reverse=True)

    header = (
        f"{'System':<30} | {'nDCG@10':>8} | {'MRR':>8} | "
        f"{'R@10':>8} | {'P@5':>7} | {'N':>5}"
    )
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)
    for row in rows:
        print(
            f"{row['variant']:<30} | {row['ndcg_at_10']:>8.4f} | "
            f"{row['mrr']:>8.4f} | {row['recall_at_10']:>8.4f} | "
            f"{row['precision_at_5']:>7.4f} | {row['n_queries']:>5}"
        )
    print(sep)

    if output_csv is not None:
        csv_path = Path(output_csv)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "variant", "ndcg_at_10", "mrr", "recall_at_10", "precision_at_5", "n_queries",
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as csvf:
            writer = csv.DictWriter(csvf, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        logger.info("Comparison CSV → %s", csv_path)

    return rows


# ---------------------------------------------------------------------------
# Manifest writer (for --download-only smoke test)
# ---------------------------------------------------------------------------


def write_manifest(
    sessions: list[dict[str, Any]],
    chunks: list[ChunkRecord],
    qa_records: list[QARecord],
    subset: list[QARecord],
    manifest_path: str | Path,
) -> Path:
    """Write a JSON manifest summarising the downloaded dataset.

    The manifest is the smoke-test artifact for ``--download-only``.

    Args:
        sessions: List of LOCOMO sessions.
        chunks: All chunks across all sessions.
        qa_records: All extracted QA records.
        subset: Stratified 100-query subset.
        manifest_path: Output path for the JSON manifest.

    Returns:
        Path to the written manifest.
    """
    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    type_counts: dict[str, int] = {}
    for qa in qa_records:
        type_counts[qa["type"]] = type_counts.get(qa["type"], 0) + 1

    subset_type_counts: dict[str, int] = {}
    for qa in subset:
        subset_type_counts[qa["type"]] = subset_type_counts.get(qa["type"], 0) + 1

    avg_chunk_chars = (
        sum(len(c["chunk_text"]) for c in chunks) / len(chunks) if chunks else 0
    )
    coverage = sum(1 for qa in qa_records if qa["n_relevant"] > 0)

    manifest = {
        "dataset": _LOCOMO_HF_DATASET,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sessions": {
            "total": len(sessions),
            "session_ids": [s["session_id"] for s in sessions],
        },
        "chunks": {
            "total": len(chunks),
            "avg_chars": round(avg_chunk_chars),
            "target_chars": _CHUNK_TARGET_CHARS,
            "overlap_chars": _CHUNK_OVERLAP_CHARS,
        },
        "qa_records": {
            "total": len(qa_records),
            "with_evidence_chunks": coverage,
            "evidence_coverage_pct": round(100 * coverage / len(qa_records)) if qa_records else 0,
            "by_type": type_counts,
        },
        "subset": {
            "total": len(subset),
            "n_per_type_target": _SUBSET_PER_TYPE,
            "by_type": subset_type_counts,
        },
        "params": {
            "min_evidence_len": _MIN_EVIDENCE_LEN,
            "seed": _DEFAULT_SEED,
        },
    }

    with manifest_path.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)

    logger.info("Manifest written → %s", manifest_path)
    return manifest_path


# ---------------------------------------------------------------------------
# Dry-run: download + build DB + FTS5 search on 1-3 queries (no API)
# ---------------------------------------------------------------------------


def run_dry_run(
    cache_dir: str | Path,
    db_path: str | Path,
    manifest_path: str | Path,
    n_queries: int = 3,
) -> None:
    """Smoke test: download, chunk, index, FTS5 search on n_queries, write manifest.

    Runs the full pipeline through FTS5 (CPU-only, no API, no vectors) to
    verify the adapter works end-to-end before dispatching the full eval.

    Args:
        cache_dir: HuggingFace cache directory.
        db_path: Path for the TEMP SQLite DB.
        manifest_path: Path for the JSON manifest.
        n_queries: Number of queries to run FTS5 search on (1-5 recommended).
    """
    t_start = time.monotonic()

    logger.info("=== DRY RUN — download + chunk + index + %d FTS5 queries ===", n_queries)

    # Stage 1: download
    sessions = download_locomo(cache_dir=cache_dir)

    # Stage 2: chunk
    chunks = chunk_all_sessions(sessions)

    # Stage 3: build DB
    build_temp_db(chunks, db_path=db_path)

    # Stage 4: extract QA + subset
    qa_records = extract_qa_records(sessions, chunks)
    subset = select_stratified_subset(qa_records)

    # Stage 4b: write manifest (smoke test artifact)
    write_manifest(sessions, chunks, qa_records, subset, manifest_path)

    # Stage 5 (partial): FTS5 search on first n_queries of subset
    logger.info("Running FTS5 dry-run on %d queries…", min(n_queries, len(subset)))
    for i, qa in enumerate(subset[:n_queries]):
        t0 = time.monotonic()
        try:
            hits = run_fts5_search(qa["question"], db_path=db_path)
        except Exception as exc:
            logger.warning("FTS5 search failed for query %s: %s", qa["qa_id"], exc)
            hits = []
        duration_ms = int((time.monotonic() - t0) * 1_000)

        retrieved_ids = [h[0] for h in hits]
        gold = set(qa["relevant_chunk_ids"])
        ndcg = _ndcg_at_k(retrieved_ids, gold)

        logger.info(
            "  [%d/%d] %s (%s) — hits=%d nDCG@10=%.3f gold_chunks=%d [%d ms]",
            i + 1, n_queries,
            qa["qa_id"], qa["type"],
            len(hits), ndcg, len(gold), duration_ms,
        )
        logger.info("    Q: %s", qa["question"][:80])
        if hits:
            logger.info("    Top-1: %s (score=%.3f)", hits[0][0], hits[0][1])

    elapsed = time.monotonic() - t_start
    logger.info(
        "Dry run complete in %.1f s. Manifest: %s, DB: %s",
        elapsed, manifest_path, db_path,
    )
    logger.info(
        "Next: run 'build-db' + 'convert-queries' to prepare for full eval, "
        "then vectorize TEMP DB and start nox-mem API."
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for all sub-commands.

    Returns:
        Configured ArgumentParser with sub-commands: download-only, build-db,
        convert-queries, eval, compare, dry-run, full.
    """
    parser = argparse.ArgumentParser(
        prog="locomo_adapter",
        description=(
            "LOCOMO benchmark adapter for nox-mem conversational memory eval (W2). "
            "Pipeline: download-only → build-db → convert-queries → "
            "[vectorize+serve] → eval → compare."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # Shared args factory
    def _add_cache(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--cache-dir",
            default=_DEFAULT_CACHE_DIR,
            metavar="DIR",
            help=f"HuggingFace dataset cache directory (default: {_DEFAULT_CACHE_DIR}).",
        )

    def _add_db(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--db",
            default=os.environ.get("LOCOMO_TEMP_DB", _DEFAULT_TEMP_DB),
            metavar="PATH",
            help=f"TEMP SQLite DB path (default: {_DEFAULT_TEMP_DB} or $LOCOMO_TEMP_DB).",
        )

    # ---- --download-only (alias: download-only sub-command) -----------------
    dl = sub.add_parser(
        "download-only",
        help=(
            "Smoke test: download LOCOMO, chunk, index, run 3 FTS5 queries, "
            "write manifest. Completes in <30 s (after first download)."
        ),
    )
    _add_cache(dl)
    _add_db(dl)
    dl.add_argument(
        "--manifest",
        default=_DEFAULT_MANIFEST,
        metavar="PATH",
        help=f"Output manifest JSON path (default: {_DEFAULT_MANIFEST}).",
    )
    dl.add_argument(
        "--n",
        type=int,
        default=3,
        metavar="N",
        help="Number of FTS5 queries to dry-run (default: 3).",
    )

    # ---- dry-run (alias for download-only with more explicit naming) --------
    drp = sub.add_parser(
        "dry-run",
        help="Alias for download-only (smoke test).",
    )
    _add_cache(drp)
    _add_db(drp)
    drp.add_argument(
        "--manifest",
        default=_DEFAULT_MANIFEST,
        metavar="PATH",
        help=f"Output manifest JSON path (default: {_DEFAULT_MANIFEST}).",
    )
    drp.add_argument(
        "--n",
        type=int,
        default=3,
        metavar="N",
        help="Number of FTS5 queries to dry-run (default: 3).",
    )

    # ---- build-db -----------------------------------------------------------
    bdb = sub.add_parser(
        "build-db",
        help="Chunk all LOCOMO sessions and build TEMP SQLite DB with FTS5.",
    )
    _add_cache(bdb)
    _add_db(bdb)
    bdb.add_argument(
        "--force",
        action="store_true",
        help="Force DB recreation even if it already exists.",
    )

    # ---- convert-queries ----------------------------------------------------
    cq = sub.add_parser(
        "convert-queries",
        help="Extract stratified 100-query subset and write eval JSONL.",
    )
    _add_cache(cq)
    _add_db(cq)
    cq.add_argument(
        "--output",
        default="/tmp/locomo-eval-queries.jsonl",
        metavar="PATH",
        help="Output eval queries JSONL (default: /tmp/locomo-eval-queries.jsonl).",
    )
    cq.add_argument(
        "--n-per-type",
        type=int,
        default=_SUBSET_PER_TYPE,
        metavar="N",
        help=f"Queries per question type (default: {_SUBSET_PER_TYPE}).",
    )
    cq.add_argument(
        "--require-evidence",
        action="store_true",
        help="Skip QA pairs with no evidence-linked chunks.",
    )

    # ---- eval ---------------------------------------------------------------
    ev = sub.add_parser(
        "eval",
        help="Run nox-mem search over all eval queries and compute metrics.",
    )
    ev.add_argument(
        "--queries",
        required=True,
        metavar="PATH",
        help="Path to eval queries JSONL (from 'convert-queries').",
    )
    ev.add_argument(
        "--output",
        default="/tmp/locomo-results.jsonl",
        metavar="PATH",
        help="Output results JSONL (default: /tmp/locomo-results.jsonl).",
    )
    ev.add_argument(
        "--api-url",
        default=_DEFAULT_API_URL,
        metavar="URL",
        help=f"nox-mem HTTP API base URL (default: {_DEFAULT_API_URL}).",
    )
    ev.add_argument(
        "--k",
        type=int,
        default=_DEFAULT_K,
        metavar="N",
        help=f"Results per query (default: {_DEFAULT_K}).",
    )

    # ---- compare ------------------------------------------------------------
    cmp = sub.add_parser(
        "compare",
        help="Generate cross-system comparison table for paper §5.2 Table 5.",
    )
    cmp.add_argument(
        "--nox",
        required=True,
        metavar="PATH",
        help="nox-mem results JSONL.",
    )
    cmp.add_argument(
        "--bm25",
        metavar="PATH",
        help="BM25 results JSONL (optional).",
    )
    cmp.add_argument(
        "--csv",
        metavar="PATH",
        help="Optional output CSV path.",
    )

    # ---- full (end-to-end pipeline, no eval) --------------------------------
    fl = sub.add_parser(
        "full",
        help=(
            "End-to-end: download → build-db → convert-queries. "
            "Does NOT run eval (requires nox-mem API running separately)."
        ),
    )
    _add_cache(fl)
    _add_db(fl)
    fl.add_argument(
        "--queries-output",
        default="/tmp/locomo-eval-queries.jsonl",
        metavar="PATH",
        help="Output eval queries JSONL.",
    )
    fl.add_argument(
        "--n-per-type",
        type=int,
        default=_SUBSET_PER_TYPE,
        metavar="N",
        help=f"Queries per question type (default: {_SUBSET_PER_TYPE}).",
    )
    fl.add_argument(
        "--force",
        action="store_true",
        help="Force DB recreation.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the LOCOMO adapter CLI.

    Args:
        argv: Argument list (defaults to sys.argv[1:] when None).

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command in ("download-only", "dry-run"):
            run_dry_run(
                cache_dir=args.cache_dir,
                db_path=args.db,
                manifest_path=args.manifest,
                n_queries=args.n,
            )

        elif args.command == "build-db":
            sessions = download_locomo(cache_dir=args.cache_dir)
            chunks = chunk_all_sessions(sessions)
            db = build_temp_db(chunks, db_path=args.db, force=args.force)
            print(f"TEMP DB: {db}")
            print(
                "\nNext step: vectorize the TEMP DB, then start nox-mem API:\n"
                f"  NOX_DB_PATH={db} nox-mem vectorize --all\n"
                f"  NOX_DB_PATH={db} node dist/index.js serve\n"
                f"  curl http://localhost:18802/api/health | jq .vectorCoverage"
            )

        elif args.command == "convert-queries":
            sessions = download_locomo(cache_dir=args.cache_dir)
            chunks = chunk_all_sessions(sessions)
            qa_records = extract_qa_records(sessions, chunks)
            subset = select_stratified_subset(
                qa_records,
                n_per_type=args.n_per_type,
                require_evidence=args.require_evidence,
            )
            out = write_eval_queries(subset, output_path=args.output)
            print(f"Eval queries: {out}")
            print(f"Total: {len(subset)} queries")

        elif args.command == "eval":
            aggregates = evaluate_all(
                eval_queries_jsonl=args.queries,
                output_results_jsonl=args.output,
                k=args.k,
                api_url=args.api_url,
            )
            print("\n=== AGGREGATE METRICS (nox-mem hybrid, LOCOMO) ===")
            for metric, value in aggregates.items():
                if isinstance(value, float):
                    print(f"  {metric:<25} {value:.4f}")

        elif args.command == "compare":
            rows = compare_with_baselines(
                nox_results_jsonl=args.nox,
                bm25_results_jsonl=args.bm25,
                output_csv=args.csv,
            )
            _ = rows  # already printed by compare_with_baselines

        elif args.command == "full":
            logger.info("=== Phase 1: Download LOCOMO ===")
            sessions = download_locomo(cache_dir=args.cache_dir)

            logger.info("=== Phase 2: Chunk sessions ===")
            chunks = chunk_all_sessions(sessions)

            logger.info("=== Phase 3: Build TEMP DB ===")
            db = build_temp_db(chunks, db_path=args.db, force=args.force)

            logger.info("=== Phase 4: Extract QA + build eval queries ===")
            qa_records = extract_qa_records(sessions, chunks)
            subset = select_stratified_subset(qa_records, n_per_type=args.n_per_type)
            queries_out = write_eval_queries(subset, output_path=args.queries_output)

            print("\n=== Phases 1-4 complete ===")
            print(f"TEMP DB:      {db}")
            print(f"Eval queries: {queries_out} ({len(subset)} queries)")
            print("\nManual steps before running 'eval':")
            print(
                f"  # 1. Vectorize (~10-20 min depending on chunk count):\n"
                f"  NOX_DB_PATH={db} nox-mem vectorize --all\n"
                f"\n  # 2. Start API (separate shell):\n"
                f"  NOX_DB_PATH={db} node dist/index.js serve\n"
                f"\n  # 3. Verify health:\n"
                f"  curl http://localhost:18802/api/health | jq .vectorCoverage\n"
                f"\n  # 4. Run eval:\n"
                f"  python locomo_adapter.py eval \\\n"
                f"    --queries {queries_out} \\\n"
                f"    --output /tmp/locomo-results.jsonl"
            )

    except (FileNotFoundError, ValueError, RuntimeError, ImportError) as exc:
        logger.error("%s: %s", type(exc).__name__, exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
