# Stage 1 — instrument failure (2026-11-03)

Pre-registration: DOI 10.5281/zenodo.23914868 (v1.1), tag `paper3-prereg-v1.1`. Run:
`runs/stage1-2026-11-03/` (rows, receipt, analysis; `lme-analyze.py --check` reproduces it byte
for byte). 200 instances, 1,444 rows, US$ 18.80, 143 of 127,522 blocks failed to distil (0.11%).
Manifest sha256 `9dc7e728…`, runner sha256 `5b047dd4…`.

## The registered reading

| control | result | required | |
|---|---|---|---|
| answerable floor | acc(11) = **0.210** (n=200) | ≥ 0.50 | **FAIL** |
| positive | 0.000 (n=40) | ≤ 0.10 | pass |
| negative | 0.150 vs 0.150, discordance 0.050 | ≤ 0.10, ≤ 0.20 | pass |
| counterfactual | original 0, altered 9 of 31 | original ≤ 3.1, altered > original | pass |

§11.3: *"If the floor fails, the run is reported as an instrument failure and the primary is not
interpreted, rather than reported as a null."* That is the result of this stage. The total-effect
estimate (+14.5 pp [+8.5, +20.5], judge 2 +15.0) is printed by the analysis and is **not** a
finding: with the full window, the pipeline answers 21% of the questions, so nothing it says about
repair is interpretable. The stop rule's "YES" is moot for the same reason.

Stage 2 is **not** run on this instrument: it would spend ~US$ 23 on a reading the registration
already forbids.

## Where cell 11 loses the answer (exploratory, not registered)

`stage1-floor-diagnosis.py`, cache only. Restricted to the 84 instances whose reference answer is
textual (letters, 4–40 chars), so verbatim matching means something:

| | count |
|---|---|
| reference verbatim in a `has_answer` turn | 47 |
| … and lost by distillation (C1) | 11 (23%) |
| reference verbatim in the distilled units served in cell 11 | 42 |
| … of which answered correctly | **15 (36%)** |
| … of which the reader abstained (`NAO SEI`) | **18 (43%)** |

The evidence units are not buried: the first one sits at a median 3% of the served list (units are
sorted by importance). Two losses stack, and **the larger one is the reader**: with the answer in
the material and near the top, flash-lite under the strict `NAO SEI` rule abstains on 43% and is
right on 36%. Mean served length in cell 11 is 161,742 characters.

## Two defects of the registration, stated

1. **The floor's derivation cites another corpus.** §11.3 says *"the deployed system scores 42.4%
   on this corpus and the repaired one 63.6%"*. Those numbers come from the PT-BR faithfulness
   replay (`audits/2026-10-26-faithfulness-replay.md`, n=99), not from LongMemEval. The threshold
   was fixed before the data and it binds; the sentence that justifies it is wrong about where it
   comes from.
2. **The smoke could not warn.** It passed the floor at 4/8 = 0.50 exactly, an interval of roughly
   ±35 pp. A smoke sized to check plumbing cannot check a threshold.

## What a next registration would have to change, and what it cannot reuse

A new run needs a reader that clears the floor *before* any contrast is looked at, checked on
instances outside every sample used here. The 200 stage-1 instances and the 8 smoke instances are
spent: their contrasts have been printed, so they cannot serve as the confirmatory sample of a
repaired instrument. The 262 never-touched instances of the 462 universe remain.

## Correction, 2026-11-03 (additive)

"The larger one is the reader" holds only for the stage-1 reader (flash-lite). With
gemini-3.8-flash on the same 200 instances (`READER-CEILING.md`, exploratory), distillation is the
larger loss: 0.475 on the evidence sessions' C1 units against 0.830 on their raw turns, while
removing the distractor sessions changes nothing (0.505 → 0.475, p = 0.24).
