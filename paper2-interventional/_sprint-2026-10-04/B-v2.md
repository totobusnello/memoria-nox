# Under-powered by construction: intention-to-treat results from a pre-registered interventional trial of agent-memory dosing

> **STATUS — DRAFT opened 2026-09-21; v2 prepared 2026-10-04.** Every number below is
> measured and traceable to an artifact, and §B names the artifact for each. What is *not*
> done: ~~figures, related work, and deposit~~ → as of v2, figures (B1, B2) and related work
> (§8) are in; still not done: **the valid sham replay** (§4.0.1c) and **deposit**. The v2
> changes are listed in the changelog at the end.
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

The registered design called for 234 epochs. **Twenty were realized**, of which nineteen
served data.

🔴 **The trial did not stop early: 234 was infeasible from the start.** All 19 designated
chunks share one `created_at` and sit in a sub-pool with a 30-day window, so they leave
eligibility together at 2026-09-20 22:51:23 — **20 of the 234 registered epochs, 8.5%**.
Past that instant no value of the dose reaches them, because the boost is addressed by id
and they are no longer in the candidate list; treatment and control would have been the
same intervention for 214 epochs. The under-powering of this study is therefore a property
of **the registration**, not of the realized window: `sizing.py` sized for 234 epochs on an
intervention that existed for 20.

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
is a measurement of the *denominator*, not of the treatment; a second hypothesis
~~inverts its conclusion on the removal of a **single** epoch whose exposure comes from one
session with three episodes~~ excludes zero **only on the locked leg** — its pre-committed
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

⚠️ One phrase in §9 overstates even so: *"we knew this ten days before the window
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

### 3.0.1 🔴 `N = 234` was infeasible by construction, and the trial ran exactly as long as it could

An adversarial reviewer asked whether the fixed designation ages out of eligibility. It
does, and the measurement is unambiguous.

All 19 designated chunks live in `memory/entities/lessons/*.md` — the **global** sub-pool,
whose window is `freshGlobalMaxAgeDays = 30`. Their `source_date` is NULL in all 19, so
the predicate falls through to `created_at`, which is a **single value for all nineteen**:

```
created_at = 2026-08-21 22:51:23   (identical across all 19)
+ 30 days  = 2026-09-20 22:51:23   ← they leave the window together, in one instant
```

| | |
|---|---:|
| epochs registered | **234** (2026-09-01 → 2027-04-22) |
| epochs in which the designation is eligible | **20** (2026-09-01 → 2026-09-20) |
| share of the registered design that could carry an intervention | **8.5%** |

**After that instant the intervention is not weak — it does not exist.** A chunk that
fails `fetchFreshCandidates` never reaches the list handed to the boost provider, and the
boost is addressed **by id**. No value of `w` and no number of `freshSlots` reaches a
chunk that is not in the candidate list. For 214 of the 234 registered epochs, the
treatment arm and the control arm would have been **the same intervention**.

**This reframes the stopping rule and the headline.** The trial did not stop early. It ran
for the entire interval in which it could have an effect, and closed 51 minutes before the
designation expired. The `09-20` epoch is partial for this reason and not by arbitrary
truncation: the analysis spec's cut *"falls inside the epoch, at 22:51:23Z"* is that
instant.

⚠️ **So the under-powering is not a consequence of the realized window. It is a property
of the registration.** `sizing.py` computed `N = 234` from the pilot; nothing in that
computation knew that the designation it would act on had a 30-day life. Both numbers are
ours, both were locked, and they are incompatible — the same shape as the H1b collision of
§4.4, on a larger object. A trial cannot be sized for 234 epochs on an intervention that
exists for 20.

We record two further facts so the finding is not overstated. The designation **passed**
the full eligibility predicate — file pattern, `importance/pain ≥ 0.7`, age ≤ 30 d — in
19 of 19 on 2026-09-09, in both the served corpus and `current.db`; expiry was a future
event, not a live defect. And the replay harness compensates for the window
(`cfgEm` offsets `freshGlobalMaxAgeDays`), so what stops biting is the **trial**, not the
instrument.

🔑 **This was measurable on 2026-09-09 and was measured then** — eleven days before the
close, in a session that recorded it and left the design decision open. It did not reach
this manuscript until an adversarial reviewer asked the question from the outside. The
finding is ours; noticing that it belonged in the paper was not.

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
| **specificity (sham)** | replay 19 non-designated chunks at the same `w` | ~~🔄 running since 2026-09-22 01:40Z~~ ⛔ **not executed** — the configuration launched was invalid; a valid one is runnable and not yet run (§4.0.1c) |

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
designation that actually ran. It was **declared as not run rather than reported as
failed**, which is the difference between the two that the near-miss above exists to make.

~~🔄 **It is now running** (launched 2026-09-22 01:40Z, `measurement/roda-sham.sh`).
21 runs of `replay-oportunidade.mjs --modo dose` at `w = 4` — one with the real
designation as baseline, 20 with sham designations — sequential, `nice -n 19 ionice -c3`,
because each run exceeds 15 min and the host serves production on 2 vCPU. Expected wall
clock ≈ 5 h.~~

⚠️ **Correction (2026-10-04).** The paragraph struck above was stale when it was written
into this draft and wrong about what the run would measure. The run produced no output and
was aborted; the configuration it used was invalid for the reasons measured in §4.0.1c.
The three design choices below are kept because two of them remain right, and the third
is the one that let the error through.

Three choices in that design, each with its reason:

- **`K = 20` is the minimum, not a round number.** With 21 runs the smallest attainable
  randomization p-value is `1/21 = 4.8%` — fewer shams and the test cannot reject at 5%
  no matter what it finds.
- **The shams are drawn from the eligible pool, not from the corpus.** A sham chunk that
  fails the eligibility predicate never reaches the candidate list, so it would "not move"
  **by construction** — the test would report specificity where there was only
  ineligibility. That is the mirror image of the tautological candidate the spec rejects,
  and it is why `gera-shams.py` applies the 30-day window as well as the path and floor
  predicates. *(2026-10-04: the principle stands; the pool it was applied to did not. See
  §4.0.1c — `gera-shams.py` drew from the 115-chunk pool of a corpus that did not serve
  the trial; the served pool has 108.)*
- **The predicate has an independent control.** Our SQL with the age window returns
  **115** eligible chunks, and the replay independently *observes* `pool: 115` at the same
  `t-ref`. Two routes, one number — without that agreement we would not know whether the
  pool we sample from is the pool the mechanism sees. *(2026-10-04: both routes read the
  same corpus, `corpus-preservado-20260908.db`, so their agreement could not detect that
  the corpus itself was the wrong one. On the corpus that served the trial the pool is
  **108** in 22/22 measured states — §4.0.1c.)*

⚠️ **One limitation, declared.** The corpus of the published anchor
(`e20260826T060003Z.db`) **no longer exists** — it was pruned. ~~This runs on
`corpus-preservado-20260908.db`, the deliberately preserved corpus of the trial, so it
cannot reproduce the published anchor and does not try to: the comparison is internal,
real against sham on **one** corpus, which is what specificity needs.~~

⚠️ **Correction (2026-10-04).** The struck sentence is factually wrong on two counts.
`corpus-preservado-20260908.db` is **not** the corpus that served the trial: it was
preserved from the live database on 2026-09-08, after 60 `memory/lessons.md` chunks had
been re-ingested on 2026-09-07, and production never served them (DEVIATIONS §10.10,
§10.14; §4.0.1c). The corpus that served is the one the serving process held open from
2026-09-03, recovered from its file descriptor as
`corpus-SERVING-REAL-e20260903-recuperado.db`. And "one corpus" does not rescue the
comparison when, on that corpus, the real arm cannot move at any dose (§4.0.1c).

Artifact: `CONTROLES-JANELA-COMPLETA-2026-09-21.json`.

#### 4.0.1c The specificity control: invalid as configured, runnable, not yet run

**What was launched, and what it measured.** The design was 21 replays
(`measurement/roda-sham.sh`): the real designation as baseline and 20 sham designations of
19 non-designated chunks each, at the same `w`. It was launched on 2026-09-22 at 01:40Z.
The first 12 runs each hit our own 3 600 s ceiling (`exit 124`) and wrote no output, and
the loop was aborted at 13:45Z (project log `docs/HANDOFF.md` at the repository root,
entry of 2026-09-22). `exit 124` is our timeout, not a verdict: **the launched sham measured nothing.**

**The probes, and the reading we gave them.** Two probes then replayed the real
designation alone, at `w = 4` and `w = 100 000`: one state (`sonda2`), and the **132**
states in which production recorded `ids_tratado ≠ ids_controle` (`sonda3`). Both returned
`churn = 0` in every state at both doses (`out/NOGO-replay-sonda{2,3}-2026-09-23.json`).
`sonda3`'s replayed *control* set matched production's in **0 of 132** states, and none
of production's fresh-slot ids appeared in any of them. Our log of 2026-09-23 read this as
a test without power — the real arm is 0, no sham can exceed it, so
`p = #{sham ≥ real} / 21 = 21/21 = 1.0` "by construction" — and named, as the remaining
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
   designated chunk in it; the first designated chunk sits at pool position 60–66. The
   bonus breaks ties only inside a stratum, so no `w` reaches a designated chunk there.
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
boundary stratum has a median of 4 members (range 3–4) and holds 1–3 designated chunks in
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
failure. This is a **prediction** from the measured strata and that arithmetic — no sham
designation was ever replayed.

**What a valid sham needs, and why it has not been run.** (i) The served corpus,
`corpus-SERVING-REAL-e20260903-recuperado.db`; (ii) the `rowid` cut; (iii) shams redrawn
from the served pool (108 chunks, 89 non-designated); (iv) a `brief_log` covering the trial
through 2026-09-20. The first three are in hand. The fourth is not: the copy we can work on
off-host ends at 2026-09-08 05:52:04, and the trial's `brief_log` after that exists only
on the production host. Exporting it is **pending authorization**. At about one minute of
wall clock per 22 states, cost is not the obstacle. **The valid sham is runnable; it has
not been run.**

**What was measured and what was not.**

| | states | status |
|---|---:|---|
| fidelity and dose response, served corpus + `rowid` | **22 of 132** | **measured** — all timestamped between 2026-09-01T11:07Z and 2026-09-02T08:37Z, i.e. inside the single treatment epoch `09-01` (09:00 UTC boundary) |
| the same, for the states timestamped 2026-09-12 to 09-16 | **110 of 132** | **not measured** — needs (iv). For these states only two facts are measured: the probe's control mismatch (0/132) and that production never served the chunks the probe put in the fresh slots. That the dose would also respond there is an **expectation** |
| a sham designation replayed | 0 | **not run** |
| byte-identity of the serving `dist/` used (rebuilt 2026-09-29) with the build that served | — | **not measured**; `src/api/brief.ts` matches the probe's recorded hash, and the 22/22 exact reproduction is the functional check |

**Our error, stated.** DEVIATIONS §10.14–§10.15 had measured this mechanism on 2026-09-09:
on the recovered corpus `mexeu(2) = 20` and `mexeu(10⁵) = 37`, matching production's
`churn > 0 = 20`; on the realigned corpus `0 / 0`; cause, a never-served cohort holding the
`freshSlots`. The sham was nevertheless configured on a corpus of the family §10.15 shows
to be blind, and the HANDOFF hypothesis of 2026-09-23 reopened a question §10.15 had
already answered.

**What this does to the claims of this paper.** Nothing in §4.1–4.7 rests on the sham. The
positive control (11/11) still establishes that the mechanism changed briefs in every
treatment epoch; until a valid sham is run, **nothing here establishes that the change is
specific to the designated chunks** rather than background churn at the same `w`. The
specificity control remains a registered analysis that has not been run, now with a
measured reason and a runnable configuration in place of a stale "running".

Artifacts: `out/NOGO-replay-sonda{2,3}-2026-09-23.json`;
`_sprint-2026-10-04/B-replay-fidelity.md`, its eight runs and stratum files in
`_sprint-2026-10-04/B-replay-fidelity/` (summary `RESUMO.txt`);
`measurement/sprint-replay-estratos.mjs`; `measurement/sprint-replay-fidelidade-resumo.py`.

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

### 4.2 H1a — excludes zero only on the locked leg, and therefore bears no weight

⚠️ **Correction (2026-10-04).** This section was titled *"H1a — inverts its conclusion on
one epoch"* and its table showed only the post-hoc leg that removes `09-14`. That broke
the rule §4.1 states for itself — the **pre-committed** sensitivity is reported first —
and it made the inversion look specific to one epoch when it is not. Under the
pre-committed leg (§9.1 of the spec: the three partials removed, `09-14` **kept**), the
H1a interval already contains zero while the point estimate barely moves. What turns on
`09-14` is the **magnitude**; the exclusion of zero is a property of the locked leg alone.

| | locked (all 20 epochs) | **pre-committed sensitivity** — partials `09-01`, `09-03`, `09-20` removed | post-hoc sensitivity — without `09-14` |
|---|---|---|---|
| session-hours, treatment / control | 12.70 / 5.16 | 12.16 / 4.08 | **5.57 / 5.16** |
| `H1a` (opportunities/h) | −143.92 · CI [−209.80; −15.34] · **excludes zero** | −133.34 · CI [−203.62; **+7.41**] · **contains zero** | −63.04 · CI [−120.45; **+1.76**] · **contains zero** |

Source of the pre-committed column: `ITT-SENSIB-PRECOMPROMETIDA.json` (field
`sensibilidade`), the same artifact that holds the pre-committed row of §4.1. The registered
re-randomization test, on a different estimand, does not reject either (`p = 0.0855`,
§4.0.2).

**The denominator measures idleness.** `span_por_sessao` computes `max(ts) − min(ts)` over
a session's episodes — the distance between first and last event, not time worked. A
session that acts, sleeps, and returns six hours later contributes six hours of exposure.

Measured: nineteen epochs fall between **0.32 and 0.97 h**; `2026-09-14` has **7.13 h**,
alone **56%** of all treatment exposure. The cause isolates to one session (`d37a5964…`)
with **three** episodes — one at 13:52 and two at 20:12, span 6.33 h. The sessions that
actually worked in that epoch produced 74, 65 and 56 episodes in ~~**9 to 10 minutes**~~
**8 to 10 minutes** each *(corrected 2026-10-04: measured spans 9.71, 8.86 and 8.03 min,
recomputed with the pilot's own per-session grouping for Figure B1)*.

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
line the reader must take away is ~~the sensitivity one: a conclusion that turns on one
sparse session is not a conclusion~~ that **both** sensitivity legs contain zero — the
registered one without touching `09-14`, the post-hoc one by removing it — and that the
registered test does not reject. An interval that excludes zero on the locked leg only,
on a denominator dominated by one sparse session, is not a conclusion.

![Figure B1](figures/figB1-h1a-inversao.svg)

**Figure B1 — H1a's interval excludes zero only on the locked leg; its exposure
denominator is dominated by one epoch of idle time.** (a) Session-hours per epoch, by
designated arm, as the registered estimator computes them: for each session, the span
between its first and last event, summed per epoch (`span_por_sessao`, imported from
`pilot_replay.py`). Nineteen epochs fall between 0.32 and 0.97 h. `2026-09-14`
(treatment, `w = 4`) has 7.13 h, which is 56% of all treatment exposure (12.70 h over 11
epochs, against 5.16 h over 9 control epochs). Almost all of it comes from one session with
three episodes spanning 6.33 h, while the epoch's three busiest sessions logged 74, 65 and
56 episodes within 8.0–9.7 min each. (b) The H1a difference, treatment − control in
opportunities per session-hour, with its 95% cluster-bootstrap interval (epoch as the
unit, 10 000 replicates, seed 20260921) under three legs. The locked leg excludes zero:
−143.92 [−209.80; −15.34]. The pre-committed sensitivity, which removes the three partial
epochs and keeps `09-14`, contains zero: −133.34 [−203.62; +7.41]. So does the post-hoc
sensitivity, chosen after seeing the data, which removes `09-14`: −63.04 [−120.45; +1.76].
Filled marker: the interval excludes zero; hollow marker: it contains zero. Every interval
here under-covers (§4.1.1, §4.4.1). The registered re-randomization test, a different
estimand (§4.0.2), gives `p = 0.0855` and does not reject. The headline embedded in the
SVG (*"H1a turns on one epoch: the exposure denominator counts idle time"*) predates this
correction; the caption title above is the one that holds, and regenerating the SVG with it
is on the working list. Sources: panel (a) from
`episodios-ensaio-20260921.jsonl` and `ASSIGNMENT-SERVING.json` — the script aborts unless
the per-arm sums reproduce `horas_sessao` in `ITT-2026-09-21.json`; panel (b) from
`ITT-2026-09-21.json`, `ITT-SENSIB-PRECOMPROMETIDA.json` and
`RERANDOMIZACAO-2026-09-21.json`. Generated by `measurement/sprint-figB-h1a-inversao.py`.

### 4.3 H1 — an interval excluding zero that is not a finding

`H1` returns **−14.62**, CI [−20.51; −4.79], excluding zero on ~~both legs~~ all three
legs (pre-committed sensitivity −15.59, CI [−22.43; −4.05]; post-hoc sensitivity without
`09-14` −9.74, CI [−16.21; −2.99]). *(2026-10-04: the pre-committed leg, from
`ITT-SENSIB-PRECOMPROMETIDA.json`, was missing here for the same reason as in §4.2; adding
it changes no conclusion of this section.)*

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
| **truncation** — conditioning on the realized dates | **+0.023** | ~~**1.0%**~~ **−1.0%** |
| **chance** — from the conditional mean to the realized | **−2.357** | **101.0%** |

*(Corrected 2026-10-04: the truncation share was printed unsigned, so the two shares summed
to 102%. With signs — +0.0232 and −2.3565 against a deficit of −2.3333 in
`ITEM7-DOSE-TOPO-2026-09-21.json` — they are −1.0% and +101.0%, which sum to 100%.)*

Conditional mean 3.357, mode 3 (25.3%), `P(n = 1) = 10.15%`, `P(n ≤ 1) = 11.95%`. The
conditional mean for `control` is 9.991 against 9 realized, so truncation does not displace
that either.

⚠️ **Two traceability notes (2026-10-04).** (1) The `control` figure 9.991 is held by no
artifact — it appears only in `DEVIATIONS-FOR-PAPER.md` — because
`ITEM7-DOSE-TOPO-2026-09-21.json` stores only the `w = 7.5` distribution. An independent
redraw of **20 000** designs with `assign_arms.assign` and a declared seed recipe
(`_sprint-2026-10-04/figures/figB2-item7-crosscheck-20000.json`) gives 10.0124 ± 0.0146 for `control`,
consistent with 9.991 within the Monte-Carlo error of a 2 000-seed run; it corroborates the
number but does not make it traceable. (2) The seed recipe of the 2 000-seed run is not
recorded in its artifact, unlike the re-randomization's `seed_prefix`; three guessed
recipes did not reproduce its histogram, so the 20 000-seed run is a second measurement,
not a reproduction. It gives `P(n = 1) = 9.11% ± 0.20%` against 10.15% here, whose own
Monte-Carlo s.e. at 2 000 seeds is about 0.7 pp: consistent, and a reminder that the
10.15% carries that much noise.

![Figure B2](figures/figB2-sementes-dose-topo.svg)

**Figure B2 — One epoch at the top dose is a tail draw, not a truncation effect.**
Distribution of `n`, the number of the 20 realized epochs assigned `w = 7.5`, over 2 000
designs re-drawn with the published `assign_arms.py` and conditioned on the same dates. The
realized `n = 1` (highlighted) has probability 10.15%, and `P(n ≤ 1) = 11.95%`. The mode is
3 (25.3%). The dashed line is the design expectation 20 × 39/234 = 3.333; the dotted line
is the conditional mean, 3.357. The two lines are 0.023 apart, which is 0.7 Monte-Carlo
standard errors (s.e. 0.035 over 2 000 seeds, computed from the histogram). Conditioning on
the realized dates therefore moves the expectation by an amount whose sign this run does
not resolve. The whole deficit of −2.333 is chance; truncation accounts for about 1% of it
in magnitude. With `n = 1` at the top dose, there is no dose-response to read (analysis
spec §7). Source: `ITEM7-DOSE-TOPO-2026-09-21.json`. The script aborts unless the
histogram reproduces the artifact's summary fields, the design counts (39 of 234) come
from `assign_arms.py`, and the realized count matches `ASSIGNMENT-SERVING.json`. Generated
by `measurement/sprint-figB-sementes-dose-topo.py`.

**Why truncation cannot bias here:** stratification is
`(calendar half) × (weekday | weekend)`, and the first 20 days fall entirely inside `h1`,
where the allocation is already balanced by construction. Conditioning moves the
expectation by +0.023 ~~— and in the direction *opposite* to the intuition~~, which is
0.7 Monte-Carlo standard errors from zero (s.e. 0.035 over 2 000 seeds); **its sign is not
resolved**, and the independent 20 000-seed redraw gives −0.007 ± 0.011. Truncation
accounts for about 1% of the deficit in magnitude, in either direction. *(Corrected
2026-10-04: the first version read a direction into a difference inside the Monte-Carlo
noise.)* This agrees with
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

## 8. Related work

Four bodies of work bear on this trial, each read for what it gives us and for what this
trial does **not** do that its authors do. In short: the agent-memory literature has
benchmarks, cost characterisations and — dated 1 October 2026 — one randomised design, but
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
as a fairness device and measures that order matters — ExpRAG's average success is 0.57
under Easy→Hard and 0.69 under Hard→Easy (its Table 2) — over two *sorted* orders, not
sampled ones.

**What the canonical survey asks for.** The TMLR survey [@huang2026survey] closes its
evaluation discussion (§9.6) by asking for "closed-loop, longitudinal, and
execution-grounded evaluation paradigms", in environments "where experience accumulation has
real consequences", "enabling comparison between memory-augmented agents and memory-free
baselines under identical conditions", with replayable state and provenance. This trial is
a **neighbour of that direction, not an instance of it**: §9.6 contrasts memory against
*no* memory; we contrast two policies of an always-on memory. We share the paradigm — a
live system, a closed loop, per-brief provenance (`ids_tratado` / `ids_controle`) and a
replayable serving state — and §4.0.1c shows what "replayable" costs: the replay reproduces
production only on the corpus that actually served and with an exact serve-state cut. On
the version pinned in Paper A (sha256 `497e9549…`, 4 Aug 2026) we count zero occurrences of
`random*` and of `pre-regist*`; the single `A/B` appears as a cost that user simulators
spare ("reducing costs associated with live user studies and online A/B testing"). We read
that as the **absence of a convention**, not a claim that no one has run such experiments.
Three other surveys [@zhang2024memorysurvey; @hu2025memoryage; @du2026memoryautonomous]
return zero for `randomi[sz]ed`, `A/B` and `pre-?regist` (lower bounds: hyphenation not
stitched).

**Telemetry is the other axis.** Omri et al. [@omri2026agentmemory] attribute tokens,
latency, utilisation and energy to memory construction, retrieval and generation across ten
systems, with no randomised contrast. We measure whether a lever changed what agents
*did*, and report **no cost, latency or energy**; a trial carrying their per-phase
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
| **This trial** | promotion dose *w* on 19 designated chunks | production fleet, 24 h epochs | **yes**, public-beacon seed | **yes** (OSF `yf7d2`) | **yes** |

"Not determined" means *we did not read far enough to say*; "not stated" means *not found
in what was read*.

**Causal Memory Policy.** Behnam and Wang [@behnam2026cmp] (arXiv, 1 Oct 2026, not
peer-reviewed) show that a memory's utility is "not identified by any design that holds
M−m fixed while randomizing only whether m is included" when retrieval mediates the effect
— a *retrieval-level positivity violation* — and restore identification by randomising
which memories occupy *k* reserved context slots, with design-fixed propensities and a
self-normalised inverse-propensity estimator. Identification fails for 54% of required
memories on LongMemEval and 67% on LoCoMo, and the failure persists in Mem0 replayed over
benchmark histories.

Three points of contact. **First, an instance of their failure is in our data.** The 19
designated chunks leave eligibility together at 2026-09-20 22:51:23, after which no dose
reaches them, because the boost is addressed by id and they are no longer candidates;
treatment and control become the same intervention for 214 of 234 registered epochs
(§3.0.1). CMP is the formal name and the first treatment of that failure we have found. We
did not have the framing at registration (2026-08-18) and claim no priority. Whether the 20
*realised* epochs also contain a partial failure is a question for Paper A's exposure
measurements and §4 of this paper; this section does not assert it. **Second, the
estimands differ.** CMP identifies an individual memory's utility per interaction; we
estimate an intention-to-treat effect of one lever with the fleet-wide epoch as unit, do
not randomise within a brief, and have no propensity-weighted estimator. **Third, the
evidence differs in kind.** Theirs is benchmark and replay evidence with a measured
per-query cost; ours is live, pre-registered, with an interval that by our own account
(§4.1.1) does not deserve trust. CMP-style slot randomisation *on* a live fleet *under* a
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
§4.0.1b. The sham replay, the placebo-like specificity control, was **not executed**: the
configuration launched was invalid, and a valid one awaits data that exist only on the
production host (§4.0.1c). We used no covariate variance reduction [@deng2013cuped] and did
not interleave [@radlinski2008clickthrough; @chapelle2012interleaved; @hofmann2016online],
for which Hofmann et al. report one to two orders of magnitude more sensitivity than
absolute metrics; we have no per-item credit signal to interleave on.

**Why the unit is the epoch.** When units share state, per-unit randomisation is biased
— the problem around which marketplace [@blake2014marketplace; @johari2022twosided] and
network [@saveski2017network; @aronow2017interference] experimentation are built. The
switchback remedy randomises the whole system over time
[@bojinov2023switchback; @hu2022switchback; @basse2023minimax] and comes with
randomisation-based inference [@bojinov2019timeseries]. Ours is a fleet-level switchback
with 24 h epochs and a two-hour washout. Unlike that literature, we fixed the washout ex
ante instead of estimating the carryover order; we have 20 periods; and a memory store
accumulates, so carryover through *state* may outlast any fixed washout. We claim the
relation, not that these theorems apply to our state process.

**Few clusters.** Our percentile cluster bootstrap runs on 9–11 clusters per arm, the
regime in which ordinary cluster bootstraps over-reject [@cameron2008bootstrap], perform
"poorly with fewer than eleven clusters" [@webb2014reworking], and for which a six-point
wild bootstrap is recommended [@cameron2015practitioner]. We used none of these. The
registered re-randomisation test (§4.0.2) is the finite-sample alternative — a Fisher
randomisation test [@imbens2015causal; @bojinov2019timeseries] — and the inference to
weight where the two disagree, as on H1a.

**Under-power and counterfactual logging.** Across twenty-five large field experiments,
"the median confidence interval on return on investment is over 100 percentage points
wide" [@lewis2015unfavorable]. Ours is a *weaker* case: they were under-powered by the
economics of the outcome, we by a registration whose sample size ignored a 30-day
eligibility window (§3.0.1). Observational comparison is not the remedy: observational methods often fail to recover the
effects measured in the same advertising experiments [@gordon2019comparison]. Our replay analyses belong to the family of Li et al.
[@li2011unbiased], and the closest analogue of our sham is ghost-ads logging of the
exposures the treatment *would* have produced [@johnson2017ghost]: in both, the
counterfactual is only as good as the state it is computed from — which is exactly where
our sham configuration failed (§4.0.1c).

### 8.4 Pre-registration, and what a null is worth

Pre-registration in ML and NLP has been piloted, not adopted: the NeurIPS 2020 and 2021
workshops [@bertinetto2020prereg; @albanie2022prereg] ran registered-report-style review
(the 2021 preface reports 22 proposals, 10 accepted and 3 results papers); it has been argued for in NLP [@vanmiltenburg2021prereg],
weighed against its costs [@sogaard2023twosided] and adapted to predictive modelling
[@hofman2023prereg]. Vaccaro [@vaccaro2026prereg] lists **memory settings** among the
researcher degrees of freedom of experiments with AI agents — agents as subjects, so the
fit is by analogy — and Wilder and Zhou [@wilder2025evaluation] propose that ML venues
require a declaration of preregistration for field experiments. In IR, a Dagstuhl report
[@bauer2023dagstuhl] recommends results-blind review. The only memory-specific
pre-registered design we found is Feng et al.'s, on benchmarks. This trial is a
*registration*, **not a registered report** — its protocol was never peer-reviewed before
data — and its deviations are in Appendix A. The cross-field arguments
[@nosek2018prereg; @chambers2022registeredreports; @munafo2017manifesto] are the standing
justification. Registration changes what gets reported: 17 of 30 large NHLBI trials before
2000 reported significant benefit, against 2 of 25 after mandatory prospective registration
of outcomes [@kaplan2015nullnhlbi].

**Power language needs care.** The critiques of low power [@ioannidis2005false;
@button2013power; @gelman2014beyond] and of post-experiment power calculations
[@hoenig2001abuse] apply here; Hoenig and Heisey also call power calculations "valuable in
planning an experiment". Our saturated minimum detectable effect is **prospective and
outcome-independent** — the planning form — but its inputs are the problem: the ICC was
estimated for a different quantity (§4.1.1). The choice of significance test is known to
change error rates on IR test collections [@urbano2019significance]; we know of no
corresponding analysis for live retrieval experiments.

### 8.5 Position

**Not new:** that memory evaluation scores systems rather than behavioural effect;
randomising a retrieval-side lever with known propensities; the switchback design and its
inference; pre-registering ML experiments. **What this trial is:** a pre-registered,
beacon-seeded, fleet-level switchback on live agent traffic, with per-brief provenance,
instrument controls, and a null reported with its power failure and its own
contradictions. **What it is not:** it does not identify per-memory utility, randomise
within a brief, estimate carryover or measure cost; it compares two policies, not memory
against none; it is one system on one fleet; and its specificity control has not been run
(§4.0.1c). **What it adds, narrowly:** a live-traffic instance of the positivity failure
CMP formalises (§3.0.1), and a registration whose sample size and estimand each looked
complete alone and contradicted each other. **What would falsify this positioning:** a
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

The honest summary of this trial is that it **could not have detected its own effect**, and
that we knew this ten days before the window closed and wrote it down rather than
discovering it afterwards. What remains is not an effect estimate but three observations
about instruments, each of which cost us a published error to find:

**A pre-registration can contradict itself, and the contradiction can survive to the
outcome.** It happened twice here, at two scales. Two locks three weeks apart defined one
estimand incompatibly (§4.4), and neither review caught it. And the sample size was
computed for 234 epochs while the intervention it would act on had a 30-day life —
**8.5% of the registered design** (§3.0.1). The second is the more instructive, because
each number is correct in isolation: `sizing.py` did its arithmetic faithfully, and the
30-day window is a documented default. Neither document was wrong; they were never read
against each other. The failure mode is not a missing lock — it is two locks that each
look complete alone, and no step in the process whose job is to cross them.

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
| `RERANDOMIZACAO-2026-09-21.json` · `rerandomizacao.py` | the registered sharp-null test, 10 000 redesigns (§4.0.1a, §4.0.2) |
| `CONTROLES-JANELA-COMPLETA-2026-09-21.json` · `controles_instrumento.py` | instrument controls over all 20 epochs (§4.0.1b) |
| `out/CONTROLES-2026-09-10.json` | the same controls at the trial's midpoint — 6/6 and 3/3, superseded by the row above |
| `out/H1C-POWER-REALIZADO-2026-09-10.json` | the MDE saturation of §4.1, computed before the window closed |
| `out/H1C-POWER-FRACIONARIA-2026-09-10.json` · `out/H1C-POWER-SEM-0903-2026-09-10.json` | the two other inclusion cuts of the power margin (§4.1.1) |
| `out/expiracao-designados-2026-09-09.json` | the designation's expiry measurement of §3.0.1 — `created_at` and the 30-day window |
| `MANIFESTO-LASTRO-P2.json` | sha256 of every artifact above, for loss detection — ⚠️ **except the rows marked † below** (2026-10-04) |
| † `ITT-SENSIB-PRECOMPROMETIDA.json` (sha256 `0191ee54…`) | the **pre-committed** sensitivity leg (§9.1 of the spec: all partials removed) — source of the pre-committed rows of §4.1, §4.2, §4.3 and of Figure B1(b). Not in the manifest, and not listed here before v2 |
| † `out/NOGO-replay-sonda{2,3}-2026-09-23.json` · `out/NOGO-replay-ts-com-alteracao-2026-09-23.txt` | the two replay probes of §4.0.1c and the 132 states they replayed |
| † `_sprint-2026-10-04/B-replay-fidelity/` (8 runs, 2 stratum files, `RESUMO.txt`) · `measurement/sprint-replay-estratos.mjs` · `measurement/sprint-replay-fidelidade-resumo.py` | the corpus × cut replay test and the stratum structure of §4.0.1c; the summary script recomputes every number from the runs |
| † `measurement/sprint-figB-h1a-inversao.py` · `measurement/sprint-figB-sementes-dose-topo.py` · `_sprint-2026-10-04/figures/` | Figures B1 and B2 (SVG + PNG + `.run.json`), regenerated from the artifacts above; each script aborts if its plotted values diverge from the locked JSON |
| † `_sprint-2026-10-04/figures/figB2-item7-crosscheck-20000.json` · `measurement/sprint-figB-item7-crosscheck.py` | an independent 20 000-seed redraw with a declared seed recipe, corroborating §4.7 within Monte-Carlo error; not a reproduction of the 2 000-seed run, whose seed recipe was not recorded |

### B.1 Where each number in the text comes from

Added 2026-09-21 after an adversarial reviewer observed that the header promised universal
traceability and several numbers had no artifact named beside them. **That review was
right, and understated: two of them had no artifact at all** — the coverage figures and
the whole of M10 were computed by an ad-hoc script and never saved. `cobertura_e_m10.py`
now produces them, and reproduces the ad-hoc values exactly.

| number | §  | artifact |
|---|---|---|
| H1, H1a, H1c and every interval | 4.1–4.3 | `ITT-2026-09-21.json` — except the pre-committed legs: |
| pre-committed sensitivity of H1c, H1a and H1; session-hours 12.16 / 4.08 | 4.1–4.3 | `ITT-SENSIB-PRECOMPROMETIDA.json`, field `sensibilidade` (added 2026-10-04) |
| session-hours per arm, opportunities, repeats | 4.2 | idem |
| 7.13 h at `09-14`; session `d37a5964…`, 3 episodes, span 6.33 h; 74/65/56 episodes | 4.2 | `episodios-ensaio-20260921.jsonl` |
| coverage 27.98% / 26.92%; 4 324 occurrences; 19/19 signatures at ≈5.3% | 4.5 | `COBERTURA-M10-2026-09-21.json` |
| the fabricated 139 650 that `boost_by_id` would yield | 4.5 | idem, field `nota_boost` |
| `r` and all four legs; −0.0521 against dose | 4.6 | idem, field `M10` |
| truncation/chance split, 2 000 seeds | 4.7 | `ITEM7-DOSE-TOPO-2026-09-21.json` |
| Monte-Carlo s.e. 0.035 of the conditional mean; signed shares −1.0% / +101.0% | 4.7 | computed from the histogram in `ITEM7-DOSE-TOPO-2026-09-21.json`; recorded in `_sprint-2026-10-04/figures/figB2-sementes-dose-topo.run.json` |
| `control` conditional mean 9.991 | 4.7 | **no artifact** — `DEVIATIONS-FOR-PAPER.md` only; corroborated (10.0124 ± 0.0146) by `_sprint-2026-10-04/figures/figB2-item7-crosscheck-20000.json` |
| spans 9.71 / 8.86 / 8.03 min of the three busiest `09-14` sessions | 4.2 | `episodios-ensaio-20260921.jsonl`; recorded in `_sprint-2026-10-04/figures/figB1-h1a-inversao.run.json` |
| every number of §4.0.1c (0/132; 22/22; 17/22; strata; pool 108 / 115) | 4.0.1c | `_sprint-2026-10-04/B-replay-fidelity/RESUMO.txt` and the runs beside it; 11.9 and 1.5 × 10⁻¹⁰ are hypergeometric arithmetic on those counts (`B-replay-fidelity.md` §4) |
| agreement 1 111/1 145; abstentions 26+6+1 / 13 / 11; gains 20, losses 28 | 6 | `ensaio-20260921-*.jsonl`, recomputed in `DEVIATIONS-FOR-PAPER.md` §10.31 |
| 20 designated, 19 served, 16+3+1 | 3 | `ASSIGNMENT-SERVING.json` + `p2-serving.ndjson` |

⚠️ Several of these are **outside the repository** and several are large.
`scripts/manifesto-lastro-p2.py` hashes all 14 (154 MiB) and
`scripts/backup-lastro-p2.sh` copies them with the hash recomputed **at the destination**.
✅ **Both legs now verified at the destination** (2026-09-22 01:48Z): local **12/12**,
off-machine **12/12** on a host that is not the one that served the trial — it has no
`/root/.openclaw`, its epoch pointer is frozen at 2026-08-23, and it already holds Paper
1's ballast. Identified by **capability, never by address**. A manifest proves the bytes
are the bytes; it does not prove a copy exists, which is why the copy is verified
separately and carries a dated receipt.

---

## Working list — struck in the commit that closes it

1. ~~**Ballast**: manifest + two verified copies~~ → ✅ **done 2026-09-22**: 17 artifacts,
   154 MiB, **both legs 12/12 recomputed at the destination**. Three defects of ours found
   and fixed along the way — a directory hash reimplemented in shell that diverged by one
   trailing newline, an `rsync` that ran *before* the check and so restored the corrupted
   byte it was meant to detect, and an `ssh` inside a `while read` that ate the loop's
   stdin and verified **1 of 12** while reporting "0 divergem".
   ⚠️ **2026-10-04:** the manifest does not cover `ITT-SENSIB-PRECOMPROMETIDA.json`, the
   only source of the pre-committed rows of §4.1–4.3 — a published number resting on an
   artifact the ballast does not protect. Open as item 10.
2. ~~**Run the registered re-randomization**~~ → ✅ **done 2026-09-21** (§4.0.1a, §4.0.2):
   10 000 redesigns, 9 941 distinct patterns, control of 300/300 reproducing the spec. It
   **disagrees with the bootstrap on H1a**, and `H1` is now reported as an unexplained
   rejection.
3. ~~**Report the pre-committed instrument controls**~~ → ✅ **two of three, 2026-09-21**
   (§4.0.1b): positive **11/11**, negative dual **8/8**, both re-measured over the full
   window. ~~🔴 **Still open: the sham replay**, which needs the serving code re-executed;
   our attempt to do it by counting over the log was invalid and is recorded as such.~~
   ⛔ **2026-10-04: the sham was not executed** (§4.0.1c). The run launched on 2026-09-22
   produced no output, and its configuration was invalid — wrong corpus, inclusive cut,
   shams drawn from the 115-pool instead of the 108-pool. On the served corpus with the
   exact cut, the replay reproduces production 22/22 and responds to dose. Still open as
   item 9.
4. ~~**Measure the 30-day freshness question**~~ → ✅ **done 2026-09-21** (§3.0.1):
   `N = 234` **was** infeasible — the designation expires 2026-09-20 22:51:23, giving 20
   eligible epochs of 234. §9 *(numbered §8 before v2)* rewritten around it.
5. ~~**Adversarial review** of this manuscript~~ → ✅ **done 2026-09-21**: five families
   launched, **four delivered with `exit: 0` receipts** (DeepSeek, Grok, GLM on this paper;
   Kimi on Paper A). Their findings produced §1.1, §3.0, §3.0.1, §4.0.1, §4.0.2, §4.1.1,
   §4.4.1, Appendix B.1 and the corrections in §3.1, §4.1–4.5. The fifth (Codex) returned a
   parecer whose citations do not resolve against the file and is recorded as invalid in
   `REVISAO-ADVERSARIAL-2026-09-21.md` — a review that cites sections the document does not
   have is not evidence about the document.
6. ~~**Figures**: the H1a sensitivity (the single-epoch inversion) and the §4.7 seed
   distribution. Both derive from locked artifacts.~~ → ✅ **done 2026-10-04**: Figure B1
   (§4.2) and Figure B2 (§4.7), each generated by a script that aborts if its values
   diverge from the locked artifacts. Making them surfaced four corrections to the text
   (§4.2 pre-committed leg; "8 to 10 minutes"; the signed truncation share; the unresolved
   sign of +0.023) — see the changelog. ⚠️ The headline embedded in the B1 SVG still reads
   *"H1a turns on one epoch"*; regenerate it with the caption title of §4.2 (item 11).
7. ~~**Related work** — Paper A's §8 covers the surface literature, not trials of memory
   interventions.~~ → ✅ **done 2026-10-04**: §8, condensed (~2 000 words) from
   `_sprint-2026-10-04/B-related-work.md` (~4 100 words), with references resolving in
   `B-related-work.bib`. Before submission: re-check Behnam & Wang (arXiv 2610.02070,
   1 Oct 2026, not peer-reviewed) for a revised version, and re-read MemoryArena v2 in
   full.
8. **Deposit** as a new version of the registration, declaring the deviations **and** the
   result in one record. Blocked by 1 (off-machine), 2 and 3 *(the open part of 3 is now item 9)*.
9. **Valid sham**: needs the trial `brief_log` 2026-09-08..09-20 from the production host
   (authorization pending). Everything else for it is in hand — served corpus, `rowid`
   cut, shams redrawn from the 108-pool (89 non-designated) — and `gera-shams.py` /
   `roda-sham.sh` must first be fixed, since both hard-code the preserved corpus and
   `--corte inclusivo` (§4.0.1c).
10. **Ballast gap**: add `ITT-SENSIB-PRECOMPROMETIDA.json` and the artifacts marked † in
    Appendix B to `MANIFESTO-LASTRO-P2.json` and to both verified copies.
11. **Traceability of §4.7 and Figure B1**: save the `control` distribution (the 9.991)
    and the seed recipe of the 2 000-seed run in an artifact, or cite the 20 000-seed
    crosscheck instead; regenerate the B1 SVG headline.

⚠️ Items 2 and 3 are **registered analyses that were not run**, not enhancements. A
manuscript that omits its own pre-registered inference test and its own instrument
controls is not ready, and the fact that three adversarial reviewers had to tell us is
itself the §6 pattern repeating on this document.

---

## Changelog — v2 (2026-10-04)

Prepared from `MANUSCRIPT-B.md` as of 2026-10-03, in `_sprint-2026-10-04/B-v2.md`; the
original is untouched. Every content change below traces to a sprint report with its
artifacts; old text that was wrong is kept struck through beside its correction, as this
manuscript already does.

**Sham / replay fidelity** (source: `_sprint-2026-10-04/B-replay-fidelity.md` and
`B-replay-fidelity/`):

1. §4.0.1b table, specificity row: "running since 2026-09-22 01:40Z" struck → "not
   executed; the configuration launched was invalid; a valid one is runnable and not yet
   run".
2. §4.0.1b: the "🔄 It is now running" paragraph struck, with a correction note; the
   bullets on the 30-day pool and on the "two routes, one number" control annotated — both
   routes read the same, wrong corpus, so their agreement could not catch it (served pool
   108, not 115).
3. §4.0.1b limitation: the sentence calling `corpus-preservado-20260908.db` "the
   deliberately preserved corpus of the trial" struck and corrected — it is not the corpus
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
8. §4.3: H1's pre-committed leg added (−15.59, CI [−22.43; −4.05], excludes zero) — same
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
