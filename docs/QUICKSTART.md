# nox-mem — 5-Minute Quickstart

> Pain-weighted hybrid memory for AI agents. SQLite on your disk. Provider your choice. Zero vendor lock-in.

**Where the code lives.** This repository (`memoria-nox`) is the research lab: paper, eval harnesses, specs. It has no `package.json` at the root and is **not** meant to be cloned and built. The engine is developed in [`totobusnello/nox-mem`](https://github.com/totobusnello/nox-mem) and published to npm as [`nox-mem`](https://www.npmjs.com/package/nox-mem). Everything below uses the npm package.

Install, ingest, keyword and temporal search, `reindex`, `doctor`, `answer --help`, the MCP server and the HTTP API were run against `nox-mem@3.4.0` installed from npm into a clean directory (2026-09-28). Steps that need a Gemini key (`vectorize`, `kg-build`, an `answer` that calls the LLM) were not exercised in that run.

---

## §1 Install (2min)

### Prerequisites

| Requirement | Check | Notes |
|---|---|---|
| Node.js 20+ | `node --version` | `engines: >=20`; install tested on Node 26 |
| C/C++ toolchain | `xcode-select -p` (macOS) · `gcc --version` (Linux) | Only needed when no prebuilt `better-sqlite3` binary matches your Node version. Linux: `apt-get install -y build-essential python3` |
| Gemini API key | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | **Optional.** Free tier works. Without it, search is keyword-only (FTS5) and still answers natural-language questions |

SQLite, FTS5 and `sqlite-vec` ship inside the package — no system SQLite needed.

### Install

```bash
npm install -g nox-mem
nox-mem --version            # 3.4.0

# Optional — enables semantic search, KG extraction and answer
export GEMINI_API_KEY=AIza...
```

The store is created on first use at **`~/.nox-mem/nox.db`**. To put it elsewhere, `export NOX_DB_PATH=/path/to/nox.db` in every shell that runs `nox-mem` (or in your MCP client config). `nox-mem doctor` prints the path in use.

> Upgrading from ≤3.3: if you never set `NOX_DB_PATH`, your data sits inside the package at `<npm root -g>/nox-mem/nox-mem.db` and 3.4 keeps using it — with a warning, because `npm update -g` replaces that directory. Move it: `mkdir -p ~/.nox-mem && mv "$(npm root -g)/nox-mem/nox-mem.db" ~/.nox-mem/nox.db`.

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

Without embeddings you will see `Vector index empty — run 'nox-mem vectorize' first. Falling back to FTS5.` — search still works. Keyword search needs every term to match, so when a question finds nothing, nox-mem retries with any of its content words (`NOX_FTS_OR_FALLBACK`, on by default only when no embedding key is set).

### Time-travel and recency window

Hard SQL pre-filters on ingestion time, not ranking boosts:

```bash
nox-mem search "deploy" --as-of 2026-04-01        # chunks that existed that day (whole day, UTC)
nox-mem search "deploy" --changed-since 7d        # created or updated in the last 7 days
nox-mem search "deploy" --as-of 2026-05-01 --changed-since 30d
```

Dates: `2026-05-01`, `2026-05-01T10:00:00Z` (no offset ⇒ UTC), or relative `15m`, `2h`, `7d`, `1w` (`1mo` is not supported — use `30d`). A bad date exits with code 2 instead of silently searching without the filter. `--as-of` answers *which chunks existed then*, not *what they said then*: there is no version history.

### Grounded answer (needs `GEMINI_API_KEY`)

```bash
nox-mem answer "what did we decide about deploys?"
nox-mem answer --help        # --top-k, --json, --no-cite, ...
```

`answer` does not take `--as-of` / `--changed-since` yet.

### Inspect

```bash
nox-mem stats      # chunk counts, tiers, DB size
nox-mem doctor     # health check
nox-mem --help     # all subcommands
```

`doctor` has two groups. **Core** (SQLite, FTS5 index, embeddings, consolidation) is what ingest and search need. **Optional integrations** (Ollama, Notion, file watcher) marked ⚪ are simply not set up — fine to skip. `nox-mem doctor --quiet` prints only core problems and exits 1 if one failed, for scripts.

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

`nox-mem-mcp` starts the MCP server over stdio: 20 tools (`nox_mem_search` with `as_of` / `changed_since`, `nox_mem_ingest`, `nox_mem_stats`, `nox_mem_kg_query`, `nox_mem_kg_path`, `nox_mem_reflect`, `nox_mem_decision_*`, ...).

```bash
# Claude Code
claude mcp add nox-mem -e GEMINI_API_KEY="$GEMINI_API_KEY" -- nox-mem-mcp
```

For clients configured by JSON (Cursor, Cline, ...):

```json
{
  "mcpServers": {
    "nox-mem": {
      "command": "nox-mem-mcp",
      "env": { "GEMINI_API_KEY": "AIza..." }
    }
  }
}
```

Add `"NOX_DB_PATH"` to `env` if you moved the store away from `~/.nox-mem/nox.db`.

### HTTP API

```bash
NOX_API_PORT=18802 NOX_API_HOST=127.0.0.1 nox-mem-api &

curl -s localhost:18802/api/health | jq '{chunks, vectorCoverage}'
curl -s 'localhost:18802/api/search?q=deploy&limit=3' | jq '.[] | {score, source_file}'
curl -s 'localhost:18802/api/search?q=deploy&changed_since=7d' | jq length

# Grounded answer with citations — needs GEMINI_API_KEY
curl -s -X POST localhost:18802/api/answer \
  -H 'Content-Type: application/json' \
  -d '{"question": "what did we decide about deploys?"}' | jq
```

Do not use port 18800 — Chrome squats it. A bad `as_of` / `changed_since` returns HTTP 400.

---

## §4 `reindex` — usually not needed

`reindex` rebuilds the index **only** from `$OPENCLAW_WORKSPACE/memory` and `$OPENCLAW_WORKSPACE/shared` (the layout of the origin deployment). If you add notes with `nox-mem ingest <file>`, you do not need it.

Safety since 3.4:

- no source directory, or an empty one while the DB holds chunks ⇒ it **refuses before touching the DB** (exit 1);
- a rebuild that would drop more than 10% of the distinct content ⇒ it refuses **before** deleting anything;
- unchanged content is kept as-is (same id, same embedding) instead of being duplicated;
- `nox-mem reindex --dry-run` previews without writing.

Chunks ingested from outside the workspace are still treated as orphans by a reindex that does run.

---

## §5 Common gotchas

| Symptom | Fix |
|---|---|
| `Done: 0 embedded, N errors` | `GEMINI_API_KEY` is not set in this shell |
| `Error: EISDIR` on ingest | You passed a directory — ingest one file at a time |
| `unknown command 'answer'` / `unknown option '--as-of'` | You are on ≤3.3 — `npm install -g nox-mem@latest` |
| `REFUSED before touching the DB` on reindex | Expected on a standalone install — see §4 |
| `database is inside node_modules` warning | Move the DB — see the upgrade note in §1 |
| `Could not locate the bindings file` (better-sqlite3) | `npm rebuild -g better-sqlite3`; install a C/C++ toolchain if it tries to compile |
| Port conflict on 18802 | `NOX_API_PORT=19000` (any free port) |

---

## §6 Next steps

| Resource | What's in it |
|---|---|
| [`README.md`](../README.md) | Feature list, architecture overview, benchmark numbers |
| [`docs/PRIMITIVES.md`](PRIMITIVES.md) | `search`, `answer` and the temporal filter — exact semantics |
| [`docs/COMPARISON.md`](COMPARISON.md) | Benchmark comparison vs other memory systems |
| [`paper/paper-tecnico-nox-mem.md`](../paper/paper-tecnico-nox-mem.md) | Technical deep dive — salience formula, hybrid search, KG design |
| [`docs/CONFIGURATION.md`](CONFIGURATION.md) | Env var reference, provider swap |
| [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) | Five-layer architecture, module map, HTTP API reference |
| [`totobusnello/nox-mem`](https://github.com/totobusnello/nox-mem) | Engine source code |
| [Issues](https://github.com/totobusnello/memoria-nox/issues) | Bug reports, feature requests |
