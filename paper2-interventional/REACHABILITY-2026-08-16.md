# Dose reachability — 2026-08-16

> **Pre-treatment measurement over the historical corpus.** No arm assignment
> exists; the study has not started. This document changes no locked number by
> itself. It supplies the input Sec. 1 needs in order to state a hypothesis the
> design can actually test.
>
> **What it is not:** a decision. The decisions remain the principal's.

---

## 1. Why this was measured

A whole-package review (Codex, 2026-08-16) observed that Sec. 1's H1 is stated on
the **unconditional** repeated-failure density and sized for a **30% relative**
change in it, while the locked treatment can only act on failures of severity S2
and above. Four earlier block-level reviews had each confirmed a constraint —
two coverage slots, first admission only, S1 out of reach, reach decaying with
chunk age — and none took the sum.

The sum is the finding. Each constraint was declared honestly; together they
bound the maximum achievable effect below the effect the study is powered to
detect.

## 2. What was measured, and how it is tied to the canonical estimator

`reachable_share.py` walks the **same opportunity set** the canonical replay
produces — same washout, same stratification, same Horvitz–Thompson weights — and
asks, for each opportunity, whether the treatment could have displaced anything.

**The validation that matters:** the script reports `r_hat_irrestrito` =
**28.6486**, identical to the canonical `r̂` = 28.648576 from
`SIZING-2026-08-14-v2.md`. What follows is not a parallel calculation; it is the
same study viewed along another axis.

Reachability needs two properties of the **matched past failure** `a_past`:

| | |
|---|---|
| **severity** | consolidated panel level — sets `pain` on the written chunk, hence the boost `w × Δ_cut × sev` |
| **age** | age of that chunk at the opportunity — sets the baseline through the 0.15-weighted recency term |

An opportunity is reachable at dose `w` iff `w ≥ w_min(sev, age)`, with `w_min`
exactly as Sec. 2 publishes it.

**Two modelling choices, both declared.** (a) The **most recent** prior failure
governs, not the first: `pilot_replay.py` keeps the earliest only because
condition (i) asks whether *any* qualifying failure exists, but the design writes
a chunk per adjudicated-failure episode, so the freshest matching chunk is the
one competing for a slot. Using the first would age every chunk artificially and
understate reach. (b) Severity is the panel's **lower median** for even counts,
matching the strict-majority rule applied to the binary verdict (correction of
2026-07-29); the upper median would inflate the term that carries the dose.

## 3. What the corpus is made of

| | |
|---|---|
| Opportunities (HT-weighted) | 4,457.77 over 155.6 session-hours |
| Repeats (HT-weighted) | 519.14 |
| Severity of `a_past` | **S1 77.07% · S2 22.93% · S3 0% · S4 0%** |
| Age of `a_past` | median **2.42 d** · p25 1.92 · p75 4.11 · max 25.83 |
| `a_past` with no consolidated severity | 0 |

Two things follow immediately. **S3 and S4 do not occur** among matched past
failures, so the severity axis in practice has two values, not four. And **age is
not the binding constraint**: at a median of 2.42 days almost every chunk sits
well inside the 6.66-day cliff Sec. 2 publishes. What binds is severity.

## 4. Reach is a step function with two cliffs

| dose `w` | reach | ceiling on unconditional effect | `r̂` restricted |
|---|---|---|---|
| 0.5 | **0.00%** | 0.00% | 0.0000 |
| 1.0 | **0.00%** | 0.00% | 0.0000 |
| **2.0** | 19.66% | **17.56%** | 5.6324 |
| 4.0 | 22.93% | 21.19% | 6.5688 |
| 6.0 | 22.93% | 21.19% | 6.5688 |
| **8.0** | **100.00%** | **100.00%** | **28.6486** |
| 10.0 | 100.00% | 100.00% | 28.6486 |

The "ceiling on unconditional effect" is the share of *repeats* the dose can
touch: if the treatment removed 100% of what it reaches, H1's outcome would fall
by that much and no more.

Dose required, by severity and age:

| age | S1 | S2 |
|---|---|---|
| 1 d | 6.03 | 1.85 |
| **2.42 d (median)** | **6.10** | **1.89** |
| 4.11 d (p75) | 6.19 | 1.93 |
| 25.83 d (max) | 7.29 | 2.48 |

## 5. Three consequences for the locked design

**(1) The locked MDE is above the physical ceiling.** MDE is 30% relative; at
`w = 2.0`, the maximum achievable is **17.56%**. Even with total efficacy on
everything it reaches, the treatment cannot produce the effect the study is
powered to detect. This is not a power problem — it is a ceiling below the
threshold.

**(2) Two of the three locked doses have a ceiling of exactly zero.** Sec. 2
pre-commits the mechanism's signature as *"a step between `w = 1.0` and
`w = 2.0`, concentrated in S2 episodes"*. Measured, that is not a point on a
dose–response curve: `w = 0.5` and `w = 1.0` cannot move anything at all. **The
predicted step would appear even if the mechanism did not exist**, because the
two lower arms are structurally inert. A pre-committed reading rule that a null
mechanism satisfies is not a reading rule.

**(3) Restricting the primary to the reachable set is exact but not viable.**
Sizing on `r̂` = 5.6324 and `p̂0` = 0.104 at the ICC's upper limit gives **984
epochs** at MDE 30% — 2.7 years — because restricting cuts `r̂` fivefold and `r̂`
is the exposure denominator.

## 6. The property that changes the comparison

**At `w ≈ 8`, `r̂` restricted returns to 28.6486 — identical to unrestricted.**
The restriction dissolves because nothing is left outside it.

The 984 epochs were never the price of conditioning the hypothesis. They were the
price of conditioning it on **19.66%**. With a dose that reaches the whole
opportunity set, H1 stays unconditional, the ceiling becomes 100% against an MDE
of 30%, and `N_epochs` returns to **174**.

## 7. What this costs, stated plainly

`w = 8` is `W_OUTCOME = 0.344` — eight times the entire top-10 spread. That is
not the nudge Sec. 2 describes; it is a policy of *"a matching recent failure
goes to the top of the brief."* The treatment stops being "subtly reweight the
ranking" and becomes "always surface the matching failure", and Sec. 1's
interpretation has to follow.

The argument for accepting that: a weak-dose experiment returning a null teaches
nothing, because it cannot separate *"outcome weighting does not work"* from
*"almost nothing was exposed to it."* Establishing that the mechanism moves
behaviour at all is the prerequisite for a dose-finding study, not a substitute
for one.

## 7-bis. Measured after §7 — and it dissolves the trade-off

Two further measurements were run, in this order, and the second reverses the
recommendation the first supported.

**(a) How many chunks are boosted at the same time.** `dose_reach.mjs` reports
that at `w = 6` and `w = 8` all ten brief slots are displaceable, and that the
pool of chunks able to clear the cut grows roughly tenfold (43 → 429 for S2). But
that script counts chunks that *would* cross **if boosted**, and only signature
matches are boosted. Measuring the actual simultaneous count, per opportunity:

| dose | 0 boosted | 1 | 2 | ≥9 boosted |
|---|---|---|---|---|
| `w = 2.0` (locked) | 42.5% | 18.0% | 11.7% | 5.7% |
| `w = 6.0` | 22.2% | 21.9% | 21.5% | 17.6% |
| `w = 8.0` | 0% | 14.3% | 3.5% | **46.1%** |

At `w = 8`, **46% of opportunities would boost nine or more chunks into a
ten-slot brief**. The treated brief stops being a reweighted ranking and becomes
failure-lessons-only; any effect measured would be confounded with the agent
having lost its other context. **The high-dose recommendation of §7 dies here.**

**(b) Which chunk the treatment designates.** Everything above assumed the
*most recent* matching failure is the one boosted. That was never specified — it
falls under the open item "which component performs the write". Designating
instead the chunk that is **easiest to reach** (highest severity for its age),
and boosting **exactly one per opportunity**:

| dose | reach, most-recent | reach, best-match | ceiling, best-match |
|---|---|---|---|
| 1.0 | 0.00% | 0.00% | 0.00% |
| **2.0 (already locked)** | 19.66% | **57.46%** | **60.18%** |
| 3.0–6.0 | 22.93% | 77.81% | 75.62% |
| 8.0 | 100.00% | 100.00% | 100.00% |

**At `w = 2.0` — a dose that is already locked — the ceiling rises from 17.56% to
60.18%, twice the 30% MDE.** And boosting exactly one chunk makes the saturation
of (a) impossible by construction: one slot, never nine.

So the trade-off between "reaches too little" and "saturates the brief" was not a
property of the mechanism. It was a consequence of an unspecified choice —
*which* matching chunk gets the boost — that the document had already listed as
open, and whose default nobody had examined.

**What this suggests, without locking it:** keep the dose band, add the rule that
the treatment boosts exactly one designated chunk per opportunity — the
easiest-to-reach match. `N_epochs` stays 174, H1 stays unconditional, and the
brief stays diverse. The dose-response band still needs revisiting on its own
terms: `w = 0.5` and `w = 1.0` reach nothing under either policy, so two of the
three arms remain structurally inert.

## 8. Open, and not settled here

- **The band is a proposal, not a lock.** `w ∈ {2.0, 6.0, 8.0}` gives reaches of
  19.66% / 22.93% / 100% — three distinct plateaus with a named mechanism at
  each: fresh S2, all S2, S1 enters. Whether to adopt it is the principal's.
- **Displacement at the new dose is unmeasured.** A chunk rising by 0.344 pushes
  something out of ten slots, and what leaves has not been measured.
  `dose_reach.mjs` already computes `displaceable`; it must be run on the
  production store with the candidate band **before** any band is locked.
- **S3/S4 are absent from this corpus**, so the severity gradient is untested at
  the top of the scale. A future corpus containing them would change the reach
  table, in the favourable direction.

## 9. Provenance

`reachable_share.py`, run over the consolidated corpus (9,579 episodes, 30
epochs) with the instability rule of `STABILITY-TEST.md` §9.2 active. Output:
`REACHABILITY-2026-08-16.json`. Verdicts and episode corpus are held outside the
repository — see `EXTERNAL-REFERENCES.md`.
