/**
 * Generated from docs/openapi/openapi.yaml (openapi 3.1.0, version 1.0.0-wave-d)
 *
 * This file is auto-generated. Regenerate with:
 *   npx openapi-typescript ../../docs/openapi/openapi.yaml -o src/generated/types.ts
 *
 * Hand-crafted stub: mirrors the OpenAPI 3.1 spec exactly.
 */

// ─── Paths ───────────────────────────────────────────────────────────────────

export interface paths {
  "/api/health": {
    get: operations["getHealth"];
  };
  "/api/search": {
    get: operations["searchGet"];
    post: operations["searchPost"];
  };
  "/api/agents": {
    get: operations["getAgents"];
  };
  "/api/kg": {
    get: operations["getKg"];
  };
  "/api/kg/path": {
    get: operations["getKgPath"];
  };
  "/api/cross-kg": {
    get: operations["getCrossKg"];
  };
  "/api/reflect": {
    get: operations["getReflect"];
  };
  "/api/procedures": {
    get: operations["getProcedures"];
  };
  "/api/crystallize": {
    post: operations["crystallize"];
  };
  "/api/crystallize/validate": {
    post: operations["crystallizeValidate"];
  };
  "/api/answer": {
    post: operations["postAnswer"];
  };
  "/api/export": {
    post: operations["postExport"];
  };
  "/api/import": {
    post: operations["postImport"];
  };
  "/api/events/stream": {
    get: operations["getEventsStream"];
  };
  "/api/kg/conflicts": {
    get: operations["getKgConflicts"];
  };
  "/api/kg/conflicts/scan": {
    post: operations["postKgConflictsScan"];
  };
  "/api/kg/conflicts/{id}": {
    get: operations["getKgConflict"];
  };
  "/api/kg/conflicts/{id}/resolve": {
    post: operations["resolveKgConflict"];
  };
  "/api/kg/conflicts/{id}/dismiss": {
    post: operations["dismissKgConflict"];
  };
  "/api/chunk/{id}/mark": {
    post: operations["markChunk"];
  };
  "/api/chunk/{id}/supersede": {
    post: operations["supersedeChunk"];
  };
  "/api/hooks/status": {
    get: operations["getHooksStatus"];
  };
  "/api/hooks/recent": {
    get: operations["getHooksRecent"];
  };
  "/api/hooks/dryrun": {
    post: operations["postHooksDryrun"];
  };
  "/viewer/{file}": {
    get: operations["getViewerFile"];
  };
}

// ─── Components / Schemas ────────────────────────────────────────────────────

export interface components {
  schemas: {
    ErrorResponse: {
      error: string;
      code?: string;
      details?: Record<string, unknown> | null;
    };

    FeatureDisabledError: {
      error: "feature disabled";
      env_var: string;
    };

    HealthResponse: {
      chunks?: {
        total?: number;
        types?: Array<{ chunk_type?: string; c?: number }>;
      };
      consolidation?: {
        done?: number;
        failed?: number;
        last?: string | null;
      };
      vectorCoverage?: {
        embedded?: number;
        total?: number;
        orphans?: number;
      };
      knowledgeGraph?: {
        entities?: number;
        relations?: number;
      };
      reflectCache?: {
        entries?: number;
        total_hits?: number;
        top_queries?: Array<{
          query?: string;
          hits?: number;
          last_hit_at?: string | null;
        }>;
      };
      procedures?: number;
      searchTelemetry?: {
        count_24h?: number;
        avg_results?: number;
        semantic_ratio?: number;
        p95_latency_ms?: number;
        expansion_enabled?: boolean;
        skip_reasons?: Record<string, number>;
      };
      services?: Record<string, boolean>;
      dbSizeMB?: number;
      confidence?: components["schemas"]["ConfidenceHealthSlice"];
    };

    ConfidenceHealthSlice: {
      ranking_mode?: components["schemas"]["RankingMode"];
      provenance?: {
        observed?: number;
        declared?: number;
        inferred?: number;
        derived?: number;
        "user-marked"?: number;
        null?: number;
      };
      confidence_distribution?: {
        mean?: number;
        p25?: number;
        p50?: number;
        p75?: number;
        p95?: number;
        stddev?: number;
      };
      superseded_count?: number;
    };

    SearchRequest: {
      q: string;
      limit?: number;
      as_of?: string;
      changed_since?: string;
    };

    SearchResult: {
      chunk_id?: number;
      content?: string;
      score?: number;
      source_path?: string | null;
      section?: "compiled" | "frontmatter" | "timeline" | null;
      chunk_type?: string | null;
      created_at?: string | null;
    };

    AgentProfile: Record<string, unknown>;

    KgResponse: {
      entities?: Array<{
        id?: number;
        name?: string;
        type?: string;
        mentions?: number;
      }>;
      relations?: Array<{
        source?: string;
        relation?: string;
        target?: string;
        confidence?: number;
      }>;
    };

    CrossKgResponse: Record<string, unknown>;

    ReflectResult: Record<string, unknown>;

    Procedure: {
      id?: number;
      title?: string;
      steps?: string[];
      agent?: string | null;
      tags?: string[];
      created_at?: string | null;
    };

    CrystallizeRequest: {
      title: string;
      steps: string[];
      agent?: string | null;
      tags?: string[];
      preconditions?: string[];
    };

    CrystallizeValidateRequest: {
      outcome?: "success" | "failure" | "partial";
      agent?: string;
      notes?: string;
    };

    AnswerRequest: {
      question: string;
      top_k?: number;
      max_tokens?: number;
      provider?: string;
      model?: string;
      temperature?: number;
      no_citations?: boolean;
      trace_id?: string;
    };

    Citation: {
      chunk_id?: number;
      marker_id?: string;
      file_path?: string;
      line_range?: string | null;
      snippet?: string;
    };

    AnswerMetadata: {
      latency_ms?: number;
      tokens_in?: number;
      tokens_out?: number;
      provider?: string;
      model?: string;
      retrieval_count?: number;
      fallback_used?: boolean;
      failed_reason?:
        | "hallucinated_citation"
        | "hallucination_after_retry"
        | "retrieval_empty"
        | "llm_error"
        | "llm_timeout"
        | "invalid_input"
        | null;
      retry_count?: number;
    };

    AnswerSuccess: {
      answer: string;
      citations: components["schemas"]["Citation"][];
      metadata: components["schemas"]["AnswerMetadata"];
      trace_id: string;
    };

    AnswerError: {
      error: true;
      reason:
        | "invalid_body"
        | "unauthorized"
        | "retrieval_empty"
        | "hallucinated_citation"
        | "hallucination_after_retry"
        | "llm_error"
        | "llm_timeout"
        | "internal_error";
      message: string;
      trace_id: string;
    };

    ExportRequest: {
      project?: string | null;
      since?: string | null;
      until?: string | null;
      format?: "tar" | "zip" | "sqlite-dump";
      exclude_embeddings?: boolean;
      exclude_kg?: boolean;
      exclude_audit?: boolean;
      encrypt?: boolean;
      compression_level?: number;
    };

    ImportResult: {
      op_id?: string;
      schema_version_archive?: number;
      schema_version_target?: number;
      migration_applied?: string[];
      chunks_inserted?: number;
      chunks_skipped_dedup?: number;
      kg_entities_inserted?: number;
      kg_entities_merged?: number;
      ops_audit_appended?: number;
      embeddings_skipped?: number;
      duration_ms?: number;
      warnings?: string[];
    };

    ImportError: {
      error_code:
        | "schema_downgrade"
        | "bad_passphrase"
        | "tampered_archive"
        | "missing_aad"
        | "manifest_error"
        | "archive_format_error";
      message: string;
      archive_schema?: number | null;
      target_schema?: number | null;
    };

    SseEventKind:
      | "chunk.created"
      | "chunk.deleted"
      | "kg.entity.created"
      | "kg.relation.created"
      | "search.executed"
      | "provider.call"
      | "op_audit.started"
      | "op_audit.completed"
      | "health.warning";

    /** SSE event payload envelope (parsed from data: line) */
    ViewerEvent: {
      kind: components["schemas"]["SseEventKind"];
      ts: string;
      payload: Record<string, unknown>;
    };

    KgConflict: {
      id?: number;
      conflict_type?: "direct" | "temporal" | "logical" | "transitive";
      source_entity_id?: number;
      source_entity_name?: string;
      predicate?: string;
      status?: "unresolved" | "resolved" | "auto_resolved" | "dismissed";
      detected_at?: string;
      relation_ids?: number[];
    };

    KgConflictDetail: components["schemas"]["KgConflict"] & {
      entities?: Array<Record<string, unknown>>;
      relations?: Array<Record<string, unknown>>;
      evidence_snippets?: Array<{
        chunk_id?: number;
        snippet?: string;
      }>;
    };

    ProvenanceKind:
      | "observed"
      | "declared"
      | "inferred"
      | "derived"
      | "user-marked";

    RankingMode: "disabled" | "shadow" | "active";

    MarkKind: "canonical" | "refuted" | "stale";

    SupersedeReason:
      | "auto_supersede_temporal"
      | "manual_resolution"
      | "stale_link_reconciliation"
      | "dismiss";

    MarkRequest: {
      kind: components["schemas"]["MarkKind"];
      notes?: string;
    };

    SupersedeRequest: {
      by_chunk_id: number;
      notes?: string;
      reason?: components["schemas"]["SupersedeReason"];
    };

    MarkResult: {
      ok: true;
      chunk_id: number;
      applied: {
        confidence?: number;
        provenance_kind?: components["schemas"]["ProvenanceKind"];
        superseded_by?: number | null;
      };
      audit_id: number;
    };

    MarkError: {
      ok: false;
      error: string;
      code: "bad_id" | "bad_body" | "bad_kind" | "bad_by_id" | "not_found" | "runtime";
    };

    HooksStatus: {
      config?: {
        enabled?: boolean;
        allowed_sources?: string[];
        rate_limit_per_min?: number;
        dedup_threshold?: number;
        llm_classify?: boolean;
        dry_run?: boolean;
        queue_size?: number;
        min_length?: number;
        pii_policy?: string;
      };
      queueDepth?: number;
      rateLimitTokens?: number | null;
    };

    HookEventMeta: {
      event_uuid?: string;
      session_id?: string;
      project_slug?: string;
      kind?: string;
      timestamp?: string;
      redaction_count?: number;
    };

    HooksDryrunRequest: {
      text: string;
      source?: string;
      role?: string;
    };

    HooksDryrunResponse: {
      result?: Record<string, unknown>;
      trace?: Array<{
        layer?: string;
        reason?: string;
        redaction_count?: number;
        kind?: string;
      }>;
    };
  };

  responses: {
    BadRequest: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    Unauthorized: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    MethodNotAllowed: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    FeatureDisabled: { content: { "application/json": components["schemas"]["FeatureDisabledError"] } };
    InternalError: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
  };

  securitySchemes: {
    BearerAuth: { type: "http"; scheme: "bearer" };
  };
}

// ─── Operations ──────────────────────────────────────────────────────────────

export interface operations {
  getHealth: {
    responses: {
      200: { content: { "application/json": components["schemas"]["HealthResponse"] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  searchGet: {
    parameters: {
      query: {
        q: string;
        limit?: number;
        as_of?: string;
        changed_since?: string;
      };
    };
    responses: {
      200: { content: { "application/json": components["schemas"]["SearchResult"][] } };
      400: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  searchPost: {
    requestBody: { content: { "application/json": components["schemas"]["SearchRequest"] } };
    responses: {
      200: { content: { "application/json": components["schemas"]["SearchResult"][] } };
      400: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  getAgents: {
    responses: {
      200: { content: { "application/json": components["schemas"]["AgentProfile"][] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  getKg: {
    responses: {
      200: { content: { "application/json": components["schemas"]["KgResponse"] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  getKgPath: {
    parameters: { query: { from: string; to: string } };
    responses: {
      200: { content: { "application/json": { path: string[] | null } } };
      400: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  getCrossKg: {
    responses: {
      200: { content: { "application/json": components["schemas"]["CrossKgResponse"] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  getReflect: {
    parameters: { query: { q: string; nocache?: "1" | "true" | "0" | "false" } };
    responses: {
      200: { content: { "application/json": components["schemas"]["ReflectResult"] } };
      400: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  getProcedures: {
    responses: {
      200: { content: { "application/json": { procedures: components["schemas"]["Procedure"][] } } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  crystallize: {
    requestBody: { content: { "application/json": components["schemas"]["CrystallizeRequest"] } };
    responses: {
      200: { content: { "application/json": { id: number; ok: true } } };
      400: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
      405: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  crystallizeValidate: {
    parameters: { query: { id: number } };
    requestBody?: { content: { "application/json": components["schemas"]["CrystallizeValidateRequest"] } };
    responses: {
      200: { content: { "application/json": { id: number; ok: boolean; applied?: components["schemas"]["CrystallizeValidateRequest"] } } };
      400: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
      404: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  postAnswer: {
    requestBody: { content: { "application/json": components["schemas"]["AnswerRequest"] } };
    responses: {
      200: { content: { "application/json": components["schemas"]["AnswerSuccess"] } };
      400: { content: { "application/json": components["schemas"]["AnswerError"] } };
      401: { content: { "application/json": components["schemas"]["AnswerError"] } };
      422: { content: { "application/json": components["schemas"]["AnswerError"] } };
      500: { content: { "application/json": components["schemas"]["AnswerError"] } };
      502: { content: { "application/json": components["schemas"]["AnswerError"] } };
      503: { content: { "application/json": components["schemas"]["AnswerError"] | components["schemas"]["FeatureDisabledError"] } };
      504: { content: { "application/json": components["schemas"]["AnswerError"] } };
    };
  };

  postExport: {
    requestBody?: { content: { "application/json": components["schemas"]["ExportRequest"] } };
    responses: {
      200: { content: { "application/gzip": Blob; "application/octet-stream": Blob } };
      400: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
      401: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
      503: { content: { "application/json": components["schemas"]["FeatureDisabledError"] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  postImport: {
    parameters: {
      query: {
        mode?: "merge" | "replace";
        dry_run?: boolean;
        force?: boolean;
        skip_embeddings?: boolean;
      };
    };
    requestBody: { content: { "application/gzip": Blob; "application/octet-stream": Blob } };
    responses: {
      200: { content: { "application/json": components["schemas"]["ImportResult"] } };
      400: { content: { "application/json": components["schemas"]["ImportError"] } };
      401: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
      422: { content: { "application/json": components["schemas"]["ImportError"] } };
      503: { content: { "application/json": components["schemas"]["FeatureDisabledError"] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  getEventsStream: {
    responses: {
      200: { content: { "text/event-stream": string } };
      401: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
      503: { content: { "application/json": components["schemas"]["FeatureDisabledError"] } };
    };
  };

  getKgConflicts: {
    parameters: {
      query: {
        status?: "unresolved" | "resolved" | "auto_resolved" | "dismissed";
        limit?: number;
        offset?: number;
      };
    };
    responses: {
      200: { content: { "application/json": { conflicts: components["schemas"]["KgConflict"][]; total: number } } };
      503: { content: { "application/json": components["schemas"]["FeatureDisabledError"] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  postKgConflictsScan: {
    responses: {
      200: { content: { "application/json": { op_id: string; detected: number; duration_ms: number } } };
      503: { content: { "application/json": components["schemas"]["FeatureDisabledError"] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  getKgConflict: {
    parameters: { path: { id: number } };
    responses: {
      200: { content: { "application/json": components["schemas"]["KgConflictDetail"] } };
      404: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
      503: { content: { "application/json": components["schemas"]["FeatureDisabledError"] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  resolveKgConflict: {
    parameters: { path: { id: number } };
    requestBody: { content: { "application/json": { keep_relation_id: number; notes?: string } } };
    responses: {
      200: { content: { "application/json": { ok: boolean; conflict_id: number } } };
      404: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
      503: { content: { "application/json": components["schemas"]["FeatureDisabledError"] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  dismissKgConflict: {
    parameters: { path: { id: number } };
    requestBody?: { content: { "application/json": { notes?: string } } };
    responses: {
      200: { content: { "application/json": { ok: boolean; conflict_id: number } } };
      404: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
      503: { content: { "application/json": components["schemas"]["FeatureDisabledError"] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  markChunk: {
    parameters: { path: { id: number } };
    requestBody: { content: { "application/json": components["schemas"]["MarkRequest"] } };
    responses: {
      200: { content: { "application/json": components["schemas"]["MarkResult"] } };
      400: { content: { "application/json": components["schemas"]["MarkError"] } };
      404: { content: { "application/json": components["schemas"]["MarkError"] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  supersedeChunk: {
    parameters: { path: { id: number } };
    requestBody: { content: { "application/json": components["schemas"]["SupersedeRequest"] } };
    responses: {
      200: { content: { "application/json": components["schemas"]["MarkResult"] } };
      400: { content: { "application/json": components["schemas"]["MarkError"] } };
      404: { content: { "application/json": components["schemas"]["MarkError"] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  getHooksStatus: {
    responses: {
      200: { content: { "application/json": components["schemas"]["HooksStatus"] } };
      503: { content: { "application/json": components["schemas"]["FeatureDisabledError"] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  getHooksRecent: {
    parameters: { query: { limit?: number } };
    responses: {
      200: { content: { "application/json": { rows: components["schemas"]["HookEventMeta"][] } } };
      503: { content: { "application/json": components["schemas"]["FeatureDisabledError"] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  postHooksDryrun: {
    requestBody: { content: { "application/json": components["schemas"]["HooksDryrunRequest"] } };
    responses: {
      200: { content: { "application/json": components["schemas"]["HooksDryrunResponse"] } };
      400: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
      503: { content: { "application/json": components["schemas"]["FeatureDisabledError"] } };
      500: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
    };
  };

  getViewerFile: {
    parameters: { path: { file: string } };
    responses: {
      200: { content: { "*/*": string } };
      404: { content: { "application/json": components["schemas"]["ErrorResponse"] } };
      503: { content: { "application/json": components["schemas"]["FeatureDisabledError"] } };
    };
  };
}
