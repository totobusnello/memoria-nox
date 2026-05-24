/**
 * @nox-mem/client — Type-safe HTTP client for the memoria-nox API
 *
 * Generated types from openapi.yaml (1.0.0-wave-d). Hand-crafted fetch wrapper.
 * No runtime dependencies — uses native fetch (Node 18+ / browser).
 */

import type { components } from "./generated/types.js";

// ─── Public re-exports ────────────────────────────────────────────────────────

export type {
  components,
  paths,
  operations,
} from "./generated/types.js";

export type SearchResult = components["schemas"]["SearchResult"];
export type SearchRequest = components["schemas"]["SearchRequest"];
export type HealthResponse = components["schemas"]["HealthResponse"];
export type AgentProfile = components["schemas"]["AgentProfile"];
export type KgResponse = components["schemas"]["KgResponse"];
export type CrossKgResponse = components["schemas"]["CrossKgResponse"];
export type ReflectResult = components["schemas"]["ReflectResult"];
export type Procedure = components["schemas"]["Procedure"];
export type CrystallizeRequest = components["schemas"]["CrystallizeRequest"];
export type CrystallizeValidateRequest = components["schemas"]["CrystallizeValidateRequest"];
export type AnswerRequest = components["schemas"]["AnswerRequest"];
export type AnswerSuccess = components["schemas"]["AnswerSuccess"];
export type AnswerError = components["schemas"]["AnswerError"];
export type ExportRequest = components["schemas"]["ExportRequest"];
export type ImportResult = components["schemas"]["ImportResult"];
export type ViewerEvent = components["schemas"]["ViewerEvent"];
export type SseEventKind = components["schemas"]["SseEventKind"];
export type KgConflict = components["schemas"]["KgConflict"];
export type KgConflictDetail = components["schemas"]["KgConflictDetail"];
export type MarkKind = components["schemas"]["MarkKind"];
export type MarkRequest = components["schemas"]["MarkRequest"];
export type MarkResult = components["schemas"]["MarkResult"];
export type SupersedeRequest = components["schemas"]["SupersedeRequest"];
export type SupersedeReason = components["schemas"]["SupersedeReason"];
export type HooksStatus = components["schemas"]["HooksStatus"];
export type HookEventMeta = components["schemas"]["HookEventMeta"];
export type HooksDryrunRequest = components["schemas"]["HooksDryrunRequest"];
export type HooksDryrunResponse = components["schemas"]["HooksDryrunResponse"];
export type ErrorResponse = components["schemas"]["ErrorResponse"];
export type FeatureDisabledError = components["schemas"]["FeatureDisabledError"];

// ─── Config ───────────────────────────────────────────────────────────────────

export interface NoxMemClientConfig {
  /**
   * Base URL of the memoria-nox HTTP API.
   * Default: http://127.0.0.1:18802
   */
  baseUrl?: string;
  /**
   * Bearer token. Required when the server has NOX_API_TOKEN set.
   * Sent as `Authorization: Bearer <token>` on every request.
   */
  authToken?: string;
  /**
   * Request timeout in milliseconds. Default: 30_000 (30s).
   * Export/import may need higher values for large corpora.
   */
  timeoutMs?: number;
}

// ─── Errors ──────────────────────────────────────────────────────────────────

/** Thrown when the server returns a non-2xx response. */
export class NoxMemApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: ErrorResponse | FeatureDisabledError | AnswerError | Record<string, unknown>,
    public readonly url: string,
  ) {
    super(
      `NoxMem API error ${status} on ${url}: ${
        "error" in body ? String(body.error) : JSON.stringify(body)
      }`,
    );
    this.name = "NoxMemApiError";
  }

  get isFeatureDisabled(): boolean {
    return (
      "env_var" in this.body &&
      (this.body as FeatureDisabledError).error === "feature disabled"
    );
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }
}

// ─── SSE helpers ─────────────────────────────────────────────────────────────

/** Parse a raw SSE text/event-stream chunk into discrete lines. */
function* parseSseLines(chunk: string): Generator<string> {
  const lines = chunk.split(/\r?\n/);
  for (const line of lines) {
    yield line;
  }
}

// ─── Client ──────────────────────────────────────────────────────────────────

export class NoxMemClient {
  private readonly baseUrl: string;
  private readonly authToken?: string;
  private readonly timeoutMs: number;

  constructor(config: NoxMemClientConfig = {}) {
    this.baseUrl = (config.baseUrl ?? "http://127.0.0.1:18802").replace(/\/$/, "");
    this.authToken = config.authToken;
    this.timeoutMs = config.timeoutMs ?? 30_000;
  }

  // ── Internal helpers ──────────────────────────────────────────────────────

  private headers(extra?: Record<string, string>): Record<string, string> {
    const h: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...extra,
    };
    if (this.authToken) {
      h["Authorization"] = `Bearer ${this.authToken}`;
    }
    return h;
  }

  private url(path: string, params?: Record<string, string | number | boolean | undefined>): string {
    const u = new URL(`${this.baseUrl}${path}`);
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        if (v !== undefined) u.searchParams.set(k, String(v));
      }
    }
    return u.toString();
  }

  private async request<T>(
    method: string,
    path: string,
    opts: {
      params?: Record<string, string | number | boolean | undefined>;
      body?: unknown;
      headers?: Record<string, string>;
      signal?: AbortSignal;
    } = {},
  ): Promise<T> {
    const signal =
      opts.signal ?? AbortSignal.timeout(this.timeoutMs);

    const res = await fetch(this.url(path, opts.params), {
      method,
      headers: this.headers(opts.headers),
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      signal,
    });

    if (!res.ok) {
      let errBody: Record<string, unknown>;
      try {
        errBody = (await res.json()) as Record<string, unknown>;
      } catch {
        errBody = { error: res.statusText };
      }
      throw new NoxMemApiError(res.status, errBody, res.url);
    }

    return res.json() as Promise<T>;
  }

  // ── Core ──────────────────────────────────────────────────────────────────

  /**
   * GET /api/health
   * Returns system health: chunk counts, vector coverage, KG stats, services.
   */
  async health(): Promise<HealthResponse> {
    return this.request<HealthResponse>("GET", "/api/health");
  }

  /**
   * GET /api/agents
   * Agent profiles from the cross-agent knowledge graph.
   */
  async agents(): Promise<AgentProfile[]> {
    return this.request<AgentProfile[]>("GET", "/api/agents");
  }

  /**
   * GET /api/reflect
   * Synthesize a reflection over memory for a given query.
   *
   * @param q - Reflection query
   * @param nocache - Bypass the cache and force fresh synthesis
   */
  async reflect(q: string, nocache?: boolean): Promise<ReflectResult> {
    return this.request<ReflectResult>("GET", "/api/reflect", {
      params: { q, nocache: nocache ? "1" : undefined },
    });
  }

  /**
   * GET /api/procedures
   * List all crystallized step-by-step procedures.
   */
  async procedures(): Promise<Procedure[]> {
    const res = await this.request<{ procedures: Procedure[] }>("GET", "/api/procedures");
    return res.procedures;
  }

  /**
   * POST /api/crystallize
   * Store a new step-by-step procedure into memory.
   *
   * @returns The new chunk id
   */
  async crystallize(req: CrystallizeRequest): Promise<{ id: number; ok: true }> {
    return this.request<{ id: number; ok: true }>("POST", "/api/crystallize", { body: req });
  }

  /**
   * POST /api/crystallize/validate
   * Record the execution outcome of a crystallized procedure.
   *
   * @param id - Chunk id of the procedure
   * @param req - Optional outcome/agent/notes body
   */
  async crystallizeValidate(
    id: number,
    req?: CrystallizeValidateRequest,
  ): Promise<{ id: number; ok: boolean; applied?: CrystallizeValidateRequest }> {
    return this.request("POST", "/api/crystallize/validate", {
      params: { id },
      body: req,
    });
  }

  // ── Search ────────────────────────────────────────────────────────────────

  /**
   * GET /api/search
   * Hybrid search (FTS5 BM25 + Gemini semantic + RRF fusion).
   *
   * @param q - Search query
   * @param opts - Optional limit, as_of, changed_since filters
   */
  async search(
    q: string,
    opts?: { limit?: number; as_of?: string; changed_since?: string },
  ): Promise<SearchResult[]> {
    return this.request<SearchResult[]>("GET", "/api/search", {
      params: { q, ...opts },
    });
  }

  /**
   * POST /api/search
   * Hybrid search via POST body (useful for long queries or programmatic use).
   */
  async searchPost(req: SearchRequest): Promise<SearchResult[]> {
    return this.request<SearchResult[]>("POST", "/api/search", { body: req });
  }

  // ── Knowledge Graph ───────────────────────────────────────────────────────

  /**
   * GET /api/kg
   * Knowledge graph snapshot: top entities and relations.
   */
  async kg(): Promise<KgResponse> {
    return this.request<KgResponse>("GET", "/api/kg");
  }

  /**
   * GET /api/kg/path
   * Shortest path between two KG entities by canonical name.
   *
   * @returns Ordered entity names from `from` to `to`, or `null` if no path.
   */
  async kgPath(from: string, to: string): Promise<string[] | null> {
    const res = await this.request<{ path: string[] | null }>("GET", "/api/kg/path", {
      params: { from, to },
    });
    return res.path;
  }

  /**
   * GET /api/cross-kg
   * Merged cross-agent knowledge graph.
   */
  async crossKg(): Promise<CrossKgResponse> {
    return this.request<CrossKgResponse>("GET", "/api/cross-kg");
  }

  // ── Answer (P1) ───────────────────────────────────────────────────────────

  /**
   * POST /api/answer
   * RAG-style question answering with inline citations.
   * Requires NOX_ANSWER_ENABLED=1 on the server.
   *
   * @param question - Natural language question
   * @param opts - Optional top_k, max_tokens, provider, model, temperature, etc.
   */
  async answer(
    question: string,
    opts?: Omit<AnswerRequest, "question">,
  ): Promise<AnswerSuccess> {
    return this.request<AnswerSuccess>("POST", "/api/answer", {
      body: { question, ...opts },
    });
  }

  // ── Export / Import (A2) ──────────────────────────────────────────────────

  /**
   * POST /api/export
   * Export memory to a portable archive (gzip tar).
   * Requires NOX_ARCHIVE_ENABLED=1.
   *
   * Returns a Blob for saving to disk or uploading to storage.
   * For large corpora, the server streams chunks — this method buffers all.
   */
  async export(opts?: ExportRequest): Promise<Blob> {
    const signal = AbortSignal.timeout(this.timeoutMs);
    const res = await fetch(this.url("/api/export"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/gzip, application/octet-stream",
        ...(this.authToken ? { Authorization: `Bearer ${this.authToken}` } : {}),
      },
      body: JSON.stringify(opts ?? {}),
      signal,
    });
    if (!res.ok) {
      let errBody: Record<string, unknown>;
      try {
        errBody = (await res.json()) as Record<string, unknown>;
      } catch {
        errBody = { error: res.statusText };
      }
      throw new NoxMemApiError(res.status, errBody, res.url);
    }
    return res.blob();
  }

  /**
   * POST /api/import
   * Import a portable archive into the database.
   * Requires NOX_ARCHIVE_ENABLED=1.
   *
   * @param archive - Blob or Uint8Array of the gzip tar archive
   * @param opts - Import options (mode, dry_run, force, skip_embeddings)
   */
  async import(
    archive: Blob | Uint8Array | ArrayBuffer,
    opts?: {
      mode?: "merge" | "replace";
      dry_run?: boolean;
      force?: boolean;
      skip_embeddings?: boolean;
    },
  ): Promise<ImportResult> {
    const params: Record<string, string | number | boolean | undefined> = {
      mode: opts?.mode,
      dry_run: opts?.dry_run,
      force: opts?.force,
      skip_embeddings: opts?.skip_embeddings,
    };
    const signal = AbortSignal.timeout(this.timeoutMs);
    const res = await fetch(this.url("/api/import", params), {
      method: "POST",
      headers: {
        "Content-Type": "application/gzip",
        Accept: "application/json",
        ...(this.authToken ? { Authorization: `Bearer ${this.authToken}` } : {}),
      },
      // Uint8Array is BodyInit-compatible directly (ArrayBufferView).
      // Previously passed `.buffer` which is `ArrayBufferLike` (union of
      // ArrayBuffer | SharedArrayBuffer) — TS5.7+ rejects SharedArrayBuffer
      // for BodyInit. Passing the typed array directly avoids the union.
      body: archive,
      signal,
    });
    if (!res.ok) {
      let errBody: Record<string, unknown>;
      try {
        errBody = (await res.json()) as Record<string, unknown>;
      } catch {
        errBody = { error: res.statusText };
      }
      throw new NoxMemApiError(res.status, errBody, res.url);
    }
    return res.json() as Promise<ImportResult>;
  }

  // ── Viewer / SSE (P5) ─────────────────────────────────────────────────────

  /**
   * GET /api/events/stream (SSE)
   * Opens a persistent Server-Sent Events stream from the internal event bus.
   * Requires NOX_VIEWER_ENABLED=1.
   *
   * Returns an AsyncIterable of ViewerEvent. The caller should break the loop
   * (or pass an AbortSignal) to close the connection.
   *
   * @example
   * ```ts
   * for await (const event of client.streamEvents()) {
   *   console.log(event.kind, event.payload);
   * }
   * ```
   */
  async *streamEvents(signal?: AbortSignal): AsyncIterable<ViewerEvent> {
    const res = await fetch(this.url("/api/events/stream"), {
      headers: {
        Accept: "text/event-stream",
        ...(this.authToken ? { Authorization: `Bearer ${this.authToken}` } : {}),
      },
      signal: signal ?? AbortSignal.timeout(this.timeoutMs * 60), // long-lived
    });

    if (!res.ok) {
      let errBody: Record<string, unknown>;
      try {
        errBody = (await res.json()) as Record<string, unknown>;
      } catch {
        errBody = { error: res.statusText };
      }
      throw new NoxMemApiError(res.status, errBody, res.url);
    }

    if (!res.body) {
      throw new Error("Response body is null — SSE not supported");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let currentData = "";
    let currentEvent = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split(/\r?\n/);
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("data:")) {
            currentData += line.slice(5).trim();
          } else if (line.startsWith("event:")) {
            currentEvent = line.slice(6).trim();
          } else if (line === "") {
            // End of event block
            if (currentData) {
              try {
                const parsed = JSON.parse(currentData) as ViewerEvent;
                if (currentEvent) {
                  parsed.kind = currentEvent as SseEventKind;
                }
                yield parsed;
              } catch {
                // Skip malformed events
              }
            }
            currentData = "";
            currentEvent = "";
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  // ── Conflict Detection (L2) ───────────────────────────────────────────────

  /**
   * GET /api/kg/conflicts
   * List KG conflicts with optional status filter.
   * Requires NOX_KG_CONFLICTS_ENABLED=1.
   */
  async listConflicts(opts?: {
    status?: "unresolved" | "resolved" | "auto_resolved" | "dismissed";
    limit?: number;
    offset?: number;
  }): Promise<{ conflicts: KgConflict[]; total: number }> {
    return this.request("GET", "/api/kg/conflicts", { params: opts });
  }

  /**
   * POST /api/kg/conflicts/scan
   * Trigger a conflict detection scan.
   * Requires NOX_KG_CONFLICTS_ENABLED=1.
   */
  async scanConflicts(): Promise<{ op_id: string; detected: number; duration_ms: number }> {
    return this.request("POST", "/api/kg/conflicts/scan");
  }

  /**
   * GET /api/kg/conflicts/{id}
   * Get a single conflict with hydrated entity/relation detail.
   * Requires NOX_KG_CONFLICTS_ENABLED=1.
   */
  async getConflict(id: number): Promise<KgConflictDetail> {
    return this.request<KgConflictDetail>("GET", `/api/kg/conflicts/${id}`);
  }

  /**
   * POST /api/kg/conflicts/{id}/resolve
   * Resolve a conflict by choosing which relation to keep.
   * Requires NOX_KG_CONFLICTS_ENABLED=1.
   */
  async resolveConflict(
    id: number,
    keepRelationId: number,
    notes?: string,
  ): Promise<{ ok: boolean; conflict_id: number }> {
    return this.request("POST", `/api/kg/conflicts/${id}/resolve`, {
      body: { keep_relation_id: keepRelationId, notes },
    });
  }

  /**
   * POST /api/kg/conflicts/{id}/dismiss
   * Dismiss a conflict (keeps chunks but marks it resolved).
   * Requires NOX_KG_CONFLICTS_ENABLED=1.
   */
  async dismissConflict(
    id: number,
    notes?: string,
  ): Promise<{ ok: boolean; conflict_id: number }> {
    return this.request("POST", `/api/kg/conflicts/${id}/dismiss`, {
      body: notes ? { notes } : undefined,
    });
  }

  // ── Confidence / Marking (L3) ─────────────────────────────────────────────

  /**
   * POST /api/chunk/{id}/mark
   * Mark a chunk as canonical, refuted, or stale.
   *
   * - canonical → confidence = 0.95, provenance = user-marked
   * - refuted → confidence = 0.05, provenance = user-marked
   * - stale → confidence = 0.3
   */
  async markChunk(id: number, kind: MarkKind, notes?: string): Promise<MarkResult> {
    return this.request<MarkResult>("POST", `/api/chunk/${id}/mark`, {
      body: { kind, notes } satisfies MarkRequest,
    });
  }

  /**
   * POST /api/chunk/{id}/supersede
   * Mark a chunk as superseded by a newer chunk.
   */
  async supersedeChunk(
    id: number,
    byChunkId: number,
    opts?: { notes?: string; reason?: SupersedeReason },
  ): Promise<MarkResult> {
    return this.request<MarkResult>("POST", `/api/chunk/${id}/supersede`, {
      body: { by_chunk_id: byChunkId, ...opts } satisfies SupersedeRequest,
    });
  }

  // ── Hooks (P2) ────────────────────────────────────────────────────────────

  /**
   * GET /api/hooks/status
   * Hooks pipeline configuration and queue depth.
   * Requires NOX_HOOKS_ENABLED=1.
   */
  async hookStatus(): Promise<HooksStatus> {
    return this.request<HooksStatus>("GET", "/api/hooks/status");
  }

  /**
   * GET /api/hooks/recent
   * Recent hook event metadata (no payloads — sanitized only).
   * Requires NOX_HOOKS_ENABLED=1.
   *
   * @param limit - Max rows to return (1-100, default 20)
   */
  async hookRecent(limit?: number): Promise<HookEventMeta[]> {
    const res = await this.request<{ rows: HookEventMeta[] }>("GET", "/api/hooks/recent", {
      params: limit !== undefined ? { limit } : undefined,
    });
    return res.rows;
  }

  /**
   * POST /api/hooks/dryrun
   * Dry-run text through the hooks pipeline to preview PII redaction, etc.
   * Requires NOX_HOOKS_ENABLED=1.
   */
  async hookDryrun(req: HooksDryrunRequest): Promise<HooksDryrunResponse> {
    return this.request<HooksDryrunResponse>("POST", "/api/hooks/dryrun", { body: req });
  }
}
