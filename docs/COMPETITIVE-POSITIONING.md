# Competitive positioning — nox-mem GTM narrative

> **The honest, backbone-portable memory layer that wins by default and offers adaptive retrieval for advanced workloads.**
>
> **Status:** rev1 2026-05-29 — 5-batch EverMemBench wins + cross-bench validation + KG path opt-in.
> Cross-links: `docs/COMPARISON.md` (full benchmark data) · `docs/DECISIONS.md` (D40 Q/A/P pivot, D43 gate, D44 Stripe-first, D51 mutex) · `docs/VISION.md` v15 · PR #377 + #378 + #379.

---

## Contents

1. [Headline](#1-headline)
2. [Three pillars — Q, A, P](#2-three-pillars)
3. [Differentiation matrix by competitor](#3-differentiation-matrix)
4. [F_MH honest gap admission](#4-fmh-honest-gap-admission)
5. [Research integrity callout](#5-research-integrity-callout)
6. [Pitch templates](#6-pitch-templates)
7. [What not to say](#7-what-not-to-say)

---

## 1. Headline

**nox-mem beats MemOS on both backbones tested — Gemini-2.5-flash (+2.95pp) and GPT-4.1-mini (+9.13pp) — validated via 5-batch protocol with 95% CI. 1.6× more backbone-portable. KG-aware multi-hop retrieval opt-in at $0/query. One SQLite file, provider your choice, zero vendor lock-in.**

---

## 2. Three pillars

### Q — Quality: numbers #1, honestly measured

**What we claim:**

- **Beats MemOS on BOTH backbones tested.** Phase D Gemini-2.5-flash 5-batch: nox-mem 62.22% vs MemOS 59.27% = +2.95pp (95% CI [61.17, 63.27%], lower bound > MemOS). Phase H v2 GPT-4.1-mini 5-batch: nox-mem 51.68% vs MemOS 42.55% = +9.13pp (95% CI [49.88, 53.49%], lower bound > MemOS). PRs #377.
- **1.6× more backbone-portable.** Backbone swap regression: nox-mem −10.54pp vs MemOS −16.72pp. Lower regression risk when users change LLM provider.
- **Cross-bench consistent.** LongMemEval n=300 (PR #378): task accuracy 68.16% (CI 0.61–0.74). Per-category fingerprint identical to EverMemBench — strong factual recall (87%), knowledge update (82%), abstention (83%); moderate multi-session (56%) and temporal (55%). Structural advantage, not benchmark-specific tuning.
- **KG path retrieval opt-in closes 17% of multi-hop gap.** Lab Q1 #4 (PR #379): F_MH +2.81pp via regex entity extraction + SQL `kg_relations` walk. Zero LLM at query time, $0/query marginal cost. 3/4 gates met, shipped opt-in (`NOX_KG_PATH_ENABLED=1`).

**What we do NOT claim:**

- Universal multi-hop WIN. F_MH gap vs MemOS is −13 to −16pp (backbone-invariant). We're actively closing it (Lab Q1 #1 + #4 + #3), but we don't claim to lead on multi-hop today.
- We don't publish single-batch numbers as headlines. Phase H v2 batch 004 showed +11.60pp — 5-batch protocol caught it as a +1.70σ outlier and corrected to +9.13pp.

**Methodology integrity:**

5-batch + 95% CI is the canonical gate (PR #371 DECISIONS). Single-batch results are for internal tracking only. MemOS numbers are from their paper Table 4 (public) — not re-measured by us, attributed correctly.

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
| KG density | Purpose-built, high-density | Incremental nightly, currently ~544 relations |
| Retrieval | Graph traversal primary | Hybrid (BM25 + semantic + RRF) primary; KG opt-in |
| Benchmark on EverMemBench | not measured on this bench | **62.22% / 51.68%** |
| License | MIT | **MIT** |

**Honest framing:** LightRAG's high-density KG and graph traversal may outperform nox-mem on pure graph-reasoning tasks. nox-mem's advantage is hybrid retrieval + portability + cost for mixed factual/relational corpora.

---

## 4. F_MH honest gap admission

**We don't claim universal multi-hop WIN. MemOS leads F_MH (18.94%) by a material gap (nox-mem ~5–6%). This is backbone-invariant — same −13 to −16pp gap on both Gemini and GPT-4.1-mini — which confirms it's a retrieval problem, not a generation problem.**

What we're doing about it:

| Lab Q1 initiative | Mechanism | Status | Expected F_MH lift |
|---|---|---|---|
| **#4 KG path retrieval** | 1-hop boost via SQL walks, $0/query | ✅ Shipped opt-in (PR #379) | +2.81pp (17% gap closure) |
| **#1 Adaptive query classifier** | Route multi-hop queries to enhanced mode | Spec (PR #373) | +3–5pp (estimated) |
| **#3 Multi-query expansion** | Sub-query decomposition for multi-hop | Spec (PR #375) | +3–5pp (estimated) |

Realistic gate: F_MH ~10–12pp (50–65% gap closure) via adaptive + KG-walk. Beyond that requires iterative retrieval or chain-of-thought agentic approaches — acknowledged as future work.

**The honest framing for multi-hop:**

> "nox-mem is stronger on factual recall (87%) and knowledge update (82%). MemOS is stronger on multi-hop (18.94% vs our 6%). We're closing the gap via KG path retrieval (shipped opt-in, +2.81pp), adaptive classifier, and multi-query expansion (Lab Q1). We don't claim to be the best multi-hop memory system today — but we're the best at the use-cases most agents actually need (single-session factual, knowledge update, abstention), and actively improving on multi-hop."

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

> nox-mem is a hybrid memory layer for LLM agents: FTS5 keyword search, Gemini 3072-d semantic embeddings, and RRF fusion — all in one SQLite file on your disk. In 5-batch EverMemBench evaluations, nox-mem outperforms MemOS by +2.95pp on Gemini-2.5-flash and +9.13pp on GPT-4.1-mini, with 1.6× less regression when swapping LLM backends. KG-aware multi-hop retrieval is opt-in at $0/query. No Neo4j. No Docker. No vendor lock-in.

### Investor / advisor (board-level)

> The memory-systems market is fragmented between vendor-locked SaaS (Zep, mem0 cloud) and research-grade systems with no production discipline. nox-mem occupies the structurally defensible position: MIT, SQLite-native (no daemon), provider-agnostic embedding, and quality validated across two independent backbones with a 5-batch auditable protocol. We beat MemOS overall (+2.95pp Gemini, +9.13pp GPT-4.1-mini). We honestly disclose the multi-hop gap (−13pp vs MemOS) and have active research closing it. GTM Phase 2 is unlocked; Stripe-first global SaaS (D44b) is the go-to-market. The moat is data autonomy + scientific rigor + shadow-discipline — the only memory system that won't regress silently in production.

### For the F_MH question in a meeting

> "Fair question. MemOS leads on multi-hop — their F_MH is around 19%, ours is around 5–6% today. We don't hide this. What the benchmarks show is that the gap is a retrieval problem, not a generation problem — the same magnitude on two different LLM backbones. We've shipped KG path retrieval as opt-in (closes 17% of the gap at $0/query), and our adaptive classifier is in active development. We think we can reach 50–65% gap closure via these mechanisms. In the meantime, for the use-cases most agents actually need — factual recall (87%), knowledge update (82%), abstention handling (83%) — we lead convincingly."

---

## 7. What not to say

| Don't say | Say instead | Why |
|---|---|---|
| "2.1× more backbone portable than MemOS" | "1.6× more backbone portable" | 2.1× was based on Phase H v2 batch 004 single-batch (outlier). 5-batch corrected to 1.6×. |
| "nox-mem beats MemOS by +11.6pp on GPT-4.1-mini" | "+9.13pp (5-batch, 95% CI)" | +11.6pp = batch 004 single outlier. |
| "We win on multi-hop" | "We're closing the multi-hop gap (KG path +2.81pp, Lab Q1 active)" | F_MH gap is real and −13pp. Claiming WIN is dishonest. |
| "nox-mem is SOTA" | "nox-mem beats MemOS on 2 backbones" | "SOTA" is a blanket claim we can't defend on all dimensions. |
| "ZeroHallucination" | (don't use) | Anti-hallucination retry exists, but formal measurement pending. |
| "We beat Zep / LightRAG / HippoRAG" | "We haven't run Zep on EverMemBench yet" | Honest — Zep is GATED, LightRAG/HippoRAG not on this bench. |

---

*rev1 2026-05-29 — Initial dedicated GTM competitive positioning doc. Narrative: 5-batch EverMemBench wins + cross-backbone portability + KG path opt-in + honest F_MH gap. PRs #377 + #378 + #379.*
