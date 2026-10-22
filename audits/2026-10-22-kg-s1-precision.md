# KG S1: sampled faithfulness, and what the graph is actually a graph of

ROADMAP v6 item 4, step S1, 2026-10-22. The gate before paying an LLM to extract over the ~93% of
the corpus the graph does not cover. Read-only: `mode=ro`, nothing written to the database.

Every relation carries `evidence_chunk_id`, so precision here is **faithfulness** — does the cited
evidence support the triple as written? That is the question that decides the spend: extracting more
of something unfaithful buys more unfaithfulness.

## 1. Sample

Uniform over the relations whose evidence chunk still exists, n=150, seed `20261022` recorded so the
draw is reproducible. Population: 17,753 relations; 2 with no `evidence_chunk_id`, 85 whose evidence
chunk is gone (counted and excluded, not silently dropped), 17,666 eligible.

The judge (`gemini-2.5-flash-lite`) had to copy the **first eight words** of the supporting sentence,
verified by substring. On this same corpus, earlier today, a judge asked for a free-length "verbatim"
span produced one that was not in the source 34.5% of the time — an unverified claim of support is
not evidence of support.

## 2. 🔴 The verification predicate had to be calibrated, and the first one was wrong

The strict check (accent- and whitespace-insensitive) rejected 32 of the 137 claimed supports. Before
reporting that, each rejection was inspected: **20 of the 32 match under a markdown- and
punctuation-insensitive comparison.** KG evidence lives in SEC filings and contracts — pipe tables,
`**bold**`, curly quotes — and the strict predicate was failing on formatting, not on fabrication.

Applying the looser rule only to the failures would have been selection, so it was recomputed over
all 150. And the looser rule was itself controlled: each quote was tested against a **randomly chosen
other chunk**, where a criterion that verifies nothing would accept freely.

```
negative control (quote vs a RANDOM chunk, n=137)
  false positives, strict criterion:  0
  false positives, loose criterion:   0
```

| criterion | precision | CI95 | |
|---|---|---|---|
| **loose, calibrated** (markdown-insensitive) | **0.833** | [0.774, 0.893] | the number |
| strict (whitespace only) | 0.700 | [0.627, 0.773] | too strict here: 20 of its 32 rejections are formatting |
| no check at all | 0.913 | — | what taking the judge at its word would have reported |

The judge's word alone inflates precision by **8 points**; a miscalibrated check deflates it by
**13**. Both directions are available to anyone who does not look.

## 3. Result

**Faithfulness 0.833 [0.774, 0.893]** — roughly one triple in six is not supported by its own cited
evidence.

| `relation_reason` | n | supported | p |
|---|---|---|---|
| `depends_on` | 31 | 29 | **0.935** |
| `unknown` | 52 | 44 | 0.846 |
| `mentions` | 60 | 46 | **0.767** |
| `derived_from` | 4 | 4 | 1.000 |
| `opposes` | 2 | 1 | — |
| `extends` | 1 | 1 | — |

The weakest bucket is also the biggest: `mentions` is 8,736 of 17,753 relations (49%) and scores
0.767. The 25 failures break down as 12 fabricated quotes, 10 `relacao_errada` (the evidence states a
different relation, sometimes the opposite — one triple asserts `grants rights` over a passage that
explicitly denies granting any), 2 `entidade_ausente`, 1 `so_co_ocorrencia`.

## 4. Two structural facts that matter more than the precision

**The predicate slot is free text, not a vocabulary.** 8,359 distinct `relation_type` values over
17,753 relations, and **6,130 of those types are used exactly once**. In the sample, **59 of 150
(39.3%)** use a predicate that appears once in the entire graph. A predicate used once cannot be
queried, filtered or aggregated — it can only point. (`relation_reason` *is* the closed 7-value enum
and is populated; `relation_type` is the free one.)

**The graph is mostly a graph of legal documents, not of engineering memory.**

| evidence comes from | n | |
|---|---|---|
| `memory/mac-docs/` | 112 | **74.7%** |
| `shared/` | 23 | 15.3% |
| `memory/` | 14 | 9.3% |
| `shared/imports/` | 1 | 0.7% |

The top evidence files are SEC 6-K filings, an SPA, a settlement agreement, term sheets. The entities
are `Variable Rate Transaction`, `Registration Rights Agreement`, `Preço de Aquisição`, `Cláusula
9.14`. Expanding coverage would mostly deepen a contract graph.

Two more, noted: **98.7% of the graph (17,517 relations) was created in 2026-07** — it is one frozen
batch, with 4 relations added since September. And `extraction_method` is **NULL in 100%** of rows,
the same never-written-column pattern that closed item 11 (`confidence`, `provenance_kind`).

## 5. What S1 decides

**Do not buy broad LLM extraction yet.** Not because 0.833 is bad — for a graph used as an *address*
into chunks it is usable, and the roadmap already frames item 4 as "aponta chunks, não os substitui".
The reasons are the other two:

1. **Extraction would multiply hapax predicates.** 39.3% of relations already carry a predicate seen
   once. Ten times the volume of an unqueryable predicate is ten times the storage and the same zero
   queries. Close the vocabulary first, or drop the pretence that the predicate is queryable and
   index on `relation_reason` (which *is* closed and populated) plus the evidence pointer.
2. **The target corpus is undecided.** Three quarters of the graph is the document vault. Extracting
   over "the uncovered 93%" means something different depending on whether the product is a contract
   graph or an agent-memory graph, and nothing in the roadmap says which.

0.833 is also the ceiling an address function has to live with: one pointer in six lands on evidence
that does not say what the triple claims. That is tolerable when the consumer reads the chunk, and
not tolerable when the triple is served as a fact. Today the search serves 3 triples per query.

**Not done:** faithfulness is not the same as coverage or usefulness — this measures whether what is
there is true to its evidence, not whether what is missing matters. The judge is
`gemini-2.5-flash-lite` throughout and its agreement with a human on a sample has not been measured.
Test residue is real but trivial (5 entities, 7 relations: `test_a`, `test_b`, `alpha`, `beta`,
`Alpha`) and was left in place rather than deleted from production on my own initiative.

**Artifacts.** `audits/2026-10-22-kg-s1-precision.py`, data
`audits/out/kg-s1-precision-2026-10-22.json` (all 150 rows with judgements, quotes and both
criteria). Raw run on the VPS in `/root/medicoes/2026-10-22-kg-s1/`.
