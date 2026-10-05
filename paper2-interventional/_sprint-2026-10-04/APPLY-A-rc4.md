# APPLY — Paper A rc3 → rc4 (2026-10-05)

Input: `A-v1.1-rc3.md` (sha256 `a8808753…abf15a`, 2,344 lines), unchanged.
Output: `A-v1.1-rc4.md` (sha256 `e1f30245…e331c6`, 2,542 lines). Only rc4 was edited.
Parity: `A-rc4/parity-rc4.py` → `PARITY OK`; `--selftest` → `SELFTEST OK` (3 mutations, all bite).

Sources: R1–R14 = the 14 confirmed findings of `REVIEW-A-rc3-2026-10-04.md`; the other IDs are
the verified findings of the 2026-10-05 round (Codex, DeepSeek, GLM, Kimi; merged duplicates
kept under the surviving ID: Kimi-9 → GLM-5, Kimi-12 → GLM-2, Kimi-13c → GLM-1). Line numbers
are rc3's.

## Recomputations (new scripts and artifacts)

| finding | script | artifact | sha256 | result |
|---|---|---|---|---|
| R4 (tie-break on the comparator's key) | `measurement/sprint-empates-salience-producao.mjs` (new, this round; imports `calculateSalience` from `serving-salience.ts`) | `out/TIEBREAK-EXPOSURE-PROD-2026-10-05.json` (new) | `6921013636cf0071…19ed7b7` | 15 distinct `calculateSalience` values over the 108 (6 on the pre-rank key). Pairs at second / minute / hour / day: 34–42 / 212–238 / 472–749 / 1,197 (0.59–0.73% / 3.67–4.12% / 8.17–12.96% / 20.72%), against 45–59 / 277–322 / 663–1,024 / 1,656 on the pre-rank key at the same three instants (2026-08-26 20:37Z, 22:00Z, 23:52:09Z). Partial anchor: the day row on the pre-rank key reproduces the published 1,656; the published 68 / 269 / 917 came from an unrecorded 2026-08-29 instant that the input (brief_log through 2026-08-26 23:52:09) does not reach. Guards: pool = the 108 reference ids at every instant; every pool chunk has a last_served inside the window. Remaining ties: chunks of one `lessons.md` ingestion, or entity chunks with identical importance, pain, access count and access instant. |
| Codex-2 / Codex-3 | `measurement/sprint-contrafactual-salience-producao.mjs` (pre-existing, run by the verifier) | `out/SALIENCE-COUNTERFACTUAL-PROD-2026-10-05.json` | `7348e948…2374d82d` | used as given; values spot-checked (1/3/4; 44–46, 45–47 by day; 23–25 drop-future; 54–56 / 40–42 / 50–52; scope pool 1/5/6 → 76–119; 76–79 above from 43–46 files; `retention_days_null` 35 / 39,130). |
| Codex-14 / 14b | `measurement/sprint-bonus-vs-passo.py` (pre-existing) | `out/BONUS-VS-STEP-2026-10-05.json` | `16be90a1…0275fb5846` | used as given (0.0473; 0.897×). |

Input of the first two: the read-only extract of a copy of `e20260907T060001Z.db`
(sha256 `4ec7e182…1fe721345`), kept in the session scratchpad only, because it lists private
source paths. No artifact written this round contains a path, host or IP.

## Finding → status → what changed

Status: **A** applied as proposed; **A\*** applied with an adjustment (reason given); **S**
superseded; **P** applied in the manuscript, with a part outside the manuscript not applied.

| finding | status | where (rc3) | what changed in rc4 |
|---|---|---|---|
| R1 | A | §9 l.1861, l.1893 | 1,635 live (1,787 counting the 152 deleted); "2.43% (1,635/67,187, live)" |
| R2 | A | §5.3 item 2 | in the 350 measured states the never-served stratum is empty, so 17/350 comes from one-second ties |
| R3 | A | Abstract, §1 l.162, §4.3.2 table, §9 | ceiling qualified: 2026-08-26 corpus, defective-ingestion regime, empty never-served stratum |
| R4 | A (recomputed) | §5.7.1 l.1400-1425; App. D | text distinguishes the SQL pre-rank (6 values) from the comparator key (`calculateSalience`, 15 values); table replaced by the recount with a same-instant pre-rank column; "24× / 1.18%" → "28–35× / 0.59–0.73%"; old artifact kept as the pre-rank count; App. D gets the new row |
| R5 | A | status block; Abstract l.58; §4.3.1 l.697-700 | exception list now names 5.6×, 1,971, 10,926, 20.5 (and the Kimi-1/Kimi-3 items); Abstract says the 5.6 reading is unpreserved; §4.3.1 flags the three numbers inline. The §5.7 strata counts: verified absent (Kimi-3) and flagged |
| R6 | A | §2 l.289-290 | drafting instruction deleted |
| R7 | A | Abstract, §4.3.2 l.980-983, §9 | "does not respond to score" → "responds to score only within `last_served` ties (17/350 here) and then saturates"; table cell "**only up to a ceiling** of 4.86%" |
| R8 | S | Abstract l.51-53 | superseded by Codex-2: positions are 1, 3, 4 (42, 90, 30 days), not 2, 3, 5 |
| R9 | A | §4.1 l.432-434 | merged with Codex#7 (see there) |
| R10 | A | §4.3.1 l.713 | "108 ids (spanning 308214 to 308496, not contiguous)" |
| R11 | A | §4.3.1 l.722-723 | "the tie structure that sets the ceiling" |
| R12 | A | §1 l.129; Open items | "5,376 main slots on a 672-brief day" |
| R13 | A | §6 l.1577-1578 | split reported in Paper B; aggregate 0.874 recorded in Appendix C |
| R14 | A | §4.3.1 l.858-859 | "every measurable day … (2026-09-02 has no rows)" |
| Codex-1 | A | §3.1 heading, l.301-302, l.313-315, l.369-370, Abstract l.44, l.91, l.471 | counter = superset of returned; complement exact as predicate count and lower bound on non-delivery; union no bound either way; 9,755 an upper bound on what search returned. Heading changed (documented in parity) |
| Codex-2 | A | §4.3.2 l.901-912, table, l.931-940, l.946-947; Abstract; App. D | production-function counterfactual: 1/3/4 → 44–46 (23–47); 201: 54–56; 144: 40–42; 196: 50–52; scope pool 76–119; old 131/129/128 kept as anchor; "beyond rank 100" withdrawn; App. D: new row, old row marked superseded |
| Codex-3 | A | §4.3.2 l.882-884 | recency has no floor; NULL retention = never-decay (39,130 chunks; 35 of 149; the three) |
| Codex-4 | A | §5.3 l.1158; Abstract l.88; §5 l.1071; §7; §9 | prefix premise stated with where it fails; "that serves a prefix of that order" added to the four generality claims |
| Codex-5 | A\* | §5.4 l.1186-1203; §5.5 table | iff restricted to a single bonused item, counterexample given, `b*` block removed, saturation from proportional bonuses. Adjustment: §5.5 table's "saturating at `b*`" → "saturating at a finite dose (§5.4)", since `b*` is no longer defined |
| Codex-14 | A | §5.4 l.1205-1210 | step vs distance not ordered in general; 0.0473, 0.90×; earlier 0.0946 / 1.79× explained |
| Codex-14b | P | §4.4 l.1032-1035 | manuscript corrected (0.0473, 0.90×; crossing several positions not established). **Not applied** (outside the manuscript): `DEVIATIONS-FOR-PAPER.md` l.83-86, l.167; `PROTOCOL-CALIBRATION-2026-08-27.md` l.306-309; `REPLAY-OPORTUNIDADE-2026-08-27.md` l.256; `replay-oportunidade.mjs:944,1014-1019` |
| Codex#6 | A | §4.4 l.1011-1013; §5.4 l.1202-1203 | lowest changing dose 0.02–4.4 (median 1.7), five censored at 0.02, spread ≥ 200× |
| Codex#7 | A | §4.1 l.432-437 | "young cohorts do not drive the headline"; descriptive, not a censoring correction; "more than twelve weeks" dropped; merged with R9 ("only the < 1 week cohort (n = 96) is higher") |
| Codex#8 | A | §5.7.1 l.1383-1385 | 2/9 ≈ 22% |
| Codex#9 | A | §4.5 l.1046-1048 | cron windows 21–23 and 51–53; 18 rows (2.6/day) of unestablished origin |
| Codex#10 | A\* | App. A l.1945-1947; §7 l.1745 | App. A caveat rewritten. Adjustment: "(through 2026-08-31)" from the proposed text replaced by "(states before 2026-09-01)", because GLM-4 established that no window ends 2026-08-31; the §7 sentence uses GLM-4's text |
| Codex#11 | A | §4.2 l.497-499 | per-type split by surface possible, not reported |
| Codex#12 | A | §6 table, `brief_log` row | attribution = paired replay `freshSlots = 2` / `0` |
| Codex#13 | A | §8.2 blockquote | monotone but responsive only within ties |
| Codex#15 | A | §6 heading, l.1569-1570; App. F l.2103 | §6 serves contribution (iv); heading changed (documented in parity) |
| Codex#16 | A | §4.1.1 l.465-467; Abstract l.40-41 | 99.98% = expected coverage under random draws; rotation reaches 100% |
| DeepSeek#1 | A | §9 l.1864; F-1 l.2115, l.2127-2128 | 325 "as printed then"; locked numbers give ≈ 327 |
| GLM-1 | A | App. D intro + rows | `claims_check.py` location; 2026-10-04 artifacts listed; four rows added (plus the rows of this round's three artifacts) |
| GLM-2 | A | Abstract l.56-57; §1 l.210-211, l.220; §4.1 l.410; §9 l.1877-1878 | 0.16% cut by patterns + importance floor + age window; which binds not decomposed |
| GLM-3 | P | §5.7.2 l.1542 | 104 s, times uncheckable. **Not applied**: the "98 segundos" comment in `claims_check.py:967` |
| GLM-4 | A | §7 l.1745 | windows named; serving-log comparisons span the trial and are descriptive |
| GLM-5 | A | title note l.4-5 | "on every measured day (inside the defective-ingestion regime, §4.3.1)" |
| GLM-6 | A | App. A table | precedence belongs to the declaration (20:07:24Z) over the round (20:25:00Z) |
| GLM-7 | A | §5.5 table | capacity moves the cut; at most one straddling stratum |
| Kimi-1 | A | App. F l.2070-2072, l.2088-2090; status block | pre-cleanup 87/77/288/26.7% flagged as unpreserved; artifact's actual content stated; per-section densities flagged |
| Kimi-2 | P | App. D size-axis row | manuscript-side fix applied. **Not applied** (script side): extending `robustez-tamanho-exposicao.py` to write the partials and regenerating `out/SIZE-ROBUSTNESS-2026-08-30.json`; rewriting a dated, cited artifact in place is the defect §6.1 describes |
| Kimi-3 | A\* | status block; §4.3.2; Abstract; l.946-947; §5.7 l.1336 | strata counts flagged; "128 other chunks" replaced (Codex-2: 22 to 44, derived from the tie ranges of the new artifact). Adjustment: the last-access dates are **not** flagged as artifact-less, because `out/SALIENCE-COUNTERFACTUAL-PROD-2026-10-05.json` (`the_three`) now holds them (2026-09-07 copy; `last_accessed_at` only moves forward, so a pre-2026-08-28 value there is also the 2026-08-28 value); a note after the table says so |
| Kimi-4 | A | §5.6 l.1250-1251; §6 table l.1583 | module-private constants named; the ordered pool is returned by no export |
| Kimi-6 | A | App. A l.1972-1974 | the S2 → ≥ S1 migration is in Paper B, not in the deviations log |
| Kimi-8 | A | §4.3.1 l.822-824 | "each day with rows … 2026-09-02 has none", criterion stated |
| Kimi-10 | A | §4.4 l.990-991 | ceiling definition carries both conditions of §5.3 |
| Kimi-11 | A | §5.3 l.1152-1153 | full exit condition `|| picked.length >= n`, `brief.ts:472`; dedup-rejected candidates do not count |
| Kimi-13a | A | §3.3 l.335-337 | `salience.ts` named; formula = `calculateSalience` in `serving-salience.ts` |

Totals: 48 findings (14 + 34). 47 applied in the manuscript (4 with an adjustment, 3 with a part
outside the manuscript left undone), 1 superseded (R8 → Codex-2).

## Appendix F and Appendix D

- New entry **F-5** (after F-4) lists every correction of this round with its source ID, the
  three recomputations, and the out-of-manuscript items not applied.
- The `[TODO at deposit]` of Appendix D is **left open**: no new Zenodo version exists and none was
  created in this round.

## Parity (`A-rc4/parity-rc4.py`)

- 205 numeric tokens change (multiset delta pinned in `EXPECTED_DELTA`); each is listed with the
  finding IDs of the hunks it changes in. 77 diff hunks; every hunk has at least one of the 86
  registry anchors and every anchor lands in a changed hunk. Most of the token churn is the new
  F-5 entry and the Appendix D rows (dates and section numbers).
- Headings: three documented changes (§3.1 Codex-1a, §6 Codex#15, F-5 inserted). Fenced blocks:
  one removed (`b* = …`, Codex-5).
- Selftest mutations: a number in untouched prose (fails on numbers + owners), a heading
  (headings + owners), a registered correction reverted, GLM-3 104 → 98 (numbers + owners).

## Writing pass

`avoid-ai-writing` (technical register) applied to the changed sentences only: one emphatic
"actually" removed (§4.3.2), bold leads removed from the F-5 list. Em dashes in changed lines are
the pre-existing table conventions and the F-5 heading, kept to match F-1..F-4.

## For integration (not done here)

- `claims_check.py::contrafactual_check` reads `MANUSCRIPT.md` and `TOP-COUNTERFACTUAL-2026-08-29.json`
  and expects the 2/3/5 → 131/129/128 rows; when rc4 becomes the guarded text it has to be
  rebased on `out/SALIENCE-COUNTERFACTUAL-PROD-2026-10-05.json`, or it will fail.
- No git command was run; nothing was published; no voice was run.

## Fixes after the independent check (2026-10-05, `CHECK-A-rc4-B-rc4.md`)

rc4 edited in place (it is not deposited). After: sha256 `bde5b8d4764c7bc3…`, 2,555 lines,
184,456 bytes. Parity rerun on rc3 → rc4: `PARITY OK`; `--selftest`: `SELFTEST OK` (3 mutations,
all bite).

| defect | where | what changed |
|---|---|---|
| D-A1 | §4.3.2, scope-pool sentence | Each variant now carries its own numbers from `out/SALIENCE-COUNTERFACTUAL-PROD-2026-10-05.json` (`scope_pool_prod_path`, all ten rounds): `prod_acc0` 76–79 candidates from 43–46 files strictly above (positions 95–119); `prod_noacc` 57–79 from 24–46 files (positions 76–119). The three score 0.69 in every round; positions are named as stable-sort order inside the 0.69 tie block, not a ranking. |
| D-A2 | §4.3.2 | "not unique. between" → "not unique. Between". |
| D-A3 | §5.7.1; App. D row | New artifact `out/TIEBREAK-EXPOSURE-PROD-SHARED-2026-10-05.json` (sha256 `82e75c08347480ce…`), written by `measurement/sprint-empates-salience-producao.mjs --shared-plus 1` (new opt-in flag: adds `last_accessed_at`, `created_at` and a source-file **class** — `memory/lessons.md` / `memory/entities/*`, never the path — to each tie group's `shared`). Without the flag the output is byte-identical to `out/TIEBREAK-EXPOSURE-PROD-2026-10-05.json` (checked with `cmp`), which was not rewritten. Result: at all five instants every tie group is either one `lessons.md` ingestion (one `created_at`, one `last_accessed_at`, same file) or entity chunks with one importance, pain, access count and `last_accessed_at`. The §5.7.1 sentence cites it; App. D row extended. |
| — | F-5 | One bullet added naming D-A1 to D-A3. |

Parity script `A-rc4/parity-rc4.py`: `EXPECTED_DELTA` extended only with the tokens these
hunks change (`0.69` +3, `04` +1, `05` +3, `1` +2, `10` +4, `119` +2, `2026` +4, `24` +2 new,
`4.3.2` +2, `43` +1, `46` +3, `5.7.1` +1, `57` +2, `76` +2, `79` +3, `95` +1 new, `five` +1,
`two` +1), each traced to the D-A1 sentence, the §5.7.1 citation, the App. D row or the F-5
bullet. Registry: the D-A2 anchor now carries the capital; four anchors added (D-A1, D-A3,
D-A3 App. D row, F-5 bullet).

`claims_check.py::contrafactual_check` rebased (still reads `MANUSCRIPT.md`): it now reads
`out/SALIENCE-COUNTERFACTUAL-PROD-2026-10-05.json` and requires (1) both artifacts present
and `anchor_reproduces_published`; (2) the causal verdict: with access all three in the
top-10, with access zeroed out of the top-10 and not beyond 100 in every variant, round and
population; (3) each chunk's row anchored to its id (importance, pain, accesses, position
1/3/4, tie block 44–46 at 2026-08-29T00:00Z); (4) "149 chunks served in the window"; (5) the
scope-pool numbers of each variant separately. On rc4 it passes; on the pre-fix rc4 it fails
on (5); on the current `MANUSCRIPT.md` it fails 6 times by design until rc4 is promoted.
Mutations caught: position 1 → 2, a tie block 44–46 → 45–47, the population 149 → 150, the
D-A1 mix restored.
