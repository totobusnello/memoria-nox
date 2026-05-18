/**
 * T10 tests — decorators.ts
 *
 * 8 cases.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { parseDecorators, attachDecorators, decoratorOverride } from "../decorators.js";
import type { HookEvent } from "../types.js";

function mk(content: string): HookEvent {
  return {
    event_id: "e",
    source: "openclaw",
    role: "user",
    content,
    session_id: "s",
    project_slug: "p",
    ts: "2026-05-18T00:00:00Z",
  };
}

describe("T10 decorators", () => {
  it("// @nox:capture detected", () => {
    assert.deepEqual(parseDecorators("// @nox:capture\nrest"), ["capture"]);
  });

  it("// @nox:skip detected", () => {
    assert.deepEqual(parseDecorators("// @nox:skip"), ["skip"]);
  });

  it("# style comment detected", () => {
    assert.deepEqual(parseDecorators("# @nox:capture\nbody"), ["capture"]);
  });

  it("HTML comment detected", () => {
    assert.deepEqual(parseDecorators("<!-- @nox:skip -->\nbody"), ["skip"]);
  });

  it("only first 4 lines scanned", () => {
    const text = "line1\nline2\nline3\nline4\nline5 // @nox:capture\n";
    assert.deepEqual(parseDecorators(text), []);
  });

  it("decoratorOverride: skip wins over capture", () => {
    const e = mk("// @nox:capture\n// @nox:skip");
    assert.equal(decoratorOverride(e), "skip");
  });

  it("attachDecorators populates field when present", () => {
    const e = mk("// @nox:capture\nbody");
    const e2 = attachDecorators(e);
    assert.deepEqual(e2.decorators, ["capture"]);
  });

  it("no decorators present → returns null", () => {
    const e = mk("just normal text with no special markers here");
    assert.equal(decoratorOverride(e), null);
  });
});
