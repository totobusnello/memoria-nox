# Paper B: what an LLM-extracted knowledge graph keeps. Pre-registration v1.0

Written 2026-11-06, after the structural census (`CENSUS-2026-11-06.json`) and before any sample is
drawn or any model is called for this paper. Nothing here is fixed until the tag
`paper-b-prereg-v1.0` is on the public main branch. The author approved the complete design on
2026-11-06 («melhor mais completa») and the tag on 2026-11-07 08:22 BRT («pode subir e taguea»).
The tag `paper-b-prereg-v1.0` fixes this text and the scripts it names; any later change is a
dated deviation.

**Revised 2026-11-07, with the scripts.** Writing and testing the scripts offline (`b-test.py`,
synthetic data, no draw, no model call) found two points the draft could not run as written and
three it left unstated; each is marked **[2026-11-07]** below. The author decided the two open
points on 2026-11-07 08:05 BRT («1. pode usar 2. ok»): judge 2 is `gpt-5.6-sol` (§4), and the
marker rows of the sheet stay on the chunk (§5). Judge 2's price moves the spend cap (§7) to
US$ 10, which he approved with the tag («pode subir»).

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
the host is six days. **[2026-11-07]** A private copy of the gz was taken from the host on
2026-11-07 and its sha256 checked equal to the one above (`~/Backups/paper-b-snapshot-2026-11-06/`,
mode 700, outside every repository), so the freeze no longer depends on the host's retention.
`b-freeze.py` refuses a file whose name or sha256 differs.

Population: every row of `kg_relations` whose `evidence_chunk_id` resolves to a row of `chunks` in
that snapshot (17,667 in the census). Superseded relations: none exist in the snapshot.

## 3. Sample

Uniform without replacement, n = 300, over the population ordered by `kg_relations.id`. Seed: the
integer value of the first eight hexadecimal digits of the tag commit's sha, so the draw cannot be
chosen before the protocol is public. At p = 0.90 the Wilson 95% half-width is about 3.4 points.

## 4. Judges and the citation check

Each sampled relation goes to two judges from different model families, temperature 0, with the
triple (source entity, predicate, target entity) and the evidence chunk. **[2026-11-07]** As in
October, a judge sees the chunk's first 6,000 characters; 4 of the 17,667 population chunks are
longer (the longest 15,517). The human sheet shows the same 6,000, so the human never sees less
than the judges:

- **Judge 1:** `gemini-2.5-flash-lite`, the October prompt (`audits/2026-10-22-kg-s1-precision.py`),
  so B-F is comparable in method to the October audit.
- **Judge 2:** `gpt-5.6-sol` (OpenAI), chat completions, the same prompt, JSON response.
  **[2026-11-07]** The draft named `gpt-6-luna`. That model answers only through OpenAI's
  Decisions API, which returns probabilities for predicates and no text
  (`audits/2026-10-26-bounded-judge.py`), so it cannot copy the eight-word quote this section
  requires and could never produce a verified label. No temperature is sent, as in the
  repository's working call to this model (`eval/brief-action-probe/probe/llm.py`); the model the
  provider served and its token counts, reasoning included, are recorded per call. The ledger
  prices it at US$ 5 per million input tokens and US$ 30 per million output tokens, the list price
  without the promotion that ends on 2026-11-30, so it can over-count the spend but not
  under-count it.

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
   October enumeration for P1 and P3. **[2026-11-07]** October applied the markers to the
   judge's *quote*; this protocol applies them to the *chunk* the judges saw (author, 2026-11-07,
   «2. ok»). Measured on the population (no draw):
   3,900 of the 17,667 chunks carry a marker (22.1%: exception 3,194, example 607, both 99), so
   item 2 alone would put about 55 to 65 of the 300 on the sheet, and the sheet would hold about
   130 to 150 rows. Applied to the quote, as in October, it would hold a handful;
3. 60 relations drawn at random, with seed + 1, from the relations not already in 1 or 2.

Rows are shuffled with seed + 2. The sheet's sha256 is committed before it is graded, and the
grades are committed (`HUMAN-COMMITMENT.json`) before the reading.

## 6. Estimate, controls and reading

**Final label.** The human grade where there is one; otherwise the label both judges agree on
(off the sheet they agree by construction, because every disagreement is on it). **[2026-11-07]**
A judge that fails a control does not count: off the sheet the label is the passing judge's. If
both fail, no row off the sheet has a final label, and B-F is estimated on the 60 random rows the
human graded, with its own Wilson interval, and stated as such.

**Primary estimate.** B-F = share of the 300 with a final label of supported, with a Wilson 95%
interval. There is no hypothesis test and no threshold. The note reports the figure and its interval.

**Controls.** Each must pass for its judge's labels to enter the final label. A judge that fails one
is reported, and its labels are replaced as the final-label rule above states. **[2026-11-07]** The
two words of the negative control are drawn with seed + 4; a quote with no two different words is
skipped and counted. A judge with no verified quote to test fails the control. "Accepts" in the
mismatched control means a verified label (claim and quote check) on the other document's chunk;
the bare claim rate is reported beside it.

| control | measured | passes when |
|---|---|---|
| citation check, negative | each verified quote, with two words swapped, tested against its own chunk | rejected in at least 95% |
| mismatched evidence | 30 sampled relations (seed + 3) shown with a live chunk from a different document | judge accepts at most 10% |
| human agreement | Cohen's kappa, human against each judge, on the 60 random rows | reported; kappa below 0.40 is stated as a limit of that judge |

**Reported, not interpreted.** Judge 1's and judge 2's verified and claimed rates alone; a claimed
ceiling, the share of the 300 whose final label is supported or that at least one judge claimed to
support with a quote that failed the check, never the estimate (**[2026-11-07]** October's ceiling
was the P2 rows read by hand; here P2 is a rule in the prompt and on the sheet, so the rows it
would restore are already in the estimate, and the ceiling bounds what the citation check costs);
the human's rate by sheet origin; the final rate by `relation_reason` and by evidence bucket of the
census.

## 7. Order and private data

Tag `paper-b-prereg-v1.0`, then:

1. **Freeze** (`b-freeze.py`): draw, then copy the 300 + 30 rows and their chunks from the
   snapshot to `~/Backups/paper-b-freeze-<date>/` (mode 700). Commit `FREEZE-COMMITMENT.json`,
   which holds counts, the seed and hashes, never text.
2. **Judges** (`b-judge.py`): both judges on the 300 and on the 30 mismatched; cost cap US$ 10 for
   the two together (**[2026-11-07]**, was US$ 1, set for two flash-lite-class judges; at the
   ledger's prices judge 2 costs about US$ 2 to 8 for 330 calls averaging 2,351 characters of
   chunk, depending on its reasoning tokens), abort above it. Commit `JUDGES-COMMITMENT.json` (calls, cost, the models the
   providers served, hashes; no label and no rate) **[2026-11-07]**.
3. **Human sheet** (`b-human.py make`, then `commit`): commit `SHEET-COMMITMENT.json` (the sheet's
   hash), grade, then commit `HUMAN-COMMITMENT.json`.
4. **Reading** (`b-read.py`): `READING-<date>.json`, then the note.

`b-test.py` exercises all four offline, on a synthetic database with fake judges and a throwaway
git repository, including mutations each check must catch.

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

## 10. Deviations after the tag

**1. 2026-11-07, judges.** Of the 660 judge calls, judge 1's verdict on one sampled relation could
not be read: the model copied into its quote a markdown escape from the chunk (`R\$`), which is not
a valid JSON escape, and every reading of the October parser failed; a rerun at temperature 0
returned the same text. `jload` in `b-common.py` gained a last attempt, run only when every earlier
reading fails, that doubles a backslash not starting a valid JSON escape, so the string keeps it
literally and the P4 check strips it as before. No verdict that was already read changes (the 659
others were cached before the change), and the label rules are untouched. The change is tested in
`b-test.py`, and the judges' commitment records the new hash of `b-common.py`.

