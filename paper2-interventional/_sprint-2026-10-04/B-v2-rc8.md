# A registration that outlived its intervention: a pre-registered randomized trial of memory dosing in a production agent fleet

> **STATUS: DRAFT opened 2026-09-21; v2 prepared 2026-10-04 (release candidate rc3);
> rc4 prepared 2026-10-05; rc5 prepared 2026-10-05 after a regression review of rc4; rc6
> prepared 2026-10-05 (ballast gap closed, writing pass); rc7 prepared 2026-10-05 (review of
> rc6 applied; every number and sentence that the registered re-analysis replaces is marked
> `REANALISE` and still carries the rc6 value); rc8 prepared 2026-10-05 (the analysis as
> registered is the reported analysis, the analysis of rc7 is a sensitivity, and no marker
> remains).** Every
> number below is measured; §B names its artifact, and B.1 declares the one number (9.991,
> §4.7) held by no artifact. What is *not*
> done: ~~figures, related work, and deposit~~ → as of v2, figures (B1, B2) and related work
> (§8) are in; ~~still not done: **the valid sham replay** (§4.0.1c) and **deposit**~~ → as
> of rc3 the valid sham replay is run (§4.0.1c); still not done: **deposit**. <!-- SHAM-JANELA: pending -->A second sham
> replay, over the whole trial window (11,812 reconstructible states of 18 epochs; job
> `job-janela2`, relaunched 2026-10-05T09:39:53Z, expected to finish about
> 2026-10-07T03:00Z), is running, and its result will be added before deposit (§4.0.1c).<!-- /SHAM-JANELA --> The v2
> changes are listed in the changelog at the end.
>
> **Caveat.** There were two different adversarial reviews. The numbers in §6
> were reviewed adversarially before this manuscript existed; that is how six of those
> seven defects were found. This manuscript is under review as of 2026-09-21 by five
> model families; §4.3, §4.4 and §3 already carry corrections it produced. The working list is at the end, and the rule of this project
> applies to it: an item is struck in the same commit that closes it.
>
> This is Paper B of the split decided on 2026-08-28 (`PAPER-SPLIT-2026-08-28.md`).
> Paper A (`MANUSCRIPT.md`, *"Spare capacity, narrow surface"*) reports the surface
> measurements and does not depend on this trial having run. This paper reports the
> trial that the public pre-registration covers, and nothing else.

---

## Abstract

We report a pre-registered, fleet-wide interventional trial of dose-weighted memory
promotion in a production agent-memory system. Epochs of 24 h were randomized to control
or to one of three dose levels by constrained randomization seeded from a public drand
beacon, with the assignment script and its hash registered before the seed was drawn
(OSF `yf7d2`, 2026-08-18T07:56:44Z; Zenodo `10.5281/zenodo.22110203`).

The registered design called for 234 epochs. Twenty were realized, of which nineteen
served data and form the analysis set.

The trial did not stop early: 234 was infeasible from the start. All 19 designated
items share one `created_at` and sit in a sub-pool with a 30-day window, so they leave
eligibility together at 2026-09-20 22:51:23 (20 of the 234 registered epochs, 8.5%).
Past that instant no value of the dose reaches them, because the boost is addressed by id
and they are no longer in the candidate list; treatment and control would have been the
same intervention for 214 epochs. The registration outlived its intervention: `sizing.py`
sized for 234 epochs on an intervention that existed for 20. The under-powering of this
study follows from that, and it is a property of the registration, not of the realized
window.

The deposited registration (v1.12) names H1, repeated-failure density per session-hour, as
the primary outcome and H1a–H1c as a Holm-corrected co-primary family. This paper reports
H1c, the share of opportunities yielding a repeated failure, as its primary. The switch was
decided on 2026-08-30 (`DESIGN-REVISION-2026-08-30.md` §3-ter;
`PROSPECTIVE-ESTIMAND-2026-08-30.md` §3-bis), before the assignment seed was drawn (round
31774052, emitted 2026-08-30T21:32:04Z) and before any randomized epoch existed, in
documents dated by our commit log and not deposited. It is therefore a deviation from the
public registration, and we report the deposited primary beside it: the registered
re-randomization test rejects the sharp null for H1 (`p = 0.0133`, §4.0.2).
Under the deposited Holm correction no member of the H1a–H1c and H2 family rejects (§1):
H1a has the smallest unadjusted p-value, 0.0241, and its Holm-adjusted p-value is 0.1205
(0.0964 if the untestable H1b is dropped from the family).

The analysis we report is the one the registration and the analysis specification lock:
the fourth panel family only as a substitute below the three-verdict floor, the analysis
window cut at the designation's expiry with the specification's exposure offsets for the
partial epochs, a BCa interval with a leave-one-epoch-out jackknife, and 19 epochs (the
empty `09-02` excluded). The analysis of earlier versions, which departed from all four, is
reported as a sensitivity, and no registered verdict differs between the two (§4).

The primary outcome is null: the registered re-randomization test does not reject the sharp
null for H1c (`p = 0.434`, §4.0.2). Under the planning assumptions and the
fractional counting the analysis specification fixes, no reduction from `p0 = 0.0782`,
including total elimination, reaches 80% power (§4.1.1). As pre-committed on 2026-08-30,
the null does not distinguish a mechanism that does not work from lessons too generic to
work (§4.5). This is a claim about H1c and not
about every quantity the trial produced. Two secondary
quantities *do* return intervals excluding zero: `H1a` on the locked and pre-committed legs
but not without `09-14` (§4.2), and not rejected under the registered Holm rule; and
`H1` on all three legs. `H1` is reported as an unexplained rejection (§4.0.2). If the
observed reduction (69.8%; 44.6% without `09-14`) were carried only by the briefs
the dose alters, in proportion to their share, it would amount to 22.2 times total
elimination on the locked leg at the pre-trial calibration share (3.14%, 11 of 350 briefs
at `w = 2`), and 15.3 times at the share realized in the trial (4.56%, 335 of the 7 350
briefs served in active mode in treatment epochs); at least 6.5 times on either leg even
at the highest per-epoch share, 6.85%. These are proportional-dilution calculations, not causal bounds:
the share of briefs altered need not equal the share of failures they carry, and an effect
can travel through activity volume or state (§4.3, §8.3). The shared denominator of §4.3
explains part of the rejection, not the residual. The
analysis specification, written on 2026-09-10 and dated by our commit log, not deposited
with the registration (ten days before the window
closed and before any outcome was computed), recorded that the minimum detectable effect
for H1c was saturated at 100% under each of its inclusion cuts, among them the 19
clusters the calculation counted (11 treatment, 8 control): no reduction, including total
elimination, was detectable at 80% power. Those 19 clusters are the registered analysis
set. The spec counts partial epochs by fractional exposure, and that counting governs the
power statement; counting whole epochs at the same 11 treatment and 8 control gives the
same verdict (effective size 90.2 against a critical 95.26). Only at the 20 epochs of the
sensitivity analysis, with `09-02` as a ninth control, does whole-epoch counting flip it
(96.41, §4.1.1). The realized estimate is −0.0121 (treatment 0.0675, control 0.0796; 95% BCa
interval [−0.0445; +0.0125], epoch as the resampling unit), containing zero on all three
legs (locked, pre-committed sensitivity, post-hoc sensitivity) and in the sensitivity
analysis (−0.0199 [−0.0560; +0.0086], `p = 0.1603`).

Our two statements about uncertainty rest on different constructions. The planning power
approximation and the realized bootstrap interval use different variance constructions and
assumptions; their difference does not establish a contradiction, and it does not quantify
any under-coverage of the bootstrap. The interval may be too narrow (a BCa bootstrap
on 19 clusters, 11 treatment and 8 control, may under-cover, and it does not re-draw the
stratum-B sample), and the power statement rests on an ICC estimated for a different
quantity. Neither is a calibrated measure of this study's uncertainty. The null
(non-rejection by the registered re-randomization test, `p = 0.434`) does not rest on the
interval; the point estimate, a 15% relative reduction, is not distinguishable from zero
at this N.

Two commitments made before the seed were not kept, and we found both only after the
trial, from the artifacts. A stopping rule written before the assignment seed
(`PROSPECTIVE-ESTIMAND-2026-08-30.md` §3-bis) closes the interventional arm with a null if
the coverage measured in Epoch 1 falls below 36.7%. Measured now from the locked artifacts
by the definition the threshold was derived from, Epoch-1 coverage is 32.4% (45 of 139
opportunities; 33.7% over the `active` phase alone, while two other readings, after the
washout or under the trial's weighted opportunity rule, are above it): the condition was
met, we find no record that it was evaluated during the trial, and the arm was not
closed (§3.0). And the seed declaration (`ASSIGN-SEED-2026-08-30.md`) named an assignment
rule other than the registered `assign_arms.py`; the declared rule was replaced
by the registered script 24 min 38 s after the drand round was emitted. Run offline on
that round, the two rules assign a different arm to 11 of the 20 realized epochs (§1).

The primary test does not reject the sharp null. Given the small number of epochs and the
uncertainty limitations above, this result neither establishes absence of effect nor
supports a confident efficacy claim. We report the trial in full regardless, because the parts
that carry information lie outside the effect estimate: the instrument controls pass,<!-- SHAM-JANELA: pending -->
including a sham replay in which the real designation changed more served briefs than each
of 20 matched sham designations (2,646 brief states of the `w = 4` epochs; `p = 1/21`, the
floor for 20 shams). Against these 20 shams, that is evidence that the dose acted
specifically on what was served; the rank is not a calibrated randomization p-value, and it
says nothing about outcomes (§4.0.1c).<!-- /SHAM-JANELA --> A hypothesis that was demoted from
primary for requiring, at the pre-trial calibration share of altered briefs, a 955% effect
nonetheless returns an interval excluding zero on all
three legs, which we report as an unexplained rejection: the *denominator* explains part
of it and not the residual, and the observed reduction is many times what the few briefs
the dose alters could carry in proportion to their share (a proportional-dilution
calculation, not a causal bound); a second hypothesis
~~inverts its conclusion on the removal of a **single** epoch whose exposure comes from one
session with three episodes~~ ~~excludes zero only on the locked leg: its pre-committed
sensitivity leg contains zero, and so does a post-hoc leg that removes a single epoch whose
exposure comes from one session with three episodes *(corrected 2026-10-04: the first
version reported only the post-hoc leg; §4.2)*~~ excludes zero on the locked and the
pre-committed legs under the registered BCa interval, contains zero on a post-hoc leg that
removes a single epoch whose exposure comes from one session with three episodes, and is
not rejected under the registered Holm rule *(corrected in rc8: "only on the locked leg"
held for the percentile interval of earlier versions, not for the registered BCa; §4.2)*;
and the member of the hypothesis family
that carried the substantive mechanism question collapses to 1.0 by construction, because two locks of our own
pre-registration define its estimand incompatibly and neither of us noticed until the
window had closed.

We take the position that these are the reportable results of a trial whose registration
outlived its intervention and which is under-powered as a result, and that publishing them is the alternative to the two things a null of this shape is usually
used for: silence, or a claim.

---

## 1. What was registered, and what this paper reports

The pre-registration (OSF `yf7d2`, Zenodo `10.5281/zenodo.22110203`, v1.12) specifies a
fleet-wide trial in which epochs (24-hour periods with a 09:00 UTC boundary) are
assigned to control or to a dose `w ∈ {2.0, 4.0, 7.5}` that scales the promotion weight of
a fixed set of designated items (memory chunks). The designation is a fixed, publicly re-derivable
set of 19 chunks, one per signature group (`DESIGNATION-2026-08-26.json`). The designation
was completed on 2026-08-26 at 20:28Z. Its declaration preceded designation round 31657512
by 1 056 s according to the recorded timestamps. Epoch assignment used the separate round
31774052 on 2026-08-30, whose declaration (`ASSIGN-SEED-2026-08-30.md`, pushed 21:18:35Z)
preceded its emission (21:32:04Z) by 13 min 29 s, again according to the recorded
timestamps.

**The assignment rule, declared and replaced (rc8).** The seed declaration did not name the
registered assignment rule. It declared a global sort of the 234 epochs by
`SHA256(seed | epoch index)`, the first 117 to control and three blocks of 39 to
treatments it left unnamed. The registered rule is `assign_arms.py` (stratified block
randomization, committed 2026-08-16, last changed 2026-08-17, deposited with v1.12). The
assignment derived from the declared rule was committed at 21:33:46Z, after the round was
emitted, and it was replaced by the output of `assign_arms.py` at 21:56:42Z, 24 min 38 s
after the emission, in a commit that calls the declared rule an error. The trial served
the registered rule's assignment. Both rules run offline on the round's published
randomness (`_sprint-2026-10-04/B-rc8/checks-rc8.json`, block E): each reproduces its own
published output (the declaration's `sha256_da_atribuicao` `2426d13d…`, and
`ASSIGNMENT.json`, which `ASSIGNMENT-SERVING.json` relabels without change), and they
assign a different binary arm to 130 of the 234 epochs and to 11 of the 20 realized ones
(`09-01`, `09-05`, `09-06`, `09-07`, `09-08`, `09-09`, `09-11`, `09-13`, `09-17`, `09-19`,
`09-20`). Under the declared rule the realized window would have held 10 control and 10
treatment epochs instead of 9 and 11. This is a deviation, and the order of events does not
remove it: the replacement was chosen after both assignments were computable, so the only
protection is that the rule it adopted was fixed and deposited two weeks before the round,
which the deposit, not our log, dates. The declared rule was never run as the trial's
assignment.

The registered hypothesis family is nested (`H1c ⊆ H1b ⊆ H1a`), and §1 of the
pre-registration calls that nesting *"the nesting that makes the joint reporting work"*:

| | statement | status here |
|---|---|---|
| `H1` | density of repeated failures per session-hour | **computable**; the deposited primary, demoted 2026-08-30 in an undeposited revision (below); the registered test rejects (§4.0.2, §4.3) |
| `H1a` | rate of eligible opportunities per session-hour | **computable**; unadjusted `p = 0.0241`, not rejected under the registered Holm rule; does not bear weight (§4.2) |
| `H1b` | share of opportunities yielding a repeat attempt | **trivially 1.0**; the question it carried is unanswerable (§4.4) |
| `H1c` | share of opportunities yielding a repeated *failure* | **primary in this report** (switched before any data, undeposited; below); null; no reduction detectable at 80% power under the spec's fractional counting (§4.1.1) |

**The primary switch, declared.** The registration as deposited (v1.12) names H1 the
primary and H1a–H1c a Holm-corrected co-primary family; its multiple-comparisons rule
tests H1 at α = 0.05 two-sided and Holm-corrects H1a–H1c together with H2. H1c was made the
primary on 2026-08-30 in `DESIGN-REVISION-2026-08-30.md` §3-ter (commit of 16:51:56Z), and
the switch was recorded in `PROSPECTIVE-ESTIMAND-2026-08-30.md` §3-bis (commit of
20:51:20Z), whose own summary table (its l.26) still names the density outcome. Both
commits precede the declaration of the assignment seed (pushed 21:18:35Z) and the emission
of its drand round (31774052, 21:32:04Z), and no randomized epoch existed then. Neither
document was deposited; a v1.13 amendment prepared on 2026-08-27 was not deposited either
(`deposit/PLAN-v1.13.md`). The ordering therefore rests on our commit log, the weaker kind
of evidence §1.1 discusses. We report both readings: under the switch, H1c is null
(`p = 0.434`); under the deposited primary, H1 rejects (`p = 0.0133`), and §4.3
states why we do not read that rejection as an effect of the dose. Under the deposited Holm
correction no member of the family rejects. The family holds H1a, H1b, H1c and the two
components of H2. H1b has no test (§4.4) and enters as `p = 1`. The smallest unadjusted
p-value is H1a's, 0.0241, which exceeds the first Holm threshold at either family size:
0.01 with all five members (adjusted 0.1205) and 0.0125 without H1b (adjusted 0.0964). H1c
(0.434) and H2 (0.831 for time, 0.684 for tokens) are further away. H1a's unadjusted
p-value below 0.05 is not a rejection: the registration decides H1a inside the Holm family,
and reporting 0.0241 alone would apply a decision rule the registration does not contain.
In the sensitivity analysis the same verdicts hold (H1 0.0127; H1a 0.0855; H1c 0.1603).
PROSPECTIVE-ESTIMAND §3-bis made H1c primary without restating the multiplicity rule; under
either reading H1c does not reject.

This paper reports the intention-to-treat analysis of that family and, in §5, the
secondary confirmatory H2 (task regret), which does not reject; H3 (retrieval metrics,
exploratory) is not computable, and §5 says why. The
surface measurements made *while* the trial was being built (the exposure ceiling, the
carousel, the coverage channel) are Paper A, are explicitly exploratory and
descriptive, and were never pre-registered.

### 1.1 The order in which decisions were taken, and why it is stated first

Two estimand decisions had to be made after the window closed (§4.4 and §4.2). Both were
taken on 2026-09-21 and are recorded in `DEVIATIONS-FOR-PAPER.md` §10.32 and §10.33, with
the times 16:14 and 16:20 (local time, UTC−3) written in the text. ~~Both were recorded
before the family was computed, and no number of the H1 family had been produced at either
point.~~ The two sections were committed in one piece with the estimates they report (at
16:22 local), so the commit timestamp dates the sections, not the decisions. The ordering
rests on the written times and on `ITT-PRELIMINAR.json`, a preliminary run of the
estimator (2 000 replicates) whose file time is 16:16:44 local and which cites §10.32. That
places the §10.32 decision (H1b, 16:14) before any estimate of the family. It places the
§10.33 decision (to keep the locked session-hour denominator, 16:20) **after** a
preliminary estimate existed: the preliminary file already holds the H1a difference,
−143.92, with an interval excluding zero. *(Corrected in rc7: earlier versions said that
no number of the H1 family had been produced at either point, which does not hold for
§10.33.)* The §10.33 decision kept the registered definition rather than changing it, so
seeing the number could not have bought a better-looking result through it; it is still
not a decision taken before the number. A file time is filesystem metadata, as forgeable
as a commit timestamp, and `ITT-PRELIMINAR.json` is not yet in the ballast manifest
(working list 17).

We state this first because it is the claim in this paper most dependent on our own
bookkeeping, and §9 of the analysis specification exists to forbid the opposite
order: *"choosing the primary set after seeing the number is the post-hoc play that this
spec exists to prevent."*

The evidence for it is also weaker than the evidence for everything else, by a gap we
created ourselves. We anchored the *assignment* in a public drand beacon so
that no one would have to trust us about it, and then anchored the decision log in
nothing but our own commit timestamps, which are forgeable in seconds. Append-only is
process discipline, not a cryptographic property. An adversarial reviewer put it as an
asymmetry, and it holds: we knew how to do this and did it for the easier
claim.

**What a reader can check without trusting us at all:**

- the MDE saturation of §4.1 is arithmetic over the spec's inclusion cuts (its fractional
  counting, and the 19 clusters the calculation counted: 11 treatment, 8 control), the
  pre-registered ICC and `p̂0`: outcome-independent, and reproducible from the artifacts;
- the designation's expiry of §3.0.1 (one `created_at` for all 19 items, a 30-day window),
  measured before the close (`out/expiracao-designados-2026-09-09.json`);
- the assignment, from drand round 31774052 through `assign_arms.py` to the served arms,
  and that the rule the seed declaration named gives a different assignment from the same
  round (§1; both rules run offline);
- the Epoch-1 coverage of §3.0 against the 36.7% stopping threshold, from the locked
  episodes and the planning artifact's list of promoted signatures, on the same terms as
  every estimate (next item);
- every estimate except the `control` mean 9.991 of §4.7 (B.1), from the artifacts of
  Appendix B, once deposited (working list 8).

**What requires trusting us:** the estimand decision of §4.4 preceded the estimates, and
the one of §4.2 preceded the final run but not the preliminary one (above); the primary
switch of §1 preceded the assignment seed; and both seed declarations preceded their drand
rounds (§1), which rests on our recorded push times against drand's public emission times.
The replacement of the declared assignment rule (§1) is dated by our commit log too, and
there the log works against us: it places the replacement after the round was emitted.
One thing speaks to our practice of committing before data, though not to these
orderings, which rest on our own timestamps: the spec omits `09-10` and marks nine
epochs as projection, which a fabricator writing
after the close would have had no reason to do. ~~And the spec contains a commitment the
data later refuted (§4.5). A post-hoc account would not contain a commitment that its
own data go on to contradict.~~ *(Struck in rc7: the realized coverage counts a different
quantity from the one the pre-commitment projected, so it neither refutes nor tests that
commitment; §4.5.)*

The core claim (the registration outlived its intervention, and the trial is under-powered
as a consequence) sits entirely in the first list. A reader
who disbelieves the second list loses §4.4 and should read H1, the deposited primary, as
the primary: it rejects (§4.0.2), and §4.3 states why we do not read that as an effect of
the dose. The rest of the paper stands.

**Caveat.** An earlier version of §9 overstated this: *"we knew this ten days before the
window closed."* On 2026-09-10 nine of the epochs were still projection. The spec's own extremes
analysis covers that (the bounding cases still return not-detectable), so the conclusion
holds, but it was projection-robust, not known; §9 now says so. And it was
projection-robust only under the spec's cuts. At the registered analysis set (11
treatment, 8 control) it holds under whole-epoch counting as well; counting whole epochs at
the sensitivity analysis's 11 treatment and 9 control, a cut the spec does not include, the
verdict flips (§4.1.1).

---

## 2. Design

**Randomization.** Stratified block randomization over four strata,
`(first calendar half | second half) × (weekday | weekend)`, with group counts allocated
by exact two-way controlled rounding and labels shuffled by a seeded Fisher-Yates. The
entropy stream is counter-mode SHA-256 rather than any language's PRNG, so that
*"re-run the committed script"* means re-run it in any language. Seed:
`SHA256(randomness_hex)` of drand round 31774052, hashed as lowercase ASCII text.
Allocation at N = 234: 117 control, 39 per dose.

The registered tolerance (every group × stratum cell receives its exact share rounded down
or up) holds by construction rather than by rejection sampling, so there is no
acceptance rate and no failure mode in which the sampler quietly relaxes a constraint.
Realized maximum deviation: 0.5 against a tolerance of 1.0.

**Washout.** Two hours from the epoch boundary; episodes inside it are excluded from the
analysis.

**Severity threshold.** `τ = S1`, locked in July 2026 on a calibration over five
model families (PREREG §697-699).

**Caveat.** We do not claim the outcome data "confirm" τ. A parameter locked in July is not
re-validated with data from the outcome period; that is post-hoc, and an earlier draft of
our own deviation log made exactly that claim before adversarial review removed it
(§10.31(5)). What the outcome data do show, and what we report instead, is an 11.9 pp
difference in marginal failure rates at the S0/S1 boundary (the boundary τ does *not*
absorb; a lower bound on their paired disagreement) between two
panel families (`google` 42.3% failure against `zhipu` 30.4%).

---

## 3. Execution: the realized window is not the projected one

The trial went `active` on 2026-09-01 at 10:25:39Z and the dose was switched off on
2026-09-21 at 09:43:05Z, closing the window at the `2026-09-20` epoch.

| | epochs |
|---|---:|
| registered design | 234 |
| designated in the realized window | **20** |
| served data | **19** |
| whole by clock exposure | **16** |
| partial by clock exposure | **3** (`09-01`, `09-03`, `09-20`) |
| empty | **1** (`09-02`, never served) |

Realized allocation over the 20 designated: **9 control · 6 at `w=2` · 4 at `w=4` · 1 at
`w=7.5`**, i.e. 9 control and 11 treatment.

**Correction.** Two different denominators, both correct, and we first wrote one number for both.

| analysis | epochs | why |
|---|---:|---|
| **ITT (§4.1–4.4), registered** | **19** | the analysis set of §2 of the analysis spec: `09-02` served no brief and is excluded, *counted and reported*. Its sessions produced **88 episodes**; it was designated control |
| ITT, sensitivity analysis | 20 | every designated epoch, `09-02` included; this was the ITT of versions up to rc7 |
| **coverage and M10 (§4.5–4.6)** | **19** | coverage is defined over served briefs, and `09-02` has none. The quantity does not exist there, which is not the same as being zero |

Earlier versions included `09-02` in the ITT on the ground that dropping a designated
epoch is post-randomization conditioning, the defect §3.1 records us committing once
already. The ground is real: `09-02` is empty because of an outage
(`INCIDENT-2026-09-02-epoch-perdido.md`), an event after randomization. But the analysis
spec, written before any outcome was computed, decided it the other way, and its decision
is the registered one; earlier versions overrode it without declaring that they did. The
cost is stated in §4.1: `09-02` is a control epoch with the second-highest per-epoch H1c of
the twenty, and its exclusion is the switch that moves H1c most.

**Deviation, declared in rc7; resolved in rc8.** §2 of the analysis spec excludes `09-02` from the analysis
set (*counted and reported*, and it records that excluding a control epoch worsens the
imbalance from 9 to 8). The ITT of rc7 included it, which the spec did not
pre-commit; the registered analysis of rc8 excludes it, and the rc7 analysis is reported as
a sensitivity.

**`09-01` is reported with both phases declared**, as §6 item 6 of the analysis spec
requires: 42 briefs in `shadow` until 10:22Z and 630 in `active` from 10:37Z, with no
overlap. The registered analysis counts it from its first `active` record
(10:37:01.943Z), which is how the spec's exposure offset is implemented (§3.0.1). The
sensitivity leg that removes it is reported alongside.

### 3.0 The stopping rule, and the feasibility question it raises

The trial closed at the `2026-09-20` epoch by a decision taken on 2026-09-21, executed by
`desliga-dose-p2.sh` at 09:43:05Z. It was not a data-dependent stop: no outcome had been
computed, and the analysis specification that governs this report was written on
2026-09-10, eleven days earlier (dated by our commit log; it was not deposited with the
registration, whose deposited version is v1.12). ~~That calendar decision is the whole of
the stopping rule.~~

**Correction (rc8): a declared stopping rule was met in Epoch 1 and not executed.** The
calendar decision was not the only stopping rule. `PROSPECTIVE-ESTIMAND-2026-08-30.md`
§3-bis, written before the assignment seed and dated by our commit log, made H1c primary
and declared *"a decisão de parar"*: if the coverage measured in Epoch 1 falls below
**36.7%**, the required effect exceeds 100% and the interventional arm is closed with a
null *"por impossibilidade de desenho, não por ausência de efeito"*. Coverage there is the
quantity of `out/CONCENTRATION-2026-08-30.json`: the share of opportunities whose signature
the dose can promote (the seven signatures that artifact lists as promotable at `w = 2`;
Epoch 1 ran at `w = 4`), 40.0% (611 of 1 526) in the planning corpus; the threshold is the H1c MDE of 36.7%, and the same section says that
measuring it *"é a primeira coisa que o Epoch 1 tem de fazer"*.

We find no record that it was measured. We have measured it now, from the locked
episodes, with the planning script's rule as written (an action is an opportunity if its
signature produced an `is_error` episode earlier in the corpus, which here begins on
2026-08-23; `_sprint-2026-10-04/B-rc8/checks-rc8.json`, block D). Epoch 1
(`09-01`, treatment at `w = 4`) has 139 opportunities, 45 of them in a promoted signature:
**32.4%** (Wilson 95% interval [25.2%; 40.5%], descriptive only). The condition the rule
names was met, and the arm was not closed. Three other readings of "coverage in Epoch 1"
are reported so that the verdict does not rest on our choice among them: 33.7% (34 of 101)
over the `active` phase alone, below the threshold; 40.0% (30 of 75) after the two-hour
washout, above it; and 54.5% of the HT-weighted opportunities under the trial's own
opportunity rule, above it. Counted against the 19 designated signature groups instead of
the seven promoted signatures, coverage is 92.1% (89.4% weighted), but that is not the
quantity the threshold was derived from. The reading that uses the rule's own definition
over the epoch it names is below the threshold, and so is the `active`-phase reading.

What this does to the paper: had the rule been executed, the interventional arm would have
ended after `09-01` with a null declared as design impossibility, and none of the H1-family
estimates of §4 would exist. We report them as what a trial that should have stopped
produced; they are not rescued by this section, and the verdict of §4.1 (H1c null,
no reduction detectable at 80% power) is the verdict the stopping rule anticipated. It is a
deviation, recorded in Appendix A, and the most consequential one we found ourselves.

### 3.0.1 `N = 234` was infeasible by construction, and the trial ran exactly as long as it could

An adversarial reviewer asked whether the fixed designation ages out of eligibility. It
does.

All 19 designated items live in `memory/entities/lessons/*.md`, the global sub-pool,
whose window is `freshGlobalMaxAgeDays = 30`. Their `source_date` is NULL in all 19, so
the predicate falls through to `created_at`, which is a single value for all nineteen:

```
created_at = 2026-08-21 22:51:23   (identical across all 19)
+ 30 days  = 2026-09-20 22:51:23   ← they leave the window together, in one instant
```

| | |
|---|---:|
| epochs registered | **234** (2026-09-01 → 2027-04-22) |
| epochs in which the designation is eligible | **20** (2026-09-01 → 2026-09-20) |
| share of the registered design that could carry an intervention | **8.5%** |

After that instant the intervention does not exist. A chunk that
fails `fetchFreshCandidates` never reaches the list handed to the boost provider, and the
boost is addressed by id. No value of `w` and no number of `freshSlots` reaches a
chunk that is not in the candidate list. For 214 of the 234 registered epochs, the
treatment arm and the control arm would have been the same intervention.

This changes how the stopping rule and the headline read. The trial did not stop early. It ran
for the entire interval in which the dose could reach a designated item: the designation
expired at 2026-09-20 22:51:23Z, and the dose was switched off later
(09:43:05Z on 2026-09-21), when it no longer reached any designated item. The `09-20` epoch
is partial for this reason and not by arbitrary
truncation: the analysis spec's cut *"falls inside the epoch, at 22:51:23Z"* is that
instant. ~~The analysis window closes at that instant.~~ The registered analysis closes the
window at that instant: the 33 episodes of `09-20` after expiry leave the analysis, taking
5 opportunities (22.835 weighted) and 2 weighted repeated failures with them, and `09-20`'s
session-hours fall from 0.6235 to 0.5154. It also applies the exposure offsets §2 of the
spec assigns to the partial epochs, as exposure windows on the timestamp axis, because the
ratio estimator has no offset term: `09-01` from its first `active` record (10:37:01.943Z),
`09-03` from its first served record (17:23:39.777Z, the end of the outage), `09-20` until
expiry. That reading of "offset" is ours, and for `09-03`, whose offset the spec gives only
as a volume (441 of 672 briefs), it is an interpretation. The cut is negligible on every
hypothesis; the offsets move H1 and H1a, because they shrink the session-hour denominator
of `09-01` (0.543 to 0.406 h) and `09-03` (0.457 to 0.246 h) (§4). The sensitivity analysis,
the estimator of earlier versions, selects episodes by epoch date and applies neither.

**Caveat.** The under-powering is a property of the registration, not a consequence of the
realized window. `sizing.py` computed `N = 234` from the pilot; nothing in that
computation knew that the designation it would act on had a 30-day life. Both numbers are
ours, both were locked, and they are incompatible: the same shape as the H1b collision of
§4.4, on a larger object: the trial was sized for 234 epochs on an intervention that
exists for 20.

We record two further facts so the finding is not overstated. The designation passed
the full eligibility predicate (file pattern, `importance/pain ≥ 0.7`, age ≤ 30 d) in
19 of 19 on 2026-09-09, in both the served corpus and `current.db`; expiry was a future
event, not a live defect. And the replay harness compensates for the window
(`cfgEm` offsets `freshGlobalMaxAgeDays`), so the expiry stops the trial and leaves the
instrument unaffected.

This was measurable on 2026-09-09 and was measured then, eleven days before the
close, in a session that recorded it and left the design decision open. It did not reach
this manuscript until an adversarial reviewer asked the question from the outside. The
measurement was ours; the reviewer saw that it belonged in the paper.

### 3.1 Two classification errors of ours, and what they cost

**Correction.** We classified `09-20` with the wrong ruler. We first published *16+3+1* as
*"17 whole + 2 partial + 1 empty"*, having measured delivery volume (672 of 672
serving records ⇒ "whole") where the pre-registered spec classifies by clock exposure
(13.86 h of 24 ⇒ partial, included with offset). The rulers are different and the
pre-registered one is not optional. The error propagated to six places including a pushed
commit, and was presented as *"matches the spec exactly"* when only the total matched
and the decomposition (which decides whether the epoch enters with an offset)
did not. Corrected in `DEVIATIONS-FOR-PAPER.md` §10.31(1).

**Correction.** We derived the arm from the data instead of from the designation. The first pass
took each epoch's arm as the mode of its observed `active` dose. That is
post-randomization conditioning: the mode is a function of *when* `active` took effect.
The arm is taken from `ASSIGNMENT-SERVING.json`. Compared, the two agree on 0
divergences across 19 epochs. The premise still changes, and the paper reports the
premise. This also voided a cross-validation we had claimed: comparing our own census
against the spec's table is not a second opinion, because both derive from the same
designation.

**Caveat.** The spec's own table **omits `09-10`**, summing to 19 against 20 allocated; it was
written on 2026-09-10 at 21:40 with that epoch still open. Including it gives 16 whole.
We record this rather than silently reconciling, because a miscount in the spec and a
miscount by the analyst need different fixes.

---

## 4. Results

**Estimator.** `estimador_itt.py`, which is composition, not reimplementation: it
imports `carregar_verdicts`, `carregar_episodios` and `span_por_sessao` from the pilot's
replay module and the arm from the assignment file. Two copies of one rule can silently
select different populations, a defect class this project has already paid
for once. The registered analysis is `measurement/estimador_itt_registrado.py`
(`out/ITT-REGISTRADO-2026-10-05.json`). It imports the same blocks and those of
`rerandomizacao.py`, leaves both files unmodified, and adds four switches, one per
departure of the earlier analysis from the registration: panel, window, interval and
epoch set. With every switch at the earlier choice it rebuilds `ITT-2026-09-21.json` and
`RERANDOMIZACAO-2026-09-21.json` byte for byte (sha256 compared at run time), so every
difference between the registered analysis and the sensitivity analysis below comes from
the switches and none from a reimplementation.

**What moves what** (one switch at a time, the others at the earlier choice; the
artifact's `deltas_um_a_um`). The epoch set moves H1c most: excluding `09-02`, a control
epoch whose own H1c (0.190) is the second-highest of the twenty, takes the H1c difference
from −0.0199 to −0.0113 and its p-value from 0.160 to 0.439. The window acts on H1 and H1a
almost entirely through the offsets (H1a's p-value from 0.0855 to 0.0375 with the offsets
alone), while the expiry cut alone moves no hypothesis by more than 0.5% of its estimate.
The panel substitution resolves 20 more episodes (1 159 to 1 179) and moves H1c to −0.0208.
BCa changes only the intervals. Removing the epoch-set switch from the registered analysis
puts H1c back at −0.0209 (`p = 0.152`).

**Adjudication.** 1 195 episodes, 395 in stratum A (census of `is_error`) and 800 in stratum B
(hash-ordered sample), were submitted to three model families from distinct training
lineages, as locked in PREREG §682. ~~Coverage 100%.~~ All 1 195 were submitted to the
three-family panel; 1 159 (97.0%) met the three-substantive-verdict requirement and 36
remained `unknown`. The registered analysis applies the substitution rule of §6 item 7
(DEVIATIONS §10.31): the fourth family's verdict is added only to those 36, and the
three-verdict floor is applied again. That adjudicates 20 more episodes, 13 of them as
failures, for 1 179 adjudicated and 16 `unknown`; no episode the three families had
adjudicated changes verdict (checked: 0). The sensitivity analysis uses the three families
alone. The unknown share of opportunities is 1.02% (1.34% in the sensitivity analysis), so
the registered 10% missing-data rule does not fire. Horvitz-Thompson weight for stratum B:
6.945 (5 556 / 800). Strict majority; an exact tie (*n*/2 failures, possible only with
an even number *n* of
substantive verdicts) resolves to `not_failure`, which `pilot_replay.py` l.145-148 declares
as *"conservative: it underestimates failures"*. In the primary panel the rule cannot bind:
an episode needs at least three substantive verdicts to be adjudicated
(`carregar_verdicts`), and with three families three cannot tie. Nor can it bind in the
registered substitution panel: the fourth verdict is added only where the three families
left fewer than three substantive verdicts, so an adjudicated episode there has exactly
three (counted: 0 ties). It binds in the four-vote
sensitivity set, where a 2-2 tie is possible. There it is directional bias toward fewer
failures, not indeterminacy; its effect on the treatment-control contrast depends on the
arms the ties fall in, which ~~we have not counted~~ we have now counted
(`out/C12-EMPATES-POR-BRACO-2026-10-05.json`, rc4). Under the registered window and epoch
set (`out/C12-EMPATES-REGISTRADO-2026-10-05.json`, rc8) the four-vote set's 28 exact ties
fall 10 in treatment epochs and 10 in control; 7 lie outside the trial dates and one, a
control tie in `09-03`, before that epoch's exposure window; `09-02` holds none. The tied
H1c opportunities are the same 4 (treatment) and 7 (control). The rc4 count below was made
under the window of the sensitivity analysis. The four-vote set has 28 exact ties: 10
in treatment epochs, 11 in control and 7 outside the window. Of the 21 in the window, 4
(treatment) and 7 (control) are H1c opportunities, and none of those 11 was a failure under
the three-family majority, so relative to the three-family labels the rule removes no
repeated failure from either arm. Nor does it move any signature's first failure, which
leaves condition (i) unchanged. Only 3 of the 28 ties change a label (failure to
`not_failure`): one in each arm, neither of them an opportunity, and one outside the window.
Relative to the opposite resolution (tie → `failure`) the rule is not neutral: it holds the
4 treatment and 7 control tied opportunities, HT weights 27.78 and 36.73, at `not_failure`.
Resolving all 28 ties as `failure` moves the four-vote H1c point difference, under the
registered window and epoch set, from −0.0121 (equal to the registered estimate, since no
tie changes a label among its opportunities) to −0.0211
(`out/C12-EMPATES-REGISTRADO-2026-10-05.json`; point only, no interval; opportunities do
not change). Under the sensitivity analysis's window it moves from −0.0208 to −0.0266
(`out/C12-EMPATES-COMO-FAILURE-2026-10-05.json`, rerunning `estimador_itt.py`; the rerun and the first-order
calculation agree, −0.0266; the sixth decimal differs, −0.026571 against −0.026566,
because the rerun's difference is taken from the artifact's per-arm proportions, one of
which is stored rounded, 0.09189). The rule pulls the four-vote contrast toward zero.

**The combined estimator, written out.** The first draft omitted it, and without it a
reader cannot tell a ratio-of-totals from a mean-of-ratios. Per arm, over epochs in the
window and episodes past washout satisfying the implemented proxy for condition (i) of the
registered definition of a repeated failure. PREREG §4.1 requires that the serving snapshot
at session start contained a failure episode of the same signature, at severity ≥ τ,
written at least one epoch length before the epoch. The estimator does not check snapshot
membership, since the historical snapshots are pruned by design; it requires that the
adjudicated corpus contain a failure (severity ≥ τ) of the same signature whose epoch
begins at least one epoch length before the episode's epoch (`estimador_itt.py`, first
failure per signature; `pilot_replay.py` declares this reconstruction an approximation):

```
opportunities = Σ w(e)                 repeats = Σ w(e)·1[state = failure]
                                       w(e) = 1        if e ∈ stratum A (census)
H1c = repeats / opportunities          w(e) = 6.945    if e ∈ stratum B (sampled)
                                       e skipped       if in neither
```

`unknown` verdicts count in the denominator and not in the numerator, per §5 of the spec.
It is a ratio of weighted totals, not an average of per-epoch ratios.

**Uncertainty.** Cluster bootstrap with the epoch as the resampling unit, resampled within
arm, 10 000 replicates, seed `20260921` declared. The registered analysis uses the
construction the registration locks: BCa, with the acceleration from the
leave-one-epoch-out jackknife, each deletion inside its own arm (PREREG §5). The
registration says the jackknife runs over all 234 epochs; only 19 exist, so it runs over
them. BCa never fell back to percentile. Its lower adjusted quantiles are extreme for H1
and H1a (0.0017 and 0.0009), so their lower bounds are the 18th and the 9th smallest of
10 000 replicates and carry visible Monte-Carlo noise. The sensitivity analysis uses the
percentile construction, which the registration allows only as a fallback when the
acceleration is undefined; earlier versions used it without that condition.

### 4.0.1 Two registered analyses we did not run, declared as deviations

Both were found by adversarial review of this manuscript, not by us.

#### 4.0.1a The registered inference test is re-randomization, not bootstrap, and we have now run it

§4 of the analysis spec locks 10 000 re-randomizations, *"redesign the 234,
never permute within the 20"*, over the trend-residualized outcome. The first draft
reported cluster bootstrap and did not declare the substitution. That was the worse
half of the error: the bootstrap assumes an iid draw of epochs, whereas the design
randomizes with stratification and exact controlled rounding, so its reference
distribution is not the one the design generates.

`rerandomizacao.py` imports `assign_arms.assign` and redesigns all 234 epochs per
replicate, restricting to the window; it never permutes labels among the 20, which the spec
pre-commits against because the 20 fall entirely in the first calendar half, where the
stratification collapses. Control: 300 distinct arm patterns in 300 replicates, which
reproduces the spec's own measurement of zero collisions; at 10 000 it is 9 941 distinct
over the 20 epochs of the sensitivity analysis and 9 903 over the 19 of the registered
analysis, which runs the same redesigns. The results are in §4.0.2.

#### 4.0.1b The pre-committed instrument controls: all three run

§5 of the spec defines three. The first draft reported none, which for a paper whose
stated contribution is *"the reportable results are about instruments"* was the worst
omission in it.

**Caveat.** The spec measured the first two on 2026-09-10, with the trial still running: 6/6
and 3/3 over a partial window. We re-measured over all 19 served epochs (`09-02` served
none), because a control measured midway does not cover what came after.

**Semantics, declared before the numbers:** `mexeu` compares `ids_tratado` with
`ids_controle` by membership (`set`), never as a list. List comparison mixes reordering
with entry/exit and at epoch `09-08` returns 48 against 20.

| control | statement | result |
|---|---|---|
| **positive** | a served treatment epoch has `mexeu > 0` | **passed, 11 / 11** (was 6/6 at midpoint) |
| **negative dual** | a control epoch has `sem_ids == n` | **passed, 8 / 8** (was 3/3) |
| **specificity (sham)** | replay 19 non-designated items at the same `w` | ~~running since 2026-09-22 01:40Z~~ ~~**not executed** — the configuration launched was invalid; a valid one is runnable and not yet run (§4.0.1c)~~ **passed, rank 1 of 21**: real designation 132 changed states against 81–122 for 20 shams, `p = 1/21 = 0.0476` (the floor at `K = 20`); restricted to the 2,646 brief states of the `w = 4` epochs and to shams drawn from the 36 boostable items (§4.0.1c) |

The positive control ranges from 2.83% to 6.85% of briefs altered per treatment epoch
(`09-09` lowest, `09-14` highest), counted over all 672 briefs of each epoch. On `09-01`
that count includes the 42 briefs served in shadow mode, before the dose went active, two of
which changed only as counterfactuals; over its 630 active briefs, 22 changed (3.49%).
Over all treatment epochs, 335 of the 7 350 briefs served in active mode changed (4.56%);
the artifact's 337 of 7 392 includes the two shadow changes. Had any treatment epoch returned 0, the null would be
the instrument's and not the effect's. That is the whole purpose of the control, and it
is the reason the null of §4.1 can be read as being about the treatment at all.

The negative dual is stated that way for a reason the spec works out and we repeat: the
obvious form, *"a control epoch has `mexeu == 0`"*, is invalid, because at `w=0` the
`ids_*` fields do not exist at all, so `mexeu == 0` is indistinguishable from *"the field
was never written"*. Such a predicate cannot detect missing data, because it needs that
data to be evaluated.

Our first attempt at the specificity control was invalid. We
counted how many briefs contain a sham chunk in `ids_tratado` and compared against the
designated set. It returned real 2 069 against a sham median of 5 832 and read as a
failed instrument. The failure was the test's. `ids_tratado` is post-dose, so
counting presence inside it is the candidate the spec's own table already labels
*tautological*; with a universe of 141 ids, the non-designated set includes the chunks
that enter nearly every brief, while the designated are one per signature group and
therefore rarer. The quantity measured is chunk frequency, not specificity.

The pre-committed sham is a replay: re-execute the dose mechanism with 19
non-designated items at the same `w` and compare the churn it produces. That requires
running the serving code, not reading its log, because the log only contains the outcome of the
designation that actually ran. It was declared as not run rather than reported as
failed; the near-miss above shows why that difference matters.

~~**It is now running** (launched 2026-09-22 01:40Z, `measurement/roda-sham.sh`).
21 runs of `replay-oportunidade.mjs --modo dose` at `w = 4` — one with the real
designation as baseline, 20 with sham designations — sequential, `nice -n 19 ionice -c3`,
because each run exceeds 15 min and the host serves production on 2 vCPU. Expected wall
clock ≈ 5 h.~~

**Correction (2026-10-04).** The paragraph struck above was stale when it was written
into this draft and wrong about what the run would measure. The run produced no output and
was aborted; the configuration it used was invalid for the reasons measured in §4.0.1c.
The three design choices below are kept because two of them remain right, and the third
is the one that let the error through.

Three choices in that design, each with its reason:

- **`K = 20` is the minimum, not a round number.** With 21 runs the smallest attainable
  rank p-value is `1/21 = 4.8%`; with fewer shams the test cannot reject at 5%
  no matter what it finds. It is a randomization p-value only to the extent that the shams
  are drawn by the same mechanism as the real designation, which neither configuration
  of §4.0.1c does: the real designation is one item per signature group, while the shams
  are drawn at random from a pool and mapped onto the signature keys arbitrarily
  (`gera-shams.py`; the corrected `sprint-gera-shams-v2.py` matches severity and bonus
  mass, not signature group).
- **The shams are drawn from the eligible pool, not from the corpus.** A sham chunk that
  fails the eligibility predicate never reaches the candidate list, so it would "not move"
  by construction, and the test would report specificity where there was only
  ineligibility. That is the mirror image of the tautological candidate the spec rejects,
  and it is why `gera-shams.py` applies the 30-day window as well as the path and floor
  predicates. *(2026-10-04: the principle stands; the pool it was applied to did not. See
  §4.0.1c: `gera-shams.py` drew from the 115-chunk pool of a corpus that did not serve
  the trial; the served pool has 108. And eligibility is not enough: only 36 of the 89
  non-designated items in the served pool can receive a bonus at all, so the run of
  §4.0.1c draws its shams from those 36.)*
- **The predicate has an independent control.** Our SQL with the age window returns
  115 eligible chunks, and the replay independently *observes* `pool: 115` at the same
  `t-ref`. Two routes, one number; without that agreement we would not know whether the
  pool we sample from is the pool the mechanism sees. *(2026-10-04: both routes read the
  same corpus, `corpus-preservado-20260908.db`, so their agreement could not detect that
  the corpus itself was the wrong one. On the corpus that served the trial the pool is
  108 in 22/22 measured states; see §4.0.1c.)*

**One limitation, declared.** The corpus of the published anchor
(`e20260826T060003Z.db`) no longer exists; it was pruned. ~~This runs on
`corpus-preservado-20260908.db`, the deliberately preserved corpus of the trial, so it
cannot reproduce the published anchor and does not try to: the comparison is internal,
real against sham on **one** corpus, which is what specificity needs.~~

**Correction (2026-10-04).** The struck sentence is factually wrong on two counts.
`corpus-preservado-20260908.db` is not the corpus that served the trial: it was
preserved from the live database on 2026-09-08, after 60 `memory/lessons.md` chunks had
been re-ingested on 2026-09-07, and production never served them (DEVIATIONS §10.10,
§10.14; §4.0.1c). The corpus that served is the one the serving process held open from
2026-09-03, recovered from its file descriptor as
`corpus-SERVING-REAL-e20260903-recuperado.db`. And "one corpus" does not rescue the
comparison when, on that corpus, the real arm cannot move at any dose (§4.0.1c).

Artifact: `CONTROLES-JANELA-COMPLETA-2026-09-21.json`.

<!-- SHAM-JANELA: pending -->
#### 4.0.1c The specificity control: invalid as first configured, then run

**What was launched, and what it measured.** The design was 21 replays
(`measurement/roda-sham.sh`): the real designation as baseline and 20 sham designations of
19 non-designated items each, at the same `w`. It was launched on 2026-09-22 at 01:40Z.
The first 12 runs each hit our own 3 600 s time limit (`exit 124`) and wrote no output, and
the loop was aborted at 13:45Z (project log `docs/HANDOFF.md` at the repository root,
entry of 2026-09-22). `exit 124` is our timeout, not a verdict: **the launched sham measured nothing.**

**The probes, and the reading we gave them.** Two probes then replayed the real
designation alone, at `w = 4` and `w = 100 000`: one state (`sonda2`), and the **132**
states in which production recorded `ids_tratado ≠ ids_controle` (`sonda3`). Both returned
`churn = 0` in every state at both doses (`out/NOGO-replay-sonda{2,3}-2026-09-23.json`).
`sonda3`'s replayed *control* set matched production's in **0 of 132** states, and none
of production's fresh-slot ids appeared in any of them. Our log of 2026-09-23 read this as
a test without power (the real arm is 0, no sham can exceed it, so
`p = #{sham ≥ real} / 21 = 21/21 = 1.0` "by construction") and named, as the remaining
explanation, a hypothesis it declared untested: that the serve-state the replay derives
today loses the ties in `last_served` that production saw, leaving strata of one, where an intra-stratum bonus
never decides. **That reading made a property of the configuration look like a property of
the design.** The tie hypothesis is refuted, and `p = 1.0` would have followed from the
corpus and the cut, not from the replay or from the sham design.

**The cause, measured on 2026-10-04.** Two defects: the first alone yields exactly zero at
any dose, the second alone nearly so (1/22 at `w = 100 000`):

1. **The wrong corpus (the main cause).** `sonda3` and `roda-sham.sh` both read
   `corpus-preservado-20260908.db`. It holds 60 `memory/lessons.md` chunks re-ingested on
   2026-09-07 that production never had: its maximum id is 309 497, against 308 752 in
   the corpus that served, and the serving log contains no id above 308 752 before
   2026-09-21T09:52:04Z. That the serving process stayed on the fd-pinned corpus through
   2026-09-20 is an **inference** from that log and from DEVIATIONS §10.14, not a direct
   observation. In the coverage order (`last_served IS NULL` first, then
   `last_served ASC`, ties broken by `salience + boost`; `freshSlots = 2`), those 60
   never-served chunks form the boundary stratum in **22/22** measured states, with **no**
   designated item in it; the first designated item sits at pool position 60–66. The
   bonus breaks ties only inside a stratum, so no `w` reaches a designated item there.
2. **The inclusive cut (an aggravating defect).** `--corte inclusivo` (`served_at <= T`)
   puts the brief's own serves into its own serve-state. Even on the served corpus it
   reproduces production's control in only 2/22 states and moves 1/22 at `w = 100 000`.
   The exact cut is `rowid` (`id <` the brief's first row).

**The control of the diagnosis.** The same, unmodified `replay-oportunidade.mjs`, on the 22
states for which the trial's `brief_log` survives off the production host:

| corpus | serve-state cut | control / churn / entering id = production | moved at `w = 2` | moved at `w = 100 000` |
|---|---|---|---:|---:|
| preserved | inclusive *(the sham's configuration)* | 0 / 0 / 0 of 22 | 0/22 | **0/22** |
| preserved | `rowid` | 0 / 0 / 0 of 22 | 0/22 | **0/22** |
| served | inclusive | 2 / 1 / 0 of 22 | 0/22 | 1/22 |
| **served** | **`rowid`** | **22 / 22 / 22 of 22** | **17/22** | **22/22** |

With the served corpus and the exact cut the replay **reproduces production exactly** and
**responds to dose**. The stratum structure of production's state (served corpus, `rowid`)
also refutes the tie hypothesis directly: the pool is 108 chunks with none never-served; the
boundary stratum has a median of 4 members (range 3–4) and holds 1–3 designated items in
22/22 states; production's entering chunk ties with its leaving chunk in 22/22; and the
median number of singleton strata per state is 0. Ties were not lost. The inclusive cut
thins them (enter/leave tie in 8/22), which is the only part of the hypothesis with any
truth, and it is secondary.

**The sham pool was wrong too.** `gera-shams.py` draws shams from the 115-chunk pool of
the preserved corpus (it asserts `len(cand) == 115`). Minus the 19 designated, that leaves
96 candidates, **60** of which are the never-served chunks that, on that corpus, form the
only stratum where a bonus decides. A sham of 19 drawn from those 96 is expected to contain
11.9 of them, and the probability that a sham contains none is 1.5 × 10⁻¹⁰
(hypergeometric arithmetic on these counts). On that corpus, then, shams could move and the
real designation could not: running the 21 replays would most likely have returned
"sham ≥ real", which reads as **failed specificity** and would have been the corpus's
failure. This is a **prediction** from the measured strata and that arithmetic; no sham
designation was ever replayed.

**What a valid sham needs, and how each need was met.** (i) The served corpus,
`corpus-SERVING-REAL-e20260903-recuperado.db`; (ii) the `rowid` cut; (iii) shams redrawn
from the served pool (108 chunks, 89 non-designated); (iv) a `brief_log` covering the trial
through 2026-09-20. ~~The first three are in hand. The fourth is not: the copy we can work on
off-host ends at 2026-09-08 05:52:04, and the trial's `brief_log` after that exists only
on the production host. Exporting it is **pending authorization**. At about one minute of
wall clock per 22 states, cost is not the obstacle. **The valid sham is runnable; it has
not been run.**~~ *(rc3: all four were met by 2026-10-04.)* For (iv) we worked on an
export of the trial's `brief_log`; where it overlaps the `brief_log` held in the served and
in the preserved corpus, its rows are hash-equal to theirs (`B-sham-v2/REPORT.md` §1.2).
(iii) needed a further correction, given with the result below. On the corpus: twelve
daily readings (2026-09-10 to 09-21) of the sha256 of the file the serving process held
open, taken through its file descriptor, return one value, equal to the served copy. A
restart would have opened a newer epoch, and a file descriptor cannot return to a deleted
file, so with the same file measured on 09-08 and the process start dated to 2026-09-03
17:23:30Z (DEVIATIONS §10.10), every state from then to 09-21 was served by that file
(`B-sham-v2/REPORT.md` §1.1). This turns the **inference** stated in defect 1 above into
daily measurements plus an argument for the gaps between them.

**What was measured and what was not.**

| | states | status |
|---|---:|---|
| fidelity and dose response, served corpus + `rowid` | **22 of 132** | **measured** — all timestamped between 2026-09-01T11:07Z and 2026-09-02T08:37Z, i.e. inside the single treatment epoch `09-01` (09:00 UTC boundary) |
| the same, for the states timestamped 2026-09-12 to 09-16 | **110 of 132** | ~~**not measured** — needs (iv). For these states only two facts are measured: the probe's control mismatch (0/132) and that production never served the chunks the probe put in the fresh slots. That the dose would also respond there is an **expectation**~~ **measured (rc3)**: control set, churn, entering id and boost count equal production in 110/110; at `w = 4` the dose moves 110/110, as in production (`B-sham-v2/fidelity-110/`) |
| every brief state of the four `w = 4` epochs (`09-01`, `09-12`, `09-14`, `09-15`), real designation | **2,646** | **measured (rc3)**: control set equal to production in 2,646/2,646 (630/630 at `09-01`, 672/672 in each of the others); churn and entering id at `w = 4` equal in 2,646/2,646; 132 states moved, production's 132 |
| a sham designation replayed | ~~0~~ **20** | ~~**not run**~~ **run (rc3)**: 20 of 20 validated, 2,646 states each, 0 errors |
| byte-identity of the serving `dist/` used with the build that served | — | **not measured**; it was rebuilt from source (2026-09-29 for the 22-state test, again for the sham run) whose `src/api/brief.ts` matches the probe's recorded hash; the 22/22, 110/110 and 2,646/2,646 exact reproductions are the functional check |

**The sham, run (2026-10-04).** Twenty-one replays (`measurement/sprint-roda-sham-v2.sh`):
the real designation and `K = 20` sham designations of 19 non-designated items each, on
the served corpus with the `rowid` cut, at `w = 4` and, as positive control, at
`w = 100 000`, over the same 2,646 brief states. The statistic is the number of states
whose served brief differs from the undosed one (`mexeu`, by membership), and total churn.

| statistic, `w = 4` | real | 20 shams (min–max) | shams ≥ real | `p = (1 + #{sham ≥ real}) / 21` |
|---|---:|---|---:|---:|
| states moved (`mexeu`) | **132** | 81–122 | 0 | **0.0476** |
| total churn | **146** | 84–132 | 0 | **0.0476** |

At `w = 100 000` the real designation moves 155 states and the shams 81–122. The real run
is identical in its dose detail to the earlier calibration run of the real designation,
and it reproduces production in 2,646/2,646 states (table above). The replay is
deterministic; three sham runs were slowed by CPU throttling on the host, which changed
their wall time and not their output.

**What it shows, and what it does not.** No sham reached the real designation on either
statistic, so the rank p-value is `1/21 = 0.0476`, the floor at `K = 20`: it says the real
designation exceeded every sham, and at this `K` it cannot say more. It is evidence that the
dose effect on **what was served** is specific to the designated items rather than the
background churn that **these 20** severity- and bonus-matched designations produce at
`w = 4`; it does not extend to every designation of that severity and bonus mass. Nor is
the rank p-value a calibrated randomization p-value: the shams are matched on severity and
bonus mass but not drawn by the real designation's rule (one item per signature group), so
real and sham are not exchangeable draws of one mechanism (third limit below). The specificity is relative: the matched shams also move 81–122 states, so most
of the real designation's churn is what a comparable designation produces, and the real
designation exceeds the largest sham by 10 states. It says nothing about the trial's
outcomes; whether serving the designated items changed repeated failures is H1c (§4.1),
a different question. Four declared limits:

- **The state set is restricted to the `w = 4` epochs.** This is a deviation from the
  configured instrument (`roda-sham.sh`, which replayed the whole serving log; the
  configuration was ours, not pre-registered). The reasons: `w = 4` is the registered
  "same `w`"; the epochs were randomized, so selecting them does not depend on the
  outcome; the corpus that served is verified in every one of these states and production
  can be checked directly against them; and the configured whole-log set (19,567 states,
  about 8,000 of them from the shadow phase, whose corpus is not identifiable) would have
  taken about 60 h, and the hash-verified trial window (11,865 states) about 36 h as
  estimated then, against a projected 8 h for this set. A replay over the whole trial window
  is now running (`job-janela2`, relaunched 2026-10-05T09:39:53Z, expected to finish about
  2026-10-07T03:00Z): 11,812 reconstructible states of 18 epochs, which excludes epoch
  `09-01`, whose corpus has no hash proof, and 53 states whose serve-state cut cannot be
  reconstructed (11,865 − 53). Its result will be added before deposit.
- **The shams are drawn from the 36 boostable items, not from all 89 non-designated.** The
  serving code gives a bonus only to ids in the designation, real or sham, that have a `p2_verdict` row of
  severity S1–S4 written at least one day before the epoch; 53 of the 89 non-designated
  pool items have none and receive a bonus of zero by code. Shams drawn from all 89
  (generated, not run) carry 21–50% of the real designation's bonus mass, which would bias
  the test toward "real > sham". The 20 shams are drawn from the 36, stratified as the
  real designation is (10 S1, 9 S2), so each carries the same bonus mass, `0.301·w`. Drawn from 36, the shams overlap:
  6–14 shared items per pair (mean 10.4), none shared with the real designation.
- **The match is on severity and bonus mass, not on signature group** (§4.0.1b, `K = 20`
  bullet), so the rank p-value is a randomization p-value only to that extent.
- **`p` is at its floor.** With `K = 20` no result could give a smaller `p`, and a single
  sham at or above the real designation would have moved it to `2/21 = 0.095`.

**Our error, stated.** DEVIATIONS §10.14–§10.15 had measured this mechanism on 2026-09-09:
on the recovered corpus `mexeu(2) = 20` and `mexeu(10⁵) = 37`, matching production's
`churn > 0 = 20`; on the realigned corpus `0 / 0`; cause, a never-served cohort holding the
`freshSlots`. The sham was nevertheless configured on a corpus of the family §10.15 shows
to be blind, and the HANDOFF hypothesis of 2026-09-23 reopened a question §10.15 had
already answered.

**What this does to the claims of this paper.** Nothing in §4.1–4.7 rests on the sham. The
positive control (11/11) establishes that the mechanism changed briefs in every
treatment epoch; ~~until a valid sham is run, **nothing here establishes that the change is
specific to the designated items** rather than background churn at the same `w`~~ the sham
establishes, on the `w = 4` epochs, that the change is larger for the designated items than
for any of 20 matched sham designations at the same `w`. Neither control bears on whether
the change reached outcomes. The null of §4.1 stands as reported; the two controls make it
a null about a lever that changed 2.83–6.85% of briefs per treatment epoch (§4.0.1b), more
through the designated items than through matched others.

Artifacts: `out/NOGO-replay-sonda{2,3}-2026-09-23.json`;
`_sprint-2026-10-04/B-replay-fidelity.md`, its eight runs and stratum files in
`_sprint-2026-10-04/B-replay-fidelity/` (summary `RESUMO.txt`);
`measurement/sprint-replay-estratos.mjs`; `measurement/sprint-replay-fidelidade-resumo.py`.
For the sham run: `_sprint-2026-10-04/B-sham-v2/REPORT.md` (§7 holds the result);
`B-sham-v2/job-v2b/RESUMO.json` (every number of the sham table and the positive control);
`B-sham-v2/job-v2b-runs.tgz` (the 21 runs) with `B-sham-v2/job-v2b/RUNS.sha256`;
`B-sham-v2/fidelity-110/` (the 110 states); the generator, runner, test and summarizer
`measurement/sprint-gera-shams-v2.py`, `sprint-roda-sham-v2.sh`,
`sprint-testa-roda-sham-v2.sh`, `sprint-resume-sham-v2.py`.
<!-- /SHAM-JANELA -->
### 4.0.2 The registered test against the bootstrap, and the Holm rule on H1a

| outcome | re-randomization *p*, unadjusted (registered analysis; sensitivity) | rejects under the registered decision rule? | what the bootstrap said (BCa; percentile in the sensitivity analysis) |
|---|---:|---|---|
| **H1c** (primary in this report) | **0.434**; 0.1603 | no (primary, α = 0.05; in the Holm family, adjusted 1.0) | contains zero in both — **agree** |
| **H1a** | **0.0241**; 0.0855 | **no**: decided in the Holm family, adjusted 0.1205 (m = 5) or 0.0964 (m = 4); 0.43 or 0.34 in the sensitivity analysis | excluded zero in both — **disagree** |
| `H1` (the deposited primary) | **0.0133**; 0.0127 | yes (tested alone at α = 0.05) | excluded zero in both — agree |

H1a's unadjusted p-value falls below 0.05 in the registered analysis and did not in the
sensitivity analysis; the offsets of the partial epochs move it (§4). It is still not a
rejection. The registration puts H1a in the Holm family with H1b, H1c and the two
components of H2, and under Holm the first threshold is 0.01 (0.0125 without H1b); 0.0241
exceeds both, so the step-down stops before H1a and nothing in the family rejects. Reading
0.0241 against 0.05 would apply a decision rule the registration does not contain.

**Different estimand, stated so the numbers are not compared naively.** The permutation
statistic is a difference of arm means over per-epoch outcomes residualized on study-day;
the ITT of §4.1 is a ratio of weighted totals. They answer related questions, not the same
one, and the observed statistic here (−0.0162 for H1c; −0.0323 in the sensitivity
analysis) is not the −0.0121 of §4.1 (−0.0199).
What transfers is the verdict, not the magnitude, and the registered scope is narrow by
construction: this tests the sharp null of *zero total effect*, and rejection alone does
not attribute magnitude.

**What this settles, and it is not in our favour rhetorically.** §4.2 argued that H1a
"does not bear weight" from the sparse-session mechanism. The registered decision rule
reaches the same verdict by a route that does not need that argument, and it is the
inference we weight (§8.3). The disagreement is what an under-covering interval would
produce, and it is also what two different estimands and a multiplicity rule can produce;
this does not demonstrate any of them. We would
rather have found this before an adversarial reviewer told us the test was missing.

`H1` rejects under both. It remains uninterpreted for the reason of §4.3: carried only by
the briefs the dose alters, in proportion to their share, the observed reduction
(69.8% on the locked leg; 70.7% in the sensitivity analysis) would amount to 22.2 times
total elimination at the pre-trial calibration share (3.14%) and 15.3 times at the share
realized in the trial (4.56%, §4.0.1b). These are proportional-dilution calculations, not causal bounds (§4.3 states what they assume), and
they are now the *only* reason standing, since the inference no longer supports dismissing
the rejection as a bootstrap artifact. We report it as an unexplained rejection: the
category for a result that survives the registered test at a magnitude the
dose's reach does not account for.

Artifacts: `out/ITT-REGISTRADO-2026-10-05.json` (field `multiplicidade` holds both Holm
variants); `RERANDOMIZACAO-2026-09-21.json` for the sensitivity analysis; seed prefix
`p2-rerand-2026-09-21` declared for both.

### 4.1 H1c: the primary outcome, null and not detectable at 80% power

| leg | treatment | control | difference | 95% CI | |
|---|---:|---:|---:|---|---|
| **locked (the 19 epochs of the analysis set)** | 0.0675 | 0.0796 | **−0.0121** | [−0.0445; +0.0125] | contains zero |
| **pre-committed sensitivity** — all partials removed | 0.0697 | 0.0884 | −0.0187 | [−0.0596; +0.0094] | contains zero |
| post-hoc sensitivity — without `09-14` | — | — | −0.0159 | [−0.0485; +0.0098] | contains zero |
| *sensitivity analysis* (rc7: 20 epochs, three-family panel, no window cut, percentile) — locked | 0.0696 | 0.0896 | −0.0199 | [−0.0560; +0.0086] | contains zero |
| *sensitivity analysis* — pre-committed sensitivity | 0.0721 | 0.0994 | −0.0273 | [−0.0725; +0.0061] | contains zero |
| *sensitivity analysis* — without `09-14` | — | — | −0.0244 | [−0.0619; +0.0051] | contains zero |

The first three rows are the registered analysis, with BCa intervals
(`out/ITT-REGISTRADO-2026-10-05.json` for the locked leg; the two sensitivity legs run
through the same estimator in `_sprint-2026-10-04/B-rc8/checks-rc8.json`, block A, which
first reproduces the artifact's locked leg exactly). The pre-committed leg removes the
partials `09-01`, `09-03` and `09-20` from the 19, leaving 10 treatment and 6 control
epochs.

**Which sensitivity is the registered one, and our error in the first draft.** §9.1 of
the analysis spec pre-commits *"the standard sensitivity that removes **all** the partials
as a block"*: `09-01`, `09-03`, `09-20`. The first draft of this paper reported instead a
sensitivity that removes `09-14`, which was chosen after seeing that one epoch dominates
exposure and was never pre-committed. Both are now reported, the registered one first
and labelled as such. We state the direction: the pre-committed leg is *more*
favourable to our reading than the post-hoc one we had picked, so the substitution gained
us nothing. That makes it a process failure rather than a self-serving one, and still a
failure. *(rc8: the direction held for the percentile intervals of the analysis now
reported as a sensitivity. Under the registered BCa interval it reverses for H1a, where the
pre-committed leg excludes zero and only the post-hoc leg contains it (§4.2); so for H1a
the leg we had picked after seeing the data was the more favourable one.)*

This is the stable outcome of the study: all three legs contain zero in the registered
analysis, and all three contain zero in the sensitivity analysis.

### 4.1.1 Our two uncertainty statements rest on different constructions

§3 of the analysis spec pre-commits this sentence:

> *"Under the realized inclusion criterion and `ICC = 0.0985`, **not even total
> elimination of repeated failures is detectable at 80% power**."*

Control sits at `H1c = 0.0796` in the registered analysis, so "total elimination" is an
effect of −0.0796, and the observed interval excludes it by 0.0351 (0.0896, −0.0896 and
0.0335 in the sensitivity analysis). That alone is not a contradiction: a power
statement is about the probability of rejection (80%), not about every realized interval,
and a single realized interval can exclude an effect that the design detects with less
than 80% probability.

~~The contradiction is in the standard error each estimate implies. A minimum detectable
effect at 80% power and two-sided 5% implies a standard error of MDE / (z₀.₉₇₅ + z₀.₈) =
MDE / 2.80. The power artifact (`out/H1C-POWER-REALIZADO-2026-09-10.json`, with its own
`p0 = 0.0782`) finds even `p1 = 0` undetectable, so its MDE is at least 0.0782 and the
standard error it implies is at least 0.0279 (0.0320 if total elimination is taken at
the realized control rate, 0.0896). The observed interval spans 0.0646, which under the
same normal approximation implies a standard error of 0.0165, 59% of the smaller bound.
Both are ours; they are incompatible estimates of the same standard error.~~

**Correction (rc7).** The struck paragraph compared two numbers that do not measure the
same thing. The planning power approximation and the realized bootstrap interval use
different variance constructions and assumptions: `measurement/potencia-h1c.py` uses one
variance term under the null and another under the alternative, so MDE / 2.80 does not
identify a single standard error, and the width of a percentile interval divided by 3.92
is not the bootstrap's standard deviation. Their difference does not establish a
contradiction, and it does not quantify any under-coverage of the bootstrap. The power
conclusion remains conditional on its planning inputs, and the bootstrap's coverage has
not been calibrated for this design. The bounds 0.0279 and 0.0320 and the 59% are
withdrawn as inferential claims.

We name the known limits of each:

| statement | known limit |
|---|---|
| **MDE saturated at 100%** | the `ICC = 0.0985` comes from the pre-registration and was estimated for **density per session-hour**, not for proportion per opportunity. The spec flags this itself and computes the margin: the verdict flips on an **11.5%** drop in ICC (5.6% under whole-epoch counting) |
| **95% CI of [−0.0445; +0.0125]** | a BCa cluster bootstrap on 11 and 8 clusters (the sensitivity analysis: percentile, on 11 and 9) may under-cover; the few-cluster literature [@cameron2008bootstrap; @webb2014reworking] motivates caution but does not calibrate this ratio estimator. Separately, the resampling does not re-draw the stratum-B sample (§4.1.2), so within-epoch sampling noise may be under-represented. Where either acts, it makes the interval **too narrow**, by an amount not established |

Both limits were known to us before this section existed. Our reading is that neither
statement is a calibrated measure of this study's uncertainty, and that the null in H1c
(non-rejection by the registered re-randomization test, `p = 0.434`) does not rest on the
interval; the point estimate, a 15% relative reduction (22% in the sensitivity analysis),
is not distinguishable from zero at this N. A reader should treat every interval in this
paper as indicative of sign and order of magnitude, not as calibrated coverage.

**Caveat.** This also disciplines §4.3: an interval "excluding zero" on H1 or H1a is a claim made
with the same machinery, whose coverage has not been established, which is a further reason, independent of the
denominator argument, not to read those as findings. The caveat applies to every
interval here, including the null one, and not only where it is convenient. The first
draft attached it only to H1; an adversarial reviewer pointed out that a method cannot be
optimistic selectively.

The under-powering is structural, not bad luck. The analysis spec counts partial epochs
by fractional exposure (its §3) and forbids rounding a partial epoch to a whole one (its
§7), and that counting is the power statement of this paper. Under it, and under the
planning assumptions, no reduction from `p0 = 0.0782`, including total elimination,
reaches 80% power: the effective size is 84.8 over the 19 served epochs
(`out/H1C-POWER-FRACIONARIA-2026-09-10.json`), which are the registered analysis set,
against a critical 95.26. At the 20 epochs of the sensitivity analysis, with `09-02` added
as a full ninth control epoch (10.9375 treatment, 8.23375 control), it is 91.49, and there
the verdict flips on a 4.1% drop in ICC. The statement is about reductions
only: `mde()` in `measurement/potencia-h1c.py` searches `p1` between 0 and `p0`, while the
registered test is two-sided, and an increase can reach 80% power (at the effective size
of 84.8, `p1 = 0.25` gives about 86%). The fractional counts take `09-01` as 630/672 = 0.9375
of an epoch, its share of briefs served in active mode, while the spec's clock exposure for
it is 22.38 h / 24 = 0.9325 (its §1); `09-03` enters by its brief share (441/672) and
`09-20` by clock (13.86 h / 24). Taking `09-01` by clock moves the effective size from
84.80 to 84.78 and changes no verdict. Whole-epoch counting, recomputed
with the unchanged `measurement/potencia-h1c.py`, is reported as a sensitivity. With the 19
clusters the power calculation counted (11 treatment, 8 control;
`out/H1C-POWER-REALIZADO-2026-09-10.json`) it agrees: effective size 90.2, which the script
reproduces from the artifact's own inputs. Those 19 clusters are the registered analysis
set, so under the registered analysis both countings give the same verdict. At the
sensitivity analysis's 11 treatment and 9 control the verdict flips under whole-epoch
counting: the effective size is 96.41 against 95.26, so total elimination (`p1 = 0`)
becomes detectable at 80% (relative MDE 0.996). The spec computed that case itself
(96.4) and set it aside because `09-02` served no brief, which is also why the registered
analysis excludes `09-02` (§3). The spec's statement that no defensible
inclusion criterion inverts the verdict therefore holds at the registered analysis set
under both countings, and fails only under whole-epoch counting at the sensitivity
analysis's allocation, where the design is borderline for total elimination and reaches
80% power only for reductions of about 99.6% or more. Inputs and outputs:
`_sprint-2026-10-04/REVIEW-B-rc2-evidence/power-*.json`. Reporting the interval without that sentence would be
the exact defect family this project spent eight weeks documenting; the spec makes the
declaration mandatory in the
abstract, not in a footnote, and that is where it is.

### 4.1.2 What the bootstrap does not resample

There are two layers of randomness: the assignment of epochs to arms, and the
hash-ordered sampling of 800 episodes from 5 556 in stratum B. The cluster bootstrap
resamples the first with the second frozen. The component `E[Var_sampling(B) | epochs]`
may therefore be under-represented, since the frozen sample enters only through the
between-epoch spread, in every interval that uses stratum B (H1, H1a, H1c; not M10), and it
is not negligible: a single
sampled failure in B enters as 6.945 failures, which is unbiased in expectation and
heavy in the tail. The finite-population correction is ≈0.856, not zero.

We also treat a systematic (hash-ordered) sample as if it were simple random. If the hash
order correlates with time, session or agent, the bootstrap does not correct for it.

The first pushes the intervals toward too narrow; the direction of the second is not
known. Combined with §4.1.1, the
intervals reported here may be optimistic, and the primary result is a
non-rejection (`p = 0.434`, §4.0.2) that wider intervals would not overturn.

### 4.2 H1a: excludes zero on a denominator dominated by one epoch, is not rejected, and bears no weight

**Correction (2026-10-04).** This section was titled *"H1a — inverts its conclusion on
one epoch"* and its table showed only the post-hoc leg that removes `09-14`. That broke
the rule §4.1 states for itself (the pre-committed sensitivity is reported first),
and it made the inversion look specific to one epoch when it is not. ~~Under the
pre-committed leg (§9.1 of the spec: the three partials removed, `09-14` kept), the
H1a interval already contains zero while the point estimate barely moves. What turns on
`09-14` is the magnitude; the exclusion of zero is a property of the locked leg alone.~~

**Correction (rc8).** The struck sentences describe the percentile intervals of the
analysis now reported as a sensitivity. Under the registered analysis the BCa interval
excludes zero on the locked leg and on the pre-committed leg, and contains zero only on the
post-hoc leg that removes `09-14`; the previous title, *"excludes zero only on the locked
leg"*, does not hold for it. What does hold is that the exclusion of zero rests on
`09-14`'s exposure and that the registered decision rule does not reject H1a: its
unadjusted re-randomization p-value is 0.0241, and under the Holm rule it is adjusted to
0.1205 (0.0964 without H1b), which does not reject (§4.0.2).

| | locked (the 19 epochs) | **pre-committed sensitivity** — partials `09-01`, `09-03`, `09-20` removed | post-hoc sensitivity — without `09-14` |
|---|---|---|---|
| session-hours, treatment / control | 12.56 / 4.33 | 12.16 / 3.57 | **5.43 / 4.33** |
| `H1a` (opportunities/h), registered (BCa) | −163.52 · CI [−282.29; −61.12] · **excludes zero** | −138.91 · CI [−254.18; −28.82] · **excludes zero** | −78.27 · CI [−146.22; **+1.95**] · **contains zero** |
| `H1a`, sensitivity analysis (percentile, 20 epochs) | −143.92 · CI [−209.80; −15.34] · excludes zero | −133.34 · CI [−203.62; +7.41] · contains zero | −63.04 · CI [−120.45; +1.76] · contains zero |

Sources: the registered locked leg from `out/ITT-REGISTRADO-2026-10-05.json`, its two
sensitivity legs from `_sprint-2026-10-04/B-rc8/checks-rc8.json` (block A); the
sensitivity analysis's pre-committed column from `ITT-SENSIB-PRECOMPROMETIDA.json` (field
`sensibilidade`), the same artifact that holds its pre-committed row of §4.1 (session-hours
12.16 / 4.08 there; the post-hoc leg's 5.57 / 5.16 is in `ITT-2026-09-21.json`). The registered decision rule does not reject H1a
(unadjusted `p = 0.0241`, Holm-adjusted 0.1205), and neither did the sensitivity
analysis's test (`p = 0.0855`; §4.0.2). The registered BCa lower bound of H1a is the 9th
smallest of 10 000 replicates (§4, *Uncertainty*), so it is the least stable number in the
table.

**The denominator measures idleness.** `span_por_sessao` computes `max(ts) − min(ts)` over
a session's episodes: the distance between first and last event, not time worked. A
session that acts, sleeps, and returns six hours later contributes six hours of exposure.

Measured under the registered window: the other eighteen epochs fall between 0.25 and
0.97 h (nineteen between 0.32 and 0.97 h in the sensitivity analysis); `2026-09-14` has 7.13 h,
alone 57% of all treatment exposure (56% in the sensitivity analysis). The cause isolates to one session (`d37a5964…`)
with three episodes (one at 13:52 and two at 20:12, span 6.33 h). The sessions that
actually worked in that epoch produced 74, 65 and 56 episodes in ~~**9 to 10 minutes**~~
8 to 10 minutes each *(corrected 2026-10-04: measured spans 9.71, 8.86 and 8.03 min,
recomputed with the pilot's own per-session grouping for Figure B1)*.

The artifact is not introduced by this analysis. The function is the pilot's, so
the pilot's own `hours_per_epoch` (1.1144) carries the same property. It is a feature of
the registered definition that only manifests when an epoch contains a sparse session.

**We did not change the denominator.** Replacing it with "effective work" would be
altering a locked definition *after* seeing that it yields an uncomfortable result, and
would invalidate `r̂`, the ICC and the `N` that `sizing.py` derived from them.

But that cuts both ways, and we did not say so in the first draft. If the exposure
measure counts idleness, then `r̂`, the ICC and the sample size derived from that same
measure inherit the defect. The power calculation that tells us this study is
under-powered was computed on a denominator we are now calling artifactual. We do not know
the direction: a denominator inflated by sparse sessions could have made the pilot's event
rate look lower than it is, which would have over-sized the study, or the reverse. What
we can state is that the under-powering claim of §4.1 rests on a quantity this
section undermines, and that resolving it requires recomputing the pilot, which is
future work, not a footnote. It does not rescue the trial either way: the realized N is 19
clusters regardless of what N *should* have been. The
sensitivity is reported alongside and the divergence is not adjudicated in favour of
either leg; the rule that says so was pre-committed in §2 of the analysis spec. The
line the reader must take away is ~~the sensitivity one: a conclusion that turns on one
sparse session is not a conclusion~~ ~~that both sensitivity legs contain zero (the
registered one without touching `09-14`, the post-hoc one by removing it) and that the
registered test does not reject. We draw no conclusion from an interval that excludes zero
on the locked leg only, on a denominator dominated by one sparse session.~~ that the
registered decision rule does not reject H1a, and that the only leg on which its interval
contains zero is the one that removes `09-14`. We draw no conclusion from intervals that
exclude zero on a denominator dominated by one sparse session, under a construction whose
coverage we have not established. *(Corrected in rc8: the struck sentence held for the
sensitivity analysis, where the pre-committed leg contains zero; under the registered BCa
interval it does not.)*

![Figure B1](figures/figB1-h1a-inversao-registrado.svg)

**Figure B1. H1a's intervals exclude zero on a denominator dominated by one epoch of idle
time, and the registered decision rule does not reject.** (a) Session-hours per epoch, by
designated arm, as the registered estimator computes them: for each session, the span
between its first and last event, summed per epoch (`span_por_sessao`, imported from
`pilot_replay.py`), inside the registered exposure windows, over the 19 epochs of the
analysis set (`09-02` excluded). The other eighteen epochs fall between 0.25 and 0.97 h.
`2026-09-14` (treatment, `w = 4`) has 7.13 h, which is 57% of all treatment exposure
(12.56 h over 11 epochs, against 4.33 h over 8 control epochs). Almost all of it comes
from one session with three episodes spanning 6.33 h, while the epoch's three busiest
sessions logged 74, 65 and 56 episodes within 8.0–9.7 min each. (b) The H1a difference,
treatment − control in opportunities per session-hour, with its 95% cluster-bootstrap
interval (epoch as the unit, 10 000 replicates, seed 20260921). Registered analysis (BCa):
the locked leg excludes zero, −163.52 [−282.29; −61.12]; so does the pre-committed
sensitivity, which removes the three partial epochs and keeps `09-14`, −138.91
[−254.18; −28.82]; the post-hoc sensitivity, chosen after seeing the data, which removes
`09-14`, contains zero, −78.27 [−146.22; +1.95]. The fourth row is the sensitivity
analysis's locked leg (percentile, 20 epochs, no window cut), −143.92 [−209.80; −15.34].
Filled marker: the interval excludes zero; hollow marker: it contains zero. These
intervals may under-cover; their coverage has not been established for this design
(§4.1.1, §4.1.2). The registered re-randomization test, a different
estimand (§4.0.2), gives an unadjusted `p = 0.0241`; H1a is decided in the Holm family,
where it is adjusted to 0.1205 (0.0964 without H1b), and it is not rejected. Sources:
panel (a) from `episodios-ensaio-20260921.jsonl`, `p2-serving.ndjson` (the windows) and
`ASSIGNMENT-SERVING.json`; the script aborts unless the per-arm sums reproduce
`horas_sessao` of the registered leg in `out/ITT-REGISTRADO-2026-10-05.json` and every
epoch reproduces `_sprint-2026-10-04/B-rc8/checks-rc8.json`. Panel (b) from those two
files; the script aborts unless `checks-rc8.json` was produced from the same
`ITT-REGISTRADO` file (sha256) and agrees with it on the registered leg. Generated by
`measurement/sprint-figB-h1a-inversao-registrado.py` (rc8). The figure of earlier versions,
`figures/figB1-h1a-inversao.svg` from `measurement/sprint-figB-h1a-inversao.py`, plots the
sensitivity analysis and is kept unchanged as its record; its embedded headline
(*"H1a turns on one epoch: the exposure denominator counts idle time"*) was never regenerated.

### 4.3 H1: an interval excluding zero that is not a finding

`H1` returns −14.12, BCa CI [−22.15; −7.04], excluding zero on ~~both legs~~ all three
legs (pre-committed sensitivity −13.93, CI [−22.98; −5.70]; post-hoc sensitivity without
`09-14` −9.03, CI [−14.68; −1.89]), and the registered test rejects (`p = 0.0133`). The
sensitivity analysis agrees on every leg: −14.62 [−20.51; −4.79], −15.59 [−22.43; −4.05]
and −9.74 [−16.21; −2.99], `p = 0.0127`. *(2026-10-04: the pre-committed leg, from
`ITT-SENSIB-PRECOMPROMETIDA.json`, was missing here for the same reason as in §4.2; adding
it changes no conclusion of this section.)*

**Caveat.** This is not presented as a result, and the reason is structural, not rhetorical.

**`H1` is the product of the other two, so it is not an independent hypothesis:**

```
H1  =  repeats / hours  =  (repeats / opportunities) × (opportunities / hours)  =  H1c × H1a
```

Verified on the estimates, relative error ≤ 5.8×10⁻⁶ in all six arm-by-leg cells (five
distinct: `09-14` is a treatment epoch, so control is identical on the locked and post-hoc
legs); the residue is the JSON rounding to six places, not a discrepancy. On the six cells
of the registered analysis the relative error is at most 6.0×10⁻⁶
(`_sprint-2026-10-04/B-rc8/checks-rc8.json`, block A). This is an algebraic
identity, so `H1` carries no information that `H1a` and `H1c` do not already carry.

The split also falls exactly along the denominator. `H1` and `H1a` both divide by
session-hours; `H1c` does not: it is a ratio of two counts. The two quantities that
exclude zero are the two that divide by the measure §4.2 shows to be
idleness, and the one quantity free of that denominator is the null one. This follows
from the arithmetic above, not from a coincidence we assert away.

**What this argument does NOT do, stated because an adversarial reviewer caught us
short here.** It does not explain why `H1` still excludes zero *without* `09-14`. Removing
that epoch nearly equalizes hours per epoch across arms (0.543 treatment against 0.541
control; 0.557 against 0.573 in the sensitivity analysis) and `H1` remains at −9.03
(−9.74). So the sparse session does not explain the residual
gap; in the arithmetic, volume does: the control arm carries 137.7 opportunities and 10.96
repeats per epoch against 95.5 and 6.08 in treatment (132.3 and 11.85 against 93.4 and 6.08
in the sensitivity analysis).

Two readings survive that, and this design does not separate them:

1. the treatment reduces the volume of failure activity without moving the rate at
   which opportunities become repeated failures (which is what `H1c` measures, and `H1c`
   is null);
2. the arms differ in baseline volume by chance: with 19 clusters and between-epoch
   volume spanning 73 to 234 episodes, that is entirely available.

We cannot adjudicate between them, and we will not pick the flattering one. What we will
say is narrower and survives both: `H1` was removed from primary on 2026-08-30, in a
revision that was not deposited (§1), for requiring a 955% effect (`DESIGN-REVISION-2026-08-30.md` l.196, *"impossible by
construction"*). The 955% is the planning figure: the registered 30% MDE divided by the
pre-trial calibration share of altered briefs, 3.14% (11 of 350 briefs at `w = 2`). The
observed reduction is 69.8% on the locked leg
(6.117 against 20.236) and 44.6% without `09-14` (70.7% and 47.1% in the sensitivity
analysis). Dividing these reductions by the calibration
share gives 22.2 and 14.2 times total elimination (22.5 and 15.0); by the share realized in the trial,
4.56% (335 of the 7 350 briefs served in active mode in treatment epochs; §4.0.1b), it gives
15.3 and 9.8 times (15.5 and 10.3); at the highest per-epoch share in the positive control, 6.85%, it
gives 10.2 and 6.5 times (10.3 and 6.9). These
are proportional-dilution calculations, not causal bounds: the share of briefs altered need
not equal the share of baseline repeated failures those briefs carry, and an effect can
travel through activity volume (reading 1 above) or through state (§8.3). They make the
magnitude hard to attribute to the altered briefs, not impossible, and `H1` therefore
remains an unexplained rejection. And with 8
and 11 epochs the cluster bootstrap has few degrees of freedom and may return optimistic
intervals.

We also owe a note on our own criterion. §4.2 discards `H1a` because its interval
excludes zero only while `09-14` is in, on a denominator dominated by one sparse session,
and because the registered decision rule does not reject it. `H1` does *not* turn on that session and is discarded anyway, on different
grounds. Applying one standard where it bites and another where it does not would let the
result choose the ruler. The grounds above are stated separately so a reader can reject
either without the other.

### 4.4 H1b: trivially 1.0, because two of our own locks collide

| lock | date | text |
|---|---|---|
| `Opportunity` (§3) | **2026-07-29** | *"An **executed action** `a` … for which the serving snapshot at session start contained ≥ 1 failure episode `a_past` with `sig(a_past) = sig(a)`"* |
| `H1b` (§1) | **2026-08-16** | *"An opportunity yields a repeat attempt if the **session** emits at least one action whose signature equals that of `a_past`"* |

These are different estimands. Under the July lock the opportunity is the action, and
the action carries `sig(a_past)` by definition ⇒ H1b = 1.0 by construction, and the
nesting that, per the pre-registration, makes the joint reporting work ceases to exist. For H1b to have content,
`Opportunity` would have to be a property of the *session*, which changes the denominator
for the whole family, not just for H1b.

No later document resolves it: the analysis spec does not mention H1b once.

**Correction of our own phrasing (2026-09-21, adversarial review).** We first wrote
that H1b is *"unevaluable"*. That conflates two things. Under the lock we kept, H1b is
evaluable and equals 1.0: it is *trivial*, not unmeasurable, and no artifact
computes it because none is needed. What is unanswerable is the question H1b was
written to carry. Saying "unevaluable" made a definitional triviality sound like missing
data, which is the more flattering of the two readings and the wrong one.

**We kept the July lock** (`Opportunity` is the action) because PREREG §420 records that
`r̂`, `p̂0` and the ICC were all computed by replay under that model, and that the
construction then locked was the one that *"keeps every locked number valid — the
alternative constructions would have invalidated them"*. Adopting the session reading now
would invalidate those three numbers and, by dependency, the `N_epochs` derived from them.

**What is lost.** H1b was the member of the family distinguishing *"the
treatment makes the agent stop trying"* from *"makes it try and succeed"*; §1 of the
pre-registration calls it *"the substantive one for this paper."* That distinction is
not reportable from this study. The loss is of mechanism, not of power: H1c was already
declared under-powered at the realized N (§4.1.1), so nothing here worsens what was
known about detectability.

The reason that goes in the record is a collision between two locks, unreconciled before
the window closed, not "we did not measure it", and not "it came out non-significant".

### 4.5 Coverage by arm, and a pre-committed explanation it does not test

Coverage is post-randomization, so per PREREG §5 the ITT over all post-washout epochs
without coverage exclusion is the primary and is what §4.1–4.3 report. Coverage is
reported descriptively:

| | treatment | control |
|---|---:|---:|
| briefs with ≥1 designated item | **28.0%** (2 068 / 7 392) | **26.9%** (1 385 / 5 145) |

The treatment column counts all briefs of the treatment epochs, including the 42 that
`09-01` served in shadow mode before the dose went active; over the 7 350 briefs served in
active mode it is 2 057 / 7 350, still 28.0%.

Across 4 324 designated-serving occurrences, all 19 signatures were served, each at
≈5.3%: uniform.

~~This contradicts the projection the pre-commitment rests on.~~
`DESIGN-REVISION-2026-08-30.md` committed in advance that a null in H1c *"does not
distinguish 'the mechanism does not work' from 'the lessons it promotes are too generic'"*,
on the grounds that 93.8% of coverage would concentrate in the bucket signature
`Bash|shell:outro`. ~~The realized distribution is flat. The pre-committed alternative
explanation is therefore weakened by the data, which is the opposite of what a
pre-commitment usually does for the party that wrote it, and is why it is reported here
rather than dropped.~~ **Correction (rc7).** The two numbers count different things. The
93.8% is 573 of the 611 covered action opportunities of the planning corpus, grouped by
signature (`out/CONCENTRATION-2026-08-30.json`). The ≈5.3% counts designated-chunk serving
occurrences: `cobertura_e_m10.py` adds one per designated item in a served brief, without
linking it to an action opportunity. Designated-chunk serving occurrences were
approximately uniform across the 19 items. That differs from the planning statistic, which
counted covered action opportunities by signature; the present measurement therefore does
not test that concentration projection, and it does not weaken the generic-lessons
explanation. The pre-committed indistinction stands: the null in H1c does not distinguish
a mechanism that does not work from lessons too generic to work.

**Caveat.** We record a near-miss: `boost_by_id` is not a coverage measure. It records
boost *calculated* for every candidate, uniformly, and reading it as coverage would have
produced a fabricated 139 650. Coverage comes from crossing the served id lists against
the designation.

### 4.6 M10: arm × coverage correlation, reported unconditionally

The registered TOST at `|r| ≤ 0.15` requires K ≥ 30 analyzed epochs; we have 19. §8 of
the analysis spec declares it **"not evaluable at the realized K"**, which is *not* the
same as "equivalence not established". The correlation and its interval are reported
unconditionally:

| leg | K | r | 95% CI (epoch bootstrap) | |
|---|---:|---:|---|---|
| primary — all | 19 | **+0.1130** | [−0.4773; +0.5088] | contains zero |
| without `09-20` (the 13.86 h partial) | 18 | **−0.1871** | [−0.5704; +0.3353] | contains zero |
| without `09-03` and `09-20` | 17 | −0.1114 | [−0.5114; +0.4518] | contains zero |
| without `09-14` | 18 | +0.0837 | [−0.5180; +0.4932] | contains zero |

The 17-epoch leg keeps `09-01`, the third partial. The pre-committed sensitivity, which
removes all three partials as a block (§9.1 of the spec), was not computed for M10.

**The sign flips.** `09-20` is a control epoch with 14.6% coverage against ≈28%
everywhere else, low because the coverage denominator counts all 672 briefs of the epoch,
of which 287 were served after the designation expired and could not contain it (98 of the
385 before expiry, 25.5%): an artifact of the clock, not of the arm. That one epoch moves `r` from −0.19 to +0.11. All four legs contain zero with
half-widths near 0.5: at K = 19 this correlation distinguishes nothing, and reporting only
the primary leg would have sold a sign that belongs to a truncated epoch. Correlation with
the dose rather than the binary arm: −0.0521.

### 4.7 The single epoch at the top dose: chance, not truncation

Only one of the 20 designated epochs drew `w = 7.5`, against 3.33 expected. The
explanation that writes itself, *stopping at 20 of 234 biases against the top dose*, is
mechanistic and plausible, and the measurement does not support it.

Measured over 2 000 seeds conditioned on the same realized dates, using the
published assignment script:

| leg | value | share of the −2.333 deficit |
|---|---:|---:|
| expected under the design (20 × 39/234) | 3.333 | — |
| **truncation** — conditioning on the realized dates | **+0.023** | ~~**1.0%**~~ **−1.0%** |
| **chance** — from the conditional mean to the realized | **−2.357** | **101.0%** |

*(Corrected 2026-10-04: the truncation share was printed unsigned, so the two shares summed
to 102%. With signs (+0.0232 and −2.3565 against a deficit of −2.3333 in
`ITEM7-DOSE-TOPO-2026-09-21.json`), they are −1.0% and +101.0%, which sum to 100%.)*

Conditional mean 3.357, mode 3 (25.3%), `P(n = 1) = 10.15%`, `P(n ≤ 1) = 11.95%`. The
conditional mean for `control` is 9.991 against 9 realized, so truncation does not displace
that either.

**Two traceability notes (2026-10-04).** (1) The `control` figure 9.991 is held by no
artifact (it appears only in `DEVIATIONS-FOR-PAPER.md`) because
`ITEM7-DOSE-TOPO-2026-09-21.json` stores only the `w = 7.5` distribution. An independent
redraw of 20 000 designs with `assign_arms.assign` and a declared seed recipe
(`_sprint-2026-10-04/figures/figB2-item7-crosscheck-20000.json`) gives 10.0124 ± 0.0146 for `control`,
consistent with 9.991 within the Monte-Carlo error of a 2 000-seed run; it corroborates the
number but does not make it traceable. (2) The seed recipe of the 2 000-seed run is not
recorded in its artifact, unlike the re-randomization's `seed_prefix`; three guessed
recipes did not reproduce its histogram, so the 20 000-seed run is a second measurement,
not a reproduction. It gives `P(n = 1) = 9.11% ± 0.20%` against 10.15% here, whose own
Monte-Carlo s.e. at 2 000 seeds is about 0.7 pp: consistent, and a reminder that the
10.15% carries that much noise.

![Figure B2](figures/figB2-sementes-dose-topo.svg)

**Figure B2. One epoch at the top dose is a tail draw, not a truncation effect.**
Distribution of `n`, the number of the 20 realized epochs assigned `w = 7.5`, over 2 000
designs re-drawn with the published `assign_arms.py` and conditioned on the same dates. The
realized `n = 1` (highlighted) has probability 10.15%, and `P(n ≤ 1) = 11.95%`. The mode is
3 (25.3%). The dashed line is the design expectation 20 × 39/234 = 3.333; the dotted line
is the conditional mean, 3.357. The two lines are 0.023 apart, which is 0.7 Monte-Carlo
standard errors (s.e. 0.035 over 2 000 seeds, computed from the histogram). Conditioning on
the realized dates therefore moves the expectation by an amount whose sign this run does
not resolve. The whole deficit of −2.333 is chance; the truncation shift is not
distinguishable from zero (1% of the deficit, MC s.e. 1.5%). With `n = 1` at the top dose, there is no dose-response to read (analysis
spec §7). Source: `ITEM7-DOSE-TOPO-2026-09-21.json`. The script aborts unless the
histogram reproduces the artifact's summary fields, the design counts (39 of 234) come
from `assign_arms.py`, and the realized count matches `ASSIGNMENT-SERVING.json`. Generated
by `measurement/sprint-figB-sementes-dose-topo.py`.

**Why truncation does not measurably bias here:** stratification is
`(calendar half) × (weekday | weekend)`, and the first 20 days fall entirely inside `h1`,
where the allocation is already balanced by construction. Conditioning moves the
expectation by +0.023 ~~— and in the direction *opposite* to the intuition~~, which is
0.7 Monte-Carlo standard errors from zero (s.e. 0.035 over 2 000 seeds); its sign is not
resolved, and the independent 20 000-seed redraw gives −0.007 ± 0.011. Truncation
accounts for about 1% of the deficit in magnitude, in either direction. *(Corrected
2026-10-04: the first version read a direction into a difference inside the Monte-Carlo
noise.)* This agrees with
the spec's earlier measurement (23/300 = 7.67%, mode 3-4; the 95% interval of that
proportion is [4.7%; 10.7%] and contains 10.15%); what is new is the separation of the
two causes, which the spec asserted without measuring.

The consequence for the paper is negative and is stated as such: with `n = 1` at the top,
there is no dose-response to read, and §7 of the analysis spec forbids reading one.

---

## 5. What is not evaluable, and why: declared, not omitted

| registered rule | why not reportable | what stands in its place |
|---|---|---|
| **H1b** | evaluable and = 1.0 by construction, because the 2026-07-29 and 2026-08-16 locks collide; the mechanism question it carried is unanswerable (§4.4) | nothing; the mechanism question is not answered |
| **TOST arm×coverage** at `\|r\| ≤ 0.15` | requires K ≥ 30; K = 19 | correlation + CI, unconditional (§4.6) |
| **dose-response reading rule** (PREREG designation block; ~~H3~~) | `n = 1` at the top dose (§4.7) | ~~per-dose effect with `n` on the same line, no gradient~~ not computed in this version |
| **H2**: task regret, secondary confirmatory (two components, time and tokens, in the Holm family) | reportable, and reported from rc8 on: computed from the locked action archive with the locked instrument; three choices the registration does not fix are declared below | the result below: neither component rejects |
| **H3**: retrieval metrics (nDCG@10, recall@10), exploratory | not computable: nDCG@10 and recall@10 need graded relevance judgments per (query, item), and none were defined or collected for the served briefs, which are push context and answer no query; building a relevance label now would be a new estimator defined after unblinding | nothing |
| **secondary model and co-estimates of PREREG §5** (the NB/binomial mixed model, the lag-1 and A→B co-estimates, the Appendix-B bounds) | not computed; they were outside the four departures the registered re-analysis resolved | nothing in this version |
| **leave-one-agent-out** | 6 agents over 19 epochs | ~~exploratory, no inference~~ not computed in this version |
| **first-half / second-half contrast** | window truncated inside the first half | not reported |

These are listed before the discussion. ~~And, except H1b (found after the close, §4.4),
were listed in §8 of the analysis spec before the window closed, so that their absence
cannot be read as omission.~~ Four of them (the TOST, the dose-response rule,
leave-one-agent-out and the half contrast) were listed in §8 of the analysis spec before
the window closed, where the dose-response rule is labelled *H3*, which is not the
registration's H3. H1b was found after the close (§4.4). H2 and H3 were listed nowhere
before rc7: no version of this manuscript, of the analysis spec or of the deviation log
mentions them, which is the omission this table exists to prevent, and we found it only
because an adversarial reviewer did. The secondary model and co-estimates were not listed
either, until rc8. Had a rule
become unevaluable and simply been dropped, a reader could not tell it from a rule that
was never there.

**H2, computed (rc8).** No regret pipeline had been run on trial data: `task_regret.py`
was run once, in August, on the pilot corpus, to lock the winsorization points (p95: 7.45 s
and 65 206 tokens, PREREG §4.2, locked 2026-08-15). The locked action archive pairs
5 951 of 5 951 `tool_use` / `tool_result` events onto the locked corpus by episode, with no
orphan in either direction and no signature divergence; 37 signatures have a regret floor
(at least five successful episodes) and 5 875 episodes carry regret. The registration does
not fix three choices, which we declare, made without looking at the arms:

1. the "best known resolution" is the minimum over successful (`not is_error`) episodes of
   the same signature, with at least five of them, over the whole locked corpus (5 951
   episodes, 2026-08-23 to 2026-09-21), both arms pooled;
2. the population is every post-washout action in the analysis epochs, not only the
   opportunities;
3. the effect is the difference of per-arm means pooled over episodes, with the same epoch
   bootstrap and BCa interval as H1; the sharp-null statistic is the per-epoch raw mean,
   trend-residualized like every permutation outcome of PREREG §5.

The winsorization applies to the estimator only; the test uses raw values, as locked.

| component | treatment / control mean (winsorized) | difference, winsorized (95% BCa) | difference, raw (95% BCa) | re-randomization *p* (raw) |
|---|---:|---:|---:|---:|
| time (s) | 1.770 / 1.486 | +0.284 [−0.030; +0.666] | −1.13 [−5.35; +0.85] | 0.831 |
| tokens | 12 861 / 10 721 | +2 141 [−1 380; +6 230] | +2 420 [−2 404; +7 760] | 0.684 |

Neither component rejects, alone or in the Holm family (adjusted 1.0); in the sensitivity
analysis the raw p-values are 0.892 and 0.950. On time the winsorized and raw estimates
have opposite signs (+0.28 s, treatment slower; −1.13 s): the raw tail is heavier in
control. Source: `out/ITT-REGISTRADO-2026-10-05.json`, field `H2`; the analysis covers 1 172
treatment and 1 115 control episodes in the 19 epochs.

---

## 6. Instrument defects that changed a reported number

Consistent with Paper A's §6, defects that changed a number we had published are part of
the contribution rather than an appendix.

1. **Ruler substitution (`09-20`)**: delivery volume where the spec locks clock exposure;
   16+3+1 published as 17+2+1, propagated to six places including a pushed commit (§3.1).
2. **Post-randomization conditioning on the arm**: mode of observed dose instead of
   designation; 0 divergences, but the premise was wrong (§3.1).
3. **"Zero inversions" is a tautology**: adding a vote to an odd panel under strict
   majority can only hold or tie, so zero reversals to the opposite strict majority is
   structurally guaranteed and a coin would achieve it. ~~Ties do change the final label
   under the tie rule; those are the 28 losses of item 6.~~ The 28 ties are the losses of
   item 6, and only 3 of them change the final label under the tie rule (failure to
   `not_failure`); the other 25 were already `not_failure` under the three-family majority
   *(corrected in rc4; `out/C12-EMPATES-POR-BRACO-2026-10-05.json`)*. The metric with content is agreement with the three-family majority:
   **1 111 / 1 145 = 97.0%**.
4. **A rate generalized from one batch**: *"100% of abstentions are `xai`"* was true in
   the first 100 episodes and false over 1 195 (`xai` 26 + 6 quota + 1 missing · `zhipu`
   13 · `google` 11), and was never re-measured before being asserted.
5. **Claiming the data confirm a locked parameter**: τ is locked since July over five
   families; "confirming" it with outcome-period data is post-hoc. We also called marginal
   rates "agreement", and cited the S1/S2 boundary that τ absorbs while omitting S0/S1,
   which it does not and where the 11.9 pp marginal gap lives.
6. **A rationalized sign**: we explained a +7/−8 swing by claiming a retry had recovered
   what a fourth panelist rescued; the sets are disjoint, and the sign comes from the
   28 losses, not the gains. Recomputed under the published rule: gains 20 (episodes the
   fourth family brings to three substantive verdicts), losses 28 (episodes it brings to an
   exact tie), balance −8.
7. **A panel composed after counting ties in the trial's own verdicts**: post-hoc by §9
   of the spec, recorded as such. What stands: the fourth family enters only as a
   substitute where fewer than three substantive verdicts exist (the role PREREG §695
   assigns it), never as a fourth vote, so it generates no ties; the four-vote set is
   published as declared sensitivity. That is the rule as stated, and the registered
   analysis implements it: the 36 episodes with fewer than three substantive verdicts from
   the three families receive the fourth family's verdict, 20 of them reach the floor (13 as
   failures), and 16 stay `unknown` (§4). The analysis of earlier versions, now the
   sensitivity analysis, did not implement it: its verdict file holds only the three
   families, so those 36 stayed `unknown`.

Defects 1–7 were found by two mechanisms that catch disjoint classes: adversarial
review by independent model families, and mechanical census. Six of the seven above came
from the former on a body of work the latter had already passed.

---

## 7. Threats to validity

**Power.** Addressed throughout and not mitigated: the registration outlived its
intervention (§3.0.1), the study is under-powered as a consequence, and no analysis choice
repairs that. Under the spec's fractional counting no reduction, including total
elimination, reaches 80% power, and at the registered analysis set the same holds under
whole-epoch counting; under whole-epoch counting at the sensitivity analysis's allocation it
is borderline (§4.1.1). The feasibility stop that §3-bis of the prospective estimand
declared for Epoch 1 was met and not executed (§3.0).

**One-system, one-fleet.** Everything is measured on a single production system. Nothing
here establishes that the effect, or its absence, generalizes.

**Tie rule.** The exact-tie rule resolves to `not_failure` by
design. It cannot bind in the three-family panel, where three substantive verdicts are required
and three cannot tie, nor in the registered substitution panel, where an adjudicated
episode has exactly three (§4), but it binds in the four-vote sensitivity set. There it biases
toward fewer failures; its effect on the treatment-control contrast depends on the arms the
ties fall in, ~~which we have not counted, and a reader is entitled to weigh that~~ and
counted in rc4: of the 28 ties, 10 fall in treatment epochs, 11 in control and 7 outside the
window (10, 10, 7, and one control tie before `09-03`'s exposure window under the
registered window; rc8). ~~it is nil for H1c~~ It changes no H1c label relative to the three-family majority
(none of the 11 tied H1c opportunities was a failure there), but against the opposite
resolution it holds 4 treatment and 7 control opportunities (HT weights 27.78 and 36.73) at
`not_failure`; resolving the ties as `failure` instead moves the four-vote H1c point
difference from −0.0121 to −0.0211 under the registered window and epoch set, and from
−0.0208 to −0.0266 under the sensitivity analysis's, toward a larger reduction under
treatment (§4; `out/C12-EMPATES-REGISTRADO-2026-10-05.json` and
`out/C12-EMPATES-COMO-FAILURE-2026-10-05.json`, point only).

**Post-randomization denominator.** H1c divides by opportunities, which are executed
actions and can themselves change under treatment (opportunities per epoch 103.5
treatment, 137.7 control; 100.3 and 132.3 in the sensitivity analysis). Its contrast is a policy-level ratio over realized
opportunities, not a per-opportunity propensity for a fixed population.<!-- SHAM-JANELA: pending -->

**Scope of the specificity control.** The sham replay (§4.0.1c) covers the 2,646 brief
states of the four `w = 4` epochs, not the whole window; its shams are drawn from the 36
non-designated items that can receive a bonus and matched on severity and bonus mass, not
on signature group; and its `p = 1/21` is the floor at `K = 20`, a rank against these
20 shams rather than a calibrated randomization p-value. It establishes that the real
designation outranked the 20 tested shams on what was served; it does not establish
specificity against every matched designation, nor an effect on outcomes.<!-- /SHAM-JANELA -->

**Denominator.** §4.2. The exposure measure counts idleness, and one epoch dominates.

**Our own bookkeeping.** §1.1. The claim that the H1b estimand decision preceded the
estimates, and that the primary switch preceded the assignment seed, rests on our own
timestamps (written times, commit times and a file time); the §10.33 decision followed a
preliminary estimate (§1.1).

**A stopping rule that was met and not executed.** §3.0. Every estimate of §4 comes from a
trial that a rule declared before the seed would have stopped after Epoch 1 for design
impossibility. The estimates are not biased by that, since the stop was never applied, but
a reader who holds us to the prospective estimand should read the whole of §4 as produced
after a declared stop.

**An assignment rule replaced after the seed.** §1. The arms served are those of the
registered script, fixed before the round; the rule the seed declaration named would have
given different arms to 11 of the 20 realized epochs, and the replacement was made after
the round was emitted.

---

## 8. Related work

Four bodies of work bear on this trial, each read for what it gives us and for what this
trial does not do that its authors do. In short: the agent-memory literature has
benchmarks, cost characterisations and (dated 1 October 2026) one randomised design, but
no pre-registered randomised trial on live traffic that we could find; the methods this
trial needs come from online experimentation, which has no memory-specific content; and
pre-registration is argued for in ML and IR but rarely practised. Paper A's §8 covers the
exposure and surface literature and is not repeated here.

### 8.1 Agent-memory evaluation, and what the surveys ask for

**Benchmarks compare systems on fixed tasks.** MemoryArena [@he2026memoryarena],
Evo-Memory [@wei2025evomemory], LifelongAgentBench [@zheng2025lifelongagentbench],
MemoryAgentBench [@hu2025memoryagentbench], LoCoMo [@maharana2024locomo], LongMemEval
[@wu2025longmemeval] and InterruptBench [@zou2026interruptbench] stress different
competencies but share one structure: a curated task suite, run once per system, systems
compared to each other. Their contrast is between *systems on fixed tasks*; ours is between
*two policies of one system on traffic we did not choose*. Evo-Memory both fixes task order
as a fairness device and measures that order matters: ExpRAG's average success is 0.57
under Easy→Hard and 0.69 under Hard→Easy (its Table 2), over two *sorted* orders, not
sampled ones.

**What the canonical survey asks for.** The TMLR survey [@huang2026survey] closes its
evaluation discussion (§9.6) by asking for "closed-loop, longitudinal, and
execution-grounded evaluation paradigms", in environments "where experience accumulation has
real consequences", "enabling comparison between memory-augmented agents and memory-free
baselines under identical conditions", with replayable state and provenance. This trial is
a neighbour of that direction, not an instance of it: §9.6 contrasts memory against
*no* memory; we contrast two policies of an always-on memory. We share the paradigm: a
live system, a closed loop, per-brief provenance (`ids_tratado` / `ids_controle`) and a
replayable serving state. §4.0.1c shows what "replayable" costs: the replay reproduces
production only on the corpus that actually served and with an exact serve-state cut. On
the version pinned in Paper A (sha256 `497e9549…`, 4 Aug 2026) we count zero occurrences of
`random*` and of `pre-regist*`; the single `A/B` appears as a cost that user simulators
spare ("reducing costs associated with live user studies and online A/B testing"). We read
that as the absence of a convention, not a claim that no one has run such experiments.
Three other surveys [@zhang2024memorysurvey; @hu2025memoryage; @du2026memoryautonomous]
return zero for `randomi[sz]ed`, `A/B` and `pre-?regist` (lower bounds: hyphenation not
stitched).

**Telemetry is the other axis.** Omri et al. [@omri2026agentmemory] attribute tokens,
latency, utilisation and energy to memory construction, retrieval and generation across ten
systems, with no randomised contrast. We measure whether a lever changed what agents
*did*, and report no cost, latency or energy; a trial carrying their per-phase
attribution would answer whether a lever that changes a brief a few percent of the time
pays for itself.

### 8.2 Interventional studies of memory

A thin literature *intervenes* on memory. Three questions separate it from this trial:
randomised exposure, advance registration, live traffic.

| Work | What is varied | Setting | Randomised exposure | Pre-registered | Live traffic |
|---|---|---|---|---|---|
| Xiong et al. [@xiong2025memorymanagement] | memory addition / deletion; record quality | four agents, controlled experiments | not determined | not determined | no |
| Feng et al. [@feng2026memorytransplants] | memory architecture × content, 2×2 factorial | LiveCodeBench → MATH, 3 seeds, 360+ runs | not determined | "six pre-registered validation gates" | no |
| Sun et al. [@sun2026experienceserving] | none / random / global / retrieved experience in prompts | production moderation workload; results on an offline benchmark | random-*content* control, not randomised units | not stated | in production; results offline |
| Tablan et al. [@tablan2026learningonthejob] | no-memory vs. feedback-learned stores vs. static RAG | τ-bench banking, simulated | not determined | not stated | no |
| Srivastava [@srivastava2026cmi] | no / with / perturbed memory, per candidate | Causal-LoCoMo (87 examples) | not described in what was read | not stated | no |
| **Behnam & Wang** [@behnam2026cmp] | which memories fill *k* reserved context slots | LongMemEval, LoCoMo, multi-hop QA; Mem0 replay | **yes**, known propensities | not stated | no |
| **This trial** | promotion dose *w* on 19 designated items | production fleet, 24 h epochs | **yes**, public-beacon seed | **yes** (OSF `yf7d2`); primary switched before any data, in an undeposited revision (§1); a declared feasibility stop met and not executed, and the seed declaration's assignment rule replaced after the round (§1, §3.0) | **yes** |

"Not determined" means *we did not read far enough to say*; "not stated" means *not found
in what was read*.

**Causal Memory Policy.** Behnam and Wang [@behnam2026cmp] (arXiv, 1 Oct 2026, not
peer-reviewed) show that, for a fixed query and context in which a memory has zero
probability of being retrieved, randomizing its presence in the store cannot identify its
utility conditional on retrieval: it is "not identified by any design that holds
M−m fixed while randomizing only whether m is included" (their Theorem 1; a
*retrieval-level positivity violation*). They restore identification by randomising
which memories occupy *k* reserved context slots, with design-fixed propensities and a
self-normalised inverse-propensity estimator. Identification fails for 54% of required
memories on LongMemEval and 67% on LoCoMo, and the failure persists in Mem0 replayed over
benchmark histories.

Three points of contact. First, an instance of their failure is in our data. The 19
designated items leave eligibility together at 2026-09-20 22:51:23, after which no dose
reaches them, because the boost is addressed by id and they are no longer candidates;
treatment and control become the same intervention for 214 of 234 registered epochs
(§3.0.1). CMP is the formal name and the first treatment of that failure we have found. We
did not have the framing at registration (2026-08-18) and claim no priority. Whether the 20
*realised* epochs also contain a partial failure is a question for Paper A's exposure
measurements and §4 of this paper; this section does not assert it. Second, the
estimands differ. CMP identifies an individual memory's utility per interaction; we
estimate an intention-to-treat effect of one lever with the fleet-wide epoch as unit, do
not randomise within a brief, and have no propensity-weighted estimator. Third, the
evidence differs in kind. Theirs is benchmark and replay evidence with a measured
per-query cost; ours is live, pre-registered, with an interval whose coverage we have not
established (§4.1.1). CMP-style slot randomisation *on* a live fleet *under* a
registration is, as far as we found, empty; it is what a successor trial would need.

Randomised evaluations of deployed AI tools exist [@peng2023copilot; @becker2025metr;
@bean2026llmmedical], but randomise *people or tasks*, which presumes no interference
between units. A memory store shared by a fleet violates that presumption.

### 8.3 Online controlled experiments

**Randomise, then check the randomisation.** The online-experimentation literature
[@kohavi2020trustworthy; @kohavi2009controlled] is the standard reference for randomised
experiments on live systems (cited for that role, not for a specific prescription);
Fabijan et al. [@fabijan2019srm] describe sample ratio mismatch as an indicator of
data-quality problems. Our analogues are the registered assignment
script with its committed hash and the positive (11/11) and dual negative (8/8) controls of
§4.0.1b. <!-- SHAM-JANELA: pending -->The sham replay, the placebo-like specificity control, ~~was **not executed**: the
configuration launched was invalid, and a valid one awaits data that exist only on the
production host~~ was invalid as first launched and was run in a corrected configuration
on 2026-10-04: the real designation ranks above all 20 shams on the `w = 4` epochs
(§4.0.1c).<!-- /SHAM-JANELA --> We used no covariate variance reduction [@deng2013cuped] and did
not interleave [@radlinski2008clickthrough; @chapelle2012interleaved; @hofmann2016online],
for which Hofmann et al. report one to two orders of magnitude more sensitivity than
absolute metrics; we have no per-item credit signal to interleave on.

**Why the unit is the epoch.** When units share state, per-unit randomisation is biased;
this is the problem around which marketplace [@blake2014marketplace; @johari2022twosided] and
network [@saveski2017network; @aronow2017interference] experimentation are built. The
switchback remedy randomises the whole system over time
[@bojinov2023switchback; @hu2022switchback; @basse2023minimax] and comes with
randomisation-based inference [@bojinov2019timeseries]. Ours is a fleet-level switchback
with 24 h epochs and a two-hour washout. Unlike that literature, we fixed the washout ex
ante instead of estimating the carryover order; we have 19 periods in the analysis (20
realized); and a memory store
accumulates, so carryover through *state* may outlast any fixed washout. We claim the
relation, not that these theorems apply to our state process.

**Few clusters.** ~~Our percentile cluster bootstrap runs on 9–11 clusters per arm, the
regime in which ordinary cluster bootstraps over-reject [@cameron2008bootstrap], perform
"poorly with fewer than eleven clusters" [@webb2014reworking], and for which a six-point
wild bootstrap is recommended [@cameron2015practitioner].~~ The analysis has 19 clusters,
split 11/8 (20, split 11/9, in the sensitivity analysis). The few-cluster literature motivates caution: ordinary cluster bootstraps can
over-reject with few clusters [@cameron2008bootstrap], and Webb's six-point wild bootstrap
is proposed for small total cluster counts [@webb2014reworking; @cameron2015practitioner].
That literature concerns cluster bootstraps for regression inference; it does not
directly calibrate this BCa (or percentile) ratio estimator or establish the direction of its
coverage error. We used none of these. The
registered re-randomisation test (§4.0.2) is the finite-sample alternative (a Fisher
randomisation test [@imbens2015causal; @bojinov2019timeseries]) and the inference to
weight where the two disagree, as on H1a.

**Under-power and counterfactual logging.** Across twenty-five large field experiments,
"the median confidence interval on return on investment is over 100 percentage points
wide" [@lewis2015unfavorable]. Ours is a *weaker* case: they were under-powered by the
economics of the outcome, we by a registration whose sample size ignored a 30-day
eligibility window (§3.0.1). Observational comparison is not the remedy: observational methods often fail to recover the
effects measured in the same advertising experiments [@gordon2019comparison]. Our replay analyses belong to the family of Li et al.
[@li2011unbiased], and the closest analogue of our sham is ghost-ads logging of the
exposures the treatment *would* have produced [@johnson2017ghost]: in both, the
counterfactual is only as good as the state it is computed from, which is exactly where
our first sham configuration failed, and what the corrected one had to reproduce before
its result could be read (§4.0.1c).

### 8.4 Pre-registration, and what a null is worth

Pre-registration in ML and NLP has been piloted, not adopted: the NeurIPS 2020 and 2021
workshops [@bertinetto2020prereg; @albanie2022prereg] ran registered-report-style review
(the 2021 preface reports 22 proposals, 10 accepted and 3 results papers); it has been argued for in NLP [@vanmiltenburg2021prereg],
weighed against its costs [@sogaard2023twosided] and adapted to predictive modelling
[@hofman2023prereg]. Vaccaro [@vaccaro2026prereg] lists memory settings among the
researcher degrees of freedom of experiments with AI agents (agents as subjects, so the
fit is by analogy), and Wilder and Zhou [@wilder2025evaluation] propose that ML venues
require a declaration of preregistration for field experiments. In IR, a Dagstuhl report
[@bauer2023dagstuhl] recommends results-blind review. The only memory-specific
pre-registered design we found is Feng et al.'s, on benchmarks. This trial is a
*registration*, not a registered report (its protocol was never peer-reviewed before
data), and its deviations are in Appendix A. The cross-field arguments
[@nosek2018prereg; @chambers2022registeredreports; @munafo2017manifesto] are the standing
justification. Registration was associated with a change in reported findings: 17 of 30
large NHLBI trials before 2000 reported significant benefit, against 2 of 25 after
mandatory prospective registration of outcomes [@kaplan2015nullnhlbi]. This observational
comparison does not identify registration as the cause.

**Power language needs care.** The critiques of low power [@ioannidis2005false;
@button2013power; @gelman2014beyond] and of post-experiment power calculations
[@hoenig2001abuse] apply here; Hoenig and Heisey also call power calculations "valuable in
planning an experiment". Our saturated minimum detectable effect (under the
spec's fractional counting and, at the registered 19 clusters, under whole-epoch counting
too; whole-epoch counting at the sensitivity analysis's 20 clusters flips it, §4.1.1) is prospective and
outcome-independent, which is the planning form, but its inputs are the problem: the ICC was
estimated for a different quantity (§4.1.1). The choice of significance test is known to
change error rates on IR test collections [@urbano2019significance]; we know of no
corresponding analysis for live retrieval experiments.

### 8.5 Position

**Not new:** that memory evaluation scores systems rather than behavioural effect;
randomising a retrieval-side lever with known propensities; the switchback design and its
inference; pre-registering ML experiments. **What this trial is:** a pre-registered,
beacon-seeded, fleet-level switchback on live agent traffic, with per-brief provenance,
instrument controls, and a null reported with its power failure and the
inconsistencies in its own registration. **What it is not:** it does not identify per-memory utility, randomise
within a brief, estimate carryover or measure cost; it compares two policies, not memory
against none; it is one system on one fleet; and <!-- SHAM-JANELA: pending -->its specificity control covers what was
served on the `w = 4` epochs only, not outcomes (§4.0.1c).<!-- /SHAM-JANELA --> **What it adds, narrowly:** a live-traffic instance of the positivity failure
CMP formalises (§3.0.1), and a registration whose sample size and whose estimand each
looked complete alone and each contradicted another lock of the same registration. **What would falsify this positioning:** a
pre-registered randomised memory trial on live traffic published before ours. A bounded
search (web and arXiv, 2026-10-03/04, one agent, not a systematic review) found none, nor
an IR registered-report track.

*Reading depth.* Full or partial text was read for the TMLR survey (§9.6, with string
counts on the pinned PDF), Omri et al., Evo-Memory, Behnam & Wang, Feng et al., the
NeurIPS 2021 preface, Søgaard et al., Vaccaro and the Dagstuhl report. MemoryArena v2 was
only string-searched. No book was opened, and several items are known at abstract or
metadata level and are cited for their topic, not for a finding. Per-reference record:
`_sprint-2026-10-04/B-related-work.verification-log.md`; long form of this section:
`_sprint-2026-10-04/B-related-work.md`.

---

## 9. Discussion

In short, the registration outlived its intervention: it sized the trial for 234 epochs on
a designation eligible for 20 (§3.0.1), and the under-powering follows from that. Under the
analysis spec's fractional counting, which governs the power statement, and under the
planning assumptions, no reduction, including total elimination, reaches 80% power, and
this was projection-robust under
the spec's cuts ten days before the window closed, and written down rather than
discovered afterwards. At the registered analysis set of 19 epochs, whole-epoch counting
gives the same verdict; only at the sensitivity analysis's 11 treatment and 9 control does
it flip (effective size 96.41 against 95.26), where total elimination becomes borderline
detectable and 80% power holds only for reductions of about 99.6% or more (§4.1.1). The
primary we report, H1c, replaced the deposited primary H1 before any data, in a revision
that was not deposited; under H1 the registered test rejects, and §4.3 states why we do
not read that as an effect of the dose (§1). Two further commitments made before the seed
were not kept, and we found both from the artifacts while preparing this version: the
feasibility stop of the prospective estimand was met in Epoch 1 and not executed (§3.0),
and the assignment rule the seed declaration named was replaced by the registered script
after the round was emitted (§1). What remains, in place of an effect estimate, is three observations
about instruments, each of which cost us a published error to find:

**A pre-registration can contradict itself, and the contradiction can survive to the
outcome.** It happened twice here, at two scales. Two locks eighteen days apart defined one
estimand incompatibly (§4.4), and neither review caught it. And the sample size was
computed for 234 epochs while the intervention it would act on had a 30-day life:
8.5% of the registered design (§3.0.1). The second is the more instructive, because
each number is correct in isolation: `sizing.py` did its arithmetic correctly, and the
30-day window is a documented default. Neither document was wrong; they were never read
against each other. The failure mode is two locks that each look complete alone, with
no step in the process whose job is to cross them.

**An interval that excludes zero can be the artifact, and the non-rejection the sound result.** The
only rejection under the registered decision rules is on the hypothesis demoted, in the undeposited
revision, as requiring a 955% effect at the calibration share of altered briefs. H1a's
unadjusted p-value (0.0241) is below 0.05 and is not a rejection: the registration decides
it in a Holm family, where it does not reject. Reading
the rejection and ignoring the null would have inverted the paper; under the deposited
registration that rejection is on the primary, which is why §1 reports both.

~~**A pre-committed alternative explanation can be refuted by the data it was written to
protect.** The concentration projection that made a null ambiguous did not hold; coverage
was flat. That weakens a defence we had reserved for ourselves, which is the only
circumstance in which a pre-commitment demonstrably did its job.~~

**A planning statistic and a realized statistic can share a name and not a quantity.** We
first read the flat distribution of designated-chunk serving occurrences as refuting the
pre-committed concentration projection, which counted covered action opportunities by
signature. The two count different things: the projection is untested, and the
pre-committed indistinction between a mechanism that does not work and lessons too generic
to work stands (§4.5). *(Corrected in rc7.)*

We publish an under-powered null in full because the two alternatives (not publishing, or
publishing a claim the design cannot support) are the behaviours that make under-powered
trials worth less than nothing to the people who read them.

---

## References

Citations in §8 are pandoc-style (`[@key]`) and resolve in `_sprint-2026-10-04/B-related-work.bib`,
which carries the full author lists, URLs and the per-entry notes on what is not established
(venue, publication status). The list below is generated from that file for the keys cited
here; where the two differ, the `.bib` file is authoritative. Reading depth per reference is
in `_sprint-2026-10-04/B-related-work.verification-log.md`. Artifacts of this study are cited
by file name in the text and listed in Appendix B.

- Albanie, S. et al. (eds.) (2022). Proceedings of the NeurIPS 2021 Workshop on Pre-registration in Machine Learning. https://proceedings.mlr.press/v181/. `[@albanie2022prereg]`
- Aronow, P. M. and Samii, C. (2017). Estimating average causal effects under general interference, with application to a social network experiment. *The Annals of Applied Statistics* 11(4). doi:10.1214/16-AOAS1005. `[@aronow2017interference]`
- Basse, G., Ding, Y. and Toulis, P. (2023). Minimax designs for causal effects in temporal experiments with treatment habituation. *Biometrika* 110: 155–168. doi:10.1093/biomet/asac024. `[@basse2023minimax]`
- Bauer, C. et al. (2023). Report from Dagstuhl Seminar 23031: Frontiers of Information Access Experimentation for Research and Education. *Dagstuhl Reports* 13(1): 68–154. doi:10.4230/DagRep.13.1.68. `[@bauer2023dagstuhl]`
- Bean, A. M. et al. (2026). Reliability of LLMs as medical assistants for the general public: a randomized preregistered study. *Nature Medicine* 32(2): 609–615. doi:10.1038/s41591-025-04074-y. `[@bean2026llmmedical]`
- Becker, J. et al. (2025). Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity. arXiv preprint. arXiv:2507.09089. `[@becker2025metr]`
- Behnam, A. and Wang, B. (2026). Causal Memory Policy: Making Memory Utility Identifiable by Intervening on Retrieval. arXiv preprint. arXiv:2610.02070. `[@behnam2026cmp]`
- Bertinetto, L. et al. (2020). The pre-registration experiment: an alternative publication model for machine learning research. *NeurIPS 2020 Workshop*. https://neurips.cc/virtual/2020/workshop/16158. `[@bertinetto2020prereg]`
- Blake, T. and Coey, D. (2014). Why marketplace experimentation is harder than it seems: the role of test-control interference. *Proceedings of the Fifteenth ACM Conference on Economics and Computation*: 567–582. doi:10.1145/2600057.2602837. `[@blake2014marketplace]`
- Bojinov, I. and Shephard, N. (2019). Time Series Experiments and Causal Estimands: Exact Randomization Tests and Trading. *Journal of the American Statistical Association* 114(528): 1665–1682. doi:10.1080/01621459.2018.1527225. `[@bojinov2019timeseries]`
- Bojinov, I., Simchi-Levi, D. and Zhao, J. (2023). Design and Analysis of Switchback Experiments. *Management Science* 69(7): 3759–3777. doi:10.1287/mnsc.2022.4583. `[@bojinov2023switchback]`
- Button, K. S. et al. (2013). Power failure: why small sample size undermines the reliability of neuroscience. *Nature Reviews Neuroscience* 14(5): 365–376. doi:10.1038/nrn3475. `[@button2013power]`
- Cameron, A. C., Gelbach, J. B. and Miller, D. L. (2008). Bootstrap-Based Improvements for Inference with Clustered Errors. *The Review of Economics and Statistics* 90(3): 414–427. doi:10.1162/rest.90.3.414. `[@cameron2008bootstrap]`
- Cameron, A. C. and Miller, D. L. (2015). A Practitioner's Guide to Cluster-Robust Inference. *Journal of Human Resources* 50(2): 317–372. doi:10.3368/jhr.50.2.317. `[@cameron2015practitioner]`
- Chambers, C. D. and Tzavella, L. (2022). The past, present and future of Registered Reports. *Nature Human Behaviour* 6(1): 29–42. doi:10.1038/s41562-021-01193-7. `[@chambers2022registeredreports]`
- Chapelle, O. et al. (2012). Large-scale validation and analysis of interleaved search evaluation. *ACM Transactions on Information Systems* 30(1): 1–41. doi:10.1145/2094072.2094078. `[@chapelle2012interleaved]`
- Deng, A. et al. (2013). Improving the sensitivity of online controlled experiments by utilizing pre-experiment data. *Proceedings of the Sixth ACM International Conference on Web Search and Data Mining*: 123–132. doi:10.1145/2433396.2433413. `[@deng2013cuped]`
- Du, P. (2026). Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers. arXiv preprint. arXiv:2603.07670. `[@du2026memoryautonomous]`
- Fabijan, A. et al. (2019). Diagnosing Sample Ratio Mismatch in Online Controlled Experiments. *Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining*: 2156–2164. doi:10.1145/3292500.3330722. `[@fabijan2019srm]`
- Feng, Z., Yao, M. and Lewis, D. S. (2026). Memory Transplants for LLM Agents: Disentangling Architecture and Content Transfer under a Code-to-Math Shift. *ICLR 2026 Workshop on Memory for LLM-Based Agentic Systems (MemAgents)*. https://openreview.net/forum?id=AIJsjIqfsp. `[@feng2026memorytransplants]`
- Gelman, A. and Carlin, J. (2014). Beyond Power Calculations: Assessing Type S (Sign) and Type M (Magnitude) Errors. *Perspectives on Psychological Science* 9(6): 641–651. doi:10.1177/1745691614551642. `[@gelman2014beyond]`
- Gordon, B. R. et al. (2019). A Comparison of Approaches to Advertising Measurement: Evidence from Big Field Experiments at Facebook. *Marketing Science* 38(2): 193–225. doi:10.1287/mksc.2018.1135. `[@gordon2019comparison]`
- He, Z. et al. (2026). MemoryArena: Benchmarking Agent Memory in Interdependent Multi-Session Agentic Tasks. arXiv preprint. arXiv:2602.16313. `[@he2026memoryarena]`
- Hoenig, J. M. and Heisey, D. M. (2001). The Abuse of Power: The Pervasive Fallacy of Power Calculations for Data Analysis. *The American Statistician* 55(1): 19–24. doi:10.1198/000313001300339897. `[@hoenig2001abuse]`
- Hofman, J. M. et al. (2023). Pre-registration for Predictive Modeling. arXiv preprint. arXiv:2311.18807. `[@hofman2023prereg]`
- Hofmann, K., Li, L. and Radlinski, F. (2016). Online Evaluation for Information Retrieval. *Foundations and Trends in Information Retrieval* 10(1): 1–117. doi:10.1561/1500000051. `[@hofmann2016online]`
- Hu, Y. and Wager, S. (2022). Switchback Experiments under Geometric Mixing. arXiv preprint. arXiv:2209.00197. `[@hu2022switchback]`
- Hu, Y. et al. (2025). Memory in the Age of AI Agents. arXiv preprint. arXiv:2512.13564. `[@hu2025memoryage]`
- Hu, Y., Wang, Y. and McAuley, J. (2025). Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions. arXiv preprint. arXiv:2507.05257. `[@hu2025memoryagentbench]`
- Huang, W. et al. (2026). A Survey of Agent Memory in the Second Half: Towards Self-Evolving and Long-Horizon Agents. *Transactions on Machine Learning Research*. arXiv:2602.06052. `[@huang2026survey]`
- Imbens, G. W. and Rubin, D. B. (2015). Causal Inference for Statistics, Social, and Biomedical Sciences: An Introduction. *Cambridge University Press*. doi:10.1017/CBO9781139025751. `[@imbens2015causal]`
- Ioannidis, J. P. A. (2005). Why Most Published Research Findings Are False. *PLoS Medicine* 2(8): e124. doi:10.1371/journal.pmed.0020124. `[@ioannidis2005false]`
- Johari, R. et al. (2022). Experimental Design in Two-Sided Platforms: An Analysis of Bias. *Management Science* 68(10): 7069–7089. doi:10.1287/mnsc.2021.4247. `[@johari2022twosided]`
- Johnson, G. A., Lewis, R. A. and Nubbemeyer, E. I. (2017). Ghost Ads: Improving the Economics of Measuring Online Ad Effectiveness. *Journal of Marketing Research* 54(6): 867–884. doi:10.1509/jmr.15.0297. `[@johnson2017ghost]`
- Kaplan, R. M. and Irvin, V. L. (2015). Likelihood of Null Effects of Large NHLBI Clinical Trials Has Increased over Time. *PLOS ONE* 10(8): e0132382. doi:10.1371/journal.pone.0132382. `[@kaplan2015nullnhlbi]`
- Kohavi, R. et al. (2009). Controlled experiments on the web: survey and practical guide. *Data Mining and Knowledge Discovery* 18(1): 140–181. doi:10.1007/s10618-008-0114-1. `[@kohavi2009controlled]`
- Kohavi, R., Tang, D. and Xu, Y. (2020). Trustworthy Online Controlled Experiments: A Practical Guide to A/B Testing. *Cambridge University Press*. doi:10.1017/9781108653985. `[@kohavi2020trustworthy]`
- Lewis, R. A. and Rao, J. M. (2015). The Unfavorable Economics of Measuring the Returns to Advertising. *The Quarterly Journal of Economics* 130(4): 1941–1973. doi:10.1093/qje/qjv023. `[@lewis2015unfavorable]`
- Li, L. et al. (2011). Unbiased offline evaluation of contextual-bandit-based news article recommendation algorithms. *Proceedings of the Fourth ACM International Conference on Web Search and Data Mining*: 297–306. doi:10.1145/1935826.1935878. `[@li2011unbiased]`
- Maharana, A. et al. (2024). Evaluating Very Long-Term Conversational Memory of LLM Agents. *Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)*: 13851–13870. doi:10.18653/v1/2024.acl-long.747. `[@maharana2024locomo]`
- Munafò, M. R. et al. (2017). A manifesto for reproducible science. *Nature Human Behaviour* 1(1): 0021. doi:10.1038/s41562-016-0021. `[@munafo2017manifesto]`
- Nosek, B. A. et al. (2018). The preregistration revolution. *Proceedings of the National Academy of Sciences* 115(11): 2600–2606. doi:10.1073/pnas.1708274114. `[@nosek2018prereg]`
- Omri, Y. et al. (2026). Agent Memory: Characterization and System Implications of Stateful Long-Horizon Workloads. arXiv preprint. arXiv:2606.06448. `[@omri2026agentmemory]`
- Peng, S. et al. (2023). The Impact of AI on Developer Productivity: Evidence from GitHub Copilot. arXiv preprint. arXiv:2302.06590. `[@peng2023copilot]`
- Radlinski, F., Kurup, M. and Joachims, T. (2008). How does clickthrough data reflect retrieval quality? *Proceedings of the 17th ACM Conference on Information and Knowledge Management*: 43–52. doi:10.1145/1458082.1458092. `[@radlinski2008clickthrough]`
- Saveski, M. et al. (2017). Detecting Network Effects: Randomizing Over Randomized Experiments. *Proceedings of the 23rd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*: 1027–1035. doi:10.1145/3097983.3098192. `[@saveski2017network]`
- Søgaard, A., Hershcovich, D. and de Lhoneux, M. (2023). A Two-Sided Discussion of Preregistration of NLP Research. *Proceedings of the 17th Conference of the European Chapter of the Association for Computational Linguistics*. doi:10.18653/v1/2023.eacl-main.6. `[@sogaard2023twosided]`
- Srivastava, S. S. (2026). Causal Intervention-Based Memory Selection for Long-Horizon LLM Agents. arXiv preprint. arXiv:2605.17641. `[@srivastava2026cmi]`
- Sun, L., Zhang, H. and Zhang, X. (2026). External Experience Serving in Production LLM Systems: A Deployment-Oriented Study of Quality-Cost Trade-offs. arXiv preprint. arXiv:2606.11806. `[@sun2026experienceserving]`
- Tablan, V., Taylor, S. and Bernhem, K. (2026). Learning on the Job: Continual Learning from Deployment Feedback for Frozen-Weights Agents. arXiv preprint. arXiv:2607.22157. `[@tablan2026learningonthejob]`
- Urbano, J., Lima, H. and Hanjalic, A. (2019). Statistical Significance Testing in Information Retrieval: An Empirical Analysis of Type I, Type II and Type III Errors. *Proceedings of the 42nd International ACM SIGIR Conference on Research and Development in Information Retrieval*: 505–514. doi:10.1145/3331184.3331259. `[@urbano2019significance]`
- Vaccaro, M. (2026). Preregistration for Experiments with AI Agents. arXiv preprint. arXiv:2606.11217. `[@vaccaro2026prereg]`
- van Miltenburg, E., van der Lee, C. and Krahmer, E. (2021). Preregistering NLP research. *Proceedings of the 2021 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies*. doi:10.18653/v1/2021.naacl-main.51. `[@vanmiltenburg2021prereg]`
- Webb, M. D. (2014). Reworking Wild Bootstrap Based Inference for Clustered Errors. *Queen's University, Department of Economics*, Queen's Economics Department Working Paper 1315. http://qed.econ.queensu.ca/working_papers/papers/qed_wp_1315.pdf. `[@webb2014reworking]`
- Wei, T. et al. (2025). Evo-Memory: Benchmarking LLM Agent Test-time Learning with Self-Evolving Memory. arXiv preprint. arXiv:2511.20857. `[@wei2025evomemory]`
- Wilder, B. and Zhou, A. (2025). Fostering the Ecosystem of AI for Social Impact Requires Expanding and Strengthening Evaluation Standards. arXiv preprint. arXiv:2510.18238. `[@wilder2025evaluation]`
- Wu, D. et al. (2025). LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory. arXiv preprint. arXiv:2410.10813. `[@wu2025longmemeval]`
- Xiong, Z. et al. (2025). How Memory Management Impacts LLM Agents: An Empirical Study of Experience-Following Behavior. arXiv preprint. arXiv:2505.16067. `[@xiong2025memorymanagement]`
- Zhang, Z. et al. (2024). A Survey on the Memory Mechanism of Large Language Model based Agents. arXiv preprint. arXiv:2404.13501. `[@zhang2024memorysurvey]`
- Zheng, J. et al. (2025). LifelongAgentBench: Evaluating LLM Agents as Lifelong Learners. arXiv preprint. arXiv:2505.11942. `[@zheng2025lifelongagentbench]`
- Zou, H. P. et al. (2026). When Users Change Their Mind: Evaluating Interruptible Agents in Long-Horizon Web Navigation. arXiv preprint. arXiv:2604.00892. `[@zou2026interruptbench]`

---

## Appendix A: relation to the pre-registration

Deviations are logged in `DEVIATIONS-FOR-PAPER.md`, which is append-only, and the
substantive ones for this paper are §10.29 through §10.34; the primary switch, the
omission of H2 and H3 until rc7, the unexecuted stopping rule and the replaced assignment
rule below are not in it, and are declared here and in §1, §3.0 and §5. The list is not summarized here
because a summary of a deviation log is a second copy that will diverge from the first.

~~Three~~ ~~Seven~~ Nine that a reader cannot reconstruct from the estimates alone:

- the primary outcome: the deposited registration (v1.12) names H1, with H1a–H1c as a
  Holm-corrected co-primary family; H1c became the primary on 2026-08-30
  (`DESIGN-REVISION-2026-08-30.md` §3-ter; `PROSPECTIVE-ESTIMAND-2026-08-30.md` §3-bis),
  before the assignment seed was drawn and before any randomized epoch, in documents dated
  by our commit log and not deposited. For the deposited primary, H1, the registered test
  rejects (`p = 0.0133`); under the deposited Holm correction no member of the family
  rejects, H1a included (unadjusted 0.0241, adjusted 0.1205) (§1);
- nothing after v1.12 was deposited: a v1.13 amendment prepared on 2026-08-27 was held
  (`deposit/PLAN-v1.13.md`); the start of the trial was authorized by
  `PROSPECTIVE-ESTIMAND-2026-08-30.md`, and the analysis was fixed by the analysis
  specification of 2026-09-10, both undeposited and dated by our commit log only;
- the registered H2 (task regret) and H3 (retrieval metrics) were not reported, and until
  rc7 their absence was not declared anywhere; from rc8, H2 is reported with three
  declared choices the registration does not fix and does not reject, and H3 is declared
  not computable (§5);
- the analysis of versions up to rc7 departed from the registered one in four places:
  percentile bootstrap instead of BCa, `09-02` included against the spec's §2, no cut at
  the designation's expiry inside `09-20` and no exposure offsets, and no fourth-family
  substitution in the panel. From rc8 the registered analysis is reported and that one is
  a sensitivity (§4); no registered verdict differs between them. Two parts of the
  registered analysis could not be implemented as written and are interpretations: the
  jackknife runs over the 19 realized epochs, not the 234 registered (§4), and the spec's
  "offset" for partial epochs is implemented as an exposure window (§3.0.1);
- a stopping rule declared before the seed (`PROSPECTIVE-ESTIMAND-2026-08-30.md` §3-bis:
  close the interventional arm with a null if Epoch-1 coverage falls below 36.7%) was met,
  32.4% by the definition the threshold was derived from, and was not evaluated or
  executed during the trial (§3.0);
- the assignment rule named in the seed declaration (`ASSIGN-SEED-2026-08-30.md`, a global
  sort) is not the registered `assign_arms.py`; it was replaced by the registered script
  24 min 38 s after the drand round was emitted, and the two assign different arms to 11 of
  the 20 realized epochs (§1);
- the analysis stratum migrated from `S2` to `≥ S1` by panel agreement (κ 0.87–0.93 at
  `≥ S1` against 0.31–0.53 for the S1/S2 split), so the S1/S2 division became an
  instrument finding rather than an analysis boundary;
- the dose band `{2 · 4 · 7.5}` was registered among *"what does not move, and could not"*
  and moves: 11/15/17 states of 350, monotone, saturating in `(4.0; 4.4]`. The
  registration promises less than what was measured;
- the designation was recorded as an open defect in v1.12 and was closed on 2026-08-26.

The two items where the registration promises *less* matter most: an error that favours
its authors is one they have no reason to correct unprompted.

## Appendix B: artifacts

| artifact | holds |
|---|---|
| `out/ITT-REGISTRADO-2026-10-05.json` · `measurement/estimador_itt_registrado.py` · `_sprint-2026-10-04/B-registered/RESULTADO.md` | **the registered analysis** (reported from rc8): every leg, the one-switch-at-a-time deltas, the Holm family, H2, provenance with the sha256 of the script, of its six imported modules and of every input; the control that rebuilds `ITT-2026-09-21.json` and `RERANDOMIZACAO-2026-09-21.json` byte for byte. Not yet in the ballast manifest (working list 17) |
| `ITT-2026-09-21.json` | the estimates of the sensitivity analysis (the analysis of versions up to rc7), both legs, bootstrap parameters |
| `ITEM7-DOSE-TOPO-2026-09-21.json` | the full 2 000-seed distribution of §4.7 |
| `ASSIGNMENT.json` · `ASSIGNMENT-SERVING.json` | designation and served arms |
| `DESIGNATION-2026-08-26.json` | the 19 designated items |
| `estimador_itt.py` · `assign_arms.py` · `pilot_replay.py` | the instruments |
| `p2-serving.ndjson` · `episodios-ensaio-20260921.jsonl` | serving log and episodes |
| `ensaio-20260921-PRIMARIO-3fam.jsonl` | 3 592 rows: 3 585 verdicts (1 195 per family) and 7 superseded xAI non-verdicts (6 quota, 1 missing), three families |
| `ensaio-20260921-SENSIB-deepseek.jsonl` | 1 195 verdicts, fourth family (sensitivity) |
| `COBERTURA-M10-2026-09-21.json` · `cobertura_e_m10.py` | coverage by arm, per-signature share, M10 and its four legs |
| `RERANDOMIZACAO-2026-09-21.json` · `rerandomizacao.py` | the registered sharp-null test, 10 000 redesigns (§4.0.1a, §4.0.2) |
| `CONTROLES-JANELA-COMPLETA-2026-09-21.json` · `controles_instrumento.py` | instrument controls over all 19 served epochs, `09-02` having served none (§4.0.1b) |
| `out/CONTROLES-2026-09-10.json` | the same controls at the trial's midpoint — 6/6 and 3/3, superseded by the row above |
| `out/H1C-POWER-REALIZADO-2026-09-10.json` | the MDE saturation of §4.1, computed before the window closed |
| `out/H1C-POWER-FRACIONARIA-2026-09-10.json` · `out/H1C-POWER-SEM-0903-2026-09-10.json` | the two other inclusion cuts of the power margin (§4.1.1) |
| `out/expiracao-designados-2026-09-09.json` | the designation's expiry measurement of §3.0.1 — `created_at` and the 30-day window |
| `MANIFESTO-LASTRO-P2.json` | sha256 of every artifact in this table, for loss detection |
| `ITT-SENSIB-PRECOMPROMETIDA.json` (sha256 `0191ee54…`) | the **pre-committed** sensitivity leg (§9.1 of the spec: all partials removed) — source of the pre-committed rows of §4.1, §4.2, §4.3 and of Figure B1(b). Not listed here before v2 |
| `out/NOGO-replay-sonda{2,3}-2026-09-23.json` · `out/NOGO-replay-ts-com-alteracao-2026-09-23.txt` | the two replay probes of §4.0.1c and the 132 states they replayed |
| `_sprint-2026-10-04/B-replay-fidelity/` (8 runs, 2 stratum files, `RESUMO.txt`) · `measurement/sprint-replay-estratos.mjs` · `measurement/sprint-replay-fidelidade-resumo.py` | the corpus × cut replay test and the stratum structure of §4.0.1c; the summary script recomputes every number from the runs |
| `measurement/sprint-figB-h1a-inversao.py` · `measurement/sprint-figB-sementes-dose-topo.py` · `_sprint-2026-10-04/figures/` | Figures B1 and B2 (SVG + PNG + `.run.json`), regenerated from the artifacts above; each script aborts if its plotted values diverge from the locked JSON |
| `_sprint-2026-10-04/figures/figB2-item7-crosscheck-20000.json` · `measurement/sprint-figB-item7-crosscheck.py` | an independent 20 000-seed redraw with a declared seed recipe, corroborating §4.7 within Monte-Carlo error; not a reproduction of the 2 000-seed run, whose seed recipe was not recorded |
| `_sprint-2026-10-04/B-sham-v2/REPORT.md` · `B-sham-v2/job-v2b/RESUMO.json` · `B-sham-v2/job-v2b-runs.tgz` · `B-sham-v2/job-v2b/RUNS.sha256` · `B-sham-v2/fidelity-110/` | the sham replay of §4.0.1c (21 runs, 2,646 states each), its summary and per-run hashes, and the fidelity runs on the 110 states (added in rc3) |
| `_sprint-2026-10-04/REVIEW-B-rc2-evidence/power-*.json` · `checks.py` | the H1c power recomputed at 11T/9C and under fractional counting (§4.1.1), and the `09-20` coverage split at expiry (§4.6) (added in rc3) |
| `out/C12-EMPATES-POR-BRACO-2026-10-05.json` · `measurement/sprint-c12-empates-por-braco.py` | the exact ties of the four-vote set per arm and their reach into H1c (§4, §6, §7); the script imports the tie rule and runs `estimador_itt.py` unchanged, and aborts unless it reproduces the per-arm counts of `ITT-2026-09-21.json` and the 20 / 28 of §6 item 6 (added in rc4) |
| `out/C12-EMPATES-COMO-FAILURE-2026-10-05.json` · same script, `--empates-como-failure-out` | the same object plus the H1c point with every tie resolved as `failure`, through the imported rule (one synthetic `failure` vote per tied episode; no other label moves, checked) (§4, §7) (added in rc4, after the independent check) |
| `_sprint-2026-10-04/B-rc7/checks-rc7.py` · `checks-rc7.json` | the rc7 numbers no earlier artifact held (realized altered-brief share, active-mode coverage, two-sided power reach, adjudication counts, the planning concentration, the preliminary run's file time) (added in rc8; in the ballast per working list 17, not yet done) |
| `_sprint-2026-10-04/B-rc8/checks-rc8.py` · `checks-rc8.json` | the registered analysis on the two sensitivity legs, per-epoch session-hours and volumes, the dilution ratios and the H1 identity (block A); the Epoch-1 coverage against the stopping threshold (block D); the declared and the registered assignment rules on round 31774052 (block E). It aborts unless it first reproduces the registered and the sensitivity legs of `out/ITT-REGISTRADO-2026-10-05.json` exactly and the points of the locked sensitivity legs (block G) (added in rc8; not yet in the ballast manifest) |
| `out/C12-EMPATES-REGISTRADO-2026-10-05.json` | the four-vote ties under the registered window and epoch set, the four-vote H1c point under the paper's rule and with ties as `failure`, and the count of ties in the substitution panel (0); written by `checks-rc8.py` block C, which aborts unless it reproduces the rc4 counts and points under the sensitivity analysis's window; the rc4 files are unchanged (added in rc8; not yet in the ballast manifest) |
| `measurement/sprint-figB-h1a-inversao-registrado.py` · `_sprint-2026-10-04/figures/figB1-h1a-inversao-registrado.{svg,png,run.json}` | Figure B1 under the registered analysis; aborts unless panel (a) reproduces the registered session-hours and panel (b) the registered artifact and `checks-rc8.json` (added in rc8; not yet in the ballast manifest) |

### B.1 Where each number in the text comes from

Added 2026-09-21 after an adversarial reviewer observed that the header promised universal
traceability and several numbers had no artifact named beside them. That review was
right, and understated: two of them had no artifact at all: the coverage figures and
the whole of M10 were computed by an ad-hoc script and never saved. `cobertura_e_m10.py`
now produces them, and reproduces the ad-hoc values exactly.

| number | §  | artifact |
|---|---|---|
| registered analysis: H1, H1a, H1c, every BCa interval and re-randomization p-value of the locked leg; session-hours, opportunities and repeats per arm; Holm-adjusted p-values (0.1205 / 0.0964); H2; panel counts 1 179 / 16 / 20 / 13; the expiry cut (33 episodes, 22.835 weighted opportunities, 2 repeats, 0.6235 → 0.5154 h); the one-switch deltas of §4 | Abstract, 1, 3.0.1, 4–4.3, 5 | `out/ITT-REGISTRADO-2026-10-05.json` (added in rc8) |
| registered analysis on the pre-committed and post-hoc legs; per-epoch session-hours (0.25–0.97 h, 7.13 h = 57%); reductions 69.8% / 44.6% and ratios 22.2 / 14.2, 15.3 / 9.8, 10.2 / 6.5; per-epoch volumes 103.5 / 137.7, 95.5 / 137.7 and 6.08 / 10.96; hours per epoch 0.543 / 0.541; H1c 15% and 0.0351; identity error 6.0×10⁻⁶ | Abstract, 4.0.2, 4.1–4.3, 7 | `_sprint-2026-10-04/B-rc8/checks-rc8.json`, block A (added in rc8) |
| Epoch-1 coverage 45 / 139 = 32.4% (Wilson [25.2%; 40.5%]); 34 / 101, 30 / 75, 54.5% weighted; 92.1% / 89.4% for the 19 designated groups | Abstract, 3.0, App. A | `_sprint-2026-10-04/B-rc8/checks-rc8.json`, block D, from `episodios-ensaio-20260921.jsonl` and `out/CONCENTRATION-2026-08-30.json` (added in rc8) |
| declared vs registered assignment rule: 130 of 234 and 11 of 20 epochs with a different arm; 10 / 10 against 9 / 11; `2426d13d…` reproduced | Abstract, 1 | `_sprint-2026-10-04/B-rc8/checks-rc8.json`, block E; commit times 21:33:46Z and 21:56:42Z from the commit log (added in rc8) |
| sensitivity analysis: H1, H1a, H1c and every interval | 4.1–4.3 | `ITT-2026-09-21.json` — except the pre-committed legs: |
| sensitivity analysis: pre-committed sensitivity of H1c, H1a and H1; session-hours 12.16 / 4.08 | 4.1–4.3 | `ITT-SENSIB-PRECOMPROMETIDA.json`, field `sensibilidade` (added 2026-10-04) |
| sensitivity analysis: session-hours per arm, opportunities, repeats | 4.2 | idem |
| 7.13 h at `09-14`; session `d37a5964…`, 3 episodes, span 6.33 h; 74/65/56 episodes | 4.2 | `episodios-ensaio-20260921.jsonl` |
| coverage 27.98% / 26.92%; 4 324 occurrences; 19/19 signatures at ≈5.3% | 4.5 | `COBERTURA-M10-2026-09-21.json` |
| the fabricated 139 650 that `boost_by_id` would yield | 4.5 | idem, field `nota_boost` |
| `r` and all four legs; −0.0521 against dose | 4.6 | idem, field `M10` |
| truncation/chance split, 2 000 seeds | 4.7 | `ITEM7-DOSE-TOPO-2026-09-21.json` |
| Monte-Carlo s.e. 0.035 of the conditional mean; signed shares −1.0% / +101.0% | 4.7 | computed from the histogram in `ITEM7-DOSE-TOPO-2026-09-21.json`; recorded in `_sprint-2026-10-04/figures/figB2-sementes-dose-topo.run.json` |
| `control` conditional mean 9.991 | 4.7 | **no artifact** — `DEVIATIONS-FOR-PAPER.md` only; corroborated (10.0124 ± 0.0146) by `_sprint-2026-10-04/figures/figB2-item7-crosscheck-20000.json` |
| spans 9.71 / 8.86 / 8.03 min of the three busiest `09-14` sessions | 4.2 | `episodios-ensaio-20260921.jsonl`; recorded in `_sprint-2026-10-04/figures/figB1-h1a-inversao.run.json` |
| every number of §4.0.1c (0/132; 22/22; 17/22; strata; pool 108 / 115) | 4.0.1c | `_sprint-2026-10-04/B-replay-fidelity/RESUMO.txt` and the runs beside it; 11.9 and 1.5 × 10⁻¹⁰ are hypergeometric arithmetic on those counts (`B-replay-fidelity.md` §4) |
| ~~implied standard errors 0.0279 / 0.0320 (power) and 0.0165 (bootstrap)~~ (struck text only; withdrawn in rc7 as inferential claims) | 4.1.1 | arithmetic on `out/H1C-POWER-REALIZADO-2026-09-10.json` (`p0`, `detectavel_no_limite_p1_igual_zero: false`) and the H1c interval of `ITT-2026-09-21.json`; z₀.₉₇₅ = 1.960, z₀.₈ = 0.842 (added 2026-10-04) |
| power at the sensitivity analysis's 11T/9C (effective size 96.41 against 95.26, relative MDE 0.996, i.e. 80% power only for reductions of about 99.6% or more) and fractional with `09-02` (91.49, margin 4.1%); at the registered 11T/8C, the reproduction of the artifact (90.2) | 4.1.1 | `_sprint-2026-10-04/REVIEW-B-rc2-evidence/power-*.json`, from the unchanged `measurement/potencia-h1c.py` (added in rc3) |
| sensitivity analysis: H1 reductions 70.7% / 47.1%; 22.5 / 15.0 and 10.3 / 6.9 times total elimination; H1c relative difference −22% | Abstract, 4.0.2, 4.1.1, 4.3 | `_sprint-2026-10-04/REVIEW-B-rc2-evidence/checks.py` on `ITT-2026-09-21.json`; 3.14% (the pre-trial calibration share at `w = 2`, 11 of 350) from `out/H1C-POWER-REALIZADO-2026-09-10.json` (added in rc3) |
| realized altered-brief share 335 / 7 350 = 4.56% in active mode (the artifact's 337 / 7 392 includes 2 shadow changes); `09-01` 22 / 630 = 3.49%; ratios 15.5 / 10.3 at the realized share in the sensitivity analysis; coverage 2 057 / 7 350 in active mode | Abstract, 4.0.1b, 4.0.2, 4.3, 4.5 | `_sprint-2026-10-04/B-rc7/checks-rc7.json` (blocks A, B), from `p2-serving.ndjson`, after reproducing the artifact's 337 / 7 392 and 2 068 / 7 392 (added in rc7) |
| `p1 = 0.25` reaches about 86% (84.8) and 89% (91.49, the sensitivity analysis's set); `09-01` by clock gives 84.78 / 91.47 | 4.1.1 | `_sprint-2026-10-04/B-rc7/checks-rc7.json` (block C), with `poder_z` copied unchanged from `measurement/potencia-h1c.py` (added in rc7) |
| 1 195 submitted, 1 159 with three substantive verdicts, 36 `unknown` (three families; the registered substitution counts are in the first row) | 4, 6 | `_sprint-2026-10-04/B-rc7/checks-rc7.json` (block D), through `carregar_verdicts` (added in rc7) |
| 93.8% = 573 / 611 covered action opportunities | 4.5 | `out/CONCENTRATION-2026-08-30.json`; `_sprint-2026-10-04/B-rc7/checks-rc7.json` (block E) (added in rc7) |
| `ITT-PRELIMINAR.json`: file time 16:16:44 local (19:16:44Z), 2 000 replicates, H1a −143.92 | 1.1 | the file itself and `_sprint-2026-10-04/B-rc7/checks-rc7.json` (block F) (added in rc7) |
| 1 056 s (designation round 31657512); 21:18:35Z and 21:32:04Z, 13 min 29 s (assignment round 31774052); commits of 16:51:56Z and 20:51:20Z | 1 | `DESIGNATION-2026-08-26.json` (`declaracao`, `emissao_de_R`); `ASSIGN-SEED-2026-08-30.md`; the commit log (added in rc7) |
| opportunities per epoch 103.5 / 137.7 (registered; 1 138.47 / 11 and 1 101.75 / 8) and 100.3 / 132.3 (sensitivity analysis) | 7 | `out/ITT-REGISTRADO-2026-10-05.json`; `ITT-2026-09-21.json` (1 103.75 / 11 and 1 191.14 / 9) (added in rc3; registered in rc8) |
| `09-20`: 385 briefs before expiry, 98 with a designated item (25.5%); 287 after, 0 | 4.6 | `_sprint-2026-10-04/REVIEW-B-rc2-evidence/checks.py` on `p2-serving.ndjson` and `DESIGNATION-2026-08-26.json` (added in rc3) |
| sham: 132 / 146 against 81–122 / 84–132; `p = 0.0476`; 155 at `w = 100 000`; 2,646/2,646; 110/110 | 4.0.1b, 4.0.1c | `_sprint-2026-10-04/B-sham-v2/job-v2b/RESUMO.json`; 110/110 and the 36 / 89 counts (53 = 89 − 36) in `B-sham-v2/RESUMO.txt`; cost and state counts (19,567; 11,865) in `B-sham-v2/REPORT.md` §3 (added in rc3) |
| <!-- SHAM-JANELA: pending -->whole-window sham, running: 11,812 reconstructible states of 18 epochs; `09-01` and 53 states excluded; `job-janela2`, relaunched 2026-10-05T09:39:53Z, expected about 2026-10-07T03:00Z | 4.0.1c | `_sprint-2026-10-04/B-sham-v2/JANELA-LANCAMENTO.md` (launch record; no result yet) (added in rc4)<!-- /SHAM-JANELA --> |
| four-vote ties: 28 (10 treatment, 11 control, 7 outside the window); 4 / 7 of them H1c opportunities, 0 failures among those; 3 change a label | 4, 6, 7 | `out/C12-EMPATES-POR-BRACO-2026-10-05.json`, from `ensaio-20260921-*.jsonl`, `episodios-ensaio-20260921.jsonl` and `ASSIGNMENT-SERVING.json` (added in rc4) |
| four-vote ties under the registered window and set: 10 treatment, 10 control, 7 outside the dates, 1 before `09-03`'s exposure window; 4 / 7 tied opportunities; four-vote H1c −0.0121 → −0.0211 with ties as `failure`; 0 ties in the substitution panel | 4, 7 | `out/C12-EMPATES-REGISTRADO-2026-10-05.json` (added in rc8) |
| Figure B1: 12.56 / 4.33 h; 7.13 h = 57%; other eighteen epochs 0.25–0.97 h | 4.2 | `_sprint-2026-10-04/figures/figB1-h1a-inversao-registrado.run.json` (added in rc8) |
| tied opportunities' HT weights 27.78 / 36.73; four-vote H1c point difference under the sensitivity analysis's window −0.0208 under the paper's rule, −0.0266 with ties resolved as `failure` (rerun −0.026571, first order −0.026566; the sixth decimal differs because the rerun uses a per-arm proportion stored rounded, 0.09189) | 4, 7 | `out/C12-EMPATES-COMO-FAILURE-2026-10-05.json` (`por_braco.*.empates_oportunidade_peso`; `contrafactual_empate_como_failure`), the same script with `--empates-como-failure-out` (added in rc4, after the independent check) |
| fractional effective size 84.8 over the 19 served epochs; the spec's own 96.4 for 9 control epochs | 4.1.1 | `out/H1C-POWER-FRACIONARIA-2026-09-10.json`; `SPEC-ANALISE-2026-09-10.md` §3 (added in rc4) |
| agreement 1 111/1 145; abstentions 26+6+1 / 13 / 11; gains 20, losses 28 | 6 | `ensaio-20260921-*.jsonl`, recomputed in `DEVIATIONS-FOR-PAPER.md` §10.31 |
| 20 designated, 19 served, 16+3+1 | 3 | `ASSIGNMENT-SERVING.json` + `p2-serving.ndjson` |

**Caveat.** Several of these are **outside the repository** and several are large.
`scripts/manifesto-lastro-p2.py` hashed the first 20 (154 MiB) on 2026-09-21;
`scripts/estende-lastro-p2.py` appended 30 more on 2026-10-05 without regenerating it, for 50
artifacts and 158 MiB. `scripts/backup-lastro-p2.sh` copies the 16 that live outside the
repository, with the hash recomputed **at the destination**; the other 34 are versioned in the
repository. The artifacts added in rc7 and rc8 (`ITT-PRELIMINAR.json`, `checks-rc7.*`,
`out/ITT-REGISTRADO-2026-10-05.json` with its script, `checks-rc8.*`,
`out/C12-EMPATES-REGISTRADO-2026-10-05.json` and the registered Figure B1) are **not yet in
the ballast manifest** (working list 17); the inputs of the registered analysis are the
ones the manifest already hashes, and its provenance records their sha256.
**Done: both legs now verified at the destination** (2026-09-22 01:48Z, and again 2026-10-05 13:03Z after item 10): local **12/12** then
**16/16**, off-machine **12/12** then **16/16** on a host that is not the one that served the trial: it has no
`/root/.openclaw`, its epoch pointer is frozen at 2026-08-23, and it already holds Paper
1's ballast. Identified by **capability, never by address**. A manifest proves the bytes
are the bytes; it does not prove a copy exists, which is why the copy is verified
separately and carries a dated receipt.

---

## Working list: struck in the commit that closes it

1. ~~**Ballast**: manifest + two verified copies~~ → **Done, 2026-09-22**: 20 artifacts
   hashed, 154 MiB; the 12 that live outside the repository copied, **both legs 12/12
   recomputed at the destination**; the other 8 versioned in the repository. Three defects of ours found
   and fixed along the way: a directory hash reimplemented in shell that diverged by one
   trailing newline, an `rsync` that ran *before* the check and so restored the corrupted
   byte it was meant to detect, and an `ssh` inside a `while read` that ate the loop's
   stdin and verified **1 of 12** while reporting "0 divergem".
   **Caveat (2026-10-04):** the manifest does not cover `ITT-SENSIB-PRECOMPROMETIDA.json`, the
   only source of the pre-committed rows of §4.1–4.3, so a published number rests on an
   artifact the ballast does not protect. Open as item 10; closed 2026-10-05.
2. ~~**Run the registered re-randomization**~~ → **Done, 2026-09-21** (§4.0.1a, §4.0.2):
   10 000 redesigns, 9 941 distinct patterns, control of 300/300 reproducing the spec. It
   **disagrees with the bootstrap on H1a**, and `H1` is now reported as an unexplained
   rejection.
3. ~~**Report the pre-committed instrument controls**~~ → **Done, two of three, 2026-09-21**
   (§4.0.1b): positive **11/11**, negative dual **8/8**, both re-measured over the full
   window. ~~**Critical.** **Still open: the sham replay**, which needs the serving code re-executed;
   our attempt to do it by counting over the log was invalid and is recorded as such.~~
   **Correction (2026-10-04): the sham was not executed** (§4.0.1c). The run launched on 2026-09-22
   produced no output, and its configuration was invalid: wrong corpus, inclusive cut,
   shams drawn from the 115-pool instead of the 108-pool. On the served corpus with the
   exact cut, the replay reproduces production 22/22 and responds to dose. ~~Still open as
   item 9.~~ → **Done, rc3 (2026-10-04)**: the corrected sham ran (item 9); all three
   pre-committed controls are now reported.
4. ~~**Measure the 30-day freshness question**~~ → **Done, 2026-09-21** (§3.0.1):
   `N = 234` **was** infeasible: the designation expires 2026-09-20 22:51:23, giving 20
   eligible epochs of 234. §9 *(numbered §8 before v2)* rewritten around it.
5. ~~**Adversarial review** of this manuscript~~ → **Done, 2026-09-21**: five families
   launched, **four delivered with `exit: 0` receipts** (DeepSeek, Grok, GLM on this paper;
   Kimi on Paper A). Their findings produced §1.1, §3.0, §3.0.1, §4.0.1, §4.0.2, §4.1.1,
   §4.1.2, Appendix B.1 and the corrections in §3.1, §4.1–4.5. The fifth (Codex) returned a
   review whose citations do not resolve against the file and is recorded as invalid in
   `REVISAO-ADVERSARIAL-2026-09-21.md`; a review that cites sections the document does not
   have is not evidence about the document.
6. ~~**Figures**: the H1a sensitivity (the single-epoch inversion) and the §4.7 seed
   distribution. Both derive from locked artifacts.~~ → **Done, 2026-10-04**: Figure B1
   (§4.2) and Figure B2 (§4.7), each generated by a script that aborts if its values
   diverge from the locked artifacts. Making them surfaced four corrections to the text
   (§4.2 pre-committed leg; "8 to 10 minutes"; the signed truncation share; the unresolved
   sign of +0.023); see the changelog. **Caveat.** The headline embedded in the B1 SVG still reads
   *"H1a turns on one epoch"*; regenerate it with the caption title of §4.2 (item 11).
7. ~~**Related work** — Paper A's §8 covers the surface literature, not trials of memory
   interventions.~~ → **Done, 2026-10-04**: §8, condensed (~2 000 words) from
   `_sprint-2026-10-04/B-related-work.md` (~4 100 words), with references resolving in
   `B-related-work.bib`. Before submission: re-check Behnam & Wang (arXiv 2610.02070,
   1 Oct 2026, not peer-reviewed) for a revised version, and re-read MemoryArena v2 in
   full.
8. **Deposit** as a new version of the registration, declaring the deviations **and** the
   result in one record. Blocked by ~~9 (valid sham) and 10 (ballast gap) and~~ <!-- SHAM-JANELA: pending -->15
   (whole-window sham).<!-- /SHAM-JANELA --> Also blocked by 17 (rc7 ballast) and 18
   (registered re-analysis), added in rc7; the record must declare the primary switch of §1.
   *(rc8: 18 is done; 17 now also covers the rc8 artifacts. The record must also declare
   the unexecuted stopping rule of §3.0 and the replaced assignment rule of §1.)*
9. ~~**Valid sham**: needs the trial `brief_log` 2026-09-08..09-20 from the production host
   (authorization pending). Everything else for it is in hand: served corpus, `rowid`
   cut, shams redrawn from the 108-pool (89 non-designated). `gera-shams.py` /
   `roda-sham.sh` must first be fixed, since both hard-code the preserved corpus and
   `--corte inclusivo` (§4.0.1c).~~ → **Done, 2026-10-04** (§4.0.1c): new generator,
   runner, test and summarizer (`sprint-*-sham-v2*`; the old scripts untouched); 21 runs on
   the served corpus with the `rowid` cut, 2,646 states of the `w = 4` epochs, shams drawn
   from the 36 boostable items; real 132 against 81–122, `p = 1/21`. <!-- SHAM-JANELA: pending -->The larger set
   (~~the 11,865 states of the trial window, about 36 h~~ 11,812 reconstructible states of
   the trial window) ~~is configured and not run~~ is running as item 15.<!-- /SHAM-JANELA -->
10. ~~**Ballast gap**: add `ITT-SENSIB-PRECOMPROMETIDA.json` and the artifacts marked † in
    Appendix B to `MANIFESTO-LASTRO-P2.json` and to both verified copies.~~ → **Done,
    2026-10-05**: 30 entries appended without regenerating the manifest: the 24 † rows, the
    five `out/` rows of 2026-09-09/10 that had never been hashed, and `B-sham-v2/RESUMO.txt`.
    The existing entries are byte-identical. It now hashes **50** artifacts (165 473 805 bytes
    = 158 MiB; sha256 `172c5382…`, previous versions kept). The 4 new ones that live outside
    the repository (`ITT-SENSIB-PRECOMPROMETIDA.json` and the three C12 files) are in both
    copies, **16/16 recomputed at the destination on each leg**, after a pre-check on both legs
    with nothing copied (receipts `RECIBO-ITEM10-20261005T125933Z.txt`,
    `RECIBO-ITEM10B-20261005T130316Z.txt`). The other 26 are versioned, **26/26** recomputed
    from `origin/main`. The whole-window sham (item 15) and `JANELA-LANCAMENTO.md` are not yet
    in it; they enter together when the job completes.
11. **Traceability of §4.7 and Figure B1**: save the `control` distribution (the 9.991)
    and the seed recipe of the 2 000-seed run in an artifact, or cite the 20 000-seed
    crosscheck instead; regenerate the B1 SVG headline. *(rc8: Figure B1 is now
    `figB1-h1a-inversao-registrado.svg`, generated with a headline that matches its
    caption; the old SVG is kept unchanged as the record of the sensitivity analysis. The
    §4.7 part stays open.)*
12. ~~**Second adversarial review** of this manuscript~~ → **Done, 2026-10-04**: five
    families launched, two valid (DeepSeek, Gemini); GLM, Grok and Kimi did not receive the
    file. 28 findings, 18 confirmed and applied in rc2, 2 rejected
    (`_sprint-2026-10-04/REVIEW-B-2026-10-04.md`).
13. **Two computations rc2 declares as not done**: ~~the H1c MDE at the ITT's 20 clusters (9
    control epochs; §4.1.1), and~~ M10 under the pre-committed leg that removes all three
    partials (§4.6). *(rc3: the first is done; §4.1.1 reports it.)*
14. ~~**Third adversarial review** of this manuscript (rc2)~~ → **Done, 2026-10-04**: one
    valid voice of four (Codex); 24 findings, 22 confirmed and applied in rc3, 2 rejected
    (`_sprint-2026-10-04/REVIEW-B-rc2-2026-10-04.md`). rc3 itself has not been reviewed.<!-- SHAM-JANELA: pending -->
15. **Whole-window sham**: the replay over the trial window, 11,812 reconstructible states of
    18 epochs (without epoch `09-01`, whose corpus has no hash proof, and without 53 states
    whose serve-state cut cannot be reconstructed), job `job-janela2`, relaunched
    2026-10-05T09:39:53Z, expected to finish about 2026-10-07T03:00Z. Add its result to
    §4.0.1c, §7 and B.1 before deposit.<!-- /SHAM-JANELA -->
16. ~~**Regression review of rc4**~~ → **Done, 2026-10-05**: one voice (Codex), 5 findings,
    5 confirmed and applied in rc5 (`_sprint-2026-10-04/APPLY-B-rc5.md`). rc5 itself has
    not been reviewed.
17. **Ballast for the rc7 and rc8 evidence**: add `ITT-PRELIMINAR.json` (the preliminary run that
    dates the §10.33 decision, §1.1) and `_sprint-2026-10-04/B-rc7/checks-rc7.json` with its
    script to `MANIFESTO-LASTRO-P2.json` and to both verified copies; *(rc8)* also
    `out/ITT-REGISTRADO-2026-10-05.json` with `measurement/estimador_itt_registrado.py` and
    `B-registered/RESULTADO.md`, `B-rc8/checks-rc8.json` with its script,
    `out/C12-EMPATES-REGISTRADO-2026-10-05.json`, and the registered Figure B1 with its
    script.
18. ~~**Registered re-analysis**: replace every `REANALISE` block of rc7 with the analysis as
    registered (panel substitution, the expiry cut with the spec's offsets, BCa with the
    leave-one-epoch-out jackknife, 19 epochs without `09-02`) and report the analysis of
    this version as a sensitivity; state why H2 and H3 are not reported (§5).~~ → **Done,
    rc8 (2026-10-05)**: all 108 blocks replaced (85 values, 23 sentences), the rc7 analysis
    reported as the sensitivity, H2 reported (§5), H3 declared not computable
    (`_sprint-2026-10-04/APPLY-B-rc8.md`).
19. ~~**Review of rc6**~~ → **Done, 2026-10-05**: two full reads (Codex, Fable), both NO-GO;
    findings verified against the artifacts and applied in rc7, except those that depend on
    the registered re-analysis, which are marked `REANALISE` (item 18;
    `_sprint-2026-10-04/APPLY-B-rc7.md`). rc7 itself has not been reviewed.
20. **Review of rc8**: the registered analysis, the two findings of §3.0 and §1 (the
    unexecuted stopping rule and the replaced assignment rule) and the rc8 sweep have not
    been reviewed by any voice.

**Caveat.** Items 2 and 3 were **registered analyses missing from the first draft**, not
enhancements; the sham (item 9) was run in rc3. A
manuscript that omits its own pre-registered inference test and its own instrument
controls is not ready, and the fact that three adversarial reviewers had to tell us is
itself the §6 pattern repeating on this document.

---

## Changelog: v2 (2026-10-04)

Prepared from `MANUSCRIPT-B.md` as of 2026-10-03, in `_sprint-2026-10-04/B-v2.md`; the
original is untouched. Release candidate rc2 is `_sprint-2026-10-04/B-v2-rc2.md`, prepared
from the form pass `B-v3.md` (a file name only; the manuscript version is v2). Every content
change below traces to a sprint report with its
artifacts; old text that was wrong is kept struck through beside its correction, as this
manuscript already does.

**Sham / replay fidelity** (source: `_sprint-2026-10-04/B-replay-fidelity.md` and
`B-replay-fidelity/`):

1. §4.0.1b table, specificity row: "running since 2026-09-22 01:40Z" struck → "not
   executed; the configuration launched was invalid; a valid one is runnable and not yet
   run".
2. §4.0.1b: the "It is now running" paragraph struck, with a correction note; the
   bullets on the 30-day pool and on the "two routes, one number" control annotated: both
   routes read the same, wrong corpus, so their agreement could not catch it (served pool
   108, not 115).
3. §4.0.1b limitation: the sentence calling `corpus-preservado-20260908.db` "the
   deliberately preserved corpus of the trial" struck and corrected: it is not the corpus
   that served (60 `memory/lessons.md` chunks re-ingested 2026-09-07 that production never
   had; served corpus = fd-recovered `e20260903`).
4. New §4.0.1c. The "no power by construction / `p = 1.0`" reading of 2026-09-23 is
   presented as superseded: the tie hypothesis is **refuted**. The zero came from (1) the
   wrong corpus and (2) the inclusive cut. With the served corpus and the `rowid` cut, the
   replay reproduces production 22/22 and responds to dose: 17/22 states at `w = 2`, 22/22
   at `w = 100 000`. Also declared: `gera-shams.py` drew from the 115-pool rather than the
   108-pool (a prediction of spurious "failed specificity", not a measurement). A valid sham
   is runnable and **not run**: it needs the trial `brief_log` after 2026-09-08, which
   exists only on the production host. Measured: 22 states, all in epoch `09-01`. Not
   measured: 110 of 132.
5. Working list item 3 updated; new item 9 (valid sham, authorization pending).

**Figures** (source: `phase2-inputs/B-figures.json`, `_sprint-2026-10-04/figures/`):

6. Figure B1 inserted in §4.2 and Figure B2 in §4.7, with captions, as relative links
   `figures/*.svg` from this file's location.
7. §4.2: the **pre-committed** sensitivity leg (`ITT-SENSIB-PRECOMPROMETIDA.json`: H1a
   −133.34, CI [−203.62; +7.41], contains zero; session-hours 12.16 / 4.08) is added and
   reported before the post-hoc leg, per §4.1's own rule. The section title "inverts its
   conclusion on one epoch" is replaced by "excludes zero only on the locked leg", and the
   abstract sentence is corrected to match. The B1 caption title is written to agree; the
   headline embedded in the SVG does not yet (item 11).
8. §4.3: H1's pre-committed leg added (−15.59, CI [−22.43; −4.05], excludes zero). Same
   artifact, same omission; no conclusion changes.
9. §4.2: "9 to 10 minutes" → "8 to 10 minutes" (measured 9.71 / 8.86 / 8.03 min).
10. §4.7: truncation share "1.0%" → "−1.0%" (the unsigned shares summed to 102%); "+0.023 …
    in the direction opposite to the intuition" → the sign is not resolved (0.7 MC s.e.;
    20 000-seed redraw gives −0.007 ± 0.011); notes that the `control` 9.991 has no
    artifact, that the 2 000-seed recipe was not recorded, and that `P(n = 1) = 10.15%`
    carries ≈0.7 pp of MC noise.
11. Appendix B: rows for `ITT-SENSIB-PRECOMPROMETIDA.json`, the replay probes, the
    replay-fidelity runs, the figure scripts and the 20 000-seed crosscheck, marked † as
    not covered by `MANIFESTO-LASTRO-P2.json`. B.1: rows for the pre-committed legs, the
    §4.7 MC numbers, the 9.991 (declared as having no artifact), the session spans and
    §4.0.1c. Working list: items 10 and 11 added; item 1 annotated.

**Related work** (source: `_sprint-2026-10-04/B-related-work.md`, `.bib`, verification
log):

12. New §8 "Related work" (~2 000 words), condensed from the ~4 100-word draft. It keeps
    the positioning against Behnam & Wang (arXiv 2610.02070) and the TMLR survey §9.6.
    Section references inside the draft were re-pointed to the manuscript's actual
    sections: "§1" for the under-covering interval and the ICC became §4.1.1. Sentences
    saying the sham was "still running" were replaced by the §4.0.1c status. The draft's
    relative dates ("two days old") became absolute ones.
13. New "References" section, generated from `B-related-work.bib` for the 61 keys cited;
    citations are pandoc-style `[@key]`. Four `.bib` entries are not cited in the condensed
    text (`frauen2026causalmethods`, `kohavi2012puzzling`, `garcin2014offline`,
    `rossetti2016contrasting`).
14. Renumbering: Discussion §8 → §9. Cross-references fixed: §1.1 ("One phrase in §9
    overstates") and working-list item 4. References to "§8 of the analysis spec" and to
    "Paper A's §8" are to other documents and are unchanged.

**Form only:**

15. The duplicated heading "### 3.1 Two classification errors of ours, and what they cost"
    was removed; one copy remains. Status header updated.

**rc2: adversarial review of 2026-10-04 and assembly fixes** (source:
`_sprint-2026-10-04/REVIEW-B-2026-10-04.md`, two valid voices of five, 18 confirmed
findings C1–C18; the phase-2 assembly report):

16. §3.0.1 (C1): "closed 51 minutes before the designation expired" replaced. The window
    closes **at** expiry (2026-09-20 22:51:23Z); the dose was switched off later, 09:43:05Z on
    2026-09-21 (`desliga-dose.ndjson`, archive stamp `20260921T094305Z`). No artifact held
    the 51 minutes.
17. §4.1.1 (C2): "19 analyzable clusters" named as the power calculation's population (11
    treatment, 8 control, `out/H1C-POWER-REALIZADO-2026-09-10.json`); the ITT has 20 and the
    MDE was not recomputed at 9 control epochs (working list 13).
18. §4 and §7 (C3): "a 2-2 tie" → an exact tie (*n*/2 failures, even *n*). Checked in
    `pilot_replay.py` (`carregar_verdicts`: fewer than three substantive verdicts are not
    adjudicated): the rule cannot bind in the three-family primary panel and binds in the
    four-vote sensitivity set; the §7 threat now says so.
19. Abstract (C4): H1a excludes zero on the locked leg only; H1 excludes zero on all three
    legs and is an unexplained rejection, set aside for the impossible 955% effect, with
    the denominator explaining part of it but not the residual (§4.3).
20. Appendix B caveat and working list 1 (C5): "all 14" and "17 artifacts" → the manifest
    hashes **20** (161 608 733 bytes = 154 MiB); 12 copied and verified 12/12 on both legs,
    8 versioned in the repository (`MANIFESTO-LASTRO-P2.json` sha256 `556ef20c…`, receipt
    `recibos/backup-20260922T014836Z.txt`).
21. §4.1.1 (C6): the "an interval must contain both 0 and −0.0896, hence span ≥ 0.0896"
    derivation and "they cannot both be right" are replaced by a comparison of implied
    standard errors: ≥ 0.0279 from the saturated MDE (0.0320 at `p0` = 0.0896) against
    0.0165 from the bootstrap interval (59%). The "72%" is withdrawn with the derivation.
22. §4.4 heading and §5 table (C7): "unevaluable" → "trivially 1.0"; §5 column "why
    unevaluable" → "why not reportable", H1b row rewritten.
23. Status header (C8): the universal traceability promise now declares the 9.991 of §4.7.
24. §4.6 (C9): M10 row "without both partials" → "without `09-03` and `09-20`"; the
    all-partials leg is declared not computed for M10 (working list 13).
25. Appendix B (C10): "3 592 verdicts" → 3 592 rows = 3 585 verdicts + 7 superseded xAI
    non-verdicts.
26. §4.0.1b and Appendix B (C11): "all 20 epochs" → "all 19 served epochs" (11 positive + 8
    negative dual, `CONTROLES-JANELA-COMPLETA-2026-09-21.json`).
27. §4.3 (C12): "≈ 5×10⁻⁶ in all four arm-by-leg cells" → "≤ 5.8×10⁻⁶ in all six (five
    distinct)", recomputed on both ITT artifacts.
28. Abstract (C13): H1c "on both the locked and the sensitivity leg" → "on all three legs".
29. §9 and §1.1 (C14): "we knew this ten days before" → "this was projection-robust ten
    days before"; the §1.1 caveat now refers to the earlier wording.
30. §4 structure (C15, assembly report): bold "(a)" and "(b)" became headings §4.0.1a and
    §4.0.1b; §4.0.2 moved after §4.0.1c; the bootstrap-layers section moved after §4.1.1
    and renumbered §4.4.1 → §4.1.2. Order is now 4.0.1 (a, b, c), 4.0.2, 4.1, 4.1.1, 4.1.2,
    4.2–4.7. Cross-references to §4.4.1 updated (§4.1.1 table, Figure B1 caption, working
    list 5); every other §4 reference already pointed at an unchanged number.
31. Working list 8 (C16): "Blocked by 1, 2 and 3" → "Blocked by 9 and 10". Working list 5
    (C17): "parecer" → "review".
32. §1.1 (C18): the two pieces of evidence speak to our practice, not to the ordering of the
    2026-09-21 decisions, which rests on commit timestamps alone.
33. Assembly report, terms: "designated chunks" → "designated items" throughout (15 places,
    including "non-designated"), matching Paper A; "lands on the floor or ceiling of its
    exact share" → "receives its exact share rounded down or up"; "our own 3 600 s ceiling"
    → "our own 3 600 s time limit". The technical "exposure ceiling" (§1) and the
    eligibility "floor predicates" (§4.0.1b) are unchanged.
34. Version label: v2 throughout, with rc2 named in the status header; working list items 12
    (struck) and 13 (open) added; B.1 row for the §4.1.1 standard errors added.

**rc3: adversarial review of rc2 and the sham result** (sources:
`_sprint-2026-10-04/REVIEW-B-rc2-2026-10-04.md`, one valid voice of four, 22 confirmed
findings C1–C22 with numbers recomputed in `REVIEW-B-rc2-evidence/`;
`_sprint-2026-10-04/B-sham-v2/REPORT.md` §7 and `B-sham-v2/job-v2b/RESUMO.json`; per-finding
record in `_sprint-2026-10-04/APPLY-B-rc3.md`). The title is unchanged.

35. Abstract, §1 table, §4.1 heading, §4.4, §9 (C1): "could not have found otherwise",
    "undetectable by construction" and "no possible result" → not detectable at 80% power
    at the N the calculation counted.
36. Abstract, §1.1, §4.1.1, §8.4, §9 (C2): the saturation is stated for the 19 clusters the
    calculation counted (11 treatment, 8 control). §4.1.1 reports the recomputation at the
    ITT's 20: whole-epoch 11T/9C detectable at 80% (effective size 96.41 against 95.26),
    fractional with `09-02` not (91.49, margin 4.1%). Working list 13, first half, closed.
37. Abstract (C3): the contradiction is stated through the implied standard errors
    (≥ 0.0279 against 0.0165), not through the interval excluding total elimination.
38. Abstract, §4.0.2, §4.3 (C4): "the 955% effect it would imply" → the observed reduction
    (70.7%; 47.1% without `09-14`) would require 22.5 times total elimination in the 3.14%
    of altered briefs (at least 6.9 times at 6.85%). 955% kept where it is the 2026-08-30
    demotion reason (abstract, §4.3, §9).
39. §4.0.2 (C5): the registered test no longer "shows" the H1a bootstrap interval was the
    artifact; the disagreement is consistent with under-coverage and does not demonstrate it.
40. Abstract, §4.1.1, §4.1.2, §9 (C6): the null is the non-rejection by the registered
    test (`p = 0.1603`), not the point estimate (a 22% relative reduction).
41. §4.1.1 table, §4.1.2, abstract (C7): under-coverage cited as expected from the
    literature, not measured; the frozen stratum-B sample "may be under-represented" in the
    intervals that use it (not M10); the direction of the systematic-sample error is not
    known.
42. Abstract, §3.0 (C8): the analysis specification is dated by our commit log and was not
    deposited with the registration (deposited version v1.12).
43. §3.0.1 (C9): "could have an effect" → "the dose could reach a designated item".
44. §7 (C10): new threat, post-randomization denominator (opportunities per epoch 100.3
    treatment, 132.3 control).
45. §6 item 3 (C11): zero reversals to the opposite strict majority; ties change the label,
    and those are the 28 losses of item 6.
46. §4 and §7 (C12): the tie rule biases toward fewer failures; its effect on the contrast
    is not counted. §7 paragraph retitled "Tie rule".
47. §2 and §6 item 5 (C13): "12 pp disagreement" → an 11.9 pp difference in marginal
    failure rates, a lower bound on paired disagreement.
48. §4.6 (C14): `09-20` coverage is low because 287 of its 672 briefs were served after
    expiry (0 covered); before expiry 98 of 385 (25.5%). B.1 row added.
49. §4.7 and Figure B2 caption (C15): "cannot bias" → "does not measurably bias"; the
    truncation shift is not distinguishable from zero (1% of the deficit, MC s.e. 1.5%).
50. §4.0.1b (C16): `1/21` is a rank p-value, a randomization p-value only to the extent the
    shams are drawn by the real designation's mechanism (one per signature group), which
    neither sham generator does.
51. §5 (C17): the per-dose and leave-one-agent-out cells → "not computed in this version".
52. §5 (C18): H1b excepted from "listed in §8 of the analysis spec before the window
    closed".
53. §4 (C19): condition (i) defined in place (PREREG §4.1; the review's fix said §3, where
    the `Opportunity` lock lives; the repeated-failure definition is in §4.1).
54. §1.1 (C20): "every estimate" excepts the 9.991 of §4.7 and is conditioned on the deposit.
55. §4.3 (C21): the H1a criterion restated as "excludes zero only on the locked leg, on a
    denominator dominated by one sparse session".
56. §3.0 heading, §4.0.1b heading, working-list caveat (C22): headings no longer say the
    feasibility question is unanswered or that a control is not runnable.
57. Sham integration: STATUS block; abstract (one sentence on the controls); §4.0.1b table
    row, heading and the eligible-pool bullet; §4.0.1c heading, the "what a valid sham
    needs" paragraph, the measured/not-measured table (110/110 and 2,646/2,646 now
    measured), a new result table with its four declared limits, the claims paragraph and
    the artifact list; §7 (new "scope of the specificity control"); §8.3 (two places); §8.5;
    Appendix B and B.1 rows; working list 3, 8, 9 and the caveat. Result: real 132 states
    moved and churn 146 against 81–122 and 84–132 for 20 shams, `p = 1/21 = 0.0476` on both;
    positive control 155 at `w = 100 000`; real run equal to calibration and to production
    in 2,646/2,646 states.
58. Working list: item 14 added (this review, struck). Status header: rc3.

**rc4: author decisions of 2026-10-05 and the tie census** (sources: the author's decisions on
the title, the power statement, the sham scope and C12; `B-sham-v2/JANELA-LANCAMENTO.md`;
`out/C12-EMPATES-POR-BRACO-2026-10-05.json`; per-change record in
`_sprint-2026-10-04/APPLY-B-rc4.md`).

59. Title: *"Under-powered by construction: intention-to-treat results from a pre-registered
    interventional trial of agent-memory dosing"* → *"A registration that outlived its
    intervention: a pre-registered randomized trial of memory dosing in a production agent
    fleet"*. The thesis sentences follow it: abstract (two places), §1.1 ("the core
    claim"), §7 (power), §9 (opening). The under-powering is still reported, as a
    consequence of the registration outliving the intervention.
60. Abstract, §1 table, §1.1, §4.1.1, §8.4, §9 (decision on C2): the spec's fractional
    counting governs the power statement (effective size 84.8 over the 19 served epochs,
    91.49 at the ITT's 20 with `09-02` as a full control epoch, against 95.26: not
    detectable). Whole-epoch counting is a sensitivity: it agrees at 11 treatment and 8
    control (90.2) and flips at 11 treatment and 9 control (96.41 > 95.26). §4.1.1 adds that
    §7 of the spec forbids rounding partial epochs and that the spec computed the
    9-control case itself (96.4) and set it aside.
61. §1.1 caveat and §9: "projection-robust" holds only under the spec's cuts; it fails at
    11 treatment and 9 control under whole-epoch counting.
62. §1.1, first list: the designation's expiry (§3.0.1) added as outcome-independent
    evidence, with its artifact.
63. STATUS block and §4.0.1c (first declared limit): a sham replay over the whole trial
    window (11,812 reconstructible states of 18 epochs; without `09-01`, whose corpus has no
    hash proof, and without 53 states whose serve-state cut cannot be reconstructed) is
    running; its result will be added before deposit. Working list: item 9 updated, new
    item 15, item 8 blocked by 10 and 15. The rc3 result (`w = 4`, `p = 1/21`) is unchanged.
64. §4 and §7 (C12): the exact ties of the four-vote set counted per arm: 28 in all, 10 in
    treatment epochs, 11 in control, 7 outside the window; 4 and 7 are H1c opportunities,
    none of them a failure under the three-family majority, so the tie rule removes no
    repeated failure from either arm and leaves condition (i) unchanged.
65. §6 item 3 (found while counting C12): "Ties do change the final label … those are the 28
    losses of item 6" struck. Only 3 of the 28 ties change the label; 25 were already
    `not_failure` under the three-family majority. §6 item 6 now defines gains (20: brought
    to three substantive verdicts) and losses (28: brought to an exact tie).
66. Appendix B: † row for `out/C12-EMPATES-POR-BRACO-2026-10-05.json` and its script. B.1:
    rows for the tie counts, the fractional effective size (84.8) and the spec's 96.4, and
    the whole-window sham launch.
67. §4 and §7 (independent check of rc4, D-B1): "counted in rc4 it is nil for H1c" struck.
    The tie rule changes no H1c label relative to the three-family majority, but against the
    opposite resolution it holds 4 treatment and 7 control tied opportunities (HT weights
    27.78 and 36.73) at `not_failure`. Measured with the C12 script and the imported rule
    (`out/C12-EMPATES-COMO-FAILURE-2026-10-05.json`): with every tie resolved as `failure`
    the four-vote H1c point difference goes from −0.0208 to −0.0266; opportunities do not
    change, and the first-order value is ~~the same~~ equal to it only at four decimals
    (corrected in rc5, item 73). Appendix B † row and B.1 row added.
68. STATUS block, §4.0.1c, working list items 9 and 15, B.1 (D-B2): the whole-window sham
    is `job-janela2`, 11,812 states (11,865 − 53), relaunched 2026-10-05T09:39:53Z, expected
    to finish about 2026-10-07T03:00Z. Item 9's "11,865 states … about 36 h" struck; in
    §4.0.1c the 11,865 / 36 h stays as the estimate that motivated the `w = 4` set.

**rc5: regression review of rc4** (source: one Codex review of rc4, five findings, all
confirmed against the code and artifacts; per-change record in
`_sprint-2026-10-04/APPLY-B-rc5.md`).

69. Abstract (two places), §4.0.2, §4.3 (H1): "would require more than 100% in the 3.14%
    of briefs the dose alters" and "a reduction above 100% is impossible, so an interval
    excluding zero there cannot be read as the treatment working" replaced. The 22.5 / 15.0
    and 10.3 / 6.9 ratios are now stated as proportional-dilution calculations, not causal
    bounds: the altered share of briefs need not equal the share of failures they carry,
    and an effect can travel through activity volume (§4.3, reading 1) or state (§8.3).
    `H1` remains an unexplained rejection.
70. §4 (combined estimator): condition (i) is now described as implemented. The estimator
    requires a same-signature failure (severity ≥ τ) whose epoch begins at least one epoch
    length earlier; it does not check membership in the serving snapshot that PREREG §4.1
    names, and `pilot_replay.py` declares the reconstruction an approximation.
71. Abstract, §4.0.1c, §7 (sham): the specificity claim is limited to the 20 tested shams
    ("any designation of the same severity and bonus mass" struck in substance), and the
    rank p-value is stated not to be a calibrated randomization p-value, because the shams
    are matched on severity and bonus mass but not drawn by the designation's
    one-per-signature-group rule. The numbers and the term "rank p-value" are unchanged.
72. §4.1.1, §9, B.1 (power): "under-powered for any smaller effect" and "anything less stays
    out of reach" replaced: under whole-epoch counting at 11 treatment and 9 control, 80%
    power holds only for reductions of about 99.6% or more (relative MDE 0.996).
73. §4, B.1 (C12): the rerun with ties as `failure` gives −0.026571 and the first-order
    calculation −0.026566; both are now stated, and item 67 is corrected.
74. Working list: item 16 added (this review, struck). Status header: rc5.

**rc6: ballast gap closed, and a writing pass** (sources: `_sprint-2026-10-04/LASTRO-B-item10.md`
and the `avoid-ai-writing` pass; per-change record in `_sprint-2026-10-04/APPLY-B-rc6.md`).

75. Appendix B: † caveat dropped; the manifest now covers every row of the table, 50
    artifacts (working list 10; `LASTRO-B-item10.md`).
76. Working list 10 struck as done, item 8 no longer blocked by it, item 1's caveat closed;
    the Appendix B caveat now counts 50 artifacts, 158 MiB, 16 copied and verified at the
    destination and 34 versioned.
77. The passages that depend on the whole-window sham (`job-janela2`) are wrapped in
    `<!-- SHAM-JANELA -->` comments with their wording unchanged; the list is in
    `APPLY-B-rc6.md`.
78. Writing pass over the rest of the text (em dashes, bold, contrast pivots, closing
    aphorisms). No number, unit, reference, identifier, path, quote or claim changed.
    Status header: rc6.

**rc7: review of rc6** (sources: `_sprint-2026-10-04/REVIEW-B-rc6-2026-10-05.md`, a Codex and
a Fable full read, both NO-GO, with the author's two decisions of 2026-10-05; numbers
added here are recomputed in `_sprint-2026-10-04/B-rc7/checks-rc7.json`; per-finding record,
with what was verified and the list of `REANALISE` blocks, in
`_sprint-2026-10-04/APPLY-B-rc7.md`). Every number and sentence that the registered
re-analysis will replace is wrapped in a `REANALISE` comment and still carries the rc6
value (working list 18).

79. Abstract, §1 (table and a new paragraph), §4.0.2 table, §4.3, §8.2 table, §9, Appendix A
    (Fable HIGH-1; author decision): the deposited primary is H1, with H1a–H1c as a
    Holm-corrected co-primary family; H1c is reported as primary under the undeposited
    revision of 2026-08-30 (`DESIGN-REVISION-2026-08-30.md` §3-ter, commit 16:51:56Z;
    `PROSPECTIVE-ESTIMAND-2026-08-30.md` §3-bis, commit 20:51:20Z), before the assignment
    seed. The result under the deposited primary is stated beside it (H1 rejects), and the
    Holm statement is added.
80. §5, §1, Appendix A (Fable HIGH-2): rows for H2 (task regret) and H3 (retrieval metrics),
    with their reason pending the re-analysis; the row "dose-response / H3" renamed to the
    registration's dose-response reading rule; the closing paragraph no longer says every
    row was listed in the spec before the close.
81. §4.5 (heading and text), §1.1, §9 (Codex 1): the flat ≈5.3% counts designated-chunk
    serving occurrences, the 93.8% counted covered action opportunities (573 / 611); the
    measurement does not test the projection, and the pre-committed indistinction stands
    (now also in the abstract, as the pre-commitment required). The third observation of §9
    is replaced.
82. Abstract, §4.1.1 (heading, text and table), B.1 (Codex 4): the comparison of implied
    standard errors is struck; the two statements use different variance constructions,
    and their difference is not a contradiction.
83. Abstract, §4.0.1b, §4.0.2, §4.3, §4.5, B.1 (Codex 5, Fable MEDIUM-7 and LOW-10): 3.14% is
    named the pre-trial calibration share (11 of 350 at `w = 2`); the realized share is
    335 of 7 350 briefs served in active mode (4.56%), the denominator chosen because the
    artifact's 337 of 7 392 includes two shadow-mode counterfactual changes on `09-01`;
    ratios at the realized share 15.5 and 10.3; coverage over active briefs 2 057 / 7 350.
84. Abstract, §1 table, §4.1.1, §7, §9 (Codex 6): the power statement covers reductions
    only; an increase can reach 80%.
85. Abstract, §4.1.1, Figure B1 caption, §4.1.2, §4.3, §8.3 (Codex 7): intervals *may*
    under-cover; the few-cluster literature is cited for caution, not as calibration.
86. §1, §1.1 (Codex 8, Fable MEDIUM-3): the 1 056 s belong to designation round 31657512;
    the assignment round 31774052 has its own precedence (21:18:35Z against 21:32:04Z).
87. §8.2 (Codex 9): CMP's Theorem 1 is stated for a memory with zero retrieval probability.
88. §8.4 (Codex 10): the NHLBI comparison is observational.
89. Abstract (Codex 11): the "evidence of nothing" sentence replaced.
90. §1.1, §7, working list 17 (Fable MEDIUM-6): `ITT-PRELIMINAR.json` (file time 16:16:44
    local) precedes the §10.33 decision (16:20), so the claim that no number existed at
    either decision is withdrawn for §10.33.
91. §4, B.1 (Fable LOW-8): the sixth-decimal difference between rerun and first-order value
    is the rounding of a stored per-arm proportion (0.09189), not feedback of condition (i);
    item 73 is left as written and corrected by this item.
92. §9 (Fable LOW-9 and LOW-11): "the only significance" → the only rejection by the
    registered test; "three weeks apart" → eighteen days apart.
93. §4.1.1 (Fable LOW-12): `09-01` enters the fractional counts by brief share (0.9375), not
    by clock (0.9325); the difference moves 84.80 to 84.78.
94. §3, §3.0.1, §4, §6 item 7, Appendix A (Codex 2 and 3, Fable MEDIUM-4 and MEDIUM-5):
    declared, not yet resolved: the panel substitution was not applied (1 159 of 1 195
    adjudicated, 36 `unknown`), the window is selected by epoch date with no cut at expiry,
    the bootstrap is percentile instead of BCa, and `09-02` is included against the spec.
    All are marked `REANALISE`.
95. Sweep of the classes the review named, outside the `SHAM-JANELA` blocks: §4.0.2 (the
    disagreement can also come from the estimands), §4.7 ("false" → not supported by the
    measurement), §8.5 (wording of the contradictions).
96. Working list: item 8 also blocked by 17 and 18; items 17 and 18 added; item 19 (this
    review, struck). Status header: rc7.

**rc8: the registered analysis reported, and two findings of ours** (sources:
`out/ITT-REGISTRADO-2026-10-05.json` and `_sprint-2026-10-04/B-registered/RESULTADO.md`;
`_sprint-2026-10-04/B-rc8/checks-rc8.json`; the author's decision of 2026-10-05 that the
registered analysis is the reported one and the analysis of rc7 a sensitivity; per-block
record in `_sprint-2026-10-04/APPLY-B-rc8.md`). No `REANALISE` marker remains.

97. Abstract, §1, §3, §3.0.1, §4–§4.3, §6 item 7, §7, §8.3, §8.4, §9, Appendix A, B.1: every
    `REANALISE` block of rc7 (85 values, 23 sentences) replaced by the registered analysis,
    with the rc7 value kept as the sensitivity where the sentence reports both. H1 rejects
    in both (0.0133; 0.0127); H1c does not reject in either (−0.0121 [−0.0445; +0.0125],
    0.434; 0.1603); H1a's unadjusted p is 0.0241 and it is not rejected under the
    registered Holm rule (adjusted 0.1205 with m = 5, 0.0964 with m = 4).
98. §4: what moves each number (`09-02`'s exclusion moves H1c most; the offsets move H1a;
    the expiry cut is negligible; the panel goes from 1 159 to 1 179 adjudicated; BCa
    changes only intervals), and the estimator's byte-for-byte control.
99. §4.0.2 (heading and table) and §4.2 (heading, table, take-away and Figure B1): under
    the registered BCa interval H1a excludes zero on the locked and pre-committed legs and
    contains zero only without `09-14`; "only on the locked leg" is struck as a statement
    about the sensitivity analysis. §4.1 notes that the direction of the pre-committed
    against the post-hoc leg reverses for H1a.
100. §4.1 and §4.2 tables: the registered analysis on the pre-committed and post-hoc legs
    (`checks-rc8.json` block A), with the sensitivity analysis's three legs beside it.
101. §4.1.1, abstract, §1.1, §7, §8.4, §9: at the registered 19 epochs both countings give
    the same power verdict; the whole-epoch flip belongs to the sensitivity analysis's 20.
102. §5: H2 computed and reported (three declared choices; neither component rejects); H3
    declared not computable; a row for the secondary model and co-estimates of PREREG §5,
    not computed.
103. §4, §7, B.1: the four-vote ties recounted under the registered window and set
    (`out/C12-EMPATES-REGISTRADO-2026-10-05.json`); the tie rule cannot bind in the
    substitution panel (0 ties).
104. §3.0 (struck sentence and a new correction), abstract, §1.1, §7, §9, Appendix A, §8.2:
    the stopping rule of `PROSPECTIVE-ESTIMAND-2026-08-30.md` §3-bis was met in Epoch 1
    (32.4%, 45 of 139, against 36.7%) and not executed (`checks-rc8.json` block D).
105. §1 (new paragraph), abstract, §1.1, §7, §9, Appendix A, §8.2: the assignment rule
    declared in `ASSIGN-SEED-2026-08-30.md` is not `assign_arms.py`; it was replaced 24 min
    38 s after the round was emitted, and the two differ on 11 of the 20 realized epochs
    (`checks-rc8.json` block E).
106. Figure B1 regenerated from the registered artifact
    (`measurement/sprint-figB-h1a-inversao-registrado.py`, new output files; the earlier
    figure is kept as the record of the sensitivity analysis).
107. Appendix B and B.1: the registered artifact, `checks-rc7.*`, `checks-rc8.*`, the
    registered C12 file and the registered figure listed, each marked as not yet in
    the ballast manifest. Working list: 8 and 17 extended, 11 annotated, 18 struck, 20
    added. Status header: rc8.
