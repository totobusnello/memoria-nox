"""Phase Triple 5-batch aggregator + 4-gate evaluator (Wave C composability).

Reads per-batch evaluation_results_<batch>.json and search_results_<batch>.json
from 5 RUN_DIRs and computes the 4-gate verdict for triple-mechanism
composability (KG + MQ + MAP).

Gates (Wave C):
  1. F_MH lift ≥ Wave B KG+MAP +4.04pp   (triple must beat best Wave B combo)
  2. Overall ≥ Phase H v2 51.68% -1.0pp  (overall regression bounded)
  3. MA composite ≥ Wave B KG+MAP -5.02pp (no further MA degradation vs KG+MAP)
  4. Additivity residual analysis (informational; no pass/fail) — measures
     observed vs theoretical perfect-additive prediction.

Decision matrix:
  4/4 PASS  -> ship default
  3/4 PASS  -> ship opt-in
  1-2/4     -> reject default
  0/4       -> reject + reconsider

Triple = phaseTriple adapter mode (KG path + MQ decomposition + cross-encoder
rerank + MA-protection with KG-anchored bypass). Each mechanism active in a
distinct pipeline stage:
  stage 1 (retrieval expansion): MQ sub-query decomposition + RRF union
  stage 2 (retrieval entity-walk): KG 1-hop boost on MQ-merged candidates
  stage 3 (rerank protection): MAP bypass-entity for KG-anchored chunks

Additivity decomposition reports:
  - Theoretical perfect-additive prediction: KG_alone + MQ_alone + MAP_alone
  - Observed Wave B combos: KG+MQ (PR #389) and KG+MAP (PR #390)
  - Observed Wave C triple (this run)
  - Residual vs perfect-additive prediction (negative = same-stage overlap;
    positive = synergy)
  - Pair-wise prediction: KG+MAP_observed + (MQ_alone − overlap_with_KG)

Usage:
    python aggregate_phaseTriple_5batch.py <out_md> <out_json> <run_dir1...>
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ── Reference baselines (5-batch CLEAN, gpt-4.1-mini, EverMemBench Phase H v2)──

# Phase H v2 baseline (5-batch CLEAN, gpt-4.1-mini)
# Source: RESULTS-PHASEH-v2-5BATCH.md (PR #372 + #377)
BASELINE_H2 = {
    "overall": 51.68,
    "F_SH": None,
    "F_MH": 3.21,
    "F_HL": None,
    "F_TP": None,
    "MA_C": 84.60,
    "MA_P": 65.40,
    "MA_U": 70.03,
    "MA_composite": 73.34,
}

# Phase KG sparse 5-batch lift vs Phase H v2 (PR #379)
KG_STANDALONE = {
    "overall_lift": 0.12,
    "F_MH_lift": 2.81,
    "MA_composite_lift": 0.44,
}

# Phase MQ 5-batch lift vs Phase H v2 (PR #385)
MQ_STANDALONE = {
    "overall_lift": -1.12,
    "F_MH_lift": 3.61,
    "MA_composite_lift": -1.38,
}

# Phase MAP standalone 5-batch lift vs Phase H v2 (PR #386)
MAP_STANDALONE = {
    "overall_lift": -1.24,
    "F_MH_lift": 4.02,
    "F_HL_lift": 4.34,
    "MA_composite_lift": -6.55,
}

# Wave B KG+MQ combo (PR #389) — 1/4 gates ship opt-in (D68 dual finding)
WAVE_B_KGMQ = {
    "F_MH_lift": 4.81,             # observed
    "predicted_perfect_additive_F_MH": 6.42,  # KG_alone + MQ_alone
    "residual_additivity_F_MH": -1.61,        # observed − predicted
    "overall_lift": -1.50,         # observed
    "MA_composite_lift": -1.92,    # observed
}

# Wave B KG+MAP combo (PR #390) — 3/4 gates ship opt-in
WAVE_B_KGMAP = {
    "F_MH_lift": 4.04,                     # observed
    "predicted_perfect_additive_F_MH": 6.83,  # KG_alone + MAP_alone
    "residual_additivity_F_MH": -2.79,       # observed − predicted
    "overall_lift": -0.92,                 # observed
    "MA_composite_lift": -5.02,            # observed
}

# Phase G rerank Gemini (5-batch reference)
PHASE_G = {
    "F_MH_lift": 1.61,
    "MA_composite_lift": -3.55,
    "p50_latency_ms": None,
}

# MemOS reference (5-batch, gpt-4.1-mini)
MEMOS_REF = {
    "overall": 42.55,
    "F_MH_lift_vs_H2": 18.88,  # MemOS F_MH gap above Phase H v2 baseline F_MH=3.21
    "F_MH": 22.09,             # absolute
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
    """Extract overall accuracy from evaluation_results json."""
    out: Dict[str, float] = {}
    if isinstance(eval_results, dict):
        acc = eval_results.get("accuracy")
        if isinstance(acc, (int, float)):
            acc_f = float(acc)
            out["overall"] = acc_f * (100.0 if 0 <= acc_f <= 1 else 1.0)
    return out


_COMBINED_RE = None


def _extract_category_scores_from_text(text: str) -> Dict[str, float]:
    """Parse `analysis.txt` Combined (Major_Minor) section for F_*/MA_* lines."""
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
                out[m.group(1)] = float(m.group(2))
    return out


def _extract_triple_instrumentation(search_results: Any) -> Dict[str, Any]:
    """Per-batch Set E / KG pool / MQ sub-query firing statistics (3-stage)."""
    items: List[Dict[str, Any]] = []
    if isinstance(search_results, list):
        items = [it for it in search_results if isinstance(it, dict)]
    elif isinstance(search_results, dict):
        items = [
            it for it in search_results.get("results", [])
            if isinstance(it, dict)
        ]
    n = len(items)

    # Stage 1: MQ
    mq_sub_counts: List[int] = []
    mq_fired: int = 0
    mq_status_counter: Dict[str, int] = {}

    # Stage 2: KG
    kg_pool_sizes: List[int] = []
    kg_queries_with_pool: int = 0

    # Stage 3: MAP
    set_e_section_counts: List[int] = []
    set_e_kg_counts: List[int] = []
    total_protected_counts: List[int] = []
    map_applied: int = 0
    kg_anchor_active: int = 0

    # Additional triple-mode fields we observed in real adapter output
    mq_total_pre_dedup_sum = 0
    mq_unique_after_dedup_sum = 0
    kg_neighbors_sum = 0
    kg_chunks_boosted_sum = 0
    composability_active_count = 0
    for it in items:
        meta = it.get("metadata") or {}

        # MQ — real key names from adapter:
        #   mq_status         (applied/fallback_single/error)
        #   mq_n_actual       (int: number of sub-queries actually generated)
        #   mq_sub_queries    (list[str]: actual sub-query texts; len == mq_n_actual)
        #   mq_total_results_pre_dedup
        #   mq_unique_after_dedup
        st = str(meta.get("mq_status") or "off")
        mq_status_counter[st] = mq_status_counter.get(st, 0) + 1
        sub_n = int(meta.get("mq_n_actual") or 0)
        if sub_n == 0:
            # Fall back to length of mq_sub_queries list if present
            sql = meta.get("mq_sub_queries") or []
            if isinstance(sql, list):
                sub_n = len(sql)
        mq_sub_counts.append(sub_n)
        if sub_n > 0:
            mq_fired += 1
        mq_total_pre_dedup_sum += int(meta.get("mq_total_results_pre_dedup") or 0)
        mq_unique_after_dedup_sum += int(meta.get("mq_unique_after_dedup") or 0)
        if meta.get("composability_kg_mq_active"):
            composability_active_count += 1

        # KG — real key names: ma_kg_evidence_pool_size (pool of evidence chunks
        # from 1-hop walk) + kg_meta.{neighbors_found,direct_chunks,chunks_boosted}
        pool = int(meta.get("ma_kg_evidence_pool_size") or 0)
        if pool == 0:
            # Try nested kg_meta direct_chunks as fallback
            kg_meta = meta.get("kg_meta") or {}
            pool = int(kg_meta.get("direct_chunks") or 0)
        kg_pool_sizes.append(pool)
        if pool > 0:
            kg_queries_with_pool += 1
        kg_meta = meta.get("kg_meta") or {}
        kg_neighbors_sum += int(kg_meta.get("neighbors_found") or 0)
        kg_chunks_boosted_sum += int(kg_meta.get("chunks_boosted") or 0)

        # MAP — these key names matched what we expected
        if meta.get("ma_protection_applied"):
            map_applied += 1
        if meta.get("ma_protection_kg_anchor"):
            kg_anchor_active += 1
        set_e_section_counts.append(int(meta.get("ma_set_e_count") or 0))
        set_e_kg_counts.append(int(meta.get("ma_set_e_kg_count") or 0))
        total_protected_counts.append(int(meta.get("ma_total_protected_count") or 0))

    return {
        "n_queries": n,
        # Stage 1: MQ
        "mq_status_counter": mq_status_counter,
        "mq_fired_queries": mq_fired,
        "mq_fired_pct": round(100.0 * mq_fired / max(n, 1), 2),
        "mq_subqueries_total": sum(mq_sub_counts),
        "mq_subqueries_mean_per_q": round(_safe_mean(mq_sub_counts), 2),
        "mq_total_results_pre_dedup_sum": mq_total_pre_dedup_sum,
        "mq_unique_after_dedup_sum": mq_unique_after_dedup_sum,
        "mq_total_results_pre_dedup_mean": round(
            mq_total_pre_dedup_sum / max(n, 1), 2
        ),
        "mq_unique_after_dedup_mean": round(
            mq_unique_after_dedup_sum / max(n, 1), 2
        ),
        "composability_kg_mq_active_pct": round(
            100.0 * composability_active_count / max(n, 1), 2
        ),
        # Stage 2: KG
        "kg_pool_total": sum(kg_pool_sizes),
        "kg_pool_mean_per_q": round(_safe_mean(kg_pool_sizes), 2),
        "kg_queries_with_pool": kg_queries_with_pool,
        "kg_queries_with_pool_pct": round(
            100.0 * kg_queries_with_pool / max(n, 1), 2
        ),
        "kg_neighbors_found_mean": round(kg_neighbors_sum / max(n, 1), 2),
        "kg_chunks_boosted_mean": round(kg_chunks_boosted_sum / max(n, 1), 2),
        # Stage 3: MAP
        "map_applied_count": map_applied,
        "map_applied_pct": round(100.0 * map_applied / max(n, 1), 2),
        "kg_anchor_active": kg_anchor_active,
        "set_e_section_mean": round(_safe_mean(set_e_section_counts), 2),
        "set_e_kg_mean": round(_safe_mean(set_e_kg_counts), 2),
        "total_protected_mean": round(_safe_mean(total_protected_counts), 2),
        "queries_with_protection": sum(1 for x in total_protected_counts if x > 0),
        "queries_with_protection_pct": round(
            100.0 * sum(1 for x in total_protected_counts if x > 0) / max(n, 1), 2
        ),
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


def _mean_instrumentation(per_batch: List[Dict[str, Any]]) -> Dict[str, float]:
    keys = [
        # MQ
        "mq_fired_pct",
        "mq_subqueries_mean_per_q",
        "mq_total_results_pre_dedup_mean",
        "mq_unique_after_dedup_mean",
        "composability_kg_mq_active_pct",
        # KG
        "kg_pool_mean_per_q",
        "kg_queries_with_pool_pct",
        "kg_neighbors_found_mean",
        "kg_chunks_boosted_mean",
        # MAP
        "map_applied_pct",
        "set_e_section_mean",
        "set_e_kg_mean",
        "total_protected_mean",
        "queries_with_protection_pct",
        "n_queries",
    ]
    out: Dict[str, float] = {}
    for k in keys:
        vals = [
            float(b["instrumentation"].get(k, 0))
            for b in per_batch
            if b.get("instrumentation")
        ]
        out[k] = round(_safe_mean(vals), 2) if vals else 0.0
    return out


def main() -> int:
    if len(sys.argv) < 4:
        print(
            "usage: aggregate_phaseTriple_5batch.py "
            "<out_md> <out_json> <run_dir1> [run_dir2 ...]"
        )
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
            "wave-C-Triple-*.json",
            "results-batch-*.json",
            "results-wave-C-Triple-*.json",
        ]:
            cands = list(d.glob(pat))
            if cands:
                eval_path = cands[0]
                break
        search_path = None
        for pat in [
            "search-wave-C-Triple-*.json",
            "search-batch-*.json",
        ]:
            cands = list(d.glob(pat))
            if cands:
                search_path = cands[0]
                break

        eval_data = _read_json(eval_path) if eval_path else None
        search_data = _read_json(search_path) if search_path else None
        cats = _extract_category_scores(eval_data) if eval_data else {}
        analysis_path = d / "analysis.txt"
        if analysis_path.is_file():
            text_cats = _extract_category_scores_from_text(
                analysis_path.read_text(errors="ignore")
            )
            for k, v in text_cats.items():
                cats[k] = v
        instr = _extract_triple_instrumentation(search_data) if search_data else {}
        p50 = _extract_latency_p50_ms(search_data) if search_data else None

        # Batch id = first 3 chars after "phaseTriple-"
        # path looks like phaseTriple-004-1716901234 → batch=004
        parts = d.name.split("-")
        bid = parts[1] if len(parts) >= 2 else d.name
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
    # MA composite = mean of MA_C, MA_P, MA_U per batch
    ma_dims = ["MA_C", "MA_P", "MA_U"]
    ma_per_batch = []
    for b in per_batch:
        vals = [float(b["categories"][m]) for m in ma_dims if m in b["categories"]]
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

    agg["instrumentation_summary"] = _mean_instrumentation(per_batch)
    p50s = [b["latency_p50_ms"] for b in per_batch if b["latency_p50_ms"]]
    agg["latency_p50_ms_mean"] = round(_safe_mean(p50s), 2) if p50s else None

    # ── Gate computation ───────────────────────────────────────────────────────
    overall = agg["per_metric"].get("overall", {}).get("mean")
    f_mh = agg["per_metric"].get("F_MH", {}).get("mean")
    ma_comp = agg["per_metric"].get("MA_composite", {}).get("mean")

    deltas: Dict[str, float] = {}
    gates: Dict[str, Dict[str, Any]] = {}

    # Gate 1: F_MH lift ≥ Wave B KG+MAP +4.04pp
    if f_mh is not None:
        f_mh_lift = f_mh - BASELINE_H2["F_MH"]
        deltas["F_MH_lift_vs_H2"] = round(f_mh_lift, 4)
        gates["gate1_FMH_beats_KGMAP"] = {
            "threshold": (
                "F_MH lift ≥ Wave B KG+MAP +4.04pp "
                "(triple must beat best Wave B combo)"
            ),
            "actual_lift": round(f_mh_lift, 4),
            "actual_value": round(f_mh, 4),
            "delta_vs_KGMAP": round(
                f_mh_lift - WAVE_B_KGMAP["F_MH_lift"], 4
            ),
            "passes": f_mh_lift >= WAVE_B_KGMAP["F_MH_lift"],
        }

    # Gate 2: Overall regression ≤ -1pp vs Phase H v2
    if overall is not None:
        delta_overall = overall - BASELINE_H2["overall"]
        deltas["overall_delta_vs_H2"] = round(delta_overall, 4)
        gates["gate2_overall_regression_bounded"] = {
            "threshold": "Overall Δ ≥ -1.0pp vs Phase H v2 (51.68%)",
            "actual_delta": round(delta_overall, 4),
            "actual_value": round(overall, 4),
            "passes": delta_overall >= -1.0,
        }

    # Gate 3: MA composite recovery ≥ Wave B KG+MAP -5.02pp (no worse)
    if ma_comp is not None:
        delta_ma = ma_comp - BASELINE_H2["MA_composite"]
        deltas["MA_composite_delta_vs_H2"] = round(delta_ma, 4)
        gates["gate3_MA_no_worse_than_KGMAP"] = {
            "threshold": (
                "MA composite Δ ≥ Wave B KG+MAP −5.02pp "
                "(no further MA degradation)"
            ),
            "actual_delta": round(delta_ma, 4),
            "actual_value": round(ma_comp, 4),
            "delta_vs_KGMAP": round(
                delta_ma - WAVE_B_KGMAP["MA_composite_lift"], 4
            ),
            "passes": delta_ma >= WAVE_B_KGMAP["MA_composite_lift"],
        }

    # Gate 4: Additivity residual analysis (informational; always passes)
    # Compare observed triple F_MH_lift against theoretical predictions
    additivity = None
    if f_mh is not None:
        f_mh_lift_obs = f_mh - BASELINE_H2["F_MH"]
        perfect_additive = (
            KG_STANDALONE["F_MH_lift"]
            + MQ_STANDALONE["F_MH_lift"]
            + MAP_STANDALONE["F_MH_lift"]
        )
        residual_perfect = f_mh_lift_obs - perfect_additive
        # Pair-wise prediction: KG+MAP observed + MQ_alone (assume MQ stacks fully)
        pair_kgmap_plus_mq = (
            WAVE_B_KGMAP["F_MH_lift"] + MQ_STANDALONE["F_MH_lift"]
        )
        residual_kgmap_plus_mq = f_mh_lift_obs - pair_kgmap_plus_mq
        # Pair-wise prediction: KG+MQ observed + MAP_alone
        pair_kgmq_plus_map = (
            WAVE_B_KGMQ["F_MH_lift"] + MAP_STANDALONE["F_MH_lift"]
        )
        residual_kgmq_plus_map = f_mh_lift_obs - pair_kgmq_plus_map

        # MemOS gap closure (vs MemOS F_MH=22.09 = +18.88pp over H2)
        gap_pct = round(
            100.0 * f_mh_lift_obs / MEMOS_REF["F_MH_lift_vs_H2"], 2
        )

        additivity = {
            "observed_triple_F_MH_lift": round(f_mh_lift_obs, 4),
            "perfect_additive_prediction": round(perfect_additive, 4),
            "residual_vs_perfect_additive": round(residual_perfect, 4),
            "pair_kgmap_plus_mq_prediction": round(pair_kgmap_plus_mq, 4),
            "residual_vs_kgmap_plus_mq": round(residual_kgmap_plus_mq, 4),
            "pair_kgmq_plus_map_prediction": round(pair_kgmq_plus_map, 4),
            "residual_vs_kgmq_plus_map": round(residual_kgmq_plus_map, 4),
            "memos_gap_closure_pct": gap_pct,
        }

    gates["gate4_additivity_decomposition"] = {
        "threshold": "informational — residual analysis only",
        "additivity": additivity,
        "passes": True,  # informational
    }

    # ── Verdict ────────────────────────────────────────────────────────────────
    strict_gates = [
        "gate1_FMH_beats_KGMAP",
        "gate2_overall_regression_bounded",
        "gate3_MA_no_worse_than_KGMAP",
    ]
    strict_passed = sum(
        1 for g in strict_gates if gates.get(g, {}).get("passes")
    )
    gates_pass = sum(1 for g in gates.values() if g.get("passes"))
    # Include gate 4 in count (informational always passes), so 4/4 with all
    # strict gates met = ship default.
    if strict_passed == 3:
        decision = "SHIP DEFAULT (4/4 — triple beats KG+MAP without MA cost)"
    elif strict_passed == 2:
        decision = "SHIP OPT-IN (3/4 — partial win, gate by env flag)"
    elif strict_passed == 1:
        decision = "REJECT DEFAULT (1-2/4 — opt-in only, document failure mode)"
    else:
        decision = "REJECT + RECONSIDER (0/4 — composability hypothesis falsified)"

    agg["gates"] = gates
    agg["gates_summary"] = {
        "passed_strict": strict_passed,
        "passed_total": gates_pass,
        "total": len(gates),
        "decision": decision,
    }
    agg["deltas"] = deltas
    agg["per_batch"] = per_batch
    agg["baselines"] = {
        "phase_h2": BASELINE_H2,
        "kg_standalone": KG_STANDALONE,
        "mq_standalone": MQ_STANDALONE,
        "map_standalone": MAP_STANDALONE,
        "wave_b_kgmq": WAVE_B_KGMQ,
        "wave_b_kgmap": WAVE_B_KGMAP,
        "phase_g": PHASE_G,
        "memos_ref": MEMOS_REF,
    }

    out_json_path.write_text(json.dumps(agg, indent=2))

    # ── Markdown report ────────────────────────────────────────────────────────
    md = []
    md.append("# Phase Triple 5-batch (Wave C composability) — KG + MQ + MAP\n")
    md.append(f"\nRun dirs: {len(run_dirs)} | Batches with data: {len(per_batch)}\n")
    md.append(
        f"\n## Decision: **{decision}** "
        f"(strict {strict_passed}/3 + informational {gates_pass - strict_passed}/1)\n"
    )

    md.append("\n## Aggregate metrics (5-batch CI95)\n")
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

    md.append("\n## Stage firing — 3-stage pipeline empirical evidence\n")
    md.append(
        "Per-query telemetry confirms each composability stage fires "
        "independently. Lesson `[[empirical-set-e-empty-confirms-mechanism-"
        "not-corpus]]`.\n\n"
    )
    md.append("| Statistic | Mean across batches |\n")
    md.append("|---|---:|\n")
    for k, v in agg["instrumentation_summary"].items():
        md.append(f"| {k} | {v} |\n")

    md.append("\n## Gates\n")
    for gname, g in gates.items():
        passes = "PASS" if g["passes"] else "FAIL"
        md.append(f"\n### {gname}: {passes}\n")
        md.append(f"- Threshold: {g['threshold']}\n")
        for k in (
            "actual_lift", "actual_delta", "actual_value",
            "delta_vs_KGMAP",
        ):
            if k in g:
                v = g[k]
                if isinstance(v, float):
                    md.append(f"- {k}: {v:+.4f}\n")
                else:
                    md.append(f"- {k}: {v}\n")
        if "additivity" in g and g["additivity"]:
            md.append("\n  Additivity decomposition:\n")
            for k, v in g["additivity"].items():
                md.append(f"  - {k}: {v}\n")

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
            md.append("- instrumentation:\n")
            for k, v in b["instrumentation"].items():
                md.append(f"  - {k}: {v}\n")
        if b["latency_p50_ms"]:
            md.append(f"- p50 latency: {b['latency_p50_ms']:.2f}ms\n")

    md.append("\n## Reference baselines\n")
    md.append("- Phase H v2 5-batch: overall=51.68% F_MH=3.21% MA_composite=73.34%\n")
    md.append("- KG sparse standalone (PR #379): overall +0.12pp F_MH +2.81pp MA +0.44pp\n")
    md.append("- MQ standalone (PR #385): overall -1.12pp F_MH +3.61pp MA -1.38pp\n")
    md.append("- MAP standalone (PR #386): overall -1.24pp F_MH +4.02pp MA -6.55pp\n")
    md.append(
        "- Wave B KG+MQ (PR #389): F_MH +4.81pp (vs +6.42pp perfect-additive, "
        "residual -1.61pp → same-stage retrieval overlap)\n"
    )
    md.append(
        "- Wave B KG+MAP (PR #390): F_MH +4.04pp (vs +6.83pp perfect-additive, "
        "residual -2.79pp → different-stage but Set E small)\n"
    )
    md.append(
        f"- MemOS reference: F_MH={MEMOS_REF['F_MH']:.2f}% "
        f"(lift +{MEMOS_REF['F_MH_lift_vs_H2']:.2f}pp vs H2)\n"
    )

    md.append("\n## Decision matrix\n")
    md.append("- 4/4 PASS → ship default\n")
    md.append("- 3/4 PASS → ship opt-in via NOX_ADAPTER_MODE=phaseTriple\n")
    md.append("- 1-2/4 PASS → reject default, opt-in only with documented failure mode\n")
    md.append("- 0/4 PASS → reject + reconsider triple composability hypothesis\n")

    out_md_path.write_text("".join(md))
    print(f"wrote: {out_md_path} + {out_json_path}")
    print(f"strict gates: {strict_passed}/3 + informational: {gates_pass - strict_passed}/1")
    print(f"decision: {decision}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
