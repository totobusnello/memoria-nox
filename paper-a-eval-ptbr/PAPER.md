# Five ways the ruler misleads: evaluating retrieval on a living Portuguese agent memory

Draft, 2026-11-05. Not deposited. H-A2 (§4) is pending until 2026-11-18.

## Abstract

We report what went wrong, and what we changed, while building a retrieval benchmark for a
Portuguese-language agent memory that keeps changing while it is measured. The paper has two parts,
kept apart. The retrospective part documents five ways the ruler misled us during development:
gold keyed by chunk id decayed under re-ingest (61 of 85 cited ids were gone); results the oracle
never judged were scored as misses; an LLM judge claimed verbatim quotes that it had paraphrased,
and a citation check built on those quotes made agreement worse; an ideal built from the ranking
measured ordering instead of retrieval; and 38 of 95 gold entries did not answer their own
question, 21 of them because the gold pointed at the wrong file. These are findings of development, made
and repaired on the same queries. The prospective part was pre-registered and frozen by a tag before
it ran: 120 new questions, written by a model from passages drawn at random, scored on the
production search path. Pooled nDCG@10 minus strict nDCG@10 was +0.1933, with a stratified
bootstrap interval of [+0.1421, +0.2464], above the registered margin of 0.10. A blind human sample
of 60 pairs agreed with the LLM judge only at chance (Cohen's kappa 0.038), so the pooled figure,
which depends on the judge, is not validated by the human grader. We report the pair of scores as a
measure of how much a retrieval result depends on the annotation protocol, not as an interval around
a true value.

## 1. Introduction

A retrieval number for an agent memory is usually reported as if the ruler were fixed: a set of
questions, a gold answer for each, a metric. In the system we measure, none of the three stays put.
The corpus is re-ingested, so chunk ids change. The gold was written against one version of the
corpus and read against another. The relevance labels for what the system returns came, for most
of the development period, from an LLM, and the LLM's labels depend on how it is asked.

We built the ruler three times (v1, v2, v3) over October 2026, and each rebuild was triggered by
finding that the previous one reported something about the ruler instead of about the system. Five
of those findings recur in any benchmark built the same way, and they make up the retrospective
part (§3). None of them is a confirmation: queries, anchors, prompts and thresholds were changed
after looking at results on the same corpus.

The prospective part (§4) asks whether the central contrast of the retrospective part, that two
complete scoring procedures disagree substantially on the same rankings, reappears on questions the
system had never ranked. It was pre-registered, frozen by a tag, and run in the registered order.

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
the whole top-10 (568/568 pairs), and with complete labels the publishable interval is [0.26 · 0.44].

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
That check protects the citation, not the claim. Measured against a second judge from another model
family on all 510 v2 pairs, agreement (kappa) was 0.5458 with the first judge's own verdict and
0.4412 with the verdict after the citation check: the check cost 0.105 of kappa. Pairs that the
citation check had rejected were confirmed by the second judge at 51.0%, slightly more often than
pairs it had accepted (48.1%). The check was adding formatting noise, not precision.

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

### Fifth: the gold did not answer its own question

The second judge, asked about each of the 95 v2 gold entries against its own query on the resolved
chunk, accepted 57 and rejected 38. In 15 of the 55 queries every gold entry was rejected, so those
queries scored zero in the strict arm whatever the system returned. Two controls bounded this: the
judge accepted 1.8% of queries paired with a random chunk, and accepted both gold entries built
that day from an oracle pass.

Repairing the gold showed where the error was. Judging every chunk of the gold's own source file
repaired 6 of the 38 entries. Judging the corpus-wide BM25 top-40 repaired 21 of the remaining 22,
and in 21 of those 21 the answer lived in a different file: the recorded file was wrong, not the
chunk. v3 kept 58 entries, repaired or added 27, and left 1 query (1.8%) with no valid gold because
nothing in the corpus answers it.

We had predicted, from the count of invalid gold, that repairing it would raise strict nDCG by up to
37.5%. It rose from 0.2428 to 0.2567. The repaired queries were not being unfairly zeroed: they
scored 0.1679 after repair, 10 of 14 still at zero, against 0.2856 for the rest, and the strict zero-hit rate rose to 32/57 =
56.1%. A count of broken gold does not predict the direction or the size of the score change,
because a query can be mis-measured and also missed. The published v2 to v3 move,
+0.0139, also confounds gold, query set and corpus. Holding one ranking fixed and changing only the
gold gives +0.0106, with 16 queries moving (9 up, 7 down).

### How much the judge's own reading moves the ceiling

Two different operations measure the judge's stability, and they answer different questions. Sent
the identical request twice, in separate runs over 540 pairs, the judge changed no label: it is
deterministic for a given request. Re-asked the same predicate in a different request (one question
instead of two, the passage wrapped), it changed 4.5% of 620 v3 labels, 23 of the 28 flips in the
0.4–0.9 probability bands. The second is the one that matters for the score. It moves pooled by
−2.9%, so the v3 ceiling is a band, [0.427 · 0.439], not a four-decimal number. A stratified sample
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
300 characters found in the passage. The questions are synthetic and conditioned on passages, so
the conclusions hold for that population, not for questions people ask.

H-A1, the primary hypothesis, is that pooled minus strict nDCG@10 stays above 0.10 on these
questions. The estimand is the mean over queries of the difference between two complete scoring
procedures. The interval is a stratified bootstrap with 10,000 resamples within strata; the
registered reading is "holds" if the lower bound is at least 0.10, "does not hold" if the upper
bound is below it, and inconclusive otherwise.

### What ran, in order

| step | commit | content |
|---|---|---|
| tag | `6c6879b` | pre-registration, prompt, quotas, scripts |
| holdout commitment | `54048e4` | hashes and counts of the 120 questions |
| human commitment | `31d90b2` | hashes of the graded sheet, the scores and the labels |
| reading | `6120a37` | the printed outputs of the reading, unchanged |

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

On these questions the two complete procedures disagree in the same direction as in development,
and by more than the margin. Pooled is not a corrected strict. It scores a different set of relevant
documents, whatever this one system returned and the judge accepted, and it can fall below strict
for a query, because each newly judged relevant document also raises the ideal.

Descriptively, pooled exceeded strict on 57 queries, tied on 40 and fell below on 23. Strict scored
zero on 28.3% of queries and pooled on 8.3%. The judge accepted the gold as containing the answer
for 117 of the 120 questions; on those, the contrast was +0.1929. The contrast appears in every
tercile of question-side lexical overlap (strict 0.4801, 0.4660 and 0.5350; pooled 0.6351, 0.6890
and 0.7325, from low to high) and in every stratum, from A (0.5189 to 0.6471) to F (0.4029 to
0.7366). At the control's exploratory thresholds, pooled reads 0.7012 at p > 0.3 and 0.6629 at
p > 0.7.

### The human sample does not validate the judge

The author graded 60 pairs drawn at random from the 1,221, blind to the judge's labels, before H-A1
was read. Raw agreement with the judge at p > 0.5 was 0.433, and Cohen's kappa 0.038.

| | judge yes | judge no |
|---|---|---|
| grader yes | 19 | 31 |
| grader no | 3 | 7 |

No threshold was registered. The pre-registration says what follows from a kappa below 0.4: the
conclusions that depend on the judge are not validated by the grader. Pooled depends on the judge
and strict does not, so H-A1 is read as registered with this qualification. The disagreement runs
mostly one way: the grader marked 50 of 60 pairs as containing the answer, the judge 22. What a more
lenient judge would do to pooled has no fixed sign, because each added relevant document raises both
the gain and the ideal, and we do not compute pooled from 60 human labels. The grader was given the
judge's predicate, but the sheet's column was named `relevante`, and the run did not record whether
the grader applied the narrower predicate on every row.

This result is the strongest limit on the paper. In development the judge agreed with a second
model family at kappa 0.5458; on the holdout it agreed with a person at chance. The pair of scores
stands as a measure of protocol dependence, but its upper end is the judge's reading, and a person
reading the same passages saw more answers than the judge did.

### H-A2: pending

H-A2 asks whether a reference by evidence keeps reaching the answer when a reference by chunk id
does not, on the first daily snapshot of 2026-11-18. It is registered and not yet run.

## 5. Related work

Incomplete judgments are an old problem in test-collection evaluation. Zobel (1998) showed how
pooled collections under-count relevant documents for systems outside the pool, and measures such
as bpref (Buckley and Voorhees, 2004) and condensed lists (Sakai, 2007) were proposed so that an
unjudged document is not silently a miss. Our second finding is the same problem in a setting where the
"pool" is one system and the gold was found by an LLM. nDCG (Järvelin and Kekäläinen, 2002)
normalises by an ideal ranking, and our fourth finding is a reminder that the ideal has to be built from what is
known to be relevant, not from what was returned.

LLMs are now widely used as relevance assessors. Thomas et al. (SIGIR 2024) found LLM labels close
to searcher preferences, with LLM "relevant" verdicts more reliable than "not relevant" ones.
Takehi, Voorhees, Sakai and Soboroff (SIGIR 2025) study when an LLM should assist human assessment
rather than replace it. Gienapp et al. (SIGIR 2026) point out that a model used as a judge can also
be used as a ranker, so an LLM may confirm its own ranking decisions, and Keller et al. (SIGIR 2026)
show that formalising the information need changes LLM judgments, including their bias toward
positive labels. Our human sample agrees with Thomas et al. in direction on this corpus: the judge
said "no" where the person said "yes" far more often than the reverse.

Agent-memory benchmarks usually fix the corpus and the gold. We report what happens to a ruler when
neither is fixed, on one private corpus in Portuguese, and we do not claim the five findings
generalise beyond benchmarks built the same way.

## 6. Limitations

- One system and one corpus. The pool is what this system returned; pooled scores a different
  relevant set for any other system.
- The retrospective findings are development findings, measured and repaired on the same queries.
- The prospective questions are synthetic and passage-conditioned, written by one model, and they
  copy the development instrument's coverage of the corpus.
- The human sample is 60 pairs graded by one person, the author, who also built the system. It did
  not validate the judge.
- The corpus is private. The paper publishes counts, hashes and code; a reader can verify the chain
  of commits and the code, not the corpus.

## 7. Reproducibility

Every number in this paper has an entry in `PROVENANCE.json` naming the artifact, a locator string
that must occur in it, and the commit that holds it; `tools/provenance.py --check` fails on any
number printed without one, or printed after being superseded. The pre-registration, its five
review passes, the scripts, both commitments and the printed outputs of the reading are in the
repository. The holdout questions, the graded sheet and the labels are private and are identified
by their sha256.

## References

- Buckley, C. and Voorhees, E. M. (2004). Retrieval evaluation with incomplete information. SIGIR.
- Gienapp, L., Potthast, M., Yates, A., Scells, H. and Yang, E. (2026). Topic-specific classifiers
  are better relevance judges than prompted LLMs. SIGIR.
- Järvelin, K. and Kekäläinen, J. (2002). Cumulated gain-based evaluation of IR techniques. ACM TOIS.
- Keller, J., Fröbe, M., Engelmann, B., Haak, F., Breuer, T., Larsen, B., et al. (2026).
  Formalized information needs improve large-language-model relevance judgments. SIGIR.
- Sakai, T. (2007). Alternatives to bpref. SIGIR.
- Takehi, R., Voorhees, E. M., Sakai, T. and Soboroff, I. (2025). LLM-assisted relevance
  assessments: when should we ask LLMs for help? SIGIR.
- Thomas, P., Spielman, S., Craswell, N. and Mitra, B. (2024). Large language models can accurately
  predict searcher preferences. SIGIR.
- Zobel, J. (1998). How reliable are the results of large-scale information retrieval experiments?
  SIGIR.
