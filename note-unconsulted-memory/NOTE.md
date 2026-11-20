---
title: "The memory the agent does not consult: a server instruction that works in evaluation and is rarely acted on in use"
author: "Luiz Antonio Busnello"
---

Status: working draft, not deposited, not peer reviewed. A data note, dated: the controlled
evaluation ran on 2026-11-06 and 2026-11-07, and the field readings cover 2026-10-11 to
2026-11-20 on one user's machine and one production host. The provenance table at the end names
the source of each figure; `PROVENANCE.json` holds the source of every decimal number and
percentage, and a gate checks each one against it.

## Abstract

In our deployment, agents connected to a memory server rarely searched it unless something told
them to. We tested what that something should be. On a frozen bank of 36 tasks whose right answer
depends on a fact in the memory that the prompt does not name, a coding agent (Claude Code,
`claude-sonnet-5-5`) had a pass rate of 0.065 with the memory server alone. Three ways of telling it
when to search raised that pass rate: a skill file (+0.250, 95% CI [0.139, 0.370]); a text the
memory server sends in its `initialize` result, with rewritten tool descriptions (+0.491 [0.352,
0.630]), which failed a pre-registered limit on false triggers (+31.7 pp against a limit of 15);
and a revision of that text that states what the memory covers and keeps its triggers inside that
scope (+0.463 [0.315, 0.611], false triggers +1.7 pp). A template of the scoped text shipped. In
the owner's own Claude Code sessions in the week after deployment, 2 of 38 sessions called the
search tool (0 of 269 sessions before). The pre-registered rule needed at least 0.20, so the
reading is "no visible change". The fleet of server agents on the same host, which never received
the text, made 13 searches after the deployment in the transcripts on disk, all from one agent on
one weekly task whose answer needed the corpus; that task was switched off on 2026-11-17. No arm
showed a measurable effect on writing to memory (0 or 1 of 30 runs in the three arms tested on
it). We report a contrast between an evaluated effect and observed field use, which are not
measured on the same scale, not an explanation of it.

## 1. Question and setting

nox-mem is a memory server for coding and operations agents: a SQLite store with hybrid
full-text and embedding search, exposed to agents as MCP tools. A census in October found that
the tools worked and almost nobody called them: five searches in thirty days outside the
server's own canary and our instrumentation. A companion note (doi:10.5281/zenodo.24017458)
reports the push side, a brief placed in the system prompt, and finds no textual trace of it in
replies.

This note asks the pull-side question. Given an agent that has the memory tools, what text makes
it search when the task needs memory but does not say so, and does the answer get better because
of it? Then: does the effect measured on a task bank show up in ordinary use?

## 2. Where a "when to search" text can live

An MCP client has three places to carry such a text, and they are not read at the same moment.

- **Tool descriptions.** In this client the MCP tools are deferred: the model sees their names
  and must call a tool-search step to load their schemas. In the main run (arms S0 and S1, kept
  tasks), every one of the 59 K runs that called a memory tool called that step first; 54 of them
  searched, and the other 5 only asked for statistics. A description is therefore read after the decision
  to search, and can hardly cause it.
- **A skill file.** The client lists each skill's short description in the system prompt and
  loads the body only when the model invokes it. In the main run the body was loaded in 28 of the
  108 S1 runs on the kept tasks (26%).
- **Server instructions.** The `instructions` field of the MCP `initialize` result goes into the
  system prompt on every turn, with no install step and no decision by the model.

## 3. Controlled evaluation

**Design.** Frozen task bank: K = 40 tasks whose answer depends on a corpus fact the prompt does
not name, G = 20 general tasks the corpus does not cover (false triggers and cost), W+ = 10 tasks
where the user states a decision (should the agent write it?), W− = 10 with nothing worth
keeping. A separate agent drafted the bank without seeing the skill or the protocol. Corpus: the
engineering docs of the memory project (decisions, incidents, audits) at a pinned commit, built
into a fresh database (1,382 chunks). The repository was public then. When its history was
rewritten on 2026-11-08, four of those audits were removed because they quoted a private corpus
(`audits/2026-10-22-abstention-baseline.md`, `audits/2026-10-27-abstention-the-durable-fix.md`,
`audits/2026-10-27-the-oracle-pass-and-what-the-judge-got-wrong.md`,
`audits/2026-10-27-the-ruler-is-deflated-not-inflated.md`), so the database cannot be rebuilt in
full from the public history. Every K task's source is in `docs/DECISIONS.md` or
`docs/INCIDENTS.md`, none in those four files, although they still sat in the index as
distractors. Each run is a fresh, isolated session against a copy of that database, so no run
writes into the next.

Arms: S0 (memory server only), S1 (plus the skill), T (server instructions, 1,198 characters,
plus rewritten tool descriptions), T2 (a scoped revision of T's instructions, 1,593 characters:
the first paragraph names the memory's scope, the settings trigger applies only inside it, and a
new sentence says not to search for software outside it; tool descriptions as in T). Two control
arms set the bounds: P+, whose prompt says to check memory first (the ceiling), and N, with no
memory server (the floor, used to screen leaked tasks). Three replicas per task, except P+, which
ran once per task. The unit is the task. Effects are differences in per-task means, with 95%
bootstrap intervals over tasks (10,000 resamples). Each arm's decision rule was written into the
protocol before that arm ran, but the arms were not all designed in advance: T was designed after
the S1 results and T2 after the T results, on the same bank. The protocol is the author's own
record, kept in git, with no external timestamp.

**Outcomes.** H1: the share of K runs with a memory call. H2: the share of K runs whose reply
uses the decisive fact, judged blind by a model from another family (Gemini 4 Argon) against a
criterion fixed per task. Every pass must quote the reply, and the quote is checked mechanically.

**Gates.** The N arm excluded 4 of 40 K tasks as answerable without memory; on the 36 kept, N
passed 0 of 108 runs. The grader passed 40 of 40 oracle replies and failed 40 of 40 generic ones.
Tool calls counted from the client stream matched the server's telemetry in every run. On a
blind 20% sample (48 replies), the project owner agreed with the grader on 43 of 45, Cohen's
kappa 0.89.

**A ceiling set by the product, found by the positive control.** The first P+ run searched in 40
of 40 runs but passed only 10 of 36. The search tool returned the first 200 characters of each
hit, and no tool returned a chunk whole. The agent found the right chunk, saw its opening, and
tried to open the file on disk: 25 of 40 runs attempted it. After the product was changed to
return whole hits (release 3.8.0), P+ passed 27 of 36 (0.75), and file attempts fell to 1 of 40.
No "when to search" text can raise a pass rate above what the search result carries, so all
arms below ran on 3.8.0.

## 4. Results

H2 and H1 on the 36 kept tasks, per-task means. Controls for T and T2 are the S0 and S1 runs of
the main run, not run concurrently.

| arm | H1 search | H2 pass | H2 vs S0, 95% CI | G false triggers vs S0 | G median token overhead |
|---|---|---|---|---|---|
| S0 | 0.046 | 0.065 | — | — | — |
| S1 skill | 0.454 | 0.315 | +0.250 [0.139, 0.370] | +10 pp | +0.5% |
| T instructions | 0.778 | 0.556 | +0.491 [0.352, 0.630] | **+31.7 pp** | +1.8% |
| T2 scoped instructions | 0.750 | 0.528 | +0.463 [0.315, 0.611] | +1.7 pp | +2.1% |

Each arm's limits, fixed in advance: false triggers at most +15 pp and median token overhead at
most 15%. S1 and T2 pass. T fails on false triggers: all 7 of the G tasks it searched on asked
to change a configuration value of software the corpus does not cover, which is what its trigger
sentence ("search before changing a setting…") says to do when nothing says what the memory
holds. The scoped revision removed most of that (1 of 60 runs) at no detectable cost on K: T2 − T
is −0.028 [−0.139, +0.083], which does not exclude a loss of up to 14 pp. Against the skill, T2 −
S1 is +0.213 [0.102, 0.333]. T2 changed several sentences at once, so these differences are the
effect of the revision as a whole, not of any one sentence in it.

**The arms differ in how often the agent searches.** In every arm, a run that searched passed at
roughly 0.6 to 0.8 (S1 0.63, T 0.69, T2 0.68), near the P+ ceiling; a run that did not search
almost never passed (S0 0.029, S1 0.051, T2 0.07). This is an association inside each arm, not
the yield of a search, since the arm itself changes which runs search (S0 searched in only 5);
what the arms visibly change is the share of runs that make one.

**Writing.** When the user stated a decision mid-task, the agent wrote it to memory in 0 of 30
S0 runs, 1 of 30 S1 runs and 0 of 30 T runs; T2 was not run on the writing sets. A rewritten
description of the write tool and a write rule in the instructions moved nothing measurable.

## 5. Field use after deployment

**What shipped.** Release 3.9.x sends a template of the T2 text when the user configures a scope.
On the owner's machine the scope names the owner's projects, which are several and broader than
the single-project corpus of the evaluation, so the text that ran in the field is not the text
that was evaluated (1,750 characters against 1,593). It went live on 2026-11-08 at 17:45 UTC.

**Rule, registered before any session after deployment was counted.** Unit: a top-level Claude
Code session with at least 3 assistant messages, excluding the evaluation's own runs. BEFORE:
sessions started in the 28 days before deployment; AFTER: sessions started after it; sessions
open across the deployment are excluded. "It searches now" if the AFTER share with a search call
is at least 0.20 and at least 0.15 above BEFORE, with at least 20 AFTER sessions; "too eager" if
the median result size exceeds 20,000 characters per session or more than 80% of sessions
search; otherwise "no visible change". The rule was written into the measurement script and into
the protocol on 2026-11-08: the frozen baseline the script wrote at 17:56 UTC counts 0 AFTER
sessions, and the protocol commit that states the rule is at 18:31 UTC. Both are the author's own
records, with no external timestamp.

**Reading on 2026-11-15.** AFTER: 38 sessions, 2 with a search (P = 0.053), 4 search calls in
total, 3 of them the same query in one session. BEFORE: 0 of 269 (the frozen baseline had 278
sessions, also with 0 searches; 9 of them were no longer on disk at the second reading). Reading:
no visible change: the threshold was not reached, which is not evidence that the effect is zero.
None of the 8 AFTER sessions in the two repositories the memory most covers searched. The field
reading counts searches in sessions whose need for memory is unknown; the evaluation counted
answers on tasks built to need it. The two are not on the same scale.

This does not by itself show that the text fails. The field differs from the evaluation in
several ways that could matter, and none of them was varied:

- the deployed scope covers many projects, so the boundary the text asks the model to draw is
  blurrier than in the evaluation, where every K task fell inside the scope by construction;
- the field sessions run with many MCP servers, skills and project instructions in context, and
  a session-start hook already pushes a short memory brief into each session;
- the task mix is whatever the owner did that week, not tasks drawn from the memory's contents,
  so the share of sessions that needed memory at all is unknown;
- before and after are not randomized; this is one user's before/after, not a trial.

## 6. The agents that never received the text

The same memory server serves a fleet of six operations agents on the production host. They
were deliberately left without the text (`NOX_MEM_INSTRUCTIONS=off`), because T2 was measured on
a coding agent with a coding corpus and never on them. Their behaviour is the untreated baseline
in a different setting:

- On 2026-10-14, their transcripts since 2026-09-01 held 0 calls to the search tool (4 memory
  tool calls in all, none of them a search).
- In the census reported on 2026-10-21, 337 of the 382 searches recorded since 2026-10-14 were the
  server's own canary probe and none was attributed to an agent.
- The agent transcripts on disk on 2026-11-20 (83 files modified after 2026-11-08 17:45 UTC) hold
  13 search calls and 1 full-text read, each dated after that time by its own timestamp: 6 on
  2026-11-09 and 8 on 2026-11-16, two Mondays, all from one agent whose weekly deadline sweep ran
  on Mondays (openclaw-vps PR #89), a task whose answer depends on the corpus by design. The owner switched that sweep
  off on 2026-11-17, so these 13 calls are history, not ongoing use. No call by any other agent
  was found in the files examined. The host prunes old transcripts, so some sessions after the
  deployment may already be gone.

The server's own telemetry cannot settle the field question by itself: from 2026-10-18 to
2026-11-17 it logged 109 MCP searches with an unknown caller; it does not record which client
made them, so it cannot tell the owner's sessions from the agents'. The counts above come from the
client transcripts, where the caller is known.

## 7. What this note claims, and what it does not

It claims: on this bank, with this model and this client, server instructions (with rewritten
tool descriptions) raised the share of tasks answered with the decisive memory fact from 0.065 to
about 0.5, more than a skill file did, and a scoped revision of the instructions kept that gain
while bringing false triggers within the limit set in advance. In the owner's ordinary use in the
week after a template of that text shipped, configured for the owner's projects, 2 of 38 sessions
searched, which the pre-registered rule reads as no visible change. No arm showed a measurable
effect on writing.

It does not claim that the text has no effect in use (38 sessions with an unknown share that
needed memory cannot show that), that the evaluated effect was wrong, that the contrast has any
one of the causes listed in section 5, that any single sentence of the T2 revision caused its
result, or that any of this holds for other models, other clients, or the operations agents.

## 8. Limits

One model and one client. One corpus, the project's own engineering docs; the tasks were written
by the team, not drawn from users. The person who built the system ran the evaluation, wrote the
scoped text and graded the human sample, blind to arm. The arms were designed one after another
on the same bank. The T and T2 controls were not run
concurrently. The minimum detectable difference, computed in advance for 40 tasks, is about
18 pp, and a little more on the 36 kept, so the T2 − T and similar comparisons near zero are not
shown to be zero. The field reading is one user, one week, 38 sessions, and measures searches,
not answers.

## 9. Data availability

**Public, next to this note.** Byte-for-byte copies of the evaluation protocol
(`skill-eval-PROTOCOL.md`), the task bank and the harness (`skill-eval/`), with the same git blobs
as `docs/skill-eval/` at commit `438e3a6` of the product repository. The bank file matches the
hash the protocol froze, and the runner matches its last re-freeze. The protocol holds the design
and every controlled-evaluation result; it does not hold the field readings, whose sources are
the reports below and `field-recount-2026-11-20.md`. The census and the audits cited in sections 1
and 6 are in this public repository; the companion note is deposited on Zenodo
(doi:10.5281/zenodo.24017458).

**Private.** The branch that holds the protocol, kept in a private repository with a git bundle as
a second copy, because it also carries the archived skill; the skill file; the frozen evaluation
database, which is not included and cannot be rebuilt in full from the public history (section
3); the run data (the agent's replies and the grader's verdicts, which can quote the corpus) and
the analysis scripts that compute the effects and intervals from them; the real-use script and its
two reports, which read the owner's transcripts (the rule is quoted in full in section 5); and
the agent transcripts, which stay on the host. A reader can check every figure against the
protocol and the recount, but cannot recompute the effects and intervals from public material.

## Provenance

`P` = `skill-eval-PROTOCOL.md` in this directory, a verbatim copy of `docs/skill-eval/PROTOCOL.md` at `438e3a6` (product repository, branch `docs/memory-skill-draft`).
`R` = the real-use reports in the owner's evaluation directory (`real-use/`), not public.
`H` = `docs/HANDOFF.md` of this repository at `b3ca58d`.
`F` = `field-recount-2026-11-20.md` in this directory: read-only queries on the production host, with the commands and their output.

| number | value | source |
|---|---|---|
| bank sizes K/G/W+/W− | 40 / 20 / 10 / 10 | P:8, P:86–91 |
| eval DB chunks | 1,382 | P:11 |
| four corpus audits removed from the public history on 2026-11-08 | the four `.md` of six audits | `docs/HISTORY-REWRITE-2026-11-08.md`:17; `skill-eval/harness/build-corpus.sh`:22–24 (corpus keeps only `.md`) |
| K task sources | 25 in `docs/DECISIONS.md`, 15 in `docs/INCIDENTS.md` | `skill-eval/bank/tasks-v1.jsonl`, field `source_file` |
| bootstrap resamples | 10,000 | P:154 |
| P+ runs per task | 1 | P:193, P:221 |
| T2 change against T | first paragraph, settings trigger, one new sentence | P:404–412; `skill-eval/harness/arm-T2-mcp-server.diff` |
| tasks kept after N screen; N floor | 36; 0 of 108 | P:185–188 |
| grader calibration | 40/40 oracle pass, 40/40 generic fail | P:179–180 |
| tool calls in the stream equal server telemetry, every run | 480/480, 240/240, 180/180, 40/40 twice | P:241, P:347, P:444, P:194, P:221 |
| P+ at 200-char preview | 40/40 searched, 10/36 pass, 25/40 file attempts | P:193–203 |
| P+ after whole-text fix (3.8.0) | 27/36 = 0.75; file attempts 25 → 1 of 40 | P:221–224 |
| deferred tools: main-run K runs with a memory call, all calling tool search first; of them, searched | 59 of 59; 54 | P:306–308 ("59 K runs that searched" there counts any memory tool); 54 = 5 + 49, P:386–387; the 5 others called only the statistics tools (run data, private) |
| skill body loaded, S1 runs on the 36 | 28 of 108 (26%) | P:286–287 |
| S0, S1 H1/H2 (36) | 0.046 / 0.454; 0.065 / 0.315 | P:360–361 |
| S1 − S0 H2 | +0.250 [0.139, 0.370] (erratum to +0.241) | P:350–353 |
| S1 G false triggers; overhead | +10 pp; +0.5% | P:258–259 |
| human agreement | 43/45, kappa 0.89, 48 replies | P:265–268 |
| T text length | 1,198 chars | P:312 |
| T H1/H2; T − S0 H2 | 0.778 / 0.556; +0.491 [0.352, 0.630] | P:360–361 |
| T G false triggers; overhead; 7 tasks | +31.7 pp; +1.8%; 7 of 20 | P:367–372 |
| T2 text length | 1,593 chars | P:412 |
| T2 H1/H2; T2 − S0 H2 | 0.750 / 0.528; +0.463 [0.315, 0.611] | P:450–451 |
| T2 G false triggers; overhead | 0.017 = 1/60, +1.7 pp; +2.1% | P:457–459 |
| T2 − T; T2 − S1 | −0.028 [−0.139, +0.083]; +0.213 [0.102, 0.333] | P:465–468 |
| pass when searched / not | S0 0.029 (not); S1 0.63 / 0.051; T 0.69; T2 0.68 / 0.07 | P:384–388 (after the erratum), P:470–471 |
| writing W+ | S0 0/30, S1 1/30, T 0/30 | P:292–293, P:394 |
| minimum detectable effect (40 tasks) | about 18 pp | P:154–155 |
| deployment time; field text length | 2026-11-08 17:45 UTC; 1,750 chars | R `measure.py`:4, :12 |
| real-use rule | as quoted in section 5 | P:502–511; R `measure.py`:5–17 |
| rule registered: baseline written; protocol commit | 2026-11-08 17:56 UTC, 0 AFTER sessions; 18:31 UTC | R `baseline-2026-11-08.json` `generated_utc`, `AFTER`; `README.md` of this directory |
| AFTER n, P, calls | 38, 0.053, 0.11 per session (= 4) | R `report-2026-11-15.json` `AFTER`; H:44–47 |
| BEFORE at reading; frozen | 0 of 269; 0 of 278 | R `report-2026-11-15.json` `BEFORE`; R `baseline-2026-11-08.json`; H:44–47 (the 269) |
| 3 of 4 calls same query; 0 of 8 sessions in the two repos | — | H:44–47 |
| companion note (push side) | — | doi:10.5281/zenodo.24017458; source `paper-c-pushed-memory/NOTE.md` |
| October census: five searches in thirty days | 5 | `audits/2026-10-23-item7-consumidor-construido.md`:22 |
| 0 search calls since 2026-09-01; 4 memory calls | 0; 4 | H:1674–1675 |
| 337 of 382 searches since 2026-10-14 were the canary | 337 / 382 | `audits/2026-10-21-r1-recency-relevance.md`:131–132 |
| agent transcripts after deploy; searches; reads; dates | 83 files; 13; 1, all one agent; 6 on 2026-11-09, 8 on 2026-11-16 | F, first section and "Each call dated" |
| six operations agents; left without the text | six; `NOX_MEM_INSTRUCTIONS=off` | `audits/2026-10-23-item7-consumidor-construido.md`:126; H:314 |
| weekly deadline sweep: Mondays; switched off | `0 11 * * 1`; 2026-11-17 | `totobusnello/openclaw-vps` PR #89 (crontab line commented, dated note in `crontab-rebuild.sh`) |
| unknown-caller MCP searches, 2026-10-18 to 2026-11-17 | 109 | F, second section |
