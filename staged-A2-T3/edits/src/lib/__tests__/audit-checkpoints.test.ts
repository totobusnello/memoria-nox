// staged-A2-T3/edits/src/lib/__tests__/audit-checkpoints.test.ts
//
// A2 Tier 3 / Phase 4 — tests for audit_checkpoints + Ed25519 signing.
//
// Test plan (per task brief §4):
//   1. Create checkpoint on ops_audit + verify signature ✅
//   2. Verify fails after row insertion (chain broken) ✅
//   3. Append-only: DELETE blocked
//   4. verifyChain detects break in specific position
//   5. Key gen + sign + verify round-trip
//   6. Hash determinism across runs
//
// Plus additional coverage:
//   7. Sub-second idempotent re-checkpoint (no new rows → undefined)
//   8. Wrong-key signature rejection
//   9. Reads scope checkpoint (parallel path)
//  10. Encrypted DB checkpoint round-trip
//  11. Tampered audit_checkpoints row → trigger fires
//
// Harness pattern: mirrors reads-audit.test.ts (P3). Each test mutates
// process.env + NOX_DB_PATH per-test tmp file. Audit-checkpoints module is
// dynamic-imported with `?seed=` ESM-cache-busting suffix.

import { test, describe, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import DatabaseConstructor from 'better-sqlite3-multiple-ciphers';
import type Database from 'better-sqlite3-multiple-ciphers';

const TMP_ROOT = mkdtempSync(join(tmpdir(), 'nox-mem-a2-t3-checkpoints-'));

after(() => {
  try { rmSync(TMP_ROOT, { recursive: true, force: true }); } catch { /* best-effort */ }
});

type AuditCheckpointsModule = typeof import('../audit-checkpoints.js');

async function freshImport(): Promise<AuditCheckpointsModule> {
  const seed = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const mod = (await import(`../audit-checkpoints.js?seed=${seed}`)) as AuditCheckpointsModule;
  mod._resetForTest();
  return mod;
}

function setupEnv(dbPath: string): void {
  process.env.NOX_DB_PATH = dbPath;
  delete process.env.NOX_DB_KEY;
}

/** Open a raw DB connection to set up audit tables. Mirrors prod schema. */
function openRawDb(path: string, key?: string): Database.Database {
  const db = new DatabaseConstructor(path);
  if (key) {
    db.pragma(`cipher='sqlcipher'`, { simple: true });
    db.pragma(`legacy=4`, { simple: true });
    db.pragma(`cipher_compatibility=4`, { simple: true });
    db.pragma(`key='${key.replace(/'/g, "''")}'`, { simple: true });
  }
  db.defaultSafeIntegers(true);
  return db;
}

/**
 * Bootstrap a minimal ops_audit schema with the same shape the production
 * src/lib/op-audit.ts uses. We don't need EVERY column — only enough to
 * exercise the checkpoint canonical-JSON pipeline.
 */
function bootstrapOpsAudit(db: Database.Database): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS ops_audit (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      op_name TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'success',
      started_at INTEGER NOT NULL,
      completed_at INTEGER,
      affected_rows INTEGER,
      notes TEXT
    );
  `);
}

/**
 * Bootstrap a minimal reads_audit schema (parallel to staged P3). We re-create
 * it inline rather than calling the P3 module to keep this test fully self-
 * contained — the canonical-JSON test only cares that the column shapes are
 * stable across producer and verifier.
 */
function bootstrapReadsAudit(db: Database.Database): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS reads_audit (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts INTEGER NOT NULL,
      query TEXT,
      k INTEGER,
      n_results INTEGER,
      latency_ms INTEGER,
      user_id TEXT,
      source_app TEXT
    );
  `);
}

/** Insert N synthetic ops_audit rows. Returns the inserted ids in order. */
function seedOpsAudit(db: Database.Database, n: number, opNamePrefix = 'op'): number[] {
  const stmt = db.prepare(
    'INSERT INTO ops_audit (op_name, status, started_at, completed_at, affected_rows, notes) ' +
    'VALUES (?, ?, CAST(? AS INTEGER), CAST(? AS INTEGER), CAST(? AS INTEGER), ?)',
  );
  const ids: number[] = [];
  for (let i = 1; i <= n; i++) {
    const r = stmt.run(`${opNamePrefix}-${i}`, 'success', Date.now() - 1000 + i, Date.now() + i, i, `note-${i}`);
    ids.push(Number(r.lastInsertRowid));
  }
  return ids;
}

function seedReadsAudit(db: Database.Database, n: number, qPrefix = 'q'): number[] {
  const stmt = db.prepare(
    'INSERT INTO reads_audit (ts, query, k, n_results, latency_ms, user_id, source_app) ' +
    'VALUES (CAST(? AS INTEGER), ?, CAST(? AS INTEGER), CAST(? AS INTEGER), CAST(? AS INTEGER), ?, ?)',
  );
  const ids: number[] = [];
  for (let i = 1; i <= n; i++) {
    const r = stmt.run(Date.now() + i, `${qPrefix}-${i}`, 5, i, 50, null, 'test');
    ids.push(Number(r.lastInsertRowid));
  }
  return ids;
}

// ────────────────────────────────────────────────────────────────────────────
// 1. Key generation — round-trip integrity.
// ────────────────────────────────────────────────────────────────────────────
describe('generateKeyPair', () => {
  test('returns 32-byte raw Ed25519 keys (base64-encoded)', async () => {
    const mod = await freshImport();
    const kp = mod.generateKeyPair();
    const priv = Buffer.from(kp.privateKey, 'base64');
    const pub = Buffer.from(kp.publicKey, 'base64');
    assert.equal(priv.length, 32, 'private key must be 32 raw bytes');
    assert.equal(pub.length, 32, 'public key must be 32 raw bytes');
    assert.match(kp.publicKeyFingerprint, /^[0-9a-f]{16}$/, 'fingerprint = 16 hex chars');
  });

  test('two keypairs are different (entropy sanity)', async () => {
    const mod = await freshImport();
    const a = mod.generateKeyPair();
    const b = mod.generateKeyPair();
    assert.notEqual(a.privateKey, b.privateKey);
    assert.notEqual(a.publicKey, b.publicKey);
    assert.notEqual(a.publicKeyFingerprint, b.publicKeyFingerprint);
  });

  test('private key can be parsed back + derives matching public key', async () => {
    const mod = await freshImport();
    const kp = mod.generateKeyPair();
    // Use the internal helper exported for tests
    const privObj = mod._internals.rawPrivateKeyToKeyObject(kp.privateKey);
    const pubObj = mod._internals.rawPublicKeyToKeyObject(kp.publicKey);
    assert.equal(privObj.asymmetricKeyType, 'ed25519');
    assert.equal(pubObj.asymmetricKeyType, 'ed25519');
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 2. Canonical row JSON — deterministic across runs.
// ────────────────────────────────────────────────────────────────────────────
describe('canonical row JSON (hash determinism)', () => {
  test('same input → same JSON regardless of key insertion order', async () => {
    const mod = await freshImport();
    const a = mod._internals.canonicalRowJson({ b: 1, a: 'x', c: null });
    const b = mod._internals.canonicalRowJson({ c: null, a: 'x', b: 1 });
    assert.equal(a, b);
    // Keys must be sorted alphabetically:
    assert.equal(a, '"a":"x","b":1,"c":null'.replace(/^/, '{').concat('}'));
  });

  test('BigInt serialized as decimal-string (not number, not throw)', async () => {
    const mod = await freshImport();
    const j = mod._internals.canonicalRowJson({ id: 99999999999999n, name: 'big' });
    assert.equal(j, '{"id":"99999999999999","name":"big"}');
  });

  test('empty rows array → "<empty>\\n" marker', async () => {
    const mod = await freshImport();
    const bytes = mod._internals.rowsToCanonicalBytes([]);
    assert.equal(bytes.toString('utf8'), '<empty>\n');
  });

  test('non-empty rows → newline-joined + trailing newline', async () => {
    const mod = await freshImport();
    const bytes = mod._internals.rowsToCanonicalBytes([
      { id: 1n, op: 'a' },
      { id: 2n, op: 'b' },
    ]);
    assert.equal(
      bytes.toString('utf8'),
      '{"id":"1","op":"a"}\n{"id":"2","op":"b"}\n',
    );
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 3. createCheckpoint — basic round-trip.
// ────────────────────────────────────────────────────────────────────────────
describe('createCheckpoint', () => {
  test('ops scope — first checkpoint covers all rows + signature verifies', async () => {
    const DB_PATH = join(TMP_ROOT, 'create-ops-1.db');
    setupEnv(DB_PATH);

    // Seed audit table via raw connection BEFORE module open
    {
      const raw = openRawDb(DB_PATH);
      bootstrapOpsAudit(raw);
      seedOpsAudit(raw, 5);
      raw.close();
    }

    const mod = await freshImport();
    const kp = mod.generateKeyPair();
    const result = mod.createCheckpoint('ops', kp.privateKey);
    assert.ok(result, 'expected a CheckpointResult');
    assert.equal(result!.scope, 'ops');
    assert.equal(result!.last_id, 5);
    assert.equal(result!.prev_last_id, null, 'first checkpoint = genesis');
    assert.equal(result!.row_count, 5);
    assert.match(result!.sha256_hex, /^[0-9a-f]{64}$/);
    assert.equal(result!.public_key_b64, kp.publicKey);
    assert.equal(result!.public_key_fingerprint, kp.publicKeyFingerprint);

    // Verify signature
    const verifyResult = mod.verifyCheckpoint(result!.id, kp.publicKey);
    assert.equal(verifyResult.valid, true, `signature must verify: ${verifyResult.error}`);
    assert.equal(verifyResult.recomputed_sha256_hex, result!.sha256_hex);
  });

  test('reads scope — works in parallel', async () => {
    const DB_PATH = join(TMP_ROOT, 'create-reads-1.db');
    setupEnv(DB_PATH);

    {
      const raw = openRawDb(DB_PATH);
      bootstrapReadsAudit(raw);
      seedReadsAudit(raw, 3);
      raw.close();
    }

    const mod = await freshImport();
    const kp = mod.generateKeyPair();
    const result = mod.createCheckpoint('reads', kp.privateKey);
    assert.ok(result);
    assert.equal(result!.scope, 'reads');
    assert.equal(result!.row_count, 3);

    const v = mod.verifyCheckpoint(result!.id, kp.publicKey);
    assert.equal(v.valid, true, `reads checkpoint sig must verify: ${v.error}`);
  });

  test('idempotent: re-checkpoint with no new rows returns undefined', async () => {
    const DB_PATH = join(TMP_ROOT, 'create-idempotent.db');
    setupEnv(DB_PATH);

    {
      const raw = openRawDb(DB_PATH);
      bootstrapOpsAudit(raw);
      seedOpsAudit(raw, 4);
      raw.close();
    }

    const mod = await freshImport();
    const kp = mod.generateKeyPair();
    const r1 = mod.createCheckpoint('ops', kp.privateKey);
    assert.ok(r1);
    const r2 = mod.createCheckpoint('ops', kp.privateKey);
    assert.equal(r2, undefined, 'no new rows → undefined');
  });

  test('incremental checkpoint after new rows covers only the delta', async () => {
    const DB_PATH = join(TMP_ROOT, 'create-incremental.db');
    setupEnv(DB_PATH);

    {
      const raw = openRawDb(DB_PATH);
      bootstrapOpsAudit(raw);
      seedOpsAudit(raw, 3);
      raw.close();
    }

    const mod = await freshImport();
    const kp = mod.generateKeyPair();
    const c1 = mod.createCheckpoint('ops', kp.privateKey);
    assert.ok(c1);
    assert.equal(c1!.row_count, 3);
    assert.equal(c1!.last_id, 3);

    // Add 4 more rows
    {
      const raw = openRawDb(DB_PATH);
      seedOpsAudit(raw, 4, 'op2');
      raw.close();
      mod._resetForTest(); // force reconnect
    }

    const c2 = mod.createCheckpoint('ops', kp.privateKey);
    assert.ok(c2);
    assert.equal(c2!.prev_last_id, 3);
    assert.equal(c2!.last_id, 7);
    assert.equal(c2!.row_count, 4);
    assert.notEqual(c2!.sha256_hex, c1!.sha256_hex, 'hashes differ for different ranges');

    // Both checkpoints verify
    assert.equal(mod.verifyCheckpoint(c1!.id, kp.publicKey).valid, true);
    assert.equal(mod.verifyCheckpoint(c2!.id, kp.publicKey).valid, true);
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 4. Tamper detection — chain breaks on audit-row mutation.
// ────────────────────────────────────────────────────────────────────────────
describe('tamper detection', () => {
  test('inserting a retroactive row → verify fails for the covering checkpoint', async () => {
    const DB_PATH = join(TMP_ROOT, 'tamper-insert.db');
    setupEnv(DB_PATH);

    {
      const raw = openRawDb(DB_PATH);
      bootstrapOpsAudit(raw);
      seedOpsAudit(raw, 5);
      raw.close();
    }

    const mod = await freshImport();
    const kp = mod.generateKeyPair();
    const cp = mod.createCheckpoint('ops', kp.privateKey);
    assert.ok(cp);

    // Verify it's currently valid
    assert.equal(mod.verifyCheckpoint(cp!.id, kp.publicKey).valid, true);

    // Tamper: ops_audit append-only triggers may be missing in this test
    // schema (we bootstrap a minimal one). Use raw INSERT to add a row in
    // the range. Even an APPEND (not just modify) breaks the hash because
    // the row at id=N might land in the (prev, last_id] range or move the
    // boundary.
    //
    // Note: we use UPDATE here on an EXISTING row id≤last_id to simulate
    // tampering of past audit data. Even though prod ops_audit blocks UPDATE,
    // our test table doesn't have those triggers — purpose is to assert that
    // the checkpoint catches such corruption.
    mod._resetForTest();
    {
      const raw = openRawDb(DB_PATH);
      raw.prepare('UPDATE ops_audit SET notes = ? WHERE id = 3').run('TAMPERED');
      raw.close();
    }

    const v = mod.verifyCheckpoint(cp!.id, kp.publicKey);
    assert.equal(v.valid, false, 'tampered row must break verification');
    assert.match(v.error ?? '', /hash mismatch/);
  });

  test('audit_checkpoints DELETE blocked by trigger', async () => {
    const DB_PATH = join(TMP_ROOT, 'tamper-delete.db');
    setupEnv(DB_PATH);

    {
      const raw = openRawDb(DB_PATH);
      bootstrapOpsAudit(raw);
      seedOpsAudit(raw, 3);
      raw.close();
    }

    const mod = await freshImport();
    const kp = mod.generateKeyPair();
    const cp = mod.createCheckpoint('ops', kp.privateKey);
    assert.ok(cp);

    // Now try DELETE — must throw
    mod._resetForTest();
    const raw = openRawDb(DB_PATH);
    assert.throws(
      () => raw.prepare('DELETE FROM audit_checkpoints WHERE id = ?').run(cp!.id),
      /append-only/,
    );
    raw.close();
  });

  test('audit_checkpoints UPDATE of signed row blocked by trigger', async () => {
    const DB_PATH = join(TMP_ROOT, 'tamper-update.db');
    setupEnv(DB_PATH);

    {
      const raw = openRawDb(DB_PATH);
      bootstrapOpsAudit(raw);
      seedOpsAudit(raw, 2);
      raw.close();
    }

    const mod = await freshImport();
    const kp = mod.generateKeyPair();
    const cp = mod.createCheckpoint('ops', kp.privateKey);
    assert.ok(cp);

    mod._resetForTest();
    const raw = openRawDb(DB_PATH);
    const fakeHash = 'a'.repeat(64);
    assert.throws(
      () => raw.prepare('UPDATE audit_checkpoints SET sha256_hex = ? WHERE id = ?').run(fakeHash, cp!.id),
      /immutable/i,
    );
    raw.close();
  });

  test('wrong public key rejected (signature does not verify)', async () => {
    const DB_PATH = join(TMP_ROOT, 'wrong-key.db');
    setupEnv(DB_PATH);

    {
      const raw = openRawDb(DB_PATH);
      bootstrapOpsAudit(raw);
      seedOpsAudit(raw, 2);
      raw.close();
    }

    const mod = await freshImport();
    const kpA = mod.generateKeyPair();
    const kpB = mod.generateKeyPair();
    const cp = mod.createCheckpoint('ops', kpA.privateKey);
    assert.ok(cp);

    // Verify with kpA → OK
    assert.equal(mod.verifyCheckpoint(cp!.id, kpA.publicKey).valid, true);
    // Verify with kpB → FAIL (mismatch on stored vs supplied)
    const v = mod.verifyCheckpoint(cp!.id, kpB.publicKey);
    assert.equal(v.valid, false);
    assert.match(v.error ?? '', /public key mismatch/);
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 5. verifyChain — aggregate verification.
// ────────────────────────────────────────────────────────────────────────────
describe('verifyChain', () => {
  test('all valid chain returns verified=N, broken=0', async () => {
    const DB_PATH = join(TMP_ROOT, 'chain-clean.db');
    setupEnv(DB_PATH);

    {
      const raw = openRawDb(DB_PATH);
      bootstrapOpsAudit(raw);
      raw.close();
    }

    const mod = await freshImport();
    const kp = mod.generateKeyPair();

    // Three checkpoints, each after 2 more rows
    {
      const raw = openRawDb(DB_PATH);
      seedOpsAudit(raw, 2);
      raw.close();
    }
    mod._resetForTest();
    const c1 = mod.createCheckpoint('ops', kp.privateKey);
    assert.ok(c1);

    {
      const raw = openRawDb(DB_PATH);
      seedOpsAudit(raw, 2, 'b');
      raw.close();
    }
    mod._resetForTest();
    const c2 = mod.createCheckpoint('ops', kp.privateKey);
    assert.ok(c2);

    {
      const raw = openRawDb(DB_PATH);
      seedOpsAudit(raw, 2, 'c');
      raw.close();
    }
    mod._resetForTest();
    const c3 = mod.createCheckpoint('ops', kp.privateKey);
    assert.ok(c3);

    const result = mod.verifyChain('ops', kp.publicKey);
    assert.equal(result.verified, 3);
    assert.equal(result.broken, 0);
    assert.deepEqual(result.breaks, []);
    assert.equal(result.total, 3);
  });

  test('break in middle: chain reports only the affected checkpoint', async () => {
    const DB_PATH = join(TMP_ROOT, 'chain-broken-middle.db');
    setupEnv(DB_PATH);

    {
      const raw = openRawDb(DB_PATH);
      bootstrapOpsAudit(raw);
      raw.close();
    }

    const mod = await freshImport();
    const kp = mod.generateKeyPair();

    // Build a 3-checkpoint chain
    {
      const raw = openRawDb(DB_PATH);
      seedOpsAudit(raw, 2);
      raw.close();
    }
    mod._resetForTest();
    const c1 = mod.createCheckpoint('ops', kp.privateKey)!;
    {
      const raw = openRawDb(DB_PATH);
      seedOpsAudit(raw, 2, 'b');
      raw.close();
    }
    mod._resetForTest();
    const c2 = mod.createCheckpoint('ops', kp.privateKey)!;
    {
      const raw = openRawDb(DB_PATH);
      seedOpsAudit(raw, 2, 'c');
      raw.close();
    }
    mod._resetForTest();
    const c3 = mod.createCheckpoint('ops', kp.privateKey)!;

    // Tamper a row inside c2's range (id 3 or 4 — c2 covers ids 3..4)
    mod._resetForTest();
    {
      const raw = openRawDb(DB_PATH);
      raw.prepare("UPDATE ops_audit SET notes = 'TAMPER' WHERE id = 4").run();
      raw.close();
    }

    const result = mod.verifyChain('ops', kp.publicKey);
    assert.equal(result.total, 3);
    assert.equal(result.broken, 1);
    assert.equal(result.verified, 2);
    assert.deepEqual(result.breaks, [c2.id]);
    assert.ok(result.errors[c2.id]);
    assert.match(result.errors[c2.id]!, /hash mismatch/);

    // c1 + c3 still valid (different ranges)
    void c1; void c3;
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 6. Schema-trigger invariants.
// ────────────────────────────────────────────────────────────────────────────
describe('schema triggers', () => {
  test('ts non-INTEGER bind → trigger rejects', async () => {
    const DB_PATH = join(TMP_ROOT, 'trg-ts-text.db');
    setupEnv(DB_PATH);

    {
      const raw = openRawDb(DB_PATH);
      bootstrapOpsAudit(raw);
      seedOpsAudit(raw, 1);
      raw.close();
    }

    const mod = await freshImport();
    const kp = mod.generateKeyPair();
    mod.createCheckpoint('ops', kp.privateKey); // bootstrap schema

    mod._resetForTest();
    const raw = openRawDb(DB_PATH);
    assert.throws(
      () => raw.prepare(
        "INSERT INTO audit_checkpoints (ts, scope, last_id, sha256_hex) " +
        "VALUES ('not-an-int', 'ops', 1, '" + 'a'.repeat(64) + "')",
      ).run(),
      /must be INTEGER/,
    );
    raw.close();
  });

  test('invalid scope rejected by trigger', async () => {
    const DB_PATH = join(TMP_ROOT, 'trg-scope.db');
    setupEnv(DB_PATH);

    {
      const raw = openRawDb(DB_PATH);
      bootstrapOpsAudit(raw);
      seedOpsAudit(raw, 1);
      raw.close();
    }

    const mod = await freshImport();
    const kp = mod.generateKeyPair();
    mod.createCheckpoint('ops', kp.privateKey); // bootstrap

    mod._resetForTest();
    const raw = openRawDb(DB_PATH);
    assert.throws(
      () => raw.prepare(
        "INSERT INTO audit_checkpoints (ts, scope, last_id, sha256_hex) " +
        "VALUES (CAST(? AS INTEGER), 'bogus-scope', CAST(? AS INTEGER), ?)",
      ).run(Date.now(), 1, 'a'.repeat(64)),
      /must be one of/,
    );
    raw.close();
  });

  test('malformed sha256_hex rejected (wrong length)', async () => {
    const DB_PATH = join(TMP_ROOT, 'trg-sha256-len.db');
    setupEnv(DB_PATH);

    {
      const raw = openRawDb(DB_PATH);
      bootstrapOpsAudit(raw);
      seedOpsAudit(raw, 1);
      raw.close();
    }

    const mod = await freshImport();
    const kp = mod.generateKeyPair();
    mod.createCheckpoint('ops', kp.privateKey); // bootstrap

    mod._resetForTest();
    const raw = openRawDb(DB_PATH);
    assert.throws(
      () => raw.prepare(
        "INSERT INTO audit_checkpoints (ts, scope, last_id, sha256_hex) " +
        "VALUES (CAST(? AS INTEGER), 'ops', CAST(? AS INTEGER), ?)",
      ).run(Date.now(), 1, 'short'),
      /64-char lowercase hex/,
    );
    raw.close();
  });

  test('uppercase sha256_hex rejected (non-hex chars)', async () => {
    const DB_PATH = join(TMP_ROOT, 'trg-sha256-case.db');
    setupEnv(DB_PATH);

    {
      const raw = openRawDb(DB_PATH);
      bootstrapOpsAudit(raw);
      seedOpsAudit(raw, 1);
      raw.close();
    }

    const mod = await freshImport();
    const kp = mod.generateKeyPair();
    mod.createCheckpoint('ops', kp.privateKey); // bootstrap

    mod._resetForTest();
    const raw = openRawDb(DB_PATH);
    assert.throws(
      () => raw.prepare(
        "INSERT INTO audit_checkpoints (ts, scope, last_id, sha256_hex) " +
        "VALUES (CAST(? AS INTEGER), 'ops', CAST(? AS INTEGER), ?)",
      ).run(Date.now(), 1, 'A'.repeat(64)),
      /64-char lowercase hex/,
    );
    raw.close();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 7. Encrypted DB — checkpoint round-trip with SQLCipher key.
// ────────────────────────────────────────────────────────────────────────────
describe('encrypted DB checkpoint', () => {
  test('NOX_DB_KEY set → checkpoint created + verified under same key', async () => {
    const DB_PATH = join(TMP_ROOT, 'encrypted-cp.db');
    const DB_KEY = 'audit-checkpoint-test-key';
    setupEnv(DB_PATH);
    process.env.NOX_DB_KEY = DB_KEY;

    // Bootstrap audit table inside encrypted DB
    {
      const raw = openRawDb(DB_PATH, DB_KEY);
      bootstrapOpsAudit(raw);
      seedOpsAudit(raw, 3);
      raw.close();
    }

    const mod = await freshImport();
    const kp = mod.generateKeyPair();
    const cp = mod.createCheckpoint('ops', kp.privateKey);
    assert.ok(cp);
    assert.equal(cp!.row_count, 3);

    // Verify under same DB key
    const v = mod.verifyCheckpoint(cp!.id, kp.publicKey);
    assert.equal(v.valid, true, `encrypted checkpoint must verify: ${v.error}`);

    // Cleanup
    delete process.env.NOX_DB_KEY;
  });
});

// ────────────────────────────────────────────────────────────────────────────
// 8. Sign/verify round-trip with same key (multi-message)
// ────────────────────────────────────────────────────────────────────────────
describe('Ed25519 sign/verify primitive', () => {
  test('multiple messages signed with same key all verify independently', async () => {
    const DB_PATH = join(TMP_ROOT, 'multi-sign.db');
    setupEnv(DB_PATH);

    {
      const raw = openRawDb(DB_PATH);
      bootstrapOpsAudit(raw);
      raw.close();
    }

    const mod = await freshImport();
    const kp = mod.generateKeyPair();

    // Create 3 checkpoints back-to-back (each adds rows + checkpoints)
    const checkpoints: number[] = [];
    for (let batch = 0; batch < 3; batch++) {
      {
        const raw = openRawDb(DB_PATH);
        seedOpsAudit(raw, 2, `batch-${batch}`);
        raw.close();
      }
      mod._resetForTest();
      const cp = mod.createCheckpoint('ops', kp.privateKey);
      assert.ok(cp);
      checkpoints.push(cp!.id);
    }

    // All independently verify
    for (const id of checkpoints) {
      const v = mod.verifyCheckpoint(id, kp.publicKey);
      assert.equal(v.valid, true, `cp ${id} must verify`);
    }
  });
});
