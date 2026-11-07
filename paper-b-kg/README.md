# Paper B: what an LLM-extracted knowledge graph keeps

A descriptive data note (PLANO.md, row B). Status: started 2026-11-06; no note text yet.

The object is the knowledge graph the memory system built by LLM extraction: what it holds, where
its evidence comes from, and when it was built. The October audits measured it once
(`audits/2026-10-22-kg-s1-precision.md`, `audits/2026-10-23-kg-s1-quatro-principios.md`). This
folder re-measures the structure on a frozen snapshot, so the note cites one dated census instead of
numbers spread across audits.

| file | what |
|---|---|
| `b-census.py` | structural census, no model call, read-only on a snapshot; counts and shares only, evidence sources in fixed buckets, never raw paths |
| `CENSUS-2026-11-06.json` | the census on the daily snapshot of 2026-11-06 03:00 UTC (name and sha256 inside) |
| `PREREGISTRATION.md` | DRAFT, not fixed: faithfulness on a fresh uniform sample of 300, two judge families, the October principles fixed in advance, blind human adjudication; fixed only by the tag `paper-b-prereg-v1.0` |
| `b-common.py` | what the scripts share: the draw, the October citation check and prompt with the four principles, the judges, the commitment order |
| `b-freeze.py` | step 1: seed from the tag commit, the 300 + 30 draw, private freeze, `FREEZE-COMMITMENT.json` |
| `b-judge.py` | step 2: both judges, cached and capped at US$ 1, `JUDGES-COMMITMENT.json` (no label, no rate) |
| `b-human.py` | step 3: the blind sheet (`make`, `SHEET-COMMITMENT.json`) and the grades (`commit`, `HUMAN-COMMITMENT.json`) |
| `b-read.py` | step 4: controls, final labels, B-F with its Wilson interval, `READING-<date>.json` |
| `b-test.py` | offline tests (53 checks): synthetic database, fake judges, throwaway git repository; no network |

## What the census of 2026-11-06 says

The graph has not grown since July. Of 17,694 relations, 17,452 were created in 2026-07 and 11
after 2026-09-01. Its predicates are free text: 8,359 distinct `relation_type` values, 6,130 of them
used once, and 34.6% of relations carry a predicate no other relation uses. Of the relations whose
evidence chunk still exists, 82.6% cite the document vault (`memory/mac-docs/`), 12.3% workspace
documents, 4.2% daily notes, and 8 relations cite a distilled session. `extraction_method` is NULL
on every relation, and 17,682 carry the same confidence, 0.80. Nothing is superseded.

## What the note still needs

- A decision on scope: the note can describe structure from this census alone, or also state
  faithfulness. The October figure (0.900, 135 of 150, after the citation checker was calibrated)
  used the same sample that defined the criteria, so stating faithfulness needs a fresh sample,
  judged and adjudicated independently. That costs judge calls and a human pass, and is the
  author's decision.
- The consumer question from PLANO.md: the graph reads as a contract graph because its evidence is
  mostly the document vault, and the only measured consumer (2026-10-23) was a task about
  contracts.
