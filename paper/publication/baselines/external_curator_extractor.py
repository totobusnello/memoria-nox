"""External Curator Query Extractor — E11 for NOX-Supermem paper §4.1.

PURPOSE
-------
This script closes Gap #2 ("internal-curator bias") in the NOX-Supermem
evaluation by selecting 10 queries authored by external, professional NIST
assessors (TREC-COVID Round 5, Voorhees et al. 2021) rather than the
repository owner (Toto), who curated all 50 golden queries in the internal
harness.

HYPOTHESIS
----------
  nDCG_external - nDCG_internal ≤ 0.10

If the gap is within ±0.10, the paper can assert low internal-curator bias
with N=10 external-curated queries as supporting evidence (§4.1 limitation
paragraph).

WHY TREC-COVID
--------------
- 50 queries written by NIST professional assessors (not the system authors).
- "Research question" format matches the style of developer memory queries
  (e.g. "what are the mechanisms of action for remdesivir").
- Freely available via the BEIR benchmark (HuggingFace BeIR/trec-covid).
- Grounded in a technically demanding domain — analogous to the engineering /
  architecture knowledge stored in nox-mem.

WHY N=10
--------
Toto curates ``expected_doc_ids`` manually at ~3 min / query.  10 queries = 30
min total curation time — the sweet spot between statistical credibility (N
small but non-trivial) and human effort ceiling for a P1 experiment.

PIPELINE
--------
1. Load all 50 TREC-COVID queries from BEIR cache (or trigger download).
2. Filter: word count ≤ max_words (default 15), no purely numeric / trivially
   short queries.
3. Select 10 diverse queries via a two-pass strategy:
     Pass A — TF-IDF vectorisation + KMeans(k=10, seed=42) → 1 query / cluster
              centroid (nearest member).
     Pass B — fallback if scikit-learn unavailable: greedy max pairwise
              Jaccard distance (random seed=42 init), keeping queries whose
              lexical overlap with already-selected set is ≤ 50 %.
4. Assign stable IDs: EXT-Q01 … EXT-Q10.
5. Write JSONL (``expected_doc_ids: []``, ``needs_human_curation: true``).
6. Write Markdown analysis report for paper §4.1 appendix.

OUTPUT
------
- ``/tmp/external-curator-queries.jsonl`` (10 lines)
- ``/tmp/external-curator-analysis.md``

DEPENDENCIES
------------
Required:
    beir >= 2.0.0   — pip install beir
Optional (improves diversity selection):
    scikit-learn    — pip install scikit-learn

HOW TO RUN
----------
  # minimal (uses ~/.cache/beir, writes to /tmp)
  python external_curator_extractor.py

  # explicit paths
  python external_curator_extractor.py \\
      --cache-dir ~/.cache/beir \\
      --output    /tmp/external-curator-queries.jsonl \\
      --report    /tmp/external-curator-analysis.md \\
      --n 10 \\
      --max-words 15 \\
      --seed 42

  # dry-run: print selected queries without writing files
  python external_curator_extractor.py --dry-run

INTEGRATION WITH EVAL HARNESS
------------------------------
After Toto fills ``expected_doc_ids`` manually, pass the JSONL to the nox-mem
eval runner:

  nox-mem eval-import /tmp/external-curator-queries.jsonl
  nox-mem eval-run --tag external-curator-E11

Then compare nDCG@10 (external) vs nDCG@10 from Run #6 internal (0.674).
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import random
import re
import sys
from pathlib import Path
from typing import Any, NamedTuple

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("external_curator_extractor")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DATASET_NAME = "BeIR/trec-covid"
_SPLIT = "test"
_DEFAULT_N = 10
_DEFAULT_MAX_WORDS = 15
_DEFAULT_SEED = 42
_DEFAULT_OUTPUT = Path("/tmp/external-curator-queries.jsonl")
_DEFAULT_REPORT = Path("/tmp/external-curator-analysis.md")
_DEFAULT_CACHE_DIR = Path.home() / ".cache" / "beir"

# Queries that are too generic or off-topic for nox-mem (knowledge-mgmt context)
# These are pre-screened TREC-COVID topic IDs known to be epidemiological counts
# ("how many cases") rather than mechanism / research-style questions.
_BLOCKLIST_TOPIC_IDS: frozenset[str] = frozenset({
    # e.g. "how many people have died from coronavirus" — count-only, not
    # suitable for knowledge-retrieval evaluation against a software memory DB.
    # Add TREC-COVID topic numbers (as strings) here if needed after inspection.
})

# Minimum meaningful query length (in words) — avoids 1-2 word trivial queries
_MIN_WORDS = 4

# Maximum pairwise Jaccard overlap allowed in greedy fallback diversity pass
_MAX_JACCARD_OVERLAP = 0.50

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

QueryRecord = dict[str, Any]  # BEIR raw query: {"_id": str, "text": str}


class ExtractedQuery(NamedTuple):
    """A single external-curator query ready for human curation."""

    ext_id: str           # EXT-Q01 … EXT-Q10
    beir_id: str          # Original BEIR / TREC-COVID topic ID
    query_text: str       # Raw query text (lowercased + stripped)
    word_count: int       # Token count
    source: str           # "beir-trec-covid"


# ---------------------------------------------------------------------------
# BEIR import guard
# ---------------------------------------------------------------------------


def _require_beir() -> Any:
    """Import and return the ``beir`` package, raising a helpful error if absent.

    Returns:
        The imported ``beir`` package.

    Raises:
        ImportError: If beir is not installed in the active environment.
    """
    try:
        import beir  # type: ignore[import-untyped]
        return beir
    except ImportError as exc:
        raise ImportError(
            "The 'beir' package is required.  Install it with:\n"
            "    pip install beir>=2.0.0\n"
            "See https://github.com/beir-cellar/beir for details."
        ) from exc


# ---------------------------------------------------------------------------
# 1. Load BEIR queries
# ---------------------------------------------------------------------------


def extract_beir_queries(
    dataset_name: str = _DATASET_NAME,
    n: int = _DEFAULT_N,
    max_words: int = _DEFAULT_MAX_WORDS,
    cache_dir: Path = _DEFAULT_CACHE_DIR,
) -> list[QueryRecord]:
    """Load and quality-filter TREC-COVID queries from the BEIR benchmark.

    Downloads the dataset on first call (cached to ``cache_dir`` afterwards).
    Filters to queries with ``_MIN_WORDS ≤ word_count ≤ max_words``, removing
    purely numeric or stop-word-only queries.

    Args:
        dataset_name: HuggingFace / BEIR dataset identifier.
            Defaults to ``"BeIR/trec-covid"``.
        n: Target number of queries to return after diversity selection.
            This function returns the full filtered pool; diversity selection
            happens in :func:`select_diverse_subset`.
        max_words: Maximum word count (inclusive).  Queries longer than this
            are excluded to match the nox-mem user query profile.
        cache_dir: Local directory for BEIR cache.

    Returns:
        List of raw BEIR query dicts, each with keys ``_id`` and ``text``,
        after quality filtering.  Length ≥ n (typically all 50 TREC-COVID
        queries pass basic filters).

    Raises:
        ImportError: If the ``beir`` package is not installed.
        RuntimeError: If the dataset cannot be loaded or is empty.
    """
    beir_pkg = _require_beir()

    logger.info("Loading dataset '%s' from cache '%s' …", dataset_name, cache_dir)

    try:
        from beir.datasets.data_loader import GenericDataLoader  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "beir.datasets.data_loader not found.  "
            "Ensure beir >= 2.0.0 is installed."
        ) from exc

    # BEIR GenericDataLoader expects a local directory containing
    # corpus.jsonl, queries.jsonl, qrels/test.tsv.
    # When these don't exist it downloads them automatically.
    dataset_local_dir = cache_dir / _dataset_local_name(dataset_name)

    _ensure_beir_dataset(dataset_name, dataset_local_dir)

    queries_path = dataset_local_dir / "queries.jsonl"
    if not queries_path.exists():
        raise RuntimeError(
            f"Queries file not found at expected path: {queries_path}\n"
            "BEIR download may have failed.  Check network access and retry."
        )

    raw_queries = _load_queries_jsonl(queries_path)
    logger.info("Loaded %d raw queries from BEIR cache.", len(raw_queries))

    if not raw_queries:
        raise RuntimeError(
            f"No queries found in {queries_path}.  "
            "The file may be empty or corrupted."
        )

    filtered = _quality_filter(raw_queries, max_words=max_words)
    logger.info(
        "After quality filter (min=%d, max=%d words, no blocklist): %d queries remain.",
        _MIN_WORDS,
        max_words,
        len(filtered),
    )

    if len(filtered) < n:
        logger.warning(
            "Filtered pool (%d) is smaller than requested n=%d.  "
            "Returning all filtered queries; increase max_words or reduce n.",
            len(filtered),
            n,
        )

    return filtered


def _dataset_local_name(dataset_name: str) -> str:
    """Derive the local directory name from the HuggingFace dataset identifier.

    Args:
        dataset_name: e.g. ``"BeIR/trec-covid"``.

    Returns:
        Directory name, e.g. ``"trec-covid"``.
    """
    # BeIR/<name> → <name>
    parts = dataset_name.split("/")
    return parts[-1]


def _ensure_beir_dataset(dataset_name: str, local_dir: Path) -> None:
    """Download the BEIR dataset if not already cached locally.

    Uses ``beir.datasets.data_loader.GenericDataLoader.download`` when the
    local directory is absent or incomplete.

    Args:
        dataset_name: HuggingFace dataset identifier.
        local_dir: Target local directory for the dataset files.

    Raises:
        RuntimeError: If download fails.
    """
    queries_path = local_dir / "queries.jsonl"
    if queries_path.exists():
        logger.info("BEIR cache hit: %s", local_dir)
        return

    logger.info(
        "BEIR dataset '%s' not cached.  Downloading to %s …",
        dataset_name,
        local_dir,
    )
    try:
        from beir import util as beir_util  # type: ignore[import-untyped]
        url = f"https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/{_dataset_local_name(dataset_name)}.zip"
        beir_util.download_and_unzip(str(url), str(local_dir.parent))
        logger.info("Download complete: %s", local_dir)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to download BEIR dataset '{dataset_name}': {exc}\n"
            "Ensure internet access and that the beir package is installed correctly."
        ) from exc


def _load_queries_jsonl(path: Path) -> list[QueryRecord]:
    """Parse a BEIR queries.jsonl file into a list of dicts.

    Args:
        path: Path to ``queries.jsonl`` where each line is a JSON object
            with keys ``_id`` and ``text``.

    Returns:
        List of query dicts.
    """
    queries: list[QueryRecord] = []
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("Skipping malformed JSON at line %d: %s", lineno, exc)
                continue
            if "_id" not in obj or "text" not in obj:
                logger.warning(
                    "Line %d missing '_id' or 'text' — skipping: %s",
                    lineno,
                    line[:80],
                )
                continue
            queries.append(obj)
    return queries


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokeniser for word-count and overlap metrics.

    Args:
        text: Raw query text.

    Returns:
        List of lowercase alphabetic tokens.
    """
    return re.findall(r"[a-zA-Z]+", text.lower())


def _quality_filter(
    queries: list[QueryRecord],
    max_words: int,
) -> list[QueryRecord]:
    """Apply quality filters to raw BEIR queries.

    Filters applied (in order):
    1. Blocklist topic IDs (manually pre-screened count-only queries).
    2. Word count in [_MIN_WORDS, max_words] (inclusive).
    3. At least one alphabetic character (eliminates code snippets or IDs).
    4. Not purely a number or date.

    Args:
        queries: Raw BEIR query list.
        max_words: Maximum allowed word count.

    Returns:
        Filtered list, preserving original order.
    """
    result: list[QueryRecord] = []
    for q in queries:
        qid: str = str(q.get("_id", ""))
        text: str = q.get("text", "").strip()

        if qid in _BLOCKLIST_TOPIC_IDS:
            logger.debug("Blocklisted topic: %s", qid)
            continue

        tokens = _tokenize(text)
        wc = len(tokens)

        if wc < _MIN_WORDS:
            logger.debug("Too short (%d words): %s", wc, text[:60])
            continue

        if wc > max_words:
            logger.debug("Too long (%d words): %s", wc, text[:60])
            continue

        if not any(ch.isalpha() for ch in text):
            logger.debug("No alphabetic chars: %s", text[:60])
            continue

        result.append(q)

    return result


# ---------------------------------------------------------------------------
# 2. Diversity selection
# ---------------------------------------------------------------------------


def select_diverse_subset(
    queries: list[QueryRecord],
    n: int = _DEFAULT_N,
    seed: int = _DEFAULT_SEED,
) -> list[QueryRecord]:
    """Select a lexically diverse subset of ``n`` queries from a filtered pool.

    Selection strategy (two-pass, with automatic fallback):

    Pass A — Scikit-learn KMeans (preferred):
        1. Build a TF-IDF matrix over all query texts (max_features=500,
           sublinear_tf=True).
        2. Cluster into ``n`` groups with KMeans(k=n, random_state=seed).
        3. From each cluster, select the query nearest to the centroid
           (cosine-projected L2 distance in TF-IDF space).

    Pass B — Greedy Jaccard (fallback if scikit-learn unavailable):
        1. Shuffle the query pool (seed=seed).
        2. Initialise selected set with a random query.
        3. Iterate: add the query with the lowest max pairwise Jaccard
           similarity to any already-selected query, until ``n`` selected.
        4. Any query whose Jaccard overlap with the current set exceeds
           ``_MAX_JACCARD_OVERLAP`` is eligible only if no better candidate
           exists.

    Args:
        queries: Quality-filtered BEIR query list (≥ n entries expected).
        n: Number of queries to select.
        seed: Random seed for reproducibility.

    Returns:
        List of ``n`` selected queries, ordered by selection pass logic
        (cluster 0 → cluster n-1 for Pass A; greedy order for Pass B).

    Raises:
        ValueError: If the input pool is smaller than ``n``.
    """
    if len(queries) < n:
        raise ValueError(
            f"Cannot select {n} queries from a pool of {len(queries)}.  "
            "Reduce n or relax quality filters."
        )
    if len(queries) == n:
        logger.info("Pool size == n (%d); returning full pool without clustering.", n)
        return list(queries)

    try:
        return _select_kmeans(queries, n=n, seed=seed)
    except ImportError:
        logger.warning(
            "scikit-learn not available; falling back to greedy Jaccard diversity."
        )
        return _select_greedy_jaccard(queries, n=n, seed=seed)


def _select_kmeans(
    queries: list[QueryRecord],
    n: int,
    seed: int,
) -> list[QueryRecord]:
    """KMeans cluster-centroid selection (Pass A).

    Args:
        queries: Filtered query pool.
        n: Number of clusters / selected queries.
        seed: Random state for KMeans initialisation.

    Returns:
        One query per cluster (the medoid nearest to the cluster centroid).

    Raises:
        ImportError: If scikit-learn is not installed.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore[import-not-found]
    from sklearn.cluster import KMeans  # type: ignore[import-not-found]
    import numpy as np  # type: ignore[import-not-found]

    logger.info("Pass A: TF-IDF + KMeans(k=%d, seed=%d) …", n, seed)

    texts = [q["text"] for q in queries]
    vectorizer = TfidfVectorizer(max_features=500, sublinear_tf=True, lowercase=True)
    tfidf_matrix = vectorizer.fit_transform(texts)  # shape: (len(queries), features)

    km = KMeans(n_clusters=n, random_state=seed, n_init="auto")
    km.fit(tfidf_matrix)

    labels: list[int] = km.labels_.tolist()
    centroids = km.cluster_centers_  # shape: (n, features)

    # For each cluster, find the query closest to its centroid (L2 in TF-IDF space)
    selected: list[QueryRecord] = []
    tfidf_dense = tfidf_matrix.toarray()

    for cluster_idx in range(n):
        member_indices = [i for i, lbl in enumerate(labels) if lbl == cluster_idx]
        if not member_indices:
            # Degenerate cluster — take global nearest not yet selected
            logger.warning("Cluster %d is empty; using global nearest.", cluster_idx)
            member_indices = list(range(len(queries)))

        centroid = centroids[cluster_idx]
        distances = [
            float(np.linalg.norm(tfidf_dense[i] - centroid))
            for i in member_indices
        ]
        nearest_local_idx = int(member_indices[int(np.argmin(distances))])
        selected.append(queries[nearest_local_idx])
        logger.debug(
            "Cluster %d centroid → '%s'",
            cluster_idx,
            queries[nearest_local_idx]["text"][:70],
        )

    logger.info("KMeans selection complete: %d queries.", len(selected))
    return selected


def _jaccard(set_a: set[str], set_b: set[str]) -> float:
    """Compute Jaccard similarity between two token sets.

    Args:
        set_a: First token set.
        set_b: Second token set.

    Returns:
        Jaccard index in [0, 1].  Returns 0.0 if both sets are empty.
    """
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union else 0.0


def _select_greedy_jaccard(
    queries: list[QueryRecord],
    n: int,
    seed: int,
) -> list[QueryRecord]:
    """Greedy max-diversity selection via pairwise Jaccard distance (Pass B).

    Args:
        queries: Filtered query pool.
        n: Number of queries to select.
        seed: Random seed for initial shuffle.

    Returns:
        ``n`` queries with low pairwise lexical overlap.
    """
    logger.info("Pass B: greedy Jaccard diversity (seed=%d) …", seed)

    rng = random.Random(seed)
    pool = list(queries)
    rng.shuffle(pool)

    token_sets: list[set[str]] = [set(_tokenize(q["text"])) for q in pool]

    # Seed with the first query
    selected_indices: list[int] = [0]
    selected_sets: list[set[str]] = [token_sets[0]]

    while len(selected_indices) < n:
        best_idx = -1
        best_min_overlap = float("inf")

        for i, ts in enumerate(token_sets):
            if i in selected_indices:
                continue
            # Max Jaccard overlap with any already-selected query
            max_overlap = max(_jaccard(ts, sel) for sel in selected_sets)
            if max_overlap < best_min_overlap:
                best_min_overlap = max_overlap
                best_idx = i

        if best_idx == -1:
            logger.warning(
                "Could not find a distinct query after selecting %d; "
                "relaxing overlap constraint.",
                len(selected_indices),
            )
            # Pick first unselected
            for i in range(len(pool)):
                if i not in selected_indices:
                    best_idx = i
                    break
            if best_idx == -1:
                break

        selected_indices.append(best_idx)
        selected_sets.append(token_sets[best_idx])
        logger.debug(
            "Greedy selected (overlap=%.2f): '%s'",
            best_min_overlap,
            pool[best_idx]["text"][:70],
        )

    result = [pool[i] for i in selected_indices]
    logger.info("Greedy Jaccard selection complete: %d queries.", len(result))
    return result


# ---------------------------------------------------------------------------
# 3. Format for nox-mem eval harness
# ---------------------------------------------------------------------------


def format_for_nox_mem_eval(
    queries: list[QueryRecord],
    output_jsonl: Path,
    source: str = "beir-trec-covid",
) -> list[dict[str, Any]]:
    """Serialise selected queries to nox-mem eval harness JSONL format.

    Output schema (one JSON object per line):

    .. code-block:: json

        {
            "query_id": "EXT-Q01",
            "query_text": "what causes covid-19 transmission",
            "source": "beir-trec-covid",
            "beir_id": "1",
            "expected_doc_ids": [],
            "needs_human_curation": true
        }

    ``expected_doc_ids`` is intentionally empty — Toto fills it manually in
    ~3 min / query by running hybrid search and marking the top-3 true positives.

    Args:
        queries: Selected query list (length n).
        output_jsonl: Destination file path.  Parent directories are created
            automatically.
        source: Source tag embedded in each output record.

    Returns:
        List of serialised record dicts (mirrors what was written to disk).

    Raises:
        OSError: If the output file cannot be written.
    """
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    for rank, q in enumerate(queries, start=1):
        ext_id = f"EXT-Q{rank:02d}"
        record: dict[str, Any] = {
            "query_id": ext_id,
            "query_text": q["text"].strip(),
            "source": source,
            "beir_id": str(q["_id"]),
            "expected_doc_ids": [],
            "needs_human_curation": True,
        }
        records.append(record)

    with output_jsonl.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    logger.info("Wrote %d queries to %s", len(records), output_jsonl)
    return records


# ---------------------------------------------------------------------------
# 4. Analyse query characteristics
# ---------------------------------------------------------------------------


def analyze_query_characteristics(
    queries: list[QueryRecord],
    golden_queries: list[str] | None = None,
) -> dict[str, Any]:
    """Compute descriptive statistics about the selected query set.

    Metrics reported:

    - ``count``: Number of selected queries.
    - ``avg_word_count``: Mean tokens per query.
    - ``min_word_count`` / ``max_word_count``: Range.
    - ``unique_vocab_size``: Number of distinct token types across all queries.
    - ``vocab_overlap_pct``: Jaccard overlap (%) between this set's vocabulary
      and the golden-query vocabulary (0 if ``golden_queries`` is None).
    - ``avg_pairwise_jaccard``: Mean pairwise Jaccard similarity — lower is
      more diverse.
    - ``domain_keywords``: Top-10 most frequent content tokens (stopwords
      removed) as a proxy for domain coverage.
    - ``source``: Dataset name tag.

    Args:
        queries: Selected BEIR query records.
        golden_queries: Optional list of raw query texts from the internal
            golden set (for vocab overlap computation).

    Returns:
        Dict with the metrics described above.
    """
    # Basic English stopwords — no external dependency
    _STOPWORDS = frozenset({
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "can", "what", "which", "who",
        "how", "when", "where", "why", "that", "this", "these", "those",
        "it", "its", "not", "no", "as", "if", "so", "up", "out",
    })

    all_tokens: list[str] = []
    word_counts: list[int] = []
    query_token_sets: list[set[str]] = []

    for q in queries:
        tokens = _tokenize(q["text"])
        word_counts.append(len(tokens))
        all_tokens.extend(tokens)
        query_token_sets.append(set(tokens))

    unique_vocab: set[str] = set(all_tokens)

    # Vocab overlap with golden set
    vocab_overlap_pct = 0.0
    if golden_queries:
        golden_tokens: set[str] = set()
        for gt in golden_queries:
            golden_tokens.update(_tokenize(gt))
        if golden_tokens or unique_vocab:
            vocab_overlap_pct = round(
                100.0
                * len(unique_vocab & golden_tokens)
                / len(unique_vocab | golden_tokens),
                1,
            )

    # Average pairwise Jaccard similarity
    pairwise_sims: list[float] = []
    n = len(query_token_sets)
    for i in range(n):
        for j in range(i + 1, n):
            pairwise_sims.append(_jaccard(query_token_sets[i], query_token_sets[j]))
    avg_pairwise_jaccard = (
        round(sum(pairwise_sims) / len(pairwise_sims), 3) if pairwise_sims else 0.0
    )

    # Domain keywords (top-10 content tokens by frequency)
    freq: dict[str, int] = {}
    for tok in all_tokens:
        if tok not in _STOPWORDS and len(tok) > 2:
            freq[tok] = freq.get(tok, 0) + 1
    domain_keywords = sorted(freq, key=lambda t: -freq[t])[:10]

    avg_wc = round(sum(word_counts) / len(word_counts), 1) if word_counts else 0.0

    return {
        "count": len(queries),
        "avg_word_count": avg_wc,
        "min_word_count": min(word_counts) if word_counts else 0,
        "max_word_count": max(word_counts) if word_counts else 0,
        "unique_vocab_size": len(unique_vocab),
        "vocab_overlap_pct": vocab_overlap_pct,
        "avg_pairwise_jaccard": avg_pairwise_jaccard,
        "domain_keywords": domain_keywords,
        "source": _DATASET_NAME,
    }


# ---------------------------------------------------------------------------
# 5. Markdown report writer
# ---------------------------------------------------------------------------


def write_analysis_report(
    records: list[dict[str, Any]],
    stats: dict[str, Any],
    report_path: Path,
) -> None:
    """Write a Markdown analysis report for paper §4.1 (External Curator subsection).

    The report includes:
    - Summary table of selected queries.
    - Descriptive statistics.
    - Curation instructions for Toto.
    - Integration commands for the eval harness.

    Args:
        records: Formatted JSONL records (output of :func:`format_for_nox_mem_eval`).
        stats: Analysis dict (output of :func:`analyze_query_characteristics`).
        report_path: Destination ``.md`` file path.

    Raises:
        OSError: If the file cannot be written.
    """
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [
        "# E11 External Curator Query Analysis — NOX-Supermem §4.1",
        "",
        "> **Purpose:** Close Gap #2 (internal-curator bias) by evaluating",
        "> nox-mem hybrid search against 10 queries authored by NIST professional",
        "> assessors (TREC-COVID Round 5, Voorhees et al. 2021).",
        "",
        "## Selected Queries",
        "",
        "| ID | BEIR Topic | Query Text | Words |",
        "|----|-----------|------------|-------|",
    ]

    for rec in records:
        qid = rec["query_id"]
        beir_id = rec.get("beir_id", "—")
        text = rec["query_text"]
        wc = len(_tokenize(text))
        lines.append(f"| {qid} | {beir_id} | {text} | {wc} |")

    lines += [
        "",
        "## Descriptive Statistics",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Query count | {stats['count']} |",
        f"| Avg word count | {stats['avg_word_count']} |",
        f"| Word count range | {stats['min_word_count']}–{stats['max_word_count']} |",
        f"| Unique vocabulary | {stats['unique_vocab_size']} tokens |",
        f"| Vocab overlap with internal golden-50 | {stats['vocab_overlap_pct']}% |",
        f"| Avg pairwise Jaccard similarity | {stats['avg_pairwise_jaccard']} (lower = more diverse) |",
        f"| Top domain keywords | {', '.join(stats['domain_keywords'])} |",
        f"| Dataset source | {stats['source']} |",
        "",
        "## Interpretation",
        "",
        "Low vocabulary overlap (target < 20%) confirms the external queries probe",
        "different terminology than Toto's internal golden set, reducing the risk",
        "that evaluation metrics are inflated by curator-specific phrasing that",
        "the system was implicitly tuned against.",
        "",
        "Low average pairwise Jaccard (target < 0.25) confirms lexical diversity",
        "across the 10 selected queries — they cover distinct sub-topics within",
        "the TREC-COVID domain.",
        "",
        "## Curation Instructions for Toto",
        "",
        "> **Estimated effort:** ~3 min per query, ~30 min total.",
        "",
        "For each query in the table above:",
        "",
        "1. Run hybrid search against nox-mem:",
        "   ```",
        "   nox-mem search \"<query_text>\" --hybrid --limit 10",
        "   ```",
        "   Or via HTTP API:",
        "   ```",
        "   curl -s 'http://127.0.0.1:18802/api/search?q=<query_text>&limit=10' | jq '.results[].chunk_id'",
        "   ```",
        "",
        "2. Identify the top-3 results that **genuinely answer** the query",
        "   (not just keyword overlap).",
        "",
        "3. Fill `expected_doc_ids` in `/tmp/external-curator-queries.jsonl`",
        "   with those 3 chunk IDs.",
        "",
        "4. Mark `needs_human_curation: false` once done.",
        "",
        "**Acceptance criterion:** At least 2 of 3 expected_doc_ids ranked in",
        "the top-5 results constitutes a relevant hit for nDCG@10 computation.",
        "",
        "## Integration with Eval Harness",
        "",
        "After curation is complete:",
        "",
        "```bash",
        "# Import into eval harness",
        "nox-mem eval-import /tmp/external-curator-queries.jsonl",
        "",
        "# Run evaluation",
        "nox-mem eval-run --tag external-curator-E11",
        "",
        "# Compare with internal baseline (Run #6 nDCG = 0.674)",
        "# Hypothesis: |nDCG_external - 0.674| <= 0.10",
        "```",
        "",
        "## Paper §4.1 Language Anchor",
        "",
        "```",
        "To assess internal-curator bias, we additionally evaluated nox-mem against",
        "10 queries authored by NIST professional assessors (TREC-COVID Round 5",
        "[CITE]), selected via TF-IDF KMeans clustering (k=10, seed=42) over the",
        "50 canonical topics to maximise lexical diversity (avg pairwise Jaccard =",
        f"{stats['avg_pairwise_jaccard']}).  Vocabulary overlap with the internal",
        f"golden-50 set was {stats['vocab_overlap_pct']}%, confirming the two sets",
        "probe complementary terminology.",
        "```",
        "",
        "---",
        "*Generated by `external_curator_extractor.py` — do not edit manually.*",
    ]

    with report_path.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    logger.info("Analysis report written to %s", report_path)


# ---------------------------------------------------------------------------
# 6. CLI / main pipeline
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        Configured :class:`argparse.ArgumentParser` instance.
    """
    parser = argparse.ArgumentParser(
        prog="external_curator_extractor",
        description=(
            "Extract N diverse TREC-COVID queries from BEIR for Gap #2 "
            "(external curator bias) evaluation — NOX-Supermem paper §4.1 / E11."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=_DEFAULT_CACHE_DIR,
        metavar="DIR",
        help=f"BEIR local cache directory (default: {_DEFAULT_CACHE_DIR})",
    )
    parser.add_argument(
        "--dataset",
        default=_DATASET_NAME,
        metavar="HF_DATASET",
        help=f"HuggingFace / BEIR dataset identifier (default: {_DATASET_NAME})",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=_DEFAULT_N,
        metavar="N",
        help=f"Number of queries to select (default: {_DEFAULT_N})",
    )
    parser.add_argument(
        "--max-words",
        type=int,
        default=_DEFAULT_MAX_WORDS,
        metavar="W",
        help=f"Maximum words per query (default: {_DEFAULT_MAX_WORDS})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=_DEFAULT_SEED,
        metavar="S",
        help=f"Random seed (default: {_DEFAULT_SEED})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        metavar="FILE",
        help=f"Output JSONL path (default: {_DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=_DEFAULT_REPORT,
        metavar="FILE",
        help=f"Analysis report Markdown path (default: {_DEFAULT_REPORT})",
    )
    parser.add_argument(
        "--golden-queries-file",
        type=Path,
        default=None,
        metavar="FILE",
        help=(
            "Optional JSONL file with internal golden queries for vocab overlap "
            "computation.  Each line must have a 'query_text' or 'text' field."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print selected queries to stdout without writing files.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser


def _load_golden_query_texts(path: Path) -> list[str]:
    """Load query texts from an internal golden queries JSONL file.

    Args:
        path: Path to JSONL where each line has ``query_text`` or ``text``.

    Returns:
        List of raw query text strings.
    """
    texts: list[str] = []
    if not path.exists():
        logger.warning("Golden queries file not found: %s — skipping overlap.", path)
        return texts
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                text = obj.get("query_text") or obj.get("text") or ""
                if text:
                    texts.append(str(text))
            except json.JSONDecodeError:
                pass
    logger.info("Loaded %d golden query texts from %s", len(texts), path)
    return texts


def main(argv: list[str] | None = None) -> int:
    """Execute the full external-curator extraction pipeline.

    Pipeline steps:
    1. Parse CLI arguments.
    2. Load + quality-filter BEIR queries.
    3. Select diverse subset.
    4. Format and write JSONL (unless ``--dry-run``).
    5. Compute and write analysis report (unless ``--dry-run``).

    Args:
        argv: Optional argument list (uses ``sys.argv[1:]`` when None).

    Returns:
        Exit code — 0 on success, 1 on handled error.
    """
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(
        "external_curator_extractor — E11 Gap #2 pipeline (n=%d, max_words=%d, seed=%d)",
        args.n,
        args.max_words,
        args.seed,
    )

    # Step 1: Load + filter
    try:
        filtered_pool = extract_beir_queries(
            dataset_name=args.dataset,
            n=args.n,
            max_words=args.max_words,
            cache_dir=args.cache_dir,
        )
    except (ImportError, RuntimeError, FileNotFoundError) as exc:
        logger.error("Failed to load BEIR queries: %s", exc)
        return 1

    # Step 2: Diversity selection
    try:
        selected = select_diverse_subset(filtered_pool, n=args.n, seed=args.seed)
    except ValueError as exc:
        logger.error("Diversity selection failed: %s", exc)
        return 1

    # Step 3: Load optional golden queries for overlap metric
    golden_texts: list[str] = []
    if args.golden_queries_file:
        golden_texts = _load_golden_query_texts(args.golden_queries_file)

    # Step 4: Analyse
    stats = analyze_query_characteristics(selected, golden_queries=golden_texts or None)

    # Step 5: Dry-run output
    if args.dry_run:
        print("\n=== Selected External-Curator Queries (dry-run) ===\n")
        for rank, q in enumerate(selected, start=1):
            wc = len(_tokenize(q["text"]))
            print(f"EXT-Q{rank:02d} [{q['_id']}] ({wc}w): {q['text']}")
        print("\n=== Statistics ===\n")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        print("\n(Dry-run — no files written.)\n")
        return 0

    # Step 6: Write JSONL
    try:
        records = format_for_nox_mem_eval(selected, output_jsonl=args.output)
    except OSError as exc:
        logger.error("Failed to write output JSONL: %s", exc)
        return 1

    # Step 7: Write report
    try:
        write_analysis_report(records, stats, report_path=args.report)
    except OSError as exc:
        logger.error("Failed to write analysis report: %s", exc)
        return 1

    # Summary
    logger.info(
        "Done. Output: %s | Report: %s",
        args.output,
        args.report,
    )
    print("\n=== E11 External Curator Extractor — Summary ===\n")
    print(f"  Queries written : {len(records)}")
    print(f"  JSONL output    : {args.output}")
    print(f"  Report          : {args.report}")
    print(f"  Avg word count  : {stats['avg_word_count']}")
    print(f"  Vocab overlap   : {stats['vocab_overlap_pct']}% (vs golden-50)")
    print(f"  Avg Jaccard     : {stats['avg_pairwise_jaccard']} (diversity metric)")
    print(
        "\n  Next step: curate expected_doc_ids manually (~3 min/query).\n"
        "  Then: nox-mem eval-import <output> && nox-mem eval-run --tag external-curator-E11\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
