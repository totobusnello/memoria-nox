/**
 * L2 conflict-detection — shared types.
 *
 * Cross-ref: specs/2026-05-17-L2-conflict-detection.md §2 (conflict types) + §3 (schema).
 *
 * v1 scope: ConflictKind='direct' end-to-end. 'temporal_supersede' gated on schema
 * (kg_relations.created_at present from v19). 'value_drift' and 'multi_target'
 * are forward-looking — accepted by schema CHECK but not produced by the v1 detector.
 *
 * **Iron law**: v1 NEVER mutates kg_relations. All resolution is recorded in
 * conflict_audit (append-only, see types.ConflictStatus). Caller may, separately
 * and explicitly, choose to call kg-relations APIs to mark superseded — but that
 * flow is OUT of scope for L2 T1-T12.
 */

/** Conflict taxonomy (matches conflict_audit.kind CHECK constraint). */
export type ConflictKind =
  | "direct"               // (subject, predicate) → N distinct targets, all active, predicate functional
  | "temporal_supersede"   // direct + predicate temporal-natured + clear newer/older ordering
  | "value_drift"          // scalar object that drifted over time (e.g. confidence decay)
  | "multi_target";        // direct contradiction where >2 targets — surfaces uncertainty

/** Audit-row lifecycle (matches conflict_audit.status CHECK constraint). */
export type ConflictStatus =
  | "open"                  // freshly detected, awaiting human review
  | "reviewed"              // analyst inspected, no resolution recorded yet
  | "resolved_pick_one"     // analyst picked one canonical relation
  | "resolved_both_valid"   // analyst confirmed both relations correct (multi-role entity)
  | "resolved_merged"       // analyst merged into a new canonical target (audit-only; v1 does NOT mutate kg_relations)
  | "dismissed";            // analyst flagged false positive

/** Resolution flavor stored on terminal rows. */
export type ResolutionKind =
  | "pick_one"
  | "both_valid"
  | "merged"
  | "dismissed";

/** Extraction provenance — propagated from kg_relations.extraction_method. */
export type ExtractionMethod =
  | "regex_only"
  | "gemini_only"
  | "regex_primary_gemini_secondary"
  | "frontmatter"
  | "manual";

/** Detector mode selector (NOX_CONFLICT_MODE env var). */
export type ConflictMode = "disabled" | "shadow" | "active";

/** Single relation involved in a conflict — snapshot at detection time. */
export interface VariantRelation {
  relation_id: number;
  target_entity_id: number;
  /** Optional human label for target entity (joined from kg_entities if available). */
  target_label?: string;
  confidence: number;
  extraction_method?: ExtractionMethod | null;
  evidence_chunk_id?: number | null;
  created_at: number;          // epoch_ms
  /** True when this relation was previously touched by a human resolve (immutable per §6.3). */
  user_marked?: boolean;
}

/** Detected conflict (in-memory, pre-audit). */
export interface Conflict {
  /** Always undefined until persisted by audit-writer.recordConflict(). */
  id?: number;
  kind: ConflictKind;
  /** Subject entity id (kg_entities.id). */
  subject_entity_id: number;
  /** Optional human label for subject — convenience for display, joined when available. */
  subject_label?: string;
  predicate: string;
  variants: VariantRelation[];
  /** epoch_ms — when the detector scan ran. Defaults to NOW. */
  detected_at?: number;
}

/** Audit-row shape (matches conflict_audit table columns). */
export interface ConflictAuditRow {
  id: number;
  ts: number;
  kind: ConflictKind;
  subject_entity_id: number;
  predicate: string;
  /** Parsed from JSON storage. */
  target_relation_ids: number[];
  /** Parsed from JSON storage. */
  variants: VariantRelation[];
  status: ConflictStatus;
  resolved_by: string | null;
  resolved_at: number | null;
  resolution_kind: ResolutionKind | null;
  picked_relation_id: number | null;
  merge_target: string | null;
  notes: string | null;
  shadow_mode: 0 | 1;
}

/** Evidence chunk attached to a variant relation (joined from chunks table). */
export interface EvidenceChunk {
  chunk_id: number;
  /** Short snippet (≤320 chars) of the chunk content. */
  snippet: string;
  /** Full content length (caller can decide to render full). */
  full_length: number;
  ts: number;
  source_session_id?: string | null;
  /** Chunk-level confidence (chunks.confidence, v19). */
  chunk_confidence?: number | null;
  provenance_kind?: string | null;
}

/** Evidence bundle: one variant + its supporting chunks. */
export interface VariantEvidence {
  variant: VariantRelation;
  chunks: EvidenceChunk[];
  /** Aggregate score combining relation.confidence + chunk.confidence (avg) — informational. */
  weighted_score: number;
}

/** Full evidence record for a conflict. */
export interface ConflictEvidence {
  conflict_subject_entity_id: number;
  predicate: string;
  variants: VariantEvidence[];
}

/** Detector options. */
export interface DetectorOptions {
  /**
   * Minimum confidence floor for a relation to be considered "active" by the detector.
   * Default 0.5 (spec §3 — don't surface low-confidence noise).
   */
  min_confidence?: number;
  /** Allowlist of predicates to scan (overrides blocklist). */
  predicate_allowlist?: string[];
  /** Blocklist of predicates (ignored). */
  predicate_blocklist?: string[];
  /** Maximum conflicts to return (0 = unlimited). */
  limit?: number;
  /**
   * Optional weighting bias for extraction_method.
   * Defaults to 1.0 for all methods (no bias).
   * Use {regex_only: 1.1, gemini_only: 0.9} to favor deterministic regex picks.
   */
  extraction_method_weights?: Partial<Record<ExtractionMethod, number>>;
  /** epoch_ms — record this as detected_at on resulting conflicts. Defaults to NOW. */
  scan_ts?: number;
}

/** Resolution input passed to audit-writer.updateConflictStatus(). */
export interface ResolutionInput {
  status: Exclude<ConflictStatus, "open" | "reviewed">;
  resolved_by: string;          // user id or 'system'
  resolution_kind: ResolutionKind;
  picked_relation_id?: number;
  merge_target?: string;
  notes?: string;
}

/** Constants — defaults referenced across modules. */
export const DEFAULT_MIN_CONFIDENCE = 0.5;
export const DEFAULT_SCAN_LIMIT = 500;
export const DEFAULT_EVIDENCE_SNIPPET_LEN = 320;
export const DEFAULT_CONFLICT_MODE: ConflictMode = "disabled";
