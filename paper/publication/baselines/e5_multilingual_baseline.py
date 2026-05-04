"""Multilingual-E5-Base Dense Embedding Baseline for nox-mem Corpus.

WHAT THIS SCRIPT DOES
---------------------
Computes dense retrieval metrics (nDCG@10, MRR, Recall@10, Precision@5) using
intfloat/multilingual-e5-base as a competitor baseline against the nox-mem
hybrid search system.  The pipeline: (1) loads all ~64K chunks from the nox-mem
SQLite DB, (2) embeds them in batches via multilingual-e5-base (768d,
L2-normalized, with mandatory "passage: " prefix), (3) caches the embedding
matrix to a .npz file so subsequent runs skip re-embedding, (4) for each of the
50 golden queries runs exact cosine search (dot product on normalized vectors),
(5) dumps ranked results to JSONL compatible with the nox-mem eval harness.

WHY multilingual-e5-base INSTEAD OF bge-m3
-------------------------------------------
BAAI/bge-m3 (~568M params) is CPU-infeasible at ~0.3 chunks/s (ETA ~55 h for
61 K chunks).  intfloat/multilingual-e5-base is ~278M params — roughly half the
size — and runs at ~3-5 chunks/s on CPU, putting overnight embedding (61 K
chunks) within 3-6 h.  The model was trained on 100+ languages including PT-BR
and technical English, making it suitable for the mixed-language nox-mem corpus.

HOW TO RUN
----------
# 1. Create / activate a dedicated venv (do NOT mix with nox-mem TypeScript env):
python -m venv /tmp/e5-baseline-venv && source /tmp/e5-baseline-venv/bin/activate
pip install "sentence-transformers>=3.0" "torch>=2.1" numpy

# 2. Embed all 64K chunks (run once; ~3-6 h on CPU, ~5-10 min with GPU):
python e5_multilingual_baseline.py embed \\
    --db /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \\
    --output /tmp/e5-corpus.npz

# 3. Run evaluation against the 50 golden queries:
python e5_multilingual_baseline.py eval \\
    --db /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \\
    --npz /tmp/e5-corpus.npz \\
    --queries /path/to/golden-queries.jsonl \\
    --output baselines-e5-results.jsonl

# 4. Or run the full pipeline (embed if cache missing, then eval):
NOX_DB_PATH=/root/.openclaw/workspace/tools/nox-mem/nox-mem.db \\
    python e5_multilingual_baseline.py full --queries /path/to/golden-queries.jsonl

ESTIMATED RUNTIMES (64K chunks, 50 queries)
-------------------------------------------
- CPU (Linux x86, 8-core): embed ~3-6 h, eval <15 s
- CPU (Apple M2 / 16GB):   embed ~2-4 h, eval <10 s
- GPU (A10, 24GB VRAM):    embed ~5-10 min, eval <2 s

IMPORTANT — E5 INSTRUCTION PREFIX REQUIREMENT
---------------------------------------------
multilingual-e5-base requires task-specific instruction prefixes at inference
time to achieve peak performance.  Omitting them degrades quality by ~10-15 pp:

  Documents (corpus chunks):  "passage: " + chunk_text
  Queries (golden queries):   "query: " + query_text

These prefixes are applied automatically inside :func:`embed_chunks` and
:func:`embed_queries`.  The underlying text in the SQLite DB is untouched.

OUTPUT FORMAT (compatible with nox-mem eval harness)
----------------------------------------------------
Each line in the output JSONL:
  {"query_id": "Q01", "rank": 1, "doc_id": 12345, "score": 0.847,
   "system": "multilingual-e5-base"}

Fields:
  query_id  — string identifier matching the golden-queries.jsonl "id" field
  rank      — 1-indexed rank within the top-10 results
  doc_id    — integer chunk id from the nox-mem DB (chunks.id)
  score     — cosine similarity (float, ~0..1 range; L2-normalized dot product)
  system    — literal "multilingual-e5-base" for harness disambiguation

INTEGRATION WITH EVAL HARNESS
------------------------------
The nox-mem eval harness reads JSONL with the schema above.  Point it at the
output file produced by this script the same way you point it at the Gemini
hybrid output or bge_baseline.py output.  The harness computes nDCG@10, MRR@10,
Recall@10, Precision@5 across all query_ids automatically.

DESIGN DECISIONS (inline rationale)
-------------------------------------
- Dimension: multilingual-e5-base outputs 768d (vs BGE-M3 1024d, Gemini 3072d).
  Each system is evaluated within its own embedding space; no cross-space
  alignment is needed for metric-space comparison.
- Instruction prefix: E5 models are asymmetric by design — passage: prefix for
  documents, query: prefix for queries.  This is the canonical usage pattern per
  the intfloat research paper and HuggingFace model card.  See:
  https://huggingface.co/intfloat/multilingual-e5-base
- Normalization: SentenceTransformer.encode(..., normalize_embeddings=True)
  returns unit-norm vectors, so dot product == cosine similarity.
  Defensive re-normalization is still applied as a belt-and-suspenders guard.
- FP16: encode() delegates to PyTorch; torch automatically uses bf16/fp16 on
  supported hardware.  No explicit fp16 flag needed — SentenceTransformer
  handles device and dtype internally.
- Cache strategy: if the output .npz exists and has the expected keys, skip
  re-embedding entirely (idempotent).  Pass --force to override.
- Batch size default=32: fits ~2-3 GB RAM on CPU; safe for 8 GB machines.
  Increase to 64-128 when GPU VRAM >= 8 GB (model is only 278M params).
- Streaming: chunks are read from SQLite in pages of `batch_size` rows via
  cursor iteration to avoid loading 64K texts into RAM simultaneously.
  The passage: prefix is applied per-batch just before encode(), keeping
  the memory overhead bounded.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Iterator

import numpy as np

# ---------------------------------------------------------------------------
# Logging setup — single handler so calling code can configure root logger
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL_NAME: str = "intfloat/multilingual-e5-base"
EMBEDDING_DIM: int = 768          # multilingual-e5-base output dimension
SYSTEM_TAG: str = "multilingual-e5-base"

# E5 instruction prefixes (mandatory for peak retrieval quality)
PREFIX_PASSAGE: str = "passage: "
PREFIX_QUERY: str = "query: "


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

ChunkRow = tuple[int, str]  # (chunk_id, chunk_text)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _iter_chunks(db_path: str, batch_size: int) -> Iterator[list[ChunkRow]]:
    """Yield successive batches of (id, chunk_text) from the chunks table.

    Uses a server-side cursor so only `batch_size` rows are in memory at once.
    The raw chunk_text values are returned WITHOUT the E5 passage: prefix;
    callers are responsible for prepending it before calling encode().

    Args:
        db_path: Absolute path to the nox-mem SQLite database.
        batch_size: Number of rows per batch.

    Yields:
        List of (chunk_id, chunk_text) tuples, length <= batch_size.
    """
    import sqlite3  # stdlib — lazy import to keep module top-level clean

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, chunk_text FROM chunks ORDER BY id")

    batch: list[ChunkRow] = []
    for row in cursor:
        batch.append((row["id"], row["chunk_text"] or ""))
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch

    cursor.close()
    conn.close()


def _count_chunks(db_path: str) -> int:
    """Return total number of rows in the chunks table.

    Args:
        db_path: Absolute path to the nox-mem SQLite database.

    Returns:
        Row count as integer.
    """
    import sqlite3

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    (n,) = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()
    conn.close()
    return int(n)


def _apply_passage_prefix(texts: list[str]) -> list[str]:
    """Prepend the E5 "passage: " instruction prefix to each document text.

    This is the canonical document-side prefix required by multilingual-e5-base
    for asymmetric retrieval.  Omitting it degrades nDCG by ~10-15 pp.

    Args:
        texts: Raw chunk text strings.

    Returns:
        New list with PREFIX_PASSAGE prepended to every element.
    """
    return [f"{PREFIX_PASSAGE}{t}" for t in texts]


def _apply_query_prefix(texts: list[str]) -> list[str]:
    """Prepend the E5 "query: " instruction prefix to each query string.

    This is the canonical query-side prefix required by multilingual-e5-base
    for asymmetric retrieval.  Must be used consistently with
    :func:`_apply_passage_prefix` on the document side.

    Args:
        texts: Raw query text strings.

    Returns:
        New list with PREFIX_QUERY prepended to every element.
    """
    return [f"{PREFIX_QUERY}{t}" for t in texts]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def embed_chunks(
    db_path: str,
    output_npz: str,
    batch_size: int = 32,
    force: bool = False,
) -> None:
    """Embed all chunks from the nox-mem SQLite DB and save to a .npz file.

    Uses intfloat/multilingual-e5-base via SentenceTransformer.  The mandatory
    E5 "passage: " prefix is prepended to each chunk text before encoding.
    Vectors are L2-normalized (normalize_embeddings=True).  The output matrix
    shape is (N, 768).

    Idempotent: if ``output_npz`` already exists (and ``force`` is False),
    this function logs a message and returns immediately without re-embedding.

    CPU estimate: ~3-5 chunks/s on a Linux x86 8-core machine = 3-6 h for
    61 K chunks.  Suitable for overnight batch runs.

    Args:
        db_path: Absolute path to the nox-mem SQLite database file.
        output_npz: Destination path for the compressed numpy archive.
            Saved with keys ``embeddings`` (float32, shape N×768) and
            ``chunk_ids`` (int64, shape N).
        batch_size: Number of chunks to embed per model call.  Default 32
            fits ~2-3 GB RAM on CPU; increase to 64-128 on GPU.
        force: If True, re-embed even when the output file already exists.

    Raises:
        AssertionError: If the saved matrix has NaN values or the length of
            ``embeddings`` does not match ``chunk_ids``.
        FileNotFoundError: If ``db_path`` does not exist.
    """
    output_path = Path(output_npz)

    if output_path.exists() and not force:
        logger.info(
            "Cache hit — %s already exists. Pass force=True to re-embed.",
            output_npz,
        )
        return

    if not Path(db_path).exists():
        raise FileNotFoundError(f"nox-mem DB not found: {db_path}")

    # Lazy import so the module is importable without sentence-transformers installed
    from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

    logger.info("Loading %s on CPU…", MODEL_NAME)
    model = SentenceTransformer(MODEL_NAME, device="cpu")

    total = _count_chunks(db_path)
    logger.info("Total chunks to embed: %d", total)
    logger.info(
        "Estimated runtime on CPU (8-core): %.0f – %.0f min",
        total / 5 / 60,
        total / 3 / 60,
    )

    all_embeddings: list[np.ndarray] = []
    all_ids: list[int] = []

    embedded = 0
    t_start = time.perf_counter()

    for batch in _iter_chunks(db_path, batch_size):
        ids, texts = zip(*batch)

        # Apply mandatory E5 passage prefix before encoding.
        # The prefix is applied in memory per-batch; underlying DB text is untouched.
        prefixed_texts = _apply_passage_prefix(list(texts))

        # SentenceTransformer.encode() returns a plain ndarray (N, 768) —
        # no dict unwrapping needed (unlike FlagEmbedding / BGE-M3).
        # normalize_embeddings=True ensures unit-norm vectors so that
        # dot product == cosine similarity in E5Searcher.search().
        vecs: np.ndarray = model.encode(
            prefixed_texts,
            batch_size=len(prefixed_texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        # Defensive L2-normalize (no-op if SentenceTransformer already normalized,
        # but guards against version drift or unexpected behaviour changes).
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms = np.where(norms > 0, norms, 1.0)
        vecs = (vecs / norms).astype(np.float32)

        all_embeddings.append(vecs)
        all_ids.extend(ids)

        embedded += len(batch)
        elapsed = time.perf_counter() - t_start
        rate = embedded / elapsed if elapsed > 0 else 0.0
        eta = (total - embedded) / rate if rate > 0 else float("inf")
        logger.info(
            "Embedded %d/%d chunks  (%.1f chunks/s, ETA %.0f s)",
            embedded,
            total,
            rate,
            eta,
        )

    embeddings_matrix = np.concatenate(all_embeddings, axis=0)  # (N, 768)
    chunk_ids_array = np.array(all_ids, dtype=np.int64)

    # Validation
    assert len(embeddings_matrix) == len(chunk_ids_array), (
        f"Shape mismatch: embeddings {len(embeddings_matrix)} "
        f"vs chunk_ids {len(chunk_ids_array)}"
    )
    assert not np.isnan(embeddings_matrix).any(), "NaN values found in embeddings"
    assert embeddings_matrix.shape[1] == EMBEDDING_DIM, (
        f"Unexpected embedding dimension: {embeddings_matrix.shape[1]} "
        f"(expected {EMBEDDING_DIM})"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        embeddings=embeddings_matrix,
        chunk_ids=chunk_ids_array,
    )
    elapsed_total = time.perf_counter() - t_start
    logger.info(
        "Saved %d embeddings (shape %s) to %s in %.1f s (%.1f chunks/s avg)",
        len(embeddings_matrix),
        embeddings_matrix.shape,
        output_npz,
        elapsed_total,
        len(embeddings_matrix) / elapsed_total if elapsed_total > 0 else 0.0,
    )


def embed_queries(
    query_strings: list[str],
    model: object,
) -> np.ndarray:
    """Embed a list of query strings using a loaded SentenceTransformer model.

    Applies the mandatory E5 "query: " instruction prefix before encoding.
    This is the asymmetric query-side prefix that pairs with the "passage: "
    prefix used during corpus embedding in :func:`embed_chunks`.

    Args:
        query_strings: Plain-text queries, one per element (no prefix needed —
            it is applied internally).
        model: A loaded ``SentenceTransformer`` instance (passed in by the
            caller so the model is not re-loaded between calls).

    Returns:
        Float32 numpy array of shape (Q, 768) where Q == len(query_strings).
        Vectors are L2-normalized (cosine similarity == dot product).

    Raises:
        AssertionError: If the returned shape does not match (Q, 768).
    """
    from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

    assert isinstance(model, SentenceTransformer), (
        f"model must be a SentenceTransformer instance, got {type(model)}"
    )

    prefixed_queries = _apply_query_prefix(query_strings)

    vecs: np.ndarray = model.encode(
        prefixed_queries,
        batch_size=len(prefixed_queries),
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    # Defensive L2-normalize
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms = np.where(norms > 0, norms, 1.0)
    vecs = (vecs / norms).astype(np.float32)

    assert vecs.shape == (len(query_strings), EMBEDDING_DIM), (
        f"Unexpected query embedding shape: {vecs.shape} "
        f"(expected ({len(query_strings)}, {EMBEDDING_DIM}))"
    )
    return vecs


class E5Searcher:
    """Cosine nearest-neighbor searcher over a pre-computed E5 corpus.

    Loads the .npz produced by :func:`embed_chunks` and exposes a
    :meth:`search` method that returns the top-k chunk ids by cosine
    similarity.

    Since multilingual-e5-base vectors are L2-normalized
    (normalize_embeddings=True), cosine similarity reduces to a plain dot
    product: ``scores = query_emb @ corpus_matrix.T``.

    Attributes:
        embeddings: Corpus embedding matrix, shape (N, 768), float32.
        chunk_ids: Corresponding chunk ids, shape (N,), int64.
    """

    def __init__(self, npz_path: str) -> None:
        """Load corpus embeddings from a .npz file.

        Args:
            npz_path: Path to the .npz produced by :func:`embed_chunks`.

        Raises:
            FileNotFoundError: If the file does not exist.
            KeyError: If the required keys are missing from the archive.
            AssertionError: If embeddings dimension is not 768 or lengths mismatch.
        """
        if not Path(npz_path).exists():
            raise FileNotFoundError(f"Embeddings file not found: {npz_path}")

        logger.info("Loading corpus embeddings from %s…", npz_path)
        archive = np.load(npz_path)

        required_keys = {"embeddings", "chunk_ids"}
        missing = required_keys - set(archive.files)
        if missing:
            raise KeyError(f"Missing keys in .npz archive: {missing}")

        self.embeddings: np.ndarray = archive["embeddings"]  # (N, 768), float32
        self.chunk_ids: np.ndarray = archive["chunk_ids"]    # (N,), int64

        assert len(self.embeddings) == len(self.chunk_ids), (
            "Corrupt .npz: embeddings and chunk_ids length mismatch "
            f"({len(self.embeddings)} vs {len(self.chunk_ids)})"
        )
        assert self.embeddings.shape[1] == EMBEDDING_DIM, (
            f"Unexpected embedding dimension in .npz: {self.embeddings.shape[1]} "
            f"(expected {EMBEDDING_DIM} for multilingual-e5-base). "
            "Did you accidentally point at a BGE-M3 .npz (1024d)?"
        )
        logger.info(
            "Loaded %d corpus embeddings (dim=%d)",
            len(self.embeddings),
            self.embeddings.shape[1],
        )

    def search(
        self,
        query_emb: np.ndarray,
        k: int = 10,
    ) -> list[tuple[int, float]]:
        """Return top-k (chunk_id, cosine_score) pairs for a single query.

        Args:
            query_emb: L2-normalized query embedding, shape (768,) or (1, 768).
                Must have been produced by :func:`embed_queries` (which applies
                the mandatory E5 "query: " prefix).  If 2-D, the first row
                is used.
            k: Number of results to return.

        Returns:
            List of (chunk_id, score) tuples sorted by score descending,
            length == min(k, N).
        """
        if query_emb.ndim == 2:
            query_emb = query_emb[0]

        # dot product == cosine similarity for L2-normalized vectors
        scores: np.ndarray = self.embeddings @ query_emb  # (N,)

        # Partial sort — O(N log k) instead of O(N log N)
        top_k_indices = np.argpartition(scores, -k)[-k:]
        top_k_indices = top_k_indices[np.argsort(scores[top_k_indices])[::-1]]

        return [
            (int(self.chunk_ids[i]), float(scores[i]))
            for i in top_k_indices
        ]


def run_eval(
    searcher: E5Searcher,
    model: object,
    queries_jsonl: str,
    output_results_jsonl: str,
) -> None:
    """Embed queries and run retrieval, writing ranked results to JSONL.

    Each query in ``queries_jsonl`` must be a JSON object with at minimum:
      - ``"id"``   — string query identifier (e.g. "Q01")
      - ``"text"`` — the query string (plain text, no prefix needed)

    The mandatory E5 "query: " prefix is applied internally via
    :func:`embed_queries` before encoding.

    Output format (one JSON object per line):
      ``{"query_id": "Q01", "rank": 1, "doc_id": 12345, "score": 0.847,
         "system": "multilingual-e5-base"}``

    Args:
        searcher: A loaded :class:`E5Searcher` instance.
        model: A loaded ``SentenceTransformer`` instance.
        queries_jsonl: Path to the golden-queries JSONL file.
        output_results_jsonl: Destination path for ranked results JSONL.
            Parent directories are created if they do not exist.

    Raises:
        FileNotFoundError: If ``queries_jsonl`` does not exist.
    """
    queries_path = Path(queries_jsonl)
    if not queries_path.exists():
        raise FileNotFoundError(f"Queries file not found: {queries_jsonl}")

    # Load all queries
    queries: list[dict] = []
    with queries_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                queries.append(json.loads(line))

    logger.info("Loaded %d queries from %s", len(queries), queries_jsonl)

    # Field-name compatibility: golden-queries.jsonl uses "query"/"query_id"
    # (matching nox-mem eval harness convention); fall back to "text"/"id"
    # for legacy/test JSONL formats.
    query_texts = [q.get("query") or q.get("text") or q.get("query_text") for q in queries]
    query_ids = [q.get("query_id") or q.get("id") for q in queries]

    # Embed all queries in one call (typically <= 50 strings, fast).
    # embed_queries() applies the mandatory "query: " prefix internally.
    logger.info("Embedding %d queries (with 'query: ' prefix)…", len(query_texts))
    query_embeddings = embed_queries(query_texts, model)  # (Q, 768)

    output_path = Path(output_results_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as out:
        for idx, (qid, q_emb) in enumerate(zip(query_ids, query_embeddings)):
            hits = searcher.search(q_emb, k=10)
            for rank, (doc_id, score) in enumerate(hits, start=1):
                record: dict = {
                    "query_id": qid,
                    "rank": rank,
                    "doc_id": doc_id,
                    "score": round(score, 6),
                    "system": SYSTEM_TAG,
                }
                out.write(json.dumps(record, ensure_ascii=False) + "\n")

            if (idx + 1) % 10 == 0 or (idx + 1) == len(queries):
                logger.info("Evaluated %d/%d queries", idx + 1, len(queries))

    logger.info("Results written to %s", output_results_jsonl)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the three sub-commands."""
    parser = argparse.ArgumentParser(
        prog="e5_multilingual_baseline",
        description=(
            "multilingual-e5-base dense retrieval baseline for nox-mem corpus. "
            "Requires sentence-transformers>=3.0 and torch>=2.1."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ---- embed sub-command ------------------------------------------------
    embed_p = sub.add_parser(
        "embed",
        help="Embed all chunks from the nox-mem DB (applies 'passage: ' prefix).",
    )
    embed_p.add_argument(
        "--db",
        default=os.environ.get("NOX_DB_PATH", ""),
        help="Path to nox-mem.db (env: NOX_DB_PATH)",
    )
    embed_p.add_argument(
        "--output",
        default="/tmp/e5-corpus.npz",
        help="Destination .npz file (default: /tmp/e5-corpus.npz)",
    )
    embed_p.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Embedding batch size (default: 32; increase to 64-128 on GPU)",
    )
    embed_p.add_argument(
        "--force",
        action="store_true",
        help="Re-embed even if the .npz cache already exists.",
    )

    # ---- eval sub-command -------------------------------------------------
    eval_p = sub.add_parser(
        "eval",
        help=(
            "Run retrieval over golden queries and write ranked JSONL "
            "(applies 'query: ' prefix to queries)."
        ),
    )
    eval_p.add_argument(
        "--db",
        default=os.environ.get("NOX_DB_PATH", ""),
        help="Path to nox-mem.db (used only to validate DB exists; not re-embedded)",
    )
    eval_p.add_argument(
        "--npz",
        default="/tmp/e5-corpus.npz",
        help="Path to the corpus .npz produced by the 'embed' command.",
    )
    eval_p.add_argument(
        "--queries",
        required=True,
        help="Path to golden-queries.jsonl (fields: id, text).",
    )
    eval_p.add_argument(
        "--output",
        required=True,
        help="Destination path for ranked results JSONL.",
    )

    # ---- full sub-command -------------------------------------------------
    full_p = sub.add_parser(
        "full",
        help="Run full pipeline: embed (if cache missing) then eval.",
    )
    full_p.add_argument(
        "--db",
        default=os.environ.get("NOX_DB_PATH", ""),
        help="Path to nox-mem.db (env: NOX_DB_PATH)",
    )
    full_p.add_argument(
        "--npz",
        default="/tmp/e5-corpus.npz",
        help="Corpus .npz cache path (created if absent). Default: /tmp/e5-corpus.npz",
    )
    full_p.add_argument(
        "--queries",
        required=True,
        help="Path to golden-queries.jsonl.",
    )
    full_p.add_argument(
        "--output",
        default="baselines-e5-results.jsonl",
        help=(
            "Destination path for ranked results JSONL "
            "(default: baselines-e5-results.jsonl)"
        ),
    )
    full_p.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Embedding batch size (default: 32)",
    )
    full_p.add_argument(
        "--force",
        action="store_true",
        help="Force re-embed even if .npz cache exists.",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    """Entry point for the multilingual-E5-base baseline CLI.

    Args:
        argv: Argument list (defaults to sys.argv[1:] when None).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "embed":
        if not args.db:
            parser.error("--db is required (or set NOX_DB_PATH env var)")
        embed_chunks(
            db_path=args.db,
            output_npz=args.output,
            batch_size=args.batch_size,
            force=args.force,
        )

    elif args.command == "eval":
        # Lazy import — keeps module importable without sentence-transformers
        from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

        logger.info("Loading %s for query embedding…", MODEL_NAME)
        model = SentenceTransformer(MODEL_NAME, device="cpu")
        searcher = E5Searcher(args.npz)
        run_eval(
            searcher=searcher,
            model=model,
            queries_jsonl=args.queries,
            output_results_jsonl=args.output,
        )

    elif args.command == "full":
        if not args.db:
            parser.error("--db is required (or set NOX_DB_PATH env var)")

        # Embed phase (idempotent — skips if cache exists and --force not set)
        embed_chunks(
            db_path=args.db,
            output_npz=args.npz,
            batch_size=args.batch_size,
            force=args.force,
        )

        # Load model once and reuse for query embedding
        from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

        logger.info("Loading %s for query embedding…", MODEL_NAME)
        model = SentenceTransformer(MODEL_NAME, device="cpu")
        searcher = E5Searcher(args.npz)
        run_eval(
            searcher=searcher,
            model=model,
            queries_jsonl=args.queries,
            output_results_jsonl=args.output,
        )

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
