# A-recon: POOL-ELEGIVEL covers one day, the claim covers four (§4.3.1)

Sprint 2026-10-04. Status: **closed by measurement.** The three missing days were
measurable from preserved data and they agree with the claim.

## The claim

`MANUSCRIPT.md` §4.3.1, lines 664-690 (English: `translation/A-06-s4.3.md` lines 69-96):
"Medido em quatro dias (`measurement/pool-elegivel.py`, `POOL-ELEGIVEL-2026-08-28.json`)",
the table row "servidos no dia | 108 — 100% do pool, em 26, 27, 28 e 29/08", and
"O pool é esgotado todos os dias medidos". Lines 667-675 already carry a warning that the
artifact covers only 28/08. Line 2042 lists this as an open item. Line 1831 (Appendix D)
lists only the 28/08 artifact.

`POOL-ELEGIVEL-2026-08-28.json` has `dia = 2026-08-28` only: corpus 67,187, global
sub-pool 108, agent sub-pool 0, never served 0, served on the day 108, 672 briefs,
12.4 slots per candidate, `dia_parcial = false`.

## Data used

Research VPS $NOX_LASTRO_HOST, `/var/backups/nox-mem/paper2-bancos-ensaio/`. Each DB was copied to
`/var/tmp/sprint-poolelegivel-A/` and opened only as a copy, with
`mode=ro&immutable=1`. The sha256 of every copy matches `p2-bancos-ensaio.sha256`
(`A-pool-elegivel/copies-sha256.txt`). The work dir was removed afterwards. A later
listing showed no `-wal` or `-shm` next to the originals. The production VPS was **not
touched**: epoch manifests could not have covered 26-29/08, because the epoch serving
started with the trial on 01/09, and the preserved DBs answered the question without them.

| copy | brief_log range (UTC) | chunks | max created_at | usable for 26-29/08? |
|---|---|---:|---|---|
| `corpus/p2-ord-ro-2026-08-26.db` | 06-04 → **08-26 21:07:02** | 67,187 | 2026-08-24 | only a partial 26/08 (594 briefs) |
| `corpus-SERVING-REAL-e20260903-recuperado.db` | 06-04 → 09-03 05:52 | 67,187 | 2026-08-24 | **yes (primary)** |
| `corpus/e20260907T060001Z.db` | 06-04 → 09-07 05:52 | 67,187 | 2026-08-24 | yes (replica) |
| `corpus-preservado-20260908.db` | 06-04 → 09-08 05:52 | 67,606 | 2026-09-08 | **no**: fails the positive control |

## Method

`measurement/sprint-pool-elegivel-multidia.py` (new). It uses the predicate of
`pool-elegivel.py` verbatim and runs it in two variants:

- `as_script`: the original queries unchanged.
- `time_bounded`: the same queries, plus chunk date ≤ end of the measured day, and
  "never served" counted only over `brief_log` rows with `served_at` ≤ end of the day.
  This keeps a later DB from answering with information that came after the day.

**Positive control.** The script was rerun for 28/08 on the primary copy. It reproduces
`POOL-ELEGIVEL-2026-08-28.json` in **all 12 fields** (`positive_control...all_equal: true`
in the artifact).

## Result

Artifact: `_sprint-2026-10-04/POOL-ELEGIVEL-2026-08-26-to-29.json`. The raw per-copy outputs
are in `A-pool-elegivel/out-*.json`.

| day | corpus | global / agent | eligible pool | never served | served on day | coverage | briefs | slots/candidate | partial |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2026-08-26 | 67,187 | 108 / 0 | 108 | 0 | 108 | 100.0% | 677 | 12.5× | no |
| 2026-08-27 | 67,187 | 108 / 0 | 108 | 0 | 108 | 100.0% | 672 | 12.4× | no |
| 2026-08-28 | 67,187 | 108 / 0 | 108 | 0 | 108 | 100.0% | 672 | 12.4× | no |
| 2026-08-29 | 67,187 | 108 / 0 | 108 | 0 | 108 | 100.0% | 672 | 12.4× | no |

On all four days the `as_script` and `time_bounded` outputs are identical. The pool-id hash
is `924f2dc31a2c3c60` on all four days, and it is the same in the copies frozen on 26/08,
03/09 and 07/09.

### Checks

- `brief_log` rows for 26-29/08 in the 03/09 and 07/09 copies: 0 rows differ in either
  direction on (id, chunk_id, served_at, brief_id).
- The 26/08 rows in the 26/08 snapshot are a subset of the 03/09 copy (0 missing). The 03/09
  copy has 3 extra rows at 21:07:02, the same second as the end of the snapshot: one brief
  caught mid-write.
- The 918 chunks matching the `memory/entities/%` and `memory/lessons.md` patterns have
  **0** changes in importance, pain, source_date, created_at or source_file between the
  26/08 and 03/09 copies.
- **26/08 has 677 brief_ids:** 672 ten-row briefs plus 5 five-row briefs, at 19:58 and
  20:28 UTC. Counting only the 672 ten-row briefs, all 108 pool chunks are still served on
  26/08, and on every other day too (`A-pool-elegivel/sensitivity-ten-row-briefs-serv0903.json`).
  So "12.4× (closed day)" holds for 27-29/08 and for 26/08 on the 672 regular briefs; on
  all 677 briefs, 26/08 gives 12.5×. Every day has serves in all 24 UTC hours.
- **Negative case.** In the 08/09 copy the chunk table was re-ingested after 07/09
  (67,606 chunks, max created_at 2026-09-08). There, `as_script` gives pool 368 = 115 + 253
  with 47.8% coverage, and `time_bounded` gives pool 55. It fails the 28/08 control and
  must not stand in for late August. This is why the positive control is part of the
  method rather than an add-on.

## Limits (stated, not estimated)

- importance and pain are read as stored in copies frozen on 26/08, 03/09 and 07/09. The
  pool hash is identical at both ends, which brackets 27-29/08. It does not observe those
  days directly.
- The original **partial** 29/08 run, which the manuscript cites as 5.6×, has no artifact
  and was not recovered: **NOT MEASURED**. What this sprint measured is the **closed**
  29/08 (672 briefs, 12.4×). The 5.6× in the text can keep being cited only as an
  unpreserved partial-day reading. Otherwise it should be dropped.
- Day key: UTC date prefix of `served_at`, the same as in the original.

## Text changes (returned as findings; MANUSCRIPT.md not edited)

1. Line 664-665: cite the new artifact next to the old one.
2. Lines 667-675: replace the "covers ONE day" warning with a note saying the gap was
   closed by re-measurement, and say how.
3. Line 681-682: note 12.5× for 26/08 (677 briefs incl. 5 five-row briefs).
4. Lines 684-686: 29/08 closed-day value is now measured (12.4×); the 5.6× partial reading has no artifact.
5. Line 1831: add the new artifact and script to Appendix D.
6. Line 2042: remove the POOL-ELEGIVEL item from the open list.
