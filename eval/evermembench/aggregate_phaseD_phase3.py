#!/usr/bin/env python3
"""Aggregate Phase D batch 004 + Phase 3 batches 005/010/011/016 results.

Question_id format: <DIM>_<SUBDIM>_Top<BATCH>_<NNN>
  - F_SH, F_MH, F_TP, F_HL — Fine-grained Recall (single/multi/temporal/hallucination)
  - MA_C, MA_P, MA_U       — Memory Awareness (constraint/proactivity/updating)
  - P_Skill, P_Style, P_Title — Profile Understanding

Outputs:
- Per-batch summary
- 5-batch weighted average overall
- Per-dimension + per-subdim aggregation
- Comparison vs MemOS / Zep / Mem0 / MemoBase (paper Table 4 Gemini-3-Flash)
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple


PAPER_TABLE4_GEMINI3 = {
    "MemOS":     59.27,
    "MemoBase":  55.83,
    "Zep":       54.90,
    "Mem0":      52.12,
}

# Sub-dim → parent dimension
SUBDIM_TO_DIM = {
    "F_SH":    "Fine-grained Recall",
    "F_MH":    "Fine-grained Recall",
    "F_TP":    "Fine-grained Recall",
    "F_HL":    "Fine-grained Recall",
    "MA_C":    "Memory Awareness",
    "MA_P":    "Memory Awareness",
    "MA_U":    "Memory Awareness",
    "P_Skill": "Profile Understanding",
    "P_Style": "Profile Understanding",
    "P_Title": "Profile Understanding",
}


def subdim_of(qid: str) -> str:
    """Extract sub-dim prefix from question_id."""
    parts = qid.split("_")
    if len(parts) >= 2 and parts[0] in {"F", "MA"}:
        return "_".join(parts[:2])
    if len(parts) >= 2 and parts[0] == "P":
        return "_".join(parts[:2])
    return "UNKNOWN"


def load_results(path: Path) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def summarize_batch(data: Dict[str, Any]) -> Dict[str, Any]:
    total = int(data.get("total_questions") or 0)
    correct = int(data.get("correct") or 0)
    acc = float(data.get("accuracy") or 0.0) * 100 if total else 0.0

    abt = data.get("accuracy_by_type", {}) or {}
    mc = abt.get("multiple_choice", {})
    oe = abt.get("open_ended", {})

    # Per-subdim from detailed_results
    by_subdim: Dict[str, Dict[str, int]] = defaultdict(lambda: {"c": 0, "t": 0})
    for r in data.get("detailed_results", []):
        sd = subdim_of(r["question_id"])
        by_subdim[sd]["t"] += 1
        if r.get("is_correct"):
            by_subdim[sd]["c"] += 1

    return {
        "total":   total,
        "correct": correct,
        "acc":     acc,
        "mc":      mc,
        "oe":      oe,
        "by_subdim": dict(by_subdim),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--phaseD", required=True, type=Path,
                   help="Phase D batch 004 results JSON")
    p.add_argument("--phase3", required=True, nargs="+", type=Path,
                   help="Phase 3 batch results JSONs (5/10/11/16)")
    p.add_argument("--out", required=True, type=Path,
                   help="Output markdown report path")
    p.add_argument("--phaseB-baseline", type=float, default=57.19,
                   help="Phase B batch 004 overall (default 57.19)")
    p.add_argument("--phaseB-multihop", type=float, default=0.00,
                   help="Phase B batch 004 multi-hop (default 0.00)")
    p.add_argument("--phaseC-baseline", type=float, default=53.83,
                   help="Phase C batch 004 overall (default 53.83)")
    p.add_argument("--pr363-baseline", type=float, default=56.07,
                   help="PR #363 baseline batch 004 (default 56.07)")
    p.add_argument("--pr363-multihop", type=float, default=4.00,
                   help="PR #363 baseline multi-hop (default 4.00)")
    args = p.parse_args()

    all_batches: List[Tuple[str, Path, bool]] = [
        ("004 (Phase D, top-k=20)", args.phaseD, True),
    ]
    for path in args.phase3:
        # Extract batch number from filename: results-batch-005.json
        stem = path.stem
        batch_num = stem.split("-")[-1]
        all_batches.append((f"{batch_num} (Phase 3, top-k=20)", path, False))

    batch_summaries: List[Dict[str, Any]] = []
    total_correct = 0
    total_questions = 0
    agg_by_subdim: Dict[str, Dict[str, int]] = defaultdict(lambda: {"c": 0, "t": 0})
    agg_mc = {"c": 0, "t": 0}
    agg_oe = {"c": 0, "t": 0}

    for label, path, is_phaseD in all_batches:
        if not path.exists():
            print(f"WARN: missing {path}")
            batch_summaries.append({"label": label, "missing": True})
            continue
        data = load_results(path)
        s = summarize_batch(data)
        s["label"] = label
        s["is_phaseD"] = is_phaseD
        batch_summaries.append(s)
        total_correct += s["correct"]
        total_questions += s["total"]
        for sd, d in s["by_subdim"].items():
            agg_by_subdim[sd]["c"] += d["c"]
            agg_by_subdim[sd]["t"] += d["t"]
        if s["mc"]:
            agg_mc["c"] += int(s["mc"].get("correct", 0))
            agg_mc["t"] += int(s["mc"].get("total", 0))
        if s["oe"]:
            agg_oe["c"] += int(s["oe"].get("correct", 0))
            agg_oe["t"] += int(s["oe"].get("total", 0))

    weighted_avg = (total_correct / total_questions * 100) if total_questions else 0.0

    # Aggregate by parent dimension
    by_dim: Dict[str, Dict[str, int]] = defaultdict(lambda: {"c": 0, "t": 0})
    for sd, d in agg_by_subdim.items():
        parent = SUBDIM_TO_DIM.get(sd, "UNKNOWN")
        by_dim[parent]["c"] += d["c"]
        by_dim[parent]["t"] += d["t"]

    # ---------------- markdown ----------------
    lines: List[str] = []
    lines.append("# EverMemBench Path B Full Results — nox-mem vs paper Table 4\n")
    lines.append("## Headline\n")
    lines.append(f"- **nox-mem 5-batch weighted average:** **{weighted_avg:.2f}%** ({total_correct}/{total_questions})")
    lines.append(f"- **vs paper Table 4 (Gemini-3-Flash backbone):**")
    for sys_name, num in sorted(PAPER_TABLE4_GEMINI3.items(), key=lambda x: -x[1]):
        delta = weighted_avg - num
        sign = "+" if delta >= 0 else ""
        verdict = "WIN" if delta > 0.5 else ("TIE" if abs(delta) <= 0.5 else "LOSS")
        lines.append(f"  - {sys_name}: {num:.2f}%  (nox-mem {sign}{delta:.2f}%)  → **{verdict}**")
    lines.append("")
    lines.append("> Honest framing: nox-mem was measured on Gemini-2.5-Flash answer-LLM (cost-throttled). Paper Table 4 column uses Gemini-3-Flash, which is the strongest backbone in the published study. Comparing across LLM backbones is directional, not authoritative.\n")

    lines.append("## Per-batch results\n")
    lines.append("| batch | correct | total | accuracy | MC | OE |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for s in batch_summaries:
        if s.get("missing"):
            lines.append(f"| {s['label']} | — | — | MISSING | — | — |")
            continue
        mc_acc = (s["mc"].get("accuracy", 0) * 100) if s["mc"] else 0
        oe_acc = (s["oe"].get("accuracy", 0) * 100) if s["oe"] else 0
        lines.append(
            f"| {s['label']} | {s['correct']} | {s['total']} | {s['acc']:.2f}% | "
            f"{mc_acc:.2f}% | {oe_acc:.2f}% |"
        )
    mc_avg = (agg_mc["c"] / agg_mc["t"] * 100) if agg_mc["t"] else 0.0
    oe_avg = (agg_oe["c"] / agg_oe["t"] * 100) if agg_oe["t"] else 0.0
    lines.append(
        f"| **5-batch weighted** | **{total_correct}** | **{total_questions}** | "
        f"**{weighted_avg:.2f}%** | **{mc_avg:.2f}%** | **{oe_avg:.2f}%** |"
    )
    lines.append("")

    lines.append("## Per-dimension aggregate (5-batch weighted)\n")
    lines.append("| dimension | correct | total | accuracy |")
    lines.append("|---|---:|---:|---:|")
    for dim in ["Fine-grained Recall", "Memory Awareness", "Profile Understanding"]:
        d = by_dim.get(dim, {"c": 0, "t": 0})
        acc = (d["c"] / d["t"] * 100) if d["t"] else 0.0
        lines.append(f"| {dim} | {d['c']} | {d['t']} | {acc:.2f}% |")
    lines.append("")

    lines.append("## Per-subdim aggregate (5-batch weighted)\n")
    lines.append("| subdim | dimension | correct | total | accuracy |")
    lines.append("|---|---|---:|---:|---:|")
    for sd in sorted(agg_by_subdim.keys()):
        d = agg_by_subdim[sd]
        dim = SUBDIM_TO_DIM.get(sd, "?")
        acc = (d["c"] / d["t"] * 100) if d["t"] else 0.0
        lines.append(f"| {sd} | {dim} | {d['c']} | {d['t']} | {acc:.2f}% |")
    lines.append("")

    # ---- Iteration journey (batch 004 only) ----
    lines.append("## Iteration journey (batch 004 only)\n")
    lines.append("| variant | overall | multi-hop (F_MH) | notes |")
    lines.append("|---|---:|---:|---|")
    lines.append(
        f"| PR #363 baseline (flat md) | {args.pr363_baseline:.2f}% | "
        f"{args.pr363_multihop:.2f}% | Original flat-paragraph markdown |"
    )
    lines.append(
        f"| Phase B (structured per-turn) | {args.phaseB_baseline:.2f}% | "
        f"{args.phaseB_multihop:.2f}% | Per-message blocks + context window |"
    )
    lines.append(
        f"| Phase C (day-group inline) | {args.phaseC_baseline:.2f}% | "
        f"0.00% | One chunk per (date,group); retrieval precision collapsed |"
    )

    phaseD = next((s for s in batch_summaries
                   if not s.get("missing") and s.get("is_phaseD")), None)
    if phaseD:
        mh = phaseD["by_subdim"].get("F_MH", {})
        mh_acc = (mh["c"] / mh["t"] * 100) if mh.get("t") else 0.0
        lines.append(
            f"| **Phase D (top-k=20, Phase B mode)** | **{phaseD['acc']:.2f}%** | "
            f"**{mh_acc:.2f}%** | Search-side fix: top_k 10→20 per MemOS methodology (paper §3.3.4) |"
        )
    lines.append("")

    lines.append("## Cost summary\n")
    lines.append("> Detailed cost in `phaseB-cost-log.md`. Hard cap was $4 (target $3.50).\n")

    lines.append("## Path B recommendations for paper §5\n")
    lines.append("- Lead with the 5-batch weighted average vs MemOS/Zep/Mem0/MemoBase deltas.")
    lines.append("- Disclose the LLM-backbone gap (Gemini-2.5-Flash vs paper's Gemini-3-Flash) upfront.")
    lines.append("- Frame the Phase A→B→C→D iteration journey as ablations, not a single shot.")
    lines.append("- Note that the F_MH (multi-hop) result reflects ingestion-side structure + search-side top_k.")
    lines.append("")

    lines.append("## Future work (not in this round)\n")
    lines.append("- Multi-query expansion (decompose multi-hop into chained single-hops at retrieval time).")
    lines.append("- Cross-encoder reranking on top-20 candidates.")
    lines.append("- Per-question top-k tuning via question-type classifier.")
    lines.append("- Repeat run on Gemini-3-Flash backbone once cost budget allows.")
    lines.append("")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines))
    print(f"Wrote {args.out}")
    print(f"5-batch overall: {weighted_avg:.2f}% ({total_correct}/{total_questions})")
    for sys_name, num in PAPER_TABLE4_GEMINI3.items():
        delta = weighted_avg - num
        print(f"  vs {sys_name} ({num:.2f}%): {'+' if delta >= 0 else ''}{delta:.2f}%")


if __name__ == "__main__":
    main()
