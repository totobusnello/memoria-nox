/**
 * src/mcp/tools/mark.ts — MCP tool definitions for L3 mark workflow.
 *
 * Two tools surfaced:
 *   chunk_mark(id, kind, notes?) → MarkResult
 *   chunk_supersede(id, by_id, notes?, reason?) → MarkResult
 *
 * MCP tool descriptors are returned by listMarkTools() so the main MCP server
 * can register them alongside its existing 16 tools.
 *
 * Spec ref: specs/2026-05-17-L3-confidence-field.md §7 (MCP).
 */

import type { Db } from "../../lib/confidence/db-shim.js";
import {
  markChunk,
  supersedeChunk,
} from "../../lib/confidence/mark.js";
import type {
  MarkKind,
  MarkResult,
  SupersedeReason,
} from "../../lib/confidence/types.js";
import { resolveConfig } from "../../lib/confidence/config.js";

export interface McpTool {
  name: string;
  description: string;
  inputSchema: {
    type: "object";
    properties: Record<string, unknown>;
    required: string[];
  };
}

export function listMarkTools(): McpTool[] {
  return [
    {
      name: "chunk_mark",
      description:
        "Mark a chunk as canonical (Toto-affirmed), refuted (Toto-negated), or stale (no longer trustworthy). Updates chunks.confidence + chunks.provenance_kind. Appends ops_audit row. Use when Toto reviews a fact and wants it elevated (canonical) or demoted (refuted/stale).",
      inputSchema: {
        type: "object",
        properties: {
          id: { type: "number", description: "Chunk id to mark." },
          kind: {
            type: "string",
            enum: ["canonical", "refuted", "stale"],
            description: "Mark kind. canonical=1.0 conf, refuted=0.05 conf, stale=conf unchanged but provenance=user-marked.",
          },
          notes: {
            type: "string",
            description: "Optional free-text note logged to ops_audit.details.",
          },
        },
        required: ["id", "kind"],
      },
    },
    {
      name: "chunk_supersede",
      description:
        "Mark a chunk as superseded by a newer chunk. Sets chunks.superseded_by FK. Useful when a fact has been replaced (e.g. 'gemini-2.5-flash → gemini-2.5-flash-lite as default model'). Older chunk remains in DB for audit; ranking integration de-prioritizes superseded chunks when NOX_RANKING_CONFIDENCE=active.",
      inputSchema: {
        type: "object",
        properties: {
          id: { type: "number", description: "Older chunk id (the one being replaced)." },
          by_id: {
            type: "number",
            description: "Newer chunk id (the one replacing it).",
          },
          notes: { type: "string", description: "Optional context." },
          reason: {
            type: "string",
            enum: [
              "auto_supersede_temporal",
              "manual_resolution",
              "stale_link_reconciliation",
              "dismiss",
            ],
            description:
              "Why this supersession is happening (mirrors kg_relations.superseded_reason).",
          },
        },
        required: ["id", "by_id"],
      },
    },
  ];
}

interface MarkInput {
  id: number;
  kind: MarkKind;
  notes?: string;
}

interface SupersedeInput {
  id: number;
  by_id: number;
  notes?: string;
  reason?: SupersedeReason;
}

export function callChunkMark(db: Db, input: MarkInput): MarkResult {
  return markChunk({
    db,
    chunk_id: input.id,
    kind: input.kind,
    notes: input.notes,
    cfg: resolveConfig(),
  });
}

export function callChunkSupersede(
  db: Db,
  input: SupersedeInput
): MarkResult {
  return supersedeChunk({
    db,
    chunk_id: input.id,
    by_chunk_id: input.by_id,
    notes: input.notes,
    reason: input.reason,
  });
}
