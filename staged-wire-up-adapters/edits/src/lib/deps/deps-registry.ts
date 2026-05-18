/**
 * src/lib/deps/deps-registry.ts — Central singleton resolver for wire-up adapters.
 *
 * Wave O (close-the-503-gap) needs five adapter modules (P1/A2/P5/L2-L3/P2)
 * to share three runtime dependencies:
 *
 *   1. Better-sqlite3 Database handle (nox-mem.db)
 *   2. Gemini provider (already used elsewhere in the codebase)
 *   3. Event bus / broadcaster singleton for SSE
 *
 * Goals (regra de ouro #2 — "Single DB connection"):
 *
 *   - One Database instance per process. All adapters acquire via `getDb()`.
 *   - Lazy initialization. Importing this module does not open the file.
 *   - Test-friendly. `resetDepsRegistryForTests()` flushes all singletons so
 *     `node --test` runs do not bleed state between cases.
 *   - Soft-fail. If better-sqlite3 isn't installed in the staged sandbox, the
 *     resolver returns `null` instead of throwing — the wire-up router maps
 *     null → 503 not_implemented (same pattern as before).
 *
 * Production wiring path:
 *   `/root/.openclaw/workspace/tools/nox-mem/dist/lib/deps/deps-registry.js`
 *   resolves NOX_DB_PATH from env (default
 *   `${OPENCLAW_WORKSPACE}/data/nox-mem.db`), opens better-sqlite3 with
 *   `readonly:false`, sets `journal_mode=WAL`. Same lifecycle the existing
 *   `nox-mem` CLI uses (see entity_file_format memory note).
 *
 * Why a registry instead of per-pillar singletons:
 *   - Avoids duplicate DB handles (one per pillar = N WAL writers, race).
 *   - Centralizes env reads so misconfig fails fast at first acquisition.
 *   - Lets tests swap the DB factory once (`__setDbFactoryForTests`) and have
 *     all five adapters honor the override.
 */

import { resolve as pathResolve } from "node:path";

// ─── Public types ────────────────────────────────────────────────────────────

/**
 * Structural Database type. Matches the better-sqlite3 surface used across
 * staged dirs (`DBHandle` in L2, `Db` in L3, the orchestrator types in A2).
 * Keeping the shim here avoids a hard `better-sqlite3` dep on the test path.
 */
export interface DbHandle {
  prepare(sql: string): {
    run(...params: unknown[]): { changes: number; lastInsertRowid: number | bigint };
    get<T = unknown>(...params: unknown[]): T | undefined;
    all<T = unknown>(...params: unknown[]): T[];
    iterate?<T = unknown>(...params: unknown[]): Iterable<T>;
  };
  exec(sql: string): void;
  transaction?<T extends (...args: any[]) => any>(fn: T): T;
  pragma?(sql: string, opts?: { simple?: boolean }): unknown;
  close?(): void;
}

export interface GeminiProvider {
  /** Identifier — e.g. "gemini-2.5-flash-lite". */
  model: string;
  /** Generate text completion. Returns {text, tokensIn, tokensOut, model}. */
  complete(opts: {
    system?: string;
    user: string;
    maxTokens?: number;
    temperature?: number;
  }): Promise<{
    text: string;
    tokensIn: number;
    tokensOut: number;
    model: string;
  }>;
}

export interface EventBus {
  /**
   * Subscribe to event envelopes. Returns an unsubscribe function.
   * The provider is opaque here; viewer-static + events-stream use it via
   * the staged-P5 `Broadcaster` directly.
   */
  publish(ev: unknown): unknown;
  addClient(id: string, notify: () => void, lastEventId?: number): unknown;
  removeClient(id: string): void;
  ringSnapshot(): readonly unknown[];
  clientCount(): number;
}

// ─── Internals (singletons + factory seams) ──────────────────────────────────

type DbFactory = () => DbHandle | null;
type ProviderFactory = () => GeminiProvider | null;
type EventBusFactory = () => EventBus | null;

let _db: DbHandle | null | undefined;
let _provider: GeminiProvider | null | undefined;
let _bus: EventBus | null | undefined;

let _dbFactory: DbFactory | null = null;
let _providerFactory: ProviderFactory | null = null;
let _eventBusFactory: EventBusFactory | null = null;

/** Resolve nox-mem.db path from env, falling back to the canonical VPS path.
 *
 * Path layout matches `src/db.ts` source of truth: workspace `${OPENCLAW_WORKSPACE}`
 * + `tools/nox-mem/nox-mem.db`. The previous `data/nox-mem.db` fallback was an
 * artifact of the staged-wire-up-adapters spec mismatch; it created an empty
 * DB at a non-existent path → `/api/conflict` returned 503 "L2 db not available"
 * because conflict_audit table didn't exist in the orphan DB. Lesson 2026-05-18.
 */
export function resolveDbPath(): string {
  // Test-override channel (avoids touching prod paths during `node --test`).
  if (process.env["NOX_DB_PATH"]) return process.env["NOX_DB_PATH"];
  const workspace = process.env["OPENCLAW_WORKSPACE"];
  if (workspace) return pathResolve(workspace, "tools/nox-mem/nox-mem.db");
  // Final fallback (VPS canonical layout — matches src/db.ts).
  return "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db";
}

/** Default DB factory — tries better-sqlite3, soft-fails when missing. */
async function defaultDbFactory(): Promise<DbHandle | null> {
  try {
    // Dynamic import keeps the staged dir installable without runtime deps.
    // String indirection — `better-sqlite3` is a peer dep on prod, not part
    // of the staged-wire-up-adapters devDependencies.
    const BSQLITE_SPEC = "better-sqlite3";
    const mod: any = await import(BSQLITE_SPEC);
    const Database = mod.default ?? mod;
    const path = resolveDbPath();
    const handle = new Database(path);
    if (typeof handle.pragma === "function") {
      try {
        handle.pragma("journal_mode = WAL");
      } catch {
        // pragma failures are non-fatal — some test DBs reject WAL.
      }
    }
    return handle as DbHandle;
  } catch {
    return null;
  }
}

/**
 * Default Gemini provider — sources GEMINI_API_KEY + GEMINI_MODEL.
 * When the key is missing OR `@google/generative-ai` isn't installed,
 * returns `null` so adapters fall through to the 503 path.
 */
async function defaultProviderFactory(): Promise<GeminiProvider | null> {
  const key = process.env["GEMINI_API_KEY"];
  if (!key) return null;
  const modelName =
    process.env["GEMINI_MODEL"] ?? "gemini-2.5-flash-lite";
  try {
    // String indirection — `@google/generative-ai` is a runtime dep on prod.
    const GEMINI_SPEC = "@google/generative-ai";
    const mod: any = await import(GEMINI_SPEC);
    const ctor = mod.GoogleGenerativeAI ?? mod.default?.GoogleGenerativeAI;
    if (!ctor) return null;
    const client = new ctor(key);
    return {
      model: modelName,
      async complete(opts) {
        const model = client.getGenerativeModel({ model: modelName });
        const prompt = opts.system
          ? `${opts.system}\n\n${opts.user}`
          : opts.user;
        const result = await model.generateContent({
          contents: [{ role: "user", parts: [{ text: prompt }] }],
          generationConfig: {
            maxOutputTokens: opts.maxTokens ?? 2048,
            temperature: opts.temperature ?? 0.2,
          },
        });
        const text = result?.response?.text?.() ?? "";
        const usage = result?.response?.usageMetadata ?? {};
        return {
          text,
          tokensIn: usage.promptTokenCount ?? 0,
          tokensOut: usage.candidatesTokenCount ?? 0,
          model: modelName,
        };
      },
    };
  } catch {
    return null;
  }
}

/**
 * Default event bus factory — wraps staged-P5 Broadcaster when present.
 * Returns null when the viewer module isn't deployed (503-fallback path).
 */
async function defaultEventBusFactory(): Promise<EventBus | null> {
  try {
    // String indirection — `../viewer/broadcast.js` is co-located only
    // after staged-P5 is rsynced.
    const BROADCAST_SPEC = "../viewer/broadcast.js";
    const mod: any = await import(BROADCAST_SPEC);
    const Broadcaster = mod.Broadcaster;
    if (!Broadcaster) return null;
    return new Broadcaster() as EventBus;
  } catch {
    return null;
  }
}

// ─── Public API ──────────────────────────────────────────────────────────────

/**
 * Acquire (and cache) the process-wide DB handle.
 * Returns null when better-sqlite3 is unavailable (staged-dir-only mode).
 */
export async function getDb(): Promise<DbHandle | null> {
  if (_db !== undefined) return _db;
  if (_dbFactory) {
    _db = _dbFactory();
    return _db ?? null;
  }
  _db = await defaultDbFactory();
  return _db ?? null;
}

/**
 * Acquire the cached Gemini provider, or null when GEMINI_API_KEY is unset.
 */
export async function getProvider(): Promise<GeminiProvider | null> {
  if (_provider !== undefined) return _provider;
  if (_providerFactory) {
    _provider = _providerFactory();
    return _provider ?? null;
  }
  _provider = await defaultProviderFactory();
  return _provider ?? null;
}

/**
 * Acquire the cached EventBus (Broadcaster instance).
 */
export async function getEventBus(): Promise<EventBus | null> {
  if (_bus !== undefined) return _bus;
  if (_eventBusFactory) {
    _bus = _eventBusFactory();
    return _bus ?? null;
  }
  _bus = await defaultEventBusFactory();
  return _bus ?? null;
}

// ─── Test seams ──────────────────────────────────────────────────────────────

/**
 * Replace the DB factory. Pass `null` to clear (re-enable default factory).
 * Internal — wire-up adapter tests use this to inject fakes.
 */
export function __setDbFactoryForTests(fn: DbFactory | null): void {
  _dbFactory = fn;
  _db = undefined;
}

export function __setProviderFactoryForTests(fn: ProviderFactory | null): void {
  _providerFactory = fn;
  _provider = undefined;
}

export function __setEventBusFactoryForTests(fn: EventBusFactory | null): void {
  _eventBusFactory = fn;
  _bus = undefined;
}

/** Drop every singleton + clear factories. Use in `beforeEach` of test suites. */
export function resetDepsRegistryForTests(): void {
  _db = undefined;
  _provider = undefined;
  _bus = undefined;
  _dbFactory = null;
  _providerFactory = null;
  _eventBusFactory = null;
}
