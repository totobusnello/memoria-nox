"""BEIR TREC-COVID Adapter for nox-mem External Corpus Generalization (E4).

WHAT THIS SCRIPT DOES
---------------------
This adapter bridges the BEIR TREC-COVID benchmark and the nox-mem hybrid
retrieval system to produce the "External corpus generalization" results
required for paper §5.3.  The pipeline has five stages:

  1. Download TREC-COVID from HuggingFace / BEIR S3 (corpus + queries + qrels).
  2. Convert the 171K-abstract corpus to a nox-mem-compatible SQLite DB
     (TEMP DB, completely separate from the production nox-mem.db).
  3. Convert BEIR queries + qrels to the eval harness format expected by
     ``nox-mem eval-import``.
  4. Run nox-mem search against the TEMP DB via the HTTP API on port 18802
     (requires the nox-mem API process running with NOX_DB_PATH overridden).
  5. Compute nDCG@10 / MRR / Recall@10 / Precision@5 across all 50 TREC-COVID
     queries and produce a cross-system comparison table (BM25 / BGE-M3 / nox).

TREC-COVID specifics
- Dataset: BEIR v1.0.0 / TREC-COVID final (Voorhees et al., 2021, SIGIR Forum)
- HuggingFace: ``BeIR/trec-covid`` (corpus shard ~450 MB compressed)
- Corpus: 171,332 COVID-19 biomedical abstracts (title + abstract)
- Queries: 50 official TREC-COVID topics (Round 5, final pooled qrels)
- Qrels: 3-grade relevance (0=not relevant, 1=partially relevant, 2=highly
  relevant); this script maps grades >= 1 to binary relevant for nDCG/Recall
  consistent with standard BEIR evaluation protocol.
- BEIR commit used: 2.0.0 (pip install beir==2.0.0)

Subset strategy (recommended for CPU dev)
- Full 171K corpus ingest + embed takes ~8-10 hours on CPU.
- Recommended subset: "relevant-seeded" — include all documents with at least
  one qrel judgment (qrels cover ~69K unique doc IDs in Round 5) plus a
  random sample to reach a target size (default: 50K).  This preserves all
  positive/negative examples for the 50 queries while cutting embed time to
  ~2-3 hours on CPU.
- BM25 and BGE-M3 baselines MUST run on the SAME subset for fairness.
- The subset seed is fixed (SEED=42) for reproducibility.
- Pass --full-corpus to disable subsetting and run all 171K docs.

HOW TO RUN
----------
# 0. Prerequisites (separate venv from nox-mem TypeScript toolchain):
python3.11 -m venv /tmp/beir-adapter-venv
source /tmp/beir-adapter-venv/bin/activate
pip install "beir==2.0.0" "datasets>=2.19" "requests>=2.31"

# 1. Download TREC-COVID corpus (~5-10 min first time, cached afterward):
python beir_trec_covid_adapter.py download --cache-dir ~/.cache/beir
# Output: ~/.cache/beir/trec-covid/{corpus.jsonl,queries.jsonl,qrels/test.tsv}

# 2. Build TEMP SQLite DB from BEIR corpus (subset 50K, ~2 min):
python beir_trec_covid_adapter.py build-db \
    --corpus ~/.cache/beir/trec-covid/corpus.jsonl \
    --qrels  ~/.cache/beir/trec-covid/qrels/test.tsv \
    --db     /tmp/nox-mem-trec-covid.db \
    --subset-size 50000
# Output: /tmp/nox-mem-trec-covid.db  (~2-5 min)

# 3. Convert queries + qrels to eval harness format:
python beir_trec_covid_adapter.py convert-queries \
    --queries ~/.cache/beir/trec-covid/queries.jsonl \
    --qrels   ~/.cache/beir/trec-covid/qrels/test.tsv \
    --db      /tmp/nox-mem-trec-covid.db \
    --output  /tmp/trec-covid-eval-queries.jsonl
# Output: /tmp/trec-covid-eval-queries.jsonl  (50 lines, one per query)

# 4. Start nox-mem API pointing at TEMP DB (in a separate shell):
#    NOX_DB_PATH=/tmp/nox-mem-trec-covid.db node dist/index.js serve
#    (after vectorizing all chunks in the TEMP DB via nox-mem vectorize)

# 5. Run evaluation (all 50 queries → per-query JSONL):
python beir_trec_covid_adapter.py eval \
    --queries /tmp/trec-covid-eval-queries.jsonl \
    --output  /tmp/corpus-beir-results.jsonl \
    --api-url http://localhost:18802
# Output: /tmp/corpus-beir-results.jsonl  (<30 s once API is up)

# 6. Compare all three systems:
python beir_trec_covid_adapter.py compare \
    --nox  /tmp/corpus-beir-results.jsonl \
    --bm25 /tmp/baselines-bm25-beir.jsonl \
    --bge  /tmp/baselines-bge-beir.jsonl \
    --csv  /tmp/baselines-comparison-beir.csv
# Output: /tmp/baselines-comparison-beir.csv + printed markdown table

EXPECTED OUTPUTS
----------------
- /tmp/corpus-beir-results.jsonl          — nox-mem ranked results (50 lines × k rows)
- /tmp/baselines-bm25-beir.jsonl          — BM25 results (same subset, bm25_baseline.py)
- /tmp/baselines-bge-beir.jsonl           — BGE-M3 results (same subset, bge_baseline.py)
- /tmp/baselines-comparison-beir.csv      — cross-system comparison table

INTEGRATION WITH PAPER §5.3 — "Cross-corpus generalization"
------------------------------------------------------------
The CSV produced by the ``compare`` sub-command maps directly to Table 3:

  System          | nDCG@10 | MRR   | R@10  | P@5
  BM25 (Pyserini) |  ?.???  | ?.??? | ?.??? | ?.???
  BGE-M3          |  ?.???  | ?.??? | ?.??? | ?.???
  NOX-Supermem    |  ?.???  | ?.??? | ?.??? | ?.???

Copy the CSV row for "Corpus B (BEIR-COVID)" into the multi-corpus table.
The citation in §5.3 should read: "n=50 TREC-COVID Round 5 topics, binary
relevance (grade>=1), identical 50K-doc subset across all systems, seed=42."
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import os
import random
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
logger = logging.getLogger("beir_trec_covid_adapter")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# TREC-COVID Round 5 (Voorhees et al., 2021) — canonical BEIR split
_TREC_COVID_DATASET_NAME = "BeIR/trec-covid"
_TREC_COVID_EXPECTED_QUERIES = 50
_TREC_COVID_VERSION = "1.0.0"  # BEIR version tag; pin for reproducibility

# Schema mapping: BEIR doc _id → nox-mem chunks.doc_id
# chunk_text = title + "\n\n" + text  (mirrors how nox-mem stores entity text)
# Design rationale:
#   - Concatenation mirrors the nox-mem internal convention (frontmatter/compiled
#     sections separated by blank line).
#   - doc_id uses the BEIR string _id stored in a separate TEXT column so that
#     qrel lookups can use the original identifier without integer conversion.
#   - The numeric INTEGER PK (id) is auto-assigned by SQLite (ROWID alias) for
#     BM25 baseline compatibility (bm25_baseline.py expects integer chunk ids).
_CHUNK_TEXT_SEPARATOR = "\n\n"

# Relevant = qrel grade >= 1  (binary mapping per BEIR evaluation protocol)
_RELEVANCE_THRESHOLD = 1

# Subset defaults — see module docstring for rationale
_DEFAULT_SUBSET_SIZE = 50_000
_DEFAULT_SEED = 42

# HTTP API
_DEFAULT_API_URL = "http://localhost:18802"
_DEFAULT_TEMP_DB = "/tmp/nox-mem-trec-covid.db"
_DEFAULT_CACHE_DIR = str(Path.home() / ".cache" / "beir")
_DEFAULT_K = 10

# nox-mem API search endpoint payload keys
_NOX_SEARCH_PAYLOAD_QUERY = "query"
_NOX_SEARCH_PAYLOAD_LIMIT = "limit"
_NOX_SEARCH_PAYLOAD_HYBRID = "hybrid"


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

QrelMap = dict[str, dict[str, int]]  # {query_id: {doc_id: grade}}
EvalQuery = dict[str, Any]  # {query_id, query_text, expected_doc_ids}
SearchHit = tuple[str, float]  # (doc_id, score)


# ---------------------------------------------------------------------------
# Helper: BEIR lazy import guard
# ---------------------------------------------------------------------------


def _require_beir() -> Any:
    """Import and return the ``beir`` module, raising ImportError with install hint.

    Returns:
        The imported ``beir`` package object.

    Raises:
        ImportError: If ``beir`` is not installed in the active environment.
    """
    try:
        import beir  # type: ignore[import-untyped]
        return beir
    except ImportError as exc:
        raise ImportError(
            "beir is not installed. Run:\n"
            "  pip install 'beir==2.0.0' 'datasets>=2.19'"
        ) from exc


# ---------------------------------------------------------------------------
# Stage 1 — Download corpus
# ---------------------------------------------------------------------------


def download_corpus(
    output_dir: str | Path | None = None,
) -> tuple[Path, Path, Path]:
    """Download the BEIR TREC-COVID dataset to a local cache directory.

    Uses ``beir.datasets.download_and_unzip`` (or the HuggingFace Datasets
    backend available in beir>=1.0.1) to fetch:

    - ``corpus.jsonl``   — 171K biomedical abstracts
    - ``queries.jsonl``  — 50 TREC-COVID topics
    - ``qrels/test.tsv`` — Round 5 relevance judgments

    The download is idempotent: if the three files already exist on disk,
    this function returns their paths without re-downloading.

    Args:
        output_dir: Parent directory for the dataset.  The TREC-COVID files
            are placed in ``output_dir/trec-covid/``.  Defaults to
            ``~/.cache/beir``.

    Returns:
        Tuple of ``(corpus_path, queries_path, qrels_path)`` as
        :class:`pathlib.Path` objects, all pointing to existing files.

    Raises:
        ImportError: If ``beir`` is not installed.
        RuntimeError: If the download fails or the expected files are not
            produced after download.
    """
    if output_dir is None:
        output_dir = Path(_DEFAULT_CACHE_DIR)
    output_dir = Path(output_dir)

    trec_dir = output_dir / "trec-covid"
    corpus_path = trec_dir / "corpus.jsonl"
    queries_path = trec_dir / "queries.jsonl"
    qrels_path = trec_dir / "qrels" / "test.tsv"

    # Idempotency check — all three files must exist
    if corpus_path.exists() and queries_path.exists() and qrels_path.exists():
        logger.info(
            "TREC-COVID cache hit — skipping download (dir: %s)", trec_dir
        )
        return corpus_path, queries_path, qrels_path

    beir = _require_beir()
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Downloading BEIR TREC-COVID (%s) → %s …", _TREC_COVID_VERSION, output_dir
    )
    logger.info(
        "Expected size: ~450 MB compressed.  First download may take 5-15 min."
    )

    # beir 2.0.0 exposes download via beir.util.download_and_unzip
    # Falls back to HuggingFace datasets backend internally when available.
    try:
        from beir.datasets.data_loader import GenericDataLoader  # type: ignore[import]
        url = (
            "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/"
            "trec-covid.zip"
        )
        data_path = beir.util.download_and_unzip(url, str(output_dir))
        logger.info("Downloaded and extracted to: %s", data_path)
    except Exception as exc:
        raise RuntimeError(
            f"BEIR download failed: {exc}\n"
            "Alternative: download manually from "
            "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/"
            "trec-covid.zip and unzip to ~/.cache/beir/"
        ) from exc

    # Validate expected files exist after download
    for p, label in [
        (corpus_path, "corpus.jsonl"),
        (queries_path, "queries.jsonl"),
        (qrels_path, "qrels/test.tsv"),
    ]:
        if not p.exists():
            raise RuntimeError(
                f"Expected file not found after download: {p}\n"
                f"Check that the zip extracted to {trec_dir}"
            )

    logger.info("TREC-COVID download complete.")
    logger.info("  corpus  → %s", corpus_path)
    logger.info("  queries → %s", queries_path)
    logger.info("  qrels   → %s", qrels_path)
    return corpus_path, queries_path, qrels_path


# ---------------------------------------------------------------------------
# Stage 2 — Build TEMP SQLite DB
# ---------------------------------------------------------------------------


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Yield parsed JSON objects from a JSONL file line by line.

    Args:
        path: Path to a UTF-8 JSONL file.

    Yields:
        Parsed dict for each non-empty line.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"JSONL file not found: {path}")
    with path.open(encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                yield json.loads(raw)
            except json.JSONDecodeError as exc:
                logger.warning(
                    "Skipping malformed JSON at %s line %d: %s", path, line_no, exc
                )


def _load_qrels(qrels_path: Path) -> QrelMap:
    """Load BEIR qrels TSV into an in-memory dict.

    Handles two TSV layouts automatically:

    - **TREC standard (4-column, no header):**
        ``query_id  0  doc_id  grade``
    - **BEIR 3-column (with header line):**
        ``query-id  corpus-id  score``
        First line is skipped when the grade column is non-numeric.

    The BEIR TREC-COVID download produces the 3-column format with a header.
    Bug fix (2026-05-04): original code expected 4 columns, silently loading
    0 judgments from BEIR's 3-column qrels.

    Args:
        qrels_path: Path to ``qrels/test.tsv``.

    Returns:
        Nested dict ``{query_id: {doc_id: grade}}`` where grade is an int
        (0 = not relevant, 1 = partially relevant, 2 = highly relevant).

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the grade column is not an integer.
    """
    if not qrels_path.exists():
        raise FileNotFoundError(f"Qrels file not found: {qrels_path}")

    qrels: QrelMap = {}
    with qrels_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\r\n")
            parts = line.split("\t")
            if len(parts) == 4:
                # TREC standard: query_id  iteration  doc_id  grade
                query_id, _, doc_id, grade_str = parts
            elif len(parts) == 3:
                # BEIR 3-column: query-id  corpus-id  score (header or data)
                query_id, doc_id, grade_str = parts
            else:
                continue
            try:
                grade = int(grade_str)
            except ValueError:
                # Skip non-numeric grade — covers the header row "score"
                logger.debug(
                    "Skipping non-numeric grade '%s' for query=%s (likely header)",
                    grade_str, query_id,
                )
                continue
            qrels.setdefault(query_id, {})[doc_id] = grade

    logger.info(
        "Loaded qrels: %d queries, %d total judgments",
        len(qrels),
        sum(len(v) for v in qrels.values()),
    )
    return qrels


def _select_doc_subset(
    corpus_path: Path,
    qrels: QrelMap,
    subset_size: int,
    seed: int,
) -> set[str]:
    """Select a reproducible subset of doc IDs for evaluation.

    Strategy (see module docstring "Subset strategy"):
    1. Include ALL doc IDs that appear in at least one qrel (guaranteed recall).
    2. Fill remaining slots with uniformly sampled docs from the corpus.
    3. Total capped at ``subset_size``.

    This ensures every positive/negative example in the 50-query qrel pool
    is present in the subset, which is a hard requirement for fair eval.

    Args:
        corpus_path: Path to the BEIR corpus.jsonl.
        qrels: Loaded qrel map (from :func:`_load_qrels`).
        subset_size: Target number of documents in the subset.
        seed: Random seed for the uniform sample (fixed for reproducibility).

    Returns:
        Set of doc_id strings to include in the TEMP DB.
    """
    # All doc IDs that appear in any qrel (judges touched them)
    judged_doc_ids: set[str] = {
        doc_id
        for doc_judgments in qrels.values()
        for doc_id in doc_judgments
    }
    logger.info("Judged docs (qrel coverage): %d", len(judged_doc_ids))

    remaining_slots = subset_size - len(judged_doc_ids)
    if remaining_slots <= 0:
        logger.info(
            "Judged docs (%d) >= subset_size (%d) — using all judged docs only.",
            len(judged_doc_ids), subset_size,
        )
        return judged_doc_ids

    # Sample random docs from corpus to fill remaining slots
    logger.info(
        "Sampling %d additional random docs from corpus (seed=%d) …",
        remaining_slots, seed,
    )
    rng = random.Random(seed)
    all_corpus_ids: list[str] = []
    for doc in _iter_jsonl(corpus_path):
        doc_id = doc.get("_id", "")
        if doc_id and doc_id not in judged_doc_ids:
            all_corpus_ids.append(doc_id)

    random_sample = set(rng.sample(all_corpus_ids, min(remaining_slots, len(all_corpus_ids))))
    selected = judged_doc_ids | random_sample
    logger.info(
        "Final subset: %d docs (%d judged + %d random)",
        len(selected), len(judged_doc_ids), len(random_sample),
    )
    return selected


def corpus_to_chunks_db(
    corpus_jsonl: str | Path,
    target_db_path: str | Path | None = None,
    qrels_path: str | Path | None = None,
    subset_size: int = _DEFAULT_SUBSET_SIZE,
    seed: int = _DEFAULT_SEED,
    full_corpus: bool = False,
) -> Path:
    """Convert BEIR TREC-COVID corpus to a nox-mem–compatible SQLite TEMP DB.

    Schema mapping:
    - BEIR ``_id``    → ``chunks.doc_id`` (TEXT, stores original BEIR string ID)
    - BEIR ``title``  → first part of ``chunks.chunk_text``
    - BEIR ``text``   → second part of ``chunks.chunk_text``
    - chunk_text = title + "\\n\\n" + text  (standard nox-mem separator)
    - BEIR ``metadata`` (pmid, publish_time, etc.) → stored as JSON in
      ``chunks.source_file`` for provenance; not used in retrieval.

    Idempotency: if the DB already exists and the row count matches the
    corpus subset size (within 5% tolerance), this function returns early
    without recreating the DB.  Pass ``full_corpus=True`` to skip subsetting.

    Args:
        corpus_jsonl: Path to the BEIR corpus.jsonl (171K lines).
        target_db_path: Path for the output SQLite DB.  Defaults to
            ``$BEIR_TEMP_DB`` env var or ``/tmp/nox-mem-trec-covid.db``.
        qrels_path: Path to qrels/test.tsv.  Required when subsetting
            (``full_corpus=False``) to seed the subset with judged docs.
            Ignored when ``full_corpus=True``.
        subset_size: Target number of docs to ingest.  Default 50,000.
            Ignored when ``full_corpus=True``.
        seed: Random seed for subset sampling.  Default 42.
        full_corpus: If True, ingest all 171K docs.  Warning: embedding
            171K docs takes ~8-10 hours on CPU; plan accordingly.

    Returns:
        Path to the created (or existing) SQLite DB file.

    Raises:
        FileNotFoundError: If ``corpus_jsonl`` does not exist.
        ValueError: If subsetting is requested but ``qrels_path`` is None.
        AssertionError: If no documents are written to the DB.
    """
    corpus_path = Path(corpus_jsonl)
    if not corpus_path.exists():
        raise FileNotFoundError(f"Corpus JSONL not found: {corpus_path}")

    if target_db_path is None:
        target_db_path = Path(
            os.environ.get("BEIR_TEMP_DB", _DEFAULT_TEMP_DB)
        )
    db_path = Path(target_db_path)

    # Determine selected doc IDs
    selected_ids: set[str] | None = None
    if not full_corpus:
        if qrels_path is None:
            raise ValueError(
                "qrels_path is required for subset selection. "
                "Pass full_corpus=True to ingest all 171K docs."
            )
        qrels = _load_qrels(Path(qrels_path))
        selected_ids = _select_doc_subset(corpus_path, qrels, subset_size, seed)

    target_count = len(selected_ids) if selected_ids is not None else None

    # Idempotency check
    if db_path.exists():
        try:
            with sqlite3.connect(str(db_path)) as conn_check:
                (existing_count,) = conn_check.execute(
                    "SELECT COUNT(*) FROM chunks"
                ).fetchone()
            # 5% tolerance for floating-point subset size differences
            if target_count is None or abs(existing_count - target_count) <= target_count * 0.05:
                logger.info(
                    "TEMP DB already exists with %d rows — skipping recreate. "
                    "(Pass --force-db to override.)",
                    existing_count,
                )
                return db_path
            else:
                logger.info(
                    "TEMP DB exists but row count %d differs from target %d — recreating.",
                    existing_count, target_count,
                )
        except sqlite3.OperationalError:
            logger.info("TEMP DB exists but has no chunks table — recreating.")

    # Create fresh TEMP DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    logger.info("Creating TEMP DB: %s", db_path)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    # Minimal schema compatible with nox-mem search machinery.
    # doc_id TEXT stores the original BEIR string identifier (_id).
    # source_file TEXT is repurposed to carry JSON metadata for provenance.
    # Fields not used by the BEIR eval (pain, section, retention_days, etc.)
    # are included with their defaults so existing nox-mem SQL queries don't
    # fail with "no such column" errors if run against this DB.
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

        -- FTS5 virtual table expected by nox-mem BM25 path
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            chunk_text,
            content='chunks',
            content_rowid='id'
        );
        """
    )

    count = 0
    batch: list[tuple[str, str, str, int]] = []
    batch_size = 2_000

    for doc in _iter_jsonl(corpus_path):
        doc_id: str = doc.get("_id", "")
        if not doc_id:
            continue
        if selected_ids is not None and doc_id not in selected_ids:
            continue

        title: str = (doc.get("title") or "").strip()
        text: str = (doc.get("text") or "").strip()
        # BEIR doc schema: _id, title, text, metadata (dict)
        # chunk_text concatenation preserves retrievability of title keywords
        chunk_text: str = (
            f"{title}{_CHUNK_TEXT_SEPARATOR}{text}" if title else text
        ).strip()

        if not chunk_text:
            logger.debug("Skipping empty doc %s", doc_id)
            continue

        # Store original metadata as JSON in source_file for provenance;
        # not used in retrieval but useful for debugging false negatives.
        metadata = doc.get("metadata", {})
        source_file = json.dumps(
            {
                "beir_doc_id": doc_id,
                "pmid": metadata.get("pmid", ""),
                "publish_time": metadata.get("publish_time", ""),
                "corpus": "trec-covid",
            },
            ensure_ascii=False,
        )

        batch.append((doc_id, chunk_text, source_file, count))
        count += 1

        if len(batch) >= batch_size:
            conn.executemany(
                "INSERT INTO chunks (doc_id, chunk_text, source_file, chunk_index) "
                "VALUES (?, ?, ?, ?)",
                batch,
            )
            conn.commit()
            logger.info("Inserted %d docs so far…", count)
            batch = []

    if batch:
        conn.executemany(
            "INSERT INTO chunks (doc_id, chunk_text, source_file, chunk_index) "
            "VALUES (?, ?, ?, ?)",
            batch,
        )
        conn.commit()

    # Populate FTS5 index from chunks table
    logger.info("Building FTS5 index on %d docs…", count)
    conn.execute(
        "INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')"
    )
    conn.commit()
    conn.close()

    assert count > 0, (
        f"No documents written to TEMP DB {db_path}. "
        "Check corpus_jsonl path and selected_ids filter."
    )
    logger.info(
        "TEMP DB created: %d docs → %s", count, db_path
    )
    return db_path


# ---------------------------------------------------------------------------
# Stage 3 — Convert queries + qrels to eval harness format
# ---------------------------------------------------------------------------


def queries_to_eval_format(
    queries_jsonl: str | Path,
    qrels_tsv: str | Path,
    output_jsonl: str | Path,
    db_path: str | Path | None = None,
) -> Path:
    """Convert BEIR queries + qrels to the nox-mem eval harness format.

    The eval harness format (one JSON object per line):

    .. code-block:: json

        {
          "query_id": "1",
          "query_text": "coronavirus origin",
          "expected_doc_ids": ["nc3bv23w", "abcde123"],
          "n_relevant": 42
        }

    Key design decisions:
    - ``expected_doc_ids`` uses BEIR string doc IDs (not the auto-increment
      integer PK in chunks.id), because qrels reference BEIR IDs.  The metric
      computation functions in this module resolve to DB integer IDs only when
      calling nox-mem API (which returns chunk integer IDs).
    - Only docs with grade >= ``_RELEVANCE_THRESHOLD`` (1) are listed as
      expected; grade=0 entries are excluded (binary relevance).
    - ``n_relevant`` is included for quick sanity checking.
    - If ``db_path`` is provided, the function also emits ``expected_chunk_ids``
      (integer PKs from the TEMP DB) alongside doc IDs, enabling direct metric
      computation against the nox-mem integer ID namespace.

    Args:
        queries_jsonl: Path to BEIR queries.jsonl.  Each line:
            ``{"_id": "1", "text": "coronavirus origin", "metadata": {}}``.
        qrels_tsv: Path to qrels/test.tsv (TREC format, 4 columns, no header).
        output_jsonl: Destination path for the output eval harness JSONL.
            Parent directory is created if missing.
        db_path: Optional path to the TEMP DB.  When provided, resolves
            BEIR doc_id strings to integer chunk PKs via a DB lookup and
            includes ``expected_chunk_ids`` in each output record.

    Returns:
        Path to the written output JSONL file.

    Raises:
        FileNotFoundError: If ``queries_jsonl`` or ``qrels_tsv`` do not exist.
        AssertionError: If the query count != 50 (TREC-COVID invariant).
    """
    queries_path = Path(queries_jsonl)
    qrels_path_obj = Path(qrels_tsv)
    output_path = Path(output_jsonl)

    if not queries_path.exists():
        raise FileNotFoundError(f"Queries JSONL not found: {queries_path}")
    if not qrels_path_obj.exists():
        raise FileNotFoundError(f"Qrels TSV not found: {qrels_path_obj}")

    # Load qrels
    qrels = _load_qrels(qrels_path_obj)

    # Load queries
    queries: list[dict[str, Any]] = list(_iter_jsonl(queries_path))
    assert len(queries) == _TREC_COVID_EXPECTED_QUERIES, (
        f"Expected {_TREC_COVID_EXPECTED_QUERIES} TREC-COVID queries, "
        f"got {len(queries)}. Verify dataset version is Round 5 final."
    )
    logger.info("Loaded %d queries from %s", len(queries), queries_path)

    # Validate qrels cover all queries
    missing_queries = [
        q["_id"] for q in queries if q.get("_id") not in qrels
    ]
    if missing_queries:
        logger.warning(
            "%d queries have no qrel entries (expected for a few TREC-COVID "
            "topics with zero judgments): %s",
            len(missing_queries), missing_queries[:5],
        )

    # Optional: resolve doc_id → integer chunk PK via TEMP DB
    doc_id_to_chunk_id: dict[str, int] = {}
    if db_path is not None:
        db_p = Path(db_path)
        if db_p.exists():
            logger.info(
                "Resolving doc_id → chunk PK from TEMP DB %s …", db_p
            )
            with sqlite3.connect(str(db_p)) as conn:
                rows = conn.execute(
                    "SELECT doc_id, id FROM chunks"
                ).fetchall()
            doc_id_to_chunk_id = {row[0]: row[1] for row in rows}
            logger.info(
                "Resolved %d doc_id → chunk_id mappings", len(doc_id_to_chunk_id)
            )
        else:
            logger.warning(
                "db_path=%s does not exist; skipping chunk ID resolution.", db_p
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    n_written = 0

    with output_path.open("w", encoding="utf-8") as fh:
        for q in queries:
            qid: str = q.get("_id", "")
            query_text: str = q.get("text", "").strip()
            if not qid or not query_text:
                logger.warning("Skipping query with missing _id or text: %s", q)
                continue

            # Binary relevance: include only docs with grade >= threshold
            doc_judgments = qrels.get(qid, {})
            relevant_doc_ids: list[str] = [
                doc_id
                for doc_id, grade in doc_judgments.items()
                if grade >= _RELEVANCE_THRESHOLD
            ]

            record: dict[str, Any] = {
                "query_id": qid,
                "query_text": query_text,
                "expected_doc_ids": relevant_doc_ids,
                "n_relevant": len(relevant_doc_ids),
            }

            # Include integer chunk IDs if TEMP DB was provided
            if doc_id_to_chunk_id:
                expected_chunk_ids = [
                    doc_id_to_chunk_id[did]
                    for did in relevant_doc_ids
                    if did in doc_id_to_chunk_id
                ]
                n_missing = len(relevant_doc_ids) - len(expected_chunk_ids)
                if n_missing > 0:
                    # Docs judged but not in the subset — expected for sampled subset
                    logger.debug(
                        "Query %s: %d relevant docs not in TEMP DB subset "
                        "(likely random sample didn't include them)",
                        qid, n_missing,
                    )
                record["expected_chunk_ids"] = expected_chunk_ids

            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            n_written += 1

    logger.info("Wrote %d eval queries → %s", n_written, output_path)
    assert n_written > 0, "No queries written — check input files."
    return output_path


# ---------------------------------------------------------------------------
# Stage 4 — nox-mem search via HTTP API
# ---------------------------------------------------------------------------


def run_nox_mem_search(
    query_text: str,
    k: int = _DEFAULT_K,
    api_url: str = _DEFAULT_API_URL,
) -> list[SearchHit]:
    """Search nox-mem via the HTTP API and return ranked (doc_id, score) pairs.

    The nox-mem HTTP API must be running on ``api_url`` (default port 18802)
    with ``NOX_DB_PATH`` pointing at the TEMP DB (not the production DB).

    Operational setup (before calling this function):
    1. Vectorize the TEMP DB:
       ``NOX_DB_PATH=/tmp/nox-mem-trec-covid.db nox-mem vectorize --all``
    2. Start the API with TEMP DB:
       ``NOX_DB_PATH=/tmp/nox-mem-trec-covid.db node dist/index.js serve``
    3. Verify health:
       ``curl http://localhost:18802/api/health | jq .vectorCoverage``
       (embedded must equal total before running eval)

    The API response JSON is expected to have a ``results`` array where each
    element contains at minimum ``id`` (int chunk PK) and ``score`` (float).
    Additional fields (``doc_id``, ``chunk_text``, etc.) are passed through.

    The function returns BEIR string doc_ids if the API response carries the
    ``doc_id`` field (set during DB creation), or stringified integer chunk IDs
    as fallback.  Callers should use :func:`evaluate_all` which handles the
    ID namespace reconciliation between nox integer PKs and BEIR string IDs.

    Args:
        query_text: Natural-language search query (English for TREC-COVID).
        k: Number of results to retrieve.  Must be >= 10 for nDCG@10 to be
            meaningful.  The API ``limit`` param is set to ``k``.
        api_url: Base URL of the nox-mem HTTP API.

    Returns:
        List of ``(doc_id_str, score)`` tuples sorted by score descending,
        length <= k.  ``doc_id_str`` is the BEIR ``_id`` string if the API
        returns ``doc_id``; otherwise the string-cast integer chunk PK.

    Raises:
        RuntimeError: If the HTTP request fails (non-2xx status or timeout).
        ImportError: If ``requests`` is not installed.
    """
    try:
        import requests  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "requests is not installed. Run: pip install requests"
        ) from exc

    payload: dict[str, Any] = {
        _NOX_SEARCH_PAYLOAD_QUERY: query_text,
        _NOX_SEARCH_PAYLOAD_LIMIT: k,
        _NOX_SEARCH_PAYLOAD_HYBRID: True,  # enable hybrid search (BM25 + semantic + RRF)
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
            f"Is the API running at {api_url}?  "
            f"Start with: NOX_DB_PATH=/tmp/nox-mem-trec-covid.db node dist/index.js serve"
        ) from exc

    data: dict[str, Any] = response.json()
    results: list[dict[str, Any]] = data.get("results", [])

    hits: list[SearchHit] = []
    for item in results[:k]:
        # Prefer BEIR string doc_id if API stored it; fall back to integer PK
        doc_id_str: str = str(item.get("doc_id") or item.get("id", ""))
        score: float = float(item.get("score", 0.0))
        if doc_id_str:
            hits.append((doc_id_str, score))

    return hits


# ---------------------------------------------------------------------------
# Metric helpers — binary relevance (matching bm25_baseline.py formulae)
# ---------------------------------------------------------------------------


def _ndcg_at_k(retrieved: list[str], gold: set[str], k: int = 10) -> float:
    """Compute nDCG@k with binary relevance.

    Args:
        retrieved: Ordered list of retrieved doc IDs (rank 1 = index 0).
        gold: Set of relevant doc IDs (qrel grade >= threshold).
        k: Cutoff rank.

    Returns:
        nDCG@k in [0.0, 1.0].  Returns 0.0 if gold is empty.
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


def _mrr(retrieved: list[str], gold: set[str]) -> float:
    """Compute MRR (reciprocal rank of first relevant hit) for a single query.

    Args:
        retrieved: Ordered list of retrieved doc IDs.
        gold: Set of relevant doc IDs.

    Returns:
        Reciprocal rank (1/rank) of first relevant result, or 0.0 if none.
    """
    for rank, doc_id in enumerate(retrieved, start=1):
        if doc_id in gold:
            return 1.0 / rank
    return 0.0


def _recall_at_k(retrieved: list[str], gold: set[str], k: int = 10) -> float:
    """Compute Recall@k.

    Args:
        retrieved: Ordered list of retrieved doc IDs.
        gold: Set of relevant doc IDs.
        k: Cutoff rank.

    Returns:
        Fraction of gold docs found in top-k.  Returns 0.0 if gold is empty.
    """
    if not gold:
        return 0.0
    hits = sum(1 for doc_id in retrieved[:k] if doc_id in gold)
    return hits / len(gold)


def _precision_at_k(retrieved: list[str], gold: set[str], k: int = 5) -> float:
    """Compute Precision@k.

    Args:
        retrieved: Ordered list of retrieved doc IDs.
        gold: Set of relevant doc IDs.
        k: Cutoff rank.

    Returns:
        Fraction of top-k results that are relevant.
    """
    if k == 0:
        return 0.0
    hits = sum(1 for doc_id in retrieved[:k] if doc_id in gold)
    return hits / k


# ---------------------------------------------------------------------------
# Stage 5 — Full evaluation loop
# ---------------------------------------------------------------------------


def evaluate_all(
    eval_queries_jsonl: str | Path,
    output_results_jsonl: str | Path,
    k: int = _DEFAULT_K,
    api_url: str = _DEFAULT_API_URL,
) -> dict[str, float]:
    """Run nox-mem search over all 50 TREC-COVID queries and compute metrics.

    For each query in ``eval_queries_jsonl``:
    1. Call :func:`run_nox_mem_search` to retrieve top-k results.
    2. Reconcile returned doc IDs with BEIR expected doc IDs from qrels.
    3. Compute nDCG@10, MRR, Recall@10, Precision@5.
    4. Write one result record per query to ``output_results_jsonl``.

    ID namespace note: nox-mem returns BEIR string doc IDs directly (stored in
    ``chunks.doc_id`` during TEMP DB creation).  If the API returns integer PKs
    instead, reconciliation falls back to string comparison — callers should
    ensure the TEMP DB was built with :func:`corpus_to_chunks_db`.

    Output format (one JSON per line, compatible with nox-mem eval harness):

    .. code-block:: json

        {
          "query_id": "1",
          "query_text": "coronavirus origin",
          "variant": "nox-hybrid-beir",
          "retrieved_doc_ids": ["nc3bv23w", ...],
          "retrieved_scores": [0.934, ...],
          "ndcg_at_10": 0.712,
          "mrr": 0.800,
          "recall_at_10": 0.241,
          "precision_at_5": 0.600,
          "n_relevant": 57,
          "duration_ms": 143
        }

    Args:
        eval_queries_jsonl: Path to the file produced by
            :func:`queries_to_eval_format`.
        output_results_jsonl: Destination path for per-query result records.
            Parent directory is created if missing.
        k: Number of results to retrieve per query.
        api_url: nox-mem HTTP API base URL.

    Returns:
        Dict with aggregate metrics averaged over all queries:
        ``ndcg_at_10``, ``mrr``, ``recall_at_10``, ``precision_at_5``.

    Raises:
        FileNotFoundError: If ``eval_queries_jsonl`` does not exist.
        AssertionError: If zero queries are evaluated.
    """
    eval_path = Path(eval_queries_jsonl)
    if not eval_path.exists():
        raise FileNotFoundError(f"Eval queries JSONL not found: {eval_path}")

    output_path = Path(output_results_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ndcg_sum = mrr_sum = recall_sum = prec_sum = 0.0
    n_queries = 0

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
            # expected_doc_ids contains BEIR string IDs
            gold: set[str] = set(str(d) for d in q.get("expected_doc_ids", []))

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

            record: dict[str, Any] = {
                "query_id": query_id,
                "query_text": query_text,
                "variant": "nox-hybrid-beir",
                "retrieved_doc_ids": retrieved_ids,
                "retrieved_scores": [round(s, 6) for s in retrieved_scores],
                "ndcg_at_10": round(ndcg, 6),
                "mrr": round(mrr_, 6),
                "recall_at_10": round(recall, 6),
                "precision_at_5": round(prec5, 6),
                "n_relevant": len(gold),
                "duration_ms": duration_ms,
            }
            ofh.write(json.dumps(record, ensure_ascii=False) + "\n")

            if n_queries % 10 == 0:
                logger.info(
                    "Progress: %d/50 queries — nDCG@10=%.3f MRR=%.3f",
                    n_queries, ndcg_sum / n_queries, mrr_sum / n_queries,
                )

    assert n_queries > 0, (
        "No queries evaluated — check eval_queries_jsonl content."
    )

    aggregates: dict[str, float] = {
        "ndcg_at_10": round(ndcg_sum / n_queries, 6),
        "mrr": round(mrr_sum / n_queries, 6),
        "recall_at_10": round(recall_sum / n_queries, 6),
        "precision_at_5": round(prec_sum / n_queries, 6),
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
# Stage 6 — Cross-system comparison table
# ---------------------------------------------------------------------------


def _load_results_jsonl(path: Path, variant_field: str = "variant") -> dict[str, Any]:
    """Load a per-query results JSONL and aggregate metrics.

    Handles two output layouts:
    - Full records (from :func:`evaluate_all`, bm25_baseline.py): one line per
      query with pre-computed ``ndcg_at_10``, ``mrr``, ``recall_at_10``,
      ``precision_at_5``.
    - Ranked records (from bge_baseline.py): one line per rank triplet
      (``query_id``, ``rank``, ``doc_id``, ``score``, ``system``).

    For ranked records, this function re-computes per-query metrics from the
    raw ranked lists using the qrels embedded in the eval queries file.  To
    avoid carrying qrels into this function (which is called without query
    context), it falls back to 0.0 metrics and logs a warning — callers should
    use the aggregated output from bge_baseline.py's eval command instead.

    Args:
        path: Path to the JSONL results file.
        variant_field: Field name for the system variant identifier.

    Returns:
        Dict with keys: ``variant`` (str), ``ndcg_at_10``, ``mrr``,
        ``recall_at_10``, ``precision_at_5`` (all float, averaged over queries),
        ``n_queries`` (int).
    """
    if not path.exists():
        raise FileNotFoundError(f"Results JSONL not found: {path}")

    # Peek at first record to detect layout
    first_record: dict[str, Any] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                first_record = json.loads(line)
                break

    variant: str = (
        first_record.get(variant_field)
        or first_record.get("system")
        or path.stem
    )
    is_per_query = "ndcg_at_10" in first_record

    if is_per_query:
        # Full-record layout: one line per query
        metrics: dict[str, list[float]] = {
            "ndcg_at_10": [],
            "mrr": [],
            "recall_at_10": [],
            "precision_at_5": [],
        }
        with path.open(encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                rec = json.loads(raw)
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
    else:
        # Ranked-record layout: multiple lines per query (rank-level)
        # Cannot recompute metrics without qrels — log warning and return zeros.
        logger.warning(
            "Results file %s uses rank-level layout but no qrels provided "
            "to compare() — metrics will be 0.0.  "
            "Re-run bge_baseline.py eval with --output-metrics or aggregate first.",
            path,
        )
        return {
            "variant": variant,
            "ndcg_at_10": 0.0,
            "mrr": 0.0,
            "recall_at_10": 0.0,
            "precision_at_5": 0.0,
            "n_queries": 0,
        }


def compare_with_baselines(
    nox_results_jsonl: str | Path,
    bm25_results_jsonl: str | Path | None = None,
    bge_results_jsonl: str | Path | None = None,
    output_csv: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Generate a cross-system comparison table for paper §5.3.

    Reads per-query result JSONL files from all available systems, computes
    mean metrics, and outputs both a printed markdown table and an optional CSV.

    The CSV is the canonical artifact fed into the LaTeX table for §5.3.

    Args:
        nox_results_jsonl: Path to nox-mem hybrid results (from
            :func:`evaluate_all`).
        bm25_results_jsonl: Optional path to BM25 baseline results.
        bge_results_jsonl: Optional path to BGE-M3 baseline results.
        output_csv: Optional path to write the comparison CSV.  If None,
            no CSV is written.

    Returns:
        List of per-system metric dicts, each with keys:
        ``variant``, ``ndcg_at_10``, ``mrr``, ``recall_at_10``,
        ``precision_at_5``, ``n_queries``.

    Raises:
        FileNotFoundError: If ``nox_results_jsonl`` does not exist.
    """
    rows: list[dict[str, Any]] = []

    # Always include nox-mem (required)
    nox_path = Path(nox_results_jsonl)
    rows.append(_load_results_jsonl(nox_path))

    # Optional baselines
    if bm25_results_jsonl is not None:
        bm25_path = Path(bm25_results_jsonl)
        if bm25_path.exists():
            rows.append(_load_results_jsonl(bm25_path))
        else:
            logger.warning("BM25 results not found at %s — skipping.", bm25_path)

    if bge_results_jsonl is not None:
        bge_path = Path(bge_results_jsonl)
        if bge_path.exists():
            rows.append(_load_results_jsonl(bge_path))
        else:
            logger.warning("BGE-M3 results not found at %s — skipping.", bge_path)

    # Sort by nDCG@10 descending (best system first)
    rows.sort(key=lambda r: r["ndcg_at_10"], reverse=True)

    # Print markdown table (mirrors paper §5.3 Table 3 format)
    header = f"{'System':<25} | {'nDCG@10':>8} | {'MRR':>8} | {'R@10':>8} | {'P@5':>7} | {'N':>5}"
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)
    for row in rows:
        print(
            f"{row['variant']:<25} | {row['ndcg_at_10']:>8.4f} | "
            f"{row['mrr']:>8.4f} | {row['recall_at_10']:>8.4f} | "
            f"{row['precision_at_5']:>7.4f} | {row['n_queries']:>5}"
        )
    print(sep)

    # Write CSV
    if output_csv is not None:
        csv_path = Path(output_csv)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "variant", "ndcg_at_10", "mrr", "recall_at_10", "precision_at_5",
            "n_queries",
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as csvf:
            writer = csv.DictWriter(csvf, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        logger.info("Comparison CSV written → %s", csv_path)

    return rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for all sub-commands.

    Returns:
        Configured :class:`argparse.ArgumentParser` with sub-commands:
        ``download``, ``build-db``, ``convert-queries``, ``eval``,
        ``compare``, and ``full`` (end-to-end pipeline).
    """
    parser = argparse.ArgumentParser(
        prog="beir_trec_covid_adapter",
        description=(
            "BEIR TREC-COVID adapter for nox-mem external corpus evaluation (E4). "
            "Run 'download → build-db → convert-queries → [vectorize+serve] → "
            "eval → compare' or use the 'full' sub-command for steps 1-3."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ---- download -----------------------------------------------------------
    dl = sub.add_parser(
        "download",
        help="Download TREC-COVID corpus from BEIR/HuggingFace.",
    )
    dl.add_argument(
        "--cache-dir",
        default=_DEFAULT_CACHE_DIR,
        metavar="DIR",
        help=f"Cache directory (default: {_DEFAULT_CACHE_DIR}).",
    )

    # ---- build-db -----------------------------------------------------------
    db_cmd = sub.add_parser(
        "build-db",
        help="Convert BEIR corpus.jsonl to nox-mem TEMP SQLite DB.",
    )
    db_cmd.add_argument(
        "--corpus",
        required=True,
        metavar="PATH",
        help="Path to corpus.jsonl (from 'download' step).",
    )
    db_cmd.add_argument(
        "--qrels",
        metavar="PATH",
        help="Path to qrels/test.tsv (required for subset selection).",
    )
    db_cmd.add_argument(
        "--db",
        default=os.environ.get("BEIR_TEMP_DB", _DEFAULT_TEMP_DB),
        metavar="PATH",
        help=f"Output SQLite DB path (default: {_DEFAULT_TEMP_DB} or $BEIR_TEMP_DB).",
    )
    db_cmd.add_argument(
        "--subset-size",
        type=int,
        default=_DEFAULT_SUBSET_SIZE,
        metavar="N",
        help=f"Target subset size in docs (default: {_DEFAULT_SUBSET_SIZE}).",
    )
    db_cmd.add_argument(
        "--seed",
        type=int,
        default=_DEFAULT_SEED,
        metavar="N",
        help=f"Random seed for subset sampling (default: {_DEFAULT_SEED}).",
    )
    db_cmd.add_argument(
        "--full-corpus",
        action="store_true",
        help="Ingest all 171K docs (ignores --subset-size; ~8-10 h on CPU).",
    )

    # ---- convert-queries ----------------------------------------------------
    cq = sub.add_parser(
        "convert-queries",
        help="Convert BEIR queries + qrels to nox-mem eval harness format.",
    )
    cq.add_argument(
        "--queries",
        required=True,
        metavar="PATH",
        help="Path to queries.jsonl.",
    )
    cq.add_argument(
        "--qrels",
        required=True,
        metavar="PATH",
        help="Path to qrels/test.tsv.",
    )
    cq.add_argument(
        "--db",
        default=os.environ.get("BEIR_TEMP_DB", _DEFAULT_TEMP_DB),
        metavar="PATH",
        help="Optional TEMP DB for chunk PK resolution.",
    )
    cq.add_argument(
        "--output",
        default="/tmp/trec-covid-eval-queries.jsonl",
        metavar="PATH",
        help="Output eval queries JSONL (default: /tmp/trec-covid-eval-queries.jsonl).",
    )

    # ---- eval ---------------------------------------------------------------
    ev = sub.add_parser(
        "eval",
        help="Run nox-mem search over all 50 queries and compute metrics.",
    )
    ev.add_argument(
        "--queries",
        required=True,
        metavar="PATH",
        help="Path to eval queries JSONL (from 'convert-queries' step).",
    )
    ev.add_argument(
        "--output",
        default="/tmp/corpus-beir-results.jsonl",
        metavar="PATH",
        help="Output results JSONL (default: /tmp/corpus-beir-results.jsonl).",
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
        help="Generate cross-system comparison table for paper §5.3.",
    )
    cmp.add_argument(
        "--nox",
        required=True,
        metavar="PATH",
        help="nox-mem results JSONL (from 'eval' step).",
    )
    cmp.add_argument(
        "--bm25",
        metavar="PATH",
        help="BM25 results JSONL (optional; from bm25_baseline.py).",
    )
    cmp.add_argument(
        "--bge",
        metavar="PATH",
        help="BGE-M3 results JSONL (optional; from bge_baseline.py).",
    )
    cmp.add_argument(
        "--csv",
        metavar="PATH",
        help="Optional output CSV path.",
    )

    # ---- full (end-to-end steps 1-3) ----------------------------------------
    fl = sub.add_parser(
        "full",
        help=(
            "End-to-end: download → build-db → convert-queries.  "
            "Does NOT run eval (requires nox-mem API running manually)."
        ),
    )
    fl.add_argument(
        "--cache-dir",
        default=_DEFAULT_CACHE_DIR,
        metavar="DIR",
        help=f"BEIR cache directory (default: {_DEFAULT_CACHE_DIR}).",
    )
    fl.add_argument(
        "--db",
        default=os.environ.get("BEIR_TEMP_DB", _DEFAULT_TEMP_DB),
        metavar="PATH",
        help=f"Output TEMP DB path (default: {_DEFAULT_TEMP_DB}).",
    )
    fl.add_argument(
        "--queries-output",
        default="/tmp/trec-covid-eval-queries.jsonl",
        metavar="PATH",
        help="Output eval queries JSONL (default: /tmp/trec-covid-eval-queries.jsonl).",
    )
    fl.add_argument(
        "--subset-size",
        type=int,
        default=_DEFAULT_SUBSET_SIZE,
        metavar="N",
        help=f"Subset size (default: {_DEFAULT_SUBSET_SIZE}).",
    )
    fl.add_argument(
        "--full-corpus",
        action="store_true",
        help="Ingest all 171K docs instead of subset.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the BEIR TREC-COVID adapter CLI.

    Args:
        argv: Argument list (defaults to sys.argv[1:] when None).

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "download":
            corpus, queries, qrels = download_corpus(output_dir=args.cache_dir)
            print(f"corpus:  {corpus}")
            print(f"queries: {queries}")
            print(f"qrels:   {qrels}")

        elif args.command == "build-db":
            db_path = corpus_to_chunks_db(
                corpus_jsonl=args.corpus,
                target_db_path=args.db,
                qrels_path=args.qrels,
                subset_size=args.subset_size,
                seed=args.seed,
                full_corpus=args.full_corpus,
            )
            print(f"TEMP DB: {db_path}")
            print(
                "\nNext step: vectorize the TEMP DB, then start nox-mem API:\n"
                f"  NOX_DB_PATH={db_path} nox-mem vectorize --all\n"
                f"  NOX_DB_PATH={db_path} node dist/index.js serve\n"
                f"  curl http://localhost:18802/api/health | jq .vectorCoverage"
            )

        elif args.command == "convert-queries":
            out = queries_to_eval_format(
                queries_jsonl=args.queries,
                qrels_tsv=args.qrels,
                output_jsonl=args.output,
                db_path=args.db if Path(args.db).exists() else None,
            )
            print(f"Eval queries: {out}")

        elif args.command == "eval":
            aggregates = evaluate_all(
                eval_queries_jsonl=args.queries,
                output_results_jsonl=args.output,
                k=args.k,
                api_url=args.api_url,
            )
            print("\n=== AGGREGATE METRICS (nox-mem hybrid, BEIR TREC-COVID) ===")
            for metric, value in aggregates.items():
                print(f"  {metric:<20} {value:.4f}")

        elif args.command == "compare":
            rows = compare_with_baselines(
                nox_results_jsonl=args.nox,
                bm25_results_jsonl=args.bm25,
                bge_results_jsonl=args.bge,
                output_csv=args.csv,
            )
            _ = rows  # result already printed by compare_with_baselines

        elif args.command == "full":
            logger.info("=== Phase 1: Download TREC-COVID ===")
            corpus_path, queries_path, qrels_path = download_corpus(
                output_dir=args.cache_dir
            )

            logger.info("=== Phase 2: Build TEMP DB ===")
            db_path = corpus_to_chunks_db(
                corpus_jsonl=corpus_path,
                target_db_path=args.db,
                qrels_path=qrels_path,
                subset_size=args.subset_size,
                full_corpus=args.full_corpus,
            )

            logger.info("=== Phase 3: Convert queries + qrels ===")
            queries_out = queries_to_eval_format(
                queries_jsonl=queries_path,
                qrels_tsv=qrels_path,
                output_jsonl=args.queries_output,
                db_path=db_path,
            )

            print("\n=== Phases 1-3 complete ===")
            print(f"TEMP DB:      {db_path}")
            print(f"Eval queries: {queries_out}")
            print("\nManual steps before running 'eval':")
            print(
                f"  # 1. Vectorize (estimated ~2-3 h on CPU for {args.subset_size:,} docs):\n"
                f"  NOX_DB_PATH={db_path} nox-mem vectorize --all\n"
                f"\n  # 2. Start API (separate shell):\n"
                f"  NOX_DB_PATH={db_path} node dist/index.js serve\n"
                f"\n  # 3. Verify health:\n"
                f"  curl http://localhost:18802/api/health | jq .vectorCoverage\n"
                f"\n  # 4. Run eval:\n"
                f"  python beir_trec_covid_adapter.py eval \\\n"
                f"    --queries {queries_out} \\\n"
                f"    --output /tmp/corpus-beir-results.jsonl"
            )

    except (FileNotFoundError, ValueError, RuntimeError, ImportError) as exc:
        logger.error("%s: %s", type(exc).__name__, exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
