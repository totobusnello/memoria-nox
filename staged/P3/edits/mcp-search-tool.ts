/**
 * src/mcp/tools/search.ts (or wherever nox_mem_search tool is defined) — P3 patch
 *
 * APPLIES ON TOP OF: the existing MCP search tool definition on VPS.
 *
 * Changes: add as_of and changed_since to the JSON Schema inputSchema,
 * and plumb them through to searchHybrid().
 *
 * ── Deployment note ───────────────────────────────────────────────────────────
 * The MCP server is a separate entry point (mcp-server.ts or similar).
 * Find the nox_mem_search tool definition and apply these changes.
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * FIND the existing tool definition (pattern):
 *   {
 *     name: "nox_mem_search",
 *     description: "...",
 *     inputSchema: {
 *       type: "object",
 *       properties: {
 *         query: { type: "string", description: "..." },
 *         limit: { type: "number", description: "..." },
 *       },
 *       required: ["query"],
 *     },
 *   }
 *
 * REPLACE WITH:
 */

{
  name: "nox_mem_search",
  description:
    "Search nox-mem memory using hybrid retrieval (BM25 FTS5 + Gemini semantic + RRF fusion). " +
    "Supports optional temporal filters: as_of for time-travel queries and changed_since " +
    "for recent-changes queries. Both filters are applied as hard SQL filters before ranking.",
  inputSchema: {
    type: "object" as const,
    properties: {
      query: {
        type: "string",
        description: "Search query — natural language, keywords, or entity names.",
      },
      limit: {
        type: "number",
        description: "Number of results to return (default: 5, max: 20).",
      },
      as_of: {
        type: "string",
        description:
          "Time-travel filter: only return chunks that existed on this date. " +
          'Accepts ISO 8601 ("2026-05-01" or "2026-05-01T00:00:00Z") ' +
          'or relative shorthand ("7d" = 7 days ago, "1w" = 1 week ago, ' +
          '"2h" = 2 hours ago, "15m" = 15 minutes ago). ' +
          'Note: "1mo" is not supported — use "30d" instead.',
      },
      changed_since: {
        type: "string",
        description:
          "Recent-changes filter: only return chunks created or updated after this date. " +
          'Accepts ISO 8601 or relative shorthand ("7d", "1w", "2h", "15m"). ' +
          'Can be combined with as_of.',
      },
    },
    required: ["query"],
  },
},

/**
 * ── Handler patch ─────────────────────────────────────────────────────────────
 *
 * In the tool handler (the switch/if block that processes nox_mem_search calls),
 * FIND the existing handler:
 *
 *   const { query, limit = 5 } = args as { query: string; limit?: number };
 *   const results = await searchHybrid(query, limit);
 *   return { content: [{ type: "text", text: formatResults(results) }] };
 *
 * REPLACE WITH:
 */

// (inside the nox_mem_search handler)
const {
  query,
  limit = 5,
  as_of,
  changed_since,
} = args as {
  query: string;
  limit?: number;
  as_of?: string;
  changed_since?: string;
};

const { parseFlexibleDate } = await import("./dates.js");
let asOf: Date | undefined;
let changedSince: Date | undefined;

if (as_of) {
  try { asOf = parseFlexibleDate(as_of); }
  catch (err) {
    return { content: [{ type: "text", text: `Error: ${(err as Error).message}` }], isError: true };
  }
}
if (changed_since) {
  try { changedSince = parseFlexibleDate(changed_since); }
  catch (err) {
    return { content: [{ type: "text", text: `Error: ${(err as Error).message}` }], isError: true };
  }
}

const results = await searchHybrid(query, Math.min(limit, 20), { asOf, changedSince });
return { content: [{ type: "text", text: formatResults(results) }] };
