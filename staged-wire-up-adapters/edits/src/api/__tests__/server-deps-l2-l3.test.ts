/**
 * Tests for `src/api/server-deps-l2-l3.ts`.
 */

import { describe, it, beforeEach } from "node:test";
import assert from "node:assert/strict";
import {
  getConflictDb,
  ensureConflictDb,
  __setConflictDbForTests,
  resetConflictDbForTests,
  getConfidenceDb,
  ensureConfidenceDb,
  __setConfidenceDbForTests,
  resetConfidenceDbForTests,
  handleHealthConfidence,
  probeSchemaReadiness,
} from "../server-deps-l2-l3.js";
import {
  __setDbFactoryForTests,
  resetDepsRegistryForTests,
} from "../../lib/deps/deps-registry.js";

beforeEach(() => {
  resetDepsRegistryForTests();
  resetConflictDbForTests();
  resetConfidenceDbForTests();
});

// ─── L2: conflict db singleton ──────────────────────────────────────────────

describe("L2: getConflictDb", () => {
  it("returns null when no DB factory and no override", () => {
    __setDbFactoryForTests(() => null);
    const db = getConflictDb();
    assert.equal(db, null);
  });

  it("returns the override DB when set", () => {
    const fake = { tag: "conflict-fake" };
    __setConflictDbForTests(fake as any);
    assert.deepEqual(getConflictDb(), fake);
  });

  it("ensureConflictDb resolves async and caches", async () => {
    let calls = 0;
    __setDbFactoryForTests(() => {
      calls += 1;
      return { tag: "lazy" } as any;
    });
    const db1 = await ensureConflictDb();
    const db2 = await ensureConflictDb();
    assert.deepEqual(db1, { tag: "lazy" });
    assert.deepEqual(db2, { tag: "lazy" });
    assert.equal(calls, 1);
  });

  it("__setConflictDbForTests + reset round-trip", () => {
    __setConflictDbForTests({ tag: "x" } as any);
    assert.deepEqual(getConflictDb(), { tag: "x" });
    resetConflictDbForTests();
    __setDbFactoryForTests(() => null);
    assert.equal(getConflictDb(), null);
  });

  it("getConflictDb is sync (callable without await)", () => {
    __setConflictDbForTests({ tag: "sync" } as any);
    const result = getConflictDb();
    // Cannot be a Promise; wire-up.ts depends on sync access.
    assert.notEqual(typeof (result as any)?.then, "function");
  });
});

// ─── L3: confidence db singleton ────────────────────────────────────────────

describe("L3: getConfidenceDb", () => {
  it("returns null when no DB factory and no override", () => {
    __setDbFactoryForTests(() => null);
    assert.equal(getConfidenceDb(), null);
  });

  it("returns the override DB when set", () => {
    __setConfidenceDbForTests({ tag: "confidence-fake" } as any);
    assert.deepEqual(getConfidenceDb(), { tag: "confidence-fake" });
  });

  it("ensureConfidenceDb resolves async and caches", async () => {
    let calls = 0;
    __setDbFactoryForTests(() => {
      calls += 1;
      return { tag: "lazy" } as any;
    });
    await ensureConfidenceDb();
    await ensureConfidenceDb();
    assert.equal(calls, 1);
  });

  it("L2 and L3 share the same underlying DB connection", async () => {
    const handle = { tag: "shared" };
    __setDbFactoryForTests(() => handle as any);
    const l2 = await ensureConflictDb();
    const l3 = await ensureConfidenceDb();
    assert.deepEqual(l2, handle);
    assert.deepEqual(l3, handle);
    assert.strictEqual(l2, l3);
  });
});

// ─── L3 health-confidence adapter ───────────────────────────────────────────

describe("L3 handleHealthConfidence", () => {
  it("returns 503 when DB is unavailable", async () => {
    __setDbFactoryForTests(() => null);
    const out = await handleHealthConfidence();
    assert.equal(out.status, 503);
    const body = out.body as Record<string, unknown>;
    assert.equal(body["error"], "not_implemented");
  });

  it("returns 503 when health-confidence module is not deployed", async () => {
    // DB exists but staged-L3 health-confidence.ts isn't co-located in the
    // staged-wire-up-adapters tree — dynamic import fails.
    __setDbFactoryForTests(() => ({ tag: "stub" }) as any);
    const out = await handleHealthConfidence();
    // Without the staged-L3 module in cwd, expect 503.
    assert.equal(out.status, 503);
  });
});

// ─── Schema readiness probe ─────────────────────────────────────────────────

describe("probeSchemaReadiness", () => {
  it("reports both pillars not ready when DB is null", async () => {
    __setDbFactoryForTests(() => null);
    const out = await probeSchemaReadiness();
    assert.equal(out.l2_ready, false);
    assert.equal(out.l3_ready, false);
    assert.equal(out.details.schema_version, 0);
  });

  it("reports L2 ready when conflict_audit exists", async () => {
    const fake = {
      prepare(sql: string) {
        return {
          get<T = unknown>(): T | undefined {
            if (sql.includes("sqlite_master") && sql.includes("conflict_audit")) {
              return { name: "conflict_audit" } as T;
            }
            if (sql.includes("PRAGMA user_version")) {
              return { user_version: 19 } as T;
            }
            return undefined;
          },
          all<T = unknown>(): T[] {
            return [] as T[];
          },
          run() {
            return { changes: 0, lastInsertRowid: 0 };
          },
        };
      },
      exec() {},
    };
    __setDbFactoryForTests(() => fake as any);
    const out = await probeSchemaReadiness();
    assert.equal(out.l2_ready, true);
  });

  it("reports L3 ready when chunks has confidence + provenance_kind + superseded_by", async () => {
    const fake = {
      prepare(sql: string) {
        return {
          get<T = unknown>(): T | undefined {
            if (sql.includes("PRAGMA user_version")) return { user_version: 19 } as T;
            return undefined;
          },
          all<T = unknown>(): T[] {
            if (sql.includes("PRAGMA table_info")) {
              return [
                { name: "id" },
                { name: "content" },
                { name: "confidence" },
                { name: "provenance_kind" },
                { name: "superseded_by" },
              ] as T[];
            }
            return [] as T[];
          },
          run() {
            return { changes: 0, lastInsertRowid: 0 };
          },
        };
      },
      exec() {},
    };
    __setDbFactoryForTests(() => fake as any);
    const out = await probeSchemaReadiness();
    assert.equal(out.l3_ready, true);
    assert.equal(out.details.schema_version, 19);
  });

  it("reports L3 not ready when columns missing", async () => {
    const fake = {
      prepare(_sql: string) {
        return {
          get() {
            return undefined;
          },
          all() {
            return [{ name: "id" }, { name: "content" }];
          },
          run() {
            return { changes: 0, lastInsertRowid: 0 };
          },
        };
      },
      exec() {},
    };
    __setDbFactoryForTests(() => fake as any);
    const out = await probeSchemaReadiness();
    assert.equal(out.l3_ready, false);
    assert.equal(out.details.has_confidence_col, false);
  });
});
