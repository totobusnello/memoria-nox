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

