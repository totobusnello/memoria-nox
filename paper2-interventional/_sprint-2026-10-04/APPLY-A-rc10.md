# APPLY A-rc10 (2026-10-05): findings of REVIEW-A-rc9-2026-10-05.md

Input `A-v1.1-rc9.md` → output `A-v1.1-rc10.md`. Gate: `A-rc10/parity-rc10.py --selftest`: PARITY OK,
SELFTEST OK (18 mutations; the Codex C2 unit mutation is not caught, and the selftest records that as
a known limit). Deposit copy `deposit/paperA-v1.1/MANUSCRIPT-v1.1.md` is byte-identical to rc10
(sha256 `71a079a4…627b3`). The previous deposit copy is saved in the session scratchpad as
`MANUSCRIPT-v1.1.pre-rc10.md`; it differed from rc9 only in Appendix D.

Abstract: 1,177 → 1,090 words.

| ID | verified? | applied? | evidence / note |
|---|---|---|---|
| F1 | yes: rc9 has the TODO at l.2231 and "open/pending" at F-4, F-5 and Open items 4, while the deposit copy filled Appendix D only | yes, with one correction | Appendix D: "Its version DOI is `10.5281/zenodo.23163119`, reserved before deposit; the record is published with this text." The status block, F-4, F-5 and Open items 4 now agree, and Open items 5 also says "the reserved version DOI is now in Appendix D". The finding's F-4 wording said "(rc9)"; rc9 still had the TODO, so the text says "(rc10)". Deposit copy = rc10 byte for byte, checked by the parity `deposit` check. |
| F2 | yes. `out-ord0826.json` `ids.lift_F7_pinned` has 116107 out and 227328 in on every epoch 2026-08-21..09-07 (09-02 has no briefs). `briefs_changed_vs_baseline` = all briefs, Jaccard 0.7778, so exactly one swap per brief. `serving-brief.ts:819-821` builds `pinnedIds` from `current.items` with `pain >= painFloor`. Positions 1/3/4 are salience ranks among 149 chunks (§4.3.2). | yes, with one correction | The Abstract now says "rank 1, 3 and 4 by salience among the 149 served chunks", names the pin and the 44–46 counterfactual, and says search traffic "put them where the pin holds them". §9 uses the finding's wording. §4.3.2 gains the pin paragraph ("the other condition, and it is measured as necessary"). **Not adopted:** "is therefore a necessary condition for their presence" / "would not be pinned". §4.3.2 says dedup was not replayed and pool positions "do not by themselves establish final served membership". |
| F3 | yes: F-2 lists the universal as corrected, and §8.1 describes the survey's three-family taxonomy | yes | Abstract and §1 use the finding's wording, adapted. |
| F4 | yes: the scope clause appeared about 15× | yes | §3.1 defines *no-record* once, right after "Only the live complement is exact…". The Abstract keeps the full clause once and §3.1 keeps it twice. §1, contributions, §2, §4.1 (×3), §4.1.1 (×2), §4.5 and §8.1 now use the term with a §3.1 pointer. "whoever initiated" goes 7→4 (Abstract 2→1, §4.1.1 and §4.3.2 removed; §7, §8.2 and §9 kept because those sections had not stated it). "defective-ingestion" goes 7→5 (the second mention in the Abstract and in §9 becomes "same regime"). The §4.3.2 symmetry table row is left byte-identical. Counts are declared in parity `qualifiers`, each ≥1. The rc8 `classes` check passes. |
| F5 | yes | yes | The correction narrative became one sentence: "A third axis: excluding the 25 rows…13/350 (3.71%)…(§5.7.2)". Abstract labels removed: "Caveat:" inline, "Correction:", "**Caveat:** what we do not claim", "**Caveat: two notes on reading.**". The first note repeated para 2 and §3.1 and was dropped. The curation note moved into "What we do not claim". The duplicate 1,635/1,787/152 and "eight times over" were removed. |
| F6 | partly. The numbers hold (exact 649/650/651/658 of 672 on 08-24..27; 85.8/85.7/98.0% on 08-21..23). The guessed reason (the 52 chunks) is **wrong**: those are coverage slots. | yes, with corrections | Real reason, from `A-filters-disaggregation.md` §4 and `diag-out.txt` (2026-08-22): the 08-26 copy carries an access to 298048 at 2026-08-22T19:09Z, so the reconstruction ranks it above 285042, which was served, for one `boris` slot (96 briefs/day). Range corrected to the text's whole window: the stricter test passes in 94.3–97.9% (634/672 to 658/672) on every day except 09-03 and 09-07, where `fresh_added` is null (served_main_slots = 10×briefs). On every other day exact + `briefs_where_served_minus_fresh_added_is_not_8` = briefs. Open items 6 says "(under the criterion of §4.3.1)". |
| F7 | — (author decision) | yes | H1 changed. One dated line was added to the title note. The old closer "A subtitle cannot sell…" was cut (F13). |
| F8 | yes (§4.3.1: 08-23 has 34) | yes | — |
| F9 | yes: `serving-brief.ts` 462-467 is phase 2 backfill; the fresh loop is 469-474, with 472 the exit already cited in §5.3 | yes | `brief.ts:470-474`. |
| F10 | yes: 617 appears only in the `superficie-de-exposicao.py` docstring and `SUPERFICIE-2026-08-27.md`; 245/151/865 are in `out/superficie.json` `janela_comum` | yes | The table row is rewritten (865 curated entities, window from 2026-06-04). The 617 is added to the status-block list of numbers without an artifact. |
| F11 | yes: `COVERAGE-SET-FROM-LOG` `2026-09-20.added_vs_ref` = [109163, 227328]; both are in `ids.lift_F1_scope_routing` / `lift_F6_quota_split` (227328 also `lift_F7_pinned`); method = all ten minus the 37-id union | yes | — |
| F12 | yes: `CLAIM-COVERAGE-2026-08-29.json` reads 10 of 32 (31.2%); no later artifact | yes | Added to the status-block list and flagged in place in §6.1. |
| F13 | yes | yes | The F-3.1 duplicate of "Declaring ignorance…" was cut. Ten closers were cut or merged: subtitle (title note), "Choices can be examined.", "The term left the control…" (merged), "Diffing provenance…", "A missing field…" (merged), "Suspicious agreement…", "A guard that compares labels…", "Retention does not read hashes.", "The marker there announced…", "A to-do list…ruler that ages." Run-in labels outside the Abstract are kept because Appendix F reports their density. Labels were removed only from the Abstract. The reported densities (26.7%, 30.6%, 32.6%, 32.8%, 87/77/288, 112/102/344) were measured on the **Portuguese** text ("the English translation needs its own measurement"), so no reported number changes. |
| C1 | yes (§2 item 2 defined search by agent initiative) | yes | Codex wording. |
| C2 | yes (unit/quotation mutations pass parity-rc9) | yes | The rc9 addendum sentence now lists exactly the parity-rc9 checks and attributes units, quotations outside code and the wording around numbers to manual review. parity-rc10 `history` allows only this replacement. |

## Number deltas (all declared in parity-rc10 with finding IDs)
Removed: 1,635 / 1,787 / 152 (one Abstract copy, F4/F5); 10,899 / 9,755 (dropped Abstract note, F5);
17 / 350 / 4.86% / 2026-08-30 (Abstract correction narrative, F5); "two" ×2, "eight" ×1 (F5);
462-466 (F9). Added: from artifacts only. F2: 149, 44–46, 116107, 227328, `brief.ts:819-821`. F6: 94.3, 97.9%,
85.8/85.7/98.0%, 298048, 285042, dates. F8: 34, 08-23. F9: 470-474. F10: 617, 865, 2026-06-04. F11:
109163, 227328, 37, "ten". F12: 0 of 32 in the status block. F5: 25. F1: DOI ×2. F7: 2026-10-05 in the
title note.

## claims_check.py (not edited)
It reads root `MANUSCRIPT.md` (Portuguese lineage, PT number formatting, e.g. `"10.899": 15`), not
rc10 or the deposit copy. No string literal of claims_check that occurs in rc9 is missing from rc10.
No guard pins any of the changed phrases ("occupy positions", "determined those positions",
"462-466", "617×245", "TODO at deposit", "None measures", the title). English-equivalent counts that
moved: `10,899` 13→12 and `4.86` 22→21 (the Abstract drops, F5). `8.7 times`, `47.16%`, `2.43%` and
`583,763` are unchanged. These only matter if rc10 is ever promoted into the guarded file with its
counts.

## Observed, not changed (no finding covers it)
The Abstract and §1 cite "no downstream outcome is instrumented (§5.4)". §5.4 is the saturation
corollary; the statement lives in §4.5. Left as is.

## Post-apply (main session, 2026-10-05)

XREF: the Abstract and §1 cited "(§5.4)" for "no downstream outcome is instrumented"; the statement
lives in §4.5 ("What these measurements do not identify", first bullet). Changed to "(§4.5)" in both;
declared in `parity-rc10.py` as XREF (numbers and refs). Deposit copy re-synchronised.
