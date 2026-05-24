# Welcome to nox-mem

Hi everyone — I'm Toto Busnello, the sole author of nox-mem, and this is the first post in the Discussions tab.

nox-mem is a hybrid long-term memory engine for AI agents: it combines BM25 full-text search, semantic vector search (Gemini embeddings, 3072d), and a knowledge graph into a single SQLite-backed library that runs on a $6/mo VPS. No GPU required. No cloud subscription. Your data, your database, your provider choice.

## Three pillars

**Quality** — benchmarked retrieval, not vibes. We track nDCG@10 and MRR on our eval corpus every time we change the search stack. Q4 cross-system comparison (definitive, 2026-05-24):

| System | nDCG@10 | p50 latency | Corpus cap |
|---|---:|---:|---:|
| nox-mem (Gemini hybrid) | **0.6380** | ~940ms | 100% |
| nox-mem (FTS5-only) | **0.3753** | 7–12ms | 100% |
| agentmemory | 0.1376 | 14ms | 20% |
| mem0 | 0.1315 | 263ms | 7.3% |
| Letta | partial eval | 14,978ms | — |

Full table with methodology disclosure: `benchmark/COMPARISON.md`. The paper (arXiv, link pending Tue 2026-06-01) documents the ablation methodology.

**Autonomy** — MIT license, SQLite on disk, provider-swappable embedding layer. You can run this fully offline with a local embedding model. No API key required for the core; Gemini is the default because it performs best in our ablations, not because of lock-in.

**Product** — a library that's actually usable: 26-command CLI, MCP server (compatible with Claude, Cursor, and any MCP host), HTTP API on port 18802, and a React dashboard.

## What's open today

- **Repo:** github.com/totobusnello/memoria-nox (MIT)
- **Paper:** arXiv link TBD (posting Tue 2026-06-01)
- **Live demo API:** `http://187.77.234.79:18802/api/health` — read-only, best-effort uptime
- **Quickstart:** see `docs/QUICKSTART.md` — up and running in under 10 minutes on a fresh Ubuntu VPS

## What nox-mem is NOT (yet)

- No SLAs, no on-call, no commercial support — this is a research + open-source project
- No multi-tenant or hosted cloud offering — that's a separate product (`nox-supermem`, not yet public)
- Not a general-purpose database or document store — purpose-built for AI agent memory retrieval

## How to participate

- **Try it:** clone the repo, run the quickstart, share what breaks (or works)
- **File issues:** bugs, performance regressions, missing docs — all welcome
- **Share use cases:** the Show and Tell thread (posting later today) is the place
- **Propose features:** use the RFC template (thread posting at 09:00 BRT)
- **Read the code:** `src/search.ts` is the core of hybrid retrieval; `src/kg-extract.ts` is the KG pipeline

We follow the Contributor Covenant Code of Conduct. Be direct, be curious, be kind.

First question? Post below.

---

*Updated 2026-05-24 with definitive cross-system numbers · [[project-sat-2026-05-24-final-closure]]*
