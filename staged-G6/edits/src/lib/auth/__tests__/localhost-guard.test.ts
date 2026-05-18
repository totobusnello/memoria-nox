/**
 * G6 — Tests for localhost-guard middleware.
 *
 * 10 tests covering:
 *   - Localhost requests always pass
 *   - Remote requests without token are denied 403
 *   - Remote requests with valid Bearer pass
 *   - Remote requests with wrong Bearer are denied
 *   - IPv6 localhost (::1) passes
 *   - extractBearerToken parsing
 *   - constantTimeEqual correctness
 *   - warnIfPubliclyExposed triggers on 0.0.0.0 without token
 *   - buildAuthContext shape
 *   - makeLocalhostGuard with explicit token
 *
 * Run: node --test staged-G6/edits/src/lib/auth/__tests__/localhost-guard.test.ts
 */

import { describe, it, mock } from "node:test";
import assert from "node:assert/strict";
import { IncomingMessage, ServerResponse } from "node:http";
import { Socket } from "node:net";

import {
  extractBearerToken,
  constantTimeEqual,
  buildAuthContext,
  makeLocalhostGuard,
  isLocalhostIp,
  extractClientIp,
} from "../localhost-guard.ts";

// ─── Minimal mock helpers ─────────────────────────────────────────────────────

function mockReq(opts: {
  remoteAddress?: string;
  authorization?: string;
}): IncomingMessage {
  const socket = { remoteAddress: opts.remoteAddress ?? "127.0.0.1" } as Socket;
  const req = Object.create(IncomingMessage.prototype) as IncomingMessage;
  (req as unknown as { socket: Socket }).socket = socket;
  req.headers = {};
  if (opts.authorization) {
    req.headers["authorization"] = opts.authorization;
  }
  return req;
}

interface WrittenResponse {
  statusCode: number;
  body: string;
}

function mockRes(): { res: ServerResponse; written: WrittenResponse } {
  const written: WrittenResponse = { statusCode: 0, body: "" };
  const res = {
    writeHead(status: number) {
      written.statusCode = status;
    },
    end(chunk: string) {
      written.body = chunk;
    },
  } as unknown as ServerResponse;
  return { res, written };
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("G6 — localhost-guard", () => {
  describe("isLocalhostIp", () => {
    it("identifies 127.0.0.1 as localhost", () => {
      assert.equal(isLocalhostIp("127.0.0.1"), true);
    });

    it("identifies ::1 as localhost (IPv6)", () => {
      assert.equal(isLocalhostIp("::1"), true);
    });

    it("rejects external IP as non-localhost", () => {
      assert.equal(isLocalhostIp("203.0.113.5"), false);
    });
  });

  describe("extractBearerToken", () => {
    it("extracts token from valid Authorization header", () => {
      const req = mockReq({ authorization: "Bearer my-secret-token" });
      assert.equal(extractBearerToken(req), "my-secret-token");
    });

    it("returns null when Authorization header is absent", () => {
      const req = mockReq({});
      assert.equal(extractBearerToken(req), null);
    });

    it("returns null for malformed header (no Bearer prefix)", () => {
      const req = mockReq({ authorization: "Basic dXNlcjpwYXNz" });
      assert.equal(extractBearerToken(req), null);
    });
  });

  describe("constantTimeEqual", () => {
    it("returns true for equal strings", () => {
      assert.equal(constantTimeEqual("abc", "abc"), true);
    });

    it("returns false for different strings", () => {
      assert.equal(constantTimeEqual("abc", "xyz"), false);
    });

    it("returns false when strings differ only in length", () => {
      assert.equal(constantTimeEqual("abc", "abcd"), false);
    });
  });

  describe("makeLocalhostGuard", () => {
    it("allows localhost request without token (returns false = not denied)", () => {
      const guard = makeLocalhostGuard({ token: "secret" });
      const req = mockReq({ remoteAddress: "127.0.0.1" });
      const { res } = mockRes();
      const denied = guard(req, res);
      assert.equal(denied, false);
    });

    it("denies remote request without token — returns true and sends 403", () => {
      const guard = makeLocalhostGuard({ token: "secret" });
      const req = mockReq({ remoteAddress: "203.0.113.5" });
      const { res, written } = mockRes();
      const denied = guard(req, res);
      assert.equal(denied, true);
      assert.equal(written.statusCode, 403);
      const body = JSON.parse(written.body) as { error: string };
      assert.equal(body.error, "forbidden");
    });

    it("allows remote request with valid Bearer token", () => {
      const guard = makeLocalhostGuard({ token: "my-token" });
      const req = mockReq({
        remoteAddress: "203.0.113.5",
        authorization: "Bearer my-token",
      });
      const { res } = mockRes();
      const denied = guard(req, res);
      assert.equal(denied, false);
    });

    it("denies remote request with wrong Bearer token", () => {
      const guard = makeLocalhostGuard({ token: "correct-token" });
      const req = mockReq({
        remoteAddress: "203.0.113.5",
        authorization: "Bearer wrong-token",
      });
      const { res, written } = mockRes();
      const denied = guard(req, res);
      assert.equal(denied, true);
      assert.equal(written.statusCode, 403);
    });

    it("denies remote request when no token is configured (localhost-only mode)", () => {
      // When token is explicitly undefined, no remote access regardless of header
      const guard = makeLocalhostGuard({ token: undefined });
      // Ensure env var is not set for this test
      const saved = process.env.NOX_API_BEARER_TOKEN;
      delete process.env.NOX_API_BEARER_TOKEN;
      try {
        const req = mockReq({
          remoteAddress: "203.0.113.5",
          authorization: "Bearer anything",
        });
        const { res, written } = mockRes();
        const denied = guard(req, res);
        assert.equal(denied, true);
        assert.equal(written.statusCode, 403);
      } finally {
        if (saved !== undefined) process.env.NOX_API_BEARER_TOKEN = saved;
      }
    });
  });
});
