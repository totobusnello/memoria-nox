/**
 * src/providers/llm/openai.ts — OpenAI LLM stub (T5).
 *
 * Interface conformance only — throws `NotImplementedError` on `complete()`.
 * `healthCheck()` returns a deterministic stub-down shape.
 *
 * Real impl deferred to A3.1.
 *
 * Models reserved:
 *   - gpt-4o-mini   ← default for the eventual fallback chain
 *   - gpt-4o        ← opt-in via NOX_LLM_MODEL
 */
import type { LLMProvider, CompleteOpts, CompleteResult } from "./types.js";
import type { HealthStatus } from "../types.js";
import { NotImplementedError } from "../types.js";

export const OPENAI_LLM_DEFAULT_MODEL = "gpt-4o-mini";
export const OPENAI_LLM_CONTEXT_WINDOWS: Record<string, number> = {
  "gpt-4o-mini": 128_000,
  "gpt-4o": 128_000,
};

export interface OpenAILLMOpts {
  model?: string;
  apiKey?: string;
  contextWindow?: number;
}

export class OpenAILLMProvider implements LLMProvider {
  public readonly name = "openai";
  public readonly model: string;
  public readonly contextWindow: number;

  constructor(opts: OpenAILLMOpts = {}) {
    this.model = opts.model ?? OPENAI_LLM_DEFAULT_MODEL;
    this.contextWindow =
      opts.contextWindow ?? OPENAI_LLM_CONTEXT_WINDOWS[this.model] ?? 128_000;
    // Stub: no key validation at construction.
  }

  public async complete(_opts: CompleteOpts): Promise<CompleteResult> {
    void _opts;
    throw new NotImplementedError("openai", "complete");
  }

  public async healthCheck(): Promise<HealthStatus> {
    return {
      ok: false,
      latencyMs: 0,
      error:
        "OpenAI LLM provider is a stub (interface conformance only). " +
        "Implement in A3.1 before activating NOX_LLM_PROVIDER=openai.",
    };
  }
}
