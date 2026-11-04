# Confirmatory run of v1.3 (2026-11-04)

Pre-registration: DOI [10.5281/zenodo.23934489](https://doi.org/10.5281/zenodo.23934489) (v1.3),
tag `paper3-prereg-v1.3`, published before this run started. Run: `runs/confirm-2026-11-04/`
(rows, receipt, analysis, per-process spend). `lme-analyze.py runs/confirm-2026-11-04 --check`
reproduces the analysis byte for byte.

| | |
|---|---|
| instances | 242 (`v13-manifest.json`, sha256 `f9c7df69…`), plus the 31 counterfactual rewrites |
| rows | 1,654, every one with finish `STOP`; no judge call failed |
| runner | sha256 `f6b82e0c…`, identical to `lme-run.py` at tag `paper3-prereg-v1.3` |
| criterion C2 | prompt sha256 `325342a3…`, identical to the calibration's (§14.8) |
| reader | R3: gemini-3.8-flash, prompt B, thinking low |
| judges | judge 1 gpt-6-luna (primary), judge 2 gemini-2.5-flash-lite |
| blocks | 155,506 distinct; 87 failed to distil and were served empty (0.056%) |
| spend | **US$ 70.73** cumulative, cap US$ 110 |

## How the run went

Three processes, one out dir, resumed from the run's own cache (§14.9 item 7, §14.10):

| process (UTC) | what it did | spend | how it ended |
|---|---|---|---|
| 1, 2026-11-04 02:12 | distilled all 155,506 blocks, started reads at 48 workers | US$ 24.49 | HTTP 429 |
| 2, 03:07 | resumed reads at 8 workers | US$ 0.02 | HTTP 402: the Gemini project's prepaid credit ran out |
| 3, 09:49 | after the credit was topped up, resumed reads to the last row | US$ 46.22 | exit 0 |

No row was read for its outcome, and `lme-analyze.py` was not run, until all 1,654 rows existed.

## Controls

| control | result | required | |
|---|---|---|---|
| answerable floor | acc(11) = **0.818** (n = 242) | ≥ 0.50 | pass |
| positive | 0.000 (n = 40) | ≤ 0.10 | pass |
| negative | 0.775 vs 0.775, discordance 0.100 | ≤ 0.10, ≤ 0.20 | pass |
| counterfactual | original 1, altered 28 of 31 | original ≤ 3.1, altered > original | pass |

All four pass, so the primary is interpreted. The counterfactual is a regression control
(§14.9 item 2): all 31 rewrites ran in stage 1, so it checks the instrument on known examples.

## Primary: H1′

> H1′: E[ Y(full window, C2, R3) − Y(0.240 window, C0, R3) ] > 0 on the 242.

| | estimate | 95% interval |
|---|---|---|
| judge 1 | **+66.5 pp** | [+60.6, +72.5] |
| judge 2 | +66.9 pp | [+61.0, +72.9] |

Cluster-robust over answer-session groups (G = 241), α = 0.05, one stage, no interim look.
acc(00) = 0.153, acc(11) = 0.818. The interval excludes 0: **H1′ is confirmed.** The two judge
families agree on 922 of 968 primary-cell judgments.

The analysis prints the v1.1 licence label, *"repair confirmed, larger on this corpus"*. That label
was written for H1 with criterion C1. Under §14.9 item 3, the reading is narrower:

- this confirms a total effect for an intervention revised after exploration (C2 with R3);
- it does not confirm the original H1, whose interaction now involves another treatment;
- it does not confirm H3, which this design does not identify;
- it does not show that C2 beats C1 on new data, because C1 did not run.

## Contrasts behind the total effect

These contrasts are reported by the registered analysis (§11.5 item 9). None of them is a
confirmatory test.

| contrast | judge 1 | judge 2 |
|---|---|---|
| window, 11 − 01 (C2 held) | +59.5 [+53.1, +65.9] | +61.6 [+55.2, +67.9] |
| criterion, 11 − 10 (full window held) | +24.8 [+18.8, +30.8] | +27.3 [+21.1, +33.4] |
| criterion, 01 − 00 (0.240 window held) | +7.0 [+3.6, +10.4] | +5.4 [+2.1, +8.6] |

The contrasts are conditional, and the interaction keeps them from adding up as shares of the
total. Taken in one order, the total splits as window +59.5 plus criterion +7.0; in the other, as
about +41.7 (10 − 00, by difference) plus +24.8. The window contrast is the larger in both orders,
which does not identify a share of the mechanism. At 0.240, cell 00 kept no annotated evidence
session in 120 of the 242 instances, so the extractor never saw those sessions; as the plan states
for its controls, a missing annotated session is not proof that no usable information was left.
The criterion contrast measures C2 against the deployed C0, not C2 against C1. As the plan requires
(§11.5 item 9), it is read as the bracket across judge families, [+24.8 · +27.3] pp at the full
window, until a human pass picks between them.

The length-matched arm (cell 00's material, padded to cell 11's length with raw text from sessions
that hold no answer) scores +0.8 pp [−0.8, +2.4] over cell 00 and −65.7 pp below cell 11, and the
primary adjusted for served length is unchanged at +66.5 pp. The plan's test (§11.5 item 8) is
whether this arm reproduces cell 11. It does not, so the primary is not read as a capacity effect.
That rules out this padding, not every explanation by length, and it does not identify the
mechanism of the window contrast by elimination.

**Interaction (secondary).** +17.8 pp, and −1.4 pp [−20.2, +11.8] after the serial null. The
interval contains 0: inconclusive, which is not a null and does not allow an equivalence claim.

**Dose.** The sign of Y(full, C2) − Y(dose, C0) is the same at both doses: +83.3 pp at 0.020 and
+35.0 pp at 0.894 (n = 60 each). `analysis.txt` prints these two levels as `W=0.20` and `W=8.94`:
that is a formatting defect in `lme-analyze.py`, which is frozen at the tag, and the cells it reads
are `d020` and `d894`.

## Calibration and confirmation

C2 was written after reading the failures of the 200 spent instances. §14.9 item 4 called its
calibration score of 0.770 likely optimistic. On the 242 new instances cell 11 scored 0.818, so
the expected drop did not appear. This is a descriptive comparison of two different samples.

| question_type | n | 00 | 01 | 10 | 11 |
|---|---|---|---|---|---|
| knowledge-update | 30 | 0.333 | 0.467 | 0.733 | 0.900 |
| multi-session | 68 | 0.059 | 0.147 | 0.603 | 0.838 |
| single-session-assistant | 28 | 0.250 | 0.321 | 0.536 | 0.786 |
| single-session-preference | 16 | 0.062 | 0.062 | 0.312 | 0.438 |
| single-session-user | 32 | 0.281 | 0.312 | 0.781 | 0.906 |
| temporal-reasoning | 68 | 0.088 | 0.147 | 0.441 | 0.824 |

Abstention falls from 0.760 in cell 00 to 0.074 in cell 11.

## Limits that still apply

- Both judges are language models. R3 and judge 2 are both Gemini, so the bracket is read on the
  contrasts, not on the levels (§14.9 item 5). Conclusions stay conditional on the judges until
  the blind human pass the plan provides for.
- Preference questions have rubric references and cap every cell (§14.9 item 9). They stayed in
  the sample.
- The window is a most-recent-first cut by whole sessions at a nominal 0.240, an approximation of
  production's window and not its mechanism (§11.2). Its realised dose in cell 00 has median 0.251
  [0.240, 0.274], and sensitivity to the shape of the cut was not measured (§11.5 item 2).
- One corpus (LongMemEval `s_cleaned`), one reader, one extraction model (gemini-2.5-flash-lite).

Not peer reviewed.
