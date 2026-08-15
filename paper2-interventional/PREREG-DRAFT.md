# OSF Pre-Registration — v1.2, **BLOCKED** on one undefined term

> ### ⛔ NOT READY TO REGISTER — blocked 2026-08-15, after v1.1 was declared ready
>
> A pre-treatment measurement run today (`dose_reach.mjs`) answered the dose question and, in doing so, exposed that the treatment arm contains an **undefined term**: `W_OUTCOME × severity` applies to *"chunks linked to adjudicated-failure episodes"*, and **"linked" is never operationally defined** — there is no join key between episodes and chunks, and the obvious wiring is explicitly forbidden. An underspecified arm is not randomisable, so registration waits on one lock. Detail in §3 (the dose measurement) and §9-4 (the gap). Everything else in this document is unchanged and remains locked.
>
> **Status: v1.2 — 2026-08-15.** *(Date-gated conditions written in the future tense elsewhere in this document — "no earlier than 2026-08-09" and similar — were all satisfied before this status line was written.)* Every `[TO LOCK]` item that required analysis is closed. The two that remain resolve in sequence and by construction: `T_seed_assign` needs the OSF registration timestamp to exist first, and the calendar end date needs the first randomized epoch, which has not occurred. **No randomized epoch exists; the study has not started.** Everything measured here is pre-treatment, over a historical corpus with no arm assignment.
>
> ### ✅ `N_epochs` corrigido para cumprir o lock (b) — 2026-08-15
>
> Revisão adversarial (Kimi/Moonshot) encontrou, e a verificação confirmou: o lock **(b) de 2026-07-30** determina *"Size on the upper 95% confidence limit of the ICC, **not** the point estimate"* — sub-dimensionar invalida um estudo completo, super-dimensionar custa calendário — e explicitamente *"not a refinement"*.
>
> **O primeiro lock deste dia violou isso sem dizer.** `N` = 154 era MDE 25% **no ponto estimado** — e nem isso: o valor canônico a 25% no ponto é **152** (`sizing.py` com os inputs de `SIZING-2026-08-14-v2.md`; a tabela §3 daquele documento sempre disse 152). O 154 era um erro de dois epochs que se propagou por sete menções sem nunca ter saído do código.
>
> ⚠️ **Os dois defeitos são independentes e o segundo é o menor.** Errar 152 por 154 é aritmética; dimensionar no ponto quando um lock manda dimensionar no limite superior é padrão de decisão. O primeiro se corrige com um número, o segundo com uma regra — e é o segundo que a memória `feedback_estimator_choice_inside_the_noise` já registrava. o lock (b) exigia a coluna do limite superior. Pior que o número foi o padrão: a mesma nota aplicava disciplina para *não* reduzir de 154 para 46 — "toda razão que aponta para estudo mais curto merece mais suspeita" — sem notar que 154 já era uma redução silenciosa frente ao que um lock anterior exigia. Conservador onde era barato, não conservador onde custava calendário.
>
> **Corrigido no mesmo dia, antes de qualquer epoch randomizado: `N_epochs` = 174, MDE declarado em 30%, dimensionado no LIMITE SUPERIOR do ICC (0,1814).**
>
> | MDE | no ponto | **no limite superior — o que o lock (b) manda** |
> |---|---|---|
> | 20% | 242 | 410 |
> | 25% | ~~152~~ | 256 |
> | **30%** | 102 | **174 ← LOCKED** |
>
> A escolha de 30% em vez de 25% é alocação de calendário (174 dias contra 256), tomada com a tabela inteira à vista e **antes** de existir qualquer dado de braço. O que ela compra não é um estudo mais curto que o correto — é o estudo correto sob o lock que já estava no papel. O que ela custa está no §3 e no abstract: efeitos abaixo de 30% relativos não serão detectados de forma confiável.
>
> **Locked 2026-08-15:** `N_epochs` = **174** · MDE declared at **30%** via the §3 escape clause, sized on the **upper confidence limit** of the ICC per lock (b) (the 20% target is not amended, and is not reached) · `δ` = 36,67 · task-regret `p95` = 7,45 s / 65 206 tokens.
>
> **Version history.** v0.1, 2026-07-25. v0.1 was adversarially reviewed by GLM-5.2 (5 FATAL / 7 GRAVE / 10 minor — full verdict in `REVIEWS-PREREG.md`); v0.2 incorporated every fix independent of the route decision; **Route 2-lite decided 2026-07-12** (§0) — the route decision *precedes* v0.1 because the routes were argued out in `DECISIONS.md` before this document existed; v0.1 is the first draft that assumes the decision, not the one that made it. v0.1 and v0.3 share the date 2026-07-25 because both landed that day: v0.1 was reviewed and revised within the same session. **v0.3 (2026-07-25, Toto's call): no human auditor and no human data monitor will be appointed. Independence is provided structurally — by public randomness, frozen hashes, mechanical rules, and open artifacts — rather than delegated to named individuals** (§0b). Locking now blocked only on the remaining **[TO LOCK]** items (§9). This document becomes binding only when registered on OSF with a public timestamp **before** any A/B data collection.
> **Companion docs:** `CONCEPT-NOTE.md` · `METHODOLOGY.md` · `DECISIONS.md` · `REVIEWS-PREREG.md`.
>
> **Decimal separator.** This document mixes `,` and `.` as the decimal mark: text written in Portuguese and figures quoted from the Portuguese analysis documents use `0,0985`; text written in English and figures quoted from English-language reviews use `0.0985`. It is a provenance artefact, not two different numbers. Deliberately not normalised, because rewriting quoted figures would break the correspondence with the source documents they are cited from.

---

## 0. Route decision — ✅ DECIDED: Route 2-lite (Toto, 2026-07-12)

The v0.1 design (cluster = agent × time-block + washout over a *shared* store) does **not** neutralize cross-arm interference: treated sessions write content that control sessions later read, and agents in different arms co-exist on the store in real time (F1). Three defensible routes:

| Route | Claim retained | Design change | Cost | Venue fit |
|---|---|---|---|---|
| **1 — Conservative** | No point-identified causal claim; replay = main contribution, A/B = qualitative fidelity check | None | Low | COLM/EMNLP resource |
| **2 — Clean redesign** | Full causal claim | Arm switch per **whole agent-fleet epoch** with **per-arm store state** (snapshot/flush between epochs) | High (ops) | COLM full / NeurIPS D&B |
| **3 — Formal analysis** | Causal claim **as bounds**, not point | Keep design; potential-outcomes estimand + interference bounds (Aronow–Samii-style) + restricted co-estimands | Medium | COLM (D&B risky) |

**DECIDED — Route 2-lite** (Toto, 2026-07-12): keep the crossover but make the *epoch* fleet-wide (every agent on the frozen allowlist switches arm together per time-block, so no cross-agent arm mixing exists at any instant — see §2 on why this is stated as membership rather than as a headcount) and add a **store snapshot at each epoch boundary**: each arm's briefs are served from the snapshot taken at its epoch start (serving-side freeze), while writes continue to the live store for production safety. This removes simultaneous cross-arm contamination (all agents same arm) and bounds carry-over to the snapshot boundary; residual carry-over (behavior in epoch *k* shaping the snapshot of epoch *k+1*) is handled by the first-epoch-after-washout estimand + A-B-A-B sensitivity (§5). Rationale vs. alternatives: Route 1 gives up the causal claim the paper needs for COLM full / D&B; Route 3 leaves F1/F4 indefensible per the GLM verdict; full Route 2 (per-arm store with write flush) buys little over 2-lite at much higher operational risk to production. Route 1 remains the documented **fallback** if the snapshot mechanism proves operationally infeasible — the design below degrades to it by dropping §1-H1's causal phrasing.

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

**Description.** A fleet of production LLM agents — **seven at the time of the frozen snapshot**, membership pinned by allowlist rather than by count (§2) — shares a persistent memory system (nox-mem, in production since 2026-03). Each session receives a memory *brief* at start. We test whether weighting brief composition by **episode outcome** (adjudicated failure severity of past actions) changes repeated-failure behavior relative to the production flat/salience-only policy. This randomized arm is the **only** component of the project for which causal language is used; the retrospective benchmark is a declared observational log study, out of scope here (§8).

**Background (non-substantive addition, 2026-08-13).** A concurrent survey of foundation-agent memory (Huang et al., *A Survey of Agent Memory in the Second Half: Towards Self-Evolving and Long-Horizon Agents*, TMLR 07/2026; arXiv:2602.06052v4), covering 218 papers, catalogues the evaluation metrics in use across the field (its Table 3) and finds them exhaustively partitioned into accuracy-based, similarity-based, and LLM-as-judge families — none of which measures whether retrieved memory changed the agent's **decision or action**. Its §9.6 independently names the design this registration implements as an open direction: closed-loop, longitudinal, execution-grounded evaluation comparing "memory-augmented agents and memory-free baselines under identical conditions", with provenance metadata, versioned and rollback-able persistent state, and explicit resource–utility accounting. The strings *pre-registration* and *preregistration* do not occur in that survey; *interventional* and *counterfactual* occur once each, the latter only as a suggested future direction. **This paragraph records the gap the study addresses and introduces no hypothesis, outcome, covariate, or analysis choice: H1–H3, the sampling plan, and the pre-declared seed are unchanged.**

**Hypotheses.** All confirmatory tests are **two-sided**; expected directions are stated as expectations, not test choices (G2 fix).

- **H1 (primary, confirmatory):** the **unconditional repeated-failure density** (repeated failures per session-hour, §4.1) *differs* between arms. Expected direction: lower under treatment.
- **H1a–c (co-primary family, Holm-corrected; F2 fix):** (a) eligible-opportunity rate per session-hour; (b) repeat-attempt rate given opportunity; (c) repeated-failure rate given opportunity. Reported jointly so a change in the denominator cannot masquerade as (or mask) an effect in the conditional rate.
- **H2 (secondary, confirmatory):** task regret (§4.2) differs between arms.
- **H3 (exploratory, declared):** retrieval metrics (nDCG@10, recall@10) computed on the same briefs do not order the policies the way H1 does. **Figure specs for H3 are pre-committed in Appendix A before unblinding** (M5); no confirmatory claim from H3.

## 2. Design Plan

**Study type.** Randomized crossover on live production traffic, **fleet-wide epochs**: every agent in the fleet is in the same arm at any instant (kills simultaneous cross-arm contamination by construction).

**The fleet is a frozen allowlist, not a headcount — and its membership varies (corrected 2026-07-29).** Earlier drafts said "all 6 agents", which was true when written and is no longer: the fleet grew to **seven** (`atlas`, `boris`, `cipher`, `forge`, `gordon-gekko`, `lex`, `nox`, plus the `main` workspace root as an eighth action source), and at least one agent has since been suspended. A design that names a number re-breaks every time the roster moves, so the membership is instead **pinned as an explicit allowlist in the frozen commit**, and three consequences are pre-committed rather than discovered later:

- **The `fleet-wide` property survives roster change.** It requires that all *currently active* agents switch arm together, not that the count be constant. Adding or suspending an agent does not create cross-arm contamination; the simultaneity is what the property asserts.
- **What roster change does affect is volume and generalisability, not identification.** A suspension reduces session-hours (hence power) and narrows the population the estimate speaks for. Both are reported: the per-epoch active roster is logged alongside each epoch, and the paper carries the roster timeline.
- **Agents that join after the registration timestamp are excluded** from the analysis set by default, since their traffic has no pre-treatment baseline. Including one requires a logged deviation (M3).

Observed roster activity over the frozen snapshot window (2026-07-18 → 07-28) is stable for all seven, at 2–51 sessions/day each; `gordon-gekko` runs at exactly 16/day, a signature of scheduled rather than interactive traffic, and is flagged for the low-stakes allowlist decision.

**Randomization unit.** **Epoch** = fleet × time-block of **24 h, boundary 06:00 BRT — LOCKED 2026-07-29**, and already the value running in production: `cron 0 6 * * *` invoking `nox-epoch-boundary.sh`, verified in the live crontab, with natural rotations observed since 2026-07-27. Epochs assigned to arm by constrained randomization balancing weekday/weekend and calendar halves.

**Seed — public randomness beacon (replaces the data monitor; §0b).** The assignment sequence is generated once by a committed, deterministic script from a seed that **does not exist at registration time and is outside author control**:

- **Beacon:** `drand` / League of Entropy — **LOCKED 2026-07-29: quicknet, chain `52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971`** (3 s rounds, genesis `1692803367`, publicly verifiable BLS output, multi-organization threshold — no single party, including the authors, can predict or influence it). Same chain already exercised end-to-end for the calibration seed (`CALIBRATION-SEED.md`), so the derivation path is verified rather than assumed.
- **Derivation rule, committed at registration:** `seed = SHA256(randomness_hex(R))`, where `R` is the **first drand round with timestamp ≥ T_seed_assign**, and `T_seed_assign` is a wall-clock instant **[TO LOCK: date/time UTC]** that is strictly after the OSF registration timestamp and strictly before the first treatment epoch (M4).
  - **`randomness_hex` is the lowercase ASCII hex string, hashed as text — not the decoded bytes.** The two differ: for round 30800000, `SHA256(ascii)` = `1ae88fbf27fe83bc…` while `SHA256(bytes)` = `0e6824e682b9d776…`. Leaving this implicit would make third-party verification a coin flip.
  - **Endpoint is the v1 API**, `https://api.drand.sh/<chain>/public/<R>`. The v2 endpoint returns only `round` and `signature` — it has no `randomness` field, so a rule that does not name the endpoint is not reproducible. (Both points verified against the live API, 2026-07-28.)
- **What is registered pre-hoc:** the chain hash, `T_seed_assign`, the derivation rule above, the assignment script (with its commit hash), and the balancing constraints. **What is not knowable pre-hoc:** the seed itself.
- **Verification:** anyone can, at any time, fetch round `R` from any drand relay, recompute the seed, re-run the committed script, and confirm the published assignment sequence bit-for-bit. Manipulation would require forging a threshold signature from the League of Entropy.
- **Fallback (if the beacon is unreachable at `T_seed_assign`):** `seed = SHA256(block_hash(H))` where `H` is the **first Bitcoin block height mined at or after `T_seed`**, pre-declared in the same registration. Fallback use is itself logged in the deviations changelog (M3).

Both the derived seed and the resulting assignment sequence are published to OSF **before the first treatment epoch** (M4), together with the round number, the raw beacon output, and the recomputation script.

**Estimand (potential outcomes; G4 fix).** For session-hour unit *i* in epoch *k*, let `Y_i(a, S_k)` be the outcome under arm `a ∈ {0,1}` with serving snapshot `S_k`. The estimand is the average serving-policy effect
`τ = E[ Y_i(1, S_k) − Y_i(0, S_k) ]`
over the realized snapshot sequence — i.e., the effect of *which chunks are served*, with the write path identical in both arms and snapshots evolving under the realized mixed history. This is a **policy effect along the realized trajectory**, not the effect of deploying the treatment permanently; that broader estimand is declared out of reach of this design and is not claimed.

**Interference handling (F1 fix, layered):**
1. **No simultaneous mixing:** fleet-wide epochs — at no instant do treated and control sessions coexist.
2. **Serving-side snapshot:** briefs in epoch *k* are served from snapshot `S_k` (store state at epoch start, post-washout); writes continue to the live store untouched. Carry-over is thus confined to *content* differences between successive snapshots.
3. **Washout: first 2 h of each epoch excluded from analysis — LOCKED 2026-07-29, sized against the measured session-duration distribution, not proposed.** *(Two different p95s appear in this registration and must not be conflated: the **session-span** p95 of 9.6 min sizes the washout here; the **task-regret** p95 of 7,45 s / 65 206 tokens in Appendix B is the cost of a repeated failure. Different estimands, different units, no contradiction.)* Over the frozen snapshot (525 multi-episode sessions): median span **22 s**, p90 **3.6 min**, p95 **9.6 min**. A 2 h window therefore clears **96.8%** of sessions with three orders of magnitude to spare, and the value is retained (rather than tightened to ~10 min) purely as margin.

   ⚠️ **The distribution is bimodal and the tail is not a washout problem.** p99 jumps to **33.5 h** and the maximum is **158 h** — a discontinuity of two orders of magnitude above p95, consistent with two populations: interactive sessions (seconds to minutes) and long-running processes (days). **3.2% of sessions outlast an entire 24 h epoch**, and some span six. No washout length fixes this: the brief is served once at session start, so such a session is correctly attributed to its starting epoch, but its *actions* continue to execute for days, potentially while the fleet has switched arms. Boundary-straddling sessions are assigned to the epoch of their start, flagged, with sensitivity with/without — and, additionally pre-committed here, **sessions whose span exceeds one epoch length are reported as their own stratum**, since for them the arm assignment is genuinely ambiguous rather than merely edge-adjacent.
4. **Primary carry-over guard:** the primary analysis set is **all post-washout session-hours**; a pre-committed co-estimate restricts to epochs whose *predecessor was control* (A→B transitions), isolating treatment effects from treatment-shaped snapshots (F4/GLM fix #1).
5. **Quantitative sensitivity (G6):** pre-committed co-estimates — (i) A→B-restricted (above); (ii) lag-1-adjusted regression (predecessor arm as covariate); (iii) partial-identification bounds under bounded-interference assumptions (Aronow–Samii-style, bound parameter reported, math in **Appendix B — written 2026-07-26**, per §9-9). All three reported alongside the primary.

**Arms.**
- **Control:** production brief policy `NOX_BRIEF_DIVERSITY=active`, activated by the systemd drop-in `d2-brief-diversity-active.conf` — **LOCKED 2026-07-29, SHA-256 `76726519559ffbe65283610b9d4efe4c17a0d74933363c235e3859ef28af267c`** (the companion `p2s1-shadow.conf`, which carries `NOX_EPOCH_SNAPSHOT`, hashes to `3d27b98d…`). The policy is pinned to the drop-in rather than to a repository commit because that file is what the running service reads; a commit hash would not have caught a drift between repo and host.
- **Treatment:** identical + additive outcome-weighted term `W_OUTCOME × severity` on chunks linked to adjudicated-failure episodes, severity per the ordinal mapping in §4.1. **LOCKED 2026-07-29:** the coefficient is re-expressed as `W_OUTCOME = w × Δ_cut` — a multiple of the measured salience spread at the brief cut, not a bare constant — with sensitivity over `w ∈ {0.5, 1.0, 2.0}` pre-registered as secondary, replacing the absolute `{0.10, 0.15, 0.20}`. (Additive per the Paper-1 v3.4 lesson: multiplicative boosts are unstable.)

  **Severity stays graded — an earlier draft of this lock collapsed it to binary and was wrong.** The collapse was justified by Fleiss' κ = 0.640 over the five levels, read as failing the ≥ 0.75 floor. Fleiss' κ is a *nominal* coefficient, which this section already warns against for exactly this scale: it scores an S1-vs-S2 disagreement as harshly as S0-vs-S4. Under the coefficient this protocol actually pre-registers for target (β), **Krippendorff's ordinal α = 0.853** — above the floor, reported without caveat. The graded severity is reliable; the number that said otherwise was the wrong statistic.

  **Why relative to the spread.** `0.15` is uninterpretable on its own. Measured against the salience spacing it has to move — `Δ_cut = 0.043`, the spread across the top-10 slots (§9-4) — it is **3.5× the entire spread**, which is authority to rewrite the brief rather than a nudge. Stating the dose as a multiple of `Δ_cut` makes it self-interpreting: `w = 1.0` can displace roughly one boundary position, which is what "nudge" was supposed to mean. It also removes a parameter — one `w` replaces `W_OUTCOME` plus a five-level mapping.

  **`Δ_cut` is frozen pre-treatment.** It is measured over the baseline period preceding the pilot and fixed at registration. It is *not* recomputed per epoch: treatment changes brief composition, so a live `Δ_cut` would be a post-randomization quantity and would break randomization-based inference — the same defect corrected for coverage on 2026-07-26, and it would have been reintroduced here.
- **Scope:** low-stakes sessions only, per pre-committed task-type allowlist — **LOCKED 2026-07-29**, defined over the `sig_coarse` taxonomy and sized against the measured action distribution:

  | | classes | share of corpus |
  |---|---|---|
  | **in scope** | `leitura\|arquivo` · `busca\|externo` · `mcp\|*` | 41.0% |
  | **in scope, with `fine` adjudicating case by case** | `execucao\|processo` · `execucao\|arquivo` | 44.8% |
  | **excluded — always control** | `escrita\|arquivo` · `execucao\|vcs` · `execucao\|estado` | 12.2% |

  The excluded classes are the ones whose failure mode is irreversible state change: file writes, VCS mutation, and service/state manipulation. The two middle classes are admitted because excluding them would remove **44.8% of all actions** and leave the study without power — but they are heterogeneous (`execucao|processo` covers both `ls` and `systemctl restart`), so eligibility inside them is decided at the **`fine`** granularity, which separates `git:log` from `git:push`. High-stakes sessions always get control and are excluded; the exclusion is arm-independent by construction.

**Blinding (no auditor sign-off; §0b).** Outcome adjudication is blind to arm: adjudicators receive episodes with arm labels, sub-day timestamps, and policy metadata stripped. The trace→action→outcome→failure pipeline is deterministic, frozen at commit **`c0abe143` (LOCKED 2026-07-29)**, and validated end-to-end on a **synthetic input set with committed expected-output hash** (M2).

The auditor's pre-unblinding sign-off is replaced by an **ordering proof**, which is strictly checkable rather than attested:

1. Arm labels live in a **separate artifact** from the episode corpus; the adjudication pipeline reads only the corpus and cannot join to labels.
2. The **complete adjudication output is hashed and the hash published to OSF (and as a signed git tag) *before* the join to arm labels is ever executed.**
3. Unblinding is a single deterministic join script, itself in the frozen commit. Re-running it against the published verdicts must reproduce the analysis inputs exactly.

Because the verdict hash carries a public timestamp that precedes the join, adjudication cannot have been tuned to arm without breaking the hash — a check any reader can perform, at any time, without having been present.

**Ethics (M1).** **No human subjects and no human research contributors participate in this study.** Adjudication is performed by a frozen multi-model panel (§4.1), not by people; the only human involvement is the sole author's, and it is confined to mechanically-triggered tie-breaks under the rule in §4.1. The agents' user is the author himself (own production system); no third-party user data enters the benchmark un-hashed. Low-stakes restriction + mechanical safety abort (§3) bound operational harm. IRB: with no human subjects and no third-party data, independent-researcher exemption applies; the filed statement is **Appendix C**.

## 3. Sampling Plan

**Existing data.** Registration precedes all treatment-arm traffic. Historical logs are used only for (a) operational definitions, (b) the **pre-registered pilot** below, (c) the separate observational benchmark.

**Pre-registered pilot (F5 fix).** Before the pilot runs, we lock: the pilot's own metric definitions, the executable sizing script (committed, seeded), and the **deterministic function** `N_epochs = f(r̂, p̂0, ICC, MDE)`. The pilot is replay-only (no live arms). After the pilot, `f` is evaluated once and its output locked — no re-runs, no post-hoc MDE shopping.

#### Pilot metric definitions — LOCKED 2026-07-29

Named in v0.3, operationalised here. Each is stated so that two people writing the replay independently would produce the same number.

**Opportunity.** An executed action `a`, in a session starting after the epoch's 2 h washout, for which the serving snapshot at session start contained ≥ 1 *failure episode* `a_past` with `sig(a_past) = sig(a)` at **`primary`** granularity, written ≥ 1 epoch length before the epoch start. "Failure episode" is severity ≥ **τ = S1** by panel median (§4.1). Opportunity is a property of condition (i) alone and **does not depend on how `a` turned out** — that is what keeps `p̂0` a conditional rate rather than a tautology.

**`r̂` = opportunities ÷ analysed session-hours**, pooled over pilot epochs. The denominator is post-washout exposure, the same quantity the sizing script calls `hours_per_epoch`.

**`p̂0` = repeats ÷ opportunities**, where a *repeat* is an opportunity whose own outcome is adjudicated failure (condition (ii), the **binary** verdict — severity governs (i) only). Computed over control-arm epochs; in the replay-only pilot, **every epoch is control by construction**, since no treatment has been applied. This is stated because it is the reason a replay can estimate `p̂0` at all.

**`ICC` = intra-epoch correlation of the outcome**, estimated by **one-way random-effects ANOVA with the epoch as grouping factor and the *session* as the unit of observation** — each session contributes one repeat-density (its repeat count ÷ its span in hours): `ICC = (MS_between − MS_within) / (MS_between + (m̄ − 1)·MS_within)`, with **`m̄` the mean number of sessions per epoch**. Negative estimates are **truncated to 0**, the conservative direction: `DE = 1 + (m̄ − 1)·ICC ≥ 1` never deflates the required sample. Epochs carrying fewer than 2 sessions contribute no within-variance and are excluded from the ICC, reported separately rather than dropped silently.

⚠️ **`m̄` counts sessions, not session-hours — corrected 2026-07-30 after the harness exposed it.** An earlier version of this definition said "mean session-hours per epoch", which conflicts with the design effect it feeds: `DE = 1 + (m̄ − 1)·ICC` needs `m̄` to be the number of *observations* per cluster, and the observations are sessions. On the current corpus the two differ by an order of magnitude (**70.4** sessions/epoch against **6.06** session-hours/epoch), so the error would have inflated or deflated `N_epochs` substantially. `sizing.py` keeps them as separate inputs precisely because they are different quantities — its own worked example passes 12.0 and 8.0.

**⚠️ Snapshot composition is reconstructed by timestamp, not read from disk.** Condition (i) asks what the snapshot *contained*, but `pruneEpochs(keep=3)` retains only the three most recent snapshot databases — the historical ones are gone by design, with only their manifests kept. The replay therefore reconstructs membership as *"chunk existed and was written before the epoch boundary"*, using `created_at`. This is an **approximation, and it is declared rather than hidden**: it can diverge from the physical snapshot wherever a chunk was deleted or rewritten between its creation and the boundary. The measured corpus divergence per 24 h epoch is **0.144%** (T7), which bounds the error but does not eliminate it. **Sensitivity:** the three retained snapshots are replayed both ways — reconstructed and read from disk — and the two `r̂` values reported side by side. If they diverge by more than the T7 bound, the approximation is reported as a limitation on `N_epochs` rather than absorbed silently.

#### `ICC` under a stratified adjudication sample — LOCKED 2026-07-30, and the lock is mostly an admission

Piece 3 adjudicated a **stratified** sample (census of the `is_error` stratum + a uniform draw of 800 from the complement, `PILOT-PROJECTION.md` §4), which raises a question the definition above does not answer: should the per-session repeat densities that feed the ANOVA be **Horvitz-Thompson weighted**? Weighting corrects the stratum mixture but injects variance that is an artifact of the design; not weighting leaves the mixture distorted, because the `is_error` stratum is 9% of the corpus and 34% of the adjudicated sample. Measured on 11 contributing epochs:

| variant | ICC | `DE` at `m̄` = 70.4 | **95% bootstrap CI on `DE`** |
|---|---|---|---|
| HT-weighted, full design | 0.0806 | 6.60 | **[1.00, 14.66]** |
| unweighted, full design | 0.1363 | 10.47 | **[1.00, 18.44]** |
| censused stratum only | 0.0447 | 4.10 | **[1.00, 7.77]** |

**All three intervals contain zero, and each point estimate lies inside the others' intervals.** The estimator choice is inside the sampling noise — the question as posed is not the binding one. Two reasons, and both are structural rather than fixable by computation:

1. **Eleven clusters cannot estimate an ICC.** ICC precision requires on the order of 30–50 clusters. The analytic standard error for these data is 0.025, matching the bootstrap.
2. **`m̄` = 70.4 amplifies whatever error remains.** In `DE = 1 + (m̄ − 1)·ICC`, a ±0.025 error in the ICC is a ±1.7 error in `DE`. Projecting the analytic SE forward: 30 epochs give an ICC CI of roughly [0.016, 0.074] and 50 epochs [0.023, 0.067] — better, but **`DE` stays uncertain by about a factor of two even at 50 epochs.** ⚠️ **These two intervals are SUPERSEDED and are kept only as the projection that was made at 11 clusters.** They were extrapolated from an 11-epoch ICC of ≈0,045; the 30-epoch corpus was later measured and the official interval is **[0,0570 ; 0,1814] around 0,0985** (`SIZING-2026-08-14-v2.md`, Searle, confirmed by cluster bootstrap) — roughly twice as high and twice as wide as this projection anticipated. Do not read the three intervals as one ICC story: two are forecasts made before the measurement, one is the measurement. This is irreducible under this design, not a matter of waiting long enough.

Four decisions, locked:

- **(a) Estimator: the censused stratum, unweighted.** On principle, not on the number it yields — it is the only variant free of weight-induced variance, and it carries **229 of ~270 repeats (85%)**, so the clustering of the repeat process is substantially its clustering. The HT-weighted and fully-unweighted variants are reported alongside, never as the primary.
- **(b) Size on the upper 95% confidence limit of the ICC, not the point estimate.** Sizing error is asymmetric: under-sizing invalidates a completed study, over-sizing costs calendar. Standard trial-design practice, and here it is the difference between `DE` = 4.10 and 7.77 — not a refinement.
- **(c) Accumulate epochs before evaluating `f`.** Epochs arrive at one per day at no cost. Running the single permitted evaluation of `f` on an ICC the data cannot support would spend the exactly-once discipline on noise. This supersedes the earlier "not before 2026-08-09" gate, which was set by the abort baseline and is now the *earlier* of the two constraints.
- **(d) Report the power curve across the ICC confidence interval,** not only at the point estimate. §3 already commits to publishing the curve rather than a single number; under an ICC this uncertain, the curve stops being a formality and becomes the honest result.

#### Live-study adjudication volume and panel — LOCKED 2026-07-30: **census, API-only panel**

The gap the ICC analysis exposed: this registration fixed the *calibration* panel but never fixed the **adjudication volume of the live study**. ⚠️ **The arithmetic below uses the sizing current on 2026-07-30 (`K` ≈ 48 per arm, 96 epochs). `N_epochs` was locked at 174 on 2026-08-15 — 87 per arm — so every volume figure in this subsection is an UNDERSTATEMENT by ~1.8×.** The conclusion it reaches (census, API-only panel; subsampling dominated) is unaffected and gets *stronger* with more epochs, which is why the numbers were not silently rewritten: the reasoning is auditable against the sizing that produced it. At `K` ≈ 48 per arm the study spans 96 epochs × ~396 episodes ≈ **38,000 episodes**. The Moonshot panelist is reached through a CLI whose quota admits ~100 calls per window, so a five-panelist census is ~380 quota windows — not feasible.

**Subsampling is dominated on principle, not on preference.** Expected observed events are `E_a = K·T·λ_0`; adjudicating a fraction `f` multiplies the epochs required by `1/f`, so the **absolute number of adjudicated episodes is invariant to `f`**. Subsampling buys no adjudication volume at all — it converts a throughput problem into a calendar problem, on a study whose calendar is already ~130 days. It also adds sampling variance that `DE` would then have to carry.

**Therefore the panel is reduced instead, and the reduction was measured before being adopted — on the existing 1,500 calibration verdicts, at zero marginal cost.** Restricting to the three API-reached families (`glm-5.2`, `grok-4.5`, `gemini-2.5-pro`) and re-running the same locked coefficient rule on the same 300-episode calibration set:

| panel | Fleiss' κ | Krippendorff ordinal α | `Pa` | prevalence | ≥3 verdicts |
|---|---|---|---|---|---|
| five families (reference) | 0.8815 | 0.8557 | 0.9551 | 0.254 | 295/300 |
| **three API families** | **0.8747** | **0.8380** | 0.9512 | 0.265 | 287/300 |

Both coefficients clear the **0.75** floor with no caveat, the loss is **0.7 pp on κ** and 1.8 pp on α, and prevalence stays inside `[0.20, 0.80]` so the mechanical rule selects the *same* coefficient — the two rows are directly comparable rather than merely adjacent.

**Declared divergence, with its direction.** Majority verdicts differ on **4 of 287 comparable episodes (1.39%)**, and all four move the same way: the pattern is `[S0,S0,S0,S2,S2]`, where the CLI-reached panelists sit at S0 and removing them turns a 2-of-5 minority into a 2-of-3 majority. The reduced panel therefore finds *slightly more* failures, concentrated in genuinely split borderline episodes. This is reported as a systematic, directional, measured effect — it is what the leave-one-family-out analysis exists to expose, and it is not argued away.

**Two pre-existing defects this closes at no cost.** (i) §4.1 already conceded that the two CLI panelists are **not reproducible by version, only by recorded output**; an API-only panel is reproducible by model identifier, so the live study's instrument becomes fully re-instantiable. (ii) **Parity dies at the source** — three is odd and has no quota, so the operational lock above ("finalize only after every panelist returns") becomes trivially satisfiable instead of requiring ~10 quota windows per batch.

**What gets worse, stated plainly.** With exactly three panelists a **single abstention** drops an episode below the 3-verdict floor: measured, 8 of 300 (2.67%) on the calibration set, inside the 10% ceiling but fragile — one provider outage or a rise in abstention rate would breach it. Mitigation, not adopted here because it needs a credential that does not exist yet: seat a fourth API family.

**Consequence for the pilot.** The pilot exists to size a study whose measuring instrument is now the three-family panel, so the pilot's `r̂`/`p̂0`/`ICC` are computed with **that same panel**, not with the five-family panel — otherwise the sizing inputs and the study's own measurements would come from different instruments. The five-family verdicts remain the reference for reliability and for the leave-one-family-out analysis. The calibration set and `τ = S1` are unaffected: both were established on five families and stay so.

**The calibration panel does not change.** Five families adjudicated the calibration set, that is what τ and the reliability coefficients rest on, and this lock changes only the panel that adjudicates the *live study*.

**Exactly-once discipline.** These definitions and `sizing.py` are frozen now, before any of `r̂`, `p̂0` or `ICC` has been computed on real data. The pilot produces those three numbers and nothing else; `f` consumes them once.

**Treatment dose — a design ceiling, measured (P2S1 T6, 2026-07-26).** Power is usually discussed as if the treatment contrast were whatever the mechanism happens to deliver. Here it is **bounded by the brief's architecture**, and the bound was measured before locking `N`.

New content written during epoch *k* can reach a brief only two ways: through the coverage slots (`freshSlots = 2` of *n*, D3 default), or by displacing a primary slot on salience alone. The second is hard by construction — salience v2 weights `access` at 0.20 and newly-written chunks start at `access_count = 0`, so they lose to established chunks on that component regardless of pain or importance.

Positive control: a synthetic chunk inserted into the live store after a boundary at `pain = 1.0`, `importance = 1.0` — the ceiling of both dimensions — entered **1 of 10** briefs and was then crowded out, because being served made it no longer never-served. This corroborates the independently-measured T7 result (0 of 7,235 served slots diverged between physical and logical snapshots over a real 24 h epoch) and supplies the mechanism for it: the divergence is small not because the corpus is static, but because the brief admits new content through a fixed, small budget.

**Consequence, declared before lock:** the achievable effect on H1 is capped by that budget. If the pilot's `f` returns an `N` powered for a 20% relative effect but the dose cannot plausibly move H1 by 20%, the correct response is the "powered only for effects ≥ X%" declaration below — not a larger `N`. Continuous shadow collection (`NOX_EPOCH_SNAPSHOT=shadow`, serving unchanged) is accumulating divergence-versus-snapshot-age observations to bound this further; it is reported whatever it shows.

> ⚠️ **The ceiling argument cuts both ways, and the cut against us is not answered — declared 2026-08-15 after adversarial review (Kimi).** The paragraph above uses the dose ceiling to *justify* raising the declared MDE instead of raising `N`. That inference is only half-valid. It establishes that a large effect is unlikely; it does **not** establish that the achievable effect is ≥30%, which is what the locked `N` is powered for. **We have no evidence that the mechanism can move H1 by 30%.** If it cannot, the study is powered for an effect the design itself precludes, and the "powered only for effects ≥ 30%" declaration becomes a formality rather than a bound.
> 
> This is stated rather than repaired because repairing it requires a dose–response measurement that does not exist and cannot be obtained without running the intervention. What follows from it, pre-committed here:
> 
> 1. **A null on H1 is reported as jointly ambiguous.** It will be written as *"either no effect ≥30%, or a dose ceiling below 30% — this design cannot separate them"*, never as evidence that memory composition does not change behaviour.
> 2. **The dose-arm contrast (`w ∈ {0.5, 1.0, 2.0}`) is the only internal handle on this.** If H1 is null while showing no gradient across `w`, a ceiling is the more parsimonious reading; a gradient without significance points at power. This is a reading rule, declared before data, not a test.
> 3. **The shadow dose–age curve is reported alongside the primary result regardless of outcome**, because it is the only pre-treatment evidence about how much of the brief the treatment can actually reach.
>
> ---
>
> #### ⚠️ MEASURED 2026-08-15 — the paragraph above was written on a false premise, and is superseded in part
>
> It claimed the dose question *"cannot be obtained without running the intervention"*. That is wrong, and the registration already contained the method: §9-4 measured displacement reach on the live candidate pool on 2026-07-26. What it did **not** do is measure it at the doses that will actually run. The 2026-07-26 note covered `W_OUTCOME ∈ {0.10, 0.15, 0.20}`; the 2026-07-29 lock re-expressed the dose as `w × Δ_cut` with `Δ_cut = 0.043`, i.e. **`W_OUTCOME ∈ {0.0215, 0.043, 0.086}` — every locked dose below the lowest value ever measured.** The famous sentence *"0.15 is authority to rewrite the brief"* therefore describes **no dose this study will administer**.
>
> Measured now by `dose_reach.mjs` (read-only, same 500-row candidate pool and the real `calculateSalience`; full output in `DOSE-REACH-2026-08-15.json`). It reproduces the historical figures within corpus drift — 0.15 at severity 1.0 gives 326 chunks in reach today against the 303 reported in July — which is what licenses reading the new rows.
>
> **The severity that matters is not the ceiling.** Over the 3 812 unique (episode, panelist) `failure` verdicts of the frozen pilot corpus: **S1 69,73% · S2 29,62% · S3 0,58% · S4 0,08%** — median **S1**, mean **0,3275**. The severity = 1.0 ceiling used throughout §9-4 is reached by **3 verdicts in 3 812**.
>
> | dose | boost at empirical median (S1) | chunks reaching the cut | of 10 incumbents, displaceable |
> |---|---|---|---|
> | `w = 0.5` | 0,0054 | 3 | **4** |
> | `w = 1.0` | 0,0107 | 5 | **5** |
> | `w = 2.0` | 0,0215 | 12 | **7** |
>
> **The mechanism is alive at the locked doses, and it is a nudge rather than a rewrite** — which is what §2 said it wanted and had never checked. At the modal severity the lowest dose puts 4 of 10 slots in play and the highest 7; none of the three reaches the total-rewrite regime that 0.15 produces. The `w` arm is therefore a real gradient and not three labels for the same brief.
>
> **What this does and does not settle.** It settles that the treatment can change brief *composition* at the doses locked. It does **not** settle that changed composition changes behaviour by 30% — that remains unmeasurable before the intervention, and the three pre-commitments above stand unchanged. What it removes is the stronger worry: the study is not powered for an effect the mechanism cannot produce at all.
>
> **Δ_cut drift, declared:** the top-10 spread measured today is **0,0349** against the **0,043** frozen at lock — −0,0081, about 19% narrower. `Δ_cut` is frozen pre-treatment by design (§2) and is **not** updated; the drift is recorded because it means the locked doses are slightly *larger* relative to today's spread than they were at lock, which moves the effect in the direction of more displacement, not less.
>
> ⛔ **This measurement also exposed a gap that no `[TO LOCK]` list contains — see the note that follows §9-4.**

**Sample size & power (G1 fix).** MDE target: **20% relative (LOCKED 2026-07-29)** change in H1 (not 40% — implausibly large for a brief-composition nudge). At lock we commit a **power curve** (power vs. true relative effect at the locked N), not a single point. If the locked N yields <80% power at the 20% MDE, we either extend the pre-committed window **before** lock or lock with an explicit "powered only for effects ≥ X%" declaration in the abstract of the registration.

> #### The escape clause above is hereby exercised — 2026-08-15, before any outcome data exists
>
> **`N_epochs` is locked at 174 randomized epochs, and the registration will declare "powered only for effects ≥ 30% relative".**
>
> ⚠️ **Corrected the same day, before any randomized epoch.** The first version of this lock read *154 epochs at 25%* — the **point estimate** of the ICC, and off by two even there (`sizing.py` returns **152**, which is what `SIZING-2026-08-14-v2.md` §3 has said all along). Lock **(b) of 2026-07-30** requires sizing on the **upper 95% confidence limit** ("not the point estimate", "not a refinement"), which at 25% is 256 epochs. Adversarial review (Kimi) caught the silent violation. The correction chooses the MDE, not the standard: **30% on the upper limit = 174**, which honours lock (b) *and* costs less calendar than 256. See the block at the head of this document.
>
> The 20% MDE target is **not** amended and remains on the record as what was wanted. What this clause does is exactly what it was written for: report honestly that the locked N does not reach 80% power at 20%, and say so in the abstract rather than let the reader assume otherwise. Sizing at 20% would require **410 epochs at the ICC's upper confidence bound** (242 at the point estimate) — 13.5 months of continuous fleet operation. The full grid, all on the same inputs, with the column lock (b) mandates in bold:
>
> | MDE relativo | no ponto | **no limite superior (0,1814)** |
> |---|---|---|
> | 20% (alvo travado em 29/07) | 242 | 410 |
> | 25% | 152 | 256 |
> | **30%** | 102 | **174 ← LOCKED** |
> | 35% | 74 | 124 |
>
> **Inputs, all fixed before this lock and none of them outcome data from the study** (`SIZING-2026-08-14-v2.md`, replay over 30 epochs of historical corpus, no live arms):
>
> | | |
> |---|---|
> | `r̂` | 28,648576 |
> | `p̂0` | 0,116457 |
> | ICC | 0,098459, IC 95% **[0,0570 ; 0,1814]** (Searle; bootstrap de cluster confirma) |
> | `hours_per_epoch` | 5,1867 (horas-sessão por epoch) |
| `session_hours_per_epoch` | **50,4667 — e este campo contém SESSÕES, não horas** |
> | design effect | 5,87 |

> ⚠️ **O nome `session_hours_per_epoch` mente, e o valor está certo.** O campo carrega a **contagem de sessões** por epoch, que é o `m̄` que o design effect exige (`DE = 1 + (m̄−1)·ICC`); `sizing.py` o consome como `m_bar` e `pilot_replay.py` o computa como `sum(sessões)/epochs`. Confere: `1 + (50,4667−1)×0,098459 = 5,87`. O §3 já registra a armadilha — *"`m̄` counts sessions, not session-hours — corrected 2026-07-30 after the harness exposed it"* — mas a correção foi feita no **valor** e o **nome do campo nunca mudou**. Renomeá-lo agora alteraria a saída JSON de um script cujos resultados já estão citados em documentos datados; fica declarado em vez de renomeado. **Quem reimplementar deve alimentar `sizing.py` com sessões por epoch, não com horas.**
>
> **Epoch length is NOT changed.** It stays at the locked 24 h. Shortening to 8 h would reach the same MDE in far fewer calendar days — a real saving — but it would be an amendment to a locked value, and it would lean on a 2 h washout whose sufficiency has been verified only *without* treatment (`WASHOUT-SENSITIVITY-2026-08-14.md`: the natural boundary effect is confined to <2 h, which removes an objection but does not establish carry-over behaviour under an active arm). Buying calendar with an unverified premise is the wrong trade for a study whose whole contribution is methodological.
>
> **What this costs, stated plainly:** a true effect of 20% — the size originally judged plausible for a brief-composition nudge — will not be reliably detected, and neither will one of 25%. If the study returns null, that null is evidence against effects ≥30%, and is *not* evidence against effects in the 15–30% band. The abstract must say this, not bury it in a limitations section. **This is the widest gap between what was wanted and what will be measured anywhere in this registration, and it is stated here rather than discovered by a reader.**
>
> **Why this is not MDE shopping.** The §3 rule is "after the pilot, `f` is evaluated once and its output locked — no re-runs, no post-hoc MDE shopping". `f` was evaluated on the pilot corpus, which contains **no arm assignment and no study outcome**; the arms have not run. The prohibition targets choosing an MDE after seeing an effect, and there is no effect to have seen. The decision, its inputs, and its cost are recorded here **before** the first randomized epoch.
>
> The same test applies to the 25%→30% move made on the day of the lock, and it passes for the same reason — **but the honest framing is not "it passes", it is "there is nothing yet against which it could fail".** The move was made with the full grid above in view, to satisfy a standard (lock (b)) that was already on the record and was being violated. What makes it auditable is not the argument: it is that `r̂`, `p̂0` and the ICC were fixed and published in `SIZING-2026-08-14-v2.md` **before** the MDE was chosen, so anyone can recompute every cell of that table and confirm 174 is the entry it claims to be.

**Stopping rule (F3 fix).** Fixed horizon defined **only in pre-treatment units**: data collection ends at **174 randomized epochs (LOCKED 2026-08-15)** or the pre-committed calendar end date **[TO LOCK — 174 epochs at 24 h is ~5,7 months of fleet operation; the calendar date must be set from the first randomized epoch, which has not yet occurred]**, whichever comes first. Opportunity counts play **no role** in stopping. No interim analyses; no optional stopping.
**Safety abort — mechanical, no monitor (§0b).** Discretion is removed rather than delegated. A script in the frozen commit evaluates the following **arm-blind** rule at every epoch boundary, over the incident stream only (it never reads arm labels):

> **Halt the study** if either (a) ≥1 incident adjudicated at level **S4** (§4.1 rubric — data loss, production broken, or reversal needing intervention outside the agent's scope) occurs in an analyzed epoch, **or** (b) the count of incidents at level **≥ S3** within a trailing window of **3 epochs (LOCKED)** exceeds **3× (LOCKED)** the per-epoch baseline rate computed over **the full action history available in the frozen snapshot, with a hard minimum of 14 days (LOCKED 2026-07-29, replacing "90 days")**.

**Why the baseline window changed.** The 90-day window was unsatisfiable and would have silently disarmed clause (b). Measured 2026-07-29: the action archive begins **2026-07-18** (11 days), its upstream source `/root/.claude/projects` retains only from **2026-07-21**, and `brief_id` — which identifies the served brief — is complete only from **2026-07-26**. There is no 90-day history and there will not be one before late October. Requiring it would either postpone the pilot by three months or, worse, leave a rule in the document that no data could ever satisfy.

The 14-day minimum is a gate, not an estimate: **the pilot does not start until 14 days of complete logging exist**, i.e. no earlier than **2026-08-09**. Since the measured baseline of incidents at median ≥ S3 is **zero** (§4.1), clause (b) behaves identically under any window length — what a short window costs is confidence that zero is the true normal, and that cost is declared rather than hidden.

**Scale note (2026-07-26):** clauses (a) and (b) previously read `1.0` and `≥ 0.8` on an unanchored decimal scale, which made clause (a) require three of five panelists to pin a ceiling with no shared referent — plausibly untriggerable. They now read against the anchored ordinal rubric of §4.1, where each level carries an operational test a panel can actually agree on.

**Positive control — the trigger is verified live, not asserted (2026-07-29).** The claim that the panel "can actually reach" S4 was, until now, an assertion. In the 300-episode calibration set it was never observed: **S4 appeared zero times in 1,289 substantive verdicts**, and S3 four times, all from a single panelist. A null of that shape is indistinguishable from a disarmed trigger, so it was tested directly rather than interpreted.

Six synthetic episodes were adjudicated by the frozen panel under the same prompt hash: four unambiguous catastrophes (recursive delete of the production DB *and* its backups; `DROP TABLE` on the live store with the newest backup 45 days stale; `push --force` destroying 211 remote commits; `TRUNCATE` on a production payments table with no PITR) and two benign paired controls (a path typo that mutated nothing; a network timeout whose retry succeeded).

| | median verdict |
|---|---|
| 4 catastrophes | **S4 in 4 of 4** |
| 2 benign controls | S1 in 2 of 2 — **zero false positives** |

**All five frozen panelists reached S4** (`google` 4, `xai` 4, `zhipu` 4, `openai` 3, `moonshot` 4).

> **How `moonshot` came to be missing, and how it was closed — 2026-08-15.** The original run on 2026-07-29 excluded it with an explicit operator flag (`--only zhipu,xai,google,openai`), because at that moment the Kimi subscription was returning `403 usage limit` partway through the calibration set. That quota returned the same night — the calibration run finished 300/300 hours later — and **nobody went back to the positive control.** For two and a half weeks the artefact that proves the S4 trigger is alive rested on four of the five frozen panelists, and an earlier version of this paragraph attributed the gap to a quota window closing mid-run, which is not what happened: it never ran.
> 
> Closed by execution rather than by explanation: `moonshot` was run against the same six synthetic episodes under the same locked prompt (`prompt_sha256 = 5b22f02c…`), 6 of 6 returned, 0 quota. It rates **S4 on all four positive controls and S1 on both benign controls** — agreeing with the panel and, on the positive controls, more consistently than `openai` (3 of 4).
> 
> **Declared, because it changes nothing about the number but changes what the number is worth:** this completion was **not blind**. The other four verdicts were already known when it was run. It is reported because the trigger evidence is stronger with five than with four, and because a result obtained unblinded and declared is worth more than a gap explained away. Verdicts: `~/.paper2-verdicts/positive-control-moonshot-2026-08-15.jsonl`. One limitation carries over: the CLI adapter returns no served-model field, so `model_served` is null for these six — the same reproducibility gap §4.1 already concedes for CLI-hosted panelists. **Clause (a) fires.** The zero in the production corpus is therefore *informative* — that corpus contains no catastrophes — and not evidence of a dead trigger. Lowering the threshold to a level the normal corpus does reach (S2 covers 18.7% of episodes) would have converted a calibrated alarm into one that fires during ordinary operation, which is how an alarm becomes decoration. The control corpus is committed as `positive-control.jsonl` (SHA-256 `b8610f7c…`) and is re-runnable; it is **synthetic and never enters the action corpus**.

**Clause (b) with a zero baseline — stated plainly.** The measured per-epoch baseline of incidents at median ≥ S3 is **zero** (0 of 295 adjudicated episodes, complete panel). With a baseline of zero, `3× baseline` is zero and the multiplier does no work: clause (b) reduces to **"≥1 incident at median ≥ S3 within the trailing window halts the study."** That is the intended conservative behaviour, but the multiplier's wording implies a calibration it does not perform at this baseline, so it is recorded here rather than left for a reader to discover.

**"Adjudicated at level X" means the panel median**, not any single panelist — fixed here because the two can diverge: in control episode PC01 one panelist returned S0 while three returned S4. The median is what absorbs a lone outlier, which is the reason the panel is odd-sized.

The rule halts the **whole study**, never one arm — so it is **symmetric by construction** and cannot be triggered selectively against the arm the author would prefer to lose. Baseline rate, window, and multiplier are frozen at lock; the trigger evaluation is logged per epoch (including non-triggers) so the entire decision series is auditable after the fact. If triggered, the halt is reported as informative censoring with the pre-committed sensitivity analysis (with/without the final partial epoch). Human judgment enters only *after* a halt, to decide whether to publish — never to decide whether to continue.

## 4. Variables

### 4.1 Primary outcome (F2 fix — unconditional)

**Repeated failure:** an executed action `a` in an analyzed session such that (i) the serving snapshot contained, at session start, ≥1 *failure episode* with `sig(a_past) = sig(a)` written **≥ 1 epoch length before the epoch (LOCKED 2026-07-29; currently 24 h)**, and (ii) the new outcome is adjudicated failure. *Expressed as a multiple of the epoch rather than as an absolute 24 h so the two cannot drift apart — if the epoch is ever re-locked, this moves with it by construction.* (Executing with a *successful* outcome is not a repeated failure.)

> **Disambiguation of (ii) — resolved 2026-07-26.** §4.1 defines two distinct panel outputs: a **binary verdict** by simple majority and a **severity level** by median. The v0.2 text left it open which of the two condition (ii) refers to, and the choice is not cosmetic: if (ii) were `severity ≥ τ`, then τ would move the numerator *and* the eligibility denominator together and the primary metric would be non-monotonic in τ — a sensitivity band scanning τ would then be scanning two effects at once and could not be interpreted.
>
> **Locked:** condition (ii) is the **binary verdict**. Severity governs condition (i) only — which past episodes count as *failure episodes* eligible to seed a repeat. So τ moves the opportunity side alone, the sensitivity band has a single interpretation, and the metric is monotone in τ by construction.
**Primary metric:** repeated failures **per analyzed session-hour** (unconditional density). Session-hours are pre-treatment-defined exposure units.
**Signature `sig()`:** command-class × target-class. **Taxonomy derived from the measured action distribution and implemented in `extract_episodes.py` (2026-07-26)**; the frozen commit is **`c0abe143df1ab6452cf83556b2bc442ec87319a0`, file SHA-256 `e860357bd9f1fc0690ec8a817b7f6d23ac0c237882152d3a8714f7c0af7748b2` — LOCKED 2026-07-29** (both recorded in `CORPUS-FREEZE.md`, together with the corpus snapshot the taxonomy was derived over).

The classes were **derived, not invented** — reading them off 4,560 real executed actions rather than introspecting about what agents might do. Three granularities are defined *before* any outcome is seen, because §5 pre-commits robustness "one level coarser and finer" and that check is meaningless if the levels are chosen afterwards:

| Level | Definition | Distinct signatures observed |
|---|---|---|
| **coarse** | tool-family × target-family — `{read, write, execute, delegate, search, mcp, other} × {file, vcs, process, state, external, none}` | **14** |
| **primary** | tool × target-class — the level §4.1 matches repeats on | **74** |
| **fine** | primary × command verb (e.g. `git:push` distinct from `git:log`) | **168** |

Target class is always the *class* of what the action touches, never the literal value: a path resolves to `file:source` / `file:doc` / `file:config` / `file:db` / `file:test` / `file:script`, a shell command to `git:mutation` / `git:read` / `fs:mutation` / `fs:read` / `build-run` / `service` / `db` / `network` / `scheduling`. Literals are unbounded and would make every action its own signature, which is the degenerate case where no repeat is ever detected.

**Corpus properties, measured on the frozen snapshot (2026-07-29T09:46:09Z):** **5,547 episodes** (`tool_use` paired with its `tool_result`), **514 carrying `is_error`** (9.3%), spanning **eight sources — seven named agents** (`atlas`, `boris`, `cipher`, `forge`, `gordon-gekko`, `lex`, `nox`) **plus the workspace root**. A ninth directory (`-tmp`, 1,615 files, 41.8% of the archive) contributes **zero** episodes: those sessions are memory-compression jobs with no executed action, verified by parse (`CORPUS-FREEZE.md`). Extraction is deterministic — the same archive yields the identical SHA-256 on re-run, verified — so the episode corpus is hashable and the pre-registration is checkable rather than merely asserted.

⚠️ **These counts are snapshot-relative, and the earlier ones were not wrong — they expired.** The v0.3 text recorded 4,560 episodes / 434 errors / 14-72-162 signatures on 2026-07-26. The archive grows ~330 episodes per day, so by the 2026-07-29 sampling it had moved to the figures above. A derived taxonomy over a live corpus has no stable cardinality; the counts are only meaningful against a named snapshot. The snapshot, its manifest, and the frozen `sig()` implementation are hashed in **`CORPUS-FREEZE.md`** — reproduction runs against that artifact, not against the live archive.

**Calibration sampling is stratified by primary signature and seeded**, refusing to run without an explicit seed (an unseeded sample is not pre-registrable). Stratification is not cosmetic: `Bash|shell:other` alone is ~27% of the corpus, so a naive random draw of 300 would be dominated by it and would never test the rubric against the tail. Verified: a 300-episode draw covers **all 72** primary signatures. The production seed is **derived from a public beacon round, not chosen** — but from a *distinct* round from the one in §2, and the distinction is forced by chronology rather than preference. The §2 round is defined at `T_seed_assign`, strictly **after** OSF registration; the severity cutoff this calibration produces is a `[TO LOCK]` item that must be filled **in** that registration. Calibration therefore precedes registration, which precedes `T_seed_assign` — so calibration cannot use the §2 seed. It uses `T_seed_calib`, declared and published before the corresponding round existed. Parameters, derivation rule, and third-party verification command: `CALIBRATION-SEED.md`.

**Redaction before adjudication.** Episodes go to an external LLM panel, so the extractor redacts API keys, tokens, JWTs, IPs and e-mail addresses before emission — verified on the full corpus (990 e-mails, 191 IPs, 10 keys, 1 JWT replaced; zero residual matches for the dangerous patterns). This is a net, not a guarantee, and is declared as such.
**Failure episode:** severity at or above the primary level of the rubric below — **LOCKED 2026-07-29: τ = S1** — adjudicated by the frozen panel (median, §3).

**Why S1, from the calibration set and not from taste.** The 300-episode calibration (seed `f61f4c46…`, §4.1) yields two candidate cuts and they are not equally sound:

| τ | failure episodes | raw agreement `Pa` | rater prevalence | **pre-registered coefficient** |
|---|---|---|---|---|
| **S1** | 71 / 295 (24.1%) | **0.952** | 25.5% → inside [0.20, 0.80] | **Fleiss' κ = 0.874** |
| S2 | 52 / 295 (17.6%) | 0.858 | 15.7% → outside | **Gwet's AC1 = 0.808** |

*(Complete panel, 1,500 verdicts, SHA-256 `b6eebe18…`. An interim reading at 1,429 verdicts — `moonshot` incomplete — gave 24.7% / 18.3% and κ = 0.873 / AC1 = 0.808. Filling the last 71 moved τ by 0.6 pp and the coefficients by ≤ 0.001, which is the robustness check the incompleteness would otherwise have demanded.)*

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

> ⚠️ **This subsection describes the FIVE-family panel, which is the CALIBRATION instrument. The LIVE study adjudicates with THREE API families** (`zhipu` / `xai` / `google`) — locked 2026-07-30 in §3, *after* measuring on the 1,500 calibration verdicts that the reduction costs κ 0,8815 → 0,8747. Wherever this subsection says "five", read it as the panel that produced κ, α and the rubric. Two properties are re-asserted for the live three-family panel and do not carry over silently: **odd size** (3 is odd; strict majority, exact tie → `not_failure`) and **leave-one-family-out**, which for the live panel is leave-one-of-three-out and is reported as a robustness check, not as an overlap remedy.

**Adjudication panel (replaces human adjudicators; §0b).** Episodes are judged by an **odd-sized panel of LLMs drawn from distinct training families** — **5 families, wired and smoke-tested 2026-07-26: Zhipu `glm-5.2` · xAI `grok-4.5` · Google `gemini-2.5-pro` · Moonshot `k3` (kimi-code 0.29.1) · OpenAI `gpt-5.6-sol` (codex-cli 0.145.0)**.

**Versions are recorded as observed at execution, not pinned — and the difference is declared (2026-07-29).** The two CLI-hosted panelists run through tools that self-update: `codex-cli` was measured at **0.144.5 on 2026-07-28** and **0.145.0 on 2026-07-29**, one day apart, with no action taken; `kimi` reads 0.29.1 on the execution host and 0.20.2 on the server. A "version pin" over software that upgrades itself is a promise the artifact cannot keep. **Consequence, stated plainly: the three API panelists (`glm-5.2`, `grok-4.5`, `gemini-2.5-pro`) are reproducible by model identifier; the two CLI panelists are not reproducible by version, only by the recorded output.** All 1,500 calibration verdicts are hashed (`b6eebe18…`), so what they returned is verifiable even where the tool that produced them is not re-instantiable.

**Anthropic is excluded by design, not by availability.** The agents under study run on `claude-cli`; seating Anthropic would be a family judging its own output. Excluding it costs nothing in provenance diversity — five distinct families remain, and the panel stays odd — and removes the conflict at the source rather than bounding it after the fact. Should Anthropic ever be seated, the leave-one-family-out analysis below is promoted from robustness check to primary result.

Access is mixed and that is recorded because it has a cost consequence: Zhipu, xAI and Google are reached through metered APIs (~1.1k tokens per adjudication); Moonshot and OpenAI have no metered key available and are reached through their CLIs, each of which spins an agent loop per call (measured: ~22k tokens of overhead on a trivial prompt). The panel is therefore roughly **an order of magnitude more expensive than an all-API panel** — ~14M tokens for a 300-episode calibration set rather than ~1.7M — chosen so that correlated annotator bias is mitigated by provenance diversity rather than by assumed impartiality. Protocol:

- **Frozen prompt.** One adjudication prompt, identical for every panelist, hashed and registered pre-hoc — **LOCKED 2026-07-29: `5b22f02c1a557417fe874b98cdf8a3ad6441cada74d69ace8e54f82b3438b03e`**, the SHA-256 of the prompt *body* as extracted and sent (the containing file hashes to `3767fdb5…`; the two are different objects and both are recorded in `CORPUS-FREEZE.md`). This hash governed all 1,685 adjudication calls executed to date. Model identifiers **LOCKED**: `glm-5.2` (Zhipu) · `grok-4.5` (xAI) · `gemini-2.5-pro` (Google) · `k3` (Moonshot) · `gpt-5.6-sol` (OpenAI).
- **Independence.** Each panelist judges every episode in isolation — no panelist sees another's verdict, and no chain-of-panel aggregation occurs before all verdicts are recorded.
- **Verdict.** Binary failure/not-failure by **simple majority**; severity by **median** of panelist severities (odd panel ⇒ no binary tie; median is well-defined and robust to a single outlier panelist).
- **Reliability.** Agreement is reported for **two targets, separately, because they are different measurements**: (α) the **binary verdict**, and (β) the **severity level**. The v0.2 text named "Fleiss' κ" without saying which — and Fleiss' κ is a *nominal* statistic, so applying it to the ordinal rubric above would score S1-vs-S4 and S3-vs-S4 as equally wrong. Locked coefficients: for (β), **Krippendorff's ordinal α**; for (α), a **mechanical prevalence rule** — if the positive class falls outside [0.20, 0.80] in the calibration set, report **Gwet's AC1**, otherwise **Fleiss' κ**. Both are always reported alongside raw agreement, and Fleiss' κ is reported in every case for comparability with the literature even when it is not the gate.
  - **Graduated floor, not a cliff.** ≥ **0.75 (LOCKED 2026-07-29)** → primary reported without a reliability caveat · **0.60–0.75** → primary reported **with** a mandatory caveat in the abstract and the attenuation bound · < **0.60** → inconclusive on reliability grounds. Rationale for graduating rather than gating: adjudication is arm-blind by construction (§2), so misclassification is non-differential and **attenuates toward the null**, and the permutation test's type-I error is exact regardless of agreement. A low coefficient therefore costs **power and effect magnitude, not validity** — a conservative error, and one that does not justify discarding a study already paid for. The 0.75 is retained as the top of the clean band; it is Fleiss' own "excellent" cut.
  - **Measured on the calibration set (2026-07-29), by the rule above — both clear the floor.**

    | target | prevalence | coefficient the rule selects | value | band |
    |---|---|---|---|---|
    | (α) binary verdict at τ = S1 | 25.5% → inside | **Fleiss' κ** | **0.874** | ≥ 0.75, no caveat |
    | (β) severity level, S0–S4 | — | **Krippendorff's ordinal α** | **0.852** | ≥ 0.75, no caveat |

> **On the three α figures in this document.** 0.852 (here) is the calibration headline over the five-family panel; **0.8557** in §3's reduction table is the same quantity recomputed inside the comparison harness, which retains four decimals and includes the 295/300 completed episodes explicitly; **0.8380** is the three-API-family value. They are not competing estimates of one number — the first two differ only in rounding and reporting precision, the third is a different panel.

    Reported alongside for comparability, and **not** the gate: raw agreement `Pa` = 0.952 (α); Fleiss' κ on the ordinal scale = 0.640. That last figure is exactly the artifact this paragraph anticipated — a nominal coefficient on an ordinal scale, penalising S1-vs-S2 as heavily as S0-vs-S4. It is printed to show the gap, not to be read as the reliability of the rubric.

    **Panel completeness: 1,500 of 1,500 calls returned.** `zhipu`, `xai`, `openai` and `moonshot` at 300/300; `google` at 298/300. Abstentions, which are recorded as missing per the tie-break rule below, are unevenly distributed and this is reported rather than pooled: `openai` 27, `moonshot` 14, `xai` 7, `zhipu` 6, `google` 2. After removing abstentions, **295 of 300 episodes** carry the ≥ 3 substantive verdicts the majority rule requires; the remaining 5 enter the unadjudicable category (§5) — **1.7%, against a pre-registered ceiling of 10%**.

  - **Declared residual.** The attenuation argument assumes non-differentiality. It fails if panel disagreement correlates with episode features that the treatment itself shifts — the arms differ in brief composition, hence possibly in the mix of actions attempted, hence possibly in the mix of episode types. This design does not exclude that path; it is reported as a limitation, not as a solved problem.
  - **Presentation order randomized.** Each panelist sees episodes and any enumerated options in an order derived per-episode from the beacon seed. Position bias in LLM judges is large and would otherwise manufacture agreement that looks like construct clarity.
- **Tie-break / abstention.** If a panelist errors or abstains, its verdict is recorded as missing and majority is computed over the remainder; if fewer than **3 (LOCKED 2026-07-29)** valid verdicts remain, the episode joins the unadjudicable category (§5, Missing data). Exercised on the calibration set: 5 of 300 episodes fell below the floor, all through abstention rather than error. The author intervenes **only** when the mechanical rule cannot resolve, and then on an arm-blind episode, with every such intervention logged and counted in the paper.
- **Even valid-verdict counts — LOCKED 2026-07-29, and the lock was forced by a broken premise.** The paragraph above justifies an odd panel on the grounds that it yields "no binary tie" and a well-defined median. That guarantee holds only while all five panelists return. **It did not hold.** On the piece-3 adjudication (1,140 episodes) the Moonshot quota cut off after 88 calls and **987 of 1,140 episodes carried exactly four substantive verdicts** — even parity became the rule, not the exception, and the rule for resolving it did not exist in this document. The harness was silently choosing one: `v[len(v)//2]` is the *upper* median, which at four verdicts accepts **2 of 4** — a tie resolved in favour of `failure` — where simple majority requires 3 of 4.

  Three things are locked, in order of how much each actually contributes.

  1. **Operational (the dominant fix).** An episode is finalized only after **every** panelist on the frozen allowlist has returned either a substantive verdict or an abstention. **Quota exhaustion is not abstention** — it is a *pending* call and must be retried in a later quota window. Measured on the two adjudications run to date: with all five panelists completing (calibration, 1,500/1,500) parity is **8.8%** and exact ties **0.3%** (1 of 295); with one panelist truncated by quota (piece 3) parity is **88.6%** and exact ties **1.2%**. Running the panel to completion therefore removes ~90% of the problem before any statistical rule is needed, and the distinction is now machine-checkable: the harness emits `status: "quota"` separately from `status: "missing"` (`run_panel.py`, 2026-07-29).
  2. **Rule for the residual: strict majority; an exact tie resolves to `not_failure`.** A tie is not a majority. With the operational lock this governs ~0.3% of episodes, and locking a rule is only safe at that prevalence. The direction of error is stated: strict majority *under*-counts failures, hence deflates `lambda_0`, hence **inflates `K`** — a longer study, never an underpowered one, which is the same trade §4.1 already accepts for a low reliability coefficient ("costs power and effect magnitude, not validity"). Rejected alternatives, on principle rather than on the number each produced: *tie ⇒ failure* is anti-conservative and unfaithful to "simple majority"; *tie ⇒ unadjudicable* is faithful but makes missingness conditional on **panel disagreement**, a post-randomization variable, which attacks the non-differentiality premise this section depends on; *drop-to-odd* restores the stated premise but its answer depends on **which** panelist is dropped — a rule whose output turns on its own tiebreaker seed is not a rule.
  3. **Mandatory disclosure.** The parity distribution and the exact-tie count are reported in the paper, and *tie ⇒ failure* is pre-registered as a **sensitivity analysis on the primary outcome** — not on `K`, which is chosen once. Without this, adopting either rule would conceal a real swing: on the piece-3 data the two readings gave `K = 64` and `K = 53`. Note the mechanism, because it generalizes: only **14** exact ties existed in 1,013 even-parity episodes (1.4%), but 11 of them fell in the stratum carrying a Horvitz-Thompson weight of **5.204**, so 1.4% of cases moved the study size by 20%. **In a weighted design an edge case must be judged by frequency × weight, never by frequency.**

> ### 🔴 SUPERSEDED 2026-07-29 — read the premise, not the remedy
>
> **The block below assumes Anthropic sits on the panel. It does not.** The 2026-07-29 lock excludes Anthropic *by design* (see the paragraph above: "seating Anthropic would be a family judging its own output"), which **dissolves the actor–judge overlap this block was written to manage** rather than mitigating it. Kept because the reasoning about actor-family variation remains the right frame, and because deleting a superseded safeguard hides that it once existed.
>
> **What survives:** leave-one-family-out is still run and still reported — over the five *non-Anthropic* families, as a panel-robustness check rather than as an overlap remedy. What does **not** survive: any reading in which a result "survives only with Anthropic in the panel", since Anthropic is never in it.
>
> ---
>
> **⚠️ Actor–judge family overlap — declared, and made testable (2026-07-26; premise revoked 2026-07-29).** The agents under study run primarily on `claude-cli`, i.e. on Anthropic models, and Anthropic sits on the adjudication panel. A family judging its own outputs is exactly the kind of conflict this design removes elsewhere by construction, and it cannot be removed here without either dropping a family (weakening provenance diversity) or dropping the family that actually produces most of the behaviour.
>
> What makes it tractable is that **the actor family varies**: the runtime falls back to non-Anthropic models on some turns (observed: `gpt-5.5` turns on the `nox` agent), so actor family is not constant across episodes. Pre-committed robustness, therefore:
> 1. **Leave-one-family-out adjudication** — the primary is recomputed five times, each dropping one panelist family, and all five are reported. A result that survives only with Anthropic in the panel is reported as not surviving.
> 2. **Family-match test** — verdicts are regressed on an indicator for *panelist family == actor family*. A non-null association is reported as a limitation on the verdict, not silently absorbed.
>
> Neither check needs the arm label, so both stay arm-blind. The residual — that Anthropic-family bias could move all five recomputations in the same direction because Anthropic produced most episodes — is **not** eliminated by this and is declared.

**Advantage over a human panel, stated plainly:** this adjudication is **fully reproducible** — a reader with the frozen prompt, the pinned model ids, and the public episode corpus can re-run it and compare against the published verdict hash (§2, Blinding). Human adjudication is not reproducible in this sense. **Declared limitation:** LLM panelists may share failure modes not eliminated by family diversity (e.g. common pretraining corpora), and a residual correlated bias cannot be excluded; the κ report and the coarser/finer `sig()` robustness checks are the available evidence against it.

### 4.2 Secondary outcomes

Task regret (excess time-to-resolution + token cost vs. best known resolution of the same signature, winsorized at **p95 — LOCKED 2026-08-15**); the H1a–c co-primary family (§1).

> #### Task regret — winsorization points, and an ambiguity in the original wording
>
> | component | winsorized at |
> |---|---|
> | excess time-to-resolution | **7,45 s** |
> | excess token cost | **65 206 tokens** |
>
> **Why two numbers and not one.** As written above, task regret is "excess time-to-resolution **+** token cost". Those are seconds and tokens; summing them requires a conversion rate the registration never declared. Inventing one now — with the distribution already measured — would be choosing an estimator with the data in view. The two components are therefore **winsorized separately and reported as a family**, in the same spirit as the Holm-corrected H1a–c. This resolves an ambiguity in the original phrasing rather than changing the outcome: no component is added or removed, and if a defensible seconds-per-token rate is ever declared, the summed version is recoverable from the two.
>
> **Reconciling §9 note (c) — LOCKED 2026-08-15.** That note asked for three things: test H2 on **raw** values; apply p95 to the **estimator only**, pooled and arm-blind; pre-commit the sensitivity. All three hold, and the wording above was ambiguous about the first. To be explicit: the **permutation test on H2 runs on raw, unwinsorized values** — its type-I error is exact under any tail, so winsorizing there would buy precision at the cost of the right tail where the hypothesis lives. Winsorization applies to the **effect estimator**, computed **pooled across both arms, once, arm-blind**; per-arm winsorization is prohibited, because it would mechanically erase between-arm tail differences and delete the effect with the instrument. The raw-value effect estimate is reported alongside the winsorized one in every case.
>
> **The defect was visible without any data, and was not caught for six weeks.** "Seconds + tokens" is dimensionally invalid on inspection; it survived v0.1 through v0.3 and an adversarial review round. Recorded because a registration that documents its own late catches is more trustworthy than one that presents each fix as if it had been foreseen.
>
> **Measured over the frozen action corpus, not the study.** 10 868 `tool_use`/`tool_result` pairs; 10 724 episodes carry regret; 0 discarded for missing timestamp and 0 for missing `usage`. "Best known resolution" is the **minimum among successful episodes** of the same signature — using the global minimum would let a fast, cheap failure define the floor, and a failure is not a resolution. Signatures with fewer than 5 successful episodes do not define a reliable floor and are excluded (47 of 106 signatures, but only 144 of 10 868 episodes — the excluded signatures are the rare tail).
>
> **The one free choice was tested.** That minimum-per-signature threshold is the only parameter here that was not forced by the definition. Varying it across {3, 5, 10, 20} moves the time p95 between 7,441 s and 7,588 s (2%) and the token p95 between 64 862 and 65 220 (0,5%). The locked values do not depend on it.
>
> **Token accounting, declared:** input + output + `cache_creation`, **excluding `cache_read`**. Cached reads bill at a fraction of the rate, and counting them at full price would inflate long sessions — precisely the ones that accumulate cache. The choice understates the cost of long sessions and is conservative for regret.
>
> Script: `task_regret.py`. It **imports** the signature functions from `extract_episodes.py` and never modifies it — that file is LOCKED at commit `c0abe143` with a registered SHA-256, and the taxonomy must stay byte-identical to the frozen corpus.

### 4.3 Covariates / recorded

Agent id (**defined by OS-level identity**: systemd unit / session namespace, M7), epoch id, predecessor-epoch arm, weekday, task-type class, brief composition (hashed chunk ids), per-brief retrieval metrics (H3).

## 5. Analysis Plan

**Primary inference (F4 fix).** Two components, reported separately:
1. **Sharp-null test:** epoch-level permutation test (re-randomize epoch→arm under the same balancing constraints, **10,000 (LOCKED 2026-07-29)** permutations) on the **trend-residualized** outcome (outcome regressed on study-day, residuals permuted). Declared scope: this tests the sharp null of *zero total effect (direct + carry-over)*; rejection alone does not attribute magnitude.
2. **Effect estimate + CI:** difference in H1 density with cluster (epoch) bootstrap CI. Magnitude claims come from here, never from the permutation p-value.

**Co-estimates (interference; pre-committed):** A→B-restricted estimate; lag-1-adjusted estimate; partial-identification bounds (§2). Concordance across the four is the claim's strength; divergence is reported as-is.

**Secondary estimator (sensitivity):** logistic/Poisson mixed model with arm fixed effect, **agent as fixed stratum** (no agent random effect — the fleet is an allowlist of ~7 named agents plus the workspace root, far too few clusters for a random effect; G7), epoch random effect.

**Multiple comparisons.** H1 at α=0.05 two-sided; H1a–c + H2 Holm-corrected within the secondary family. **The two task-regret components (time, tokens) enter that Holm family as two members, not one — LOCKED 2026-08-15.** Splitting a summed outcome into two makes the correction stricter, not looser, which is the direction that keeps the split from being a way to buy significance; treating them as a single member would require a pooling rule, and pooling is exactly what the missing conversion rate makes impossible (§4.2). H3 exploratory, effect sizes only, figures per pre-committed Appendix A specs.

**Exclusions (ex-ante, arm-blind; G3 fix).** All exclusion rules are deterministic, evaluable without arm labels, frozen at the pipeline commit, and applied by script before unblinding. **Arm-blindness is not attested by an auditor but is checkable by inspection (§0b):** the exclusion code takes the episode corpus as its only input — the arm-label artifact is not in scope for that module — so any reader can confirm by reading the frozen commit that no exclusion rule *could* have consulted an arm label. The set of excluded units is itself hashed and published before the join. Rules: washout windows; boundary-straddling sessions (flag + sensitivity); epochs overlapping `ops_audit`-logged manual memory interventions (**both arms equally, by timestamp**); epochs with `brief_log` coverage < **95% (LOCKED 2026-07-29)**, coverage computed arm-blind.

**The floor is satisfied, and it dates the earliest usable epoch.** Measured on the frozen epoch snapshots: `brief_id` — the field that identifies which brief was served — was absent for every row through 2026-07-24, appeared mid-day on 07-25 (16.9%), and has been at **100.0% on 07-26, 07-27, 07-28 and 07-29** (~7,300 rows/day). The 95% floor therefore sits comfortably below observed behaviour and exists to absorb transient logging failure, not to be a live constraint. **Consequence, pre-committed: epochs before 2026-07-26 are ineligible by construction** — not excluded on a statistical criterion, but because the instrument that measures coverage did not yet record it. This is the same date that gates the 14-day baseline minimum in §3, so both point at the same earliest pilot start.

**Coverage is post-randomization, and arm-blindness does not license conditioning on it (corrected 2026-07-26).** Every other exclusion above is defined on pre-treatment quantities. Coverage is not: treatment changes brief composition, which could plausibly change retrieval load and therefore logging failure. Conditioning on a post-treatment variable breaks randomization-based inference **even when the rule never reads the arm label** — arm-blindness protects against a different failure (rule-shopping), not this one. Two consequences, both pre-committed:

1. **Mandatory ITT co-estimate.** The primary is reported alongside an intention-to-treat estimate over **all post-washout epochs with no coverage exclusion whatsoever**. Agreement between the two is the strength of the claim; divergence is reported as-is and is not adjudicated in favour of either.
2. **The coverage floor defines an analysis set, not a validity gate.** Its role is precision, not identification. Excluded epochs are counted and reported, never silently dropped.

**Coverage–arm association: a test, not a fixed threshold (corrected 2026-07-26).** The v0.2 rule — *"if coverage loss correlates with arm at |r| > 0.2, the primary is declared compromised"* — is miscalibrated, and the miscalibration is computable without any data. Under the null of no association, the Fisher-z standard error is `1/√(K−3)` and `atanh(0.2) = 0.2027`, so the rule fires **by chance alone** at 29.2% for K = 30, 25.9% at K = 34, 18.4% at K = 46, 12.6% at K = 60, and 4.6% at K = 100. The §9.7 sizing function, evaluated at inputs of the order now measurable from the action corpus, returns **34–70 epochs** — precisely the range where a threshold intended as a safeguard misfires between roughly one run in four and one in ten.

It is replaced by an **equivalence test**, which matches the claim actually being made. The claim is *absence* of an arm–coverage association; a rejection test cannot deliver absence, and a fixed |r| cutoff converts sampling noise into a verdict. Pre-committed: **TOST at α = 0.05 against a pre-declared irrelevance band of |r| ≤ 0.15 (LOCKED 2026-07-29)**, evaluated only when **K ≥ 30 (LOCKED)** epochs are analyzed. Failing to establish equivalence is reported as *"arm–coverage independence not established at the pre-committed band"* — a stated limitation carried into the abstract — and **not** as an automatic "compromised" verdict, because the mandatory ITT co-estimate above already covers the case it was meant to guard. The realized correlation and its confidence interval are reported unconditionally, whichever way the test lands (M10).

**Missing data.** Unadjudicable outcomes → third category, reported, excluded from numerator; if >**10% (LOCKED 2026-07-29)** of executed matching actions are unadjudicable, the primary is reported inconclusive regardless of p-value.

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
| Underpowering (rare events) | Density metric, pilot-sized power curve, **N = 174 locked at MDE 30%, sized on the ICC upper confidence limit (0,1814) per lock (b), with the "powered only for effects ≥ X%" clause exercised (§3)**, re-scope-before-lock | **Effects < 30% relative undetectable — declared in the abstract, not in a limitations section.** The 20% target originally judged plausible for a brief-composition nudge is *not* reached: a null result is evidence against effects ≥30%, and not against the 15–30% band |
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

## 9. Open items blocking lock — **HISTORICAL SECTION, closed 2026-08-15**

> ⚠️ **Read this section as archaeology, not as a checklist.** It is the running log of what blocked the lock, kept intact because the order in which things were decided is itself part of the record. Every item below is closed except the two named in the status banner (calendar end date and `T_seed_assign`), both of which are open *by construction* — they require the registration to exist. Present-tense phrases inside it ("Still open", "Still blocked on item 0") describe the state **at the time each was written** and are struck or annotated where they are no longer true. The authoritative current state is the table at the end of this section.

1. ~~§0 route decision~~ ✅ **Route 2-lite (Toto, 2026-07-12).**
2. ~~Named external auditor + named independent data monitor~~ ✅ **CLOSED by decision, not by appointment (Toto, 2026-07-25): no humans in either role; independence is structural (§0b).** Replaced by: public beacon seed (§2), mechanical abort (§3), multi-family LLM panel (§4.1), ordering proof via pre-join verdict hash (§2), exclusions-as-code (§5).
3. Epoch length + washout (24h + 2h proposed) · ~~snapshot mechanism spec~~ ✅ **SPEC WRITTEN 2026-07-25** → `specs/2026-07-25-P2S1-serving-side-snapshot.md`. Design settled: physical `VACUUM INTO` snapshot per epoch freezing **the corpus only** (`chunks`, `chunks_fts`, `vec_chunks`, `vec_chunk_map`); `brief_log` stays on the live store because the D2 coverage sampler is stateful *within* an epoch (freezing it would degenerate the brief and change what the treatment arm measures). Sliding retention of 3 snapshots keeps disk cost constant, not linear in epochs. ✅ **LOCKED 2026-07-26 — measured, not estimated.** DB **1.6 GB**; `VACUUM INTO` **9.8 s** bare / **17.8 s** including manifest (SHA-256 streamed over the full file); free disk **270 GB of 387 GB**. Sliding retention of 3 ⇒ **~4.8 GB = 1.8% of free space**, against the ≥20% headroom the kill criterion demanded. **K1 PASSES with wide margin** — the causal phrasing in §1-H1 stands and the Route 1 degrade is not triggered.

Mechanism implemented and **in production**: per-epoch snapshot with auditable manifest (SHA-256, per-table counts, `user_version`, `integrity_check`), serving split (corpus from snapshot, `brief_log` from live — two connections, no `ATTACH`), atomic pointer swap via `rename()` over symlink, sliding retention that preserves manifests after pruning the `.db`, and `/api/health.servingSnapshot` reporting the epoch in use and its hash. Frozen-corpus invariant is enforced by test: content written after a boundary does not appear in that epoch's own snapshot.

✅ **Validation complete 2026-07-26 (T6, T7, T8).** All six acceptance criteria pass over 8 boundaries on the production host: briefs served from the snapshot were identical to the live-served briefs at the boundary (327/327); the write path was untouched (`ops_audit` 126 → 126); the D2 coverage rotation stayed alive within the epoch (210 distinct chunks across 386 briefs), which is the counter-proof that freezing the corpus does not freeze the sampler; the pointer swap served 300 concurrent requests with zero non-200; disk stayed at 3 snapshots across 8 boundaries with all 8 manifests retained; and `/api/health` reports the epoch and its hash. Copy cost: **1.5 GB in 14.0 s**, during which `/api/brief` latency rose from a ~58 ms baseline to **p50 87 ms, p95 240 ms, max 300 ms** — small, non-zero, and scheduled into the traffic valley.

**The identity result was verified against a positive control**, because 327/327 identical is exactly what a broken instrument comparing the live store to itself would report. Forcing a real divergence (§3, treatment dose) produced it, confirming the shadow arm reads the snapshot.

M2 (logical `created_at` filter) remains a **documented fallback with measured error**, not the design: 0.144% of corpus rows and 0 of 7,235 served slots per 24 h epoch (T7). Failure drills pass 5/5 — a corrupted snapshot does not flip the pointer, an absent snapshot degrades to the live store **with a stated reason and a RED health check**, and absent `vec0` degrades partially rather than totally (T8).

**Still open before the pilot:** ~~epoch length + washout remain [TO LOCK]~~ **✅ BOTH LOCKED 2026-07-29** — 24 h at 06:00 BRT (the value already in production) and a 2 h washout sized against the measured session-duration distribution (§2). ~~boundary rotation is not yet scheduled~~ **✅ SCHEDULED AND RUNNING since 2026-07-27** — `cron 0 6 * * *` invoking `nox-epoch-boundary.sh`, verified in the live crontab on 2026-07-29; first natural rotation produced epoch `e20260727T090002Z` (operational, not mechanism).
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
> Consequently items 4–8 are unblocked for calibration, and item 5's taxonomy is derivable today (the 71 signatures observed at that date were the first cut; on the frozen snapshot of 2026-07-29 the count is **74** primary — see the taxonomy table and `CORPUS-FREEZE.md` for why a derived taxonomy has no stable cardinality over a live corpus).
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
   > ⚠️ *(Quoted reviewer text below. The literal string `[TO LOCK: α]` that appears inside it is **HISTORICAL** — `α` was locked on 2026-07-29 as `w × Δ_cut`, `w ∈ {0.5, 1.0, 2.0}`. A grep for `[TO LOCK` will match it; it is not an open item.)*
   > **Recommendation:** parameterize `W_OUTCOME` **relative to the observed salience spread at the cut** rather than as a round absolute. E.g. `W_OUTCOME = α × (s_1 − s_N)`, which at the measured top-10 spread makes α = 1 mean "a maximum-severity episode moves from the cut to the top" — an interpretable unit that survives corpus drift, whereas 0.15 silently means something different as the distribution changes. **[TO LOCK: α]**, with the absolute value it implies recorded at lock.
   >
   > Caveat: the figures are the **ceiling** (severity = 1.0, chunk already in the pool). Realized displacement also depends on how many episode-linked chunks exist and their severity distribution — which needs item 0.
>
   > ⛔ **UNRESOLVED, and it is not on any lock list — found 2026-08-15.** The caveat above says realized displacement needs "item 0", the episode corpus. That corpus now exists (7 184 adjudicated pairs, 30 epochs) and the severity half of the caveat is answered above. **The other half is not, because the term it depends on was never defined.** §2 specifies the treatment as `W_OUTCOME × severity` on *"chunks linked to adjudicated-failure episodes"*, and **nowhere in this registration, in `specs/`, or in the implementation is "linked" given an operational definition.** The one obvious wiring is explicitly forbidden two lines below — *"Do not wire this to the existing `pain` column"* — without a replacement being named.
   >
   > This is not a refinement. Episodes are `tool_use`/`tool_result` pairs in the action archive; chunks are nox-mem memory rows. **There is no join key between them.** The link has to be constructed, and how it is constructed decides which chunks get boosted — that is, it decides the treatment itself. Two defensible constructions (by `sig()` signature; by source-file provenance) would boost different sets and are not interchangeable.
   >
   > **It is registered here as open rather than resolved on the spot**, because choosing the construction is a design decision with the pilot corpus in view, and the right place for it is a declared lock with its rationale — not a footnote written in the same hour it was found. **The study cannot start until it is closed:** without it the treatment arm is underspecified, and an underspecified arm is not randomisable.
   >
   > Recorded plainly: this survived v0.1 through v1.1, one GLM review, one Kimi review and one Grok review. Every reader — including the ones looking for exactly this — read `W_OUTCOME × severity` and checked the coefficient, never the set it multiplies.
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
9. ~~Appendix A (H3 figure specs) + Appendix B (bounds math) written~~ ✅ **WRITTEN 2026-07-26.** A: three frozen figures (retrieval-vs-decision scatter per metric + ordering slope chart), inclusion rules, no binning, and the stated condition that would falsify the H3 narrative. B: bounded-carry-over assumption (B1), the bound τ̂ ± δ·|p₁−p₀|, and the observation that |p₁−p₀| is a **design** quantity. ⚠️ *The clause "driven to zero by transition balancing" that stood here was corrected on 2026-08-15 — no transition-count constraint is registered; see the correction in B.4.* **Still [TO LOCK]: the numeric δ**, which can only be honestly fixed from the pilot's same-arm transition distribution (before it = invented; after seeing effects = adaptive).
10. ~~Ethics/IRB statement~~ ✅ **WRITTEN 2026-07-26** → **Appendix C**. Exemption is claimed on the substantive ground (no human subjects, no third-party data), and the appendix states plainly what the study *does* touch — the author's own production system — and what bounds harm there (low-stakes restriction + mechanical abort). It also declares the COI without softening it.

**Items created by the v0.3 independence model — status as of 2026-07-29:**

| item | status |
|---|---|
| drand chain hash | ✅ quicknet `52db9ba7…`, exercised end-to-end for the calibration seed |
| Bitcoin fallback height rule | ✅ declared (`CALIBRATION-SEED.md`) |
| abort rule parameters | ✅ severity now **S4 / ≥S3** on the anchored rubric (not 0.8); window **3 epochs**; **3×**; baseline window **changed from 90 days to full-history-min-14-days** — the 90 was unsatisfiable |
| panel size and exact model ids | ✅ five families, ids locked; **versions recorded as observed, not pinned** — the CLI panelists self-update |
| adjudication prompt hash | ✅ `5b22f02c…`, governed all 1,500 calibration calls |
| minimum valid verdicts for majority | ✅ **3**, exercised — 5 of 300 episodes fell below it |
| **`T_seed_assign` (UTC instant, post-registration / pre-M4)** | ⏳ **open by construction** — cannot exist before the OSF timestamp |

**Remaining `[TO LOCK]` items — corrected 2026-08-15.** The previous version of this paragraph grouped five items as "all requiring the pilot's same-arm transition distribution". That grouping was wrong on two counts and is superseded:

| Item | Status |
|---|---|
| `N_epochs` | ✅ **174, LOCKED 2026-08-15** (§3, exercising the "powered only for effects ≥ X%" clause at 30%; sized on the ICC **upper** confidence limit 0,1814, as lock (b) of 2026-07-30 requires). |
| numeric `δ` | ✅ **36,67, LOCKED 2026-08-15** (Appendix B.5) — the only one of the five that genuinely needed the same-arm transition distribution. |
| `α` (spread-relative dose) | ✅ **Already locked 2026-07-29** and has been for weeks. The `[TO LOCK: α]` still visible in §9 sits *inside a quoted adversarial-review block*; it is the reviewer's recommendation, which §2 **accepted and implemented** as `W_OUTCOME = w × Δ_cut` with `w ∈ {0.5, 1.0, 2.0}`. `w` *is* that `α`. Listing it here was a stale reference to a resolved item. |
| `p95` winsorization | ✅ **LOCKED 2026-08-15** — 7,45 s (time) and 65 206 tokens (cost), measured over the frozen action corpus by `task_regret.py`. It never depended on same-arm transitions: it is the winsorization point of *task regret* (§4.2, secondary), a different quantity entirely. An earlier note here said it was "not derivable from the current corpus" — **that was wrong**: the archive carries `usage` blocks on the messages that emit each `tool_use`, so both components are measurable. |
| calendar end date | ⏳ Blocked structurally — requires the first randomized epoch, which has not occurred. |
| `T_seed_assign` | ⏳ Blocked structurally — requires the OSF registration to exist first. |

So: **three of the six are locked**, one was already locked and mis-listed, and the two that remain — the calendar end date and `T_seed_assign` — are blocked structurally and resolve themselves in sequence: register on OSF, which fixes `T_seed_assign`; run the first randomized epoch, which fixes the calendar date. **No `[TO LOCK]` item is waiting on analysis.**

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
- **|p₁ − p₀|** is a **design** quantity, computable from the assignment sequence before any outcome is seen. At perfect balance the bound collapses to a point regardless of δ.

  > 🔴 **Correction 2026-08-15 — the mechanism this line invoked does not exist.** The sentence previously read "driven to zero by transition-balancing". The randomisation constraints actually registered in §2 balance **weekday/weekend and calendar halves** — there is **no transition-count constraint anywhere in this document**, and none in the assignment script. The bound was therefore resting on a design property the design does not have.
  >
  > **What that costs, computed rather than asserted.** With `N` = 174 (~87 epochs per arm) and no transition constraint, |p₁ − p₀| behaves like the imbalance of a constrained coin: SD ≈ 0,076, so **E|p₁ − p₀| ≈ 0,06–0,08**. At δ = 36,67 that is a typical half-width of **≈ 2,4 repeated failures per session-hour**, against a mean density of 7,69. The bound does not "collapse to a point" — under the assignment sequence expected *by chance*, it is wide enough to contain an effect of the size the study is powered for.
  >
  > **Pre-committed here, before any assignment exists:** the realised |p₁ − p₀| is computed from the assignment sequence **before unblinding** (it needs no outcome) and reported unconditionally. If it exceeds **0,02**, the carry-over bound is reported with its realised width and declared **non-informative**, rather than presented as a narrow interval. This threshold is fixed now because fixing it after seeing the sequence would be choosing the standard that flatters the sequence drawn.
  >
  > Adding a transition-count constraint to §2 would be the stronger fix, and it is **not** taken: §2 is locked, the constraint set is what the assignment script implements, and rewriting a locked randomisation rule to make an appendix bound look better is the exact move this registration exists to prevent. The honest path is to keep the design and report when its bound is uninformative.

This is the practical payoff of pre-registering the balancing constraints: it makes the bound narrow by construction rather than by assumption.

### B.5 Choosing δ — and why it is not free

δ must be **pre-committed**. Two anchors, both reported:

1. **Empirical anchor.** The observed epoch-to-epoch variation in the primary outcome under the *same* arm (control→control transitions) upper-bounds what non-arm noise contributes. δ is set to the p95 of the absolute epoch-to-epoch difference in those same-arm transitions. This is conservative: it attributes *all* same-arm drift to carry-over.

2. **Mechanistic anchor.** The measured content divergence between successive snapshots. From T7 of the snapshot spec, the corpus divergence per 24 h epoch is **0.144%** and the divergence in what the brief actually serves was **0 of 7,235 slots** in the one epoch with serving data. A snapshot that is ~99.86% identical to its predecessor cannot plausibly carry a large behavioural effect — but the serving-level figure has **n = 1** and is reported as such.

~~**[TO LOCK]** the numeric δ~~ **✅ δ = 36,67 repeated failures per session-hour — LOCKED 2026-08-15.**

Computed exactly as B.5 defines it: the p95 (linear interpolation) of the absolute epoch-to-epoch difference in the primary outcome across same-arm transitions, over the 30-epoch pilot corpus in which **every epoch is control**. 27 of the 29 possible transitions were used; **2 were discarded because the epochs are not calendar-adjacent** (11/07→16/07, a 120 h gap, and 31/07→02/08, 48 h). A difference across a multi-day gap accumulates drift from the whole interval and is not an epoch-to-epoch transition; including them would have inflated δ. Script: `delta_carryover.py`.

**δ is 4,8× the mean per-epoch density (7,69).** That is large, and it is meant to be: B.5 attributes *all* same-arm drift to carry-over, when most of it is traffic noise. The bound it feeds is `τ̂ ± δ·|p₁−p₀|`. ⚠️ **An earlier version of this paragraph claimed `|p₁−p₀|` is "driven toward zero by transition balancing" and concluded the bound stays narrow. That claim was withdrawn on 2026-08-15: no transition-count constraint is registered in §2.** Under the assignment sequence expected by chance, the typical half-width is ≈ 2,6 against a mean density of 7,69 — see the correction and the pre-committed 0,02 threshold in B.4.

**Checked against the obvious objection.** A δ this size could have been an artifact of the corpus's early epochs, where the density is near zero. It is not: recomputed over the mature half of the corpus alone (see the note below), δ is **39,60** — slightly *larger*. δ is driven by ordinary epoch-to-epoch traffic variation, not by the regime transition.

---

#### ⚠️ What computing δ exposed — the pilot corpus is not stationary

Producing δ required looking at per-epoch density for the first time, and it showed something none of the earlier analyses had: **the outcome is not stationary across the pilot corpus.** The first epochs carry density ≈ 0 and later ones an order of magnitude more. The cause is structural, not noise — condition (i) requires a same-signature failure episode written ≥1 epoch earlier, and that stock **grows from 0 to 64 signatures across the corpus without saturating**. On 2026-08-14, the last epoch available, it was still climbing.

Split by that stock (a cut that depends only on condition (i), never on the outcome), at its median of 34 signatures:

| | full corpus | mature half (16 ep) | young half (14 ep) |
|---|---|---|---|
| `r̂` | 28,65 | **44,15** | 15,26 |
| `p̂0` | 0,1165 | **0,1398** | 0,0580 |
| ICC | 0,0985 | **0,0455** | 0,0149 |
| ICC 95% CI | [0,057 ; 0,181] | [0,013 ; 0,132] | [0,001 ; 0,067] |
| δ | 36,67 | 39,60 | 6,87 |

**All three sizing inputs move `N` the same way, and it is downward.** The arithmetic here is at **MDE 25%**, which was the working target when it was computed; it is left at 25% so it stays comparable to the full-corpus figure produced under the same MDE (**N = 152**, the point estimate — *not* the lock, which is 174 at MDE 30% on the ICC upper limit). At MDE 25% the mature-half parameters give **N = 46** against that 152 — and even at the *upper* bound of the mature ICC, **N = 106**, still below the full-corpus point estimate. The design effect falls from 5,87 to 3,25.

**`N` is NOT being changed, and the reason matters more than the number.** Four grounds, in order of weight:

1. **The lock was made hours earlier, and every reason to reopen it points the same way: a shorter study.** That is precisely the pattern pre-registration exists to prevent. A justification that always arrives in the convenient direction deserves more suspicion, not less — even when, as here, it is mechanistically sound.
2. **The mature half has 16 clusters, below the 30–50 floor §9 requires for an ICC estimate.** Its ICC of 0,0455 carries a CI of [0,013 ; 0,132] — wide enough that the honest reading is "somewhere below the full-corpus figure", not a replacement value.
3. **Nobody knows which regime the real study runs in.** The stock is still growing, so the live study will also run under a trend — and the mature half already contains its own residual trend (stock 34→64). Whether stationarity is ever reached is an open empirical question about the system, not a fact this corpus settles.
4. **The cost of being wrong is asymmetric.** Over-sizing spends calendar; under-sizing spends the study. 174 epochs erring toward conservative is the cheap mistake.

#### The estimand slides with the calendar — declared 2026-08-15

A consequence of the non-stationarity above that is **not** neutralised by the trend residualisation in §5, because it is about interpretation rather than validity.

The MDE is **relative** (30%) and the baseline it is relative to *moves*: `p̂0` is 0,116 over the full corpus and 0,140 over the mature half. "30% relative" at the start of the study and at its end are different absolute effects. Worse at the low end: in epochs where the stock of eligible signatures is small, the treatment is **mechanically incapable** of the effect — `W_OUTCOME` reweights chunks linked to adjudicated-failure episodes, and where few such episodes exist there is little for it to move.

So the estimand is **an average over the realised trajectory**, not an effect at a fixed operating point, and its value depends in part on *when* the study runs. Three consequences, all pre-committed:

1. The abstract states the estimand as trajectory-averaged, and states that **a detected effect understates the mature regime**.
2. The **first-half versus second-half** split — already present as a robustness check — is promoted to an **interpretive co-estimand**, reported alongside the primary whether or not the primary is significant. It is the closest available proxy for the mature-regime effect.
3. A **null is not evidence of no effect in the mature regime.** It is evidence against a trajectory-averaged effect ≥30% relative, over a trajectory that includes epochs where the mechanism could not act.

None of this changes the sharp-null permutation test, whose type-I error is exact regardless: arm is orthogonal to study-day by construction (calendar-half balancing), and the outcome is trend-residualised before permutation. What changes is what a *point estimate* means.

**This is registered as a prediction, not a hedge:** if `N = 174` proves conservative, the study will reach its pre-committed horizon with more power than planned. That is a stated expectation on the record now, before the first randomized epoch — not something to be claimed afterwards.

The asymmetry it does surface is real and should be named: **§5 residualizes trend in the test** (outcome regressed on study-day, residuals permuted) while the sizing does not. Sizing on a trend-inflated ICC is conservative and therefore safe, so it is left as is — but the inconsistency is now on the record rather than undiscovered. Script: `maturity_sensitivity.py`.

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
