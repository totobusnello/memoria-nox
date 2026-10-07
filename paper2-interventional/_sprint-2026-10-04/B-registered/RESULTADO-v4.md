# Paper B — the registered ITT analysis, v4 (2026-10-05): arm-stratified BCa acceleration

The review of rc14 (`_sprint-2026-10-04/REVIEW-B-rc14-2026-10-05.md`, Codex C1) found that
`measurement/estimador_itt_registrado.py` computed the BCa acceleration as a one-sample
quantity: the 19 leave-one-epoch-out jackknife estimates (11 treatment deletions, 8 control
deletions) were pooled and centred at one overall mean, while the bootstrap resamples the two
arms independently. v4 replaces it with the multi-sample (arm-stratified) acceleration and
changes nothing else. Nothing here touches `estimador_itt.py`, the locked artifacts in
`~/Backups/paper2-ensaio-2026-09-21/`, git, a deposit, a voice, the VPS or production. v1, v2
and v3 (files and frozen scripts) are left as they were.

## The finding, verified

`bootstrap()` (v3, l.430-450 of the frozen `estimador_itt_registrado-v3-0aa9202b.py`):

```
jk = [all 11 treatment deletions] + [all 8 control deletions]
m  = mean(jk)                         # one overall centre
a  = sum((m - x)^3) / (6 sum((m - x)^2)^1.5)
```

and the draws `at = [t[rng.randrange(len(t))] for _ in t]`, `ac = [c[...] for _ in c]`, i.e.
two independent samples. The finding holds. The multi-sample acceleration (SciPy
`stats._resampling._bca_interval`, the per-sample generalisation of Efron and Tibshirani
1993, eq. 14.15) is, for arm g with delete-one estimates θ_(g,−i):

```
q_gi = ((n_g − 1)/n_g) (mean_g(θ_(g,−·)) − θ_(g,−i))
a    = Σ_g,i q_gi³ / (6 (Σ_g,i q_gi²)^1.5)
```

## What v4 changes

`aceleracao_estratificada()` computes it; `aceleracao_uma_amostra()` keeps the v3 formula.
The flag `--aceleracao {estratificada,uma_amostra}` (default `estratificada`) selects which
one feeds the interval. Draws, z0 (`Φ⁻¹(#{θ* < θ̂}/B)`), the quantile index rule, rounding,
the percentile fallback rule, point estimates and every re-randomization p are untouched. In
v4 each `bca` block also carries the v3 values (`acel_uma_amostra_v3`,
`fallback_uma_amostra_v3`, `ic95_bca_uma_amostra_v3`), the construction name and the per-arm
counts. The H1b metadata (review C6) now reads: *"TRIVIALLY 1.0 under the retained
action-level Opportunity definition; the intended mechanism question is not identifiable
(DEVIATIONS §10.32)."* (the v3 string is emitted under `--aceleracao uma_amostra`).

| new artifact | sha256 (prefix) | what it is |
|---|---|---|
| `measurement/estimador_itt_registrado.py` | `b3095740…` | v3 + arm-stratified acceleration + v3 control; frozen at `B-registered/estimador_itt_registrado-v4-b3095740.py` |
| `out/ITT-REGISTRADO-v4-2026-10-05.json` | `3ed7637e…` | the v4 run; carries `bca_aceleracao` and `controle_v3_registrado` |
| `B-registered/teste_aceleracao_v4.py` · `teste-aceleracao-v4.json` | `bb9c3197…` · `ae9e8fe9…` | the test of the acceleration (below) |
| `B-rc15/checks-rc15.py` · `checks-rc15.json` | `603695e0…` · `914d4fa0…` | checks-rc10 under v4 + block V (v3 construction gives back checks-rc10) + block R (rc8's and rc9's analyses under v4, v3 construction gives back checks-rc8/rc9) |
| `measurement/sprint-figB-h1a-inversao-registrado-v4.py` · `figures/figB1-h1a-inversao-registrado-v4.*` | `6adc7f1e…` · `ddacff58…` (svg) | Figure B1 from v4 (aborting guards) |

```
python3 measurement/estimador_itt_registrado.py --out out/ITT-REGISTRADO-v4-2026-10-05.json
python3 measurement/estimador_itt_registrado.py --aceleracao uma_amostra --out <scratch>/v3.json
python3 _sprint-2026-10-04/B-registered/teste_aceleracao_v4.py --out _sprint-2026-10-04/B-registered/teste-aceleracao-v4.json
python3 _sprint-2026-10-04/B-rc15/checks-rc15.py
python3 measurement/sprint-figB-h1a-inversao-registrado-v4.py \
  --itt-registrado out/ITT-REGISTRADO-v4-2026-10-05.json \
  --checks _sprint-2026-10-04/B-rc15/checks-rc15.json \
  --episodes <locked episodes> --serving <locked serving log> --assignment ASSIGNMENT-SERVING.json \
  --out _sprint-2026-10-04/figures/figB1-h1a-inversao-registrado-v4.svg --png
```

## Reproducibility controls

| control | result |
|---|---|
| locked `ITT-2026-09-21.json` and `RERANDOMIZACAO-2026-09-21.json` rebuilt byte for byte (exit 2 otherwise) | identical (both modes; the locked analysis is percentile, untouched) |
| v1 `resumo.registrado` field for field, under the v3 acceleration (exit 3) | identical |
| v2 `resumo.registrado` and its diagnostic leg, under the v3 acceleration (exit 4) | identical |
| **new**: v3 — every `resumo` leg (6), every H2 interval and acceleration (5 legs × 2 components × 2 estimators), and every leg's BCa interval, acceleration and z0, under the v3 acceleration carried beside v4 (exit 5) | identical, 0 divergences (`controle_v3_registrado`) |
| **new**: `--aceleracao uma_amostra`, whole output against `out/ITT-REGISTRADO-v3-2026-10-05.json` | identical in every field except `gerado_em` and `proveniencia.script.sha256` (deep diff, run 2026-10-06T00:17Z) |

## The test of the acceleration (`teste-aceleracao-v4.json`, exit 0)

1. **Hand case, exact.** T = {1, 2, 4}, C = {0, 3}, statistic = difference of means. Delete-one
   values: T → 1.5, 1.0, 0.0; C → −2/3, 7/3. Σq² = 355/216, Σq³ = 20/243, a = 0.006510443418…;
   the script gives the same to 5×10⁻¹⁸.
2. **SciPy on the toy** (`scipy.stats._resampling._bca_interval`, SciPy 1.18.0, which returns
   `a_hat` "for testing"): equal to the exact value (|Δ| < 10⁻¹⁷). The v3 one-sample value on
   the same jackknife is 0.003432, so the test bites.
3. **SciPy on the real data.** SciPy's `a_hat`, computed with the estimator's own aggregation
   over epoch indices (11 treatment, 8 control), equals the v4 `acel` to the 6th decimal for
   H1, H1a, H1c of the registered leg and of the 'without' leg, and for the four H2 estimators
   of the registered leg (10 of 10).

## v3 → v4, every BCa interval the manuscript reports

Same draws, same z0, same quantile rule; acceleration only.

| leg | hypothesis | v3 | v4 | contains zero (v3 → v4) |
|---|---|---|---|---|
| registered, locked | H1 | [−28.151441, +23.503350] | [−28.364131, +23.152967] | yes → yes |
| registered, locked | H1a | [−372.202800, +314.654494] | [−373.699037, +310.823666] | yes → yes |
| registered, locked | H1c | [−0.046363, +0.010973] | [−0.046363, +0.010955] | yes → yes |
| registered, pre-committed | H1 / H1a / H1c | [−29.99; +24.62] / [−359.53; +321.30] / [−0.0622; +0.0074] | [−30.26; +24.02] / [−362.55; +315.50] / [−0.0623; +0.0073] | yes → yes (all) |
| registered, post-hoc (no `09-14`) | H1 / H1a / H1c | [−28.26; +19.30] / [−373.87; +300.07] / [−0.0509; +0.0073] | [−28.40; +18.79] / [−375.88; +295.33] / [−0.0509; +0.0073] | yes → yes (all) |
| registered 'without' straddling sessions | H1 / H1a / H1c | [−16.33; +1.64] / [−115.60; +22.07] / [−0.0425; +0.0137] | [−16.32; +1.65] / [−115.53; +22.23] / [−0.0425; +0.0138] | yes → yes (all) |
| rc9's analysis, locked / pre-committed / post-hoc | H1a | [−352.07; −80.31] / [−349.29; −55.45] / [−162.77; −26.43] | [−351.70; −79.81] / [−348.56; −54.93] / [−162.77; −26.28] | no → no (all) |
| rc8's analysis, locked / pre-committed / post-hoc | H1a | [−282.29; −61.12] / [−254.18; −28.82] / [−146.22; +1.95] | [−281.49; −61.02] / [−254.18; −28.88] / [−146.19; +2.11] | no, no, yes → no, no, yes |
| H2, registered, winsorized time | | [+0.010780, +0.689995] | [+0.009913, +0.689492] | no → no |
| H2, registered, raw time | | [−5.521528, +0.829711] | [−5.508407, +0.832108] | yes → yes |
| H2, registered, winsorized tokens | | [−1069.70, +6182.36] | [−1066.20, +6183.95] | yes → yes |
| H2, registered, raw tokens | | [+740.168869, +12281.622226] | [+749.488478, +12307.687696] | no → no |

The five intervals the review computed (H1, H1a, H1c of the registered leg; H2 winsorized time
and raw tokens) match the review's numbers to every printed digit. Over every leg of the
artifact (all `pernas`, all three hypotheses; all H2 legs and estimators) and every leg of
checks-rc15 blocks A and R, **no interval changes whether it contains zero**. Point estimates,
every re-randomization p, and the `multiplicidade` block (Holm under both readings) are
identical to v3 (checked: `json.dumps` equal). No fallback to percentile fires in v4. The H1 and
H1a upper adjusted quantiles move from 99.68% / 99.71% (33rd / 30th largest replicate) to
99.51% / 99.56% (50th / 45th largest); H1c's lower quantile index is unchanged (205th smallest).

## Text carried from RESULTADO-v3 that v4 corrects

`RESULTADO-v3.md`, own-stratum paragraph (review C4): "no within-stratum inferential contrast
(interval or test) is estimable" now reads "No standalone inferential interval or test is
reported for this stratum. The descriptive per-hour contrasts (…) are reported in the
manuscript (§4); H1c cannot be contrasted because control has no eligible opportunities.",
with a dated correction note. No number changed; no recorded sha256 covers that file.

## Note added 2026-10-05 (rc17): the acceleration test was revised in rc16

The artifact table above records the test as rc15 left it (`bb9c3197…` · `ae9e8fe9…`); those
bytes are kept unchanged as `B-registered/teste_aceleracao_v4-rc15-bb9c3197.py` and
`teste-aceleracao-v4-rc15-ae9e8fe9.json`. rc16 revised the test so that it also compares the
unrounded accelerations, to 1e-12 (largest difference 1.4×10⁻¹⁶); the current files,
`teste_aceleracao_v4.py` · `teste-aceleracao-v4.json`, have sha256 `d4d960db…` · `041bd4a9…`
(`APPLY-B-rc16.md`). Nothing above this note was edited, so every hash it records still
resolves; the bytes before this note are kept as `RESULTADO-v4-rc16-d5b3b8b6.md`.
