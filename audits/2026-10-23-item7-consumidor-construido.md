# Nobody was searching, and that included me. So we built the question.

**2026-10-23, same day as the pull experiment.** The morning measured that the
agent *will* search when a task needs the corpus
(`2026-10-23-item7-pull-degraus-1-2.md`). The afternoon asked the obvious next
question — *who actually searches today?* — and the answer reframed the whole
item.

## The 30-day census

Every row of `search_telemetry` in the last 30 days, by `requesting_agent`:

| surface | rows | what it is |
|---|---|---|
| `probe:semantic-canary` | 422 | the 30-minute canary |
| *(null)* | 224 | pre-13/10, before the column had a writer |
| `probe:*` (other) | 152 | my own probes, today and on 14/10 |
| `mcp:unknown` | 9 | **me, at 12:41 today** — the pull experiment |
| `cli:unknown` | **4** | 18/10 and 23/10 |
| `http:unknown` | **1** | 14/10 |

Outside the canary and my own instrumentation: **five searches in thirty
days.** The daily volume is a flat 48 — exactly the canary's two per hour.

## The part that was not about the agents

The `nox-mem` MCP on the user's Mac is not broken. It is configured as an SSH
transport into the production server, and the last connection log shows a
clean handshake in 2.7 s with all tools negotiated. It works.

And `requesting_agent LIKE 'mcp:%'` had **zero rows in the entire table** until
my own experiment today.

> I have had that tool available for days and never once called it. Across
> three days of audits *about this corpus*, I reached it through `ssh` and
> `sqlite3`, every single time.

Not laziness. My questions were **censuses** — *how many triples have evidence
in the vault*, *which columns have no writer*, *what is the distribution of
dates*. A census wants SQL. Hybrid search answers **retrieval** — *find me the
passage that says X*. Those are different operations, and only one of them had
come up.

This is the finding that generalises past this system: a retrieval index with
no traffic is not necessarily unwanted. It can be perfectly good at an
operation nobody currently needs to perform. **Zero searches measures the
shape of the questions, not the quality of the answers** — and no amount of
better ranking, lower latency or richer graph moves it.

## So the task was built, not waited for

If the diagnosis is "no task needs the corpus", the test is to create one that
genuinely does — and the honest version of that is not a synthetic errand.
82.2% of the graph's evidence sits in the private document vault, which is
contracts. Contracts carry dated obligations. Nobody was scanning them.

**Two legs, because two different questions are involved:**

| leg | question | tool | why |
|---|---|---|---|
| 1 | which documents mention a date in the window, near a deadline term? | SQL over all 27,166 vault chunks | census: exhaustive, cheap, deterministic |
| 2 | was this one amended, renewed or terminated since? | the agent, searching | retrieval: the answer is elsewhere in the corpus |

Building leg 1 as semantic search would have repeated the exact error the
census diagnosed. The measurement's own lesson had to survive contact with the
thing it motivated.

### Measured, two full runs in production

| | run 1 | run 2 |
|---|---|---|
| candidates from the scan | 33, in 14 files | 33, in 14 files |
| obligations the agent confirmed | 5 | 5 |
| **searches the agent issued unprompted** | **11** | **6** |
| wall clock | 2m41s | 2m16s |

The prompt never names the tool. That is deliberate: whether the agent reaches
for the corpus on its own is part of what the run measures, and naming it
would answer the question by construction.

One result is worth more than the counts. For one obligation the agent found,
by searching, that a **later draft of the same instrument exists with a
different formula**, and flagged it: check the signed version before paying.
The mechanical scan could never produce that — it is precisely the retrieval
half.

## Three defects, each found by a number being wrong

1. **Position must come from the match.** Looking up the formatted date in the
   text *after* already matching it fails for dates written out in words, and
   the year-based fallback points at the first occurrence of the year in the
   chunk, which is usually somewhere else.
2. **A proximity filter can be tighter than the document.** Requiring a
   deadline term within 180 characters of the date cut 33 candidates to 1, and
   the discarded ones were real obligations: in legal prose the term sits in
   the clause heading. This vault's median chunk is **3,079 characters**
   (p90 3,930), so 360 covered 12% of it. Requiring the term *in the chunk* is
   all the proximity this corpus supports.
3. **The probe was writing inside what it measures.** The watcher indexes
   `workspace/memory` wholesale, and it ingested the report and the scan JSON
   into the corpus — 19 chunks, removed the same day behind a pre-op snapshot.
   The scan itself is immune (it filters on the vault path), but the **agent**
   is not: next week it would search for an amendment and receive its own
   previous conclusion as evidence. Output now lives outside both watched
   trees.

Defect 2 is the one worth carrying. 33 → 1 does not look like a bug; it looks
like a clean corpus with nothing due. **A filter that is too strict and a
world with nothing in it produce the same number**, and only measuring each
rung of the sieve separately tells them apart.

## What this does and does not settle

- **Settled:** the agent searches when the task requires it, now in a
  recurring job and not only in a probe — n=2, 17 searches total, against a
  baseline of zero rows on that surface in the table's entire history.
- **Settled:** zero traffic was never evidence that retrieval is unwanted. It
  was evidence that the questions being asked were censuses.
- **Not settled:** whether the output is *useful*. Five obligations were
  surfaced and one carried a real warning, but value is the reader's verdict,
  not the job's. If the weekly report is read and changes something, item 7
  has a consumer and items 4, 6 and 11 reopen with an object. If it is ignored
  for two weeks running, that is item 7's answer and the pull side closes.
- **Not settled:** attribution. The surface still records `mcp:unknown`, so
  these 17 searches are attributable only by timestamp and window. Step 3 of
  the pull experiment — spontaneous traffic across all six agents — remains
  blocked.
- **Scope:** one job, one agent, one corpus, two runs on the same day. The
  candidate count is stable because the corpus did not change between runs,
  not because the scan was shown to be stable over time.

**Artifacts.** `openclaw-vps/infra/scripts/{lex-prazos-semanal.sh,
contratos-prazos-scan.py}` (PR #49), cron in three places because the crontab
is generated by an applier. The reports themselves stay on the host: the vault
is private and this repository is public.
