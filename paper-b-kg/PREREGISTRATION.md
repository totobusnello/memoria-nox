# Paper B: what an LLM-extracted knowledge graph keeps. Pre-registration (DRAFT, not fixed)

Written 2026-11-06, after the structural census (`CENSUS-2026-11-06.json`) and before any sample is
drawn or any model is called for this paper. Nothing here is fixed until the tag
`paper-b-prereg-v1.0` is on the public main branch. The author approved the complete design on
2026-11-06 («melhor mais completa»); the tag, the draw and every paid call wait for his ok.

## 1. Questions

**B-S (structure, descriptive).** What the graph holds, where its evidence comes from, and when it
was built. Answered by the census on the frozen snapshot; no hypothesis, no model call.

**B-F (faithfulness, estimated).** Of the relations whose evidence chunk still exists, what share
are supported by that chunk, as the triple is written? This is the one inferential figure of the
note.

The October figure (0.900, 135 of 150, `audits/2026-10-23-kg-s1-quatro-principios.md`) is not an
estimate of B-F: its four adjudication principles were decided from the same sample, which that
audit declares spent. B-F is measured on a fresh sample, with those principles fixed in advance.

## 2. Population and snapshot

The daily snapshot `daily-main-main-20261106030002-…db.gz`, sha256
`14f5000a1b4dfe6cd0a0f78e57c0295d52d39049ebeaed1fc707a961af8dac4c` (the census's). Its retention on
the host is six days, so the freeze (§7) must run by 2026-11-11.

Population: every row of `kg_relations` whose `evidence_chunk_id` resolves to a row of `chunks` in
that snapshot (17,667 in the census). Superseded relations: none exist in the snapshot.

## 3. Sample

Uniform without replacement, n = 300, over the population ordered by `kg_relations.id`. Seed: the
integer value of the first eight hexadecimal digits of the tag commit's sha, so the draw cannot be
chosen before the protocol is public. At p = 0.90 the Wilson 95% half-width is about 3.4 points.

## 4. Judges and the citation check

Each sampled relation goes to two judges from different model families, temperature 0, with the
triple (source entity, predicate, target entity) and the full evidence chunk:

- **Judge 1:** `gemini-2.5-flash-lite`, the October prompt (`audits/2026-10-22-kg-s1-precision.py`),
  so B-F is comparable in method to the October audit.
- **Judge 2:** `gpt-6-luna` (OpenAI), the same prompt.

The prompt adds, before any call, the four October principles as explicit rules: a triple that
inverts the relation does not count as supported (P1); an impoverished but not inverted predicate
does (P2); a placeholder inside a worked example is not an entity (P3); formatting never rejects
(P4).

A judge's "supported" counts only if its quote, the first eight words of the supporting sentence,
occurs in the chunk under the alphanumeric check
(`audits/2026-10-23-kg-s1-recheck-conferidor.py`, the P4 rule). A judge's label is *verified* when
both hold.

## 5. Human adjudication

One blind sheet, graded by the author, who sees the triple and the chunk but no judge verdict and no
quote. It holds:

1. every relation where the two judges' verified labels disagree;
2. every relation that both judges verify and whose chunk carries an exception marker (`exceto`,
   `except`, `unless`, `other than`) or an example marker (`Ex:`, `e.g.`, `por exemplo`), the
   October enumeration for P1 and P3;
3. 60 relations drawn at random, with seed + 1, from the relations not already in 1 or 2.

Rows are shuffled with seed + 2. The sheet's sha256 is committed before it is graded, and the
grades are committed (`HUMAN-COMMITMENT.json`) before the reading.

## 6. Estimate, controls and reading

**Final label.** The human grade where there is one; otherwise the label both judges agree on.

**Primary estimate.** B-F = share of the 300 with a final label of supported, with a Wilson 95%
interval. There is no hypothesis test and no threshold. The note reports the figure and its interval.

**Controls.** Each must pass for its judge's labels to enter the final label. A judge that fails one
is reported, and its labels are replaced by the human's on every row it would have decided.

| control | measured | passes when |
|---|---|---|
| citation check, negative | each verified quote, with two words swapped, tested against its own chunk | rejected in at least 95% |
| mismatched evidence | 30 sampled relations (seed + 3) shown with a live chunk from a different document | judge accepts at most 10% |
| human agreement | Cohen's kappa, human against each judge, on the 60 random rows | reported; kappa below 0.40 is stated as a limit of that judge |

**Reported, not interpreted.** Judge 1's and judge 2's verified rates alone; the substantive ceiling
(P2 rows the judges rejected with an empty quote, counted as a ceiling, never as the estimate, as in
October); the final rate by `relation_reason` and by evidence bucket of the census.

## 7. Order and private data

Tag `paper-b-prereg-v1.0`, then:

1. **Freeze:** draw, then copy the 300 + 30 rows and their chunks from the snapshot to
   `~/Backups/paper-b-freeze-<date>/` (mode 700). Commit `FREEZE-COMMITMENT.json`, which holds
   counts, the seed and hashes, never text.
2. **Judges:** both judges and both controls; cost cap US$ 1, abort above it.
3. **Human sheet:** commit its hash, grade, then commit `HUMAN-COMMITMENT.json`.
4. **Reading:** `READING-<date>.json`, then the note.

Each script refuses to run unless the previous commitment is on the public main branch and
byte-equal to the private copy, as in Paper D. The triples, entity names and chunk text are private:
they stay in the backup directory and are sent only to the two judge APIs. Only counts, rates and
hashes enter the repository.

## 8. Descriptive measurements without a model

Computed by the census script on the same snapshot and reported as description:

- **Predicate usability.** For each `relation_type` used at least twice, the share of its relations
  that carry its most common `relation_reason`. If free predicates do not line up with the closed
  enum, the graph can be queried by `relation_reason` and evidence pointer, not by predicate.
- **What search serves.** How many KG triples the search endpoint attaches per query, measured on
  the canary probe's own fixed queries (no private query text), with the evidence bucket of each
  served triple.

## 9. What a result can and cannot say

B-F says how often a cited chunk supports its triple in this graph, frozen in July and dominated by
the document vault. It does not say how faithful a new extraction would be, nor how useful the graph
is to an agent: §8 describes reach and form, and no consumer study is part of this protocol.
