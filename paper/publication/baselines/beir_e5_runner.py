"""multilingual-e5-base dense retrieval baseline for BEIR TREC-COVID.

Adapter between beir_trec_covid_adapter.py TEMP DB and the e5 embedding
pipeline.  Embeds all chunks in the TEMP DB, caches to .npz, then runs
cosine retrieval for all 50 eval queries and writes per-query JSONL in the
same format as beir_bm25_fts5.py (beir_trec_covid_adapter compare-compatible).

WHY THIS IS NOT e5_multilingual_baseline.py
--------------------------------------------
e5_multilingual_baseline.py targets the production nox-mem DB with PT-BR
golden queries (different query format: {"query": ..., "expected_chunk_ids": [...]}).
This runner targets the BEIR TEMP DB with TREC-COVID queries in the
convert-queries format ({"query_id": ..., "query_text": ..., "expected_doc_ids": [...]}).
Query-doc ID reconciliation uses BEIR string doc_ids (chunks.doc_id column).

PROGRESS LOGGING
-----------------
Every 5 minutes: appends to /var/log/nox-mem/beir-progress.log:
    timestamp | docs_embedded=N | eta=Xh Ym

USAGE
------
python beir_e5_runner.py \
    --db      /tmp/nox-mem-trec-covid.db \
    --queries /tmp/trec-covid-eval-queries.jsonl \
    --npz     /root/beir-results/e5-trec-covid.npz \
    --output  /root/beir-results/baselines-e5-beir.jsonl

OPTIONS
--------
--batch-size N    Rows per encode() call (default: 32; increase to 64 on >=8GB RAM)
--force           Re-embed even if .npz cache exists
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("beir_e5_runner")

MODEL_NAME = "intfloat/multilingual-e5-base"
EMBEDDING_DIM = 768
PREFIX_PASSAGE = "passage: "
PREFIX_QUERY = "query: "
SYSTEM_TAG = "multilingual-e5-base"

_DEFAULT_K = 10
_DEFAULT_BATCH_SIZE = 32
_PROGRESS_LOG = "/var/log/nox-mem/beir-progress.log"
_PROGRESS_INTERVAL_SEC = 300  # 5 minutes


def _log_progress(msg: str) -> None:
    """Append progress line to /var/log/nox-mem/beir-progress.log."""
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    line = f"{ts} | {msg}\n"
    try:
        with open(_PROGRESS_LOG, "a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        pass  # log dir may not exist in test environments
    logger.info(msg)


def _ndcg_at_k(retrieved: list[str], gold: set[str], k: int = 10) -> float:
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
    for rank, doc_id in enumerate(retrieved, start=1):
        if doc_id in gold:
            return 1.0 / rank
    return 0.0


def _recall_at_k(retrieved: list[str], gold: set[str], k: int = 10) -> float:
    if not gold:
        return 0.0
    return sum(1 for d in retrieved[:k] if d in gold) / len(gold)


def _precision_at_k(retrieved: list[str], gold: set[str], k: int = 5) -> float:
    if k == 0:
        return 0.0
    return sum(1 for d in retrieved[:k] if d in gold) / k


def embed_corpus(
    db_path: str | Path,
    npz_path: str | Path,
    batch_size: int = _DEFAULT_BATCH_SIZE,
    force: bool = False,
) -> tuple[np.ndarray, list[str]]:
    """Embed all chunks in the TEMP DB and cache to .npz.

    Args:
        db_path: Path to BEIR TEMP SQLite DB.
        npz_path: Output .npz cache path.
        batch_size: Rows per SentenceTransformer.encode() call.
        force: If True, re-embed even if cache exists.

    Returns:
        Tuple of (embedding_matrix, doc_id_list) where embedding_matrix is
        shape (N, 768) float32 and doc_id_list[i] is the BEIR string doc_id
        for embedding_matrix[i].

    Raises:
        FileNotFoundError: If db_path does not exist.
        ImportError: If sentence_transformers is not installed.
    """
    db_path = Path(db_path)
    npz_path = Path(npz_path)

    if not db_path.exists():
        raise FileNotFoundError(f"TEMP DB not found: {db_path}")

    # Cache hit
    if npz_path.exists() and not force:
        logger.info("Loading cached embeddings from %s", npz_path)
        data = np.load(str(npz_path), allow_pickle=True)
        matrix = data["embeddings"].astype(np.float32)
        doc_ids = list(data["doc_ids"])
        logger.info("Cache loaded: %d embeddings (dim=%d)", len(doc_ids), matrix.shape[1])
        return matrix, doc_ids

    # Load model
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "sentence_transformers not installed. Run:\n"
            "  pip install 'sentence-transformers>=3.0'"
        ) from exc

    logger.info("Loading model: %s", MODEL_NAME)
    model = SentenceTransformer(MODEL_NAME)

    # Load chunks from DB
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT id, doc_id, chunk_text FROM chunks ORDER BY id")
    rows = cursor.fetchall()
    conn.close()

    n_total = len(rows)
    logger.info("Embedding %d chunks in batches of %d", n_total, batch_size)
    _log_progress(f"docs_embedded=0 | total={n_total} | phase=embed_start")

    all_embeddings: list[np.ndarray] = []
    doc_ids: list[str] = []
    t_start = time.monotonic()
    last_progress = t_start

    for batch_start in range(0, n_total, batch_size):
        batch = rows[batch_start : batch_start + batch_size]
        texts = [PREFIX_PASSAGE + (row["chunk_text"] or "") for row in batch]

        emb: np.ndarray = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        # Defensive re-normalize (belt and suspenders)
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        norms = np.where(norms < 1e-10, 1.0, norms)
        emb = (emb / norms).astype(np.float32)

        all_embeddings.append(emb)
        doc_ids.extend(row["doc_id"] for row in batch)

        # 5-minute progress log
        now = time.monotonic()
        if now - last_progress >= _PROGRESS_INTERVAL_SEC:
            done = batch_start + len(batch)
            elapsed = now - t_start
            rate = done / elapsed if elapsed > 0 else 1.0
            eta_sec = (n_total - done) / rate if rate > 0 else 0
            eta_str = f"{int(eta_sec // 3600)}h {int((eta_sec % 3600) // 60)}m"
            _log_progress(
                f"docs_embedded={done} | total={n_total} | "
                f"rate={rate:.1f}/s | eta={eta_str}"
            )
            last_progress = now

    matrix = np.vstack(all_embeddings).astype(np.float32)
    logger.info("Embedding complete: shape=%s", matrix.shape)

    # Save cache
    npz_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        str(npz_path),
        embeddings=matrix,
        doc_ids=np.array(doc_ids, dtype=object),
    )
    logger.info("Embeddings cached → %s", npz_path)
    _log_progress(f"docs_embedded={n_total} | total={n_total} | phase=embed_done")

    return matrix, doc_ids


def run_e5_eval(
    db_path: str | Path,
    queries_jsonl: str | Path,
    npz_path: str | Path,
    output_jsonl: str | Path,
    k: int = _DEFAULT_K,
    batch_size: int = _DEFAULT_BATCH_SIZE,
    force: bool = False,
) -> dict[str, float]:
    """Embed, retrieve, and evaluate using multilingual-e5-base.

    Args:
        db_path: BEIR TEMP SQLite DB path.
        queries_jsonl: Eval queries JSONL from convert-queries step.
        npz_path: .npz cache path for corpus embeddings.
        output_jsonl: Destination for per-query results JSONL.
        k: Results per query.
        batch_size: Encoding batch size.
        force: Force re-embedding.

    Returns:
        Aggregate metric dict.
    """
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore[import]
    except ImportError as exc:
        raise ImportError("sentence_transformers not installed.") from exc

    queries_path = Path(queries_jsonl)
    output_path = Path(output_jsonl)

    if not queries_path.exists():
        raise FileNotFoundError(f"Eval queries not found: {queries_path}")

    # Load / embed corpus
    matrix, doc_ids = embed_corpus(db_path, npz_path, batch_size=batch_size, force=force)
    doc_id_to_idx: dict[str, int] = {did: i for i, did in enumerate(doc_ids)}

    # Load model for query encoding
    logger.info("Loading model for query encoding: %s", MODEL_NAME)
    model = SentenceTransformer(MODEL_NAME)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    ndcg_sum = mrr_sum = recall_sum = prec_sum = 0.0
    n_queries = 0

    _log_progress("phase=eval_start")

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

            t0 = time.monotonic()

            # Encode query with mandatory prefix
            q_vec: np.ndarray = model.encode(
                [PREFIX_QUERY + query_text],
                normalize_embeddings=True,
                show_progress_bar=False,
                convert_to_numpy=True,
            )[0].astype(np.float32)

            # Cosine similarity via dot product (both sides L2-normalized)
            scores = matrix @ q_vec  # shape: (N,)

            # Top-k indices
            if k < len(scores):
                top_k_idx = np.argpartition(scores, -k)[-k:]
                top_k_idx = top_k_idx[np.argsort(scores[top_k_idx])[::-1]]
            else:
                top_k_idx = np.argsort(scores)[::-1][:k]

            retrieved_ids = [doc_ids[i] for i in top_k_idx]
            retrieved_scores = [float(scores[i]) for i in top_k_idx]

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
                "variant": SYSTEM_TAG,
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
                    "Eval progress: %d/50 — nDCG@10=%.3f MRR=%.3f",
                    n_queries, ndcg_sum / n_queries, mrr_sum / n_queries,
                )

    assert n_queries > 0, "No queries evaluated."

    aggregates: dict[str, float] = {
        "ndcg_at_10": round(ndcg_sum / n_queries, 6),
        "mrr": round(mrr_sum / n_queries, 6),
        "recall_at_10": round(recall_sum / n_queries, 6),
        "precision_at_5": round(prec_sum / n_queries, 6),
    }
    logger.info(
        "E5 eval complete — %d queries | nDCG@10=%.4f | MRR=%.4f | "
        "Recall@10=%.4f | Prec@5=%.4f",
        n_queries,
        aggregates["ndcg_at_10"],
        aggregates["mrr"],
        aggregates["recall_at_10"],
        aggregates["precision_at_5"],
    )
    _log_progress(
        f"phase=eval_done | ndcg@10={aggregates['ndcg_at_10']:.4f} | "
        f"mrr={aggregates['mrr']:.4f}"
    )
    logger.info("Results → %s", output_path)
    return aggregates


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="beir_e5_runner",
        description="multilingual-e5-base dense retrieval for BEIR TREC-COVID.",
    )
    parser.add_argument("--db", required=True, metavar="PATH",
                        help="BEIR TEMP SQLite DB.")
    parser.add_argument("--queries", required=True, metavar="PATH",
                        help="Eval queries JSONL (from beir_trec_covid_adapter convert-queries).")
    parser.add_argument("--npz", default="/root/beir-results/e5-trec-covid.npz",
                        metavar="PATH", help="Corpus embeddings cache path.")
    parser.add_argument("--output", default="/root/beir-results/baselines-e5-beir.jsonl",
                        metavar="PATH", help="Output results JSONL.")
    parser.add_argument("--k", type=int, default=_DEFAULT_K)
    parser.add_argument("--batch-size", type=int, default=_DEFAULT_BATCH_SIZE)
    parser.add_argument("--force", action="store_true",
                        help="Force re-embedding even if .npz cache exists.")

    args = parser.parse_args(argv)

    try:
        agg = run_e5_eval(
            db_path=args.db,
            queries_jsonl=args.queries,
            npz_path=args.npz,
            output_jsonl=args.output,
            k=args.k,
            batch_size=args.batch_size,
            force=args.force,
        )
        print("\n=== AGGREGATE METRICS (multilingual-e5-base, BEIR TREC-COVID) ===")
        for metric, value in agg.items():
            print(f"  {metric:<20} {value:.4f}")
        return 0
    except (FileNotFoundError, ImportError, AssertionError) as exc:
        logger.error("%s: %s", type(exc).__name__, exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
