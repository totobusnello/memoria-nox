import unittest
from probe.sham import item_tokens, common_tokens, filter_candidates, build_sham


def it(i, text, created="2026-10-01 00:00:00"):
    return {"id": i, "created_at": created, "text": text}


class ShamTest(unittest.TestCase):
    T = "2026-10-05 12:00:00"

    def test_filters_future_b1_ids_overlap_and_duplicates(self):
        b1 = [it(1, "gateway restart drill procedure")]
        cands = [it(1, "same id as b1"), it(2, "future item text", "2026-10-06 00:00:00"),
                 it(3, "gateway restart drill procedure again"), it(4, "solar panel quotes"),
                 it(4, "solar panel quotes")]
        out = filter_candidates(cands, b1, self.T, set())
        self.assertEqual([c["id"] for c in out], [4])

    def test_common_tokens_are_excluded_from_overlap(self):
        texts = ["lessons something"] * 10 + ["unique words here"]
        common = common_tokens(texts, share=0.5)
        self.assertIn("lessons", common)
        b1 = [it(1, "lessons alpha")]
        out = filter_candidates([it(2, "lessons beta")], b1, self.T, common)
        self.assertEqual([c["id"] for c in out], [2])

    def test_sliding_window_accepts_first_within_tolerance(self):
        f = [it(i, "x") for i in range(5)]
        lens = {(0, 1): 50, (1, 2): 100, (2, 3): 102}
        render_len = lambda w: lens[(w[0]["id"], w[1]["id"])]
        w = build_sham(f, 2, 100, render_len)
        self.assertEqual([x["id"] for x in w], [1, 2])

    def test_exhausted_sequence_returns_none(self):
        f = [it(i, "x") for i in range(3)]
        self.assertIsNone(build_sham(f, 2, 100, lambda w: 10))
        self.assertIsNone(build_sham(f[:1], 2, 100, lambda w: 100))

    def test_item_tokens(self):
        toks = item_tokens("The CLI path: /usr/bin/bird ok")
        self.assertIn("path", toks)
        self.assertNotIn("the", toks)
        self.assertNotIn("ok", toks)


if __name__ == "__main__":
    unittest.main()
