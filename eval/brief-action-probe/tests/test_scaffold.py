import unittest
from probe.scaffold import parse_template, build_prompt, strip_brief, assert_only_brief_differs

TPL = "\n".join([
    "## Tooling", "x", "## Workspace", "Working directory: /root/.openclaw/workspace/agents/forge",
    "# Project Context",
    "## /root/.openclaw/workspace/agents/forge/AGENTS.md", "agents body", "## Rules",
    "## /root/.openclaw/workspace/agents/forge/brief/MEMORY.md", "old brief",
    "## /root/.openclaw/workspace/agents/forge/MEMORY.md", "memory body",
    "## Temporal Context", "Current date: 2026-09-30", "## Conversation Context", "discord stuff",
    "## Runtime", "Runtime: agent=forge | session=agent:forge:discord:channel:1 | sessionId=abc",
    "Current model identity: claude-cli/claude-sonnet-5.",
])


class ScaffoldTest(unittest.TestCase):
    def test_parse(self):
        t = parse_template(TPL)
        self.assertEqual([p.rsplit("/", 1)[-1] for p, _ in t["sections"]], ["AGENTS.md", "MEMORY.md", "MEMORY.md"])
        self.assertEqual(t["tail"][0], "## Temporal Context")

    def test_build_for_other_agent_and_date(self):
        t = parse_template(TPL)
        out = build_prompt(t, "boris", {"AGENTS.md": "B agents", "MEMORY.md": "B mem"}, "BRIEF", "2026-10-02", False)
        self.assertIn("Working directory: /root/.openclaw/workspace/agents/boris", out)
        self.assertIn("## /root/.openclaw/workspace/agents/boris/brief/MEMORY.md\nBRIEF", out)
        self.assertIn("Current date: 2026-10-02", out)
        self.assertNotIn("discord stuff", out)
        self.assertIn("Runtime: agent=boris | host=openclaw", out)
        self.assertNotIn("old brief", out)

    def test_main_uses_workspace_root(self):
        out = build_prompt(parse_template(TPL), "main", {"AGENTS.md": "M"}, None, "2026-10-02", False)
        self.assertIn("## /root/.openclaw/workspace/AGENTS.md\nM", out)
        self.assertNotIn("brief/MEMORY.md", out)

    def test_only_brief_differs(self):
        t = parse_template(TPL)
        files = {"AGENTS.md": "A", "MEMORY.md": "M"}
        arms = {a: build_prompt(t, "boris", files, b, "2026-10-02", False)
                for a, b in (("B0", None), ("B1", "real"), ("BS", "sham"))}
        assert_only_brief_differs(arms, "boris")
        arms["BS"] = arms["BS"].replace("M\n", "M changed\n")
        with self.assertRaises(AssertionError):
            assert_only_brief_differs(arms, "boris")

    def test_strip_brief_removes_only_that_section(self):
        out = build_prompt(parse_template(TPL), "boris", {"AGENTS.md": "A", "MEMORY.md": "M"}, "real", "2026-10-02", False)
        s = strip_brief(out, "boris")
        self.assertNotIn("real", s)
        self.assertIn("## /root/.openclaw/workspace/agents/boris/MEMORY.md\nM", s)


    def test_blank_separator_before_tail_is_preserved(self):
        raw = TPL.replace("memory body\n## Temporal Context", "memory body\n\n\n## Temporal Context")
        t = parse_template(raw)
        files = {p.split("/agents/forge/", 1)[1]: c for p, c in t["sections"]}
        brief = files.pop("brief/MEMORY.md")
        out = build_prompt(t, "forge", files, brief, "2026-09-30", True)
        self.assertEqual(out.split("\n")[:-2], raw.split("\n")[:-2])

if __name__ == "__main__":
    unittest.main()
