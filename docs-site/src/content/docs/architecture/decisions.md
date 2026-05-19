---
title: Architectural Decisions
description: ADR-001 through ADR-008 — every major architectural pivot and its rationale.
sidebar:
  order: 4
---

Architectural Decision Records (ADRs) document every significant choice and what was explicitly rejected. Full files at [`docs/adr/`](https://github.com/totobusnello/memoria-nox/tree/main/docs/adr).

## ADR-001 — Hybrid Search Architecture

**Decision:** FTS5 BM25 + Gemini semantic embeddings + Reciprocal Rank Fusion (k=60).

**Rationale:** FTS5 provides zero-cost keyword recall with AND-strict semantics. Vector search covers semantic similarity. RRF fusion is provably better than linear combination for heterogeneous ranked lists. Neither FTS alone (nDCG=0.000 on NL queries) nor vector alone (misses keyword-exact matches) is sufficient.

**Rejected:** Linear weighted combination of BM25 and cosine scores — multiplicative boost accumulation is poison (caused incident v3.4).

---

## ADR-002 — Append-Only Audit Log

**Decision:** `ops_audit` table with DB-level triggers blocking DELETE and UPDATE of terminal rows.

**Rationale:** Destructive operations in a live memory store need an irrefutable audit trail. Application-level enforcement is insufficient — DB trigger enforcement is CWE-693 defense.

---

## ADR-003 — Shadow Discipline

**Decision:** Every ranking change ships in `NOX_SALIENCE_MODE=shadow` for ≥7 days before affecting real queries.

**Rationale:** Ranking changes are invisible bugs if shipped without baseline comparison. Shadow mode exposes scores via `/api/health.salience` for offline comparison while real retrieval stays unchanged. Validated on Fase 1.7b-b salience formula.

**Rule:** Never introduce ranking/scoring changes in a "fix" commit. Always prefix with `tune(search):` or `feat(search):`.

---

## ADR-004 — Q/A/P Pillars Pivot (D40)

**Decision:** Reorganize all roadmap work into Quality / Autonomy / Product + Lab + GTM Phase 2.

**Rationale:** Prior roadmap was feature-list driven. Q/A/P gives every sprint a strategic anchor. Quality (numbers #1) is the gating constraint for GTM Phase 2 flip.

**Tagline locked:** *"Pain-weighted hybrid memory with shadow discipline — yours by design."* (D45)

---

## ADR-005 — Data Autonomy Moat

**Decision:** Single SQLite file as the canonical store. No vendor cloud sync. Provider-agnostic embedding interface.

**Rationale:** Most memory systems force a choice: vendor cloud (convenient but locked) or self-hosted (free but poor recall). memoria-nox refuses the trade. Copy the file = copy the memory. Switch the provider = the store does not care.

**Rejected:** Postgres, vector-specific DBs (Pinecone, Weaviate), proprietary sync protocols.

---

## ADR-006 — D41 Cross-Cutting Constraints

**Decision:** All modules respect `OPENCLAW_WORKSPACE` env var. Entry point is `dist/index.js` not `cli.js`. ESM static imports hoist before body — use dynamic `await import()` for env-dependent config in async `before()`.

**Rationale:** Consolidates 6 operational lessons from incidents into codified module constraints.

---

## ADR-007 — Threat Model Quarterly Review

**Decision:** STRIDE matrix + 10 gap categories + control matrix reviewed quarterly. Stored at `docs/security/THREAT-MODEL.md`.

**Rationale:** Security posture drifts without forced review cadence. Quarterly is practical for a research-stage project; semi-annual for post-GTM.

---

## ADR-008 — Provider Abstraction Layer

**Decision:** Embedding provider is a runtime-swappable interface, not a compile-time dependency. `NOX_EMBEDDING_PROVIDER` selects Gemini / OpenAI / local at startup.

**Rationale:** Autonomy pillar requires that switching providers does not require code changes. Vendor API shapes differ — the abstraction normalizes to a `embed(texts: string[]) → Float32Array[]` interface.

**Constraint:** Provider abstraction must never introduce latency >5ms overhead on the critical path (validated in Q3 latency benchmark).
