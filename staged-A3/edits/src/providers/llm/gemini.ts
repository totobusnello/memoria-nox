/**
 * src/providers/llm/gemini.ts — Gemini LLM provider (T4).
 *
 * Real impl wrapping `generativelanguage.googleapis.com/v1beta`.
 * D41 default model: `gemini-2.5-flash-lite`.
 *
 * Models supported (opt-in via `NOX_LLM_MODEL`):
 *   - `gemini-2.5-flash-lite` (default — cheapest, fastest, lowest quality)
 *   - `gemini-2.5-flash`      (KG extraction full, higher cost — CLAUDE.md regra #3)
 *   - `gemini-2.5-pro`        (opt-in, expensive — for synthesis/reflection)
 *
 * CLAUDE.md regra #3: NUNCA voltar pra `gemini-2.5-flash` (quota 3M/d estoura)
 * silently. Caller must explicitly select via env override. This impl honours
 * the constructor-time `model` arg verbatim — selection policy lives in
 * registry (T2).
 *
 * Wire shape mirrors the existing `src/lib/gemini-client.ts` so wrapping in
 * T13 is byte-equivalent at the request level.
 */
import type { LLMProvider, CompleteOpts, CompleteResult } from "./types.js";
import type { HealthStatus } from "../types.js";
import { MissingKeyError } from "../types.js";
import { redactSecrets, type FetchLike } from "../embedding/gemini.js";

export const GEMINI_LLM_DEFAULT_MODEL = "gemini-2.5-flash-lite";

/** Approximate context windows; used for the `contextWindow` readonly. */
export const GEMINI_LLM_CONTEXT_WINDOWS: Record<string, number> = {
  "gemini-2.5-flash-lite": 1_000_000,
  "gemini-2.5-flash": 1_000_000,
  "gemini-2.5-pro": 2_000_000,
};

export interface GeminiLLMOpts {
  /** Override model. Default: gemini-2.5-flash-lite (D41). */
  model?: string;
  /** Override API key. Else read GEMINI_API_KEY. */
  apiKey?: string;
  /** Injected fetch for tests. */
  fetchFn?: FetchLike;
  /** Base URL override (lets tests point at fixture server). */
  baseUrl?: string;
  /** Override context window (else inferred from `model`). */
  contextWindow?: number;
}

const DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta";

export class GeminiLLMProvider implements LLMProvider {
  public readonly name = "gemini";
  public readonly model: string;
  public readonly contextWindow: number;
  private readonly apiKey: string;
  private readonly fetchFn: FetchLike;
  private readonly baseUrl: string;

  constructor(opts: GeminiLLMOpts = {}) {
    this.model = opts.model ?? GEMINI_LLM_DEFAULT_MODEL;
    this.contextWindow =
      opts.contextWindow ?? GEMINI_LLM_CONTEXT_WINDOWS[this.model] ?? 1_000_000;
    this.baseUrl = opts.baseUrl ?? DEFAULT_BASE_URL;
    const resolvedKey = opts.apiKey ?? process.env.GEMINI_API_KEY ?? "";
    if (!resolvedKey) {
      throw new MissingKeyError("gemini", "GEMINI_API_KEY");
    }
    this.apiKey = resolvedKey;
    const f = opts.fetchFn ?? (globalThis as { fetch?: FetchLike }).fetch;
    if (!f) {
      throw new Error(
        "GeminiLLMProvider: no fetch available (Node<18?). Pass opts.fetchFn explicitly.",
      );
    }
    this.fetchFn = f;
  }

  public async complete(opts: CompleteOpts): Promise<CompleteResult> {
    if (!opts.user || typeof opts.user !== "string") {
      throw new Error("GeminiLLMProvider.complete: `user` is required and must be a string");
    }
    const t0 = Date.now();
    const url =
      `${this.baseUrl}/models/${encodeURIComponent(this.model)}:generateContent` +
      `?key=${encodeURIComponent(this.apiKey)}`;
    // Build content array; Gemini accepts `system_instruction` separately.
    const body: Record<string, unknown> = {
      contents: [{ role: "user", parts: [{ text: opts.user }] }],
      generationConfig: {
        temperature: opts.temperature ?? 0.2,
        maxOutputTokens: opts.maxTokens ?? 1500,
      },
    };
    if (opts.system && opts.system.length > 0) {
      body.system_instruction = { parts: [{ text: opts.system }] };
    }
    const res = await this.fetchFn(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const raw = await res.text().catch(() => "");
      const redacted = redactSecrets(raw).slice(0, 200);
      throw new Error(
        `GeminiLLMProvider: HTTP ${res.status} ${res.statusText} — ${redacted}`,
      );
    }
    const parsed = (await res.json()) as GeminiGenerateResponse;
    const latencyMs = Date.now() - t0;
    const candidate = parsed.candidates?.[0];
    const text = candidate?.content?.parts?.[0]?.text ?? "";
    const usage = parsed.usageMetadata ?? {};
    return {
      text,
      tokensIn: usage.promptTokenCount ?? 0,
      tokensOut: usage.candidatesTokenCount ?? 0,
      latencyMs,
    };
  }

  public async healthCheck(): Promise<HealthStatus> {
    const t0 = Date.now();
    try {
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

interface GeminiGenerateResponse {
  candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }>;
  usageMetadata?: { promptTokenCount?: number; candidatesTokenCount?: number };
}
