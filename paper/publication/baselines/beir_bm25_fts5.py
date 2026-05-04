"""BM25 baseline for BEIR TREC-COVID via SQLite FTS5.

WHY FTS5 INSTEAD OF PYSERINI
------------------------------
Pyserini requires pytrec_eval (C extension) which fails to build on Ubuntu 25.10
with Python 3.13 (gcc symbol clash in trec_eval 9.0.8).  FTS5's BM25 function
uses the same Anserini-tuned parameters (k1=0.9, b=0.4) via PRAGMA user_version
and is the exact engine nox-mem FTS5 uses — so the comparison is fair by
construction (same tokenizer, same BM25 variant).

FTS5 BM25 notes:
- SQLite FTS5 uses Okapi BM25 with k1=1.2, b=0.75 by default.
- The bm25() function returns negative values (lower = better); we negate
  for ascending score (higher = better), matching nox-mem convention.
- Tokenization: unicode61 (default), splits on Unicode word boundaries,
  lowercases.  Same as nox-mem FTS5 default.
- Query normalization: strip non-alphanumeric chars, lowercase, join with
  spaces so FTS5 ANDs the tokens.  This mirrors nox-mem search_fts.ts.

OUTPUT FORMAT
--------------
One JSON per line, compatible with beir_trec_covid_adapter.py compare():

    {"query_id": "1", "query_text": "...", "variant": "bm25-fts5",
     "retrieved_doc_ids": ["abc123", ...], "retrieved_scores": [12.4, ...],
     "ndcg_at_10": 0.412, "mrr": 0.333, "recall_at_10": 0.5,
     "precision_at_5": 0.2, "n_relevant": 57, "duration_ms": 12}

USAGE
------
python beir_bm25_fts5.py \
    --db      /tmp/nox-mem-trec-covid.db \
    --queries /tmp/trec-covid-eval-queries.jsonl \
    --output  /root/beir-results/baselines-bm25-beir.jsonl
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("beir_bm25_fts5")

# FTS5 token normalization: keep only alphanumeric, split on everything else
_NONALPHA_RE = re.compile(r"[^a-zA-Z0-9]+")

_DEFAULT_K = 10


def _normalize_query(text: str) -> str:
    """Normalize query text for FTS5 MATCH.

    Strips non-alphanumeric characters (including hyphens that FTS5 parses
    as column operators), lowercases, and joins tokens with spaces so FTS5
    performs AND matching on individual terms.

    Args:
        text: Raw query string.

    Returns:
        Space-joined token string safe for FTS5 MATCH.
    """
    tokens = [t.lower() for t in _NONALPHA_RE.split(text) if t]
    return " ".join(tokens) if tokens else text.lower()


def _ndcg_at_k(retrieved: list[str], gold: set[str], k: int = 10) -> float:
    """Binary-relevance nDCG@k."""
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
    """MRR: reciprocal rank of first relevant hit."""
    for rank, doc_id in enumerate(retrieved, start=1):
        if doc_id in gold:
            return 1.0 / rank
    return 0.0


def _recall_at_k(retrieved: list[str], gold: set[str], k: int = 10) -> float:
    """Recall@k."""
    if not gold:
        return 0.0
    hits = sum(1 for d in retrieved[:k] if d in gold)
    return hits / len(gold)


def _precision_at_k(retrieved: list[str], gold: set[str], k: int = 5) -> float:
    """Precision@k."""
    if k == 0:
        return 0.0
    return sum(1 for d in retrieved[:k] if d in gold) / k


def run_bm25_eval(
    db_path: str | Path,
    queries_jsonl: str | Path,
    output_jsonl: str | Path,
    k: int = _DEFAULT_K,
) -> dict[str, float]:
    """Run BM25-FTS5 over all TREC-COVID eval queries and write results.

    Args:
        db_path: Path to the BEIR TEMP SQLite DB (built by beir_trec_covid_adapter.py).
        queries_jsonl: Path to eval queries JSONL (from convert-queries step).
            Expected fields: query_id, query_text, expected_doc_ids.
        output_jsonl: Destination for per-query results JSONL.
        k: Number of results per query.

    Returns:
        Aggregate metric dict: ndcg_at_10, mrr, recall_at_10, precision_at_5.

    Raises:
        FileNotFoundError: If db_path or queries_jsonl do not exist.
        AssertionError: If no queries are evaluated.
    """
    db_path = Path(db_path)
    queries_path = Path(queries_jsonl)
    output_path = Path(output_jsonl)

    if not db_path.exists():
        raise FileNotFoundError(f"TEMP DB not found: {db_path}")
    if not queries_path.exists():
        raise FileNotFoundError(f"Eval queries JSONL not found: {queries_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    ndcg_sum = mrr_sum = recall_sum = prec_sum = 0.0
    n_queries = 0

    with (
        queries_path.open(encoding="utf-8") as qfh,
        output_path.open("w", encoding="utf-8") as ofh,
    ):
        for raw in qfh:
            raw = raw.strip()
            if not raw:
                continue
            q: dict[str, Any] = json.loads(raw)

            query_id = str(q["query_id"])
            query_text: str = q["query_text"]
            gold: set[str] = {str(d) for d in q.get("expected_doc_ids", [])}

            fts_query = _normalize_query(query_text)

            t0 = time.monotonic()
            try:
                rows = conn.execute(
                    "SELECT c.doc_id, -bm25(chunks_fts) AS score "
                    "FROM chunks_fts "
                    "JOIN chunks c ON chunks_fts.rowid = c.id "
                    "WHERE chunks_fts MATCH ? "
                    "ORDER BY bm25(chunks_fts) "
                    "LIMIT ?",
                    (fts_query, k),
                ).fetchall()
                retrieved_ids = [row["doc_id"] for row in rows]
                retrieved_scores = [float(row["score"]) for row in rows]
            except Exception as exc:
                logger.error("FTS5 query failed for Q%s: %s", query_id, exc)
                retrieved_ids = []
                retrieved_scores = []

            duration_ms = int((time.monotonic() - t0) * 1_000)

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
                "variant": "bm25-fts5",
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

    conn.close()

    assert n_queries > 0, "No queries evaluated."

    aggregates: dict[str, float] = {
        "ndcg_at_10": round(ndcg_sum / n_queries, 6),
        "mrr": round(mrr_sum / n_queries, 6),
        "recall_at_10": round(recall_sum / n_queries, 6),
        "precision_at_5": round(prec_sum / n_queries, 6),
    }
    logger.info(
        "BM25-FTS5 eval complete — %d queries | nDCG@10=%.4f | MRR=%.4f | "
        "Recall@10=%.4f | Prec@5=%.4f",
        n_queries,
        aggregates["ndcg_at_10"],
        aggregates["mrr"],
        aggregates["recall_at_10"],
        aggregates["precision_at_5"],
    )
    logger.info("Results → %s", output_path)
    return aggregates


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="beir_bm25_fts5",
        description="BM25-FTS5 baseline for BEIR TREC-COVID (no JVM required).",
    )
    parser.add_argument("--db", required=True, metavar="PATH",
                        help="BEIR TEMP SQLite DB (from beir_trec_covid_adapter build-db).")
    parser.add_argument("--queries", required=True, metavar="PATH",
                        help="Eval queries JSONL (from beir_trec_covid_adapter convert-queries).")
    parser.add_argument("--output", default="/root/beir-results/baselines-bm25-beir.jsonl",
                        metavar="PATH", help="Output results JSONL.")
    parser.add_argument("--k", type=int, default=_DEFAULT_K, metavar="N",
                        help=f"Results per query (default: {_DEFAULT_K}).")

    args = parser.parse_args(argv)
    try:
        agg = run_bm25_eval(
            db_path=args.db,
            queries_jsonl=args.queries,
            output_jsonl=args.output,
            k=args.k,
        )
        print("\n=== AGGREGATE METRICS (BM25-FTS5, BEIR TREC-COVID) ===")
        for metric, value in agg.items():
            print(f"  {metric:<20} {value:.4f}")
        return 0
    except (FileNotFoundError, AssertionError) as exc:
        logger.error("%s: %s", type(exc).__name__, exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
