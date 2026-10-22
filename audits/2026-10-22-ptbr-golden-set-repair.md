# The PT-BR golden set had rotted; repairing it, and what the oracle could and could not filter

ROADMAP v6 item 9, 2026-10-22. Read-only throughout: the production database was opened with
`mode=ro` and every probe went straight to SQLite, never through `/api/search` or the CLI — a search
through those writes `search_telemetry` and bumps `access_count`, which is to say it feeds the very
ranking signals a golden set exists to score.

## 1. The set already existed, and 50% of it pointed at nothing

`eval/golden-queries.jsonl`: 66 Portuguese queries with `category`, `difficulty` and
`expected_chunk_ids`, imported from the VPS "for paper pre-registration" (`f75d186`). Checked
against the served corpus:

| state | queries | |
|---|---|---|
| gold intact | 6 | 9.1% |
| gold partial (some ids alive) | 12 | 18.2% |
| **gold entirely dead** | **33** | **50.0%** |
| never had gold (`[]`) | 15 | 22.7% |

**61 of the 85 cited chunk ids (71.8%) no longer exist.** Eighteen of 66 queries were still usable
as positives, and none of the 66 had ever been through the oracle filter the roadmap names as the
gate.

🔑 **The cause is structural, and it condemns rebuilding the same way.** The gold was keyed by chunk
id, and every re-ingest mints new ids — the April static-import removal, the 15/10 re-embed, and
others. An id-keyed ruler decays at each re-ingest *in silence*: the file still parses, still looks
valid, and scores against ghosts. Writing 50 fresh queries with `expected_chunk_ids` would buy the
same rot again.

So the repair keys gold by **(source_file, verbatim anchor)**, resolved to ids at run time by
`eval/resolve-gold-anchors.py`, which exits non-zero when an anchor fails to resolve. Anchors break
too — the difference is that a broken anchor announces itself.

## 2. The oracle filter

A query earns its place only if the answer is in the corpus and *not already in the model's head*:

> accept chunk `c` as gold for query `q` iff `answer(q | c)` is correct **and** `answer(q | nothing)`
> is not.

Without the second leg, a golden set scores retrieval on questions the model answers from general
knowledge, and the retriever gets credit for nothing.

**Candidate pool.** BM25 top-40 ∪ vector-KNN top-40 per query (65–80 distinct chunks). The depth is
deliberate: the set is evaluated at rank 10, so drawing gold from a top-10 pool would guarantee a
high score by construction. The bias that remains is stated rather than hidden — a query whose
answer this index cannot surface within 40 ranks on either leg finds no gold here, so the set cannot
measure what the index is wholly blind to.

**The judge is checked mechanically.** It must copy the supporting span *verbatim* from the chunk,
and the span is verified by accent-folded, whitespace-collapsed substring match. A judgement whose
quote is not in the chunk is discarded, not trusted. This is the positive control on the judge.

## 3. Result

| verdict | queries | |
|---|---|---|
| **accepted** (gold found and verified) | **48** | 72.7% |
| quote unverified | 11 | 16.7% |
| no source in pool | 6 | 9.1% |
| negative, unvalidated (see §5) | 1 | 1.5% |

85 gold chunks over 48 queries. Per category, accepted/total: decision 6/6, security 5/6,
procedure 10/13, entity 8/11, concept 10/15, temporal 7/10, cross-agent 2/4.

**The anchor key works.** Resolving the 85 anchors against today's corpus: **82 resolved exactly, 0
unresolved**, 3 ambiguous. The ambiguity is not a defect of the anchor — it is the entity-file
format, where `ingestEntityFile()` produces one `frontmatter` and one `compiled` chunk per file
whose text overlaps by construction, so one anchor legitimately matches two chunks of the same file.
The resolver reported it instead of picking one.

## 4. 🔴 The judge called 34.5% of its "verbatim" quotes verbatim, and they were not

Of 172 judgements, 139 claimed the chunk answers the question. Of those 139, **48 (34.5%) quoted a
span that is not in the chunk.** Inspecting them, the quotes do not diverge at the margin: they
match for the first 13–53 characters and then drift into paraphrase, and one splices two separate
passages together with a `\n---\n` of its own invention.

Without the mechanical check, those 48 judgements would have entered the set as grounded gold. The
check cost one substring comparison per judgement.

**This is the generalisable part:** asking a model to quote its evidence is worth nothing unless the
quote is verified against the source. The request alone does not make the quote real.

## 5. 🔴 An LLM judge cannot hold a negative

Q68 — *"como resolver Sentence Transformer Issue 62028"* — is labelled `negative`. It is a
false-premise trap: Issue 62028 is the OpenClaw gateway fratricide, and has nothing to do with
Sentence Transformers. The positive oracle **accepted it on three chunks**.

A second pass was run with a prompt that explicitly asks the model to check the premise before
answering. It returned `premissa_confere: true` on all three — and on two of them its own stated
reason reads, verbatim: *"Embora a pergunta mencione 'Sentence Transformer', o trecho foca em
'OpenClaw gateway fratricide — Issue #62028'."* The model noticed the false premise, wrote it down,
and set the flag to true anyway.

**The prose and the field disagreed, and only the field would have been read.** Negatives therefore
cannot be validated by this instrument at all. They need a construction that is true by design — a
query over an entity mechanically verified absent from the corpus — or a human author. This is a
direct input to ROADMAP item 8 (abstention), which depends on negatives: item 8 cannot source them
from an LLM judge.

## 6. What the counterfactual leg actually did

Honest accounting: **the counterfactual leg rejected zero queries.** 58 of 66 closed-book answers
were `NAO SEI`, because the corpus asks about internal systems the model cannot know.

It is not, however, inert. At the *chunk* level it fired 6 times, and those candidates were excluded
from gold — for instance Q67 (*"qual a regra sobre rsync delete"*) had three candidates, two of them
flagged as already answered without any source, and only the third became gold. The leg discriminates
where the question is generic; on this set most questions are not. Two accepted queries are generic
enough to deserve a second look by hand: Q101 (*"o que acontece se o disco enche"*) and Q104 (*"como
medir se a busca está boa"*).

## 7. Status and what is not done

`eval/golden-queries-v2.jsonl` carries all 66 queries with their status, anchors, and the oracle's
provenance (model, date, closed-book answer, pool size, judgements). **v1 is left untouched**: it is
the registered artifact, and the repair is offered beside it, not over it.

Not done, and named so it is not mistaken for done:

- **17 queries are not usable as positives** (11 quote-unverified, 6 no-source-in-pool). The
  quote-unverified ones are not necessarily bad queries — they need a second judging pass.
- **The set has one negative, and it is wrong.** Item 8 needs a real negative pipeline.
- **No retrieval has been scored yet.** This produced the ruler, not a measurement.
- Nothing published depends on this file. The Wave A set of 100 queries in the paper (§5.1) is a
  separate artifact, of which the paper itself records that "no record documents how the 100 queries
  were selected".

**Artifacts.** Pool builder `audits/2026-10-22-gold-pool.py`, oracle `audits/2026-10-22-gold-oracle.py`,
resolver `eval/resolve-gold-anchors.py`, resolution report
`audits/out/resolve-gold-anchors-2026-10-22.json`. Raw run on the VPS in
`/root/medicoes/2026-10-22-gold/`. Oracle model `gemini-2.5-flash-lite`. Production untouched,
nothing written to the database.
