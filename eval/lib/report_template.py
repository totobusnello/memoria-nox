"""eval/lib/report_template.py — MA-aware markdown report generator for EverMemBench.

Lesson codified: [[memory-awareness-dimension-must-be-audited]]
  MA_C / MA_P / MA_U regressions were invisible at Phase G batch 004 because
  batch 004 was already the worst MA batch. They only surfaced at 5-batch
  aggregate. Reports MUST include all three MA sub-dims as mandatory rows, and
  any regression vs baseline must be highlighted (bold + sign annotation).

Usage:
  from eval.lib.report_template import generate_report

  results = {
      "batch_id": "phaseH-v2-5batch",
      "per_batch": {
          "004": {"overall": 54.15, "F_MH": 10.00, "MA_C": 88.00, ...},
          ...
      },
  }
  baselines = {
      "phaseD": {"overall": 62.22, "F_MH": 5.22, "MA_C": 81.40, ...},
      "memos_gpt4mini": {"overall": 42.55, "F_MH": 18.88, "MA_C": 69.90, ...},
  }
  md = generate_report(results, baselines)
  Path("eval/evermembench/RESULTS-PHASEH-5BATCH.md").write_text(md)

The generate_report() function raises ValueError if any REPORT_REQUIRED_DIMS
entry is absent from the per-batch results — fail loudly rather than silently
omit a dimension.
"""

from __future__ import annotations

from typing import Any

from eval.lib.aggregate_5batch import aggregate_5batch, gate_5batch, REQUIRED_DIMS


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Sub-dims always included in the report table, in display order.
# MA_C / MA_P / MA_U are mandatory — regressions there are the costliest
# rerank side-effect and the easiest to overlook in single-batch runs.
# Per [[memory-awareness-dimension-must-be-audited]].
REPORT_REQUIRED_DIMS: list[str] = [
    "overall",
    # Fine-grained Recall
    "F_SH",
    "F_MH",
    "F_TP",
    "F_HL",
    # Memory Awareness — MANDATORY per [[memory-awareness-dimension-must-be-audited]]
    "MA_C",
    "MA_P",
    "MA_U",
    # Profile Understanding
    "P_Style",
    "P_Skill",
    "P_Title",
]

# Parent dimension for display grouping
_SUBDIM_PARENT: dict[str, str] = {
    "overall": "Overall",
    "F_SH": "Fine-grained Recall",
    "F_MH": "Fine-grained Recall",
    "F_TP": "Fine-grained Recall",
    "F_HL": "Fine-grained Recall",
    "MA_C": "Memory Awareness",
    "MA_P": "Memory Awareness",
    "MA_U": "Memory Awareness",
    "P_Style": "Profile Understanding",
    "P_Skill": "Profile Understanding",
    "P_Title": "Profile Understanding",
}

# Threshold below which a delta is considered a regression (pp)
_REGRESSION_THRESHOLD: float = -0.5


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_report(
    results: dict[str, Any],
    baselines: dict[str, dict[str, float]],
    output_path: str | None = None,
    phase_label: str = "Phase X",
) -> str:
    """Generate markdown report with full sub-dim audit including MA dimensions.

    Per [[memory-awareness-dimension-must-be-audited]]: raises ValueError if
    any REPORT_REQUIRED_DIMS entry (except F_HL) is absent from the aggregate
    results — fail loudly rather than silently omit a dimension.

    Args:
        results:
            Dict with keys:
              - "batch_id":  str — label for this phase (e.g. "phaseH-v2-5batch")
              - "per_batch": {batch_id: {metric: value}} — raw per-batch numbers.
                             Values are percentages (0–100).

        baselines:
            Dict of named baselines for comparison columns.
            Example::
                {
                    "Phase D (5-batch)": {"overall": 62.22, "F_MH": 5.22, ...},
                    "MemOS GPT-4.1-mini": {"overall": 42.55, "F_MH": 18.88, ...},
                }
            Baselines with no value for a given metric show "—" in the table.

        output_path:
            If provided, write the markdown to this path.

        phase_label:
            Human-readable label for the current phase (e.g. "Phase H v2").

    Returns:
        Markdown string.

    Raises:
        ValueError: If any required dimension (except F_HL) is missing from
                    the aggregate results.
    """
    per_batch = results.get("per_batch", {})
    batch_id_label = results.get("batch_id", phase_label)
    agg = aggregate_5batch(per_batch)

    # ── Mandatory dim check ──────────────────────────────────────────────────
    # F_HL is optional (not always measured); all others are required.
    optional_dims = {"F_HL"}
    missing_required = [
        d for d in REPORT_REQUIRED_DIMS
        if d not in optional_dims and d not in agg
    ]
    if missing_required:
        raise ValueError(
            f"generate_report: missing required dimensions {missing_required} "
            f"in results for '{batch_id_label}'. "
            f"Per [[memory-awareness-dimension-must-be-audited]], MA_C/MA_P/MA_U "
            f"are mandatory. Available: {sorted(agg.keys())}"
        )

    lines: list[str] = []

    # ── Header ───────────────────────────────────────────────────────────────
    lines.append(f"# EverMemBench {phase_label} — {batch_id_label}\n")
    n_batches = len(per_batch)
    lines.append(f"**Batches:** {', '.join(sorted(per_batch.keys()))} (n={n_batches})\n")

    # ── Headline (overall) ───────────────────────────────────────────────────
    lines.append("## Headline\n")
    overall = agg.get("overall", {})
    overall_mean = overall.get("mean")
    if overall_mean is not None:
        ci_lo = overall.get("ci_lower_95")
        ci_hi = overall.get("ci_upper_95")
        ci_str = (
            f" (95% CI: {ci_lo:.2f}–{ci_hi:.2f}%)"
            if ci_lo is not None and ci_hi is not None
            else ""
        )
        lines.append(
            f"- **{phase_label} overall: {overall_mean:.2f}%**{ci_str} "
            f"(n={overall.get('n',n_batches)} batches)"
        )

    # vs baselines
    for bname, bvals in baselines.items():
        base_overall = bvals.get("overall")
        if base_overall is not None and overall_mean is not None:
            delta = overall_mean - base_overall
            sign = "+" if delta >= 0 else ""
            lines.append(f"- vs **{bname}** ({base_overall:.2f}%): **{sign}{delta:.2f} pp**")
    lines.append("")

    # ── Main results table ───────────────────────────────────────────────────
    lines.append("## Sub-dimension breakdown\n")
    lines.append(
        "> MA_C / MA_P / MA_U are MANDATORY rows — per "
        "`[[memory-awareness-dimension-must-be-audited]]`.\n"
        "> Regressions vs any baseline are highlighted in **bold** with ⚠️.\n"
    )

    # Build table header
    baseline_names = list(baselines.keys())
    header_cols = ["sub-dim", "dimension", f"{phase_label} mean", "stdev", "95% CI"]
    for bn in baseline_names:
        header_cols.append(f"Δ vs {bn}")
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("|" + "|".join(["---"] + ["---:"] * (len(header_cols) - 1)) + "|")

    prev_parent = None
    for dim in REPORT_REQUIRED_DIMS:
        stats = agg.get(dim)
        parent = _SUBDIM_PARENT.get(dim, "Other")

        # Group separator row
        if parent != prev_parent:
            prev_parent = parent
            sep_cols = [f"**{parent}**"] + [""] * (len(header_cols) - 1)
            lines.append("| " + " | ".join(sep_cols) + " |")

        if stats is None:
            row = [f"*{dim}*", "", "—", "—", "—"] + ["—"] * len(baseline_names)
            lines.append("| " + " | ".join(row) + " |")
            continue

        mean = stats["mean"]
        stdev = stats.get("stdev")
        ci_lo = stats.get("ci_lower_95")
        ci_hi = stats.get("ci_upper_95")

        mean_str = f"{mean:.2f}%"
        stdev_str = f"{stdev:.2f} pp" if stdev is not None else "—"
        ci_str = (
            f"{ci_lo:.2f}–{ci_hi:.2f}%"
            if ci_lo is not None and ci_hi is not None
            else "—"
        )

        row = [dim, parent, mean_str, stdev_str, ci_str]

        for bname, bvals in baselines.items():
            base = bvals.get(dim)
            if base is None or stdev is None:
                row.append("—")
                continue
            delta = mean - base
            sign = "+" if delta >= 0 else ""
            delta_str = f"{sign}{delta:.2f} pp"
            # Highlight regressions
            if delta < _REGRESSION_THRESHOLD:
                delta_str = f"**{delta_str} ⚠️**"
            row.append(delta_str)

        lines.append("| " + " | ".join(row) + " |")

    lines.append("")

    # ── Per-batch variance table ─────────────────────────────────────────────
    lines.append("## Per-batch detail\n")
    batch_ids = sorted(per_batch.keys())
    pb_header = ["metric"] + batch_ids + ["mean", "stdev"]
    lines.append("| " + " | ".join(pb_header) + " |")
    lines.append("|" + "|".join(["---"] + ["---:"] * (len(pb_header) - 1)) + "|")

    for dim in REPORT_REQUIRED_DIMS:
        stats = agg.get(dim)
        if stats is None:
            row = [dim] + ["—"] * (len(batch_ids) + 2)
            lines.append("| " + " | ".join(row) + " |")
            continue
        per_b = stats.get("per_batch", {})
        row = [dim]
        for bid in batch_ids:
            val = per_b.get(bid)
            row.append(f"{val:.2f}" if val is not None else "—")
        row.append(f"{stats['mean']:.2f}")
        stdev = stats.get("stdev")
        row.append(f"{stdev:.2f}" if stdev is not None else "—")
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")

    # ── Gate summary ────────────────────────────────────────────────────────
    # Use the first baseline as the gate baseline (typically Phase D)
    if baselines:
        primary_bname, primary_bvals = next(iter(baselines.items()))
        gate = gate_5batch(agg, primary_bvals)
        lines.append(f"## Gate summary vs {primary_bname}\n")
        lines.append("| sub-dim | mean Δ | CI lower Δ | verdict |")
        lines.append("|---|---:|---:|---|")
        for dim in REPORT_REQUIRED_DIMS:
            g = gate.get(dim)
            if g is None:
                continue
            verdict = g.get("verdict", "—")
            mean_d = g.get("mean_delta")
            ci_lo_d = g.get("ci_lower_delta")
            mean_d_str = (
                f"{'+' if mean_d >= 0 else ''}{mean_d:.2f} pp"
                if mean_d is not None
                else "—"
            )
            ci_lo_d_str = (
                f"{'+' if ci_lo_d >= 0 else ''}{ci_lo_d:.2f} pp"
                if ci_lo_d is not None
                else "—"
            )
            verdict_fmt = f"**{verdict}**" if verdict == "SHIP" else verdict
            lines.append(
                f"| {dim} | {mean_d_str} | {ci_lo_d_str} | {verdict_fmt} |"
            )
        lines.append("")

    md = "\n".join(lines)

    if output_path is not None:
        from pathlib import Path
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(md, encoding="utf-8")

    return md
