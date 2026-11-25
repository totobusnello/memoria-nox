# Running a memory ruler's failure mechanisms in public: a synthetic Portuguese corpus and two versions of nox-mem

Luiz Antonio Busnello · draft, 2026-11-25

## Abstract

Paper A (doi:10.5281/zenodo.24400444) reported five ways an evaluation ruler for agent memory misled
its authors, measured on a private corpus in Portuguese. Nobody outside can run those checks. This
note releases a small constructed corpus in Brazilian Portuguese (200 files, 45 planted facts, 5
false-premise questions) built so that the ground truth is known by construction and kept apart from
the labels an evaluator would record. On it we ran three of the five mechanisms against the
published nox-mem package at two pinned versions, one before and one after a change to how it
ingests files.

The results split the findings. Gold keyed by chunk id decays exactly as Paper A found under the old
ingest, which replaced every id of a file on each re-ingest; under the current ingest the id
survives re-ingests, edits elsewhere in the file and renames, and on a rename it outlives the
evidence anchor. Neither kind of reference notices a deleted file. The unjudged-as-miss symptom does
not appear on this corpus, because no question scores zero; registered labels err in both
directions instead. An ideal built from the ranking changed 5 of 45 scores. The corpus, the plan
that built it, the generation records, the frozen results and the code are released together.

## 1. Why a constructed corpus

Paper A's corpus is the working memory of a group of agents and cannot be released; the paper
publishes counts, hashes and code. Its method findings are claims about rulers, though, not about
that corpus, and a ruler can be exercised on any corpus whose truth is known. Two reviewers of the
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
- 0 to 3 paraphrases written by the planner with a variant form of the value ("4301 cópias"
  for "4.301 exemplares"), in other files;
- for 15 facts, a context negative: the same entity and attribute with a different invented
  value, rejected or superseded, labelled not relevant;
- for 4 facts, a duplicated primary, written as two identical sections;
- for 30 facts, one of six operations, applied to a file that holds that fact alone.

The latent truth T of a question is every chunk holding a positive of its fact. The registered
labels R keep the primary and each paraphrase with probability 0.25, drawn by the planner before
any ranking existed; 20 of the 50 questions have R smaller than T. Five more questions ask an
attribute that no file states (false premises).

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
chunk. Both versions cut the corpus into the same 851 chunks.

## 3. What was run

The two versions are nox-mem 3.5.2, the last release whose ingest deleted a file's chunks and
inserted them again, and 3.11.1, which keeps the id of every unchanged chunk and lets a renamed file
take over the chunks of the file it replaced. Ranking is the package's full-text path (BM25 with its
own boosts, top 10), queried with access tracking off so the probe does not feed the signals it
measures. Deletions and renames are passed through what each version's file watcher does on a path
that left the disk: 3.5.2 does nothing, 3.11.1 marks the file's chunks with a tombstone and keeps
them. The rules for classifying every outcome were committed before the first run.

For finding 1, two references are recorded for each operation fact on the fresh database: the id
of the chunk holding the primary sentence, and the anchor (recorded path and the whole sentence),
resolved by the resolver Paper A used with its prefix limit lifted. After the operations, a
reference is *live* if it reaches the sentence under the key of the file that holds it on disk now,
*stale* if it reaches the sentence in a chunk whose file is gone, moved or tombstoned, and *none*
if it reaches nothing.

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

Under the old ingest the finding holds as Paper A stated it: every re-ingest replaces every id, so an
id-keyed gold dies on the most routine operation while the anchor survives. Under the current ingest
it does not: the id survives a re-ingest and an edit to another section, and on a rename it is the
anchor, looked up by its recorded path, that fails. Paper A met the same reversal in its own data,
where a path migration left 119 questions reaching their evidence by id and 117 by anchor. Neither
reference notices a deletion: both still reach the deleted sentence, through chunks kept with or
without a tombstone.

### Finding 2: an unjudged result is not a miss

On the same frozen rankings, nDCG@10 under the
registered labels averaged 0.7542, against 0.7372 under the truth. No question scored zero under the
registered labels, so the symptom Paper A measured, a zero made almost entirely of results nobody
had judged (96.9% of the top 10 on its zero-scoring questions), has nothing to act on here: every
question's registered positive was retrieved. Instead, the registered labels erred in both
directions: the registered score sat above the truth on 12 questions, below it on 8 and equal on 25. It sits above
when a hidden positive was not retrieved (the ideal is too small) and below when one was retrieved
and counted as a miss. Pooled labels (the registered ones plus the true positives in the top 10)
cannot score below the truth, since they share its numerator and have an ideal no larger; that is
arithmetic. They scored above it on 5 of 45 questions. Removing exactly the pooled additions gave
back the registered score on all 45.

### Finding 4: an ideal built from the ranking measures ordering

Under the truth, replacing the
gold ideal with one built from the relevant chunks the ranking returned changed the score of 5 of
45 questions, by 0.2033 on average and at most 0.2441, always upward. The direction follows from
the definition; the corpus measures how often and how much.

Context negatives, which share the entity and the attribute with the question, ranked above its
first positive on 4 of 45 questions.

## 5. What this note claims, and what it does not

It claims that, on this corpus and these two pinned versions, the mechanisms behave as the table
and the counts above say, and that anyone can rerun them: the ingestion, ranking and operations from
the markdown files, the analysis from the frozen files alone.

It does not claim:

- that Paper A's numbers replicate; the corpus was built to exercise mechanisms, and five facts per
  operation support a description, not an estimate;
- anything about retrieval quality, of nox-mem or of BM25: the values are invented and unique, the
  questions name their entity, and a full-text ranker finds them easily, which is why finding 2 could
  not show its symptom here;
- independence from the generator: one model family wrote all the free text, with marks of its own
  that the release lists (a stock phrase in 181 of 200 files that came from the prompt's own
  example);
- that the corpus is uncontaminated for future use; it is public, so it is a regression fixture.

## 6. What transfers

Which of the two, id or anchor, is the safer key for gold depends on what the system's ingest does
to ids, and in this system that changed between two releases published the same day (3.5.2 and
3.6.0, on 2026-10-14). A ruler that must survive both should record both and report which one resolved. A deleted source is
invisible to both, so a ruler over a living memory also needs a check that its evidence is still
on disk. And reproducing finding 2 needs a corpus on which retrieval misses relevant chunks; this one is
too easy for it, which is the main thing a next version should change.

## 7. Data and code availability

Everything is in `synthetic-ptbr/` of the nox-mem research repository (github.com/totobusnello/memoria-nox):
the plan and its coverage table, the corpus, one generation record per file (system prompt, prompt,
every attempt, reported cost, model returned), the frozen results for both versions, and the code
with offline tests in which every gate passes on a valid state and fails on its infractor. The
corpus and plan are released under CC BY 4.0.

```sh
python3 -I synthetic-ptbr/test-synthetic.py
python3 -I synthetic-ptbr/method-tests.py --analyze --check
python3 -I synthetic-ptbr/method-tests.py --run --work <scratch dir>   # needs npm and the network
```

## References

Busnello, L. A. (2026). Five ways the ruler misleads: evaluating retrieval on a living Portuguese
agent memory. Zenodo. doi:10.5281/zenodo.24400444
