/**
 * T8 — Client ID + session tracking
 *
 * Each SSE connection gets a UUIDv4 client_id (or accepts one from header
 * `X-Viewer-Client-Id` / cookie `nox_viewer_id`). A session row is opened
 * in `viewer_telemetry` on connect and finalized on disconnect.
 *
 * The actual DB write is delegated to a `SessionStore` interface so this
 * module stays decoupled from the storage layer. The default in-memory
 * store is suitable for tests and unit-test environments.
 */

import { randomUUID } from "node:crypto";
import { nowIso } from "./event-types.js";

export interface ViewerSessionRow {
  id?: number;
  client_id: string;
  ts_start: string;
  ts_last_event: string | null;
  ts_end: string | null;
  events_consumed: number;
  events_dropped: number;
  remote_label: string | null;
}

export interface SessionStore {
  open(row: Omit<ViewerSessionRow, "id">): Promise<number>;
  update(id: number, patch: Partial<ViewerSessionRow>): Promise<void>;
  close(id: number, patch: Partial<ViewerSessionRow>): Promise<void>;
  list(): Promise<readonly ViewerSessionRow[]>;
}

export class InMemorySessionStore implements SessionStore {
  private rows: ViewerSessionRow[] = [];

  async open(row: Omit<ViewerSessionRow, "id">): Promise<number> {
    const id = this.rows.length + 1;
    this.rows.push({ ...row, id });
    return id;
  }

  async update(id: number, patch: Partial<ViewerSessionRow>): Promise<void> {
    const row = this.rows.find((r) => r.id === id);
    if (row) Object.assign(row, patch);
  }

  async close(id: number, patch: Partial<ViewerSessionRow>): Promise<void> {
    const row = this.rows.find((r) => r.id === id);
    if (row) Object.assign(row, patch, { ts_end: nowIso() });
  }

  async list(): Promise<readonly ViewerSessionRow[]> {
    return this.rows.slice();
  }
}

// ─── Client id extraction / minting ─────────────────────────────────────────

export interface ClientIdSources {
  headerXViewer?: string;
  cookieHeader?: string;
}

const COOKIE_NAME = "nox_viewer_id";

export function extractClientId(src: ClientIdSources): string | null {
  if (src.headerXViewer && isValidUuid(src.headerXViewer)) {
    return src.headerXViewer;
  }
  if (src.cookieHeader) {
    const parts = src.cookieHeader.split(/;\s*/);
    for (const p of parts) {
      const [k, v] = p.split("=");
      if (k === COOKIE_NAME && v && isValidUuid(v)) return v;
    }
  }
  return null;
}

export function mintClientId(): string {
  return randomUUID();
}

export function clientIdCookie(id: string, maxAgeSec = 86400): string {
  return `${COOKIE_NAME}=${id}; Max-Age=${maxAgeSec}; Path=/; SameSite=Lax; HttpOnly`;
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function isValidUuid(s: string): boolean {
  return UUID_RE.test(s);
}

// ─── Session lifecycle helpers ──────────────────────────────────────────────

export interface SessionContext {
  rowId: number;
  client_id: string;
  events_consumed: number;
  events_dropped: number;
}

export async function openSession(
  store: SessionStore,
  client_id: string,
  remote_label: string | null = null
): Promise<SessionContext> {
  const row: Omit<ViewerSessionRow, "id"> = {
    client_id,
    ts_start: nowIso(),
    ts_last_event: null,
    ts_end: null,
    events_consumed: 0,
    events_dropped: 0,
    remote_label,
  };
  const rowId = await store.open(row);
  return { rowId, client_id, events_consumed: 0, events_dropped: 0 };
}

export async function recordEvent(
  store: SessionStore,
  ctx: SessionContext,
  droppedDelta = 0
): Promise<void> {
  ctx.events_consumed += 1;
  ctx.events_dropped += droppedDelta;
  await store.update(ctx.rowId, {
    ts_last_event: nowIso(),
    events_consumed: ctx.events_consumed,
    events_dropped: ctx.events_dropped,
  });
}

export async function closeSession(
  store: SessionStore,
  ctx: SessionContext
): Promise<void> {
  await store.close(ctx.rowId, {
    events_consumed: ctx.events_consumed,
    events_dropped: ctx.events_dropped,
  });
}
