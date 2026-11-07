# Paper B2: does a repair pass against the source fix an LLM-extracted knowledge graph? Pre-registration v1.0

Written 2026-11-07, after Paper B's human grades were committed (`paper-b-kg/HUMAN-COMMITMENT.json`,
#682) and **before Paper B's reading** (`b-read.py`). Nothing here is fixed until the tag
`paper-b2-prereg-v1.0` is on the public main branch. The author opened this study on 2026-11-07
(«o ponto 3 pode virar um paper interessante! e vamos seguir sua recomendacao») and chose the
repairer (Claude Opus 5.5) and the order (this tag before B's reading). He approved the tag on
2026-11-07 18:06 BRT («pode taguear, sem vozes»), then asked for two voices first («alias passa
codex e deepseek e ai taguea»); the round and what it changed are in §9. Points marked
**[v1.0, Codex]** or **[v1.0, DeepSeek]** come from it.

**What the author of this draft knew about Paper B when writing it.** The public commitments only:
the 300 + 30 sampled relations exist, the two judges disagreed on 76 of the 300, 37 rows carried a
marker, and 60 were drawn at random for the sheet (`SHEET-COMMITMENT.json`). No label, no judge
rate, no human grade, and no direction of any disagreement. B's private `judges.json` and the
graded sheet were read only by B's scripts, which print counts and hashes.

## 0. Why

A post by Anthropic («The components of agent memory», 2026-11-06) reports that an offline pass
which rereads the source ("dreaming") corrects wrong memory notes. Its evidence is one run per arm
in a game and 24 to 25 questions on document sets, with no interval and no control. Paper B already
measures, on a frozen sample, whether each relation of this graph is supported by the chunk it
cites. Running a repair pass on the same relations and measuring them again turns that claim into a
paired estimate with a positive control.

## 1. Questions

**B2-P (precision, estimated).** Of the relations left after the repair pass, what share are
supported by their chunk, against B-F before the pass on the same 300?

**B2-R (retention, estimated).** Of the relations Paper B labels supported, what share does the
repair pass keep **unchanged**? **[v1.0, Codex]** A supported relation that the pass rewrites is not
retained, even when the rewrite is itself supported: a rewrite may change the predicate or both
entities, and counting a substitute fact as the original would let precision and retention rise
while the specific information is lost. The lenient figure (kept, or rewritten into a supported
triple) is reported beside it, not interpreted.

The two answer different costs: a pass that deletes everything doubtful raises precision and loses
retention. Neither number alone says the pass helps. The post's own wiki case (41 of 57 facts kept
before the instructions changed) is a retention failure, which is why retention is primary here.

Reported beside them, not interpreted, so that a gain can be split into filtering and correcting:
the transitions of each relation (keep, delete, or rewrite of the same pair, the swapped pair or a
new pair, supported or not), separately for those Paper B labels supported and unsupported; the
correction rate (of the unsupported, the share deleted or rewritten into a supported triple) and the
damage rate (of the supported, the share deleted or rewritten into an unsupported triple); the
precision the pass would have reached had every rewrite been a delete; and the count of supported
outputs before and after.

## 2. Sample and the "before" labels

No new draw. The 300 relations and the 30 mismatched pairs frozen by Paper B
(`FREEZE-COMMITMENT.json`, seed 3335023133), with the same chunks, cut at the same 6,000
characters. The "before" label of each relation is Paper B's final label, under Paper B's rules,
unchanged. **[v1.0, Codex]** The universe is fixed at those 300: no relation leaves it because a
label is missing. If Paper B's reading falls back to its random rows (both of its judges fail a
control), some relations have no final label and no judge can label a rewrite off the sheet; B2-P
and B2-R are then declared unavailable, not computed on the complete cases, and only the actions
are reported.

Precision is limited by how many relations B labels unsupported. If B-F is near October's 0.900,
about 30 of the 300 are unsupported, and the correction rate's Wilson 95% interval is about ±17
points. This protocol does not enlarge the sample, because no relation outside the 300 has a label.
The note states the interval it gets.

## 3. The repair pass

**Repairer:** `claude-opus-5-5` (Anthropic). Its family differs from both of Paper B's judges
(Google, OpenAI). **[2026-11-07]** No Anthropic API key exists on the author's machines, and the
author chose to run the repairer through the Claude Code CLI on his subscription («Via claude -p»).
Each call is `claude -p` with this protocol's system prompt replacing Claude Code's, no tools, no
MCP server, no setting source (so no hook and no instruction file), no saved session, an empty
working directory, and structured output against the schema in `b2-common.py`. The CLI implements
structured output as a tool call, so each call has two turns, and it reports the served model, the
tokens (thinking included) and a cost at list price, which this protocol records as the spend
although the subscription does not bill it per token. The model takes no temperature and its
thinking cannot be turned off; effort is `medium` (author, 2026-11-07, «02. Medium»). With no
temperature the output is not repeatable: each relation is asked **once**, the answer is cached,
and a relation is asked again only after a transport error, which is counted. No fallback to
another model: a refusal or an answer that does not fit the schema is counted, and the relation is
kept unchanged (the conservative action). **[v1.0, Codex]** A served model other than
`claude-opus-5-5` stops the run, to be reported as a deviation. Every attempt, answered or not, is
appended to a private log with its status and list-price cost; the cap counts every attempt, and
the commitment reports the attempts by status, the CLI version and the turns per call. The figure
is a list-price equivalent, not money spent. The unit studied is this configuration (this CLI,
this model, this prompt, this effort, this output mechanism), not the model in general.

**Input.** The triple (source entity, predicate, target entity) and the chunk. Nothing else: no
label, no judge verdict, no human grade, no other relation. One sentence of purpose and the support
definition the judges use, with Paper B's four rules (P1 inversion is not supported, P2 an
impoverished but not inverted predicate is, P3 a placeholder in a worked example is not an entity,
P4 formatting never rejects).

**Output** (structured JSON, schema in the script): one action:

- `keep`, with a quote: the first eight words of the supporting sentence;
- `rewrite`, with a new triple and its quote; the new triple must state a relation between the
  same two entities or between entities named in the chunk;
- `delete`, with a one-line reason.

A quote is checked with Paper B's alphanumeric check. A `keep` or `rewrite` whose quote fails is
still applied as the repairer chose and counted; the rewrite then goes to the judges like any other.
A `rewrite` whose triple equals the original (ignoring case and spacing) is a `keep`, everywhere,
the positive control included. Each rewrite is classed by its entities: the same pair in the same
order, the same pair swapped, or a new pair.

**Disclosure.** The repairer is given the rubric the judges apply. The pass is therefore optimised
toward the measuring rule, which is what a repair pass against a stated standard does. The human
grades on the rewrites (§4) are a check against a pass that satisfies the judges without satisfying
the source, not an independent one: **[v1.0, Codex]** the same author graded Paper B's sheet, and
both sheets judge support by the same rules. The labels are an operational reference, fallible,
and the intervals do not carry their error.

## 4. Labels after the pass

- `keep`: the relation keeps its Paper B final label.
- `delete`: the relation leaves the graph; it counts against retention if B labels it supported.
- `rewrite`: the new triple, with the same chunk, goes to both of Paper B's judges with Paper B's
  prompt, rules and quote check (`b-common.py`, as tagged by Paper B). A judge that failed one of
  Paper B's controls does not count, as in Paper B.

**Human sheet for the rewrites.** Blind, graded by the author, who sees the new triple and the chunk
and no verdict, no quote, no original triple and no "before" label. It holds Paper B's strata: every
rewrite on which the two judges' verified labels disagree; **[v1.0, Codex]** every rewrite both
verify whose chunk carries an exception or example marker (Paper B §5, applied to the chunk); and 30
rewrites drawn with seed + 1 from the rest (all of them if fewer). With no rewrite the sheet is
empty, and the empty grades are committed like any others. Rows shuffled with seed + 2. The seed is the integer value of the first eight
hexadecimal digits of the `paper-b2-prereg-v1.0` tag commit. Final label of a rewrite: the human
grade where there is one, otherwise the label both judges agree on.

## 5. Estimates, controls and reading

**Primary.** B2-P after the pass against B-F before, as a difference whose bootstrap 95% interval
resamples the 300 relations jointly for both figures (10,000 resamples, seed + 3; the "after"
denominator is the resampled relations not deleted); B2-R with a Wilson 95% interval.
No hypothesis test and no threshold: the note reports both figures and their intervals.

**Controls.**

| control | measured | passes when |
|---|---|---|
| positive: the pass must act on wrong evidence | the 30 mismatched pairs from Paper B, each relation shown with a chunk from a different document | the repairer keeps at most 10% unchanged |
| repairer quote check | share of `keep` and `rewrite` answers whose quote passes the alphanumeric check | reported |
| human against judges on rewrites | Cohen's kappa on the 30 random rewrite rows | reported; below 0.40 is stated as a limit |

If the positive control fails, B2-P and B2-R are reported as a failed instrument and not
interpreted, as in Paper D. **[v1.0, Codex]** Passing it shows only that the pass reacts to evidence
from another document; a pass that deletes or rewrites everything also passes. Retention (B2-R) is
the guard against that, and the mismatched pairs' actions are reported by kind.

**Reported, not interpreted.** Counts of each action; correction and damage rates; the actions by
Paper B's `relation_reason`, evidence bucket and sheet origin; the cost.

## 6. Order, cost and private data

Tag `paper-b2-prereg-v1.0`. After the tag Paper B's reading may run: nothing in this protocol
depends on its result, and the repairer never sees a label. Then:

One script, `b2.py`, one subcommand per step; the commitments live in this directory, so their
names do not collide with Paper B's:

1. **Repair** (`b2.py repair`): the 300 and the 30 mismatched. Commit `REPAIR-COMMITMENT.json`
   (calls, cost, tokens, served model, answers per kind, hashes; no action count, no triple and
   no text, so the human sheet is graded before any outcome is public).
2. **Judges on rewrites** (`b2.py judge`): commit `JUDGES-COMMITMENT.json`; its cap is US$ 20
   minus the repair's spend.
3. **Sheet** (`b2.py sheet`, then `b2.py grades`): `SHEET-COMMITMENT.json` (the sheet's hash, the
   selection's hash and the rows per stratum, as in Paper B; **[v1.0, DeepSeek]** the count of
   judge disagreements is therefore public before the grades, but not which rows they are), grade,
   `HUMAN-COMMITMENT.json`.
4. **Reading** (`b2.py read`): `READING-<date>.json`, then the note.

Each step refuses to run unless the previous commitment is on the public main branch, after the
tag, written once and byte-equal to the private copy; the reading also recomputes Paper B's final
labels under `b-read.py`'s own checks, from Paper B's four commitments. If no Paper B judge passed
its controls, a rewrite off the sheet has no label; it is excluded from both figures and counted.
`b2-test.py` exercises every step offline (fake `claude -p`, fake judges, a synthetic outcome whose
figures are known in advance, a throwaway git repository) with mutations each check must catch. Triples,
entity names and chunk text stay in `~/Backups/paper-b2-repair-<date>/` (mode 700) and are sent
only to the repairer and the two judge APIs.

**Cost cap: US$ 20** for the repair and the rewrite judging together, at list price, abort above
(author, 2026-11-07, «01. Ok»). **[2026-11-07] Smoke** (`b2-smoke.py`, approved with the cap): five
relations drawn with the fixed public seed `paper-b2-smoke-2026-11-07` from the population outside
Paper B's 330, then discarded. All five answers fit the schema, the served model was
`claude-opus-5-5` on every call, and every quote passed the check. Median 3,233 input tokens (most
of it the system prompt and the schema, written to the provider's cache), 578 output tokens of
which 228 thinking; US$ 0.0279 per call at list price, so about US$ 9.20 for the 330 calls. Rewrite
judging costs at most what Paper B's judges cost per call (US$ 4.49 for 660).

## 7. What a result can and cannot say

One graph, one sample of 300, one repairer, one pass, and one chunk per relation: a relation whose
support lives in another document is deleted by a pass that sees only its cited chunk, and Paper B
would have labelled it unsupported too, so the two measures agree on what "supported" means. The
result says whether this pass, on this graph, moves precision and at what retention. It says
nothing about repeated passes, about building new representations (the post's wikis), or about
whether an agent answers better from the repaired graph. **[v1.0, Codex]** Also:

- Supported by the chunk is not true, current or consistent across documents.
- The figures do not measure completeness, duplicates or the integrity of the graph.
- The reference labels come from two fallible judges and one author who graded both sheets; the
  intervals do not carry that error.
- The pass both filters and may extract substitute facts; it does not isolate one mechanism.
- One run: nothing about the repairer's stability across runs.
- About 30 unsupported relations allow a local description, not a claim of general efficacy, nor
  of a difference between models or kinds of error; zero observed damage would not show no risk.
- The relations come from Paper B's population, which excludes relations whose chunk is gone.
- The private files' hashes let their holder verify integrity; they do not allow independent
  public reproduction.

## 8. Open before the tag

1. ~~Cap and smoke~~ and ~~effort~~: decided 2026-11-07 (§3, §6).
2. ~~Route~~: `claude -p` on the subscription, decided 2026-11-07 (§3).
3. ~~Scripts~~: `b2.py` and `b2-test.py`; after the voices, 67 checks, 0 failures, including every
   subcommand end to end through a throwaway repository, with and without rewrites (2026-11-07).
4. ~~Voices~~ and ~~tag~~: §9.

## 9. Adversarial round before the tag

2026-11-07, on the text and scripts at `1c92eeb`, at the author's request (18:06 BRT). Both receipts
`exit 0`, working directory the main clone.

| voice | mode | verdict | taken |
|---|---|---|---|
| Codex (gpt-6-astra, 108 s) | challenge | block the freeze | retention redefined as kept unchanged (a substitute fact is not retention), lenient figure reported; universe fixed at 300, primary declared unavailable instead of computed on complete cases; zero-rewrite flow fixed and tested; transitions, rewrite pairs and a filter-only precision reported; identical rewrites are keeps; served-model stop, attempt log, CLI version and list-price wording; marker stratum on the sheet; labels declared an operational reference graded by the same author; positive control's reach stated; §7 limits |
| DeepSeek (v4-pro, 284 s, 70,567 characters attached) | review | eight findings | the exclusion finding (same as Codex's); reading now carries the cost and the human rate by sheet origin; `judge` and `sheet` refuse a Paper B freeze other than the repair's; the message-purity test checks the exact message; the end-to-end test it asked for. Not taken: "the bootstrap is not paired" (both figures are resampled over the same relations; the wording now says so), and checking the sheet's hash in `grades` (the graded sheet differs from the blank by construction; the texts are checked row by row, as in Paper B) |

What neither voice could check: that the repairer's behaviour through the CLI matches the smoke's
on the 330. The commitment records the served model, the turns and the attempts for that.
