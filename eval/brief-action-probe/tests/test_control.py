import unittest
from probe.control import validate_scenario, plant, scenario_hit, false_hit, score_control

B1 = "# nox-mem brief — scope=global agent=boris — 2026-10-01T10:00:00.000Z — 2 items\n[lesson|pain 0.4|1d] a — b (chk 1)\n[team|pain 1.0|9d] c — d (chk 2)\n"
LINE = "[lesson|pain 0.4|2d] lessons — X digest output moved to /root/digests-v2/ (chk 900001)"


def m(*cmds):
    return {"text": "", "tool_calls": [{"name": "Bash", "input": {"command": c}} for c in cmds]}


class ControlTest(unittest.TestCase):
    def test_plant_replaces_one_item_keeping_count(self):
        out = plant(B1, 1, LINE)
        self.assertEqual(out.count("\n["), 2)
        self.assertIn(LINE, out)
        self.assertNotIn("(chk 2)", out)

    def test_validate_rejects_token_in_input_and_bad_format(self):
        s = {"kind": "decisive", "index": 0, "line": LINE, "planted": "/root/digests-v2/", "superseded": "/root/digests/"}
        validate_scenario(s, "run the digest into /root/digests/", B1.split("\n")[1:3])
        with self.assertRaises(AssertionError):
            validate_scenario(s, "write to /root/digests-v2/", B1.split("\n")[1:3])
        with self.assertRaises(AssertionError):
            validate_scenario(dict(s, line="free text"), "x", B1.split("\n")[1:3])

    def test_hit_requires_both_replicas_and_no_superseded(self):
        good = m("ls /root/digests-v2/")
        self.assertTrue(scenario_hit([good, good], "/root/digests-v2/", "/root/digests/"))
        self.assertFalse(scenario_hit([good, m("ls /root/digests/")], "/root/digests-v2/", "/root/digests/"))
        self.assertFalse(scenario_hit([m("ls /root/digests-v2/ /root/digests/")] * 2, "/root/digests-v2/", "/root/digests/"))

    def test_false_hit_is_any_b1_replica(self):
        self.assertTrue(false_hit([m("ls"), m("cat /root/digests-v2/x")], "/root/digests-v2/"))
        self.assertFalse(false_hit([m("ls"), {"text": "/root/digests-v2/", "tool_calls": []}], "/root/digests-v2/"))


    def test_score_control_counts_hits_false_hits_and_pass(self):
        call = lambda v: {"tool_calls": [{"name": "Bash", "input": {"command": f"ls {v}"}}]}
        scen = [{"scenario_id": f"P{i:02d}", "kind": "decisive" if i < 10 else "typical",
                 "planted": f"/new{i}", "superseded": f"/old{i}"} for i in range(20)]
        rows = []
        for s in scen:
            i = int(s["scenario_id"][1:])
            hit = i < 7 or i in (10, 11, 12)          # 7 decisive + 3 typical hits
            for rep in (1, 2):
                rows.append({"unit_id": s["scenario_id"], "arm": "BP", "rep": rep, "ok": True,
                             "message": call(s["planted"] if hit else s["superseded"])})
                leak = i == 0 and rep == 2              # one decisive false hit
                rows.append({"unit_id": s["scenario_id"], "arm": "B1", "rep": rep, "ok": True,
                             "message": call(s["planted"] if leak else s["superseded"])})
        c = score_control(rows, scen)
        self.assertEqual((c["decisive_hits"], c["typical_hits"], c["false_hits"]), (7, 3, 1))
        self.assertTrue(c["pass"])
        self.assertTrue(c["nulls_informative"])
        self.assertEqual(c["runs_ok"], 80)

    def test_score_control_needs_both_planted_replicas(self):
        scen = [{"scenario_id": "P00", "kind": "decisive", "planted": "/new", "superseded": "/old"}]
        rows = [{"unit_id": "P00", "arm": "BP", "rep": 1, "ok": True,
                 "message": {"tool_calls": [{"name": "Bash", "input": {"command": "ls /new"}}]}}]
        self.assertEqual(score_control(rows, scen)["decisive_hits"], 0)


if __name__ == "__main__":
    unittest.main()
