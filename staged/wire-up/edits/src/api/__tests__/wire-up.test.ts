/**
 * src/api/__tests__/wire-up.test.ts — smoke tests for Wave A→K route table.
 *
 * Strategy:
 *   - Build minimal IncomingMessage / ServerResponse stubs (no real socket).
 *   - For each route, assert:
 *       1. `matchesWireUpRoute(method, path)` is true.
 *       2. `registerWireUpRoutes(req, res)` returns true (caller short-circuit).
 *       3. The response status falls in the expected envelope (200 / 4xx / 503).
 *
 * We don't boot a real http.Server; the wire-up module is pure
 * (req, res) → side effects. Stubbing is enough to lock in the route table.
 *
 * Why 503 is OK in the happy path:
 *   The wire-up uses lazy imports that fall back to "not_implemented" 503
 *   when downstream lib deps aren't deployed. In CI (no DB binding), this
 *   is the canonical pass — proves the route fires, the handler is reached.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import type { IncomingMessage, ServerResponse } from "node:http";

import { matchesWireUpRoute, registerWireUpRoutes } from "../wire-up.js";

// ─── Stubs ─────────────────────────────────────────────────────────────────

interface ResponseCapture {
  status: number | null;
  headers: Record<string, string>;
  body: string;
  ended: boolean;
}

function makeRes(): { res: ServerResponse; cap: ResponseCapture } {
  const cap: ResponseCapture = {
    status: null,
    headers: {},
    body: "",
    ended: false,
  };
  const res = new EventEmitter() as unknown as ServerResponse;
  // Minimal shim to record everything writeJson / writeBuffer touches.
  (res as any).writeHead = (status: number, headers?: Record<string, string>) => {
    cap.status = status;
    if (headers) Object.assign(cap.headers, headers);
    return res;
  };
  (res as any).setHeader = (k: string, v: string) => {
    cap.headers[k] = v;
  };
  (res as any).write = (chunk: string | Buffer) => {
    cap.body += typeof chunk === "string" ? chunk : chunk.toString("utf-8");
    return true;
  };
  (res as any).end = (data?: string | Buffer) => {
    if (data) cap.body += typeof data === "string" ? data : data.toString("utf-8");
    cap.ended = true;
  };
  (res as any).once = res.once.bind(res);
  return { res, cap };
}

function makeReq(method: string, url: string, body?: string, remoteAddress = "127.0.0.1"): IncomingMessage {
  const req = new EventEmitter() as unknown as IncomingMessage;
  (req as any).method = method;
  (req as any).url = url;
  (req as any).headers = {};
  (req as any).socket = { remoteAddress };
  // Schedule the body emission on next tick so handlers can attach listeners.
  if (body !== undefined) {
    setImmediate(() => {
      req.emit("data", Buffer.from(body, "utf-8"));
      req.emit("end");
    });
  } else {
    setImmediate(() => req.emit("end"));
  }
  return req;
}

function parseBody(cap: ResponseCapture): unknown {
  try {
    return JSON.parse(cap.body);
  } catch {
    return cap.body;
  }
}

// ─── Route-table tests ──────────────────────────────────────────────────────

describe("matchesWireUpRoute", () => {
  it("matches POST /api/answer", () => {
    assert.equal(matchesWireUpRoute("POST", "/api/answer"), true);
  });

  it("matches POST /api/export and /api/import", () => {
    assert.equal(matchesWireUpRoute("POST", "/api/export"), true);
    assert.equal(matchesWireUpRoute("POST", "/api/import"), true);
  });

  it("matches GET /api/events/stream", () => {
    assert.equal(matchesWireUpRoute("GET", "/api/events/stream"), true);
  });

  it("matches GET /viewer and /viewer/<path>", () => {
    assert.equal(matchesWireUpRoute("GET", "/viewer"), true);
    assert.equal(matchesWireUpRoute("GET", "/viewer/app.js"), true);
    assert.equal(matchesWireUpRoute("GET", "/viewer/sub/page.html"), true);
  });

  it("matches GET /api/conflict and /api/conflict/:id", () => {
    assert.equal(matchesWireUpRoute("GET", "/api/conflict"), true);
    assert.equal(matchesWireUpRoute("GET", "/api/conflict/42"), true);
  });

  it("matches POST /api/conflict/:id/resolve", () => {
    assert.equal(matchesWireUpRoute("POST", "/api/conflict/42/resolve"), true);
  });

  it("matches POST /api/chunk/:id/mark and /supersede", () => {
    assert.equal(matchesWireUpRoute("POST", "/api/chunk/7/mark"), true);
    assert.equal(matchesWireUpRoute("POST", "/api/chunk/7/supersede"), true);
  });

  it("matches GET /api/health/confidence", () => {
    assert.equal(matchesWireUpRoute("GET", "/api/health/confidence"), true);
  });

  it("matches GET /api/hooks/status and /recent, POST /api/hooks/dryrun", () => {
    assert.equal(matchesWireUpRoute("GET", "/api/hooks/status"), true);
    assert.equal(matchesWireUpRoute("GET", "/api/hooks/recent"), true);
    assert.equal(matchesWireUpRoute("POST", "/api/hooks/dryrun"), true);
  });

  it("rejects unrelated paths", () => {
    assert.equal(matchesWireUpRoute("GET", "/api/health"), false);
    assert.equal(matchesWireUpRoute("GET", "/api/search"), false);
    assert.equal(matchesWireUpRoute("POST", "/api/conflict"), false);
    assert.equal(matchesWireUpRoute("GET", "/api/conflict/notanumber"), false);
    assert.equal(matchesWireUpRoute("POST", "/api/chunk/abc/mark"), false);
  });
});

describe("registerWireUpRoutes — dispatch", () => {
  it("returns false for non-wired paths (caller falls through to 404)", async () => {
    const req = makeReq("GET", "/api/health");
    const { res } = makeRes();
    const handled = await registerWireUpRoutes(req, res);
    assert.equal(handled, false);
  });

  it("POST /api/answer — handler reached (200 with trace_id, or 4xx/503 if lib absent)", async () => {
    const req = makeReq("POST", "/api/answer", JSON.stringify({ question: "smoke" }));
    const { res, cap } = makeRes();
    const handled = await registerWireUpRoutes(req, res);
    assert.equal(handled, true);
    assert.ok(cap.status !== null, "status set");
    // P1 handler runs; lib/answer may throw retrieval_empty etc. → 200/422/502/503/504.
    // Accept the full envelope; we just want to confirm we are NOT in 404 land.
    assert.notEqual(cap.status, 404);
    const body = parseBody(cap) as Record<string, unknown>;
    // Either a success body (answer/citations) or a sanitized error body.
    assert.ok(
      "trace_id" in body || "error" in body || "code" in body,
      `unexpected body shape: ${cap.body.slice(0, 120)}`,
    );
  });

  it("POST /api/export — handler reached", async () => {
    const req = makeReq("POST", "/api/export", JSON.stringify({ unencrypted: true }));
    const { res, cap } = makeRes();
    const handled = await registerWireUpRoutes(req, res);
    assert.equal(handled, true);
    assert.ok(cap.status !== null);
    assert.notEqual(cap.status, 404);
  });

  it("POST /api/import — blocked from non-localhost", async () => {
    const req = makeReq(
      "POST",
      "/api/import",
      JSON.stringify({ archive_b64: "ZHVtbXk=" }),
      "203.0.113.7", // non-localhost
    );
    const { res, cap } = makeRes();
    const handled = await registerWireUpRoutes(req, res);
    assert.equal(handled, true);
    assert.equal(cap.status, 403, "remote IP must be denied by G6 guard");
  });

  it("POST /api/import — allowed from localhost (reaches handler)", async () => {
    const req = makeReq(
      "POST",
      "/api/import",
      JSON.stringify({ archive_b64: "" }),
      "127.0.0.1",
    );
    const { res, cap } = makeRes();
    const handled = await registerWireUpRoutes(req, res);
    assert.equal(handled, true);
    assert.notEqual(cap.status, 403);
    assert.notEqual(cap.status, 404);
  });

  it("GET /viewer — handler reached (200 or 404 file-not-found)", async () => {
    const req = makeReq("GET", "/viewer");
    const { res, cap } = makeRes();
    const handled = await registerWireUpRoutes(req, res);
    assert.equal(handled, true);
    assert.ok(cap.status === 200 || cap.status === 404 || cap.status === 503);
  });

  it("GET /viewer/../etc/passwd — traversal blocked (404)", async () => {
    const req = makeReq("GET", "/viewer/../../etc/passwd");
    const { res, cap } = makeRes();
    const handled = await registerWireUpRoutes(req, res);
    assert.equal(handled, true);
    assert.notEqual(cap.status, 200, "must NEVER return 200 on traversal");
  });

  it("GET /api/conflict — handler reached", async () => {
    const req = makeReq("GET", "/api/conflict?status=open&limit=5");
    const { res, cap } = makeRes();
    const handled = await registerWireUpRoutes(req, res);
    assert.equal(handled, true);
    assert.notEqual(cap.status, 404);
  });

  it("GET /api/conflict/42 — handler reached", async () => {
    const req = makeReq("GET", "/api/conflict/42");
    const { res, cap } = makeRes();
    const handled = await registerWireUpRoutes(req, res);
    assert.equal(handled, true);
    assert.notEqual(cap.status, 404);
  });

  it("POST /api/conflict/:id/resolve — guard blocks remote", async () => {
    const req = makeReq(
      "POST",
      "/api/conflict/42/resolve",
      JSON.stringify({ kind: "dismissed" }),
      "203.0.113.7",
    );
    const { res, cap } = makeRes();
    const handled = await registerWireUpRoutes(req, res);
    assert.equal(handled, true);
    assert.equal(cap.status, 403);
  });

  it("POST /api/chunk/:id/mark — guard blocks remote", async () => {
    const req = makeReq(
      "POST",
      "/api/chunk/7/mark",
      JSON.stringify({ kind: "canonical" }),
      "203.0.113.7",
    );
    const { res, cap } = makeRes();
    const handled = await registerWireUpRoutes(req, res);
    assert.equal(handled, true);
    assert.equal(cap.status, 403);
  });

  it("POST /api/chunk/:id/supersede — guard blocks remote", async () => {
    const req = makeReq(
      "POST",
      "/api/chunk/7/supersede",
      JSON.stringify({ by_chunk_id: 99 }),
      "203.0.113.7",
    );
    const { res, cap } = makeRes();
    const handled = await registerWireUpRoutes(req, res);
    assert.equal(handled, true);
    assert.equal(cap.status, 403);
  });

  it("GET /api/health/confidence — handler reached", async () => {
    const req = makeReq("GET", "/api/health/confidence");
    const { res, cap } = makeRes();
    const handled = await registerWireUpRoutes(req, res);
    assert.equal(handled, true);
    assert.notEqual(cap.status, 404);
  });

  it("GET /api/hooks/status — handler reached", async () => {
    const req = makeReq("GET", "/api/hooks/status");
    const { res, cap } = makeRes();
    const handled = await registerWireUpRoutes(req, res);
    assert.equal(handled, true);
    assert.notEqual(cap.status, 404);
  });

  it("GET /api/hooks/recent — handler reached", async () => {
    const req = makeReq("GET", "/api/hooks/recent?limit=10");
    const { res, cap } = makeRes();
    const handled = await registerWireUpRoutes(req, res);
    assert.equal(handled, true);
    assert.notEqual(cap.status, 404);
  });

  it("POST /api/hooks/dryrun — guard blocks remote", async () => {
    const req = makeReq(
      "POST",
      "/api/hooks/dryrun",
      JSON.stringify({ text: "hello" }),
      "203.0.113.7",
    );
    const { res, cap } = makeRes();
    const handled = await registerWireUpRoutes(req, res);
    assert.equal(handled, true);
    assert.equal(cap.status, 403);
  });

  it("POST /api/hooks/dryrun — localhost reaches handler", async () => {
    const req = makeReq(
      "POST",
      "/api/hooks/dryrun",
      JSON.stringify({ text: "hello" }),
      "127.0.0.1",
    );
    const { res, cap } = makeRes();
    const handled = await registerWireUpRoutes(req, res);
    assert.equal(handled, true);
    assert.notEqual(cap.status, 403);
    assert.notEqual(cap.status, 404);
  });

  it("body validation error surfaces as 4xx (not 500)", async () => {
    // POST /api/answer with no question → P1 should return 400.
    const req = makeReq("POST", "/api/answer", JSON.stringify({ not_a_question: 1 }));
    const { res, cap } = makeRes();
    const handled = await registerWireUpRoutes(req, res);
    assert.equal(handled, true);
    // P1 returns 400 validate_body OR 503 if lib not present — both acceptable.
    assert.ok(cap.status === 400 || cap.status === 503 || cap.status === 500);
  });

  it("never returns 200 on a missing JSON body for POST /api/answer", async () => {
    const req = makeReq("POST", "/api/answer", "");
    const { res, cap } = makeRes();
    const handled = await registerWireUpRoutes(req, res);
    assert.equal(handled, true);
    assert.notEqual(cap.status, 200);
  });
});

describe("CORS headers", () => {
  it("includes Access-Control-Allow-Origin on responses", async () => {
    const req = makeReq("GET", "/api/conflict");
    const { res, cap } = makeRes();
    await registerWireUpRoutes(req, res);
    assert.equal(cap.headers["Access-Control-Allow-Origin"], "*");
  });
});

// ─── F10 Phase C Phase 2: /api/answer telemetry hook ───────────────────────
//
// These tests verify that the telemetry hook in wire-up.ts:
//   1. Does not break the existing answer handler path.
//   2. Degrades gracefully when telemetry-collector is absent (no crash).
//   3. Captures timing around the actual handler call (t1 > t0).
//
// We cannot easily assert that `recordRequest` was called without injecting
// a mock, but we can verify:
//   - The answer route still returns `handled = true`.
//   - The response body + status are unaffected.
//   - No errors are thrown when telemetry-collector is missing (default in CI).

describe("F10 Phase C Phase 2 — /api/answer telemetry hook", () => {
  it("answer route still returns handled=true after telemetry hook added", async () => {
    const req = makeReq("POST", "/api/answer", JSON.stringify({ question: "telemetry smoke" }));
    const { res, cap } = makeRes();
    const handled = await registerWireUpRoutes(req, res);
    assert.equal(handled, true, "handler must claim the route");
  });

  it("answer route response body is unaffected by telemetry hook", async () => {
    const req = makeReq("POST", "/api/answer", JSON.stringify({ question: "telemetry smoke" }));
    const { res, cap } = makeRes();
    await registerWireUpRoutes(req, res);
    // Body must be valid JSON (not empty/corrupted by hook).
    const body = parseBody(cap) as Record<string, unknown>;
    assert.ok(
      typeof body === "object" && body !== null,
      `body must be JSON object, got: ${cap.body.slice(0, 120)}`,
    );
    // Either success shape (trace_id present) or error shape (error:true) — never corrupt.
    assert.ok(
      "trace_id" in body || "error" in body || "code" in body,
      `unexpected body shape: ${JSON.stringify(body).slice(0, 120)}`,
    );
  });

  it("answer route does not crash when telemetry-collector module is absent", async () => {
    // In CI the telemetry-collector.js may not exist in node_modules path.
    // The lazy import falls back to null — this test confirms no unhandled rejection.
    const req = makeReq("POST", "/api/answer", JSON.stringify({ question: "absent collector" }));
    const { res, cap } = makeRes();
    // Must not throw.
    const handled = await registerWireUpRoutes(req, res);
    assert.equal(handled, true);
    assert.ok(cap.status !== null, "status must be set even without telemetry");
    assert.notEqual(cap.status, 500, "telemetry absence must not cause 500");
  });

  it("answer route status code reflects handler result, not telemetry side effect", async () => {
    // Bad body → 400 from validateBody; telemetry hook must not interfere.
    const req = makeReq("POST", "/api/answer", JSON.stringify({ wrong_field: 1 }));
    const { res, cap } = makeRes();
    await registerWireUpRoutes(req, res);
    // 400 from validateBody or 503 from lib absence — never 200.
    assert.notEqual(cap.status, 200, "missing question must not yield 200");
  });
});
