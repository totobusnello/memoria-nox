/**
 * src/api/__tests__/cors.test.ts — Unit tests for CORS handler module.
 *
 * Uses node:test (same pattern as A3/A4 retention tests in this repo).
 * Run: node --experimental-vm-modules --loader ts-node/esm \
 *        src/api/__tests__/cors.test.ts
 *
 * Or via package.json test script after deploying to VPS:
 *   npm run test:cors
 */

import { describe, it, before } from "node:test";
import assert from "node:assert/strict";
import type { IncomingMessage, ServerResponse } from "node:http";
import { EventEmitter } from "node:events";

// Import module under test
import {
  isOriginAllowed,
  applyCorsHeaders,
  handlePreflight,
} from "../cors.js";

// ─── Minimal request / response stubs ──────────────────────────────────────

function makeReq(
  method: string,
  origin?: string
): IncomingMessage {
  const req = new EventEmitter() as unknown as IncomingMessage;
  (req as unknown as Record<string, unknown>).method = method;
  (req as unknown as Record<string, unknown>).headers = origin
    ? { origin }
    : {};
  return req;
}

function makeRes(): ServerResponse & {
  _headers: Record<string, string | number>;
  _statusCode: number | null;
  _ended: boolean;
} {
  const headers: Record<string, string | number> = {};
  let statusCode: number | null = null;
  let ended = false;

  const res = {
    _headers: headers,
    _statusCode: statusCode,
    _ended: ended,
    setHeader(name: string, value: string | number) {
      headers[name.toLowerCase()] = value;
    },
    getHeader(name: string) {
      return headers[name.toLowerCase()];
    },
    writeHead(code: number) {
      this._statusCode = code;
    },
    end() {
      this._ended = true;
    },
  };

  return res as unknown as ServerResponse & {
    _headers: Record<string, string | number>;
    _statusCode: number | null;
    _ended: boolean;
  };
}

// ─── Tests ──────────────────────────────────────────────────────────────────

describe("isOriginAllowed", () => {
  it("T01 — Chrome extension 32-char ID is allowed", () => {
    const origin = "chrome-extension://abcdefghijklmnopqrstuvwxyzabcdef";
    assert.equal(isOriginAllowed(origin), true);
  });

  it("T02 — Firefox extension UUID is allowed", () => {
    const origin = "moz-extension://12345678-1234-1234-1234-1234567890ab";
    assert.equal(isOriginAllowed(origin), true);
  });

  it("T03 — Random HTTPS origin is blocked", () => {
    assert.equal(isOriginAllowed("https://example.com"), false);
  });

  it("T04 — localhost HTTPS is blocked (not in default allowlist)", () => {
    assert.equal(isOriginAllowed("https://localhost:3000"), false);
  });

  it("T05 — chrome-extension with wrong ID length (31 chars) is blocked", () => {
    const origin = "chrome-extension://abcdefghijklmnopqrstuvwxyzabcde"; // 31 chars
    assert.equal(isOriginAllowed(origin), false);
  });

  it("T06 — chrome-extension with digits in ID is blocked (only a-z allowed)", () => {
    const origin = "chrome-extension://abcdefghijklmnopqrstuvwxyz123456";
    assert.equal(isOriginAllowed(origin), false);
  });

  it("T07 — extra origin via extraOrigins param is allowed", () => {
    const extra = [/^https:\/\/localhost:\d+$/];
    assert.equal(isOriginAllowed("https://localhost:4000", extra), true);
  });

  it("T08 — extra origin param does NOT bypass other origins", () => {
    const extra = [/^https:\/\/localhost:\d+$/];
    assert.equal(isOriginAllowed("https://evil.com", extra), false);
  });
});

describe("applyCorsHeaders", () => {
  it("T09 — Chrome extension origin sets required CORS headers", () => {
    const origin = "chrome-extension://abcdefghijklmnopqrstuvwxyzabcdef";
    const req = makeReq("GET", origin);
    const res = makeRes();

    applyCorsHeaders(req, res);

    assert.equal(res._headers["access-control-allow-origin"], origin);
    assert.equal(res._headers["vary"], "Origin");
    assert.equal(res._headers["access-control-allow-methods"], "GET, POST, OPTIONS");
    assert.equal(res._headers["access-control-allow-headers"], "Content-Type, Authorization");
    assert.equal(res._headers["access-control-max-age"], "86400");
  });

  it("T10 — Firefox extension origin sets required CORS headers", () => {
    const origin = "moz-extension://12345678-1234-1234-1234-1234567890ab";
    const req = makeReq("POST", origin);
    const res = makeRes();

    applyCorsHeaders(req, res);

    assert.equal(res._headers["access-control-allow-origin"], origin);
    assert.equal(res._headers["vary"], "Origin");
  });

  it("T11 — Unknown origin → no headers set", () => {
    const req = makeReq("GET", "https://evil.com");
    const res = makeRes();

    applyCorsHeaders(req, res);

    assert.equal(res._headers["access-control-allow-origin"], undefined);
    assert.equal(res._headers["vary"], undefined);
  });

  it("T12 — No Origin header → no headers set (non-browser / same-origin request)", () => {
    const req = makeReq("GET", undefined);
    const res = makeRes();

    applyCorsHeaders(req, res);

    assert.equal(res._headers["access-control-allow-origin"], undefined);
  });

  it("T13 — allowCredentials option sets the header", () => {
    const origin = "chrome-extension://abcdefghijklmnopqrstuvwxyzabcdef";
    const req = makeReq("GET", origin);
    const res = makeRes();

    applyCorsHeaders(req, res, { allowCredentials: true });

    assert.equal(res._headers["access-control-allow-credentials"], "true");
  });

  it("T14 — allowCredentials omitted → header absent", () => {
    const origin = "chrome-extension://abcdefghijklmnopqrstuvwxyzabcdef";
    const req = makeReq("GET", origin);
    const res = makeRes();

    applyCorsHeaders(req, res);

    assert.equal(res._headers["access-control-allow-credentials"], undefined);
  });
});

describe("handlePreflight", () => {
  it("T15 — OPTIONS from extension → 204 + headers, returns true", () => {
    const origin = "chrome-extension://abcdefghijklmnopqrstuvwxyzabcdef";
    const req = makeReq("OPTIONS", origin);
    const res = makeRes();

    const handled = handlePreflight(req, res);

    assert.equal(handled, true);
    assert.equal(res._statusCode, 204);
    assert.equal(res._ended, true);
    assert.equal(res._headers["access-control-allow-origin"], origin);
  });

  it("T16 — POST request → returns false, does NOT terminate", () => {
    const origin = "chrome-extension://abcdefghijklmnopqrstuvwxyzabcdef";
    const req = makeReq("POST", origin);
    const res = makeRes();

    const handled = handlePreflight(req, res);

    // Must return false — caller continues routing
    assert.equal(handled, false);
    assert.equal(res._statusCode, null);
    assert.equal(res._ended, false);
  });

  it("T17 — OPTIONS from unknown origin → 204 but no CORS headers", () => {
    // Preflight always responds 204 (so browser doesn't hang), but without
    // ACAO header the browser will still block the actual request.
    const req = makeReq("OPTIONS", "https://evil.com");
    const res = makeRes();

    const handled = handlePreflight(req, res);

    assert.equal(handled, true);
    assert.equal(res._statusCode, 204);
    assert.equal(res._headers["access-control-allow-origin"], undefined);
  });

  it("T18 — GET from extension → returns false (not OPTIONS)", () => {
    const origin = "chrome-extension://abcdefghijklmnopqrstuvwxyzabcdef";
    const req = makeReq("GET", origin);
    const res = makeRes();

    const handled = handlePreflight(req, res);

    assert.equal(handled, false);
  });
});
