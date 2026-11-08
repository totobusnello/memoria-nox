# Paper E result (2026-11-08)

Pre-registration: `PREREGISTRATION.md` at tag `paper-e-prereg-v1.0` (commit `7113c3f`), pushed
before any paid call of the run. Run: `runs/confirm-2026-11-08/` (rows, receipt, analysis, chunk
record, per-process spend). `python3 -I e-analyze.py runs/confirm-2026-11-08 --check` reproduces
the analysis byte for byte.

| | |
|---|---|
| instances | 242 (`v13-manifest.json`, sha256 `f9c7df69…`); 241 answer-session clusters, largest 2 |
| rows | 1,532, every one with finish `STOP` |
| distillations | 420,402: 419,520 from 22 batch chunks, 882 by the sync pass |
| failed blocks | 432 (0.10%), served empty; none over the 1% flag (table below) |
| extractors | `gemini-2.5-flash-lite`, `gemini-2.5-flash` (thinking off), as returned by the API |
| reader | R3, `gemini-3.8-flash` |
| judges | judge 1 `gpt-6-luna` (primary), judge 2 `gemini-2.5-flash-lite` |
| spend | **US$ 150.55** at list price, cap US$ 160 |

## How the run went

Five processes, one out dir. Each one passed the tag check, and each resumed from the run's own
cache.

| process (UTC) | what it did | spend | how it ended |
|---|---|---|---|
| 1, 12:59 | 22 batch chunks | US$ 81.91 | exit 0; 882 answers invalid under §3.4 |
| 2, 14:13 | sync pass on the 882 | US$ 0.35 | exit 0; 0 left |
| 3, 16:54 | read, 388 rows | US$ 17.29 | HTTP 402 from the Gemini API (prepaid credit) |
| 4, 17:10 | read resumed from cache | US$ 50.56 | HTTP 402 again |
| 5, 17:24 | read resumed from cache, last rows | US$ 0.44 | exit 0; analysis |

The prepaid Gemini credit ran out four times. Twice it happened during the batch phase: the
runner held the next chunk and submitted it after the top-up, and no chunk was lost. Twice it
happened during the read: judge 2 raised on HTTP 402 and the process stopped. Each restart
reused every cached answer and grade, so nothing was charged twice: the cached counts in the
spend files grow and the spend does not. The sync pass took 2 h 41 min for 882 calls because many
of the invalid answers were long, repetitive generations (up to 39,478 output tokens).

The estimate was about US$ 122. Reading cost US$ 0.045 per row against the US$ 0.028 measured in
Paper 3, because full-window material is long (median 104,000 to 234,000 characters per cell).
No row was read for its outcome, and the analysis did not run, until all 1,532 rows existed.

## Controls

| control | result | required | |
|---|---|---|---|
| floor | acc(F_C2) 0.793, acc(L_C2) 0.806 | ≥ 0.50 each | pass |
| positive | acc(L_C2_pos) 0.000, acc(F_C2_pos) 0.000 (n = 40 each) | ≤ 0.10 each | pass |

Both pass, so the primary is interpreted.

## Primary: H_E1

> I = E[(F_C2 − F_C0) − (L_C2 − L_C0)] < 0 on the 242.

| | estimate | 95% interval |
|---|---|---|
| judge 1 | **−4.1 pp** | [−12.3, +4.1] |
| judge 2 | −5.0 pp | [−13.4, +3.5] |

The interval contains 0: **inconclusive**. This is not evidence that the C2 advantage is the same
for both extractors. The point estimate is a shrinkage of about 4 pp. The interval allows anything
from a shrinkage of 12.3 pp to a growth of 4.1 pp, so it rules out, at this level, a shrinkage
larger than about 12 pp. The pre-registration put the shrinkage detectable with 80% power at
9.4 to 12.2 pp (§7).

## What the contrasts show

All secondary, with intervals and no test claimed (§4).

| contrast | judge 1 | judge 2 |
|---|---|---|
| F_C2 − F_C0: the C2 advantage with flash | +21.1 [+14.8, +27.4] | +19.4 [+13.1, +25.8] |
| L_C2 − L_C0: the C2 advantage with flash-lite (Paper 3: +24.8) | +25.2 [+18.8, +31.6] | +24.4 [+17.7, +31.1] |
| F_C0 − L_C0 | +2.9 [−3.5, +9.3] | +6.6 [+0.1, +13.2] |
| F_C2 − L_C2 | −1.2 [−6.4, +4.0] | +1.7 [−3.1, +6.4] |
| L_P − L_C0 | +13.2 [+7.5, +19.0] | +13.6 [+7.8, +19.5] |
| F_P − F_C0 | +17.4 [+11.1, +23.6] | +14.5 [+8.7, +20.2] |
| F_P − F_C2 | −3.7 [−9.4, +1.9] | −5.0 [−10.1, +0.1] |
| P interaction, (F_P − F_C0) − (L_P − L_C0) | +4.1 [−4.3, +12.6] | +0.8 [−7.0, +8.7] |

- **The C2 advantage stays large with flash.** With the stronger extractor, C2 still beats C0 by
  +21.1 pp, with a lower bound of +14.8 under judge 1.
- **Paper 3's contrast reproduces.** On fresh distillations, a fresh read and fresh grades, the
  flash-lite contrast is +25.2 pp, against +24.8 in Paper 3.
- **Where the small shrinkage comes from.** It comes, if anywhere, from flash raising C0: +2.9 pp
  under judge 1, and +6.6 pp under judge 2, whose interval just excludes 0. Flash does not change
  C2 (−1.2 and +1.7). §4 reads a negative I as "the stronger model needs the rules less" only if
  F_C0 − L_C0 > 0. That condition holds in the point estimate, but I itself is inconclusive.
- **P beats C0 with both extractors.** It is +13.2 pp on flash-lite and +17.4 on flash. With flash,
  P is 3.7 pp below C2, an interval that reaches 0. So with flash, stating the purpose of the
  memories gets most of the way to the rules, but the data do not show it matching them. The P
  interaction is inconclusive.

## Cells

| cell | acc j1 | acc j2 | abstain | median characters served |
|---|---|---|---|---|
| L_C0 | 0.554 | 0.566 | 0.289 | 142,450 |
| L_C2 | 0.806 | 0.810 | 0.099 | 231,304 |
| L_P | 0.686 | 0.702 | 0.198 | 222,106 |
| F_C0 | 0.583 | 0.632 | 0.260 | 104,243 |
| F_C2 | 0.793 | 0.826 | 0.083 | 175,468 |
| F_P | 0.756 | 0.777 | 0.153 | 234,388 |

Flash writes less under C0 and C2 than flash-lite (2.03 against 2.63 units per block under C0,
3.13 against 4.18 under C2) and about the same under P (4.22 and 4.24). Its C0 material is the
shortest of all cells and scores above flash-lite's. The two judges agree on 1,353 of the 1,452
main-cell rows.

## Failed blocks

| extractor, criterion | failed | share | units per block |
|---|---|---|---|
| flash-lite, C0 | 59 of 70,067 | 0.08% | 2.63 |
| flash-lite, C2 | 45 of 70,067 | 0.06% | 4.18 |
| flash-lite, P | 293 of 70,067 | 0.42% | 4.24 |
| flash, C0 | 10 of 70,067 | 0.01% | 2.03 |
| flash, C2 | 9 of 70,067 | 0.01% | 3.13 |
| flash, P | 16 of 70,067 | 0.02% | 4.22 |

None is over 1%. Flash-lite fails more often under P than under C0 or C2.

## Deviations

None. The four HTTP 402 stops are operational: §8 already says the run resumes from its cache,
and no registered step changed. The spend passed the estimate and stayed under the cap.

## Limits that still apply

- These 242 instances were read by Paper 3; this is a paired extension, not an independent
  confirmation (§2).
- Flash and flash-lite differ as whole configured models, not only in strength (§1). An
  inconclusive result at this step does not rule out a shrinkage with a much stronger extractor.
- The reader and judge 2 are Gemini, like both extractors. The contrasts are reported under both
  judges, and they agree in sign on every row of the table above except F_C2 − L_C2, whose two
  intervals both contain 0.
- One corpus. The prompts are in Portuguese and the conversations in English. P and C2 were
  written by the authors.

Not peer reviewed.
