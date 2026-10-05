# APPLY A-rc12 (2026-10-05): findings of REVIEW-A-rc11-2026-10-05.md

Input `A-v1.1-rc11.md` (sha256 `2ee8520c…fb00d`) → output `A-v1.1-rc12.md` (sha256
`01423190…f695d`). Gate: `A-rc12/parity-rc12.py --selftest`: PARITY OK, SELFTEST OK (19 mutations:
18 bite on the expected check; the unit mutation is not caught, as in rc10 and rc11, and the
selftest records that as a known limit). The deposit copy `deposit/paperA-v1.1/MANUSCRIPT-v1.1.md`
is byte-identical to rc12 (parity `deposit` check).

parity-rc12 carries every rc11 check (numbers, footnotes, refs, code, links, headings, tables,
history, qualifiers, the 35 `classes`, `withdrawn`, dashes, addendum, deposit). `history` now
requires the addenda rc5..rc11 to be byte-identical (rc12 edits none of them). `withdrawn` carries
the 8 rc10 phrasings and adds 2: the old §4.3.1 phrase "the 3 shared slots are taken by the
high-pain floor" (R11-2) and the old §9 order "last accessed 90, 30, and 42 days" (R11-4c). Both
reverts move no token, so only `withdrawn` sees them (two selftest mutations show it biting).
Qualifier counts are compared against rc11's own counts plus a declared delta (one: R11-2 adds a
"phase 0").

The review is saved verbatim (findings part) in `REVIEW-A-rc11-2026-10-05.md`; its findings are
numbered (2), (3), (4) there, and finding 4 has two parts (Appendix D and §9).

| # | verified against | holds? | applied? | note |
|---|---|---|---|---|
| 2 [medium-low] | `serving-brief.ts`: l.436 `mainTarget = max(0, n − freshSlots)`; l.442-451 phase 0 (pinned, sorted by score, `tryPick` until `n`); l.457 phase 1 breaks at `got >= quotas[i]` or `picked.length >= mainTarget`; l.531 `buildPools` pushes the agent pool (`sessions/<agent>/%`, from `scopePatterns("global", agent)`, l.202-215) first with quota `ceil(n/2)` = 5, then the `scope=global` pool with `floor(n/2)`. `out-ord0826.json`: on all 17 days with briefs `pinned_per_brief_hist` is `{"3": all}`, `pinned_ids_seen` = [112241, 116107, 116467]; `ids.lift_F7_pinned` has 33 ids, without 116107, with 227328, 112241 and 116467; baseline − lift = {116107}, lift − baseline = {227328}; `mean_jaccard_vs_baseline` 0.7778 = 7/9 (one id swapped of 8). `picks.by_subpool` on 2026-08-26: scope 2016 = 672 × 3, agent 3360 = 672 × 5 | yes | yes, verbatim (line breaks only) | As served: phase 0 places the 3 pinned (picked = 3), phase 1 gives the agent pool 5 (picked = 8 = `mainTarget`) and the `scope=global` pool breaks at once. With F7 lifted: the agent pool takes 5, the global pool takes 3 (8 − 5). So the floor decides one occupant (116107) of the three slots, not the slots. §4.3.2 (rc12 l.1012) already says "227328 takes its place, while 112241 and 116467 stay", so the pointer `(§4.3.2)` lands. The rc11 APPLY had left this sentence as is (row 5 note); this finding corrects that. Sweep: l.863-866 (F7 definition, phase order) and the §4.3.2 pin paragraph are code descriptions; the l.895 table label names the filter; §1 l.138-140 ("held there by the high-pain pin … takes all three corpus-wide slots") is true as served and was the rc11 finding 5 wording. Left as is. |
| 3 [low] | `.remember/adversary-receipt-codex-2026-10-05T100118-80790.txt`: exists, 630 bytes, under `.gitignore:6` (`.remember/`), not tracked; cited by the rc8 addendum (rc12 l.2627); in neither zip. `diag-out.txt` headers: `# diag.py preservado-0908.db 2026-09-08`, `# diag.py ord-0826.db 2026-08-22`, `# diag.py ord-0826.db 2026-08-28 (control: expect no mismatch)` | yes | yes, verbatim, in `build-package.py` | Both declarations live in `EXCLUIDOS` of `build-package.py`, so a rebuild keeps them: a new entry for the receipt, and the `.db` entry's `o_que` now ends "(nomes de trabalho em diag-out.txt: ord-0826.db, preservado-0908.db)". No text change. |
| 4a [low] | Appendix D table: full sprint paths are `_sprint-2026-10-04/A-rc2/coverage-set-from-log.py` and, after 4b, `_sprint-2026-10-04/A-filters-disaggregation/diag-residual-mismatch.py` (file exists there) | yes | yes, verbatim | "the two sprint scripts whose full paths the table gives". |
| 4b [low] | `diag-out.txt`: three runs (2026-09-08 on `preservado-0908.db`, 2026-08-22 and the 2026-08-28 control on `ord-0826.db`) | yes | yes, verbatim | Table row of the filter disaggregation. |
| 4c [low] | `out/SALIENCE-COUNTERFACTUAL-PROD-2026-10-05.json` `the_three` (`last_accessed_at`: 116467 2026-07-17, 112241 2026-05-30, 116107 2026-07-29 → 42, 90, 30 days before 2026-08-28) and `rounds[0].union_149.prod` ranks (116467 1, 112241 3, 116107 4); Abstract l.59 "(last accessed 42, 90 and 30 days …)" | yes | yes, verbatim | Reorder only; the multiset of numbers is unchanged. |

## Number deltas (all declared in parity-rc12 with finding IDs)

Added: 8, 5, 0 ("phase 0"), 3, "three" ×2, 227328, 116107, §4.3.2 (R11-2); "two" (R11-4a); 2026 ×3,
08 ×2, 09, 28, 10, 04 (R11-4b: the two dates, and the `_sprint-2026-10-04/` path, whose digits the
extractor counts). Code spans: `mainTarget`, `scope=global` (R11-2); `diag-residual-mismatch.py`
→ `_sprint-2026-10-04/A-filters-disaggregation/diag-residual-mismatch.py` (R11-4b). Removed: none.

## F-5

"Addendum, rc12 (2026-10-05): a Fable review of rc11." appended after the rc11 addendum, before
Open items.

## Package

`build-package.py`: `FONTE` → rc12; `REVIEW-A-rc11-2026-10-05.md` and `APPLY-A-rc12.md` added to
the artefacts, `A-rc12/parity-rc12.py` to the scripts (the rc12 addendum cites all three); the two
exclusion declarations of finding 3. Rebuild results are in `deposit/paperA-v1.1/DRAFT-READBACK.md`.
