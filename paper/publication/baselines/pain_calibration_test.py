"""
Pain Calibration Test — E10 follow-up.

Hypothesis
----------
The near-zero Δ observed in both hybrid and FTS-only E10 ablations is driven by
89% of the corpus having pain=0.2 (default), not by pain being a weak signal per se.
If pain were properly calibrated with varied spread, it would show a measurable
retrieval effect.

This script tests three artificial pain distributions against the real distribution
to answer: "Is the limiting factor calibration, or is pain fundamentally weak?"

Distributions tested
--------------------
  real    : Production distribution (89% pain=0.2, range 0.1–1.0)
  uniform : Random uniform 0.1–1.0 (equal spread, no semantic meaning)
  bimodal : 50% pain=0.1, 50% pain=1.0 (maximum contrast)
  logscale: Spread 0.01–10.0 on log scale (wider dynamic range)

All artificial distributions are applied to /tmp/ copies of the snapshot.
The original DB is opened read-only; no production data is modified.

Search method
-------------
FTS5 BM25 × pain multiplier (same as pain_ablation_fts_only.py):
    composite_score = (-bm25_score) * pain

This isolates the pain effect from Gemini semantic scoring.

Safety
------
- Real snapshot opened read-only via SQLite URI mode.
- Three temp DBs created in /tmp/, deleted in try/finally regardless of outcome.
- NOX_ALLOW_NO_SNAPSHOT not needed (no op-audit, pure read experiment).

Usage
-----
    python3 pain_calibration_test.py \\
        --db-real    /root/paper-experiments/nox-mem-snapshot-20260504-0616.db \\
        --queries    /root/paper-experiments/golden-queries.jsonl \\
        --output     /root/paper-experiments/E10-pain-calibration-test.md

Output
------
  Markdown report with distribution histograms, 5 pairwise comparisons,
  and H1/H2/H3 hypothesis verdicts.
  Printed summary: 4 distributions, top 3 Δ pairs, and §6.3 recommendation.
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
from dataclasses import dataclass, field
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
logger = logging.getLogger("pain_calibration_test")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_K = 10
_BOOTSTRAP_N = 10_000
_BOOTSTRAP_SEED = 42
_SIGNIFICANCE_ALPHA = 0.05
_DELTA_SIGNIFICANT = 0.05   # Δ ≥ this AND CI excludes 0 → SIGNIFICANT
_DELTA_DIRECTIONAL = 0.01   # Δ ≥ this → DIRECTIONAL (lower bar than E10)

# The 31-query subset from the hybrid ablation (for cross-run comparability).
_HYBRID_N31_QUERY_IDS: frozenset[int] = frozenset({
    46, 47, 48, 52, 55, 56, 57, 61, 63, 64, 66, 67, 70, 71,
    74, 75, 77, 78, 80, 83, 85, 87, 88, 89, 90, 91, 92, 97,
    100, 101, 102,
})

# Temp DB paths (always deleted in try/finally)
_TEMP_UNIFORM = "/tmp/nox-mem-pain-random-uniform.db"
_TEMP_BIMODAL = "/tmp/nox-mem-pain-bimodal.db"
_TEMP_LOGSCALE = "/tmp/nox-mem-pain-logscale.db"

# Distribution labels
DIST_REAL = "real"
DIST_UNIFORM = "uniform"
DIST_BIMODAL = "bimodal"
DIST_LOGSCALE = "logscale"

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
    """FTS-only search result for one query under one pain distribution."""

    query_id: int
    retrieved_chunk_ids: list[int]
    ndcg_at_10: float
    fts_hit_count: int


@dataclass
class DistributionStats:
    """Pain value distribution statistics for one DB variant."""

    label: str
    count: int
    min_pain: float
    max_pain: float
    avg_pain: float
    median_pain: float
    # Histogram: list of (bucket_label, count) sorted by bucket
    histogram: list[tuple[str, int]] = field(default_factory=list)


class BootstrapResult(NamedTuple):
    """Bootstrap 95% CI on mean Δ nDCG."""

    mean_delta: float
    ci_lower: float
    ci_upper: float
    excludes_zero: bool
    n_samples: int


@dataclass
class PairwiseComparison:
    """Result of comparing two pain distribution variants."""

    variant_a: str
    variant_b: str
    label: str          # e.g. "real vs uniform"
    mean_delta: float   # ndcg_a - ndcg_b
    bs: BootstrapResult
    verdict: str        # SIGNIFICANT / DIRECTIONAL / INSIGNIFICANT


# ---------------------------------------------------------------------------
# Query loading
# ---------------------------------------------------------------------------


def load_queries(queries_jsonl: Path) -> list[Query]:
    """Load golden queries from a JSONL file.

    Args:
        queries_jsonl: Path to golden-queries.jsonl.

    Returns:
        List of Query in file order.

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
# DB snapshot creation (artificial distributions)
# ---------------------------------------------------------------------------


def _sqlite3_rng_uniform_sql() -> str:
    """SQL expression for uniform random float in [0.1, 1.0] using SQLite RANDOM().

    SQLite RANDOM() returns a signed 64-bit integer uniformly distributed.
    We use modulo 10 to get integers 0–9, add 1 to get 1–10, divide by 10.0
    to get 0.1 steps in [0.1, 1.0].  This gives 10 discrete values at equal
    probability — the "random uniform 0.1–1.0" bucket distribution requested.
    """
    return "(ABS(RANDOM()) % 10 + 1) / 10.0"


def _sqlite3_bimodal_sql() -> str:
    """SQL expression for bimodal distribution: 50% pain=0.1, 50% pain=1.0."""
    return "CASE WHEN ABS(RANDOM()) % 2 = 0 THEN 0.1 ELSE 1.0 END"


def _sqlite3_logscale_sql() -> str:
    """SQL expression for log-scale spread: pain in [0.01, 10.0].

    Uses POWER(10.0, x) where x is linearly distributed in [-2, 1].
    ABS(RANDOM()) % 1000 gives integers 0–999; dividing by 333.0 gives
    [0.0, ~3.0]; subtracting 2.0 gives [-2.0, ~1.0].
    POWER(10, -2) = 0.01; POWER(10, 1) = 10.0.
    """
    return "POWER(10.0, (ABS(RANDOM()) % 1000) / 333.0 - 2.0)"


def create_artificial_db(
    source_db: Path,
    dest_path: str,
    distribution: str,
) -> Path:
    """Copy the real DB and apply an artificial pain distribution.

    Args:
        source_db: Path to the original real-pain snapshot DB.
        dest_path: Destination path for the temp DB.
        distribution: One of 'uniform', 'bimodal', 'logscale'.

    Returns:
        Path to the created temp DB.

    Raises:
        ValueError: If distribution label is unknown.
    """
    dist_sql_map: dict[str, str] = {
        DIST_UNIFORM: _sqlite3_rng_uniform_sql(),
        DIST_BIMODAL: _sqlite3_bimodal_sql(),
        DIST_LOGSCALE: _sqlite3_logscale_sql(),
    }
    if distribution not in dist_sql_map:
        raise ValueError(f"Unknown distribution: {distribution!r}. "
                         f"Must be one of: {list(dist_sql_map)}")

    pain_expr = dist_sql_map[distribution]

    logger.info(
        "Creating %s DB at %s (pain expr: %s)",
        distribution, dest_path, pain_expr,
    )
    shutil.copy2(str(source_db), dest_path)

    # Write directly — this is our own temp copy, not production
    conn = sqlite3.connect(dest_path)
    try:
        conn.execute(f"UPDATE chunks SET pain = {pain_expr}")
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        logger.info("Updated %d chunks with %s distribution", count, distribution)
    finally:
        conn.close()

    return Path(dest_path)


# ---------------------------------------------------------------------------
# Distribution statistics
# ---------------------------------------------------------------------------


def compute_distribution_stats(
    conn: sqlite3.Connection,
    label: str,
) -> DistributionStats:
    """Compute pain distribution statistics from a DB connection.

    Args:
        conn: Open sqlite3 connection.
        label: Human-readable label for this variant.

    Returns:
        DistributionStats with histogram and summary statistics.
    """
    row = conn.execute(
        "SELECT COUNT(*), MIN(pain), MAX(pain), AVG(pain) FROM chunks"
    ).fetchone()
    count, min_pain, max_pain, avg_pain = (
        int(row[0]),
        float(row[1] or 0.0),
        float(row[2] or 0.0),
        float(row[3] or 0.0),
    )

    # Median via SQLite approximation
    median_row = conn.execute(
        "SELECT pain FROM chunks ORDER BY pain LIMIT 1 OFFSET (SELECT COUNT(*)/2 FROM chunks)"
    ).fetchone()
    median_pain = float(median_row[0]) if median_row else 0.0

    # Build histogram: 12 buckets rounded to 1 decimal (cap at 10.0 for logscale)
    hist_rows = conn.execute(
        "SELECT ROUND(MIN(pain, 10.0), 1) AS bucket, COUNT(*) AS cnt "
        "FROM chunks GROUP BY bucket ORDER BY bucket LIMIT 20"
    ).fetchall()
    histogram = [(str(r[0]), int(r[1])) for r in hist_rows]

    logger.info(
        "Distribution [%s]: n=%d min=%.3f max=%.3f avg=%.3f median=%.3f",
        label, count, min_pain, max_pain, avg_pain, median_pain,
    )
    return DistributionStats(
        label=label,
        count=count,
        min_pain=min_pain,
        max_pain=max_pain,
        avg_pain=avg_pain,
        median_pain=median_pain,
        histogram=histogram,
    )


# ---------------------------------------------------------------------------
# FTS5 search helpers
# ---------------------------------------------------------------------------

_FTS5_TOKEN_RE = re.compile(r"""[^\s"'\(\)\[\]<>{}|:,;.!?]+""")


def escape_fts5_query(query_text: str) -> str:
    """Escape a natural-language string for safe FTS5 MATCH.

    Args:
        query_text: Raw query string (PT-BR or EN).

    Returns:
        FTS5-safe MATCH expression string.
    """
    tokens = _FTS5_TOKEN_RE.findall(query_text)
    if not tokens:
        return '""'
    return " ".join('"' + t + '"' for t in tokens[:20])


def fts_pain_search(
    conn: sqlite3.Connection,
    query_text: str,
    k: int = _DEFAULT_K,
) -> list[tuple[int, float]]:
    """FTS5 BM25 × pain composite search.

    Scoring: composite = (-bm25_score) * pain
    Identical formula to pain_ablation_fts_only.py for cross-run consistency.

    Args:
        conn: Open sqlite3 connection to any nox-mem snapshot.
        query_text: Natural-language query string.
        k: Number of results to return.

    Returns:
        List of (chunk_id, composite_score) descending by score. Empty on FTS error.
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
        return [(int(r[0]), float(r[1])) for r in rows]
    except sqlite3.OperationalError as exc:
        logger.warning("FTS5 error for query %r: %s", query_text[:60], exc)
        return []


# ---------------------------------------------------------------------------
# nDCG@k
# ---------------------------------------------------------------------------


def ndcg_at_k(retrieved: list[int], gold: set[int], k: int = _DEFAULT_K) -> float:
    """Binary-relevance nDCG@k.

    Args:
        retrieved: Ordered list of retrieved chunk IDs.
        gold: Set of relevant (gold) chunk IDs.
        k: Cutoff rank.

    Returns:
        nDCG@k in [0.0, 1.0].
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


def run_eval(
    variant_label: str,
    queries: list[Query],
    conn: sqlite3.Connection,
    k: int = _DEFAULT_K,
) -> dict[int, QueryResult]:
    """Evaluate all queries against one DB variant using FTS-only search.

    Args:
        variant_label: Label for logging.
        queries: Queries to evaluate.
        conn: Open read-only connection to the variant DB.
        k: Retrieval cutoff.

    Returns:
        Dict mapping query_id to QueryResult.
    """
    results: dict[int, QueryResult] = {}
    logger.info("Eval [%s] — %d queries", variant_label, len(queries))

    for q in queries:
        hits = fts_pain_search(conn, q.query_text, k=k)
        retrieved_ids = [doc_id for doc_id, _ in hits]
        score = ndcg_at_k(retrieved_ids, set(q.expected_chunk_ids), k=k)
        results[q.query_id] = QueryResult(
            query_id=q.query_id,
            retrieved_chunk_ids=retrieved_ids,
            ndcg_at_10=score,
            fts_hit_count=len(hits),
        )

    mean_ndcg = (
        sum(r.ndcg_at_10 for r in results.values()) / len(results)
        if results else 0.0
    )
    zero_recall = sum(1 for r in results.values() if r.fts_hit_count == 0)
    logger.info(
        "[%s] mean_nDCG=%.4f zero_recall=%d/%d",
        variant_label, mean_ndcg, zero_recall, len(results),
    )
    return results


# ---------------------------------------------------------------------------
# Bootstrap CI
# ---------------------------------------------------------------------------


def bootstrap_ci(
    deltas: list[float],
    n_bootstrap: int = _BOOTSTRAP_N,
    seed: int = _BOOTSTRAP_SEED,
    alpha: float = _SIGNIFICANCE_ALPHA,
) -> BootstrapResult:
    """Bootstrap 95% CI on mean Δ nDCG via percentile method.

    Args:
        deltas: Per-query Δ nDCG values.
        n_bootstrap: Number of resamples.
        seed: RNG seed for reproducibility.
        alpha: Significance level.

    Returns:
        BootstrapResult with CI bounds.

    Raises:
        ValueError: If deltas is empty.
    """
    if not deltas:
        raise ValueError("Cannot bootstrap empty delta list")

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
        "Bootstrap (n=%d seed=%d): mean=%.4f CI=[%.4f, %.4f] excl_zero=%s",
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
# Pairwise comparison
# ---------------------------------------------------------------------------


def compare_variants(
    label_a: str,
    label_b: str,
    results_a: dict[int, QueryResult],
    results_b: dict[int, QueryResult],
    queries: list[Query],
) -> PairwiseComparison:
    """Compare two distribution variants by computing Δ nDCG = A − B.

    Args:
        label_a: Label for variant A (e.g., 'real').
        label_b: Label for variant B (e.g., 'uniform').
        results_a: QueryResults from variant A.
        results_b: QueryResults from variant B.
        queries: Query list (must be same for both).

    Returns:
        PairwiseComparison with mean Δ, bootstrap CI, and verdict.
    """
    deltas: list[float] = []
    for q in queries:
        ra = results_a.get(q.query_id)
        rb = results_b.get(q.query_id)
        if ra is None or rb is None:
            logger.warning(
                "Q%d missing from %s=%s %s=%s — skipping",
                q.query_id, label_a, ra is not None, label_b, rb is not None,
            )
            continue
        deltas.append(ra.ndcg_at_10 - rb.ndcg_at_10)

    if not deltas:
        logger.error("No deltas computed for %s vs %s", label_a, label_b)
        bs = BootstrapResult(0.0, 0.0, 0.0, False, 0)
        mean_delta = 0.0
        v = "INSIGNIFICANT"
    else:
        bs = bootstrap_ci(deltas)
        mean_delta = bs.mean_delta
        if abs(mean_delta) < _DELTA_DIRECTIONAL:
            v = "INSIGNIFICANT"
        elif abs(mean_delta) >= _DELTA_SIGNIFICANT and bs.excludes_zero:
            v = "SIGNIFICANT"
        else:
            v = "DIRECTIONAL"

    pair_label = f"{label_a} vs {label_b}"
    logger.info(
        "Comparison [%s]: Δ=%.4f CI=[%.4f, %.4f] verdict=%s",
        pair_label, mean_delta, bs.ci_lower, bs.ci_upper, v,
    )
    return PairwiseComparison(
        variant_a=label_a,
        variant_b=label_b,
        label=pair_label,
        mean_delta=mean_delta,
        bs=bs,
        verdict=v,
    )


# ---------------------------------------------------------------------------
# Hypothesis verdicts
# ---------------------------------------------------------------------------


def h1_verdict(
    real_vs_uniform: PairwiseComparison,
    real_vs_bimodal: PairwiseComparison,
    real_vs_logscale: PairwiseComparison,
) -> tuple[str, str]:
    """H1: Real pain (89% default) shows ~0 Δ vs all artificial spreads.

    CONFIRMED if all 3 baseline-vs-artificial Δ are near-zero (< 0.01)
    with CIs spanning zero — meaning pain calibration alone drives the null.

    Args:
        real_vs_uniform: Comparison real vs random uniform.
        real_vs_bimodal: Comparison real vs bimodal.
        real_vs_logscale: Comparison real vs log-scale.

    Returns:
        Tuple of (verdict_label, explanation).
    """
    all_insignificant = all(
        c.verdict == "INSIGNIFICANT"
        for c in (real_vs_uniform, real_vs_bimodal, real_vs_logscale)
    )
    max_abs_delta = max(
        abs(c.mean_delta)
        for c in (real_vs_uniform, real_vs_bimodal, real_vs_logscale)
    )

    if all_insignificant:
        return (
            "CONFIRMED",
            f"All 3 real-vs-artificial comparisons are INSIGNIFICANT "
            f"(max |Δ|={max_abs_delta:.4f}). "
            "Real pain distribution is indistinguishable from artificial spreads "
            "in FTS-only mode. Root cause: 90%+ zero-recall queries mean FTS cannot "
            "surface gold chunks regardless of pain distribution — pain is irrelevant "
            "when recall is zero."
        )
    else:
        significant_pairs = [
            c.label for c in (real_vs_uniform, real_vs_bimodal, real_vs_logscale)
            if c.verdict != "INSIGNIFICANT"
        ]
        return (
            "REFUTED",
            f"Some real-vs-artificial pairs show non-trivial Δ: {significant_pairs}. "
            f"Max |Δ|={max_abs_delta:.4f}. "
            "Real pain distribution is not equivalent to artificial spreads — "
            "calibration may matter in the FTS-retrievable query subset."
        )


def h2_verdict(
    uniform_vs_bimodal: PairwiseComparison,
) -> tuple[str, str]:
    """H2: Bimodal (max contrast) shows MORE Δ than uniform → calibration matters.

    CONFIRMED if bimodal significantly outperforms uniform (Δ > directional threshold).

    Args:
        uniform_vs_bimodal: Comparison uniform vs bimodal (bimodal in B slot,
            so positive Δ means uniform > bimodal; we check |Δ| > threshold).

    Returns:
        Tuple of (verdict_label, explanation).
    """
    delta_bimodal_vs_uniform = -uniform_vs_bimodal.mean_delta  # bimodal - uniform
    is_better = delta_bimodal_vs_uniform > _DELTA_DIRECTIONAL
    is_significant = (
        delta_bimodal_vs_uniform >= _DELTA_SIGNIFICANT
        and uniform_vs_bimodal.bs.excludes_zero
    )

    if is_significant:
        return (
            "CONFIRMED",
            f"Bimodal significantly outperforms uniform: Δ={delta_bimodal_vs_uniform:+.4f} "
            f"CI=[{-uniform_vs_bimodal.bs.ci_upper:+.4f}, {-uniform_vs_bimodal.bs.ci_lower:+.4f}]. "
            "Maximum contrast (0.1/1.0 split) provides measurable calibration benefit."
        )
    elif is_better:
        return (
            "DIRECTIONAL",
            f"Bimodal is directionally better than uniform: Δ={delta_bimodal_vs_uniform:+.4f}, "
            "but CI includes zero — not statistically significant. "
            "Calibration may matter in the FTS-recall subset, but N is insufficient."
        )
    else:
        return (
            "REFUTED",
            f"Bimodal does not outperform uniform: Δ={delta_bimodal_vs_uniform:+.4f}. "
            "Maximum contrast calibration provides no measurable benefit over random uniform. "
            "Pain signal is fundamentally weak in FTS-only mode regardless of spread."
        )


def h3_verdict(
    uniform_vs_logscale: PairwiseComparison,
) -> tuple[str, str]:
    """H3: Log-scale (wider range) shows MORE Δ than uniform → dynamic range matters.

    CONFIRMED if log-scale significantly outperforms uniform.

    Args:
        uniform_vs_logscale: Comparison uniform vs log-scale.

    Returns:
        Tuple of (verdict_label, explanation).
    """
    delta_log_vs_uniform = -uniform_vs_logscale.mean_delta  # logscale - uniform
    is_better = delta_log_vs_uniform > _DELTA_DIRECTIONAL
    is_significant = (
        delta_log_vs_uniform >= _DELTA_SIGNIFICANT
        and uniform_vs_logscale.bs.excludes_zero
    )

    if is_significant:
        return (
            "CONFIRMED",
            f"Log-scale significantly outperforms uniform: Δ={delta_log_vs_uniform:+.4f} "
            f"CI=[{-uniform_vs_logscale.bs.ci_upper:+.4f}, {-uniform_vs_logscale.bs.ci_lower:+.4f}]. "
            "Wider dynamic range (0.01–10.0) provides measurable ranking benefit."
        )
    elif is_better:
        return (
            "DIRECTIONAL",
            f"Log-scale is directionally better than uniform: Δ={delta_log_vs_uniform:+.4f}, "
            "but not statistically significant. Dynamic range may help in recall subset."
        )
    else:
        return (
            "REFUTED",
            f"Log-scale does not outperform uniform: Δ={delta_log_vs_uniform:+.4f}. "
            "Wider dynamic range (0.01–10.0) provides no measurable benefit over "
            "uniform 0.1–1.0. Dynamic range is not the limiting factor."
        )


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def _format_histogram(stats: DistributionStats) -> str:
    """Format a compact histogram row for the report table."""
    top_buckets = stats.histogram[:8]
    parts = [f"{b}×{c}" for b, c in top_buckets]
    if len(stats.histogram) > 8:
        parts.append("...")
    return " | ".join(parts)


def generate_report(
    dist_stats: dict[str, DistributionStats],
    comparisons: list[PairwiseComparison],
    h1: tuple[str, str],
    h2: tuple[str, str],
    h3: tuple[str, str],
    output_path: Path,
    elapsed_s: float,
    db_real: Path,
    queries_path: Path,
    n_queries: int,
    n31_queries: int,
    all_results: dict[str, dict[int, QueryResult]],
    all_queries: list[Query],
) -> None:
    """Write the full Markdown report.

    Args:
        dist_stats: Distribution statistics per variant label.
        comparisons: All 5 pairwise comparisons.
        h1: H1 verdict tuple.
        h2: H2 verdict tuple.
        h3: H3 verdict tuple.
        output_path: Path to write the report.
        elapsed_s: Total wall-clock seconds.
        db_real: Path to the real DB.
        queries_path: Path to golden queries JSONL.
        n_queries: Total queries evaluated.
        n31_queries: Number of n=31 subset queries matched.
        all_results: Dict of label → {query_id: QueryResult}.
        all_queries: Full query list.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = [
        "# Pain Calibration Test — E10 follow-up",
        "",
        f"> Generated: {timestamp} | Runtime: {elapsed_s:.0f}s",
        "> Script: `paper/publication/baselines/pain_calibration_test.py`",
        "",
        "## Hypothesis",
        "",
        "If 89% pain=default is the limiting factor, artificial spread should show",
        "measurable Δ. Specifically:",
        "",
        "- **H1**: Real pain (89% default) shows ~0 Δ vs ALL artificial spreads",
        "  → CONFIRMED if calibration is the root cause of null effect",
        "- **H2**: Bimodal (0.1/1.0 max contrast) > uniform → calibration spread matters",
        "- **H3**: Log-scale (0.01–10.0) > uniform → dynamic range matters",
        "",
        "## Setup",
        "",
        "| Parameter | Value |",
        "|---|---|",
        "| Mode | FTS5 BM25 × pain ONLY (no Gemini, no RRF) |",
        "| Scoring | composite = (−bm25_score) × pain |",
        f"| Real DB | `{db_real.name}` (read-only) |",
        "| Temp DBs | 3 copies in /tmp/, deleted after run |",
        f"| Queries | `{queries_path.name}` ({n_queries} total) |",
        f"| Bootstrap | {_BOOTSTRAP_N:,} resamples, seed={_BOOTSTRAP_SEED} |",
        f"| Significance threshold | Δ ≥ {_DELTA_SIGNIFICANT} AND CI excludes 0 |",
        f"| Directional threshold | Δ ≥ {_DELTA_DIRECTIONAL} |",
        "",
        "## Distributions tested",
        "",
        "| Distribution | N chunks | Min | Max | Avg | Median | Top histogram buckets |",
        "|---|---|---|---|---|---|---|",
    ]

    for label in (DIST_REAL, DIST_UNIFORM, DIST_BIMODAL, DIST_LOGSCALE):
        s = dist_stats.get(label)
        if s is None:
            continue
        hist_str = _format_histogram(s)
        lines.append(
            f"| {label} | {s.count:,} "
            f"| {s.min_pain:.3f} | {s.max_pain:.3f} "
            f"| {s.avg_pain:.3f} | {s.median_pain:.3f} "
            f"| {hist_str} |"
        )

    lines += [
        "",
        "## Pairwise comparisons",
        "",
        "| Comparison | Mean Δ nDCG@10 | 95% CI lower | 95% CI upper | CI excl. 0 | Verdict |",
        "|---|---|---|---|---|---|",
    ]

    for c in comparisons:
        lines.append(
            f"| {c.label} "
            f"| {c.mean_delta:+.4f} "
            f"| {c.bs.ci_lower:+.4f} "
            f"| {c.bs.ci_upper:+.4f} "
            f"| {'YES' if c.bs.excludes_zero else 'NO'} "
            f"| **{c.verdict}** |"
        )

    lines += [
        "",
        "## Per-variant nDCG@10 (n=60)",
        "",
        "| Distribution | Mean nDCG@10 | FTS recall rate |",
        "|---|---|---|",
    ]

    for label in (DIST_REAL, DIST_UNIFORM, DIST_BIMODAL, DIST_LOGSCALE):
        results = all_results.get(label, {})
        if not results:
            continue
        mean_ndcg = sum(r.ndcg_at_10 for r in results.values()) / len(results)
        recall_rate = sum(1 for r in results.values() if r.fts_hit_count > 0) / len(results)
        lines.append(
            f"| {label} | {mean_ndcg:.4f} | {recall_rate:.1%} |"
        )

    # Top queries where FTS actually returned results (most informative)
    lines += [
        "",
        "## Queries with FTS recall (the only ones where pain can matter)",
        "",
        "| Q | Query | Category | real nDCG | uniform nDCG | bimodal nDCG | logscale nDCG |",
        "|---|---|---|---|---|---|---|",
    ]

    real_results = all_results.get(DIST_REAL, {})
    recall_queries = [
        q for q in all_queries
        if real_results.get(q.query_id, QueryResult(0, [], 0.0, 0)).fts_hit_count > 0
    ]
    for q in recall_queries[:20]:  # max 20 rows
        q_short = q.query_text[:50].replace("|", "&#124;")
        cat = q.category or "—"
        scores = []
        for label in (DIST_REAL, DIST_UNIFORM, DIST_BIMODAL, DIST_LOGSCALE):
            r = all_results.get(label, {}).get(q.query_id)
            scores.append(f"{r.ndcg_at_10:.3f}" if r else "—")
        lines.append(
            f"| Q{q.query_id} | {q_short} | {cat} | {' | '.join(scores)} |"
        )

    if not recall_queries:
        lines.append("| *No FTS recall in real DB* | | | | | | |")

    lines += [
        "",
        "## Verdict",
        "",
        f"### H1 [{h1[0]}]",
        "",
        h1[1],
        "",
        f"### H2 [{h2[0]}]",
        "",
        h2[1],
        "",
        f"### H3 [{h3[0]}]",
        "",
        h3[1],
        "",
        "## Implication for paper §6.3 future work",
        "",
    ]

    # Choose implication based on combined verdict
    h1_status, h2_status, h3_status = h1[0], h2[0], h3[0]

    if h1_status == "CONFIRMED" and h2_status in ("CONFIRMED", "DIRECTIONAL"):
        lines += [
            "**Calibration spread is the limiting factor** (H1 confirmed, H2 confirmed/directional).",
            "",
            "> §6.3 recommended framing: *'Current pain calibration assigns 89% of chunks",
            "> the default value 0.2, collapsing the signal to near-zero variance.",
            "> A bimodal or log-scale recalibration would materially improve the",
            "> pain dimension's discriminating power. We leave principled pain",
            "> annotation (e.g., incident severity labeling, user feedback loops)",
            "> to future work.'*",
            "",
            "**Production recommendation:** If Toto wants pain to function as a real",
            "retrieval signal, recalibrate via one of:",
            "1. Bimodal: assign pain=1.0 to all error/incident/critical chunks, pain=0.1 to all others",
            "2. Log-scale: severity tiers (trivial=0.1, normal=0.3, warning=0.6, error=1.0, critical=3.0)",
        ]
    elif h1_status == "CONFIRMED" and h2_status == "REFUTED" and h3_status == "REFUTED":
        lines += [
            "**Pain dimension is fundamentally weak signal in FTS-only retrieval** (H1 confirmed,",
            "H2+H3 refuted). Even with maximum contrast or wide dynamic range, pain does not",
            "move the needle. Root cause: FTS zero-recall rate (~92%) means gold chunks are",
            "never surfaced for re-ranking — the pain multiplier has no candidates to discriminate.",
            "",
            "> §6.3 recommended framing: *'The pain dimension's retrieval contribution is",
            "> constrained by BM25 recall: when gold chunks are absent from FTS candidates,",
            "> no pain calibration can rescue ranking. The pain signal is most relevant",
            "> in hybrid mode where semantic recall surfaces candidates for BM25 re-ranking.",
            "> Future work should evaluate pain contribution in the semantic-only regime,",
            "> where all chunks are candidates.'*",
            "",
            "**Production recommendation:** Do NOT recalibrate pain values in prod for retrieval",
            "gain — the bottleneck is FTS recall, not pain spread. Pain values can still serve",
            "their original purpose (salience formula for attention/retention), just not",
            "as a standalone BM25 re-ranker.",
        ]
    else:
        lines += [
            f"**Mixed results** (H1={h1_status}, H2={h2_status}, H3={h3_status}).",
            "",
            "> §6.3 recommended framing: *'Pain calibration shows mixed evidence.",
            "> Artificial spread experiments suggest the signal is sensitive to",
            "> distribution shape but the effect is constrained by FTS recall limits.",
            "> Future work should co-optimize recall (BM25 query expansion or",
            "> denser indexing) with pain re-calibration.'*",
        ]

    lines += [
        "",
        "---",
        "",
        "**Safety:** Prod DB not modified. Real snapshot opened read-only.",
        "3 temp DBs created in /tmp/ and deleted (try/finally).",
        f"**Runtime:** {elapsed_s:.0f}s",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Report written → %s", output_path)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pain_calibration_test",
        description=(
            "E10 Pain Calibration Test — "
            "artificial pain spread ablation to test H1/H2/H3."
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
        "--queries",
        required=True,
        metavar="PATH",
        help="Path to golden-queries.jsonl.",
    )
    parser.add_argument(
        "--output",
        default="./E10-pain-calibration-test.md",
        metavar="PATH",
        help="Output Markdown report path.",
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
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Full pain calibration test pipeline.

    Steps:
        1. Load golden queries.
        2. Create 3 artificial-pain temp DBs (uniform / bimodal / logscale).
        3. Collect distribution statistics for all 4 variants.
        4. Run FTS-only eval for all 4 variants.
        5. Compute 5 pairwise comparisons with bootstrap CI.
        6. Evaluate H1 / H2 / H3 hypotheses.
        7. Write Markdown report.
        8. Delete temp DBs (try/finally).

    Args:
        argv: CLI args (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 success, 1 error.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    db_real = Path(args.db_real)
    queries_path = Path(args.queries)
    output_path = Path(args.output)

    if not db_real.exists():
        logger.error("Real DB not found: %s", db_real)
        return 1

    temp_dbs: list[str] = [_TEMP_UNIFORM, _TEMP_BIMODAL, _TEMP_LOGSCALE]
    t_start = time.monotonic()

    try:
        # ------------------------------------------------------------------ #
        # Step 1: Load queries                                                 #
        # ------------------------------------------------------------------ #
        logger.info("=== Step 1: Load queries ===")
        all_queries = load_queries(queries_path)
        if not all_queries:
            logger.error("No queries loaded")
            return 1

        n31_queries = [q for q in all_queries if q.query_id in _HYBRID_N31_QUERY_IDS]
        logger.info("Loaded %d total queries, %d in n=31 subset", len(all_queries), len(n31_queries))

        # ------------------------------------------------------------------ #
        # Step 2: Create artificial-pain DBs                                   #
        # ------------------------------------------------------------------ #
        logger.info("=== Step 2: Create artificial-pain DBs ===")
        db_paths: dict[str, Path] = {
            DIST_REAL: db_real,
        }

        for dist_label, tmp_path in (
            (DIST_UNIFORM, _TEMP_UNIFORM),
            (DIST_BIMODAL, _TEMP_BIMODAL),
            (DIST_LOGSCALE, _TEMP_LOGSCALE),
        ):
            db_paths[dist_label] = create_artificial_db(db_real, tmp_path, dist_label)

        # ------------------------------------------------------------------ #
        # Step 3: Distribution statistics                                       #
        # ------------------------------------------------------------------ #
        logger.info("=== Step 3: Collect distribution stats ===")
        dist_stats: dict[str, DistributionStats] = {}
        conns: dict[str, sqlite3.Connection] = {}

        for label, path in db_paths.items():
            if label == DIST_REAL:
                conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            else:
                conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            conns[label] = conn
            dist_stats[label] = compute_distribution_stats(conn, label)

        # ------------------------------------------------------------------ #
        # Step 4: FTS-only eval for all 4 variants (n=60 full set)             #
        # ------------------------------------------------------------------ #
        logger.info("=== Step 4: Eval all 4 variants ===")
        all_results: dict[str, dict[int, QueryResult]] = {}

        for label, conn in conns.items():
            all_results[label] = run_eval(label, all_queries, conn, k=args.k)

        # ------------------------------------------------------------------ #
        # Step 5: Pairwise comparisons                                          #
        # ------------------------------------------------------------------ #
        logger.info("=== Step 5: Pairwise comparisons ===")

        real_vs_uniform = compare_variants(
            DIST_REAL, DIST_UNIFORM,
            all_results[DIST_REAL], all_results[DIST_UNIFORM],
            all_queries,
        )
        real_vs_bimodal = compare_variants(
            DIST_REAL, DIST_BIMODAL,
            all_results[DIST_REAL], all_results[DIST_BIMODAL],
            all_queries,
        )
        real_vs_logscale = compare_variants(
            DIST_REAL, DIST_LOGSCALE,
            all_results[DIST_REAL], all_results[DIST_LOGSCALE],
            all_queries,
        )
        uniform_vs_bimodal = compare_variants(
            DIST_UNIFORM, DIST_BIMODAL,
            all_results[DIST_UNIFORM], all_results[DIST_BIMODAL],
            all_queries,
        )
        uniform_vs_logscale = compare_variants(
            DIST_UNIFORM, DIST_LOGSCALE,
            all_results[DIST_UNIFORM], all_results[DIST_LOGSCALE],
            all_queries,
        )

        comparisons = [
            real_vs_uniform,
            real_vs_bimodal,
            real_vs_logscale,
            uniform_vs_bimodal,
            uniform_vs_logscale,
        ]

        # ------------------------------------------------------------------ #
        # Step 6: Hypothesis verdicts                                           #
        # ------------------------------------------------------------------ #
        logger.info("=== Step 6: Hypothesis verdicts ===")
        h1 = h1_verdict(real_vs_uniform, real_vs_bimodal, real_vs_logscale)
        h2 = h2_verdict(uniform_vs_bimodal)
        h3 = h3_verdict(uniform_vs_logscale)

        logger.info("H1: %s | H2: %s | H3: %s", h1[0], h2[0], h3[0])

        # Close connections before writing report
        for conn in conns.values():
            conn.close()

        # ------------------------------------------------------------------ #
        # Step 7: Write report                                                  #
        # ------------------------------------------------------------------ #
        logger.info("=== Step 7: Write report ===")
        elapsed_s = time.monotonic() - t_start
        generate_report(
            dist_stats=dist_stats,
            comparisons=comparisons,
            h1=h1,
            h2=h2,
            h3=h3,
            output_path=output_path,
            elapsed_s=elapsed_s,
            db_real=db_real,
            queries_path=queries_path,
            n_queries=len(all_queries),
            n31_queries=len(n31_queries),
            all_results=all_results,
            all_queries=all_queries,
        )

        # ------------------------------------------------------------------ #
        # Print compact summary                                                 #
        # ------------------------------------------------------------------ #
        print()
        print("=" * 70)
        print("Pain Calibration Test — E10 follow-up")
        print("=" * 70)
        print("Distributions (mean pain):")
        for label in (DIST_REAL, DIST_UNIFORM, DIST_BIMODAL, DIST_LOGSCALE):
            s = dist_stats.get(label)
            if s:
                print(f"  {label:10s}: avg={s.avg_pain:.3f} median={s.median_pain:.3f} "
                      f"range=[{s.min_pain:.3f}, {s.max_pain:.3f}]")

        print()
        print("Pairwise Δ nDCG@10 (sorted by |Δ|):")
        for c in sorted(comparisons, key=lambda x: -abs(x.mean_delta)):
            print(
                f"  {c.label:30s}: Δ={c.mean_delta:+.4f} "
                f"CI=[{c.bs.ci_lower:+.4f}, {c.bs.ci_upper:+.4f}] "
                f"{'excl0' if c.bs.excludes_zero else '    '} "
                f"→ {c.verdict}"
            )

        print()
        print(f"H1 [{h1[0]:9s}]: {h1[1][:80]}")
        print(f"H2 [{h2[0]:9s}]: {h2[1][:80]}")
        print(f"H3 [{h3[0]:9s}]: {h3[1][:80]}")
        print()
        print(f"Report: {output_path}")
        print("=" * 70)

        return 0

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130

    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)
        return 1

    finally:
        # ------------------------------------------------------------------ #
        # Step 8: Cleanup temp DBs (always, regardless of success/failure)      #
        # ------------------------------------------------------------------ #
        logger.info("=== Step 8: Cleanup temp DBs ===")
        for tmp_path in temp_dbs:
            for suffix in ("", "-wal", "-shm"):
                p = Path(tmp_path + suffix)
                if p.exists():
                    try:
                        p.unlink()
                        logger.info("Deleted temp DB: %s", p)
                    except OSError as exc:
                        logger.warning("Failed to delete %s: %s", p, exc)


if __name__ == "__main__":
    sys.exit(main())
