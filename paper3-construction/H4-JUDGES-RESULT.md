# H4 with four judges — result (v1.5, §16)

Registered by the tag `paper3-prereg-v1.5` (commit `977ec5f`). GitHub's activity log records the
push of `977ec5f` at 22:48:26 UTC on 2026-11-04; the first call on the data started at 22:48:32 UTC.
Before §16 was written, two endpoint probes ran on a question unrelated to the corpus. 976 calls,
376 s, no failed call. `python3 -I h4-judges.py --out runs/h4-judges-2026-11-04 --analyze`
reproduces `h4-judges.txt` without any API key.

## Gate (§16.3)

| judge | model | abstentions accepted | references accepted | |
|---|---|---|---|---|
| 3 | glm-5.3 | 0 / 16 | 8 / 8 | pass |
| 4 | gemini-4-argon | 0 / 16 | 8 / 8 | pass |

## H4: E-dist(C2) − E-raw, on the 484 rows of the v1.4 arm

| label | E-dist(C2) | E-raw | estimate | 95% interval | discordant | §15.4 row |
|---|---|---|---|---|---|---|
| judge 1 (gpt-6-luna) | 0.818 | 0.872 | −5.4 pp | [−10.3, −0.8] | 11 / 24 | units lose to raw evidence |
| judge 2 (gemini-2.5-flash-lite) | 0.835 | 0.884 | −5.0 pp | [−9.9, 0.0] | 12 / 24 | non-inferior at 10 pp |
| judge 3 (glm-5.3) | 0.835 | 0.893 | −5.8 pp | [−10.4, −1.2] | 9 / 23 | units lose to raw evidence |
| judge 4 (gemini-4-argon) | 0.839 | 0.901 | −6.2 pp | [−10.8, −1.7] | 9 / 24 | units lose to raw evidence |
| **committee, ≥ 3 of 4 (primary)** | 0.839 | 0.897 | **−5.8 pp** | **[−10.4, −1.2]** | 10 / 24 | **units lose to raw evidence** |

**Reading under §16.4.** The committee's interval lies below zero, so under this protocol the C2
units of the evidence sessions lose to the raw turns of the same sessions, by about 6 pp. Its lower
bound, −10.4 pp, misses the 10 pp non-inferiority margin, so non-inferiority is not shown. Three
of the four judges land in the same row; judge 2 is the only one that does not.

There were 3 two-two ties (1 in E-dist, 2 in E-raw), counted as not correct. Counted as correct
instead, they would move the estimate by −0.4 pp, so the reading does not depend on the tie rule.
Pairwise agreement between judges ranges from 0.957 (judges 1 and 2) to 0.981 (judges 3 and 4).

## What this does and does not change

It settles the v1.4 arm's reading under the rule registered for it in v1.5: a loss of about 6 pp,
not non-inferiority. It does not change what H4 measures. Both arms have perfect retrieval through
the annotations, and the materials differ in length, order and format as well as in content, so
the result is compatible with 2601.00821's prediction and does not test retention. The committee
is four language models, two of them in the reader's family; the blind human grading of §8 is
still the step that would validate any of them.

## Files

`runs/h4-judges-2026-11-04/`: `rows-h4-judges.ndjson` (four verdicts per row), `preflight.json`,
`receipt.json`, `h4-judges.txt`, `h4-judges.json`. The run cache is kept outside the repository
with its sha256.
