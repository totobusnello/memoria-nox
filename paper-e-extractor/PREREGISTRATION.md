# Paper E pre-registration: writing criterion × extractor model

Status: draft v1.1, not frozen. It is frozen by the tag `paper-e-prereg-v1.0`. The runner refuses
the paid phases until that tag exists, until every file it runs, this one included, matches the
tag byte for byte, and until the Paper 3 modules it imports match `paper3-prereg-v1.3`.

v1.1 follows a Codex review of the v1.0 draft (`review-codex-prereg.md`). §12 lists what changed.

## 1. Question

Paper 3 (DOI 10.5281/zenodo.23934489, v1.3) found that a rule-based writing criterion, C2, beats
the deployed criterion, C0, by +24.8 pp (judge 1; +27.3 under judge 2) when the whole history is
distilled. Every distillation there used one extractor, `gemini-2.5-flash-lite`, and the manuscript
lists that as a limit. This study asks whether the C2 advantage depends on the extractor: is it
smaller when the extractor is `gemini-2.5-flash`, the larger model of the same generation and
family? A third criterion, P, states what the memories are for and lists no rules about what
to keep.

**Estimand.** The interaction between extractor and criterion, for these two configured models
(§3.2), on these instances, under this reader and these judges. If the advantage shrinks, model
strength is one possible explanation, and it stays a hypothesis: the two models also differ in
prompt following, importance calibration and verbosity, and the design does not separate those.

## 2. Design

**Instances.** The 242 of `paper3-construction/v13-manifest.json` (sha256 `f9c7df69…`). No
untouched LongMemEval `s_cleaned` instance remains (500 − 30 abstention − 8 smoke − 200 stage 1
− 262 confirmatory = 0). Paper 3 read these 242 with the flash-lite extractor, so its C0 and C2
results on them are known: 0.570 and 0.818, judge 1. This study is therefore a paired extension
on a reused sample, not an independent confirmation. In particular, it was motivated by an
advantage already observed on the same instances. If that observation was high by chance,
regression toward the mean would push the interaction negative, and this design cannot separate
that from a real interaction.

**Cells.** The full window (every session of the haystack) in all main cells.

| cell | extractor | criterion | instances |
|---|---|---|---|
| L_C0, L_C2, L_P | `gemini-2.5-flash-lite` | C0, C2, P | 242 |
| F_C0, F_C2, F_P | `gemini-2.5-flash` | C0, C2, P | 242 |
| L_C2_pos, F_C2_pos | each extractor | C2, answer sessions removed | the 40 of `control_subsample` |

1,532 rows. Everything is made in this run, and the same code path serves both extractors:
distillations (Batch API, then a sync pass for what the batches did not return), answers and
grades. Nothing is carried over from Paper 3.

## 3. Components

**3.1 Unchanged from Paper 3.** These are imported from `paper3-construction/lme-run.py`, and the
runner checks that the file equals its copy at tag `paper3-prereg-v1.3`:

- blocking: 2,000 characters, per session, with the noise filter;
- serving: the units of the cell's sessions, importance descending, then recency;
- the question text;
- reader R3: `gemini-3.8-flash`, prompt B, thinking low;
- judge 1: `gpt-6-luna`, Decisions API, correct ⇔ P(contem) > 0.5;
- judge 2: `gemini-2.5-flash-lite`, with the family-2 prompt;
- the cache keys of the reader and the judges.

The confidence intervals come from `lme-analyze.py` at the same tag, under the same check.

**3.2 Extractors.** The request body is Paper 3's distill body: the criterion prompt, then
`"\n\nConversa:\n"` and the block, with `responseMimeType: application/json` and temperature
0.1. `gemini-2.5-flash` adds `thinkingConfig: {thinkingBudget: 0}`, so it runs with thinking off,
as flash-lite does by default. Both share the same family and generation. Nothing measured here
establishes that flash extracts better with thinking off: the smokes counted cost and units, not
quality. `gemini-2.5-pro` was priced and dropped: US$ 380 to 1,370 for this design
(`SMOKE-RESULT.md`).

**3.3 Criteria.** C0 and C2 are Paper 3's, byte for byte (sha256 `72208f90…` and `325342a3…`).
P (`e_prompts.py`, sha256 `9e7668b2…`) is C0's header, then this paragraph, then C0's output
contract unchanged (JSON format with its category field, importance scale, "Retorne [] se não
houver nada relevante", at most 10 items):

> As memórias que você extrair serão, mais tarde, a única fonte de um assistente que vai responder
> perguntas do usuário sobre o que ele contou e sobre o que foi dito nesta conversa. A conversa em
> si não estará mais disponível. Decida você, pelo conteúdo desta conversa, o que precisa ser
> guardado para que essas perguntas possam ser respondidas.

P was written before any call that used it. It is a whole prompt, not a pure ablation of rules.
It drops C0's lists of what to keep and what to ignore, adds the use of the memories, and keeps
the category field, the importance scale, the filter and the ceiling. Like C2, it is written for
this task. A contrast involving P compares prompts as whole policies, including how many units
each produces. The analysis reports units per block per cell (§6) for that reason.

**3.4 Parser** (`parse_memories`). A response is valid if it parses as JSON and is either an
object whose `memories` is a list, or a top-level list. Inside a valid list, an item is kept if
it is an object with a string `text` and a numeric, non-boolean `importance` ≥ 0.5; other items
are dropped. Anything else is a failed block, including `{}` and a `memories` that is not a
list. Paper 3 accepted only the object form. The smoke found `gemini-2.5-pro` using the list form
in up to 25 of 40 blocks, and `gemini-2.5-flash` in 0 of 120 (`SMOKE-RESULT.md`). The parser is
the same for both extractors, and both are distilled fresh with it.

## 4. Hypotheses

**Primary, H_E1.** I = E[(F_C2 − F_C0) − (L_C2 − L_C0)] < 0: the C2 advantage is smaller with
`gemini-2.5-flash`. It is tested with judge 1, two-sided 95% interval:

- hi < 0: H_E1 is confirmed for this contrast: the advantage is smaller with flash;
- lo > 0: the advantage is larger with flash, reported as such;
- otherwise inconclusive. An interval containing 0 is not evidence of equal advantages.

The verdict is statistical only. A negative I can arise in two ways: flash raises C0 (the two
criteria converge from below), or flash lowers C2. These have different readings, so the result
reports F_C0 − L_C0 and F_C2 − L_C2 beside I and says which term moved. A negative I is not read
as "the stronger model no longer needs rules" unless F_C0 − L_C0 > 0.

**Secondary.** Intervals under both judges. No test is claimed and there is no multiplicity
correction. The contrasts are:

- F_C0 − L_C0 and F_C2 − L_C2;
- F_P − F_C2;
- the P interaction, (F_P − F_C0) − (L_P − L_C0);
- L_P − L_C0, F_P − F_C0 and F_C2 − F_C0;
- L_C2 − L_C0, beside Paper 3's +24.8 pp.

## 5. Controls

Both gate interpretation of the primary. If one fails, the primary is not interpreted, and the
result names the failed control without attributing its cause.

- **Floor:** acc(F_C2) ≥ 0.50 and acc(L_C2) ≥ 0.50, judge 1.
- **Positive:** acc(L_C2_pos) ≤ 0.10 and acc(F_C2_pos) ≤ 0.10 (at most 4 of 40 each), judge 1.
  With the answer sessions removed, the reader should not find the answer in either extractor's
  memories. This is an operational threshold on 40 instances, not an estimate of a population
  rate. It does not test leakage in the other cells, nor the reader's sensitivity to changed
  facts (Paper 3's counterfactual control is not repeated here).

## 6. Analysis

`e-analyze.py`, as frozen at the tag. No other analysis counts as confirmatory.

- It refuses to analyze unless the rows are exactly the design: one row per (instance, cell),
  242 × 6 main cells plus 40 × 2 control rows. Rows that are missing, duplicated or unexpected
  stop it.
- Per-instance contrasts are averaged. Their standard errors are cluster-robust (CR1) over
  answer-session groups, using Paper 3's `clusters` and `cluster_mean_ci`.
- Judge 1 is primary and judge 2 is the bracket, as in Paper 3 §11.5 item 9.
- From `receipt.json`, it reports failed blocks and kept units per block for each extractor ×
  criterion. It flags any extractor × criterion with more than 1% failed blocks.
- It describes accuracy, abstention and served length per cell, and accuracy per question type.
- `--check` reproduces `analysis.txt` and `analysis.json` byte for byte.

## 7. Power

An approximation under stated assumptions. From the 242 Paper 3 rows, the flash-lite difference
d = Y(L_C2) − Y(L_C0) has variance 0.228 (judge 1). Assume the flash difference has the same
variance and correlation ρ with it, and treat instances as independent. In Paper 3 the 242
formed 241 answer-session clusters, so clustering changes little. Under these assumptions, a
paired test at α = 0.05 with 80% power detects, on 242 instances, a shrinkage of:

| ρ | detectable shrinkage |
|---|---|
| 0 | 12.2 pp |
| 0.2 | 10.9 pp |
| 0.4 | 9.4 pp |

A 10 pp shrinkage is detectable only if ρ is about 0.32 or more; at ρ = 0 it would need 358
instances. (Variance 0.228 is the population variance of the 242 differences, 0.22778; with the
rounded 0.228 the 15 pp, ρ = 0 entry of `SMOKE-RESULT.md` would read 160 instead of 159.)

Other sources of dependence are not in the standard errors:

- the stochastic draw of each distillation;
- blocks shared between haystacks: one distillation serves every instance that contains its
  block.

The intervals are conditional on one realisation of the distillations. The step from flash-lite
to flash is smaller than the step to pro, so an inconclusive result would not rule out a
shrinkage at a larger step.

## 8. Procedure

1. Tag `paper-e-prereg-v1.0` on a commit where `e-test.py` passes. The runner's freeze list
   (`FROZEN`) is `e-run.py`, `e_prompts.py`, `e_batch.py`, `e-analyze.py`, `e-test.py` and this
   file. The runner also checks Paper 3's `lme-run.py` and `lme-analyze.py` against their tag,
   and the dataset's sha256 against the manifest.
2. Distill with `distill --via batch --wait` on the Batch API, at half price.
   - Each chunk holds at most 20,000 requests. Its display name carries a random identity of the
     run directory, so no other run's batch is ever adopted.
   - A chunk is recorded as soon as it is created, and a restart never resubmits a recorded
     chunk. If a process dies between creating a chunk and recording it, the next process adopts
     the chunk by its display name.
   - Re-ingesting a chunk charges nothing.
   - If the provider refuses a chunk for its queue quota (HTTP 429), the chunk waits for a later
     pass; any other creation error stops the run.
3. Run `distill --via sync` at the standard price on what the batches left: requests that
   returned an error or no line, expired chunks, and answers that were invalid under §3.4. Each
   gets one sync attempt, after the HTTP retries of Paper 3's `post`. A block that still fails is
   recorded as failed and served empty. The receipt counts failed blocks per extractor ×
   criterion.
4. Run `read`. It refuses while any block lacks a final distillation. Then run `e-analyze.py`.
   No row is read for its outcome, and the analysis does not run, until all 1,532 rows exist.

**Cap.** US$ 160, cumulative across the processes of one run directory, from the token counts
the API returns. Sync calls and reads check the cap before each call, so it can be passed only by
calls already in flight (at most `--workers`). Batch chunks are held while the estimated cost of
the chunks in flight plus the next one would pass the cap. The ledger is the runner's estimate at
list price; the provider's bill is the real cost, and the result reports both. The estimate is
about US$ 79 for distillation in batch and about US$ 43 for reading and both judges.

## 9. Deviations

Any change after the tag is a numbered deviation in the result document, with its reason and its
effect on the numbers where it can be computed.

## 10. What was seen before the tag

- Two cost smokes (`SMOKE-RESULT.md`): 40 blocks from the haystacks of the 200 spent stage-1
  instances, none from the 242. They kept token and unit counts only and ran no reader, judge
  or question.
- A shape probe of 24 failed `gemini-2.5-pro` calls, keeping only the JSON shape.
- `batch-test`: the batch path on 30 other spent blocks, criterion P on both extractors.
- The Codex review of the v1.0 draft (`review-codex-prereg.md`) and the Kimi review
  (`review-kimi-prereg.md`).
- Spend on Paper E before the tag: US$ 2.10 (`README.md`).

## 11. Limits known now

- The corpus is a single one, LongMemEval `s_cleaned`, and these 242 instances were already used
  by Paper 3 (§2).
- The reader R3 and judge 2 are Gemini, like both extractors. A reader of the same family may
  favour one extractor's way of writing; the bracket across judge families does not address
  that. Levels are read with that caution, and the contrasts are reported under both judges.
- The prompts are in Portuguese and the conversations in English, as in Paper 3.
- P and C2 were written by the authors; neither is a neutral sample of possible criteria.
- The model changes as a whole: thinking budget, family and memory budget are not varied, and
  the number of units each prompt produces is not controlled.

## 12. Changes from the v1.0 draft

| Codex finding | change |
|---|---|
| 1 "stronger extractor" not isolated | estimand stated as the interaction for two configured models; strength kept as a hypothesis (§1, §3.2) |
| 2 historical vs new extractions | Paper 3's flash-lite distillations are no longer reused; all six cells are distilled in this run through one path (§2) |
| 3 reused sample | stated as a paired extension, with the regression-to-the-mean caveat (§2) |
| 4 shrinkage by F lowering C2 | F_C0 − L_C0 and F_C2 − L_C2 registered and reported beside I; statistical verdict separated from interpretation (§4) |
| 5 tag lock covers three files | the lock covers every file run, this document, Paper 3's modules at their tag, and the dataset hash (§8) |
| 6 analysis accepts partial rows | the analysis refuses anything but the exact design (§6) |
| 7 failures not retried or reported | invalid batch answers get the sync pass; final failures are recorded and served empty; failures per extractor × criterion reported and flagged over 1% (§6, §8) |
| 8 cap not hard; re-ingest double counts | cap checked before each sync call and read; re-ingest charges nothing; ledger vs bill stated (§8) |
| 9 P is not a pure ablation | described as a whole prompt; units per block reported (§3.3) |
| 10 parser contract | `{}` and non-list `memories` are failures; boolean importance and non-string text dropped; the 0.06% remark removed with the reuse (§3.4) |
| 11 controls | positive control added for flash-lite; a failure blocks interpretation without attributing cause (§5) |
| 12 power vs cluster-robust test | stated as an approximation; cluster count and unmodelled dependence named (§7) |
| 13 batch adopted by name only | display names carry the run directory's identity (§8) |

The Kimi review of the same draft (`review-kimi-prereg.md`) found the cap, the sync failures, the
failure report and the parser cases also listed above, and two roundings, fixed in §7. It recomputed
every cost, projection and power figure and found them consistent.

Not peer reviewed.
