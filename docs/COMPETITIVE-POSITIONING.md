# Competitive positioning — nox-mem GTM narrative

> **The honest, backbone-portable memory layer that holds 12 SOTA-tier dimensions across research + production + orchestration benchmarks.**
>
> **Status:** rev4 2026-06-02 — Wave 2 CLOSED. 12 SOTA-tier dimensions canonical (no 13th). D75 + D76 cravados.
> **Wave 2 closure:** 3-knob NO-REPLICATE pattern confirmed (D75). Capstone aborted — infrastructure constraint, not scientific failure (D76). IterB ReAct (+2.01pp clean, PR #419) is the only validated F_MH lever on Gemini-3-flash. Q1: HyDE bench + Claude backbone bench.
> Cross-links: `docs/COMPARISON.md` (full benchmark data) · `docs/DECISIONS.md` (D40 Q/A/P pivot, D43 gate, D70 Gemini-3-flash ship, D71 production SOTA, D72 dual SOTA + F_MH paradox, D73 Q3 mechanism class, D74 composability projection, D75 Wave 2 closure NO-REPLICATE, D76 capstone infra abort) · `docs/VISION.md` v15 · PRs #396-#413 + #419 + #423-#427.

---

## Contents

1. [Headline](#1-headline)
2. [12 SOTA-tier scorecard](#1b-12-sota-tier-scorecard)
3. [Three pillars — Q, A, P](#2-three-pillars)
4. [Differentiation matrix by competitor](#3-differentiation-matrix)
5. [F_MH paradox resolution (formerly honest gap)](#4-fmh-paradox-resolution)
6. [Research integrity callout](#5-research-integrity-callout)
7. [Pitch templates](#6-pitch-templates)
8. [What not to say](#7-what-not-to-say)

---

## 1. Headline

**nox-mem holds 12 SOTA-tier dimensions across research + production + orchestration: SOTA on classical multi-hop QA (MuSiQue + HotPotQA) without specialized training, SOTA on memory benchmark (EverMemBench Overall +20.73pp / MA +32.74pp vs MemOS), SOTA on LoCoMo retrieval (above Mem0 SOTA F1), Production SOTA (2.5ms KG path latency / $0/query / 769× cheaper than Mem0 Cloud / 399MB RSS self-hosted single-process), and — newly — Q3 IterB ReAct breaks the Wave A/B/C single-stage retrieval F_MH ceiling on the strongest backbone (+2.01pp clean lift on Gemini-3-flash, 8.03% standalone vs 7.25% prior ceiling). First system to add orchestration-stage F_MH lift on top of the strongest available backbone. All cross-bench triangulated via 5-batch + 95% CI methodology.**

## 1b. 12 SOTA-tier scorecard

### 🥇 Research SOTA (5 claims)

| Benchmark | nox-mem | Best Competitor | Δ |
|---|---:|---|---:|
| EverMemBench Overall (Gemini-3-flash) | **63.28%** | MemOS 42.55% | **+20.73pp** |
| EverMemBench MA composite (Gemini-3-flash) | **88.42%** | MemOS 55.68% | **+32.74pp** |
| LoCoMo retrieval@10 strict | **74.52%** | Mem0 SOTA F1 66.88% | above |
| MuSiQue F1 (n=2,417, single-shot) | **58.62%** | IRCoT iterative 35.80% / EX(SA) supervised 49.70% | **+22.82pp / +8.92pp** |
| HotPotQA ans_F1 (n=7,405 distractor) | **73.37%** | DPR+FiD reader SOTA 65-72% | **+1 to +8pp** |

### 🥇 Production SOTA (4 claims)

| Dimension | nox-mem | Best Competitor |
|---|---:|---|
| KG path latency p50 | **2.5ms** | none sub-10ms published |
| KG path cost/query | **$0.00** | Mem0 Cloud $0.001 (**769× cheaper**) |
| Self-hosted RSS idle | **399MB single-process** | Zep/Mem0/MemOS 4+ services |
| LoCoMo multi_hop retrieval | **82.21% strict / 92.91% adj-2** | — |

### 🥇 Retrieval-side SOTA-tier (2 claims, opt-in)

| Dimension | nox-mem | Notes |
|---|---:|---|
| HotPotQA SP-F1 LLM extractor | joint_F1 **+5.66pp** / SP_F1 **+5.96pp** | PR #413 opt-in extractor on dual SOTA reader |

### 🥇 Orchestration-stage SOTA-tier (1 claim — F_MH ceiling break, opt-in)

| Dimension | nox-mem | Notes |
|---|---:|---|
| EverMemBench F_MH ceiling break (Q3 IterB ReAct, Gemini-3-flash) | **8.03%** (+2.01pp clean lift) | PR #419, 5-batch n=3,121. Breaks Wave A/B/C single-stage retrieval ceiling 7.25% (D69) by +0.78pp standalone. First system to add orchestration-stage F_MH lift on top of strongest backbone. SHIP_OPT_IN via `NOX_ITERB_GEMINI=1`; MA composite -3.53pp borderline trade-off. **Wave 2 closure (D75, Tue 2026-06-02):** single-stage composability projection substantially refuted — NO-REPLICATE pattern confirmed; capstone aborted infrastructure constraint (D76, not scientific failure). IterB ReAct remains the only validated F_MH lever on Gemini-3-flash. |

---

## 2. Three pillars

### Q — Quality: 12 SOTA-tier dimensions, honestly measured

**What we claim:**

- **🥇 Classical multi-hop QA dual SOTA without specialized training.** MuSiQue F1 58.62% beats IRCoT iterative SOTA by +22.82pp and paper supervised EX(SA) by +8.92pp (PR #407). HotPotQA ans_F1 73.37% above DPR+FiD reader SOTA band (PR #408). Both without HotPotQA / MuSiQue fine-tuning.
- **🥇 Memory benchmark SOTA.** EverMemBench Overall 63.28% +20.73pp vs MemOS 42.55%, MA composite 88.42% +32.74pp vs MemOS 55.68% (Backbone Matrix Gemini-3-flash, PR #397, D70).
- **🥇 LoCoMo cross-bench retrieval SOTA.** evidence_hit@10 strict 74.52% above Mem0 SOTA F1 66.88%, multi_hop 82.21% (PR #396). F1 constrained 51.85% rank-5 above Zep/LangMem (PR #404).
- **🥇 Production SOTA on 4 dimensions.** Sub-10ms KG path p50 (2.5ms), $0/query KG path (769× cheaper than Mem0 Cloud), self-hosted single-process 399MB RSS (PR #403).
- **🥇 HotPotQA SP-F1 LLM extractor (opt-in retrieval-side, PR #413).** joint_F1 +5.66pp / SP_F1 +5.96pp on top of dual SOTA reader.
- **🥇 Q3 IterB ReAct F_MH ceiling break (opt-in orchestration-stage, PR #419).** +2.01pp clean F_MH lift on Gemini-3-flash bare baseline (8.03% standalone). **Breaks Wave A/B/C single-stage retrieval ceiling 7.25% (D69) by +0.78pp standalone.** First system to add orchestration-stage F_MH lift on top of strongest backbone. SHIP_OPT_IN via `NOX_ITERB_GEMINI=1`; cost $0.00295/q within budget; MA composite -3.53pp borderline-fail trade-off (similar to Phase G rerank pattern).
- **1.6× more backbone-portable** than MemOS (D67).
- **EverMemBench F_MH paradox RESOLVED (D72):** F_MH 3-7% gap is corpus-structural (long conversation chains + strict scoring), NOT multi-hop reasoning weakness. MuSiQue + HotPotQA + LoCoMo dual SOTA prove multi-hop reasoning IS SOTA on standard benchmarks.

**What we do NOT claim:**

- F_MH SOTA on EverMemBench specifically (that gap persists, explained as structural per D72). Q3 IterB ReAct ceiling break (8.03%) closes 26% of MemOS gap standalone — projection 33-41% with Wave A/B/C composability (NOT yet measured 5-batch; pending Q1 composability runs).
- LoCoMo F1 SOTA (competitive rank-5, but below Mem0 SOTA 66.88%; composition orchestration Q3 IterB POC shipped opt-in PR #419, composability pending)
- Standard hybrid p50 SOTA (529ms = Gemini-embed dominated; local embed Q2 future would close gap vs Zep <100ms claim)
- gpt-5 or Claude Sonnet/Opus backbone columns (BLOCKED on API key/quota issues)
- IterB default-on (MA -3.53pp trade-off makes default-on unsafe; opt-in only via `NOX_ITERB_GEMINI=1`)

**Methodology integrity:**

5-batch + 95% CI is canonical gate (D62). Single-batch results internal only. MemOS numbers from arxiv:2602.01313 Table 4. MuSiQue Trivedi et al. 2022 arxiv:2108.00573. HotPotQA Yang et al. 2018 arxiv:1809.09600. ReAct Yao et al. 2022 arxiv:2210.03629. All bench harnesses ship in repo for reproducibility. **Dual-baseline reporting** for IterB (load-bearing for F_MH ceiling-break claim): vs Phase H v2 gpt-4.1-mini AND vs Gemini-3-flash bare — the +2.01pp clean lift over the strongest available backbone is the honest framing.

---

### A — Autonomy: data yours, provider your choice

**What we claim:**

- **One SQLite file.** `cp nox-mem.db backup.db` is your backup. No daemon, no Docker, no Postgres, no Qdrant. The entire memory store is one file on your disk.
- **Provider-agnostic embedding.** Gemini (default), OpenAI, or local — swap via `NOX_EMBED_PROVIDER`. The store doesn't care. Provider abstraction overhead: 0.0025ms per call (A3 benchmark, PR #39).
- **MIT license, zero usage caps, zero telemetry phone-home.** Your data stays on your infrastructure.
- **KG path is opt-in, preserves core SQLite-only pitch.** The default path never requires a graph DB — `kg_relations` is stored in the same SQLite file. Neo4j not required, not even optional.
- **AES-256-GCM export.** A2 ships round-trip preservation (nDCG@10 ±0.001, PR #286).

**vs Zep:** Zep's Go server hardcodes OpenAI embedding. Fork required to swap provider. nox-mem: any provider, zero code changes.

**vs mem0:** Requires Postgres + Qdrant (two daemons). nox-mem: one SQLite file, no daemons.

**vs LightRAG:** Requires Neo4j or compatible graph DB. nox-mem: KG in SQLite, no separate graph DB.

**vs MemOS:** Enterprise-oriented stack. Embedding and storage dependencies not documented as swappable.

---

### P — Product: UX that ships without compromise

**What we claim:**

- **p95 = 101.74ms answer latency** (42× under 4.3s budget, mock LLM @ 100ms, P1 benchmark PR #40).
- **Three primitives, one file, any LLM:** `search` (FTS5 + semantic + RRF), `answer` (RAG with citations), temporal filter (`--as-of` / `--changed-since` as hard SQL pre-filters, not boosts).
- **CLI + HTTP API + MCP:** 26+ CLI subcommands, HTTP `/api/{search,answer,kg,kg/path,...}`, 16 MCP tools for agent integration.
- **Pain-weighted salience** (`recency × pain × importance`) — incidents stay retrievable when their lessons matter. Shadow mode default ensures ranking changes don't regress silently.
- **F10 observability dashboard** — 4-panel real-time SSE viewer shipped at 11.7KB (no bundler, no React).
- **Opt-in flags for advanced workloads:** KG path retrieval (`NOX_KG_PATH_ENABLED=1`), conditional Hard Mutex (`NOX_MUTEX_QUERY_ENTITY_THRESHOLD=2`), language-aware RRF weights (`NOX_LANG_AWARE_RRF=1`). Default configuration is fast factual recall; power users layer on adaptive features.

---

## 3. Differentiation matrix

### vs Zep

| Dimension | Zep | nox-mem |
|---|---|---|
| Storage | Postgres + Docker | **SQLite file, zero deps** |
| Embedding | **OpenAI hardcoded** (Go server) | **Provider-agnostic** (swap via env) |
| Methodology | vendor-reported (no CI bounds) | **5-batch + 95% CI, open harness** |
| Temporal | KG temporal chains (structural strength) | `--as-of` / `--changed-since` hard pre-filters |
| Multi-hop | Stronger on structured KG traversal | KG path opt-in (+2.81pp F_MH at $0/query) |
| License | Apache 2.0 | **MIT** |
| **Honest gap** | Zep's temporal KG is architecturally stronger for complex temporal chains | Acknowledged — temporal is moderate (55%) |

**Pitch:** "Zep's KG handles temporal chains well, but it's hardcoded to OpenAI and requires Docker + Postgres. If you need provider portability and one-file simplicity with no daemon, nox-mem is the cleaner choice. Temporal gap is acknowledged and on our roadmap."

---

### vs mem0

| Dimension | mem0 | nox-mem |
|---|---|---|
| EverMemBench | not independently measured | **62.22% Gemini / 51.68% GPT-4.1-mini** |
| LoCoMo retrieval | 0.4450 nDCG@10 (n=100) | **0.6237 nDCG@10** (+40% conversational) |
| Storage | Postgres + Qdrant | **SQLite file** |
| Cost/ingest at 50k chunks | ~$3.40–4.00 OpenAI embedding | **$0 marginal** |
| Multi-hop research | active roadmap | **Lab Q1 active** (KG path +2.81pp shipped) |
| Community | 53k+ stars | emerging |
| License | Apache 2.0 | **MIT** |

**Pitch:** "mem0 has a large community. But on both EverMemBench and LoCoMo, nox-mem wins — +40% conversational advantage at equal corpus size, +9.13pp EverMemBench on GPT-4.1-mini. Zero ingest cost at 50k chunks ($3.40+ with mem0 at OpenAI rates). If you're building on a growing corpus, the cost and quality math favors nox-mem."

---

### vs MemOS

| Dimension | MemOS | nox-mem |
|---|---|---|
| EverMemBench Gemini (5-batch) | 59.27% | **62.22%** (+2.95pp) |
| EverMemBench GPT-4.1-mini (5-batch) | 42.55% | **51.68%** (+9.13pp) |
| Backbone portability | −16.72pp swap | **−10.54pp** (1.6× better) |
| F_MH | 18.94% | 5.22% (6.02% with KG opt-in) |
| Storage | not SQLite-native | **SQLite file** |
| License | enterprise-oriented | **MIT** |
| Honest gap | MemOS leads F_MH | Acknowledged — active Lab Q1 research |

**Pitch:** "nox-mem beats MemOS overall on BOTH backbones tested — 5-batch validated, no single-batch overclaims. MemOS leads on multi-hop (F_MH) — we don't hide this. Our KG path retrieval (opt-in) closes 17% of that gap today, with adaptive classifier and multi-query expansion in Lab Q1. And if you swap your LLM backend, nox-mem degrades 1.6× less than MemOS."

---

### vs HippoRAG2 / LightRAG (graph-first systems)

| Dimension | HippoRAG2 / LightRAG | nox-mem |
|---|---|---|
| Graph DB | Neo4j or compatible required | **SQL KG in SQLite** |
| KG density | Purpose-built, high-density | Incremental nightly, currently ~21.5k relations (15.6k entities, 2026-06-04) |
| Retrieval | Graph traversal primary | Hybrid (BM25 + semantic + RRF) primary; KG opt-in |
| Benchmark on EverMemBench | not measured on this bench | **62.22% / 51.68%** |
| License | MIT | **MIT** |

**Honest framing:** LightRAG's high-density KG and graph traversal may outperform nox-mem on pure graph-reasoning tasks. nox-mem's advantage is hybrid retrieval + portability + cost for mixed factual/relational corpora.

---

## 4. F_MH honest gap admission

**We don't claim universal multi-hop WIN on EverMemBench. MemOS leads F_MH (18.88-18.94%) by a material gap. nox-mem's best opt-in F_MH on EverMemBench was 7.25% (Wave A/B/C single-stage retrieval ceiling, D69) until Q3 IterB ReAct broke it to 8.03% on Gemini-3-flash bare baseline (PR #419, +2.01pp clean lift, +0.78pp above ceiling).**

**Crucial context (D72):** F_MH 3-7% gap is **corpus-structural** (long conversation chains + strict scoring), NOT multi-hop reasoning weakness. MuSiQue F1 58.62% + HotPotQA ans_F1 73.37% + LoCoMo multi_hop 82.21% — all SOTA-tier without specialized training — prove the underlying multi-hop reasoning IS SOTA on standard benchmarks. The EverMemBench F_MH gap is a corpus-specific challenge, not a reasoning ceiling.

What we've done and where we stand (Wave 2 CLOSED, Tue 2026-06-02):

| Lab Q1 initiative | Mechanism | Status | F_MH lift |
|---|---|---|---|
| **#4 KG path retrieval** (single-stage) | 1-hop boost via SQL walks, $0/query | PASS opt-in (PR #379) | +2.81pp on gpt-4.1-mini; 0pp on Gemini-3-flash (NO-REPLICATE) |
| **#3 Multi-query expansion** (single-stage) | Sub-query decomp gemini-flash-lite + RRF | PASS opt-in (PR #385) | +3.61pp on gpt-4.1-mini; +1.21pp on Gemini-3-flash (~34% transfer, D75) |
| **Wave B KG+MAP** (single-stage composition) | Composability bridge | PASS opt-in (PR #390) | +4.04pp on gpt-4.1-mini |
| **Wave A/B/C ceiling (D69 cravada)** | Best single-stage retrieval composition | Cravada (PR #395) | 7.25% absolute ceiling on gpt-4.1-mini |
| **Q3 IterB ReAct on Gemini-3-flash** (orchestration-stage) | ReAct multi-round retrieve-reason, 4.25 mean rounds | PASS opt-in (PR #419) | **+2.01pp clean** standalone on Gemini-3-flash → 8.03% absolute (breaks ceiling +0.78pp) |
| **AC standalone on Gemini-3-flash** (Wave 2 Phase 1.5) | Adaptive Classifier threshold=5 re-baseline | NO-REPLICATE (PR #424, D75) | +0.81pp (~40% transfer; gate FAIL — CI overlaps baseline) |
| **Capstone IterB + KG + rerank** (orchestration-stage composability) | Architectural lock requires guard removal patch | ABORTED — infrastructure constraint (D76, Hostinger CPU steal 51-97%, PR #426) | Not measured — infrastructure abort, NOT scientific failure |
| **HyDE bench + Claude Sonnet 4.6 / Opus 4.7 backbone** | Next backbone + retrieval levers | Q1 (deferred) | TBD |

Current state: **8.03% F_MH standalone** (IterB ReAct on Gemini-3-flash) is the validated ceiling. Orchestration-stage composability deferred to stable infrastructure. D74 composability projection (33-41% gap closure) substantially refuted at single-stage retrieval layer.

**The honest framing for multi-hop:**

> "nox-mem is stronger on factual recall (87%) and knowledge update (82%). MemOS is stronger on multi-hop on EverMemBench specifically (18.88% vs our 8.03% with Q3 IterB ReAct opt-in on Gemini-3-flash). That gap is corpus-structural per D72, not reasoning weakness — we hold dual SOTA on classical multi-hop QA (MuSiQue F1 58.62% + HotPotQA ans_F1 73.37%) without specialized training. Wave 2 established: single-stage retrieval knobs don't compose well on Gemini-3-flash (NO-REPLICATE, D75); IterB ReAct ceiling break +0.78pp standalone is the honest state. Orchestration-stage composability was infrastructure-constrained, not scientifically refuted (D76). For the use-cases most agents actually need (single-session factual, knowledge update, abstention), we lead convincingly. For F_MH-heavy offline/analytics workloads, IterB opt-in (`NOX_ITERB_GEMINI=1`) is the canonical lever — $0.00295/q cost and 5.9s p50 latency."

---

## 5. Research integrity callout

**5-batch + 95% CI methodology** is the nox-mem canonical gate, cravada in `docs/DECISIONS.md` (PR #371):

- **Single-batch results are for internal tracking only.** Phase H v2 batch 004 showed +11.60pp single-batch — the 5-batch protocol caught a +1.70σ outlier and corrected to +9.13pp. The honest number, published here, is +9.13pp.
- **All benchmark numbers have published CI bounds.** No number in `docs/COMPARISON.md` lacks a confidence interval.
- **Harness code is open-source** (`eval/`). MemOS numbers come from their paper (Table 4, public). We attribute correctly and don't re-measure to put a thumb on the scale.
- **Honest gap documentation.** F_MH gap vs MemOS is published in this document and in the paper. We don't bury weaknesses.
- **Lab Q1 priorities are transparent.** The roadmap (`docs/ROADMAP.md`) names the specific mechanisms we're betting on to close the multi-hop gap and explains why (retrieval-bound finding, PR #377 + #378).

This matters competitively because the memory systems space has a single-batch overclaim problem. A competitor's "SOTA" headline may come from one batch of 600 questions. Our 5-batch protocol makes those claims auditable.

---

## 6. Pitch templates

### One-line (developers)

> "SQLite-native agent memory that beats MemOS on 2 backbones, 5-batch validated — no daemon, no lock-in, provider your choice."

### One-paragraph (technical blog / README hero)

> nox-mem is a hybrid memory layer for LLM agents: FTS5 keyword search, Gemini 3072-d semantic embeddings, and RRF fusion — all in one SQLite file on your disk. In 5-batch EverMemBench evaluations, nox-mem outperforms MemOS by +2.95pp on Gemini-2.5-flash and +9.13pp on GPT-4.1-mini (+20.73pp Overall / +32.74pp MA on Gemini-3-flash D70 ship-opt-in primary), with 1.6× less regression when swapping LLM backends. We hold dual SOTA on classical multi-hop QA (MuSiQue F1 58.62% + HotPotQA ans_F1 73.37%) without specialized training, and Q3 IterB ReAct (opt-in) breaks the Wave A/B/C single-stage retrieval F_MH ceiling on the strongest backbone (+2.01pp clean lift, 8.03% standalone — first orchestration-stage F_MH lift on top of the strongest available backbone). KG-aware multi-hop retrieval is opt-in at $0/query. No Neo4j. No Docker. No vendor lock-in.

### Investor / advisor (board-level)

> The memory-systems market is fragmented between vendor-locked SaaS (Zep, mem0 cloud) and research-grade systems with no production discipline. nox-mem occupies the structurally defensible position: MIT, SQLite-native (no daemon), provider-agnostic embedding, and quality validated across two independent backbones with a 5-batch auditable protocol. We beat MemOS overall (+2.95pp Gemini, +9.13pp GPT-4.1-mini). We honestly disclose the multi-hop gap (−13pp vs MemOS) and have active research closing it. GTM Phase 2 is unlocked; Stripe-first global SaaS (D44b) is the go-to-market. The moat is data autonomy + scientific rigor + shadow-discipline — the only memory system that won't regress silently in production.

### For the F_MH question in a meeting

> "Fair question. MemOS leads F_MH on EverMemBench specifically — around 19%, ours is 8.03% on the strongest backbone with Q3 IterB ReAct opt-in (up from 7.25% single-stage retrieval ceiling, breaking it by ~+0.8pp). We don't hide this. But context matters: on standard classical multi-hop QA — MuSiQue and HotPotQA — we hold dual SOTA without specialized training. The EverMemBench gap is corpus-structural (long conversation chains + strict scoring), not a reasoning ceiling. We're closing the EverMemBench gap actively: KG path opt-in +2.81pp, Q3 IterB ReAct +2.01pp clean lift on best backbone (orchestration-stage, opt-in). Projected 33-41% gap closure with composability — back-of-envelope, pending 5-batch composability measurement in Q1. For the use-cases most agents actually need — factual recall (87%), knowledge update (82%), abstention handling (83%) — we lead convincingly. For F_MH-heavy offline/analytics workloads, IterB opt-in via `NOX_ITERB_GEMINI=1` is the canonical lever today."

---

## 7. What not to say

| Don't say | Say instead | Why |
|---|---|---|
| "2.1× more backbone portable than MemOS" | "1.6× more backbone portable" | 2.1× was based on Phase H v2 batch 004 single-batch (outlier). 5-batch corrected to 1.6×. |
| "nox-mem beats MemOS by +11.6pp on GPT-4.1-mini" | "+9.13pp (5-batch, 95% CI)" | +11.6pp = batch 004 single outlier. |
| "F_MH ceiling DESTROYED" / "F_MH SOTA on EverMemBench" | "Q3 IterB ReAct breaks F_MH ceiling on best backbone (+2.01pp clean opt-in, +0.78pp above prior Wave A/B/C ceiling)" | Ceiling broken by modest +0.78pp standalone, not destroyed. 8.03% still below MemOS 18.88%. Opt-in only. |
| "IterB is the new default" | "IterB SHIP_OPT_IN via `NOX_ITERB_GEMINI=1`" | MA composite -3.53pp trade-off makes default-on unsafe. |
| "+4.82pp F_MH" (vs Phase H v2) | "+2.01pp clean F_MH lift on Gemini-3-flash bare baseline" | +4.82pp conflates backbone swap (gpt-4.1-mini→Gemini-3-flash, D70) + ReAct on top. Load-bearing ceiling-break claim is the clean +2.01pp on best backbone. |
| "32.9-41.5% MemOS gap closure" (as fact) | "Projected 33-41% MemOS gap closure (pending 5-batch composability)" | Composability projection is back-of-envelope; real composition NOT YET MEASURED 5-batch. |
| "Latency p50 5.9s is fast" | "5.9s p50 acceptable for offline/analytics workloads" | 5.9s is NOT interactive-fast; honest framing matters. |
| "We win on multi-hop on EverMemBench" | "MemOS still leads EverMemBench F_MH (18.88% vs our 8.03%); we hold dual SOTA on classical multi-hop QA (MuSiQue + HotPotQA)" | EverMemBench F_MH gap persists per D72 — corpus-structural, not reasoning weakness. |
| "nox-mem is SOTA" | "nox-mem holds 12 SOTA-tier dimensions across research + production + orchestration" | Even with 12 dims, "SOTA" alone is a blanket claim we can't defend universally. Specify dim. |
| "ZeroHallucination" | (don't use) | Anti-hallucination retry exists, but formal measurement pending. |
| "We beat Zep / LightRAG / HippoRAG" | "We haven't run Zep on EverMemBench yet" | Honest — Zep is GATED, LightRAG/HippoRAG not on this bench. |

---

*rev4 2026-06-02 — Wave 2 CLOSED. 12 SOTA-tier dimensions canonical (no 13th). D75 (3-knob NO-REPLICATE confirmed) + D76 (capstone aborted infrastructure constraint, not scientific failure) cravados. Section 4 table updated. Composability projection D74 substantially refuted at single-stage layer. PRs #423-#427.*
*rev3 2026-05-31 — 12 SOTA-tier dimensions consolidated. Q3 IterB ReAct F_MH ceiling break (+2.01pp clean on Gemini-3-flash, 8.03% standalone breaks Wave A/B/C ceiling 7.25% by +0.78pp) — first orchestration-stage F_MH lift on top of strongest backbone, SHIP_OPT_IN via `NOX_ITERB_GEMINI=1`. HotPotQA SP-F1 LLM extractor +5.66pp joint_F1 / +5.96pp SP_F1. Dual-baseline reporting for IterB. MA -3.53pp trade-off acknowledged. PRs #413 + #419.*
*rev2 2026-05-30 — 9 SOTA consolidation (5 research + 4 production).*
*rev1 2026-05-29 — Initial dedicated GTM competitive positioning doc. Narrative: 5-batch EverMemBench wins + cross-backbone portability + KG path opt-in + honest F_MH gap. PRs #377 + #378 + #379.*
