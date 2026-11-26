# Running a memory ruler's failure mechanisms in public: a synthetic Portuguese corpus and two versions of nox-mem

Luiz Antonio Busnello

Status: working draft, not deposited, not peer reviewed. A dataset with a short note: the corpus was
generated, both versions were run and Paper A's judges were re-run on it on 2026-11-25. `PROVENANCE.json` holds the source of every
decimal number and percentage in this note, and a gate checks each one against it.

## Abstract

Paper A (doi:10.5281/zenodo.24400444) reported five ways an evaluation ruler for agent memory misled
its authors, measured on a private corpus in Portuguese and English. Outsiders can rerun its scripts
on the published outputs but cannot redo its scoring. This note releases a small constructed corpus
in Brazilian Portuguese (200 files, 45 planted facts, 5 false-premise questions) whose ground truth
is known by construction and kept apart from the labels an evaluator would record. On it we ran
three of the five mechanisms against the published nox-mem package at two pinned versions, one
before and one after a change to how it ingests files.

Under the old ingest, a gold reference keyed by chunk id was lost when its file was re-ingested
unchanged or edited outside the evidence's section, while the evidence anchor survived, as Paper A
found. Under the current ingest the id survived both, and in the one rename sequence we ran (rename, tombstone
on the old path, ingest of the new path) the id still reached the evidence while the anchor, looked
up by its recorded path, did not. Both references still reached the evidence after its file was deleted. Registered
labels that omit some true positives changed the score of all 20 questions where they were
incomplete, upward on 12 and downward on 8; no question scored zero, so the extreme case Paper A
measured did not occur. An ideal built from the ranking changed 5 of 45 scores.

In a second, pre-registered step we re-ran Paper A's LLM judges, with their model ids, prompts and
request bodies, on 555 question–chunk pairs and read them against the planted key, which a blind
reading of 100 pairs by the author contradicted once. The judges found every planted positive but
one, and their other errors were acceptances. Among the pairs they judged were 15 planted
decoys: chunks giving the asked entity and attribute a value the text marks as rejected or
superseded. Every judge accepted some of these (from 7 to all 15), and they were half of all false
acceptances. The judge Paper A used to check its gold accepted all 59 correct entries, none of 50
random chunks and 12 of the 15 decoys; the pooling judge accepted the same 12, and the two agreed
with each other more than either agreed with the key. The citation check that lowered agreement in
Paper A removed one pair here; the corpus does not carry the formatting behind Paper A's case. The
corpus, the plan that built it, the generation records, the frozen results, both steps' code and
the step 2 runs are released together.

## 1. Why a constructed corpus

Paper A's corpus is the working memory of a group of agents and cannot be released; the paper
publishes counts, hashes and code. Its method findings, though, are claims about rulers, and a ruler
can be exercised on any corpus whose truth is known. Two reviewers of the
plan for this corpus (Codex and Kimi, run independently) made the same objection to its first draft:
a corpus whose labels are complete by construction cannot *reproduce* a finding that arose from
incomplete labels, and injecting id changes by script only shows that a broken pointer is broken.
The design below follows from that objection. The corpus therefore supports a public, executable
test of whether each mechanism produces its failure under stated conditions, and no independent
replication of Paper A's numbers.

## 2. The corpus

A planner with a fixed seed (20261125) writes the plan before any text exists: 200 files in the
forms of the private corpus (130 daily notes, 22 decisions, 20 lessons, 28 entity files with
frontmatter, compiled summary and timeline) for an invented publishing house, and 45 facts. Each
fact joins an entity to an attribute and an invented value that occurs nowhere else (a print run,
a cover price, a launch date, a contract code). Around each fact the plan places:

- a primary sentence with the value's literal form;
- 0 to 3 paraphrases written by the planner in other files, some with a variant form of the value
  ("4301 cópias" for "4.301 exemplares");
- for 15 facts, a context negative: the same entity and attribute with a different invented
  value, rejected or superseded, labelled not relevant;
- for 4 facts, a duplicated primary, written as two identical sections;
- for 30 facts, one of six operations, applied to a file that holds that fact alone.

The latent truth T of a question is every chunk holding a positive of its fact. The registered
labels R always hold the primary and keep each paraphrase with probability 0.25, drawn by the
planner before any ranking existed; 20 of the 45 fact questions have R smaller than T. The five
false-premise questions ask an attribute that no file states and are left out of the scores. T is
exact for the planted sentences and makes no claim about other text that might also answer a
question.

A language model (claude-sonnet-5-5) wrote the free text of each file around markers; the script
then put the planted sentences in place of the markers, so a value reaches the corpus only through
the planner. The model's text was refused, before assembly, if it held a digit, an e-mail address,
a link, any form of a planted value, or a term of the account the generator ran under. Every file
passed on its first attempt, at a reported cost of US$ 1.91. The generator ran in an empty
directory with no tools, settings, hooks, memory or MCP servers; the one piece of account context
the client attaches to every call (the account e-mail) could not be removed and is the reason for
the account-term check. A scan for every run of 8 words of the generated material (corpus, plan,
generation records and frozen results) inside the private corpus found none (99,165 runs against
65,211 private chunks, on the day of release); a positive control, run with an earlier scan of the
same kind, planted one private chunk in a copy of the package and was caught.

nox-mem cuts markdown into chunks only at `##` and `###` headings. A first assembly with no
sub-headings gave one chunk per file, which would have made any edit to a file an edit to its
planted sentence. The released corpus is split into `##` sections by the assembler, from the same
model text, and a gate checks after ingestion that every planted sentence lies whole in one chunk,
that each duplicate is two byte-identical chunks, and that each operation file has more than one
chunk. Both versions cut the corpus into the same 851 chunks, byte for byte, and returned identical
rankings for all 50 questions.

## 3. What was run

The two versions are nox-mem 3.5.2, whose ingest deleted a file's chunks and inserted them again,
and 3.11.1, which keeps the id of every unchanged chunk and lets a renamed file take over the chunks
of the file it replaced; 3.5.2 and 3.6.0, the first release with the new ingest, were published the
same day (2026-10-14). Ranking is the package's full-text path (BM25 with its own boosts, top 10),
queried with access tracking off so the probe does not feed the signals it measures.

No live file watcher ran. Where an operation removes a path, the harness calls the routine each
version's watcher runs on a path that left the disk: 3.5.2 has none and does nothing, 3.11.1 marks
the file's chunks with a tombstone and keeps them. The operations, each on five facts, are
these:

| operation | what the harness does |
|---|---|
| re-ingest, file unchanged | ingest the same path |
| edit outside the planted sentence | append one fixed sentence to the opening block, before the first `##`, ingest |
| edit inside (value replaced) | replace the value in the planted sentence with words, ingest |
| rename, then re-ingest | rename to `<name>-movido.md`, watcher routine on the old path, ingest the new path |
| rename, no re-ingest | rename to `<name>-movido.md` and nothing else (watcher down) |
| delete | remove the file, watcher routine on the old path |

The rules for classifying every outcome were committed before the first run.

For finding 1, two references are recorded for each operation fact on the fresh database: the id
of the chunk holding the primary sentence, and the anchor (recorded path and the whole sentence),
resolved by the resolver Paper A used with its prefix limit lifted. After the operations, each
reference is resolved directly in the database, with no search, and compared with the files on
disk. It is *live* if a chunk it reaches holds the whole sentence, under the key of a file that
holds the sentence on disk now and is not tombstoned; *stale* if it reaches the sentence only in a
chunk whose file is gone, moved or tombstoned; and *none* if no chunk it reaches holds the sentence.
In this run every id classed *none* no longer existed, and every anchor classed *none* resolved to
no chunk; no anchor was ambiguous.

## 4. Results

### Finding 1: gold keyed by chunk id decays

Five facts per operation:

| after the operation | 3.5.2: id / anchor | 3.11.1: id / anchor |
|---|---|---|
| re-ingest, file unchanged | none / live | live / live |
| edit outside the planted sentence | none / live | live / live |
| edit inside (value replaced) | none / none | none / none |
| rename, then re-ingest | stale / stale | live / none |
| rename, no re-ingest | stale / stale | stale / stale |
| delete | stale / stale | stale / stale |

Under 3.5.2 the five tracked ids were lost on a re-ingest of an unchanged file and on an edit to
the file's opening block, while the anchor survived both. That fits Paper A's account of the old ingest, in
which every re-ingest replaced every id of a file; the harness tracked only the primary's id, so the
table shows those five ids per operation, not every id in the file. Under 3.11.1 the id survived
both operations. In the rename sequence above, the id still reached the sentence under the new
path, and the anchor, looked up by its recorded path, reached nothing; with no re-ingest after the
rename, both stayed on the old, stale chunk. Paper A met the same reversal in its own data: a path
migration made three anchors miss their evidence and an unrelated edit made one id miss, leaving 119
questions reaching their evidence by id and 117 by anchor; over a longer
window spanning both ingests, its retrospective reading found the anchor reaching 404 of 406
surviving passages and the id 265. Replacing the value inside the sentence leaves nothing for either
reference to find, which is what a changed fact should do. After a deletion both references still
reach the deleted sentence, through chunks that 3.5.2 keeps and 3.11.1 keeps with a tombstone;
neither the id lookup nor the anchor resolver consults the tombstone.

### Finding 2: an unjudged result is not a miss

On the same frozen rankings, mean nDCG@10 was 0.7543 under the registered labels, 0.7372 under the
truth and 0.7598 under pooled labels (the registered ones plus the true positives in the top 10).
Every one of the 20 questions with incomplete labels changed score: 12 rose above the truth and 8
fell below it, and the other 25 were equal. The direction depends on where the omitted positives
sit. A true positive that was retrieved but not registered is counted as a miss in the numerator,
which is Paper A's mechanism, and it also leaves the registered ideal smaller. When omitting a
positive cuts the ideal by a larger share than it cuts the discounted gain, which happens when the
positive sits lower than the ones registered, the score rises: in 7 of the 12 questions that rose,
every true positive was in the top 10. Registered and pooled scores
therefore need not bracket the truth: on 5 questions both sat strictly above it.

What did not occur is the extreme case Paper A measured: a zero made almost entirely of results
nobody had judged (96.9% of the top 10 on its zero-scoring questions). R always holds the primary,
and every registered positive of every question was retrieved, so no question scored zero. The
harness also could not count such a case: its labels are sets of positives, so a chunk missing from
R might be one a judge rejected or one no judge saw, and Paper A's figure is about the second kind.

Pooled labels cannot score below the truth when the oracle is perfect, since they share its
numerator and have an ideal no larger; that is arithmetic, and it does not carry over to pooling
with a fallible judge, as in Paper A. Here they scored above the truth on 5 of 45 questions, the
five in which some true positive was ranked outside the top 10.

### Finding 4: an ideal built from the ranking measures ordering

Under the truth, replacing the gold ideal with one built from the relevant chunks the ranking
returned changed 5 of 45 scores, by 0.2033 on average over those five and at most 0.2441, always
upward. The direction follows from the definition; the corpus measures how often and how much.
These are the same five questions as in finding 2: since every registered positive was retrieved,
the pooled set equals the true positives in the top 10, and the pooled score equals the
ranking-ideal score on all 45. Here they are one observation, counted twice.

Context negatives, which share the entity and the attribute with the question, ranked above its
first positive on 4 of 45 questions, 4 of the 15 that had a negative.

## 5. Step 2: Paper A's judges against the planted key

For the judgements behind its third and fifth findings, Paper A had no adjudicated reference: nobody
had checked the pairs its judges labelled. This corpus has one by construction. Step 2 was
pre-registered (tag `synthetic-ptbr-stage2-prereg`, frozen on 2026-11-25 after a challenge round by
Codex and Kimi) and re-ran Paper A's judges with the same model ids, prompts and request bodies. The
prompts were copied by code from the scripts that ran them, and a test compares each with its source
(the gold check's by a pinned hash, since its script left the public tree for privacy) and checks the
request bodies field by field. The procedure is not identical: the oracle judged every pair without
the triage that used to pick its candidates, and its second pass took pairs rather than questions;
the pre-registration lists both. Three judges are prompts to `gemini-2.5-flash-lite`: an oracle asked
to quote its evidence, a pooling judge with the 8-word citation leg, and an 8-word second pass on
failed quotes. Four are requests to `gpt-6-luna` through OpenAI's Decisions API: the registered judge,
the same request sent again, the same predicate in another request envelope, and the gold check
behind Paper A's fifth finding ("does the recorded gold answer the question"). The same model id
does not prove the same weights.

The judges read 555 pairs: the top 10 of the frozen ranking for all 50 questions, the 5 true
positives ranked below it, and one random chunk per question. The key T marks planted evidence and
says nothing about meaning, so before any model call the author read a stratified sample of 100 pairs
blind, question and chunk only, and coded each (complete, partial, discarded value, mention, off).
The reading disagreed with T on one row, a partial answer that T counts as positive: a weighted
estimate of 0.0053 over the 555, from one reader. The judges are read against T below; the same
counts against the human reading, per stratum, are in the supplement.

One parser rule changed after the runs began. The pooling judge's first full run came back with 329
of 555 labels missing: 328 were "no" answers carrying a null quote, which the frozen parser read as a
missing label where the source scripts read an empty quote, and one response did not parse. The
registered re-run started and was stopped after 172 attempts; amendment 1 restored the source rule
and re-read the stored responses with no new call (`run.py <judge> reparse`), leaving one label
missing. Nothing had been compared with T or with the human reading before the fix. The ledger records
under US$ 1 in all. Some readings the pre-registration promised were not printed by the frozen
analysis; a dated supplement (`stage2/supplement.py`) computes them from the same stored labels, and
also holds the three post-hoc checks used below.

### Errors of acceptance

Every judge found every planted positive (89 of 89), except the gold check,
which missed one. Their other errors were acceptances, and they differed in how many. Precision
against T was 0.6096 for the quoting oracle (0.6268 under the full rule of its source, which also
requires a verified quote and a closed-book answer that did not already hold the answer), 0.8318 for the pooling
judge, 0.8641 for the registered judge, 0.89 in the other envelope and 0.88 for the gold check. The
15 context negatives were planted for this purpose: they give the asked entity and attribute a value
the text marks as rejected (8) or superseded (7). The oracle accepted all 15, the pooling judge 14,
the gold check 12, the registered judge 8 and the other envelope 7, and the author coded all 15 as a
discarded value. They were 12 of the gold check's 12 false positives, 14 of the pooling judge's 18,
8 of the registered judge's 14, 7 of the other envelope's 11 and 15 of the oracle's 57; across the
five judges, 56 of 112. These counts describe how the judges handle a decoy built
to test them; the overall precision depends on the mix of pairs, and nothing here measures how often
a live memory holds such decoys.

### The gold check, with a key

Asked whether a recorded gold entry answers its question, the gold
check accepted all 59 correct entries, none of the 50 random chunks drawn as Paper A drew them, and
12 of the 15 decoys presented as gold. A random-chunk control alone would have found no error in this
judge; the decoys found 12. This corpus cannot say whether Paper A's 38 rejections were right; its wrong gold is of one
planted kind.

### Agreement is not accuracy

The pooling judge accepted the same 12 decoys as the gold check. On
the 554 pairs both labelled, the two agreed at kappa 0.9584, more than either agreed with T on those
pairs (0.8886 and 0.9171). Of the six pairs of judges this is the closest; it is an example, picked
after seeing the table. Paper A warned that agreement between judges says nothing about precision;
here a shared error shows it.

### Pooled scores

Mean nDCG@10 over the 45 fact questions was 0.7372 under T and 0.7598 under pooling
with a perfect judge (section 4): the 5 true positives ranked below the top 10 drop out of the pooled
ideal. Pooling with the registered judge's positives gave 0.7688. Against perfect pooling, the judge's
labels raised 6 questions, lowered 5 and left 34 equal; on this ranking its false positives raised
the mean while lowering five scores.

### The citation leg

On this corpus the 8-word check removed one pooled positive, a pair T counts as
negative, and kappa with the registered judge rose from 0.906 to 0.9115, so Paper A's drop was not
seen again. That says little about Paper A. Its failures came from copyable formatting (table pipes,
`<u>`, an escaped currency sign) and from quotes that drift after 13 to 53 characters; here the
planted sentences have 43 to 95 characters and no chunk carries any of those formats. Offline
fixtures released with the step show the check vetoing a quote that drops those formats. The quoting
oracle's quote failed the check on 4 of its 146 positives, and the second pass verified 2 of those 4.

### False premises and stability

None of the Decisions requests labelled any of the 55
false-premise pairs as answering; the oracle labelled 4 and the pooling judge 1. A premise check
written for this step, since Paper A's was never committed, said that 6 of those 55 chunks supported
a premise the corpus never states; it is exploratory. As in Paper A, the identical request changed
none of 555 labels, and the other envelope changed 9, which moved pooled nDCG@10 from 0.7688 to
0.7652.

## 6. What this note claims, and what it does not

It claims that, on this corpus, these two pinned versions and the operations as the harness ran
them, the references and scores behave as the tables and counts above say, and that anyone can
check them: the analysis reruns offline from the frozen results and the plan, and the full run
redoes ingestion, ranking and operations from the markdown files.

It does not claim:

- that Paper A's numbers replicate; the corpus was built to exercise mechanisms, and five facts per
  operation are enough to describe and too few to estimate;
- that the rename result holds for other renames: every rename went to the same suffix in the same
  directory, in one order, through the watcher routine called directly rather than a live watcher;
- that *live*, *stale* and *none* say what a search would return; they describe direct resolution
  in the database against the disk;
- anything about retrieval quality, of nox-mem or of BM25: the values are invented and unique, the
  questions name their entity, and a full-text ranker finds them easily;
- independence from the generator: one model family wrote all the free text, with marks of its own
  that the release lists ("semana seguinte", "the following week", in 181 of 200 files, from the
  prompt's own example);
- that the corpus is uncontaminated for future use; it is public, so it is a regression fixture;
- that the judges of step 2 behave this way on other text: the planted positives are short and
  clean, the hard negatives are of two kinds (a rejected and a superseded value), and one reader,
  the author, coded the human sample;
- anything about Paper A's private pairs: step 2 describes the judges on this corpus, and settling
  what happened in Paper A would need a blind reading of those pairs.

## 7. What transfers

Which of the two, id or anchor, is the safer key for gold depends on what the system's ingest does
to ids, and in this system that changed between two releases published the same day. A ruler that
must survive both should record both and report which one resolved. When the ingest keeps
the chunks of a deleted file, as both versions did, the deleted source stays reachable by both
unless the resolver checks for it, so a ruler over a living memory also needs
either a tombstone-aware resolver or a check that its evidence is still on disk. And reproducing
the zero-scoring case of finding 2 needs questions on which no registered positive is retrieved,
and labels that record which results a judge saw; this corpus has neither, which is the main thing
a next version should change.

A ruler that pools with an LLM judge needs, among its controls, negatives that carry a plausible
value the text has discarded: on this corpus every judge accepted some of them, while the gold check
passed Paper A's random-chunk control without error. And agreement between two judges is not
evidence that either is right; on this corpus the two judges that agreed most closely shared twelve of
their errors, and only the key showed it.

## 8. Data and code availability

Everything is in `synthetic-ptbr/` of the nox-mem research repository (github.com/totobusnello/memoria-nox),
except the anchor resolver, which the full run calls from `eval/resolve-gold-anchors.py` in the same
repository: the plan and its coverage table, the corpus, one generation record per file (system
prompt, prompt, every attempt, reported cost, model returned), the frozen results for both versions
with the Node and better-sqlite3 versions they ran under, and the code with offline tests in which
every gate passes on a valid state and fails on its infractor. The corpus and plan are released
under CC BY 4.0. The commands run from the repository root:

```sh
python3 -I synthetic-ptbr/test-synthetic.py
python3 -I synthetic-ptbr/method-tests.py --analyze --check
python3 -I synthetic-ptbr/method-tests.py --run --work <scratch dir>   # npm, network
python3 -I synthetic-ptbr/stage2/test-stage2.py
python3 -I synthetic-ptbr/stage2/analyze.py --check
```

Step 2 is in `synthetic-ptbr/stage2/`: the pre-registration and its amendment, the population and
the blind sheet with the author's codes, the copied prompts, the runner with its ledger, every
request's stored response, and the analysis. `analyze.py --check` and `supplement.py --check` recompute every
step 2 number from the stored labels (`run.py <judge> reparse` re-reads the stored responses into
those labels); re-running the judges (`run.py`) needs the two providers' keys and is
not expected to return identical labels.

## References

Busnello, L. A. (2026). Five ways the ruler misleads: evaluating retrieval on a living Portuguese
agent memory. Zenodo. doi:10.5281/zenodo.24400444
