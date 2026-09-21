# Under-powered by construction: intention-to-treat results from a pre-registered interventional trial of agent-memory dosing

> **STATUS — DRAFT opened 2026-09-21.** Every number below is measured and traceable to
> an artifact, and §B names the artifact for each. What is *not* done: figures, related
> work, and deposit.
>
> ⚠️ **Two different adversarial reviews, and the distinction matters.** The numbers in §6
> were reviewed adversarially before this manuscript existed — that is how six of those
> seven defects were found. **This manuscript** is under review as of 2026-09-21 by five
> model families; §4.3, §4.4 and §3 already carry corrections it produced. The working list is at the end, and the rule of this project
> applies to it — **an item is struck in the same commit that closes it.**
>
> This is **Paper B** of the split decided on 2026-08-28 (`PAPER-SPLIT-2026-08-28.md`).
> Paper A — `MANUSCRIPT.md`, *"Spare capacity, narrow surface"* — reports the surface
> measurements and does **not** depend on this trial having run. This paper reports the
> trial that the public pre-registration covers, and nothing else.

---

## Abstract

We report a pre-registered, fleet-wide interventional trial of dose-weighted memory
promotion in a production agent-memory system. Epochs of 24 h were randomized to control
or to one of three dose levels by constrained randomization seeded from a public drand
beacon, with the assignment script and its hash registered before the seed was drawn
(OSF `yf7d2`, 2026-08-18T07:56:44Z; Zenodo `10.5281/zenodo.22110203`).

The registered design called for 234 epochs. **Twenty were realized** before the trial was
closed on 2026-09-20, of which nineteen served data.

**The primary outcome is null and the study could not have found otherwise** — a claim
about **H1c**, the primary, and not about every quantity the trial produced. Two secondary
quantities *do* return intervals excluding zero, and §4.3 argues they are properties of a
shared denominator rather than of the treatment; a reader who rejects that argument should
read them as unexplained. The
pre-registered analysis specification, written on 2026-09-10 — ten days before the window
closed and before any outcome was computed — recorded that the minimum detectable effect
for H1c was **saturated at 100%** at the realized N, i.e. no effect size within the
parameter space was detectable. The realized estimate is **−0.0199** (treatment 0.0696,
control 0.0896; 95% CI [−0.0560; +0.0086], cluster bootstrap with the epoch as unit),
containing zero on both the locked and the sensitivity leg.

🔴 **And our two estimates of uncertainty contradict each other.** The pre-committed power
statement says not even total elimination of repeated failures is detectable here; the
observed 95% interval *excludes* total elimination. Both are ours. The interval is too
narrow — percentile bootstrap at ~10 clusters under-covers, and it never resamples the
stratum-B draw — and the power figure rests on an ICC estimated for a different quantity.
We report both and adjudicate neither: **this study does not have a trustworthy measure of
its own uncertainty**, and the null rests on the point estimate and the design rather than
on the interval.

**Absence of significance is not evidence of absence of effect**, and at this N it is not
evidence of anything at all. We report the trial in full regardless, because the parts
that do carry information are not the effect estimate: a hypothesis that was demoted from
primary for requiring a 955% effect nonetheless returns an interval excluding zero — which
is a measurement of the *denominator*, not of the treatment; a second hypothesis inverts
its conclusion on the removal of a **single** epoch whose exposure comes from one session
with three episodes; and the member of the hypothesis family that carried the substantive
mechanism question collapses to **1.0 by construction**, because two locks of our own
pre-registration define its estimand incompatibly and neither of us noticed until the
window had closed.

We take the position that these are the reportable results of an under-powered trial, and
that publishing them is the alternative to the two things a null of this shape is usually
used for: silence, or a claim.

---

## 1. What was registered, and what this paper reports

The pre-registration (OSF `yf7d2`, Zenodo `10.5281/zenodo.22110203`, v1.12) specifies a
fleet-wide trial in which epochs — 24-hour periods with a 09:00 UTC boundary — are
assigned to control or to a dose `w ∈ {2.0, 4.0, 7.5}` that scales the promotion weight of
a fixed set of designated memory chunks. The designation is a fixed, publicly re-derivable
set of 19 chunks, one per signature group (`DESIGNATION-2026-08-26.json`), closed on
2026-08-26 at 20:28Z with verifiable precedence of 1 056 s over the drand round that seeds
the assignment.

The registered hypothesis family is nested — `H1c ⊆ H1b ⊆ H1a` — and §1 of the
pre-registration calls that nesting *"the nesting that makes the joint reporting work"*:

| | statement | status here |
|---|---|---|
| `H1` | density of repeated failures per session-hour | **computable**; demoted from primary 2026-08-30 |
| `H1a` | rate of eligible opportunities per session-hour | **computable**; does not bear weight (§4.2) |
| `H1b` | share of opportunities yielding a repeat attempt | **trivially 1.0**; the question it carried is unanswerable (§4.4) |
| `H1c` | share of opportunities yielding a repeated *failure* | **primary**; null, and undetectable by construction |

This paper reports the intention-to-treat analysis of that family and nothing else. The
surface measurements made *while* the trial was being built — the exposure ceiling, the
carousel, the coverage channel — are Paper A, are explicitly **exploratory and
descriptive**, and were never pre-registered.

### 1.1 The order in which decisions were taken, and why it is stated first

Two estimand decisions had to be made after the window closed and before any estimate
existed (§4.4 and §4.2). Both were taken on 2026-09-21 and **recorded before the family
was computed** — the timestamps are in `DEVIATIONS-FOR-PAPER.md` §10.32 (16:14) and §10.33
(16:20), and no number of the H1 family had been produced at either point.

We state this first because it is the claim in this paper most dependent on our own
bookkeeping, and §9 of the analysis specification exists precisely to forbid the opposite
order: *"choosing the primary set after seeing the number is the post-hoc play that this
spec exists to prevent."*

🔴 **And the evidence for it is weaker than the evidence for everything else, by a gap we
created ourselves.** We anchored the *assignment* in a public drand beacon precisely so
that no one would have to trust us about it — and then anchored the decision log in
nothing but our own commit timestamps, which are forgeable in seconds. Append-only is
process discipline, not a cryptographic property. An adversarial reviewer put it as an
asymmetry, and the asymmetry is real: we knew how to do this and did it for the easier
claim.

**What a reader can check without trusting us at all:**

- the MDE saturation of §4.1 is arithmetic over the realized N, the pre-registered ICC and
  `p̂0` — outcome-independent, and reproducible from the artifacts;
- the assignment, from drand round 31774052 through `assign_arms.py` to the served arms;
- every estimate, from the artifacts of Appendix B.

**What requires trusting us:** the two estimand decisions of §4.2 and §4.4 preceded the
estimates. Two things make that more credible than a bare timestamp, and neither is proof:
the spec omits `09-10` and marks nine epochs as projection, which a fabricator writing
after the close would have had no reason to do; and the spec contains a commitment the
data later **refuted** (§4.5). Writing a commitment your data go on to contradict is not
how a post-hoc account is built.

The core claim — under-powered by construction — sits entirely in the first list. A reader
who disbelieves the second list loses §4.2 and §4.4 and keeps the paper.

⚠️ One phrase in §8 overstates even so: *"we knew this ten days before the window
closed."* On 2026-09-10 nine of the epochs were still projection. The spec's own extremes
analysis covers that — the bounding cases still return not-detectable — so the conclusion
holds, but it was **projection-robust**, not known.

---

## 2. Design

**Randomization.** Stratified block randomization over four strata —
`(first calendar half | second half) × (weekday | weekend)` — with group counts allocated
by exact two-way controlled rounding and labels shuffled by a seeded Fisher-Yates. The
entropy stream is counter-mode SHA-256 rather than any language's PRNG, so that
*"re-run the committed script"* means re-run it in any language. Seed:
`SHA256(randomness_hex)` of drand round **31774052**, hashed as lowercase ASCII text.
Allocation at N = 234: 117 control, 39 per dose.

The registered tolerance — every group × stratum cell lands on the floor or ceiling of its
exact share — holds **by construction** rather than by rejection sampling, so there is no
acceptance rate and no failure mode in which the sampler quietly relaxes a constraint.
Realized maximum deviation: **0.5** against a tolerance of 1.0.

**Washout.** Two hours from the epoch boundary; episodes inside it are excluded from the
analysis.

**Severity threshold.** `τ = S1`, locked in July 2026 on a calibration over **five**
model families (PREREG §697-699).

⚠️ **We do not claim the outcome data "confirm" τ.** A parameter locked in July is not
re-validated with data from the outcome period; that is post-hoc, and an earlier draft of
our own deviation log made exactly that claim before adversarial review removed it
(§10.31(5)). What the outcome data do show, and what we report instead, is a **12 pp
disagreement at the S0/S1 boundary** — the boundary τ does *not* absorb — between two
panel families (`google` 42.3% failure against `zhipu` 30.4%).

---

## 3. Execution: the realized window is not the projected one

The trial went `active` on **2026-09-01 at 10:25:39Z** and the dose was switched off on
**2026-09-21 at 09:43:05Z**, closing the window at the `2026-09-20` epoch.

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

🔴 **Two different denominators, both correct, and we first wrote one number for both.**

| analysis | epochs | why |
|---|---:|---|
| **ITT (§4.1–4.4)** | **20** | every designated epoch. `09-02` served no brief but its sessions produced **88 episodes**; it was designated control, and dropping it would be post-randomization conditioning — the exact defect §3.1 records us committing once already |
| **coverage and M10 (§4.5–4.6)** | **19** | coverage is defined over served briefs, and `09-02` has none. The quantity does not exist there, which is not the same as being zero |

An earlier draft said "19 analyzable clusters" throughout. That is the coverage
denominator applied to the ITT, and it is the family of error this project catalogues as
*a correct number attributed to the wrong population*.

**`09-01` is reported with both phases declared**, as §6 item 6 of the analysis spec
requires: 42 briefs in `shadow` until 10:22Z and 630 in `active` from 10:37Z, with no
overlap. The sensitivity leg that removes it is reported alongside.

### 3.0 The stopping rule, and a feasibility question we cannot yet answer

The trial closed at the `2026-09-20` epoch by a decision taken on 2026-09-21, executed by
`desliga-dose-p2.sh` at 09:43:05Z. It was not a data-dependent stop: no outcome had been
computed, and the analysis specification that governs this report was written on
2026-09-10, eleven days earlier. It was a calendar decision, and saying so is the whole of
the stopping rule.

🔴 **What we cannot answer, raised by adversarial review and left open here.** The
designation was fixed on 2026-08-26, and the coverage channel's global sub-pool carries a
**30-day freshness window** (Paper A §4.3.1). If designated chunks age out of eligibility
on that clock, then a 234-epoch trial on a fixed designation was **never feasible**, and
the under-powering would not be a consequence of stopping early but of an internal
inconsistency in the registration itself — a larger specimen of this paper's own thesis
than the H1b collision. We have not measured it, we are not going to assert either way,
and it is on the working list. Should it prove true, §8 needs rewriting, not amending.

### 3.1 Two classification errors of ours, and what they cost

🔴 **We classified `09-20` with the wrong ruler.** We first published *16+3+1* as
*"17 whole + 2 partial + 1 empty"*, having measured **delivery volume** (672 of 672
serving records ⇒ "whole") where the pre-registered spec classifies by **clock exposure**
(13.86 h of 24 ⇒ partial, included with offset). The rulers are different and the
pre-registered one is not optional. The error propagated to six places including a pushed
commit, and was presented as *"matches the spec exactly"* when only the **total** matched
and the decomposition — which is what decides whether the epoch enters with an offset —
did not. Corrected in `DEVIATIONS-FOR-PAPER.md` §10.31(1).

🔴 **We derived the arm from the data instead of from the designation.** The first pass
took each epoch's arm as the mode of its observed `active` dose. That is
post-randomization conditioning: the mode is a function of *when* `active` took effect.
The arm is taken from `ASSIGNMENT-SERVING.json`. Confronted, the two agree on **0
divergences across 19 epochs** — but the premise changes, and it is the premise that goes
in a paper. This also voided a cross-validation we had claimed: comparing our own census
against the spec's table is not a second opinion, because both derive from the same
designation.

⚠️ The spec's own table **omits `09-10`**, summing to 19 against 20 allocated; it was
written on 2026-09-10 at 21:40 with that epoch still open. Including it gives 16 whole.
We record this rather than silently reconciling, because a spec that miscounts and an
analyst who miscounts are different failures with different fixes.

---

## 4. Results

**Estimator.** `estimador_itt.py`, which is **composition, not reimplementation**: it
imports `carregar_verdicts`, `carregar_episodios` and `span_por_sessao` from the pilot's
replay module and the arm from the assignment file. Two copies of one rule silently
populate different populations, and that is a defect class this project has already paid
for once.

**Adjudication.** 1 195 episodes — 395 stratum A (census of `is_error`) and 800 stratum B
(hash-ordered sample) — adjudicated by **three** model families from distinct training
lineages, as locked in PREREG §682. Coverage 100%. Horvitz-Thompson weight for stratum B:
**6.945** (5 556 / 800). Strict majority; a 2-2 tie resolves to `not_failure`, which
`pilot_replay.py` l.145-148 declares as *"conservative: it underestimates failures"* —
that is **directional bias toward the null**, not indeterminacy, and it is the direction
that makes a null easier to obtain.

**The combined estimator, written out** — the first draft omitted it, and without it a
reader cannot tell a ratio-of-totals from a mean-of-ratios. Per arm, over epochs in the
window and episodes past washout satisfying condition (i):

```
opportunities = Σ w(e)                 repeats = Σ w(e)·1[state = failure]
                                       w(e) = 1        if e ∈ stratum A (census)
H1c = repeats / opportunities          w(e) = 6.945    if e ∈ stratum B (sampled)
                                       e skipped       if in neither
```

`unknown` verdicts count in the denominator and not in the numerator, per §5 of the spec.
It is a **ratio of weighted totals**, not an average of per-epoch ratios.

**Uncertainty.** Cluster bootstrap with the **epoch** as the resampling unit, 10 000
replicates, seed `20260921` declared.

### 4.0.1 🔴 Two registered analyses we did not run, declared as deviations

Both were found by adversarial review of this manuscript, not by us.

**(a) The registered inference test is re-randomization, not bootstrap — and we have now
run it.** §4 of the analysis spec locks **10 000 re-randomizations**, *"redesign the 234,
never permute within the 20"*, over the trend-residualized outcome. The first draft
reported cluster bootstrap and **did not declare the substitution**. That was the worse
half of the error: the bootstrap assumes an iid draw of epochs, whereas the design
randomizes with stratification and exact controlled rounding, so its reference
distribution is **not the one the design generates**.

`rerandomizacao.py` imports `assign_arms.assign` and redesigns all 234 epochs per
replicate, restricting to the window — never permuting labels among the 20, which the spec
pre-commits against because the 20 fall entirely in the first calendar half, where the
stratification collapses. **Control: 300 distinct arm patterns in 300 replicates**, which
reproduces the spec's own measurement of zero collisions; at 10 000 it is 9 941 distinct.

### 4.0.2 🔴 The registered test disagrees with the bootstrap on H1a

| outcome | re-randomization *p* (registered) | reject sharp null at 5%? | what the bootstrap said |
|---|---:|---|---|
| **H1c** (primary) | **0.1603** | no | contains zero — **agree** |
| **H1a** | **0.0855** | **no** | excluded zero — 🔴 **disagree** |
| `H1` | **0.0127** | yes | excluded zero — agree |

⚠️ **Different estimand, stated so the numbers are not compared naively.** The permutation
statistic is a difference of arm means over per-epoch outcomes residualized on study-day;
the ITT of §4.1 is a ratio of weighted totals. They answer related questions, not the same
one, and the observed statistic here (−0.0323 for H1c) is **not** the −0.0199 of §4.1.
What transfers is the verdict, not the magnitude — and the registered scope is narrow by
construction: this tests the sharp null of *zero total effect*, and rejection alone does
not attribute magnitude.

**What this settles, and it is not in our favour rhetorically.** §4.2 argued that H1a
"does not bear weight" from the sparse-session mechanism. The registered test reaches the
same verdict by a route that does not need that argument at all — and in doing so shows
that the bootstrap interval which *excluded* zero for H1a was the artifact, exactly as
§4.1.1 predicts an under-covering interval would behave. We would rather have found this
before an adversarial reviewer told us the test was missing.

`H1` rejects under both. It remains excluded from interpretation for the reason of §4.3 —
the effect it would imply is outside what the mechanism can produce — and that reason is
now the *only* one standing, since the inference no longer supports dismissing it as a
bootstrap artifact. **We report it as an unexplained rejection**, which is the honest
category for a result that survives the registered test on a hypothesis whose magnitude
the design rules out.

Artifact: `RERANDOMIZACAO-2026-09-21.json`; seed prefix `p2-rerand-2026-09-21` declared.

**(b) The pre-committed instrument controls — two run, one not runnable.** §5 of the spec
defines three. The first draft reported none, which for a paper whose stated contribution
is *"the reportable results are about instruments"* was the worst omission in it.

⚠️ The spec measured the first two on **2026-09-10, with the trial still running** — 6/6
and 3/3 over a partial window. We re-measured over all 20 epochs, because a control
measured midway does not cover what came after.

**Semantics, declared before the numbers:** `mexeu` compares `ids_tratado` with
`ids_controle` by **membership** (`set`), never as a list. List comparison mixes reordering
with entry/exit and at epoch `09-08` returns 48 against 20.

| control | statement | result |
|---|---|---|
| **positive** | a served treatment epoch has `mexeu > 0` | ✅ **11 / 11** (was 6/6 at midpoint) |
| **negative dual** | a control epoch has `sem_ids == n` | ✅ **8 / 8** (was 3/3) |
| **specificity (sham)** | replay 19 non-designated chunks at the same `w` | ⏭ **not run** — see below |

The positive control ranges from **2.83% to 6.85%** of briefs altered per treatment epoch
(`09-09` lowest, `09-14` highest). Had any treatment epoch returned 0, **the null would be
the instrument's and not the effect's** — that is the whole purpose of the control, and it
is the reason the null of §4.1 can be read as being about the treatment at all.

The negative dual is stated that way for a reason the spec works out and we repeat: the
obvious form, *"a control epoch has `mexeu == 0`"*, is **invalid**, because at `w=0` the
`ids_*` fields do not exist at all — so `mexeu == 0` is indistinguishable from *"the field
was never written"*. A predicate that needs the data that is missing does not cover the
data being missing.

🔴 **The specificity control was not run, and our first attempt at it was invalid.** We
counted how many briefs contain a sham chunk in `ids_tratado` and compared against the
designated set. It returned real 2 069 against a sham median of 5 832 and read as a
**failed instrument**. The failure was the test's. `ids_tratado` is **post-dose**, so
counting presence inside it is the candidate the spec's own table already labels
*tautological*; with a universe of 141 ids, the non-designated set includes the chunks
that enter nearly every brief, while the designated are one per signature group and
therefore rarer. The quantity measured is **chunk frequency**, not specificity.

The pre-committed sham is a **replay**: re-execute the dose mechanism with 19
non-designated chunks at the same `w` and compare the churn it produces. That requires
running the serving code, not reading its log — the log only contains the outcome of the
designation that actually ran. It stays on the working list, **declared as not run rather
than reported as failed**, which is the difference between the two that this near-miss
exists to make.

Artifact: `CONTROLES-JANELA-COMPLETA-2026-09-21.json`.

### 4.4.1 What the bootstrap does not resample

There are **two** layers of randomness: the assignment of epochs to arms, and the
hash-ordered sampling of 800 episodes from 5 556 in stratum B. The cluster bootstrap
resamples the first with the second **frozen**. The component `E[Var_sampling(B) | epochs]`
is therefore absent from every interval in this paper, and it is not negligible: a single
sampled failure in B enters as **6.945** failures, which is unbiased in expectation and
heavy in the tail. The finite-population correction is ≈0.856, not zero.

We also treat a systematic (hash-ordered) sample as if it were simple random. If the hash
order correlates with time, session or agent, the bootstrap does not correct for it.

Both push the intervals in the same direction: **too narrow**. Combined with §4.1.1, the
intervals reported here are, if anything, optimistic — and the primary result is a null
that survives them being optimistic.

### 4.1 H1c — the primary outcome, null and undetectable

| leg | treatment | control | difference | 95% CI | |
|---|---:|---:|---:|---|---|
| **locked (all 20 epochs)** | 0.0696 | 0.0896 | **−0.0199** | [−0.0560; +0.0086] | contains zero |
| **pre-committed sensitivity** — all partials removed | 0.0721 | 0.0994 | −0.0273 | [−0.0725; +0.0061] | contains zero |
| post-hoc sensitivity — without `09-14` | — | — | −0.0244 | [−0.0619; +0.0051] | contains zero |

🔴 **Which sensitivity is the registered one, and our error in the first draft.** §9.1 of
the analysis spec pre-commits *"the standard sensitivity that removes **all** the partials
as a block"* — `09-01`, `09-03`, `09-20`. The first draft of this paper reported instead a
sensitivity that removes `09-14`, which was **chosen after seeing that one epoch dominates
exposure** and was never pre-committed. Both are now reported, the registered one first
and labelled as such. The direction is worth stating: the pre-committed leg is *more*
favourable to our reading than the post-hoc one we had picked, so the substitution gained
us nothing — which is what makes it a process failure rather than a self-serving one, and
does not make it less of a failure.

This is the stable outcome of the study, and all three legs agree.

### 4.1.1 🔴 Our two uncertainty estimates contradict each other

§3 of the analysis spec pre-commits this sentence:

> *"Under the realized inclusion criterion and `ICC = 0.0985`, **not even total
> elimination of repeated failures is detectable at 80% power**."*

Control sits at `H1c = 0.0896`, so "total elimination" is an effect of **−0.0896**. For
that sentence to hold, an interval must be unable to separate −0.0896 from 0 — it would
have to contain both, hence span at least 0.0896.

**The observed interval spans 0.0646, which is 72% of that, and excludes −0.0896 by
0.0335.** The empirical interval *rejects* the effect the power calculation calls
undetectable. Both statements are ours; they cannot both be right.

We do not adjudicate, and we name the defect on each side:

| estimate | known defect |
|---|---|
| **MDE saturated at 100%** | the `ICC = 0.0985` comes from the pre-registration and was estimated for **density per session-hour**, not for proportion per opportunity. The spec flags this itself and computes the margin: the verdict flips on an **11.5%** drop in ICC (5.6% under whole-epoch counting) |
| **95% CI of [−0.0560; +0.0086]** | percentile cluster bootstrap at 11 and 9 clusters under-covers — real coverage falls well below nominal at this K — and, separately, the resampling does not re-draw the stratum-B sample (§4.4.1), so one component of variance is missing entirely. Both make the interval **too narrow** |

Both defects were known to us before this section existed; what was not done was putting
the two numbers side by side. **The honest reading is that this study does not have a
trustworthy measure of its own uncertainty**, and that the null in H1c rests on the point
estimate and the design, not on the interval. A reader should treat every interval in this
paper as indicative of sign and order of magnitude, not as calibrated coverage.

⚠️ This also disciplines §4.3: an interval "excluding zero" on H1 or H1a is a claim made
with the same under-covering machinery, which is a further reason — independent of the
denominator argument — not to read those as findings. **The caveat applies to every
interval here, including the null one, and not only where it is convenient.** The first
draft attached it only to H1; an adversarial reviewer pointed out that a method cannot be
optimistic selectively.

🔴 **The under-powering is structural, not bad luck.** With 19 analyzable clusters there
is no effect size in the registered parameter space that this design distinguishes from
zero. Reporting the interval without that sentence would be the exact defect family this
project spent eight weeks documenting; the spec makes the declaration mandatory **in the
abstract, not in a footnote**, and that is where it is.

### 4.2 H1a — inverts its conclusion on one epoch, and therefore bears no weight

| | locked | sensitivity (without `09-14`) |
|---|---|---|
| session-hours, treatment / control | 12.70 / 5.16 | **5.57 / 5.16** |
| `H1a` (opportunities/h) | −143.92 · CI [−209.80; −15.34] · **excludes zero** | −63.04 · CI [−120.45; **+1.76**] · **contains zero** |

**The denominator measures idleness.** `span_por_sessao` computes `max(ts) − min(ts)` over
a session's episodes — the distance between first and last event, not time worked. A
session that acts, sleeps, and returns six hours later contributes six hours of exposure.

Measured: nineteen epochs fall between **0.32 and 0.97 h**; `2026-09-14` has **7.13 h**,
alone **56%** of all treatment exposure. The cause isolates to one session (`d37a5964…`)
with **three** episodes — one at 13:52 and two at 20:12, span 6.33 h. The sessions that
actually worked in that epoch produced 74, 65 and 56 episodes in **9 to 10 minutes** each.

⚠️ **The artifact is not introduced by this analysis.** The function is the pilot's, so
the pilot's own `hours_per_epoch` (1.1144) carries the same property. It is a feature of
the registered definition that only manifests when an epoch contains a sparse session.

**We did not change the denominator.** Replacing it with "effective work" would be
altering a locked definition *after* seeing that it yields an uncomfortable result, and
would invalidate `r̂`, the ICC and the `N` that `sizing.py` derived from them.

🔴 **But that cuts both ways, and we did not say so in the first draft.** If the exposure
measure counts idleness, then `r̂`, the ICC and the sample size derived **from that same
measure** inherit the defect. The power calculation that tells us this study is
under-powered was computed on a denominator we are now calling artifactual. We do not know
the direction: a denominator inflated by sparse sessions could have made the pilot's event
rate look lower than it is, which would have **over**-sized the study, or the reverse. The
honest statement is that **the under-powering claim of §4.1 rests on a quantity this
section undermines**, and that resolving it requires recomputing the pilot — which is
future work, not a footnote. It does not rescue the trial either way: the realized N is 20
clusters regardless of what N *should* have been. The
sensitivity is reported alongside and **the divergence is not adjudicated in favour of
either leg** — the rule that says so was pre-committed in §2 of the analysis spec. The
line the reader must take away is the sensitivity one: a conclusion that turns on one
sparse session is not a conclusion.

### 4.3 H1 — an interval excluding zero that is not a finding

`H1` returns **−14.62**, CI [−20.51; −4.79], excluding zero on both legs (sensitivity
−9.74, CI [−16.21; −2.99]).

⚠️ This is **not** presented as a result — and the reason is structural, not rhetorical.

🔑 **`H1` is not an independent hypothesis. It is the product of the other two:**

```
H1  =  repeats / hours  =  (repeats / opportunities) × (opportunities / hours)  =  H1c × H1a
```

Verified on the estimates, relative error ≈ 5×10⁻⁶ in all four arm-by-leg cells — the
residue is the JSON rounding to six places, not a discrepancy. This is an algebraic
identity, so `H1` carries no information that `H1a` and `H1c` do not already carry.

**And the split falls exactly along the denominator.** `H1` and `H1a` both divide by
session-hours; `H1c` does not — it is a ratio of two counts. The two quantities that
exclude zero are **precisely the two that divide by the measure §4.2 shows to be
idleness**, and the one quantity free of that denominator is the null one. That is not a
coincidence we are asserting away; it is visible in the arithmetic above.

⚠️ **What this argument does NOT do, stated because an adversarial reviewer caught us
short here.** It does not explain why `H1` still excludes zero *without* `09-14`. Removing
that epoch nearly equalizes hours per epoch across arms (0.557 treatment against 0.573
control) and `H1` remains at −9.74. So the residual gap is **not** the sparse session. It
is volume: the control arm carries **132.3 opportunities and 11.85 repeats per epoch**
against **93.4 and 6.08** in treatment.

Two readings survive that, and this design does not separate them:

1. the treatment reduces the **volume** of failure activity without moving the **rate** at
   which opportunities become repeated failures (which is what `H1c` measures, and `H1c`
   is null);
2. the arms differ in baseline volume by chance — with 20 clusters and between-epoch
   volume spanning 73 to 234 episodes, that is entirely available.

We cannot adjudicate between them, and we will not pick the flattering one. What we will
say is narrower and survives both: `H1` was **removed from primary on 2026-08-30** for
requiring a **955%** effect (`DESIGN-REVISION-2026-08-30.md` l.196, *"impossible by
construction"*), so an interval excluding zero there cannot be read as the treatment
working — the effect it would imply is outside what the mechanism can produce. And with 9
and 11 epochs the cluster bootstrap has few degrees of freedom and returns optimistic
intervals.

⚠️ **We also owe a note on our own criterion.** §4.2 discards `H1a` because it turns on one
sparse session. `H1` does *not* turn on that session and is discarded anyway, on different
grounds. Applying one standard where it bites and another where it does not is how a ruler
gets chosen by its result. The grounds above are stated separately so a reader can reject
either without the other.

### 4.4 H1b — unevaluable, because two of our own locks collide

| lock | date | text |
|---|---|---|
| `Opportunity` (§3) | **2026-07-29** | *"An **executed action** `a` … for which the serving snapshot at session start contained ≥ 1 failure episode `a_past` with `sig(a_past) = sig(a)`"* |
| `H1b` (§1) | **2026-08-16** | *"An opportunity yields a repeat attempt if the **session** emits at least one action whose signature equals that of `a_past`"* |

These are different estimands. Under the July lock the opportunity **is** the action, and
the action carries `sig(a_past)` by definition ⇒ **H1b = 1.0 by construction**, and the
nesting the pre-registration calls load-bearing ceases to exist. For H1b to have content,
`Opportunity` would have to be a property of the *session* — which changes the denominator
for the **whole** family, not just for H1b.

No later document resolves it: the analysis spec does not mention H1b once.

⚠️ **Correction of our own phrasing (2026-09-21, adversarial review).** We first wrote
that H1b is *"unevaluable"*. That conflates two things. Under the lock we kept, **H1b is
perfectly evaluable and equals 1.0** — it is *trivial*, not unmeasurable, and no artifact
computes it because none is needed. What is unanswerable is the **question** H1b was
written to carry. Saying "unevaluable" made a definitional triviality sound like missing
data, which is the more flattering of the two readings and the wrong one.

**We kept the July lock** — `Opportunity` is the action — because PREREG §420 records that
`r̂`, `p̂0` and the ICC were **all computed by replay under that model**, and that the
construction then locked was the one that *"keeps every locked number valid — the
alternative constructions would have invalidated them"*. Adopting the session reading now
would invalidate those three numbers and, by dependency, the `N_epochs` derived from them.

⚠️ **What is lost, stated plainly.** H1b was the member of the family distinguishing *"the
treatment makes the agent stop trying"* from *"makes it try and succeed"* — §1 of the
pre-registration calls it *"the substantive one for this paper."* **That distinction is
not reportable from this study.** The loss is of mechanism, not of power: H1c was already
declared to have no possible result at the realized N, so nothing here worsens what was
known about detectability.

The reason that goes in the record is **a collision between two locks, unreconciled before
the window closed** — not "we did not measure it", and not "it came out non-significant".

### 4.5 Coverage by arm, and the pre-committed explanation it weakens

Coverage is post-randomization, so per PREREG §5 the ITT over all post-washout epochs
without coverage exclusion is the primary and is what §4.1–4.3 report. Coverage is
reported descriptively:

| | treatment | control |
|---|---:|---:|
| briefs with ≥1 designated chunk | **28.0%** (2 068 / 7 392) | **26.9%** (1 385 / 5 145) |

Across 4 324 designated-serving occurrences, **all 19 signatures were served, each at
≈5.3%** — uniform.

🔴 **This contradicts the projection the pre-commitment rests on.**
`DESIGN-REVISION-2026-08-30.md` committed in advance that a null in H1c *"does not
distinguish 'the mechanism does not work' from 'the lessons it promotes are too generic'"*,
on the grounds that **93.8%** of coverage would concentrate in the bucket signature
`Bash|shell:outro`. The realized distribution is flat. The pre-committed alternative
explanation is therefore **weakened** by the data, which is the opposite of what a
pre-commitment usually does for the party that wrote it, and is why it is reported here
rather than dropped.

⚠️ A near-miss worth recording: `boost_by_id` is **not** a coverage measure — it records
boost *calculated* for every candidate, uniformly, and reading it as coverage would have
produced a fabricated 139 650. Coverage comes from crossing the served id lists against
the designation.

### 4.6 M10 — arm × coverage correlation, reported unconditionally

The registered TOST at `|r| ≤ 0.15` requires **K ≥ 30** analyzed epochs; we have 19. §8 of
the analysis spec declares it **"not evaluable at the realized K"**, which is *not* the
same as "equivalence not established". The correlation and its interval are reported
unconditionally:

| leg | K | r | 95% CI (epoch bootstrap) | |
|---|---:|---:|---|---|
| primary — all | 19 | **+0.1130** | [−0.4773; +0.5088] | contains zero |
| without `09-20` (the 13.86 h partial) | 18 | **−0.1871** | [−0.5704; +0.3353] | contains zero |
| without both partials | 17 | −0.1114 | [−0.5114; +0.4518] | contains zero |
| without `09-14` | 18 | +0.0837 | [−0.5180; +0.4932] | contains zero |

⚠️ **The sign flips.** `09-20` is a control epoch with 14.6% coverage against ≈28%
everywhere else — low because the epoch is 13.86 h long, an artifact of the **clock**, not
of the arm. That one epoch moves `r` from −0.19 to +0.11. All four legs contain zero with
half-widths near 0.5: at K = 19 this correlation distinguishes nothing, and reporting only
the primary leg would have sold a sign that belongs to a truncated epoch. Correlation with
the **dose** rather than the binary arm: −0.0521.

### 4.7 The single epoch at the top dose: chance, not truncation

Only **one** of the 20 designated epochs drew `w = 7.5`, against 3.33 expected. The
explanation that writes itself — *stopping at 20 of 234 biases against the top dose* — is
mechanistic, plausible, and **false**.

Measured over **2 000 seeds** conditioned on the **same realized dates**, using the
published assignment script:

| leg | value | share of the −2.333 deficit |
|---|---:|---:|
| expected under the design (20 × 39/234) | 3.333 | — |
| **truncation** — conditioning on the realized dates | **+0.023** | **1.0%** |
| **chance** — from the conditional mean to the realized | **−2.357** | **101.0%** |

Conditional mean 3.357, mode 3 (25.3%), `P(n = 1) = 10.15%`, `P(n ≤ 1) = 11.95%`. The
conditional mean for `control` is 9.991 against 9 realized, so truncation does not displace
that either.

**Why truncation cannot bias here:** stratification is
`(calendar half) × (weekday | weekend)`, and the first 20 days fall entirely inside `h1`,
where the allocation is already balanced by construction. Conditioning moves the
expectation by +0.023 — and in the direction *opposite* to the intuition. This agrees with
the spec's earlier measurement (23/300 = 7.67%, mode 3-4; the 95% interval of that
proportion is [4.7%; 10.7%] and contains 10.15%); what is new is the **separation of the
two causes**, which the spec asserted without measuring.

The consequence for the paper is negative and is stated as such: with `n = 1` at the top,
**there is no dose-response to read**, and §7 of the analysis spec forbids reading one.

---

## 5. What is not evaluable, and why — declared, not omitted

| registered rule | why unevaluable | what stands in its place |
|---|---|---|
| **H1b** | collision between the 2026-07-29 and 2026-08-16 locks (§4.4) | nothing; the mechanism question is not answered |
| **TOST arm×coverage** at `\|r\| ≤ 0.15` | requires K ≥ 30; K = 19 | correlation + CI, unconditional (§4.6) |
| **dose-response / H3** | `n = 1` at the top dose (§4.7) | per-dose effect with `n` on the same line, no gradient |
| **leave-one-agent-out** | 6 agents over 19 epochs | exploratory, no inference |
| **first-half / second-half contrast** | window truncated inside the first half | not reported |

These are listed **before** the discussion, and were listed in §8 of the analysis spec
before the window closed, so that their absence cannot be read as omission. A rule that
becomes unevaluable and is simply dropped is indistinguishable from a rule that was never
there.

---

## 6. Instrument defects that changed a reported number

Consistent with Paper A's §6, defects that changed a number we had published are part of
the contribution rather than an appendix.

1. **Ruler substitution (`09-20`)** — delivery volume where the spec locks clock exposure;
   16+3+1 published as 17+2+1, propagated to six places including a pushed commit (§3.1).
2. **Post-randomization conditioning on the arm** — mode of observed dose instead of
   designation; 0 divergences, but the premise was wrong (§3.1).
3. **"Zero inversions" is a tautology** — adding a vote to an odd panel under strict
   majority can only hold or tie, so zero inversions is structurally guaranteed and a coin
   would achieve it. The metric with content is agreement with the three-family majority:
   **1 111 / 1 145 = 97.0%**.
4. **A rate generalized from one batch** — *"100% of abstentions are `xai`"* was true in
   the first 100 episodes and false over 1 195 (`xai` 26 + 6 quota + 1 missing · `zhipu`
   13 · `google` 11), and was never re-measured before being asserted.
5. **Claiming the data confirm a locked parameter** — τ is locked since July over five
   families; "confirming" it with outcome-period data is post-hoc. We also called marginal
   rates "agreement", and cited the S1/S2 boundary that τ absorbs while omitting S0/S1,
   which it does not and where the 12 pp gap lives.
6. **A rationalized sign** — we explained a +7/−8 swing by claiming a retry had recovered
   what a fourth panelist rescued; the sets are **disjoint**, and the sign comes from the
   28 losses, not the gains. Recomputed under the published rule: gains 20, losses 28,
   balance **−8**.
7. **A panel composed after counting ties in the trial's own verdicts** — post-hoc by §9
   of the spec, recorded as such. What stands: the fourth family enters **only** as a
   substitute where fewer than three substantive verdicts exist (the role PREREG §695
   assigns it), never as a fourth vote, so it generates no ties; the four-vote set is
   published as declared sensitivity.

Defects 1–7 were found by two mechanisms that catch **disjoint** classes: adversarial
review by independent model families, and mechanical census. Six of the seven above came
from the former on a body of work the latter had already passed.

---

## 7. Threats to validity

**Power.** Addressed throughout and not mitigated: the study is under-powered by
construction and no analysis choice repairs that.

**One-system, one-fleet.** Everything is measured on a single production system. Nothing
here establishes that the effect, or its absence, generalizes.

**Directional bias toward the null.** The 2-2 tie rule resolves to `not_failure` by
design. The study's conservative choice runs in the same direction as its result, and a
reader is entitled to weigh that.

**Denominator.** §4.2. The exposure measure counts idleness, and one epoch dominates.

**Our own bookkeeping.** §1.1. The claim that two estimand decisions preceded the
estimates rests on our commit timestamps in an append-only log.

---

## 8. Discussion

The honest summary of this trial is that it **could not have detected its own effect**, and
that we knew this ten days before the window closed and wrote it down rather than
discovering it afterwards. What remains is not an effect estimate but three observations
about instruments, each of which cost us a published error to find:

**A pre-registration can contradict itself, and the contradiction can survive to the
outcome.** Two locks three weeks apart defined one estimand incompatibly, neither review
caught it, and the analysis specification written a month later did not mention the
affected hypothesis once. The failure mode is not a missing lock — it is two locks that
each look complete alone.

**An interval that excludes zero can be the artifact, and the null the sound result.** The
only significance this trial produced is on the hypothesis previously ruled out as
requiring a 955% effect. Reading the significant line and ignoring the null one would have
inverted the paper.

**A pre-committed alternative explanation can be refuted by the data it was written to
protect.** The concentration projection that made a null ambiguous did not hold; coverage
was flat. That weakens a defence we had reserved for ourselves, which is the only
circumstance in which a pre-commitment demonstrably did its job.

We publish an under-powered null in full because the two alternatives — not publishing, or
publishing a claim the design cannot support — are the behaviours that make under-powered
trials worth less than nothing to the people who read them.

---

## Appendix A — relation to the pre-registration

Deviations are logged in `DEVIATIONS-FOR-PAPER.md`, which is append-only, and the
substantive ones for this paper are §10.29 through §10.34. The list is not summarized here
because a summary of a deviation log is a second copy that will diverge from the first.

Three that a reader cannot reconstruct from the estimates alone:

- the analysis stratum migrated from `S2` to `≥ S1` by panel agreement (κ 0.87–0.93 at
  `≥ S1` against 0.31–0.53 for the S1/S2 split), so the S1/S2 division became an
  instrument finding rather than an analysis boundary;
- the dose band `{2 · 4 · 7.5}` was registered among *"what does not move, and could not"*
  and **moves** — 11/15/17 states of 350, monotone, saturating in `(4.0; 4.4]`. The
  registration promises **less** than what was measured;
- the designation was recorded as an open defect in v1.12 and was **closed** on 2026-08-26.

The two items where the registration promises *less* are the ones that matter, because
nobody corrects unprompted an error that favours them.

## Appendix B — artifacts

| artifact | holds |
|---|---|
| `ITT-2026-09-21.json` | the estimates, both legs, bootstrap parameters |
| `ITEM7-DOSE-TOPO-2026-09-21.json` | the full 2 000-seed distribution of §4.7 |
| `ASSIGNMENT.json` · `ASSIGNMENT-SERVING.json` | designation and served arms |
| `DESIGNATION-2026-08-26.json` | the 19 designated chunks |
| `estimador_itt.py` · `assign_arms.py` · `pilot_replay.py` | the instruments |
| `p2-serving.ndjson` · `episodios-ensaio-20260921.jsonl` | serving log and episodes |
| `ensaio-20260921-PRIMARIO-3fam.jsonl` | 3 592 verdicts, three families |
| `ensaio-20260921-SENSIB-deepseek.jsonl` | 1 195 verdicts, fourth family (sensitivity) |
| `COBERTURA-M10-2026-09-21.json` · `cobertura_e_m10.py` | coverage by arm, per-signature share, M10 and its four legs |
| `MANIFESTO-LASTRO-P2.json` | sha256 of every artifact above, for loss detection |

### B.1 Where each number in the text comes from

Added 2026-09-21 after an adversarial reviewer observed that the header promised universal
traceability and several numbers had no artifact named beside them. **That review was
right, and understated: two of them had no artifact at all** — the coverage figures and
the whole of M10 were computed by an ad-hoc script and never saved. `cobertura_e_m10.py`
now produces them, and reproduces the ad-hoc values exactly.

| number | §  | artifact |
|---|---|---|
| H1, H1a, H1c and every interval | 4.1–4.3 | `ITT-2026-09-21.json` |
| session-hours per arm, opportunities, repeats | 4.2 | idem |
| 7.13 h at `09-14`; session `d37a5964…`, 3 episodes, span 6.33 h; 74/65/56 episodes | 4.2 | `episodios-ensaio-20260921.jsonl` |
| coverage 27.98% / 26.92%; 4 324 occurrences; 19/19 signatures at ≈5.3% | 4.5 | `COBERTURA-M10-2026-09-21.json` |
| the fabricated 139 650 that `boost_by_id` would yield | 4.5 | idem, field `nota_boost` |
| `r` and all four legs; −0.0521 against dose | 4.6 | idem, field `M10` |
| truncation/chance split, 2 000 seeds | 4.7 | `ITEM7-DOSE-TOPO-2026-09-21.json` |
| agreement 1 111/1 145; abstentions 26+6+1 / 13 / 11; gains 20, losses 28 | 6 | `ensaio-20260921-*.jsonl`, recomputed in `DEVIATIONS-FOR-PAPER.md` §10.31 |
| 20 designated, 19 served, 16+3+1 | 3 | `ASSIGNMENT-SERVING.json` + `p2-serving.ndjson` |

⚠️ Several of these are **outside the repository** and several are large.
`scripts/manifesto-lastro-p2.py` hashes all 14 (154 MiB) and
`scripts/backup-lastro-p2.sh` copies them with the hash recomputed **at the destination**.
🔴 **The off-machine leg is declared unverified**: the environment has no host set, so the
ballast currently exists on **one machine**. A manifest proves the bytes are the bytes; it
does not prove a copy exists.

---

## Working list — struck in the commit that closes it

1. ~~**Ballast**: manifest~~ → ✅ **done 2026-09-21** (14 artifacts, 154 MiB, verified at
   the destination; two defects of ours found by mutation and fixed). 🔴 **Still open: the
   off-machine copy** — one machine is not a backup. The trial cannot be re-run: ephemeral
   pod, non-deterministic provider, and `rc4/nox_mem.json` already shows what an unresolved
   version placeholder costs.
2. ~~**Run the registered re-randomization**~~ → ✅ **done 2026-09-21** (§4.0.1a, §4.0.2):
   10 000 redesigns, 9 941 distinct patterns, control of 300/300 reproducing the spec. It
   **disagrees with the bootstrap on H1a**, and `H1` is now reported as an unexplained
   rejection.
3. ~~**Report the pre-committed instrument controls**~~ → ✅ **two of three, 2026-09-21**
   (§4.0.1b): positive **11/11**, negative dual **8/8**, both re-measured over the full
   window. 🔴 **Still open: the sham replay**, which needs the serving code re-executed;
   our attempt to do it by counting over the log was invalid and is recorded as such.
4. **Measure the 30-day freshness question** of §3.0. If a fixed designation ages out,
   `N = 234` was infeasible from the start and §8 changes.
5. **Adversarial review** of this manuscript — **in progress**, five families, 2026-09-21.
   Three have returned; their findings produced §1.1, §3.0, §4.0.1, §4.1.1, §4.4.1, the
   corrections in §4.3 and §4.4, and this appendix. Two pending. Disjoint defect class from
   mechanical census, and §6 is the evidence.
6. **Figures**: the H1a sensitivity (the single-epoch inversion) and the §4.7 seed
   distribution. Both derive from locked artifacts.
7. **Related work** — Paper A's §8 covers the surface literature, not trials of memory
   interventions.
8. **Deposit** as a new version of the registration, declaring the deviations **and** the
   result in one record. Blocked by 1 (off-machine), 2 and 3.

⚠️ Items 2 and 3 are **registered analyses that were not run**, not enhancements. A
manuscript that omits its own pre-registered inference test and its own instrument
controls is not ready, and the fact that three adversarial reviewers had to tell us is
itself the §6 pattern repeating on this document.
