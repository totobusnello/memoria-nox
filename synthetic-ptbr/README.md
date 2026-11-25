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

Steps 1 to 3 of the plan in `PLANO.md` («Objetivo (2026-11-25)»): the plan is fixed, the corpus is
generated, checked and scanned, and the method tests ran on nox-mem 3.5.2 and 3.11.1. The note that
reports them is `NOTE.md`, revised after two rounds of review (Codex and Kimi) and deposited with
this directory on Zenodo.

| file | what |
|---|---|
| `plan.py` | deterministic planner (seed 20261125): 200 files, 45 planted facts, 5 false-premise queries, variants, context negatives, duplicates, operation targets, latent truth `T` and registered labels `R` |
| `plan/plan.json`, `plan/COVERAGE.md` | the committed plan and its coverage matrix; `plan.py --check` fails if they drift |
| `generate.py` | writes the corpus: the model writes free text around markers, the script puts the planted sentences in; isolated `claude -p` |
| `corpus/` | the 200 generated files (about 49,000 words) |
| `generation/` | one record per file: system prompt, prompt, every attempt, reported cost, model returned |
| `check-corpus.py` | gate: the corpus on disk is exactly what was planted, values appear only inside their planted sentences, free text has no digits, no e-mail or link |
| `privacy-scan.py` | gate: no run of 8 words of this package is also in the private corpus; run on the host that holds it |
| `check-ingest.py` | gate: after ingestion, every planted sentence lies whole in a chunk, a duplicated primary is two byte-identical chunks, every operation file has two or more chunks |
| `method-tests.py`, `nm.mjs` | step 1: installs the two pinned versions, ingests, ranks the 50 queries (FTS path, no access tracking), runs the six operations, freezes everything under `results/`; `--analyze` reads only the frozen files |
| `results/` | frozen per version (`chunks-baseline.json`, `rankings.json`, `operations.json`) and the report `etapa1.txt`/`etapa1.json` |
| `metrics.py` | nDCG@10 with a gold ideal and a ranking ideal (an empty ideal is undefined, never 0 or 1), pooling, and hand-computed fixtures |
| `test-synthetic.py` | offline tests: each gate passes on a valid state and fails on its infractor; also the contract of `eval/resolve-gold-anchors.py` |

```sh
python3 -I synthetic-ptbr/plan.py --check
python3 -I synthetic-ptbr/check-corpus.py --corpus synthetic-ptbr/corpus
python3 -I synthetic-ptbr/generate.py --reassemble --check --out synthetic-ptbr/corpus --raw synthetic-ptbr/generation
python3 -I synthetic-ptbr/method-tests.py --analyze --check
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

- Sections. nox-mem chunks markdown only at `##`/`###` headings, so the first assembly (one
  section per file) gave one chunk per file, and an edit anywhere in a file would have changed the
  planted sentence's chunk. The assembler now splits the model's text into `##` sections with fixed
  headings; the committed corpus is exactly what `--reassemble` rebuilds from `generation/`. No
  model call was repeated.
- A second privacy scan after sectioning and with `results/` in the package: 0 shared runs of 8
  words (99,999 package runs against 65,208 private chunks). On release day (2026-11-25), a scan of
  the generated material alone (corpus, plan, generation records, results): 0 shared runs (99,165
  runs against 65,211 private chunks).

### Step 1 results (`results/etapa1.txt`)

The analysis rules were committed before the first run. Both versions built the same 851 chunks and
returned the same 50 rankings, so findings 2 and 4 are the same on both; finding 1 differs.

| after the operation (5 facts each) | 3.5.2: id / anchor | 3.11.1: id / anchor |
|---|---|---|
| re-ingest, file unchanged | none / live | live / live |
| edit outside the planted sentence | none / live | live / live |
| edit inside (value replaced) | none / none | none / none |
| rename, then re-ingest | stale / stale | live / none |
| rename, no re-ingest | stale / stale | stale / stale |
| delete | stale / stale | stale / stale |

*live*: reaches the sentence under the key of the file that holds it now; *stale*: reaches the
sentence in a chunk whose file is gone or moved (or tombstoned); *none*: no chunk it reaches holds
the sentence (in this run: the id no longer existed and the anchor resolved to nothing). These are
direct resolutions in the database against the disk, not search results.

- Finding 1: under 3.5.2 the tracked ids were lost on a re-ingest and on an edit to another
  section, while the anchor survived. Under 3.11.1 the id survived both, and in the one rename
  sequence run (rename to `-movido.md`, watcher routine on the old path, ingest of the new path) the
  id reached the sentence and the anchor did not; with no re-ingest after the rename both stayed
  stale. No live watcher ran: the harness calls each version's routine directly. After a delete
  both references still reach the sentence, because neither the id lookup nor the anchor resolver
  consults the tombstone.
- Finding 2: all 20 queries with incomplete registered labels changed score, 12 upward and 8
  downward (25 equal; means 0.7543 registered, 0.7372 truth, 0.7598 pooled). A retrieved positive
  left out of R counts as a miss, but it also shrinks the ideal, and in 7 of the 12 upward queries
  every true positive was in the top 10. The zero-scoring case Paper A measured did not occur: R
  always holds the primary and every registered positive was retrieved. Pooled labels cannot score
  below the truth with a perfect oracle (arithmetic); they scored above it on 5 of 45 queries, the
  same five as finding 4. Means are taken over unrounded scores (corrected 2026-11-25 after the
  note's review: the first analysis averaged scores rounded to four places and printed 0.7542).
- Finding 4: the ranking ideal changed the score of 5 of 45 queries, by +0.2033 on average (at most
  +0.2441); its direction is arithmetic, the frequency and size are what this corpus measures.
- Context negatives ranked above the first positive on 4 of 45 queries.

### Known marks of the generated text

These do not touch the method tests, and are left as they are:

- "semana seguinte" ("the following week") appears in 181 of the 200 files (115 as "na semana
  seguinte", the prompt's own wording): the prompt gave it
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
