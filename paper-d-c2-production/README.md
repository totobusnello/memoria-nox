# Paper D: criterion C2 on the production corpus

Status: 2026-11-05. All nine decisions taken (`PROTOCOL-DRAFT.md` §11); a paid smoke on 5 sessions
sized the sample; the pre-registration is drafted. Nothing is fixed or tagged.

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
| `PROTOCOL-DRAFT.md` | question, estimand, freezing and sampling of sessions, outcome without a gold set, reader and judges, controls, privacy, cost arithmetic, and the decisions |
| `d-select.py` | read-only session selection on the archive host (piped over ssh); prints counts and paths, no text |
| `d-smoke.py` | the smoke pipeline: writer, distillation C0/C2, reader, two judges; prints counts only |
| `SMOKE-2026-11-05.md` | the smoke's counts: pool sizes, accuracies per arm and judge, discordant pairs, sample-size table |

## Privacy

The corpus is private and this repository is public. Session ids, transcripts, questions, units and
answers stay outside the repository; only code, counts, hashes and aggregate results are committed.
