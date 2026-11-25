# Running a memory ruler's failure mechanisms in public: a synthetic Portuguese corpus and two versions of nox-mem

Luiz Antonio Busnello

Status: working draft, not deposited, not peer reviewed. A dataset with a short note: the corpus was
generated and both versions were run on 2026-11-25. `PROVENANCE.json` holds the source of every
decimal number and percentage in this note, and a gate checks each one against it.

## Abstract

Paper A (doi:10.5281/zenodo.24400444) reported five ways an evaluation ruler for agent memory misled
its authors, measured on a private corpus in Portuguese and English. Outsiders can rerun its scripts
on the published outputs but cannot redo its scoring. This note releases a small constructed corpus
in Brazilian Portuguese (200 files, 45 planted facts, 5 false-premise questions) whose ground truth
is known by construction and kept apart from the labels an evaluator would record. On it we ran
three of the five mechanisms against the published nox-mem package at two pinned versions, one
before and one after a change to how it ingests files.

Under the old ingest, a gold reference keyed by chunk id was lost on every re-ingest of its file
while the evidence anchor survived, as Paper A found. Under the current ingest the id survived a
re-ingest and an edit to another section, and in the one rename sequence we ran (rename, tombstone
on the old path, ingest of the new path) the id still reached the evidence while the anchor, looked
up by its recorded path, did not. Both references still reached the evidence after its file was deleted. Registered
labels that omit some true positives changed the score of all 20 questions where they were
incomplete, upward on 12 and downward on 8; no question scored zero, so the extreme case Paper A
measured did not occur. An ideal built from the ranking changed 5 of 45 scores. The corpus, the
plan that built it, the generation records, the frozen results and the code are released together.

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
the account-term check. A scan for every run of 8 words of the released package inside the private
corpus found none (99,999 runs against 65,208 private chunks); a positive control that planted one
private chunk in a copy of the package was caught.

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
| edit outside the planted sentence | append one fixed sentence to another `##` section, ingest |
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
In every *none* of this run the id no longer existed and the anchor resolved to no chunk; no anchor
was ambiguous.

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
another section, while the anchor survived both. That fits Paper A's account of the old ingest, in
which every re-ingest replaced every id of a file; the harness tracked only the primary's id, so the
table shows those five ids per operation, not every id in the file. Under 3.11.1 the id survived
both operations. In the rename sequence above, the id still reached the sentence under the new
path, and the anchor, looked up by its recorded path, reached nothing; with no re-ingest after the
rename, both stayed on the old, stale chunk. Paper A met the same reversal in its own data, where a
path migration left 119 questions reaching their evidence by id and 117 by anchor; over a longer
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
which is Paper A's mechanism, and it also leaves the registered ideal smaller. When the omitted
positive is ranked low, the smaller ideal outweighs the lost gain and the score rises: in 7 of the
12 questions that rose, every true positive was in the top 10. Registered and pooled scores
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

## 5. What this note claims, and what it does not

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
  that the release lists (a stock phrase in 181 of 200 files that came from the prompt's own
  example);
- that the corpus is uncontaminated for future use; it is public, so it is a regression fixture.

## 6. What transfers

Which of the two, id or anchor, is the safer key for gold depends on what the system's ingest does
to ids, and in this system that changed between two releases published the same day. A ruler that
must survive both should record both and report which one resolved. A deleted source stays
reachable by both unless the resolver checks for it, so a ruler over a living memory also needs
either a tombstone-aware resolver or a check that its evidence is still on disk. And reproducing
the zero-scoring case of finding 2 needs questions on which no registered positive is retrieved,
and labels that record which results a judge saw; this corpus has neither, which is the main thing
a next version should change.

## 7. Data and code availability

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
```

## References

Busnello, L. A. (2026). Five ways the ruler misleads: evaluating retrieval on a living Portuguese
agent memory. Zenodo. doi:10.5281/zenodo.24400444
