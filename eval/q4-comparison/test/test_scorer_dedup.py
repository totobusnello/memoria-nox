#!/usr/bin/env python3
"""Unit tests for the 2026-10-04 scorer fix: each retrieved id is credited once.

Runs against the harness scorer and, when present, the copy shipped in the Section 6
evidence dataset (10.5281/zenodo.23146656), so the two cannot drift apart silently:

    eval/q4-comparison/aggregate.py
    paper2-interventional/_sprint-2026-10-04/noxmem-evidence/payload/scripts/aggregate.py

    python3 -m unittest eval/q4-comparison/test/test_scorer_dedup.py
    (or run the file directly)

Mutation check: reverting `_first_occurrences` to a pass-through makes
test_duplicated_gold_* fail (nDCG 1.0 + 1/log2(3) > 1, recall 2.0).
"""
from __future__ import annotations

import importlib.util
import math
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
COPIES = {
    "harness": ROOT / "eval" / "q4-comparison" / "aggregate.py",
    "payload": ROOT / "paper2-interventional" / "_sprint-2026-10-04" / "noxmem-evidence" / "payload"
    / "scripts" / "aggregate.py",
}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(f"aggregate_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


COPIES = {n: p for n, p in COPIES.items() if p.exists()}  # the payload copy lives outside the repo
MODS = {n: _load(n, p) for n, p in COPIES.items()}
L2 = lambda r: 1 / math.log2(r + 1)  # gain at 1-based rank r  # noqa: E731


class ScorerDedup(unittest.TestCase):
    def each(self):
        # plain list (no generator): a failing assertion inside the caller's loop must not
        # be raised into a suspended generator. The copy name is in every message via msg=.
        return list(MODS.values())

    def test_copies_identical(self):
        if len(COPIES) < 2:
            self.skipTest("payload copy not present")
        a, b = (p.read_bytes() for p in COPIES.values())
        self.assertEqual(a, b, "harness and payload scorers differ")

    def test_duplicated_gold_single_gold(self):
        # gold g appears at ranks 1 and 2: credited once, at rank 1 -> nDCG 1.0, not 1.63
        r, gold = ["g", "g", "x", "y"], {"g"}
        for m in self.each():
            n = m.ndcg_at_k(r, gold, 10)
            self.assertLessEqual(n, 1.0)
            self.assertAlmostEqual(n, 1.0, places=12)
            self.assertEqual(m.recall_at_k(r, gold, 10), 1.0)
            self.assertEqual(m.reciprocal_rank(r, gold), 1.0)

    def test_duplicated_gold_two_golds(self):
        # gold {a, b}; a at ranks 2 and 3, b at rank 5. Old scorer: (L2(2)+L2(3)+L2(5))/(L2(1)+L2(2)).
        # Fixed: rank 3 is a repeat -> (L2(2)+L2(5))/(L2(1)+L2(2)).
        r, gold = ["x", "a", "a", "y", "b"], {"a", "b"}
        want = (L2(2) + L2(5)) / (L2(1) + L2(2))
        for m in self.each():
            n = m.ndcg_at_k(r, gold, 10)
            self.assertLessEqual(n, 1.0)
            self.assertAlmostEqual(n, want, places=12)
            self.assertEqual(m.recall_at_k(r, gold, 10), 1.0)
            self.assertAlmostEqual(m.reciprocal_rank(r, gold), 0.5, places=12)

    def test_duplicated_gold_not_at_top(self):
        # single gold g at ranks 1 and 3: old scorer 1 + 1/log2(4) = 1.5 (> 1), recall 2.0
        r, gold = ["g", "x", "g"], {"g"}
        old = L2(1) + L2(3)
        self.assertGreater(old, 1.0)
        for m in self.each():
            n = m.ndcg_at_k(r, gold, 10)
            self.assertAlmostEqual(n, 1.0, places=12)
            self.assertLess(n, old)
            self.assertEqual(m.recall_at_k(r, gold, 10), 1.0)
        # one of two golds returned twice, the other missed: once-credit = L2(1)/IDCG(2), recall 0.5
        r2, gold2 = ["g1", "g1", "x"], {"g1", "g2"}
        for m in self.each():
            self.assertAlmostEqual(m.ndcg_at_k(r2, gold2, 10), L2(1) / (L2(1) + L2(2)), places=12)
            self.assertEqual(m.recall_at_k(r2, gold2, 10), 0.5)

    def test_no_repad(self):
        # k=3; the repeat at rank 2 must NOT pull the gold at rank 4 into the top 3.
        r, gold = ["x", "x", "y", "g"], {"g"}
        for m in self.each():
            self.assertEqual(m.ndcg_at_k(r, gold, 3), 0.0)
            self.assertEqual(m.recall_at_k(r, gold, 3), 0.0)
        # and a gold after a repeat keeps its ORIGINAL rank (3), not rank 2
        r2 = ["x", "x", "g"]
        for m in self.each():
            self.assertAlmostEqual(m.ndcg_at_k(r2, gold, 10), L2(3), places=12)
            self.assertAlmostEqual(m.reciprocal_rank(r2, gold), 1 / 3, places=12)

    def test_without_duplicates_unchanged(self):
        # no repeats -> identical to the textbook binary formula
        r, gold = ["a", "x", "b", "y", "z"], {"a", "b", "c"}
        want = (L2(1) + L2(3)) / (L2(1) + L2(2) + L2(3))
        for m in self.each():
            self.assertAlmostEqual(m.ndcg_at_k(r, gold, 10), want, places=12)
            self.assertAlmostEqual(m.recall_at_k(r, gold, 10), 2 / 3, places=12)

    def test_bounds_random(self):
        import random
        rng = random.Random(20261004)
        ids = [f"i{j}" for j in range(8)]
        for m in self.each():
            for _ in range(2000):
                r = [rng.choice(ids) for _ in range(rng.randint(0, 15))]
                gold = set(rng.sample(ids, rng.randint(1, 4)))
                self.assertGreaterEqual(m.ndcg_at_k(r, gold, 10), 0.0)
                self.assertLessEqual(m.ndcg_at_k(r, gold, 10), 1.0 + 1e-12)
                self.assertLessEqual(m.recall_at_k(r, gold, 10), 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
