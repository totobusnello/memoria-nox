# Spare capacity, narrow surface: the exposure record of a production agent-memory system

> **Correction:** the title changed on 2026-08-29, and the reason belongs to the paper itself. It used to be
> *"Spare capacity, starved coverage"*, and adversarial review pointed out two flaws in the
> metaphor. First, the coverage channel is not starved: it exhausts the eligible pool at 100% on every measured day
> (inside the defective-ingestion regime, §4.3.1). It is the corpus that is starved, not the coverage, so the image inverted the mechanism
> described in the body. Second, *starved* is normative, and §4.5 explicitly refuses that judgment:
> "a reader who concludes 'the system is losing valuable information' has gone beyond what was
> measured".
>
> On 2026-10-05 the title changed again. The previous one ended *"what a production agent-memory
> system actually surfaces"*, which used "actually" as an intensifier and repeated surface/surfaces;
> the new title is the author's decision on a reviewer's suggestion.

> **Status (2026-10-05).** v1.0 of this manuscript (Portuguese) was published on Zenodo on
> 2026-08-30 (`10.5281/zenodo.22181415`). This is v1.1: the text revised after the 2026-09-21
> corrections and the 2026-10-04 audit of aged claims (Appendix F), translated to English, and
> deposited on 2026-10-05 as v1.1 of that record under the version DOI reserved for it,
> `10.5281/zenodo.23163119` (version 2 of concept `10.5281/zenodo.22181414`). Rule of this file: where there is a
> number, it comes from an artifact locked by `--assert-json` and its reproduction command is
> cited, except the numbers the text itself flags as having no preserved artifact: the
> 7,908 (81%) of §4.3.2; the 5.6× partial-day reading and the 1,971, 10,926 and 20.5 days of
> §4.3.1; the strata counts of §5.7 (1,139 / 951 / 311 / 57 and 14 / 61 / 89 / 186); the 617 of
> the last table row of §6; the 19 of 32, the 0 of 32 and the 591,323 of §6.1; the pre-cleanup
> warning density (87 markers, 77 of 288 paragraphs, 26.7%) and the per-section densities of
> Appendix F; the survey counts of §1 and the 46.9% of §6 (the last two marked "—" in Appendix D).
>
> Sources: `SUPERFICIE-2026-08-27.md` · `REPLAY-OPORTUNIDADE-2026-08-27.md` ·
> `REMEDIATION-2026-08-27.md` · `DEVIATIONS-FOR-PAPER.md` ·
> `PROTOCOL-CALIBRATION-2026-08-27.md`.

---

## Abstract

Memory systems for agents are evaluated on fixed sets of queries and tasks. The field's canonical
survey (218 papers) covers retrieval, memory-quality, response-quality and end-to-end task
metrics; its metric taxonomy does not include a census of distinct memory items delivered under
production traffic. Retrieval is also conditional on a query having been
issued, so an item that no query reaches has an undefined nDCG, not a low one. For 12 weeks we
instrumented the two surfaces through which a memory system in operation delivers content to a
fleet of 6 agents: a proactive 10-item brief and on-demand search.

The brief delivered 583,763 slots, 8.7 times the size of the corpus, enough to
serve each of the 67,187 chunks eight times. It delivered 1,635 distinct live chunks:
2.43% (1,787 counting the 152 that were served and later deleted; see §4.1). The
aggregate capacity therefore did not force this result. It does not follow that the ordering is wrong, only that
the number was not produced by a lack of space. The per-session capacity (10 items)
is not tested here. (The 99.98% expected coverage under uniform random service, against a 100% maximum,
illustrates what the capacity would allow; it is not a recommended policy.) Adding search, 56,288 live chunks (83.78%) have neither a
brief-log record nor a positive search counter. This is a lower bound on non-delivery by the brief and by tracked search; non-delivery across all agent-facing search is not established (§3.1). The capacity figure and the 83.78% sit in different universes on purpose: the slack is the brief's, the 83.78% counts the
union. Of the 10,899 live chunks with a record on either surface, 9,755 have a positive search counter. That counter records that a chunk was a top candidate of some tracked search call, whoever initiated the call (automated callers included) and whether or not the chunk was then returned: it bounds from above what tracked search returned (§3.1).
The brief is the surface that proactively selects content for delivery. Every claim in this paper about
*mechanism* concerns the brief; the 83.78% describes the state and does not assign a cause.

The two channels of the surface freeze, for opposite reasons and neither tied to
capacity. The 8 slots of the main pool are ordered by a score whose terms, with
one exception, do not decay: the access component is monotone in a counter that only
goes up. The 3 chunks present in 100% of the 4,632 briefs of the week rank 1, 3 and 4 by
salience among the 149 served chunks that still exist (last accessed 42, 90 and 30 days before
the close of the window, 2026-08-28; §4.3.2). With the access term zeroed they fall to ranks
44–46: tracked search traffic from months ago (§3.1) is necessary for their observed salience
ranks in the measured counterfactual. The high-pain pin selects them in phase 0, before the quota
pass, but it protects only items that the score has already placed there (`brief.ts:819-821`), and lifting it
removes only one of the three from the main set (§4.3.2). The top-10 takes 47.16% of the slots. The other 2 slots are a *coverage* channel, whose declared
purpose is to serve the never-served, and it freezes for a different reason:
its eligible population is 108 chunks in a corpus of 67,187 (0.16%, carved out by
two path patterns together with the channel's importance floor and 30-day window), and it exhausts
that population entirely on every measured day, with 12.4 slots per candidate on a closed day
(an unpreserved reading on a partial day gave 5.6, and the two are not comparable; see
§4.3.1). On every measured day there was no never-served item left to serve. These coverage
numbers were measured on 2026-08-26 to 08-29, inside a period of defective session ingestion
(§4.3.1), and describe the channel in that regime, not its steady state. The main pool would respond to a score adjustment, and nobody adjusts it. The coverage channel,
designed to compensate for the main pool, has a daily reach bounded by its eligible population (path patterns, the importance/pain floor and age windows), which it exhausted in that regime;
within a brief it responds to score only within `last_served` ties
(17/350 here) and then saturates.

The mechanism of the coverage channel is deducible from the code. It orders by a
lexicographic comparator `(last_served ASC, salience DESC)`: the score is the
subordinate coordinate and decides only within ties of the dominant one. That predicts a ceiling,
not a proportional response, for any additive bonus on the score of that channel.
We tested with an increasing dose by counterfactual replay over 350 of 350 real
brief states, faithful to the serving pipeline. The states are from production, and the intervention
was not served: the mode is *shadow*, so the treated composition is computed and recorded, and
what the agent received during the measured window was always the control (§7). Result: a monotone response in each state, saturation at `w ∈ (4.0, 4.4]`, and a ceiling of
4.86% of briefs (measured on the 2026-08-26 corpus, in the same regime, with an empty never-served stratum). The ceiling is also not a constant of the mechanism:
under the same rule with another draw of designated items it reaches 7.43% (the draw
in force sits at the minimum of the distribution, tied with another), and truncating the timestamp resolution from second to
minute or hour takes it to 36% and 80%, without changing a single line of code. The reach of the
mechanism is fixed by decisions that nobody took as policy. A third axis: excluding the 25 rows
of our own health probes from the serve-state lowers the ceiling to 13/350 (3.71%), with one
sensitive state in common between the two arms (§5.7.2).

What we do not claim: no effect on agent behavior, since no downstream outcome is
instrumented (§4.5). Nor do we claim that the concentration is *wrong*. A policy
that serves 10 items per session should concentrate; uniform serving is used only as a capacity
reference, and its effect on agent utility was not measured;
the finding is that the non-exposure is a result of policy and not a capacity limit,
hence revisable by a design decision. Collection size, which correlates with exposure
(§4.2), may be a proxy for how the type is produced: curation is not ruled out
as a common cause. And we claim nothing about the field: this is one system. The generalization
of the mechanism is deductive and holds for any ranker with lexicographic order and a bonus on the subordinate coordinate that serves a prefix of that order. How many systems have this shape is an open question, and the
executable diagnostic we publish exists so that others can answer it one at a time.

## 1. Introduction

An agent memory system is judged today on fixed inputs: given a set of queries,
how well it ranks what is relevant; given a set of tasks, whether the agent completes them.
The first is the question the retrieval benchmarks answer and the
one engineering optimizes (better embeddings, reranking, query expansion). It
presupposes, without saying so, that what the agent receives is the top of that
ranking.

A question comes before it and goes unasked: what does the agent receive?
It cannot be answered with a set of queries, because it requires the system in
operation. It can be answered, because every delivery passes through a small number of
surfaces that can be instrumented. Here there are two: a proactive 10-item brief at the
start of each session, and on-demand search.

The expected answer would be "it doesn't fit", and the measurement says it fits. In 84.7 days the brief
delivered 583,763 slots against 67,187 chunks, enough capacity to serve every chunk
8.7 times. It served 1,635 distinct live chunks, 2.43% of the corpus (1,787 in
the historical count, which includes 152 deleted afterwards; §4.1 gives the reason both
numbers exist). Under uniform serving the expected coverage would be 99.98%.
Adding search, 83.78% of the corpus is *no-record* (§3.1): it has no record on either surface,
which bounds non-delivery by the brief and tracked search from below. The number of slots does not
impose the non-exposure. Caveat: the part that the ranking explains is the brief's,
and §4.1.1 delimits what can be attributed to each surface. The claim about mechanism
is about the brief, and the aggregate number measures what has no record of arriving, not what
the ranker refused.

**Caveat:** this is not an accusation against the policy. A 10-item surface must
concentrate. Uniform serving is used only as a capacity reference; its effect on agent utility
was not measured. What the
number changes is the nature of the problem. As long as the surface is believed to be
too small, non-exposure is a fact of life; once it is measured to be 8.7× the corpus,
non-exposure becomes a policy choice. There are two choices, one per
channel: the coverage channel exhausted a pool of 108 chunks selected by path patterns, the importance/pain floor and age windows in the measured regime, and the main pool serves 33 distinct chunks on every measurable day but one (34 on 2026-08-23),
the identical set from 2026-08-24 to 2026-09-19, from 5,376 main slots on a 672-brief day because its ranking is a deterministic top-k with no serve-history term
(§4.3.1).

We examined them, and we located the concentration. The 8 slots of the main pool
converge: 3 chunks appear in 100% of briefs (measured over 2026-08-21 to 09-21, §4.3.1). The
high-pain pin (`pain ≥ 0.9`) selects them in phase 0, before the quota pass, and they fill the three shared main-pool slots; it protects
only what the score has already placed in the brief, and it is measured as necessary for
main-set membership for one of the three (§4.3.2). The top-10 takes 47.16% of a week's slots. The remaining 2
slots are a coverage channel, which exists precisely to serve the never-served.
That channel has two distinct constraints: eligibility (path patterns, the importance/pain floor and age windows) bounds daily reach; holding eligibility fixed, an additive salience bonus changes per-brief selection only within `last_served` ties:

1. **Calendar:** the channel cuts by age, and ingestion arrives in batches. Between
   batches no new item enters the coverage pool (on 2026-08-26 to 08-29 its per-agent
   sub-pool held 0 eligible chunks and its global sub-pool 108, §4.3.1), and the channel
   serves the same set for days: over its 10-row agent briefs, the serving log shows the same
   108 coverage-side ids on every day from 2026-08-23 to 2026-08-29
   (`A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json`; the five agent-less health probes of
   2026-08-26 are outside that count, §4.3.1).
   Separately, counting serves across both channels, the batch of 2026-08-21 to 08-22
   contributed 108 distinct chunks a day from 2026-08-22 to 2026-08-29, except 109 on
   2026-08-26, and its minimum served age, reported to two decimal places, rose from 0.92 on
   2026-08-23 to 6.92 on 2026-08-29 in daily increments of 1.00 (0.72 on 2026-08-22;
   `BATCH-CYCLE-2026-08-29.json`). We later
   established that those days fell inside an ingestion defect, not the normal cadence
   of ingestion: session ingestion produced zero chunks from 2026-08-11 until its repair
   on 2026-09-07 (`DEVIATIONS-FOR-PAPER.md` §10.7; §4.3.1), so they describe the channel
   under defective ingestion, not its steady state. The window is not unique: there
   are two sub-pools, the per-agent one with 7 days and the global one with 30 (§4.3.1),
   and the coverage-served portion of that batch belongs to the global sub-pool. Applying the per-agent sub-pool's
   window to a batch of the global sub-pool is an error we made and that a registered
   prediction refuted (F-2);
2. **Algebra:** the channel orders by a lexicographic comparator
   `(last_served ASC, salience DESC)`, in which the score is the subordinate
   coordinate and decides only within ties of the dominant one. Deductively, from seven
   lines of code, this predicts a ceiling for any additive bonus on the score of
   that channel.

The prediction is testable and we tested it, with increasing dose in counterfactual
replay over 350 of 350 real brief states, faithful to the serving pipeline.
Caveat: these are production states, and the intervention was not served
(*shadow* mode in the window this paper measures, §7). The response is monotonic in
each state and saturates at `w ∈ (4.0, 4.4]`, with a ceiling of 4.86% of briefs (measured on the 2026-08-26
corpus, inside the defective-ingestion regime of §4.3.1, with an empty never-served stratum).
The prediction survived the test that could have killed it, as well as an earlier
instrument that confirmed it for the wrong reason (§5.6).

**Caveat on scope.** It is one system. We
did not measure the effect on the agent's behavior; no downstream outcome is
instrumented (§4.5). We do not claim that the field optimizes the wrong coordinate. We
claim that there is a coordinate the benchmarks do not measure, we give the instrument
to measure it, and we leave the question open. Of the two surfaces, the brief
proactively selects content for delivery; the other, search, is instrumented by a counter of candidacy in tracked
calls, which records neither who initiated a call nor what it returned, so its share of
delivered exposure is not established (§3.1, §4.1.1).

- **The gap:** the field's canonical survey (TMLR 2602.06052v4, 218 papers) maps agent
  memory architectures and benchmarks. Its metrics cover retrieval (nDCG/recall over sets of
  queries), memory quality, responses and end-to-end task success. The survey's taxonomy of
  metrics contains no measure of the delivery surface: how many distinct items an agent in
  production sees, and which ones.

  The vocabulary of experimental methodology is also absent. Recomputed over the
  v4 PDF (`measurement/survey-string-count.py`, sha256 `497e9549…b46a6`, 429,387
  characters, 63 end-of-line hyphenations stitched together before counting):

  | term | body | bibliography |
  |---|---|---|
  | `pre-registration` / `preregistration` (and the 6 other spellings) | **0** | **0** |
  | `randomized` / `randomised` | **0** | **0** |
  | `ablation` / `ablations` | **0** | **0** |
  | `interventional` | 1 | 0 |
  | `counterfactual` | 1 | 0 |

  The absence covers the whole family of terms, not one word. A survey of 218
  papers that says `memory` 1,208 times (the positive control's count over the whole extracted
  text, bibliography included; the script emits no body-only count for `memory`) and
  `randomized` never describes a field whose
  instrument is the offline benchmark, not the experiment. The two occurrences that
  exist are singular, and one of them, that of `counterfactual`, appears as a suggested
  future direction.

  **Caveat:** zero is the result that a broken extraction produces for free, so the
  count runs with a positive control (`memory`, `agent`, `benchmark`, `evaluation` above
  floors) and aborts if it fails. The control did fire once, on `ablation=0`. The
  control's floor for `ablation` was what was wrong (a survey catalogs, it does not ablate), and the direct
  check (`memory`=1,208, `benchmark`=126 in the same text) showed the extraction was
  intact, and the term moved from the control to the data.
- **Why the question matters:** ~~If the surface has fixed, small capacity, then
  improving ranking does not improve exposure, and the field optimizes the wrong
  coordinate.~~ That was the hypothesis this work started with, and the measurement
  contradicts it: the surface is 8.7× the corpus. That leaves the
  following: a surface with slack delivers 2.43%, and the channel that
  would exist to compensate for it is governed by an eligibility predicate (two path patterns, an importance floor and an age
  window) that admits 0.16% of the corpus, and by a lexicographic order in which the score decides only within ties of the dominant coordinate. Whether
  other systems have this shape is an open question, not a claim of this paper, and
  the published diagnostic exists so that it can be answered.
- **Contributions:** (i) the measurement of the exposure surface of an agent memory
  system in production, with the result that capacity exceeds the corpus by 8.7×
  and yet 83.78% is no-record (§3.1; caveat: that number sums the two surfaces,
  whereas the capacity cited is only the brief's, and §4.1.1 delimits what each one
  authorizes concluding); (ii) the localization of the bottleneck in the coverage
  channel, with the two mechanisms that freeze it: an eligible population of 108
  chunks (0.16% of the corpus), cut by path patterns, an importance floor and age windows, and
  measured inside a period of
  defective session ingestion (§4.3.1), and a lexicographic order that
  demotes the score to a subordinate coordinate; (iii) a deductive ceiling
  prediction for additive bonuses in that channel, tested with dose-response and
  faithful replay; (iv) the executable diagnostic (`measurement/`), so that the
  measurement is reproducible on another system.

  **Caveat:** the catalog of instrument defects (Appendix E) does not count as a
  contribution. It lists 17 defects that we committed, eight of them altering a
  number that this paper reports. We report them as an obligation, and eight findings
  do not bound the non-findings. They are in the appendix because whoever reproduces
  the measurement will fall into the same ones.

## 2. System under measurement

The system is the persistent memory of a fleet of 6 coding agents in continuous
operation; during the measured week (2026-08-20 → 08-27) it served 4,632 briefs, ~660 per
day (`out/superficie.json`, `briefs_7d`). The corpus is a single SQLite database with lexical
search (FTS5), dense vectors and an entity graph; at the measurement instant (2026-08-28) it held
67,187 chunks. A chunk is a unit of text with a type (`lesson`, `decision`,
`daily`, ...), a date of origin and three scalars that feed the ranking: `importance`,
`pain` and `access_count`. None of this is specific to the system; the paper depends on the
shape of the surface, not on the implementation underneath.

There are exactly two surfaces through which a chunk can reach an agent, and this is
what makes the population measurable:

1. the proactive brief (`/api/brief`), assembled at the start of each session with
   10 items. Every organic brief in the §4.3 window has 10; the only exceptions are our own
   five 5-item health probes (§4.3; `RECON-52-e-sondas-2026-10-04.json`, `c25`). No agent asks
   for it: it receives it;
2. search, invoked by agents or automated callers; its counter records candidacy in tracked
   calls, not initiator identity or final delivery (§3.1).

Every exposure goes through one of the two. *No-record*, the absence of a record in both (§3.1),
is therefore a verifiable property of the records, not an inference; read as non-delivery, it is
a lower bound for the brief and tracked search (§3.1).

The mechanism lives in the composition of the brief. Of the 10 slots, `10 − freshSlots` come from a
main pool ordered by `salience` (an additive sum of importance, recency, pain and
access), and up to `freshSlots` are reserved for a coverage pool, whose declared
function is to serve what has not yet been served. The coverage pool is ordered by
a lexicographic comparator `(last_served ASC, salience DESC)`.

Three parameters of this description are themselves results, and §5 establishes them:

- `freshSlots = 2` in production during the measured window, and by *configuration default
  with no override* (verified on 2026-08-27, §5.3): the number that governs the entire renewal
  of the surface was never chosen;
- it is a ceiling, not a quota: the 2 slots are filled *if* there is an eligible candidate.
  No measured day lacked one: §4.3.1 finds 108 eligible on each of 2026-08-26 to 08-29, and
  coverage filled exactly 2 slots in each of the 40 briefs attributed by channel
  (`CHANNEL-ATTRIBUTION-2026-08-29.json`). The frozen days that §1 cites (2026-08-23 to
  2026-08-29) are days on which the coverage set served in the agent briefs did not change
  (`A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json`), not days without a candidate (§4.3.1);
- and the comparator being lexicographic, rather than a weighted sum, is what gives
  `salience` the role of a subordinate coordinate inside the coverage channel.

**Caveat.** This is one system. The generalization of the mechanism (§5) is deductive, from the
algebra of the comparator, and not empirical; how many systems share this shape is an
open question, which the published diagnostic allows to be answered one system at a time.

**Figure 0** (`out/fig0-arquitetura.svg`): corpus → two channels → 10 slots,
with the comparator annotated on the coverage channel and its 2 slots highlighted.

**Caveat.** It is the only figure in the paper that does not derive from data: an architecture diagram is
a claim about the code, not about a measurement, and the geometry is hand-drawn. But
every number labeled in it comes from `out/superficie.json`, because a typed label silently ages
into falsehood, and in this project one already has. The generator aborts if the
identity `live-exposed + never-exposed = corpus` stops holding; when the generator was written, this check
exposed that the naive sum exceeds the corpus by 152.

## 3. Method

### 3.1 The two surfaces, and what the count is exact about

| surface | instrument | coverage |
|---|---|---|
| brief | `brief_log` | the endpoint's entire lifetime (went live 2026-06-04) and **no pruning** — the only `DELETE FROM brief_log` in the repository is in a test |
| search | `chunks.access_count`, incremented for the top candidates of each tracked search sub-query | since always; the brief **never** writes to that column |

Both instruments cover the period from the start, but they do not record the same event.
`brief_log` records what the brief returned. `access_count` is incremented inside `search()` and
`searchSemantic()` for each sub-search's own top candidates (`search.ts:396`, called at `:466`
and `:579`), and `searchHybrid` runs several such sub-searches (FTS on the original query and on
each expansion variant at `2·limit` each, semantic at `4·limit`) before RRF fusion, truncation
and `dedupe` cut the answer to `limit` (`search.ts:616-676`). A positive counter therefore marks
a chunk that was a top candidate of at least one tracked sub-search: a superset of the chunks
tracked search returned. Tracking is switched off per call by `trackAccess = false`, which the
healthchecks and the semantic canary use (`search.ts:379-380`), so what untracked calls returned
leaves no counter. Tracking is also the default, and the counter is cumulative: the same comment
records that the semantic canary, an automated caller, incremented the counter of its top
candidates on every cycle until it was switched to untracked (`search.ts:377-396`). A positive
counter therefore records search candidacy in some tracked call; it records neither who initiated
that call (an agent or an automated caller) nor whether the chunk was returned. The complement (live chunks with neither a `brief_log` row nor a positive
counter) is an exact count of that predicate and a lower bound on the live chunks returned by
neither the brief nor tracked search. Extending it to every search return would require
showing that no agent-facing call ran untracked, which is not established here.

**Correction.** The union is not, and the earlier version of this sentence said it was (corrected 2026-09-21,
by adversarial review). The two legs have different durabilities, and the table above
shows why: `brief_log` is a durable, unpruned log, so it records exposure of chunks
that have since been deleted; these are the 152 in §4.1. `chunks.access_count` is a column of the
live row: a chunk exposed by search and deleted afterwards takes its counter with it, and the
per-chunk telemetry that could have preserved it had no writer from 2026-05-19 14:47Z until its
writer was restored on 2026-08-27 22:18Z (commit `32f78109`; §6). Exposure by search followed by
deletion within that interval is therefore invisible by construction.

Hence the historical union of 11,051 is not a bound in either direction on delivered exposure:
the search leg loses chunks deleted after exposure (downward) and counts candidates that were
never returned (upward). Only the live complement is exact, as a count of its predicate; read as
non-delivery by the brief and by tracked search, the 56,288 (83.78%) is a lower bound, and
non-delivery across all agent-facing search is not established. The asymmetry changes no number in this
paper, but it changes what can be said about the union, which must not be reported as a count.

We call this quantity *no-record*: a live chunk with neither a `brief_log` row nor a positive
search counter. Read as non-delivery it is a lower bound for the brief and tracked search
together; non-delivery across all agent-facing search is not established, because untracked
calls leave no counter. The rest of the paper uses the term with a pointer here instead of
repeating this scope.

### 3.2 Measurement discipline

Five rules, each of which exists because violating it has already produced a wrong number in this
work (§6):

1. **window closed at both ends**, with the `sha256` of the slice;
2. **derivation in script**, never in prose: prose that asserts a computed result is
   a cache with no invalidation. Every number in the paper comes from `measurement/*.py|mjs` and is
   locked by `--assert-json`, except those flagged where they occur as having no preserved
   artifact (listed in the status block at the top);
3. **reproduce a published anchor before varying anything**;
4. **exact vs. bound** declared per number, with the direction the bound protects;
5. **replay through the real code**, imported, never reimplemented.

### 3.3 Replay fidelity

The interventional evidence depends on a replay of the serving pipeline. It imports the
composition function from the production build as of 2026-08-27/28 and is validated, brief by
brief, against what production recorded. (Code line citations in this paper refer to
`brief.ts`, `brief-diversity.ts`, `salience.ts` and `search.ts` as deposited in `serving-*.ts`;
the salience formula of §4.3.2 is `calculateSalience` in `serving-salience.ts`;
`brief-diversity.ts` is pinned by `sha256 34c9aee5…`.)

| serve-state cut | briefs | control matches | churn matches | production churn | replay churn | invented | lost |
|---|---|---|---|---|---|---|---|
| **by insertion order** | 350 | **350** | **350** | 12 | **12** | **0** | **0** |
| by timestamp (strict) | 350 | — | 346 | 12 | 14 | 3 | 1 |

Checking the composition of the control arm prevents fidelity by
coincidence: without that column, a brief whose control and treated arms were both wrong could
still match on the outcome.

`replay-resumo.py --campo out/c-350-v3.json --campo-estrito out/c-350.json`

## 4. Results

### 4.1 Exposure: 83.78% of the corpus has no exposure record — and 74.75% of what passes the coverage channel's importance floor

| | |
|---|---|
| **live** corpus at 2026-08-28 | **67,187** |
| exposed in the brief (historical) | 1,787 |
| positive search counter (live) | 9,755 |
| historical union | 11,051 |
| — of which, **deleted afterwards** | 152 |
| **live union** = 11,051 − 152 | **10,899** |
| **no record on either** = 67,187 − 10,899 | **56,288 = 83.78%** |
| of these, pass the coverage channel's **importance floor** | **10,008** |

The table closes over one universe: the live corpus. The bridge between the
historical union (11,051) and the live complement is the row for the 152 chunks
served in the brief and deleted afterwards: `11,051 − 152 = 10,899` live exposed chunks,
and `67,187 − 10,899 = 56,288` (↩ F-3.2). The search row is a live count
(`access_count > 0` on the rows that exist, `superficie-de-exposicao.py`), so the historical
union mixes the historical brief with live search and is not a bound on delivered exposure (§3.1).
The complement row is exact as a count of its predicate: 56,288 live chunks (83.78%) are
no-record (§3.1).

The importance-floor row belongs in the headline. A reader may grant the aggregate and
reject the consequence: if most of the 56,288 were low-value noise, there would be
nothing to deliver. That is not the case: of the 13,388 chunks that pass the importance
floor of the coverage channel, 10,008 = 74.75% have no exposure record.

This importance floor belongs to one channel, not to the system. `freshMinImp` and
`freshMinPain` live in `DIVERSITY_DEFAULTS`, next to `freshSlots: 2`, and enter only
through `fetchFreshCandidates`: they are the eligibility criterion of the 2-slot
coverage channel. The 8 slots of the main pool apply no importance filter at all. (F-2)

**Caveat:** the two sides of the ratio also come from different universes, which constrains the
reading: the numerator counts the absence of a record on both surfaces (brief ∪ tracked search),
whereas the denominator is the criterion of one channel. The quantity is legitimate
("the coverage channel would consider this chunk, and neither the brief nor tracked search has a
record of showing it"), but it
is not "the system judged it relevant and refused to serve it".

**Caveat:** the importance floor is also not a constant of the code. The *form* of the predicate is at `brief.ts:642`: `(COALESCE(importance,0) >= ?
OR COALESCE(pain,0) >= ?)`, and the `OR` is the code's, not ours. The *values* 0.7/0.7 are
at `brief-diversity.ts:59-60`, and they are defaults that can be overridden at runtime
by `NOX_BRIEF_DIV_FRESH_MIN_IMP` and `NOX_BRIEF_DIV_FRESH_MIN_PAIN` (`:88-89`). Verified
in the server process on 2026-08-29: neither is set, neither in the process environment
nor in the `.env`, so the defaults apply and the numbers above are the production ones
(↩ F-3.3).

Conditioning on declared relevance lowers the rate by 9 points and the absolute value by
5.6×, but does not dissolve it. The complement is the
larger part: of the 56,288 with no record, 46,280 (82.2%) do not pass even this
importance floor. Anyone who argues that non-exposure is, to a large extent, correct filtering of
irrelevant material has those 82% on their side. What the co-headline establishes is that
10,008 chunks remain (14.9% of the corpus) that pass the coverage channel's
importance floor and are no-record.

Passing the importance floor is not being eligible, and the difference is two orders of
magnitude. The channel applies three joint conditions: the importance floor
(`importance ≥ 0.7 OR pain ≥ 0.7`), a path-pattern cut and an age window. The
importance floor alone selects 13,388; the three together select 108 (§4.3.1), and of these,
zero were never served. The 10,008 are chunks whose importance the channel would recognize if they reached it,
not "chunks the channel wanted to serve and did not", and what keeps them from reaching it is the eligibility predicate (path patterns and age
windows; which of the two binds was not decomposed per chunk), not the ranking (↩ F-2).

**Caveat:** the tempting reading of this number is false. Of the 10,008, 8,928 (89.2%) are `distilled`: session fragments averaging
232 characters (`measurement/composicao-do-piso.py`,
`out/FLOOR-COMPOSITION-2026-08-29.json`). The finding is not "ten thousand invisible
lessons"; it concerns no-record fragments that pass the coverage channel's importance floor
(↩ F-3.4; §3.1).

The rate is unconditional, and that is the objection whose direction is unknown. A
chunk created in week 11 of the window had 7 days of opportunity for exposure; one from
week 1 had 84. Both enter the denominator equally. Had the corpus grown quickly near the
end, a slice of the 56,288 would be "too new to judge" rather than "not delivered".
Stratifying by age (`measurement/exposicao-por-coorte.py`,
`out/EXPOSURE-BY-COHORT-2026-08-29.json`):

| cohort | chunks | never exposed | % |
|---|---:|---:|---:|
| < 1 week | 96 | 90 | 93.75% |
| 1–4 weeks | 1,213 | 753 | 62.08% |
| 4–12 weeks | 4,553 | 3,013 | 66.18% |
| **> 12 weeks** | **61,325** | **52,432** | **85.50%** |

The young cohorts do not drive the headline. The oldest cohort (91.3% of the corpus) is more
unexposed than the aggregate (85.50% against 83.78%); only the < 1 week cohort (n = 96) is
higher, and the two young cohorts together are 1.95% of the corpus, too small to move the
aggregate in either direction. This is a descriptive comparison, not a censoring correction:
the cohorts differ in composition, age is measured from `COALESCE(source_date, created_at)`,
which can precede ingestion, and additional follow-up could only move a young chunk from never
exposed to exposed. We report the aggregate.

**Caveat:** a third leg of the same objection is uncountable by construction, and is declared:
a chunk created and deleted within the window without ever having been exposed appears in
no population; the complement is over the *live* corpus. That the inverse exists (the 152
served and later deleted) proves there is churn within the window. The direction of this
bias is unknown and cannot be measured with the data we have.

#### 4.1.1 Aggregate capacity does not force the outcome — and what this does not establish

**Caveat:** one objection is that 583,763 accumulated slots
are not fungible. The surface delivers 10 items per session, and if a session needed
more than 10 relevant items, capacity would be binding *today*, however much slack there
was in the aggregate. The objection is correct and restricts the claim: we do not claim
that 10 slots per session are many.

The claim is about rotation, not session size. The question measured is how many
*distinct* items the surface has ever shown, and for that question the slots are
fungible over time: nothing obliges today's session to show the same 10 items as
yesterday's, and showing ten different items per session would never violate the limit of
ten.

And the evidence that aggregate capacity does not bind is one line of arithmetic, not a
test: 583,763 slots against 67,187 chunks. There was room to show everything, eight
times over. That is what can be asserted, and it suffices for what the previous paragraph
supports.

**Note:** this section previously carried a table of "opposing predictions" (ratio `slots/distinct` ≈ 1 versus ≫ 1) presented as the test that separated the two hypotheses. It was withdrawn; the argument is in Appendix F-1.

**Note:** this is why the uniform counterfactual (99.98%, the expected coverage under independent
uniform draws with replacement; a rotation over the same slots would reach 100%) appears in
this paper as a reference point and not as a recommended policy. Its effect on agent utility was
not measured; the number exists to say what capacity *would allow*, not what
should be done.

The two surfaces are not the same kind of thing. The brief proactively selects content for
delivery; the search counter records candidacy in tracked calls without identifying their
initiators. Of the 10,899 live chunks with an exposure record, 9,755 have a positive search
counter, an upper bound on what tracked search returned (§3.1). The brief (1,635 live; 1,787 counting the 152 later deleted) records what was selected for delivery. This
does not invalidate the complement ("never exposed" remains no-record, §3.1), but it restricts what can be said about cause: the 83.78% figure measures what has no
record of arriving, not what the ranker refused. The claims about mechanism (§5) hold for the
brief.

**Caveat:** the two surfaces also intersect, which the decomposition "9,755 came from search,
1,787 from the brief" hides: `1,787 + 9,755 = 11,542` against a historical union of
11,051 ⇒ 491 chunks are in both. The two numbers do not partition the 10,899, and
presenting them side by side as if they did is the same mixing of universes that erratum
F-3.2 corrected elsewhere. Added on 2026-09-21 following adversarial review.

**Caveat:** the two rows count different populations, and the sum gives it away: 11,051 +
56,288 = 67,339, 152 more than the corpus. The historical union combines historical
brief-log membership with positive search counters on live chunks; it includes 152 chunks served
in the brief and deleted afterwards and does not count delivered exposure. The complement counts
the no-record live chunks at 2026-08-28 09:52Z (`out/superficie.json`; §3.1). Discounting
them, 10,899 + 56,288 = 67,187 exactly. The percentage cited is over the live corpus, over which
this record predicate is measured.

### 4.2 Secondary result: the large types cluster at 10.7–27.0% exposure, and size cannot be separated from curation

**Caveat.** "Exposed" here is the UNION of the two surfaces (`brief_log` ∪ `access_count > 0`),
the same definition as in §4.1. We say this because most of the records are search-counter
records, which mark candidacy in a tracked search call, not delivery (§3.1). The gradient below describes that search candidacy added to what the brief
delivered. For live chunks the two contributions could be tabulated separately by type
(brief-log membership and `access_count > 0` are both recorded per chunk, with an
intersection); that split is not reported here.

| type | exposed/total | % |
|---|---|---|
| `lesson` | 53/53 | **100.0** |
| `test` | 14/14 | 100.0 |
| `project` | 36/43 | 83.7 |
| `feedback` | 12/17 | 70.6 |
| `digest` | 15/25 | 60.0 |
| `person` | 8/14 | 57.1 |
| `decision` | 4/11 | 36.4 |
| `shared` | 13/40 | 32.5 |
| `graph_node` | 282/1,046 | 27.0 |
| `daily` | 798/3,231 | 24.7 |
| `team` | 3,327/15,308 | 21.7 |
| `distilled` | 2,822/14,456 | 19.5 |
| `other` | 3,515/32,920 | **10.7** |

**Caveat.** The table above uses a filter that is in the code and was not in the text, and it is still in the code.
`superficie-de-exposicao.py` selects types with `HAVING total >= 10`, which excludes
`pending` (n=6) and `procedure` (n=3). Both have 0% exposure and both are small;
that is, the filter removes exactly the evidence that contradicts "small ⇒ highly
exposed". A filter that can only help must be declared, and its effect measured
(`measurement/robustez-tamanho-exposicao.py`).

Two explanations compete: curation (more curated types are more exposed) and
size (small collections fit on the surface). Nothing here separates them (↩ F-3.5).
The tests below separate *filter artifact* from *signal*; the partials further on control for
age, mean importance and text length, and none of them is curation. No variable in the
corpus measures curation, so "size" and "curation" remain
confounded by construction. What does change with the count is the strength:

| analysis | 13 types (with filter) | 15 types (without filter) |
|---|---|---|
| Pearson `r` (log₁₀ n × % exposed) | **−0.728** | **−0.334** |
| Spearman ρ | −0.687 | **−0.098** |
| **binomial β** (logit, weighted by n) | **−0.982** | **−0.961** |

The correlation of percentages is fragile to the filter; the binomial model is not. The reason
is that correlating percentages gives a type of 3 chunks the same weight as one with 32,920.
The binomial model uses all the types and weights each by the information it carries: the
two excluded types move the coefficient by 2%, not by half. The binomial is what this
paper reports, and the correlation stays as a description of the figure, not as a test.

**β = −0.961.** Correction. But "×0.38 per decade of size" is a parameterization the
axis does not support, and the previous version reported it that way. The 15 types are not
distributed along size: they form two clouds with a void between them
(`measurement/lacuna-no-eixo-de-tamanho.py`, `out/SIZE-AXIS-GAP-2026-08-29.json`).

| | |
|---|---|
| types with n < 100 | **10** (from 3 to 53) |
| types with 100 ≤ n < 1,000 | **0** |
| types with n ≥ 1,000 | **5** (from 1,046 to 32,920) |
| largest gap on the log₁₀(n) axis | **1.295 decades**, between `lesson` (53) and `graph_node` (1,046) |
| — as a fraction of the axis range | **32.1%, without a single point** |

A slope fitted over two clouds is, arithmetically, the difference between them
divided by the distance between them. It describes the data, but it does not
license a point reading inside the void: a prediction such as "a type of 300 chunks would have ×0.38 the chance
of one of 30" has no observation at all in this corpus. With
n = 15 independent units and a third of the axis empty, the defensible form of the finding is
the contrast between the clouds, not the rate: the 5 large types occupy 10.7–27.0% of
exposure; of the 10 small ones, 7 are above 32.5%, one is exactly at 32.5%, and 2 are at zero.

And the model's standard error is unusable. It gives `± 0.027` (z = −35) because it assumes
67,187 independent observations; the predictor is constant within the type, so the
unit of independence is the type and the effective `n` is 15. By the jackknife over types:
SE = 0.471, z = −2.0. Leaving one type out moves β within
`[−1.12, −0.51]`. The finding survives, but narrowly. Saying the opposite
would be selling as robust a result that a single collection can nearly halve.

**Corollary.** The same argument imposes this: recomputing the correlation "at the
chunk level" does not answer the ecological objection. Since `log₁₀(size)` does not vary within the
type, the point-biserial `r` over 67,187 chunks (−0.150) merely reweights the same
15 points. Disaggregating a predictor that is a property of the group does not create information.

What survives intact, and is the strongest form of the finding: *no small type falls
within the range of the large ones.* The 5 types with n ≥ 1,000 occupy 10.7–27.0%, and none
of the 10 types with n < 100 is in that interval; they are above it (32.5% to 100%) or
at zero. Correction. The phrase "no overlap" in the previous version was stronger than that and
false with the 15 types: including `pending` and `procedure`, the range of the small ones
becomes 0–100%, which contains that of the large ones entirely. The two cases at zero are explainable
(`pending` was 6 days old at the measurement instant, 2026-08-28; `procedure` has 3 chunks), and the explanation is *post hoc*;
it is here as a limit, not as a defense.

And the age confounder does not explain the finding. Large types are, in fact, older
(`r(log n, age) = +0.41`), but the partial controlling for age stays at −0.709, almost
unchanged. Restricting to the 9 types with mean age ≥ 70 days, where age is
approximately constant, the relationship strengthens: `r = −0.843`, ρ = −0.883.

These partials are over the 13 filtered types, and therefore inherit the fragility that
the previous paragraph just established. "Almost unchanged" is relative to −0.728,
which is the Pearson with the filter; the Pearson for the 15 is −0.334, and against it −0.709 would
not be "almost unchanged": it would be double in magnitude. The "9 types with age ≥ 70 days" are also 9
of the 13 (↩ F-3.6). What they establish, then, is limited: within the filtered subset, age does not explain the
gradient. They are not evidence about the 15. The same
holds for mean importance (partial −0.685) and for text length (−0.732).

And the confounder that remains after age is what prevents the strong conclusion. §4.3.1
shows that ingestion arrives in batches of files: large types are those fed by an automatic
pipeline; small types are written by hand. This is curation disguised as size, a common cause of both, which no correlation
between them can separate. The paper does not rule out the curation hypothesis; what it
shows is that size predicts better than the *relevance the system itself
assigns*, which is a weaker claim and is the one the data support.

Two properties of the corpus composition limit how surprising the separation is.
There is no type with `n` between 53 and 1,046. With a void in the middle of the axis, some
separation between "large" and "small" is guaranteed by the composition, not discovered. And
`other` alone is 49% of the corpus, so the aggregate of 83.78% is, in large part, a single type.

`lesson` is at 100% and has 53 rows. The relevance assigned by the system predicts exposure
less well than the size of the collection does, with the caveat above that size
may be a proxy for how the type is produced.

**Figure 1.** `out/fig1-capacidade.svg`: scatter of `log₁₀(size)` ×
`% exposed`, one point for each of the 15 types, with the two bands (n ≥ 1,000 ·
n < 100) shaded and the stretch of the axis without observations marked. Generated by
`fig1-capacidade.py --dados out/SIZE-EXPOSURE-15-2026-08-29.json`, a locked artifact.

**Correction.** Three design decisions, and all three are retractions of earlier versions of the
figure. (i) It was generated over the artifact with `HAVING total >= 10` and showed 13
types, and the two omitted, `pending` and `procedure`, are exactly those that sit at 0% and
break the reading of a clean separation. A figure that visually asserts what the text
refutes is worse than no figure, because the reader believes what they see before reading the
caveat; a caveat placed below the figure does not fix this, for the same reason. The
guard in `fig1-capacidade.py` now refuses the filtered artifact. (ii) The regression
line was removed: it crossed 1.295 decades without a single point, which asserts
graphically the continuity that §4.2 withdraws from the text. In its place, the stretch is
shaded and labeled *no observation*. (iii) With the 15 types the Pearson of the figure is
−0.334, not −0.728. The figure shows the fragile number, the one computed without the filter, and the
binomial model stays in the text.

**What the figure shows, then:** the 5 large types cluster at 10.7–27.0%,
while the 10 small ones spread across 0–100%. Rather than a separation, this is much
greater variance in the small ones, with the range of the small ones containing that of the large ones.

### 4.3 The brief surface is a carousel of 201 items

Closed window `[2026-08-20, 2026-08-27)`:

| | |
|---|---|
| slots served | **46,295** in **4,632** briefs |
| — deficit against 10 per brief | **25** = `4,632 × 10 − 46,295` |
| distinct chunks | **201**, of which 5 were served only by our five health probes; **196** organic |
| present in **100%** of briefs | **3** |
| top-10 | **47.16%** of slots · top-20 **61.46%** |
| without the 5 probes | **46,270** slots in **4,627** briefs · deficit **0** · top-10 47.16% · top-20 61.46% |

**Figure 2** (`out/fig2-concentracao.svg`): Lorenz curve of the carousel
(rank × cumulative share of slots), with marks on the 3 constant items (which alone take
30.0% of the slots) and on the top-10 cut. Generated by `fig2-concentracao.py --dados
out/superficie.json`, and the script aborts if the curve does not sum to `slots_7d`.

**Caveat:** the 25 missing slots, and what they suggest (added 2026-09-21, following
adversarial review). An earlier version of §2 said the brief comes *"always with 10 items"*, and `4,632 × 10 = 46,320`
against the 46,295 measured. §5.7.2 establishes that the health probes are briefs of 5
lines and that there are five of them, and `5 × 5 = 25`, exactly the deficit. The arithmetic
suggests that the 4,632 include the five probes, that is, that the denominator
of this section carries the same contamination that §5.7.2 turns into a headline elsewhere.

Confirmed by identity, not only by arithmetic (2026-10-04; `measurement/sprint-recon-52-e-sondas.py`,
`RECON-52-e-sondas-2026-10-04.json`). The window holds exactly 5 briefs that do not have 10 rows.
Each has 5 rows; the other 4,627 all have 10, and no row lacks a `brief_id`. Their `brief_id`s
are, as a set, the five that `out/ancora-sondas.json` lists as `sondas_excluidas`. All are
`scope=global` with no agent, issued on 2026-08-26 at 19:58:17–18 and 20:28:55–56 UTC. So the
4,632 briefs do include our five health probes, and `25 = 5 × 5` is an identity. The probes
are also not neutral to the distinct count. Each carries the three constants plus two other
chunks, and five of those chunks (307967–307970 from `memory/decisions.md`, 308443 from
`memory/projects.md`) were served exactly once ever, inside a probe. Without the probes the
window has 46,270 slots in 4,627 briefs and 196 distinct chunks. Top-10 and top-20 shares
are unchanged (47.16%, 61.46%), and the same 3 chunks appear in 100% of briefs. The earlier
phrase *"always with 10 items"* was false for exactly these five probe briefs; §2 now states
the exception.

The 201 are what was measured, not the ceiling. There was room for 46,295, one per slot. Treating
the measured value as the ceiling would turn a result into a pigeonhole and teach the reader to find the curve
inevitable. The diagonal is a reference for reading; the finding is that the curve is this far from
it with a 230× margin by which it need not have been. (F-2)

#### 4.3.1 The carousel does not rotate because there is nowhere for it to rotate

The daily diversity of the coverage channel has steps. The explanation we tried
first, that "each ingestion batch feeds the channel for seven days and expires", was
refuted by a dated prediction that we registered before the day (§6 and
`PREDICTION-2026-08-29.md`). The refutation exposed the structure described below.

The channel sees 0.16% of the corpus. It is the union of two sub-pools, each with its own
path patterns and its own window (`brief.ts:135,642,645`; `brief-diversity.ts:59-62`):

| sub-pool | patterns | window | eligible |
|---|---|---:|---:|
| per agent | `sessions/<agent>/%` | 7 d | **0** |
| global | `memory/entities/%`, `memory/lessons.md` | 30 d | **108** |

The zero in the per-agent sub-pool does not come from a lack of material. On 2026-08-30, 10,899 `sessions/%` chunks pass the importance
floor, and none falls within the 7-day window, because the newest of them is
20.5 days old. Caveat: this 10,899 has no relation to the 10,899 of the live union of exposed items
in §4.1: they are distinct sets whose sizes coincide at this instant. We checked:
the intersection between them is 1,971, and the live union measured on the same day is 10,926. The
coincidence belongs to the calendar, not to the quantity, and disappears the next day. (The
20.5 days, the 1,971 and the 10,926 have no preserved artifact.)

The system did have relevant session memory; none of it was younger
than the sub-pool's 7-day window. We later established why
(`DEVIATIONS-FOR-PAPER.md` §10.5, §10.7). A host migration had moved both the address and the
schema of the agents' session transcripts, and session ingestion produced zero chunks from
2026-08-11 until it was repaired on 2026-09-07, while its cron reported `ok`. Separately, all
ingestion was frozen from 2026-08-24 01:06Z to 2026-09-07 14:06Z by a watcher invoking a
missing binary. Half of the coverage channel was therefore inert because of an ingestion
defect, not by design and not because of the normal cadence of ingestion. After the repair,
the per-agent sub-pool held 285 eligible chunks (2026-09-09). The served coverage set did not
follow. From the serving log alone (`_sprint-2026-10-04/A-rc2/coverage-set-from-log.py`,
`A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json`), over the 10-row agent briefs (the script keeps
only those; the five 5-row probes of 2026-08-26, §4.3, are outside this count and served 5
further chunks that day), the ids served outside the main pool are the
same 108 ids (spanning 308214 to 308496, not contiguous) on every day of the log from 2026-08-23 to 2026-09-19 (2026-09-02 has
no rows), the repair of 2026-09-07 included. The set first changes on 2026-09-20, when 109163 and
227328 appear; both are main-pool candidates in the leave-one-out lists
(`A-filters-disaggregation/out-ord0826.json`), and the log-only method (all ten slots minus the
month's 37-id main union) cannot tell a main-pool change from a coverage one. Why the post-repair 285 never reached the
served set is not established here, and neither is how it relates to the pool of 55 that a copy
frozen on 2026-09-08 gives (below). Every coverage-channel number in
this section was measured inside that broken regime, including the 108-chunk pool and its daily
exhaustion on 2026-08-26 to 2026-08-29; so was the frozen set that §1 cites, the same 108
coverage-side ids in the agent briefs on every day from 2026-08-23 to 2026-08-29 (the log-only
method above).
Separately, counting serves across both channels (`ciclo-do-lote.py` selects the batch by
creation date and attributes no serve to a channel), the batch of 2026-08-21 to 08-22
contributed 108 distinct chunks a day from 2026-08-22 to 2026-08-29, except 109 on 2026-08-26,
and its minimum served age, reported to two decimal places, rose from 0.92 on 2026-08-23 to
6.92 on 2026-08-29 in daily increments of 1.00 (`BATCH-CYCLE-2026-08-29.json`).
They describe the channel under defective ingestion, not its steady state.

**Caveat.** This makes the composition of the channel unstable in a way that the table above hides: a
burst of new sessions would repopulate the per-agent sub-pool and change the eligible pool (and
with it the tie structure that sets the ceiling) without a single line of code changing. The obligation to say
this had been registered in `DEVIATIONS-FOR-PAPER.md` since 2026-08-27 and had not been
fulfilled; the 2026-08-30 retrospective found it by cross-checking the registered commitments against
what the manuscript carries.

Both are subject to the importance floor `importance ≥ 0.7 OR pain ≥ 0.7`. Measured over four closed days
(`measurement/pool-elegivel.py`, `POOL-ELEGIVEL-2026-08-28.json`; the four days are in
`POOL-ELEGIVEL-2026-08-26-to-29.json`, produced by `measurement/sprint-pool-elegivel-multidia.py`):

**Caveat:** until 2026-10-04 the artifact covered ONE day while the claim covered four. Adversarial
review on 2026-09-21 found that `POOL-ELEGIVEL-2026-08-28.json` holds only 2026-08-28
(`"dia": "2026-08-28"`, `"dia_parcial": false`). The other three days had been measured by the
same route and not preserved, which is the gap that the backing-artifact discipline of
§6.1 exists to prevent: an artifact cited to support more than it contains. The review
suspected in-place rewriting; there was none, because the file on disk is identical to the
versioned one. The gap was closed by re-measuring from a preserved trial database
(`corpus-SERVING-REAL-e20260903-recuperado.db`, sha256-verified copy) using the same predicate.
A positive control came first: re-running 2026-08-28 reproduces all 12 fields of the original
artifact. 2026-08-26, 2026-08-27 and 2026-08-29 then give the same pool of 108, 0 never served
and 108 served (`POOL-ELEGIVEL-2026-08-26-to-29.json`). The set of pool ids is identical (same
hash) in copies frozen on 2026-08-26, 2026-09-03 and 2026-09-07. A copy frozen on 2026-09-08,
after the corpus was re-ingested, fails the control (pool 55) and is not used. Limit:
importance and pain are read as stored in those copies, so they bracket the four days rather
than observe each instant.

| | |
|---|---:|
| live corpus | 67,187 |
| **eligible pool of the channel** | **108** — 0.161% |
| of those, never served | **0** |
| served on the day | **108 — 100% of the pool**, on 2026-08-26, 2026-08-27, 2026-08-28 and 2026-08-29 |
| coverage slots per eligible candidate | **12.4×** (closed day; 12.5× on 2026-08-26, which had 5 extra five-row briefs) |

**Caveat.** The last number is for a closed day. The original 2026-08-29 reading was taken with the
day still in progress and gave 5.6× only because fewer briefs had occurred; that partial
reading was not preserved. Measured on the closed day, 2026-08-29 gives 12.4× (672 briefs).
The script flags `dia_parcial` so that partial and closed days are not compared.

The pool is exhausted on every day measured. There are twelve times more slots than candidates, so the
ordering `last_served ASC` orders but does not exclude anyone: every eligible item appears,
every day. There is no carousel turning and no batch expiring; the pool is too small for
rotation to be a question.

This changes where the scarcity lives. On the day, coverage of the eligible pool is 100%. In one
brief, there are 2 slots for 108 candidates. What the ordering decides, and what the intervention
of §5 moves, is *which two appear in each brief*, not *how much of the corpus is reached*.
The corpus is not reached because 99.84% of it never enters the draw.

**Why the prediction failed.** There are two coverage sub-pools,
with different patterns and windows:

| sub-pool | patterns | window |
|---|---|---|
| per agent | `sessions/<agent>/%` | `freshMaxAgeDays = 7` |
| global | `memory/entities/%`, `memory/lessons.md` | `freshGlobalMaxAgeDays = 30` |

The batch of 2026-08-09 to 2026-08-10, on which we made the retrodiction, was entirely
`sessions/boris/…`, the per-agent sub-pool, so it stopped cleanly at 7.0 days, with the maximum age served never reaching 7.00 in eight days. The batch of 2026-08-21 to 2026-08-22, on which we
made the prediction, is `entities/%` + `lessons.md`, the global sub-pool, with a 30-day
window. We applied the window of one channel to a batch of the other. The retrodiction was valid; the
extrapolation was not. It is the same defect of "verifying an invariant over the
wrong set" that §6 catalogs, committed this time on the mechanism that the paper itself
describes.

Attribution by channel was measured, not inferred. The decisive objection to everything above is that
`brief_log` does not record the origin of each serve, and an eligibility rule excludes
but does not attribute: the same 108 serves would be equally compatible with "coverage stopped
at 7 days and the main pool served everything". The test that separates the two hypotheses
needs no new column. It suffices to run the same state twice through the real code, once with
`freshSlots = 2` (production) and once with `freshSlots = 0`, and take the difference. What
disappears when the channel is switched off is, by construction, what the channel delivered.

In 40 briefs of 2026-08-29 (`CHANNEL-ATTRIBUTION-2026-08-29.json`): 80 slots attributed to
coverage (exactly 2 per brief, across all 40), 62 distinct chunks, and all 62 belong
to the 2026-08-21 to 2026-08-22 batch. Coverage *was* serving the batch at 7.4 days; the
alternative hypothesis is ruled out by measurement.

**Caveat:** without this test, the argument was asymmetric. `brief_log`
does not record through which channel each line was served; there is no origin column. Counting
serves of a batch measures the union of the main pool with the coverage pool, and the main
pool has no age filter at all. That is why the cut guard flagged
"age 7.42 served" as a violation of the 7-day window: part of those serves was never
subject to any window. Using this limitation to void the old guard without
applying it to the new explanation would be choosing the ruler by the result, and the new explanation
suffered from the same union bias until the differential test above existed.

This is a separate result, and it concerns the channel's daily reach, not its per-brief
selection. Eligibility combines path patterns, the importance/pain floor and age windows. In the
measured regime, the channel exhausted that eligible population on every measured day, and the
corpus grew outside the configured path patterns. Holding eligibility fixed, an additive salience
bonus changes per-brief selection only within `last_served` ties; the tested intervention
saturated at 17/350 replay states (§5.3, §5.4).

**The main pool, filter by filter.** The main pool reaches its 8 slots through seven serial
stages (`brief.ts:202-215, 371-397, 420-468, 819-821`): (F1) routing, where the agent sub-pool
sees only `sessions/<agent>/%` with quota 5 and the `scope=global` sub-pool sees the whole
corpus; (F2) a `since` window, inactive because production sends none; (F3) a SQL proxy
pre-rank with `LIMIT 500` per sub-pool; (F4) the exact `calculateSalience` re-rank; (F5) dedup
by id, exact title/one-liner and near-duplicate containment ≥ 0.6; (F6) quotas capped at
`mainTarget = n − freshSlots = 8`; and (F7) the high-pain floor, which picks the items of
the no-fresh brief with `pain ≥ 0.9`. F7 is listed last but runs first: it is phase 0 of
`pickDedup`, and the pinned items it places count toward `mainTarget` before the F6 quota pass
(phase 1) and the backfill by global score (`brief.ts:438-480`). We reimplemented them on the frozen corpus of these days
(`p2-ord-ro-2026-08-26.db`, 67,187 chunks; `measurement/sprint-desagrega-filtros-pool-principal.py`,
`A-filters-disaggregation/out-ord0826.json`). The reconstruction reproduces the served main
slots in 100% of the briefs of each day with rows from 2026-08-24 to 2026-09-07 (672 per day;
441 on 2026-09-03; 2026-09-02 has none), counting a brief as reproduced when its 8
reconstructed ids lie inside the 10 served and leave the 2 coverage slots. The stricter test,
the 8 ids equal to the served ids minus the logged `fresh_added`, passes in 94.3–97.9% of the
briefs of each of those days except 2026-09-03 and 2026-09-07, where `fresh_added` is null;
on those non-null days, every brief that fails the stricter test has treated `fresh_added`
differing from the control's coverage picks, so the subtraction leaves 9 or 10 ids. On
2026-09-03 and 2026-09-07, null `fresh_added` leaves all 10 served ids (`out-ord0826.json`,
`fidelity`). 2026-08-21 to 08-23 are left out because the frozen copy does not hold the served
state of one `boris` slot on those days: it carries an access to chunk 298048 at
2026-08-22T19:09Z, so the reconstruction ranks 298048 above 285042, while production served
285042 in that slot on 08-21, 08-22 and part of 08-23 (`A-filters-disaggregation/diag-out.txt`,
diagnostic of the 2026-08-22 epoch; why production kept 285042 after the access is not
established). Under the first criterion those days reproduce 85.8%, 85.7% and 98.0%; under the
stricter one, 85.8%, 85.7% and 84.3%. Counting exclusions is the wrong instrument here: F3 alone removes 95.7% of the
corpus from candidacy and binds nothing. The question is answered by lifting one filter at
a time and recomputing every brief:

| lifted | briefs whose main set changes (of a 672-brief day) | distinct main chunks per day |
|---|---:|---:|
| none (as served) | — | **33** |
| F1 routing | 672 | **8** |
| F2 `since` | — (inactive) | 33 |
| F3 `LIMIT 500` | **0** | 33 |
| F4 exact re-rank | 672 | 33 |
| F5 dedup | 192 | 33 |
| F6 quota split | 672 | **8** |
| F7 high-pain floor | 672 | 33 |

The counts are per day, and every 672-brief day from 2026-08-24 to 2026-09-07 gives these
values; on 2026-09-03 (441 briefs) the rows that read 672 read 441 and F5 reads 126. The distinct
counts are the same on every day (`out-ord0826.json`, `leave_one_out`).

No filter, lifted, widens the surface; the two that change its breadth narrow it, because
routing by agent is the main pool's only source of variety. The breadth is exactly
`3 + 6 agents × 5`: the 3 shared slots are what `mainTarget` leaves after the agent quota
(8 − 5), and in every brief the three pinned chunks fill them (112241, 116107 and 116467,
`pain = 1.0`, placed in phase 0 before the quota pass); with F7 lifted the same 3 slots go to
the `scope=global` sub-pool's top three after dedup, where 227328 replaces 116107 (§4.3.2),
and each agent gets the same 5 in every brief. A day
has 5,376 main slots and they serve 33 distinct chunks, which is 0.61% of the slot
capacity and 163 serves per chunk. From the serving log alone, without the database
(`observed-main-from-log.json`), there are 33 distinct main chunks on every measurable day from
2026-08-21 to 2026-09-21 except 2026-08-23, which shows 34, and the set is identical on every
measurable day from 2026-08-24 to 2026-09-19. On 2026-08-21 and 2026-08-22 one `boris` slot
carries 285042 instead of 298048, 2026-08-23 carries both, and on 2026-09-21 three ids
(309422, 309529, 311215) replace three (273772, 285044, 298048). The month's union is 37
(33 + 285042 + the three new ids). A
rotation over the same slots could serve 5,376 distinct chunks a day, or 8.0% of the corpus.
So the main pool is not capacity-bound at the day, the unit at which §4.1 measures
exposure. It is bound by its ranking: a deterministic top-k with no serve-history term, removed
on purpose on 2026-06-26 (`brief.ts:786-792`). Both channels are therefore governed by policy
rather than by slots, but by different policies. The coverage channel exhausts an
eligibility predicate of 108 chunks; the main pool returns the same arg-max for the same route,
with no eligibility predicate: all 67,187 chunks enter the SQL pre-rank, and 99.95% of them are
never reached. Daily, in the agent briefs, the two channels are disjoint and add up to the
whole: 33 + 108 = 141 distinct chunks, every measurable day from 2026-08-24 to 2026-09-19
(2026-09-02 has no rows; on 2026-08-26 `brief_log` as a whole holds 146 distinct chunks, the 5
probe-only chunks of §4.3 included: `RECON-52-e-sondas-2026-10-04.json`, `por_dia_utc`).

**Caveat:** a counting trap, recorded because it nearly caught us. Counting exposure with
`JOIN chunks` makes 2026-08-21 show 33 distinct chunks where `brief_log` says 85. The other
52 no longer exist. The same 52 vanish from 2026-08-20 (87 → 35) and 2026-08-22 (193 → 141).
They are one ingestion of `memory/lessons.md` (ids 308114–308165), replaced by a re-ingest on
2026-08-22 02:01:58 UTC, and the serving path kept handing them out for about 17 h afterwards
(966 of their 2,600 slots; `RECON-52-e-sondas-2026-10-04.json`). This trap was first recorded
here as 2026-08-20 with 85 → 33; measured per day (UTC and BRT alike), that pair belongs to
2026-08-21. Exposure counts come from `brief_log`; only what needs chunk metadata uses the
JOIN, and it declares the loss.

#### 4.3.2 The other channel also freezes, for the opposite reason

If the coverage channel fails because of the calendar and because of algebra, the thesis still
needs to explain why the other 8 slots concentrate. There the score is the dominant coordinate
and an additive bonus has no ceiling, so the concentration cannot be explained
by a bounded response to the score. It has another cause, and it is read directly off the formula.

`salience = 0.55·importance + 0.15·recency + 0.10·pain + 0.20·access`

Of the four terms, three do not decay. Importance and pain are static. The access term is
`0.20 · log1p(access_count)/log(1000)` over a monotonic counter: it
rises and never falls. Recency is `2^(−age/retention)`, with age measured from `last_accessed_at` when it
exists and from `source_date` otherwise, and it has no floor (`serving-salience.ts:78-98`).
A NULL `retention_days` is the code's never-decay marker (recency = 1.0, `:58-71`); 39,130 of
the 67,187 live chunks carry it, among them 35 of the 149 served in the window and all three
chunks below. For those, no term decays: the score of an old and once-popular chunk is
non-decreasing and stays at its ceiling. For chunks with a positive retention, recency does
decay, and a search hit resets it through `last_accessed_at`, so access enters the score twice
(`out/SALIENCE-COUNTERFACTUAL-PROD-2026-10-05.json`, `retention_days_null`).

The three chunks present in 100% of the 4,632 briefs of the week are exactly that:

| chunk | type | importance | pain | `access_count` | last access |
|---|---|---|---|---|---|
| 112241 | `team` | 0.80 | **1.00** | 414 | 2026-05-30 |
| 116107 | `team` | 0.80 | **1.00** | 363 | 2026-07-29 |
| 116467 | `team` | 0.80 | **1.00** | 911 | 2026-07-17 |

(The dates are read from a copy of the 2026-09-07 trial epoch,
`out/SALIENCE-COUNTERFACTUAL-PROD-2026-10-05.json`, `the_three`. `last_accessed_at` only moves
forward, so a value earlier than 2026-08-28 in that copy is also its value on 2026-08-28.)

They had last been accessed 90, 30 and 42 days before 2026-08-28, and they won every
brief of that week. The positions they occupy are determined by tracked search traffic from months
ago (§3.1), and "determined" here is a measured counterfactual, not a reading of the formula.

**Caveat:** the scope of the word, corrected on 2026-08-30. A read-through observed that "the top of the
brief is determined" generalizes from the three chunks that the counterfactual moves to the entire top,
and that the support is a recompute over 149 of the 201 chunks of the window. What
is measured is the position of those three: zeroing the access component takes them from 1/3/4 to
44–46 among 149 served (23–47 across instants and access-timing assumptions). It is a claim about them, not about the ten positions.

| chunk | `importance` | `pain` | accesses | position | position with access **zeroed** |
|---|---:|---:|---:|---:|---:|
| 116467 | 0.80 | 1.00 | 911 | **1** | **44–46** (tie at 0.69) |
| 112241 | 0.80 | 1.00 | 414 | **3** | **44–46** (tie at 0.69) |
| 116107 | 0.80 | 1.00 | 363 | **4** | **44–46** (tie at 0.69) |

Recomputing the salience of the 149 chunks served in the window with the access component at
zero, through the production function `calculateSalience` imported from `serving-salience.ts`
(`measurement/sprint-contrafactual-salience-producao.mjs`,
`out/SALIENCE-COUNTERFACTUAL-PROD-2026-10-05.json`), the three leave the top-10: they fall from
positions 1, 3 and 4 to a three-way tie at 0.69, at positions 44–46 of 149 on 2026-08-29
(45–47 at noon of each day of the window). The epoch keeps only the latest
`last_accessed_at`, so competitors accessed after the pinned instant get full recency; dropping
those accesses gives 23–25. Across the tested instants and access-timing assumptions, positions
span 23–47 in this fixed retrospective population, with every other attribute as in the copy:
a sensitivity range, not a reconstructed historical serving position. On the path the brief
uses (the `scope=global` pool: SQL pre-rank, `LIMIT 500`, `calculateSalience` re-rank,
`brief.ts:359-398`) they fall from pool ranks 1, 5 and 6 into a tie at 0.69. With the access
count zeroed (`prod_acc0`), 76–79 candidates from 43–46 distinct source files score strictly
above them; with no access history at all (`prod_noacc`, which also drops `last_accessed_at` from
recency), 57–79 candidates from 24–46 files do. For agent-specific requests that pool has a
nominal quota of five in the quota pass (phase 1 of `pickDedup`), which runs after the pinned
high-pain items have been placed (phase 0, counting toward `mainTarget`) and before the backfill by
global score; without an agent its quota is the whole brief (`buildPools`, `pickDedup` in
`brief.ts:438-480`). Their positions
(95–119 under `prod_acc0`, 76–119 under `prod_noacc`) are stable-sort order inside the 0.69 tie
block, not a ranking. The recomputation stops before final selection: near-duplicate dedup was not
replayed, and it may remove candidates above them or reject them, so these pool positions do not
by themselves establish final served membership.
The first version
of this counterfactual (`contrafactual-do-topo.py`, `out/TOP-COUNTERFACTUAL-2026-08-29.json`)
used a linear 365-day recency from `source_date` and a 0.5 default for `importance`, which is
not the production function; it gave 131/129/128, and the new artifact reproduces that number
as an anchor.

Tracked search traffic is necessary for their observed salience ranks in the measured
counterfactual. The pin (F7, §4.3.1) separately affects selection, and for one of the three it is
measured as necessary for main-set membership: lifting it removes 116107 from the main set of every
reconstructed brief on every day with briefs from 2026-08-21 to 2026-09-07, with its salience
rank unchanged, and 227328 takes its place, while 112241 and 116467 stay
(`A-filters-disaggregation/out-ord0826.json`, `lift_F7_pinned`). The pin protects only what the
score has already placed in the no-fresh brief (`brief.ts:819-821`).

**Caveat:** the population of the counterfactual is 149, while §4.3 counts 201 distinct chunks in the
same window. The 52 missing are one identified set, not a coincidence (an open reconciliation
declared on 2026-09-21 after adversarial review, closed on 2026-10-04 by
`measurement/sprint-recon-52-e-sondas.py`, `RECON-52-e-sondas-2026-10-04.json`). As sets, the
52 absent from the week (201 → 149) are exactly the 52 absent from each of 2026-08-20,
2026-08-21 and 2026-08-22. They are ids 308114–308165: one ingestion of `memory/lessons.md`
(`lesson`, created 2026-08-20 02:02:03 UTC), served only by the coverage channel (2 per brief,
1,300 briefs, all six agents) from 2026-08-20 21:38 to 2026-08-22 19:07 UTC. The file was
re-ingested on 2026-08-22 02:01:58 UTC and the 52 were replaced by 53 new chunks. All 53
replacements were served in the window and are among the 149. A deleted chunk has no
`importance`, `pain` or `access_count` to recompute salience from, so the 149-chunk recompute
of 2026-08-29 leaves them out. The 52 were restored from a backup taken while they existed;
the result is below.

**Caveat:** the set is also defined by the original score, which the adversarial objection pointed out
as possible circularity (correctly, in form). The choice is conservative, by an argument
that does not depend on measurement: recomputing over a larger pool can only add
competitors, and adding competitors never improves anyone's position. So 44–46 is a
lower bound on the drop. It is now measured on the full pool
(`RECON-52-e-sondas-2026-10-04.json` for the restored rows,
`out/SALIENCE-COUNTERFACTUAL-PROD-2026-10-05.json` for the scores): with the 52 deleted chunks
restored from a backup taken while they existed (2026-08-21 06:00 UTC), and zeroing the access
term, the three fall to 54–56 of 201. That is 10 places lower, not 52: of the restored chunks
only the 10 with `pain = 0.9` outrank them. One caveat: the 52 are earlier versions of
`lessons.md` whose replacements are already among the 149, so the 201-pool counts that content
twice; it is nonetheless the population that was served. Excluding our five health probes
(§4.3) the figures are 40–42 of 144 and 50–52 of 196. Every variant takes the three out of the
top-10; none places them beyond rank 100.

**Caveat.** The objection that
motivated this measurement, raised in adversarial review, was that `pain = 1.00` and
`importance = 0.80` could suffice to put them at the top, making access irrelevant and
the word "determined" too strong. The objection was valid in form and false in
substance: those values are high, but not unique. Between 22 and 44 other chunks
of the 149 score strictly above them without the access term, and it is the old traffic that
puts the three ahead of them.

**Caveat:** a record of how the claim came to need this. The sentence said "the top of the
brief is a *fossil* of search traffic from months ago", and the metaphor was replaced by
"determined by" in a pass that removed value judgment from the text. But "determined"
is a stronger causal claim than the metaphor it replaced: neutralizing the tone
hardened the claim. The counterfactual above exists because the swap left it exposed. Nor is it an isolated
case: of the 9,755 chunks with any access, 7,908 (81%) had gone more than 60 days without
being accessed, with the access component intact. This count has no preserved artifact, and
its instant is not recorded; by context it is the 2026-08-28 measurement.

**Note:** the three constant items belong to the main pool, by
deduction. The coverage channel orders by `last_served ASC`. A chunk served in the
previous brief has the most recent possible `last_served`, so it sits at the end of that
ordering, behind the entire stratum of never-served items. A chunk present in 4,632 of 4,632
briefs cannot have been chosen by a comparator that prioritizes the least-recently-
served. This decomposes the concentration between the two channels without needing a position column
in the log, which does not exist.

**Caveat:** the feedback loop is NOT closed by the system, and this is a deliberate design decision. `access_count` is incremented only in `search.ts:396`, and the brief declares
in its header that it is *"read-only over `chunks`; does NOT touch `access_count`"*. So serving in
the brief does not raise the priority of anything, which separates this case from the
classic recommendation feedback loop (Chaney et al.), in which exposure reinforces itself. Here
exposure in the brief does not reinforce itself; what exists is a permanent encoding,
without decay, of past traffic. If the loop closes, it closes through the agent (which sees the
item and may search for it again), and that we did not measure.

**The symmetry.** The two channels of the surface freeze, for
opposite reasons and neither of them tied to capacity:

| channel | slots | why it freezes | responds to score adjustment? |
|---|---|---|---|
| main pool | 8 | deterministic score with a **monotonic, non-decaying** component | **yes** — and nobody adjusts it |
| coverage | 2 | eligible population of **108 chunks** (0.16% of the corpus), exhausted 100% on each measured day (defective-ingestion regime, §4.3.1); **lexicographic** order | **only up to a ceiling** of 4.86% (§5; 2026-08-26 corpus, defective-ingestion regime) |

The main pool *could* be corrected by score, and nobody corrects it. The coverage channel,
designed to compensate for the main pool, has a daily reach bounded by its eligible population (path patterns, the
importance/pain floor and age windows), which it exhausted in the measured regime, and within a brief it responds to score only within `last_served` ties
(17/350 here) and then saturates. That is why the 8.7× headroom
does not turn into coverage.

### 4.4 The deductive prediction, and the test

The coverage comparator is lexicographic: when `last_served` differs, `salience`
is never consulted. An additive bonus on `salience` only decides within strata
of identical `last_served`. Hence any intervention of this kind has a ceiling. Under the premises
of §5.3 (prefix selection, filtering that does not depend on the bonus), only briefs in which the
cut of the coverage pool falls inside a `last_served` tie with a designated item on the
non-selected side can change, so their fraction bounds the alterable briefs from above; it is a
necessary condition, not a sufficient one (§5.4). The ceiling reported here is measured directly,
as the fraction of states whose served set changes at a saturating dose in a replay of the
production pipeline, deduplication included (§5.6).

The test is a counterfactual replay with increasing dose over 350 real brief states, faithful to the serving
pipeline. The `w = 2` column is the dose configured for the *shadow* arm during the measured
window: the treated composition under it, over these 350 historical states, was computed and
logged and never delivered to any agent. (In the later trial, `w = 2` was served in six
epochs, as recorded in `DEVIATIONS-FOR-PAPER.md` §10.29. That is Paper B's data, not these 350 states.)
Caveat. Until 2026-08-30
that column was labelled only `(served)`, with the caveat on this line. A read-through
showed that the label alone suggests delivery to the agent, because a table label is read
without the paragraph that precedes it. See Appendix F.

| `w` | 0 | 0.5 | 1 | **2** (*shadow* dose) | 4 | 7.5 | 15 | 100 | 100,000 |
|---|---|---|---|---|---|---|---|---|---|
| states that change | **0** | 5 | 8 | **11** | 15 | 17 | 17 | 17 | **17** |
| displacement events | 0 | 5 | 8 | 12 | 18 | 20 | 20 | 20 | 20 |

- **negative control passes:** `w = 0` gives 0 in 350/350;
- monotone in each of the 350 states, not only in the aggregate;
- ceiling 17/350 = 4.86%;
- saturation at `w ∈ (4.0, 4.4]`: on a fine grid of 23 doses (0.02 to 13) over the 17 states
  that move, the lowest tested dose at which a state changes ranges from 0.02 to 4.4 (median
  1.7), with 0 non-monotone states and 0 states that never change on the grid. Five states
  already change at 0.02, the lowest dose tested, so their thresholds are bounded only from
  above; the spread across states is at least 200× (4.0/0.02) and is not measured exactly;
- the *shadow* dose of the measured window reproduces the published rate: `w = 2` gives
  11/350 = 3.1429%.

**Figure 3** (`out/fig3-dose-resposta.svg`): the two dose-response series
on a logarithmic `w` axis, a coarse grid (9 doses × 350 states) and a fine grid (23 doses × the
17 that move), with the registered band `{2 · 4 · 7.5}` marked on the axis, the
`17/350` ceiling line and the saturation region. Generated by `fig3-dose-resposta.py`.

**Caveat.** The two series have different denominators and the same numerator, and that is what
authorizes overlaying them: a state outside the 17 does not move at any dose. This can be
checked rather than argued. The series share exactly one dose (`w = 1`), and there
both give 8. The script aborts if they cease to match, because two curves on the same
axis that disagree where they cross make a figure that is silently wrong.

**Caveat.** The negative control `w = 0 ⇒ 0/350` appears as an annotation, not as a point, because zero
does not exist on a log axis. Placing it on the first tick would mean plotting `w = 0.015`, which was not
measured; omitting it would mean not reporting the control.

**Caveat.** The quantity that governs is distance, not step, but this measurement does not show
it. At the largest `w_min` (4.4) the two S1 items that enter receive `4.4 · 0.043 · 0.25 =
0.0473`, 0.90× the largest gap between adjacent candidates of the pool (`0.05272`, measured in
a single state; `out/BONUS-VS-STEP-2026-10-05.json`). An earlier version said 0.0946 and 1.79×,
using a multiplier of 0.5 for S1 that production does not apply. Whether these items crossed
one position or several is not established.

### 4.5 What these measurements do **not** identify

This section is mandatory, and it comes before the discussion of purpose. The most
important limit is the first, and it holds for everything this paper reports:

- nothing here says that the missing exposure matters. There is no instrumented
  downstream outcome. Three agent-facing quality tables have 0 rows; this was measured
  on 2026-08-30 and not re-verified after the trial closed (dose switched off
  2026-09-21 09:43:05Z, `DEVIATIONS-FOR-PAPER.md` §10.29), so it is a declared debt and not a
  current fact. The search telemetry recorded mostly the cron health probe: in a closed
  7-day window analysed on 2026-08-27, 325 of 343 rows (94.8%) fall within one minute of the
  two cron firings per hour (minutes 21–23 and 51–53 of the `22,52 * * * *` schedule), leaving
  18 rows (2.6/day) outside those windows, whose origin was not independently established. Of the 25
  columns of that table, 16 had no writer in a census taken on 2026-08-27, among them the
  only one with per-chunk identification (`top_chunk_ids`). Its writer was restored that night
  (commit `32f78109`, together with `top_scores`; `query_text` deliberately left out), less
  than a day before the exposure window closes (2026-08-28, `out/superficie.json`), so that
  window is almost entirely without it. That
  83.78% of the corpus is no-record (§3.1) is a fact about the surface, not about
  the usefulness of what was left out. A reader who concludes "the system is losing valuable
  information" has gone beyond what was measured;
- nothing is randomized, and nothing needs to be. This paper does not estimate an intervention
  effect. Every comparison is descriptive or deductive: the surface is a census, and the ceiling
  of §5 is a consequence of the comparator verified by replay. Effect estimation is the
  object of the interventional study, which is not reported here (see "Relation to the
  pre-registration");
- one system, one corpus, one operator. The exposure numbers are this system's. What
  generalizes is the method and the shape of the argument (a lexicographic comparator imposes a
  ceiling, and the ceiling depends on the granularity of the key), not the percentages;
- **the coverage state feeds back.** `last_served` is not frozen: serving at `T`
  alters the strata structure at `T+1`. This limits any extrapolation of the ceiling to
  sustained-treatment regimes.

## 5. Mechanism

This section is deductive. What it proves holds for any ranker with the same
form, serving a prefix of one lexicographic order, and it is the reason a study on an `n = 1` system still says something general
(§7). The whole structure comes from seven lines of code, quoted rather than
paraphrased.

### 5.1 The object

Let `P` be the set of eligible candidates (the *pool*). Each `c ∈ P` has:

- `ℓ(c) ∈ ℝ ∪ {−∞}`: the instant of the last serve, with `−∞` for never-served;
- `s(c) ∈ ℝ`: the `salience`.

The production comparator, verbatim (`src/api/brief-diversity.ts:130-140`):

```ts
const al = aLastServedMs ?? Number.NEGATIVE_INFINITY;
const bl = bLastServedMs ?? Number.NEGATIVE_INFINITY;
if (al !== bl) return al - bl;      // ASC: menos-recentemente-servido primeiro
return bSalience - aSalience;       // tie: maior salience
```

This is exactly the lexicographic order `≺` on the pair `(ℓ(c), −s(c))`:

> `c ≺ c′` ⟺ `ℓ(c) < ℓ(c′)`, or `ℓ(c) = ℓ(c′)` and `s(c) > s(c′)`.

The intervention is a function `b : P → ℝ₊`, zero outside the designated set `D`. It
enters at a single point (`src/api/brief.ts:612-614`):

```ts
const eff = (c) => c.salience + (boosts?.get(c.row.id) ?? 0);
ranked.sort((a, b) => coverageCompare(a.lastServedMs, eff(a), b.lastServedMs, eff(b)));
```

That is: `b` shifts only the second argument of `coverageCompare`. Write
`≺_b` for the resulting order.

**Where `D` comes from, and what of that matters here.** The designated set has 19 designated items,
one per signature group, drawn from a population of 55 by a rule with a declared seed
and verifiable precedence over the beacon (Appendix B). For what this paper
measures, `D` is merely a fixed set that a third party can re-derive: an
independent reviewer reproduced the 19 using only the public beacon and the deposited CSV. The criterion
that selected the 55 is severity adjudication by a panel, and it belongs to the interventional
study (Appendix C).

**Caveat.** Both numbers in §5 inherit that provenance. The effective
bonus is `W = w · Δ_cut · severity_pain`, so the panel's label scales the dose per chunk:

- the ceiling (§5.3, §5.7) was measured at `w = 100,000` with the recorded severity labels held
  fixed. Its sensitivity to changing those labels was not measured: raising `w` does not remove
  the relative differences between multipliers, so when two designated items share a stratum the
  labels can decide which of them is served;
- the saturation band `(4.0, 4.4]` (§5.4) locates a dose, and the
  effective dose of each chunk depends on the multiplier. Read as a property of the comparator,
  it would be more general than it is.

### 5.2 Proposition 1: invariance across strata

*For any `c, c′` with `ℓ(c) ≠ ℓ(c′)`, the relative order of `c` and `c′` is the
same under `≺` and under `≺_b`, for every `b`.*

**Proof.** If `ℓ(c) ≠ ℓ(c′)`, the comparator returns on the first line, whose value
`al − bl` depends on neither of the `salience` arguments. Hence `b` cannot
alter it. ∎

Define `c ∼ c′` ⟺ `ℓ(c) = ℓ(c′)`. The equivalence classes are the strata.
All never-served items fall into a single stratum (`ℓ = −∞`).

**Corollary 1 (the order is a concatenation).** The sequence sorted under `≺_b` is the
concatenation, over the strata in increasing order of `ℓ`, of each stratum
sorted internally by `−s_b`. Consequently, `b` permutes within
strata and never moves an item from one stratum to another.

### 5.3 Corollary 2: the ceiling, and where it lives

The surface has fixed capacity: of the 10 slots in the brief, the coverage pool
feeds at most `K = freshSlots`. In production `K = 2`, and the provenance of that
number has to be stated carefully, because it is not measured in the log:

- it is the default `DIVERSITY_DEFAULTS.freshSlots = 2`, overridable by
  `NOX_BRIEF_DIV_FRESH_SLOTS`, and there was no override, neither in the systemd unit nor in
  the `.env`, verified on 2026-08-27 (`SUPERFICIE-2026-08-27.md`), i.e. within the measured
  window. The unit's configuration changed afterwards for the trial, and it is not re-verified
  here;
- it is a ceiling, not a quota: the fill loop exits on
  `if (freshGot >= freshSlots || picked.length >= n) break` (`brief.ts:472`), and a candidate
  rejected by deduplication does not count, so a brief may have fewer;
- and `brief_log` has no column that marks the origin of the slot, so the split
  "8 main + 2 coverage" is not observable in the record. It is configuration
  plus code, and is declared as such.

The derivation assumes that the coverage pool serves the first `≤ K` items of `≺_b` that survive
deduplication. In the measured window this holds: the per-agent sub-pool was empty (§4.3.1), so
`interleaveFresh` returns the global sub-pool unchanged, and `pickDedup` scans it in order
(`brief.ts:470-474`). It does not hold in general. With both sub-pools populated, the coverage
pool is the round-robin of two orders, each sorted by `≺_b` (`brief-diversity.ts:180-196`); the
statements below then apply to each sub-pool separately, and they do not cover the
interleaving. Deduplication against the main-pool items does not depend on `b`. Deduplication
between two coverage candidates does: when two near-duplicates share a stratum, the bonus
decides which of them is served even if the cut does not fall in that stratum, and consequence
1 below does not count that case. The 17/350 is measured by replay of the production code and
needs none of these premises.

*The served set changes under `b` only if there exists a stratum that contains both
a selected item and a non-selected item.*

**Proof.** By Corollary 1, `b` only permutes within strata. A stratum
entirely contained in the prefix has its items permuted among positions that are all
selected ⇒ the set does not change. A stratum entirely outside the prefix,
likewise. What remains is the stratum that crosses the cut, and by Corollary 1 there is at most
one. ∎

Three consequences, and all three are measurable rather than arguable:

1. under these premises, the fraction of states in which the cut falls strictly inside a
   stratum and a designated item is on the non-selected side bounds the alterable decisions
   from above. The condition is necessary, not sufficient: with several bonused items in the
   stratum a designated item may not enter (§5.4). The ceiling itself is measured, as the
   fraction of states whose served set changes at a saturating dose in the replay, which
   includes deduplication. Measured in §4.4: 17/350 = 4.86%. In §5.6 those same 17
   states are exactly the ones in which there is a swap, with all 20 entries
   occurring within the stratum of the item that left;
2. if `ℓ` were injective, `b` would have no effect at all. Every stratum would be
   a singleton, nothing would cross the cut, and the intervention would be identically
   inert. The entire room for maneuver of the intervention comes from ties in the
   dominant coordinate. In nox-mem these are the stratum of the never-served items and the
   one-second resolution of `served_at`. In the 350 measured states the first is empty (0
   never-served in the pool on 2026-08-26/27, §4.3.1), so the measured 17/350 comes entirely
   from one-second ties;
3. the ceiling is a property of the distribution of `ℓ` in the pool, which the
   traffic itself produces, and not a design parameter.

### 5.4 Corollary 3: saturation, and why step is not the right quantity

Within the stratum that crosses the cut, the order is by `−s_b`, and the bonus is applied to
every designated item at once, so the selected item `c_K` of lowest position in that stratum
may itself carry a bonus. A non-selected designated item `d` enters the served set exactly when
its treated score `s(d) + b(d)`, tie-break included, ranks within the slots that the stratum
receives. When `d` is the only bonused item of the stratum this reduces to

```
b(d)  >  s(c_K) − s(d)
```

or to equality with the tie-break placing `d` ahead of `c_K` (on equal treated scores the
comparator returns 0 and the stable sort keeps the input order), so the strict inequality is
sufficient but, with the tie-break included, not necessary. With several bonused items in the
stratum the condition does not reduce to this form: with `K = 1`, a selected designated `c` with `s = 0.8, b = 0.4`
keeps its slot against `d` with `s = 0.7, b = 0.2`, although `0.2 > 0.8 − 0.7`. Either way the
quantity is a distance to the cut, not the step to the immediate neighbour of `d`. Since every
bonus is proportional to `w` (`W = w · Δ_cut · severity_pain`) and there are finitely many
states, there is a finite dose beyond which the treated order inside every crossing stratum no
longer changes: saturation is an identity, not a chosen threshold. Measured on the dose grids:
the last change occurs at `w ∈ (4.0, 4.4]`, with the lowest changing dose ranging across states
from 0.02 (the grid's lowest dose, so a censored value) to 4.4, a spread of at least 200×.

**Caveat.** This is where a monitoring trigger goes wrong. Item 7 of the registration watched
`max_j (s(c_j) − s(c_{j+1}))`, the largest step between adjacent items anywhere in the pool.
That is a different quantity from the distance of §5.4, and the two are not ordered in general:
the distance of `d` to the cut is the sum of the adjacent gaps along its path inside the
stratum, so it is at least the largest of those gaps, while the largest gap elsewhere in the
pool can be larger or smaller. As measured, the two items whose threshold is the largest
`w_min` (4.4; both S1) receive `4.4 · 0.043 · 0.25 = 0.0473` at that dose, 0.90× the largest
adjacent gap of the global sub-pool (0.05272, one state at 2026-08-26 20:35Z with the inclusive
cut, `out/gaps.json`), so this comparison does not show that they crossed several positions
(`measurement/sprint-bonus-vs-passo.py`, `out/BONUS-VS-STEP-2026-10-05.json`). An earlier
version said 0.0946 and 1.79×, from a severity multiplier of 0.5 for S1 hardcoded in the
replay's summary (`replay-oportunidade.mjs:944, 1014-1019`); production multiplies S1 by 0.25.
A trigger on the step can stay green while the channel saturates because it watches the wrong
quantity, which is what forced the reimplementation of item 7 as the identity
`churn(w_servido) = churn(w_absurdo)`.

### 5.5 The design consequence

A fixed-capacity surface ordered lexicographically responds to interventions on the subordinate
coordinate only within ties of the dominant one, and that response is bounded by construction.
To move what the agent sees beyond that bound there are three levers, and the score is not one
of them:

| lever | effect |
|---|---|
| the **dominant** coordinate (`ℓ`: rotation policy) | reorders across strata — no ceiling |
| the **capacity** `K` | moves the cut along the order: it changes which stratum (at most one, §5.3) straddles the cut and how many lie wholly inside the served prefix |
| the **eligibility** (who enters `P`) | changes the object, not the order |
| ~~the subordinate score~~ | bounded by Corollary 2, saturating at a finite dose (§5.4) |

The table holds for the coverage channel, which is 2 of the 10 slots, and not for the
whole surface. The other 8 come from the main pool, ordered by pure `salience`
(§2), where an additive bonus acts on the dominant coordinate and has no ceiling. Writing "the
score is not a lever" without that qualification would be false for 80% of the slots, and it is a
qualification that the Abstract needs to carry, not only this section.

The correct conclusion is narrower and still holds: the channel that exists precisely
to serve the never-served is the only one whose response to relevance adjustments is bounded by
construction. The surface has two parts with different algebras, and the part reserved for
coverage is the one that responds to the score only within `last_served` ties and then saturates
(§5.3, §5.4).

It is the same conclusion as §4, reached by another route, and it has two parts that must be kept
apart. The first is the channel's daily reach, bounded by its eligible population. Eligibility
combines path patterns, the importance/pain floor and age windows. In the measured regime, the
channel exhausted that eligible population on every measured day (§4.3.1). The second is
per-brief selection.
Holding eligibility fixed, an additive salience bonus changes per-brief selection only within
`last_served` ties. §4 measures the first on the population of chunks; §5 proves why the second
is bounded. With eligibility, designation and severity multipliers held fixed, the tested dose
family saturated at 17/350 states. This is not a maximum over all additive salience adjustments:
with eligibility held fixed, other designations give 17 to 26 of 350 (§5.7.1).

### 5.6 The test this derivation has to pass

The derivation can be checked against recorded quantities. The first attempt to test it failed because of a defect in the
test, and we recount that failure here because the episode belongs to §6 and is the reason the
current test has the form it has.

**Attempt 1, invalid.** Classify the 350 states by the position of the designated item in the
ordered pool: outside the pool / already selected / in a stratum different from the cut /
in the stratum of the cut. The prediction was that the last class would contain exactly the 17
at the ceiling. Result: 25, and, decisively, only 1 of the 17 fell in it.
`FRESH_CANDIDATE_POOL` and `GLOBAL_FRESH_PATTERNS` are module-private constants of `brief.ts`
(l.111, l.135), and the ordered pool the coverage slots are drawn from is built inside
`buildBriefDiverse` (`interleaveFresh` over the two sub-pools, then `pickDedup`, which places the
pinned items first and deduplicates as it fills) and returned by no export, so that pool was a reconstruction, and the 24 violations of the prefix assumption were
the symptom. Testing a derivation against a reconstructed pipeline does not test the
derivation: it tests the reconstruction.

**Test 2, on recorded quantities.** When deduplication between coverage candidates does not
intervene (§5.3), Proposition 1 implies a pattern that does not require assembling any pool:

> In every state in which the served set changes, each id that enters must share
> `last_served` with some id that leaves.

The check is a same-stratum matching check on these replay states, not a falsifier of
Proposition 1. Deduplication in `pickDedup` is order-dependent (`brief.ts:420-433`, §5.3): a bonus
that only reorders one stratum can change which of two near-duplicates is rejected and so admit
an id from another stratum, with no cross-stratum order changed. With that deduplication, an
unmatched entry would not by itself refute Proposition 1. The three quantities (`would_enter`, `would_leave` and
`last_served` in the pruned serve-state) are recorded by production and by the replay,
not derived. Caveat. "350/350" is coverage, not validation: it means that the 350 brief states of
the window were reproduced, each from its own recorded serve-state. What was *validated*, and
against what, is in this section (§5.6): the pool reconstruction was withdrawn for producing 24 violations
of the prefix assumption, and what remains uses only recorded quantities.

`replay-oportunidade.mjs --modo porque --corte rowid --so-ts-file ts-350.txt`
aborts if there is a single entry without a partner. (`ts-350.txt` is the list of the 350
state timestamps. It was not kept and its hash was not recorded. The same 350 timestamps are
the `ts` fields of `out/c-350-v3.json`; that they match the original input byte for byte is
not verified.)

**Result.**

| | |
|---|---|
| states replayed | **350** (errors: 0) |
| states in which the served set changes | **17** |
| ids that enter, summed | **20** |
| **entries with no exit in the same stratum** | **0** |
| same-stratum matching check | **passes** |

All 20 observed entries had an exit in the same stratum. This is an empirical property of these
replay states. The `17` and the `20` exactly reproduce the independent dose artifact
(`mexeu = 17`, `churn_total = 20` at `w = 100,000`), and that reproduction is what makes the
zero interpretable: it guarantees that the two runs speak about the same population.

**Caveat.** The zero was also checked against the possibility of being a test that does not
look. We mutated the stratum function to give each id its own stratum, under
which no entry would have a partner; the mode then reports 20 violations in 17
states and aborts. The assertion bites at the maximum possible, so the `0` in the table is a
result, not instrument silence.

**Provenance of the run.** Corpus = epoch snapshot
`e20260826T060003Z.db` (`sha256` of its first MB `56826f69…`), probe exclusion = none, cut by
insertion order, designation with `sha256` verified. This provenance is identical to the dose
artifact's. Caveat. The first execution of this test diverged (13 states, not 17) because I
had changed two things at once (live corpus and exclusion of the health probes: every preserved probe list has 5 `brief_id`s,
but this first run was not preserved, so how many it excluded cannot be checked); the diff of the `procedencia` block of the two
artifacts showed both.

**Caveat.** That corpus no longer exists: epoch retention pruned it, and it is not among the four
preserved trial databases nor on either host or the author's machine (checked 2026-10-03/04).
The run can be re-read from its artifacts but not re-executed on its original input.

### 5.7 The 4.86% ceiling is a property of the FORMAT, not of the comparator

Proposition 1 says that the bonus permutes within a `last_served` tie and never crosses it.
From this it follows, deductively, that the reachability ceiling depends on more than the
comparator: it depends on how many ties the `last_served` format produces. The
resolution of `served_at` is inherited from SQLite's `datetime('now')`: seconds. Nobody chose it as
a design parameter; it is the default of a library function.

The counterfactual that separates the two things is the same replay with the stratum key
truncated and padded back with zeros (`--granularidade`, in `replay-oportunidade.mjs`). Truncating
is surgical here because of a fact verified in the source: `served_at` has a single live consumer
in serving, the stratum key. The other (`serveCounts`, the window of the
novelty penalty) is exported and tested, but no production path calls it; it is the
remnant of mechanism A, replaced by coverage in the 2026-06-26 tune (`brief.ts:588`).

| resolution of `served_at` | briefs that change | ceiling |
|---|---:|---:|
| **second — production's** | **17** / 350 | **4.86%** |
| minute | 127 / 350 | 36.29% |
| hour | 281 / 350 | 80.29% |
| day | 348 / 350 | 99.43% |

Corpus, designation, cut, dose and the set of 350 states are byte for byte the same in the four
rows; the consolidating script aborts if any of them diverges, and the native granularity must
reproduce the published `17/350` before the table is emitted (both assertions were tested by
mutation). Artifact: `CEILING-GRANULARITY-2026-08-28.json`.

The intuition for why lies in the size of the ties, and it comes from another population:
the 1,787 chunks that were ever served, over the whole history of the `brief_log`, without the
per-brief pruning that the replay applies. In that population, truncating takes the number of
distinct strata (counts not preserved in any artifact) from 1,139 (second) to 951, 311 and 57, and the largest stratum from 14 to
61, 89 and 186. The two sets of numbers answer different questions and must not be
read on the same line: one describes the tie structure of the served corpus, the other counts
briefs that change in the replay.

**The reading, and the care it demands.** A mechanism that reaches 4.86% of briefs
would reach 36% if the system stored the time with one field fewer.

**Caveat.** It would be overclaiming to say that the ceiling is "a fact about the width of a text
field". It is a fact about the ratio between serving cadence and key resolution: the
serves concentrated in the same second create the ties, and in a system that served one item
per hour the same field width would move almost nothing. What the measurement establishes
is that one of the two terms of that ratio was inherited from a default (the resolution comes
from SQLite's `datetime('now')`, not from a design decision), and that changing only it shifts the
reach of the mechanism by an order of magnitude. We did not isolate the two terms; doing so
would require repeating the table over a corpus with artificially spaced cadence.

#### 5.7.1 And the ceiling also depends on WHICH chunk the draw picked

The designation rule chooses one chunk per signature group by a draw with a declared seed.
The choice within the group is, by construction, arbitrary, so the `17/350` can be a property of
the comparator or an accident of the draw, and the difference matters for how the number is read.

We redid the same replay with eight alternative designations, generated by the same rule
over the same population, varying only the seed. The seeds come from a family derived
deterministically from a fixed phrase in the script (choosing them by hand would allow fishing for
the result, since the beacon is public), and all eight are reported
(`CEILING-DESIGNATION-SENSITIVITY-2026-08-28.json`):

| | change / 350 | ceiling |
|---|---:|---:|
| designation **in force** | **17** | **4.86%** |
| minimum of the eight alternatives | 17 | 4.86% |
| median | 20 | 5.71% |
| maximum | 26 | 7.43% |

The arbitrariness is bounded by construction: 12 of the 19 groups are singletons, so
no seed can move more than 7 designated items.

**Two readings.** The first, which the data support: the
ceiling is robust in order of magnitude: nine draws of the same rule give from 4.86% to
7.43%, and none comes close to changing the conclusion that the mechanism reaches a few
percent of briefs. The second: the designation in force is at the minimum of the distribution,
tied with `sens-03`, which also gives 17, and not alone. Reporting `4.86%` as "the ceiling of the
mechanism" describes the extreme, not the rule.

**Caveat.** Even so, one must not overstate. With 8 alternatives, two of the nine results share
the minimum (the designation in force and `sens-03`, both 17), so under exchangeable permutation
the probability that the pre-specified designation sits at the minimum is 2/9 ≈ 22%: being at
the minimum does not establish that it is atypical. The median `5.71%` is an n = 8 point, with deviation ≈ 2.9
states; any reasonable interval covers 17 to 22, so the median should not be
read as "the value the rule produces". What is supported is simpler and weaker:
where this paper says `4.86%`, read *the ceiling under the designation in force*, and the ceiling of
the rule is a distribution that we did not measure precisely enough to summarize in one number.

**Caveat.** The alternatives also do not move only *more* briefs: they move different ones. The intersection with
the 17 original states stays between 9 and 14 (`estados_em_comum_com_a_publicada` in the
artifact; it concerns replay states, not which designated items were drawn). The granularity
finding, in which the beneficiary changes identity when the resolution changes, shows the same pattern: which chunk
receives exposure is decided by details that nobody chose as policy.

**Caveat.** We did not measure the interaction between the two axes (designation × granularity); the table of
§5.7 is entirely under the designation in force, and this one is entirely under second resolution.

**Caveat.** A growing part of this table is decided by a tie-break that nobody declared.
Truncating creates ties, and when two candidates tie on `last_served` and on
`salience`, the comparator does not separate them; the sort is stable, so what decides is the
order in which SQLite returned the rows. The SQL pre-rank of this channel orders by a coarse
expression (`0.55·importance + 0.10·pain + 0.1 if access > 0`) that takes six values over the
108; the comparator itself re-sorts by `calculateSalience` (§4.3.2), which takes 15 values over
the same 108. An earlier version of this table counted ties on the pre-rank expression
(`measurement/empates-por-granularidade.py`, `TIEBREAK-EXPOSURE-2026-08-29.json`: 68 / 269 /
917 / 1,656 pairs), a coarser key than the comparator's. Exposure measured on the comparator's
key, at three instants inside the 350-state replay window that the input covers (2026-08-26
20:37Z, 22:00Z and 23:52:09Z; `measurement/sprint-empates-salience-producao.mjs`,
`out/TIEBREAK-EXPOSURE-PROD-2026-10-05.json`), with the pre-rank expression at the same
instants for comparison:

| resolution | indistinguishable pairs | % of pairs | largest block | pre-rank expression, same instants |
|---|---:|---:|---:|---:|
| **second — production's** | **34–42** | **0.59–0.73%** | 4 | 45–59 |
| minute | 212–238 | 3.67–4.12% | 10–12 | 277–322 |
| hour | 472–749 | 8.17–12.96% | 18–33 | 663–1,024 |
| day | 1,197 | 20.72% | 42 | 1,656 |

The input is a read-only copy of the 2026-09-07 trial epoch (the one behind
`out/SALIENCE-COUNTERFACTUAL-PROD-2026-10-05.json`), with `importance`, `pain` and access fields
as stored there and each candidate's `last_served` taken from the `brief_log` rows up to the
instant. The pool at each instant is exactly the 108 ids of §4.3.1. The day row of the pre-rank
column reproduces the published 1,656; the published second, minute and hour values come from
an unrecorded instant of 2026-08-29 that this input does not reach. The ties that remain under
`calculateSalience` are chunks of one `lessons.md` ingestion with identical fields, or entity
chunks with the same importance, pain, access count and access instant
(`out/TIEBREAK-EXPOSURE-PROD-SHARED-2026-10-05.json`, the same run with `last_accessed_at`,
`created_at` and a source-file class added to each tie group; it holds at all five instants).

The natural counter-argument, that "the two arms share the same arbitrary order, so
it cancels out", does not hold: a shared tie-break does not guarantee cancellation, because it
can change membership at the selection boundaries, which is where churn is born and dies. Here
`churn` counts the treated-only ids (`would_enter`); for equally sized sets it is half the
cardinality of their symmetric difference.

What survives and what does not: the direction and the order of magnitude of the effect, because
on the comparator's key the exposure grows 28–35× from second to day while the ceiling grows
20×, and because at the resolution this paper reports it is 0.59–0.73% of pairs. The exact values of the coarse rows
(127, 281, 348) carry an arbitrary component that we did not quantify;
doing so would require rerunning the 4×350 with a third, explicit tie-break coordinate, and we
declare that we did not do so.

**Caveat.** A prediction of ours died in this test, and it stays. The design note said:
"coarsening only merges strata, never splits them ⇒ the ceiling is monotonically non-decreasing, and that
monotonicity is the self-test of the instrument". The count does in fact rise, but the sets
are not nested: 1 state leaves from second→minute, 2 from minute→hour. The error is that merging
strata also moves the control arm, and churn is the difference between the two
arms. As measured, the three lost states split into opposite mechanisms:

- **redundancy:** under minute, the designated item comes to enter the control on its own; the
  intervention is left with nothing to do;
- **unreachability:** under hour, the designated item's whole stratum drops below the selection
  cut, and the bonus does not cross strata. It is Proposition 1 biting in the opposite
  direction.

So the monotonicity of the count is empirical, not structural, and the consolidator reports it
instead of requiring it; a guard that asserted nesting would be wrong and would have hidden the
finding. And the effect is not only one of quantity: in one of the states the id that enters changes from
`308284` under second to `308296` under minute. The resolution of the timestamp also decides
which chunk benefits.

#### 5.7.2 A third axis: the anchor measured, the ceiling not

This finding comes from an audit of the artifact chain (2026-08-30), not from review. The replay that
produces the 4.86% ceiling ran with `sondas_excluidas: []`: none of our own
health probes was removed from the `serve_state`. There existed, in the repository, two artifacts
recorded on 2026-08-27 and never read by anyone (`out/ancora-sondas.json` and
`ancora-sem-exclusao.json`) which show that this choice is not neutral:

| | without excluding | excluding the 25 rows of 5 probes |
|---|---:|---:|
| distinct `last_served` groups | 44 | **43** |
| position of the first chunk of the study | 3 | **0** |

The anchor moves, and the paper reported "two axes" when there are three. The ceiling moves
with it, as measured on 2026-08-30, after this section had existed for two days stating that
we did not know:

| | without excluding | excluding the probes |
|---|---:|---:|
| states that change (of 350) | 17 | **13** |
| ceiling | 4.86% | **3.71%** |
| total `churn` | 20 | **13** |
| sensitive states in common | — | **1** |

Two readings, and the second is the stronger.

The ceiling falls by about a quarter. The published 4.86% includes the effect of our
own verification probes: five briefs that exist because we *confirmed that the
mechanism had gone up*. The act of measuring added itself to what was being measured, and the
decontaminated version of the reachability is smaller than the published one. The direction
matters for how the paper is read: the published ceiling is a loose upper bound, and loosened by us.
The argument that the surface is narrow comes out reinforced, not weakened.

Identity is hardly preserved: of 17 and 13 sensitive states, only ONE is
common to both arms. The sets are not nested. The exclusion does not remove some
states from a stable set; it almost entirely reorganizes which set is
sensitive. This is a much larger sensitivity than the difference between 17 and 13
suggests, and it only appears when identities are compared; anyone looking only at the totals would read
"four states fewer" and conclude that the convention hardly matters.

**How this was measured, given that the original condition was lost.** Paired design: the two
arms run over the same corpus of 2026-08-30, the same log of 350 states, the same
designation, and vary only the exclusion; the provenance of the two artifacts differs in
exactly two fields, `gerado_em` (2 seconds) and `sondas_excluidas`. The 350 states are
identical and in the same order, with the same `rowid_corte`, verified element by element.

**Caveat.** The paired arms ran on `e20260830T060001Z.db` (`sha256` of its first MB `3679bca8…`), an
epoch snapshot under the same retention that pruned `e20260826T060003Z.db` (§5.6). It is not among the
preserved trial databases, and it was not found on the research host or on the author's
machine on 2026-10-03; the production host was not searched. Both artifacts survive. The
input that would let a third party re-run them is, as far as we know, gone.

**Caveat.** The control that makes the comparison with the published number valid, at the level of
identity rather than count. The arm without exclusion, run on the 2026-08-30 corpus, returns
17/350 = 4.86%, the value published on the 2026-08-26 corpus. A matching total alone would be
the kind of evidence this section has just disqualified (17 and 13 sensitive states share only
one), so the comparison was redone state by state over the existing artifacts
(`measurement/sprint-comparabilidade-identidade-572.py`, `COMPARABILITY-IDENTITY-5.7.2.json`).
The 350 state keys `(ts, agent, rowid_corte)` coincide 350/350. The sensitive set is the same
17 states, not merely 17 states. In each of the 350 states the ids that would enter and leave
are identical. The undosed control arm (the top-10 served at w = 0, which depends on corpus and
serve-state but not on the dose) is identical, in order, in 350/350 states (`out/c-350-v3.json`
on 2026-08-26 against the 2026-08-30 arm). Changing the corpus moves neither the count, nor
which states are sensitive, nor the undosed ranking, so the arm with exclusion is comparable to
the published one, and not only to its own pair. The check can see a difference when one
exists: applied to the probe-exclusion arm it keeps 1 of 17 sensitive states and 1 of 350
control lists, and a mutation that keeps the count at 17 but changes one entering id makes it
fail. Without this control, the difference would be attributable to the corpus as much as to
the probes. It does not recover the level of the ceiling under exclusion on the original
corpus, which remains unrecoverable (below).

**Note.** The artifacts are `out/CEILING-PROBE-EXCLUSION-none-2026-08-30.json` and
`out/CEILING-PROBE-EXCLUSION-probes-2026-08-30.json`.

**Caveat.** The original condition is no longer reproducible, but the sensitivity is measurable.
These are two different things (↩ F-3.1). The replay corpus, `e20260826T060003Z.db`, was an
epoch snapshot and was rotated; on 2026-08-30 only those from 2026-08-28 to 2026-08-30 remained, and the daily backup of 2026-08-26 is from
another instant: the `sha256` of the first MB does not match the published pin. So the
level of the ceiling under probe exclusion is not recoverable.

What was recoverable is whether the exclusion moves the ceiling, through the paired design described
above, which is the same design as that of the two anchor artifacts, one level down. Two conditions
made this possible, and were verified before running:

- the closed-window log with the 350 states survived the rotation (it is an `.ndjson`, not a
  database snapshot), and the designation on disk matches the published `sha256`;
- sweeping the 2026-08-30 corpus by the same signature that identified the probes on 2026-08-27
  (a brief with 5 rows instead of the 10 of an organic brief), exactly the same
  five appear, and no new one. The exclusion is the same act in both corpora.

A pair of artifacts seemed to answer this, and does not. On 2026-08-30 the serving
machine held a `campo-churn.json` and a `campo-churn-sem-exclusao.json` (not preserved in the
repository or the trial's evidence archive; their current existence is not verified), and a direct reading
suggests a dramatic finding: the fidelity of the replay to the field falls from 0.909 to 0 when
the probes are excluded. This pair is not usable. The arm with exclusion was generated
at 15:17:11 and does not record `corte_serve_state`; the one without exclusion was generated at 15:18:55 and
records `estrito`. The field came into existence in the 104 seconds between the two (by the generation times
above; neither file was preserved, so those times cannot be re-checked): they are different
versions of the script, and the drop may be due to the exclusion or to the code change, with no way to
separate them.

**Caveat.** Two arms generated minutes apart look paired and may not be. What
disambiguates them is not proximity in time, but field-by-field provenance. Here,
a field *absent* on one side was the only sign that the instrument had changed
midway, and only diffing the two provenances showed it.

**Note.** What this changes in the reading of the ceiling: the 4.86% remains the value under the convention
declared in the artifacts, and the two measured axes remain valid. What falls is the
suggestion that the measured axes exhaust the sensitivity. They do not, and the third,
once measured, is the largest of the three in relative effect on the identity of the
sensitive states, even though the smallest in effect on the count.

**Caveat.** The process lesson, which is bigger than the number. This axis existed in two
artifacts recorded on 2026-08-27 and never read; it was found by mechanical audit of the
script→artifact→claim chain, not by review. Between the discovery and the measurement,
this section spent two days stating *"whether the ceiling moves with it, we do not know"*, an
honest declaration of ignorance, and an unnecessary one: the measurement cost two runs of half an
hour over material that was all on disk. Declaring ignorance is cheaper than
measuring, and that is why it is the path taken by inertia. Before writing that one does not know,
one should ask how much it would cost to know.

## 6. Instrument defects: what an auditor of these numbers needs

This section serves contribution (iv), the executable diagnostic: whoever reproduces the
measurement needs the defects that changed its numbers. The catalog itself is not a declared
contribution (§1). The full catalog has 17 entries and lives in Appendix
E. Here are the eight that changed a number this paper reports, because without them the
reader has no way to audit the numbers. That is the cut criterion, not the interest of
the lesson.

**Note.** The criterion excludes one that would be the most quotable of all: an aggregate `κ` of 0.874
reported alongside a stratification that depends on a different boundary, where the panel
agrees only 0.31–0.53. It does not enter because it does not change any number in this
paper; it changes the analysis stratum of the interventional study, where the split is reported; the
aggregate 0.874 itself is recorded in Appendix C.

| defect | number it changed |
|---|---|
| positive control run on a **reimplemented** pipeline | produced "absurd dose ⇒ zero effect", which became the central retraction. The real pipeline gives **20** events |
| **test of a derivation on a RECONSTRUCTED pool** (the coverage pool is not returned by any exported function) | classified 25 states as alterable against 17 real ones, and only **1 of the 17** fell in the class; 24 violations of the prefix assumption were the symptom. The valid test uses only **recorded** quantities (§5.6) |
| `served_at` with **second** resolution and 6 agents firing within 1–2 s | **46.9%** of briefs share the second; no temporal cut reproduces the state. Under a strict cut the replay **invents** 3 and **misses** 1 event: the outcome comes out **14 instead of 12** (+16.7%) |
| coarse grid | saturation *seemed* to fall exactly at the top of the registered band; with 23 doses it is in `(4.0, 4.4]` |
| per-chunk search telemetry **silent** from 2026-05-19 14:47:04, at a deploy boundary (a 1 h 19 min gap in the rows, then null until the writer was restored on 2026-08-27 22:18Z, commit `32f78109`), **without a `CUT`** — this project's convention for deliberate withdrawal | comparison across surfaces **within a window** is impossible, and went **3.3 months** without anyone noticing |
| **window of one sub-pool applied to a batch of the other** | §4.3.1 said each batch feeds the coverage channel for 7 days and expires. There are **two** sub-pools: per-agent (`sessions/%`, 7 d) and global (`entities/%` + `lessons.md`, **30 d**). The retrodiction batch belonged to the first, the prediction batch to the second. The dated prediction **refuted** the section, which was replaced: the eligible pool is **108 chunks (0.16% of the corpus)** and is **100% exhausted every day** |
| **`brief_log` does not record the channel that served each row** | counting serves of a batch measures the UNION of coverage with the main pool, and the main pool has no age filter. It made a guard flag "age 7.42 served" as a violation of the 7-day window — serves that were never subject to any window. Eligibility excludes but does not attribute; the attribution is the paired replay of the same state with `freshSlots = 2` and `freshSlots = 0` (§4.3.1, `CHANNEL-ATTRIBUTION-2026-08-29.json`) |
| comparison of a **filtered** count with an **unfiltered** one | produced opposite readings: over the 865 curated entities, cumulatively search leads the brief 617 to 245; in the window both instruments share (from 2026-06-04), the common-window artifact reports 245 live curated entities with brief records and 151 with `last_accessed_at` on or after 2026-06-04 (`out/superficie.json`, `janela_comum`). These different record predicates do not establish which surface delivered more distinct entities; the 617 has no preserved field |

The pattern running through all eight, and the transferable finding, is that each one passed
verification and survived. In each, the verification
instrument shared the wrong premise of what it verified. A positive control
run on the reimplemented pipeline confirms the reimplemented pipeline; a census of
dead columns done by `grep` inherits the blindness of `grep`. The defense that worked, in all
eight, was the same: reproduce a published anchor before varying anything.

**Note.** There is also an asymmetry: four of the eight were found because a number
matched too well: saturation exactly at the top of the registered band, an absurd dose
with exactly zero effect.

### 6.1 How much of this paper the verifier actually verifies

A verification discipline that does not measure itself is a statement of intent. `claims_check.py`
recomputes claims against an artifact and fails if they diverge, but until
2026-08-29 nobody had asked *over how many*. Adversarial review asked the question,
and the first measurement (`measurement/censo-de-alegacoes-sem-guarda.py`) showed 19 of the 32 curated numeric
claims with no guard at all (59.4%).

And the artifact of that measurement no longer exists, for the reason this paragraph
describes. `out/CLAIM-COVERAGE-2026-08-29.json` is rewritten on every run of the census:
as of 2026-10-03 it still reads 10 of 32 (31.2%), which is the state after the 2026-08-29 round, not the 19
that the text attributed to it. An earlier version of this sentence cited it as the source of
the 59.4%, and the citation had been false since the second time the script ran. The number 19 has
as its record this paragraph and the round's commit, not an artifact, which is
the defect the section catalogs, committed by the section that catalogs it. Found
by adversarial review (Codex, 2026-08-30); the operational lesson is that an artifact rewritten
in place does not serve as a historical citation: either the name carries the instant, or the claim
cannot point to it.

There were, therefore, two rounds of guards, and the earlier text mentioned only one: the one of
2026-08-29 closed nine (19 → 10) and the one of 2026-08-30 closed the remaining ten
unguarded claims, reaching 0 of 32 (0.0%; this count has no preserved artifact), and strengthened five weakly guarded ones. The
table lists all fifteen; the five that were weakly guarded rather than unguarded are in italics
(`out/CLAIM-COVERAGE-2026-08-29.json`, the state after the 2026-08-29 round, has exactly ten
`SEM_GUARDA`). They came from three distinct origins, and the distinction matters
because only the third was serious:

| origin | claims | remedy |
|---|---|---|
| derivable from numbers already locked | 99.98% · *8.7×* · *brief coverage* · 46,280 · 82.2% | recompute in the guard |
| existing artifact, never read | 0.161% · 12.4 · 4.86% · *36%* · 80% · *32.1%* · *232* | open and compare |
| **artifact that did not exist** | **−0.961 · −0.728 · 0.471** | the script wrote nothing |

The third row only appeared when writing the guard, and it is the finding of this section.
`measurement/robustez-tamanho-exposicao.py` ran from 2026-08-27 to 2026-08-30 without writing any
artifact (no `--out`, no `json.dump`). The three coefficients that support the whole of
§4.2, including the `β` that is the result that *survives* the 15 types, existed
only on `stdout`, were read by a human and transcribed by hand into the text. Changing the input
CSV would change all three and the manuscript would go on asserting the old ones, with
nothing to flag it. It is the exact form of the defect this section describes
(prose asserting a computed result is a cache without invalidation), found in the numbers the paper uses
to defend itself against the strongest objection it received.

**Note.** The gap sat in what §4.2 presents as
the most robust estimator, not in a peripheral number. The degree of protection of a claim bears no relation to
its centrality; if it did, this one would have been the first. `out/SIZE-ROBUSTNESS-2026-08-30.json`
is the first artifact the three have.

This gap had already produced an error, which only appeared because the gap was measured:
the manuscript asserted 583,973 cumulative slots in five places. The artifact says
583,763. Two digits and 210 slots of difference, no artifact with the value in the text,
and nothing to flag it. It was
the most-cited number in the paper, the basis of the capacity thesis, and the least protected. In addition, the field
is called `slots_historicos_ATE_AGORA_serie_viva` and the quantity was growing by about 6,600
per day at the time (the closed week's 46,295 slots / 7 = 6,614, `slots_7d` in
`out/superficie.json`; the series stood at 583,763 on 2026-08-28 09:52Z in the same artifact, and
a reading of 591,323 on 2026-08-30 has no preserved artifact); and the sentence said *"today"*,
which that rate refutes: at about 6,600/day, three weeks later the value would be about
722 thousand. Corrected on 2026-09-21; the instance was in this same paragraph that
states the rule. Citing a live series without fixing the instant is
writing a number that ages into falsehood on its own; for that reason the claim carries the
84.7 days and the artifact's `T_REF`, and the new guard recomputes the derived values (8.7× and
2.43%) instead of only checking that the text did not change.

And recomputing was not enough. The recomputed value was `1,787 / 67,187 = 2.66%`, which
mixes a historical numerator (it includes the 152 deleted later) with a live
denominator, the defect that F-3.2 corrected in the 83.78% and that the rule in §4.1.1 (*"the
cited percentage is over the live corpus"*) prohibits. The guard faithfully recomputed the
wrong calculation. Corrected on 2026-09-21 to `1,635 / 67,187 = 2.43%`, by adversarial
review.

The census of universes did not catch it either. `censo-de-universos-no-paragrafo.py`
exists for this family and has `2,66` in its table, labeled `("cobertura do brief",
"brief")`. It compares the declared universes of adjacent numbers, and a number
has only one label: the mixture that lives inside a single quotient is invisible to
it by construction.

And the occurrence count became part of the guard, because `valor in texto` is
satisfied by any occurrence: three mutations passed the first test because I
changed only the first of several mentions of the same number. The assumed cost is that a
legitimate edit that changes the number of mentions has to update the count on purpose.

### 6.2 Pinning an artifact's identifier does not preserve it: two losses and one mis-scoped search

The eight defects above are instrument defects: a number measured wrongly, a constant with no
referent, a guard that does not bite. This one is of a different nature, and only became visible when
what we took to be the third occurrence appeared: three reports in three days, from three independent
mechanisms. Rechecked on 2026-10-03, the third was not a loss of the pinned artifact (third row):

| artifact | how it was pinned | what happened |
|---|---|---|
| corpus of the ceiling replay (`e20260826T060003Z.db`) | `sha256` of the first MB, published | **rotated** — epoch snapshot, retention deleted it; the same day's daily backup is from a different instant and does not match |
| three *serving* modules (`brief-diversity`, `salience`, `search`) | **commit hash** | a merge rewrote the hashes; recovered on 2026-08-30 and re-pinned by `sha256` of the bytes |
| frozen corpus of the interventional study (`action-archive-20260729T094609Z.tar.gz`) | `sha256`, path and mode `0400` declared | searched on 2026-08-30 by name, size and hash **on the serving machine only**, and reported missing. It is not: on 2026-10-03 it was at its declared path on the other host, with `sha256` equal to the pin (`ba5fcc81…`) and its 3,860-line manifest intact. The **280 adjudicated episodes** (`p2_verdict`, adjudicated 2026-08-15 → 08-21) were never in it (0 of 280 ids among its 5,547 episodes; id list in `_sprint-2026-10-04/A-aging/p2_verdict_ids-280.txt`), and none of them survives in the live archive or in the preserved episode files of the trial |

All three pins were correct; the first two failed in the same way, and the third did not fail. A published `sha256`
identifies an artifact without requiring trust in whoever published it, which is
the property one wants. What it does not do is prevent the artifact from disappearing,
and these two things are easy to confuse because the hash *looks like* an act of preservation.
It is an act of identification.

The third case shows the cost in its pure form, though not in the way we first wrote it.
The panel adjudicated 280 episodes between 2026-08-15 and 08-21. The table kept `sig_primary`,
`severity` and `chunk_id`, and the judged material is gone: 0 of the 280 ids appear in the frozen
July corpus or in the preserved episode files of the trial (checked 2026-10-03). What remains is a
verdict without evidence: verifiable against itself and unrecoverable for any third party.
The frozen corpus itself was never lost. Our search looked at one host and reported "does not exist";
the file was at its declared path on the other host, byte-identical to the pin. That search was a
guard whose predicate lacked the data, the same class this section catalogues. And the `sig()`
function, versioned in a repository rather than pinned by hash, survived as expected: its
`sha256` (`e860357bd9f1fc06…`) matches the frozen one because the file is in git.

The rule that comes out of this, and that holds for any deposit: deposit the blob, not the
hash. If the artifact is too large to deposit, then the reproducibility claim that rests on it
has to say that it is perishable. That is a considerably weaker claim, and it is the true one.

**Note.** None of the three
was found by review. The first two came from a mechanical audit of the script→artifact→claim chain;
the third, from trying to use the corpus and not finding it on the host we searched. A reviewer
reading `CORPUS-FREEZE.md` sees an impeccable document (path, size, hash, file
mode, verification command), and the file is where it says. Our own search still declared it
missing, because it covered one host. No reading distinguishes a valid pin from an orphaned one,
and neither does a search scoped too narrowly; only retrieving the artifact does.

## 7. Threats to validity

- **`n = 1` system.** This is the main threat and has no mitigation within this paper.
  The generalization of the mechanism is deductive (§5), not empirical: it holds for any
  ranker with lexicographic order and a bonus on the subordinate coordinate that serves a prefix
  of that order, and whether other
  systems have this structure is an open question. Partial mitigation: publishing the executable
  diagnostic so that third parties can measure their own system;
- small types (`decision` n=11, `person` n=14, `feedback` n=17) do not support an
  individual reading; they enter only in the correlation test;
- `access_count` is "a top candidate of at least one tracked search sub-query", whoever
  initiated the call and whether or not the chunk was returned (§3.1), with no per-event history, and
  not "exposed at least once": the brief never writes to that column (§2, §4.3.2). Whoever measures
  exposure needs the union with `brief_log`, never this column alone;
- ~~the per-day coverage diversity has a regime break on 2026-08-21–22, still without
  explanation~~ → explained (§4.3.1), and the first explanation we gave was refuted
  by a dated prediction before it reached the deposit (§6). It is not a regime break: the eligible
  pool has 108 chunks and is 100% exhausted per day, so daily diversity measures
  when new material entered within the patterns, not rotation. It becomes a declared limit:
  an outcome built on daily diversity is non-stationary because of its dependence on the
  ingestion calendar, and a window with no new ingestion measures zero by construction;
- in the windows from which this paper's rates and replay results are computed (the closed
  brief week `[2026-08-20, 2026-08-27)`, the census of 2026-08-28, the 350 replay states of
  2026-08-26/27 and the pool measurements of 2026-08-26 to 08-29), the intervention ran in
  shadow mode: the counterfactual is observed and nothing treated was served, so every rate
  here is an opportunity rate, not an effect. The serving-log set comparisons of §4.3.1 extend
  to 2026-09-21 and so span the trial's control and treatment epochs; they are descriptive. From
  2026-09-01 10:25:39Z to 2026-09-21 09:43:05Z the
  separately registered trial did serve treated briefs (11 treatment epochs out of 19 with data;
  `DEVIATIONS-FOR-PAPER.md` §10.29, §10.31). Its results belong to Paper B, not to this paper.

## 8. Related Work

### 8.1 What the agent-memory field measures

The canonical survey (TMLR 2602.06052v4) partitions the metrics in use into three families
(accuracy-based, similarity-based, and LLM-as-judge). Together they cover retrieval,
memory-quality, response-quality and end-to-end task metrics (Recall@K and NDCG@K, Memory
Integrity and False Memory Rate, judge scores, Success Rate and Resolved Rate; survey §7.1, Table 3).
Its metric taxonomy does not include a census of distinct memory items delivered under
production traffic. MemoryArena (2602.16313) and Evo-Memory (2511.20857) are the closest neighbors, and
both compare systems on fixed tasks. Neither measures what the
system delivered to the agent under the traffic it received.

The empty cell matters because a retrieval metric is conditional
on a query having been issued. An item that no query reaches and that no brief includes
has an undefined nDCG, not a low one. That is the population this paper measures, within a
stated scope: 56,288 live chunks (83.78%) are no-record (§3.1).

### 8.2 Exposure in recommendation: where the vocabulary exists

The notion that delivered attention is a finite, allocable resource, distinct from
estimated relevance, is mature in retrieval and recommendation. Singh and Joachims
(KDD '18) formulate exposure allocation as an optimizable constraint; Diaz et al.
(CIKM '20) make expected exposure an evaluation metric, over stochastic rankings.
The *popularity bias* literature measures the correlated phenomenon on the catalog side:
long-tail items receive disproportionately less exposure than their
prevalence (survey by Klimashevskaia et al., UMUAI 2024, covering 123 works).
Chaney et al. (RecSys '18) show that the feedback loop between what is exposed and
what is learned increases homogeneity over time.

Our result is *popularity bias* where "popularity" is the size of the collection
to which the item belongs. Chaney's loop has only a partial analogue here, and the
difference is one of design, not chance: `access_count` enters `salience`, but is
incremented only by search (`search.ts:396`); the brief is declaredly *read-only*
over `chunks`. So serving in the brief does not raise the priority of anything, and the
classic loop, in which exposure reinforces itself, does not close inside the system (§4.3.2). What
exists is a permanent, non-decaying encoding of past tracked search traffic, whoever initiated
it (§3.1). If
the loop closes, it closes through the agent, who sees the item and may search for it again.
We did not measure that.

The work closest to our finding is Bower et al. (2022), which shows that exposure
inequality originates before the ordering, in the candidate set,
and that randomizing the next step can even worsen it. We agree on the location and
diverge on the mechanism:

> That literature presupposes that exposure responds to the score being controlled, which is
> what licenses redistributing exposure by making the ranking stochastic. Here exposure stays
> weakly monotone in the score (§4.4: monotone in each of the 350 states) but responds only
> within ties of the dominant coordinate: the coverage slots are ordered by a lexicographic
> comparator, the score is the subordinate coordinate, and an additive bonus on the score acts
> only within those ties (§5.2). A lever built on the score does not move what the dominant coordinate has already decided.
> This follows from the algebra of the comparator, not from the bonus's magnitude.

Hence the bridge is not merely terminological. The vocabulary of surface capacity matters
for agent memory, and the standard redistribution technique does not transfer without
first checking on which coordinate the ordering decides. That check is the
diagnosis we publish.

**Two scope caveats.** The analogy is one of mechanism, not of application: there the consumer
is a human user with decreasing position and attention; here it is an agent that
receives 10 items at once, and there is no position model. And "exposure fairness" is a
normative question that we do not raise: the argument here is one of utility and
diagnosis, not of equity among items.

### 8.3 Pre-registration in systems CS

Prospective registration of hypothesis, outcome, and analysis is routine in clinical trials and
in parts of psychology; in systems CS, it is not. The survey of 218 papers from §8.1 has
zero occurrences of any spelling of *pre-registration*; measured together, it also has
zero of `randomized`/`randomised` and of `ablation` (§1). The absence is of the entire
methodological family, not of one term.

This paper does not claim to be that precedent. The
prospective registration we deposited (OSF `yf7d2`) is for another study: a randomized
crossover on the behavior of the agent. Corrected on 2026-09-21: an
earlier version of this sentence said it *"did not run"*. It did: from 2026-09-01 10:25:39Z
until the dose was switched off on 2026-09-21 09:43:05Z (the window closed at the 2026-09-20
epoch; 20 epochs realized, 19 with data). Its results are Paper B, not this one.
What remains true, and what the sentence meant to say, is that this manuscript is not
that study: what it reports is descriptive and was not pre-registered.

**Correction.** The claim remained false for three weeks in a paragraph whose function is to correct the
public record. A reviewer who opened OSF `yf7d2`, saw the dates, and cross-checked them against this
line would disqualify the paper's entire self-audit thesis with a single
counterfactual. It was found by adversarial review, not by the sweep that item 5 of the
list *Open items* (at the end of this manuscript) declares open. That is evidence that declaring a sweep
open is not the same as performing it.

Appendix A records the deviations from that registration anyway, and the reason is narrow:
as long as the public deposit exists asserting things that the measurement contradicts (including
two that understate the design itself), leaving them standing is choosing to let the error survive.
This is an obligation of correction, not a methodological credential.

What the absence of experimental vocabulary in the survey supports is more modest: there is no
established convention on what to declare before intervening in a live memory
system, and we found that out the expensive way.

**Provenance of this section.** MemoryArena and Evo-Memory were read in full
on 2026-08-15 (`RELATED-WORK.md` §4 and §4.1); the survey, in full on 2026-08-13, with the
counts recomputed on 2026-08-28 over the PDF pinned by sha256. The recommendation papers of §8.2 were read in abstract and metadata, not in full text. I declare this because the
claim I make about them is about the monotonicity
presupposition, and full text could refine that claim.

## 9. Discussion

Three claims, and none beyond them.

**First:** this system's non-exposure is the result of policy, not of capacity.
This is the claim that the measurement inverted relative to the hypothesis we started with. What
supports it is one line of arithmetic plus one mechanism, not a statistical test:
583,763 slots (the live series frozen at 2026-08-28 09:52:08Z, the `ate` field of
`out/superficie.json`, §6.1) against 67,187 chunks, capacity to show everything 8.7 times over, while
the brief served 1,635 distinct live chunks (1,787 counting the 152 later deleted; §4.1). There is no physical constraint to remove here; there is an ordering
that revisits, and §5 shows by which path.

**Note.** This section used to support the same conclusion through the `slots/distinct` ratio (printed then as 325; the locked numbers give
583,763/1,787 ≈ 327), withdrawn for the reason given in Appendix F-1.

**Caveat.** The correct objection to this is that slots are not fungible: the surface delivers 10
per session, and nothing guarantees that a session tolerates more than 10. That is true, and the claim does not
depend on it. Showing ten different items per session would never violate the limit of
ten; what is missing is rotation across sessions (§4.1.1), not session size. This changes
what can be asked for: while the surface looks small, "expose more" is an
impossible request; once the slack is measured, it is a request about design.

**Caveat.** Nor does it follow that the policy is wrong. A 10-item surface has to
concentrate; uniform serving is used here only as a capacity reference, and its effect on agent
utility was not measured. What follows is that the
boundary between "what the agent sees" and "what exists" was chosen, almost always without
anyone choosing it explicitly: `freshSlots = 2` was a configuration default with no
override in the measured window (verified on 2026-08-27, `SUPERFICIE-2026-08-27.md`), and the two patterns of `GLOBAL_FRESH_PATTERNS`, together with the importance floor and the
30-day window, carve out 0.16% of the corpus in a
way that no design document anticipated.

**Second:** both channels freeze, and the asymmetry between them is the finding. The
coverage channel (2 of the 10 slots) fails by population: 108 eligible in a corpus of 67,187,
with zero never-served remaining and 12.4 slots per candidate on a closed day (measured
inside the defective-ingestion period of §4.3.1), and by responding to the score only within
`last_served` ties, up to a ceiling whose existence is derivable from the code before any experiment
and whose value, 4.86% under the conventions in force on the 2026-08-26 corpus
(same regime, empty never-served stratum), was measured by replay. The main pool (the other 8) fails
for the opposite reason: there the score is the dominant coordinate, and three of its four terms
do not decay. The access component is monotone in a counter that only goes up, so
the three constant chunks hold ranks 1, 3 and 4 by salience only through tracked search traffic from months ago, whoever initiated it (§3.1; measured counterfactual, §4.3.2: last accessed 42, 90 and
30 days before the window closed on 2026-08-28, in chunks that won 4,632 of 4,632 briefs). The high-pain pin, which selects them in phase 0 of every brief, before the quota pass, protects what that score placed there and is measured as necessary for main-set membership for one of the three (§4.3.2).

The main pool would respond to a score adjustment, and nobody adjusts it. The coverage channel,
designed to compensate for the main pool, has a daily reach bounded by its eligible population (path patterns, the
importance/pain floor and age windows), which it exhausted in the measured regime, and within a brief it responds to score only within `last_served` ties
(17/350 here) and then saturates. This combination, not capacity, produces the 2.43%
(1,635/67,187, live).

**Caveat.** This differs from the classic recommendation feedback loop: here
exposure in the brief does not reinforce itself, since `access_count` is only incremented by search
and the brief is declaredly read-only over it. What exists is a
permanent, non-decaying encoding of past traffic, not a loop.

We state the design consequence in full: we designed an
intervention whose ceiling was derivable from the code before anything was served.
Corrected on 2026-09-21: the sentence ended with *"and, at the close of this manuscript,
nothing yet has been"*, which stopped being true on 2026-09-01. The trial produced 19 epochs
with serving data, 11 of them in a treatment arm. The point survives the correction: the ceiling
was derivable from the code before the intervention ran. Whether the served dose changed anything
is Paper B's question, and its answer is not a measurement of this ceiling. This paper does not
claim that the trial left the ceiling unchanged. Whoever is
going to intervene on a ranker should read the comparator first and ask *on which coordinate
my lever acts*; it costs an afternoon and saves an experimental round.

**Third:** none of this is visible through the metrics the field uses. This is the only
claim that goes beyond this system, because it concerns the instrument, not the
result. nDCG and recall are conditional on a query having been issued; an item that
no query reaches and no brief includes has an undefined score, not a low one.
Measuring the delivery surface requires the system in operation and a per-item record of what
was served, and this system almost lacked that record: 16 telemetry columns with no writer
during the measurement window (census of 2026-08-27), at six distinct instants, among them
the one that recorded which chunks search returned. Its writer was restored on
2026-08-27 (commit `32f78109`), too late for this window (§6).

**What we do not claim.** That the field optimizes the wrong coordinate: it is one system, and the
only generalization we make is deductive. For any ranker with lexicographic order
and a bonus on the subordinate coordinate that serves a prefix of that order, the ceiling
exists. How many systems have that shape is an
open question, and it is to answer it that the diagnosis is published. That the 83.78% without an
exposure record is *bad*: part of the corpus is log, and a log does not need to be read to be
useful. The number establishes the scale of the population that no retrieval metric
reaches, not a harm. And that exposure changes the agent's behavior: we did not measure it.

## Appendix A — Relation to the pre-registration

There is a public pre-registration (OSF `yf7d2`, Zenodo `10.5281/zenodo.22110203`) and this paper
is not the study it registers. The registration covers an interventional study (designating
chunks, serving a dose, estimating an effect), which went `active` on 2026-09-01 at 10:25:39Z
and whose dose was switched off on 2026-09-21 at 09:43:05Z, closing the window at the
`2026-09-20` epoch. Of 234 registered epochs, 20 were realized and 19 carry serving data (16 whole
and 3 partial under the analysis spec's clock ruler; `09-02` is empty); 11 were in treatment arms
and 8 in control (`DEVIATIONS-FOR-PAPER.md` §10.29, §10.31). When the first version of this
manuscript was closed, the study had not yet begun, and the text
below was written under that condition; it no longer holds. The interventional results
are not here. They are Paper B (`MANUSCRIPT-B.md`, a draft opened on 2026-09-21 and not yet
deposited), whose underlying records are `DEVIATIONS-FOR-PAPER.md` §10.29–§10.34, in the version
deposited with this text; the v1.0 deposit (Appendix D) predates them, and its
`DEVIATIONS-FOR-PAPER.md` stops at §9.

**Caveat.** Nothing this paper measures depends on the trial having run: the surface census,
the mechanism and the 350-state replay of the ceiling use pre-treatment data (states before
2026-09-01). The longitudinal serving-log checks of §4.3.1 (spanning 2026-08-21 to 2026-09-21;
the same 33 main and 108 coverage ids in the agent briefs on every measurable day from
2026-08-24 to 2026-09-19)
extend into the trial, which served treated briefs in 11
epochs; they are descriptive observations across control and treatment epochs, not
pre-treatment measurement. The only thing that changes with the close of the trial is that the sentence "had
not begun" can no longer be read in the present tense.

What this paper reports are the measurements made while that study was being built:
the surface, the carousel, the mechanism and its ceiling. They were not pre-registered,
so they are exploratory and descriptive,
not confirmatory.

**Caveat.** Three things we measured here contradict the registration, and they are stated here because the
registration is public and someone will cross-check the two:

| the registration states | what was measured | direction |
|---|---|---|
| `Δ_cut = 0.043` is *"the measured salience spread at the brief cut"* | **there is no cut**: the code applies no threshold. The comparator is lexicographic and `salience` only breaks ties between identical `last_served` values (§5.1) | overstates: the registration promises more |
| the `{2 · 4 · 7.5}` band is among *"what does not move, and could not"* | **it moves**: 11 / 15 / 17 states out of 350, monotonic, with saturation in `(4.0, 4.4]` (§5.4) | understates: the registration promises **less** |
| *(v1.12 §5)* the designation is an **open** defect | **closed** on 2026-08-26: the seed declaration was pushed at 20:07:24Z, 1,056 s before the drand round it names was issued (20:25:00Z), and the designation was derived from that round (Appendix B) | understates: the registration promises **less** |

The two understating rows are the ones that matter, because nobody corrects on their own an error that
favors them: the registration states that a parameter has no effect when it does, and that a
defect is open when it has been closed.

**Caveat.** And the band row changed status because of an instrument defect of ours, not because of new data: the
positive control that produced the *"does not move"* was running on a reimplemented
pool. That is a matter for §5.6, not a footnote.

The full list of deviations lives in `DEVIATIONS-FOR-PAPER.md` and belongs to the
interventional paper. One that affects only the interventional study, the migration of the
analysis stratum from `S2` to `≥ S1` by panel agreement, is not in that log; it is reported in
Paper B's list of deviations (`MANUSCRIPT-B.md`).

## Appendix B — Designation chain

Draw with a declared seed: drand quicknet round 31657512 (issued at 20:25:00Z),
declaration pushed at 20:07:24Z: 1,056 s of precedence, with the round returning
HTTP 425 at the time of writing. An independent reviewer re-derived the designated set
using only the public beacon and the deposited CSV.

## Appendix C — The panel, and why it is not here

The population of 55 chunks in 19 groups comes from `p2_verdict`, the product of a 3-family severity
adjudication panel. The panel, its agreement per boundary and the rate parameter it estimates belong to the
interventional study and are reported in Paper B (`MANUSCRIPT-B.md`, Appendix A, relation to the pre-registration),
which carries the split agreement: κ 0.87–0.93 at `≥ S1` against 0.31–0.53 at the `≥ S2`
boundary. The aggregate `κ` of 0.874 that hid this split is not in Paper B nor in
`DEVIATIONS-FOR-PAPER.md`; it is recorded here.

For what this paper reports, the panel enters in two ways: it fixed a population, and its
severity labels scale the dose. The 19 designated items are a fixed and publicly re-derivable
set (Appendix B); both numbers in §5 were measured with the recorded labels held fixed (see the
caveat in §5.1).

## Appendix D — Artifacts

Scripts are in `measurement/`, except `claims_check.py`, which is at the root of
`paper2-interventional/`, and the two sprint scripts whose full paths the table gives. Artifacts are
in `out/` (including the three dated 2026-10-05), in `measurement/`
(`CHANNEL-ATTRIBUTION-2026-08-29.json`), at the root of `paper2-interventional/` (`CEILING-*`,
`TIEBREAK-*`, `POOL-ELEGIVEL-2026-08-28.json`, `BATCH-CYCLE-*`, `PREDICTION-*`), and, for the
ones produced on 2026-10-04, in `_sprint-2026-10-04/` (`POOL-ELEGIVEL-2026-08-26-to-29.json`;
`A-recon/RECON-52-e-sondas-2026-10-04.json`; `A-recon/ORGANICO-e-hashes-2026-10-04.txt`;
`A-recon-evidence/COMPARABILITY-IDENTITY-5.7.2.json`;
`A-filters-disaggregation/out-ord0826.json`; `A-filters-disaggregation/diag-out.txt`;
`A-filters-disaggregation/observed-main-from-log.json`;
`A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json`;
`A-aging/WARNING-DENSITY-recomputed-2026-10-03.json`; `A-aging/p2_verdict_ids-280.txt`):

| what | script | artifact |
|---|---|---|
| exposure surface | `superficie-de-exposicao.py` | `out/superficie.json` |
| replay + dose + threshold + gaps | `replay-oportunidade.mjs` · `replay-resumo.py` | `out/c-350-v3.json` · `out/dose-350-v3.json` · `out/limiar-17.json` · `out/gaps.json` |
| ceiling granularity (§5.7) | `replay-oportunidade.mjs --granularidade` · `granularidade-do-teto.py` | `out/gran-{seg,min,hora,dia}.json` · `out/gran3-{seg,min,hora}.json` · `CEILING-GRANULARITY-2026-08-28.json` |
| exposure to arbitrary tie-breaking on the comparator's key (§5.7.1) | `sprint-empates-salience-producao.mjs` (`--shared-plus 1` for the second file) | `out/TIEBREAK-EXPOSURE-PROD-2026-10-05.json` · `out/TIEBREAK-EXPOSURE-PROD-SHARED-2026-10-05.json` (what each tie group shares) |
| the same on the SQL pre-rank expression (superseded as the §5.7.1 table; cited for comparison) | `empates-por-granularidade.py` | `TIEBREAK-EXPOSURE-2026-08-29.json` |
| ceiling sensitivity to the designation (§5.7.1) | `sensibilidade-da-designacao.py` | `out/sens-*.json` · `CEILING-DESIGNATION-SENSITIVITY-2026-08-28.json` |
| eligible pool of the coverage channel (§4.3.1) | `pool-elegivel.py` · `sprint-pool-elegivel-multidia.py` | `POOL-ELEGIVEL-2026-08-28.json` · `POOL-ELEGIVEL-2026-08-26-to-29.json` |
| differential attribution by channel (§4.3.1) | `replay-oportunidade.mjs --modo canal` | `CHANNEL-ATTRIBUTION-2026-08-29.json` |
| served coverage set per day, from the serving log (§4.3.1) | `_sprint-2026-10-04/A-rc2/coverage-set-from-log.py` | `A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json` |
| batch cycle, and the refuted prediction (§4.3.1, §6) | `ciclo-do-lote.py` · `regime-cobertura.py` | `BATCH-CYCLE-2026-08-28.json` · `BATCH-CYCLE-2026-08-29.json` · `PREDICTION-2026-08-29.md` |
| exposure to the resolution defect | `irmaos-no-segundo.py` | — |
| monitoring triggers (retired 2026-09-21; kept as record) | `gatilho-saturacao.sh` · `gatilho-composicao.mjs` | `measurement/implantacao/` |
| probe-exclusion axis of the ceiling (§5.7.2) | `replay-oportunidade.mjs --excluir-briefs` | `out/CEILING-PROBE-EXCLUSION-{none,probes}-2026-08-30.json` · `out/ancora-sondas.json` · `out/ancora-sem-exclusao.json` |
| identity-level comparability control (§5.7.2) | `sprint-comparabilidade-identidade-572.py` | `COMPARABILITY-IDENTITY-5.7.2.json` |
| importance-floor composition, cohort exposure (§4.1) | `composicao-do-piso.py` · `exposicao-por-coorte.py` | `out/FLOOR-COMPOSITION-2026-08-29.json` · `out/EXPOSURE-BY-COHORT-2026-08-29.json` |
| size axis (§4.2, §6.1) | `lacuna-no-eixo-de-tamanho.py` · `robustez-tamanho-exposicao.py --dados out/tipos-2026-08-28.csv` · `fig1-capacidade.py` | `out/tipos-2026-08-28.csv` (input) · `out/SIZE-AXIS-GAP-2026-08-29.json` · `out/SIZE-ROBUSTNESS-2026-08-30.json` · `out/SIZE-EXPOSURE-15-2026-08-29.json`; the 13-type Spearman ρ, the three partials, `r(log n, age)` and the 9-type r/ρ of §4.2 are printed by the script, not written to the JSON |
| top-of-pool counterfactual, production salience (§4.3.2) | `sprint-contrafactual-salience-producao.mjs` | `out/SALIENCE-COUNTERFACTUAL-PROD-2026-10-05.json` |
| top-of-pool counterfactual, first version (superseded: not the production function; kept as the anchor) | `contrafactual-do-topo.py` | `out/TOP-COUNTERFACTUAL-2026-08-29.json` |
| bonus at the largest threshold against the largest adjacent gap (§4.4, §5.4) | `sprint-bonus-vs-passo.py` | `out/BONUS-VS-STEP-2026-10-05.json` |
| the 52 deleted chunks, the five probes and the full-pool counterfactual (§4.3, §4.3.1, §4.3.2) | `sprint-recon-52-e-sondas.py` | `A-recon/RECON-52-e-sondas-2026-10-04.json` · `A-recon/ORGANICO-e-hashes-2026-10-04.txt` |
| main-pool filter disaggregation, and the served main set from the log (§4.3.1) | `sprint-desagrega-filtros-pool-principal.py` (`--log-only` for the log census) | `A-filters-disaggregation/out-ord0826.json` · `A-filters-disaggregation/observed-main-from-log.json` · `A-filters-disaggregation/diag-out.txt` (the residual mismatch of 2026-08-22, produced by `_sprint-2026-10-04/A-filters-disaggregation/diag-residual-mismatch.py`; the file also holds a 2026-09-08 run and the 2026-08-28 control) |
| warning density recomputed on the 2,058-line text (App. F) | `densidade-de-avisos.py` | `A-aging/WARNING-DENSITY-recomputed-2026-10-03.json` |
| ids of the 280 adjudicated episodes (§6.2) | — | `A-aging/p2_verdict_ids-280.txt` |
| verifier coverage and warning density (§6.1, App. F) | `claims_check.py` · `censo-de-alegacoes-sem-guarda.py` · `censo-de-universos-no-paragrafo.py` · `densidade-de-avisos.py` | `out/CLAIM-COVERAGE-2026-08-29.json` · `out/WARNING-DENSITY-2026-08-30.json` |
| survey count (§1) | `survey-string-count.py` | — |
| figures 0–3 | `fig0-arquitetura.py` · `fig1-capacidade.py` · `fig2-concentracao.py` · `fig3-dose-resposta.py` | `out/fig{0..3}-*.svg` |
| strict-cut field replay (§3.3) | `replay-resumo.py --campo-estrito` | `out/c-350.json` |
| deviations from the registration, and the records behind the interventional results (Paper B, not yet deposited) | — | `DEVIATIONS-FOR-PAPER.md` |
| source notes the text cites | — | `SUPERFICIE-2026-08-27.md` · `REPLAY-OPORTUNIDADE-2026-08-27.md` · `REMEDIATION-2026-08-27.md` · `PROTOCOL-CALIBRATION-2026-08-27.md` · `CORPUS-FREEZE.md` · `RELATED-WORK.md` · `REVISAO-ADVERSARIAL-2026-09-21.md` |

**Deposit.** Zenodo, concept DOI `10.5281/zenodo.22181414` (it resolves to the latest
version). Version 1.0 (`10.5281/zenodo.22181415`, published 2026-08-30T21:39:24Z, in Portuguese)
holds an earlier text of this manuscript (a 126,564-byte `MANUSCRIPT.md`, plus 12 supporting
files) and an earlier `DEVIATIONS-FOR-PAPER.md` that stops at §9. It does not contain the
§10.29–§10.34 cited in Appendix A, the 2026-09-21 corrections, this English translation, nor the
consolidated artifacts of §4.3.1, §5.7 and §5.7.1 listed above (10 of the paths this table
listed before 2026-10-04 are absent from it; `_sprint-2026-10-04/A-recon-5.7.2-appD.md`). The
version that matches this text is the next one (v1.1) under the same concept DOI.
Its version DOI is `10.5281/zenodo.23163119`, reserved before deposit; the record is published
with this text. The pre-registration of the interventional study is a separate record
(`10.5281/zenodo.22110203`, v1.12, still the latest version of that record as of 2026-10-03).

## Appendix E — Full catalog of instrument defects

The eight of §6 plus the nine below. The separation is by consequence, not by
importance: these did not change any number reported in this paper. That does not make them
less transferable, and three of them are the lessons I would expect to be the most useful
to third parties.

| defect | measured consequence |
|---|---|
| database clock inside the eligibility filter, even though the function receives the instant as an argument | the brief is not a pure function of (corpus, state, `nowMs`); a naive replay measures another population |
| the sorter **discards** the key that ordered the pool | grouping by it gives **one** group, silently |
| monitoring trigger calibrated on **adjacent** gap | watches a quantity that does not bound the mechanism: stays **green while saturating** |
| **attributing the death of an instrument to a commit, without checking the timestamp** | I published that `7fdaab4f` erased it; the commit is from **2026-05-20 01:03 UTC** and the writes stopped **ten hours earlier**. It removed code that was already mute. A diff that *explains* the effect is not proof that it *caused* it |
| **census of "columns without a writer" by grep, by non-null, or by distinct>1** | the three give different answers and all are wrong: grep misses `UPDATE` and dynamic SQL (−3 columns), `DEFAULT` produces 11 false live ones, and pre-death history inflates the distinct counts (`reranker_latency_ms`: **394**, all earlier). The valid census is **distinct in a later window**, cross-checked with the literal `INSERT` list: **16** columns, at **six** distinct instants over 10 days — and in one of them a `CUT` exists, so it is a **withdrawal**, not a regression |
| field without a writer used as an **origin signature** | `requesting_agent` null was treated by me as proof that the telemetry measured the cron; it is null for everyone since 2026-05-18. The valid test is the **cron minute** (94.8%) |
| live series cited as a snapshot | an `n` changed within minutes and the assertion caught it |
| value **typed** inside the verification instrument itself | `w_min` maximum was pinned at `7.5` in the script and aged into false when the fine grid gave `4.4`; it is now a required argument coming from the dose artifact |
| **"the problem is the dissenting panelist"** — which here was false | `xai` is almost a superset of the others (1 of 16 and 1 of 13 outside): a threshold shift, correctable by normalization. The irreducible disagreement is between the **two families of similar severity** (16 and 13 severe, intersection **5**), which disagree about **which** episodes. Blaming the outlier would have "fixed" the wrong family |

---

## Appendix F — Correction history

This appendix exists because of an adversarial-review finding about the form of the
document, not about a number: the narrative of each correction was in the body,
interrupting the argument to report the diff. Measured before touching anything with
`measurement/densidade-de-avisos.py`: 87 markers distributed over 77 of the 288 paragraphs,
26.7% marked, with retraction being the largest category of repetition. That pre-cleanup output
was not preserved: `out/WARNING-DENSITY-2026-08-30.json` was overwritten by the post-cleanup run
(112 markers; 102 of 344 paragraphs, 29.7%; body 91 of 297, 30.6%), so the 87 / 77 / 288 /
26.7% have no artifact. Caveat. The two units are distinct and the earlier wording
juxtaposed them (*"87 markers in 288 paragraphs — 26.7%"*), which gives 30.2% if read as a
ratio. The number comparable to the one below is that of marked paragraphs.

**Correction.** The cleanup was partial, and the number after the change has to be here, otherwise this
appendix claims an effect it does not demonstrate. In the body (before the appendices, which is what
a reviewer reads first), 91 of 297 paragraphs were marked (30.6%) on 2026-08-30, on the
1,914-line version (`out/WARNING-DENSITY-2026-08-30.json`). The 2026-09-21 corrections added
marked paragraphs: recomputed on 2026-10-03 with the same script over the 2,058-line text
(`_sprint-2026-10-04/A-aging/WARNING-DENSITY-recomputed-2026-10-03.json`), the body has
100 of 307 marked (32.6%), and the whole document 119 of 363 (32.8%), above the 26.7%
measured before the cleanup. (Both counts are of the Portuguese text; the English translation
needs its own measurement.) The
aggregate count is no use for judging: moving material to an appendix does not change the total, and the
appendix brings warnings of its own.

**Caveat.** And the aggregate hides what decides the reading: the warnings are concentrated. Measured on
2026-08-30, §4.2 had 12 markers in 21 paragraphs and §4.1.1 had 5 in 8, while all of
§5 stayed between 8% and 17% (per-section counts, not preserved; the artifact holds totals only). A reader who learns to skip the caveat marker learns it in §4.2, and that is
where the retractions that change what the result means are. The intervention of 2026-08-30 was therefore
surgical and not global, on two fronts: (i) the retractions of §4.1, §4.2 and §5.7.2 came
to F-3, leaving a cross-reference; (ii) three paragraphs that are the
result (the unusable standard error, the confounder that prevents the strong conclusion, the
two properties of the corpus composition) lost the marker without losing a word.

**Caveat.** What remains undecided is the third kind: the warnings of *provenance* and of
*scope*, which `measurement/densidade-de-avisos.py` promises in its own header to classify and
does not classify; the script counts repetition, which is what it measures without
judgment. As long as the classification is manual, the remaining reduction is editorial.

The material serves the executable diagnostic (contribution (iv)), and so was not discarded.
But it belongs here, and in the body only the corrected state remains, with a cross-reference where the
reader needs to know *why* the text is the way it is.

**Caveat.** What did not come here: validity conditions and scope limits. Those
qualify the claim at the point where it is made, and moving them would repeat the error that
Figure 1 itself taught: a caveat displaced from the point of reading protects no one.

### F-1 — The `slots / distinct` ratio, withdrawn as a test

**Caveat.** An earlier version of this section carried here a table of "opposing predictions"
(`slots/distinct` ratio ≈ 1 under a capacity bottleneck versus ≫ 1 under a policy bottleneck,
with 325 printed, though the locked numbers give 583,763/1,787 ≈ 327), presented as the test that separated the two hypotheses. It was
withdrawn, for the reasons below. First, the "≈ 1" prediction is not
derived from the capacity hypothesis: it is the hypothesis rewritten in the unit of the ratio, so
that observing ≫ 1 *is* observing slack (a measurement with two labeled regions, not a test with an error
rate). Second, the hypothesis it overturned was already dead by the arithmetic above,
while the hypothesis a defender would sustain (demand per session above 10) is
the one we declare out of scope. Third, and decisive: any concentrating policy
produces ≫ 1, including a correct one. In a corpus with thousands of session fragments and
3,231 chunks of type `daily`, a ratio near 1 would mean serving obsolete digests;
it would be the *worse* policy. The ratio measured concentration, and the inference to *defect* came
for free.

**Caveat.** An earlier version of this section sustained the same conclusion through the
`slots / distinct` ratio (325 as printed then; ≈ 327 with the locked numbers), presented as a
test that separated capacity from policy.
§4.1.1 withdraws that argument and the withdrawal holds here too: any
concentrating policy produces a ratio ≫ 1, including a correct one, so that the ratio measured
concentration and the inference to *defect* came for free.

### F-2 — Where else the correction did not reach

Each of these was found by adversarial review after the corresponding correction
had already been applied at another point in the text. That is the pattern of this class:
correcting where the defect was found does not correct it where it also is.

| correction applied | where it did not reach | who found it |
|---|---|---|
| the importance floor belongs to the channel, but passing the importance floor ≠ being eligible | the channel applies **three** conditions; the importance floor alone gives 13,388 and the three give **108** | DeepSeek |
| the importance floor belongs to the coverage channel, not to the system | the phrase "that the system marked as relevant", twenty lines below, in the same section | GLM |
| the 13-type Pearson is fragile to the filter | the partials (`−0.709`, `r=−0.843`) that are compared against it | GLM |
| brief ≠ search | Contributions (i), abstract, §4.2, §8.2 | Grok |
| `583,973` → `583,763` | none — the value was in five places and all were corrected, but no guard existed | Codex |
| the equal distribution is impossible "because only 201 fit" | **46,295 fit** — the measured value was treated as a ceiling, which makes the curve inevitable by construction | internal |
| the coverage channel window is 7 days | there are **two** sub-pools, 7 and 30 days; the window of one was applied to the batch of the other | registered prediction |
| "fossil" → "determined" (tone neutralization) | the swap **hardened** the claim: "determined" is causally stronger than the metaphor, and demanded a counterfactual that did not exist | DeepSeek |
| the `w = 2` column labeled **`(served)`** | the defense — "means the dose in force in the *shadow*" — lived in the paragraph **above** the table, and nobody reads a table together with the previous paragraph | DeepSeek |
| "Nobody measures what the agent actually receives" | a universal over the entire literature sustained by **one** vocabulary census of a survey of 218 papers | DeepSeek |
| "the **top** of the brief is determined by traffic" | the counterfactual measures **three** chunks; "the top" generalizes to the ten positions | DeepSeek |
| the 83.78% attributed to a system decision | **9,755 of the 10,899** records are search-counter records, not brief deliveries (the counter marks tracked-search candidacy, not who initiated the call; §3.1, rc6); the caveat existed, but behind a caveat marker in the middle of the paragraph | DeepSeek |

### F-3 — Six retractions that lived in the middle of the result

These six were inside §4.1, §4.2 and §5.7.2, each interrupting the sentence that
carried the finding to report what an earlier version of that same sentence said. The
outside reader never saw the earlier version; for them the paragraph alternated between a
result and the erratum of a document that does not exist. The corrected state stayed in the body,
with a cross-reference; the narrative of the correction is this.

**F-3.1 · §5.7.2 — "not measurable" conceded more ignorance than the facts required.**
The section stated for two days that the third axis of the ceiling was not measurable. There are two
distinct things: the *level* of the ceiling under probe exclusion is not recoverable (the corpus
`e20260826T060003Z.db` was an epoch snapshot and was rotated), but the *sensitivity*
is (the log of the 350 states is `.ndjson` and survived).

**F-3.2 · §4.1 — the table closed over two universes.** The earlier version listed the historical
union next to the live complement; whoever subtracted `67,187 − 11,051` got
56,136 instead of 56,288. Each number was right; the table was not. The row for the 152 chunks
served-and-then-deleted is what makes the bridge, and it is now explicit.

**F-3.3 · §4.1 — "verbatim from `brief.ts:642`" for values that are in another file.** The
*form* of the predicate is there; the *values* `0.7 / 0.7` are in `brief-diversity.ts:59-60`
and are defaults overridable by environment variable. Presenting runtime configuration as a
code constant is what makes a correct number age into a wrong one without
warning: the same class that §6 catalogs.

**F-3.4 · §4.1 — the mean length was that of another population.** The sentence names the
8,928 `distilled` chunks that pass the importance floor, and the earlier version cited 205 characters, which is the mean of
all 14,456 `distilled` in the corpus, not that of the 8,928. Right number,
wrong population, from an *ad hoc* query that left no artifact. The correct value is 232, and it only
appeared on recomputing: it survived three reviews because none of them could
recompute it.

**F-3.5 · §4.2 — "the test separated curation from size".** It does not, and nothing in the section
does: there is no variable in the corpus that measures curation. What the tests separate is
*filter artifact* from *signal*. The two explanations remain confounded by
construction, and the text and the title now say so.

**F-3.6 · §4.2 — orphan partials of the number the section itself had withdrawn.** The
partials (`−0.709`, `r = −0.843`) appeared without saying over which set they were
computed, immediately after the text demoted `−0.728` for fragility to the
filter. They are the 13 filtered types, and against the Pearson of the 15 (`−0.334`) "almost unchanged"
would be double. Found by GLM (see F-2).

### F-4 — 2026-10-04: a verified adversarial review of v1.1

Two voices delivered over v1.1 (DeepSeek and Kimi; three others did not deliver and are not
counted). Of the 28 distinct findings, 23 were confirmed against the text and the cited
artifacts (`_sprint-2026-10-04/REVIEW-A-2026-10-04.md`) and are applied here. What changed:

- §9 still said that "the top of the brief is determined" by old traffic after §4.3.2 had
  scoped the claim to three chunks; it now says the positions of those three.
- §2 said §4.3.1 shows five days with no eligible candidate. §4.3.1 shows 108 eligible on every
  measured day; the five days of §1 are days without new items.
- The Abstract, Contributions (ii), the §4.3.2 table and §9 now carry the qualifier that the
  108-chunk pool was measured during defective session ingestion; "there is never" became "on
  every measured day there was no".
- §9: the code yields the existence of the ceiling; its value, 4.86%, was measured by replay.
- §1 and §4.3.1: "the same 33 on every measurable day from 2026-08-21 to 2026-09-21" held for
  the count, not the set. The set is identical from 2026-08-24 to 2026-09-19, 2026-08-23 has
  34, and the month's 37 is now reconciled (33 + 285042 + three ids of 2026-09-21).
- §4.3.1: the coverage set served in the agent briefs stayed the same 108 ids through 2026-09-19 although 285
  per-agent chunks were eligible after the repair; the text now says so, and that the reason is
  not established. The computation, first done by hand during the review, is preserved
  (`A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json`).
- Abstract and §4.1.1 set the brief's historical 1,787 beside live counts; they now give 1,635
  live (1,787 historical). The §4.1 table labelled the search count 9,755 historical; it is live.
- §4.3 attributed *"always with 10 items"* to the current §2, which no longer says it.
- §5.7.2 carried a dangling cross-reference (↩ H-x); removed.
- §6.1: "~7,500 per day" had no source. The rate is now 6,614/day (46,295 slots / 7, the closed
  week), and the three-week extrapolation goes from ~750 thousand to about 722 thousand. The
  591,323 of 2026-08-30 is marked as having no artifact.
- §6.1: "those ten" introduced a table of fifteen values; ten were unguarded and five weakly
  guarded, and the five are now marked.
- §1: `memory` = 1,169 had no generating path in `survey-string-count.py`; replaced by 1,208,
  the count its positive control computes over the whole text.
- §5.6: "6 probes" against 5 in every preserved probe list; the first run was not preserved, and
  its count is now declared uncheckable.
- §5.5: "governed by capacity" contradicted §4.3.1; now "by eligibility".
- §4.2: "`lesson` is at 100% because it has 53 rows" was causal in a section that declares size
  and curation confounded; now descriptive. "8 are above 32.5%" became 7 above and 1 at 32.5%.
- The status block and §3.2 rule 2 stated the artifact rule as absolute; they now name the
  numbers the text itself flags as having no artifact.
- §4.3.1: "99.95% admitted to the ranking" now says what admitted means (no eligibility
  predicate: all 67,187 enter the pre-rank), and "surfaces" became "channels".
- §4.3.2: an `age` column (125 d for all three chunks) was never defined and no artifact gives
  it; dropped.
- Open items, item 5: its quotation of §9 now matches §9 (*"nothing yet has been"*).
- Form: the arrows of the Appendix A table became words; the appendices were relabelled into
  letter order with no gaps (this appendix, formerly H, is now F, after the defect catalog, E),
  with every cross-reference updated; the work list became the final, unnumbered *Open items*;
  each bare "the floor" now names which floor; "designated items" is used throughout.

Nothing from that review remains open: the `[TODO at deposit]` of Appendix D closed when the
reserved version DOI was written into it (rc10).

### F-5 — 2026-10-05: two verified reviews of rc3, applied in rc4

Two sources. The first is the verification of the rc3 review (Grok and Gemini; 14 findings
confirmed, `_sprint-2026-10-04/REVIEW-A-rc3-2026-10-04.md`, cited below as R1 to R14). The
second is a further round by Codex, DeepSeek, GLM and Kimi, each finding checked against the
text, the code and the cited artifacts on 2026-10-05; the finding-by-finding record is
`_sprint-2026-10-04/APPLY-A-rc4.md`. Three quantities were recomputed rather than relabelled, each
with a dated artifact: the salience scripts import the production function `calculateSalience`,
and the bonus script reads the production constants from the deposited source. What changed:

- Access counterfactual, §4.3.2 and Abstract (Codex-2, superseding R8). The published
  2/3/5 → 131/129/128 came from `contrafactual-do-topo.py`, whose recency (linear over 365 days,
  from `source_date`) and `importance` default (0.5) are not those of `calculateSalience`.
  Recomputed with the production function (`out/SALIENCE-COUNTERFACTUAL-PROD-2026-10-05.json`,
  which reproduces the old numbers as an anchor): positions 1/3/4, falling to a tie at 44–46 of
  149 (23–47 across instants and access-timing assumptions), 54–56 of 201, 40–42 of 144 and
  50–52 of 196. "Beyond rank 100" and "exactly 52 places lower" are withdrawn; "128 other
  chunks" became 22 to 44. The claim that zeroing the access component takes the three out of the top-10 stands.
- Recency mechanism, §4.3.2 (Codex-3). Recency has no floor; the three never decay because
  their `retention_days` is NULL, the code's never-decay marker, which 39,130 chunks carry.
- Tie-break exposure, §5.7.1 (R4). Recounted on the comparator's key, `calculateSalience`,
  instead of the SQL pre-rank expression (`out/TIEBREAK-EXPOSURE-PROD-2026-10-05.json`): 34–42
  pairs at second resolution (0.59–0.73%) and 1,197 at day resolution, against 45–59 and 1,656 on
  the pre-rank expression at the same instants. The 68 / 269 / 917 / 1,656 of 2026-08-29 stay
  cited as the pre-rank count.
- Bonus against step, §4.4 and §5.4 (Codex-14, and 14b in §4.4). The 0.0946 and 1.79× used
  a 0.5 severity multiplier for S1 that only the replay's summary applies; production applies
  0.25. Recomputed: 0.0473, 0.90× the largest adjacent gap (`out/BONUS-VS-STEP-2026-10-05.json`).
  The claim that the items crossed several positions is withdrawn, and so is "step ≤ distance".
- What the exposure count is exact about, §3.1, §4.1, §4.1.1, Abstract (Codex-1). A positive
  `access_count` marks a top candidate of some tracked search sub-query, a superset of what
  tracked search returned. The 56,288 is exact as a count of its predicate and a lower bound on
  non-delivery by the brief and tracked search; the 9,755 is an upper bound on what tracked
  search returned; the union is no bound in either direction.
- Derivation premises, §5.3 and §5.4 (Codex-4, Codex-5). The prefix premise is stated, and
  where it fails (interleaved sub-pools, dedup between coverage candidates) is named. The
  "if and only if" entry condition holds only when `d` is the only bonused item of its stratum,
  and then with equality admitting `d` when the tie-break places it ahead of `c_K` (rc5);
  `b*` as a formula is withdrawn, and saturation rests on proportional bonuses over finitely many
  states. The generality claims (Abstract, §5, §7, §9) now say "that serves a prefix of that
  order"; §5.5's table no longer cites `b*`.
- Smaller corrections. §1, §4.3.2, §9 and the Abstract: the ceiling carries its regime
  (R3), and the coverage channel "responds to score only within `last_served` ties" instead of
  "does not respond" (R7). §9 uses 1,635 live (R1). §5.3: the 17/350 comes entirely from
  one-second ties (R2). §2: a drafting instruction removed (R6). §4.1: the cohort paragraph is
  descriptive, not a censoring correction (R9, Codex#7). §4.3.1: the 108 ids are not contiguous
  (R10); the pool changes the tie structure, not the denominator (R11); "every measurable day"
  (R14); 2026-09-02 has no briefs (Kimi-8). §1 and Open items: 5,376 is a 672-brief day (R12).
  §6 and Appendix C agree on where 0.874 is recorded (R13). §4.4: the saturation spread is at
  least 200×, not 220× (Codex#6); the ceiling's definition carries both conditions of §5.3
  (Kimi-10). §5.7.1: 2/9 ≈ 22%, not 11% (Codex#8). §4.5: the cron windows are named and the
  residual is not attributed to agents (Codex#9). §7 and Appendix A: which windows are
  pre-treatment (GLM-4, Codex#10). §4.2: the per-type split by surface is possible and not
  reported (Codex#11). §6: the attribution method matches §4.3.1 (Codex#12); §6 serves
  contribution (iv), and its heading changed (Codex#15). §8.2: monotone but responsive only within
  ties (Codex#13). §4.1.1 and Abstract: 99.98% is an expected coverage (Codex#16). §9 and F-1: 325
  is not reproducible; the locked numbers give about 327 (DeepSeek#1). The 0.16% is cut by the
  whole eligibility predicate, not by path patterns alone (GLM-2). §5.7.2: 104 s, not 98 (GLM-3).
  Title note: "on every measured day" (GLM-5). Appendix A: the 1,056 s precede the round, not the
  20:28Z closure (GLM-6). §5.5: capacity moves the cut (GLM-7). §5.6 and §6: what is
  module-private (Kimi-4). Appendix A: the S2 → ≥ S1 migration is in Paper B, not in the
  deviations log (Kimi-6). §5.3: the full exit condition of the fill loop (Kimi-11). §3.3:
  `salience.ts` is named (Kimi-13a).
- Provenance. Status block, §4.3.1, §5.7 and Appendix F: the numbers without an artifact
  are flagged (R5, Kimi-1, Kimi-3). The last-access dates of §4.3.2 now have one. Appendix D
  lists the 2026-10-04 and 2026-10-05 artifacts and where `claims_check.py` lives (GLM-1), and
  where the §4.2 partials are printed (Kimi-2).
- Independent check of rc4 (`_sprint-2026-10-04/CHECK-A-rc4-B-rc4.md`, D-A1 to D-A3). §4.3.2:
  the scope-pool sentence mixed two variants; each now carries its own numbers (`prod_acc0`:
  76–79 candidates from 43–46 files strictly above; `prod_noacc`: 57–79 from 24–46), and the
  positions 76–119 are named as stable-sort order inside a tie at 0.69, not a ranking. §4.3.2: a
  sentence-initial capital restored. §5.7.1: what the remaining ties share is now carried by an
  artifact, `out/TIEBREAK-EXPOSURE-PROD-SHARED-2026-10-05.json` (the same script with
  `--shared-plus 1`, written to a new file; the dated artifact cited before is unchanged).

Not applied here, because this round edits only the manuscript: the same 0.0946 / 1.79× in
`DEVIATIONS-FOR-PAPER.md`, `PROTOCOL-CALIBRATION-2026-08-27.md` and
`REPLAY-OPORTUNIDADE-2026-08-27.md`, the hardcoded S1 multiplier in `replay-oportunidade.mjs`,
the "98 segundos" comment in `claims_check.py`, and writing the §4.2 partials into
`out/SIZE-ROBUSTNESS-2026-08-30.json`. The `[TODO at deposit]` of Appendix D closed when the
version DOI was reserved (Appendix D).

**Addendum, rc5 (2026-10-05): a regression review of rc4.** Codex reviewed the text changed in
rc4 and returned ten findings; each was checked against the text, the deposited `serving-*.ts`
and the cited artifacts, all ten were confirmed, and the record is
`_sprint-2026-10-04/APPLY-A-rc5.md`. No number was recomputed. What changed:

- Ceiling, §4.4 and §5.3 consequence 1. The stratum condition is a necessary condition under
  the premises of §5.3, so its fraction bounds the alterable briefs from above; the ceiling is
  the replay's measured fraction of states that change at a saturating dose, deduplication
  included. This replaces the definition attributed to Kimi-10 above.
- Abstract. "For the most part initiated by the agent" claimed more than an upper bound can
  carry; it now says that most recorded exposure is not a delivery the system decided, and that
  how much search actually delivered is not established.
- §3.1, §1, §4.1 and the Codex-1 entry above. Search tracking can be switched off per call
  (`trackAccess = false`, healthchecks and the canary), so the bounds are on tracked search.
- §4.3.2, scope pool. "At most 5 slots" was the quota-pass allowance for agent-specific requests,
  not a maximum (pinning precedes the quota pass and backfill follows it, rc6); dedup may also reject the three themselves, so
  pool positions do not establish final membership.
- §4.3.2, positions 23–47. A sensitivity range over a fixed retrospective population, not "the
  true position".
- Appendix A. The constant 33 + 108 set holds from 2026-08-24 to 2026-09-19, inside checks that
  span 2026-08-21 to 2026-09-21 (`A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json`).
- §5.5 and §9. "Immune" and "deaf to the score" contradicted the corrected response claim; the
  coverage channel responds within `last_served` ties up to the ceiling.
- §5.4 and the Codex-4/Codex-5 entry above. With the tie-break included, equality can admit `d`;
  the strict inequality is sufficient, not necessary.
- This appendix. The entry on the access counterfactual had the direction reversed (it is
  zeroing access that takes the three out of the top-10), and the bonus script reads production
  constants from source rather than importing a production function.

**Addendum, rc6 (2026-10-05): four rc4 corrections that were applied only where they were quoted.**
A final Codex pass over rc5 confirmed six of the ten rc4 corrections and found that four held only
at the quoted place. Each is now fixed as a class: the whole manuscript was searched for it, every
hit was decided, and the search tables are in `_sprint-2026-10-04/APPLY-A-rc6.md`. No number was
recomputed or changed.

- Who initiated a search, and what search delivered (Codex-R2). `access_count` is incremented for
  the top candidates of every tracked sub-query; tracking is the default, and the source comment
  records that the semantic canary, an automated caller, incremented it until it was switched to
  untracked (`search.ts:377-396`). The counter records candidacy in a tracked call, not who
  initiated the call and not whether the chunk was returned. The Abstract, §1, §3.1, §4.1.1,
  §4.2, §4.3.2, §7, §8.2, §9 and the F-2 table no longer say that the counter shows
  agent-initiated exposure or that search accounts for most of the exposure. This supersedes
  the rc5 wording quoted above ("most recorded exposure is not a delivery the system decided").
- Scope of non-delivery (Codex-R3). Every statement that the 83.78% was never exposed by either
  surface, never reached the agent or was never shown now carries its scope: those live chunks
  have neither a brief-log record nor a positive search counter, which is a lower bound on
  non-delivery by the brief and by tracked search, and non-delivery across all agent-facing
  search is not established (Abstract, §1, contributions, §2, §3.1, §4.1 heading, table and
  text, §4.1.1, §4.5, §8.1, §9). Later uses of "never exposed" as the term defined in §2 are left
  as they are.
- Pinning order (Codex-R4). Pinning is phase 0 of `pickDedup` and precedes the quota pass and the
  backfill (`brief.ts:438-480`). §4.3.2 said the quota pass came "before pinning" and the rc5
  entry above said "pinning and backfill follow"; both now put pinning first, and the §4.3.1
  filter list says that F7 runs first although it is listed last.
- Relevance and eligibility (Codex-R7). The coverage channel's daily reach is set by eligibility,
  which fixes the candidate population and which the channel exhausted in the measured regime;
  per-brief selection is where salience acts, within `last_served` ties, saturating at 17/350 in
  the replay. The categorical forms ("nothing to do with relevance", "not governed by relevance",
  "the score does not decide", "deafness to the score", "not by relevance", "does not predict
  exposure") are replaced in §1, §4.2, §4.3.1, §4.3.2 and §5.5, and the Abstract, §4.3.2 and §9
  summaries now name both quantities.

**Addendum, rc7 (2026-10-05): four rc6 phrasings that kept an exclusive or unscoped reading.**
A Codex pass over rc6 found four medium findings. Each was checked against the code or against
§3.1 before it was applied, and each was then fixed as a class: the whole manuscript was searched
for it, every hit was decided, and the search table is in `_sprint-2026-10-04/APPLY-A-rc7.md`. No
number was recomputed or changed.

- Scope of the §4.1 finding (Codex-R3). §4.1 said that "the surface does not show" the fragments
  that pass the importance floor. It now says that those fragments have neither a brief-log record
  nor a positive search counter, a lower bound on non-delivery by the brief and tracked search.
- The historical union (Codex-R2/R3). §4.1.1 no longer says that the union "counts what was
  exposed at some point". The union combines historical brief-log membership, the chunks deleted
  afterwards included, with positive search counters on live chunks, and it does not count
  delivered exposure; the live corpus is the population over which the record predicate is
  measured, not the one "of which one can say never exposed".
- Exclusive attribution to the system (Codex-R2). The Abstract (twice), §1 and §4.1.1 (twice) no
  longer say that only the brief is decided by the system. The brief proactively selects content
  for delivery; the search counter records candidacy in tracked calls without identifying their
  initiators, automated callers included, so the counter supports no exclusive attribution.
- What eligibility is (Codex-R7). Eligibility is not a set of paths: the predicate combines path
  patterns, the importance/pain floor and the age windows, one for the agent sub-pool and one for
  the global sub-pool (`brief.ts:638-647`). §4.3.1 and §5.5 now say so, and say that the
  within-tie response holds with eligibility fixed. The Abstract, §4.3.2 and §9 summaries now say
  that the channel's daily reach is bounded by its eligible population, which it exhausted in the
  measured regime. This supersedes the rc6 entry above where it says that eligibility "fixes the
  candidate population" without naming its components and that per-brief selection "is where
  salience acts".

**Addendum, rc8 (2026-10-05): two §1 sentences that the rc7 class search missed.** A further
Codex pass over rc7 (receipt `.remember/adversary-receipt-codex-2026-10-05T100118-80790.txt`,
exit 0) proposed two §1 sentences, and both are taken verbatim. The first replaces "exhausts a
path-and-age eligibility predicate", which named two of the three components of eligibility,
with a pool "selected by path patterns, the importance/pain floor and age windows", exhausted in
the measured regime. The second replaces "fails, for two reasons, neither of them a shortage of
relevance", a categorical exclusion of the kind the rc6 entry above retired, with "two distinct
constraints": eligibility bounds daily reach, and with eligibility fixed an additive salience
bonus changes per-brief selection only within `last_served` ties. Both phrasings are added to the
class check. No number was recomputed or changed.

**Addendum, rc9 (writing pass, 2026-10-05).** A prose-only pass over the whole manuscript, with
priority on the text that entered in rc5 to rc8, against the patterns that make technical prose
read as generated: em dashes in running prose, "it is not X: it is Y" pivots, hollow
intensifiers ("actually", "radically", "the very", emphatic "exactly"), significance labels
("what matters is", "in its own right", "completes the thesis"), mid-list bold and stacked
hedges. Twenty-three spans were reworded; the list, with each before and after, is in
`_sprint-2026-10-04/APPLY-A-rc9.md`. Em dashes in running prose went to zero; those left are
table separators and empty cells, headings, quoted material and the run-in labels of F-3. Left
as written on purpose: "exactly" wherever it states an identity or a count, "robust" in its
statistical sense, the drand "beacon", the run-in caveat markers (whose density this appendix
measures), the correction history of F-1 to F-5, and the two §1 sentences taken verbatim from
Codex in rc8. `_sprint-2026-10-04/A-rc9/parity-rc9.py` checks, against rc8: the multisets of
numeric tokens and number words, footnote markers and back-references, cross-references, inline
code spans and fenced blocks (which carry the paths and line citations), and link targets and
DOIs; headings and table rows, byte for byte; the rc5 to rc8 addenda, byte for byte; the count
of each rc6 to rc8 scope qualifier; the class check inherited from rc8; and em dashes in running
prose. It does not check units, quotations outside code spans or the wording around a number;
that these did not change rests on manual review of the before-and-after list.

**Addendum, rc10 (2026-10-05): a Fable pass and a Codex check over rc9.** Fifteen findings (Fable
F1 to F13, Codex C1 and C2; `_sprint-2026-10-04/REVIEW-A-rc9-2026-10-05.md`), each checked against
the code and the cited artifacts before it was applied; the record is
`_sprint-2026-10-04/APPLY-A-rc10.md`. All fifteen were applied, three of them with a correction to
the finding itself (F1, F2, F6). What changed:

- Deposit (F1). Appendix D carries the reserved version DOI, and the status block, F-4, F-5 and
  Open items 4 and 5 now agree with it.
- The three constant chunks (F2). The Abstract and §9 named search traffic as what determines
  positions 1, 3 and 4, which are salience ranks among 149 served chunks, and left out the
  high-pain pin. Lifting the pin removes 116107 from every reconstructed brief of 2026-08-21 to
  2026-09-07 (`lift_F7_pinned`), and §4.3.2 now says so. The Abstract does not adopt the proposed
  "necessary condition for their presence": §4.3.2 does not replay dedup, so final membership with
  access zeroed is not established.
- The survey (F3). The Abstract and §1 no longer state a universal over 218 papers; they say what
  the survey's metric taxonomy contains.
- Scope clause (F4). §3.1 defines *no-record* once. The Abstract keeps the full statement, and §1,
  §2, §4.1, §4.1.1, §4.5 and §8.1 use the term with a pointer to §3.1. Repeats of "whoever
  initiated" and of the defective-ingestion regime were thinned where the same section had already
  stated them.
- Abstract (F5). The correction narrative of the third axis became one sentence, the Caveat and
  Correction labels left the Abstract, the note that repeated §3.1 was dropped and the curation
  note joined what we do not claim: 1,177 words became 1,090.
- §4.3.1 fidelity (F6). The 100% holds under the criterion the text declares; the stricter
  id-for-id test passes in 94.3–97.9% of the briefs of each day except 2026-09-03 and 2026-09-07, where `fresh_added` is null, and every failure comes from
  `fresh_added` being logged from the treated composition. 2026-08-21 to 08-23 are left out
  because the frozen copy does not hold the served state of one `boris` slot (chunk 298048), not
  for the reason the finding guessed (the 52 deleted chunks, which are coverage slots).
- Smaller corrections. Title (F7). §1: the parenthesis on the 33 (F8). §5.3: the fresh-slot loop
  is at `brief.ts:470-474` (F9). §6: the 617 is defined and flagged as having no preserved field
  (F10). §4.3.1: the coverage set's change on 2026-09-20 may be a main-pool change (F11). §6.1:
  the 0 of 32 joins the status block's list of numbers without an artifact (F12). §2: search is
  no longer defined by agent initiative (C1). rc9 addendum: its last sentence lists the checks
  `parity-rc9.py` implements and leaves the rest to manual review (C2).
- Prose (F13). The duplicated sentence on declaring ignorance (F-3.1) and ten paragraph closers
  were cut or merged into the sentence before. The run-in labels outside the Abstract stay,
  because this appendix reports their density; that density was measured on the Portuguese text,
  so removing the Abstract's labels changes no reported number.

`_sprint-2026-10-04/A-rc10/parity-rc10.py` compares rc9 with rc10 and requires every changed
numeric token, reference, code span, link, heading and table row to be one that a finding above
declares.

**Addendum, rc11 (2026-10-05): a Fable regression review of rc10.** Eight findings
(`_sprint-2026-10-04/REVIEW-A-rc10-2026-10-05.md`), each checked against the artifacts it cites
before it was applied; the record is `_sprint-2026-10-04/APPLY-A-rc11.md`. All eight were applied
with the wording the review proposed. What changed:

- Deposit (finding 1). §4.3.1 cites `A-filters-disaggregation/diag-out.txt`, which the v1.1
  package had excluded as not cited by the text. Appendix D now lists it, with the script that
  produced it (`diag-residual-mismatch.py`), and the deposit carries both.
- The three days left out of the §4.3.1 fidelity test (finding 2). The 85.8%, 85.7% and 98.0% are
  the first criterion; under the stricter one 2026-08-23 gives 84.3%. The text no longer explains
  the mismatch by briefs served before the access of 2026-08-22T19:09Z: production kept 285042
  after that access, on 2026-08-22 and part of 2026-08-23, and why is not established.
- The three constant chunks (findings 3, 4 and 5). §9 says that search traffic holds their
  salience ranks, not their slots. §4.3.2 says that the pin is measured as necessary for one of
  the three (116107), and that 112241 and 116467 stay when it is lifted. §1 says that the pin holds
  them, not that the floor placed them.
- Smaller corrections. Open items 5 says that the v1.1 deposit carries the 10 Appendix D entries
  (finding 6). The rc10 addendum names the two days where the stricter test does not apply
  (finding 7). The Abstract's sentence on the two universes is reworded (finding 8).

`_sprint-2026-10-04/A-rc11/parity-rc11.py` compares rc10 with rc11 under the same rule: every
changed numeric token, reference, code span, link, heading and table row must be one that a
finding above declares.

**Addendum, rc12 (2026-10-05): a Fable review of rc11.** Three findings
(`_sprint-2026-10-04/REVIEW-A-rc11-2026-10-05.md`, numbered 2 to 4 there), each checked against
the code and the artifacts it cites before it was applied; the record is
`_sprint-2026-10-04/APPLY-A-rc12.md`. All were applied with the wording the review proposed. The
review found no wrong number in rc11. What changed:

- The three shared slots of the main pool (finding 2). §4.3.1 no longer says that the high-pain
  floor takes them. They are what `mainTarget` leaves after the agent quota (8 − 5); as served,
  the three pinned chunks fill them in phase 0, before the quota pass; with F7 lifted the same
  three slots go to the `scope=global` sub-pool's top three after dedup, where 227328 replaces
  116107. The rc11 addendum had left that sentence as is; it was the same class as the §1
  sentence corrected in rc11.
- Deposit (finding 3). The package manifest now declares two exclusions: the local receipt of
  the voice cited by the rc8 addendum, and the working names of the two databases that
  `diag-out.txt` mentions.
- Smaller corrections (finding 4). Appendix D says that the table gives the full paths of two
  sprint scripts, and its row for the filter disaggregation gives the full path of
  `diag-residual-mismatch.py` and says that `diag-out.txt` also holds a 2026-09-08 run and the
  2026-08-28 control. §9 gives the days since last access in rank order (42, 90 and 30), as the
  Abstract does.

`_sprint-2026-10-04/A-rc12/parity-rc12.py` compares rc11 with rc12 under the same rule: every
changed numeric token, reference, code span, link, heading and table row must be one that a
finding above declares.

**Addendum, rc13 (2026-10-05): a Codex and a DeepSeek review of rc12.** Eight findings, two from
Codex (C1, C2) and six from DeepSeek (DS1 to DS6), saved verbatim in
`_sprint-2026-10-04/REVIEW-A-rc12-2026-10-05.md`. Each was checked against the text, the serving
code and the artifacts before it was applied; the record is `_sprint-2026-10-04/APPLY-A-rc13.md`.
All eight were applied, C1 and C2 with the wording Codex proposed. What changed:

- The frozen set of §1 (DS1). §1 said that we measured five consecutive days with zero new items,
  the minimum served age rising by exactly +1.00 per day. No preserved artifact holds that series:
  v1.0 stated it in §1, item 1 of the coverage channel's two reasons, and its §2 said that §4.3.1
  showed five consecutive days without an eligible candidate, which v1.0's §4.3.1 does not show.
  The table it came from was in a pre-deposit draft, computed by `regime-cobertura.py`, whose
  output was not kept.
  The claim also does not hold as written: that table itself showed 52 new items on 2026-08-20,
  the `memory/lessons.md` ingestion of that day, which its age column could not see because the
  chunks were later deleted (§4.3.1, the counting trap). §1 now cites two measurements that
  artifacts hold, kept apart: the serving log shows the same 108 coverage-side ids on every day
  from 2026-08-23 to 2026-08-29 (`A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json`); separately,
  counting serves across both channels, the batch of 2026-08-21 to 08-22 contributed 108
  distinct chunks a day, except 109 on 2026-08-26, its minimum served age rising from 0.92 to
  6.92 days in daily increments of 1.00 (`BATCH-CYCLE-2026-08-29.json`). §4.3.1 states both with
  those dates, and §2 calls those days frozen days rather than five days without new items. The
  coverage-served portion of that batch belongs to the global sub-pool, so §1 no longer assigns
  the observation to the per-agent one. (This item was corrected in rc14; see below.)
- The three constant chunks (C1, DS2, DS6). Tracked search traffic is necessary for their
  salience ranks; the pin affects selection, and lifting it removes one of the three (116107)
  from the main set. The Abstract, §1, §4.3.2 and §9 now keep the two apart: the Abstract no
  longer says that the pin keeps them in every brief, and §1 names the slots as the three shared
  main-pool slots. The pin selects them in phase 0, before the quota pass; it does not fix their
  position in the brief (wording corrected in rc14).
- §4.3.1 fidelity (C2). On the days where `fresh_added` is not null, a brief that fails the
  stricter test leaves 9 or 10 ids, not 9; on 2026-09-03 and 2026-09-07 all 10 served ids stay.
- Scope and denominators (DS3, DS4, DS5). §2 calls *no-record* a verifiable property of the
  records and, read as non-delivery, a lower bound. The §4.3.1 filter table counts briefs of a
  672-brief day, and a note gives 2026-09-03 (441 and 126). §1 says which sub-pool was empty
  (the per-agent one, 0 eligible) and that the global one held 108.

`_sprint-2026-10-04/A-rc13/parity-rc13.py` compares rc12 with rc13 under the same rule: every
changed numeric token, reference, code span, link, heading and table row must be one that a
finding above declares.

**Addendum, rc14 (2026-10-05): a Codex review of rc13.** Two findings (CR1, CR2), saved verbatim
in `_sprint-2026-10-04/REVIEW-A-rc13-2026-10-05.md`, both checked against the artifacts and the
serving code and both applied; the record is `_sprint-2026-10-04/APPLY-A-rc14.md`. The rc13
addendum above is part of this unpublished version, so its two affected items were corrected in
place rather than left as history. What changed:

- Two measurements kept apart (CR1). rc13 read `BATCH-CYCLE-2026-08-29.json` as the frozen
  coverage set. Its query selects the batch by creation date and counts serves in both channels,
  so its 109 on 2026-08-26 is not a coverage-channel count: in its 10-row agent briefs, the
  serving log gives the same 108 coverage-side ids on that day as on every day from 2026-08-23
  to 2026-08-29 (`A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json`). §1 and §4.3.1 now state the
  coverage set from the log and, separately, the batch's serves across both channels (108 a day,
  except 109 on 2026-08-26) with its minimum served age rising from 0.92 on 2026-08-23 to 6.92
  on 2026-08-29 in daily increments of 1.00 (0.72 on 2026-08-22), reported to two decimal
  places (agent-brief qualifier and dates added in rc15). §1 assigns the coverage-served portion of the batch to the
  global sub-pool, and §2 cites the coverage-set artifact.
- Selection is not position (CR2). Phase 0 of `pickDedup` selects the pinned items before the
  quota pass, and the picked list is then sorted by score (`brief.ts:483`), so the pin does not
  place them first in the brief. The Abstract, §1 and §9 now say that the pin selects them in
  phase 0, before the quota pass; the measured necessity of the pin for one of the three stays.
- The rc13 addendum also said that the table behind the withdrawn five-day series was in the v1.0
  text. It was in a pre-deposit draft; v1.0 carried the statement in §1 and a pointer in §2.

`_sprint-2026-10-04/A-rc14/parity-rc14.py` compares rc13 with rc14 under the same rule.

**Addendum, rc15 (2026-10-05): a Fable and a Codex review of rc14.** Ten findings (Fable FB1 to
FB3, Codex CX1 to CX7), saved verbatim in `_sprint-2026-10-04/REVIEW-A-rc14-2026-10-05.md`, each
checked against the code, the artifacts or the source it cites; all ten hold and all ten were
applied. The record is `_sprint-2026-10-04/APPLY-A-rc15.md`. No number of rc14 changed; the text
gains the 146 and the 0.72 below, both read from artifacts it already cites. What changed:

- The coverage set is a count over the agent briefs (FB1). `coverage-set-from-log.py` keeps only
  10-row briefs with an agent, so the five 5-row health probes of 2026-08-26 are outside it; they
  served 5 further chunks that day, and `brief_log` holds 146 distinct chunks on that day, not
  141. §1, §2, §4.3.1, Appendix A and F-4 now say "in the agent briefs", and §4.3.1 names the
  exception. The rc14 addendum above was corrected in place; the rc13 addendum keeps its wording
  as history and is read with this qualifier.
- Dates of the minimum served age (FB2). It rose from 0.92 on 2026-08-23 to 6.92 on 2026-08-29;
  on 2026-08-22 it was 0.72. §1 and the rc14 addendum now give the dates.
- The survey's metrics (CX1). Table 3 of the survey also lists memory-quality, response-quality
  and end-to-end task metrics, so the Abstract, §1 and §8.1 no longer say that every metric in
  use is a score over a set of queries; they say that its metric taxonomy does not include a
  census of distinct memory items delivered under production traffic.
- §5.6 is a same-stratum matching check, not a falsifier (CX2). Deduplication in `pickDedup` is
  order-dependent, so an entry with no exit in its stratum would not by itself refute
  Proposition 1. The result row now reads "same-stratum matching check: passes".
- Severity labels (CX3). The ceiling was measured with the recorded labels held fixed; its
  independence from them is not established. Appendix C says that the labels are a second way the panel enters.
- §5.5 (CX4). The 17/350 holds with eligibility, designation and severity multipliers fixed; it is
  not a maximum over all additive salience adjustments (other designations give 17 to 26).
- §6, last row (CX5). 245 brief records against 151 search records with a lower-bound predicate
  do not establish which surface delivered more distinct entities; the row no longer says that the
  brief leads.
- `churn` (CX6) counts the treated-only ids (`would_enter`), half the symmetric difference for sets
  of equal size; every reported churn number was computed that way and stays.
- Utility (CX7). The Abstract, §1, §4.1.1 and §9 no longer say that uniform serving would be
  useless or worse than not serving; its effect on agent utility was not measured.
- The package (FB3). The manifest now keeps the hash of the original for all eight packaged files
  whose local paths were replaced, `REVIEW-A-rc12-2026-10-05.md` included. This touches the
  deposit, not the text.

`_sprint-2026-10-04/A-rc15/parity-rc15.py` compares rc14 with rc15 under the same rule.

## Open items

What is missing, in order of what blocks what. Items are struck through when closed.

Done on 2026-08-28, unless indicated:

**Done.** §1, §2, §8, §9 written · §5 on 2026-08-27 · Abstract written.
**Done.** Figures 1, 2 and 3: each derived from a locked artifact, with its own guard.
**Done.** survey count recomputed over the PDF pinned by sha256, with positive control.
**Done.** regime break of 2026-08-21–22: explained (§4.3.1), with a dated prediction for 2026-08-29.
**Done.** S2, decided by measurement: substantive items at `≥ S1` (κ 0.87–0.93), the S1/S2 split
becomes an instrument finding (κ 0.31–0.53). Deviation declared in Appendix A.
**Done.** defect catalog: 8 in the body (those that changed a reported number), 9 in
Appendix E. No separate methods paper.

Missing:

~~1. architecture figure of §2~~ → Done on 2026-08-28: Figure 0,
   `out/fig0-arquitetura.svg`. It is the only figure that does not derive from an artifact, because it
   describes structure and not data;
~~2. verify the prediction of 2026-08-29~~ → Done on 2026-08-29, and the prediction was
   REFUTED: the gate came out `exit 1`, §4.3.1 was rewritten around what the
   investigation found (two sub-pools; eligible pool of 108 out of 67,187 = 0.161%, exhausted
   100% every day), and the new explanation was validated by a differential test
   `freshSlots=2` vs `freshSlots=0`. Resolved by replacement, not by confirmation;

**Caveat.** The two items above went three weeks without being struck through, and on 2026-09-21 this list sent an entire
session in the wrong direction: reading a worklist from 2026-08-28 and concluding
about today's state. What is actually missing:

~~3. adversarial review pass~~ → Done on 2026-09-21: Kimi (Moonshot),
   receipt `exit: 0`, 682 s, 76 KB over the 1,937 lines. Findings applied in full;
   see the correction history and `REVISAO-ADVERSARIAL-2026-09-21.md`. Codex ran in the
   same batch and returned an invalid opinion: four citations that do not resolve against this
   file, including *"there is no section §4.3.1"*; recorded with the evidence, because «the
   voice found nothing» and «the voice did not read» are not the same thing.

   **Caveat.** One voice is not the five. The adversarial review of this manuscript was done by
   one family; Paper B took three. If the deposit requires more, this reopens.

   ~~original pass:~~ voices of distinct families over the
   entire manuscript; the recorded lesson is that adversarial review and mechanical census catch
   disjoint classes of defect, and only the second had been done so far;
4. ~~**deposit** with the manuscript + artifacts~~ → v1.0 was deposited on 2026-08-30, in
   Portuguese (`10.5281/zenodo.22181415`, concept DOI `10.5281/zenodo.22181414`; Appendix D).
   → v1.1 is this text, under the reserved version DOI `10.5281/zenodo.23163119` (Appendix D);
   the grouped amendment of the pre-registration follows the deposit: a single registration,
   declaring the deviations and the new result.

5. Partial. Sweep of claims that have aged (opened on 2026-09-21, three
   instances closed on 2026-09-21 by adversarial review, not by the sweep): §8.3
   (*"that did not run"*), §9 (*"nothing yet has been"*) and §4.5 (*"0 rows"*, now dated and
   marked as not re-verified). Caveat. The systematic sweep remains to be done. Three
   instances found by external reading are not a census, and the lesson of today is precisely
   that declaring a sweep open is not the same as doing it.

   **Open and declared in the text, from the same opinion:** ~~the `52 = 52` reconciliation
   (§4.3.1 vs §4.3.2), the 25 probe slots (§4.3)~~ → Closed 2026-10-04 by identity
   measurement (`_sprint-2026-10-04/A-recon-52-and-slots.md`,
   `measurement/sprint-recon-52-e-sondas.py`). The 52 are one `lessons.md` batch, missing
   identically on 2026-08-20, 08-21 and 08-22; the "2026-08-20: 85 → 33" was 2026-08-21. The 25
   slots are the five probes, identified by `brief_id`, which also add 5 probe-only chunks
   (organic distinct = 196). ~~the `POOL-ELEGIVEL` that covers one day for a claim about four
   (§4.3.1)~~ → closed 2026-10-04 by re-measurement from a preserved database, with a
   positive control (`_sprint-2026-10-04/A-recon-pool-elegivel.md`,
   `POOL-ELEGIVEL-2026-08-26-to-29.json`). ~~the comparability control of §5.7.2 that validates
   by count~~ → closed 2026-10-04 at identity level; ~~the `[MISSING]` DOI in Appendix D~~ →
   concept DOI cited, and the reserved version DOI is now in Appendix D; ~~the pointers to
   `DEVIATIONS-FOR-PAPER.md` that Appendix D does not list among the deposited artifacts~~ →
   listed (`_sprint-2026-10-04/A-recon-5.7.2-appD.md`). The artifact census
   (`measurement/sprint-censo-artefatos-paperA.py`) reported 1 missing input
   (`ts-350.txt`) and 10 Appendix D entries absent from the v1.0 deposit. The v1.1 deposit carries
   the 10 entries; `ts-350.txt` was not kept (§5.6) and stays declared missing.

6. ~~**Caveat.** The seven serial filters are not disaggregated (opened 2026-09-21, from Codex's opinion,
   the only criticism of it that does not depend on a citation). §4.3.1 attributes the non-exposure of the
   coverage channel to path patterns; the main pool, 8 of the 10 slots, does not
   receive the same decomposition. The thesis «policy, not capacity» is sustained for the channel
   and assumed for the main one.~~ → Done: the seven serial filters of the main pool are now
   disaggregated (§4.3.1, sprint 2026-10-04; `measurement/sprint-desagrega-filtros-pool-principal.py`,
   `_sprint-2026-10-04/A-filters-disaggregation.md`). The reconstruction on the frozen
   corpus reproduces the served briefs in 100% of the briefs of 2026-08-24 to 2026-09-07 (under the
   criterion of §4.3.1), and
   leave-one-out on it shows that no filter, lifted, widens the daily surface beyond 33 chunks; F3 (proxy pre-rank with `LIMIT 500`)
   removes 95.7% of the corpus and changes 0 briefs; F1 (scope routing) and F6 (quota split)
   narrow it to 8. The main pool is policy-bound (a deterministic top-k, no rotation), not
   capacity-bound (33 distinct chunks, 0.61% of the 5,376 main slots of a 672-brief day). Caveat: the Codex output
   naming "seven" was not preserved (only its receipt), so the seven are the stages read from
   `brief.ts`, not necessarily the reviewer's list.

~~(the old item 5 said:)~~ Caveat. Sweep of claims that have aged (opened on
   2026-09-21). Appendix A said that the interventional study "had not begun", true
   on 2026-09-01 and false since then; corrected. That is not necessarily the only one: any
   sentence written in the present tense about the state of the trial needs to be re-read before the deposit.
   The method is a reading of the sections that talk about the trial (§4.5, Appendix A,
   Appendix C, §9), not a substring search.
