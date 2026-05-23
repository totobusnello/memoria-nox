// staged-A2-T3/edits/src/lib/__tests__/reads-audit.test.ts
//
// A2 Tier 3 / Phase 3 — tests for reads_audit opt-in wrapper + retention sweep.
//
// Test plan (per task brief §4):
//   1. Disabled (default): zero rows written
//   2. Enabled via env: rows appended correctly
//   3. PII sanitization: long query truncated to 200 chars + control chars stripped
//   4. Hash mode: raw user_id NEVER stored; query stored as sha256-hex
//   5. Retention sweep: ts < cutoff archived, ts >= cutoff retained
//   6. Append-only: DELETE/UPDATE blocked by trigger
//   7. Encrypted DB: works with NOX_DB_KEY set
//
// Harness pattern: same as db.crypto.test.ts (P1 PR #280). Each test mutates
// process.env + sets NOX_DB_PATH to a per-test tmp file, then dynamic-imports
// the module with a unique ?seed= suffix to evict the ESM cache + reset the
// db.ts singleton.

import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { createHash } from 'node:crypto';

const TMP_ROOT = mkdtempSync(join(tmpdir(), 'nox-mem-a2-t3-reads-audit-'));

after(() => {
  try { rmSync(TMP_ROOT, { recursive: true, force: true }); } catch { /* best-effort */ }
});

/**
 * Force a fresh module instance of reads-audit.ts and db.ts. Uses query-string
 * ESM trick — appends a unique seed so the Node module cache treats it as a
 * new specifier and re-evaluates module top-level code. This resets the
 * _db singleton in db.ts and the _schemaApplied/_insertStmt cache in
 * reads-audit.ts simultaneously.
 *
 * Critical: must reset env BEFORE the import, because module-level constants
 * (like SCHEMA_PATH) and process.env access in early code happen at import
 * time.
 */
type FreshModules = {
  ra: typeof import('../reads-audit.js');
  db: typeof import('../db.js');
};
async function freshImport(): Promise<FreshModules> {
  const seed = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const ra = (await import(`../reads-audit.js?seed=${seed}`)) as typeof import('../reads-audit.js');
  const db = (await import(`../db.js?seed=${seed}`)) as typeof import('../db.js');
  // Critical: reset the inner (un-seeded) db.ts singleton that reads-audit.ts
  // imported statically. Without this, the previous test's _db handle from
  // reads-audit's perspective stays open against the OLD NOX_DB_PATH file,
  // and audit INSERTs land in the wrong place. See _resetForTest() in
  // reads-audit.ts for the full explanation.
  ra._resetForTest();
  return { ra, db };
}

/** Helper: clear env + set fresh per-test NOX_DB_PATH. Tests should call
 *  this BEFORE freshImport(). */
function setupEnv(dbPath: string): void {
  process.env.NOX_DB_PATH = dbPath;
  delete process.env.NOX_DB_KEY;
  delete process.env.NOX_DB_REQUIRE_KEY;
  delete process.env.NOX_READS_AUDIT;
  delete process.env.NOX_READS_AUDIT_HASH_QUERIES;
  delete process.env.NOX_READS_AUDIT_USER_HASH;
  delete process.env.NOX_READS_AUDIT_RETENTION_DAYS;
  delete process.env.NOX_READS_AUDIT_ARCHIVE_PATH;
}

// ────────────────────────────────────────────────────────────────────────────
// 1. Disabled (default) — zero rows written, zero overhead path.
// ────────────────────────────────────────────────────────────────────────────
describe('reads_audit DISABLED (default)', () => {
  test('NOX_READS_AUDIT unset → withReadAudit passes through, zero rows written, schema not bootstrapped', async () => {
    const DB_PATH = join(TMP_ROOT, 'disabled.db');
    setupEnv(DB_PATH);

    const { ra, db } = await freshImport();
    assert.equal(ra.isReadsAuditEnabled(), false);

    const fn = async () => ['r1', 'r2', 'r3'];
    const result = await ra.withReadAudit(
      { op_name: 'search', query: 'hello', k: 5, source_app: 'cli' },
      fn,
    );
    assert.deepEqual(result, ['r1', 'r2', 'r3']);

    // The reads_audit table must NOT have been created — disabled path never
    // touches the DB. Verify by querying sqlite_master directly via the db
    // module (which DOES touch the DB but only for its own schema setup).
    const dbh = db.getDb();
    const tbl = dbh
      .prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='reads_audit'")
      .get() as { name: string } | undefined;
    assert.equal(tbl, undefined, 'reads_audit table must NOT exist when audit is disabled');

    db.closeDb();
  });

  test('NOX_READS_AUDIT="0" (explicit false) → also disabled', async () => {
    const DB_PATH = join(TMP_ROOT, 'disabled-explicit.db');
    setupEnv(DB_PATH);
    process.env.NOX_READS_AUDIT = '0';

    const { ra, db } = await freshImport();
    assert.equal(ra.isReadsAuditEnabled(), false);

    await ra.withReadAudit({ op_name: 'search', query: 'x' }, async () => [1]);

    const dbh = db.getDb();
    const tbl = dbh
      .prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='reads_audit'")
      .get() as { name: string } | undefined;
    assert.equal(tbl, undefined);

    db.closeDb();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 2. Enabled — rows appended correctly with all fields.
// ────────────────────────────────────────────────────────────────────────────
describe('reads_audit ENABLED — basic round-trip', () => {
  test('NOX_READS_AUDIT=1 → row inserted with correct ts/query/k/n_results/latency/source_app', async () => {
    const DB_PATH = join(TMP_ROOT, 'enabled-basic.db');
    setupEnv(DB_PATH);
    process.env.NOX_READS_AUDIT = '1';

    const { ra, db } = await freshImport();
    assert.equal(ra.isReadsAuditEnabled(), true);

    const t0 = Date.now();
    const result = await ra.withReadAudit(
      { op_name: 'search', query: 'red apple', k: 10, source_app: 'http' },
      async () => {
        // Simulate small latency so latency_ms > 0
        await new Promise((r) => setTimeout(r, 20));
        return ['a', 'b', 'c'];
      },
    );
    const t1 = Date.now();
    assert.deepEqual(result, ['a', 'b', 'c']);

    const dbh = db.getDb();
    const rows = dbh
      .prepare('SELECT id, ts, query, k, n_results, latency_ms, user_id, source_app FROM reads_audit ORDER BY id')
      .all() as Array<{
        id: bigint;
        ts: bigint;
        query: string;
        k: bigint;
        n_results: bigint;
        latency_ms: bigint;
        user_id: string | null;
        source_app: string;
      }>;
    assert.equal(rows.length, 1, 'exactly one row expected');
    const row = rows[0]!;
    assert.equal(row.query, 'red apple', 'query stored sanitized + untruncated');
    assert.equal(row.k, 10n);
    assert.equal(row.n_results, 3n, 'n_results derived from array length');
    assert.equal(row.source_app, 'http');
    assert.equal(row.user_id, null);
    // ts within window of t0..t1
    assert.ok(row.ts >= BigInt(t0) && row.ts <= BigInt(t1), `ts (${row.ts}) outside expected window [${t0}, ${t1}]`);
    // latency >= 20ms (matches sleep above)
    assert.ok(row.latency_ms >= 20n, `latency_ms (${row.latency_ms}) should be ≥ 20`);

    // Stats helper sanity
    const stats = ra.getReadsAuditStats();
    assert.equal(stats.total_rows, 1n);
    assert.equal(stats.rows_24h, 1n);

    db.closeDb();
  });

  test('n_results derived from {results: [...]} object response', async () => {
    const DB_PATH = join(TMP_ROOT, 'enabled-results-obj.db');
    setupEnv(DB_PATH);
    process.env.NOX_READS_AUDIT = '1';

    const { ra, db } = await freshImport();
    await ra.withReadAudit(
      { op_name: 'answer', query: 'q', k: 5, source_app: 'mcp' },
      async () => ({ results: [{ id: 1 }, { id: 2 }, { id: 3 }, { id: 4 }] }),
    );

    const dbh = db.getDb();
    const row = dbh.prepare('SELECT n_results FROM reads_audit').get() as { n_results: bigint };
    assert.equal(row.n_results, 4n);

    db.closeDb();
  });

  test('n_results explicit via {n_results: N} wins over .results.length', async () => {
    const DB_PATH = join(TMP_ROOT, 'enabled-explicit-n.db');
    setupEnv(DB_PATH);
    process.env.NOX_READS_AUDIT = '1';

    const { ra, db } = await freshImport();
    await ra.withReadAudit(
      { op_name: 'search', query: 'q', k: 5 },
      async () => ({ n_results: 99, results: [{ id: 1 }] }),
    );

    const dbh = db.getDb();
    const row = dbh.prepare('SELECT n_results FROM reads_audit').get() as { n_results: bigint };
    assert.equal(row.n_results, 99n);

    db.closeDb();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 3. PII sanitization — long query truncated to ≤200 chars, control chars stripped.
// ────────────────────────────────────────────────────────────────────────────
describe('reads_audit PII sanitization', () => {
  test('query >200 chars truncated to exactly 200', async () => {
    const DB_PATH = join(TMP_ROOT, 'sanitize-truncate.db');
    setupEnv(DB_PATH);
    process.env.NOX_READS_AUDIT = '1';

    const { ra, db } = await freshImport();
    const longQuery = 'x'.repeat(500);
    await ra.withReadAudit(
      { op_name: 'search', query: longQuery, k: 5, source_app: 'cli' },
      async () => [],
    );

    const dbh = db.getDb();
    const row = dbh.prepare('SELECT query FROM reads_audit').get() as { query: string };
    assert.equal(row.query.length, 200, 'query must be truncated to exactly 200 chars');
    assert.equal(row.query, 'x'.repeat(200));

    db.closeDb();
  });

  test('NUL bytes + control chars stripped before bind', async () => {
    const DB_PATH = join(TMP_ROOT, 'sanitize-control.db');
    setupEnv(DB_PATH);
    process.env.NOX_READS_AUDIT = '1';

    const { ra, db } = await freshImport();
    const dirty = 'hello\x00world\x01\x02test\x7Fdone\nNewlineOK\tTabOK';
    await ra.withReadAudit(
      { op_name: 'search', query: dirty, k: 5, source_app: 'cli' },
      async () => [],
    );

    const dbh = db.getDb();
    const row = dbh.prepare('SELECT query FROM reads_audit').get() as { query: string };
    // NUL + ETX + STX + DEL stripped; newline + tab preserved.
    assert.equal(row.query, 'helloworldtestdone\nNewlineOK\tTabOK');

    db.closeDb();
  });

  test('empty/whitespace-only query → stored as NULL or whitespace (no error)', async () => {
    const DB_PATH = join(TMP_ROOT, 'sanitize-empty.db');
    setupEnv(DB_PATH);
    process.env.NOX_READS_AUDIT = '1';

    const { ra, db } = await freshImport();
    await ra.withReadAudit(
      { op_name: 'search', query: '', k: 0, source_app: 'cli' },
      async () => [],
    );
    await ra.withReadAudit(
      { op_name: 'search', source_app: 'cli' },
      async () => [],
    );

    const dbh = db.getDb();
    const rows = dbh.prepare('SELECT query FROM reads_audit ORDER BY id').all() as Array<{ query: string | null }>;
    assert.equal(rows.length, 2);
    // Both should be NULL since transformQuery returns null for empty/missing.
    assert.equal(rows[0]!.query, null);
    assert.equal(rows[1]!.query, null);

    db.closeDb();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 4. Hash mode — query as sha256-hex; user_id NEVER raw.
// ────────────────────────────────────────────────────────────────────────────
describe('reads_audit hash mode', () => {
  test('NOX_READS_AUDIT_HASH_QUERIES=1 → query stored as 64-char sha256-hex', async () => {
    const DB_PATH = join(TMP_ROOT, 'hash-queries.db');
    setupEnv(DB_PATH);
    process.env.NOX_READS_AUDIT = '1';
    process.env.NOX_READS_AUDIT_HASH_QUERIES = '1';

    const { ra, db } = await freshImport();
    assert.equal(ra.isQueryHashingEnabled(), true);

    const plaintext = 'secret query about prod incident';
    await ra.withReadAudit(
      { op_name: 'search', query: plaintext, k: 5, source_app: 'cli' },
      async () => [],
    );

    const dbh = db.getDb();
    const row = dbh.prepare('SELECT query FROM reads_audit').get() as { query: string };
    assert.equal(row.query.length, 64, 'sha256-hex is 64 chars');
    assert.match(row.query, /^[0-9a-f]{64}$/, 'must be lowercase hex');
    // Spot-check: query must NOT be the plaintext
    assert.notEqual(row.query, plaintext);
    // And must match the expected hash
    const expected = createHash('sha256').update(plaintext, 'utf8').digest('hex');
    assert.equal(row.query, expected);

    db.closeDb();
  });

  test('user_id passed without NOX_READS_AUDIT_USER_HASH → throws (fail-closed)', async () => {
    const DB_PATH = join(TMP_ROOT, 'user-id-no-salt.db');
    setupEnv(DB_PATH);
    process.env.NOX_READS_AUDIT = '1';

    const { ra, db } = await freshImport();
    await assert.rejects(
      () => ra.withReadAudit(
        { op_name: 'search', query: 'q', user_id: 'toto@example.com', source_app: 'http' },
        async () => [],
      ),
      /NOX_READS_AUDIT_USER_HASH env is unset/,
    );

    // No row should have been inserted (the wrapper throws BEFORE fn runs).
    const dbh = db.getDb();
    // The schema may have been bootstrapped (ensureReadsAuditSchema is called on
    // the success path of safeRecord, but the throw happens BEFORE any record
    // attempt). Confirm zero rows regardless.
    const tbl = dbh
      .prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='reads_audit'")
      .get() as { name: string } | undefined;
    if (tbl) {
      const cnt = dbh.prepare('SELECT COUNT(*) AS c FROM reads_audit').get() as { c: bigint };
      assert.equal(cnt.c, 0n, 'no row should be inserted when user_id rejected');
    }

    db.closeDb();
  });

  test('user_id with NOX_READS_AUDIT_USER_HASH → stored as sha256(salt + user_id), NEVER raw', async () => {
    const DB_PATH = join(TMP_ROOT, 'user-id-hashed.db');
    setupEnv(DB_PATH);
    process.env.NOX_READS_AUDIT = '1';
    process.env.NOX_READS_AUDIT_USER_HASH = 'pepper-2026-05-24';

    const { ra, db } = await freshImport();
    const rawUser = 'toto@nuvini.com.br';
    await ra.withReadAudit(
      { op_name: 'search', query: 'q', user_id: rawUser, source_app: 'http' },
      async () => [],
    );

    const dbh = db.getDb();
    const row = dbh.prepare('SELECT user_id FROM reads_audit').get() as { user_id: string };
    // Must NOT be the raw email
    assert.notEqual(row.user_id, rawUser, 'raw user_id MUST NEVER be stored');
    assert.doesNotMatch(row.user_id, /@/, 'stored value must not look like an email');
    // Must be lowercase 64-char hex
    assert.match(row.user_id, /^[0-9a-f]{64}$/);
    // Verify it matches sha256(salt + ':' + user_id) — the wrapper's exact format
    const expected = createHash('sha256').update('pepper-2026-05-24:' + rawUser, 'utf8').digest('hex');
    assert.equal(row.user_id, expected);

    db.closeDb();
  });

  test('user_id null/undefined → stored as NULL even with salt set', async () => {
    const DB_PATH = join(TMP_ROOT, 'user-id-null.db');
    setupEnv(DB_PATH);
    process.env.NOX_READS_AUDIT = '1';
    process.env.NOX_READS_AUDIT_USER_HASH = 'some-salt';

    const { ra, db } = await freshImport();
    await ra.withReadAudit(
      { op_name: 'search', query: 'q', source_app: 'cli' },
      async () => [],
    );

    const dbh = db.getDb();
    const row = dbh.prepare('SELECT user_id FROM reads_audit').get() as { user_id: string | null };
    assert.equal(row.user_id, null);

    db.closeDb();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 5. Append-only — DELETE / UPDATE blocked by triggers.
// ────────────────────────────────────────────────────────────────────────────
describe('reads_audit append-only triggers', () => {
  test('DELETE FROM reads_audit → throws RAISE(ABORT)', async () => {
    const DB_PATH = join(TMP_ROOT, 'append-only-delete.db');
    setupEnv(DB_PATH);
    process.env.NOX_READS_AUDIT = '1';

    const { ra, db } = await freshImport();
    // Seed one row
    await ra.withReadAudit({ op_name: 'search', query: 'q', source_app: 'cli' }, async () => []);

    const dbh = db.getDb();
    assert.throws(
      () => dbh.prepare('DELETE FROM reads_audit').run(),
      /append-only/,
    );

    db.closeDb();
  });

  test('UPDATE reads_audit → throws RAISE(ABORT)', async () => {
    const DB_PATH = join(TMP_ROOT, 'append-only-update.db');
    setupEnv(DB_PATH);
    process.env.NOX_READS_AUDIT = '1';

    const { ra, db } = await freshImport();
    await ra.withReadAudit({ op_name: 'search', query: 'orig', source_app: 'cli' }, async () => []);

    const dbh = db.getDb();
    assert.throws(
      () => dbh.prepare("UPDATE reads_audit SET query='tampered'").run(),
      /immutable|append-only/i,
    );

    db.closeDb();
  });

  test('ts non-INTEGER bind → trigger fires (defense-in-depth past CAST)', async () => {
    const DB_PATH = join(TMP_ROOT, 'ts-non-int.db');
    setupEnv(DB_PATH);
    process.env.NOX_READS_AUDIT = '1';

    const { ra, db } = await freshImport();
    // Bootstrap schema via a normal audited call.
    await ra.withReadAudit({ op_name: 'search', query: 'q', source_app: 'cli' }, async () => []);

    const dbh = db.getDb();
    // Now try to bypass CAST by binding a literal TEXT for ts — trigger must fire.
    assert.throws(
      () => dbh
        .prepare("INSERT INTO reads_audit (ts, query, source_app) VALUES ('not-an-int', 'q', 'cli')")
        .run(),
      /must be INTEGER/,
    );

    db.closeDb();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 6. Failure-path recording — fn() throws, row still inserted with n_results=0.
// ────────────────────────────────────────────────────────────────────────────
describe('reads_audit failure path', () => {
  test('fn throws → audit row recorded with n_results=0; original error re-thrown', async () => {
    const DB_PATH = join(TMP_ROOT, 'fn-throws.db');
    setupEnv(DB_PATH);
    process.env.NOX_READS_AUDIT = '1';

    const { ra, db } = await freshImport();
    await assert.rejects(
      () => ra.withReadAudit(
        { op_name: 'search', query: 'broken', source_app: 'cli' },
        async () => { throw new Error('boom'); },
      ),
      /boom/,
    );

    const dbh = db.getDb();
    const row = dbh.prepare('SELECT n_results, query FROM reads_audit').get() as { n_results: bigint; query: string };
    assert.equal(row.n_results, 0n);
    assert.equal(row.query, 'broken');

    db.closeDb();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 7. Encrypted DB — wrapper works transparently with NOX_DB_KEY.
// ────────────────────────────────────────────────────────────────────────────
describe('reads_audit on encrypted DB', () => {
  test('NOX_DB_KEY set → audit row written + reread under same key', async () => {
    const DB_PATH = join(TMP_ROOT, 'encrypted.db');
    setupEnv(DB_PATH);
    process.env.NOX_DB_KEY = 'reads-audit-test-key';
    process.env.NOX_READS_AUDIT = '1';

    const { ra, db } = await freshImport();
    // Touch getDb() once to trigger the encrypted open + set the _isEncrypted
    // flag (it starts false; only set after applyCipherPragmas runs inside
    // getDb()). Then the audit wrapper exercises its OWN connection (separate
    // from db.ts's singleton — see resolveDbPathLazy() / getAuditConn()).
    db.getDb();
    assert.equal(db.isDbEncrypted(), true);

    await ra.withReadAudit(
      { op_name: 'search', query: 'enc-test', k: 7, source_app: 'mcp' },
      async () => ['a', 'b'],
    );

    const dbh = db.getDb();
    const row = dbh
      .prepare('SELECT query, k, n_results, source_app FROM reads_audit')
      .get() as { query: string; k: bigint; n_results: bigint; source_app: string };
    assert.equal(row.query, 'enc-test');
    assert.equal(row.k, 7n);
    assert.equal(row.n_results, 2n);
    assert.equal(row.source_app, 'mcp');

    db.closeDb();

    // Reopen + re-read to confirm the encrypted round-trip works through the
    // audit table specifically (regression guard for any cipher-stream issue).
    const { ra: ra2, db: db2 } = await freshImport();
    const dbh2 = db2.getDb();
    const cnt = dbh2.prepare('SELECT COUNT(*) AS c FROM reads_audit').get() as { c: bigint };
    assert.equal(cnt.c, 1n);
    assert.equal(ra2.isReadsAuditEnabled(), true);
    db2.closeDb();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 8. Retention sweep — archive ts < cutoff; main retains; idempotent.
// ────────────────────────────────────────────────────────────────────────────
describe('reads_audit retention sweep', () => {
  // Note: the sweep CLI is intentionally a separate module that does its own
  // Database() open (not via getDb()). It needs NOX_DB_PATH + (optional)
  // NOX_DB_KEY in the env at run-time. We invoke runSweep() directly rather
  // than spawning a subprocess.

  test('sweep moves ts<cutoff rows to archive; main retains (append-only invariant)', async () => {
    const DB_PATH = join(TMP_ROOT, 'sweep.db');
    const ARCHIVE_PATH = join(TMP_ROOT, 'sweep-archive.db');
    setupEnv(DB_PATH);
    process.env.NOX_READS_AUDIT = '1';

    const { ra, db } = await freshImport();
    const dbh = db.getDb();

    // Seed: 5 rows total. 3 OLD (ts well below cutoff) + 2 RECENT.
    // We bypass the wrapper (which sets ts=Date.now()) and INSERT directly so we
    // can plant historical timestamps. The trigger only blocks DELETE/UPDATE,
    // not INSERT, so this is allowed.
    //
    // Schema is bootstrapped via one normal call first.
    await ra.withReadAudit({ op_name: 'seed', query: 'recent-1', source_app: 'test' }, async () => []);
    await ra.withReadAudit({ op_name: 'seed', query: 'recent-2', source_app: 'test' }, async () => []);

    const veryOld = Date.now() - 200 * 86_400_000; // 200 days ago
    const stmt = dbh.prepare(
      'INSERT INTO reads_audit (ts, query, k, n_results, latency_ms, user_id, source_app) ' +
      'VALUES (CAST(? AS INTEGER), ?, NULL, 0, 0, NULL, ?)',
    );
    stmt.run(veryOld + 1000, 'old-1', 'test');
    stmt.run(veryOld + 2000, 'old-2', 'test');
    stmt.run(veryOld + 3000, 'old-3', 'test');

    const beforeCount = dbh.prepare('SELECT COUNT(*) AS c FROM reads_audit').get() as { c: bigint };
    assert.equal(beforeCount.c, 5n, 'pre-sweep main count');

    // IMPORTANT: close the singleton so the sweep CLI can open the file fresh
    // without WAL/lock contention.
    db.closeDb();

    // Dynamic-import the sweep module with current env. Pass argv via mutating
    // process.argv (cli-style).
    process.argv = [
      'node',
      'reads-audit-sweep.js',
      '--retention-days',
      '90',
      '--archive-path',
      ARCHIVE_PATH,
    ];
    const sweepMod = await import(`../../../scripts/reads-audit-sweep.js?seed=${Date.now()}`);
    sweepMod.runSweep();

    // Verify archive contains 3 OLD rows
    const Database = (await import('better-sqlite3-multiple-ciphers')).default;
    assert.ok(existsSync(ARCHIVE_PATH), 'archive file must exist');
    const archive = new Database(ARCHIVE_PATH);
    archive.defaultSafeIntegers(true);
    const archCount = archive.prepare('SELECT COUNT(*) AS c FROM reads_audit').get() as { c: bigint };
    assert.equal(archCount.c, 3n, 'archive should contain the 3 OLD rows');
    const archQueries = archive
      .prepare('SELECT query FROM reads_audit ORDER BY ts')
      .all() as Array<{ query: string }>;
    assert.deepEqual(archQueries.map((r) => r.query), ['old-1', 'old-2', 'old-3']);
    archive.close();

    // Verify MAIN still has all 5 rows (D58: archive is logical, main is append-only)
    const { db: db2 } = await freshImport();
    const dbh2 = db2.getDb();
    const afterCount = dbh2.prepare('SELECT COUNT(*) AS c FROM reads_audit').get() as { c: bigint };
    assert.equal(afterCount.c, 5n, 'main reads_audit must still contain all 5 rows post-sweep (append-only)');
    db2.closeDb();
  });

  test('sweep is idempotent — running twice does not double-insert', async () => {
    const DB_PATH = join(TMP_ROOT, 'sweep-idempotent.db');
    const ARCHIVE_PATH = join(TMP_ROOT, 'sweep-idempotent-archive.db');
    setupEnv(DB_PATH);
    process.env.NOX_READS_AUDIT = '1';

    const { ra, db } = await freshImport();
    const dbh = db.getDb();

    await ra.withReadAudit({ op_name: 'bootstrap', source_app: 'test' }, async () => []);
    const veryOld = Date.now() - 200 * 86_400_000;
    dbh.prepare(
      'INSERT INTO reads_audit (ts, query, source_app) VALUES (CAST(? AS INTEGER), ?, ?)',
    ).run(veryOld, 'old', 'test');
    db.closeDb();

    process.argv = ['node', 'reads-audit-sweep.js', '--retention-days', '90', '--archive-path', ARCHIVE_PATH];

    const sweepMod = await import(`../../../scripts/reads-audit-sweep.js?seed=${Date.now()}-r1`);
    sweepMod.runSweep();
    // Second run — should be no-op (INSERT OR IGNORE)
    const sweepMod2 = await import(`../../../scripts/reads-audit-sweep.js?seed=${Date.now()}-r2`);
    sweepMod2.runSweep();

    const Database = (await import('better-sqlite3-multiple-ciphers')).default;
    const archive = new Database(ARCHIVE_PATH);
    archive.defaultSafeIntegers(true);
    const cnt = archive.prepare('SELECT COUNT(*) AS c FROM reads_audit').get() as { c: bigint };
    assert.equal(cnt.c, 1n, 'archive must still have exactly 1 row after re-running sweep');
    archive.close();
  });

  test('--dry-run reports counts without writing', async () => {
    const DB_PATH = join(TMP_ROOT, 'sweep-dry-run.db');
    const ARCHIVE_PATH = join(TMP_ROOT, 'sweep-dry-archive.db');
    setupEnv(DB_PATH);
    process.env.NOX_READS_AUDIT = '1';

    const { ra, db } = await freshImport();
    const dbh = db.getDb();
    await ra.withReadAudit({ op_name: 'bootstrap', source_app: 'test' }, async () => []);
    const veryOld = Date.now() - 200 * 86_400_000;
    dbh.prepare(
      'INSERT INTO reads_audit (ts, query, source_app) VALUES (CAST(? AS INTEGER), ?, ?)',
    ).run(veryOld, 'will-not-be-archived', 'test');
    db.closeDb();

    process.argv = [
      'node', 'reads-audit-sweep.js',
      '--retention-days', '90',
      '--archive-path', ARCHIVE_PATH,
      '--dry-run',
    ];
    const sweepMod = await import(`../../../scripts/reads-audit-sweep.js?seed=${Date.now()}-dry`);
    sweepMod.runSweep();

    // Archive file MUST NOT exist
    assert.equal(existsSync(ARCHIVE_PATH), false, 'dry-run must not create archive file');
  });

  test('encrypted main DB → encrypted archive (same key)', async () => {
    const DB_PATH = join(TMP_ROOT, 'sweep-encrypted.db');
    const ARCHIVE_PATH = join(TMP_ROOT, 'sweep-encrypted-archive.db');
    setupEnv(DB_PATH);
    process.env.NOX_DB_KEY = 'archive-cipher-key';
    process.env.NOX_READS_AUDIT = '1';

    const { ra, db } = await freshImport();
    const dbh = db.getDb();
    await ra.withReadAudit({ op_name: 'bootstrap', source_app: 'test' }, async () => []);
    const veryOld = Date.now() - 200 * 86_400_000;
    dbh.prepare(
      'INSERT INTO reads_audit (ts, query, source_app) VALUES (CAST(? AS INTEGER), ?, ?)',
    ).run(veryOld, 'enc-old', 'test');
    db.closeDb();

    process.argv = ['node', 'reads-audit-sweep.js', '--retention-days', '90', '--archive-path', ARCHIVE_PATH];
    const sweepMod = await import(`../../../scripts/reads-audit-sweep.js?seed=${Date.now()}-enc`);
    sweepMod.runSweep();

    // Open archive — WITHOUT key first → should fail
    const Database = (await import('better-sqlite3-multiple-ciphers')).default;
    {
      const plain = new Database(ARCHIVE_PATH);
      plain.defaultSafeIntegers(true);
      assert.throws(
        () => plain.prepare('SELECT COUNT(*) FROM reads_audit').get(),
        /file is not a database|not a database|file is encrypted/i,
        'plaintext open of encrypted archive must fail',
      );
      plain.close();
    }
    // Open WITH key → should read 1 row
    {
      const enc = new Database(ARCHIVE_PATH);
      enc.pragma(`cipher='sqlcipher'`, { simple: true });
      enc.pragma(`legacy=4`, { simple: true });
      enc.pragma(`cipher_compatibility=4`, { simple: true });
      enc.pragma(`key='archive-cipher-key'`, { simple: true });
      enc.defaultSafeIntegers(true);
      const cnt = enc.prepare('SELECT COUNT(*) AS c FROM reads_audit').get() as { c: bigint };
      assert.equal(cnt.c, 1n);
      enc.close();
    }
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 9. parseArgs unit tests (cheap, no DB)
// ────────────────────────────────────────────────────────────────────────────
describe('reads-audit-sweep parseArgs', () => {
  before(() => {
    process.env.NOX_DB_PATH = join(TMP_ROOT, 'fake.db');
  });

  test('defaults: retention=90, archive sibling of NOX_DB_PATH', async () => {
    const sweepMod = await import(`../../../scripts/reads-audit-sweep.js?seed=${Date.now()}-pa1`);
    const a = sweepMod.parseArgs(['node', 'sweep.js']);
    assert.equal(a.retentionDays, 90);
    assert.match(a.archivePath, /nox-mem-audit-archive\.db$/);
    assert.equal(a.dryRun, false);
  });

  test('--retention-days 30 + --archive-path /tmp/foo.db parsed correctly', async () => {
    const sweepMod = await import(`../../../scripts/reads-audit-sweep.js?seed=${Date.now()}-pa2`);
    const a = sweepMod.parseArgs([
      'node', 'sweep.js',
      '--retention-days', '30',
      '--archive-path', '/tmp/foo.db',
    ]);
    assert.equal(a.retentionDays, 30);
    assert.equal(a.archivePath, '/tmp/foo.db');
  });

  test('invalid --retention-days throws', async () => {
    const sweepMod = await import(`../../../scripts/reads-audit-sweep.js?seed=${Date.now()}-pa3`);
    assert.throws(
      () => sweepMod.parseArgs(['node', 'sweep.js', '--retention-days', 'banana']),
      /positive integer/,
    );
    assert.throws(
      () => sweepMod.parseArgs(['node', 'sweep.js', '--retention-days', '-5']),
      /positive integer/,
    );
    assert.throws(
      () => sweepMod.parseArgs(['node', 'sweep.js', '--retention-days', '0']),
      /positive integer/,
    );
  });

  test('unknown arg throws', async () => {
    const sweepMod = await import(`../../../scripts/reads-audit-sweep.js?seed=${Date.now()}-pa4`);
    assert.throws(
      () => sweepMod.parseArgs(['node', 'sweep.js', '--bogus']),
      /unknown arg/,
    );
  });
});
