# Is the 2 h washout enough? — exploratory analysis, 2026-08-14

> ⚠️ **Exploratory, not pre-specified.** It does not enter the study outcome and
> changes no `pilot_replay` number. It exists to unblock a design decision:
> `SIZING-2026-08-14-v2.md` §4 shows that shortening the epoch is the only lever
> that buys calendar without selling MDE (24 h→242 d, 8 h→113 d), but the
> washout is **fixed at 2 h** — costing 8% of a 24 h epoch and 25% of an 8 h one
> — and the premise that 2 h suffices had never been verified.

## Short answer

**Yes, for the boundary effect that exists without treatment.** The anomaly is
concentrated in the first two hours and the baseline level is already reached by
2–4 h. A 2 h washout captures the whole phenomenon, with little slack and little
waste.

This does **not** on its own license a short epoch — see §4.

## 1. Where the effect is: error incidence

`is_error` is a **census** — no sampling, no weighting, no composition that could
confound. It is the clean test.

| zone | n | `is_error` rate | 95% CI |
|---|---|---|---|
| **0–2 h** | 2,090 | **10.67%** | [9.42% ; 12.07%] |
| 2–4 h | 1,616 | 6.68% | [5.57% ; 8.01%] |
| 4–6 h | 1,112 | 4.50% | [3.43% ; 5.88%] |
| 6–12 h | 2,614 | 6.69% | [5.80% ; 7.72%] |
| 12–24 h | 2,147 | 6.61% | [5.64% ; 7.74%] |

0–2 h against everything else: **10.67% vs 6.34%**, difference **+4.33 pp**,
95% CI **[+2.89 ; +5.76]**, not crossing zero.

The epoch boundary is **not a neutral point**: 68% more errors occur in the first
two hours. And the effect **ends there** — 2–4 h (6.68%) is already
indistinguishable from 12–24 h (6.61%). The washout is well calibrated: neither
too short nor generous.

The 4–6 h bin (4.50%) falls *below* baseline, with its CI almost touching it. I
have no explanation and will not invent one; with n=1,112 and five bins
inspected, it is the kind of thing that appears by chance.

## 2. A trap I fell into, and why it stays on the record

The first reading of this analysis compared aggregate `p0` across zones and
concluded there was a boundary effect: **0.397 in 0–2 h against 0.316 in 2 h+**,
difference CI [+0.026 ; +0.136], not crossing zero. It looked clean.

It was wrong. The **composition** varies across zones:

| zone | % stratum A | `p0` in A | `p0` in B |
|---|---|---|---|
| 0–2 h | **37.5%** | 0.967 (n=151) | 0.056 (n=252) |
| 2–6 h | 30.5% | 0.880 (n=108) | 0.037 (n=246) |
| 6 h+ | 29.8% | 0.960 (n=227) | 0.056 (n=534) |

With `p0_A ≈ 0.96` against `p0_B ≈ 0.05`, a 7-point difference in the share of A
moves the aggregate on its own. Applying the 2 h+ composition to the 0–2 h zone:
`0.30 × 0.967 + 0.70 × 0.056 = 0.329`, against the 0.316 observed. **The effect
vanishes.** Within each stratum there is no gradient at all.

The aggregate remains in the script's output, flagged
`testes_confundidos_NAO_USAR` ("confounded tests — DO NOT USE"), rather than
removed: whoever reproduces this needs to see the trap, not a clean result that
hides that it existed.

Note that the composition varying **is** the §1 finding seen from another angle:
there is more stratum A in 0–2 h *because* more errors happen in 0–2 h. The
signal was real; it was the estimator that was wrong.

## 3. And `p0`?

There is no `p0` gradient within stratum. What changes near the boundary is **how
many errors happen**, not **how often a known error repeats**. These are
different things, and only the second is the study's outcome.

## 4. What this does NOT authorise

**In the replay corpus every epoch is control — no arm switch ever occurred.**
This therefore does not measure treatment carry-over. It measures the
intra-epoch temporal structure in the absence of intervention: work rhythm,
sessions crossing the boundary, time zone.

The logic is asymmetric, and the direction must be explicit:

- A gradient here **would prove** that 2 h is not enough even without treatment.
- The absence of a gradient **does not prove** that it is enough under treatment.

What this result does is remove an objection, not grant a licence. The premise
"2 h washes out the previous arm's effect" remains without direct evidence — all
that is now known is that it is not being contradicted by the system's natural
behaviour.

For short epochs specifically: since the natural boundary effect lasts under
2 h, a 2 h washout still captures it in 8 h or 6 h epochs. What worsens is not
sufficiency but **cost** — 25% of the epoch at 8 h, 33% at 6 h — and the sizing
document's §4 table already models that.

## 5. Reproduction

```
python3 washout_sensitivity.py \
  --episodes universo-combinado.jsonl \
  --verdicts verdicts-combinado-v2.jsonl \
  --estrato-b-ids estrato-b-ids.txt \
  --replicas 'tiebreak-rep*.jsonl' 'tiebreak-v2-rep*.jsonl' 'extensao-moonshot-cycle-*.jsonl'
```

Corpus: 9,579 episodes, 30 epochs, 7,184 `(episode, panelist)` pairs. Proportion
tests run on **raw** counts — the HT weight amplifies stratum B by ~5.2× and
would inflate any `n` used in a test, manufacturing significance where there is
none.
