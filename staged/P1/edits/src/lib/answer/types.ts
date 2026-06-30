/**
 * src/lib/answer/types.ts — Public interfaces for P1 answer primitive.
 *
 * Per kickoff doc PR #18 §3:
 * - AnswerOpts:  request shape (kickoff §6 contract simplified for T1-T4 MVP)
 * - AnswerResult: response shape with citations + metadata
 * - Citation:    chunk_id + marker_id bridge (LLM never sees real ids)
 * - RetrievedChunk: shape returned by retrieval.ts wrapper
 *
 * Naming convention: kickoff doc uses AnswerRequest/AnswerResponse; T1-T4
 * spec from operator uses AnswerOpts/AnswerResult. We export BOTH aliases
 * so downstream T8 (CLI) and T9 (HTTP) can pick either without churn.
 */
import type { LLMProvider } from "./provider.js";

/** Request to answer(): {question, topK, maxTokens, provider, model, temperature}. */
export interface AnswerOpts {
  /** Natural-language question. Required. */
  question: string;
  /** Top-K chunks from retrieval. Default 8. Range 1-20. */
  topK?: number;
  /** Max output tokens from LLM. Default 1500. */
  maxTokens?: number;
  /** Provider name: 'gemini' | 'mock' | future 'openai'/'anthropic'. Default 'gemini'. */
  provider?: string;
  /** Model id. Default 'gemini-2.5-flash-lite' (D41 #1 locked). */
  model?: string;
  /** LLM temperature. Default 0.2. */
  temperature?: number;
  /**
   * Optional injection point for testing. If set, used INSTEAD of selectProvider().
   * Production code should leave undefined and let config defaults flow.
   */
  providerOverride?: LLMProvider;
  /**
   * Optional retrieval injection point for testing/mocking.
   * If set, used INSTEAD of the real hybrid search wrapper.
   */
  retrieveOverride?: (question: string, topK: number) => Promise<RetrievedChunk[]>;
}

/** Alias kept for kickoff-doc consistency. */
export type AnswerRequest = AnswerOpts;

/** A chunk surfaced by retrieval, with marker_id assigned for LLM-side citation. */
export interface RetrievedChunk {
  /** Real DB chunk id — server-side only, NEVER shown to LLM. */
  chunk_id: number;
  /** Display marker for LLM: "chunk_1", "chunk_2", ..., "chunk_N". */
  marker_id: string;
  /** Source file path (absolute or workspace-relative). */
  file_path: string;
  /** Optional "L42-L58" hint when chunk maps to specific lines. */
  line_range?: string;
  /** Chunk body text. */
  content: string;
  /** Optional content hash (sha256 hex) used by dedupe. */
  content_hash?: string;
  /** Optional fused score from hybrid search (RRF or similar). */
  score?: number;
}

/** A citation as returned to the caller — marker_id + real chunk pointer. */
export interface Citation {
  chunk_id: number;
  marker_id: string;
  file_path: string;
  line_range?: string;
  /** Short excerpt (≤200 chars) for inline preview. */
  snippet: string;
}

/** Top-level answer() return shape. */
export interface AnswerResult {
  /** Final answer text from LLM. May contain `[chunk_N]` markers inline. */
  answer: string;
  /** Citations parsed + validated against the retrieval set. */
  citations: Citation[];
  /** Telemetry/observability metadata. */
  metadata: AnswerMetadata;
}

export type AnswerResponse = AnswerResult;

export interface AnswerMetadata {
  /** Wall-clock latency in milliseconds, end-to-end. */
  latency_ms: number;
  /** Input tokens billed to the LLM call. */
  tokens_in: number;
  /** Output tokens billed to the LLM call. */
  tokens_out: number;
  /** Provider name as actually selected. */
  provider: string;
  /** Model id as actually called. */
  model: string;
  /** Chunks returned by retrieval (post-dedupe, pre-prompt). */
  retrieval_count: number;
  /** Whether fallback retry path was exercised (e.g., hallucinated citation). */
  fallback_used?: boolean;
  /** If non-success path, machine-readable reason. */
  failed_reason?: AnswerFailureReason;
  /** Number of retries attempted (0 or 1 in T1-T4 MVP). */
  retry_count?: number;
}

/** Failure-reason enum, aligned with kickoff §6 contract + T5/T6 partial. */
export type AnswerFailureReason =
  | "hallucinated_citation"
  | "hallucination_after_retry"
  | "retrieval_empty"
  | "llm_error"
  | "llm_timeout"
  | "invalid_input";

/** Internal: chunk before marker_id is assigned (raw from search). */
export interface RawChunk {
  chunk_id: number;
  file_path: string;
  line_range?: string;
  content: string;
  content_hash?: string;
  score?: number;
}
