/**
 * redact.js — A1 + A1.1 filter pipeline (vanilla JS for browser extension).
 *
 * Single-pass redaction over text. Each pattern is applied in catalog order.
 * Patterns with `validate(normalized)` discard non-validating matches (e.g.
 * 11 random digits that aren't a valid CPF stay as-is — avoid FP).
 *
 * Return shape mirrors staged/privacy filter.ts (TS server side) so callers
 * can keep telemetry consistent across stack.
 *
 * NEVER logs the original text or the redacted values. Only kinds[] + count.
 */

import { ALL_PATTERNS } from "./patterns.js";

/**
 * @typedef {Object} RedactResult
 * @property {string}   text            Texto após redação.
 * @property {number}   redactionCount  Total de substituições aplicadas.
 * @property {string[]} kinds           Kinds que dispararam (deduplicado).
 */

/**
 * Aplica TODA a pipeline de redação.
 *
 * @param {string} rawText
 * @returns {RedactResult}
 */
export function redactAll(rawText) {
  if (typeof rawText !== "string" || rawText.length === 0) {
    return { text: rawText || "", redactionCount: 0, kinds: [] };
  }

  let current = rawText;
  let redactionCount = 0;
  const kindsSet = new Set();

  for (const pat of ALL_PATTERNS) {
    const regex = pat.getRegex();
    let count = 0;

    // Use replace with callback so we can apply validate() per-match.
    current = current.replace(regex, (match) => {
      // If pattern has validate, only redact when it passes (when validate
      // returns true). Match is the captured raw text.
      if (typeof pat.validate === "function") {
        const ok = pat.validate(match);
        if (!ok) return match;
      }
      count++;
      return `[REDACTED:${pat.kind}]`;
    });

    if (count > 0) {
      redactionCount += count;
      kindsSet.add(pat.kind);
    }
  }

  return {
    text: current,
    redactionCount,
    kinds: Array.from(kindsSet),
  };
}

/**
 * Versão "scan-only" — retorna matches sem alterar texto.
 * Útil pra preview UI (mostra ao usuário "vamos redatar X coisas antes de
 * enviar"), sem perder o texto original.
 *
 * @param {string} rawText
 * @returns {{ kinds: string[], totalMatches: number }}
 */
export function scanRedactions(rawText) {
  if (typeof rawText !== "string" || rawText.length === 0) {
    return { kinds: [], totalMatches: 0 };
  }

  let totalMatches = 0;
  const kindsSet = new Set();
  let scratch = rawText;

  for (const pat of ALL_PATTERNS) {
    const regex = pat.getRegex();
    let count = 0;

    // Use replace just to walk matches; mutate scratch to consume them
    // (otherwise overlapping patterns would double-count).
    scratch = scratch.replace(regex, (match) => {
      if (typeof pat.validate === "function" && !pat.validate(match)) {
        return match;
      }
      count++;
      // Replace by spaces of same length to preserve indices in scratch
      return " ".repeat(match.length);
    });

    if (count > 0) {
      totalMatches += count;
      kindsSet.add(pat.kind);
    }
  }

  return { kinds: Array.from(kindsSet), totalMatches };
}
