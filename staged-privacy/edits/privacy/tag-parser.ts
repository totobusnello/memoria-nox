/**
 * privacy/tag-parser.ts — Handle user-marked <private>...</private> blocks.
 *
 * Strips content inside <private> tags BEFORE the regex redaction pass.
 * Tags are case-insensitive, allow whitespace before/after, and work across
 * multiple lines. The replacement is `[REDACTED:user-marked]`.
 *
 * Design decision: tag stripping is independent and runs first so that any
 * secrets explicitly marked by the author are handled even if the regex pass
 * would miss them (e.g., non-standard formats, obfuscated values).
 *
 * Nesting: nested tags are NOT supported — the first `</private>` closes the
 * block. This is intentional: nested marks are unlikely in practice and
 * supporting them adds regex complexity with no real benefit.
 */

const PRIVATE_TAG_RE = /<private>[\s\S]*?<\/private>/gi;
const PRIVATE_REPLACEMENT = "[REDACTED:user-marked]";

export interface TagStripResult {
  text: string;
  tagCount: number;
}

/**
 * Strip all `<private>...</private>` blocks from text.
 * Returns the cleaned text and the number of blocks removed.
 */
export function stripPrivateTags(text: string): TagStripResult {
  let tagCount = 0;
  const cleaned = text.replace(PRIVATE_TAG_RE, () => {
    tagCount++;
    return PRIVATE_REPLACEMENT;
  });
  return { text: cleaned, tagCount };
}
