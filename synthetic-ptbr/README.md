# Synthetic PT-BR memory corpus

A small, public, constructed corpus in Brazilian Portuguese for running the method checks of
Paper A (doi:10.5281/zenodo.24400444) outside the private corpus it was measured on.

**What it is for.** A public, executable suite of the failure mechanisms of an evaluation ruler
for agent memory: gold keyed by chunk id against gold keyed by evidence anchor (finding 1), an
unjudged result read as a miss (finding 2), and an nDCG ideal built from the ranking (finding 4).
It reports, under pinned package versions, whether each mechanism produces the failure.

**What it is not.** It is not an independent replication of Paper A's empirical numbers, not a
measure of retrieval quality (invented, unique values favour BM25), and not an uncontaminated
benchmark: it is public, so treat it as an open regression fixture.

## Status

Steps 1 and 2 of the plan in `PLANO.md` («Objetivo (2026-11-25)»): the plan is fixed and the
corpus is generated, checked and scanned. The method tests (step 3) have not run yet.

| file | what |
|---|---|
| `plan.py` | deterministic planner (seed 20261125): 200 files, 45 planted facts, 5 false-premise queries, variants, context negatives, duplicates, operation targets, latent truth `T` and registered labels `R` |
| `plan/plan.json`, `plan/COVERAGE.md` | the committed plan and its coverage matrix; `plan.py --check` fails if they drift |
| `generate.py` | writes the corpus: the model writes free text around markers, the script puts the planted sentences in; isolated `claude -p` |
| `corpus/` | the 200 generated files (about 49,000 words) |
| `generation/` | one record per file: system prompt, prompt, every attempt, reported cost, model returned |
| `check-corpus.py` | gate: the corpus on disk is exactly what was planted, values appear only inside their planted sentences, free text has no digits, no e-mail or link |
| `privacy-scan.py` | gate: no run of 8 words of this package is also in the private corpus; run on the host that holds it |
| `metrics.py` | nDCG@10 with a gold ideal and a ranking ideal (an empty ideal is undefined, never 0 or 1), pooling, and hand-computed fixtures |
| `test-synthetic.py` | offline tests: each gate passes on a valid state and fails on its infractor; also the contract of `eval/resolve-gold-anchors.py` |

```sh
python3 -I synthetic-ptbr/plan.py --check
python3 -I synthetic-ptbr/check-corpus.py --corpus synthetic-ptbr/corpus
python3 -I synthetic-ptbr/metrics.py --fixtures
python3 -I synthetic-ptbr/test-synthetic.py
```

### How the corpus was generated (2026-11-25)

- Model `claude-sonnet-5-5` through `claude -p`, one call per file, in an empty temporary
  directory with `--tools "" --setting-sources "" --strict-mcp-config --no-session-persistence`
  and the system prompt recorded in `generation/`. Every file passed on its first attempt; the
  reported cost was US$ 1.91. The text is not reproducible; the committed corpus is the artefact.
- The CLI attaches the e-mail of the account it runs under to every call, and no flag removes it.
  The generator refuses any output that carries a term of that account (checked at run time, never
  written down), and `check-corpus.py` refuses any `@` or link.
- Privacy scan: 0 shared runs of 8 words between this package (74,742 runs) and the 65,206 chunks
  of the private corpus, with a positive control that planted one private chunk and was caught.

### Known marks of the generated text

These do not touch the method tests, and are left as they are:

- "na semana seguinte" ("the following week") appears in 181 of the 200 files: the prompt gave it
  as the example of how to avoid writing a date. The queries do not contain it.
- 3 files open by echoing the prompt ("Assuntos do dia: ...").
- 12 decision and lesson titles repeat, because titles come from a pool of 20 topics.
- The model invented first names for staff (e.g. "Marta"), without surnames.
- A blind read of 10 files drawn with a fixed seed found natural Brazilian Portuguese and one
  agreement slip; a search of the free text for quantities written in words found none.

## Design notes

- **Labels come from construction, but are kept apart.** `T` is every planted positive (primary
  sentence plus paraphrases written by the planner with a variant form of the value). `R` is `T`
  masked by a seeded rule fixed before any ranking exists. Pooled labels are `R` plus the members
  of `T` found in the top 10 of the same ranking.
- **Free text has no digits.** The model that writes the text around the planted sentences may
  not write a digit; the gate enforces it. A value restated in words by the model is the residue
  no text check sees, and is audited by a blind sample.
- **The resolver's prefix.** `eval/resolve-gold-anchors.py` matches the first 160 normalised
  characters of an anchor by default, so an edit after that prefix goes unseen. The tests show it,
  and this corpus resolves anchors with the whole anchor (`ANCHOR_PREFIX` above its length).

Licence of the corpus and plan, once published: CC BY 4.0.
