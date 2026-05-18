/**
 * src/lib/confidence/types.ts — Public interfaces for L3 confidence + provenance.
 *
 * Schema reference: staged-migrations/v19.sql
 *   - chunks.confidence       REAL DEFAULT 0.8 CHECK (0..1)
 *   - chunks.provenance_kind  TEXT CHECK IN ('observed','declared','inferred','derived','user-marked') OR NULL
 *   - kg_relations.confidence REAL DEFAULT 0.7
 *   - kg_relations.superseded_by_relation_id INTEGER FK
 *   - kg_relations.superseded_at INTEGER (epoch_ms)
 *   - kg_relations.superseded_reason TEXT
 *   - kg_relations.created_at / updated_at INTEGER (epoch_ms)
 *   - kg_relations.extraction_method TEXT
 *
 * Spec reference: specs/2026-05-17-L3-confidence-field.md
 *
 * NB: The DB-level `user-marked` provenance is a SINGLE bucket; CLI exposes
 * three sub-variants (canonical / refuted / stale) via different
 * (confidence, provenance_kind) tuples — see write-hooks.ts and mark.ts.
 */

/** DB-level provenance enum (matches CHECK constraint in v19.sql). */
export type ProvenanceKind =
  | "observed"
  | "declared"
  | "inferred"
  | "derived"
  | "user-marked";

/** Ingest-source enum — driver for write-side defaults. */
export type IngestSource =
  | "entity-compiled"
  | "entity-frontmatter"
  | "entity-timeline"
  | "markdown"
  | "graphify"
  | "kg-extract"
  | "consolidate"
  | "crystallize"
  | "cli-explicit";

/** Mark-workflow operations available via CLI / HTTP / MCP. */
export type MarkKind = "canonical" | "refuted" | "stale";

/** Ranking integration mode — defaults to "disabled" per CLAUDE.md regra #5. */
export type RankingMode = "disabled" | "shadow" | "active";

/** Reason recorded when a chunk supersedes another (mirrors kg_relations.superseded_reason). */
export type SupersedeReason =
  | "auto_supersede_temporal"
  | "manual_resolution"
  | "stale_link_reconciliation"
  | "dismiss";

/** Resolved configuration object (post env merge). */
export interface ConfidenceConfig {
  /** Default confidence for observed chunks (witnessed/recorded). */
  default_observed: number;
  /** Default confidence for declared chunks (frontmatter/compiled truth). */
  default_declared: number;
  /** Default confidence for inferred chunks (LLM-extracted). */
  default_inferred: number;
  /** Default confidence for derived chunks (consolidate/crystallize). */
  default_derived: number;
  /** Default confidence for graphify-generated chunks. */
  default_graphify: number;
  /** Value applied to user_marked_canonical chunks. */
  user_marked_canonical: number;
  /** Value applied to user_marked_refuted chunks. */
  user_marked_refuted: number;
  /** Floor below which chunks are filtered out when ranking mode=active. */
  active_floor: number;
  /** Ranking integration mode. */
  ranking_mode: RankingMode;
  /** Optional half-life decay window (days). Disabled in v1 (-1). */
  decay_halflife_days: number;
}

/** Input for write-side hooks — minimal chunk shape produced by ingest. */
export interface ChunkDataPartial {
  /** Optional pre-existing confidence (rare; cli-explicit only). */
  confidence?: number;
  /** Optional pre-existing provenance kind. */
  provenance_kind?: ProvenanceKind | null;
  /** Pain field (used by ranking integration, decay rule). */
  pain?: number;
  /** Section field (already in schema v10). */
  section?: string | null;
}

/** Output of applyConfidence() — chunk with confidence + provenance set. */
export interface ChunkDataWithConfidence extends ChunkDataPartial {
  confidence: number;
  provenance_kind: ProvenanceKind | null;
}

/** Extraction-metadata input from kg-extract pipeline. */
export interface ExtractionMetadata {
  /** Confidence the LLM/regex extractor assigned. */
  confidence?: number;
  /** Extraction method (regex_only, gemini_only, ...). */
  extraction_method?: string;
  /** Whether this relation came from frontmatter (high-trust path). */
  source_section?: "frontmatter" | "compiled" | "timeline" | "body";
}

/** Output for applyConfidenceToRelation(). */
export interface RelationDataWithConfidence {
  confidence: number;
  extraction_method?: string;
  provenance_kind: ProvenanceKind;
}

/** Mark-operation request shape. */
export interface MarkOpts {
  /** Chunk id to mark. */
  chunk_id: number;
  /** Kind of mark. */
  kind: MarkKind;
  /** Optional free-text note (logged to ops_audit). */
  notes?: string;
}

/** Supersede-operation request shape. */
export interface SupersedeOpts {
  /** Older chunk being superseded. */
  chunk_id: number;
  /** Newer chunk that replaces it. */
  by_chunk_id: number;
  /** Optional reason text. */
  notes?: string;
}

/** Result of a mark/supersede write — returned to API/CLI/MCP layer. */
export interface MarkResult {
  ok: true;
  chunk_id: number;
  applied: {
    confidence: number;
    provenance_kind: ProvenanceKind;
    superseded_by?: number | null;
  };
  audit_id: number;
}

/** Telemetry slice exposed on /api/health. */
export interface ConfidenceHealthSlice {
  provenance: {
    observed: number;
    declared: number;
    inferred: number;
    derived: number;
    "user-marked": number;
    null: number;
  };
  confidence_distribution: {
    mean: number;
    p25: number;
    p50: number;
    p75: number;
    p95: number;
    stddev: number;
  };
  superseded_count: number;
  ranking_mode: RankingMode;
}

/** Eval result delta-row stored in confidence_eval_log table (v22). */
export interface ConfidenceEvalDelta {
  /** Query id from golden set (e.g., "GS-042"). */
  query_id: string;
  /** Variant label: 'A','B','C','D' (see spec §6). */
  variant: "A" | "B" | "C" | "D";
  /** nDCG@10 score for this run. */
  ndcg_at_10: number;
  /** Delta vs baseline A (0 for variant A itself). */
  delta_vs_baseline: number;
  /** ISO timestamp when run captured. */
  ran_at: string;
}
