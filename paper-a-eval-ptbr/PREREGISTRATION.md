# Paper A, prospective part: pre-registration (DRAFT, not fixed)

Status: draft, revised after an adversarial review (§8). It becomes binding when the tag
`paper-a-prereg-v1.0` is pushed; nothing listed under "Order" may run before that push. Everything
retrospective in the paper is development and is reported as such (`README.md`).

## 1. Question

The retrospective part found that, on one PT-BR agent-memory corpus, what a retrieval evaluation
reports depends on how the gold is kept and labelled. Gold keyed by chunk id decayed under
re-ingest, and with the top-10 fully judged the v3 ruler read nDCG@10 0.2567 under the registered
gold and between 0.427 and 0.439 under pooled labels, a band set by how much a full re-read of the
labels moves them. All of it was measured on queries the ruler was built and repaired on.

This part asks whether the two central findings reappear on queries the system has never ranked.
The new queries are **synthetic and conditioned on passages**: a language model writes each one
from a passage drawn at random, so the test covers that population and not the questions people
ask. Its conclusions are stated for that population only.

## 2. Material

- **Corpus:** the production daily snapshot of 2026-11-04 03:00 UTC,
  `daily-main-main-20261104030005-…db.gz`, sha256
  `e04dfee9d7e0674cb043dc3362fefc24b7ec235acf6868365569106a322560a7`; decompressed, sha256
  `4ab1a94f7245c272177e184e0b465eeb795ab90813c91fb9afc1b6cf273a58ad`. Copied off the host the
  same day and verified by hash at both ends. Private; not published.
- **Search build:** the production `dist/` served when this document is fixed, identified by the
  sha256 of its sorted per-file hashes,
  `cd75e48d7e9517a7b2548f4d50feb1a381f9ea6de1d8686ae67d5303f532f07e`. If production serves a
  different build when the run starts, the run stops and the deviation is reported (§7). The
  `NOX_*` settings the build reads at run time are pinned the same way (sha256 of the sorted
  settings of the production `.env`, secrets and the database path excluded,
  `cd157cc97987f6fdd9b38a663ccfb47d872fa46869c79358cf1f9c6be3ec0f9a`).
- **Holdout:** 120 questions (§3), written and committed by hash before any system ranks them.

## 3. How the holdout is drawn and written

- **Frame:** chunks of the snapshot with `superseded_by` NULL and at least 200 characters, in six
  strata by the directory of their source file (`holdout-draw.py`, `stratum`). Two large parts of
  the corpus are outside the frame because no accepted v3 query has gold in them: the private
  document vault (4,721 files) and the nox-mem source tree (2,812 files). `frame-census.txt` has
  the counts. The ruler, and this test, cover the engineering and agent memory, not the vault.
- **Quotas:** derived by `derive-quotas.py` from the v3 gold, not typed: one count per (accepted v3
  query, stratum of one of its gold files), 72 pairs, allocated to n = 120 by largest remainder in
  integer arithmetic, ties broken by stratum letter. Result in `quotas.json`: A 30, B 19, C 18,
  D 17, E 23, F 13. The quotas copy where the development queries had their gold, so the holdout
  inherits the development instrument's coverage; this is stated, not corrected.
- **Draw:** `holdout-draw.py`, seed `20261105`, refuses any database but the registered snapshot
  and any quota but `quotas.json`; the generator recomputes the draw and refuses a draw file it
  does not reproduce.
  One RNG; strata A to F; within a stratum the eligible source files sorted and shuffled, and one
  chunk per file uniformly at random. Every file gets a position, so a replacement is the next draw.
- **Writer:** `glm-5.3` (Z.ai), a family that is neither the embedder (Gemini) nor the judge
  (OpenAI), temperature 0, prompt `holdout-prompt.txt`: one PT-BR question a user would ask, in
  their own words, plus the verbatim passage of the chunk that answers it.
- **Validation, fixed now** (`holdout-generate.py`, `VALIDATION`): an output is accepted only if
  it is not IMPOSSIVEL; has the question on one line; the question has at most 25 words; the
  question shares no run of 4 or more consecutive tokens with the chunk (tokens are split on
  whitespace and stripped of end punctuation only, so an identifier such as `a.b.c.d`, which the
  prompt allows verbatim, is one token); and the evidence, once
  whitespace is normalised, is a substring of the chunk of 30 to 300 characters. A rejected
  passage is replaced by the next draw of its stratum; replacements and their reasons are counted
  and published. The cache of every call is hashed into the commitment.
- **Gold:** for H-A1, the drawn chunk id, checked at scoring time by the sha256 of its text. For
  H-A2, the evidence span, which is what a reference has to keep reaching. The validation checks
  form, copying and the substring, not that the evidence answers the question: the gold is the
  reference the writer proposed, relevant by definition in both arms. The analysis reports how
  many golds the judge accepts (p > 0.5) and repeats pooled minus strict on those queries as an
  exploratory figure, with no reading attached; H-A2 is read as persistence of the proposed
  reference, not of a verified answer.
- **Lexical overlap, measured:** the share of the question's content words that occur in its chunk
  (question-side, so chunk length does not dilute it), and the longest run of shared words.

## 4. Hypotheses

**H-A1 (primary): the two annotation protocols still disagree upward on new queries.** Scored by
`score-holdout.sh`, on the path that scored v3: strict nDCG@10 (gold = the drawn chunk) and pooled
nDCG@10 (the top-10 of the production search, fully judged by `eval/judge-relevance.py` at
p > 0.5, union the gold; the labelled pairs must be exactly the top-10 plus the gold), each with
its own ideal. The estimand is the mean over queries of pooled
minus strict: the directional contrast between two complete scoring procedures. It is not a
correction of one by the other, and it can be negative for a query, because a newly judged
relevant document raises the ideal. The pool contains only what this one system returned.
Interval: 10,000 bootstrap resamples within strata (quotas kept), seed `20261105`. Reading with
margin 0.10: lower bound ≥ 0.10, holds; upper bound < 0.10, does not; otherwise inconclusive. In
development the pooled reading exceeded the strict one by more than this margin. A 6-query smoke
run suggests a half-width of roughly 0.04 at n = 120; that is a rough guide, not a power analysis.

**H-A2 (secondary): a reference by evidence keeps reaching the answer when a reference by chunk id
does not.** A natural experiment on the first daily snapshot of 2026-11-18
(`holdout-persistence.py`). A reference persists if it leads to an active chunk whose text still
contains the evidence span: by id, the chunk with the gold id; by anchor, any active chunk of the
same source file (more than one is reported as ambiguous). The frozen database is checked by its
hash and the commitment must be the registered one; the later snapshot is the daily `.gz` whose
name carries the date 2026-11-18 (one fixed day, so there is no later snapshot to choose), the
earliest of that day by the time in its name, and it must appear in a listing of the backup
directory; its hash is reported. Daily snapshots are kept 6 days, so the copy is taken by
2026-11-23; if no snapshot of 2026-11-18 exists, H-A2 is reported as not tested. Precondition:
at least 10% of the queries exposed, that is, with a gold id that no longer names an active chunk
with identical text (a gap of 10 points can only come from exposed queries); below that, H-A2 is
reported as not tested. Churn over the chunks of the drawn source files is reported as a
description. Prediction:
persists by anchor ≥ 95% of queries, and by anchor minus by id ≥ 10 points. Every share is
compared as an integer count.

**Blind human sample (registered, mandatory).** `human-sample.py make` draws 60 (query, chunk)
pairs uniformly at random from every pair the judge labelled, seed `20261105`, and writes a sheet
with the question and the first 6,000 characters of the chunk, without the judge's output. The
author grades it blind (`relevante`: s/n) before H-A1 is read: `score-holdout.sh` prints no
reading, and `read-h-a1.sh` refuses to run until `HUMAN-COMMITMENT.json` (the graded sheet's
sha256 and the counts, from `human-sample.py commit`) is in a commit that descends from the holdout
commitment. The sheet must be exactly the 60 drawn pairs, each with the question and passage the
judge saw (compared whitespace-normalised), and the analysis refuses a `labels.json` whose sha256
is not the one in the human commitment. `human-sample.py agree` reports
agreement and Cohen's kappa with the judge at p > 0.5. No threshold is registered; if kappa is
below 0.4, the paper states that its judge-dependent conclusions are not validated by a human.

**Descriptive, no threshold:** per-query direction of pooled minus strict; strict and pooled by
overlap tercile and by stratum; replacements and rejection reasons; rankings shorter than 10.

## 5. Order

1. This document, the prompt, `quotas.json` and the scripts are fixed by the tag
   `paper-a-prereg-v1.0`, pushed to the public repository. Smoke runs before the tag used other
   seeds (`--smoke-seed`); none used the registered seed.
2. Draw, then write the 120 questions. The holdout stays outside the repository; its sha256, n,
   per-stratum counts, replacements and the hashes of draw, prompt, cache and script are committed
   as `HOLDOUT-COMMITMENT.json` and pushed before step 3.
3. On the serving host, in a full clone of the public repository:
   `score-holdout.sh <snapshot> <holdout> <commitment commit>` scores and judges, and prints no
   reading, only the sha256 of `score.json` and `labels.json`. It executes the code extracted from
   the tag (`git archive`), not the working tree; reads the commitment from its commit, which must
   descend from the tag and be on `origin/main`, and records that commit in the workdir;
   checks the commitment's prompt and generator hashes against the tag, the snapshot, the build
   and the settings; pins the configuration after the production `.env`; and works in a new
   private directory.
4. Human sample made from the labels, graded blind, and `HUMAN-COMMITMENT.json` pushed: it
   carries the sha256 of the graded sheet, of `score.json`, of `labels.json` and of the holdout.
5. `read-h-a1.sh <workdir> <holdout> <human commit>` reads H-A1 from the same workdir. Before
   anything is computed it checks that the human commit is a later commit than the scored
   commitment's, descends from it, is on `origin/main`, carries the same `HOLDOUT-COMMITMENT.json`,
   and that the human commitment was made from this workdir's `score.json` and `labels.json`. A
   smoke run reads only a smoke commitment. `holdout-analyze.py` checks the input contract
   (the registered n and quotas, not only the commitment's; the human commitment; the committed
   question texts; the exact label set; the judge configuration) and refuses to print a reading
   unless it reproduces `audits/2026-10-27-v3-rescore.py`. That control script divides by the
   number of queries with a relevant chunk in their top-10; if no query has one, it stops on a
   division by zero, and H-A1 is then read as does not hold (with nothing relevant in any top-10,
   strict and pooled are both 0).
6. H-A2 on or after 2026-11-18.
7. Every number in the paper has an entry in `PROVENANCE.json`.

## 6. What this cannot show

That the findings hold on another corpus, another language or another system; that questions a
model writes from a passage behave like questions people ask; that the judge is right beyond what
the human sample measures; or anything about relevant documents the system never returned, since
the pool is this system's own top-10.

## 7. Deviations

Any change after the tag (a different search build, a failed call that cannot be retried, a
stratum whose frame runs out) is reported with the result, with what was done and why. None turns
a result that did not hold into one that did.

## 8. Review before fixing

Codex (gpt-6-astra) and Kimi (k3.1-pro) read the first draft and its scripts on 2026-11-05. Both
recommended against fixing it. What changed: quotas derived by script (the typed ones did not
reproduce); gold for H-A1 the drawn id, not a resolved prefix anchor; an input contract in the
analysis (the first version accepted 1 query of 60 and printed a reading); a stratified bootstrap;
n raised from 60 to 120; a symmetric criterion and a script for H-A2; validation rules in the
generator; overlap measured from the question's side; the build pinned and the configuration set
after the `.env`; a private `mktemp` workdir; the commitment read from its own commit; the human
sample made mandatory; and the claim narrowed to synthetic, passage-conditioned queries. A promise
to measure false "verbatim" citations was dropped: the registered judge returns no citation.

A second pass on the revised version, by Codex and DeepSeek (v4-pro), still recommended against
fixing it. Codex showed, with synthetic inputs, that the input contract accepted 5 queries all in
one stratum, that an extra positive label outside the pool changed the pooled score with both
controls passing, that the wrapper ran the working tree rather than the tag, that the prescribed
run printed H-A1 before the human grading, that 114/120 against 102/120 failed a gap of exactly
ten points in floating point, that the copy rule rejected a dotted identifier the prompt allows,
and that `derive-quotas.py > quotas.json` truncated its own input; DeepSeek found that H-A2 took
any later database and that the human sample size was not enforced. Each is fixed above, and each
fix was tested with an input that the previous version accepted.

A third pass, by the same two voices, again recommended against fixing it. Codex showed that the
reading could still be reached out of order (a smoke run read the registered holdout; the control
wrote strict and pooled before the human commitment was checked; the holdout commit was given
again by hand, and the same commit was accepted as both commitments), that `score.json` and
`labels.json` could be changed after the grading, that H-A2 accepted a later snapshot past a
caller-supplied listing, that a churn of 5% could pass with no gold exposed, and that the gold is
not checked to answer its question; DeepSeek found the same-day snapshot, the unchecked labels
hash, and that the graded sheet's text was not compared with what the judge saw. Each is fixed
above, or stated where it cannot be fixed (the gold's answerability), and each fix was tested.
