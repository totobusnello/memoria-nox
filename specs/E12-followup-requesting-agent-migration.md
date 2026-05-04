# E12 Followup: `requesting_agent` Column Migration

**Spec ID:** E12-followup-requesting-agent-migration
**Status:** Ready for implementation — no authorization gate required
**Effort:** ~1h implementation + 2-week telemetry collection window + ~5min re-evaluation
**Risk:** Minimal — additive schema change; backfill is non-blocking; no prod restart needed

---

## 1. Motivation

Cross-agent retrieval quantification is Differentiator #3 of the nox-mem paper:
> "Shared-canonical multi-agent memory without federation overhead enables cross-agent intelligence — a retrieval property no existing system measures."

Storage-level cross-agent coverage has been validated at 99.92% (E12 Q1, 2026-05-04). However, retrieval-level quantification — the percentage of queries whose highest-ranked result was authored by a different agent than the one issuing the query — remains unmeasured. This gap blocks paper §5.6 (Q2–Q6 of `cross_agent_quantifier.py`).

The missing piece is a single nullable column in `search_telemetry` that records which agent issued each search call. Without it, `cross_agent_quantifier.py` cannot join query origin to chunk authorship and compute the cross-agent retrieval rate.

---

## 2. Schema Change

Apply once on the production database. The statement is idempotent via the `IF NOT EXISTS` guard available in SQLite 3.37+; on older versions, wrap in a try/catch in the migration script.

```sql
ALTER TABLE search_telemetry ADD COLUMN requesting_agent TEXT;
```

- Type: `TEXT`, nullable.
- Default: `NULL` (historical rows remain null; populated going forward).
- No index required at this stage — Q2–Q6 queries group by this column on a table that will remain in the tens of thousands of rows.

Migration script: `scripts/migrate-requesting-agent.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
DB="${NOX_DB_PATH:-/root/.openclaw/workspace/tools/nox-mem/nox-mem.db}"
sqlite3 "$DB" "ALTER TABLE search_telemetry ADD COLUMN requesting_agent TEXT;" 2>/dev/null || true
echo "Migration complete."
```

---

## 3. Code Change — `src/search.ts`

### 3.1 Signature update

Extend `logTelemetry()` to accept `requestingAgent`:

```typescript
async function logTelemetry(
  params: TelemetryParams & { requestingAgent?: string | null }
): Promise<void>
```

The field defaults to `null` when callers do not supply it, preserving backward compatibility with all existing call sites.

### 3.2 Agent identifier resolution (caller side)

Callers populate `requestingAgent` via the following priority chain:

| Call surface | Source |
|---|---|
| CLI (`nox-mem search`) | `process.env.NOX_AGENT_NAME` |
| MCP server | `process.env.NOX_AGENT_NAME` (set per-agent in systemd unit) |
| HTTP API (`POST /api/search`) | `X-Agent-Name` request header; falls back to `NOX_AGENT_NAME` env |

The value is stored as-is (free-form string). Recommended convention: lowercase slug, e.g. `nox`, `atlas`, `boris`, `cipher`, `forge`, `lex`.

### 3.3 No schema version bump required

This migration does not alter retrieval or scoring behavior. Schema `user_version` remains at the current value. Document the column addition in `docs/EVOLUTION.md` under the next patch entry.

---

## 4. Backfill

Historical rows carry `NULL` for `requesting_agent`. A lightweight backfill labels them `'unknown'` to simplify Q2–Q6 aggregations:

```sql
UPDATE search_telemetry
SET requesting_agent = 'unknown'
WHERE requesting_agent IS NULL;
```

Run as a background job (not in the migration script) to avoid locking the table during peak hours. A single `UPDATE` on the current table size (~tens of thousands of rows) completes in under one second; no chunking is needed.

---

## 5. Validation

After two weeks of telemetry with `requesting_agent` populated:

1. Verify coverage: `SELECT COUNT(*) FROM search_telemetry WHERE requesting_agent IS NOT NULL` should equal the total row count minus pre-migration rows.
2. Re-run `cross_agent_quantifier.py` with `--questions Q2 Q3 Q4 Q5 Q6`.
3. Expected output: cross-agent retrieval rate (%) per agent pair, confirming or challenging the 99.92% storage-level figure at retrieval level.
4. Integrate result into paper §5.6.

**Gate:** No minimum threshold required to proceed with paper writing — any non-null result (positive or null effect) provides publishable evidence for or against Differentiator #3.

---

## 6. Effort and Risk Summary

| Dimension | Estimate |
|---|---|
| Implementation (migration + code change) | ~1h |
| Prod downtime | None |
| Telemetry collection window | 2 weeks |
| Re-evaluation run | ~5 min |
| Rollback complexity | None — column is nullable; removing it requires a table rebuild but is never necessary |

Authorization: none required. Implementation can proceed at any time within W2 (2026-05-11–17).
