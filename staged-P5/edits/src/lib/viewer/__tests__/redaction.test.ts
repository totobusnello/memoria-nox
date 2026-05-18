import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  REDACTED,
  queryHash,
  nameHash,
  safeBasename,
  redactEvent,
  stripForbiddenFields,
  viewerStartupWarnings,
} from "../redaction.js";
import { nowIso, type ViewerEvent } from "../event-types.js";

function makeSearchEvent(): ViewerEvent {
  return {
    ts: nowIso(),
    type: "search",
    source: "search-hybrid",
    summary: "search ok",
    details: {
      query_hash: queryHash("hello"),
      query: "hello world raw query",
      latency_ms: 50,
      top_k: 10,
      result_count: 5,
      mode: "hybrid",
      hybrid_breakdown: { bm25: 0.3, vec: 0.6, kg: 0.1 },
    },
  };
}

describe("T4 — redaction", () => {
  it("queryHash deterministic, 16 chars", () => {
    const a = queryHash("abc");
    const b = queryHash("abc");
    assert.equal(a, b);
    assert.equal(a.length, 16);
  });

  it("nameHash deterministic, 8 chars", () => {
    assert.equal(nameHash("Atlas"), nameHash("Atlas"));
    assert.equal(nameHash("Atlas").length, 8);
  });

  it("safeBasename strips path components", () => {
    assert.equal(safeBasename("/Users/lab/x.md"), "x.md");
    assert.equal(safeBasename("C:\\Windows\\file.txt"), "file.txt");
    assert.equal(safeBasename("name.md"), "name.md");
    assert.equal(safeBasename(""), undefined);
    assert.equal(safeBasename(null), undefined);
  });

  it("SearchEvent.query redacted by default", () => {
    const ev = makeSearchEvent();
    if (ev.type !== "search") throw new Error("setup");
    const originalHash = ev.details.query_hash;
    const out = redactEvent(ev, { showQuery: false });
    if (out.type !== "search") throw new Error("type drift");
    assert.equal(out.details.query, REDACTED);
    assert.equal(out.details.query_hash, originalHash);
  });

  it("SearchEvent.query surfaces raw when showQuery=true", () => {
    const ev = makeSearchEvent();
    const out = redactEvent(ev, { showQuery: true });
    if (out.type !== "search") throw new Error("type drift");
    assert.equal(out.details.query, "hello world raw query");
  });

  it("redactEvent does not mutate input", () => {
    const ev = makeSearchEvent();
    const original = JSON.parse(JSON.stringify(ev));
    redactEvent(ev, { showQuery: false });
    assert.deepEqual(ev, original);
  });

  it("stripForbiddenFields removes content/body/embedding/token", () => {
    const obj: Record<string, unknown> = {
      ok: 1,
      content: "leak",
      body: "leak",
      nested: { token: "leak", deep: { embedding: [1, 2, 3] } },
    };
    stripForbiddenFields(obj);
    assert.equal(obj.ok, 1);
    assert.equal("content" in obj, false);
    assert.equal("body" in obj, false);
    const nested = obj.nested as Record<string, unknown>;
    assert.equal("token" in nested, false);
    const deep = nested.deep as Record<string, unknown>;
    assert.equal("embedding" in deep, false);
  });

  it("stripForbiddenFields rewrites absolute paths to basename", () => {
    const obj: Record<string, unknown> = {
      file: "/Users/lab/Claude/note.md",
      arr: ["/abs/path/x.md", "rel.md"],
    };
    stripForbiddenFields(obj);
    assert.equal(obj.file, "note.md");
    const arr = obj.arr as string[];
    assert.equal(arr[0], "x.md");
    assert.equal(arr[1], "rel.md");
  });

  it("viewerStartupWarnings emits on NOX_VIEWER_SHOW_QUERY=1", () => {
    const out = viewerStartupWarnings({
      NOX_VIEWER_SHOW_QUERY: "1",
    } as NodeJS.ProcessEnv);
    assert.equal(out.length, 1);
    assert.match(out[0]!, /NOX_VIEWER_SHOW_QUERY=1/);
  });

  it("viewerStartupWarnings emits on bind 0.0.0.0 without token", () => {
    const out = viewerStartupWarnings({
      NOX_VIEWER_BIND: "0.0.0.0",
    } as NodeJS.ProcessEnv);
    assert.equal(out.length, 1);
    assert.match(out[0]!, /NOX_VIEWER_BIND=0\.0\.0\.0/);
  });

  it("viewerStartupWarnings empty when default", () => {
    const out = viewerStartupWarnings({} as NodeJS.ProcessEnv);
    assert.equal(out.length, 0);
  });

  it("redactEvent leaves non-search events untouched in query field", () => {
    const ev: ViewerEvent = {
      ts: nowIso(),
      type: "ingest",
      source: "ingest-router",
      summary: "x",
      details: {
        chunk_id: 1,
        chunk_kind: "entity",
        length: 100,
        redaction_count: 0,
        section: null,
        retention_days: null,
        pain: 0.2,
      },
    };
    const out = redactEvent(ev);
    assert.equal(out.type, "ingest");
  });
});
