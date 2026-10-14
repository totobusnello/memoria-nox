import unittest
from probe.canon import serialize, divergence, canon_bash, MAX_TOKENS


def msg(text="", calls=()):
    return {"text": text, "tool_calls": [{"name": n, "input": i} for n, i in calls]}


class CanonTest(unittest.TestCase):
    def test_identical_messages_have_zero_divergence(self):
        m = msg("hello", [("Bash", {"command": "ls -la /root"})])
        self.assertEqual(divergence(serialize(m), serialize(m)), 0.0)

    def test_both_empty_is_zero_and_one_empty_is_one(self):
        self.assertEqual(divergence([], []), 0.0)
        self.assertEqual(divergence(serialize(msg("x")), []), 1.0)

    def test_dates_times_uuids_hashes_and_tmp_paths_are_masked(self):
        a = msg("", [("Bash", {"command": "cat /tmp/abc.1/x 2026-10-14T23:00:05Z 12:30 0123456789abcdef 3f2a9c1e-1111-2222-3333-444455556666"})])
        b = msg("", [("Bash", {"command": "cat /tmp/zz9/y 2025-01-02T08:00:00Z 09:15 fedcba9876543210 00000000-aaaa-bbbb-cccc-dddddddddddd"})])
        self.assertEqual(serialize(a), serialize(b))

    def test_bash_option_order_is_canonical(self):
        self.assertEqual(canon_bash("grep -n -i foo file"), canon_bash("grep -i -n foo file"))
        self.assertNotEqual(canon_bash("cp a b"), canon_bash("cp b a"))

    def test_bash_description_is_ignored(self):
        a = msg("", [("Bash", {"command": "ls", "description": "list files"})])
        b = msg("", [("Bash", {"command": "ls", "description": "show me the directory"})])
        self.assertEqual(serialize(a), serialize(b))

    def test_unparseable_shell_falls_back_without_raising(self):
        out = canon_bash("cat <<'EOF'\nit's open\n")
        self.assertIsInstance(out, str)
        self.assertEqual(out, canon_bash("cat <<'EOF'\nit's open\n"))

    def test_json_arguments_are_key_order_insensitive(self):
        a = msg("", [("Read", {"file_path": "/x", "limit": 5})])
        b = msg("", [("Read", {"limit": 5, "file_path": "/x"})])
        self.assertEqual(serialize(a), serialize(b))

    def test_call_order_matters(self):
        a = msg("", [("Read", {"file_path": "/a"}), ("Read", {"file_path": "/b"})])
        b = msg("", [("Read", {"file_path": "/b"}), ("Read", {"file_path": "/a"})])
        self.assertGreater(divergence(serialize(a), serialize(b)), 0.0)

    def test_unicode_text_tokenizes(self):
        self.assertIn("ação", serialize(msg("Vou checar a ação agora")))

    def test_sequence_is_truncated(self):
        self.assertEqual(len(serialize(msg("w " * 5000))), MAX_TOKENS)

    def test_divergence_is_normalized_levenshtein(self):
        self.assertAlmostEqual(divergence(["a", "b", "c", "d"], ["a", "x", "c", "d"]), 0.25)
        self.assertEqual(divergence(["a"], ["b"]), 1.0)


if __name__ == "__main__":
    unittest.main()
