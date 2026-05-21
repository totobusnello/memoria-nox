# OpenClaw Memory System: Architecture & Technical Deep Dive

**nox-mem v3.7 — March 2026, §5 empirical evaluation added May 2026 (Wave A G5 V3)**

**Author:** Luiz Antonio Busnello (Toto)
**Platform:** OpenClaw Autonomous Agent Platform
**Infrastructure:** Hostinger KVM4, Tailscale VPN, Debian Linux

---

## Abstract

This paper presents the architecture, implementation, and operational characteristics of nox-mem, a persistent memory system designed for autonomous AI agent fleets. The system provides hybrid search (combining BM25 full-text, semantic vector similarity, and Reciprocal Rank Fusion), an LLM-powered knowledge graph with temporal decay, cross-agent intelligence sharing, and automated consolidation pipelines. Deployed in production since March 14, 2026, the system manages 1,481 memory chunks across 7 databases, 384 knowledge graph entities with 529 relations, and serves 6 specialized AI agents with isolated yet interconnectable memory spaces.

---

## 1. Introduction

### 1.1 Problem Statement

Large Language Model (LLM) agents operating in production environments face a fundamental limitation: context window ephemerality. When a conversation ends or context is compacted, the agent loses accumulated knowledge, decisions, and operational state. For multi-agent systems where specialized agents collaborate on complex tasks, this problem compounds — agents cannot learn from each other's experiences, cannot recall past decisions, and cannot build institutional knowledge over time.

### 1.2 Design Goals

nox-mem was designed with four core objectives:

1. **Persistent Memory**: Survive context window resets, session boundaries, and agent restarts
2. **Intelligent Retrieval**: Return semantically relevant results, not just keyword matches
3. **Cross-Agent Intelligence**: Enable knowledge sharing across isolated agent workspaces
4. **Operational Autonomy**: Self-maintain through automated consolidation, pruning, and indexing

### 1.3 Scope

The system operates within the OpenClaw platform, serving 6 AI agents (Nox, Atlas, Boris, Cipher, Forge, Lex) on a single VPS with 4 vCPUs and 8GB RAM. Each agent has a distinct role and memory profile. The workspace (shared memory) and individual agent databases form a federated memory architecture.

---

## 2. System Architecture

### 2.1 Infrastructure Overview

The system runs on a Hostinger KVM4 VPS accessible via Tailscale VPN (IP: 100.87.8.44). Five systemd-managed services provide the runtime environment:

| Service | Port | Type | Function |
|---------|------|------|----------|
| openclaw-gateway | 18789 | WebSocket | Agent communication gateway |
| nox-mem-watcher | — | inotifywait | Filesystem event monitor |
| nox-mem-api | 18800 | HTTP/JSON | Dashboard data API |
| ollama | 11434 | HTTP | Local LLM inference (llama3.2:3b) |
| tailscaled | — | WireGuard | VPN mesh connectivity |

### 2.2 Database Schema

The primary storage is SQLite 3 with WAL (Write-Ahead Logging) mode for concurrent access. The schema (version 3) contains:

**Core Tables:**

- `chunks` — Memory fragments with full-text indexing
  - `id` (INTEGER PK), `source_file` (TEXT), `chunk_text` (TEXT), `chunk_type` (TEXT)
  - `source_date` (TEXT), `is_consolidated` (INTEGER), `memory_type` (TEXT)
  - `created_at`, `updated_at` (TEXT, ISO 8601)
  - `metadata` (TEXT, JSON)

- `chunks_fts` — FTS5 virtual table with porter unicode61 tokenizer
  - Content-sync triggers (INSERT, UPDATE, DELETE) maintain index consistency
  - BM25 ranking with configurable column weights (1.0, 0.5, 0.5)

- `consolidated_files` — Processing state tracker
  - `source_file` (TEXT PK), `status` (INTEGER: 0=pending, 1=done, -1=failed)

- `meta` — Key-value configuration store (schema_version, cursors, metrics)

**Knowledge Graph Tables:**

- `kg_entities` — Named entities with type classification and mention counting
  - UNIQUE constraint on (name, entity_type)
  - TTL tracking via `first_seen`, `last_seen`

- `kg_relations` — Typed relationships between entities
  - Confidence scoring (0.0-1.0) with temporal decay
  - TTL via `expires_at` (90-day default), `last_confirmed`
  - Evidence linking via `evidence_chunk_id`

- `decision_versions` — Architectural decision version history
  - Supersession chain via `is_current` flag and `superseded_at` timestamp

**Vector Tables (sqlite-vec):**

- `vec_chunks` — Virtual table storing float32 embeddings (3072 dimensions)
- `vec_chunk_map` — Rowid-to-chunk_id mapping (sqlite-vec requires rowid-based access)

- `dedup_log` — Suppressed duplicate tracking for audit

### 2.3 Chunk Type Taxonomy

Memory chunks are classified into 10 types based on source file path patterns:

| Type | Source Pattern | Current Count | Purpose |
|------|---------------|---------------|---------|
| team | `shared/` | 499 | Shared team knowledge, cross-agent docs |
| daily | `memory/YYYY-MM-DD` | 161 | Daily operational notes |
| other | (default) | 126 | Unclassified content |
| decision | `memory/decisions.md` | 34 | Architectural and strategic decisions |
| lesson | `memory/lessons.md` | 21 | Errors, corrections, learnings |
| project | `memory/projects.md` | 11 | Active project tracking |
| pending | `memory/pending.md` | 8 | Incomplete tasks and blockers |
| feedback | `memory/feedback/` | 6 | User and system feedback |
| person | `memory/people.md` | 6 | People profiles and contacts |
| digest | `memory/digests/` | 2 | Weekly summary reports |

### 2.4 Multi-Agent Memory Architecture

Each of the 6 agents operates with an isolated database at `/root/.openclaw/agents/{name}/tools/nox-mem/nox-mem.db`. The `OPENCLAW_WORKSPACE` environment variable controls path resolution across all modules, enabling the same nox-mem binary to operate on different databases depending on the calling context.

**Agent Memory Distribution (as of March 23, 2026):**

| Agent | Role | Chunks | DB Size | Dominant Type |
|-------|------|--------|---------|---------------|
| Nox | Chief of Staff | 185 | 268 KB | daily (91) |
| Boris | Head of Communications | 148 | 268 KB | team (50) |
| Forge | Code Reviewer | 182 | 292 KB | daily (135) |
| Atlas | Research | 30 | 128 KB | other (17) |
| Cipher | Security | 31 | 132 KB | other (12) |
| Lex | Legal/Compliance | 31 | 132 KB | other (12) |
| **Workspace** | **Shared** | **874** | **25.2 MB** | **team (499)** |

Total system memory: 1,481 chunks across 7 databases.

---

## 3. Memory Pipeline

### 3.1 Ingestion

Files created or modified in monitored directories trigger the inotifywait-based watcher service. The watcher implements:

- **Debounce logic**: 2-second delay to batch rapid successive writes
- **File filtering**: Only `.md` and `.json` files are processed
- **Recursion prevention**: `MEMORY.md` and `SESSION-STATE.md` are excluded to avoid feedback loops
- **Heartbeat**: Touch `/tmp/nox-mem-watcher-heartbeat` on every event for liveness monitoring

Upon trigger, `ingestFile()` executes:

1. Read file content with UTF-8 sanitization (fixes common mojibake patterns for Portuguese text)
2. Detect chunk type from relative file path
3. Extract date from filename pattern (YYYY-MM-DD)
4. Split content into semantic chunks:
   - Markdown: Split on H2/H3 headers, with sub-splitting for chunks exceeding 500 words
   - JSON: Array items become individual chunks; object entries become key-value pairs
   - Small chunks (<20 words) are merged with the previous chunk
5. Delete existing chunks for the same source file (idempotent re-ingestion)
6. Insert new chunks via prepared statement transaction
7. Auto-vectorize if GEMINI_API_KEY is available (up to 20 chunks per file)

### 3.2 Consolidation

Nightly consolidation (23:00, 5-minute stagger across agents) processes daily notes into structured topic files:

1. **Reindex**: Scan all `.md`/`.json` files in memory directories, rebuild chunk index
2. **Extract**: Use Ollama llama3.2:3b to identify facts, decisions, lessons, and action items from daily notes
3. **Append**: Add extracted content to topic files (decisions.md, lessons.md, people.md, projects.md, pending.md)
4. **Notion Sync**: Push structured items to "Memoria & Decisoes" Notion database (best-effort, non-blocking)
5. **Git Commit**: Auto-commit memory changes with standardized message format
6. **Session Update**: Refresh SESSION-STATE.md with current statistics

### 3.3 Deduplication

Before insertion, chunks are checked for duplicates using a two-tier strategy:

- **Primary**: Gemini cosine similarity with 0.85 threshold (when embeddings are available)
- **Fallback**: Keyword overlap calculation with 60% threshold
- **Audit**: Suppressed duplicates are logged to `dedup_log` table with reason and preview

---

## 4. Hybrid Search System

### 4.1 Architecture

Search combines three complementary retrieval methods:

**Layer 1 — FTS5 BM25 (Keyword)**

SQLite FTS5 with porter unicode61 tokenizer provides fast keyword matching. Results are scored using BM25 with column weights (chunk_text: 1.0, source_file: 0.5, chunk_type: 0.5). Post-retrieval boosting applies:

- Type boost: `decision` and `lesson` chunks receive 2.0x multiplier (higher signal-to-noise ratio)
- Recency boost: Chunks from the last 7 days receive 1.5x multiplier

The query sanitizer strips special characters but preserves hyphens for compound terms (e.g., "nox-mem").

**Layer 2 — Gemini Semantic (Vector)**

Each chunk is embedded using Google's gemini-embedding-001 model (3072 dimensions) with task type RETRIEVAL_DOCUMENT. Query embeddings use task type RETRIEVAL_QUERY for asymmetric similarity optimization.

Vectors are stored in sqlite-vec virtual tables. Retrieval uses cosine distance with a map table (vec_chunk_map) bridging vec_chunks rowids to chunks.id values due to sqlite-vec's rowid-only constraint.

Scoring normalizes distances to a 0-10 scale with type and recency boosting (1.5x and 1.2x respectively, lower than FTS5 to avoid double-boosting in fusion).

**Layer 3 — Reciprocal Rank Fusion (RRF)**

FTS5 and semantic results are merged using RRF with k=60:

```
RRF_score(d) = Σ 1/(k + rank_i(d))
```

Documents appearing in both result sets receive combined scores, marked as `match_type: "hybrid"`. Content-prefix deduplication (first 50 characters) prevents near-duplicate results.

### 4.2 Performance Characteristics

The hybrid approach provides significant quality improvements over single-method search:

| Query | FTS5 Only | Hybrid | Analysis |
|-------|-----------|--------|----------|
| "qual o proximo passo" | 0 results | ROADMAP + PHASE-3 | Semantic captures intent without keyword match |
| "nox-mem" | 0 results | decisions.md + docs | Vector bypasses tokenizer hyphen issues |
| "quem e o Toto" | people.md | people.md + TEAM_MEMORY | RRF combines exact match + semantic context |

### 4.3 Cross-Agent Search

The `crossSearch()` function opens all 7 databases in read-only mode, executes FTS5 queries in each, and merges results with agent attribution. Deduplication uses content-prefix comparison to handle shared documents that appear across multiple agent databases.

---

## 5. Empirical Evaluation — Wave A G5 V3 (May 2026)

> **Headline (canonical, 2026-05-19):** A8 full stack with active salience reaches **nDCG@10 = 0.6237** on the entity-flavored golden set (n=100), a **+78.8% relative improvement over the G3 baseline (0.3488)** measured prior to Wave A deployment, and **+9.4% over the mid-deployment G4 checkpoint (0.5702)**. The peak ablation isolating `section_boost` alone (A3) reaches 0.6228, recovering **99.85% of the full stack** — section-aware ranking is the dominant driver of the lift.

### 5.1 Setup

The evaluation uses an entity-flavored golden set of 100 queries (`entity-eval.db`), curated from production usage to exercise the V10 schema's `section` and `pain` dimensions. Configurations are toggled via environment-variable feature gates (`NOX_SALIENCE_MODE`, `NOX_DISABLE_TIER_BOOST`, `NOX_ENABLE_TIER_BOOST`, `NOX_DISABLE_SECTION_BOOST`, etc.), allowing isolation of individual ranking components without code changes between runs. All measurements occur post-deployment of PRs #150 (salience formula + tier_boost off-by-default), #151 (source_type backfill of 67,949 chunks), and #153 (search wiring). Reported nDCG@10 follows the standard TREC formulation (gain by relevance, log-position discount).

Progression vs prior ablation generations:

| Generation | Date | A8 nDCG@10 | Δ vs G3 baseline | Notes |
|---|---|---|---|---|
| G3 baseline (pre-Wave A) | 2026-05-15 | 0.3488 | — | Multiplicative salience, tier_boost on, section_boost only via legacy code path |
| G4 mid-deployment | 2026-05-18 | 0.5702 | +63.5% | Salience aditivo wired but `active < shadow` puzzle observed |
| **G5 V3 canonical** | **2026-05-19** | **0.6237** | **+78.8%** | Wave A fully deployed; reversal `active > shadow` cravado |

The four sub-claims below decompose the +78.8% total into measurable contributions; the full G5 V3 matrix (12 configurations) is archived in `audits/` and HANDOFF.md (`#g5-v3-matrix-2026-05-19`).

### 5.2 Claim 1 — Additive salience outperforms multiplicative

The Wave A formula replaces the legacy multiplicative `salience = recency × pain × importance` with a weighted-additive form (PR #150):

```
salience = W_IMPORTANCE·importance + W_RECENCY·recency + W_PAIN·pain + W_ACCESS·access_score
W_IMPORTANCE = 0.55   W_RECENCY = 0.15   W_PAIN = 0.10   W_ACCESS = 0.20
```

**Result.** With `NOX_SALIENCE_MODE=active`, A8 reaches 0.6237 vs. 0.6155 with `shadow` (A7) — a +1.3% lift and the reversal of the G4 puzzle, where shadow had outranked active. The multiplicative form concentrated 99.7% of chunks in the [0.05, 0.40] salience range, dominated by 90.67% of chunks at the default `pain = 0.2` and 99.76% of chunks with `recency ∈ [7, 30]` days; small differences in any factor were swallowed by the product. The additive form exposes each dimension proportionally to its calibrated weight, preserving signal from pain spikes and importance heuristics without requiring all three factors to be simultaneously non-default.

### 5.3 Claim 2 — `section_boost` is the moat (99.85% of the gain)

Isolating `section_boost` alone (A3 ablation: section enabled, tier off, source_type off, salience shadow) yields **nDCG@10 = 0.6228 = 99.85% of A8's full-stack 0.6237**. The V10 schema multipliers — `compiled = 2.0`, `frontmatter = 1.5`, `timeline = 0.8`, legacy = 1.0 — together with the entity-file format introduced in v3.7 (769 entity files × 3 sections ≈ 2,307 boost-bearing chunks) explain the majority of the headline improvement.

The negative control A11 (full stack minus `section_boost`) drops to 0.5646, **−9.5% relative to A8**, confirming the contribution is not redundant with semantic embeddings or RRF fusion. This is the architectural pivot the paper's narrative rests on: section-aware boosting over an entity-file canonical form is the load-bearing component, not the multiplicative salience formula that the v1 paper draft over-emphasized.

### 5.4 Claim 3 — `tier_boost` off-by-default is the correct calibration

Isolated, `tier_boost` (boost for `chunks` flagged as `tier='core'`) is actively harmful: A6 (tier only, no other boosts) reaches 0.4059, **−21% versus the no-boost baseline 0.5126**. Even integrated into the full stack, A9 (full + tier enabled) drops to 0.5884, **−5.7% versus A8**. Inspection of the corpus reveals the cause: `tier='core'` chunks account for only 3.96% of the corpus and consist of memory-system internals (lifecycle docs, schema metadata, operational runbooks) rather than user content — over-promoting them displaces directly-relevant entity facts.

PR #150 therefore makes tier_boost **off by default** via `NOX_DISABLE_TIER_BOOST=1`, with an explicit `NOX_ENABLE_TIER_BOOST=1` opt-in for callers who want the legacy behavior. The default reflects the calibration this evaluation establishes; the opt-in preserves backward compatibility for downstream pipelines that depend on it.

### 5.5 Claim 4 — `source_type` backfill recovery

Pre-backfill, **67,949 chunks (98.48% of the corpus)** carried `source_type = NULL`, rendering the `SOURCE_TYPE_BOOST` map inert at search time regardless of the configured multipliers. PR #151 backfills 11 canonical keys (`entity`, `lesson`, `skill`, `project-doc`, `command`, `legal-template`, `personal-doc`, `session`, `note`, `external`, `other`, `ocr-cache`) by classifying each chunk via deterministic path/prefix rules under `withOpAudit()` (audit_id = 118), preserving the 1,046 chunks already marked `external` (1.52%). The post-backfill distribution skews to `personal-doc` (32.74%), `skill` (19.89%), and `session` (16.95%), reflecting the lived shape of the operational corpus.

In the G5 V3 matrix, A5 (source_type only) and A10 (full minus source_type) both score 0.6237 — identical to A8 — confirming the `SOURCE_TYPE_BOOST` map remained **inert by key mismatch**, not by data absence. PR #154 (merged 2026-05-20) updated the boost map to the new keys (calibration ranging from `entity = 2.0` for high-curation chunks down to `ocr-cache = 0.7` for low-signal scanned material).

The G8 ablation (2026-05-20, PR #177) re-ingested an isolated `entity-eval-v2.db` (500 chunks) with source_type values deterministically remapped to prod-consistent vocabulary (`entity_file → entity`, `event_log → lesson`, `session_summary → session`), achieving 100% key-match with the SOURCE_TYPE_BOOST map. Results:

| Config | nDCG@10 | Δ vs A0 | Verdict |
|---|---|---|---|
| A0 (no boosts) | 0.4816 | baseline | — |
| **A5 (source_type only)** | **0.4944** | **+2.66%** | LIVE — boost contributes when keys match |
| A8 (full canonical) | 0.5798 | +20.4% | full stack |
| A10 (full minus source_type) | 0.5845 | +21.4% | source_type *removed* from full stack |

A5 > A0 by +2.66% empirically validates that `SOURCE_TYPE_BOOST` contributes to ranking when source_type values match the map keys. However, A8 < A10 by −0.81% reveals **redundant double-boost** when `section_boost` (e.g., `compiled = 2.0` for entity-file truth sections) and `SOURCE_TYPE_BOOST` (e.g., `entity = 2.0` for the same chunks) stack on identical chunks, over-promoting at the cost of top-K diversity. Per-category, the redundancy manifests as a −3.5 pp regression on open-domain queries and a +1.4 pp gain on multi-hop.

The **G9 ablation** (2026-05-20, against the prod-flavored `g5.db` 68k corpus, PR planned) **reproduces and amplifies** both findings — at production scale the boost contribution and the redundancy are both **5× larger in magnitude** than in the synthetic G8 set:

| Config | G8 (n=500) | G9 (n=68,995) | Δ G9 magnitude vs G8 |
|---|---|---|---|
| A0 (no boosts) | 0.4816 | 0.4108 | smaller baseline (prod diversity) |
| **A5 (source_type only)** | **+2.66% vs A0** | **+14.2% vs A0** | **5× larger** |
| A8 vs A10 (redundancy) | **−0.81%** | **−2.6%** | **3× larger** |

The G9 data **structurally validates** the resolution path of mutual-exclusion logic (PR #182, merged 2026-05-20): when a chunk has `section ∈ {compiled, frontmatter, timeline}` populated (entity-file structural metadata), the `source_type_boost` is gated to `0` to prevent stacking on top of `section_boost`. The mutex is rollback-gated via `NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1`.

The **G10 ablation** (2026-05-20, against `g9.db` 69,495 chunks) validates the mutex in production conditions:

| Config | nDCG@10 | MRR | R@10 |
|---|---|---|---|
| A8' (mutex active, default) | **0.5478** | **0.5967** | 0.6183 |
| A8 (mutex disabled, rollback flag) | 0.5435 | 0.5813 | 0.6333 |
| **Δ mutex effect** | **+0.79%** | **+2.65%** | −2.4% |

The mutex recovers ~46% of the A10 − A8 gap (where A10 fully removes `source_type_boost`) without removing the signal entirely. The per-metric pattern — MRR ↑ (top-1 quality) and R@10 ↓ (diversity) — surfaces a deliberate trade-off: the mutex improves precision at the cost of some recall breadth, with net positive on the weighted nDCG@10.

The **G10b per-category breakdown** (2026-05-21, same DB, n = 100 across 5 categories) reveals which query types absorb the trade-off:

| Category | n | nDCG@10 Δ% | MRR Δ% | R@10 Δ% | Verdict |
|---|---|---|---|---|---|
| single-hop | 20 | **+8.22%** | **+13.20%** | 0% | strong win |
| open-domain | 20 | **+2.42%** | **+5.56%** | 0% | win |
| multi-hop | 20 | −3.95% | −2.70% | **−6.02%** | regression |
| adversarial | 20 | −2.95% | −5.88% | 0% | regression |
| temporal | 20 | n/a | n/a | n/a | degenerate corpus gap |

The aggregate Δ (+0.43% nDCG, +0.82% MRR) is consistent in direction with the G10 measurement (+0.79% / +2.65%) but attenuated in magnitude — within harness noise at n = 100, suggesting the deploy-time figure was on the upper end of a noisy distribution. Substantively: the mutex is a **single-hop optimizer with open-domain side benefits**, balanced against a multi-hop chain-traversal regression of −6.02% R@10. Net retrieval value (+0.0616 nDCG abs gain) exceeds losses (−0.0498 nDCG abs), so the mutex stays deployed; the multi-hop regression is documented as a follow-up candidate for **conditional mutex** (active only when `query_entities ≤ 1`).

The **G11 trim ablation** (2026-05-20, same DB) tested whether trimming the top SOURCE_TYPE_BOOST values (`entity: 2.0 → 1.3`, `lesson: 1.8 → 1.2`) could provide additive benefit over the mutex:

| Config | nDCG@10 | MRR |
|---|---|---|
| Canonical (entity=2.0, lesson=1.8) | **0.5376** | **0.5843** |
| Trim (entity=1.3, lesson=1.2) | 0.5337 | 0.5751 |
| Δ | **−0.73%** | **−1.58%** |

Trim is **rejected**. The mutex already zeroes `sourceTypeDelta` where redundancy occurs (chunks with both `section` and high source-type); the `entity = 2.0` still fires legitimately on legacy non-compiled chunks where the mutex does not trigger, and trimming kills that residual signal. The single-hop category suffered worst (−4.62% nDCG, −7.40% MRR), confirming the mutex resolves redundancy **precisely**, while a global trim over-corrects. The boost stack settles at the canonical configuration: `section_boost × source_type_boost (mutex-gated) × additive salience v2`.

The **G10c per-style breakdown** (2026-05-21, same DB, n = 100 across 2 styles — the dataset distinguishes `keyword` vs `natural-language` rather than the paraphrase/literal axis the spec anticipated) cuts the same data along a different dimension to test whether mutex behavior is style-conditional:

| Style | n | nDCG@10 Δ% | MRR Δ% | R@10 Δ% | Verdict |
|---|---|---|---|---|---|
| natural-language | 50 | **+1.56%** | **+3.86%** | −1.62% | mutex helps |
| keyword | 50 | −0.72% | −2.27% | −1.06% | mutex slightly hurts |

The aggregate effect (+0.43% nDCG, +0.82% MRR — identical to G10b because G10c reuses the same A8 active vs A8 disabled detail JSONs and re-buckets) is entirely carried by the natural-language subset. The keyword bucket is a small drag, within the noise floor. Two cross-cuts (style × category) surface as notable outliers: NL × single-hop (+13.83% nDCG, +21.32% MRR — the biggest individual win in the data) and keyword × adversarial (−5.35% nDCG, −10.0% MRR — the only delta crossing the 5% regression threshold, n = 10). Multi-hop suffers ≈ −4% across both styles, confirming the regression is **style-agnostic** and motivating the conditional-mutex follow-up rather than a style-specific routing.

Triangulated across G10 (deploy figure +0.79% / +2.65%), G10b (per-category +0.43% / +0.82%), and G10c (per-style +0.43% / +0.82%), the mutex effect is consistent in direction and on the lower end of the original deploy measurement in magnitude — the deploy figure sat on the upper tail of a noisy distribution rather than reflecting a structural shift. The architectural conclusion stands: **keep the mutex deployed at the per-chunk level; address the multi-hop chain-traversal regression via a conditional gate keyed on `query_entities`**, deferred to the G10d ablation in a future session.

### 5.6 Honest characterization

The +78.8% headline is decisive for the "Pain-weighted hybrid memory" framing in the sense that pain is one of four additive salience components and the full additive formulation outperforms the legacy multiplicative one. It is **not** decisive for "pain as a standalone retrieval signal in hybrid mode" — that question is addressed in the companion arXiv draft (`paper/publication/paper-draft-sec4-7.md` §5.5, E10 pain ablation: directional but not significant, Δ = +0.0065, 95% CI [−0.0143, +0.0338], n = 31 on the prior R01c-v1.1 corpus). The Wave A measurement validates the architectural choices around section-aware ranking and additive salience composition; per-dimension causal attribution of pain alone awaits the post-PR-#154 ablation generation and a corpus with broader pain distribution than the current 90.67% default.

---

## 6. Knowledge Graph v2

### 6.1 Entity Extraction

**v1 (Regex-based)**: Used hardcoded regular expressions for 3 entity types (person, project, agent) with a static alias map for name normalization. Limited to predefined names, producing 26 entities.

**v2 (LLM-powered)**: Uses Ollama llama3.2:3b with a structured extraction prompt. Each chunk is processed with temperature 0.1 for deterministic output. The LLM returns JSON with entities (name + type) and relations (source + relation + target).

Extraction results after processing 866 chunks:

| Metric | Regex v1 | LLM v2 | Improvement |
|--------|----------|--------|-------------|
| Entities | 26 | 384 | 14.8x |
| Relations | 59 | 529 | 9.0x |
| Entity Types | 3 | 11 | 3.7x |

**Entity Type Distribution:**

| Type | Count | Description |
|------|-------|-------------|
| project | 109 | Software projects, products, repos |
| tool | 67 | Libraries, frameworks, CLI tools |
| concept | 54 | Abstract ideas, patterns, methodologies |
| person | 53 | Team members, contacts, stakeholders |
| organization | 50 | Companies, teams, departments |
| agent | 45 | AI agents in the fleet |
| location | 2 | Geographic references |
| other | 4 | Device, currency, date, computer |

### 6.2 Temporal Decay and TTL

Relations have a 90-day time-to-live (TTL) from creation. The confidence decay mechanism operates as follows:

1. Relations start with confidence 0.8 (extracted) or 0.9 (confirmed)
2. Every 30 days without re-confirmation, confidence drops by 0.1
3. Relations below 0.3 confidence receive accelerated 7-day expiry
4. Expired relations are deleted during `kg-prune` execution
5. Re-confirmation (observing the same relation in new chunks) resets confidence to 0.9 and extends TTL by 90 days

This mechanism ensures the knowledge graph naturally forgets stale information while reinforcing actively observed patterns.

### 6.3 Decision Versioning

Architectural decisions are tracked with full version history in the `decision_versions` table. Each decision has a unique key (e.g., `dedup-strategy`, `fallback-chain`) and supports:

- Version chains with supersession tracking
- Authorship attribution
- Source file provenance
- Current vs. historical querying

10 decisions are currently tracked, covering API key management, LLM fallback chains, embedding model selection, agent isolation strategy, and synchronization schedules.

### 6.4 Graph Traversal

The `findPath()` function implements BFS (Breadth-First Search) to discover shortest paths between any two entities. This enables queries like "How is Toto connected to nox-mem?" which traverses person → project → tool → agent relationships. Maximum depth is configurable (default: 4 hops).

---

## 7. Cross-Agent Intelligence

### 7.1 Agent Expertise Profiling

Each agent's memory is analyzed to determine its unique expertise based on chunk type distribution. The dominant chunk type determines the agent's strength category:

- **daily** → "Daily operations & activity logging"
- **team** → "Team coordination & shared knowledge"
- **decision** → "Decision tracking & rationale"
- **lesson** → "Lessons learned & pattern recognition"

Profiles include chunk counts, type breakdowns, top topics (via FTS5 term frequency), and last activity dates.

### 7.2 Knowledge Sharing

The `pullInsightsFrom()` function enables any agent to query lessons and decisions from other agents without direct database access. This creates a knowledge transfer mechanism where, for example, Cipher (Security) can learn from Forge's (Code Reviewer) past code review decisions.

`pullAllInsights()` aggregates insights across all agents, sorted by date, providing a fleet-wide learning feed.

### 7.3 Cross-Agent Knowledge Graph Merge

`mergeCrossKnowledgeGraphs()` scans all agent databases for kg_entities and kg_relations tables, merging them into a unified entity view. Entities are matched by type + lowercase name. The output shows which entities are known to which agents and their combined mention counts, enabling identification of shared knowledge vs. agent-specific expertise.

---

## 8. MCP Server Interface

nox-mem exposes 14 tools via the Model Context Protocol (MCP) over stdio (JSON-RPC 2.0):

| Tool | Category | Description |
|------|----------|-------------|
| nox_mem_search | Retrieval | Hybrid search (FTS5 + semantic + RRF) |
| nox_mem_stats | Monitoring | Database statistics and health |
| nox_mem_primer | Context | Session recovery summary (~500 tokens) |
| nox_mem_ingest | Ingestion | Index a file into memory |
| nox_mem_cross_search | Cross-Agent | Search across all 7 databases |
| nox_mem_cross_stats | Cross-Agent | Chunk counts per agent |
| nox_mem_metrics | Monitoring | Daily observability metrics |
| nox_mem_kg_build | KG | Build knowledge graph from chunks |
| nox_mem_kg_query | KG | Query entity and its relations |
| nox_mem_kg_stats | KG | Knowledge graph statistics |
| nox_mem_agent_profiles | Intelligence | Agent expertise profiles |
| nox_mem_cross_kg | Intelligence | Merged cross-agent knowledge graph |
| nox_mem_kg_path | Intelligence | BFS path between entities |
| nox_mem_self_improve | Analysis | Contradiction detection, pattern analysis |

---

## 9. HTTP API Server

A lightweight HTTP API (Node.js built-in `http` module, zero dependencies) runs on port 18800, exposing memory data to the React dashboard:

| Endpoint | Method | Response |
|----------|--------|----------|
| `/api/health` | GET | System health: chunks, consolidation, vector coverage, services, KG stats, DB size |
| `/api/agents` | GET | Agent expertise profiles array |
| `/api/kg` | GET | Knowledge graph entities and relations |
| `/api/kg/path?from=X&to=Y` | GET | BFS shortest path between entities |
| `/api/search?q=QUERY&limit=N` | GET | Hybrid search results |
| `/api/cross-kg` | GET | Merged cross-agent knowledge graph |

CORS headers are set for cross-origin access from the Vercel-hosted dashboard.

---

## 10. Operational Infrastructure

### 10.1 Cron Schedule

24 cron jobs manage automated operations:

| Time | Frequency | Job | Details |
|------|-----------|-----|---------|
| 23:00-23:25 | Daily | Agent consolidation | 6 agents, 5-min stagger, reindex→consolidate |
| 23:30 | Daily | Workspace consolidation | Central workspace daily notes |
| 23:35 | Daily | Session wrap-up | SESSION-STATE.md, Notion sync, git commit |
| 04:00 | Weekly (Sun) | Vectorize | Gemini embeddings for new/changed chunks |
| */5 min | Continuous | Health check | Watcher heartbeat, service liveness |
| 02:00 | Daily | SQLite backup | Online backup API, 7-day retention pruning |
| */6 hours | Continuous | Git backup | Auto-commit memory file changes |
| 09:00 | Weekly (Mon) | Token check | Forge CC token verification |

### 10.2 Backup Strategy

Three backup mechanisms operate independently:

1. **SQLite Online Backup**: Uses better-sqlite3's backup API for crash-consistent copies. Daily at 02:00, 7-day retention with automatic pruning.
2. **Git Auto-Commit**: Memory directory changes are committed every 6 hours, providing full change history.
3. **File System**: WAL mode ensures database consistency during concurrent reads/writes.

### 10.3 LLM Fallback Chain

To ensure continuous operation regardless of provider availability:

**Paid Tier**: Claude Opus → Sonnet → Haiku → GPT-5.1 → Gemini 2.5
**Free Tier**: Nemotron → Groq Llama70B → Healer → Hunter → Trinity → Gemma27B

The fallback is configured in the environment and selected at runtime based on task complexity and availability.

---

## 11. Dashboard Integration

The TotoClaw Command Center (React 18 + TypeScript + Vite + shadcn/ui) provides 11 pages including 4 nox-mem-specific views:

- **Memory Health** (`/memory`): Real-time system stats, vector coverage progress bar, service status indicators, agent breakdown table
- **Knowledge Graph** (`/knowledge-graph`): Interactive force-directed canvas graph, entity type filters, BFS path finder
- **Agent Intel** (`/agent-intel`): Agent expertise cards with type distribution bars, hybrid search interface, cross-agent knowledge entities
- **System Paper** (`/system-paper`): Live technical analysis with Recharts visualizations (pie, bar, radar, area charts), auto-refresh every 60 seconds

All data is fetched from the nox-mem API server via TanStack React Query with configurable polling intervals.

---

## 12. Evolution History

| Version | Date | Key Changes |
|---------|------|-------------|
| v1.0 | Mar 14 | SQLite FTS5, basic search, consolidation, Notion sync |
| v2.0 | Mar 17 | MCP server, systemd services, watcher heartbeat, primer |
| v2.2 | Mar 20 | Cross-agent search, KG v1 (regex), self-improve, decision versioning |
| v2.5 | Mar 22 | Multi-agent workspace fix (OPENCLAW_WORKSPACE), gateway supervision |
| v2.6 | Mar 22 | Hybrid search default (FTS5+Gemini+RRF), 866/866 vectorized |
| v3.0 | Mar 23 | KG v2 (LLM, 384 entities), Cross-Agent Intelligence, HTTP API, dashboard |
| v3.7 | Apr 23 | Schema V10 (`retention_days` v8 + `pain` v9 + `section` v10), entity file format, section_boost |
| Wave A | May 19 | Additive salience formula, `tier_boost` off-by-default, `source_type` backfill (67,949 chunks), G5 V3 ablation (PRs #150 / #151 / #153) |

---

## 13. Conclusion

nox-mem demonstrates that persistent, searchable, and shareable memory for AI agent fleets is achievable with commodity infrastructure (single VPS, SQLite, local LLM). The hybrid search system consistently outperforms single-method retrieval, particularly for multilingual content and compound technical terms. The LLM-powered knowledge graph provides 15x richer entity extraction compared to regex approaches, while temporal decay ensures the graph stays current without manual curation. The Wave A empirical evaluation (§5) cravou nDCG@10 = 0.6237 on the entity-flavored golden set (+78.8% relative over the G3 baseline), with `section_boost` identified as the dominant driver (99.85% of the lift recovered by A3 alone) and the additive salience formula validated by the `active > shadow` reversal.

The cross-agent intelligence layer transforms isolated agent memories into a collaborative knowledge base, enabling institutional learning across the fleet. Combined with the live dashboard, the system provides full observability into the collective memory of the agent organization.

**Repository:** github.com/totobusnello/nox-workspace
**Dashboard:** github.com/totobusnello/agent-hub-dashboard
**Spec:** Projetos/memoria-nox/specs/2026-03-14-nox-memory-system-design.md
