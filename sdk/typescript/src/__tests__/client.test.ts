/**
 * Tests for NoxMemClient
 *
 * Uses a lightweight HTTP mock server (Node http module) to simulate
 * the memoria-nox API — no external dependencies required.
 */

import { createServer, type Server, type IncomingMessage, type ServerResponse } from "node:http";
import { NoxMemClient, NoxMemApiError } from "../client.js";
import type {
  HealthResponse,
  SearchResult,
  AnswerSuccess,
  MarkResult,
  HooksStatus,
  HooksDryrunResponse,
  ImportResult,
} from "../client.js";

// ─── Mock server helpers ──────────────────────────────────────────────────────

interface RouteHandler {
  method: string;
  path: string;
  statusCode: number;
  body: unknown;
  contentType?: string;
}

function startMockServer(routes: RouteHandler[]): Promise<{ server: Server; baseUrl: string }> {
  return new Promise((resolve) => {
    const server = createServer((req: IncomingMessage, res: ServerResponse) => {
      const urlPath = req.url?.split("?")[0] ?? "";
      const method = req.method ?? "GET";

      const route = routes.find(
        (r) => r.method === method && (r.path === urlPath || urlPath.startsWith(r.path + "/")),
      );

      if (!route) {
        res.writeHead(404, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: `No mock route for ${method} ${urlPath}` }));
        return;
      }

      const ct = route.contentType ?? "application/json";
      res.writeHead(route.statusCode, { "Content-Type": ct });
      if (typeof route.body === "string") {
        res.end(route.body);
      } else {
        res.end(JSON.stringify(route.body));
      }
    });

    server.listen(0, "127.0.0.1", () => {
      const addr = server.address() as { port: number };
      resolve({ server, baseUrl: `http://127.0.0.1:${addr.port}` });
    });
  });
}

function stopServer(server: Server): Promise<void> {
  return new Promise((resolve, reject) => server.close((err) => (err ? reject(err) : resolve())));
}

// ─── Tests ────────────────────────────────────────────────────────────────────

const HEALTH_FIXTURE: HealthResponse = {
  chunks: { total: 62836, types: [{ chunk_type: "decision", c: 1200 }] },
  vectorCoverage: { embedded: 62836, total: 62836, orphans: 0 },
  knowledgeGraph: { entities: 402, relations: 544 },
  procedures: 28,
  dbSizeMB: 487.3,
  services: { "openclaw-gateway": true, "nox-mem-watch": true },
};

const SEARCH_FIXTURE: SearchResult[] = [
  {
    chunk_id: 41203,
    content: "Gemini 2.5 Flash Lite is the default model...",
    score: 0.913,
    source_path: "memory/entities/decision/model-selection.md",
    section: "compiled",
    chunk_type: "decision",
    created_at: "2026-04-22T14:30:00Z",
  },
  {
    chunk_id: 41204,
    content: "Never hardcode API keys...",
    score: 0.872,
    source_path: "memory/entities/lesson/secrets.md",
    section: "frontmatter",
    chunk_type: "lesson",
    created_at: "2026-04-21T10:00:00Z",
  },
];

// ── Health ────────────────────────────────────────────────────────────────────

describe("health()", () => {
  let server: Server;
  let client: NoxMemClient;

  beforeAll(async () => {
    const s = await startMockServer([{ method: "GET", path: "/api/health", statusCode: 200, body: HEALTH_FIXTURE }]);
    server = s.server;
    client = new NoxMemClient({ baseUrl: s.baseUrl });
  });

  afterAll(() => stopServer(server));

  test("returns health response with chunk count", async () => {
    const h = await client.health();
    expect(h.chunks?.total).toBe(62836);
    expect(h.vectorCoverage?.embedded).toBe(62836);
    expect(h.knowledgeGraph?.entities).toBe(402);
  });

  test("services field is a boolean map", async () => {
    const h = await client.health();
    expect(h.services?.["openclaw-gateway"]).toBe(true);
  });
});

// ── Search GET ────────────────────────────────────────────────────────────────

describe("search()", () => {
  let server: Server;
  let client: NoxMemClient;

  beforeAll(async () => {
    const s = await startMockServer([{ method: "GET", path: "/api/search", statusCode: 200, body: SEARCH_FIXTURE }]);
    server = s.server;
    client = new NoxMemClient({ baseUrl: s.baseUrl });
  });

  afterAll(() => stopServer(server));

  test("returns array of SearchResult", async () => {
    const res = await client.search("gemini quota");
    expect(Array.isArray(res)).toBe(true);
    expect(res).toHaveLength(2);
    expect(res[0].chunk_id).toBe(41203);
    expect(res[0].score).toBeCloseTo(0.913);
  });

  test("result has section field", async () => {
    const res = await client.search("secrets");
    expect(res[1].section).toBe("frontmatter");
  });
});

// ── Search POST ───────────────────────────────────────────────────────────────

describe("searchPost()", () => {
  let server: Server;
  let client: NoxMemClient;

  beforeAll(async () => {
    const s = await startMockServer([{ method: "POST", path: "/api/search", statusCode: 200, body: SEARCH_FIXTURE }]);
    server = s.server;
    client = new NoxMemClient({ baseUrl: s.baseUrl });
  });

  afterAll(() => stopServer(server));

  test("POST body variant returns same shape", async () => {
    const res = await client.searchPost({ q: "monkey patch", limit: 5 });
    expect(res).toHaveLength(2);
  });
});

// ── Answer ────────────────────────────────────────────────────────────────────

describe("answer()", () => {
  let server: Server;
  let client: NoxMemClient;

  const ANSWER_FIXTURE: AnswerSuccess = {
    answer: "After upgrading, run /root/reapply-monkey-patch.sh [chunk_1].",
    citations: [
      {
        chunk_id: 41203,
        marker_id: "chunk_1",
        file_path: "memory/entities/lesson/openclaw-upgrade.md",
        line_range: "L12-L18",
        snippet: "After any npm upgrade, immediately reapply the monkey-patch...",
      },
    ],
    metadata: {
      latency_ms: 1847,
      tokens_in: 2341,
      tokens_out: 198,
      provider: "gemini",
      model: "gemini-2.5-flash-lite",
      retrieval_count: 8,
      fallback_used: false,
      retry_count: 0,
    },
    trace_id: "f3a9c812-1b2e-4d7f-9a03-c1e8b5d60a22",
  };

  beforeAll(async () => {
    const s = await startMockServer([{ method: "POST", path: "/api/answer", statusCode: 200, body: ANSWER_FIXTURE }]);
    server = s.server;
    client = new NoxMemClient({ baseUrl: s.baseUrl });
  });

  afterAll(() => stopServer(server));

  test("returns AnswerSuccess with citations", async () => {
    const res = await client.answer("How to reapply monkey-patch?");
    expect(res.answer).toContain("[chunk_1]");
    expect(res.citations).toHaveLength(1);
    expect(res.citations[0].chunk_id).toBe(41203);
    expect(res.trace_id).toBe("f3a9c812-1b2e-4d7f-9a03-c1e8b5d60a22");
  });

  test("metadata contains model field", async () => {
    const res = await client.answer("test question");
    expect(res.metadata.model).toBe("gemini-2.5-flash-lite");
  });
});

// ── Agents ────────────────────────────────────────────────────────────────────

describe("agents()", () => {
  let server: Server;
  let client: NoxMemClient;

  beforeAll(async () => {
    const s = await startMockServer([{
      method: "GET",
      path: "/api/agents",
      statusCode: 200,
      body: [{ name: "forge", type: "dev" }, { name: "atlas", type: "memory" }],
    }]);
    server = s.server;
    client = new NoxMemClient({ baseUrl: s.baseUrl });
  });

  afterAll(() => stopServer(server));

  test("returns agent profiles array", async () => {
    const agents = await client.agents();
    expect(agents).toHaveLength(2);
    expect((agents[0] as { name: string }).name).toBe("forge");
  });
});

// ── KG ────────────────────────────────────────────────────────────────────────

describe("kg()", () => {
  let server: Server;
  let client: NoxMemClient;

  beforeAll(async () => {
    const s = await startMockServer([{
      method: "GET",
      path: "/api/kg",
      statusCode: 200,
      body: {
        entities: [{ id: 12, name: "openclaw-gateway", type: "service", mentions: 847 }],
        relations: [{ source: "openclaw-gateway", relation: "depends_on", target: "nox-mem-api", confidence: 0.92 }],
      },
    }]);
    server = s.server;
    client = new NoxMemClient({ baseUrl: s.baseUrl });
  });

  afterAll(() => stopServer(server));

  test("returns entities and relations", async () => {
    const res = await client.kg();
    expect(res.entities).toHaveLength(1);
    expect(res.relations?.[0].confidence).toBeCloseTo(0.92);
  });
});

// ── KG Path ───────────────────────────────────────────────────────────────────

describe("kgPath()", () => {
  let server: Server;
  let client: NoxMemClient;

  beforeAll(async () => {
    const s = await startMockServer([{
      method: "GET",
      path: "/api/kg/path",
      statusCode: 200,
      body: { path: ["nox-mem-api", "vectorize", "gemini-embedding-001"] },
    }]);
    server = s.server;
    client = new NoxMemClient({ baseUrl: s.baseUrl });
  });

  afterAll(() => stopServer(server));

  test("returns ordered path array", async () => {
    const path = await client.kgPath("nox-mem-api", "gemini-embedding-001");
    expect(path).toEqual(["nox-mem-api", "vectorize", "gemini-embedding-001"]);
  });
});

// ── KG Path null ──────────────────────────────────────────────────────────────

describe("kgPath() — no path found", () => {
  let server: Server;
  let client: NoxMemClient;

  beforeAll(async () => {
    const s = await startMockServer([{
      method: "GET",
      path: "/api/kg/path",
      statusCode: 200,
      body: { path: null },
    }]);
    server = s.server;
    client = new NoxMemClient({ baseUrl: s.baseUrl });
  });

  afterAll(() => stopServer(server));

  test("returns null when no path exists", async () => {
    const path = await client.kgPath("a", "z");
    expect(path).toBeNull();
  });
});

// ── Mark chunk ────────────────────────────────────────────────────────────────

describe("markChunk()", () => {
  let server: Server;
  let client: NoxMemClient;

  const MARK_FIXTURE: MarkResult = {
    ok: true,
    chunk_id: 41203,
    applied: { confidence: 0.95, provenance_kind: "user-marked" },
    audit_id: 1047,
  };

  beforeAll(async () => {
    const s = await startMockServer([{
      method: "POST",
      path: "/api/chunk",
      statusCode: 200,
      body: MARK_FIXTURE,
    }]);
    server = s.server;
    client = new NoxMemClient({ baseUrl: s.baseUrl });
  });

  afterAll(() => stopServer(server));

  test("returns MarkResult with confidence applied", async () => {
    const res = await client.markChunk(41203, "canonical", "Verified 2026-05-18");
    expect(res.ok).toBe(true);
    expect(res.applied.confidence).toBeCloseTo(0.95);
    expect(res.applied.provenance_kind).toBe("user-marked");
    expect(res.audit_id).toBe(1047);
  });
});

// ── Supersede chunk ───────────────────────────────────────────────────────────

describe("supersedeChunk()", () => {
  let server: Server;
  let client: NoxMemClient;

  const SUPERSEDE_FIXTURE: MarkResult = {
    ok: true,
    chunk_id: 40123,
    applied: { confidence: 0.1, provenance_kind: "user-marked", superseded_by: 41203 },
    audit_id: 1048,
  };

  beforeAll(async () => {
    const s = await startMockServer([{
      method: "POST",
      path: "/api/chunk",
      statusCode: 200,
      body: SUPERSEDE_FIXTURE,
    }]);
    server = s.server;
    client = new NoxMemClient({ baseUrl: s.baseUrl });
  });

  afterAll(() => stopServer(server));

  test("returns MarkResult with superseded_by set", async () => {
    const res = await client.supersedeChunk(40123, 41203, { reason: "manual_resolution" });
    expect(res.applied.superseded_by).toBe(41203);
    expect(res.applied.confidence).toBeCloseTo(0.1);
  });
});

// ── Hooks status ──────────────────────────────────────────────────────────────

describe("hookStatus()", () => {
  let server: Server;
  let client: NoxMemClient;

  const HOOKS_FIXTURE: HooksStatus = {
    config: {
      enabled: true,
      allowed_sources: ["mcp", "api", "cli"],
      rate_limit_per_min: 60,
      dedup_threshold: 0.85,
      pii_policy: "redact",
    },
    queueDepth: 3,
    rateLimitTokens: 47,
  };

  beforeAll(async () => {
    const s = await startMockServer([{
      method: "GET",
      path: "/api/hooks/status",
      statusCode: 200,
      body: HOOKS_FIXTURE,
    }]);
    server = s.server;
    client = new NoxMemClient({ baseUrl: s.baseUrl });
  });

  afterAll(() => stopServer(server));

  test("returns hooks config and queue depth", async () => {
    const res = await client.hookStatus();
    expect(res.config?.enabled).toBe(true);
    expect(res.queueDepth).toBe(3);
    expect(res.config?.allowed_sources).toContain("mcp");
  });
});

// ── Hooks dryrun ──────────────────────────────────────────────────────────────

describe("hookDryrun()", () => {
  let server: Server;
  let client: NoxMemClient;

  const DRYRUN_FIXTURE: HooksDryrunResponse = {
    result: { accepted: true, content: "[PERSON] from Nuvini called about Q2", redacted: true },
    trace: [{ layer: "pii_redact", reason: "name_pattern_matched", redaction_count: 1, kind: "pii" }],
  };

  beforeAll(async () => {
    const s = await startMockServer([{
      method: "POST",
      path: "/api/hooks/dryrun",
      statusCode: 200,
      body: DRYRUN_FIXTURE,
    }]);
    server = s.server;
    client = new NoxMemClient({ baseUrl: s.baseUrl });
  });

  afterAll(() => stopServer(server));

  test("returns trace with pii_redact layer", async () => {
    const res = await client.hookDryrun({ text: "John Smith from Nuvini called" });
    expect(res.trace).toHaveLength(1);
    expect(res.trace?.[0].layer).toBe("pii_redact");
    expect(res.trace?.[0].redaction_count).toBe(1);
  });
});

// ── Reflect ───────────────────────────────────────────────────────────────────

describe("reflect()", () => {
  let server: Server;
  let client: NoxMemClient;

  beforeAll(async () => {
    const s = await startMockServer([{
      method: "GET",
      path: "/api/reflect",
      statusCode: 200,
      body: { summary: "You have 3 recurring prod incidents related to Gemini quota." },
    }]);
    server = s.server;
    client = new NoxMemClient({ baseUrl: s.baseUrl });
  });

  afterAll(() => stopServer(server));

  test("returns reflect result", async () => {
    const res = await client.reflect("recurring production incidents");
    expect((res as { summary: string }).summary).toContain("Gemini");
  });
});

// ── Procedures ────────────────────────────────────────────────────────────────

describe("procedures()", () => {
  let server: Server;
  let client: NoxMemClient;

  beforeAll(async () => {
    const s = await startMockServer([{
      method: "GET",
      path: "/api/procedures",
      statusCode: 200,
      body: {
        procedures: [
          { id: 88, title: "Reapply monkey-patch", steps: ["SSH", "Run script", "Verify"], agent: "forge" },
        ],
      },
    }]);
    server = s.server;
    client = new NoxMemClient({ baseUrl: s.baseUrl });
  });

  afterAll(() => stopServer(server));

  test("returns unwrapped procedures array", async () => {
    const procs = await client.procedures();
    expect(procs).toHaveLength(1);
    expect(procs[0].id).toBe(88);
    expect(procs[0].agent).toBe("forge");
  });
});

// ── Crystallize ───────────────────────────────────────────────────────────────

describe("crystallize()", () => {
  let server: Server;
  let client: NoxMemClient;

  beforeAll(async () => {
    const s = await startMockServer([{
      method: "POST",
      path: "/api/crystallize",
      statusCode: 200,
      body: { id: 88, ok: true },
    }]);
    server = s.server;
    client = new NoxMemClient({ baseUrl: s.baseUrl });
  });

  afterAll(() => stopServer(server));

  test("returns new procedure id", async () => {
    const res = await client.crystallize({
      title: "Reapply monkey-patch",
      steps: ["SSH into VPS", "Run script", "Verify"],
    });
    expect(res.id).toBe(88);
    expect(res.ok).toBe(true);
  });
});

// ── Conflicts ─────────────────────────────────────────────────────────────────

describe("listConflicts()", () => {
  let server: Server;
  let client: NoxMemClient;

  beforeAll(async () => {
    const s = await startMockServer([{
      method: "GET",
      path: "/api/kg/conflicts",
      statusCode: 200,
      body: {
        conflicts: [
          {
            id: 1,
            conflict_type: "direct",
            source_entity_name: "openclaw-gateway",
            predicate: "version",
            status: "unresolved",
            detected_at: "2026-05-18T10:00:00Z",
          },
        ],
        total: 1,
      },
    }]);
    server = s.server;
    client = new NoxMemClient({ baseUrl: s.baseUrl });
  });

  afterAll(() => stopServer(server));

  test("returns conflicts list with total", async () => {
    const res = await client.listConflicts({ status: "unresolved" });
    expect(res.total).toBe(1);
    expect(res.conflicts[0].conflict_type).toBe("direct");
  });
});

// ── Import result shape ───────────────────────────────────────────────────────

describe("ImportResult type", () => {
  // Static type test — ensures ImportResult has the right fields
  const fixture: ImportResult = {
    chunks_inserted: 12455,
    chunks_skipped_dedup: 873,
    kg_entities_inserted: 402,
    kg_entities_merged: 56,
    duration_ms: 47832,
    warnings: [],
  };
  test("ImportResult fixture compiles and has expected shape", () => {
    expect(fixture.chunks_inserted).toBe(12455);
    expect(fixture.warnings).toHaveLength(0);
  });
});

// ── Error handling ────────────────────────────────────────────────────────────

describe("NoxMemApiError", () => {
  let server: Server;
  let client: NoxMemClient;

  beforeAll(async () => {
    const s = await startMockServer([
      { method: "GET", path: "/api/health", statusCode: 500, body: { error: "SQLITE_ERROR: no such table" } },
      { method: "POST", path: "/api/answer", statusCode: 503, body: { error: "feature disabled", env_var: "NOX_ANSWER_ENABLED" } },
      { method: "GET", path: "/api/reflect", statusCode: 401, body: { error: "unauthorized" } },
    ]);
    server = s.server;
    client = new NoxMemClient({ baseUrl: s.baseUrl });
  });

  afterAll(() => stopServer(server));

  test("throws NoxMemApiError on 500", async () => {
    await expect(client.health()).rejects.toBeInstanceOf(NoxMemApiError);
  });

  test("error.status is 500", async () => {
    try {
      await client.health();
    } catch (e) {
      expect((e as NoxMemApiError).status).toBe(500);
    }
  });

  test("isFeatureDisabled is true on 503 feature disabled", async () => {
    try {
      await client.answer("test");
    } catch (e) {
      expect((e as NoxMemApiError).isFeatureDisabled).toBe(true);
    }
  });

  test("isUnauthorized is true on 401", async () => {
    try {
      await client.reflect("test");
    } catch (e) {
      expect((e as NoxMemApiError).isUnauthorized).toBe(true);
    }
  });
});

// ── Auth header ───────────────────────────────────────────────────────────────

describe("auth token forwarding", () => {
  let server: Server;
  let client: NoxMemClient;
  let lastAuthHeader: string | undefined;

  beforeAll(async () => {
    server = createServer((req: IncomingMessage, res: ServerResponse) => {
      lastAuthHeader = req.headers["authorization"];
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ chunks: { total: 1 } }));
    });
    await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
    const addr = server.address() as { port: number };
    client = new NoxMemClient({
      baseUrl: `http://127.0.0.1:${addr.port}`,
      authToken: "test-secret-token",
    });
  });

  afterAll(() => stopServer(server));

  test("sends Authorization: Bearer header when authToken configured", async () => {
    await client.health();
    expect(lastAuthHeader).toBe("Bearer test-secret-token");
  });
});

// ── SSE stream parsing ────────────────────────────────────────────────────────

describe("streamEvents() SSE parsing", () => {
  let server: Server;
  let client: NoxMemClient;

  const SSE_PAYLOAD = [
    "id: 1",
    "event: chunk.created",
    `data: ${JSON.stringify({ kind: "chunk.created", ts: "2026-05-18T10:00:00Z", payload: { chunk_id: 41203 } })}`,
    "",
    "id: 2",
    "event: search.executed",
    `data: ${JSON.stringify({ kind: "search.executed", ts: "2026-05-18T10:00:01Z", payload: { query: "test" } })}`,
    "",
    "",
  ].join("\n");

  beforeAll(async () => {
    server = createServer((_req: IncomingMessage, res: ServerResponse) => {
      res.writeHead(200, {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      });
      res.write(SSE_PAYLOAD);
      res.end();
    });
    await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
    const addr = server.address() as { port: number };
    client = new NoxMemClient({ baseUrl: `http://127.0.0.1:${addr.port}` });
  });

  afterAll(() => stopServer(server));

  test("yields parsed ViewerEvent objects from SSE stream", async () => {
    const events = [];
    for await (const event of client.streamEvents()) {
      events.push(event);
    }
    expect(events.length).toBeGreaterThanOrEqual(1);
    expect(events[0].kind).toBe("chunk.created");
    expect((events[0].payload as { chunk_id: number }).chunk_id).toBe(41203);
  });

  test("second event has correct kind", async () => {
    const events = [];
    for await (const event of client.streamEvents()) {
      events.push(event);
    }
    expect(events[1]?.kind).toBe("search.executed");
  });
});
