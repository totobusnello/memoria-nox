<!--
  README-DRAFT.md — staged for Q4 gate flip.
  When Q4 COMPARISON shows nox-mem #1 (or tied #1):
    1) Replace Q-pillar placeholders (LoCoMo, LongMemEval, latency, tests count, arXiv, YouTube ID).
    2) `mv README-DRAFT.md README.md`.
    3) Do NOT publish stat SVGs with unresolved placeholders.
  Spec: specs/2026-05-17-GTM-readme-hero-upgrade.md · Assets: assets/readme/README.md
-->

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/readme/banner-dark.svg">
    <img alt="nox-mem — Hybrid memory with shadow discipline" src="assets/readme/banner-light.svg" width="720">
  </picture>
</p>

<h1 align="center">Hybrid memory with shadow discipline — yours by design.</h1>

<p align="center"><em>The only agent memory that's genuinely yours. SQLite on your disk, provider your choice, zero vendor lock-in.</em></p>

<p align="center">
  <a href="https://www.npmjs.com/package/nox-mem"><img src="https://img.shields.io/npm/v/nox-mem?style=for-the-badge&color=00C896&label=npm" alt="npm"></a>
  <a href="https://github.com/totobusnello/memoria-nox/actions"><img src="https://img.shields.io/github/actions/workflow/status/totobusnello/memoria-nox/ci.yml?style=for-the-badge&color=00C896" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/totobusnello/memoria-nox?style=for-the-badge&color=00C896" alt="License: MIT"></a>
  <a href="https://github.com/totobusnello/memoria-nox/stargazers"><img src="https://img.shields.io/github/stars/totobusnello/memoria-nox?style=for-the-badge&color=00C896" alt="Stars"></a>
</p>

<p align="center">
  <picture><source media="(prefers-color-scheme: dark)" srcset="assets/readme/stat-locomo-dark.svg"><img src="assets/readme/stat-locomo-light.svg" alt="LoCoMo R@5 (pending Q1)" height="38"></picture>
  <picture><source media="(prefers-color-scheme: dark)" srcset="assets/readme/stat-longmemeval-dark.svg"><img src="assets/readme/stat-longmemeval-light.svg" alt="LongMemEval (pending Q2)" height="38"></picture>
  <picture><source media="(prefers-color-scheme: dark)" srcset="assets/readme/stat-latency-dark.svg"><img src="assets/readme/stat-latency-light.svg" alt="p95 latency (pending Q3)" height="38"></picture>
  <br>
  <picture><source media="(prefers-color-scheme: dark)" srcset="assets/readme/stat-scale-dark.svg"><img src="assets/readme/stat-scale-light.svg" alt="69k chunks · 21k relations" height="38"></picture>
  <picture><source media="(prefers-color-scheme: dark)" srcset="assets/readme/stat-opex-dark.svg"><img src="assets/readme/stat-opex-light.svg" alt="<$11/mo all-in" height="38"></picture>
  <picture><source media="(prefers-color-scheme: dark)" srcset="assets/readme/stat-tests-dark.svg"><img src="assets/readme/stat-tests-light.svg" alt="950+ tests passing" height="38"></picture>
</p>

<p align="center">
  <a href="#-install">Install</a> ·
  <a href="#-quick-start">Quick Start</a> ·
  <a href="#-benchmarks">Benchmarks</a> ·
  <a href="#-vs-competitors">vs Competitors</a> ·
  <a href="#-architecture">Architecture</a> ·
  <a href="#why-nox-mem-leads">Why</a> ·
  <a href="#-paper--research">Paper</a> ·
  <a href="#-configuration">Config</a>
</p>

---

## What is nox-mem?

nox-mem is a hybrid memory engine for AI agents. It combines FTS5 keyword search with Gemini 3072-dimensional embeddings via Reciprocal Rank Fusion, layered with a knowledge graph (21k+ relations) and shadow-mode validation discipline. Everything runs on local SQLite — portable, auditable, yours. No vendor lock-in, no cloud round-trips for retrieval. Published research, reproducible benchmarks, production-tested.

- **Hybrid retrieval** — FTS5 BM25 + Gemini semantic + RRF fusion (k=60), language-aware
- **Knowledge graph** — 15.6k entities, 21.5k typed relations, incremental nightly extraction
- **Pain-weighted salience** — `recency × pain × importance` ranks severity, not just freshness
- **Shadow discipline** — every ranking change ships in shadow ≥7d before going live
- **Yours by design** — one SQLite file, your provider key, your disk, MIT-licensed

---

## The Six Gaps in agent memory today

| Gap | Industry default | nox-mem |
|---|---|---|
| **Portability** | Cloud-locked vector DB, your data on their servers | One SQLite file. Copy it. It's yours. |
| **Provider lock-in** | Embedding API tied to vendor's billing | BYO key. Gemini today, swap tomorrow. |
| **Retrieval transparency** | Opaque ranking, "trust the magic" | RRF formula in code, every score auditable |
| **Severity signal** | Recency-only decay; outages = vacation photos | Pain field weights ranking, never decays for `feedback`/`person` |
| **Change safety** | Ship ranking, hope for the best | Shadow-mode mandatory ≥7d; salience exposed on `/api/health` |
| **Cost surface** | $$$ per million tokens stored + queried | <$11/mo all-in for 69k chunks. Embeddings amortize. |

---

## Why nox-mem leads

- **Benchmarks are public and reproducible** — every number in [Benchmarks](#-benchmarks) ships with a harness in `benchmark/`
- **SQLite-native, not SQLite-wrapped** — better-sqlite3 + sqlite-vec + FTS5 in one file; no Postgres dep, no Docker required
- **Bring your own provider** — Gemini default, OpenAI/local swappable via `NOX_EMBED_PROVIDER`
- **Three primitives, not thirty** — chunks, relations, salience. Everything else composes from these.
- **Open architecture** — CLI (26+ commands), MCP server (16 tools), HTTP API on `:18802`. Pick your interface.
- **Pain-weighted, not vibe-weighted** — production incidents stay retrievable when their lessons matter
- **Shadow discipline is enforced, not aspirational** — `NOX_SALIENCE_MODE=shadow` is the default; flipping to `active` requires a 7-day baseline

---

## 🏗️ Architecture

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/readme/architecture-dark.svg">
    <img alt="nox-mem architecture: ingest → FTS5 + Gemini embed → RRF fusion + KG layer → salience-ranked answer" src="assets/readme/architecture-light.svg" width="900">
  </picture>
</p>

Five layers: **ingest** (router auto-detects entity files, markdown, graphify input) → **store** (chunks + FTS5 + sqlite-vec 3072d + KG entities/relations) → **retrieve** (FTS5 BM25 ∥ Gemini semantic → RRF fusion) → **rank** (salience × section_boost × temporal × language-aware RRF) → **answer** (MCP/HTTP/CLI with citation footers). Mermaid source: [`assets/readme/mermaid/architecture-source.mmd`](assets/readme/mermaid/architecture-source.mmd).

---

## 📺 Setup & Demo

<p align="center">
  <a href="https://youtu.be/PENDING_YOUTUBE_ID">
    <img src="assets/readme/banner-light.svg" alt="Watch the 90-second setup demo" width="640">
  </a>
  <br>
  <em>90-second walkthrough — install, ingest, search with citations. <a href="https://youtu.be/PENDING_YOUTUBE_ID">Watch on YouTube →</a></em>
</p>

---

## 🚀 Install

```bash
# Global install (recommended for CLI + MCP server)
npm install -g nox-mem

# Or run once with npx — no install
npx nox-mem demo
```

Requires Node 20+. SQLite ships bundled via `better-sqlite3`. Set `GEMINI_API_KEY` (or your provider equivalent) in your environment.

---

## Quick Start

```bash
# 1. Initialize a memory store on your disk
nox-mem init ~/my-memory

# 2. Ingest a directory of markdown
nox-mem ingest ~/notes

# 3. Search with hybrid retrieval (FTS5 + semantic + RRF)
nox-mem search "what's the salience formula?"

# 4. Build the knowledge graph from your ingested chunks
nox-mem kg-build && nox-mem kg-path salience pain importance
```

Full reference: [`docs/QUICKSTART.md`](docs/QUICKSTART.md) · 26+ CLI commands via `nox-mem --help`.

---

## 🤖 Works with every agent

**Tier A — first-class integration**

<table>
  <tr>
    <td align="center"><strong>Claude Code</strong><br><sub>MCP server</sub></td>
    <td align="center"><strong>ChatGPT</strong><br><sub>HTTP API</sub></td>
    <td align="center"><strong>OpenClaw</strong><br><sub>native plugin</sub></td>
    <td align="center"><strong>Cursor</strong><br><sub>MCP server</sub></td>
    <td align="center"><strong>Cline</strong><br><sub>MCP server</sub></td>
  </tr>
</table>

**Tier B — works via MCP or HTTP**

Continue · Aider · Codex · Roo · Tabnine · Windsurf · Goose · Zed · Open Interpreter · LangChain · LlamaIndex · CrewAI · AutoGen · Custom

See [`docs/integrations/`](docs/integrations/) for per-agent setup. The MCP server exposes 16 tools including `nox_mem_search`, `kg_build`, `cross_search`, and `reflect`.

---

## 🧠 How It Works

Memory passes through four consolidation tiers — each tier earns its retention via observed utility, not eager storage.

1. **Ingest** — markdown, entity files, or graphify input → router dispatches to typed handler → privacy filter (13 redaction patterns) → chunk + embed
2. **Store** — chunks land in SQLite with FTS5 index, 3072-d Gemini vector, optional KG extraction. Retention is typed (`feedback`/`person` never decay, `lesson` 180d, `decision` 365d, default 90d).
3. **Retrieve** — query runs in parallel through FTS5 BM25 and Gemini semantic, fused by RRF (k=60). Language-aware boost +1.92pp on PT/EN mixed corpora.
4. **Rank** — salience (`recency × pain × importance`) and section_boost (compiled 2.0 / frontmatter 1.5 / timeline 0.8) compose additively. Shadow-mode gates every change ≥7d before activation.

Deep dive: [`paper/paper-tecnico-nox-mem.md`](paper/paper-tecnico-nox-mem.md) (v1.1, 31 pages, arXiv-ready).

---

## 📊 Benchmarks

| Benchmark | nox-mem | Best alternative | Methodology |
|---|---|---|---|
| **LoCoMo R@5** | _pending Q1_ | — | n=N stratified, hybrid + KG retrieval |
| **LongMemEval** | _pending Q2_ | — | Multi-session conversational eval |
| **Internal golden (n=78)** | **nDCG@10 = 0.6813** | BM25 Pyserini 0.1475 (4.0×) | R01c-v1.1 honest golden, post-cure |
| **External BEIR TREC-COVID** | FTS5 = 0.1007 | e5-base = 0.8335 | Corpus-dependent, confirms domain fit |
| **External LOCOMO (n=100)** | FTS5 = 0.281 | — | Stratified, above baseline |
| **p95 latency** | _pending Q3_ | — | Cold cache, single-node, 69k chunks |
| **OPEX (all-in)** | **<$11/mo** | $40-200/mo typical | Gemini embed + KG + VPS, March-May 2026 |

Full table + methodology + reproducibility kit: [`paper/publication/Q4-COMPARISON.md`](paper/publication/Q4-COMPARISON.md). Harnesses in [`benchmark/`](benchmark/).

---

## vs Competitors

Abridged. Full matrix in [`paper/publication/Q4-COMPARISON.md`](paper/publication/Q4-COMPARISON.md).

| Capability | mem0 | MemGPT | A-MEM | LangChain Memory | **nox-mem** |
|---|---|---|---|---|---|
| Local-first (SQLite) | ✗ | ✗ | ✗ | partial | ✅ |
| BYO embedding provider | partial | ✗ | ✓ | ✓ | ✅ |
| Knowledge graph (typed relations) | partial | ✗ | ✓ | ✗ | ✅ |
| Shadow-mode ranking discipline | ✗ | ✗ | ✗ | ✗ | ✅ |
| Pain-weighted salience | ✗ | ✗ | ✗ | ✗ | ✅ |
| Published reproducible paper | ✗ | ✓ | ✓ | ✗ | ✅ (v1.1) |
| MIT, no usage caps | partial | ✓ | ✓ | ✓ | ✅ |

---

## 📄 Paper & Research

**Title:** *The Pain Diary and Shadow Discipline: A Memory System That Learns from Its Own Incidents*
**Status:** v1.1 compiled (31 pages PDF) · arXiv target: cs.IR, _pending submission_
**PDF:** [`paper/publication/latex/paper.pdf`](paper/publication/latex/paper.pdf)
**Hugging Face:** _pending release_ — `huggingface.co/totobusnello/nox-mem` (datasets + eval harness)

```bibtex
@article{busnello2026noxmem,
  title   = {The Pain Diary and Shadow Discipline: A Memory System That Learns from Its Own Incidents},
  author  = {Busnello, Toto},
  year    = {2026},
  journal = {arXiv preprint arXiv:PENDING_ARXIV_ID},
  url     = {https://arxiv.org/abs/PENDING_ARXIV_ID}
}
```

Distribution drafts (dev.to, LinkedIn, Substack) live in [`paper/publication/distribution/`](paper/publication/distribution/).

---

## 🔧 Configuration

Top 10 env vars. Full reference: [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md).

| Variable | Default | Purpose |
|---|---|---|
| `NOX_API_PORT` | `18802` | HTTP API port (never hardcode; Chrome squats 18800) |
| `NOX_SALIENCE_MODE` | `shadow` | Salience ranking mode: `shadow` (default) / `active` |
| `NOX_SEARCH_LOG_TEXT` | `0` | Persist query text in `search_telemetry` (eval harness) |
| `NOX_EMBED_PROVIDER` | `gemini` | Embedding provider: `gemini` / `openai` / `local` |
| `GEMINI_API_KEY` | _required_ | Default embedding provider key |
| `NOX_DB_PATH` | `./nox-mem.db` | SQLite store location |
| `NOX_RETENTION_OVERRIDE` | — | Per-type retention overrides (typed) |
| `NOX_ALLOW_NO_SNAPSHOT` | `0` | Emergency override for destructive ops without snapshot |
| `OPENCLAW_WORKSPACE` | — | Workspace dir (multi-agent setups) |
| `NOX_LANG_AWARE_RRF` | `1` | Language-aware RRF fusion (+1.92pp on PT/EN mix) |

---

## 📞 Support & Documentation

- **Quickstart:** [`docs/QUICKSTART.md`](docs/QUICKSTART.md)
- **Architecture:** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- **Decisions log:** [`docs/DECISIONS.md`](docs/DECISIONS.md) (why we don't do reranker, focus_boost, A1/A2/G)
- **Roadmap:** [`docs/ROADMAP.md`](docs/ROADMAP.md) (Q/A/P pillars, GTM gate)
- **Incidents:** [`docs/INCIDENTS.md`](docs/INCIDENTS.md) (the pain diary that feeds salience)
- **Paper:** [`paper/`](paper/) · **Issues:** [GitHub Issues](https://github.com/totobusnello/memoria-nox/issues) · **Discussions:** [GitHub Discussions](https://github.com/totobusnello/memoria-nox/discussions)

---

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/readme/logo-dark.svg">
    <img alt="nox-mem" src="assets/readme/logo-light.svg" width="64">
  </picture>
</p>

<p align="center">
  <strong>Hybrid memory with shadow discipline — yours by design.</strong>
  <br>
  <sub>MIT License · <a href="LICENSE">LICENSE</a> · Maintained by <a href="https://github.com/totobusnello">@totobusnello</a> · <a href="https://github.com/totobusnello/memoria-nox/graphs/contributors">Contributors</a></sub>
</p>
