"""eval/lib/aggregate_5batch.py — 5-batch CI computation library.

Lesson codified: [[single-batch-gates-unreliable-5x-overstate]]
  Phase G batch 004 (single batch) showed F_MH = 10.00% (+8 pp vs Phase D).
  5-batch confirmation revealed the true mean was 6.83% with 95% CI
  [3.97%, 9.69%]. The single-batch result sat at the upper tail (~1.4σ)
  and overstated the rerank benefit by ~3-4× in absolute terms.
  Any ship/reject gate based on a single batch should use the 95% CI
  lower bound, not the point estimate.

Lesson codified: [[memory-awareness-dimension-must-be-audited]]
  MA_C / MA_P / MA_U regressions were invisible at batch 004 (it was
  already the worst MA batch). They only surfaced at 5-batch. Reports
  MUST include all three MA sub-dims.

Usage:
  from eval.lib.aggregate_5batch import aggregate_5batch, gate_5batch

  per_batch = {
      "004": {"F_MH": 10.00, "overall": 59.74, "MA_C": 68.00},
      "005": {"F_MH":  4.00, "overall": 63.44, "MA_C": 85.00},
      ...
  }
  agg = aggregate_5batch(per_batch)
  # agg["F_MH"] = {mean, stdev, ci_lower_95, ci_upper_95, n, per_batch}

  gate = gate_5batch(agg, baseline={"F_MH": 5.22, "overall": 62.22})
  # gate["F_MH"] = {ship: bool, mean_delta, ci_lower_delta, verdict}
"""

from __future__ import annotations

import math
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# t-distribution critical value for 95% CI, n=5 (dof=4).
# scipy.stats.t.ppf(0.975, df=4) == 2.776
# Hard-coded to avoid requiring scipy for this pure-stdlib module.
_T_CRIT_95_N5: float = 2.776

# Sub-dims that MUST be present in every report.
# Per [[memory-awareness-dimension-must-be-audited]]: MA regressions are the
# costliest rerank side-effect and the hardest to detect in single-batch runs.
REQUIRED_DIMS: list[str] = [
    "F_SH",
    "F_MH",
    "F_TP",
    "MA_C",
    "MA_P",
    "MA_U",
    "P_Style",
    "P_Skill",
    "P_Title",
    "overall",
]


# ---------------------------------------------------------------------------
# Core aggregation
# ---------------------------------------------------------------------------


def aggregate_5batch(
    per_batch_results: dict[str, dict[str, float]],
) -> dict[str, dict[str, Any]]:
    """Aggregate per-batch results into mean + 95% CI per metric.

    Per [[single-batch-gates-unreliable-5x-overstate]]: use t-distribution CI
    (n=5, dof=4, t_crit=2.776) rather than normal approximation because batch
    counts are small and variance can be high.

    Args:
        per_batch_results:
            Mapping from batch_id (e.g. "004") to metric dict.
            Example::
                {
                    "004": {"overall": 59.74, "F_MH": 10.00, "MA_C": 68.00},
                    "005": {"overall": 63.44, "F_MH":  4.00, "MA_C": 85.00},
                }
            Values are percentages (0–100).

    Returns:
        Mapping from metric name to::
            {
                "mean":         float,       # arithmetic mean
                "stdev":        float,       # sample stdev (ddof=1)
                "sem":          float,       # standard error of mean
                "ci_lower_95":  float,       # mean - t_crit * sem
                "ci_upper_95":  float,       # mean + t_crit * sem
                "n":            int,         # number of batches contributing
                "per_batch":    dict,        # {batch_id: value} for raw audit
            }
        If a metric appears in fewer than 2 batches, stdev/CI are set to None.
    """
    if not per_batch_results:
        return {}

    # Collect all metric names across batches
    all_metrics: set[str] = set()
    for metrics in per_batch_results.values():
        all_metrics.update(metrics.keys())

    result: dict[str, dict[str, Any]] = {}

    for metric in sorted(all_metrics):
        values: dict[str, float] = {}
        for batch_id, metrics in per_batch_results.items():
            if metric in metrics:
                values[batch_id] = float(metrics[metric])

        n = len(values)
        vals = list(values.values())

        if n == 0:
            continue

        mean = sum(vals) / n

        if n < 2:
            result[metric] = {
                "mean": mean,
                "stdev": None,
                "sem": None,
                "ci_lower_95": None,
                "ci_upper_95": None,
                "n": n,
                "per_batch": values,
            }
            continue

        # Sample stdev (ddof=1)
        variance = sum((v - mean) ** 2 for v in vals) / (n - 1)
        stdev = math.sqrt(variance)
        sem = stdev / math.sqrt(n)

        # t-distribution CI: use hard-coded n=5 critical value when n==5,
        # otherwise fall back to normal approximation (z=1.96) for larger n.
        # For n < 5, use t_crit from a table (conservative).
        t_crit = _t_crit_for_n(n)
        margin = t_crit * sem

        result[metric] = {
            "mean": mean,
            "stdev": stdev,
            "sem": sem,
            "ci_lower_95": mean - margin,
            "ci_upper_95": mean + margin,
            "n": n,
            "per_batch": values,
        }

    return result


def gate_5batch(
    aggregate: dict[str, dict[str, Any]],
    baseline: dict[str, float],
    gate_threshold: float = 0.0,
) -> dict[str, dict[str, Any]]:
    """Decide ship/reject for each metric based on 5-batch CI vs baseline.

    Ship criterion (both conditions must hold):
      1. mean - baseline > gate_threshold
      2. ci_lower_95 > baseline   (the lower CI bound still beats baseline)

    This prevents a high-mean single outlier batch from passing a gate when
    the CI lower bound dips below baseline.  Per [[single-batch-gates-unreliable-5x-overstate]]:
    batch 004's F_MH 10.0% would pass a >5.22% gate, but the 5-batch CI lower
    bound 3.97% is actually *below* baseline — so gate_5batch would REJECT.

    Args:
        aggregate:      Output of aggregate_5batch().
        baseline:       {metric: baseline_value} — Phase D 5-batch is the
                        canonical baseline for EverMemBench comparisons.
        gate_threshold: Minimum mean delta above baseline required to ship
                        (default 0.0 = any positive improvement passes).

    Returns:
        Mapping from metric name to::
            {
                "ship":           bool,
                "mean_delta":     float,    # mean - baseline
                "ci_lower_delta": float,    # ci_lower_95 - baseline (or None)
                "verdict":        str,      # "SHIP" | "REJECT" | "NO_BASELINE" | "NO_CI"
                "mean":           float,
                "ci_lower_95":    float | None,
                "ci_upper_95":    float | None,
                "baseline":       float | None,
            }
    """
    gate_result: dict[str, dict[str, Any]] = {}

    for metric, stats in aggregate.items():
        base = baseline.get(metric)
        mean = stats["mean"]
        ci_lower = stats.get("ci_lower_95")
        ci_upper = stats.get("ci_upper_95")

        if base is None:
            gate_result[metric] = {
                "ship": False,
                "mean_delta": None,
                "ci_lower_delta": None,
                "verdict": "NO_BASELINE",
                "mean": mean,
                "ci_lower_95": ci_lower,
                "ci_upper_95": ci_upper,
                "baseline": None,
            }
            continue

        mean_delta = mean - base

        if ci_lower is None:
            # Single batch — cannot compute CI
            gate_result[metric] = {
                "ship": False,
                "mean_delta": mean_delta,
                "ci_lower_delta": None,
                "verdict": "NO_CI",
                "mean": mean,
                "ci_lower_95": None,
                "ci_upper_95": ci_upper,
                "baseline": base,
            }
            continue

        ci_lower_delta = ci_lower - base
        ships = (mean_delta > gate_threshold) and (ci_lower_delta > gate_threshold)

        gate_result[metric] = {
            "ship": ships,
            "mean_delta": mean_delta,
            "ci_lower_delta": ci_lower_delta,
            "verdict": "SHIP" if ships else "REJECT",
            "mean": mean,
            "ci_lower_95": ci_lower,
            "ci_upper_95": ci_upper,
            "baseline": base,
        }

    return gate_result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _t_crit_for_n(n: int) -> float:
    """Return two-tailed 95% CI t critical value for sample size n (dof=n-1).

    Values from standard t-table. Falls back to normal approximation (1.96)
    for n >= 30.
    """
    _TABLE = {
        2: 12.706,
        3: 4.303,
        4: 3.182,
        5: 2.776,
        6: 2.571,
        7: 2.447,
        8: 2.365,
        9: 2.306,
        10: 2.262,
        15: 2.131,
        20: 2.086,
        25: 2.060,
    }
    if n in _TABLE:
        return _TABLE[n]
    if n >= 30:
        return 1.960  # Normal approximation
    # Linear interpolation for intermediate n not in table (rough)
    keys = sorted(_TABLE.keys())
    for i in range(len(keys) - 1):
        if keys[i] < n < keys[i + 1]:
            lo, hi = keys[i], keys[i + 1]
            t_lo, t_hi = _TABLE[lo], _TABLE[hi]
            frac = (n - lo) / (hi - lo)
            return t_lo + frac * (t_hi - t_lo)
    return 1.960
