/**
 * L4 regex-extract — public surface (T1-T6).
 *
 * gbrain-inspired (MIT, Garry Tan) regex-first KG extraction with Gemini
 * fallback. See specs/2026-05-18-L4-regex-first-extraction.md.
 */

export * from "./types.js";
export { stripCodeBlocks, type StripResult } from "./strip-code.js";
export {
  DIR_PATTERN,
  OPTIONAL_TOP,
  SLUG_CHARS,
  buildMarkdownLinkRe,
  buildWikilinkRe,
  buildBareRefRe,
  buildCodeRefRe,
} from "./patterns.js";
export { extractEntityRefsRegex, extractCodeRefs } from "./extractor.js";
export {
  extractFrontmatterBlock,
  parseFrontmatterFields,
  extractFrontmatterRelations,
  extractFrontmatterRelationsFromObject,
} from "./frontmatter.js";
export {
  decideExtraction,
  mergeRelations,
  type ChunkContext,
  type ExtractionTelemetry,
  type IngestDecision,
  type MergedRelation,
} from "./ingest-router-l4.js";
