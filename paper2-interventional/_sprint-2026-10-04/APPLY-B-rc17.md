# APPLY B-rc17: review of rc16 applied (2026-10-05)

`B-v2-rc16.md` was copied to `B-v2-rc17.md`, and only rc17 was edited (plus one dated note appended
to `B-registered/RESULTADO-v4.md`). rc16 is unchanged (`d6a9259e…`). No git write, no Zenodo, no
voices, no VPS, no API calls (one read-only `git show paper2-v1.12:…/PREREG-DRAFT.md`, byte-identical
to the working-tree `PREREG-DRAFT.md`). Sources: the Codex read of rc16 (receipt
`.remember/adversary-receipt-codex-2026-10-05T221948-70096.txt`, exit 0, NO-GO: M1 MEDIUM, two LOW)
and the Fable read (three LOW), as relayed. Each finding was verified before it was applied; none
was rejected.

## M1 — verdict: **holds**

| claim | primary source | finding |
|---|---|---|
| v1.12 designates at brief composition, recomputed at every brief | PREREG-DRAFT.md l.535 (= tag `paper2-v1.12`), §2: *"Registered: at brief composition, partition eligible failure chunks in the serving snapshot by `sig_primary`; within each group designate the single chunk with the lowest `w_min(severity, age)`"*. AMENDMENT-v1.12.md §0: *"a designação é recomputada a cada brief"*; §5.2-bis: *"hoje a designação **é recomputada a cada brief**"*; §3.3: the 16 ids are *"a união dos conjuntos designados ao longo da série, não um conjunto estável"* | holds |
| v1.12 records the rule as not frozen | AMENDMENT §5 heading *"Defeito aberto: a designação não está validamente congelada"*; §8 puts *"Corrigir a designação"* **after** *"Depositar esta emenda"*; Zenodo v1.12 description: *"The designation rule … is not validly frozen"* | holds |
| fixed 19-item set adopted after v1.12 | v1.12 published **2026-08-26T14:01Z** (`deposit/PLAN-v1.13.md`; metadata `publication_date` 2026-08-26, version 1.12); replacement decided **14:47Z** (`DESIGNATION-SEED-2026-08-26.md`), seed declared 20:07Z, designation completed 20:28Z (commit `3462ff2`, 22:27 +0200) | holds |
| resolution outside the public registration | PROSPECTIVE-ESTIMAND §3 item 1: *"resolvido em 2026-08-26 …; a v1.12 foi depositada **antes** e não foi emendada"*; *"A resolução vive **fora** do registro"*. v1.13 never deposited (`PLAN-v1.13.md`: *"NÃO executado"*). DEVIATIONS front table: *"(v1.12 §5) a designação é defeito aberto → fechada em 26/08 20:28Z"* | holds |
| the registration does not frame the 30-day window as an expiry | PREREG §2 (l.565) names the 7/30-day windows as a constraint on **reach**; the only "expir…" in PREREG is about snapshot counts (l.861) | holds |

Consequence: the 234-epoch horizon is registered; the 20-epoch life belongs to the fixed set (one
shared `created_at`) adopted after v1.12 and not deposited. The mismatch is between the registered
horizon and the subsequently frozen intervention, present before Epoch 1 — not "a property of the
registration" and not "another lock of the same registration". The H1b collision (§4.4) stays
internal: both its locks (`Opportunity` 2026-07-29, `H1b` 2026-08-16) are in the deposited PREREG.

Not claimed (declared): whether the deposited per-brief rule would have escaped the expiry depends on
the registered write path renewing the eligible pool during the trial (PREREG §2 registers writes
"whenever consolidation completes"); the paper never measured that counterfactual, and rc17 does not
assert it.

## Findings: verification and action

| ID | verified? | applied |
|---|---|---|
| M1 | holds (above) | reviewer's texts adapted: Abstract (horizon kept / fixed designation eligible for 20 epochs, adopted after v1.12, not deposited; "present before the trial began"); §1 ("designated memory chunks"; deposited rule, §5.2-bis, open defect; times 14:01Z / 14:47Z / 20:28Z; resolution outside the registration); §1.1 core claim, §3.0.1 caveat ("not a contradiction inside the registration"; window as reach constraint; unlike H1b, only the horizon is registered), §7, §8.5 (reviewer's "internal contradiction … and a mismatch …"), §9 (reviewer's "One contradiction was internal…; a second incompatibility arose…"), Appendix A designation item. Every "the registration outlived its intervention" in the body swept |
| Codex LOW, "every earlier version" | holds: H1 rejected in v1/v2/rc3–rc9 (MANUSCRIPT-B.md and rc2–rc6: "`H1` rejects under both"; rc7 0.0127, rc8 0.0133, rc9 0.0302) and in none from rc10 | "versions up to rc9" in the Abstract (**two** places: the reviewer named one; the second, "did reject in every earlier version of this analysis", was caught by the sweep) and §9 |
| Codex LOW, B.1 | holds: v4 differs from v3 in the accelerations too (RESULTADO-v4: "acceleration only") | first row: "the BCa intervals, accelerations and adjusted quantiles" |
| Fable LOW, DEVIATIONS | holds: the band row of the front table still reads *"what does not move, and could not"* → "move", marked ⬇ | App. A note: still carries the withdrawn reading; dated, append-only, not edited |
| Fable LOW, nesting attribution | **the attribution was right**: PREREG l.308 lies in `## 1. Study Information` (l.293), inside the 2026-08-16 H1b lock | made precise: "the H1b lock of 2026-08-16 in §1 of the pre-registration (PREREG l.308)" |
| Fable LOW, RESULTADO-v4 test hashes | holds: its table records the rc15 test (`bb9c3197…`/`ae9e8fe9…`) with no pointer to rc16's | dated note appended to `RESULTADO-v4.md` (names `d4d960db…`/`041bd4a9…`, 1.4×10⁻¹⁶); nothing above it edited, so every recorded hash still resolves; the pre-note bytes kept as `RESULTADO-v4-rc16-d5b3b8b6.md`; App. B says so |

## Title — flagged for the author, NOT changed

*"A registration that outlived its intervention"* no longer holds in its strong reading: the
intervention that expired is not the registration's own (the deposited rule recomputes per brief; the
fixed set came after v1.12 and was not deposited). It survives only as "the registered horizon
outlived the intervention the trial ran" — the wording rc17 uses in the body. Options for the author,
e.g. *"A registered horizon that outlived its intervention: …"* or *"A registration that outlived
the intervention it ran: …"*. The current title was set in rc4 (author decisions of 2026-10-05); changing it would also
move any deposit metadata that carries it.

## Declared, not dictated by the review

1. `B-rc16/parity-rc16.py` now fails 1 check as written (`res4 changed`, the d5b3b8b6 pin), as rc16's
   did for rc15. rc17's parity carries rc16's integrity reading `RESULTADO-v4.md` as its frozen rc16
   bytes and requires the live file to be exactly those bytes plus the note.
2. Observed, not changed: §1 says the designation declaration preceded round 31657512 by "1 056 s";
   `DESIGNATION-SEED-2026-08-26.md` records 1.053 s (T_declare 20:07:27Z; the commit is 20:07:24Z,
   which gives 1 056). The paper qualifies it "according to the recorded timestamps"; the author may
   want to name which timestamp.

## Artifacts (sha256 prefix)

| file | sha256 |
|---|---|
| `B-v2-rc17.md` | `243801dd…` |
| `B-rc17/parity-rc17.py` | `9d430bd8…` |
| `B-registered/RESULTADO-v4.md` (rc17, with note) | `9151c61f…` |
| `B-registered/RESULTADO-v4-rc16-d5b3b8b6.md` (frozen pre-note bytes) | `d5b3b8b6…` |

Unchanged: `B-v2-rc16.md` `d6a9259e…`, v4 `3ed7637e…`, checks-rc15, the acceleration test
(`d4d960db…`/`041bd4a9…`), Figure B1, every SHAM-JANELA block.

## Parity (`python3 B-rc17/parity-rc17.py`: **PASS**)

Imports `B-rc16/parity-rc16.py` (pinned `527f9484…`), which carries rc15–rc11; pins rc16 at `d6a9259e…`.

- 21 hunks, all with an ID (ST, M1, LV, LB1, FD, FN, FR, WL, CL).
- Numbers: none removed; added tokens are in rc16, or derived from their source file read in the
  script (14:01Z from `PLAN-v1.13.md`, 14:47Z from `DESIGNATION-SEED-2026-08-26.md`).
- Invariants: italic quotations, citations, footnotes, DOIs, image links, struck spans unchanged;
  headings (40) unchanged.
- Tail: working list + changelog minus one declared insertion (item 24) and the rc17 block
  byte-identical to rc16; changelog 149–163; the block records the title flag.
- SHAM-JANELA: 10/10 blocks byte-identical.
- Carried locks: rc13 claims (with rc16's deviation count, 11), rc15 + rc16 sweeps, status marks,
  presence locks — none replaced. New sweep: "property of the registration", "the registration
  outlived its intervention" (title exempt by construction: "A registration that…"), "each
  contradicted another lock of the same registration", "inconsistencies in its own registration",
  "twice here, at two scales", "same shape as the H1b collision … larger object", "a fixed set of
  designated items", "in every earlier version", B.1 without accelerations. 15 presence locks.
- Qualifiers: 102 locked phrases; 1 justified delta ("not deposited" +6, M1). Hedge words declared
  per ID (ST, M1, LV, FD, FR) and summed to the body delta.
- Integrity: rc16's carried checks; RESULTADO-v4 = frozen bytes + note exactly; note names the live
  test sha8s and 1.4×10⁻¹⁶; **source block S** re-verifies the M1 facts from the primary files
  (v1.12 time, 14:47Z, "recomputada a cada brief" ×2, §5 heading, "fora do registro", PREREG l.535
  and l.308 in §1, no designation expiry in PREREG, DEVIATIONS band row ⬇).

`--self-test`: **39/39 mutations caught**, unmutated rc17 passes (29 text: each M1 sentence restored,
times dropped, each LV occurrence, B.1, the three Fable fixes, status, title flag, changelog,
old changelog line, SHAM, hedge, three carried claims, italic quotation, citation, unsourced number,
unmapped hunk; 10 integrity/source: RESULTADO edited above the note, note missing/altered, frozen copy
altered, frozen rc15 test altered, v1.12 time, amendment wording, prospective estimand wording,
PREREG §1 heading, DEVIATIONS arrow).

## Not done (declared)

- rc17 has not been reviewed.
- The title (above).
- None of the rc15–rc17 artifacts is in the ballast manifest (working list 17).

## Author decision (Toto, 2026-10-05 ~22:45 BRT): title
Title changed to *"A registered horizon that outlived its intervention: a pre-registered randomized trial of
memory dosing in a production agent fleet"* (line 1 only). Parity rc17 re-run after this edit.
