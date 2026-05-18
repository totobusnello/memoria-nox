---
title: Configuration
description: Environment variables and runtime configuration for memoria-nox.
sidebar:
  order: 3
---

All configuration is done via environment variables. No config file required.

## Core

| Variable | Default | Description |
|---|---|---|
| `NOX_DB_PATH` | `~/.nox-mem/nox-mem.db` | Path to SQLite database file |
| `NOX_API_PORT` | `18802` | HTTP API listen port (never hardcode — Chrome uses 18800) |
| `NOX_LOG_LEVEL` | `info` | Log level: `debug`, `info`, `warn`, `error` |
| `OPENCLAW_WORKSPACE` | `~/.openclaw/workspace` | Base workspace path (all modules respect this) |

## Embedding providers

| Variable | Default | Description |
|---|---|---|
| `NOX_EMBEDDING_PROVIDER` | `gemini` | Provider: `gemini`, `openai`, `local` |
| `GEMINI_API_KEY` | — | Required for `gemini` provider |
| `OPENAI_API_KEY` | — | Required for `openai` provider |
| `NOX_EMBEDDING_BASE_URL` | — | Base URL for `local` provider (Ollama, etc.) |
| `NOX_EMBEDDING_MODEL` | `gemini-embedding-001` | Embedding model name |

:::caution[Gemini quota]
Never switch back to `gemini-2.5-flash` for embeddings — it exhausts the 3M/day quota. Keep `gemini-embedding-001`. KG extraction can use `gemini-2.5-flash` while volume is low.
:::

## Search

| Variable | Default | Description |
|---|---|---|
| `NOX_HYBRID_K` | `60` | RRF fusion parameter k |
| `NOX_FTS_LIMIT` | `20` | FTS5 candidate count before fusion |
| `NOX_VEC_LIMIT` | `20` | Vector candidate count before fusion |
| `NOX_SEARCH_LOG_TEXT` | `0` | Set `1` to log query text in `search_telemetry` |

## Salience

| Variable | Default | Description |
|---|---|---|
| `NOX_SALIENCE_MODE` | `shadow` | `shadow` (expose via `/api/health` only) or `active` (affects ranking) |

:::tip[Shadow discipline]
Ship ranking changes in shadow mode for ≥7 days before activating. The salience formula (`recency × pain × importance`) is accessible at `/api/health.salience` for offline comparison.
:::

## Operations

| Variable | Default | Description |
|---|---|---|
| `NOX_ALLOW_NO_SNAPSHOT` | `0` | Emergency override: allows destructive ops without pre-op snapshot. Use only when disk is full and snapshot failed — never as a shortcut. |
| `NOX_SALIENCE_SESSION` | — | Session ID override for CLI ↔ API session sync |

## Loading the environment

On VPS / cron / scripts, always source the env file before running any command:

```bash
set -a; source /root/.openclaw/.env; set +a
nox-mem vectorize
```

Without this, `vectorize` and `kg-extract` fail silently (`Done: 0 embedded, N errors`).
