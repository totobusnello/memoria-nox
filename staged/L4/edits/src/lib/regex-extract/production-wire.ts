/**
 * T9 — Production wire-up: regex extractor as FAST-PATH before LLM extraction.
 *
 * Hooks the regex extractor into the existing `ingestFile()` pipeline as a
 * fast-path check BEFORE calling Gemini for KG extraction.
 *
 * Decision rule (spec §7 + T9):
 *   If regex extraction confidence ≥ CONFIDENCE_THRESHOLD (0.8):
 *     - Typed link from frontmatter (is_agent_of, supersedes, etc.) → confidence=0.95
 *     - Explicit [[wikilink]] or [md-link](slug) → confidence=0.90
 *     - Bare ref `entityType/slug` → confidence=0.75 (below threshold → falls through)
 *     → SKIP Gemini for this chunk
 *   Else:
 *     → Fall through to LLM (existing path)
 *
 * Telemetry: `extraction_method` logged per kg_relations row.
 *
 * This module is a pure adapter — it wraps `decideExtraction` with the
 * confidence-gate logic and returns a wire-compatible result. The production
 * `ingestFile()` router imports this and acts on the decision.
 *
 * Spec: specs/2026-05-18-L4-regex-first-extraction.md §3, §7, T9.
 */

import { decideExtraction, type ChunkContext, type IngestDecision } from "./ingest-router-l4.js";
import { type EntityRef, type FrontmatterRelation } from "./types.js";

// ---------------------------------------------------------------------------
// Confidence thresholds
// ---------------------------------------------------------------------------

/**
 * Minimum confidence required to skip LLM extraction.
 * Below this, fall through to Gemini (existing path).
 */
export const CONFIDENCE_THRESHOLD = 0.8;

/** Confidence for frontmatter typed-link relations (highest precision). */
export const CONFIDENCE_FRONTMATTER = 0.95;

/** Confidence for explicit [[wikilink]] or [md-link](slug) matches. */
export const CONFIDENCE_EXPLICIT_LINK = 0.90;

/** Confidence for bare `entityType/slug` references. */
export const CONFIDENCE_BARE_REF = 0.75;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Confidence-scored relation ready for kg_relations insert.
 * All fields are production-wire compatible (no DB types imported here).
 */
export interface ScoredRelation {
  /** Source entity slug (chunk-owning entity). */
  sourceSlug: string;
  /** Target entity slug. */
  targetSlug: string;
  /** Relation type. */
  relationType: string;
  /** Confidence score [0.0, 1.0]. */
  confidence: number;
  /** Extraction method for telemetry. */
  extraction_method: "regex" | "llm";
  /** Raw reason tag for kg_relations.relation_reason. */
  relation_reason: "regex_extracted" | "gemini_extracted";
}

/** Wire-compatible result from the fast-path check. */
export interface ProductionWireResult {
  /** Relations from regex with confidence scores. */
  regexRelations: ScoredRelation[];
  /** Maximum confidence seen in any relation (gate decision basis). */
  maxConfidence: number;
  /** Whether to skip the LLM call (max confidence ≥ threshold). */
  skipLlm: boolean;
  /** Extraction decision from decideExtraction (for telemetry). */
  decision: IngestDecision;
  /** Telemetry fields for logging to kg_relations. */
  telemetry: {
    extraction_method: "regex_only" | "gemini_only" | "regex_primary_gemini_secondary" | "gemini_only_after_regex_zero";
    regex_relations_count: number;
    gemini_call_skipped: boolean;
    latency_ms_regex: number;
  };
}

// ---------------------------------------------------------------------------
// Confidence scoring
// ---------------------------------------------------------------------------

/**
 * Compute confidence for a single entity ref based on its source pattern.
 * Spec §7: frontmatter > explicit link > bare ref.
 */
export function scoreEntityRef(ref: EntityRef): number {
  switch (ref.source) {
    case "markdown_link":
    case "wikilink":
      return CONFIDENCE_EXPLICIT_LINK;
    case "bare_ref":
      return CONFIDENCE_BARE_REF;
    default:
      return CONFIDENCE_BARE_REF;
  }
}

/**
 * Compute confidence for a frontmatter-derived typed relation.
 * Frontmatter fields are explicitly authored → highest precision.
 */
export function scoreFrontmatterRelation(_rel: FrontmatterRelation): number {
  return CONFIDENCE_FRONTMATTER;
}

// ---------------------------------------------------------------------------
// Core fast-path check
// ---------------------------------------------------------------------------

/**
 * Run the regex fast-path check for a chunk.
 *
 * 1. Calls `decideExtraction` to get regex hits and LLM skip decision.
 * 2. Scores each relation by confidence.
 * 3. If max confidence ≥ CONFIDENCE_THRESHOLD → skipLlm=true.
 * 4. Returns scored relations ready for kg_relations insert.
 *
 * @param chunk     Chunk metadata + content.
 * @param sourceSlug The entity slug this chunk belongs to (for FK resolution).
 */
export function runProductionFastPath(
  chunk: ChunkContext,
  sourceSlug: string,
): ProductionWireResult {
  const decision = decideExtraction(chunk);
  const { regex } = decision;

  const regexRelations: ScoredRelation[] = [];
  let maxConfidence = 0;

  // Score frontmatter relations (highest confidence).
  for (const rel of regex.frontmatterRelations) {
    const confidence = scoreFrontmatterRelation(rel);
    maxConfidence = Math.max(maxConfidence, confidence);
    regexRelations.push({
      sourceSlug,
      targetSlug: rel.target,
      relationType: rel.relationType,
      confidence,
      extraction_method: "regex",
      relation_reason: "regex_extracted",
    });
  }

  // Score entity refs (wikilink/markdown_link/bare_ref).
  for (const ref of regex.entityRefs) {
    const confidence = scoreEntityRef(ref);
    maxConfidence = Math.max(maxConfidence, confidence);
    regexRelations.push({
      sourceSlug,
      targetSlug: ref.key,
      relationType: "references",
      confidence,
      extraction_method: "regex",
      relation_reason: "regex_extracted",
    });
  }

  // Code refs: treated as bare-ref confidence level.
  for (const cref of regex.codeRefs) {
    const confidence = CONFIDENCE_BARE_REF;
    maxConfidence = Math.max(maxConfidence, confidence);
    regexRelations.push({
      sourceSlug,
      targetSlug: cref.key,
      relationType: "code_ref",
      confidence,
      extraction_method: "regex",
      relation_reason: "regex_extracted",
    });
  }

  // Override skip decision: also check our confidence gate.
  // decideExtraction may say skipGemini=true via section/type gate;
  // we additionally require maxConfidence ≥ CONFIDENCE_THRESHOLD.
  const skipLlm = decision.skipGemini && maxConfidence >= CONFIDENCE_THRESHOLD;

  const telemetry: ProductionWireResult["telemetry"] = {
    extraction_method: skipLlm
      ? "regex_only"
      : decision.telemetry.extraction_method,
    regex_relations_count: regexRelations.length,
    gemini_call_skipped: skipLlm,
    latency_ms_regex: decision.telemetry.latency_ms.regex,
  };

  return {
    regexRelations,
    maxConfidence,
    skipLlm,
    decision,
    telemetry,
  };
}

// ---------------------------------------------------------------------------
// Filter helpers (for production ingestFile() integration)
// ---------------------------------------------------------------------------

/**
 * Filter a list of scored relations to only those above the confidence gate.
 * Used when merging regex + LLM output — only high-confidence regex relations
 * suppress their LLM counterparts.
 */
export function filterHighConfidence(
  relations: ScoredRelation[],
  threshold = CONFIDENCE_THRESHOLD,
): ScoredRelation[] {
  return relations.filter((r) => r.confidence >= threshold);
}

/**
 * Build a dedup key for a relation — used to merge regex + LLM output.
 * Key = `<sourceSlug>|<targetSlug>|<relationType>` (case-insensitive).
 */
export function relationDedupKey(r: {
  sourceSlug: string;
  targetSlug: string;
  relationType: string;
}): string {
  return `${r.sourceSlug}|${r.targetSlug}|${r.relationType}`.toLowerCase();
}

/**
 * Merge regex scored relations with LLM relations. Deduplicates by key,
 * preferring high-confidence regex entries over LLM for the same triple.
 */
export function mergeWithLlmRelations(
  regexRelations: ScoredRelation[],
  llmRelations: Array<{ sourceSlug: string; targetSlug: string; relationType: string }>,
): ScoredRelation[] {
  const seen = new Map<string, ScoredRelation>();

  // Regex first (higher priority for dedup).
  for (const r of regexRelations) {
    const k = relationDedupKey(r);
    if (!seen.has(k)) seen.set(k, r);
  }

  // LLM fills gaps not covered by regex.
  for (const r of llmRelations) {
    const k = relationDedupKey(r);
    if (!seen.has(k)) {
      seen.set(k, {
        ...r,
        confidence: 0.7, // default LLM confidence
        extraction_method: "llm",
        relation_reason: "gemini_extracted",
      });
    }
  }

  return Array.from(seen.values());
}

// ---------------------------------------------------------------------------
// Env-flag helpers
// ---------------------------------------------------------------------------

/**
 * Returns true when the L4 regex feature is enabled via env flag.
 * Feature is opt-in via `NOX_L4_REGEX_ENABLED=1`.
 */
export function isRegexEnabled(): boolean {
  return process.env["NOX_L4_REGEX_ENABLED"] === "1";
}

/**
 * Returns true when the skip-Gemini gate is enabled.
 * Requires both `NOX_L4_REGEX_ENABLED=1` AND `NOX_L4_SKIP_GEMINI=1`.
 */
export function isSkipGeminiEnabled(): boolean {
  return isRegexEnabled() && process.env["NOX_L4_SKIP_GEMINI"] === "1";
}
