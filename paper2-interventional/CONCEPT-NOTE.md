# Concept Note — Paper 2 (one page)

> **Working title:** *Interventional Memory: Decision-Relevant Retrieval from Live Multi-Agent Traces*
> (alt: *Retrieval Metrics Can't See What Agent Memory Is For*)
> **Status:** concept note, anticipated 2026-07-12 with authorization (execution remains gated on Paper 1 arXiv ID). Source decisions: `DECISIONS.md` · design detail: `METHODOLOGY.md` · adversarial provenance: `REVIEWS.md`.

## Problem

Dominant memory/retrieval evaluations for LLM agents — nDCG, recall, MRR — measure whether the system ranks the *right document*. For an agent that **acts**, what matters is not ranking well: it is **not repeating the action that failed**. That is a property of the *downstream decision*, not of the ranked list. An IR metric is structurally blind to the thing agent memory exists to do.

**Origin (honest lineage from Paper 1).** Paper 1 bet on pain-weighting and reported the null honestly: pain's isolated retrieval effect was directional but not significant (Δ = +0.0065, CI crossing zero, n=31); section-aware boosting drove ~99.85% of the gain. Our diagnosis: pain did not fail as a mechanism — it was **measured with the wrong instrument**. `pain` is the outcome signal of an *intervention* ("when I did X, it hurt"); a retrieval benchmark cannot reward it because it never measures action outcomes. The null is a measurement artifact, not proof the signal is useless. Paper 2 replaces the headline: out goes pain-as-protagonist, in comes the **decision-relevant value of memory**, measured by an evaluation that can actually see it.

## Claim (one sentence, two-layer)

> For LLM agents, memory value lives in the downstream decision — avoiding costly repeated actions — a property retrieval metrics are structurally blind to; we introduce (i) a **retrospective action-outcome benchmark** over months of production multi-agent traces (observational, log-study layer, stated as such), and (ii) a **small pre-registered randomized A/B arm** on low-stakes live decisions (the *only* layer for which any causal language is used), showing that **outcome-weighted** memory reduces *repeated-failure-rate* where nDCG cannot distinguish policies.

**Terminology rule (hard, from the 3-voice review):** "causal"/"interventional" is reserved **exclusively** for the randomized arm. Everywhere else: *decision-relevant*, *outcome-associated*, *behaviourally validated*. Methods carry the two layers explicitly (benchmark = retrospective log study, n/period stated; causal claim = randomized withholding arm only, pre-registered primary outcome).

## The two figures that close the story

- **Figure A — "metrics lie":** scatter of nDCG/recall vs. repeat-avoidance across memory policies → decorrelated. The old instrument is blind.
- **Figure B — the effect:** randomized arm, outcome-weighted vs. flat memory → lower repeated-failure-rate / task regret. Real incidents (`docs/INCIDENTS.md`, e.g. the double-reindex wipe) are the gold decision episodes.

## Design (hybrid, harm-free bulk + causal validation)

1. **Counterfactual replay harness** (bulk): simulate memory policies offline over the real brief/priming flow (`brief_log`). Zero production harm, large N — observational, and labeled as such.
2. **Randomized A/B, small, live, low-stakes decisions only** (validation): the single causal element, used to validate replay fidelity.

**Guards baked in from day 1 (not retrofitted):**
- **Pre-registration (OSF, timestamped before the A/B):** primary outcome = repeated-failure-rate with full operational definition (what counts as "repeat", time window, action granularity); sample size; stopping rule; randomization strategy; pre-committed analysis (estimator, tests, multiple-comparison correction). Antidote to the researcher-degrees-of-freedom exposure created by Paper 1's post-hoc null.
- **SUTVA / cross-agent interference:** the 6 agents share memory and interact — naive per-session on/off randomization breaks the estimator. Design is **cluster-randomized** (by agent and/or time block) with **washout** between conditions, documented explicitly.
- **Outcome adjudication independent by construction, not by appointment:** blind to arm; judged by a **pinned panel of LLMs from distinct training families** under a pre-registered, hashed prompt. The complete verdict set is **hashed and publicly timestamped before arm labels are ever joined**, so the `raw-trace → action → outcome → failure` pipeline is provably deterministic and specified before analysis — checkable by any reader, rather than attested by a named auditor.
- **Public artifact:** anonymized benchmark (hashed ids, buckets, zero raw text) + label schema + IAA reported; **≥2 baselines run by people outside the team**; analysis code released.
- **Conflict-of-interest declaration:** we own the system, the benchmark, and the proposed metric — stated plainly.

## Reuses vs. builds

| Reuses (nox-mem, in production since 2026-03) | Builds new |
|---|---|
| `brief_log` + priming traces; `docs/INCIDENTS.md` decision episodes | Sanitized public decision-replay benchmark (action-outcome) |
| 6 live agents, shared memory (the SUTVA testbed itself) | Counterfactual replay harness + low-stakes randomized withholding harness |
| Chunk metadata: access, pain, contradiction, salience | **Outcome-weighted** memory variant (the honest evolution of pain) |
| Honest-null track record from Paper 1 (credibility asset) | OSF pre-registration + auditable trace→failure pipeline |

## Venue & kill-conditions

**COLM 2027** (primary; interactions/multi-agent/evaluation) · NeurIPS D&B 2027 if the artifact is serious · EMNLP 2027 fallback (negative-finding + resource). **Killed if:** no pre-registration (vendor whitepaper), SUTVA untreated (desk-reject), "causal" oversold (terminological inflation), or selection/survivorship + Hawthorne/drift left un-addressed in the design.

**Timeline:** T0 = Paper 1 arXiv ID public → OSF pre-registration draft → SUTVA design + replay harness → pre-registration locked → A/B → analysis → draft.
