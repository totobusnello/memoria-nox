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
| License | Apache-2.0 (CLI + npm package); iii-engine = **ELv2** (self-host OK; SaaS-compete prohibited) |
| Stars (2026-05-23 probe) | 16,726 |
| Install | `npm install -g '@agentmemory/agentmemory'` |
| Version pin | **v0.9.21** (installed + verified 2026-05-23) |
| Daemon | iii-engine **auto-installs** from npm on first run (no paid license required for self-host) |
| API keys | None required for local run |
| REST API | `POST http://localhost:3111/agentmemory/remember` + `POST /agentmemory/search` |

**Probe results (2026-05-23):**

- `npm install -g @agentmemory/agentmemory` — SUCCEEDED, v0.9.21, ~8s, 242 packages
- iii-engine: auto-downloaded + started (v0.11.2 pinned in npm bundle). **Not paid-only.**
  License is ELv2 (not MIT) but self-host for benchmark is permitted; SaaS-compete is not.
- REST API liveness: `GET /agentmemory/livez` → `{"service":"agentmemory","status":"ok"}` PASS
- Smoke ingest (5 chunks via `POST /agentmemory/remember`): PASS, all returned `"success":true`
- Smoke search (`POST /agentmemory/search`, `query="hybrid search BM25"`): PASS, 5 results, scores ~0.68
- **Adapter mismatch (BLOCKER fixed in adapter):** CLI has no `add`/`recall` subcommands — it is
  server-only (REST on :3111). Adapter rewritten to use REST (`POST /remember`, `POST /search`).
- **ID round-trip gap:** `/agentmemory/remember` does NOT accept custom `id`; issues system-generated
  `mem_xxx` IDs. Nox-mem chunk id must be embedded in `content` and extracted at search time.
  Adapter updated to embed `[nox_id:<id>]` prefix and parse it back from returned content.

**Pinning rationale:** v0.9.21 confirmed installed. Record `agentmemory --version` on VPS after
daemon is running (the binary outputs version only after iii-engine connects).

**⚠️ Start sequence on VPS:**
```bash
agentmemory &   # starts daemon + auto-installs iii-engine if absent; binds :3111
sleep 5
curl http://localhost:3111/agentmemory/livez   # must return {"status":"ok"}
```

Adapter: `adapters/agentmemory.py` — REST `POST /agentmemory/remember` + `POST /agentmemory/search`.

---

## 6. EverMind-AI (EverOS) — SKIPPED

| Field | Value |
|---|---|
| Repo | https://github.com/EverOS-AI/EverMind-AI — **DOES NOT EXIST** (404 on 2026-05-23 probe) |
| License | N/A |
| Stars | 0 (repo not found) |
| Install | N/A |

**Probe results (2026-05-23) — SKIP:**

- `gh repo view EverOS-AI/EverMind-AI` → "Could not resolve to a Repository"
- `curl https://api.github.com/repos/EverOS-AI/EverMind-AI` → 404
- GitHub org `EverOS-AI` does not exist.
- `pip install evermind-ai` → "No matching distribution found" (not on PyPI)
- Searched all variants: `EverMind-AI/EverMind-AI`, `EverMindAI/EverMindAI`, `EverOS/EverMind` — none found.

**What was found instead:**

The 2026-05-19 audit memory (`[[everos-benchmark-publisher-competitor]]`) referenced a competitor
that has since been made private, deleted, or the name was incorrectly captured. What exists in
2026-05 public GitHub:

- `evermemos/evermemos-python` — Python SDK for **EverMemOS cloud API** (`pip install evermemos`),
  requires `EVERMEMOS_API_KEY`. Cloud-only, not self-hostable, no benchmark-runnable OSS core.
- `evermindai/public_website` — marketing website only.
- ~43 repos with "EverMemOS" in name — all are community integrations (OpenClaw plugins, MCP
  wrappers), none are the core EverMemOS OSS engine itself.

**Decision: SKIP agentmemory EverMind from Q4 run.**

COMPARISON.md will show "no data" for EverMind with honest note: "repo unavailable / cloud-only".
This does not affect the narrative — the key benchmark competitors (Mem0, Zep, Letta) are verified.
agentmemory is the 4th system (now unblocked).

Adapter: `adapters/evermind.py` — kept in repo for future use if repo surfaces; validate() returns
`ok=False` cleanly (no crash). Runner skips it per spec §4 stop condition handling.

---

## Quick reference

```bash
# Python-side (run once)
pip install -r requirements.txt

# Node-side (agentmemory — verified working 2026-05-23)
npm install -g @agentmemory/agentmemory   # installs v0.9.21 + iii-engine auto-download
agentmemory &                              # start daemon; binds REST on :3111
sleep 5 && curl http://localhost:3111/agentmemory/livez   # verify {"status":"ok"}

# Docker-side (Zep + optional Letta + optional noxmem)
docker compose -f compose/docker-compose.yml up -d zep postgres
# add --profile letta or --profile noxmem if desired

# EverMind-AI: SKIPPED — repo does not exist (see §6 above)

# Set env (paste into shell or .env.q4):
export OPENAI_API_KEY=...
export GEMINI_API_KEY=...
# Optional:
# export ZEP_USE_CLOUD=1 ZEP_API_KEY=...
# export NOX_API_BASE=http://vps.host:18802
```

---

## Blockers resolved / needing Toto's decision

- [x] **agentmemory iii-engine daemon** — RESOLVED 2026-05-23. iii-engine auto-installs
      from npm bundle (ELv2, not paid). REST API verified working. Adapter updated to REST.
- [x] **EverMind-AI retrieve API** — RESOLVED 2026-05-23. Repo EverOS-AI/EverMind-AI
      does not exist. System SKIPPED. COMPARISON.md will show "no data / repo unavailable".
- [ ] **OpenAI quota** — Mem0 + Letta both default to OpenAI embeddings.
      Estimate: ~600 queries × 2 datasets × 2 systems = 2,400 embedding
      calls. Budget < $1 at current ada pricing, but confirm before run.
- [ ] **Zep self-host RAM** — Postgres + Zep ~2 GB resident. VPS has 16 GB,
      well-budgeted, but verify other services don't compete.
