# nox-mem Glossary

> Terms reference for developers, researchers, and ML enthusiasts landing on this project.
> Jump in at any point — a blog post, an HN thread, a README scan — and look up unfamiliar terms here.
> Entries are alphabetical. Where a term has a deeper explanation elsewhere in `docs/`, that link is included.

---

## §1 How to use this glossary

Alphabetical reference. Each entry gives a tight definition and a concrete example drawn from nox-mem itself. Cross-links point to the canonical doc where the concept lives in full detail. If a term appears in the paper, the §-reference is noted. For acronym expansions alone, skip to [§3 Acronyms](#3-acronyms).

---

## §2 Glossary

### Ablation

**Definition.** A controlled experiment that removes or isolates one scoring/retrieval component at a time to measure its individual contribution to a metric (nDCG@10, MRR).

**Example.** The G-series runs (G3 through G12 R3 + G10d) each toggle one boost — section_boost, source_type_boost, salience, temporal anchor — and compare nDCG@10 against the same corpus and golden set before concluding whether to keep or discard the change.

**See also:** [docs/DECISIONS.md](DECISIONS.md), [docs/ROADMAP.md](ROADMAP.md), paper §4.

---

### Active mode (salience)

**Definition.** `NOX_SALIENCE_MODE=active` — pain-weighted salience scores are computed and actually applied to retrieval ranking. Contrast with shadow mode (logs only) and off (formula disabled).

**Example.** After 7+ days of shadow-mode validation showing neutral or positive delta, G10d deploy was promoted to active; the API's `/api/health` endpoint exposes `salience.mode` to confirm the current setting.

**See also:** [shadow mode](#shadow-mode-salience), [Pain-weighted salience](#pain-weighted-salience), [docs/DECISIONS.md](DECISIONS.md).

---

### Append-only audit

**Definition.** The `ops_audit` table is protected by database triggers that reject DELETE and UPDATE on rows that have reached a terminal status, making the audit log deletion-proof at the SQL layer.

**Example.** A `withOpAudit()` call that ends in `'success'` cannot be overwritten by a subsequent UPDATE, preventing silent history tampering (CWE-693 mitigation).

**See also:** [withOpAudit](#withopaudit), [docs/DECISIONS.md](DECISIONS.md).

---

### BM25

**Definition.** Best Match 25 — the probabilistic relevance function introduced by Robertson & Sparck Jones (1976) and refined through TREC. SQLite FTS5 uses BM25 as its default ranking function for keyword search.

**Example.** A query `"production outage 403"` goes through FTS5's BM25 scorer, returning chunks that contain these exact tokens with term-frequency/inverse-document-frequency weighting, before the result list is fused with the dense semantic results via RRF.

**See also:** [FTS5](#fts5), [Hybrid search](#hybrid-search), [RRF](#rrf-reciprocal-rank-fusion), paper §3.1.

---

### Chunk

**Definition.** The atomic unit of memory in nox-mem — a text segment of roughly 256–1024 characters that is ingested, indexed in FTS5, embedded as a dense vector, and retrievable as a search result.

**Example.** Ingesting a 4,000-character incident report splits it into ~6 chunks. Each chunk carries metadata: `source_type`, `pain`, `importance`, `section`, `retention_days`, `access_count`. The live production instance holds 68,995 chunks (as of 2026-05-19).

**See also:** [docs/ARCHITECTURE.md](ARCHITECTURE.md) §3, paper §2.

---

### Conditional Hard Mutex (G10d)

**Definition.** A scoring rule that blocks `section_boost` and `source_type_boost` from both applying simultaneously, but only when the number of entities detected in the query (`query_entities`) is at or below the threshold set by `NOX_MUTEX_QUERY_ENTITY_THRESHOLD` (default: 2). When the query is entity-dense (>2 entities), both boosts are permitted.

**Example.** A single-hop query "what is the salience formula?" has 1 entity — the mutex fires, and only one boost applies, preventing double-counting. A multi-hop query referencing three entities bypasses the mutex.

**See also:** [section_boost](#section--section_boost), [source_type_boost](#source_type_boost), [docs/DECISIONS.md](DECISIONS.md) D51.

---

### Cross-encoder reranker

**Definition.** A neural model that scores each (query, document) pair jointly — rather than comparing pre-computed embeddings — yielding more accurate relevance scores at the cost of higher latency per candidate.

**Example.** A cross-encoder reranker is parked in Lab Q1 as a potential fourth retrieval layer on top of RRF fusion; expected nDCG@10 gain is +3–8% based on published results (e.g., MS-MARCO SBERT benchmarks).

**See also:** [Hybrid search](#hybrid-search), [RRF](#rrf-reciprocal-rank-fusion), [docs/ROADMAP.md](ROADMAP.md).

---

### D## (Decision)

**Definition.** A formal, numbered decision record in `docs/DECISIONS.md`. Each D-record documents the option space, the chosen path, and the explicit "NÃO FAZEMOS" (things explicitly ruled out) to prevent re-litigating settled choices.

**Example.** D43 set the Q4 benchmark gate threshold (≥+15% nDCG@10 over baseline) that unlocked Phase 2 GTM. D51 formalized the G10d conditional mutex.

**See also:** [docs/DECISIONS.md](DECISIONS.md).

---

### Defense hook

**Definition.** A global git pre-commit hook (`~/.git-hooks-global/pre-commit`) that aborts a commit if the parent repository's HEAD is not on `main`, preventing multi-agent worktree branch leaks from contaminating the main session.

**Example.** If an agent's worktree accidentally checks out a feature branch and then commits, the hook fires with an error. The override is `COMMIT_TO_NON_MAIN_OK=1 git commit ...` for intentional feature-branch commits.

**See also:** [docs/DECISIONS.md](DECISIONS.md).

---

### Entity file

**Definition.** A structured markdown file under `memory/entities/<type>/<slug>.md` that describes a named entity (person, project, lesson, incident, decision, etc.). The file has three sections — `frontmatter` (YAML metadata), `compiled` (canonical truth), and `timeline` (dated events) — which are each ingested as separately-boosted chunks.

**Example.** `memory/entities/project/nox-mem.md` compiles everything nox-mem-related: version milestones, architectural decisions, benchmark results. Ingesting it produces N+2 chunks with `section_boost` applied per section.

**See also:** [section_boost](#section--section_boost), [docs/CONVENTIONS.md](CONVENTIONS.md), [docs/DECISIONS.md](DECISIONS.md).

---

### EverMemBench

**Definition.** A standardized memory benchmark published by EverMind-AI (5k+ GitHub stars), analogous to LongMemEval but with a public dataset and leaderboard. Running nox-mem against EverMemBench is a Lab Q1 priority to close the benchmark-gap narrative.

**Example.** Competitors publish EverMemBench scores in their READMEs. Matching their reporting format with isolated eval infra (separate DB, separate golden set) is the prerequisite before any comparative claim.

**See also:** [LongMemEval](#longmemeval), [docs/ROADMAP.md](ROADMAP.md).

---

### F10 dashboards

**Definition.** The observability frontend introduced in sprint F10. Phase A delivers `/observability/health.html` — a live production snapshot showing chunk counts, vector coverage, salience mode, and 24h delta. Phase B delivers `/observability/evals.html` — an annotated history of G-series ablation results.

**Example.** After the G10 deploy, the Phase A dashboard confirmed vector coverage stayed at 100% and salience mode flipped from shadow → active within the expected time window.

**See also:** [docs/ARCHITECTURE.md](ARCHITECTURE.md) §2 (observability block).

---

### FTS5

**Definition.** SQLite's Full-Text Search version 5 — a built-in virtual table that indexes text and supports BM25-ranked keyword search, phrase queries, and prefix matching. It is nox-mem's Layer 1 (keyword) retriever.

**Example.** `nox-mem search "error code 403"` routes to FTS5 first. The Unicode-aware tokenizer (regex `[^\p{L}\p{N}\s]` stripping) ensures Portuguese and accented characters tokenize correctly before BM25 scoring.

**See also:** [BM25](#bm25), [Hybrid search](#hybrid-search), [docs/ARCHITECTURE.md](ARCHITECTURE.md) §3.

---

### G-series (Ablations)

**Definition.** The numbered sequence of pre-registered retrieval ablation experiments — G3 through G12 R3 plus sub-experiments G10b/c/d — each testing one scoring change against a fixed corpus and golden query set with nDCG@10 and MRR as primary metrics.

**Example.** G5 V3 A8 is the canonical configuration currently deployed: section_boost + source_type_boost + Hard Mutex. It achieved +78.8% nDCG@10 vs the G3 baseline (0.6237 on entity-eval-v2, n=100).

**See also:** [Ablation](#ablation), [Conditional Hard Mutex (G10d)](#conditional-hard-mutex-g10d), [docs/ROADMAP.md](ROADMAP.md).

---

### Gemini embedding

**Definition.** Google's `gemini-embedding-001` model producing 3072-dimensional dense embeddings; the default embedding provider in nox-mem. All chunks are embedded and stored in the `vec_chunks` sqlite-vec table.

**Example.** Semantic search issues a single `gemini-embedding-001` call (~800ms, the dominant latency cost), then runs cosine similarity via sqlite-vec over the 3072d vectors, returning top-K candidates that are fused with BM25 results via RRF.

**See also:** [sqlite-vec](#sqlite-vec), [Hybrid search](#hybrid-search), [docs/ARCHITECTURE.md](ARCHITECTURE.md) §4, [docs/CONFIGURATION.md](CONFIGURATION.md).

---

### Hard Mutex

**Definition.** A scoring rule that prevents two boost signals from both contributing to a chunk's final score in the same query evaluation. "Hard" means the exclusion is binary — one boost is zeroed out entirely, not attenuated.

**Example.** The mutex between `section_boost` and `source_type_boost` was introduced after G9 confirmed that stacking both signals redundantly degraded performance on multi-hop queries. G10 validated that the mutex raised nDCG@10 +0.79% and MRR +2.65% vs no-mutex on the production corpus.

**See also:** [Conditional Hard Mutex (G10d)](#conditional-hard-mutex-g10d), [section_boost](#section--section_boost), [source_type_boost](#source_type_boost).

---

### Hybrid search

**Definition.** nox-mem's three-layer retrieval architecture: Layer 1 FTS5 BM25 (keyword), Layer 2 sqlite-vec cosine (semantic dense), and Layer 3 RRF fusion (rank merging). All three layers run in parallel per query and their ranked lists are merged.

**Example.** `nox-mem search "salience formula weights"` simultaneously queries FTS5 for lexical matches and sqlite-vec for semantic neighbors, then combines the two ranked lists using RRF at k=60 to produce a single result list stronger than either strategy alone.

**See also:** [BM25](#bm25), [FTS5](#fts5), [sqlite-vec](#sqlite-vec), [RRF](#rrf-reciprocal-rank-fusion), [docs/ARCHITECTURE.md](ARCHITECTURE.md) §4, paper §3.

---

### importance

**Definition.** A per-chunk REAL column in the `chunks` table (range 0.0–1.0, default 0.5) that records how significant the memory is, independently of its recency or pain severity.

**Example.** A foundational architectural decision might be tagged `importance=0.9` — ensuring it surfaces above routine daily notes even when both were created at the same time. In the salience formula, `importance` carries weight W_I=0.55 (the largest weight).

**See also:** [Pain-weighted salience](#pain-weighted-salience), [pain](#pain-salience).

---

### KG / Knowledge Graph

**Definition.** A graph of named entities (`kg_entities`) and their typed relations (`kg_relations`) extracted from chunks by Gemini 2.5 Flash via nightly incremental cron. The KG enables path-based queries and cross-entity retrieval unavailable to flat chunk search.

**Example.** `nox-mem kg-path "nox-mem" "sqlite-vec"` traverses the KG to find how the project connects to its vector storage dependency, returning intermediate entities (e.g., `vec_chunk_map`, `hybrid search`) along the path.

**See also:** [docs/ARCHITECTURE.md](ARCHITECTURE.md) §5, paper §2.3.

---

### LightRAG

**Definition.** Guo et al. (HKU, EMNLP 2025 / arXiv:2410.05779); a KG-augmented RAG system with an incremental entity merge pattern where an LLM summarizes duplicate entity descriptions into a single canonical entry. 35k GitHub stars, MIT licensed.

**Example.** nox-mem references LightRAG's incremental merge pattern as a potential Lab Q1 upgrade path when KG entity density grows beyond ~10× the current level.

**See also:** [KG / Knowledge Graph](#kg--knowledge-graph), [docs/ROADMAP.md](ROADMAP.md).

---

### LongMemEval

**Definition.** A long-horizon memory evaluation set used in nox-mem's Q4 COMPARISON.md study (n=100 queries, oracle-validated). Results as of 2026-05-19: nDCG@10 D2 = 0.9126, MRR = 0.9162 on the production hybrid stack.

**Example.** The Q4 gate (D43) required ≥+15% nDCG@10 vs baseline to unlock Phase 2 GTM. LongMemEval oracle results showed +18.8%, clearing the gate.

**See also:** [EverMemBench](#everembench), [docs/ROADMAP.md](ROADMAP.md), paper §5.

---

### Mem0 / Zep / Letta / agentmemory / EverMind-AI

**Definition.** The five competitors benchmarked in nox-mem's published comparison. Each uses a different memory architecture: Mem0 and Zep are hosted-API vector-first systems; Letta (MemGPT origin) uses in-context paging; agentmemory is a lightweight local library; EverMind-AI is the publisher of EverMemBench.

**Example.** `docs/COMPARISON.md` shows nox-mem's feature breakdown vs all five across dimensions: retrieval strategy, data ownership, benchmark methodology, latency, and cost.

**See also:** [docs/COMPETITIVE-ANALYSIS-2026-05-19.md](COMPETITIVE-ANALYSIS-2026-05-19.md), [EverMemBench](#everembench).

---

### Pain (salience)

**Definition.** A REAL column in `chunks` (DEFAULT 0.2) encoding the severity of the memory's associated incident or context, on a scale from 0.1 (trivial) to 1.0 (production outage). It is one of three inputs to the salience formula alongside recency and importance.

**Example.** A note about a p0 database wipe receives `pain=1.0`; a routine daily standup summary receives `pain=0.1`. The difference causes the incident chunk to rank above the standup note even if the standup was ingested more recently.

**See also:** [Pain-weighted salience](#pain-weighted-salience), [docs/DECISIONS.md](DECISIONS.md) D48.

---

### Pain-weighted salience

**Definition.** nox-mem's core scoring formula: `salience = W_R·recency + W_P·pain + W_I·importance + W_A·access_count`, with default weights (W_R=0.15, W_P=0.10, W_I=0.55, W_A=0.20). The formula biases retrieval toward memories that were important and frequently accessed, not merely recent.

**Example.** A critical architectural decision (importance=0.9, pain=0.8, access_count=12) scores far above a one-off note (importance=0.3, pain=0.1, access_count=1) even if the note is twice as recent. Shadow mode lets you observe the formula's ranking influence before enabling it.

**See also:** [Active mode (salience)](#active-mode-salience), [shadow mode](#shadow-mode-salience), [pain](#pain-salience), [importance](#importance), [docs/DECISIONS.md](DECISIONS.md) D48, paper §3.3.

---

### RRF (Reciprocal Rank Fusion)

**Definition.** Cormack, Clarke & Buettcher (SIGIR 2009) rank fusion algorithm. Given N ranked lists, each document's fused score is `sum(1 / (k + rank_i))` across all lists. Robust to score-scale differences between heterogeneous retrievers. nox-mem uses k=60.

**Example.** BM25 ranks chunk A at position 3 and chunk B at position 12; sqlite-vec ranks chunk B at position 1 and chunk A at position 15. After RRF (k=60): score(A) = 1/63 + 1/75 ≈ 0.029; score(B) = 1/72 + 1/61 ≈ 0.030. Chunk B wins — semantic signal rescued it from low BM25 rank.

**See also:** [Hybrid search](#hybrid-search), [BM25](#bm25), [sqlite-vec](#sqlite-vec), paper §3.2.

---

### Section / section_boost

**Definition.** The `section` column on `chunks` records which section of an entity file a chunk came from: `compiled` (canonical truth), `frontmatter` (YAML metadata), `timeline` (dated events), or `NULL` (plain markdown, no entity). `section_boost` is a REAL multiplier applied during scoring: 2.0 (compiled), 1.5 (frontmatter), 0.8 (timeline), 1.0 (NULL/default).

**Example.** When searching for the canonical definition of a project, compiled-section chunks (boost 2.0) outrank the same entity's timeline entries (boost 0.8), ensuring the authoritative section surfaces first.

**See also:** [Entity file](#entity-file), [Conditional Hard Mutex (G10d)](#conditional-hard-mutex-g10d), [docs/ARCHITECTURE.md](ARCHITECTURE.md) §3.

---

### Shadow mode (salience)

**Definition.** `NOX_SALIENCE_MODE=shadow` — the salience formula is computed and logged to the telemetry table on every query, but its scores are not factored into the retrieval ranking returned to callers. Allows ≥7-day observation before activating the formula.

**Example.** After deploying the pain-weighted formula (D48), shadow mode ran for 7+ days. Query-level salience scores were visible at `/api/health.salience` without affecting production retrieval, confirming the formula had neutral-to-positive effect before the switch to active.

**See also:** [Active mode (salience)](#active-mode-salience), [Pain-weighted salience](#pain-weighted-salience).

---

### Snapshot pre-op

**Definition.** An atomic SQLite backup (`VACUUM INTO`) created by `withOpAudit()` before any destructive operation (reindex, consolidate, crystallize, kg-prune). Stored at `/var/backups/nox-mem/pre-op/<op>-<ts>-<pid>-<uuid>.db`, retained 7 days, accessible only to the nox-mem process (0600 ACL).

**Example.** Before a `nox-mem reindex`, `withOpAudit()` snapshots the live DB. If the reindex corrupts the `section` column (as occurred in the 2026-04-25 incident), `safeRestore()` can roll back from the snapshot in under 2 minutes.

**See also:** [withOpAudit](#withopaudit), [Append-only audit](#append-only-audit), [docs/INCIDENTS.md](INCIDENTS.md).

---

### source_type_boost

**Definition.** A per-source-type REAL multiplier (stored in `chunks.source_type`) that scales the final chunk score based on the category of memory: entity, lesson, decision, incident, etc. Canonical defaults are defined in `src/search/boosts.ts`.

**Example.** `decision` chunks receive a higher boost than `daily` chunks, ensuring that formal architectural decisions surface above routine log entries in mixed-type result sets.

**See also:** [section_boost](#section--section_boost), [Conditional Hard Mutex (G10d)](#conditional-hard-mutex-g10d), [docs/ARCHITECTURE.md](ARCHITECTURE.md) §3.

---

### sqlite-vec

**Definition.** Alex Garcia's MIT-licensed SQLite extension that adds a `vec0` virtual table for fast cosine-similarity search over dense float vectors. nox-mem uses it as Layer 2 (semantic) retrieval over 3072-dimensional Gemini embeddings.

**Example.** `vec_chunks` stores one `FLOAT[3072]` row per chunk; `vec_chunk_map` bridges `chunks.id ↔ vec_chunks.rowid`. At ~95k chunks × 3072d, the total vector store is ~1.2 GB — still fits in a small VPS alongside the main DB.

**See also:** [Gemini embedding](#gemini-embedding), [Hybrid search](#hybrid-search), [docs/ARCHITECTURE.md](ARCHITECTURE.md) §3.

---

### Temporal anchor / spike

**Definition.** A query-time enrichment layer that detects date references in the query (e.g., "last Tuesday", "in April") and injects a recency bias toward chunks created near that date. The v2 implementation (PR #181) uses regex + median anchor inference with confidence tiers.

**Example.** The query "what did we decide about auth in March?" has a temporal anchor at "March 2026". Without temporal spike, results are dominated by the most-relevant chunks regardless of date. With v2 active, chunks from March receive a rank boost, recovering a +10.37% MRR gain on date-anchored golden queries.

**See also:** [Pain-weighted salience](#pain-weighted-salience), [docs/ROADMAP.md](ROADMAP.md).

---

### Vec coverage

**Definition.** The ratio `embedded / total` chunks that have a corresponding vector in `vec_chunks`. Monitored via `/api/health` → `vectorCoverage`. Production target is 100%.

**Example.** After a batch ingest of 500 new chunks, vec coverage temporarily drops below 100% until the vectorize cron runs. A coverage below 99% is a warning signal; below 95% triggers a manual `nox-mem vectorize` pass.

**See also:** [sqlite-vec](#sqlite-vec), [Gemini embedding](#gemini-embedding), [docs/ARCHITECTURE.md](ARCHITECTURE.md) §2.

---

### withOpAudit

**Definition.** A TypeScript wrapper function in `src/lib/op-audit.ts` that envelopes any destructive database operation with: (1) an atomic pre-op snapshot via `VACUUM INTO`, (2) an `ops_audit` row recording `started_at`, op name, and operator, and (3) a terminal status update (`success` or `failed`) on completion. Mandatory for all destructive ops in production.

**Example.** `await withOpAudit('reindex', async () => { /* reindex logic */ })` creates a snapshot, runs the reindex, and writes the audit row. If the lambda throws, `withOpAudit` writes `status='failed'` and the snapshot remains available for `safeRestore()`.

**See also:** [Snapshot pre-op](#snapshot-pre-op), [Append-only audit](#append-only-audit), [docs/ARCHITECTURE.md](ARCHITECTURE.md) §6.

---

## §3 Acronyms

| Acronym | Expansion |
|---|---|
| API | Application Programming Interface |
| BM25 | Best Match 25 (Robertson & Sparck Jones 1976) |
| CI/CD | Continuous Integration / Continuous Deployment |
| FOSS | Free + Open Source Software |
| FTS5 | Full-Text Search v5 (SQLite built-in) |
| HN | Hacker News |
| IR | Information Retrieval |
| KG | Knowledge Graph |
| LLM | Large Language Model |
| MIT | Massachusetts Institute of Technology (license) |
| MRR | Mean Reciprocal Rank |
| nDCG | normalized Discounted Cumulative Gain |
| OWASP | Open Worldwide Application Security Project |
| PH | Product Hunt |
| RAG | Retrieval-Augmented Generation |
| RRF | Reciprocal Rank Fusion (Cormack et al. 2009) |
| VPS | Virtual Private Server |
| WAL | Write-Ahead Log (SQLite concurrency mode) |

---

## §4 See also

- [README.md](../README.md) — project pitch, quick start, benchmark numbers
- [docs/ARCHITECTURE.md](ARCHITECTURE.md) — full system depth: storage, retrieval layers, KG, observability
- [docs/FAQ.md](FAQ.md) — Q&A for common questions from HN / Reddit / PH visitors
- [docs/USE-CASES.md](USE-CASES.md) — concrete integration patterns (personal assistant, team knowledge base, etc.)
- [docs/DECISIONS.md](DECISIONS.md) — formal D## decision records with rationale and ruled-out alternatives
- [docs/ROADMAP.md](ROADMAP.md) — Q/A/P pillars, Lab track, GTM gates, capacity allocation
- [paper/paper-tecnico-nox-mem.md](../paper/paper-tecnico-nox-mem.md) — formal treatment of retrieval architecture, salience formula derivation, and benchmark methodology
