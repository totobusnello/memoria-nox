---
title: "Five ways the ruler misleads: evaluating retrieval on a living Portuguese agent memory"
author: "Luiz Antonio Busnello"
---

Status: working draft, not deposited, not peer reviewed. H-A2 (§4) ran on 2026-11-18 and is not tested; H-A2R, its retrospective form, ran on 2026-11-20 and holds on its primary reading (§5).
Every number in this text has an entry in `PROVENANCE.json`; §10 says how they are checked.

## Abstract

We report what went wrong, and what we changed, while building a retrieval benchmark for a
Portuguese-language agent memory that keeps changing while it is measured. The paper has two parts,
kept apart. The retrospective part documents five ways the ruler misled us during development:
gold keyed by chunk id decayed under re-ingest (61 of 85 cited ids were gone); results the oracle
never judged were scored as misses; an LLM judge claimed verbatim quotes that it had paraphrased,
and a citation check built on those quotes made agreement worse; an ideal built from the ranking
measured ordering instead of retrieval; and a second judge rejected 38 of 95 gold entries as not answering their own
question, and found an accepted passage in a different file for 21 of them. These are findings of development, made
and repaired on the same queries. The prospective part was pre-registered and frozen by a tag before
it ran: 120 new questions, written by a model from passages drawn at random and kept when they passed
fixed acceptance rules, scored on the production search path. Pooled nDCG@10 minus strict nDCG@10 was +0.1933, with a stratified
bootstrap interval of [+0.1421, +0.2464], above the registered margin of 0.10. A blind human sample
of 60 pairs showed chance-corrected agreement with the LLM judge near zero (Cohen's kappa 0.038),
so the pooled figure,
which depends on the judge, is not validated by the human grader. We report the pair of scores as a
measure of how much a retrieval result depends on the annotation protocol, not as an interval around
a true value. A second registered hypothesis, that a reference by evidence outlasts a reference by
chunk id, could not be tested: the system had stopped replacing a file's ids on every re-ingest
before the study began. Its retrospective re-registration over earlier copies of the database is
reported apart (§5).

## 1. Introduction

A retrieval number for an agent memory is usually reported as if the ruler were fixed: a set of
questions, a gold answer for each, a metric. In the system we measure, none of the three stays put.
The corpus is re-ingested, so chunk ids change. The gold was written against one version of the
corpus and read against another. The relevance labels for what the system returns came, for most
of the development period, from an LLM, and the LLM's labels depend on how it is asked.

We built the ruler three times (v1, v2, v3) over October 2026, and each rebuild was triggered by
finding that the previous one reported something about the ruler instead of about the system. Five
of those findings are risks for any benchmark built the same way, and they make up the retrospective
part (§3). None of them is a confirmation: queries, anchors, prompts and thresholds were changed
after looking at results on the same corpus.

The prospective part (§4) asks whether the central contrast of the retrospective part, that two
scoring procedures that judge the whole top-10 disagree substantially on the same rankings,
reappears on questions the system had never ranked. It was pre-registered, frozen by a tag, and run
in the registered order. A retrospective re-registration, over database copies that already existed,
is reported apart from it (§5).

Throughout, the pair `[strict, pooled]` is not an interval that contains a true nDCG. Completing the
gold changes the ideal as well as the gain, and pooled labels can carry judge errors in both
directions. The pair measures sensitivity to the annotation protocol. We also do not treat the LLM
judge as ground truth; the human sample (§4) is part of the design and its result limits what the
paper can claim.

## 2. Setting

The system is nox-mem, a hybrid memory for a group of software agents: SQLite FTS5 (BM25),
Gemini embeddings in sqlite-vec, and reciprocal rank fusion. The corpus is the agents' own working
memory, written in Portuguese and English: session transcripts, agent notes, engineering documents.
It is private; the repository is public, so this paper publishes counts, hashes and code, never
corpus text, questions or anchors. All scoring ran on the production search path against isolated
copies of the database.

The ruler had three versions.

- **v1** was an existing PT-BR golden set of 66 queries whose gold was a list of chunk ids.
- **v2** re-found gold with an LLM oracle over a pool of BM25 top-40 union KNN top-40 per query
  (65–80 distinct candidates), stored each gold entry as an evidence anchor instead of an id, and
  accepted 55 queries with 95 gold entries.
- **v3** repaired the v2 gold where it did not answer its question, added two queries, and judged
  the whole top-10 of every query: 57 queries, 85 gold entries.

Two arms are scored on the same rankings. Strict nDCG@10 counts only the registered gold as
relevant. Pooled nDCG@10 counts the gold plus every returned chunk the judge labels as containing
the answer, and builds its ideal from all relevant chunks known for the query. The judge is a
bounded predicate over the passage ("does the PASSAGE contain the answer to this QUESTION"), which
returns a probability; the registered cut is p > 0.5.

## 3. Retrospective: five ways the ruler misled us

Each finding below was made while building or scoring the ruler, and each changed the next
version. They are reported in the order they were found, with the population and the gold
version each was measured on. Two shorter sections follow, on the judge's stability and on
abstention, because both bear on how the numbers of the five should be read.

### First: gold keyed by chunk id decays

The v1 gold named chunk ids. After the corpus had been re-ingested, 61 of the 85 cited chunk ids
(71.8%) no longer existed. Half of the queries (50%) pointed only at ids that were gone, 18.2% had
some gold still alive, 22.7% had never had gold, and 9.1% were fully intact. Eighteen of 66 queries
were still usable as positives.

An id is a pointer into one build of the corpus. Re-ingest is a normal operation for a living
memory, not a fault, so a gold set keyed this way measures the age of the gold as much as the
system. v2 stored each gold entry as an evidence anchor: the source file plus a verbatim span of
the passage, resolved to a chunk at scoring time. Of the 95 v2 anchors, 91 resolved exactly, 4 were
ambiguous between an entity file and its copy, and none failed to resolve. After a later re-ingest
moved ids, all 91 still resolved; one anchor whose recorded id was 116814 now resolves to a chunk in
the 227xxx range.

Anchors have their own failure mode. One corpus file holds 93 chunks of which 47 are exact
duplicates, and an anchor cannot separate byte-identical chunks; 1.9% of chunk rows in the corpus
are duplicates, the largest cluster with 127 copies. The resolver therefore refuses wide ambiguity
instead of choosing: a self-test that plants an ambiguity with 897 hits must exit non-zero, and does.

### Second: an unjudged result is not a miss

When v2 was first scored, strict nDCG@10 was computed against gold found by the oracle, and the
oracle had judged only part of what the system returned. On queries that scored zero, 96.9% of the
top-10 had never been judged at all. A zero there says nothing about whether the system returned a
relevant chunk.

The first v2 report gave the pair [0.2428, 0.5114]: strict, and pooled after judging what the
system returned. Most of the distance between the two came from coverage, not from the system.
Holding v2's own rankings, gold and queries fixed and only completing the labels moves pooled
0.5114 → 0.4412, which is 97% of the drop from v2 pooled to v3 pooled. v3 judged
the whole top-10 (568/568 pairs), and with complete labels on the top-10 the published pair is [0.26 · 0.44].

A control that matters here: "reproducing strict" is a weak check when labels change, because
strict does not depend on them. The control we kept perturbs the labels instead. Flipping all 113
in-ranking labels collapses pooled onto strict exactly, which shows the pooled arm moves only
through the labels it is supposed to move through.

### Third: the judge cites what it paraphrased, and a check built on its citations made things worse

The v2 oracle was asked to quote the passage that answers the question. Of the judgements that
said the chunk answers, 34.5% quoted text that was not in the chunk: the quotes matched for 13–53
characters and then drifted into paraphrase, still presented as verbatim. When asked for only the
first eight words, seven of the unverified quotes did verify, which is what drift over length, rather
than invention, would produce.

The pooling then required each "relevant" label to carry an eight-word quote found in the chunk.
That check verifies the citation and says nothing about the claim. Measured against a second judge from another model
family on all 510 v2 pairs, agreement (kappa) was 0.5458 with the first judge's own verdict and
0.4412 with the verdict after the citation check: the check cost 0.105 of kappa. Pairs that the
citation check had rejected were confirmed by the second judge at 51.0%, slightly more often than
pairs it had accepted (48.1%). The check lowered agreement with the second judge and did not raise its confirmation rate; with
no independent reference, this says nothing either way about precision.

The judge also could not hold a negative. For a false-premise question, one with no answer in the
corpus, the oracle accepted gold on three chunks. With a prompt that asked it first to check the
premise, it still set the premise flag to true on all three, while its prose said the premise was
false.

### Fourth: an ideal built from the ranking measures ordering

nDCG divides by an ideal. Our first score for the second judge built that ideal from the relevant
chunks found inside the ranking, while both published arms carried the whole registered gold in
theirs. An ideal that counts only what the ranking returned cannot see a relevant chunk the system
failed to retrieve: one relevant item at rank 1 scores perfectly even where the corpus holds five. Under
that ideal, the second judge appeared to lower pooled by −6.8%. Rebuilt over the top-10 union the
gold (609 of 615 pairs labelled), the drop was −15.6%, from 0.5114 to 0.4315.

The same construction appears whenever a judge labels only what one system returned. In v3 we keep
it as a third column, labelled as ordering only: at p > 0.5 it reads 0.6984 on the development set,
a number that is not comparable to strict or pooled and is never reported as retrieval quality.

### Fifth: a second judge rejected much of the gold

The second judge, asked about each of the 95 v2 gold entries against its own query on the resolved
chunk, accepted 57 and rejected 38. In 15 of the 55 queries every gold entry was rejected; if those rejections are right, a
correct answer elsewhere in the corpus could not raise their strict score. Two controls bounded this: the
judge accepted 1.8% of queries paired with a random chunk, and accepted both gold entries built
that day from an oracle pass. No person checked the 38 rejections; the count is the second judge's.

Repairing the gold, with the same judge, suggested where the error was. Judging every chunk of the gold's own source file
repaired 6 of the 38 entries. Judging the corpus-wide BM25 top-40 repaired 21 of the remaining 22,
and in 21 of those 21 the accepted passage was in a different file: by this procedure, the
recorded file was wrong, not the chunk. v3 kept 58 entries, repaired or added 27, and left 1 query (1.8%) with no valid gold because
the search found nothing that answers it.

We had predicted, from the count of invalid gold, that repairing it would raise strict nDCG by up to
37.5%. It rose from 0.2428 to 0.2567. The repair did not lift the repaired queries much: they
scored 0.1679 after repair, 10 of 14 still at zero, against 0.2856 for the rest, and the strict zero-hit rate rose to 32/57 =
56.1%. A count of broken gold does not predict the direction or the size of the score change,
because a query can be mis-measured and also missed. The published v2 to v3 move,
+0.0139, also confounds gold, query set and corpus. Holding one ranking fixed and changing only the
gold gives +0.0106, with 16 queries moving (9 up, 7 down).

### How much the judge's own reading moves the pooled score

Two different operations measure the judge's stability, and they answer different questions. Sent
the identical request twice, in separate runs over 540 pairs, the judge changed no label: in those runs an identical
request returned identical labels. Re-asked the same predicate in a different request (one question
instead of two, the passage wrapped), it changed 4.5% of 620 v3 labels, 23 of the 28 flips in the
0.4–0.9 probability bands. The second is the one that matters for the score. It moves pooled by
−2.9%, so the v3 pooled reading is a range, [0.427 · 0.439], between two wordings
of the same predicate, not a four-decimal number. A stratified sample
of 60 pairs had first suggested a flip rate of 20.0%; it over-weighted the unstable bands and also
understated the effect on the score.

### Abstention, measured three ways

The ruler also carries 23 constructed negatives, questions with no answer in the corpus. Measured
by the registered detector (five refusal substrings), the system abstained on 0.696 of negatives and
on 0.200 of answerable questions, a gap of 0.496. This figure stays the primary one. A judge reading
of the same 48 answers gives 0.7826, 0.3200 and a gap of 0.4626, as a reference. A structural
predicate, an answer with no citation, gives a gap of +0.4157 and agrees with the judge better
(kappa 0.8754); it measures a different thing (an answer that anchors nothing in context) and is
reported as such. 17.4% of negatives got an answer that asserted a concrete datum with no hedge, all
of them cited. All three figures describe the system before the no-citation rule went into serving
on 2026-10-27.

## 4. Prospective: a pre-registered test on new questions

This part was written down before it ran, and it ran in the order written. It tests one
contrast from the retrospective part on questions the system had never ranked, and it reports a
blind human check of the judge that the design made mandatory.

### Design

The pre-registration (`PREREGISTRATION.md`) was frozen by the tag `paper-a-prereg-v1.0` before any
of the steps below ran, after five rounds of adversarial review recorded in its §8. Every script
reads the code of the tag, and refuses to run out of order.

The corpus is the production daily snapshot of 2026-11-04, identified by hash. The frame is the
non-superseded chunks of at least 200 characters, in six strata by source directory. The private
document vault (4,721 files) and the nox-mem source tree (2,812 files) are outside the frame,
because no accepted v3 query has gold there. Quotas per stratum were derived from the v3 gold by
script: A 30, B 19, C 18, D 17, E 23, F 13. The holdout therefore inherits the development
instrument's coverage.

A single seeded draw (seed 20261105) gave one passage per source file. A writer model from a
third family (`glm-5.3`; the embedder is Gemini and the judge OpenAI) wrote one PT-BR question per
passage and a verbatim evidence span, under validation rules fixed in advance: no output marked
impossible, at most 25 words, no run of four words copied from the passage, and evidence of 30 to
300 characters found in the passage. The validation checks form, copying and the substring, not
that the evidence answers the question: the passage the writer was given counts as relevant in both
arms by definition. The questions are synthetic and conditioned on passages, so the conclusions
hold for questions this pipeline wrote and accepted, not for questions people ask.

H-A1, the primary hypothesis, is that pooled minus strict nDCG@10 stays above 0.10 on these
questions. The estimand is the mean over queries of the difference between two scoring procedures
that judge the whole top-10. The interval is a stratified bootstrap with 10,000 resamples within strata; the
registered reading is "holds" if the lower bound is at least 0.10, "does not hold" if the upper
bound is below it, and inconclusive otherwise.

### What ran, in order

| step | commit | content |
|---|---|---|
| tag | `c473958` | pre-registration, prompt, quotas, scripts |
| holdout commitment | `248d361` | hashes and counts of the 120 questions |
| human commitment | `0adbdca` | hashes of the graded sheet, the scores and the labels |
| reading | `abdf7bf` | the printed outputs of the reading, unchanged |

The hashes are those of the public history after a rewrite on 2026-11-08 that gave new hashes to the 168
commits made from 2026-10-22 on;
the repository maps them to the earlier ones (`docs/history-rewrite-2026-11-08-commit-map.txt`).

Each commitment file was written once on the public main branch, after the tag; every script that
reads one refuses if any other commit has touched it. The writer took 171 calls for 120 accepted
questions; 51 drawn passages were replaced by the next draw of their stratum (26 marked impossible,
17 copied from the passage, 8 with evidence that failed the checks). Replacements were uneven: 23 in
stratum E for a quota of 23, 2 in A for a quota of 30.

Scoring ran on the serving host from the code of the tag, with the production build and settings
checked against registered hashes, and each of the 120 gold chunks verified by the hash of its text.
The judge labelled 1,221 pairs with no errors. The scoring step printed nothing but two hashes, and
the human sample was graded before the reading.

### H-A1 holds

Over the 120 queries, pooled minus strict nDCG@10 was +0.1933, interval [+0.1421, +0.2464]. Strict
was 0.4939 and pooled 0.6872. The input contract passed (120 queries in the registered quotas, and
1,187 of 1,187 top-10 pairs judged), and a second implementation of the scoring reproduced both
figures to the fourth decimal.

On these questions the two procedures disagree in the same direction as in development,
and by more than the margin. Pooled is not a corrected strict. It scores a different set of relevant
documents, whatever this one system returned and the judge accepted, and it can fall below strict
for a query, because each newly judged relevant document also raises the ideal.

Descriptively, pooled exceeded strict on 57 queries, tied on 40 and fell below on 23. Strict scored
zero on 28.3% of queries and pooled on 8.3%. The judge accepted the gold as containing the answer
for 117 of the 120 questions; the other three count as relevant in both arms by definition, as
registered. On the 117, the contrast was +0.1929. At the control's exploratory
thresholds, pooled reads 0.7012 at p > 0.3 and 0.6629 at p > 0.7. The contrast appears in every
tercile of question-side lexical overlap and in every stratum (both tables generated by
`manuscript-tables.py`):

| overlap tercile | n | strict | pooled |
|---|---|---|---|
| low | 37 | 0.4801 | 0.6351 |
| mid | 42 | 0.4660 | 0.6890 |
| high | 41 | 0.5350 | 0.7325 |

| stratum | n | strict | pooled |
|---|---|---|---|
| A | 30 | 0.5189 | 0.6471 |
| B | 19 | 0.3559 | 0.6000 |
| C | 18 | 0.3873 | 0.5568 |
| D | 17 | 0.6306 | 0.8470 |
| E | 23 | 0.6092 | 0.7677 |
| F | 13 | 0.4029 | 0.7366 |

### The human sample does not validate the judge

The author graded 60 pairs drawn at random from the 1,221, blind to the judge's labels, before H-A1
was read. Raw agreement with the judge at p > 0.5 was 0.433, and Cohen's kappa 0.038.

|  | judge yes | judge no |
|---|---|---|
| grader yes | 19 | 31 |
| grader no | 3 | 7 |

No threshold was registered. The pre-registration says what follows from a kappa below 0.4: the
conclusions that depend on the judge are not validated by the grader. Pooled depends on the judge's labels
and strict does not, although strict depends on gold that another model proposed and nobody checked
for answering; H-A1 is read as registered with this qualification. The disagreement runs
mostly one way: the grader marked 50 of 60 pairs as containing the answer, the judge 22. What a more
lenient judge would do to pooled has no fixed sign, because each added relevant document raises both
the gain and the ideal, and we do not compute pooled from 60 human labels. The grader was given the
judge's predicate, but the sheet's column was named `relevante`, and the run did not record whether
the grader applied the narrower predicate on every row.

This result is the strongest limit on the paper. In development the judge agreed with a second
model family at kappa 0.5458; on the holdout its chance-corrected agreement with a person was near zero. The pair of scores
stands as a measure of protocol dependence, but its upper end is the judge's reading, and a person
reading the same passages saw more answers than the judge did.

### H-A2: not tested

H-A2 asks whether a reference by evidence keeps reaching the answer when a reference by chunk id
does not, on the first daily snapshot of 2026-11-18. It ran on that snapshot and is not tested:
the registered precondition needs at least 12 of the 120 gold ids to have changed, and 1 had. That
one was changed by an edit of the author's on 2026-11-16, outside the study. By id, 119 queries
still reached their evidence; by anchor, 117; by neither, none.

The anchor did worse than the id, the reverse of the prediction. An exploratory check, written
after the reading, traced the difference to a path rename. A migration on 2026-11-11 renamed the
source keys of three stratum-F notes and kept their chunk ids, so the anchor, which looks the
source file up by its recorded path, no longer found them. Apart from the author's edit, the system
re-chunked nothing in the window. `RESULTS.md` has the run, the counts and the
deviation.

The pre-registration missed why the system re-chunked nothing. On
2026-10-14, three weeks before H-A2 was registered, the production ingest changed (nox-supermem#42).
Before that date every re-ingest of a file deleted all of its chunks and inserted new ones, so any
edit to a file changed the ids of all its chunks; that is the behaviour behind the 61 of 85 lost
ids in §3. Since that date a re-ingest compares the file's chunks by section and text, keeps the id
of every chunk whose text did not change, and lets a renamed file take over the ids of its old
chunks. Under the current code an id is still lost when its own chunk changes, as the one exposed query
shows; what stopped is the replacement of every id of a file on each re-ingest, which produced the
exposure H-A2 was sized for. An anchor is lost when a path changes without a re-ingest, as in the
migration above. H-A2 stays not tested, and its object is unchanged.

An amendment registered on 2026-11-19 (`AMENDMENT-H-A2.md`, tag `paper-a-h-a2-amendment-v1.0`)
reads H-A2 once more, unchanged except for the date, on the first daily snapshot of 2027-05-18.
That reading is pending, and §5 does not replace it.

## 5. Retrospective: H-A2R, registered over a window that had already happened

This section is not prospective. Copies of the production database from earlier dates still
existed, so the H-A2 question was registered a second time (`PREREGISTRATION-H-A2R.md`, tag
`paper-a-h-a2r-prereg-v1.0`) over a past window: from 2026-05-04 to 2026-11-18, across both ingest
regimes. The registration came after H-A2 was not tested, and its author knew the main events of
the window: the cleanups, the renames and the change of ingest. Expecting evidence to leave the
corpus, it made the primary reading conditional on the evidence surviving. That choice was
registered before the run, but it was an informed one, and the reading below is not an independent
confirmation of H-A2.

Six copies, each fixed by its hash. That they are one database over time rests on their documented
provenance and on schema checks, not on a test that could fail. 510 references were drawn on the
first, stratified like the holdout (stratum C had no eligible file on that date), each a 12-token
passage chosen mechanically and unique in its file; the criterion and thresholds are those of H-A2.

The primary reading is over the 406 references whose passage was still somewhere in the corpus at
the end. Of those, 141 were exposed; at the last copy the chunk id still reached its passage for 265
and the anchor, source path plus passage, for 404. The reading holds. Over all 510, the form H-A2
used, it does not hold: 104 passages had left the corpus, mostly from the imported documents of
stratum A, and no reference reaches evidence that is gone. None of the 85 sampled entity references
(stratum D) kept its chunk id over the window, and every one kept its anchor. The reading compares
the first copy with the last: six observations do not show that a reference stayed reachable in
between, and a few passages left the corpus and came back. The passages are arbitrary, not answers,
and the window is one history of one system; `RESULTS.md` has the counts per database and per
stratum.

## 6. Related work

Incomplete judgments are an old problem in test-collection evaluation. Zobel (1998) showed that pooled collections leave many relevant documents unjudged, so recall is overestimated, although in his leave-one-out test the relative ranking of systems held up. Measures such as bpref (Buckley and Voorhees, 2004) and condensed lists (Sakai, 2007) were proposed so that an
unjudged document is not silently a miss. Our second finding is the same problem in a setting where the
"pool" is one system and the gold was found by an LLM. nDCG (Järvelin and Kekäläinen, 2002)
normalises by an ideal ranking, and our fourth finding is a reminder that the ideal has to be built from what is
known to be relevant, not from what was returned.

LLMs are now widely used as relevance assessors. Thomas et al. (SIGIR 2024) found LLM labels close
to searcher preferences, with LLM "relevant" verdicts more reliable than "not relevant" ones.
Takehi, Voorhees, Sakai and Soboroff (SIGIR 2025) study when an LLM should assist human assessment
rather than replace it. Gienapp et al. (SIGIR 2026) take up the criticism that the same model can be both ranker and judge, so an LLM may confirm its own ranking decisions, and propose topic-specific classifiers as judges instead; Keller et al. (SIGIR 2026)
show that formalising the information need changes LLM judgments, including their bias toward
positive labels. Our human sample agrees with Thomas et al. in direction on this corpus: the judge
said "no" where the person said "yes" far more often than the reverse.

Agent-memory benchmarks usually fix the corpus and the gold. We report what happens to a ruler when
neither is fixed, on one private corpus in Portuguese, and we do not claim the five findings
occur elsewhere; they are risks to check in benchmarks built the same way.

## 7. Limitations

- One system and one corpus. The pool is what this system returned; pooled scores a different
  relevant set for any other system, neither arm estimates recall over the corpus, and a judge,
  writer and embedder from different model families need not make independent errors.
- The retrospective findings are development findings, measured and repaired on the same queries.
- The prospective questions are synthetic and passage-conditioned, written by one model, and they
  copy the development instrument's coverage of the corpus. They are the questions that passed the
  acceptance rules: passages hard to turn into a question are under-represented within a stratum.
- The second judge's rejections in §3, and the repair that used the same judge, were not checked by
  a person.
- H-A2R was registered with knowledge of the window it reads, and rests on documented lineage (§5).
- The human sample is 60 pairs graded by one person, the author, who also built the system. It did
  not validate the judge.
- The corpus is private. The paper publishes counts, hashes and code; a reader can verify the chain
  of commits and the code, not the corpus.

## 8. Release

The pre-registration, its five review passes, every script, both commitments and the printed
outputs of the reading are in the public repository, under `paper-a-eval-ptbr/`, from the tag
`paper-a-prereg-v1.0` onward. The holdout questions, the graded sheet and the judge's labels name
passages of a private corpus; they stay outside the repository and are identified by their sha256
in the commitments.

## 9. Data availability

The corpus is the private working memory of a group of agents and is not released. Counts, hashes
and code are. A reader can verify the chain of commits, rerun every keyless script on the
committed outputs, and check each number against its source; a reader cannot rerun the scoring
without the corpus.

## 10. Sources of the numbers in this text

Every number in this paper has an entry in `PROVENANCE.json` naming the artifact, a locator string
that must occur in it, and the commit that holds it. `tools/provenance.py --check` fails on any
number printed without one, or printed after being superseded except where the entry declares the
passage as history. The tables are generated by `manuscript-tables.py`, whose `--check` fails
unless each one appears here exactly as generated.

## References

- Buckley, C. and Voorhees, E. M. (2004). Retrieval evaluation with incomplete information. SIGIR.
- Gienapp, L., Potthast, M., Yates, A., Scells, H. and Yang, E. (2026). Topic-specific classifiers
  are better relevance judges than prompted LLMs. SIGIR.
- Järvelin, K. and Kekäläinen, J. (2002). Cumulated gain-based evaluation of IR techniques. ACM TOIS.
- Keller, J., Fröbe, M., Engelmann, B., Haak, F., Breuer, T., Larsen, B., et al. (2026).
  Formalized information needs improve large-language-model relevance judgments. SIGIR.
- Sakai, T. (2007). Alternatives to Bpref. SIGIR.
- Takehi, R., Voorhees, E. M., Sakai, T. and Soboroff, I. (2025). LLM-assisted relevance
  assessments: when should we ask LLMs for help? SIGIR.
- Thomas, P., Spielman, S., Craswell, N. and Mitra, B. (2024). Large language models can accurately
  predict searcher preferences. SIGIR.
- Zobel, J. (1998). How reliable are the results of large-scale information retrieval experiments?
  SIGIR.
