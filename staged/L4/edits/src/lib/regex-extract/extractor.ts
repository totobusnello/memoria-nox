/**
 * T3 + T5 — Entity ref + code-path extractors.
 *
 * Pure functions: no IO, no DB, no async. Caller composes with stripCodeBlocks
 * (default) and frontmatter parsing in the router (T6).
 *
 * Adapted from gbrain/src/core/link-extraction.ts (MIT) — adjusted to nox-mem
 * domain (DIR_PATTERN whitelist, FK-id resolution deferred to router).
 *
 * Spec: specs/2026-05-18-L4-regex-first-extraction.md §6.2-§6.4.
 */

import { stripCodeBlocks } from "./strip-code.js";
import {
  buildBareRefRe,
  buildCodeRefRe,
  buildMarkdownLinkRe,
  buildWikilinkRe,
} from "./patterns.js";
import {
  CodeRef,
  EntityRef,
  NOX_ENTITY_TYPES,
  NoxEntityType,
} from "./types.js";

const ENTITY_TYPE_SET: ReadonlySet<string> = new Set(NOX_ENTITY_TYPES);

function asEntityType(value: string): NoxEntityType | null {
  return ENTITY_TYPE_SET.has(value) ? (value as NoxEntityType) : null;
}

function pushRef(
  bucket: Map<string, EntityRef>,
  rawEntityType: string,
  rawSlug: string,
  source: EntityRef["source"],
  display?: string,
): void {
  const entityType = asEntityType(rawEntityType);
  if (!entityType) return;
  const slug = rawSlug.toLowerCase();
  if (!slug) return;
  const key = `${entityType}/${slug}`;
  const existing = bucket.get(key);
  if (existing) {
    // Prefer explicit display from markdown_link/wikilink over bare_ref.
    if (!existing.display && display) existing.display = display;
    return;
  }
  bucket.set(key, { entityType, slug, key, source, display });
}

/**
 * Pure regex-based entity-ref extractor.
 *
 * Pipeline:
 *  1. stripCodeBlocks (suppress matches inside ```code```)
 *  2. Markdown links `[Name](type/slug)`
 *  3. Obsidian wikilinks `[[type/slug|Display]]`
 *  4. Bare refs `type/slug` (boundary-anchored)
 *  5. Dedupe by canonical key
 */
export function extractEntityRefsRegex(content: string): EntityRef[] {
  if (!content) return [];
  const { stripped } = stripCodeBlocks(content);
  const refs = new Map<string, EntityRef>();

  const mdRe = buildMarkdownLinkRe();
  for (const m of stripped.matchAll(mdRe)) {
    pushRef(refs, m[2] ?? "", m[3] ?? "", "markdown_link", m[1]?.trim());
  }

  const wikiRe = buildWikilinkRe();
  for (const m of stripped.matchAll(wikiRe)) {
    pushRef(refs, m[1] ?? "", m[2] ?? "", "wikilink", m[3]?.trim());
  }

  const bareRe = buildBareRefRe();
  for (const m of stripped.matchAll(bareRe)) {
    pushRef(refs, m[1] ?? "", m[2] ?? "", "bare_ref");
  }

  return Array.from(refs.values());
}

/**
 * T5 — extract code-path references (`src/foo.ts:42`, `specs/X.md`).
 *
 * Stripped of code fences first (gbrain pattern — avoid recursive matches
 * inside example fences).
 */
export function extractCodeRefs(content: string): CodeRef[] {
  if (!content) return [];
  const { stripped } = stripCodeBlocks(content);
  const seen = new Map<string, CodeRef>();
  const re = buildCodeRefRe();
  for (const m of stripped.matchAll(re)) {
    const root = (m[1] ?? "").toLowerCase();
    const path = m[2] ?? "";
    if (!root || !path) continue;
    const lineRaw = m[4];
    const line = lineRaw ? Number.parseInt(lineRaw, 10) : undefined;
    const normalized = `${root}/${path}`.toLowerCase();
    const key = `codepath/${normalized}${line ? `:${line}` : ""}`;
    if (seen.has(key)) continue;
    seen.set(key, { root, path, line, key });
  }
  return Array.from(seen.values());
}
