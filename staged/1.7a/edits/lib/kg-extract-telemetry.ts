/**
 * kg-extract-telemetry.ts — Shadow telemetry for L4 regex-first extraction.
 *
 * Logs per-chunk diff entries to a rotating daily JSONL file, allowing
 * 7-day shadow validation before promoting hybrid_active mode.
 *
 * Log path: /var/log/nox-kg/extract-diff-YYYY-MM-DD.jsonl
 * Override: NOX_KG_TELEMETRY_DIR env (useful for local dev / tests)
 *
 * Shadow-mode usage:
 *  1. Both regex and Gemini run.
 *  2. Diff is logged here.
 *  3. After 7 days, review diff to verify: regex coverage ≥85% of Gemini,
 *     false-positive rate ≤2%, no retrieval regression.
 *  4. Only then set NOX_KG_EXTRACT_MODE=hybrid_active.
 *
 * Design: append-only, no DB dependency. File is the audit trail.
 */

import { appendFileSync, mkdirSync } from "fs";
import { join, dirname } from "path";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ExtractDiffEntry {
  /** ISO timestamp of the extraction. */
  ts: string;
  /** Chunk ID from the DB (string form; caller resolves). */
  chunk_id: string;
  /** Section of the chunk (compiled / frontmatter / timeline / prose / null). */
  section: "compiled" | "frontmatter" | "timeline" | "prose" | null;
  /** Extraction mode that produced this diff. */
  mode: "hybrid_shadow" | "hybrid_active" | "regex_only";
  /** Entity refs found by regex. */
  regex_entity_refs: string[];
  /** Frontmatter relations found by regex. */
  regex_frontmatter_relations: string[];
  /** Code refs found by regex. */
  regex_code_refs: string[];
  /** Entity names extracted by Gemini (null when Gemini was not called). */
  gemini_entities: string[] | null;
  /** Relation triples extracted by Gemini (null when not called). */
  gemini_relations: string[] | null;
  /** Wall-clock latency of regex pass in ms. */
  latency_regex_ms: number;
  /** Wall-clock latency of Gemini pass in ms (null when skipped). */
  latency_gemini_ms: number | null;
}

// ─── Internal helpers ─────────────────────────────────────────────────────────

function telemetryDir(): string {
  return process.env["NOX_KG_TELEMETRY_DIR"] ?? "/var/log/nox-kg";
}

function todayString(): string {
  return new Date().toISOString().slice(0, 10); // YYYY-MM-DD
}

function logPath(date?: string): string {
  return join(telemetryDir(), `extract-diff-${date ?? todayString()}.jsonl`);
}

let _dirEnsured = false;
function ensureDir(): void {
  if (_dirEnsured) return;
  try {
    mkdirSync(telemetryDir(), { recursive: true });
    _dirEnsured = true;
  } catch {
    // If we can't create the dir (e.g., read-only FS in CI), telemetry is silently dropped.
    _dirEnsured = true; // don't retry on every call
  }
}

// ─── Public API ───────────────────────────────────────────────────────────────

/**
 * Append a single diff entry to today's JSONL log file.
 *
 * Silently drops if the log directory is not writable (never throws).
 * Caller should NOT await — this is fire-and-forget telemetry.
 */
export function logExtractDiff(entry: ExtractDiffEntry): void {
  ensureDir();
  const line = JSON.stringify({ ...entry, ts: new Date().toISOString() }) + "\n";
  try {
    appendFileSync(logPath(), line, { encoding: "utf8" });
  } catch {
    // Telemetry write failure must never crash the extraction pipeline.
  }
}

/**
 * Build an ExtractDiffEntry from regex + Gemini results.
 *
 * Call after both regex AND Gemini have run (shadow mode).
 * Pass `gemini_entities=null` and `gemini_relations=null` when Gemini was skipped.
 */
export function buildDiffEntry(opts: {
  chunkId: string;
  section: ExtractDiffEntry["section"];
  mode: ExtractDiffEntry["mode"];
  regexEntityRefs: string[];
  regexFrontmatterRelations: string[];
  regexCodeRefs: string[];
  geminiEntities: string[] | null;
  geminiRelations: string[] | null;
  latencyRegexMs: number;
  latencyGeminiMs: number | null;
}): ExtractDiffEntry {
  return {
    ts: new Date().toISOString(),
    chunk_id: opts.chunkId,
    section: opts.section,
    mode: opts.mode,
    regex_entity_refs: opts.regexEntityRefs,
    regex_frontmatter_relations: opts.regexFrontmatterRelations,
    regex_code_refs: opts.regexCodeRefs,
    gemini_entities: opts.geminiEntities,
    gemini_relations: opts.geminiRelations,
    latency_regex_ms: opts.latencyRegexMs,
    latency_gemini_ms: opts.latencyGeminiMs,
  };
}

/**
 * Compute a simple coverage ratio: regex entity refs / Gemini entities.
 *
 * Returns null when gemini_entities is null (Gemini not called).
 * Returns 1.0 when Gemini found zero entities (vacuous).
 *
 * Used in 7-day shadow review to check coverage ≥ 85% threshold.
 */
export function computeCoverageRatio(entry: ExtractDiffEntry): number | null {
  if (entry.gemini_entities === null) return null;
  if (entry.gemini_entities.length === 0) return 1.0;
  // Count regex refs whose slug appears in Gemini entity names (case-insensitive).
  const geminiNames = new Set(entry.gemini_entities.map((n) => n.toLowerCase()));
  let matched = 0;
  for (const ref of entry.regex_entity_refs) {
    // ref is `entityType/slug` — try matching slug component against Gemini names.
    const slug = ref.split("/")[1] ?? ref;
    if (geminiNames.has(slug.toLowerCase())) matched++;
  }
  return matched / entry.gemini_entities.length;
}

/**
 * Summarize a batch of entries for shadow validation reporting.
 *
 * Returns aggregate metrics used in the weekly shadow review:
 *  - totalEntries: total chunks sampled
 *  - geminiSkipped: how many times Gemini was not called
 *  - avgCoverageRatio: mean coverage where both ran (null when no overlap)
 *  - avgLatencyRegexMs: mean regex latency
 *  - avgLatencyGeminiMs: mean Gemini latency (over runs that called it)
 */
export function summarizeDiffEntries(entries: ExtractDiffEntry[]): {
  totalEntries: number;
  geminiSkipped: number;
  avgCoverageRatio: number | null;
  avgLatencyRegexMs: number;
  avgLatencyGeminiMs: number | null;
} {
  if (entries.length === 0) {
    return { totalEntries: 0, geminiSkipped: 0, avgCoverageRatio: null, avgLatencyRegexMs: 0, avgLatencyGeminiMs: null };
  }

  const skipped = entries.filter((e) => e.gemini_entities === null).length;
  const coverages = entries.map(computeCoverageRatio).filter((r): r is number => r !== null);
  const avgCov = coverages.length > 0 ? coverages.reduce((a, b) => a + b, 0) / coverages.length : null;
  const avgRegex = entries.reduce((s, e) => s + e.latency_regex_ms, 0) / entries.length;
  const geminiLatencies = entries.map((e) => e.latency_gemini_ms).filter((n): n is number => n !== null);
  const avgGemini = geminiLatencies.length > 0
    ? geminiLatencies.reduce((a, b) => a + b, 0) / geminiLatencies.length
    : null;

  return {
    totalEntries: entries.length,
    geminiSkipped: skipped,
    avgCoverageRatio: avgCov,
    avgLatencyRegexMs: avgRegex,
    avgLatencyGeminiMs: avgGemini,
  };
}

/**
 * Returns the log file path for a given date (or today).
 * Exposed for tests and external readers.
 */
export { logPath };
