"""
temporal_aware_retrieve.py — temporal-aware retrieval wrapper.

Wraps standard nox-mem hybrid retrieval (POST /api/search) with a
post-retrieval re-rank pass using `lib/temporal_scoring`. Two entry points:

  1. `retrieve_temporal_aware(...)`: live HTTP path for adapter_nox_mem.py
     (called inside the per-QA loop, replaces direct `search_api(...)`).
  2. `rerank_existing_records(...)`: offline path for generation-only re-runs
     over an existing baseline JSONL (re-orders `retrieved_texts` &
     `retrieved_chunk_ids` in place, no new HTTP calls). Used by the
     generation-pass companion script when budget rules out re-ingest.

Behaviour:
  - For temporal-class queries (LoCoMo cat=2, or is_temporal_query=True),
    re-rank the top-K chunks by `(1-alpha)*norm_retrieval + alpha*temporal_proximity`.
  - For non-temporal queries, return original order unchanged.
  - Always preserves the same length (no chunk drop).

Tuning knobs:
  - alpha (default 0.5): weight of temporal_score in blend.
  - retrieve_k (default 30): fetch larger pool than final top-K so re-rank
    has room to surface date-aligned chunks the original ranker missed.
  - keep_top_k (default 20): truncate to this many after re-rank (matches
    adapter top_k=20).

Public exports:
  - retrieve_temporal_aware(...)
  - rerank_existing_records(records, session_date_maps, alpha, keep_top_k)
  - SearchHit dict shape: {chunk_id, score, text, dia_id, raw}
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

# Allow flat imports inside lib/
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from temporal_scoring import (  # type: ignore[import-not-found]
    ScoredChunk,
    is_temporal_query,
    rerank_with_temporal_proximity,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_ALPHA = 0.5
DEFAULT_RETRIEVE_K = 30
DEFAULT_KEEP_TOP_K = 20
DEFAULT_SEARCH_TIMEOUT = 30


# ---------------------------------------------------------------------------
# Live HTTP path
# ---------------------------------------------------------------------------


def _search_api_raw(
    api_base: str, query: str, limit: int, timeout: int,
) -> tuple[list[dict], float, Optional[str]]:
    """Direct POST /api/search returning raw hits.

    Mirrors adapter_nox_mem.search_api but kept local so this module is
    importable without the adapter.
    """
    url = api_base.rstrip("/") + "/api/search"
    body = json.dumps(
        {"query": query, "limit": limit, "hybrid": True}
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"content-type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            j = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return [], (time.time() - t0) * 1000.0, f"{type(e).__name__}: {e}"
    ms = (time.time() - t0) * 1000.0
    if isinstance(j, list):
        return j, ms, None
    if isinstance(j, dict):
        hits = j.get("results") or j.get("hits") or []
        return hits if isinstance(hits, list) else [], ms, None
    return [], ms, None


def _to_chunk_dict(hit: dict) -> dict:
    """Normalize an API hit to {chunk_id, text, score, raw}."""
    cid = str(hit.get("chunk_id") or hit.get("id") or "")
    txt = str(hit.get("chunk_text") or hit.get("text") or hit.get("snippet") or "")
    try:
        sc = float(hit.get("score") or hit.get("relevance") or 0.0)
    except (TypeError, ValueError):
        sc = 0.0
    return {"chunk_id": cid, "text": txt, "score": sc, "raw": hit}


def retrieve_temporal_aware(
    api_base: str,
    query: str,
    *,
    session_date_map: Optional[dict[str, str]],
    category_name: Optional[str] = None,
    alpha: float = DEFAULT_ALPHA,
    retrieve_k: int = DEFAULT_RETRIEVE_K,
    keep_top_k: int = DEFAULT_KEEP_TOP_K,
    timeout: int = DEFAULT_SEARCH_TIMEOUT,
    force_on: Optional[bool] = None,
    has_date_fallback: bool = True,
) -> tuple[list[ScoredChunk], float, Optional[str]]:
    """Fetch top-retrieve_k hits and apply temporal-aware re-rank.

    Returns:
      (scored, retrieval_ms, error_str_or_None)
      `scored` is a list[ScoredChunk] of length <= keep_top_k.

    Notes:
      - When activate is False (non-temporal), the result is equivalent to
        the baseline top-keep_top_k (just sliced from the larger pool).
      - retrieve_k must be >= keep_top_k.
    """
    if retrieve_k < keep_top_k:
        retrieve_k = keep_top_k

    hits, ms, err = _search_api_raw(api_base, query, retrieve_k, timeout)
    if err:
        return [], ms, err

    chunks_in = [_to_chunk_dict(h) for h in hits if isinstance(h, dict)]
    scored = rerank_with_temporal_proximity(
        chunks_in,
        query=query,
        session_date_map=session_date_map,
        alpha=alpha,
        category_name=category_name,
        force_on=force_on,
        has_date_fallback=has_date_fallback,
    )
    return scored[:keep_top_k], ms, None


# ---------------------------------------------------------------------------
# Offline path — re-rank existing JSONL
# ---------------------------------------------------------------------------


def rerank_existing_records(
    records: list[dict],
    session_date_maps: dict[str, dict[str, str]],
    *,
    alpha: float = DEFAULT_ALPHA,
    keep_top_k: int = DEFAULT_KEEP_TOP_K,
    force_on: Optional[bool] = None,
    has_date_fallback: bool = True,
    progress_every: int = 200,
    log_file=None,
) -> dict:
    """Re-order `retrieved_*` arrays in-place across records.

    Each input record (from PR #404 baseline JSONL) carries:
      - sample_id, category_name, augmented_question
      - retrieved_chunk_ids: list[str]
      - retrieved_scores: list[float]
      - retrieved_texts: list[str]
      - retrieved_dia_ids: list[str]  (optional)

    After this function returns, those arrays have been re-ordered (and
    optionally truncated to keep_top_k) per the temporal-aware scorer.
    Stats are accumulated for the caller's reporting.

    Returns a stats dict:
      {n_records, n_temporal, n_reranked, n_changed_order, n_no_chunks,
       avg_chunks_with_date_pct, alpha, keep_top_k}
    """
    n_records = 0
    n_temporal = 0
    n_reranked = 0
    n_changed_order = 0
    n_no_chunks = 0
    sum_chunks_with_date = 0.0
    sum_total_chunks = 0.0

    def _log(msg: str) -> None:
        line = f"[temporal-rerank] {msg}"
        if log_file is not None:
            print(line, file=log_file, flush=True)
        print(line, file=sys.stderr, flush=True)

    for i, r in enumerate(records):
        n_records += 1
        sid = str(r.get("sample_id") or "")
        category = r.get("category_name") or ""
        question = (
            r.get("augmented_question")
            or r.get("question")
            or ""
        )

        texts = r.get("retrieved_texts") or []
        scores = r.get("retrieved_scores") or []
        chunk_ids = r.get("retrieved_chunk_ids") or []
        dia_ids = r.get("retrieved_dia_ids") or []

        if not texts:
            n_no_chunks += 1
            continue

        activate = (
            force_on
            if force_on is not None
            else is_temporal_query(question, category)
        )
        if activate:
            n_temporal += 1

        # Build chunks_in with parallel arrays
        n_in = min(len(texts), len(scores), len(chunk_ids))
        chunks_in = []
        for j in range(n_in):
            chunks_in.append({
                "chunk_id": str(chunk_ids[j]),
                "text": str(texts[j] or ""),
                "score": float(scores[j] or 0.0),
            })

        smap = session_date_maps.get(sid) or {}
        scored = rerank_with_temporal_proximity(
            chunks_in,
            query=question,
            session_date_map=smap,
            alpha=alpha,
            category_name=category,
            force_on=force_on,
            has_date_fallback=has_date_fallback,
        )

        # Coverage stats
        with_date = sum(1 for s in scored if s.parsed_chunk_date is not None)
        sum_chunks_with_date += with_date
        sum_total_chunks += len(scored)

        # Detect order change
        new_chunk_ids = [s.chunk_id for s in scored[:keep_top_k]]
        old_chunk_ids = [str(x) for x in chunk_ids[:keep_top_k]]
        if new_chunk_ids != old_chunk_ids:
            n_changed_order += 1
        if activate:
            n_reranked += 1

        # Build new dia_ids by mapping chunk_id -> original index for fallback
        old_id_to_dia: dict[str, str] = {}
        for j, cid in enumerate(chunk_ids):
            if j < len(dia_ids):
                old_id_to_dia[str(cid)] = str(dia_ids[j])

        new_texts = [s.text for s in scored[:keep_top_k]]
        new_scores = [s.final_score for s in scored[:keep_top_k]]
        new_dia_ids = []
        # Rebuild retrieved_dia_ids: union extracted-from-text + per-position
        for s in scored[:keep_top_k]:
            if s.dia_id:
                new_dia_ids.append(s.dia_id)
            else:
                fallback = old_id_to_dia.get(s.chunk_id, "")
                if fallback:
                    new_dia_ids.append(fallback)

        # Dedupe preserving order
        seen: set[str] = set()
        deduped_dia = []
        for d in new_dia_ids:
            if d and d not in seen:
                seen.add(d)
                deduped_dia.append(d)

        r["retrieved_chunk_ids"] = new_chunk_ids
        r["retrieved_scores"] = new_scores
        r["retrieved_texts"] = new_texts
        r["retrieved_dia_ids"] = deduped_dia
        # Annotate
        r["temporal_aware"] = bool(activate)
        r["temporal_alpha"] = float(alpha)
        r["temporal_chunks_with_date"] = with_date
        r["temporal_chunks_total"] = len(scored)
        r["temporal_proximity_scores"] = [s.temporal_score for s in scored[:keep_top_k]]

        if (i + 1) % progress_every == 0:
            _log(f"processed {i+1}/{len(records)} "
                 f"(temporal={n_temporal}, reordered={n_changed_order})")

    avg_pct = (
        100.0 * sum_chunks_with_date / sum_total_chunks
        if sum_total_chunks > 0
        else 0.0
    )

    stats = {
        "n_records": n_records,
        "n_temporal": n_temporal,
        "n_reranked": n_reranked,
        "n_changed_order": n_changed_order,
        "n_no_chunks": n_no_chunks,
        "avg_chunks_with_date_pct": avg_pct,
        "alpha": alpha,
        "keep_top_k": keep_top_k,
        "has_date_fallback": has_date_fallback,
    }
    _log(f"DONE: {json.dumps(stats)}")
    return stats


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _self_test() -> int:
    fail = 0

    def _assert(cond: bool, msg: str) -> None:
        nonlocal fail
        status = "OK" if cond else "FAIL"
        if not cond:
            fail += 1
        print(f"{status} {msg}")

    # Synthetic record exercising rerank_existing_records
    records = [
        {
            "sample_id": "conv-26",
            "qa_index": 0,
            "category_name": "temporal",
            "augmented_question": "When did Caroline join the LGBTQ group? Use DATE of CONVERSATION to answer with an approximate date.",
            "answer": "8 May 2023",
            "retrieved_chunk_ids": ["c-far", "c-near", "c-no-date"],
            "retrieved_scores": [0.95, 0.85, 0.75],
            "retrieved_texts": [
                "sample_id: conv-26 | session_id: session_5 | dia_id: D5:2\nirrelevant",
                "sample_id: conv-26 | session_id: session_1 | dia_id: D1:3\nLGBTQ support group",
                "no anchor here",
            ],
            "retrieved_dia_ids": ["D5:2", "D1:3"],
        },
        {
            "sample_id": "conv-26",
            "qa_index": 1,
            "category_name": "single_hop",
            "augmented_question": "What is Caroline's favorite color?",
            "answer": "blue",
            "retrieved_chunk_ids": ["c-far", "c-near"],
            "retrieved_scores": [0.95, 0.85],
            "retrieved_texts": [
                "session_id: session_5\nirrelevant",
                "session_id: session_1\nfoo",
            ],
            "retrieved_dia_ids": [],
        },
    ]
    smaps = {
        "conv-26": {
            "session_1": "8 May 2023",
            "session_5": "1 December 2023",
        },
    }

    # Temporal record has no explicit date in question, but we use cat=temporal
    # to force activation, and we test that session_1 doesn't move (no query date).
    # To test ordering shift, inject an explicit date:
    records[0]["augmented_question"] = (
        "What did Caroline do on 8 May 2023? "
        "Use DATE of CONVERSATION to answer with an approximate date."
    )

    rerank_existing_records(records, smaps, alpha=0.6, keep_top_k=3, log_file=None)
    r0 = records[0]
    _assert(r0["retrieved_chunk_ids"][0] == "c-near",
            f"rerank: explicit date 8 May 2023 -> c-near (session_1) first; got {r0['retrieved_chunk_ids']}")
    _assert(r0["temporal_aware"] is True,
            f"rerank: temporal_aware annotated True; got {r0['temporal_aware']}")

    r1 = records[1]
    _assert(r1["retrieved_chunk_ids"] == ["c-far", "c-near"],
            f"rerank: non-temporal passthrough preserves order; got {r1['retrieved_chunk_ids']}")
    _assert(r1["temporal_aware"] is False,
            f"rerank: non-temporal annotated False; got {r1['temporal_aware']}")

    print(f"\n{fail} failures")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(_self_test())
