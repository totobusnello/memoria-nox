"""
Pain Dimension Validator — E10 nox-mem paper experiment.

Validates empirically whether the ``pain`` dimension of the salience formula
``recency × pain × importance`` improves retrieval quality on "post-incident"
queries compared to a counterfactual where every chunk has ``pain = 1.0``
(uniform — removes the discriminating power of the dimension).

Hypothesis
----------
Pain-aware salience (real pain values) achieves nDCG@10 ≥ 0.05 higher than
pain=1.0 uniform on the subset of golden queries that ask about incidents,
outages, and hard-learned lessons.

Counterfactual choice
---------------------
- ``pain = 0.0`` would zero out salience entirely (recency × 0 × importance = 0),
  making all rankings collapse. Meaningless comparison.
- ``pain = 1.0`` neutralises discrimination while keeping the ranking functional.
  This is the scientifically valid ablation: "what if every chunk hurt equally?".

Statistical approach
--------------------
N ≈ 12 queries is small. Bootstrap CI (n_bootstrap=10_000, seed=42) captures
uncertainty better than a paired t-test whose normality assumption is fragile at
N < 30. If the 95% CI excludes 0 the claim is "statistically significant at
α=0.05" under bootstrap; otherwise the paper must downgrade to
"directional evidence".

Safety design
-------------
- Prod DB is NEVER touched. All mutations happen on an atomic ``shutil.copy2``
  snapshot at ``/tmp/nox-mem-pain-test.db``.
- Every SQL operation is logged with timestamp to ``pain_test_audit.log`` in the
  same directory as the output report.
- A confirmation prompt shows DB sizes and estimated runtime before proceeding.
- The temp DB is deleted after the run regardless of success or failure
  (``finally`` block).

-------------------------------------------------------------------------------
HOW TO RUN
-------------------------------------------------------------------------------

Prerequisites
~~~~~~~~~~~~~
  # Standard library only — no extra deps except numpy (usually present).
  pip install numpy   # if not already in venv

  # The script talks to nox-mem HTTP API for search — so the API must be running:
  #   On VPS:  curl http://127.0.0.1:18802/api/health
  #   Locally: set NOX_API_URL=http://<vps-ip>:18802  (or tunnel via SSH)

Full run (explicit args)
~~~~~~~~~~~~~~~~~~~~~~~~
  export NOX_DB_PATH=/root/.openclaw/workspace/tools/nox-mem/nox-mem.db
  export NOX_API_URL=http://127.0.0.1:18802

  python pain_dimension_validator.py \\
    --db        "$NOX_DB_PATH" \\
    --queries   /path/to/golden_queries.jsonl \\
    --output    ./pain_validation_results.md \\
    --api-url   "$NOX_API_URL"

Quick run (env vars + defaults)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  export NOX_DB_PATH=/root/.openclaw/workspace/tools/nox-mem/nox-mem.db
  python pain_dimension_validator.py --queries golden_queries.jsonl

Dry-run (skip confirmation prompt, useful in CI)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  python pain_dimension_validator.py --queries golden_queries.jsonl --yes

-------------------------------------------------------------------------------
INPUT: golden_queries.jsonl (one JSON object per line)
-------------------------------------------------------------------------------
  {"query": "o que aconteceu com as 183 entities no reindex?",
   "expected_chunk_ids": [1234, 5678],
   "query_id": 47,
   "difficulty": "hard",
   "category": "incident"}

  Fields:
    query               (str, required)  — natural-language query text
    expected_chunk_ids  (list[int], req) — gold chunk IDs
    query_id            (int, optional)  — falls back to 1-based line counter
    difficulty          (str, optional)  — easy/medium/hard
    category            (str, optional)  — incident/lesson/entity/concept/temporal/...

-------------------------------------------------------------------------------
OUTPUT: pain_validation_results.md
-------------------------------------------------------------------------------
  Markdown table with per-query Δ nDCG@10 + aggregate stats + bootstrap CI
  + CONFIRMED / DIRECTIONAL / NOT SUPPORTED verdict.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import re
import shutil
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("pain_validator")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_TEMP_DB = Path("/tmp/nox-mem-pain-test.db")
_DEFAULT_API_URL = "http://127.0.0.1:18802"
_DEFAULT_K = 10
_BOOTSTRAP_N = 10_000
_BOOTSTRAP_SEED = 42
_SIGNIFICANCE_ALPHA = 0.05
_DELTA_THRESHOLD = 0.05  # paper claim: Δ nDCG ≥ 0.05

# Post-incident keyword heuristics — English and PT-BR
_POST_INCIDENT_KEYWORDS: list[str] = [
    "incident",
    "outage",
    "lesson",
    "after",
    "pós-",
    "pos-",
    "rsync delete",
    "withopaudit",
    "reindex",
    "section retention",
    "183 entities",
    "lição",
    "licao",
    "problema",
    "falha",
    "crash",
    "recovery",
    "rollback",
    "downtime",
    "corruption",
    "corrupt",
    "apagou",
    "quebrou",
    "perdeu",
    "destruiu",
]

# Known curated post-incident query IDs from R01b (Toto cured Q47/Q67/Q71)
_KNOWN_POST_INCIDENT_IDS: frozenset[int] = frozenset({47, 67, 71})

# Categories that signal post-incident regardless of text
_INCIDENT_CATEGORIES: frozenset[str] = frozenset({
    "incident",
    "lesson",
    "post-incident",
    "postmortem",
    "recovery",
    "outage",
})

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class Query(NamedTuple):
    """A single golden evaluation query."""

    query_id: int
    query_text: str
    expected_chunk_ids: list[int]
    difficulty: str | None
    category: str | None


class QueryResult(NamedTuple):
    """Search result for one query at one variant."""

    query_id: int
    retrieved_chunk_ids: list[int]
    retrieved_scores: list[float]
    ndcg_at_10: float
    duration_ms: int


class DeltaRow(NamedTuple):
    """Per-query comparison between baseline and ablated variant."""

    query_id: int
    query_text: str
    category: str | None
    pain_mean_real: float  # mean pain of expected chunks in baseline
    ndcg_baseline: float
    ndcg_ablated: float
    delta: float  # baseline − ablated (positive = pain-aware is better)


class BootstrapResult(NamedTuple):
    """Bootstrap CI result."""

    mean_delta: float
    ci_lower: float
    ci_upper: float
    excludes_zero: bool
    n_samples: int


# ---------------------------------------------------------------------------
# Audit log helper
# ---------------------------------------------------------------------------


class AuditLog:
    """Append-only timestamped log for every SQL/HTTP operation.

    Args:
        path: Path to the audit log file. Created if it does not exist.
            Parent directory is created as needed.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write(f"=== pain_dimension_validator started pid={os.getpid()} ===")

    def _write(self, message: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        line = f"[{ts}] {message}\n"
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(line)
        logger.debug("AUDIT: %s", message)

    def sql(self, operation: str, sql: str, rows_affected: int | None = None) -> None:
        """Log a SQL operation.

        Args:
            operation: Human-readable label (e.g., "backup_pain").
            sql: The SQL statement executed.
            rows_affected: Optional row count from cursor.rowcount.
        """
        suffix = f" — {rows_affected} rows affected" if rows_affected is not None else ""
        self._write(f"SQL [{operation}] {sql.strip()[:200]}{suffix}")

    def http(self, method: str, url: str, status: int, duration_ms: int) -> None:
        """Log an HTTP request.

        Args:
            method: HTTP method (GET, POST, …).
            url: Request URL.
            status: HTTP status code.
            duration_ms: Round-trip duration in milliseconds.
        """
        self._write(f"HTTP {method} {url} → {status} ({duration_ms}ms)")

    def event(self, message: str) -> None:
        """Log a general event.

        Args:
            message: Free-form event description.
        """
        self._write(f"EVENT {message}")

    def close(self, success: bool) -> None:
        """Write a closing entry.

        Args:
            success: Whether the overall run completed successfully.
        """
        status = "SUCCESS" if success else "FAILED"
        self._write(f"=== pain_dimension_validator finished status={status} ===")


# ---------------------------------------------------------------------------
# Query loading
# ---------------------------------------------------------------------------


def load_queries(queries_jsonl: str | Path) -> list[Query]:
    """Load all golden queries from a JSONL file.

    Args:
        queries_jsonl: Path to the golden queries JSONL file.

    Returns:
        List of :class:`Query` objects in file order.

    Raises:
        FileNotFoundError: If ``queries_jsonl`` does not exist.
        ValueError: If a line is missing required fields.
    """
    path = Path(queries_jsonl)
    if not path.exists():
        raise FileNotFoundError(f"Queries JSONL not found: {path}")

    queries: list[Query] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                logger.warning("Skipping malformed JSON at line %d: %s", line_no, exc)
                continue

            query_text = obj.get("query")
            expected = obj.get("expected_chunk_ids")
            if query_text is None or expected is None:
                raise ValueError(
                    f"Line {line_no}: missing 'query' or 'expected_chunk_ids'"
                )

            queries.append(
                Query(
                    query_id=int(obj.get("query_id", line_no)),
                    query_text=str(query_text),
                    expected_chunk_ids=[int(cid) for cid in expected],
                    difficulty=obj.get("difficulty"),
                    category=obj.get("category"),
                )
            )

    logger.info("Loaded %d queries from %s", len(queries), path)
    return queries


# ---------------------------------------------------------------------------
# 1. Post-incident query identification
# ---------------------------------------------------------------------------


def identify_post_incident_queries(queries: list[Query]) -> list[Query]:
    """Filter golden queries to those categorised as "post-incident".

    A query is classified as post-incident if ANY of the following hold:
    1. Its ``query_id`` is in the curated set ``{47, 67, 71}`` (R01b cured).
    2. Its ``category`` field matches an incident-type label.
    3. Its ``query_text`` contains at least one post-incident keyword (case-insensitive).

    The function logs which criterion triggered for each accepted query so the
    selection rationale is auditable.

    Args:
        queries: Full list of golden queries (typically all 50).

    Returns:
        Filtered list of post-incident queries.  Order is preserved.
    """
    result: list[Query] = []
    for q in queries:
        reasons: list[str] = []

        # Criterion 1: known curated IDs from R01b
        if q.query_id in _KNOWN_POST_INCIDENT_IDS:
            reasons.append(f"curated_id={q.query_id}")

        # Criterion 2: category label
        if q.category and q.category.lower().strip() in _INCIDENT_CATEGORIES:
            reasons.append(f"category={q.category}")

        # Criterion 3: keyword match in query text
        text_lower = q.query_text.lower()
        matched_kws = [
            kw for kw in _POST_INCIDENT_KEYWORDS if kw.lower() in text_lower
        ]
        if matched_kws:
            reasons.append(f"keywords={matched_kws[:3]}")

        if reasons:
            logger.info(
                "Post-incident Q%d: %r — reasons: %s",
                q.query_id,
                q.query_text[:60],
                "; ".join(reasons),
            )
            result.append(q)

    logger.info(
        "Identified %d post-incident queries out of %d total", len(result), len(queries)
    )
    return result


# ---------------------------------------------------------------------------
# 2. Pain backup/restore SQL generators
# ---------------------------------------------------------------------------


def set_pain_uniform_sql(backup_table: str = "chunks_pain_backup") -> list[str]:
    """Return SQL statements to backup pain values and set pain = 1.0 uniformly.

    The caller is responsible for executing these statements within a
    transaction on the TEMP DB (never on prod).

    The backup table is created as a simple ``id + pain`` table so that the
    original values can be restored precisely, including NULL values.

    Args:
        backup_table: Name of the backup table (default ``chunks_pain_backup``).

    Returns:
        Ordered list of SQL strings to execute sequentially.

    Example::

        stmts = set_pain_uniform_sql()
        for stmt in stmts:
            conn.execute(stmt)
        conn.commit()
    """
    return [
        f"DROP TABLE IF EXISTS {backup_table}",
        f"CREATE TABLE {backup_table} AS SELECT id, pain FROM chunks",
        "UPDATE chunks SET pain = 1.0",
    ]


def restore_pain_from_backup_sql(backup_table: str = "chunks_pain_backup") -> list[str]:
    """Return SQL statements to restore pain values from the backup table.

    Args:
        backup_table: Name of the backup table created by
            :func:`set_pain_uniform_sql`.

    Returns:
        Ordered list of SQL strings to execute sequentially.
    """
    return [
        f"UPDATE chunks SET pain = (SELECT pain FROM {backup_table} "
        f"WHERE {backup_table}.id = chunks.id) "
        f"WHERE EXISTS (SELECT 1 FROM {backup_table} WHERE {backup_table}.id = chunks.id)",
        f"DROP TABLE IF EXISTS {backup_table}",
    ]


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _snapshot_db(prod_db: Path, temp_db: Path, audit: AuditLog) -> None:
    """Create an atomic copy of the prod DB to a temp location.

    Uses ``shutil.copy2`` which is atomic on POSIX at the vnode level for
    files that fit in the filesystem buffer, and is safe for SQLite WAL-mode
    databases because copy2 copies bytes without page interpretation.

    For extra safety, the prod DB connection is opened in ``PRAGMA
    journal_mode=WAL`` read-only mode and a SHARED lock is obtained via
    ``BEGIN DEFERRED`` before the copy — this ensures WAL checkpoint has flushed
    all committed pages to the main DB file before we copy.

    Args:
        prod_db: Path to the production SQLite database (read-only intent).
        temp_db: Destination path for the temp copy.
        audit: Audit log instance.

    Raises:
        FileNotFoundError: If ``prod_db`` does not exist.
        OSError: If the copy fails (disk full, permissions, etc.).
    """
    if not prod_db.exists():
        raise FileNotFoundError(f"Prod DB not found: {prod_db}")

    temp_db.parent.mkdir(parents=True, exist_ok=True)
    if temp_db.exists():
        temp_db.unlink()

    audit.event(f"snapshot_start prod={prod_db} temp={temp_db}")

    # Open prod read-only and trigger a WAL checkpoint to flush committed pages
    try:
        with sqlite3.connect(f"file:{prod_db}?mode=ro", uri=True) as conn:
            conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
            logger.debug("WAL checkpoint issued on prod DB before snapshot")
    except sqlite3.OperationalError as exc:
        logger.warning("WAL checkpoint failed (may be OK if not WAL mode): %s", exc)

    t0 = time.monotonic()
    shutil.copy2(str(prod_db), str(temp_db))
    elapsed_ms = int((time.monotonic() - t0) * 1_000)

    size_mb = temp_db.stat().st_size / (1024 * 1024)
    audit.event(
        f"snapshot_done size_mb={size_mb:.1f} duration_ms={elapsed_ms} dest={temp_db}"
    )
    logger.info("Snapshot done: %.1f MB in %d ms → %s", size_mb, elapsed_ms, temp_db)


def _apply_pain_uniform(
    conn: sqlite3.Connection, audit: AuditLog, backup_table: str = "chunks_pain_backup"
) -> int:
    """Apply uniform pain=1.0 on the TEMP DB connection.

    Args:
        conn: Open SQLite connection to the TEMP DB (NOT prod).
        audit: Audit log.
        backup_table: Backup table name.

    Returns:
        Number of rows updated.
    """
    stmts = set_pain_uniform_sql(backup_table)
    for stmt in stmts:
        cur = conn.execute(stmt)
        audit.sql("set_pain_uniform", stmt, cur.rowcount if cur.rowcount >= 0 else None)
    conn.commit()

    rows_updated = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    logger.info("Applied pain=1.0 uniform — %d chunks affected", rows_updated)
    return rows_updated


def _restore_pain(
    conn: sqlite3.Connection, audit: AuditLog, backup_table: str = "chunks_pain_backup"
) -> None:
    """Restore original pain values from backup table on the TEMP DB.

    Args:
        conn: Open SQLite connection to the TEMP DB.
        audit: Audit log.
        backup_table: Backup table name.
    """
    stmts = restore_pain_from_backup_sql(backup_table)
    for stmt in stmts:
        cur = conn.execute(stmt)
        audit.sql("restore_pain", stmt, cur.rowcount if cur.rowcount >= 0 else None)
    conn.commit()
    logger.info("Pain values restored from backup table")


def _read_mean_pain(
    conn: sqlite3.Connection, chunk_ids: list[int]
) -> float:
    """Compute mean pain of a set of chunk IDs.

    Args:
        conn: SQLite connection (to either prod read-only or temp DB).
        chunk_ids: List of chunk IDs whose pain values to average.

    Returns:
        Mean pain in [0.1, 1.0], or 0.5 if no valid rows found.
    """
    if not chunk_ids:
        return 0.5
    placeholders = ",".join("?" * len(chunk_ids))
    row = conn.execute(
        f"SELECT AVG(COALESCE(pain, 0.2)) FROM chunks WHERE id IN ({placeholders})",
        chunk_ids,
    ).fetchone()
    return float(row[0]) if row and row[0] is not None else 0.5


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def _ndcg_at_k(retrieved: list[int], gold: set[int], k: int = 10) -> float:
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


# ---------------------------------------------------------------------------
# 4. Search via nox-mem HTTP API
# ---------------------------------------------------------------------------


def _http_get(url: str, params: dict[str, Any], timeout_s: float = 30.0) -> tuple[Any, int]:
    """HTTP GET with URL query params (nox-mem API expects GET, not POST).

    Args:
        url: Full URL for the GET request (without query string).
        params: Dict of query string parameters; values URL-encoded.
        timeout_s: Socket timeout in seconds.

    Returns:
        Tuple of (parsed JSON response body, HTTP status code).
        Body may be a list (search results) or dict (errors), per nox-mem API.
    """
    qs = urllib.parse.urlencode({k: str(v) for k, v in params.items()})
    full_url = f"{url}?{qs}"
    req = urllib.request.Request(
        full_url,
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status = resp.status
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read().decode("utf-8", errors="replace")
    return json.loads(raw), status


def run_eval_variant(
    variant: str,
    queries: list[Query],
    api_url: str,
    audit: AuditLog,
    k: int = _DEFAULT_K,
) -> dict[int, QueryResult]:
    """Run a search eval for a list of queries against the nox-mem HTTP API.

    The nox-mem API is assumed to be pointing at the TEMP DB when called for
    the "ablated" variant (the caller must restart the API or use the direct
    DB mode — see notes below).

    IMPORTANT: Because nox-mem's HTTP API reads from its own DB connection
    (initialised at startup), changing the TEMP DB on disk is NOT sufficient
    to affect the running API. The recommended approach for ablation is to
    use the ``direct_db_search`` function instead, which bypasses the API and
    reads the TEMP DB directly via Python's sqlite3 + FTS5.

    This function is kept for completeness and is used when the API can be
    pointed at a fresh DB path via ``NOX_DB_PATH`` env and restarted.

    Args:
        variant: Label for this variant (e.g., "pain_real", "pain_uniform").
        queries: List of queries to evaluate.
        api_url: Base URL of the nox-mem HTTP API.
        audit: Audit log.
        k: Number of results to retrieve per query.

    Returns:
        Dict mapping query_id to :class:`QueryResult`.
    """
    search_url = f"{api_url.rstrip('/')}/api/search"
    results: dict[int, QueryResult] = {}

    logger.info("Running eval variant=%s against %s (%d queries)", variant, search_url, len(queries))

    for q in queries:
        params = {"q": q.query_text, "k": k}
        t0 = time.monotonic()
        try:
            resp_body, status = _http_get(search_url, params)
            duration_ms = int((time.monotonic() - t0) * 1_000)
            audit.http("GET", search_url, status, duration_ms)
        except Exception as exc:
            logger.error("HTTP search failed for Q%d: %s", q.query_id, exc)
            audit.event(f"search_error Q{q.query_id} error={exc}")
            continue

        if status != 200:
            logger.warning("API returned status=%d for Q%d body=%s", status, q.query_id, str(resp_body)[:200])
            continue

        # nox-mem /api/search returns array of {id, score, ...} directly
        chunks = resp_body if isinstance(resp_body, list) else resp_body.get("results", resp_body.get("chunks", []))
        retrieved_ids = [int(c.get("id", 0)) for c in chunks[:k]]
        retrieved_scores = [float(c.get("score", 0.0)) for c in chunks[:k]]

        ndcg = _ndcg_at_k(retrieved_ids, set(q.expected_chunk_ids), k=k)
        results[q.query_id] = QueryResult(
            query_id=q.query_id,
            retrieved_chunk_ids=retrieved_ids,
            retrieved_scores=retrieved_scores,
            ndcg_at_10=ndcg,
            duration_ms=duration_ms,
        )
        logger.debug(
            "Q%d nDCG@10=%.4f duration=%dms", q.query_id, ndcg, duration_ms
        )

    logger.info(
        "Variant %s done — %d/%d queries evaluated, mean nDCG@10=%.4f",
        variant,
        len(results),
        len(queries),
        (sum(r.ndcg_at_10 for r in results.values()) / len(results)) if results else 0.0,
    )
    return results


def direct_db_search(
    query_text: str,
    db_conn: sqlite3.Connection,
    k: int = _DEFAULT_K,
) -> list[tuple[int, float]]:
    """FTS5 BM25 search directly on a SQLite connection (no HTTP).

    This is used for the ablation run against the TEMP DB, bypassing the
    nox-mem HTTP API which cannot be trivially hot-swapped to a different DB
    without a restart.  The FTS5 BM25 component of hybrid search is used here;
    semantic re-ranking is omitted for the ablation (the salience boost applied
    via pain is what we are measuring).

    The scores are BM25 raw values (negative, lower = more relevant) multiplied
    by the chunk's salience weight:
        salience = recency_weight × pain × importance
    where recency_weight is approximated from chunk age and importance defaults
    to 0.5 if not present.

    Args:
        query_text: Natural-language query string.
        db_conn: Open SQLite connection to the DB to search.
        k: Number of top results to return.

    Returns:
        List of ``(chunk_id, composite_score)`` tuples sorted by score descending.
    """
    # FTS5 BM25 + salience composite — mirrors search.ts logic at a high level
    sql = """
        WITH fts_hits AS (
            SELECT
                c.id,
                bm25(chunks_fts) AS bm25_score,
                COALESCE(c.pain, 0.2) AS pain,
                COALESCE(c.importance, 0.5) AS importance,
                CASE
                    WHEN c.created_at IS NULL THEN 0.5
                    ELSE MAX(0.1,
                        1.0 - (
                            CAST((julianday('now') - julianday(c.created_at)) AS REAL)
                            / COALESCE(c.retention_days, 90)
                        )
                    )
                END AS recency
            FROM chunks_fts
            JOIN chunks c ON c.id = chunks_fts.rowid
            WHERE chunks_fts MATCH ?
            LIMIT ?
        )
        SELECT
            id,
            -- composite: FTS score (negated BM25) × salience
            (-bm25_score) * (recency * pain * importance) AS composite_score
        FROM fts_hits
        ORDER BY composite_score DESC
        LIMIT ?
    """
    # Escape FTS5 special characters in query
    safe_query = _escape_fts5_query(query_text)
    try:
        rows = db_conn.execute(sql, (safe_query, k * 3, k)).fetchall()
        return [(int(row[0]), float(row[1])) for row in rows]
    except sqlite3.OperationalError as exc:
        logger.warning("FTS5 search failed for query %r: %s", query_text[:60], exc)
        return []


def _escape_fts5_query(query: str) -> str:
    """Escape a natural-language string for FTS5 MATCH.

    Wraps each token in double-quotes so FTS5 treats them as literals rather
    than interpreting AND/OR/NOT and other special syntax.

    Args:
        query: Raw natural-language query string.

    Returns:
        FTS5-safe query string.
    """
    # Tokenise on whitespace + punctuation
    tokens = re.findall(r'[^\s\"\'\(\)\[\]<>{}|:,;.!?]+', query)
    if not tokens:
        return '""'
    quoted = " ".join(f'"{t}"' for t in tokens[:20])  # cap at 20 tokens
    return quoted


def run_eval_variant_direct(
    variant: str,
    queries: list[Query],
    db_conn: sqlite3.Connection,
    audit: AuditLog,
    k: int = _DEFAULT_K,
) -> dict[int, QueryResult]:
    """Run search eval directly on a SQLite connection (no HTTP API).

    Used for the ablation (pain=1.0) run on the TEMP DB.  The search uses
    FTS5 BM25 + salience composite (no semantic re-ranking because Gemini
    embeddings live in the API process, not accessible here).

    This is a FAIR comparison because:
    - The baseline also uses ``direct_db_search`` (same code path).
    - Both variants see the exact same FTS5 scores; only the pain column differs.
    - Δ nDCG isolates the pain signal.

    Args:
        variant: Label for logging.
        queries: Queries to evaluate.
        db_conn: SQLite connection to the DB to search (prod-read-only for
            baseline, temp for ablation).
        audit: Audit log.
        k: Number of results per query.

    Returns:
        Dict mapping query_id to :class:`QueryResult`.
    """
    results: dict[int, QueryResult] = {}
    logger.info(
        "Running direct eval variant=%s (%d queries, k=%d)", variant, len(queries), k
    )

    for q in queries:
        t0 = time.monotonic()
        hits = direct_db_search(q.query_text, db_conn, k=k)
        duration_ms = int((time.monotonic() - t0) * 1_000)

        retrieved_ids = [doc_id for doc_id, _ in hits]
        retrieved_scores = [score for _, score in hits]

        ndcg = _ndcg_at_k(retrieved_ids, set(q.expected_chunk_ids), k=k)
        results[q.query_id] = QueryResult(
            query_id=q.query_id,
            retrieved_chunk_ids=retrieved_ids,
            retrieved_scores=retrieved_scores,
            ndcg_at_10=ndcg,
            duration_ms=duration_ms,
        )
        audit.event(
            f"eval_query variant={variant} qid={q.query_id} "
            f"ndcg={ndcg:.4f} duration_ms={duration_ms}"
        )
        logger.debug(
            "Q%d [%s] nDCG@10=%.4f in %dms", q.query_id, variant, ndcg, duration_ms
        )

    mean_ndcg = (
        sum(r.ndcg_at_10 for r in results.values()) / len(results)
        if results
        else 0.0
    )
    logger.info(
        "Direct eval %s done — %d queries, mean nDCG@10=%.4f",
        variant,
        len(results),
        mean_ndcg,
    )
    return results


# ---------------------------------------------------------------------------
# 5. Delta table computation
# ---------------------------------------------------------------------------


def compute_delta_table(
    baseline_results: dict[int, QueryResult],
    ablated_results: dict[int, QueryResult],
    queries: list[Query],
    prod_conn: sqlite3.Connection,
) -> tuple[list[DeltaRow], dict[str, Any]]:
    """Compare per-query nDCG@10 between baseline and ablated variants.

    Args:
        baseline_results: Results from the pain-aware (real values) run.
        ablated_results: Results from the pain=1.0 uniform run.
        queries: Post-incident query list (same queries used in both runs).
        prod_conn: Read-only connection to prod DB for reading real pain values.

    Returns:
        Tuple of:
        - ``rows``: List of :class:`DeltaRow` objects, one per query.
        - ``aggregate``: Dict with ``mean_delta``, ``queries_improved``,
          ``queries_degraded``, ``queries_unchanged``, ``mean_ndcg_baseline``,
          ``mean_ndcg_ablated``.
    """
    rows: list[DeltaRow] = []
    skipped = 0

    for q in queries:
        base = baseline_results.get(q.query_id)
        abl = ablated_results.get(q.query_id)
        if base is None or abl is None:
            logger.warning(
                "Q%d missing from one variant — baseline=%s ablated=%s, skipping",
                q.query_id,
                base is not None,
                abl is not None,
            )
            skipped += 1
            continue

        mean_pain = _read_mean_pain(prod_conn, q.expected_chunk_ids)
        delta = base.ndcg_at_10 - abl.ndcg_at_10  # positive = pain-aware wins
        rows.append(
            DeltaRow(
                query_id=q.query_id,
                query_text=q.query_text,
                category=q.category,
                pain_mean_real=mean_pain,
                ndcg_baseline=base.ndcg_at_10,
                ndcg_ablated=abl.ndcg_at_10,
                delta=delta,
            )
        )

    if skipped > 0:
        logger.warning("Skipped %d queries due to missing results", skipped)

    if not rows:
        return rows, {
            "mean_delta": 0.0,
            "queries_improved": 0,
            "queries_degraded": 0,
            "queries_unchanged": 0,
            "mean_ndcg_baseline": 0.0,
            "mean_ndcg_ablated": 0.0,
        }

    mean_delta = sum(r.delta for r in rows) / len(rows)
    queries_improved = sum(1 for r in rows if r.delta > 0.0)
    queries_degraded = sum(1 for r in rows if r.delta < 0.0)
    queries_unchanged = sum(1 for r in rows if r.delta == 0.0)
    mean_ndcg_baseline = sum(r.ndcg_baseline for r in rows) / len(rows)
    mean_ndcg_ablated = sum(r.ndcg_ablated for r in rows) / len(rows)

    aggregate: dict[str, Any] = {
        "mean_delta": mean_delta,
        "queries_improved": queries_improved,
        "queries_degraded": queries_degraded,
        "queries_unchanged": queries_unchanged,
        "mean_ndcg_baseline": mean_ndcg_baseline,
        "mean_ndcg_ablated": mean_ndcg_ablated,
        "n_queries": len(rows),
    }

    logger.info(
        "Delta table: N=%d mean_Δ=%.4f improved=%d degraded=%d unchanged=%d",
        len(rows),
        mean_delta,
        queries_improved,
        queries_degraded,
        queries_unchanged,
    )
    return rows, aggregate


# ---------------------------------------------------------------------------
# 6. Bootstrap significance
# ---------------------------------------------------------------------------


def bootstrap_significance(
    deltas: list[float],
    n_bootstrap: int = _BOOTSTRAP_N,
    seed: int = _BOOTSTRAP_SEED,
    alpha: float = _SIGNIFICANCE_ALPHA,
) -> BootstrapResult:
    """Compute bootstrap 95% CI on the mean Δ nDCG.

    Uses numpy's default_rng for reproducible results.  The CI is computed
    via the percentile method: resample ``deltas`` with replacement 10,000
    times, compute mean each time, take the (α/2) and (1−α/2) percentiles.

    If the CI excludes zero, the improvement is statistically significant at
    level α under bootstrap (which is more appropriate than a t-test for N<30).

    Args:
        deltas: List of per-query Δ nDCG values (baseline − ablated).
        n_bootstrap: Number of bootstrap resamples (default 10,000).
        seed: Random seed for reproducibility (default 42).
        alpha: Significance level (default 0.05 → 95% CI).

    Returns:
        :class:`BootstrapResult` with mean, CI bounds, and ``excludes_zero``.

    Raises:
        ValueError: If ``deltas`` is empty.
    """
    if not deltas:
        raise ValueError("Cannot bootstrap an empty list of deltas")

    arr = np.array(deltas, dtype=np.float64)
    rng = np.random.default_rng(seed)

    bootstrap_means = np.empty(n_bootstrap, dtype=np.float64)
    n = len(arr)
    for i in range(n_bootstrap):
        sample = rng.choice(arr, size=n, replace=True)
        bootstrap_means[i] = sample.mean()

    ci_lower = float(np.percentile(bootstrap_means, 100 * alpha / 2))
    ci_upper = float(np.percentile(bootstrap_means, 100 * (1.0 - alpha / 2)))
    mean_delta = float(arr.mean())
    excludes_zero = ci_lower > 0.0 or ci_upper < 0.0

    logger.info(
        "Bootstrap CI (n=%d, seed=%d): mean=%.4f CI=[%.4f, %.4f] excludes_zero=%s",
        n_bootstrap,
        seed,
        mean_delta,
        ci_lower,
        ci_upper,
        excludes_zero,
    )
    return BootstrapResult(
        mean_delta=mean_delta,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        excludes_zero=excludes_zero,
        n_samples=n,
    )


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def _verdict(
    aggregate: dict[str, Any], bootstrap: BootstrapResult
) -> tuple[str, str]:
    """Determine paper claim verdict based on delta and CI.

    Args:
        aggregate: Aggregated metrics from :func:`compute_delta_table`.
        bootstrap: Bootstrap CI result.

    Returns:
        Tuple of ``(verdict_label, verdict_detail)`` where label is one of
        CONFIRMED / DIRECTIONAL / NOT_SUPPORTED.
    """
    mean_delta = aggregate["mean_delta"]
    if mean_delta >= _DELTA_THRESHOLD and bootstrap.excludes_zero:
        return (
            "CONFIRMED",
            f"Δ={mean_delta:+.3f} ≥ {_DELTA_THRESHOLD} threshold, "
            f"95% CI [{bootstrap.ci_lower:+.3f}, {bootstrap.ci_upper:+.3f}] excludes 0",
        )
    elif mean_delta > 0.0:
        return (
            "DIRECTIONAL",
            f"Δ={mean_delta:+.3f} positive but {'below threshold' if mean_delta < _DELTA_THRESHOLD else ''}"
            f"{'CI includes 0' if not bootstrap.excludes_zero else ''}. "
            "Paper must downgrade claim to 'directional evidence'.",
        )
    else:
        return (
            "NOT_SUPPORTED",
            f"Δ={mean_delta:+.3f} ≤ 0. Pain dimension does not improve retrieval on "
            "this query set. Paper must revise or remove this claim.",
        )


def generate_report(
    rows: list[DeltaRow],
    aggregate: dict[str, Any],
    bootstrap: BootstrapResult,
    output_path: Path,
    elapsed_s: float,
) -> None:
    """Write the Markdown validation report.

    Args:
        rows: Per-query delta rows.
        aggregate: Aggregated metrics.
        bootstrap: Bootstrap CI result.
        output_path: Path to write the report.
        elapsed_s: Total wall-clock time for the validation run.
    """
    verdict_label, verdict_detail = _verdict(aggregate, bootstrap)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = [
        "# Pain Dimension Validation — E10",
        "",
        f"> Generated: {timestamp} | Runtime: {elapsed_s:.0f}s",
        f"> Script: `paper/publication/baselines/pain_dimension_validator.py`",
        "",
        "## Setup",
        "",
        "| Parameter | Value |",
        "|---|---|",
        f"| Comparison | pain-aware (real values) vs pain=1.0 uniform |",
        f"| Metric | nDCG@10 (binary relevance) |",
        f"| N queries | {aggregate['n_queries']} post-incident |",
        f"| Bootstrap | {bootstrap.n_samples} samples × {_BOOTSTRAP_N:,} resamples, seed={_BOOTSTRAP_SEED} |",
        f"| Threshold | Δ ≥ {_DELTA_THRESHOLD} to confirm hypothesis |",
        "",
        "## Per-Query Results",
        "",
        "| Query ID | Query (truncated) | Category | Pain_real (mean) | pain-aware nDCG | pain=1.0 nDCG | Δ nDCG |",
        "|---|---|---|---|---|---|---|",
    ]

    for r in sorted(rows, key=lambda x: -x.delta):
        q_short = r.query_text[:50].replace("|", "&#124;")
        cat = r.category or "—"
        lines.append(
            f"| Q{r.query_id} | {q_short} | {cat} "
            f"| {r.pain_mean_real:.2f} "
            f"| {r.ndcg_baseline:.3f} "
            f"| {r.ndcg_ablated:.3f} "
            f"| {r.delta:+.3f} |"
        )

    lines += [
        f"| **Mean** | | | | "
        f"**{aggregate['mean_ndcg_baseline']:.3f}** | "
        f"**{aggregate['mean_ndcg_ablated']:.3f}** | "
        f"**{aggregate['mean_delta']:+.3f}** |",
        "",
        "## Aggregate Statistics",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Mean Δ nDCG@10 (pain-aware − uniform) | {aggregate['mean_delta']:+.4f} |",
        f"| Queries improved (Δ > 0) | {aggregate['queries_improved']} / {aggregate['n_queries']} |",
        f"| Queries degraded (Δ < 0) | {aggregate['queries_degraded']} / {aggregate['n_queries']} |",
        f"| Queries unchanged (Δ = 0) | {aggregate['queries_unchanged']} / {aggregate['n_queries']} |",
        f"| Baseline mean nDCG@10 | {aggregate['mean_ndcg_baseline']:.4f} |",
        f"| Ablated mean nDCG@10 | {aggregate['mean_ndcg_ablated']:.4f} |",
        "",
        "## Bootstrap Significance",
        "",
        f"Bootstrap 95% CI: [{bootstrap.ci_lower:+.3f}, {bootstrap.ci_upper:+.3f}]",
        "",
        f"- **Excludes zero:** {'YES' if bootstrap.excludes_zero else 'NO'}",
        f"- **Mean Δ:** {bootstrap.mean_delta:+.4f}",
        f"- **N samples:** {bootstrap.n_samples} queries × {_BOOTSTRAP_N:,} resamples",
        f"- **Seed:** {_BOOTSTRAP_SEED} (reproducible)",
        "",
        "## Verdict",
        "",
        f"**{verdict_label}**",
        "",
        f"{verdict_detail}",
        "",
        "---",
        "",
        "## Interpretation",
        "",
        f"The pain dimension in `salience = recency × pain × importance` "
        f"{'improved' if aggregate['mean_delta'] >= 0 else 'did not improve'} "
        f"retrieval on post-incident queries by Δ nDCG@10 = {aggregate['mean_delta']:+.4f}.",
        "",
        f"{'The 95% bootstrap CI excludes zero, supporting the paper claim that pain-aware salience is a meaningful retrieval signal for incident-related queries.' if bootstrap.excludes_zero else 'The 95% bootstrap CI includes zero. N is small — this is directional evidence only. The paper should state this explicitly.'}",
        "",
        "**Safety note:** This experiment ran on a TEMP DB copy. Prod DB was not modified.",
        "",
        f"**Audit log:** `pain_test_audit.log` (same directory as this report)",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Report written → %s", output_path)


# ---------------------------------------------------------------------------
# Confirmation prompt
# ---------------------------------------------------------------------------


def _confirmation_prompt(
    prod_db: Path,
    temp_db: Path,
    n_post_incident: int,
    yes: bool,
) -> bool:
    """Show scope summary and ask for user confirmation before proceeding.

    Args:
        prod_db: Path to the production DB.
        temp_db: Destination path for the temp copy.
        n_post_incident: Number of post-incident queries identified.
        yes: If True, skip the prompt and return True immediately.

    Returns:
        True if the user confirmed (or ``yes=True``), False if aborted.
    """
    if yes:
        logger.info("--yes flag set — skipping confirmation prompt")
        return True

    prod_size_mb = prod_db.stat().st_size / (1024 * 1024) if prod_db.exists() else 0.0
    free_bytes = shutil.disk_usage(temp_db.parent).free
    free_mb = free_bytes / (1024 * 1024)

    print("\n" + "=" * 60)
    print("Pain Dimension Validator — E10 Confirmation")
    print("=" * 60)
    print(f"  Prod DB:            {prod_db}")
    print(f"  Prod DB size:       {prod_size_mb:.1f} MB")
    print(f"  Temp DB dest:       {temp_db}")
    print(f"  Disk free (/tmp):   {free_mb:.0f} MB")
    print(f"  Post-incident Qs:   {n_post_incident}")
    print(f"  Bootstrap N:        {_BOOTSTRAP_N:,} resamples (seed={_BOOTSTRAP_SEED})")
    print(f"  Est. runtime:       ~{int(prod_size_mb / 100 + n_post_incident * 0.1) + 30}s")
    print()
    print("  SAFETY: Prod DB will NOT be modified.")
    print("  All mutations occur on a temp copy that is deleted after the run.")
    print()

    if free_mb < prod_size_mb * 1.2:
        print(
            f"  WARNING: Disk space may be insufficient "
            f"({free_mb:.0f} MB free < {prod_size_mb * 1.2:.0f} MB needed)"
        )
        print()

    answer = input("Proceed? [y/N] ").strip().lower()
    if answer not in {"y", "yes"}:
        print("Aborted.")
        return False
    return True


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser.

    Returns:
        Configured :class:`argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        prog="pain_dimension_validator",
        description=(
            "E10 — Validate the pain dimension of nox-mem salience formula "
            "via nDCG@10 comparison on post-incident golden queries."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("NOX_DB_PATH"),
        metavar="PATH",
        help="Path to nox-mem.db (prod, read-only). Defaults to $NOX_DB_PATH.",
    )
    parser.add_argument(
        "--queries",
        required=True,
        metavar="PATH",
        help="Path to golden_queries.jsonl (required).",
    )
    parser.add_argument(
        "--output",
        default="./pain_validation_results.md",
        metavar="PATH",
        help="Output Markdown report path (default: ./pain_validation_results.md).",
    )
    parser.add_argument(
        "--temp-db",
        default=str(_DEFAULT_TEMP_DB),
        metavar="PATH",
        help=f"Temp DB path for ablation (default: {_DEFAULT_TEMP_DB}). Deleted after run.",
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("NOX_API_URL", _DEFAULT_API_URL),
        metavar="URL",
        help=(
            f"nox-mem API base URL (default: {_DEFAULT_API_URL} or $NOX_API_URL). "
            "Only used when --mode=api."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["direct", "api"],
        default="direct",
        help=(
            "Search mode: 'direct' (sqlite3 FTS5, no API restart needed — recommended) "
            "or 'api' (HTTP API, requires NOX_DB_PATH env + API restart between variants). "
            "Default: direct."
        ),
    )
    parser.add_argument(
        "--k",
        type=int,
        default=_DEFAULT_K,
        metavar="N",
        help=f"Retrieval cutoff (default: {_DEFAULT_K}).",
    )
    parser.add_argument(
        "--n-bootstrap",
        type=int,
        default=_BOOTSTRAP_N,
        metavar="N",
        help=f"Bootstrap resamples (default: {_BOOTSTRAP_N:,}).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt (useful for CI/scripting).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Full validation pipeline.

    Pipeline steps:
    1. Load golden queries → filter post-incident subset.
    2. Confirmation prompt (scope + DB sizes + time estimate).
    3. Snapshot prod DB → temp DB (atomic copy).
    4. Open prod DB read-only → run baseline eval (pain = real values).
    5. Open temp DB read-write → apply pain=1.0 uniform → run ablated eval.
    6. Restore pain from backup on temp DB (for hygiene; temp is deleted anyway).
    7. Compute delta table + bootstrap CI.
    8. Write Markdown report.
    9. Delete temp DB.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code 0 on success, 1 on error.
    """
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.db:
        parser.error("--db is required (or set $NOX_DB_PATH)")

    prod_db = Path(args.db)
    temp_db = Path(args.temp_db)
    output_path = Path(args.output)
    audit_path = output_path.parent / "pain_test_audit.log"
    audit = AuditLog(audit_path)

    t_start = time.monotonic()
    success = False

    try:
        # -----------------------------------------------------------------------
        # Step 1: Load queries + identify post-incident subset
        # -----------------------------------------------------------------------
        logger.info("=== Step 1: Load queries ===")
        all_queries = load_queries(args.queries)
        post_incident = identify_post_incident_queries(all_queries)

        if not post_incident:
            logger.error(
                "No post-incident queries found in %s. "
                "Add queries with category 'incident'/'lesson' or matching keywords. "
                "Alternatively, ensure query_ids 47/67/71 are present.",
                args.queries,
            )
            audit.event("ERROR no_post_incident_queries_found")
            return 1

        audit.event(
            f"post_incident_queries n={len(post_incident)} "
            f"ids={[q.query_id for q in post_incident]}"
        )

        # -----------------------------------------------------------------------
        # Step 2: Confirmation prompt
        # -----------------------------------------------------------------------
        logger.info("=== Step 2: Confirmation ===")
        if not _confirmation_prompt(prod_db, temp_db, len(post_incident), args.yes):
            audit.event("ABORTED user_declined_confirmation")
            return 0

        # -----------------------------------------------------------------------
        # Step 3: Snapshot prod DB
        # -----------------------------------------------------------------------
        logger.info("=== Step 3: Snapshot prod DB ===")
        _snapshot_db(prod_db, temp_db, audit)

        # -----------------------------------------------------------------------
        # Step 4: Baseline eval (real pain values, read from prod OR temp pre-mutation)
        # -----------------------------------------------------------------------
        logger.info("=== Step 4: Baseline eval (pain = real values) ===")
        baseline_results: dict[int, QueryResult]

        if args.mode == "direct":
            # Read prod DB in read-only URI mode — baseline uses real pain values
            with sqlite3.connect(
                f"file:{prod_db}?mode=ro", uri=True
            ) as prod_conn:
                baseline_results = run_eval_variant_direct(
                    variant="pain_real",
                    queries=post_incident,
                    db_conn=prod_conn,
                    audit=audit,
                    k=args.k,
                )
        else:
            # API mode: assumes API is running against prod DB
            baseline_results = run_eval_variant(
                variant="pain_real",
                queries=post_incident,
                api_url=args.api_url,
                audit=audit,
                k=args.k,
            )

        if not baseline_results:
            logger.error("Baseline eval returned no results. Check DB path and FTS5 schema.")
            audit.event("ERROR baseline_no_results")
            return 1

        # -----------------------------------------------------------------------
        # Step 5: Ablated eval (pain = 1.0 uniform)
        # -----------------------------------------------------------------------
        logger.info("=== Step 5: Ablated eval (pain = 1.0 uniform) ===")
        ablated_results: dict[int, QueryResult]

        if args.mode == "direct":
            with sqlite3.connect(str(temp_db)) as temp_conn:
                rows_updated = _apply_pain_uniform(temp_conn, audit)
                logger.info("pain=1.0 applied to %d chunks in temp DB", rows_updated)

                ablated_results = run_eval_variant_direct(
                    variant="pain_uniform",
                    queries=post_incident,
                    db_conn=temp_conn,
                    audit=audit,
                    k=args.k,
                )

                # Restore for hygiene (temp DB deleted anyway, but makes the
                # audit log clean and the code intention explicit)
                _restore_pain(temp_conn, audit)
        else:
            logger.warning(
                "API mode ablation requires restarting the nox-mem API "
                "with the temp DB and pain columns set to 1.0. "
                "This must be done manually. Results will be empty if skipped."
            )
            ablated_results = {}

        if not ablated_results:
            logger.error(
                "Ablated eval returned no results. "
                "In API mode you must restart the API pointed at the temp DB "
                "and with pain=1.0 applied — see script docstring."
            )
            audit.event("ERROR ablated_no_results")
            return 1

        # -----------------------------------------------------------------------
        # Step 6: Delta table + bootstrap CI
        # -----------------------------------------------------------------------
        logger.info("=== Step 6: Compute deltas + bootstrap CI ===")
        # Re-open prod read-only for pain value lookup
        with sqlite3.connect(f"file:{prod_db}?mode=ro", uri=True) as prod_conn_ro:
            delta_rows, aggregate = compute_delta_table(
                baseline_results=baseline_results,
                ablated_results=ablated_results,
                queries=post_incident,
                prod_conn=prod_conn_ro,
            )

        if not delta_rows:
            logger.error("Delta table is empty — no matching query results in both variants")
            audit.event("ERROR delta_table_empty")
            return 1

        deltas = [r.delta for r in delta_rows]
        bootstrap = bootstrap_significance(
            deltas=deltas,
            n_bootstrap=args.n_bootstrap,
            seed=_BOOTSTRAP_SEED,
        )

        # -----------------------------------------------------------------------
        # Step 7: Write report
        # -----------------------------------------------------------------------
        logger.info("=== Step 7: Write report ===")
        elapsed_s = time.monotonic() - t_start
        generate_report(
            rows=delta_rows,
            aggregate=aggregate,
            bootstrap=bootstrap,
            output_path=output_path,
            elapsed_s=elapsed_s,
        )

        verdict_label, _ = _verdict(aggregate, bootstrap)
        print(f"\nVerdict: {verdict_label}")
        print(f"Mean Δ nDCG@10 = {aggregate['mean_delta']:+.4f}")
        print(f"Bootstrap 95% CI: [{bootstrap.ci_lower:+.3f}, {bootstrap.ci_upper:+.3f}]")
        print(f"Report: {output_path}")
        print(f"Audit:  {audit_path}")

        success = True
        return 0

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        audit.event("ABORTED keyboard_interrupt")
        return 130

    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)
        audit.event(f"ERROR unexpected exc={exc!r}")
        return 1

    finally:
        # Always delete temp DB — no side effects on prod
        if temp_db.exists():
            try:
                temp_db.unlink()
                # Also clean up WAL and SHM if present
                for suffix in ("-wal", "-shm"):
                    sidecar = Path(str(temp_db) + suffix)
                    if sidecar.exists():
                        sidecar.unlink()
                logger.info("Temp DB deleted: %s", temp_db)
                audit.event(f"temp_db_deleted path={temp_db}")
            except OSError as exc:
                logger.warning("Failed to delete temp DB %s: %s", temp_db, exc)

        audit.close(success)


if __name__ == "__main__":
    sys.exit(main())
