# Where our construction tax actually is — 2026-10-26

**Question.** The Memory Tax paper (UIUC/Tsinghua, published 2026-10-26) decomposes the net value
of an agent memory system against naive RAG, and its *faithfulness* axis asks what the construction
step discards before any retrieval happens. It measures this on a bench: one builder, one pass, a
static corpus. We have something no bench has — a distiller that has been running on a live corpus
for seven months, with its own log, and a raw archive to compare against. So: how much of our own
corpus never became memory, and why?

This is a feasibility probe for that measurement, not the measurement. It is entirely read-only
(`?mode=ro`, no `searchHybrid` call, so no telemetry row and no `access_count` bump) and cost zero.

**Snapshot.** `2026-10-27 01:08 UTC`. The distiller ran *during* this probe — `built_window` and
`log_window` both end `01:01` — so the population moves while being measured, and every figure
below is stamped rather than stated as standing.

## The three sides, and the key that joins them

| side | address | n |
|---|---|---|
| built | `chunks.source_file = sessions/<agent>/<agent>:<uuid>` | 6,898 chunks in 314 sessions |
| the distiller's own log | `session_distill_log.session_key = <agent>:<uuid>` | 2,498 rows |
| raw | `/var/lib/nox-mem/action-archive/<dir>/<uuid>.jsonl` | 1,610 transcripts, 493 MB |

The session uuid is the join key, and **both of the first two readings of it were wrong.** Both
errors inflated the loss, and both were caught by controls rather than by inspection.

### Defect 1 — the log is keyed by (agent, session), not by session

2,498 rows hold **1,931 distinct uuids**: 567 collisions, 453 sessions logged under more than one
agent. Keying a dict by uuid lets the last row read win. In **63** of those collisions the agents
*disagree* — one extracted chunks from the transcript, another recorded zero — so the silent
overwrite decided those cases by file order.

| | keyed by row | aggregated per session (`max`) |
|---|---|---|
| non-trivial sessions (≥3 msgs) with zero chunks | 114 | **45** |
| largest `message_count` among them | 2,097 | **393** |
| of those with 100+ messages | 75 | **8** |

The 2,097-message session that made the first version of this finding dramatic **did** leave
memory, under another agent.

### Defect 2 — "is this directory in scope?" cannot be answered by its name

The raw side spans 11 directories; only 7 ever produced a chunk. The obvious test — does the name
contain `agents-` — puts `-root--openclaw-workspace` outside, and that directory is 649 files, 40%
of the whole archive. It is the `main` agent's own cwd: its 59 built sessions equal
`built_by_agent[main] = 59` exactly. The test that works is behavioural — a directory is in reach
if it ever produced a log row or a chunk:

| genuinely out of reach | transcripts | ever logged or built |
|---|---|---|
| `-root`, `-tmp`, `-root-medicoes-7b`, `-root--openclaw-workspace-skills` | 54 | **0** |

Those 54 are Claude Code sessions started from other working directories; the distiller iterates
agent ids and can never list them. They are out of scope by design and come out of the loss count.
**1,556 transcripts remain in reach.**

## Result — the three outcomes, and which of them is tax

371 + 991 + 194 = 1,556, so the partition is exhaustive (asserted in the script).

| outcome | n | median file | > 1 MB | what it is |
|---|---|---|---|---|
| never reached the log | **371** | 105 KB | 16 | **operational tax** — see below |
| logged, yielded nothing | 991 | 241 KB | 1 | almost entirely by design |
| logged, produced chunks | 194 | 675 KB | 37 | the measurable window |

### The 45 non-trivial zeros do not survive contact with the raw text

Only **5 of the 45** still have a raw transcript — the other 40 were pruned before the archive
existed (the log reaches back to 2026-03-31, the archive to mid-August), so they support no claim
in either direction. Reading those 5: real user/assistant prose runs **192 to 3,500 characters**,
in files of 55 to 541 KB. The weight is tool output and reminder envelopes, not dialogue.

🔑 `message_count` is written **before** the noise filter (`session-distill.ts:384` against
`:478`), so it counts heartbeats and tool turns as messages. Reading it as a measure of content is
what produced "sessions with 100+ messages left nothing". **A session holding 192 characters of
prose yielding zero chunks is the distiller working, not failing.** The construction tax from "the
LLM discarded substantive sessions" is *not established by this probe*, and the earlier claim that
it was is withdrawn.

### What is established: 259 transcripts the distiller never saw, holding 4.5M characters of prose

Of the 371 never-logged transcripts, **259 (69.8%) hold ≥ 2,000 characters** of real
user/assistant prose — 4,489,370 characters in all, across 86 MB of files. Every one of the 16
over 1 MB holds prose:

| file | prose chars | turns | prose / file |
|---|---|---|---|
| 2.57 MB | **978,624** | 102 | 38.1% |
| 4.76 MB | 265,320 | 50 | 5.6% |
| 3.31 MB | 145,316 | 59 | 4.4% |
| 1.04 MB | 130,038 | 26 | 12.5% |
| the other 12 | 11.8k – 21.0k | 7 – 28 | 1.2 – 2.0% |

**The separation is settled by the code, not by hypothesis.** When the noise filter empties a
conversation, `session-distill.ts:397` does `continue` *without writing a log row*; on every other
path a row is written. So no row **and** real prose means the session was never listed — which is
the operational component: the 7-day prune of the live session directories, `lookbackDays = 30`,
and `maxSessionsPerRun = 50`. The distiller reads the live directories and never the archive, so a
transcript pruned before its turn came is gone from the builder's reach while still sitting in the
archive.

This is also why the planned next step — copy the database and run `isNoise` against the copy,
because `isNoise` writes to `noise_prototypes` — **is not needed**. Counting the prose answers the
same question for free.

### It is concentrated, and it is concentrated on the two heaviest agents

| directory | files | never logged | logged zero | produced | never-logged with prose |
|---|---|---|---|---|---|
| `-root--openclaw-workspace` (main) | 649 | 25 | 565 | 59 | 1 |
| `agents-forge` | 415 | 120 | 280 | 15 | 79 |
| `agents-boris` | 298 | **162** | 50 | 86 | **136** |
| `agents-nox` | 111 | 22 | 77 | 12 | 13 |
| `agents-cipher` | 54 | 30 | 14 | 10 | 26 |
| `agents-lex` | 18 | 7 | 3 | 8 | 2 |
| `agents-atlas` | 11 | 5 | 2 | 4 | 2 |

The failure mode differs by agent, which a single aggregate hides. **boris loses by never entering
the log** (162 of 298, and it owns 41 of the archive's large files); **nox loses after entering it**
(77 of 111 logged and empty). A fix aimed at one does nothing for the other.

### Size predicts survival, monotonically

| file size | n | survived | rate |
|---|---|---|---|
| 0–50 KB | 92 | 1 | 1.1% |
| 50–200 KB | 565 | 9 | 1.6% |
| 200 KB–1 MB | 845 | 147 | 17.4% |
| 1–5 MB | 51 | 34 | 66.7% |
| > 5 MB | 3 | 3 | 100% |

Monotonic across four orders of magnitude, which is what a *capacity* limit looks like rather than
a content judgement — and it is the wrong direction for memory to be useful, because the long
sessions that most need summarising are the ones that survive, while the operational loss falls on
everything else.

## The measurable window for the QA replay

| | n | chunks |
|---|---|---|
| both sides present | **194** | 2,266 = **32.9%** of the 6,898 |
| built, raw already pruned | 120 | 4,632 — not measurable |

Control: zero sessions have chunks while their log row says zero (`built_but_log_says_zero_n = 0`),
so the two routes to "this session produced memory" agree.

## What this changes

- **The claim to make is about the operational component, not the LLM's judgement.** 259 sessions
  holding 4.5M characters of prose were never offered to the builder. Every paper in the 2026-10-26
  batch measures a builder that is offered its whole corpus exactly once; none of them can see
  this, because a bench has no prune, no window and no per-run cap.
- **Two numbers reported earlier are withdrawn**: "114 non-trivial sessions lost irreversibly" (the
  join key was wrong; it is 45, of which only 5 are auditable and those 5 look correct) and "441
  ambiguous between never-reached and all-noise" (54 were out of scope by design, and the ambiguity
  is resolved by the code path plus a prose count: 371, of which 259 hold prose).
- **`isNoise` against a copy is off the list.** The cheaper instrument answers it.
- **The replay is still the open leg.** Unit-level loss is not answer-level loss, and converting one
  into the other needs queries generated from the raw side of those 194 sessions.

## Limits

- The prose counter approximates what `isNoise` would keep: it drops tool results, `<system-reminder>`
  and `<command-name>` envelopes, and one-word turns. A filter far more aggressive than that could
  empty a transcript this counter calls substantive. For the 16 large files the margin makes the
  question moot — no plausible noise filter empties 978 KB of dialogue in 102 turns — but for the
  smaller ones the 2,000-character threshold is a choice, not a measurement.
- 40 of the 45 non-trivial zeros are unauditable, so "the distiller discards substantive sessions"
  is *unmeasured*, not refuted.
- `maxSessionsPerRun`, `lookbackDays` and the 7-day prune are named in the code as the mechanism,
  but their individual contributions are not separated here. That needs the distiller's run history,
  not the corpus.
- The population moved during the probe. Re-running the scripts will not reproduce these counts
  exactly, by design rather than by flakiness.

**Artifacts.** `audits/2026-10-26-construction-tax-probe.py` (the three-sided census),
`audits/2026-10-26-nontrivial-zeros-audit.py` (the 45 against the raw text),
`audits/2026-10-26-never-logged-prose.py` (the 371 separated by prose). Outputs stay on the host
(`/root/medicoes/2026-10-26-memory-tax/`): the corpus is private and this repository is public.
