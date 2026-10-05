# APPLY — Paper A rc4 → rc5 (2026-10-05)

Input: `A-v1.1-rc4.md` (sha256 `bde5b8d4764c7bc3…db004bea`, 2,555 lines), unchanged.
Output: `A-v1.1-rc5.md` (sha256 `d2be7f49ddcab74a…e116e086`, 2,609 lines). Only rc5 was edited.
Parity: `A-rc5/parity-rc5.py` → `PARITY OK` (19 hunks, 20/20 anchors, 31 token keys, no heading or
fence change); `--selftest` → `SELFTEST OK` (5 mutations, all bite).
Guard: `claims_check.py::contrafactual_check` gains item 6 (see below).

Source: the Codex regression review of rc4 (receipt
`.remember/adversary-receipt-codex-2026-10-05T073216-97736.txt`, exit 0), findings verbatim in
`A-rc4/CODEX-REGRESSAO-rc4-VERBATIM.md`, cited here as R1–R10. Line numbers are rc4's. Each was
checked against rc4, the deposited `serving-*.ts` and the cited artifacts. **10 confirmed, 0
rejected.** No number was recomputed in this round.

| # | where (rc4) | verdict | evidence | applied in rc5 |
|---|---|---|---|---|
| R1 | §4.4 l.1042–1044; §5.3 cons. 1 l.1240–1242 | confirmed | §5.3 already admits dedup-driven swaps outside the boundary stratum; §5.4's own counterexample shows the condition is necessary, not sufficient. The 17/350 is the replay's count of states that change at `w = 100,000` (`mexeu = 17`), and Attempt 1 of §5.6 shows the stratum condition itself was never validly measured. | §4.4 and consequence 1: under §5.3's premises the condition's fraction is an upper bound; the ceiling is the measured fraction of states that change at a saturating dose, dedup included. |
| R2 | Abstract l.47 | confirmed | 9,755 is a candidate count (upper bound on tracked-search returns); it cannot carry "for the most part initiated by the agent". §1 l.97 and §4.1 l.491 make no majority claim. | Abstract: most recorded exposure is not a system-decided delivery (supported by the 1,635 of the next sentence); search's actual delivered share is not established. No numeric change. |
| R3 | §3.1 l.312–315, l.328–329 | confirmed | `serving-search.ts:379-380`: `enabled=false skips the write entirely — used by healthchecks / the semantic canary`; `search`, `searchSemantic`, `searchHybrid` all take `trackAccess` (l.400, 488, 616). | §3.1: "tracked search" in the superset, complement and 56,288 statements, plus one sentence on `trackAccess = false`; same qualifier in §1 l.98, §4.1 l.492 and the F-5 Codex-1 entry. |
| R4 | §4.3.2 l.954, l.956 | confirmed | `buildPools` (`brief.ts:521-538`): agent ⇒ quotas `ceil(n/2)`, `floor(n/2)`; no agent ⇒ `n`. `pickDedup` (`:406-485`): pinned first, phase 1 quota, phase 2 and 4 backfill from `pools.flat()` by global score; `tryPick` can reject any candidate, the target included. | "Nominal quota of five in the first pass, before pinning and backfill; without an agent the whole brief"; dedup "may remove candidates above them or reject them", so pool positions do not establish final membership. |
| R5 | §4.3.2 l.948–949 | confirmed (partly overstated by the reviewer) | `sprint-contrafactual-salience-producao.mjs` fixes the 149-chunk population and every attribute except the access ones (`prod_acc0`, `dropFuture` at l.92–106). The recency bracket is sound for that fixed population, but "the true position" asserts a historical reconstruction the script does not do. Envelope from the artifact: 23–47 (`prod_acc0` ∪ `prod_acc0_drop_future_access`, `union_149`, all 10 instants). | "Positions span 23–47 in this fixed retrospective population, with every other attribute as in the copy: a sensitivity range, not a reconstructed historical serving position." |
| R6 | Appendix A l.2060–2061 | confirmed | `A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json`: non-main distinct = 52 (08-21), 160 (08-22), 108 from 08-23 to 09-19 (09-02 no rows), 110 (09-20), 92 (09-21); main set identical only 08-24 to 09-19 (§4.3.1 l.868–870). | "(spanning 2026-08-21 to 2026-09-21; the same 33 main and 108 coverage ids on every measurable day from 2026-08-24 to 2026-09-19)", matching §4.3.1's `33 + 108 = 141` interval. |
| R7 | §5.5 l.1294–1296, l.1312–1314 | confirmed | "immune, by construction" and "does not respond to the score" contradict §4.3.2/Abstract/§9 ("responds to score only within `last_served` ties") and §5.5's own table row ("bounded by Corollary 2"). Same class found and fixed in §5.5 l.1318 ("no relevance adjustment could change it there") and §9 l.1993 ("structurally deaf to the score"). | §5.5: responds only within dominant-coordinate ties, bounded by construction; the coverage part "responds to the score only within `last_served` ties and then saturates (§5.3, §5.4)"; l.1318 "beyond the ceiling"; §9 "responding to the score only within `last_served` ties, up to a ceiling". |
| R8 | §5.4 l.1259–1264; F-5 l.2414–2415 | confirmed | `coverageCompare` (`brief-diversity.ts:130-140`) returns `bSalience − aSalience` = 0 on equal treated scores; `ranked.sort` (`brief.ts:612-614`) is stable, so input order decides. Strict `>` is sufficient, not necessary. | Sentence after the (unchanged) fence: equality admits `d` when the tie-break places it ahead of `c_K`; the "in general it does not" clause reworded so it no longer dangles. F-5's Codex-4/5 entry carries the equality case. |
| R9 | F-5 l.2397 | confirmed | `SALIENCE-COUNTERFACTUAL-PROD-2026-10-05.json`: with access the three rank 1/3/4; with access zeroed 44–46. "Access takes the three out of the top-10" states the reverse. | "The claim that zeroing the access component takes the three out of the top-10 stands." |
| R10 | F-5 l.2387–2388 | confirmed | `sprint-bonus-vs-passo.py:38-41` parses `P2_DELTA_CUT` and `SEVERIDADE_PAIN` from `serving-brief-outcome.ts` with regexes; the two `.mjs` import `calculateSalience` from `serving-salience.ts`. | "Three quantities ... each with a dated artifact: the salience scripts import the production function `calculateSalience`, and the bonus script reads the production constants from the deposited source." |

Appendix F-5 also gets an **Addendum, rc5** paragraph (end of F-5, before Open items) listing the
ten corrections. The Kimi-10 description inside F-5 is left as the rc4 history and superseded
explicitly in the addendum.

## Numeric delta rc4 → rc5 (all owned, none recomputed)

| token | Δ | owner | justification |
|---|---:|---|---|
| `379`, `380` | +1 each | R3 | file lines of the `trackAccess` comment, `search.ts:379-380` |
| `5` / `five` | −1 / +1 | R4 | "at most 5 slots" → "nominal quota of five" (the addendum then quotes "At most 5" once and "Codex-5" once: net `5` +1) |
| `0` | +1 | R8 | "the comparator returns 0" |
| `5.6` | +1 | R1 | §4.4 cites §5.6 for the measured ceiling |
| `5.4` | +4 | R1 (×2), R7, addendum | §4.4 and consequence 1 cite §5.4 for "not sufficient"; §5.5 cites §5.3, §5.4 |
| `5.3` | +3 | R7, addendum (×2) | |
| `2026`, `08`, `09`, `24`, `19` | +2, +1, +1, +1, +1 from R6; rest addendum | R6, addendum | Appendix A adds the 2026-08-24 to 2026-09-19 interval; the addendum repeats both intervals and cites two dated files |
| `10`, `04`, `05`, `21` | +5, +2, +1, +2 | addendum | dates and paths; `10` also from "Kimi-10" and "top-10" |
| `1`, `4`, `9`, `3.1`, `4.1`, `4.3.2`, `4.4`, `5.5` | small | addendum | section and finding labels |
| `23`, `47`, `33`, `108` | +1 each | addendum | names the R5 range and the R6 set |
| `ten`, `three` | +2 each | addendum | "ten findings", "all ten"; "the three themselves", "takes the three" |

## parity-rc5.py

Extends `parity-rc4.py` (same numbers / owners / headings / fences contract, rc4 → rc5 defaults)
with one stricter rule: a REGISTRY anchor must not occur on the other side, so an anchor cannot
land in a hunk by being text that already existed. Self-test mutations: (1) number in untouched
prose → `numbers`; (2) heading → `headings`; (3) R4 reverted with its numeral → `numbers`;
(4) R9 reverted in pure prose → `owners`; (5) an anchor planted in OLD inside a hunk that changes
anyway → `owners` with "also occurs on the other side" (only the new rule sees it).

## claims_check.py::contrafactual_check

Item 6 added: the text must contain "positions span LO–HI in this fixed retrospective
population" with LO–HI derived from `out/SALIENCE-COUNTERFACTUAL-PROD-2026-10-05.json` (envelope
of `prod_acc0` and `prod_acc0_drop_future_access`, `union_149`, all instants = 23–47), compared on
whitespace-normalised text, and must not contain "the true position lies in". Run against a
scratch root holding rc5 as `MANUSCRIPT.md`: 0 failures; rc4: both new checks fail; a mutated
range (23–46) and a reinserted "the true position lies in" each fail. The guard still reads
`MANUSCRIPT.md`, which rc5 has not been promoted to.

Not done here (rules of this round): no git, no Zenodo, no voices. The rc4 "Not applied here"
list in F-5 is unchanged.
