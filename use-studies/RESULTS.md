# Use studies W and S: results

Pre-registration: `PREREGISTRATION.md`, tag `use-studies-prereg-v1.0` (commit `62728791`, frozen
2026-11-26 21:07 BRT, before any bank run). Runs: 2026-11-27 00:08 to 01:16 UTC (W 240, S 180),
grading done 01:37 UTC. Analysis: `analyze_use.py` as frozen, unchanged; its output is in
`results/W-main.analysis.json` and `results/S-main.analysis.json`.

## Gates

| gate | W0 | WH | WN | WP | SD |
|---|---|---|---|---|---|
| 1. served `claude-sonnet-5-5` | yes | yes | yes | yes | yes |
| 2. connection failures | 0/60 | 0/60 | 0/60 | 0/60 | 0/180 |
| 3. stream counts agree with `search_telemetry` | yes | yes | yes | yes | yes |
| 4. built-in tool executed | 0 | 0 | 0 | 0 | 0 |
| 5. WP ceiling, W+ content ≥ 0.70 | | | | 1.00 | |

Gate 4 needs a note. Some runs asked for a built-in tool (Glob, Grep, Bash, Read, Write): 20 runs
of study W (26 calls) and 53 runs of SD (93 calls). Every one of the 119 calls was answered *"No
such tool available"*, read from the tool results in the streams, so no built-in tool ran. The
2026-11-07 runs show the same behaviour under the older client, where the calls were refused by the
permission mode instead: 73 of the 180 T2 runs asked for a built-in tool. We read gate 4 as written
("no run executed a built-in tool") and keep these runs in the primary analysis. The gate's
parenthesis ("the run is reported and dropped") allows a stricter reading, so section 4 reports
that reading as a sensitivity analysis.

## 1. Study W: does the agent record a decision the user stated?

W+ is 10 tasks where the user states a decision worth keeping; W− is 10 tasks with nothing worth
keeping. Three replicas per task and arm.

| arm | W+ content | W+ wrote | W− wrote |
|---|---|---|---|
| W0 (T2 build, nothing added) | 0.033 (1/30) | 0.033 | 0.000 |
| WH (Stop hook asks once) | 1.000 (30/30) | 1.000 | 0.000 |
| WN (reminder appended to tool results) | 0.067 (2/30) | 0.067 | 0.000 |
| WP (user prompt asks to record; ceiling) | 1.000 (30/30) | 1.000 | 0.000 |

| contrast | W+ content, mean per-task difference [95% CI] | tasks up / down | W− wrote | decision |
|---|---|---|---|---|
| WH − W0 | +0.967 [0.900, 1.000] | 10 / 0 | +0.000 | **works** |
| WN − W0 | +0.033 [0.000, 0.100] | 1 / 0 | +0.000 | **no detectable effect over W0** |

Two contrasts, no correction for multiplicity, as registered.

What the hook costs: in WH the agent takes one more round after the hook fires. Median wall time on
W+ tasks was 13 s against 7 s in W0, with 6 turns against 1. On W− tasks it was 5 s against 4 s. The
hook's text is in the stream of all 60 WH runs. The `hook_fired` field of the run record was never
filled by the runner (it is `None` in every arm); the streams are the evidence.

Without help the agent almost never records a decision (1 in 30). A reminder placed in the tool
results does nothing measurable. A Stop hook that asks once records the decision in every W+ run and
writes nothing on the W− tasks. The hook works as well as the user asking for it in the prompt (WP).

## 2. Study S: can the scope sentence be derived from the store?

SD is T2 with the scope sentence produced by `derive_scope.py` from the store's own chunks instead
of written by hand. S0 (no instructions) and T2 (hand-written scope) are the 2026-11-07 runs.
**This comparison is not concurrent.** The model pin, build, DB, bank and grader are the same; the
Claude Code version is not (2.1.332 now, 2.1.319 then).

| arm | K pass | K searched | G false trigger |
|---|---|---|---|
| S0 (2026-11-07) | 0.065 (n=108) | 0.046 | 0.000 (0/60) |
| T2 (2026-11-07) | 0.528 (n=108) | 0.750 | 0.017 (1/60) |
| SD | 0.579 (n=107) | 0.852 | 0.133 (8/60) |

One SD K run has no grade (`grader_invalid`: the quote check failed) and is left out, as on
2026-11-07.

| contrast | mean per-task difference [95% CI] | tasks up / down |
|---|---|---|
| SD − T2, K pass | +0.056 [−0.046, 0.167] | 8 / 4 |
| SD − S0, K pass | +0.519 [0.370, 0.657] | 24 / 0 |
| SD − S0, G false trigger | +0.133 [0.000, 0.283] | 3 / 0 |

Decision by the registered rule: **the derived scope works as well as the hand-written one (margin
0.10).** SD − T2 has a lower bound of −0.046, above −0.10; SD − S0 has a lower bound above 0; and
the false-trigger rise is 0.133, under the 0.15 limit.

The false-trigger condition passes narrowly. The rule compares the point estimate with 0.15, and
the upper bound of its interval is 0.283. The 8 false triggers all fall on three G tasks: G02 (nginx
log rotation), G08 (embedding batch size) and G09 (backup cron time), each written as "our ..."
infrastructure. T2 had 1 false trigger in 60 runs. In this bank, the derived sentence finds the
decisive fact as often as the hand-written one and searches more often when it should not.

## 3. Spending

The Claude runs used the subscription's allowance. Their `total_cost_usd` is notional, as on
2026-11-07. Real money went to Gemini: 183 grader calls (about 230 thousand input tokens, estimated
from the graded texts plus a fixed prompt allowance) and the query embeddings of the runs. The
grader does not record token usage per call, and billing is not readable from this machine, so the
exact figure has to come from the provider console. By this estimate it is a few dollars at most,
far below the US$ 30 ceiling of study S.

## 4. Sensitivity: dropping runs that asked for a built-in tool

`results/sensitivity-builtin-attempts.json`, computed with the frozen functions and only the run
filter changed:

| reading | W decision | S decision |
|---|---|---|
| drop attempt runs in every arm (new and 2026-11-07) | WH works, WN no effect | works as well as the hand-written one |
| drop attempt runs in the new runs only | WH works, WN no effect | **fails the T2 rule** (G false-trigger rise +0.167 over 32 SD runs) |

Study W does not move. Study S moves only in the second reading, and only on the false-trigger
condition, which drops more than half of SD's G runs and none of the older arms'. That reading
treats the two dates differently. We report it because it shows how close the false-trigger
condition is to its limit.

## 5. What follows

- Study S phase 2 (the same SD test in a second client) is allowed by the registration because
  phase 1 passed. It is not pre-registered; it needs its own registration and the owner's go-ahead.
- Two things the registration does not cover, for a later step: whether WH keeps W− at zero on
  tasks that resemble decisions without being one, and whether a scope sentence that leaves out
  generic infrastructure words lowers SD's false triggers.
