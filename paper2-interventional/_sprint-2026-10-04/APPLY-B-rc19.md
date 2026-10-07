# APPLY B-rc19: review of rc18 applied (2026-10-05)

`B-v2-rc18.md` (`b07f19c2…`) was copied to `B-v2-rc19.md`, and only rc19 was edited. No git
write, no Zenodo write, no voices, no VPS, no LLM API call. Read-only operations used: `git log` /
`git show` on `assign_arms.py` and `DECISION-designacao-2026-08-25.md`; one public GET each of
`https://zenodo.org/api/records/21978476` and `…/21978476/files` (Zenodo v1.11), saved as
`B-rc19/zenodo-21978476-record.json` and `B-rc19/zenodo-21978476-files.json` so the parity reads
them offline; a read of the ballast manifest `~/Backups/paper2-ensaio-2026-09-21/MANIFESTO-LASTRO-P2.json`.
Source: the Fable read of rc18 (GO, six LOW), as relayed. Each finding was verified before it was
applied. L4 was stated more exactly than proposed. None was rejected.

## L1: verdict **holds**

`AMENDMENT-v1.12.md` §5 is headed *"Defeito aberto: a designação não está validamente congelada"*
and says the defect *"é declarado aqui em vez de consertado em silêncio"*. §5.1 retracts the threshold
model behind `CUT_FRESH = 0.7342` (*"Retratado o modelo de limiar (§1.1)"*). It does not retract the
per-brief rule. In §1 and §3.0.1, "the per-brief rule retracted as an open defect" became "the
per-brief rule declared an open defect". Changelog item 165 (rc18 block) keeps rc18's wording,
because it is the record of what rc18 wrote. The parity sweep bars the phrase from the body.

## L2: verdict **holds**

- Zenodo v1.12 file list: `DECISION-designacao-2026-08-25.md` is `md5:35abeb68…`, size **7 036**.
  `git show d42f950:` gives 7 036 bytes and the same md5.
- The next commit to touch the file is `d8fcf89` at 12:09:39Z, which is after the record's
  `created` time of 12:01:06Z. HEAD is 18 530 bytes and contains "DECIDIDO". So "extended after
  publication to record the decision" is accurate.
- `DESIGNATION-SEED-2026-08-26.md` l.31 has *"decidida em **2026-08-26T14:47Z**"*. l.96–97 have
  the 14:47Z layout and *"Foi corrigido às 19:40Z"*.

What was applied:

- §1: the reviewer's parenthetical, verbatim, after "(option B)".
- B.1: a row for 12:01Z, the md5 and size, 19:40Z and 2 h 46 min. It points to
  `B-rc18/zenodo-22110203-{record,files}.json` and to DESIGNATION-SEED l.31 and l.96–97.
- Appendix B: a row for the `B-rc18/` snapshot, marked "not in the ballast manifest, working
  list 17". The snapshots were also added to the Appendix B paragraph that lists the artifacts
  not yet in the manifest.

## L3: verdict **holds**

§3.0.1 now reads: "Both numbers, the horizon and the 20-epoch life of the fixed set, are ours, both
were locked, and they are incompatible, but only the horizon is locked in the registration".

## L4: verdict **holds, stated more exactly than proposed**

| fact | value | source |
|---|---|---|
| `assign_arms.py` last change | `3199ec1`, 2026-08-17T16:37:43Z; no later commit touches the file | `git log` |
| Zenodo v1.11 published | 2026-08-17T18:32:45Z, record 21978476, version 1.11 | `B-rc19/zenodo-21978476-record.json` |
| `assign_arms.py` in v1.11 | `md5:3fa3f710…`, equal to the blob of `3199ec1`, and equal to v1.12's | both file lists |
| OSF `yf7d2` registered | 2026-08-18T07:56:44Z | PREREG l.3, l.8 |
| round 31774052 emitted | 2026-08-30T21:32:04Z | `ASSIGN-SEED-2026-08-30.md` l.130 |

From the v1.11 deposit to the emission is **13 d 3 h**, which is not two weeks. The proposed "registered on
OSF on 2026-08-18, twelve days before the round" was not used, for two reasons. First, the OSF
registration attaches the document (PREREG l.10: the PDF, the HTML and `PREREG-DRAFT.md`), not the
script. Second, the deposit that dates the script's bytes is v1.11's, on 2026-08-17, one day before OSF.

§1 now reads: "fixed on 2026-08-17 (its last commit) and deposited in Zenodo v1.11 (record
21978476, published 2026-08-17T18:32Z, the day before the OSF registration; v1.12 carries the same
bytes, md5 `3fa3f710…`), thirteen days before the round was emitted, which the deposit, not our
log, dates". The parenthetical "deposited with v1.12" a few lines up became "deposited with v1.11 and
v1.12". A sweep found no other "two weeks", "fortnight" or "twelve days" about this, and the parity
now bars "two weeks" from the body. B.1 and Appendix B each have a row for the v1.11 snapshot.

## L5: verdict **holds**

`AMENDMENT-DRAFT-band-collapse-2026-08-26.md` l.5 reads *"(`10.5281/zenodo.22110203`,
2026-08-26T14:01Z)"*, the same UTC+2 time labelled Z that `deposit/PLAN-v1.13.md` l.13 has. rc18
changelog item 165 now names both files (with their lines), and says that neither file is edited.
That is a declared tail edit, and neither source file was touched.

## L6: verdict **holds**

The manifest holds 50 artifacts and no `B-rc15/` … `B-rc19/` path, and neither Zenodo snapshot.
What was added:

- working list 8: 17 is still open and still blocks the deposit, and it now also covers rc15–rc18
  and the snapshots;
- working list 17: a dated rc19 note with that check;
- working list 24: the rc18 read and the fact that rc19 is unreviewed.

## Artifacts (sha256 prefix)

| file | sha256 |
|---|---|
| `B-v2-rc19.md` | `fe1be667…` |
| `B-rc19/parity-rc19.py` | `13ad30fe…` |
| `B-rc19/zenodo-21978476-record.json` | `bb2cf301…` |
| `B-rc19/zenodo-21978476-files.json` | `9bb619d2…` |

Unchanged: `B-v2-rc18.md` `b07f19c2…`, `B-rc18/parity-rc18.py` `dee8a51a…` (still PASS),
`B-rc17/parity-rc17.py` (still PASS), every SHAM-JANELA block, `PLAN-v1.13.md`, the band draft.

## Parity (`python3 B-rc19/parity-rc19.py`: **PASS**)

The script imports `B-rc18/parity-rc18.py` (pinned `dee8a51a…`), which carries rc17 and earlier,
and it pins rc18 at `b07f19c2…`.

- **Hunks:** 14, each with an ID (ST, L1–L6, WL, CL).
- **Numbers:** none removed. The added tokens are in rc18 or derived from a source the script
  reads: 21978476, 2026-08-17T18:32(:45)Z (v1.11 snapshot), and 7 036 (v1.12 file list).
- **Invariants:** italic quotations, citations, footnotes, DOIs, image links and struck spans
  are unchanged. All 40 headings are unchanged, and so is the title lock.
- **Tail:** byte-identical to rc18 once three things are undone: the three working-list
  insertions are removed, the item-165 edit is reverted, and the rc19 block (items 168–173) is
  removed. The block must record that the L4 proposal was not used and that L5 did not edit.
- **SHAM-JANELA:** 10/10 blocks byte-identical.
- **Carried locks:** rc18's and everything it carries, including the title lock. Two rc18 presence
  locks are replaced and declared (the §1 and §3.0.1 clauses), and they must now be absent.
- **New sweep:** "retracted as an open defect", "two weeks", "deposited with v1.12)", "Both
  numbers are ours" and "twelve days before the round".
- **New presence locks:** 8.
- **Qualifiers:** 102 locked phrases, no delta. Hedge words are declared per ID: ST
  (registered/deposited), L2 ("the deposited bytes"), and L2+L4 ("deposited" ×2, "every", and
  "not" ×2 in the B.1 and Appendix B rows). They sum to the body delta.
- **Integrity:** rc18's carried checks (S, S18), plus a new block, S19:
  - AMENDMENT-v1.12 §5 heading and §5.1;
  - the DECISION md5 and size, and the later extension;
  - the DESIGNATION-SEED lines;
  - `assign_arms.py`'s last commit, and its md5 in v1.11 and v1.12;
  - v1.11 being created one day before OSF;
  - the emission time, and the 13 days;
  - band l.5 and PLAN l.13;
  - the manifest has no rc15–rc19 paths (if the manifest is absent this is only a warning, and it
    is declared).

`--self-test`: **47/47 mutations caught**, and unmutated rc19 passes.

- 31 text mutations. Each L1–L6 edit reverted, the wrong size, "twelve days", the wrong v1.11
  time, the B.1 and Appendix B rows, the WL notes, item 165, item 172, the L4 note in the block,
  status, title, heading, an old changelog line, SHAM, four carried locks, an italic quotation, a
  citation, an unsourced number and an unmapped hunk.
- 16 integrity mutations. The amendment §5 or §5.1 reworded, the DECISION size, DECISION never
  extended, a seed-file line shift, a later `assign_arms.py` commit, the md5 in v1.11 or in v1.12,
  v1.11 a day later, the OSF date, the emission date, band l.5 corrected, the manifest listing
  `B-rc18/`, and three carried ones (S18 created at 14:01Z, the rc17 amendment wording, the
  RESULTADO note).

## Not done (declared)

- rc19 has not been reviewed.
- None of the rc15–rc19 artifacts is in the ballast manifest (working list 17), and this remains
  a deposit blocker (item 8).
- `PLAN-v1.13.md` l.13 and the band draft l.5 still say 14:01Z, and they were not edited. No sweep
  was made for 14:01Z outside this manuscript and those two files.
- In §1, the reviewer's parenthetical follows "(option B)" directly, which gives two consecutive
  parentheses. It was kept verbatim, as asked.
