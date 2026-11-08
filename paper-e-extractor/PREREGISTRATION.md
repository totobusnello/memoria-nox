# Paper E pre-registration: writing criterion × extractor strength

Status: draft, not frozen. It is frozen by the tag `paper-e-prereg-v1.0`; the runner refuses the
paid phases until that tag exists and its three files match the tag byte for byte.

## 1. Question

Paper 3 (DOI 10.5281/zenodo.23934489, v1.3) found that a rule-based writing criterion, C2, beats
the deployed criterion, C0, by +24.8 pp (judge 1; +27.3 under judge 2) when the whole history is
distilled. Every distillation there used one extractor, `gemini-2.5-flash-lite`, and the manuscript
lists that as a limit. The question here is whether that advantage is a property of the criterion
or a crutch for a weak extractor: does it shrink when the extractor is stronger? A third criterion,
P, states only what the memories are for and leaves the choice of what to keep to the model. It is
the "let the model judge" end of the same axis.

## 2. Design

**Instances.** The 242 of `paper3-construction/v13-manifest.json` (sha256 `f9c7df69…`). No
untouched LongMemEval `s_cleaned` instance remains (500 − 30 abstention − 8 smoke − 200 stage 1
− 262 confirmatory = 0). These 242 were read in the Paper 3 confirmatory run, so the flash-lite
results for C0 and C2 on them are known: accuracy 0.818 for C2 and 0.570 for C0, judge 1. The
hypothesis below concerns the strong extractor and the interaction, which no run has measured.

**Cells.** The full window (every session of the haystack) in all cells.

| cell | extractor | criterion | instances |
|---|---|---|---|
| L_C0, L_C2, L_P | `gemini-2.5-flash-lite` | C0, C2, P | 242 |
| F_C0, F_C2, F_P | `gemini-2.5-flash` | C0, C2, P | 242 |
| F_C2_pos | `gemini-2.5-flash` | C2, answer sessions removed | the 40 of `control_subsample` |

1,492 rows. Every cell is read and judged in this run, including L_C0 and L_C2. What is reused
from Paper 3 is only the flash-lite distillation of C0 and C2 (§3.4), never an answer or a grade.

## 3. Components

**3.1 Unchanged from Paper 3** (imported from `paper3-construction/lme-run.py` at tag
`paper3-prereg-v1.3`): blocking (2,000 characters, per session, noise filter), serving (units of
the cell's sessions, importance descending, then recency), the question text, reader R3
(`gemini-3.8-flash`, prompt B, thinking low), judge 1 (`gpt-6-luna`, Decisions API, correct ⇔
P(contem) > 0.5) and judge 2 (`gemini-2.5-flash-lite`, family-2 prompt), with their cache keys.

**3.2 Extractors.** The request body is Paper 3's distill body: the criterion prompt, then
`"\n\nConversa:\n"` and the block, with `responseMimeType: application/json` and temperature
0.1. `gemini-2.5-flash` adds `thinkingConfig: {thinkingBudget: 0}`, so it runs with thinking off,
as flash-lite does by default. The strong extractor is the next model of the same generation and
family. The family stays fixed so that a change in the C2 advantage is not a change of model family.
`gemini-2.5-pro` was priced and dropped: US$ 380 to 1,370 for this design (`SMOKE-RESULT.md`).

**3.3 Criteria.** C0 and C2 are Paper 3's, byte for byte (sha256 `72208f90…` and `325342a3…`).
P (`e_prompts.py`, sha256 `9e7668b2…`) is C0's header, then this paragraph, then C0's output
contract unchanged (JSON format, importance scale, "Retorne [] se não houver nada relevante",
at most 10 items):

> As memórias que você extrair serão, mais tarde, a única fonte de um assistente que vai responder
> perguntas do usuário sobre o que ele contou e sobre o que foi dito nesta conversa. A conversa em
> si não estará mais disponível. Decida você, pelo conteúdo desta conversa, o que precisa ser
> guardado para que essas perguntas possam ser respondidas.

P was written before any call that used it. Like C2, it is written for this task: it names the
use (questions about what the user said), which C0 does not.

**3.4 Parser.** A response is parsed as JSON. If it is an object, its `memories` list is used; if
it is a top-level list, the list is used. Units with importance ≥ 0.5 are kept, and units whose
importance is not a number are dropped. Anything else is a failed block, served empty, as in
Paper 3. Paper 3 accepted only the object form. The smoke found `gemini-2.5-pro` answering in
the list form in up to 25 of 40 blocks, which the old parser would have served empty
(`SMOKE-RESULT.md`); `gemini-2.5-flash` used the object form in 120 of 120.

**3.5 Reuse of Paper 3 distillations.** Phase `seed` copies Paper 3's confirmatory flash-lite
distillations of C0 and C2 into this run's cache (140,052 of the 140,134 needed). The 82 that
failed in Paper 3 are distilled again with this parser, so L_C0 and L_C2 can differ from Paper 3's
material on at most 0.06% of blocks. Reading and grading are new.

## 4. Hypotheses

**Primary, H_E1.** I = E[(F_C2 − F_C0) − (L_C2 − L_C0)] < 0: the C2 advantage is smaller with the
stronger extractor. It is tested with judge 1, two-sided 95% interval:

- hi < 0: H_E1 confirmed, the advantage shrinks;
- lo > 0: the advantage grows (the opposite direction, reported as such);
- otherwise inconclusive. An interval containing 0 is not evidence of equal advantages.

**Secondary** (intervals reported under both judges, no test claimed, no multiplicity
correction): F_P − F_C2; the P interaction (F_P − F_C0) − (L_P − L_C0); L_P − L_C0; F_P − F_C0;
F_C2 − F_C0; and L_C2 − L_C0 beside Paper 3's +24.8 pp.

## 5. Controls

Both gate interpretation of the primary. If one fails, the result is an instrument failure and
the primary is not interpreted.

- **Floor:** acc(F_C2) ≥ 0.50 and acc(L_C2) ≥ 0.50, judge 1.
- **Positive:** acc(F_C2_pos) ≤ 0.10 on the 40 control instances. With the answer sessions
  removed, the reader must not find the answer in the strong extractor's memories.

## 6. Analysis

`e-analyze.py`, as frozen at the tag, with no other analysis counted as confirmatory. Per-instance
contrasts are averaged and their standard errors are cluster-robust (CR1) over answer-session
groups, using Paper 3's `clusters` and `cluster_mean_ci`. Judge 1 is primary and judge 2 is the
bracket, as in Paper 3 §11.5 item 9. An instance missing any of the six main cells is left out
and named. The analysis also describes accuracy, abstention and served length per cell, and
accuracy per question type. `--check` reproduces `analysis.txt` and `analysis.json` byte for byte.

## 7. Power

From the 242 Paper 3 rows, the flash-lite difference d = Y(L_C2) − Y(L_C0) has variance 0.228
(judge 1). If the strong extractor's difference has the same variance and correlation ρ with it,
a paired test at α = 0.05 with 80% power detects, on 242 instances, a shrinkage of 12.2 pp at
ρ = 0, 10.9 pp at ρ = 0.2 and 9.4 pp at ρ = 0.4. A 10 pp shrinkage is detectable only if ρ is
about 0.35 or more; at ρ = 0 it would need 358 instances. The step from flash-lite to flash is smaller than
the step to pro, so an inconclusive result would not rule out a shrinkage at a larger step.

## 8. Procedure

1. Tag `paper-e-prereg-v1.0` on the commit that holds this file, `e-run.py`, `e_prompts.py`,
   `e_batch.py`, `e-analyze.py` and `e-test.py` with all tests passing.
2. `seed`; then `distill --via batch --wait` (Batch API, half price). Each chunk of at most 20,000
   requests is recorded as soon as it is created, a restart never resubmits a recorded chunk, and
   a chunk created by a process that died before recording it is adopted by its display name.
3. `distill --via sync` for whatever the batches did not return (errors, missing lines, expired
   chunks), at the standard price.
4. `read`, then `e-analyze.py`. No row is read for its outcome, and the analysis does not run,
   until all 1,492 rows exist.

**Cap:** US$ 160 cumulative across processes. The runner holds a batch chunk whose estimate would
pass the cap and stops a process at the cap. Estimate: about US$ 72 for distillation in batch and
about US$ 42 for reading and both judges.

**Failures.** A block that fails to distill after the sync pass is served empty, and the result
reports the count per extractor and criterion. If more than 1% of the blocks of any extractor ×
criterion fail, the result says so beside the primary.

## 9. Deviations

Any change after the tag is a numbered deviation in the result document, with its reason and its
effect on the numbers where it can be computed.

## 10. What was seen before the tag

- Two cost smokes (`SMOKE-RESULT.md`): 40 blocks from the haystacks of the 200 spent stage-1
  instances, none from the 242, with token and unit counts only. No reader, judge or question.
- A shape probe of 24 failed `gemini-2.5-pro` calls, keeping only the JSON shape.
- `batch-test`: the batch path on 30 other spent blocks, criterion P on both extractors.
- Spend on Paper E before the tag: US$ 2.10 (`README.md`).

## 11. Limits known now

- One corpus, LongMemEval `s_cleaned`, and these 242 instances were already used by Paper 3.
- The reader R3 and judge 2 are Gemini, like both extractors; the bracket across judge families is
  read on the contrasts, not on levels, as in Paper 3.
- The prompts are in Portuguese and the conversations in English, as in Paper 3.
- P and C2 were written by the authors; neither is a neutral sample of possible criteria.
- "Stronger" is one step within one family with thinking off. Thinking budget and model family
  are not varied.

Not peer reviewed.
