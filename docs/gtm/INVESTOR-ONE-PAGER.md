# memoria-nox — Investor One-Pager

> **Version:** 2026-05-18 — post-D40/D41 Q/A/P pivot
> **Audience:** investors, partners, strategic decision-makers
> **Honesty convention:** [verified] = production telemetry or reproducible benchmark; [estimated] = modeled projection; [pending] = gated on future milestone

---

## One-Line Description

**memoria-nox: hybrid memory layer for AI agents — data stays yours, benchmarks are honest, shadow discipline enforced.**

Tagline: *"Pain-weighted hybrid memory with shadow discipline — yours by design."*

---

## The Problem

Every serious AI agent system eventually asks the same question: *where does memory live?* Today there are two answers, and both are traps.

**SaaS trap (memanto / Moorcheh pattern):** memory lives on someone else's server. You pay a recurring cost, your data is locked to their API, and if they shut down or raise prices, you start over. No moat — theirs.

**Runtime trap (agentmemory / iii-engine pattern):** memory lives inside a proprietary runtime. The UX is smooth, but the data is inseparable from the runtime. Switching means re-ingesting everything. The product is viral precisely because escape is painful.

Neither path delivers what developers and operators actually need: memory that is **genuinely theirs** — portable, readable with any SQLite client, provider-agnostic, provably quality-first.

There is also a third, underappreciated failure: **dishonest benchmarks.** Most memory-layer READMEs show charts with no methodology. When Nox runs against BM25 Pyserini on the same n=60 curated queries, BM25 gets nDCG@10 = 0.1475. Our hybrid gets 0.5831 (±0.0046). We publish the methodology, the harness, and the golden labels — because "honest by construction" is part of the moat.

---

## Our Solution

**memoria-nox** is a memory layer built on four non-negotiable choices:

| Choice | Implementation | Why it matters |
|---|---|---|
| **SQLite-first storage** | `nox-mem.db` — yours, portable, readable offline forever | No daemon lock-in; `sqlite3 nox-mem.db "SELECT *"` works in 2040 |
| **Hybrid retrieval** | FTS5 BM25 + Gemini 3072d dense + language-aware RRF (k=60, λ=0.7) | +68 pp vs FTS5 vanilla; 4× vs BM25 Pyserini (verified) |
| **Knowledge graph** | 15,600 entities / 21,500 relations, edge-typed, derived from chunks not parallel | No 3-way drift; KG re-derives when chunks change |
| **Shadow discipline** | Any ranking change runs ≥7 days baseline-only before going active | Enforced architectural constraint, not a guideline — blocked regressions ≥3 times in production |

The result: a system where **data autonomy, retrieval quality, and shadow discipline coexist** — something no current competitor delivers simultaneously.

---

## Architecture (High Level)

```
┌─────────────────────────────────────────────────────────┐
│                    nox-mem.db (SQLite)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  chunks      │  │  vec_chunks  │  │  kg_entities  │  │
│  │  + FTS5      │  │  (3072d)     │  │  + kg_relations│ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬────────┘  │
│         └─────────────────┼──────────────────┘           │
│                           ↓                              │
│              Hybrid RRF Fusion (k=60, λ=0.7)            │
│              + salience(recency × pain × importance)     │
└─────────────────────────────────────────────────────────┘
           ↑                              ↑
    CLI / MCP Server              HTTP API (:18802)
    (Claude Code, Codex,          (agents, dashboards,
     Cursor, any agent)            eval harness)
```

Provider abstraction (A3): swap Gemini → OpenAI / Voyage / local in one flag. Zero-vendor CI invariant runs the full suite against mocks — no API key required.

---

## Market

**Total addressable context:** every AI agent system — from personal second-brain to enterprise multi-agent pipelines — needs persistent memory. The market is not "memory SaaS"; it is the entire AI agent infrastructure layer.

**Reference anchors (estimated):**
- LangChain Memory module: millions of downstream users [estimated, based on LangChain download counts]
- mem0 (memory layer abstraction): 30,000+ GitHub stars [verified, 2026-05]
- agentmemory (iii-engine runtime): 11,300+ GitHub stars [verified, 2026-05]
- Letta (ex-MemGPT, agent runtime with memory): 12,000+ GitHub stars [verified, 2026-05]

**The gap:** no current player simultaneously offers (a) SQLite portability, (b) benchmark-honest retrieval quality, (c) IDE-native UX without runtime lock-in. That gap is the market.

**Nox's initial wedge:** developers building on Claude Code, Codex, Cursor — the 80% of serious AI dev tooling — who want memory that doesn't require trusting a third-party server or buying an entire runtime.

---

## Traction

**Production metrics (VPS Hostinger, 2026-05-18):** [verified]

| Metric | Value |
|---|---|
| Chunks in production | 69,298 (99.97% embedded, Gemini 3072d) |
| Vector coverage | 99.97% |
| KG entities / relations | 15,600 / 21,500 |
| Hybrid nDCG@10 (n=78 honest golden set) | **0.6813** |
| Gain vs paper baseline (n=60, R01c-v1.1) | +16.9% relative / +9.8 pp absolute |
| Gain vs BM25 Pyserini (same corpus) | **4.0× better** (0.5831 vs 0.1475) |
| OCR pipeline | 2,835 docs processed ($14.20 total cost) [verified] |
| Total OPEX | <$11/month all-in (Gemini embeddings + KG extraction + VPS) [verified] |
| Concurrent agents served | 6 agents sharing one canonical corpus [verified] |
| Shadow discipline enforced | ≥3 silent regressions blocked in production [verified] |

**Paper:** *"The Pain Diary and Shadow Discipline: A Memory System That Learns from Its Own Incidents"* — v1.1 (31 pages), target arXiv cs.IR submission 2026-06-02. [verified: compiled]

**GitHub:** private during open-source ramp-up [pending: public launch gate Q3 2026]

**Community:** Discord placeholder active. [pending: public]

---

## Business Model

**OSS core is the moat, not the product:**

```
Free forever (OSS, MIT license):
  nox-mem.db SQLite file
  CLI (26+ commands)
  MCP Server (16 tools)
  HTTP API
  Eval harness

Commercial layer (Nox-Supermem):
  Installer + friendly setup
  Brazilian market (Hotmart, tiers A/B/C)
  PT-BR support + documentation
  Later: international expansion
  Later (2027 H2): managed single-tenant hosting
```

**Why OSS-first is right here:** memory quality only improves with adoption data. OSS builds the corpus of community trust and real-world eval signals. Commercial layer monetizes the friction reduction (setup, support, tiers) without touching the autonomy invariant.

**Revenue path (estimated):**
- Nox-Supermem Tier A (Hotmart, Brazil): R$ 97/month [estimated]
- Tier B: R$ 297/month [estimated]
- Tier C (enterprise): negotiated [estimated]
- International SaaS horizon: 2027 H1 [pending: GTM Phase 2 gate]

---

## Competition

| Player | Stars (2026-05) | Retrieval model | Data portability | Runtime lock-in | Benchmark honesty |
|---|---|---|---|---|---|
| **nox-mem** | (OSS ramp) | Hybrid FTS5+Gemini3072d+RRF, pain-salience, KG edge-typed | ✅ SQLite file, yours | ✅ None | ✅ Methodology published |
| **mem0** | ~30k+ [verified] | Vector-first (multi-backend) | ⚠️ SaaS preferred | ⚠️ Paid tier | ❌ No public harness |
| **agentmemory** (iii-engine) | ~11.3k [verified] | BM25 + vec + KG + RRF | ❌ Runtime-bound | ❌ iii-engine | ❌ No baseline published |
| **memanto** (Moorcheh) | ~126 [verified] | Semantic, conflict detection | ❌ SaaS API | ❌ Cloud | ❌ Academic framing |
| **Letta** (ex-MemGPT) | ~12k+ [verified] | Embedding-first, hierarchical | ❌ Runtime-bound | ❌ Full runtime | ❌ |
| **gbrain** (Garry Tan) | ~16.6k [verified] | Personal brain framework | ⚠️ Local-ish | ⚠️ Personal focus | ❌ |

**The gap no one occupies:** SQLite portability + benchmark-honest quality + IDE-native UX without runtime lock-in. This is the space nox-mem is designed to own.

---

## Roadmap

**Milestones are gated on empirical measurement, not intention.**

### Q3 2026 — Quality declared + GTM Phase 2 launch [pending: gate]
- Q1: LoCoMo benchmark results published (if and only if numbers lead) [pending]
- Q2: LongMemEval results published [pending]
- Q3: Latency p95 benchmark published [pending]
- Q4: `COMPARISON.md` head-to-head (memanto + agentmemory + mem0 + Letta) published [pending: gated on Q1-Q3]
- GTM Phase 2: README hero + COMPARISON table + 30s install demo live [pending: gated on Q4]
- arXiv paper live (target 2026-06-02) [pending]

### Q4 2026 — Product breadth (Tier A IDEs) [pending]
- P1: `nox-mem answer` primitive (answer before search)
- P2: hooks auto-capture in Claude Code
- P3: temporal queries ("what did I decide about X last week?")
- P4 Tier A: Claude Code + Codex + Cursor deep integration
- P5: real-time viewer at port 18802

### 2027 H1 — Federation prototype + Nox-Supermem launch [estimated]
- A2-extended: multiple Nox instances sync via P2P mesh, no broker
- Encryption end-to-end in transport
- Nox-Supermem commercial launch (Hotmart, BR)

### 2027 H2 — API platform (autonomy-preserving) [estimated]
- Single-tenant managed hosting (your SQLite file, our ops)
- Kubernetes operator for enterprise self-host

---

## Team

**Toto Busnello** — founder, sole engineer + AI agent team lead

Operates at board/advisor/fund leader level across multiple entities:
- **Nuvini** — advisor + board member
- **FII Treviso** — entrepreneur and leader (real estate fund)
- **Fundo Exclusivo Lombardia** — investment fund leader
- **Granix** — co-founder
- **Galapagos Capital** — AI advisor + AI Committee member

Prior trajectory spans full C-level coverage (CEO, CFO, CTO, CPO, CMO) in technology and finance businesses — fluency in all functions. Now operates at capital allocation and strategic governance level.

**AI agent execution team:** Atlas, Boris, Cipher, Forge, Lex, Nox — 6 specialized agents operating in parallel over a shared canonical memory corpus (this system). The product is literally the infrastructure that makes this working model scalable.

**Paper co-author:** Toto Busnello (primary). Submission target: arXiv cs.IR 2026-06-02.

---

## The Ask

We are not raising a funding round today. The ask is **strategic partnership and leverage:**

1. **Advisor introductions** — AI infrastructure investors, OSS developer tools VCs, agent-framework leads (LangChain, Llamaindex, Claude ecosystem). Who in your network is building agent infrastructure and needs a memory layer with honest benchmarks?

2. **Early adopter / design partner signups** — Teams building multi-agent systems who want data autonomy + quality. Design partners get: direct access to roadmap decisions, early P4 IDE integration support, and co-authorship credit on any case study published.

3. **Distribution leverage** — Channels that reach serious AI engineers: technical newsletters, arXiv distribution, HN/dev.to communities, AI agent builder conferences.

4. **Strategic partnership** — If you operate an AI agent platform, fund, or infrastructure company that needs memory without vendor lock-in for your clients or portfolio companies, let's talk about a white-label or OEM arrangement preserving the autonomy invariant.

**What we will never do:** compromise data autonomy for revenue, fake a benchmark number, or ship a ranking change without shadow discipline. These are not aspirational values — they are enforced constraints that define the product. Partners who share these values will find us exceptionally reliable; partners who need marketing-first will find us inflexible.

---

## Contact

**Toto Busnello**
Email: lab@nuvini.com.br
GitHub: github.com/totobusnello/memoria-nox [pending: public launch]
Paper: `paper/publication/latex/paper.pdf` (v1.1, compiled)

---

*One-pager version: 2026-05-18. Numbers [verified] sourced from production telemetry and reproducible eval harness. Numbers [estimated] are modeled projections. Numbers [pending] are gated on future milestones explicitly named above.*
