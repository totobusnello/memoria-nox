/**
 * T11/T12 — CLI argv parser tests + end-to-end CLI runner tests.
 *
 * Critically: NEVER accept passphrase from argv. Tested first because security.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { parseExportArgs, runCliExport } from "../export.js";
import { parseImportArgs, runCliImport } from "../import.js";
import { ChunkRow } from "../../lib/archive/types.js";

function makeChunk(id: number): ChunkRow {
  return {
    id,
    content: `chunk-${id}`,
    content_hash: `h-${id}`,
    source_path: null,
    source_kind: null,
    project: "test",
    created_at: "2026-05-18T00:00:00.000Z",
    updated_at: null,
    retention_days: 90,
    pain: 0.2,
    section: null,
    section_boost: null,
    metadata_json: null,
  };
}

function dbReader(n: number) {
  return async () => ({
    schema_version: 18,
    source_hostname: "test",
    source_nox_mem_version: "v3.7-test",
    embedding_provider: "gemini",
    embedding_model: "gemini-embedding-001",
    embedding_dim: 32,
    sqlite_vec_version: null,
    chunks: Array.from({ length: n }, (_, i) => makeChunk(i + 1)),
    embeddings: [],
    kg_entities: [],
    kg_relations: [],
    ops_audit: [],
  });
}

describe("cli / parseExportArgs", () => {
  it("parses --out + --unencrypted", () => {
    const args = parseExportArgs(["--out", "/tmp/a.tgz", "--unencrypted"]);
    assert.equal(args.out, "/tmp/a.tgz");
    assert.equal(args.unencrypted, true);
  });

  it("parses --passphrase-env <ENV>", () => {
    const args = parseExportArgs(["--passphrase-env", "MY_PASS"]);
    assert.equal(args.passphraseEnv, "MY_PASS");
  });

  it("REFUSES --passphrase=value flag (security)", () => {
    assert.throws(() => parseExportArgs(["--passphrase=hunter2"]), /REFUSED/);
  });

  it("REFUSES --passphrase <value> flag (security)", () => {
    assert.throws(() => parseExportArgs(["--passphrase", "hunter2"]), /REFUSED/);
  });

  it("REFUSES -p flag (alias)", () => {
    assert.throws(() => parseExportArgs(["-p", "hunter2"]), /REFUSED/);
  });

  it("parses --project + --since + --until", () => {
    const args = parseExportArgs([
      "--project",
      "nox-mem",
      "--since",
      "2026-01-01",
      "--until",
      "2026-12-31",
    ]);
    assert.equal(args.project, "nox-mem");
    assert.equal(args.since, "2026-01-01");
    assert.equal(args.until, "2026-12-31");
  });

  it("parses --exclude-embeddings", () => {
    const args = parseExportArgs(["--exclude-embeddings"]);
    assert.equal(args.excludeEmbeddings, true);
  });

  it("rejects unknown flags", () => {
    assert.throws(() => parseExportArgs(["--bogus"]), /Unknown flag/);
  });

  it("rejects flags missing required value", () => {
    assert.throws(() => parseExportArgs(["--out"]), /requires a value/);
  });
});

describe("cli / parseImportArgs", () => {
  it("parses positional archive path + --merge", () => {
    const args = parseImportArgs(["/tmp/a.tgz", "--merge"]);
    assert.equal(args.archivePath, "/tmp/a.tgz");
    assert.equal(args.mode, "merge");
  });

  it("parses --replace (mutually exclusive with --merge, last wins)", () => {
    const args = parseImportArgs(["/tmp/a.tgz", "--merge", "--replace"]);
    assert.equal(args.mode, "replace");
  });

  it("parses --dry-run + --verify", () => {
    const args = parseImportArgs(["/tmp/a.tgz", "--dry-run", "--verify"]);
    assert.equal(args.dryRun, true);
    assert.equal(args.verifyOnly, true);
  });

  it("REFUSES --passphrase=value flag", () => {
    assert.throws(
      () => parseImportArgs(["/tmp/a.tgz", "--passphrase=hunter2"]),
      /REFUSED/,
    );
  });

  it("requires positional archive path", () => {
    assert.throws(() => parseImportArgs(["--merge"]), /missing archive path/);
  });

  it("rejects multiple positional args", () => {
    assert.throws(
      () => parseImportArgs(["/tmp/a.tgz", "/tmp/b.tgz"]),
      /Only one positional/,
    );
  });
});

describe("cli / runCliExport end-to-end", () => {
  it("writes encrypted archive when passphrase from env, returns exit 0", async () => {
    let writtenPath = "";
    let writtenBuf: Buffer | null = null;
    const result = await runCliExport(
      ["--out", "/tmp/test.tgz", "--passphrase-env", "MY_PASS"],
      {
        dbReader: dbReader(3),
        writeArchive: async (p, buf) => {
          writtenPath = p;
          writtenBuf = buf;
        },
        env: { MY_PASS: "secret-test" },
        log: () => {},
      },
    );
    assert.equal(result.exitCode, 0);
    assert.equal(writtenPath, "/tmp/test.tgz");
    assert.ok(writtenBuf);
    assert.equal(result.manifest?.encryption.enabled, true);
  });

  it("writes unencrypted archive when --unencrypted + ACK", async () => {
    const result = await runCliExport(
      ["--out", "/tmp/x.tgz", "--unencrypted"],
      {
        dbReader: dbReader(2),
        writeArchive: async () => {},
        env: { NOX_EXPORT_UNENCRYPTED_ACK: "1" },
        isTTY: false,
        log: () => {},
      },
    );
    assert.equal(result.exitCode, 0);
    assert.equal(result.manifest?.encryption.enabled, false);
  });

  it("refuses --unencrypted in non-TTY without ACK", async () => {
    const result = await runCliExport(
      ["--out", "/tmp/x.tgz", "--unencrypted"],
      {
        dbReader: dbReader(2),
        env: {},
        isTTY: false,
        log: () => {},
      },
    );
    assert.equal(result.exitCode, 2);
  });

  it("returns exit 2 when --passphrase-env points to missing env var", async () => {
    const result = await runCliExport(
      ["--out", "/tmp/x.tgz", "--passphrase-env", "MISSING_VAR"],
      {
        dbReader: dbReader(1),
        env: {},
        log: () => {},
      },
    );
    assert.equal(result.exitCode, 2);
  });
});

describe("cli / runCliImport end-to-end", () => {
  it("round-trips through CLI export → CLI import (encrypted)", async () => {
    let archiveBuf: Buffer | null = null;
    const exp = await runCliExport(
      ["--out", "/tmp/rt.tgz", "--passphrase-env", "PASS"],
      {
        dbReader: dbReader(5),
        writeArchive: async (_, buf) => {
          archiveBuf = buf;
        },
        env: { PASS: "rt-secret" },
        log: () => {},
      },
    );
    assert.equal(exp.exitCode, 0);
    assert.ok(archiveBuf);

    const imp = await runCliImport(
      ["/tmp/rt.tgz", "--passphrase-env", "PASS"],
      {
        loadExisting: async () => ({
          chunks: [],
          kg_entities: [],
          kg_relations: [],
          ops_audit: [],
        }),
        currentSchemaVersion: async () => 18,
        readArchive: async () => archiveBuf!,
        env: { PASS: "rt-secret" },
        log: () => {},
      },
    );
    assert.equal(imp.exitCode, 0);
    assert.equal(imp.result?.resolved.chunks.length, 5);
  });

  it("--dry-run does not call persist", async () => {
    let archiveBuf: Buffer | null = null;
    await runCliExport(
      ["--out", "/tmp/dr.tgz", "--unencrypted"],
      {
        dbReader: dbReader(3),
        writeArchive: async (_, buf) => {
          archiveBuf = buf;
        },
        env: { NOX_EXPORT_UNENCRYPTED_ACK: "1" },
        isTTY: false,
        log: () => {},
      },
    );
    let persisted = false;
    const imp = await runCliImport(
      ["/tmp/dr.tgz", "--dry-run"],
      {
        loadExisting: async () => ({
          chunks: [],
          kg_entities: [],
          kg_relations: [],
          ops_audit: [],
        }),
        currentSchemaVersion: async () => 18,
        readArchive: async () => archiveBuf!,
        persist: async () => {
          persisted = true;
        },
        log: () => {},
      },
    );
    assert.equal(imp.exitCode, 0);
    assert.equal(persisted, false);
    assert.equal(imp.result?.applied, false);
    assert.equal(imp.result?.resolved.chunks.length, 3);
  });

  it("--verify does not call persist and resolves no rows", async () => {
    let archiveBuf: Buffer | null = null;
    await runCliExport(
      ["--out", "/tmp/v.tgz", "--unencrypted"],
      {
        dbReader: dbReader(3),
        writeArchive: async (_, buf) => {
          archiveBuf = buf;
        },
        env: { NOX_EXPORT_UNENCRYPTED_ACK: "1" },
        isTTY: false,
        log: () => {},
      },
    );
    let persisted = false;
    const imp = await runCliImport(
      ["/tmp/v.tgz", "--verify"],
      {
        loadExisting: async () => ({
          chunks: [],
          kg_entities: [],
          kg_relations: [],
          ops_audit: [],
        }),
        currentSchemaVersion: async () => 18,
        readArchive: async () => archiveBuf!,
        persist: async () => {
          persisted = true;
        },
        log: () => {},
      },
    );
    assert.equal(imp.exitCode, 0);
    assert.equal(persisted, false);
    assert.equal(imp.result?.resolved.chunks.length, 0);
    // Manifest counts must still be readable
    assert.equal(imp.result?.manifest.counts.chunks, 3);
  });

  it("missing passphrase env causes exit 2", async () => {
    let archiveBuf: Buffer | null = null;
    await runCliExport(
      ["--out", "/tmp/m.tgz", "--passphrase-env", "PASS"],
      {
        dbReader: dbReader(2),
        writeArchive: async (_, buf) => {
          archiveBuf = buf;
        },
        env: { PASS: "set-on-export" },
        log: () => {},
      },
    );
    const imp = await runCliImport(
      ["/tmp/m.tgz", "--passphrase-env", "MISSING_VAR"],
      {
        loadExisting: async () => ({
          chunks: [],
          kg_entities: [],
          kg_relations: [],
          ops_audit: [],
        }),
        currentSchemaVersion: async () => 18,
        readArchive: async () => archiveBuf!,
        env: {},
        log: () => {},
      },
    );
    assert.equal(imp.exitCode, 2);
  });
});
