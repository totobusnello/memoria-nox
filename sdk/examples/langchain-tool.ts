/**
 * langchain-tool.ts
 *
 * LangChain (v0.3) tool adapter wrapping the NoxMemClient.
 * Exposes 3 tools: nox_search, nox_answer, nox_kg_path
 *
 * Usage:
 *   import { noxSearchTool, noxAnswerTool, noxKgPathTool } from "./langchain-tool.js";
 *   const agent = await createToolCallingAgent({ tools: [noxSearchTool, noxAnswerTool] });
 */

import { NoxMemClient } from "@nox-mem/client";
import type { SearchResult } from "@nox-mem/client";

// Minimal LangChain tool interface compatible with v0.2+ and v0.3+
interface LangChainTool {
  name: string;
  description: string;
  schema?: Record<string, unknown>;
  call(input: string | Record<string, unknown>): Promise<string>;
}

const client = new NoxMemClient({
  baseUrl: process.env.NOX_API_URL ?? "http://127.0.0.1:18802",
  authToken: process.env.NOX_API_TOKEN,
});

// ─── nox_search ───────────────────────────────────────────────────────────────

export const noxSearchTool: LangChainTool = {
  name: "nox_search",
  description:
    "Search the memoria-nox hybrid memory store. " +
    "Returns ranked chunks relevant to the query. " +
    "Input: a search query string.",
  schema: {
    type: "object",
    properties: {
      query: { type: "string", description: "The search query" },
      limit: { type: "number", description: "Max results (1-20)", default: 5 },
    },
    required: ["query"],
  },

  async call(input): Promise<string> {
    const { query, limit } =
      typeof input === "string"
        ? { query: input, limit: 5 }
        : { query: String(input.query ?? input), limit: Number(input.limit ?? 5) };

    const results: SearchResult[] = await client.search(query, { limit });

    if (results.length === 0) return "No relevant memory found.";

    return results
      .map(
        (r, i) =>
          `[${i + 1}] (score ${r.score?.toFixed(3) ?? "?"}) ${r.content ?? ""}\n` +
          `    Source: ${r.source_path ?? "unknown"}, section: ${r.section ?? "?"}`,
      )
      .join("\n\n");
  },
};

// ─── nox_answer ───────────────────────────────────────────────────────────────

export const noxAnswerTool: LangChainTool = {
  name: "nox_answer",
  description:
    "Answer a question using RAG over the memoria-nox memory store. " +
    "Returns a grounded answer with source citations. " +
    "Requires NOX_ANSWER_ENABLED=1 on the server. " +
    "Input: a natural-language question.",
  schema: {
    type: "object",
    properties: {
      question: { type: "string", description: "The question to answer" },
      top_k: { type: "number", description: "Chunks to retrieve (default 8)", default: 8 },
    },
    required: ["question"],
  },

  async call(input): Promise<string> {
    const { question, top_k } =
      typeof input === "string"
        ? { question: input, top_k: 8 }
        : { question: String(input.question ?? input), top_k: Number(input.top_k ?? 8) };

    const { answer, citations, metadata } = await client.answer(question, { top_k });

    const citationLines = citations
      .map((c) => `  [${c.marker_id}] ${c.file_path ?? "?"}: ${c.snippet ?? ""}`)
      .join("\n");

    return [
      answer,
      "",
      `Citations (${citations.length}):`,
      citationLines,
      "",
      `Model: ${metadata.model ?? "?"}, latency: ${metadata.latency_ms ?? "?"}ms`,
    ].join("\n");
  },
};

// ─── nox_kg_path ──────────────────────────────────────────────────────────────

export const noxKgPathTool: LangChainTool = {
  name: "nox_kg_path",
  description:
    "Find the shortest relation path between two entities in the memoria-nox knowledge graph. " +
    "Useful for understanding how two concepts are connected. " +
    "Input: two entity names.",
  schema: {
    type: "object",
    properties: {
      from: { type: "string", description: "Source entity canonical name" },
      to: { type: "string", description: "Target entity canonical name" },
    },
    required: ["from", "to"],
  },

  async call(input): Promise<string> {
    if (typeof input === "string") {
      return "Error: input must be an object with 'from' and 'to' fields.";
    }
    const from = String(input.from);
    const to = String(input.to);

    const path = await client.kgPath(from, to);

    if (!path) return `No path found between "${from}" and "${to}".`;
    return `Path: ${path.join(" → ")} (${path.length - 1} hops)`;
  },
};
