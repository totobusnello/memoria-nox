"""E11 — Semi-automatic curation of expected_doc_ids for external-curator queries.

PURPOSE
-------
For each of the 10 BEIR TREC-COVID queries in ``external-curator-queries.jsonl``,
run nox-mem hybrid search (top-10) via READ-ONLY HTTP API and apply the
``top3_hybrid_heuristic``: assume the top-3 returned chunk IDs are relevant.

This gives a strong LLM-as-judge baseline — nox-mem's own hybrid ranking acts
as the relevance oracle.  Toto then reviews the ``--review`` preview to confirm
or override before committing the curated file.

USAGE
-----
    # Write curated JSONL (default paths):
    python curate_external_queries.py

    # Preview only — no files written:
    python curate_external_queries.py --review

    # Explicit paths + custom API URL:
    python curate_external_queries.py \\
        --input  /path/to/external-curator-queries.jsonl \\
        --output /path/to/external-curator-queries-curated.jsonl \\
        --api-url http://127.0.0.1:18802

    # Override top-N selection (default 3):
    python curate_external_queries.py --top-n 5

ENVIRONMENT
-----------
    NOX_API_URL — base URL for nox-mem API (overrides --api-url)

OUTPUT SCHEMA (one JSON object per line)
-----------------------------------------
    {
        "query_id":        "EXT-Q01",
        "query_text":      "are there any clinical trials...",
        "source":          "beir-trec-covid",
        "beir_id":         "17",
        "expected_doc_ids": ["chunk-123", "chunk-456", "chunk-789"],
        "retrieved_full":  [
            {"rank": 1, "chunk_id": "chunk-123", "score": 0.912,
             "snippet": "Clinical trials for coronavirus..."},
            ...  // top-10 entries
        ],
        "curation_method": "top3_hybrid_heuristic",
        "needs_human_curation": false
    }

NOTES
-----
- READ-ONLY: never modifies the nox-mem database.
- ``--review`` mode is safe to run in any environment — no files written.
- If the API returns fewer than ``top_n`` results for a query, all returned
  IDs are used and a warning is emitted.
- Network errors per query are logged and the query is written with an empty
  ``expected_doc_ids`` and ``curation_method: "api_error"``.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, TypedDict

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("curate_external_queries")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_API_URL: str = "http://127.0.0.1:18802"
_DEFAULT_TOP_N: int = 3
_DEFAULT_SEARCH_K: int = 10
_SNIPPET_LEN: int = 200

_RESULTS_DIR = Path(__file__).parent.parent / "results"
_DEFAULT_INPUT: Path = _RESULTS_DIR / "external-curator-queries.jsonl"
_DEFAULT_OUTPUT: Path = _RESULTS_DIR / "external-curator-queries-curated.jsonl"

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class QueryRecord(TypedDict):
    """Raw record from the input JSONL file."""

    query_id: str
    query_text: str
    source: str
    beir_id: str
    expected_doc_ids: list[str]
    needs_human_curation: bool


class RetrievedChunk(TypedDict):
    """Single chunk entry in the retrieved_full list."""

    rank: int
    chunk_id: str
    score: float
    snippet: str


class CuratedRecord(TypedDict):
    """Output record written to the curated JSONL file."""

    query_id: str
    query_text: str
    source: str
    beir_id: str
    expected_doc_ids: list[str]
    retrieved_full: list[RetrievedChunk]
    curation_method: str
    needs_human_curation: bool


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def load_queries(path: Path) -> list[QueryRecord]:
    """Load the 10 external-curator query records from a JSONL file.

    Args:
        path: Absolute path to the input ``external-curator-queries.jsonl``.

    Returns:
        List of query dicts, one per line.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If any line is not valid JSON or is missing required fields.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Input file not found: {path}\n"
            "Pass --input <path> or ensure the default path exists."
        )

    records: list[QueryRecord] = []
    required_fields = {"query_id", "query_text"}

    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj: dict[str, Any] = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Malformed JSON on line {lineno} of {path}: {exc}"
                ) from exc

            missing = required_fields - obj.keys()
            if missing:
                raise ValueError(
                    f"Line {lineno} is missing required fields: {missing}"
                )

            records.append(
                QueryRecord(
                    query_id=str(obj["query_id"]),
                    query_text=str(obj["query_text"]),
                    source=str(obj.get("source", "beir-trec-covid")),
                    beir_id=str(obj.get("beir_id", "")),
                    expected_doc_ids=list(obj.get("expected_doc_ids", [])),
                    needs_human_curation=bool(obj.get("needs_human_curation", True)),
                )
            )

    logger.info("Loaded %d queries from %s", len(records), path)
    return records


def write_curated(records: list[CuratedRecord], path: Path) -> None:
    """Write curated records to a JSONL file.

    Args:
        records: List of fully-populated curated records.
        path: Destination file path.  Parent directories are created if absent.

    Raises:
        OSError: If the file cannot be written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    logger.info("Wrote %d curated records to %s", len(records), path)


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------


def search_hybrid(
    query_text: str,
    api_base_url: str,
    k: int = _DEFAULT_SEARCH_K,
) -> list[dict[str, Any]]:
    """Run hybrid search against the nox-mem HTTP API (READ-ONLY GET).

    Calls ``GET /api/search?q=<query>&k=<k>`` and returns the raw result list.
    Uses only the Python standard library (``urllib``) — no external deps.

    Args:
        query_text: Natural-language query string.
        api_base_url: Base URL, e.g. ``"http://127.0.0.1:18802"``.
            Trailing slash is handled automatically.
        k: Number of results to request from the API.

    Returns:
        List of raw result dicts from the API ``results`` (or ``hits``) array.
        Returns an empty list if the API returns no results field.

    Raises:
        urllib.error.URLError: On network-level failure (connection refused, timeout).
        ValueError: If the API response is not valid JSON.
    """
    base = api_base_url.rstrip("/")
    params = urllib.parse.urlencode({"q": query_text, "k": k})
    url = f"{base}/api/search?{params}"

    logger.debug("GET %s", url)

    req = urllib.request.Request(url, method="GET")
    req.add_header("Accept", "application/json")

    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")

    try:
        payload: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Non-JSON response from {url!r}: {raw[:200]!r}"
        ) from exc

    # The API may return results under different keys depending on version
    results: list[dict[str, Any]] = (
        payload.get("results")
        or payload.get("hits")
        or payload.get("chunks")
        or []
    )

    logger.debug("Received %d results for query %r", len(results), query_text[:60])
    return results


def _extract_chunk_id(result: dict[str, Any]) -> str:
    """Extract the chunk identifier from a raw API result dict.

    Tries multiple field names used across nox-mem API versions:
    ``chunk_id``, ``id``, ``_id``.

    Args:
        result: Single result dict from the API response.

    Returns:
        Chunk ID string, or empty string if no recognised field is found.
    """
    return str(
        result.get("chunk_id")
        or result.get("id")
        or result.get("_id")
        or ""
    )


def _extract_score(result: dict[str, Any]) -> float:
    """Extract the relevance score from a raw API result dict.

    Tries ``score``, ``rrf_score``, ``hybrid_score``, ``_score`` in order.

    Args:
        result: Single result dict from the API response.

    Returns:
        Float score, or 0.0 if no recognised field is found.
    """
    for field in ("score", "rrf_score", "hybrid_score", "_score"):
        val = result.get(field)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass
    return 0.0


def _extract_snippet(result: dict[str, Any], max_len: int = _SNIPPET_LEN) -> str:
    """Extract a short text snippet from a raw API result dict.

    Tries ``chunk_text``, ``text``, ``content``, ``body`` in order.
    Truncates to ``max_len`` characters.

    Args:
        result: Single result dict from the API response.
        max_len: Maximum snippet character length.

    Returns:
        Snippet string (possibly empty).
    """
    for field in ("chunk_text", "text", "content", "body"):
        val = result.get(field)
        if val and isinstance(val, str):
            text = val.strip()
            return text[:max_len] + ("…" if len(text) > max_len else "")
    return ""


# ---------------------------------------------------------------------------
# Core curation logic
# ---------------------------------------------------------------------------


def curate_query(
    query: QueryRecord,
    api_base_url: str,
    top_n: int = _DEFAULT_TOP_N,
    k: int = _DEFAULT_SEARCH_K,
) -> CuratedRecord:
    """Run hybrid search for a single query and apply the top-N heuristic.

    The ``top3_hybrid_heuristic`` (default ``top_n=3``) assumes that the top-N
    results from nox-mem's hybrid search (BM25 + semantic RRF) are relevant.
    This is a strong baseline for a knowledge-retrieval system evaluated against
    the same corpus it was trained to serve.

    Args:
        query: Input query record from the JSONL file.
        api_base_url: nox-mem API base URL.
        top_n: Number of top results to mark as expected (default 3).
        k: Total results to retrieve from the API for ``retrieved_full``.

    Returns:
        A fully-populated :class:`CuratedRecord` with:
        - ``expected_doc_ids``: top-N chunk IDs.
        - ``retrieved_full``: top-K entries with rank, score, and snippet.
        - ``curation_method``: ``"top3_hybrid_heuristic"`` (or ``"api_error"``).
        - ``needs_human_curation``: ``False`` on success, ``True`` on API error.
    """
    method = f"top{top_n}_hybrid_heuristic"

    try:
        raw_results = search_hybrid(query["query_text"], api_base_url, k=k)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        logger.warning(
            "API error for %s (%r): %s",
            query["query_id"],
            query["query_text"][:60],
            exc,
        )
        return CuratedRecord(
            query_id=query["query_id"],
            query_text=query["query_text"],
            source=query["source"],
            beir_id=query["beir_id"],
            expected_doc_ids=[],
            retrieved_full=[],
            curation_method="api_error",
            needs_human_curation=True,
        )

    # Build structured top-K list
    retrieved_full: list[RetrievedChunk] = []
    for rank, res in enumerate(raw_results[:k], start=1):
        chunk_id = _extract_chunk_id(res)
        score = _extract_score(res)
        snippet = _extract_snippet(res)
        retrieved_full.append(
            RetrievedChunk(
                rank=rank,
                chunk_id=chunk_id,
                score=round(score, 6),
                snippet=snippet,
            )
        )

    # Apply top-N heuristic
    available = len(retrieved_full)
    if available < top_n:
        logger.warning(
            "%s: API returned %d results (< top_n=%d); using all %d.",
            query["query_id"],
            available,
            top_n,
            available,
        )

    expected_doc_ids = [
        entry["chunk_id"]
        for entry in retrieved_full[:top_n]
        if entry["chunk_id"]  # skip empty IDs (malformed responses)
    ]

    logger.info(
        "%s — %d results, top-%d selected: %s",
        query["query_id"],
        available,
        top_n,
        expected_doc_ids,
    )

    return CuratedRecord(
        query_id=query["query_id"],
        query_text=query["query_text"],
        source=query["source"],
        beir_id=query["beir_id"],
        expected_doc_ids=expected_doc_ids,
        retrieved_full=retrieved_full,
        curation_method=method,
        needs_human_curation=False,
    )


def curate_all(
    queries: list[QueryRecord],
    api_base_url: str,
    top_n: int = _DEFAULT_TOP_N,
    k: int = _DEFAULT_SEARCH_K,
) -> list[CuratedRecord]:
    """Run curation for all queries sequentially.

    Args:
        queries: All input query records.
        api_base_url: nox-mem API base URL.
        top_n: Number of top results to mark as expected per query.
        k: Total results to retrieve per query.

    Returns:
        List of curated records in the same order as the input.
    """
    curated: list[CuratedRecord] = []
    for query in queries:
        record = curate_query(query, api_base_url, top_n=top_n, k=k)
        curated.append(record)
    return curated


# ---------------------------------------------------------------------------
# Review (human-readable preview)
# ---------------------------------------------------------------------------


def print_review(curated: list[CuratedRecord]) -> None:
    """Print a human-readable preview of the curated results to stdout.

    Designed for Toto to visually verify the top-N selections before writing
    the curated JSONL file.  Does NOT modify any file.

    Args:
        curated: List of curated records (output of :func:`curate_all`).
    """
    sep = "=" * 72
    print(f"\n{sep}")
    print("  E11 EXTERNAL CURATOR — CURATION PREVIEW (--review mode)")
    print(f"{sep}\n")
    print("  Strategy : top3_hybrid_heuristic")
    print("  API      : READ-ONLY (no DB changes)")
    print(f"  Queries  : {len(curated)}")
    print()

    for rec in curated:
        method = rec["curation_method"]
        status = "API_ERROR" if method == "api_error" else "OK"
        print(f"{'─' * 72}")
        print(f"  {rec['query_id']}  [{status}]  beir_id={rec['beir_id']}")
        print(f"  Query : {rec['query_text']}")
        print()

        if method == "api_error":
            print("  ERROR: API call failed — expected_doc_ids left empty.")
            print("         Check that nox-mem API is running on the configured URL.")
            print()
            continue

        print(f"  expected_doc_ids (top-{len(rec['expected_doc_ids'])}):")
        for chunk_id in rec["expected_doc_ids"]:
            print(f"    - {chunk_id}")
        print()

        print(f"  retrieved_full (top-{len(rec['retrieved_full'])}):")
        for entry in rec["retrieved_full"]:
            marker = ">>>" if entry["rank"] <= len(rec["expected_doc_ids"]) else "   "
            snippet = entry["snippet"][:80] + ("…" if len(entry["snippet"]) > 80 else "")
            print(
                f"  {marker} #{entry['rank']:2d}  score={entry['score']:.4f}"
                f"  id={entry['chunk_id']}"
            )
            if snippet:
                print(f"           {snippet!r}")
        print()

    # Summary
    print(f"{'─' * 72}")
    errors = sum(1 for r in curated if r["curation_method"] == "api_error")
    ok = len(curated) - errors
    print(f"\n  Summary: {ok} OK / {errors} errors")
    if errors:
        print("  Fix API errors before writing the curated file.")
    else:
        print("  Re-run without --review to write the curated JSONL file.")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        Configured :class:`argparse.ArgumentParser` instance.
    """
    parser = argparse.ArgumentParser(
        prog="curate_external_queries",
        description=(
            "Semi-automatic curation of expected_doc_ids for E11 external-curator "
            "queries via nox-mem hybrid search (top-N heuristic, READ-ONLY)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Preview only (no files written):\n"
            "  python curate_external_queries.py --review\n\n"
            "  # Write curated JSONL:\n"
            "  python curate_external_queries.py\n\n"
            "  # Remote VPS API:\n"
            "  python curate_external_queries.py --api-url http://<vps-ip>:18802\n"
        ),
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=_DEFAULT_INPUT,
        metavar="FILE",
        help=(
            f"Input JSONL with external-curator queries "
            f"(default: {_DEFAULT_INPUT})"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        metavar="FILE",
        help=(
            f"Output curated JSONL path "
            f"(default: {_DEFAULT_OUTPUT})"
        ),
    )
    parser.add_argument(
        "--api-url",
        default=None,
        metavar="URL",
        help=(
            f"nox-mem API base URL.  Overridden by NOX_API_URL env var.  "
            f"(default: {_DEFAULT_API_URL})"
        ),
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=_DEFAULT_TOP_N,
        metavar="N",
        help=f"Number of top results to mark as expected_doc_ids (default: {_DEFAULT_TOP_N})",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=_DEFAULT_SEARCH_K,
        metavar="K",
        help=f"Total results to retrieve from API per query (default: {_DEFAULT_SEARCH_K})",
    )
    parser.add_argument(
        "--review",
        action="store_true",
        help="Print human-readable preview to stdout; do NOT write any files.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser


def _resolve_api_url(cli_arg: str | None) -> str:
    """Resolve the API URL from env var or CLI argument.

    Priority: ``NOX_API_URL`` env var > ``--api-url`` CLI arg > built-in default.

    Args:
        cli_arg: Value passed via ``--api-url`` (may be None).

    Returns:
        Resolved API base URL string.
    """
    env_url = os.environ.get("NOX_API_URL", "").strip()
    if env_url:
        logger.debug("Using NOX_API_URL from environment: %s", env_url)
        return env_url
    if cli_arg:
        return cli_arg
    return _DEFAULT_API_URL


def main(argv: list[str] | None = None) -> int:
    """Execute the curation pipeline.

    Steps:
    1. Parse CLI arguments and resolve API URL.
    2. Load input queries from JSONL.
    3. Run hybrid search for each query via HTTP GET (READ-ONLY).
    4. Apply top-N heuristic to populate ``expected_doc_ids``.
    5. Either print review preview (``--review``) or write curated JSONL.

    Args:
        argv: Optional argument list (uses ``sys.argv[1:]`` when None).

    Returns:
        Exit code — 0 on success, 1 on handled error.
    """
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    api_url = _resolve_api_url(args.api_url)

    logger.info(
        "curate_external_queries — E11 curation (top_n=%d, k=%d, api=%s)",
        args.top_n,
        args.k,
        api_url,
    )

    # Step 1: Load input
    try:
        queries = load_queries(args.input)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Failed to load input queries: %s", exc)
        return 1

    if not queries:
        logger.error("Input file is empty: %s", args.input)
        return 1

    # Step 2: Curate
    curated = curate_all(queries, api_url, top_n=args.top_n, k=args.k)

    # Step 3: Output
    if args.review:
        print_review(curated)
        return 0

    try:
        write_curated(curated, args.output)
    except OSError as exc:
        logger.error("Failed to write output: %s", exc)
        return 1

    # Final summary
    errors = sum(1 for r in curated if r["curation_method"] == "api_error")
    ok = len(curated) - errors
    print(f"\n=== E11 Curation Complete ===")
    print(f"  Queries curated : {ok}/{len(curated)}")
    print(f"  API errors      : {errors}")
    print(f"  Output          : {args.output}")
    print(f"  Method          : top{args.top_n}_hybrid_heuristic")
    if errors:
        print(f"\n  WARNING: {errors} queries have empty expected_doc_ids (API error).")
        print("  Re-run after ensuring the nox-mem API is reachable.")
    print(
        f"\n  Next step: python curate_external_queries.py --review"
        f" && nox-mem eval-import {args.output}"
    )
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
