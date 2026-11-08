# Paper E: writing criterion × extractor strength

Does the advantage of the rule-based criterion C2 over the deployed C0 (Paper 3: +24.8 pp with
`gemini-2.5-flash-lite`) shrink with a stronger extractor? Design, hypotheses and analysis:
`PREREGISTRATION.md`.

| file | what it is |
|---|---|
| `PREREGISTRATION.md` | the plan; frozen by the tag `paper-e-prereg-v1.0` |
| `e_prompts.py` | criteria C0, C2 (Paper 3, byte for byte) and P; Paper E's parser |
| `e_batch.py` | Gemini Batch API over REST: upload, create, poll, list, download |
| `e-run.py` | runner: `plan`, `batch-test`, `distill`, `read` |
| `e-analyze.py` | the registered analysis; `--check` reproduces it byte for byte |
| `e-test.py` | offline tests, fake API, synthetic instances |
| `review-codex-prereg.md`, `review-kimi-prereg.md` | the voices on the v1.0 draft of the plan |
| `review-codex-note.md`, `review-kimi-note.md` | the voices on the first draft of the note |
| `e-smoke.py`, `e-shape-probe.py` | the cost smokes and the JSON shape probe |
| `SMOKE-RESULT.md` | what the smokes measured, cost projection, power |
| `RESULT.md` | the registered run of 2026-11-08 and its analysis |
| `pdf-build/build-note-pdf.sh` | builds the note PDF with Paper 3's preamble, after the provenance gate |
| `deposit/deposit-note.py`, `deposit/description-note-v1.0.html` | the Zenodo deposit of the note (plan, draft, build, fill, readback; never publishes) |
| `NOTE.md`, `PROVENANCE.json` | the research note (draft) and the source of each of its numbers (`tools/provenance.py --check paper-e-extractor`) |
| `runs/` | smoke outputs (counts only), the batch test, and `confirm-2026-11-08/` (rows, receipt, analysis) |

## Tests

`python3 -I e-test.py` runs 71 checks without network and ends with ALL PASS. Ten planted
defects were each caught (exit 1):

- the parser refusing the list form;
- the duplicate-batch guard removed;
- batch spend at full price;
- re-ingest charging again;
- invalid batch answers not retried;
- the positive controls keeping the answer sessions;
- the freeze check skipping the analysis, this plan and Paper 3's modules;
- the analysis accepting a partial row set;
- sync calls ignoring the cap;
- the primary contrast without its flash-lite term.

The freeze check is tested in a temporary git repository with both tags.

## Spend before the tag

| step | US$ |
|---|---|
| smoke, `gemini-2.5-pro` arms and flash-lite P | 1.92 |
| shape probe | 0.09 |
| smoke, `gemini-2.5-flash` | 0.08 |
| batch test (60 requests, `runs/batch-test-2026-11-08/`) | 0.01 |
| **total** | **2.10** |

The registered run (`RESULT.md`) spent US$ 150.55, under the US$ 160 cap.

## The note

`NOTE.md` reports the registered run. Version 1.0 is deposited on Zenodo, doi:10.5281/zenodo.24057928
(concept doi:10.5281/zenodo.24057927; published 2026-11-08, files verified by checksum against
`deposit/`). Before the deposit, Codex (`gpt-6-astra`) and Kimi read it at the author's request
(2026-11-08); the Codex review changed the abstract, §5 and §6 and added the missing parts of the
registered report, and the Kimi review recomputed every number. The `avoid-ai-writing` pass ran after
both reviews.
