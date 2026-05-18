---
title: CLI Recipes
description: Scripting and automation recipes for the nox-mem CLI.
sidebar:
  order: 4
---

Full source: [`integrations/cli/`](https://github.com/totobusnello/memoria-nox/tree/main/integrations/cli)

## All 26+ commands

```bash
nox-mem --help
```

| Command | Description |
|---|---|
| `search <query>` | Hybrid search |
| `answer <question>` | Grounded answer with citations |
| `ingest <path>` | Ingest file or directory |
| `ingest-entity <file>` | Ingest structured entity file |
| `reindex [--dry-run]` | Reindex all chunks |
| `vectorize` | Embed unembedded chunks |
| `kg-build` | Build / update knowledge graph |
| `kg-prune [--dry-run]` | Prune stale KG entities |
| `kg-search <query>` | Search KG entities |
| `kg-path <from> <to>` | Find path between entities |
| `cross-search <query>` | Search across multiple stores |
| `reflect` | Reflection and consolidation |
| `crystallize [--dry-run]` | Crystallize memories |
| `stats` | Corpus statistics |
| `health` | Health check |
| `serve` | Start HTTP API server |
| `mcp` | Start MCP server |
| `init <path>` | Initialize new memory store |
| `restore --snapshot <path>` | Restore from op-audit snapshot |

## Recipes

### Daily ingest from Obsidian vault

```bash
#!/bin/bash
set -a; source /root/.openclaw/.env; set +a

nox-mem ingest ~/obsidian-vault --changed-since 24h
nox-mem vectorize
echo "Done: $(nox-mem stats --json | jq .totalChunks) chunks"
```

### Search and pipe to jq

```bash
nox-mem search "salience formula" --json | jq '.[].content'
```

### Dry-run before destructive operations

```bash
# Always preview before reindex
nox-mem reindex --dry-run
# Output: { "wouldDelete": 0, "wouldProcess": 69298, "protected": 183, "estimatedDuration": "2m30s" }

# Then run for real
nox-mem reindex
```

### Health check in scripts

```bash
COVERAGE=$(curl -s http://127.0.0.1:18802/api/health | jq '.vectorCoverage.embedded / .vectorCoverage.total')
if (( $(echo "$COVERAGE < 0.95" | bc -l) )); then
  echo "WARNING: vector coverage is $COVERAGE" >&2
  exit 1
fi
```

### Batch ingest with tmux (long-running)

```bash
# Use tmux for long batches — nohup alone is fragile
tmux new-session -d -s ingest 'set -a; source /root/.openclaw/.env; set +a && nox-mem ingest /large/corpus && nox-mem vectorize'
tmux attach -t ingest
```

### KG path query

```bash
nox-mem kg-path "memoria-nox" "sqlite-vec" --json | jq '.path[].name'
```
