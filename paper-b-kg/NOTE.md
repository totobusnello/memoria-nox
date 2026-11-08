---
title: "What an LLM-built knowledge graph keeps, and what a repair pass against its sources changes"
author: "Luiz Antonio Busnello"
---

Status: working draft, not deposited, not peer reviewed. A data note on one deployment, with
measurements taken on 2026-11-06 and 2026-11-07 on a snapshot of 2026-11-06. Every number with a
decimal, a percentage or a thousands separator has an entry in `PROVENANCE.json`.

## Abstract

An agent memory system extracts a knowledge graph from its corpus with a language model. Each
relation cites the chunk of text it came from. We asked two questions, each under its own public
pre-registration, on the same frozen sample of 300 relations. First, how often does the cited chunk
support the relation as written? Two judges from different model families, a check that each
judge's quote occurs in the chunk, and a blind human grade of 173 rows give 0.913 (274 of 300,
Wilson 95% interval 0.876 to 0.940). Both judges passed both controls; on 60 rows drawn at random
from those the two judges agreed on, their agreement with the human was low (kappa 0.155). Second, does a repair pass that rereads each relation
against its chunk, the offline "dreaming" step recently described for agent memory, fix what is
wrong without losing what is right? Run once with `claude-opus-5-5`, it raised the share of
supported relations among those it left from 0.913 to 0.990, a difference of +7.6 points
(bootstrap 95% interval +4.7 to +10.7). The 180 relations it kept unchanged were
already 0.989 supported, so most of the measured gain came from which relations it chose to leave
alone, not from the content of its rewrites. It also rewrote 87 of the 274 relations that were already supported, 30 of them into a
relation between a different pair of entities, and kept 0.650 of the supported relations unchanged
(0.591 to 0.704). A third of the correct relations came out as a different supported fact, a cost
that a precision figure alone does not show. Three of the human grades behind these figures were
regraded after a spreadsheet error; with the first grades, precision after would be 0.979.

## 1. The graph

The snapshot holds 17,694 relations between 15,620 entities (census `CENSUS-2026-11-06.json`, no
model call). The graph was built almost at once: 17,452 relations were created in July 2026, and 11
since 1 September. Every relation has the same empty extraction method, and 17,682 carry the same
confidence, 0.80, so neither field says anything about a relation.

Predicates are free text. There are 8,359 distinct ones; 6,130 of them are used by a single
relation, which is 73.3% of the predicates and 34.6% of the relations. A closed field,
`relation_reason`, sorts the relations into seven kinds, of which `mentions` and `unknown` hold
most. The evidence comes mostly from one place: of the relations whose chunk still exists, 82.6% cite a chunk from a vault of
legal and corporate documents, 12.3% from workspace documents, and 4.2% from daily notes.

A relation is checkable only if its chunk still exists. In the snapshot, 17,667 relations cite a
live chunk. That set is the population for both studies.

## 2. Is the cited chunk faithful?

**Design** (`paper-b-kg/PREREGISTRATION.md`, tag `paper-b-prereg-v1.0`). A uniform draw of 300
from the 17,667, seeded by the tag's commit. Two judges read each triple and the first 6,000
characters of its chunk: `gemini-2.5-flash-lite` with the prompt of an earlier audit, and
`gpt-5.6-sol`. The prompt states four rules fixed in advance: a triple that inverts the relation is
not supported; a poorer but not inverted predicate is; a placeholder in a worked example is not an
entity; formatting never rejects. A judge's "supported" counts only when the first eight words it
quotes occur in the chunk. The author graded, blind to the judges, every relation the judges
disagreed on (76), every relation both accepted whose chunk carries an exception or example marker
(37), and 60 drawn at random from the rest, 173 rows. A row's final label is the human grade where there is one,
and the two judges' shared label elsewhere.

**Controls.** With the words of each judge's quotes swapped, the citation check rejected every one
(negative citation control); this tests the check that gates the judges, not the judges' reading.
Neither judge accepted any of 30 relations shown with a chunk from another document (mismatched
evidence). Both controls passed for both judges.

**Result.** B-F = 0.913 (274 of 300; 0.876 to 0.940). By evidence source, 229 of the 252 relations
from the document vault are supported. The judges differed in strictness: judge 1 verified 0.857 of
the 300 and judge 2 0.717. The human resolved 71 of the 76 disagreements as supported. Counted
after the reading (not registered, `DISAGREEMENT-DIRECTION-2026-11-07.json`): on the 59 rows only
judge 1 accepted, the human sided with judge 1 on 55; on the 17 only judge 2 accepted, with judge 2
on 16. Judge 2's extra rejections were mostly wrong by the human's reading.

On the 60 random rows, the human's agreement with each judge was kappa 0.155, under the 0.40 the
protocol names as a limit. Those rows were drawn from the ones both judges agreed on and whose chunk
carries no marker, so the figure is the same for both judges and describes their shared label on
the easier rows, not each judge on the 300. The human graded 58 of the 60 as supported, and kappa is
unstable when nearly every row falls in one class. Off the sheet, where the judges' shared label stands, that
label is a fallible reference.

An October audit of an earlier draw of 150 relations gave 0.900. That figure is not an estimate: its rules
were decided on the same sample. The two numbers agree, and this note's is the one with fixed rules.

## 3. What does a repair pass change?

A post by Anthropic on 2026-11-06 describes "dreaming": an offline pass in which a model rereads
its notes against the original record and corrects them. It compares conditions, but on single runs
of a game and on question sets of 24 and 25 items, without intervals. The graph above
keeps, for each relation, the record it was built from, so the claim can be tested here.

**Design** (`paper-b2-kg-repair/PREREGISTRATION.md`, tag `paper-b2-prereg-v1.0`, written and
tagged before Paper B's reading ran). The repairer, `claude-opus-5-5` at effort `medium`, saw each
of the 300 triples with its chunk and nothing else, and chose to keep it, rewrite it, or delete it.
It was given the same four rules the judges use. It ran through the Claude Code command line on the
author's subscription, with the protocol's own system prompt, no tools and structured output; the
unit studied is that configuration. Rewrites went to Paper B's two judges, and the author graded 60
of them blind, without the original triple: the 3 the judges disagreed on, 27 on chunks with a
marker, and 30 at random. The "before" labels are Paper B's final labels.

Two figures were registered as primary. Precision: the share of supported relations among those the
pass leaves, against 0.913 before. Retention: the share of Paper B's supported relations that the
pass keeps unchanged. Retention counts a supported relation that was rewritten as not retained,
even when the rewrite is itself supported, because a rewrite can change the predicate or both
entities. That definition came from an adversarial review before the tag (§4).

**Control.** Shown the 30 relations with another document's chunk, the pass deleted 29, rewrote 1
and kept none. The registered bar was at most 10% kept. It passed.

**Result.**

| | value | 95% interval |
|---|---|---|
| precision before | 0.913 (274 of 300) | 0.876 to 0.940 |
| precision after | 0.990 (283 of 286) | 0.970 to 0.996 |
| difference | +7.6 points | +4.7 to +10.7 (bootstrap) |
| retention, kept unchanged | 0.650 (178 of 274) | 0.591 to 0.704 |
| retention, kept or rewritten into a supported triple | 0.967 (265 of 274) | 0.939 to 0.983 |
| precision had every rewrite been a delete | 0.989 (178 of 180) | 0.960 to 0.997 |

The pass kept 180 relations, rewrote 106 and deleted 14. Of the 26 relations Paper B labels
unsupported, it deleted 5, rewrote 19 (18 into a supported triple) and kept 2: 23 of 26 corrected.
Of the 274 supported, it deleted 9 and rewrote 87: 50 kept the same pair of entities with a new
predicate, 7 reversed the pair, and 30 named a different pair. Every one of those 87 rewrites was
supported by the chunk, two of them by a grade that was regraded (§4).

Precision went up, and most of the gain does not depend on the rewrites: the 180 relations the pass
kept unchanged are 0.989 supported, against 0.990 for all 286 it left. That compares two subsets of
one run. A pass allowed only to keep or delete was not run, and it might keep or delete differently.
What the rewrites add is mostly change to relations that were already right. A third of the correct relations came out different, and one in nine came out as a relation
between other entities in the same passage. Under the lenient definition, retention would read
0.967 and the pass would look nearly free. Under the registered one it is 0.650.

The pass cost the equivalent of US$ 7.93 at list price for the 330 calls and US$ 1.34 for the
judges on the rewrites. Through the subscription, the first was not billed per token.

## 4. How this was run, and what went wrong

Both studies used the same order: tag, then each step's public commitment (counts and hashes, never
text) before the next step, with scripts that refuse to run otherwise and offline tests with
mutations. The private data (triples, entity names, chunk text) stayed outside the repository.

Before Paper B2's tag, Codex (`gpt-6-astra`) and DeepSeek (`deepseek-v4-pro`) reviewed the protocol
and scripts at the author's request. Codex asked to block the tag on three points that held: the
retention figure counted a substitute fact as the original, a rewrite without a label would have
shrunk the "before" set, and a run with no rewrites could not finish. All three were fixed before
the tag, with the rest of both reviews recorded in the protocol's §9.

Three deviations after the tags are on record. In Paper B, one judge verdict could not be parsed
(a markdown escape copied into its quote), so the JSON reader gained a last-resort repair. Also in
Paper B, the judges' commitment was corrected to count the cost of every verdict, not only the last
run. In Paper B2, the graded sheet came back as a spreadsheet file in which the chunk cells of three
rows were empty. The author confirmed grading those rows without seeing the chunk and regraded them
from a plain-text file; all three grades changed from not supported to supported. The committed
grades are the second ones. Had the first grades stood (computed after the reading, not registered,
`paper-b2-kg-repair/REGRADE-SENSITIVITY-2026-11-07.json`), precision after would be 0.979 (280 of 286), the difference
+6.6 points (+3.6 to +9.8), and lenient retention 0.960; strict retention would not change, since
all three are rewrites. The text check that caught it compares the returned file with the written
one; it cannot see what a grader saw on screen.

## 5. Limits

- One graph, one sample of 300, one repair run, one configuration of one model. Nothing here
  measures the repairer's stability across runs, other models, or repeated passes.
- "Supported by the chunk" is not "true", "current" or "consistent across documents". Neither study
  measures completeness, duplicates or whether an agent answers better from the graph.
- The labels come from two fallible judges and one author who graded both sheets. The intervals do
  not carry their error, and kappa with the human was low.
- With 26 unsupported relations, the correction rate (23 of 26) is a description, not an estimate
  that transfers.
- The population excludes relations whose chunk is gone. The private data's hashes let its holder
  check integrity; they do not allow public reproduction.

## 6. What it means for memory systems

The graph's citations are mostly faithful, and its structure is weak: a third of its relations use
a predicate no other relation uses. A repair pass against the source worked as a filter here: it corrected
23 of the 26 unsupported relations and kept none of the 30 shown with the wrong chunk. It also
rewrites freely, so a system that runs one should measure retention of the original facts as well
as the precision of what remains. In this run, the relations it kept or deleted already account for
nearly all of the precision gain. Whether a pass allowed only to keep or delete would have kept the
87 correct relations this one rewrote was not tested.

## Availability

Protocols, scripts, tests, commitments and readings are in the public repository
(`paper-b-kg/`, `paper-b2-kg-repair/`); the tags are `paper-b-prereg-v1.0` and
`paper-b2-prereg-v1.0`. The frozen sample and the human grades are private, with their hashes in the
commitments.
