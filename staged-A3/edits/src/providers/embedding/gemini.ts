/**
 * src/providers/embedding/gemini.ts — Gemini embedding provider (T3).
 *
 * Real impl wrapping `generativelanguage.googleapis.com/v1beta`.
 * D41 default model: `gemini-embedding-001` at 3072 dimensions.
 *
 * Design notes:
 * - Uses `fetch` (Node 18+) — no SDK dependency. The live `src/embedder.ts`
 *   in prod uses the official SDK; this staged path mirrors its wire shape
 *   so behaviour is byte-equivalent for the same model + input.
 * - `apiKey` resolved from `GEMINI_API_KEY` env at construction. Stored
 *   privately and NEVER echoed in errors (regex-blocked).
 * - `fetchFn` is injectable for tests — production passes nothing and the
 *   global `fetch` is used. Tests pass a stub to avoid network calls.
 * - `healthCheck()` calls the `:embedContent` endpoint with a 1-token input
 *   ("ping") — cheapest possible probe per spec §4 (T9 conformance: probes
 *   never cost > $0.01).
 * - All errors redacted: never include the API key value, never echo upstream
 *   401/403 body verbatim (some Gemini errors echo bearer prefix).
 */
import type { EmbeddingProvider } from "./types.js";
import type { HealthStatus } from "../types.js";
import { MissingKeyError } from "../types.js";

/** Default model + dim per D41. */
export const GEMINI_EMBED_DEFAULT_MODEL = "gemini-embedding-001";
export const GEMINI_EMBED_DEFAULT_DIM = 3072;
/** Public list price (USD per 1M tokens) — gemini-embedding-001 as of 2026-05. */
export const GEMINI_EMBED_COST_PER_M_TOKENS = 0.15;
/** Per-input token ceiling (Gemini hard limit ~2048 input tokens / item). */
export const GEMINI_EMBED_MAX_TOKENS = 2048;

/** Minimal fetch type compatible with Node 18+ global fetch (avoid lib.dom dep). */
export type FetchLike = (
  input: string,
  init?: {
    method?: string;
    headers?: Record<string, string>;
    body?: string;
    signal?: AbortSignal;
  },
) => Promise<{
  ok: boolean;
  status: number;
  statusText: string;
  text: () => Promise<string>;
  json: () => Promise<unknown>;
}>;

export interface GeminiEmbeddingOpts {
  /** Override model (e.g., 'text-embedding-004'). Default: gemini-embedding-001. */
  model?: string;
  /** Override dimensions. Default: 3072. */
  dimensions?: number;
  /** Override API key (else read GEMINI_API_KEY env). */
  apiKey?: string;
  /** Injected fetch for tests; defaults to globalThis.fetch. */
  fetchFn?: FetchLike;
  /** Base URL override (lets tests point at fixture server). */
  baseUrl?: string;
}

const DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta";

export class GeminiEmbeddingProvider implements EmbeddingProvider {
  public readonly name = "gemini";
  public readonly dimensions: number;
  public readonly maxTokens: number = GEMINI_EMBED_MAX_TOKENS;
  public readonly costPerMillionTokens: number = GEMINI_EMBED_COST_PER_M_TOKENS;
  public readonly model: string;
  private readonly apiKey: string;
  private readonly fetchFn: FetchLike;
  private readonly baseUrl: string;

  constructor(opts: GeminiEmbeddingOpts = {}) {
    this.model = opts.model ?? GEMINI_EMBED_DEFAULT_MODEL;
    this.dimensions = opts.dimensions ?? GEMINI_EMBED_DEFAULT_DIM;
    this.baseUrl = opts.baseUrl ?? DEFAULT_BASE_URL;
    const resolvedKey = opts.apiKey ?? process.env.GEMINI_API_KEY ?? "";
    if (!resolvedKey) {
      throw new MissingKeyError("gemini", "GEMINI_API_KEY");
    }
    this.apiKey = resolvedKey;
    const f = opts.fetchFn ?? (globalThis as { fetch?: FetchLike }).fetch;
    if (!f) {
      throw new Error(
        "GeminiEmbeddingProvider: no fetch available (Node<18?). Pass opts.fetchFn explicitly.",
      );
    }
    this.fetchFn = f;
  }

  public async embed(texts: string[]): Promise<Float32Array[]> {
    if (texts.length === 0) return [];
    // Gemini v1beta batchEmbedContents — array of request objects.
    const url =
      `${this.baseUrl}/models/${encodeURIComponent(this.model)}:batchEmbedContents` +
      `?key=${encodeURIComponent(this.apiKey)}`;
    const body = JSON.stringify({
      requests: texts.map((t) => ({
        model: `models/${this.model}`,
        content: { parts: [{ text: t }] },
        outputDimensionality: this.dimensions,
      })),
    });
    const res = await this.fetchFn(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body,
    });
    if (!res.ok) {
      const safeStatus = `${res.status} ${res.statusText}`;
      // Do NOT echo response body verbatim — providers can leak partial key
      // in 401/403 error envelopes. Read first 200 chars after key-regex strip.
      const raw = await res.text().catch(() => "");
      const redacted = redactSecrets(raw).slice(0, 200);
      throw new Error(`GeminiEmbeddingProvider: HTTP ${safeStatus} — ${redacted}`);
    }
    const parsed = (await res.json()) as {
      embeddings?: Array<{ values?: number[] }>;
    };
    if (!parsed.embeddings || !Array.isArray(parsed.embeddings)) {
      throw new Error("GeminiEmbeddingProvider: malformed response (no embeddings[])");
    }
    const out: Float32Array[] = [];
    for (let i = 0; i < parsed.embeddings.length; i++) {
      const e = parsed.embeddings[i];
      const values = e?.values;
      if (!values || values.length !== this.dimensions) {
        throw new Error(
          `GeminiEmbeddingProvider: response index ${i} dim mismatch ` +
            `(got ${values?.length ?? 0}, expected ${this.dimensions})`,
        );
      }
      // Copy values into a fresh Float32Array. Do NOT use Buffer.from then view —
      // lesson 2026-05-03: Node Buffer pool aliasing corrupts typed arrays under GC.
      const f32 = new Float32Array(this.dimensions);
      for (let j = 0; j < this.dimensions; j++) {
        f32[j] = values[j] ?? 0;
      }
      out.push(f32);
    }
    return out;
  }

  public async healthCheck(): Promise<HealthStatus> {
    const t0 = Date.now();
    try {
      // Cheapest probe: list models endpoint (no token billing) — or 1-input embed.
      // We use the metadata `:get` endpoint per A3 spec §T9 (no token consumption).
      const url =
        `${this.baseUrl}/models/${encodeURIComponent(this.model)}` +
        `?key=${encodeURIComponent(this.apiKey)}`;
      const res = await this.fetchFn(url, { method: "GET" });
      const latencyMs = Date.now() - t0;
      if (!res.ok) {
        return {
          ok: false,
          latencyMs,
          error: `health: HTTP ${res.status} ${res.statusText}`,
        };
      }
      return { ok: true, latencyMs };
    } catch (err) {
      const latencyMs = Date.now() - t0;
      const msg = err instanceof Error ? err.message : String(err);
      return { ok: false, latencyMs, error: `health: ${redactSecrets(msg)}` };
    }
  }
}

/**
 * Strip anything that looks like an API key from error text before surfacing.
 * Gemini keys are typically 39 chars starting "AIza"; we also catch generic
 * long base64-ish tokens to be defensive (covers OpenAI sk-... etc).
 */
export function redactSecrets(s: string): string {
  return s
    .replace(/AIza[0-9A-Za-z_-]{20,}/g, "AIza<REDACTED>")
    .replace(/sk-[A-Za-z0-9_-]{20,}/g, "sk-<REDACTED>")
    .replace(/Bearer\s+[A-Za-z0-9._-]{20,}/g, "Bearer <REDACTED>")
    .replace(/key=[A-Za-z0-9_-]{20,}/g, "key=<REDACTED>");
}
