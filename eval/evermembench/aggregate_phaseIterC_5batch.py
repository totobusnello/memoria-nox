#!/usr/bin/env python3
"""Aggregate Phase IterC (Q3 POC) 5-batch results + generate RESULTS-Q3-ITERC-POC.md.

Mirrors aggregate-phaseMQ.py shape. Reads analysis.txt from each phaseIterC-<batch>-<ts>/
run dir, parses Combined + Overall sections, then calls eval/lib/aggregate_5batch.py +
eval/lib/report_template.py.

Compares against:
  - Phase H v2 5-batch baseline (PR #377) — orchestration-stage delta target
  - MemOS GPT-4.1-mini Table 4 — F_MH gap closure tracker

Gate criteria (per task spec §4):
  1. F_MH lift >= +2pp 5-batch (target F_MH >= 5.21%)
  2. Overall regression <= -2pp (target >= 49.68%)
  3. MA composite non-regression <= -3pp (target MA >= 70.34%)
  4. Latency p95 <= 5s

3/4 PASS = SHIP OPT-IN + greenlight Q3 IterB (ReAct)
1-2/4 PASS = mechanism documented but insufficient
0/4 PASS = Q3 IterC dead, pivot to IterB direct

Usage:
    python3 aggregate_phaseIterC_5batch.py \\
        --runs-dir /root/.openclaw/evermembench-runs \\
        --pattern 'phaseIterC-*' \\
        --output-md RESULTS-Q3-ITERC-POC.md \\
        --output-json RESULTS-Q3-ITERC-POC.json
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent  # eval/evermembench -> repo root
sys.path.insert(0, str(REPO))

# Locked baseline from PR #377 RESULTS-PHASEH-v2-5BATCH.md
PHASE_H_V2_5BATCH = {
    "overall": 51.68,
    "F_SH": 80.97,
    "F_MH": 3.21,
    "F_TP": 15.00,
    "F_HL": 22.68,
    "MA_C": 84.60,
    "MA_P": 65.40,
    "MA_U": 70.03,
    "MA_composite": 73.34,  # mean(MA_C, MA_P, MA_U) per spec
    "P_Style": 39.78,
    "P_Skill": 49.77,
    "P_Title": 56.05,
}

# MemOS GPT-4.1-mini (Table 4) — F_MH gap tracker
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

# Gate thresholds (mirrors task spec §4)
GATES = {
    "F_MH_lift_pp_min": 2.0,        # F_MH lift >= +2pp vs Phase H v2
    "overall_max_regression_pp": 2.0,   # Overall regression <= -2pp
    "MA_composite_max_regression_pp": 3.0,  # MA composite non-regression <= -3pp
    "latency_p95_ms_max": 5000.0,    # Latency p95 <= 5s
}


def _parse_overall(text: str) -> Dict[str, float]:
    out: Dict[str, float] = {}
    m = re.search(
        r"Overall:\s+(\d+)\s+questions,\s+(\d+)\s+correct,\s+([\d.]+)%",
        text,
    )
    if m:
        out["_total"] = float(m.group(1))
        out["_correct"] = float(m.group(2))
        out["overall"] = float(m.group(3))
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
    out.update(_parse_combined(text))
    return out


def parse_iterc_meta(search_results_path: Path) -> Dict[str, Any]:
    """Walk search_results.json and compute Set E IterC coverage + Set E stats."""
    out: Dict[str, Any] = {
        "queries_total": 0,
        "queries_iterc_applied": 0,
        "queries_iterc_fallback": 0,
        "queries_iterc_error": 0,
        "sub_question_counts": [],   # N actual per query
        "decompose_ms": [],
        "retrieve_ms": [],
        "synthesis_ms": [],
        "total_latency_ms": [],
        "pre_dedup_total": [],
        "unique_after_dedup": [],
        "subq_overlap": [],
        "sub_answer_error_counts": [],
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
        if meta.get("iterc_applied"):
            out["queries_iterc_applied"] += 1
            n_actual = int(meta.get("iterc_n_actual") or 0)
            if n_actual > 0:
                out["sub_question_counts"].append(n_actual)
            for k_src, k_dst in (
                ("iterc_decompose_ms", "decompose_ms"),
                ("iterc_retrieve_ms", "retrieve_ms"),
                ("iterc_synthesis_ms", "synthesis_ms"),
            ):
                v = meta.get(k_src)
                if v is not None:
                    try:
                        out[k_dst].append(float(v))
                    except (TypeError, ValueError):
                        pass
            # Total latency = harness search_duration_ms if available
            sd = item.get("search_duration_ms")
            if sd is not None:
                try:
                    out["total_latency_ms"].append(float(sd))
                except (TypeError, ValueError):
                    pass
            pre = meta.get("iterc_total_results_pre_dedup")
            uniq = meta.get("iterc_unique_after_dedup")
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
            ov = meta.get("iterc_subq_overlap")
            if ov is not None:
                try:
                    out["subq_overlap"].append(float(ov))
                except (TypeError, ValueError):
                    pass
            err_count = meta.get("iterc_sub_answer_error_count")
            if err_count is not None:
                try:
                    out["sub_answer_error_counts"].append(int(err_count))
                except (TypeError, ValueError):
                    pass
            sq = meta.get("iterc_sub_questions") or []
            sa = meta.get("iterc_sub_answers") or []
            if sq and len(out["sample_decompositions"]) < 5:
                out["sample_decompositions"].append({
                    "query": item.get("query", "?"),
                    "sub_questions": sq,
                    "sub_answers": sa,
                })
        elif meta.get("iterc_status") == "fallback_single":
            out["queries_iterc_fallback"] += 1
        if meta.get("iterc_error"):
            out["queries_iterc_error"] += 1

    return out


def _percentile(xs: List[float], p: float) -> Optional[float]:
    if not xs:
        return None
    xs_sorted = sorted(xs)
    k = (len(xs_sorted) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(xs_sorted) - 1)
    if f == c:
        return xs_sorted[f]
    d0 = xs_sorted[f] * (c - k)
    d1 = xs_sorted[c] * (k - f)
    return d0 + d1


def _mean(xs: List[float]) -> Optional[float]:
    return statistics.fmean(xs) if xs else None


def aggregate_runs(
    runs_dir: Path, pattern: str
) -> Dict[str, Any]:
    run_dirs = sorted(p for p in runs_dir.glob(pattern) if p.is_dir())
    print(f"[iterc-agg] {len(run_dirs)} dirs matching {pattern} in {runs_dir}",
          file=sys.stderr)

    per_batch: List[Dict[str, Any]] = []
    aggregated_meta = {
        "queries_total": 0,
        "queries_iterc_applied": 0,
        "queries_iterc_fallback": 0,
        "queries_iterc_error": 0,
        "sub_question_counts": [],
        "decompose_ms": [],
        "retrieve_ms": [],
        "synthesis_ms": [],
        "total_latency_ms": [],
        "pre_dedup_total": [],
        "unique_after_dedup": [],
        "subq_overlap": [],
        "sub_answer_error_counts": [],
        "sample_decompositions": [],
    }

    for d in run_dirs:
        m = re.match(r"phaseIterC-(\d+)-\d+", d.name)
        batch = m.group(1) if m else d.name
        analysis = d / "analysis.txt"
        search_results = next(d.glob("search-results-batch-*.json"), None)
        scores: Dict[str, float] = {}
        if analysis.exists():
            scores = parse_analysis(analysis)
        meta_stats = (
            parse_iterc_meta(search_results) if search_results else {}
        )
        if scores or meta_stats:
            per_batch.append({"batch": batch, "scores": scores, "meta": meta_stats})

        # Roll into aggregate
        for k in (
            "queries_total",
            "queries_iterc_applied",
            "queries_iterc_fallback",
            "queries_iterc_error",
        ):
            aggregated_meta[k] += meta_stats.get(k, 0) or 0
        for k in (
            "sub_question_counts",
            "decompose_ms",
            "retrieve_ms",
            "synthesis_ms",
            "total_latency_ms",
            "pre_dedup_total",
            "unique_after_dedup",
            "subq_overlap",
            "sub_answer_error_counts",
        ):
            aggregated_meta[k].extend(meta_stats.get(k, []) or [])
        # Up to 5 samples total
        if len(aggregated_meta["sample_decompositions"]) < 5:
            remaining = 5 - len(aggregated_meta["sample_decompositions"])
            aggregated_meta["sample_decompositions"].extend(
                (meta_stats.get("sample_decompositions") or [])[:remaining]
            )

    # Aggregate per-metric across batches
    metric_keys = sorted({k for b in per_batch for k in b["scores"].keys()})
    aggregated_scores: Dict[str, Dict[str, Optional[float]]] = {}
    for k in metric_keys:
        vals = [b["scores"].get(k) for b in per_batch if b["scores"].get(k) is not None]
        if not vals:
            continue
        aggregated_scores[k] = {
            "mean": _mean(vals),
            "stdev": statistics.stdev(vals) if len(vals) > 1 else 0.0,
            "min": min(vals),
            "max": max(vals),
            "n_batches": len(vals),
        }

    # MA composite = mean(MA_C, MA_P, MA_U) per batch then aggregate
    ma_per_batch: List[float] = []
    for b in per_batch:
        s = b["scores"]
        parts = [s.get(k) for k in ("MA_C", "MA_P", "MA_U") if s.get(k) is not None]
        if len(parts) == 3:
            ma_per_batch.append(sum(parts) / 3.0)
    if ma_per_batch:
        aggregated_scores["MA_composite"] = {
            "mean": _mean(ma_per_batch),
            "stdev": statistics.stdev(ma_per_batch) if len(ma_per_batch) > 1 else 0.0,
            "min": min(ma_per_batch),
            "max": max(ma_per_batch),
            "n_batches": len(ma_per_batch),
        }

    # Latency summary
    lat_stats: Dict[str, Optional[float]] = {}
    lat = aggregated_meta["total_latency_ms"]
    if lat:
        lat_stats["mean_ms"] = _mean(lat)
        lat_stats["p50_ms"] = _percentile(lat, 50)
        lat_stats["p95_ms"] = _percentile(lat, 95)
        lat_stats["p99_ms"] = _percentile(lat, 99)
        lat_stats["max_ms"] = max(lat)
        lat_stats["n_queries"] = float(len(lat))

    # Sub-component latency summary
    component_lat: Dict[str, Optional[float]] = {}
    for k in ("decompose_ms", "retrieve_ms", "synthesis_ms"):
        xs = aggregated_meta[k]
        if xs:
            component_lat[f"{k}_mean"] = _mean(xs)
            component_lat[f"{k}_p95"] = _percentile(xs, 95)

    # Sub-question counts summary
    sq_counts = aggregated_meta["sub_question_counts"]
    sq_overlap = aggregated_meta["subq_overlap"]
    sub_q_stats = {
        "n_mean": _mean(sq_counts),
        "n_min": min(sq_counts) if sq_counts else None,
        "n_max": max(sq_counts) if sq_counts else None,
        "overlap_mean": _mean(sq_overlap),
        "overlap_p50": _percentile(sq_overlap, 50),
    }

    # Gate evaluation
    gates: Dict[str, Any] = {}
    overall_mean = aggregated_scores.get("overall", {}).get("mean")
    f_mh_mean = aggregated_scores.get("F_MH", {}).get("mean")
    ma_mean = aggregated_scores.get("MA_composite", {}).get("mean")
    lat_p95 = lat_stats.get("p95_ms")

    if f_mh_mean is not None:
        f_mh_lift = f_mh_mean - PHASE_H_V2_5BATCH["F_MH"]
        gates["F_MH_lift_pp"] = round(f_mh_lift, 3)
        gates["F_MH_pass"] = bool(f_mh_lift >= GATES["F_MH_lift_pp_min"])
    else:
        gates["F_MH_lift_pp"] = None
        gates["F_MH_pass"] = None

    if overall_mean is not None:
        ovr_delta = overall_mean - PHASE_H_V2_5BATCH["overall"]
        gates["overall_delta_pp"] = round(ovr_delta, 3)
        gates["overall_pass"] = bool(ovr_delta >= -GATES["overall_max_regression_pp"])
    else:
        gates["overall_delta_pp"] = None
        gates["overall_pass"] = None

    if ma_mean is not None:
        ma_delta = ma_mean - PHASE_H_V2_5BATCH["MA_composite"]
        gates["MA_composite_delta_pp"] = round(ma_delta, 3)
        gates["MA_pass"] = bool(
            ma_delta >= -GATES["MA_composite_max_regression_pp"]
        )
    else:
        gates["MA_composite_delta_pp"] = None
        gates["MA_pass"] = None

    if lat_p95 is not None:
        gates["latency_p95_ms"] = round(lat_p95, 1)
        gates["latency_pass"] = bool(lat_p95 <= GATES["latency_p95_ms_max"])
    else:
        gates["latency_p95_ms"] = None
        gates["latency_pass"] = None

    pass_count = sum(
        1 for k in ("F_MH_pass", "overall_pass", "MA_pass", "latency_pass")
        if gates.get(k) is True
    )
    gates["pass_count"] = pass_count
    gates["pass_out_of"] = 4
    if pass_count >= 3:
        gates["verdict"] = "SHIP_OPT_IN_GREENLIGHT_ITERB"
    elif pass_count >= 1:
        gates["verdict"] = "DOCUMENTED_INSUFFICIENT"
    else:
        gates["verdict"] = "DEAD_PIVOT_TO_ITERB"

    return {
        "per_batch": per_batch,
        "aggregated_scores": aggregated_scores,
        "iterc_meta_stats": {
            **{
                k: aggregated_meta[k]
                for k in (
                    "queries_total",
                    "queries_iterc_applied",
                    "queries_iterc_fallback",
                    "queries_iterc_error",
                )
            },
            "sub_question_stats": sub_q_stats,
            "latency": lat_stats,
            "component_latency": component_lat,
            "sample_decompositions": aggregated_meta["sample_decompositions"],
            "sub_answer_error_count_total": sum(
                aggregated_meta["sub_answer_error_counts"]
            ),
        },
        "gates": gates,
        "baseline_phaseH_v2": PHASE_H_V2_5BATCH,
        "memos_gpt41mini": MEMOS_GPT41MINI,
    }


def _fmt(v: Optional[float], fmt: str = "{:.2f}") -> str:
    if v is None:
        return "n/a"
    return fmt.format(v)


def _delta_fmt(delta: Optional[float]) -> str:
    if delta is None:
        return "n/a"
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.2f}pp"


def render_markdown(payload: Dict[str, Any]) -> str:
    agg = payload["aggregated_scores"]
    meta = payload["iterc_meta_stats"]
    gates = payload["gates"]
    base = payload["baseline_phaseH_v2"]
    memos = payload["memos_gpt41mini"]
    lat = meta.get("latency", {})
    clat = meta.get("component_latency", {})
    sq_stats = meta.get("sub_question_stats", {})

    verdict = gates.get("verdict", "?")
    pass_count = gates.get("pass_count", 0)

    lines: List[str] = []
    lines.append("# Q3 IterC POC — Self-Ask 5-batch Results")
    lines.append("")
    lines.append(f"**Verdict:** {verdict} ({pass_count}/4 gates pass)")
    lines.append("")
    lines.append(
        "Phase IterC POC implements Self-Ask (Press et al. 2022, arxiv:2210.03350) — "
        "the cheapest of Q3's three orchestration-stage candidates per "
        "PR #393 spec. Goal: validate whether moving the mechanism from "
        "retrieval-stage stacking (Waves A/B/C, F_MH ceiling ≈7.25%) to "
        "orchestration-stage opens a new lift axis on F_MH."
    )
    lines.append("")
    lines.append("## Headline 5-batch metrics (sequential 004,005,010,011,016)")
    lines.append("")
    lines.append(
        "| Metric | Phase H v2 5-batch | Phase IterC 5-batch | Δ vs H v2 | MemOS GPT-4.1-mini | Δ vs MemOS |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|")
    for k in (
        "overall", "F_SH", "F_MH", "F_TP", "F_HL",
        "MA_C", "MA_P", "MA_U", "MA_composite",
        "P_Style", "P_Skill", "P_Title",
    ):
        bv = base.get(k)
        iv = agg.get(k, {}).get("mean") if isinstance(agg.get(k), dict) else None
        memos_v = memos.get(k)
        d_base = (iv - bv) if (iv is not None and bv is not None) else None
        d_memos = (iv - memos_v) if (iv is not None and memos_v is not None) else None
        lines.append(
            f"| {k} | {_fmt(bv)} | {_fmt(iv)} | {_delta_fmt(d_base)} | "
            f"{_fmt(memos_v)} | {_delta_fmt(d_memos)} |"
        )
    lines.append("")

    # Gate matrix
    lines.append("## 4-Gate verdict matrix")
    lines.append("")
    lines.append("| Gate | Threshold | Observed | Pass |")
    lines.append("|---|---|---|---|")
    lines.append(
        f"| 1. F_MH lift | ≥ +2.00pp | {_delta_fmt(gates.get('F_MH_lift_pp'))} | "
        f"{'PASS' if gates.get('F_MH_pass') else 'FAIL'} |"
    )
    lines.append(
        f"| 2. Overall regression | ≥ -2.00pp | {_delta_fmt(gates.get('overall_delta_pp'))} | "
        f"{'PASS' if gates.get('overall_pass') else 'FAIL'} |"
    )
    lines.append(
        f"| 3. MA composite | ≥ -3.00pp | {_delta_fmt(gates.get('MA_composite_delta_pp'))} | "
        f"{'PASS' if gates.get('MA_pass') else 'FAIL'} |"
    )
    lines.append(
        f"| 4. Latency p95 | ≤ 5000ms | {_fmt(gates.get('latency_p95_ms'), '{:.0f}')}ms | "
        f"{'PASS' if gates.get('latency_pass') else 'FAIL'} |"
    )
    lines.append("")
    lines.append(f"**Total:** {pass_count}/4 gates pass → **{verdict}**.")
    lines.append("")
    if pass_count >= 3:
        lines.append(
            "**Decision rule:** 3/4 PASS = SHIP OPT-IN + greenlight Q3 IterB "
            "(ReAct full implementation per PR #393 spec §3.B)."
        )
    elif pass_count >= 1:
        lines.append(
            "**Decision rule:** 1-2/4 PASS = mechanism documented but "
            "insufficient. Inspect Set E to decide whether Q3 IterB (ReAct) "
            "should rerun with isolated knob or pivot."
        )
    else:
        lines.append(
            "**Decision rule:** 0/4 PASS = Q3 IterC dead. Pivot directly to "
            "Q3 IterB (ReAct) — orchestration hypothesis still alive but "
            "Self-Ask shape rejected."
        )
    lines.append("")

    # Set E
    lines.append("## Set E (per-query instrumentation)")
    lines.append("")
    lines.append(
        f"- Queries total: {meta.get('queries_total', 0)}"
    )
    lines.append(
        f"- IterC applied: {meta.get('queries_iterc_applied', 0)} "
        f"({100*meta.get('queries_iterc_applied', 0)/max(meta.get('queries_total', 1), 1):.1f}%)"
    )
    lines.append(
        f"- Decomposer fallback (single-query): {meta.get('queries_iterc_fallback', 0)}"
    )
    lines.append(
        f"- IterC errors total: {meta.get('queries_iterc_error', 0)}"
    )
    lines.append(
        f"- Sub-answer errors total: {meta.get('sub_answer_error_count_total', 0)}"
    )
    lines.append("")
    lines.append("**Sub-question counts:**")
    lines.append(
        f"- mean N = {_fmt(sq_stats.get('n_mean'), '{:.2f}')} "
        f"(range {sq_stats.get('n_min')}-{sq_stats.get('n_max')})"
    )
    lines.append(
        f"- mean per-sub-Q overlap (Jaccard) = "
        f"{_fmt(sq_stats.get('overlap_mean'), '{:.3f}')} "
        f"(p50 {_fmt(sq_stats.get('overlap_p50'), '{:.3f}')})"
    )
    lines.append(
        "  - Low overlap → sub-Qs span distinct facets (Self-Ask sweet spot)"
    )
    lines.append(
        "  - High overlap (>0.5) → decomposition redundant, less benefit expected"
    )
    lines.append("")
    lines.append("**Latency breakdown:**")
    lines.append(
        f"- decompose: mean {_fmt(clat.get('decompose_ms_mean'), '{:.0f}')}ms, "
        f"p95 {_fmt(clat.get('decompose_ms_p95'), '{:.0f}')}ms"
    )
    lines.append(
        f"- retrieve (N parallel): mean {_fmt(clat.get('retrieve_ms_mean'), '{:.0f}')}ms, "
        f"p95 {_fmt(clat.get('retrieve_ms_p95'), '{:.0f}')}ms"
    )
    lines.append(
        f"- synthesis (N parallel sub-answers): "
        f"mean {_fmt(clat.get('synthesis_ms_mean'), '{:.0f}')}ms, "
        f"p95 {_fmt(clat.get('synthesis_ms_p95'), '{:.0f}')}ms"
    )
    lines.append(
        f"- total search_duration_ms: mean {_fmt(lat.get('mean_ms'), '{:.0f}')}ms, "
        f"p50 {_fmt(lat.get('p50_ms'), '{:.0f}')}ms, "
        f"p95 {_fmt(lat.get('p95_ms'), '{:.0f}')}ms, "
        f"p99 {_fmt(lat.get('p99_ms'), '{:.0f}')}ms"
    )
    lines.append("")

    # Wave A/B/C composition outlook
    lines.append("## Composition outlook with Wave A/B/C retrieval knobs")
    lines.append("")
    lines.append(
        "Self-Ask operates at the orchestration stage. Wave A/B/C "
        "mechanisms (KG path, MA-protection, MQ, rerank) operate at the "
        "retrieval stage. The hypothesis (per PR #393 spec §1) is that the "
        "two stages are partially orthogonal — so composition should be "
        "approximately additive minus an interaction penalty."
    )
    lines.append("")
    f_mh_lift = gates.get("F_MH_lift_pp")
    if f_mh_lift is not None and f_mh_lift > 0:
        # Estimate composite ceiling: Wave A/B/C F_MH ceiling ≈7.25% (D69 cravada)
        # IterC lift on top of Phase H v2 (3.21%) gives orthogonal component.
        # Pessimistic additive: 7.25% + lift - 1pp interaction penalty.
        wave_abc_ceiling = 7.25
        composed_pessimistic = wave_abc_ceiling + max(0.0, f_mh_lift - 1.0)
        composed_optimistic = wave_abc_ceiling + f_mh_lift
        memos_gap = MEMOS_GPT41MINI["F_MH"] - wave_abc_ceiling
        closed_pess = 100.0 * (composed_pessimistic - wave_abc_ceiling) / memos_gap
        closed_opt = 100.0 * (composed_optimistic - wave_abc_ceiling) / memos_gap
        lines.append(
            f"- Wave A/B/C F_MH ceiling (D69 cravada): 7.25% (PR #395)"
        )
        lines.append(
            f"- IterC F_MH lift on Phase H v2: {_delta_fmt(f_mh_lift)}"
        )
        lines.append(
            f"- Pessimistic composed F_MH (Wave A/B/C ⊕ IterC w/ -1pp interaction "
            f"penalty): {composed_pessimistic:.2f}%"
        )
        lines.append(
            f"- Optimistic composed F_MH (pure additive): {composed_optimistic:.2f}%"
        )
        lines.append(
            f"- MemOS F_MH gap closure if pessimistic holds: "
            f"{closed_pess:.1f}% (currently {wave_abc_ceiling:.2f}% → MemOS {MEMOS_GPT41MINI['F_MH']:.2f}%)"
        )
        lines.append(
            f"- MemOS F_MH gap closure if optimistic holds: {closed_opt:.1f}%"
        )
        lines.append("")
        lines.append(
            "**Caveat:** This is a back-of-envelope projection. Real composition "
            "must be measured by stacking Wave A/B/C knobs on top of IterC in a "
            "follow-up run. The POC isolated Self-Ask vs Phase H v2 baseline by "
            "design — clean orthogonality test."
        )
    else:
        lines.append(
            "F_MH lift was zero or negative — Wave A/B/C ⊕ IterC composition "
            "irrelevant for this knob. Pivot to Q3 IterB (ReAct) directly per "
            "decision rule."
        )
    lines.append("")

    # Per-batch table
    lines.append("## Per-batch breakdown")
    lines.append("")
    lines.append("| Batch | Overall | F_MH | F_SH | F_TP | MA_C | MA_P | MA_U |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for b in payload["per_batch"]:
        s = b["scores"]
        lines.append(
            f"| {b['batch']} | {_fmt(s.get('overall'))} | "
            f"{_fmt(s.get('F_MH'))} | {_fmt(s.get('F_SH'))} | "
            f"{_fmt(s.get('F_TP'))} | {_fmt(s.get('MA_C'))} | "
            f"{_fmt(s.get('MA_P'))} | {_fmt(s.get('MA_U'))} |"
        )
    lines.append("")

    # Sample decompositions
    if meta.get("sample_decompositions"):
        lines.append("## Sample Self-Ask decompositions")
        lines.append("")
        for i, sample in enumerate(meta["sample_decompositions"], 1):
            lines.append(f"### Sample {i}")
            lines.append(f"- **Query:** {sample.get('query', '?')[:200]}")
            for j, sq in enumerate(sample.get("sub_questions") or [], 1):
                lines.append(f"  {j}. *Sub-Q:* {sq[:200]}")
                sa = (sample.get("sub_answers") or [])
                if j - 1 < len(sa):
                    lines.append(f"     *Sub-A:* {sa[j-1][:200]}")
            lines.append("")

    # Ship recommendation
    lines.append("## Ship recommendation")
    lines.append("")
    if pass_count >= 3:
        lines.append(
            "**SHIP OPT-IN** with `NOX_ADAPTER_MODE=phaseIterC` or "
            "`NOX_ITERC_ENABLED=1`. Greenlight Q3 IterB (ReAct full) — "
            "orthogonal-stage hypothesis CONFIRMED."
        )
    elif pass_count == 2:
        lines.append(
            "**DOCUMENT + DEFER.** Mechanism shows partial wins; gate-strict "
            "criterion not met. Consider deeper isolation analysis (Set E sub-Q "
            "overlap + per-sub-A error rate) before greenlighting IterB."
        )
    elif pass_count == 1:
        lines.append(
            "**DOCUMENT + PIVOT to IterB.** Single-gate win is insufficient. "
            "Self-Ask shape does not break F_MH ceiling at orthogonal cost; "
            "test if ReAct (richer multi-round orchestration) does better."
        )
    else:
        lines.append(
            "**DEAD.** 0/4 PASS — Self-Ask shape rejected. Pivot directly to "
            "Q3 IterB (ReAct) per PR #393 §3.B. Document mechanism for paper."
        )
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--runs-dir", required=True, type=Path)
    p.add_argument("--pattern", default="phaseIterC-*")
    p.add_argument("--output-md", required=True, type=Path)
    p.add_argument("--output-json", required=True, type=Path)
    args = p.parse_args()

    payload = aggregate_runs(args.runs_dir, args.pattern)
    args.output_json.write_text(json.dumps(payload, indent=2, default=str))
    args.output_md.write_text(render_markdown(payload))
    print(f"[iterc-agg] wrote {args.output_md}")
    print(f"[iterc-agg] wrote {args.output_json}")
    print(f"[iterc-agg] verdict: {payload['gates'].get('verdict')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
