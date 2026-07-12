# OSF Pre-Registration — DRAFT v0.2 (NOT LOCKED)

> **Status:** working draft, 2026-07-12. v0.1 was adversarially reviewed by GLM-5.2 same day (5 FATAL / 7 GRAVE / 10 minor — full verdict in `REVIEWS-PREREG.md`); v0.2 incorporates every fix that does not depend on the route decision. **Route decided 2026-07-12 (Toto): Route 2-lite** (§0). Locking now blocked only on the **[TO LOCK]** items (§9). This document becomes binding only when registered on OSF with a public timestamp **before** any A/B data collection.
> **Companion docs:** `CONCEPT-NOTE.md` · `METHODOLOGY.md` · `DECISIONS.md` · `REVIEWS-PREREG.md`.

---

## 0. Route decision — ✅ DECIDED: Route 2-lite (Toto, 2026-07-12)

The v0.1 design (cluster = agent × time-block + washout over a *shared* store) does **not** neutralize cross-arm interference: treated sessions write content that control sessions later read, and agents in different arms co-exist on the store in real time (F1). Three defensible routes:

| Route | Claim retained | Design change | Cost | Venue fit |
|---|---|---|---|---|
| **1 — Conservative** | No point-identified causal claim; replay = main contribution, A/B = qualitative fidelity check | None | Low | COLM/EMNLP resource |
| **2 — Clean redesign** | Full causal claim | Arm switch per **whole agent-fleet epoch** with **per-arm store state** (snapshot/flush between epochs) | High (ops) | COLM full / NeurIPS D&B |
| **3 — Formal analysis** | Causal claim **as bounds**, not point | Keep design; potential-outcomes estimand + interference bounds (Aronow–Samii-style) + restricted co-estimands | Medium | COLM (D&B risky) |

**DECIDED — Route 2-lite** (Toto, 2026-07-12): keep the crossover but make the *epoch* fleet-wide (all 6 agents switch arm together per time-block, so no cross-agent arm mixing exists at any instant) and add a **store snapshot at each epoch boundary**: each arm's briefs are served from the snapshot taken at its epoch start (serving-side freeze), while writes continue to the live store for production safety. This removes simultaneous cross-arm contamination (all agents same arm) and bounds carry-over to the snapshot boundary; residual carry-over (behavior in epoch *k* shaping the snapshot of epoch *k+1*) is handled by the first-epoch-after-washout estimand + A-B-A-B sensitivity (§5). Rationale vs. alternatives: Route 1 gives up the causal claim the paper needs for COLM full / D&B; Route 3 leaves F1/F4 indefensible per the GLM verdict; full Route 2 (per-arm store with write flush) buys little over 2-lite at much higher operational risk to production. Route 1 remains the documented **fallback** if the snapshot mechanism proves operationally infeasible — the design below degrades to it by dropping §1-H1's causal phrasing.

**Engineering prerequisite created by this decision:** the **serving-side snapshot mechanism** (brief served from epoch-start snapshot; writes untouched) — spec item §9.3, to be implemented and shadow-validated in nox-mem before the pilot.

## 1. Study Information

**Title:** Does outcome-weighted memory reduce repeated failures in live LLM agents? A pre-registered fleet-epoch randomized crossover experiment.

**Authors:** Luiz Antonio Busnello (Independent Researcher) + external auditor(s) **[TO LOCK: named]** + independent data monitor **[TO LOCK: named, distinct from auditor]**.

**Description.** Six production LLM agents share a persistent memory system (nox-mem, in production since 2026-03). Each session receives a memory *brief* at start. We test whether weighting brief composition by **episode outcome** (adjudicated failure severity of past actions) changes repeated-failure behavior relative to the production flat/salience-only policy. This randomized arm is the **only** component of the project for which causal language is used; the retrospective benchmark is a declared observational log study, out of scope here (§8).

**Hypotheses.** All confirmatory tests are **two-sided**; expected directions are stated as expectations, not test choices (G2 fix).

- **H1 (primary, confirmatory):** the **unconditional repeated-failure density** (repeated failures per session-hour, §4.1) *differs* between arms. Expected direction: lower under treatment.
- **H1a–c (co-primary family, Holm-corrected; F2 fix):** (a) eligible-opportunity rate per session-hour; (b) repeat-attempt rate given opportunity; (c) repeated-failure rate given opportunity. Reported jointly so a change in the denominator cannot masquerade as (or mask) an effect in the conditional rate.
- **H2 (secondary, confirmatory):** task regret (§4.2) differs between arms.
- **H3 (exploratory, declared):** retrieval metrics (nDCG@10, recall@10) computed on the same briefs do not order the policies the way H1 does. **Figure specs for H3 are pre-committed in Appendix A before unblinding** (M5); no confirmatory claim from H3.

## 2. Design Plan

**Study type.** Randomized crossover on live production traffic, **fleet-wide epochs**: all 6 agents are in the same arm at any instant (kills simultaneous cross-arm contamination by construction).

**Randomization unit.** **Epoch** = fleet × time-block of **[TO LOCK: 24h, boundary 06:00 BRT]**. Epochs assigned to arm by constrained randomization balancing weekday/weekend and calendar halves. The assignment sequence is generated once from a seed **created and held by the independent data monitor** (not the authors), committed to OSF before the first treatment epoch (M4).

**Estimand (potential outcomes; G4 fix).** For session-hour unit *i* in epoch *k*, let `Y_i(a, S_k)` be the outcome under arm `a ∈ {0,1}` with serving snapshot `S_k`. The estimand is the average serving-policy effect
`τ = E[ Y_i(1, S_k) − Y_i(0, S_k) ]`
over the realized snapshot sequence — i.e., the effect of *which chunks are served*, with the write path identical in both arms and snapshots evolving under the realized mixed history. This is a **policy effect along the realized trajectory**, not the effect of deploying the treatment permanently; that broader estimand is declared out of reach of this design and is not claimed.

**Interference handling (F1 fix, layered):**
1. **No simultaneous mixing:** fleet-wide epochs — at no instant do treated and control sessions coexist.
2. **Serving-side snapshot:** briefs in epoch *k* are served from snapshot `S_k` (store state at epoch start, post-washout); writes continue to the live store untouched. Carry-over is thus confined to *content* differences between successive snapshots.
3. **Washout:** first **[TO LOCK: 2h]** of each epoch excluded from analysis; boundary-straddling sessions assigned to the epoch of their start, flagged, sensitivity with/without.
4. **Primary carry-over guard:** the primary analysis set is **all post-washout session-hours**; a pre-committed co-estimate restricts to epochs whose *predecessor was control* (A→B transitions), isolating treatment effects from treatment-shaped snapshots (F4/GLM fix #1).
5. **Quantitative sensitivity (G6):** pre-committed co-estimates — (i) A→B-restricted (above); (ii) lag-1-adjusted regression (predecessor arm as covariate); (iii) partial-identification bounds under bounded-interference assumptions (Aronow–Samii-style, bound parameter reported, math in Appendix B **[TO LOCK: appendix written]**). All three reported alongside the primary.

**Arms.**
- **Control:** production brief policy at freeze commit **[TO LOCK: hash]** (`NOX_BRIEF_DIVERSITY=active`).
- **Treatment:** identical + additive outcome-weighted term `W_OUTCOME × severity` on chunks linked to adjudicated-failure episodes **[TO LOCK: W_OUTCOME, proposed 0.15; sensitivity {0.10, 0.15, 0.20} pre-registered as secondary]** (additive per the Paper-1 v3.4 lesson: multiplicative boosts are unstable).
- **Scope:** low-stakes sessions only, per pre-committed task-type allowlist **[TO LOCK]**; high-stakes sessions always get control and are excluded (this exclusion is arm-independent by construction).

**Blinding.** Outcome adjudication blind to arm: adjudicators receive episodes with arm labels, sub-day timestamps, and policy metadata stripped. The trace→action→outcome→failure pipeline is deterministic, frozen at commit **[TO LOCK]**, validated end-to-end on a **synthetic input set with committed expected-output hash** (M2), and signed off by the external auditor before arm labels are unblinded for analysis.

**Ethics (M1).** Human adjudicators are research contributors, not subjects of intervention; their participation is documented with consent. The agents' users are the authors themselves (own production system); no third-party user data enters the benchmark un-hashed. Low-stakes restriction + safety abort (§3) bound operational harm. IRB: independent-researcher exemption status stated at lock **[TO LOCK: statement]**.

## 3. Sampling Plan

**Existing data.** Registration precedes all treatment-arm traffic. Historical logs are used only for (a) operational definitions, (b) the **pre-registered pilot** below, (c) the separate observational benchmark.

**Pre-registered pilot (F5 fix).** Before the pilot runs, we lock: the pilot's own metric definitions (`r̂` = opportunity rate/session-hour, `p̂0` = control conditional repeat rate, ICC estimate), the executable sizing script (committed, seeded), and the **deterministic function** `N_epochs = f(r̂, p̂0, ICC, MDE)`. The pilot is replay-only (no live arms). After the pilot, `f` is evaluated once and its output locked — no re-runs, no post-hoc MDE shopping.

**Sample size & power (G1 fix).** MDE target: **[TO LOCK: 20% relative]** change in H1 (not 40% — implausibly large for a brief-composition nudge). At lock we commit a **power curve** (power vs. true relative effect at the locked N), not a single point. If the locked N yields <80% power at the 20% MDE, we either extend the pre-committed window **before** lock or lock with an explicit "powered only for effects ≥ X%" declaration in the abstract of the registration.

**Stopping rule (F3 fix).** Fixed horizon defined **only in pre-treatment units**: data collection ends at **[TO LOCK: N_epochs]** randomized epochs or the pre-committed calendar end date **[TO LOCK]**, whichever comes first. Opportunity counts play **no role** in stopping. No interim analyses; no optional stopping.
**Safety abort:** if either arm's brief policy is implicated in a severity-1.0 incident (adjudicated by the data monitor, arm-blind at triage), the study halts. The abort is **symmetric by rule**; if triggered, the halt is reported as informative censoring with a pre-committed sensitivity analysis (with/without the final partial epoch).

## 4. Variables

### 4.1 Primary outcome (F2 fix — unconditional)

**Repeated failure:** an executed action `a` in an analyzed session such that (i) the serving snapshot contained, at session start, ≥1 *failure episode* with `sig(a_past) = sig(a)` written ≥ **[TO LOCK: 24h]** before the epoch, and (ii) the new outcome is adjudicated failure. (Executing with a *successful* outcome is not a repeated failure.)
**Primary metric:** repeated failures **per analyzed session-hour** (unconditional density). Session-hours are pre-treatment-defined exposure units.
**Signature `sig()`:** command-class × target-class **[TO LOCK: taxonomy + frozen commit]**; robustness at one level coarser and finer pre-committed.
**Failure episode:** severity ≥ **[TO LOCK: 0.5]** (sensitivity {0.4, 0.5, 0.6}; M9) adjudicated by the blind pipeline; human gold set with IAA **κ ≥ 0.75** (sensitivity {0.6, 0.7, 0.8}; M8).

### 4.2 Secondary outcomes

Task regret (excess time-to-resolution + token cost vs. best known resolution of the same signature, winsorized at **[TO LOCK: p95]**); the H1a–c co-primary family (§1).

### 4.3 Covariates / recorded

Agent id (**defined by OS-level identity**: systemd unit / session namespace, M7), epoch id, predecessor-epoch arm, weekday, task-type class, brief composition (hashed chunk ids), per-brief retrieval metrics (H3).

## 5. Analysis Plan

**Primary inference (F4 fix).** Two components, reported separately:
1. **Sharp-null test:** epoch-level permutation test (re-randomize epoch→arm under the same balancing constraints, **[TO LOCK: 10,000]** permutations) on the **trend-residualized** outcome (outcome regressed on study-day, residuals permuted). Declared scope: this tests the sharp null of *zero total effect (direct + carry-over)*; rejection alone does not attribute magnitude.
2. **Effect estimate + CI:** difference in H1 density with cluster (epoch) bootstrap CI. Magnitude claims come from here, never from the permutation p-value.

**Co-estimates (interference; pre-committed):** A→B-restricted estimate; lag-1-adjusted estimate; partial-identification bounds (§2). Concordance across the four is the claim's strength; divergence is reported as-is.

**Secondary estimator (sensitivity):** logistic/Poisson mixed model with arm fixed effect, **agent as fixed stratum** (no agent random effect at n=6; G7), epoch random effect.

**Multiple comparisons.** H1 at α=0.05 two-sided; H1a–c + H2 Holm-corrected within the secondary family. H3 exploratory, effect sizes only, figures per pre-committed Appendix A specs.

**Exclusions (ex-ante, arm-blind; G3 fix).** All exclusion rules are deterministic, evaluable without arm labels, frozen at the pipeline commit, and applied by script before unblinding; the external auditor verifies arm-blindness. Rules: washout windows; boundary-straddling sessions (flag + sensitivity); epochs overlapping `ops_audit`-logged manual memory interventions (**both arms equally, by timestamp**); epochs with `brief_log` coverage < **[TO LOCK: 95%]** (coverage computed arm-blind; fallback: if coverage loss correlates with arm at |r| > 0.2, primary is declared compromised and reported as such; M10).

**Missing data.** Unadjudicable outcomes → third category, reported, excluded from numerator; if >**[TO LOCK: 10%]** of executed matching actions are unadjudicable, the primary is reported inconclusive regardless of p-value.

**Robustness (pre-committed):** leave-one-agent-out; first vs. second calendar half; `sig()` granularity ±1; dominance check (drop most opportunity-dense signature); W_OUTCOME sensitivity.

**Deviations protocol (M3).** This registration is versioned; any post-lock deviation is recorded in a public changelog with timestamp and rationale, and the paper carries a deviations table. Post-unblinding changes to hypotheses or exclusions are prohibited (reported as exploratory if unavoidable).

## 6. Threat map (updated post-GLM)

| Threat | Mitigation | Residual (disclosed) |
|---|---|---|
| Researcher DOF | This registration + pre-registered pilot function | — |
| Simultaneous cross-arm interference | Fleet-wide epochs (no mixing, by construction) | — |
| Carry-over via shared writes | Serving snapshots + washout + A→B co-estimate + lag-1 + bounds | Snapshot content shaped by prior arm; bounded, not eliminated |
| Collider / post-treatment denominator | Unconditional primary + co-primary family | — |
| Optional stopping | Horizon in epochs/calendar only; symmetric abort | Abort = informative censoring (sensitivity) |
| Permutation validity | Trend-residualized; sharp-null scope declared; CI separate | Sharp null covers total effect only |
| Underpowering (rare events) | Density metric, pilot-sized power curve, MDE 20%, re-scope-before-lock | Effects < MDE undetectable (declared) |
| Adjudication conflict | Blind pipeline + external auditor + independent data monitor | — |
| Hawthorne / drift | Calendar-balanced randomization + half-vs-half robustness | — |
| Selection / survivorship | All in-scope sessions enter; no curation | — |

## 7. Conflict of interest

The authors built the system, the benchmark, and the proposed metric. External auditor and data monitor are independent; the monitor holds the randomization seed and the abort authority. Registration, analysis code, sanitized benchmark, and a runnable environment (**Docker image + Zenodo/OSF DOI**; M6) are public.

## 8. Not covered by this registration

The retrospective decision-replay benchmark and the counterfactual replay harness are observational contributions (declared log study). No causal claims from them. Under **Route 1** (§0) this registration converts to a transparency artifact for the qualitative A/B validation, and all causal phrasing in §1–§5 is downgraded accordingly.

---

## 9. Open items blocking lock

1. ~~§0 route decision~~ ✅ **Route 2-lite (Toto, 2026-07-12).**
2. Named external auditor + named independent data monitor.
3. Epoch length + washout (24h + 2h proposed) · snapshot mechanism spec (serving-side freeze).
4. W_OUTCOME formula value (0.15) + low-stakes allowlist.
5. `sig()` taxonomy + frozen pipeline commit + synthetic-input PAP hash.
6. Severity (0.5) + IAA (κ ≥ 0.75) thresholds.
7. Pilot function `f` locked **before** pilot; then N_epochs, MDE (20%), calendar end, power curve.
8. Coverage floor (95%) + unadjudicable ceiling (10%) + winsorization (p95).
9. Appendix A (H3 figure specs) + Appendix B (bounds math) written.
10. Ethics/IRB statement.

## Appendix A — H3 figure specs (stub, pre-commit before unblind)

Fig. A: scatter, x = nDCG@10 per policy-epoch, y = H1 density per policy-epoch; marker = arm; report Spearman ρ + CI. Axes, binning, and inclusion rules to be frozen here before unblinding. **[TO WRITE]**

## Appendix B — Interference bounds (stub)

Bounded-interference assumption + Aronow–Samii-style partial identification for τ under snapshot carry-over; bound parameter = max per-epoch spillover. **[TO WRITE — required for Route 3, recommended for Route 2-lite]**
