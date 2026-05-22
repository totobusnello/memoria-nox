/**
 * Unit tests for NoxMemClient — no real network calls.
 * Run with: node --test src/index.test.js
 */

import { describe, it, beforeEach, mock } from "node:test";
import assert from "node:assert/strict";
import { NoxMemClient, NoxMemError } from "./index.js";

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

function makeResponse(status, body) {
  return {
    status,
    ok: status >= 200 && status < 400,
    json: async () => body,
    text: async () => JSON.stringify(body),
  };
}

function mockFetch(responses) {
  let call = 0;
  return async () => responses[Math.min(call++, responses.length - 1)];
}

// ------------------------------------------------------------------
// Constructor tests
// ------------------------------------------------------------------

describe("NoxMemClient constructor", () => {
  it("uses default base URL", () => {
    const c = new NoxMemClient();
    assert.equal(c.baseUrl, "http://187.77.234.79:18802");
  });

  it("strips trailing slash from baseUrl", () => {
    const c = new NoxMemClient({ baseUrl: "http://localhost:18802/" });
    assert.equal(c.baseUrl, "http://localhost:18802");
  });

  it("accepts custom timeout", () => {
    const c = new NoxMemClient({ timeout: 5000 });
    assert.equal(c.timeout, 5000);
  });
});

// ------------------------------------------------------------------
// URL building
// ------------------------------------------------------------------

describe("NoxMemClient._url", () => {
  it("builds URL with leading slash", () => {
    const c = new NoxMemClient({ baseUrl: "http://example.com:18802" });
    assert.equal(c._url("/api/health"), "http://example.com:18802/api/health");
  });

  it("builds URL without leading slash", () => {
    const c = new NoxMemClient({ baseUrl: "http://example.com:18802" });
    assert.equal(c._url("api/search"), "http://example.com:18802/api/search");
  });
});

// ------------------------------------------------------------------
// Retry logic
// ------------------------------------------------------------------

describe("Retry on 5xx", () => {
  it("retries once on 503 and succeeds on second attempt", async () => {
    const fail = makeResponse(503, { error: "unavailable" });
    const ok = makeResponse(200, { chunksTotal: 100, vectorCoverage: 0.99,
      salienceMode: "shadow", kgEntities: 10, kgRelations: 15, uptime: "1d", indicators: {} });

    let calls = 0;
    const fetchMock = async () => {
      calls++;
      return calls === 1 ? fail : ok;
    };

    const c = new NoxMemClient({ fetch: fetchMock, timeout: 1000 });
    const snap = await c.health();
    assert.equal(snap.chunksTotal, 100);
    assert.equal(calls, 2);
  });

  it("throws NoxMemError after 3 failed attempts", async () => {
    const fail = makeResponse(503, { error: "down" });
    let calls = 0;
    const fetchMock = async () => { calls++; return fail; };

    const c = new NoxMemClient({ fetch: fetchMock, timeout: 1000 });
    await assert.rejects(
      () => c.health(),
      (err) => {
        assert(err instanceof NoxMemError);
        assert.equal(err.statusCode, 503);
        return true;
      }
    );
    assert.equal(calls, 3);
  });

  it("does NOT retry on 4xx", async () => {
    const fail = makeResponse(404, { error: "not found" });
    let calls = 0;
    const fetchMock = async () => { calls++; return fail; };

    const c = new NoxMemClient({ fetch: fetchMock, timeout: 1000 });
    await assert.rejects(() => c.health(), NoxMemError);
    assert.equal(calls, 1);
  });
});

// ------------------------------------------------------------------
// Response shaping
// ------------------------------------------------------------------

describe("search() response shaping", () => {
  it("normalizes camelCase API response", async () => {
    const raw = [
      { id: 1, score: 0.87, sourceFile: "memory/entities/nox.md", snippet: "test chunk",
        section: "compiled", pain: 0.8 }
    ];
    const fetchMock = async () => makeResponse(200, raw);
    const c = new NoxMemClient({ fetch: fetchMock, timeout: 1000 });
    const results = await c.search("test");
    assert.equal(results.length, 1);
    assert.equal(results[0].score, 0.87);
    assert.equal(results[0].section, "compiled");
  });
});

describe("answer() response shaping", () => {
  it("maps API fields correctly", async () => {
    const raw = { answer: "42", citations: [], sessionId: "sess-1", latencyMs: 940 };
    const fetchMock = async () => makeResponse(200, raw);
    const c = new NoxMemClient({ fetch: fetchMock, timeout: 1000 });
    const resp = await c.answer("what is life?");
    assert.equal(resp.answer, "42");
    assert.equal(resp.latencyMs, 940);
    assert.equal(resp.sessionId, "sess-1");
  });
});
