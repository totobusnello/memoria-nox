/**
 * src/lib/answer/prompt.ts — Prompt assembly for P1 (T3 scope).
 *
 * Two builders:
 *   buildPrompt()      — initial pass; standard anti-hallucination guard.
 *   buildRetryPrompt() — stricter variant when first pass cited a marker
 *                        that did not exist in the retrieval set
 *                        (anti-hallucination retry, partial T5/T6).
 *
 * Design (kickoff §T3 + critical decision #1):
 *   - LLM only ever sees marker_ids (`chunk_1`..`chunk_N`), never DB ids.
 *   - System prompt = anti-hallucination guard + citation rule.
 *   - User prompt = the question + the numbered context block.
 *   - Token-budget truncation drops LOWEST-SCORE chunks first
 *     (kickoff critical decision #2 — old chunks can be high-salience).
 *
 * Pure functions: no I/O, deterministic given inputs.
 */

import type { RetrievedChunk } from "./types.js";

/** Approximate chars-per-token; conservative for English+code. */
const APPROX_CHARS_PER_TOKEN = 4;

/** Reserve budget for system prompt + question + LLM completion + slack. */
const RESERVED_NON_CHUNK_TOKENS = 800;

const SYSTEM_BASE =
  "Answer ONLY from the numbered context blocks below. " +
  "If the context does not contain the answer, reply exactly: " +
  '"I have no memory matches for this question." ' +
  "Cite EVERY factual claim with [chunk_N] using the marker shown next to each block. " +
  "Never invent citations. Never cite a marker that is not in the context.";

const SYSTEM_RETRY =
  "STRICT MODE — your previous answer cited a marker that does not exist. " +
  "You MUST only cite markers literally listed in the context below, e.g. [chunk_1], [chunk_2]. " +
  "If you cannot answer using ONLY these markers, reply exactly: " +
  '"I have no memory matches for this question." ' +
  "Do NOT speculate. Do NOT invent marker numbers.";

/**
 * Assemble system + user prompt for the initial LLM call.
 *
 * @param question  User question.
 * @param chunks    Retrieved chunks with marker_id already assigned.
 * @param maxTokens Token budget for the full prompt (incl. completion reserve).
 */
export function buildPrompt(
  question: string,
  chunks: RetrievedChunk[],
  maxTokens: number = 4000
): { system: string; user: string } {
  return {
    system: SYSTEM_BASE,
    user: assembleUserPrompt(question, chunks, maxTokens),
  };
}

/**
 * Stricter retry variant. Same shape as buildPrompt; different system prompt.
 */
export function buildRetryPrompt(
  question: string,
  chunks: RetrievedChunk[],
  maxTokens: number = 4000
): { system: string; user: string } {
  return {
    system: SYSTEM_RETRY,
    user: assembleUserPrompt(question, chunks, maxTokens),
  };
}

/**
 * Assemble the user-role message: question first, then numbered chunks.
 * Drops lowest-score chunks until the rough char budget fits.
 */
function assembleUserPrompt(
  question: string,
  chunks: RetrievedChunk[],
  maxTokens: number
): string {
  if (chunks.length === 0) {
    return `${question}\n\n(No context retrieved.)`;
  }

  const budgetChars = Math.max(
    256,
    (maxTokens - RESERVED_NON_CHUNK_TOKENS) * APPROX_CHARS_PER_TOKEN
  );

  // Stable copy ordered by score desc — drop tail first if over budget.
  const sortedDesc = [...chunks].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));

  let used = question.length;
  const kept: RetrievedChunk[] = [];
  for (const chunk of sortedDesc) {
    const renderedLen = chunk.marker_id.length + chunk.content.length + 8; // brackets + newlines
    if (used + renderedLen > budgetChars && kept.length > 0) {
      break; // keep at least one chunk even if oversized
    }
    kept.push(chunk);
    used += renderedLen;
  }

  // Render in original retrieval order (marker_id 1..N) so the LLM sees a
  // monotonically numbered list, not score-sorted noise.
  const inMarkerOrder = kept.sort((a, b) => markerNum(a) - markerNum(b));

  const contextBlock = inMarkerOrder
    .map((chunk) => `[${chunk.marker_id}] ${chunk.content}`)
    .join("\n\n");

  return `Question: ${question}\n\nContext:\n\n${contextBlock}`;
}

/** Helper — strip "chunk_" prefix to get the integer index for ordering. */
function markerNum(chunk: RetrievedChunk): number {
  const match = chunk.marker_id.match(/chunk_(\d+)/);
  return match && match[1] ? parseInt(match[1], 10) : Number.MAX_SAFE_INTEGER;
}
