/**
 * src/providers/embedding/types.ts — EmbeddingProvider interface (T1).
 *
 * A3 spec §3 (locked from user task description):
 *   readonly name, dimensions, maxTokens, costPerMillionTokens
 *   embed(texts: string[]): Promise<Float32Array[]>
 *   healthCheck(): Promise<HealthStatus>
 *
 * Notes:
 * - `Float32Array[]` — one vector per input text. Avoid Buffer typed-array aliasing
 *   (lesson 2026-05-03: Node Buffer pool corrupts Float32Array views; cache impls
 *   must copy via Uint8Array intermediate).
 * - Implementations may also expose `task_type` (retrieval.query|document) via
 *   provider-specific options; this base interface keeps the signature minimal
 *   per the locked spec to keep the swap surface narrow.
 * - Stubs may throw "not implemented" from `embed()`; `healthCheck()` MUST still
 *   return a deterministic shape so the registry's boot-time ping is uniform.
 */
import type { HealthStatus } from "../types.js";

export interface EmbeddingProvider {
  /** Provider id: 'gemini' | 'openai' | 'voyage' | future ids. */
  readonly name: string;
  /** Output vector dimensionality. Pre-A3.1: must match active corpus dim. */
  readonly dimensions: number;
  /** Max input tokens per single embed() input element (provider-side limit). */
  readonly maxTokens: number;
  /** Public list price in USD per 1,000,000 input tokens. */
  readonly costPerMillionTokens: number;

  /**
   * Compute embeddings for an ordered batch of texts.
   * Returns one Float32Array (length = `dimensions`) per input, in order.
   */
  embed(texts: string[]): Promise<Float32Array[]>;

  /**
   * Boot-time / on-demand health probe.
   * MUST be cheap (no token consumption) and complete within ~5s.
   */
  healthCheck(): Promise<HealthStatus>;
}
