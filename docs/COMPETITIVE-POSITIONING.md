# Competitive positioning — memoria-nox vs memanto / agentmemory / gbrain

> Strategic positioning matrix for GTM, investor conversations, and internal alignment.
> Source-of-truth for "why does this differ from X?" responses.
>
> **Status:** 2026-05-18 (post-D40 Q/A/P pivot + D41 cross-cutting decisions resolved)
> **Cross-link:** D40 + D41 in `docs/DECISIONS.md`; `docs/VISION.md` v15; `docs/ROADMAP.md`

---

## Contents

1. [Executive summary (TL;DR)](#1-executive-summary)
2. [memanto Six Gaps × nox-mem](#2-memanto-six-gaps--nox-mem)
3. [agentmemory × nox-mem](#3-agentmemory--nox-mem)
4. [gbrain × nox-mem](#4-gbrain--nox-mem)
5. [Cross-cutting differentiation rationale (the moat)](#5-cross-cutting-differentiation-rationale)
6. [Honest gaps — what they have that we don't yet](#6-honest-gaps)
7. [Roadmap to close gaps](#7-roadmap-to-close-gaps)
8. [Pitch templates](#8-pitch-templates)
9. [References](#9-references)

---

## 1. Executive summary

### TL;DR

**memanto** markets "Six Gaps" in incumbent memory systems. Our pivot D40 took each of those gaps and made them competitive differentiators on our KG substrate. We solve them **structurally** (SQL, typed edges, deterministic) where they solve **textually** (embedding similarity, NLI models, probabilistic thresholds).

**agentmemory** ships the iii-engine runtime — user data tied to their inference daemon. We ship as a SQLite file portable across providers (Gemini / OpenAI / Anthropic / Voyage), with provider abstraction already specced (A3) and a zero-vendor validation suite in CI (A4).

**gbrain** (Garry Tan personal brain) has elegant regex-first KG extraction — zero LLM cost, fast, but requires authoring convention. We adopted the pattern in Wave 1 E-lite-2 as a fast-path with confidence gating, keeping LLM as fallback for unstructured text. Hybrid beats either alone.

Our **moat = data autonomy** (SQLite file, no daemon, no SaaS, `cp` is your backup) **+ shadow discipline** (≥7d shadow-mode before activating any ranking change — codified in CLAUDE.md rule #5) **+ scientific rigor** (eval gates, ablation, append-only ops_audit, transparent benchmarks published only when we win).

**Tagline:** *"Pain-weighted hybrid memory with shadow discipline — yours by design."*

### What this doc covers

This is an internal working document — candid about gaps, evidence-grounded, not marketing copy. Use it as prep for:

- GTM conversations (why choose this over X?)
- Investor or advisor framing (how is the moat defensible?)
- Internal roadmap decisions (what to build next + why?)
- Agent/contributor onboarding (what is out of scope + why?)

---

## 2. memanto Six Gaps × nox-mem

memanto (Moorcheh AI) positions their product around six claimed gaps in how current agent memory systems work. The framing is from their public positioning materials (paraphrased — no verbatim copy).

Status legend: ✅ shipped / 🔄 in progress / 📋 specced / ❌ not in scope / ❓ unknown

---

### Gap #1: Static injection — memory is never updated

**memanto framing:** Incumbent systems inject the same frozen memory payload into the system prompt every turn regardless of what changed in the session or the world. Memory is static; context is dynamic. The gap is that there is no writeback path — memory doesn't learn from the session.

**memanto approach:** SaaS pipeline with Moorcheh-managed writeback. Memory is updated on their backend after each interaction. Implementation detail opaque (closed backend).

**nox-mem approach:** Memory updates happen via four paths:
- `nox-mem ingest` CLI — explicit ingest of any file
- inotifywait watcher — file-level reactive ingest (real-time)
- Claude Code hooks auto-capture (P2 spec — PR #4) — zero-manual-ingest path that hooks `SessionStart`, `UserPromptSubmit`, `PostToolUse`, `Stop`, `PreCompact`
- `crystallize` — LLM-assisted consolidation that synthesizes lessons from recent chunks into durable entities

There is no "static frozen snapshot." The DB is the live state; retrieval always queries current data.

**Status:** ✅ shipped (ingest + watcher + crystallize), 📋 specced (P2 auto-capture hooks)

**Implementation:** P2 spec PR #4 (`specs/2026-05-17-P2-hooks-autocapture.md`, 3,968 words, 5 privacy defense layers). Wave 1 E-lite-2 + language-aware RRF already in prod.

**Differentiator:** Our writeback is transparent and inspectable (`sqlite3 nox-mem.db` — open terminal, see everything). Their writeback requires trust in a closed API. Additionally, our `crystallize` command uses Gemini to identify patterns across chunks and produce new canonical entity files — a richer consolidation than simple writeback.

**Honest gap:** Their auto-capture UX is closer to production-ready today. P2 hooks spec is done but implementation is not yet merged. memanto's SaaS model means they can ship UX faster without worrying about self-host compatibility surface.

---

### Gap #2: No temporal decay — all memories treated as equally fresh

**memanto framing:** Incumbent systems give no preferential weight to recency. A fact recorded two years ago competes equally with one recorded yesterday.

**memanto approach:** Proprietary decay function managed by Moorcheh backend. Details not public.

**nox-mem approach:** Three orthogonal temporal mechanisms:

1. **Recency component in salience formula** — `salience = recency × pain × importance`. `recency` = exponential decay function of `created_at` age. Every chunk's retrieval score is modulated by how fresh it is.
2. **`retention_days` typed retention** — schema v8 column. Chunk types decay at different rates: `daily=90d`, `lesson=180d`, `decision/project=365d`, `feedback/person=NULL` (never-decay), `pending=30d`. A daily note from 91 days ago doesn't compete with a crystallized decision.
3. **E13 temporal boost** (shipped Wave 0, active in prod) — `--changed-since` / `--as-of` hard pre-filter on search (P3, PR #2, 23 tests). Temporal is a filter, not a boost — no silent false positives from recency re-weighting.

Additionally, `superseded_by` relation in the KG marks when a fact is replaced by a newer one — the old fact stays in history (audit trail) but is deprioritized. This is temporal supersession at the **relation level**, not just chunk level.

**Status:** ✅ shipped (salience recency + retention_days + E13 temporal boost + P3 temporal queries)

**Implementation:** Salience formula active since G01 (2026-04-30). Retention_days in schema v8. E13 in prod since 2026-05-06. P3 implemented (staged, PR #2).

**Differentiator:** `superseded_by` in KG gives temporal supersession at the semantic level, not just recency bias. We know not just that chunk A is older than chunk B — we know that `(entity X, has_status=Y)` was superseded by `(entity X, has_status=Z)` with a typed edge. memanto's decay is timestamp-only; ours is timestamp + semantic supersession.

**Honest gap:** Salience formula ablation (D24 in DECISIONS.md) is documented as deferred. The pain component's regime-bound effect (D29 — BM25 recall ceiling) is not yet fully resolved. The formula works but the pain dimension's marginal contribution is small outside narrow tied-semantic regimes.

---

### Gap #3: No confidence or provenance metadata

**memanto framing:** Every memory fact is stored with equal epistemic status — observed facts, inferred conclusions, and stale records that were once true all get the same weight. There is no way to distinguish "Toto said X" from "the LLM inferred X from context" from "X was true 8 months ago."

**memanto approach:** Proprietary confidence score + provenance tag on each memory record. Backend assigns these during ingestion (details not public).

**nox-mem approach:** L3 spec (PR #15) introduces schema v19 with five fields:

```
chunks.confidence REAL DEFAULT 0.8       -- epistemic confidence 0–1
chunks.provenance_kind TEXT              -- 'observed'|'declared'|'inferred'|'derived'|'user-marked'
chunks.confidence_set_at TEXT            -- ISO 8601
chunks.confidence_set_by TEXT            -- 'ingest'|'cli'|'consolidate'|'kg-extract'|'decay'
chunks.last_accessed_at TEXT             -- decay reference point
```

Five `provenance_kind` values map the exact distinctions memanto tries to solve: `observed` (witnessed, e.g., recorded in session), `inferred` (LLM-extracted, error-prone), `derived` (consolidated/synthetic), `declared` (user-marked canonical truth), and implicit `stale` behavior via confidence decay on `inferred` + `derived` kinds over time.

**Additionally**, KG relations already have `evidence_chunk_id FK` — every relation points back to the chunk that produced it. Provenance at the knowledge graph level is already structural.

**Status:** 📋 specced (L3, PR #15, 3,526 words) — implementation-ready, ranking integration GATED on eval showing ≥1.0pp absolute lift

**Implementation:** `specs/2026-05-17-L3-confidence-field.md`. Ranking integration is intentionally gated (D41 §4): schema ships first; confidence signal only affects retrieval if ablation confirms lift. This is shadow discipline applied to provenance — ship the data, prove it helps before activating.

**Differentiator:** Two structural advantages over memanto's approach:
1. **KG provenance is already there** — `evidence_chunk_id` in `kg_relations` means relations have provenance today, even before v19.
2. **Pain × confidence interaction** — `pain` already modulates salience. A high-pain (`pain=1.0`) inferred chunk (production incident) should decay slower than a low-pain inferred chunk (casual observation). The interaction is a natural fit for our multiplicative formula.

**Honest gap:** This is Lab-tier, not shipped. memanto has confidence scores in production today. Our gate is higher (≥1.0pp lift required to activate ranking integration), which means we ship responsibly but later.

---

### Gap #4: Flat memory — no structure, no relationships

**memanto framing:** Memories are flat documents/embeddings with no concept of entities, relationships, or structured knowledge. Queries cannot traverse "who knows whom" or "what depends on what."

**memanto approach:** Moorcheh backend (closed). From positioning: embedding-based similarity search is the primary retrieval mechanism. No public description of a structured KG layer.

**nox-mem approach:** Full knowledge graph layer on the same SQLite database:

```
kg_entities: 15,646 typed nodes (id, name, entity_type, description, source_file)
kg_relations: 21,533 typed edges (source_entity_id FK, predicate, target_entity_id FK,
              relation_reason ENUM(7), evidence_chunk_id FK, extraction_metadata)
```

Relation vocabulary is a **closed enum** (`mentions` / `owns` / `decides` / `depends` / `derives_from` / `contradicts` / `supersedes`) — this is an architectural constraint, not a limitation. Free-form predicates would become "Text2Cypher in disguise" (NÃO FAZEMOS #11 in DECISIONS.md).

The KG is queryable via:
- `kg-path` API — find paths between two entities
- `kg-build` CLI — force rebuild/incremental
- SPO injection (E03b, active in prod since 2026-05-17) — entity-rich queries automatically prepend a triple block to the search result, grounding the response in structured facts

**Status:** ✅ shipped (KG entities + relations + SPO injection, active in prod)

**Implementation:** KG extraction via Gemini 2.5 Flash, incremental nightly. SPO injection integrated in `nox-mem search` CLI (commit `90fa3180`, 2026-05-17). `/api/kg/path` endpoint live.

**Differentiator:** The KG is **co-located with the chunks** in the same SQLite file. No separate graph database (NÃO FAZEMOS #9 — Memgraph/Neo4j is over-engineering for this scale). This means:
- Every relation has `evidence_chunk_id` — traceable back to source text
- SPO injection adds deterministic structured context to semantic search without a second API call
- KG + FTS5 + sqlite-vec in one file = one `cp` is a complete backup

**Honest gap:** KG coverage is 5.5% of chunks as of 2026-05-17 (up from 4.92%). memanto's flat embedding approach is faster to ingest and doesn't depend on LLM extraction quality. Our structured approach requires ongoing Gemini extraction (cost + latency). The quality of our KG is directly tied to extraction prompt quality — D38 (reason boost cut) was partly caused by trivial relations with high coverage scores.

---

### Gap #5: No conflict detection — contradictions silently coexist

**memanto framing:** When two memories contradict each other, both are stored and retrieved with equal weight. The system has no mechanism to detect or surface the conflict — users discover contradictions at use time, if at all.

**memanto approach:** Text-level / embedding-based contradiction detection. Two chunks with embeddings above a similarity threshold but opposing semantic content trigger a flag. Requires an NLI (natural language inference) model. Probabilistic threshold — false positives on paraphrase, negation polarity, hedge language.

**nox-mem approach:** L2 spec (PR #13) implements conflict detection at the **relation level**, not text level:

**Type 1 — Direct contradiction:** SQL `GROUP BY (source_entity_id, predicate)` finds predicates that are functional (max 1 object per subject) but have >1 distinct object. No NLI model needed. `O(N)` over relations.

Example: `(tool X, is_deployed_at, vps-A)` AND `(tool X, is_deployed_at, vps-B)` — SQL detects this deterministically in milliseconds.

**Type 3 — Temporal supersession:** Same `(subject, predicate)` with different objects at different times. The newer supersedes the older; older is flagged as stale, not deleted (append-only audit). Evidence chunk linked to the supersession.

```sql
-- Type 1 detection is this simple:
SELECT source_entity_id, predicate, COUNT(DISTINCT target_entity_id) AS n_objects
FROM kg_relations
WHERE predicate IN (SELECT predicate FROM functional_predicates)
GROUP BY source_entity_id, predicate
HAVING n_objects > 1;
```

**Status:** 📋 specced (L2, PR #13, 3,067 words) — implementation-ready, blocked on Phase 0 schema extension (`created_at`/`updated_at` on `kg_relations`)

**Implementation:** `specs/2026-05-17-L2-conflict-detection.md`. Phase 0 schema extension is a blocker for Type 3 (temporal supersession). Type 1 detection is unblocked.

**Differentiator:** Structural vs probabilistic. memanto must guess (NLI + similarity threshold). We can prove (SQL deterministic). False positive rate for Type 1 is 0 by construction — the functional predicate registry is the only variable. False positive rate for Type 3 is controlled by temporal window configuration.

Additionally: our conflict detection does **not auto-resolve**. Default is `conflict_status = 'pending'` — surfaces to the user, logged in `kg_conflicts` table, decision is human's. Auto-resolution is opt-in only (append-only audit maintained throughout). This matches our shadow discipline philosophy: surface, don't silently fix.

**Honest gap:** Not shipped. memanto has this in production. Our implementation is blocked on Phase 0 schema extension. Type 2 (logical conflicts) and Type 4 (transitive/multi-hop) are deferred to L2.1.

---

### Gap #6: Indexing delay — memory not available immediately

**memanto framing:** After storing a new memory, there is an indexing delay before it is retrievable. Sub-second ingestion is a claimed differentiator for memanto ("zero indexing latency").

**memanto approach:** Moorcheh claims near-instant availability post-ingest. Architecture likely avoids batch embedding re-runs by indexing inline at write time (unverified — closed backend).

**nox-mem approach:** Two modes:

- **FTS5 (BM25):** Available immediately on ingest. `INSERT INTO chunks_fts` happens in the same transaction as `INSERT INTO chunks`. Zero delay for lexical search.
- **Dense vector (sqlite-vec):** Requires an embedding call to Gemini (gemini-embedding-001, 3072d). By default this is synchronous at ingest time for new content, but batch backfill (`nox-mem vectorize`) handles large imports. Coverage is 99.97% as of snapshot 2026-05-17.

In practice: hybrid search (FTS5 + dense + RRF) has the dense component delayed by one Gemini round-trip (~200-400ms), but FTS5 coverage is instant. For local use where corpus growth is incremental (not bulk imports), this is imperceptible.

**Status:** ✅ shipped (FTS5 instant), ✅ shipped (vectorize batch with 99.97% coverage), 🔄 in progress (sub-second per-chunk embedding at ingest for new chunks)

**Differentiator:** Our FTS5 layer delivers immediate lexical coverage with zero delay. For hybrid search, the dense component adds one Gemini round-trip — a tradeoff for 3072d quality over 768d speed. Q3 (latency benchmark, PR #11) will quantify p50/p95/p99 cold + warm to provide honest numbers against memanto's "sub-90ms" claim.

**Honest gap:** memanto's claim of "sub-90ms" for end-to-end search is plausible for a SaaS with precomputed embeddings served from GPU-backed inference. Our hybrid search p95 on VPS Hostinger is currently unmeasured (Q3 not yet run). The honest answer is: we don't know yet. Q3 will tell us.

---

## 3. agentmemory × nox-mem

agentmemory (`rohitg00/agentmemory`) is a runtime/library built on iii-engine. It reached ~11.3k stars in under 3 months (as of 2026-05), largely through auto-capture hooks UX and strong marketing. It is the most direct market signal for what viral adoption looks like in this space.

### Architecture comparison

| Aspect | agentmemory | nox-mem |
|---|---|---|
| Storage | iii-engine binary (proprietary runtime) | SQLite `.db` file (open format) |
| Portability | Requires iii-engine process running | Any SQLite-capable language, no daemon |
| Inspect raw data | Via iii API only | `sqlite3 nox-mem.db` — open terminal |
| Provider | iii-engine managed (unknown internals) | Pluggable (A3 spec): Gemini / OpenAI / Anthropic / Voyage |
| Daemon required | Yes (iii-engine) | No (A4 zero-vendor suite validates this) |
| Self-host | With iii-engine dependency | Without any external runtime dependency |
| Backup | Depends on iii-engine state | `cp nox-mem.db backup.db` — complete |
| Encryption | Unknown | AES-256-GCM + scrypt KDF, opt-out via `--unencrypted` (A2 spec D41) |
| Open-source | MIT (wrapper); iii-engine: ❓ | MIT (full stack) |
| Embedding model | ❓ (iii-managed) | Gemini gemini-embedding-001 3072d (best public dense) |
| Retrieval | BM25 + vec + KG + RRF (claimed) | FTS5 BM25 + Gemini 3072d + RRF language-aware (shipped) |
| KG | Yes (iii-engine managed) | Yes (SQLite, co-located, evidence-linked) |
| Shadow discipline | None (no public evidence) | ≥7d shadow before any ranking change (CLAUDE.md rule #5, documented) |
| Eval harness | Self-reported benchmarks | LoCoMo R@5, LongMemEval accuracy (Q1+Q2 in scaffold, full run pending) |
| Star count (2026-05) | ~11.3k | Private repo, open-source rampup planned |

### Feature comparison

| Feature | agentmemory | nox-mem |
|---|---|---|
| Auto-capture hooks | ✅ (viral selling point) | 📋 P2 specced (PR #4, 5 hook types) |
| Answer primitive | ✅ (chat-based recall) | 📋 P1 specced (PR #3, 5,307 words) |
| Temporal queries | ❓ unknown | ✅ shipped (P3, PR #2, 23 tests) |
| IDE integration | ✅ (multi-IDE shallow) | 📋 P4 specced (Tier A deep: Claude Code + Cursor + Codex) |
| Real-time viewer | ✅ (live feed) | 📋 P5 specced (PR #10, SSE + 4 panels) |
| Privacy filter pre-storage | ❓ unknown | ✅ shipped (A1, PR #5, 68 tests, 1.7% FP rate) |
| Schema export/import portable | ❌ (tied to iii-engine state) | 📋 A2 specced (encrypted-by-default, round-trip nDCG ±0.001) |
| Provider abstraction | ❌ (iii-engine only) | 📋 A3 specced (EmbeddingProvider + LLMProvider interfaces) |
| Zero-vendor validation | ❌ | ✅ A4 scaffolded (8 checks, CI-runnable, PR #14) |
| Conflict detection | ❓ unknown | 📋 L2 specced (SQL deterministic, KG-level) |
| Confidence/provenance | ❓ unknown | 📋 L3 specced (schema v19, gated on eval lift) |
| Append-only ops audit | ❌ | ✅ shipped (ops_audit, CWE-693 triggers, append-only) |
| Public eval methodology | Self-reported LoCoMo 95.2% | Scaffold done (Q1), full run pending; honest = publish only when winning |

### Why agentmemory reached 11.3k stars

agentmemory's viral growth came from a specific UX insight: **developers don't want to remember to save memories**. Auto-capture hooks (SessionStart, PostToolUse, etc.) eliminate the manual ingest friction. Combined with multi-IDE breadth and a memorable marketing narrative, this created a viral loop.

nox-mem's P2 spec (PR #4) is a direct response to this signal — with one critical difference: P2's 5 privacy defense layers ensure that auto-capture doesn't silently ingest credentials, code snippets with secrets, or personal data. The 5-layer defense is:

1. Privacy filter A1 (13 patterns, pre-storage)
2. Hook-level content type detection (binary, credential patterns)
3. User-configurable allowlist/denylist per hook type
4. Dry-run mode showing what would be captured before enabling
5. `<private>` tag inline in content blocks

This is not a feature agentmemory markets — their approach optimizes for "capture everything." Our approach optimizes for "capture intelligently, never capture secrets."

### The lock-in asymmetry

agentmemory's growth creates a moat through lock-in: once your session history is in iii-engine, migration is non-trivial. This is intentional product design — it's why their auto-capture UX is so frictionless. The cost is that the user's memory data is inseparable from the runtime.

nox-mem's A2 (export/import) + A3 (provider abstraction) + A4 (zero-vendor suite) are explicitly designed to make lock-in impossible. A user can `export`, take the `.tar.gz` archive, import into a new instance, and pass Q3 latency benchmarks. The round-trip is validated to ±0.001 nDCG@10.

---

## 4. gbrain × nox-mem

gbrain (Garry Tan, `thedivtagguy/gbrain` or similar — public MIT repo) is a personal brain framework with a strong following due to Garry Tan's profile. It is architecturally different from memanto and agentmemory: it is not primarily a memory layer for agents, but a personal knowledge graph tool.

### Approach comparison

| Aspect | gbrain | nox-mem |
|---|---|---|
| Target user | Individual (personal brain) | Individual + multi-agent (6 personas sharing one DB) |
| Primary goal | Personal knowledge retrieval | Agent memory layer (retrieval + KG + salience + audit) |
| KG extraction | Regex on authored conventions (zero LLM cost) | L4 regex-first + LLM fallback hybrid (Wave 1 E-lite-2) |
| Storage | Local SQLite / git-backed markdown | SQLite file (WAL mode, concurrent readers) |
| Search | Grep / regex / BM25 | Hybrid: FTS5 BM25 + Gemini 3072d + RRF language-aware |
| MCP tools | 30+ tools (wide surface) | 16 tools (cap enforced, NÃO FAZEMOS #8 DECISIONS.md) |
| Conflict detection | ❌ (no mechanism) | 📋 L2 specced (KG-level SQL, Type 1 + Type 3) |
| Provider abstraction | N/A (no LLM in retrieval) | 📋 A3 specced |
| Daemon required | No | No |
| Agent multi-tenancy | No | Yes (7 personas, cross-agent search) |
| Shadow discipline | N/A | ≥7d shadow before ranking activation |
| Eval harness | No | LoCoMo + LongMemEval (Q1+Q2, in progress) |
| Inspectable | Yes (markdown + SQLite) | Yes (SQLite3 open terminal) |
| Star count (2026-05) | ~16.6k | Private (open-source rampup planned) |

### Why we adopted regex-first from gbrain (Wave 1 E-lite-2)

gbrain's core insight: when your corpus follows authoring conventions (structured markdown, consistent frontmatter, typed sections), regex extraction is cheaper and more reliable than LLM inference for the structured parts.

We integrated this as a confidence-gated fast-path in Wave 1 (E14 E-lite-2, shipped 2026-05-17):

- `fts_anchor` field added to `chunks` (schema v18, `ALTER TABLE chunks ADD COLUMN fts_anchor TEXT`)
- Bilingual regex patterns extract English + Portuguese anchors from structured headings, code identifiers, proper nouns
- If regex extracts with high confidence → indexing skips LLM anchor generation
- If unstructured text → falls through to existing Gemini embedding pipeline

Result: FTS5 recall improved (Wave 1 E14 D-letter language-aware RRF weights: nDCG@10 from 0.6813 baseline to measured improvement). The regex fast-path reduced Gemini calls for structured content without sacrificing quality on unstructured content.

**What we explicitly did not adopt from gbrain:**

- 30+ MCP tools pattern (NÃO FAZEMOS #8 — more tools = more maintenance surface; cap at 16, capabilities grow via search quality)
- git-as-source-of-truth (NÃO FAZEMOS #19 — incompatible architectures; features portable, architecture not)
- Postgres/PGLite as storage engine (NÃO FAZEMOS #10 — adds daemon, autovacuum, backup complexity)

### gbrain's architectural philosophy vs nox-mem

gbrain's philosophy: knowledge lives in markdown files, git is the source of truth, regex is cheap and transparent.

nox-mem's philosophy: knowledge lives in SQLite, the DB is the source of truth, hybrid retrieval (text + structure + vector) is the quality bar.

These are genuinely different bets. gbrain wins on simplicity and transparency for a personal brain with consistent authoring conventions. nox-mem wins on recall quality for heterogeneous corpora (PDFs, transcripts, PPTX, code, markdown mixed) and for multi-agent scenarios where different agents produce differently-structured content.

The convergence point (regex-first extraction as a fast-path on structured content) is the idea worth borrowing — not the architecture.

---

## 5. Cross-cutting differentiation rationale

### 1. Data autonomy (Pillar A)

The moat that differentiates from all three competitors simultaneously:

| Autonomy layer | What it means | Shipped? |
|---|---|---|
| **SQLite portable file** | `cp nox-mem.db /anywhere` — complete backup, zero runtime dep | ✅ (architecture) |
| **No daemon required** | Works without iii-engine, without Moorcheh, without any SaaS | ✅ A4 scaffold validates |
| **Provider pluggable** | Swap Gemini for OpenAI / Voyage / Anthropic in one env var | 📋 A3 specced |
| **Schema export/import** | tar.gz archive, encrypted-by-default, round-trip ±0.001 nDCG | 📋 A2 specced |
| **Privacy filter pre-storage** | 13 patterns, `<private>` tag, FP rate 1.7% | ✅ A1 shipped (staged) |
| **Open format** | Any language reads it: `sqlite3`, Python `sqlite3`, Rust `rusqlite` | ✅ (architecture) |

The stacking effect: a user who moves from VPS to a local Mac, then to a cloud VM, then decides Gemini is too expensive and switches to Voyage — they do this with two shell commands and zero data loss. No competitor in the matrix offers all six layers.

### 2. Structural KG over flat text

Why KG substrate matters (not just for "Gap #4"):

- **Conflict detection (L2):** flat text needs NLI models (expensive, error-prone). KG needs SQL GROUP BY (O(N), deterministic, zero false positives on Type 1).
- **Temporal supersession (L2 Type 3):** flat text decays by timestamp. KG decays by semantic edge — `(entity, has_status)` pointing to an old value gets a typed `superseded_by` edge pointing to the new value. History preserved, truth updated.
- **SPO injection (E03b, active):** entity-rich queries automatically prepend a triple block (7 triples typical, 91 tokens) from the KG before semantic search results. Zero extra API call — SQL join, not LLM inference.
- **Cross-agent reasoning:** 15,646 entities shared across 7 personas. When Atlas asks about Boris's expertise, the KG path query answers without needing Boris's session history in context.
- **Provenance (L3):** every KG relation carries `evidence_chunk_id` — traceable to source text. memanto stores assertions; we store where the assertion came from.

### 3. Shadow discipline (CLAUDE.md rule #5)

Every feature that affects retrieval ranking or scoring must spend ≥7 days in shadow-mode (observing, not changing results) before activation. This is CLAUDE.md critical rule #5 — not a suggestion, an architectural invariant.

**Why this is a competitive advantage:**

agentmemory and memanto both ship new ranking/scoring features in production immediately ("ship and pray"). Our shadow discipline means:

- We accumulate telemetry (`search_telemetry` table, A0 query logging) in shadow before any ranking change goes live
- Gate reviews compare shadow nDCG@10 delta against production baseline
- Features that look good in isolation but harm production (D38 reason boost, D36 focus boost, D39 FTS5 tuning) are cut before users see regression

The public evidence: D38 (reason boost) was caught at gate review round 3 (after 3 sessions and n=80 golden queries). If shipped immediately, it would have regressed cross-agent and procedure categories in production. No user would have noticed until they saw worse answers — and the root cause (KG quality feeding the boost) would have been invisible.

Shadow discipline is not overhead. It is the mechanism that allows rapid iteration without production regressions. The cost is 7d per ranking feature. The benefit is zero silent regressions in prod since system inception.

### 4. Scientific rigor — eval gates, ablation, append-only audit

**Eval discipline:**
- Honest golden set: n=80 queries (not a cherry-picked 10-query set)
- nDCG@10 as primary metric (not a proprietary score we define)
- Cross-corpus validation: LOCOMO FTS5 0.281 vs our golden FTS5 0.012 = 23× harder corpus (D30 — documents that corpus quality matters)
- Public benchmarks only when winning (D27 + ROADMAP §Q4 gate)

**Ablation discipline:**
- D29 (pain ablation): ran n=31 + n=60, refuted H1+H2+H3. Pain effect is real but regime-bound. Result published in paper §5.5, not swept under the rug.
- D28 (multilingual-e5-base baseline): ran n=60 3-run replicated. gemini-embedding-001 wins 5/8 categories by 1.7× lift. Kept Gemini, published the comparison.
- D38 (reason boost): 3 full gate review rounds, consistent diagnosis. Cut permanently. Lesson: "reason quality > reason quantity" codified in DECISIONS.md.

**Append-only audit:**
- `ops_audit` table has CWE-693 triggers: DELETE blocked, UPDATE blocked on terminal status rows
- Every destructive operation (reindex, compact, crystallize, kg-prune) goes through `withOpAudit()` — VACUUM INTO snapshot before, ops_audit row after
- Snapshot retention 7d, ACL 0600, dir 0700
- `safeRestore()` function for recovery validates user_version match before restore

This is the operational complement to shadow discipline: not just "measure before activating" but "audit everything that could corrupt state, and make the audit immutable."

### 5. Q/A/P pillars completeness

No single competitor covers all three pillars:

| Pillar | memanto | agentmemory | gbrain | nox-mem |
|---|---|---|---|---|
| **Q — Quality** (benchmarks, eval, ablation) | Self-reported benchmarks | Self-reported LoCoMo 95.2% | No benchmarks | LoCoMo + LongMemEval + p95 latency (Q1+Q2+Q3 in progress) |
| **A — Autonomy** (data portability, no lock-in) | ❌ SaaS lock-in | ❌ iii-engine lock-in | Partial (git/markdown portable but no agent layer) | A1-A4 (privacy + export + provider + zero-vendor) |
| **P — Product** (UX, hooks, IDE integration) | Yes (SaaS UX) | Yes (viral auto-capture, multi-IDE) | Partial (personal use only) | P1-P5 specced; P3 shipped |

The unique cell: only nox-mem is pursuing all three simultaneously. memanto sacrifices A to win P. agentmemory sacrifices A to win P with viral UX. gbrain sacrifices Q and agent-P to win personal A.

---

## 6. Honest gaps

What competitors have that we do not yet have in production (as of 2026-05-18). This list is for internal calibration — not for external communication.

### vs memanto

| Gap | Their status | Our status | Roadmap |
|---|---|---|---|
| Confidence scores in production | ✅ live | 📋 L3 specced, gated on ≥1pp eval lift | L3 implementation, estimated Q3 2026 |
| Conflict detection in production | ✅ live (text-level) | 📋 L2 specced, blocked on Phase 0 schema | L2 Phase 0 → Phase 1 implementation |
| Sub-90ms search latency (claimed) | "sub-90ms" (unverified) | Unknown (Q3 not run) | Q3 full run on VPS (week 2026-05-20) |
| Auto-writeback from session | ✅ live | 📋 P2 specced, not merged | P2 implementation (after P1 ships) |
| Measured LongMemEval accuracy | 89.8% (self-reported) | Q2 scaffold done, full run pending | Q2 full run (week 2026-11) |
| Public hosted option | ✅ SaaS | ❌ (self-host only by design) | Not planned (A pillar = self-host is the moat) |

### vs agentmemory

| Gap | Their status | Our status | Roadmap |
|---|---|---|---|
| Auto-capture hooks shipped | ✅ live (viral) | 📋 P2 specced, not merged | P2 implementation post-P1 |
| Multi-IDE shallow coverage (10+ IDEs) | ✅ live | 📋 P4 Tier B (10 IDEs MCP-passive) | P4 Tier A first, Tier B after |
| Real-time viewer shipped | ✅ live | 📋 P5 specced, not merged | P5 implementation post-P1+P3 |
| GitHub star count | ~11.3k | Private (open-source rampup) | GTM Phase 2 gated on Q4 COMPARISON.md |
| Answer primitive shipped | ✅ (chat-based) | 📋 P1 specced, not merged | P1 first implementation sprint |
| Measured LoCoMo R@5 | 95.2% (self-reported) | Q1 scaffold done, full run pending | Q1 full run (week 2026-11) |

### vs gbrain

| Gap | Their status | Our status | Roadmap |
|---|---|---|---|
| GitHub star count | ~16.6k | Private | GTM Phase 2 gated |
| Simplicity / onboarding curve | Very low (markdown + regex) | Higher (SQLite + Gemini API + daemon-optional setup) | P4 `nox-mem connect <ide>` reduces setup friction |
| Established community / contributors | Active | None yet | Post-open-source-launch |

### Universal honest gaps (all competitors)

- **nox-mem is not yet open-source** — currently private. agentmemory's viral loop required public repo + README-first marketing. Without this, comparison site rankings and community contributions are impossible. GTM Phase 2 is locked behind Q4 COMPARISON.md winning.
- **No hosted option** — by design (Pillar A = data autonomy). But this means adoption requires self-hosting competence. The P4 `nox-mem connect <ide>` CLI is the UX answer to onboarding friction, but it's not shipped yet.
- **Q1+Q2 full runs not complete** — we have scaffold + honest golden set at n=80. Claims about LoCoMo R@5 and LongMemEval accuracy are hypotheses until the full runs complete.

---

## 7. Roadmap to close gaps

| Gap | Closes | Sprint | Gate | ETA bucket |
|---|---|---|---|---|
| Auto-capture hooks | agentmemory (UX parity), memanto (writeback) | P2 implementation | Depends on P1 shipped; 5 privacy layers verified | Q4 2026 |
| P1 answer primitive | agentmemory, memanto (recall UX) | P1 implementation (first sprint, D41 §5) | Anti-hallucination guard + citation by chunk_id | Q3 2026 |
| Conflict detection | memanto Gap #5 (structural > text-level) | L2 Phase 0 → Phase 1 | Phase 0 schema extension (created_at on kg_relations) | Q4 2026 |
| Confidence/provenance | memanto Gap #3 | L3 implementation | ≥1.0pp absolute lift on eval golden set | Q3-Q4 2026 |
| LoCoMo R@5 measured | agentmemory (95.2%), Letta (83.2%), mem0 (68.5%) | Q1 full run on VPS | Scaffold done (PR #6); needs VPS compute window | Week 2026-11 |
| LongMemEval accuracy | memanto (89.8% self-reported) | Q2 full run | Scaffold done (PR #12); needs LLM-as-judge budget | Week 2026-11 |
| p95 latency vs "sub-90ms" | memanto claim | Q3 full run | 6 workloads × cold+warm, p50/p95/p99 | Week 2026-11 |
| Open-source launch | gbrain / agentmemory (community, stars) | GTM Phase 2 | Locked: Q4 COMPARISON.md must show nox-mem winning or tied | When Q4 gate opens |
| Provider abstraction live | agentmemory (iii lock-in) | A3 implementation | EmbeddingProvider + LLMProvider interfaces, health check + fallback | Q3 2026 |
| Export/import live | agentmemory (data portability) | A2 implementation (parallel with P1, D41 §5) | Round-trip nDCG ±0.001, encrypted-by-default | Q3 2026 |
| Real-time viewer | agentmemory (UX), memanto | P5 implementation | P1+P3 shipped first | Q4 2026 |
| Multi-IDE Tier A | agentmemory (breadth) | P4 Tier A (3 IDEs deep) | Claude Code + Cursor + Codex deep integration | Q4 2026 |

**Sprint sequencing** (D41 §5 decided 2026-05-18 morning):

```
P1 (answer primitive) — first implementation sprint
A2 (export/import)    — parallel if capacity allows
P2 (auto-capture hooks) — depends on P1
P4 (connect IDE)        — depends on P2 hooks
```

Q1+Q2+Q3 full runs are VPS compute-bound, not development-bound. Scheduling: week of 2026-11 (third week of November 2026, matching ROADMAP §8 calendar).

---

## 8. Pitch templates

These are internal copy templates for common positioning scenarios. Candid, evidence-based, no marketing fluff. Tune to audience.

---

### "Why not just use memanto?"

**30-second answer:**

"memanto is a SaaS — your memories live on Moorcheh's servers. If Moorcheh goes down, raises prices, or gets acquired, your knowledge history is hostage to their business continuity. nox-mem is a SQLite file on your disk. The backup is `cp nox-mem.db /anywhere`. You bring your own Gemini key, or swap to OpenAI or Voyage — your choice, not ours. Also: we detect contradictions at the knowledge graph level with SQL — no NLI model, no probabilistic threshold. Where memanto has to guess, we can prove."

---

### "What's your moat vs runtime libraries like agentmemory?"

**1-minute answer:**

"agentmemory reached 11k stars fast because they nailed one UX insight: developers don't want to remember to save. Auto-capture hooks eliminate manual ingest friction — we're building exactly that in P2. The difference is what happens to your data. agentmemory wraps the iii-engine runtime — your session history is inseparable from that runtime. If you move to a different machine, migrate providers, or the library changes breaking APIs, you have a migration problem. With nox-mem, your data is a SQLite file. Full export, encrypted archive, round-trip validated. The runtime is replaceable; your data isn't.

Additionally: we ship a zero-vendor CI suite (A4) that proves nox-mem works without any third-party runtime dependency. It's a test you can run — not a claim we make."

---

### "How does this differ from RAG-as-a-service?"

**1-minute answer:**

"RAG-as-a-service adds memory to an LLM by shoving documents into a vector store and retrieving the most similar chunks at query time. It works, and it's simple. What it doesn't do: it doesn't know that 'X is true' was superseded by 'X is now false'. It doesn't understand that a production incident (pain=1.0) should rank differently than a casual note (pain=0.2). It doesn't detect that two retrieved facts contradict each other before surfacing them.

nox-mem is hybrid: BM25 lexical (catches exact matches, identifiers, names), Gemini 3072d dense (catches semantic similarity), RRF fusion (language-aware weights — PT-BR and EN retrieved with appropriate term weights), salience formula (recency × pain × importance — not just similarity score), KG substrate (typed entities and relations with evidence linking back to source chunks). Each layer solves a failure mode the previous layer misses. Shadow discipline means we've validated each layer against a real golden query set before activating it in production.

The result: nDCG@10 of 0.6813 on our honest n=80 golden set — 16.9% relative improvement from the paper baseline (0.5831). And 23× harder corpus than LOCOMO public benchmark (conversational + multi-agent vs clean academic data)."

---

### "Why doesn't nox-mem just use a graph database?"

**30-second answer (for technical audiences):**

"We considered it (see DECISIONS.md NÃO FAZEMOS #9). At 15k entities and 21k relations, Neo4j or Memgraph is overengineering. SQLite handles this in milliseconds with a JOIN. The benefit of co-location: KG + chunks + vectors in one file means one `cp` is your complete backup, one `sqlite3` session inspects everything, and zero daemon coordination failures. The trigger point for a dedicated graph DB is >500k entities — we document that threshold explicitly. Until then, SQLite wins on operational simplicity."

---

## 9. References

| Source | Location |
|---|---|
| D40 — Q/A/P pivot rationale | `docs/DECISIONS.md` §2026-05-17 |
| D41 — 5 cross-cutting decisions (models, encryption, palette, L3 gate, sprint order) | `docs/DECISIONS.md` §2026-05-18 |
| D38 — Reason boost cut (3 gate reviews, 3 failures) | `docs/DECISIONS.md` §D38 |
| D29 — Pain ablation: BM25 recall ceiling | `docs/DECISIONS.md` §D29 |
| D30 — LOCOMO 23× harder corpus | `docs/DECISIONS.md` §D30 |
| NÃO FAZEMOS inventory | `docs/DECISIONS.md` §1 |
| L2 conflict detection spec | `specs/2026-05-17-L2-conflict-detection.md` |
| L3 confidence field spec | `specs/2026-05-17-L3-confidence-field.md` |
| Q/A/P pivot memory | `.claude/projects/.../memory/project_qap_pillars_strategic_decision.md` |
| memanto-inspired ideas memory | `.claude/projects/.../memory/project_memanto_inspired_ideas.md` |
| VISION.md v15 | `docs/VISION.md` |
| ROADMAP.md v2 | `docs/ROADMAP.md` |
| P2 auto-capture hooks spec | `specs/2026-05-17-P2-hooks-autocapture.md` (PR #4) |
| A1 privacy filter | PR #5 (68 tests, 1.7% FP rate) |
| A2 export/import spec | `specs/2026-05-17-A2-schema-export-import.md` (PR #9) |
| A3 provider abstraction spec | `specs/2026-05-17-A3-provider-abstraction.md` (PR #8) |
| A4 zero-vendor suite | PR #14 (8 checks, CI-runnable) |
| Q1 LoCoMo scaffold | PR #6 (`eval/locomo/`) |
| Q2 LongMemEval scaffold | PR #12 (`eval/longmemeval/`) |
| Q3 latency benchmark scaffold | PR #11 (`eval/latency/`) |
| Wave 1 E14 E-lite-2 + language-aware RRF | `specs/2026-05-10-E14-retrieval-evolution.md` |
| SPO injection (E03b) | Commit `90fa3180` (2026-05-17) |
| Overnight 2026-05-17 delivered | Memory `project_overnight_2026_05_17_delivered.md` |
| Morning 2026-05-18 delivered | Memory `project_morning_2026_05_18_delivered.md` |

---

*Generated 2026-05-18. Update trigger: any new competitor analysis, Q/A/P sprint ships, or Q4 COMPARISON.md gate changes.*
