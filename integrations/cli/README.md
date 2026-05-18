# CLI — nox-mem command reference

nox-mem ships 26+ subcommands. The binary is `nox-mem` (entry point: `dist/index.js`).

```bash
nox-mem --help     # list all subcommands
nox-mem <cmd> --help   # help for a specific command
```

---

## Key subcommands

| Command | Description |
|---|---|
| `nox-mem init <path>` | Initialize a new memory store (SQLite + schema) |
| `nox-mem serve` | Start the HTTP API on `NOX_API_PORT` (default 18802) |
| `nox-mem mcp` | Start the MCP server (stdio) |
| `nox-mem ingest <path>` | Ingest a file or directory |
| `nox-mem ingest-entity <file>` | Ingest an entity file (3-section: compiled/frontmatter/timeline) |
| `nox-mem search <query>` | Hybrid search (BM25 + semantic + RRF) |
| `nox-mem answer <question>` | Grounded answer with citations |
| `nox-mem reflect <query>` | Check reflect cache |
| `nox-mem vectorize` | Embed unvectorized chunks |
| `nox-mem reindex` | Rebuild FTS5 index (destructive — use `--dry-run` first) |
| `nox-mem kg-build` | Extract entities + relations |
| `nox-mem kg-prune` | Remove orphaned KG nodes |
| `nox-mem cross-search <query>` | Search across all agent DBs |
| `nox-mem crystallize <topic>` | Consolidate low-salience chunks |
| `nox-mem archive export <output>` | Export store to portable archive (A2) |
| `nox-mem archive import <input>` | Import archive into store (A2) |
| `nox-mem conflicts scan` | Scan for KG conflicts (L2, pending impl) |
| `nox-mem conflicts list` | List unresolved conflicts |
| `nox-mem conflicts resolve <id>` | Resolve a conflict |
| `nox-mem connect <ide>` | Inject MCP block into IDE config (P4, pending impl) |
| `nox-mem disconnect <ide>` | Remove nox-mem MCP block from IDE config |
| `nox-mem cli-stats` | Telemetry: top usage, slow, error-prone commands |

---

## Output formats

Most commands accept `--json` for machine-readable output:

```bash
nox-mem search "shadow discipline" --json | jq '.[0].content'
nox-mem kg-build --dry-run --json | jq '.would_process'
```

---

## Guides

- [Common workflows / recipes](recipes.md) — 10 real-world patterns
- [Shell scripting](scripting.md) — env loading, cron, systemd templates
