import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  InMemorySessionStore,
  extractClientId,
  mintClientId,
  clientIdCookie,
  isValidUuid,
  openSession,
  recordEvent,
  closeSession,
} from "../session.js";

describe("T8 — session", () => {
  it("mintClientId returns valid UUIDv4", () => {
    const id = mintClientId();
    assert.ok(isValidUuid(id));
  });

  it("isValidUuid rejects garbage", () => {
    assert.equal(isValidUuid("not-uuid"), false);
    assert.equal(isValidUuid(""), false);
  });

  it("extractClientId prefers X-Viewer header", () => {
    const id = mintClientId();
    const out = extractClientId({ headerXViewer: id });
    assert.equal(out, id);
  });

  it("extractClientId falls back to cookie", () => {
    const id = mintClientId();
    const out = extractClientId({
      cookieHeader: `other=1; nox_viewer_id=${id}; foo=bar`,
    });
    assert.equal(out, id);
  });

  it("extractClientId returns null when nothing valid", () => {
    const out = extractClientId({ cookieHeader: "other=1" });
    assert.equal(out, null);
  });

  it("clientIdCookie format", () => {
    const id = mintClientId();
    const c = clientIdCookie(id);
    assert.match(c, new RegExp(`nox_viewer_id=${id}`));
    assert.match(c, /HttpOnly/);
    assert.match(c, /SameSite=Lax/);
  });

  it("openSession + recordEvent + closeSession lifecycle", async () => {
    const store = new InMemorySessionStore();
    const id = mintClientId();
    const ctx = await openSession(store, id);
    assert.equal(ctx.events_consumed, 0);
    await recordEvent(store, ctx);
    await recordEvent(store, ctx, 1);
    assert.equal(ctx.events_consumed, 2);
    assert.equal(ctx.events_dropped, 1);
    await closeSession(store, ctx);
    const rows = await store.list();
    assert.equal(rows.length, 1);
    assert.equal(rows[0]!.events_consumed, 2);
    assert.notEqual(rows[0]!.ts_end, null);
  });

  it("openSession stores remote_label", async () => {
    const store = new InMemorySessionStore();
    const ctx = await openSession(store, mintClientId(), "127.0.0.1");
    const rows = await store.list();
    assert.equal(rows.find((r) => r.id === ctx.rowId)?.remote_label, "127.0.0.1");
  });
});
