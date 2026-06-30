/**
 * src/lib/hooks/decorators.ts — T10: Explicit user override of classifier.
 *
 * Users (or upstream agents) can mark content with inline annotations:
 *
 *   // @nox:capture      → force capture, bypassing classifier (but NOT
 *                          privacy filter or rate-limit/dedup)
 *   // @nox:skip         → force skip, short-circuit pipeline immediately
 *
 * Supported comment shapes (case-insensitive, leading whitespace allowed):
 *   "// @nox:capture", "/* @nox:capture *\/", "# @nox:capture",
 *   "<!-- @nox:capture -->"
 *
 * The decorator is detected on the FIRST 4 lines of the content body to
 * avoid scanning huge transcripts. False positives in code-style text are
 * acceptable — the user opt-in is explicit.
 */

import type { HookEvent } from "./types.js";

export type Decorator = "capture" | "skip";

const PATTERNS: ReadonlyArray<{ re: RegExp; kind: Decorator }> = [
  { re: /(^|\s)(?:\/\/|#|<!--|\/\*)\s*@nox:capture\b/i, kind: "capture" },
  { re: /(^|\s)(?:\/\/|#|<!--|\/\*)\s*@nox:skip\b/i, kind: "skip" },
];

/**
 * Parse decorators from the first MAX_LINES lines of `content`.
 * Returns deduped, ordered list.
 */
export function parseDecorators(content: string, MAX_LINES = 4): Decorator[] {
  if (!content) return [];
  const head = content.split("\n").slice(0, MAX_LINES).join("\n");
  const seen = new Set<Decorator>();
  for (const p of PATTERNS) {
    if (p.re.test(head)) seen.add(p.kind);
  }
  return Array.from(seen);
}

/**
 * Mutates event.decorators with parsed results if not already set.
 */
export function attachDecorators(event: HookEvent): HookEvent {
  if (event.decorators && event.decorators.length > 0) return event;
  const decorators = parseDecorators(event.content);
  return decorators.length > 0 ? { ...event, decorators } : event;
}

/**
 * Returns "capture" if force-capture decorator present, "skip" if force-skip,
 * else null (no override).
 *
 * Precedence: skip wins over capture (defensive).
 */
export function decoratorOverride(event: HookEvent): Decorator | null {
  const decorators = event.decorators ?? parseDecorators(event.content);
  if (decorators.includes("skip")) return "skip";
  if (decorators.includes("capture")) return "capture";
  return null;
}
