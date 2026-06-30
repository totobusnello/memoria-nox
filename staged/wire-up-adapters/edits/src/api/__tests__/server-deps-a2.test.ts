/**
 * Tests for `src/api/server-deps-a2.ts` + `src/lib/archive/server-deps.ts`.
 */

import { describe, it, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import type { ServerResponse } from "node:http";
import {
  buildExportDeps,
  buildImportDeps,
} from "../../lib/archive/server-deps.js";
import {
  writeExportResponse,
  parseMultipartFirstFile,
  readRequestBodyBuffer,
} from "../server-deps-a2.js";
import {
  __setDbFactoryForTests,
  resetDepsRegistryForTests,
} from "../../lib/deps/deps-registry.js";

// ─── Fake DB ────────────────────────────────────────────────────────────────

function makeFakeDb(state: Record<string, unknown[]>) {
  return {
    prepare(sql: string) {
      return {
        run() {
          return { changes: 1, lastInsertRowid: 1 };
        },
        get<T = unknown>(): T | undefined {
          if (sql.includes("PRAGMA user_version")) {
            return { user_version: 19 } as T;
          }
          return undefined;
        },
        all<T = unknown>(): T[] {
          if (sql.includes("FROM chunks")) return (state["chunks"] as T[]) ?? [];
          if (sql.includes("FROM kg_entities"))
            return (state["kg_entities"] as T[]) ?? [];
          if (sql.includes("FROM kg_relations"))
            return (state["kg_relations"] as T[]) ?? [];
          if (sql.includes("FROM ops_audit"))
            return (state["ops_audit"] as T[]) ?? [];
          if (sql.includes("vec_chunk_map")) return [];
          return [];
        },
      };
    },
    exec() {},
    transaction(fn: any) {
      return (...args: any[]) => fn(...args);
    },
  };
}

// ─── Fake ServerResponse ────────────────────────────────────────────────────

function makeRes(): { res: ServerResponse; sent: { status?: number; headers?: any; body: Buffer } } {
  const sent = { status: undefined as number | undefined, headers: undefined as any, body: Buffer.alloc(0) };
  const res = new EventEmitter() as unknown as ServerResponse;
  (res as any).writeHead = (status: number, headers: any) => {
    sent.status = status;
    sent.headers = headers;
    return res;
  };
  (res as any).write = (chunk: Buffer | string) => {
    sent.body = Buffer.concat([sent.body, typeof chunk === "string" ? Buffer.from(chunk) : chunk]);
    return true;
  };
  (res as any).end = (chunk?: Buffer | string) => {
    if (chunk) {
      sent.body = Buffer.concat([sent.body, typeof chunk === "string" ? Buffer.from(chunk) : chunk]);
    }
  };
  (res as any).once = res.once.bind(res);
  return { res, sent };
}

beforeEach(() => {
  resetDepsRegistryForTests();
});

describe("server-deps-a2", () => {
  it("buildExportDeps returns dbReader closure", async () => {
    __setDbFactoryForTests(() => null);
    const deps = await buildExportDeps();
    assert.equal(typeof deps.dbReader, "function");
  });

  it("dbReader returns empty corpus when DB is null", async () => {
    __setDbFactoryForTests(() => null);
    const deps = await buildExportDeps();
    const corpus = await deps.dbReader();
    assert.equal(corpus.chunks.length, 0);
    assert.equal(corpus.kg_entities?.length ?? 0, 0);
  });

  it("dbReader pulls chunks from real DB shape", async () => {
    const fake = makeFakeDb({
      chunks: [
        {
          id: 1,
          content: "hello",
          content_hash: "abc",
          source_path: null,
          source_kind: null,
          project: null,
          created_at: "2026-05-18",
          updated_at: null,
          retention_days: 90,
          pain: 0.2,
          section: null,
          section_boost: null,
          metadata_json: null,
        },
      ],
    });
    __setDbFactoryForTests(() => fake as any);
    const deps = await buildExportDeps();
    const corpus = await deps.dbReader();
    assert.equal(corpus.chunks.length, 1);
    assert.equal(corpus.chunks[0]!.content, "hello");
    assert.equal(corpus.schema_version, 19);
  });

  it("buildImportDeps exposes loadExisting + currentSchemaVersion", async () => {
    const fake = makeFakeDb({ chunks: [{ id: 1, content: "x" }] as any });
    __setDbFactoryForTests(() => fake as any);
    const deps = await buildImportDeps();
    const existing = await deps.loadExisting();
    assert.ok(Array.isArray(existing.chunks));
    const v = await deps.currentSchemaVersion();
    assert.equal(v, 19);
  });

  it("buildImportDeps.persist throws when DB is null", async () => {
    __setDbFactoryForTests(() => null);
    const deps = await buildImportDeps();
    assert.equal(typeof deps.persist, "function");
    await assert.rejects(
      () =>
        deps.persist!({
          chunks: [],
          kg_entities: [],
          kg_relations: [],
          ops_audit: [],
          embeddings: new Map(),
        }),
      /DB unavailable/,
    );
  });

  it("writeExportResponse single-shot for small payload", async () => {
    const { res, sent } = makeRes();
    const buf = Buffer.from("hello world");
    await writeExportResponse(res, buf, {
      "Content-Type": "application/gzip",
      "Content-Length": String(buf.length),
    });
    assert.equal(sent.status, 200);
    assert.equal(sent.body.toString(), "hello world");
  });

  it("writeExportResponse uses chunked for large payload", async () => {
    const { res, sent } = makeRes();
    const buf = Buffer.alloc(3 * 1024 * 1024, 0x41); // 3 MiB of 'A'
    await writeExportResponse(
      res,
      buf,
      { "Content-Type": "application/gzip", "Content-Length": String(buf.length) },
      1024 * 1024, // 1 MiB threshold
    );
    assert.equal(sent.status, 200);
    assert.equal(sent.headers["Transfer-Encoding"], "chunked");
    assert.equal(sent.headers["Content-Length"], undefined);
    assert.equal(sent.body.length, buf.length);
  });

  it("parseMultipartFirstFile parses a single file part", () => {
    const boundary = "----X";
    const body = Buffer.concat([
      Buffer.from(`--${boundary}\r\n`),
      Buffer.from(
        `Content-Disposition: form-data; name="archive"; filename="x.tgz"\r\n`,
      ),
      Buffer.from(`Content-Type: application/gzip\r\n\r\n`),
      Buffer.from("BINARY-PAYLOAD"),
      Buffer.from(`\r\n--${boundary}--\r\n`),
    ]);
    const file = parseMultipartFirstFile(
      body,
      `multipart/form-data; boundary=${boundary}`,
    );
    assert.ok(file);
    assert.equal(file!.name, "archive");
    assert.equal(file!.filename, "x.tgz");
    assert.equal(file!.content.toString(), "BINARY-PAYLOAD");
  });

  it("parseMultipartFirstFile returns null for non-multipart content type", () => {
    const file = parseMultipartFirstFile(Buffer.from("x"), "application/json");
    assert.equal(file, null);
  });

  it("readRequestBodyBuffer collects binary-safe chunks", async () => {
    const req = new EventEmitter() as any;
    setImmediate(() => {
      req.emit("data", Buffer.from([0x00, 0x01, 0x02]));
      req.emit("data", Buffer.from([0xff, 0xfe]));
      req.emit("end");
    });
    const buf = await readRequestBodyBuffer(req);
    assert.equal(buf.length, 5);
    assert.equal(buf[0], 0x00);
    assert.equal(buf[4], 0xfe);
  });

  it("readRequestBodyBuffer rejects oversize payload", async () => {
    const req = new EventEmitter() as any;
    (req as any).destroy = () => {};
    setImmediate(() => {
      req.emit("data", Buffer.alloc(100));
    });
    await assert.rejects(() => readRequestBodyBuffer(req, 10), /Payload too large/);
  });
});
