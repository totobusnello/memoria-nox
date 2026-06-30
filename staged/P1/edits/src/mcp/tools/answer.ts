/**
 * src/mcp/tools/answer.ts — P1 T10: `nox_mem_answer` MCP tool.
 *
 * Mirrors the HTTP shape (kickoff §5/§6). Single code path: under the hood
 * we call the same `answer()` library function used by CLI/HTTP. The only
 * difference is the MCP `content` envelope expected by the protocol.
 *
 * MCP tool contract (CallToolResult):
 *   {
 *     content: [{ type: "text", text: "<JSON or human-readable>" }],
 *     isError?: boolean
 *   }
 *
 * We always emit a JSON payload in `content[0].text` so the consumer (LLM
 * agent / Claude desktop) can JSON.parse it deterministically. We also set
 * `isError: true` on hard failures (hallucination_after_retry, llm_error).
 *
 * Registration: production `src/mcp/tools/index.ts` imports
 * `noxMemAnswerTool` and pushes into its tool registry. Shape is intentionally
 * MCP-SDK-agnostic — same factory works with `@modelcontextprotocol/sdk` v0.x
 * or the in-tree minimal MCP runner used by VPS.
 */

import { answer as defaultAnswer, AnswerError } from "../../lib/answer/index.js";
import type { AnswerOpts, AnswerResult } from "../../lib/answer/index.js";
import {
  recordAnswer,
  type TelemetryStore,
} from "../../lib/answer/telemetry.js";

// ─── MCP wire types (minimal — avoids hard dep on SDK package) ────────────

export interface McpToolDefinition {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  handler: (input: unknown, ctx?: McpCallContext) => Promise<McpCallResult>;
}

export interface McpCallContext {
  sessionId?: string | null;
  telemetryStore?: TelemetryStore;
  /** Test seam: replace answer() under test. */
  answer?: (opts: AnswerOpts) => Promise<AnswerResult>;
}

export interface McpCallResult {
  content: Array<{ type: "text"; text: string }>;
  isError?: boolean;
}

// ─── Input schema ─────────────────────────────────────────────────────────

export const INPUT_SCHEMA = {
  type: "object",
  properties: {
    question: { type: "string", minLength: 1, maxLength: 2000 },
    top_k: { type: "integer", minimum: 1, maximum: 20, default: 8 },
    max_tokens: { type: "integer", minimum: 64, maximum: 8192, default: 1500 },
    provider: { type: "string" },
    model: { type: "string" },
    temperature: { type: "number", minimum: 0, maximum: 1 },
    no_citations: { type: "boolean", default: false },
  },
  required: ["question"],
  additionalProperties: false,
} as const;

// ─── Input parsing (defensive — MCP sends arbitrary JSON) ─────────────────

interface ParsedInput {
  question: string;
  topK?: number;
  maxTokens?: number;
  provider?: string;
  model?: string;
  temperature?: number;
  noCitations: boolean;
}

class McpInputError extends Error {}

export function parseInput(input: unknown): ParsedInput {
  if (input === null || typeof input !== "object" || Array.isArray(input)) {
    throw new McpInputError("input must be an object");
  }
  const o = input as Record<string, unknown>;
  if (typeof o.question !== "string" || o.question.trim().length === 0) {
    throw new McpInputError("question is required (non-empty string)");
  }
  if (o.question.length > 2000) {
    throw new McpInputError("question exceeds 2000 chars");
  }

  const parsed: ParsedInput = {
    question: o.question,
    noCitations: false,
  };

  if (o.top_k !== undefined) {
    if (typeof o.top_k !== "number" || !Number.isFinite(o.top_k)) {
      throw new McpInputError("top_k must be a number");
    }
    parsed.topK = o.top_k;
  }
  if (o.max_tokens !== undefined) {
    if (typeof o.max_tokens !== "number" || !Number.isFinite(o.max_tokens)) {
      throw new McpInputError("max_tokens must be a number");
    }
    parsed.maxTokens = o.max_tokens;
  }
  if (o.temperature !== undefined) {
    if (typeof o.temperature !== "number" || !Number.isFinite(o.temperature)) {
      throw new McpInputError("temperature must be a number");
    }
    parsed.temperature = o.temperature;
  }
  if (o.provider !== undefined) {
    if (typeof o.provider !== "string") {
      throw new McpInputError("provider must be a string");
    }
    parsed.provider = o.provider;
  }
  if (o.model !== undefined) {
    if (typeof o.model !== "string") {
      throw new McpInputError("model must be a string");
    }
    parsed.model = o.model;
  }
  if (o.no_citations !== undefined) {
    if (typeof o.no_citations !== "boolean") {
      throw new McpInputError("no_citations must be a boolean");
    }
    parsed.noCitations = o.no_citations;
  }
  return parsed;
}

// ─── Handler factory ──────────────────────────────────────────────────────

const MARKER_RE = /\s?\[chunk_\d+\]/g;

export const noxMemAnswerTool: McpToolDefinition = {
  name: "nox_mem_answer",
  description:
    "Answer a question using the nox-mem corpus with grounded citations [chunk_N]. " +
    "Anti-hallucination guard built-in (retry-once on cited markers not in the retrieval set). " +
    "Returns JSON: { answer, citations[], metadata } in content[0].text.",
  inputSchema: INPUT_SCHEMA as unknown as Record<string, unknown>,

  async handler(input: unknown, ctx?: McpCallContext): Promise<McpCallResult> {
    let parsed: ParsedInput;
    try {
      parsed = parseInput(input);
    } catch (err) {
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              error: true,
              reason: "invalid_input",
              message: (err as Error).message,
            }),
          },
        ],
        isError: true,
      };
    }

    const opts: AnswerOpts = { question: parsed.question };
    if (parsed.topK !== undefined) opts.topK = parsed.topK;
    if (parsed.maxTokens !== undefined) opts.maxTokens = parsed.maxTokens;
    if (parsed.provider !== undefined) opts.provider = parsed.provider;
    if (parsed.model !== undefined) opts.model = parsed.model;
    if (parsed.temperature !== undefined) opts.temperature = parsed.temperature;

    const run = ctx?.answer ?? defaultAnswer;
    try {
      const res = await run(opts);

      if (ctx?.telemetryStore) {
        recordAnswer(ctx.telemetryStore, {
          question: parsed.question,
          citationCount: res.citations.length,
          metadata: res.metadata,
          sessionId: ctx.sessionId ?? null,
        });
      }

      const finalAnswer = parsed.noCitations
        ? res.answer.replace(MARKER_RE, "")
        : res.answer;

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              answer: finalAnswer,
              citations: res.citations,
              metadata: res.metadata,
            }),
          },
        ],
        // retrieval_empty is not an error from MCP's perspective — caller sees
        // citations:[] and the canonical "no memory matches" string.
      };
    } catch (err) {
      if (err instanceof AnswerError) {
        if (ctx?.telemetryStore) {
          recordAnswer(ctx.telemetryStore, {
            question: parsed.question,
            citationCount: 0,
            metadata: {
              latency_ms: (err.metadata.latency_ms as number | undefined) ?? 0,
              tokens_in: (err.metadata.tokens_in as number | undefined) ?? 0,
              tokens_out: (err.metadata.tokens_out as number | undefined) ?? 0,
              provider: (err.metadata.provider as string | undefined) ?? "n/a",
              model: (err.metadata.model as string | undefined) ?? "n/a",
              retrieval_count:
                (err.metadata.retrieval_count as number | undefined) ?? 0,
              fallback_used:
                (err.metadata.fallback_used as boolean | undefined) ?? false,
              failed_reason: err.reason,
            },
            sessionId: ctx.sessionId ?? null,
          });
        }
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                error: true,
                reason: err.reason,
                message: err.message,
                metadata: err.metadata,
              }),
            },
          ],
          isError: true,
        };
      }
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              error: true,
              reason: "internal_error",
              message: (err as Error).message,
            }),
          },
        ],
        isError: true,
      };
    }
  },
};

export default noxMemAnswerTool;
