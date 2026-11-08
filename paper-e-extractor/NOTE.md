---
title: "Do writing rules for agent memory matter less with a stronger extractor? A paired extension"
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
depends on the extractor. We ran three criteria, C0, C2 and a third (P) that only states what the
memories will be used for, with flash-lite and with `gemini-2.5-flash` (thinking off). We used the
same 242 questions and remade every memory, answer and grade, under a pre-registration frozen
before any paid call.

Both controls passed. The pre-registered interaction, the change in the C2 advantage from
flash-lite to flash, was −4.1 points (95% interval −12.3 to +4.1; −5.0 under a second judge):
inconclusive. With flash, C2 still beat C0 by +21.1 points (+14.8 to +27.4), and the earlier
+24.8 reproduced as +25.2 with flash-lite. P beat C0 with both extractors, by +13.2 and +17.4
points, and with flash it scored 3.7 points below C2, an interval that reaches 0. At this step of
model size, the rules kept most of their value. The data rule out a loss of more than about 12
points, and say nothing about a much larger model.

## 1. Question

The extractor reads a block of conversation and returns a few memories with an importance score.
A reader later answers questions from those memories alone. The deployed criterion, C0, lists kinds
of things to keep (decisions, preferences, lessons, project context) and things to ignore. C2 adds
two paragraphs of rules: copy identifiers letter by letter, keep incidental facts about the user
with their numbers, keep when an event happened as well as when it was told, and keep what the
assistant said that the user may ask back. These rules were written after reading the failures
of the weak extractor. A stronger model might find those facts without being told, so that the rules matter
less. A post on agent memory published by Anthropic on 2026-11-06 raised the same question in general
terms: fixed
rules about what to record, or the model's own judgement. Criterion P is the "own judgement" end:
it removes C0's lists and says only that the memories will be the sole source for answering the
user's later questions.

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
flash, a thinking budget of 0, so neither model reasons before writing. The reader (R3,
`gemini-3.8-flash`), the two judges (`gpt-6-luna`, and `gemini-2.5-flash-lite` with a separate
prompt), blocking, serving and the confidence intervals are the earlier study's code, which the
runner checks byte for byte against that study's tag. The response parser accepts the memories as
an object or as a bare list; a cost smoke had shown a larger Gemini model using the bare list in
up to 25 of 40 blocks, which the earlier parser would have dropped.

**Hypothesis.** H_E1: the interaction I = E[(F_C2 − F_C0) − (L_C2 − L_C0)] is negative, where F
is flash and L is flash-lite. It is tested with judge 1 and a two-sided 95% interval,
cluster-robust over groups of questions that share an answer session. An interval below 0 confirms
a smaller advantage with flash, one above 0 a larger one, and anything else is inconclusive.
Because a negative I could also come from flash doing worse under C2, the plan registered F_C0 −
L_C0 and F_C2 − L_C2 to say which term moved.

**Pre-registration and review.** The plan, runner, analysis and tests were frozen by the tag
`paper-e-prereg-v1.0` after two adversarial reviews from other model families (Codex and Kimi).
Both asked not to freeze the first draft. Their findings changed the design: every flash-lite
memory is remade in the run instead of reused from the earlier study, a positive control was added
for flash-lite, the lock covers every file of the run and the earlier study's modules, the analysis refuses an incomplete
row set, and the cap is checked before each call. The runner refuses its paid phases unless the
tag exists and every file matches it.

**Power.** Under stated assumptions, 242 questions detect with 80% power a drop of 9.4 to 12.2
points in the C2 advantage, depending on how the two extractors' errors correlate.

## 3. Run

The 420,402 distillations went through 22 batch jobs on the Gemini Batch API, plus a sync retry
for the 882 answers the batches returned in an unusable form. After the retry, 432 blocks (0.10%)
stayed failed and were served empty; no extractor × criterion passed the registered 1% flag. The
prepaid API credit ran out four times. Each time the run resumed from its own cache, so nothing was
paid twice, and no registered step changed. Every one of the 1,532 rows finished normally. The run
cost US$ 150.55 at list price, under a cap of US$ 160. No row was read for its outcome until all of
them existed.

## 4. Results

**Controls.** The floor required both extractors to answer at least half the questions under C2:
flash scored 0.793 and flash-lite 0.806. The positive control required at most 4 of 40 correct
answers without the answer sessions: both scored 0.000. Both passed.

**Primary.**

| | estimate | 95% interval |
|---|---|---|
| judge 1 | −4.1 points | −12.3 to +4.1 |
| judge 2 | −5.0 points | −13.4 to +3.5 |

The interval contains 0, so H_E1 is not confirmed. Inconclusive does not mean equal advantages: the
data allow anything from a drop of 12.3 points to a gain of 4.1.

**Contrasts behind it** (secondary, intervals under judge 1, judge 2 in brackets):

| contrast | points |
|---|---|
| C2 − C0 with flash | +21.1 (+14.8 to +27.4) [+19.4] |
| C2 − C0 with flash-lite | +25.2 (+18.8 to +31.6) [+24.4] |
| flash − flash-lite under C0 | +2.9 (−3.5 to +9.3) [+6.6] |
| flash − flash-lite under C2 | −1.2 (−6.4 to +4.0) [+1.7] |
| P − C0 with flash-lite | +13.2 (+7.5 to +19.0) [+13.6] |
| P − C0 with flash | +17.4 (+11.1 to +23.6) [+14.5] |
| P − C2 with flash | −3.7 (−9.4 to +1.9) [−5.0] |

**Accuracy and length per cell** (judge 1; characters served to the reader, median):

| extractor | C0 | C2 | P |
|---|---|---|---|
| flash-lite | 0.554, 142,450 | 0.806, 231,304 | 0.686, 222,106 |
| flash | 0.583, 104,243 | 0.793, 175,468 | 0.756, 234,388 |

## 5. What the result says

The rules still paid with the larger model. C2's advantage over C0 was +21.1 points with flash,
with a lower bound of +14.8, so whatever the true interaction, flash did not make C2 unnecessary.
The earlier contrast also reproduced: with every memory, answer and grade remade, flash-lite gave
+25.2 points for C2 over C0, against +24.8 in the earlier study.

The interaction is the difference of two changes, and most of the small negative estimate comes from
C0. Under C2, flash moved accuracy little (−1.2 points under judge 1, +1.7 under judge 2). Under C0
it scored +2.9 points higher under judge 1 and +6.6 under judge 2, whose interval just excludes 0.
Flash also wrote fewer memories under C0 (2.03 per block against 2.63) and served the shortest
material of any cell, yet scored higher. That is consistent with a stronger extractor doing part of
the rules' work unasked, which the primary does not establish.

Stating the purpose of the memories got most of the way to the rules. P beat C0 by +13.2 points
with flash-lite and +17.4 with flash, and with flash it came within 3.7 points of C2. That interval
reaches 0, so the data show P neither below C2 nor equal to it. Flash-lite had more failed blocks
under P than under the other criteria (0.42%).

## 6. Limits

- The questions were already used by the earlier study (§2).
- Flash and flash-lite are whole configured models. They differ in size, but also in how they
  follow a prompt, how they score importance and how much they write. "Stronger extractor" names
  the comparison, not a mechanism. Thinking budget and model family were not varied, and the
  inconclusive result at this step says nothing about a much larger model. `gemini-2.5-pro` was
  priced for this design at US$ 380 to 1,370 and dropped.
- The reader and judge 2 are Gemini models, like both extractors. The contrasts are reported under
  both judges; they disagree in sign only on flash − flash-lite under C2, where both intervals
  contain 0.
- One benchmark. The prompts are in Portuguese and the conversations in English. C2 and P were
  written by the author; neither is a neutral sample of possible criteria.
- The intervals are conditional on one draw of the distillations.

## Data and code

`paper-e-extractor/` in the repository: the pre-registration, runner, analysis and tests at tag
`paper-e-prereg-v1.0`; the run's rows, receipt and analysis in `runs/confirm-2026-11-08/`
(`e-analyze.py --check` reproduces the analysis byte for byte); the result in `RESULT.md`; the two
reviews; the cost smokes in `SMOKE-RESULT.md`. The benchmark is public; no private data was used.
