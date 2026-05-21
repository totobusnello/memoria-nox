/**
 * staged-1.7a/tests/export-import-roundtrip.test.ts
 *
 * A2 Tier 1 — Export/Import roundtrip + tamper test suite.
 *
 * Run: node --test dist/tests/export-import-roundtrip.test.js
 *
 * Critical invariants (memory [[aad-bug-caught-by-integration-test]]):
 *   - Roundtrip uses TWO SEPARATE Database instances (source + target).
 *     Single-instance tests would silently pass even if AAD chained-checksum
 *     bugs slipped in. Integration only catches the real failure mode.
 *   - Tamper test flips ONE byte in the encrypted bundle and asserts import
 *     fails with a typed error — not a silent garbage decode.
 */

import { describe, it, before, after } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import Database from "better-sqlite3";

import {
  exportEncrypted,
  importEncrypted,
  ExportImportError,
  type ExportBundle,
} from "../edits/lib/export-import.js";
import { runCli } from "../edits/cli/export-import-cli.js";

// ────────────────────────────────────────────────────────────────────────────
// Test fixtures: tiny synthetic schema mirroring real nox-mem (chunks + KG).
// ────────────────────────────────────────────────────────────────────────────

const SCHEMA = `
  CREATE TABLE chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    content_hash TEXT UNIQUE,
    source TEXT,
    section TEXT,
    section_boost REAL,
    pain REAL DEFAULT 0.2,
    retention_days INTEGER,
    created_at TEXT NOT NULL
  );
  CREATE TABLE kg_entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name TEXT NOT NULL,
    type TEXT NOT NULL,
    frontmatter_json TEXT,
    UNIQUE(canonical_name, type)
  );
  CREATE TABLE kg_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_entity_id INTEGER NOT NULL,
    predicate TEXT NOT NULL,
    target_entity_id INTEGER NOT NULL,
    confidence REAL,
    UNIQUE(source_entity_id, predicate, target_entity_id)
  );
`;

function makeDb(path: string): Database.Database {
  const db = new Database(path);
  db.exec(SCHEMA);
  return db;
}

function seed(db: Database.Database): void {
  const insertChunk = db.prepare(
    `INSERT INTO chunks (content, content_hash, source, section, section_boost, pain, retention_days, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
  );
  insertChunk.run("first chunk text", "hash-001", "doc-a.md", "compiled", 2.0, 0.5, 365, "2026-05-21T10:00:00Z");
  insertChunk.run("second chunk", "hash-002", "doc-a.md", "timeline", 0.8, 0.2, 90, "2026-05-21T10:01:00Z");
  insertChunk.run("third chunk", "hash-003", "doc-b.md", null, 1.0, 0.9, 180, "2026-05-21T10:02:00Z");

  const insertEntity = db.prepare(
    `INSERT INTO kg_entities (canonical_name, type, frontmatter_json) VALUES (?, ?, ?)`,
  );
  insertEntity.run("Toto Busnello", "person", `{"role":"founder"}`);
  insertEntity.run("nox-mem", "project", `{"stack":"sqlite+vec"}`);

  const insertRel = db.prepare(
    `INSERT INTO kg_relations (source_entity_id, predicate, target_entity_id, confidence) VALUES (?, ?, ?, ?)`,
  );
  insertRel.run(1, "founded", 2, 0.95);
}

function countTable(db: Database.Database, table: string): number {
  const row = db.prepare(`SELECT COUNT(*) as n FROM ${table}`).get() as { n: number };
  return row.n;
}

// ────────────────────────────────────────────────────────────────────────────
// Shared workdir across cases
// ────────────────────────────────────────────────────────────────────────────

let workdir: string;

before(() => {
  workdir = mkdtempSync(join(tmpdir(), "nox-mem-a2-t1-"));
});

after(() => {
  if (workdir) rmSync(workdir, { recursive: true, force: true });
});

// ────────────────────────────────────────────────────────────────────────────
// Cases (ordered; each opens its own DBs to avoid cross-contamination)
// ────────────────────────────────────────────────────────────────────────────

describe("A2 Tier 1 — export/import roundtrip", () => {
  it("case 1: roundtrip preserves all rows across two separate DB instances", () => {
    const srcPath = join(workdir, "case1-src.db");
    const dstPath = join(workdir, "case1-dst.db");
    const bundlePath = join(workdir, "case1-bundle.json");
    const passphrase = "case1-test-passphrase-strong";

    const src = makeDb(srcPath);
    seed(src);

    const exp = exportEncrypted(src, passphrase, bundlePath);
    assert.equal(exp.chunksExported, 3);
    assert.equal(exp.entitiesExported, 2);
    assert.equal(exp.relationsExported, 1);
    src.close();

    // SEPARATE instance — critical per memory [[aad-bug-caught-by-integration-test]].
    const dst = makeDb(dstPath);
    const imp = importEncrypted(dst, passphrase, bundlePath, { strategy: "replace" });
    assert.equal(imp.chunksImported, 3);
    assert.equal(imp.entitiesImported, 2);
    assert.equal(imp.relationsImported, 1);
    assert.equal(imp.dryRun, false);

    // Content equality — sample fields
    const c1 = dst.prepare(`SELECT content, section_boost, pain FROM chunks WHERE content_hash = ?`).get("hash-001") as
      | { content: string; section_boost: number; pain: number }
      | undefined;
    assert.ok(c1, "chunk hash-001 should exist after import");
    assert.equal(c1.content, "first chunk text");
    assert.equal(c1.section_boost, 2.0);
    assert.equal(c1.pain, 0.5);

    const e = dst.prepare(`SELECT canonical_name, type FROM kg_entities ORDER BY id`).all() as
      { canonical_name: string; type: string }[];
    assert.deepEqual(
      e,
      [
        { canonical_name: "Toto Busnello", type: "person" },
        { canonical_name: "nox-mem", type: "project" },
      ],
    );

    dst.close();
  });

  it("case 2: tamper test — flipping one ciphertext byte triggers TAMPERED_BUNDLE error", () => {
    const srcPath = join(workdir, "case2-src.db");
    const dstPath = join(workdir, "case2-dst.db");
    const bundlePath = join(workdir, "case2-bundle.json");
    const passphrase = "case2-test-passphrase-strong";

    const src = makeDb(srcPath);
    seed(src);
    exportEncrypted(src, passphrase, bundlePath);
    src.close();

    // Flip a byte inside the ciphertext (decode → mutate → re-encode → re-serialize).
    const raw = readFileSync(bundlePath, "utf8");
    const bundle = JSON.parse(raw) as ExportBundle;
    const ct = Buffer.from(bundle.ciphertext, "base64");
    assert.ok(ct.length > 0, "ciphertext should be non-empty");
    // XOR one byte in the middle — guaranteed to break GCM auth.
    const mid = Math.floor(ct.length / 2);
    ct[mid] = (ct[mid]! ^ 0xff) & 0xff;
    bundle.ciphertext = ct.toString("base64");
    writeFileSync(bundlePath, JSON.stringify(bundle), "utf8");

    const dst = makeDb(dstPath);
    assert.throws(
      () => importEncrypted(dst, passphrase, bundlePath, { strategy: "replace" }),
      (e: unknown) => {
        assert.ok(e instanceof ExportImportError, `expected ExportImportError, got ${(e as Error).name}`);
        assert.equal((e as ExportImportError).code, "TAMPERED_BUNDLE");
        return true;
      },
    );
    // Target DB must remain untouched.
    assert.equal(countTable(dst, "chunks"), 0);
    dst.close();
  });

  it("case 3: wrong passphrase fails with TAMPERED_BUNDLE (indistinguishable from tamper — by design)", () => {
    const srcPath = join(workdir, "case3-src.db");
    const dstPath = join(workdir, "case3-dst.db");
    const bundlePath = join(workdir, "case3-bundle.json");

    const src = makeDb(srcPath);
    seed(src);
    exportEncrypted(src, "correct-passphrase-xyz", bundlePath);
    src.close();

    const dst = makeDb(dstPath);
    assert.throws(
      () =>
        importEncrypted(dst, "WRONG-passphrase-abc", bundlePath, { strategy: "replace" }),
      (e: unknown) => {
        assert.ok(e instanceof ExportImportError);
        assert.equal((e as ExportImportError).code, "TAMPERED_BUNDLE");
        return true;
      },
    );
    assert.equal(countTable(dst, "chunks"), 0);
    dst.close();
  });

  it("case 4: AAD verification — modifying the manifest header (chunks_count) triggers AAD_MISMATCH", () => {
    const srcPath = join(workdir, "case4-src.db");
    const dstPath = join(workdir, "case4-dst.db");
    const bundlePath = join(workdir, "case4-bundle.json");
    const passphrase = "case4-test-passphrase-strong";

    const src = makeDb(srcPath);
    seed(src);
    exportEncrypted(src, passphrase, bundlePath);
    src.close();

    const raw = readFileSync(bundlePath, "utf8");
    const bundle = JSON.parse(raw) as ExportBundle;
    bundle.chunks_count = bundle.chunks_count + 99; // tamper the header
    writeFileSync(bundlePath, JSON.stringify(bundle), "utf8");

    const dst = makeDb(dstPath);
    assert.throws(
      () => importEncrypted(dst, passphrase, bundlePath, { strategy: "replace" }),
      (e: unknown) => {
        assert.ok(e instanceof ExportImportError);
        assert.equal((e as ExportImportError).code, "AAD_MISMATCH");
        return true;
      },
    );
    dst.close();
  });

  it("case 5: empty DB roundtrip — export 0 rows, import into empty target succeeds", () => {
    const srcPath = join(workdir, "case5-src.db");
    const dstPath = join(workdir, "case5-dst.db");
    const bundlePath = join(workdir, "case5-bundle.json");
    const passphrase = "case5-test-passphrase-strong";

    const src = makeDb(srcPath);
    // no seed → all tables empty
    const exp = exportEncrypted(src, passphrase, bundlePath);
    assert.equal(exp.chunksExported, 0);
    assert.equal(exp.entitiesExported, 0);
    assert.equal(exp.relationsExported, 0);
    src.close();

    const dst = makeDb(dstPath);
    const imp = importEncrypted(dst, passphrase, bundlePath, { strategy: "replace" });
    assert.equal(imp.chunksImported, 0);
    assert.equal(imp.entitiesImported, 0);
    assert.equal(imp.relationsImported, 0);
    dst.close();
  });

  it("case 6: dry-run returns counts but does not mutate the target DB", () => {
    const srcPath = join(workdir, "case6-src.db");
    const dstPath = join(workdir, "case6-dst.db");
    const bundlePath = join(workdir, "case6-bundle.json");
    const passphrase = "case6-test-passphrase-strong";

    const src = makeDb(srcPath);
    seed(src);
    exportEncrypted(src, passphrase, bundlePath);
    src.close();

    const dst = makeDb(dstPath);
    const imp = importEncrypted(dst, passphrase, bundlePath, {
      strategy: "merge",
      dryRun: true,
    });
    assert.equal(imp.dryRun, true);
    // Reports what would be imported (no rows exist yet → all would be).
    assert.equal(imp.chunksImported, 3);
    assert.equal(imp.entitiesImported, 2);
    assert.equal(imp.relationsImported, 1);
    // DB must still be untouched.
    assert.equal(countTable(dst, "chunks"), 0);
    assert.equal(countTable(dst, "kg_entities"), 0);
    assert.equal(countTable(dst, "kg_relations"), 0);
    dst.close();
  });

  it("case 7: replace strategy clears target DB before import", () => {
    const srcPath = join(workdir, "case7-src.db");
    const dstPath = join(workdir, "case7-dst.db");
    const bundlePath = join(workdir, "case7-bundle.json");
    const passphrase = "case7-test-passphrase-strong";

    const src = makeDb(srcPath);
    seed(src);
    exportEncrypted(src, passphrase, bundlePath);
    src.close();

    const dst = makeDb(dstPath);
    // Pre-populate target with orthogonal data
    dst.prepare(
      `INSERT INTO chunks (content, content_hash, source, section, section_boost, pain, retention_days, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    ).run("preexisting", "hash-preexisting", "old.md", "compiled", 1.0, 0.1, 90, "2026-01-01T00:00:00Z");
    assert.equal(countTable(dst, "chunks"), 1);

    const imp = importEncrypted(dst, passphrase, bundlePath, { strategy: "replace" });
    assert.equal(imp.chunksImported, 3);
    assert.equal(countTable(dst, "chunks"), 3); // pre-existing wiped
    const survivors = dst.prepare(`SELECT content_hash FROM chunks ORDER BY content_hash`).all() as
      { content_hash: string }[];
    assert.deepEqual(
      survivors.map((r) => r.content_hash),
      ["hash-001", "hash-002", "hash-003"],
    );
    dst.close();
  });

  it("case 8: merge strategy preserves existing rows + skips duplicates by content_hash", () => {
    const srcPath = join(workdir, "case8-src.db");
    const dstPath = join(workdir, "case8-dst.db");
    const bundlePath = join(workdir, "case8-bundle.json");
    const passphrase = "case8-test-passphrase-strong";

    const src = makeDb(srcPath);
    seed(src);
    exportEncrypted(src, passphrase, bundlePath);
    src.close();

    const dst = makeDb(dstPath);
    // Pre-populate target with:
    //   (a) one row with the SAME content_hash as the bundle (should be skipped)
    //   (b) one row with a unique content_hash (must survive)
    dst.prepare(
      `INSERT INTO chunks (content, content_hash, source, section, section_boost, pain, retention_days, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    ).run("preexisting unique row", "hash-unique-existing", "old.md", "compiled", 1.0, 0.1, 90, "2026-01-01T00:00:00Z");
    dst.prepare(
      `INSERT INTO chunks (content, content_hash, source, section, section_boost, pain, retention_days, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    ).run("preexisting collides", "hash-001", "old.md", "compiled", 1.0, 0.1, 90, "2026-01-01T00:00:00Z");
    assert.equal(countTable(dst, "chunks"), 2);

    const imp = importEncrypted(dst, passphrase, bundlePath, { strategy: "merge" });
    // Out of 3 source chunks, hash-001 collides and is skipped → 2 imported.
    assert.equal(imp.chunksImported, 2);
    assert.ok(
      imp.conflicts.some((c) => c.table === "chunks" && c.key === "hash-001"),
      "expected conflict for hash-001",
    );
    // Final DB = 2 pre-existing + 2 newly imported = 4
    assert.equal(countTable(dst, "chunks"), 4);
    // The pre-existing unique row must still exist
    const stillThere = dst
      .prepare(`SELECT content FROM chunks WHERE content_hash = ?`)
      .get("hash-unique-existing") as { content: string } | undefined;
    assert.ok(stillThere);
    assert.equal(stillThere.content, "preexisting unique row");
    // The pre-existing colliding row keeps its original content
    const colliding = dst
      .prepare(`SELECT content FROM chunks WHERE content_hash = ?`)
      .get("hash-001") as { content: string } | undefined;
    assert.equal(colliding!.content, "preexisting collides");
    dst.close();
  });

  it("case 9 [bonus]: weak passphrase is rejected at export time (WEAK_PASSPHRASE)", () => {
    const srcPath = join(workdir, "case9-src.db");
    const bundlePath = join(workdir, "case9-bundle.json");

    const src = makeDb(srcPath);
    seed(src);
    assert.throws(
      () => exportEncrypted(src, "short", bundlePath),
      (e: unknown) => {
        assert.ok(e instanceof ExportImportError);
        assert.equal((e as ExportImportError).code, "WEAK_PASSPHRASE");
        return true;
      },
    );
    src.close();
  });

  it("case 10 [bonus]: CLI refuses --passphrase=<value> argv flag (no leak via ps aux)", () => {
    const srcPath = join(workdir, "case10-src.db");
    const db = makeDb(srcPath);
    const stderrLines: string[] = [];
    const result = runCli({
      argv: ["export", "--output", join(workdir, "case10-bundle.json"), "--passphrase=leak-via-argv-1234"],
      env: {},
      db,
      stdout: () => {},
      stderr: (m) => stderrLines.push(m),
    });
    assert.equal(result.exitCode, 2);
    assert.ok(
      stderrLines.some((l) => /REFUSED/.test(l) && /passphrase/i.test(l)),
      `expected stderr to include REFUSED passphrase message; got: ${JSON.stringify(stderrLines)}`,
    );
    db.close();
  });

  it("case 11 [bonus]: CLI happy-path roundtrip end-to-end via subcommands", () => {
    const srcPath = join(workdir, "case11-src.db");
    const dstPath = join(workdir, "case11-dst.db");
    const bundlePath = join(workdir, "case11-bundle.json");
    const ENV_NAME = "NOX_TEST_CASE11_PASSPHRASE";
    const env = { [ENV_NAME]: "case11-cli-roundtrip-passphrase" };

    const src = makeDb(srcPath);
    seed(src);
    const exportLines: string[] = [];
    const expResult = runCli({
      argv: ["export", "--output", bundlePath, "--passphrase-env", ENV_NAME],
      env,
      db: src,
      stdout: (m) => exportLines.push(m),
      stderr: () => {},
    });
    assert.equal(expResult.exitCode, 0);
    const exportJson = JSON.parse(exportLines[0]!) as {
      ok: boolean;
      chunks_exported: number;
    };
    assert.equal(exportJson.ok, true);
    assert.equal(exportJson.chunks_exported, 3);
    src.close();

    const dst = makeDb(dstPath);
    const importLines: string[] = [];
    const impResult = runCli({
      argv: [
        "import",
        "--input",
        bundlePath,
        "--passphrase-env",
        ENV_NAME,
        "--strategy",
        "replace",
      ],
      env,
      db: dst,
      stdout: (m) => importLines.push(m),
      stderr: () => {},
    });
    assert.equal(impResult.exitCode, 0);
    const importJson = JSON.parse(importLines[0]!) as { chunks_imported: number };
    assert.equal(importJson.chunks_imported, 3);
    assert.equal(countTable(dst, "chunks"), 3);
    dst.close();
  });
});
