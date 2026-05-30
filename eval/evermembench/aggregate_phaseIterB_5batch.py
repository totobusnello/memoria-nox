#!/usr/bin/env python3
"""Aggregate Phase IterB (Q3 POC) 5-batch results + generate RESULTS-Q3-ITERB-POC.md.

Mirrors aggregate_phaseIterC_5batch.py shape. Reads analysis.txt from each
phaseIterB-<batch>-<ts>/ run dir, parses Combined + Overall sections, then
calls into the Set E (per-query ReAct instrumentation) JSON for round
counts, overlap stats, termination reasons, cost.

Compares against:
  - Phase H v2 5-batch baseline (PR #377) — orchestration-stage delta target
  - MemOS GPT-4.1-mini Table 4 — F_MH gap closure tracker
  - Phase IterC 5-batch (PR #406, DOCUMENTED_INSUFFICIENT) — sibling
    orchestration POC (Self-Ask was wrong class for F_MH).

Gate criteria (per task spec §4):
  1. F_MH lift >= +3pp 5-batch (target F_MH >= 6.21%) — primary canonical
     F_MH ceiling break attempt
  2. Overall regression <= -3pp (allow some cost for orchestration)
  3. MA composite non-regression <= -3pp tolerance
  4. Cost per query <= $0.01 (orchestration cap; gate aligned with
     NOX_ITERB_COST_CEILING_USD)

3/4 PASS = SHIP OPT-IN canonical F_MH ceiling break
4/4 PASS = potential default switch on (depends on Q1 full impl)
≤2/4 PASS = REJECT — Q3 IterB doesn't break ceiling, document insight

Usage:
    python3 aggregate_phaseIterB_5batch.py \\
        --runs-dir /root/.openclaw/evermembench-runs \\
        --pattern 'phaseIterB-*' \\
        --output-md RESULTS-Q3-ITERB-POC.md \\
        --output-json RESULTS-Q3-ITERB-POC.json
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
    "MA_composite": 73.34,
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

# Sibling Phase IterC 5-batch (PR #406) — for orchestration comparison.
# Placeholder zeros if IterC results not parseable; the markdown still
# renders meaningfully against H v2 + MemOS.
PHASE_ITERC_5BATCH_REFERENCE = {
    "overall": None,
    "F_MH": None,
    "MA_composite": None,
}

# Wave A/B/C F_MH ceiling — D69 cravada (PR #395)
WAVE_ABC_F_MH_CEILING = 7.25

# Gate thresholds (mirrors task spec §4 — IterB-specific)
GATES = {
    "F_MH_lift_pp_min": 3.0,            # primary, vs Phase H v2 3.21%
    "overall_max_regression_pp": 3.0,   # allow more headroom for orchestration
    "MA_composite_max_regression_pp": 3.0,
    "cost_per_query_usd_max": 0.01,     # NOX_ITERB_COST_CEILING_USD
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


def parse_iterb_meta(search_results_path: Path) -> Dict[str, Any]:
    """Walk search_results.json and compute Set E IterB stats."""
    out: Dict[str, Any] = {
        "queries_total": 0,
        "queries_iterb_applied": 0,
        "queries_iterb_fallback": 0,
        "queries_iterb_error": 0,
        "rounds_executed_per_query": [],
        "termination_reasons": {},
        "per_query_chunk_counts_first_round": [],
        "per_query_chunk_counts_last_round": [],
        "per_query_overlap_round2": [],   # round 2 overlap vs prior (best signal)
        "per_query_overlap_round3": [],
        "per_query_total_latency_ms": [],
        "per_query_cost_usd": [],
        "per_query_input_tokens": [],
        "per_query_output_tokens": [],
        "sample_traces": [],  # up to 5 samples for paper
        "loop_ms_list": [],
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
        if meta.get("iterb_applied"):
            out["queries_iterb_applied"] += 1
            rounds = int(meta.get("iterb_rounds_executed") or 0)
            if rounds > 0:
                out["rounds_executed_per_query"].append(rounds)
            reason = str(meta.get("iterb_termination_reason") or "unknown")
            out["termination_reasons"][reason] = (
                out["termination_reasons"].get(reason, 0) + 1
            )
            cnt_list = meta.get("iterb_per_round_chunk_counts") or []
            if cnt_list:
                out["per_query_chunk_counts_first_round"].append(cnt_list[0])
                out["per_query_chunk_counts_last_round"].append(cnt_list[-1])
            overlap_list = meta.get("iterb_per_round_overlap_with_prior") or []
            if len(overlap_list) >= 2 and overlap_list[1] is not None:
                try:
                    out["per_query_overlap_round2"].append(float(overlap_list[1]))
                except (TypeError, ValueError):
                    pass
            if len(overlap_list) >= 3 and overlap_list[2] is not None:
                try:
                    out["per_query_overlap_round3"].append(float(overlap_list[2]))
                except (TypeError, ValueError):
                    pass
            sd = item.get("search_duration_ms")
            if sd is not None:
                try:
                    out["per_query_total_latency_ms"].append(float(sd))
                except (TypeError, ValueError):
                    pass
            cost = meta.get("iterb_total_cost_usd")
            if cost is not None:
                try:
                    out["per_query_cost_usd"].append(float(cost))
                except (TypeError, ValueError):
                    pass
            in_t = meta.get("iterb_total_input_tokens")
            out_t = meta.get("iterb_total_output_tokens")
            if in_t is not None:
                try:
                    out["per_query_input_tokens"].append(int(in_t))
                except (TypeError, ValueError):
                    pass
            if out_t is not None:
                try:
                    out["per_query_output_tokens"].append(int(out_t))
                except (TypeError, ValueError):
                    pass
            loop_ms = meta.get("iterb_loop_ms")
            if loop_ms is not None:
                try:
                    out["loop_ms_list"].append(float(loop_ms))
                except (TypeError, ValueError):
                    pass
            # Sample trace
            if len(out["sample_traces"]) < 5:
                sub_qs = meta.get("iterb_per_round_sub_queries") or []
                thoughts = meta.get("iterb_per_round_thoughts") or []
                draft = meta.get("iterb_final_draft_answer") or ""
                if sub_qs or thoughts or draft:
                    out["sample_traces"].append({
                        "query": item.get("query", "?"),
                        "rounds": rounds,
                        "termination": reason,
                        "sub_queries": sub_qs,
                        "thoughts": thoughts,
                        "draft_answer": draft,
                        "cost_usd": cost,
                    })
        elif meta.get("iterb_status") == "fallback_single":
            out["queries_iterb_fallback"] += 1
        if meta.get("iterb_error"):
            out["queries_iterb_error"] += 1

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
    print(f"[iterb-agg] {len(run_dirs)} dirs matching {pattern} in {runs_dir}",
          file=sys.stderr)

    per_batch: List[Dict[str, Any]] = []
    aggregated_meta = {
        "queries_total": 0,
        "queries_iterb_applied": 0,
        "queries_iterb_fallback": 0,
        "queries_iterb_error": 0,
        "rounds_executed_per_query": [],
        "termination_reasons": {},
        "per_query_chunk_counts_first_round": [],
        "per_query_chunk_counts_last_round": [],
        "per_query_overlap_round2": [],
        "per_query_overlap_round3": [],
        "per_query_total_latency_ms": [],
        "per_query_cost_usd": [],
        "per_query_input_tokens": [],
        "per_query_output_tokens": [],
        "sample_traces": [],
        "loop_ms_list": [],
    }

    for d in run_dirs:
        m = re.match(r"phaseIterB-(\d+)-\d+", d.name)
        batch = m.group(1) if m else d.name
        analysis = d / "analysis.txt"
        search_results = next(d.glob("search-results-batch-*.json"), None)
        scores: Dict[str, float] = {}
        if analysis.exists():
            scores = parse_analysis(analysis)
        meta_stats = (
            parse_iterb_meta(search_results) if search_results else {}
        )
        if scores or meta_stats:
            per_batch.append({"batch": batch, "scores": scores, "meta": meta_stats})

        # Roll into aggregate
        for k in (
            "queries_total",
            "queries_iterb_applied",
            "queries_iterb_fallback",
            "queries_iterb_error",
        ):
            aggregated_meta[k] += meta_stats.get(k, 0) or 0
        for k in (
            "rounds_executed_per_query",
            "per_query_chunk_counts_first_round",
            "per_query_chunk_counts_last_round",
            "per_query_overlap_round2",
            "per_query_overlap_round3",
            "per_query_total_latency_ms",
            "per_query_cost_usd",
            "per_query_input_tokens",
            "per_query_output_tokens",
            "loop_ms_list",
        ):
            aggregated_meta[k].extend(meta_stats.get(k, []) or [])
        # Termination reasons (dict merge)
        for reason, cnt in (meta_stats.get("termination_reasons") or {}).items():
            aggregated_meta["termination_reasons"][reason] = (
                aggregated_meta["termination_reasons"].get(reason, 0) + cnt
            )
        if len(aggregated_meta["sample_traces"]) < 5:
            remaining = 5 - len(aggregated_meta["sample_traces"])
            aggregated_meta["sample_traces"].extend(
                (meta_stats.get("sample_traces") or [])[:remaining]
            )

    # Per-metric aggregation across batches
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

    # MA composite per batch
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
    lat = aggregated_meta["per_query_total_latency_ms"]
    if lat:
        lat_stats["mean_ms"] = _mean(lat)
        lat_stats["p50_ms"] = _percentile(lat, 50)
        lat_stats["p95_ms"] = _percentile(lat, 95)
        lat_stats["p99_ms"] = _percentile(lat, 99)
        lat_stats["max_ms"] = max(lat)
        lat_stats["n_queries"] = float(len(lat))

    # Cost summary
    cost_stats: Dict[str, Optional[float]] = {}
    costs = aggregated_meta["per_query_cost_usd"]
    if costs:
        cost_stats["mean_usd"] = _mean(costs)
        cost_stats["p50_usd"] = _percentile(costs, 50)
        cost_stats["p95_usd"] = _percentile(costs, 95)
        cost_stats["p99_usd"] = _percentile(costs, 99)
        cost_stats["max_usd"] = max(costs)
        cost_stats["sum_usd"] = sum(costs)

    # Round stats
    rounds = aggregated_meta["rounds_executed_per_query"]
    round_stats: Dict[str, Any] = {
        "rounds_mean": _mean(rounds),
        "rounds_min": min(rounds) if rounds else None,
        "rounds_max": max(rounds) if rounds else None,
        "rounds_p50": _percentile(rounds, 50) if rounds else None,
        "rounds_p95": _percentile(rounds, 95) if rounds else None,
        "overlap_round2_mean": _mean(aggregated_meta["per_query_overlap_round2"]),
        "overlap_round3_mean": _mean(aggregated_meta["per_query_overlap_round3"]),
        "chunks_first_round_mean": _mean(
            aggregated_meta["per_query_chunk_counts_first_round"]
        ),
        "chunks_last_round_mean": _mean(
            aggregated_meta["per_query_chunk_counts_last_round"]
        ),
    }

    # Gate evaluation
    gates: Dict[str, Any] = {}
    overall_mean = aggregated_scores.get("overall", {}).get("mean")
    f_mh_mean = aggregated_scores.get("F_MH", {}).get("mean")
    ma_mean = aggregated_scores.get("MA_composite", {}).get("mean")
    cost_mean = cost_stats.get("mean_usd")

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

    if cost_mean is not None:
        gates["cost_per_query_usd"] = round(cost_mean, 5)
        gates["cost_pass"] = bool(cost_mean <= GATES["cost_per_query_usd_max"])
    else:
        gates["cost_per_query_usd"] = None
        gates["cost_pass"] = None

    pass_count = sum(
        1 for k in ("F_MH_pass", "overall_pass", "MA_pass", "cost_pass")
        if gates.get(k) is True
    )
    gates["pass_count"] = pass_count
    gates["pass_out_of"] = 4
    if pass_count >= 4:
        gates["verdict"] = "SHIP_DEFAULT_CANDIDATE"
    elif pass_count >= 3:
        gates["verdict"] = "SHIP_OPT_IN_F_MH_BREAK"
    elif pass_count >= 1:
        gates["verdict"] = "DOCUMENTED_INSUFFICIENT"
    else:
        gates["verdict"] = "REJECT_CEILING_HOLDS"

    return {
        "per_batch": per_batch,
        "aggregated_scores": aggregated_scores,
        "iterb_meta_stats": {
            **{
                k: aggregated_meta[k]
                for k in (
                    "queries_total",
                    "queries_iterb_applied",
                    "queries_iterb_fallback",
                    "queries_iterb_error",
                    "termination_reasons",
                )
            },
            "round_stats": round_stats,
            "latency": lat_stats,
            "cost": cost_stats,
            "sample_traces": aggregated_meta["sample_traces"],
            "tokens_input_total": sum(aggregated_meta["per_query_input_tokens"]),
            "tokens_output_total": sum(aggregated_meta["per_query_output_tokens"]),
        },
        "gates": gates,
        "baseline_phaseH_v2": PHASE_H_V2_5BATCH,
        "memos_gpt41mini": MEMOS_GPT41MINI,
        "wave_abc_f_mh_ceiling": WAVE_ABC_F_MH_CEILING,
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
    meta = payload["iterb_meta_stats"]
    gates = payload["gates"]
    base = payload["baseline_phaseH_v2"]
    memos = payload["memos_gpt41mini"]
    wave_abc_ceil = payload["wave_abc_f_mh_ceiling"]
    lat = meta.get("latency", {})
    cost = meta.get("cost", {})
    rstats = meta.get("round_stats", {})

    verdict = gates.get("verdict", "?")
    pass_count = gates.get("pass_count", 0)

    lines: List[str] = []
    lines.append("# Q3 IterB POC — ReAct 5-batch Results")
    lines.append("")
    lines.append(f"**Verdict:** {verdict} ({pass_count}/4 gates pass)")
    lines.append("")
    lines.append(
        "Phase IterB POC implements ReAct (Yao et al. 2022, arxiv:2210.03629) "
        "— canonical multi-round retrieve-reason orchestration. Per PR #393 "
        "spec §3.B, ReAct is the canonical mechanism for sequential multi-hop "
        "chains. Q3 IterC (PR #406, Self-Ask) confirmed Self-Ask the wrong "
        "class for F_MH (2/4 gates). IterB is the remaining hypothesis for "
        "breaking the Wave A/B/C F_MH ceiling at "
        f"{wave_abc_ceil:.2f}% (D69 cravada, PR #395)."
    )
    lines.append("")
    lines.append("## Headline 5-batch metrics (sequential 004,005,010,011,016)")
    lines.append("")
    lines.append(
        "| Metric | Phase H v2 5-batch | Phase IterB 5-batch | Δ vs H v2 | MemOS GPT-4.1-mini | Δ vs MemOS |"
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
        f"| 1. F_MH lift | ≥ +3.00pp | {_delta_fmt(gates.get('F_MH_lift_pp'))} | "
        f"{'PASS' if gates.get('F_MH_pass') else 'FAIL'} |"
    )
    lines.append(
        f"| 2. Overall regression | ≥ -3.00pp | {_delta_fmt(gates.get('overall_delta_pp'))} | "
        f"{'PASS' if gates.get('overall_pass') else 'FAIL'} |"
    )
    lines.append(
        f"| 3. MA composite | ≥ -3.00pp | {_delta_fmt(gates.get('MA_composite_delta_pp'))} | "
        f"{'PASS' if gates.get('MA_pass') else 'FAIL'} |"
    )
    lines.append(
        f"| 4. Cost per query | ≤ $0.01 | "
        f"${_fmt(gates.get('cost_per_query_usd'), '{:.5f}')} | "
        f"{'PASS' if gates.get('cost_pass') else 'FAIL'} |"
    )
    lines.append("")
    lines.append(f"**Total:** {pass_count}/4 gates pass → **{verdict}**.")
    lines.append("")
    if pass_count >= 4:
        lines.append(
            "**Decision rule:** 4/4 PASS = SHIP DEFAULT candidate — canonical "
            "F_MH ceiling break confirmed. Greenlight full Q1 implementation."
        )
    elif pass_count >= 3:
        lines.append(
            "**Decision rule:** 3/4 PASS = SHIP OPT-IN canonical F_MH "
            "ceiling break. Enable via NOX_ADAPTER_MODE=phaseIterB or "
            "NOX_ITERB_ENABLED=1. Full Q1 evaluation needed for default switch."
        )
    elif pass_count >= 1:
        lines.append(
            "**Decision rule:** 1-2/4 PASS = mechanism documented but "
            "insufficient. ReAct shows partial wins; inspect Set E "
            "(rounds + overlap + termination reasons) to decide whether to "
            "iterate prompt + termination logic or pivot."
        )
    else:
        lines.append(
            "**Decision rule:** 0/4 PASS = Wave A/B/C F_MH ceiling holds. "
            "Orchestration-stage hypothesis rejected for EverMemBench shape. "
            "Document insight + close Q3 IterB. F_MH gap vs MemOS is "
            "structural to EverMemBench (per D72 reframe)."
        )
    lines.append("")

    # Set E
    lines.append("## Set E (per-query ReAct instrumentation)")
    lines.append("")
    lines.append(
        f"- Queries total: {meta.get('queries_total', 0)}"
    )
    qa = meta.get('queries_iterb_applied', 0)
    qt = max(meta.get('queries_total', 1), 1)
    lines.append(
        f"- IterB applied: {qa} ({100 * qa / qt:.1f}%)"
    )
    lines.append(
        f"- IterB fallback (single-query): {meta.get('queries_iterb_fallback', 0)}"
    )
    lines.append(
        f"- IterB errors total: {meta.get('queries_iterb_error', 0)}"
    )
    lines.append("")
    term = meta.get("termination_reasons", {})
    if term:
        lines.append("**Termination reasons:**")
        for reason, cnt in sorted(term.items(), key=lambda x: -x[1]):
            pct = 100 * cnt / max(qa, 1) if qa else 0.0
            lines.append(f"- {reason}: {cnt} ({pct:.1f}%)")
        lines.append("")
    lines.append("**Round statistics:**")
    lines.append(
        f"- mean rounds = {_fmt(rstats.get('rounds_mean'), '{:.2f}')} "
        f"(range {rstats.get('rounds_min')}-{rstats.get('rounds_max')}, "
        f"p50 {_fmt(rstats.get('rounds_p50'), '{:.0f}')}, "
        f"p95 {_fmt(rstats.get('rounds_p95'), '{:.0f}')})"
    )
    lines.append(
        f"- mean chunks first round = {_fmt(rstats.get('chunks_first_round_mean'), '{:.1f}')}"
    )
    lines.append(
        f"- mean chunks last round = {_fmt(rstats.get('chunks_last_round_mean'), '{:.1f}')}"
    )
    lines.append("")
    lines.append("**Per-round overlap (Jaccard vs union of priors):**")
    lines.append(
        f"- mean round-2 overlap = {_fmt(rstats.get('overlap_round2_mean'), '{:.3f}')}"
    )
    lines.append(
        f"- mean round-3 overlap = {_fmt(rstats.get('overlap_round3_mean'), '{:.3f}')}"
    )
    lines.append(
        "  - Low overlap → each round explores NEW evidence (ReAct sweet spot)"
    )
    lines.append(
        "  - High overlap (>0.5) → orchestrator stuck in loops, retrieves redundant"
    )
    lines.append("")
    lines.append("**Cost & latency:**")
    lines.append(
        f"- cost per query: mean ${_fmt(cost.get('mean_usd'), '{:.5f}')}, "
        f"p50 ${_fmt(cost.get('p50_usd'), '{:.5f}')}, "
        f"p95 ${_fmt(cost.get('p95_usd'), '{:.5f}')}, "
        f"p99 ${_fmt(cost.get('p99_usd'), '{:.5f}')}, "
        f"max ${_fmt(cost.get('max_usd'), '{:.5f}')}"
    )
    lines.append(
        f"- total orchestration spend: ${_fmt(cost.get('sum_usd'), '{:.4f}')}"
    )
    lines.append(
        f"- tokens: input {meta.get('tokens_input_total', 0):,} / "
        f"output {meta.get('tokens_output_total', 0):,}"
    )
    lines.append(
        f"- total latency: mean {_fmt(lat.get('mean_ms'), '{:.0f}')}ms, "
        f"p50 {_fmt(lat.get('p50_ms'), '{:.0f}')}ms, "
        f"p95 {_fmt(lat.get('p95_ms'), '{:.0f}')}ms, "
        f"p99 {_fmt(lat.get('p99_ms'), '{:.0f}')}ms"
    )
    lines.append("")

    # Composability + ceiling break analysis
    lines.append("## Composability with Wave A/B/C and ceiling break")
    lines.append("")
    f_mh_iv = agg.get("F_MH", {}).get("mean") if isinstance(agg.get("F_MH"), dict) else None
    if f_mh_iv is not None:
        gap_to_ceiling = f_mh_iv - wave_abc_ceil
        memos_gap_before = MEMOS_GPT41MINI["F_MH"] - wave_abc_ceil
        gap_closed_pct = (
            100.0 * (f_mh_iv - wave_abc_ceil) / memos_gap_before
            if memos_gap_before > 0 else None
        )
        lines.append(
            f"- Wave A/B/C F_MH ceiling (D69 cravada, PR #395): {wave_abc_ceil:.2f}%"
        )
        lines.append(
            f"- Phase IterB F_MH 5-batch: {f_mh_iv:.2f}%"
        )
        lines.append(
            f"- Δ vs ceiling: {_delta_fmt(gap_to_ceiling)} "
            f"({'BREAKS ceiling' if gap_to_ceiling > 0 else 'WITHIN ceiling'})"
        )
        if gap_closed_pct is not None:
            lines.append(
                f"- MemOS F_MH gap closure: "
                f"{gap_closed_pct:.1f}% "
                f"(ceiling {wave_abc_ceil:.2f}% → IterB {f_mh_iv:.2f}% → MemOS {MEMOS_GPT41MINI['F_MH']:.2f}%)"
            )
        lines.append("")
        lines.append(
            "**Composability projection** (IterB ⊕ Wave A/B/C, additive minus "
            "1pp interaction penalty):"
        )
        iterb_lift_over_h_v2 = f_mh_iv - PHASE_H_V2_5BATCH["F_MH"]
        composed_pess = wave_abc_ceil + max(0.0, iterb_lift_over_h_v2 - 1.0)
        composed_opt = wave_abc_ceil + iterb_lift_over_h_v2
        memos_gap = MEMOS_GPT41MINI["F_MH"] - wave_abc_ceil
        if memos_gap > 0:
            closed_pess = 100.0 * (composed_pess - wave_abc_ceil) / memos_gap
            closed_opt = 100.0 * (composed_opt - wave_abc_ceil) / memos_gap
        else:
            closed_pess = closed_opt = None
        lines.append(
            f"- Pessimistic composed F_MH (Wave A/B/C ⊕ IterB w/ -1pp): "
            f"{composed_pess:.2f}%"
        )
        lines.append(
            f"- Optimistic composed F_MH (pure additive): {composed_opt:.2f}%"
        )
        if closed_pess is not None:
            lines.append(
                f"- MemOS F_MH gap closure pessimistic: {closed_pess:.1f}%"
            )
            lines.append(
                f"- MemOS F_MH gap closure optimistic: {closed_opt:.1f}%"
            )
        lines.append("")
        lines.append(
            "**Caveat:** projection is back-of-envelope. Real Wave A/B/C ⊕ "
            "IterB composition must be measured by stacking knobs on top of "
            "IterB in a follow-up run. This POC isolated ReAct vs Phase H v2 "
            "baseline by design — clean orthogonality test."
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

    # Sample traces
    if meta.get("sample_traces"):
        lines.append("## Sample ReAct traces")
        lines.append("")
        for i, sample in enumerate(meta["sample_traces"], 1):
            lines.append(f"### Sample {i}")
            lines.append(f"- **Query:** {sample.get('query', '?')[:200]}")
            lines.append(f"- **Rounds:** {sample.get('rounds', '?')}")
            lines.append(f"- **Termination:** {sample.get('termination', '?')}")
            cost_s = sample.get("cost_usd")
            if cost_s is not None:
                lines.append(f"- **Cost:** ${cost_s:.5f}")
            sub_qs = sample.get("sub_queries") or []
            thoughts = sample.get("thoughts") or []
            for j, sq in enumerate(sub_qs):
                if not sq:
                    continue
                lines.append(f"  Round {j+1}: retrieve(\"{sq[:200]}\")")
                if j < len(thoughts) and thoughts[j]:
                    lines.append(f"    thought: {thoughts[j][:200]}")
            draft = sample.get("draft_answer")
            if draft:
                lines.append(f"  Final draft answer: {draft[:300]}")
            lines.append("")

    # Ship recommendation
    lines.append("## Ship recommendation")
    lines.append("")
    if pass_count >= 4:
        lines.append(
            "**SHIP DEFAULT candidate** — IterB clears all 4 gates. F_MH "
            "ceiling broken. Validate with Q1 full implementation (5-batch "
            "+ 95% CI + composability stacking on Wave A/B/C)."
        )
    elif pass_count >= 3:
        lines.append(
            "**SHIP OPT-IN** with `NOX_ADAPTER_MODE=phaseIterB` or "
            "`NOX_ITERB_ENABLED=1`. Canonical F_MH ceiling break "
            "CONFIRMED at orchestrator-stage. Default switch deferred to "
            "Q1 full implementation."
        )
    elif pass_count == 2:
        lines.append(
            "**DOCUMENT + DEFER.** Mechanism shows partial wins; full gate "
            "not met. Inspect Set E (rounds + overlap + termination "
            "distribution) to decide whether prompt + termination tweaks "
            "could close the remaining gap before re-running."
        )
    elif pass_count == 1:
        lines.append(
            "**DOCUMENT + DEFER.** Single-gate win — insufficient to ship. "
            "ReAct mechanism works but doesn't cleanly break F_MH ceiling. "
            "Document insight; defer further work to Q1 cycle."
        )
    else:
        lines.append(
            "**REJECT — Wave A/B/C F_MH ceiling HOLDS.** 0/4 gates pass. "
            "Orchestration-stage hypothesis dead for EverMemBench shape. "
            "F_MH gap vs MemOS is structural to EverMemBench (per D72 "
            "reframe). Close Q3 IterB; document for paper."
        )
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--runs-dir", required=True, type=Path)
    p.add_argument("--pattern", default="phaseIterB-*")
    p.add_argument("--output-md", required=True, type=Path)
    p.add_argument("--output-json", required=True, type=Path)
    args = p.parse_args()

    payload = aggregate_runs(args.runs_dir, args.pattern)
    args.output_json.write_text(json.dumps(payload, indent=2, default=str))
    args.output_md.write_text(render_markdown(payload))
    print(f"[iterb-agg] wrote {args.output_md}")
    print(f"[iterb-agg] wrote {args.output_json}")
    print(f"[iterb-agg] verdict: {payload['gates'].get('verdict')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
