# APPLY — `B-v2-rc3.md` → `B-v2-rc4.md` (Paper B, 2026-10-05)

Sources: the author's five decisions of 2026-10-05 (final, not reopened);
`B-sham-v2/JANELA-LANCAMENTO.md` (launch record of the whole-window sham, including the
relaunch section); `SPEC-ANALISE-2026-09-10.md` §3, §7, §9; `REVIEW-B-rc2-evidence/power-*.json`
and `out/H1C-POWER-*-2026-09-10.json` read field by field; the new C12 census.
`B-v2-rc3.md` is unchanged (1 879 lines, 141 027 bytes). rc4: 1 965 lines, 148 941 bytes.
No git command, no deposit, no contact, no adversarial voice.

## Decisions applied

| # | decision | where in rc4 | check |
|---|---|---|---|
| 1 | Title → *"A registration that outlived its intervention: a pre-registered randomized trial of memory dosing in a production agent fleet"* | title line; abstract ¶3 ("The registration outlived its intervention … the under-powering follows from that") and last ¶ ("a trial whose registration outlived its intervention and which is under-powered as a result"); §1.1 "the core claim"; §7 Power; §9 opening; changelog 59 | `grep` for "under-powered by construction": 0 left outside the changelog quote. "Under-powered" kept wherever it is a technical statement (§3.0.1 caveat, §4.1.1, §4.2, §4.4, §8.3, §9 last ¶) |
| 2 | Power: the spec's fractional counting is the primary statement; whole-epoch 11T/9C is a sensitivity where the verdict flips | abstract ¶4; §1 table (H1c cell); §1.1 first list; §4.1.1 last ¶ rewritten; §7 Power; §8.4; §9 | fractional over 19 served epochs: `H1C-POWER-FRACIONARIA` `n_efetivo_realizado` 84.8, not detectable; with `09-02` as a full control epoch: `power-10.9375T-8.23375C` 91.49 (margin 4.1%); whole 11T/8C: 90.2 (`H1C-POWER-REALIZADO`, reproduced); whole 11T/9C: 96.41 > 95.26, `detectavel_no_limite_p1_igual_zero: true`, MDE 0.996 |
| 3 | "projection-robust" qualified | §1.1 caveat (two sentences added); §9 ("projection-robust under the spec's cuts") | the spec's extremes (`SPEC-ANALISE` §9) are 11T/8C and 11T/7C; neither is 11T/9C |
| 4 | Sham stays (`w = 4`, `p = 1/21`); one sentence on the whole-window run | STATUS block; §4.0.1c first declared limit; also working list 9 ("configured and not run" was stale → "running as item 15"), new item 15, item 8 now blocked by 10 and 15; B.1 row | `JANELA-LANCAMENTO.md` §"Relançamento 2026-10-05T09:39:53Z": 11,812 states (`cal/ts-janela-reconstruivel.txt`), 18 epochs, `09-01` excluded (no hash proof), 53 states excluded (cut impossible, all agent `nox`). No result is reported: the job is not CONCLUIDO |
| 5 | C12: compute per-arm ties if possible | computed; §4 tie paragraph, §7 "Tie rule", §6 items 3 and 6, App B † row, B.1 row | see below |

Wording beyond the letter of the decisions, and why:

- §4.1.1 now says that §7 of the spec forbids rounding a partial epoch to a whole one
  ("Arredondar parcial para inteiro. Nem para dentro, nem para fora.") and that the spec
  computed the 9-control case itself (`n_ef = 96,4`, §3 item 3) and set it aside because
  `09-02` delivered 0 briefs. Both are the spec's own text and are the reason the fractional
  counting governs; the ITT still counts `09-02` as a cluster (§3), so the flip is reported.
- §1.1 first list gains one bullet: the designation's expiry
  (`out/expiracao-designados-2026-09-09.json`), because the new core claim rests on it and
  it is outcome-independent. The artifact was already in Appendix B.

## C12: ties per arm in the four-vote set (computed)

Script `measurement/sprint-c12-empates-por-braco.py`; output
`out/C12-EMPATES-POR-BRACO-2026-10-05.json`. Composition only: `carregar_verdicts`,
`carregar_episodios`, `TAU` from `pilot_replay.py`; `estimador_itt.py` run unchanged on the
three-family file and on the four-vote file (primary + DeepSeek, DEVIATIONS §10.31).
Inputs: the two verdict files (canonical location named in `MANIFESTO-LASTRO-P2.json`; a
byte-identical copy is in the backup `-COPIA/verdicts/`), `episodios-ensaio-20260921.jsonl`
and `estrato-b-ids-20260921.txt` from the `paper2-ensaio-2026-09-21` backup,
`ASSIGNMENT-SERVING.json` from the repo.

Controls (the script aborts on 1–3):

1. sha256 of every input equals `MANIFESTO-LASTRO-P2.json` (estrato-b-ids is not in it; 2 covers it);
2. `estimador_itt.py` on the primary file reproduces `ITT-2026-09-21.json` per arm
   (1 103.75 / 76.84 / 2 unknown / 11 epochs; 1 191.14 / 106.67 / 5 / 9);
3. DEVIATIONS §10.31(6) "ganhos 20 · perdas 28" reproduced. **What they are, measured:**
   gains = 20 episodes the fourth family brings to the floor of three substantive verdicts;
   losses = 28 episodes it brings to an exact 2-2 tie. My first reading (losses = label flips)
   gave 13 / 3 and the control aborted; that is how the definitions were pinned;
4. per-arm change in `repeats` (0.00 treatment, +1.00 control) equals rescued failures minus
   label-changing ties among opportunities;
5. resolving the 3 label-changing ties as failure moves no signature's first failure.

Result:

| | treatment | control | outside window | total |
|---|---:|---:|---:|---:|
| exact ties | 10 | 11 | 7 | 28 |
| of which H1c opportunities | 4 (HT 27.78) | 7 (HT 36.73) | — | 11 |
| tied opportunities that were failures under 3 families | 0 | 0 | — | 0 |
| ties that change a label (failure → `not_failure`) | 1 | 1 | 1 | 3 |

So the tie rule changes no repeated failure in either arm of H1c and does not touch
condition (i). For the record only (not in the paper): the four-vote H1c point estimates are
0.0675 / 0.0883, difference −0.0208 against −0.0199 (from rescues and condition-(i) shifts,
not from ties; no interval computed).

**A correction this produced (flag for the author).** rc3 §6 item 3 (from C11) said "Ties
do change the final label under the tie rule; those are the 28 losses of item 6." Measured:
only 3 of the 28 change the label; 25 were already `not_failure` with three families. rc4
strikes the sentence and states the counts, and §6 item 6 now defines gains and losses. This
is outside the five decisions; it is a factual fix to a sentence about the very ties C12
counts.

## Parity

`B-rc4/parity-rc4.py` (adapted from `B-rc3/parity-rc3.py`: old = rc3, new = rc4; same five
checks): **PASS**. 35 numeric tokens change count; each is listed with its exact signed
change and a reason (TITLE, POWER, SHAM, C12, B1, CHANGELOG); none disappears. Headings: 40,
identical except the one allowed rename (the title). Internal § refs: 7 dangling in both
(pre-existing), 0 new. Citation keys unchanged; no footnotes; no host, IP or personal path
added (the one `/root/` match is pre-existing, Appendix B caveat). `--self-test`: 3 mutations
caught, unmutated rc4 passes.

## Style pass (avoid-ai-writing, changed sentences only)

Detect on the added lines (technical register): 0 em dashes added; no Tier 1 vocabulary,
hedge stacks or reveal constructions. Fixed: a double "so … so" chain in the §4 tie
paragraph (split into two sentences); one bold added in §4.1.1 ("the power statement of this
paper") removed. Bold labels and struck-through text follow the manuscript's convention.

## Open for the author

1. The §6 item 3 correction above (C11 text was wrong about how many ties change a label).
2. Whole-window sham: ETA of `job-janela2` ≈ 2026-10-07T03:00Z per the launch record; the
   result goes into §4.0.1c, §7, B.1 and working list 15 before deposit.
3. rc4 has not been reviewed adversarially (by instruction).

## Fixes after the independent check (2026-10-05, `CHECK-A-rc4-B-rc4.md`)

rc4 edited in place (it is not deposited). After: sha256 `32680551e055d620…`, 1,991 lines,
152,035 bytes. Parity rerun: `PARITY: PASS` (43 tokens changed, 43 justified; 1 heading
renamed; dangling § refs 7 → 7, 0 new); `--self-test`: 3 mutations caught, unmutated rc4
passes.

| defect | where | what changed |
|---|---|---|
| D-B1 | §4 tie paragraph; §7 "Tie rule"; App. B; B.1; changelog 67 | "counted in rc4 it is nil for H1c" struck. Now: no H1c label changes relative to the three-family majority, but against the opposite resolution the rule holds 4 treatment and 7 control tied opportunities (HT 27.78 and 36.73) at `not_failure`. **Measured**, not approximated: `measurement/sprint-c12-empates-por-braco.py --empates-como-failure-out` (new opt-in flag; appends one synthetic `failure` vote at level TAU per tied episode, so the imported `carregar_verdicts` resolves n/2 of n as n/2+1 of n+1; aborts if a tie does not flip or any non-tied label moves) → `out/C12-EMPATES-COMO-FAILURE-2026-10-05.json` (sha256 `1307de2bc8d6a756…`). Four-vote H1c point difference: −0.020843 under the paper's rule, **−0.026571** with all 28 ties as `failure` (treatment 104.62 / 1,138.47 = 0.091890; control 144.40 / 1,218.92 = 0.118461). Opportunities do not change (no condition-(i) feedback), and the first-order value is −0.026566. Without the flag the script's `--out` is byte-identical to `out/C12-EMPATES-POR-BRACO-2026-10-05.json` (checked with `cmp`). |
| D-B2 | STATUS; §4.0.1c; working list 9 and 15; B.1; changelog 68 | All say `job-janela2`, 11,812 states (11,865 − 53; `09-01` excluded), relaunched 2026-10-05T09:39:53Z, expected about 2026-10-07T03:00Z (`B-sham-v2/JANELA-LANCAMENTO.md`, "Relançamento"). Item 9's "11,865 states … about 36 h" struck; §4.0.1c keeps 11,865 / 36 h only as the estimate that motivated the `w = 4` set ("as estimated then"). |
| D-B3 | `B-rc4/parity-rc4.py` | Labels rc2/rc3 → rc3/rc4; variables `RC2`/`RC3` → `OLD`/`NEW` (a local `new` that shadowed the text was renamed `added`); the leftover rc2→rc3 comment above `JUSTIFIED` removed; self-test prints "unmutated rc4". |

`JUSTIFIED` extended: new `0.0208` +4, `0.0266` +5, `11,865` +4, `2026-10-05T09:39:53Z` +5,
`2026-10-07T03:00Z` +5, `27.78` +4, `36` +2, `36.73` +4; adjusted `11,812` +5→+7, `15` +4→+5,
`2026-10-05` +9→+13, `28` +10→+11, `4` +4→+8, `53` +4→+6, `7` +7→+10, `9` +7→+9. Each reason
names the CHECK defect and the places.

Not done: `measurement/auditoria-da-cadeia.py` lists the two new `out/` artifacts as orphans
(measured, not read by a guard), the same class as their siblings `C12-EMPATES-POR-BRACO` and
`TIEBREAK-EXPOSURE-PROD`, which were already listed. Declaring them is integration work.
