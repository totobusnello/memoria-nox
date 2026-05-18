/**
 * L2 T8 — HTTP API handlers.
 *
 * Endpoints (mounted on nox-mem-api at :18802):
 *   GET  /api/conflict?status=open&limit=20   → list audit rows
 *   GET  /api/conflict/:id                    → row + evidence
 *   POST /api/conflict/:id/resolve            → write resolution
 *
 * Implementation is framework-agnostic: pure handlers operating on
 * a `RequestInput` shape so they can be wired to Express, native http,
 * or tested directly. No external HTTP library imported.
 *
 * All responses are JSON. Errors return {error: ...} with HTTP status.
 */

import type { DBHandle } from "../lib/conflict/db.js";
import {
  getConflictById,
  listConflicts,
  updateConflictStatus,
} from "../lib/conflict/audit-writer.js";
import { collectEvidence } from "../lib/conflict/evidence.js";
import type {
  ConflictStatus,
  ResolutionInput,
  ResolutionKind,
} from "../lib/conflict/types.js";

export interface RequestInput {
  method: "GET" | "POST";
  path: string;                          // e.g. "/api/conflict" or "/api/conflict/42/resolve"
  query?: Record<string, string | undefined>;
  body?: unknown;
  /** Caller actor id — populated from session/auth middleware in production. */
  actor?: string;
}

export interface ApiResponse {
  status: number;
  body: unknown;
}

const VALID_STATUSES: ConflictStatus[] = [
  "open",
  "reviewed",
  "resolved_pick_one",
  "resolved_both_valid",
  "resolved_merged",
  "dismissed",
];

/**
 * Dispatch incoming request to the appropriate handler. Returns 404 when
 * the path does not match any conflict endpoint (caller can fall through
 * to other routes).
 */
export function dispatchConflictApi(
  db: DBHandle,
  req: RequestInput,
): ApiResponse {
  const { method, path } = req;

  if (method === "GET" && path === "/api/conflict") {
    return handleList(db, req);
  }
  const idMatch = /^\/api\/conflict\/(\d+)$/.exec(path);
  if (method === "GET" && idMatch) {
    return handleShow(db, Number(idMatch[1]));
  }
  const resolveMatch = /^\/api\/conflict\/(\d+)\/resolve$/.exec(path);
  if (method === "POST" && resolveMatch) {
    return handleResolve(db, Number(resolveMatch[1]), req);
  }
  return { status: 404, body: { error: "not_found", path } };
}

function handleList(db: DBHandle, req: RequestInput): ApiResponse {
  const statusParam = req.query?.status ?? "open";
  if (!VALID_STATUSES.includes(statusParam as ConflictStatus)) {
    return {
      status: 400,
      body: { error: "invalid_status", value: statusParam },
    };
  }
  const limitParam = req.query?.limit;
  let limit = 20;
  if (limitParam !== undefined) {
    const n = Number(limitParam);
    if (!Number.isFinite(n) || n <= 0 || n > 500) {
      return { status: 400, body: { error: "invalid_limit", value: limitParam } };
    }
    limit = n;
  }
  const rows = listConflicts(db, statusParam as ConflictStatus, limit);
  return { status: 200, body: { count: rows.length, rows } };
}

function handleShow(db: DBHandle, id: number): ApiResponse {
  const row = getConflictById(db, id);
  if (!row) return { status: 404, body: { error: "conflict_not_found", id } };
  const conflict = {
    kind: row.kind,
    subject_entity_id: row.subject_entity_id,
    predicate: row.predicate,
    variants: row.variants,
  };
  const evidence = collectEvidence(db, conflict);
  return { status: 200, body: { row, evidence } };
}

function handleResolve(db: DBHandle, id: number, req: RequestInput): ApiResponse {
  const row = getConflictById(db, id);
  if (!row) return { status: 404, body: { error: "conflict_not_found", id } };

  const body = req.body as
    | undefined
    | {
        kind?: string;
        picked_relation_id?: number;
        merge_target?: string;
        notes?: string;
      };

  if (!body || typeof body !== "object") {
    return { status: 400, body: { error: "missing_body" } };
  }
  const kind = body.kind;
  const VALID_KIND: ResolutionKind[] = ["pick_one", "both_valid", "merged", "dismissed"];
  if (!kind || !VALID_KIND.includes(kind as ResolutionKind)) {
    return { status: 400, body: { error: "invalid_kind", value: kind } };
  }
  const actor = req.actor ?? "api";

  let resolution: ResolutionInput;
  switch (kind as ResolutionKind) {
    case "pick_one":
      if (typeof body.picked_relation_id !== "number") {
        return { status: 400, body: { error: "picked_relation_id_required" } };
      }
      resolution = {
        status: "resolved_pick_one",
        resolution_kind: "pick_one",
        resolved_by: actor,
        picked_relation_id: body.picked_relation_id,
        notes: body.notes,
      };
      break;
    case "both_valid":
      resolution = {
        status: "resolved_both_valid",
        resolution_kind: "both_valid",
        resolved_by: actor,
        notes: body.notes,
      };
      break;
    case "merged":
      if (typeof body.merge_target !== "string" || body.merge_target === "") {
        return { status: 400, body: { error: "merge_target_required" } };
      }
      resolution = {
        status: "resolved_merged",
        resolution_kind: "merged",
        resolved_by: actor,
        merge_target: body.merge_target,
        notes: body.notes,
      };
      break;
    case "dismissed":
      resolution = {
        status: "dismissed",
        resolution_kind: "dismissed",
        resolved_by: actor,
        notes: body.notes,
      };
      break;
  }

  try {
    updateConflictStatus(db, id, resolution);
  } catch (err) {
    return { status: 409, body: { error: "resolution_failed", message: (err as Error).message } };
  }
  const updated = getConflictById(db, id);
  return { status: 200, body: { row: updated } };
}
