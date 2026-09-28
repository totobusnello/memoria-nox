# nox-mem — 5-Minute Quickstart

> Pain-weighted hybrid memory for AI agents. SQLite on your disk. Provider your choice. Zero vendor lock-in.

**Where the code lives.** This repository (`memoria-nox`) is the research lab: paper, eval harnesses, specs. It has no `package.json` at the root and is **not** meant to be cloned and built. The engine is developed in [`totobusnello/nox-mem`](https://github.com/totobusnello/nox-mem) and published to npm as [`nox-mem`](https://www.npmjs.com/package/nox-mem). Everything below uses the npm package.

Install, ingest, search, `stats`, `doctor`, the MCP server (`tools/list`) and the HTTP API were run against `nox-mem@3.3.0` on a clean install (2026-09-28). Steps that need a Gemini key (`vectorize`, `kg-build`, a successful `answer`) were not exercised in that run.

---

## §1 Install (2min)

### Prerequisites

| Requirement | Check | Notes |
|---|---|---|
| Node.js 20+ | `node --version` `engines: >=20`; install tested on Node 26 |
| C/C++ toolchain | `xcode-select -p` (macOS) · `gcc --version` (Linux) | Only needed when no prebuilt `better-sqlite3` binary matches your Node version. Linux: `apt-get install -y build-essential python3` |
| Gemini API key | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | **Optional.** Free tier works. Without it, search runs keyword-only (FTS5) |

SQLite, FTS5 and `sqlite-vec` ship inside the package — no system SQLite needed.

### Install and configure

```bash
npm install -g nox-mem
nox-mem --version            # 3.3.0

# Keep the store in a directory you own
export NOX_DB_PATH="$HOME/.nox-mem/nox.db"
export NOX_MEM_DIR="$HOME/.nox-mem/memory"
mkdir -p "$NOX_MEM_DIR"

# Optional — enables semantic search, KG extraction and answer
export GEMINI_API_KEY=AIza...
```

Put the `export` lines in your shell profile (or a `.env` you load with `set -a; source .env; set +a`). Every `nox-mem` command reads them; **always set `NOX_DB_PATH`**, otherwise the store lands in a default path you did not choose.

> **npm 11 note:** recent npm versions may print `allow-scripts ... better-sqlite3` during install. If `nox-mem stats` then fails with a missing `.node` binding, run `npm rebuild -g better-sqlite3`.

---

## §2 First use (5min)

### Ingest markdown

`ingest` takes **one file** per call (a directory raises `EISDIR`):

```bash
nox-mem ingest ~/notes/decisions.md

# A whole folder
for f in ~/notes/*.md; do nox-mem ingest "$f"; done
```

The ingest router auto-detects entity files (`memory/entities/<type>/<slug>.md`) and applies section boosts. Plain markdown goes through the standard chunker. A date in the filename (`2026-09-27.md`) becomes the chunk's `source_date`.

### Embed (needs `GEMINI_API_KEY`)

```bash
nox-mem vectorize
```

Read the last line: `Done: N embedded, 0 skipped, 0 errors`. If it says `0 embedded, N errors`, the key is not in the environment of that shell.

### Search

```bash
nox-mem search "what did we decide about deploys?"
nox-mem search "salience formula" --limit 10
nox-mem search "salience formula" --no-hybrid    # keyword-only (FTS5)
```

Without embeddings you will see `Vector index empty — run 'nox-mem vectorize' first. Falling back to FTS5.` — search still works.

### Inspect

```bash
nox-mem stats      # chunk counts, tiers, DB size
nox-mem doctor     # health check
nox-mem --help     # all subcommands
```

In `doctor`, **Ollama**, **Notion token** and **File watcher** are optional integrations. A ❌ there does not affect ingest or search; the lines that matter are `SQLite DB` and `FTS5 Index`.

### Knowledge graph (optional, needs `GEMINI_API_KEY`)

```bash
nox-mem kg-build --limit 200
nox-mem kg-stats
nox-mem kg-query "some entity"
nox-mem kg-path "entity A" "entity B"
```

---

## §3 Connect an agent

### MCP server (Claude Code, Cursor, Cline, ...)

The MCP server ships in the package but has no binary of its own — point your client at the file. It exposes 20 tools (`nox_mem_search`, `nox_mem_ingest`, `nox_mem_stats`, `nox_mem_kg_query`, `nox_mem_kg_path`, `nox_mem_reflect`, `nox_mem_decision_*`, ...).

```bash
# Claude Code
claude mcp add nox-mem \
  -e NOX_DB_PATH="$HOME/.nox-mem/nox.db" -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -- node "$(npm root -g)/nox-mem/dist/mcp-server.js"
```

For clients configured by JSON (Cursor, Cline, ...):

```json
{
  "mcpServers": {
    "nox-mem": {
      "command": "node",
      "args": ["<output of `npm root -g`>/nox-mem/dist/mcp-server.js"],
      "env": { "NOX_DB_PATH": "/Users/you/.nox-mem/nox.db", "GEMINI_API_KEY": "AIza..." }
    }
  }
}
```

### HTTP API

```bash
NOX_API_PORT=18802 node "$(npm root -g)/nox-mem/dist/api-server.js" &

curl -s localhost:18802/api/health | jq '{chunks, vectorCoverage}'
curl -s 'localhost:18802/api/search?q=deploy&limit=3' | jq '.[] | {score, source_file}'

# Grounded answer with citations — HTTP only for now, needs GEMINI_API_KEY
curl -s -X POST localhost:18802/api/answer \
  -H 'Content-Type: application/json' \
  -d '{"question": "what did we decide about deploys?"}' | jq
```

Do not use port 18800 — Chrome squats it. The server binds to `NOX_API_HOST` (set `127.0.0.1` to keep it local).

---

## §4 Not in the release yet

These appear in the paper and in [`PRIMITIVES.md`](PRIMITIVES.md) but are **not** in `nox-mem@3.3.0`. They live as staged patch sets under [`staged/`](../staged/) and are in development:

| Feature | Status on 3.3.0 |
|---|---|
| `nox-mem answer` (CLI) · `nox_mem_answer` (MCP) | Not shipped — use `POST /api/answer` |
| Temporal filter `--as-of` / `--changed-since` | CLI rejects the options; HTTP accepts `as_of` / `changed_since` but ignores them |
| `nox-mem init` | Not needed — the schema is created on first use |
| Directory ingest (`nox-mem ingest <dir>`) | Not supported — loop over files |

---

## §5 Common gotchas

| Symptom | Fix |
|---|---|
| `Done: 0 embedded, N errors` | `GEMINI_API_KEY` is not set in this shell |
| `Error: EISDIR` on ingest | You passed a directory — ingest one file at a time |
| `unknown command 'answer'` / `unknown option '--as-of'` | Not in the release yet — see §4 |
| `Could not locate the bindings file` (better-sqlite3) | `npm rebuild -g better-sqlite3`; install a C/C++ toolchain if it tries to compile |
| Data showed up in an unexpected place | `NOX_DB_PATH` was not exported in that shell |
| Port conflict on 18802 | `NOX_API_PORT=19000` (any free port) |

---

## §6 Next steps

| Resource | What's in it |
|---|---|
| [`README.md`](../README.md) | Feature list, architecture overview, benchmark numbers |
| [`docs/COMPARISON.md`](COMPARISON.md) | Benchmark comparison vs other memory systems |
| [`paper/paper-tecnico-nox-mem.md`](../paper/paper-tecnico-nox-mem.md) | Technical deep dive — salience formula, hybrid search, KG design |
| [`docs/CONFIGURATION.md`](CONFIGURATION.md) | Env var reference, provider swap |
| [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) | Five-layer architecture, module map, HTTP API reference |
| [`totobusnello/nox-mem`](https://github.com/totobusnello/nox-mem) | Engine source code |
| [Issues](https://github.com/totobusnello/memoria-nox/issues) | Bug reports, feature requests |
