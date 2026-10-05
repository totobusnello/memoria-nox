# APPLY A-rc16 (2026-10-05): findings of REVIEW-A-rc15-2026-10-05.md

Input `A-v1.1-rc15.md` (sha256 `61574887…0b125c`) → output `A-v1.1-rc16.md` (sha256
`6980c9e2…918169`). Gate: `A-rc16/parity-rc16.py --selftest`: PARITY OK, SELFTEST OK (31
mutations: 30 bite on the expected check; the unit mutation is not caught, as in rc10 to rc15, and
the selftest records that as a known limit). The deposit copy
`deposit/paperA-v1.1/spare-capacity-narrow-surface-v1.1.md` is byte-identical to rc16 (parity
`deposit` check).

The reviews are saved verbatim in `REVIEW-A-rc15-2026-10-05.md`: the Codex final message (receipt
`adversary-receipt-codex-2026-10-05T142159-29079.txt`, exit 0, 360 s, verdict NO-GO) and a single
Fable pass (remaining defects only, verdict GO). IDs: CX-A..CX-D = Codex findings 1..4; FB-A, FB-B
= Fable findings 1..2; FB-nit = the Fable nit.

parity-rc16 carries every rc15 check (numbers, footnotes, refs, code, links, headings, tables,
history, qualifiers, the 35 `classes`, `withdrawn`, dashes, addendum, deposit). `history` is
stricter than in rc15: rc16 corrects no earlier addendum, so the addenda rc5..rc15 must be
byte-identical. `withdrawn` carries the 55 phrasings of rc11 to rc15 and adds 17 (CX-A ×4, CX-B ×4,
CX-C ×4, CX-D ×2, FB-A ×2, FB-B ×1). One heading (§5.6) and one table row (§6, reconstructed
pool) are declared replacements, both from the CX-A sweep. No qualifier delta.

| # | verified against | holds? | applied? | note |
|---|---|---|---|---|
| CX-A [medium] §1 | rc15 §1 l.182-183 ("The prediction survived the test that could have killed it, as well as an earlier instrument that confirmed it for the wrong reason (§5.6)") against rc15 §5.6 l.1451-1455 ("not a falsifier of Proposition 1 … an unmatched entry would not by itself refute Proposition 1"): the two contradict | yes | yes, adapted | §1: "All 20 entries observed at saturation had an exit in the same stratum. That matching check is an empirical result on these replay states, not a falsifier of Proposition 1 (§5.2, §5.6)." Codex's "The replay exhibited saturation" dropped: the sentence before already gives the saturation band; "at saturation" ties the 20 to `w = 100,000`. §5.2 added because §1 had not yet named Proposition 1. The "earlier instrument" clause goes with the sentence; the episodes it alluded to stay told in §5.6 and §6. **Sweep (class: a check called a falsifier):** §5.6 heading "The test this derivation has to pass" → "A same-stratum matching check on recorded quantities"; §6 table row "The valid test uses only **recorded** quantities (§5.6)" → "The check that replaced it uses only **recorded** quantities and is not a falsifier (§5.6)". Kept, not of the class: §1/Abstract "The prediction is testable and we tested it" / "We tested with an increasing dose" (the dose replay measures saturation; CX4 already narrowed it to the tested family), §4.4 heading "The deductive prediction, and the test" (the same dose replay), §4.3.1 "The test that separates the two hypotheses" (the `freshSlots = 2/0` attribution is a direct measurement), §5.6 "Attempt 1" / "Test 2" labels and "The first attempt to test it" (history of the instrument, not a falsifier claim), §5.7.1 "A prediction of ours died in this test" (the nesting prediction was contradicted by data), §6 row "The valid test is the **cron minute**" (origin signature, not the derivation). The description has no sentence of this class. |
| CX-B [medium] Appendix F-1 | rc15 F-1 l.2372-2374; §4.5 and CX7 of rc15 (utility not measured); no artifact measures utility under any serving policy | yes | yes, Codex wording | "A ratio near 1 would indicate little repetition; whether that policy would improve or worsen agent utility was not measured." The `daily`/3,231 premise goes with the sentence. **Sweep (class: a policy called better/worse/useless/harmful without measured utility):** F-1 "including a correct one" (×2, l.2372 and l.2381) → "whatever its effect on agent utility": it posited a correct concentrating policy, a judgment nothing measured; the argument (the ratio is ≫ 1 for any concentrating policy) is unchanged. Title note: "It is the corpus that is starved, not the coverage" → "It is the corpus that largely goes without an exposure record, not the coverage channel": the note says one sentence later that *starved* is normative and refused by §4.5. Checked and kept: §4.1.1 note "as a reference point and not as a recommended policy. Its effect on agent utility was not measured"; §4.5 "A reader who concludes 'the system is losing valuable information' has gone beyond what was measured"; §9 "What we do not claim … That the 83.78% … is *bad* … not a harm"; §1 struck-through hypothesis ("Why the question matters"); §4.2 "size predicts better" (statistical, not a policy); §4.3.2 "adding competitors never improves anyone's position" (mechanical); §8.2 Bower et al. "can even worsen it" (cited literature). The description has no sentence of this class (its "not a recommended policy" wording is absent; the v1.0 translation says "expected coverage would be 99.98%", a capacity figure). |
| CX-C [medium] §5.7.1 | `measurement/granularidade-do-teto.py:200-213`: `mec = "inalcancabilidade …"` whenever the id that entered in `a` is not in `ids_controle_replay` of `b` and churn is 0; no stratum or cut is read. `CEILING-GRANULARITY-2026-08-28.json` `diagnostico_dos_perdidos`: min→hora lost states `2026-08-27T05:37:05.210Z` (boris, `would_enter` [308284]) and `2026-08-27T07:37:02.488Z` (nox, [308296]). `out/gran3-hora.json`: hour controls hold 308222 and 308240 in both. Closed-window log `p2-serving-CLOSED-WINDOW-2026-08-26T2028-2026-08-27T0900.ndjson`, last serve before each state: 05:37 state: 308284 03:37:06.174Z, 308222 03:37:06.174Z, 308240 03:52:07.329Z (all hour 03); 07:37 state: 308296 05:37:07.078Z, 308222 05:37:05.210Z, 308240 05:52:03.710Z (all hour 05) | yes, contradiction confirmed | yes, adapted | Opener: "The recorded outputs distinguish the following cases:" (Codex). Bullet: "**loss of sensitivity:** under hour resolution, the two states have zero churn, and the items that entered under minute resolution remain outside the control (`out/gran3-hora.json`). These observations do not establish that their strata fell below the selection cut, and the closed-window serving log (raw production data, not deposited) contradicts it in both states: it places the last serve of each of those items in the same hour as that of `308222` and `308240`, which the hour control selects. The classifier (`granularidade-do-teto.py`) labels these states from control membership and churn alone, so it does not distinguish within-stratum competition from deduplication or other selection constraints." The log evidence was added because it is checked here, and flagged as not deposited (the raw serving log is in `MANIFEST-v1.1.json` → `excluidos`). The redundancy bullet stays: 308216 is in the minute control of `2026-08-26T20:52:04.856Z` (`gran3-min.json`). The script and the JSON keep the label "inalcancabilidade … (Proposição 1)" as deposited instruments; they are not edited. |
| CX-D [low] §4.3.2 | `serving-salience.ts:227-234` (`accessCountComponent`: `return clamp01(Math.log1p(access_count) / Math.log(1000))`); repository copy md5 `b908155b…0525` = the v1.0 deposited `serving-salience.ts`, so the line numbers hold for the deposited file | yes | yes, Codex wording + line cite | "`0.20 · clamp01(log1p(access_count)/log(1000))` (`serving-salience.ts:227-234`) over a monotonic counter: it is non-decreasing and capped at 0.20." No other occurrence of the formula in the text or the description. |
| FB-A [low] §4.3.1, status block | Search of the whole repository for `10899`/`10,899`/`10.899`: every artifact hit is the live union of §4.1 (`CLAIM-COVERAGE-2026-08-29.json`, `PARAGRAPH-UNIVERSES-2026-08-30.json`, `POPULATION-LABELS-2026-08-30.json`, `fig0-arquitetura.svg`, the census scripts); `claims_check.py` only counts the literal's occurrences ("+1 em 30/08: o §4.3.1 passou a citar 10.899 para OUTRA grandeza"). No artifact holds the `sessions/%` count | yes | yes, Fable wording | §4.3.1: "(The 10,899 `sessions/%` count, the 20.5 days, the 1,971 and the 10,926 have no preserved artifact.)"; status block: "the 5.6× partial-day reading and the 10,899 `sessions/%` count, the 1,971, 10,926 and 20.5 days of §4.3.1". |
| FB-B [low] Appendix D | `out/` holds six files dated 2026-10-05; the text cites four (`BONUS-VS-STEP`, `SALIENCE-COUNTERFACTUAL-PROD`, `TIEBREAK-EXPOSURE-PROD`, `TIEBREAK-EXPOSURE-PROD-SHARED`), the four packaged in `artefatos-v1.1.zip`; the other two (`C12-*`) belong to Paper B and are listed in `excluidos` | yes | yes, adapted | "(including the four cited here that are dated 2026-10-05)": "the four" alone would be false for the repository folder, which holds six. |
| FB-nit §4.3.1 | `DEVIATIONS-FOR-PAPER.md` l.1257 (§10.11, "Medido em 2026-09-09"): "elegíveis na janela \| **285** = 219 (`source_date` 08/09) + **66 (09/09)**" | yes | yes, with the section | "(2026-09-09; `DEVIATIONS-FOR-PAPER.md` §10.11)". The current `DEVIATIONS-FOR-PAPER.md` is in `artefatos-v1.1.zip`. |

## Number deltas (all declared in parity-rc16 with finding IDs)

CX-A §1: 20 +1, 5.2 +1 (and `1` net 0: Proposition 1 added in §1, removed from the CX-C bullet).
CX-B F-1: 3,231 −1. CX-C §5.7.1: three −1, two +1, 308222 +1, 308240 +1. CX-D: 227 +1, 234 +1,
0.20 +1. FB-A: 10,899 +2. FB-B: three −1, four +1. FB-nit: 10.11 +1. Refs: §5.2 +1, §10.11 +1
(Proposition 1 net 0). Code: `daily` −1 (CX-B); `out/gran3-hora.json`, `308222`, `308240`,
`granularidade-do-teto.py` +1 each (CX-C); old formula −1, new formula +1,
`serving-salience.ts:227-234` +1 (CX-D); `sessions/%` +2 (FB-A); `DEVIATIONS-FOR-PAPER.md` +1
(FB-nit). Headings: §5.6 (CX-A sweep). Tables: the §6 row (CX-A sweep). No footnote or link
change. The CX-B sweep edits carry no token.

## F-5

"Addendum, rc16 (2026-10-05): a Codex and a Fable review of rc15." appended after the rc15
addendum, before Open items. No earlier addendum is touched.

## Package

`build-package.py`: `FONTE` → rc16; `REVIEW-A-rc15-2026-10-05.md` and `APPLY-A-rc16.md` added to
the artefacts, `A-rc16/parity-rc16.py` to the scripts (the rc16 addendum cites all three). The
description block gains the package counts, "rc8 to rc16" and "(rc16, Appendix F-5)"; nothing
else it says is changed by rc16. Rebuild results are in `deposit/paperA-v1.1/DRAFT-READBACK.md`.
