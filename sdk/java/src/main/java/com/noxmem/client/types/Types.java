package com.noxmem.client.types;

import java.util.List;
import java.util.Map;

/**
 * All OpenAPI schema types for the memoria-nox HTTP API (wave-d).
 *
 * Java 17 records are used for immutability. Fields are nullable where the
 * OpenAPI spec marks them as optional or nullable.
 */
public final class Types {

    private Types() {}

    // ── Core ──────────────────────────────────────────────────────────────────

    /** GET /api/health */
    public record HealthResponse(
        ChunkStats chunks,
        ConsolidationStats consolidation,
        VectorCoverage vectorCoverage,
        KgStats knowledgeGraph,
        ReflectCache reflectCache,
        int procedures,
        SearchTelemetry searchTelemetry,
        Map<String, Boolean> services,
        double dbSizeMB,
        ConfidenceSlice confidence  // nullable — only present when L3 enabled
    ) {}

    public record ChunkStats(int total, List<ChunkTypeCount> types) {}
    public record ChunkTypeCount(String chunk_type, int c) {}

    public record ConsolidationStats(int done, int failed, String last) {}

    public record VectorCoverage(int embedded, int total, int orphans) {}

    public record KgStats(int entities, int relations) {}

    public record ReflectCache(int entries, int total_hits, List<ReflectCacheEntry> top_queries) {}
    public record ReflectCacheEntry(String query, int hits, String last_hit_at) {}

    public record SearchTelemetry(
        int count_24h,
        double avg_results,
        double semantic_ratio,
        int p95_latency_ms,
        boolean expansion_enabled,
        Map<String, Integer> skip_reasons
    ) {}

    public record ConfidenceSlice(
        String ranking_mode,
        Map<String, Integer> provenance,
        ConfidenceDist confidence_distribution,
        int superseded_count
    ) {}

    public record ConfidenceDist(
        double mean, double p25, double p50, double p75, double p95, double stddev
    ) {}

    /** GET /api/agents */
    public record AgentProfile(
        String agent,
        int entity_count,
        int relation_count,
        List<String> top_entities,
        String last_updated
    ) {}

    /** GET /api/reflect */
    public record ReflectResult(
        String query,
        String synthesis,
        List<String> supporting_chunk_ids,
        boolean cache_hit,
        String generated_at
    ) {}

    /** GET /api/procedures — one item */
    public record Procedure(
        int id,
        String title,
        List<String> steps,
        String agent,
        List<String> tags,
        String created_at
    ) {}

    /** POST /api/crystallize — request body */
    public record CrystallizeRequest(
        String title,
        List<String> steps,
        String agent,     // nullable
        List<String> tags // nullable
    ) {}

    /** POST /api/crystallize — response */
    public record CrystallizeResult(int id, boolean ok) {}

    /** POST /api/crystallize/validate — request body */
    public record CrystallizeValidateRequest(
        String outcome, // nullable
        String agent,   // nullable
        String notes    // nullable
    ) {}

    // ── Search ────────────────────────────────────────────────────────────────

    /** GET or POST /api/search — single result item */
    public record SearchResult(
        int chunk_id,
        String content,
        double score,
        String source_path,
        String section,     // nullable
        String chunk_type,
        String created_at
    ) {}

    /** POST /api/search — request body */
    public record SearchRequest(
        String q,
        Integer limit,        // nullable
        String as_of,         // nullable
        String changed_since  // nullable
    ) {}

    // ── Knowledge Graph ───────────────────────────────────────────────────────

    public record KgResponse(List<KgEntity> entities, List<KgRelation> relations) {}

    public record KgEntity(int id, String name, String type, int mentions) {}

    public record KgRelation(String source, String relation, String target, double confidence) {}

    public record KgPathResponse(List<String> path) {} // path may be null => empty list

    /** GET /api/cross-kg */
    public record CrossKgResponse(
        List<KgEntity> entities,
        List<KgRelation> relations,
        List<String> agents
    ) {}

    // ── Answer (P1) ───────────────────────────────────────────────────────────

    /** POST /api/answer — request */
    public record AnswerRequest(
        String question,
        Integer top_k,       // nullable
        Integer max_tokens,  // nullable
        String provider,     // nullable
        String model,        // nullable
        Double temperature,  // nullable
        Boolean no_citations,// nullable
        String trace_id      // nullable
    ) {}

    /** POST /api/answer — 200 response */
    public record AnswerSuccess(
        String answer,
        List<Citation> citations,
        AnswerMetadata metadata,
        String trace_id
    ) {}

    public record Citation(
        int chunk_id,
        String marker_id,
        String file_path,
        String line_range,
        String snippet
    ) {}

    public record AnswerMetadata(
        int latency_ms,
        int tokens_in,
        int tokens_out,
        String provider,
        String model,
        int retrieval_count,
        boolean fallback_used,
        int retry_count
    ) {}

    // ── Export / Import (A2) ──────────────────────────────────────────────────

    /** POST /api/export — request body (all optional) */
    public record ExportRequest(
        String project,          // nullable
        String since,            // nullable
        String format,           // nullable — "tar"
        Boolean exclude_embeddings, // nullable
        Boolean encrypt,            // nullable
        String passphrase           // nullable
    ) {}

    /** POST /api/import — 200 response */
    public record ImportResult(
        String op_id,
        int schema_version_archive,
        int schema_version_target,
        List<String> migration_applied,
        int chunks_inserted,
        int chunks_skipped_dedup,
        int kg_entities_inserted,
        int kg_entities_merged,
        int ops_audit_appended,
        int embeddings_skipped,
        long duration_ms,
        List<String> warnings
    ) {}

    // ── Conflict Detection (L2) ───────────────────────────────────────────────

    public record KgConflict(
        int id,
        String conflict_type,
        int source_entity_id,
        String source_entity_name,
        String predicate,
        String status,
        String detected_at,
        List<Integer> relation_ids
    ) {}

    public record KgConflictDetail(
        int id,
        String conflict_type,
        KgEntity source_entity,
        String predicate,
        List<KgRelation> conflicting_relations,
        List<SearchResult> evidence_chunks,
        String status,
        String detected_at,
        String resolved_at,   // nullable
        String notes          // nullable
    ) {}

    public record ConflictsResponse(List<KgConflict> conflicts, int total) {}

    public record ScanConflictsRequest(String subject, Boolean dry_run) {} // both nullable

    public record ScanConflictsResult(
        int conflicts_found,
        int conflicts_written,
        boolean dry_run,
        int duration_ms
    ) {}

    public record ResolveConflictRequest(String keep, String note) {} // keep = int or "both"

    public record ResolveConflictResult(boolean ok, int conflict_id, String resolution) {}

    public record DismissConflictRequest(String note) {} // nullable

    public record DismissConflictResult(boolean ok, int conflict_id) {}

    // ── Confidence / Mark (L3) ────────────────────────────────────────────────

    public record MarkRequest(String kind, String notes) {} // notes nullable

    public record MarkResult(
        boolean ok,
        int chunk_id,
        MarkApplied applied,
        int audit_id
    ) {}

    public record MarkApplied(double confidence, String provenance_kind) {}

    public record SupersedeRequest(int by_chunk_id, String notes, String reason) {} // notes, reason nullable

    // ── Hooks (P2) ────────────────────────────────────────────────────────────

    public record HooksStatus(
        boolean enabled,
        int queue_depth,
        List<String> active_hooks,
        Map<String, Object> config
    ) {}

    public record HookEventMeta(
        String event_id,
        String hook_name,
        String received_at,
        String status,
        int retries
    ) {}

    public record HooksDryrunRequest(String text, String hook_name) {} // hook_name nullable

    public record HooksDryrunResult(
        List<String> matched_hooks,
        List<Map<String, Object>> pipeline_steps,
        boolean would_ingest,
        int estimated_chunks
    ) {}

    // ── SSE / Viewer (P5) ─────────────────────────────────────────────────────

    public record ViewerEvent(
        String kind,
        long ts,
        Map<String, Object> payload
    ) {}

    // ── Errors ────────────────────────────────────────────────────────────────

    public record ErrorResponse(String error) {}

    public record FeatureDisabledError(String error, String env_var) {}
}
