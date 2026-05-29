#!/usr/bin/env python3
"""
Aggregate Phase KG 5-batch results + generate RESULTS-PHASEKG-5BATCH.md.

Reads analysis.txt files from each phaseKG-<batch>-<ts>/ run dir, parses the
"Combined (Major_Minor) Accuracy" + "Overall" sections, then calls
eval/lib/aggregate_5batch.py + eval/lib/report_template.py.

Compares against Phase H v2 5-batch baseline (PR #377) and MemOS GPT-4.1-mini
Table 4.

Usage:
    python3 aggregate-phaseKG.py \\
        --runs-dir /root/.openclaw/evermembench-runs \\
        --pattern 'phaseKG-*' \\
        --output RESULTS-PHASEKG-5BATCH.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Make the eval.lib package importable from any path
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent  # eval/evermembench → repo root
sys.path.insert(0, str(REPO))

try:
    from eval.lib.aggregate_5batch import aggregate_5batch, gate_5batch  # noqa: E402
    from eval.lib.report_template import generate_report, REPORT_REQUIRED_DIMS  # noqa: E402
except ImportError as exc:
    print(f"FATAL: eval/lib not importable: {exc}")
    print(f"sys.path = {sys.path[:5]}")
    sys.exit(2)


# ──────────────────────────────────────────────────────────────────────────────
# Baselines (locked from PR #377 RESULTS-PHASEH-v2-5BATCH.md)
# ──────────────────────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────────────────────
# Analysis parser
# ──────────────────────────────────────────────────────────────────────────────


def _parse_overall(text: str) -> Optional[Dict[str, float]]:
    """Extract overall accuracy from analyze_results.py text output."""
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
    """Parse the 'Combined (Major_Minor) Accuracy' table."""
    out: Dict[str, float] = {}
    in_combined = False
    for line in text.splitlines():
        if "Combined (Major_Minor) Accuracy" in line:
            in_combined = True
            continue
        if in_combined:
            # Stop at end of section (empty line after table or new header)
            if line.strip().startswith("---") and "Category" not in text[text.find(line):text.find(line)+100]:
                continue
            # Header row
            if line.strip().startswith("Category"):
                continue
            # Empty line ends section
            if not line.strip():
                continue
            # Try parse row like "F_HL  78  19  24.36%"
            m = re.match(r"\s*([A-Z][A-Za-z_]+)\s+(\d+)\s+(\d+)\s+([\d.]+)%\s*$", line)
            if m:
                key = m.group(1)
                pct = float(m.group(4))
                out[key] = pct
            elif line.strip() and not line.strip().startswith("="):
                # Non-matching content past the table — end
                if any(h in line for h in ("=====", "Question Type", "Major Category")):
                    break
    return out


def parse_analysis(path: Path) -> Dict[str, float]:
    """Parse analysis.txt → {overall, F_SH, F_MH, ... MA_C, ...}."""
    text = path.read_text(encoding="utf-8", errors="replace")
    out: Dict[str, float] = {}
    over = _parse_overall(text)
    if over:
        out.update({k: v for k, v in over.items() if not k.startswith("_")})
    combined = _parse_combined(text)
    out.update(combined)
    return out


def parse_kg_meta_coverage(search_results_path: Path) -> Dict[str, float]:
    """Walk search_results.json and compute KG coverage stats."""
    out = {
        "queries_total": 0,
        "queries_kg_applied": 0,
        "queries_with_entity": 0,
        "queries_with_neighbor": 0,
        "queries_with_chunks_boosted": 0,
        "kg_ms_p50": 0.0,
        "kg_ms_p95": 0.0,
    }
    try:
        data = json.loads(search_results_path.read_text(encoding="utf-8"))
    except Exception:
        return out
    if not isinstance(data, list):
        # Some harness versions wrap in {"results": [...]}
        if isinstance(data, dict) and "results" in data:
            data = data["results"]
        else:
            return out
    kg_ms_list: List[float] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        out["queries_total"] += 1
        meta = item.get("metadata") or item.get("meta") or {}
        if meta.get("kg_applied"):
            out["queries_kg_applied"] += 1
        km = meta.get("kg_meta") or {}
        if km.get("entities_in_query", 0) > 0:
            out["queries_with_entity"] += 1
        if km.get("neighbors_found", 0) > 0:
            out["queries_with_neighbor"] += 1
        if km.get("chunks_boosted", 0) > 0:
            out["queries_with_chunks_boosted"] += 1
        if meta.get("kg_ms") is not None:
            try:
                kg_ms_list.append(float(meta["kg_ms"]))
            except (TypeError, ValueError):
                pass
    if kg_ms_list:
        kg_ms_list.sort()
        n = len(kg_ms_list)
        out["kg_ms_p50"] = kg_ms_list[n // 2]
        out["kg_ms_p95"] = kg_ms_list[min(int(n * 0.95), n - 1)]
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", default="/root/.openclaw/evermembench-runs")
    ap.add_argument("--pattern", default="phaseKG-*")
    ap.add_argument("--output", default="RESULTS-PHASEKG-5BATCH.md")
    ap.add_argument("--phase-label", default="Phase KG (Lab Q1 #4)")
    args = ap.parse_args()

    runs_root = Path(args.runs_dir)
    run_dirs = sorted(runs_root.glob(args.pattern))
    if not run_dirs:
        print(f"FATAL: no dirs matching {args.pattern} in {runs_root}")
        return 2

    print(f"Found {len(run_dirs)} run dirs:")
    for d in run_dirs:
        print(f"  {d}")

    # Group by batch id (extract 3-digit batch from phaseKG-NNN-...)
    per_batch_metrics: Dict[str, Dict[str, float]] = {}
    per_batch_coverage: Dict[str, Dict[str, float]] = {}
    per_batch_kg_state: Dict[str, Dict[str, int]] = {}
    for d in run_dirs:
        m = re.match(r"phaseKG-(\d+)-", d.name)
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
        # Prefer the most recent run for a given batch
        if batch not in per_batch_metrics or d > run_dirs[run_dirs.index(d) - 1]:
            per_batch_metrics[batch] = metrics
        # Parse KG coverage
        search_results = d / f"search-results-batch-{batch}.json"
        if search_results.exists():
            per_batch_coverage[batch] = parse_kg_meta_coverage(search_results)
        # KG state of DB (if we can run sqlite3 locally — skip for now, can be added)

    if not per_batch_metrics:
        print("FATAL: no batches parsed successfully")
        return 2

    print(f"\nPer-batch metrics:")
    for b, m in sorted(per_batch_metrics.items()):
        print(f"  {b}: overall={m.get('overall')}")

    # Build the results dict for report_template
    results = {
        "batch_id": "phaseKG-5batch",
        "per_batch": per_batch_metrics,
    }

    baselines = {
        "Phase H v2 (5-batch)": PHASE_H_V2_5BATCH,
        "MemOS GPT-4.1-mini": MEMOS_GPT41MINI,
    }

    # Generate base report
    try:
        md = generate_report(
            results,
            baselines,
            phase_label=args.phase_label,
        )
    except ValueError as exc:
        print(f"WARN: generate_report failed: {exc}")
        # Fall through with raw aggregate
        agg = aggregate_5batch(per_batch_metrics)
        md = f"# Phase KG 5-batch — RAW (report_template failed)\n\n{json.dumps(agg, indent=2, default=str)}\n"

    # Append KG-specific coverage section + gate decision
    md += "\n\n## KG Coverage & Latency\n\n"
    md += "| batch | queries | kg_applied | with_entity | with_neighbor | with_boost | kg_ms p50 | kg_ms p95 |\n"
    md += "|---|---:|---:|---:|---:|---:|---:|---:|\n"
    total_q = total_app = total_ent = total_nbr = total_bst = 0
    for b in sorted(per_batch_coverage.keys()):
        cov = per_batch_coverage[b]
        total_q += int(cov["queries_total"])
        total_app += int(cov["queries_kg_applied"])
        total_ent += int(cov["queries_with_entity"])
        total_nbr += int(cov["queries_with_neighbor"])
        total_bst += int(cov["queries_with_chunks_boosted"])
        md += (
            f"| {b} | {int(cov['queries_total'])} | "
            f"{int(cov['queries_kg_applied'])} | "
            f"{int(cov['queries_with_entity'])} | "
            f"{int(cov['queries_with_neighbor'])} | "
            f"{int(cov['queries_with_chunks_boosted'])} | "
            f"{cov['kg_ms_p50']:.2f}ms | {cov['kg_ms_p95']:.2f}ms |\n"
        )
    if total_q > 0:
        md += (
            f"| **TOTAL** | **{total_q}** | "
            f"**{total_app}** ({100*total_app/total_q:.1f}%) | "
            f"**{total_ent}** ({100*total_ent/total_q:.1f}%) | "
            f"**{total_nbr}** ({100*total_nbr/total_q:.1f}%) | "
            f"**{total_bst}** ({100*total_bst/total_q:.1f}%) | "
            f"— | — |\n"
        )

    # Gate decisions (4 conditions from task spec)
    md += "\n\n## Lab Q1 #4 Gate Decisions (vs Phase H v2 5-batch)\n\n"
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
    coverage_pct = (100.0 * total_nbr / total_q) if total_q else 0.0

    gates = [
        ("F_MH lift ≥ +2pp (5-batch)", f_mh_delta >= 2.0,
         f"observed {f_mh_delta:+.2f}pp ({f_mh_mean:.2f}% vs {PHASE_H_V2_5BATCH['F_MH']:.2f}%)"),
        ("MA lift ≥ +1pp (avg of MA_C, MA_P, MA_U)", ma_delta >= 1.0,
         f"observed {ma_delta:+.2f}pp ({ma_avg:.2f}% vs {ma_avg_base:.2f}%)"),
        ("Overall non-regression (≥ 0pp)", overall_delta >= 0.0,
         f"observed {overall_delta:+.2f}pp ({overall_mean:.2f}% vs {PHASE_H_V2_5BATCH['overall']:.2f}%)"),
        ("Coverage ≥ 30% queries with ≥1 neighbor", coverage_pct >= 30.0,
         f"observed {coverage_pct:.2f}% ({total_nbr}/{total_q})"),
    ]

    md += "| Gate | Pass | Observed |\n|---|---|---|\n"
    for label, passed, observed in gates:
        md += f"| {label} | {'✅' if passed else '❌'} | {observed} |\n"

    n_pass = sum(1 for _, p, _ in gates if p)
    md += f"\n**Gate summary:** {n_pass} / {len(gates)} conditions met.\n"
    if n_pass == len(gates):
        md += "\n**Decision:** SHIP as opt-in `--kg-walk=1` flag (per spec §9 Q1.7).\n"
    elif n_pass >= 2:
        md += "\n**Decision:** Partial — document trade-offs and consider Approach B (N-hop walk) or KG enrichment per spec §9 Q2.\n"
    else:
        md += "\n**Decision:** REJECT — KG path retrieval insufficient at current KG density. Spec §7.3 threshold of abort applies.\n"

    Path(args.output).write_text(md, encoding="utf-8")
    print(f"\nWrote {args.output} ({len(md)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
