/**
 * src/mcp/tools/hooks.ts — T13: MCP tool wrappers around the CLI/HTTP API.
 *
 * Exposes 4 tools to MCP clients (Claude Desktop, Claude Code, etc.):
 *
 *   nox_hooks_status   → { config, queue_depth }
 *   nox_hooks_recent   → { rows[] }  (metadata only, no content)
 *   nox_hooks_dryrun   → { result, trace }  (input: { text, role?, source? })
 *   nox_hooks_stats    → { last_24h, last_7d }  (counters)
 *
 * Schema follows the Anthropic MCP spec (JSON schema for inputs/outputs).
 * Implementation defers to the same handlers as HTTP (T12) and CLI (T11)
 * to keep one source of truth per verb.
 */

import { handleHooksRequest, type HooksApiDeps } from "../../api/hooks.js";
import { runHooksCommand, type HooksCliDeps } from "../../cli/hooks.js";

export interface McpToolSchema {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

export const HOOK_TOOLS: ReadonlyArray<McpToolSchema> = [
  {
    name: "nox_hooks_status",
    description: "Return current nox-mem hooks pipeline config + queue depth.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "nox_hooks_recent",
    description:
      "Return last N captured events (metadata only — never raw content). Default N=20.",
    inputSchema: {
      type: "object",
      properties: { limit: { type: "integer", minimum: 1, maximum: 100 } },
      additionalProperties: false,
    },
  },
  {
    name: "nox_hooks_dryrun",
    description:
      "Run a single text through all 5 hook layers in dry-run mode. Returns per-layer trace and final decision. Does NOT persist anything.",
    inputSchema: {
      type: "object",
      properties: {
        text: { type: "string", minLength: 1 },
        role: { type: "string", enum: ["user", "assistant", "system", "tool", "unknown"] },
        source: { type: "string", enum: ["openclaw", "cli", "manual", "mcp", "api", "unknown"] },
      },
      required: ["text"],
      additionalProperties: false,
    },
  },
  {
    name: "nox_hooks_stats",
    description: "Return aggregate counters of captures/rejections over last 24h and 7d.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
];

export interface McpDeps extends HooksApiDeps, Pick<HooksCliDeps, "readStats"> {}

/** Dispatch a single MCP tool call by name. */
export async function callHookTool(
  name: string,
  args: Record<string, unknown>,
  deps: McpDeps,
): Promise<{ ok: boolean; content: unknown }> {
  switch (name) {
    case "nox_hooks_status": {
      const resp = await handleHooksRequest({ method: "GET", path: "/api/hooks/status" }, deps);
      return { ok: resp.status === 200, content: resp.body };
    }
    case "nox_hooks_recent": {
      const limit = typeof args["limit"] === "number" ? String(args["limit"]) : "20";
      const resp = await handleHooksRequest(
        { method: "GET", path: "/api/hooks/recent", query: { limit } },
        deps,
      );
      return { ok: resp.status === 200, content: resp.body };
    }
    case "nox_hooks_dryrun": {
      const resp = await handleHooksRequest(
        { method: "POST", path: "/api/hooks/dryrun", body: args },
        deps,
      );
      return { ok: resp.status === 200, content: resp.body };
    }
    case "nox_hooks_stats": {
      const result = await runHooksCommand(["stats"], {
        readRecent: deps.readRecent as HooksCliDeps["readRecent"],
        readStats: deps.readStats,
      });
      return { ok: result.ok, content: result.data ?? { output: result.output } };
    }
    default:
      return { ok: false, content: { error: `unknown tool: ${name}` } };
  }
}
