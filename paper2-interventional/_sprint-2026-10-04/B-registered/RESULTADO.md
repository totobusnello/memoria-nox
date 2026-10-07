# Paper B — the ITT analysis as registered (2026-10-05)

Decision of the author, 2026-10-05: the registered analysis is the reported analysis; the
analysis implemented in `estimador_itt.py` (locked output `ITT-2026-09-21.json`) becomes a
sensitivity leg.

- Script: `measurement/estimador_itt_registrado.py` (sha256 `c28b064f7fcd2f83…`). It does not
  modify `estimador_itt.py` or `rerandomizacao.py`; it imports their building blocks.
- Output: `out/ITT-REGISTRADO-2026-10-05.json`. Every leg, the one-at-a-time deltas, the Holm
  family, H2, and provenance (sha256 of the script, of the six imported modules and of every
  input; seed `20260921`; 10,000 replicates; re-randomization seed prefix
  `p2-rerand-2026-09-21`). Re-running it reproduces every field except `gerado_em` (checked).
- Inputs are read in place, read-only, from `~/Backups/paper2-ensaio-2026-09-21/` and
  `~/.paper2-verdicts/`. They are **not** copied here. The episode corpus and the panel's
  verdict reasons contain real work content, `extract_episodes.py` says they must never enter
  a public repo, and this repo is public. The JSON records their hashes instead. All of them
  match `MANIFESTO-LASTRO-P2.json`.

```
python3 measurement/estimador_itt_registrado.py --out out/ITT-REGISTRADO-2026-10-05.json
```

## 1. Validation

**(i) Control: same estimator.** With the four switches set to the current choices, the
script rebuilds both locked files **byte for byte**. It compares the sha256 at run time and
exits with status 2 on any mismatch:

| locked file | sha256 locked | sha256 rebuilt |
|---|---|---|
| `ITT-2026-09-21.json` (primary and the 09-14 sensitivity leg) | `19afa7cc2214bedd…` | `19afa7cc2214bedd…` |
| `RERANDOMIZACAO-2026-09-21.json` | `ee1d4e47a980c34b…` | `ee1d4e47a980c34b…` |

So any difference below comes from the switches. None of it comes from a reimplementation.

**(ii) One switch at a time.** All other switches stay at their current values. Δ is
switched minus current. p is the re-randomization p, two-sided.

| switch on | H1 point (Δ) | H1 p | H1a point (Δ) | H1a p | H1c point (Δ) | H1c CI | H1c p |
|---|---|---|---|---|---|---|---|
| none (current) | −14.622 | 0.0127 | −143.92 | 0.0855 | −0.01994 | [−0.0560; +0.0086] | 0.1603 |
| (1) panel substitution | −14.816 (−0.19) | 0.0126 | −146.57 (−2.6) | 0.0917 | −0.02084 (−0.0009) | [−0.0565; +0.0068] | 0.1475 |
| (2) window: expiry cut + offsets | −15.508 (−0.89) | 0.0058 | −153.50 (−9.6) | **0.0380** | −0.01998 (−0.00004) | [−0.0563; +0.0092] | 0.1649 |
| (2a) expiry cut only | −14.669 (−0.05) | 0.0127 | −144.35 (−0.4) | 0.0830 | −0.01998 (−0.00004) | [−0.0563; +0.0092] | 0.1649 |
| (2b) offsets only | −15.439 (−0.82) | 0.0057 | −152.84 (−8.9) | **0.0375** | −0.01994 (0) | [−0.0560; +0.0086] | 0.1603 |
| (3) BCa interval | −14.622 (0) | 0.0127 | −143.92 (0) | 0.0855 | −0.01994 (0) | [−0.0579; +0.0080] | 0.1603 |
| (4) 19-epoch set (09-02 out) | −13.011 (+1.61) | 0.0403 | −148.72 (−4.8) | 0.0778 | **−0.01128 (+0.0087)** | [−0.0434; +0.0144] | **0.4393** |

What moves what:
- **H1c is moved almost entirely by (4).** `09-02`, the epoch that served no brief, is a
  control epoch with H1c = 0.190 (94.3 weighted opportunities, 17.95 repeats). That is the
  second-highest per-epoch H1c of the twenty, after `09-17` at 0.209. Removing it shrinks
  the control rate from 0.0896 to 0.0796 and roughly halves the contrast.
- **The window switch acts on H1 and H1a almost entirely through the offsets (2b), not the
  expiry cut (2a).** The offsets only shrink the session-hour denominator: `09-01` goes from
  0.543 to 0.406 h (treatment) and `09-03` from 0.457 to 0.246 h (control). No opportunity
  falls in the cut-off stretches. The pre-exposure episodes are 40 in `09-01` and 84 in
  `09-03`, and all but four of them fall inside the washout.
- The expiry cut does what the reviewers measured. It removes 33 post-expiry episodes,
  5 opportunities (22.835 weighted) and 2 weighted repeats, and it takes `09-20` from 0.6235
  to 0.5154 session-hours. It is negligible on every hypothesis.
- The panel switch reproduces Codex's figures. The three families resolve 1,159 of 1,195
  episodes (36 unknown). Substitution resolves 20 more (1,179; 16 unknown), 13 of them as
  failure, and gives H1c = −0.020843. A guard checks that no episode the three families had
  resolved changes verdict: 0 do.
- BCa changes only intervals. H1 and H1a get wider and shift away from zero, because z0 and
  the acceleration are both negative. The H1c interval barely moves.

The JSON also holds the reverse decomposition (registered minus one switch,
`deltas_registrado_menos_um`). It tells the same story: removing (4) from the registered
analysis puts H1c back at −0.0209 (p 0.152), and removing (2) puts H1a's p back at 0.0785.

## 2. Current vs registered

Current = `estimador_itt.py` (3-family panel, epoch dates 09-01..09-20, percentile, 20
epochs). Registered = §10.31 substitution, expiry cut + SPEC §2 offsets, BCa with the
leave-one-epoch-out jackknife stratified by arm, 19 epochs. Bootstrap: 10,000 replicates,
seed 20260921, both arms resampled separately. BCa never fell back to percentile in any leg.

| | current | **registered** |
|---|---|---|
| epochs T / C | 11 / 9 | **11 / 8** (`09-02` counted, excluded) |
| session-hours T / C | 12.70 / 5.16 | **12.56 / 4.33** |
| opportunities (weighted) T / C | 1,103.75 / 1,191.14 | **1,138.47 / 1,101.75** |
| repeated failures (weighted) T / C | 76.84 / 106.67 | **76.84 / 87.72** |
| unknown share of opportunities (10% rule) | 1.34% | **1.02%**, rule does not fire |
| **H1** repeats/session-hour | −14.62 [−20.51; −4.79], p 0.0127 | **−14.12 [−22.15; −7.04] BCa, p 0.0133** |
| **H1a** opportunities/session-hour | −143.92 [−209.80; −15.34], p 0.0855 | **−163.52 [−282.29; −61.12] BCa, p 0.0241** |
| H1b | unevaluable (§10.32) | unevaluable (§10.32) |
| **H1c** repeats/opportunity | −0.0199 [−0.0560; +0.0086], p 0.160 | **−0.0121 [−0.0445; +0.0125] BCa, p 0.434** |
| T / C H1c | 0.0696 / 0.0896 | **0.0675 / 0.0796** |
| **H2 time** (s, winsorized at 7.45) | — not in paper | **+0.284 [−0.030; +0.666] BCa**; raw −1.13 [−5.35; +0.85]; p(raw) 0.831 |
| **H2 tokens** (winsorized at 65,206) | — not in paper | **+2,141 [−1,380; +6,230] BCa**; raw +2,420 [−2,404; +7,760]; p(raw) 0.684 |

The unequal-voiding trigger (PREREG §5: realized arm sizes differ by more than 5 epochs)
does not fire at 11/8. The stratified interval stays the only interval.

### Verdicts

| hypothesis | decision rule (PREREG §5 l.1025) | current | registered | changes? |
|---|---|---|---|---|
| H1 | alone, α = 0.05 | rejects (p 0.0127) | rejects (p 0.0133) | no |
| H1a | Holm family | does not reject (adj. p 0.43 with m=5; 0.34 with m=4) | does not reject (adj. p **0.1205** with m=5; **0.0964** with m=4) | no |
| H1c | Holm family; primary per PROSPECTIVE-ESTIMAND §3-bis | does not reject (raw 0.160) | does not reject (raw 0.434) | no |
| H2 time / tokens | Holm family | not computed | does not reject (raw 0.831 / 0.684) | — |
| Holm family as a whole | | no rejection | no rejection | no |

**No registered verdict changes.** One thing could flip if read the wrong way. H1a's
**unadjusted** p falls below 0.05 (0.0855 → 0.0241), and its CI excludes zero in both
analyses. But H1a is registered inside the Holm family, and its Holm-adjusted p stays above
0.05 in both variants. Reporting 0.0241 as a rejection would apply a decision rule the
registration does not contain. The same caution applies to the earlier warning
(DEVIATIONS §10.33): an interval that excludes zero on a rate whose denominator is
session-hours depends on `09-14`'s sparse session.

Holm variants. Variant A keeps the registered family size, m = 5: H1a, H1b, H1c, H2-time
and H2-tokens. The unevaluable H1b enters as p = 1, so it cannot reject. Variant B drops H1b
(m = 4). The two give the same verdicts.

## 3. What could not be implemented as written

1. **"acceleration from the leave-one-epoch-out jackknife over all 234 epochs"** (PREREG
   l.997). Only 19 epochs were realised. The jackknife runs over the 19 analysis epochs
   (20 for legs that keep `09-02`), each deletion inside its own arm. The lower adjusted
   quantiles are extreme: α₁ = 0.0017 (H1) and 0.0009 (H1a). At 10,000 replicates the
   lower BCa bound of H1/H1a is therefore the 18th or 9th smallest replicate (0-based index
   17 / 8), and it carries visible Monte-Carlo noise. Percentile was never needed as a fallback. The script also
   treats an infinite z0 as a fallback trigger. The registration does not list that trigger,
   and it never fired.
2. **"incluída, com offset"** (SPEC §2, for `09-01`, `09-03` and `09-20`). The ratio
   estimator has no offset term; only the secondary GLM in PREREG §5 does. The offsets are
   implemented as exposure windows on the timestamp axis: episodes outside the window leave
   both the numerator and the session-hour denominator. The windows are read from
   `p2-serving.ndjson` and asserted against the quoted values:
   - `09-01` starts at the first `active` record, 10:37:01.943Z. The spec says "offset sobre
     a exposição tratada (630 briefs / 22,38 h)".
   - `09-03` starts at the first served record, 17:23:39.777Z, which is the end of the outage
     in `INCIDENT-2026-09-02`. The spec gives only a volume, "441/672", and no clock
     interval. So the volume offset is realised as the uptime window; that is an
     interpretation.
   - `09-20` ends at 22:51:23Z.

   The a_past corpus (condition (i)) is never cut.
3. **Panel.** PREREG §676–695 locks a **three-family** live panel and names the fourth
   family only as a mitigation "not adopted here". The substitution rule is the §10.31
   deviation, implemented verbatim as the author directed (quoted in the script docstring).
   §10.31 calls its own predecessor decision post hoc, because it was taken after counting
   ties. That provenance travels with the rule.
4. **Multiplicity after the primary was switched.** PREREG l.1025 tests H1 alone and puts
   H1a–c + H2 in a Holm family. PROSPECTIVE-ESTIMAND §3-bis (2026-08-30, before assignment)
   promotes H1c to primary and H1/H1a/H1b to secondary, without restating the multiplicity
   rule. Both readings are reported, and they agree: H1c does not reject under either.
5. **H2 has three choices the registration does not fix.** They are declared in the JSON
   and made arm-blind:
   - (a) "best known resolution" is the minimum over successful (`not is_error`) episodes of
     the same `sig_primary`, with at least 5 such episodes, computed over the whole locked
     corpus (5,951 episodes, 08-23..09-21) with both arms pooled;
   - (b) the population is every post-washout action in the analysis epochs, not only the
     opportunities;
   - (c) the effect is the difference of per-arm means pooled over episodes, with the same
     epoch bootstrap/BCa as H1, and the sharp-null statistic is the per-epoch raw mean,
     trend-residualized like every §5 permutation outcome.

   Everything else is as locked: the instrument (`task_regret.py` pairing and token
   accounting) and the winsorization at the locked p95 (7.45 s / 65,206 tokens), applied to
   the estimator only, with the raw values used for the test (PREREG §4.2, LOCKED
   2026-08-15).
6. **Out of scope, not computed here.** These parts of §5 are not among the four
   divergences and were not computed: the secondary NB/binomial mixed model, the lag-1 and
   A→B co-estimates, and the Appendix-B bounds. SPEC §8 lists the rest as unevaluable at
   K=19: TOST, dose-response, leave-one-agent-out, and first vs second half. The bootstrap
   still does not re-draw the stratum-B sample. That is a known missing variance component,
   unchanged from the current analysis.

## 4. H2 and H3

**H2 (task regret, secondary confirmatory): instantiated now, computable, computed.** No
regret pipeline had ever been run on trial data. `task_regret.py` was run once, in August,
on the pilot corpus, to lock the p95, and the paper has no H2. The locked backup does hold
what it needs: `action-archive/` (715 transcripts) pairs **5,951/5,951** `tool_use` /
`tool_result` events onto the locked corpus by `episode_id`, with 0 orphans in either
direction, 0 `sig_primary` divergences and 0 missing `usage`. 37 signatures have a floor (at
least 5 successful episodes); 5,875 episodes carry regret. Result: H2 does not reject for
either component (table in §2). Note the sign split on time: the winsorized estimate is
**+0.28 s**, treatment slower, while the raw one is **−1.13 s**. The raw tail is heavier in
control.

**H3 (retrieval-metric ordering, exploratory): not computable.** nDCG@10 and recall@10
need graded relevance judgments per (query, item), and none were ever defined or collected
for the served briefs. A grep over `paper2-interventional/` finds nDCG only in prose and in
Paper A, never in a script or artifact over trial briefs. The briefs are push context, not
answers to a query. Paper A states the consequence itself: an item no query reaches has an
undefined nDCG, not a low one. The served chunk ids do exist for both arms in
`p2-serving.ndjson` (5,166 control and 7,763 treatment rows in the window, all with
`ids_controle`). So what is missing is not the brief but its relevance label. Building one
now, for example "relevant = a chunk whose signature the session later acted on", would be
a new estimator defined after unblinding. That is exploratory by PREREG §5's deviation
protocol, not H3 as registered. SPEC §8 had already listed "dose-resposta / H3" as
unevaluable at n=1 on the top dose. Appendix A also requires the 95% coverage floor and
per-brief metrics that were never logged.
