import unittest
from probe_analyze import unit_deltas, decide  # scripts/analyze.py is importable as probe_analyze via the test shim

M = lambda t: {"text": t, "tool_calls": []}


class AnalyzeTest(unittest.TestCase):
    def test_unit_deltas_needs_all_six_runs(self):
        msgs = {(a, r): M("same words here") for a in ("B0", "B1", "BS") for r in (1, 2)}
        d = unit_deltas(msgs)
        self.assertEqual((d["dp"], d["dc"]), (0.0, 0.0))
        del msgs[("BS", 2)]
        self.assertIsNone(unit_deltas(msgs))

    def test_presence_effect_detected_and_holm_family_of_four(self):
        by = {"C": {"dp": {f"c{i}": [0.4] for i in range(12)}, "dc": {f"c{i}": [0.0] for i in range(12)}},
              "H": {"dp": {f"h{i}": [0.0] for i in range(12)}, "dc": {f"h{i}": [0.0] for i in range(12)}}}
        params = {"valid": {"C": True, "H": True}, "mde": {"C": 0.1, "H": 0.1}}
        out = decide(by, params, inconclusive=set())
        self.assertTrue(out["C"]["dp"]["effect"])
        self.assertFalse(out["C"]["dc"]["effect"])
        self.assertEqual(len(out["holm"]), 4)

    def test_invalid_stratum_has_no_delta_and_p_one(self):
        by = {"C": {"dp": {"c": [0.4]}, "dc": {"c": [0.4]}}, "H": {"dp": {"h": [0.0]}, "dc": {"h": [0.0]}}}
        out = decide(by, {"valid": {"C": False, "H": True}, "mde": {"C": 0.1, "H": 0.1}}, inconclusive=set())
        self.assertEqual(out["C"], {"invalid": True})
        self.assertEqual(out["holm_raw"]["C.dp"], 1.0)

    def test_inconclusive_contrast_gets_p_one(self):
        by = {"C": {"dp": {f"c{i}": [0.4] for i in range(12)}, "dc": {f"c{i}": [0.4] for i in range(12)}},
              "H": {"dp": {"h": [0.0]}, "dc": {"h": [0.0]}}}
        out = decide(by, {"valid": {"C": True, "H": True}, "mde": {"C": 0.1, "H": 0.1}}, inconclusive={"C.dc"})
        self.assertEqual(out["holm_raw"]["C.dc"], 1.0)
        self.assertTrue(out["C"]["dc"]["inconclusive"])

    def test_null_reading_branches(self):
        by = {"C": {"dp": {f"c{i}": [0.0] for i in range(12)}, "dc": {f"c{i}": [0.0] for i in range(12)}},
              "H": {"dp": {"h": [0.0]}, "dc": {"h": [0.0]}}}
        out = decide(by, {"valid": {"C": True, "H": True}, "mde": {"C": 0.05, "H": 0.05}}, inconclusive=set())
        self.assertEqual(out["C"]["dp"]["null_reading"], "effects >= MDE excluded")


if __name__ == "__main__":
    unittest.main()
