/**
 * src/lib/confidence/write-hooks.ts — write-side hooks for L3.
 *
 * Two responsibilities:
 *   1. applyConfidence(chunk, source) — set confidence + provenance on insert,
 *      driven by the IngestSource (entity-compiled / markdown / graphify / ...)
 *   2. applyConfidenceToRelation(rel, meta) — set kg_relations.confidence from
 *      the kg-extract extraction_metadata (already present in v19).
 *
 * Mapping from IngestSource → (confidence, provenance_kind) follows
 * spec §4a (routing table). Callers (ingest-router, kg-extract, consolidate,
 * crystallize) call this BEFORE persistence.
 *
 * Per spec §4 + §11, these hooks NEVER overwrite an existing explicit value —
 * cli-explicit takes precedence; legacy chunks with pre-set confidence pass
 * through untouched.
 */

import type {
  ChunkDataPartial,
  ChunkDataWithConfidence,
  ConfidenceConfig,
  ExtractionMetadata,
  IngestSource,
  ProvenanceKind,
  RelationDataWithConfidence,
} from "./types.js";
import { clamp01, resolveConfig } from "./config.js";

/** Returns (confidence, provenance_kind) tuple for the given ingest source. */
export function defaultsForSource(
  source: IngestSource,
  cfg: ConfidenceConfig
): { confidence: number; provenance_kind: ProvenanceKind | null } {
  switch (source) {
    case "entity-compiled":
    case "entity-frontmatter":
      return {
        confidence: cfg.default_declared,
        provenance_kind: "declared",
      };
    case "entity-timeline":
      return {
        confidence: cfg.default_observed,
        provenance_kind: "observed",
      };
    case "markdown":
      // Generic markdown → confidence 0.8 floor (legacy default), NULL kind.
      return { confidence: 0.8, provenance_kind: null };
    case "graphify":
      return {
        confidence: cfg.default_graphify,
        provenance_kind: "derived",
      };
    case "kg-extract":
      return {
        confidence: cfg.default_inferred,
        provenance_kind: "inferred",
      };
    case "consolidate":
      return {
        confidence: cfg.default_derived,
        provenance_kind: "derived",
      };
    case "crystallize":
      // crystallize produces summarised truth — slight bump over consolidate
      return {
        confidence: Math.min(cfg.default_derived + 0.1, 1.0),
        provenance_kind: "derived",
      };
    case "cli-explicit":
      // Caller MUST pass confidence + provenance via chunkData; we no-op here.
      return { confidence: 0.8, provenance_kind: null };
    default: {
      // Exhaustiveness check — never reach
      const _exhaustive: never = source;
      void _exhaustive;
      return { confidence: 0.8, provenance_kind: null };
    }
  }
}

/**
 * applyConfidence() — fills confidence + provenance on a chunk-data object.
 *
 * Behaviour:
 *   - If chunkData.confidence is ALREADY set (not undefined, not null), preserve it.
 *   - Otherwise use defaults from the IngestSource.
 *   - confidence is always clamp01'd as final guard.
 *
 * Returns a NEW object — never mutates input.
 */
export function applyConfidence(
  chunkData: ChunkDataPartial,
  source: IngestSource,
  cfgOverride?: ConfidenceConfig
): ChunkDataWithConfidence {
  const cfg = cfgOverride ?? resolveConfig();
  const defaults = defaultsForSource(source, cfg);

  const hasExplicitConf =
    chunkData.confidence !== undefined && chunkData.confidence !== null;
  const hasExplicitKind =
    chunkData.provenance_kind !== undefined &&
    chunkData.provenance_kind !== null;

  const confidence = clamp01(
    hasExplicitConf ? (chunkData.confidence as number) : defaults.confidence
  );
  const provenance_kind = hasExplicitKind
    ? (chunkData.provenance_kind as ProvenanceKind)
    : defaults.provenance_kind;

  return {
    ...chunkData,
    confidence,
    provenance_kind,
  };
}

/**
 * applyConfidenceToRelation() — fills confidence on a kg_relation insert.
 *
 * The v19 schema gives kg_relations.confidence DEFAULT 0.7. We override based
 * on the ExtractionMetadata that the kg-extract pipeline already produces:
 *
 *   - If meta.confidence is explicit, use it (clamped)
 *   - Else if extraction_method='frontmatter', confidence = default_declared (0.9)
 *   - Else if extraction_method='regex_only', confidence = 0.85 (regex deterministic)
 *   - Else if extraction_method='manual', confidence = 1.0
 *   - Else (gemini_only / regex_primary_gemini_secondary), default_inferred (0.65)
 *
 * provenance_kind: 'inferred' for LLM-extracted; 'observed' for manual or
 * regex_only (deterministic); 'declared' for frontmatter.
 */
export function applyConfidenceToRelation(
  meta: ExtractionMetadata = {},
  cfgOverride?: ConfidenceConfig
): RelationDataWithConfidence {
  const cfg = cfgOverride ?? resolveConfig();

  // Explicit confidence wins (clamped).
  if (typeof meta.confidence === "number" && Number.isFinite(meta.confidence)) {
    const c = clamp01(meta.confidence);
    return {
      confidence: c,
      extraction_method: meta.extraction_method,
      provenance_kind: pickProvenanceForMethod(meta.extraction_method),
    };
  }

  const method = meta.extraction_method;
  const section = meta.source_section;

  let confidence: number;
  let provenance_kind: ProvenanceKind;

  if (section === "frontmatter" || method === "frontmatter") {
    confidence = cfg.default_declared;
    provenance_kind = "declared";
  } else if (method === "manual") {
    confidence = 1.0;
    provenance_kind = "observed";
  } else if (method === "regex_only") {
    confidence = 0.85;
    provenance_kind = "observed";
  } else if (
    method === "gemini_only" ||
    method === "regex_primary_gemini_secondary"
  ) {
    confidence = cfg.default_inferred;
    provenance_kind = "inferred";
  } else {
    confidence = cfg.default_inferred;
    provenance_kind = "inferred";
  }

  return {
    confidence: clamp01(confidence),
    extraction_method: method,
    provenance_kind,
  };
}

function pickProvenanceForMethod(
  method: string | undefined
): ProvenanceKind {
  if (method === "frontmatter") return "declared";
  if (method === "manual") return "observed";
  if (method === "regex_only") return "observed";
  return "inferred";
}
