# Q4 COMPARISON — competitor versions + install commands

> Resolved 2026-05-21 overnight. Toto runs Saturday morning. Re-verify each
> pin before install — projects iterate weekly.

Per spec `specs/2026-05-23-Q4-comparison-execution-plan.md` §1, we benchmark
the **default configuration** of each system (no tuning to win). Pinned
versions match the latest stable release available at overnight resolution
time.

---

## 1. nox-mem (self / reference)

| Field | Value |
|---|---|
| Repo | https://github.com/totobusnello/memoria-nox |
| Version pin | current `main` SHA (resolve at run time via `git rev-parse HEAD`) |
| Install | `npm install && npm run build` |
| API surface | HTTP `/api/search` on port 18802 |
| API keys | `GEMINI_API_KEY` |
| Daemon | `node dist/index.js api` (or via `docker compose --profile noxmem`) |

Adapter: `adapters/nox_mem.py` — uses `requests.get(/api/search)`.

---

## 2. Mem0 (mem0ai)

| Field | Value |
|---|---|
| Repo | https://github.com/mem0ai/mem0 |
| License | Apache-2.0 |
| Stars (2026-05-21) | 53k+ |
| Install | `pip install 'mem0ai==0.1.114'` |
| Version pin | `0.1.114` (latest stable on PyPI as of 2026-05-21) |
| Defaults | Chroma vector store (in-process) + OpenAI embeddings |
| API keys | `OPENAI_API_KEY` (mandatory in default config) |
| Optional extras | `pip install 'mem0ai[graph]'` for the graph layer (Neo4j) |

**Pinning rationale:** 0.1.x is stable; 0.2.x branch is unreleased as of
2026-05-21. Default config doesn't need a daemon (Chroma runs in-process),
so the only setup cost is the OpenAI key.

Adapter: `adapters/mem0.py` — `from mem0 import Memory; Memory().search(...)`.

---

## 3. Zep (getzep)

| Field | Value |
|---|---|
| Repo | https://github.com/getzep/zep |
| License | Apache-2.0 |
| Stars (2026-05-21) | 1.8k+ |
| Install (server) | Docker compose — `docker compose -f compose/docker-compose.yml up -d zep postgres` |
| Install (client) | `pip install 'zep-python==2.4.0'` |
| Version pin (server) | `ghcr.io/getzep/zep:0.27.2` |
| Version pin (client) | `zep-python==2.4.0` |
| Defaults | Postgres backend; FastEmbed for local embeddings (no OpenAI required in OSS mode) |
| API keys | None for OSS self-host. `ZEP_API_KEY` only for Zep Cloud variant. |
| Daemon | `zep` + `postgres` containers (see `compose/docker-compose.yml`) |

**Pinning rationale:** Zep 0.27.x is the latest OSS line; 0.28 is roadmapped
but not released. Self-hosted OSS is the fair comparison surface (Cloud is
a paid tier).

Adapter: `adapters/zep.py` — uses `zep_python.client.Zep.memory.search_session`.

---

## 4. Letta (ex-MemGPT, letta-ai)

| Field | Value |
|---|---|
| Repo | https://github.com/letta-ai/letta |
| License | Apache-2.0 |
| Stars (2026-05-21) | 14k+ |
| Install (server) | `pip install 'letta==0.6.6'` then `letta server` OR `docker compose --profile letta up -d` |
| Install (client) | `pip install 'letta-client==0.1.46'` |
| Version pin (server) | `letta==0.6.6` |
| Defaults | SQLite backend; OpenAI embeddings (configurable) |
| API keys | `OPENAI_API_KEY` (mandatory in default config) |
| Daemon | `letta server` on :8283 OR `q4-letta` container |
| Notes | Letta is a full agent runtime; we bench `archival_memory_search` (recall-only) for fair retrieval comparison. |

**Pinning rationale:** 0.6.x is current stable. The bench-only entrypoint
`archival_memory_search` has been stable since 0.5.x.

Adapter: `adapters/letta.py` — uses `letta_client.Letta`.

---

## 5. agentmemory (rohitg00)

| Field | Value |
|---|---|
| Repo | https://github.com/rohitg00/agentmemory |
| License | MIT (CLI) / unclear (iii-engine daemon) |
| Stars (2026-05-21) | 11k+ |
| Install | `npm install -g '@agentmemory/agentmemory'` |
| Version pin | latest npm tag at install time — record output of `agentmemory --version` |
| Daemon | iii-engine runtime (proprietary; license terms unclear) |
| API keys | None on CLI surface; iii-engine may require its own |

**Known blockers (per `benchmark/competitor-configs.json`):**

1. Confirm iii-engine can be installed on the VPS without a paid license.
2. Confirm published claims (R@5 = 95.2% on LoCoMo) correspond to the
   LoCoMo revision we use.

**Pinning rationale:** npm package version not yet stable; pin via
`--version` output captured at install time and recorded in the eventual
methodology writeup.

Adapter: `adapters/agentmemory.py` — subprocess `agentmemory recall ... --json`.

---

## 6. EverMind-AI (EverOS)

| Field | Value |
|---|---|
| Repo | https://github.com/EverOS-AI/EverMind-AI |
| License | check repo (was MIT-leaning per 2026-05-19 audit) |
| Stars (2026-05-21) | ~5k |
| Install | `git clone https://github.com/EverOS-AI/EverMind-AI && cd EverMind-AI && pip install -e .` |
| Version pin | git SHA at clone time — record in REQUIREMENTS.md after Saturday clone |
| Defaults | sentence-transformers (local embeddings, no API key) |
| API keys | None for default; LLM-rerank stage optional, would use `OPENAI_API_KEY` |

**Why interesting (per memory `[[everos-benchmark-publisher-competitor]]`):**

EverOS-AI publishes their own EverMemBench + papers. Direct
"benchmark-publisher competitor" — beating them on their preferred eval
set has narrative value for the Q4 GTM Phase 2 launch.

**Known gap:** retrieval surface less standardized than the other four;
adapter has dual call paths (CLI subprocess + Python module import) and
fails gracefully if neither exposes `retrieve()`.

Adapter: `adapters/evermind.py` — subprocess CLI OR Python module fallback.

---

## Quick reference

```bash
# Python-side (run once)
pip install -r requirements.txt

# Node-side (only if including agentmemory)
npm install -g @agentmemory/agentmemory

# Docker-side (Zep + optional Letta + optional noxmem)
docker compose -f compose/docker-compose.yml up -d zep postgres
# add --profile letta or --profile noxmem if desired

# EverMind-AI (clone outside this repo)
cd /tmp && git clone https://github.com/EverOS-AI/EverMind-AI
cd EverMind-AI && pip install -e .

# Set env (paste into shell or .env.q4):
export OPENAI_API_KEY=...
export GEMINI_API_KEY=...
# Optional:
# export ZEP_USE_CLOUD=1 ZEP_API_KEY=...
# export NOX_API_BASE=http://vps.host:18802
```

---

## Blockers needing Toto's decision

- [ ] **agentmemory iii-engine daemon** — install path unclear. If
      paid-only, skip agentmemory and document gap in COMPARISON.md.
- [ ] **EverMind-AI retrieve API** — `evermind retrieve` CLI assumed but
      not verified against the public repo as of overnight. Toto verifies
      Saturday before runner.py.
- [ ] **OpenAI quota** — Mem0 + Letta both default to OpenAI embeddings.
      Estimate: ~600 queries × 2 datasets × 2 systems = 2,400 embedding
      calls. Budget < $1 at current ada pricing, but confirm before run.
- [ ] **Zep self-host RAM** — Postgres + Zep ~2 GB resident. VPS has 16 GB,
      well-budgeted, but verify other services don't compete.
