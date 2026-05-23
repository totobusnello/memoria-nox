# nox-mem — Fact Sheet

**Project name:** nox-mem
**Tagline:** "Pain-weighted hybrid memory with shadow discipline — yours by design"
**Launch date:** Wednesday, 2026-06-03
**Launch channels:** arXiv preprint + GitHub public release + Product Hunt

---

## At a Glance

nox-mem is an open-source, production-grade memory layer for LLM agents. It
combines three retrieval strategies — BM25 full-text search, Gemini semantic
embeddings, and knowledge-graph traversal — fused via Reciprocal Rank Fusion.
What sets it apart is a pain-weighted salience formula: memories are ranked not
just by recency and importance but by the severity of what it cost to forget them.
Every design decision is backed by published, reproducible ablation studies.

---

## Key Facts

| Field | Value |
|---|---|
| License (code) | MIT |
| License (paper) | CC BY 4.0 |
| Language (primary) | TypeScript (Node.js 20+) |
| Language (eval harness) | Python |
| Database | SQLite + FTS5 extension + sqlite-vec |
| Embedding model | Gemini text-embedding-001 (3072 dimensions) |
| Author | Luiz Antonio (Toto) Busnello, Independent |
| Contact | lab@nuvini.com.br |
| Repository | github.com/totobusnello/memoria-nox |

---

## Technical Innovation

- **Pain-weighted salience formula:** `salience = recency × pain × importance` —
  severity score (0.1 trivial → 1.0 production outage) modulates how long a memory
  remains salient, independent of access frequency.
- **Conditional Hard Mutex on hybrid boosts:** prevents double-counting when
  section-level and source-type boosts would otherwise stack multiplicatively.
  Validated in ablation G10 through G10d.
- **Three-layer hybrid retrieval:** FTS5 BM25 → Gemini dense semantic →
  knowledge-graph entities + relations, fused with RRF (k=60).
- **Shadow-mode deployment pattern:** scoring changes run in parallel without
  affecting production ranking until validated over ≥7 days.
- **10+ pre-registered ablation studies (G3 → G10d)** published in `audits/`,
  each with runner code attached.

---

## Production Metrics (as of 2026-05-24)

| Metric | Value |
|---|---|
| Chunks in production | 68,995 |
| Vector coverage | 100% |
| Knowledge-graph entities | ~402 |
| Knowledge-graph relations | ~544 |
| HTTP API latency p50 | 7–12ms (FTS5 local) · ~940ms (with Gemini embed) |
| HTTP API latency p95 | ~2.3s |
| HTTP API latency p99 | ~2.5s |
| Eval hit-rate (entity-eval-v2, n=100) | 65% |
| Uptime | Production-stable since 2026-04 (24/7 on Hostinger VPS) |

---

## Benchmark Results — Q4 Cross-System Comparison (Sat 2026-05-24, definitive)

> **Disclosure (4/6 systems evaluated):** Zep requires an OpenAI API key that
> breaks the FTS5-fair isolation protocol; EverMind repo returned 404 at eval
> time. Full methodology in `benchmark/COMPARISON.md`.

### nDCG@10 on entity-eval-v2 (FTS5-fair protocol, n=100 golden queries)

| System | nDCG@10 | Corpus cap | p50 latency | Cost/query | Status |
|---|---:|---:|---:|---:|---|
| **nox-mem (FTS5-only)** | **0.3753** | 100% | 7–12ms | $0 | full eval |
| **nox-mem (Gemini hybrid)** | **0.6380** | 100% | ~940ms | ~$0* | full eval |
| agentmemory | 0.1376 | 20% | 14ms | $0 | partial cap |
| mem0 | 0.1315 | 7.3% | 263ms | $0.07/query | partial cap |
| Letta | partial eval | — | 14,978ms | $0.001 | agent-loop arch |
| Zep | not evaluated | — | — | $0.02 | OpenAI key req |
| EverMind | not evaluated | — | — | — | repo 404 |

*Gemini embed cost amortized at current free-tier quota.

**Interpretation notes:**
- agentmemory (20% cap) and mem0 (7.3% cap) were evaluated on a subset of the
  corpus. Concentration in the ingested subset inflates their absolute nDCG on
  in-distribution queries. The 80%/92.7% out-of-distribution gap is the open
  question (Lab Q1, hypothesis H1/H2).
- Letta's 14,978ms p50 reflects its agent-loop orchestration design, not retrieval
  latency — it is a different architectural paradigm and direct latency comparison
  is misleading.
- nox-mem FTS5-only (0.3753) is the cleanest apples-to-apples with pure BM25
  systems. Gemini hybrid (0.6380) shows the full stack advantage (+70% over FTS5).

---

## Reproducibility

- All ablation runs (G-series) have runner scripts published alongside results in `audits/`
- Eval harness is fully isolated (separate SQLite instance, never touches production DB)
- Cross-system comparison runner: `benchmark/runner.py` (reproducible by anyone)
- Paper published simultaneously on arXiv under CC BY 4.0
- Schema history documented from V1 → V10 in `docs/EVOLUTION.md`

---

## Three Strategic Pillars

1. **Quality** — Benchmark numbers first. Every claim is backed by reproducible measurement.
2. **Autonomy** — Your data, your provider, zero vendor lock-in. Runs on a single VPS with standard SQLite.
3. **Product** — UX that earns daily use. CLI (26+ commands), MCP server (16 tools), HTTP API, and dashboard.

---

*Last updated: 2026-05-24 (Sat) · Cross-system numbers definitive · [[project-sat-2026-05-24-final-closure]]*
