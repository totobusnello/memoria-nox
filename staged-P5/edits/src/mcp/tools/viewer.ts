/**
 * T13 — MCP tool: viewer_recent_events
 *
 * Lets Claude (or any MCP client) peek at recent viewer events without
 * opening an SSE connection. Backed by the same Broadcaster's ring buffer.
 *
 * Inputs:
 *   - limit: 1..200 (default 50)
 *   - type_filter: optional ViewerEventKind | "all"
 *
 * Output: array of envelopes (id + event), newest last.
 */

import { Broadcaster, type BroadcastEnvelope } from "../../lib/viewer/broadcast.js";
import { type ViewerEventKind, type ViewerEvent } from "../../lib/viewer/event-types.js";

export const VIEWER_MCP_TOOL_NAME = "viewer_recent_events";

export interface ViewerMcpInput {
  limit?: number;
  type_filter?: ViewerEventKind | "all";
}

export interface ViewerMcpItem {
  id: number;
  ev: ViewerEvent;
}

export interface ViewerMcpOutput {
  count: number;
  items: ViewerMcpItem[];
  ring_size: number;
  filter: ViewerEventKind | "all";
}

const DEFAULT_LIMIT = 50;
const MAX_LIMIT = 200;

export function validateInput(input: ViewerMcpInput): {
  limit: number;
  filter: ViewerEventKind | "all";
} {
  let limit = input.limit ?? DEFAULT_LIMIT;
  if (!Number.isFinite(limit) || limit <= 0) limit = DEFAULT_LIMIT;
  if (limit > MAX_LIMIT) limit = MAX_LIMIT;

  const filter = input.type_filter ?? "all";
  return { limit: Math.floor(limit), filter };
}

export function recentEvents(
  broadcaster: Broadcaster,
  input: ViewerMcpInput = {}
): ViewerMcpOutput {
  const { limit, filter } = validateInput(input);
  const ring = broadcaster.ringSnapshot();
  const filtered: BroadcastEnvelope[] =
    filter === "all"
      ? ring.slice()
      : ring.filter((env) => env.ev.type === filter);
  const tail = filtered.slice(-limit);
  return {
    count: tail.length,
    items: tail.map((env) => ({ id: env.id, ev: env.ev })),
    ring_size: ring.length,
    filter,
  };
}

/** MCP-style tool descriptor. The host wires this into the tools registry. */
export const VIEWER_MCP_DESCRIPTOR = {
  name: VIEWER_MCP_TOOL_NAME,
  description:
    "Returns the last N viewer events from the in-memory ring buffer. " +
    "Useful for peeking at recent ingest/search/KG activity without opening " +
    "an SSE connection. All events are post-redaction.",
  inputSchema: {
    type: "object",
    properties: {
      limit: {
        type: "integer",
        minimum: 1,
        maximum: MAX_LIMIT,
        default: DEFAULT_LIMIT,
        description: "Max events to return (1..200).",
      },
      type_filter: {
        type: "string",
        enum: ["ingest", "search", "kg", "crystallize", "op_audit", "all"],
        default: "all",
        description: "Restrict by event type.",
      },
    },
    additionalProperties: false,
  },
} as const;
