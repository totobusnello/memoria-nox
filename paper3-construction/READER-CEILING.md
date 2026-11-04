# Reader ceiling — exploratory, not registered (2026-11-03)

Script `reader-ceiling.py`, committed before its first call (`5f6d497`). Run:
`runs/ceiling-2026-11-03/` (rows, table, json, log). 200 stage-1 instances (spent), 800 answers,
US$ 1.71. No cell of the 2×2 was built, so no registered contrast can be computed from it.

v1.2 selected no reader (§13.10): the best, R3 (gemini-3.8-flash, prompt B), reached
acc(11) = 0.505 against a 0.55 bar. This run asks how much of the gap is the reader and how much
is what the reader is served. Two oracle materials, both restricted to the answer sessions:

- **E-dist**: the C1 distilled units of the evidence sessions only, served as cell 11 serves them
  (stage-1 cache, nothing re-distilled; 2 of 200 come out empty);
- **E-raw**: the evidence sessions as raw turns, in chronological order.

## Result (judge 1; judge 2 in `ceiling.txt`)

| reader | cell 11 (all sessions, units) | E-dist (evidence, units) | E-raw (evidence, raw) |
|---|---|---|---|
| R0 flash-lite, prompt A | 0.210 | 0.205 | 0.340 |
| R3 3.8-flash, prompt B | 0.505 | 0.475 | **0.830** |
| R3 abstention | 0.320 | 0.360 | 0.070 |
| mean characters served | ~161,700 | 9,178 | 26,458 |

R3, paired over the same 200 instances:
- cell 11 → E-dist: 12 right only in cell 11 and 6 right only in E-dist (exact McNemar p = 0.24). **Removing the ~50 distractor sessions buys nothing.**
- E-dist → E-raw: 6 against 77 (p < 10⁻¹⁶), +35.5 pp. **The loss is the distillation.**

By type (R3, judge 1):

| type | n | cell 11 | E-dist | E-raw |
|---|---|---|---|---|
| knowledge-update | 31 | 0.742 | 0.710 | 0.871 |
| multi-session | 51 | 0.510 | 0.451 | 0.745 |
| single-session-assistant | 24 | 0.542 | 0.458 | 1.000 |
| single-session-preference | 13 | 0.077 | 0.154 | 0.077 |
| single-session-user | 27 | 0.630 | 0.630 | 0.926 |
| temporal-reasoning | 54 | 0.389 | 0.370 | 0.944 |

## Reading

1. **With a capable reader, the floor fails because of construction, not because of the reader or
   the length.** R3 reads 83% of the answers from the raw evidence and 47.5% from its distilled
   units. With the haystack added around those units the score stays where it was. The largest
   gaps are temporal reasoning (0.37 → 0.94) and single-session-assistant (0.46 → 1.00). This
   suggests that C1 units lose the time anchors inside a session and the assistant's side of the
   conversation. That is a hypothesis to check in the units, not something measured here.
2. **The two losses interact.** With R0, distillation costs 13.5 pp and the reader costs most of
   the rest (0.340 against R3's 0.830 on the same raw material). With R3, distillation costs
   35.5 pp. A weak reader hides the construction loss, and that is why stage 1 seemed to point at
   the reader.
3. **Preference questions stay at 0.08 even on raw evidence.** That is a judge or reference problem
   (their references are rubrics, not answers), not a memory problem. Any floor that includes them
   is capped by about 6.5% of the sample.

## Correction to STAGE1-RESULT.md (dated 2026-11-03, additive)

STAGE1-RESULT.md says "the larger one is the reader". That holds only for the stage-1 reader. Its
verbatim count gave distillation 23% of the textual answers, and that count misses losses that are
not verbatim, such as dates and relative order. Measured with a capable reader on the same 200
instances, distillation is the larger loss: −35.5 pp, against ≈ 0 for the distractors.

## What this does and does not license

It does not license a v1.3 that only buys a stronger reader. Its ceiling on C1 units is about 0.5,
whatever haystack is served around them.

A registration that wants the W × C contrast interpretable would need one of two things:
- a construction step whose units clear the floor on oracle evidence, checked first on the
  spent 200;
- a floor defined relative to E-raw rather than as an absolute 0.50.

Either way the question changes. It is no longer only "does the window/criterion repair help" but
first "what does distillation keep". That is the construction thesis this paper exists to test.
