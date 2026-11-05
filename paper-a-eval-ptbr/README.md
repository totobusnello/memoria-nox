# Paper A: evaluating retrieval on a living PT-BR agent memory

Working title: *Five ways the ruler misleads: evaluating retrieval on a living Portuguese agent
memory.* Status: setup. Not deposited. The plan lives in `../PLANO.md` (section "Os quatro papers",
row A); this file is the paper's own scope.

## What the paper is

A methods paper in two parts, kept apart in the text:

1. **Retrospective (what was found while building the ruler, October 2026).** Each finding is
   reported with the population it was measured on and the version of the gold set it used. These
   are findings of development, not confirmations: the queries, anchors, prompts and thresholds were
   changed after looking at results on the same corpus.
2. **Prospective (what is fixed before it runs).** 120 new, synthetic, passage-conditioned
   queries, written and committed (by hash) before any system ranks them, scored under a protocol
   frozen by a tag (`PREREGISTRATION.md`). Its conclusions hold for that population only.

## What it will not claim

- That `[strict, pooled]` nDCG is an interval containing the true value. Completing the gold changes
  the ideal (IDCG) as well as the gain, and the pooled labels can carry judge errors in both
  directions. The pair is reported as **sensitivity to the annotation protocol**.
- That an LLM judge is a ground truth. A blind human sample of the discordant pairs is part of the
  design, not an extra.
- Anything about the private corpus's content. The repository is public: queries, anchors and
  rows stay outside it (`../.gitignore`), and only counts, hashes and code are published.

## Gates (see `../PLANO.md`, "Gates")

| gate | command |
|---|---|
| provenance | `python3 -I tools/provenance.py --check paper-a-eval-ptbr` |
| privacy | runs on every commit through `tools/hooks/pre-commit` |

## Files

| file | what |
|---|---|
| `PROVENANCE.json` | every number the text may print, with its audit, locator, commit and `superseded_by` |
| `RESULTS.md` | the prospective results as read: H-A1 (2026-11-05), the human sample, descriptives; H-A2 pending |
| `results/` | the registered run's printed outputs, copied unchanged from the serving host, and the hashes of its private outputs |
| `HOLDOUT-COMMITMENT.json`, `HUMAN-COMMITMENT.json` | the two commitments, each written once on `origin/main` after the tag |

`PROVENANCE.json` was seeded on 2026-11-04 from twelve audits (2026-10-22 to 2026-11-03): 161
records, 122 current and 39 superseded, in 20 correction chains (for example the v2 interval
[0.2428, 0.5114] → v3 [0.2567, 0.4394], whose ceiling a full re-read then widened to
[0.427, 0.439]; a re-judge flip rate of 20.0% that a census corrected to 4.5%). Every locator was
checked against its audit by `tools/provenance.py`. Knowledge-graph records belong to paper B and
were left out.

## Open before the text is written

1. Two ceilings under full labels on the v2 rankings: 0.4315 (bounded judge, p > 0.5, 2026-10-26)
   and 0.4412 (controlled contrast, 2026-10-27 addendum). Find the audit that reconciles them.
2. Judge stability: a re-judge of 540 pairs flipped 0 labels (2026-10-26); a full re-read of 620
   flipped 4.5% (2026-10-27). Two different operations; say which one the paper means.
3. Abstention gap: the registered five-substring detector gave 0.496, which the judge relabelling
   corrected to 0.4626; the structural predicate adopted later gives +0.4157. The last two measure
   different things; pick one by definition, not by size.
4. The oracle-pass figures (−3.5%, 0.2343, 0.4935) are projections on v2 labels; the v3 ruler also
   repairs 27 gold entries. Keep them as v2 history.
5. Audits the inventory cites but did not read: `2026-10-27-the-adversarial-pass-and-what-it-moved.md`
   and the "deflated, not inflated" pass. Add them before writing.
6. ~~The holdout~~ decided 2026-11-04: 120 synthetic questions written by a model from passages
   drawn at random, with a blind human sample graded by the author (`PREREGISTRATION.md`).
