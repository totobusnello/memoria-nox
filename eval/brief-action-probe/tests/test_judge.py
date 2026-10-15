import unittest
from probe.judge import parse_verdict, score, corrupt, render_candidate


def m(name, inp, text=""):
    return {"text": text, "tool_calls": [{"name": name, "input": inp}]}


class JudgeTest(unittest.TestCase):
    def test_parse_verdict(self):
        self.assertEqual(parse_verdict({"winner": "A"}), "A")
        self.assertEqual(parse_verdict({"winner": "tie"}), "tie")
        self.assertEqual(parse_verdict({"winner": "both"}), "tie")

    def test_score(self):
        self.assertEqual(score("B1", "B1"), 1.0)
        self.assertEqual(score(None, "B1"), 0.5)
        self.assertEqual(score("B0", "B1"), 0.0)

    def test_corrupt_path(self):
        out, op = corrupt(m("Read", {"file_path": "/root/x/report.md"}), "path", ["Read", "Bash"], {})
        self.assertEqual(op, "path")
        self.assertEqual(out["tool_calls"][0]["input"]["file_path"], "/root/x/nonexistent-report.md")

    def test_corrupt_tool_and_required_and_fallback(self):
        out, op = corrupt(m("Read", {"file_path": "/a"}), "tool", ["Bash", "Read", "Write"], {})
        self.assertEqual((op, out["tool_calls"][0]["name"]), ("tool", "Write"))
        out, op = corrupt(m("Read", {"file_path": "/a", "limit": 3}), "required", ["Read"], {"required_args": ["limit"]})
        self.assertNotIn("limit", out["tool_calls"][0]["input"])
        out, op = corrupt(m("Bash", {"command": "ls"}), "path", ["Bash", "Read"], {})
        self.assertEqual(op, "tool")  # no path to corrupt -> next operator in the cycle

    def test_render_candidate_truncates(self):
        self.assertLessEqual(len(render_candidate({"text": "x" * 9000, "tool_calls": []})), 4100)


if __name__ == "__main__":
    unittest.main()
