#!/usr/bin/env python3
"""
Backbone Matrix bench — 5-batch aggregator + cross-backbone comparison (2026-05-29).

Reads per-backbone run directories under /root/.openclaw/evermembench-runs/
matching the pattern backbone-matrix-<slug>-<batch>-<ts>/results-batch-<batch>.json,
plus existing Phase H v2 runs (gpt-4.1-mini baseline) for the matrix entry.

Outputs:
  - Per-backbone 5-batch table (Overall, F_*, MA_*, P_*) with mean / stdev / 95% CI
  - F_MH gap closure vs MemOS 18.88%
  - Cross-backbone comparison verdict (4-gate per backbone)
  - JSON dump + markdown summary

Usage:
  python aggregate_backbone_matrix.py [--json <out.json>] [--md <out.md>]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# MemOS GPT-4.1-mini Table 4 (arxiv 2602.01313) — comparison anchor
MEMOS_GPT41MINI = {
    "Overall": 42.55,
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

# Phase H v2 baseline (gpt-4.1-mini, 5-batch, from PR #377)
PHASE_H_V2_BASELINE = {
    "Overall": 51.68,
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

# Approx cost per 1k tokens (USD, 2026-05-29) — rough public pricing
COST_PER_1K_TOKENS = {
    "gpt-4.1-mini": {"in": 0.0004, "out": 0.0016},
    "gpt-5":        {"in": 0.00125, "out": 0.010},
    "gpt-5-mini":   {"in": 0.00025, "out": 0.002},
    "gemini-3-flash-preview": {"in": 0.0003, "out": 0.0025},
    "gemini-2.5-pro": {"in": 0.00125, "out": 0.005},
    "gemini-3.1-flash-lite-preview": {"in": 0.0001, "out": 0.0004},
}

RUNS_ROOT = Path("/root/.openclaw/evermembench-runs")

# Slug -> canonical backbone name
SLUG_TO_BACKBONE = {
    "gpt5": "gpt-5",
    "gpt5-mini": "gpt-5-mini",
    "gemini3flash": "gemini-3-flash-preview",
    "gemini31flashlite": "gemini-3.1-flash-lite-preview",
    "gemini25pro": "gemini-2.5-pro",
    "gpt41mini": "gpt-4.1-mini",
}

# Question-id prefix -> dimension category
def classify_question_id(qid: str) -> Optional[str]:
    # Examples: "MA_C_Top005_001", "F_MH_005_023", "P_Style_010_001"
    m = re.match(r"^(F|MA|P)_([A-Z]+[A-Za-z]*)", qid)
    if not m:
        return None
    major, minor = m.group(1), m.group(2)
    return f"{major}_{minor}"


def aggregate_one_batch(results_file: Path) -> Dict[str, Dict[str, int]]:
    """Return {dimension: {total, correct}} from a single batch results JSON."""
    with results_file.open() as f:
        d = json.load(f)
    by_dim = defaultdict(lambda: {"total": 0, "correct": 0})
    for item in d.get("detailed_results", []):
        qid = item.get("question_id", "")
        dim = classify_question_id(qid)
        if not dim:
            continue
        by_dim[dim]["total"] += 1
        if item.get("is_correct"):
            by_dim[dim]["correct"] += 1
    # Overall
    by_dim["Overall"]["total"] = d.get("total_questions", 0)
    by_dim["Overall"]["correct"] = d.get("correct", 0)
    return dict(by_dim)


def discover_backbone_runs(slug: str) -> Dict[str, Path]:
    """Map batch -> results JSON file for the given backbone slug. Picks newest TS per batch."""
    pattern = f"backbone-matrix-{slug}-*"
    candidates = sorted(RUNS_ROOT.glob(pattern))
    out: Dict[str, Path] = {}
    for d in candidates:
        # extract batch
        # name: backbone-matrix-<slug>-<batch>-<ts>
        parts = d.name.split("-")
        # slug may contain dash (gpt5-mini, gemini3flash), batch is always 3-digit numeric
        # Find the 3-digit batch token
        batch = None
        for tok in parts:
            if re.fullmatch(r"\d{3}", tok):
                batch = tok
                break
        if not batch:
            continue
        rf = d / f"results-batch-{batch}.json"
        if rf.is_file():
            # Newer dirs overwrite older
            out[batch] = rf
    return out


def discover_phaseH_v2_runs() -> Dict[str, Path]:
    """Find the existing Phase H v2 5-batch runs (gpt-4.1-mini baseline)."""
    out: Dict[str, Path] = {}
    for d in sorted(RUNS_ROOT.glob("phaseH-v2-*")):
        parts = d.name.split("-")
        batch = None
        for tok in parts:
            if re.fullmatch(r"\d{3}", tok):
                batch = tok
                break
        if not batch:
            continue
        rf = d / f"results-batch-{batch}.json"
        if rf.is_file():
            out[batch] = rf
    return out


def pct(c: int, t: int) -> float:
    return (c / t * 100.0) if t > 0 else float("nan")


def t_dist_ci(values: List[float], confidence: float = 0.95) -> Tuple[float, float]:
    """Two-sided 95% CI using t-distribution (n=5, dof=4 -> t=2.776)."""
    if len(values) < 2:
        return (float("nan"), float("nan"))
    mean = statistics.mean(values)
    stdev = statistics.stdev(values)
    n = len(values)
    se = stdev / (n ** 0.5)
    # t-critical for dof=n-1 at 95% two-sided: hardcoded table
    t_crit = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262}.get(n - 1, 1.96)
    half = t_crit * se
    return (mean - half, mean + half)


def compute_backbone_metrics(batches_map: Dict[str, Path]) -> Dict:
    """Aggregate per-batch accuracies into per-dim {batches: [...], weighted, stats}."""
    if not batches_map:
        return {}
    per_batch: Dict[str, Dict[str, Dict[str, int]]] = {}
    for batch, rf in sorted(batches_map.items()):
        per_batch[batch] = aggregate_one_batch(rf)

    dims = set()
    for b in per_batch.values():
        dims.update(b.keys())

    out: Dict[str, Dict] = {}
    for dim in sorted(dims):
        per_batch_pcts = []
        sum_total = 0
        sum_correct = 0
        per_batch_detail = {}
        for batch in sorted(per_batch.keys()):
            ct = per_batch[batch].get(dim, {"total": 0, "correct": 0})
            t, c = ct["total"], ct["correct"]
            if t > 0:
                per_batch_pcts.append(pct(c, t))
                per_batch_detail[batch] = {"total": t, "correct": c, "pct": pct(c, t)}
                sum_total += t
                sum_correct += c
        if sum_total == 0:
            continue
        weighted = pct(sum_correct, sum_total)
        if len(per_batch_pcts) >= 2:
            mean = statistics.mean(per_batch_pcts)
            stdev = statistics.stdev(per_batch_pcts)
            ci_lo, ci_hi = t_dist_ci(per_batch_pcts)
        else:
            mean = per_batch_pcts[0] if per_batch_pcts else float("nan")
            stdev = float("nan")
            ci_lo, ci_hi = float("nan"), float("nan")
        out[dim] = {
            "per_batch": per_batch_detail,
            "weighted": weighted,
            "mean": mean,
            "stdev": stdev,
            "ci95_lo": ci_lo,
            "ci95_hi": ci_hi,
            "n_batches": len(per_batch_pcts),
            "sum_total": sum_total,
            "sum_correct": sum_correct,
        }
    return out


def gate_verdict(metrics: Dict, backbone: str) -> Dict:
    """4-gate per backbone evaluation."""
    gates = {}

    # Gate 1: F_MH lift >= +5pp vs Phase H v2 baseline 3.21% (target F_MH >= 8.21%)
    fmh = metrics.get("F_MH", {}).get("weighted", float("nan"))
    gates["gate1_F_MH_lift_5pp"] = {
        "metric": "F_MH",
        "value": fmh,
        "target": 8.21,
        "baseline": PHASE_H_V2_BASELINE["F_MH"],
        "delta_vs_baseline_pp": fmh - PHASE_H_V2_BASELINE["F_MH"] if fmh == fmh else float("nan"),
        "pass": (fmh >= 8.21) if fmh == fmh else False,
    }

    # Gate 2: Overall preservation >= baseline - 0.5pp = 51.18
    overall = metrics.get("Overall", {}).get("weighted", float("nan"))
    gates["gate2_overall_preserve"] = {
        "metric": "Overall",
        "value": overall,
        "target": PHASE_H_V2_BASELINE["Overall"] - 0.5,
        "pass": (overall >= PHASE_H_V2_BASELINE["Overall"] - 0.5) if overall == overall else False,
    }

    # Gate 3: MA composite >= baseline - 1pp = 72.34
    # MA composite = unweighted mean of MA_C, MA_P, MA_U
    ma_c = metrics.get("MA_C", {}).get("weighted", float("nan"))
    ma_p = metrics.get("MA_P", {}).get("weighted", float("nan"))
    ma_u = metrics.get("MA_U", {}).get("weighted", float("nan"))
    if all(v == v for v in [ma_c, ma_p, ma_u]):
        ma_comp = (ma_c + ma_p + ma_u) / 3.0
    else:
        ma_comp = float("nan")
    ma_baseline = (PHASE_H_V2_BASELINE["MA_C"] + PHASE_H_V2_BASELINE["MA_P"] + PHASE_H_V2_BASELINE["MA_U"]) / 3.0
    gates["gate3_MA_composite_preserve"] = {
        "metric": "MA_composite",
        "value": ma_comp,
        "target": ma_baseline - 1.0,
        "pass": (ma_comp >= ma_baseline - 1.0) if ma_comp == ma_comp else False,
    }

    # Gate 4: Cost ratio <= 5x gpt-4.1-mini baseline ($4.56 total for 5-batch / 0.92 per batch)
    # Compute from approx pricing if backbone known
    pricing = COST_PER_1K_TOKENS.get(backbone, None)
    baseline_pricing = COST_PER_1K_TOKENS["gpt-4.1-mini"]
    if pricing is not None:
        # Use input-token-weighted heuristic (3:1 input:output observed in Phase H v2)
        # cost = 3 * in + 1 * out per 4 tokens basis
        cost_unit = 3 * pricing["in"] + 1 * pricing["out"]
        base_unit = 3 * baseline_pricing["in"] + 1 * baseline_pricing["out"]
        ratio = cost_unit / base_unit
    else:
        ratio = float("nan")
    gates["gate4_cost_ratio_<=5x"] = {
        "metric": "cost_ratio_vs_baseline",
        "value": ratio,
        "target": 5.0,
        "pass": (ratio <= 5.0) if ratio == ratio else None,
    }

    passes = sum(1 for g in gates.values() if g.get("pass") is True)
    gates["summary"] = {
        "passes": passes,
        "total": 4,
        "recommendation": (
            "ship_primary" if passes == 4
            else "ship_opt_in" if passes == 3
            else "reject_skip"
        ),
    }
    return gates


def f_mh_gap_closure_pct(fmh: float) -> float:
    """Percentage of MemOS F_MH 18.88pp closed (vs Phase H v2 baseline 3.21%)."""
    if fmh != fmh:
        return float("nan")
    gap_initial = MEMOS_GPT41MINI["F_MH"] - PHASE_H_V2_BASELINE["F_MH"]  # 18.88 - 3.21 = 15.67pp
    closed = fmh - PHASE_H_V2_BASELINE["F_MH"]  # positive if we improved
    return (closed / gap_initial) * 100.0 if gap_initial != 0 else float("nan")


def format_pct(v: float, prec: int = 2) -> str:
    return f"{v:.{prec}f}%" if v == v else "n/a"


def format_signed(v: float, prec: int = 2) -> str:
    return f"{v:+.{prec}f}" if v == v else "n/a"


def render_markdown(results: Dict[str, Dict], out_path: Path) -> None:
    lines: List[str] = []
    lines.append("# Backbone Matrix — Cross-Backbone SOTA F_MH Gap Closure (2026-05-29)")
    lines.append("")
    lines.append("> **Date:** 2026-05-29")
    lines.append("> **Methodology:** Phase H v2 baseline (pre-warmed Phase B DBs, top_k=20, rerank OFF, adapter=phaseB).")
    lines.append("> **Only the answer backbone changes between matrix entries.** Judge stays on gemini-2.5-flash.")
    lines.append("> **Anchor:** MemOS GPT-4.1-mini (arxiv 2602.01313 Table 4) — Overall 42.55%, F_MH 18.88%.")
    lines.append("> **Baseline:** nox-mem Phase H v2 5-batch gpt-4.1-mini (PR #377) — Overall 51.68%, F_MH 3.21%.")
    lines.append("")
    lines.append("---")
    lines.append("")

    backbones = list(results.keys())

    # Headline
    lines.append("## Headline")
    lines.append("")
    lines.append("| Backbone | Overall | F_MH | F_MH lift vs baseline | F_MH closure of MemOS gap | MA composite | 4-gate pass | Verdict |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---|")
    for bb, payload in results.items():
        m = payload.get("metrics", {})
        gates = payload.get("gates", {})
        overall = m.get("Overall", {}).get("weighted", float("nan"))
        fmh = m.get("F_MH", {}).get("weighted", float("nan"))
        delta = gates.get("gate1_F_MH_lift_5pp", {}).get("delta_vs_baseline_pp", float("nan"))
        closure = f_mh_gap_closure_pct(fmh)
        ma_c = m.get("MA_C", {}).get("weighted", float("nan"))
        ma_p = m.get("MA_P", {}).get("weighted", float("nan"))
        ma_u = m.get("MA_U", {}).get("weighted", float("nan"))
        if all(v == v for v in [ma_c, ma_p, ma_u]):
            ma_comp = (ma_c + ma_p + ma_u) / 3.0
        else:
            ma_comp = float("nan")
        passes = gates.get("summary", {}).get("passes", 0)
        rec = gates.get("summary", {}).get("recommendation", "n/a")
        lines.append(
            f"| **{bb}** | {format_pct(overall)} | {format_pct(fmh)} | {format_signed(delta)}pp | "
            f"{format_pct(closure, 1)} | {format_pct(ma_comp)} | {passes}/4 | {rec} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")

    # Per-backbone detail
    for bb, payload in results.items():
        m = payload.get("metrics", {})
        gates = payload.get("gates", {})
        n_batches = m.get("Overall", {}).get("n_batches", 0)
        sum_total = m.get("Overall", {}).get("sum_total", 0)

        lines.append(f"## {bb} — {n_batches}-batch (n={sum_total})")
        lines.append("")

        # Per-dim table
        lines.append("### Per-dimension breakdown")
        lines.append("")
        lines.append("| dimension | n_batches | sum_total | sum_correct | weighted | mean | stdev | 95% CI |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---|")
        prio = ["Overall", "F_SH", "F_MH", "F_TP", "F_HL", "MA_C", "MA_P", "MA_U", "P_Style", "P_Skill", "P_Title"]
        seen = set()
        for dim in prio:
            if dim in m:
                seen.add(dim)
                d = m[dim]
                ci_str = f"{d['ci95_lo']:.2f}–{d['ci95_hi']:.2f}%" if d['ci95_lo'] == d['ci95_lo'] else "n/a"
                stdev_str = f"{d['stdev']:.2f}pp" if d['stdev'] == d['stdev'] else "n/a"
                lines.append(
                    f"| {dim} | {d['n_batches']} | {d['sum_total']} | {d['sum_correct']} | "
                    f"**{format_pct(d['weighted'])}** | {format_pct(d['mean'])} | {stdev_str} | {ci_str} |"
                )
        for dim in sorted(set(m.keys()) - seen):
            d = m[dim]
            ci_str = f"{d['ci95_lo']:.2f}–{d['ci95_hi']:.2f}%" if d['ci95_lo'] == d['ci95_lo'] else "n/a"
            stdev_str = f"{d['stdev']:.2f}pp" if d['stdev'] == d['stdev'] else "n/a"
            lines.append(
                f"| {dim} | {d['n_batches']} | {d['sum_total']} | {d['sum_correct']} | "
                f"**{format_pct(d['weighted'])}** | {format_pct(d['mean'])} | {stdev_str} | {ci_str} |"
            )
        lines.append("")

        # Gates
        lines.append("### 4-gate verdict")
        lines.append("")
        for gname, gpayload in gates.items():
            if gname == "summary":
                continue
            pass_mark = "PASS" if gpayload.get("pass") is True else ("FAIL" if gpayload.get("pass") is False else "n/a")
            val_str = (
                f"{gpayload['value']:.3f}" if isinstance(gpayload.get("value"), float) and gpayload['value'] == gpayload['value']
                else "n/a"
            )
            tgt_str = (
                f"{gpayload['target']:.3f}" if isinstance(gpayload.get("target"), float) and gpayload['target'] == gpayload['target']
                else "n/a"
            )
            lines.append(f"- **{gname}**: {pass_mark} (value={val_str}, target={tgt_str})")
        summary = gates.get("summary", {})
        lines.append(f"- **Total: {summary.get('passes', 0)}/{summary.get('total', 4)} gates pass — {summary.get('recommendation', 'n/a')}**")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Verdict + recommendation
    lines.append("## Verdict")
    lines.append("")
    # Find best F_MH backbone
    best_bb = None
    best_fmh = -1.0
    for bb, payload in results.items():
        fmh = payload.get("metrics", {}).get("F_MH", {}).get("weighted", -1)
        if fmh == fmh and fmh > best_fmh:
            best_fmh = fmh
            best_bb = bb
    lines.append(f"**Best F_MH backbone:** {best_bb} (F_MH={format_pct(best_fmh)})")
    lines.append("")
    lines.append("**MemOS gap closure ranking (F_MH):**")
    sorted_by_closure = sorted(
        results.items(),
        key=lambda kv: kv[1].get("metrics", {}).get("F_MH", {}).get("weighted", -1),
        reverse=True,
    )
    for bb, payload in sorted_by_closure:
        fmh = payload.get("metrics", {}).get("F_MH", {}).get("weighted", float("nan"))
        closure = f_mh_gap_closure_pct(fmh)
        lines.append(f"- {bb}: F_MH={format_pct(fmh)}, closure={format_pct(closure, 1)} of MemOS 18.88%")
    lines.append("")

    out_path.write_text("\n".join(lines))
    print(f"[aggregate] markdown -> {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="eval/evermembench/RESULTS-BACKBONE-MATRIX.json")
    ap.add_argument("--md", default="eval/evermembench/RESULTS-BACKBONE-MATRIX.md")
    ap.add_argument("--include-phaseH-v2", action="store_true", default=True,
                    help="Include existing Phase H v2 gpt-4.1-mini 5-batch as 'gpt-4.1-mini' entry (baseline)")
    args = ap.parse_args()

    results: Dict[str, Dict] = {}

    # 1) gpt-4.1-mini baseline (Phase H v2 5-batch)
    if args.include_phaseH_v2:
        ph_runs = discover_phaseH_v2_runs()
        if ph_runs:
            metrics = compute_backbone_metrics(ph_runs)
            gates = gate_verdict(metrics, "gpt-4.1-mini")
            results["gpt-4.1-mini"] = {
                "source": "PR-377-phaseH-v2-5-batch",
                "batches": list(ph_runs.keys()),
                "metrics": metrics,
                "gates": gates,
            }
            print(f"[aggregate] gpt-4.1-mini (baseline) — {len(ph_runs)} batches discovered")

    # 2) Each backbone slug
    for slug, bb in SLUG_TO_BACKBONE.items():
        if bb == "gpt-4.1-mini":
            continue  # already loaded as baseline
        runs = discover_backbone_runs(slug)
        if not runs:
            print(f"[aggregate] no runs found for {bb} (slug={slug}) — skipping")
            continue
        metrics = compute_backbone_metrics(runs)
        gates = gate_verdict(metrics, bb)
        results[bb] = {
            "source": f"backbone-matrix-{slug}-*",
            "batches": list(runs.keys()),
            "metrics": metrics,
            "gates": gates,
        }
        print(f"[aggregate] {bb} — {len(runs)} batches discovered")

    out_json = Path(args.json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps({"backbones": results, "memos_anchor": MEMOS_GPT41MINI, "baseline_phaseH_v2": PHASE_H_V2_BASELINE}, indent=2))
    print(f"[aggregate] json -> {out_json}")

    render_markdown(results, Path(args.md))


if __name__ == "__main__":
    main()
