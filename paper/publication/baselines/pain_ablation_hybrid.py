"""
Pain Ablation — Hybrid Retrieval Variant (E10 addendum).

Computes Δ nDCG@10 between pain_real and pain_uniform using the full
nox-mem hybrid retrieval pipeline (FTS5 BM25 + Gemini semantic + RRF fusion)
rather than FTS5-only direct-DB mode used in E10 baseline.

Motivation
----------
The previous E10 run (pain_dimension_validator.py) used direct sqlite3 FTS5
search, which had zero recall on all 6 post-incident queries — the gold chunks
were never ranked because FTS5 BM25 alone could not surface them without
semantic re-ranking.  This script uses the real hybrid stack via the nox-mem
Node.js CLI (subprocess per query) so that semantic similarity (Gemini
embeddings) properly ranks the gold chunks.

Method
------
Two pre-built snapshots on VPS:
  pain_real    — nox-mem-pain-real.db    (original pain values, varied 0.2–1.0)
  pain_uniform — nox-mem-pain-uniform.db (pain = 1.0 for ALL chunks)

For each of the 6 post-incident queries (Q47, Q52, Q67, Q71, Q85, Q89):
  1. Run nox-mem hybrid search against pain_real snapshot → top-10 chunk IDs
  2. Run nox-mem hybrid search against pain_uniform snapshot → top-10 chunk IDs
  3. Compute nDCG@10 (binary relevance against expected_chunk_ids from golden JSONL)
  4. Δ = nDCG_real − nDCG_uniform

Bootstrap CI (10,000 resamples, seed=42) gives 95% CI on mean Δ.

Subprocess design
-----------------
Uses nox-search-json.mjs — a thin Node.js wrapper that calls searchHybrid()
directly and outputs JSON [{id, score, source_file, match_type}, ...].  The
wrapper lives at /root/.openclaw/paper-experiments/nox-search-json.mjs.

Safety
------
- Prod DB is NEVER touched.  Both snapshot DBs are in paper-experiments/.
- The script is read-only (no mutations to any DB).
- Cleanup of the uniform snapshot is the caller's responsibility (or passed via
  --cleanup flag which removes nox-mem-pain-uniform.db after the run).

Usage (on VPS)
--------------
  set -a; source /root/.openclaw/.env; set +a

  python3 pain_ablation_hybrid.py \\
    --db-real    /root/.openclaw/paper-experiments/nox-mem-pain-real.db \\
    --db-uniform /root/.openclaw/paper-experiments/nox-mem-pain-uniform.db \\
    --queries    /root/paper-experiments/golden-queries.jsonl \\
    --cli-bin    /root/.openclaw/paper-experiments/nox-search-json.mjs \\
    --output     /root/paper-experiments/pain_ablation_hybrid_results.md \\
    --cleanup

Output
------
  /root/paper-experiments/pain_ablation_hybrid_results.md
  (also printed to stdout as plain-text summary)
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import subprocess
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
logger = logging.getLogger("pain_ablation_hybrid")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_K = 10
_BOOTSTRAP_N = 10_000
_BOOTSTRAP_SEED = 42
_SIGNIFICANCE_ALPHA = 0.05
_DELTA_THRESHOLD = 0.05  # paper claim: Δ nDCG ≥ 0.05

# Post-incident query IDs that this experiment targets.
# Matches the IDs used in pain_dimension_validator.py + procedure spec.
_POST_INCIDENT_IDS: frozenset[int] = frozenset({47, 52, 67, 71, 85, 89})

# Post-incident keyword heuristics (fallback when query_id not available)
_POST_INCIDENT_KEYWORDS: list[str] = [
    "incident", "outage", "lesson", "pós-", "withopaudit", "reindex",
    "rsync", "183 entities", "lição", "falha", "crash", "recovery",
    "rollback", "downtime", "corruption", "apagou", "quebrou",
]

# Categories considered post-incident
_INCIDENT_CATEGORIES: frozenset[str] = frozenset({
    "incident", "lesson", "post-incident", "postmortem", "recovery",
    "outage", "temporal", "procedure", "decision", "security",
})

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class Query(NamedTuple):
    """A golden evaluation query."""

    query_id: int
    query_text: str
    expected_chunk_ids: list[int]
    difficulty: str | None
    category: str | None


class SearchHit(NamedTuple):
    """A single search result from the nox-mem hybrid stack."""

    chunk_id: int
    score: float
    source_file: str
    match_type: str | None


class QueryResult(NamedTuple):
    """Search outcome for one query × one variant."""

    query_id: int
    variant: str
    hits: list[SearchHit]
    ndcg_at_10: float
    duration_ms: int
    error: str | None


class DeltaRow(NamedTuple):
    """Per-query Δ nDCG between real and uniform pain variants."""

    query_id: int
    query_text: str
    category: str | None
    expected_chunk_ids: list[int]
    ndcg_real: float
    ndcg_uniform: float
    delta: float  # positive = pain-aware is better


class BootstrapResult(NamedTuple):
    """Bootstrap 95% CI on mean Δ nDCG."""

    mean_delta: float
    ci_lower: float
    ci_upper: float
    excludes_zero: bool
    n_queries: int


# ---------------------------------------------------------------------------
# Query loading + filtering
# ---------------------------------------------------------------------------


def load_queries(path: str | Path) -> list[Query]:
    """Load all golden queries from a JSONL file.

    Args:
        path: Path to golden_queries.jsonl.

    Returns:
        List of Query objects in file order.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If a required field is missing on a line.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Queries JSONL not found: {p}")

    queries: list[Query] = []
    with p.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                logger.warning("Skipping malformed JSON at line %d: %s", lineno, exc)
                continue

            query_text = obj.get("query")
            expected = obj.get("expected_chunk_ids")
            if query_text is None or expected is None:
                raise ValueError(
                    f"Line {lineno}: missing 'query' or 'expected_chunk_ids'"
                )

            queries.append(
                Query(
                    query_id=int(obj.get("query_id", lineno)),
                    query_text=str(query_text),
                    expected_chunk_ids=[int(cid) for cid in expected],
                    difficulty=obj.get("difficulty"),
                    category=obj.get("category"),
                )
            )

    logger.info("Loaded %d queries from %s", len(queries), p)
    return queries


def identify_post_incident_queries(queries: list[Query]) -> list[Query]:
    """Filter queries to the post-incident subset.

    A query is post-incident if ANY of:
    1. Its query_id is in the curated set {47, 52, 67, 71, 85, 89}.
    2. Its category matches an incident-type label.
    3. Its query_text contains at least one post-incident keyword.

    Args:
        queries: Full query list.

    Returns:
        Filtered post-incident query list preserving order.
    """
    result: list[Query] = []
    for q in queries:
        reasons: list[str] = []

        if q.query_id in _POST_INCIDENT_IDS:
            reasons.append(f"curated_id={q.query_id}")

        if q.category and q.category.lower().strip() in _INCIDENT_CATEGORIES:
            reasons.append(f"category={q.category}")

        text_lower = q.query_text.lower()
        matched = [kw for kw in _POST_INCIDENT_KEYWORDS if kw in text_lower]
        if matched:
            reasons.append(f"keywords={matched[:3]}")

        if reasons:
            logger.info(
                "Post-incident Q%d %r — %s",
                q.query_id,
                q.query_text[:50],
                "; ".join(reasons),
            )
            result.append(q)

    logger.info(
        "Identified %d post-incident queries out of %d total",
        len(result),
        len(queries),
    )
    return result


# ---------------------------------------------------------------------------
# nDCG metric
# ---------------------------------------------------------------------------


def ndcg_at_k(retrieved: list[int], gold: set[int], k: int = 10) -> float:
    """Compute nDCG@k with binary relevance.

    Args:
        retrieved: Ordered list of retrieved chunk IDs (rank 1 first).
        gold: Set of relevant chunk IDs.
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


# ---------------------------------------------------------------------------
# Hybrid search via subprocess (nox-search-json.mjs)
# ---------------------------------------------------------------------------


def run_hybrid_search(
    query_text: str,
    db_path: str,
    cli_bin: str,
    limit: int = _K,
    timeout_s: float = 60.0,
) -> tuple[list[SearchHit], str | None]:
    """Run nox-mem hybrid search via Node.js subprocess.

    Calls nox-search-json.mjs with NOX_DB_PATH set to db_path.  The Node
    script calls searchHybrid() directly and outputs a JSON array of results
    to stdout.  Stderr contains nox-mem internals (focus-shadow, WAL info)
    which are captured and discarded.

    Args:
        query_text: Natural-language query string.
        db_path: Absolute path to the snapshot DB (must be inside
            /root/.openclaw/ due to op-audit allowlist).
        cli_bin: Absolute path to nox-search-json.mjs.
        limit: Number of results to request.
        timeout_s: Subprocess timeout in seconds.

    Returns:
        Tuple of (hits, error_message).  If error_message is not None,
        hits will be an empty list.
    """
    env = {**os.environ, "NOX_DB_PATH": db_path}

    cmd = ["node", cli_bin, query_text, str(limit)]

    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return [], f"subprocess timed out after {timeout_s}s"
    except OSError as exc:
        return [], f"subprocess OS error: {exc}"

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.returncode != 0:
        logger.warning(
            "Search subprocess exited %d for query %r — stderr: %s",
            result.returncode,
            query_text[:60],
            stderr[-300:] if stderr else "(empty)",
        )
        return [], f"exit code {result.returncode}: {stderr[-200:]}"

    # The stdout contains a focus-shadow log line (starts with "[focus-shadow]")
    # followed by the JSON array on the next line (starts with "[{").
    # We search all lines for one that starts with "[{" to find the JSON array
    # unambiguously; failing that, we try the last "[" line (may be the array
    # when focus is set and the bracket pattern differs).
    json_line: str | None = None
    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("[{") or stripped == "[]":
            json_line = stripped
            break
    # Fallback: last line starting with "[" that is not a log line
    if json_line is None:
        for line in reversed(stdout.splitlines()):
            stripped = line.strip()
            if stripped.startswith("[") and not stripped.startswith("[focus") and not stripped.startswith("[INFO") and not stripped.startswith("[WARN"):
                json_line = stripped
                break

    if json_line is None:
        logger.warning(
            "No JSON array found in stdout for query %r — stdout: %s",
            query_text[:60],
            stdout[:300],
        )
        return [], "no JSON output from subprocess"

    try:
        raw_hits: list[dict[str, Any]] = json.loads(json_line)
    except json.JSONDecodeError as exc:
        return [], f"JSON parse error: {exc}"

    hits = [
        SearchHit(
            chunk_id=int(h.get("id", 0)),
            score=float(h.get("score", 0.0)),
            source_file=str(h.get("source_file", "")),
            match_type=h.get("match_type"),
        )
        for h in raw_hits
        if h.get("id")
    ]

    return hits, None


def eval_variant(
    variant: str,
    queries: list[Query],
    db_path: str,
    cli_bin: str,
    k: int = _K,
) -> dict[int, QueryResult]:
    """Evaluate all queries against one DB variant.

    Args:
        variant: Label ("pain_real" or "pain_uniform") for logging.
        queries: List of post-incident queries.
        db_path: Path to the snapshot DB for this variant.
        cli_bin: Path to nox-search-json.mjs.
        k: Retrieval cutoff.

    Returns:
        Dict mapping query_id to QueryResult.
    """
    results: dict[int, QueryResult] = {}
    logger.info(
        "Evaluating variant=%s db=%s (%d queries)",
        variant,
        db_path,
        len(queries),
    )

    for q in queries:
        t0 = time.monotonic()
        hits, error = run_hybrid_search(
            query_text=q.query_text,
            db_path=db_path,
            cli_bin=cli_bin,
            limit=k,
        )
        duration_ms = int((time.monotonic() - t0) * 1_000)

        retrieved_ids = [h.chunk_id for h in hits]
        score = ndcg_at_k(retrieved_ids, set(q.expected_chunk_ids), k=k)

        results[q.query_id] = QueryResult(
            query_id=q.query_id,
            variant=variant,
            hits=hits,
            ndcg_at_10=score,
            duration_ms=duration_ms,
            error=error,
        )

        logger.info(
            "Q%d [%s] nDCG@10=%.4f retrieved=%s expected=%s dur=%dms%s",
            q.query_id,
            variant,
            score,
            [h.chunk_id for h in hits[:5]],
            q.expected_chunk_ids[:5],
            duration_ms,
            f" ERROR={error}" if error else "",
        )

    mean_ndcg = (
        sum(r.ndcg_at_10 for r in results.values()) / len(results)
        if results
        else 0.0
    )
    logger.info(
        "Variant %s complete — %d/%d queries, mean nDCG@10=%.4f",
        variant,
        len(results),
        len(queries),
        mean_ndcg,
    )
    return results


# ---------------------------------------------------------------------------
# Delta computation
# ---------------------------------------------------------------------------


def compute_deltas(
    real_results: dict[int, QueryResult],
    uniform_results: dict[int, QueryResult],
    queries: list[Query],
) -> list[DeltaRow]:
    """Compute per-query Δ nDCG@10 (pain_real − pain_uniform).

    Args:
        real_results: Results from pain_real variant.
        uniform_results: Results from pain_uniform variant.
        queries: Post-incident query list.

    Returns:
        List of DeltaRow objects, one per query with results in both variants.
    """
    rows: list[DeltaRow] = []
    for q in queries:
        real = real_results.get(q.query_id)
        uniform = uniform_results.get(q.query_id)

        if real is None or uniform is None:
            logger.warning(
                "Q%d missing in one variant (real=%s uniform=%s) — skipping",
                q.query_id,
                real is not None,
                uniform is not None,
            )
            continue

        if real.error or uniform.error:
            logger.warning(
                "Q%d has errors (real=%s uniform=%s) — including with error flag",
                q.query_id,
                real.error,
                uniform.error,
            )

        delta = real.ndcg_at_10 - uniform.ndcg_at_10
        rows.append(
            DeltaRow(
                query_id=q.query_id,
                query_text=q.query_text,
                category=q.category,
                expected_chunk_ids=q.expected_chunk_ids,
                ndcg_real=real.ndcg_at_10,
                ndcg_uniform=uniform.ndcg_at_10,
                delta=delta,
            )
        )

    return rows


# ---------------------------------------------------------------------------
# Bootstrap CI
# ---------------------------------------------------------------------------


def bootstrap_ci(
    deltas: list[float],
    n_bootstrap: int = _BOOTSTRAP_N,
    seed: int = _BOOTSTRAP_SEED,
    alpha: float = _SIGNIFICANCE_ALPHA,
) -> BootstrapResult:
    """Compute bootstrap 95% CI on mean Δ nDCG via percentile method.

    Args:
        deltas: Per-query delta values (pain_real − pain_uniform).
        n_bootstrap: Number of bootstrap resamples.
        seed: Random seed for reproducibility.
        alpha: Significance level (0.05 → 95% CI).

    Returns:
        BootstrapResult with mean, CI bounds, and excludes_zero flag.

    Raises:
        ValueError: If deltas is empty.
    """
    if not deltas:
        raise ValueError("Cannot bootstrap empty deltas list")

    arr = np.array(deltas, dtype=np.float64)
    rng = np.random.default_rng(seed)
    n = len(arr)

    bootstrap_means = np.empty(n_bootstrap, dtype=np.float64)
    for i in range(n_bootstrap):
        sample = rng.choice(arr, size=n, replace=True)
        bootstrap_means[i] = sample.mean()

    ci_lower = float(np.percentile(bootstrap_means, 100 * alpha / 2))
    ci_upper = float(np.percentile(bootstrap_means, 100 * (1.0 - alpha / 2)))
    mean_delta = float(arr.mean())
    excludes_zero = ci_lower > 0.0 or ci_upper < 0.0

    logger.info(
        "Bootstrap CI (n_bootstrap=%d, seed=%d, n_queries=%d): "
        "mean=%.4f CI=[%.4f, %.4f] excludes_zero=%s",
        n_bootstrap,
        seed,
        n,
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
        n_queries=n,
    )


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------


def determine_verdict(
    mean_delta: float,
    ci: BootstrapResult,
) -> tuple[str, str]:
    """Determine the paper claim verdict.

    Three possible verdicts:
    - SIGNIFICANT: Δ ≥ 0.05 AND CI excludes 0
    - DIRECTIONAL: Δ > 0 but either below threshold or CI includes 0
    - NOT_SIGNIFICANT: Δ ≤ 0

    Args:
        mean_delta: Mean Δ nDCG@10 (pain_real − pain_uniform).
        ci: Bootstrap CI result.

    Returns:
        Tuple of (verdict_label, verdict_detail_string).
    """
    if mean_delta >= _DELTA_THRESHOLD and ci.excludes_zero:
        return (
            "SIGNIFICANT",
            f"Δ={mean_delta:+.3f} ≥ {_DELTA_THRESHOLD} threshold and "
            f"95% CI [{ci.ci_lower:+.3f}, {ci.ci_upper:+.3f}] excludes 0. "
            "Pain dimension is a statistically significant retrieval signal.",
        )
    elif mean_delta > 0.0:
        reasons = []
        if mean_delta < _DELTA_THRESHOLD:
            reasons.append(f"Δ below {_DELTA_THRESHOLD} threshold")
        if not ci.excludes_zero:
            reasons.append("95% CI includes 0")
        return (
            "DIRECTIONAL",
            f"Δ={mean_delta:+.3f} positive but {' and '.join(reasons)}. "
            "Directional evidence only — paper must downgrade claim.",
        )
    else:
        return (
            "NOT_SIGNIFICANT",
            f"Δ={mean_delta:+.3f} ≤ 0. Pain dimension does not improve "
            "retrieval on post-incident queries. Paper must revise this claim.",
        )


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(
    rows: list[DeltaRow],
    real_results: dict[int, QueryResult],
    uniform_results: dict[int, QueryResult],
    ci: BootstrapResult,
    output_path: Path,
    elapsed_s: float,
    db_real: str,
    db_uniform: str,
) -> str:
    """Write Markdown report and return verdict label.

    Args:
        rows: Per-query delta rows.
        real_results: Raw results from pain_real variant.
        uniform_results: Raw results from pain_uniform variant.
        ci: Bootstrap CI result.
        output_path: Path to write the report.
        elapsed_s: Total elapsed time.
        db_real: Path to the real pain snapshot.
        db_uniform: Path to the uniform pain snapshot.

    Returns:
        Verdict label string.
    """
    n = len(rows)
    mean_real = sum(r.ndcg_real for r in rows) / n if n else 0.0
    mean_uniform = sum(r.ndcg_uniform for r in rows) / n if n else 0.0
    mean_delta = sum(r.delta for r in rows) / n if n else 0.0

    improved = sum(1 for r in rows if r.delta > 0.0)
    degraded = sum(1 for r in rows if r.delta < 0.0)
    unchanged = sum(1 for r in rows if r.delta == 0.0)

    verdict_label, verdict_detail = determine_verdict(mean_delta, ci)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = [
        "# E10 Pain Ablation — Hybrid Retrieval Results",
        "",
        f"> Generated: {timestamp} | Runtime: {elapsed_s:.0f}s",
        f"> Script: `paper/publication/baselines/pain_ablation_hybrid.py`",
        "",
        "## Experiment Setup",
        "",
        "| Parameter | Value |",
        "|---|---|",
        f"| Method | Hybrid (FTS5 BM25 + Gemini semantic + RRF fusion) |",
        f"| Metric | nDCG@10 (binary relevance) |",
        f"| N queries | {n} post-incident (Q47, Q52, Q67, Q71, Q85, Q89) |",
        f"| pain_real DB | `{db_real}` |",
        f"| pain_uniform DB | `{db_uniform}` |",
        f"| Bootstrap | {n} deltas × {_BOOTSTRAP_N:,} resamples, seed={_BOOTSTRAP_SEED} |",
        f"| Significance threshold | Δ ≥ {_DELTA_THRESHOLD} AND CI excludes 0 |",
        "",
        "## Per-Query Results",
        "",
        "| Q | Query (truncated) | Category | Expected IDs | pain_real nDCG | uniform nDCG | Δ nDCG |",
        "|---|---|---|---|---|---|---|",
    ]

    for r in sorted(rows, key=lambda x: -x.delta):
        q_short = r.query_text[:55].replace("|", "&#124;")
        cat = r.category or "—"
        exp = str(r.expected_chunk_ids[:3]).replace("|", "&#124;") if r.expected_chunk_ids else "∅"
        delta_fmt = f"**{r.delta:+.3f}**" if abs(r.delta) > 0.001 else f"{r.delta:+.3f}"
        lines.append(
            f"| Q{r.query_id} | {q_short} | {cat} | {exp} "
            f"| {r.ndcg_real:.3f} | {r.ndcg_uniform:.3f} | {delta_fmt} |"
        )

    lines += [
        f"| **Mean** | | | | **{mean_real:.3f}** | **{mean_uniform:.3f}** | **{mean_delta:+.3f}** |",
        "",
        "## Top-5 Retrieved Chunks Per Query (pain_real)",
        "",
    ]

    for r in sorted(rows, key=lambda x: x.query_id):
        real_r = real_results.get(r.query_id)
        lines.append(f"### Q{r.query_id}: {r.query_text[:70]}")
        lines.append(f"Expected: {r.expected_chunk_ids}")
        if real_r and real_r.hits:
            for rank, h in enumerate(real_r.hits[:5], start=1):
                hit_flag = " ← GOLD" if h.chunk_id in set(r.expected_chunk_ids) else ""
                lines.append(
                    f"  {rank}. id={h.chunk_id} score={h.score:.2f} "
                    f"[{h.match_type}] {h.source_file[:60]}{hit_flag}"
                )
        else:
            lines.append("  (no results)")
        lines.append("")

    lines += [
        "## Aggregate Statistics",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Mean Δ nDCG@10 (pain_real − pain_uniform) | {mean_delta:+.4f} |",
        f"| Queries improved (Δ > 0) | {improved} / {n} |",
        f"| Queries degraded (Δ < 0) | {degraded} / {n} |",
        f"| Queries unchanged (Δ = 0) | {unchanged} / {n} |",
        f"| Baseline (pain_real) mean nDCG@10 | {mean_real:.4f} |",
        f"| Ablated (pain_uniform) mean nDCG@10 | {mean_uniform:.4f} |",
        "",
        "## Bootstrap Significance (95% CI)",
        "",
        f"- **Mean Δ nDCG@10:** {ci.mean_delta:+.4f}",
        f"- **95% CI:** [{ci.ci_lower:+.4f}, {ci.ci_upper:+.4f}]",
        f"- **Excludes zero:** {'YES' if ci.excludes_zero else 'NO'}",
        f"- **N queries:** {ci.n_queries}  |  **Resamples:** {_BOOTSTRAP_N:,}  |  "
        f"**Seed:** {_BOOTSTRAP_SEED}",
        "",
        "## Verdict",
        "",
        f"**{verdict_label}**",
        "",
        verdict_detail,
        "",
        "---",
        "",
        "## Interpretation for Paper §5.5",
        "",
    ]

    if verdict_label == "SIGNIFICANT":
        lines += [
            f"The pain dimension contributes Δ nDCG@10 = {mean_delta:+.4f} on post-incident "
            "queries under full hybrid retrieval (FTS5 + Gemini semantic + RRF).",
            "",
            "The 95% bootstrap CI excludes zero, supporting the paper claim that "
            "pain-aware salience is a statistically significant retrieval signal for "
            "incident-related queries.",
            "",
            "**Recommendation:** Include this result in §5.5 as confirmation of the "
            "pain dimension hypothesis. Cite bootstrap CI for statistical rigor.",
        ]
    elif verdict_label == "DIRECTIONAL":
        lines += [
            f"The pain dimension shows directional improvement (Δ nDCG@10 = {mean_delta:+.4f}) "
            "but statistical significance is not established at the n=6 scale.",
            "",
            "**Recommendation:** Report as 'directional evidence' in §5.5. Note that "
            "N=6 is underpowered for firm conclusions; a larger golden set would be "
            "required for statistical significance.",
        ]
    else:
        lines += [
            f"The pain dimension did not improve retrieval (Δ nDCG@10 = {mean_delta:+.4f}) "
            "under hybrid search on this query set.",
            "",
            "**Recommendation:** The paper §5.5 claim requires revision. Investigate "
            "whether (a) gold chunk IDs are correct, (b) semantic search dominates pain "
            "signal, or (c) the post-incident subset needs curation.",
        ]

    lines += [
        "",
        "**Safety note:** Both snapshots are read-only copies in "
        "`/root/.openclaw/paper-experiments/`. Prod DB was not modified.",
        "",
        f"**Compared to E10 (FTS5-only):** Previous run returned nDCG=0 for all "
        "queries — FTS5 alone could not surface gold chunks. Hybrid search with "
        "Gemini embeddings is the correct evaluation method.",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Report written → %s", output_path)
    return verdict_label


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        Configured ArgumentParser.
    """
    p = argparse.ArgumentParser(
        prog="pain_ablation_hybrid",
        description="E10 hybrid pain ablation: Δ nDCG@10 via real nox-mem hybrid stack.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--db-real",
        required=True,
        metavar="PATH",
        help="Path to pain_real snapshot DB (original pain values).",
    )
    p.add_argument(
        "--db-uniform",
        required=True,
        metavar="PATH",
        help="Path to pain_uniform snapshot DB (pain=1.0 for all chunks).",
    )
    p.add_argument(
        "--queries",
        required=True,
        metavar="PATH",
        help="Path to golden_queries.jsonl.",
    )
    p.add_argument(
        "--cli-bin",
        default="/root/.openclaw/paper-experiments/nox-search-json.mjs",
        metavar="PATH",
        help="Path to nox-search-json.mjs Node wrapper (default: %(default)s).",
    )
    p.add_argument(
        "--output",
        default="/root/paper-experiments/pain_ablation_hybrid_results.md",
        metavar="PATH",
        help="Output Markdown report path.",
    )
    p.add_argument(
        "--k",
        type=int,
        default=_K,
        metavar="N",
        help=f"Retrieval cutoff k (default: {_K}).",
    )
    p.add_argument(
        "--n-bootstrap",
        type=int,
        default=_BOOTSTRAP_N,
        metavar="N",
        help=f"Bootstrap resamples (default: {_BOOTSTRAP_N:,}).",
    )
    p.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete the pain_uniform snapshot DB after the run.",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return p


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Full ablation pipeline.

    Pipeline:
    1. Validate inputs (DB files, CLI binary, queries JSONL).
    2. Load queries → filter post-incident subset.
    3. Evaluate pain_real variant (hybrid search per query).
    4. Evaluate pain_uniform variant (hybrid search per query).
    5. Compute Δ nDCG@10 per query.
    6. Bootstrap 95% CI on mean Δ.
    7. Write Markdown report.
    8. (Optional) Cleanup uniform snapshot.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 success, 1 error.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    t_start = time.monotonic()

    # ------------------------------------------------------------------
    # Step 1: Validate inputs
    # ------------------------------------------------------------------
    logger.info("=== Step 1: Validate inputs ===")

    for label, path_str in [
        ("--db-real", args.db_real),
        ("--db-uniform", args.db_uniform),
        ("--queries", args.queries),
        ("--cli-bin", args.cli_bin),
    ]:
        p = Path(path_str)
        if not p.exists():
            logger.error("%s not found: %s", label, p)
            return 1

    logger.info(
        "Inputs validated: db_real=%s db_uniform=%s queries=%s cli=%s",
        args.db_real,
        args.db_uniform,
        args.queries,
        args.cli_bin,
    )

    # ------------------------------------------------------------------
    # Step 2: Load queries → filter post-incident subset
    # ------------------------------------------------------------------
    logger.info("=== Step 2: Load queries ===")
    try:
        all_queries = load_queries(args.queries)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Failed to load queries: %s", exc)
        return 1

    post_incident = identify_post_incident_queries(all_queries)
    if not post_incident:
        logger.error(
            "No post-incident queries found. Ensure query_ids 47/52/67/71/85/89 "
            "are present or queries have incident-type categories/keywords."
        )
        return 1

    logger.info(
        "Post-incident subset: %d queries — IDs: %s",
        len(post_incident),
        [q.query_id for q in post_incident],
    )

    # ------------------------------------------------------------------
    # Step 3: Evaluate pain_real variant
    # ------------------------------------------------------------------
    logger.info("=== Step 3: Evaluate pain_real variant ===")
    real_results = eval_variant(
        variant="pain_real",
        queries=post_incident,
        db_path=args.db_real,
        cli_bin=args.cli_bin,
        k=args.k,
    )

    if not real_results:
        logger.error("pain_real eval returned no results.")
        return 1

    # ------------------------------------------------------------------
    # Step 4: Evaluate pain_uniform variant
    # ------------------------------------------------------------------
    logger.info("=== Step 4: Evaluate pain_uniform variant ===")
    uniform_results = eval_variant(
        variant="pain_uniform",
        queries=post_incident,
        db_path=args.db_uniform,
        cli_bin=args.cli_bin,
        k=args.k,
    )

    if not uniform_results:
        logger.error("pain_uniform eval returned no results.")
        return 1

    # ------------------------------------------------------------------
    # Step 5: Compute per-query deltas
    # ------------------------------------------------------------------
    logger.info("=== Step 5: Compute deltas ===")
    rows = compute_deltas(real_results, uniform_results, post_incident)

    if not rows:
        logger.error("Delta table is empty — no matching results across variants.")
        return 1

    # ------------------------------------------------------------------
    # Step 6: Bootstrap CI
    # ------------------------------------------------------------------
    logger.info("=== Step 6: Bootstrap CI ===")
    deltas = [r.delta for r in rows]
    ci = bootstrap_ci(
        deltas=deltas,
        n_bootstrap=args.n_bootstrap,
        seed=_BOOTSTRAP_SEED,
    )

    # ------------------------------------------------------------------
    # Step 7: Write report
    # ------------------------------------------------------------------
    logger.info("=== Step 7: Write report ===")
    elapsed_s = time.monotonic() - t_start
    verdict_label = generate_report(
        rows=rows,
        real_results=real_results,
        uniform_results=uniform_results,
        ci=ci,
        output_path=Path(args.output),
        elapsed_s=elapsed_s,
        db_real=args.db_real,
        db_uniform=args.db_uniform,
    )

    # Print summary to stdout
    n = len(rows)
    mean_real = sum(r.ndcg_real for r in rows) / n
    mean_uniform = sum(r.ndcg_uniform for r in rows) / n
    mean_delta = ci.mean_delta

    print(f"\n{'='*60}")
    print("E10 Pain Ablation — Hybrid Retrieval Summary")
    print(f"{'='*60}")
    print(f"  Queries evaluated:    {n}")
    print(f"  pain_real mean nDCG:  {mean_real:.4f}")
    print(f"  pain_uniform mean:    {mean_uniform:.4f}")
    print(f"  Mean Δ nDCG@10:       {mean_delta:+.4f}")
    print(f"  Bootstrap 95% CI:     [{ci.ci_lower:+.4f}, {ci.ci_upper:+.4f}]")
    print(f"  CI excludes zero:     {'YES' if ci.excludes_zero else 'NO'}")
    print(f"  Verdict:              {verdict_label}")
    print(f"  Report:               {args.output}")
    print(f"  Runtime:              {elapsed_s:.1f}s")
    print()
    print("Per-query Δ nDCG:")
    for r in sorted(rows, key=lambda x: x.query_id):
        flag = "↑" if r.delta > 0 else ("↓" if r.delta < 0 else "=")
        print(
            f"  Q{r.query_id:3d} [{flag}] real={r.ndcg_real:.3f} "
            f"uniform={r.ndcg_uniform:.3f} Δ={r.delta:+.3f}  "
            f"({r.query_text[:40]})"
        )

    # ------------------------------------------------------------------
    # Step 8: Optional cleanup
    # ------------------------------------------------------------------
    if args.cleanup:
        uniform_path = Path(args.db_uniform)
        try:
            uniform_path.unlink()
            logger.info("Cleaned up uniform snapshot: %s", uniform_path)
            print(f"\nCleaned up: {uniform_path}")
        except OSError as exc:
            logger.warning("Failed to remove uniform snapshot: %s", exc)

    return 0


if __name__ == "__main__":
    sys.exit(main())
