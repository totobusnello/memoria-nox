import json
import unittest
from probe.runner import build_cmd, parse_first_message, is_rate_limited, hook_mismatch, probe_env, RateLimited, run_unit


def ev(mid, blocks, typ="assistant"):
    return json.dumps({"type": typ, "message": {"id": mid, "content": blocks}})


class RunnerTest(unittest.TestCase):
    def test_cmd_mirrors_production_flags(self):
        c = build_cmd("/x/B1.md")
        for flag in ("-p", "--output-format", "stream-json", "--verbose", "--setting-sources", "user",
                     "--allowedTools", "mcp__openclaw__*", "--disallowedTools",
                     "ScheduleWakeup,CronCreate,Bash(run_in_background:true),Monitor",
                     "--append-system-prompt-file", "/x/B1.md", "--max-turns", "1", "--strict-mcp-config"):
            self.assertIn(flag, c)
        self.assertEqual(c[c.index("--model") + 1], "claude-sonnet-5")

    def test_parse_merges_blocks_of_first_message_only(self):
        out = "\n".join([
            json.dumps({"type": "system", "subtype": "init"}),
            ev("m1", [{"type": "thinking", "thinking": "hmm"}]),
            ev("m1", [{"type": "text", "text": "Vou olhar."}]),
            ev("m1", [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "ls"}}]),
            ev("m1", [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "ls"}}]),
            ev("m2", [{"type": "text", "text": "second message"}]),
        ])
        m = parse_first_message(out)
        self.assertEqual(m["text"], "Vou olhar.")
        self.assertEqual(m["tool_calls"], [{"name": "Bash", "input": {"command": "ls"}}])

    def test_no_assistant_message_is_none_not_empty(self):
        self.assertIsNone(parse_first_message(json.dumps({"type": "result", "is_error": True})))
        self.assertIsNone(parse_first_message(""))

    def test_rate_limit_detection(self):
        self.assertTrue(is_rate_limited("", "Claude AI usage limit reached|1760000000"))
        self.assertTrue(is_rate_limited('{"type":"result","result":"API Error: 429 rate_limit_error"}', ""))
        self.assertFalse(is_rate_limited("ok", ""))

    def test_hook_cross_check(self):
        msg = {"tool_calls": [{"name": "Bash", "input": {}}, {"name": "Read", "input": {}}]}
        self.assertFalse(hook_mismatch(msg, ["Bash", "Read"]))
        self.assertTrue(hook_mismatch(msg, ["Bash"]))
        self.assertTrue(hook_mismatch({"tool_calls": []}, ["Bash"]))


    def test_probe_env_uses_token_and_isolated_dir_and_drops_anthropic_vars(self):
        env = probe_env({"ANTHROPIC_MAX_API_KEY": "x", "ANTHROPIC_API_KEY": "y", "PATH": "/bin"}, "/h.jsonl", "tok")
        self.assertEqual(env["CLAUDE_CODE_OAUTH_TOKEN"], "tok")
        self.assertEqual(env["CLAUDE_CONFIG_DIR"], "/root/.claude-7b-probe")
        self.assertEqual(env["PROBE_HOOK_LOG"], "/h.jsonl")
        self.assertNotIn("ANTHROPIC_MAX_API_KEY", env)
        self.assertNotIn("ANTHROPIC_API_KEY", env)
        self.assertEqual(env["PATH"], "/bin")

    def test_rate_limit_stops_the_unit(self):
        import random, probe.runner as r
        calls = []
        orig = r.run_arm
        r.run_arm = lambda *a, **k: calls.append(1) or {"ok": False, "rate_limited": True, "message": None,
                                                         "returncode": 1, "hook_calls": [], "hook_mismatch": False}
        try:
            with self.assertRaises(RateLimited):
                run_unit("u", {"B1": "/x"}, "in", "/", "/tmp/r", 2, random.Random(1), token="t")
        finally:
            r.run_arm = orig
        self.assertEqual(len(calls), 1)

if __name__ == "__main__":
    unittest.main()
