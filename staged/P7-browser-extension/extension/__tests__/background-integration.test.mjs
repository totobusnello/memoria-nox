/**
 * background-integration.test.mjs — Integration tests for background SW
 * pure helpers.
 *
 * We can't easily boot a Chrome SW in node, but the pure functions exported
 * from background.js (isAllowed, escapeXml) are testable.
 *
 * Heavier flows (message hub, alarms) are tested in a future e2e harness
 * (deferred — see README "Phase 1 vs Phase 2").
 */

import { test, mock } from "node:test";
import assert from "node:assert/strict";

// Mock chrome.* surface enough that the background module can import.
// The background.js attaches listeners at module load; we stub the minimum.
const noop = () => {};
const addListenerStub = () => ({ addListener: noop, removeListener: noop });

globalThis.chrome = {
  storage: {
    local: {
      get: async () => ({}),
      set: async () => {},
    },
  },
  alarms: {
    get: async () => null,
    create: noop,
    onAlarm: addListenerStub(),
  },
  contextMenus: {
    create: noop,
    removeAll: async () => {},
    onClicked: addListenerStub(),
  },
  omnibox: {
    onInputChanged: addListenerStub(),
    onInputEntered: addListenerStub(),
  },
  tabs: {
    sendMessage: async () => {},
    create: async () => {},
  },
  runtime: {
    onMessage: addListenerStub(),
    onInstalled: addListenerStub(),
    onStartup: addListenerStub(),
    openOptionsPage: noop,
    getURL: (p) => `chrome-extension://test/${p}`,
    lastError: null,
  },
};

// Stub fetch to avoid network in tests
globalThis.fetch = async () => ({
  ok: false,
  status: 0,
  json: async () => ({}),
});

const bg = await import("../src/background.js");

test("isAllowed — empty allowlist denies everything", () => {
  assert.equal(bg.isAllowed("https://github.com/foo", []), false);
  assert.equal(bg.isAllowed("https://example.com", []), false);
});

test("isAllowed — exact hostname match", () => {
  const allow = ["github.com", "news.ycombinator.com"];
  assert.equal(bg.isAllowed("https://github.com/foo/bar", allow), true);
  assert.equal(bg.isAllowed("https://news.ycombinator.com/", allow), true);
  assert.equal(bg.isAllowed("https://example.com/", allow), false);
});

test("isAllowed — subdomain NOT matched (no wildcards in v0.1)", () => {
  const allow = ["github.com"];
  // gist.github.com is a different hostname — by design, user must opt in
  assert.equal(bg.isAllowed("https://gist.github.com/foo", allow), false);
});

test("isAllowed — malformed URL → false", () => {
  assert.equal(bg.isAllowed("not a url", ["github.com"]), false);
  assert.equal(bg.isAllowed("", ["github.com"]), false);
});

test("isAllowed — null/undefined allowlist → false", () => {
  assert.equal(bg.isAllowed("https://github.com", null), false);
  assert.equal(bg.isAllowed("https://github.com", undefined), false);
});

test("escapeXml — HTML entities escaped", () => {
  assert.equal(bg.escapeXml("<b>foo</b>"), "&lt;b&gt;foo&lt;/b&gt;");
  assert.equal(bg.escapeXml("a&b"), "a&amp;b");
  assert.equal(bg.escapeXml(`a"b'c`), "a&quot;b&apos;c");
});

test("escapeXml — non-string input coerced safely", () => {
  assert.equal(bg.escapeXml(123), "123");
  assert.equal(bg.escapeXml(null), "null");
});
