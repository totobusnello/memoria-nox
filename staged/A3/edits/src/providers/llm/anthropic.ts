/**
 * src/providers/llm/anthropic.ts — Anthropic LLM stub (T6).
 *
 * Interface conformance only — throws `NotImplementedError` on `complete()`.
 *
 * Real impl deferred to A3.1. No embedding sibling: Anthropic has no public
 * embedding API as of 2026-05 (A3 spec §T6).
 *
 * Models reserved:
 *   - claude-3-5-haiku    ← cheap fallback default
 *   - claude-3-5-sonnet   ← opt-in heavy reasoning
 */
import type { LLMProvider, CompleteOpts, CompleteResult } from "./types.js";
import type { HealthStatus } from "../types.js";
import { NotImplementedError } from "../types.js";

export const ANTHROPIC_LLM_DEFAULT_MODEL = "claude-3-5-haiku";
export const ANTHROPIC_LLM_CONTEXT_WINDOWS: Record<string, number> = {
  "claude-3-5-haiku": 200_000,
  "claude-3-5-sonnet": 200_000,
};

export interface AnthropicLLMOpts {
  model?: string;
  apiKey?: string;
  contextWindow?: number;
}

export class AnthropicLLMProvider implements LLMProvider {
  public readonly name = "anthropic";
  public readonly model: string;
  public readonly contextWindow: number;

  constructor(opts: AnthropicLLMOpts = {}) {
    this.model = opts.model ?? ANTHROPIC_LLM_DEFAULT_MODEL;
    this.contextWindow =
      opts.contextWindow ?? ANTHROPIC_LLM_CONTEXT_WINDOWS[this.model] ?? 200_000;
  }

  public async complete(_opts: CompleteOpts): Promise<CompleteResult> {
    void _opts;
    throw new NotImplementedError("anthropic", "complete");
  }

  public async healthCheck(): Promise<HealthStatus> {
    return {
      ok: false,
      latencyMs: 0,
      error:
        "Anthropic LLM provider is a stub (interface conformance only). " +
        "Implement in A3.1 before activating NOX_LLM_PROVIDER=anthropic.",
    };
  }
}
