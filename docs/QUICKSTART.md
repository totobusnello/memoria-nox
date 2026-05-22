# nox-mem — 5-Minute Quickstart

> Pain-weighted hybrid memory for AI agents. SQLite on your disk. Provider your choice. Zero vendor lock-in.

**Just want to see it work?** Hit the live demo — no install:

```bash
curl -s 'http://187.77.234.79:18802/api/search?q=pain-weighted+memory&limit=3' \
  | jq '.results[] | {score, source_file, snippet}'
```

**Want it local?** Three commands after clone:

```bash
npm install && npm run build
set -a; source .env; set +a
node dist/index.js search "hello"
```

---

## §1 Try the public demo (0 install, 30s)

The live corpus has 69k+ chunks from real agent memory. Read-only.

```bash
# Hybrid search: FTS5 BM25 + Gemini semantic + RRF fusion
curl -s 'http://187.77.234.79:18802/api/search?q=pain-weighted+memory&limit=3' \
  | jq '.results[] | {score, source_file, snippet}'

# Grounded answer with citations (flagship /api/answer endpoint)
curl -s -X POST http://187.77.234.79:18802/api/answer \
  -H 'Content-Type: application/json' \
  -d '{"query": "what is conditional hard mutex?"}' | jq

# Health check — schema version, vector coverage, chunk count
curl -s http://187.77.234.79:18802/api/health | jq '{schemaVersion, totalChunks, vectorCoverage}'
```

---

## §2 Local install (5min)

### Prerequisites

| Requirement | Check | Notes |
|---|---|---|
| Node.js 20+ | `node --version` | 22 LTS recommended |
| SQLite 3.40+ | `sqlite3 --version` | Most modern systems — needs FTS5 compiled in |
| Gemini API key | [aistudio.google.com](https://aistudio.google.com) | Free tier works; required for embeddings |

### Clone and build

```bash
git clone https://github.com/totobusnello/memoria-nox.git
cd memoria-nox
npm install
npm run build
```

Verify:

```bash
node dist/index.js --version
# nox-mem v3.7.0
```

### Configure `.env`

No `.env.example` ships yet — create it manually:

```bash
cat > .env << 'EOF'
GEMINI_API_KEY=AIza...       # Required for embeddings + semantic search
NOX_API_PORT=18802           # Do not use 18800 — Chrome squats it
NOX_DB_PATH=./data/nox-mem.db
EOF
```

**Always load env before any nox-mem command:**

```bash
set -a; source .env; set +a
```

Without this, `vectorize` and `kg-build` fail silently — they print progress but report `Done: 0 embedded, N errors`.

### Initialize schema

```bash
node dist/index.js init
```

Expected:

```
[nox-mem] Schema v19 applied (additive, idempotent)
[nox-mem] FTS5 index: ready
[nox-mem] sqlite-vec: loaded (3072d)
[nox-mem] Done.
```

### First search

```bash
node dist/index.js search "hello world"
```

Empty results are expected on a fresh DB — proceed to §3 to ingest something.

---

## §3 First-time use flow (10min)

### Ingest a snippet directly

```bash
node dist/index.js ingest --text "The salience formula: recency × pain × importance. Pain 0.1=trivial, 1.0=prod outage."
```

### Ingest a markdown file

```bash
node dist/index.js ingest path/to/notes.md
```

The ingest router auto-detects entity files (`memory/entities/<type>/<slug>.md`) and applies section boosts. Plain markdown goes through the standard chunker.

### Vectorize (embed un-embedded chunks)

```bash
node dist/index.js vectorize
```

This calls Gemini embeddings (3072d). Requires `GEMINI_API_KEY`. Check coverage:

```bash
# Start the API server first
node dist/index.js serve &
curl -s http://127.0.0.1:18802/api/health | jq .vectorCoverage
# embedded should equal total
```

### Build the knowledge graph

```bash
node dist/index.js kg-build
```

Extracts entities and relations via Gemini. Optional but improves cross-topic retrieval.

### Hybrid search

```bash
node dist/index.js search "salience formula"
# Mode: hybrid (FTS5 + semantic + RRF k=60)

# Options
node dist/index.js search "query" --limit 5
node dist/index.js search "query" --no-hybrid   # keyword-only
node dist/index.js search "query" --json        # machine-readable output
```

### Grounded answer

```bash
node dist/index.js answer "what is the salience formula?"
# Returns direct answer + citation footnotes, not just chunks
```

---

## §4 Common gotchas

| Symptom | Fix |
|---|---|
| `GEMINI_API_KEY not set` | Run `set -a; source .env; set +a` before the command |
| `Done: 0 embedded, N errors` | Same as above — env not loaded |
| `FTS5 not available` | Upgrade SQLite or recompile with `--enable-fts5`; most distros ship it |
| `sqlite-vec extension not loaded` | `npm install` compiles it; try `npm rebuild better-sqlite3` |
| Port conflict on 18802 | Set `NOX_API_PORT=19000` (or any free port) in `.env` |
| `Cannot find module` on `dist/index.js` | Run `npm run build` first |

---

## §5 Next steps

| Resource | What's in it |
|---|---|
| [`README.md`](../README.md) | Full feature list, architecture overview, benchmark numbers |
| [`docs/COMPARISON.md`](COMPETITIVE-ANALYSIS-2026-05-19.md) | Benchmark comparison vs competitors |
| [`paper/paper-tecnico-nox-mem.md`](../paper/paper-tecnico-nox-mem.md) | Technical deep dive — salience formula, hybrid search, KG design |
| [`docs/CONFIGURATION.md`](CONFIGURATION.md) | Full env var reference, provider swap (OpenAI, Voyage) |
| [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) | Five-layer architecture, module map, HTTP API reference |
| [Issues](https://github.com/totobusnello/memoria-nox/issues) | Bug reports, feature requests |

---

<sub>Versão em PT-BR em breve. Live demo is read-only — production corpus, no writes accepted.</sub>
