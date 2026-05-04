"""
BM25 baseline via Pyserini for the nox-mem corpus.

This script exports the nox-mem chunk corpus from SQLite, builds a Lucene BM25
index via Pyserini, runs a set of golden eval queries against it, and writes
per-query results in the JSONL format that the nox-mem eval harness consumes
via ``nox-mem eval-import``.

The BM25 configuration uses Pyserini defaults (k1=0.9, b=0.4), which are
Anserini-tuned BM25 parameters known to generalise well across TREC/BEIR
collections.  No stemming or stopword removal is applied beyond Lucene's
default StandardAnalyzer (lowercases + splits on Unicode boundaries) so the
comparison against nox-mem FTS5 is fair: FTS5 also uses default tokenisation
without custom stemmers.  The only deliberate pre-processing is collapsing
runs of whitespace and stripping ASCII control characters from ``chunk_text``
before indexing—both safe and reversible.

-------------------------------------------------------------------------------
HOW TO RUN
-------------------------------------------------------------------------------

Prerequisites
~~~~~~~~~~~~~
  # 1. Separate venv (do NOT mix with nox-mem TypeScript toolchain)
  python3.11 -m venv /tmp/bm25-env
  source /tmp/bm25-env/bin/activate
  pip install "pyserini==0.36.0"
  # faiss-cpu comes in as a transitive dep; if pip omits it: pip install faiss-cpu

  # 2. JDK 21 must be on PATH (Pyserini shells out to java for indexing)
  java -version   # expect: openjdk 21.x

Full pipeline (all args explicit)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  export NOX_DB_PATH=/root/.openclaw/workspace/tools/nox-mem/nox-mem.db

  python bm25_baseline.py \\
    --db        "$NOX_DB_PATH" \\
    --jsonl     /tmp/nox-corpus.jsonl \\
    --index-dir /tmp/pyserini-nox-index \\
    --queries   /path/to/golden_queries.jsonl \\
    --output    /tmp/baselines-bm25.jsonl \\
    --k         10

Quick run (using env var + all defaults)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  export NOX_DB_PATH=/root/.openclaw/workspace/tools/nox-mem/nox-mem.db
  python bm25_baseline.py --queries golden_queries.jsonl

  # Defaults:
  #   --jsonl      /tmp/nox-corpus.jsonl
  #   --index-dir  /tmp/pyserini-nox-index
  #   --output     /tmp/baselines-bm25.jsonl
  #   --k          10

Skip export + index if already built
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  python bm25_baseline.py \\
    --skip-export \\
    --skip-index \\
    --jsonl     /tmp/nox-corpus.jsonl \\
    --index-dir /tmp/pyserini-nox-index \\
    --queries   golden_queries.jsonl \\
    --output    /tmp/baselines-bm25.jsonl

-------------------------------------------------------------------------------
INPUT: golden_queries.jsonl  (one JSON object per line)
-------------------------------------------------------------------------------
  {"query": "como funciona withOpAudit", "expected_chunk_ids": [1234, 5678],
   "difficulty": "medium", "category": "entity", "query_id": 1}

  Fields:
    query               (str, required)  — natural-language query text
    expected_chunk_ids  (list[int], req) — gold chunk IDs from eval_queries table
    query_id            (int, optional)  — eval_queries.id; falls back to 1-based counter
    difficulty          (str, optional)  — easy/medium/hard (pass-through to output)
    category            (str, optional)  — entity/concept/temporal/... (pass-through)

-------------------------------------------------------------------------------
OUTPUT: baselines-bm25.jsonl  (one JSON object per line)
-------------------------------------------------------------------------------
  {"query_id": 1, "query": "...", "variant": "bm25-pyserini",
   "retrieved_chunk_ids": [4321, 9999, ...],
   "retrieved_scores": [12.34, 11.22, ...],
   "ndcg_at_10": 0.412, "mrr": 0.333, "recall_at_10": 0.500,
   "precision_at_5": 0.200, "duration_ms": 42}

  Fields match eval_results schema (R01a spec, 2026-04-27).

-------------------------------------------------------------------------------
HOW TO IMPORT INTO NOX-MEM EVAL HARNESS
-------------------------------------------------------------------------------
  # On the VPS, after copying baselines-bm25.jsonl:
  nox-mem eval-import \\
    --source  bm25-baseline \\
    --variant bm25-pyserini \\
    --file    baselines-bm25.jsonl

  # Then compare against the stored hybrid run:
  nox-mem eval compare <bm25_run_id> <hybrid_run_id>
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("bm25_baseline")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PYSERINI_INDEXER_MODULE = "pyserini.index.lucene"
_DEFAULT_JSONL_PATH = Path("/tmp/nox-corpus.jsonl")
_DEFAULT_INDEX_DIR = Path("/tmp/pyserini-nox-index")
_DEFAULT_OUTPUT_PATH = Path("/tmp/baselines-bm25.jsonl")
_DEFAULT_K = 10
_INDEXER_THREADS = 4

# Matches runs of whitespace and ASCII control chars (except \t which Lucene handles fine)
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+")
_WS_RE = re.compile(r"[ \t\r\n]+")


# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------


def _normalise_text(text: str) -> str:
    """Lightweight text normalisation for indexing and querying.

    Applies only:
    - Strip ASCII control characters (not whitespace classes)
    - Collapse runs of whitespace to a single space
    - Strip leading/trailing whitespace

    Intentionally does NOT apply stemming, stopword removal, or lowercasing
    beyond what Lucene StandardAnalyzer already does.  This keeps the BM25
    baseline comparable to nox-mem FTS5 which also uses default tokenisation.

    Args:
        text: Raw chunk text or query string.

    Returns:
        Normalised string safe for Lucene indexing or querying.
    """
    text = _CTRL_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Step 1: Export chunks to JSONL
# ---------------------------------------------------------------------------


def export_chunks_to_jsonl(db_path: str | Path, output_jsonl: str | Path) -> int:
    """Export nox-mem chunks to a Pyserini-compatible JSONL file.

    Reads all rows from the ``chunks`` table and writes one JSON object per
    line with the two fields Pyserini's ``JsonCollection`` expects:

    .. code-block:: json

        {"id": "42", "contents": "chunk text …"}

    The ``id`` field is always a string (Pyserini docid contract).  The
    ``contents`` field is the normalised ``chunk_text`` column value.

    Args:
        db_path: Absolute path to the nox-mem SQLite database.
        output_jsonl: Destination path for the output JSONL file.
            The parent directory is created if it does not exist.

    Returns:
        Number of chunks written to the JSONL file.

    Raises:
        FileNotFoundError: If ``db_path`` does not exist.
        AssertionError: If the chunks table is empty.
        sqlite3.Error: On any database access error.
    """
    db_path = Path(db_path)
    output_jsonl = Path(output_jsonl)

    if not db_path.exists():
        raise FileNotFoundError(f"nox-mem DB not found: {db_path}")

    logger.info("Connecting to DB: %s", db_path)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        # Use server-side cursor for memory efficiency over 64K+ rows
        cursor = conn.execute(
            "SELECT id, chunk_text FROM chunks ORDER BY id"
        )
        with output_jsonl.open("w", encoding="utf-8") as fh:
            while True:
                batch = cursor.fetchmany(2_000)
                if not batch:
                    break
                for row in batch:
                    contents = _normalise_text(row["chunk_text"] or "")
                    if not contents:
                        logger.debug("Skipping empty chunk id=%s", row["id"])
                        continue
                    doc = {"id": str(row["id"]), "contents": contents}
                    fh.write(json.dumps(doc, ensure_ascii=False) + "\n")
                    count += 1
                logger.debug("Exported %d chunks so far…", count)

    assert count > 0, (
        f"No chunks exported from {db_path}. "
        "Verify the 'chunks' table is populated and chunk_text is non-empty."
    )
    logger.info("Exported %d chunks → %s", count, output_jsonl)
    return count


# ---------------------------------------------------------------------------
# Step 2: Build Pyserini / Lucene BM25 index
# ---------------------------------------------------------------------------


def build_pyserini_index(
    jsonl_path: str | Path,
    index_dir: str | Path,
    threads: int = _INDEXER_THREADS,
) -> None:
    """Build a Lucene BM25 index from a JSONL corpus file using Pyserini.

    Shells out to ``python -m pyserini.index.lucene`` with the arguments
    required for a ``JsonCollection`` index that stores positions, doc vectors,
    and raw text (needed for BM25 scoring and snippet retrieval).

    The JSONL file must reside in its own directory because Pyserini's
    ``--input`` flag expects a *directory* path, not a file path.  This
    function creates a staging directory alongside ``jsonl_path`` that contains
    a symlink (or copy on non-POSIX platforms) to the file.

    Args:
        jsonl_path: Path to the corpus JSONL file produced by
            :func:`export_chunks_to_jsonl`.
        index_dir: Directory where the Lucene index will be written.
            Created if it does not exist.  **Existing index is overwritten.**
        threads: Number of indexing threads.  Defaults to 4 which saturates
            typical 4-core VPS without memory pressure.

    Raises:
        FileNotFoundError: If ``jsonl_path`` does not exist.
        AssertionError: If the index directory is empty after indexing.
        subprocess.CalledProcessError: If the Pyserini indexer exits non-zero.
    """
    jsonl_path = Path(jsonl_path)
    index_dir = Path(index_dir)

    if not jsonl_path.exists():
        raise FileNotFoundError(f"Corpus JSONL not found: {jsonl_path}")

    # Pyserini --input expects a directory containing the JSONL file(s)
    input_dir = jsonl_path.parent
    index_dir.mkdir(parents=True, exist_ok=True)

    cmd: list[str] = [
        sys.executable,
        "-m",
        _PYSERINI_INDEXER_MODULE,
        "--collection", "JsonCollection",
        "--input", str(input_dir),
        "--index", str(index_dir),
        "--generator", "DefaultLuceneDocumentGenerator",
        "--threads", str(threads),
        "--storePositions",
        "--storeDocvectors",
        "--storeRaw",
    ]

    logger.info("Building Pyserini index — this may take several minutes for 64K+ docs")
    logger.info("Command: %s", " ".join(cmd))
    t0 = time.monotonic()

    result = subprocess.run(
        cmd,
        capture_output=False,  # let stdout/stderr stream to terminal
        text=True,
        check=True,
    )

    elapsed = time.monotonic() - t0
    logger.info("Indexing completed in %.1fs", elapsed)

    # Sanity check: index directory must be non-empty
    index_files = list(index_dir.iterdir())
    assert len(index_files) > 0, (
        f"Pyserini index directory is empty after build: {index_dir}. "
        "Check the indexer output above for errors."
    )
    logger.info("Index contains %d files: %s", len(index_files), index_dir)


# ---------------------------------------------------------------------------
# Step 3: BM25 search wrapper
# ---------------------------------------------------------------------------


class BM25Searcher:
    """Thin wrapper around Pyserini's ``LuceneSearcher`` for nox-mem eval.

    Encapsulates lazy import of ``pyserini`` (so the module can be imported
    without Pyserini installed, as long as search is not called), query
    normalisation, and result deserialization.

    Args:
        index_dir: Path to the Lucene index built by :func:`build_pyserini_index`.
        bm25_k1: BM25 k1 parameter (term frequency saturation).
            Pyserini default is 0.9.
        bm25_b: BM25 b parameter (document length normalisation).
            Pyserini default is 0.4.

    Example::

        searcher = BM25Searcher("/tmp/pyserini-nox-index")
        hits = searcher.search("como funciona withOpAudit", k=10)
        # hits = [(chunk_id_int, score_float), ...]
    """

    def __init__(
        self,
        index_dir: str | Path,
        bm25_k1: float = 0.9,
        bm25_b: float = 0.4,
    ) -> None:
        self._index_dir = Path(index_dir)
        self._k1 = bm25_k1
        self._b = bm25_b
        self._searcher: Any = None  # LuceneSearcher, imported lazily

    def _ensure_loaded(self) -> None:
        """Lazily initialise the LuceneSearcher on first use.

        Raises:
            ImportError: If ``pyserini`` is not installed in the active
                Python environment.
            FileNotFoundError: If ``index_dir`` does not exist or is empty.
        """
        if self._searcher is not None:
            return

        try:
            from pyserini.search.lucene import LuceneSearcher  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "pyserini is not installed. "
                "Run: pip install 'pyserini==0.36.0'"
            ) from exc

        if not self._index_dir.exists():
            raise FileNotFoundError(f"Index directory not found: {self._index_dir}")

        logger.info("Loading Lucene index from %s", self._index_dir)
        self._searcher = LuceneSearcher(str(self._index_dir))
        self._searcher.set_bm25(self._k1, self._b)
        logger.info(
            "BM25Searcher ready (k1=%.2f, b=%.2f)", self._k1, self._b
        )

    def search(self, query: str, k: int = _DEFAULT_K) -> list[tuple[int, float]]:
        """Search the BM25 index for a natural-language query.

        The query string is normalised (same rules as during indexing) before
        being passed to Lucene.  Special Lucene query syntax characters are
        NOT escaped — this intentionally allows Lucene to parse multi-word
        queries as bag-of-words BM25 (no phrase boosting).

        Args:
            query: Natural-language query string (Portuguese or English).
            k: Maximum number of results to return.

        Returns:
            List of ``(chunk_id, score)`` tuples sorted by score descending.
            ``chunk_id`` is an integer matching ``chunks.id`` in nox-mem.db.
            The list may be shorter than ``k`` if the index has fewer matching
            documents.
        """
        self._ensure_loaded()
        normalised = _normalise_text(query)
        if not normalised:
            logger.warning("Empty query after normalisation, returning []")
            return []

        hits = self._searcher.search(normalised, k=k)
        return [(int(h.docid), float(h.score)) for h in hits]

    def close(self) -> None:
        """Release the underlying Lucene reader (optional, GC handles it)."""
        if self._searcher is not None:
            try:
                self._searcher.close()
            except Exception:
                pass
            self._searcher = None

    def __enter__(self) -> "BM25Searcher":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Metric helpers (matching R01a spec formulae exactly)
# ---------------------------------------------------------------------------


def _ndcg_at_k(
    retrieved: list[int], gold: set[int], k: int = 10
) -> float:
    """Compute nDCG@k with binary relevance.

    Args:
        retrieved: Ordered list of retrieved chunk IDs (first = rank 1).
        gold: Set of relevant chunk IDs (gold standard).
        k: Cutoff rank.

    Returns:
        nDCG@k in [0.0, 1.0]. Returns 0.0 if ``gold`` is empty.
    """
    if not gold:
        return 0.0
    dcg = sum(
        1.0 / math.log2(rank + 2)
        for rank, doc_id in enumerate(retrieved[:k])
        if doc_id in gold
    )
    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(gold), k)))
    return dcg / idcg if idcg > 0.0 else 0.0


def _mrr(retrieved: list[int], gold: set[int]) -> float:
    """Compute MRR (Mean Reciprocal Rank for a single query).

    Args:
        retrieved: Ordered list of retrieved chunk IDs.
        gold: Set of relevant chunk IDs.

    Returns:
        Reciprocal rank of first relevant hit, or 0.0 if none found.
    """
    for rank, doc_id in enumerate(retrieved, start=1):
        if doc_id in gold:
            return 1.0 / rank
    return 0.0


def _recall_at_k(retrieved: list[int], gold: set[int], k: int = 10) -> float:
    """Compute Recall@k.

    Args:
        retrieved: Ordered list of retrieved chunk IDs.
        gold: Set of relevant chunk IDs.
        k: Cutoff rank.

    Returns:
        Fraction of gold items found in top-k. Returns 0.0 if ``gold`` is empty.
    """
    if not gold:
        return 0.0
    hits = sum(1 for doc_id in retrieved[:k] if doc_id in gold)
    return hits / len(gold)


def _precision_at_k(retrieved: list[int], gold: set[int], k: int = 5) -> float:
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
    hits = sum(1 for doc_id in retrieved[:k] if doc_id in gold)
    return hits / k


# ---------------------------------------------------------------------------
# Step 4: Run eval over golden queries
# ---------------------------------------------------------------------------


def run_eval(
    searcher: BM25Searcher,
    queries_jsonl: str | Path,
    output_results_jsonl: str | Path,
    k: int = _DEFAULT_K,
) -> dict[str, float]:
    """Run BM25 search over golden queries and write per-query result JSONL.

    For each query in ``queries_jsonl``:
    1. Search the BM25 index for top-``k`` results.
    2. Compute nDCG@10, MRR, Recall@10, and Precision@5.
    3. Write one JSON record to ``output_results_jsonl``.

    The output format matches the ``eval_results`` schema (R01a spec) and is
    directly importable via ``nox-mem eval-import --source bm25-baseline``.

    Args:
        searcher: An initialised :class:`BM25Searcher` instance.
        queries_jsonl: Path to the golden queries JSONL file.  Each line must
            be a JSON object with at least ``query`` and
            ``expected_chunk_ids`` fields (see module docstring).
        output_results_jsonl: Destination path for per-query result records.
            Parent directory is created if missing.
        k: Number of results to retrieve per query (must be >= 10 for
            nDCG@10 and Recall@10 to be meaningful).

    Returns:
        Dict with aggregate metrics: ``ndcg_at_10``, ``mrr``,
        ``recall_at_10``, ``precision_at_5`` (averages over all queries).

    Raises:
        FileNotFoundError: If ``queries_jsonl`` does not exist.
        ValueError: If a query line is malformed (missing required fields).
    """
    queries_path = Path(queries_jsonl)
    output_path = Path(output_results_jsonl)

    if not queries_path.exists():
        raise FileNotFoundError(f"Queries JSONL not found: {queries_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    ndcg_sum = 0.0
    mrr_sum = 0.0
    recall_sum = 0.0
    precision_sum = 0.0
    n_queries = 0

    with (
        queries_path.open("r", encoding="utf-8") as qfh,
        output_path.open("w", encoding="utf-8") as ofh,
    ):
        for line_no, raw_line in enumerate(qfh, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                q = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                logger.warning("Skipping malformed JSON at line %d: %s", line_no, exc)
                continue

            query_text: str | None = q.get("query")
            expected: list[int] | None = q.get("expected_chunk_ids")
            if query_text is None or expected is None:
                raise ValueError(
                    f"Line {line_no}: missing 'query' or 'expected_chunk_ids' field"
                )

            query_id: int = q.get("query_id", line_no)
            gold: set[int] = set(int(cid) for cid in expected)

            t0 = time.monotonic()
            hits = searcher.search(query_text, k=k)
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
            precision_sum += prec5
            n_queries += 1

            record: dict[str, Any] = {
                "query_id": query_id,
                "query": query_text,
                "variant": "bm25-pyserini",
                "difficulty": q.get("difficulty"),
                "category": q.get("category"),
                "retrieved_chunk_ids": retrieved_ids,
                "retrieved_scores": [round(s, 6) for s in retrieved_scores],
                "ndcg_at_10": round(ndcg, 6),
                "mrr": round(mrr_, 6),
                "recall_at_10": round(recall, 6),
                "precision_at_5": round(prec5, 6),
                "duration_ms": duration_ms,
            }
            ofh.write(json.dumps(record, ensure_ascii=False) + "\n")

            if n_queries % 10 == 0:
                logger.info(
                    "Progress: %d queries — nDCG@10=%.3f, MRR=%.3f",
                    n_queries,
                    ndcg_sum / n_queries,
                    mrr_sum / n_queries,
                )

    if n_queries == 0:
        logger.warning("No queries processed — output file is empty.")
        return {"ndcg_at_10": 0.0, "mrr": 0.0, "recall_at_10": 0.0, "precision_at_5": 0.0}

    aggregates = {
        "ndcg_at_10": round(ndcg_sum / n_queries, 6),
        "mrr": round(mrr_sum / n_queries, 6),
        "recall_at_10": round(recall_sum / n_queries, 6),
        "precision_at_5": round(precision_sum / n_queries, 6),
    }

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
# CLI argument parsing
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        Configured :class:`argparse.ArgumentParser` instance.
    """
    parser = argparse.ArgumentParser(
        prog="bm25_baseline",
        description=(
            "BM25 baseline (Pyserini/Lucene) for the nox-mem corpus. "
            "Runs export → index → eval pipeline and writes per-query results "
            "compatible with the nox-mem eval harness."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("NOX_DB_PATH"),
        metavar="PATH",
        help=(
            "Path to nox-mem.db SQLite file.  "
            "Defaults to $NOX_DB_PATH env var.  Required unless --skip-export."
        ),
    )
    parser.add_argument(
        "--jsonl",
        default=str(_DEFAULT_JSONL_PATH),
        metavar="PATH",
        help=f"Corpus JSONL path (default: {_DEFAULT_JSONL_PATH}).",
    )
    parser.add_argument(
        "--index-dir",
        default=str(_DEFAULT_INDEX_DIR),
        metavar="DIR",
        help=f"Lucene index directory (default: {_DEFAULT_INDEX_DIR}).",
    )
    parser.add_argument(
        "--queries",
        required=True,
        metavar="PATH",
        help="Path to golden_queries.jsonl (required).",
    )
    parser.add_argument(
        "--output",
        default=str(_DEFAULT_OUTPUT_PATH),
        metavar="PATH",
        help=f"Output results JSONL path (default: {_DEFAULT_OUTPUT_PATH}).",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=_DEFAULT_K,
        metavar="N",
        help=f"Number of results per query (default: {_DEFAULT_K}).",
    )
    parser.add_argument(
        "--bm25-k1",
        type=float,
        default=0.9,
        metavar="FLOAT",
        help="BM25 k1 parameter (default: 0.9 — Anserini tuned).",
    )
    parser.add_argument(
        "--bm25-b",
        type=float,
        default=0.4,
        metavar="FLOAT",
        help="BM25 b parameter (default: 0.4 — Anserini tuned).",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=_INDEXER_THREADS,
        metavar="N",
        help=f"Indexing threads (default: {_INDEXER_THREADS}).",
    )
    parser.add_argument(
        "--skip-export",
        action="store_true",
        help="Skip JSONL export (use existing --jsonl file).",
    )
    parser.add_argument(
        "--skip-index",
        action="store_true",
        help="Skip index build (use existing --index-dir).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Full pipeline: export → index → eval → save results.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # -----------------------------------------------------------------------
    # Phase 1: Export chunks to JSONL
    # -----------------------------------------------------------------------
    if not args.skip_export:
        if not args.db:
            parser.error(
                "--db is required (or set $NOX_DB_PATH) unless --skip-export is used."
            )
        logger.info("=== Phase 1: Export chunks to JSONL ===")
        n_chunks = export_chunks_to_jsonl(
            db_path=args.db,
            output_jsonl=args.jsonl,
        )
        logger.info("Phase 1 done — %d chunks exported", n_chunks)
    else:
        logger.info("=== Phase 1: SKIPPED (--skip-export) ===")

    # -----------------------------------------------------------------------
    # Phase 2: Build Pyserini index
    # -----------------------------------------------------------------------
    if not args.skip_index:
        logger.info("=== Phase 2: Build Pyserini BM25 index ===")
        build_pyserini_index(
            jsonl_path=args.jsonl,
            index_dir=args.index_dir,
            threads=args.threads,
        )
        logger.info("Phase 2 done — index at %s", args.index_dir)
    else:
        logger.info("=== Phase 2: SKIPPED (--skip-index) ===")

    # -----------------------------------------------------------------------
    # Phase 3: Run eval
    # -----------------------------------------------------------------------
    logger.info("=== Phase 3: Run eval (%d results per query) ===", args.k)
    with BM25Searcher(
        index_dir=args.index_dir,
        bm25_k1=args.bm25_k1,
        bm25_b=args.bm25_b,
    ) as searcher:
        aggregates = run_eval(
            searcher=searcher,
            queries_jsonl=args.queries,
            output_results_jsonl=args.output,
            k=args.k,
        )

    logger.info("=== Pipeline complete ===")
    logger.info("Results: %s", args.output)
    logger.info(
        "Aggregate metrics: nDCG@10=%.4f | MRR=%.4f | Recall@10=%.4f | Prec@5=%.4f",
        aggregates["ndcg_at_10"],
        aggregates["mrr"],
        aggregates["recall_at_10"],
        aggregates["precision_at_5"],
    )
    logger.info(
        "To import into nox-mem eval harness:\n"
        "  nox-mem eval-import --source bm25-baseline --variant bm25-pyserini "
        "--file %s",
        args.output,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
