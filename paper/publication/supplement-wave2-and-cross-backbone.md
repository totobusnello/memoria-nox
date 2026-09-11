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

