#!/usr/bin/env python3
"""
Aggregate Phase KGMQ 5-batch results + generate RESULTS-WAVE-B-KG-MQ.md.

Wave B composability bench: validates additive hypothesis (KG +2.81pp + MQ
+3.61pp = ~+6.42pp F_MH if mechanically additive). Reads analysis.txt from
each phaseKGMQ-<batch>-<ts>/ run dir, parses Combined (Major_Minor) +
Overall, then evaluates 4-gate composability decision.

Gate criteria (per task spec):
  - F_MH lift ≥ +5.5pp (additivity floor: +2.81 + +3.61 − 1pp interaction)
  - F_MH ≥ Phase MQ alone (combo MUST exceed strongest single knob)
  - Overall regression ≤ Phase MQ alone (-1.12pp) + 0.5pp tolerance
  - MA composite ≥ Phase MQ alone − 0.5pp tolerance

Usage:
    python3 aggregate-phaseKGMQ.py \\
        --runs-dir /root/.openclaw/evermembench-runs \\
        --pattern 'phaseKGMQ-0*' \\
        --output RESULTS-WAVE-B-KG-MQ.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

try:
    from eval.lib.aggregate_5batch import aggregate_5batch
    from eval.lib.report_template import generate_report
except ImportError as exc:
    print(f"FATAL: eval/lib not importable: {exc}")
    print(f"sys.path = {sys.path[:5]}")
    sys.exit(2)


# ===== Locked baselines (Wave A + memory) =====
# Phase H v2 5-batch (PR #377)
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

# Phase KG sparse 5-batch (PR #379)
PHASE_KG_5BATCH = {
    "overall": 51.80,
    "F_MH": 6.02,
    "MA_C": 84.60,
    "MA_P": 66.60,
    "MA_U": 70.15,
    "MA_mean": 73.78,
}

# Phase MQ 5-batch (PR #385)
PHASE_MQ_5BATCH = {
    "overall": 50.56,
    "F_MH": 6.82,
    "MA_C": 84.60,  # approx, MA unchanged by MQ at retrieval level
    "MA_P": 65.40,
    "MA_U": 70.03,
    "MA_mean": 71.97,
}

# Additive prediction (KG +2.81 + MQ +3.61 - 0pp interaction = +6.42pp F_MH)
ADDITIVE_PREDICTION = {
    "overall": PHASE_H_V2_5BATCH["overall"] + (PHASE_KG_5BATCH["overall"] - PHASE_H_V2_5BATCH["overall"]) + (PHASE_MQ_5BATCH["overall"] - PHASE_H_V2_5BATCH["overall"]),  # ~50.68
    "F_MH": PHASE_H_V2_5BATCH["F_MH"] + (PHASE_KG_5BATCH["F_MH"] - PHASE_H_V2_5BATCH["F_MH"]) + (PHASE_MQ_5BATCH["F_MH"] - PHASE_H_V2_5BATCH["F_MH"]),  # 3.21 + 2.81 + 3.61 = 9.63
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


# ===== analysis.txt parsing =====
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
                out[m.group(1)] = float(m.group(4))
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


# ===== search_results.json metadata parsing =====
def parse_meta_coverage(search_results_path: Path) -> Dict[str, Any]:
    """Walk search_results.json and compute MQ + KG coverage stats."""
    out: Dict[str, Any] = {
        "queries_total": 0,
        "queries_mq_applied": 0,
        "queries_kg_applied": 0,
        "queries_composability_active": 0,
        "queries_mq_fallback": 0,
        "queries_mq_error": 0,
        "sub_query_counts": [],
        "decompose_ms": [],
        "retrieve_ms": [],
        "kg_ms": [],
        "kg_entities_in_query": [],
        "kg_chunks_boosted": [],
        "sample_decompositions": [],
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
            sq = meta.get("mq_sub_queries") or []
            if sq and len(out["sample_decompositions"]) < 6:
                out["sample_decompositions"].append({
                    "query": item.get("query", "?"),
                    "sub_queries": sq,
                })
        elif meta.get("mq_status") == "fallback_single":
            out["queries_mq_fallback"] += 1
        if meta.get("mq_error"):
            out["queries_mq_error"] += 1
        if meta.get("kg_applied"):
            out["queries_kg_applied"] += 1
            if meta.get("kg_ms") is not None:
                try:
                    out["kg_ms"].append(float(meta["kg_ms"]))
                except (TypeError, ValueError):
                    pass
            kg_meta = meta.get("kg_meta") or {}
            if kg_meta.get("entities_in_query") is not None:
                try:
                    out["kg_entities_in_query"].append(int(kg_meta["entities_in_query"]))
                except (TypeError, ValueError):
                    pass
            if kg_meta.get("chunks_boosted") is not None:
                try:
                    out["kg_chunks_boosted"].append(int(kg_meta["chunks_boosted"]))
                except (TypeError, ValueError):
                    pass
        if meta.get("composability_kg_mq_active"):
            out["queries_composability_active"] += 1
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
    ap.add_argument("--pattern", default="phaseKGMQ-0*")
    ap.add_argument("--output", default="RESULTS-WAVE-B-KG-MQ.md")
    ap.add_argument("--phase-label", default="Phase KGMQ (Wave B composability)")
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
        m = re.match(r"phaseKGMQ-(\d+)-", d.name)
        if not m:
            continue
        batch = m.group(1)
        # Skip smoke runs
        if batch.startswith("smoke"):
            continue
        analysis = d / "analysis.txt"
        if not analysis.exists():
            print(f"  WARN: {d}/analysis.txt missing")
            continue
        metrics = parse_analysis(analysis)
        if not metrics or "overall" not in metrics:
            print(f"  WARN: {d}/analysis.txt did not parse cleanly")
            continue
        # Only keep latest run per batch
        if batch in per_batch_metrics:
            # take whichever has higher timestamp (sorted glob is alphabetical, latest wins)
            pass
        per_batch_metrics[batch] = metrics
        search_results = d / f"search-results-batch-{batch}.json"
        if search_results.exists():
            per_batch_coverage[batch] = parse_meta_coverage(search_results)

    if not per_batch_metrics:
        print("FATAL: no batches parsed successfully")
        return 2

    print("\nPer-batch metrics:")
    for b, m in sorted(per_batch_metrics.items()):
        print(f"  {b}: overall={m.get('overall')} F_MH={m.get('F_MH')}")

    results = {"batch_id": "phaseKGMQ-5batch", "per_batch": per_batch_metrics}
    baselines = {
        "Phase H v2 (5-batch)": PHASE_H_V2_5BATCH,
        "MemOS GPT-4.1-mini": MEMOS_GPT41MINI,
    }

    try:
        md = generate_report(results, baselines, phase_label=args.phase_label)
    except (ValueError, Exception) as exc:
        print(f"WARN: generate_report failed: {exc}")
        agg = aggregate_5batch(per_batch_metrics)
        md = f"# Phase KGMQ 5-batch — RAW (report_template failed)\n\n{json.dumps(agg, indent=2, default=str)}\n"

    # Coverage section
    md += "\n\n## Composability Coverage (KG + MQ firing rate)\n\n"
    md += (
        "| batch | queries | mq_applied | kg_applied | both | "
        "avg sub-Q N | decompose p50 | kg p50 |\n"
    )
    md += "|---|---:|---:|---:|---:|---:|---:|---:|\n"
    tot_q = tot_mq = tot_kg = tot_both = 0
    all_dec_ms: List[float] = []
    all_kg_ms: List[float] = []
    all_sub_n: List[int] = []
    all_kg_ent: List[int] = []
    all_kg_boost: List[int] = []
    sample_decompositions_all: List[Dict[str, Any]] = []
    for b in sorted(per_batch_coverage.keys()):
        cov = per_batch_coverage[b]
        tot_q += int(cov["queries_total"])
        tot_mq += int(cov["queries_mq_applied"])
        tot_kg += int(cov["queries_kg_applied"])
        tot_both += int(cov["queries_composability_active"])
        avg_sub_n = (
            sum(cov["sub_query_counts"]) / len(cov["sub_query_counts"])
            if cov["sub_query_counts"] else 0.0
        )
        dec_p50 = _percentile(cov["decompose_ms"], 50)
        kg_p50 = _percentile(cov["kg_ms"], 50)
        all_dec_ms.extend(cov["decompose_ms"])
        all_kg_ms.extend(cov["kg_ms"])
        all_sub_n.extend(cov["sub_query_counts"])
        all_kg_ent.extend(cov["kg_entities_in_query"])
        all_kg_boost.extend(cov["kg_chunks_boosted"])
        sample_decompositions_all.extend(cov.get("sample_decompositions", []))
        md += (
            f"| {b} | {int(cov['queries_total'])} | "
            f"{int(cov['queries_mq_applied'])} | "
            f"{int(cov['queries_kg_applied'])} | "
            f"{int(cov['queries_composability_active'])} | "
            f"{avg_sub_n:.2f} | "
            f"{dec_p50:.0f}ms | {kg_p50:.0f}ms |\n"
        )

    if tot_q > 0:
        total_avg_sub_n = sum(all_sub_n) / len(all_sub_n) if all_sub_n else 0.0
        md += (
            f"| **TOTAL** | **{tot_q}** | "
            f"**{tot_mq}** ({_pct(tot_mq, tot_q):.1f}%) | "
            f"**{tot_kg}** ({_pct(tot_kg, tot_q):.1f}%) | "
            f"**{tot_both}** ({_pct(tot_both, tot_q):.1f}%) | "
            f"**{total_avg_sub_n:.2f}** | "
            f"**{_percentile(all_dec_ms, 50):.0f}ms** | "
            f"**{_percentile(all_kg_ms, 50):.0f}ms** |\n"
        )

    # Sample decompositions
    if sample_decompositions_all:
        md += "\n\n## Sample Decompositions (for paper / sanity)\n\n"
        for i, sample in enumerate(sample_decompositions_all[:6]):
            md += f"### Sample {i+1}\n\n"
            md += f"**Original query:** {sample.get('query', '?')}\n\n"
            md += "**Sub-queries:**\n\n"
            for sq in sample.get("sub_queries", []):
                md += f"- {sq}\n"
            md += "\n"

    # ===== 4-Gate Composability Decision =====
    md += "\n\n## Wave B 4-Gate Composability Decision\n\n"
    agg = aggregate_5batch(per_batch_metrics)
    overall_mean = agg.get("overall", {}).get("mean", 0.0)
    f_mh_mean = agg.get("F_MH", {}).get("mean", 0.0)
    ma_c_mean = agg.get("MA_C", {}).get("mean", 0.0)
    ma_p_mean = agg.get("MA_P", {}).get("mean", 0.0)
    ma_u_mean = agg.get("MA_U", {}).get("mean", 0.0)
    ma_avg = (ma_c_mean + ma_p_mean + ma_u_mean) / 3.0

    f_mh_delta_h2 = f_mh_mean - PHASE_H_V2_5BATCH["F_MH"]
    f_mh_delta_mq = f_mh_mean - PHASE_MQ_5BATCH["F_MH"]
    f_mh_delta_kg = f_mh_mean - PHASE_KG_5BATCH["F_MH"]
    overall_delta_h2 = overall_mean - PHASE_H_V2_5BATCH["overall"]
    overall_delta_mq = overall_mean - PHASE_MQ_5BATCH["overall"]
    ma_delta_mq = ma_avg - PHASE_MQ_5BATCH["MA_mean"]

    # Additivity verification
    additive_pred = ADDITIVE_PREDICTION["F_MH"]  # 9.63
    additivity_residual = f_mh_mean - additive_pred  # positive = positive surprise, negative = diminishing

    # 4 gates
    gates = [
        ("F_MH lift ≥ +5.5pp vs Phase H v2 (additivity floor)",
         f_mh_delta_h2 >= 5.5,
         f"observed {f_mh_delta_h2:+.2f}pp ({f_mh_mean:.2f}% vs H v2 {PHASE_H_V2_5BATCH['F_MH']:.2f}%)"),
        ("F_MH ≥ Phase MQ alone (combo > strongest single knob)",
         f_mh_mean >= PHASE_MQ_5BATCH["F_MH"],
         f"observed {f_mh_delta_mq:+.2f}pp ({f_mh_mean:.2f}% vs MQ {PHASE_MQ_5BATCH['F_MH']:.2f}%)"),
        ("Overall regression ≤ MQ alone (-1.12pp) + 0.5pp tolerance",
         overall_delta_mq >= -0.5,
         f"observed {overall_delta_mq:+.2f}pp ({overall_mean:.2f}% vs MQ {PHASE_MQ_5BATCH['overall']:.2f}%)"),
        ("MA composite ≥ Phase MQ alone − 0.5pp tolerance",
         ma_delta_mq >= -0.5,
         f"observed {ma_delta_mq:+.2f}pp ({ma_avg:.2f}% vs MQ {PHASE_MQ_5BATCH['MA_mean']:.2f}%)"),
    ]

    md += "| Gate | Pass | Observed |\n|---|---|---|\n"
    for label, passed, observed in gates:
        md += f"| {label} | {'PASS' if passed else 'FAIL'} | {observed} |\n"

    n_pass = sum(1 for _, p, _ in gates if p)
    md += f"\n**Gate summary:** {n_pass} / {len(gates)} conditions met.\n"

    # Additivity verification table
    md += "\n## Additivity Verification\n\n"
    md += (
        "| Quantity | Value |\n|---|---:|\n"
        f"| Phase H v2 baseline F_MH | {PHASE_H_V2_5BATCH['F_MH']:.2f}% |\n"
        f"| Phase KG sparse F_MH | {PHASE_KG_5BATCH['F_MH']:.2f}% (+{PHASE_KG_5BATCH['F_MH'] - PHASE_H_V2_5BATCH['F_MH']:.2f}pp) |\n"
        f"| Phase MQ alone F_MH | {PHASE_MQ_5BATCH['F_MH']:.2f}% (+{PHASE_MQ_5BATCH['F_MH'] - PHASE_H_V2_5BATCH['F_MH']:.2f}pp) |\n"
        f"| **Additive prediction** (KG + MQ stack) | **{additive_pred:.2f}%** |\n"
        f"| **Phase KGMQ actual** | **{f_mh_mean:.2f}%** |\n"
        f"| Additivity residual (actual − predicted) | **{additivity_residual:+.2f}pp** |\n"
    )

    if additivity_residual >= 0.5:
        md += "\n**Interpretation: POSITIVE SURPRISE** — combo exceeds additive prediction. "
        md += "Mechanisms may be SYNERGISTIC. Major narrative shift for paper §5.\n"
    elif additivity_residual >= -1.0:
        md += "\n**Interpretation: ADDITIVE HOLDS** — combo within noise of independent stacking. "
        md += "Validates [[mq-kg-mechanically-additive-prediction-6-42pp]]. Major paper §5 update.\n"
    elif additivity_residual >= -3.0:
        md += "\n**Interpretation: PARTIAL ADDITIVITY** — combo shows diminishing returns. "
        md += "Interaction penalty larger than 1pp tolerance. Document trade-off.\n"
    else:
        md += "\n**Interpretation: ANTI-ADDITIVE** — combo underperforms either single knob. "
        md += "Mechanisms compete. Rethink composition strategy.\n"

    # Strategic interpretation
    md += "\n## Strategic Interpretation\n\n"
    memos_gap_h2 = MEMOS_GPT41MINI["F_MH"] - PHASE_H_V2_5BATCH["F_MH"]  # 15.67
    memos_gap_closed = f_mh_delta_h2 / memos_gap_h2 * 100.0 if memos_gap_h2 else 0.0
    md += (
        f"- **MemOS F_MH gap closure:** {memos_gap_closed:.1f}% of the 15.67pp baseline gap "
        f"(KG alone closed 17%, MQ alone closed 23%, additive prediction was 41%).\n"
        f"- **Cost:** ~$0.0001/query (decomposer) + $0 (KG SQL+regex).\n"
        f"- **Latency overhead:** ~{_percentile(all_dec_ms, 50):.0f}ms decompose + "
        f"~{_percentile(all_kg_ms, 50):.0f}ms KG = "
        f"~{_percentile(all_dec_ms, 50) + _percentile(all_kg_ms, 50):.0f}ms total retrieval-side.\n"
        f"- **Composability firing rate:** {_pct(tot_both, tot_q):.1f}% of queries had BOTH "
        f"mechanisms active (mq_applied AND kg_applied).\n"
    )

    # Comparative table
    md += "\n## Comparative Table (vs siblings + MemOS)\n\n"
    md += "| System | Overall | F_MH | Δ F_MH vs H v2 | MA mean | Cost/query |\n"
    md += "|---|---:|---:|---:|---:|---:|\n"
    md += (
        f"| Phase H v2 (baseline) | {PHASE_H_V2_5BATCH['overall']:.2f}% | "
        f"{PHASE_H_V2_5BATCH['F_MH']:.2f}% | — | "
        f"{(PHASE_H_V2_5BATCH['MA_C']+PHASE_H_V2_5BATCH['MA_P']+PHASE_H_V2_5BATCH['MA_U'])/3:.2f}% | $0 |\n"
    )
    md += (
        f"| Phase KG sparse (PR #379) | {PHASE_KG_5BATCH['overall']:.2f}% | "
        f"{PHASE_KG_5BATCH['F_MH']:.2f}% | "
        f"{PHASE_KG_5BATCH['F_MH'] - PHASE_H_V2_5BATCH['F_MH']:+.2f}pp | "
        f"{PHASE_KG_5BATCH['MA_mean']:.2f}% | $0 |\n"
    )
    md += (
        f"| Phase MQ (PR #385) | {PHASE_MQ_5BATCH['overall']:.2f}% | "
        f"{PHASE_MQ_5BATCH['F_MH']:.2f}% | "
        f"{PHASE_MQ_5BATCH['F_MH'] - PHASE_H_V2_5BATCH['F_MH']:+.2f}pp | "
        f"{PHASE_MQ_5BATCH['MA_mean']:.2f}% | ~$0.0001/q |\n"
    )
    md += (
        f"| **Phase KGMQ (this run)** | **{overall_mean:.2f}%** | "
        f"**{f_mh_mean:.2f}%** | "
        f"**{f_mh_delta_h2:+.2f}pp** | "
        f"**{ma_avg:.2f}%** | ~$0.0001/q |\n"
    )
    md += (
        f"| Additive prediction | ~{ADDITIVE_PREDICTION['overall']:.2f}% | "
        f"~{ADDITIVE_PREDICTION['F_MH']:.2f}% | "
        f"+{ADDITIVE_PREDICTION['F_MH'] - PHASE_H_V2_5BATCH['F_MH']:.2f}pp | — | — |\n"
    )
    md += (
        f"| MemOS GPT-4.1-mini (target) | {MEMOS_GPT41MINI['overall']:.2f}% | "
        f"{MEMOS_GPT41MINI['F_MH']:.2f}% | "
        f"{MEMOS_GPT41MINI['F_MH'] - PHASE_H_V2_5BATCH['F_MH']:+.2f}pp | "
        f"{(MEMOS_GPT41MINI['MA_C']+MEMOS_GPT41MINI['MA_P']+MEMOS_GPT41MINI['MA_U'])/3:.2f}% | unknown |\n"
    )

    if n_pass == len(gates):
        md += "\n**Decision:** SHIP composability as default-when-both-flags-set. Propose default-OFF→default-ON migration path for Phase KGMQ.\n"
    elif n_pass >= 2:
        md += "\n**Decision:** Partial composability — ship opt-in via `NOX_ADAPTER_MODE=phaseKGMQ` (both flags ON simultaneously). Document interaction trade-off.\n"
    else:
        md += "\n**Decision:** REJECT composability default — mechanisms compete more than they compose. Document failure mode in paper §5.\n"

    # Implications for paper §5
    md += "\n## Implications for Paper §5\n\n"
    if additivity_residual >= -1.0 and n_pass >= 3:
        md += (
            "- **Major narrative shift:** cheap retrieval-side mechanisms COMPOUND. "
            "Cross-encoder rerank (+1.61pp) is not the only path; KG + MQ "
            "additively stack for {:.2f}pp F_MH improvement, closing {:.1f}% of "
            "the MemOS gap WITHOUT any new model.\n".format(f_mh_delta_h2, memos_gap_closed)
        )
        md += (
            "- **Strategic positioning:** nox-mem multi-knob composition beats single-knob SOTA on "
            "cost-efficiency, with $0.0001/query and <2× latency.\n"
        )
    else:
        md += (
            "- **Composability nuance:** additive prediction overshot by "
            "{:.2f}pp. Paper §5 should document interaction effects + "
            "recommend single-knob deployment for multi-hop workloads.\n".format(additivity_residual)
        )

    out_path = Path(args.output)
    out_path.write_text(md, encoding="utf-8")
    print(f"\nWrote {out_path} ({len(md)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
