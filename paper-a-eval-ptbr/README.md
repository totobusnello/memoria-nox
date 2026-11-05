# Paper A: evaluating retrieval on a living PT-BR agent memory

Working title: *Five ways the ruler misleads: evaluating retrieval on a living Portuguese agent
memory.* Status: manuscript draft (`MANUSCRIPT.md`), H-A2 pending until 2026-11-18. Not deposited. The plan lives in `../PLANO.md` (section "Os quatro papers",
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
| `MANUSCRIPT.md` | the manuscript draft (2026-11-05): five retrospective findings, the pre-registered test, H-A2 pending |
| `manuscript-tables.py` | generates the manuscript's tables from `results/` and the commitments; `--check` is the table-parity gate |
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

Items 1 to 5 were decided on 2026-11-05, after reading the audits behind each one (Toto chose
1 to 3; 4 was already settled; 5 found a defect).

1. ~~Two ceilings~~ decided: the v2 ceiling under full labels is 0.4412 (gold counted relevant
   without judging, the rule v3 uses), so it compares like with like against the v3 ceiling band
   [0.427 · 0.439] and carries the 97% coverage attribution. 0.4315 (bounded judge, p > 0.5, 2026-10-26) differs in one rule: the
   gold must also pass the judge, and 19 of 30 did. It is reported only as that variant. The same
   digits name a different v3 quantity in the adversarial-pass audit; never print it without
   saying which.
2. ~~Judge stability~~ decided: both, named. 0 of 540 flips is repeatability: the identical
   request sent twice (2026-10-26). 4.5% of 620 is re-read stability: the same predicate re-asked in
   a different request (one question instead of two, the passage wrapped), closer to prompt
   sensitivity than to sampling noise (2026-10-27). The paper's stability figure is the second,
   which sets the ceiling band in `PREREGISTRATION.md`.
3. ~~Abstention gap~~ decided: the registered five-substring figure 0.496 stays the primary, as
   the audits keep it ("the published number survives"); the judge relabelling's 0.4626 is the
   reference, not a correction. The structural predicate's +0.4157 is reported separately, defined
   as a different measure (an answer that anchors nothing in context). All three describe the
   system before the `citations === 0` rule went into serving on 2026-10-27, and the text says so.
4. ~~Oracle pass~~ settled in the repo: −3.5%, 0.2343 and 0.4935 are arithmetic on v2 labels
   (the two added queries assumed to score zero), not scores. Kept as v2 history.
5. ~~Unread audits~~ read on 2026-11-05. Their figures enter `PROVENANCE.json` when the text cites
   them. One defect: the "deflated, not inflated" audit and the v3-scored audit give the share of
   gold entries that do not answer their question as the share their own table says the judge
   accepted (57 of 95 accepted, 38 rejected). An erratum is appended to both, and the provenance record that carried the inverted
   reading is superseded by `gold-entries-accepted` and `gold-entries-rejected`.
6. ~~The holdout~~ decided 2026-11-04: 120 synthetic questions written by a model from passages
   drawn at random, with a blind human sample graded by the author (`PREREGISTRATION.md`).
