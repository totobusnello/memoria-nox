# Paper B — the registered ITT analysis, v3 (2026-10-05): sessions in the epoch of their start

The author decided that the analysis reported is the registered one. PREREG §2 item 3 then
requires: *"Boundary-straddling sessions are assigned to the epoch of their start, flagged, with
sensitivity with/without"*, and sessions longer than one epoch are their own stratum. v2 did not
apply the attribution (it counted every episode in the epoch of its own timestamp) and computed
the 'without' leg only as a diagnostic. v3 makes the attribution the sixth switch,
`sessao_ao_epoch_de_inicio`, on in the registered analysis, and the 'without' leg its registered
sensitivity. Nothing here touches `estimador_itt.py`, the locked artifacts in
`~/Backups/paper2-ensaio-2026-09-21/`, git, a deposit, a voice, the VPS or production. Inputs are
read in place, read-only, and not copied here (the episode corpus holds real work content).
`RESULTADO-v2.md` and `out/ITT-REGISTRADO-v2-2026-10-05.json` are left as they were.

| new artifact | sha256 (prefix) | what it is |
|---|---|---|
| `measurement/estimador_itt_registrado.py` | `0aa9202b…` (rc11; `b5135f04…` in rc10) | v2 + switch 6 + registered 'without' leg + rc8/rc9-equivalent legs with their Holm families; frozen at `B-registered/estimador_itt_registrado-v3-0aa9202b.py`. rc11 corrected four stale comments and docstrings ("four switches" ×3, the 'with' leg "not implemented"); the AST is identical apart from docstrings, and the rc10 bytes are kept at `B-registered/estimador_itt_registrado-v3-rc10-b5135f04.py` |
| `out/ITT-REGISTRADO-v3-2026-10-05.json` | `41a0a0ee…` (rc11; `36f6421a…` in rc10) | the v3 run (v1 and v2 files untouched); regenerated in rc11 by the corrected script, identical to rc10's in every field except `gerado_em` and `proveniencia.script.sha256`; the rc10 bytes are kept at `B-registered/ITT-REGISTRADO-v3-rc10-36f6421a.json`, the file `checks-rc10.json` and the rc10 Figure B1 pin (the figure script aborts against the regenerated file and reproduces the rc10 SVG byte for byte against the kept one) |
| `B-registered/estimador_itt_registrado-v2-ac9d2f05.py` | `ac9d2f05…` | frozen copy of the v2 script, the sha256 v2's provenance records |
| `B-rc10/checks-rc10.py` · `checks-rc10.json` | `1cd8d626…` · `b774e61c…` | v3 sensitivity legs, per-epoch hours, ratios, BCa ranks, washout, straddling sessions, four-vote ties |
| `measurement/sprint-figB-h1a-inversao-registrado-v3.py` · `figures/figB1-h1a-inversao-registrado-v3.*` | `ddc3f552…` · `d1068b3f…` (svg) | Figure B1 from v3 (aborting guards) |

None of them is in the ballast manifest yet.

```
python3 measurement/estimador_itt_registrado.py --out out/ITT-REGISTRADO-v3-2026-10-05.json
python3 _sprint-2026-10-04/B-rc10/checks-rc10.py
python3 measurement/sprint-figB-h1a-inversao-registrado-v3.py \
  --itt-registrado out/ITT-REGISTRADO-v3-2026-10-05.json \
  --checks _sprint-2026-10-04/B-rc10/checks-rc10.json \
  --episodes <locked episodes> --serving <locked serving log> --assignment ASSIGNMENT-SERVING.json \
  --out _sprint-2026-10-04/figures/figB1-h1a-inversao-registrado-v3.svg --png
```

Re-running the estimator reproduces every field except `gerado_em` (checked on a second run).

## The switch

**Rule.** Under `sessao_ao_epoch_de_inicio = sim`, every episode takes the epoch of its session's
first episode (`atribui_ao_inicio`), and its offset is recomputed from that epoch's start. The
window, the washout eligibility, the spans (`span_por_sessao`), the outcomes and H2's population
all see the attributed epoch. Condition (i) (`primeiro_failure` at least one epoch before) is
checked against the attributed epoch, since PREREG §4.1 reads the serving snapshot *at session
start*; the corpus of past failures that defines an opportunity keeps the epoch in which each
failure was written (it is computed on the unattributed episodes).

**Controls (all pass, exit 0).**

- every switch at the earlier choice: `ITT-2026-09-21.json` and `RERANDOMIZACAO-2026-09-21.json`
  rebuilt byte for byte (exit 2 otherwise);
- switch 6 at the earlier choice (`registrado_v2_equivalente`): v2's `resumo.registrado` field for
  field (exit 4 otherwise), and the v2-equivalent 'without' leg equals v2's diagnostic leg;
- switches 5 and 6 at the earlier choice (`registrado_v1_equivalente`): v1's `resumo.registrado`
  field for field (exit 3 otherwise);
- `checks-rc10.py` rebuilds the atual, registered, 'without' and v2-equivalent legs with its own
  leg builder and aborts on any difference in points, both intervals and per-arm totals.

## v3 against v2 (registered analysis, 19 epochs, BCa, 10,000 replicates, seed 20260921)

| hypothesis | v2 (rc9: sessions split by epoch) | **v3 (registered: sessions at their start)** | v3 'without' boundary-crossing sessions |
|---|---|---|---|
| H1 | −19.85 [−32.69; −9.89] · p = 0.0302 | **−1.27 [−28.15; +23.50] · p = 0.3294** | −7.40 [−16.33; +1.64] · p = 0.1957 |
| H1a | −233.20 [−352.07; −80.31] · p = 0.0168 | **−15.22 [−372.20; +314.65] · p = 0.2599** | −51.12 [−115.60; +22.07] · p = 0.1501 |
| H1c | −0.0121 [−0.0445; +0.0125] · p = 0.434 | **−0.0140 [−0.0464; +0.0110] · p = 0.4006** | −0.0109 [−0.0425; +0.0137] · p = 0.4571 |

| per arm (T / C) | v2 | v3 | v3 without |
|---|---|---|---|
| session-hours | 10.75 / 3.25 | 324.95 / 57.06 | 3.52 / 3.06 |
| opportunities (weighted) | 1 138.47 / 1 101.75 | 1 203.98 / 1 079.91 | 1 064.02 / 1 079.91 |
| repeats (weighted) | 76.84 / 87.72 | 79.84 / 86.72 | 73.84 / 86.72 |
| epochs | 11 / 8 | 11 / 8 | 11 / 8 |

H1 = H1c × H1a holds on the six v3 cells to 3.8×10⁻⁶ (checks-rc10 block A). BCa: no fallback;
for H1 and H1a the acceleration is ≈ 0.153 and the upper adjusted quantiles are 99.68% and
99.71% (ranks 9 968 and 9 971 of 10 000), so the upper bounds carry Monte-Carlo noise.

**What changes and why.** The session-hours grow ×30 in treatment and ×18 in control. Three
sessions start in the window and last longer than one epoch; counted at their start, their whole
span lands in one epoch:

| session | start epoch (arm) | span | episodes | epochs touched |
|---|---|---:|---:|---:|
| `d37a5964` | 09-08 (treatment, `w = 2`) | 240.42 h | 60 | 11 |
| `74de1e72` | 09-12 (treatment) | 81.01 h | 67 | 2 |
| `ce6f5640` | 09-11 (control) | 54.00 h | 2 | 2 |

`09-08` holds 240.75 h (74% of treatment exposure), `09-12` 81.37 h, `09-11` 54.31 h; the other
sixteen epochs 0.23–0.62 h. Three more sessions have episodes in more than one epoch but start
outside the window (`1a5d8840` on 08-27, with 49 episodes reaching into 09-02…09-07; two in
August only) and leave the analysis. Episodes also change epoch and arm, so opportunities and
repeats move and H1c moves a little (−0.0121 → −0.0140).

**The own stratum (PREREG §2: sessions longer than one epoch).** The three sessions above hold
321.43 h, 139.96 weighted opportunities and 6.00 weighted repeats in treatment and 54.00 h, 0
opportunities and 0 repeats in control (v3 minus 'without'). Two treatment sessions and one
control session. No standalone inferential interval or test is reported for this stratum. The
descriptive per-hour contrasts (6.00 / 321.43 and 139.96 / 321.43 in treatment against 0 / 54.00
in control) are reported in the manuscript (§4); H1c cannot be contrasted because control has no
eligible opportunities. They are listed, and the with/without sensitivity is the registered way to see
their weight. *(Corrected 2026-10-05, rc13: this sentence read "no within-stratum contrast is
estimable", which the descriptive differences reported since rc11 contradict. No number
changed.)* *(Corrected again 2026-10-05, rc15 (review of rc14, Codex C4): it read "no within-stratum
inferential contrast (interval or test) is estimable"; an interval or test is not reported, which
is not the same as not estimable. No number changed.)*

## Multiplicity under both readings (`multiplicidade`)

Deposited reading: H1 primary, alone at α = 0.05; Holm over H1a, H1b, H1c, H2 time, H2 tokens
(m = 5 with H1b as p = 1; m = 4 without H1b). Switch reading: H1c primary; H1 joins the Holm
family (m = 6 / 5); variant with H1c tested alone and the rest in Holm (m = 5 / 4).

| leg | deposited: H1 alone | deposited Holm, H1a (m = 5 / 4) | switch, H1 (m = 6 / 5) | switch, H1c alone: H1 (m = 5 / 4) | anything rejects in a Holm family? |
|---|---|---|---|---|---|
| **v3 registered** | p 0.3294 → **no** | 1.0 / 1.0 | 1.0 / 1.0 | 1.0 / 1.0 | no |
| v3 'without' | p 0.1957 → no | 0.7505 / 0.6004 | 0.9785 / 0.7828 | 0.7828 / 0.6004 | no |
| rc9 (v2-equivalent) | p 0.0302 → **rejects** | 0.0840 / 0.0672 | 0.151 / 0.1208 | 0.1208 / 0.0906 | no |
| rc8 (v1-equivalent) | p 0.0133 → **rejects** | 0.1205 / 0.0964 | 0.0798 / 0.0665 | 0.0665 / 0.0532 | no |
| sensitivity (rc7 analysis) | p 0.0127 → **rejects** | 0.4275 / 0.342 | 0.0762 / 0.0635 | 0.0635 / 0.0508 | no |

H1c is not rejected under either reading in any leg (v3: p 0.4006; Holm-adjusted 1.0). H2 (v3):
time p 0.8285, tokens p 0.3372, Holm-adjusted 1.0; winsorized time +0.316 [+0.011; +0.690] and
raw tokens +5 533 [+740; +12 282] are intervals that exclude zero in the direction of a costlier
treatment, which the registered test does not reject. H2's population is 1 218 / 1 089 episodes
(v2: 1 172 / 1 115).

**Verdict change v2 → v3:** under the deposited reading H1 goes from rejecting (0.0302) to not
rejecting (0.3294); no interval of H1 or H1a excludes zero on any registered leg (locked,
pre-committed, post-hoc without `09-14`; checks-rc10 block A) nor on the 'without' sensitivity.
Under the switch nothing rejected in v2 and nothing rejects in v3.

## One switch at a time (`deltas_um_a_um`; others at the earlier choice; Δ on the point)

| switch alone | ΔH1 | ΔH1a | ΔH1c |
|---|---:|---:|---:|
| panel | −0.19 | −2.65 | −0.0009 |
| window (expiry + offsets) | −0.89 | −9.58 | −0.0000 |
| — expiry only | −0.05 | −0.42 | −0.0000 |
| — offsets only | −0.82 | −8.92 | 0 |
| BCa | 0 | 0 | 0 |
| epoch set (19, no `09-02`) | +1.61 | −4.80 | +0.0087 |
| washout out of the denominator | −7.33 | −78.34 | 0 |
| **sessions at their start** | **+13.07** | **+127.67** | −0.0022 |

Registered minus one switch (point, p): without the start-epoch switch, H1 −19.85 (0.0302), H1a
−233.20 (0.0168), H1c −0.0121 (0.434), i.e. v2 exactly; without any other single switch, H1 stays
in −1.58…−1.25 and H1a in −16.78…−14.84, none with p < 0.05 (the closest: without the epoch-set
switch, H1 p = 0.0985).

## Four-vote ties under v3 (checks-rc10 block C)

28 exact ties: 4 fall in the analysed exposure of treatment epochs, 7 of control, 9 in the
washout, 7 outside the trial dates, 1 before `09-03`'s exposure window; 1 tie belongs to a
straddling session. Four-vote H1c: −0.0140 under the paper's rule (equal to the registered
estimate), −0.0249 with every tie as `failure`.

## Side effect to know

`B-rc9/checks-rc9.py` no longer runs against the v3 script: it stops with `KeyError:
'v2_registrado'` (the new input is not in v2's provenance), and its next guard, which pins v2's
script sha256, would abort it anyway. To re-run it, point it at the frozen v2 copy
(`B-registered/estimador_itt_registrado-v2-ac9d2f05.py`) under the original module name. The
same holds for `B-rc8/checks-rc8.py` and the v1 copy (RESULTADO-v2.md).
