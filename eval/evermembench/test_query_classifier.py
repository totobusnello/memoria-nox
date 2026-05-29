"""Unit + smoke test for eval/evermembench/query_classifier.py.

Run via:
    python -m unittest eval.evermembench.test_query_classifier
    # or
    python eval/evermembench/test_query_classifier.py
"""
from __future__ import annotations

import time
import unittest

from eval.evermembench.query_classifier import (
    DEFAULT_THRESHOLD,
    classify_query,
)


class TestHeuristicClassifier(unittest.TestCase):
    """Spec PR #373 §2 Option A — score-based routing."""

    # ── Factual / single-hop queries (should score < 4) ────────────────────

    def test_factual_short(self):
        r = classify_query("What is the speed limit?")
        self.assertEqual(r.decision, "factual")
        self.assertLess(r.score, DEFAULT_THRESHOLD)

    def test_factual_who(self):
        r = classify_query("Who is Joe?")
        self.assertEqual(r.decision, "factual")

    def test_factual_lookup(self):
        # Single entity, no chain
        r = classify_query("What color is the door?")
        self.assertEqual(r.decision, "factual")

    # ── Multi-hop queries (should score >= 4) ──────────────────────────────

    def test_multi_hop_comparative(self):
        r = classify_query(
            "How does Acme Inc compare to Globex Co after the 2023 merger?"
        )
        self.assertEqual(r.decision, "multi_hop")
        self.assertGreaterEqual(r.score, DEFAULT_THRESHOLD)
        # Has comparative + token count > 10 + entity count >= 3
        self.assertTrue(r.features["has_comparative"])
        self.assertGreater(r.features["token_count"], 10)

    def test_multi_hop_explain(self):
        # Abstract reasoning + temporal chain + entities
        r = classify_query(
            "Explain why John switched teams after the 2024 reorg "
            "and how that affected Sarah's project."
        )
        self.assertEqual(r.decision, "multi_hop")
        self.assertTrue(r.features["has_abstract_reasoning"])

    def test_multi_hop_temporal_chain(self):
        # "before X happened" + multiple entities + token count
        r = classify_query(
            "Before the Lisbon office closed, what did Maria and Pedro "
            "agree about the budget?"
        )
        self.assertEqual(r.decision, "multi_hop")

    # ── PT-BR multi-hop ────────────────────────────────────────────────────

    def test_pt_br_comparative(self):
        r = classify_query(
            "Como se compara a Acme com a Globex depois da fusão em 2023?"
        )
        self.assertEqual(r.decision, "multi_hop")
        self.assertTrue(r.features["has_comparative"])

    def test_pt_br_abstract_reasoning(self):
        r = classify_query("Por que o Joao trocou de time depois da reorganização?")
        # has_abstract_reasoning (por que) + conjunction (depois) — may or may
        # not cross threshold depending on entity_count; assert features fire
        self.assertTrue(r.features["has_abstract_reasoning"])

    # ── Threshold tunability ───────────────────────────────────────────────

    def test_threshold_override_strict(self):
        # Same query — strict threshold pushes it to factual
        q = "What is the speed limit in 2024?"
        r_default = classify_query(q)
        r_strict = classify_query(q, threshold=10)
        # Stricter threshold should never raise score
        self.assertLessEqual(r_strict.score, r_default.score + 0)
        self.assertEqual(r_strict.decision, "factual")

    # ── Edge cases ─────────────────────────────────────────────────────────

    def test_empty_query(self):
        r = classify_query("")
        self.assertEqual(r.score, 0)
        self.assertEqual(r.decision, "factual")

    def test_whitespace_only_query(self):
        r = classify_query("    \n\t  ")
        self.assertEqual(r.decision, "factual")

    def test_quoted_topics_count_as_entities(self):
        r = classify_query(
            'Show me notes about "project alpha", "Q3 budget" and "Lisbon move".'
        )
        # 3 quoted topics → entity_count >= 3 → +3
        self.assertGreaterEqual(r.features["entity_count"], 3)

    def test_numerals_count_as_entities(self):
        r = classify_query("Compare 2022, 2023, 2024 revenue trends.")
        self.assertGreaterEqual(r.features["entity_count"], 3)

    # ── Latency budget ─────────────────────────────────────────────────────

    def test_latency_under_5ms(self):
        """Spec §1.4: Option A target ~1ms; gate §5.3 cond D: factual <=1.5x baseline."""
        # Warm up regex cache
        for _ in range(5):
            classify_query("warm up")

        queries = [
            "What is the budget?",
            "How does Acme Inc compare to Globex Co after the 2023 merger?",
            "Explain why John switched teams after the 2024 reorg.",
            "Show me notes about 'project alpha' and 'Q3 budget'.",
            "Before Lisbon closed, what did Maria and Pedro discuss?",
        ]
        start = time.perf_counter()
        for q in queries * 200:  # 1000 queries
            classify_query(q)
        elapsed_ms = (time.perf_counter() - start) * 1000
        per_query_ms = elapsed_ms / (len(queries) * 200)
        # Allow 5ms ceiling (target ~1ms, generous for CI variance)
        self.assertLess(
            per_query_ms,
            5.0,
            f"Classifier exceeded 5ms budget: {per_query_ms:.3f} ms/query",
        )


def _print_smoke_table():
    """Smoke print — for human inspection when run directly."""
    samples = [
        ("What is the speed limit?", "factual"),
        ("Who is Joe?", "factual"),
        ("How does Acme Inc compare to Globex Co after the 2023 merger?", "multi_hop"),
        ("Explain why John switched teams after the 2024 reorg.", "multi_hop"),
        ("Before the Lisbon office closed, what did Maria and Pedro agree about the budget?", "multi_hop"),
        ("Como se compara a Acme com a Globex depois da fusão em 2023?", "multi_hop"),
        ("Show me notes about 'project alpha', 'Q3 budget' and 'Lisbon move'.", "multi_hop"),
    ]
    print(f"\n{'='*100}")
    print(f"{'query':<70} {'expected':<12} {'got':<12} {'score':<6}")
    print("=" * 100)
    for q, expected in samples:
        r = classify_query(q)
        marker = "✓" if r.decision == expected else "✗"
        print(f"{marker} {q[:68]:<70} {expected:<12} {r.decision:<12} {r.score:<6}")
        print(
            f"   features: ent={r.features['entity_count']} "
            f"conj={r.features['conjunction_count']} "
            f"cmp={int(r.features['has_comparative'])} "
            f"abs={int(r.features['has_abstract_reasoning'])} "
            f"tok={r.features['token_count']} "
            f"tmp={int(r.features['has_temporal_chain'])} "
            f"-> entities={r.features['entity_set']}"
        )
    print("=" * 100)


if __name__ == "__main__":
    _print_smoke_table()
    print("\nRunning unittest suite...\n")
    unittest.main(verbosity=2)
