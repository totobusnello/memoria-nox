/**
 * parser.ts — T1: Markdown code block extractor for DEPLOY-WAVE-B.md
 *
 * Parses markdown and extracts fenced code blocks with language tags.
 * Returns array of CodeBlock with line numbers and surrounding heading context.
 */

import * as fs from "fs";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CodeBlock {
  /** 1-based line number of the opening fence (```) */
  lineNumber: number;
  /** Language tag after fence: "bash", "sql", "typescript", etc. Empty = "" */
  language: string;
  /** Raw content of the block (no fence lines) */
  content: string;
  /** Nearest preceding heading text (e.g. "Step 1 — Schema v11") */
  contextHeading: string;
  /** Full section path, e.g. "4. Step-by-Step Deployment Commands > Step 1 — Schema v11" */
  sectionPath: string;
}

// ---------------------------------------------------------------------------
// Parser
// ---------------------------------------------------------------------------

/**
 * Parse a markdown file and extract all fenced code blocks.
 * Handles nested context from ATX headings (# / ## / ###).
 */
export function parseMarkdown(filePath: string): CodeBlock[] {
  const source = fs.readFileSync(filePath, "utf8");
  return parseMarkdownSource(source);
}

/**
 * Parse markdown source string (useful for testing without file I/O).
 */
export function parseMarkdownSource(source: string): CodeBlock[] {
  const lines = source.split("\n");
  const blocks: CodeBlock[] = [];

  // Heading stack: index = heading level (1-6), value = text
  const headingStack: string[] = Array(7).fill("");

  let inBlock = false;
  let blockStartLine = 0;
  let blockLanguage = "";
  let blockLines: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const lineNumber = i + 1; // 1-based

    // --- Heading detection (ATX style: # Heading) ---
    if (!inBlock) {
      const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);
      if (headingMatch) {
        const level = headingMatch[1].length;
        const text = headingMatch[2].trim();
        headingStack[level] = text;
        // Clear deeper levels
        for (let l = level + 1; l <= 6; l++) headingStack[l] = "";
      }
    }

    // --- Fence detection ---
    const fenceMatch = line.match(/^(`{3,}|~{3,})(\w*)(.*)$/);

    if (!inBlock && fenceMatch) {
      // Opening fence
      inBlock = true;
      blockStartLine = lineNumber;
      blockLanguage = fenceMatch[2].toLowerCase();
      blockLines = [];
      continue;
    }

    if (inBlock) {
      // Check for closing fence (any ``` or ~~~)
      const closingFence = line.match(/^(`{3,}|~{3,})\s*$/);
      if (closingFence) {
        // Emit block
        const contextHeading = buildContextHeading(headingStack);
        const sectionPath = buildSectionPath(headingStack);
        blocks.push({
          lineNumber: blockStartLine,
          language: blockLanguage,
          content: blockLines.join("\n"),
          contextHeading,
          sectionPath,
        });
        inBlock = false;
        blockLines = [];
        blockLanguage = "";
      } else {
        blockLines.push(line);
      }
    }
  }

  return blocks;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildContextHeading(stack: string[]): string {
  // Return deepest non-empty heading
  for (let l = 6; l >= 1; l--) {
    if (stack[l]) return stack[l];
  }
  return "(no heading)";
}

function buildSectionPath(stack: string[]): string {
  const parts: string[] = [];
  for (let l = 1; l <= 6; l++) {
    if (stack[l]) parts.push(stack[l]);
  }
  return parts.join(" > ") || "(root)";
}
