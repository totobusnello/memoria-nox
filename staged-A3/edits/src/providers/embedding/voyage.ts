/**
 * src/providers/embedding/voyage.ts — Voyage embedding stub (T7).
 *
 * Interface conformance only — throws `NotImplementedError` on `embed()`.
 * Real impl deferred to A3.1.
 *
 * Models reserved:
 *   - voyage-3        (1024d) ← default
 *   - voyage-3-large  (1024d)
 *   - voyage-code-2   (1536d) ← code-aware retrieval
 *
 * Note: 1024d ≠ Gemini's 3072d — swap to Voyage requires A3.1 reembed.
 * Stub `healthCheck()` flags this to surface as a clear error before any
 * user accidentally points the corpus at a dim-mismatched provider.
 */
import type { EmbeddingProvider } from "./types.js";
import type { HealthStatus } from "../types.js";
import { NotImplementedError } from "../types.js";

export const VOYAGE_EMBED_DEFAULT_MODEL = "voyage-3";
export const VOYAGE_EMBED_DEFAULT_DIM = 1024;
export const VOYAGE_EMBED_DEFAULT_COST = 0.06;
export const VOYAGE_EMBED_MAX_TOKENS = 32_000;

export interface VoyageEmbeddingOpts {
  model?: string;
  dimensions?: number;
  apiKey?: string;
}

export class VoyageEmbeddingProvider implements EmbeddingProvider {
  public readonly name = "voyage";
  public readonly model: string;
  public readonly dimensions: number;
  public readonly maxTokens: number = VOYAGE_EMBED_MAX_TOKENS;
  public readonly costPerMillionTokens: number = VOYAGE_EMBED_DEFAULT_COST;

  constructor(opts: VoyageEmbeddingOpts = {}) {
    this.model = opts.model ?? VOYAGE_EMBED_DEFAULT_MODEL;
    this.dimensions = opts.dimensions ?? VOYAGE_EMBED_DEFAULT_DIM;
  }

  public async embed(_texts: string[]): Promise<Float32Array[]> {
    void _texts;
    throw new NotImplementedError("voyage", "embed");
  }

  public async healthCheck(): Promise<HealthStatus> {
    return {
      ok: false,
      latencyMs: 0,
      error:
        "Voyage embedding provider is a stub (interface conformance only). " +
        "Implement in A3.1 before activating NOX_EMBEDDING_PROVIDER=voyage. " +
        "Note: Voyage default dim is 1024 — swap requires A3.1 reembed.",
    };
  }
}
