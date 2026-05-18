/**
 * src/lib/answer/retrieval.ts — Hybrid-search wrapper for P1 (T2 scope).
 *
 * T1-T4 MVP: this module exposes `retrieveContext()` which is a thin
 * wrapper over the existing hybrid search (BM25 + sqlite-vec + RRF +
 * salience). In production this calls `src/lib/search/hybrid.ts`; here
 * (staged dir) we expose `defaultRawSearch` as a pluggable injection
 * point so the unit tests can inject deterministic fixtures.
 *
 * Responsibilities (kickoff §T2 DoD):
 *   1. Call hybrid search (or injected stub).
 *   2. Dedupe near-duplicates by content_hash (keep highest score).
 *   3. Cap to topK.
 *   4. Assign marker_id = "chunk_1".."chunk_N" stable to retrieved order.
 *
 * Pure function: no DB writes, no LLM calls.
 */

import type { RawChunk, RetrievedChunk } from "./types.js";
import { searchHybrid } from "../../search.js";


/**
 * Signature for the underlying hybrid search call.
 * In prod this is bound to `hybridSearch()` from existing search module.
 */
export type RawSearchFn = (question: string, topK: number) => Promise<RawChunk[]>;

let injectedSearch: RawSearchFn | null = null;

/**
 * Test-only seam: replace the underlying raw search with a stub.
 * Pass `null` to restore real-prod hybridSearch binding (set by VPS adapter).
 */
export function __setRawSearchForTests(fn: RawSearchFn | null): void {
  injectedSearch = fn;
}

/**
 * Default raw search — in this staged dir we do NOT bind to the real
 * hybrid search (it lives in prod src/). The VPS-side apply step will
 * patch this to import from `src/lib/search/hybrid.js`. For now we
 * throw a clear error if called without injection — keeps tests honest
 * (must always inject) and prevents accidental network calls.
 */
async function defaultRawSearch(question: string, topK: number): Promise<RawChunk[]> {
  const hits = await searchHybrid(question, topK);
  return hits.map((h) => ({
    chunk_id: h.id ?? 0,
    file_path: h.source_file,
    content: h.chunk_text,
    score: h.score,
  }));
}

/**
 * Retrieve context chunks for a question.
 *
 * @param question  Natural-language input.
 * @param topK      Max chunks to return. Caller should pre-clamp via config.
 * @returns         Deduplicated, marker-assigned chunks ordered by score desc.
 */
export async function retrieveContext(
  question: string,
  topK: number
): Promise<RetrievedChunk[]> {
  if (!question || question.trim().length === 0) {
    return [];
  }
  if (topK <= 0) return [];

  const search = injectedSearch ?? defaultRawSearch;
  const raw = await search(question, topK * 2); // overfetch to survive dedupe

  // Sort by score desc (defensive — most hybrid impls already do this, but
  // we cannot trust ordering of an injected/mocked search).
  const sorted = [...raw].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));

  // Dedupe by content_hash (keep highest-score = first hit in sorted list).
  // If content_hash missing, dedupe by chunk_id as a fallback.
  const seenHashes = new Set<string>();
  const seenIds = new Set<number>();
  const deduped: RawChunk[] = [];
  for (const chunk of sorted) {
    const key = chunk.content_hash ?? "";
    if (key.length > 0) {
      if (seenHashes.has(key)) continue;
      seenHashes.add(key);
    } else {
      if (seenIds.has(chunk.chunk_id)) continue;
      seenIds.add(chunk.chunk_id);
    }
    deduped.push(chunk);
    if (deduped.length >= topK) break;
  }

  // Assign markers 1-indexed.
  return deduped.map((chunk, idx) => ({
    chunk_id: chunk.chunk_id,
    marker_id: `chunk_${idx + 1}`,
    file_path: chunk.file_path,
    line_range: chunk.line_range,
    content: chunk.content,
    content_hash: chunk.content_hash,
    score: chunk.score,
  }));
}
