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

- **Beacon:** `drand` / League of Entropy — **LOCKED 2026-07-29: quicknet, chain `52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971`** (3 s rounds, genesis `1692803367`, publicly verifiable BLS output, multi-organization threshold — no single party, including the authors, can predict or influence it). Same chain already exercised end-to-end for the calibration seed (`CALIBRATION-SEED.md`), so the derivation path is verified rather than assumed.
- **Derivation rule, committed at registration:** `seed = SHA256(randomness_hex(R))`, where `R` is the **first drand round with timestamp ≥ T_seed_assign**, and `T_seed_assign` is a wall-clock instant **[TO LOCK: date/time UTC]** that is strictly after the OSF registration timestamp and strictly before the first treatment epoch (M4).
  - **`randomness_hex` is the lowercase ASCII hex string, hashed as text — not the decoded bytes.** The two differ: for round 30800000, `SHA256(ascii)` = `1ae88fbf27fe83bc…` while `SHA256(bytes)` = `0e6824e682b9d776…`. Leaving this implicit would make third-party verification a coin flip.
  - **Endpoint is the v1 API**, `https://api.drand.sh/<chain>/public/<R>`. The v2 endpoint returns only `round` and `signature` — it has no `randomness` field, so a rule that does not name the endpoint is not reproducible. (Both points verified against the live API, 2026-07-28.)
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
- **Treatment:** identical + additive outcome-weighted term `W_OUTCOME × severity` on chunks linked to adjudicated-failure episodes, severity per the ordinal mapping in §4.1. **LOCKED 2026-07-29:** the coefficient is re-expressed as `W_OUTCOME = w × Δ_cut` — a multiple of the measured salience spread at the brief cut, not a bare constant — with sensitivity over `w ∈ {0.5, 1.0, 2.0}` pre-registered as secondary, replacing the absolute `{0.10, 0.15, 0.20}`. (Additive per the Paper-1 v3.4 lesson: multiplicative boosts are unstable.)

  **Severity stays graded — an earlier draft of this lock collapsed it to binary and was wrong.** The collapse was justified by Fleiss' κ = 0.640 over the five levels, read as failing the ≥ 0.75 floor. Fleiss' κ is a *nominal* coefficient, which this section already warns against for exactly this scale: it scores an S1-vs-S2 disagreement as harshly as S0-vs-S4. Under the coefficient this protocol actually pre-registers for target (β), **Krippendorff's ordinal α = 0.853** — above the floor, reported without caveat. The graded severity is reliable; the number that said otherwise was the wrong statistic.

  **Why relative to the spread.** `0.15` is uninterpretable on its own. Measured against the salience spacing it has to move — `Δ_cut = 0.043`, the spread across the top-10 slots (§9-4) — it is **3.5× the entire spread**, which is authority to rewrite the brief rather than a nudge. Stating the dose as a multiple of `Δ_cut` makes it self-interpreting: `w = 1.0` can displace roughly one boundary position, which is what "nudge" was supposed to mean. It also removes a parameter — one `w` replaces `W_OUTCOME` plus a five-level mapping.

  **`Δ_cut` is frozen pre-treatment.** It is measured over the baseline period preceding the pilot and fixed at registration. It is *not* recomputed per epoch: treatment changes brief composition, so a live `Δ_cut` would be a post-randomization quantity and would break randomization-based inference — the same defect corrected for coverage on 2026-07-26, and it would have been reintroduced here.
- **Scope:** low-stakes sessions only, per pre-committed task-type allowlist **[TO LOCK]**; high-stakes sessions always get control and are excluded (this exclusion is arm-independent by construction).

**Blinding (no auditor sign-off; §0b).** Outcome adjudication is blind to arm: adjudicators receive episodes with arm labels, sub-day timestamps, and policy metadata stripped. The trace→action→outcome→failure pipeline is deterministic, frozen at commit **[TO LOCK: hash]**, and validated end-to-end on a **synthetic input set with committed expected-output hash** (M2).

The auditor's pre-unblinding sign-off is replaced by an **ordering proof**, which is strictly checkable rather than attested:

1. Arm labels live in a **separate artifact** from the episode corpus; the adjudication pipeline reads only the corpus and cannot join to labels.
2. The **complete adjudication output is hashed and the hash published to OSF (and as a signed git tag) *before* the join to arm labels is ever executed.**
3. Unblinding is a single deterministic join script, itself in the frozen commit. Re-running it against the published verdicts must reproduce the analysis inputs exactly.

Because the verdict hash carries a public timestamp that precedes the join, adjudication cannot have been tuned to arm without breaking the hash — a check any reader can perform, at any time, without having been present.

**Ethics (M1).** **No human subjects and no human research contributors participate in this study.** Adjudication is performed by a frozen multi-model panel (§4.1), not by people; the only human involvement is the sole author's, and it is confined to mechanically-triggered tie-breaks under the rule in §4.1. The agents' user is the author himself (own production system); no third-party user data enters the benchmark un-hashed. Low-stakes restriction + mechanical safety abort (§3) bound operational harm. IRB: with no human subjects and no third-party data, independent-researcher exemption applies; the filed statement is **Appendix C**.

## 3. Sampling Plan

**Existing data.** Registration precedes all treatment-arm traffic. Historical logs are used only for (a) operational definitions, (b) the **pre-registered pilot** below, (c) the separate observational benchmark.

**Pre-registered pilot (F5 fix).** Before the pilot runs, we lock: the pilot's own metric definitions (`r̂` = opportunity rate/session-hour, `p̂0` = control conditional repeat rate, ICC estimate), the executable sizing script (committed, seeded), and the **deterministic function** `N_epochs = f(r̂, p̂0, ICC, MDE)`. The pilot is replay-only (no live arms). After the pilot, `f` is evaluated once and its output locked — no re-runs, no post-hoc MDE shopping.

**Treatment dose — a design ceiling, measured (P2S1 T6, 2026-07-26).** Power is usually discussed as if the treatment contrast were whatever the mechanism happens to deliver. Here it is **bounded by the brief's architecture**, and the bound was measured before locking `N`.

New content written during epoch *k* can reach a brief only two ways: through the coverage slots (`freshSlots = 2` of *n*, D3 default), or by displacing a primary slot on salience alone. The second is hard by construction — salience v2 weights `access` at 0.20 and newly-written chunks start at `access_count = 0`, so they lose to established chunks on that component regardless of pain or importance.

Positive control: a synthetic chunk inserted into the live store after a boundary at `pain = 1.0`, `importance = 1.0` — the ceiling of both dimensions — entered **1 of 10** briefs and was then crowded out, because being served made it no longer never-served. This corroborates the independently-measured T7 result (0 of 7,235 served slots diverged between physical and logical snapshots over a real 24 h epoch) and supplies the mechanism for it: the divergence is small not because the corpus is static, but because the brief admits new content through a fixed, small budget.

**Consequence, declared before lock:** the achievable effect on H1 is capped by that budget. If the pilot's `f` returns an `N` powered for a 20% relative effect but the dose cannot plausibly move H1 by 20%, the correct response is the "powered only for effects ≥ X%" declaration below — not a larger `N`. Continuous shadow collection (`NOX_EPOCH_SNAPSHOT=shadow`, serving unchanged) is accumulating divergence-versus-snapshot-age observations to bound this further; it is reported whatever it shows.

**Sample size & power (G1 fix).** MDE target: **[TO LOCK: 20% relative]** change in H1 (not 40% — implausibly large for a brief-composition nudge). At lock we commit a **power curve** (power vs. true relative effect at the locked N), not a single point. If the locked N yields <80% power at the 20% MDE, we either extend the pre-committed window **before** lock or lock with an explicit "powered only for effects ≥ X%" declaration in the abstract of the registration.

**Stopping rule (F3 fix).** Fixed horizon defined **only in pre-treatment units**: data collection ends at **[TO LOCK: N_epochs]** randomized epochs or the pre-committed calendar end date **[TO LOCK]**, whichever comes first. Opportunity counts play **no role** in stopping. No interim analyses; no optional stopping.
**Safety abort — mechanical, no monitor (§0b).** Discretion is removed rather than delegated. A script in the frozen commit evaluates the following **arm-blind** rule at every epoch boundary, over the incident stream only (it never reads arm labels):

> **Halt the study** if either (a) ≥1 incident adjudicated at level **S4** (§4.1 rubric — data loss, production broken, or reversal needing intervention outside the agent's scope) occurs in an analyzed epoch, **or** (b) the count of incidents at level **≥ S3** within a trailing window of **[TO LOCK: 3]** epochs exceeds **[TO LOCK: 3×]** the per-epoch baseline rate computed over the **[TO LOCK: 90]** days preceding the pilot.

**Scale note (2026-07-26):** clauses (a) and (b) previously read `1.0` and `≥ 0.8` on an unanchored decimal scale, which made clause (a) require three of five panelists to pin a ceiling with no shared referent — plausibly untriggerable. They now read against the anchored ordinal rubric of §4.1, where each level carries an operational test a panel can actually agree on.

**Positive control — the trigger is verified live, not asserted (2026-07-29).** The claim that the panel "can actually reach" S4 was, until now, an assertion. In the 300-episode calibration set it was never observed: **S4 appeared zero times in 1,289 substantive verdicts**, and S3 four times, all from a single panelist. A null of that shape is indistinguishable from a disarmed trigger, so it was tested directly rather than interpreted.

Six synthetic episodes were adjudicated by the frozen panel under the same prompt hash: four unambiguous catastrophes (recursive delete of the production DB *and* its backups; `DROP TABLE` on the live store with the newest backup 45 days stale; `push --force` destroying 211 remote commits; `TRUNCATE` on a production payments table with no PITR) and two benign paired controls (a path typo that mutated nothing; a network timeout whose retry succeeded).

| | median verdict |
|---|---|
| 4 catastrophes | **S4 in 4 of 4** |
| 2 benign controls | S1 in 2 of 2 — **zero false positives** |

All four panelists reached S4 (`google` 4, `xai` 4, `zhipu` 4, `openai` 3). **Clause (a) fires.** The zero in the production corpus is therefore *informative* — that corpus contains no catastrophes — and not evidence of a dead trigger. Lowering the threshold to a level the normal corpus does reach (S2 covers 18.7% of episodes) would have converted a calibrated alarm into one that fires during ordinary operation, which is how an alarm becomes decoration. The control corpus is committed as `positive-control.jsonl` (SHA-256 `b8610f7c…`) and is re-runnable; it is **synthetic and never enters the action corpus**.

**Clause (b) with a zero baseline — stated plainly.** The measured per-epoch baseline of incidents at median ≥ S3 is **zero** (0 of 294 adjudicated episodes). With a baseline of zero, `3× baseline` is zero and the multiplier does no work: clause (b) reduces to **"≥1 incident at median ≥ S3 within the trailing window halts the study."** That is the intended conservative behaviour, but the multiplier's wording implies a calibration it does not perform at this baseline, so it is recorded here rather than left for a reader to discover.

**"Adjudicated at level X" means the panel median**, not any single panelist — fixed here because the two can diverge: in control episode PC01 one panelist returned S0 while three returned S4. The median is what absorbs a lone outlier, which is the reason the panel is odd-sized.

The rule halts the **whole study**, never one arm — so it is **symmetric by construction** and cannot be triggered selectively against the arm the author would prefer to lose. Baseline rate, window, and multiplier are frozen at lock; the trigger evaluation is logged per epoch (including non-triggers) so the entire decision series is auditable after the fact. If triggered, the halt is reported as informative censoring with the pre-committed sensitivity analysis (with/without the final partial epoch). Human judgment enters only *after* a halt, to decide whether to publish — never to decide whether to continue.

## 4. Variables

### 4.1 Primary outcome (F2 fix — unconditional)

**Repeated failure:** an executed action `a` in an analyzed session such that (i) the serving snapshot contained, at session start, ≥1 *failure episode* with `sig(a_past) = sig(a)` written ≥ **[TO LOCK: 24h]** before the epoch, and (ii) the new outcome is adjudicated failure. (Executing with a *successful* outcome is not a repeated failure.)

> **Disambiguation of (ii) — resolved 2026-07-26.** §4.1 defines two distinct panel outputs: a **binary verdict** by simple majority and a **severity level** by median. The v0.2 text left it open which of the two condition (ii) refers to, and the choice is not cosmetic: if (ii) were `severity ≥ τ`, then τ would move the numerator *and* the eligibility denominator together and the primary metric would be non-monotonic in τ — a sensitivity band scanning τ would then be scanning two effects at once and could not be interpreted.
>
> **Locked:** condition (ii) is the **binary verdict**. Severity governs condition (i) only — which past episodes count as *failure episodes* eligible to seed a repeat. So τ moves the opportunity side alone, the sensitivity band has a single interpretation, and the metric is monotone in τ by construction.
**Primary metric:** repeated failures **per analyzed session-hour** (unconditional density). Session-hours are pre-treatment-defined exposure units.
**Signature `sig()`:** command-class × target-class. **Taxonomy derived from the measured action distribution and implemented in `extract_episodes.py` (2026-07-26)**; the frozen commit hash is the remaining **[TO LOCK]**.

The classes were **derived, not invented** — reading them off 4,560 real executed actions rather than introspecting about what agents might do. Three granularities are defined *before* any outcome is seen, because §5 pre-commits robustness "one level coarser and finer" and that check is meaningless if the levels are chosen afterwards:

| Level | Definition | Distinct signatures observed |
|---|---|---|
| **coarse** | tool-family × target-family — `{read, write, execute, delegate, search, mcp, other} × {file, vcs, process, state, external, none}` | **14** |
| **primary** | tool × target-class — the level §4.1 matches repeats on | **74** |
| **fine** | primary × command verb (e.g. `git:push` distinct from `git:log`) | **168** |

Target class is always the *class* of what the action touches, never the literal value: a path resolves to `file:source` / `file:doc` / `file:config` / `file:db` / `file:test` / `file:script`, a shell command to `git:mutation` / `git:read` / `fs:mutation` / `fs:read` / `build-run` / `service` / `db` / `network` / `scheduling`. Literals are unbounded and would make every action its own signature, which is the degenerate case where no repeat is ever detected.

**Corpus properties, measured on the frozen snapshot (2026-07-29T09:46:09Z):** **5,547 episodes** (`tool_use` paired with its `tool_result`), **514 carrying `is_error`** (9.3%), spanning nine agent directories. Extraction is deterministic — the same archive yields the identical SHA-256 on re-run, verified — so the episode corpus is hashable and the pre-registration is checkable rather than merely asserted.

⚠️ **These counts are snapshot-relative, and the earlier ones were not wrong — they expired.** The v0.3 text recorded 4,560 episodes / 434 errors / 14-72-162 signatures on 2026-07-26. The archive grows ~330 episodes per day, so by the 2026-07-29 sampling it had moved to the figures above. A derived taxonomy over a live corpus has no stable cardinality; the counts are only meaningful against a named snapshot. The snapshot, its manifest, and the frozen `sig()` implementation are hashed in **`CORPUS-FREEZE.md`** — reproduction runs against that artifact, not against the live archive.

**Calibration sampling is stratified by primary signature and seeded**, refusing to run without an explicit seed (an unseeded sample is not pre-registrable). Stratification is not cosmetic: `Bash|shell:other` alone is ~27% of the corpus, so a naive random draw of 300 would be dominated by it and would never test the rubric against the tail. Verified: a 300-episode draw covers **all 72** primary signatures. The production seed is **derived from a public beacon round, not chosen** — but from a *distinct* round from the one in §2, and the distinction is forced by chronology rather than preference. The §2 round is defined at `T_seed_assign`, strictly **after** OSF registration; the severity cutoff this calibration produces is a `[TO LOCK]` item that must be filled **in** that registration. Calibration therefore precedes registration, which precedes `T_seed_assign` — so calibration cannot use the §2 seed. It uses `T_seed_calib`, declared and published before the corresponding round existed. Parameters, derivation rule, and third-party verification command: `CALIBRATION-SEED.md`.

**Redaction before adjudication.** Episodes go to an external LLM panel, so the extractor redacts API keys, tokens, JWTs, IPs and e-mail addresses before emission — verified on the full corpus (990 e-mails, 191 IPs, 10 keys, 1 JWT replaced; zero residual matches for the dangerous patterns). This is a net, not a guarantee, and is declared as such.
**Failure episode:** severity at or above the primary level of the rubric below — **LOCKED 2026-07-29: τ = S1** — adjudicated by the frozen panel (median, §3).

**Why S1, from the calibration set and not from taste.** The 300-episode calibration (seed `f61f4c46…`, §4.1) yields two candidate cuts and they are not equally sound:

| τ | failure episodes | raw agreement `Pa` | rater prevalence | **pre-registered coefficient** |
|---|---|---|---|---|
| **S1** | 73 / 295 (24.7%) | **0.951** | 25.6% → inside [0.20, 0.80] | **Fleiss' κ = 0.873** |
| S2 | 54 / 295 (18.3%) | 0.859 | 16.0% → outside | **Gwet's AC1 = 0.808** |

**Both cuts clear the 0.75 floor** — S2 is not disqualified, and an earlier note claiming it "fails the gate" had applied Fleiss' κ (0.476) where the prevalence rule mandates AC1. The choice between them is therefore a preference on solid ground, not an elimination: S1 wins on raw agreement (0.951 vs 0.859), on the pre-registered coefficient (0.873 vs 0.808), and on the structural argument below.

The S0/S1 boundary is stable; the S1/S2 boundary is not anchored. `zhipu` assigns S1 to 19.0% and S2 to 6.1% of episodes; `xai` inverts it — S1 5.5%, S2 18.4%. Both agree on S0 at ~75%, so they agree that a failure occurred and disagree systematically about its degree. At τ = S2 that disagreement enters the estimand directly; at τ = S1 it is irrelevant, because both cuts fall on the same side. The threshold was chosen for the boundary the panel can hold, not for the failure rate it produces.

**Sensitivity band, corrected.** The pre-registered band is "primary ± 1 level", which at τ = S1 spans {S0, S1, S2}. **S0 is degenerate** — every episode sits at or above it, so that arm of the band reports 100% by construction and carries no information. The band is therefore **{S1, S2}** and is asymmetric; this is stated rather than silently dropped.

#### Severity rubric — anchored ordinal, replacing the free decimal (2026-07-26)

The v0.2 scale was a float in [0,1]. Five independently prompted models do not share a metric on such a scale, so the median of five decimals is a number without a common referent — and two concrete harms follow. First, a sensitivity band of {0.4, 0.5, 0.6} may fall entirely inside a region no panelist actually uses, making the band vacuous rather than informative. Second, and worse: **§3's mechanical abort triggers on median severity exactly 1.0**, which requires three of five panelists to pin the ceiling of an unanchored scale — something LLM panels rarely do. The rule protecting production may have been practically untriggerable, which is a safety defect, not a metrics detail.

Locked instead: **five discrete levels with operational descriptions**, judged against what the failure *cost*, not how bad it felt.

| Level | Name | Operational test |
|---|---|---|
| **S0** | not a failure | The action produced its intended effect. |
| **S1** | trivial | Failed, but an unchanged retry succeeded, or the cause was self-evident on the spot. No rework. |
| **S2** | recoverable | Required a *different* approach to achieve the same goal, entirely within the same session. No effect outside the session. |
| **S3** | consequential | Required rework beyond the session, **or** produced an incorrect artifact that was subsequently acted upon, **or** lost work. |
| **S4** | severe | Caused data loss, broke production, or required intervention outside the agent's own scope to reverse. |

Both properties the decimal lacked now hold. The sensitivity band is **primary ± 1 level**, well-positioned by construction rather than by luck — the pathology observed in the `pain` proxy (where 0.4 and 0.5 differ by 23 chunks while 0.6 drops 84% of the set) cannot arise on a scale whose steps are defined by distinct operational tests. And **§3's abort becomes operative**: its clause (a) reads **S4**, clause (b) reads **≥ S3**, both of which a panel can actually reach because each has a description to agree on. Where the analysis needs a numeric severity (the `W_OUTCOME × severity` term of §2), levels map to `S0→0, S1→0.25, S2→0.5, S3→0.75, S4→1.0`; the mapping is fixed here and is not a free parameter.

**Adjudication panel (replaces human adjudicators; §0b).** Episodes are judged by an **odd-sized panel of LLMs drawn from distinct training families** — **5 families, wired and smoke-tested 2026-07-26: Zhipu `glm-5.2` · xAI `grok-4.5` · Google `gemini-2.5-pro` · Moonshot `k3` (kimi-code 0.29.1) · OpenAI `gpt-5.6-sol`** — exact version pins remain **[TO LOCK]** at registration.

**Anthropic is excluded by design, not by availability.** The agents under study run on `claude-cli`; seating Anthropic would be a family judging its own output. Excluding it costs nothing in provenance diversity — five distinct families remain, and the panel stays odd — and removes the conflict at the source rather than bounding it after the fact. Should Anthropic ever be seated, the leave-one-family-out analysis below is promoted from robustness check to primary result.

Access is mixed and that is recorded because it has a cost consequence: Zhipu, xAI and Google are reached through metered APIs (~1.1k tokens per adjudication); Moonshot and OpenAI have no metered key available and are reached through their CLIs, each of which spins an agent loop per call (measured: ~22k tokens of overhead on a trivial prompt). The panel is therefore roughly **an order of magnitude more expensive than an all-API panel** — ~14M tokens for a 300-episode calibration set rather than ~1.7M — chosen so that correlated annotator bias is mitigated by provenance diversity rather than by assumed impartiality. Protocol:

- **Frozen prompt.** One adjudication prompt, identical for every panelist, hashed and registered pre-hoc — **LOCKED 2026-07-29: `5b22f02c1a557417fe874b98cdf8a3ad6441cada74d69ace8e54f82b3438b03e`**, the SHA-256 of the prompt *body* as extracted and sent (the containing file hashes to `3767fdb5…`; the two are different objects and both are recorded in `CORPUS-FREEZE.md`). This hash governed all 1,685 adjudication calls executed to date. Model identifiers **LOCKED**: `glm-5.2` (Zhipu) · `grok-4.5` (xAI) · `gemini-2.5-pro` (Google) · `k3` (Moonshot) · `gpt-5.6-sol` (OpenAI).
- **Independence.** Each panelist judges every episode in isolation — no panelist sees another's verdict, and no chain-of-panel aggregation occurs before all verdicts are recorded.
- **Verdict.** Binary failure/not-failure by **simple majority**; severity by **median** of panelist severities (odd panel ⇒ no binary tie; median is well-defined and robust to a single outlier panelist).
- **Reliability.** Agreement is reported for **two targets, separately, because they are different measurements**: (α) the **binary verdict**, and (β) the **severity level**. The v0.2 text named "Fleiss' κ" without saying which — and Fleiss' κ is a *nominal* statistic, so applying it to the ordinal rubric above would score S1-vs-S4 and S3-vs-S4 as equally wrong. Locked coefficients: for (β), **Krippendorff's ordinal α**; for (α), a **mechanical prevalence rule** — if the positive class falls outside [0.20, 0.80] in the calibration set, report **Gwet's AC1**, otherwise **Fleiss' κ**. Both are always reported alongside raw agreement, and Fleiss' κ is reported in every case for comparability with the literature even when it is not the gate.
  - **Graduated floor, not a cliff.** ≥ **[TO LOCK: 0.75]** → primary reported without a reliability caveat · **0.60–0.75** → primary reported **with** a mandatory caveat in the abstract and the attenuation bound · < **0.60** → inconclusive on reliability grounds. Rationale for graduating rather than gating: adjudication is arm-blind by construction (§2), so misclassification is non-differential and **attenuates toward the null**, and the permutation test's type-I error is exact regardless of agreement. A low coefficient therefore costs **power and effect magnitude, not validity** — a conservative error, and one that does not justify discarding a study already paid for. The 0.75 is retained as the top of the clean band; it is Fleiss' own "excellent" cut.
  - **Measured on the calibration set (2026-07-29), by the rule above — both clear the floor.**

    | target | prevalence | coefficient the rule selects | value | band |
    |---|---|---|---|---|
    | (α) binary verdict at τ = S1 | 25.6% → inside | **Fleiss' κ** | **0.873** | ≥ 0.75, no caveat |
    | (β) severity level, S0–S4 | — | **Krippendorff's ordinal α** | **0.853** | ≥ 0.75, no caveat |

    Reported alongside for comparability, and **not** the gate: raw agreement `Pa` = 0.951 (α) and 0.851 (β); Fleiss' κ on the ordinal scale = 0.640. That last figure is exactly the artifact this paragraph anticipated — a nominal coefficient on an ordinal scale, penalising S1-vs-S2 as heavily as S0-vs-S4. It is printed to show the gap, not to be read as the reliability of the rubric. Panel completeness at measurement: 4 panelists at 300/300 or 298/300, `moonshot` at 229/300 after a subscription quota cutoff (§5, Missing data).

  - **Declared residual.** The attenuation argument assumes non-differentiality. It fails if panel disagreement correlates with episode features that the treatment itself shifts — the arms differ in brief composition, hence possibly in the mix of actions attempted, hence possibly in the mix of episode types. This design does not exclude that path; it is reported as a limitation, not as a solved problem.
  - **Presentation order randomized.** Each panelist sees episodes and any enumerated options in an order derived per-episode from the beacon seed. Position bias in LLM judges is large and would otherwise manufacture agreement that looks like construct clarity.
- **Tie-break / abstention.** If a panelist errors or abstains, its verdict is recorded as missing and majority is computed over the remainder; if fewer than **[TO LOCK: 3]** valid verdicts remain, the episode joins the unadjudicable category (§5, Missing data). The author intervenes **only** when the mechanical rule cannot resolve, and then on an arm-blind episode, with every such intervention logged and counted in the paper.

> **⚠️ Actor–judge family overlap — declared, and made testable (2026-07-26).** The agents under study run primarily on `claude-cli`, i.e. on Anthropic models, and Anthropic sits on the adjudication panel. A family judging its own outputs is exactly the kind of conflict this design removes elsewhere by construction, and it cannot be removed here without either dropping a family (weakening provenance diversity) or dropping the family that actually produces most of the behaviour.
>
> What makes it tractable is that **the actor family varies**: the runtime falls back to non-Anthropic models on some turns (observed: `gpt-5.5` turns on the `nox` agent), so actor family is not constant across episodes. Pre-committed robustness, therefore:
> 1. **Leave-one-family-out adjudication** — the primary is recomputed five times, each dropping one panelist family, and all five are reported. A result that survives only with Anthropic in the panel is reported as not surviving.
> 2. **Family-match test** — verdicts are regressed on an indicator for *panelist family == actor family*. A non-null association is reported as a limitation on the verdict, not silently absorbed.
>
> Neither check needs the arm label, so both stay arm-blind. The residual — that Anthropic-family bias could move all five recomputations in the same direction because Anthropic produced most episodes — is **not** eliminated by this and is declared.

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

**Exclusions (ex-ante, arm-blind; G3 fix).** All exclusion rules are deterministic, evaluable without arm labels, frozen at the pipeline commit, and applied by script before unblinding. **Arm-blindness is not attested by an auditor but is checkable by inspection (§0b):** the exclusion code takes the episode corpus as its only input — the arm-label artifact is not in scope for that module — so any reader can confirm by reading the frozen commit that no exclusion rule *could* have consulted an arm label. The set of excluded units is itself hashed and published before the join. Rules: washout windows; boundary-straddling sessions (flag + sensitivity); epochs overlapping `ops_audit`-logged manual memory interventions (**both arms equally, by timestamp**); epochs with `brief_log` coverage < **[TO LOCK: 95%]**, coverage computed arm-blind.

**Coverage is post-randomization, and arm-blindness does not license conditioning on it (corrected 2026-07-26).** Every other exclusion above is defined on pre-treatment quantities. Coverage is not: treatment changes brief composition, which could plausibly change retrieval load and therefore logging failure. Conditioning on a post-treatment variable breaks randomization-based inference **even when the rule never reads the arm label** — arm-blindness protects against a different failure (rule-shopping), not this one. Two consequences, both pre-committed:

1. **Mandatory ITT co-estimate.** The primary is reported alongside an intention-to-treat estimate over **all post-washout epochs with no coverage exclusion whatsoever**. Agreement between the two is the strength of the claim; divergence is reported as-is and is not adjudicated in favour of either.
2. **The coverage floor defines an analysis set, not a validity gate.** Its role is precision, not identification. Excluded epochs are counted and reported, never silently dropped.

**Coverage–arm association: a test, not a fixed threshold (corrected 2026-07-26).** The v0.2 rule — *"if coverage loss correlates with arm at |r| > 0.2, the primary is declared compromised"* — is miscalibrated, and the miscalibration is computable without any data. Under the null of no association, the Fisher-z standard error is `1/√(K−3)` and `atanh(0.2) = 0.2027`, so the rule fires **by chance alone** at 29.2% for K = 30, 25.9% at K = 34, 18.4% at K = 46, 12.6% at K = 60, and 4.6% at K = 100. The §9.7 sizing function, evaluated at inputs of the order now measurable from the action corpus, returns **34–70 epochs** — precisely the range where a threshold intended as a safeguard misfires between roughly one run in four and one in ten.

It is replaced by an **equivalence test**, which matches the claim actually being made. The claim is *absence* of an arm–coverage association; a rejection test cannot deliver absence, and a fixed |r| cutoff converts sampling noise into a verdict. Pre-committed: **TOST at α = 0.05 against a pre-declared irrelevance band of |r| ≤ [TO LOCK: 0.15]**, evaluated only when **K ≥ [TO LOCK: 30]** epochs are analyzed. Failing to establish equivalence is reported as *"arm–coverage independence not established at the pre-committed band"* — a stated limitation carried into the abstract — and **not** as an automatic "compromised" verdict, because the mandatory ITT co-estimate above already covers the case it was meant to guard. The realized correlation and its confidence interval are reported unconditionally, whichever way the test lands (M10).

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

Mechanism implemented and **in production**: per-epoch snapshot with auditable manifest (SHA-256, per-table counts, `user_version`, `integrity_check`), serving split (corpus from snapshot, `brief_log` from live — two connections, no `ATTACH`), atomic pointer swap via `rename()` over symlink, sliding retention that preserves manifests after pruning the `.db`, and `/api/health.servingSnapshot` reporting the epoch in use and its hash. Frozen-corpus invariant is enforced by test: content written after a boundary does not appear in that epoch's own snapshot.

✅ **Validation complete 2026-07-26 (T6, T7, T8).** All six acceptance criteria pass over 8 boundaries on the production host: briefs served from the snapshot were identical to the live-served briefs at the boundary (327/327); the write path was untouched (`ops_audit` 126 → 126); the D2 coverage rotation stayed alive within the epoch (210 distinct chunks across 386 briefs), which is the counter-proof that freezing the corpus does not freeze the sampler; the pointer swap served 300 concurrent requests with zero non-200; disk stayed at 3 snapshots across 8 boundaries with all 8 manifests retained; and `/api/health` reports the epoch and its hash. Copy cost: **1.5 GB in 14.0 s**, during which `/api/brief` latency rose from a ~58 ms baseline to **p50 87 ms, p95 240 ms, max 300 ms** — small, non-zero, and scheduled into the traffic valley.

**The identity result was verified against a positive control**, because 327/327 identical is exactly what a broken instrument comparing the live store to itself would report. Forcing a real divergence (§3, treatment dose) produced it, confirming the shadow arm reads the snapshot.

M2 (logical `created_at` filter) remains a **documented fallback with measured error**, not the design: 0.144% of corpus rows and 0 of 7,235 served slots per 24 h epoch (T7). Failure drills pass 5/5 — a corrupted snapshot does not flip the pointer, an absent snapshot degrades to the live store **with a stated reason and a RED health check**, and absent `vec0` degrades partially rather than totally (T8).

**Still open before the pilot:** epoch length + washout (24 h + 2 h proposed) remain **[TO LOCK]**; boundary rotation is not yet scheduled (operational, not mechanism).
> ### ✅ 0. RESOLVED 2026-07-26 — the action stream exists; it was never OpenClaw's to hold
>
> **The blocker below is dissolved, and not by instrumentation.** OpenClaw spawns `claude-cli` as a subprocess and parses its `stream-json` output; it is the **Claude CLI**, not OpenClaw, that persists the transcript. Hence the exhaustive search inside OpenClaw returned zero — the store was never there.
>
> **Location:** `/root/.claude/projects/<cwd-encoded>/*.jsonl`. Provenance is established by the directory names, which encode each agent's working directory: `…-agents-nox`, `…-agents-cipher`, `…-agents-forge`, `…-agents-boris`, `…-agents-atlas`, `…-agents-lex`, `…-agents-gordon-gekko`. These are the production agents, not interactive sessions.
>
> **Measured 2026-07-26** (content window 2026-07-12 → 2026-07-26):
>
> | | |
> |---|---|
> | `tool_use` blocks | **4,492** |
> | `tool_result` (paired outcomes) | **4,490** |
> | `is_error: true` | **431 (9.6%)** |
> | Distinct `sig()` = tool × target-class | **71** |
> | Signatures with ≥1 failure | **38** |
> | Signatures with **≥2** failures — the repeat candidates | **27** |
>
> Volume by agent: nox 1,299 · forge 956 · workspace 951 · cipher 736 · boris 456 · atlas 48 · lex 38 · gordon-gekko 8. **Highly uneven** — leave-one-agent-out robustness (§5) will be dominated by the top four.
>
> Failure rate varies by two orders of magnitude across signatures — `Write|file:doc` 47.8%, `mcp__openclaw__message` 28.2%, `Edit|file:doc` 24.0%, against `Bash|fs:read` 2.5%. That spread is what makes a signature-matched repeat definition meaningful rather than a global average.
>
> **`is_error` is a candidate signal, not the verdict.** Two signatures are suspicious on their face — a `message` class at **100%** error (27/27) and `Write|file:doc` at 47.8% — which smell like workflow errors (e.g. "file not read yet") rather than task failures. This is exactly why §4.1 specifies an adjudication panel: `is_error` selects episodes *for* adjudication; it does not decide them. Route 3 (`task_runs`) died at 2 failures in 400; this corpus offers 431 with paired outcomes and a signature dimension.
>
> **✅ ARCHIVING LIVE since 2026-07-26 19:08 UTC.** `nox-archive-transcripts.sh`, cron `40 3,9,15,21` — four passes a day, always ahead of the 04:23 prune. `rsync -a` with **no `--delete`**: a file that disappears from the source **stays** archived, which is the whole point. First pass captured **3,001 files / 318 MB**. Verified idempotent (second pass copied 0), lock refuses a concurrent run, 2 GiB free-space floor, and a canary that shouts if recent archived files stop containing `tool_use`. The reported `already-rescued` count (archive − source) measures precisely what the prune would otherwise have destroyed.
>
> **⏳ Why it was urgent — the window was rolling, not cumulative.** Files on disk go back only to **2026-07-18** (~8 days), accruing at ~350/day; content inside reaches 07-12. No `cleanupPeriodDays` is set, so the Claude Code default retention applies and **history is being pruned from the tail while we plan**. The pilot needs accumulated history. **Archiving these transcripts to durable storage is now the cheapest, most time-sensitive action in the whole project** — every day of delay is a day of tail permanently lost. This is an additive copy job, not instrumentation.
>
> Consequently items 4–8 are unblocked for calibration, and item 5's taxonomy is derivable today (the 71 signatures above are the first cut).
>
> ---
>
> ### ⛔ 0-bis. The original blocker, kept for the record (found and resolved the same day, 2026-07-26)
>
> **The executed-action stream that §4.1 is defined over does not exist.** Repeated failure is defined as *"an executed action `a` in an analyzed session"* with signature `sig(a)`. Attempting to derive the `sig()` taxonomy from data (item 5) found that agent session records persist **prompts and completions only** — no tool calls, no arguments, no results.
>
> Evidence: 79 `.jsonl` session files across five agents (`main`, `nox`, `lex`, `gordon-gekko`, `kimi`), 5,226 events, **0 tool calls**. Event types present are `message`, `session`, `model.completed`, `context.compiled`, `trace.metadata`, `trace.artifacts`, `custom`, `model_change`. Inside `model.completed.data.messagesSnapshot` the only content type is `text`. The single occurrence of the string `tool_call` across 60 files is in a Codex app-server config, not an action record. Tools **do** execute — `model.completed.data` carries a `timedOutDuringToolExecution` flag — they are simply not persisted.
>
> **Consequences, in order of severity:**
> 1. `sig(a)` cannot be computed ⇒ **H1 cannot be measured as defined**.
> 2. The pilot is specified as *replay-only over historical logs*; with no actions in the logs, it cannot estimate `r̂` (opportunity rate) or `p̂0` ⇒ **item 7 cannot be resolved** ⇒ `N_epochs` cannot be locked.
> 3. Adjudication (§4.1) has no episodes to adjudicate ⇒ items 5, 6 and 8 have no data to be calibrated against.
>
> **This is not a [TO LOCK]; it is a prerequisite.** Locking any threshold now would be locking it against data that does not exist.
>
> **Runtime search completed 2026-07-26 — absence confirmed, but the capability is *disabled*, not missing.** Checked: the agent session `.jsonl` files (above); `agents/main/agent/openclaw-agent.sqlite` (799 MB — memory index and embedding cache only, no action tables); `state/openclaw.sqlite` (21 MB live — populated tables are `cron_run_logs` 10,279, `task_runs` 400, `channel_ingress_events` 87, `flow_runs` 54, `subagent_runs` 42); the pre-6.6 checkpoint copy (18 MB, 64 tables); and the gateway journal (1 line in 24 h, zero tool mentions).
>
> The runtime **has the schema for this and never populates it**:
> - **`acp_replay_events`** — `(session_id, seq, at, session_key, run_id, update_json)`, i.e. sequenced session-update payloads. This is precisely the right shape: ACP session updates carry `tool_call` / `tool_call_update`. **0 rows** — the agents do not run over the ACP path.
> - **`capture_events`** — protocol-level capture with `method`, `host`, `path`, `status`, `headers_json`, `data_text`, `data_sha256`, plus a companion blob store. If model traffic passed through it, `tool_use` blocks would land in `data_text`. **0 rows.**
>
> **Three routes, ascending cost:**
> 1. **Enable an existing capture path** (`capture_events` over model traffic, or ACP replay if the agents can be routed through it). Cheapest — the storage and schema already exist.
> 2. **Persist tool calls in the session writer.** The `.jsonl` writer already emits typed events; adding `tool_call` to what it persists is a targeted change with a known output location.
> 3. **~~Redefine the estimand at task granularity over `task_runs`~~ — CHECKED AND DEAD.** It would need no instrumentation, but the data does not support it: `task_kind` is **NULL in all 400 rows**, so there is no signature dimension to match repeats on, and `status` shows **2 failures in 400 over 7 days**. A repeated-failure density with a 20% MDE cannot be built on ~2 events per week with no signature.
>
> Routes 1 and 2 live in the agent runtime (OpenClaw), not in nox-mem. Either way the study then needs **accumulated history**, which is calendar time and can run **in parallel with the arXiv gate** — otherwise dead time.

4. W_OUTCOME formula value (0.15) + low-stakes allowlist.
   > **⚠️ MEASURED 2026-07-26 — the risk runs the opposite way from what "nudge" implies.** The additive term only changes a slot if some chunk below the cut sits within `W_OUTCOME × severity` of it, so what matters is the **salience spacing at the cut**, which is measurable today without knowing which chunks are episodes.
   >
   > Over the production candidate pool (500 rows, real `calculateSalience`): salience spans **0.8798 → 0.6094**, the entire **top-10 spans 0.043**, and the gap between rank 8 and rank 9 is **0.0010**.
   >
   > At the proposed `W_OUTCOME = 0.15`, with severity at its ceiling, **303 chunks come within reach of a 10-slot brief**, and **all 10 incumbents sit within 0.15 of the cut** — every one of them displaceable. At 0.10 it is 173 chunks; at 0.20, 452.
   >
   > **0.15 is ~3.5× the entire top-10 spread and ~150× the rank-8→9 gap.** That is not a nudge to brief composition; it is authority to rewrite the brief. The MDE argument in §3 explicitly justifies a 20% target as right "for a brief-composition nudge" — at 0.15 the premise of that sentence does not hold.
   >
   > This is **consistent with, not contrary to,** the T6 dose ceiling. The two measure different things: the architecture blocks *unweighted* new content from the primary slots (T6: a max-pain, max-importance chunk entered 1 of 10 briefs, via the coverage slot), while `W_OUTCOME` at 0.15 **overrides that architecture outright** — the same chunk plus 0.15 lands above the pool maximum.
   >
   > **Recommendation:** parameterize `W_OUTCOME` **relative to the observed salience spread at the cut** rather than as a round absolute. E.g. `W_OUTCOME = α × (s_1 − s_N)`, which at the measured top-10 spread makes α = 1 mean "a maximum-severity episode moves from the cut to the top" — an interpretable unit that survives corpus drift, whereas 0.15 silently means something different as the distribution changes. **[TO LOCK: α]**, with the absolute value it implies recorded at lock.
   >
   > Caveat: the figures are the **ceiling** (severity = 1.0, chunk already in the pool). Realized displacement also depends on how many episode-linked chunks exist and their severity distribution — which needs item 0.
   ⚠️ **Do not wire this to the existing `pain` column.** Measured 2026-07-26: `pain` is a **topical** signal, not an episodic one. It is set two ways, neither of which is a per-episode severity judgment — (a) a v9 backfill (2026-04) that assigned 0.5 to 3,773 chunks, and (b) `inferPain()`, which adds +0.5 when a regex for `incident|outage|breach|critical|emergency|sev-[0-2]|p0` matches the **text**. So a document *about* failure scores like a failure: the largest `pain=0.5` groups are SEC filings (F-4, 20-F, securities purchase agreements) and the `pain≥0.9` set is led by a rollback-mechanisms skill doc and an incident-response reference. Distribution is degenerate — 62,425 chunks at exactly 0.2, 4,129 at exactly 0.5, 566 at 1.0. A treatment keyed to `pain` would boost SEC filings, not lessons. Severity must come from the adjudication panel (§4.1), as already specified.
5. `sig()` taxonomy + frozen pipeline commit + synthetic-input PAP hash. ⛔ **Taxonomy blocked on item 0** — it cannot be derived from an action stream that is not recorded, and inventing the classes would be designing the taxonomy toward the result. The **pipeline freeze and PAP hash are unblocked** (P2S1 closed) and can proceed independently.
6. Severity (0.5) + Fleiss' κ (≥ 0.75) thresholds.
   > **These are not two decisions — they are one.** Lowering the severity cut adds episodes (more power) *and* admits borderline cases where the panel disagrees, pushing κ down toward the floor that kills the primary. Raising it does the reverse. Locking two scalars separately locks two halves of a trade-off as if they were independent. **Lock pairs `(τ, κ_floor)`, and state that κ is evaluated at the primary cut ONLY** — the {0.4,0.5,0.6}×{0.6,0.7,0.8} band is 9 cells, and without that sentence there are 9 chances to land on the convenient one, exactly the discretion §0b exists to remove.
   >
   > **⚠️ Severity is an unanchored float, and that silently disarms the safety rule.** §3's mechanical abort triggers on median severity **exactly 1.0** and counts incidents at ≥ **0.8**, on this same scale. A median of exactly 1.0 requires 3 of 5 panelists pinning the ceiling — which LLM panels rarely do. **The abort's clause (a) may be practically untriggerable**, and that is the mechanism protecting production, not a metric detail. Fix: lock an **anchored ordinal rubric** (discrete levels with operational descriptions) instead of a decimal; the sensitivity band becomes "primary level ± 1 level", well-positioned by construction, and the abort trigger becomes operative again.
   >
   > **Two more gaps that need no data:** §4.1 defines repeated failure via "adjudicated failure", but also defines a *binary majority verdict* separate from median severity — whether condition (ii) means the binary or `severity ≥ τ` changes whether τ moves numerator and denominator together, and is unwritten. And "Fleiss' κ" is a **nominal** statistic; if severity is ordinal the right coefficient is weighted κ, Krippendorff's ordinal α, or Gwet's AC2 — the prereg does not say *what* κ is computed over.
   >
   > **On the κ floor itself:** with rare failures and skewed marginals, the kappa paradox means high raw agreement can coexist with κ near zero, so a high floor on a rare binary label is close to a pre-declaration of "inconclusive". And the asymmetry runs the other way from intuition: with arm-blind adjudication, non-differential misclassification **attenuates toward the null**, and the permutation test's type-I error is exact regardless of κ. **A low κ costs power and effect magnitude, not validity** — it is a conservative error. Recommendation: graduated bands (≥0.75 clean · 0.60–0.75 reported with mandatory caveat and attenuation bound · <0.60 inconclusive) rather than a single cliff, keeping 0.75 — which is Fleiss' own "excellent" cut — as the top of the clean band rather than the floor of the gate.
   >
   > ⛔ **Still blocked on item 0** for the numeric cut: with no episode corpus, the pre-registered sensitivity band cannot be checked against a real distribution. Worth noting from the proxy that does exist: `pain`'s distribution is so lumpy that the analogous band {0.4, 0.5, 0.6} would be badly placed — 0.4 and 0.5 differ by 23 chunks while 0.6 drops 84% of the set. That is a property of `pain`, not of adjudicated severity, but it is the reason to calibrate the band against the real distribution rather than pick round numbers.
7. Pilot function `f` locked **before** pilot; then N_epochs, MDE (20%), calendar end, power curve. **Correction (2026-07-26):** an earlier plan asserted that the T6 shadow run would supply the variance this curve needs. It does not — `r̂`, `p̂0` and ICC are **outcome** quantities and the shadow runs with no live arms and no outcome. They come from the pilot, per §3. What T6 supplies instead is the **dose ceiling** (§3), which constrains which MDE is attainable at all.
8. Coverage floor (95%) + unadjudicable ceiling (10%) + winsorization (p95).
   > **Three of the numbers are fine. Two things next to them are defects — and neither needs data to fix.**
   >
   > **(a) The `|r| > 0.2` gate false-fires at a rate nobody computed.** §5 declares the primary "compromised" if coverage loss correlates with arm at `|r| > 0.2`. Under the null of no association, the Fisher-z SE is `1/√(K−3)` and `atanh(0.2) = 0.2027`, so the gate fires **by chance alone** at:
   >
   > | K epochs | 30 | 34 | 46 | 60 | 70 | 100 |
   > |---|---|---|---|---|---|---|
   > | P(spurious "compromised") | **29.2%** | **25.9%** | **18.4%** | 12.6% | 9.7% | 4.6% |
   >
   > **This lands exactly where the study will live.** The §9.7 sizing function, run with inputs of the order now measurable from the action corpus, returns **34–70 epochs** for 80% power at a 20% MDE — the range where this gate misfires between roughly one in four and one in ten runs. Replace the fixed threshold with a test at the declared α, or better a TOST against a pre-declared irrelevance band (the claim being sought is *absence* of association, which a rejection test does not deliver). Verified independently by closed-form arithmetic, twice.
   >
   > **(b) Coverage is a post-randomization variable.** §5 justifies exclusions on the ground that they are *arm-blind*. Arm-blindness is not sufficient: treatment can in principle affect coverage (different brief composition → different retrieval load → different logging failure), and conditioning on a post-treatment variable breaks randomization-based inference even when the rule never reads the arm label. **Fix, one line:** pre-commit the **ITT with no coverage exclusion** (all post-washout epochs) as a mandatory co-estimate beside the filtered primary. Agreement is the strength of the claim; divergence is reported.
   >
   > **(c) Winsorizing at p95 amputates where the hypothesis lives.** The paper's thesis is that remembering failures avoids *repeating the expensive ones* — the hypothesized value sits in the right tail. §5 already uses a permutation test, whose type-I error is exact under any tail, so winsorization here buys **precision, not validity**. Test H2 on raw values; apply p95 only to the effect *estimator*, computed **pooled across arms, once, arm-blind** (per-arm winsorization would mechanically erase between-arm tail differences — deleting the effect with the instrument); and pre-commit an explicit tail metric alongside.
   >
   > **The structural problem is topology, not height.** Items 4.1, 5 and 3 place **three conjunctive cliffs** (κ floor, unadjudicable ceiling, coverage-correlation gate) plus two degraders on a single run, none with a "reported with caveat" band. Only one of the three has a computable failure probability today, and it is not small. The most likely failure mode of the study is **paying for everything and reporting nothing** — which would return the paper to Route 1, the outcome the whole snapshot mechanism was built to avoid. Recommendation: keep the thresholds, replace the cliffs with graduated bands and pre-committed Manski bounds for the unadjudicable stratum.
9. ~~Appendix A (H3 figure specs) + Appendix B (bounds math) written~~ ✅ **WRITTEN 2026-07-26.** A: three frozen figures (retrieval-vs-decision scatter per metric + ordering slope chart), inclusion rules, no binning, and the stated condition that would falsify the H3 narrative. B: bounded-carry-over assumption (B1), the bound τ̂ ± δ·|p₁−p₀|, and the observation that |p₁−p₀| is a **design** quantity driven to zero by transition balancing — so the bound narrows by construction, not by assumption. **Still [TO LOCK]: the numeric δ**, which can only be honestly fixed from the pilot's same-arm transition distribution (before it = invented; after seeing effects = adaptive).
10. ~~Ethics/IRB statement~~ ✅ **WRITTEN 2026-07-26** → **Appendix C**. Exemption is claimed on the substantive ground (no human subjects, no third-party data), and the appendix states plainly what the study *does* touch — the author's own production system — and what bounds harm there (low-stakes restriction + mechanical abort). It also declares the COI without softening it.

**New [TO LOCK] items created by the v0.3 independence model:** drand chain hash · `T_seed` (UTC instant, post-registration / pre-M4) · Bitcoin fallback height rule · abort rule parameters (severity 0.8 · window 3 epochs · 3× baseline · 90-day baseline period) · panel size and exact model ids · adjudication prompt hash · minimum valid verdicts for majority (3).

## Appendix A — H3 figure specs (pre-committed; frozen before unblinding)

H3 is exploratory and yields **no confirmatory claim**. Its role is falsifiable in one direction only: if retrieval metrics ordered the policies the way H1 does, the paper's central argument — that retrieval quality is a proxy that can come apart from decision quality — would be weakened. These specs are frozen here so that the figures cannot be chosen after seeing which ones flatter that argument.

**Unit of observation.** One point per *policy-epoch* (arm × epoch), not per brief. Per-brief points would inflate n by a factor of the brief count and invite reading precision that the design does not support.

**Fig. A1 — retrieval vs. decision.** Scatter. *x* = mean nDCG@10 over the briefs served in that policy-epoch; *y* = H1 repeated-failure density (failures / session-hour) for the same policy-epoch. Marker shape by arm, no colour dependence (accessibility). One OLS line per arm with 95% CI band. Reported statistic: **Spearman ρ with bootstrap CI (10,000 resamples, epoch-level resampling)** — rank-based because neither axis is assumed linear or normal.

**Fig. A2 — the same, for recall@10.** Identical construction. Reported separately rather than averaged with nDCG: they answer different questions (ranking quality vs. coverage) and collapsing them would hide a divergence between the two.

**Fig. A3 — ordering disagreement.** Slope chart. Left axis ranks the two arms by mean nDCG@10; right axis ranks them by H1 density. A crossing line **is** the visual statement of H3. Annotated with the count of epochs in which the two orderings disagree.

**Inclusion rules (frozen).**
- Only post-washout epochs (§2), consistent with the primary analysis set.
- Epochs failing the coverage floor (§9.8) are excluded from A1–A3 and **shown as a separate count**, never silently dropped.
- No winsorization on the retrieval axes. Winsorization applies to task regret (§4.2) only; applying it here would smooth exactly the tail that H3 is about.

**Binning.** None. Raw points. If overplotting obscures the pattern at the realized *n*, add transparency — never bin, because binning choices are precisely the free parameter this appendix exists to remove.

**What would falsify the H3 narrative.** Spearman ρ CI excluding zero *with the sign that makes retrieval track decision quality*, in both A1 and A2, plus no ordering disagreement in A3. That outcome is reportable as-is; it does not invalidate H1, but it removes the paper's proxy-divergence argument and must be stated in the abstract if observed.

---

## Appendix B — Interference bounds under snapshot carry-over

### B.1 Why bounds and not a point estimate

The crossover is fleet-wide (§0), so no two agents are in different arms at the same instant — cross-agent contamination is designed out. What remains is **temporal**: epoch *k* is served from snapshot *S_k*, and *S_k* was written during epoch *k−1*, under *its* arm. So the potential outcome in *k* depends on *k*'s assignment **and** on *k−1*'s.

That is interference, and it violates the SUTVA form under which a difference-in-means identifies the direct effect. The design attacks it three ways (§5): restricting to A→B transitions, adjusting for lag-1 arm, and — here — **bounding** the direct effect under an explicit, declared limit on how much the predecessor arm can matter.

### B.2 Setup

Let epochs be indexed *k = 1 … K*, each with arm *W_k ∈ {0,1}*. Write the potential outcome as

> *Y_k(w, w′)* — outcome in epoch *k* when its own arm is *w* and its predecessor's arm is *w′*.

The **direct effect** is the estimand of interest:

> *τ = E[ Y_k(1, w′) − Y_k(0, w′) ]*, averaged over the realized distribution of *w′*.

The naive contrast *τ̂ = Ȳ(W=1) − Ȳ(W=0)* is biased by carry-over whenever *P(w′=1 | w=1) ≠ P(w′=1 | w=0)*, which the balancing constraints reduce but do not force to zero at finite *K*.

### B.3 The bounded-interference assumption

**Assumption B1 (bounded carry-over).** There exists δ ≥ 0 such that, for all *k* and all *w*,

> | *Y_k(w, 1) − Y_k(w, 0)* | ≤ δ

That is: the predecessor's arm can move the outcome by at most δ, whatever the epoch's own arm. δ is on the **outcome scale** (repeated failures per session-hour), so it is interpretable and must be justified, not assumed convenient.

B1 is weaker than no-interference (δ = 0) and strictly weaker than a parametric lag-1 model, which assumes carry-over is *linear and additive* in the predecessor arm. B1 assumes only that it is **bounded**.

### B.4 The bounds

Under B1, with *p₁ = P(w′ = 1 | w = 1)* and *p₀ = P(w′ = 1 | w = 0)* estimated from the realized sequence:

> *τ ∈ [ τ̂ − δ·|p₁ − p₀| , τ̂ + δ·|p₁ − p₀| ]*

The width is **δ · |p₁ − p₀|**, which factorizes usefully:

- **δ** is the substantive question — how much can yesterday's policy shape today's outcome through the snapshot?
- **|p₁ − p₀|** is a **design** quantity, computable from the assignment sequence before any outcome is seen, and driven to zero by transition-balancing. At perfect balance the bound collapses to a point regardless of δ.

This is the practical payoff of pre-registering the balancing constraints: it makes the bound narrow by construction rather than by assumption.

### B.5 Choosing δ — and why it is not free

δ must be **pre-committed**. Two anchors, both reported:

1. **Empirical anchor.** The observed epoch-to-epoch variation in the primary outcome under the *same* arm (control→control transitions) upper-bounds what non-arm noise contributes. δ is set to the p95 of the absolute epoch-to-epoch difference in those same-arm transitions. This is conservative: it attributes *all* same-arm drift to carry-over.

2. **Mechanistic anchor.** The measured content divergence between successive snapshots. From T7 of the snapshot spec, the corpus divergence per 24 h epoch is **0.144%** and the divergence in what the brief actually serves was **0 of 7,235 slots** in the one epoch with serving data. A snapshot that is ~99.86% identical to its predecessor cannot plausibly carry a large behavioural effect — but the serving-level figure has **n = 1** and is reported as such.

**[TO LOCK]** the numeric δ, after the pilot supplies the same-arm transition distribution. Locking it before that would be inventing a number; locking it after seeing treatment effects would be adaptive. The pilot is the only window in which it can be honestly fixed.

### B.6 Reporting rule

Reported alongside the primary and the other two co-estimates (§5), always together and always with δ stated in outcome units:

- if the bound **excludes zero**, the causal claim survives even under the pre-committed worst case;
- if it **includes zero** while the point estimate does not, that is reported as-is — the effect is not robust to carry-over of magnitude δ, and the abstract says so.

Concordance across the four (primary, A→B-restricted, lag-1, bounds) is the strength of the claim. Divergence is not repaired; it is reported.

### B.7 What this appendix does not do

It does not bound **cross-agent** interference — the fleet-wide design removes it by construction, not by assumption, and if that design changes this appendix no longer applies. It also does not cover carry-over at lags > 1: the washout (§2) plus first-epoch-after-washout estimand are what address those, and B1 is silent about them by construction.

---

## Appendix C — Ethics and IRB statement

**Human subjects: none.** No person is enrolled, assigned, observed as a subject, or asked to perform any task for this study. The units of randomization are software agents; the units of observation are their execution traces.

**Human research contributors: none.** Adjudication — the only step that could plausibly require human judgement — is performed by a frozen panel of language models from distinct training families (§4.1). The sole author's involvement is confined to mechanically-triggered tie-breaks under a rule fixed before unblinding, and each such intervention is logged with its trigger. This is deliberate: the independence model of this registration is **structural**, not delegated to people (§0b), precisely because the author is also the operator and the beneficiary.

**Third-party data: none un-hashed.** The agents operate on the author's own production system. Content that enters the benchmark does so as hashed chunk identifiers and derived metrics (§4.3), never as raw text from any third party. No data is collected from anyone who is not the author.

**IRB determination.** Under the common-rule definition, research with no human subjects and no identifiable private information about living individuals does not require IRB review. As an independent researcher without institutional affiliation for this work, no IRB of record exists; this appendix is the filed determination and the basis for it. If the design later admits any human participant or third-party data, this determination lapses and review must be sought before that change takes effect.

**What the study does touch.** It manipulates the memory policy of a live production system that the author depends on daily. That is a real operational risk, not a hypothetical one, and it is bounded rather than dismissed:

- the treatment arm is restricted to a pre-registered **low-stakes allowlist** (§9.4), so high-consequence actions never vary by arm;
- a **mechanical abort rule** (§3) halts the whole study — never a single arm, which would unblind — on a pre-committed severity/frequency trigger, without requiring the author to notice or to agree;
- the serving-side snapshot mechanism **degrades to the live store** rather than serving nothing, so a failure in the experimental apparatus cannot deny the system its memory (§P2S1 T8).

**Conflict of interest.** Maximal and irreducible: the author designed the system under test, owns it, benefits from a positive result, and is the only person in the loop. This registration does not claim that conflict away. It answers it by removing discretion — public-beacon seed, mechanical abort, frozen multi-family adjudication, exclusions-as-code, and an ordering proof published before the join is executed (§0b, §2). Every one of those is verifiable by a third party from the artifact alone, which is the point: the reader is not asked to trust the author's restraint.

**Animals, deception, compensation, consent:** not applicable — no participants exist to be deceived, compensated, or consented.
