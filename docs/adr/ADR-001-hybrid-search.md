# ADR-001: Hybrid search architecture (BM25 + sqlite-vec + RRF)

Date: 2024-04-01

## Status

Accepted

## Context

nox-mem needs a retrieval architecture that satisfies two competing requirements simultaneously:

1. **Lexical precision** — exact term matches, identifiers, code snippets, proper nouns where semantic models hallucinate or drift.
2. **Semantic recall** — natural language queries where the exact wording is unknown, paraphrase queries, cross-language retrieval (PT/EN corpus).

Evaluated approaches:
- Pure BM25/FTS5: high precision on exact terms, but AND-strict semantics produces zero recall on 96% of natural language queries in this tech-mixed PT/EN corpus (confirmed via E14 eval runs 80-84, 2026-05-17).
- Pure vector (dense only): handles semantic well but silently breaks on lexical/identifier queries; hard to debug recall failures.
- Hybrid with RRF (Reciprocal Rank Fusion): combines both lists without requiring score normalization; k parameter controls the degree of smoothing.

The corpus is ~62K+ chunks (2026-05-01), bilingual PT/EN, covering agent conversations, entity files (person/project/lesson), and markdown docs. Query patterns are mixed: entity lookups, natural language questions, code/config snippets.

Measured baseline (2026-05-17): hybrid nDCG@10 = 0.699 on golden set (n=80). Pure FTS5 nDCG@10 ≈ 0.012 (near-zero; confirmed by E14 eval baseline).

## Decision

The default retrieval pipeline is **3-stage hybrid search**:

1. **FTS5 BM25** (lexical) — SQLite FTS5 with AND-strict semantics; acts as exact-term recall tier and graceful failsafe when vector service is unavailable.
2. **Gemini semantic** (`gemini-embedding-001`, 3072d) — dense vector retrieval via `sqlite-vec`; carries 100% of semantic recall in practice.
3. **RRF fusion** with **k=60**, **λ=0.7** — fuses ranked lists from both tiers without score normalization.

Parameters:
- `k=60`: standard RRF smoothing constant; prevents high-ranked-in-one-list items from dominating. Empirically stable across corpus sizes from 20K to 62K+ chunks.
- `λ=0.7`: language-aware weight introduced by E14 D-component (2026-05-17, +1.92pp). Weights BM25 vs dense based on detected query language.
- Dense pool default: 50 results pre-fusion; expand via `--pool` flag.

FTS5 AND-strict is intentional — "waking up" FTS5 via OR-fallback or stopword stripping consistently degrades ranking in this corpus (4 empirical attempts, all negative: -5.4pp to -23.6pp overall). FTS5 acts as a lexical precision tier and Gemini failure failsafe, not a recall driver.

## Consequences

- **Positive:** Covers both lexical and semantic query patterns from a single pipeline. Latency <100ms p50 (no change from single-tier). Degrades gracefully to FTS5-only if Gemini quota/outage.
- **Positive:** RRF requires no score normalization; stable across corpus size changes.
- **Negative:** Two storage layers (`chunks_fts` + `vec_chunks`) must stay in sync; `trg_chunks_delete_cascade` trigger handles cascade deletes.
- **Negative:** Dense embeddings depend on external Gemini API (SPOF mitigated by FTS5 failsafe + quota monitoring canary `*/30min`).
- **Risks:** Any modification to ranking/scoring must go through 7-day shadow mode (ADR-003) to avoid silent regressions.

## Alternatives considered

- **Pure BM25 (FTS5 only)** — rejected: 96% zero-recall on natural language queries empirically confirmed; unacceptable for production.
- **Pure vector (sqlite-vec only)** — rejected: silent recall failures on lexical/identifier queries; no graceful degradation on Gemini outage.
- **Atomic hybrid CTE (single query)** — rejected: latency currently <100ms (within SLA); marginal gain does not justify complexity. Revisit if p95 >500ms sustained (DECISIONS.md §1 item 13).
- **Postgres / PGLite** — rejected: adds daemon + autovacuum + backup complexity; SQLite WAL <5ms sufficient for current scale (DECISIONS.md §1 item 10).
- **Memgraph / Neo4j** — rejected: over-engineering for ~400 entities; SQLite + sqlite-vec covers the graph layer (DECISIONS.md §1 item 9).
- **Cross-encoder reranker (Q5/D01)** — deferred: latency +200ms exceeds SLA, requires llama-server (2-3GB RAM on VPS), no eval baseline yet (DECISIONS.md §2).

## Related

- Supersedes: none
- References:
  - `docs/DECISIONS.md` §3.Search & Ranking items 1, 3 and §2 (Q5 deferred)
  - `docs/DECISIONS.md` D39 (FTS5 silent design accepted after 4 attempts)
  - `feedback_shadow_mode_for_ranking_changes.md`
  - E14 eval runs (2026-05-17): `specs/2026-05-10-E14-retrieval-evolution.md`
