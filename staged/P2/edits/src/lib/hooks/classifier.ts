/**
 * src/lib/hooks/classifier.ts — T4: Layer 4 of pipeline.
 *
 * Heuristics-first content classifier. Decides if a redacted text chunk
 * is "worth capturing" or noise. Cheap regex/length checks before any LLM.
 *
 * Heuristics (each contributes a small signal):
 *   - length > NOX_HOOK_MIN_LENGTH (default 20)  → +0.25
 *   - not pure code (no ratio ≥0.8 of /[{};=<>]/) → +0.15
 *   - not pure URLs (≥50% chars in URL tokens drops to 0)
 *   - contains noun-phrase markers (capitalized words, common conjunctions) → +0.20
 *   - contains sentence terminator (. ! ?) → +0.15
 *   - has lowercase + uppercase mix → +0.10
 *   - not just whitespace/punctuation → +0.15
 *
 * Final score in [0, 1]. Decision:
 *   score < 0.4   → reject (low signal)
 *   score > 0.6   → accept
 *   0.4..0.6      → ambiguous; LLM fallback if NOX_HOOK_LLM_CLASSIFY=1, else
 *                   accept (lean towards capture in ambiguous-mid range)
 *
 * No content escapes this module; only score + reason.
 */

import type { CaptureDecision, HookContext } from "./types.js";

export interface ClassifierOpts {
  /** Min chars to even consider capturing. Mirrors config.minLength. */
  minLength?: number;
  /** Allow LLM fallback for ambiguous (score 0.4..0.6). Default false. */
  llmFallback?: boolean;
  /**
   * Pluggable LLM-classify hook. Called only when score ambiguous AND
   * llmFallback=true. Returns {capture, reason}. The pipeline can wire
   * this to flash-lite per D41 if desired.
   */
  llmClassify?: (text: string) => { capture: boolean; reason: string };
}

const URL_RE = /\bhttps?:\/\/\S+/gi;
const CODE_TOKENS_RE = /[{};=<>()[\]]/g;
const SENTENCE_TERM_RE = /[.!?](\s|$)/;
const NOUN_HINT_RE = /\b[A-Z][a-z]{2,}\b|\b(the|a|an|and|or|but|because|when|if|while|that|this)\b/i;
const WHITESPACE_OR_PUNCT_RE = /^[\s\p{P}]+$/u;

/**
 * Score a text in isolation. Pure, deterministic, no LLM.
 */
export function scoreText(text: string, minLength: number): number {
  if (text.length < minLength) return 0;
  if (WHITESPACE_OR_PUNCT_RE.test(text)) return 0;

  let score = 0;
  // Length bonus
  score += 0.25;

  // URL ratio kills the score
  const urlMatches = text.match(URL_RE) ?? [];
  const urlChars = urlMatches.reduce((sum, m) => sum + m.length, 0);
  if (urlChars / text.length >= 0.5) return Math.min(score, 0.1);

  // Code ratio
  const codeChars = (text.match(CODE_TOKENS_RE) ?? []).length;
  const codeRatio = codeChars / Math.max(1, text.length);
  if (codeRatio >= 0.08) {
    // looks like code — heavy penalty
    score -= 0.15;
  } else {
    score += 0.15;
  }

  // Noun-phrase / conjunction hint
  if (NOUN_HINT_RE.test(text)) score += 0.2;

  // Sentence terminator
  if (SENTENCE_TERM_RE.test(text)) score += 0.15;

  // Mixed case (proxy for natural prose)
  if (/[a-z]/.test(text) && /[A-Z]/.test(text)) score += 0.1;

  // Has non-whitespace, non-punct chars
  if (/\w/.test(text)) score += 0.15;

  if (score < 0) score = 0;
  if (score > 1) score = 1;
  return score;
}

/**
 * Apply Layer 4 to a HookContext (uses ctx.redacted.text if present, else event.content).
 */
export function applyClassifier(
  ctx: HookContext,
  opts: ClassifierOpts = {},
): CaptureDecision {
  const minLength = opts.minLength ?? 20;
  const llmFallback = opts.llmFallback ?? false;

  const text = ctx.redacted?.text ?? ctx.event.content;
  const score = scoreText(text, minLength);

  ctx.classification = { score, reason: `heuristic_score=${score.toFixed(2)}` };

  if (score < 0.4) {
    return {
      capture: false,
      reason: `low_signal score=${score.toFixed(2)} len=${text.length}`,
      layer: "classifier",
      score,
    };
  }
  if (score > 0.6) {
    return {
      capture: true,
      reason: `high_signal score=${score.toFixed(2)}`,
      layer: "classifier",
      score,
    };
  }
  // Ambiguous range 0.4..0.6
  if (llmFallback && opts.llmClassify) {
    try {
      const llm = opts.llmClassify(text);
      ctx.classification = {
        score,
        reason: `llm_fallback decision=${llm.capture ? "yes" : "no"} reason=${llm.reason}`,
      };
      return {
        capture: llm.capture,
        reason: `llm_fallback ${llm.reason} (heuristic=${score.toFixed(2)})`,
        layer: "classifier",
        score,
      };
    } catch (e) {
      return {
        capture: true,
        reason: `llm_fallback_failed lean_capture err=${(e as Error).message}`,
        layer: "classifier",
        score,
      };
    }
  }

  // Default: ambiguous → lean towards capture (Toto's bias = better recall over precision here)
  return {
    capture: true,
    reason: `ambiguous_lean_capture score=${score.toFixed(2)}`,
    layer: "classifier",
    score,
  };
}
