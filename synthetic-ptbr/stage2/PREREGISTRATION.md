# Step 2 pre-registration: the judges of Paper A against a planted answer key

Status: DRAFT, revised after a challenge round by Codex and Kimi (2026-11-25). It is frozen by the
tag `synthetic-ptbr-stage2-prereg` on the commit that also carries the scripts named below. No model
call of step 2 happens before that tag exists and before the human annotations of §6 are committed.

## 1. What this step can and cannot say

Paper A (doi:10.5281/zenodo.24400444, §3) reports failures of its LLM judges and says, of one of
them, that "with no independent reference, this says nothing either way about precision". The
synthetic corpus of step 1 (doi:10.5281/zenodo.24535848) carries a key: every question was written
from sentences the planner placed. Step 2 re-runs the judges of Paper A, with the same model ids,
prompts and request bodies, on this corpus and reads them against that key and against a blind
human reading of a sample.

What it can say: how these judges behave on this corpus, against the planted key and against the
human sample. What it cannot say:

- Whether the citation check misbehaves the way it did in Paper A. Paper A's failures came from
  copyable formatting (Markdown table pipes, `<u>`, an escaped currency sign) and from quotes that
  drift after 13 to 53 characters. Here the 85 planted sentences have 43 to 95 characters, the largest
  chunk has 924, and no chunk carries `|`, `<u>` or `\R$`. Readings 1 and 2 hold for this corpus only;
  the check itself is described separately on offline fixtures (§5).
- Whether Paper A's 38 gold rejections were right. Its wrong gold came from a fallible build (one
  documented case confused a per-call limit with a storage capacity). Here wrong gold is introduced
  by the planner, as values that were rejected or superseded. The step measures acceptance of
  correct gold and of these two kinds of impostor, nothing about the private pairs.
- Anything about the same model versions Paper A used. The model ids are the same; whether a
  provider serves the same weights under an id is not observable. Every output records the model id
  the API returned.

## 2. Fixed inputs

- Corpus, plan and baseline: the v1.0 deposit, commit `70c82859`: `synthetic-ptbr/plan/plan.json` and
  `synthetic-ptbr/results/3.11.1/{chunks-baseline.json,rankings.json}` (nox-mem 3.11.1, BM25, frozen in
  step 1). Chunk text is read from `chunks-baseline.json`; nothing is re-ingested or re-ranked.
- Key `T` for a (query, chunk) pair: the chunk contains, verbatim, the planted primary sentence or a
  planted paraphrase listed in the query's `T` (step 1's rule). Every pair of a false-premise query is
  false in `T`. Registered gold `R`: the same rule over the query's `R`. `T` is a key of planted
  evidence, not a semantic truth; §6 measures how far the two differ.
- Population, built by `stage2/pairs.py` and committed as `stage2/pairs.json` (`--check` fails on
  drift): for each of the 50 queries, the top 10 of the frozen ranking, every chunk in `T` outside the
  top 10, and one chunk drawn from the rest (candidates sorted by id, `random.Random(20261126).choice`,
  in query order). Result: 555 pairs (500 top-10, 5 `T` outside the top 10, 50 drawn), 89 true in `T`,
  59 true in `R`. Context negatives: 15 pairs, all inside the top 10, each holding a value for the
  asked entity and attribute that the corpus marks as rejected (8) or superseded (7); none holds a
  correct form of the asked value. A pair counts once even when two chunks have the same text.
- Gold-check groups (finding five), over the same 555 pairs plus one control per query: correct gold
  = the 59 `R` pairs; wrong gold = the 15 context-negative pairs; random control = one chunk per query
  drawn as Paper A drew it (all chunk ids sorted, `random.Random(20261027)`, redrawn while equal to the
  query's first gold chunk; for false-premise queries, no exclusion). Controls outside the 555 are
  judged by J-gold only.

## 3. Instruments

Prompts and request bodies are copied from the sources below, at the commits given, with only the
input plumbing changed (chunk text from the frozen JSON). `stage2/judges.py` holds them;
`stage2/test-stage2.py` renders each request for a fixed pair and compares the prompt strings with
the source files at those commits, and the request bodies (fields, generation settings, question
names) with the bodies the sources build.

| id | role | model, API, settings | source (commit) |
|---|---|---|---|
| J-closed | closed-book answer per query, input of J-oracle | `gemini-2.5-flash-lite`, `generateContent`, temperature 0, `maxOutputTokens` 1200, JSON mime | `audits/2026-10-22-gold-oracle.py` `CLOSED` (`582a8cee`) |
| J-oracle | answer, verbatim quote, `trecho_responde`, `sem_fonte_ja_responde` | same | same file, `JUDGE` |
| J-repass | first 8 words, on J-oracle positives whose quote fails the 160-character check | same, `maxOutputTokens` 900 | `audits/2026-10-22-gold-repass.py` `P` (`b3dcc47c`) |
| J-pool | `trecho_responde` plus first 8 words | same, `maxOutputTokens` 700 | `audits/2026-10-22-gold-pooling.py` `P` (`0c628152`) |
| J-reg | registered judge: predicate `contem_resposta` plus four-level score, p > 0.5 | `gpt-6-luna`, OpenAI Decisions API | `eval/judge-relevance.py` `PREDICATE`, `LEVEL_Q`, `LEVELS` (`0c628152`) |
| J-reg-2 | J-reg again, identical request, separate run after J-reg ends | same | same |
| J-envelope | same predicate string sent alone, chunk wrapped in `TRECHO:\n---\n…\n---`, p > 0.5 | same | `audits/2026-10-27-judge-reread-full.py` `PRED` (`0c063e73`) |
| J-gold | "contains information that answers, totally or partly", chunk wrapped, p > 0.5 | same | `RESPONDE` of `audits/2026-10-27-does-the-recorded-gold-answer-the-question.py`, removed from the public tree on 2026-11-08 because it carried private anchors; the prompt string, which carries no corpus text, is copied; private file sha256 prefix `43bd20fd8419` |
| J-premise | exploratory: does the chunk support, contradict or say nothing about the question's premise | `gemini-2.5-flash-lite`, temperature 0, `maxOutputTokens` 700, JSON mime | **new**: Paper A's premise-check prompt was never committed; the text in `judges.py` is written for this step and reported as new |

Deviations from the sources, all declared: J-oracle judges every pair directly, without the
triage that showed 12 candidates and kept 3, and without the closed-book gate in the label;
J-repass selects pairs (J-oracle positives failing the quote check), where the source selected
queries and re-judged all their candidates; chunk text comes from JSON (the 6,000-character cut is
kept and is inert: the largest chunk has 924 characters). J-envelope changes two things at once
(no level question; wrapped chunk) and is read as sensitivity to the request envelope, not as a
reworded predicate.

Labels. A Gemini response is read with the source's tolerant extractor (`jload`, copied verbatim)
and is valid only if it yields a JSON object whose fields read below have the right JSON type
(`true`/`false` for booleans; the string `"false"` is not a boolean); a Decisions response is valid
only if it carries the expected answer name with a numeric probability. Anything else is a missing
label, never `false`. The sources coerced with `bool(...)`; this step does not, and says so. Positive label per
instrument: J-oracle `trecho_responde` (reported also with the source's full rule: `trecho_responde
AND NOT sem_fonte_ja_responde AND quote check`); J-pool `trecho_responde`, and with the leg
`trecho_responde AND citacao_confere`; J-reg, J-reg-2, J-envelope, J-gold probability > 0.5.

Citation checks, as in the sources, with `norm` = NFKD, accents stripped, whitespace collapsed,
lower case. Oracle quote: `bool(quote) and norm(quote)[:160] in norm(chunk)`. 8-word leg:
`bool(q8) and len(norm(q8)) >= 12 and norm(q8) in norm(chunk)` (the source checks 12 normalised
characters and a substring; it does not count words, and neither does this step). Added beside the
oracle check, not replacing it: the whole normalised quote as a substring.

Who judges what: J-closed, 50 queries; J-oracle, J-pool, J-reg, J-reg-2, J-envelope, J-gold, the
555 pairs; J-gold also the random controls outside the 555; J-repass, the eligible J-oracle pairs;
J-premise, the 55 false-premise pairs and 55 fact pairs (30 true in `T`, 25 false, drawn with seed
`20261126` and committed in `pairs.json`).

## 4. Readings

Every rate is printed with its numerator and denominator; a rate with denominator zero prints as
undefined. Agreement between two instruments is computed on the pairs where both have a valid
label. Results are reported over all 555 pairs and, separately, over the 500 top-10 pairs (the
population a pooling pass would judge).

1. **Quotation (J-oracle, J-repass), this corpus only.** Among J-oracle positives: quotes empty;
   failing the 160-character check; passing it but failing the whole-quote check; and, of the
   160-character failures, those J-repass verifies.
2. **The citation leg (J-pool).** The paired table of J-pool positives: leg passed or failed × `T`
   × J-reg label, with counts. From it: precision and recall against `T` without and with the leg,
   and kappa with J-reg without and with the leg, on the same pairs. The leg can only lower recall
   or leave it; precision can move either way or become undefined; the table shows which pairs
   moved.
3. **Negatives.** For each of the 5 false-premise queries and each of the 15 context-negative pairs,
   which instruments labelled it as answering. J-premise (exploratory): for the 55 false-premise
   pairs, how many it says support the premise (an error: the premise is absent from the corpus);
   for the 30 fact pairs true in `T`, how many it says support it; the other 25 are reported without
   a reading. Its `motivo` texts are published; no number is derived from them.
4. **Gold check (J-gold).** Acceptance of correct gold (59), wrong gold (15) and random controls
   (50), and the fact queries whose whole `R` J-gold rejects. Also J-gold against `T` on the 555.
5. **Stability.** J-reg against J-reg-2 and J-reg against J-envelope: labels changed, their direction,
   and the absolute change in probability in the bands 0–0.1, 0.1–0.3, 0.3–0.5 crossing, and over.
   Pooled nDCG@10 (step 1's definition: `R` plus the instrument's positives in the top 10) under
   J-reg, J-reg-2 and J-envelope, and nDCG@10 on `T`, over the fact queries whose top 10 has a valid
   label in all three runs; the other fact queries and the 5 false-premise queries (empty ideal) are
   listed apart.
6. **Each instrument against `T`** (primary, all pairs it judged): true and false positives and
   negatives, precision, recall, kappa against `T`; and kappa between each pair of the judges J-oracle,
   J-pool, J-reg, J-gold, beside their kappas against `T`.
7. **Against the human sample** (secondary, §6): the same counts for each instrument against the
   human reading, per stratum and weighted by inverse inclusion probability.

## 5. The citation check on fixtures (offline, no model)

`stage2/citation-fixtures.json` holds chunks and quotes built from the formats Paper A documented: a
Markdown table row, `<u>` wrapping, an escaped currency sign, a quote that drifts into paraphrase
after 13, 30 and 53 characters, a quote longer than 160 characters that diverges after character
160, an empty quote and a quote assembled from two places. The report prints, for each, the result
of the oracle check, the whole-quote check and the 8-word rule. This describes what the check
vetoes; it is not a measurement of any judge.

## 6. Human reading of a sample

Before any model call, `pairs.py` draws a stratified sample of 100 pairs (seed `20261126`) and
writes `stage2/human/SHEET.md` with only the question and the chunk text, in shuffled order, with
no key, no source, no rank; codes go into `stage2/human/annotations.tsv` (row, code, note). Strata and inclusion: 30 of the 89 pairs true in `T`; all 15 context-negative pairs; 10 of
the 55 false-premise pairs (2 per query); 45 of the 396 other pairs false in `T`.

The owner (Luiz Antonio Busnello) reads every row alone and marks one code:

- **C**, complete: a sentence gives the asked datum for the asked entity, as current;
- **P**, partial: a sentence gives part of the asked datum;
- **D**, discarded: a sentence gives a value for the asked entity and attribute that the text marks as
  rejected, superseded or negated;
- **M**, mention: the asked entity or subject appears without the datum;
- **F**, off: none of the above;
- **?**, cannot decide, with a one-line note; these rows are counted and left out.

Mapping, fixed now: "answers" is C for J-oracle, J-pool, J-reg, J-reg-2 and J-envelope, and C or P
for J-gold. The key `T` is compared with C. No model reads the sheet and nobody revises a code after
the first model call. The annotations are committed before the first model call; the runner refuses
to start without them. Reported: the rate at which the human reading and `T` disagree per stratum,
the weighted estimate over the 555, and every disagreeing row with its code and note.

## 7. Runs, money and stopping

- Order, fixed: J-closed, J-oracle, J-pool, J-reg, J-reg-2, J-envelope, J-gold, J-repass, J-premise.
  Within an instrument, the order of `pairs.json`. At most 4 calls in flight.
- Smoke: the first 10 units of each instrument in that order (queries for J-closed; for J-repass,
  up to 10 of the eligible pairs), counted in the ledger and excluded from every reading. The full
  run then calls every unit again, smoke units included.
- Retries: up to 5 attempts on timeouts, HTTP 429 and 5xx, as in the sources; none on other HTTP
  errors and none on an invalid response. A pair still without a valid label is missing and is
  reported per instrument and per stratum.
- One complete re-run of an instrument is allowed only if more than 10% of its units are missing; the
  decision reads the missing count only. The re-run replaces the first run as primary; both are
  published. J-reg-2 runs after the primary J-reg is settled.
- Ledger: `stage2/ledger.json` records every attempt with timestamp, instrument, unit, sha256 of the
  request body, HTTP status, usage returned and cost from `stage2/prices.json` (frozen with the tag).
  A call starts only if spent plus US$ 0.01 for every call in flight, including itself, stays at or
  under US$ 20. An instrument cut by the ceiling is reported as incomplete, with how far it got.
  Expected spend, from Paper A's recorded costs: under US$ 1.
- Keys come from the environment (`GEMINI_API_KEY`, `OPENAI_API_KEY`), never from a file in the
  repository.

## 8. Predictions carried over from Paper A

Each is read as "seen again" or "not seen again" and printed with its counts. P1 and P4 can be met by
a single case, and P3 by two runs that happen to agree; they are weak by design and are not a
validation of anything.

- P1: at least one J-oracle positive fails the 160-character check.
- P2: J-pool with the leg has lower kappa with J-reg than without it (undefined if either kappa is).
- P3: J-reg and J-reg-2 differ on no label.
- P4: J-envelope differs from J-reg on at least one label.
- P5: J-gold accepts at most 2 of the 50 random controls (under 5%), read together with its
  acceptance of the 59 correct gold: a judge that rejects everything meets P5.

Nothing is predicted about agreement with `T` or with the human reading.

## 9. Frozen files, review and amendments

Frozen by the tag, in `synthetic-ptbr/stage2/`: this file, `pairs.py`, `pairs.json`,
`human/SHEET.md`, `prompts.py`, `judges.py`, `run.py`, `analyze.py`, `prices.json`,
`citation-fixtures.json` and `test-stage2.py` (offline; it compares every copied prompt and the two
copied helpers with their sources, checks the population, the parsing, the citation fixtures and
the ceiling, and runs the analysis end to end on fabricated runs; `--sabotage` must fail).

Codex and Kimi challenged the first draft on 2026-11-25 (both "do not freeze"); this version answers
their findings, and the record of the round is in `PLANO.md`. After the tag, nothing in §2 to §8
changes; an error found in a script is fixed in a dated amendment that says what it changes and
whether any reading had been seen, and readings computed under the frozen scripts stay in the record.
