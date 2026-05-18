/**
 * T6 — Ingest router integration: regex-first KG extraction with Gemini fallback.
 *
 * Pure orchestration layer — no DB writes, no Gemini API calls. Returns a
 * structured decision payload that the actual ingest router (production
 * `src/lib/ingest-router.ts`) consumes to:
 *  1) write `kg_relations` rows tagged `extraction_method`
 *  2) decide whether to invoke `geminiKgExtract`
 *  3) merge + dedup results
 *  4) emit telemetry per spec §7
 *
 * Keeping this layer pure means it's covered by unit tests without DB or
 * network fixtures — the integration test layer (T7+ deferred) wires the
 * production ingestor.
 *
 * Spec: specs/2026-05-18-L4-regex-first-extraction.md §3 + §7.
 */

import { extractEntityRefsRegex, extractCodeRefs } from "./extractor.js";
import { extractFrontmatterRelations } from "./frontmatter.js";
import {
  CodeRef,
  EntityRef,
  FrontmatterRelation,
  RegexExtractionResult,
} from "./types.js";

/** Chunk metadata that the production ingest router already maintains. */
export interface ChunkContext {
  /** Chunk section per schema v10 (NULL for legacy/unsectioned chunks). */
  section: "compiled" | "frontmatter" | "timeline" | "prose" | null;
  /** Chunk type taxonomy (used to force Gemini for conversation logs). */
  type:
    | "entity"
    | "spec"
    | "audit"
    | "conversation"
    | "daily_log"
    | "freeform"
    | "code"
    | "other";
  /** Raw chunk content (markdown). */
  content: string;
  /** Approximate chunk size in characters — used to short-circuit tiny chunks. */
  size?: number;
}

/** Per-chunk telemetry record emitted per spec §7. */
export interface ExtractionTelemetry {
  section: ChunkContext["section"];
  extraction_method:
    | "regex_only"
    | "gemini_only"
    | "regex_primary_gemini_secondary"
    | "gemini_only_after_regex_zero";
  regex_relations_count: number;
  /** Set by production caller once Gemini returns; unset here. */
  gemini_relations_count: number | null;
  gemini_call_skipped: boolean;
  latency_ms: { regex: number; gemini: number | null; total: number | null };
}

/** Decision returned by the router pre-Gemini. */
export interface IngestDecision {
  /** All regex-extracted artifacts (entity refs + frontmatter rels + code refs). */
  regex: RegexExtractionResult;
  /** Total count of regex relations (refs + frontmatter; code refs counted separately). */
  regexRelationsCount: number;
  /** Whether the caller should SKIP the Gemini KG call. */
  skipGemini: boolean;
  /** Telemetry placeholder — Gemini fields filled by caller post-call. */
  telemetry: ExtractionTelemetry;
}

/** Sections eligible for the skip-Gemini fast path. */
const SKIP_ELIGIBLE_SECTIONS = new Set<ChunkContext["section"]>([
  "compiled",
  "frontmatter",
  "timeline",
]);

/** Chunk types that ALWAYS run Gemini (prose-heavy, weak structure). */
const FORCE_GEMINI_TYPES = new Set<ChunkContext["type"]>([
  "conversation",
  "daily_log",
  "freeform",
]);

/**
 * Run regex extraction + decide whether Gemini should be skipped.
 *
 * Skip-gate (spec §7):
 *   section ∈ {compiled, frontmatter, timeline}
 *   AND regex_relations_count ≥ 1
 *   AND chunk.type ∉ {conversation, daily_log, freeform}
 */
export function decideExtraction(chunk: ChunkContext): IngestDecision {
  const t0 = performanceNowSafe();
  const entityRefs: EntityRef[] = extractEntityRefsRegex(chunk.content);
  const frontmatterRelations: FrontmatterRelation[] =
    extractFrontmatterRelations(chunk.content);
  const codeRefs: CodeRef[] = extractCodeRefs(chunk.content);
  const regexElapsed = performanceNowSafe() - t0;

  const regexRelationsCount =
    entityRefs.length + frontmatterRelations.length + codeRefs.length;

  const sectionEligible = chunk.section
    ? SKIP_ELIGIBLE_SECTIONS.has(chunk.section)
    : false;
  const typeAllowsSkip = !FORCE_GEMINI_TYPES.has(chunk.type);
  const skipGemini =
    sectionEligible && typeAllowsSkip && regexRelationsCount >= 1;

  let method: ExtractionTelemetry["extraction_method"];
  if (skipGemini) {
    method = "regex_only";
  } else if (regexRelationsCount === 0) {
    method = "gemini_only_after_regex_zero";
  } else if (sectionEligible) {
    method = "regex_primary_gemini_secondary";
  } else {
    method = "gemini_only";
  }

  const regex: RegexExtractionResult = {
    entityRefs,
    frontmatterRelations,
    codeRefs,
    hadCodeFences: chunk.content.includes("`"),
  };

  const telemetry: ExtractionTelemetry = {
    section: chunk.section,
    extraction_method: method,
    regex_relations_count: regexRelationsCount,
    gemini_relations_count: null,
    gemini_call_skipped: skipGemini,
    latency_ms: { regex: regexElapsed, gemini: null, total: null },
  };

  return {
    regex,
    regexRelationsCount,
    skipGemini,
    telemetry,
  };
}

/**
 * Merge regex + Gemini relations into a single dedup'd set ready for insert.
 * Production caller passes Gemini relations after the API call when skipGemini
 * was false. Dedup key = `<source>|<target>|<type>` (case-insensitive).
 */
export interface MergedRelation {
  /** Source entity key (chunk-owning entity), resolved by caller. */
  source: string;
  target: string;
  relationType: string;
  extraction_method: "regex" | "gemini";
}

export function mergeRelations(
  regex: MergedRelation[],
  gemini: MergedRelation[],
): MergedRelation[] {
  const seen = new Set<string>();
  const out: MergedRelation[] = [];
  for (const r of [...regex, ...gemini]) {
    const k = `${r.source}|${r.target}|${r.relationType}`.toLowerCase();
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(r);
  }
  return out;
}

/** Cross-platform high-resolution timer; falls back to Date.now() on Edge runtimes. */
function performanceNowSafe(): number {
  const g = globalThis as { performance?: { now?: () => number } };
  return g.performance?.now?.() ?? Date.now();
}
