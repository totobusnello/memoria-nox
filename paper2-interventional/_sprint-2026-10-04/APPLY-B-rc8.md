# APPLY B-rc8: the registered analysis reported (2026-10-05)

Manuscript: `B-v2-rc7.md` copied to `B-v2-rc8.md`; only rc8 was edited. No git (read-only
`git log` / `git show` only, to date commits), no Zenodo, no voices, no VPS. Not touched:
`measurement/estimador_itt_registrado.py`, `out/ITT-REGISTRADO-2026-10-05.json`,
`B-registered/`, `estimador_itt.py`, `rerandomizacao.py`, the rc4 files `out/C12-EMPATES-*.json`
and the rc4 figure `figures/figB1-h1a-inversao.*`.

Inputs: `out/ITT-REGISTRADO-2026-10-05.json` (sha256 `72642ad9…`), `B-registered/RESULTADO.md`,
`APPLY-B-rc7.md` (integration notes 1-4 and observations 1-3), `B-rc7/reanalise-list.txt`
(R01-R108), `REVIEW-B-rc6-2026-10-05.md` (author decisions: H1c primary with the switch
declared; the registered analysis reported, the rc7 analysis a sensitivity).

## New evidence

`B-rc8/checks-rc8.py` -> `B-rc8/checks-rc8.json` (+ `out/C12-EMPATES-REGISTRADO-2026-10-05.json`).
Read-only on the trial ballast (`~/Backups/paper2-ensaio-2026-09-21/`, `~/.paper2-verdicts/`);
every input's sha256 is checked against the provenance recorded in ITT-REGISTRADO; offline.

| block | what | result |
|---|---|---|
| G | guards | the leg builder reproduces `pernas.atual` and `pernas.registrado` of ITT-REGISTRADO exactly (points, percentile and BCa intervals, per-arm totals) and the points and per-arm hours of the two locked sensitivity legs (`ITT-SENSIB-PRECOMPROMETIDA.json`, `ITT-2026-09-21.json`) |
| A | registered analysis on the sensitivity legs (fresh rng 20260921 per leg, as `correr_perna`) | pre-committed (09-01/03/20 removed, 10T/6C): H1c −0.0187 [−0.0596; +0.0094]; H1a −138.91 [−254.18; −28.82] **excludes zero**; H1 −13.93 [−22.98; −5.70]. Post-hoc (09-14 removed): H1c −0.0159 [−0.0485; +0.0098]; H1a −78.27 [−146.22; +1.95] contains zero; H1 −9.03 [−14.68; −1.89]. Hours/epoch, 09-14 = 57% of 12.56 h, other 18 epochs 0.25–0.97 h; H1 reductions 69.8% / 44.6%; ratios 22.2/14.2, 15.3/9.8, 10.2/6.5; volumes; identity error ≤ 6.0e-6 |
| C | C12 ties, registered window + 19 set (new file) | 28 ties: 10 T, 10 C, 7 outside the dates, 1 control tie in 09-03 before its exposure window, 0 in 09-02; tied opportunities 4 / 7 (27.78 / 36.725), unchanged; four-vote H1c −0.012134 (paper's rule) → −0.021067 (ties as failure); 0 ties possible/counted in the substitution panel. Guard: reproduces the rc4 counts and the −0.020843 / −0.026571 points under the current window |
| D | stopping rule, PROSPECTIVE-ESTIMAND §3-bis | Epoch 1 (09-01, T w=4), the planning script's rule as written over the locked corpus, the 7 promoted signatures of CONCENTRATION: **45 / 139 = 32.4%** (Wilson [25.2%; 40.5%]) < 36.7% → **met, not executed**. Other readings: active phase 34/101 = 33.7% (below); post-washout 30/75 = 40.0% (above); trial's weighted opportunity rule 54.5% (above); 19 designated groups 92.1% / 89.4% (not the threshold's quantity) |
| E | declared rule (ASSIGN-SEED, via `assignment_derive.atribuir`) vs `assign_arms.py`, round 31774052 | both reproduce their published outputs (`sha256_da_atribuicao` 2426d13d…; `ASSIGNMENT.json`, coherent with `ASSIGNMENT-SERVING.json`). **Different**: binary arm differs in 130/234 epochs and in **11/20 realized** (09-01, 05, 06, 07, 08, 09, 11, 13, 17, 19, 20); declared rule would give 10C/10T vs 9C/11T. Commit log: declared assignment committed 21:33:46Z (686bea6), replaced 21:56:42Z (3e1c259), round emitted 21:32:04Z → **deviation**, declared in §1 / App. A |

Figure B1: `measurement/sprint-figB-h1a-inversao-registrado.py` (new; the rc4 script and
figure untouched) -> `figures/figB1-h1a-inversao-registrado.{svg,png,run.json}`. Aborts unless
panel (a) reproduces the registered session-hours (12.56 / 4.33) and every epoch of block A,
and panel (b) matches ITT-REGISTRADO and a `checks-rc8.json` produced from the same
ITT-REGISTRADO (sha256). **Regenerated** (not declared as current); headline matches caption.

## The 108 REANALISE blocks (85 value, 23 rewrite) -> registered analysis

Every block was replaced; where the sentence reports both, the rc7 value stays as the
sensitivity. Per-block numeric deltas with their source: `python3 B-rc8/parity-rc8.py --report`.

| blocks | location | registered value(s) written (sensitivity kept) |
|---|---|---|
| R01-R02 | Abstract, switch | H1 `p = 0.0133`; Holm: H1a 0.0241 → 0.1205 (m=5) / 0.0964 (m=4), no rejection |
| R03, R10 | Abstract | H1c `p = 0.434` |
| R04-R07 | Abstract | 69.8% / 44.6%; 22.2; 15.3; 6.5 |
| R08 (rw) | Abstract | 19 = registered set; whole-epoch 90.2 at 11T/8C same verdict; flip only at 20 (96.41); −0.0121 (0.0675 / 0.0796) BCa [−0.0445; +0.0125]; sensitivity −0.0199 [−0.0560; +0.0086], 0.1603 |
| R09, R11 | Abstract | 19 clusters, 11T/8C, BCa; 15% |
| R12-R14 (rw) | §1 | 0.434; 0.0133; Holm statement with H2 (0.831 / 0.684), m=5/m=4 thresholds, "0.0241 is not a rejection"; sensitivity verdicts |
| R15 (rw) | §1.1 | holds at 11T/8C under whole-epoch; flips only at 11T/9C |
| R16-R19 (1 value, 3 rw) | §3 | ITT 19 (registered), 20 as sensitivity row; why `09-02` is excluded and what it costs; deviation resolved |
| R20 (rw) | §3.0.1 | expiry cut (33 episodes, 5 / 22.835 opportunities, 2 repeats, 0.6235 → 0.5154 h) and offsets as exposure windows (09-01 10:37:01.943Z, 09-03 17:23:39.777Z — an interpretation), 0.543→0.406, 0.457→0.246 |
| R21 (rw) | §4 adjudication | substitution: +20 adjudicated (13 failures), 1 179 / 16 unknown; 0 changed; unknown share 1.02% (1.34%) |
| R22 | §4 ties | −0.0121 → −0.0211 (registered); −0.0208 → −0.0266 kept as sensitivity |
| R23 (rw) | §4 uncertainty | BCa, jackknife over 19 (not 234), no fallback, α₁ 0.0017 / 0.0009 → 18th / 9th smallest |
| R24-R31 | §4.0.2 | table: 0.434; 0.0241 (Holm 0.1205 / 0.0964; sens. 0.43 / 0.34); 0.0133; observed −0.0162 vs −0.0121; 69.8%, 22.2, 15.3 |
| R32-R43 | §4.1 | locked 0.0675 / 0.0796 / −0.0121 [−0.0445; +0.0125]; pre-committed 0.0697 / 0.0884 / −0.0187 [−0.0596; +0.0094]; post-hoc −0.0159 [−0.0485; +0.0098]; three sensitivity rows; "all three legs agree" in both analyses |
| R44-R50 | §4.1.1 | 0.0796 / −0.0796 / 0.0351; [−0.0445; +0.0125], 11 and 8 BCa; 0.434; 15% |
| R51-R53 (rw) | §4.1.1 power | 84.8 = registered set; 91.49 / 4.1% and 96.41 / 0.996 / 99.6% moved to the sensitivity allocation |
| R54 | §4.1.2 | 0.434 |
| R55-R62 | §4.2 table | 19 epochs; 12.56/4.33, 12.16/3.57, 5.43/4.33; H1a −163.52 [−282.29; −61.12], −138.91 [−254.18; −28.82], −78.27 [−146.22; +1.95]; sensitivity row; 0.0241 / 0.1205 |
| R63-R65 | §4.2 | other 18 epochs 0.25–0.97 h; 57%; 19 clusters |
| R66-R70 | Fig B1 caption | registered figure, values as above, 0.0241 / Holm |
| R71-R77 | §4.3 | H1 −14.12 [−22.15; −7.04], −13.93 [−22.98; −5.70], −9.03 [−14.68; −1.89]; 0.543 / 0.541; −9.03; 137.7 / 10.96 vs 95.5 / 6.08; 19 clusters |
| R78-R84 | §4.3 | 69.8% (6.117 / 20.236), 44.6%; 22.2 / 14.2; 15.3 / 9.8; 10.2 / 6.5; 8 and 11 |
| R85-R86 (rw) | §5 | H2 reported (three declared choices, table, no rejection); H3 not computable (reason) |
| R87 (rw) | §6 item 7 | the registered analysis implements the rule (20 / 13 / 16) |
| R88 (rw) | §7 | same verdict at 11T/8C; borderline only at the sensitivity allocation |
| R89-R90 | §7 | −0.0121 → −0.0211; 103.5 / 137.7 (100.3 / 132.3) |
| R91-R92 | §8.3 | 19 periods (20 realized); 19 clusters 11/8 (20, 11/9) |
| R93 (rw) | §8.4 | registered 19 under both countings; flip at 20 |
| R94 (rw) | §9 | same, with 96.41 / 99.6% at the sensitivity allocation |
| R95-R97 | Appendix A | 0.0133; Holm with H1a 0.0241 / 0.1205; the four departures (now resolved) + two interpretations |
| R98-R108 | B.1 | rows rewritten as registered / sensitivity; new rows for ITT-REGISTRADO, checks-rc8 A/D/E, C12-REGISTRADO, Figure B1 |

## Integration notes of APPLY-B-rc7, closed

1. §4.0.2 reject/agree cells re-verified against the registered p-values and the Holm
   family: H1c no / agree; **H1a no (Holm) / disagree** with the BCa interval; H1 yes /
   agree. Heading renamed (*"The registered test against the bootstrap, and the Holm rule
   on H1a"*) because the disagreement on H1a is now with the multiplicity rule, not the raw p.
2. C12 ties recounted under the expiry cut (block C; new artifact). The rc4 files unchanged.
3. Figure B1 regenerated from the registered artifact (new files; old kept as the record of
   the sensitivity analysis).
4. Headings: §4.1 ("null and not detectable at 80% power") holds under the registered
   analysis (p 0.434; 84.8 and 90.2 both below 95.26). §4.2 ("excludes zero only on the
   locked leg") **does not hold** under BCa (the pre-committed leg excludes zero too):
   renamed to *"H1a: excludes zero on a denominator dominated by one epoch, is not rejected,
   and bears no weight"*, with the old sentences struck and corrected.

## Observations of APPLY-B-rc7, resolved

1. Stopping rule: computed (block D) and reported in §3.0 (struck sentence "That calendar
   decision is the whole of the stopping rule"), abstract, §1.1, §7, §9, Appendix A, §8.2.
2. Commit `3e1c259`: both rules run (block E); **different** → declared as a deviation in
   §1 (new paragraph), abstract, §1.1, §7, §9, Appendix A, §8.2.
3. `ITT-PRELIMINAR.json` still not in the manifest: working list 17, now with every rc8
   artifact; Appendix B caveat states it.

## Sweep (outside SHAM-JANELA)

Abstract (analysis paragraph; H1a legs; stopping/assignment paragraph), §1 (H1a row; H2/H3
sentence), §1.1 (two checkable bullets; trust), §3 (09-01 offset), §3.0, §4 (estimator,
what moves what, adjudication, ties), §4.0.1a (9 903 patterns at 19), §4.0.2, §4.1 (direction
note), §4.2 (heading, correction, take-away), §4.3 (identity on registered cells; criterion),
§5 (H2 result; secondary model row), §7 (tie rule; two new threats), §8.2 (table row), §8.3
(BCa wording), §8.4, §9, Appendix A (nine items), Appendix B (five new rows, ballast caveat),
B.1, working list (8, 11, 17, 18, 20), changelog 97-107, status header.

Checked unchanged on purpose: "between-epoch volume spanning 73 to 234 episodes" (§4.3) is
the post-washout episode count per epoch, and it is 73–234 under both windows (recomputed).

## Parity

`python3 B-rc8/parity-rc8.py` -> **PASS**: 110 hunks, all with an ID; 108/108 REANALISE blocks
inside a hunk; 520 numeric tokens added, each justified (rc7 value, artifact read at run time,
or a literal with its source); headline strings formatted from the artifacts present; no
H1a-as-rejection sentence; `1 195` never called adjudicated; headings: 2 declared renames;
citations unchanged; SHAM-JANELA 10 blocks byte-identical; 0 REANALISE markers; 4 quotes
added, each verbatim in rc7 or PROSPECTIVE-ESTIMAND; added code spans resolve on disk.
`--self-test`: every mutation caught, unmutated PASS. `--report`: per-ID numeric deltas.

## Not done (open)

- Ballast: the rc7/rc8 artifacts are not in `MANIFESTO-LASTRO-P2.json` (working list 17).
- No voice reviewed rc8 (working list 20).
- The whole-window sham (SHAM-JANELA blocks) is untouched and still running (item 15).
