---
title: "Writing rules for agent memory with two extractor models: a paired extension"
author: "Luiz Antonio Busnello"
---

Status: working draft, not deposited, not peer reviewed. A research note on one public benchmark,
with one run on 2026-11-08 under a public pre-registration. Every number with a decimal, a
percentage or a thousands separator has an entry in `PROVENANCE.json`.

## Abstract

An agent memory system turns past conversations into short memories with a language model, the
extractor, guided by a writing criterion: a prompt that says what to keep. In an earlier study on
LongMemEval, a rule-based criterion (C2) beat the deployed one (C0) by +24.8 points of answer
accuracy, with one small extractor, `gemini-2.5-flash-lite`. Here we ask whether that advantage
changes with another extractor, `gemini-2.5-flash` with thinking off, the larger model of the same
family and generation. We ran C0, C2 and a third prompt (P), which drops C0's lists of what to keep
and states what the memories are for, with both extractors on the same 242 questions. Every memory,
answer and grade was remade, under a pre-registration frozen before any paid call of the run.

Both controls passed. The pre-registered interaction, the change in the C2 advantage from
flash-lite to flash, was −4.1 points (95% interval −12.3 to +4.1; second judge −5.0, −13.4 to
+3.5): inconclusive. As secondary contrasts, C2 beat C0 by +21.1 points with flash (+14.8 to
+27.4), and by +25.2 with flash-lite, close to the earlier +24.8 on the same questions. P beat C0
with both extractors, and with flash it scored 3.7 points below C2 (−9.4 to +1.9). The comparison
is between two configured models under one reader: it does not isolate extractor strength, and an
inconclusive result here says nothing about a much larger model.

## 1. Question

The extractor reads a block of conversation and returns a few memories with an importance score.
A reader later answers questions from those memories alone. The deployed criterion, C0, lists kinds
of things to keep (decisions, preferences, lessons, project context) and things to ignore. C2 adds
two paragraphs of rules: copy identifiers letter by letter, keep incidental facts about the user
with their numbers, keep when an event happened as well as when it was told, and keep what the
assistant said that the user may ask back. These rules were written after reading the failures of
the small extractor. Another model might keep those facts without being told, so that the rules
matter less. A post on agent memory published by Anthropic on 2026-11-06 raised the same question
in general terms: fixed rules about what to record, or the model's own judgement.

P is a whole alternative prompt, not a pure removal of rules. It drops C0's lists of what to keep
and what to ignore, adds one paragraph saying the memories will be the only source for answering
the user's later questions, and keeps C0's output format, its category field, its importance scale
and its ceiling of 10 items. A contrast with P compares whole policies, including how much each
writes.

## 2. Design

**Instances.** The 242 LongMemEval `s_cleaned` questions of the earlier study's confirmatory run.
No untouched instance of the benchmark remains, so this is a paired extension on a reused sample,
not an independent confirmation. The earlier flash-lite results on these questions were known
(C0 0.570, C2 0.818). If they were high by chance, regression toward the mean would make the
interaction look negative, and this design cannot separate that from a real effect.

**Cells.** Each question's whole history is distilled, block by block (2,000 characters), under
each of the six extractor × criterion combinations. The reader sees all the memories of its cell.
Two control cells, one per extractor, remove the sessions that hold the answer, on 40 of the
questions. That makes 1,532 rows, each read by one reader and graded by two judges.

**Components.** The extractor request is the same for both models except the model name and, for
flash, a thinking budget of 0, so neither model reasons before writing. Nothing measured here shows
that flash extracts better with thinking off; the cost smokes counted tokens and units, not quality.
The reader (R3, `gemini-3.8-flash`), the two judges (`gpt-6-luna`, and `gemini-2.5-flash-lite` with
a separate prompt), blocking, serving and the confidence intervals are the earlier study's code,
which the runner checks byte for byte against that study's tag. The response parser accepts the
memories as an object or as a bare list; a cost smoke had shown a larger Gemini model using the
bare list in up to 25 of 40 blocks, which the earlier parser would have dropped.

**Hypothesis.** H_E1: the interaction I = E[(F_C2 − F_C0) − (L_C2 − L_C0)] is negative, where F
is flash and L is flash-lite. It is tested with judge 1 and a two-sided 95% interval,
cluster-robust over groups of questions that share an answer session. An interval below 0 confirms
a smaller advantage with flash, one above 0 a larger one, and anything else is inconclusive.
Because a negative I could also come from flash doing worse under C2, the plan registered F_C0 −
L_C0 and F_C2 − L_C2 to say which term moved. The other contrasts are secondary: intervals are
reported under both judges, no test is claimed, and there is no correction for multiplicity.

**Pre-registration and review.** The plan, runner, analysis and tests were frozen by the tag
`paper-e-prereg-v1.0` after two adversarial reviews from other model families (Codex and Kimi).
Both asked not to freeze the first draft. Their findings changed the design:

- every flash-lite memory is remade in the run instead of reused from the earlier study;
- a positive control was added for flash-lite;
- the lock covers every file of the run and the earlier study's modules;
- the analysis refuses an incomplete row set;
- the cap is checked before each call.

The runner refuses its paid phases unless the tag exists and every file matches it. Two cost
smokes and a batch test, on questions the earlier study had already spent and with no reader or
judge, cost US$ 2.10 before the tag.

**Power.** Under stated assumptions, 242 questions detect with 80% power a drop of 9.4 to 12.2
points in the C2 advantage, depending on how the two extractors' errors correlate.

## 3. Run

The 420,402 distillations went through 22 batch jobs on the Gemini Batch API, plus a sync retry
for the 882 answers the batches returned in an unusable form. After the retry, 432 blocks (0.10%)
stayed failed and were served empty; no extractor × criterion passed the registered 1% flag (table
in §4). The prepaid API credit ran out four times. Each time the run resumed from its own cache, so
nothing was paid twice, and no registered step changed. Every one of the 1,532 rows finished
normally. The runner's ledger at list price is US$ 150.55, under a cap of US$ 160; the provider's
invoice was not reconciled against it at the time of writing. No row was read for its outcome until
all of them existed.

## 4. Results

**Controls.** The floor required both extractors to answer at least half the questions under C2:
flash scored 0.793 and flash-lite 0.806. The positive control required at most 4 of 40 correct
answers without the answer sessions: both scored 0.000. Both passed, so the primary is interpreted
under the registered rule. The positive control is an operational threshold on 40 questions. It
does not estimate a population rate, test leakage in the other cells, or check the reader's
sensitivity to changed facts.

**Primary.**

| | estimate | 95% interval |
|---|---|---|
| judge 1 | −4.1 points | −12.3 to +4.1 |
| judge 2 | −5.0 points | −13.4 to +3.5 |

The interval contains 0, so H_E1 is not confirmed. Inconclusive does not mean equal advantages: the
judge 1 interval runs from a drop of 12.3 points to a gain of 4.1.

**Secondary contrasts** (points, 95% intervals):

| contrast | judge 1 | judge 2 |
|---|---|---|
| C2 − C0 with flash | +21.1 (+14.8 to +27.4) | +19.4 (+13.1 to +25.8) |
| C2 − C0 with flash-lite | +25.2 (+18.8 to +31.6) | +24.4 (+17.7 to +31.1) |
| flash − flash-lite under C0 | +2.9 (−3.5 to +9.3) | +6.6 (+0.1 to +13.2) |
| flash − flash-lite under C2 | −1.2 (−6.4 to +4.0) | +1.7 (−3.1 to +6.4) |
| P − C0 with flash-lite | +13.2 (+7.5 to +19.0) | +13.6 (+7.8 to +19.5) |
| P − C0 with flash | +17.4 (+11.1 to +23.6) | +14.5 (+8.7 to +20.2) |
| P − C2 with flash | −3.7 (−9.4 to +1.9) | −5.0 (−10.1 to +0.1) |
| P interaction, (F_P − F_C0) − (L_P − L_C0) | +4.1 (−4.3 to +12.6) | +0.8 (−7.0 to +8.7) |

**Per cell** (judge 1 accuracy, abstention rate, median characters served to the reader):

| extractor | C0 | C2 | P |
|---|---|---|---|
| flash-lite | 0.554, 0.289, 142,450 | 0.806, 0.099, 231,304 | 0.686, 0.198, 222,106 |
| flash | 0.583, 0.260, 104,243 | 0.793, 0.083, 175,468 | 0.756, 0.153, 234,388 |

**Failed blocks and memories written** (per block, over 70,067 blocks per cell):

| extractor | C0 | C2 | P |
|---|---|---|---|
| flash-lite | 0.08% failed, 2.63 memories | 0.06%, 4.18 | 0.42%, 4.24 |
| flash | 0.01%, 2.03 | 0.01%, 3.13 | 0.02%, 4.22 |

Accuracy per question type is in `RESULT.md` and `runs/confirm-2026-11-08/analysis.txt`, which
belong to this note's record.

## 5. What the result says

With flash, C2 kept an advantage over C0: +21.1 points, with a lower bound of +14.8 under judge 1.
Whether that advantage differs from flash-lite's is the primary question, and it stays open. A new
run on the same questions, with every memory, answer and grade remade, gave +25.2 points for C2
over C0 with flash-lite, similar to the earlier +24.8. Because the questions are the same, this is
a repeat of the measurement, not an independent replication.

The interaction is the difference of two changes: −1.2 points under C2 minus +2.9 under C0, under
judge 1. In the point estimates most of the small negative value comes from C0, but both intervals
include 0 and allow changes in either direction. A gain under C0, a loss under C2 and sampling noise
remain unresolved. Flash wrote fewer memories than flash-lite under C0 (2.03 per block against
2.63) and served the shortest material of any cell. One reading, not established here, is that
flash keeps some of what the rules ask for without being told.

P beat C0 with both extractors, by +13.2 points with flash-lite and +17.4 with flash. With flash it
scored 3.7 points below C2, and the interval (−9.4 to +1.9) allows a deficit of more than 9 points
as well as a small gain. The data show P neither below C2 nor equal to it. Because P changes several
things at once, this does not say which part of it does the work; separating them would need
further prompts and a control for how much each one writes. The P interaction was also
inconclusive.

## 6. Limits

- The questions were already used by the earlier study (§2).
- Flash and flash-lite are whole configured models. They differ in size, but also in how they
  follow a prompt, how they score importance and how much they write. The comparison is between
  these two configurations, not a measure of extractor strength. Thinking budget and model family
  were not varied, and the inconclusive result at this step says nothing about a much larger model.
  `gemini-2.5-pro` was priced for this design at US$ 380 to 1,370 and dropped.
- One reader, a Gemini model, answers every question, and both extractors are Gemini too. The reader
  may favour one extractor's way of writing. The two judges grade the answers of that same reader,
  so they do not replicate the result across readers. Their contrasts differ in sign only on flash
  − flash-lite under C2, where both intervals contain 0.
- The intervals are conditional on one draw of the distillations, and they do not include the
  dependence between questions whose histories share blocks: one distillation serves every
  question that contains its block.
- One benchmark. The prompts are in Portuguese and the conversations in English. C2 and P were
  written by the author; neither is a neutral sample of possible criteria.

## Data and code

`paper-e-extractor/` in the repository: the pre-registration, runner, analysis and tests at tag
`paper-e-prereg-v1.0`; the run's rows, receipt and analysis in `runs/confirm-2026-11-08/`
(`e-analyze.py --check` reproduces the analysis byte for byte); the result in `RESULT.md`; the
reviews of the plan and of this note; the cost smokes in `SMOKE-RESULT.md`. The benchmark is public;
no private data was used.
