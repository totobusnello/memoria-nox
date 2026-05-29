#!/usr/bin/env python3
"""
Aggregate Phase KG DENSE 5-batch results + generate RESULTS-KG-DENSIFICATION.md.

Wraps aggregate-phaseKG.py with:
  - Pattern `phaseKG-dense-*` (isolates from sparse phaseKG-NNN-*)
  - Adds Phase KG sparse 5-batch baseline (from PR #379 RESULTS-PHASEKG-5BATCH.md)
    in addition to the Phase H v2 baseline
  - Surfaces KG before/after counts (pulled from .db files)
  - Custom output filename
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import sqlite3
from pathlib import Path
from typing import Dict, List

HERE = Path(__file__).resolve().parent
REPO = HERE  # at repo root for aggregator imports
sys.path.insert(0, str(REPO / "repo" if (REPO / "repo").exists() else REPO))

# Import aggregator from repo (after fresh clone)
AGG_PATH = REPO / "repo" / "eval" / "evermembench" / "aggregate-phaseKG.py"
if not AGG_PATH.exists():
    AGG_PATH = Path("/tmp/kg-densify-F7D5B2B2-534A-4FB3-8A57-30B96488298F/repo/eval/evermembench/aggregate-phaseKG.py")

# Inline the constants we need
PHASE_H_V2_5BATCH = {
    "overall": 51.68, "F_SH": 80.97, "F_MH": 3.21, "F_TP": 15.00, "F_HL": 22.68,
    "MA_C": 84.60, "MA_P": 65.40, "MA_U": 70.03,
    "P_Style": 39.78, "P_Skill": 49.77, "P_Title": 56.05,
}

PHASE_KG_SPARSE_5BATCH = {
    "overall": 51.80, "F_SH": 81.37, "F_MH": 6.02, "F_TP": 14.67, "F_HL": 22.13,
    "MA_C": 84.60, "MA_P": 66.60, "MA_U": 70.15,
    "P_Style": 39.88, "P_Skill": 47.88, "P_Title": 55.25,
}

MEMOS_GPT41MINI = {
    "overall": 42.55, "F_SH": 71.36, "F_MH": 18.88, "F_TP": 15.67,
    "MA_C": 69.90, "MA_P": 51.99, "MA_U": 45.15,
    "P_Style": 28.98, "P_Skill": 32.54, "P_Title": 48.47,
}


def get_kg_counts(db_path: Path) -> Dict[str, int]:
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        e = con.execute("SELECT COUNT(*) FROM kg_entities").fetchone()[0]
        r = con.execute("SELECT COUNT(*) FROM kg_relations").fetchone()[0]
        con.close()
        return {"entities": e, "relations": r}
    except Exception:
        return {"entities": 0, "relations": 0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", default="/root/.openclaw/evermembench-runs")
    ap.add_argument("--pattern", default="phaseKG-dense-*")
    ap.add_argument("--output", default="RESULTS-KG-DENSIFICATION.md")
    args = ap.parse_args()

    runs_root = Path(args.runs_dir)
    run_dirs = sorted(runs_root.glob(args.pattern))
    if not run_dirs:
        print(f"FATAL: no dirs matching {args.pattern} in {runs_root}")
        return 2

    print(f"Found {len(run_dirs)} dense run dirs:")
    for d in run_dirs:
        print(f"  {d}")

    # Re-implement parser locally rather than monkey-patching
    sys.path.insert(0, "/tmp/kg-densify-F7D5B2B2-534A-4FB3-8A57-30B96488298F/repo/eval/evermembench")
    from importlib import util as ilu
    spec = ilu.spec_from_file_location("agg_kg", "/tmp/kg-densify-F7D5B2B2-534A-4FB3-8A57-30B96488298F/repo/eval/evermembench/aggregate-phaseKG.py")
    agg_kg = ilu.module_from_spec(spec)
    spec.loader.exec_module(agg_kg)

    # Set repo path so its eval.lib imports work
    sys.path.insert(0, "/tmp/kg-densify-F7D5B2B2-534A-4FB3-8A57-30B96488298F/repo")
    try:
        from eval.lib.aggregate_5batch import aggregate_5batch
        from eval.lib.report_template import generate_report
    except ImportError as exc:
        print(f"FATAL: cannot import eval.lib: {exc}")
        return 2

    per_batch_metrics: Dict[str, Dict[str, float]] = {}
    per_batch_coverage: Dict[str, Dict[str, float]] = {}
    per_batch_kg: Dict[str, Dict[str, int]] = {}
    for d in run_dirs:
        m = re.match(r"phaseKG-dense-(\d+)-", d.name)
        if not m:
            continue
        batch = m.group(1)
        analysis = d / "analysis.txt"
        if not analysis.exists():
            print(f"  WARN: {d}/analysis.txt missing")
            continue
        metrics = agg_kg.parse_analysis(analysis)
        if not metrics or "overall" not in metrics:
            print(f"  WARN: {d}/analysis.txt did not parse")
            continue
        per_batch_metrics[batch] = metrics
        sr = d / f"search-results-batch-{batch}.json"
        if sr.exists():
            per_batch_coverage[batch] = agg_kg.parse_kg_meta_coverage(sr)
        per_batch_kg[batch] = get_kg_counts(d / "nox-mem.db")

    if not per_batch_metrics:
        print("FATAL: no batches parsed")
        return 2

    results = {"batch_id": "phaseKG-dense-5batch", "per_batch": per_batch_metrics}
    baselines = {
        "Phase H v2 (no-KG baseline)": PHASE_H_V2_5BATCH,
        "Phase KG sparse (PR #379)": PHASE_KG_SPARSE_5BATCH,
        "MemOS GPT-4.1-mini": MEMOS_GPT41MINI,
    }

    try:
        md = generate_report(results, baselines, phase_label="Phase KG DENSE (Lab Q1 #4 densification)")
    except ValueError as exc:
        print(f"WARN: generate_report failed: {exc}")
        agg = aggregate_5batch(per_batch_metrics)
        md = f"# Phase KG DENSE 5-batch — RAW\n\n```json\n{json.dumps(agg, indent=2, default=str)}\n```\n"

    # Append KG state table
    md += "\n\n## KG Density (per-batch DB state after dense extract)\n\n"
    md += "| batch | entities | relations | sparse_entities | sparse_relations | × entities | × relations |\n"
    md += "|---|---:|---:|---:|---:|---:|---:|\n"
    SPARSE_KG = {"004": (560, 1748), "005": (624, 1823), "010": (565, 1837), "011": (599, 1783), "016": (517, 1583)}
    tot_de = tot_dr = tot_se = tot_sr = 0
    for b in sorted(per_batch_kg.keys()):
        de = per_batch_kg[b]["entities"]
        dr = per_batch_kg[b]["relations"]
        se, sr_ = SPARSE_KG.get(b, (1, 1))
        tot_de += de; tot_dr += dr; tot_se += se; tot_sr += sr_
        md += f"| {b} | {de} | {dr} | {se} | {sr_} | {de/max(se,1):.2f}× | {dr/max(sr_,1):.2f}× |\n"
    md += f"| **TOTAL** | **{tot_de}** | **{tot_dr}** | **{tot_se}** | **{tot_sr}** | **{tot_de/max(tot_se,1):.2f}×** | **{tot_dr/max(tot_sr,1):.2f}×** |\n"

    # KG coverage section
    md += "\n\n## KG Coverage & Latency (dense bench)\n\n"
    md += "| batch | queries | kg_applied | with_entity | with_neighbor | with_boost | kg_ms p50 | kg_ms p95 |\n"
    md += "|---|---:|---:|---:|---:|---:|---:|---:|\n"
    tq = ta = te = tnbr = tb = 0
    for b in sorted(per_batch_coverage.keys()):
        cov = per_batch_coverage[b]
        tq += int(cov["queries_total"]); ta += int(cov["queries_kg_applied"])
        te += int(cov["queries_with_entity"]); tnbr += int(cov["queries_with_neighbor"])
        tb += int(cov["queries_with_chunks_boosted"])
        md += (f"| {b} | {int(cov['queries_total'])} | "
               f"{int(cov['queries_kg_applied'])} | "
               f"{int(cov['queries_with_entity'])} | "
               f"{int(cov['queries_with_neighbor'])} | "
               f"{int(cov['queries_with_chunks_boosted'])} | "
               f"{cov['kg_ms_p50']:.2f}ms | {cov['kg_ms_p95']:.2f}ms |\n")
    if tq:
        md += (f"| **TOTAL** | **{tq}** | "
               f"**{ta}** ({100*ta/tq:.1f}%) | "
               f"**{te}** ({100*te/tq:.1f}%) | "
               f"**{tnbr}** ({100*tnbr/tq:.1f}%) | "
               f"**{tb}** ({100*tb/tq:.1f}%) | "
               "— | — |\n")

    # 4-gate: DENSE vs SPARSE (the explicit task gate Q1.6)
    md += "\n\n## Lab Q1.6 Densification Gate (vs Phase KG sparse PR #379)\n\n"
    agg = aggregate_5batch(per_batch_metrics)
    overall_mean = agg.get("overall", {}).get("mean", 0.0)
    f_mh_mean = agg.get("F_MH", {}).get("mean", 0.0)
    ma_c_mean = agg.get("MA_C", {}).get("mean", 0.0)
    ma_p_mean = agg.get("MA_P", {}).get("mean", 0.0)
    ma_u_mean = agg.get("MA_U", {}).get("mean", 0.0)
    ma_avg = (ma_c_mean + ma_p_mean + ma_u_mean) / 3.0

    # vs SPARSE
    ma_avg_sparse = (PHASE_KG_SPARSE_5BATCH["MA_C"] + PHASE_KG_SPARSE_5BATCH["MA_P"] + PHASE_KG_SPARSE_5BATCH["MA_U"]) / 3.0
    ma_avg_h = (PHASE_H_V2_5BATCH["MA_C"] + PHASE_H_V2_5BATCH["MA_P"] + PHASE_H_V2_5BATCH["MA_U"]) / 3.0
    f_mh_dlt_sparse = f_mh_mean - PHASE_KG_SPARSE_5BATCH["F_MH"]
    ma_dlt_sparse = ma_avg - ma_avg_sparse
    overall_dlt_sparse = overall_mean - PHASE_KG_SPARSE_5BATCH["overall"]
    coverage_pct = (100.0 * tnbr / tq) if tq else 0.0
    # vs H v2 (for original Q1 #4 gate)
    f_mh_dlt_h = f_mh_mean - PHASE_H_V2_5BATCH["F_MH"]
    ma_dlt_h = ma_avg - ma_avg_h

    md += "### Q1.6 densification gates (dense vs sparse KG)\n\n"
    gates = [
        ("MA mean ≥ +1pp vs sparse KG (Q1.6 original target)",
         ma_dlt_sparse >= 1.0,
         f"observed {ma_dlt_sparse:+.2f}pp ({ma_avg:.2f}% vs {ma_avg_sparse:.2f}%)"),
        ("F_MH ≥ sparse KG (preserve +2.81pp vs Phase H v2)",
         f_mh_dlt_h >= 2.81,
         f"observed {f_mh_dlt_h:+.2f}pp vs Phase H v2 ({f_mh_mean:.2f}% vs {PHASE_H_V2_5BATCH['F_MH']:.2f}%)"),
        ("Overall ≥ sparse KG (no regression)",
         overall_dlt_sparse >= 0.0,
         f"observed {overall_dlt_sparse:+.2f}pp ({overall_mean:.2f}% vs {PHASE_KG_SPARSE_5BATCH['overall']:.2f}%)"),
        ("Coverage ≥ 30% queries with ≥1 neighbor",
         coverage_pct >= 30.0,
         f"observed {coverage_pct:.2f}% ({tnbr}/{tq})"),
    ]
    md += "| Gate | Pass | Observed |\n|---|---|---|\n"
    for label, passed, observed in gates:
        md += f"| {label} | {'✅' if passed else '❌'} | {observed} |\n"
    n_pass = sum(1 for _, p, _ in gates if p)
    md += f"\n**Gate summary:** {n_pass} / {len(gates)} conditions met.\n"

    # Decision
    md += "\n### Decision\n\n"
    if n_pass == 4:
        md += "**SHIP DENSE as default for `--kg-walk=1`.** Density signal validated — closes MA gap (Q1.6 original target).\n"
    elif n_pass >= 2 and gates[0][1]:  # MA passed
        md += "**PARTIAL — MA closed via density.** Trade-offs apply; document and consider Q2 spec.\n"
    elif n_pass >= 2:
        md += "**PARTIAL — F_MH preserved, MA NOT closed by density.** Density signal LIMIT validated (Q1 #4 MA gap is NOT density-bound).\n"
    else:
        md += "**REJECT DENSE — regression vs sparse KG.** Keep sparse as canonical; document density LIMIT.\n"

    # Original Q1 #4 gate (vs Phase H v2)
    md += "\n### Original Q1 #4 gates (dense vs Phase H v2, for reference)\n\n"
    gates_orig = [
        ("F_MH lift ≥ +2pp vs Phase H v2", f_mh_dlt_h >= 2.0,
         f"observed {f_mh_dlt_h:+.2f}pp"),
        ("MA lift ≥ +1pp vs Phase H v2", ma_dlt_h >= 1.0,
         f"observed {ma_dlt_h:+.2f}pp"),
        ("Overall non-regression vs Phase H v2",
         (overall_mean - PHASE_H_V2_5BATCH["overall"]) >= 0.0,
         f"observed {overall_mean - PHASE_H_V2_5BATCH['overall']:+.2f}pp"),
        ("Coverage ≥ 30%", coverage_pct >= 30.0,
         f"observed {coverage_pct:.2f}%"),
    ]
    md += "| Gate | Pass | Observed |\n|---|---|---|\n"
    for label, passed, observed in gates_orig:
        md += f"| {label} | {'✅' if passed else '❌'} | {observed} |\n"

    Path(args.output).write_text(md, encoding="utf-8")
    print(f"\nWrote {args.output} ({len(md)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
