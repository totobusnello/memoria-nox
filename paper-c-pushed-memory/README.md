# Paper C: no textual trace of a pushed memory brief

A data note, narrow and dated (PLANO.md, row C). Status: **deposited** on Zenodo on 2026-11-06 as
version 1.0, "No textual match to a pushed memory brief in agent replies",
doi:10.5281/zenodo.24017459 (concept doi:10.5281/zenodo.24017458), after two passes by Codex and
one by Kimi (#668, #670). `NOTE.md` is the source of that version; the deposit copy replaces its
status line with the DOI line.

It reports three measurements already made in October 2026, each with its own audit, and states
one claim: in these protocols we did not detect a textual trace of the pushed brief in the agents'
replies, nor a change in the first action. It does not claim that the agents do not use memory.

| file | what |
|---|---|
| `NOTE.md` | the note |
| `PROVENANCE.json` | every number the note prints, with its audit, locator and commit |
| `pdf-build/build-note-pdf.sh` | the PDF, with Paper 3's preamble and layout check; runs the provenance gate first |
| `deposit/deposit-note.py` | the Zenodo record; never publishes. `--plan` is read-only |

| measurement | audit |
|---|---|
| 7a, textual trace in replies | `audits/2026-10-14-brief-usage.md` (with the 2026-10-22 rerun on three roots) |
| R1, served against recency-ordered brief | `audits/2026-10-21-r1-recency-relevance.md` |
| 7b, first action, behavioural | `audits/2026-10-15-7b-positive-control.md` |
| pull side, unprompted searches | `audits/2026-10-23-item7-consumidor-construido.md` |

Gate: `python3 -I tools/provenance.py --check paper-c-pushed-memory`.
