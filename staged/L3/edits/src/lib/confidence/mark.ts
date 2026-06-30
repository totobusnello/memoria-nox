/**
 * src/lib/confidence/mark.ts — core mark/supersede operations.
 *
 * All writes:
 *   1. Resolve target confidence + provenance_kind from MarkKind + cfg
 *   2. Update chunks SET confidence, provenance_kind, updated_at
 *   3. Append row to ops_audit (status='success' on success, 'failed' on error)
 *
 * ops_audit is append-only (CLAUDE.md regra #6 — DB trigger blocks DELETE/UPDATE
 * on terminal rows).
 *
 * Mark mapping (DB-level provenance_kind is single bucket 'user-marked' per
 * v19.sql; confidence differentiates intent):
 *   canonical → confidence = cfg.user_marked_canonical (1.0), kind = 'user-marked'
 *   refuted   → confidence = cfg.user_marked_refuted  (0.05), kind = 'user-marked'
 *   stale     → confidence = unchanged,                kind = 'user-marked'
 *               (we annotate the chunk as user-touched; supersession is separate)
 *
 * Caller is responsible for verifying the chunk exists before invoking;
 * markChunk() returns an error result if the row is missing.
 */

import type { Db } from "./db-shim.js";
import type {
  ConfidenceConfig,
  MarkKind,
  MarkResult,
  ProvenanceKind,
  SupersedeReason,
} from "./types.js";
import { resolveConfig } from "./config.js";

export interface MarkChunkArgs {
  db: Db;
  chunk_id: number;
  kind: MarkKind;
  notes?: string;
  cfg?: ConfidenceConfig;
  /** Override Date.now() for test determinism. */
  now?: () => number;
}

export interface SupersedeChunkArgs {
  db: Db;
  chunk_id: number;
  by_chunk_id: number;
  notes?: string;
  reason?: SupersedeReason;
  cfg?: ConfidenceConfig;
  now?: () => number;
}

interface ChunkRow {
  id: number;
  confidence: number;
  provenance_kind: ProvenanceKind | null;
  pain?: number;
  superseded_by?: number | null;
}

function nowIso(now: () => number): string {
  return new Date(now()).toISOString();
}

/** Compute target (confidence, provenance_kind) for a MarkKind. */
export function targetForMark(
  kind: MarkKind,
  existing: ChunkRow,
  cfg: ConfidenceConfig
): { confidence: number; provenance_kind: ProvenanceKind } {
  switch (kind) {
    case "canonical":
      return {
        confidence: cfg.user_marked_canonical,
        provenance_kind: "user-marked",
      };
    case "refuted":
      return {
        confidence: cfg.user_marked_refuted,
        provenance_kind: "user-marked",
      };
    case "stale":
      // Keep existing confidence but mark as user-touched; ranking integration
      // treats provenance_kind='user-marked' + low confidence as filterable.
      return {
        confidence: existing.confidence,
        provenance_kind: "user-marked",
      };
    default: {
      const _exhaustive: never = kind;
      void _exhaustive;
      throw new Error(`unknown mark kind: ${String(kind)}`);
    }
  }
}

/** Mark a chunk canonical / refuted / stale. Returns success or throws. */
export function markChunk(args: MarkChunkArgs): MarkResult {
  const cfg = args.cfg ?? resolveConfig();
  const now = args.now ?? Date.now;

  const existing = args.db
    .prepare("SELECT id, confidence, provenance_kind, pain, superseded_by FROM chunks WHERE id = ?")
    .get<ChunkRow>(args.chunk_id);

  if (!existing) {
    appendAudit(args.db, {
      op: `confidence-mark-${args.kind}`,
      status: "failed",
      details: JSON.stringify({
        chunk_id: args.chunk_id,
        reason: "chunk_not_found",
      }),
      now,
    });
    throw new Error(`chunk ${args.chunk_id} not found`);
  }

  const target = targetForMark(args.kind, existing, cfg);

  args.db
    .prepare(
      "UPDATE chunks SET confidence = ?, provenance_kind = ?, updated_at = ? WHERE id = ?"
    )
    .run(target.confidence, target.provenance_kind, nowIso(now), args.chunk_id);

  const auditId = appendAudit(args.db, {
    op: `confidence-mark-${args.kind}`,
    status: "success",
    details: JSON.stringify({
      chunk_id: args.chunk_id,
      kind: args.kind,
      before: {
        confidence: existing.confidence,
        provenance_kind: existing.provenance_kind,
      },
      after: target,
      notes: args.notes ?? null,
    }),
    now,
  });

  return {
    ok: true,
    chunk_id: args.chunk_id,
    applied: {
      confidence: target.confidence,
      provenance_kind: target.provenance_kind,
      superseded_by: existing.superseded_by ?? null,
    },
    audit_id: auditId,
  };
}

/** Supersede a chunk by pointing it to a newer one. */
export function supersedeChunk(args: SupersedeChunkArgs): MarkResult {
  const cfg = args.cfg ?? resolveConfig();
  void cfg; // not used directly but kept for future expansion (e.g., supersede policy)
  const now = args.now ?? Date.now;

  if (args.chunk_id === args.by_chunk_id) {
    appendAudit(args.db, {
      op: "confidence-supersede",
      status: "failed",
      details: JSON.stringify({
        chunk_id: args.chunk_id,
        reason: "self_supersede",
      }),
      now,
    });
    throw new Error(
      `cannot supersede chunk ${args.chunk_id} by itself`
    );
  }

  const existing = args.db
    .prepare("SELECT id, confidence, provenance_kind, pain, superseded_by FROM chunks WHERE id = ?")
    .get<ChunkRow>(args.chunk_id);
  const newer = args.db
    .prepare("SELECT id, confidence, provenance_kind, pain, superseded_by FROM chunks WHERE id = ?")
    .get<ChunkRow>(args.by_chunk_id);

  if (!existing || !newer) {
    appendAudit(args.db, {
      op: "confidence-supersede",
      status: "failed",
      details: JSON.stringify({
        chunk_id: args.chunk_id,
        by_chunk_id: args.by_chunk_id,
        reason: !existing ? "chunk_not_found" : "supersede_target_not_found",
      }),
      now,
    });
    throw new Error(
      `missing row(s) — chunk_id=${args.chunk_id} or by_chunk_id=${args.by_chunk_id}`
    );
  }

  args.db
    .prepare("UPDATE chunks SET superseded_by = ?, updated_at = ? WHERE id = ?")
    .run(args.by_chunk_id, nowIso(now), args.chunk_id);

  const auditId = appendAudit(args.db, {
    op: "confidence-supersede",
    status: "success",
    details: JSON.stringify({
      chunk_id: args.chunk_id,
      by_chunk_id: args.by_chunk_id,
      reason: args.reason ?? "manual_resolution",
      notes: args.notes ?? null,
    }),
    now,
  });

  return {
    ok: true,
    chunk_id: args.chunk_id,
    applied: {
      confidence: existing.confidence,
      provenance_kind: "user-marked",
      superseded_by: args.by_chunk_id,
    },
    audit_id: auditId,
  };
}

function appendAudit(
  db: Db,
  args: { op: string; status: string; details: string; now: () => number }
): number {
  const result = db
    .prepare(
      "INSERT INTO ops_audit (op, status, details, started_at) VALUES (?, ?, ?, ?)"
    )
    .run(args.op, args.status, args.details, nowIso(args.now));
  return Number(result.lastInsertRowid);
}
