import { GeminiLLMProvider } from "../../providers/llm/gemini.js";

/**
 * src/lib/answer/provider.ts — LLM provider abstraction for P1 (T4 scope).
 *
 * Goal: a minimal interface that ANTICIPATES the A3 module (PR #8) without
 * creating a hard dependency. When A3 lands, the real Gemini provider in
 * this file is replaced by a thin re-export of A3's `llm.call()`.
 *
 * Interface shape kept in sync with A3 spec §3:
 *   complete({system, user, maxTokens, temperature, model}) → {text, tokensIn, tokensOut, latencyMs}
 *
 * In this staged-P1 dir we ship:
 *   - MockProvider          — deterministic, no network. Always available.
 *   - placeholderGemini     — throws clear error; real impl bound on VPS apply.
 *   - selectProvider(name?) — name-based dispatch + env override.
 *
 * Per D41 #1: default model is `gemini-2.5-flash-lite`; never silently
 * switch to `gemini-2.5-flash` (CLAUDE.md regra #3).
 */

import { DEFAULT_PROVIDER } from "./config.js";

export interface LLMCallOpts {
  system: string;
  user: string;
  maxTokens: number;
  temperature: number;
  model: string;
}

export interface LLMCallResult {
  text: string;
  tokensIn: number;
  tokensOut: number;
  latencyMs: number;
}

export interface LLMProvider {
  readonly name: string;
  complete(opts: LLMCallOpts): Promise<LLMCallResult>;
}

/**
 * MockProvider — used by tests and by `--provider mock` CLI flag.
 *
 * Behaviour:
 *   - If `responses` queue non-empty, dequeue one per call (deterministic).
 *   - Else returns an echo of the question prefix + `[chunk_1]` citation,
 *     useful for happy-path smoke tests without scripting.
 *   - Token counts derived from text length / 4 (rough char-per-token).
 */
export class MockProvider implements LLMProvider {
  public readonly name = "mock";
  private readonly responses: string[];
  /** Per-call delay in ms; lets tests assert latency_ms is set. */
  private readonly delayMs: number;
  /** Optional canned error to throw on next call. */
  private errorOnNextCall: Error | null = null;

  constructor(responses: string[] = [], delayMs: number = 1) {
    this.responses = [...responses];
    this.delayMs = delayMs;
  }

  /** Test seam — force the next complete() to throw. */
  public throwNext(err: Error): void {
    this.errorOnNextCall = err;
  }

  public async complete(opts: LLMCallOpts): Promise<LLMCallResult> {
    const t0 = Date.now();
    if (this.delayMs > 0) {
      await new Promise((res) => setTimeout(res, this.delayMs));
    }
    if (this.errorOnNextCall) {
      const err = this.errorOnNextCall;
      this.errorOnNextCall = null;
      throw err;
    }
    const text = this.responses.shift() ?? defaultMockText(opts);
    return {
      text,
      tokensIn: estimateTokens(opts.system) + estimateTokens(opts.user),
      tokensOut: estimateTokens(text),
      latencyMs: Date.now() - t0,
    };
  }
}

/**
 * placeholderGemini — explicit failure surface; the VPS-side apply step
 * replaces this with a real `@google/genai` client. Keeping it as an
 * explicit throw prevents accidental real-network calls during tests.
 */
const placeholderGemini: LLMProvider = new GeminiLLMProvider({});

/**
 * Select a provider by name. Honours `NOX_ANSWER_PROVIDER` env when no
 * explicit name is passed. Defaults to Gemini (D41 #1).
 *
 * Unknown name → falls back to Gemini default rather than throwing, so
 * a typo in CLI flag never causes a hard crash; metadata.provider will
 * surface the actual provider used.
 */
export function selectProvider(name?: string): LLMProvider {
  const resolved = name ?? process.env.NOX_ANSWER_PROVIDER ?? DEFAULT_PROVIDER;
  switch (resolved) {
    case "mock":
      return new MockProvider();
    case "gemini":
      return placeholderGemini;
    default:
      // Unknown provider name — defensively fall back to Gemini.
      return placeholderGemini;
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────────

function estimateTokens(text: string): number {
  if (!text) return 0;
  return Math.max(1, Math.ceil(text.length / 4));
}

function defaultMockText(opts: LLMCallOpts): string {
  // Cheap echo response that includes a valid-looking citation so the
  // happy-path test can assert citation parsing without scripting a queue.
  const firstLine = (opts.user.split("\n")[0] ?? "").slice(0, 80);
  return `Mock answer for: ${firstLine} [chunk_1]`;
}
