# APPLY B-rc18: review of rc17 applied (2026-10-05)

`B-v2-rc17.md` (`2af62266…`, the author's title included) was copied to `B-v2-rc18.md`, and only
rc18 was edited. No git write, no Zenodo write, no voices, no VPS, no LLM API call. Read-only
operations used: `git log` / `git show` on `DECISION-designacao-2026-08-25.md`,
`deposit/deposit-v1.12.sh` and the commits of 2026-08-26; one public GET each of
`https://zenodo.org/api/records/22110203` and `…/22110203/files`, saved as
`B-rc18/zenodo-22110203-record.json` and `B-rc18/zenodo-22110203-files.json` so the parity reads
them offline. Source: the Fable read of rc17 (NO-GO, three MEDIUM, four LOW, no HIGH), as relayed.
Each finding was verified before it was applied. Two were adapted because their source did not hold
as written (M-1 in part, M-3 in part). None was rejected outright.

## M-3: verdict **holds, adapted** (and a correction it led to)

**What the deposited `DECISION-designacao-2026-08-25.md` contained.** The Zenodo v1.12 file list
gives `md5:35abeb688f3747ed816255548e361162`, 7 036 bytes. I computed the md5 of the file's blob in
every commit that touched it. Only `d42f950` (2026-08-25T18:16:58+02:00 = 16:16:58Z) matches:

| commit | time (UTC) | md5 | bytes |
|---|---|---|---|
| **`d42f950`** | 08-25 16:16:58Z | **`35abeb68…`** = deposited | 7 036 |
| `d8fcf89` | 08-26 12:09:39Z | `9cb05668…` | 9 412 |
| `c46d7e3` | 08-26 14:48:45Z ("DECIDIDO 14:47Z") | `8026e696…` | 11 063 |
| `dd4ba6c`, `3edc352`, `df3070b` (= HEAD) | 19:40Z → 20:02Z | other | 13 481 → 18 530 |

The deposited bytes are the **open** version. The header says *"Status: aberta, aguardando o
Toto"* (open, awaiting the author), and it blocks the prospective registration but not the v1.12
deposit. It lays out the three measured defects and requirements R1–R5, then options **A**
(maximum severity), **B** (seeded pseudorandom draw, `argmin SHA256(seed ‖ "|" ‖ sig_primary ‖ "|" ‖
chunk_id)` per group), **C** (one per cell) and **D** (lowest `chunk_id`). It recommends **B** and
offers to compute the dose cost before the author chooses. It has no decision, no seed, no frozen
file, no sha256 pin, no 19 items, and it does not mention "not recomputed at every brief". Its
option B also keys on `sig_primary`. The layout actually used dropped that field at 19:40Z
(`DESIGNATION-SEED` l.96–97; commit `dd4ba6c` at 19:40:52Z).

**What did not hold in the reviewer's text: "46 minutes after publication".** rc17 had v1.12
published at 14:01Z, taken from `deposit/PLAN-v1.13.md` l.13. That time is wrong. Three independent
anchors put publication at **12:01Z**:

- the Zenodo record has `created` 2026-08-26T12:01:06Z and `updated` 12:01:13Z, and its files were
  created between 12:01:06Z and 12:01:12Z;
- the local `deposit/.published.json` (untracked) has mtime 09:01:15 −0300 = 12:01:15Z;
- the handoff commit `ca69084` "v1.12 DEPOSITADA" is at 14:04:15+02:00 = 12:04:15Z, and the fix
  just before publish (`fa094f7`) is at 11:59:55Z.

PLAN-v1.13's "14:01Z" is the +02:00 local time labelled Z. The decision's 14:47Z is real UTC: its
commit `c46d7e3` is at 14:48:45Z, and the seed file's other Z times match their commits (19:40Z →
`dd4ba6c` 19:40:52Z). So the decision came **2 h 46 min** after publication, not 46 min. PLAN-v1.13
was not edited, because it is a dated planning file. rc17's parity check that it still says 14:01Z
is carried, and its meaning is now "the mislabelled time rc18 declares".

**Applied.** §1: after "was not deposited as an amendment", the reviewer's clause, adapted: *"the
deposit carries the per-brief rule retracted as an open defect (`AMENDMENT-v1.12.md` §5) and, in
`DECISION-designacao-2026-08-25.md`, a recommendation, marked as awaiting the author's decision, of
a seeded pseudorandom draw of one chunk per signature group (option B); the decision, the seed, the
key layout that was used and the 19 items were not deposited."* Times: "published at 12:01Z (the
creation time of Zenodo record 22110203) … decided at 14:47Z, 2 h 46 min later". §3.0.1: "only the
horizon is in the registration" becomes "only the horizon is locked in the registration", followed
by the same clause with "decided 2 h 46 min after publication" and "(the deposited option B keys on
`sig_primary`, which was dropped from the key at 19:40Z)". After it comes the reviewer's *"This is
therefore a mismatch between the registered horizon and the intervention frozen after it"*, and the
H1b contrast is kept. "Seeded fixed designation" (the reviewer's wording) became "seeded
pseudorandom draw of one chunk per signature group". The deposited option B does not say the set is
frozen or fixed; that commitment exists only in the later `DESIGNATION-SEED` (l.84–92).

## M-2: verdict **holds**

§8.3: "we by a registration whose sample size ignored a 30-day eligibility window" now reads "we by
a registered horizon of 234 epochs that was never re-read against the intervention frozen after
registration, whose 19 items left a 30-day eligibility window together after 20 epochs (§3.0.1)".
I checked the source: PREREG l.513–519 computes reach under the 30-day window, so the registration
did not ignore it. The 20 epochs come from §3.0.1's table (expiry 2026-09-20 22:51:23). Sweep:
every body sentence pairing registration/registered/deposit with window/30-day/expiry was read. No
other one carries the framing.

## M-1: verdict **holds, adapted**

The rc17 changelog block said the title was not changed, but the author changed it
(`APPLY-B-rc17.md`, end). The line now records the change in the reviewer's words. One clause was
adapted. The reviewer wrote "the deposit metadata that carries the title must follow", but **no
deposit metadata for Paper B exists yet** (`grep` over the repo: the old title is only in sprint
drafts/APPLY/parity files, and `deposit/` has no Paper B metadata). It now reads "no deposit
metadata for this paper exists yet, and the one written at deposit must carry this title". Item
164 was added.

## LOWs

- **L1, holds.** "the designation was completed at 20:28Z" became "went live at 20:28Z
  (`AMENDMENT-DRAFT-band-collapse-2026-08-26.md` §1)", where the §1 table has *"vigente desde
  20:28Z"* and l.432 has *"A regra nova entrou às 20:28Z"*. `REPLAY-OPORTUNIDADE-2026-08-27.md` only
  opens its window at 20:28Z (l.30), so it is not cited as the source of the go-live.
- **L2, holds.** 1 056 s = 20:25:00Z − 20:07:24Z, the commit time recorded in
  `DESIGNATION-2026-08-26.json` (`declaracao`: "commit 40d2462 pushado 2026-08-26T20:07:24Z"; git
  shows `40d2462` at 22:07:24+02:00). The seed file's own T_declare is 20:07:27Z, which gives
  1 053 s. Both are now named in §1.
- **L3, holds.** Heading: "infeasible by construction" became "infeasible once the designation
  was frozen". The body agrees: the 20-epoch life belongs to the frozen set, and the deposited
  per-brief rule would recompute. Abstract "infeasible from the start" (of the trial) is consistent
  and unchanged.
- **L4, applied.** §3.0.1 caveat: "(PREREG §2: the reach table at l.513–519 is computed under it,
  and l.550–558 give the minimum dose at chunk ages up to 90 days)". These are line ranges, so the
  reviewer's l.550/l.557 is widened to the whole age table, which runs to its 90 d row at l.558.

## Artifacts (sha256 prefix)

| file | sha256 |
|---|---|
| `B-v2-rc18.md` | `b07f19c2…` |
| `B-rc18/parity-rc18.py` | `dee8a51a…` |
| `B-rc18/zenodo-22110203-record.json` | `d9e059f9…` |
| `B-rc18/zenodo-22110203-files.json` | `5ecf1366…` |

Unchanged: `B-v2-rc17.md` `2af62266…`, `B-rc17/parity-rc17.py` `dc25fa22…` (still PASS), v4,
checks-rc15, the acceleration test, RESULTADO-v4 + note, every SHAM-JANELA block.

## Parity (`python3 B-rc18/parity-rc18.py`: **PASS**)

Imports `B-rc17/parity-rc17.py` (pinned `dc25fa22…`), which carries rc16–rc11. Pins rc17 at
`2af62266…`.

- 10 hunks, all with an ID (ST, M3, L1, L2, L3, L4, M2, WL, M1, CL).
- Numbers: none removed. Added tokens are in rc17 or derived from a source read in the script:
  12:01Z and 22110203 (Zenodo snapshot), 19:40Z and 20:07:27Z (DESIGNATION-SEED), 20:07:24Z
  (DESIGNATION json), 1 053 and 46 (arithmetic checked in S18), 519/558 (PREREG lines checked in
  S18), 2026-08-25 (the deposited file name).
- Invariants: italic quotations, citations, footnotes, DOIs, image links and struck spans are
  unchanged. Headings (40) are unchanged except the declared §3.0.1 heading. **Title lock**: line 1
  is exactly the author's title, and the old title is absent from the body.
- Tail: the rc17 tail is reproduced byte for byte once the working-list insertion (item 24) is
  removed, the declared rc17-block edit (M-1) is reverted and the rc18 block (items 164–167) is
  removed. The block must record "not 14:01Z" and "2 h 46 min …, not 46 min".
- SHAM-JANELA: 10/10 blocks byte-identical.
- Carried locks: everything from rc17, including its sweeps, presence locks, rc13 claims and status
  marks. Two rc17 presence locks are replaced and declared (the 14:01Z sentence, "this is a
  mismatch…"), and both must now be absent. New sweep: "sample size ignored a 30-day", "only the
  horizon is in the registration", "published at 14:01Z", "46 min after publication" (unless
  "2 h 46 min"), "completed at 20:28Z", "1 056 s according to the recorded timestamps",
  "infeasible by construction", and the old title in the body. 8 new presence locks.
- Qualifiers: 102 locked phrases. One justified delta: "not deposited" +3 (§1, §3.0.1, item 165).
  Hedge words are declared per ID (ST, M3+L1, M3, M2) and sum to the body delta.
- Integrity: rc17's carried checks, its source block S included. **New block S18**:
  - the Zenodo record is 1.12, created 12:01Z;
  - the listed DECISION md5 equals `git show d42f950:` and differs from HEAD;
  - `deposit-v1.12.sh` NOVOS lists the file;
  - the deposited bytes contain the open status, options B and D, the recommendation of B and the
    `sig_primary` key, and contain no "DECIDID" and no seed;
  - DESIGNATION-SEED has 14:47Z, 19:40Z, 20:07:27Z and 1.053 s;
  - 1 056 s and 1 053 s are recomputed from the json, and 12:01Z → 14:47Z = 2 h 46 min;
  - the band draft §1 has "vigente desde 20:28Z";
  - PREREG l.513/515/519/550/558 are the cited tables;
  - PLAN-v1.13 still carries the mislabelled 14:01Z.

`--self-test`: **39/39 mutations caught**, and unmutated rc18 passes. 28 are text mutations: each
M-3 piece reverted, 14:01Z restored, "46 minutes" inserted, M-2 restored, L1–L4 each reverted, the
rc17 "title not changed" line restored, item 164 removed, the old title on line 1 or in the body,
status, the working-list note, the 12:01Z record in the block, an old changelog line, SHAM, three
carried locks, an italic quotation, a citation, an unsourced number, an unmapped hunk. 11 are
integrity/source mutations: Zenodo created at 14:01Z; the listed md5 equal to HEAD; the deposited
bytes carrying a decision, losing `sig_primary` or losing option D, each with the md5 rewritten so
that the content needle has to catch it; 19:40Z absent; the band draft time moved; a PREREG line
shift; the json commit time moved; the carried amendment wording; the carried RESULTADO note.

## Not done (declared)

- rc18 has not been reviewed.
- `deposit/PLAN-v1.13.md` l.13 still says 14:01Z, and it was not edited. The same mislabel may sit
  in other notes that copied it (the rc17 APPLY table cites it). That was not swept outside this
  manuscript.
- Appendix A's designation item ("closed … by the fixed 19-item designation, which was not
  deposited") was left as is. It is consistent with M-3, and the detail lives in §1 and §3.0.1.
- None of the rc15–rc18 artifacts is in the ballast manifest (working list 17). The Zenodo
  snapshot in `B-rc18/` is new and not manifested either.
