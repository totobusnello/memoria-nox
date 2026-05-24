# Technical Deep Dive — nox-mem

For technical podcast appearances, conference talks, and written interviews with
engineering-focused audiences. Companion to `03-elevator-pitches.md`.

References: `ARCHITECTURE.md`, `audits/`, `docs/DECISIONS.md`, `docs/ROADMAP.md`

---

## System Architecture Overview

nox-mem is a memory layer with four distinct subsystems:

### 1. Storage Layer

A single SQLite database with three extension-backed tables:

- **`chunks` + `chunks_fts`** — the primary store. Each chunk carries metadata:
  `type` (lesson, decision, person, daily, etc.), `pain` (0.1 → 1.0),
  `importance` (float), `retention_days` (typed decay schedule), `section`
  (compiled / frontmatter / timeline / NULL), `source_type`.
- **`vec_chunks` + `vec_chunk_map`** — sqlite-vec extension tables holding
  3072-dimensional Gemini embeddings. 100% coverage in production.
- **`kg_entities` + `kg_relations`** — knowledge graph extracted nightly by
  Gemini 2.5 Flash from the chunk corpus. ~402 entities, ~544 relations.

The schema is at V10 as of launch. Key evolutions:
- V8: `retention_days` — typed decay (feedback/person = NULL never-decay;
  lesson = 180d; decision/project = 365d)
- V9: `pain` REAL DEFAULT 0.2 — the severity anchor for salience
- V10: `section` + `section_boost` — entity file format awareness

### 2. Retrieval Layer (Hybrid Search)

Three independent retrieval signals fused via Reciprocal Rank Fusion (k=60):

**Signal A — BM25 / FTS5**
SQLite's built-in full-text search. Handles keyword precision — exact terms,
code identifiers, proper nouns. Sanitized with a Unicode whitelist to avoid
FTS5's AND-strict semantics zeroing out natural-language queries.

**Signal B — Gemini Semantic Embeddings**
`gemini-embedding-001` at 3072 dimensions. Handles conceptual similarity —
paraphrase, synonym, topical drift. Running on the vec_chunks table via
sqlite-vec's ANN implementation.

**Signal C — Knowledge Graph**
Multi-hop traversal over kg_entities/kg_relations. Handles questions that
require connecting two facts ("what did we decide about X that also involves Y").
Built by Gemini 2.5 Flash in nightly incremental extraction runs.

**RRF Fusion (k=60)**
Reciprocal Rank Fusion combines the three ranked lists without requiring score
normalization. k=60 was selected empirically across the G-series ablations.

### 3. Salience Layer

```
salience = recency_score × pain × importance
```

- `recency_score`: decays exponentially from the chunk's `created_at` timestamp,
  half-life parameterized by `retention_days`.
- `pain`: the ingest-time severity label (0.1 trivial → 1.0 production outage).
- `importance`: a normalized float set at ingest, independent of pain.

The salience layer runs as the final re-ranking step, after RRF fusion. It was
validated in G7 (salience isolation ablation) and confirmed to contribute
meaningfully only at corpus scale (68k+ chunks). Below ~500 chunks, the signal
is noise.

**Shadow mode:** `NOX_SALIENCE_MODE=shadow` (the default) computes salience
scores and logs them without affecting ranking. Promotion to `active` requires
≥7 days of measured improvement in `/api/health.salience`.

### 4. Interfaces

- **CLI (26+ commands):** `nox-mem search`, `ingest`, `ingest-entity`, `reindex`,
  `vectorize`, `kg-build`, `kg-extract`, `cross-search`, `reflect`, `crystallize`,
  and more. Entry point: `dist/index.js`.
- **MCP Server (16 tools):** `nox_mem_search`, `stats`, `kg_build`, `cross_search`,
  `reflect`, etc. — for LLM agent use via the Model Context Protocol.
- **HTTP API (port 18802):** `/api/{health,search,kg,kg/path,agents,cross-kg,
  reflect,procedures}` + `POST /api/crystallize`.
- **F10 Dashboard:** browser-based production health and evaluation metrics
  (PR #207). Four live phases: Prod Health · Eval Browser · Telemetry · Shadow tracker.
  Screenshots captured 2026-05-23 in `05-screenshots/` — see
  [`05-screenshots/README.md`](05-screenshots/README.md) for per-dashboard captions.

---

## Why These Design Decisions

**Why SQLite instead of a dedicated vector database?**
Three reasons. First, operational simplicity: one file, zero infrastructure,
trivially backupable with a `cp` command. Second, ownership: the user's memory
lives in a file they control. Third, correctness: sqlite-vec implements HNSW ANN
in a battle-tested extension; the failure modes are well-understood.

The ceiling is real — at ~1M chunks, WAL file growth and ANN index rebuild time
become non-trivial. That ceiling is documented, not hidden.

**Why Gemini embeddings instead of a local model?**
At 3072 dimensions, `gemini-embedding-001` outperforms the local alternatives
tested during G4-G5 ablations on the entity-eval corpus. The dependency on
Gemini's API is the primary autonomy tradeoff in the system — documented in
`docs/DECISIONS.md`. A local-embedding pathway is on the Lab roadmap (Q1 2027).

**Why RRF instead of learned fusion?**
RRF requires no training data and has no hyperparameters beyond k. Given that the
evaluation corpus (LongMemEval-style, 100 golden queries) is too small to train
a reliable fusion model without overfitting, RRF is the correct choice at this
scale. Learned fusion is a Lab Q2 item contingent on corpus growth.

**Why the Hard Mutex on hybrid boosts?**
Ablation G10 (and subsequent G10b–G10d variants) showed that stacking section
boosts and source-type boosts multiplicatively created double-counting on entity
chunks. The Hard Mutex applies only one boost per chunk, selected by priority.
Result: +2.65% MRR on the G10 eval without any retrieval quality regression.

---

## What Hurt to Discover (G-Series Ablation Journey)

The G-series is not a smooth progression. It is a record of what went wrong.

**G6 (the false regression):** An apparent -6% nDCG regression turned out to be
a database swap artifact — the eval was running against a different chunk corpus
than the baseline. The lesson: always verify the eval DB SHA and chunk count
before comparing nDCG. Four-check protocol now mandatory.

**G7 (salience is neutral at small scale):** The pain-weighted salience formula
showed no measurable effect at the 500-chunk eval corpus. It only contributes at
scale. This was the expected result — but confirming it required a dedicated
ablation, not an assumption.

**Temporal spike v1 (rollback):** PR #176 added temporal anchor inference that
self-reinforced — a query about "last week" would shift the anchor based on its
own result, creating a feedback loop. Rolled back within 6 hours. Version 2 (PR
#181) uses regex + median anchor to break the loop.

**G10d threshold selection:** Threshold=2 for the per-style Hard Mutex won, but
only because the entity count in prod (15,612) was high enough to make the
threshold meaningful. At eval corpus size (500), threshold=1 and threshold=2
were indistinguishable. Scale matters.

---

## Cross-System Benchmark (Q4 Final, 2026-05-24)

The Q4 COMPARISON run is the first full cross-system evaluation using a
FTS5-fair protocol. All systems were given the same 100 golden queries against
the same entity-eval-v2 corpus. Two systems (Zep, EverMind) could not be
evaluated under protocol constraints — see disclosure below.

### FTS5-fair vs Gemini-hybrid: what the distinction means

nox-mem reports two numbers:

**FTS5-only (0.3753)** — BM25 retrieval without Gemini embeddings. This is
the fairest comparison to systems that use keyword or BM25 search only, and
to systems whose corpus was partially ingested (corpus cap). If you are
benchmarking a new system against nox-mem, use this number as the baseline.

**Gemini hybrid (0.6380)** — Full three-layer stack: BM25 + Gemini semantic
embeddings + KG, fused via RRF. The +70% uplift over FTS5-only is entirely
driven by the Gemini dense embedding signal (confirmed in G4-G5 ablations —
ablation F showed Gemini dense was the entire driver). This number is not
directly comparable to systems that lack dense semantic retrieval.

### Results table

| System | nDCG@10 | Corpus cap | p50 lat | Ingest cost (@500 chunks) | Production cost (5k–50k typical) | Notes |
|---|---:|---:|---:|---:|---:|---|
| nox-mem (FTS5) | 0.3753 | 100% | 7–12ms | $0 | $0 | BM25-comparable baseline |
| nox-mem (hybrid) | 0.6380 | 100% | ~940ms | ~$0* | $0 | full three-layer stack (local Gemini) |
| agentmemory | 0.1376 | 20% | 14ms | $0 | $0–25 est. | corpus cap; in-dist bias likely |
| mem0 | 0.1315 | 7.3% | 263ms | ~$0.07 | $0.34–4.00 (OpenAI rates) | **cost-imposed cap; full corpus unaffordable at 5k+ chunks** |
| Letta | partial | — | 14,978ms | $0.001 | ~$0.005–0.05 | agent-loop; latency not retrieval |
| Zep | — | — | — | $0.02 est. | $0.10–1.40 (OpenAI rates) | OpenAI key required; not evaluated |
| EverMind | — | — | — | — | — | repo 404 at eval time |

*Gemini embed at current free-tier quota. Production cost estimates based on OpenAI text-embedding-3-small ($0.02/M tokens) at 1.5 tokens/chunk average.

### Corpus cap — per-dataset breakdown (PR #318 rev3)

The per-dataset apples-to-apples experiment at 500-chunk cap (PR #318) produced a nuanced result:

| System | nDCG@10 (aggregate) | nDCG@10 (LoCoMo-only) | Corpus | Mode |
|---|---:|---:|---:|---|
| **nox-mem FTS5@500** | 0.0466 | — | 500 (cap) | FTS5-only, no Gemini |
| **nox-mem Gemini hybrid@500** | 0.0918 | **0.1835** | 500 (cap) | FTS5 + Gemini + RRF |
| **mem0@500** | **0.1315** | 0.1315 | 500 (cap) | LLM rewrite + embed |

**LoCoMo conversational memory (PR #318):** nox-mem Gemini hybrid@500 = **0.1835**, mem0@500 = 0.1315 — **+40% win** for nox-mem at equal corpus size on conversational scope. This is the cleanest apples-to-apples signal at 500-chunk cap.

**Corpus-ordering artifact (aggregate):** Aggregate hybrid@500 = 0.0918 (below mem0's 0.1315). Root cause: at 500-chunk cap, LoCoMo's 5,882 chunks are ingested first and exhaust the budget entirely before any LongMemEval chunk enters the index. The 10 LongMemEval golden queries have zero relevant coverage → nDCG = 0.0 for those queries, dragging the aggregate down. This is a dataset-ordering confound, not a retrieval quality signal.

**Hybrid stack validation:** Gemini hybrid@500 lifts FTS5@500 by **+97%** (0.0466 → 0.0918 aggregate), confirming the architectural value of dense embeddings even at sparse coverage. On LoCoMo-only, the lift is from zero signal (FTS5@500 too sparse to disaggregate) to 0.1835.

**H2 finding (PR #311, maintained):** FTS5-only@500 = 0.0466 vs mem0 = 0.1315 is **architecturally real** for FTS5-only mode — LLM-rewriting semantically generalizes at sparse corpora in ways keyword search cannot. The full Gemini hybrid stack reverses this on conversational scope (+40%).

**What this means:**
- nox-mem Gemini hybrid wins on conversational memory (LoCoMo) at equal corpus size.
- LongMemEval comparison at 500-cap is confounded by corpus-ordering; deferred to full ingest.
- Full canonical ingest (uniform corpus, no cap) is the definitive per-dataset arbiter.
- Phase 2 gate uses BOTH per-dataset AND aggregate at full corpus — not any single capped row.

**Cost:** PR #318 run cost $0.003 (Gemini API, full smoke). The hybrid@500 path is viable even for cost-sensitive evaluation scenarios.

### Letta latency — architectural difference

Letta p50 = 14,978ms is not a bug. Letta is an agent-loop memory system: it
spawns an LLM reasoning pass before returning a retrieval result. This makes it
~2000× slower on p50 than nox-mem FTS5, but it is also doing more work.
Direct p50 comparison is misleading — the systems answer different architectural
questions. The right comparison is: do you need synchronous retrieval for
real-time agent use, or async memory consolidation with reasoning?

---

## Cost Analysis — Why the 500-Chunk Cap Matters

The benchmark comparison at 500-chunk cap (mem0 wins) is often cited without context. Here
is the production cost reality:

**Ingest cost by system (OpenAI text-embedding-3-small rates):**

| Corpus size | mem0 (OpenAI embeds) | nox-mem (Gemini local) | agentmemory (iii-engine) |
|---|---:|---:|---:|
| 500 chunks (benchmark) | ~$0.07 | $0 | $0–5 est. (iii-engine proprietary) |
| 5,000 chunks (typical prod) | ~$0.70 | $0 | — |
| 50,000 chunks (large prod) | ~$7.00 | $0 | — |

**The framing:** mem0's benchmark advantage at 500 chunks comes from a cost-control cap,
not production choice. Production deployments rarely live at 500-chunk cap — they grow to
5k–50k chunks organically. At 5k chunks, mem0's cost (1% overhead per ingest) becomes
material; at 50k, it becomes prohibitive ($7 per ingest, plus per-query embedding costs
on some architectures).

nox-mem's zero-cost ingest scales to any corpus size. The trade-off is architectural:
- **mem0:** wins at sparse, curated corpora (high concentration per chunk, LLM rewriting generalization)
- **nox-mem:** wins at large, growing corpora (zero marginal cost, hybrid retrieval depth)

Both results in `COMPARISON.md` are published honestly. The canonical run (full corpus, uniform
across 6 systems) will resolve the production-scale comparison. When choosing a system, weigh
both benchmark nDCG (mem0 advantage at cap) and cost envelope (nox-mem advantage at scale).

---

## Tradeoffs (Honest)

| Tradeoff | Current State | Roadmap |
|---|---|---|
| Gemini API dependency | Required for embeddings and KG extraction | Local embedding option Lab Q1 2027 |
| p50 latency ~940ms (hybrid) | Dominated by Gemini embed call (~800ms) | Batch pre-embed, cache warm path |
| p50 latency 7–12ms (FTS5-only) | No embed call; pure SQLite retrieval | — |
| Scale ceiling ~1M chunks | SQLite WAL + ANN rebuild | Sharding spec in Lab backlog |
| KG extraction quality | Gemini 2.5 Flash; incremental nightly | Cross-encoder rerank Lab Q1 |
| No multi-tenancy | Single DB, single user | Not on roadmap; design philosophy |
| **Corpus cap comparison** | LoCoMo-only: nox-mem hybrid@500 0.1835 vs mem0 0.1315 (+40% win). Aggregate@500: 0.0918 vs 0.1315 (corpus-ordering artifact). FTS5-only@500 = 0.0466 (H2: architecturally real for FTS5-only). Full canonical ingest is definitive arbiter. | Full-corpus canonical run Sun 2026-05-25 |
| Corpus cap comparison gap | Competitors evaluated at partial corpus | Lab Q1 H1/H2 experiment |

---

## What's Next (Lab Q1 Priorities)

1. **EverMemBench evaluation** — run nox-mem on the EverOS public benchmark for
   standardized comparison against EverMind and competitors.
2. **Corpus cap experiment (H1/H2)** — disambiguate the concentration paradox
   for mem0 and agentmemory under full-corpus conditions.
3. **Neural reranker** — cross-encoder re-ranking after RRF, targeting +3–8%
   nDCG on multi-hop and adversarial queries.
4. **Local embedding pathway** — vLLM-backed local model option for users who
   cannot or will not use Gemini API.
5. **Temporal reasoning (v3)** — improved date/time anchor inference beyond the
   regex+median approach in v2.

Full roadmap: `docs/ROADMAP.md`.

---

*Last updated: 2026-05-23 (rev3) · LoCoMo-only hybrid@500 +40% win (PR #318) · corpus-ordering caveat explicit · per-dataset table added · [[project-sat-2026-05-24-final-closure]]*
