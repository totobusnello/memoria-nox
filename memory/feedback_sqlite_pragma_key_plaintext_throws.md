# SQLite PRAGMA key + plaintext DB mismatch — cannot retrofit encryption

**Timeline:** PR #280 A2 Tier 3 canary test (2026-05-24) caught critical bug before production.

**Problem:** A2 Tier 3 (Encrypted memory backups) adds **PRAGMA key=<password>** to nox-mem.db. But existing plaintext database cannot be opened with PRAGMA key applied — SQLite refuses to read encrypted header.

**Scenario:**
1. Existing deployment: `nox-mem.db` is plaintext, 69.5k chunks
2. Operator enables Tier 3: adds `PRAGMA key='secret'` to db.ts module
3. App restarts, tries to open nox-mem.db with cipher
4. SQLite throws: `file is not a database` (header mismatch)
5. Zero queries execute. Alerts fire. Downtime.

**Why it fails:** SQLite's `PRAGMA key` statement only works on **new databases** or databases that were previously encrypted with the same key. Plaintext databases have unencrypted pages. SQLite's cipher plugin (better-sqlite3-multiple-ciphers) validates the page header on open; mismatch = corruption error.

**Attempted fix (WRONG — PR #286):**
```javascript
// DOES NOT WORK
const db = new Database('nox-mem.db');
db.pragma('key=secret');  // Too late! Pages already read as plaintext
```

SQLite reads the first page during `new Database()` call, before PRAGMA. By the time PRAGMA key is called, database is already in "plaintext mode."

**Correct fix (PR #286 — VACUUM INTO + atomic swap):**
```javascript
// 1. Open plaintext DB
const plainDb = new Database('nox-mem.db');

// 2. ATTACH encrypted target
plainDb.exec(`
  ATTACH DATABASE 'nox-mem-encrypted.db' AS encrypted 
  KEY 'secret'
`);

// 3. Copy schema + data via VACUUM INTO (atomically)
plainDb.exec(`
  VACUUM INTO 'nox-mem-encrypted.db'
`);

// 4. Close plaintext, swap files atomically
plainDb.close();
fs.renameSync('nox-mem-encrypted.db', 'nox-mem.db');
```

**Key insight:** `VACUUM INTO` is the **only** way to migrate plaintext → encrypted. PRAGMA key must be applied **during attachment**, not after open.

**Schema requirement (PR #280 canary):** Test covers round-trip:
- Create plaintext DB with 100 rows
- Call encrypt migration script
- Open with PRAGMA key — verify 100 rows still there
- Verify plaintext copy deleted

**Status:** Migration script pinned in PR #286. A2 Tier 3 rollout gated on successful dry-run on test DB. PR #280 canary test mandatory before prod enable.

**Reference:** SQLite cipher plugin docs. better-sqlite3-multiple-ciphers issue #73. Incident type: "silent data visibility escalation."

**Applies to:** Any memory system with future encryption features (A2, A3, etc).
