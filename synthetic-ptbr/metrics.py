#!/usr/bin/env python3
"""Scoring for the synthetic corpus: nDCG@10 with binary gain, two ideals, and pooling.

  python3 -I synthetic-ptbr/metrics.py --fixtures     gate «S: achado 4»: hand-computed cases

Two ideals (finding 4 of Paper A):
  gold ideal     built from every relevant item that exists (min(|relevant|, k) ones);
  ranking ideal  built only from the relevant items the ranking returned in its top k.
With binary gain and the same numerator the ranking ideal can only raise or keep the score when
both denominators are positive: that direction is arithmetic, so the corpus measures only how
often and by how much the choice changes a score, zero included.

Ideal zero: when the chosen ideal has no relevant item (nothing relevant exists, or nothing
relevant was retrieved under the ranking ideal) the score is UNDEFINED and returned as None. It is
counted and reported, never averaged as 0 or as 1.

Pooling (finding 2): P = R ∪ (T ∩ top-k). The plumbing control removes exactly the additions,
P − (P − R) = R, and must give back the R score.
"""
import math
import sys

K = 10


def dcg(gains):
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def ndcg_gold(ranking, relevant, k=K):
    if not relevant:
        return None
    gains = [1 if x in relevant else 0 for x in ranking[:k]]
    return dcg(gains) / dcg([1] * min(len(relevant), k))


def ndcg_ranking_ideal(ranking, relevant, k=K):
    gains = [1 if x in relevant else 0 for x in ranking[:k]]
    hits = sum(gains)
    if hits == 0:
        return None
    return dcg(gains) / dcg([1] * hits)


def pooled(registered, truth, ranking, k=K):
    return set(registered) | (set(truth) & set(ranking[:k]))


# Hand-computed expectations. 1/log2(3) = 0.6309298, 1/log2(5) = 0.4306766, 1/log2(6) = 0.3868528,
# so the ideal DCG of five relevant items is 1 + 0.6309298 + 0.5 + 0.4306766 + 0.3868528 = 2.9484592.
FIXTURES = [
    # name, ranking, relevant, expected gold-ideal score, expected ranking-ideal score
    ("one relevant at rank 1, four never retrieved",
     ["a", "x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8", "x9"], {"a", "b", "c", "d", "e"},
     1 / 2.9484592, 1.0),
    ("all three relevant retrieved at ranks 1-3",
     ["a", "b", "c", "x1", "x2", "x3", "x4", "x5", "x6", "x7"], {"a", "b", "c"}, 1.0, 1.0),
    ("two relevant exist, none retrieved",
     ["x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8", "x9", "x10"], {"a", "b"}, 0.0, None),
    ("no answer exists (false premise)",
     ["x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8", "x9", "x10"], set(), None, None),
    ("one relevant at rank 2 of one",
     ["x1", "a", "x2", "x3", "x4", "x5", "x6", "x7", "x8", "x9"], {"a"}, 0.6309298, 0.6309298),
]


def run_fixtures(gold=ndcg_gold, rank=ndcg_ranking_ideal, tol=1e-6):
    fails = []
    for name, ranking, rel, want_g, want_r in FIXTURES:
        for label, fn, want in (("gold", gold, want_g), ("ranking", rank, want_r)):
            got = fn(ranking, rel)
            same = (got is None and want is None) or (
                got is not None and want is not None and abs(got - want) < tol)
            if not same:
                fails.append(f"{name}: {label} ideal gave {got}, want {want}")
    # pooling plumbing control on a fixed case
    truth, reg = {"a", "b", "c"}, {"a"}
    ranking = ["x1", "b", "x2", "a", "x3", "x4", "x5", "x6", "x7", "x8"]
    p = pooled(reg, truth, ranking)
    if p != {"a", "b"}:
        fails.append(f"pooled gave {sorted(p)}, want ['a', 'b']")
    if p - (p - reg) != reg or ndcg_gold(ranking, p - (p - reg)) != ndcg_gold(ranking, reg):
        fails.append("removing the pooled additions does not give back R")
    # the scores of the same case, computed by hand (positions 2 and 4; ideals of 2, 3 and 1 items):
    # pooled (1/log2 3 + 1/log2 5) / (1 + 1/log2 3), truth over (1 + 1/log2 3 + 1/2), strict (1/log2 5) / 1
    for label, rel, want in (("pooled", p, 0.6509209298), ("truth", truth, 0.4981892575),
                             ("strict", reg, 0.4306765581)):
        got = ndcg_gold(ranking, rel)
        if got is None or abs(got - want) > 1e-9:
            fails.append(f"pooling control: {label} nDCG gave {got}, want {want}")
    return fails


def main():
    if "--fixtures" not in sys.argv:
        print(__doc__)
        return 2
    fails = run_fixtures()
    for f in fails:
        print(f"  ! {f}")
    print(f"metrics --fixtures: {'FAIL' if fails else 'ok'} ({len(FIXTURES)} cases x 2 ideals + pooling)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
