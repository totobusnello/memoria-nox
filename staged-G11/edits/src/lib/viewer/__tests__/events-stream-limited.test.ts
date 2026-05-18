/**
 * G11 — SSE connection limit tests.
 *
 * Strategy: stub the upstream `openSseStream` via a fake Broadcaster that
 * matches its public contract (addClient, removeClient, ringSnapshot,
 * clientCount). Avoids pulling in real broadcaster + ring buffer.
 */

import { describe, it, before, beforeEach, after } from "node:test";
import assert from "node:assert/strict";

// Allow dynamic env tweaking without polluting global process.env across runs.
let savedEnv: NodeJS.ProcessEnv;

// We import lazily so test-local env overrides take effect.
let mod: typeof import("../../../api/events-stream-limited.js");

before(async () => {
  savedEnv = { ...process.env };
  // Clean slate — drop relevant env vars before each test resets.
  delete process.env.NOX_VIEWER_MAX_CONNECTIONS;
  delete process.env.NOX_VIEWER_MAX_PER_IP;
  delete process.env.NOX_VIEWER_DROP_OLDEST;
  mod = await import("../../../api/events-stream-limited.js");
});

after(() => {
  process.env = savedEnv;
});

// ── fake broadcaster ────────────────────────────────────────────────────────

type FakeClient = { id: string; wake: () => void; queue: { drain: () => unknown[]; stats: () => { dropped: number } } };

function makeFakeBroadcaster() {
  const clients = new Map<string, FakeClient>();
  return {
    addClient: (id: string, wake: () => void): FakeClient => {
      const c: FakeClient = {
        id,
        wake,
        queue: { drain: () => [], stats: () => ({ dropped: 0 }) },
      };
      // ClientHandle in broadcast.ts has additional fields (lastSentId etc).
      // We add them to satisfy the type when cast.
      (c as unknown as { lastSentId: number }).lastSentId = 0;
      clients.set(id, c);
      return c;
    },
    removeClient: (id: string): void => {
      clients.delete(id);
    },
    ringSnapshot: () => [] as unknown[],
    clientCount: () => clients.size,
    /** Test helper. */
    _live: () => clients.size,
  };
}

beforeEach(() => {
  // Reset tracker singleton between tests (otherwise state bleeds).
  mod.setSseTracker(new mod.SseConnectionTracker());
});

// ── env parsing ─────────────────────────────────────────────────────────────

describe("readSseLimitConfig", () => {
  it("returns defaults when env unset", () => {
    const c = mod.readSseLimitConfig({});
    assert.equal(c.maxConnections, 50);
    assert.equal(c.maxPerIp, 5);
    assert.equal(c.dropOldest, false);
  });

  it("parses positive integers", () => {
    const c = mod.readSseLimitConfig({
      NOX_VIEWER_MAX_CONNECTIONS: "100",
      NOX_VIEWER_MAX_PER_IP: "20",
      NOX_VIEWER_DROP_OLDEST: "1",
    });
    assert.equal(c.maxConnections, 100);
    assert.equal(c.maxPerIp, 20);
    assert.equal(c.dropOldest, true);
  });

  it("falls back to defaults on invalid/negative/zero", () => {
    const c = mod.readSseLimitConfig({
      NOX_VIEWER_MAX_CONNECTIONS: "-5",
      NOX_VIEWER_MAX_PER_IP: "0",
      NOX_VIEWER_DROP_OLDEST: "0",
    });
    assert.equal(c.maxConnections, 50);
    assert.equal(c.maxPerIp, 5);
    assert.equal(c.dropOldest, false);
  });

  it("dropOldest only true on exactly '1'", () => {
    assert.equal(mod.readSseLimitConfig({ NOX_VIEWER_DROP_OLDEST: "true" }).dropOldest, false);
    assert.equal(mod.readSseLimitConfig({ NOX_VIEWER_DROP_OLDEST: "yes" }).dropOldest, false);
    assert.equal(mod.readSseLimitConfig({ NOX_VIEWER_DROP_OLDEST: "1" }).dropOldest, true);
  });
});

// ── tracker basics ──────────────────────────────────────────────────────────

describe("SseConnectionTracker", () => {
  it("tracks size + per-IP independently", () => {
    const t = new mod.SseConnectionTracker();
    t.register({ clientId: "a", ip: "1.1.1.1", openedAt: 1, close: () => {} });
    t.register({ clientId: "b", ip: "1.1.1.1", openedAt: 2, close: () => {} });
    t.register({ clientId: "c", ip: "2.2.2.2", openedAt: 3, close: () => {} });
    assert.equal(t.size(), 3);
    assert.equal(t.sizePerIp("1.1.1.1"), 2);
    assert.equal(t.sizePerIp("2.2.2.2"), 1);
    assert.equal(t.sizePerIp("9.9.9.9"), 0);
  });

  it("unregister cleans both maps", () => {
    const t = new mod.SseConnectionTracker();
    t.register({ clientId: "a", ip: "1.1.1.1", openedAt: 1, close: () => {} });
    t.unregister("a");
    assert.equal(t.size(), 0);
    assert.equal(t.sizePerIp("1.1.1.1"), 0);
  });

  it("dropOldest closes the first-registered client", () => {
    const t = new mod.SseConnectionTracker();
    let closedOldest = false;
    t.register({ clientId: "a", ip: "1.1.1.1", openedAt: 1, close: () => { closedOldest = true; } });
    t.register({ clientId: "b", ip: "1.1.1.1", openedAt: 2, close: () => {} });
    const dropped = t.dropOldest();
    assert.equal(dropped, "a");
    assert.equal(closedOldest, true);
    assert.equal(t.size(), 1);
  });

  it("dropOldest returns null when empty", () => {
    const t = new mod.SseConnectionTracker();
    assert.equal(t.dropOldest(), null);
  });
});

// ── openLimitedSseStream — accept path ──────────────────────────────────────

describe("openLimitedSseStream: accept", () => {
  it("accepts the first connection and registers in tracker", () => {
    const bc = makeFakeBroadcaster();
    const tracker = new mod.SseConnectionTracker();
    const res = mod.openLimitedSseStream({
      broadcaster: bc as unknown as import("../../../lib/viewer/broadcast.js").Broadcaster,
      clientId: "c1",
      ip: "10.0.0.1",
      tracker,
      config: { maxConnections: 5, maxPerIp: 2, dropOldest: false },
    });
    assert.equal(res.rejected, false);
    if (res.rejected) return; // narrow
    assert.equal(res.liveCount, 1);
    assert.equal(tracker.size(), 1);
    res.stream.close();
    assert.equal(tracker.size(), 0);
  });
});

// ── rejection — global cap ─────────────────────────────────────────────────

describe("openLimitedSseStream: global cap", () => {
  it("rejects 503 when global cap reached", () => {
    const bc = makeFakeBroadcaster();
    const tracker = new mod.SseConnectionTracker();
    const cfg = { maxConnections: 2, maxPerIp: 99, dropOldest: false };
    // Fill the cap from different IPs so per-ip doesn't trip first.
    for (let i = 0; i < 2; i++) {
      const r = mod.openLimitedSseStream({
        broadcaster: bc as unknown as import("../../../lib/viewer/broadcast.js").Broadcaster,
        clientId: `c${i}`,
        ip: `10.0.0.${i + 1}`,
        tracker,
        config: cfg,
      });
      assert.equal(r.rejected, false);
    }
    const rej = mod.openLimitedSseStream({
      broadcaster: bc as unknown as import("../../../lib/viewer/broadcast.js").Broadcaster,
      clientId: "c-overflow",
      ip: "10.0.0.99",
      tracker,
      config: cfg,
    });
    assert.equal(rej.rejected, true);
    if (!rej.rejected) return;
    assert.equal(rej.status, 503);
    assert.equal(rej.reason, "global_cap");
    assert.equal(rej.body.max, 2);
    assert.equal(rej.retryAfterSeconds, 5);
  });

  it("dropOldest=true evicts oldest and accepts new", () => {
    const bc = makeFakeBroadcaster();
    const tracker = new mod.SseConnectionTracker();
    const cfg = { maxConnections: 2, maxPerIp: 99, dropOldest: true };
    const accepted: string[] = [];
    for (let i = 0; i < 2; i++) {
      const r = mod.openLimitedSseStream({
        broadcaster: bc as unknown as import("../../../lib/viewer/broadcast.js").Broadcaster,
        clientId: `c${i}`,
        ip: `10.0.0.${i + 1}`,
        tracker,
        config: cfg,
      });
      if (!r.rejected) accepted.push(`c${i}`);
    }
    const r2 = mod.openLimitedSseStream({
      broadcaster: bc as unknown as import("../../../lib/viewer/broadcast.js").Broadcaster,
      clientId: "c-new",
      ip: "10.0.0.99",
      tracker,
      config: cfg,
    });
    assert.equal(r2.rejected, false, "dropOldest should accept new");
    assert.equal(tracker.size(), 2);
    // The first registered (`c0`) should be gone.
    assert.equal(tracker.snapshot().find((c) => c.clientId === "c0"), undefined);
  });
});

// ── rejection — per-IP cap ─────────────────────────────────────────────────

describe("openLimitedSseStream: per-IP cap", () => {
  it("rejects 503 with reason=per_ip_cap when per-IP exceeded", () => {
    const bc = makeFakeBroadcaster();
    const tracker = new mod.SseConnectionTracker();
    const cfg = { maxConnections: 100, maxPerIp: 2, dropOldest: false };
    const ip = "10.0.0.7";
    for (let i = 0; i < 2; i++) {
      const r = mod.openLimitedSseStream({
        broadcaster: bc as unknown as import("../../../lib/viewer/broadcast.js").Broadcaster,
        clientId: `c${i}`,
        ip,
        tracker,
        config: cfg,
      });
      assert.equal(r.rejected, false);
    }
    const rej = mod.openLimitedSseStream({
      broadcaster: bc as unknown as import("../../../lib/viewer/broadcast.js").Broadcaster,
      clientId: "c-over",
      ip,
      tracker,
      config: cfg,
    });
    assert.equal(rej.rejected, true);
    if (!rej.rejected) return;
    assert.equal(rej.reason, "per_ip_cap");
    assert.equal(rej.body.max, 2);
    assert.equal(rej.retryAfterSeconds, 10);
  });

  it("per-IP cap NEVER triggers dropOldest (would let one IP evict tenants)", () => {
    const bc = makeFakeBroadcaster();
    const tracker = new mod.SseConnectionTracker();
    const cfg = { maxConnections: 100, maxPerIp: 1, dropOldest: true };
    const ip = "10.0.0.99";
    const r1 = mod.openLimitedSseStream({
      broadcaster: bc as unknown as import("../../../lib/viewer/broadcast.js").Broadcaster,
      clientId: "first",
      ip,
      tracker,
      config: cfg,
    });
    assert.equal(r1.rejected, false);
    const r2 = mod.openLimitedSseStream({
      broadcaster: bc as unknown as import("../../../lib/viewer/broadcast.js").Broadcaster,
      clientId: "second",
      ip,
      tracker,
      config: cfg,
    });
    assert.equal(r2.rejected, true, "per-IP cap must reject, never drop");
    // The first one should still be alive.
    assert.equal(tracker.snapshot().some((c) => c.clientId === "first"), true);
  });
});

// ── close lifecycle ─────────────────────────────────────────────────────────

describe("close lifecycle", () => {
  it("close() unregisters from tracker exactly once", () => {
    const bc = makeFakeBroadcaster();
    const tracker = new mod.SseConnectionTracker();
    const cfg = { maxConnections: 5, maxPerIp: 5, dropOldest: false };
    const r = mod.openLimitedSseStream({
      broadcaster: bc as unknown as import("../../../lib/viewer/broadcast.js").Broadcaster,
      clientId: "c-x",
      ip: "10.0.0.1",
      tracker,
      config: cfg,
    });
    assert.equal(r.rejected, false);
    if (r.rejected) return;
    r.stream.close();
    r.stream.close(); // idempotent
    assert.equal(tracker.size(), 0);
  });
});

// ── rejection-to-http helper ───────────────────────────────────────────────

describe("rejectionToHttp", () => {
  it("emits 503 + Retry-After + JSON body", () => {
    const http = mod.rejectionToHttp({
      rejected: true,
      status: 503,
      retryAfterSeconds: 5,
      reason: "global_cap",
      body: { error: "sse_capacity", reason: "global_cap", max: 50 },
    });
    assert.equal(http.status, 503);
    assert.equal(http.headers["Retry-After"], "5");
    assert.equal(http.headers["Content-Type"], "application/json; charset=utf-8");
    assert.equal(http.body.error, "sse_capacity");
  });
});
