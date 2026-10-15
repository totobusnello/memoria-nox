import unittest
from probe.llm import extract_json, build_catalog_guard


class LlmTest(unittest.TestCase):
    def test_extract_json_from_fenced_or_bare(self):
        self.assertEqual(extract_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(extract_json('text before [1, 2] after'), [1, 2])
        with self.assertRaises(ValueError):
            extract_json("no json here")

    def test_catalog_guard_rejects_brief_content(self):
        build_catalog_guard("cron prompt about the digest")
        for bad in ("item (chk 12345)", "# nox-mem brief — scope=global", "AUTO-GERADO por nox-mem-brief-refresh"):
            with self.assertRaises(AssertionError):
                build_catalog_guard(bad)


if __name__ == "__main__":
    unittest.main()
