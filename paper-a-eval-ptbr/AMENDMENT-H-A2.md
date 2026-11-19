# Paper A, H-A2: amendment of 2026-11-19, one more reading on 2027-05-18

Status: draft. It becomes binding when the tag `paper-a-h-a2-amendment-v1.0` is pushed to the
public repository. It changes one thing in `PREREGISTRATION.md` §4: the date of the later
snapshot. Nothing else in the pre-registration changes, and the reading of 2026-11-18 stands as
reported in `RESULTS.md`.

## 1. What was known when this was written

This amendment was written after the first reading, and it says what that reading showed:

- On 2026-11-18, 1 of the 120 gold ids had changed; the precondition needs 12. H-A2 was reported
  as not tested. By id 119 queries reached their evidence, by anchor 117.
- The one change was an edit of the author's. The anchor's three misses were stratum-F notes whose
  source path a migration renamed on 2026-11-11 while keeping their ids.
- Since 2026-10-14 (nox-supermem#42) a re-ingest keeps the id of every chunk whose text did not
  change, and a renamed file takes over its old ids. The re-chunk that motivated H-A2 no longer
  happens. An id is now lost when its own chunk's text changes; the registered anchor is lost when
  a path changes without a re-ingest.

So a longer window measures the system as it now is, not the one that motivated the hypothesis.
The question becomes whether, over six months of ordinary use, a reference by evidence outlives a
reference by chunk id. The author expects exposure to stay low, and H-A2 may again be not tested.
That outcome is reported the same way as the first.

## 2. What is fixed

- **Everything the first reading used:** the frozen database of 2026-11-04 and its registered
  hash, the holdout and its commitment (read from its commit on `origin/main`, as before), the
  criterion (an active chunk whose whitespace-normalised text contains the evidence span), the
  precondition and the prediction. `h-a2-amendment-run.py` loads `holdout-persistence.py`
  unchanged and sets only its date constant. In integers, as the script compares them, over 120
  queries: the precondition is at least 12 exposed; the prediction is at least 114 reached by anchor
  and by anchor minus by id at least 12.
- **The later snapshot:** the daily `.gz` whose name carries the date 2027-05-18, the earliest of
  that day by the time in its name, listed in a listing of the backup directory taken in the same
  session as the copy. The listing and the snapshot's hash are reported. Daily snapshots are kept 6
  days, so the copy is taken by 2027-05-23. If no snapshot of 2027-05-18 exists, H-A2 is reported
  as not tested, and no other date replaces it.
- **One reading.** A run that stops on a refusal (a wrong file, a listing that does not contain
  it) may be repeated once the input is corrected. A run that has printed the reading is the
  reading. No later date is added after this one.
- **Renames count against the anchor.** The first reading showed that a renamed path breaks the
  registered anchor. Changing the anchor now, after seeing that, would fit the rule to the data, so
  the anchor stays a source path plus an evidence span, compared to the path exactly as recorded.

## 3. Descriptive, no threshold

Printed after the reading by the same script, from the same snapshot, as counts:

- **Path-free anchor:** queries whose evidence span is contained in any active chunk of the whole
  snapshot, with how many of those match more than one chunk. This says how much of the anchor's
  loss is the path and not the span.
- **Cause of each disagreement:** for every exposed query, and every query where the id and the
  anchor disagree, whether the gold id's chunk moved to another path, the path has no active chunk
  left, or the path is there and the gold chunk changed or is gone.

None of these enters the reading.

## 4. Order

1. This document and `h-a2-amendment-run.py` are fixed by the tag `paper-a-h-a2-amendment-v1.0`.
   The script refuses to run unless the tag exists on origin and the script and
   `holdout-persistence.py` are byte-identical to the tag's.
2. Before the tag, a second copy of the frozen database and of the holdout is made off the
   research host and verified by hash at the destination. Today the research host holds the only
   copy; six months is long enough to lose it.
3. Between 2027-05-18 and 2027-05-23: on the serving host, one session lists the backup directory,
   takes the sha256 of the earliest snapshot of 2027-05-18 and copies it, with the listing, to the
   research host, where the hash is checked again.
4. On the research host, from a fresh clone of the tag, `h-a2-amendment-run.py` runs once. Its
   output, unchanged, goes to `results/h-a2-2027-05-18.txt`; the listing and the hash go next to it.
5. The version of nox-mem the serving host runs that day is recorded with the result, since the
   code that decides when ids change may differ from the code of 2026-11-18.

## 5. What this cannot show

Six months of one person's use of one system is one window. A change in nox-mem's ingest between
now and then changes what is measured; step 5 records it but cannot undo it. As in
`PREREGISTRATION.md` §6, the scripts cannot stop the person who runs them from looking at a later
snapshot privately before the registered date; what they guarantee is that the reported reading
comes from the registered files and the registered snapshot.
