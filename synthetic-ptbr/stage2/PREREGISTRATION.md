# Step 2 pre-registration: the judges of Paper A against a planted answer key

Status: DRAFT, not frozen. It is frozen by the tag `synthetic-ptbr-stage2-prereg` on the commit that
also carries the scripts named below; no model call of step 2 happens before that tag exists, except
the offline tests, which call no model.

## 1. Why

Paper A (doi:10.5281/zenodo.24400444, §3) reports two failures of its LLM judges and says, of the
second, that "with no independent reference, this says nothing either way about precision". The
synthetic corpus of step 1 (doi:10.5281/zenodo.24535848) has that reference: every question was
written from a sentence the planner placed, so whether a chunk answers a question is known by
construction. Step 2 re-runs the judges of Paper A, with their own prompts and models, on this corpus
and reads them against that key.

Findings of Paper A under test:

- **Third.** The quoting oracle presents paraphrase as verbatim quotation; the 8-word citation check
  built on its quotes lowered agreement with a second judge; the oracle could not hold a negative on a
  false-premise question.
- **Fifth.** A second judge rejected much of the recorded gold, and Paper A could not say whether the
  rejections were right.
- **Judge stability** (§3, "How much the judge's own reading moves the pooled score"): an identical
  request returned identical labels; the same predicate reworded changed some labels and moved pooled.

## 2. Fixed inputs

- Corpus, plan and baseline: the v1.0 deposit, commit `70c82859`, files `synthetic-ptbr/plan/plan.json`
  and `synthetic-ptbr/results/3.11.1/{chunks-baseline.json,rankings.json}` (nox-mem 3.11.1, BM25,
  frozen in step 1). No re-ingest and no new ranking: chunk text is read from `chunks-baseline.json`.
- Truth `T` for a (query, chunk) pair: the chunk contains, verbatim, the planted primary sentence or a
  planted paraphrase listed in the query's `T` (the rule used in step 1). Every pair of a
  false-premise query is false in `T`. Registered gold `R`: the same rule over the query's `R`.
- Population, built by `stage2/pairs.py` and committed as `stage2/pairs.json` before the tag:
  for each of the 50 queries, the top 10 of the frozen ranking, every chunk in `T` outside the top 10,
  every chunk holding a context negative of the query's fact (negated value, rejected proposal, other
  entity), and one chunk drawn at random from the rest (seed `20261126`). As computed before writing
  this: 555 pairs (500 top-10, 5 `T` outside the top 10, 50 random; the 15 context-negative chunks are
  all inside the top 10), 89 of them true in `T`, 59 in `R`.
- Gold-check population (finding five): the 59 `R` pairs (correct gold, by construction), the 15
  context-negative pairs presented as gold (wrong gold that shares the value), and the 50 random pairs
  presented as gold (Paper A's random-chunk control): 124 pairs.

## 3. Instruments (copied, not rewritten)

Prompts are copied character for character from the scripts named, with only the input plumbing
changed (chunk text from the frozen JSON instead of a SQLite file). `stage2/judges.py` holds them,
and `stage2/test-stage2.py` checks that each prompt string equals the one in its source script at the
cited commit.

| id | instrument | model and API | source in this repository |
|---|---|---|---|
| J-closed | closed-book answer per query (input of the oracle) | `gemini-2.5-flash-lite`, Gemini `generateContent`, temperature 0 | `audits/2026-10-22-gold-oracle.py`, `CLOSED` |
| J-oracle | quoting oracle: answer, verbatim quote, `trecho_responde` | same | `audits/2026-10-22-gold-oracle.py`, `JUDGE` |
| J-repass | 8-word second pass, on oracle positives whose quote failed | same | `audits/2026-10-22-gold-repass.py`, `P` |
| J-pool | pooling judge with the 8-word citation leg | same | `audits/2026-10-22-gold-pooling.py`, `P` |
| J-reg | registered judge: predicate plus four levels, p > 0.5 | `gpt-6-luna`, OpenAI Decisions API | `eval/judge-relevance.py`, `PREDICATE`, `LEVELS` |
| J-reg-2 | J-reg again, identical request, separate run | same | same |
| J-reword | same predicate, sent alone, passage wrapped in `TRECHO:` | same | `audits/2026-10-27-judge-reread-full.py`, `PRED` |
| J-gold | "does the recorded gold answer the question" | same | `audits/2026-10-27-does-the-recorded-gold-answer-the-question.py`, `RESPONDE` |
| J-premise | premise check, on the 55 false-premise pairs and on 55 fact pairs drawn with seed `20261126` | `gemini-2.5-flash-lite` | **reconstructed**: Paper A's premise-check prompt was never committed; the text in `judges.py` is new and is reported as such |

Citation checks, as in the sources: oracle quote `norm(quote)[:160] in norm(chunk)`; 8-word leg
`len(norm(q8)) >= 12 and norm(q8) in norm(chunk)`, with `norm` = NFKD, accents stripped, whitespace
collapsed, lower case. A full-quote check (the whole normalised quote) is added and reported beside
the 160-character one. Chunk text is cut at 6,000 characters for every judge, as in the sources.

J-oracle, J-pool, J-reg, J-reg-2 and J-reword judge all 555 pairs. J-gold judges the 124 gold-check
pairs. J-closed runs once per query (50 calls).

## 4. Readings

All readings are descriptive. Precision, recall and Cohen's kappa are computed against `T` per judge.
Kappa between judges is reported next to each judge's kappa against `T`.

1. **Quotation.** Among J-oracle positives: the share whose quote fails the 160-character check, the
   share failing the full-quote check, and, of the failures, the share J-repass verifies.
2. **The citation leg.** For J-pool: precision and recall against `T` of `trecho_responde` alone and of
   `trecho_responde AND citacao_confere`; kappa of each with J-reg. This is the reading Paper A could
   not make: whether the kappa the check costs is a loss of precision, of recall, or neither.
3. **Negatives.** Pairs of the 5 false-premise queries labelled as answering, per judge; and, for the
   15 context-negative pairs, the same count. J-premise: the premise flag against the known premise
   (false for the 55 false-premise pairs, true for the 55 fact pairs); the `motivo` texts are published,
   no number is derived from them.
4. **Gold check.** J-gold acceptance on correct gold (59), on wrong gold with the value (15), and on
   random chunks (50).
5. **Stability.** Labels changed between J-reg and J-reg-2, and between J-reg and J-reword. Pooled
   nDCG@10 (gold `R` plus the judge's positives in the top 10, step 1's definition) under J-reg, J-reg-2
   and J-reword, against nDCG@10 on `T`.

## 5. Predictions carried over from Paper A

Read as "seen again" or "not seen again"; none is a pass mark for the method.

- P1: some J-oracle positives fail the 160-character quote check.
- P2: J-pool with the citation leg has lower kappa with J-reg than J-pool without it.
- P3: J-reg and J-reg-2 differ on no label.
- P4: J-reword differs from J-reg on at least one label.
- P5: J-gold accepts under 5% of the random pairs.

Nothing is predicted about precision against `T`: that is what the step measures.

## 6. Truth gaps

The key is as good as the generator's discipline: a generated sentence could answer a question
without being planted (step 1 audited a sample and found none, which is not completeness). Every pair
that any judge labels as answering and `T` labels false is put in a blind sheet together with an
equal number of pairs that `T` and the judges label false, shuffled with seed `20261126`, with the
question and the chunk and no label. Claude reads all of it and the owner reads 10 rows; each row is
marked "answers" or "does not answer". Readings in §4 are reported against `T` as registered
(primary) and against `T` corrected by this sheet (secondary), side by side.

## 7. Runs, money and stopping

- Each instrument first runs a smoke of 10 pairs, which is counted in the ledger and excluded from
  every reading. Then one full run. No instrument is re-run, except one complete re-run when more than
  10% of its pairs end without a label after the scripts' own retries; that re-run is reported.
- Pairs without a label after retries are reported per instrument and left out of that instrument's
  denominators.
- `stage2/ledger.json` records the reported cost of every call. The runner refuses any call that would
  start with the ledger at or above US$ 20 and stops; an instrument cut by the ceiling is reported as
  incomplete, with how far it got. Expected cost from Paper A's recorded prices: well under US$ 1.
- Keys are read from the environment (`GEMINI_API_KEY`, `OPENAI_API_KEY`), never from a file in the
  repository; outputs carry the model id each API returned.

## 8. What changes after the tag

Nothing in §2 to §7. An error found later in a script is fixed in a dated amendment that states what
it changes and whether any reading had been seen; readings computed under the frozen scripts stay in
the record.
