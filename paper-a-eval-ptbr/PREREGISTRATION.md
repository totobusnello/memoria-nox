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
  different build when the run starts, the run stops and the deviation is reported (§7).
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
- **Draw:** `holdout-draw.py`, seed `20261105`, refuses any database but the registered snapshot.
  One RNG; strata A to F; within a stratum the eligible source files sorted and shuffled, and one
  chunk per file uniformly at random. Every file gets a position, so a replacement is the next draw.
- **Writer:** `glm-5.3` (Z.ai), a family that is neither the embedder (Gemini) nor the judge
  (OpenAI), temperature 0, prompt `holdout-prompt.txt`: one PT-BR question a user would ask, in
  their own words, plus the verbatim passage of the chunk that answers it.
- **Validation, fixed now** (`holdout-generate.py`, `VALIDATION`): an output is accepted only if
  it is not IMPOSSIVEL; has the question on one line; the question has at most 25 words; the
  question shares no run of 4 or more consecutive words with the chunk; and the evidence, once
  whitespace is normalised, is a substring of the chunk of 30 to 300 characters. A rejected
  passage is replaced by the next draw of its stratum; replacements and their reasons are counted
  and published. The cache of every call is hashed into the commitment.
- **Gold:** for H-A1, the drawn chunk id, checked at scoring time by the sha256 of its text. For
  H-A2, the evidence span, which is what a reference has to keep reaching.
- **Lexical overlap, measured:** the share of the question's content words that occur in its chunk
  (question-side, so chunk length does not dilute it), and the longest run of shared words.

## 4. Hypotheses

**H-A1 (primary): the two annotation protocols still disagree upward on new queries.** Scored by
`score-holdout.sh`, on the path that scored v3: strict nDCG@10 (gold = the drawn chunk) and pooled
nDCG@10 (the top-10 of the production search, fully judged by `eval/judge-relevance.py` at
p > 0.5, union the gold), each with its own ideal. The estimand is the mean over queries of pooled
minus strict: the directional contrast between two complete scoring procedures. It is not a
correction of one by the other, and it can be negative for a query, because a newly judged
relevant document raises the ideal. The pool contains only what this one system returned.
Interval: 10,000 bootstrap resamples within strata (quotas kept), seed `20261105`. Reading with
margin 0.10: lower bound ≥ 0.10, holds; upper bound < 0.10, does not; otherwise inconclusive. In
development the pooled reading exceeded the strict one by more than this margin. A 6-query smoke
run suggests a half-width of roughly 0.04 at n = 120; that is a rough guide, not a power analysis.

**H-A2 (secondary): a reference by evidence keeps reaching the answer when a reference by chunk id
does not.** A natural experiment on the first daily snapshot dated 2026-11-18 or later
(`holdout-persistence.py`). A reference persists if it leads to an active chunk whose text still
contains the evidence span: by id, the chunk with the gold id; by anchor, any active chunk of the
same source file (more than one is reported as ambiguous). Precondition: churn over the chunks of
the drawn source files of at least 5%; below that, H-A2 is reported as not tested. Prediction:
persists by anchor ≥ 95% of queries, and by anchor minus by id ≥ 10 points.

**Blind human sample (registered, mandatory).** `human-sample.py make` draws 60 (query, chunk)
pairs uniformly at random from every pair the judge labelled, seed `20261105`, and writes a sheet
with the question and the first 6,000 characters of the chunk, without the judge's output. The
author grades it blind (`relevante`: s/n) before seeing H-A1. `human-sample.py agree` reports
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
3. On the serving host, from a checkout of the tag: `score-holdout.sh <snapshot> <holdout>
   <commitment commit>`. It reads the commitment from that commit, refuses if the commit does not
   descend from the tag or if any executed file changed, checks every hash, pins the configuration
   after the production `.env` is read, and works in a new private directory. `holdout-analyze.py`
   checks the input contract (120 queries, quotas, gold, judge configuration, labels) and refuses
   to print a reading unless it reproduces `audits/2026-10-27-v3-rescore.py`.
4. Human sample made from the labels and graded blind; then H-A1 is read.
5. H-A2 on or after 2026-11-18.
6. Every number in the paper has an entry in `PROVENANCE.json`.

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
