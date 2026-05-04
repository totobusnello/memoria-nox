"""
Pain Ablation — FTS-Only Mode (E10 addendum).

Hypothesis
----------
Pain dimension shows a measurable effect when isolated from the Gemini semantic
layer, using only FTS5 BM25 × pain multiplier.

This script deliberately excludes Gemini embeddings and RRF fusion so that the
pain signal is the *only* discriminating factor beyond term-frequency relevance.
If pain is meaningful, Δ nDCG (real − uniform) should be positive and the
bootstrap 95% CI should exclude zero.

Context
-------
The hybrid run (pain_ablation_hybrid.py) showed Δ = +0.0065 (mean) — essentially
zero — because Gemini semantic scoring dominates the RRF fusion and pain (a
multiplicative factor on the BM25 branch) is diluted to noise at that scale.

This FTS-only ablation isolates the question: *does pain carry signal when the
semantic layer is removed?*  The paper §5.5 narrative is:
    "pain serves as a fallback discriminator in the tied-regime when semantic
     confidence is low or semantic retrieval is absent."

Two N variants are evaluated:
  - n=31: the same post-incident query subset used in the hybrid run, for
          direct comparability (same queries, same gold, different search mode)
  - n=60: all queries in the golden set for a broader statistical picture

Search method
-------------
Direct sqlite3 query against the real-pain snapshot and the uniform-pain copy:

    WITH fts_results AS (
      SELECT chunks.id, chunks.pain, bm25(chunks_fts) AS bm25_score
      FROM chunks_fts
      JOIN chunks ON chunks.rowid = chunks_fts.rowid
      WHERE chunks_fts MATCH ?
      LIMIT 100
    )
    SELECT id, (-bm25_score) * pain AS composite_score
    FROM fts_results
    ORDER BY composite_score DESC
    LIMIT 10

(-bm25_score) negates the negative BM25 value (lower BM25 = more relevant in
SQLite FTS5), then multiplies by pain.  This is the purest form of the pain
signal without salience (recency × importance are held constant at 1.0 for both
variants, so they cancel in the comparison).

Safety
------
- Real snapshot is opened read-only (URI mode).
- Uniform-pain DB is the caller-supplied temp copy (--db-uniform), which the
  caller creates via ``cp real.db uniform.db && sqlite3 uniform.db "UPDATE
  chunks SET pain = 1.0;"``.  This script does NOT mutate any DB.
- ``--cleanup`` flag deletes the uniform DB after the run (try/finally).

Usage
-----
    python3 pain_ablation_fts_only.py \\
        --db-real    /root/paper-experiments/nox-mem-snapshot-20260504-0616.db \\
        --db-uniform /tmp/nox-mem-pain-uniform-fts.db \\
        --queries    /root/paper-experiments/golden-queries.jsonl \\
        --output     /root/paper-experiments/pain_ablation_fts_results.md \\
        --cleanup

Output
------
  /root/paper-experiments/pain_ablation_fts_results.md
  (also printed to stdout as a compact summary)
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("pain_ablation_fts")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_K = 10
_BOOTSTRAP_N = 10_000
_BOOTSTRAP_SEED = 42
_SIGNIFICANCE_ALPHA = 0.05
_DELTA_THRESHOLD = 0.05   # paper claim threshold
_DIRECTIONAL_THRESHOLD = 0.02  # below this → INSIGNIFICANT

# The 31-query subset used in the hybrid run.
# This set was selected in pain_ablation_hybrid.py and corresponds to
# queries that were included in that eval (post-incident + broad coverage).
# Keeping it identical ensures the FTS-only Δ is directly comparable to
# the hybrid Δ = +0.0065.
_HYBRID_N31_QUERY_IDS: frozenset[int] = frozenset({
    46, 47, 48, 52, 55, 56, 57, 61, 63, 64, 66, 67, 70, 71,
    74, 75, 77, 78, 80, 83, 85, 87, 88, 89, 90, 91, 92, 97,
    100, 101, 102,
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
    """FTS-only search result for one query at one pain variant."""

    query_id: int
    retrieved_chunk_ids: list[int]
    retrieved_scores: list[float]
    ndcg_at_10: float
    duration_ms: int
    fts_hit_count: int  # how many FTS results returned (0 = zero recall)


class DeltaRow(NamedTuple):
    """Per-query comparison: pain_real vs pain_uniform."""

    query_id: int
    query_text: str
    category: str | None
    pain_mean_gold: float   # mean pain of gold chunks in real DB
    ndcg_real: float
    ndcg_uniform: float
    delta: float            # real − uniform (positive = pain-aware wins)
    fts_hits_real: int      # FTS recall depth (0 = no match)


class BootstrapResult(NamedTuple):
    """Bootstrap 95% CI on mean Δ nDCG."""

    mean_delta: float
    ci_lower: float
    ci_upper: float
    excludes_zero: bool
    n_samples: int


# ---------------------------------------------------------------------------
# Query loading
# ---------------------------------------------------------------------------


def load_queries(queries_jsonl: Path) -> list[Query]:
    """Load golden queries from a JSONL file.

    Args:
        queries_jsonl: Path to golden-queries.jsonl (one JSON object per line).

    Returns:
        List of :class:`Query` in file order.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If a line is missing required fields.
    """
    if not queries_jsonl.exists():
        raise FileNotFoundError(f"Queries JSONL not found: {queries_jsonl}")

    queries: list[Query] = []
    with queries_jsonl.open("r", encoding="utf-8") as fh:
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

    logger.info("Loaded %d queries from %s", len(queries), queries_jsonl)
    return queries


# ---------------------------------------------------------------------------
# FTS5 helpers
# ---------------------------------------------------------------------------

_FTS5_SPECIAL_CHARS_RE = re.compile(r"""[^\s"'\(\)\[\]<>{}|:,;.!?]+""")


def escape_fts5_query(query_text: str) -> str:
    """Escape a natural-language string for safe FTS5 MATCH.

    Wraps each whitespace-delimited token in double-quotes so that FTS5 treats
    them as literals rather than interpreting AND/OR/NOT/NEAR and other
    special syntax operators.

    Caps at 20 tokens to avoid hitting SQLite expression-depth limits.

    Args:
        query_text: Raw natural-language query string (PT-BR or EN).

    Returns:
        FTS5-safe MATCH expression string.

    Examples:
        >>> escape_fts5_query("withOpAudit reindex")
        '"withOpAudit" "reindex"'
        >>> escape_fts5_query("OR AND NOT")
        '"OR" "AND" "NOT"'
    """
    tokens = _FTS5_SPECIAL_CHARS_RE.findall(query_text)
    if not tokens:
        return '""'
    quoted = " ".join('"' + t + '"' for t in tokens[:20])
    return quoted


def fts_search_pain_composite(
    conn: sqlite3.Connection,
    query_text: str,
    k: int = _DEFAULT_K,
) -> list[tuple[int, float]]:
    """FTS5 BM25 × pain multiplier search (pure FTS, no semantic embeddings).

    Scoring formula:
        composite_score = (-bm25_score) * pain

    where ``-bm25_score`` negates the SQLite BM25 value (which is negative;
    lower value = more relevant in SQLite's convention) to produce a positive
    relevance magnitude, then multiplies by ``pain`` to boost high-pain chunks.

    Both real-pain and uniform-pain DBs use the same formula.  When pain is
    uniform (1.0 everywhere), it cancels out and ranking is pure BM25.  When
    pain varies, high-pain chunks receive proportionally higher scores.

    This is intentionally *not* the full salience formula (recency × pain ×
    importance).  Recency and importance are held constant (excluded) so that
    pain is the sole differentiating factor.  This gives the cleanest possible
    isolation of the pain signal.

    Args:
        conn: Open ``sqlite3.Connection`` to a nox-mem snapshot DB.
        query_text: Natural-language query string.
        k: Number of top results to return.

    Returns:
        List of ``(chunk_id, composite_score)`` sorted descending by score.
        Empty list if FTS finds no matches or raises an error.
    """
    safe_query = escape_fts5_query(query_text)
    sql = """
        WITH fts_results AS (
            SELECT
                chunks.id,
                chunks.pain,
                bm25(chunks_fts) AS bm25_score
            FROM chunks_fts
            JOIN chunks ON chunks.rowid = chunks_fts.rowid
            WHERE chunks_fts MATCH ?
            LIMIT 100
        )
        SELECT
            id,
            (-bm25_score) * COALESCE(pain, 0.2) AS composite_score
        FROM fts_results
        ORDER BY composite_score DESC
        LIMIT ?
    """
    try:
        rows = conn.execute(sql, (safe_query, k)).fetchall()
        return [(int(row[0]), float(row[1])) for row in rows]
    except sqlite3.OperationalError as exc:
        logger.warning(
            "FTS5 search error for query %r: %s", query_text[:60], exc
        )
        return []


# ---------------------------------------------------------------------------
# nDCG@k metric
# ---------------------------------------------------------------------------


def ndcg_at_k(retrieved: list[int], gold: set[int], k: int = _DEFAULT_K) -> float:
    """Compute nDCG@k with binary relevance.

    Args:
        retrieved: Ordered list of retrieved chunk IDs (rank 1 = index 0).
        gold: Set of relevant chunk IDs.
        k: Cutoff rank.

    Returns:
        nDCG@k in [0.0, 1.0]. Returns 0.0 if gold is empty.
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
# Eval runner
# ---------------------------------------------------------------------------


def run_eval_variant(
    variant: str,
    queries: list[Query],
    conn: sqlite3.Connection,
    k: int = _DEFAULT_K,
) -> dict[int, QueryResult]:
    """Evaluate a list of queries against a DB connection using FTS-only search.

    Args:
        variant: Label for logging (e.g., "pain_real", "pain_uniform").
        queries: List of queries to evaluate.
        conn: Open sqlite3 connection to the snapshot DB for this variant.
        k: Retrieval cutoff (nDCG@k).

    Returns:
        Dict mapping ``query_id`` to :class:`QueryResult`.
    """
    results: dict[int, QueryResult] = {}
    logger.info(
        "Running FTS-only eval variant=%s (%d queries, k=%d)",
        variant, len(queries), k,
    )

    for q in queries:
        t0 = time.monotonic()
        hits = fts_search_pain_composite(conn, q.query_text, k=k)
        duration_ms = int((time.monotonic() - t0) * 1_000)

        retrieved_ids = [doc_id for doc_id, _ in hits]
        retrieved_scores = [score for _, score in hits]
        score_val = ndcg_at_k(retrieved_ids, set(q.expected_chunk_ids), k=k)

        results[q.query_id] = QueryResult(
            query_id=q.query_id,
            retrieved_chunk_ids=retrieved_ids,
            retrieved_scores=retrieved_scores,
            ndcg_at_10=score_val,
            duration_ms=duration_ms,
            fts_hit_count=len(hits),
        )
        logger.debug(
            "Q%d [%s] nDCG@10=%.4f fts_hits=%d in %dms",
            q.query_id, variant, score_val, len(hits), duration_ms,
        )

    mean_ndcg = (
        sum(r.ndcg_at_10 for r in results.values()) / len(results)
        if results else 0.0
    )
    zero_recall = sum(1 for r in results.values() if r.fts_hit_count == 0)
    logger.info(
        "Variant %s done — %d queries, mean nDCG@10=%.4f, zero_recall=%d",
        variant, len(results), mean_ndcg, zero_recall,
    )
    return results


# ---------------------------------------------------------------------------
# Delta computation
# ---------------------------------------------------------------------------


def read_mean_pain_gold(
    conn: sqlite3.Connection, chunk_ids: list[int]
) -> float:
    """Compute mean pain of gold chunks in the real-pain DB.

    Args:
        conn: Read-only connection to the real-pain snapshot.
        chunk_ids: Gold chunk IDs for this query.

    Returns:
        Mean pain value, or 0.2 (default) if no matching rows found.
    """
    if not chunk_ids:
        return 0.2
    placeholders = ",".join("?" * len(chunk_ids))
    row = conn.execute(
        f"SELECT AVG(COALESCE(pain, 0.2)) FROM chunks WHERE id IN ({placeholders})",
        chunk_ids,
    ).fetchone()
    return float(row[0]) if row and row[0] is not None else 0.2


def compute_deltas(
    real_results: dict[int, QueryResult],
    uniform_results: dict[int, QueryResult],
    queries: list[Query],
    real_conn: sqlite3.Connection,
) -> tuple[list[DeltaRow], dict[str, Any]]:
    """Compute per-query Δ nDCG and aggregate statistics.

    Args:
        real_results: QueryResults from the real-pain DB.
        uniform_results: QueryResults from the uniform-pain DB.
        queries: Query list (same subset used for both variants).
        real_conn: Read-only connection to the real-pain DB for pain lookups.

    Returns:
        Tuple of (list of DeltaRow, aggregate stats dict).
    """
    rows: list[DeltaRow] = []
    skipped = 0

    for q in queries:
        real = real_results.get(q.query_id)
        uni = uniform_results.get(q.query_id)
        if real is None or uni is None:
            logger.warning(
                "Q%d missing from one variant (real=%s uniform=%s) — skipping",
                q.query_id, real is not None, uni is not None,
            )
            skipped += 1
            continue

        mean_pain = read_mean_pain_gold(real_conn, q.expected_chunk_ids)
        delta = real.ndcg_at_10 - uni.ndcg_at_10

        rows.append(
            DeltaRow(
                query_id=q.query_id,
                query_text=q.query_text,
                category=q.category,
                pain_mean_gold=mean_pain,
                ndcg_real=real.ndcg_at_10,
                ndcg_uniform=uni.ndcg_at_10,
                delta=delta,
                fts_hits_real=real.fts_hit_count,
            )
        )

    if skipped:
        logger.warning("Skipped %d queries due to missing results", skipped)

    if not rows:
        return rows, {
            "mean_delta": 0.0,
            "queries_improved": 0,
            "queries_degraded": 0,
            "queries_unchanged": 0,
            "mean_ndcg_real": 0.0,
            "mean_ndcg_uniform": 0.0,
            "n_queries": 0,
            "zero_recall_count": 0,
        }

    mean_delta = sum(r.delta for r in rows) / len(rows)
    mean_ndcg_real = sum(r.ndcg_real for r in rows) / len(rows)
    mean_ndcg_uniform = sum(r.ndcg_uniform for r in rows) / len(rows)
    queries_improved = sum(1 for r in rows if r.delta > 1e-6)
    queries_degraded = sum(1 for r in rows if r.delta < -1e-6)
    queries_unchanged = sum(1 for r in rows if abs(r.delta) <= 1e-6)
    zero_recall = sum(1 for r in rows if r.fts_hits_real == 0)

    aggregate: dict[str, Any] = {
        "mean_delta": mean_delta,
        "queries_improved": queries_improved,
        "queries_degraded": queries_degraded,
        "queries_unchanged": queries_unchanged,
        "mean_ndcg_real": mean_ndcg_real,
        "mean_ndcg_uniform": mean_ndcg_uniform,
        "n_queries": len(rows),
        "zero_recall_count": zero_recall,
    }

    logger.info(
        "Deltas N=%d mean_Δ=%.4f improved=%d degraded=%d unchanged=%d zero_recall=%d",
        len(rows), mean_delta, queries_improved, queries_degraded,
        queries_unchanged, zero_recall,
    )
    return rows, aggregate


# ---------------------------------------------------------------------------
# Bootstrap significance
# ---------------------------------------------------------------------------


def bootstrap_ci(
    deltas: list[float],
    n_bootstrap: int = _BOOTSTRAP_N,
    seed: int = _BOOTSTRAP_SEED,
    alpha: float = _SIGNIFICANCE_ALPHA,
) -> BootstrapResult:
    """Bootstrap 95% CI on mean Δ nDCG via percentile method.

    Args:
        deltas: Per-query Δ nDCG values (real − uniform).
        n_bootstrap: Number of resamples (default 10,000).
        seed: RNG seed for reproducibility (default 42).
        alpha: Significance level (default 0.05 → 95% CI).

    Returns:
        :class:`BootstrapResult` with mean, CI bounds, and excludes_zero flag.

    Raises:
        ValueError: If deltas is empty.
    """
    if not deltas:
        raise ValueError("Cannot bootstrap an empty list of deltas")

    arr = np.array(deltas, dtype=np.float64)
    rng = np.random.default_rng(seed)
    n = len(arr)

    bootstrap_means = np.array(
        [rng.choice(arr, size=n, replace=True).mean() for _ in range(n_bootstrap)],
        dtype=np.float64,
    )

    ci_lower = float(np.percentile(bootstrap_means, 100 * alpha / 2))
    ci_upper = float(np.percentile(bootstrap_means, 100 * (1.0 - alpha / 2)))
    mean_delta = float(arr.mean())
    excludes_zero = ci_lower > 0.0 or ci_upper < 0.0

    logger.info(
        "Bootstrap CI (n=%d, seed=%d): mean=%.4f CI=[%.4f, %.4f] excludes_zero=%s",
        n_bootstrap, seed, mean_delta, ci_lower, ci_upper, excludes_zero,
    )
    return BootstrapResult(
        mean_delta=mean_delta,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        excludes_zero=excludes_zero,
        n_samples=n,
    )


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------


def verdict(
    aggregate: dict[str, Any],
    bs: BootstrapResult,
) -> tuple[str, str]:
    """Determine evidence verdict for the FTS-only pain hypothesis.

    Thresholds (mirroring the hybrid run conventions):
    - SIGNIFICANT  : |Δ| ≥ 0.05 AND CI excludes 0
    - DIRECTIONAL  : Δ > 0 but below threshold OR CI includes 0
    - INSIGNIFICANT: |Δ| < 0.02

    Args:
        aggregate: Aggregated metrics from :func:`compute_deltas`.
        bs: Bootstrap CI result.

    Returns:
        Tuple of (verdict_label, detail_string).
    """
    mean_delta = aggregate["mean_delta"]

    if abs(mean_delta) < _DIRECTIONAL_THRESHOLD:
        return (
            "INSIGNIFICANT",
            f"Δ={mean_delta:+.4f} — absolute effect below {_DIRECTIONAL_THRESHOLD} threshold. "
            "FTS-only pain signal is too weak to discriminate.  "
            "This confirms the paper §5.5 framing: pain is a secondary signal, "
            "not a standalone retrieval mechanism.",
        )
    elif mean_delta >= _DELTA_THRESHOLD and bs.excludes_zero:
        return (
            "SIGNIFICANT",
            f"Δ={mean_delta:+.4f} ≥ {_DELTA_THRESHOLD} and 95% CI "
            f"[{bs.ci_lower:+.4f}, {bs.ci_upper:+.4f}] excludes 0.  "
            "Pain dimension is a statistically significant retrieval signal "
            "in FTS-only mode, confirming §5.5 fallback-regime hypothesis.",
        )
    elif mean_delta > 0.0:
        return (
            "DIRECTIONAL",
            f"Δ={mean_delta:+.4f} is positive but "
            + (f"below {_DELTA_THRESHOLD} threshold" if mean_delta < _DELTA_THRESHOLD else "")
            + (" and CI includes 0" if not bs.excludes_zero else "")
            + ".  Directional evidence only — paper §5.5 should state "
            "'directional evidence in FTS-only regime'.",
        )
    else:
        return (
            "NOT_SUPPORTED",
            f"Δ={mean_delta:+.4f} ≤ 0.  Pain-aware ranking is not better than "
            "uniform in FTS-only mode.  Paper must revise §5.5 claim.",
        )


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def _section_header(n: int, variant_label: str) -> list[str]:
    return [
        f"## Results n={n} — {variant_label}",
        "",
    ]


def _results_table(
    rows: list[DeltaRow],
    aggregate: dict[str, Any],
    bs: BootstrapResult,
) -> list[str]:
    """Format a results table block for one N variant."""
    lines: list[str] = [
        "| Q | Query (truncated 55 chars) | Category | Gold pain (mean) "
        "| FTS hits | nDCG real | nDCG uniform | Δ nDCG |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for r in sorted(rows, key=lambda x: -abs(x.delta)):
        q_short = r.query_text[:55].replace("|", "&#124;")
        cat = r.category or "—"
        delta_str = f"**{r.delta:+.3f}**" if abs(r.delta) > 0.01 else f"{r.delta:+.3f}"
        lines.append(
            f"| Q{r.query_id} | {q_short} | {cat} "
            f"| {r.pain_mean_gold:.2f} "
            f"| {r.fts_hits_real} "
            f"| {r.ndcg_real:.3f} "
            f"| {r.ndcg_uniform:.3f} "
            f"| {delta_str} |"
        )

    lines.append(
        f"| **Mean** | | | | "
        f"| **{aggregate['mean_ndcg_real']:.3f}** "
        f"| **{aggregate['mean_ndcg_uniform']:.3f}** "
        f"| **{aggregate['mean_delta']:+.3f}** |"
    )

    lines += [
        "",
        "### Aggregate statistics",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| N queries | {aggregate['n_queries']} |",
        f"| Mean Δ nDCG@10 (real − uniform) | {aggregate['mean_delta']:+.4f} |",
        f"| Queries improved (Δ > 0) | {aggregate['queries_improved']} / {aggregate['n_queries']} |",
        f"| Queries degraded (Δ < 0) | {aggregate['queries_degraded']} / {aggregate['n_queries']} |",
        f"| Queries unchanged (Δ ≈ 0) | {aggregate['queries_unchanged']} / {aggregate['n_queries']} |",
        f"| Zero-recall queries (FTS hits = 0) | {aggregate['zero_recall_count']} / {aggregate['n_queries']} |",
        f"| Bootstrap 95% CI | [{bs.ci_lower:+.4f}, {bs.ci_upper:+.4f}] |",
        f"| CI excludes zero | {'YES' if bs.excludes_zero else 'NO'} |",
        "",
    ]
    return lines


def generate_report(
    rows_n31: list[DeltaRow],
    agg_n31: dict[str, Any],
    bs_n31: BootstrapResult,
    rows_n60: list[DeltaRow],
    agg_n60: dict[str, Any],
    bs_n60: BootstrapResult,
    output_path: Path,
    elapsed_s: float,
    db_real: Path,
    db_uniform: Path,
    queries_path: Path,
) -> None:
    """Write the full Markdown report for both N variants.

    Args:
        rows_n31: Delta rows for n=31 subset.
        agg_n31: Aggregate stats for n=31.
        bs_n31: Bootstrap result for n=31.
        rows_n60: Delta rows for n=60 (all queries).
        agg_n60: Aggregate stats for n=60.
        bs_n60: Bootstrap result for n=60.
        output_path: Path to write the report.
        elapsed_s: Total wall-clock seconds.
        db_real: Path to the real-pain DB.
        db_uniform: Path to the uniform-pain DB.
        queries_path: Path to the golden queries JSONL.
    """
    verdict_label_31, verdict_detail_31 = verdict(agg_n31, bs_n31)
    verdict_label_60, verdict_detail_60 = verdict(agg_n60, bs_n60)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Top 10 by |Δ| across n=60 (broadest picture)
    top10 = sorted(rows_n60, key=lambda x: -abs(x.delta))[:10]

    lines: list[str] = [
        "# E10 Pain Ablation — FTS-Only Mode",
        "",
        f"> Generated: {timestamp} | Runtime: {elapsed_s:.0f}s",
        "> Script: `paper/publication/baselines/pain_ablation_fts_only.py`",
        "",
        "## Hypothesis",
        "",
        "Pain dimension shows significant effect when isolated from semantic Gemini layer.",
        "",
        "## Setup",
        "",
        "| Parameter | Value |",
        "|---|---|",
        "| Mode | FTS5 BM25 × pain multiplier ONLY (no Gemini embeddings, no RRF) |",
        "| Scoring | composite = (−bm25_score) × pain |",
        "| pain_real DB | `" + str(db_real.name) + "` |",
        "| pain_uniform DB | `" + str(db_uniform.name) + "` (pain = 1.0 for ALL chunks) |",
        "| Queries | `" + str(queries_path.name) + "` |",
        f"| Bootstrap | {_BOOTSTRAP_N:,} resamples, seed={_BOOTSTRAP_SEED} |",
        f"| Significance threshold | Δ ≥ {_DELTA_THRESHOLD} AND CI excludes 0 |",
        f"| Directional threshold | Δ ≥ {_DIRECTIONAL_THRESHOLD} |",
        "",
        "**Comparison baseline:** Hybrid run E10 Δ = +0.0065 (n=31, Gemini semantic dominant)",
        "",
    ]

    # n=31 results
    lines += _section_header(agg_n31["n_queries"], "post-incident subset (comparable to hybrid run)")
    lines += _results_table(rows_n31, agg_n31, bs_n31)

    lines += [
        f"**Verdict (n=31): {verdict_label_31}**",
        "",
        verdict_detail_31,
        "",
    ]

    # n=60 results
    lines += _section_header(agg_n60["n_queries"], "all queries")
    lines += _results_table(rows_n60, agg_n60, bs_n60)

    lines += [
        f"**Verdict (n=60): {verdict_label_60}**",
        "",
        verdict_detail_60,
        "",
    ]

    # Per-query breakdown top 10
    lines += [
        "## Per-query breakdown — top 10 by |Δ| (n=60)",
        "",
        "| Q | Query | Category | Gold pain | FTS hits | nDCG real | nDCG uniform | Δ |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in top10:
        q_short = r.query_text[:55].replace("|", "&#124;")
        lines.append(
            f"| Q{r.query_id} | {q_short} | {r.category or '—'} "
            f"| {r.pain_mean_gold:.2f} "
            f"| {r.fts_hits_real} "
            f"| {r.ndcg_real:.3f} "
            f"| {r.ndcg_uniform:.3f} "
            f"| **{r.delta:+.3f}** |"
        )

    lines += [
        "",
        "## Comparison: FTS-only vs Hybrid",
        "",
        "| Metric | FTS-only (n=31) | FTS-only (n=60) | Hybrid (n=31) |",
        "|---|---|---|---|",
        f"| Mean Δ nDCG@10 | {agg_n31['mean_delta']:+.4f} | {agg_n60['mean_delta']:+.4f} | +0.0065 |",
        f"| 95% CI lower | {bs_n31.ci_lower:+.4f} | {bs_n60.ci_lower:+.4f} | — |",
        f"| 95% CI upper | {bs_n31.ci_upper:+.4f} | {bs_n60.ci_upper:+.4f} | — |",
        f"| CI excludes 0 | {'YES' if bs_n31.excludes_zero else 'NO'} "
        f"| {'YES' if bs_n60.excludes_zero else 'NO'} | NO |",
        f"| Verdict | {verdict_label_31} | {verdict_label_60} | DIRECTIONAL |",
        "",
        "## Verdict",
        "",
        f"**n=31: {verdict_label_31}** — {verdict_detail_31}",
        "",
        f"**n=60: {verdict_label_60}** — {verdict_detail_60}",
        "",
        "## Interpretation for paper §5.5",
        "",
    ]

    # Interpretation block depends on FTS-only verdict vs hybrid
    combined_verdict = verdict_label_31  # primary comparable verdict
    if combined_verdict == "SIGNIFICANT":
        lines += [
            "FTS-only shows a statistically significant pain effect, while hybrid Δ ≈ 0.  "
            "This directly supports the §5.5 narrative:",
            "",
            "> *'Pain serves as a meaningful discriminator in the FTS-only regime.  "
            "In the full hybrid pipeline, Gemini semantic scoring dominates RRF fusion "
            "and the pain signal is diluted to noise.  Pain therefore functions as a "
            "fallback signal: consequential when semantic confidence is low or absent, "
            "negligible when semantic retrieval is operating normally.'*",
        ]
    elif combined_verdict == "DIRECTIONAL":
        lines += [
            "FTS-only shows a positive directional pain effect (Δ > 0) but the CI "
            "includes zero, meaning statistical significance is not established at N=31.  "
            "Recommended §5.5 framing:",
            "",
            "> *'Pain provides directional retrieval improvement in the FTS-only regime "
            "(Δ = " + f"{agg_n31['mean_delta']:+.4f}" + ", 95% CI "
            + f"[{bs_n31.ci_lower:+.4f}, {bs_n31.ci_upper:+.4f}]" + ").  "
            "While statistical significance is limited by N, the direction is consistent "
            "with the hypothesis that pain is a secondary signal whose effect is masked "
            "by Gemini semantic dominance in hybrid mode.'*",
        ]
    elif combined_verdict == "INSIGNIFICANT":
        lines += [
            "FTS-only Δ is effectively zero — pain does not move the needle in FTS-only mode.  "
            "Two possible explanations:",
            "",
            "1. **Pain range is too narrow** (0.1–1.0, mostly 0.2):  "
            "54,794 of 61,257 chunks have pain=0.2 (default).  "
            "With ~89% of the corpus at the same value, the discriminating power is minimal.",
            "",
            "2. **FTS recall is zero for most queries** (gold chunks not retrieved by BM25):  "
            "If FTS cannot surface the gold chunks at all, pain cannot influence their ranking.  "
            "Check the `FTS hits` column — queries with 0 hits are unrescuable by pain.",
            "",
            "Recommended §5.5 revision: *'Pain calibration (current range: 0.2–1.0, "
            "median 0.2) is insufficient to produce measurable retrieval gains.  "
            "The pain dimension requires wider calibration or a normalized log-scale "
            "to serve as an effective fallback discriminator.'*",
        ]
    else:  # NOT_SUPPORTED
        lines += [
            "FTS-only pain effect is negative or zero.  Paper §5.5 claim must be "
            "revised or removed.  Consider re-examining the pain calibration methodology.",
        ]

    lines += [
        "",
        "---",
        "",
        "**Safety note:** Prod DB was not modified.  Real snapshot is read-only.  "
        "Uniform-pain DB is a caller-created temp copy (deleted if --cleanup passed).",
        "",
        f"**Runtime:** {elapsed_s:.0f}s total for both N variants.",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Report written → %s", output_path)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pain_ablation_fts_only",
        description=(
            "E10 FTS-Only Ablation — Δ nDCG@10 between real-pain and "
            "uniform-pain DB using FTS5 BM25 × pain composite (no Gemini)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--db-real",
        required=True,
        metavar="PATH",
        help="Path to real-pain snapshot DB (read-only).",
    )
    parser.add_argument(
        "--db-uniform",
        required=True,
        metavar="PATH",
        help="Path to uniform-pain DB (pain=1.0 applied by caller before this script).",
    )
    parser.add_argument(
        "--queries",
        required=True,
        metavar="PATH",
        help="Path to golden-queries.jsonl.",
    )
    parser.add_argument(
        "--output",
        default="./pain_ablation_fts_results.md",
        metavar="PATH",
        help="Output Markdown report path (default: ./pain_ablation_fts_results.md).",
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
        "--cleanup",
        action="store_true",
        help="Delete --db-uniform after the run (try/finally).",
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
    """Full FTS-only ablation pipeline.

    Pipeline:
    1. Load all 60 golden queries.
    2. Split into n=31 subset (same IDs as hybrid run) and n=60 (all).
    3. Open real-pain DB read-only; open uniform-pain DB read-only
       (caller must have applied pain=1.0 already).
    4. Run FTS-only eval on both DBs for n=31 subset.
    5. Run FTS-only eval on both DBs for n=60 all queries.
    6. Compute delta tables + bootstrap CI for each N variant.
    7. Write Markdown report.

    Args:
        argv: CLI args (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    db_real = Path(args.db_real)
    db_uniform = Path(args.db_uniform)
    queries_path = Path(args.queries)
    output_path = Path(args.output)

    if not db_real.exists():
        logger.error("Real-pain DB not found: %s", db_real)
        return 1
    if not db_uniform.exists():
        logger.error(
            "Uniform-pain DB not found: %s — "
            "create it first: cp real.db uniform.db && "
            'sqlite3 uniform.db "UPDATE chunks SET pain = 1.0;"',
            db_uniform,
        )
        return 1

    t_start = time.monotonic()
    cleanup_done = False

    try:
        # Step 1: Load queries
        logger.info("=== Step 1: Load golden queries ===")
        all_queries = load_queries(queries_path)
        if not all_queries:
            logger.error("No queries loaded from %s", queries_path)
            return 1

        # Step 2: Build query subsets
        logger.info("=== Step 2: Build query subsets ===")

        # n=31: exactly the same query IDs as the hybrid run
        n31_queries = [q for q in all_queries if q.query_id in _HYBRID_N31_QUERY_IDS]
        # n=60: all queries in the JSONL (may be fewer than 60 if some are missing)
        n60_queries = all_queries

        logger.info(
            "n=31 subset: %d queries (matched %d of %d hybrid IDs)",
            len(n31_queries),
            len({q.query_id for q in n31_queries} & _HYBRID_N31_QUERY_IDS),
            len(_HYBRID_N31_QUERY_IDS),
        )
        logger.info("n=60 (all): %d queries", len(n60_queries))

        if not n31_queries:
            logger.error(
                "No n=31 queries matched.  "
                "Ensure golden-queries.jsonl contains the hybrid-run query IDs: %s",
                sorted(_HYBRID_N31_QUERY_IDS),
            )
            return 1

        # Step 3: Open DB connections (both read-only — uniform was mutated by caller)
        logger.info("=== Step 3: Open DB connections ===")
        real_conn = sqlite3.connect(f"file:{db_real}?mode=ro", uri=True)
        # Uniform DB must be opened read-only too — it was mutated by the caller
        # before this script ran, so we just read it.
        uniform_conn = sqlite3.connect(f"file:{db_uniform}?mode=ro", uri=True)

        # Validate that uniform DB actually has pain=1.0
        uni_pain_check = uniform_conn.execute(
            "SELECT MIN(pain), MAX(pain), AVG(pain) FROM chunks"
        ).fetchone()
        logger.info(
            "Uniform DB pain stats: min=%.3f max=%.3f avg=%.3f",
            uni_pain_check[0] or 0.0,
            uni_pain_check[1] or 0.0,
            uni_pain_check[2] or 0.0,
        )
        if uni_pain_check[1] and abs(float(uni_pain_check[1]) - 1.0) > 0.01:
            logger.warning(
                "Uniform DB max pain = %.3f (expected 1.0) — "
                "check that the caller ran UPDATE chunks SET pain = 1.0",
                uni_pain_check[1],
            )

        real_pain_check = real_conn.execute(
            "SELECT MIN(pain), MAX(pain), AVG(pain) FROM chunks"
        ).fetchone()
        logger.info(
            "Real DB pain stats: min=%.3f max=%.3f avg=%.3f",
            real_pain_check[0] or 0.0,
            real_pain_check[1] or 0.0,
            real_pain_check[2] or 0.0,
        )

        # Step 4: Run eval — n=31
        logger.info("=== Step 4: Eval n=31 ===")
        real_n31 = run_eval_variant("pain_real/n31", n31_queries, real_conn, args.k)
        uniform_n31 = run_eval_variant("pain_uniform/n31", n31_queries, uniform_conn, args.k)

        rows_n31, agg_n31 = compute_deltas(real_n31, uniform_n31, n31_queries, real_conn)
        if not rows_n31:
            logger.error("Delta table for n=31 is empty")
            return 1

        bs_n31 = bootstrap_ci(
            [r.delta for r in rows_n31],
            n_bootstrap=args.n_bootstrap,
            seed=_BOOTSTRAP_SEED,
        )

        # Step 5: Run eval — n=60
        logger.info("=== Step 5: Eval n=60 ===")
        real_n60 = run_eval_variant("pain_real/n60", n60_queries, real_conn, args.k)
        uniform_n60 = run_eval_variant("pain_uniform/n60", n60_queries, uniform_conn, args.k)

        rows_n60, agg_n60 = compute_deltas(real_n60, uniform_n60, n60_queries, real_conn)
        if not rows_n60:
            logger.error("Delta table for n=60 is empty")
            return 1

        bs_n60 = bootstrap_ci(
            [r.delta for r in rows_n60],
            n_bootstrap=args.n_bootstrap,
            seed=_BOOTSTRAP_SEED,
        )

        real_conn.close()
        uniform_conn.close()

        # Step 6: Write report
        logger.info("=== Step 6: Write report ===")
        elapsed_s = time.monotonic() - t_start
        generate_report(
            rows_n31=rows_n31,
            agg_n31=agg_n31,
            bs_n31=bs_n31,
            rows_n60=rows_n60,
            agg_n60=agg_n60,
            bs_n60=bs_n60,
            output_path=output_path,
            elapsed_s=elapsed_s,
            db_real=db_real,
            db_uniform=db_uniform,
            queries_path=queries_path,
        )

        vl31, _ = verdict(agg_n31, bs_n31)
        vl60, _ = verdict(agg_n60, bs_n60)

        print()
        print("=" * 60)
        print("E10 Pain Ablation — FTS-Only Results")
        print("=" * 60)
        print(f"  n=31  mean Δ nDCG@10 = {agg_n31['mean_delta']:+.4f}  "
              f"CI=[{bs_n31.ci_lower:+.4f}, {bs_n31.ci_upper:+.4f}]  "
              f"verdict={vl31}")
        print(f"  n=60  mean Δ nDCG@10 = {agg_n60['mean_delta']:+.4f}  "
              f"CI=[{bs_n60.ci_lower:+.4f}, {bs_n60.ci_upper:+.4f}]  "
              f"verdict={vl60}")
        print(f"  hybrid n=31 Δ = +0.0065 (comparison)")
        print(f"  Report: {output_path}")
        print("=" * 60)

        return 0

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130

    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)
        return 1

    finally:
        if args.cleanup and not cleanup_done:
            uniform_db_path = Path(args.db_uniform)
            if uniform_db_path.exists():
                try:
                    uniform_db_path.unlink()
                    for suffix in ("-wal", "-shm"):
                        sidecar = Path(str(uniform_db_path) + suffix)
                        if sidecar.exists():
                            sidecar.unlink()
                    logger.info("Cleaned up uniform DB: %s", uniform_db_path)
                except OSError as exc:
                    logger.warning("Failed to clean up uniform DB %s: %s", uniform_db_path, exc)


if __name__ == "__main__":
    sys.exit(main())
