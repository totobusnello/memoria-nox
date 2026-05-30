# vec0 Load Source Fix Migration

**Status:** SPEC (ready to apply next session) — tactical patch documented for source migration
**Date:** 2026-05-30
**Branch when applied:** `fix/db-vec0-load-source-migration`

## Problem

Tactical patch applied 2026-05-30 13:53 UTC directly to `dist/db.js` on VPS production. Next `npm run build` will revert the fix, causing `trg_chunks_delete_cascade` trigger to abort with `"no such module: vec0"` when CLI runs DELETE/INSERT on chunks table.

**Backup of pre-patch dist:** `/root/.openclaw/workspace/tools/nox-mem/dist/db.js.bak-pre-vec0-load-retry-20260530-135315`

## Root cause

`src/db.ts` initializes the SQLite database via `better-sqlite3` but does NOT load the `sqlite-vec` extension. Schema v18+ includes `vec_chunks` virtual table + `trg_chunks_delete_cascade` trigger that references `vec0` module. CLI operations (delete/insert chunks) trigger the cascade which fails without the extension loaded.

## Solution — source patch

Add sqlite-vec extension load BEFORE `ensureSchema(_db)` in `getDb()`.

**File:** `src/db.ts` (canonical source lives in `nox-workspace` repo on VPS at `/root/.openclaw/workspace/tools/nox-mem/src/db.ts`; will be migrated to `memoria-nox/src/` per Toto's plan)

**Injection point:** line ~78, after pragmas and before `ensureSchema(_db);`

### Diff

```diff
   _db.pragma("synchronous = NORMAL");    // Faster writes (WAL ensures safety)
+
+  // Load sqlite-vec extension (required for vec_chunks triggers on chunks table).
+  // Without this, trg_chunks_delete_cascade aborts with "no such module: vec0"
+  // when CLI runs DELETE/INSERT on chunks. Source fix migrated 2026-05-30 from
+  // tactical dist/db.js patch; persists across npm build.
+  try {
+    const VEC0_PATH = resolve(__dirname, "..", "node_modules", "sqlite-vec-linux-x64", "vec0");
+    _db.loadExtension(VEC0_PATH);
+  } catch (err) {
+    console.error("[db] sqlite-vec load failed (vec_chunks triggers may fail):", (err as Error).message);
+  }
+
   ensureSchema(_db);
   return _db;
 }
```

### Imports — already present

`resolve` from `path` and `__dirname` (defined via `fileURLToPath(import.meta.url)`) are already imported. No additional imports needed.

## Application steps (next session)

1. SSH to VPS OR pull `nox-workspace` repo locally
2. Edit `src/db.ts` per diff above
3. `npm run build` — verify `dist/db.js` regenerates with the fix
4. `diff dist/db.js dist/db.js.bak-pre-vec0-load-retry-20260530-135315` — should match the tactical patch
5. Restart `nox-mem-api` service to load new dist
6. Smoke test: CLI delete a chunk, verify no `"no such module: vec0"` error
7. Commit + push to `nox-workspace` repo (origin: github.com/totobusnello/nox-workspace.git)

## Verification

```bash
# Should print without errors:
node -e 'import("./dist/db.js").then(m => { const db = m.getDb(); console.log("OK", db.open); })'

# Trigger test:
nox-mem search "test" --limit 1  # should not crash
```

## Cleanup after migration

Once source fix is verified live:

```bash
# Remove obsolete tactical backups
rm /root/.openclaw/workspace/tools/nox-mem/dist/db.js.bak-pre-vec0-load-*
```

## Cross-platform consideration

Path `sqlite-vec-linux-x64/vec0` is hardcoded for Linux x64. For local Mac development:
- macOS arm64: `sqlite-vec-darwin-arm64/vec0`
- macOS x64: `sqlite-vec-darwin-x64/vec0`

Future improvement: detect platform dynamically:

```typescript
const platform = process.platform === "darwin"
  ? (process.arch === "arm64" ? "darwin-arm64" : "darwin-x64")
  : "linux-x64";
const VEC0_PATH = resolve(__dirname, "..", "node_modules", `sqlite-vec-${platform}`, "vec0");
```

But for production (Linux VPS), hardcoded path is fine.

## Risk

- **Low** — try/catch wraps load failure with console.error (degrades gracefully)
- vec0 already needed in production; load is non-destructive
- Idempotent (safe to apply multiple times)

## Testing already done

- Tactical patch verified working on VPS production 2026-05-30 13:53 UTC
- CLI DELETE/INSERT on chunks no longer aborts
- `trg_chunks_delete_cascade` trigger now successfully calls vec_chunks DELETE

## Estimated effort

- Edit src/db.ts: ~2 minutes
- Build + verify: ~5 minutes
- Total: <10 minutes

## Cross-links

- VPS tactical patch (current state): `/root/.openclaw/workspace/tools/nox-mem/dist/db.js` lines 69-77
- VPS pre-patch backup: `/root/.openclaw/workspace/tools/nox-mem/dist/db.js.bak-pre-vec0-load-retry-20260530-135315`
- VPS source canonical: `/root/.openclaw/workspace/tools/nox-mem/src/db.ts`
- Repo origin: github.com/totobusnello/nox-workspace.git
- Related: `trg_chunks_delete_cascade` (schema v18) requires vec0 in connection

## Open questions

- Should we migrate `nox-workspace/src/` entirely to `memoria-nox/src/` per Toto's plan? Separate session, larger scope.
- Should `loadExtension` happen at module load (not first `getDb()` call)? Currently it's first-call cost; subsequent calls hit the `if (_db && _db.open) return _db` fast path.

## Origem

Tactical patch aplicado em outra sessão (paralela ao session 2026-05-29/30 SOTA push). Spec criada 2026-05-30 ~16h UTC para migration permanente.
