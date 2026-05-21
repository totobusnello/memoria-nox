# opsAudit Issue #3B — Require Explicit db_source in withOpAudit (2026-05-21)

> **Status:** STAGED. PR `fix/opsaudit-3b-require-db-source` opened. Pending deploy.

## Context

Issue #3A (PR #193, commit `7362b29`) solved the immediate metric problem by filtering `op_name NOT LIKE 'test-%'` from `/api/health.opsAudit` and removing historical test rows. Issue #3B was deferred at the time.

This PR closes #3B: require an explicit `db_source` parameter in `withOpAudit()` at the TypeScript call site so the `unknown` bucket can never be created by omission. The fix is at the source code level, not the reporting layer.

## Problem Statement

Before this change, `withOpAudit(opName, fn)` derived `db_source` internally via `deriveDbSource()`:

```
Primary:   NOX_DB_SOURCE env
Fallback:  path heuristic (agents/<name>/ → name; tools/nox-mem/ → main)
Final:     'unknown'
```

When `NOX_DB_SOURCE` was unset and the path didn't match, every op landed in `byDbSource.unknown`. The reporting-layer filter (#3A) masked the symptom but didn't prevent new unknown rows from being created.

## Solution

**Signature change** — `withOpAudit()` now requires 3 arguments:

```typescript
// Before (2 args, db_source implicit):
await withOpAudit("reindex", async () => { ... });

// After (3 args, db_source REQUIRED):
await withOpAudit("reindex", { db_source: 'main' }, async () => { ... });
```

TypeScript compile-time enforcement: omitting `options` or `options.db_source` is a type error. No `'unknown'` fallback at the call site.

## Types Added

```typescript
// staged-1.7a/edits/op-audit.ts

export type DbSource = 'main' | 'shadow' | 'isolated' | 'test';

export interface WithOpAuditOptions {
  db_source: DbSource;  // REQUIRED — no default
}
```

## Files Changed

### Core (signature change)

| File | Change |
|---|---|
| `staged-1.7a/edits/op-audit.ts` | New 3-arg signature + `DbSource` + `WithOpAuditOptions` types + `snapshot()` receives `dbSource` from caller (no longer calls `deriveDbSource()` internally — `deriveDbSource()` kept but unused by `withOpAudit`) |

### Existing staged callers (already had entries)

| File | db_source assigned |
|---|---|
| `staged-1.7a/edits/reindex.ts` | `'main'` |
| `staged-1.7a/edits/backfill-source-type.ts` | `'main'` |
| `staged-1.7a/edits/index.ts` (kg-merge) | `'main'` |

### New staged entries (VPS callers not previously in staged)

| File | db_source assigned | Notes |
|---|---|---|
| `staged-1.7a/edits/compact.ts` | `'main'` | Full copy from VPS + patch |
| `staged-1.7a/edits/backfill-fts-anchor.ts` | `'main'` | Full copy from VPS + patch |
| `staged-1.7a/edits/graphify-ingest.ts` | `'main'` | Full copy from VPS + patch |
| `staged-1.7a/edits/cli/snapshot-main.ts` | `'main'` | Full copy from VPS + patch |
| `staged-1.7a/edits/cli/ocr-batch.ts` | `'main'` | Full copy from VPS + patch |
| `staged-1.7a/edits/scripts/migrate-v17-ops-audit.ts` | `'main'` | Full copy from VPS + patch |
| `staged-1.7a/edits/__tests__/op-audit-e2e.test.ts` | `'test'` | Test ops use `db_source: 'test'` |

### Audit

| File | Purpose |
|---|---|
| `audits/2026-05-21-opsaudit-3B-db-source-enforcement.md` | This file |

## Why 'main' for all prod callers

All production callers operate on the primary `nox-mem.db`. The `deriveDbSource()` heuristic correctly returned `'main'` for these callers when `NOX_DB_SOURCE` was set — but the point of #3B is to make that explicit in code, not rely on env/heuristic.

`'shadow'` would be correct for eval harness runs (G-series ablation) using `entity-eval.db`. Those are not wrapped by `withOpAudit` currently (eval harness has its own isolation via `NOX_DB_PATH`), so no staged callers use `'shadow'` in this PR.

## snapshot() filename impact

The `snapshot()` internal function previously called `deriveDbSource()` to qualify the snapshot filename. It now receives `dbSource` from `withOpAudit`:

```
Before: reindex-unknown-20260521143012-12345-abc.db  (when NOX_DB_SOURCE unset)
After:  reindex-main-20260521143012-12345-abc.db     (always explicit)
```

`deriveDbSource()` is kept for backward compatibility with any external snapshot callers but is no longer invoked by `withOpAudit` itself.

## TypeScript enforcement strategy

`db_source: DbSource` is a non-optional field in `WithOpAuditOptions`. The `options` parameter itself is non-optional (second positional arg). TypeScript strict mode catches:

1. Missing `options` entirely → `Expected 3 arguments, but got 2`
2. `options = {}` (missing db_source) → `Property 'db_source' is missing`
3. `db_source: 'unknown'` → `Type '"unknown"' is not assignable to type 'DbSource'`

## Deployment plan

Same pattern as hygiene PR #193:

```bash
# 1. Push op-audit.ts + all caller files to VPS src/
scp staged-1.7a/edits/op-audit.ts root@187.77.234.79:/root/.openclaw/workspace/tools/nox-mem/src/lib/
scp staged-1.7a/edits/reindex.ts ... <other callers>

# 2. Build
ssh root@187.77.234.79 'cd /root/.openclaw/workspace/tools/nox-mem && npx tsc --noEmit 2>&1 | head -20'
# If zero errors: npx tsc

# 3. Restart API
ssh root@187.77.234.79 'systemctl restart nox-mem-api'

# 4. Validate
curl http://127.0.0.1:18802/api/health | jq '.opsAudit.byDbSource'
# Expect: no 'unknown' key in the response
```

## Rollback

Revert PR, re-deploy from `main` branch. Old 2-arg signature is backward-incompatible at TypeScript level but behavior-identical at runtime if deployed incrementally (old callers don't pass options → runtime error "options is undefined"). Deploy op-audit.ts and all callers as a batch (which this PR ensures they are).

## Validation checklist

- [x] TypeScript types: `DbSource` union + `WithOpAuditOptions.db_source` required field
- [x] `snapshot()` receives explicit `dbSource` from `withOpAudit`
- [x] 3 existing staged callers updated: reindex, backfill-source-type, index.ts (kg-merge)
- [x] 7 VPS callers added to staged: compact, backfill-fts-anchor, graphify-ingest, cli/snapshot-main, cli/ocr-batch, scripts/migrate-v17-ops-audit, __tests__/op-audit-e2e.test.ts
- [x] E2E test uses `db_source: 'test'` (consistent with op_name 'test-' prefix filter)
- [ ] tsc --noEmit zero errors on VPS (run at deploy time)
- [ ] /api/health.opsAudit.byDbSource has no 'unknown' key after first op
- [ ] Daily nightly op `daily-main` shows `byDbSource.main` after restart

## Cross-links

- `audits/2026-05-21-opsaudit-hygiene-deployed.md` — Issues #1 + #3A (predecessor)
- `audits/2026-05-21-opsAudit-investigation.md` — original 3-issue analysis
- `staged-1.7a/DEPLOY-OPSAUDIT-HYGIENE.md` — deploy guide for #1 + #3A (reference pattern)
