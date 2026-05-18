/**
 * L2 T9 — MCP tools.
 *
 * Three tools exposed to MCP clients (e.g. Claude Code, agents):
 *   - conflict_scan      → triggers a detection pass under current mode
 *   - conflict_list      → list audit rows by status
 *   - conflict_resolve   → write resolution (terminal status only)
 *
 * MCP write tools must be gated by `NOX_MCP_ALLOW_WRITES=1` per existing
 * pattern in nox-mem MCP server. `conflict_resolve` returns an
 * `mcp_write_disabled` error when the env var is unset.
 *
 * Tools return JSON payloads matching the HTTP API shapes for
 * consistency (see ../../api/conflict.ts).
 */

import type { DBHandle } from "../../lib/conflict/db.js";
import {
  getConflictById,
  listConflicts,
  updateConflictStatus,
} from "../../lib/conflict/audit-writer.js";
import { runConflictPass, resolveMode } from "../../lib/conflict/shadow.js";
import { collectEvidence } from "../../lib/conflict/evidence.js";
import type {
  ConflictMode,
  ConflictStatus,
  ResolutionInput,
  ResolutionKind,
} from "../../lib/conflict/types.js";

export interface ScanInput {
  min_confidence?: number;
  predicate_allowlist?: string[];
  mode_override?: ConflictMode;
}

export interface ListInput {
  status?: ConflictStatus;
  limit?: number;
}

export interface ResolveInput {
  id: number;
  kind: ResolutionKind;
  picked_relation_id?: number;
  merge_target?: string;
  notes?: string;
  actor?: string;
}

export interface ToolResult<T = unknown> {
  ok: boolean;
  data?: T;
  error?: string;
  /** Surface a structured detail object for clients to render. */
  detail?: Record<string, unknown>;
}

const VALID_STATUSES: ConflictStatus[] = [
  "open",
  "reviewed",
  "resolved_pick_one",
  "resolved_both_valid",
  "resolved_merged",
  "dismissed",
];

const VALID_KINDS: ResolutionKind[] = ["pick_one", "both_valid", "merged", "dismissed"];

export function conflict_scan(db: DBHandle, input: ScanInput = {}): ToolResult {
  // Honor mode env unless explicit override. `disabled` short-circuits to
  // a successful no-op with zero counts (predictable).
  const mode = input.mode_override ?? resolveMode();
  const effective = mode === "disabled" ? "shadow" : mode;
  const result = runConflictPass(
    db,
    {
      min_confidence: input.min_confidence,
      predicate_allowlist: input.predicate_allowlist,
    },
    effective,
  );
  return { ok: true, data: result };
}

export function conflict_list(db: DBHandle, input: ListInput = {}): ToolResult {
  const status = input.status ?? "open";
  if (!VALID_STATUSES.includes(status)) {
    return { ok: false, error: "invalid_status", detail: { value: status } };
  }
  const limit = clampInt(input.limit ?? 20, 1, 500);
  const rows = listConflicts(db, status, limit);
  return { ok: true, data: { count: rows.length, rows } };
}

export function conflict_resolve(
  db: DBHandle,
  input: ResolveInput,
  env: Record<string, string | undefined> = process.env,
): ToolResult {
  if (env.NOX_MCP_ALLOW_WRITES !== "1") {
    return {
      ok: false,
      error: "mcp_write_disabled",
      detail: { hint: "set NOX_MCP_ALLOW_WRITES=1 to enable MCP write tools" },
    };
  }
  if (!Number.isFinite(input.id) || input.id <= 0) {
    return { ok: false, error: "invalid_id" };
  }
  if (!VALID_KINDS.includes(input.kind)) {
    return { ok: false, error: "invalid_kind", detail: { value: input.kind } };
  }
  const actor = input.actor ?? "mcp";

  let resolution: ResolutionInput;
  switch (input.kind) {
    case "pick_one":
      if (input.picked_relation_id == null) {
        return { ok: false, error: "picked_relation_id_required" };
      }
      resolution = {
        status: "resolved_pick_one",
        resolution_kind: "pick_one",
        resolved_by: actor,
        picked_relation_id: input.picked_relation_id,
        notes: input.notes,
      };
      break;
    case "both_valid":
      resolution = {
        status: "resolved_both_valid",
        resolution_kind: "both_valid",
        resolved_by: actor,
        notes: input.notes,
      };
      break;
    case "merged":
      if (!input.merge_target) {
        return { ok: false, error: "merge_target_required" };
      }
      resolution = {
        status: "resolved_merged",
        resolution_kind: "merged",
        resolved_by: actor,
        merge_target: input.merge_target,
        notes: input.notes,
      };
      break;
    case "dismissed":
      resolution = {
        status: "dismissed",
        resolution_kind: "dismissed",
        resolved_by: actor,
        notes: input.notes,
      };
      break;
  }

  try {
    updateConflictStatus(db, input.id, resolution);
  } catch (err) {
    return {
      ok: false,
      error: "resolution_failed",
      detail: { message: (err as Error).message },
    };
  }
  const row = getConflictById(db, input.id);
  if (!row) return { ok: false, error: "conflict_not_found", detail: { id: input.id } };
  const conflict = {
    kind: row.kind,
    subject_entity_id: row.subject_entity_id,
    predicate: row.predicate,
    variants: row.variants,
  };
  const evidence = collectEvidence(db, conflict);
  return { ok: true, data: { row, evidence } };
}

function clampInt(n: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, Math.floor(n)));
}
