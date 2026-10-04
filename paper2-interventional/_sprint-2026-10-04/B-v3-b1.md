# Under-powered by construction: intention-to-treat results from a pre-registered interventional trial of agent-memory dosing

> **STATUS: DRAFT opened 2026-09-21; v2 prepared 2026-10-04.** Every number below is
> measured and traceable to an artifact, and §B names the artifact for each. What is *not*
> done: ~~figures, related work, and deposit~~ → as of v2, figures (B1, B2) and related work
> (§8) are in; still not done: **the valid sham replay** (§4.0.1c) and **deposit**. The v2
> changes are listed in the changelog at the end.
>
> **Caveat.** **Two different adversarial reviews, and the distinction matters.** The numbers in §6
> were reviewed adversarially before this manuscript existed; that is how six of those
> seven defects were found. **This manuscript** is under review as of 2026-09-21 by five
> model families; §4.3, §4.4 and §3 already carry corrections it produced. The working list is at the end, and the rule of this project
> applies to it: **an item is struck in the same commit that closes it.**
>
> This is **Paper B** of the split decided on 2026-08-28 (`PAPER-SPLIT-2026-08-28.md`).
> Paper A (`MANUSCRIPT.md`, *"Spare capacity, narrow surface"*) reports the surface
> measurements and does **not** depend on this trial having run. This paper reports the
> trial that the public pre-registration covers, and nothing else.

---

## Abstract

We report a pre-registered, fleet-wide interventional trial of dose-weighted memory
promotion in a production agent-memory system. Epochs of 24 h were randomized to control
or to one of three dose levels by constrained randomization seeded from a public drand
beacon, with the assignment script and its hash registered before the seed was drawn
(OSF `yf7d2`, 2026-08-18T07:56:44Z; Zenodo `10.5281/zenodo.22110203`).

The registered design called for 234 epochs. **Twenty were realized**, of which nineteen
served data.

**Critical.** **The trial did not stop early: 234 was infeasible from the start.** All 19 designated
chunks share one `created_at` and sit in a sub-pool with a 30-day window, so they leave
eligibility together at 2026-09-20 22:51:23 (**20 of the 234 registered epochs, 8.5%**).
Past that instant no value of the dose reaches them, because the boost is addressed by id
and they are no longer in the candidate list; treatment and control would have been the
same intervention for 214 epochs. The under-powering of this study is therefore a property
of **the registration**, not of the realized window: `sizing.py` sized for 234 epochs on an
intervention that existed for 20.

**The primary outcome is null and the study could not have found otherwise.** This is a claim
about **H1c**, the primary, and not about every quantity the trial produced. Two secondary
quantities *do* return intervals excluding zero, and §4.3 argues they are properties of a
shared denominator rather than of the treatment; a reader who rejects that argument should
read them as unexplained. The
pre-registered analysis specification, written on 2026-09-10 (ten days before the window
closed and before any outcome was computed), recorded that the minimum detectable effect
for H1c was **saturated at 100%** at the realized N, i.e. no effect size within the
parameter space was detectable. The realized estimate is **−0.0199** (treatment 0.0696,
control 0.0896; 95% CI [−0.0560; +0.0086], cluster bootstrap with the epoch as unit),
containing zero on both the locked and the sensitivity leg.

**Critical.** **And our two estimates of uncertainty contradict each other.** The pre-committed power
statement says not even total elimination of repeated failures is detectable here; the
observed 95% interval *excludes* total elimination. Both are ours. The interval is too
narrow (percentile bootstrap at ~10 clusters under-covers, and it never resamples the
stratum-B draw), and the power figure rests on an ICC estimated for a different quantity.
We report both and adjudicate neither: **this study does not have a trustworthy measure of
its own uncertainty**, and the null rests on the point estimate and the design rather than
on the interval.

**Absence of significance is not evidence of absence of effect**, and at this N it is not
evidence of anything at all. We report the trial in full regardless, because the parts
that do carry information are not the effect estimate: a hypothesis that was demoted from
primary for requiring a 955% effect nonetheless returns an interval excluding zero, which
is a measurement of the *denominator*, not of the treatment; a second hypothesis
~~inverts its conclusion on the removal of a **single** epoch whose exposure comes from one
session with three episodes~~ excludes zero **only on the locked leg**: its pre-committed
sensitivity leg contains zero, and so does a post-hoc leg that removes a single epoch whose
exposure comes from one session with three episodes *(corrected 2026-10-04: the first
version reported only the post-hoc leg; §4.2)*; and the member of the hypothesis family
that carried the substantive mechanism question collapses to **1.0 by construction**, because two locks of our own
pre-registration define its estimand incompatibly and neither of us noticed until the
window had closed.

We take the position that these are the reportable results of an under-powered trial, and
that publishing them is the alternative to the two things a null of this shape is usually
used for: silence, or a claim.

---

## 1. What was registered, and what this paper reports

The pre-registration (OSF `yf7d2`, Zenodo `10.5281/zenodo.22110203`, v1.12) specifies a
fleet-wide trial in which epochs (24-hour periods with a 09:00 UTC boundary) are
assigned to control or to a dose `w ∈ {2.0, 4.0, 7.5}` that scales the promotion weight of
a fixed set of designated memory chunks. The designation is a fixed, publicly re-derivable
set of 19 chunks, one per signature group (`DESIGNATION-2026-08-26.json`), closed on
2026-08-26 at 20:28Z with verifiable precedence of 1 056 s over the drand round that seeds
the assignment.

The registered hypothesis family is nested (`H1c ⊆ H1b ⊆ H1a`), and §1 of the
pre-registration calls that nesting *"the nesting that makes the joint reporting work"*:

| | statement | status here |
|---|---|---|
| `H1` | density of repeated failures per session-hour | **computable**; demoted from primary 2026-08-30 |
| `H1a` | rate of eligible opportunities per session-hour | **computable**; does not bear weight (§4.2) |
| `H1b` | share of opportunities yielding a repeat attempt | **trivially 1.0**; the question it carried is unanswerable (§4.4) |
| `H1c` | share of opportunities yielding a repeated *failure* | **primary**; null, and undetectable by construction |

This paper reports the intention-to-treat analysis of that family and nothing else. The
surface measurements made *while* the trial was being built (the exposure ceiling, the
carousel, the coverage channel) are Paper A, are explicitly **exploratory and
descriptive**, and were never pre-registered.

### 1.1 The order in which decisions were taken, and why it is stated first

Two estimand decisions had to be made after the window closed and before any estimate
existed (§4.4 and §4.2). Both were taken on 2026-09-21 and **recorded before the family
was computed**: the timestamps are in `DEVIATIONS-FOR-PAPER.md` §10.32 (16:14) and §10.33
(16:20), and no number of the H1 family had been produced at either point.

We state this first because it is the claim in this paper most dependent on our own
bookkeeping, and §9 of the analysis specification exists precisely to forbid the opposite
order: *"choosing the primary set after seeing the number is the post-hoc play that this
spec exists to prevent."*

**Critical.** **And the evidence for it is weaker than the evidence for everything else, by a gap we
created ourselves.** We anchored the *assignment* in a public drand beacon precisely so
that no one would have to trust us about it, and then anchored the decision log in
nothing but our own commit timestamps, which are forgeable in seconds. Append-only is
process discipline, not a cryptographic property. An adversarial reviewer put it as an
asymmetry, and the asymmetry is real: we knew how to do this and did it for the easier
claim.

**What a reader can check without trusting us at all:**

- the MDE saturation of §4.1 is arithmetic over the realized N, the pre-registered ICC and
  `p̂0`: outcome-independent, and reproducible from the artifacts;
- the assignment, from drand round 31774052 through `assign_arms.py` to the served arms;
- every estimate, from the artifacts of Appendix B.

**What requires trusting us:** the two estimand decisions of §4.2 and §4.4 preceded the
estimates. Two things make that more credible than a bare timestamp, and neither is proof:
the spec omits `09-10` and marks nine epochs as projection, which a fabricator writing
after the close would have had no reason to do; and the spec contains a commitment the
data later **refuted** (§4.5). Writing a commitment your data go on to contradict is not
how a post-hoc account is built.

The core claim (under-powered by construction) sits entirely in the first list. A reader
who disbelieves the second list loses §4.2 and §4.4 and keeps the paper.

**Caveat.** One phrase in §9 overstates even so: *"we knew this ten days before the window
closed."* On 2026-09-10 nine of the epochs were still projection. The spec's own extremes
analysis covers that (the bounding cases still return not-detectable), so the conclusion
holds, but it was **projection-robust**, not known.

---

## 2. Design

**Randomization.** Stratified block randomization over four strata,
`(first calendar half | second half) × (weekday | weekend)`, with group counts allocated
by exact two-way controlled rounding and labels shuffled by a seeded Fisher-Yates. The
entropy stream is counter-mode SHA-256 rather than any language's PRNG, so that
*"re-run the committed script"* means re-run it in any language. Seed:
`SHA256(randomness_hex)` of drand round **31774052**, hashed as lowercase ASCII text.
Allocation at N = 234: 117 control, 39 per dose.

The registered tolerance (every group × stratum cell lands on the floor or ceiling of its
exact share) holds **by construction** rather than by rejection sampling, so there is no
acceptance rate and no failure mode in which the sampler quietly relaxes a constraint.
Realized maximum deviation: **0.5** against a tolerance of 1.0.

**Washout.** Two hours from the epoch boundary; episodes inside it are excluded from the
analysis.

**Severity threshold.** `τ = S1`, locked in July 2026 on a calibration over **five**
model families (PREREG §697-699).

**Caveat.** **We do not claim the outcome data "confirm" τ.** A parameter locked in July is not
re-validated with data from the outcome period; that is post-hoc, and an earlier draft of
our own deviation log made exactly that claim before adversarial review removed it
(§10.31(5)). What the outcome data do show, and what we report instead, is a **12 pp
disagreement at the S0/S1 boundary** (the boundary τ does *not* absorb) between two
panel families (`google` 42.3% failure against `zhipu` 30.4%).

---

