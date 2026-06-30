/**
 * G13 — dryrun rate limit tests.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import {
  readDryrunRateLimitConfig,
  createDryrunRateLimiter,
  checkDryrunGate,
} from "../rate-limit-dryrun-fix.js";

describe("readDryrunRateLimitConfig", () => {
  it("defaults to 10/min when env unset", () => {
    assert.equal(readDryrunRateLimitConfig({}).perMinute, 10);
  });

  it("parses positive integers", () => {
    assert.equal(
      readDryrunRateLimitConfig({ NOX_HOOK_DRYRUN_RATE_LIMIT: "30" }).perMinute,
      30,
    );
  });

  it("falls back to 10 on invalid/zero/negative", () => {
    for (const v of ["abc", "0", "-5", ""]) {
      assert.equal(
        readDryrunRateLimitConfig({ NOX_HOOK_DRYRUN_RATE_LIMIT: v }).perMinute,
        10,
        `should default for ${v}`,
      );
    }
  });
});

describe("createDryrunRateLimiter — per-IP bucket", () => {
  it("allows up to capacity bursts then rejects", () => {
    const lim = createDryrunRateLimiter({ perMinute: 5 });
    let now = 1_000_000;
    for (let i = 0; i < 5; i++) {
      assert.equal(lim.tryConsume("1.1.1.1", now), true, `req ${i} should pass`);
    }
    assert.equal(lim.tryConsume("1.1.1.1", now), false, "6th should reject");
  });

  it("isolates IPs from each other", () => {
    const lim = createDryrunRateLimiter({ perMinute: 2 });
    const now = 5_000_000;
    assert.equal(lim.tryConsume("a", now), true);
    assert.equal(lim.tryConsume("a", now), true);
    assert.equal(lim.tryConsume("a", now), false);
    // Different IP still has full bucket.
    assert.equal(lim.tryConsume("b", now), true);
    assert.equal(lim.tryConsume("b", now), true);
  });

  it("refills over time", () => {
    const lim = createDryrunRateLimiter({ perMinute: 60 }); // 1/sec
    let now = 10_000_000;
    // Drain
    for (let i = 0; i < 60; i++) assert.equal(lim.tryConsume("x", now), true);
    assert.equal(lim.tryConsume("x", now), false);
    // 30 seconds later → 30 tokens refilled.
    now += 30_000;
    let allowed = 0;
    for (let i = 0; i < 40; i++) if (lim.tryConsume("x", now)) allowed++;
    assert.equal(allowed >= 29 && allowed <= 31, true, `refill expected ~30, got ${allowed}`);
  });
});

describe("checkDryrunGate", () => {
  it("returns allowed=true when bucket has tokens", () => {
    const lim = createDryrunRateLimiter({ perMinute: 10 });
    const r = checkDryrunGate(lim, "1.2.3.4");
    assert.equal(r.allowed, true);
  });

  it("returns 429 with Retry-After + dryrun_per_ip reason when exhausted", () => {
    const lim = createDryrunRateLimiter({ perMinute: 1 });
    const cfg = { perMinute: 1 };
    checkDryrunGate(lim, "ip", cfg); // consume the only token
    const r = checkDryrunGate(lim, "ip", cfg);
    assert.equal(r.allowed, false);
    assert.equal(r.rejectResponse?.status, 429);
    assert.equal(r.rejectResponse?.headers["Retry-After"], "60");
    assert.equal(r.rejectResponse?.body.reason, "dryrun_per_ip");
    assert.equal(r.rejectResponse?.body.retry_after_seconds, 60);
  });
});
