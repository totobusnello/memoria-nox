# APPLY A-rc14 (2026-10-05): findings of REVIEW-A-rc13-2026-10-05.md

Input `A-v1.1-rc13.md` (sha256 `9c3cefc0…f1eb86c`) → output `A-v1.1-rc14.md` (sha256
`73602894…ea803fe`). Gate: `A-rc14/parity-rc14.py --selftest`: PARITY OK, SELFTEST OK (26
mutations: 25 bite on the expected check; the unit mutation is not caught, as in rc10 to rc13, and
the selftest records that as a known limit). The deposit copy
`deposit/paperA-v1.1/MANUSCRIPT-v1.1.md` is byte-identical to rc14 (parity `deposit` check).

The review is saved verbatim in `REVIEW-A-rc13-2026-10-05.md`: the Codex final message (receipt
`adversary-receipt-codex-2026-10-05T132453-63584.txt`, exit 0). IDs: CR1, CR2 = Codex findings
1, 2 (R1..R14 are taken by the rc3 review). V10 = a correction found while applying CR1.

parity-rc14 carries every rc13 check (numbers, footnotes, refs, code, links, headings, tables,
history, qualifiers, the 35 `classes`, `withdrawn`, dashes, addendum, deposit). `history` now
requires the addenda rc5..rc12 to be byte-identical and the rc13 addendum to occur once: the rc13
addendum is part of the same unpublished version, so rc14 corrects two of its items in place and
declares their token deltas like any other edit. `withdrawn` carries the 20 phrasings of rc11 to
rc13 and adds 8 (CR2 ×3, among them the bare "places them first"; CR1 ×5). Qualifier delta
declared: "phase 0" +3 (CR2: Abstract, §1, §9).

| # | verified against | holds? | applied? | note |
|---|---|---|---|---|
| CR1 [medium] §1, §4.3.1, rc13 addendum | `measurement/ciclo-do-lote.py:72-81`: the batch is `SELECT id FROM chunks WHERE created_at >= ? AND created_at < ?`, joined to `brief_log` with `COUNT(DISTINCT b.chunk_id)` per day; no channel, no eligibility. `BATCH-CYCLE-2026-08-29.json` `lotes[0].serie`: `servidos` 108 on 2026-08-22..08-29 except 109 on 08-26; `idade_min` 0.72 (08-22), then 0.92, 1.92, 2.92, 3.92, 4.92, 5.92, 6.92 on 08-23..08-29 (two decimals, `round(mi, 2)`). `A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json` `per_epoch`: `distinct_non_main` 108 and `equals_ref` true on every day 2026-08-23..09-19 (09-02 has no rows), 08-26 included, so the 109th batch chunk of 08-26 is not on the coverage side | yes | yes, Codex's wording with small adaptations | §1 now gives the coverage set from the log (108 ids, 08-23..08-29, the COVERAGE file) and then, "Separately, counting serves across both channels", the batch's 108 a day 08-22..08-29 "except 109 on 2026-08-26" and its minimum served age "reported to two decimal places, rose from 0.92 to 6.92 days in daily increments of 1.00". "the signature of a frozen set" is withdrawn (it attached the coverage-set reading to the cross-channel series). "that batch belongs to the second" → "the coverage-served portion of that batch belongs to the global sub-pool". §4.3.1: the same split, naming `ciclo-do-lote.py` as the query that "selects the batch by creation date and attributes no serve to a channel". §2: already true of the coverage set (Codex agrees); the COVERAGE file is now cited next to it. rc13 addendum DS1 item: rewritten with both measurements and the 109 exception. |
| CR2 [low] Abstract, §1, §9 | `serving-brief.ts:438-451` (phase 0: `pinnedIds` candidates, sorted by score, picked before phase 1), `:453` phase 1 quotas, `:483` `picked.sort((a, b) => scoreOf(b) - scoreOf(a))` over the whole picked list | yes | yes, verbatim core | Abstract: "The high-pain pin selects them in phase 0, before the quota pass, but it protects only items …". §1: "selects them in phase 0, before the quota pass, and they fill the three shared main-pool slots; it protects …". §9: "The high-pain pin, which selects them in phase 0 of every brief, before the quota pass, protects …". The measured necessity for one of the three (116107) is kept in all three. §4.3.1 (rc14 l.878, "F7 is listed last but runs first: it is phase 0"; l.920 ("placed in phase 0 before the quota pass") already describe selection order and stay. rc13 addendum C1 item: one sentence added ("The pin selects them in phase 0, before the quota pass; it does not fix their position in the brief"). Description block aligned the same way. |
| V10 rc13 addendum | `A-recon-evidence/deposited-22181415/MANUSCRIPT.md` (published v1.0): §1 (Introdução) item 1 "calendário", l.228-232, states "cinco dias seguidos com zero itens novos … subindo exatamente +1,00 por dia"; §2 (Sistema sob medição) l.337-338 says "o §4.3.1 mostra cinco dias seguidos em que não houve [candidato elegível]"; v1.0 §4.3.1 (l.698-802) holds no five-day series and no table with 13,96 → 17,96. The table was added to `MANUSCRIPT.md` in commit `bcca3a3` (2026-08-28) and removed in `734e59a`, before the deposit | yes | yes | rc13's addendum said "the table that carried it lived only in the v1.0 text": wrong. It now says v1.0 stated it in §1 and that its §2 pointed to a §4.3.1 that does not show it; the table was in a pre-deposit draft. The same slip is in DRAFT-READBACK's rc13 round ("a tabela da v1.0"), corrected in the rc14 round there. |

## Number deltas (all declared in parity-rc14 with finding IDs)

CR2: 0 +4 (Abstract, §1, §9, rc13 addendum). CR1 §1: 2026 +3, 08 +2, 22 +1, 29 +1, 108 +1,
0.92 +1, 6.92 +1, two +1, 10 +1, 04 +1 (the COVERAGE file name counts its digits; `+1.00` →
`1.00` leaves 1.00 unchanged). CR1 §2: 2026 +1, 10 +1, 04 +1. CR1 §4.3.1: 108 +1, 2026 +2, 08 +2,
23 +1, 29 +1, two +1. CR1 rc13 addendum: 2026 +2, 08 +1, 26 +1, 108 +1, 109 +1, 0.92 +1, 6.92 +1,
10 +1, 04 +1, two +1. V10: 1 +2, 2 +1, 4.3.1 +2, two +1, five +1. Refs (V10): §1 +1, §2 +1, §4.3.1
+2. Code: `A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json` +3 (§1, §2, rc13 addendum),
`ciclo-do-lote.py` +1 (§4.3.1). No heading, table, footnote or link change.

## F-5

"Addendum, rc14 (2026-10-05): a Codex review of rc13." appended after the rc13 addendum, before
Open items; it says that the rc13 addendum was corrected in place and why.

## Package

`build-package.py`: `FONTE` → rc14; `REVIEW-A-rc13-2026-10-05.md` and `APPLY-A-rc14.md` added to
the artefacts, `A-rc14/parity-rc14.py` to the scripts (the rc14 addendum cites all three). The
description block gains a paragraph recording the withdrawn v1.0 statement and aligns its pin
wording. Rebuild results are in `deposit/paperA-v1.1/DRAFT-READBACK.md`.
