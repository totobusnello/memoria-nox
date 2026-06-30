/**
 * T7 tests — config.ts (env loader + validator)
 *
 * 8 cases.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { loadConfig, DEFAULTS, __test } from "../config.js";

describe("T7 config", () => {
  it("defaults: enabled=false, sources={openclaw}", () => {
    const c = loadConfig({});
    assert.equal(c.enabled, false);
    assert.deepEqual(Array.from(c.allowedSources), ["openclaw"]);
    assert.equal(c.rateLimitPerMin, DEFAULTS.rateLimitPerMin);
    assert.equal(c.dedupThreshold, DEFAULTS.dedupThreshold);
    assert.equal(c.llmClassify, false);
    assert.equal(c.dryRun, false);
  });

  it("NOX_HOOKS_ENABLED=1 turns on", () => {
    const c = loadConfig({ NOX_HOOKS_ENABLED: "1" });
    assert.equal(c.enabled, true);
  });

  it("invalid bool falls back to default", () => {
    const c = loadConfig({ NOX_HOOKS_ENABLED: "maybe" });
    assert.equal(c.enabled, false);
  });

  it("NOX_HOOK_SOURCES CSV parsed + filtered", () => {
    const c = loadConfig({ NOX_HOOK_SOURCES: "openclaw,cli,bogus,manual" });
    assert.ok(c.allowedSources.has("openclaw"));
    assert.ok(c.allowedSources.has("cli"));
    assert.ok(c.allowedSources.has("manual"));
    assert.ok(!c.allowedSources.has("bogus" as never));
  });

  it("rate limit out of range falls back", () => {
    const c1 = loadConfig({ NOX_HOOK_RATE_LIMIT: "0" });
    assert.equal(c1.rateLimitPerMin, DEFAULTS.rateLimitPerMin);
    const c2 = loadConfig({ NOX_HOOK_RATE_LIMIT: "9999" });
    assert.equal(c2.rateLimitPerMin, DEFAULTS.rateLimitPerMin);
    const c3 = loadConfig({ NOX_HOOK_RATE_LIMIT: "50" });
    assert.equal(c3.rateLimitPerMin, 50);
  });

  it("dedup threshold out of range falls back", () => {
    const c1 = loadConfig({ NOX_HOOK_DEDUP_THRESHOLD: "1.5" });
    assert.equal(c1.dedupThreshold, DEFAULTS.dedupThreshold);
    const c2 = loadConfig({ NOX_HOOK_DEDUP_THRESHOLD: "0.85" });
    assert.equal(c2.dedupThreshold, 0.85);
  });

  it("pii policy drop is honored", () => {
    const c = loadConfig({ NOX_HOOK_PII_POLICY: "drop" });
    assert.equal(c.piiPolicy, "drop");
    const c2 = loadConfig({ NOX_HOOK_PII_POLICY: "redact" });
    assert.equal(c2.piiPolicy, "redact");
    const c3 = loadConfig({ NOX_HOOK_PII_POLICY: "wat" });
    assert.equal(c3.piiPolicy, "redact");
  });

  it("internal helpers behave", () => {
    assert.equal(__test.parseBool("yes", false), true);
    assert.equal(__test.parseBool("nope", true), true);
    assert.equal(__test.parseInt0("5", 1, 1, 10), 5);
    assert.equal(__test.parseInt0("abc", 1, 1, 10), 1);
    const ps = __test.parseSources("a,b,manual", new Set(["openclaw"]));
    assert.ok(ps.has("manual"));
  });
});
