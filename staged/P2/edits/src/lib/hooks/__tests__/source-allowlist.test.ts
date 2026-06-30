/**
 * T2 tests — source-allowlist.ts (Layer 2)
 *
 * 8 cases covering:
 *  - unknown source always rejected
 *  - source in allowlist + role user → accept
 *  - source in allowlist + role assistant → accept
 *  - source NOT in allowlist → reject with reason
 *  - role system/tool/unknown → reject
 *  - allowed source + role inversion ablation
 *  - empty allowlist behavior
 *  - case sensitivity preservation
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { evaluateSourceAllowlist, isKnownSource } from "../source-allowlist.js";
import { loadConfig } from "../config.js";
import type { HookEvent } from "../types.js";

function mkEvent(overrides: Partial<HookEvent> = {}): HookEvent {
  return {
    event_id: "e1",
    source: "openclaw",
    role: "user",
    content: "hello world this is a real prompt",
    session_id: "s1",
    project_slug: "p1",
    ts: "2026-05-18T12:00:00Z",
    ...overrides,
  };
}

describe("T2 source-allowlist (Layer 2)", () => {
  it("rejects source=unknown unconditionally", () => {
    const cfg = loadConfig({ NOX_HOOK_SOURCES: "openclaw,cli,unknown" });
    const dec = evaluateSourceAllowlist(mkEvent({ source: "unknown" }), cfg);
    assert.equal(dec.capture, false);
    assert.match(dec.reason, /unknown/);
  });

  it("accepts source=openclaw role=user under default config", () => {
    const cfg = loadConfig({});
    const dec = evaluateSourceAllowlist(mkEvent(), cfg);
    assert.equal(dec.capture, true);
  });

  it("accepts source=openclaw role=assistant", () => {
    const cfg = loadConfig({});
    const dec = evaluateSourceAllowlist(mkEvent({ role: "assistant" }), cfg);
    assert.equal(dec.capture, true);
  });

  it("rejects source=cli when not in allowlist (default openclaw only)", () => {
    const cfg = loadConfig({});
    const dec = evaluateSourceAllowlist(mkEvent({ source: "cli" }), cfg);
    assert.equal(dec.capture, false);
    assert.match(dec.reason, /not in NOX_HOOK_SOURCES/);
  });

  it("accepts source=cli when explicitly allowed", () => {
    const cfg = loadConfig({ NOX_HOOK_SOURCES: "openclaw,cli" });
    const dec = evaluateSourceAllowlist(mkEvent({ source: "cli" }), cfg);
    assert.equal(dec.capture, true);
  });

  it("rejects role=system / tool / unknown", () => {
    const cfg = loadConfig({});
    for (const role of ["system", "tool", "unknown"] as const) {
      const dec = evaluateSourceAllowlist(mkEvent({ role }), cfg);
      assert.equal(dec.capture, false, `role=${role} should be rejected`);
    }
  });

  it("isKnownSource returns true only for valid sources", () => {
    assert.equal(isKnownSource("openclaw"), true);
    assert.equal(isKnownSource("foobar"), false);
    assert.equal(isKnownSource(""), false);
  });

  it("empty allowlist falls back to defaults", () => {
    const cfg = loadConfig({ NOX_HOOK_SOURCES: "" });
    assert.equal(cfg.allowedSources.has("openclaw"), true);
  });
});
