import unittest
from probe.stats import (stratum_estimate, cluster_bootstrap, one_sided_p, percentile_ci, holm,
                         fisher_2x2, tost_proportion, simulate_mde, mde_from_curve)


class StatsTest(unittest.TestCase):
    def test_estimate_weighs_each_cluster_once(self):
        self.assertAlmostEqual(stratum_estimate({"a": [1.0, 1.0, 1.0, 1.0], "b": [0.0]}), 0.5)

    def test_bootstrap_is_seeded_and_bounded(self):
        d1 = cluster_bootstrap({"a": [0.2], "b": [0.4]}, 500, seed=7)
        self.assertEqual(d1, cluster_bootstrap({"a": [0.2], "b": [0.4]}, 500, seed=7))
        self.assertTrue(all(0.2 <= x <= 0.4 for x in d1))

    def test_one_sided_p(self):
        self.assertAlmostEqual(one_sided_p([1.0] * 99), 1 / 100)
        self.assertAlmostEqual(one_sided_p([-1.0] * 99), 1.0)

    def test_percentile_ci(self):
        lo, hi = percentile_ci([float(i) for i in range(101)])
        self.assertEqual((lo, hi), (2.0, 98.0))

    def test_holm_matches_hand_computation(self):
        adj = holm({"a": 0.01, "b": 0.04, "c": 0.03, "d": 1.0})
        self.assertAlmostEqual(adj["a"], 0.04)
        self.assertAlmostEqual(adj["c"], 0.09)
        self.assertAlmostEqual(adj["b"], 0.09)  # monotone: max(0.08, 0.09)
        self.assertAlmostEqual(adj["d"], 1.0)

    def test_fisher_two_sided_known_value(self):
        # Classic tea-tasting table [[3,1],[1,3]]: two-sided p = 0.4857
        self.assertAlmostEqual(fisher_2x2(3, 1, 1, 3), 0.4857, places=4)
        self.assertAlmostEqual(fisher_2x2(0, 10, 0, 10), 1.0)

    def test_tost(self):
        self.assertTrue(tost_proportion(250, 500)[0])
        self.assertFalse(tost_proportion(300, 500)[0])
        self.assertFalse(tost_proportion(10, 20)[0])

    def test_mde_simulation_moves_with_q(self):
        units = [[(u, r) for r in range(4)] for u in range(6)]
        dist = lambda x, y: 0.0 if x[0] == y[0] else 1.0
        curve = simulate_mde(units, dist, [3, 3, 3, 3], [0.0, 1.0], n_sim=40, n_boot=200, seed=1)
        self.assertAlmostEqual(curve[0]["mean_delta"], 0.0)
        self.assertLess(curve[0]["power"], 0.2)
        self.assertAlmostEqual(curve[1]["mean_delta"], 1.0)
        self.assertEqual(curve[1]["power"], 1.0)
        self.assertAlmostEqual(mde_from_curve(curve), 1.0)
        self.assertIsNone(mde_from_curve([{"q": 0, "mean_delta": 0.0, "power": 0.1}]))


if __name__ == "__main__":
    unittest.main()
