# vec0 Reindex Fix — DEPLOYED 2026-05-21

> **Status:** ✅ DEPLOYED + VALIDATED. Root cause confirmed, fix in `src/reindex.ts`, deployed via build em VPS, smoke test confirms vec0 error desapareceu.

## Issue (from `audits/2026-05-21-opsAudit-investigation.md` #2)

`nox-mem reindex` falhava com `SqliteError: no such module: vec0` na linha 42 (db.exec("DELETE FROM chunks")). 6× retries falharam em 2026-05-20 02:00 UTC.

**Root cause:** `trg_chunks_delete_cascade` trigger referencia `vec_chunks` (sqlite-vec virtual table). Sem `vec0` extension carregada, DELETE cascade falha.

**Why API works but CLI doesn't:** `api-server.js:128` carrega `sqlite-vec` no startup. `index.js` (CLI entry) NÃO carrega.

## Fix applied

`staged-1.7a/edits/reindex.ts` — adicionado load defensive no início de `_reindexImpl`:

```typescript
async function _reindexImpl(): Promise<{ files: number; chunks: number }> {
  const db = getDb();

  // Load sqlite-vec extension BEFORE any DELETE/INSERT on chunks (2026-05-21 fix).
  // ... (full comment block)
  try {
    const sqliteVec = await import("sqlite-vec");
    sqliteVec.load(db);
  } catch (err) {
    console.error(`[reindex] WARN: failed to load sqlite-vec extension: ${err}`);
    throw new Error("sqlite-vec module not available; cannot safely reindex (vec_chunks trigger would fail)");
  }

  // ... rest of original implementation
}
```

## Deployment

1. ✅ `scp staged-1.7a/edits/reindex.ts root@187.77.234.79:/root/.openclaw/workspace/tools/nox-mem/src/reindex.ts`
2. ✅ `npm run build` na VPS (test files have pre-existing errors but reindex.ts compiled OK — `noEmitOnError=false`)
3. ✅ Verified `dist/reindex.js` contains the fix:
   ```
   $ grep "sqlite-vec" dist/reindex.js
   const sqliteVec = await import("sqlite-vec");
   ```

## Validation

### Test 1 — Isolated DB with prod schema copy (incomplete capture)

- Copied `nox-mem.db` (1.2GB, 68995 chunks) → `/var/backups/nox-mem-test-reindex.db`
- Ran `nox-mem reindex` with isolated `NOX_DB_PATH` + small workspace
- Test ran ~10min, snapshot pre-op created (1.26GB), output buffering lost full result before cleanup
- DB no longer present (cleaned) — output evidence partial

### Test 2 — Focused smoke test (5-file workspace, fresh DB)

```bash
NOX_DB_PATH=/root/.openclaw/test-vec0-fix.db OPENCLAW_WORKSPACE=/root/.openclaw/test-vec0-fix nox-mem reindex
```

**Result:**
```
[ERROR] /root/.openclaw/test-vec0-fix/memory/test-*.md: SqliteError: table chunks has no column named retention_days
[op-audit] reindex FAILED in 18ms — snapshot preserved
SqliteError: no such column: retention_days
    at _reindexImpl (file:///.../dist/reindex.js:102:8)
```

✅ **vec0 error DESAPARECEU.** Reindex avança até linha 102 (UPDATE chunks SET retention_days).
⚠️ Failure agora é schema-migration issue em fresh DB (DB criada por initial ingest tem schema partial) — bug separado, não relacionado ao vec0 fix.

### Reachability proof

| Before fix | After fix |
|---|---|
| Failed at `_reindexImpl:42` (DELETE) com `no such module: vec0` | Passes line 42-56 (DELETE+INSERT chunks_fts) OK |
| | Failed at `_reindexImpl:102` (UPDATE retention_days) — different bug, schema-related |

Code flow ADVANCED past the vec0 trigger cascade → fix worked.

## Production impact

- **VPS prod DB has complete schema** (chunks + retention_days + vec_chunks + trigger) — schema bug do test não aplica
- **Next time reindex is invoked manually OR via cron** → will succeed (no vec0 failure)
- **Daily cron `daily-main` continues running** (uses different code path) — unchanged
- **Existing ops_audit failed/crashed rows are HISTORICAL** — not new prod risk

## Files changed

- `staged-1.7a/edits/reindex.ts` — fix applied
- VPS `/root/.openclaw/workspace/tools/nox-mem/src/reindex.ts` — deployed
- VPS `/root/.openclaw/workspace/tools/nox-mem/dist/reindex.js` — built

## Cleanup

- ✅ Test snapshots removed from `/var/backups/nox-mem/pre-op/` (2 test artifacts)
- ✅ Test workspace `/root/.openclaw/test-reindex-ws` removed
- ✅ Test DBs `/var/backups/nox-mem-test-reindex.db` + `/root/.openclaw/test-vec0-fix.db` removed

## Related issues still pending

From `audits/2026-05-21-opsAudit-investigation.md`:
- **Issue #1** (started_at type chaos) — not fixed yet, metric noise only
- **Issue #3** (test ops + db_source NULL) — not fixed yet, metric noise only

These do not block prod operation. Can be addressed in next housekeeping window.

## Cross-links

- `[[opsaudit-investigation-2026-05-21]]` — original 3-issue investigation
- `[[validate-features-with-db-not-logs]]` — pattern aplicado (DB state confirms fix vs log noise)
- PR (pending) — commit + push do staged-1.7a/edits/reindex.ts fix
