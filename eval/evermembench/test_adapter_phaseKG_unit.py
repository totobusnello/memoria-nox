"""Unit tests for Phase KG helpers — no DB or network required.

Validates pure logic of regex entity extraction.
Tested via plain `python3 -m unittest`.
"""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from adapter_nox_mem import _kg_extract_query_entities  # noqa: E402


class TestEntityExtraction(unittest.TestCase):
    def setUp(self):
        # (id, lowercased name) pool typical of an EverMemBench KG
        self.pool = (
            (1, "weihua zhang"),
            (2, "mingzhi li"),
            (3, "weihua"),
            (4, "group 1"),
            (5, "project"),
            (6, "boss zhang"),
            (7, "yu"),  # short — will be filtered if min_name_len > 2
        )

    def test_match_full_name(self):
        result = _kg_extract_query_entities(
            "What did Weihua Zhang say in the meeting?", self.pool
        )
        ids = [r[0] for r in result]
        # Should pick up id=1 "weihua zhang" AND id=3 "weihua" (substring)
        self.assertIn(1, ids)
        self.assertIn(3, ids)

    def test_no_match_for_unknown_entity(self):
        result = _kg_extract_query_entities(
            "Random unknown term xyz123", self.pool
        )
        self.assertEqual(result, [])

    def test_max_entities_caps(self):
        # Query that mentions many entities → cap respected
        result = _kg_extract_query_entities(
            "weihua zhang mingzhi li project group 1 boss zhang weihua",
            self.pool,
            max_entities=3,
        )
        self.assertLessEqual(len(result), 3)

    def test_word_boundary_avoids_partial_match(self):
        # "of" should NOT match "boss zhang" or similar
        result = _kg_extract_query_entities(
            "What is the topic of conversation?", self.pool
        )
        # No entity name appears in "of" — should be empty
        self.assertEqual(result, [])

    def test_case_insensitive(self):
        # All caps query — should still match
        result1 = _kg_extract_query_entities("WEIHUA ZHANG TALKED", self.pool)
        result2 = _kg_extract_query_entities("Weihua Zhang talked", self.pool)
        ids1 = sorted([r[0] for r in result1])
        ids2 = sorted([r[0] for r in result2])
        self.assertEqual(ids1, ids2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
