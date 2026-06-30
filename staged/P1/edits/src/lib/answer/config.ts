/**
 * src/lib/answer/config.ts — Defaults + env overrides for P1.
 *
 * D41 #1 locks `gemini-2.5-flash-lite` as default.
 * CLAUDE.md regra #3 forbids silent fallback to `gemini-2.5-flash`.
 *
 * Env overrides honoured:
 *   NOX_ANSWER_MODEL      — overrides default model id
 *   NOX_ANSWER_PROVIDER   — overrides provider name
 *   NOX_ANSWER_TEMPERATURE — overrides temperature (parse-float, clamped 0..1)
 *   NOX_ANSWER_TOPK       — overrides top-K (parse-int, clamped 1..20)
 *   NOX_ANSWER_MAX_TOKENS — overrides max output tokens (parse-int, clamped 64..8192)
 *   NOX_ANSWER_TIMEOUT_MS — overrides per-LLM timeout (parse-int, ≥1000)
 */

export const DEFAULT_MODEL = "gemini-2.5-flash-lite";
export const DEFAULT_PROVIDER = "gemini";
export const DEFAULT_TOPK = 8;
export const DEFAULT_MAX_TOKENS = 1500;
export const DEFAULT_TEMPERATURE = 0.2;
export const DEFAULT_TIMEOUT_MS = 15_000;

/** Hard limits — never widen without spec update. */
export const TOPK_MIN = 1;
export const TOPK_MAX = 20;
export const MAX_TOKENS_MIN = 64;
export const MAX_TOKENS_MAX = 8192;

function clampInt(value: number, lo: number, hi: number): number {
  if (!Number.isFinite(value)) return lo;
  return Math.min(hi, Math.max(lo, Math.floor(value)));
}

function clampFloat(value: number, lo: number, hi: number): number {
  if (!Number.isFinite(value)) return lo;
  return Math.min(hi, Math.max(lo, value));
}

function parseEnvInt(name: string, fallback: number, lo: number, hi: number): number {
  const raw = process.env[name];
  if (!raw) return fallback;
  const parsed = parseInt(raw, 10);
  if (!Number.isFinite(parsed)) return fallback;
  return clampInt(parsed, lo, hi);
}

function parseEnvFloat(name: string, fallback: number, lo: number, hi: number): number {
  const raw = process.env[name];
  if (!raw) return fallback;
  const parsed = parseFloat(raw);
  if (!Number.isFinite(parsed)) return fallback;
  return clampFloat(parsed, lo, hi);
}

/** Resolved config object — env wins over hardcoded default, opts win over env. */
export interface ResolvedConfig {
  provider: string;
  model: string;
  topK: number;
  maxTokens: number;
  temperature: number;
  timeoutMs: number;
}

export function resolveConfig(opts: {
  provider?: string;
  model?: string;
  topK?: number;
  maxTokens?: number;
  temperature?: number;
}): ResolvedConfig {
  const envProvider = process.env.NOX_ANSWER_PROVIDER;
  const envModel = process.env.NOX_ANSWER_MODEL;

  const provider = opts.provider ?? envProvider ?? DEFAULT_PROVIDER;
  const model = opts.model ?? envModel ?? DEFAULT_MODEL;

  const topK =
    opts.topK !== undefined
      ? clampInt(opts.topK, TOPK_MIN, TOPK_MAX)
      : parseEnvInt("NOX_ANSWER_TOPK", DEFAULT_TOPK, TOPK_MIN, TOPK_MAX);

  const maxTokens =
    opts.maxTokens !== undefined
      ? clampInt(opts.maxTokens, MAX_TOKENS_MIN, MAX_TOKENS_MAX)
      : parseEnvInt(
          "NOX_ANSWER_MAX_TOKENS",
          DEFAULT_MAX_TOKENS,
          MAX_TOKENS_MIN,
          MAX_TOKENS_MAX
        );

  const temperature =
    opts.temperature !== undefined
      ? clampFloat(opts.temperature, 0, 1)
      : parseEnvFloat("NOX_ANSWER_TEMPERATURE", DEFAULT_TEMPERATURE, 0, 1);

  const timeoutMs = parseEnvInt(
    "NOX_ANSWER_TIMEOUT_MS",
    DEFAULT_TIMEOUT_MS,
    1000,
    120_000
  );

  return { provider, model, topK, maxTokens, temperature, timeoutMs };
}
