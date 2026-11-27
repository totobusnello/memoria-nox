# Does the agent write, and does a derived scope work? Two use studies, pre-registered

v1.0, 2026-11-26. Written, with the code it names, before any run of the task bank in a new arm.
Only the mechanics smoke and one probe in section 8 have run, on tasks outside the bank. The project
owner approved both studies on 2026-11-26 («pode rodar o 12»; «ok 30 fecha, pode seguir com o
resto», a ceiling of US$ 30 for study S).

Both studies extend the 2026-11-07 evaluation reported in *The memory the agent does not consult*
(doi:10.5281/zenodo.24408078; protocol, bank and harness in `../note-unconsulted-memory/`). There,
an MCP server instruction with a scope sentence (arm T2) raised the pass rate on tasks that need
memory from 0.065 to 0.528, +0.463 [0.315, 0.611], with 1 false trigger in 60 runs on tasks that do
not. Two questions were left open, and this file fixes how each is answered.

- **Study W (writing).** No arm ever made the agent record a decision the user stated: 0 or 1 of 30
  runs in S0, S1 and T. T2 itself was never run on the writing tasks. Does T2 write, and does a
  stop hook or a reminder in the tool results make it write more, without writing on tasks that
  hold nothing worth keeping?
- **Study S (scope).** The scope sentence of T2 was written by hand. In a product it has to come
  from the user's configuration or from the store itself. Does a sentence derived from the
  database, by a fixed rule and with no LLM, work as well?

## 1. Frozen artifacts

| artifact | sha256 |
|---|---|
| bank `tasks-v1.jsonl` (K40, G20, W+10, W−10), unchanged since 2026-11-06 | `0c877ad186696428d60e923bd2ee2982a3b3043c00fb9e5ce12229bc1d17e41a` |
| eval DB `eval-a819385.db` (1,382 chunks), unchanged | `869ddf6d68491dfcb02b71ed0869d13ba1fc977bf8e54b857912b437569dbf64` |
| T2 build `nox-mem-3.8.0-T2/dist/mcp-server.js`, as run on 2026-11-07 | `9243af178447be6cfea8f906dbc54c945bcc5e6a44325ab63f51881457dfaa84` |
| SD build `nox-mem-3.8.0-T2-SD/dist/mcp-server.js` (= T2 + `arm-SD-mcp-server.diff`) | `8b413c06492668ac478e91ffb0b35b155386ec9ba0e86e726d494ae10ce09038` |
| WN build `nox-mem-3.8.0-T2-WN/dist/mcp-server.js` (= T2 + `arm-WN-mcp-server.diff`) | `b222c1974b01b50059cb4a6c11fa583cff880c30b805645b65c46da7f1baf004` |

The scripts in this directory are frozen by the commit that carries this file and by the tag
`use-studies-prereg-v1.0`.

## 2. Arms

Every arm runs the T2 build of 2026-11-07, so each differs from the measured T2 in one thing.

| arm | study | the one change |
|---|---|---|
| W0 | W | none: T2 as measured (control) |
| WH | W | a project Stop hook (`stop_hook.py`) blocks the first stop once with: *"Before you finish: if the user stated a decision, rule or ownership in this task that should still hold next time, record it now with nox_mem_decision_set (stable slug key, with the reason). If nothing like that was stated, finish without writing anything."* The second stop always ends the run. |
| WN | W | every result of a nox-mem read tool ends with one line: *"[nox-mem] If the user has stated a decision, rule or ownership in this task that should still hold next time, record it now with nox_mem_decision_set (stable slug key, with the reason)."* Write tools are unchanged. |
| WP | W | the prompt starts with *"Record in nox-mem memory any decision I state here."* Positive control: the ceiling of the instrument. |
| SD | S | the scope sentence is the one `derive_scope.py` builds from the eval DB, in place of the hand-written one |

The derived sentence, fixed now (320 characters; the rest of the T2 text is unchanged):

> the notes in this store (1382 passages, most from DECISIONS, INCIDENTS and
> 2026-05-21-G10d-ablation-execution), about VPS, API, Phase, Gemini, LLM, CLI, Toto, Wave, JSON,
> BM25, FTS5, LoCoMo; recurring identifiers: ops_audit, nox-mem-api, withOpAudit,
> gemini-2.5-flash-lite, kg_entities, NOX_DB_PATH, nox-mem, source_file

The hand-written sentence it replaces: *the nox-mem memory system itself (TypeScript; SQLite with
FTS5, sqlite-vec and a knowledge graph; hybrid search; salience; Gemini embeddings; its CLI, MCP
server and HTTP API; how it is operated in production), its evaluations and technical paper.* The
rule in `derive_scope.py` was written once and run once; it was not tuned against any reply. It is
crude on purpose: it is what a product could compute from any store without a model.

## 3. Harness

`run_use.py` imports the 2026-11-07 runner (`run_eval.py`) unchanged and adds the per-arm change.
Same model pin (`claude-sonnet-5-5`, served id read from each stream), same isolation (`env -i`,
project settings only, strict MCP config, a fresh copy of the frozen DB per run, empty cwd, English
pinned), same 420 s timeout and US$ 1 per-run budget.

**One deviation, and why.** Claude Code is 2.1.332 now; it was 2.1.319 on 2026-11-07. In the smoke
of section 8 the agent ran `Bash` (an `ls` of its empty cwd) under `--permission-mode dontAsk`,
which 2.1.319 denied. From the cwd it could have reached the run's copy of the database and skipped
the MCP. The runner now passes `--disallowedTools` for the built-in tools (Bash, Read, Grep, Glob,
Write, Edit, NotebookEdit, WebFetch, WebSearch, Task, Agent); a probe asking for `Bash` got *"No
such tool available"*. This restores the 2026-11-07 condition. A denied call no longer appears in
`permission_denials`; it is counted from the tool calls instead (gate 4).

## 4. Runs

| study | arms | tasks | replicas | runs |
|---|---|---|---|---|
| W | W0, WH, WN, WP | W+ (10), W− (10) | 3 | 240 |
| S | SD | K (40), G (20) | 3 | 180 |

Order randomized within each study (seed 20261126), arms interleaved. Study W runs first. Study S
compares SD with the 2026-11-07 runs of S0 (`runs/v1-main`) and T2 (`runs/v1-T2`): a
non-concurrent comparison, chosen to keep within the US$ 30 ceiling. Between the two dates the
model pin, the build, the DB, the bank and the grader are the same; Claude Code's version is not.
The report states this next to every number of study S.

## 5. Outcomes

**Study W.**
- *Primary, W+ content*: the run has at least one memory write call (`nox_mem_decision_set`,
  `nox_mem_ingest`, `nox_mem_crystallize`) whose content captures the decision the user stated.
  Judged by the 2026-11-07 grader (Gemini 4 Argon, temperature 0, JSON schema), given the task, the
  stated decision as the decisive fact, the task's pass criterion and the text of the run's write
  calls; a pass must quote that text verbatim and the quote is checked mechanically. A W+ run with
  no write call fails without a grader call. `grade_use.py`.
- *W+ wrote*: any write call, whatever its content (comparable to the 2026-11-07 counts).
- *W− wrote*: any write call on a task with nothing worth keeping (noise).

**Study S.** As on 2026-11-07: *K pass* (H2, the decisive fact used, same grader, same criterion),
*K searched* (H1, at least one `nox_mem_search`), *G false trigger* (at least one `nox_mem_search`
on a G task). K tasks K08, K12, K15 and K38 stay excluded by the 2026-11-07 leakage screen.

## 6. Analysis

`analyze_use.py`, written before any bank run. The unit is the task: per task, the rate over its
replicas; a contrast is the mean over tasks of the per-task difference, with a 95% CI by bootstrap
over tasks (10,000 resamples, seed 1). Validated before freezing: fed the 2026-11-07 T2 runs in place
of SD, it returns SD − T2 = 0 and SD − S0 = +0.463 [0.315, 0.611], G +0.017, the published values.

## 7. Gates and decision rules, fixed now

Gates, checked before any primary is read; a failed gate means the primary is not interpreted:
1. every run served `claude-sonnet-5-5`;
2. connection failures at most 5% of the runs of each arm, reported by arm;
3. tool calls counted from the stream agree with `search_telemetry` rows of the run;
4. no run executed a built-in tool (any call is listed; the run is reported and dropped);
5. study W only: the ceiling arm WP reaches a W+ content rate of at least 0.70. Below that the
   writing tools, the grader or the tasks are broken, and no W contrast is interpreted.

**Study W**, for WH and for WN, each against W0 (two contrasts, no correction; the report says so):
- **works** if the lower bound of the W+ content CI is above 0 **and** the W− write rate rises at
  most 15 pp over W0;
- **hurts** if the upper bound of the W+ content CI is below 0;
- otherwise **no detectable effect over W0**.
W0 against the 2026-11-07 arms is reported as a description, not a test: T2 was never run on the
writing tasks, and a T2 that already writes would change what the paper says about writing.

**Study S:**
- **the derived scope works as well as the hand-written one** if SD − T2 on K pass has a lower bound
  above −0.10 (non-inferiority margin of 10 pp), SD − S0 on K pass has a lower bound above 0, and
  the G false-trigger rate rises at most 15 pp over S0 (the T2 rule of 2026-11-07);
- **beats no instructions but is not shown within 0.10 of the hand-written one** if only the last
  two hold;
- otherwise **fails the T2 rule**.
With 36 tasks the CI of a difference is about ±0.15 wide; a non-inferiority call at 0.10 may come
back inconclusive, and the report will say so rather than widen the margin.

**Stopping and spending.** Each study runs once, in full; no peeking at primaries mid-run. The
Claude runs use the subscription's allowance, as on 2026-11-07 (their `total_cost_usd` is
notional). Money is spent on the grader and on query embeddings, both Gemini, measured from the
provider; study S stops if its real spend reaches US$ 30. Study S phase 2 (the same SD test in a
second client) is not part of this registration and runs only if study S passes.

## 8. Before freezing (outside the bank)

- Mechanics smoke, 2026-11-26, one task written for it (a reflect-cache retention decision), one run
  per arm W0, WH, WN, WP: the WN reminder appeared in the tool results, the WH hook reason appeared
  in the stream, every arm served the pinned model, and every arm wrote once or twice. This is one
  task, outside the bank; it is not a result.
- A second smoke on the 2026-11-06 smoke task `smoke-ret`, arms W0 and SD, after the built-in tools
  were denied: both searched, telemetry agreed, no built-in call.
- Probe: a task asking for `Bash` got *"No such tool available: Bash."*

## 9. Limits, declared now

One model, one client, one corpus (the public docs of this repository), 10 tasks per writing set.
The writing tasks state the decision openly; a decision implied over a long conversation is not
tested. Study S is non-concurrent (section 4). The derived sentence names the owner of the store
("Toto") because the corpus does; a product would have to decide whether a scope sentence may carry
names.
