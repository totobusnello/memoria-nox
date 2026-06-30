import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  authorize,
  authEnabled,
  denyResponse,
  type AuthRequest,
} from "../auth.js";

function req(
  headers: Record<string, string> = {},
  query: Record<string, string> = {}
): AuthRequest {
  const lower: Record<string, string> = {};
  for (const k of Object.keys(headers)) lower[k.toLowerCase()] = headers[k]!;
  return { headers: lower, query };
}

describe("T11 — auth", () => {
  it("authEnabled false when env unset", () => {
    assert.equal(authEnabled({} as NodeJS.ProcessEnv), false);
  });

  it("authEnabled true when env set", () => {
    assert.equal(
      authEnabled({ NOX_VIEWER_AUTH_TOKEN: "x" } as NodeJS.ProcessEnv),
      true
    );
  });

  it("authorize ok when no token configured", () => {
    const r = authorize(req(), {} as NodeJS.ProcessEnv);
    assert.equal(r.ok, true);
    assert.equal(r.reason, "no_token_configured");
  });

  it("authorize denies when token required but missing", () => {
    const r = authorize(req(), {
      NOX_VIEWER_AUTH_TOKEN: "secret",
    } as NodeJS.ProcessEnv);
    assert.equal(r.ok, false);
    assert.equal(r.reason, "missing");
  });

  it("authorize accepts matching Bearer header", () => {
    const r = authorize(req({ Authorization: "Bearer secret" }), {
      NOX_VIEWER_AUTH_TOKEN: "secret",
    } as NodeJS.ProcessEnv);
    assert.equal(r.ok, true);
    assert.equal(r.reason, "matched");
  });

  it("authorize accepts matching query token", () => {
    const r = authorize(req({}, { token: "secret" }), {
      NOX_VIEWER_AUTH_TOKEN: "secret",
    } as NodeJS.ProcessEnv);
    assert.equal(r.ok, true);
  });

  it("authorize denies wrong token", () => {
    const r = authorize(req({ Authorization: "Bearer wrong" }), {
      NOX_VIEWER_AUTH_TOKEN: "secret",
    } as NodeJS.ProcessEnv);
    assert.equal(r.ok, false);
    assert.equal(r.reason, "mismatch");
  });

  it("authorize handles different-length tokens safely", () => {
    const r = authorize(req({ Authorization: "Bearer short" }), {
      NOX_VIEWER_AUTH_TOKEN: "much-longer-token",
    } as NodeJS.ProcessEnv);
    assert.equal(r.ok, false);
    assert.equal(r.reason, "mismatch");
  });

  it("denyResponse returns 401 + WWW-Authenticate", () => {
    const d = denyResponse("missing");
    assert.equal(d.status, 401);
    assert.equal(d.headers["WWW-Authenticate"], 'Bearer realm="nox-mem-viewer"');
    const body = JSON.parse(d.body);
    assert.equal(body.error, "unauthorized");
    assert.equal(body.reason, "missing");
  });
});
