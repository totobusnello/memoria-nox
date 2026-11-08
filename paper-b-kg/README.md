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
| `PREREGISTRATION.md` | v1.0, fixed by the tag `paper-b-prereg-v1.0` (2026-11-07): faithfulness on a fresh uniform sample of 300, two judge families, the October principles fixed in advance, blind human adjudication |
| `b-common.py` | what the scripts share: the draw, the October citation check and prompt with the four principles, the judges, the commitment order |
| `b-freeze.py` | step 1: seed from the tag commit, the 300 + 30 draw, private freeze, `FREEZE-COMMITMENT.json` |
| `b-judge.py` | step 2: both judges, cached and capped at US$ 1, `JUDGES-COMMITMENT.json` (no label, no rate) |
| `b-human.py` | step 3: the blind sheet (`make`, `SHEET-COMMITMENT.json`) and the grades (`commit`, `HUMAN-COMMITMENT.json`) |
| `b-read.py` | step 4: controls, final labels, B-F with its Wilson interval, `READING-<date>.json` |
| `b-test.py` | offline tests (56 checks): synthetic database, fake judges, throwaway git repository; no network |
| `READING-2026-11-07.json` | the reading: B-F 0.913 [0.876, 0.940], both judges pass both controls, kappa with the human 0.155 |
| `b-disagreement-direction.py`, `DISAGREEMENT-DIRECTION-2026-11-07.json` | after the reading, not registered: which judge accepted on each disagreement row, against the human grade (counts only) |
| `NOTE.md`, `PROVENANCE.json` | the data note covering Paper B and Paper B2 (`../paper-b2-kg-repair/`); gate `python3 -I tools/provenance.py --check paper-b-kg` |
| `../paper-b2-kg-repair/b2-regrade-sensitivity.py`, `../paper-b2-kg-repair/REGRADE-SENSITIVITY-2026-11-07.json` | after the reading, not registered: Paper B2's figures with sheet items 39, 40 and 55 at their first grade (B2 deviation 1); counts only |
| `pdf-build/build-note-pdf.sh` | the note's PDF, with Paper 3's preamble, table pass and layout check; refuses if the provenance gate fails |
| `deposit/deposit-note.py`, `deposit/description-note-v1.0.html` | the Zenodo record of the note: `--plan`, `--create-draft`, `--build`, `--fill`, `--readback`; never publishes |

## What the census of 2026-11-06 says

The graph has not grown since July. Of 17,694 relations, 17,452 were created in 2026-07 and 11
after 2026-09-01. Its predicates are free text: 8,359 distinct `relation_type` values, 6,130 of them
used once, and 34.6% of relations carry a predicate no other relation uses. Of the relations whose
evidence chunk still exists, 82.6% cite the document vault (`memory/mac-docs/`), 12.3% workspace
documents, 4.2% daily notes, and 8 relations cite a distilled session. `extraction_method` is NULL
on every relation, and 17,682 carry the same confidence, 0.80. Nothing is superseded.

## The note

`NOTE.md` covers both studies. Version 1.0 is deposited on Zenodo, doi:10.5281/zenodo.24046282
(published 2026-11-07, files verified by checksum against `deposit/`). Before the deposit, Codex (`gpt-6-astra`) and Kimi read it at the
author's request (2026-11-07); their findings changed the abstract, §1 to §4 and §6, and added the
regrade sensitivity above.
