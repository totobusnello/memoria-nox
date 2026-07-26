# OSF Pre-Registration — DRAFT v0.3 (NOT LOCKED)

> **Status:** working draft, 2026-07-25. v0.1 was adversarially reviewed by GLM-5.2 (5 FATAL / 7 GRAVE / 10 minor — full verdict in `REVIEWS-PREREG.md`); v0.2 incorporated every fix independent of the route decision; **Route 2-lite decided 2026-07-12** (§0). **v0.3 (2026-07-25, Toto's call): no human auditor and no human data monitor will be appointed. Independence is provided structurally — by public randomness, frozen hashes, mechanical rules, and open artifacts — rather than delegated to named individuals** (§0b). Locking now blocked only on the remaining **[TO LOCK]** items (§9). This document becomes binding only when registered on OSF with a public timestamp **before** any A/B data collection.
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

## 0b. Independence model — ✅ DECIDED: structural, not delegated (Toto, 2026-07-25)

**Decision:** no external auditor and no independent data monitor will be appointed. Every guarantee those roles were meant to provide is instead discharged by a mechanism that a third party can verify after the fact, without having had to be present beforehand.

**Rationale.** The two roles existed to answer three questions: *was the randomization manipulated?*, *were the rules fixed before the data were seen?*, and *did a self-interested party decide to stop?* Each is answerable by construction:

| Guarantee | v0.2 mechanism (person) | **v0.3 mechanism (structural)** | Strength vs. person |
|---|---|---|---|
| Randomization not chosen to taste | Monitor generates + holds seed | **Public randomness beacon** (§2, Randomization): seed derived from a `drand` round that does not exist yet at registration time | **Stronger** — requires no trust in anyone; verifiable by anyone, forever |
| Rules fixed before seeing data | Auditor sign-off pre-unblind | **OSF timestamp + frozen pipeline commit hash + synthetic-input expected-output hash**, all registered pre-hoc | **Equivalent** — moves attestation from testimony to hash |
| Exclusions are arm-blind | Auditor verifies | **Exclusions are code**, deterministic and evaluable without arm labels, in the hashed commit; anyone can re-run them | **Equivalent** |
| Adjudication not biased by arm | Blind human adjudicators | **Frozen multi-model panel** (§4.1) across distinct training families, prompts hashed pre-hoc | **Equivalent or stronger** — fully reproducible, unlike human judgment |
| Stopping not self-interested | Monitor holds abort authority | **Mechanical abort rule** (§3), numeric and arm-blind, evaluated by script at every epoch boundary | **Equivalent** — removes discretion entirely rather than relocating it |

**What is genuinely weaker, and is declared as a limitation:** there is no independent party attesting *in real time* that the registered procedure was the one executed. The mitigation is that every artifact needed to check this after the fact — registration timestamp, beacon round, pipeline commit, prompt hashes, analysis code, logs — is public and immutable, so verification is **open and post-hoc rather than delegated and ex ante**. Borderline adjudication calls also lose the tie-breaking judgment a human panel would supply; §4.1 handles ties mechanically instead.

**Causal claim is retained.** Causal identification in this design comes from randomization, not from oversight. A beacon-derived assignment sequence is not weaker than a monitor-held seed — it is strictly harder to manipulate. The claim in §1-H1 stands as written.

## 1. Study Information

**Title:** Does outcome-weighted memory reduce repeated failures in live LLM agents? A pre-registered fleet-epoch randomized crossover experiment.

**Authors:** Luiz Antonio Busnello (Independent Researcher). **Sole author; no external auditor and no independent data monitor** — independence is structural, per §0b.

**Description.** Six production LLM agents share a persistent memory system (nox-mem, in production since 2026-03). Each session receives a memory *brief* at start. We test whether weighting brief composition by **episode outcome** (adjudicated failure severity of past actions) changes repeated-failure behavior relative to the production flat/salience-only policy. This randomized arm is the **only** component of the project for which causal language is used; the retrospective benchmark is a declared observational log study, out of scope here (§8).

**Hypotheses.** All confirmatory tests are **two-sided**; expected directions are stated as expectations, not test choices (G2 fix).

- **H1 (primary, confirmatory):** the **unconditional repeated-failure density** (repeated failures per session-hour, §4.1) *differs* between arms. Expected direction: lower under treatment.
- **H1a–c (co-primary family, Holm-corrected; F2 fix):** (a) eligible-opportunity rate per session-hour; (b) repeat-attempt rate given opportunity; (c) repeated-failure rate given opportunity. Reported jointly so a change in the denominator cannot masquerade as (or mask) an effect in the conditional rate.
- **H2 (secondary, confirmatory):** task regret (§4.2) differs between arms.
- **H3 (exploratory, declared):** retrieval metrics (nDCG@10, recall@10) computed on the same briefs do not order the policies the way H1 does. **Figure specs for H3 are pre-committed in Appendix A before unblinding** (M5); no confirmatory claim from H3.

## 2. Design Plan

**Study type.** Randomized crossover on live production traffic, **fleet-wide epochs**: all 6 agents are in the same arm at any instant (kills simultaneous cross-arm contamination by construction).

**Randomization unit.** **Epoch** = fleet × time-block of **[TO LOCK: 24h, boundary 06:00 BRT]**. Epochs assigned to arm by constrained randomization balancing weekday/weekend and calendar halves.

**Seed — public randomness beacon (replaces the data monitor; §0b).** The assignment sequence is generated once by a committed, deterministic script from a seed that **does not exist at registration time and is outside author control**:

- **Beacon:** `drand` / League of Entropy, mainnet chain **[TO LOCK: chain hash]** (30 s rounds, publicly verifiable BLS output, multi-organization threshold — no single party, including the authors, can predict or influence it).
- **Derivation rule, committed at registration:** `seed = SHA256(randomness_hex(R))`, where `R` is the **first drand round with timestamp ≥ T_seed**, and `T_seed` is a wall-clock instant **[TO LOCK: date/time UTC]** that is strictly after the OSF registration timestamp and strictly before the first treatment epoch (M4).
- **What is registered pre-hoc:** the chain hash, `T_seed`, the derivation rule above, the assignment script (with its commit hash), and the balancing constraints. **What is not knowable pre-hoc:** the seed itself.
- **Verification:** anyone can, at any time, fetch round `R` from any drand relay, recompute the seed, re-run the committed script, and confirm the published assignment sequence bit-for-bit. Manipulation would require forging a threshold signature from the League of Entropy.
- **Fallback (if the beacon is unreachable at `T_seed`):** `seed = SHA256(block_hash(H))` where `H` is the **first Bitcoin block height mined at or after `T_seed`**, pre-declared in the same registration. Fallback use is itself logged in the deviations changelog (M3).

Both the derived seed and the resulting assignment sequence are published to OSF **before the first treatment epoch** (M4), together with the round number, the raw beacon output, and the recomputation script.

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

**Blinding (no auditor sign-off; §0b).** Outcome adjudication is blind to arm: adjudicators receive episodes with arm labels, sub-day timestamps, and policy metadata stripped. The trace→action→outcome→failure pipeline is deterministic, frozen at commit **[TO LOCK: hash]**, and validated end-to-end on a **synthetic input set with committed expected-output hash** (M2).

The auditor's pre-unblinding sign-off is replaced by an **ordering proof**, which is strictly checkable rather than attested:

1. Arm labels live in a **separate artifact** from the episode corpus; the adjudication pipeline reads only the corpus and cannot join to labels.
2. The **complete adjudication output is hashed and the hash published to OSF (and as a signed git tag) *before* the join to arm labels is ever executed.**
3. Unblinding is a single deterministic join script, itself in the frozen commit. Re-running it against the published verdicts must reproduce the analysis inputs exactly.

Because the verdict hash carries a public timestamp that precedes the join, adjudication cannot have been tuned to arm without breaking the hash — a check any reader can perform, at any time, without having been present.

**Ethics (M1).** **No human subjects and no human research contributors participate in this study.** Adjudication is performed by a frozen multi-model panel (§4.1), not by people; the only human involvement is the sole author's, and it is confined to mechanically-triggered tie-breaks under the rule in §4.1. The agents' user is the author himself (own production system); no third-party user data enters the benchmark un-hashed. Low-stakes restriction + mechanical safety abort (§3) bound operational harm. IRB: with no human subjects and no third-party data, independent-researcher exemption applies; statement filed at lock **[TO LOCK: statement]**.

## 3. Sampling Plan

**Existing data.** Registration precedes all treatment-arm traffic. Historical logs are used only for (a) operational definitions, (b) the **pre-registered pilot** below, (c) the separate observational benchmark.

**Pre-registered pilot (F5 fix).** Before the pilot runs, we lock: the pilot's own metric definitions (`r̂` = opportunity rate/session-hour, `p̂0` = control conditional repeat rate, ICC estimate), the executable sizing script (committed, seeded), and the **deterministic function** `N_epochs = f(r̂, p̂0, ICC, MDE)`. The pilot is replay-only (no live arms). After the pilot, `f` is evaluated once and its output locked — no re-runs, no post-hoc MDE shopping.

**Sample size & power (G1 fix).** MDE target: **[TO LOCK: 20% relative]** change in H1 (not 40% — implausibly large for a brief-composition nudge). At lock we commit a **power curve** (power vs. true relative effect at the locked N), not a single point. If the locked N yields <80% power at the 20% MDE, we either extend the pre-committed window **before** lock or lock with an explicit "powered only for effects ≥ X%" declaration in the abstract of the registration.

**Stopping rule (F3 fix).** Fixed horizon defined **only in pre-treatment units**: data collection ends at **[TO LOCK: N_epochs]** randomized epochs or the pre-committed calendar end date **[TO LOCK]**, whichever comes first. Opportunity counts play **no role** in stopping. No interim analyses; no optional stopping.
**Safety abort — mechanical, no monitor (§0b).** Discretion is removed rather than delegated. A script in the frozen commit evaluates the following **arm-blind** rule at every epoch boundary, over the incident stream only (it never reads arm labels):

> **Halt the study** if either (a) ≥1 incident adjudicated at severity **1.0** occurs in an analyzed epoch, **or** (b) the count of incidents at severity ≥ **[TO LOCK: 0.8]** within a trailing window of **[TO LOCK: 3]** epochs exceeds **[TO LOCK: 3×]** the per-epoch baseline rate computed over the **[TO LOCK: 90]** days preceding the pilot.

The rule halts the **whole study**, never one arm — so it is **symmetric by construction** and cannot be triggered selectively against the arm the author would prefer to lose. Baseline rate, window, and multiplier are frozen at lock; the trigger evaluation is logged per epoch (including non-triggers) so the entire decision series is auditable after the fact. If triggered, the halt is reported as informative censoring with the pre-committed sensitivity analysis (with/without the final partial epoch). Human judgment enters only *after* a halt, to decide whether to publish — never to decide whether to continue.

## 4. Variables

### 4.1 Primary outcome (F2 fix — unconditional)

**Repeated failure:** an executed action `a` in an analyzed session such that (i) the serving snapshot contained, at session start, ≥1 *failure episode* with `sig(a_past) = sig(a)` written ≥ **[TO LOCK: 24h]** before the epoch, and (ii) the new outcome is adjudicated failure. (Executing with a *successful* outcome is not a repeated failure.)
**Primary metric:** repeated failures **per analyzed session-hour** (unconditional density). Session-hours are pre-treatment-defined exposure units.
**Signature `sig()`:** command-class × target-class **[TO LOCK: taxonomy + frozen commit]**; robustness at one level coarser and finer pre-committed.
**Failure episode:** severity ≥ **[TO LOCK: 0.5]** (sensitivity {0.4, 0.5, 0.6}; M9), adjudicated by the frozen panel below.

**Adjudication panel (replaces human adjudicators; §0b).** Episodes are judged by an **odd-sized panel of LLMs drawn from distinct training families** — **[TO LOCK: 5, proposed: Anthropic · OpenAI · Zhipu · Moonshot · xAI]** — chosen so that correlated annotator bias is mitigated by provenance diversity rather than by assumed impartiality. Protocol:

- **Frozen prompt.** One adjudication prompt, identical for every panelist, hashed and registered pre-hoc **[TO LOCK: prompt hash]**. Model identifiers and versions are pinned **[TO LOCK: exact model ids]**.
- **Independence.** Each panelist judges every episode in isolation — no panelist sees another's verdict, and no chain-of-panel aggregation occurs before all verdicts are recorded.
- **Verdict.** Binary failure/not-failure by **simple majority**; severity by **median** of panelist severities (odd panel ⇒ no binary tie; median is well-defined and robust to a single outlier panelist).
- **Reliability.** Inter-annotator agreement across panelists reported as **Fleiss' κ ≥ [TO LOCK: 0.75]** (sensitivity {0.6, 0.7, 0.8}; M8). If κ falls below the floor, the primary is reported inconclusive on reliability grounds — the same consequence a human panel below floor would carry.
- **Tie-break / abstention.** If a panelist errors or abstains, its verdict is recorded as missing and majority is computed over the remainder; if fewer than **[TO LOCK: 3]** valid verdicts remain, the episode joins the unadjudicable category (§5, Missing data). The author intervenes **only** when the mechanical rule cannot resolve, and then on an arm-blind episode, with every such intervention logged and counted in the paper.

**Advantage over a human panel, stated plainly:** this adjudication is **fully reproducible** — a reader with the frozen prompt, the pinned model ids, and the public episode corpus can re-run it and compare against the published verdict hash (§2, Blinding). Human adjudication is not reproducible in this sense. **Declared limitation:** LLM panelists may share failure modes not eliminated by family diversity (e.g. common pretraining corpora), and a residual correlated bias cannot be excluded; the κ report and the coarser/finer `sig()` robustness checks are the available evidence against it.

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

**Exclusions (ex-ante, arm-blind; G3 fix).** All exclusion rules are deterministic, evaluable without arm labels, frozen at the pipeline commit, and applied by script before unblinding. **Arm-blindness is not attested by an auditor but is checkable by inspection (§0b):** the exclusion code takes the episode corpus as its only input — the arm-label artifact is not in scope for that module — so any reader can confirm by reading the frozen commit that no exclusion rule *could* have consulted an arm label. The set of excluded units is itself hashed and published before the join. Rules: washout windows; boundary-straddling sessions (flag + sensitivity); epochs overlapping `ops_audit`-logged manual memory interventions (**both arms equally, by timestamp**); epochs with `brief_log` coverage < **[TO LOCK: 95%]** (coverage computed arm-blind; fallback: if coverage loss correlates with arm at |r| > 0.2, primary is declared compromised and reported as such; M10).

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
| Adjudication conflict | Frozen multi-family LLM panel, majority + median, Fleiss' κ floor; verdict hash published pre-join | Correlated bias across panelists not fully excludable (§4.1) |
| Self-interested stopping | Mechanical arm-blind abort rule; halts whole study, never one arm | — |
| Manipulated randomization | Public `drand` beacon round postdating registration; anyone can recompute | — |
| No real-time independent oversight | Open post-hoc verification: OSF timestamp, beacon round, frozen commit, prompt + verdict hashes, public code/logs | **Declared:** verification is post-hoc, not contemporaneous (§0b) |
| Hawthorne / drift | Calendar-balanced randomization + half-vs-half robustness | — |
| Selection / survivorship | All in-scope sessions enter; no curation | — |

## 7. Conflict of interest

**The conflict is maximal and is stated without hedging:** the sole author built the system under test, the benchmark, and the proposed metric, and is also the operator of the production fleet the experiment runs on. **No external auditor and no independent data monitor were appointed** (§0b).

The response to that conflict is not a person vouching for the author, but the removal of the author's discretion at every point where discretion could bias the result:

- **He does not choose the randomization** — it is derived from a `drand` round that did not exist when the study was registered (§2).
- **He does not decide when to stop** — a frozen numeric rule halts the whole study, arm-blind (§3).
- **He does not adjudicate outcomes** — a pinned multi-family LLM panel does, under a hashed prompt, with verdicts hashed and timestamped before arm labels are ever joined (§4.1, §2).
- **He cannot retro-fit the exclusions** — they are code in the frozen commit, structurally unable to read arm labels (§5).
- **He cannot revise the hypotheses** — the OSF timestamp predates all treatment data (§0b).

Registration, seed derivation and beacon round, assignment sequence, adjudication prompt and verdicts, analysis code, sanitized benchmark, and a runnable environment (**Docker image + Zenodo/OSF DOI**; M6) are public. **Residual, declared:** no independent party observed the execution in real time; all verification is post-hoc. A reader who distrusts the author must be able to check the artifacts — the design is built so that they can, and the burden is deliberately placed there rather than on trust.

## 8. Not covered by this registration

The retrospective decision-replay benchmark and the counterfactual replay harness are observational contributions (declared log study). No causal claims from them. Under **Route 1** (§0) this registration converts to a transparency artifact for the qualitative A/B validation, and all causal phrasing in §1–§5 is downgraded accordingly.

---

## 9. Open items blocking lock

1. ~~§0 route decision~~ ✅ **Route 2-lite (Toto, 2026-07-12).**
2. ~~Named external auditor + named independent data monitor~~ ✅ **CLOSED by decision, not by appointment (Toto, 2026-07-25): no humans in either role; independence is structural (§0b).** Replaced by: public beacon seed (§2), mechanical abort (§3), multi-family LLM panel (§4.1), ordering proof via pre-join verdict hash (§2), exclusions-as-code (§5).
3. Epoch length + washout (24h + 2h proposed) · ~~snapshot mechanism spec~~ ✅ **SPEC WRITTEN 2026-07-25** → `specs/2026-07-25-P2S1-serving-side-snapshot.md`. Design settled: physical `VACUUM INTO` snapshot per epoch freezing **the corpus only** (`chunks`, `chunks_fts`, `vec_chunks`, `vec_chunk_map`); `brief_log` stays on the live store because the D2 coverage sampler is stateful *within* an epoch (freezing it would degenerate the brief and change what the treatment arm measures). Sliding retention of 3 snapshots keeps disk cost constant, not linear in epochs. ✅ **LOCKED 2026-07-26 — measured, not estimated.** DB **1.6 GB**; `VACUUM INTO` **9.8 s** bare / **17.8 s** including manifest (SHA-256 streamed over the full file); free disk **270 GB of 387 GB**. Sliding retention of 3 ⇒ **~4.8 GB = 1.8% of free space**, against the ≥20% headroom the kill criterion demanded. **K1 PASSES with wide margin** — the causal phrasing in §1-H1 stands and the Route 1 degrade is not triggered.

Mechanism implemented and **in production (mode `off`)**: per-epoch snapshot with auditable manifest (SHA-256, per-table counts, `user_version`, `integrity_check`), serving split (corpus from snapshot, `brief_log` from live — two connections, no `ATTACH`), atomic pointer swap via `rename()` over symlink, sliding retention that preserves manifests after pruning the `.db`, and `/api/health.servingSnapshot` reporting the epoch in use and its hash. Frozen-corpus invariant is enforced by test: content written after a boundary does not appear in that epoch's own snapshot.

**Still open before the pilot:** shadow validation over N boundaries (T6), the M2-vs-M1 approximation error (T7), and the failure drills — corrupted snapshot, full disk, absent `vec0` (T8).
4. W_OUTCOME formula value (0.15) + low-stakes allowlist.
5. `sig()` taxonomy + frozen pipeline commit + synthetic-input PAP hash.
6. Severity (0.5) + Fleiss' κ (≥ 0.75) thresholds.
7. Pilot function `f` locked **before** pilot; then N_epochs, MDE (20%), calendar end, power curve.
8. Coverage floor (95%) + unadjudicable ceiling (10%) + winsorization (p95).
9. Appendix A (H3 figure specs) + Appendix B (bounds math) written.
10. Ethics/IRB statement (simplified — no human subjects, no human contributors; §2 Ethics).

**New [TO LOCK] items created by the v0.3 independence model:** drand chain hash · `T_seed` (UTC instant, post-registration / pre-M4) · Bitcoin fallback height rule · abort rule parameters (severity 0.8 · window 3 epochs · 3× baseline · 90-day baseline period) · panel size and exact model ids · adjudication prompt hash · minimum valid verdicts for majority (3).

## Appendix A — H3 figure specs (stub, pre-commit before unblind)

Fig. A: scatter, x = nDCG@10 per policy-epoch, y = H1 density per policy-epoch; marker = arm; report Spearman ρ + CI. Axes, binning, and inclusion rules to be frozen here before unblinding. **[TO WRITE]**

## Appendix B — Interference bounds (stub)

Bounded-interference assumption + Aronow–Samii-style partial identification for τ under snapshot carry-over; bound parameter = max per-epoch spillover. **[TO WRITE — required for Route 3, recommended for Route 2-lite]**
