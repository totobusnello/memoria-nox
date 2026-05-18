---
title: Schema Reference
description: Database schema V10 — tables, columns, migrations, and invariants.
sidebar:
  order: 3
---

## Current version: Schema V10

Schema version tracked via SQLite `PRAGMA user_version`. The `withOpAudit()` safety wrapper validates version match before any restore.

## Core tables

### `chunks`

The canonical text store. Every ingestible piece of content becomes one or more chunks.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `source` | TEXT | File path or URI |
| `content` | TEXT | Raw text content |
| `type` | TEXT | Chunk type: `markdown`, `entity`, `graphify`, etc. |
| `section` | TEXT | Entity file section: `compiled`, `frontmatter`, `timeline`, NULL for non-entity |
| `section_boost` | REAL | Ranking multiplier: compiled=2.0, frontmatter=1.5, timeline=0.8, legacy=1.0 |
| `pain` | REAL DEFAULT 0.2 | Severity 0.1 (trivial) → 1.0 (prod-outage) |
| `retention_days` | INTEGER | NULL = never-decay; 30/60/90/120/180/365 by type |
| `importance` | REAL | Salience component |
| `created_at` | INTEGER | Unix timestamp |
| `updated_at` | INTEGER | Unix timestamp |

### `chunks_fts`

FTS5 virtual table. Populated by triggers on `chunks` INSERT/UPDATE/DELETE.

:::note
FTS5 uses AND-strict semantics by default. Multi-word natural language queries may return zero FTS results — this is by design, not a bug. Hybrid search always runs the vector layer alongside FTS, so recall remains high.
:::

### `vec_chunks`

sqlite-vec 3072-dimensional float32 vectors. One row per embedded chunk.

### `vec_chunk_map`

Maps vec row IDs back to `chunks.id`. Used by vector search to return chunk content.

### `kg_entities`

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | — |
| `name` | TEXT | Entity name |
| `type` | TEXT | person, project, concept, tool, etc. |
| `description` | TEXT | Short description |
| `chunk_ids` | TEXT | JSON array of source chunk IDs |

### `kg_relations`

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | — |
| `source_entity_id` | INTEGER FK | `kg_entities(id)` |
| `target_entity_id` | INTEGER FK | `kg_entities(id)` |
| `relation` | TEXT | Relation type (uses, depends_on, leads, etc.) |
| `weight` | REAL | Relation strength |

:::caution[FK pattern]
Relations use integer FK columns (`source_entity_id`, `target_entity_id`), not inline string names. SPO queries require dual JOIN on `kg_entities`.
:::

### `ops_audit`

Append-only operation log. DELETE and UPDATE of terminal-status rows are blocked by DB triggers (CWE-693 defense).

| Status | Terminal? |
|---|---|
| `started` | No |
| `success` | Yes |
| `failed` | Yes |
| `crashed` | Yes |

`completed` and `rolled_back` are **not** valid statuses despite appearing in old docs.

### `search_telemetry`

Query log with 4 extended columns (since v11): `query_text`, `golden_id`, `top_chunk_ids`, `top_scores`. Opt-in via `NOX_SEARCH_LOG_TEXT=1`.

## Schema migrations

Migrations in `staged-migrations/`:

| Version | Change |
|---|---|
| v11 | `search_telemetry` + 4 telemetry columns |
| v19 | `confidence` + `provenance` fields |
| v20 | `viewer_events` table |
| v21 | `conflict_audit` table |
| v22 | `confidence_eval_log` table |

Apply via [staged-migrations/README.md](https://github.com/totobusnello/memoria-nox/blob/main/staged-migrations/README.md).

## Invariants (checked */15min)

1. `section` NOT NULL on entity chunks
2. `feedback` and `person` types have `retention_days IS NULL` (never-decay)
3. `ops_audit` has no failed rows without `error_message`
4. `section_boost` consistent with `section` value

Invariant failures trigger Discord alerts.

## Safety rules

- **NEVER `sed -i` on `.db` files** — SQLite page boundaries corrupt silently. Filter sweeps to `{json,md,sh,txt,jsonl,env}` only.
- **NEVER `cp snapshot.db nox-mem.db` directly** — use `safeRestore()` in `src/lib/op-audit.ts` which validates `user_version` match and removes stale WAL/SHM files.
