/**
 * src/plugins/nox-hooks/index.ts — T8: OpenClaw plugin entrypoint.
 *
 * OpenClaw lifecycle (see ~/Claude/Projetos/openclaw-vps/infra/CLAUDE.md):
 *   afterTurn(payload)  → fires after each user/assistant turn
 *   sessionStart(meta)  → fires once at session boot
 *   sessionEnd(summary) → fires at session close
 *
 * This plugin:
 *   1. Constructs HookEvent from OpenClaw payload (role + content + meta).
 *   2. Enqueues into the worker (non-blocking).
 *   3. Never throws — failures are logged via the host's logger and
 *      reported as telemetry; the host turn is unaffected.
 *
 * The worker is created lazily on first afterTurn so the plugin loads
 * even when NOX_HOOKS_ENABLED=0 (Layer 1 will reject the events cheaply).
 */

import { randomUUID } from "node:crypto";

import { createPipeline, type IngestFn, type TelemetrySink } from "../../lib/hooks/pipeline.js";
import { createWorker, type WorkerHandle } from "../../lib/hooks/worker.js";
import { loadConfig } from "../../lib/hooks/config.js";
import type { HookEvent, HookRole, HookSource } from "../../lib/hooks/types.js";

/** Shape of OpenClaw afterTurn payload (subset we care about). */
export interface AfterTurnPayload {
  role: string;
  content?: string;
  text?: string;
  session_id?: string;
  cwd?: string;
  meta?: Record<string, string | number | boolean>;
}

export interface PluginDeps {
  /** Where to send captured chunks. Must be wired at plugin install. */
  ingest: IngestFn;
  /** Telemetry sink (writes to agent_events). */
  telemetry: TelemetrySink;
  /** Override staged-A1 redact. Default = identity (T11 will swap). */
  redact?: (s: string) => { text: string; redactionCount: number; kinds: string[] };
}

export interface PluginHandle {
  afterTurn(payload: AfterTurnPayload): { accepted: boolean; reason: string };
  sessionStart(meta?: { session_id?: string; cwd?: string }): void;
  sessionEnd(): Promise<void>;
  /** Inspection for CLI/HTTP. */
  inspect(): { config: ReturnType<typeof loadConfig>; queueDepth: number };
}

function normalizeRole(r: string): HookRole {
  const s = (r || "").toLowerCase();
  if (s === "user" || s === "assistant" || s === "system" || s === "tool") return s as HookRole;
  return "unknown";
}

function projectSlugFromCwd(cwd: string | undefined): string {
  if (!cwd) return "unknown";
  const parts = cwd.split("/").filter(Boolean);
  return parts[parts.length - 1] ?? "unknown";
}

/**
 * Build a plugin handle. Worker starts on first afterTurn().
 * Each plugin instance owns a single pipeline + worker.
 */
export function createPlugin(deps: PluginDeps): PluginHandle {
  const config = loadConfig();
  const pipeline = createPipeline({
    config,
    ...(deps.redact ? { redact: deps.redact } : {}),
    ingest: deps.ingest,
    telemetry: deps.telemetry,
  });
  const worker: WorkerHandle = createWorker({
    pipeline,
    maxSize: config.queueSize,
    telemetry: deps.telemetry,
  });

  let started = false;
  let sessionId: string | undefined;
  let cwd: string | undefined;
  let autoStart = true;

  function ensureStarted(): void {
    if (autoStart && !started) {
      worker.start();
      started = true;
    }
  }

  return {
    afterTurn(payload: AfterTurnPayload): { accepted: boolean; reason: string } {
      ensureStarted();
      try {
        const content = payload.content ?? payload.text ?? "";
        const role = normalizeRole(payload.role);
        const event: HookEvent = {
          event_id: `evt_${randomUUID()}`,
          source: "openclaw" as HookSource,
          role,
          content,
          session_id: payload.session_id ?? sessionId ?? "openclaw-session",
          project_slug: projectSlugFromCwd(payload.cwd ?? cwd),
          ts: new Date().toISOString(),
          ...(payload.meta ? { meta: payload.meta } : {}),
        };
        const res = worker.enqueue(event);
        return { accepted: res.accepted, reason: res.reason };
      } catch (e) {
        return { accepted: false, reason: `plugin_error:${(e as Error).message}` };
      }
    },

    sessionStart(meta = {}): void {
      sessionId = meta.session_id ?? `s_${randomUUID()}`;
      cwd = meta.cwd;
      ensureStarted();
    },

    async sessionEnd(): Promise<void> {
      if (started) {
        await worker.stop();
        started = false;
      }
    },

    inspect() {
      return { config, queueDepth: worker.stats().queueDepth };
    },
  };
}
