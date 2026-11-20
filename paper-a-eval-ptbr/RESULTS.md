# Paper A, prospective part: results

H-A1 read on 2026-11-05 and H-A2 on 2026-11-18, in the order `PREREGISTRATION.md` §5 fixes; H-A2R, pre-registered separately in `PREREGISTRATION-H-A2R.md`, read on 2026-11-20. Nothing here changes a registered
rule; where the run departed from the expected path, it says so.

## The chain that was checked before anything was computed

| step | commit on `origin/main` | what it holds |
|---|---|---|
| tag `paper-a-prereg-v1.0` | `6c6879b` | the pre-registration, the prompt, `quotas.json` and every script |
| holdout commitment | `54048e4` | sha256 and counts of the 120 questions, written once, after the tag |
| human commitment | `31d90b2` | sha256 of the graded sheet, of `score.json` and of `labels.json`, written once |
| reading | `6120a37` | `results/h-a1-2026-11-05.txt` and `results/v3-rescore-2026-11-05.txt`, copied unchanged |

The holdout came from the registered draw (seed `20261105`) on the frozen snapshot of 2026-11-04.
The writer model (`glm-5.3`, the model the provider reported serving) took 171 calls for 120
accepted questions: 51 drawn passages were replaced by the next draw of their stratum (26 answered
IMPOSSIVEL, 17 copied four or more consecutive words of the passage, 8 gave an evidence span that
failed the checks). Replacements were uneven across strata: 23 in E for a quota of 23, 2 in A for
a quota of 30.

`score-holdout.sh` ran on the serving host from the code of the tag, checked the production build
and settings against their registered hashes, and verified each of the 120 gold chunks by the
sha256 of its text in a fresh copy of the snapshot. The judge labelled 1,221 pairs with no errors.
The script printed only the two output hashes; `results/run-2026-11-05.sha256` keeps them.

## H-A1 holds

Over the 120 queries, pooled minus strict nDCG@10 is **+0.1933**, with a stratified bootstrap
interval of [+0.1421, +0.2464]. The registered reading is "holds" when the lower bound is at least
0.10, and it is. Strict nDCG@10 is 0.4939; pooled is 0.6872. The input contract passed (120
queries in the registered quotas, the top-10 fully judged: 1,187 of 1,187 pairs), and the control
script reproduced both figures to the fourth decimal. It did not stop on its exploratory
thresholds, so the rule for that case was not needed.

The interval is wider than the rough guide in §4, which came from a 6-query smoke run and was
labelled as not a power analysis.

What the result says, and only this: on new questions, written by a model from passages drawn at
random from the live corpus, the two complete scoring procedures disagree in the same direction
and by more than the margin, as they did in development. Pooled is not a corrected strict. It
scores a different set of relevant documents (whatever this one system returned and the judge
accepted), and it can be lower than strict for a query, because each newly judged relevant
document also raises the ideal.

## The human sample does not validate the judge

The author graded 60 pairs drawn at random from the 1,221, blind to the judge's labels, before
H-A1 was read. Raw agreement with the judge at p > 0.5 is 0.433; Cohen's kappa is 0.038.

| | judge yes | judge no |
|---|---|---|
| grader yes | 19 | 31 |
| grader no | 3 | 7 |

No threshold was registered for this figure. §4 says what follows from a kappa below 0.4: the
conclusions that depend on the judge are not validated by the grader. Pooled depends on the judge;
strict does not. H-A1 is therefore read as registered, with this qualification attached to it.

The disagreement runs mostly one way. The grader marked 50 of the 60 pairs as containing the
answer; the judge marked 22, so on this sample the judge is the stricter rater. What a more
lenient judge would do to pooled has no fixed sign, since each added relevant document raises both
the gain and the ideal, and the paper does not compute pooled from 60 human labels. One more fact about the sample: the sheet's column is named
`relevante`, and the grader was given the judge's narrower predicate ("does the PASSAGE contain the
answer to this QUESTION"). The run did not record whether the grader applied that predicate on
every row.

## Descriptive, not tested

None of these was registered as a test.

Per query, pooled exceeds strict on 57 queries, ties on 40, and falls below on 23. With no hit
from the gold in the top-10, strict scores zero on 34 of the 120 queries (28.3%); pooled scores
zero on 10 (8.3%). The judge says the gold chunk contains the answer for 117 of the 120 questions.
On those 117, pooled minus strict is +0.1929.

By the lexical overlap between question and passage, measured from the question's side:

| tercile | n | strict | pooled |
|---|---|---|---|
| low | 37 | 0.4801 | 0.6351 |
| mid | 42 | 0.4660 | 0.6890 |
| high | 41 | 0.5350 | 0.7325 |

By stratum:

| stratum | n | strict | pooled |
|---|---|---|---|
| A | 30 | 0.5189 | 0.6471 |
| B | 19 | 0.3559 | 0.6000 |
| C | 18 | 0.3873 | 0.5568 |
| D | 17 | 0.6306 | 0.8470 |
| E | 23 | 0.6092 | 0.7677 |
| F | 13 | 0.4029 | 0.7366 |

The contrast appears in every tercile and every stratum. At the control's two exploratory judge
thresholds, pooled is 0.7012 (p > 0.3) and 0.6629 (p > 0.7); strict does not change.

## H-A2 is not tested

Run on 2026-11-18. Too few gold ids changed between the two snapshots for the test to be read, so
H-A2 is reported as not tested, as `PREREGISTRATION.md` §4 requires.

**The run.** On the serving host, one SSH session listed the backup directory
(`results/h-a2-listing-2026-11-18.txt`; with sizes and times, `results/h-a2-listing-long-2026-11-18.txt`),
took the sha256 of the earliest snapshot named 2026-11-18
(`daily-main-main-20261118030003-…db.gz`, `abbf0274…a16d`, `results/h-a2-origin-2026-11-18.sha256`)
and copied it, with the listing, to the research host. The hash at the destination matched. The
session ran from 14:36:21Z to 14:37:29Z. `holdout-persistence.py` ran on the research host from a
fresh clone of `origin/main`, where the script, `holdout-draw.py` and `quotas.json` are byte-identical
to the tag. It checked the frozen database against its registered hash and read the commitment
from its commit on `origin/main` (`248d361`, the same commit as `54048e4` above, renamed by the
history rewrite of 2026-11-08; see `docs/HISTORY-REWRITE-2026-11-08.md`). The output,
unchanged, is `results/h-a2-2026-11-18.txt`.

**What it printed.**

| | count |
|---|---|
| exposed queries (gold id gone, superseded or with changed text) | 1 of 120; the precondition needs 12 |
| reached by id | 119 of 120 |
| reached by anchor | 117 of 120 (6 of them ambiguous) |
| reached by neither | 0 |
| churn over the chunks of the 120 drawn source files (descriptive) | 96 of 1394 |

**Deviation.** The one exposed query is the result of an edit by the author, not of the system. On
2026-11-16 the author removed exact duplicate lines from five memory files and dated undated
entries, outside this study. One of those files holds the gold of one holdout query (stratum B,
`memory/lessons.md`). The edit re-chunked the file and the gold id disappeared; its evidence span
is still in the file, once. Without that edit, exposure in the window would have been 0 of 120.
It does not change the outcome: with or without it, H-A2 is not tested.

**Exploratory, not registered: why the anchor did worse than the id.** The prediction was the
reverse. `h-a2-anchor-diagnosis.py`, written after the reading, lists the queries behind the
difference (paths and counts only; `results/h-a2-anchor-diagnosis-2026-11-18.txt`):

- The three queries reached by id and not by anchor are all in stratum F, notes of the `nox` agent
  stored under `../agents/nox/memory/`. On 2026-11-11 a migration in the production system
  (nox-mem#64) renamed those source keys to `agents/nox/memory/` by UPDATE. The chunk ids stayed
  and the text did not change, but no active chunk is left under the old path, so an anchor that
  looks for the source file by its recorded path finds nothing.
- The exposed query is the stratum-B edit above. The anchor still reaches it.

In this window the two changes that touched the gold were a path rename and a manual edit. The
system re-chunked nothing on its own, and a re-chunk is the case H-A2 was written to measure. The
reading here is limited to that: the anchor as registered, a source path plus an evidence span,
breaks when a path is renamed, and this window had no re-chunk to show what the id does in one.

**Exploratory, not registered: why there was no re-chunk.** The production ingest changed on
2026-10-14 (nox-supermem#42, `nox-mem/src/lib/chunk-sync.ts`), three weeks before the
pre-registration, which did not take it into account. Before that date a re-ingest deleted every
chunk of the file and inserted new ones, so an edit anywhere in a file changed all of its ids.
Since then a re-ingest compares chunks by section and text, keeps the id of every chunk whose text
did not change, and a renamed file takes over the ids of its old chunks. The one exposed query fits
this: its file was edited, the gold id is gone, and the evidence span is still in the file. Under the current
code the id fails only when its own chunk's text changes, and the anchor fails when a path changes
without a re-ingest. The failure mode H-A2 was registered to measure no longer occurs in this
system.

## H-A2R: the primary reading holds; the H-A2 form does not

Run on 2026-11-20 (`PREREGISTRATION-H-A2R.md`), once, from a fresh clone of the tag
`paper-a-h-a2r-prereg-v1.0` on the research host, between 10:36Z and 10:38Z. The six inputs matched
their registered sha256. The output, unchanged, is `results/h-a2r-2026-11-20.txt`; its hash and the
hash of the private file of drawn references are in `results/h-a2r-2026-11-20.sha256`.

**Lineage.** All six databases passed: `chunks` with the three required columns and `quick_check`
ok. `MAX(id)` rises at every date (212262 on 2026-05-04 to 347273 on 2026-11-18). The four
databases up to 2026-10-11 have no `superseded_by`, so every chunk in them counts as active, as
registered.

**Draw.** 510 references, not 600. Stratum C (`events/mac/`) had no eligible file on 2026-05-04,
so its quota of 90 went undrawn; the pre-registration keeps what a stratum has and reports the
shortfall. Every other stratum met its quota; 13 chunks in B and 6 in F had no unique span and were
replaced.

**Reading.**

| | primary: span still in the end database | secondary: all drawn (H-A2 form) |
|---|---|---|
| references | 406 | 510 |
| exposed | 141 | 245 |
| reached by id | 265 | 265 |
| reached by anchor | 404 (3 ambiguous) | 404 |
| reading | holds | does not hold |

Primary: the population is above 120 and exposure above a tenth of it; by anchor 404 of 406 clears
the bar of 386, and anchor minus id is 139 references, above the 41 the 10-point margin needs.
Secondary: by anchor 404 of 510 is below the bar of 485. The 104 references between the two
populations are those whose span is in no active chunk of the end database; neither reference can
reach them.

**Descriptive, no threshold.**

| database | by id | by anchor | span present anywhere | exposed |
|---|---|---|---|---|
| 2026-08-23 | 361 | 475 | 476 | 149 |
| 2026-09-08 | 360 | 475 | 476 | 150 |
| 2026-10-11 | 287 | 396 | 397 | 223 |
| 2026-11-04 | 265 | 404 | 406 | 245 |
| 2026-11-18 | 265 | 404 | 406 | 245 |

The id first stopped reaching its span on 2026-08-23 for 149 references, on 2026-10-11 for 73, on
2026-11-04 for 22 and on 2026-09-08 for 1; the anchor first stopped on 2026-08-23 for 35, on
2026-10-11 for 79, on 2026-11-04 for 15 and on 2026-11-18 for 1. "First" counts a reference once,
including the few whose span came back in a later database.

| stratum | n | span present at the end | by id | by anchor |
|---|---|---|---|---|
| A (`shared/imports/`) | 150 | 68 | 54 | 66 |
| B (memory notes and lessons) | 95 | 76 | 48 | 76 |
| D (`memory/entities/`) | 85 | 85 | 0 | 85 |
| E (`shared/`) | 115 | 113 | 99 | 113 |
| F (agents, sessions, top level) | 65 | 64 | 64 | 64 |

**Against the expectations stated before the run** (`PREREGISTRATION-H-A2R.md` §1): exposure passed
the precondition, as expected. Stratum A lost much of its evidence, as expected: the span of 82 of
its 150 references is gone from the corpus. The expected loss of the anchor in stratum F did not
happen: the anchor reached all 64 F references whose span survived. Whether any F reference sat
under a `../agents/` path at the start was not printed and is not inferred here.

**What it says, and only this.** Over six and a half months of this system's history, among
references whose evidence was still in the corpus, the evidence span under its recorded path
reached it 404 times in 406, and the chunk id 265 times. No entity reference (stratum D) kept its
id, and every one kept its anchor. The window mixes the old ingest, which replaced a file's ids on
every re-ingest, with the new one. The largest loss of evidence itself (present anywhere, 476 to
397) falls between 2026-09-08 and 2026-10-11, the window of the September cleanups. The references
are arbitrary 12-token passages drawn mechanically, not answers to questions.
