# APPLY A-rc11 (2026-10-05): findings of REVIEW-A-rc10-2026-10-05.md

Input `A-v1.1-rc10.md` (sha256 `c25cd8c9…6466d`) → output `A-v1.1-rc11.md` (sha256
`2ee8520c…fb00d`). Gate: `A-rc11/parity-rc11.py --selftest`: PARITY OK, SELFTEST OK (20 mutations:
19 bite on the expected check; the unit mutation is not caught, as in rc10, and the selftest
records that as a known limit). The deposit copy `deposit/paperA-v1.1/MANUSCRIPT-v1.1.md` is
byte-identical to rc11 (parity `deposit` check).

parity-rc11 carries every rc10 check (numbers, footnotes, refs, code, links, headings, tables,
history, qualifiers, the 35 `classes`, dashes, addendum, deposit) and adds `withdrawn`: the 8 rc10
phrasings this review withdrew must not come back outside the F-5 addenda. That covers wording
regressions that move no token (three selftest mutations show it biting). Qualifier counts are now
compared against rc10's own counts plus a declared delta (one: R10-2 adds a "not established").

| # | verified against | holds? | applied? | note |
|---|---|---|---|---|
| 1 [high] | `MANIFEST-v1.1.json` (`excluidos`: "…, diag-*" with "não citados pelo texto"); rc10 l.879 cites `A-filters-disaggregation/diag-out.txt`; Appendix D enumeration and row lack it | yes | yes, verbatim | (a) Appendix D enumeration and table row. (b) is Part 2: `diag-out.txt` and `diag-residual-mismatch.py` go into `artefatos-v1.1.zip`, and the exclusion entry is narrowed to the files of that directory the manuscript does not cite (`out-pres0908.json`, `out-ord0826-tzm3-0828.json`, `copies-sha256.txt`). The script is the producer: its output format (`print(dict(mis))` then the JSON of `ex`) matches the file; the `# diag.py <db> <epoch>` header lines name it by its working name `diag.py`. Both files were committed on 2026-10-04 (#559), so Appendix D's "produced on 2026-10-04, in `_sprint-2026-10-04/`" holds. |
| 2 [medium] | `out-ord0826.json` `per_epoch.*.fidelity`; `diag-out.txt`; `observed-main-from-log.json`; `A-filters-disaggregation.md` §4 | yes, all three parts | yes, verbatim | 08-21: exact 242/282 = 0.8582, subset 0.8582. 08-22: 576/672 = 0.8571 both. 08-23: exact 472/560 = 0.8429, subset 549/560 = 0.9804. So 98.0% is the first criterion and the stricter one gives 84.3% on 08-23. On 08-22 all 96 `boris` briefs mismatch (672 − 576), the epoch's briefs run past 19:09Z, while the diagnostic's example brief is at 09:07Z. On 08-23, after the access, `boris` has 9 distinct main ids in the log (285042 and 298048), and 11 briefs still mismatch under the first criterion: production kept 285042 after the access. Why is not established; the sprint note says only that 298048 "enters for boris after the access bump". The diagnostic ran on the 2026-08-22 epoch; the file dates from 2026-10-04. |
| 3 [medium] | §4.3.2 l.995-997 (dedup not replayed; positions do not establish final served membership); the Abstract wording after rc10 F2 | yes | yes, verbatim | §9 now says salience ranks 1, 3 and 4, not slots. "90, 30, and 42 days" and "4,632 of 4,632" were already in §9. |
| 4 [medium] | `out-ord0826.json` `ids.lift_F7_pinned`: 17 lists (2026-09-02 is `null`, 0 briefs), each without 116107 and with 227328, 112241 and 116467; `serving-brief.ts:783-784` (`current` = baseline, no fresh slots) and 819-821 (`pinnedIds` from `current.items`) | yes | yes, verbatim | "no-fresh brief" is right: `current` is built by `pickDedup(pools, quotas, n, salience)` without the fresh pool. |
| 5 [medium-low] | rc10 l.137-140 | yes | yes, verbatim | Not covered by any finding and left as is: §4.3.1 "the 3 shared slots are taken by the high-pain floor" (rc11 l.899) and the F7 row label "high-pain floor" in the leave-one-out table. They name the filter (F7) by its code name and say which slots it takes, not what placed the chunks there. |
| 6 [low] | `measurement/sprint-censo-artefatos-paperA.py` run on the Portuguese `MANUSCRIPT.md` (the text the item referred to; its Appendix D detector matches only `## Apêndice D`): 1 MISSING (`ts-350.txt`) and the Appendix D entries absent from v1.0. Against `MANIFEST-v1.1.json`: the 9 files (`BATCH-CYCLE-2026-08-28/29.json`, `CEILING-DESIGNATION-SENSITIVITY-2026-08-28.json`, `CEILING-GRANULARITY-2026-08-28.json`, `measurement/CHANNEL-ATTRIBUTION-2026-08-29.json`, `POOL-ELEGIVEL-2026-08-28.json`, `PREDICTION-2026-08-29.md`, `TIEBREAK-EXPOSURE-2026-08-29.json`, `measurement/gatilho-saturacao.sh`) are items of v1.1, and `implantacao/` is carried as its 9 files under `measurement/implantacao/`. The census also lists `measurement/` itself (a directory token; v1.0 already carries that directory). §5.6 l.1418-1421 says `ts-350.txt` "was not kept" | yes | yes, verbatim | — |
| 7 [low] | `out-ord0826.json`: 09-03 exact 0/441 and 09-07 exact 0/672, `briefs_where_served_minus_fresh_added_is_not_8` = all briefs (`fresh_added` null) | yes | yes | Edit inside the rc10 addendum. parity-rc11 `history` allows exactly this replacement there. |
| 8 [low] | — (wording) | yes | yes, verbatim | — |

## Number deltas (all declared in parity-rc11 with finding IDs)

Removed: "two" (R10-8); "diagnosed on 2026-08-22" (R10-2). Added: 83.78% (R10-8); 08-21, 08-22,
08-23, the 2026-08-22 epoch, 285042 ×2, 85.8%, 85.7%, 84.3% (R10-2); 1, 3, 4 (R10-3); 112241,
116467, "three" (R10-4); §4.3.2 (R10-5); 10, §5.6, `ts-350.txt` (R10-6); 2026-09-03, 2026-09-07,
`fresh_added` (R10-7); `diag-out.txt` ×2, `diag-residual-mismatch.py`, 2026-08-22 (R10-1).

## F-5

"Addendum, rc11 (2026-10-05): a Fable regression review of rc10." appended after the rc10
addendum, before Open items.
