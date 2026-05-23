# VACUUM INTO + ATTACH reverse pattern — better-sqlite3 limitation

**Timeline:** PR #286 (2026-05-24) P2 migration script — agent caught invalid algorithm sketched in task brief.

**Context:** A2 Tier 3 needs to migrate plaintext nox-mem.db → encrypted. Algorithm sketched in brief:
```javascript
// SKETCHED (DOES NOT WORK with better-sqlite3)
const db = new Database('nox-mem.db');
db.exec(`ATTACH DATABASE 'target.db' AS encrypted KEY 'secret'`);
db.exec(`VACUUM INTO encrypted.target.db`);
```

**Problem:** better-sqlite3 (currently v11.x) doesn't support **multiple open connections** to same database + ATTACH syntax properly. The `ATTACH` plumbing works in sqlite3 CLI, but better-sqlite3's synchronous JavaScript bindings don't handle ATTACH database context switches reliably.

**Error signature:**
```
Error: SQLITE_CANTOPEN: unable to open database file
at Database.exec (better_sqlite3.js:...)
```

Happens at `VACUUM INTO` step — target attachment context is lost.

**Correct pattern (PR #286 — reverse order):**
Instead of opening plaintext → attach encrypted, do **reverse**:
1. Open/create encrypted DB separately (fresh instance)
2. Copy schema + data via **JavaScript-level copy** (read chunks, insert encrypted)
3. Close both
4. Atomic rename

```javascript
// CORRECT (reverse pattern)
const plainDb = new Database('nox-mem.db');  // No PRAGMA
const encDb = new Database('nox-mem-encrypted.db');
encDb.pragma('key=secret');

// Read schema from plain
const schema = plainDb.exec(`SELECT sql FROM sqlite_master 
  WHERE type='table'`);

// Recreate schema in encrypted
schema.forEach(stmt => encDb.exec(stmt.sql));

// Copy data (chunk-at-a-time to handle large tables)
const chunks = plainDb.prepare(`SELECT * FROM chunks LIMIT 1000`);
const insert = encDb.prepare(`INSERT INTO chunks VALUES (...)`);

for (const row of chunks.all()) {
    insert.run(...Object.values(row));
}

plainDb.close();
encDb.close();
fs.renameSync('nox-mem-encrypted.db', 'nox-mem.db');
```

**Why reverse works:**
- No ATTACH needed — two separate Database instances
- `PRAGMA key` applied **before any schema/data access** in encrypted DB
- SQLite page cipher initialized on `new Database()` + PRAGMA, not on open
- JavaScript loop handles row iteration — better-sqlite3's strength

**Trade-off:** JavaScript-level copy is slower than VACUUM INTO (no kernel-level copy). For 69.5k chunks + KG tables, expect ~30-60s on mid-range VPS. Acceptable for offline migration (scheduled maintenance window).

**Alternative (future):** Upgrade to better-sqlite3 v12+ if it improves ATTACH handling. For now, reverse pattern is the production-ready path.

**Status:** PR #286 implements reverse pattern. Migration script includes `--dry-run` mode (reads only, no write) to validate setup before actual migration.

**Reference:** better-sqlite3 issue #1489 (ATTACH context). PR #286 runbook section 3.

**Lesson:** Clever database operations don't always map 1:1 from SQL CLI → driver API. Test with real driver, not mental model.
