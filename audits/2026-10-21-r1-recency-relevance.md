# R1: would a recency-ordered brief be more relevant? — ROADMAP v6 item 7, 2026-10-21

**Question.** Since 2026-10-14 22:13 UTC the brief server also computes, on every refresh, what a
recency-ordered brief *would* have contained, and logs both id lists side by side without changing
what the agent receives (`NOX_BRIEF_RECENCY=shadow`, nox-workspace#59, log
`/root/.openclaw/logs/brief-recency-shadow.ndjson`). Seven days later: do the agents' replies show
more trace of what R1 would serve than of what was actually served?

**Design.** Unit: one assistant message, 2026-10-14 22:13 → 2026-10-22 01:00 UTC. Two arms measured
on the *same* message, from the last shadow record of that agent before it:

| arm | what it is |
|---|---|
| `served_now` | the 10 items actually in the prompt — the only arm that can produce *use* |
| `recency_now` | the 10 items R1 would have chosen instead — counterfactual, never exposed |

Plus past/future controls per arm (items in that arm at another moment of the window but not at
this one). The **future** control is the discount for topic continuity: the conversation itself
pushes material into later briefs, and a recency-ordered brief is made of exactly that material.

The arms are **not symmetric, and the asymmetries run in opposite directions**: only `served_now`
can be copied from the prompt, while `recency_now` is favoured by topic continuity. So this
measures *relevance*, not *use*: a `served_now` hit may be use, a `recency_now` hit cannot be.

Detectors are audit 7a's, unchanged (strict: one-liner ≥ 25 chars verbatim, or a distinctive file
stem on word boundaries; fuzzy: ≥ 60% of the item's distinctive tokens, min 4). Paired test:
McNemar on "message has ≥ 1 hit", because both arms come from the same record at the same instant.

Read-only throughout: sqlite `mode=ro`, transcripts and ndjson only read.

⚠️ **Transcripts live under TWO roots, and the first pass only read one.** `atlas` and `lex` have
no directory under `/root/.claude-nuvini-team/projects`, which I first reported as "those two
agents are not measurable". Wrong: they are under `/root/.claude/projects`, and so is a second set
of sessions for *every* other agent. Reading one root covered **345 of 523** messages (66%);
`cipher` went from 3 to 42. Both roots are read below, deduped by `(agent, message id)`. The 7a
audit has the same hole and its numbers are understated by the same mechanism.

**Result.**

```
transcript dirs read: 12
assistant messages with text in window: 523
by brief agent: {'nox': 200, 'boris': 236, 'forge': 42, 'cipher': 42, 'atlas': 1, 'lex': 2}
shadow records in window: 4778 {'nox': 1364, 'atlas': 682, 'boris': 683, 'cipher': 682, 'forge': 683, 'lex': 684}
distinct brief items: 539, resolvable in chunks: 528
messages skipped (no shadow record before them): 0

== ALL
  served_now      pairs=  5212  strict=   0  fuzzy=   0   msgs_with_hit=0/523
  recency_now     pairs=  4965  strict=   0  fuzzy=   0   msgs_with_hit=0/523
  served_only     pairs=  4258  strict=   0  fuzzy=   0   msgs_with_hit=0/523
  recency_only    pairs=  4011  strict=   0  fuzzy=   0   msgs_with_hit=0/523
  both            pairs=   954  strict=   0  fuzzy=   0   msgs_with_hit=0/523
  served_past     pairs= 93947  strict=   0  fuzzy=  11   msgs_with_hit=4/523
  served_future   pairs= 24856  strict=   0  fuzzy=   5   msgs_with_hit=3/523
  recency_past    pairs= 87932  strict=   0  fuzzy=  11   msgs_with_hit=4/523
  recency_future  pairs= 27068  strict=   0  fuzzy=   6   msgs_with_hit=4/523

== McNemar (unit = message; served_now vs recency_now)
  both hit: 0   served only: 0   recency only: 0   neither: 523
  discordant pairs = 0 -> no evidence either way (test has no information)
```

**Zero on both exposed arms.** No strict hit in any arm at all. Every fuzzy hit is in a *control*
arm (past and future overlap, so these counts are not additive), and every one of them is a
`distilled` chunk of the agent's own session: the conversation produced the chunk, the chunk
entered a later brief, and the detector matched the conversation against its own summary. That is
the self-match the future control exists to expose, and it is the only thing that lit up.

## The null is not an instrument failure — the positive control says so

Lesson of 7b: a null without a positive control is uninterpretable. Two checks, same code path:

```
== CAPACITY (unique items of the window)
  served    items= 485  one_liner>=25c= 482 (99.4%)  distinctive stem=  23 (4.7%)  detectable=483 (99.6%)
  recency   items= 453  one_liner>=25c= 451 (99.6%)  distinctive stem=   5 (1.1%)  detectable=451 (99.6%)

== POSITIVE CONTROL (inject the item into the message text, re-detect; n=300 pairs)
  injecting one_liner        strict fires=287 ( 95.7%)  fuzzy fires=238 (79.3%)
  injecting one_liner+stem   strict fires=300 (100.0%)  fuzzy fires=300 (100.0%)
  injecting chunk_text[:200] strict fires=245 ( 81.7%)  fuzzy fires=231 (77.0%)
```

99.6% of brief items are detectable by construction, and if an agent *did* quote one the detector
fires 95.7–100% of the time. The zero is a fact about the agents, not about the probe.

**What the probe still cannot see:** influence without textual trace. An agent can be steered by a
brief item and never reuse its wording. That is precisely what 7b tried to measure behaviourally,
and 7b failed its own positive control (0/10). So the honest statement is: *no measurable trace by
any instrument this project currently has* — three independent nulls (7a, 7b, R1), not proof of no
effect.

## What R1 would actually change

This part does not depend on relevance and is the part that decides.

```
overlap served × R1: median 2/10 (mean 1.97)  =>  R1 would replace 8 of 10 items
age served  (days): median 173.0   p10=3   p90=179   max=185   >90d: 65.1%
age R1      (days): median   4.0   p10=0   p90=  8   max= 13   >90d:  0.0%

composition, weighted by slots served
  SERVED    distilled 48.3% · lessons.md 13.0% · PHASE-3-COMPLETION-REPORT 10.0%
            · EVOLUTION.md 10.0% · INCIDENTS.md 10.0% · 2026-04-20 notion-import 8.7%
            pain>=0.9: 45.0%
  R1        distilled 67.5% · lessons.md 29.5% · decisions.md 3.1%
            pain>=0.9: 21.2%
```

R1 does what it promised: it takes the brief from a median age of 173 days to 4, and removes every
item older than 90 days. But **it does not trade stale material for curated fresh material** — it
trades the incident record for more machine-written session summaries. `distilled` goes 48.3% →
67.5%, `INCIDENTS.md` / `EVOLUTION.md` / `PHASE-3-COMPLETION-REPORT` drop out entirely, and the
share of `pain >= 0.9` items halves (45.0% → 21.2%).

The old items are old *by design*, not by bug: they are the D2 pain floor (invariant #4, `pain ≥
0.9` is always served) and they are the April incidents — gateway fratricide, the fake-green
rollback, the crash loop. Severe incidents are old because severe incidents are rare.

And every control hit lands on the material R1 would serve more of: an agent matching the distilled
summary of the conversation it just had. Serving an agent its own summary back is the one thing
this measurement showed happening, and R1 raises its share by 19 points.

**Verdict: do not activate R1.** Not because the comparison came out null — it came out null with
no information (0 discordant pairs) — but because the composition shift is measurable, is in an
identifiable direction, and is not one we have a reason to want. Activating would replace 8 of 10
brief slots in production, halve the severe-incident share, and buy a difference no instrument we
have can observe.

**What would change the answer:** a consumer that actually reads memory. 337 of 382 searches since
14/10 are the canary probe and none are a real agent (`project_agents_do_not_search_nox_mem`);
item 7's premise is that the brief is the only channel, and this measurement says the channel is
not being drawn on at either end. Fix the consumer first, then re-run this script — it is
parameterised by `R1_START` / `R1_END` and the shadow keeps logging.

**Artifacts.** Detector `audits/2026-10-21-r1-recency-relevance.py`, positive control
`audits/2026-10-21-r1-positive-control.py`; raw output on the VPS in
`/root/medicoes/2026-10-21-r1/{saida-v2,controle-v2}.txt`. Shadow unchanged, production untouched,
nothing written to the database.
