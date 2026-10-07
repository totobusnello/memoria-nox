# APPLY — `B-v2-rc2.md` → `B-v2-rc3.md` (Paper B, sprint 2026-10-04)

Sources: `REVIEW-B-rc2-2026-10-04.md` §2 (22 confirmed findings, C1–C22; §3 rejections
not applied); numbers recomputed in `REVIEW-B-rc2-evidence/` (`checks.py` rerun here and
reproduced every figure used; `power-*.json` read field by field); sham result from
`B-sham-v2/REPORT.md` §7 and `B-sham-v2/job-v2b/RESUMO.json`. `B-v2-rc2.md` is unchanged
(1 657 lines, 120 823 bytes). rc3: 1 879 lines. Title unchanged.

Every quote was re-located by `grep` in rc3 before editing. Wrong text was struck through
beside its correction only where the manuscript's own convention already did so (the sham
row, the §4.0.1c paragraphs, working-list items); elsewhere it was replaced, with the change
recorded in the rc3 changelog (items 35–58).

## Findings

| # | status | what changed in rc3 | check against the artifact |
|---|---|---|---|
| C1 | applied | Abstract headline; §1 table H1c cell; §4.1 heading; §9 opening: "could not have found otherwise" / "undetectable by construction" → "not detectable at 80% power at the N the calculation counted". Also propagated to §4.4 ("no possible result" → "under-powered at the realized N"), same overclaim | `potencia-h1c.py` l.87 tests `poder_z >= z_0.8`; artifact states the claim at 80% only |
| C2 | applied | Abstract and §1.1: saturation stated "at the 19 clusters the calculation counted (11 treatment, 8 control)"; abstract adds one sentence on the 20-cluster result. §4.1.1: "has not been recomputed" struck and replaced by the two numbers (11T/9C whole-epoch: 96.41 > 95.26, detectable, relative MDE 0.996; fractional with `09-02`: 91.49, margin 4.1%) and the reproduction (90.2). Working list 13, first half, struck. Propagated to §8.4 (one parenthesis) and §9 (one clause) | `power-11T-9C-whole-epochs.json` (`n_efetivo_realizado` 96.41, `detectavel_no_limite_p1_igual_zero: true`, `mde_relativo_h1c` 0.996); `power-10.9375T-8.23375C-…json` (91.49, `queda…pct` 4.1); `power-11T-8C-…json` (90.2) |
| C3 | partial (as confirmed) | Abstract: contradiction stated via implied s.e. (≥ 0.0279 vs 0.0165). The rejected core (the two s.e. not estimating the same thing) not applied | §4.1.1 numbers unchanged |
| C4 | applied | Abstract (two places), §4.0.2, §4.3: the observed reduction (70.7%; 47.1% without `09-14`) would require 22.5 times total elimination in the 3.14% of altered briefs (15.0 post-hoc; 10.3 / 6.9 at 6.85%). 955% kept where it is the 2026-08-30 demotion reason (abstract, §4.3, §9). Wording fixed vs the review's "22.5×" (ambiguous) to "22.5 times total elimination" | `checks.py` output: 0.7073 / 0.4713; /0.0314 = 22.53 / 15.01; /0.0685 = 10.33 / 6.88. `H1C-POWER-REALIZADO` `fracao_de_briefs_alterada` 0.0314 |
| C5 | applied | §4.0.2: "shows that the bootstrap interval … was the artifact" → the review's sentence verbatim | — |
| C6 | applied | Abstract, §4.1.1, §4.1.2, §9: the null is the non-rejection (`p = 0.1603`); the point estimate is a 22% relative reduction not distinguishable from zero | `checks.py`: H1c relative difference −0.2227 |
| C7 | applied | §4.1.1 table row: under-coverage "expected … [@cameron2008bootstrap; @webb2014reworking]"; stratum-B "may be under-represented"; §4.1.2: "every interval that uses stratum B (H1, H1a, H1c; not M10)", "the direction of the second is not known". Propagated to the abstract's "the interval is too narrow" (now "likely too narrow … expected to under-cover") | citations already in References |
| C8 | applied | Abstract and §3.0: the spec is "dated by our commit log, not deposited with the registration" (§3.0 adds "whose deposited version is v1.12") | `deposit/PLAN-v1.13.md` l.1 "NÃO executado"; no `deposit/` file references `SPEC-ANALISE-2026-09-10`; `docs/HANDOFF.md` still says v1.13 "preparado e não executado" |
| C9 | applied | §3.0.1: "could have an effect" → "the dose could reach a designated item" | — |
| C10 | applied | §7: new paragraph "Post-randomization denominator" (100.3 / 132.3); B.1 row | `ITT-2026-09-21.json`: 1 103.75 / 11 = 100.3; 1 191.14 / 9 = 132.3 |
| C11 | applied | §6 item 3: "zero reversals to the opposite strict majority"; ties change the label = the 28 losses of item 6 | `DEVIATIONS-FOR-PAPER.md` l.3318 («Perda» é rótulo meu … 2-2 resolve para `not_failure`) |
| C12 | applied | §4: "directional bias toward fewer failures; … depends on the arms the ties fall in, which we have not counted". §7 paragraph label "Directional bias toward the null" → "Tie rule" (bold label, not a heading) | per-arm tie counts not computed (see decisions) |
| C13 | applied | §2 and §6 item 5: 11.9 pp difference in marginal rates, a lower bound on paired disagreement | 42.3 − 30.4 = 11.9 |
| C14 | applied | §4.6: low coverage explained by the denominator (287 of 672 after expiry, 0 covered; 98/385 = 25.5% before); B.1 row added | `checks.py`: 385 / 98 / 0.2545; 287 / 0; all 0.1458 |
| C15 | partial (as confirmed) | Figure B2 caption: "truncation shift is not distinguishable from zero (1% of the deficit, MC s.e. 1.5%)"; §4.7 label "does not measurably bias". The rejected part (replacing the decomposition) not applied. The later sentence "about 1% … in either direction" left as is (consistent) | 0.035 / 2.333 = 1.5% |
| C16 | applied, extended | §4.0.1b K = 20 bullet: "rank p-value", randomization p-value only to the extent shams follow the real designation's mechanism. Extended to the v2 generator, which also maps onto signature keys arbitrarily (matches severity and bonus mass, not signature group); the same caveat is a declared limit of the sham result in §4.0.1c and §7 | `gera-shams.py` l.49-52; `sprint-gera-shams-v2.py` l.165 `zip(chaves, escolhidos)` |
| C17 | applied | §5: both cells → "not computed in this version" (old text struck) | — |
| C18 | applied | §5: "except H1b (found after the close, §4.4)" | — |
| C19 | applied, section number corrected | §4: condition (i) defined in place. The review's fix cites "PREREG §3"; the repeated-failure definition is in **PREREG §4.1** (`PREREG-DRAFT.md` l.841, "### 4.1 Primary outcome"); §3 holds the `Opportunity` lock. Wording follows the PREREG text (severity ≥ τ governs (i), "≥ 1 epoch length before the epoch") | `PREREG-DRAFT.md` l.839-846 and l.642 |
| C20 | applied | §1.1: "every estimate except the `control` mean 9.991 of §4.7 (B.1), from the artifacts of Appendix B, once deposited (working list 8)" | — |
| C21 | applied | §4.3: H1a criterion restated as in rc2 §4.2 | — |
| C22 | applied, superseded in part by the sham | §3.0 heading → "The stopping rule, and the feasibility question it raises"; working-list caveat → "registered analyses missing from the first draft". §4.0.1b heading: the review's "two run, one not yet run" was superseded by the sham result → "all three run"; the caveat's "the sham is still not run" → "was run in rc3" | — |

Rejected by the review and not applied: codex #3 core, #20, #22.

## Sham integration (not a finding; source `B-sham-v2/REPORT.md` §7, `job-v2b/RESUMO.json`)

| place | change |
|---|---|
| STATUS block | rc2 → rc3; "still not done: the valid sham replay and deposit" struck → sham run; deposit still open |
| Abstract | one sentence: controls pass; real designation above each of 20 matched shams on 2,646 states of the `w = 4` epochs, `p = 1/21` (floor); specificity on what was served, nothing about outcomes |
| §4.0.1b | table row (old text struck; "passed, rank 1 of 21: 132 vs 81–122, p = 0.0476", restriction to w = 4 epochs and 36 boostable items); heading; first paragraph "was not run" removed; eligible-pool bullet: only 36 of 89 can receive a bonus |
| §4.0.1c | heading; "what a valid sham needs" (old text struck; (iv) met by a `brief_log` export hash-equal on the overlap; corpus per state from the fd sha readings, stated as daily measurements plus an argument for the gaps); measured/not-measured table (110/110 measured; new 2,646 row; 20 shams run; dist byte identity still not measured); new "The sham, run" table (mexeu 132 vs 81–122, churn 146 vs 84–132, 0 shams ≥ real, p = 0.0476 on both; positive control 155 vs 81–122 at w = 100 000; real = calibration and production 2,646/2,646; throttling changed timing only); "What it shows, and what it does not" with four declared limits (w = 4 restriction and why; 36 of 89 boostable and why, including overlap 6–14, mean 10.4; signature-group match; p at floor, one tie → 0.095); claims paragraph; artifact list |
| §7 | new "Scope of the specificity control" |
| §8.3, §8.5 | "not executed" sentences struck/replaced; ghost-ads sentence updated |
| Appendix B, B.1 | † rows for the sham artifacts and for `REVIEW-B-rc2-evidence/`; B.1 rows for every new number |
| Working list | item 3 (struck "still open"), 8 (blocked by 10 only), 9 struck → done, 13 first half struck, new 14 (this review, struck); caveat |
| Changelog | rc3 block, items 35–58 |

Declared caveats, as asked: state set restricted to the `w = 4` epochs (deviation from the
configured, not pre-registered, `roda-sham.sh`; reasons from REPORT §4/§3: registered "same w",
randomized epochs, corpus verified per state, production checkable, whole log ≈60 h with ~8k
shadow states of unidentifiable corpus, trial window ≈36 h); shams from the 36 boostable
items (bonus only for ids with a `p2_verdict` row S1–S4 written ≥ 1 day before the epoch;
53 of 89 have none; drawing from all 89 gives 21–50% of the real bonus mass and biases toward
real > sham); `p` at the floor; specificity on what is served, not an effect on outcomes.

Left as historical (not rewritten): the §4.0.1 heading "Two registered analyses we did not
run" (describes the first draft); "declared as not run rather than reported as failed"
(§4.0.1b, about the 2026-09-22 attempt); the rc2 changelog items 1–5 (a record of rc2).

## Style pass (avoid-ai-writing, changed sentences only)

Detect + edit on the 319 added/changed lines (technical register). Fixed: one em dash added
inside the §4.1.1 table row (→ semicolon); a "not X: Y" reveal in the sham reading ("It is not
specific in an absolute sense" → "The specificity is relative"); "not by how much in
probability" (vague) → "at this `K` it cannot say more"; an abstract sentence split where a
relative clause carried two claims; "designated ids" clarified to "ids in the designation,
real or sham". No Tier 1 vocabulary, hedge stacks or filler found in the changed text. Bold
labels in §7 and the bullets of §4.0.1c follow the manuscript's existing convention.

## Parity

`B-rc3/parity-rc3.py`: PASS. 97 numeric tokens change count between rc2 and rc3; each is
listed with its exact signed change and a reason (finding ID, SHAM or CHANGELOG); 3 tokens
disappear (`95` C3, `12` C13, `13.86` C14). Headings: 40, identical except the 4 allowed
renames (§3.0 C22, §4.0.1b C22+SHAM, §4.0.1c SHAM, §4.1 C1). Internal § refs: 7 dangling in
both (pre-existing: §9.1 ×4 and §9.6 are external refs the cue list does not catch, §4.4.1 ×2
in the rc2 changelog), 0 new. Citation keys unchanged and all listed; no footnotes; no host,
IP or personal path added. `--self-test`: 3 mutations (a number, a heading, a new § ref),
all caught; unmutated rc3 passes.

## Needs the author's decision

1. **Title** (kept): options in the hand-off report.
2. **C2 changes the headline's footing.** At the ITT's own allocation under whole-epoch
   counting, total elimination is detectable at 80%; the paper now says "borderline for total
   elimination, under-powered for anything less" at 20 clusters. Which counting governs the
   claim (whole-epoch vs the spec's fractional) is a choice the spec did not anticipate for
   `09-02`; rc3 reports both and does not pick.
3. **C12:** the per-arm tie counts in the four-vote set were not computed; rc3 says so.
   Computing them would close the point.
4. **Sham scope:** the trial-window run (11,865 states, ≈36 h) is configured and not run.
   Running it would remove the main declared limit; not running it is defensible as stated.
5. **§9 "projection-robust"**: kept with the qualifier; the §1.1 caveat that says the extremes
   analysis "still returns not-detectable" is true for the spec's cuts, not for 11T/9C
   whole-epoch. Left unedited because no finding covers it; the author may want one clause.
