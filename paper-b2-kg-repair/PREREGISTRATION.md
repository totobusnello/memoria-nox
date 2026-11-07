# Paper B2: does a repair pass against the source fix an LLM-extracted knowledge graph? Pre-registration DRAFT v0.1

Written 2026-11-07, after Paper B's human grades were committed (`paper-b-kg/HUMAN-COMMITMENT.json`,
#682) and **before Paper B's reading** (`b-read.py`). Nothing here is fixed until the tag
`paper-b2-prereg-v1.0` is on the public main branch. The author opened this study on 2026-11-07
(«o ponto 3 pode virar um paper interessante! e vamos seguir sua recomendacao») and chose the
repairer (Claude Opus 5.5) and the order (this tag before B's reading).

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
repair pass leave supported (kept, or rewritten into a supported triple)?

The two answer different costs: a pass that deletes everything doubtful raises precision and loses
retention. Neither number alone says the pass helps. The post's own wiki case (41 of 57 facts kept
before the instructions changed) is a retention failure, which is why retention is primary here.

Reported beside them, not interpreted: the correction rate (of the relations B labels unsupported,
the share deleted or rewritten into a supported triple) and the damage rate (of those B labels
supported, the share deleted or rewritten into an unsupported triple).

## 2. Sample and the "before" labels

No new draw. The 300 relations and the 30 mismatched pairs frozen by Paper B
(`FREEZE-COMMITMENT.json`, seed 3335023133), with the same chunks, cut at the same 6,000
characters. The "before" label of each relation is Paper B's final label, under Paper B's rules,
unchanged.

Precision is limited by how many relations B labels unsupported. If B-F is near October's 0.900,
about 30 of the 300 are unsupported, and the correction rate's Wilson 95% interval is about ±17
points. This protocol does not enlarge the sample, because no relation outside the 300 has a label.
The note states the interval it gets.

## 3. The repair pass

**Repairer:** `claude-opus-5-5` (Anthropic), Messages API. Its family differs from both of Paper
B's judges (Google, OpenAI). The model takes no temperature and its thinking cannot be turned off;
effort is set explicitly to `medium` (the model's default), and the provider's served model and
token counts are recorded per call. With no temperature the output is not repeatable: each relation
is asked **once**, the answer is cached, and a relation is asked again only after a transport error
or an unreadable answer, which is counted. No server-side fallback to another model: a refusal is
counted, and the relation is kept unchanged (the conservative action).

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

**Disclosure.** The repairer is given the rubric the judges apply. The pass is therefore optimised
toward the measuring rule, which is what a repair pass against a stated standard does. The human
grades on the rewrites (§4) are the check against a pass that satisfies the judges without
satisfying the source.

## 4. Labels after the pass

- `keep`: the relation keeps its Paper B final label.
- `delete`: the relation leaves the graph; it counts against retention if B labels it supported.
- `rewrite`: the new triple, with the same chunk, goes to both of Paper B's judges with Paper B's
  prompt, rules and quote check (`b-common.py`, as tagged by Paper B). A judge that failed one of
  Paper B's controls does not count, as in Paper B.

**Human sheet for the rewrites.** Blind, graded by the author, who sees the new triple and the chunk
and no verdict, no quote, no original triple and no "before" label. It holds every rewrite on which
the two judges' verified labels disagree, and 30 rewrites drawn with seed + 1 from the rest (all of
them if fewer). Rows shuffled with seed + 2. The seed is the integer value of the first eight
hexadecimal digits of the `paper-b2-prereg-v1.0` tag commit. Final label of a rewrite: the human
grade where there is one, otherwise the label both judges agree on.

## 5. Estimates, controls and reading

**Primary.** B2-P after the pass against B-F before, as a paired difference over the 300 with a
bootstrap 95% interval (10,000 resamples of relations, seed + 3); B2-R with a Wilson 95% interval.
No hypothesis test and no threshold: the note reports both figures and their intervals.

**Controls.**

| control | measured | passes when |
|---|---|---|
| positive: the pass must act on wrong evidence | the 30 mismatched pairs from Paper B, each relation shown with a chunk from a different document | the repairer keeps at most 10% unchanged |
| repairer quote check | share of `keep` and `rewrite` answers whose quote passes the alphanumeric check | reported |
| human against judges on rewrites | Cohen's kappa on the 30 random rewrite rows | reported; below 0.40 is stated as a limit |

If the positive control fails, B2-P and B2-R are reported as a failed instrument and not
interpreted, as in Paper D.

**Reported, not interpreted.** Counts of each action; correction and damage rates; the actions by
Paper B's `relation_reason`, evidence bucket and sheet origin; the cost.

## 6. Order, cost and private data

Tag `paper-b2-prereg-v1.0`. After the tag Paper B's reading may run: nothing in this protocol
depends on its result, and the repairer never sees a label. Then:

1. **Repair** (`b2-repair.py`): the 300 and the 30 mismatched. Commit `REPAIR-COMMITMENT.json`
   (calls, cost, counts per action, served model, hashes; no triple and no text).
2. **Judges on rewrites** (`b2-judge.py`): commit `B2-JUDGES-COMMITMENT.json`.
3. **Sheet** (`b2-human.py make`, then `commit`): `B2-SHEET-COMMITMENT.json`, grade,
   `B2-HUMAN-COMMITMENT.json`.
4. **Reading** (`b2-read.py`): `READING-<date>.json`, then the note.

Each script refuses to run unless the previous commitment is on the public main branch and
byte-equal to the private copy, and the reading also requires Paper B's four commitments. Triples,
entity names and chunk text stay in `~/Backups/paper-b2-repair-<date>/` (mode 700) and are sent
only to the repairer and the two judge APIs.

**Cost cap: US$ 20** for the repair and the rewrite judging together, abort above. Estimate at the
list prices (US$ 4 per million input and US$ 20 per million output tokens for the repairer): about
1,700 input tokens per call, or US$ 2.30 for 330 calls; output is mostly thinking, which effort
`medium` does not bound, so 500 to 2,000 output tokens per call gives US$ 3.30 to 13.20. Rewrite
judging costs at most what Paper B's judges cost per call (US$ 4.49 for 660). **[open]** A paid
smoke on five relations drawn from outside Paper B's 330 (discarded afterwards) would measure the
output tokens before the tag; it needs the author's approval.

## 7. What a result can and cannot say

One graph, one sample of 300, one repairer, one pass, and one chunk per relation: a relation whose
support lives in another document is deleted by a pass that sees only its cited chunk, and Paper B
would have labelled it unsupported too, so the two measures agree on what "supported" means. The
result says whether this pass, on this graph, moves precision and at what retention. It says
nothing about repeated passes, about building new representations (the post's wikis), or about
whether an agent answers better from the repaired graph.

## 8. Open before the tag

1. Cap (US$ 20) and the smoke (five relations, under US$ 1).
2. Effort `medium` or `low` for the repairer.
3. The scripts `b2-repair.py`, `b2-judge.py`, `b2-human.py`, `b2-read.py` and their offline test
   `b2-test.py` (synthetic data, fake repairer, mutations), written and green before the tag.
4. Adversarial voices on this text: only if the author asks for them.
