import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class RuntimeTest(unittest.TestCase):
    def test_deny_hook_logs_and_denies(self):
        log = os.path.join(tempfile.mkdtemp(), "hook.jsonl")
        ev = {"tool_name": "Bash", "tool_input": {"command": "touch /tmp/should-not-exist"}}
        p = subprocess.run([sys.executable, os.path.join(HERE, "runtime", "deny_hook.py")], input=json.dumps(ev),
                           capture_output=True, text=True, env={**os.environ, "PROBE_HOOK_LOG": log})
        self.assertEqual(p.returncode, 0)
        out = json.loads(p.stdout)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(json.loads(open(log).read())["tool_name"], "Bash")

    def test_deny_hook_denies_even_on_garbage_input(self):
        p = subprocess.run([sys.executable, os.path.join(HERE, "runtime", "deny_hook.py")], input="not json",
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)

    def test_stub_mcp_lists_and_refuses(self):
        d = tempfile.mkdtemp()
        surface = os.path.join(d, "surface.json")
        json.dump({"openclaw": [{"name": "session_status", "description": "stub",
                                 "inputSchema": {"type": "object"}}]}, open(surface, "w"))
        reqs = "\n".join(json.dumps(r) for r in [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "session_status"}},
        ]) + "\n"
        p = subprocess.run([sys.executable, os.path.join(HERE, "runtime", "stub_mcp.py"), surface, "openclaw"],
                           input=reqs, capture_output=True, text=True, timeout=10)
        lines = [json.loads(l) for l in p.stdout.splitlines()]
        self.assertEqual([l["id"] for l in lines], [1, 2, 3])
        self.assertEqual(lines[1]["result"]["tools"][0]["name"], "session_status")
        self.assertTrue(lines[2]["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
