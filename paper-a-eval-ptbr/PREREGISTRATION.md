# Paper A, prospective part: pre-registration (DRAFT, not fixed)

Status: draft for review. It becomes binding when the tag `paper-a-prereg-v1.0` is pushed; nothing
listed under "Order" below may run before that push. Everything retrospective in the paper is
development and is reported as such (`README.md`).

## 1. Question

The retrospective part found that, on one PT-BR agent-memory corpus, the number a retrieval
evaluation reports depends heavily on how the gold is kept and labelled: gold keyed by chunk id
decayed (61 of 85 ids dead), and with the top-10 fully judged the v3 ruler reads nDCG@10 0.2567
under the registered gold and between 0.427 and 0.439 under pooled labels, a band set by how
much a full re-read of the labels moves them. All of it was measured on queries the
ruler was built and repaired on. This part asks whether the two central findings hold on queries
the system has never ranked.

## 2. Material

- **Corpus:** the production daily snapshot of 2026-11-04 03:00 UTC, file
  `daily-main-main-20261104030005-…db.gz`, sha256 `e04dfee9d7e0674cb043dc3362fefc24b7ec235acf6868365569106a322560a7`, copied off the host the same
  day and verified by hash at both ends. It is private and is not published.
- **Holdout queries:** 60 new PT-BR questions written by a language model from passages drawn at
  random (§3). Written, then committed by hash (§5), before any system ranks them.

## 3. How the holdout is drawn and written

- **Frame:** chunks of the snapshot with at least 200 characters of text, grouped in six strata by
  the directory of their source file, in proportion to where the 57 accepted v3 queries have their
  gold. Allocation for n = 60 (largest remainder over 73 query-directory pairs): `shared/imports`
  15; files at the root of `memory/` and `memory/lessons` 10; `events/mac` 9; `memory/entities` 8;
  the rest of `shared/` 12; sessions, agents, docs and files at the corpus root 6. Two large parts of
  the corpus are outside the frame because no accepted v3 query has gold in them: the private
  document vault (4,721 files) and the nox-mem source tree (2,812 files). The ruler, and therefore
  this test, covers the engineering and agent memory, not the vault.
- **Draw:** within each stratum, one source file uniformly at random, then one chunk of it
  uniformly at random, seed `20261105`, without replacement of source files. The draw script and
  its output (chunk ids only, kept private) are fixed before generation.
- **Writer:** `glm-5.3` (Z.ai), a family that is neither the embedder (Gemini) nor the judge
  (OpenAI), temperature 0. One question per chunk, in Brazilian Portuguese, answerable from the
  chunk alone, phrased as a user of the memory would ask it and told not to copy phrases from the
  passage. The prompt is fixed in `holdout-prompt.txt` before the draw.
- **Gold:** the drawn chunk, stored as (source_file, verbatim anchor), the format the v2 repair
  introduced. A question the writer marks as unanswerable from the chunk is replaced by the next
  draw of the same stratum; replacements are counted and reported.
- **Known bias, measured rather than fixed:** a question written from its answer tends to reuse the
  answer's words, which favours lexical retrieval. The lexical overlap between each question and its
  chunk (Jaccard over content words) is recorded, and every result is also reported by overlap
  tercile.

## 4. Hypotheses

**H-A1 (primary): annotation sensitivity holds on new queries.** On the holdout, scored by the
production search path exactly as `audits/2026-10-27-score-v3.sh` scores v3, pooled nDCG@10
(the top-10 fully judged by the bounded judge of 2026-10-26 at p > 0.5, union the gold) minus strict
nDCG@10 (gold = the drawn chunk only) is at least 0.10. Estimate with a 95% bootstrap interval over
queries (10,000 resamples, seed `20261105`). Reading: lower bound ≥ 0.10, holds; upper bound
< 0.10, does not; otherwise inconclusive. In development the v3 interval was 0.183 wide.

**H-A2 (secondary): chunk-id gold decays; anchored gold does not.** A natural experiment, not a
forced re-ingest: running the production re-ingest against a copy is ruled out, because in May 2026
that command ignored its isolation twice and wrote to the served database. On the first daily
snapshot dated 2026-11-18 or later, count (a) the holdout gold chunk ids of 2026-11-04 that still
name the same chunk text, and (b) the anchors that resolve. Prediction: (b) ≥ 95%, and (b) − (a)
≥ 10 points. Precondition, checked first: across the whole corpus, at least 5% of the 2026-11-04
chunk ids must no longer name the same text; otherwise no re-ingest happened in the window and H-A2
is reported as not tested, with the churn figure.

**Descriptive, no threshold:** strict and pooled nDCG@10 by overlap tercile; the share of the
judge's "verbatim" citations that are not in the chunk (34.5% in development); agreement between the
judge and a blind human on a stratified sample of judged pairs, if a human grader is available (who
grades is decided before the sample is drawn).

## 5. Order

1. This document, `holdout-prompt.txt`, the draw script and the scoring wrapper are fixed by the tag
   `paper-a-prereg-v1.0`, pushed to the public repository.
2. Draw, then generate the 60 questions. The holdout file stays outside the repository; its sha256,
   n and per-stratum counts are committed as `HOLDOUT-COMMITMENT.json` and pushed **before** step 3.
3. On the serving host, from a checkout of the tag: `score-holdout.sh` (fresh copy of the snapshot,
   hash checked; anchors resolved on the copy; strict through `eval/run-gold-eval.mjs`; the whole
   top-10 judged by `eval/judge-relevance.py` at p > 0.5; `audits/2026-10-27-v3-rescore.py`; then
   `holdout-analyze.py`, which refuses to print a reading unless it reproduces both). The sha256 of
   the production `dist/search.js` is recorded with the result. H-A2 after 2026-11-18.
4. Report every number with its entry in `PROVENANCE.json`.

## 6. What this cannot show

That the findings hold on another corpus, another language or another system; that LLM-written
questions behave like a person's (they come from the answer); that the bounded judge is right. It
tests whether two properties of the evaluation found during development reappear on queries the
development never saw.
