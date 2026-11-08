# Paper E: writing criterion × extractor strength

Does the advantage of the rule-based criterion C2 over the deployed C0 (Paper 3: +24.8 pp with
`gemini-2.5-flash-lite`) shrink with a stronger extractor? Design, hypotheses and analysis:
`PREREGISTRATION.md`.

| file | what it is |
|---|---|
| `PREREGISTRATION.md` | the plan; frozen by the tag `paper-e-prereg-v1.0` |
| `e_prompts.py` | criteria C0, C2 (Paper 3, byte for byte) and P; Paper E's parser |
| `e_batch.py` | Gemini Batch API over REST: upload, create, poll, list, download |
| `e-run.py` | runner: `plan`, `seed`, `batch-test`, `distill`, `read` |
| `e-analyze.py` | the registered analysis; `--check` reproduces it byte for byte |
| `e-test.py` | offline tests, fake API, synthetic instances |
| `e-smoke.py`, `e-shape-probe.py` | the cost smokes and the JSON shape probe |
| `SMOKE-RESULT.md` | what the smokes measured, cost projection, power |
| `runs/` | smoke outputs (counts only) and the batch test |

## Tests

`python3 -I e-test.py` runs 46 checks without network and ends with ALL PASS. Five planted
defects were each caught: the parser refusing the list form, the duplicate-batch guard removed,
batch spend at full price, the positive control keeping the answer sessions, and the primary
contrast without its flash-lite term.

## Spend before the tag

| step | US$ |
|---|---|
| smoke, `gemini-2.5-pro` arms and flash-lite P | 1.92 |
| shape probe | 0.09 |
| smoke, `gemini-2.5-flash` | 0.08 |
| batch test (60 requests, `runs/batch-test-2026-11-08/`) | 0.01 |
| **total** | **2.10** |
