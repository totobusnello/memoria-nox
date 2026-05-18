/**
 * G12 — safeErrorMessage tests.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import {
  safeErrorMessage,
  buildSafeErrorBody,
  checkErrorPassthroughAtBoot,
} from "../safe-error-message.js";
import { safeError500, safeConflict409, safeMark500 } from "../error-leak-fix.js";

// ── stripping ───────────────────────────────────────────────────────────────

describe("safeErrorMessage — path stripping", () => {
  it("strips /Users/... with line:col suffix", () => {
    const { message } = safeErrorMessage(
      new Error("SQLITE_ERROR at /Users/lab/Claude/Projetos/memoria-nox/db.ts:42:15"),
    );
    assert.equal(message.includes("/Users"), false);
    assert.equal(message.includes("<path>"), true);
  });

  it("strips /root/... (linux prod)", () => {
    const { message } = safeErrorMessage(
      new Error("ENOENT: no such file '/root/.openclaw/workspace/tools/nox-mem/foo.db'"),
    );
    assert.equal(message.includes("/root"), false);
  });

  it("strips /var, /opt, /tmp, /home", () => {
    for (const p of ["/var/lib/foo", "/opt/nox/bar", "/tmp/x.db", "/home/u/y.db"]) {
      const { message } = safeErrorMessage(new Error(`failed at ${p}`));
      assert.equal(message.includes(p), false, `should strip ${p}`);
    }
  });
});

describe("safeErrorMessage — DB / secret stripping", () => {
  it("strips sqlite:// connection strings", () => {
    const { message } = safeErrorMessage(
      new Error("Connection failed: sqlite:///var/lib/foo.db"),
    );
    assert.equal(message.includes("<dburl>") || message.includes("<path>"), true);
    assert.equal(message.includes("sqlite:///var"), false);
  });

  it("strips ENV=value patterns", () => {
    // gitleaks-safe fixture: obviously-synthetic test token built from
    // joined non-secret tokens. Verifies the regex matches ENV=value.
    const fixtureToken = ["EXAMPLE", "PLACEHOLDER", "DUMMY"].join("_");
    const { message } = safeErrorMessage(
      new Error(`config error NOX_API_TOKEN=${fixtureToken} not accepted`),
    );
    assert.equal(message.includes(fixtureToken), false);
    assert.equal(message.includes("NOX_API_TOKEN=<redacted>"), true);
  });

  it("strips Bearer tokens", () => {
    const { message } = safeErrorMessage(
      new Error("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.abc.def failed"),
    );
    assert.equal(message.includes("eyJhbGci"), false);
    assert.match(message, /Bearer <redacted>/);
  });

  it("strips long opaque tokens (32+ chars)", () => {
    const { message } = safeErrorMessage(
      new Error("token aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa invalid"),
    );
    assert.match(message, /<token>/);
  });
});

describe("safeErrorMessage — fallback + cap", () => {
  it("returns fallback when stripping leaves empty", () => {
    const { message } = safeErrorMessage(
      new Error("/Users/lab/foo/bar.ts:1:1"),
    );
    // After stripping, only <path> remains → fallback kicks in.
    assert.equal(message, "internal_error");
  });

  it("respects custom fallback", () => {
    const { message } = safeErrorMessage(new Error("/root/x"), { fallback: "boom" });
    assert.equal(message, "boom");
  });

  it("caps to maxLength with ellipsis", () => {
    // Use a stripping-resistant payload: natural-language words separated by
    // spaces, none long enough to match <token>. Verifies the maxLength cap
    // rather than stripping behavior.
    const longMsg = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega ".repeat(5);
    const { message } = safeErrorMessage(new Error(longMsg), { maxLength: 50 });
    assert.equal(message.length, 50);
    assert.equal(message.endsWith("..."), true);
  });
});

describe("safeErrorMessage — input shape", () => {
  it("accepts plain string", () => {
    const { message } = safeErrorMessage("plain string error");
    assert.equal(message, "plain string error");
  });

  it("accepts {message: string} duck type", () => {
    const { message } = safeErrorMessage({ message: "duck error" });
    assert.equal(message, "duck error");
  });

  it("falls back to String(e) for arbitrary objects", () => {
    const { message } = safeErrorMessage({ foo: "bar" });
    assert.equal(typeof message, "string");
    assert.equal(message.length > 0, true);
  });

  it("each call yields a unique correlationId (UUIDv4 shape)", () => {
    const r1 = safeErrorMessage("e1");
    const r2 = safeErrorMessage("e2");
    assert.notEqual(r1.correlationId, r2.correlationId);
    assert.match(r1.correlationId, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  });
});

describe("passthrough mode", () => {
  it("returns raw message when passthrough=true", () => {
    const { message } = safeErrorMessage(new Error("/Users/lab/sensitive"), { passthrough: true });
    assert.equal(message, "/Users/lab/sensitive");
  });

  it("checkErrorPassthroughAtBoot returns true + warns when env=1", () => {
    let warned = false;
    const r = checkErrorPassthroughAtBoot(
      { warn: () => { warned = true; } },
      { NOX_ERROR_PASSTHROUGH: "1" },
    );
    assert.equal(r, true);
    assert.equal(warned, true);
  });

  it("checkErrorPassthroughAtBoot returns false when env unset", () => {
    let warned = false;
    const r = checkErrorPassthroughAtBoot(
      { warn: () => { warned = true; } },
      {},
    );
    assert.equal(r, false);
    assert.equal(warned, false);
  });
});

// ── buildSafeErrorBody / adoption helpers ──────────────────────────────────

describe("buildSafeErrorBody", () => {
  it("invokes onLog with raw + correlationId, returns sanitized body", () => {
    const logs: Array<{ correlationId: string; raw: unknown }> = [];
    const body = buildSafeErrorBody(new Error("/Users/lab/whatever:1:1"), {
      onLog: (info) => logs.push(info),
    });
    assert.equal(typeof body.correlation_id, "string");
    assert.equal(body.error, "internal_error");
    assert.equal(logs.length, 1);
    assert.equal(logs[0].correlationId, body.correlation_id);
  });
});

// ── adoption: safeError500 / safeConflict409 / safeMark500 ──────────────────

describe("safeError500 (drop-in for hooks.ts)", () => {
  it("returns { error, correlation_id } and logs raw", () => {
    const logs: Array<{ context?: string }> = [];
    const body = safeError500(new Error("/Users/secret"), {
      onLog: (info) => logs.push(info),
      context: "hooks.recent",
    });
    assert.equal(body.error, "internal_error");
    assert.equal(typeof body.correlation_id, "string");
    assert.equal(logs[0].context, "hooks.recent");
  });

  it("preserves clean error message when nothing to strip", () => {
    const body = safeError500(new Error("invalid_argument"), {
      onLog: () => {},
    });
    assert.equal(body.error, "invalid_argument");
  });
});

describe("safeConflict409", () => {
  it("emits { error: resolution_failed, message, correlation_id }", () => {
    const body = safeConflict409(new Error("/root/x.db"), { onLog: () => {} });
    assert.equal(body.error, "resolution_failed");
    assert.equal(body.message, "internal_error");
    assert.equal(typeof body.correlation_id, "string");
  });
});

describe("safeMark500", () => {
  it("strips SQL fragment leak (R-L3-3)", () => {
    const body = safeMark500(
      new Error(
        "SQLITE_ERROR: near \"WHERE id = 42 AND col = 'sensitive'\": at /var/lib/x.db:1",
      ),
      { onLog: () => {} },
    );
    assert.equal(body.error.includes("/var"), false);
    assert.equal(typeof body.correlation_id, "string");
  });
});
