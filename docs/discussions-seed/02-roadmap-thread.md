# Public roadmap + upcoming lab priorities

This thread is the living roadmap discussion. The canonical file is `docs/ROADMAP.md` in the repo — this thread is for questions, pushback, and surfacing what matters to the community.

## Release targets

| Version | Target | Scope |
|---|---|---|
| **v1.0.0** | 2026-07 | Stable API + schema freeze + full test coverage + deployment guide |
| **v1.1.0** | ~2026-08 | Encrypted local backup (A2 spec) |
| **v1.2.0** | ~2026-09 | Provider abstraction layer — swap Gemini for OpenAI / local Ollama without schema migration |
| **v2.0.0** | TBD, not committed | Multi-tenant; requires architectural rethink beyond SQLite per-user |

v1.0.0 is a stability milestone, not a feature release. The goal is: if you build on nox-mem after v1.0.0, your integration doesn't break at the next upgrade.

## Lab priorities (Q3-Q4 2026)

The lab track runs at ~40% of total capacity and feeds future releases:

- **EverMemBench eval** — run nox-mem against the public EverMemBench dataset so we have an apples-to-apples comparison with published systems (EverOS, MemGPT, etc.)
- **BGE-reranker ablations (A11–A15)** — cross-encoder reranking sits on top of RRF fusion; early results suggest +3–8% nDCG but adds ~200ms latency; ablations will quantify the trade-off
- **Scale to 250k+ chunks** — current production corpus is ~70k chunks; we need to verify FTS5 + sqlite-vec performance at 250k before claiming "large-scale" in benchmarks
- **PT-BR multilingual eval** — baseline corpus is English; Brazilian Portuguese queries perform differently, especially on FTS5 tokenization; building a PT-BR golden set
- **Salience formula optimization** — current `salience = recency × pain × importance` is hand-tuned; exploring Bayesian optimization and CMA-ES for coefficient search

## What is NOT on the roadmap and why

**GPU inference for embeddings** — contradicts the Autonomy pillar. The goal is a system that runs on a $6/mo VPS. GPU inference requires a $50+/mo instance or a cloud API, which reintroduces vendor dependency. If you need sub-100ms embeddings at scale, that's a valid use case but it belongs in a different project.

**SaaS hosted offering** — nox-mem stays self-hosted MIT. The commercial layer (`nox-supermem`) is a separate product for users who don't want to operate their own VPS. Not public yet.

**LangGraph / LlamaIndex first-class integration** — these frameworks move fast and have their own memory abstractions. We expose an MCP server and an HTTP API; integration is the caller's responsibility. Happy to accept community-contributed examples in `docs/integrations/`.

## How to influence the roadmap

File an issue with the `roadmap` label, or open an RFC thread here in Discussions (use the RFC template). Priority is driven by: benchmark impact, community need, and implementation feasibility on minimal infra.

If you're building something on nox-mem and a feature would unblock production use, say so explicitly in the issue — production blockers get fast-tracked.

The full detail is in `docs/ROADMAP.md`. This thread is for discussion; the file is the source of truth.
