# APPLY B-rc16: review of rc15 applied (2026-10-05)

`B-v2-rc15.md` was copied to `B-v2-rc16.md`, and only rc16 was edited (plus K4 in
`B-registered/teste_aceleracao_v4.py`). rc15 is unchanged (`65b870bb…`). No git, no Zenodo, no
voices, no VPS, no API calls. Source: `REVIEW-B-rc15-2026-10-05.md` (Codex K1–K4, Fable L1–L4
and an optional note). Each finding was verified before it was applied; none was rejected.

## Findings: verification and action

| ID | verified? | how | applied |
|---|---|---|---|
| K1 MEDIUM, dose band | **holds** | PREREG-DRAFT.md l.1–60 read in full; the block is l.18–46: "What does not move, and could not" sits inside the 2026-08-17 design-effect correction and lists the inputs that correction left unchanged (`r̂`, `p̂0`, ICC, `m̄`, `λ₀`, `δ`, the outcome, the dose band, the reach numbers, H1's status); the next sentence is "`cv²` enters the variance, not the rate". The dose-band text elsewhere (l.178–184, 454–480) locks the band's *values* and predicts steps; nowhere does it say the dose cannot change briefs | App. A: item removed (Twelve → ~~Twelve~~ Eleven), the paragraph "The two items where the registration promises *less*…" removed (it rested on this item and the designation), Codex's replacement sentence kept as a note after the list, with one sentence saying what rc15 read and why it was wrong. Swept: Abstract, §1, §3, §5, §8, §9, B.1 and the status header carry no other occurrence (the grep for the quotation, "promises less", "registered among", 11/15/17 hits only App. A; earlier changelog lines are history and stay) |
| K2 MEDIUM, adjudication uncertainty | holds | §4.1.2's own closing paragraph already said "some realized variation enters through between-epoch differences", which contradicts "this variation is in none of them"; "unbiased in expectation and heavy in the tail" has no artifact | reviewer's texts in §4.1.2 (both sentences) and §7; the status header's rc13 clause ("no interval includes") restated, marked as rc16 wording |
| K3 LOW, nesting | holds | PREREG l.308: H1c ⊆ H1b ⊆ H1a is "the nesting that makes the joint reporting work"; with H1b = H1a the inclusions still hold, so the nesting does not cease to exist | reviewer's text in §4.4 |
| K4 LOW, test docstring | holds | l.11 promised 1e-12 before rounding; l.145 compared only `round(a_scipy, 6) == acel` | the unrounded check added (preferred option): `a_v4_cru` recomputed from the same arm-wise delete-one estimates through the script's `aceleracao_estratificada`, `|a_v4_cru − a_scipy| ≤ 1e-12` and `round(a_v4_cru, 6) == acel`, plus the old rounded check. Rerun: exit 0, 10/10, largest difference **1.42×10⁻¹⁶** (Codex measured 1.43e-16). Every field of the rc15 output is unchanged; the new fields are `a_v4_cru`, `dif_cru`, `confere_cru`, `confere_arredondado`, `tolerancia_cru`, `max_dif_cru`. The rc15 bytes were reproduced byte for byte before the edit and are kept as `teste_aceleracao_v4-rc15-bb9c3197.py` and `teste-aceleracao-v4-rc15-ae9e8fe9.json`. App. B's v4 row cites the new sha8 |
| L1 LOW, source of the zero-inclusion claim | holds | `controle_v3_registrado` compares `resumo` (points, `p_rerand`), H2 and every BCa interval/acceleration/z0 under the v3 construction; it says nothing about zero inclusion, which is in checks-rc15 blocks V and R (`exclui_zero` flags) and `RESULTADO-v4.md`'s table | Fable's text in §4 *Uncertainty* (paths written in full, as elsewhere in the body) |
| L2 LOW | = K2 | — | K2's text |
| L3 LOW, rc8 rows | holds | rc15 recomputed the rc8 rows' intervals with v4 (block R; APPLY-rc15 decision 1); points and session-hours are rc8's | Fable's text in B.1 |
| L4 LOW, scaling | holds | `aceleracao_estratificada` docstring and code: `f = (ng − 1)/ng`, `ng` the arm's epoch count | Fable's text in §4 *Uncertainty* ("centred") |
| optional, H2 margin | holds | v4 H2 registered winsorized-time lower bound +0.009913; Monte-Carlo error not measured | §5: "The winsorized-time lower bound, +0.009913 s, clears zero by less than 0.01 s, and its Monte-Carlo error was not measured." (same terms as §4 *Uncertainty*) |
| optional, `gerado_em` | holds | v4 `gerado_em` = 2026-10-06T00:17:25+00:00 | one clause in B.1's first row: the UTC timestamp falls on 2026-10-06, the day after the date in the file name |

## Declared, not dictated by the review

1. **`DEVIATIONS-FOR-PAPER.md` carries the same misreading** (l.20: the band is "entre *what does
   not move, and could not*", "move: 11 / 15 / 17 estados de 350", marked ⬇; l.24–33 build on it).
   Not edited: it is a dated historical log. Same for `AMENDMENT-DRAFT-band-collapse-2026-08-26.md`
   l.634 (retraction 31), which I found during the check.
2. The App. A note keeps Codex's replacement sentence (the replay fact) instead of dropping it, and
   keeps the PREREG quotation verbatim, so the italic-quotation invariant does not move; "monotone,
   saturating in `(4.0; 4.4]`" is not carried (Codex's text omits it).
3. With the band item gone, the "two items where the registration promises less" paragraph has one
   item left (the designation); Codex's fix removes the paragraph and I followed it. The designation
   item itself stays in the list unchanged.
4. **`B-registered/RESULTADO-v4.md` still records the rc15 test bytes** (`bb9c3197…` / `ae9e8fe9…`):
   not edited (the instruction was rc16 plus the test only). The frozen copies make those hashes
   resolvable; rc16's App. B states it.
5. **`B-rc15/parity-rc15.py` no longer passes as written** (2 FAILs, both "RESULTADO-v4.md does not
   record" the new test sha8). rc16's parity carries its v4 integrity with the test pinned to the
   frozen rc15 bytes.

## Artifacts (sha256 prefix)

| file | sha256 |
|---|---|
| `B-registered/teste_aceleracao_v4.py` · `teste-aceleracao-v4.json` (rc16) | `d4d960db…` · `041bd4a9…` |
| `B-registered/teste_aceleracao_v4-rc15-bb9c3197.py` · `teste-aceleracao-v4-rc15-ae9e8fe9.json` (frozen rc15) | `bb9c3197…` · `ae9e8fe9…` |
| `B-v2-rc16.md` | `d6a9259e…` |
| `B-rc16/parity-rc16.py` | `527f9484…` |

Unchanged: v4 artifact `3ed7637e…`, estimator `b3095740…`, `checks-rc15.{py,json}`, `RESULTADO-v4.md`
`d5b3b8b6…`, Figure B1, `B-v2-rc15.md` `65b870bb…`.

## Parity (`python3 B-rc16/parity-rc16.py`: **PASS**)

Imports `B-rc15/parity-rc15.py` (pinned `df4f492b…`), which carries rc14–rc11.

- 17 hunks, all with an ID (ST, L4+L1, K2, K2-S7, K3, H2M, K1, K4, L3+GER, WL, CL); the removal-only
  hunk (the band item) has its own anchor on the removed text.
- Numbers: removed `2`, `4`, `4.4` (the `{2 · 4 · 7.5}` and `(4.0; 4.4]` of the withdrawn item);
  every added token is in rc15, an artifact leaf, or derived (1.4×10⁻¹⁶ and 1e-12 from the test
  output; 0.009913 from v4 at six decimals; 2026-10-06 from `gerado_em`).
- Invariants: italic quotations, citations, footnotes, DOIs, image links unchanged; struck spans +1
  (`~~Twelve~~`, declared); headings (40) unchanged.
- Tail: working list and changelog, minus two declared insertions (items 17 and 24) and the rc16
  block, byte-identical to rc15; changelog 149–160.
- SHAM-JANELA: 10/10 blocks byte-identical.
- Carried locks: rc11–rc13 claims, rc15 sweep/status/presence. **Deviation-count lock** (rc13's
  `appa_count`) replaced: the count word after `~~Thirteen~~ ~~Twelve~~` must be Eleven, must equal
  the unstruck items (11 of 12), and no dose-band item may be in the list; justification K1 recorded
  in the script. rc15's presence lock on C1's sentence replaced by the L4 wording (old wording swept).
- New sweep locks for K1, K2 (four phrasings, status included), K3, L1, L3, L4; presence locks for
  every reviewer text.
- Qualifiers: 102 locked phrases; 3 justified deltas (two rc13 headlines K2 withdraws; the rc13
  App. A count headline, K1). Hedge words declared per ID (6 groups) and summed to the body delta.
- Integrity: rc11/rc12/rc13 carried; rc15's v4 integrity with the frozen test; new test integrity
  (frozen hashes, 10/10 within 1e-12, every unrounded value rounds to `acel`, rc15 fields unchanged,
  tolerance enforced in the source, sha8 and largest difference cited in rc16; v4, checks-rc15 and
  RESULTADO-v4 unchanged).

`--self-test`: **32/32 mutations caught**, unmutated rc16 passes (26 text mutations: each K/L fix
reverted, band item and "promises less" paragraph restored, count word wrong both ways, H2 sentence
dropped, test sha8, status, changelog, old changelog line, SHAM, hedge, three carried claims, italic
quotation, citation, unsourced number, unmapped hunk; 6 integrity: tolerance exceeded, rc15 field
changed, checks-rc15 pin, tolerance not enforced in source, RESULTADO-v4 sha8, frozen copy altered).

## Not done (declared)

- rc16 has not been reviewed.
- The Monte-Carlo error of the H1/H1a upper bounds and of the H2 winsorized-time lower bound was not
  measured.
- None of the rc15 or rc16 artifacts is in the ballast manifest (working list 17).
