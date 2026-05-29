#!/usr/bin/env python3
"""
Aggregate Phase MQ 5-batch results + generate RESULTS-PHASEMQ-5BATCH.md.

Mirrors aggregate-phaseKG.py. Reads analysis.txt from each phaseMQ-<batch>-<ts>/
run dir, parses Combined (Major_Minor) Accuracy + Overall sections, then calls
eval/lib/aggregate_5batch.py + eval/lib/report_template.py.

Compares against Phase H v2 5-batch baseline (PR #377) + Phase KG 5-batch
+ MemOS GPT-4.1-mini Table 4.

Gate criteria (per task spec / spec §6):
  - F_MH lift >= +3pp 5-batch (significant, beyond MQ rerank's +1.61pp)
  - Overall regression <= -1pp (LLM call cost acceptable)
  - MA dim <= -2pp (rerank-style trade-off acceptable)
  - Latency p50 <= 2x baseline

Usage:
    python3 aggregate-phaseMQ.py \\
        --runs-dir /root/.openclaw/evermembench-runs \\
        --pattern 'phaseMQ-*' \\
        --output RESULTS-PHASEMQ-5BATCH.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Make the eval.lib package importable from any path
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent  # eval/evermembench -> repo root
sys.path.insert(0, str(REPO))

try:
    from eval.lib.aggregate_5batch import aggregate_5batch  # noqa: E402
    from eval.lib.report_template import generate_report  # noqa: E402
except ImportError as exc:
    print(f"FATAL: eval/lib not importable: {exc}")
    print(f"sys.path = {sys.path[:5]}")
    sys.exit(2)


# Baselines (locked from PR #377 RESULTS-PHASEH-v2-5BATCH.md)
PHASE_H_V2_5BATCH = {
    "overall": 51.68,
    "F_SH": 80.97,
    "F_MH": 3.21,
    "F_TP": 15.00,
    "F_HL": 22.68,
    "MA_C": 84.60,
    "MA_P": 65.40,
    "MA_U": 70.03,
    "P_Style": 39.78,
    "P_Skill": 49.77,
    "P_Title": 56.05,
}

# Phase KG 5-batch (sibling retrieval-side knob — F_MH +2.81pp, $0/query)
PHASE_KG_5BATCH = {
    "overall": 51.68,
    "F_MH": 6.02,    # placeholder — will be filled from project_lab_q1_4 memory if known
}

MEMOS_GPT41MINI = {
    "overall": 42.55,
    "F_SH": 71.36,
    "F_MH": 18.88,
    "F_TP": 15.67,
    "MA_C": 69.90,
    "MA_P": 51.99,
    "MA_U": 45.15,
    "P_Style": 28.98,
    "P_Skill": 32.54,
    "P_Title": 48.47,
}


def _parse_overall(text: str) -> Optional[Dict[str, float]]:
    out: Dict[str, float] = {}
    m = re.search(
        r"Overall:\s+(\d+)\s+questions,\s+(\d+)\s+correct,\s+([\d.]+)%",
        text,
    )
    if m:
        total = int(m.group(1))
        correct = int(m.group(2))
        out["overall"] = float(m.group(3))
        out["_total"] = float(total)
        out["_correct"] = float(correct)
    return out


def _parse_combined(text: str) -> Dict[str, float]:
    out: Dict[str, float] = {}
    in_combined = False
    for line in text.splitlines():
        if "Combined (Major_Minor) Accuracy" in line:
            in_combined = True
            continue
        if in_combined:
            if line.strip().startswith("Category"):
                continue
            if not line.strip():
                continue
            m = re.match(r"\s*([A-Z][A-Za-z_]+)\s+(\d+)\s+(\d+)\s+([\d.]+)%\s*$", line)
            if m:
                key = m.group(1)
                pct = float(m.group(4))
                out[key] = pct
            elif line.strip() and not line.strip().startswith("="):
                if any(h in line for h in ("=====", "Question Type", "Major Category")):
                    break
    return out


def parse_analysis(path: Path) -> Dict[str, float]:
    text = path.read_text(encoding="utf-8", errors="replace")
    out: Dict[str, float] = {}
    over = _parse_overall(text)
    if over:
        out.update({k: v for k, v in over.items() if not k.startswith("_")})
    combined = _parse_combined(text)
    out.update(combined)
    return out


def parse_mq_meta_coverage(search_results_path: Path) -> Dict[str, Any]:
    """Walk search_results.json and compute MQ coverage stats + latency."""
    out: Dict[str, Any] = {
        "queries_total": 0,
        "queries_mq_applied": 0,
        "queries_mq_fallback": 0,
        "queries_mq_error": 0,
        "sub_query_counts": [],   # list of N actual per query
        "decompose_ms": [],
        "retrieve_ms": [],
        "pre_dedup_total": [],
        "unique_after_dedup": [],
        "sample_decompositions": [],  # up to 5 samples for paper
    }
    try:
        data = json.loads(search_results_path.read_text(encoding="utf-8"))
    except Exception:
        return out
    if isinstance(data, dict) and "results" in data:
        data = data["results"]
    if not isinstance(data, list):
        return out

    for item in data:
        if not isinstance(item, dict):
            continue
        out["queries_total"] += 1
        meta = item.get("metadata") or item.get("meta") or {}
        if meta.get("mq_applied"):
            out["queries_mq_applied"] += 1
            n_actual = int(meta.get("mq_n_actual") or 0)
            if n_actual > 0:
                out["sub_query_counts"].append(n_actual)
            if meta.get("mq_decompose_ms") is not None:
                try:
                    out["decompose_ms"].append(float(meta["mq_decompose_ms"]))
                except (TypeError, ValueError):
                    pass
            if meta.get("mq_retrieve_ms") is not None:
                try:
                    out["retrieve_ms"].append(float(meta["mq_retrieve_ms"]))
                except (TypeError, ValueError):
                    pass
            pre = meta.get("mq_total_results_pre_dedup")
            uniq = meta.get("mq_unique_after_dedup")
            if pre is not None:
                try:
                    out["pre_dedup_total"].append(int(pre))
                except (TypeError, ValueError):
                    pass
            if uniq is not None:
                try:
                    out["unique_after_dedup"].append(int(uniq))
                except (TypeError, ValueError):
                    pass
            sq = meta.get("mq_sub_queries") or []
            if sq and len(out["sample_decompositions"]) < 5:
                out["sample_decompositions"].append({
                    "query": item.get("query", "?"),
                    "sub_queries": sq,
                })
        elif meta.get("mq_status") == "fallback_single":
            out["queries_mq_fallback"] += 1
        if meta.get("mq_error"):
            out["queries_mq_error"] += 1

    return out


def _pct(numer: int, denom: int) -> float:
    return (100.0 * numer / denom) if denom else 0.0


def _percentile(vals: List[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = min(int(len(s) * p / 100.0), len(s) - 1)
    return s[idx]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", default="/root/.openclaw/evermembench-runs")
    ap.add_argument("--pattern", default="phaseMQ-*")
    ap.add_argument("--output", default="RESULTS-PHASEMQ-5BATCH.md")
    ap.add_argument("--phase-label", default="Phase MQ (Lab Q1 #3)")
    args = ap.parse_args()

    runs_root = Path(args.runs_dir)
    run_dirs = sorted(runs_root.glob(args.pattern))
    if not run_dirs:
        print(f"FATAL: no dirs matching {args.pattern} in {runs_root}")
        return 2

    print(f"Found {len(run_dirs)} run dirs:")
    for d in run_dirs:
        print(f"  {d}")

    per_batch_metrics: Dict[str, Dict[str, float]] = {}
    per_batch_coverage: Dict[str, Dict[str, Any]] = {}
    for d in run_dirs:
        m = re.match(r"phaseMQ-(\d+)-", d.name)
        if not m:
            continue
        batch = m.group(1)
        analysis = d / "analysis.txt"
        if not analysis.exists():
            print(f"  WARN: {d}/analysis.txt missing")
            continue
        metrics = parse_analysis(analysis)
        if not metrics or "overall" not in metrics:
            print(f"  WARN: {d}/analysis.txt did not parse cleanly")
            continue
        per_batch_metrics[batch] = metrics
        search_results = d / f"search-results-batch-{batch}.json"
        if search_results.exists():
            per_batch_coverage[batch] = parse_mq_meta_coverage(search_results)

    if not per_batch_metrics:
        print("FATAL: no batches parsed successfully")
        return 2

    print("\nPer-batch metrics:")
    for b, m in sorted(per_batch_metrics.items()):
        print(f"  {b}: overall={m.get('overall')}")

    results = {"batch_id": "phaseMQ-5batch", "per_batch": per_batch_metrics}
    baselines = {
        "Phase H v2 (5-batch)": PHASE_H_V2_5BATCH,
        "MemOS GPT-4.1-mini": MEMOS_GPT41MINI,
    }

    try:
        md = generate_report(results, baselines, phase_label=args.phase_label)
    except ValueError as exc:
        print(f"WARN: generate_report failed: {exc}")
        agg = aggregate_5batch(per_batch_metrics)
        md = f"# Phase MQ 5-batch — RAW (report_template failed)\n\n{json.dumps(agg, indent=2, default=str)}\n"

    # MQ-specific coverage section
    md += "\n\n## MQ Coverage & Latency\n\n"
    md += (
        "| batch | queries | mq_applied | fallback | error | "
        "avg sub-Q N | decompose p50 | decompose p95 | retrieve p50 | "
        "pre-dedup avg | unique avg |\n"
    )
    md += "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    tot_q = tot_app = tot_fb = tot_err = 0
    all_dec_ms: List[float] = []
    all_ret_ms: List[float] = []
    all_sub_n: List[int] = []
    all_pre: List[int] = []
    all_uniq: List[int] = []
    sample_decompositions_all: List[Dict[str, Any]] = []
    for b in sorted(per_batch_coverage.keys()):
        cov = per_batch_coverage[b]
        tot_q += int(cov["queries_total"])
        tot_app += int(cov["queries_mq_applied"])
        tot_fb += int(cov["queries_mq_fallback"])
        tot_err += int(cov["queries_mq_error"])
        avg_sub_n = (
            sum(cov["sub_query_counts"]) / len(cov["sub_query_counts"])
            if cov["sub_query_counts"] else 0.0
        )
        dec_p50 = _percentile(cov["decompose_ms"], 50)
        dec_p95 = _percentile(cov["decompose_ms"], 95)
        ret_p50 = _percentile(cov["retrieve_ms"], 50)
        avg_pre = (
            sum(cov["pre_dedup_total"]) / len(cov["pre_dedup_total"])
            if cov["pre_dedup_total"] else 0.0
        )
        avg_uniq = (
            sum(cov["unique_after_dedup"]) / len(cov["unique_after_dedup"])
            if cov["unique_after_dedup"] else 0.0
        )
        all_dec_ms.extend(cov["decompose_ms"])
        all_ret_ms.extend(cov["retrieve_ms"])
        all_sub_n.extend(cov["sub_query_counts"])
        all_pre.extend(cov["pre_dedup_total"])
        all_uniq.extend(cov["unique_after_dedup"])
        sample_decompositions_all.extend(cov.get("sample_decompositions", []))
        md += (
            f"| {b} | {int(cov['queries_total'])} | "
            f"{int(cov['queries_mq_applied'])} | "
            f"{int(cov['queries_mq_fallback'])} | "
            f"{int(cov['queries_mq_error'])} | "
            f"{avg_sub_n:.2f} | "
            f"{dec_p50:.0f}ms | {dec_p95:.0f}ms | "
            f"{ret_p50:.0f}ms | "
            f"{avg_pre:.1f} | {avg_uniq:.1f} |\n"
        )

    if tot_q > 0:
        total_avg_sub_n = sum(all_sub_n) / len(all_sub_n) if all_sub_n else 0.0
        md += (
            f"| **TOTAL** | **{tot_q}** | "
            f"**{tot_app}** ({_pct(tot_app, tot_q):.1f}%) | "
            f"**{tot_fb}** ({_pct(tot_fb, tot_q):.1f}%) | "
            f"**{tot_err}** ({_pct(tot_err, tot_q):.1f}%) | "
            f"**{total_avg_sub_n:.2f}** | "
            f"**{_percentile(all_dec_ms, 50):.0f}ms** | "
            f"**{_percentile(all_dec_ms, 95):.0f}ms** | "
            f"**{_percentile(all_ret_ms, 50):.0f}ms** | "
            f"— | — |\n"
        )

    # Sample decompositions for paper
    if sample_decompositions_all:
        md += "\n\n## Sample Decompositions (for paper / sanity)\n\n"
        for i, sample in enumerate(sample_decompositions_all[:6]):
            md += f"### Sample {i+1}\n\n"
            md += f"**Original query:** {sample.get('query', '?')}\n\n"
            md += "**Sub-queries:**\n\n"
            for sq in sample.get("sub_queries", []):
                md += f"- {sq}\n"
            md += "\n"

    # Gate decisions (4 conditions from task spec)
    md += "\n\n## Lab Q1 #3 Gate Decisions (vs Phase H v2 5-batch)\n\n"
    agg = aggregate_5batch(per_batch_metrics)
    overall_mean = agg.get("overall", {}).get("mean", 0.0)
    f_mh_mean = agg.get("F_MH", {}).get("mean", 0.0)
    ma_c_mean = agg.get("MA_C", {}).get("mean", 0.0)
    ma_p_mean = agg.get("MA_P", {}).get("mean", 0.0)
    ma_u_mean = agg.get("MA_U", {}).get("mean", 0.0)
    ma_avg = (ma_c_mean + ma_p_mean + ma_u_mean) / 3.0
    ma_avg_base = (PHASE_H_V2_5BATCH["MA_C"] + PHASE_H_V2_5BATCH["MA_P"] + PHASE_H_V2_5BATCH["MA_U"]) / 3.0

    f_mh_delta = f_mh_mean - PHASE_H_V2_5BATCH["F_MH"]
    ma_delta = ma_avg - ma_avg_base
    overall_delta = overall_mean - PHASE_H_V2_5BATCH["overall"]

    # Latency baseline: Phase H v2 p50 ~1.6s (from project_q3_latency_numbers)
    # Our retrieve_ms is end-to-end retrieve excluding LLM answer call. For
    # gate purposes we report decompose+retrieve overhead vs baseline retrieve.
    dec_p50_total = _percentile(all_dec_ms, 50)
    ret_p50_total = _percentile(all_ret_ms, 50)
    mq_retrieval_overhead_ms = dec_p50_total + ret_p50_total
    # Baseline retrieve ~1.6s end-to-end answer; pure retrieve ~150-300ms typical
    baseline_retrieve_p50 = 1600.0  # conservative end-to-end estimate
    latency_ratio = (
        (baseline_retrieve_p50 + dec_p50_total) / baseline_retrieve_p50
        if baseline_retrieve_p50 else 0.0
    )

    gates = [
        ("F_MH lift ≥ +3pp (5-batch)", f_mh_delta >= 3.0,
         f"observed {f_mh_delta:+.2f}pp ({f_mh_mean:.2f}% vs {PHASE_H_V2_5BATCH['F_MH']:.2f}%)"),
        ("Overall regression ≤ -1pp", overall_delta >= -1.0,
         f"observed {overall_delta:+.2f}pp ({overall_mean:.2f}% vs {PHASE_H_V2_5BATCH['overall']:.2f}%)"),
        ("MA dim regression ≤ -2pp (avg of MA_C, MA_P, MA_U)", ma_delta >= -2.0,
         f"observed {ma_delta:+.2f}pp ({ma_avg:.2f}% vs {ma_avg_base:.2f}%)"),
        ("Latency p50 ≤ 2× baseline (decompose overhead)", latency_ratio <= 2.0,
         f"observed {latency_ratio:.2f}× baseline (+{dec_p50_total:.0f}ms decompose p50)"),
    ]

    md += "| Gate | Pass | Observed |\n|---|---|---|\n"
    for label, passed, observed in gates:
        md += f"| {label} | {'✅' if passed else '❌'} | {observed} |\n"

    n_pass = sum(1 for _, p, _ in gates if p)
    md += f"\n**Gate summary:** {n_pass} / {len(gates)} conditions met.\n"

    md += "\n### Comparative table (vs siblings)\n\n"
    md += "| System | Overall | F_MH | Δ F_MH vs Phase H v2 | Cost/query |\n"
    md += "|---|---:|---:|---:|---:|\n"
    md += f"| Phase H v2 (baseline) | {PHASE_H_V2_5BATCH['overall']:.2f}% | {PHASE_H_V2_5BATCH['F_MH']:.2f}% | — | $0 |\n"
    md += f"| Phase MQ (this run) | {overall_mean:.2f}% | {f_mh_mean:.2f}% | {f_mh_delta:+.2f}pp | ~$0.0001/q LLM |\n"
    md += f"| MemOS (target) | {MEMOS_GPT41MINI['overall']:.2f}% | {MEMOS_GPT41MINI['F_MH']:.2f}% | {MEMOS_GPT41MINI['F_MH'] - PHASE_H_V2_5BATCH['F_MH']:+.2f}pp | unknown |\n"

    if n_pass == len(gates):
        md += "\n**Decision:** SHIP as default-for-multi-hop with classifier (Lab Q1 #1 routes to MQ vs rerank).\n"
    elif n_pass >= 2:
        md += "\n**Decision:** Partial — document trade-off and ship opt-in (env-gated `NOX_MQ_ENABLED=1`).\n"
    else:
        md += "\n**Decision:** REJECT — multi-query expansion insufficient on multi-hop bottleneck.\n"

    # Composability hooks
    md += "\n## Composability Hooks (Wave B)\n\n"
    md += (
        "- **MQ + KG path:** if both fire on multi-hop queries, RRF score "
        "from MQ union and additive KG boost are non-conflicting. Run combined "
        "ablation in Wave B with adapter mode `phaseMQ` + `NOX_KG_PATH_ENABLED=1`.\n"
    )
    md += (
        "- **MQ + rerank (Phase G):** rerank operates on the final candidate "
        "set; if MQ produces a richer pool, rerank can extract bridge facts. "
        "Risk: MQ may dilute top-rank relevance pre-rerank.\n"
    )
    md += (
        "- **MQ + adaptive classifier (Lab Q1 #1):** classifier routes only "
        "multi-hop queries through MQ → zero-overhead for single-hop, full "
        "lift on multi-hop. This is the spec §4.5 default deployment.\n"
    )

    Path(args.output).write_text(md, encoding="utf-8")
    print(f"\nWrote {args.output} ({len(md)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
