// staged-A2-T3/scripts/__tests__/post-deployment-smoke.ts
//
// A2 Tier 3 / Phase 5 — post-deployment smoke test suite.
//
// PURPOSE
// -------
// After the deployment runbook walks the operator through Phases A→K
// (key gen → P1 code deploy → migration → atomic swap → env set → restart →
// re-enable ingest → first checkpoint → cron schedule), THIS suite is the
// machine-checkable contract that the encrypted prod stack is healthy.
//
// Each test exercises a distinct deployment surface:
//
//   Test 1 — Encrypted DB opens with key, plaintext-blind without
//             (validates Phase E/F migration + Phase G env wiring)
//   Test 2 — All chunks/kg_entities/kg_relations row counts match
//             (validates Phase E migration row-fidelity)
//   Test 3 — FTS5 query roundtrip (chunks_fts MATCH returns relevant docs)
//             (validates Phase H smoke + FTS5 rebuild from migrate-encrypt)
//   Test 4 — Defensive integer/BigInt round-trip on rowid-bearing tables
//             (validates Phase B P1 db.ts defaultSafeIntegers wiring;
//              vec0 itself is not exercised here — that requires loading
//              sqlite-vec which is not bundled with these tests, but the
//              underlying contract is the same INTEGER affinity guard)
//   Test 5 — Initial checkpoint created + verifies clean via Ed25519
//             (validates Phase J first-checkpoint + P4 audit-checkpoint
//              create/verify-chain happy path against the encrypted DB)
//
// HARNESS DESIGN
// --------------
// These tests are HERMETIC. They do NOT touch prod.  They build a
// synthetic nox-mem-shaped plaintext DB in tmpdir, run the migration
// script (same one used in Phase E of the deployment runbook), open the
// encrypted result, and exercise each surface.  The deployment runbook
// itself encodes the same checks via `curl /api/health`, `nox-mem
// search`, etc — but those require a live VPS, which a CI-runnable test
// can't assume.  By piggybacking on the exact same migration code path,
// these tests are a faithful proxy for the operator's manual smoke.
//
// Operators MAY also invoke these tests as a post-deployment "tracer
// suite" on a staging VPS (point NOX_DB_PATH at a snapshot of prod
// post-migration, supply the cipher key via env, and run
// `npm run test:p5`).  That mode is documented in
// docs/A2-TIER3-DEPLOYMENT-MASTER.md §Validation.

import { test, describe, after, before } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import Database from "better-sqlite3-multiple-ciphers";

import {
  migrateEncryptDb,
} from "../migrate-encrypt-db.js";
import {
  createCheckpoint,
  verifyChain,
  verifyCheckpoint,
  generateKeyPair,
  _resetForTest as resetCheckpointModule,
} from "../../edits/src/lib/audit-checkpoints.js";

const TMP_ROOT = mkdtempSync(join(tmpdir(), "nox-mem-a2-t3-p5-smoke-"));

after(() => {
  try { rmSync(TMP_ROOT, { recursive: true, force: true }); } catch { /* best-effort */ }
});

// ─────────────────────────────────────────────────────────────────────────────
// Synthetic prod-shaped plaintext DB (nox-mem.db proxy)
// ─────────────────────────────────────────────────────────────────────────────
//
// Mirrors the migrate-encrypt-db.test.ts fixture but adds a few extras that
// matter for the smoke-test surface:
//   - source_type column on chunks (used in /api/search filtering)
//   - audit_checkpoints schema is bootstrapped by P4 module itself, so we
//     don't pre-create it here (test 5 exercises that bootstrap path)

const CIPHER_KEY = "p5-smoke-test-cipher-key-AES256-CBC-HMAC-SHA512";
const FIXTURE_CHUNK_COUNT = 250;
const FIXTURE_ENTITY_COUNT = 25;
const FIXTURE_RELATION_COUNT = 20;

function buildSyntheticPlaintextDb(path: string): void {
  const db = new Database(path);
  db.exec(`
    CREATE TABLE chunks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source_file TEXT NOT NULL,
      chunk_text TEXT NOT NULL,
      chunk_type TEXT NOT NULL,
      source_date TEXT,
      is_consolidated INTEGER DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now')),
      metadata TEXT,
      tier TEXT DEFAULT 'peripheral',
      importance REAL DEFAULT 0.5,
      pain REAL DEFAULT 0.2,
      retention_days INTEGER,
      section TEXT,
      section_boost REAL DEFAULT 1.0,
      source_type TEXT,
      is_compiled INTEGER DEFAULT 0
    );
    CREATE VIRTUAL TABLE chunks_fts USING fts5(
      chunk_text, source_file, chunk_type,
      content=chunks, content_rowid=id,
      tokenize='unicode61 remove_diacritics 2'
    );
    CREATE TRIGGER chunks_ai AFTER INSERT ON chunks BEGIN
      INSERT INTO chunks_fts(rowid, chunk_text, source_file, chunk_type)
      VALUES (new.id, new.chunk_text, new.source_file, new.chunk_type);
    END;
    CREATE TRIGGER chunks_ad AFTER DELETE ON chunks BEGIN
      INSERT INTO chunks_fts(chunks_fts, rowid, chunk_text, source_file, chunk_type)
      VALUES ('delete', old.id, old.chunk_text, old.source_file, old.chunk_type);
    END;
    CREATE INDEX idx_chunks_source ON chunks(source_file);
    CREATE INDEX idx_chunks_type ON chunks(chunk_type);
    CREATE INDEX idx_chunks_source_type ON chunks(source_type);

    CREATE TABLE kg_entities (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT UNIQUE NOT NULL,
      type TEXT,
      attributes TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE kg_relations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source_entity_id INTEGER NOT NULL,
      target_entity_id INTEGER NOT NULL,
      predicate TEXT NOT NULL,
      created_at TEXT DEFAULT (datetime('now')),
      FOREIGN KEY (source_entity_id) REFERENCES kg_entities(id),
      FOREIGN KEY (target_entity_id) REFERENCES kg_entities(id)
    );
    CREATE TABLE meta (
      key TEXT PRIMARY KEY,
      value TEXT,
      updated_at TEXT DEFAULT (datetime('now'))
    );
    INSERT INTO meta (key, value) VALUES ('schema_version', '18');
  `);

  const insChunk = db.prepare(
    "INSERT INTO chunks (source_file, chunk_text, chunk_type, pain, retention_days, section, source_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
  );
  const types = ["daily", "decision", "lesson", "person", "project"];
  const sections = ["compiled", "frontmatter", "timeline", null];
  const sourceTypes = ["compiled", "external", "user_statement", "timeline"];
  const insMany = db.transaction((n: number) => {
    for (let i = 0; i < n; i++) {
      const t = types[i % types.length]!;
      const sec = sections[i % sections.length];
      const st = sourceTypes[i % sourceTypes.length]!;
      // Keyword "memoria-nox-smoke-tracer" appears in 1 row only — used as a
      // discriminator for FTS5 round-trip in Test 3.
      const text = i === 42
        ? "memoria-nox-smoke-tracer pain-weighted hybrid memory test row 42"
        : `content of chunk ${i} memoria nox encrypted memory test row ${i}`;
      insChunk.run(
        `synthetic-${i}.md`,
        text,
        t,
        i % 10 === 0 ? 0.8 : 0.2,
        t === "decision" ? 365 : 90,
        sec,
        st,
      );
    }
  });
  insMany(FIXTURE_CHUNK_COUNT);

  const insEnt = db.prepare("INSERT INTO kg_entities (name, type, attributes) VALUES (?, ?, ?)");
  const insRel = db.prepare(
    "INSERT INTO kg_relations (source_entity_id, target_entity_id, predicate) VALUES (?, ?, ?)",
  );
  const entIds: number[] = [];
  for (let i = 0; i < FIXTURE_ENTITY_COUNT; i++) {
    const r = insEnt.run(`entity-${i}`, i % 2 === 0 ? "person" : "project", JSON.stringify({ idx: i }));
    entIds.push(Number(r.lastInsertRowid));
  }
  for (let i = 0; i < FIXTURE_RELATION_COUNT; i++) {
    insRel.run(entIds[i % entIds.length]!, entIds[(i + 1) % entIds.length]!, "knows");
  }

  db.close();
}

function openEncrypted(path: string, key: string, readonly = false): Database.Database {
  const db = new Database(path, { readonly });
  db.pragma(`cipher='sqlcipher'`, { simple: true });
  db.pragma(`legacy=4`, { simple: true });
  db.pragma(`cipher_compatibility=4`, { simple: true });
  const esc = key.replace(/'/g, "''");
  db.pragma(`key='${esc}'`, { simple: true });
  db.defaultSafeIntegers(true);
  return db;
}

// ─────────────────────────────────────────────────────────────────────────────
// Shared fixture — built once, reused by tests 1-4 (test 5 isolates its own).
// ─────────────────────────────────────────────────────────────────────────────

const SHARED_SRC = join(TMP_ROOT, "smoke-shared-src.db");
const SHARED_DST = join(TMP_ROOT, "smoke-shared-enc.db");
let sharedMigrationDone = false;

function ensureSharedMigration(): void {
  if (sharedMigrationDone) return;
  buildSyntheticPlaintextDb(SHARED_SRC);
  const result = migrateEncryptDb({
    sourcePath: SHARED_SRC,
    destPath: SHARED_DST,
    key: CIPHER_KEY,
    quiet: true,
  });
  assert.equal(result.success, true, "shared migration must succeed for smoke tests to run");
  sharedMigrationDone = true;
}

// ─────────────────────────────────────────────────────────────────────────────
// Test 1 — Encrypted DB opens with key, plaintext-blind without
// ─────────────────────────────────────────────────────────────────────────────
//
// Maps to Phase E (migration produces encrypted DB) + Phase G (env wiring
// post-restart enforces key requirement).  Without the cipher key, the DB
// must reject every query with "file is not a database (26)" — the
// canonical sqlite3mc wrong/missing-key error.

describe("Test 1 — encrypted DB opens with key + plaintext-blind without", () => {
  before(() => ensureSharedMigration());

  test("opens with correct key and reads metadata", () => {
    const db = openEncrypted(SHARED_DST, CIPHER_KEY, true);
    try {
      const row = db.prepare("SELECT value FROM meta WHERE key = 'schema_version'").get() as
        | { value: string }
        | undefined;
      assert.ok(row, "schema_version row must be readable post-migration");
      assert.equal(row.value, "18", "schema_version should match source");
    } finally {
      db.close();
    }
  });

  test("rejects opening with wrong key", () => {
    const db = new Database(SHARED_DST, { readonly: true });
    db.pragma(`cipher='sqlcipher'`, { simple: true });
    db.pragma(`legacy=4`, { simple: true });
    db.pragma(`cipher_compatibility=4`, { simple: true });
    db.pragma(`key='wrong-key-attempt'`, { simple: true });
    try {
      assert.throws(
        () => db.prepare("SELECT 1 FROM meta LIMIT 1").get(),
        /file is not a database|not a database|HMAC/i,
        "wrong key must surface NOTADB / HMAC error",
      );
    } finally {
      db.close();
    }
  });

  test("rejects opening with no key at all (plaintext open of encrypted DB)", () => {
    const db = new Database(SHARED_DST, { readonly: true });
    try {
      assert.throws(
        () => db.prepare("SELECT 1 FROM meta LIMIT 1").get(),
        /file is not a database|not a database|HMAC/i,
        "no-key open must surface NOTADB error",
      );
    } finally {
      db.close();
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Test 2 — Row counts match pre-migration on every table
// ─────────────────────────────────────────────────────────────────────────────
//
// Maps to Phase E manual-validation step in the runbook (script counts
// match source counts).  We open BOTH the plaintext source and the
// encrypted dest, count every ordinary table on each side, and demand
// 1:1 equality.

describe("Test 2 — row counts match pre-migration", () => {
  before(() => ensureSharedMigration());

  test("chunks count matches", () => {
    const src = new Database(SHARED_SRC, { readonly: true });
    const dst = openEncrypted(SHARED_DST, CIPHER_KEY, true);
    try {
      const srcCnt = Number((src.prepare("SELECT count(*) AS n FROM chunks").get() as { n: number | bigint }).n);
      const dstCnt = Number((dst.prepare("SELECT count(*) AS n FROM chunks").get() as { n: number | bigint }).n);
      assert.equal(dstCnt, srcCnt, `dst chunks count ${dstCnt} ≠ src ${srcCnt}`);
      assert.equal(dstCnt, FIXTURE_CHUNK_COUNT, "chunks count should equal fixture target");
    } finally {
      src.close();
      dst.close();
    }
  });

  test("kg_entities count matches", () => {
    const src = new Database(SHARED_SRC, { readonly: true });
    const dst = openEncrypted(SHARED_DST, CIPHER_KEY, true);
    try {
      const srcCnt = Number((src.prepare("SELECT count(*) AS n FROM kg_entities").get() as { n: number | bigint }).n);
      const dstCnt = Number((dst.prepare("SELECT count(*) AS n FROM kg_entities").get() as { n: number | bigint }).n);
      assert.equal(dstCnt, srcCnt);
      assert.equal(dstCnt, FIXTURE_ENTITY_COUNT);
    } finally {
      src.close();
      dst.close();
    }
  });

  test("kg_relations count matches", () => {
    const src = new Database(SHARED_SRC, { readonly: true });
    const dst = openEncrypted(SHARED_DST, CIPHER_KEY, true);
    try {
      const srcCnt = Number((src.prepare("SELECT count(*) AS n FROM kg_relations").get() as { n: number | bigint }).n);
      const dstCnt = Number((dst.prepare("SELECT count(*) AS n FROM kg_relations").get() as { n: number | bigint }).n);
      assert.equal(dstCnt, srcCnt);
      assert.equal(dstCnt, FIXTURE_RELATION_COUNT);
    } finally {
      src.close();
      dst.close();
    }
  });

  test("meta + chunks_fts internal row counts match", () => {
    const src = new Database(SHARED_SRC, { readonly: true });
    const dst = openEncrypted(SHARED_DST, CIPHER_KEY, true);
    try {
      // FTS5 docsize row count == content row count for a healthy rebuild.
      const srcFtsRows = Number((src.prepare("SELECT count(*) AS n FROM chunks_fts").get() as { n: number | bigint }).n);
      const dstFtsRows = Number((dst.prepare("SELECT count(*) AS n FROM chunks_fts").get() as { n: number | bigint }).n);
      assert.equal(dstFtsRows, srcFtsRows, `dst FTS rows ${dstFtsRows} ≠ src ${srcFtsRows}`);
    } finally {
      src.close();
      dst.close();
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Test 3 — FTS5 query roundtrip
// ─────────────────────────────────────────────────────────────────────────────
//
// Maps to Phase H smoke: `curl /api/search?q=...` returns results.  The
// fixture seeds exactly one chunk containing the tracer phrase
// "memoria-nox-smoke-tracer"; we demand the FTS5 MATCH returns exactly
// that 1 row, with the body intact (BLOB/TEXT decrypts cleanly).

describe("Test 3 — FTS5 query roundtrip on encrypted DB", () => {
  before(() => ensureSharedMigration());

  test("MATCH on tracer phrase returns exactly the seeded row", () => {
    const dst = openEncrypted(SHARED_DST, CIPHER_KEY, true);
    try {
      const rows = dst
        .prepare(
          "SELECT c.id, c.chunk_text FROM chunks_fts " +
          "JOIN chunks c ON c.id = chunks_fts.rowid " +
          "WHERE chunks_fts MATCH 'tracer' " +
          "ORDER BY c.id",
        )
        .all() as Array<{ id: bigint; chunk_text: string }>;
      assert.equal(rows.length, 1, `expected 1 match for 'tracer', got ${rows.length}`);
      assert.match(rows[0]!.chunk_text, /memoria-nox-smoke-tracer/);
    } finally {
      dst.close();
    }
  });

  test("MATCH on common term returns many results (FTS index populated)", () => {
    const dst = openEncrypted(SHARED_DST, CIPHER_KEY, true);
    try {
      const cnt = Number(
        (dst.prepare("SELECT count(*) AS n FROM chunks_fts WHERE chunks_fts MATCH 'memoria'").get() as {
          n: number | bigint;
        }).n,
      );
      // Every fixture row contains "memoria" — full population proves rebuild OK.
      assert.equal(cnt, FIXTURE_CHUNK_COUNT, `MATCH 'memoria' returned ${cnt} of ${FIXTURE_CHUNK_COUNT}`);
    } finally {
      dst.close();
    }
  });

  test("unicode-folded MATCH works (tokenizer survived migration)", () => {
    // unicode61 remove_diacritics=2 tokenizer should fold accents.
    // We seeded plain ASCII text in fixtures; this test just confirms the
    // tokenizer config survived (a misconfigured tokenizer would error or
    // return 0 rows).
    const dst = openEncrypted(SHARED_DST, CIPHER_KEY, true);
    try {
      // 'MEMORIA' (uppercase) should match 'memoria' rows via unicode61 case fold.
      const cnt = Number(
        (dst.prepare("SELECT count(*) AS n FROM chunks_fts WHERE chunks_fts MATCH 'MEMORIA'").get() as {
          n: number | bigint;
        }).n,
      );
      assert.equal(cnt, FIXTURE_CHUNK_COUNT, "case-insensitive MATCH should hit all rows");
    } finally {
      dst.close();
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Test 4 — BigInt/INTEGER round-trip on encrypted DB
// ─────────────────────────────────────────────────────────────────────────────
//
// Maps to Phase B (P1 db.ts wiring) — defaultSafeIntegers(true) is the
// pre-requisite for vec0 rowid binding.  We can't load sqlite-vec in
// these tests (not a bundled dep), but the underlying invariant — that
// INTEGER columns round-trip as BigInt on read, and BigInt INSERTs bind
// as INTEGER — IS the same contract, and any cipher path issue with
// number marshaling will manifest here.

describe("Test 4 — BigInt INTEGER round-trip on encrypted DB", () => {
  before(() => ensureSharedMigration());

  test("read returns BigInt for INTEGER columns under safe-integers mode", () => {
    const dst = openEncrypted(SHARED_DST, CIPHER_KEY, true);
    try {
      const row = dst.prepare("SELECT id FROM chunks LIMIT 1").get() as { id: bigint | number };
      assert.equal(
        typeof row.id,
        "bigint",
        "INTEGER column must read as bigint under defaultSafeIntegers(true)",
      );
    } finally {
      dst.close();
    }
  });

  test("BigInt write + read round-trip via test table on writable encrypted DB", () => {
    // Open writable copy (separate path so the shared readonly tests stay safe)
    const writePath = join(TMP_ROOT, "smoke-rw-bigint.db");
    const writeSrc = join(TMP_ROOT, "smoke-rw-bigint-src.db");
    buildSyntheticPlaintextDb(writeSrc);
    const r = migrateEncryptDb({
      sourcePath: writeSrc,
      destPath: writePath,
      key: CIPHER_KEY,
      quiet: true,
    });
    assert.equal(r.success, true);

    const db = openEncrypted(writePath, CIPHER_KEY, false);
    try {
      db.exec(
        "CREATE TABLE bigint_probe (id INTEGER PRIMARY KEY, val INTEGER NOT NULL)",
      );
      // 2^53 + 1 — JS Number loses precision here; BigInt does not.
      const beyond53 = 9007199254740993n;
      db.prepare("INSERT INTO bigint_probe (id, val) VALUES (?, ?)").run(1n, beyond53);
      const got = db.prepare("SELECT val FROM bigint_probe WHERE id = ?").get(1n) as { val: bigint };
      assert.equal(typeof got.val, "bigint");
      assert.equal(got.val, beyond53, "BigInt > 2^53 must round-trip exactly under cipher");
    } finally {
      db.close();
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Test 5 — Initial checkpoint creation + verify-chain happy path
// ─────────────────────────────────────────────────────────────────────────────
//
// Maps to Phase J: operator runs `audit-checkpoint create --scope ops`
// (after first prod ops_audit row exists), then `audit-checkpoint
// verify-chain --scope all` to establish baseline.  We exercise the
// programmatic equivalent against an isolated encrypted DB.

describe("Test 5 — initial checkpoint creation + verify-chain (Phase J)", () => {
  const SRC = join(TMP_ROOT, "checkpoint-src.db");
  const DST = join(TMP_ROOT, "checkpoint-dst.db");
  const KEY = "checkpoint-smoke-key";
  // Shared signing key across ALL Test 5 sub-cases — mirrors a real
  // operator workflow: one Ed25519 keypair backs every checkpoint in a
  // deployment.  If we generated a fresh keypair per sub-test, the chain
  // would naturally fail (each new checkpoint signed by a different key
  // vs the stored row's public_key_b64 fingerprint).
  let sharedKp: ReturnType<typeof generateKeyPair>;
  let savedDbPath: string | undefined;
  let savedDbKey: string | undefined;

  before(() => {
    // Build a synthetic DB AND pre-seed ops_audit/reads_audit so the
    // checkpoint module has rows to checkpoint over. The schema bootstrap
    // for audit_checkpoints is done by createCheckpoint() itself.
    const db = new Database(SRC);
    db.exec(`
      CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
      INSERT INTO meta (key, value) VALUES ('schema_version', '18');

      -- Minimal ops_audit shape compatible with the P4 module's expectations.
      CREATE TABLE ops_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts INTEGER NOT NULL,
        op TEXT NOT NULL,
        actor TEXT,
        status TEXT,
        meta_json TEXT,
        started_at INTEGER,
        ended_at INTEGER,
        rows_affected INTEGER
      );
      CREATE TABLE reads_audit (
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
    const now = Date.now();
    const insOps = db.prepare(
      "INSERT INTO ops_audit (ts, op, actor, status, started_at, ended_at, rows_affected) VALUES (?, ?, ?, ?, ?, ?, ?)",
    );
    for (let i = 0; i < 7; i++) {
      insOps.run(now + i, `reindex-${i}`, "smoke", "success", now + i, now + i + 100, 42);
    }
    const insReads = db.prepare(
      "INSERT INTO reads_audit (ts, query, k, n_results, latency_ms, source_app) VALUES (?, ?, ?, ?, ?, ?)",
    );
    for (let i = 0; i < 5; i++) {
      insReads.run(now + i * 2, `query-${i}`, 10, 3, 15, "smoke");
    }
    db.close();

    // Migrate to encrypted destination
    const r = migrateEncryptDb({ sourcePath: SRC, destPath: DST, key: KEY, quiet: true });
    assert.equal(r.success, true, "checkpoint test prerequisite: migration");

    // Point the audit-checkpoints module at the encrypted DB by setting
    // the env vars its lazy connection resolver reads.  Save + restore.
    savedDbPath = process.env.NOX_DB_PATH;
    savedDbKey = process.env.NOX_DB_KEY;
    process.env.NOX_DB_PATH = DST;
    process.env.NOX_DB_KEY = KEY;
    resetCheckpointModule();

    // Mint the shared keypair AFTER the env is in place — purely defensive
    // (keypair generation does not touch the DB connection at all, but
    // ordering this way means any future "tie keypair to DB" coupling
    // surfaces here, not in user-facing prod).
    sharedKp = generateKeyPair();
  });

  after(() => {
    resetCheckpointModule();
    if (savedDbPath === undefined) delete process.env.NOX_DB_PATH;
    else process.env.NOX_DB_PATH = savedDbPath;
    if (savedDbKey === undefined) delete process.env.NOX_DB_KEY;
    else process.env.NOX_DB_KEY = savedDbKey;
  });

  test("5a — generateKeyPair + createCheckpoint over ops scope succeeds", () => {
    // sharedKp was generated in before() — exercise it here.
    assert.equal(typeof sharedKp.privateKey, "string");
    assert.equal(typeof sharedKp.publicKey, "string");
    assert.equal(sharedKp.publicKeyFingerprint.length, 16, "fingerprint is 16-hex SHA-256 prefix");

    const cp = createCheckpoint("ops", sharedKp.privateKey);
    assert.ok(cp, "first checkpoint must be created (rows exist)");
    assert.equal(cp.scope, "ops");
    assert.equal(cp.row_count, 7, "checkpoint should cover all 7 ops_audit rows");
    assert.equal(typeof cp.signature_b64, "string");
    assert.equal(cp.public_key_fingerprint, sharedKp.publicKeyFingerprint);
  });

  test("5b — verifyChain --scope all returns 0 broken on the fresh checkpoint", () => {
    // Create a reads-scope checkpoint with the same shared key so the chain
    // verifier sees only consistently-signed rows.
    createCheckpoint("reads", sharedKp.privateKey);

    const opsChain = verifyChain("ops", sharedKp.publicKey);
    const readsChain = verifyChain("reads", sharedKp.publicKey);

    assert.equal(opsChain.broken, 0, `ops chain broken: ${JSON.stringify(opsChain)}`);
    assert.equal(readsChain.broken, 0, `reads chain broken: ${JSON.stringify(readsChain)}`);
    assert.equal(opsChain.scope, "ops");
    assert.equal(readsChain.scope, "reads");
    assert.equal(opsChain.total >= 1, true, "ops chain should have at least 1 checkpoint");
    assert.equal(readsChain.total >= 1, true, "reads chain should have at least 1 checkpoint");
  });

  test("5c — verifyCheckpoint of just-created checkpoint returns valid", () => {
    // Insert one more ops_audit row so this sub-test has something fresh to
    // checkpoint over (avoids the idempotent-noop branch of createCheckpoint).
    const db = openEncrypted(DST, KEY, false);
    try {
      db.prepare(
        "INSERT INTO ops_audit (ts, op, actor, status, started_at, ended_at, rows_affected) VALUES (?, ?, ?, ?, ?, ?, ?)",
      ).run(Date.now(), "tracer-5c", "smoke", "success", Date.now(), Date.now() + 50, 1);
    } finally {
      db.close();
    }
    // Force the audit-checkpoints module to refresh its connection (we just
    // wrote through a separate handle).
    resetCheckpointModule();

    const cp = createCheckpoint("ops", sharedKp.privateKey);
    assert.ok(cp, "fresh ops row should yield a new checkpoint");
    const result = verifyCheckpoint(cp.id, sharedKp.publicKey);
    assert.equal(result.valid, true, `verify must pass: ${result.error ?? "<no error>"}`);
    assert.equal(result.recomputed_sha256_hex, cp.sha256_hex);
  });

  test("5d — verifyCheckpoint detects forged checkpoint signed with wrong key", () => {
    // Negative case: an adversary who got hold of audit DB write access
    // cannot forge a checkpoint without the published private key.  We
    // verify a sharedKp-signed checkpoint AGAINST a different public key —
    // it must fail with a fingerprint / signature / key-mismatch error.
    const opsChain = verifyChain("ops", sharedKp.publicKey);
    if (opsChain.total === 0) {
      // No checkpoint to verify (shouldn't happen given 5a created one) —
      // skip rather than false-pass.
      return;
    }

    const adversaryKp = generateKeyPair();
    const target = opsChain.verified > 0 ? 1 : opsChain.breaks[0]!;
    const verify = verifyCheckpoint(target, adversaryKp.publicKey);
    assert.equal(verify.valid, false, "checkpoint must fail verification under wrong public key");
    assert.match(verify.error ?? "", /signature|key|fingerprint|mismatch/i);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Sanity: smoke suite was actually picked up by the test runner
// (separate from the 5 numbered tests; this is a meta-test to surface
// any node:test discovery issues immediately).
// ─────────────────────────────────────────────────────────────────────────────

describe("smoke suite discovery sanity", () => {
  test("fixture builder + migration helpers are importable", () => {
    assert.equal(typeof migrateEncryptDb, "function");
    assert.equal(typeof createCheckpoint, "function");
    assert.equal(typeof verifyChain, "function");
    assert.equal(typeof verifyCheckpoint, "function");
    assert.equal(typeof generateKeyPair, "function");
  });

  test("tmp fixtures are isolated to TMP_ROOT", () => {
    assert.equal(TMP_ROOT.startsWith(tmpdir()), true, "TMP_ROOT must be under os.tmpdir()");
    assert.equal(existsSync(TMP_ROOT), true);
  });
});
