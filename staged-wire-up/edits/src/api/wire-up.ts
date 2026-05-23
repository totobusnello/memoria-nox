#!/usr/bin/env node
/**
 * src/api/wire-up.ts — Wave A→K HTTP route registration.
 *
 * Post-deploy gap closure: Wave A→K shipped framework-agnostic handlers under
 * `src/api/*.ts` (answer, export, import, events-stream, viewer-static,
 * conflict, mark, hooks) but `src/api-server.ts` (native http switch/case
 * dispatch) was never updated to mount them. Result: every new endpoint
 * returns 404.
 *
 * This module exports `registerWireUpRoutes()` — a single function called
 * from `src/api-server.ts` immediately after the existing switch/case block
 * (or before its `default` arm). It pattern-matches the request path against
 * the Wave A→K routes and delegates to each handler. Returns `true` when the
 * request was handled; `false` lets the host fall through to the existing
 * 404 reply.
 *
 * Framework constraint (regra "match existing routing pattern"):
 *   - Native Node `http` (`IncomingMessage` / `ServerResponse`). No Express.
 *   - JSON response helper signature mirrors `api-server.ts::json()`.
 *   - CORS headers piggyback the existing `json()` helper.
 *
 * Security defaults applied here:
 *   - G5 (error sanitizer): every catch funnels through `sanitizeErrorForHttp`
 *     so stack traces and internal paths never leak in 500 responses.
 *   - G6 (localhost guard): every mutating endpoint (`POST /api/import`,
 *     `POST /api/conflict/:id/resolve`, `POST /api/chunk/:id/mark`,
 *     `POST /api/chunk/:id/supersede`, `POST /api/hooks/dryrun`) gates on
 *     `makeLocalhostGuard()`. Read-only endpoints stay open (parity with
 *     `/api/health`, `/api/kg`, etc.).
 *
 * Caller contract (`api-server.ts`):
 *
 *   import { registerWireUpRoutes } from "./api/wire-up.js";
 *
 *   async function handleRequest(req, res) {
 *     // … existing switch/case …
 *     // before falling through to 404, ask the wire-up router:
 *     if (await registerWireUpRoutes(req, res)) return;
 *     // existing 404 reply
 *   }
 *
 * The handlers are imported lazily (`await import(…)`) so that the existing
 * API server boots even when a staged-* dir hasn't been deployed yet
 * (degraded mode: route returns 503 not_implemented, never 500).
 */

import { IncomingMessage, ServerResponse } from "node:http";

// ─── F10 Phase C Phase 2: telemetry-collector hook ───────────────────────────
// Lazy import — falls back silently if telemetry-collector is not yet deployed.
// recordRequest is fire-and-forget synchronous; zero async overhead.
let _recordRequest:
  | ((
      path: "search" | "answer",
      startMs: number,
      endMs: number,
      resultCount: number,
      pathUsed: string,
      semanticUsed: boolean,
      statusCode?: number,
    ) => void)
  | null
  | undefined = undefined; // undefined = not yet resolved; null = not available

async function getRecordRequest(): Promise<typeof _recordRequest> {
  if (_recordRequest !== undefined) return _recordRequest;
  try {
    const mod: any = await import("../lib/telemetry-collector.js");
    _recordRequest = mod.recordRequest ?? null;
  } catch {
    _recordRequest = null; // telemetry-collector not deployed — degrade gracefully
  }
  return _recordRequest;
}

// ─── CORS / JSON helpers (parity with src/api-server.ts) ────────────────────

const CORS_HEADERS: Record<string, string> = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, X-Trace-Id, X-Request-ID, Authorization, Last-Event-ID",
};

function writeJson(
  res: ServerResponse,
  data: unknown,
  status = 200,
  extraHeaders: Record<string, string> = {},
): void {
  res.writeHead(status, {
    "Content-Type": "application/json",
    ...CORS_HEADERS,
    ...extraHeaders,
  });
  res.end(typeof data === "string" ? data : JSON.stringify(data));
}

function writeBuffer(
  res: ServerResponse,
  body: Buffer | string,
  status: number,
  headers: Record<string, string>,
): void {
  res.writeHead(status, { ...CORS_HEADERS, ...headers });
  res.end(body);
}

// ─── Body parsing ────────────────────────────────────────────────────────────

function readBody(req: IncomingMessage, limit = 64 * 1024 * 1024): Promise<string> {
  // 64 MiB upper bound for /api/import archive_b64 payloads.
  return new Promise((resolve, reject) => {
    let data = "";
    let size = 0;
    req.on("data", (chunk: Buffer) => {
      size += chunk.length;
      if (size > limit) {
        reject(new Error("Payload too large"));
        req.destroy();
        return;
      }
      data += chunk.toString("utf-8");
    });
    req.on("end", () => resolve(data));
    req.on("error", reject);
  });
}

async function readJsonBody<T = unknown>(req: IncomingMessage, limit?: number): Promise<T> {
  const raw = await readBody(req, limit);
  if (!raw) return {} as T;
  try {
    return JSON.parse(raw) as T;
  } catch {
    throw new Error("Invalid JSON body");
  }
}

function parseQueryString(url: string): Record<string, string> {
  const idx = url.indexOf("?");
  if (idx === -1) return {};
  const params: Record<string, string> = {};
  for (const part of url.substring(idx + 1).split("&")) {
    const [k, v] = part.split("=");
    if (k) params[decodeURIComponent(k)] = decodeURIComponent(v || "");
  }
  return params;
}

// ─── G5 sanitizer + G6 guard wiring (lazy, never crash boot) ───────────────

type SanitizerFn = (err: unknown, opts?: { requestId?: string }) => { status: number; body: unknown };
type GuardFn = (req: IncomingMessage, res: ServerResponse) => boolean;

let _sanitizer: SanitizerFn | null = null;
let _guard: GuardFn | null = null;

async function getSanitizer(): Promise<SanitizerFn> {
  if (_sanitizer) return _sanitizer;
  try {
    const mod: any = await import("../lib/error-sanitizer/sanitize.js");
    _sanitizer = (err, opts) => mod.sanitizeErrorForHttp(err, opts ?? {});
  } catch {
    // Fallback when G5 isn't deployed: minimal redaction (no stack, no paths).
    _sanitizer = (err) => ({
      status: 500,
      body: {
        error: "internal error",
        code: "INTERNAL_ERROR",
        requestId: "n/a",
      },
    });
  }
  return _sanitizer;
}

async function getLocalhostGuard(): Promise<GuardFn> {
  if (_guard) return _guard;
  try {
    const mod: any = await import("../lib/auth/localhost-guard.js");
    _guard = mod.defaultLocalhostGuard as GuardFn;
  } catch {
    // Fallback when G6 isn't deployed: default-deny remote, allow local.
    _guard = (req, res) => {
      const addr = req.socket?.remoteAddress ?? "";
      const local = addr === "127.0.0.1" || addr === "::1" || addr === "::ffff:127.0.0.1";
      if (local) return false;
      writeJson(res, { error: "forbidden", reason: "localhost-only" }, 403);
      return true;
    };
  }
  return _guard;
}

// Helper: header lookup (case-insensitive).
function getReqHeader(req: IncomingMessage, name: string): string | undefined {
  const v = req.headers[name.toLowerCase()];
  if (Array.isArray(v)) return v[0];
  return v;
}

// Helper: catch + sanitize wrapper around a route handler.
async function safeHandle(
  req: IncomingMessage,
  res: ServerResponse,
  fn: () => Promise<void>,
): Promise<void> {
  try {
    await fn();
  } catch (err) {
    const sanitizer = await getSanitizer();
    const requestId = getReqHeader(req, "x-request-id");
    const out = sanitizer(err, { requestId });
    writeJson(res, out.body, out.status, { "X-Request-ID": String((out.body as any)?.requestId ?? requestId ?? "") });
  }
}

// ─── Route table ────────────────────────────────────────────────────────────

const CONFLICT_ID_RE = /^\/api\/conflict\/(\d+)$/;
const CONFLICT_RESOLVE_RE = /^\/api\/conflict\/(\d+)\/resolve$/;
const CHUNK_MARK_RE = /^\/api\/chunk\/(\d+)\/mark$/;
const CHUNK_SUPERSEDE_RE = /^\/api\/chunk\/(\d+)\/supersede$/;

/** Cheap probe — caller can detect "is this URL ours?" without parsing body. */
export function matchesWireUpRoute(method: string, path: string): boolean {
  if (method === "POST" && path === "/api/answer") return true;
  if (method === "POST" && path === "/api/export") return true;
  if (method === "POST" && path === "/api/import") return true;
  if (method === "GET" && path === "/api/events/stream") return true;
  if (method === "GET" && path.startsWith("/viewer")) return true;
  if (method === "GET" && path === "/api/conflict") return true;
  if (method === "GET" && CONFLICT_ID_RE.test(path)) return true;
  if (method === "POST" && CONFLICT_RESOLVE_RE.test(path)) return true;
  if (method === "POST" && CHUNK_MARK_RE.test(path)) return true;
  if (method === "POST" && CHUNK_SUPERSEDE_RE.test(path)) return true;
  if (method === "GET" && path === "/api/hooks/status") return true;
  if (method === "GET" && path === "/api/hooks/recent") return true;
  if (method === "POST" && path === "/api/hooks/dryrun") return true;
  if (method === "GET" && path === "/api/health/confidence") return true;
  return false;
}

/**
 * Main router. Returns true when the request was handled (response sent).
 * Returns false when caller should keep dispatching.
 */
export async function registerWireUpRoutes(
  req: IncomingMessage,
  res: ServerResponse,
): Promise<boolean> {
  const url = req.url || "/";
  const path = url.split("?")[0];
  const method = (req.method || "GET").toUpperCase();

  if (!matchesWireUpRoute(method, path)) return false;

  // ── P1: POST /api/answer ────────────────────────────────────────────────
  // F10 Phase C Phase 2: wrapped with telemetry timing.
  if (method === "POST" && path === "/api/answer") {
    await safeHandle(req, res, async () => {
      const _t0 = Date.now();
      const body = await readJsonBody(req);
      const mod: any = await import("./answer.js");
      const out = await mod.handleAnswerRequest({
        body,
        headers: req.headers,
      });
      const _t1 = Date.now();
      // Fire-and-forget telemetry — non-blocking, degrades gracefully if not deployed.
      // /api/answer always runs the full semantic pipeline (Gemini embed + LLM synthesis).
      // result_count = 1: one synthesized answer per call (not a ranked list).
      const rec = await getRecordRequest();
      rec?.("answer", _t0, _t1, 1, "answer-pipeline", true, out.status);
      writeJson(res, out.body, out.status, out.headers ?? {});
    });
    return true;
  }

  // ── A2: POST /api/export ───────────────────────────────────────────────
  if (method === "POST" && path === "/api/export") {
    // Read-only on the corpus, but produces large encrypted blob — keep
    // open to localhost; remote access controlled at network layer (G6
    // bind host). No mutation = no guard required here.
    await safeHandle(req, res, async () => {
      const body = await readJsonBody(req);
      const handlerMod: any = await import("./export.js");
      const depsMod: any = await tryImport("../lib/archive/server-deps.js");
      if (!depsMod || typeof depsMod.buildExportDeps !== "function") {
        writeJson(
          res,
          {
            error: "not_implemented",
            reason: "export deps not deployed",
            hint: "deploy staged-A2 + lib/archive/server-deps.js (post-A2 wire-up needs DB reader binding)",
          },
          503,
        );
        return;
      }
      const out = await handlerMod.handleExport(body, await depsMod.buildExportDeps());
      writeBuffer(res, out.body, out.status, out.headers);
    });
    return true;
  }

  // ── A2: POST /api/import ───────────────────────────────────────────────
  if (method === "POST" && path === "/api/import") {
    const guard = await getLocalhostGuard();
    if (guard(req, res)) return true;
    await safeHandle(req, res, async () => {
      const body = await readJsonBody(req); // 64 MiB cap
      const handlerMod: any = await import("./import.js");
      const depsMod: any = await tryImport("../lib/archive/server-deps.js");
      if (!depsMod || typeof depsMod.buildImportDeps !== "function") {
        writeJson(
          res,
          {
            error: "not_implemented",
            reason: "import deps not deployed",
            hint: "deploy staged-A2 + lib/archive/server-deps.js",
          },
          503,
        );
        return;
      }
      const out = await handlerMod.handleImport(body, await depsMod.buildImportDeps());
      writeJson(res, out.body, out.status, out.headers);
    });
    return true;
  }

  // ── P5: GET /api/events/stream (SSE) ───────────────────────────────────
  if (method === "GET" && path === "/api/events/stream") {
    await safeHandle(req, res, async () => {
      const sseMod: any = await import("./events-stream.js");
      const brMod: any = await tryImport("../lib/viewer/broadcast.js");
      if (!brMod || typeof brMod.getBroadcaster !== "function") {
        writeJson(
          res,
          { error: "not_implemented", reason: "viewer broadcaster not deployed" },
          503,
        );
        return;
      }
      const broadcaster = brMod.getBroadcaster();
      const lastEventId = sseMod.parseLastEventId(req.headers);
      const clientId = (await import("node:crypto")).randomUUID();
      const sse = sseMod.openSseStream({ broadcaster, clientId, lastEventId });
      res.writeHead(200, { ...CORS_HEADERS, ...sse.headers });
      req.on("close", () => sse.close());
      try {
        for await (const chunk of sse.iter) {
          if (!res.write(chunk)) {
            await new Promise<void>((r) => res.once("drain", r));
          }
        }
      } finally {
        sse.close();
        res.end();
      }
    });
    return true;
  }

  // ── P5: GET /viewer/* (static) ─────────────────────────────────────────
  if (method === "GET" && path.startsWith("/viewer")) {
    await safeHandle(req, res, async () => {
      const mod: any = await import("./viewer-static.js");
      const out = mod.serveViewerFile(path);
      writeBuffer(res, out.body, out.status, out.headers);
    });
    return true;
  }

  // ── L2: GET /api/conflict ──────────────────────────────────────────────
  if (method === "GET" && path === "/api/conflict") {
    await safeHandle(req, res, async () => {
      const mod: any = await import("./conflict.js");
      const dbMod: any = await tryImport("../lib/conflict/db.js");
      if (!dbMod || typeof dbMod.getConflictDb !== "function") {
        writeJson(res, { error: "not_implemented", reason: "L2 db not deployed" }, 503);
        return;
      }
      // Ensure singleton is warmed before the synchronous getConflictDb() call.
      // On a cold start the async warmup() hasn't settled yet; awaiting
      // ensureConflictDb() guarantees a non-null handle (or surfaces a real
      // DB-open failure as a 500 via safeHandle rather than a misleading 503).
      if (typeof dbMod.ensureConflictDb === "function") {
        await dbMod.ensureConflictDb();
      }
      const db = dbMod.getConflictDb();
      if (!db) {
        writeJson(res, { error: "not_implemented", reason: "L2 db not available" }, 503);
        return;
      }
      const out = mod.dispatchConflictApi(db, {
        method: "GET",
        path,
        query: parseQueryString(url),
      });
      writeJson(res, out.body, out.status);
    });
    return true;
  }

  // ── L2: GET /api/conflict/:id ──────────────────────────────────────────
  if (method === "GET" && CONFLICT_ID_RE.test(path)) {
    await safeHandle(req, res, async () => {
      const mod: any = await import("./conflict.js");
      const dbMod: any = await tryImport("../lib/conflict/db.js");
      if (!dbMod || typeof dbMod.getConflictDb !== "function") {
        writeJson(res, { error: "not_implemented", reason: "L2 db not deployed" }, 503);
        return;
      }
      if (typeof dbMod.ensureConflictDb === "function") {
        await dbMod.ensureConflictDb();
      }
      const db = dbMod.getConflictDb();
      if (!db) {
        writeJson(res, { error: "not_implemented", reason: "L2 db not available" }, 503);
        return;
      }
      const out = mod.dispatchConflictApi(db, {
        method: "GET",
        path,
      });
      writeJson(res, out.body, out.status);
    });
    return true;
  }

  // ── L2: POST /api/conflict/:id/resolve ─────────────────────────────────
  if (method === "POST" && CONFLICT_RESOLVE_RE.test(path)) {
    const guard = await getLocalhostGuard();
    if (guard(req, res)) return true;
    await safeHandle(req, res, async () => {
      const body = await readJsonBody(req);
      const mod: any = await import("./conflict.js");
      const dbMod: any = await tryImport("../lib/conflict/db.js");
      if (!dbMod || typeof dbMod.getConflictDb !== "function") {
        writeJson(res, { error: "not_implemented", reason: "L2 db not deployed" }, 503);
        return;
      }
      if (typeof dbMod.ensureConflictDb === "function") {
        await dbMod.ensureConflictDb();
      }
      const db = dbMod.getConflictDb();
      if (!db) {
        writeJson(res, { error: "not_implemented", reason: "L2 db not available" }, 503);
        return;
      }
      const actor = getReqHeader(req, "x-actor") ?? "api";
      const out = mod.dispatchConflictApi(db, {
        method: "POST",
        path,
        body,
        actor,
      });
      writeJson(res, out.body, out.status);
    });
    return true;
  }

  // ── L3: POST /api/chunk/:id/mark ───────────────────────────────────────
  if (method === "POST" && CHUNK_MARK_RE.test(path)) {
    const guard = await getLocalhostGuard();
    if (guard(req, res)) return true;
    await safeHandle(req, res, async () => {
      const m = CHUNK_MARK_RE.exec(path)!;
      const idStr = m[1];
      const body = await readJsonBody(req);
      const mod: any = await import("./mark.js");
      const shimMod: any = await tryImport("../lib/confidence/db-shim.js");
      if (!shimMod || typeof shimMod.getConfidenceDb !== "function") {
        writeJson(res, { error: "not_implemented", reason: "L3 db not deployed" }, 503);
        return;
      }
      const out = mod.handleMarkRequest(shimMod.getConfidenceDb(), idStr, body);
      writeJson(res, out.body, out.status);
    });
    return true;
  }

  // ── L3: POST /api/chunk/:id/supersede ──────────────────────────────────
  if (method === "POST" && CHUNK_SUPERSEDE_RE.test(path)) {
    const guard = await getLocalhostGuard();
    if (guard(req, res)) return true;
    await safeHandle(req, res, async () => {
      const m = CHUNK_SUPERSEDE_RE.exec(path)!;
      const idStr = m[1];
      const body = await readJsonBody(req);
      const mod: any = await import("./mark.js");
      const shimMod: any = await tryImport("../lib/confidence/db-shim.js");
      if (!shimMod || typeof shimMod.getConfidenceDb !== "function") {
        writeJson(res, { error: "not_implemented", reason: "L3 db not deployed" }, 503);
        return;
      }
      const out = mod.handleSupersedeRequest(shimMod.getConfidenceDb(), idStr, body);
      writeJson(res, out.body, out.status);
    });
    return true;
  }

  // ── L3: GET /api/health/confidence ─────────────────────────────────────
  if (method === "GET" && path === "/api/health/confidence") {
    await safeHandle(req, res, async () => {
      const mod: any = await tryImport("./health-confidence.js");
      if (!mod || typeof mod.handleHealthConfidence !== "function") {
        writeJson(res, { error: "not_implemented", reason: "L3 health not deployed" }, 503);
        return;
      }
      const out = await mod.handleHealthConfidence();
      writeJson(res, out.body, out.status);
    });
    return true;
  }

  // ── P2: GET /api/hooks/status ──────────────────────────────────────────
  if (method === "GET" && path === "/api/hooks/status") {
    await safeHandle(req, res, async () => {
      const mod: any = await import("./hooks.js");
      const depsMod: any = await tryImport("../lib/hooks/server-deps.js");
      if (!depsMod || typeof depsMod.buildHooksDeps !== "function") {
        writeJson(res, { error: "not_implemented", reason: "P2 deps not deployed" }, 503);
        return;
      }
      const out = await mod.handleHooksRequest(
        { method: "GET", path },
        await depsMod.buildHooksDeps(),
      );
      writeJson(res, out.body, out.status);
    });
    return true;
  }

  // ── P2: GET /api/hooks/recent ──────────────────────────────────────────
  if (method === "GET" && path === "/api/hooks/recent") {
    await safeHandle(req, res, async () => {
      const mod: any = await import("./hooks.js");
      const depsMod: any = await tryImport("../lib/hooks/server-deps.js");
      if (!depsMod || typeof depsMod.buildHooksDeps !== "function") {
        writeJson(res, { error: "not_implemented", reason: "P2 deps not deployed" }, 503);
        return;
      }
      const out = await mod.handleHooksRequest(
        { method: "GET", path, query: parseQueryString(url) },
        await depsMod.buildHooksDeps(),
      );
      writeJson(res, out.body, out.status);
    });
    return true;
  }

  // ── P2: POST /api/hooks/dryrun ─────────────────────────────────────────
  if (method === "POST" && path === "/api/hooks/dryrun") {
    const guard = await getLocalhostGuard();
    if (guard(req, res)) return true;
    await safeHandle(req, res, async () => {
      const body = await readJsonBody(req);
      const mod: any = await import("./hooks.js");
      const depsMod: any = await tryImport("../lib/hooks/server-deps.js");
      if (!depsMod || typeof depsMod.buildHooksDeps !== "function") {
        writeJson(res, { error: "not_implemented", reason: "P2 deps not deployed" }, 503);
        return;
      }
      const out = await mod.handleHooksRequest(
        { method: "POST", path, body },
        await depsMod.buildHooksDeps(),
      );
      writeJson(res, out.body, out.status);
    });
    return true;
  }

  // Should be unreachable (matchesWireUpRoute already filtered), but be safe.
  return false;
}

// ─── Internals ──────────────────────────────────────────────────────────────

async function tryImport(spec: string): Promise<any | null> {
  try {
    return await import(spec);
  } catch {
    return null;
  }
}

// ─── Patch to src/api-server.ts (caller integration) ────────────────────────
//
// Add this line near the top:
//
//   import { registerWireUpRoutes } from "./api/wire-up.js";
//
// Then, inside `handleRequest()`, BEFORE the `default:` arm of the existing
// switch/case (or after the entire switch, before the `} catch (err) {` block),
// insert:
//
//   if (await registerWireUpRoutes(req, res)) return;
//
// The function is idempotent and side-effect-free for paths it does not own.
// Order matters only when the host has a conflicting route — currently none.
