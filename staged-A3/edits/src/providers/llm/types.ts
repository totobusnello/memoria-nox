/**
 * src/providers/llm/types.ts — LLMProvider interface (T1).
 *
 * A3 spec §3 (locked from user task description):
 *   readonly name, model, contextWindow
 *   complete({system?, user, maxTokens?, temperature?}) -> {text, tokensIn, tokensOut, latencyMs}
 *   healthCheck(): Promise<HealthStatus>
 *
 * Notes:
 * - `system` is optional — many calls (kg-extract, heartbeat) use only `user`.
 * - `maxTokens` / `temperature` are optional with provider-side defaults.
 *   Defaults are intentionally NOT defined on the interface to let each provider
 *   apply its own (e.g., Gemini flash-lite uses temperature=0.2 in heartbeat).
 * - Stubs may throw "not implemented" from `complete()`; `healthCheck()` MUST
 *   still return a deterministic shape.
 */
import type { HealthStatus } from "../types.js";

export interface CompleteOpts {
  /** Optional system instruction; omitted if undefined. */
  system?: string;
  /** Required user prompt. */
  user: string;
  /** Output token budget; provider applies its own default if omitted. */
  maxTokens?: number;
  /** Sampling temperature; provider applies its own default if omitted. */
  temperature?: number;
}

export interface CompleteResult {
  /** Generated text from the model. */
  text: string;
  /** Input tokens billed by provider. */
  tokensIn: number;
  /** Output tokens billed by provider. */
  tokensOut: number;
  /** Wall-clock latency in milliseconds, end-to-end (provider call only). */
  latencyMs: number;
}

export interface LLMProvider {
  /** Provider id: 'gemini' | 'openai' | 'anthropic' | future ids. */
  readonly name: string;
  /** Model id (e.g., 'gemini-2.5-flash-lite', 'gpt-4o-mini'). */
  readonly model: string;
  /** Effective context window in tokens. */
  readonly contextWindow: number;

  complete(opts: CompleteOpts): Promise<CompleteResult>;

  healthCheck(): Promise<HealthStatus>;
}
