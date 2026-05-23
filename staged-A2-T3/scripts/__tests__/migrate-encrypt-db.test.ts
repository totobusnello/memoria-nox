// staged-A2-T3/scripts/__tests__/migrate-encrypt-db.test.ts
//
// A2 Tier 3 / Phase 2 — tests for migrate-encrypt-db.ts
//
// Covers (per task brief §3):
//   1. Migration on fixture plaintext DB (~100 chunks + FTS5)
//   2. Dest opens with correct key + reads same data + matches all row counts
//   3. Dest does NOT open with wrong key
//   4. Already-encrypted source aborts (no overwrite)
//   5. Dest-exists aborts (no overwrite)
//   6. Same-source-and-dest path aborts
//   7. Empty key aborts
//   8. FTS5 MATCH works after migration (rebuild path)
//   9. Atomic swap helper backs up source + moves dest into place
//
// Notes on harness:
//   - Each test uses a unique tmpdir to keep DBs isolated.
//   - Tests do NOT touch process.env (CLI parsing tests use parseCliArgs
//     directly with explicit argv/env objects).
//   - sqlite-vec is NOT loaded — vec0 path is exercised by separate spike
//     integration tests; here we focus on the migration algorithm.

import { test, describe, after, before } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, existsSync, statSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import Database from "better-sqlite3-multiple-ciphers";

import {
  migrateEncryptDb,
  isSourcePlaintext,
  swapEncryptedIntoSource,
  parseCliArgs,
} from "../migrate-encrypt-db.js";

const TMP_ROOT = mkdtempSync(join(tmpdir(), "nox-mem-a2-t3-p2-migrate-"));

after(() => {
  try { rmSync(TMP_ROOT, { recursive: true, force: true }); } catch { /* best-effort */ }
});

// Helpers ----------------------------------------------------------------------

/**
 * Build a synthetic plaintext source DB modeled after nox-mem's actual schema:
 *  - chunks table (autoinc PK + FTS5 mirror via triggers)
 *  - chunks_fts (FTS5 with unicode61 remove_diacritics=2 tokenizer)
 *  - kg_entities + kg_relations
 *  - search_telemetry
 *  - meta (schema_version row)
 */
function buildSyntheticPlaintextDb(path: string, rowCount: number): void {
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
      section_boost REAL DEFAULT 1.0
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
    CREATE TABLE search_telemetry (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts TEXT NOT NULL DEFAULT (datetime('now')),
      query_hash TEXT NOT NULL,
      results_count INTEGER DEFAULT 0
    );
    CREATE TABLE meta (
      key TEXT PRIMARY KEY,
      value TEXT,
      updated_at TEXT DEFAULT (datetime('now'))
    );
    INSERT INTO meta (key, value) VALUES ('schema_version', '18');
  `);

  const insChunk = db.prepare(
    "INSERT INTO chunks (source_file, chunk_text, chunk_type, pain, retention_days, section) VALUES (?, ?, ?, ?, ?, ?)",
  );
  const types = ["daily", "decision", "lesson", "person", "project"];
  const sections = ["compiled", "frontmatter", "timeline", null];
  const insMany = db.transaction((n: number) => {
    for (let i = 0; i < n; i++) {
      const t = types[i % types.length]!;
      const sec = sections[i % sections.length];
      insChunk.run(
        `synthetic-${i}.md`,
        `content of chunk ${i} memoria nox encrypted memory test row ${i}`,
        t,
        i % 10 === 0 ? 0.8 : 0.2,
        t === "decision" ? 365 : 90,
        sec,
      );
    }
  });
  insMany(rowCount);

  const insEnt = db.prepare("INSERT INTO kg_entities (name, type, attributes) VALUES (?, ?, ?)");
  const insRel = db.prepare(
    "INSERT INTO kg_relations (source_entity_id, target_entity_id, predicate) VALUES (?, ?, ?)",
  );
  const entIds: number[] = [];
  for (let i = 0; i < 10; i++) {
    const r = insEnt.run(`entity-${i}`, "person", JSON.stringify({ idx: i }));
    entIds.push(Number(r.lastInsertRowid));
  }
  for (let i = 0; i < 5; i++) {
    insRel.run(entIds[i]!, entIds[(i + 1) % entIds.length]!, "knows");
  }

  const insTel = db.prepare("INSERT INTO search_telemetry (query_hash, results_count) VALUES (?, ?)");
  for (let i = 0; i < 20; i++) insTel.run(`hash-${i}`, i * 3);

  db.close();
}

function openEncrypted(path: string, key: string): Database.Database {
  const db = new Database(path);
  db.pragma(`cipher='sqlcipher'`, { simple: true });
  db.pragma(`legacy=4`, { simple: true });
  db.pragma(`cipher_compatibility=4`, { simple: true });
  const esc = key.replace(/'/g, "''");
  db.pragma(`key='${esc}'`, { simple: true });
  db.defaultSafeIntegers(true);
  return db;
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. End-to-end migration: 100 chunks + FTS + entities + relations + telemetry
// ─────────────────────────────────────────────────────────────────────────────

describe("end-to-end migration of synthetic nox-mem-like DB", () => {
  const SRC = join(TMP_ROOT, "e2e-src.db");
  const DST = join(TMP_ROOT, "e2e-dst.db");
  const KEY = "e2e-test-key-1";

  before(() => buildSyntheticPlaintextDb(SRC, 100));

  test("migrate succeeds and all row counts match", () => {
    const result = migrateEncryptDb({ sourcePath: SRC, destPath: DST, key: KEY, quiet: true });
    assert.equal(result.success, true, `migration must succeed; got ${JSON.stringify(result.tableCounts)}`);
    assert.equal(result.tableCounts.length >= 5, true, "expected at least 5 ordinary tables");
    for (const tc of result.tableCounts) {
      assert.equal(tc.match, true, `${tc.table}: src=${tc.sourceCount} dst=${tc.destCount}`);
    }
    // Spot-check headline counts
    const chunks = result.tableCounts.find((t) => t.table === "chunks");
    assert.equal(chunks?.destCount, 100, "chunks should have 100 rows");
    const ents = result.tableCounts.find((t) => t.table === "kg_entities");
    assert.equal(ents?.destCount, 10);
    const rels = result.tableCounts.find((t) => t.table === "kg_relations");
    assert.equal(rels?.destCount, 5);
    const tele = result.tableCounts.find((t) => t.table === "search_telemetry");
    assert.equal(tele?.destCount, 20);
  });

  test("dest opens with correct key + reads same data", () => {
    const db = openEncrypted(DST, KEY);
    try {
      const cnt = db.prepare("SELECT count(*) AS n FROM chunks").get() as { n: bigint };
      assert.equal(Number(cnt.n), 100);

      // Spot-check a row content matches source pattern
      const row = db.prepare("SELECT chunk_text, pain, section FROM chunks WHERE id = 1").get() as {
        chunk_text: string;
        pain: number;
        section: string | null;
      };
      assert.match(row.chunk_text, /content of chunk 0/);
      assert.equal(row.section, "compiled");

      // meta.schema_version preserved
      const ver = db.prepare("SELECT value FROM meta WHERE key = 'schema_version'").get() as { value: string };
      assert.equal(ver.value, "18");
    } finally {
      db.close();
    }
  });

  test("FTS5 MATCH works on dest (rebuild path)", () => {
    const db = openEncrypted(DST, KEY);
    try {
      const hits = db.prepare(
        "SELECT count(*) AS n FROM chunks_fts WHERE chunks_fts MATCH 'memoria'",
      ).get() as { n: bigint };
      assert.equal(Number(hits.n), 100, "FTS5 'memoria' should match all 100 synthetic chunks");

      // Sub-string token from row body
      const hits2 = db.prepare(
        "SELECT count(*) AS n FROM chunks_fts WHERE chunks_fts MATCH 'encrypted'",
      ).get() as { n: bigint };
      assert.equal(Number(hits2.n), 100);
    } finally {
      db.close();
    }
  });

  test("dest does NOT open with wrong key", () => {
    const db = openEncrypted(DST, "wrong-key-xyz");
    try {
      assert.throws(
        () => db.prepare("SELECT count(*) AS n FROM chunks").get(),
        (err: Error & { code?: string }) =>
          err.code === "SQLITE_NOTADB" ||
          /file is not a database|HMAC|file is encrypted/i.test(err.message),
        "wrong key must throw SQLITE_NOTADB",
      );
    } finally {
      db.close();
    }
  });

  test("AUTOINCREMENT sequence carries over (new INSERT continues from max+1)", () => {
    const db = openEncrypted(DST, KEY);
    try {
      // Insert one more row — id should be 101 (or greater) not start from 1
      db.prepare(
        "INSERT INTO chunks (source_file, chunk_text, chunk_type) VALUES (?, ?, ?)",
      ).run("post-migrate.md", "post-migrate content", "daily");
      const newId = (db.prepare("SELECT max(id) AS m FROM chunks").get() as { m: bigint }).m;
      assert.equal(Number(newId) >= 101, true, `new id should be >= 101, got ${newId}`);
    } finally {
      db.close();
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. Already-encrypted source aborts (no overwrite of caller intent)
// ─────────────────────────────────────────────────────────────────────────────

describe("already-encrypted source detection", () => {
  const SRC_ENC = join(TMP_ROOT, "already-enc-src.db");
  const DST = join(TMP_ROOT, "already-enc-dst.db");

  before(() => {
    // Make SRC an encrypted DB
    const db = openEncrypted(SRC_ENC, "some-prior-key");
    db.exec("CREATE TABLE chunks (id INTEGER PRIMARY KEY, content TEXT)");
    db.prepare("INSERT INTO chunks (content) VALUES (?)").run("encrypted");
    db.close();
  });

  test("isSourcePlaintext returns false for encrypted DB", () => {
    assert.equal(isSourcePlaintext(SRC_ENC), false);
  });

  test("migrateEncryptDb throws when source already encrypted", () => {
    assert.throws(
      () => migrateEncryptDb({ sourcePath: SRC_ENC, destPath: DST, key: "new-key", quiet: true }),
      /already encrypted/,
      "must abort with 'already encrypted' message",
    );
    assert.equal(existsSync(DST), false, "dest must not be created on abort");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. Dest exists → abort
// ─────────────────────────────────────────────────────────────────────────────

describe("dest-exists protection", () => {
  const SRC = join(TMP_ROOT, "dest-exists-src.db");
  const DST = join(TMP_ROOT, "dest-exists-dst.db");

  before(() => {
    buildSyntheticPlaintextDb(SRC, 10);
    // Put a dummy file at DST
    writeFileSync(DST, "I'm in your way");
  });

  test("migrate refuses to overwrite existing dest", () => {
    assert.throws(
      () => migrateEncryptDb({ sourcePath: SRC, destPath: DST, key: "k", quiet: true }),
      /already exists/,
    );
    // Verify the file was not modified
    assert.equal(statSync(DST).size, "I'm in your way".length);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. Edge-case argument validation
// ─────────────────────────────────────────────────────────────────────────────

describe("argument validation", () => {
  const SRC = join(TMP_ROOT, "argval-src.db");
  before(() => buildSyntheticPlaintextDb(SRC, 1));

  test("empty key rejected", () => {
    assert.throws(
      () => migrateEncryptDb({
        sourcePath: SRC,
        destPath: join(TMP_ROOT, "argval-dst-1.db"),
        key: "",
        quiet: true,
      }),
      /key must be non-empty/,
    );
  });

  test("same source and dest rejected", () => {
    assert.throws(
      () => migrateEncryptDb({ sourcePath: SRC, destPath: SRC, key: "k", quiet: true }),
      /source and dest must differ/,
    );
  });

  test("source not found throws", () => {
    assert.throws(
      () => isSourcePlaintext("/nonexistent/path/foo.db"),
      /does not exist/,
    );
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 5. CLI argument parsing
// ─────────────────────────────────────────────────────────────────────────────

describe("parseCliArgs", () => {
  test("positional args → opts", () => {
    const parsed = parseCliArgs(["/src.db", "/dst.db", "secret"], {});
    assert.equal(parsed?.opts.sourcePath, "/src.db");
    assert.equal(parsed?.opts.destPath, "/dst.db");
    assert.equal(parsed?.opts.key, "secret");
    assert.equal(parsed?.swap, false);
  });

  test("positional args + --swap flag → swap=true", () => {
    const parsed = parseCliArgs(["/src.db", "/dst.db", "secret", "--swap"], {});
    assert.equal(parsed?.swap, true);
  });

  test("env-driven (no positional args)", () => {
    const parsed = parseCliArgs([], {
      NOX_DB_PATH: "/env-src.db",
      NOX_DB_DEST: "/env-dst.db",
      NOX_DB_KEY: "env-secret",
    });
    assert.equal(parsed?.opts.sourcePath, "/env-src.db");
    assert.equal(parsed?.opts.destPath, "/env-dst.db");
    assert.equal(parsed?.opts.key, "env-secret");
  });

  test("missing args returns null (caller should exit 4)", () => {
    const parsed = parseCliArgs([], {});
    assert.equal(parsed, null);
  });

  test("env-driven + --swap", () => {
    const parsed = parseCliArgs(["--swap"], {
      NOX_DB_PATH: "/a.db",
      NOX_DB_DEST: "/b.db",
      NOX_DB_KEY: "k",
    });
    assert.equal(parsed?.swap, true);
    assert.equal(parsed?.opts.sourcePath, "/a.db");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 6. swapEncryptedIntoSource — atomic swap helper
// ─────────────────────────────────────────────────────────────────────────────

describe("swapEncryptedIntoSource", () => {
  const SRC = join(TMP_ROOT, "swap-src.db");
  const DST = join(TMP_ROOT, "swap-dst.db");
  const KEY = "swap-key";

  before(() => {
    buildSyntheticPlaintextDb(SRC, 25);
    migrateEncryptDb({ sourcePath: SRC, destPath: DST, key: KEY, quiet: true });
  });

  test("swap moves dest into source slot + creates backup", () => {
    const backupPath = swapEncryptedIntoSource(SRC, DST, true);
    // 1. Backup exists at the expected location
    assert.equal(existsSync(backupPath), true);
    assert.match(backupPath, /\.pre-encrypt-/);
    // 2. Original SRC path now holds the ENCRYPTED file
    assert.equal(existsSync(SRC), true);
    assert.equal(existsSync(DST), false, "dest should be moved away");
    // 3. SRC must open with the key (= encrypted)
    const db = openEncrypted(SRC, KEY);
    try {
      const cnt = db.prepare("SELECT count(*) AS n FROM chunks").get() as { n: bigint };
      assert.equal(Number(cnt.n), 25);
    } finally {
      db.close();
    }
    // 4. Backup is the original plaintext DB (no key needed)
    const plain = new Database(backupPath, { readonly: true });
    try {
      const cnt = plain.prepare("SELECT count(*) AS n FROM chunks").get() as { n: bigint | number };
      assert.equal(Number(cnt.n), 25, "backup should be original plaintext with 25 rows");
    } finally {
      plain.close();
    }
  });

  test("swap refuses when source missing", () => {
    assert.throws(
      () => swapEncryptedIntoSource("/nonexistent/x.db", DST, true),
      /sourcePath does not exist/,
    );
  });

  test("swap refuses when dest missing", () => {
    assert.throws(
      () => swapEncryptedIntoSource(SRC, "/nonexistent/y.db", true),
      /destPath does not exist/,
    );
  });
});
