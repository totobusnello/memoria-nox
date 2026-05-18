/**
 * src/providers/embedding/openai.ts — OpenAI embedding stub (T5).
 *
 * Interface conformance only — throws `NotImplementedError` on `embed()`.
 * `healthCheck()` returns a deterministic shape so the registry boot probe
 * can still report a structured failure without a real network call.
 *
 * Real impl deferred to A3.1 / first user activation. Stubs ensure:
 *   - factory selection works (T2 throws UnknownProviderError if missing)
 *   - boot path is non-throwing when user keeps Gemini default but has
 *     OPENAI_API_KEY in env (validation skipped — only fails on actual use)
 *
 * Models reserved (will be wired in A3.1):
 *   - text-embedding-3-small (1536d)  ← default
 *   - text-embedding-3-large (3072d)  ← matches Gemini dim for swap parity
 */
import type { EmbeddingProvider } from "./types.js";
import type { HealthStatus } from "../types.js";
import { NotImplementedError } from "../types.js";

export const OPENAI_EMBED_DEFAULT_MODEL = "text-embedding-3-small";
/** Default dim for `text-embedding-3-small`. Large is 3072. */
export const OPENAI_EMBED_DEFAULT_DIM = 1536;
/** Per OpenAI public pricing 2026-05: $0.02 / 1M for 3-small, $0.13 / 1M for 3-large. */
export const OPENAI_EMBED_DEFAULT_COST = 0.02;
export const OPENAI_EMBED_MAX_TOKENS = 8191;

export interface OpenAIEmbeddingOpts {
  model?: string;
  dimensions?: number;
  apiKey?: string;
}

export class OpenAIEmbeddingProvider implements EmbeddingProvider {
  public readonly name = "openai";
  public readonly model: string;
  public readonly dimensions: number;
  public readonly maxTokens: number = OPENAI_EMBED_MAX_TOKENS;
  public readonly costPerMillionTokens: number = OPENAI_EMBED_DEFAULT_COST;

  constructor(opts: OpenAIEmbeddingOpts = {}) {
    this.model = opts.model ?? OPENAI_EMBED_DEFAULT_MODEL;
    this.dimensions = opts.dimensions ?? OPENAI_EMBED_DEFAULT_DIM;
    // NOTE: do NOT validate OPENAI_API_KEY here — stub conformance must not
    // throw at construction. Validation moves to A3.1 when embed() is wired.
  }

  public async embed(_texts: string[]): Promise<Float32Array[]> {
    void _texts;
    throw new NotImplementedError("openai", "embed");
  }

  public async healthCheck(): Promise<HealthStatus> {
    return {
      ok: false,
      latencyMs: 0,
      error:
        "OpenAI embedding provider is a stub (interface conformance only). " +
        "Implement in A3.1 before activating NOX_EMBEDDING_PROVIDER=openai.",
    };
  }
}
