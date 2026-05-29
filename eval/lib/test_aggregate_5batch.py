"""eval/lib/test_aggregate_5batch.py — Tests for aggregate_5batch.py.

Uses synthetic data from Phase G 5-batch (RESULTS-PHASEG-5BATCH.md per-batch
detail table) to validate CI computation and gate logic.

Run:
    python -m pytest eval/lib/test_aggregate_5batch.py -v
  or:
    python eval/lib/test_aggregate_5batch.py
"""

from __future__ import annotations

import math
import sys
import unittest

# Allow running from repo root without install
sys.path.insert(0, ".")

from eval.lib.aggregate_5batch import aggregate_5batch, gate_5batch, REQUIRED_DIMS


# ---------------------------------------------------------------------------
# Fixtures — Phase G 5-batch per-batch table (RESULTS-PHASEG-5BATCH.md)
# ---------------------------------------------------------------------------

PHASE_G_PER_BATCH: dict[str, dict[str, float]] = {
    "004": {
        "overall": 59.74,
        "F_MH": 10.00,
        "F_SH": 79.59,
        "F_TP": 31.67,
        "MA_C": 68.00,
        "MA_P": 76.00,
        "MA_U": 82.76,
        "P_Skill": 62.22,
        "P_Style": 51.35,
        "P_Title": 73.47,
    },
    "005": {
        "overall": 63.44,
        "F_MH": 4.00,
        "F_SH": 78.00,
        "F_TP": 28.33,
        "MA_C": 85.00,
        "MA_P": 82.00,
        "MA_U": 87.27,
        "P_Skill": 60.47,
        "P_Style": 35.71,
        "P_Title": 71.43,
    },
    "010": {
        "overall": 60.67,
        "F_MH": 6.00,
        "F_SH": 70.00,
        "F_TP": 26.67,
        "MA_C": 78.00,
        "MA_P": 81.00,
        "MA_U": 74.14,
        "P_Skill": 67.39,
        "P_Style": 48.39,
        "P_Title": 62.00,
    },
    "011": {
        "overall": 60.19,
        "F_MH": 6.00,
        "F_SH": 84.00,
        "F_TP": 21.67,
        "MA_C": 76.00,
        "MA_P": 79.00,
        "MA_U": 85.19,
        "P_Skill": 53.49,
        "P_Style": 37.50,
        "P_Title": 70.00,
    },
    "016": {
        "overall": 62.32,
        "F_MH": 8.16,
        "F_SH": 77.08,
        "F_TP": 31.67,
        "MA_C": 80.00,
        "MA_P": 83.00,
        "MA_U": 77.42,
        "P_Skill": 52.27,
        "P_Style": 51.35,
        "P_Title": 62.00,
    },
}

# Phase D 5-batch baseline (RESULTS-PATHB-FULL.md headline)
PHASE_D_BASELINE: dict[str, float] = {
    "overall": 62.22,
    "F_MH": 5.22,
    "F_SH": 77.33,
    "F_TP": 26.00,
    "MA_C": 81.40,
    "MA_P": 83.00,
    "MA_U": 85.02,
    "P_Skill": 60.63,
    "P_Style": 46.96,
    "P_Title": 67.34,
}


class TestAggregateBasics(unittest.TestCase):
    def setUp(self) -> None:
        self.agg = aggregate_5batch(PHASE_G_PER_BATCH)

    def test_overall_mean(self) -> None:
        """Phase G 5-batch overall mean == 61.27 (per RESULTS-PHASEG-5BATCH.md)."""
        mean = self.agg["overall"]["mean"]
        self.assertAlmostEqual(mean, 61.272, places=1)

    def test_f_mh_mean(self) -> None:
        """Phase G F_MH mean == 6.83% (per RESULTS-PHASEG-5BATCH.md)."""
        mean = self.agg["F_MH"]["mean"]
        self.assertAlmostEqual(mean, 6.832, places=1)

    def test_f_mh_stdev(self) -> None:
        """Phase G F_MH stdev == 2.30 pp (per RESULTS-PHASEG-5BATCH.md)."""
        stdev = self.agg["F_MH"]["stdev"]
        self.assertAlmostEqual(stdev, 2.30, places=1)

    def test_f_mh_ci_lower(self) -> None:
        """Phase G F_MH 95% CI lower bound == 3.97% (per RESULTS-PHASEG-5BATCH.md)."""
        ci_lower = self.agg["F_MH"]["ci_lower_95"]
        self.assertAlmostEqual(ci_lower, 3.97, places=0)

    def test_f_mh_ci_upper(self) -> None:
        """Phase G F_MH 95% CI upper bound == 9.69% (per RESULTS-PHASEG-5BATCH.md)."""
        ci_upper = self.agg["F_MH"]["ci_upper_95"]
        self.assertAlmostEqual(ci_upper, 9.69, places=0)

    def test_n_equals_five(self) -> None:
        for metric, stats in self.agg.items():
            self.assertEqual(stats["n"], 5, f"Expected n=5 for {metric}")

    def test_per_batch_preserved(self) -> None:
        """per_batch dict must contain all 5 batch ids."""
        self.assertEqual(
            set(self.agg["F_MH"]["per_batch"].keys()),
            {"004", "005", "010", "011", "016"},
        )

    def test_all_metrics_present(self) -> None:
        """All metrics from the fixture should appear in aggregate output."""
        expected = set(PHASE_G_PER_BATCH["004"].keys())
        actual = set(self.agg.keys())
        self.assertEqual(expected, actual)

    def test_empty_input(self) -> None:
        self.assertEqual(aggregate_5batch({}), {})


class TestAggregateEdgeCases(unittest.TestCase):
    def test_single_batch_no_ci(self) -> None:
        """Single-batch input should have stdev=None and ci=None."""
        agg = aggregate_5batch({"004": {"F_MH": 10.0}})
        stats = agg["F_MH"]
        self.assertIsNone(stats["stdev"])
        self.assertIsNone(stats["ci_lower_95"])
        self.assertIsNone(stats["ci_upper_95"])
        self.assertAlmostEqual(stats["mean"], 10.0)

    def test_two_batch_has_ci(self) -> None:
        """Two batches should produce finite CI (dof=1, t_crit=12.706)."""
        agg = aggregate_5batch({"004": {"F_MH": 10.0}, "005": {"F_MH": 4.0}})
        stats = agg["F_MH"]
        self.assertIsNotNone(stats["ci_lower_95"])
        self.assertIsNotNone(stats["ci_upper_95"])
        # Mean should be 7.0
        self.assertAlmostEqual(stats["mean"], 7.0)

    def test_metric_missing_in_one_batch(self) -> None:
        """Metric missing from one batch should aggregate only present batches."""
        data = {
            "004": {"F_MH": 10.0, "overall": 59.74},
            "005": {"overall": 63.44},           # F_MH absent
        }
        agg = aggregate_5batch(data)
        self.assertEqual(agg["F_MH"]["n"], 1)
        self.assertEqual(agg["overall"]["n"], 2)


class TestGate5Batch(unittest.TestCase):
    def setUp(self) -> None:
        self.agg = aggregate_5batch(PHASE_G_PER_BATCH)

    def test_overall_gate_reject(self) -> None:
        """Phase G overall mean (61.27) < Phase D baseline (62.22) → REJECT."""
        gate = gate_5batch(self.agg, PHASE_D_BASELINE)
        self.assertEqual(gate["overall"]["verdict"], "REJECT")
        self.assertFalse(gate["overall"]["ship"])

    def test_f_mh_gate_reject(self) -> None:
        """Phase G F_MH CI lower (3.97) < Phase D baseline (5.22) → REJECT.

        This is the key lesson from [[single-batch-gates-unreliable-5x-overstate]]:
        batch 004's single point (10.0%) would pass a >5.22% gate, but the
        5-batch CI lower bound (3.97%) is below baseline — gate correctly rejects.
        """
        gate = gate_5batch(self.agg, PHASE_D_BASELINE)
        self.assertEqual(gate["F_MH"]["verdict"], "REJECT")
        self.assertFalse(gate["F_MH"]["ship"])

    def test_single_batch_would_naively_pass(self) -> None:
        """Demonstrate that single-batch 10.0% F_MH would pass a naive >5.22% gate,
        but gate_5batch rejects because CI lower bound < baseline."""
        # Single batch "004" only
        agg_single = aggregate_5batch({"004": {"F_MH": 10.0}})
        gate_single = gate_5batch(agg_single, {"F_MH": 5.22})
        # Single batch → NO_CI verdict (cannot compute CI with n=1)
        self.assertEqual(gate_single["F_MH"]["verdict"], "NO_CI")
        self.assertFalse(gate_single["F_MH"]["ship"])

    def test_gate_threshold_positive(self) -> None:
        """gate_threshold > 0 requires mean delta to exceed threshold."""
        # Use a synthetic metric where mean > baseline but barely
        agg = aggregate_5batch({
            "a": {"x": 11.0},
            "b": {"x": 11.0},
            "c": {"x": 11.0},
            "d": {"x": 11.0},
            "e": {"x": 11.0},
        })
        # baseline=10.0, threshold=0.5 → mean_delta=1.0 > 0.5 → SHIP
        gate = gate_5batch(agg, {"x": 10.0}, gate_threshold=0.5)
        self.assertEqual(gate["x"]["verdict"], "SHIP")
        self.assertTrue(gate["x"]["ship"])

    def test_gate_no_baseline(self) -> None:
        """Metrics with no baseline in the baseline dict get NO_BASELINE verdict."""
        gate = gate_5batch(self.agg, {})  # empty baseline
        for metric in self.agg:
            self.assertEqual(gate[metric]["verdict"], "NO_BASELINE")
            self.assertFalse(gate[metric]["ship"])

    def test_gate_delta_sign(self) -> None:
        """mean_delta should equal mean - baseline."""
        gate = gate_5batch(self.agg, PHASE_D_BASELINE)
        for metric, stats in gate.items():
            if stats.get("baseline") is not None:
                expected_delta = stats["mean"] - stats["baseline"]
                self.assertAlmostEqual(stats["mean_delta"], expected_delta, places=5)


class TestRequiredDims(unittest.TestCase):
    def test_required_dims_in_phase_g(self) -> None:
        """Phase G fixture must cover all REQUIRED_DIMS."""
        agg = aggregate_5batch(PHASE_G_PER_BATCH)
        # REQUIRED_DIMS except F_HL (not in Phase G fixture)
        required = set(REQUIRED_DIMS) - {"F_HL"}
        missing = required - set(agg.keys())
        self.assertEqual(missing, set(), f"Missing required dims: {missing}")


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
