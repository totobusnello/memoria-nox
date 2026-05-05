# NOX-Supermem — Architecture Overview

*Standalone reference for blog posts, HN comments, recruiter intros, and dev.to articles. Full paper: arXiv.org/abs/XXXX (forthcoming 2026-06-02).*

---

NOX-Supermem is a production memory system for AI agents built on a single architectural thesis: memory is not a retrieval problem, it is an operational discipline problem. The system has run six AI personas (Atlas, Boris, Cipher, Forge, Lex, Nox) on a shared corpus for three months. Everything below is measured, not claimed.

---

## Five operational layers

### 1. Storage layer

SQLite single-file (~1 GB). 61,257 chunks of markdown, PDF, and code, each annotated with typed metadata:

- `retention_days` — typed lifetime (feedback: NULL/never-decay; decisions: 365d; daily notes: 90d)
- `pain` — incident severity signal, float in [0.1, 1.0] (0.1 = trivial note; 1.0 = prod-outage)
- `section` — structural provenance (`compiled` / `frontmatter` / `timeline`)

Single-file means atomic backup via `cp`, trivial replication, zero ops overhead. Schema is versioned v1→v12 with idempotent zero-downtime migrations.

### 2. Retrieval layer

Three-layer hybrid, not a single-vector store:

```
L1: FTS5 BM25        — lexical recall, sub-millisecond
L2: Gemini 3072-d    — semantic cosine similarity
L3: RRF k=60         — reciprocal rank fusion of L1 + L2
```

Measured nDCG@10 on 60 golden queries (3-run mean ± std):

| Approach | nDCG@10 |
|---|---|
| FTS5 vanilla (AND-strict) | 0.0123 |
| BM25 Pyserini (strong baseline) | 0.1475 |
| **nox-mem hybrid** | **0.5213 ± 0.0004** |

Hybrid is **3.5× above a strong BM25 baseline**. FTS5 alone returns near-zero on natural-language queries — structural constraint of AND-strict tokenization, not a corpus artifact.

p95 latency: under 1 second across 61K chunks on commodity CPU.

### 3. Knowledge graph layer

Automated KG with 1,107 typed relations across a closed enum of seven reasons:

```
depends_on | derived_from | opposes | extends | replaces | mentions | unknown
```

Gemini 2.5 Flash extracts SPO triples from the corpus nightly. A defensive three-path normalizer collapses free-text LLM output into the enum:

```typescript
// Path 1: direct enum match
// Path 2: 24-entry PT-BR + EN alias map
// Path 3: fallback → "unknown"
const reason = RELATION_TYPE_TO_REASON[raw.toLowerCase()] ?? "unknown";
```

Before the normalizer: 14% classified, 86% `unknown`. After: **56% classified — 4× improvement** (n=100). A closed enum without a defensive normalizer is half a feature.

Enables blast-radius queries: *what is affected by this change*, not just *does something match*.

### 4. Governance layer

Every destructive operation is wrapped by `withOpAudit()`:

```typescript
await withOpAudit(db, "reindex", async () => {
  // VACUUM INTO atomic snapshot created before this runs
  // ops_audit row written (append-only — DELETE/UPDATE blocked by trigger)
  // safeRestore() available if op crashes
});
```

- Append-only `ops_audit` table (CWE-693 enforced via DB triggers)
- Pre-op VACUUM INTO snapshot to `/var/backups/nox-mem/pre-op/` (7-day retention, 0600 ACL)
- Shadow-mode: every ranking change runs `NOX_<FEATURE>_MODE=shadow` for a minimum of seven days before activation, monitored via `/api/health` every 15 minutes
- Activation requires three independent signals: wall-clock ≥7d, healthy distribution, explicit human approval

Shadow-mode validation of salience (Phase 1.7b-b): 191 promotions, 16,608 reviews, 45,743 archives collected before activation. This is the gate, not a suggestion.

### 5. Interface layer

Three caller-agnostic interfaces over the same core:

```bash
# CLI — 26+ subcommands
nox-mem search "sqlite WAL corruption"
nox-mem ingest ./docs/
nox-mem kg-build --incremental
nox-mem reindex --dry-run   # preview JSON, no mutation
```

- **HTTP API** on port 18802: `/api/{search, health, kg, kg/path, agents, cross-kg, reflect, procedures}`
- **MCP server**: 16 tools for Claude/MCP-compatible agents
- **Opt-in telemetry** (`search_telemetry` table): nDCG/MRR tracked per query for continuous eval

---

## Ten distinctive characteristics

**Operational**
1. Single-file SQLite — atomic backup, zero infrastructure overhead
2. Schema versioned v1→v12, idempotent zero-downtime migrations
3. Append-only audit log with pre-op atomic snapshot (VACUUM INTO)
4. Shadow-mode as architectural constraint — cron-enforced, not a documented suggestion

**Retrieval and knowledge**
5. Hybrid 3-layer with RRF fusion — not a single-vector store
6. Closed-enum edge typing (7 reasons, 24-alias defensive normalize)
7. Pain-weighted salience: incident severity as a retrieval signal typed into the schema
8. Cross-agent shared corpus — 99.92% of 61,257 chunks shared across all six agents, zero federation

**Production and reproducibility**
9. Production-tested for three months with six real AI agents
10. Reproducibility-first: eval harness with 60 golden queries, public incident log, versioned schema

---

## Three novel contributions

| # | Contribution | Empirical anchor |
|---|---|---|
| **#1** | **Incident severity as retrieval signal** (`salience = recency × pain × importance`) | Q55 case study: Δ=+0.349 in tied-semantic regime; aggregate Δ=+0.0065 NOT_SIGNIFICANT — methodological contribution stands independent of retrieval result |
| **#2** | **Shadow validation as architectural constraint** (≥7d wall-clock, cron-enforced, health-endpoint observable) | Phase 1.7b-b: 7-day telemetry gate with 62,542 classified events before activation |
| **#3** | **Shared-canonical multi-agent** (one corpus, six agents, zero federation) | 61,207 / 61,257 chunks shared = 99.92%; counterfactual MemGPT/Mem0 per-agent isolation = 0% sharing |

Literature coverage: zero papers in agent memory systems to date encode **#2 and #3** as enforced architectural constraints. **#1** is a transferable methodology — any persistent memory system could adopt a severity multiplier as a typed schema field with an operational annotation pipeline.

---

## Honest gaps

- Corpus scale: 61K chunks vs ≥100K benchmarks (BEIR, MS-MARCO)
- Third-party benchmark: internal 60-query golden set, not LOCOMO or BEIR
- Pain ablation in production (salience=shadow vs salience=off head-to-head) requires two production restarts — documented as future work

The comparison table (7 architectural axes, 8 systems) is in the full paper. Nearest competitor by axis coverage: Cognee at 3/7. nox-mem: 5/7. Competitor mean: 1.6/7.

---

*Built solo by one developer in São Paulo. The incidents are in the log. The log is in the schema. The schema is in the paper.*

Full paper at arXiv.org/abs/XXXX (forthcoming 2026-06-02). Repo: github.com/totobusnello/memoria-nox
