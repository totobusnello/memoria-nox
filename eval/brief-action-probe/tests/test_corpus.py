import json
import os
import tempfile
import unittest
from probe.corpus import classify, template_key, load_turns, evenly, build_strata


def line(ts, content, typ="user", uuid=None):
    return json.dumps({"type": typ, "timestamp": ts, "uuid": uuid, "message": {"content": content}})


class CorpusTest(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(classify("Read HEARTBEAT.md"), "heartbeat")
        self.assertEqual(classify("<task-notification> x"), "task-notification")
        self.assertEqual(classify("[cron:abc relatorio-eod] do it"), "auto")
        self.assertEqual(classify("[Inter-session message] sourceSession=..."), "inter-agent")
        self.assertEqual(classify('Conversation info: {"conversation_label":"#x"}'), "human")
        self.assertEqual(classify("plain"), "other")

    def test_template_key_ignores_dates_and_retry_prefix(self):
        a = template_key("main", "[Wed 2026-10-14 09:00 GMT-3] [cron:1 eod] run 2026-10-14 report 12345")
        b = template_key("main", "[Thu 2026-10-15 09:00 GMT-3] [Retry after the previous model attempt failed or timed out] [cron:1 eod] run 2026-10-15 report 99999")
        self.assertEqual(a, b)

    def test_load_turns_skips_tool_results_and_dedupes_retries(self):
        d = tempfile.mkdtemp()
        sub = os.path.join(d, "-root--openclaw-workspace-agents-boris")
        os.makedirs(sub)
        with open(os.path.join(sub, "s1.jsonl"), "w") as f:
            f.write(line("2026-10-01T10:00:00Z", "[cron:x digest] go", uuid="u1") + "\n")
            f.write(line("2026-10-01T10:00:05Z", [{"type": "tool_result", "content": "ok"}], uuid="u2") + "\n")
            f.write(line("2026-10-01T10:01:00Z", "[Retry after the previous model attempt failed or timed out] [cron:x digest] go", uuid="u3") + "\n")
            f.write(line("2026-10-01T10:02:00Z", [{"type": "text", "text": "Read HEARTBEAT.md"}], uuid="u4") + "\n")
            f.write("not json\n")
            f.write(line("2026-08-01T10:00:00Z", "[cron:old] out of window", uuid="u5") + "\n")
        turns = load_turns(d, "2026-09-21T00:00:00Z", "2026-10-15T00:00:00Z")
        self.assertEqual([(t["unit_id"], t["agent"], t["kind"]) for t in turns],
                         [("u1", "boris", "auto"), ("u4", "boris", "heartbeat")])

    def test_evenly(self):
        self.assertEqual(evenly(3, 8), [0, 1, 2])
        self.assertEqual(evenly(24, 8), [0, 3, 7, 10, 13, 16, 20, 23])

    def test_build_strata_caps_and_pilot_uses_surplus(self):
        turns = [{"unit_id": f"a{i}", "agent": "main", "ts": f"2026-10-{i + 1:02d}T00:00:00Z", "kind": "auto",
                  "template": "main|A", "text": "x"} for i in range(24)]
        turns += [{"unit_id": "h1", "agent": "forge", "ts": "2026-10-02T00:00:00Z", "kind": "human",
                   "template": "forge|H", "text": "y"}]
        s = build_strata(turns, cap=8, n_pilot=4, big=1, seed=3)
        self.assertEqual(len(s["C"]), 8)
        self.assertEqual([t["unit_id"] for t in s["R"]], ["h1"])
        self.assertEqual(len(s["pilot_C"]), 4)
        self.assertFalse({t["unit_id"] for t in s["pilot_C"]} & {t["unit_id"] for t in s["C"]})


if __name__ == "__main__":
    unittest.main()
