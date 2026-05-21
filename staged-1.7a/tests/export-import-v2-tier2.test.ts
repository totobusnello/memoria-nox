/**
 * staged-1.7a/tests/export-import-v2-tier2.test.ts
 *
 * A2 Tier 2 — Per-table encryption export/import test suite (V2 bundle format).
 *
 * Run:
 *   cd staged-1.7a && npx tsc -p tsconfig.export-import.json && \
 *     node --test dist/tests/export-import-v2-tier2.test.js
 *
 * Critical invariants (memory `[[aad-bug-caught-by-integration-test]]`):
 *   - Roundtrip uses TWO SEPARATE Database instances (source + target).
 *   - Per-table tamper test flips ONE byte in ONE table's ciphertext and
 *     asserts that subset import of the OTHER tables still succeeds.
 *   - V1 backward-compat path is exercised through the auto-detect importer.
 */

import { describe, it, before, after } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import Database from "better-sqlite3";

import {
  // T1 used for the v1 backward-compat case
  exportEncrypted,
  // T2 public API
  exportEncryptedV2,
  importEncryptedV2,
  importEncryptedAuto,
  ExportImportError,
  type ExportBundleV2,
} from "../edits/lib/export-import.js";
import { runCli } from "../edits/cli/export-import-cli.js";

// ────────────────────────────────────────────────────────────────────────────
// Fixtures (same schema as T1 — chunks + KG)
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
// Shared workdir
// ────────────────────────────────────────────────────────────────────────────

let workdir: string;

before(() => {
  workdir = mkdtempSync(join(tmpdir(), "nox-mem-a2-t2-"));
});

after(() => {
  if (workdir) rmSync(workdir, { recursive: true, force: true });
});

// ────────────────────────────────────────────────────────────────────────────
// Cases
// ────────────────────────────────────────────────────────────────────────────

describe("A2 Tier 2 — V2 per-table encryption export/import", () => {
  it("case 1: V2 roundtrip preserves all 3 tables across two separate DB instances", () => {
    const srcPath = join(workdir, "case1-src.db");
    const dstPath = join(workdir, "case1-dst.db");
    const bundlePath = join(workdir, "case1-bundle.json");
    const passphrase = "case1-v2-test-passphrase-strong";

    const src = makeDb(srcPath);
    seed(src);

    const exp = exportEncryptedV2(src, passphrase, bundlePath);
    assert.equal(exp.tablesExported.length, 3, "expected 3 tables in V2 bundle");
    const byName = Object.fromEntries(exp.tablesExported.map((t) => [t.name, t.rows]));
    assert.equal(byName.chunks, 3);
    assert.equal(byName.kg_entities, 2);
    assert.equal(byName.kg_relations, 1);
    src.close();

    // SEPARATE instance — critical per `[[aad-bug-caught-by-integration-test]]`.
    const dst = makeDb(dstPath);
    const imp = importEncryptedV2(dst, passphrase, bundlePath, { strategy: "replace" });
    assert.equal(imp.dryRun, false);
    const impByName = Object.fromEntries(imp.tablesImported.map((t) => [t.name, t.rows]));
    assert.equal(impByName.chunks, 3);
    assert.equal(impByName.kg_entities, 2);
    assert.equal(impByName.kg_relations, 1);

    // Content equality — sample fields across tables
    const c1 = dst.prepare(`SELECT content, section_boost, pain FROM chunks WHERE content_hash = ?`).get("hash-001") as
      | { content: string; section_boost: number; pain: number }
      | undefined;
    assert.ok(c1, "chunk hash-001 should exist after V2 import");
    assert.equal(c1.content, "first chunk text");
    assert.equal(c1.section_boost, 2.0);
    assert.equal(c1.pain, 0.5);

    const ents = dst.prepare(`SELECT canonical_name, type FROM kg_entities ORDER BY id`).all() as
      { canonical_name: string; type: string }[];
    assert.deepEqual(
      ents,
      [
        { canonical_name: "Toto Busnello", type: "person" },
        { canonical_name: "nox-mem", type: "project" },
      ],
    );

    const rels = dst.prepare(`SELECT source_entity_id, predicate, target_entity_id, confidence FROM kg_relations`).all() as
      { source_entity_id: number; predicate: string; target_entity_id: number; confidence: number }[];
    assert.equal(rels.length, 1);
    assert.equal(rels[0]!.predicate, "founded");
    assert.equal(rels[0]!.confidence, 0.95);

    dst.close();
  });

  it("case 2: per-table tamper — flip chunks ciphertext byte → import chunks fails; subset import of others still OK", () => {
    const srcPath = join(workdir, "case2-src.db");
    const dstAllPath = join(workdir, "case2-dst-all.db");
    const dstSubsetPath = join(workdir, "case2-dst-subset.db");
    const bundlePath = join(workdir, "case2-bundle.json");
    const passphrase = "case2-v2-test-passphrase-strong";

    const src = makeDb(srcPath);
    seed(src);
    exportEncryptedV2(src, passphrase, bundlePath);
    src.close();

    // Flip one byte inside the CHUNKS ciphertext only.
    const raw = readFileSync(bundlePath, "utf8");
    const bundle = JSON.parse(raw) as ExportBundleV2;
    const chunksCt = Buffer.from(bundle.tables.chunks!.ciphertext, "base64");
    assert.ok(chunksCt.length > 0, "chunks ciphertext should be non-empty");
    const mid = Math.floor(chunksCt.length / 2);
    chunksCt[mid] = (chunksCt[mid]! ^ 0xff) & 0xff;
    bundle.tables.chunks!.ciphertext = chunksCt.toString("base64");
    writeFileSync(bundlePath, JSON.stringify(bundle), "utf8");

    // Full import (default tables = all) must fail because chunks is corrupted.
    const dstAll = makeDb(dstAllPath);
    assert.throws(
      () => importEncryptedV2(dstAll, passphrase, bundlePath, { strategy: "replace" }),
      (e: unknown) => {
        assert.ok(e instanceof ExportImportError, `expected ExportImportError, got ${(e as Error).name}`);
        assert.equal((e as ExportImportError).code, "TAMPERED_BUNDLE");
        return true;
      },
    );
    // Target DB must remain untouched (transaction or pre-decrypt throw → no DB mutation).
    assert.equal(countTable(dstAll, "chunks"), 0);
    assert.equal(countTable(dstAll, "kg_entities"), 0);
    assert.equal(countTable(dstAll, "kg_relations"), 0);
    dstAll.close();

    // Subset import of ONLY the OTHER tables must succeed — chunks tampered byte
    // is never even decrypted in this path.
    const dstSubset = makeDb(dstSubsetPath);
    const imp = importEncryptedV2(dstSubset, passphrase, bundlePath, {
      strategy: "replace",
      tables: ["kg_entities", "kg_relations"],
    });
    const impByName = Object.fromEntries(imp.tablesImported.map((t) => [t.name, t.rows]));
    assert.equal(impByName.kg_entities, 2);
    assert.equal(impByName.kg_relations, 1);
    // chunks should NOT have been touched
    assert.equal(countTable(dstSubset, "chunks"), 0);
    assert.equal(countTable(dstSubset, "kg_entities"), 2);
    assert.equal(countTable(dstSubset, "kg_relations"), 1);
    dstSubset.close();
  });

  it("case 3: subset export — only chunks in bundle", () => {
    const srcPath = join(workdir, "case3-src.db");
    const dstPath = join(workdir, "case3-dst.db");
    const bundlePath = join(workdir, "case3-bundle.json");
    const passphrase = "case3-v2-test-passphrase-strong";

    const src = makeDb(srcPath);
    seed(src);
    const exp = exportEncryptedV2(src, passphrase, bundlePath, { tables: ["chunks"] });
    assert.equal(exp.tablesExported.length, 1);
    assert.equal(exp.tablesExported[0]!.name, "chunks");
    assert.equal(exp.tablesExported[0]!.rows, 3);

    // Inspect the bundle file directly: tables map should have only "chunks"
    const bundle = JSON.parse(readFileSync(bundlePath, "utf8")) as ExportBundleV2;
    assert.deepEqual(Object.keys(bundle.tables), ["chunks"]);
    src.close();

    // Import: target gets chunks only, kg_* remain empty.
    const dst = makeDb(dstPath);
    const imp = importEncryptedV2(dst, passphrase, bundlePath, { strategy: "replace" });
    assert.equal(imp.tablesImported.length, 1);
    assert.equal(imp.tablesImported[0]!.name, "chunks");
    assert.equal(imp.tablesImported[0]!.rows, 3);
    assert.equal(countTable(dst, "chunks"), 3);
    assert.equal(countTable(dst, "kg_entities"), 0);
    assert.equal(countTable(dst, "kg_relations"), 0);
    dst.close();
  });

  it("case 4: subset import — pull only kg_entities from a full bundle", () => {
    const srcPath = join(workdir, "case4-src.db");
    const dstPath = join(workdir, "case4-dst.db");
    const bundlePath = join(workdir, "case4-bundle.json");
    const passphrase = "case4-v2-test-passphrase-strong";

    const src = makeDb(srcPath);
    seed(src);
    exportEncryptedV2(src, passphrase, bundlePath);
    src.close();

    const dst = makeDb(dstPath);
    const imp = importEncryptedV2(dst, passphrase, bundlePath, {
      strategy: "replace",
      tables: ["kg_entities"],
    });
    assert.equal(imp.tablesImported.length, 1);
    assert.equal(imp.tablesImported[0]!.name, "kg_entities");
    assert.equal(imp.tablesImported[0]!.rows, 2);
    // chunks + kg_relations must remain untouched
    assert.equal(countTable(dst, "chunks"), 0);
    assert.equal(countTable(dst, "kg_entities"), 2);
    assert.equal(countTable(dst, "kg_relations"), 0);
    dst.close();
  });

  it("case 5: backward compat — old V1 bundle imports correctly via auto-detect", () => {
    const srcPath = join(workdir, "case5-src.db");
    const dstPath = join(workdir, "case5-dst.db");
    const bundlePath = join(workdir, "case5-v1-bundle.json");
    const passphrase = "case5-v1-backcompat-passphrase";

    // Produce a V1 bundle with the legacy exporter.
    const src = makeDb(srcPath);
    seed(src);
    exportEncrypted(src, passphrase, bundlePath);
    src.close();

    // Verify it really is v1 on disk.
    const bundle = JSON.parse(readFileSync(bundlePath, "utf8")) as { version: number };
    assert.equal(bundle.version, 1);

    // Import via the auto-detect path — must route to V1 handler.
    const dst = makeDb(dstPath);
    const imp = importEncryptedAuto(dst, passphrase, bundlePath, { strategy: "replace" });
    assert.equal(imp.dryRun, false);
    const byName = Object.fromEntries(imp.tablesImported.map((t) => [t.name, t.rows]));
    assert.equal(byName.chunks, 3);
    assert.equal(byName.kg_entities, 2);
    assert.equal(byName.kg_relations, 1);
    // Confirm in DB
    assert.equal(countTable(dst, "chunks"), 3);
    assert.equal(countTable(dst, "kg_entities"), 2);
    assert.equal(countTable(dst, "kg_relations"), 1);
    dst.close();
  });

  it("case 6: V2 dry-run returns per-table counts and does not mutate the target", () => {
    const srcPath = join(workdir, "case6-src.db");
    const dstPath = join(workdir, "case6-dst.db");
    const bundlePath = join(workdir, "case6-bundle.json");
    const passphrase = "case6-v2-test-passphrase-strong";

    const src = makeDb(srcPath);
    seed(src);
    exportEncryptedV2(src, passphrase, bundlePath);
    src.close();

    const dst = makeDb(dstPath);
    const imp = importEncryptedV2(dst, passphrase, bundlePath, {
      strategy: "merge",
      dryRun: true,
    });
    assert.equal(imp.dryRun, true);
    const byName = Object.fromEntries(imp.tablesImported.map((t) => [t.name, t.rows]));
    assert.equal(byName.chunks, 3);
    assert.equal(byName.kg_entities, 2);
    assert.equal(byName.kg_relations, 1);
    // Nothing should have been written.
    assert.equal(countTable(dst, "chunks"), 0);
    assert.equal(countTable(dst, "kg_entities"), 0);
    assert.equal(countTable(dst, "kg_relations"), 0);
    dst.close();
  });

  it("case 7: replace per-table — chunks replaced, kg_entities untouched (subset import)", () => {
    const srcPath = join(workdir, "case7-src.db");
    const dstPath = join(workdir, "case7-dst.db");
    const bundlePath = join(workdir, "case7-bundle.json");
    const passphrase = "case7-v2-test-passphrase-strong";

    // Source bundle has all three tables seeded.
    const src = makeDb(srcPath);
    seed(src);
    exportEncryptedV2(src, passphrase, bundlePath);
    src.close();

    // Target pre-populated with DIFFERENT chunks AND DIFFERENT kg_entities.
    const dst = makeDb(dstPath);
    dst.prepare(
      `INSERT INTO chunks (content, content_hash, source, section, section_boost, pain, retention_days, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    ).run("preexisting chunk", "hash-preex", "old.md", "compiled", 1.0, 0.1, 90, "2026-01-01T00:00:00Z");
    dst.prepare(
      `INSERT INTO kg_entities (canonical_name, type, frontmatter_json) VALUES (?, ?, ?)`,
    ).run("Preexisting Person", "person", `{"role":"keeper"}`);
    assert.equal(countTable(dst, "chunks"), 1);
    assert.equal(countTable(dst, "kg_entities"), 1);

    // Replace ONLY chunks — kg_entities must remain untouched even though strategy=replace.
    const imp = importEncryptedV2(dst, passphrase, bundlePath, {
      strategy: "replace",
      tables: ["chunks"],
    });
    assert.equal(imp.tablesImported.length, 1);
    assert.equal(imp.tablesImported[0]!.name, "chunks");
    assert.equal(imp.tablesImported[0]!.rows, 3);

    // chunks: pre-existing wiped + 3 from bundle
    assert.equal(countTable(dst, "chunks"), 3);
    const preExisting = dst.prepare(`SELECT 1 FROM chunks WHERE content_hash = ?`).get("hash-preex");
    assert.equal(preExisting, undefined, "pre-existing chunk row must have been deleted");

    // kg_entities: untouched (still has the original pre-existing row)
    assert.equal(countTable(dst, "kg_entities"), 1);
    const survivor = dst.prepare(`SELECT canonical_name FROM kg_entities`).get() as
      | { canonical_name: string }
      | undefined;
    assert.equal(survivor?.canonical_name, "Preexisting Person");

    // kg_relations: also untouched
    assert.equal(countTable(dst, "kg_relations"), 0);
    dst.close();
  });

  it("case 8: merge per-table — preserves existing rows where IDs collide; conflicts reported per table", () => {
    const srcPath = join(workdir, "case8-src.db");
    const dstPath = join(workdir, "case8-dst.db");
    const bundlePath = join(workdir, "case8-bundle.json");
    const passphrase = "case8-v2-test-passphrase-strong";

    const src = makeDb(srcPath);
    seed(src);
    exportEncryptedV2(src, passphrase, bundlePath);
    src.close();

    const dst = makeDb(dstPath);
    // Pre-populate the target with a row that collides on chunks (hash-001),
    // plus an unrelated chunk that must survive merge.
    dst.prepare(
      `INSERT INTO chunks (content, content_hash, source, section, section_boost, pain, retention_days, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    ).run("preexisting unique", "hash-unique-existing", "old.md", "compiled", 1.0, 0.1, 90, "2026-01-01T00:00:00Z");
    dst.prepare(
      `INSERT INTO chunks (content, content_hash, source, section, section_boost, pain, retention_days, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    ).run("preexisting collides", "hash-001", "old.md", "compiled", 1.0, 0.1, 90, "2026-01-01T00:00:00Z");

    // Pre-populate the target with the same kg_entity (canonical_name+type collide).
    dst.prepare(
      `INSERT INTO kg_entities (canonical_name, type, frontmatter_json) VALUES (?, ?, ?)`,
    ).run("Toto Busnello", "person", `{"role":"old-record"}`);

    const imp = importEncryptedV2(dst, passphrase, bundlePath, { strategy: "merge" });
    // chunks: hash-001 collides → 2 imported out of 3, 1 conflict
    const chunksRow = imp.tablesImported.find((t) => t.name === "chunks")!;
    assert.equal(chunksRow.rows, 2);
    assert.equal(chunksRow.conflicts, 1);
    assert.ok(
      imp.conflicts.some((c) => c.table === "chunks" && c.key === "hash-001"),
      "expected chunks conflict for hash-001",
    );

    // kg_entities: "Toto Busnello::person" collides → 1 imported, 1 conflict
    const entRow = imp.tablesImported.find((t) => t.name === "kg_entities")!;
    assert.equal(entRow.rows, 1);
    assert.equal(entRow.conflicts, 1);

    // Pre-existing colliding chunk must keep its content
    const surviving = dst.prepare(`SELECT content FROM chunks WHERE content_hash = ?`).get("hash-001") as
      | { content: string }
      | undefined;
    assert.equal(surviving?.content, "preexisting collides");

    // Pre-existing unique chunk must still be there
    const stillThere = dst.prepare(`SELECT 1 FROM chunks WHERE content_hash = ?`).get("hash-unique-existing");
    assert.ok(stillThere, "pre-existing unique chunk must survive merge");

    // Pre-existing kg_entities row must keep its frontmatter_json (not overwritten)
    const ent = dst.prepare(`SELECT frontmatter_json FROM kg_entities WHERE canonical_name = ? AND type = ?`)
      .get("Toto Busnello", "person") as { frontmatter_json: string } | undefined;
    assert.equal(ent?.frontmatter_json, `{"role":"old-record"}`);

    dst.close();
  });

  it("case 9 [bonus]: per-table AAD tamper — flipping kg_entities rows_count in envelope triggers AAD_MISMATCH", () => {
    const srcPath = join(workdir, "case9-src.db");
    const dstPath = join(workdir, "case9-dst.db");
    const bundlePath = join(workdir, "case9-bundle.json");
    const passphrase = "case9-v2-test-passphrase-strong";

    const src = makeDb(srcPath);
    seed(src);
    exportEncryptedV2(src, passphrase, bundlePath);
    src.close();

    // Tamper the kg_entities rows_count in the envelope header.
    const raw = readFileSync(bundlePath, "utf8");
    const bundle = JSON.parse(raw) as ExportBundleV2;
    bundle.tables.kg_entities!.rows_count = bundle.tables.kg_entities!.rows_count + 7;
    writeFileSync(bundlePath, JSON.stringify(bundle), "utf8");

    const dst = makeDb(dstPath);
    assert.throws(
      () => importEncryptedV2(dst, passphrase, bundlePath, { strategy: "replace" }),
      (e: unknown) => {
        assert.ok(e instanceof ExportImportError);
        assert.equal((e as ExportImportError).code, "AAD_MISMATCH");
        return true;
      },
    );
    // Target unchanged
    assert.equal(countTable(dst, "chunks"), 0);
    assert.equal(countTable(dst, "kg_entities"), 0);
    assert.equal(countTable(dst, "kg_relations"), 0);
    dst.close();
  });

  it("case 10 [bonus]: CLI happy-path V2 export with --tables subset + auto-detect import", () => {
    const srcPath = join(workdir, "case10-src.db");
    const dstPath = join(workdir, "case10-dst.db");
    const bundlePath = join(workdir, "case10-bundle.json");
    const ENV_NAME = "NOX_TEST_CASE10_PASSPHRASE";
    const env = { [ENV_NAME]: "case10-cli-v2-passphrase-strong" };

    const src = makeDb(srcPath);
    seed(src);
    const exportLines: string[] = [];
    const exp = runCli({
      argv: [
        "export",
        "--output", bundlePath,
        "--passphrase-env", ENV_NAME,
        "--tables", "chunks,kg_relations",
      ],
      env,
      db: src,
      stdout: (m) => exportLines.push(m),
      stderr: () => {},
    });
    assert.equal(exp.exitCode, 0);
    const exportJson = JSON.parse(exportLines[0]!) as {
      ok: boolean;
      tier: number;
      tables_exported: { name: string; rows: number }[];
    };
    assert.equal(exportJson.ok, true);
    assert.equal(exportJson.tier, 2);
    assert.deepEqual(
      exportJson.tables_exported.map((t) => t.name).sort(),
      ["chunks", "kg_relations"],
    );
    src.close();

    // Import via auto-detect — bundle is v2.
    const dst = makeDb(dstPath);
    const importLines: string[] = [];
    const imp = runCli({
      argv: ["import", "--input", bundlePath, "--passphrase-env", ENV_NAME, "--strategy", "replace"],
      env,
      db: dst,
      stdout: (m) => importLines.push(m),
      stderr: () => {},
    });
    assert.equal(imp.exitCode, 0);
    const impJson = JSON.parse(importLines[0]!) as {
      tables_imported: { name: string; rows: number }[];
    };
    const impByName = Object.fromEntries(impJson.tables_imported.map((t) => [t.name, t.rows]));
    assert.equal(impByName.chunks, 3);
    assert.equal(impByName.kg_relations, 1);
    assert.equal(countTable(dst, "chunks"), 3);
    assert.equal(countTable(dst, "kg_entities"), 0); // not in bundle
    assert.equal(countTable(dst, "kg_relations"), 1);
    dst.close();
  });

  it("case 11 [bonus]: CLI --tier 1 forces v1 path; import auto-detect handles v1 transparently", () => {
    const srcPath = join(workdir, "case11-src.db");
    const dstPath = join(workdir, "case11-dst.db");
    const bundlePath = join(workdir, "case11-bundle.json");
    const ENV_NAME = "NOX_TEST_CASE11V2_PASSPHRASE";
    const env = { [ENV_NAME]: "case11-cli-v1-backcompat-passphrase" };

    const src = makeDb(srcPath);
    seed(src);
    // Force V1 via CLI flag
    const expResult = runCli({
      argv: ["export", "--output", bundlePath, "--passphrase-env", ENV_NAME, "--tier", "1"],
      env,
      db: src,
      stdout: () => {},
      stderr: () => {},
    });
    assert.equal(expResult.exitCode, 0);
    const bundle = JSON.parse(readFileSync(bundlePath, "utf8")) as { version: number };
    assert.equal(bundle.version, 1, "expected V1 bundle when --tier 1 specified");
    src.close();

    // Auto-detect import handles V1.
    const dst = makeDb(dstPath);
    const importLines: string[] = [];
    const impResult = runCli({
      argv: ["import", "--input", bundlePath, "--passphrase-env", ENV_NAME, "--strategy", "replace"],
      env,
      db: dst,
      stdout: (m) => importLines.push(m),
      stderr: () => {},
    });
    assert.equal(impResult.exitCode, 0);
    const impJson = JSON.parse(importLines[0]!) as { tables_imported: { name: string; rows: number }[] };
    const byName = Object.fromEntries(impJson.tables_imported.map((t) => [t.name, t.rows]));
    assert.equal(byName.chunks, 3);
    assert.equal(byName.kg_entities, 2);
    assert.equal(byName.kg_relations, 1);
    dst.close();
  });

  it("case 12 [bonus]: rejecting unknown tables in --tables yields a typed error", () => {
    const srcPath = join(workdir, "case12-src.db");
    const bundlePath = join(workdir, "case12-bundle.json");
    const passphrase = "case12-v2-test-passphrase-strong";

    const src = makeDb(srcPath);
    seed(src);
    assert.throws(
      () => exportEncryptedV2(src, passphrase, bundlePath, { tables: ["chunks", "bogus_table"] }),
      (e: unknown) => {
        assert.ok(e instanceof ExportImportError);
        assert.equal((e as ExportImportError).code, "UNKNOWN_TABLE");
        return true;
      },
    );
    src.close();
  });

  it("case 13 [bonus]: requesting a table absent from the bundle yields TABLE_NOT_IN_BUNDLE", () => {
    const srcPath = join(workdir, "case13-src.db");
    const dstPath = join(workdir, "case13-dst.db");
    const bundlePath = join(workdir, "case13-bundle.json");
    const passphrase = "case13-v2-test-passphrase-strong";

    const src = makeDb(srcPath);
    seed(src);
    // Bundle contains only chunks.
    exportEncryptedV2(src, passphrase, bundlePath, { tables: ["chunks"] });
    src.close();

    const dst = makeDb(dstPath);
    assert.throws(
      () =>
        importEncryptedV2(dst, passphrase, bundlePath, {
          strategy: "replace",
          tables: ["kg_entities"], // not in bundle
        }),
      (e: unknown) => {
        assert.ok(e instanceof ExportImportError);
        assert.equal((e as ExportImportError).code, "TABLE_NOT_IN_BUNDLE");
        return true;
      },
    );
    dst.close();
  });
});
