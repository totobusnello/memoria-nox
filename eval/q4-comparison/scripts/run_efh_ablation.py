#!/usr/bin/env python3
"""
Path E+F+H ablation runner — 4-config × 20-query smoke.

Configs:
    1. baseline        — hybrid@500 unchanged (matches PR #318 = 0.0918)
    2. E (KG)          — NOX_RETRIEVAL_KG=1
    3. E+F (KG+RRF)    — + NOX_RRF_K=20
    4. E+F+H (KG+RRF+expand) — + NOX_TOP_K_EXPAND=50

Each config drives the 20 dry-run queries (10 LoCoMo + 10 LongMemEval).
DB is the @500 cap LoCoMo-only hybrid DB built by build_efh_500_db.py +
build_efh_kg.py (KG tables in same DB, 576 entities / 1219 relations).

Output JSON: `output/efh_ablation_results.json`
Console: human-readable summary table + per-category breakdown.

Cost:
    - Embedding (query): 20 queries × 4 configs × 1 call = 80 calls.
      Models: gemini-embedding-001 (free tier covers this trivially).
    - KG entity extraction: 20 unique queries × 1 call (cached). KG boost
      runs in 3 of 4 configs but the cache means only 20 extra calls.
      Models: gemini-2.5-flash-lite (~$0.000005 per call × 20 = ~$0.0001).
    - Total per full run: <$0.001.
"""
from __future__ import annotations

import importlib
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent.parent  # eval/q4-comparison/
sys.path.insert(0, str(HERE))

OUTPUT_DIR = HERE / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EFH_DB = HERE / "cache" / "efh" / "nox-mem-hybrid-500.db"

DATASET_PATHS = {
    "locomo": HERE.parent / "locomo" / "dry-run-sample.json",
    "longmemeval": HERE.parent / "longmemeval" / "dry-run-sample.json",
}


CONFIGS: list[dict] = [
    {
        "label": "1_baseline",
        "name": "baseline (PR #318 hybrid@500)",
        "env": {
            # All unset — reproduces PR #318 byte-for-byte: RRF k=60,
            # k_fetch=30 (== k*3), no KG, no query rewrite.
        },
    },
    {
        "label": "2_E_kg",
        "name": "E (KG traversal)",
        "env": {
            "NOX_RETRIEVAL_KG": "1",
        },
    },
    {
        "label": "3_EF_kg_rrf20",
        "name": "E+F (KG + RRF k=20)",
        "env": {
            "NOX_RETRIEVAL_KG": "1",
            "NOX_RRF_K": "20",
        },
    },
    {
        "label": "4_EFH_kg_rrf20_expand50",
        "name": "E+F+H (KG + RRF k=20 + expand 50)",
        "env": {
            "NOX_RETRIEVAL_KG": "1",
            "NOX_RRF_K": "20",
            "NOX_TOP_K_EXPAND": "50",
        },
    },
    # Diagnostic configs — isolate each lever to attribute the +0.0022 gain in
    # config #3 (E+F) to its actual driver: KG or RRF tune?
    {
        "label": "5_F_only_rrf20",
        "name": "F only (RRF k=20, no KG)",
        "env": {
            "NOX_RRF_K": "20",
        },
    },
    {
        "label": "6_H_only_expand50",
        "name": "H only (top-k expansion=50, no KG, default RRF)",
        "env": {
            "NOX_TOP_K_EXPAND": "50",
        },
    },
]


def load_queries() -> list[dict]:
    out: list[dict] = []
    for ds_name, path in DATASET_PATHS.items():
        if not path.exists():
            print(f"WARN: missing {path}", file=sys.stderr)
            continue
        payload = json.loads(path.read_text())
        for row in payload.get("records", []):
            out.append(
                {
                    "dataset": ds_name,
                    "question_id": str(row.get("question_id") or row.get("id") or ""),
                    "query": row.get("question") or row.get("query") or "",
                    "gold_chunk_ids": list(
                        row.get("gold_chunk_ids") or row.get("answer_session_ids") or []
                    ),
                    "category": row.get("category_name")
                    or row.get("question_type")
                    or "unknown",
                }
            )
    return out


def dcg(relevances: list[float]) -> float:
    return sum(
        rel / math.log2(rank + 1)
        for rank, rel in enumerate(relevances, start=1)
        if rel > 0
    )


def ndcg_at_k(retrieved_ids: list[str], gold_ids: list[str], k: int = 10) -> float:
    gold_set = set(gold_ids)
    if not gold_set:
        return 0.0
    top_k = retrieved_ids[:k]
    rels = [1.0 if rid in gold_set else 0.0 for rid in top_k]
    ideal = [1.0] * min(len(gold_set), k)
    ideal_dcg = dcg(ideal)
    if ideal_dcg == 0:
        return 0.0
    return dcg(rels) / ideal_dcg


def mrr(retrieved_ids: list[str], gold_ids: list[str]) -> float:
    gold_set = set(gold_ids)
    if not gold_set:
        return 0.0
    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid in gold_set:
            return 1.0 / rank
    return 0.0


def recall_at_k(retrieved_ids: list[str], gold_ids: list[str], k: int = 10) -> float:
    gold_set = set(gold_ids)
    if not gold_set:
        return 0.0
    top_k = set(retrieved_ids[:k])
    return len(top_k & gold_set) / len(gold_set)


def hit_rate(retrieved_ids: list[str], gold_ids: list[str], k: int = 10) -> float:
    gold_set = set(gold_ids)
    if not gold_set:
        return 0.0
    top_k = retrieved_ids[:k]
    return 1.0 if any(rid in gold_set for rid in top_k) else 0.0


def aggregate_metrics(per_query: list[dict]) -> dict:
    ndcgs, mrrs, r10s, hits, latencies = [], [], [], [], []
    skipped = 0
    for r in per_query:
        gold = r.get("gold_chunk_ids") or []
        retrieved = [item["id"] for item in r.get("results") or []]
        if not gold:
            skipped += 1
            continue
        ndcgs.append(ndcg_at_k(retrieved, gold, k=10))
        mrrs.append(mrr(retrieved, gold))
        r10s.append(recall_at_k(retrieved, gold, k=10))
        hits.append(hit_rate(retrieved, gold, k=10))
        latencies.append(r.get("latency_ms") or 0.0)
    if not ndcgs:
        return {"n": 0, "n_skipped": skipped}
    return {
        "n": len(ndcgs),
        "n_skipped": skipped,
        "ndcg@10": round(statistics.mean(ndcgs), 4),
        "mrr": round(statistics.mean(mrrs), 4),
        "r@10": round(statistics.mean(r10s), 4),
        "hit@10": round(statistics.mean(hits), 4),
        "p50_latency_ms": round(statistics.median(latencies), 1),
        "p95_latency_ms": round(
            statistics.quantiles(latencies, n=20)[-1] if len(latencies) >= 20
            else max(latencies),
            1,
        ),
    }


def per_category_breakdown(per_query: list[dict]) -> dict[str, dict]:
    by_cat: dict[str, list[dict]] = {}
    for r in per_query:
        cat = r.get("category") or "unknown"
        by_cat.setdefault(cat, []).append(r)
    out = {}
    for cat, qs in by_cat.items():
        out[cat] = aggregate_metrics(qs)
        out[cat]["n_queries"] = len(qs)
    return out


def per_dataset_breakdown(per_query: list[dict]) -> dict[str, dict]:
    by_ds: dict[str, list[dict]] = {}
    for r in per_query:
        ds = r.get("dataset") or "unknown"
        by_ds.setdefault(ds, []).append(r)
    out = {}
    for ds, qs in by_ds.items():
        out[ds] = aggregate_metrics(qs)
        out[ds]["n_queries"] = len(qs)
    return out


def run_one_config(config: dict, queries: list[dict], k: int = 10) -> dict:
    """Run one ablation config end-to-end. Returns per-query records + metrics."""
    label = config["label"]
    print(f"\n[ablation] ===== {label}: {config['name']} =====", file=sys.stderr)

    # Set env vars for this config (cleanup at end)
    env_keys = {
        "NOX_RETRIEVAL_KG",
        "NOX_RRF_K",
        "NOX_TOP_K_EXPAND",
        "NOX_QUERY_REWRITE",
    }
    saved = {k: os.environ.get(k) for k in env_keys}
    for k_env in env_keys:
        os.environ.pop(k_env, None)
    for k_env, v in config["env"].items():
        os.environ[k_env] = v

    # Always isolate to the @500 cap hybrid DB (with KG)
    os.environ["NOX_EVAL_MODE"] = "hybrid"
    os.environ["NOX_HYBRID_DB_PATH"] = str(EFH_DB)
    # Cap ingest at 500 so setup() never tries to grow the DB beyond the
    # @500 LoCoMo subset (we built it offline via build_efh_500_db.py;
    # without this cap setup() resumes ingest from the corpus loader and
    # mutates the eval DB — same trap that bit the smoke run).
    os.environ["NOX_MEM_INGEST_LIMIT"] = "500"

    # Reload nox_mem adapter so module-level state is fresh
    if "adapters.nox_mem" in sys.modules:
        nm = importlib.reload(sys.modules["adapters.nox_mem"])
    else:
        nm = importlib.import_module("adapters.nox_mem")

    nm._hybrid_con = None
    nm._hybrid_db_path = None
    nm._hybrid_dim = None
    # Reset KG cache so each config measures cold start fairly. But within a
    # config, repeat queries hit the cache (matches prod behaviour).
    nm._kg_query_entities_cache.clear()
    nm._kg_query_calls = 0
    nm._kg_query_errors = 0
    nm._rewrite_calls = 0
    nm._rewrite_errors = 0
    nm._rewrite_cache.clear()

    # Setup (opens DB, no re-ingest since rows already present)
    nm.setup(datasets=["locomo", "longmemeval"])

    results: list[dict] = []
    n_err = 0
    t_start = time.time()
    for q in queries:
        t0 = time.perf_counter()
        try:
            ranked = nm.search(q["query"], k=k)
            lat = (time.perf_counter() - t0) * 1000
            results.append(
                {
                    **q,
                    "results": ranked,
                    "latency_ms": round(lat, 2),
                    "error": None,
                }
            )
        except Exception as exc:
            lat = (time.perf_counter() - t0) * 1000
            n_err += 1
            results.append(
                {
                    **q,
                    "results": [],
                    "latency_ms": round(lat, 2),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    nm.teardown()
    elapsed = time.time() - t_start

    metrics = aggregate_metrics(results)
    by_cat = per_category_breakdown(results)
    by_ds = per_dataset_breakdown(results)

    kg_stats = nm.get_kg_stats()
    rewrite_stats = nm.get_rewrite_stats()

    print(
        f"[ablation] {label}: nDCG@10={metrics.get('ndcg@10')} "
        f"MRR={metrics.get('mrr')} R@10={metrics.get('r@10')} "
        f"hit={metrics.get('hit@10')} p50={metrics.get('p50_latency_ms')}ms "
        f"errors={n_err} ({elapsed:.1f}s)",
        file=sys.stderr,
    )

    # Restore saved env
    for k_env, v in saved.items():
        if v is None:
            os.environ.pop(k_env, None)
        else:
            os.environ[k_env] = v

    return {
        "label": label,
        "name": config["name"],
        "env": config["env"],
        "metrics_aggregate": metrics,
        "per_dataset": by_ds,
        "per_category": by_cat,
        "kg_stats": kg_stats,
        "rewrite_stats": rewrite_stats,
        "n_errors": n_err,
        "elapsed_s": round(elapsed, 1),
        "queries": results,
    }


def main() -> int:
    if not EFH_DB.exists():
        print(f"ERROR: efh DB missing at {EFH_DB}. Run build_efh_500_db.py first.", file=sys.stderr)
        return 1

    queries = load_queries()
    print(f"[ablation] loaded {len(queries)} queries", file=sys.stderr)
    if not queries:
        return 1

    all_results = []
    for cfg in CONFIGS:
        all_results.append(run_one_config(cfg, queries))

    # Build comparison table
    print("\n" + "=" * 92)
    print("PATH E+F+H ABLATION — hybrid@500 cap (LoCoMo first 500 chunks)")
    print("=" * 92)
    print(
        f"{'Config':<40} {'nDCG@10':>9} {'MRR':>7} {'R@10':>7} "
        f"{'hit@10':>7} {'p50ms':>7} {'p95ms':>7}"
    )
    print("-" * 92)
    base = all_results[0]["metrics_aggregate"]
    base_ndcg = base.get("ndcg@10", 0.0) or 0.0
    for r in all_results:
        m = r["metrics_aggregate"]
        row = (
            f"{r['label'][:40]:<40} "
            f"{m.get('ndcg@10', 0.0):>9.4f} "
            f"{m.get('mrr', 0.0):>7.4f} "
            f"{m.get('r@10', 0.0):>7.4f} "
            f"{m.get('hit@10', 0.0):>7.4f} "
            f"{m.get('p50_latency_ms', 0.0):>7.1f} "
            f"{m.get('p95_latency_ms', 0.0):>7.1f}"
        )
        print(row)

    # Per-dataset table (compare LoCoMo only, since LongMemEval is uniformly 0)
    print("\nPer-dataset nDCG@10:")
    print(f"{'Config':<40} {'LoCoMo':>9} {'LongMemEval':>13}")
    print("-" * 64)
    for r in all_results:
        l = r["per_dataset"].get("locomo", {})
        lme = r["per_dataset"].get("longmemeval", {})
        print(
            f"{r['label'][:40]:<40} "
            f"{l.get('ndcg@10', 0.0):>9.4f} "
            f"{lme.get('ndcg@10', 0.0):>13.4f}"
        )

    # Per-category breakdown (LoCoMo only — LongMemEval has 0 useful signal)
    print("\nPer-category nDCG@10 (LoCoMo + LongMemEval combined):")
    cats = sorted({c for r in all_results for c in r["per_category"].keys()})
    header = f"{'Category':<25}" + "".join(f"{r['label'][:18]:>20}" for r in all_results)
    print(header)
    print("-" * len(header))
    for cat in cats:
        row = f"{cat[:25]:<25}"
        for r in all_results:
            v = r["per_category"].get(cat, {}).get("ndcg@10")
            row += f"{v if v is not None else 0.0:>20.4f}"
        print(row)

    # Delta vs baseline + regression check
    print("\n" + "=" * 92)
    print("Δ vs baseline (PR #318 hybrid@500 = baseline of this run)")
    print("=" * 92)
    print(f"{'Config':<40} {'nDCG Δ':>9} {'% lift':>9} {'verdict':>20}")
    print("-" * 92)
    REGRESSION_THRESHOLD = -0.05
    WIN_THRESHOLD = 0.05
    mem0_500_ndcg = 0.1315
    verdicts = []
    for r in all_results[1:]:
        m = r["metrics_aggregate"]
        ndcg = m.get("ndcg@10", 0.0) or 0.0
        delta = ndcg - base_ndcg
        pct = (delta / base_ndcg * 100) if base_ndcg > 0 else 0.0
        if ndcg >= mem0_500_ndcg:
            verdict = "BEATS mem0@500"
        elif delta >= WIN_THRESHOLD:
            verdict = "win vs baseline"
        elif delta <= REGRESSION_THRESHOLD:
            verdict = "REGRESSION"
        elif delta > 0:
            verdict = "marginal +"
        else:
            verdict = "marginal -"
        verdicts.append((r["label"], delta, pct, verdict))
        print(
            f"{r['label'][:40]:<40} "
            f"{delta:>+9.4f} "
            f"{pct:>+8.2f}% "
            f"{verdict:>20}"
        )

    # Per-category regression check (each config × each category)
    print("\nPer-category regression check (apply G10b discipline):")
    print("(>=+5% lift = potential win; <=-5% = potential regression)")
    print()
    for cfg_result in all_results[1:]:
        label = cfg_result["label"]
        flags = []
        for cat, m in cfg_result["per_category"].items():
            base_cat = base.get("ndcg@10")
            base_cat_full = all_results[0]["per_category"].get(cat, {})
            bcv = base_cat_full.get("ndcg@10")
            cur = m.get("ndcg@10")
            if bcv is None or cur is None:
                continue
            if bcv == 0:
                continue
            pct = (cur - bcv) / bcv * 100
            if pct >= 5.0:
                flags.append(f"  + {cat}: {bcv:.4f}→{cur:.4f} (+{pct:.1f}%)")
            elif pct <= -5.0:
                flags.append(f"  - {cat}: {bcv:.4f}→{cur:.4f} ({pct:.1f}%) ⚠ REGRESSION")
        print(f"[{label}]")
        if flags:
            print("\n".join(flags))
        else:
            print("  (no >5% deltas vs baseline per category — neutral)")
        print()

    # Verdict block
    print("=" * 92)
    print("VERDICT")
    print("=" * 92)
    best_label = max(
        all_results,
        key=lambda r: r["metrics_aggregate"].get("ndcg@10", 0.0) or 0.0,
    )
    best_ndcg = best_label["metrics_aggregate"].get("ndcg@10", 0.0) or 0.0
    gap_to_mem0 = best_ndcg - mem0_500_ndcg
    print(f"Best config: {best_label['label']} ({best_label['name']})")
    print(f"  nDCG@10 = {best_ndcg:.4f}")
    print(f"  baseline (PR #318) = {base_ndcg:.4f}  Δ = {best_ndcg - base_ndcg:+.4f}")
    print(f"  mem0@500 reference = {mem0_500_ndcg:.4f}  Δ = {gap_to_mem0:+.4f}")
    if best_ndcg >= mem0_500_ndcg:
        print(f"  ► WIN: combo @ 500 beats mem0@500.")
    elif gap_to_mem0 >= -0.02:
        print(f"  ► MARGINAL: gap closes to <-0.02. Lab Q1 P1 chunk summariser → closure.")
    elif best_ndcg <= base_ndcg - 0.05:
        print(f"  ► REGRESSION: rolled back, document negative result.")
    else:
        print(f"  ► NEUTRAL: no material change vs baseline; ship-no-ship neutral.")

    # Persist JSON output (drop per-query results to keep file < ~1 MB; full
    # raw written separately).
    summary = {
        "meta": {
            "description": "Path E+F+H ablation — hybrid@500 + KG traversal + RRF tune + top-k expansion",
            "mission": "close gap to mem0@500 (-0.0397) without changing model",
            "baseline_reference_pr": 318,
            "mem0_500_ndcg_reference": mem0_500_ndcg,
            "n_queries": len(queries),
            "datasets": ["locomo", "longmemeval"],
            "db": str(EFH_DB),
            "harness_version": "efh_ablation_v1",
        },
        "configs": [
            {
                "label": r["label"],
                "name": r["name"],
                "env": r["env"],
                "metrics_aggregate": r["metrics_aggregate"],
                "per_dataset": r["per_dataset"],
                "per_category": r["per_category"],
                "kg_stats": r["kg_stats"],
                "rewrite_stats": r["rewrite_stats"],
                "n_errors": r["n_errors"],
                "elapsed_s": r["elapsed_s"],
            }
            for r in all_results
        ],
        "verdicts": [
            {"label": v[0], "ndcg_delta": v[1], "pct_lift": v[2], "verdict": v[3]}
            for v in verdicts
        ],
        "best_config": best_label["label"],
        "best_ndcg": best_ndcg,
        "gap_to_mem0_500": gap_to_mem0,
    }
    out_path = OUTPUT_DIR / "efh_ablation_results.json"
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nSummary written: {out_path}")

    raw_path = OUTPUT_DIR / "efh_ablation_raw.json"
    raw_path.write_text(
        json.dumps(
            {
                "meta": summary["meta"],
                "configs": [
                    {
                        "label": r["label"],
                        "name": r["name"],
                        "env": r["env"],
                        "queries": r["queries"],
                    }
                    for r in all_results
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    print(f"Raw per-query results: {raw_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
