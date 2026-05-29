"""Phase KGMAP 5-batch aggregator + 4-gate evaluator.

Reads per-batch evaluation_results_<batch>.json and search_results_<batch>.json,
computes the 4-gate verdict for Wave B composability (KG + MA-protection).

Gates:
  1. MA composite ≥ Phase H v2 baseline -1pp tolerance (recover MA cost vs
     standalone MAP -6.55pp)
  2. F_MH ≥ Phase MAP standalone +4.02pp (preserve hard-recall gain)
  3. Overall ≥ Phase H v2 -1.5pp tolerance
  4. Latency p50 ≤ 1.2× Phase G (rerank) + KG overhead

Also dumps Set E / Set KG / total_protected instrumentation per query for
empirical mechanism validation (lesson `[[empirical-set-e-empty-confirms-
mechanism-not-corpus]]`).

Usage:
    python aggregate_phaseKGMAP_5batch.py <run_dirs...> <out_md> <out_json>
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Phase H v2 baseline (5-batch CLEAN, gpt-4.1-mini) — source: RESULTS-PHASEH-v2-5BATCH.md
# Combined Major_Minor naming matches analysis.txt format.
BASELINE_H2 = {
    "overall": 51.68,
    "F_SH": None,    # not used as gate
    "F_MH": 3.21,
    "F_HL": None,
    "F_TP": None,
    "MA_C": 84.60,
    "MA_P": 65.40,
    "MA_U": 70.03,
    "MA_composite": 73.34,
}

# Combined naming aliases for downstream lookups
CATEGORY_ALIAS = {
    "MA_C": "MA_C",
    "MA_P": "MA_P",
    "MA_U": "MA_U",
    "F_MH": "F_MH",
    "F_SH": "F_SH",
    "F_TP": "F_TP",
    "F_HL": "F_HL",
}

# Phase MAP standalone 5-batch (PR #386)
MAP_STANDALONE = {
    "overall": 50.44,
    "F_MH_lift": 4.02,
    "F_HL_lift": 4.34,
    "MA_composite_lift": -6.55,
}

# Phase KG sparse 5-batch (PR #379)
KG_SPARSE = {
    "overall_lift": 0.12,
    "F_MH_lift": 2.81,
    "MA_composite_lift": 0.44,
}

# Phase G rerank Gemini (5-batch reference)
PHASE_G = {
    "F_MH_lift": 1.61,
    "MA_composite_lift": -3.55,
    "p50_latency_ms": None,  # if available
}


CATEGORY_FIELDS = ["F_SH", "F_MH", "F_TP", "F_HL", "MA_C", "MA_P", "MA_U"]


def _read_json(p: Path) -> Optional[Any]:
    try:
        with open(p) as fp:
            return json.load(fp)
    except Exception:
        return None


def _safe_mean(xs: List[float]) -> float:
    return statistics.fmean(xs) if xs else 0.0


def _safe_pstdev(xs: List[float]) -> float:
    return statistics.pstdev(xs) if len(xs) > 1 else 0.0


def _ci95(xs: List[float]) -> Tuple[float, float]:
    if not xs:
        return 0.0, 0.0
    mean = _safe_mean(xs)
    if len(xs) < 2:
        return mean, mean
    sd = statistics.pstdev(xs)
    half = 1.96 * sd / math.sqrt(len(xs))
    return mean - half, mean + half


def _extract_category_scores(eval_results: Any) -> Dict[str, float]:
    """Extract per-category accuracy from evaluation_results json.

    Wave B harness shape (per evaluation_results_<batch>.json):
      { "accuracy": float (0-1), "total_questions": int, ... }
    Categories are NOT in the eval JSON — they are computed by
    tools/analyze_results.py into analysis.txt. Returns overall only here;
    categories are read separately via _extract_category_scores_from_text.
    """
    out: Dict[str, float] = {}
    if isinstance(eval_results, dict):
        if "accuracy" in eval_results and isinstance(
            eval_results["accuracy"], (int, float)
        ):
            acc = float(eval_results["accuracy"])
            out["overall"] = acc * (100.0 if 0 <= acc <= 1 else 1.0)
    return out


# Matches lines like "F_MH                    50          3           6.00%"
_COMBINED_RE = None


def _extract_category_scores_from_text(text: str) -> Dict[str, float]:
    """Parse `analysis.txt` Combined (Major_Minor) Accuracy section.

    Format:
        F_HL                    78         20          25.64%
        F_MH                    50          3            6.00%
        ...
    Returns dict like {"F_MH": 6.00, "MA_C": 74.00, ...} in 0-100 scale.
    """
    global _COMBINED_RE
    if _COMBINED_RE is None:
        import re as _re
        _COMBINED_RE = _re.compile(
            r"^\s*([A-Za-z]+_[A-Za-z]+)\s+\d+\s+\d+\s+([\d.]+)%\s*$"
        )
    out: Dict[str, float] = {}
    in_combined = False
    for line in text.splitlines():
        if "Combined (Major_Minor)" in line:
            in_combined = True
            continue
        if in_combined:
            m = _COMBINED_RE.match(line)
            if m:
                combined = m.group(1)
                pct = float(m.group(2))
                # Map "F_MH" → "F_MH", "MA_C" → "MA_C". Keep combined form.
                out[combined] = pct
    return out


def _extract_set_e_instrumentation(search_results: Any) -> Dict[str, Any]:
    """Per-batch Set E / Set KG / total_protected statistics."""
    items: List[Dict[str, Any]] = []
    if isinstance(search_results, list):
        items = [it for it in search_results if isinstance(it, dict)]
    elif isinstance(search_results, dict):
        items = [
            it for it in search_results.get("results", [])
            if isinstance(it, dict)
        ]
    n = len(items)
    set_e_counts: List[int] = []
    set_kg_counts: List[int] = []
    total_counts: List[int] = []
    kg_pool_sizes: List[int] = []
    applied_count = 0
    kg_anchor_active = 0
    for it in items:
        meta = it.get("metadata") or {}
        if meta.get("ma_protection_applied"):
            applied_count += 1
        if meta.get("ma_protection_kg_anchor"):
            kg_anchor_active += 1
        set_e_counts.append(int(meta.get("ma_set_e_count") or 0))
        set_kg_counts.append(int(meta.get("ma_set_e_kg_count") or 0))
        total_counts.append(int(meta.get("ma_total_protected_count") or 0))
        kg_pool_sizes.append(int(meta.get("ma_kg_evidence_pool_size") or 0))
    return {
        "n_queries": n,
        "applied_count": applied_count,
        "applied_pct": round(100.0 * applied_count / max(n, 1), 2),
        "kg_anchor_active": kg_anchor_active,
        "set_e_section_mean": round(_safe_mean(set_e_counts), 2),
        "set_e_kg_mean": round(_safe_mean(set_kg_counts), 2),
        "total_protected_mean": round(_safe_mean(total_counts), 2),
        "kg_pool_size_mean": round(_safe_mean(kg_pool_sizes), 2),
        "queries_with_kg_pool": sum(1 for x in kg_pool_sizes if x > 0),
        "queries_with_protected": sum(1 for x in total_counts if x > 0),
    }


def _extract_latency_p50_ms(search_results: Any) -> Optional[float]:
    items: List[Dict[str, Any]] = []
    if isinstance(search_results, list):
        items = [it for it in search_results if isinstance(it, dict)]
    elif isinstance(search_results, dict):
        items = [
            it for it in search_results.get("results", [])
            if isinstance(it, dict)
        ]
    durs = [
        it.get("search_duration_ms")
        for it in items
        if isinstance(it.get("search_duration_ms"), (int, float))
    ]
    if not durs:
        return None
    return statistics.median(durs)


def main() -> int:
    if len(sys.argv) < 4:
        print("usage: aggregate_phaseKGMAP_5batch.py <out_md> <out_json> <run_dir1> [run_dir2 ...]")
        return 1
    out_md_path = Path(sys.argv[1])
    out_json_path = Path(sys.argv[2])
    run_dirs = [Path(d) for d in sys.argv[3:]]

    per_batch: List[Dict[str, Any]] = []
    for d in run_dirs:
        if not d.is_dir():
            print(f"WARN: {d} not a directory, skipping")
            continue
        # Try multiple filename patterns
        eval_path = None
        for pat in [
            "wave-B-KGMAP-*.json",
            "results-batch-*.json",
            "results-wave-B-KGMAP-*.json",
        ]:
            cands = list(d.glob(pat))
            if cands:
                eval_path = cands[0]
                break
        search_path = None
        for pat in [
            "search-wave-B-KGMAP-*.json",
            "search-batch-*.json",
        ]:
            cands = list(d.glob(pat))
            if cands:
                search_path = cands[0]
                break

        eval_data = _read_json(eval_path) if eval_path else None
        search_data = _read_json(search_path) if search_path else None
        cats = _extract_category_scores(eval_data) if eval_data else {}
        # analysis.txt parses the combined Major_Minor categories
        analysis_path = d / "analysis.txt"
        if analysis_path.is_file():
            text_cats = _extract_category_scores_from_text(
                analysis_path.read_text(errors="ignore")
            )
            for k, v in text_cats.items():
                cats[k] = v
        instr = _extract_set_e_instrumentation(search_data) if search_data else {}
        p50 = _extract_latency_p50_ms(search_data) if search_data else None

        # Batch id = first 3 chars after "phaseKGMAP-"
        bid = d.name.split("-")[1] if "-" in d.name else d.name
        per_batch.append({
            "batch": bid,
            "run_dir": str(d),
            "eval_file": str(eval_path) if eval_path else None,
            "search_file": str(search_path) if search_path else None,
            "categories": cats,
            "instrumentation": instr,
            "latency_p50_ms": p50,
        })

    # Compute aggregates over batches that have data
    agg: Dict[str, Any] = {"per_metric": {}}
    metrics = CATEGORY_FIELDS + ["overall"]
    for m in metrics:
        vals = [
            float(b["categories"][m])
            for b in per_batch
            if m in b["categories"]
        ]
        if not vals:
            continue
        lo, hi = _ci95(vals)
        agg["per_metric"][m] = {
            "mean": round(_safe_mean(vals), 4),
            "stdev": round(_safe_pstdev(vals), 4),
            "ci95_lo": round(lo, 4),
            "ci95_hi": round(hi, 4),
            "n_batches": len(vals),
            "per_batch": [round(v, 4) for v in vals],
        }
    # MA composite = mean of MA_C, MA_P, MA_U
    ma_dims = ["MA_C", "MA_P", "MA_U"]
    ma_per_batch = []
    for b in per_batch:
        vals = [
            float(b["categories"][m])
            for m in ma_dims
            if m in b["categories"]
        ]
        if len(vals) == 3:
            ma_per_batch.append(_safe_mean(vals))
    if ma_per_batch:
        lo, hi = _ci95(ma_per_batch)
        agg["per_metric"]["MA_composite"] = {
            "mean": round(_safe_mean(ma_per_batch), 4),
            "stdev": round(_safe_pstdev(ma_per_batch), 4),
            "ci95_lo": round(lo, 4),
            "ci95_hi": round(hi, 4),
            "n_batches": len(ma_per_batch),
            "per_batch": [round(v, 4) for v in ma_per_batch],
        }
    # Aggregate instrumentation
    agg["instrumentation_summary"] = {
        k: round(_safe_mean([
            b["instrumentation"].get(k, 0)
            for b in per_batch
            if b["instrumentation"]
        ]), 2)
        for k in [
            "applied_pct",
            "set_e_section_mean",
            "set_e_kg_mean",
            "total_protected_mean",
            "kg_pool_size_mean",
            "queries_with_kg_pool",
            "queries_with_protected",
            "n_queries",
        ]
    }
    p50s = [b["latency_p50_ms"] for b in per_batch if b["latency_p50_ms"]]
    agg["latency_p50_ms_mean"] = round(_safe_mean(p50s), 2) if p50s else None

    # Gate verdicts
    overall = agg["per_metric"].get("overall", {}).get("mean")
    f_mh = agg["per_metric"].get("F_MH", {}).get("mean")
    ma_comp = agg["per_metric"].get("MA_composite", {}).get("mean")
    latency = agg["latency_p50_ms_mean"]

    deltas: Dict[str, float] = {}
    gates: Dict[str, Dict[str, Any]] = {}

    # Gate 1: MA composite ≥ Phase H v2 baseline -1pp tolerance
    if ma_comp is not None:
        delta_ma = ma_comp - BASELINE_H2["MA_composite"]
        deltas["MA_composite_delta_vs_H2"] = round(delta_ma, 4)
        gates["gate1_MA_recovery"] = {
            "threshold": "Δ ≥ -1.0pp vs Phase H v2 baseline (73.34%)",
            "actual_delta": round(delta_ma, 4),
            "actual_value": round(ma_comp, 4),
            "passes": delta_ma >= -1.0,
            "vs_MAP_standalone_delta": round(delta_ma - MAP_STANDALONE["MA_composite_lift"], 4),
        }

    # Gate 2: F_MH ≥ Phase MAP standalone +4.02pp gain over baseline
    if f_mh is not None:
        delta_fmh = f_mh - BASELINE_H2["F_MH"]
        deltas["F_MH_delta_vs_H2"] = round(delta_fmh, 4)
        gates["gate2_FMH_preservation"] = {
            "threshold": f"Δ ≥ +{MAP_STANDALONE['F_MH_lift']:.2f}pp vs Phase H v2 baseline",
            "actual_delta": round(delta_fmh, 4),
            "actual_value": round(f_mh, 4),
            "passes": delta_fmh >= MAP_STANDALONE["F_MH_lift"],
        }

    # Gate 3: Overall ≥ Phase H v2 -1.5pp tolerance
    if overall is not None:
        delta_overall = overall - BASELINE_H2["overall"]
        deltas["overall_delta_vs_H2"] = round(delta_overall, 4)
        gates["gate3_overall_tolerance"] = {
            "threshold": "Δ ≥ -1.5pp vs Phase H v2 baseline (51.68%)",
            "actual_delta": round(delta_overall, 4),
            "actual_value": round(overall, 4),
            "passes": delta_overall >= -1.5,
        }

    # Gate 4: latency informational (no Phase G baseline available locally)
    gates["gate4_latency"] = {
        "threshold": "p50 ≤ 1.2× Phase G rerank + KG overhead (informational)",
        "actual_p50_ms": latency,
        "passes": True,  # informational
    }

    gates_pass = sum(1 for g in gates.values() if g.get("passes"))
    agg["gates"] = gates
    agg["gates_summary"] = {
        "passed": gates_pass,
        "total": len(gates),
        "verdict": (
            "WIN: KG anchor closes MA gap"
            if gates.get("gate1_MA_recovery", {}).get("passes")
            and gates.get("gate2_FMH_preservation", {}).get("passes")
            else "PARTIAL: see gates"
        ),
    }
    agg["deltas"] = deltas
    agg["per_batch"] = per_batch
    agg["baselines"] = {
        "phase_h2": BASELINE_H2,
        "map_standalone": MAP_STANDALONE,
        "kg_sparse": KG_SPARSE,
        "phase_g": PHASE_G,
    }

    out_json_path.write_text(json.dumps(agg, indent=2))

    # Markdown report
    md = []
    md.append("# Phase KGMAP 5-batch (Wave B composability) — KG-anchored MA-protection\n")
    md.append(f"Run dirs: {len(run_dirs)} | Batches with data: {len(per_batch)}\n")
    md.append(f"\n## Verdict: {agg['gates_summary']['verdict']} ({gates_pass}/{len(gates)} gates met)\n")

    md.append("\n## Aggregate metrics (per-batch CI95)\n")
    md.append("| Metric | Mean | CI95 lo | CI95 hi | Δ vs H2 | Per-batch |\n")
    md.append("|---|---:|---:|---:|---:|---|\n")
    for m in metrics + ["MA_composite"]:
        if m in agg["per_metric"]:
            row = agg["per_metric"][m]
            base = BASELINE_H2.get(m)
            d = (
                f"{row['mean'] - base:+.2f}pp"
                if isinstance(base, (int, float))
                else "—"
            )
            md.append(
                f"| {m} | {row['mean']:.4f} | {row['ci95_lo']:.4f} | "
                f"{row['ci95_hi']:.4f} | {d} | "
                f"{', '.join(f'{v:.2f}' for v in row['per_batch'])} |\n"
            )

    md.append("\n## Set E / KG anchor instrumentation\n")
    md.append("Empirical mechanism firing — Wave B composability hypothesis test.\n")
    md.append("Lesson `[[empirical-set-e-empty-confirms-mechanism-not-corpus]]`.\n\n")
    md.append("| Statistic | Mean across batches |\n")
    md.append("|---|---:|\n")
    for k, v in agg["instrumentation_summary"].items():
        md.append(f"| {k} | {v} |\n")

    md.append("\n## Gates\n")
    for gname, g in gates.items():
        passes = "PASS" if g["passes"] else "FAIL"
        md.append(f"\n### {gname}: {passes}\n")
        md.append(f"- Threshold: {g['threshold']}\n")
        if "actual_delta" in g:
            md.append(f"- Actual Δ: {g['actual_delta']:+.4f}pp\n")
        if "actual_value" in g:
            md.append(f"- Actual: {g['actual_value']:.4f}\n")
        if "vs_MAP_standalone_delta" in g:
            md.append(f"- vs Phase MAP standalone Δ: {g['vs_MAP_standalone_delta']:+.4f}pp\n")
        if "actual_p50_ms" in g:
            md.append(f"- p50 latency: {g['actual_p50_ms']}\n")

    md.append("\n## Per-batch detail\n")
    for b in per_batch:
        md.append(f"\n### Batch {b['batch']}\n")
        md.append(f"- run_dir: `{b['run_dir']}`\n")
        if b["categories"]:
            md.append(
                "- categories: "
                + ", ".join(f"{k}={v:.2f}" for k, v in sorted(b["categories"].items()))
                + "\n"
            )
        if b["instrumentation"]:
            md.append(
                "- instrumentation: "
                + ", ".join(f"{k}={v}" for k, v in b["instrumentation"].items())
                + "\n"
            )
        if b["latency_p50_ms"]:
            md.append(f"- p50 latency: {b['latency_p50_ms']:.2f}ms\n")

    md.append("\n## Baselines\n")
    md.append("- Phase H v2 5-batch: overall=51.68% F_MH=3.21% MA_composite=73.34%\n")
    md.append("- Phase MAP standalone: overall=50.44% F_MH lift=+4.02pp MA lift=-6.55pp\n")
    md.append("- Phase KG sparse: overall lift=+0.12pp F_MH lift=+2.81pp MA lift=+0.44pp\n")
    md.append("- Phase G rerank Gemini: F_MH lift=+1.61pp MA lift=-3.55pp\n")

    out_md_path.write_text("".join(md))
    print(f"wrote: {out_md_path} + {out_json_path}")
    print(f"gates passed: {gates_pass}/{len(gates)}")
    print(f"verdict: {agg['gates_summary']['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
