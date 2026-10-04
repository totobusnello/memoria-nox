## 4. Results

**Estimator.** `estimador_itt.py`, which is **composition, not reimplementation**: it
imports `carregar_verdicts`, `carregar_episodios` and `span_por_sessao` from the pilot's
replay module and the arm from the assignment file. Two copies of one rule silently
populate different populations, and that is a defect class this project has already paid
for once.

**Adjudication.** 1 195 episodes, 395 in stratum A (census of `is_error`) and 800 in stratum B
(hash-ordered sample), were adjudicated by **three** model families from distinct training
lineages, as locked in PREREG §682. Coverage 100%. Horvitz-Thompson weight for stratum B:
**6.945** (5 556 / 800). Strict majority; a 2-2 tie resolves to `not_failure`, which
`pilot_replay.py` l.145-148 declares as *"conservative: it underestimates failures"*.
That is **directional bias toward the null**, not indeterminacy, and it is the direction
that makes a null easier to obtain.

**The combined estimator, written out.** The first draft omitted it, and without it a
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

### 4.0.1 Two registered analyses we did not run, declared as deviations

Both were found by adversarial review of this manuscript, not by us.

**(a) The registered inference test is re-randomization, not bootstrap, and we have now
run it.** §4 of the analysis spec locks **10 000 re-randomizations**, *"redesign the 234,
never permute within the 20"*, over the trend-residualized outcome. The first draft
reported cluster bootstrap and **did not declare the substitution**. That was the worse
half of the error: the bootstrap assumes an iid draw of epochs, whereas the design
randomizes with stratification and exact controlled rounding, so its reference
distribution is **not the one the design generates**.

`rerandomizacao.py` imports `assign_arms.assign` and redesigns all 234 epochs per
replicate, restricting to the window; it never permutes labels among the 20, which the spec
pre-commits against because the 20 fall entirely in the first calendar half, where the
stratification collapses. **Control: 300 distinct arm patterns in 300 replicates**, which
reproduces the spec's own measurement of zero collisions; at 10 000 it is 9 941 distinct.

### 4.0.2 The registered test disagrees with the bootstrap on H1a

| outcome | re-randomization *p* (registered) | reject sharp null at 5%? | what the bootstrap said |
|---|---:|---|---|
| **H1c** (primary) | **0.1603** | no | contains zero — **agree** |
| **H1a** | **0.0855** | **no** | excluded zero — **disagree** |
| `H1` | **0.0127** | yes | excluded zero — agree |

**Different estimand, stated so the numbers are not compared naively.** The permutation
statistic is a difference of arm means over per-epoch outcomes residualized on study-day;
the ITT of §4.1 is a ratio of weighted totals. They answer related questions, not the same
one, and the observed statistic here (−0.0323 for H1c) is **not** the −0.0199 of §4.1.
What transfers is the verdict, not the magnitude, and the registered scope is narrow by
construction: this tests the sharp null of *zero total effect*, and rejection alone does
not attribute magnitude.

**What this settles, and it is not in our favour rhetorically.** §4.2 argued that H1a
"does not bear weight" from the sparse-session mechanism. The registered test reaches the
same verdict by a route that does not need that argument at all, and in doing so shows
that the bootstrap interval which *excluded* zero for H1a was the artifact, exactly as
§4.1.1 predicts an under-covering interval would behave. We would rather have found this
before an adversarial reviewer told us the test was missing.

`H1` rejects under both. It remains excluded from interpretation for the reason of §4.3
(the effect it would imply is outside what the mechanism can produce), and that reason is
now the *only* one standing, since the inference no longer supports dismissing it as a
bootstrap artifact. **We report it as an unexplained rejection**, which is the honest
category for a result that survives the registered test on a hypothesis whose magnitude
the design rules out.

Artifact: `RERANDOMIZACAO-2026-09-21.json`; seed prefix `p2-rerand-2026-09-21` declared.

**(b) The pre-committed instrument controls: two run, one not runnable.** §5 of the spec
defines three. The first draft reported none, which for a paper whose stated contribution
is *"the reportable results are about instruments"* was the worst omission in it.

**Caveat.** The spec measured the first two on **2026-09-10, with the trial still running**: 6/6
and 3/3 over a partial window. We re-measured over all 20 epochs, because a control
measured midway does not cover what came after.

**Semantics, declared before the numbers:** `mexeu` compares `ids_tratado` with
`ids_controle` by **membership** (`set`), never as a list. List comparison mixes reordering
with entry/exit and at epoch `09-08` returns 48 against 20.

| control | statement | result |
|---|---|---|
| **positive** | a served treatment epoch has `mexeu > 0` | **passed, 11 / 11** (was 6/6 at midpoint) |
| **negative dual** | a control epoch has `sem_ids == n` | **passed, 8 / 8** (was 3/3) |
| **specificity (sham)** | replay 19 non-designated chunks at the same `w` | ~~running since 2026-09-22 01:40Z~~ **not executed** — the configuration launched was invalid; a valid one is runnable and not yet run (§4.0.1c) |

The positive control ranges from **2.83% to 6.85%** of briefs altered per treatment epoch
(`09-09` lowest, `09-14` highest). Had any treatment epoch returned 0, **the null would be
the instrument's and not the effect's**. That is the whole purpose of the control, and it
is the reason the null of §4.1 can be read as being about the treatment at all.

The negative dual is stated that way for a reason the spec works out and we repeat: the
obvious form, *"a control epoch has `mexeu == 0`"*, is **invalid**, because at `w=0` the
`ids_*` fields do not exist at all, so `mexeu == 0` is indistinguishable from *"the field
was never written"*. A predicate that needs the data that is missing does not cover the
data being missing.

**The specificity control was not run, and our first attempt at it was invalid.** We
counted how many briefs contain a sham chunk in `ids_tratado` and compared against the
designated set. It returned real 2 069 against a sham median of 5 832 and read as a
**failed instrument**. The failure was the test's. `ids_tratado` is **post-dose**, so
counting presence inside it is the candidate the spec's own table already labels
*tautological*; with a universe of 141 ids, the non-designated set includes the chunks
that enter nearly every brief, while the designated are one per signature group and
therefore rarer. The quantity measured is **chunk frequency**, not specificity.

The pre-committed sham is a **replay**: re-execute the dose mechanism with 19
non-designated chunks at the same `w` and compare the churn it produces. That requires
running the serving code, not reading its log, because the log only contains the outcome of the
designation that actually ran. It was **declared as not run rather than reported as
failed**, which is the difference between the two that the near-miss above exists to make.

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
  randomization p-value is `1/21 = 4.8%`; with fewer shams the test cannot reject at 5%
  no matter what it finds.
- **The shams are drawn from the eligible pool, not from the corpus.** A sham chunk that
  fails the eligibility predicate never reaches the candidate list, so it would "not move"
  **by construction**, and the test would report specificity where there was only
  ineligibility. That is the mirror image of the tautological candidate the spec rejects,
  and it is why `gera-shams.py` applies the 30-day window as well as the path and floor
  predicates. *(2026-10-04: the principle stands; the pool it was applied to did not. See
  §4.0.1c: `gera-shams.py` drew from the 115-chunk pool of a corpus that did not serve
  the trial; the served pool has 108.)*
- **The predicate has an independent control.** Our SQL with the age window returns
  **115** eligible chunks, and the replay independently *observes* `pool: 115` at the same
  `t-ref`. Two routes, one number; without that agreement we would not know whether the
  pool we sample from is the pool the mechanism sees. *(2026-10-04: both routes read the
  same corpus, `corpus-preservado-20260908.db`, so their agreement could not detect that
  the corpus itself was the wrong one. On the corpus that served the trial the pool is
  **108** in 22/22 measured states; see §4.0.1c.)*

**One limitation, declared.** The corpus of the published anchor
(`e20260826T060003Z.db`) **no longer exists**; it was pruned. ~~This runs on
`corpus-preservado-20260908.db`, the deliberately preserved corpus of the trial, so it
cannot reproduce the published anchor and does not try to: the comparison is internal,
real against sham on **one** corpus, which is what specificity needs.~~

**Correction (2026-10-04).** The struck sentence is factually wrong on two counts.
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
failure. This is a **prediction** from the measured strata and that arithmetic; no sham
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
intervals reported here are, if anything, optimistic, and the primary result is a null
that survives them being optimistic.

### 4.1 H1c: the primary outcome, null and undetectable

| leg | treatment | control | difference | 95% CI | |
|---|---:|---:|---:|---|---|
| **locked (all 20 epochs)** | 0.0696 | 0.0896 | **−0.0199** | [−0.0560; +0.0086] | contains zero |
| **pre-committed sensitivity** — all partials removed | 0.0721 | 0.0994 | −0.0273 | [−0.0725; +0.0061] | contains zero |
| post-hoc sensitivity — without `09-14` | — | — | −0.0244 | [−0.0619; +0.0051] | contains zero |

**Which sensitivity is the registered one, and our error in the first draft.** §9.1 of
the analysis spec pre-commits *"the standard sensitivity that removes **all** the partials
as a block"*: `09-01`, `09-03`, `09-20`. The first draft of this paper reported instead a
sensitivity that removes `09-14`, which was **chosen after seeing that one epoch dominates
exposure** and was never pre-committed. Both are now reported, the registered one first
and labelled as such. We state the direction: the pre-committed leg is *more*
favourable to our reading than the post-hoc one we had picked, so the substitution gained
us nothing. That makes it a process failure rather than a self-serving one; it does
not make it less of a failure.

This is the stable outcome of the study, and all three legs agree.

### 4.1.1 Our two uncertainty estimates contradict each other

§3 of the analysis spec pre-commits this sentence:

> *"Under the realized inclusion criterion and `ICC = 0.0985`, **not even total
> elimination of repeated failures is detectable at 80% power**."*

Control sits at `H1c = 0.0896`, so "total elimination" is an effect of **−0.0896**. For
that sentence to hold, an interval must be unable to separate −0.0896 from 0: it would
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

**Caveat.** This also disciplines §4.3: an interval "excluding zero" on H1 or H1a is a claim made
with the same under-covering machinery, which is a further reason, independent of the
denominator argument, not to read those as findings. **The caveat applies to every
interval here, including the null one, and not only where it is convenient.** The first
draft attached it only to H1; an adversarial reviewer pointed out that a method cannot be
optimistic selectively.

**The under-powering is structural, not bad luck.** With 19 analyzable clusters there
is no effect size in the registered parameter space that this design distinguishes from
zero. Reporting the interval without that sentence would be the exact defect family this
project spent eight weeks documenting; the spec makes the declaration mandatory **in the
abstract, not in a footnote**, and that is where it is.

### 4.2 H1a: excludes zero only on the locked leg, and therefore bears no weight

**Correction (2026-10-04).** This section was titled *"H1a — inverts its conclusion on
one epoch"* and its table showed only the post-hoc leg that removes `09-14`. That broke
the rule §4.1 states for itself (the **pre-committed** sensitivity is reported first),
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
a session's episodes: the distance between first and last event, not time worked. A
session that acts, sleeps, and returns six hours later contributes six hours of exposure.

Measured: nineteen epochs fall between **0.32 and 0.97 h**; `2026-09-14` has **7.13 h**,
alone **56%** of all treatment exposure. The cause isolates to one session (`d37a5964…`)
with **three** episodes (one at 13:52 and two at 20:12, span 6.33 h). The sessions that
actually worked in that epoch produced 74, 65 and 56 episodes in ~~**9 to 10 minutes**~~
**8 to 10 minutes** each *(corrected 2026-10-04: measured spans 9.71, 8.86 and 8.03 min,
recomputed with the pilot's own per-session grouping for Figure B1)*.

**The artifact is not introduced by this analysis.** The function is the pilot's, so
the pilot's own `hours_per_epoch` (1.1144) carries the same property. It is a feature of
the registered definition that only manifests when an epoch contains a sparse session.

**We did not change the denominator.** Replacing it with "effective work" would be
altering a locked definition *after* seeing that it yields an uncomfortable result, and
would invalidate `r̂`, the ICC and the `N` that `sizing.py` derived from them.

**But that cuts both ways, and we did not say so in the first draft.** If the exposure
measure counts idleness, then `r̂`, the ICC and the sample size derived **from that same
measure** inherit the defect. The power calculation that tells us this study is
under-powered was computed on a denominator we are now calling artifactual. We do not know
the direction: a denominator inflated by sparse sessions could have made the pilot's event
rate look lower than it is, which would have **over**-sized the study, or the reverse. The
honest statement is that **the under-powering claim of §4.1 rests on a quantity this
section undermines**, and that resolving it requires recomputing the pilot, which is
future work, not a footnote. It does not rescue the trial either way: the realized N is 20
clusters regardless of what N *should* have been. The
sensitivity is reported alongside and **the divergence is not adjudicated in favour of
either leg**; the rule that says so was pre-committed in §2 of the analysis spec. The
line the reader must take away is ~~the sensitivity one: a conclusion that turns on one
sparse session is not a conclusion~~ that **both** sensitivity legs contain zero (the
registered one without touching `09-14`, the post-hoc one by removing it) and that the
registered test does not reject. An interval that excludes zero on the locked leg only,
on a denominator dominated by one sparse session, is not a conclusion.

![Figure B1](figures/figB1-h1a-inversao.svg)

**Figure B1. H1a's interval excludes zero only on the locked leg; its exposure
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
`episodios-ensaio-20260921.jsonl` and `ASSIGNMENT-SERVING.json` (the script aborts unless
the per-arm sums reproduce `horas_sessao` in `ITT-2026-09-21.json`); panel (b) from
`ITT-2026-09-21.json`, `ITT-SENSIB-PRECOMPROMETIDA.json` and
`RERANDOMIZACAO-2026-09-21.json`. Generated by `measurement/sprint-figB-h1a-inversao.py`.

### 4.3 H1: an interval excluding zero that is not a finding

`H1` returns **−14.62**, CI [−20.51; −4.79], excluding zero on ~~both legs~~ all three
legs (pre-committed sensitivity −15.59, CI [−22.43; −4.05]; post-hoc sensitivity without
`09-14` −9.74, CI [−16.21; −2.99]). *(2026-10-04: the pre-committed leg, from
`ITT-SENSIB-PRECOMPROMETIDA.json`, was missing here for the same reason as in §4.2; adding
it changes no conclusion of this section.)*

**Caveat.** This is **not** presented as a result, and the reason is structural, not rhetorical.

**`H1` is not an independent hypothesis. It is the product of the other two:**

```
H1  =  repeats / hours  =  (repeats / opportunities) × (opportunities / hours)  =  H1c × H1a
```

Verified on the estimates, relative error ≈ 5×10⁻⁶ in all four arm-by-leg cells; the
residue is the JSON rounding to six places, not a discrepancy. This is an algebraic
identity, so `H1` carries no information that `H1a` and `H1c` do not already carry.

**And the split falls exactly along the denominator.** `H1` and `H1a` both divide by
session-hours; `H1c` does not: it is a ratio of two counts. The two quantities that
exclude zero are **precisely the two that divide by the measure §4.2 shows to be
idleness**, and the one quantity free of that denominator is the null one. That is not a
coincidence we are asserting away; it is visible in the arithmetic above.

**What this argument does NOT do, stated because an adversarial reviewer caught us
short here.** It does not explain why `H1` still excludes zero *without* `09-14`. Removing
that epoch nearly equalizes hours per epoch across arms (0.557 treatment against 0.573
control) and `H1` remains at −9.74. So the residual gap is **not** the sparse session. It
is volume: the control arm carries **132.3 opportunities and 11.85 repeats per epoch**
against **93.4 and 6.08** in treatment.

Two readings survive that, and this design does not separate them:

1. the treatment reduces the **volume** of failure activity without moving the **rate** at
   which opportunities become repeated failures (which is what `H1c` measures, and `H1c`
   is null);
2. the arms differ in baseline volume by chance: with 20 clusters and between-epoch
   volume spanning 73 to 234 episodes, that is entirely available.

We cannot adjudicate between them, and we will not pick the flattering one. What we will
say is narrower and survives both: `H1` was **removed from primary on 2026-08-30** for
requiring a **955%** effect (`DESIGN-REVISION-2026-08-30.md` l.196, *"impossible by
construction"*), so an interval excluding zero there cannot be read as the treatment
working: the effect it would imply is outside what the mechanism can produce. And with 9
and 11 epochs the cluster bootstrap has few degrees of freedom and returns optimistic
intervals.

**We also owe a note on our own criterion.** §4.2 discards `H1a` because it turns on one
sparse session. `H1` does *not* turn on that session and is discarded anyway, on different
grounds. Applying one standard where it bites and another where it does not is how a ruler
gets chosen by its result. The grounds above are stated separately so a reader can reject
either without the other.

### 4.4 H1b: unevaluable, because two of our own locks collide

| lock | date | text |
|---|---|---|
| `Opportunity` (§3) | **2026-07-29** | *"An **executed action** `a` … for which the serving snapshot at session start contained ≥ 1 failure episode `a_past` with `sig(a_past) = sig(a)`"* |
| `H1b` (§1) | **2026-08-16** | *"An opportunity yields a repeat attempt if the **session** emits at least one action whose signature equals that of `a_past`"* |

These are different estimands. Under the July lock the opportunity **is** the action, and
the action carries `sig(a_past)` by definition ⇒ **H1b = 1.0 by construction**, and the
nesting the pre-registration calls load-bearing ceases to exist. For H1b to have content,
`Opportunity` would have to be a property of the *session*, which changes the denominator
for the **whole** family, not just for H1b.

No later document resolves it: the analysis spec does not mention H1b once.

**Correction of our own phrasing (2026-09-21, adversarial review).** We first wrote
that H1b is *"unevaluable"*. That conflates two things. Under the lock we kept, **H1b is
perfectly evaluable and equals 1.0**: it is *trivial*, not unmeasurable, and no artifact
computes it because none is needed. What is unanswerable is the **question** H1b was
written to carry. Saying "unevaluable" made a definitional triviality sound like missing
data, which is the more flattering of the two readings and the wrong one.

**We kept the July lock** (`Opportunity` is the action) because PREREG §420 records that
`r̂`, `p̂0` and the ICC were **all computed by replay under that model**, and that the
construction then locked was the one that *"keeps every locked number valid — the
alternative constructions would have invalidated them"*. Adopting the session reading now
would invalidate those three numbers and, by dependency, the `N_epochs` derived from them.

**What is lost, stated plainly.** H1b was the member of the family distinguishing *"the
treatment makes the agent stop trying"* from *"makes it try and succeed"*; §1 of the
pre-registration calls it *"the substantive one for this paper."* **That distinction is
not reportable from this study.** The loss is of mechanism, not of power: H1c was already
declared to have no possible result at the realized N, so nothing here worsens what was
known about detectability.

The reason that goes in the record is **a collision between two locks, unreconciled before
the window closed**, not "we did not measure it", and not "it came out non-significant".

### 4.5 Coverage by arm, and the pre-committed explanation it weakens

Coverage is post-randomization, so per PREREG §5 the ITT over all post-washout epochs
without coverage exclusion is the primary and is what §4.1–4.3 report. Coverage is
reported descriptively:

| | treatment | control |
|---|---:|---:|
| briefs with ≥1 designated chunk | **28.0%** (2 068 / 7 392) | **26.9%** (1 385 / 5 145) |

Across 4 324 designated-serving occurrences, **all 19 signatures were served, each at
≈5.3%**: uniform.

**This contradicts the projection the pre-commitment rests on.**
`DESIGN-REVISION-2026-08-30.md` committed in advance that a null in H1c *"does not
distinguish 'the mechanism does not work' from 'the lessons it promotes are too generic'"*,
on the grounds that **93.8%** of coverage would concentrate in the bucket signature
`Bash|shell:outro`. The realized distribution is flat. The pre-committed alternative
explanation is therefore **weakened** by the data, which is the opposite of what a
pre-commitment usually does for the party that wrote it, and is why it is reported here
rather than dropped.

**Caveat.** We record a near-miss: `boost_by_id` is **not** a coverage measure. It records
boost *calculated* for every candidate, uniformly, and reading it as coverage would have
produced a fabricated 139 650. Coverage comes from crossing the served id lists against
the designation.

### 4.6 M10: arm × coverage correlation, reported unconditionally

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

**The sign flips.** `09-20` is a control epoch with 14.6% coverage against ≈28%
everywhere else, low because the epoch is 13.86 h long, an artifact of the **clock**, not
of the arm. That one epoch moves `r` from −0.19 to +0.11. All four legs contain zero with
half-widths near 0.5: at K = 19 this correlation distinguishes nothing, and reporting only
the primary leg would have sold a sign that belongs to a truncated epoch. Correlation with
the **dose** rather than the binary arm: −0.0521.

### 4.7 The single epoch at the top dose: chance, not truncation

Only **one** of the 20 designated epochs drew `w = 7.5`, against 3.33 expected. The
explanation that writes itself, *stopping at 20 of 234 biases against the top dose*, is
mechanistic, plausible, and **false**.

Measured over **2 000 seeds** conditioned on the **same realized dates**, using the
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

**Figure B2. One epoch at the top dose is a tail draw, not a truncation effect.**
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

