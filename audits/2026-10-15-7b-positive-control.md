# 7b action probe — positive control failed; main phase not run (2026-10-15)

Spec: `specs/2026-10-14-7b-brief-action-probe-design.md` §7. Plan ledger:
`.superpowers/sdd/2026-10-14-7b-brief-action-probe-plan/progress.md`.

## Decision rule (fixed before the run)

The pilot left the mechanical primaries invalid (A/A C 0.636, H 0.665, ceiling 0.5; spec §5.3), so
Toto ordered the positive control to run **before** the main phase, with the spec's own gate: if
decisive hits < 7/10, the main phase is not launched and 7b closes on that finding. No spec amendment.

## Run

20 frozen scenarios (10 decisive, 10 typical) × {BP = B1 with one item substituted by the planted
fact, B1} × 2 replicas = **80 runs, 80 ok**, 0 hook mismatches. Launched 10:45 UTC, finished 12:36
UTC (300 s spacing). Scorer: `eval/brief-action-probe/scripts/score_control.py` (same
`probe.control.score_control` the pre-registered analysis uses).

## Result

| metric | value | gate |
|---|---|---|
| decisive hits | **0/10** | ≥ 7/10 |
| typical hits | 0/10 | ≥ 3/10 for informative nulls |
| false hits (B1) | 0/10 | ≤ 1/10 |
| **pass** | **false** | |

Per spec §7, the main phase's nulls would be uninformative, so it was **not run** (~744 runs saved).

## Checks that the zero is real, not an artefact

1. **The fact reaches the prompt.** The planted value exists only in the BP arm file (`BP.md`,
   injected with `--append-system-prompt-file`, the production path); it is absent from B1 and from
   every input turn. In P01 (both replicas) and P09 (one replica) the agent's first action used the
   planted value, which it could only have read from the brief. Delivery works.
2. **The scorer is right.** P01 shows 2/2 replicas with the planted value in actions but is not a hit:
   replica 1 touched the planted **and** the superseded path in the same message, which §7 excludes.
3. **Structural ceiling, measured.** 12 of 40 BP first messages contain only a `ToolSearch` (loading
   deferred tools), which cannot carry the planted value. Restricting to first messages with a real
   action:

| arm | runs with a real first action | planted value used | superseded value used |
|---|---|---|---|
| BP | 28 | **3** (all decisive) | 13 |
| B1 | 27 | 0 | 12 |

The planted fact did not displace the old value: the superseded value appears at the same rate with
and without the substitution (13/28 vs 12/27).

## Finding

**A salient, specific fact placed in the brief changes the agent's first action in 3 of 28 runs where
that action could show it (1 of 10 decisive scenarios meets the two-replica criterion); a fact in the
brief's usual register, in 0 of 14.** The agents' first actions follow the cron prompt and workspace
instructions, not the brief. Together with `audits/2026-10-14-brief-usage.md` (implicit use 0 of
9,398 pairs), the brief, as served today, does not steer the first action.

## Limits (declared, not acted on)

- The outcome is the **first assistant message** (spec §4). With deferred tools, 30% of those messages
  are tool loading; a later-action outcome might see more. Changing the outcome is a spec amendment,
  which Toto ruled out for this run.
- 20 scenarios on the 5 largest cron prompts; one model (`claude-sonnet-5`); two replicas.
- A null here says nothing about whether the brief helps **later** in a session or in free-form
  conversation; 7b measured only the first action of cron runs.

## Reproduce (on the VPS, read-only)

```sh
cd /root/medicoes/7b && python3 code/scripts/score_control.py
```

Ceiling table: filter each row's `message.tool_calls` to names other than `ToolSearch`, then count
`planted`/`superseded` substrings from `control/scenarios.jsonl` in the JSON of their inputs.
Raw results stay on the VPS (`/root/medicoes/7b/`, never versioned: they contain agent outputs).
