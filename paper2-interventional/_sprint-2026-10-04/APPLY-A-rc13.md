# APPLY A-rc13 (2026-10-05): findings of REVIEW-A-rc12-2026-10-05.md

Input `A-v1.1-rc12.md` (sha256 `01423190…f695d`) → output `A-v1.1-rc13.md` (sha256
`9c3cefc0…f1eb86c`). Gate: `A-rc13/parity-rc13.py --selftest`: PARITY OK, SELFTEST OK (24
mutations: 23 bite on the expected check; the unit mutation is not caught, as in rc10 to rc12, and
the selftest records that as a known limit). The deposit copy
`deposit/paperA-v1.1/MANUSCRIPT-v1.1.md` is byte-identical to rc13 (parity `deposit` check).

The two reviews are saved verbatim in `REVIEW-A-rc12-2026-10-05.md`: the Codex final message
(receipt `adversary-receipt-codex-2026-10-05T125855-34251.txt`, exit 0) and the DeepSeek findings
JSON (receipt `adversary-receipt-deepseek-2026-10-05T125812-33216.txt`, exit 0), both recovered
from the shell transcripts because the wrapper does not persist output. IDs: C1, C2 = Codex
findings 1, 2; DS1..DS6 = the DeepSeek findings in order.

parity-rc13 carries every rc12 check (numbers, footnotes, refs, code, links, headings, tables,
history, qualifiers, the 35 `classes`, `withdrawn`, dashes, addendum, deposit). `history` now
requires the addenda rc5..rc12 to be byte-identical (rc13 edits none of them). `withdrawn` carries
the 10 rc12 phrasings and adds 10 (DS1 ×3, DS2, DS3, DS5, DS6, C1, C2, and the §9 sentence of the
C1 sweep). Qualifier counts are unchanged from rc12 (no declared delta).

| # | verified against | holds? | applied? | note |
|---|---|---|---|---|
| C1 [medium] §4.3.2 | `serving-brief.ts:436-451` (phase 0 places `pinnedIds` first, sorted by score), `:819-821` (`pinnedIds` = high-pain items of the no-fresh `current` brief); `out-ord0826.json`: `lift_F7_pinned` on every day with briefs 2026-08-21..09-07 has 33 ids, without 116107, with 227328, 112241 and 116467 still present; `out/SALIENCE-COUNTERFACTUAL-PROD-2026-10-05.json` (ranks 1/3/4 → 44–46 with access zeroed) | yes | yes, verbatim | "the other [condition of their rank]" made the pin a rank condition, while the same paragraph says the rank is unchanged when it is lifted. Sweep (Abstract, §1, §9; addenda left as history): the Abstract said "keeps them in every brief" (DS2, below); §1 said "held there by the high-pain pin … takes all three corpus-wide slots" (DS6, below); §9 said "the high-pain pin holds in every brief what that score placed there", now "The high-pain pin, which places them first in every brief, protects what that score placed there and is measured as necessary for main-set membership for one of the three (§4.3.2)". §4.3.2 l.965-966 ("positions … determined by tracked search traffic") is about rank and stays. |
| C2 [medium] §4.3.1 | `out-ord0826.json` `per_epoch.*.fidelity`: on every non-null day 2026-08-24..09-06 `briefs_main_set_exact + briefs_where_served_minus_fresh_added_is_not_8 == briefs`; `served_main_slots − 8 × briefs` exceeds the not-8 count by 1 (08-24, 08-26, 08-28), 3 (08-29, 08-30, 08-31), 2 (09-01, 09-05), 6 (09-04, 09-06), 0 (08-25, 08-27). E.g. 2026-08-24: 672 briefs, 649 exact, 23 not-8, 5,400 residual ids = 5,376 + 24. Since served minus `fresh_added` is at most 10, those briefs leave 9 or 10. Null days: 2026-09-03 4,410 = 441 × 10, 2026-09-07 6,720 = 672 × 10 | yes | yes, verbatim | Codex's arithmetic reproduced exactly. |
| DS1 [high] §1 | Searched `out/`, `measurement/out/`, `_sprint-2026-10-04/`, `A-recon-evidence/deposited-22181415/` (v1.0 MANUSCRIPT, MANIFEST, zips): no artifact holds the five-day series. Origin: commit `bcca3a3` (2026-08-28) added a v1.0 table computed by `measurement/regime-cobertura.py` (17–21/08, "frescos ≤7d" 0, "idade mín." 13.96 → 17.96); the script's output was never saved (no `novos_absolutos` / `idade_minima_servida` file anywhere). The claim also fails as written: that table's own "novos" column shows 1 on 17/08 and 52 on 20/08, and `RECON-52-e-sondas-2026-10-04.json` shows the 52 (`memory/lessons.md`, created 2026-08-20 02:02:03 UTC) served from 2026-08-20 21:38 to 08-22 19:07, absent from `chunks` (`por_dia_utc`: 87 vs 35 on 08-20, 85 vs 33 on 08-21), so the min-age column, computed with `JOIN chunks`, could not see them. What an artifact does hold: `BATCH-CYCLE-2026-08-29.json` (packaged since v1.0; in `artefatos-v1.1.zip`), batch 2026-08-21..22: `servidos` 108 every day 08-22..08-29 except 109 on 08-26; `idade_min` 0.92, 1.92, 2.92, 3.92, 4.92, 5.92, 6.92 on 08-23..08-29 | partly: the measurement exists for another set (the global batch), not for the five days | yes, rewritten | §1 now cites the BATCH-CYCLE series with dates and the file; §4.3.1 (end of the defective-ingestion paragraph) states it with dates and the endpoints 0.92 → 6.92; §2's bullet calls them "the frozen days that §1 cites (2026-08-23 to 2026-08-29) … days on which the served coverage set did not change" (`COVERAGE-SET-FROM-LOG-2026-10-04.json`: same 108 ids 08-23..09-19). §1's "the five-day observation belongs to the first [per-agent sub-pool]" became "that batch belongs to the second", since the 08-21..22 batch is `entities/%` + `lessons.md` (§4.3.1). The withdrawn claim is not added to the status block's no-artifact list because it no longer appears in the text; the rc13 addendum records why it left. |
| DS2 [medium] Abstract | as C1 | yes | yes, own wording, aligned with C1 | "With the access term zeroed they fall to ranks 44–46: tracked search traffic from months ago (§3.1) is necessary for their observed salience ranks in the measured counterfactual. The high-pain pin places them first in every brief, but it protects only items that the score has already placed there (`brief.ts:819-821`), and lifting it removes only one of the three from the main set (§4.3.2)." The proposed "contributes to keeping them" was not used: it keeps the vagueness C1 removes. |
| DS3 [medium] §2 | §3.1 definition of *no-record* and its lower-bound clause | yes | yes, own wording | "*No-record*, the absence of a record in both (§3.1), is therefore a verifiable property of the records, not an inference; read as non-delivery, it is a lower bound for the brief and tracked search (§3.1)." The definition still occurs once, in §3.1 (parity `qualifiers`). |
| DS4 [low] §4.3.1 table | `out-ord0826.json` `leave_one_out.*.briefs_changed_vs_baseline` per day: every 672-brief day 2026-08-24..09-07 gives 672/0/672/192/672/672 (F1, F3, F4, F5, F6, F7); 2026-09-03 (441 briefs) gives 441/0/441/126/441/441; distinct counts identical on every day | yes | yes | Header "(of a 672-brief day)" and a note under the table naming 2026-09-03 (441, 126) and citing `leave_one_out`. |
| DS5 [low] §1 | `serving-brief.ts:800-813` (`freshPool = interleaveFresh(agentFresh, globalFresh)`); §4.3.1 sub-pool table (per agent 0, global 108; `POOL-ELEGIVEL-2026-08-26-to-29.json`) | yes | yes, own wording | "Between batches no new item enters the coverage pool (on 2026-08-26 to 08-29 its per-agent sub-pool held 0 eligible chunks and its global sub-pool 108, §4.3.1)". "The pool is empty" is withdrawn. |
| DS6 [low] §1 | §4.3.1 "the 3 shared slots are what `mainTarget` leaves after the agent quota (8 − 5)" | yes | yes | §1 now reads "The high-pain pin (`pain ≥ 0.9`) places them first, in the three shared main-pool slots; it protects only what the score has already placed in the brief, and it is measured as necessary for main-set membership for one of the three (§4.3.2)." |

## Number deltas (all declared in parity-rc13 with finding IDs)

DS2: "three" +1, 4.3.2 +1. DS6: "three" +1. DS5: 2026 +1, 08 +2, 26 +1, 29 +1, 0 +1, 108 +1,
4.3.1 +1. DS1 (§1, §2, §4.3.1; the file name `BATCH-CYCLE-2026-08-29.json` counts its digits):
2026 +14, 08 +16, 21 +2, 22 +3, 23 +3, 26 +2, 29 +6, 108 +2, 109 +2, 1.00 +1, 0.92 +1, 6.92 +1,
"five" −4. DS3: 3.1 +1. DS4: 2026 +3, 08 +1, 24 +1, 09 +2, 07 +1, 03 +1, 672 +2, 441 +2, 126 +1.
C2: 10 +2, 2026 +2, 09 +2, 03 +1, 07 +1. C1 sweep (§9): "three" +1, 4.3.2 +1. Refs: §4.3.2 +2,
§4.3.1 +1, §3.1 +1. Code: `BATCH-CYCLE-2026-08-29.json` +2, `fresh_added` +1,
`out-ord0826.json` +1, `leave_one_out` +1. Table: the §4.3.1 filter-table header (DS4).

## F-5

"Addendum, rc13 (2026-10-05): a Codex and a DeepSeek review of rc12." appended after the rc12
addendum, before Open items.

## Package

`build-package.py`: `FONTE` → rc13; `REVIEW-A-rc12-2026-10-05.md` and `APPLY-A-rc13.md` added to
the artefacts, `A-rc13/parity-rc13.py` to the scripts (the rc13 addendum cites all three). Rebuild
results are in `deposit/paperA-v1.1/DRAFT-READBACK.md`.
