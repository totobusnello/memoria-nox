# OpenClaw Memory System: Architecture & Technical Deep Dive

**nox-mem v3.0.0 — March 2026**

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

## 5. Knowledge Graph v2

### 5.1 Entity Extraction

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

### 5.2 Temporal Decay and TTL

Relations have a 90-day time-to-live (TTL) from creation. The confidence decay mechanism operates as follows:

1. Relations start with confidence 0.8 (extracted) or 0.9 (confirmed)
2. Every 30 days without re-confirmation, confidence drops by 0.1
3. Relations below 0.3 confidence receive accelerated 7-day expiry
4. Expired relations are deleted during `kg-prune` execution
5. Re-confirmation (observing the same relation in new chunks) resets confidence to 0.9 and extends TTL by 90 days

This mechanism ensures the knowledge graph naturally forgets stale information while reinforcing actively observed patterns.

### 5.3 Decision Versioning

Architectural decisions are tracked with full version history in the `decision_versions` table. Each decision has a unique key (e.g., `dedup-strategy`, `fallback-chain`) and supports:

- Version chains with supersession tracking
- Authorship attribution
- Source file provenance
- Current vs. historical querying

10 decisions are currently tracked, covering API key management, LLM fallback chains, embedding model selection, agent isolation strategy, and synchronization schedules.

### 5.4 Graph Traversal

The `findPath()` function implements BFS (Breadth-First Search) to discover shortest paths between any two entities. This enables queries like "How is Toto connected to nox-mem?" which traverses person → project → tool → agent relationships. Maximum depth is configurable (default: 4 hops).

---

## 6. Cross-Agent Intelligence

### 6.1 Agent Expertise Profiling

Each agent's memory is analyzed to determine its unique expertise based on chunk type distribution. The dominant chunk type determines the agent's strength category:

- **daily** → "Daily operations & activity logging"
- **team** → "Team coordination & shared knowledge"
- **decision** → "Decision tracking & rationale"
- **lesson** → "Lessons learned & pattern recognition"

Profiles include chunk counts, type breakdowns, top topics (via FTS5 term frequency), and last activity dates.

### 6.2 Knowledge Sharing

The `pullInsightsFrom()` function enables any agent to query lessons and decisions from other agents without direct database access. This creates a knowledge transfer mechanism where, for example, Cipher (Security) can learn from Forge's (Code Reviewer) past code review decisions.

`pullAllInsights()` aggregates insights across all agents, sorted by date, providing a fleet-wide learning feed.

### 6.3 Cross-Agent Knowledge Graph Merge

`mergeCrossKnowledgeGraphs()` scans all agent databases for kg_entities and kg_relations tables, merging them into a unified entity view. Entities are matched by type + lowercase name. The output shows which entities are known to which agents and their combined mention counts, enabling identification of shared knowledge vs. agent-specific expertise.

---

## 7. MCP Server Interface

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

## 8. HTTP API Server

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

## 9. Operational Infrastructure

### 9.1 Cron Schedule

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

### 9.2 Backup Strategy

Three backup mechanisms operate independently:

1. **SQLite Online Backup**: Uses better-sqlite3's backup API for crash-consistent copies. Daily at 02:00, 7-day retention with automatic pruning.
2. **Git Auto-Commit**: Memory directory changes are committed every 6 hours, providing full change history.
3. **File System**: WAL mode ensures database consistency during concurrent reads/writes.

### 9.3 LLM Fallback Chain

To ensure continuous operation regardless of provider availability:

**Paid Tier**: Claude Opus → Sonnet → Haiku → GPT-5.1 → Gemini 2.5
**Free Tier**: Nemotron → Groq Llama70B → Healer → Hunter → Trinity → Gemma27B

The fallback is configured in the environment and selected at runtime based on task complexity and availability.

---

## 10. Dashboard Integration

The TotoClaw Command Center (React 18 + TypeScript + Vite + shadcn/ui) provides 11 pages including 4 nox-mem-specific views:

- **Memory Health** (`/memory`): Real-time system stats, vector coverage progress bar, service status indicators, agent breakdown table
- **Knowledge Graph** (`/knowledge-graph`): Interactive force-directed canvas graph, entity type filters, BFS path finder
- **Agent Intel** (`/agent-intel`): Agent expertise cards with type distribution bars, hybrid search interface, cross-agent knowledge entities
- **System Paper** (`/system-paper`): Live technical analysis with Recharts visualizations (pie, bar, radar, area charts), auto-refresh every 60 seconds

All data is fetched from the nox-mem API server via TanStack React Query with configurable polling intervals.

---

## 11. Evolution History

| Version | Date | Key Changes |
|---------|------|-------------|
| v1.0 | Mar 14 | SQLite FTS5, basic search, consolidation, Notion sync |
| v2.0 | Mar 17 | MCP server, systemd services, watcher heartbeat, primer |
| v2.2 | Mar 20 | Cross-agent search, KG v1 (regex), self-improve, decision versioning |
| v2.5 | Mar 22 | Multi-agent workspace fix (OPENCLAW_WORKSPACE), gateway supervision |
| v2.6 | Mar 22 | Hybrid search default (FTS5+Gemini+RRF), 866/866 vectorized |
| v3.0 | Mar 23 | KG v2 (LLM, 384 entities), Cross-Agent Intelligence, HTTP API, dashboard |

---

## 12. Conclusion

nox-mem v3.0.0 demonstrates that persistent, searchable, and shareable memory for AI agent fleets is achievable with commodity infrastructure (single VPS, SQLite, local LLM). The hybrid search system consistently outperforms single-method retrieval, particularly for multilingual content and compound technical terms. The LLM-powered knowledge graph provides 15x richer entity extraction compared to regex approaches, while temporal decay ensures the graph stays current without manual curation.

The cross-agent intelligence layer transforms isolated agent memories into a collaborative knowledge base, enabling institutional learning across the fleet. Combined with the live dashboard, the system provides full observability into the collective memory of the agent organization.

**Repository:** github.com/totobusnello/nox-workspace
**Dashboard:** github.com/totobusnello/agent-hub-dashboard
**Spec:** Projetos/memoria-nox/specs/2026-03-14-nox-memory-system-design.md
