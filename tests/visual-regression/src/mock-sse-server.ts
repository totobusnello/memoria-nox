/**
 * mock-sse-server.ts
 *
 * Deterministic HTTP server for P5 viewer visual regression tests.
 *
 * Endpoints:
 *   GET  /viewer/          → serves index.html (P5 viewer frontend)
 *   GET  /viewer/app.js    → serves app.js
 *   GET  /viewer/style.css → serves style.css
 *   GET  /api/events/stream → SSE stream (subscribes client to event queue)
 *   POST /api/test/inject  → inject one or more events into connected clients
 *   POST /api/test/disconnect → force-close all SSE connections (simulate disconnect)
 *   POST /api/test/reset   → reset all state (call between tests)
 *   GET  /api/test/status  → { clients: N, totalInjected: N, ringBuffer: [...] }
 */

import http from "http";
import fs from "fs";
import path from "path";

// ── Types ──────────────────────────────────────────────────────────────────

export interface ViewerEvent {
  ts: string;
  type: "ingest" | "search" | "kg" | "crystallize" | "op_audit";
  source: string;
  summary: string;
  details?: Record<string, unknown>;
}

interface SseClient {
  id: string;
  res: http.ServerResponse;
}

// ── State ──────────────────────────────────────────────────────────────────

let clients: SseClient[] = [];
let totalInjected = 0;
const ringBuffer: ViewerEvent[] = [];
const RING_SIZE = 1000;

function resetState(): void {
  clients = [];
  totalInjected = 0;
  ringBuffer.length = 0;
}

// ── Static files ───────────────────────────────────────────────────────────

// Resolve viewer source files. In worktree context, look for them relative to
// repo root staged-P5 dir or fallback to fixtures.
function resolveViewerDir(): string {
  const candidates = [
    // Main worktree with merged P5
    path.resolve(__dirname, "../../../staged-P5/edits/src/viewer"),
    // Sibling worktrees (any agent-* that has staged-P5)
    path.resolve(
      __dirname,
      "../../../../../../worktrees/agent-a9ebac90048246300/staged-P5/edits/src/viewer"
    ),
    // Fixtures bundled with tests
    path.resolve(__dirname, "../fixtures/viewer"),
  ];
  for (const dir of candidates) {
    if (fs.existsSync(path.join(dir, "index.html"))) return dir;
  }
  throw new Error(
    `Cannot locate P5 viewer source files. Looked in:\n${candidates.join("\n")}`
  );
}

const VIEWER_DIR = resolveViewerDir();

const MIME: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
};

function serveStatic(
  req: http.IncomingMessage,
  res: http.ServerResponse,
  filePath: string
): boolean {
  if (!fs.existsSync(filePath)) return false;
  const ext = path.extname(filePath);
  res.writeHead(200, { "Content-Type": MIME[ext] ?? "text/plain" });
  res.end(fs.readFileSync(filePath));
  return true;
}

// ── SSE helpers ────────────────────────────────────────────────────────────

function sseWrite(client: SseClient, event: ViewerEvent): void {
  const id = totalInjected;
  const data = JSON.stringify(event);
  client.res.write(`id: ${id}\nevent: ${event.type}\ndata: ${data}\n\n`);
}

function broadcastEvent(event: ViewerEvent): void {
  totalInjected++;
  ringBuffer.push(event);
  if (ringBuffer.length > RING_SIZE) ringBuffer.shift();
  for (const client of clients) {
    sseWrite(client, event);
  }
}

function generateClientId(): string {
  return `test-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

// ── Router ─────────────────────────────────────────────────────────────────

function handleRequest(
  req: http.IncomingMessage,
  res: http.ServerResponse
): void {
  const url = req.url ?? "/";
  const method = req.method ?? "GET";

  // CORS for local dev
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (method === "OPTIONS") {
    res.writeHead(204);
    res.end();
    return;
  }

  // Static viewer files
  if (url === "/viewer/" || url === "/viewer/index.html") {
    serveStatic(req, res, path.join(VIEWER_DIR, "index.html"));
    return;
  }
  if (url === "/viewer/app.js") {
    serveStatic(req, res, path.join(VIEWER_DIR, "app.js"));
    return;
  }
  if (url === "/viewer/style.css") {
    serveStatic(req, res, path.join(VIEWER_DIR, "style.css"));
    return;
  }

  // SSE stream
  if (url === "/api/events/stream" && method === "GET") {
    const clientId = generateClientId();
    res.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    });
    res.write(": connected\n\n");

    const client: SseClient = { id: clientId, res };
    clients.push(client);

    req.on("close", () => {
      clients = clients.filter((c) => c.id !== clientId);
    });
    return;
  }

  // Test control endpoints
  if (url === "/api/test/inject" && method === "POST") {
    readBody(req, (body) => {
      try {
        const payload = JSON.parse(body);
        const events: ViewerEvent[] = Array.isArray(payload)
          ? payload
          : [payload];
        for (const ev of events) {
          broadcastEvent(ev);
        }
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({ ok: true, injected: events.length, clients: clients.length })
        );
      } catch (e) {
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: false, error: String(e) }));
      }
    });
    return;
  }

  if (url === "/api/test/disconnect" && method === "POST") {
    for (const client of clients) {
      client.res.end();
    }
    clients = [];
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true, disconnected: clients.length }));
    return;
  }

  if (url === "/api/test/reset" && method === "POST") {
    for (const client of clients) {
      try {
        client.res.end();
      } catch {}
    }
    resetState();
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
    return;
  }

  if (url === "/api/test/status" && method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        clients: clients.length,
        totalInjected,
        ringBuffer: ringBuffer.slice(-20),
      })
    );
    return;
  }

  // Health check (real nox-mem-api compat)
  if (url === "/api/health" && method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true, mock: true }));
    return;
  }

  res.writeHead(404);
  res.end("Not Found");
}

// ── Helpers ────────────────────────────────────────────────────────────────

function readBody(req: http.IncomingMessage, cb: (body: string) => void): void {
  let body = "";
  req.on("data", (chunk) => (body += chunk.toString()));
  req.on("end", () => cb(body));
}

// ── Boot ───────────────────────────────────────────────────────────────────

const PORT = Number(process.env.NOX_MOCK_SSE_PORT ?? 18903);
const server = http.createServer(handleRequest);
server.listen(PORT, "127.0.0.1", () => {
  // eslint-disable-next-line no-console
  console.log(`mock-sse-server listening on http://127.0.0.1:${PORT}`);
});

// Graceful shutdown
process.on("SIGTERM", () => server.close());
process.on("SIGINT", () => server.close());

export { server, broadcastEvent, resetState };
