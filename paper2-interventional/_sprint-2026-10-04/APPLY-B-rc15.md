# APPLY B-rc15: review of rc14 applied (2026-10-05)

`B-v2-rc14.md` was copied to `B-v2-rc15.md`, and only rc15 was edited. rc14 is unchanged.
No git, no Zenodo, no voices, no VPS, no API calls. Source:
`REVIEW-B-rc14-2026-10-05.md` (Codex C1–C6, Fable F1–F2). Each finding was verified before
it was applied; none was rejected.

## Findings: verification and action

| ID | verified? | how | applied |
|---|---|---|---|
| C1 MEDIUM, BCa acceleration | **holds** | v3 `bootstrap()` pools the 19 delete-one values (11 T + 8 C) and centres them at one mean; the draws resample the arms independently. SciPy 1.18.0 `_bca_interval` uses per-sample centring and `(n−1)/n` scaling. The review's five corrected intervals reproduced **to every printed digit** | estimator v4 (`--aceleracao`, default `estratificada`; `uma_amostra` = v3); `out/ITT-REGISTRADO-v4-2026-10-05.json`; test (hand case in exact fractions + SciPy on the toy and on 10 real estimators); every reported BCa interval switched; §4 *Uncertainty* carries the reviewer's sentence and a dated correction; App. A, B, B.1; Figure B1 regenerated |
| C2 MEDIUM, census attempt | holds | `GATE-RULES-PREDECLARED.md` states 0.99^150 ≈ 22% without the independence condition; §7 says the record cannot separate non-determinism from a changed model, which "instrument change" contradicts; 1 − 0.99^150 = 0.7785 | reviewer's text in §4 (independence, evidence not proof, criteria fail) and §7; "instrument change" → "whether the instrument's response distribution changed is unresolved" (kept the 4 756 / 1 195); B.1 noise row; changelog item 144 annotated (the item itself is not rewritten; a dated note points to item 152) |
| C3 MEDIUM, what the bootstrap resamples | holds | `bootstrap()` draws epochs within fixed arms; the assignment is redrawn only by `rerand()` | reviewer's two sentences in §4.1.2; sweep: the abstract's "may be too narrow … neither re-draws … nor re-adjudicates" and §4.1.1's "makes the interval **too narrow**" restated without a direction; "may under-cover" (few clusters) and "may be optimistic" kept, both hedged and tied to §4.1.1 |
| C4 LOW, own stratum | holds | an interval or test is not reported; "not estimable" is a stronger claim than the data support | reviewer's text in App. B and in `B-registered/RESULTADO-v3.md` (with a dated rc15 note; no number changed; no recorded sha256 covers that file) |
| C5 LOW, header time | holds | header 23:15Z vs file-system 23:13:58Z | "is rounded" → "is inconsistent with the file-system timestamp" |
| C6 LOW, H1b metadata | holds | §4.4 says trivially 1.0; estimator l.975 said "UNEVALUABLE" | docstring and v4 output carry the reviewer's string (the v3 string is emitted only under `--aceleracao uma_amostra`, to keep v3 reproducible) |
| F1 LOW, §9 and abstract | holds | H1 excluded zero on every leg in every version up to rc9 (rc7 percentile, rc8, rc9; and under v4 too, `checks-rc15` block R); H1a on every registered leg only in rc9; rc8's post-hoc leg contains zero (−78.27 [−146.19; +2.11] under v4, [−146.22; +1.95] as rc8 printed); the sensitivity analysis excludes zero on the locked leg only | Fable's text in §9 and the abstract |
| F2 LOW, rc14 not recorded | holds | status header and changelog ended at rc13 | status clauses for rc14 and rc15; changelog block rc14 (item 149) and rc15 (150–155) |

## v3 → v4 (registered leg; full table in `B-registered/RESULTADO-v4.md`)

| | v3 | v4 |
|---|---|---|
| H1 | [−28.151441, +23.503350] | [−28.364131, +23.152967] |
| H1a | [−372.202800, +314.654494] | [−373.699037, +310.823666] |
| H1c | [−0.046363, +0.010973] | [−0.046363, +0.010955] |
| H2 winsorized time | [+0.010780, +0.689995] | [+0.009913, +0.689492] |
| H2 raw tokens | [+740.168869, +12281.622226] | [+749.488478, +12307.687696] |

Census over 160 intervals (all legs of the artifact, BCa and reported, and all H2 legs) and
every leg of `checks-rc15` blocks A and R: **no interval changes whether it contains zero**;
points, every re-randomization p and the whole `multiplicidade` block are identical; no
percentile fallback fires. 17 of the 24 bounds of the four BCa legs move; 7 do not (H1c's
registered lower bound among them), so the text says "most", not "every". Upper adjusted
quantiles of H1/H1a: 99.68% / 99.71% (33rd / 30th largest) → 99.51% / 99.56% (50th / 45th).

## Reproducibility

- Locked `ITT-2026-09-21.json` and `RERANDOMIZACAO-2026-09-21.json`: byte for byte (both modes).
- v1 and v2 field for field (under the v3 acceleration); **new** v3 control inside v4: every
  `resumo` leg, every H2 interval/acceleration, every leg's BCa interval, acceleration and z0 —
  0 divergences.
- `--aceleracao uma_amostra`: deep diff against `out/ITT-REGISTRADO-v3-2026-10-05.json` differs
  only in `gerado_em` and `proveniencia.script.sha256`.
- v1, v2, v3 JSON and frozen scripts, `checks-rc10.json` and the rc10 Figure B1: untouched.

## Decisions the review did not dictate (declared)

1. **rc8 and rc9 rows of §4.2** are reported analyses (sensitivities), so they were recomputed
   with the v4 acceleration (`checks-rc15` block R, which first reproduces checks-rc8/rc9 under
   the old acceleration). Text that **records what an earlier version printed** keeps the
   printed value: struck spans, the changelog, §5's "the table read …" parenthetical (with a
   new rc15 note giving the v4 values) and "in rc9, … the 6th smallest" (qualified "with the
   one-sample acceleration").
2. Body references to the registered artifact moved from v3 / checks-rc10 to v4 /
   checks-rc15 (identical non-BCa fields; checked by deep diff: only `bca`/`ic95*` differ).
3. The two "categorical noise" claims ("carry visible Monte-Carlo noise", "the least stable
   number in the table") were replaced by the measured rank and "Monte-Carlo error not measured".
4. `RESULTADO-v3.md` was corrected (C4 names it); rc13's parity check on that file is carried by
   reverting the rc15 correction first.

## Artifacts (sha256 prefix)

| file | sha256 |
|---|---|
| `measurement/estimador_itt_registrado.py` = `B-registered/estimador_itt_registrado-v4-b3095740.py` | `b3095740…` |
| `out/ITT-REGISTRADO-v4-2026-10-05.json` | `3ed7637e…` |
| `B-registered/teste_aceleracao_v4.py` · `teste-aceleracao-v4.json` | `bb9c3197…` · `ae9e8fe9…` |
| `B-registered/RESULTADO-v4.md` | `d5b3b8b6…` |
| `B-rc15/checks-rc15.py` · `checks-rc15.json` | `603695e0…` · `914d4fa0…` |
| `measurement/sprint-figB-h1a-inversao-registrado-v4.py` | `6adc7f1e…` |
| `figures/figB1-h1a-inversao-registrado-v4.svg` · `.png` · `.run.json` | `ddacff58…` · `8e7aeebb…` · `3d949511…` |
| `B-v2-rc15.md` | `65b870bb…` |
| `B-rc15/parity-rc15.py` | `df4f492b…` |

The figure script aborts against the v3 artifact and against `checks-rc10.json` (tested).

## Parity (`python3 B-rc15/parity-rc15.py`: **PASS**)

The script imports `B-rc14/parity-rc14.py` (pinned `04e2dc01…`), which carries rc13, rc12 and
rc11. rc11's checks read the script sha256; they are pointed at the frozen v3 script, which is
the one rc11 pinned.

- 53 hunks, each with an ID; hunks that are only v4 substitutions get `V4` automatically.
- Intervals traced to v4: 34 (v3 → v4) pairs **formatted at run time from the artifacts**,
  25 used, 40 occurrences in rc14; after the substitution no v3 string is left in the unstruck
  body outside two declared history contexts. Numeric tokens removed beyond the substitution:
  `78` ×2, `0.22` ×2, `99`, `100` (C2), each declared; every token added is in rc14, an
  artifact leaf or derived (0.779; the v4 H2 bounds of rc9's analysis).
- Italic quotations, citations, footnotes, DOIs and struck spans unchanged; headings (40)
  unchanged; image link v3 → v4 declared; code spans, paths, § references and table lines
  change only inside ID'd hunks.
- Working list and changelog: with the three declared insertions removed, byte-identical to
  rc14; new blocks numbered 149 and 150–155.
- SHAM-JANELA: 10/10 blocks byte-identical.
- Carried locks: `claims_rc13` (rc11 (a)–(f), rc12 (g)–(h), rc13 (i)–(l)) clean; new sweep
  locks for every class the review named, presence locks for the reviewers' sentences, status
  header names rc14 and rc15.
- Qualifier set: rc14's locked phrases are **102 distinct** (38 qualifiers + 4 census marks + 61
  headlines − 1 duplicate; `APPLY-B-rc14.md` said 101, a miscount: rc14's own code gives 102).
  2 headlines carry a BCa interval and are replaced one for one by their v4 formatting; 14
  phrase deltas are justified, each tied to C1–C5 or F1 (6 of them rc12/rc13 headlines the
  findings rewrite: "instrument change", "neither re-draws … nor re-adjudicates", "is rounded",
  the 78% noise sentence, "not that case", "resamples the first with the other two frozen").
- Hedge words: checked per edit ID (14 groups, each declared with its reason) and summed to the
  body delta.
- Integrity: rc11 script integrity (v3), rc12 census record, rc13 B-censo paths (RESULTADO-v3
  with the rc15 note reverted gives rc13's file); v4 integrity (frozen copy = running script =
  provenance; v1/v2/v3 controls identical; test passed on 10/10 real cases; checks-rc15 and the
  rc15 figure pin v4; v1, v2, v3 and checks-rc10 unchanged; every sha8 cited for v4 is the
  file's).

`--self-test`: **27/27 mutations caught**, unmutated rc15 passes (an interval reverted to v3, a
v4 bound altered, the rc8 row left at v3, H2 tokens reverted, a rank not updated, "may
under-cover" dropped, "instrument change", "too narrow", independence dropped, "not that case",
a noise claim, F1 reverted, the status header, a changelog item removed, an old changelog line
edited, a SHAM block, two hedges, two carried claims, a citation, an unmapped hunk, and five
integrity mutations).

## Not done (declared)

- rc15 has not been reviewed; the arm-stratified acceleration in particular.
- `B-rc14/parity-rc14.py` and `B-rc13/parity-rc13.py` no longer pass as written: the script they
  read is now v4 and `RESULTADO-v3.md` carries the rc15 note. rc15's parity carries their checks
  with those two inputs pinned or reverted.
- The Monte-Carlo error of the H1/H1a upper bounds (50th / 45th largest of 10 000) was not
  measured.
- None of the rc15 artifacts is in the ballast manifest (working list 17).
