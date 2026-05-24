#!/usr/bin/env python3
"""
Quick smoke: verify the refactored adapter (with E+F+H knobs at their
DEFAULT values) reproduces PR #318's hybrid@500 = 0.0918 baseline on
the @500 cap DB.

If this doesn't match within ±0.005, STOP — the refactor broke baseline.

Usage:
    source /tmp/q4-gemini-env.sh
    .venv/bin/python eval/q4-comparison/scripts/smoke_baseline_efh.py
"""
from __future__ import annotations

import importlib
import json
import math
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

EFH_DB = HERE / "cache" / "efh" / "nox-mem-hybrid-500.db"
DATASET_PATHS = {
    "locomo": HERE.parent / "locomo" / "dry-run-sample.json",
    "longmemeval": HERE.parent / "longmemeval" / "dry-run-sample.json",
}
EXPECTED = 0.0918  # from PR #318 audit


def load_queries():
    out = []
    for ds, p in DATASET_PATHS.items():
        d = json.loads(p.read_text())
        for r in d.get("records", []):
            out.append({
                "dataset": ds,
                "question_id": str(r.get("question_id") or r.get("id") or ""),
                "query": r.get("question") or r.get("query") or "",
                "gold_chunk_ids": list(
                    r.get("gold_chunk_ids") or r.get("answer_session_ids") or []
                ),
                "category": r.get("category_name") or r.get("question_type") or "unknown",
            })
    return out


def dcg(rels):
    return sum(
        r / math.log2(i + 1) for i, r in enumerate(rels, 1) if r > 0
    )


def ndcg10(retrieved, gold):
    gs = set(gold)
    if not gs:
        return 0.0
    rels = [1.0 if r in gs else 0.0 for r in retrieved[:10]]
    ideal = [1.0] * min(len(gs), 10)
    id_dcg = dcg(ideal)
    if id_dcg == 0:
        return 0.0
    return dcg(rels) / id_dcg


def main():
    if not EFH_DB.exists():
        print(f"ERROR: {EFH_DB} missing", file=sys.stderr)
        return 1

    # CLEAR all path-efh flags to lock in baseline
    for k in ("NOX_RETRIEVAL_KG", "NOX_RRF_K", "NOX_TOP_K_EXPAND",
              "NOX_QUERY_REWRITE"):
        os.environ.pop(k, None)
    os.environ["NOX_EVAL_MODE"] = "hybrid"
    os.environ["NOX_HYBRID_DB_PATH"] = str(EFH_DB)
    # CRITICAL: cap ingest at 500 so setup() doesn't try to grow the DB beyond
    # the cap (memory [[eval-harness-must-explicit-isolate-db]] discipline).
    # Without this, setup() with NOX_EVAL_MODE=hybrid resumes ingest because
    # _hybrid_schema_ready() returns True (DB has chunks) but no cap →
    # continues to full 6822 corpus, mutating the eval DB.
    os.environ["NOX_MEM_INGEST_LIMIT"] = "500"

    if "adapters.nox_mem" in sys.modules:
        nm = importlib.reload(sys.modules["adapters.nox_mem"])
    else:
        nm = importlib.import_module("adapters.nox_mem")

    nm._hybrid_con = None
    nm.setup(datasets=["locomo", "longmemeval"])

    queries = load_queries()
    print(f"[smoke] {len(queries)} queries", file=sys.stderr)

    ndcgs = []
    t0 = time.time()
    for q in queries:
        try:
            res = nm.search(q["query"], k=10)
        except Exception as e:
            print(f"[smoke] query error: {e}", file=sys.stderr)
            res = []
        rids = [r["id"] for r in res]
        ndcgs.append(ndcg10(rids, q["gold_chunk_ids"]))

    nm.teardown()
    elapsed = time.time() - t0
    mean_ndcg = sum(ndcgs) / len(ndcgs)
    delta = mean_ndcg - EXPECTED
    print(f"\n[smoke] baseline nDCG@10 = {mean_ndcg:.4f} (expected ~{EXPECTED})")
    print(f"[smoke] delta vs expected = {delta:+.4f}")
    print(f"[smoke] elapsed = {elapsed:.1f}s")

    if abs(delta) > 0.01:
        print(f"\n⚠ ⚠ BASELINE DRIFT >0.01 — refactor likely broke something.", file=sys.stderr)
        return 1
    print("[smoke] ✓ baseline matches PR #318 within ±0.01")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
