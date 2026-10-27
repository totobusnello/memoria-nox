/**
 * src/lib/answer/index.ts — Public API for P1 (T1-T4 + minimal T5 partial).
 *
 * Exports:
 *   answer(opts) → AnswerResult
 *   Types: AnswerOpts, AnswerResult, Citation, RetrievedChunk, AnswerMetadata
 *   Helpers (re-export for adjacency modules): selectProvider, buildPrompt, retrieveContext
 *
 * Pipeline (T1-T4 scope + minimal T5/T6 anti-hallucination retry-once):
 *   1. resolveConfig(opts)                 → ResolvedConfig
 *   2. retrieveContext(question, topK)     → RetrievedChunk[]
 *   3. buildPrompt(question, chunks)       → {system, user}
 *   4. provider.complete(prompt + cfg)     → LLMCallResult
 *   5. parseCitations(text, chunks)        → { citations, hallucinated[] }
 *   6. If hallucinated.length > 0 → retry once with buildRetryPrompt()
 *   7. If retry still hallucinates → throw AnswerError('hallucination_after_retry')
 *
 * Empty retrieval, and an answer with no citation, both return the canonical
 * "no memory matches" answer. The first WITHOUT
 * calling the LLM (kickoff §6 retrieval_empty path).
 */

import { resolveConfig } from "./config.js";
import { buildPrompt, buildRetryPrompt } from "./prompt.js";
import { retrieveContext } from "./retrieval.js";
import { selectProvider } from "./provider.js";
import type {
  AnswerOpts,
  AnswerResult,
  AnswerMetadata,
  Citation,
  RetrievedChunk,
  AnswerFailureReason,
} from "./types.js";

export type {
  AnswerOpts,
  AnswerResult,
  AnswerMetadata,
  Citation,
  RetrievedChunk,
  AnswerFailureReason,
} from "./types.js";
export { selectProvider, MockProvider } from "./provider.js";
export type { LLMProvider, LLMCallOpts, LLMCallResult } from "./provider.js";
export { buildPrompt, buildRetryPrompt } from "./prompt.js";
export { retrieveContext, __setRawSearchForTests } from "./retrieval.js";
export { resolveConfig } from "./config.js";

/** Thrown when the pipeline produces an unrecoverable failure. */
export class AnswerError extends Error {
  public readonly reason: AnswerFailureReason;
  public readonly metadata: Partial<AnswerMetadata>;
  constructor(reason: AnswerFailureReason, message: string, metadata: Partial<AnswerMetadata>) {
    super(message);
    this.name = "AnswerError";
    this.reason = reason;
    this.metadata = metadata;
  }
}

const CANONICAL_EMPTY_ANSWER = "I have no memory matches for this question.";
const CITATION_REGEX = /\[chunk_(\d+)\]/g;
const SNIPPET_MAX_CHARS = 200;

export async function answer(opts: AnswerOpts): Promise<AnswerResult> {
  const t0 = Date.now();

  if (!opts || typeof opts.question !== "string" || opts.question.trim().length === 0) {
    throw new AnswerError("invalid_input", "answer(): question is required", {
      latency_ms: Date.now() - t0,
      provider: "n/a",
      model: "n/a",
      retrieval_count: 0,
    });
  }

  const cfg = resolveConfig(opts);
  const provider = opts.providerOverride ?? selectProvider(cfg.provider);
  const retrieve = opts.retrieveOverride ?? retrieveContext;

  // ── Step 2: retrieval ──────────────────────────────────────────────────
  const chunks = await retrieve(opts.question, cfg.topK);

  if (chunks.length === 0) {
    // Honour kickoff §6 retrieval_empty: short-circuit, no LLM spend.
    return {
      answer: CANONICAL_EMPTY_ANSWER,
      citations: [],
      metadata: {
        latency_ms: Date.now() - t0,
        tokens_in: 0,
        tokens_out: 0,
        provider: provider.name,
        model: cfg.model,
        retrieval_count: 0,
        fallback_used: false,
        failed_reason: "retrieval_empty",
        retry_count: 0,
      },
    };
  }

  // ── Steps 3-4: prompt + first LLM call ─────────────────────────────────
  const firstPrompt = buildPrompt(opts.question, chunks, cfg.maxTokens);
  let llmRes;
  try {
    llmRes = await provider.complete({
      system: firstPrompt.system,
      user: firstPrompt.user,
      maxTokens: cfg.maxTokens,
      temperature: cfg.temperature,
      model: cfg.model,
    });
  } catch (err) {
    throw new AnswerError("llm_error", `LLM call failed: ${(err as Error).message}`, {
      latency_ms: Date.now() - t0,
      provider: provider.name,
      model: cfg.model,
      retrieval_count: chunks.length,
      failed_reason: "llm_error",
    });
  }

  // ── Step 5: citation parse + validation ────────────────────────────────
  const first = parseCitations(llmRes.text, chunks);

  let finalText = llmRes.text;
  let finalCitations = first.citations;
  let tokensIn = llmRes.tokensIn;
  let tokensOut = llmRes.tokensOut;
  let retryCount = 0;
  let fallbackUsed = false;
  let failedReason: AnswerFailureReason | undefined;

  if (first.hallucinated.length > 0) {
    // ── Step 6: retry once with stricter prompt ─────────────────────────
    fallbackUsed = true;
    failedReason = "hallucinated_citation"; // tentative; cleared if retry succeeds
    const retryPrompt = buildRetryPrompt(opts.question, chunks, cfg.maxTokens);
    let retryRes;
    try {
      retryRes = await provider.complete({
        system: retryPrompt.system,
        user: retryPrompt.user,
        maxTokens: cfg.maxTokens,
        temperature: cfg.temperature,
        model: cfg.model,
      });
    } catch (err) {
      throw new AnswerError(
        "llm_error",
        `LLM retry call failed: ${(err as Error).message}`,
        {
          latency_ms: Date.now() - t0,
          provider: provider.name,
          model: cfg.model,
          retrieval_count: chunks.length,
          fallback_used: true,
          retry_count: 1,
          failed_reason: "llm_error",
        }
      );
    }
    retryCount = 1;
    tokensIn += retryRes.tokensIn;
    tokensOut += retryRes.tokensOut;

    const second = parseCitations(retryRes.text, chunks);
    if (second.hallucinated.length > 0) {
      // ── Step 7: hard fail per kickoff critical decision #3 ────────────
      throw new AnswerError(
        "hallucination_after_retry",
        `LLM cited unknown markers after retry: [${second.hallucinated.join(", ")}]`,
        {
          latency_ms: Date.now() - t0,
          tokens_in: tokensIn,
          tokens_out: tokensOut,
          provider: provider.name,
          model: cfg.model,
          retrieval_count: chunks.length,
          fallback_used: true,
          retry_count: 1,
          failed_reason: "hallucination_after_retry",
        }
      );
    }
    finalText = retryRes.text;
    finalCitations = second.citations;
    failedReason = undefined; // retry succeeded
  }

  // ── Step 7b: normalise an UNANCHORED answer to the canonical refusal ───
  //
  // The system prompt requires every factual claim to carry a [chunk_N] marker.
  // An answer with no citation therefore violates that contract: nothing in it
  // is anchored in the retrieved context, and the caller has no way to check any
  // of it. Serving such an answer is worse than serving the refusal, so it is
  // replaced here and the reason is recorded.
  //
  // Measured before being adopted (audits/2026-10-27-abstention-the-durable-fix.md):
  // against a bounded judge over 48 items, `citations.length === 0` identifies
  // abstention with TP=23 FP=0 FN=3, kappa 0.8754, against the evaluation
  // harness's five-substring predicate at TP=21 FP=0 FN=5, kappa 0.7938. FP=0
  // matters more than recall here — turning a useful answer into a refusal is
  // the worse error, and it did not happen once in 48.
  //
  // ⚠️ WHAT THIS DOES NOT FIX, stated so nobody reads the gate as complete: the
  // three items it misses cite a chunk AND declare the context does not explain
  // the thing — refusing while offering the neighbour. The answer is genuinely
  // both, so no predicate over the answer text can split it. That case needs the
  // model to return a FIELD (`answered: boolean`) rather than prose, which means
  // changing the prompt, the parse and the retry path; it is deliberately not
  // bundled here.
  if (finalCitations.length === 0) {
    finalText = CANONICAL_EMPTY_ANSWER;
    failedReason = "model_abstained";
  }

  const metadata: AnswerMetadata = {
    latency_ms: Date.now() - t0,
    tokens_in: tokensIn,
    tokens_out: tokensOut,
    provider: provider.name,
    model: cfg.model,
    retrieval_count: chunks.length,
    fallback_used: fallbackUsed,
    retry_count: retryCount,
  };
  if (failedReason !== undefined) metadata.failed_reason = failedReason;

  return {
    answer: finalText,
    citations: finalCitations,
    metadata,
  };
}

// ─── Citation parsing ──────────────────────────────────────────────────────

interface ParsedCitations {
  citations: Citation[];
  /** Marker strings the LLM emitted that did NOT exist in the retrieval set. */
  hallucinated: string[];
}

/**
 * Extract `[chunk_N]` markers from LLM output, validate each against the
 * retrieval set, and return Citation objects + the list of hallucinated
 * markers (out-of-range N).
 *
 * Exported for testability.
 */
export function parseCitations(
  text: string,
  chunks: RetrievedChunk[]
): ParsedCitations {
  // Build a lookup of marker_id → chunk for O(1) validation.
  const byMarker = new Map<string, RetrievedChunk>();
  for (const c of chunks) byMarker.set(c.marker_id, c);

  const seen = new Set<string>();
  const citations: Citation[] = [];
  const hallucinated: string[] = [];

  // Reset regex state defensively (it is /g so .exec advances lastIndex).
  CITATION_REGEX.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = CITATION_REGEX.exec(text)) !== null) {
    const idxStr = m[1];
    if (idxStr === undefined) continue;
    const marker = `chunk_${idxStr}`;
    if (seen.has(marker)) continue;
    seen.add(marker);

    const chunk = byMarker.get(marker);
    if (!chunk) {
      hallucinated.push(marker);
      continue;
    }
    const citation: Citation = {
      chunk_id: chunk.chunk_id,
      marker_id: chunk.marker_id,
      file_path: chunk.file_path,
      snippet: snippetOf(chunk.content),
    };
    if (chunk.line_range !== undefined) {
      citation.line_range = chunk.line_range;
    }
    citations.push(citation);
  }

  return { citations, hallucinated };
}

function snippetOf(content: string): string {
  const trimmed = content.replace(/\s+/g, " ").trim();
  if (trimmed.length <= SNIPPET_MAX_CHARS) return trimmed;
  return trimmed.slice(0, SNIPPET_MAX_CHARS - 1) + "…";
}
