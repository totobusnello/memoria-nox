// staged-A2-T3/edits/src/lib/__tests__/db.crypto.test.ts
//
// A2 Tier 3 / Phase 1 — crypto open-path tests for staged db.ts wire-up.
//
// Tests cover (per task brief §3):
//   1. Encrypted open with key → write 5 rows → close → reopen same key → read 5 rows back
//   2. Reopen with WRONG key → throws SqliteError "file is not a database"
//   3. Reopen with NO key (when DB was encrypted) → throws
//   4. Plaintext mode (NOX_DB_KEY unset) → all existing migrations + writes work
//   5. NOX_DB_REQUIRE_KEY=1 + key missing → throws at getDb() open time
//   6. VACUUM INTO snapshot of encrypted DB → reopen with same key → data preserved
//   7. defaultSafeIntegers(true) — INTEGER columns return BigInt (vec0 contract)
//
// Test harness avoids the getDb() singleton on purpose:
// - The singleton in db.ts caches across import calls within a module.
// - Each test needs a FRESH process-env + FRESH DB file.
// - We exercise the raw better-sqlite3-multiple-ciphers binding directly to
//   validate the PRAGMA pattern, then a small subset of tests do dynamic
//   import of db.ts with mutated process.env + NOX_DB_PATH to validate the
//   integration wiring.
//
// Run: cd staged-A2-T3 && npm test

import { test, describe, before, after } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, existsSync, statSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import Database from "better-sqlite3-multiple-ciphers";

const TMP_ROOT = mkdtempSync(join(tmpdir(), "nox-mem-a2-t3-crypto-"));

/**
 * Apply the same PRAGMA pattern used in production db.ts. Kept in lock-step
 * with applyCipherPragmas() in edits/src/lib/db.ts — if you change one, change
 * both.
 */
function openEncrypted(path: string, key: string): Database.Database {
  const db = new Database(path);
  db.pragma(`cipher='sqlcipher'`, { simple: true });
  db.pragma(`legacy=4`, { simple: true });
  db.pragma(`cipher_compatibility=4`, { simple: true });
  const escapedKey = key.replace(/'/g, "''");
  db.pragma(`key='${escapedKey}'`, { simple: true });
  db.defaultSafeIntegers(true);
  return db;
}

function openPlaintext(path: string): Database.Database {
  const db = new Database(path);
  db.defaultSafeIntegers(true);
  return db;
}

after(() => {
  try { rmSync(TMP_ROOT, { recursive: true, force: true }); } catch { /* best-effort */ }
});

// ────────────────────────────────────────────────────────────────────────────
// 1. Encrypted round-trip — write 5 rows, close, reopen same key, read back.
// ────────────────────────────────────────────────────────────────────────────
describe("encrypted round-trip", () => {
  const DB_PATH = join(TMP_ROOT, "roundtrip.db");
  const KEY = "test-key-1-spike-pass";

  test("write 5 rows then reopen with same key reads same 5 rows", () => {
    // Phase A — open + write
    {
      const db = openEncrypted(DB_PATH, KEY);
      db.exec(`CREATE TABLE chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        src TEXT NOT NULL
      )`);
      const ins = db.prepare("INSERT INTO chunks (content, src) VALUES (?, ?)");
      for (let i = 1; i <= 5; i++) ins.run(`row-${i}`, "crypto-test");
      const count = db.prepare("SELECT count(*) AS n FROM chunks").get() as { n: bigint };
      // safe-integers mode returns BigInt for INTEGER columns
      assert.equal(count.n, 5n);
      db.close();
    }
    // Phase B — reopen, read
    {
      assert.equal(existsSync(DB_PATH), true);
      const db = openEncrypted(DB_PATH, KEY);
      const rows = db.prepare("SELECT id, content, src FROM chunks ORDER BY id").all() as Array<{ id: bigint; content: string; src: string }>;
      assert.equal(rows.length, 5);
      for (let i = 0; i < 5; i++) {
        const r = rows[i]!;
        assert.equal(r.content, `row-${i + 1}`);
        assert.equal(r.src, "crypto-test");
      }
      db.close();
    }
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 2. Wrong-key rejection — must throw with deterministic message.
// ────────────────────────────────────────────────────────────────────────────
describe("wrong-key rejection", () => {
  const DB_PATH = join(TMP_ROOT, "wrongkey.db");
  const KEY = "correct-key-x";
  const WRONG_KEY = "wrong-key-y";

  before(() => {
    const db = openEncrypted(DB_PATH, KEY);
    db.exec("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)");
    db.prepare("INSERT INTO t (v) VALUES (?)").run("encrypted");
    db.close();
  });

  test("reopen with wrong key throws SqliteError on first query", () => {
    const db = openEncrypted(DB_PATH, WRONG_KEY);
    assert.throws(
      () => db.prepare("SELECT count(*) AS n FROM t").get(),
      (err: Error) => /file is not a database|not a database|HMAC|file is encrypted/i.test(err.message),
      "wrong key should trigger 'file is not a database' (or HMAC-failure cousin)",
    );
    db.close();
  });

  test("reopen with empty key throws", () => {
    const db = openEncrypted(DB_PATH, "");
    assert.throws(
      () => db.prepare("SELECT count(*) AS n FROM t").get(),
      (err: Error) => /file is not a database|not a database|HMAC|file is encrypted/i.test(err.message),
      "empty key should be rejected as 'not a database'",
    );
    db.close();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 3. Encrypted DB opened without ANY key PRAGMA throws.
// ────────────────────────────────────────────────────────────────────────────
describe("encrypted DB opened without key", () => {
  const DB_PATH = join(TMP_ROOT, "nokey.db");
  const KEY = "the-real-key";

  before(() => {
    const db = openEncrypted(DB_PATH, KEY);
    db.exec("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)");
    db.prepare("INSERT INTO t (v) VALUES (?)").run("payload");
    db.close();
  });

  test("plain open of encrypted DB throws on first query", () => {
    const db = openPlaintext(DB_PATH);
    assert.throws(
      () => db.prepare("SELECT count(*) AS n FROM t").get(),
      (err: Error) => /file is not a database|not a database|file is encrypted/i.test(err.message),
      "plaintext open of encrypted DB must fail with 'file is not a database'",
    );
    db.close();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 4. Plaintext mode (no key set) — backward-compat path.
// ────────────────────────────────────────────────────────────────────────────
describe("plaintext mode (backward-compat)", () => {
  const DB_PATH = join(TMP_ROOT, "plaintext.db");

  test("open without key + write 5 rows + reopen reads 5 rows", () => {
    {
      const db = openPlaintext(DB_PATH);
      db.exec(`CREATE TABLE chunks (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT)`);
      const ins = db.prepare("INSERT INTO chunks (content) VALUES (?)");
      for (let i = 1; i <= 5; i++) ins.run(`plain-row-${i}`);
      db.close();
    }
    {
      const db = openPlaintext(DB_PATH);
      const count = db.prepare("SELECT count(*) AS n FROM chunks").get() as { n: bigint };
      assert.equal(count.n, 5n);
      db.close();
    }
  });

  test("plaintext DB REJECTS spurious PRAGMA key (sqlite3mc behavior)", () => {
    // OPERATIONAL CRITICAL: sqlite3mc does NOT silently no-op PRAGMA key on a
    // plaintext DB. It throws SQLITE_NOTADB on first query. This means rollout
    // CANNOT be "set NOX_DB_KEY pointing at unmigrated plaintext DB" — the API
    // would fail immediately on first request. Migration to encrypted form
    // MUST be a separate atomic step (P2: VACUUM INTO new encrypted file +
    // swap). This test pins the expected error so any sqlite3mc behavior drift
    // is caught at build time.
    const db = openEncrypted(DB_PATH, "wouldve-been-key");
    assert.throws(
      () => db.prepare("SELECT count(*) AS n FROM chunks").get(),
      (err: Error & { code?: string }) => {
        return err.code === "SQLITE_NOTADB" && /file is not a database/i.test(err.message);
      },
      "spurious key on plaintext DB must throw SQLITE_NOTADB — informs P2 migration design",
    );
    db.close();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 5. defaultSafeIntegers(true) — vec0 contract (BigInt rowid).
// ────────────────────────────────────────────────────────────────────────────
describe("defaultSafeIntegers(true) — vec0 BigInt contract", () => {
  const DB_PATH = join(TMP_ROOT, "bigint.db");
  const KEY = "bigint-key";

  test("INTEGER column returns BigInt under safe-integers mode", () => {
    const db = openEncrypted(DB_PATH, KEY);
    db.exec("CREATE TABLE t (id INTEGER PRIMARY KEY, n INTEGER)");
    db.prepare("INSERT INTO t (n) VALUES (?)").run(42);
    const row = db.prepare("SELECT id, n FROM t").get() as { id: bigint; n: bigint };
    assert.equal(typeof row.id, "bigint", "id should be BigInt");
    assert.equal(typeof row.n, "bigint", "n should be BigInt");
    assert.equal(row.n, 42n);
    db.close();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 6. VACUUM INTO encrypted snapshot — preserves data when reopened with key.
//    (Mirrors RESULTS.md Phase 2 + 5.e — op-audit snapshot compatibility.)
// ────────────────────────────────────────────────────────────────────────────
describe("VACUUM INTO encrypted snapshot", () => {
  const SRC_PATH = join(TMP_ROOT, "vacuum-src.db");
  const SNAP_PATH = join(TMP_ROOT, "vacuum-snap.db");
  const KEY = "snap-key";

  test("VACUUM INTO produces encrypted snapshot that reopens with same key", () => {
    // Phase A — fill source, take snapshot
    {
      const src = openEncrypted(SRC_PATH, KEY);
      src.exec("CREATE TABLE chunks (id INTEGER PRIMARY KEY AUTOINCREMENT, body TEXT)");
      const ins = src.prepare("INSERT INTO chunks (body) VALUES (?)");
      for (let i = 0; i < 10; i++) ins.run(`snap-body-${i}`);
      src.exec(`VACUUM INTO '${SNAP_PATH.replace(/'/g, "''")}'`);
      src.close();
    }
    assert.equal(existsSync(SNAP_PATH), true);
    assert.ok(statSync(SNAP_PATH).size > 0, "snapshot must be non-empty");

    // Phase B — reopen snap with same key, count rows
    {
      const snap = openEncrypted(SNAP_PATH, KEY);
      const count = snap.prepare("SELECT count(*) AS n FROM chunks").get() as { n: bigint };
      assert.equal(count.n, 10n, "snapshot should preserve all 10 rows");
      snap.close();
    }

    // Phase C — reopen snap with WRONG key must fail
    {
      const snap = openEncrypted(SNAP_PATH, "wrong-snap-key");
      assert.throws(
        () => snap.prepare("SELECT count(*) AS n FROM chunks").get(),
        (err: Error) => /file is not a database|not a database|HMAC|file is encrypted/i.test(err.message),
      );
      snap.close();
    }
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 7. Integration — actual db.ts module under various env configurations.
//
// We use dynamic import + process.env mutation + NOX_DB_PATH override per the
// op-audit-e2e.test.ts pattern in staged-1.7a. Each test gets its own subprocess
// boundary via fresh import; the singleton inside db.ts is reset by deleting
// the cached module via the Node ESM import-cache evict trick (re-import with
// query suffix to force a fresh module instance).
// ────────────────────────────────────────────────────────────────────────────
describe("db.ts integration — env-driven open paths", () => {
  test("NOX_DB_REQUIRE_KEY=1 + NOX_DB_KEY unset throws at getDb()", async () => {
    const DB_PATH = join(TMP_ROOT, "require-key.db");
    // Reset env, set require-key without providing key
    process.env.NOX_DB_PATH = DB_PATH;
    process.env.NOX_DB_REQUIRE_KEY = "1";
    delete process.env.NOX_DB_KEY;

    // Force fresh module instance via query-string ESM trick (otherwise the
    // singleton from a prior import would short-circuit).
    const mod = await import(`../db.js?seed=${Date.now()}`);

    assert.throws(
      () => mod.getDb(),
      /NOX_DB_REQUIRE_KEY=1 but NOX_DB_KEY is unset/,
    );

    // Cleanup env
    delete process.env.NOX_DB_REQUIRE_KEY;
    delete process.env.NOX_DB_PATH;
    if (mod.closeDb) mod.closeDb();
  });

  test("NOX_DB_KEY set + plaintext-mode default → encrypted open + isDbEncrypted()=true", async () => {
    const DB_PATH = join(TMP_ROOT, "encrypted-via-env.db");
    process.env.NOX_DB_PATH = DB_PATH;
    process.env.NOX_DB_KEY = "env-driven-key";
    delete process.env.NOX_DB_REQUIRE_KEY;

    const mod = await import(`../db.js?seed=${Date.now()}`);
    const db = mod.getDb();

    assert.equal(mod.isDbEncrypted(), true, "isDbEncrypted() must report true after encrypted open");

    // Write+read smoke (schema migrations should have populated chunks table)
    const ins = db.prepare("INSERT INTO chunks (source_file, chunk_text, chunk_type) VALUES (?, ?, ?)");
    ins.run("test.md", "encrypted via env", "daily");
    const row = db.prepare("SELECT chunk_text FROM chunks WHERE source_file = ?").get("test.md") as { chunk_text: string } | undefined;
    assert.equal(row?.chunk_text, "encrypted via env");

    mod.closeDb();
    delete process.env.NOX_DB_KEY;
    delete process.env.NOX_DB_PATH;
  });

  test("no NOX_DB_KEY → plaintext open + isDbEncrypted()=false", async () => {
    const DB_PATH = join(TMP_ROOT, "plaintext-via-env.db");
    process.env.NOX_DB_PATH = DB_PATH;
    delete process.env.NOX_DB_KEY;
    delete process.env.NOX_DB_REQUIRE_KEY;

    const mod = await import(`../db.js?seed=${Date.now()}`);
    const db = mod.getDb();

    assert.equal(mod.isDbEncrypted(), false, "isDbEncrypted() must report false when no NOX_DB_KEY");

    const row = db.prepare("SELECT count(*) AS n FROM chunks").get() as { n: bigint };
    assert.equal(typeof row.n, "bigint", "safe-integers should still be active on plaintext open");

    mod.closeDb();
    delete process.env.NOX_DB_PATH;
  });
});
