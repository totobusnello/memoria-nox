/**
 * src/providers/index.ts — Public registry / factories (T2 + T8).
 *
 * Two factories drive provider selection:
 *   - selectEmbeddingProvider(name?)
 *   - selectLLMProvider(name?)
 *
 * Resolution order:
 *   1. explicit `name` arg
 *   2. env var `NOX_EMBEDDING_PROVIDER` / `NOX_LLM_PROVIDER`
 *   3. default = 'gemini' (D41)
 *
 * Model override:
 *   - `NOX_EMBEDDING_MODEL=text-embedding-3-large`
 *   - `NOX_LLM_MODEL=gemini-2.5-flash`     (CLAUDE.md regra #3 — explicit only)
 *
 * Boot-time health check (T8):
 *   - `bootProviderHealth({ embedding?, llm?, failFast? })`
 *   - failFast=true (default) throws `ProviderHealthError` on any down provider
 *   - failFast=false logs a warning via `onWarn` callback; caller continues
 *   - Driven by `NOX_PROVIDER_HEALTH_FAIL_FAST` env (default '1')
 *
 * Stubs (openai/anthropic/voyage) return `ok=false` from healthCheck() by
 * design. boot health by default ONLY probes the *selected* providers, NOT
 * every registered one — so a user who keeps Gemini defaults never gets
 * spurious failures from un-activated stubs.
 */
import type { EmbeddingProvider } from "./embedding/types.js";
import type { LLMProvider } from "./llm/types.js";
import {
  ProviderHealthError,
  UnknownProviderError,
  type HealthStatus,
} from "./types.js";

import { GeminiEmbeddingProvider } from "./embedding/gemini.js";
import { OpenAIEmbeddingProvider } from "./embedding/openai.js";
import { VoyageEmbeddingProvider } from "./embedding/voyage.js";

import { GeminiLLMProvider } from "./llm/gemini.js";
import { OpenAILLMProvider } from "./llm/openai.js";
import { AnthropicLLMProvider } from "./llm/anthropic.js";

// Re-exports — single import surface for the rest of the codebase.
export type { EmbeddingProvider } from "./embedding/types.js";
export type { LLMProvider, CompleteOpts, CompleteResult } from "./llm/types.js";
export type { HealthStatus } from "./types.js";
export {
  MissingKeyError,
  UnknownProviderError,
  NotImplementedError,
  ProviderHealthError,
} from "./types.js";

export const KNOWN_EMBEDDING_PROVIDERS = ["gemini", "openai", "voyage"] as const;
export const KNOWN_LLM_PROVIDERS = ["gemini", "openai", "anthropic"] as const;

export type EmbeddingProviderName = (typeof KNOWN_EMBEDDING_PROVIDERS)[number];
export type LLMProviderName = (typeof KNOWN_LLM_PROVIDERS)[number];

/**
 * Factory: returns an EmbeddingProvider.
 *
 * @param name explicit provider name; else `NOX_EMBEDDING_PROVIDER` env; else 'gemini'
 * @param env  optional env override (test seam)
 *
 * Throws `UnknownProviderError` if name is not in `KNOWN_EMBEDDING_PROVIDERS`.
 * May throw `MissingKeyError` (Gemini) at construction.
 */
export function selectEmbeddingProvider(
  name?: string,
  env: NodeJS.ProcessEnv = process.env,
): EmbeddingProvider {
  const resolvedName = (name ?? env.NOX_EMBEDDING_PROVIDER ?? "gemini").trim();
  const model = env.NOX_EMBEDDING_MODEL;
  // Pass apiKey through so a test-env arg fully isolates from real process.env.
  const apiKey = env.GEMINI_API_KEY;
  switch (resolvedName) {
    case "gemini":
      return new GeminiEmbeddingProvider({ model, apiKey });
    case "openai":
      return new OpenAIEmbeddingProvider({ model });
    case "voyage":
      return new VoyageEmbeddingProvider({ model });
    default:
      throw new UnknownProviderError(resolvedName, KNOWN_EMBEDDING_PROVIDERS);
  }
}

/**
 * Factory: returns an LLMProvider.
 *
 * @param name explicit provider name; else `NOX_LLM_PROVIDER` env; else 'gemini'
 * @param env  optional env override (test seam)
 *
 * Throws `UnknownProviderError` if unknown. Gemini may throw `MissingKeyError`
 * at construction.
 *
 * Default model for gemini is `gemini-2.5-flash-lite` (D41). Override via
 * `NOX_LLM_MODEL` env (CLAUDE.md regra #3: switching to flash full is opt-in).
 */
export function selectLLMProvider(
  name?: string,
  env: NodeJS.ProcessEnv = process.env,
): LLMProvider {
  const resolvedName = (name ?? env.NOX_LLM_PROVIDER ?? "gemini").trim();
  const model = env.NOX_LLM_MODEL;
  const apiKey = env.GEMINI_API_KEY;
  switch (resolvedName) {
    case "gemini":
      return new GeminiLLMProvider({ model, apiKey });
    case "openai":
      return new OpenAILLMProvider({ model });
    case "anthropic":
      return new AnthropicLLMProvider({ model });
    default:
      throw new UnknownProviderError(resolvedName, KNOWN_LLM_PROVIDERS);
  }
}

// ─── T8 Boot-time health check ──────────────────────────────────────────────

export interface BootHealthOpts {
  embedding?: EmbeddingProvider;
  llm?: LLMProvider;
  /** Override env-driven fail-fast (`NOX_PROVIDER_HEALTH_FAIL_FAST=0` to soft-warn). */
  failFast?: boolean;
  /** Per-probe timeout in ms. Default 5000. */
  timeoutMs?: number;
  /** Hook for soft-warn mode; receives `{providerName, kind, error}`. */
  onWarn?: (warning: { providerName: string; kind: "embedding" | "llm"; error: string }) => void;
  /** Env override for tests. */
  env?: NodeJS.ProcessEnv;
}

export interface BootHealthReport {
  embedding?: HealthStatus & { providerName: string };
  llm?: HealthStatus & { providerName: string };
  /** True iff every probed provider returned ok=true. */
  allOk: boolean;
}

/**
 * Probe configured providers and (by default) throw if any are down.
 *
 * Returns a structured report regardless of failFast: in soft-warn mode
 * the caller gets the full picture and can decide. In fail-fast mode the
 * report is also returned (alongside the throw) so caller's stack trace
 * shows the actual probe latencies for forensics.
 */
export async function bootProviderHealth(
  opts: BootHealthOpts = {},
): Promise<BootHealthReport> {
  const env = opts.env ?? process.env;
  const failFast =
    opts.failFast ?? !(env.NOX_PROVIDER_HEALTH_FAIL_FAST === "0");
  const timeoutMs = opts.timeoutMs ?? 5000;

  const report: BootHealthReport = { allOk: true };
  const downs: string[] = [];

  if (opts.embedding) {
    const e = opts.embedding;
    const status = await probeWithTimeout(() => e.healthCheck(), timeoutMs);
    report.embedding = { ...status, providerName: e.name };
    if (!status.ok) {
      report.allOk = false;
      downs.push(`embedding:${e.name} (${status.error ?? "unknown"})`);
      opts.onWarn?.({
        providerName: e.name,
        kind: "embedding",
        error: status.error ?? "unknown",
      });
    }
  }

  if (opts.llm) {
    const l = opts.llm;
    const status = await probeWithTimeout(() => l.healthCheck(), timeoutMs);
    report.llm = { ...status, providerName: l.name };
    if (!status.ok) {
      report.allOk = false;
      downs.push(`llm:${l.name} (${status.error ?? "unknown"})`);
      opts.onWarn?.({
        providerName: l.name,
        kind: "llm",
        error: status.error ?? "unknown",
      });
    }
  }

  if (failFast && downs.length > 0) {
    throw new ProviderHealthError(downs.map((d) => d.split(" ")[0] ?? d).join(", "), downs.join("; "));
  }
  return report;
}

/** Wrap a probe in a hard timeout so a hung provider can't block boot forever. */
async function probeWithTimeout(
  fn: () => Promise<HealthStatus>,
  timeoutMs: number,
): Promise<HealthStatus> {
  const t0 = Date.now();
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race<HealthStatus>([
      fn(),
      new Promise<HealthStatus>((_resolve, reject) => {
        timer = setTimeout(() => {
          reject(new Error(`health probe timeout after ${timeoutMs}ms`));
        }, timeoutMs);
      }),
    ]);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return { ok: false, latencyMs: Date.now() - t0, error: msg };
  } finally {
    if (timer) clearTimeout(timer);
  }
}
