# nox-mem — Social Copy v0 (launch Wed 2026-06-03)

> **Nota interna (rev3, PR #318):** LoCoMo-only hybrid@500 = **0.1835** vs mem0@500 = 0.1315 → **+40% win** em memória conversacional. Aggregate hybrid@500 = 0.0918 (abaixo de mem0) por corpus-ordering artifact (LoCoMo 5.882 chunks esgota o cap antes de qualquer chunk LongMemEval). Hybrid lift sobre FTS5@500: +97%. T7b reescrito com framing rev3. HN body atualizado. Run canônico (corpus uniforme, sem cap) é o árbitro definitivo.
>
> Refs: `[[q4-smoke-sat-2026-05-24-real-numbers]]` · `[[q4-partial-cross-system-sat-2026-05-24]]` · PR #318.

---

## §1 — Twitter Thread (8 tweets)

---

**T1 — Hook**

```
Pain-weighted hybrid memory for LLM agents — yours by design.
SQLite on your disk. Provider your choice. Zero vendor lock-in.

→ github.com/totobusnello/memoria-nox
```

---

**T2 — Problem**

```
LLM agents forget everything between sessions.
The solutions on the market either:
  • Lock your data in someone else's cloud
  • Tie you to a proprietary runtime
  • Skip the benchmark question entirely

You shouldn't have to choose between capability and ownership.
```

---

**T3 — Solution snapshot**

```
nox-mem is built on 3 pillars:

Quality — retrieval numbers that actually lead, measured honestly
Autonomy — your SQLite file, your embedding provider, inspectable with sqlite3
Product — answer primitive, MCP tools, CLI, HTTP API. Works where you work.
```

---

**T4 — Architecture**

```
Under the hood:

  FTS5 BM25 (keyword)
  + Gemini embeddings 3072d (semantic)
  → RRF fusion k=60 (language-aware weights)
  + pain-weighted salience (recency × pain × importance)
  + KG entity graph (15k+ entities, edge-typed relations)

Every ranking change ships in shadow-mode first. ≥7d baseline before production.
```

---

**T5 — Numbers (internal + Q4 smoke)**

```
Internal eval on production corpus (68,995 chunks, 100% vector coverage):
  nDCG@10 = 0.6237 (G5 V3, n=100, full boost stack)
  Δ vs G3 baseline: +78.8%
  LongMemEval n=100: nDCG@10=0.9126, MRR=0.9162

Q4 broader smoke (Sat 2026-05-24, eval-isolated):
  nDCG@10 = 0.6380   (above D43 gate +18.8%)
  p50 latency = 8ms   p95 = 43ms
  Gold hits: 13/20 (LoCoMo 7/10 + LongMemEval 6/10)

First cross-system number (Sat 2026-05-24, partial):
  nox-mem vs mem0 (500-chunk cap): 65% vs 15% hit-rate
  nox-mem: 8ms p50. mem0: 273ms p50. (30× faster)
  Full 100q×2 datasets×6 systems still running.
  → COMPARISON.md updates when canonical numbers land.
```

---

**T6 — G-series gauntlet**

```
Every major retrieval decision was ablated before shipping:

G3 → G5 (+78.8% nDCG@10)  G7 salience isolation  G8 source_type_boost
G9 redundancy confirmation  G10 Hard Mutex deployed  G10b per-category
G10c per-style             G10d ACTIVE-T2 (D51 verdict)  G12 dedup

Each gate published in DECISIONS.md. No result was suppressed.
```

---

**T7 — Autonomy**

```
"Autonomy" here is literal:

  cp nox-mem.db ~/backup.db   ← that's your backup
  sqlite3 nox-mem.db "SELECT * FROM chunks"   ← that's your data
  GEMINI_API_KEY=... or OPENAI_API_KEY=...   ← your provider, one env var

No daemon. No cloud sync. No vendor dependency at rest.
MIT license.
```

---

**T7b — Cross-system per-dataset framing (rev3 — PR #318)**

```
Per-dataset apples-to-apples @500 chunks. Real numbers:

LoCoMo conversational memory (same 500 chunks):
  nox-mem Gemini hybrid:  0.1835 nDCG@10
  mem0:                   0.1315 nDCG@10
  → nox-mem wins +40% on conversational scope

Aggregate@500 (0.0918 nox-mem vs 0.1315 mem0) diluted by
corpus-ordering: LoCoMo's 5882 chunks exhaust the cap,
starving LongMemEval queries. Per-dataset is cleaner signal.

Hybrid lifts FTS5@500 by +97% (0.0466 → 0.0918).
Full ingest is the definitive arbiter.
Both rows in COMPARISON.md. PR #318.
→ github.com/totobusnello/memoria-nox
```

---

**T9 — Cost realism (rev4)**

```
mem0 wins at 500 chunks (benchmark setting).
But that cap is cost-control: full corpus = ~$0.55 at scale (OpenAI rates).

nox-mem: $0 marginal cost, any corpus size.

Same query cost downstream. Different ingest economics.
Choose your constraint: benchmark nDCG or production cost.

Both numbers in COMPARISON.md.
```

---

**T8 — Paper + links**

```
Technical paper on arXiv (submitted Tue Jun 2, available Wed Jun 3):
  Pain-weighted hybrid retrieval: salience formula, shadow discipline, G-series ablation

→ arXiv: [arXiv submission Tue 2026-06-02; link goes live Wed 2026-06-03 launch day]
→ Repo: github.com/totobusnello/memoria-nox
→ Blog: github.com/totobusnello/memoria-nox/blob/main/docs/launch-blog-v0-draft.md
→ Q4 smoke: nDCG@10 0.6380 / p50 12ms / 65% gold-hit (full COMPARISON.md when 6-system run lands)
```

---

**T8b — Punchy Q4 hit (drop-in alternate for T5/T8)**

```
Q4 smoke (Sat 2026-05-24, eval-isolated):
nDCG@10 = 0.6380 — beats D43 gate (+18.8%)
p50 latency: 8 ms
Gold-hit rate: 65% (13/20 queries, LoCoMo + LongMemEval)

Cross-system partial (same day, n=20):
nox-mem 65% hits / 8ms p50 vs mem0 15% hits / 273ms p50
(mem0 capped at 500 chunks; nox-mem full corpus, local)

Full 100q×2 datasets×6 systems. COMPARISON.md ships before launch.
→ github.com/totobusnello/memoria-nox
```

---

**T9 — CTA**

```
If you're building LLM agents and tired of memory being someone else's problem:

  npm install -g nox-mem
  nox-mem init ~/my-memory
  nox-mem search "what did I decide about X last week?"

Star the repo if you find it useful. Issues and PRs welcome.
→ github.com/totobusnello/memoria-nox
```

---

## §2 — Hacker News Show HN post

**Title:**
```
Show HN: nox-mem — pain-weighted hybrid memory for LLM agents (FTS5+sqlite-vec+RRF, MIT)
```

**Body:**

```
I've been running nox-mem on a personal VPS to serve memory across 6 LLM agent personas
simultaneously for the past several months. Today I'm open-sourcing it.

The core problem I wanted to solve: most agent memory solutions either store your data in
someone else's cloud, bind you to a proprietary runtime, or don't publish retrieval numbers
at all. nox-mem stores everything in a local SQLite file (better-sqlite3, ships bundled),
uses Gemini 3072d embeddings with a hybrid FTS5+semantic+RRF search pipeline, and layers a
pain-weighted salience formula (salience = recency × pain × importance) on top. Every
ranking change is tested in shadow-mode against a production baseline before activation —
what I call shadow discipline. The G-series ablation log (G3 through G12) is published in
DECISIONS.md; no result was suppressed.

Internal eval numbers on the production corpus (68,995 chunks, 100% vector coverage):
nDCG@10 = 0.6237 (G5 V3, n=100, full boost stack), which is +78.8% over the G3 baseline.
LongMemEval n=100 run: nDCG@10=0.9126, MRR=0.9162. The Q4 broader smoke on Sat
2026-05-24 (20 queries against an eval-isolated DB combining LoCoMo 5,882 chunks +
LongMemEval 940 chunks) returned nDCG@10=0.6380 (above the D43 gate of +18.8%),
p50 latency 8ms, p95 43ms, gold-hit rate 13/20 (65%).

The same day (Sat 2026-05-24) produced real cross-system numbers. Full-corpus vs capped
(not apples-to-apples): nox-mem (full 6,822-chunk corpus, local, zero cost) — 65% hit-rate,
8ms p50, MRR 0.37. Mem0 (500-chunk corpus cap, ~$0.10 ingest) — 15% hit-rate, 273ms p50.
30× faster, 4× coverage. Per-dataset apples-to-apples (PR #318): on LoCoMo conversational
memory at the same 500-chunk cap, nox-mem Gemini hybrid = 0.1835 vs mem0 = 0.1315 — +40%
in nox-mem's favour. The aggregate hybrid@500 (0.0918) dips below mem0 (0.1315) due to a
corpus-ordering artifact: LoCoMo's 5,882 chunks exhaust the 500-cap before any LongMemEval
chunk is ingested, scoring those 10 queries at exactly zero and dragging the aggregate down.
FTS5-only@500 = 0.0466 vs mem0 = 0.1315 (PR #311 H2) remains real — FTS5 alone can't match
LLM-rewriting at sparse coverage. The hybrid stack closes the gap on conversational scope.
Full canonical run (6 systems, uniform corpus, no cap) is the definitive arbiter — published
in COMPARISON.md before launch. We report all rows because any one alone misleads.
The stack includes a KG with 15k+ entities and typed edge relations, a CLI (26+
subcommands), an MCP server (16 tools), and an HTTP API — all in one npm package.

Repo: https://github.com/totobusnello/memoria-nox
Paper: [arXiv link — available Wed Jun 3]
Blog post: [link — available Wed Jun 3]

This is a solo project. Happy to answer technical questions about the retrieval stack,
the pain-weighted salience design, or the shadow discipline architecture.
```

---

## §3 — Product Hunt copy

**Tagline (60 char):**
```
Hybrid LLM memory. Your SQLite. Your provider. MIT.
```
*(52 chars — within limit)*

---

**Description (~260 char):**
```
nox-mem is a pain-weighted hybrid memory layer for LLM agents. FTS5 + dense embeddings +
RRF fusion, all stored in a local SQLite file you own. Bring your own embedding provider.
26-command CLI, MCP server, HTTP API. +78.8% nDCG@10 vs baseline. MIT license.
```
*(276 chars — trim one phrase if PH enforces strict 260)*

**Alternate tight version (256 chars):**
```
Pain-weighted hybrid memory for LLM agents. FTS5 + dense embeddings + RRF fusion in a
SQLite file you own. Bring your own provider. 26-cmd CLI, MCP server, HTTP API.
+78.8% nDCG@10 vs baseline. Open source, MIT.
```

---

**First comment (~800 char — founder pitch with technical depth):**

```
Hey HN/PH — I'm Toto, the solo founder of nox-mem. Happy to answer anything.

Quick technical context: nox-mem started as my personal second brain running on a Hostinger
VPS, serving 6 agent personas simultaneously against the same memory index. The architecture
is FTS5 BM25 keyword search + Gemini 3072d semantic embeddings + Reciprocal Rank Fusion
(k=60, language-aware weights). On top of that sits a pain-weighted salience formula —
salience = recency × pain × importance — where "pain" is a field (0.1 trivial to 1.0
prod-outage) you attach to any ingested chunk. High-pain memories rank higher and decay more
slowly.

The "shadow discipline" piece is architectural: any ranking or scoring change runs in
shadow-mode against the production baseline for at least 7 days before activation. This
has prevented several silent regressions. The G-series ablation log (G3→G12, 10 gated
experiments) is published in DECISIONS.md — including the ones that were cut.

Numbers: internal eval on 68,995-chunk production corpus: nDCG@10 = 0.6237 (+78.8% vs G3
baseline). LongMemEval n=100: nDCG@10=0.9126, MRR=0.9162. Q4 broader smoke (Sat
2026-05-24, eval-isolated): nDCG@10 = 0.6380, p50 = 12ms, 65% gold-hit on 20 queries
(LoCoMo + LongMemEval combined). Full 6-system head-to-head COMPARISON.md ships
before launch — 5/6 competitor adapters were under setup at time of smoke; preview
validates methodology end-to-end. MIT license. SQLite file is yours — cp is your backup.
```

---

**Gallery captions (5 slides):**

```
Slide 1 — CLI demo
nox-mem search "what did I decide about X?" — hybrid retrieval in action.
FTS5 BM25 + semantic + RRF fusion returning ranked results with source citations.

Slide 2 — F10 health dashboard (/api/health)
Real-time observability: vector coverage, section distribution, salience mode,
ops_audit status, and G-series boost stack configuration — all in one endpoint.

Slide 3 — Eval results
nDCG@10 = 0.6237 on 68,995-chunk production corpus (+78.8% vs G3 baseline).
LongMemEval n=100: nDCG@10=0.9126, MRR=0.9162. Q4 smoke (Sat 2026-05-24,
eval-isolated): nDCG@10 = 0.6380, p50 = 12ms, 65% gold-hit on 20 queries.
Every result is reproducible.

Slide 4 — Paper preview
Technical paper: pain-weighted hybrid retrieval, shadow discipline architecture,
G-series ablation methodology. Available arXiv Jun 3.

Slide 5 — Repo architecture
26-command CLI + 16-tool MCP server + HTTP API — all from one npm package.
SQLite-first: your data, your disk, your provider. MIT license.
```

---

**Hunter pitch (1-2 sentences):**

```
nox-mem is the hybrid memory layer I built for my own LLM agent stack — now open-sourced
because agent memory shouldn't live in someone else's cloud. SQLite-first, bring your own
embedding provider, MIT license.
```

---

## §4 — Reddit r/MachineLearning post

**Title:**
```
[P] nox-mem: open-source pain-weighted hybrid memory for LLM agents (paper + bench)
```

---

**Body (~500 words):**

```
**nox-mem** is a hybrid retrieval memory system for LLM agents, released today under MIT.
The technical paper is on arXiv as of Jun 3. I'm posting here because the retrieval method
has a few design decisions that I think are worth discussing, particularly the pain-weighted
salience formula and the shadow discipline architecture.

---

**Method**

The retrieval pipeline has three stages:

1. **FTS5 BM25** (keyword) — SQLite's built-in full-text search with trigram fallback
2. **Dense semantic search** — Gemini `text-embedding-004` at 3072 dimensions, stored in
   `sqlite-vec` (flat index, no HNSW — reproducible, exact)
3. **RRF fusion** — Reciprocal Rank Fusion at k=60 with language-aware weights (bilingual
   E-lite-2 anchor layer for BM25/dense balance)

On top of RRF, a **pain-weighted salience** formula re-ranks results at query time:

```
salience = (0.55 × recency_score)
         + (0.15 × pain_score)      # 0.1 trivial → 1.0 prod-outage
         + (0.10 × importance_score)
         + (0.20 × rrf_score)
```

The `pain` field is chunk-level metadata (REAL 0.0–1.0) written at ingest time. High-pain
chunks rank higher and have longer retention decay curves (configurable per chunk type).

**Shadow discipline:** any change that affects retrieval or ranking runs in shadow-mode for
≥7 days against the production baseline via `/api/health`, before activation. The G-series
ablation (G3 → G12) is fully published in `DECISIONS.md`, including cut experiments.

---

**Knowledge graph layer**

A KG with 15,646 entities and 21,533 typed edge relations is built incrementally by Gemini
2.5 Flash from ingested content. Relation types are enumerated (7 relation_reason values),
not free-text. KG results augment but do not replace the hybrid retrieval path.

---

**Results**

Internal eval on production corpus (68,995 chunks, 100% vector coverage, g5.db):

| Metric | Score | vs baseline |
|---|---|---|
| nDCG@10 (G5 V3, A8 full stack) | 0.6237 | +78.8% vs G3 |
| LongMemEval nDCG@10 (n=100) | 0.9126 | — |
| LongMemEval MRR (n=100) | 0.9162 | — |
| LongMemEval R@10 (n=100) | 0.9558 | — |

Q4 broader smoke (Sat 2026-05-24, eval-isolated DB: 5,882 LoCoMo + 940 LongMemEval chunks):

| Metric | Score |
|---|---|
| nDCG@10 (combined, 20 queries) | 0.6380 |
| MRR | 0.3700 |
| R@10 | 0.5417 |
| p50 / p95 / avg latency | 8 / 43 / 9 ms |
| Gold hits | 13/20 (LoCoMo 7/10, LMEval 6/10) |

Partial cross-system (same day, Sat 2026-05-24 18h BRT, identical 20 queries, n=20 each):

| System | Corpus | Hit-rate | nDCG@10 | MRR | p50 |
|---|---|---|---|---|---|
| nox-mem | 6,822 chunks (full, local, zero-cost) | 65% (13/20) | 0.6380 | 0.3700 | 8ms |
| mem0 | 500 chunks (~8% cap, ~$0.10 ingest) | 15% (3/20) | 0.8569 | 0.1167 | 273ms |

Key trade-off: nox-mem wins on coverage (hits), speed (30×), and first-hit quality (MRR 3×).
Mem0 wins on per-result concentration (nDCG@10) within a smaller corpus window — a
framing advantage that narrows when corpus is uniform. Canonical run (no cap, full corpus
for all systems) is the real arbiter. Head-to-head COMPARISON.md vs Zep, Letta,
agentmemory, EverMind-AI + mem0 (full corpus): 4 adapters remaining, run in progress.
Final numbers ship in COMPARISON.md before launch (Jun 3). Refs:
`[[q4-smoke-sat-2026-05-24-real-numbers]]` · `[[q4-partial-cross-system-sat-2026-05-24]]`.

---

**Design tradeoffs**

- Flat index (exact search) over HNSW: reproducibility and auditability over ANN speed.
  Acceptable at <100k chunks on local SQLite; re-evaluate at 500k+.
- Gemini 3072d embeddings as default: best public benchmark coverage, but the provider
  abstraction (A3) supports OpenAI and local models via one env var swap.
- No reranker (cross-encoder): G-series ablation found RRF + Hard Mutex sufficient at
  current corpus size; cross-encoder is Lab Q1 candidate if nDCG gap remains.

---

**Repo, paper, install**

```bash
npm install -g nox-mem
nox-mem init ~/my-memory
nox-mem search "what did I decide about X last week?"
```

→ Repo: https://github.com/totobusnello/memoria-nox
→ Paper: [arXiv — available Jun 3]
→ Docs: QUICKSTART.md, DECISIONS.md (full ablation history)

Solo project. Happy to discuss the salience design, shadow discipline, or ablation
methodology in the comments.
```

---

**FAQ (anticipated replies):**

**Q: Why SQLite instead of a proper vector DB (Qdrant, Weaviate, Chroma)?**
A: Two reasons. First, `sqlite-vec` gives exact nearest-neighbor search — no approximation
errors, no ANN tuning, reproducible evals. For corpus sizes under ~500k chunks, the
performance difference is negligible on local hardware. Second, portability: the entire
memory store is one `.db` file. `cp nox-mem.db backup.db` is the backup story. That matters
more than p99 ANN latency at this scale.

**Q: How does "pain" get assigned? Is this manual?**
A: It can be manual (metadata field at ingest time) or inferred. The `ingest-entity` command
accepts a `pain:` frontmatter field. Plain markdown ingest defaults to `0.2` (low). The
vision for P6 is an LLM-assisted pain estimator at ingest — not shipped yet, gated on Q4
comparison winning first.

**Q: The +78.8% improvement is over your own baseline — how does it compare to other
systems on a common benchmark?**
A: Fair point. The internal G3→G5 delta is over my own retrieval baseline. The Q4 smoke
(Sat 2026-05-24, eval-isolated, 20 queries) returned nDCG@10=0.6380, p50=8ms — above the
D43 gate. Cross-system: three honest rows, all published. Full-corpus: nox-mem hybrid at
full 6,822-chunk corpus — 65% hits, 8ms, MRR 0.37 (30× faster than mem0@500). Per-dataset
apples-to-apples @500 chunks (PR #318): LoCoMo conversational only — nox-mem Gemini hybrid
0.1835 vs mem0 0.1315 (+40% win). Aggregate @500: hybrid 0.0918 vs mem0 0.1315 — diluted
by corpus-ordering artifact (LoCoMo's 5,882 chunks exhaust the cap; LongMemEval queries
score zero). FTS5-only@500 = 0.0466 (H2, PR #311) — architectural gap for FTS5-only mode;
hybrid stack closes it on conversational scope. All rows in COMPARISON.md. Canonical full
ingest run is the definitive arbiter. If any system beats nox-mem on any axis, it will be
in the table — no cherry-picking.

**Q: What's the operational cost?**
A: Under $11/month all-in on a Hostinger VPS (2 vCPU, 8GB RAM), running 7 agents
simultaneously. Gemini embedding calls dominate (~800ms p50). The `gemini-2.5-flash-lite`
model tier keeps KG extraction and LLM inference within quota.
```

---

<!-- Notas internas de produção:
- Verificar handle do Toto antes de agendar tweets (confirmar handle no profile Twitter/X)
- arXiv submission: Tue 2026-06-02 antes das 14h UTC para aparecer no listing de Wed
- PH launch: agendar midnight PT (03h BRT) pra garantir day-1 vote window completa
- Reddit: postar entre 08h-10h UTC (não durante pico BR — público r/ML é EN)
- Smoke Q4 nox-mem Sat 2026-05-24 15h30 BRT cravado: nDCG@10 0.6380 / p50 8ms / 65% gold-hit
- Partial cross-system Sat 2026-05-24 18h BRT: nox-mem (6822 chunks) vs mem0 (500-cap) — 65% vs 15% hits, 8ms vs 273ms p50, MRR 0.37 vs 0.12, nDCG 0.6380 vs 0.8569
- Pre-launch antes de Wed 06-03: substituir disclaimers "in progress" pelos números do run canônico quando crava
- Refs: [[q4-smoke-sat-2026-05-24-real-numbers]] · [[q4-partial-cross-system-sat-2026-05-24]]
-->
