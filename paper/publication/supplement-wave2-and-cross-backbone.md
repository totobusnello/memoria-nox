# Supplement — Wave 2 closure and cross-backbone analysis (§S5.1.11–S5.1.12, §S5.5.4–S5.5.8)

> Removed from `paper/paper-tecnico-nox-mem.md` on 2026-09-10 and preserved here
> **verbatim**. Nothing was rewritten or condensed. The body keeps every section anchor
> as a stub carrying the headline number, so the manuscript's ~21 internal references to
> these subsections still resolve.

## Why these were moved out

Both blocks are **ablation history**, not the result a reader needs in order to evaluate
the system: §5.1.11–5.1.12 are cross-backbone portability analysis with **zero** internal
citations, and §5.5.4–5.5.8 are the Wave 2 knob-transfer campaign (PRs #423–#426). They
are the same genre as the operational appendices C–G moved out on 2026-09-09 — process,
not measurement.

⚠️ **Honest accounting of what this buys.** A projection published earlier the same day
claimed §5.1 + §5.5 together were 5,159 movable words, which would take the manuscript to
18,846 words and the reference density to 1.59/1,000. **That projection was wrong.** §5.1
cannot move: §5.1.2 (additive salience) and §5.1.3 (`section_boost`) are the evidence the
paper's own title rests on, and §5.1.9/§5.1.10 are cited 12 and 17 times as premises.
What actually moved is 1,908 words, and after the stubs the net reduction is smaller
still. Like the C–G move, this buys **form** — a body that stops reading as a lab
notebook — not the length target. Reaching the accepted-paper band needs further cuts
outside §5.1/§5.5 **and** additional references; the arithmetic is in
`regua-recontada-2026-09-10.md`.

---

## §S5.1.11–S5.1.12 — Cross-backbone analysis and the F_MH retrieval-bound finding

### S5.1.11 Cross-backbone analysis and backbone portability

Phase D (Gemini-2.5-flash) and Phase H v2 (GPT-4.1-mini) together enable a cross-backbone portability comparison against MemOS Table 4:

| System | Gemini-2.5-flash (5-batch) | GPT-4.1-mini (5-batch) | Δ swap |
|---|---:|---:|---:|
| **nox-mem** | **62.22%** | **51.68%** | **−10.54 pp** |
| MemOS | 59.27% | 42.55% | −16.72 pp |

nox-mem regresses **1.6× less** than MemOS on backbone swap (10.54 pp vs 16.72 pp). This structural portability advantage stems from the adapter framework: nox-mem's retrieval layer is backbone-agnostic (FTS5 + dense embeddings + RRF), and the backbone only affects generation. MemOS's memory consolidation pipeline is more tightly coupled to generation model behavior, amplifying regression on backbone swap.

**Important caveats on backbone choice.** GPT-4.1-mini is the only backbone in MemOS Table 4 where *all* memory systems gain over the Full Context baseline (GPT-4.1-mini Full Context: 37.44%, MemOS: 42.55%, nox-mem: 51.68%). The Gemini-3-flash Full Context baseline (72.61%) was a catastrophe zone for MemOS and other systems (regress −13 to −21 pp); nox-mem's Backbone Matrix run (§5.1.10) shows nox-mem **does not regress** under Gemini-3-flash but reaches 63.28% Overall and 88.42% MA composite — above every MemOS Table 4 number, which were obtained on GPT-4.1-mini. The structural difference: nox-mem's adapter framework separates retrieval (backbone-agnostic FTS5 + dense + RRF) from generation, while MemOS's tighter coupling amplifies regression on frontier-backbone swaps. Llama-4-Scout remains a weak baseline. The valid cross-backbone comparison spans **Gemini-2.5-flash, GPT-4.1-mini, and Gemini-3-flash**.

---

### S5.1.12 F_MH retrieval-bound finding (gpt-4.1-mini era) — strategic implication

The F_MH (multi-hop) gap vs MemOS is **backbone-invariant**:

| Backbone | nox-mem F_MH (5-batch) | MemOS F_MH (Table 4) | Gap |
|---|---:|---:|---:|
| Gemini-2.5-flash | 5.22% (Phase D) | 18.94% | −13.72 pp |
| GPT-4.1-mini | ~3–5% (Phase H v2) | 18.88% | −13 to −16 pp |

The same gap magnitude on two independent backbones implies the gap on the EverMemBench corpus specifically is **retrieval-bound** (the right multi-hop chunks are not surfacing in the structured Memory Awareness sub-tracks), NOT generation (the LLM can reason multi-hop when given the right evidence). This was confirmed by partial gap closure from retrieval-side mechanisms: cross-encoder rerank (§5.1.7) +1.61 pp (11.7%), KG path (§5.1.8.1) +2.81 pp (17%), KG+MAP composed (§5.1.9) +4.04 pp (~24%). The Wave C ceiling (§5.1.9) caps retrieval-stage stacking at ~+7.25 pp F_MH.

**Reframing (see §5.4):** the §5.2 classical multi-hop QA results (MuSiQue-Ans dev answer F1 58.62%, HotPotQA distractor dev answer F1 73.37%) place nox-mem's multi-hop reasoning well above the specialized readers these datasets are conventionally compared against and roughly 10–12 points below current published SOTA — competent, with headroom. That rules out a wholesale multi-hop reasoning failure as the explanation for the EverMemBench F_MH 3–7% absolute, and points to the task setup (very long conversation chains + strict scoring + entity-anchor sparsity) as the principal factor; the same-metric evidence for the track's difficulty is that the best published system on it, MemOS, reaches only 18.88% strict EM. It does not establish that the corpus accounts for the entire gap. The §5.4 section develops what the evidence supports.

---


---

## §S5.5.4–S5.5.8 — Wave 2 closure

### S5.5.4 Empirical per-backbone × per-knob composability matrix (Wave 2 closure, replaces D74 projection)

The D74 revision of this section contained a projection table assuming Wave A/B/C retrieval-side lifts measured on gpt-4.1-mini transfer additively to the Gemini-3-flash backbone. Wave 2 (2026-05-31, D75, PRs #423–#425) empirically tested this assumption. The projection is replaced by the measured matrix below.

**Empirically measured per-backbone × per-knob F_MH matrix (5-batch CLEAN, n=3,121, batches 004/005/010/011/016):**

| Backbone | Knob | F_MH lift (5-batch CI) | Gate +1.5 pp | Validated? | Source |
|---|---|---:|:---:|---|---|
| gpt-4.1-mini | KG path | +2.81 pp (CI [2.11, 9.93]) | PASS | YES | PR #379 |
| Gemini-3-flash | KG path | −0.01 pp (CI [3.00, 9.04]) | FAIL NO-REPLICATE | 0% transfer | PR #423 |
| gpt-4.1-mini | AC (threshold=5) | +2.01 pp (CI [1.06, 9.39]) | PASS marginal | YES | PR #381 |
| Gemini-3-flash | AC (threshold=5) | +0.81 pp (CI [4.62, 9.03]) | FAIL NO-REPLICATE | 40% transfer | PR #424 |
| gpt-4.1-mini | MQ standalone | +3.61 pp | PASS | YES | PR #385 |
| Gemini-3-flash | MQ standalone | +1.21 pp (CI [4.99, 9.48]) | FAIL borderline | 34% transfer | PR #425 |
| Gemini-3-flash | IterB ReAct | +2.01 pp (bare CLEAN) | PASS | **ONLY VALIDATED** | PR #419 |
| Gemini-3-flash | IterB + Wave C triple | INDETERMINATE | — | infra-bound | PR #426 (D76)¹ |

> ¹ **D76 capstone deferral footnote (§5.5.8):** The IterB + Wave C triple composability test (PR #426) was aborted due to Hostinger VPS CPU steal 51–97% sustained, not due to scientific failure. Batch 004 (n=49) preserved. 5-batch threshold not reached. Outcome is INDETERMINATE; composability claim is neither confirmed nor refuted. Capstone deferred to future stable infrastructure with dedicated CPU SLO.

**Headline numbers.** The 3-knob sum on Gemini-3-flash (KG −0.01 pp + AC +0.81 pp + MQ +1.21 pp) = **+2.01 pp aggregate** = 24% of the D74 pessimistic projection of +8.43 pp. All three individual knob CIs fully overlap the Gemini-3-flash baseline (6.02%), meaning no single knob clears statistical significance at the +1.5 pp gate. IterB ReAct standalone (+2.01 pp clean, §5.5.2) equals the entire 3-knob aggregate while being structurally distinct — an orchestration-stage mechanism rather than retrieval-stage augmentation.

**Corrected composability landscape.** The original D74 projection table (IterB + Wave C triple → ~12.07% F_MH = ~41% MemOS gap closure) assumed backbone-invariant transfer of all knob lifts. That assumption is empirically refuted on Gemini-3-flash for all three tested retrieval-stage knobs. The current empirically supported picture:

| Configuration | F_MH | Closure of MemOS F_MH gap (~18.88 pp) | Status |
|---|---:|---:|---|
| Bare Gemini-3-flash | 6.02% | baseline | measured |
| **IterB ReAct standalone on bare (this work, §5.5.2)** | **8.03%** | **~7%** | **measured** |
| IterB + retrieval-stage knobs (aggregate upper bound) | ~8–9% | ~10–15% | bounded estimate |
| IterB + Wave C triple (orchestration composability) | INDETERMINATE | INDETERMINATE | D76 deferred |

---

### S5.5.5 Wave 2 — Single-stage knob backbone-portability refinement (D75)

**Setup.** Wave 2 Phase 1 (R0 sanity, PR #423) and Phase 1.5 (AC + MQ re-baseline, PRs #424 + #425) re-ran all three principal Lab Q1 single-stage retrieval knobs on the Gemini-3-flash backbone (D70, §5.1.10) using the identical 5-batch CLEAN sequential protocol (n=3,121, batches 004/005/010/011/016). The motivation: D74 composability projection assumed knob lifts measured on gpt-4.1-mini were backbone-invariant. R0 tested this assumption for KG path before dispatching the full composability matrix run.

**3-knob NO-REPLICATE pattern.** Three independent retrieval-stage knobs all show the same structural pattern:

| Knob | gpt-4.1-mini F_MH | Gemini-3-flash F_MH | Transfer rate | 95% CI on Gemini |
|---|---:|---:|---:|---|
| KG path (R0, PR #423) | +2.81 pp | **−0.01 pp** | 0% | [3.00, 9.04] |
| AC threshold=5 (PR #424) | +2.01 pp | **+0.81 pp** | 40% | [4.62, 9.03] |
| MQ standalone (PR #425) | +3.61 pp | **+1.21 pp** | 34% | [4.99, 9.48] |
| **3-knob sum** | **+8.43 pp** | **+2.01 pp** | **24% aggregate** | — |

All three Gemini-3-flash CIs fully overlap the bare baseline (6.02%). The pattern is consistent across knobs of different mechanism families (entity-walk SQL, heuristic query routing, LLM sub-query decomposition), indicating a structural backbone-conditional property rather than a knob-specific failure.

**Mechanism interpretation.** The hypothesis consistent with all three observations: Wave A knobs were designed to compensate for context-bottleneck weaknesses of gpt-4.1-mini — smaller context window, weaker filtering, lower context utilization per token. Gemini-3-flash's larger context window and stronger native context utilization saturates the compensation signal that these knobs provide, yielding diminishing marginal returns. KG path (0% transfer) is the extreme case: Gemini already processes the relevant entity graph context from retrieved chunks without requiring explicit vault-fact injection. AC and MQ show partial transfer (34–40%) because their mechanisms involve multi-round or breadth-expansion effects that provide some marginal diversity even for stronger backbones, but not enough to clear the statistical gate.

**Generalization principle.** Any retrieval-stage knob lift of the form "Knob X delivers +N pp on backbone Y" is backbone-conditional. Cross-backbone generalization requires explicit re-baseline. As backbones strengthen (Claude Opus 4.7, GPT-5, Gemini 4), retrieval-stage compensation mechanisms may show further transfer-rate attenuation. Future composability projections should re-baseline each knob on the target deployment backbone before projecting stacked effects.

---

### S5.5.6 Wave 2 — MQ multi-axis backbone-conditional behavior (sub-finding, PR #425)

The MQ re-baseline (PR #425) revealed a sub-finding that is paper-worthy independent of the NO-REPLICATE verdict: MQ exhibits **inverse backbone-portability across metric axes**.

| Metric axis | gpt-4.1-mini result | Gemini-3-flash result | Direction |
|---|---|---|---|
| F_MH lift | +3.61 pp (biggest single retrieval knob) | +1.21 pp (borderline, CI overlap) | Attenuates |
| MA composite | −1.38 pp (regression) | **+0.12 pp (preserved)** | **Flips sign** |
| MA_U (Memory Update) | modest | **+3.10 pp** (strongest MA gain in Wave 2) | Inverts entirely |

On gpt-4.1-mini, MQ sub-query decomposition multiplies retrieval breadth but introduces noise that the backbone cannot fully filter — manifesting as MA composite regression. On Gemini-3-flash with stronger filtering and broader context integration, the wider retrieval pool from MQ sub-queries is interpretable rather than noisy, yielding MA_U improvement (Unrelated detection benefits from additional diversity in retrieved context).

**Implication.** Per-knob evaluation on a single metric axis (F_MH alone) can hide compensating effects on orthogonal dimensions. Retrieval-stage mechanisms with multi-factor effect profiles (knob benefits on dimension A, costs dimension B on backbone X; costs A but benefits B on backbone Y) require multi-axis backbone-conditional reporting. The gpt-4.1-mini measurements in §5.1.8 remain valid for that backbone but should not be assumed to represent the MA dimension on stronger backbones.

---

### S5.5.7 Architectural composability vs mechanism composability

Wave 2 Phase 2 setup (PR #426, capstone) exposed a third composability requirement independent of backbone-portability: **architectural composability** between orchestration-stage mechanisms (IterB ReAct) and retrieval-stage mechanisms (Wave A knobs).

**Code evidence (`eval/evermembench/adapter_nox_mem.py`).** The PR #419 IterB adapter contains explicit guards at three locations:

```python
# Line 2736 — MQ short-circuit
if not iterb_used_path:
    # ... MQ sub-query decomposition + RRF fusion logic ...

# Line 2906 — KG path short-circuit
if not iterb_used_path:
    # ... KG entity extract + 1-hop walk + vault-fact injection ...

# Line 3063 — cross-encoder rerank short-circuit
if not iterb_used_path:
    # ... bge-reranker-v2-m3 cross-encoder rerank ...
```

The `iterb_used_path` flag is set when IterB's ReAct loop fires on a query. Each Wave A knob checks this flag and skips itself if IterB took the path. Setting `NOX_ADAPTER_MODE=phaseTriple` combined with `NOX_ITERB_ENABLED=1` does **not** produce a composed IterB + Wave C triple system — IterB takes exclusive precedence and phaseTriple stages are bypassed entirely.

**Design rationale (reconstructed from D74 intent).** IterB ReAct per-round retrieval already uses the full hybrid stack (FTS5 + vec + RRF). Adding KG + MQ + MAP per ReAct round would multiplicatively expand per-round cost (×N stages × 4.25 mean rounds) without empirically validated additivity. The conservative default — exclusive operation with explicit short-circuits — was the rational design choice at D74 time.

**Scientific implication.** D74's composability projection (IterB + Wave C triple → ~12.07% F_MH) implicitly assumed architectural composability. The code evidence shows that assumption was **false by design** — the system would have needed an explicit code patch to test it. This demonstrates a general principle: orchestration-stage mechanisms designed without forward-looking composability planning create silent architectural locks discoverable only by empirical code-level inspection. The lock is not a bug; it is a design decision with sound rationale. But it invalidated the composability projection as stated.

**Partial composability test (PR #426 capstone design).** The Wave 2 capstone agent patched 2 of 3 guards: KG vault-fact injection (line 2906, removed — KG facts injected per ReAct round) and cross-encoder rerank (line 3063, removed — reranks IterB's merged candidate pool). The MQ guard (line 2736) was deliberately kept because IterB ReAct sub-queries are semantically equivalent to MQ decomposition; composing both would double-decompose without mechanistic benefit. This partial composability test was the object of the D76 capstone run; the infrastructure abort (§5.5.8) means the result remains INDETERMINATE.

**Future research recommendation.** When designing new orchestration-stage mechanisms, specify upfront whether they should compose with or short-circuit existing mechanisms. Document the integration choice in the spec PR. This prevents discovering composability locks post-implementation via code archaeology — and prevents composability projection errors in interim paper revisions.

---

### S5.5.8 Wave 2 Capstone — D76 infrastructure abort (INDETERMINATE, not scientific failure)

The Wave 2 Phase 2 Capstone (PR #426 draft, IterB + KG + rerank composability, 2-guard patch per §5.5.7) was dispatched on the production Hostinger VPS on 2026-05-31. After 48 hours elapsed and ~$20–25 spent, the bench was aborted due to Hostinger anti-abuse CPU throttling, not due to scientific hypothesis failure.

**Infrastructure failure timeline.**

| Measurement window | CPU steal | State |
|---|---:|---|
| Pre-second reboot | 96.93% | critical |
| Immediately post-second reboot | 8.54% | brief recovery (8 min) |
| 30 min post-reboot | 21.03% | degrading |
| Sustained working state | 51–71% | oscillating |
| Bench running (ONNX rerank active) | 51–97% | throttled |

Mitigation attempted: openclaw service disable, taskset CPU pinning (cores 0–3 eval / 4–5 API), ORT/OMP/MKL/OpenBLAS thread caps to 2, search timeout extension 120 s → 600 s, concurrency reduction 3 → 1, two VPS reboots. None achieved sustained CPU steal below 30% under bench load. Mathematical impossibility under sustained throttle: 20 retries × (600 s + 300 s) = 5 h max per query × 50 questions × 4 batches = 1,000 h ceiling. Batch 005 ran 23 h with 0/50 questions completed.

**Distinction: infrastructure abort is not scientific failure.** The distinction is load-bearing for interpreting this result:

- A *scientific failure* means the hypothesis was tested and the data refuted it — a publishable negative result.
- An *infrastructure abort* means the hypothesis was not testable in the current environment — the outcome is INDETERMINATE, neither confirming nor refuting the hypothesis.

The capstone abort falls in the second category. The hypothesis (IterB + KG + rerank compose on Gemini-3-flash for F_MH gain) remains scientifically open. Batch 004 (n=49 questions, completed pre-second-reboot) is preserved at `/root/.openclaw/evermembench-runs/capstone-iterB-triple-004-1780260019/analysis.txt` for future re-run but does not constitute valid 5-batch evidence alone.

**Deferred infrastructure requirement.** Completing the capstone requires a dedicated CPU plan with a guaranteed CPU SLO — ONNX cross-encoder rerank (bge-reranker-v2-m3) is CPU-bound; shared VPS infrastructure with host-level anti-abuse scanning is insufficient for sustained heavy ONNX workloads. The capstone is deferred to Q1+ on stable infrastructure (dedicated CPU plan or alternate provider).

**Wave 2 scientific output.** Despite the capstone abort, Wave 2 delivers five paper-worthy findings: (1) D74 IterB +2.01 pp clean F_MH lift on Gemini-3-flash (§5.5.2); (2) D75 3-knob NO-REPLICATE backbone-conditional pattern (§5.5.5); (3) MQ MA backbone flip sub-finding (§5.5.6); (4) architectural composability lock discovery (§5.5.7); (5) this D76 honest infrastructure framing (§5.5.8). The 12 measured dimensions documented in §5.1–§5.7 are unaffected by the capstone outcome.

---

---

## Moved 2026-09-11 — §5 shortening for the arXiv appeal

> These three subsections were removed from the manuscript **verbatim** on 2026-09-11.
> Reason, stated plainly: the manuscript's only remaining gap of *form* is length, and the
> reference-density floor of the symmetric ruler (2.06/1000 words) cannot be met at 28,228
> words with 55 distinct works. Each keeps a stub in the body carrying its headline number.

#### S5.1.8 EverMemBench Lab Q1 — Retrieval augmentation standalone knobs (5-batch)

Four Lab Q1 standalone experiments shipped in 2026-05-29, targeting the backbone-invariant F_MH gap identified in §5.1.10. Each is evaluated against the Phase H v2 GPT-4.1-mini baseline with 5-batch protocol.

##### 5.1.8.1 Lab Q1 #4 — KG path retrieval (3/4 gates WIN)

**Approach:** 1-hop entity boost via regex entity extraction from query text + `kg_relations` SQL walk. Zero LLM calls at query time. Cost: $0/query. PR #379.

| Gate | Threshold | Actual | Decision |
|---|---|---:|:---:|
| F_MH lift | >= +2 pp | **+2.81 pp** | PASS |
| Overall non-regression | >= 0 pp | **+0.12 pp** | PASS |
| Coverage (queries with entity match) | >= 30% | **90.84%** | PASS |
| MA avg lift | >= +1 pp | +0.44 pp | FAIL |

Full 5-batch results vs Phase H v2 baseline:

| Metric | Phase KG (5-batch) | Phase H v2 baseline | Δ | vs MemOS GPT-4.1-mini |
|---|---:|---:|---:|---:|
| Overall | 51.80% (CI 50.27–53.34) | 51.68% | +0.12 pp | +9.25 pp |
| F_MH | **6.02%** (CI 2.11–9.93) | 3.21% | **+2.81 pp** | −12.86 pp |
| MA_P | 66.60% | 65.40% | +1.20 pp | +14.61 pp |

The KG path mechanism closes **~17% of the MemOS F_MH gap** via pure retrieval-side SQL + regex — no LLM involvement. The regex entity extractor achieves 90.84% coverage of the eval query set (91% of queries contain at least one entity name that matches `kg_entities`), with sub-50 ms p50 overhead. MA_C and MA_U remain flat; MA_P alone improves +1.20 pp. MA avg misses the >=+1 pp gate at +0.44 pp (deficit driven by MA_C flatness).

**Verdict:** ship opt-in (`NOX_KG_PATH_ENABLED=1` / `--kg-walk=1`). Default OFF until KG density increases (current ~544 relations sparse) or composability with Lab Q1 #1 adaptive classifier routes KG path selectively to avoid profile-query MA regressions.

##### 5.1.8.2 Lab Q1 #1 — Adaptive query classifier (2/4 gates, fragile)

**Approach:** heuristic query classifier (Option A, threshold=5 keyword features) routes queries above threshold to cross-encoder rerank path; queries below threshold use standard hybrid retrieval. Activation rate target 30–60%. PR #381.

| Gate | Threshold | Actual | Decision |
|---|---|---:|:---:|
| Overall >= Phase H v2 | 51.68% | 51.21% | FAIL (−0.47 pp) |
| F_MH >= Phase H v2 CI-strict | 3.21% (CI lower) | 5.22% mean (CI [1.06, 9.39]) | FAIL CI overlaps |
| MA mean >= 72.84% (0.5 pp tol) | 72.84% | 71.72% | FAIL (−1.63 pp) |
| Activation rate 30–60% | target band | 44.2% | PASS |

The F_MH mean lift of +2.01 pp is comparable to KG path (+2.81 pp) but the 95% CI [1.06, 9.39] overlaps the baseline — statistically not significant. MA regresses −1.63 pp, confirming that adaptive routing does not fully avoid the Memory Awareness cost of cross-encoder rerank. Overall regresses −0.47 pp.

**Verdict:** ship opt-in only (`NOX_ADAPTIVE_CLASSIFIER=1` / `--adaptive`). NOT default-enabled. Cost-benefit clearly favors KG path (Lab Q1 #4) over adaptive classifier for F_MH improvement: KG is $0/query SQL+regex with 3/4 gates vs AC requiring rerank infra + classifier compute with 2/4 gates fragile.

##### 5.1.8.3 Lab Q1 #2 — Memory-aware projection / MAP (bypass-entity, F_MH + F_HL WIN)

**Approach:** entity-aware retrieval bypass — when query lacks section-anchored entity tokens, the classifier routes to the global pool (Set E = empty), bypassing entity-only chunk restriction. Used Approach A (bypass-entity) due to EverMemBench corpus lacking section markers. PR #386.

| Metric | Phase MAP (5-batch) | Phase H v2 baseline | Δ |
|---|---:|---:|---:|
| F_MH | — | — | **+4.02 pp** (2.5× Phase G rerank) |
| F_HL | — | — | **+4.34 pp** |
| MA composite | — | — | **−6.55 pp** (gpt-4.1-mini amplifies rerank trade-off) |
| Overall | — | — | mixed |

MAP isolates the bypass mechanism: when a query is profile-shaped (no entity anchors), refusing to constrain retrieval to entity chunks reveals the right multi-hop evidence. The mechanism composes with KG path because they operate at different retrieval stages (KG = entity-walk during candidate gen; MAP = section bypass during pool selection).

**Verdict:** ship opt-in (`NOX_MAP_ENABLED=1`). Hard MA trade-off rules out default-enabled until query classifier (Lab Q1 #1) can selectively route to avoid MA-fragile queries. Composability path with KG identified for Wave B.

##### 5.1.8.4 Lab Q1 #3 — Multi-query expansion / MQ (3/4 gates, biggest F_MH knob)

**Approach:** sub-query decomposition via gemini-flash-lite + RRF union on top-k from each sub-query. Adds one cheap LLM call per query (~$0.0002, p50 ~400 ms). PR #385.

| Gate | Threshold | Actual | Decision |
|---|---|---:|:---:|
| F_MH lift | >= +2 pp | **+3.61 pp** (2× KG, biggest single retrieval-side) | PASS |
| Overall non-regression | >= 0 pp | −1.12 pp (narrowly misses) | FAIL |
| MA composite >= baseline | flat | −1.38 pp | PASS (within band) |
| Coverage / cost | reasonable | $0.0002 / 400 ms | PASS |

MQ is the **biggest single retrieval-side F_MH knob** measured in Lab Q1 (2× KG path). The −1.12 pp overall regression is below the 0-pp non-regression gate, but additive composability with KG was modelled at **+6.42 pp F_MH (KG + MQ)** = 41% closure of MemOS F_MH gap — actually validated in Wave B (§5.1.9).

**Verdict:** ship opt-in (`NOX_MQ_ENABLED=1`). Default OFF until paired with KG (Wave B composability).

---

#### S5.1.9 Wave B + Wave C composability — additive F_MH and the retrieval-stage ceiling

The Lab Q1 standalones identified four orthogonal mechanisms with overlapping F_MH lift profiles. Wave B (D68, PR #393) and Wave C (D69, PR #399) measure composability — do they stack, or do they overlap?

**D68 KG + MQ co-fire analysis (same-stage retrieval):** KG path and MQ expansion overlap at **90.8% co-fire rate** on EverMemBench queries — both activate on the same query population (entity-bearing multi-hop queries). Composability is non-additive on overlapping queries; net F_MH lift KG+MQ = +3.93 pp (vs predicted +6.42 pp), confirming the overlap.

**D68 KG + MAP composability (different-stage):** KG (entity-walk) and MAP (section bypass) operate at different retrieval stages and compose additively:

| Configuration | F_MH | Δ vs Phase H v2 |
|---|---:|---:|
| Phase H v2 baseline | 3.21% | — |
| Phase KG standalone | 6.02% | +2.81 pp |
| Phase MAP standalone | ~7.23% | +4.02 pp |
| **Phase KG+MAP composed** | **7.25%** | **+4.04 pp (additive on F_MH)** |

KG+MAP closes **~24% of the MemOS F_MH gap** while staying within MA tolerance on multi-stage composition (MAP MA cost is partially absorbed when KG entity-walk pre-filters profile queries).

**D69 Wave C ceiling — same-stage retrieval triple compose:** Wave C tested KG + MQ + MAP triple composition with CLEAN refinement (sequential 5-batch + outlier-aware aggregation). Result: triple composition caps at **~7.25 pp F_MH**, **statistically indistinguishable from KG+MAP doublet**. Adding MQ on top of KG+MAP yields no incremental lift. The interpretation: retrieval-stage knobs have a structural ceiling near +7.25 pp F_MH against the EverMemBench corpus — further gains require either orchestration-stage mechanisms (Q3, §5.5) or backbone upgrades (§5.1.10).

**Composability triangulation summary (D64-D69):**

1. Same-stage retrieval knobs **overlap** (D68: KG + MQ 90.8% co-fire) — composing them does not add proportionally.
2. Different-stage knobs **compose additively** on F_MH (D68: KG + MAP +4.04 pp combined).
3. Retrieval-stage stacking **caps at ~+7.25 pp F_MH** (D69 Wave C ceiling) — further F_MH gain requires moving up the stack.
4. Q3 orchestration is the open path for incremental F_MH gain beyond the retrieval ceiling (§5.5).

---

#### S5.5.2 Q3 IterB ReAct — F_MH retrieval-stage ceiling break on best backbone (NEW)

**Method.** Q3 IterB ReAct (Yao et al. 2022, arxiv:2210.03629) — multi-round retrieve-reason loop. The orchestrator (gemini-2.5-flash-lite, low-cost cheap-class) generates `thought → action (search) → observation` cycles up to 5 rounds (mean 4.25 rounds across the 5-batch set), with the final-answer backbone (gemini-3-flash-preview, the in-matrix strongest, §5.1.10). Evaluated on EverMemBench using the canonical 5-batch sequential protocol (batches 004 / 005 / 010 / 011 / 016, n=3,121 queries). PR #419.

**Headline (dual-baseline honest reporting, per D74 convention §5).** The Phase H v2 (GPT-4.1-mini) baseline conflates ReAct mechanism lift with the backbone swap; the gemini-3-flash bare baseline isolates the clean mechanism effect on the strongest backbone. The ceiling-break claim load-bears on the latter.

| Metric | IterB vs Phase H v2 conflated (GPT-4.1-mini) | Δ conflated | IterB vs gemini-3-flash bare CLEAN | Δ bare HONEST |
|---|---:|---:|---:|---:|
| Overall | 51.68% → 62.70% | **+11.02 pp** | 63.28% → 62.70% | −0.58 pp (within ±1.5 pp CI noise) |
| **F_MH** | 3.21% → **8.03%** | **+4.82 pp** | 6.02% → **8.03%** | **+2.01 pp** |
| F_TP | 15.00% → 33.33% | +18.33 pp | n/a | n/a |
| F_HL | 22.68% → 43.06% | +20.38 pp | n/a | n/a |
| MA composite | 73.34% → 84.89% | +11.55 pp | 88.42% → 84.89% | −3.53 pp (borderline) |
| Cost / query | n/a | — | within $0.005 ($0.00295 measured) | PASS |

**Interpretation — two ship verdicts.** Against the project-convention Phase H v2 baseline the result clears 4/4 gates (SHIP_DEFAULT_CANDIDATE). Against the gemini-3-flash bare baseline — the load-bearing comparison for any ceiling-break claim — the result clears 3/4 gates: F_MH +2.01 pp PASS, Overall within CI noise PASS, cost within budget PASS, MA composite borderline (−3.53 pp, falls inside the MA tolerance band but at its lower edge). Final verdict: **SHIP_OPT_IN** (`NOX_Q3_ITERB_ENABLED=1`). The opt-in framing reflects the MA borderline, not the F_MH or cost finding.

**Why two baselines.** Reporting only the +4.82 pp F_MH vs Phase H v2 would conflate two distinct effects: (i) the backbone swap GPT-4.1-mini → Gemini-3-flash, which alone delivers +20.73 pp Overall and +32.74 pp MA composite (§5.1.10, Backbone Matrix), and (ii) the IterB ReAct multi-round mechanism. The +2.01 pp F_MH vs gemini-3-flash bare is the **clean isolated ReAct effect**, with backbone held constant. The +0.78 pp by which this clean number exceeds the Wave A/B/C single-stage retrieval ceiling of 7.25 pp (D69, §5.1.9) is the load-bearing ceiling-break claim.

**Mechanism instrumentation (Set E).** The 5-batch run reports IterB applied to 99.6% of queries (3,107 of 3,121, zero errors, zero generation-backbone fallbacks), mean 4.25 rounds with p95=5, 99.5% terminated via `answer` action versus 0.5% via `max_rounds` exhaustion, and round-2 chunk overlap mean of 0.257 with round-1 (LOW overlap — ReAct explores new evidence rather than re-fetching the same chunks, the sweet-spot mechanism profile for sequential refinement).

**Ceiling refinement — D74 vs D69 / D72.** D69 established the Wave A/B/C single-stage retrieval ceiling at +7.25 pp F_MH (§5.1.9). D72 (PR #410, third revision) framed F_MH as "structural challenge of EverMemBench" on the strength of the MuSiQue / HotPotQA / LoCoMo retrieval results, which that revision described as SOTA; §5.2 now states them as competent-but-below-SOTA, and the structural framing rests instead on the same-metric observation that the best published system on this track reaches 18.88% strict EM. D74 refines this framing: F_MH is **still largely structural** (long chains × cross-session compression × strict EM scoring), but MAS orchestration via ReAct adds **+2 pp clean F_MH on top of the strongest backbone above the retrieval-stage ceiling**. The paradox is refined rather than dissolved — closing the EverMemBench F_MH gap now has both a backbone path (Backbone Matrix, §5.1.10) and an orchestration path (Q3 IterB ReAct, this section), in addition to retrieval-stage mechanisms (Wave A/B/C, §5.1.8/§5.1.9).

#### S5.1.4 Wave A — Claims 3 & 4: `tier_boost` and `source_type` calibration

**`tier_boost` off-by-default.** Isolated, `tier_boost` (boost for `chunks` flagged as `tier='core'`) is actively harmful: A6 (tier only, no other boosts) reaches 0.4059, **−21% versus the no-boost baseline 0.5126**. Even integrated into the full stack, A9 (full + tier enabled) drops to 0.5884, **−5.7% versus A8**. Inspection of the corpus reveals the cause: `tier='core'` chunks account for only 3.96% of the corpus and consist of memory-system internals (lifecycle docs, schema metadata, operational runbooks) rather than user content — over-promoting them displaces directly-relevant entity facts. PR #150 makes tier_boost **off by default** via `NOX_DISABLE_TIER_BOOST=1`, with an explicit opt-in preserved for backward compatibility.

**`source_type` backfill and Hard Mutex.** Pre-backfill, **67,949 chunks (98.48% of the corpus)** carried `source_type = NULL`, rendering the `SOURCE_TYPE_BOOST` map inert. PR #151 backfills 11 canonical keys via deterministic path/prefix rules under `withOpAudit()`. The G8 ablation (PR #177) empirically validates +2.66% lift when keys match. However, G9 (68k prod corpus) reveals **redundant double-boost** when `section_boost` and `SOURCE_TYPE_BOOST` stack on identical entity-file chunks — the redundancy is 5× larger at prod scale than in the synthetic G8 set (−2.6% vs −0.81%). PR #182 (Hard Mutex) zeroes `source_type_boost` when a chunk carries `section in {compiled, frontmatter, timeline}`, recovering +0.79% nDCG / +2.65% MRR (G10). The conditional gate G10d (PR #198, `NOX_MUTEX_QUERY_ENTITY_THRESHOLD=2`) further recovers multi-hop (+1.58% nDCG, +3.75% R@10) and adversarial (+3.04% nDCG, +6.25% MRR) regressions introduced by the hard mutex, at the cost of moderate single-hop dilution. The canonical production boost stack is:

> `section_boost × source_type_boost (Hard Mutex, query_entity_count <= 2) × salience v2 additive`

The full G3 → G4 → G5 V3 → G8 → G9 → G10 → G10b → G10c → G10d trajectory and all ablation matrices are archived in `audits/data-G*/` and observable via the F10 dashboard (`/observability/evals.html`).

---

#### S5.5.3 Mechanism-class distinction — parallel decomposition vs sequential refinement

The Q3 IterC F_MH no-lift (−0.40 pp, §5.5.1) and Q3 IterB F_MH +2.01 pp clean lift (§5.5.2) together establish a mechanism-class distinction that is sharper than any individual measurement.

| Mechanism class | Example | Q3 result | F_MH lift | F_HL lift |
|---|---|---|---:|---:|
| Parallel decomposition | Self-Ask, Decomposed prompting | **Q3 IterC (shipped opt-in)** | no-lift (−0.40 pp) | **+35.84 pp** (measured) |
| Sequential refinement | **ReAct (Yao 2022), Iterative retrieval** | **Q3 IterB (shipped opt-in, D74)** | **+2.01 pp clean (above ceiling)** | n/a |
| Single-round augmentation | KG path, MQ, MAP | §5.1.8 standalones | +2.81 to +4.04 pp (capped at Wave C ceiling 7.25 pp) | marginal |

**Why the class matters.** Self-Ask retrieves all sub-questions in parallel — appropriate when the synthesis target factors into independent sub-facts (F_HL). EverMemBench F_MH is a **sequential dependency** task where each hop depends on the previous hop's resolved entity; parallel decomposition cannot help because the second sub-question is not knowable until the first has resolved. ReAct's `thought → action → observation` loop fits the sequential dependency structure directly: each round's observation refines the next thought's action. The +2.01 pp clean F_MH lift on Gemini-3-flash bare confirms the class-fit empirically.

**Practical reading.** Workloads with high F_HL share benefit from IterC; workloads with high F_MH share benefit from IterB. Both ship opt-in. Routing a query to the appropriate orchestration mechanism (parallel vs sequential) is an open Q1 work item.

#### S5.3.3 Path to >=55% F1 — composition orchestration (Q3)

Wave C ceiling analysis (§5.1.9) demonstrates that retrieval-stage knobs cannot lift LoCoMo F1 above the verbosity gap. The path to >=55% F1 (rank-3 territory) requires **orchestration-stage** mechanisms: prompt-level fact extraction, iterative refinement (Q3 IterB ReAct), or explicit answer-shaping. §5.5 reports the first measurement on this axis.

---

---

## Moved 2026-09-11 — §1.4 design-space table

Relocated from §1.4 of the main paper during the form and length pass for the arXiv
appeal. It is a map of the design space compiled from each system's own documentation,
not an evaluation: only the `nox-mem` column is measured, and the measured cross-system
comparison lives in §6 of the main paper. It sat in the introduction, where a
nine-column matrix against named systems reads as a vendor comparison rather than as
related work.

Across these systems, six recurring gaps appear in the design space. Each gap motivates a concrete subsystem of nox-mem. Table 1 summarizes who covers what:

**Table 1 — Design-space coverage of the six gaps, as reported by each system's own
documentation.**

⚠️ **What this table is and is not.** Only the `nox-mem` column is measured here. Every
other cell records what that system's paper, README, or API reference *states* about
itself, read between 2026-05 and 2026-06; we did not deploy the other six systems to
verify their claims, and §6 explains why only two of them (Mem0 and agentmemory) could be
brought to a same-corpus comparison at all. A cell therefore answers "does the system
claim this property?", not "does the system have it?". `n/r` means the source material
does not address the gap either way — it is an absence of documentation, not a negative
finding. Read the table as a map of the design space that motivates §§2–4, and not as an
evaluation of competing systems.

| # | Gap | nox-mem (measured) | mem0 | Letta | Zep | EverOS | LightRAG | MeMo |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | Static injection | yes — live writeback | partial | yes | yes | yes | no — batch | no — retrain |
| 2 | No temporal decay | yes — salience + retention | no | no | yes | partial | no | no |
| 3 | No provenance | yes — chunk_id + source_file | partial | yes | yes | yes | yes | no — baked-in |
| 4 | Flat memory | yes — KG + section\_boost | no | no | yes | yes — hypergraph | yes — dual-level | no |
| 5 | No writeback | yes — crystallize/reflect/consolidate | partial | yes | yes | yes — EvoAgent | no | no |
| 6 | Indexing delay | yes — inotifywait <1 s | `n/r` | yes | yes | `n/r` | partial — batch | no — retrain |

Sources for the non-`nox-mem` columns: mem0 [^mem0], Letta [^letta], Zep [^zep], EverOS
[^everos], LightRAG [^lightrag], MeMo [^memo].

---

# Moved 2026-09-11 — §5–§7 length pass for the arXiv appeal

The blocks below were relocated verbatim from the main paper. Nothing was deleted:
each block is either a product- or cost-comparison surface, a derivation whose result
is stated in the main text, an aborted run with no result, a restatement of limitations
that §7 already carries, or an appendix.

---

## §5.4 — F_MH paradox derivation

### 5.4 EverMemBench F_MH paradox — resolved

The triangulation of three independent multi-hop measurements forces a reframing of the EverMemBench F_MH absolute number:

| Benchmark | Multi-hop metric | nox-mem score | Conventional reference readers | Published SOTA (split noted) | Verdict |
|---|---|---:|---:|---:|---|
| **MuSiQue-Ans dev** | answer F1 (multi-hop decomposable) | **58.62%** | 35.80% (IRCoT) – 49.70% (EX(SA)) | 69.20% (Beam Retrieval, *test*) | +8.92 pp vs EX(SA); **−10.58 pp vs SOTA** |
| **HotPotQA dev distractor** | answer F1 (multi-hop bridge) | **73.37%** | 65–72% (DPR+FiD) | 85.04% (Beam Retrieval, *blind test*) | above DPR+FiD; **−11.67 pp vs SOTA** |
| **LoCoMo dev** | retrieval@10 strict | **74.52%** | 66.88% (Mem0 answer-F1, different metric) | **retrieval ceiling; not comparable to Mem0 F1** |
| **LoCoMo dev (F1 push)** | F1 (verbosity-sensitive) | 51.85% | 66.88% (Mem0 SOTA) | rank-5, verbosity gap |
| **EverMemBench F_MH** | strict EM (multi-hop chain on long conv) | 3–7% (5-batch) | 18.88% (MemOS Table 4) | **−13 to −16 pp gap** |

If nox-mem's multi-hop reasoning were structurally weak, the MuSiQue and HotPotQA results would sit near the original benchmark readers rather than well above them. They do not: the pipeline composes multi-hop answers competently on both. That rules out a wholesale reasoning failure as the explanation for F_MH, which is what this argument requires. It does **not** establish that classical multi-hop is saturated for this system — the 10–12 point shortfall against Beam Retrieval says the opposite — so the contrast with EverMemBench F_MH is a contrast between *competent-with-headroom* and *3–7%*, not between *solved* and *broken*. The quantitative evidence that the F_MH track is intrinsically hard does not come from cross-metric comparison at all: it is the 18.88% strict EM that the best published system on this same track and same metric attains. The LoCoMo retrieval ceiling at 74.52% strict (82.21% multi-hop sub-track) further confirms that multi-hop retrieval over long conversations is achievable.

**The proposed explanation.** Four features of the EverMemBench task setup are candidates for the F_MH 3–7% number, and we present them as the leading account rather than an established attribution — nothing below separates a corpus effect from a system limitation, and §5.2 leaves 10–12 points of headroom on classical multi-hop:

1. **Very long conversation chains.** EverMemBench F_MH questions require composing facts across 100+ conversation turns, far longer than MuSiQue (<=4 paragraphs) or HotPotQA (2 bridge paragraphs).
2. **Strict scoring.** EverMemBench F_MH uses strict exact-match against canonical answers; minor wording variations are penalised even when the answer is correct. MuSiQue F1 and HotPotQA ans_F1 are partial-credit scores.
3. **Entity-anchor sparsity.** EverMemBench questions often lack explicit entity tokens that nox-mem's section/source-type boost framework can latch onto. The §5.1.8.3 MAP (bypass-entity) mechanism was designed specifically to address this sparsity.
4. **Memory-vs-retrieval mismatch.** EverMemBench is a *memory* benchmark with implicit world-state updates; the chunks that answer F_MH questions may not be the chunks that explicit retrieval would surface. This is the architectural distinction MemOS optimises for.

**Implication for Q3 priorities — refined by D74 (2026-05-31).** The §5.4 framing shifts Q3 retrieval-mechanism priorities: pure retrieval-stage knobs (KG, MQ, MAP) cap at ~+7.25 pp F_MH (Wave C ceiling §5.1.9). Closing the remaining EverMemBench F_MH gap requires either (a) orchestration-stage multi-round refinement matching the long-chain structure (Q3 IterB ReAct), or (b) backbone upgrade (Backbone Matrix §5.1.10: Gemini-3-flash already narrows the F_MH gap meaningfully). Both paths are now empirically validated. The §5.5 Q3 IterC mechanism-class finding confirms that not all orchestration mechanisms transfer to EverMemBench F_MH equally (parallel decomposition vs sequential refinement). The §5.5.2 Q3 IterB ReAct result (D74) goes further: on the strongest backbone (Gemini-3-flash bare), multi-round retrieve-reason loop delivers **+2.01 pp clean F_MH lift (8.03% from 6.02% bare baseline)** — exceeding the Wave A/B/C single-stage retrieval ceiling of 7.25 pp by +0.78 pp standalone. The paradox is therefore refined rather than dissolved: EverMemBench F_MH is still largely a structural property of very long conversation chains × strict scoring, but MAS orchestration adds ~+2 pp on top of the strongest backbone above the retrieval ceiling — closing the gap is no longer purely structural, it now has both a backbone path and an orchestration path.

---

---

## §5.5.8 — Wave 2 Capstone (infrastructure abort, INDETERMINATE)

#### 5.5.8 Wave 2 Capstone — D76 infrastructure abort (INDETERMINATE)

The IterB + KG + rerank composability test was dispatched on the production VPS on 2026-05-31 and aborted after 48 h of sustained CPU steal, measured at **51–97%** while the ONNX cross-encoder rerank was active. The outcome is **INDETERMINATE — the hypothesis was not testable in that environment, which is neither a negative result nor a scientific failure**; it remains scientifically open, and completing it requires a plan with a guaranteed CPU SLO. Failure timeline, attempted mitigations and the preserved branch: supplement §S5.5.8.

---

## §5.7.1–§5.7.3 — latency, cost and footprint

#### 5.7.1 Latency — sub-10 ms KG path

| Path | p50 | p95 | p99 | Notes |
|---|---:|---:|---:|---|
| **KG path (entity-walk)** | **2.9 ms** | 5.7 ms | — | SQL + regex over `kg_relations`, no LLM call; re-validated 2026-06-15, n=10 (the original run measured 2.5 ms / ~7 ms / ~14 ms) |
| Hybrid search (FTS5 + dense + RRF, no rerank) | ~940 ms | ~2,342 ms | ~2,523 ms | Gemini-embedding-001 query dominates (~800 ms) |
| Hybrid + cross-encoder rerank (MiniLM) | +3,700 ms p50 | — | — | Opt-in, exploratory mode |

The KG path is in the sub-10 ms class at 2.9 ms p50 (re-validated 2026-06-15; the original run measured 2.5 ms — see the table above). Among the systems compared here, none reports retrieval latency in this band — but the comparison is not like-for-like and we do not treat it as a measured contrast: Zep's <100 ms p50 is a vendor-published figure, not independently verified by us (§7.1), and is therefore never used as a measured operand; the 100–500 ms range cited for Mem0 Cloud and MemOS multi-service deployments comes from their own deployment documentation, not from our harness. What is ours and measured is the mechanism: nox-mem's single-process embedded architecture (better-sqlite3 + sqlite-vec in-process) eliminates network and IPC overhead entirely. **Re-validated 2026-06-15** on the 70.7k-chunk production corpus: the KG path (`/api/kg/path`, real entity pair, n=10) measured p50 = 2.9 ms / p95 = 5.7 ms, confirming the sub-10 ms class; the Gemini-embedding-dominated standard hybrid path measured p50 = 653 ms / p95 = 706 ms (n=20) — up from 529 ms as the corpus grew 69k → 70.7k chunks and reflecting Gemini API round-trip variance, which reinforces (rather than weakens) the case for the local KG path on latency-sensitive workloads.

#### 5.7.2 Cost — $0/query KG path; hybrid vs managed SaaS is list-price, not like-for-like

| Component | nox-mem | Mem0 Cloud (published pricing) | Ratio |
|---|---:|---:|---:|
| Retrieval API cost (KG path) | **$0.00** | $0.001/query (est. embedding + retrieval) | **effectively free** |
| Retrieval API cost (hybrid w/ Gemini embedding) | $0.0000015/query | ~$0.001/query (est.) | **~667× cheaper** |
| Ingest API cost (per chunk) | $0.00 (local) | varies | n/a |
| Total cost per 1M queries (hybrid) | $1.50 | $1,000 (est.) | ~667× |

The KG path achieves **$0 per query** because the entity-walk uses only local SQL + regex with no LLM call (re-confirmed 2026-06-15). The hybrid path costs **$0.0000015/query** (gemini-embedding-001 at $0.15/1M input tokens — a Feb-2026 increase from $0.13/1M — × ~10 tokens/query). Against an *estimated* Mem0 Cloud per-query rate of ~$0.001 this is **~667× cheaper** (revised down from the 769× figure as Gemini embedding pricing rose). We lead with the unconditional claim — **$0/query KG path and zero marginal retrieval cost** — and treat the multiplier as secondary: Mem0 is sold as a subscription (free 1K calls/month, then $19–$249/month) with no published per-call overage, so the denominator is an explicit modeling assumption, not a quoted price.

#### 5.7.3 Footprint — 399 MB RSS, single-process, self-hosted

| Scaling | Idle RSS | 10× concurrent | Notes |
|---|---:|---:|---|
| nox-mem-api process | **399 MB** | +15 MB (= ~414 MB) | better-sqlite3 + sqlite-vec single-process |
| Scaling pattern | flat | quasi-flat | No per-request memory blow-up |

Self-hosted single-process means no multi-container orchestration, no Postgres/Redis/Chroma sidecars, no per-tenant container overhead. The 399 MB idle footprint runs on a $5/month VPS tier. Mem0 / Zep / Letta canonical deployments require >=3 services (API + DB + vector store) with combined RSS typically in the 1.5–3 GB range.

---

## §5.8.5–§5.8.6 — scope of claims and open work

#### 5.8.5 Honest scope of EverMemBench, LoCoMo, and classical-QA claims

- **EverMemBench Phase D headline (+2.95 pp vs MemOS Gemini)** is a modest win; the structural differentiator is the Memory Awareness composite, consistently strong across all backbones.
- **EverMemBench Phase H v2 headline (+9.13 pp vs MemOS GPT-4.1-mini)** is real and CI-verified, but the absolute score (51.68%) is not high — MemOS itself is only 42.55%. GPT-4.1-mini is the only tested backbone where all memory systems gain vs Full Context.
- **EverMemBench Backbone Matrix (Gemini-3-flash): +20.73 pp Overall / +32.74 pp MA composite** is the strongest cross-system claim in the paper. The lift is the multiplicative interaction of nox-mem's V10 retrieval stack and frontier-tier reasoning, not exclusively backbone-driven (§5.1.10).
- **MuSiQue-Ans dev answer F1 58.62%** (§5.2.1) and **HotPotQA distractor dev answer F1 73.37%** (§5.2.2) sit above the specialized readers these datasets are conventionally compared against (IRCoT, EX(SA), DPR+FiD) and roughly 10–12 points below current published SOTA (Beam Retrieval), without specialized fine-tuning. This bounds the architecture's multi-hop reasoning as competent rather than state-of-the-art, and is the sense in which §5.4 uses it.
- **LoCoMo retrieval@10 strict 74.52%** (§5.3) above Mem0 SOTA F1 66.88% is the retrieval ceiling on LoCoMo; the F1 push of 51.85% is rank-5 (above Zep / LangMem, below Mem0 SOTA 66.88%) due to a verbosity gap (§5.3.2). Path to >=55% requires orchestration (§5.5).
- **KG path, MAP, MQ, adaptive classifier, and Q3 IterC** are opt-in features, not defaults. Each addresses a known structural gap; combined effects measured in Wave B/C (§5.1.9).
- The Unicode-aware FTS5 sanitize fix is a prerequisite for all scores reported here; pre-fix Q2 numbers (nDCG@10 0.9126 LongMemEval) would have been reported as lower and should not be compared directly.
- **Wave 2 NO-REPLICATE findings (D75, §5.5.5):** the Lab Q1 single-stage knob lifts in §5.1.8 were measured on gpt-4.1-mini and are valid for that backbone. They do NOT transfer reliably to Gemini-3-flash (transfer rate ~0–40%). Any claim of "Wave A knob X delivers +N pp F_MH" must specify the backbone. The §5.5.4 composability matrix replaces the D74 projection with measured numbers; the original projection table is superseded and should not be cited.
- **IterB composability projection from D74 (IterB + Wave C → ~12.07% F_MH) is superseded.** The projection assumed both backbone-portability (refuted by D75) and architectural composability (refuted by adapter guard discovery in §5.5.7). The corrected empirical upper bound for measured+plausible IterB composability on Gemini-3-flash is ~8–9% F_MH (see §5.5.4 corrected table).
- **D76 capstone (§5.5.8):** the IterB + Wave C triple composability outcome is INDETERMINATE due to infrastructure abort. This is not a negative scientific result — it is an untested hypothesis. Batch 004 (n=49) is preserved but not 5-batch valid.
- **Limitations to flag (§5.8.6):** GPT-5 / Claude backbone columns are blocked by API access; the Zep <100 ms p50 claim is unverified by independent runs; the EverMemBench F_MH absolute number (3–7%) is not directly comparable to multi-hop reasoning gains on MuSiQue/HotPotQA — see §5.4 for the mechanism distinction.

#### 5.8.6 Honest limitations and open work

- **EverMemBench F_MH absolute (3–7%) gap vs MemOS Table 4 (18.88%)** remains, and the §5.4 reframing argues it is not primarily a multi-hop reasoning failure, attributing it principally to the task setup — with the difficulty of the track visible same-metric in the 18.88% that the best published system reaches on it, rather than inferred from the classical benchmarks. Closing it requires either Q3 IterB ReAct (multi-round refinement on long conversation chains, §5.5.2) or backbone upgrade (Backbone Matrix §5.1.10 shows the gap narrows with Gemini-3-flash). Retrieval-stage knobs cap at ~+7.25 pp F_MH (D69 Wave C ceiling §5.1.9) and show low backbone-portability to Gemini-3-flash (D75 §5.5.5).
- **IterB composability with Wave A/B/C knobs on Gemini-3-flash** is an open question. The D76 capstone (§5.5.8) was infrastructure-aborted before producing valid 5-batch data. The composability matrix in §5.5.4 documents this gap honestly. Completing the capstone requires dedicated CPU infrastructure.
- **LoCoMo F1 vs Mem0 SOTA 66.88%** remains open at rank-5 (51.85%). Wave C ceiling analysis (§5.1.9) indicates retrieval-stage knobs cannot close this gap; composition orchestration (Q3, §5.5) is the open path.
- **Zep <100 ms p50 claim** is published in marketing but not independently verified. nox-mem KG path p50 = 2.9 ms (§5.7) is measured on production VPS with the harness instrumented end-to-end. Comparison is fair only when both are measured under matched conditions.
- **GPT-5 / Claude columns** are blocked by API key constraints in the current eval setup. Backbone Matrix is currently three-cell (Gemini-2.5-flash, GPT-4.1-mini, Gemini-3-flash); GPT-5 and Claude entries are in the runway for Q3+ if access opens.
- **Wave A knob backbone-portability to other backbones** beyond Gemini-3-flash is unverified. The D75 ~30–40% transfer rate pattern is based on three knobs on one backbone pair. Additional backbone pairs (Claude Sonnet 4.6, GPT-5, Gemini 4) require independent re-baseline before composability projections can be made.
- **EverMind-AI / EverMemBench reference baselines** rely on MemOS Table 4 published numbers (arxiv:2602.01313); we have not re-run MemOS internally on the canonical 5-batch subset, only validated that the 5-batch sampling preserves the per-category distribution of the published numbers.

---

---

## §6.8 — operational cost per system (Table 2)

### 6.8 Autonomy quantified — operational cost per memory system

The Q4 quality comparison (§6.3 – §6.6) reports retrieval *quality* under matched corpora. Operational *cost* — services, RAM, cold start, mandatory third-party credentials, setup commands — is the second axis on which a memory system can be evaluated, and is the axis where the nox-mem Autonomy pillar [^q-a-p-pivot] is most legible. Table 2 summarizes the steady-state idle footprint of each system in its default self-host configuration.

**Table 2 — Autonomy quantified: services, RAM, cold start, mandatory keys, setup commands.** Headline: **~12× less RSS than EverOS, single process, no service stack.** Competitor numbers are *estimates* derived from each project's docker-compose defaults and documented system requirements (sources cited in the row). The nox-mem row is **[measured 2026-05-24, prod VPS, 6830 chunks live, uptime 9h28min]** via `ps -eo pid,rss,vsz,comm,args` against the production `nox-mem-api` process (single production process). See footnote [^nox-mem-rss] for full methodology including the cgroup `MemoryCurrent` vs process RSS distinction.

| System | Services | RAM idle | Cold start | Mandatory third-party keys | Setup commands | Sources |
|---|---:|---:|---:|---:|---:|---|
| **nox-mem** | **1** (SQLite file + Node process) | **~341 MB RSS** [measured 2026-05-24] | **<1 s** | **0** (offline-OK; embeddings optional) | **1** (`npm i && nox-mem reindex`) | This work; [^nox-mem-rss] |
| mem0 | 2 (Postgres + Qdrant) | ~800 MB | ~15 s | 1 (OpenAI for embeddings) | ~5 | mem0 docker-compose defaults [^mem0-stack] |
| Letta | 3 (Letta server + Postgres + OpenAI) | ~1.5 GB | ~30 s | 1 (OpenAI) | ~8 | Letta self-host guide [^letta-stack] |
| Zep OSS | 2 (Zep + Postgres; 3 with the local embedder) | ~1.2 GB | ~30 s | **1 mandatory** (a paid LLM key — OpenAI *or* Anthropic; the server aborts at startup without it) | ~6 | Zep v0.27.2 source [^zep-stack] |
| EverOS / EverMind-AI | **5** (MongoDB + Elasticsearch + Milvus + Redis + Postgres) | **~4 GB+** | **~60 s** | 2–3 (LLM + embedding + optional reranker) | ~15+ | EverMind-AI docker-compose [^everos-stack] |
| LightRAG | 2 (Neo4j + vector DB) | ~1 GB | ~20 s | 1 (LLM provider for KG extraction) | ~6 | LightRAG repo defaults [^lightrag-stack] |

**Reading the table.** Three rows of the cost matrix translate directly into Autonomy:

1. **Services column.** Every additional service is an additional failure mode, an additional security-patching surface, and an additional vendor that must be available on the day a user spins up the system. nox-mem ships as a single Node process operating on a single SQLite file; the only durable on-disk artifact is `nox-mem.db`. mem0/Zep/Letta/LightRAG each require >=1 database container and at least one external LLM/embedding provider. EverOS requires five containers, three of which are heavyweight infrastructure (MongoDB, Elasticsearch, Milvus). The single-service property is what makes "open `nox-mem.db` in `sqlite3` and inspect everything" a literal operation, not a euphemism.

2. **Mandatory third-party keys column.** A system that requires an OpenAI key by default is not autonomous regardless of license — the user is dependent on one specific vendor's pricing, rate limits, and terms of service. nox-mem treats embeddings as optional (FTS5-only retrieval is a valid degraded mode; §4) and is provider-agnostic when embeddings are enabled (Gemini default, Ollama-local feasible — §7.1 L2). Zep requires a paid LLM key of one of two vendors (OpenAI by default, Anthropic selectable) and refuses to start without it; what is *not* vendor-locked in Zep is the embedder, which can run keyless against its own local embedding service at the cost of a third container ([^zep-stack]). Letta documents OpenAI as its default provider.

3. **Cold start column.** A `<1s` cold start is what makes self-host *try-before-deciding* — the user can `npm i`, run one command, see results, and decide. A `~60s` cold start with five containers is what makes EverOS effectively a "build a small team to evaluate" decision, not an individual decision.

**Caveat — RAM measurement methodology.** The competitor RAM figures are *idle* (i.e., process started, no queries served, no ingestion in progress) and are *estimates* read from each project's documented system requirements and `docker stats` defaults in the published docker-compose files. They are not from a head-to-head benchmark on a single host. A side-by-side measurement on a controlled 4-vCPU / 8-GB host is a §7.2 future-work item (F-cost-bench). The nox-mem `~341 MB RSS` figure is **measured** on the production VPS via `ps -eo pid,rss,vsz,comm,args` (single production process, uptime 9h28min, 6830 chunks live); see footnote [^nox-mem-rss] for full methodology including the cgroup `MemoryCurrent` vs process RSS distinction.

---

## Appendix A — Knowledge Graph v2

## Appendix A. Knowledge Graph v2

### A.1 Entity Extraction

**v1 (Regex-based)**: Used hardcoded regular expressions for 3 entity types (person, project, agent) with a static alias map for name normalization. Limited to predefined names, producing 26 entities.

**v2 (LLM-powered)**: Uses Ollama llama3.2:3b with a structured extraction prompt. Each chunk is processed with temperature 0.1 for deterministic output. The LLM returns JSON with entities (name + type) and relations (source + relation + target).

Extraction results after processing 866 chunks:

| Metric | Regex v1 | LLM v2 | Improvement |
|--------|----------|--------|-------------|
| Entities | 26 | 384 | 14.8x |
| Relations | 59 | 529 | 9.0x |
| Entity Types | 3 | 11 | 3.7x |

**Entity Type Distribution:**

| Type | Count | Description |
|------|-------|-------------|
| project | 109 | Software projects, products, repos |
| tool | 67 | Libraries, frameworks, CLI tools |
| concept | 54 | Abstract ideas, patterns, methodologies |
| person | 53 | Team members, contacts, stakeholders |
| organization | 50 | Companies, teams, departments |
| agent | 45 | AI agents in the fleet |
| location | 2 | Geographic references |
| other | 4 | Device, currency, date, computer |

### A.2 Temporal Decay and TTL

Relations have a 90-day time-to-live (TTL) from creation. The confidence decay mechanism operates as follows:

1. Relations start with confidence 0.8 (extracted) or 0.9 (confirmed)
2. Every 30 days without re-confirmation, confidence drops by 0.1
3. Relations below 0.3 confidence receive accelerated 7-day expiry
4. Expired relations are deleted during `kg-prune` execution
5. Re-confirmation (observing the same relation in new chunks) resets confidence to 0.9 and extends TTL by 90 days

This mechanism ensures the knowledge graph naturally forgets stale information while reinforcing actively observed patterns.

### A.3 Decision Versioning

Architectural decisions are tracked with full version history in the `decision_versions` table. Each decision has a unique key (e.g., `dedup-strategy`, `fallback-chain`) and supports:

- Version chains with supersession tracking
- Authorship attribution
- Source file provenance
- Current vs. historical querying

10 decisions are currently tracked, covering API key management, LLM fallback chains, embedding model selection, agent isolation strategy, and synchronization schedules.

### A.4 Graph Traversal

The `findPath()` function implements BFS (Breadth-First Search) to discover shortest paths between any two entities. This enables queries like "How is [person] connected to nox-mem?" which traverses person → project → tool → agent relationships. Maximum depth is configurable (default: 4 hops).

---

---

## Appendix B — Cross-Agent Intelligence

## Appendix B. Cross-Agent Intelligence

### B.1 Agent Expertise Profiling

Each agent's memory is analyzed to determine its unique expertise based on chunk type distribution. The dominant chunk type determines the agent's strength category:

- **daily** → "Daily operations & activity logging"
- **team** → "Team coordination & shared knowledge"
- **decision** → "Decision tracking & rationale"
- **lesson** → "Lessons learned & pattern recognition"

Profiles include chunk counts, type breakdowns, top topics (via FTS5 term frequency), and last activity dates.

### B.2 Knowledge Sharing

The `pullInsightsFrom()` function enables any agent to query lessons and decisions from other agents without direct database access. This creates a knowledge transfer mechanism where, for example, Cipher (Security) can learn from Forge's (Code Reviewer) past code review decisions.

`pullAllInsights()` aggregates insights across all agents, sorted by date, providing a fleet-wide learning feed.

### B.3 Cross-Agent Knowledge Graph Merge

`mergeCrossKnowledgeGraphs()` scans all agent databases for kg_entities and kg_relations tables, merging them into a unified entity view. Entities are matched by type + lowercase name. The output shows which entities are known to which agents and their combined mention counts, enabling identification of shared knowledge vs. agent-specific expertise.

---

---

## Table 2 sources (accompanies §6.8)

### Autonomy table (Table 2) sources

[^nox-mem-rss]: The `~341 MB RSS` figure for nox-mem in Table 2 is **measured 2026-05-24** on the production VPS (single production process, uptime 9h28min, 6830 chunks live, 100% vector coverage). Main process RSS = 349,276 KB via `ps -eo pid,rss,vsz,comm,args | grep dist/api-server.js`. The cgroup `MemoryCurrent` reported by `systemctl show nox-mem-api -p MemoryCurrent` is 727,064,576 bytes (~727 MB); the ~386 MB delta vs process RSS is SQLite memory-mapped I/O (chunks table, FTS5 index, vec0 index) — kernel-managed page cache, reclaimable on memory pressure, not exclusive process memory. Standard `ps`/`top` RSS is the canonical comparison metric used in Table 2 across all competitors. Original revision marked this as `~50 MB [estimated]` based on Node baseline + better-sqlite3 cache projections; the production measurement (initially denied during the first revision and granted later) replaced the estimate.

[^mem0-stack]: mem0 default self-host requires Postgres + Qdrant + an OpenAI key for embeddings (or a configured alternative provider). Counts: 2 services + 1 mandatory third-party key. Source: mem0 README and `docker-compose.yml` defaults at github.com/mem0ai/mem0.

[^letta-stack]: Letta default self-host requires the Letta server, Postgres, and an OpenAI key (or alternative LLM provider) for the agent loop. Counts: 3 components + 1 mandatory third-party key. Source: Letta self-host documentation at docs.letta.com and github.com/letta-ai/letta.


[^everos-stack]: EverMind-AI / EverOS docker-compose declares MongoDB + Elasticsearch + Milvus + Redis + Postgres = 5 services, plus 2–3 third-party API keys for LLM, embedding, and (optional) reranker. Counts confirmed against the published `docker-compose.yml` in the EverMind-AI repo **as of 2026-06-15**. ⚠️ Re-probed 2026-09-10: that file returns HTTP 404 at the repository root and the project now ships as a pip-installable local-first library (v1.3.1) — the count was correct when taken and has since expired; it is retained because the operational-footprint comparison it supports was made against that version, and silently updating it would misdate the comparison. The ~4 GB RAM-idle figure is the sum of documented minimum requirements for each service's container.

[^lightrag-stack]: LightRAG defaults to Neo4j for the knowledge graph + a vector store (Qdrant/Milvus/etc.), plus one LLM provider key for entity/relation extraction during indexing. Counts: 2 services + 1 mandatory third-party key. Source: LightRAG README at github.com/HKUDS/LightRAG.

[^q-a-p-pivot]: Q/A/P strategic pivot of 2026-05-17 — three pillars (**Q**uality, **A**utonomy, **P**roduct).

---

## §5.1.7 — cross-encoder rerank trade-off study

#### 5.1.7 EverMemBench Phase G — Cross-encoder rerank trade-off study (5-batch)

**Config:** MiniLM[^minilm]-L-6-v2 cross-encoder rerank (22M params), top_k=20 pool rescored, Gemini-2.5-flash backbone. 5-batch, n=3,121.

Cross-encoder reranking[^sbert] exposes a **4-dimensional trade-off** across retrieval workload types:

| Category type | Δ vs Phase D (no rerank) | Direction |
|---|---:|---|
| Hard-recall: F_MH (multi-hop) | **+1.61 pp** (95% CI [3.97, 9.69] — overlaps baseline) | marginal gain |
| Hard-recall: F_HL (high-level) | +2.58 pp | marginal gain |
| Hard-recall: F_TP (temporal) | +2.00 pp | marginal gain |
| Head-precision: F_SH (single-hop) | +0.40 pp | quasi-neutral |
| Head-precision: MC (multi-choice) | −2.63 pp | regression |
| Memory Awareness: MA_C | **−4.00 pp** | significant regression |
| Memory Awareness: MA_P | **−2.80 pp** | significant regression |
| Memory Awareness: MA_U | **−3.84 pp** | significant regression |
| Overall | −0.96 pp | net regression |

The F_MH gain of +1.61 pp closes only **11.7% of the MemOS F_MH gap** (Phase D baseline 5.22% → Phase G 6.83% vs MemOS 18.94%). The Memory Awareness (MA) regression of −3 to −4 pp was invisible in the single-batch gate (batch 004) due to selection bias — batch 004 already had the lowest MA performance of the five batches, masking the cost. The −0.96 pp overall regression is real across all 5 batches (2.3× smaller than the single-batch −2.24 pp estimate, but consistent in direction).

**Verdict:** REJECT as default. Ship opt-in via `--rerank` flag / `NOX_RERANKER_ENABLED=1` / `/api/answer?mode=exploratory`. Documented latency cost: +3.7 s p50. Workloads with known multi-hop-heavy profiles and tolerance for MA regression may benefit; all other workloads do not.

---

#### 5.1.8 EverMemBench Lab Q1 — Retrieval augmentation standalone knobs (5-batch)

Four standalone retrieval knobs on Gemini-2.5-flash; none significant alone. Campaign in `publication/supplement-wave2-and-cross-backbone.md` §S5.1.8.

#### 5.1.9 Wave B + Wave C composability — additive F_MH and the retrieval-stage ceiling

Wave B and Wave C compose additively on F_MH; the ceiling is the retrieval stage, not the orchestrator. Detail in `publication/supplement-wave2-and-cross-backbone.md` §S5.1.9.

---

## §5.1.10 — backbone matrix on EverMemBench (Gemini-3-flash)

#### 5.1.10 Backbone Matrix — Gemini-3-flash on EverMemBench, above the published MemOS numbers

**Config:** phaseB adapter, top_k=20, rerank OFF, Gemini-3-flash backbone (frontier reasoning tier). 5-batch n=3,121.

| Metric | nox-mem (Gemini-3-flash) | MemOS Table 4 baseline (GPT-4.1-mini col) | Δ vs MemOS | Δ vs nox-mem gpt-4.1-mini (Phase H v2) |
|---|---:|---:|---:|---:|
| **Overall** | **63.28%** | 42.55% | **+20.73 pp** | +11.60 pp |
| **MA composite** | **88.42%** | 55.68% | **+32.74 pp** | +15.08 pp |
| MA_C | ~95% | 69.90% | +25 pp class | +10 pp class |
| MA_P | ~83% | 51.99% | +31 pp class | +18 pp class |
| MA_U | ~87% | 45.15% | +42 pp class | +17 pp class |

Gemini-3-flash leads on both the Overall and Memory Awareness composite tracks. The MA composite at **+32.74 pp over the published MemOS numbers** is consistent with a structural advantage from the V10 schema's section/source-type/salience drivers when paired with a frontier-tier reasoning backbone.

⚠️ **The backbones differ, and the deltas are not SOTA claims.** The MemOS column is the published Table 4 result obtained on **GPT-4.1-mini**; our column is **Gemini-3-flash**. Beating a published number produced on a weaker backbone is a cross-backbone comparison, not a state-of-the-art result, and §5.5.4–§5.5.8 measure directly how much backbone choice alone can move these metrics (single-stage retrieval knobs transfer at only 0–40% between these two backbones). The split-matched comparison against MemOS is the GPT-4.1-mini row in §5.1.6 (+9.13 pp, 95% CI [49.88, 53.49]); that one holds the backbone fixed and is the number to cite when the question is architecture rather than backbone.

**Backbone Matrix interpretation.** The +20.73 pp Overall and +32.74 pp MA composite lifts vs gpt-4.1-mini baseline are not exclusively backbone-driven: nox-mem's V10 retrieval stack contributes ~+9.13 pp Overall and ~+25 pp MA composite at the gpt-4.1-mini tier alone (Phase H v2, §5.1.6). The incremental +11.60 pp Overall and +15.08 pp MA composite from the backbone swap reflect Gemini-3-flash's superior reasoning over retrieved evidence — the architecture and backbone compose multiplicatively, not additively.

---
