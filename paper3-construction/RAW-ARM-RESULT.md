# Raw-evidence arm on the 242 — result (v1.4, §15)

Registered by the tag `paper3-prereg-v1.4` (commit `bca912c`), pushed before the first call.
Run 2026-11-04, 484 rows, every one with finish `STOP`, no failed call, US$ 2.06 in 148 s.
`python3 -I raw-arm.py --out runs/raw-arm-2026-11-04 --analyze` reproduces `raw-arm.txt` without
any API key.

A first attempt stopped at its first judge call (HTTP 401: the session's `OPENAI_API_KEY` was a
stale key; the working one is the file the earlier runs used). It wrote no row, so no outcome was
read. Its answer calls stayed in the run's cache and were reused; its spend was not ledgered.

## Instrument check

acc(E-raw) = 0.872 under judge 1, against the required 0.60. PASS, so H4 is interpreted.

## Arms (reader R3)

| arm | material | judge 1 | judge 2 | abstention | mean chars |
|---|---|---|---|---|---|
| cell 11 (from the confirmatory run) | all sessions, C2 units | 0.818 | 0.826 | 0.074 | 231,416 |
| E-dist(C2) | evidence sessions, C2 units | 0.818 | 0.835 | 0.087 | 13,115 |
| E-raw | evidence sessions, raw turns | 0.872 | 0.884 | 0.083 | 28,153 |

## H4: E-dist(C2) − E-raw

| judge | estimate | 95% interval | discordant (units only / raw only) | row of the §15.4 table |
|---|---|---|---|---|
| 1 | −5.4 pp | [−10.3, −0.8] | 11 / 24 | upper < 0: C2 units lose to raw evidence; lower bound misses −δ by 0.3 pp |
| 2 | −5.0 pp | [−9.9, 0.0] | 12 / 24 | lower > −δ: non-inferior at δ = 10 pp; upper bound is exactly 0, so "worse" is not shown |

G = 241 answer-session clusters.

**Reading under the registered rule.** The two judges land in different rows, and each by the
smallest margin the interval can carry (0.3 pp below −δ under judge 1; an upper bound of exactly
zero under judge 2). §15.4 says the claim is then the weaker of the two. Neither directional
reading holds under both judges: "C2 units lose to raw evidence" fails under judge 2, and
"non-inferior at 10 pp" fails under judge 1. What both judges agree on is the estimate, a gap of
about 5 pp against the C2 units (−5.4 and −5.0), with intervals that reach from about −10 pp to
about 0. The result is reported as that bracket, not as a confirmation of either reading.

## Secondary, descriptive

| contrast | judge 1 | judge 2 |
|---|---|---|
| cell 11 − E-raw | −5.4 [−10.7, −0.4] | −5.8 [−11.5, −0.4] |
| cell 11 − E-dist(C2) | 0.0 [−3.7, +3.7] | −0.8 [−4.1, +2.5] |

The ~50 distractor sessions per instance cost nothing detectable under C2 (10 / 10 discordant
pairs under judge 1), as under C1 in development. The full memory of cell 11 sits about 5 pp below
the raw evidence sessions under both judges, and both intervals exclude zero; this contrast mixes
retrieval by oracle with representation, so it is not a test of 2601.00821's prediction.

By question type, judge 1:

| type | n | cell 11 | E-dist(C2) | E-raw |
|---|---|---|---|---|
| knowledge-update | 30 | 0.900 | 0.900 | 0.933 |
| multi-session | 68 | 0.838 | 0.853 | 0.956 |
| single-session-assistant | 28 | 0.786 | 0.821 | 0.964 |
| single-session-preference | 16 | 0.438 | 0.375 | 0.250 |
| single-session-user | 32 | 0.906 | 0.875 | 0.906 |
| temporal-reasoning | 68 | 0.824 | 0.824 | 0.853 |

The gap sits in multi-session (−10.3 pp) and single-session-assistant (−14.3 pp). Temporal
reasoning, where C1 lost most in development (0.37 against 0.94), is now within 3 pp.

## Against development

On the spent 200, E-dist(C2) scored 0.745 and E-raw 0.830 (−8.5 pp). On the 242 they scored
0.818 and 0.872 (−5.4 pp). Different samples; a description, not a test.

## Files

`runs/raw-arm-2026-11-04/`: `rows-raw-arm.ndjson`, `raw-arm.txt`, `raw-arm.json`, `receipt.json`.
The run cache (answers and judgments) is kept outside the repository with its sha256.
