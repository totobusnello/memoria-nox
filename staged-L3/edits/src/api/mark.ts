/**
 * src/api/mark.ts — HTTP routes for L3 mark workflow.
 *
 * Routes:
 *   POST /api/chunk/:id/mark      body { kind: "canonical"|"refuted"|"stale", notes?: string }
 *   POST /api/chunk/:id/supersede body { by_chunk_id: number, notes?: string, reason?: string }
 *
 * Returns 200 + JSON on success, 400 on bad request, 404 on missing chunk,
 * 500 on unexpected.
 *
 * Framework-agnostic: exposes request/response handlers that take a minimal
 * Request shape. Production caller (Express/Fastify/native http) wires them
 * via `handleMarkRequest()` and `handleSupersedeRequest()`.
 */

import type { Db } from "../lib/confidence/db-shim.js";
import {
  markChunk,
  supersedeChunk,
} from "../lib/confidence/mark.js";
import type {
  MarkKind,
  MarkResult,
  SupersedeReason,
} from "../lib/confidence/types.js";
import { resolveConfig } from "../lib/confidence/config.js";

export interface ApiResponse<T = unknown> {
  status: number;
  body: T | { ok: false; error: string; code: string };
}

interface MarkBody {
  kind?: string;
  notes?: string;
}

interface SupersedeBody {
  by_chunk_id?: number;
  notes?: string;
  reason?: string;
}

function validateKind(raw: unknown): raw is MarkKind {
  return raw === "canonical" || raw === "refuted" || raw === "stale";
}

function validateReason(raw: unknown): raw is SupersedeReason {
  return (
    raw === "auto_supersede_temporal" ||
    raw === "manual_resolution" ||
    raw === "stale_link_reconciliation" ||
    raw === "dismiss"
  );
}

function parseChunkId(idStr: string): number | null {
  const id = parseInt(idStr, 10);
  if (!Number.isFinite(id) || id <= 0) return null;
  return id;
}

/**
 * handleMarkRequest(db, idStr, body) → ApiResponse<MarkResult>
 */
export function handleMarkRequest(
  db: Db,
  idStr: string,
  body: MarkBody | null | undefined
): ApiResponse<MarkResult> {
  const chunk_id = parseChunkId(idStr);
  if (chunk_id === null) {
    return {
      status: 400,
      body: { ok: false, error: `invalid chunk id: ${idStr}`, code: "bad_id" },
    };
  }
  if (!body || typeof body !== "object") {
    return {
      status: 400,
      body: { ok: false, error: "missing JSON body", code: "bad_body" },
    };
  }
  if (!validateKind(body.kind)) {
    return {
      status: 400,
      body: {
        ok: false,
        error: `invalid kind: ${String(body.kind)} — expected canonical|refuted|stale`,
        code: "bad_kind",
      },
    };
  }

  try {
    const result = markChunk({
      db,
      chunk_id,
      kind: body.kind,
      notes: body.notes,
      cfg: resolveConfig(),
    });
    return { status: 200, body: result };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    const status = /not found/i.test(msg) ? 404 : 500;
    return {
      status,
      body: { ok: false, error: msg, code: status === 404 ? "not_found" : "runtime" },
    };
  }
}

/**
 * handleSupersedeRequest(db, idStr, body) → ApiResponse<MarkResult>
 */
export function handleSupersedeRequest(
  db: Db,
  idStr: string,
  body: SupersedeBody | null | undefined
): ApiResponse<MarkResult> {
  const chunk_id = parseChunkId(idStr);
  if (chunk_id === null) {
    return {
      status: 400,
      body: { ok: false, error: `invalid chunk id: ${idStr}`, code: "bad_id" },
    };
  }
  if (!body || typeof body !== "object") {
    return {
      status: 400,
      body: { ok: false, error: "missing JSON body", code: "bad_body" },
    };
  }
  const by_chunk_id =
    typeof body.by_chunk_id === "number" ? body.by_chunk_id : NaN;
  if (!Number.isFinite(by_chunk_id) || by_chunk_id <= 0) {
    return {
      status: 400,
      body: {
        ok: false,
        error: `invalid by_chunk_id: ${String(body.by_chunk_id)}`,
        code: "bad_by_id",
      },
    };
  }
  const reason: SupersedeReason = validateReason(body.reason)
    ? body.reason
    : "manual_resolution";

  try {
    const result = supersedeChunk({
      db,
      chunk_id,
      by_chunk_id,
      notes: body.notes,
      reason,
    });
    return { status: 200, body: result };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    const status = /missing|not found/i.test(msg) ? 404 : 500;
    return {
      status,
      body: { ok: false, error: msg, code: status === 404 ? "not_found" : "runtime" },
    };
  }
}
