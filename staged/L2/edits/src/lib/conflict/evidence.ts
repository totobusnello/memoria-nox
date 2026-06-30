/**
 * L2 T4 — Evidence collector.
 *
 * Joins kg_relations.evidence_chunk_id → chunks.*, returning a ranked evidence
 * bundle per conflict. Used by:
 *   - audit-writer (variants serialized into conflict_audit.variants JSON)
 *   - CLI `conflict show <id>`
 *   - HTTP `GET /api/conflict/:id`
 *
 * Ranking heuristic — within a single conflict, variants are returned in
 * (a) created_at DESC (recency) then (b) confidence DESC — newer + higher
 * confidence first. The weighted_score is informational: avg(relation.conf,
 * chunk.conf) — surfaces "does the chunk back up the relation's confidence?"
 *
 * Snippet is truncated to DEFAULT_EVIDENCE_SNIPPET_LEN with an ellipsis marker.
 * Caller can request full content via chunk_id lookup.
 */

import type { DBHandle } from "./db.js";
import {
  DEFAULT_EVIDENCE_SNIPPET_LEN,
  type Conflict,
  type ConflictEvidence,
  type EvidenceChunk,
  type VariantEvidence,
} from "./types.js";

interface ChunkRow {
  id: number;
  content: string;
  ts: number;
  source_session_id: string | null;
  confidence: number | null;
  provenance_kind: string | null;
}

export interface CollectEvidenceOptions {
  /** Snippet length cap. Default DEFAULT_EVIDENCE_SNIPPET_LEN (320). */
  snippet_len?: number;
}

export function collectEvidence(
  db: DBHandle,
  conflict: Conflict,
  opts: CollectEvidenceOptions = {},
): ConflictEvidence {
  const snippetLen = opts.snippet_len ?? DEFAULT_EVIDENCE_SNIPPET_LEN;
  if (snippetLen <= 0) {
    throw new RangeError(`snippet_len must be > 0: ${snippetLen}`);
  }

  // Sort variants for stable display order.
  const sorted = [...conflict.variants].sort((a, b) => {
    if (b.created_at !== a.created_at) return b.created_at - a.created_at;
    return b.confidence - a.confidence;
  });

  const variants: VariantEvidence[] = sorted.map((v) => {
    const chunks: EvidenceChunk[] = [];
    if (v.evidence_chunk_id != null) {
      // Single-id IN clause — fake & real both accept this shape.
      const rows = db
        .prepare(
          `SELECT id, content, ts, source_session_id, confidence, provenance_kind FROM chunks WHERE id = ?`,
        )
        .all(v.evidence_chunk_id) as ChunkRow[];
      for (const r of rows) {
        chunks.push({
          chunk_id: r.id,
          snippet: snippet(r.content, snippetLen),
          full_length: r.content?.length ?? 0,
          ts: r.ts,
          source_session_id: r.source_session_id,
          chunk_confidence: r.confidence,
          provenance_kind: r.provenance_kind,
        });
      }
    }

    // weighted_score: avg of relation + chunk confidence (or relation alone if no chunk)
    let weighted = v.confidence;
    if (chunks.length > 0) {
      const chunkConfs = chunks
        .map((c) => c.chunk_confidence ?? null)
        .filter((c): c is number => c != null);
      if (chunkConfs.length > 0) {
        const avg = chunkConfs.reduce((a, b) => a + b, 0) / chunkConfs.length;
        weighted = (v.confidence + avg) / 2;
      }
    }

    return { variant: v, chunks, weighted_score: weighted };
  });

  return {
    conflict_subject_entity_id: conflict.subject_entity_id,
    predicate: conflict.predicate,
    variants,
  };
}

function snippet(content: string | null | undefined, max: number): string {
  if (!content) return "";
  // Collapse whitespace for a clean snippet — the original chunk is intact in DB.
  const flat = content.replace(/\s+/g, " ").trim();
  if (flat.length <= max) return flat;
  return flat.slice(0, max - 1).trimEnd() + "…";
}
