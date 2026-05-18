# nox-mem — Quickstart

> **Get from zero to your first hybrid search query in under 10 minutes.**

This guide is copy-paste-ready. Every command runs as-is. Expected outputs are shown so you know things worked.

---

## Prerequisites

| Requirement | Check | Notes |
|---|---|---|
| Node.js 22+ | `node --version` | `better-sqlite3` requires ≥ Node 20; 22 is the tested target |
| npm 10+ | `npm --version` | Ships with Node 22 |
| `sqlite3` CLI | `sqlite3 --version` | Optional — useful for manual schema inspection |
| ~2 GB free disk | `df -h .` | DB + build artifacts + test corpus |
| Gemini API key | [aistudio.google.com](https://aistudio.google.com) | Optional for text-only ingest; required for embedding and semantic search |

---

## 1. Install

```bash
git clone https://github.com/totobusnello/memoria-nox.git
cd memoria-nox
npm install
npm run build
```

Verify:

```bash
node dist/index.js --version
```

Expected output:

```
nox-mem v3.7.0
```

If the command fails with `Cannot find module`, make sure you are in the `memoria-nox/` directory and that `npm run build` completed without errors.

---

## 2. Configure

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```bash
GEMINI_API_KEY=AIza...          # Your Gemini API key from aistudio.google.com
NOX_API_PORT=18802              # HTTP API port — do not change to 18800 (Chrome squats it)
NOX_DB_PATH=./data/nox-mem.db  # Where the SQLite store lives
```

Load the env into your shell before any `nox-mem` command:

```bash
set -a; source .env; set +a
```

> **Important:** This `set -a; source .env; set +a` pattern is mandatory in any shell, SSH session, or script that calls `nox-mem`. Without it, `GEMINI_API_KEY` is absent from the process environment, and vectorize/kg-extract fail silently — the CLI prints progress but the final line reports `Done: 0 embedded, N errors`.

For full env var reference, see [`docs/CONFIGURATION.md`](CONFIGURATION.md).

---

## 3. Initialize the schema

On first run, the schema migrations apply automatically:

```bash
nox-mem init
```

Expected output (abbreviated):

```
[nox-mem] Initializing data directory: ./data
[nox-mem] Running migrations...
[nox-mem] Schema v19 applied (additive, idempotent)
[nox-mem] FTS5 index: ready
[nox-mem] sqlite-vec: loaded (3072d)
[nox-mem] ops_audit: ready (append-only)
[nox-mem] Done.
```

If you see `sqlite-vec extension not loaded`, check that `better-sqlite3` installed cleanly (`npm install` should have compiled it from source).

Verify with the health endpoint (start the API first if needed):

```bash
# Start the HTTP API in the background
nox-mem serve &

# Check health
curl -s http://127.0.0.1:18802/api/health | jq '{schemaVersion, vectorCoverage}'
```

Expected:

```json
{
  "schemaVersion": 19,
  "vectorCoverage": {
    "total": 0,
    "embedded": 0,
    "coverage": 1
  }
}
```

---

## 4. First ingest

### Ingest a text snippet directly

```bash
nox-mem ingest --text "The salience formula is recency times pain times importance. Pain scores range from 0.1 (trivial) to 1.0 (prod outage)."
```

Expected output:

```
[ingest] 1 chunk written (chunk_type: other, retention: 90d)
```

### Ingest a markdown file

Create a test file:

```bash
cat > /tmp/test-note.md << 'EOF'
# Decisions

## 2026-05-18 — Use FTS5 for keyword search

FTS5 BM25 is the keyword backbone. Do not replace with a trigram index — FTS5 handles PT-BR accented tokens correctly. Decision confirmed in evaluation run 85.
EOF
```

Ingest it:

```bash
nox-mem ingest /tmp/test-note.md
```

Expected output:

```
[ingest] 2 chunks written (chunk_type: other, retention: 90d)
```

### Ingest a directory

```bash
nox-mem ingest ~/notes/
```

The ingest router auto-detects entity files (`memory/entities/<type>/<slug>.md` with `compiled` / `frontmatter` / `timeline` sections) and routes them through the entity ingestor, which applies `section_boost` weights. Plain markdown files go through the standard chunker.

---

## 5. First search

```bash
nox-mem search "salience formula"
```

Expected output (abbreviated):

```
Query: "salience formula"
Mode: hybrid (FTS5 + semantic + RRF k=60)

[1] score=0.847  chunk_id=1  type=other
    "The salience formula is recency times pain times importance..."
    match_type: fts5

[2] score=0.731  chunk_id=2  type=other
    "FTS5 BM25 is the keyword backbone..."
    match_type: semantic
```

If no results appear, verify that vectorization ran:

```bash
curl -s http://127.0.0.1:18802/api/health | jq .vectorCoverage
```

The `embedded` count should equal `total`. If `embedded=0` after ingest, run:

```bash
nox-mem vectorize
```

Search options:

```bash
# Keyword-only (skip semantic)
nox-mem search "salience" --no-hybrid

# Limit results
nox-mem search "salience" --limit 5

# Search with metadata output
nox-mem search "salience" --json
```

---

## 6. First answer

The `answer` primitive runs a hybrid search and grounding pass — it returns a direct answer with citation footnotes, not just a list of chunks.

```bash
nox-mem answer "what is the salience formula?"
```

Expected output:

```
Answer: The salience formula is recency × pain × importance. Pain scores
range from 0.1 (trivial) to 1.0 for a production outage. [1]

Citations:
  [1] chunk_id=1 — "The salience formula is recency times pain times
      importance. Pain scores range from 0.1 (trivial) to 1.0 (prod
      outage)." (score=0.847)

Latency: 112ms total (search 8ms · LLM 104ms)
```

The anti-hallucination guard prevents the LLM from answering questions whose context is absent from the retrieved chunks — it returns `"I don't have information about that in the current memory store."` instead of fabricating.

---

## 7. First export

Export creates a portable archive of the SQLite store. The default mode is encrypted (AES-256-GCM + scrypt KDF). You will be prompted for a passphrase:

```bash
nox-mem export --out /tmp/my-memory.nox.tgz
# Enter passphrase:
# Confirm passphrase:
```

Expected output:

```
[export] Snapshot: /var/backups/nox-mem/pre-op/export-<ts>-<uuid>.db
[export] Chunks: 3 | Vectors: 3 | KG entities: 0 | KG relations: 0
[export] Archive: /tmp/my-memory.nox.tgz (AES-256-GCM, scrypt)
[export] Manifest SHA-256: a3f9...
[export] Done.
```

To export without encryption (for inspection or migration):

```bash
nox-mem export --out /tmp/my-memory.nox.tgz --unencrypted
```

To import on another machine:

```bash
nox-mem import /tmp/my-memory.nox.tgz
# Enter passphrase: (leave blank if exported with --unencrypted)
```

The archive format preserves full round-trip fidelity — `nDCG@10` degrades by at most `±0.001` across export/import.

---

## 8. First viewer

The SSE viewer streams live ingest and search activity to a browser panel:

```bash
# Make sure the API is running
nox-mem serve &

# Open the viewer
open http://127.0.0.1:18802/ui
```

Or access it from another machine:

```bash
curl http://<host>:18802/ui
```

The viewer has four panels:
- **Recent ingests** — chunks written in real time
- **Search stream** — queries and result previews
- **KG activity** — entity and relation extraction events
- **Health** — vector coverage, schema version, ops audit status

The viewer redacts query text by default. To see full queries:

```bash
NOX_VIEWER_SHOW_QUERY=1 nox-mem serve
```

> **Security note:** If the viewer is exposed on a network interface (not `127.0.0.1`), set `NOX_VIEWER_AUTH_TOKEN=<random-string>`. Requests without `Authorization: Bearer <token>` will be rejected.

---

## 9. Using the MCP server

nox-mem exposes 16 MCP tools. To connect from Claude Code, add to your `claude_desktop_config.json` (or equivalent):

```json
{
  "mcpServers": {
    "nox-mem": {
      "command": "node",
      "args": ["/path/to/memoria-nox/dist/mcp-server.js"],
      "env": {
        "GEMINI_API_KEY": "AIza...",
        "NOX_DB_PATH": "/path/to/nox-mem.db",
        "NOX_API_PORT": "18802"
      }
    }
  }
}
```

Key MCP tools:

| Tool | Purpose |
|---|---|
| `nox_mem_search` | Hybrid search — primary retrieval surface |
| `nox_mem_answer` | Grounded answer with citations |
| `kg_build` | Trigger KG entity/relation extraction on new chunks |
| `cross_search` | Search across multiple memory stores |
| `reflect` | Crystallize + consolidate daily notes |
| `stats` | Chunk count, vector coverage, schema version |

---

## 10. Using the HTTP API

The API listens on `NOX_API_PORT` (default `18802`):

```bash
# Search
curl -s "http://127.0.0.1:18802/api/search?q=salience+formula" | jq .

# Grounded answer
curl -s -X POST http://127.0.0.1:18802/api/answer \
  -H "Content-Type: application/json" \
  -d '{"query": "what is the salience formula?"}' | jq .

# Health check
curl -s http://127.0.0.1:18802/api/health | jq .

# KG path query
curl -s "http://127.0.0.1:18802/api/kg/path?from=salience&to=pain" | jq .
```

Full API reference: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md).

---

## CLI reference (abbreviated)

```bash
nox-mem --help            # Full subcommand list (26+)
nox-mem ingest <path>     # Ingest file or directory
nox-mem ingest-entity <file>  # Ingest entity file (3-section format)
nox-mem search <query>    # Hybrid search
nox-mem answer <query>    # Grounded answer with citations
nox-mem vectorize         # Embed any un-embedded chunks
nox-mem kg-build          # Extract KG entities and relations
nox-mem reindex           # Rebuild FTS5 index (runs --dry-run first)
nox-mem export --out <path>  # Export encrypted archive
nox-mem import <path>     # Import archive
nox-mem reflect           # Crystallize daily notes
nox-mem stats             # Chunk count, coverage, schema version
nox-mem serve             # Start HTTP API + SSE viewer
```

---

## Next steps

- **Configure providers:** [`docs/CONFIGURATION.md`](CONFIGURATION.md) — full env var reference, including OpenAI and Voyage embedding alternatives, cost caps, and privacy filter settings.
- **Understand the architecture:** [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) — the five layers, module map, and hybrid search pipeline.
- **Contribute:** [`CONTRIBUTING.md`](../CONTRIBUTING.md) — shadow discipline, testing requirements, branch conventions.
- **Agent integrations:** [`docs/integrations/`](integrations/) — per-agent setup for Claude Code, Cursor, Codex, and more.
- **Roadmap:** [`docs/ROADMAP.md`](ROADMAP.md) — Q/A/P pillars, active sprints, and gates.
