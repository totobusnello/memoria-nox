"""BGE-M3 Dense Embedding Baseline for nox-mem Corpus.

WHAT THIS SCRIPT DOES
---------------------
Computes dense retrieval metrics (nDCG@10, MRR, Recall@10, Precision@5) using
BAAI/bge-m3 as a competitor baseline against the nox-mem hybrid search system.
The pipeline: (1) loads all ~64K chunks from the nox-mem SQLite DB, (2) embeds
them in batches via BGE-M3 (1024d, L2-normalized), (3) caches the embedding
matrix to a .npz file so subsequent runs skip re-embedding, (4) for each of the
50 golden queries runs exact cosine search (dot product on normalized vectors),
(5) dumps ranked results to JSONL compatible with the nox-mem eval harness.

HOW TO RUN
----------
# 1. Create / activate a dedicated venv (do NOT mix with nox-mem TypeScript env):
python -m venv /tmp/bge-baseline-venv && source /tmp/bge-baseline-venv/bin/activate
pip install FlagEmbedding==1.2.10 "torch==2.3.0" numpy

# 2. Embed all 64K chunks (run once, takes ~20-40 min on CPU, ~3-5 min with GPU):
python bge_baseline.py embed \
    --db /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
    --output /tmp/bge-m3-embeddings.npz

# 3. Run evaluation against the 50 golden queries:
python bge_baseline.py eval \
    --db /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
    --npz /tmp/bge-m3-embeddings.npz \
    --queries /path/to/golden-queries.jsonl \
    --output /path/to/results/baselines-bge.jsonl

# 4. Or run the full pipeline (embed if cache missing, then eval):
NOX_DB_PATH=/root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
    python bge_baseline.py full --queries /path/to/golden-queries.jsonl

ESTIMATED RUNTIMES (64K chunks, 50 queries)
-------------------------------------------
- CPU (Apple M2 / 16GB): embed ~25-40 min, eval <10 s
- CPU (Linux x86, 8-core): embed ~35-50 min, eval <15 s
- GPU (A10, 24GB VRAM): embed ~3-5 min, eval <2 s

OUTPUT FORMAT (compatible with nox-mem eval harness)
----------------------------------------------------
Each line in the output JSONL:
  {"query_id": "Q01", "rank": 1, "doc_id": 12345, "score": 0.847, "system": "bge-m3"}

Fields:
  query_id  — string identifier matching the golden-queries.jsonl "id" field
  rank      — 1-indexed rank within the top-10 results
  doc_id    — integer chunk id from the nox-mem DB (chunks.id)
  score     — cosine similarity (float, 0..1 range since vectors are L2-normalized)
  system    — literal "bge-m3" for harness disambiguation

INTEGRATION WITH EVAL HARNESS
------------------------------
The nox-mem eval harness reads JSONL with the schema above.  Point it at the
output file produced by this script the same way you point it at the Gemini
hybrid output.  The harness computes nDCG@10, MRR@10, Recall@10, Precision@5
across all query_ids automatically.

DESIGN DECISIONS (inline rationale)
------------------------------------
- Dimension: BGE-M3 outputs 1024d (vs Gemini 3072d) — dimensionality differs
  but the comparison is metric-space agnostic (each system is evaluated on its
  own embedding space); no cross-space alignment needed.
- Normalization: BGEM3FlagModel.encode() with normalize_embeddings=True (the
  default) returns unit-norm vectors, so dot product == cosine similarity.
  This lets us use np.dot for O(N) search without an explicit L2 division.
- Multilingual: BGE-M3 was trained on 100+ languages including PT-BR and
  technical English — ideal for the nox-mem corpus which mixes both.
- FP16: use_fp16=True halves VRAM / RAM usage and cuts encode time ~50% on
  both GPU and modern CPU (torch CPU FP16 support since 2.1).
- Cache strategy: if the output .npz exists and has the expected keys, skip
  re-embedding entirely (idempotent).  Pass --force to override.
- Batch size default=32: empirically fits ~4 GB RAM on CPU; increase to 64
  or 128 when GPU VRAM >= 16 GB.
- Streaming: chunks are read from SQLite in pages of `batch_size` rows via
  cursor iteration to avoid loading 64K texts into RAM simultaneously.
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
# Type aliases
# ---------------------------------------------------------------------------

ChunkRow = tuple[int, str]  # (chunk_id, chunk_text)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _iter_chunks(db_path: str, batch_size: int) -> Iterator[list[ChunkRow]]:
    """Yield successive batches of (id, chunk_text) from the chunks table.

    Uses a server-side cursor so only `batch_size` rows are in memory at once.

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

    Uses BAAI/bge-m3 with FP16 weights.  Vectors are L2-normalized by the
    model (normalize_embeddings=True).  The output matrix shape is (N, 1024).

    Idempotent: if ``output_npz`` already exists (and ``force`` is False),
    this function logs a message and returns immediately without re-embedding.

    Args:
        db_path: Absolute path to the nox-mem SQLite database file.
        output_npz: Destination path for the compressed numpy archive.
            Saved with keys ``embeddings`` (float32, shape N×1024) and
            ``chunk_ids`` (int64, shape N).
        batch_size: Number of chunks to embed per model call.  Default 32
            fits ~4 GB RAM on CPU; use 64-128 on GPU.
        force: If True, re-embed even when the output file already exists.

    Raises:
        AssertionError: If the saved matrix has NaN values or the length of
            ``embeddings`` does not match ``chunk_ids``.
        FileNotFoundError: If ``db_path`` does not exist.
    """
    output_path = Path(output_npz)

    if output_path.exists() and not force:
        logger.info(
            "Cache hit — %s already exists. Pass force=True to re-embed.", output_npz
        )
        return

    if not Path(db_path).exists():
        raise FileNotFoundError(f"nox-mem DB not found: {db_path}")

    # Lazy import so the module is importable without torch installed
    from FlagEmbedding import BGEM3FlagModel  # type: ignore[import-untyped]

    logger.info("Loading BAAI/bge-m3 (use_fp16=True)…")
    model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)

    total = _count_chunks(db_path)
    logger.info("Total chunks to embed: %d", total)

    all_embeddings: list[np.ndarray] = []
    all_ids: list[int] = []

    embedded = 0
    t_start = time.perf_counter()

    for batch in _iter_chunks(db_path, batch_size):
        ids, texts = zip(*batch)

        # BGE-M3 returns a dict; dense_vecs is the 1024d embedding
        # NOTE: FlagEmbedding>=1.3 doesn't accept normalize_embeddings kwarg
        # (it's normalized by default in BGEM3FlagModel.encode); we re-normalize
        # explicitly below as a defensive belt-and-suspenders against version drift.
        result = model.encode(
            list(texts),
            batch_size=len(texts),
            max_length=1024,  # corpus chunks ≤1k tokens typical; 8192 default wastes 8× compute on padding
        )
        vecs: np.ndarray = result["dense_vecs"]  # shape: (len(batch), 1024)
        # Defensive L2-normalize (no-op if already normalized)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms = np.where(norms > 0, norms, 1.0)
        vecs = vecs / norms

        all_embeddings.append(vecs.astype(np.float32))
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

    embeddings_matrix = np.concatenate(all_embeddings, axis=0)  # (N, 1024)
    chunk_ids_array = np.array(all_ids, dtype=np.int64)

    # Validation
    assert len(embeddings_matrix) == len(chunk_ids_array), (
        f"Shape mismatch: embeddings {len(embeddings_matrix)} "
        f"vs chunk_ids {len(chunk_ids_array)}"
    )
    assert not np.isnan(embeddings_matrix).any(), "NaN values found in embeddings"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        embeddings=embeddings_matrix,
        chunk_ids=chunk_ids_array,
    )
    elapsed_total = time.perf_counter() - t_start
    logger.info(
        "Saved %d embeddings (shape %s) to %s in %.1f s",
        len(embeddings_matrix),
        embeddings_matrix.shape,
        output_npz,
        elapsed_total,
    )


def embed_queries(
    query_strings: list[str],
    model: object,
) -> np.ndarray:
    """Embed a list of query strings using a loaded BGE-M3 model.

    Args:
        query_strings: Plain-text queries, one per element.
        model: A loaded ``BGEM3FlagModel`` instance (returned by the caller
            so the model is not re-loaded between calls).

    Returns:
        Float32 numpy array of shape (Q, 1024) where Q == len(query_strings).
        Vectors are L2-normalized (cosine similarity == dot product).
    """
    result = model.encode(
        query_strings,
        batch_size=len(query_strings),
        max_length=512,  # queries are short; cap for speed
    )
    vecs: np.ndarray = result["dense_vecs"].astype(np.float32)
    # Defensive L2-normalize (FlagEmbedding>=1.3 doesn't accept normalize_embeddings kwarg)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms = np.where(norms > 0, norms, 1.0)
    vecs = vecs / norms
    assert vecs.shape == (len(query_strings), 1024), (
        f"Unexpected query embedding shape: {vecs.shape}"
    )
    return vecs


class BGESearcher:
    """Cosine nearest-neighbor searcher over a pre-computed BGE-M3 corpus.

    Loads the .npz produced by :func:`embed_chunks` and exposes a
    :meth:`search` method that returns the top-k chunk ids by cosine
    similarity.

    Since BGE-M3 vectors are L2-normalized, cosine similarity reduces to a
    plain dot product: ``scores = query_emb @ corpus_matrix.T``.

    Attributes:
        embeddings: Corpus embedding matrix, shape (N, 1024), float32.
        chunk_ids: Corresponding chunk ids, shape (N,), int64.
    """

    def __init__(self, npz_path: str) -> None:
        """Load corpus embeddings from a .npz file.

        Args:
            npz_path: Path to the .npz produced by :func:`embed_chunks`.

        Raises:
            FileNotFoundError: If the file does not exist.
            KeyError: If the required keys are missing from the archive.
        """
        if not Path(npz_path).exists():
            raise FileNotFoundError(f"Embeddings file not found: {npz_path}")

        logger.info("Loading corpus embeddings from %s…", npz_path)
        archive = np.load(npz_path)

        self.embeddings: np.ndarray = archive["embeddings"]  # (N, 1024), float32
        self.chunk_ids: np.ndarray = archive["chunk_ids"]    # (N,), int64

        assert len(self.embeddings) == len(self.chunk_ids), (
            "Corrupt .npz: embeddings and chunk_ids length mismatch"
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
            query_emb: L2-normalized query embedding, shape (1024,) or (1, 1024).
                If 2-D, the first row is used.
            k: Number of results to return.

        Returns:
            List of (chunk_id, score) tuples sorted by score descending,
            length == min(k, N).
        """
        if query_emb.ndim == 2:
            query_emb = query_emb[0]

        # dot product == cosine similarity for normalized vectors
        scores: np.ndarray = self.embeddings @ query_emb  # (N,)

        # Partial sort — O(N log k) instead of O(N log N)
        top_k_indices = np.argpartition(scores, -k)[-k:]
        top_k_indices = top_k_indices[np.argsort(scores[top_k_indices])[::-1]]

        return [
            (int(self.chunk_ids[i]), float(scores[i]))
            for i in top_k_indices
        ]


def run_eval(
    searcher: BGESearcher,
    model: object,
    queries_jsonl: str,
    output_results_jsonl: str,
) -> None:
    """Embed queries and run retrieval, writing ranked results to JSONL.

    Each query in ``queries_jsonl`` must be a JSON object with at minimum:
      - ``"id"``   — string query identifier (e.g. "Q01")
      - ``"text"`` — the query string

    Output format (one JSON object per line):
      ``{"query_id": "Q01", "rank": 1, "doc_id": 12345, "score": 0.847, "system": "bge-m3"}``

    Args:
        searcher: A loaded :class:`BGESearcher` instance.
        model: A loaded ``BGEM3FlagModel`` instance.
        queries_jsonl: Path to the golden-queries JSONL file.
        output_results_jsonl: Destination path for ranked results JSONL.
            Parent directories are created if they do not exist.
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

    query_texts = [q["text"] for q in queries]
    query_ids = [q["id"] for q in queries]

    # Embed all queries in one call (typically <= 50 strings, fast)
    logger.info("Embedding %d queries…", len(query_texts))
    query_embeddings = embed_queries(query_texts, model)  # (Q, 1024)

    output_path = Path(output_results_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as out:
        for idx, (qid, q_emb) in enumerate(zip(query_ids, query_embeddings)):
            hits = searcher.search(q_emb, k=10)
            for rank, (doc_id, score) in enumerate(hits, start=1):
                record = {
                    "query_id": qid,
                    "rank": rank,
                    "doc_id": doc_id,
                    "score": round(score, 6),
                    "system": "bge-m3",
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
        prog="bge_baseline",
        description="BGE-M3 dense retrieval baseline for nox-mem corpus.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ---- embed sub-command ------------------------------------------------
    embed_p = sub.add_parser("embed", help="Embed all chunks from the nox-mem DB.")
    embed_p.add_argument(
        "--db",
        default=os.environ.get("NOX_DB_PATH", ""),
        help="Path to nox-mem.db (env: NOX_DB_PATH)",
    )
    embed_p.add_argument(
        "--output",
        default="/tmp/bge-m3-embeddings.npz",
        help="Destination .npz file (default: /tmp/bge-m3-embeddings.npz)",
    )
    embed_p.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Embedding batch size (default: 32)",
    )
    embed_p.add_argument(
        "--force",
        action="store_true",
        help="Re-embed even if the .npz cache already exists.",
    )

    # ---- eval sub-command -------------------------------------------------
    eval_p = sub.add_parser(
        "eval", help="Run retrieval over golden queries and write ranked JSONL."
    )
    eval_p.add_argument(
        "--db",
        default=os.environ.get("NOX_DB_PATH", ""),
        help="Path to nox-mem.db (needed only for model load, not re-embed)",
    )
    eval_p.add_argument(
        "--npz",
        default="/tmp/bge-m3-embeddings.npz",
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
        default="/tmp/bge-m3-embeddings.npz",
        help="Corpus .npz cache path (created if absent).",
    )
    full_p.add_argument(
        "--queries",
        required=True,
        help="Path to golden-queries.jsonl.",
    )
    full_p.add_argument(
        "--output",
        default="/tmp/bge-m3-results.jsonl",
        help="Destination path for ranked results JSONL.",
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
    """Entry point for the BGE-M3 baseline CLI.

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
        from FlagEmbedding import BGEM3FlagModel  # type: ignore[import-untyped]

        logger.info("Loading BAAI/bge-m3 for query embedding…")
        model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
        searcher = BGESearcher(args.npz)
        run_eval(
            searcher=searcher,
            model=model,
            queries_jsonl=args.queries,
            output_results_jsonl=args.output,
        )

    elif args.command == "full":
        if not args.db:
            parser.error("--db is required (or set NOX_DB_PATH env var)")

        # Embed phase (idempotent)
        embed_chunks(
            db_path=args.db,
            output_npz=args.npz,
            batch_size=args.batch_size,
            force=args.force,
        )

        # Load model once, reuse for query embedding
        from FlagEmbedding import BGEM3FlagModel  # type: ignore[import-untyped]

        logger.info("Loading BAAI/bge-m3 for query embedding…")
        model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
        searcher = BGESearcher(args.npz)
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
