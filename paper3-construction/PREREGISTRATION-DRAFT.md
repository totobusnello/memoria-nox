# Pre-registration plan — the construction interaction. DRAFT for approval, not deposited.

> 🔴 **NOT DEPOSITABLE AS WRITTEN — blocked 2026-10-27.** Writing the sampling code revealed that the
> corpus cannot support §4. The window factor has variance in **12 of 194** eligible sessions and
> **8 of those 12 were already used** in the exploratory run; the `>1M` stratum holds **zero**
> sessions and `50-200k` holds **three**. §4 asks for 60 sessions, 15 per stratum. A confirmatory run
> here would re-use the sessions that generated the hypothesis.
>
> The correction is in `audits/2026-10-27-neither-cause-explains-it-alone.md`, and the choice of
> redesign is Toto's — see **§10**. Everything below §4 stands as written and is reusable; §4 is the
> part that broke.
>
> **Status.** Written 2026-10-27 after the collision check (`README.md`), and **revised the same day
> after reading `2601.00821` in full** — which took the faithfulness half off our side of the ledger
> and replaced it with a named prediction to test. H2 and H3 are the revision. **Nothing has been run
> under this plan.** It is submitted for Toto's approval; on approval it gets a Zenodo DOI *before*
> any arm executes, and the DOI goes in the paper. The exploratory run that motivated it
> (`audits/2026-10-27-*`) is cited as exploratory and never as confirmation.

## 1. The question, and why it is not settled by the literature

Four studies find that LLM-extracted memory loses to retrieval over raw turns, and conclude that the
answer is better search rather than better construction (`2601.00821`, `2609.34227`, `2610.29823`,
`2609.34160`). All four hold the extraction step at its defaults — `2610.29823` says so: *"Mem0 and
Zep run with their default extraction and retrieval, and other settings may do better"* — and
`2601.00821`, which is the closest and the one that isolates the mechanism, states the open question
as a prediction:

> *"Better extraction prompts — explicit date/time targeting, temporal attribute modeling — could
> shrink this class, **but cannot reach the unconditional retention of a verbatim store.**"*

This plan tests that prediction, and adds a factor no benchmark study can have: how much of the
conversation the builder was shown. `factorial` appears **zero** times in all four.

**H1 (primary).** The window the builder is shown and the criterion it extracts under **interact**:
the joint effect on answer accuracy exceeds the sum of the two main effects.

**H2 (the prediction).** With both changed, extracted memory is **non-inferior** to naive RAG over
the raw transcript. Pre-specified in **two budget regimes**, because the exploratory run split on
exactly this and reporting one alone would be choosing the answer:

- **H2a, equal context budget** — the memory arm truncated to the characters the deployed memory
  serves. The exploratory estimate was 48.5% against 63.6%, i.e. **the prediction holds**.
- **H2b, native budget** — the memory arm serving all the units a repaired builder produces, which
  is 2.4× the deployed volume and is what the fixed system would actually serve. The exploratory
  estimate was 63.6% against 63.6%, i.e. **the prediction fails**.

Both are reported whatever they say. A result that holds in one regime and fails in the other is the
outcome, not a problem with it.

**H3 (mechanism — identifier survival, not text survival).** `2601.00821` establishes that accuracy
tracks how much **source text** survives the store. We predict the governing quantity is narrower:
the survival of the **identifier the question asks for**. Two consequences are tested:

- **H3a.** The interaction is concentrated in facts whose answer is an identifier — file name, path,
  command, config key, numeric value — and is small or absent for lessons and decisions.
- **H3b.** Accuracy draws level **well below** full retention. Mechanical identifier-survival rate is
  measured by string match, with no judge, before any accuracy is read; the exploratory run saw
  6.6% → 12.9% against a verbatim store's 100%.

⚠️ **H3a is confirmatory of An, not novel.** That extraction loses the literal detail is already
established there (*"use type hints everywhere"* → *"the user prefers type hints"*, 14.0% against
91.0%), with a 69%/31% write-time/query-time split. H3a is included because the factorial needs it,
and it is labelled as replication. **H3b is the new claim.**

## 2. Design — 2×2 factorial, within-question

Every arm answers the **same** questions, so every contrast is paired.

| factor | level 0 | level 1 |
|---|---|---|
| **window** | the prose the builder actually saw, cut at its `processed_at` | the session's complete prose |
| **criterion** | `DISTILL_SYSTEM` as deployed | the same, plus one paragraph requiring identifiers verbatim |

Four memory arms, plus three reference arms that are **controls, not results**:

| arm | role |
|---|---|
| W0C0, W0C1, W1C0, W1C1 | the factorial |
| **oracle** — the raw window around the evidence | positive control. A question it cannot answer is a bad question and the item is dropped **before** any memory arm is read |
| **naive RAG** — BM25 and dense over raw 2000-char chunks, truncated to the memory arm's characters | the comparator for H2 |
| **replica check** — W0C0 against the memory the live system actually holds | fidelity. W0C0 must reproduce the deployed system |

Fixed across all arms, and named here so no later change is silent: extractor
`gemini-2.5-flash-lite` at temperature 0.1 with `responseMimeType: application/json`; the
**10-item ceiling**; `importance >= 0.5`; blocking at `BLOCK_SIZE = 2000` by the deployed algorithm
(which never splits a line); answerer `gemini-2.5-flash-lite` at temperature 0 with the deployed
`ANSWER_SYSTEM`, which permits `NAO SEI`; judge `gpt-6-luna` via the Decisions API with the
predicates and 4-level scale already in use.

## 3. Primary endpoint and test

**Endpoint.** Per (question, arm): the judge's `contem` probability thresholded at 0.5 — the
candidate conveys the reference fact. Pre-specified; the three-cut sensitivity (0.3/0.5/0.7) is
secondary.

**Primary test — H1.** The interaction contrast on paired data:

```
I = (W1C1 − W1C0) − (W0C1 − W0C0)
```

estimated by a logistic GLM with question-level random intercepts, `window * criterion` as fixed
effects, and the interaction coefficient's Wald test at **two-sided α = 0.05**. H1 is supported only
if the interaction term is positive and significant. **A positive joint effect with a null
interaction term refutes H1**, and that outcome is written up as such.

**H2.** One-sided non-inferiority of W1C1 against the better naive-RAG arm at equal budget, margin
**−5 percentage points**, the margin `2609.34227` used, chosen so the two studies are comparable and
not because it flatters us. H2 fails if the lower bound falls below −5 pp.

**H3.** Interaction estimated within each of `identifier` / `lesson` / `decision`, pre-declared as
**exploratory-confirmatory**: directional, with Holm correction over the three, and reported as
suggestive if only the direction holds.

## 4. Sample, and the power it buys

**Unit.** A (question, session) pair. Questions are generated from the **raw** prose by a model that
never sees any memory arm, under the deployed `DISTILL_SYSTEM`'s own criterion, and must carry a
verbatim citation that is verified by string match against the source before the item enters.

**Target n = 400 questions over 60 sessions**, stratified by final transcript prose
(<50k / 50–200k / 200k–1M / >1M), 15 sessions per stratum, drawn with a seed recorded in this plan
(**20261028**) from the 194 sessions that hold both a raw transcript and distilled chunks.

**Power.** The exploratory run gave main effects of +4.0 pp each and an interaction of +13.2 pp at
n=99. A paired interaction contrast carries roughly twice the variance of a main effect of the same
size, so n=400 gives >0.90 power for a 13 pp interaction and ~0.80 for 8 pp at α=0.05. **n=400 is
not powered to resolve an interaction below ~6 pp**, and a null at that scale will be reported as
inconclusive rather than as absence.

**Stopping rule.** Fixed n. No interim look, no extension on a near-miss. If the pipeline fails on a
session it is replaced by the next draw in the same stratum, and replacements are reported.

## 5. Exclusions, declared in advance

1. Items the **oracle** cannot answer (bad questions). The exploratory run lost 5 of 104 this way.
2. Items whose verbatim citation is not found in the source prose.
3. Sessions whose turns are under 90% timestamped — the window cut would be unmeasurable.
4. **Cron sessions** (`[cron:…]`, `HEARTBEAT_OK`), which the deployed builder filters by design.

Nothing else is excluded, and in particular **no item is dropped for being hard**.

## 6. What would falsify each claim

| claim | falsified by |
|---|---|
| H1 | interaction term not significant, or negative |
| H2a | lower bound **above** −5 pp at equal budget — i.e. An's prediction would fail where we expect it to hold |
| H2b | lower bound below −5 pp at native budget — the prediction holds everywhere and we have no accuracy result |
| H3a | interaction as large on `lesson`/`decision` as on `identifier` |
| **H3b** | accuracy drawing level **only** once identifier survival approaches a verbatim store's, which would make the mechanism text survival after all and leave An's law unrefined |
| the whole instrument | W0C0 failing to reproduce the deployed system's accuracy within 5 pp |

Note that H2a and H2b are falsified by **opposite** results, deliberately: the claim is that the
budget regime decides, so a plan that could only be confirmed by one direction would not be testing
it.

## 7. Known weaknesses of this plan, stated before the result

- **The judge is one model family.** Deterministic on this corpus (540 pairs, 0 label changes) but
  single. A blind human grading of a 60-item stratified subsample is **required** for the strong form
  of H2; without it H2 is reported as judge-only. Human grading is Toto's to schedule — and the
  grader must not be whoever built the arms, which is the limitation `2609.34227` had to declare.
- **The replica is not the deployed builder.** It omits the embedding dedup (`isDuplicate`), which
  needs the live database, and the learned noise prototypes, because `isNoise` writes to
  `noise_prototypes`. Both omissions give the memory arms **more** units, so they bias against our
  own hypothesis. The exploratory run's replica matched the deployed accuracy exactly (42.4%) in
  aggregate but missed two cells; per-cell claims therefore carry that caveat.
- **One corpus, one language, six agents.** External validity is not claimed. The window factor is
  specific to systems that build memory incrementally from live sessions.
- **The production system must not be repaired before this runs.** Fixing
  `session-distill.ts:141-144` or the prompt would destroy the W0C0 cell, which *is* the deployed
  system. Repair is sequenced after the run.

## 8. Release

Plan DOI before execution. On publication: the code, the generated questions in redacted form, the
judge keys and all per-item labels. **The corpus prose is not releasable** — it holds live
credentials this repository has already catalogued, and 2.66M characters of the user's own
conversation. The paper states plainly which numbers a third party cannot reproduce from the release
and why.

## 9. Cost

| step | estimate |
|---|---|
| distillation, 4 cells over ~60 sessions | ~US$ 1.30 |
| answering, 7 arms × 400 | ~US$ 0.80 |
| judging, ~2,800 items | ~US$ 0.25 |
| embeddings for the dense RAG arm | ~US$ 0.25 |
| **total** | **~US$ 2.60** |

Anchored on measured costs from 2026-10-27, not on list prices: 563 blocks cost US$ 0.2436, 99 pairs
over 4 arms cost US$ 0.1082, 396 judgements cost US$ 0.0318.


## 10. The redesign the corpus forces — three options, one recommendation

Added 2026-10-27 after §4 was found unexecutable.

**The binding constraint is sessions, not questions.** The unit of inference is the session: questions
from one session share its prose, its builder window and its memory. n=400 questions over 12 sessions
is not n=400. And the window factor — the one production has and benchmarks do not — varies in only
those 12.

| option | what it buys | what it costs |
|---|---|---|
| **(a) publish the exploratory run as exploratory** | honest, cheap, available today; `2610.29823` publishes on one conversation and says so | no confirmation of anything, and the interaction rests on 8 sessions |
| **(b) manipulate the window experimentally on this corpus** — truncate the prose artificially instead of using the window the builder happened to have | gives the factor variance in all 194 sessions, and makes it a manipulated variable rather than one confounded with session size | only **28** sessions hold ≥2 blocks of prose and **16** are unused; the truncated window is not the window production produces |
| **(c) two legs: production for existence, a public corpus for the estimate** | the interaction is estimated on LoCoMo/LongMemEval with the window truncated under our control — large n, reproducible **by third parties**, which also answers the release problem — while production supplies what no benchmark can: that the window occurs naturally, and its magnitude (median 24.0% seen in the 200k–1M band) | two instruments to build and validate; the public-corpus leg inherits the criticism we make of benchmarks |

🔑 **Recommendation: (c), with (a) as its production leg.** It separates the two claims by the
evidence each needs. *That the window exists and bites* is a fact about production and can only be
shown there — observationally, on 12 sessions, as an existence result with a magnitude, which is
exactly what 12 sessions can carry. *That window and criterion interact* is a quantitative claim that
needs n and a manipulated factor, and a public corpus gives both plus third-party reproducibility.

It also fixes the release problem from `README.md` §Open decisions: the confirmatory numbers would
rest on data anyone can download, and the production leg would be cited for existence, where the
unreleasable prose matters least.

⚠️ And it keeps us honest about something (b) would hide: a truncated window is **our** truncation.
Production's window is set by a 7-day prune crossed with a 30-day lookback and a 50-session-per-run
ceiling, and reproducing that shape on a benchmark is a modelling choice to declare, not a detail.
