# Pre-registration plan — the construction interaction. DRAFT for approval, not deposited.

> **Status.** Written 2026-10-27 after the collision check (`README.md`). **Nothing has been run
> under this plan.** It is submitted for Toto's approval; on approval it gets a Zenodo DOI *before*
> any arm executes, and the DOI goes in the paper. The exploratory run that motivated it
> (`audits/2026-10-27-*`) is cited as exploratory and never as confirmation.

## 1. The question, and why it is not settled by the literature

Four studies find that LLM-extracted memory loses to retrieval over raw turns, and conclude that the
answer is better search rather than better construction (`2601.00821`, `2609.34227`, `2610.29823`,
`2609.34160`). All four hold the extraction step at its defaults — `2610.29823` says so: *"Mem0 and
Zep run with their default extraction and retrieval, and other settings may do better."*

**H1 (primary).** The window the builder is shown and the criterion it extracts under **interact**:
the joint effect on answer accuracy exceeds the sum of the two main effects.

**H2.** With both changed, extracted memory is **non-inferior** to naive RAG over the raw transcript
at equal context budget.

**H3 (mechanism).** The interaction is concentrated in facts whose answer is an identifier — file
name, path, command, config key, numeric value — and is absent or small for facts whose answer is a
lesson or a decision.

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
| H2 | lower bound below −5 pp against naive RAG at equal budget |
| H3 | interaction as large on `lesson`/`decision` as on `identifier` |
| the whole instrument | W0C0 failing to reproduce the deployed system's accuracy within 5 pp |

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
