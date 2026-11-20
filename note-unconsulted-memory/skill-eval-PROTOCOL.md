# Does the nox-mem skill change what the agent does? Evaluation protocol

v1.0, 2026-11-06. **Task bank frozen** after review by the project owner ("td certo", 14:45 BRT).
Only smoke runs (section 8a) have happened; no bank task has been run in any arm.

| frozen artifact | sha256 |
|---|---|
| `bank/tasks-v1.jsonl` (K40, G20, W+10, W−10) | `0c877ad186696428d60e923bd2ee2982a3b3043c00fb9e5ce12229bc1d17e41a` |
| `skills/nox-mem-memory/SKILL.md` (v0.2) | `722fa072da4b99f5494fb420175ba92fa1fca5990b31d1f9fdcfcddaeb994d09` |
| `harness/run_eval.py` | `46a3d5e405797cf23d1ef14871509e8370cc4a779f033f8c0cfb4ff77e03c7a6` |
| eval DB `eval-a819385.db` (1,382 chunks, all embedded) | `869ddf6d68491dfcb02b71ed0869d13ba1fc977bf8e54b857912b437569dbf64` |

The bank was drafted by a separate agent that never saw the skill or this protocol (so the tasks
cannot be tuned to the skill's triggers), then checked against the whole corpus for facts the
corpus itself later superseded: 5 tasks were replaced from reserves in rank order, 4 kept with a
narrowed criterion. Details in `bank/tasks-v1-draft-notes.md`; the draw in `bank/draw-v1.json`.

## 1. Question

Given an agent that has the nox-mem MCP server, does adding `skills/nox-mem-memory/SKILL.md` make it
(a) consult memory when the task needs it without saying so, and (b) produce a better answer
because of it, at an acceptable cost on tasks that do not need memory?

Why (b) and not only (a): a skill that raises the search rate without changing answers adds cost
and nothing else.

Prior evidence, from the research repo (`memoria-nox`):
- 2026-10-23 census: five non-probe searches in 30 days. The MCP worked; nobody called it.
- 2026-10-23 pull probe: the agent searched when the task named something only the corpus holds,
  and did not search on a generic task. The case this protocol targets, a need the task does not
  name, was declared untested there.
- Paper C: three push measurements (a brief placed in the prompt) found no trace in the replies and
  no change in the first action.

## 2. Arms

| arm | MCP | skill | purpose |
|---|---|---|---|
| S0 | yes | no | baseline |
| S1 | yes | yes | treatment |
| P+ | yes | no, and the prompt says "check nox-mem memory first" | positive control: the ceiling |
| N | no | no | floor; screens tasks answerable without memory |

Deferred arm T: rewritten MCP tool descriptions, no skill. The current `nox_mem_search` description
still says "FTS5 full-text search with BM25 ranking", which is out of date (search is hybrid). Better
descriptions might do part of the skill's job at no cost. If S1 wins, T runs next, before anyone
calls the skill necessary.

## 3. Harness

- `claude -p --output-format stream-json --verbose`, model pinned (`claude-sonnet-5-5`). The served
  model id is read from each run's stream and checked, not assumed.
- Isolation: `env -i` (HOME, USER, PATH, LANG only) plus `--setting-sources project
  --strict-mcp-config --mcp-config <one local stdio nox-mem> --no-session-persistence`, stdin from
  `/dev/null`. Probed 2026-11-06 (Claude Code 2.1.319), two runs. A canary phrase from the user's
  global CLAUDE.md was absent, user plugins and skills were absent, the skill was listed, and auth
  was the subscription's OAuth. Without `env -i`, three user mods leaked in through
  `CLAUDE_CODE_PLUGIN_DIRS` inherited from the parent environment. What remains in both arms:
  Claude Code's built-in plugins and its ~19 built-in skills. The user's `language` setting leaked
  past `--setting-sources project` (replies came back in Portuguese); the runner pins it with
  `--settings '{"language":"english"}'`.
- Rejected routes: `--bare` (API key only, and skills resolve only via `/skill-name`, which would
  remove the autonomous triggering that S1 measures); an empty `CLAUDE_CONFIG_DIR` (no OAuth
  credentials in it).
- The skill's body is not in context until the model loads it; only its `description` is. The
  probe confirmed this. Loading is read from the stream (a `Skill` tool call).
- cwd is an empty temp directory. In S1 it contains only `.claude/skills/nox-mem-memory/`. The agent
  has no copy of the corpus on disk, so memory is the only route to the facts.
- **Never the production database.** Searches write access counts that feed salience. Each run gets
  a fresh copy of a frozen eval DB (`NOX_DB_PATH`), so writes from one run cannot reach the next.
- `NOX_AGENT_NAME=skilleval-<arm>-<run>` on the server, so `search_telemetry` attributes every row.
- One fresh session per run. Order of runs interleaved and randomized across arms.
- The extracted corpus files are deleted after the DB is built. Chunk sources carry absolute paths,
  and in the first smoke run the agent saw a path in a search result and tried `find`/`Read` on it.
  `dontAsk` denied both; deleting the files removes the route entirely. Every denied attempt is
  recorded per run (`permission_denials`).

## 4. Corpus

The public docs of `memoria-nox` at a pinned commit (`DECISIONS.md`, `INCIDENTS.md`, `CLAUDE.md`,
`audits/*.md`), ingested into a fresh DB with the product's default hybrid search. Recorded: commit,
DB sha256, chunk count, embedding provider and model. The corpus is public, so anyone can rebuild it.

## 5. Task bank (frozen before the first real run)

| set | n | what it is | outcome |
|---|---|---|---|
| K | 40 | a realistic request whose right answer depends on a corpus fact the prompt does not name | searched? decisive fact used? |
| G | 20 | answerable from general knowledge; the corpus is irrelevant | false trigger; token overhead |
| W+ | 10 | the user states a decision mid-task | was it written? |
| W− | 10 | nothing in the task is worth keeping | was anything written? (noise) |

K tasks start from the corpus, not from the skill. Decisions and incident root causes are
enumerated from `DECISIONS.md` and `INCIDENTS.md`, 40 are drawn with a fixed seed, and a natural
request is written for each drawn fact. Writing tasks to cover the skill's trigger list would teach
to the test and inflate S1. The section 1 trigger each task touches is labelled afterwards, for
analysis only. Whoever writes the tasks never sees S0/S1 output before the bank is frozen, and the
user reviews the bank before the freeze.

Every K task carries: the prompt, the decisive fact, the source file and the chunk ids that hold it,
the pass criterion, and the post-hoc trigger label. Two examples, to show the shape:

- *"Set the pre-op snapshot retention to 2 days, we need the disk."* Pass: the reply raises that
  5 days was chosen on purpose, to cover detection over a weekend.
- *"Switch the default Gemini model to gemini-2.5-flash for better quality."* Pass: the reply raises
  the quota rule that forbids it.

Leakage screen: arm N runs every K task 3 times. A task that N passes in 2 or more of 3 runs is
excluded **before** any S0/S1 result is read. The rule uses only N, which no treatment touches.
Results are reported with and without the exclusion.

## 6. Outcomes

Primary:
- **H1, search rate on K**: fraction of runs with at least one call to `nox_mem_search`,
  `nox_mem_decision_get`, `nox_mem_decision_list` or `nox_mem_reflect`. S1 against S0.
- **H2, pass rate on K**: the decisive fact is used. An LLM grader blind to the arm applies the
  pre-registered criterion. One person grades a 20% sample, also blind, and the report gives their
  agreement (kappa). H2 is the one that decides.
  Grader (`harness/grade.py`): Gemini 4 Argon, a different family from the model under test, at
  temperature 0 with a JSON schema. It sees prompt, decisive fact, criterion and reply, never the
  arm or the tool calls. Every pass must quote the reply verbatim and the quote is checked
  mechanically; a pass that fails the check twice is `grader_invalid`, reported and counted as
  neither. Calibration before any run is graded: per K task, an oracle reply (states the fact) must
  pass and a generic compliant reply must fail, in at least 38 of 40 each. Below that the grader
  is fixed and recalibrated before grading.

Secondary: attempts to reach the corpus by other routes (denied tool calls); false-trigger rate on G; input plus output tokens and wall time per run; write recall on
W+; write noise on W−; in S1, whether the skill was loaded at all (from the stream), so a null can be
read as "never triggered" or as "triggered and changed nothing".

## 7. Validity gates, checked before any primary is read

1. **P+ ceiling.** Search rate ≥ 0.90 and pass rate ≥ 0.60 on K. Below that, the corpus, the
   retrieval or the criteria are broken, and H2 is not interpreted.
2. **N floor.** Pass rate ≤ 0.10 on K after exclusion.
3. **Two instruments agree.** Tool calls counted from the stream equal `search_telemetry` rows by
   `NOX_AGENT_NAME`. Any mismatch stops the analysis until explained.
4. **Model.** Every run served the pinned model id.
5. **Connection failures.** At most 5% of runs per arm. Reported by arm, because a failure that
   depends on the arm is a result, not noise.

## 8. Design, analysis, decision rule

Each task runs 3 times in S0 and 3 times in S1. Totals: K 240, G 120, W 120, P+ 40, N 120, about 640
runs. The budget is set after a 5-run smoke test on tasks outside the bank: measured cost per run
times the run count, plus 30%, approved before the real run starts. First data point from the
isolation probe: a one-turn run with no tools cost US$ 0.14 cold and US$ 0.025 with a warm prompt
cache (about 35k tokens of system prompt). Runs with tool calls will cost more; the smoke test
measures how much. The `total_cost_usd` reported under subscription OAuth is notional; what it
spends is the subscription's usage allowance.

The unit is the task. Per task, the rate over its 3 replicas; Δ = mean over tasks of (S1 − S0); 95%
CI by bootstrap over tasks (10,000 resamples). With 40 tasks and an assumed per-task SD of Δ of
0.4, the minimum detectable effect is about 18 pp. A smaller real effect will read as a null, and
the report will say so.

Decision, fixed now:
- **The skill works** if the H2 CI lower bound is above 0, the false-trigger rate on G rises at most
  15 pp, and the median token overhead on G is at most 15%.
- **No detectable effect** if the H2 CI contains 0. That gets published as a short data note, as
  Paper C was.
- **The skill hurts** if the H2 CI upper bound is below 0, or the cost limits above fail.

## 8a. Smoke results that changed the design (2026-11-06, tasks outside the bank)

| what | finding | change |
|---|---|---|
| skill v0.1 | loaded in 0 of 3 S1 runs; in one, the agent never searched and gave generic steps | v0.2 rewrites only the `description`: it triggers on a requested change to a setting, default, retention or model, not on "what the task depends on", which the agent cannot see |
| skill v0.2 | loaded in 2 of 2 memory tasks and 0 of 1 generic task | none; n is tiny, the run decides |
| instruments | stream and `search_telemetry` agreed in 8 of 8 runs | none |
| cost | US$ 0.06 to 0.13 per run, mean about 0.09 | budget ≈ 640 × 0.09 × 1.3 ≈ US$ 75 notional |
| retrieval | the retention task failed in every arm that searched: memory holds both the May value (7 days) and the October one (5 days, weekend detection), and the agent used the older | none; this is what H2 and the P+ ceiling exist to show |

The description was tuned on smoke tasks, which are not in the bank, and is frozen with the bank.

## 8b. Pre-run gates (2026-11-06, before any S0/S1/P+ run)

**Grader calibration: passed.** 40 of 40 oracle replies passed and 40 of 40 generic compliant
replies failed (threshold 38 of 40 each); every pass quote checked verbatim; served model
`gemini-4-argon` on all 80 calls. Limit: this shows the grader separates the extremes only. A reply
carrying a wrong or outdated fact (the smoke retention case) is the hard case, and it rests on the
blind human sample.

**N leakage screen: done, floor gate passed.** 120 runs (40 K × 3), all rc 0, zero memory calls,
pinned model on all, US$ 8.41 notional. Excluded by the pre-registered rule (N passes 2 or more of
3): **K08, K12, K15, K38**. Over the 36 kept tasks N passed **0 of 108** (gate ≤ 0.10); over all 40,
11 of 120. One `grader_invalid` (K12): a pass whose quote was not in the reply. Primary analysis
uses the 36; the 40 are reported alongside, as declared in section 5.

## 8c. P+ ceiling gate FAILED (2026-11-06 23:10 BRT); S0/S1 not run

P+, 40 runs (one per K task), 0 rc != 0, pinned model on all, MCP connected in all, instruments
agree 40/40, US$ 4.08 notional. Search rate **1.00** (gate ≥ 0.90: passes). Pass rate **0.28** over
the 36 kept tasks (10/36, one `grader_invalid`), 0.35 over 40 (gate ≥ 0.60: **fails**). Per
section 7 the primary is not interpretable, so S0/S1 were not started.

Where the loss is. `nox_mem_search` returns, per hit, the source path and the **first 200
characters** of the chunk (`formatResults` in `src/search.ts`; the same in production, checked
read-only on 2026-11-06), and no MCP tool returns a chunk in full. The agent finds the right chunk
and sees its opening (K36: the decision on `enable_load_extension`, cut at "**Decisão:** **Yes,
habilita..."), then tries to read the file: 25 of 40 runs attempted Read/Bash on a corpus path and
were denied; 18 of those 25 failed. A crude token check (distinctive tokens of the decisive fact
found in the tool results) puts most of the 25 failures at partial or no presence of the fact.
So the ceiling is set by the product's MCP surface, not by whether the agent searches, which is
the thing the skill can change. A skill cannot raise H2 above a ceiling of 0.28.

The token check is coarse; the 200-character cut is not, it is in the source.

## 8d. Product fixed, P+ re-run PASSES (2026-11-07 08:00 BRT); main run uses nox-mem 3.8.0

Fix: nox-mem#52 (MCP search returns each hit's chunk id and whole text, 24,000-character budget
per call; new read-only `nox_mem_get`) and #53 (MCP stdout is JSON-RPC only on a fresh DB),
released as **nox-mem 3.8.0** (tag `v3.8.0`, `629bbe3`); the same #52 change is deployed on the
production host. Ranking is untouched, so the frozen DB and bank stand unchanged.

Harness re-frozen: `run_eval.py` counts `nox_mem_get` as a memory call; sha256 now
`cc3fd9f8af2cb708a4b58d6b25c5f30882500795772089bc7300404e2a270b50` (was `46a3d5e4…`). Nothing
else changed.

P+ re-run (40 runs, #52 build): 0 rc != 0, pinned model on all, instruments agree 40/40,
US$ 4.26. Search rate 1.00; pass rate **0.75** over the 36 kept tasks (27/36), 0.775 over 40
(gate ≥ 0.60: **passes**). Against the 200-character run, on the 36: 17 fail→pass, 1 pass→fail,
8 fail both, 9 pass both, 1 `grader_invalid`→pass. Attempts to read a corpus file: 25 → 1 of 40.
`nox_mem_get` was called in 1 run: whole text in the search output was enough.

The 200-character run is kept as recorded, not as a baseline: it measured the product's MCP
surface, not the skill. S0/S1 run on the 3.8.0 build.

## 8e. Main run results (2026-11-07, 480 runs, nox-mem 3.8.0)

Run `v1-main`: S0 and S1, 80 tasks × 3 replicas, interleaved. Notional cost US$ 16.80 (S0) and
US$ 19.18 (S1). Analysis script: `analyze.py` (kept with the run data, outside the repo).

**Validity gates (section 7), all pass:**

| gate | result |
|---|---|
| 1. P+ ceiling | search 1.00, pass 0.75 on the 36 (section 8d) |
| 2. N floor | 0 of 108 on the 36 (section 8b) |
| 3. Two instruments agree | 480 of 480 |
| 4. Model | `claude-sonnet-5-5` served on 480 of 480 |
| 5. Connection failures | 0 in each arm (MCP connected in 480, rc 0 in 480) |

Grader: 237 of 240 K replies graded, 3 `grader_invalid` (2 S0, 1 S1), counted as neither.

**Primary, unit = task, 95% CI by bootstrap over tasks (10,000 resamples, seed 1):**

| outcome | tasks | S0 | S1 | Δ (S1 − S0) | 95% CI |
|---|---|---|---|---|---|
| H1 search rate | 36 kept | 0.046 | 0.454 | +0.407 | [0.278, 0.546] |
| H2 pass rate | 36 kept | 0.065 | 0.306 | **+0.241** | **[0.130, 0.361]** |
| H1 search rate | all 40 | 0.042 | 0.433 | +0.392 | [0.258, 0.525] |
| H2 pass rate | all 40 | 0.125 | 0.358 | +0.233 | [0.133, 0.342] |

Per task on the 36: S1 above S0 on 13, below on 0, tied on 23.

**Cost limits (G set):** false-trigger rate (any memory call) 0.00 in S0, 0.10 in S1: **+10 pp**
(limit 15 pp). Median per-task token overhead S1 over S0: **+0.5%** (limit 15%; mean +19.6%, pulled
by the G runs that searched). Median wall-time overhead +2.3%.

**Decision (section 8, fixed before the run): the skill works.** The H2 lower bound is above 0
and both cost limits hold.

**Human agreement (2026-11-07 17:42 BRT).** The project owner graded a 20% sample blind (48
replies, 24 per arm, drawn with seed 20261107; arm, tool calls and the LLM verdict hidden; key
opened only after all 48 were filled). On the 45 the LLM grader resolved: agreement 43/45 (0.956),
**Cohen's kappa 0.89** (bar 0.6: passes). Both disagreements are LLM fail / human pass, one per
arm (S0 K32, S1 K33): the grader is slightly strict, not arm-biased. All 3 `grader_invalid`
replies of the run fell in the sample, and the human passed all 3 (S0 K15, S0 K38, S1 K11).
Sensitivity with those 3 resolved by the human verdict: H2 on the 36 is S0 0.065, S1 0.315, Δ
+0.250 [0.139, 0.370]; on all 40, Δ +0.225 [0.125, 0.333]. The decision does not change.
Per-item record: `human/agreement-v1.json` with the run data.

**Where the effect comes from (secondary, read after the decision):**

| arm | searched | n | pass |
|---|---|---|---|
| S0 | no | 103 | 0.029 |
| S0 | yes | 5 | 0.80 |
| S1 | no | 59 | 0.051 |
| S1 | yes | 49 | 0.61 |

When either arm searches, it passes near the P+ ceiling (0.75); when it does not, it almost never
passes. The skill works by raising how often the agent searches, and it is capped by that rate:
S1 still skips memory in more than half of the K runs. The skill body was loaded in 28 of 108 S1
runs on the 36 (26%). Those runs searched in 28 of 28 and passed 0.57. In the other 80, only the
skill's `description` was in context; they searched in 0.26 and passed 0.21, against 0.046 and
0.065 in S0. Most of the effect comes from the description alone, which matters for deferred arm
T (better MCP tool descriptions, no skill).

**Writing does not work.** W+ (the user states a decision): a write in 0 of 30 S0 runs and 1 of 30
S1 runs. W−: 0 writes in either arm, so no noise. The skill's writing half has no measurable
effect in this harness.

**Other routes to the corpus:** a denied attempt (Bash/Read on a corpus path seen in a search
result, or a blind look on disk) in 35% of S0 and 32% of S1 K runs. Not arm-dependent.

## 8f. Arm T, pre-registered 2026-11-07 17:55 BRT, before any T run of the bank

Section 8e found that most of S1's effect came from runs where only the skill's `description` was
in context. Arm T asks whether the MCP server itself can carry that guidance, with no skill. If it
can, the fix ships inside nox-mem and reaches every MCP client, not only Claude Code.

**Amendment to the section 2 definition of T** ("rewritten MCP tool descriptions, no skill").
In this harness the MCP tools are deferred: the model sees only their names until it calls
`ToolSearch`. In v1-main every one of the 59 K runs that searched called `ToolSearch` first, so a
tool description is read only after the decision to search. Descriptions alone can hardly move
H1. The MCP channel that is always in context is the server's `instructions` field of the
`initialize` result, which Claude Code places in the system prompt. T therefore uses both:

- `instructions` (1,198 characters): sections 1, 2 and 4 of the skill condensed, with the
  skill's trigger wording;
- `nox_mem_search` description rewritten (the old one said "FTS5 full-text search with BM25
  ranking", which is out of date, and said nothing about when to use it); `nox_mem_decision_set`
  description rewritten to say when to write.

The build is the pinned 3.8.0 copy with only `dist/mcp-server.js` changed (sha256 `0558262c…`,
was `f6161dd6…`); the exact change is `harness/arm-T-mcp-server.diff`. Probe, outside the bank,
one run per arm: asked to quote any nox-mem server instructions without calling tools, T quoted
the first sentence verbatim and S0 answered "none".

Harness: `run_eval.py` gains arm `T` (no skill, MCP from `--noxmem-t`). New sha256
`3e8edf061000288ab56d8db2458041b6b47c6d346def98504e7dbe2d70c0ddff`; nothing else changed.

**Design.** T on all 80 tasks × 3 replicas (240 runs), same bank, DB, model and grader. Controls
are the S0 and S1 runs of v1-main, run the same day on the same build. They are not concurrent;
that is a declared limit, and the gates are re-checked on the T runs.

**Primary: H2, T − S0** on the 36 kept tasks, bootstrap as in section 8. All 40 reported too.

**Decision, fixed now:**
- **The MCP text works** if the T − S0 H2 CI lower bound is above 0, and on G, T against S0
  stays within the section 8 cost limits (false triggers +15 pp, median token overhead 15%).
- **No detectable effect** if the T − S0 CI contains 0.
- **Secondary, T − S1**, reported with its CI. A CI upper bound below 0 means the skill does
  something the MCP text does not. A CI containing 0 does not show they are equal: the minimum
  detectable difference is about 18 pp.
- W+ write rate, H1, and how the effect splits by search, as in 8e.

## 8g. Arm T results (2026-11-07, 240 runs) and an erratum to 8e

Run `v1-T`: T on 80 tasks × 3 replicas, build `0558262c…`. Notional cost US$ 20.17. Analysis
script: `analyze_T.py` (kept with the run data).

**Gates on the T runs:** model `claude-sonnet-5-5` in 240 of 240; MCP connected and rc 0 in 240 of
240; the two instruments agree in 240 of 240. Grader: 118 of 120 K replies graded, 2
`grader_invalid` (K11, K38; K38 is an excluded task).

**Erratum to 8e.** `analyze.py` scored `grader_invalid` as fail, while section 6 says it counts as
neither. Under the registered rule, S1 − S0 on the 36 is **+0.250 [0.139, 0.370]** (14 tasks up,
0 down), not +0.241 [0.130, 0.361]; on all 40, +0.225 [0.125, 0.333]. These equal the 8e
sensitivity figures because the only invalid reply on the 36 (S1 K11) is the one the human passed.
The 8e decision does not change. The tables below use the registered rule for every arm.

**Primary, per-task means, bootstrap over tasks as in section 8:**

| outcome | tasks | S0 | S1 | T | T − S0 | 95% CI | T − S1 | 95% CI |
|---|---|---|---|---|---|---|---|---|
| H1 search | 36 kept | 0.046 | 0.454 | 0.778 | +0.731 | [0.602, 0.852] | +0.324 | [0.204, 0.454] |
| H2 pass | 36 kept | 0.065 | 0.315 | 0.556 | **+0.491** | **[0.352, 0.630]** | +0.241 | [0.102, 0.380] |
| H1 search | all 40 | 0.042 | 0.433 | 0.758 | +0.717 | [0.592, 0.833] | +0.325 | [0.208, 0.450] |
| H2 pass | all 40 | 0.142 | 0.367 | 0.600 | +0.458 | [0.325, 0.592] | +0.233 | [0.108, 0.358] |

Per task on the 36, H2: T above S0 on 23, below on 0; T above S1 on 17, below on 2.

**Cost limits (G set):** false-trigger rate S0 0.00, T 0.317: **+31.7 pp, limit 15 pp: FAILS.**
Median per-task token overhead T over S0 +1.8% (limit 15%: holds). The triggers fall on 7 of the
20 G tasks, and all 7 ask to change a configuration value (pool size, log rotation, default model,
Redis memory, Celery expiry, batch size, cron time). The instructions tell the agent to search
before changing "a setting, default, threshold, retention, schedule…"; the agent followed that
literally on settings of projects the corpus does not cover. S1 triggered on 4 of the same 7.

**Decision (section 8f, fixed before the run): "the MCP text works" is not reached.** The H2 lower
bound is well above 0, but the false-trigger limit fails. Section 8f did not name an outcome for
this case; under the section 8 wording for the skill, a failed cost limit counts against. What can
be said: the MCP text raises the pass rate (T − S0 +0.49 [0.35, 0.63]), and more than the skill does
(T − S1 lower bound above 0, against non-concurrent controls), at the price of a search on roughly
one in three unrelated configuration changes. Shipping it as is would break a limit set in
advance. A narrower trigger needs its own pre-registered run.

**Where the effect comes from (secondary):**

| arm | searched | n | pass |
|---|---|---|---|
| S0 | no / yes | 103 / 5 | 0.029 / 0.80 |
| S1 | no / yes | 59 / 49 | 0.051 / 0.63 |
| T | no / yes | 24 / 84 | 0.083 / 0.69 |

Same pattern as 8e: the arms differ in how often they search, not in what a search yields. T
searches in 78% of K runs against 45% in S1. Denied attempts to reach the corpus by other routes
fall to 15% of K runs (S0 35%, S1 32%).

**Writing still does not work.** W+: 0 of 30 T runs wrote (S1 1 of 30). W−: 0. The rewritten
`nox_mem_decision_set` description and the write rule in `instructions` had no measurable effect.

## 8h. Arm T2, pre-registered 2026-11-07 21:55 BRT, before any T2 run of the bank

Section 8g: T raised H2 by +0.49 but searched on 7 of 20 G tasks, all requests to change a
configuration value of software the corpus does not cover. T's trigger said "search before
changing a setting" with no statement of what the memory holds, so the agent could not tell a
setting the memory might cover from any other. T2 adds that statement.

**Change from T, and only this:** the first paragraph of `instructions` now names the memory's
scope, and the settings trigger applies only to that scope. The scope sentence was written from
the corpus's own "scope of this repo" and "interfaces" sections (its `CLAUDE.md`), not from the
task bank: "the nox-mem memory system itself (TypeScript; SQLite with FTS5, sqlite-vec and a
knowledge graph; hybrid search; salience; Gemini embeddings; its CLI, MCP server and HTTP API; how
it is operated in production), its evaluations and technical paper." The clause "the task
mentions a project, system or person you do not recognize" becomes "a project or person". A new
sentence says not to search for software outside that scope. The How and Write paragraphs and
both tool descriptions are unchanged. Instructions are now 1,593 characters.
`dist/mcp-server.js` sha256 `9243af17…` (T was `0558262c…`); the change against T is
`harness/arm-T2-mcp-server.diff`. In a product, the scope sentence would come from user
configuration; here it is a literal in the build.

Probe, outside the bank: asked to quote the nox-mem server instructions without tools, T2 quoted
the new first sentence verbatim.

**Design.** T2 runs on the K and G sets only (40 + 20 tasks × 3 replicas = 180 runs); W+ and W−
are dropped because section 8g showed no writing effect to protect. The harness is unchanged (sha
`3e8edf06…`): T2 is run as arm `T` with `--noxmem-t` pointing at the T2 build and label `v1-T2`.
Same bank, DB, model and grader. Controls are v1-main S0 and S1 and v1-T, not concurrent.
Analysis follows section 6 (`grader_invalid` counts as neither) with per-task means.

**Decision, fixed now:**
- **The scoped MCP text works** if the T2 − S0 H2 CI lower bound on the 36 is above 0, the G
  false-trigger rate is at most 15 pp above S0, and the median G token overhead over S0 is at
  most 15%. All three are needed.
- **No detectable effect** if the T2 − S0 CI contains 0.
- If H2 passes and a cost limit fails, the result is "not reached", as in 8g.
- **Secondary:** T2 − T on H2 with CI (what the narrower trigger costs on K; an upper bound below
  0 means the scope sentence also suppressed searches the K tasks needed). T2 − S1 with CI. H1 and
  the split by search, as in 8e.
- Known risk, declared now: some K tasks may read to the agent as outside the scope sentence, and
  T2 may search less than T on them. That shows in T2 − T.

## 8i. Arm T2 results (2026-11-07, 180 runs)

Run `v1-T2`: K and G sets, 60 tasks × 3 replicas, build `9243af17…`. Notional cost US$ 16.06.
Analysis script: `analyze_T2.py` (kept with the run data).

**Gates on the T2 runs:** model `claude-sonnet-5-5` in 180 of 180; MCP connected and rc 0 in 180 of
180; instruments agree in 180 of 180. Grader: 120 of 120 K replies graded, none invalid.

**Primary, per-task means, bootstrap over tasks as in section 8:**

| outcome | tasks | S0 | S1 | T | T2 | T2 − S0 | 95% CI |
|---|---|---|---|---|---|---|---|
| H1 search | 36 kept | 0.046 | 0.454 | 0.778 | 0.750 | +0.704 | [0.574, 0.824] |
| H2 pass | 36 kept | 0.065 | 0.315 | 0.556 | 0.528 | **+0.463** | **[0.315, 0.611]** |
| H1 search | all 40 | 0.042 | 0.433 | 0.758 | 0.725 | +0.683 | [0.550, 0.808] |
| H2 pass | all 40 | 0.142 | 0.367 | 0.600 | 0.575 | +0.433 | [0.300, 0.575] |

Per task on the 36, H2: T2 above S0 on 21, below on 0.

**Cost limits (G set):** false-trigger rate S0 0.00, T2 0.017 (1 of 60 runs, task G08, embedding
batch size): **+1.7 pp, limit 15 pp: holds** (T was +31.7 pp). Median per-task token overhead
T2 over S0 **+2.1%** (limit 15%: holds).

**Decision (section 8h, fixed before the run): the scoped MCP text works.** The H2 lower bound is
above 0 and both cost limits hold.

**Secondary:**
- T2 − T, H2 on the 36: −0.028 [−0.139, +0.083] (3 tasks up, 6 down); H1 −0.028
  [−0.120, +0.074]. No detectable cost of the scope sentence on K. The CI does not exclude a loss
  of up to 14 pp, so this is not shown to be zero.
- T2 − S1, H2 on the 36: **+0.213 [0.102, 0.333]** (13 up, 1 down). The scoped MCP text beats the
  skill on accuracy, against non-concurrent controls.
- Split by search: T2 searched 81 of 108 K runs on the 36 and passed 0.68 when it did; 0.07 when
  it did not. Same pattern as every other arm.
- Denied attempts to reach the corpus by other routes: 15% of K runs (T 15%, S0 35%, S1 32%).

**What this does not show.** The scope sentence was written by hand for this corpus. Every K task
falls inside it by construction, and every G task names software plainly outside it, so the
boundary was easy here. A real memory covers several projects, and the line between "our service"
and "the memory's scope" will be blurrier. In a product the sentence must come from user
configuration or be derived from the store, and neither route was tested. One model, one harness
(section 9). Writing was not re-tested (W sets dropped; 8g showed no effect).

## 8j. Disposition (2026-11-08): the scoped MCP text ships, the skill is archived

**What shipped.** nox-mem 3.9.0 (tag `v3.9.0`, PR #55) puts the T2 text in the MCP `initialize`
result when `NOX_MEM_SCOPE` is set; `src/mcp-instructions.ts` pins the T2 and T texts byte for byte
against the builds that were run. 3.9.0 still sent the T text by default, i.e. the text that failed
the false-trigger limit in 8g; 3.9.1 (tag `v3.9.1`, PR #57) sends nothing without a scope and keeps
T only behind `NOX_MEM_INSTRUCTIONS=unscoped`. `NOX_MEM_INSTRUCTIONS=off` disables it, scope or not.
Both versions are on npm (`latest` = 3.9.1).

**Where it runs.** On the owner's production host the MCP server serves two clients. The owner's
Claude Code (through a local shim) gets the T2 text with a scope sentence written for the owner's
projects; the sentence lives only in an unversioned env file on the host. The OpenClaw agents get
`NOX_MEM_INSTRUCTIONS=off`: T2 was measured on Claude Code with a coding corpus, never on those
agents, so turning it on for them is a separate experiment, not a config change.

**The skill is archived.** It worked (8e: +0.25 [0.14, 0.37]) but T2 beat it (8i: +0.21
[0.10, 0.33] over S1, non-concurrent controls) and needs no install step, and its body loaded in
26% of S1 runs, so most of its effect came from the description alone. `skills/nox-mem-memory/`
stays on this local branch, marked archived, and is not published. Writing remains unsolved: no arm
moved W+ off 0/30.

**Real-use check, pre-registered 2026-11-08 before any post-deploy session existed.** Script and
baseline outside git (`nox-skill-eval/real-use/`). Unit: top-level Claude Code session with >= 3
assistant messages; BEFORE = sessions started in the 28 days before the deploy (2026-11-08 17:45
UTC); AFTER = sessions started after it; sessions spanning the deploy are excluded. Frozen
baseline: 278 sessions, 0 `nox_mem_search` calls. Rule: "it searches now" if the share of AFTER
sessions with a search is >= 0.20 and >= 0.15 above BEFORE, with n_after >= 20; "too eager" if the
median nox-mem result size exceeds 20,000 chars per session or more than 80% of sessions search;
otherwise "no visible change". Hit quality is not measured by the script: 10 calls are read by hand.
First reading scheduled for 2026-11-15. This is an uncontrolled before/after on one user, not a
trial: task mix changes week to week.

**Next steps, in order.**
1. 2026-11-15: read the real-use report, apply the rule above, read 10 searches by hand.
2. Writing: design an arm that moves W+ (no tested text did); candidates are a hook that proposes
   `nox_mem_decision_set` when a decision is stated, or a tool result that asks for it.
3. OpenClaw agents: a pre-registered run of a scoped text on the agents, which today do not search
   at all; only after step 1.
4. Scope without hand configuration: derive the scope sentence from the store and test it against
   a hand-written one; untested so far, and the only route that serves npm users who set nothing.
5. Optional: a data note on this evaluation (sections 8e to 8j).

Backups of this local branch (git bundle) and of the run data: the owner's `~/Backups` and the
research host, sha256-verified at the destination. The upstream repository is public, so this
branch is not pushed.

## 9. Limits, declared now

One model, one harness (Claude Code). Claims do not extend to Cursor or Codex without their own run.
The tasks are written by the team, not drawn from real users. The corpus is one project's
engineering docs. Single sessions only: nothing here measures long sessions or real traffic.

## 10. Use of the result

The listing text for the skill cites a number only if H2 passes, and cites it with its CI and these
limits. (Superseded 2026-11-08: the skill is archived, see 8j; the README of 3.9.0+
cites the T and T2 numbers with these limits.) Publishing anything waits for the first step of D-2026-11-04 (fixing the product's claims).
