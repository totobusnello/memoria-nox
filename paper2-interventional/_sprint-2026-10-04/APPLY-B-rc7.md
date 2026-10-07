# APPLY B-rc7: review of rc6, per finding (2026-10-05)

Source: `REVIEW-B-rc6-2026-10-05.md` (Codex 1-11, Fable HIGH-1..LOW-12, author decisions of
2026-10-05). Manuscript: `B-v2-rc6.md` copied to `B-v2-rc7.md`; only rc7 was edited.
No git, no Zenodo, no voices, no VPS. Not touched: `measurement/estimador_itt_registrado.py`,
`out/ITT-REGISTRADO-2026-10-05.json`, `_sprint-2026-10-04/B-registered/`.

Evidence script (new): `B-rc7/checks-rc7.py` -> `B-rc7/checks-rc7.json`. It reads the trial
ballast read-only (`~/Backups/paper2-ensaio-2026-09-21/`, verdicts from the `-COPIA` copy) and
aborts unless it first reproduces the existing artifacts (337/7,392 changed briefs; coverage
2,068/7,392 and 1,385/5,145; effective sizes 84.8 and 91.49; ratios 22.5 and 6.9).

Parity: `python3 B-rc7/parity-rc7.py` -> **PASS**; `--self-test` -> 14/14 mutations caught,
unmutated PASS; `--list` -> the 108 `REANALISE` blocks (saved in `B-rc7/reanalise-list.txt`).
SHAM-JANELA: 10 blocks, byte-identical to rc6, no `REANALISE` marker inside them.

## Findings

| ID | verified? | applied? | evidence / what changed |
|---|---|---|---|
| **Fable HIGH-1** | **yes**, with one correction | yes (author decision: H1c stays primary, switch declared) | PREREG-DRAFT.md l.305-306 (H1 primary; H1a–c Holm co-primary) and l.1025 (H1 at α=0.05; H1a–c + H2 Holm, H2 as two members). Switch: `DESIGN-REVISION-2026-08-30.md` §3-ter, commit `4da7e43` 16:51:56Z; `PROSPECTIVE-ESTIMAND-2026-08-30.md` §3-bis, commit `05a60e8` 20:51:20Z; seed declaration push 21:18:35Z, round 31774052 emitted 21:32:04Z (ASSIGN-SEED-2026-08-30.md l.130). `deposit/PLAN-v1.13.md` l.3-5: not deposited. **Correction to Fable:** PROSPECTIVE-ESTIMAND does record the switch (§3-bis, l.217-275, "H1c primária, H1/H1a/H1b secundárias"); only its summary table l.26 still names the density outcome. The text says exactly that. Applied in Abstract (new first paragraph), §1 table (H1, H1c rows) + new paragraph "The primary switch, declared" with Holm statement, §1.1 trust list, §4.0.2 table labels, §4.3, §8.2 table, §9, Appendix A (new bullets: switch; nothing after v1.12 deposited, incl. v1.13 and PROSPECTIVE; H2/H3; the four analysis departures). DEVIATIONS-FOR-PAPER.md has no entry for the switch (grep), so Appendix A now says so. p-values and the Holm sentence are `REANALISE`. |
| **Fable HIGH-2** | yes | yes (structure) | PREREG l.309-310 define H2 (secondary confirmatory) and H3 (exploratory, nDCG@10/recall@10); 0 occurrences of H2/regret/nDCG/recall@10 in rc6, SPEC, DEVIATIONS, DESIGN-REVISION, AMENDMENT-v1.12, PROSPECTIVE (grep -c). SPEC §8 l.292 is the source of the mislabel "dose-resposta / H3"; PREREG l.351 calls it "the dose–response reading rule of the designation block". §5: row renamed, H2 and H3 rows added with the reason in `REANALISE: rewrite` placeholders, closing paragraph rewritten (four rows were in SPEC §8; H1b after the close; H2/H3 nowhere). §1 and Appendix A point to §5. |
| Codex 1 | yes | yes | `out/CONCENTRATION-2026-08-30.json`: `Bash|shell:outro` 573 of 611 covered opportunities = 93.8%; `cobertura_e_m10.py` l.54-73 increments `sig_hits` once per served designated item. §4.5 heading + text (struck and corrected, Codex wording), §1.1 (the "commitment the data refuted" argument struck), §9 third observation replaced. DESIGN-REVISION l.215-218 required the indistinction to go in the abstract: added there. |
| Codex 2 | yes | wrapped, not resolved | `carregar_verdicts` on `ensaio-20260921-PRIMARIO-3fam.jsonl`: 1,195 submitted, 1,159 adjudicated, 36 unknown; panelists xai/google/zhipu only (`checks-rc7.json` D). §4 "Coverage 100%" struck, submission vs adjudication stated; §6 item 7 says the rule was not implemented. All `REANALISE: rewrite`. |
| Codex 3 | yes (code) | wrapped, not resolved | `estimador_itt.py` l.37 and l.103-105 select by epoch date; no 22:51:23 cut, no exposure offset. §3.0.1 no longer says the window closes at expiry; the estimator's behaviour is stated in a `REANALISE: rewrite` block. The counts 33 / 5 / 22.835 / 2 were **not** re-verified and are not in the text (left to the registered analysis). |
| Codex 4 | yes | yes | `potencia-h1c.py` l.28-32: null term `sqrt(2·pb(1−pb))`, alternative term `sqrt(p1(1−p1)+p0(1−p0))`. Abstract paragraph rewritten (Codex wording), §4.1.1 heading renamed, the implied-SE paragraph struck with a correction, table "known defect" → "known limit", B.1 row struck. 0.0279/0.0320/59% survive only in struck text and in the correction that withdraws them. |
| Codex 5 + Fable MEDIUM-7 | yes | yes | Denominator decided from the serving log: in treatment epochs, **335 of 7,350** briefs served in active mode changed (4.56%); the artifact's 337/7,392 includes 2 shadow-mode counterfactual changes among the 42 shadow briefs of `09-01` (`checks-rc7.json` A). Chosen: 335/7,350 (served changes over served briefs). 3.14% named "pre-trial calibration share (11 of 350 at `w = 2`)" in Abstract, §4.0.2, §4.3, B.1; realized ratios 15.5 (locked) and 10.3 (without `09-14`) added; §4.0.1b states both counts. |
| Codex 6 | yes | yes | `mde()` bisects in [0, p0]; `poder_z` at 91.49, p1 = 0.25 → 0.887; at 84.8 → 0.862 (`checks-rc7.json` C). Abstract, §1 table, §4.1.1, §7, §9: "no reduction from p0 = 0.0782, including total elimination, reaches 80% power"; §4.1.1 states an increase can reach 80%. |
| Codex 7 | yes | yes | No coverage experiment exists; Webb's abstract concerns wild bootstrap with few total clusters (verification log l.76). Fig B1 caption, §4.1.1 table and caveat, §4.1.2, §4.3, abstract: "may under-cover; coverage not established". §8.3 rewritten (old text struck); cluster counts in `REANALISE`. |
| Codex 8 + Fable MEDIUM-3 | yes | yes | `DESIGNATION-2026-08-26.json`: declaration pushed 20:07:24Z, round 31657512 emitted 20:25:00Z → 1,056 s; ASSIGN-SEED l.130: push 21:18:35Z, emission 21:32:04Z → 13 min 29 s. §1 rewritten (Codex wording + the second precedence); §1.1 trust list adds both precedences as resting on our push times. |
| Codex 9 | yes | yes | Long-form related work l.102-105 and verification log l.39 (Theorem 1 read): the failure is for a non-retrievable memory. §8.2: zero-retrieval condition stated, quote kept. |
| Codex 10 | yes | yes | Verification log l.94 ("registration coincides"). §8.4 rewritten with the observational caveat. |
| Codex 11 | yes | yes | Abstract sentence replaced with Codex wording. |
| Fable MEDIUM-4 | yes | wrapped + declared | PREREG l.997 locks BCa with leave-one-epoch-out jackknife, percentile only as fallback; `estimador_itt.py` l.140-149 is percentile, resampled within arm. §4 "Uncertainty" declares the deviation in a `REANALISE: rewrite` block; Appendix A lists it. |
| Fable MEDIUM-5 | yes | wrapped + declared | SPEC §2 l.89: `09-02` "excluída do conjunto de análise". §3 new "Deviation, declared in rc7"; the ITT row and the "19 analyzable clusters" paragraph are `REANALISE: rewrite`. |
| **Fable MEDIUM-6** | **yes** | yes: **§1.1 claim withdrawn for §10.33** | `ITT-PRELIMINAR.json` (backup, read-only): no `gerado_em`; content cites "DEVIATIONS 10.32", 2,000 replicates, H1a −143.92 [−210.89; −15.67]; file time **2026-09-21 16:16:44 −03:00** (19:16:44Z). DEVIATIONS §10.32 "16:14", §10.33 "16:20"; both committed in `55476b7` at 16:22:04 −03:00 with the estimates. The preliminary precedes 16:20 → the sentence "no number of the H1 family had been produced at either point" is struck; §1.1 now says §10.32 preceded any estimate and §10.33 followed the preliminary H1a, and that a file time is as forgeable as a commit time. §7 "Our own bookkeeping" updated. Working list 17: put the preliminary and `checks-rc7` in the ballast. |
| Fable LOW-8 | yes | yes | `C12-EMPATES-COMO-FAILURE`: rerun −0.026571 = 0.09189 − 0.118461 (treatment proportion stored rounded); first order 0.091895 − 0.118461 = −0.026566. §4 and B.1 say so; changelog item 73 left as history, corrected by item 91. |
| Fable LOW-9 | yes | yes | §9: "The only rejection by the registered test is on the hypothesis…". |
| Fable LOW-10 | yes | yes (declared) | Coverage over active briefs: 2,057/7,350 = 28.0% (`checks-rc7.json` B); §4.5 note and §4.0.1b (09-01: 22 of 630 active changed, 3.49%). |
| Fable LOW-11 | yes | yes | 2026-07-29 → 2026-08-16 = 18 days; §9 "eighteen days apart". |
| Fable LOW-12 | yes | yes | SPEC l.32 `09-01` 22.38 h/24 = 0.9325; artifacts use 630/672 = 0.9375 (and `09-03` by brief share 441/672, `09-20` by clock). Effect: 84.80 → 84.78, 91.49 → 91.47; no verdict changes. Note added in §4.1.1. |

## Sweep (outside SHAM-JANELA blocks)

- **Causal/strong language from null or under-powered tests:** abstract "evidence of nothing"
  (C11); §8.4 "Registration changes" (C10); §4.7 "plausible, and false" → "not supported by
  the measurement"; §4.3 "volume does" → "in the arithmetic, volume does".
- **"Incompatible"/"contradicts" across different quantities:** abstract and §4.1.1 (C4);
  §4.5, §1.1, §9 (C1); §4.0.2 "the disagreement … is also what two different estimands can
  produce"; §8.2 "does not deserve trust" → "whose coverage we have not established"; §8.5
  "its own contradictions" → "the inconsistencies in its own registration", and the
  sample-size/estimand sentence made explicit. Kept on purpose: §3.0.1 (234 epochs vs a
  20-epoch intervention) and §4.4 (two locks defining one estimand): same object, real
  conflict.
- **"Every interval under-covers":** Fig B1 caption, §4.1.1 table/caveat, §4.1.2 ("may be
  optimistic"), §4.3 ("may return"), abstract, §8.3. Remaining "under-cover" uses are
  conditional.
- **Calibration share as realized:** abstract (×2), §4.0.2, §4.3, B.1; 955% now named a
  planning figure at the calibration share.

## REANALISE blocks (108: 85 value, 23 rewrite)

Full list with line numbers: `B-rc7/reanalise-list.txt` (regenerate with `--list`). By
location: Abstract R01-R11; §1 R12-R14; §1.1 caveat R15; §3 R16-R19; §3.0.1 R20; §4 R21-R23;
§4.0.2 R24-R31; §4.1 table/closing; §4.1.1 (control rate, CI, cluster counts, p, 22%,
91.49/96.41 power sentences); §4.1.2 p; §4.2 table, p, session-hours, N; Fig B1 caption;
§4.3 values and ratios; §5 H2/H3 reasons; §6 item 7; §7 power, ties, opportunities/epoch;
§8.3 periods, clusters; §8.4 power; §9 power; Appendix A (p, Holm, the four departures);
B.1 rows (ratios, adjudication counts, power at 91.49, opportunities/epoch, four-vote H1c).

Integration notes (not done here, for working list 18):
1. The "reject?" and "agree/disagree" cells of the §4.0.2 table follow the p-values; recheck.
2. The C12 tie counts per arm (10/11/7, 4/7, HT weights) were not wrapped; they depend on the
   window and should be rechecked under the expiry cut.
3. Figure B1 (SVG and caption values) must be regenerated from the registered artifact.
4. Section headings §4.1 and §4.2 assert "null" and "excludes zero only on the locked leg";
   recheck against the registered result.

## Observations for the author (outside the review; not applied)

1. `PROSPECTIVE-ESTIMAND-2026-08-30.md` §3-bis declares a stop rule: if coverage measured in
   Epoch 1 falls below 36.7%, the interventional arm ends with a null "por impossibilidade
   de desenho". The manuscript does not mention this rule or whether it fired (the 36.7%
   refers to covered opportunities, a different quantity from the 28% of briefs in §4.5).
2. Commit `3e1c259` (2026-08-30 21:56:42Z, after round 31774052 was emitted): "retract: the
   assignment rule I declared was not the registered one — replaced by assign_arms.py". The
   registered script was used, so the abstract's claim stands, but the declared rule in
   `ASSIGN-SEED-2026-08-30.md` changed after the seed was public; a reviewer may ask.
3. `ITT-PRELIMINAR.json` is not in `MANIFESTO-LASTRO-P2.json` (working list 17).
