#!/usr/bin/env python3
"""
Path A2 — capped@500 + full benchmark of nox_mem_a2 adapter.

Reads the same 20 dry-run-sample queries that the cap-comparison script uses
(`run_cap_comparison.py`), measures nDCG@10 / MRR / R@10 / hit_rate / p50
latency at multiple caps, and emits:

  - staged-q4-a2/results.json   — raw numbers
  - staged-q4-a2/RESULTS.md     — verdict table + analysis (WIN/NEUTRAL/NEGATIVE)

Reference baselines (Sat 2026-05-24, PR #338 + Sat closure):
  nox_mem hybrid full corpus  nDCG@10 = 0.4509  (winner overall)
  nox_mem hybrid cap=500       nDCG@10 = 0.0918  (gap target)
  mem0 capped@500              nDCG@10 = 0.1315  (gap closer, ingest-side win)
  Gap to close:                Δ = +0.0397

WIN criterion: A2 nDCG@10 ≥ 0.1315 at cap=500. NEUTRAL: +0.01..+0.04. NEGATIVE: ≤-0.01.
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

REPO_ROOT = HERE.parent.parent
STAGED = REPO_ROOT / "staged-q4-a2"
STAGED.mkdir(parents=True, exist_ok=True)

# Baselines (Sat 2026-05-24)
BASELINE_HYBRID_FULL_NDCG = 0.4509
BASELINE_HYBRID_CAP500_NDCG = 0.0918
BASELINE_MEM0_CAP500_NDCG = 0.1315
GAP_TARGET = BASELINE_MEM0_CAP500_NDCG - BASELINE_HYBRID_CAP500_NDCG  # +0.0397


DATASET_PATHS = {
    "locomo": REPO_ROOT / "eval" / "locomo" / "dry-run-sample.json",
    "longmemeval": REPO_ROOT / "eval" / "longmemeval" / "dry-run-sample.json",
}


def load_all_queries() -> list[dict]:
    rows = []
    for name, p in DATASET_PATHS.items():
        if not p.exists():
            print(f"WARN: {p} missing — skipping {name}", file=sys.stderr)
            continue
        payload = json.loads(p.read_text())
        for r in payload.get("records", []):
            rows.append(
                {
                    "dataset": name,
                    "question_id": str(r.get("question_id") or r.get("id") or ""),
                    "query": r.get("question") or r.get("query") or "",
                    "gold_chunk_ids": list(
                        r.get("gold_chunk_ids") or r.get("answer_session_ids") or []
                    ),
                    "category": (
                        r.get("category_name")
                        or r.get("question_type")
                        or "unknown"
                    ),
                }
            )
    return rows


# ---------------------------------------------------------------------------
# Metrics (same as run_cap_comparison.py — verbatim)
# ---------------------------------------------------------------------------


def dcg(rels: list[float]) -> float:
    return sum(rel / math.log2(rank + 1) for rank, rel in enumerate(rels, 1) if rel > 0)


def ndcg_at_k(retrieved: list[str], gold: list[str], k: int = 10) -> float:
    g = set(gold)
    if not g:
        return 0.0
    rels = [1.0 if r in g else 0.0 for r in retrieved[:k]]
    ideal = [1.0] * min(len(g), k)
    idcg = dcg(ideal)
    if idcg == 0:
        return 0.0
    return dcg(rels) / idcg


def mrr_single(retrieved: list[str], gold: list[str]) -> float:
    g = set(gold)
    if not g:
        return 0.0
    for i, r in enumerate(retrieved, 1):
        if r in g:
            return 1.0 / i
    return 0.0


def recall_at_k(retrieved: list[str], gold: list[str], k: int = 10) -> float:
    g = set(gold)
    if not g:
        return 0.0
    return len(set(retrieved[:k]) & g) / len(g)


def hit_rate(retrieved: list[str], gold: list[str]) -> float:
    g = set(gold)
    if not g:
        return 0.0
    return 1.0 if any(r in g for r in retrieved) else 0.0


def compute(results: list[dict]) -> dict:
    ndcgs, mrrs, r10s, hits, lats = [], [], [], [], []
    skipped = 0
    for r in results:
        gold = r.get("gold_chunk_ids") or []
        retrieved = [x["id"] for x in r.get("results") or []]
        if not gold:
            skipped += 1
            continue
        ndcgs.append(ndcg_at_k(retrieved, gold))
        mrrs.append(mrr_single(retrieved, gold))
        r10s.append(recall_at_k(retrieved, gold))
        hits.append(hit_rate(retrieved, gold))
        lats.append(r.get("latency_ms") or 0.0)

    if not ndcgs:
        return {
            "n_queries": len(results), "n_scored": 0, "n_skipped_no_gold": skipped,
            "ndcg@10": None, "mrr": None, "r@10": None, "hit_rate": None,
            "p50_latency_ms": None, "p95_latency_ms": None,
        }
    sl = sorted(lats)
    p50 = sl[int(len(sl) * 0.50)]
    p95 = sl[min(int(len(sl) * 0.95), len(sl) - 1)]
    return {
        "n_queries": len(results), "n_scored": len(ndcgs),
        "n_skipped_no_gold": skipped,
        "ndcg@10": round(statistics.mean(ndcgs), 4),
        "mrr":     round(statistics.mean(mrrs), 4),
        "r@10":    round(statistics.mean(r10s), 4),
        "hit_rate": round(statistics.mean(hits), 4),
        "p50_latency_ms": round(p50, 1),
        "p95_latency_ms": round(p95, 1),
    }


def compute_per_subset(results: list[dict]) -> dict[str, dict]:
    """Break out nDCG@10 by category subset."""
    by_cat: dict[str, list[dict]] = {}
    for r in results:
        cat = r.get("category") or "unknown"
        by_cat.setdefault(cat, []).append(r)
    out: dict[str, dict] = {}
    for cat, rows in by_cat.items():
        m = compute(rows)
        out[cat] = {"n": len(rows), **m}
    return out


# ---------------------------------------------------------------------------
# Adapter runner
# ---------------------------------------------------------------------------


def run_adapter(
    adapter_name: str,
    queries: list[dict],
    *,
    cap: int | None,
    k: int = 10,
    env_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Generic adapter runner. Returns per-query results + aggregate metrics."""
    cap_label = str(cap) if cap is not None else "full"

    # Set env vars
    env_overrides = env_overrides or {}
    saved = {}
    for k_env, v_env in env_overrides.items():
        saved[k_env] = os.environ.get(k_env)
        os.environ[k_env] = v_env
    if cap is not None:
        os.environ["NOX_MEM_INGEST_LIMIT"] = str(cap)
    else:
        os.environ.pop("NOX_MEM_INGEST_LIMIT", None)

    try:
        mod_path = f"adapters.{adapter_name}"
        if mod_path in sys.modules:
            mod = importlib.reload(sys.modules[mod_path])
        else:
            mod = importlib.import_module(mod_path)

        # Reset state
        for attr in (
            "_eval_con", "_eval_db_path", "_hybrid_con", "_con", "_db_path",
        ):
            if hasattr(mod, attr):
                setattr(mod, attr, None)

        print(f"[a2-bench] {adapter_name} cap={cap_label}: setup()...", file=sys.stderr)
        t_setup = time.perf_counter()
        mod.setup()
        setup_s = time.perf_counter() - t_setup
        print(
            f"[a2-bench] {adapter_name} setup done in {setup_s:.1f}s",
            file=sys.stderr,
        )

        per_q: list[dict] = []
        for q in queries:
            t0 = time.perf_counter()
            try:
                ranked = mod.search(q["query"], k=k)
                latency_ms = (time.perf_counter() - t0) * 1000
                per_q.append({
                    **q,
                    "results": ranked,
                    "latency_ms": round(latency_ms, 2),
                    "error": None,
                })
            except Exception as exc:  # noqa: BLE001
                latency_ms = (time.perf_counter() - t0) * 1000
                per_q.append({
                    **q,
                    "results": [],
                    "latency_ms": round(latency_ms, 2),
                    "error": f"{type(exc).__name__}: {exc}",
                })

        try:
            mod.teardown()
        except Exception:  # noqa: BLE001
            pass

        metrics = compute(per_q)
        subsets = compute_per_subset(per_q)
        return {
            "adapter": adapter_name,
            "cap": cap_label,
            "cap_int": cap,
            "setup_s": round(setup_s, 1),
            "metrics": metrics,
            "subsets": subsets,
            "queries": per_q,
        }
    finally:
        # Restore env
        for k_env, v_env in saved.items():
            if v_env is None:
                os.environ.pop(k_env, None)
            else:
                os.environ[k_env] = v_env


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------


def verdict_for(a2_ndcg: float) -> tuple[str, str]:
    """Return (label, narrative)."""
    if a2_ndcg is None:
        return "ERROR", "A2 nDCG@10 unavailable (run failed)."
    delta_vs_baseline = a2_ndcg - BASELINE_HYBRID_CAP500_NDCG
    delta_vs_mem0 = a2_ndcg - BASELINE_MEM0_CAP500_NDCG

    if a2_ndcg >= BASELINE_MEM0_CAP500_NDCG:
        return (
            "WIN",
            f"A2 nDCG@10={a2_ndcg:.4f} ≥ mem0@500 ({BASELINE_MEM0_CAP500_NDCG:.4f}). "
            f"Δ vs baseline hybrid@500: +{delta_vs_baseline:.4f}. "
            f"Δ vs mem0@500: {delta_vs_mem0:+.4f}. "
            "Ingest-side concentration WORKED. Merge candidate.",
        )
    if delta_vs_baseline >= 0.01:
        return (
            "NEUTRAL",
            f"A2 nDCG@10={a2_ndcg:.4f}. Δ vs baseline hybrid@500: +{delta_vs_baseline:.4f} "
            f"(closes {delta_vs_baseline/GAP_TARGET*100:.0f}% of mem0 gap). "
            "Some lift but doesn't match mem0. Hold for Toto sign-off on re-ingest cost.",
        )
    if delta_vs_baseline <= -0.01:
        return (
            "NEGATIVE",
            f"A2 nDCG@10={a2_ndcg:.4f}. Δ vs baseline hybrid@500: {delta_vs_baseline:+.4f}. "
            "Summarization HURT retrieval — fact extraction stripped retrieval-relevant tokens. "
            "Do NOT merge. Document for the ship narrative.",
        )
    return (
        "NEUTRAL",
        f"A2 nDCG@10={a2_ndcg:.4f}. Δ vs baseline hybrid@500: {delta_vs_baseline:+.4f}. "
        "Statistical wash. Not worth the re-ingest cost. Do NOT merge.",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(description="Path A2 benchmark")
    p.add_argument("--template", default="A", choices=["A", "B", "C"])
    p.add_argument(
        "--run-baseline-cap500", action="store_true",
        help="Also re-run hybrid baseline cap=500 for fresh comparison "
             "(default uses Sat 2026-05-24 numbers from PR #338).",
    )
    p.add_argument(
        "--also-run-full", action="store_true",
        help="Also benchmark A2 at full corpus (no cap). Costs more compute.",
    )
    args = p.parse_args()

    print(f"[a2-bench] template={args.template}", file=sys.stderr)
    queries = load_all_queries()
    print(
        f"[a2-bench] {len(queries)} queries "
        f"({sum(1 for q in queries if q['dataset']=='locomo')} locomo + "
        f"{sum(1 for q in queries if q['dataset']=='longmemeval')} longmemeval)",
        file=sys.stderr,
    )

    summarized_path = HERE / "cache" / f"summarized-{args.template}.jsonl"
    if not summarized_path.exists():
        print(
            f"FATAL: summarized JSONL not found at {summarized_path}. "
            f"Run lib.chunk_summarizer summarize first.",
            file=sys.stderr,
        )
        return 2

    a2_db = HERE / "cache" / f"nox-mem-a2-{args.template}.db"
    env_overrides = {
        "NOX_A2_SUMMARIZED_PATH": str(summarized_path),
        "NOX_A2_DB_PATH":         str(a2_db),
    }

    runs: list[dict] = []

    # Capped@500
    cap500 = run_adapter(
        "nox_mem_a2", queries, cap=500, env_overrides=env_overrides,
    )
    runs.append(cap500)
    print(
        f"[a2-bench] A2@500: nDCG@10={cap500['metrics']['ndcg@10']} | "
        f"MRR={cap500['metrics']['mrr']} | R@10={cap500['metrics']['r@10']} | "
        f"hit_rate={cap500['metrics']['hit_rate']} | p50={cap500['metrics']['p50_latency_ms']}ms",
        file=sys.stderr,
    )

    if args.also_run_full:
        full = run_adapter(
            "nox_mem_a2", queries, cap=None, env_overrides=env_overrides,
        )
        runs.append(full)
        print(
            f"[a2-bench] A2 full: nDCG@10={full['metrics']['ndcg@10']} | "
            f"MRR={full['metrics']['mrr']}",
            file=sys.stderr,
        )

    optional_baseline: dict | None = None
    if args.run_baseline_cap500:
        # Run hybrid baseline at cap=500 too (fresh apples-to-apples)
        optional_baseline = run_adapter(
            "nox_mem", queries, cap=500,
            env_overrides={"NOX_EVAL_MODE": "hybrid"},
        )

    # ----------------- Verdict + report -----------------
    a2_ndcg_500 = cap500["metrics"]["ndcg@10"] or 0.0
    label, narrative = verdict_for(a2_ndcg_500)

    out_json = {
        "meta": {
            "template": args.template,
            "summarized_path": str(summarized_path),
            "a2_db_path": str(a2_db),
            "baselines": {
                "hybrid_full_ndcg@10":    BASELINE_HYBRID_FULL_NDCG,
                "hybrid_cap500_ndcg@10":  BASELINE_HYBRID_CAP500_NDCG,
                "mem0_cap500_ndcg@10":    BASELINE_MEM0_CAP500_NDCG,
                "gap_target":             GAP_TARGET,
            },
            "verdict": label,
            "narrative": narrative,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "runs": runs,
        "fresh_baseline_cap500": optional_baseline,
    }

    out_path = STAGED / "results.json"
    out_path.write_text(json.dumps(out_json, indent=2, ensure_ascii=False))
    print(f"[a2-bench] results.json → {out_path}", file=sys.stderr)

    # Render results.md
    md = render_md(out_json)
    md_path = STAGED / "RESULTS.md"
    md_path.write_text(md)
    print(f"[a2-bench] RESULTS.md → {md_path}", file=sys.stderr)

    print("\n" + "=" * 80)
    print(f"VERDICT: {label}")
    print("=" * 80)
    print(narrative)
    print("=" * 80)

    return 0


def render_md(out: dict) -> str:
    meta = out["meta"]
    runs = out["runs"]
    baseline = out.get("fresh_baseline_cap500")

    lines: list[str] = []
    lines.append("# Path A2 — Gemini Flash chunk summarizer (capped@500)")
    lines.append("")
    lines.append(f"**Verdict:** `{meta['verdict']}`")
    lines.append("")
    lines.append(f"**Template:** `{meta['template']}` (1=facts, 2=tldr, 3=hybrid)")
    lines.append("")
    lines.append(f"**Generated:** {meta['generated_at']}")
    lines.append("")
    lines.append("## Narrative")
    lines.append("")
    lines.append(meta["narrative"])
    lines.append("")

    # Main table
    lines.append("## Metrics table")
    lines.append("")
    lines.append("| Run | n_chunks | nDCG@10 | MRR | R@10 | hit_rate | p50 (ms) | p95 (ms) |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    bl = meta["baselines"]
    lines.append(f"| Baseline hybrid full (PR #338) | 6,830 | {bl['hybrid_full_ndcg@10']:.4f} | — | — | — | — | — |")
    lines.append(f"| Baseline hybrid cap=500       | 500   | {bl['hybrid_cap500_ndcg@10']:.4f} | — | — | — | — | — |")
    lines.append(f"| **mem0 cap=500** (target)     | 500   | **{bl['mem0_cap500_ndcg@10']:.4f}** | — | — | — | — | — |")
    if baseline:
        bm = baseline["metrics"]
        lines.append(f"| Fresh hybrid cap=500 (this run) | 500 | {bm['ndcg@10']} | {bm['mrr']} | {bm['r@10']} | {bm['hit_rate']} | {bm['p50_latency_ms']} | {bm['p95_latency_ms']} |")
    for r in runs:
        m = r["metrics"]
        n = "500" if r["cap_int"] == 500 else ("full" if r["cap_int"] is None else str(r["cap_int"]))
        lines.append(
            f"| **A2 (template {meta['template']}) cap={n}** | {n} | "
            f"**{m['ndcg@10']}** | {m['mrr']} | {m['r@10']} | "
            f"{m['hit_rate']} | {m['p50_latency_ms']} | {m['p95_latency_ms']} |"
        )

    # Gap closure
    lines.append("")
    lines.append("## Gap closure analysis")
    lines.append("")
    a2_run = next((r for r in runs if r["cap_int"] == 500), None)
    if a2_run and a2_run["metrics"]["ndcg@10"] is not None:
        a2 = a2_run["metrics"]["ndcg@10"]
        delta_vs_b = a2 - bl["hybrid_cap500_ndcg@10"]
        delta_vs_m = a2 - bl["mem0_cap500_ndcg@10"]
        pct_gap = delta_vs_b / meta["baselines"]["gap_target"] * 100 if meta["baselines"]["gap_target"] else 0.0
        lines.append(f"- Gap to close (mem0@500 − hybrid@500): **+{meta['baselines']['gap_target']:.4f}**")
        lines.append(f"- A2@500 lift over hybrid@500:          **{delta_vs_b:+.4f}**")
        lines.append(f"- Gap closure:                          **{pct_gap:+.0f}%**")
        lines.append(f"- A2@500 vs mem0@500:                   **{delta_vs_m:+.4f}**")
    lines.append("")

    # Subset breakdown
    lines.append("## Subset breakdown (capped@500)")
    lines.append("")
    if a2_run and a2_run.get("subsets"):
        lines.append("| Subset | n | nDCG@10 | MRR | R@10 | hit_rate |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for cat, m in sorted(a2_run["subsets"].items()):
            lines.append(
                f"| {cat} | {m['n']} | {m.get('ndcg@10','—')} | "
                f"{m.get('mrr','—')} | {m.get('r@10','—')} | "
                f"{m.get('hit_rate','—')} |"
            )
    lines.append("")

    # Cost
    lines.append("## Cost")
    lines.append("")
    summ_cost_path = Path(meta["summarized_path"]).with_name(
        Path(meta["summarized_path"]).stem + "-cost.jsonl"
    )
    total_cost = 0.0
    total_in = 0
    total_out = 0
    if summ_cost_path.exists():
        for line in summ_cost_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                c = json.loads(line)
            except json.JSONDecodeError:
                continue
            total_cost += float(c.get("cost_usd") or 0.0)
            total_in += int(c.get("in_tokens") or 0)
            total_out += int(c.get("out_tokens") or 0)
    lines.append(f"- Summarizer total cost: **${total_cost:.4f}**")
    lines.append(f"- Input tokens:          {total_in:,}")
    lines.append(f"- Output tokens:         {total_out:,}")
    lines.append("- Model:                 `gemini-2.5-flash-lite`")
    lines.append("- Hard cap was $5; well under.")
    lines.append("")

    # References
    lines.append("## References")
    lines.append("")
    lines.append("- Baseline #338 hybrid: `output/nox_mem_hybrid_full.json` (Sat 2026-05-24)")
    lines.append("- mem0@500 ref:         PR #306 Sat closure (nDCG@10 = 0.1315)")
    lines.append("- Prior failed paths:")
    lines.append("  - PR #337 query rewrite: -11.8% nDCG@10")
    lines.append("  - PR #339 E+F+H combo:    +2.4% (gap persists)")
    lines.append("- Memories:")
    lines.append("  - [[concentration-vs-coverage]]")
    lines.append("  - [[shared-loader-canonical-pattern]]")
    lines.append("  - [[adapter-response-shape-validation]]")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
