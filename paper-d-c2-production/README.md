# Paper D: criterion C2 on the production corpus

Status: 2026-11-06. All nine decisions taken (`PROTOCOL-DRAFT.md` §11); a paid smoke on 5 sessions
sized the sample; the pre-registration is drafted and its scripts are written and pass the offline
test (`d-test.py`). Nothing is fixed or tagged.

## Scope

Whether the revised extraction criterion C2 (Paper 3) builds a more useful memory than the deployed
criterion C0 from the same frozen production sessions, measured by an offline paired replay with no
deploy (`../PLANO.md`, row D and Decisões 2026-11-04). A live shadow is out of scope until the
replay shows an effect and a product decision needs it.

## Files

| file | what |
|---|---|
| `PREREGISTRATION.md` | the draft pre-registration: frame, draw, questions, arms, controls, hypotheses, order; binding at the tag `paper-d-prereg-v1.0` |
| `d-frame-census.py` | read-only census of the frame on the archive host: eligible sessions split by what the production distiller did with them; counts only |
| `FRAME-CENSUS-2026-11-05.json` | the census output the design was set on |
| `FRAME-CENSUS-2026-11-06.json` | the same census with the logged sessions split by the message count production recorded, and the recount from the transcript |
| `d-common.py` | what the registered scripts share: windows, cut, visible prefix, production's message count, counterfactual, serving, draw, the checks of the public order |
| `d-freeze.py` | step 2: freeze and draw (`run` on the author's machine, `host` on the serving host, `commit`) |
| `d-generate.py` | step 3: questions, validation, the extension rule, `QUESTIONS-COMMITMENT.json` |
| `FREEZE-COMMITMENT.json` | step 2 output, public: window, seed, counts, and the sha256 of every frozen file |
| `QUESTIONS-COMMITMENT.json` | step 3 output, public: counts, drops, and the sha256 of the questions, prompts, scripts and writer cache |
| `HUMAN-COMMITMENT.json` | step 5 output, public: agreement and kappa of the blind human sample with judge 1, and the sha256 of the sheet, results and questions |
| `READING-2026-11-06.json`, `READING-2026-11-06.txt` | step 6 output (`d-read.sh`), aggregates only: the fidelity control failed (P 0.248, V 0.438 on the 30 sessions production sent), so H-D1 and H-D2 are not interpreted |
| `d-fidelity-diagnosis.py` | written after the reading, not registered: rebuilds the text production's distiller sent and compares it with arm V's; classifies each question by whether its citations sit in a scheduled job's prompt |
| `FIDELITY-DIAGNOSIS-2026-11-06.json` | its output: 82% of V's input on the sent sessions (301,441 of 367,003 chars) is `[cron:` prompts, which production drops before distilling; 138 of 255 primary questions cite only such prompts |
| `d-frame-census-v11.py`, `FRAME-CENSUS-V11-2026-11-06.json` | read-only census of the frame under production's input rule, for a possible v1.1: 223 eligible sessions outside v1.0's sample, 19 of them sent to the model by production |
| `DISTILL-LOG-2026-11-06.json` | counts of the production distiller's eight weekly runs read from the host's maintenance log: sessions, ingested, deduplicated |
| `d-distiller-reach.py`, `d-two-message-profile.py`, `DISTILLER-REACH-2026-11-06.json` | read-only, after the note's first draft: which eligible sessions the distiller logged, by week, and what the skipped two-message sessions contain; most of the unreached sessions are one backlog left before the 2026-09-08 address fix |
| `NOTE.md` | the data note: the registered study ran in full and failed its fidelity control; the cause, what it exposed, and the distiller's coverage |
| `PROVENANCE.json` | one entry per number printed in `NOTE.md`; `python3 tools/provenance.py --check paper-d-c2-production` |
| `pdf-build/build-note-pdf.sh` | the note's PDF, with Paper 3's preamble and layout check; runs the provenance gate first |
| `deposit/deposit-note.py` | the Zenodo record for the note; never publishes. `--plan` is read-only |
| `d-run.sh`, `d-run.py` | step 4: every arm, from the code of the tag; prints counts, cost and a hash |
| `d-human.py` | step 5: the blind human sample (`make`, `agree`, `commit`) |
| `d-read.sh`, `d-read.py` | step 6: controls, H-D1, H-D2, descriptives; keyless |
| `d-test.py` | offline test of all of the above on a synthetic archive and snapshot, model calls stubbed, ssh shimmed |
| `PROTOCOL-DRAFT.md` | question, estimand, freezing and sampling of sessions, outcome without a gold set, reader and judges, controls, privacy, cost arithmetic, and the decisions |
| `d-select.py` | read-only session selection on the archive host (piped over ssh); prints counts and paths, no text |
| `d-smoke.py` | the smoke pipeline: writer, distillation C0/C2, reader, two judges; prints counts only |
| `SMOKE-2026-11-05.md` | the smoke's counts: pool sizes, accuracies per arm and judge, discordant pairs, sample-size table |

## Privacy

The corpus is private and this repository is public. Session ids, transcripts, questions, units and
answers stay outside the repository; only code, counts, hashes and aggregate results are committed.
