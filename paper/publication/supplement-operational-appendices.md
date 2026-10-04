# Supplement — Operational appendices (C–G)

> Removed from `paper/paper-tecnico-nox-mem.md` on 2026-09-09 and preserved here
> **verbatim**, 874 words. Nothing was rewritten or condensed.

## Why these were moved out

The four operational appendices (MCP interface, HTTP API, cron/backup schedule, dashboard
integration) document *how the deployment is wired*, not *what was measured*. A comparison
against four agent-memory papers the arXiv accepted in 2026 found **none of them carries
any appendix**; five operational appendices read as product documentation rather than as a
paper, and that form — not the rigor — was the measured outlier.

⚠️ **This move buys form, not length.** C–G are **874 words of 28,862 = 3.0%** of the
manuscript. An earlier measurement put the appendices at 3,067 words; that was wrong,
because the block boundary was "next appendix heading **or end of file**" and the end of
file swallowed the *References and Footnotes* section. Re-measured with every level-2
heading as a boundary. Shortening the paper to the canonical 10–12k words is a separate
problem, in the body.

## Why they were copied here rather than pointed at existing docs

Appendix G (Evolution History) looked redundant with `docs/EVOLUTION.md`, which covers
**v1.0 → v3.7b** against the appendix's **v1.0 → v3.7** — a superset by version label.
Measured by *content*, the overlap is **5%**: the appendix is a compact
`version | date | features` table and the doc is prose. Version-label overlap is not
content coverage, and pointing at `docs/EVOLUTION.md` would have destroyed the table.

A search of `docs/*.md` for the material of appendices D (HTTP API) and E (cron/backup)
returned **nothing** — those two had no home in the repository at all. Removing them
without this file would have deleted the only copy.

---

## Appendix C. MCP Server Interface

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

## Appendix D. HTTP API Server

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

## Appendix E. Operational Infrastructure

### E.1 Cron Schedule

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

### E.2 Backup Strategy

Three backup mechanisms operate independently:

1. **SQLite Online Backup**: Uses better-sqlite3's backup API for crash-consistent copies. Daily at 02:00, 7-day retention with automatic pruning.
2. **Git Auto-Commit**: Memory directory changes are committed every 6 hours, providing full change history.
3. **File System**: WAL mode ensures database consistency during concurrent reads/writes.

### E.3 LLM Fallback Chain

To ensure continuous operation regardless of provider availability:

**Paid Tier**: Claude Opus → Sonnet → Haiku → GPT-5.1 → Gemini 2.5
**Free Tier**: Nemotron → Groq Llama70B → Healer → Hunter → Trinity → Gemma27B

The fallback is configured in the environment and selected at runtime based on task complexity and availability.

---

## Appendix F. Dashboard Integration

The TotoClaw Command Center (React 18 + TypeScript + Vite + shadcn/ui) provides 11 pages including 4 nox-mem-specific views:

- **Memory Health** (`/memory`): Real-time system stats, vector coverage progress bar, service status indicators, agent breakdown table
- **Knowledge Graph** (`/knowledge-graph`): Interactive force-directed canvas graph, entity type filters, BFS path finder
- **Agent Intel** (`/agent-intel`): Agent expertise cards with type distribution bars, hybrid search interface, cross-agent knowledge entities
- **System Paper** (`/system-paper`): Live technical analysis with Recharts visualizations (pie, bar, radar, area charts), auto-refresh every 60 seconds

All data is fetched from the nox-mem API server via TanStack React Query with configurable polling intervals.

---

## Appendix G. Evolution History

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
| G10 Hard Mutex | May 20 | `section/source_type` mutex deployed against `g9.db` 69,495 chunks (PRs #181 / #182) |
| G10d ACTIVE-T2 | May 21 | Conditional mutex gated by `query_entity_count <= 2`, deployed via systemd drop-in `NOX_MUTEX_QUERY_ENTITY_THRESHOLD=2` (PR #198, decision D51); multi-hop +1.58% nDCG / adversarial +3.04% nDCG recovered |
| F10 Phase A + B | May 21 | Foundation observability dashboards (`/observability/health.html` + `/observability/evals.html`) deployed via Tailscale tunnel (PRs #207 / #212, decision D53) |

---

## §S3.5 Session priming — the full measured account

> Taken out of §3.5 of `paper/paper-tecnico-nox-mem.md` on 2026-10-04 (v1.0.3, part E) to keep the manuscript's reference density above its floor after the audit corrections added text; §3.5 keeps a summary with the same numbers. The three paragraphs below are reproduced without change.

**An honest measurement, and a methodology caveat.** Running priming in production (6 agents + shared workspace store, ~6.7k serves/day) surfaced a failure mode worth reporting. Over a clean 7-day window the brief served only **83 distinct chunks across 46.8k serves (0.18% diversity)**, median content age 48 days: salience, dominated by importance and the high pain of old incidents, produces a near-static top set, and recently-written content (the very output the loop produces) rarely enters — we measured **931 recent (<=7d), relevant chunks (importance >= 0.7 or pain >= 0.7) that were never once served**. More instructive was a *negative* result on evaluation: we could not measure a downstream "follow-up rate" (does a primed chunk get used later?) because the signal does not exist — in 7 days there were **3 genuine searches and 0 `answer` calls**. This is structural, not a logging gap: priming-by-injection delivers the knowledge *into the context window*, so the agent does not re-query what it already holds. **The utility of an injection-based primer is therefore a property of the served set (diversity, freshness, coverage of what matters) — not of downstream re-retrieval.** Memory work that imports a re-query metric from RAG-style retrieval will mis-evaluate this class of mechanism.

**Diversity term (D2).** The fix follows the same discipline as §3.4.3: it does **not** fork `calculateSalience` (that would alter search too) — it is a re-rank *inside the brief only*. (A) a novelty penalty `brief_score = salience - min(P_max, lambda*log1p(n_serves))` reads `brief_log` to demote over-served chunks, saturating in log so serving 2,000x ~= serving 100x; (B) a freshness quota reserves F of the N slots for recent, relevant, not-yet-served content (a separate query — the candidate pool, ranked by importance and access, structurally excludes `access_count = 0` newcomers). A **high-pain floor** makes incidents with `pain >= 0.9` immune to both demotion and displacement: diversity must not hide the critical. Per the shadow-discipline rule (§3.4.3, §5), the term ships behind `NOX_BRIEF_DIVERSITY = off | shadow | active`, default off and bit-identical to the prior behavior; it is validated in shadow (logging the would-enter/would-leave diff against a per-day gate: diversity up, median age down, floor preserved, churn non-thrashing) before any flip to active. Notably, the shadow gate itself caught a design bug on its first run — the freshness quota was displacing `pain = 1.0` incidents — which the floor now prevents; the active-mode measurements are reported in the next paragraph.

**Active-mode validation surfaced a second, subtler failure — and the fix unifies the two slots.** Two refinements followed the first gate. First, the freshness query as scoped (`global+agent`) only ever saw `sessions/<agent>/%`, never the curated `memory/entities/%` store, so freshly-consolidated lessons and decisions were structurally invisible to every brief; a *split-slot* interleave (one agent-recent plus one curated-global per brief, with its own age window) restored that channel. Second — and this is the instructive part — once the curated channel was live in `active`, a 24-hour gate showed the global slot serving **190 distinct curated chunks on day one, then exactly 1 per day thereafter**. The cause was the slot's *hard* anti-repeat (`id NOT IN brief_log` over a 72h window): under production volume (~6.7k briefs/day) over a 189-chunk eligible pool, the entire pool is served — and thus excluded — within a single day, after which the slot dries up and fails open to the static salience top-1 for the remaining 72h. The first remedy *seemed* obvious: replace hard exclusion with the soft novelty penalty already used by the primary pool (mechanism A) — serving a curated chunk *demotes* it by `lambda*log1p(n_serves)` (capped at `P_max = 0.15`) rather than *removing* it, with the high-pain floor keeping critical incidents immune. Active-mode measurement refuted it: the 24-hour gate fell **146 → 67 → 3 distinct curated chunks per day** over three successive days. The cap was the flaw — `P_max` (0.15) is smaller than the base-salience gap between the pool's few high-salience outliers (decisions at importance 0.9 with high access counts) and its homogeneous body, so once the penalty saturated (within one 72h window under production volume) the pick reconverged to the static salience top-*k*. A bounded soft penalty cannot out-vote an unbounded salience gap. The fix that held ranks the slot not by *count* of prior serves but by *time since last serve* (mechanism B', coverage-sampling): never-served first, then least-recently-served, tie-broken by salience. Having no ceiling, it sweeps the entire pool continuously regardless of the salience gap. The first full post-deploy 24-hour active gate (2026-06-27, ~6.8k briefs/day) confirmed it: **184 of 184 eligible entity files served (100% pool coverage), 190 distinct curated chunks, ~45 distinct chunks rotated per hour — sustained, not a day-one burst** (the cumulative distinct count reached 190 within four hours of deploy and held flat through hour 24; the pool is swept fast and then re-cycled by recency rather than exhausted). The general lesson — **hard de-duplication under volume >> pool produces bursty rotation; a *saturating* soft penalty silently reconverges once its cap falls below the salience gap; only coverage-by-recency-of-serve, which has no ceiling, produces true continuous rotation** — is the kind of finding only a shadow→active→measure loop on real traffic exposes. An offline diversity metric on a static corpus would have scored all three designs identically, and the saturating-penalty regression in particular would have been invisible without a multi-day active gate.

---

## §S5.7.4 Observability layer

> Taken out of §5.7.4 of `paper/paper-tecnico-nox-mem.md` on 2026-10-04 (v1.0.3, part G) as deployment documentation rather than a measured result (review finding A2). Reproduced without change.

The F10 observability layer (Phase A: `/observability/health.html`; Phase B: `/observability/evals.html`) renders the full G3→G10d ablation trajectory in real time over Chart.js, with an annotation at each recorded decision gate. Three rollback paths are documented (conditional layer only, full mutex, drop-in removal), each executable in under five minutes.

---

## §S5.8.4 Search error rate monitoring

> Taken out of §5.8.4 of `paper/paper-tecnico-nox-mem.md` on 2026-10-04 (v1.0.3, part G; review finding A2). In the manuscript the next two subsections were renumbered §5.8.4 and §5.8.5. Reproduced without change; "Lab Q1" is the internal name of the standalone retrieval-knob runs of §5.1.8.

Concurrent agent operations during Lab Q1 benchmarking caused a batch contamination incident (batch 010): a concurrent agent re-installed its adapter mid-run, contaminating results. Recovery via merged adapter pattern. Lesson: shared adapter install paths on VPS are a race condition; sequential dispatch and 0/n search-error-per-batch monitoring are mandatory before accepting 5-batch results.

---

## §S6.8 Competitor RAM, cold start and setup steps — author's estimates, not measurements

> Taken out of Table 2 (§6.8) of `paper/paper-tecnico-nox-mem.md` on 2026-10-04 (v1.0.3, part G; review finding M8). Table 2 now carries only what is read from each system's source or documentation (services, mandatory keys). The figures below for systems other than nox-mem are the **author's estimates**: no run on a single host measured them, a published docker-compose file does not state an idle resident set, and no source is held for the competitors' cold-start times. They are kept here so the earlier table can be checked, not as evidence. The "~10× less RSS" headline that rested on the EverOS estimate is withdrawn.

| System | RAM idle | Cold start | Setup commands | Basis |
|---|---:|---:|---:|---|
| nox-mem | 399 MB RSS, **measured** 2026-05-29 (§5.7.3) | <1 s (no archived artifact) | 2 (`npm i`, `nox-mem reindex`; earlier tables counted this as 1) | `benchmark/latency-cost/results/RESULTS-PRODUCTION-SOTA.json` |
| mem0 | ~800 MB (estimate) | ~15 s (estimate) | ~5 (estimate) | docker-compose defaults and documentation |
| Letta | ~1.5 GB (estimate) | ~30 s (estimate) | ~8 (estimate) | self-host guide |
| Zep OSS | ~1.2 GB (estimate) | ~30 s (estimate) | ~6 (estimate) | v0.27.2 source and compose file; Zep was run on 2026-09-10 (§6.3.4) but its footprint was not measured |
| EverOS (docker-compose, as of 2026-06-15) | ~4 GB+ (estimate: sum of documented minimum requirements for each service's container) | ~60 s (estimate) | ~15+ (estimate) | EverMind-AI docker-compose as of 2026-06-15 (no longer at the repository root, checked 2026-09-10) |
| LightRAG | not estimated | not estimated | ~6 (estimate) | LightRAG source defaults |

A side-by-side measurement of these footprints on one controlled host is future work.
