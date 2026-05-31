#!/usr/bin/env python3
"""Wave 2 Capstone — IterB + Wave C Triple aggregation.

Reads results-batch-*.json + search-results-batch-*.json + analysis.txt from
each run-dir and produces:
  - RESULTS-CAPSTONE-ITERB-TRIPLE-GEMINI3FLASH.json
  - RESULTS-CAPSTONE-ITERB-TRIPLE-GEMINI3FLASH.md

Gates (per spec):
  - F_MH lift >= +1.5pp over IterB-alone (8.03%) = SHIP_DEFAULT_CANDIDATE
  - F_MH lift >= +1pp but <+1.5pp = SHIP_OPT_IN
  - F_MH <+1pp = CLOSED (orchestration ceiling structural)
"""
import argparse
import json
import math
import os
import sys
from pathlib import Path
from statistics import mean, stdev

# Baselines (from prior PRs)
ITERB_ALONE = {
    "overall": 62.70, "f_mh": 8.03, "f_sh": 76.61, "f_tp": 33.33, "f_hl": 43.06,
    "ma_composite": 84.89, "cost_per_q": 0.00295, "source": "PR #419 D74"
}
BARE = {
    "overall": 63.28, "f_mh": 6.02, "ma_composite": 88.42, "source": "PR #397 D70"
}
MEMOS = {"overall": 42.55, "f_mh": 3.21, "source": "MemOS Table 4"}

def parse_analysis(path):
    """Parse analysis.txt from a single batch."""
    data = {}
    if not path.exists():
        return data
    text = path.read_text()
    for line in text.splitlines():
        line = line.strip()
        # Expect lines like:
        # "Combined: 51.21%" or "Overall: 62.70%" or "F_MH: 8.03%"
        if ":" in line and "%" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().rstrip("%")
            try:
                data[key] = float(val)
            except ValueError:
                pass
    return data

def aggregate_search(search_path):
    """Extract Set E IterB metadata from search_results."""
    if not search_path.exists():
        return {}
    with open(search_path) as f:
        d = json.load(f)
    results = d if isinstance(d, list) else d.get("results", [])
    iterb_applied = 0
    iterb_rounds_total = []
    iterb_term_reasons = {}
    iterb_cost_total = 0.0
    iterb_total_latency = []
    kg_applied = 0
    rerank_applied = 0
    map_applied = 0
    overlap_vals = []
    for r in results:
        m = r.get("metadata", {})
        if m.get("iterb_applied"):
            iterb_applied += 1
            iterb_rounds_total.append(m.get("iterb_rounds_executed", 0))
            tr = m.get("iterb_termination_reason") or "unknown"
            iterb_term_reasons[tr] = iterb_term_reasons.get(tr, 0) + 1
            cost = m.get("iterb_total_cost_usd") or 0
            iterb_cost_total += float(cost)
            # Round-2 overlap (mean)
            ovs = m.get("iterb_per_round_overlap_with_prior") or []
            if len(ovs) >= 2:
                overlap_vals.append(ovs[1])
        if m.get("kg_applied"):
            kg_applied += 1
        if m.get("rerank_applied"):
            rerank_applied += 1
        if m.get("ma_protection_applied"):
            map_applied += 1
        sd = r.get("search_duration_ms") or 0
        iterb_total_latency.append(float(sd))
    n = len(results)
    return {
        "n": n,
        "iterb_applied_pct": (iterb_applied / max(1, n)) * 100,
        "iterb_mean_rounds": (mean(iterb_rounds_total) if iterb_rounds_total else 0),
        "iterb_term_reasons": iterb_term_reasons,
        "iterb_total_cost_usd": iterb_cost_total,
        "iterb_cost_per_q": iterb_cost_total / max(1, n),
        "kg_applied_pct": (kg_applied / max(1, n)) * 100,
        "rerank_applied_pct": (rerank_applied / max(1, n)) * 100,
        "map_applied_pct": (map_applied / max(1, n)) * 100,
        "round2_overlap_mean": (mean(overlap_vals) if overlap_vals else None),
        "search_latency_p50_ms": (sorted(iterb_total_latency)[len(iterb_total_latency)//2] if iterb_total_latency else 0),
        "search_latency_p95_ms": (sorted(iterb_total_latency)[int(len(iterb_total_latency)*0.95)] if iterb_total_latency else 0),
    }

def ci_95(values):
    if len(values) < 2:
        return (0, 0)
    m = mean(values)
    s = stdev(values)
    se = s / math.sqrt(len(values))
    return (m - 1.96*se, m + 1.96*se)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--runs-dir", default="/root/.openclaw/evermembench-runs")
    p.add_argument("--pattern", default="capstone-iterB-triple-*")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    runs = sorted(Path(args.runs_dir).glob(args.pattern))
    batches = {}
    for run in runs:
        # Extract batch from name like capstone-iterB-triple-004-1780260019
        parts = run.name.split("-")
        batch = None
        for token in parts:
            if token.isdigit() and len(token) == 3:
                batch = token
                break
        if not batch:
            continue
        anal = parse_analysis(run / "analysis.txt")
        if not anal:
            continue
        search_meta = aggregate_search(run / f"search-results-batch-{batch}.json")
        batches[batch] = {
            "run_dir": str(run),
            "analysis": anal,
            "search_meta": search_meta,
        }

    if not batches:
        print("No batches found.")
        sys.exit(1)

    # Aggregate metrics across batches
    metrics_keys = ["Combined", "Overall", "F_MH", "F_SH", "F_TP", "F_HL", "MA_C", "MA_P", "MA_U"]
    agg = {}
    for k in metrics_keys:
        vals = [b["analysis"].get(k) for b in batches.values() if b["analysis"].get(k) is not None]
        if vals:
            agg[k] = {"mean": mean(vals), "ci_lo": ci_95(vals)[0], "ci_hi": ci_95(vals)[1], "vals": vals}

    # MA composite = (MA_C + MA_P + MA_U) / 3
    ma_composites = []
    for b in batches.values():
        an = b["analysis"]
        parts = [an.get("MA_C"), an.get("MA_P"), an.get("MA_U")]
        if all(p is not None for p in parts):
            ma_composites.append(mean(parts))
    if ma_composites:
        agg["MA_composite"] = {
            "mean": mean(ma_composites),
            "ci_lo": ci_95(ma_composites)[0],
            "ci_hi": ci_95(ma_composites)[1],
            "vals": ma_composites,
        }

    # Aggregate Set E
    total_n = sum(b["search_meta"].get("n", 0) for b in batches.values())
    total_iterb_cost = sum(b["search_meta"].get("iterb_total_cost_usd", 0) for b in batches.values())
    overall_iterb_applied = mean([b["search_meta"].get("iterb_applied_pct", 0) for b in batches.values()])
    overall_kg_applied = mean([b["search_meta"].get("kg_applied_pct", 0) for b in batches.values()])
    overall_rerank_applied = mean([b["search_meta"].get("rerank_applied_pct", 0) for b in batches.values()])
    overall_map_applied = mean([b["search_meta"].get("map_applied_pct", 0) for b in batches.values()])
    overall_mean_rounds = mean([b["search_meta"].get("iterb_mean_rounds", 0) for b in batches.values()])

    # Gate verdict
    f_mh = agg.get("F_MH", {}).get("mean", 0)
    f_mh_delta_iterb = f_mh - ITERB_ALONE["f_mh"]
    f_mh_delta_bare = f_mh - BARE["f_mh"]

    if f_mh_delta_iterb >= 1.5:
        verdict = "SHIP_DEFAULT_CANDIDATE"
    elif f_mh_delta_iterb >= 1.0:
        verdict = "SHIP_OPT_IN"
    elif f_mh_delta_iterb >= 0:
        verdict = "CLOSED_NO_GAIN"
    else:
        verdict = "INTERFERENCE"

    # Build report
    out = {
        "spec": "Wave 2 Phase 2 Capstone — IterB ReAct + Wave C Triple Gemini-3-flash",
        "config": {
            "backbone_answer": "gemini-3-flash-preview",
            "orchestrator": "gemini-2.5-flash-lite",
            "judge": "gemini-2.5-flash",
            "mode": "phaseTriple + NOX_ITERB_ENABLED=1 (patched: removed iterb_used_path guards)",
            "batches": list(batches.keys()),
            "n_total": total_n,
        },
        "metrics_5batch": agg,
        "set_e_iterb_instrumentation": {
            "iterb_applied_pct_mean": overall_iterb_applied,
            "iterb_mean_rounds_overall": overall_mean_rounds,
            "iterb_total_cost_usd": total_iterb_cost,
            "iterb_cost_per_q_mean": total_iterb_cost / max(1, total_n),
            "kg_applied_pct_mean": overall_kg_applied,
            "rerank_applied_pct_mean": overall_rerank_applied,
            "ma_protection_applied_pct_mean": overall_map_applied,
        },
        "baselines": {
            "iterb_alone_PR419": ITERB_ALONE,
            "bare_gemini3_PR397": BARE,
            "memos_table4": MEMOS,
        },
        "deltas_vs_iterb_alone": {
            "f_mh_delta_pp": f_mh_delta_iterb,
            "overall_delta_pp": agg.get("Overall", {}).get("mean", 0) - ITERB_ALONE["overall"],
            "ma_composite_delta_pp": agg.get("MA_composite", {}).get("mean", 0) - ITERB_ALONE["ma_composite"],
        },
        "deltas_vs_bare": {
            "f_mh_delta_pp": f_mh_delta_bare,
            "overall_delta_pp": agg.get("Overall", {}).get("mean", 0) - BARE["overall"],
            "ma_composite_delta_pp": agg.get("MA_composite", {}).get("mean", 0) - BARE["ma_composite"],
        },
        "verdict": verdict,
        "per_batch": {b: {"analysis": batches[b]["analysis"], "set_e": batches[b]["search_meta"]} for b in batches},
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"Wrote: {out_path}")
    print(f"VERDICT: {verdict}  F_MH {f_mh:.2f}%  delta vs IterB-alone {f_mh_delta_iterb:+.2f}pp  delta vs bare {f_mh_delta_bare:+.2f}pp")
    print(f"Cost: ${total_iterb_cost:.2f}")

if __name__ == "__main__":
    main()
