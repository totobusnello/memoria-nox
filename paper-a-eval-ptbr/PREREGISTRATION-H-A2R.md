# Paper A, H-A2R: a retrospective test of reference persistence (pre-registration)

Status: draft. It becomes binding when the tag `paper-a-h-a2r-prereg-v1.0` is pushed to the
public repository; nothing under §5 runs before that push. H-A2 (`PREREGISTRATION.md` §4), its
reading of 2026-11-18 and its amendment for 2027-05-18 (`AMENDMENT-H-A2.md`) are separate and
are not changed by this document.

## 1. Why, and what was known when this was written

H-A2 asked whether a reference by evidence (a source path plus an evidence span) keeps reaching
the evidence when a reference by chunk id does not. Read on 2026-11-18, it was not tested: 1 of
120 gold ids had changed in the window. The cause is in `RESULTS.md`: since 2026-10-14 a re-ingest
keeps the id of every unchanged chunk, so the two weeks after the frozen snapshot had almost no
churn to measure.

Copies of the production database from earlier dates still exist. This test uses them to ask the
same question over a window that has already happened, from 2026-05-04 to 2026-11-18. The window
covers the period the hypothesis was written about, when every re-ingest replaced a file's ids,
and the events a stored reference actually meets in this system.

The author knew these events before writing this, and states them so the reading can be judged
against them:

- 2026-05-19: an evaluation ingest wrote into the production database; legacy chunks were lost and
  restored from a snapshot.
- 2026-08-24 to 2026-09-07: the production ingest was stopped by a missing binary; a catch-up
  re-ingested 13 files on 2026-09-07.
- June to September: cleanups removed tens of thousands of chunks, among them duplicate chunks and
  whole imported directories under `shared/imports/` (stratum A).
- 2026-10-14: the ingest started keeping ids of unchanged chunks (nox-supermem#42).
- 2026-11-11: a migration renamed `../agents/…` source keys to `agents/…` and kept their ids
  (nox-mem#64).
- H-A2's counts between 2026-11-04 and 2026-11-18 (`RESULTS.md`), and chunk counts of copies
  from 2026-08-26 to 2026-09-08 (read for Paper 2) and of 2026-11-04 (this paper).

No persistence of any reference between these databases has been measured, and the 2026-05-04
database has not been opened for this study. The author expects exposure to pass the
precondition, expects stratum A to lose much of its evidence to the cleanups (which is why the
primary reading conditions on the evidence still existing, §4), and expects the rename of
2026-11-11 to cost the anchor in stratum F.

## 2. Material

Copies of the production database, private, on the research host. Each is identified by sha256;
`h-a2r.py` refuses any other file.

| date | file | sha256 | what it is |
|---|---|---|---|
| 2026-05-04 (start) | `nox-mem-snapshot-20260504-0616.db` | `03cd8f55afd3a57b4ff71e7427bce40401796132a1b1d1e54cf8c6345f136e93` | copy taken 2026-05-04 06:16 UTC for the Paper 1 experiments; modification time unchanged since 06:17 |
| 2026-08-23 | `e20260823T090002Z.db` | `6247e6889feb2e423fbf32a89a68882b1cefe9b4117649e276a726aa6071164b` | daily serving epoch |
| 2026-09-08 | `corpus-preservado-20260908.db` | `b277bc96d0223a2360ac54ad81f451bf7dea9a05687fceacc6feef194634b47d` | preserved at the end of the Paper 2 trial |
| 2026-10-11 | `compact-main-20261011230147-…db` | `d1cd2b57bdf7a1a1d0163b7e37ccf839f2492e7dcfd613e094c3979a6399aa07` | pre-operation snapshot taken before a `compact`, preserved |
| 2026-11-04 | `snapshot.db` | `4ab1a94f7245c272177e184e0b465eeb795ab90813c91fb9afc1b6cf273a58ad` | the frozen snapshot of Paper A (`PREREGISTRATION.md` §2) |
| 2026-11-18 (end) | `daily-main-main-20261118030003-…db.gz` | `abbf0274bdaae1a05e175d5afa4e72649cc27b0354a455e29b15a3073fa1a16d` | the daily snapshot H-A2 read |

**Lineage.** That these are copies of one production database rests on their documented
provenance, not on a test: testing it by whether ids persist would use the outcome. Before drawing,
the script prints for each database the columns of `chunks`, `PRAGMA quick_check`, the row and
active counts and `MAX(id)`. If the start or the end has no `chunks(id, source_file, chunk_text)`
or fails the check, the test is not run and that is reported; a failing intermediate database is
dropped from the descriptive counts and reported. A database without `superseded_by` has every
chunk active. If a copy were not of the production database, its ids would be unrelated; since a
reference by id persists only if its chunk still contains the span, an unrelated id cannot count
as persisting, but it would count as exposed.

## 3. Draw and evidence spans

- **Frame**, on the start database only: active chunks of at least 200 characters, in the six
  strata of `strata.py`, the holdout's. Paths are as recorded on 2026-05-04.
- **n = 600**: five times `quotas.json`, so A 150, B 95, C 90, D 85, E 115, F 65. Larger than the
  holdout because nothing is written by a model; the cost does not change with n.
- **Order:** seed `20261120`; strata A to F; within a stratum the eligible source files sorted and
  shuffled; passes over that order take, per file, one untried eligible chunk uniformly at random,
  until the quota is met. A stratum with too few chunks keeps what it has, and the shortfall is
  reported.
- **Evidence span:** 12 consecutive whitespace tokens of the chunk's normalised text, from a start
  drawn uniformly, accepted if it has 30 to 300 characters and occurs exactly once in the active
  chunks of its source file. Up to 20 starts are tried; a chunk with no accepted span is replaced
  by the next draw, and rejections are counted.
- The span is mechanical so that nothing chooses it by what will survive and no model is paid.
  These references are not questions and not evidence a writer picked as an answer; they are
  arbitrary passages, likely less distinctive than the holdout's spans.
- The references (ids, paths, spans) are written only to the private work directory; the script
  prints their sha256 and never prints a chunk text, path or span.

## 4. Hypothesis and reading

**H-A2R: over 2026-05-04 to 2026-11-18, a reference by evidence keeps reaching its evidence when a
reference by chunk id does not.** The criterion is H-A2's: a reference persists if it leads to an
active chunk of the end database whose whitespace-normalised text contains the span. By id, the
chunk with the drawn id; by anchor, any active chunk with the same source path (more than one is
reported as ambiguous). Exposed: the drawn id no longer names an active chunk with the same text.

- **Primary population:** the references whose span is still contained in some active chunk of the
  end database, under any path. Evidence that left the corpus is lost to both references and says
  nothing about which is better; conditioning on its presence anywhere uses neither the id nor the
  path, so it favours neither.
- **Precondition:** the primary population has at least 120 references, and at least 10% of it is
  exposed. Otherwise H-A2R is reported as not tested.
- **Prediction:** H-A2's thresholds, fixed on 2026-11-05: persists by anchor ≥ 95% of the
  population, and by anchor minus by id ≥ 10 points. All comparisons in integers.
- **Secondary:** the same precondition (exposure only) and prediction over all drawn references,
  the form H-A2 used.

**Descriptive, no threshold:** the counts by id, by anchor, present anywhere and exposed on each
database in date order; for each arm, the first database where it no longer reaches the span; the
counts at the end by stratum; the lineage figures and the draw's rejections and shortfalls.

## 5. Order

1. This document, `h-a2r.py`, `strata.py` and `quotas.json` are fixed by the tag
   `paper-a-h-a2r-prereg-v1.0`. The script refuses to run unless the tag exists on origin and the
   three files are byte-identical to the tag's.
2. On the research host, the six inputs are copied to a private work directory outside any
   repository.
3. `h-a2r.py` runs once, from a fresh clone of the tag. Its output, unchanged, goes to
   `results/h-a2r-<date of the run>.txt`. A run that stops on a refusal (an unregistered file, a
   missing start) may be repeated once the input is corrected; a run that printed the reading is
   the reading.
4. `RESULTS.md` and `MANUSCRIPT.md` report the reading as registered, with every number in
   `PROVENANCE.json`.

Smoke runs use synthetic databases only: `--smoke` refuses any registered file.

## 6. What this cannot show

The window is one history of one system, and it mixes two ingest regimes and several incidents;
the reading describes how references fared in that history, not how ids and anchors compare in
general. The spans are arbitrary passages, not answers to questions. Lineage rests on provenance.
The author knew the events in §1; the thresholds are H-A2's, fixed before any of this was looked at,
and the expectations in §1 are stated so the reading can be checked against them. As in
`PREREGISTRATION.md` §6, the script cannot stop the person who runs it from computing a reading
privately before the tag; what it guarantees is that the reported reading came from the registered
files and the tagged code.
