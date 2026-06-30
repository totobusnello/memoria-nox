/**
 * privacy/filter.ts — Pre-storage redaction pipeline.
 *
 * Hook into ingest BEFORE chunk text is written to nox-mem.db.
 * Pipeline:
 *   1. Strip <private>...</private> blocks (tag-parser)
 *   2. Apply regex patterns in sequence (patterns.ts)
 *   3. Credit card candidates filtered through Luhn check
 *
 * Returns cleaned text + telemetry (count + kinds[]).
 * NEVER logs the original text or the values that were redacted.
 */

import { stripPrivateTags } from "./tag-parser.js";
import { REDACTION_PATTERNS, luhn } from "./patterns.js";

export interface RedactResult {
  /** Text with secrets replaced */
  text: string;
  /** Total number of redactions applied */
  redactionCount: number;
  /** Deduplicated list of pattern names that fired */
  kinds: string[];
}

/**
 * Redact secrets from `text` before it is stored as a chunk.
 *
 * @param rawText  Full raw text string (entity content, markdown body, etc.)
 * @returns        { text, redactionCount, kinds }
 */
export function redact(rawText: string): RedactResult {
  const kindsSet = new Set<string>();
  let redactionCount = 0;

  // ── Phase 1: strip user-marked <private> blocks ──────────────────────────
  const { text: afterTags, tagCount } = stripPrivateTags(rawText);
  if (tagCount > 0) {
    redactionCount += tagCount;
    kindsSet.add("user-marked");
  }

  // ── Phase 2: apply regex patterns ─────────────────────────────────────────
  let current = afterTags;

  for (const pattern of REDACTION_PATTERNS) {
    // Reset lastIndex for global regexes (important — they share state if reused)
    pattern.regex.lastIndex = 0;

    if (pattern.name === "credit-card") {
      // Credit card: apply Luhn validation to candidates before replacing
      let count = 0;
      current = current.replace(pattern.regex, (match) => {
        const digits = match.replace(/[-\s]/g, "");
        if (digits.length === 16 && luhn(digits)) {
          count++;
          return pattern.replacement;
        }
        // Not Luhn-valid — return unchanged (e.g., UUID, hash)
        return match;
      });
      if (count > 0) {
        redactionCount += count;
        kindsSet.add(pattern.name);
      }
    } else {
      // All other patterns: straightforward replace + count occurrences
      let count = 0;
      const replaced = current.replace(pattern.regex, (match) => {
        // aws-secret-key and env-secret patterns include the key name in match,
        // replacement already preserves that prefix via the pattern's replacement string
        void match;
        count++;
        return pattern.replacement;
      });
      if (count > 0) {
        current = replaced;
        redactionCount += count;
        kindsSet.add(pattern.name);
      }
    }
  }

  return {
    text: current,
    redactionCount,
    kinds: Array.from(kindsSet),
  };
}
