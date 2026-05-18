/**
 * T1 — stripCodeBlocks helper.
 *
 * Adapted from gbrain/src/core/link-extraction.ts (MIT, Garry Tan, https://github.com/garry-tan/gbrain).
 * Spec: specs/2026-05-18-L4-regex-first-extraction.md §6.1.
 *
 * Replaces fenced ``` blocks (with optional language tag) AND inline `code`
 * with whitespace of equivalent length. Preserving length keeps any downstream
 * offset/line maths stable across the strip — callers can run regexes over the
 * stripped buffer and report locations against the original text.
 */

/** Stable result of stripping. */
export interface StripResult {
  stripped: string;
  hadFences: boolean;
}

/** Match fenced code blocks (```...``` with optional info-string). DOTALL via [\s\S]. */
const FENCE_RE = /```[^\n]*\n[\s\S]*?```/g;
/** Match indented (4-space) code blocks at line start. Multi-line block. */
const INDENTED_BLOCK_RE = /(^|\n)((?:    [^\n]*(?:\n|$))+)/g;
/** Match inline code: balanced single/double/triple backticks on one line. */
const INLINE_CODE_RE = /(`{1,3})([^\n`]|`(?!`))+?\1/g;

/**
 * Replace each match with same-length whitespace (newlines preserved verbatim
 * so line numbers don't shift).
 */
function blankPreserveNewlines(input: string): string {
  let out = "";
  for (let i = 0; i < input.length; i++) {
    const ch = input[i];
    out += ch === "\n" || ch === "\r" ? ch : " ";
  }
  return out;
}

/**
 * Strip fenced + inline + indented-4 code spans from markdown, returning a
 * length-preserved string safe for further regex matching.
 *
 * Order matters: fences first (so triple-backtick inline doesn't get clipped),
 * then inline backticks.
 */
export function stripCodeBlocks(text: string): StripResult {
  let hadFences = false;
  let out = text.replace(FENCE_RE, (m) => {
    hadFences = true;
    return blankPreserveNewlines(m);
  });
  out = out.replace(INDENTED_BLOCK_RE, (full, prefix: string, body: string) => {
    hadFences = true;
    return prefix + blankPreserveNewlines(body);
  });
  out = out.replace(INLINE_CODE_RE, (m) => {
    hadFences = true;
    return blankPreserveNewlines(m);
  });
  return { stripped: out, hadFences };
}
