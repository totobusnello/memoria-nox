/**
 * Tests for `src/api/server-deps-p5.ts`.
 *
 * We avoid importing `broadcast-singleton.ts` (top-level await on missing
 * staged-P5 broadcast.js would fail in CI). All P5 behavior under test is
 * pure / dynamic-import-guarded.
 */

import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import type { ServerResponse, IncomingMessage } from "node:http";
import {
  redactEnvelope,
  viewerShowQueryEnabled,
  resolveViewerRoot,
  openRedactedSseStream,
  pumpSseToResponse,
} from "../server-deps-p5.js";

const ENV_BACKUP: Record<string, string | undefined> = {};
function setEnv(k: string, v: string | undefined): void {
  if (!(k in ENV_BACKUP)) ENV_BACKUP[k] = process.env[k];
  if (v === undefined) delete process.env[k];
  else process.env[k] = v;
}
function restoreEnv(): void {
  for (const k of Object.keys(ENV_BACKUP)) {
    const v = ENV_BACKUP[k];
    if (v === undefined) delete process.env[k];
    else process.env[k] = v;
    delete ENV_BACKUP[k];
  }
}

describe("server-deps-p5: redaction", () => {
  beforeEach(() => {
    setEnv("NOX_VIEWER_SHOW_QUERY", "0");
  });
  afterEach(() => restoreEnv());

  it("viewerShowQueryEnabled is false by default", () => {
    setEnv("NOX_VIEWER_SHOW_QUERY", undefined);
    assert.equal(viewerShowQueryEnabled(), false);
  });

  it("viewerShowQueryEnabled is true when NOX_VIEWER_SHOW_QUERY=1", () => {
    setEnv("NOX_VIEWER_SHOW_QUERY", "1");
    assert.equal(viewerShowQueryEnabled(), true);
  });

  it("redactEnvelope masks query_text by default", () => {
    const env = { id: 1, ev: { type: "search", query_text: "sensitive query" } };
    const out = redactEnvelope(env);
    assert.equal(out.ev["query_text"], "[redacted]");
  });

  it("redactEnvelope passes through when NOX_VIEWER_SHOW_QUERY=1", () => {
    setEnv("NOX_VIEWER_SHOW_QUERY", "1");
    const env = { id: 1, ev: { type: "search", query_text: "raw" } };
    const out = redactEnvelope(env);
    assert.equal(out.ev["query_text"], "raw");
  });

  it("redactEnvelope truncates long content to 40 chars + ellipsis", () => {
    const longText = "x".repeat(100);
    const env = { id: 1, ev: { type: "chunk", content: longText } };
    const out = redactEnvelope(env);
    const content = out.ev["content"] as string;
    assert.ok(content.endsWith("…"));
    assert.ok(content.length <= 41); // 40 chars + ellipsis
  });

  it("redactEnvelope leaves short content untouched", () => {
    const env = { id: 1, ev: { type: "chunk", content: "short" } };
    const out = redactEnvelope(env);
    assert.equal(out.ev["content"], "short");
  });

  it("redactEnvelope walks nested chunks array", () => {
    const env = {
      id: 1,
      ev: {
        type: "search",
        query_text: "q",
        chunks: [{ id: 1, content: "y".repeat(80) }, { id: 2, content: "ok" }],
      },
    };
    const out = redactEnvelope(env);
    const chunks = out.ev["chunks"] as any[];
    assert.ok((chunks[0].content as string).endsWith("…"));
    assert.equal(chunks[1].content, "ok");
  });

  it("redactEnvelope returns new object — does not mutate original", () => {
    const env = { id: 1, ev: { type: "search", query_text: "x" } };
    const out = redactEnvelope(env);
    assert.notStrictEqual(out, env);
    assert.notStrictEqual(out.ev, env.ev);
    assert.equal(env.ev.query_text, "x"); // original intact
  });
});

describe("server-deps-p5: viewer root", () => {
  afterEach(() => restoreEnv());

  it("resolveViewerRoot defaults to <cwd>/dist/viewer", () => {
    setEnv("NOX_VIEWER_ROOT", undefined);
    const r = resolveViewerRoot();
    assert.ok(r.endsWith("/dist/viewer") || r.endsWith("\\dist\\viewer"));
  });

  it("resolveViewerRoot honors NOX_VIEWER_ROOT", () => {
    setEnv("NOX_VIEWER_ROOT", "/tmp/viewer-test");
    assert.equal(resolveViewerRoot(), "/tmp/viewer-test");
  });
});

describe("server-deps-p5: degraded paths", () => {
  it("openRedactedSseStream returns null when sse module missing", async () => {
    const out = await openRedactedSseStream({ clientId: "c1" });
    // In the staged-wire-up-adapters isolated build, `./events-stream.js` is
    // not co-located, so the dynamic import fails and we return null.
    assert.equal(out, null);
  });

  it("pumpSseToResponse drains async iter to response", async () => {
    const sent: string[] = [];
    const res = new EventEmitter() as unknown as ServerResponse;
    (res as any).write = (s: string) => {
      sent.push(s);
      return true;
    };
    (res as any).end = () => {};
    (res as any).once = res.once.bind(res);

    const req = new EventEmitter() as unknown as IncomingMessage;

    async function* gen(): AsyncGenerator<string> {
      yield "a";
      yield "b";
      yield "c";
    }

    let closed = false;
    await pumpSseToResponse(res, gen(), req, () => {
      closed = true;
    });

    assert.deepEqual(sent, ["a", "b", "c"]);
    assert.equal(closed, true);
  });
});
