using System.Text.Json.Serialization;

namespace NoxMem.Client.Types;

// ── Core ──────────────────────────────────────────────────────────────────────

/// <summary>GET /api/health response.</summary>
public record HealthResponse(
    [property: JsonPropertyName("chunks")] ChunkStats? Chunks,
    [property: JsonPropertyName("consolidation")] ConsolidationStats? Consolidation,
    [property: JsonPropertyName("vectorCoverage")] VectorCoverage? VectorCoverage,
    [property: JsonPropertyName("knowledgeGraph")] KgStats? KnowledgeGraph,
    [property: JsonPropertyName("reflectCache")] ReflectCache? ReflectCache,
    [property: JsonPropertyName("procedures")] int Procedures,
    [property: JsonPropertyName("searchTelemetry")] SearchTelemetry? SearchTelemetry,
    [property: JsonPropertyName("services")] Dictionary<string, bool>? Services,
    [property: JsonPropertyName("dbSizeMB")] double DbSizeMB,
    [property: JsonPropertyName("confidence")] ConfidenceSlice? Confidence
);

public record ChunkStats(
    [property: JsonPropertyName("total")] int Total,
    [property: JsonPropertyName("types")] List<ChunkTypeCount>? Types
);

public record ChunkTypeCount(
    [property: JsonPropertyName("chunk_type")] string ChunkType,
    [property: JsonPropertyName("c")] int Count
);

public record ConsolidationStats(
    [property: JsonPropertyName("done")] int Done,
    [property: JsonPropertyName("failed")] int Failed,
    [property: JsonPropertyName("last")] string? Last
);

public record VectorCoverage(
    [property: JsonPropertyName("embedded")] int Embedded,
    [property: JsonPropertyName("total")] int Total,
    [property: JsonPropertyName("orphans")] int Orphans
);

public record KgStats(
    [property: JsonPropertyName("entities")] int Entities,
    [property: JsonPropertyName("relations")] int Relations
);

public record ReflectCache(
    [property: JsonPropertyName("entries")] int Entries,
    [property: JsonPropertyName("total_hits")] int TotalHits,
    [property: JsonPropertyName("top_queries")] List<ReflectCacheEntry>? TopQueries
);

public record ReflectCacheEntry(
    [property: JsonPropertyName("query")] string Query,
    [property: JsonPropertyName("hits")] int Hits,
    [property: JsonPropertyName("last_hit_at")] string? LastHitAt
);

public record SearchTelemetry(
    [property: JsonPropertyName("count_24h")] int Count24h,
    [property: JsonPropertyName("avg_results")] double AvgResults,
    [property: JsonPropertyName("semantic_ratio")] double SemanticRatio,
    [property: JsonPropertyName("p95_latency_ms")] int P95LatencyMs,
    [property: JsonPropertyName("expansion_enabled")] bool ExpansionEnabled,
    [property: JsonPropertyName("skip_reasons")] Dictionary<string, int>? SkipReasons
);

public record ConfidenceSlice(
    [property: JsonPropertyName("ranking_mode")] string? RankingMode,
    [property: JsonPropertyName("provenance")] Dictionary<string, int>? Provenance,
    [property: JsonPropertyName("confidence_distribution")] ConfidenceDist? Distribution,
    [property: JsonPropertyName("superseded_count")] int SupersededCount
);

public record ConfidenceDist(
    [property: JsonPropertyName("mean")] double Mean,
    [property: JsonPropertyName("p25")] double P25,
    [property: JsonPropertyName("p50")] double P50,
    [property: JsonPropertyName("p75")] double P75,
    [property: JsonPropertyName("p95")] double P95,
    [property: JsonPropertyName("stddev")] double Stddev
);

public record AgentProfile(
    [property: JsonPropertyName("agent")] string Agent,
    [property: JsonPropertyName("entity_count")] int EntityCount,
    [property: JsonPropertyName("relation_count")] int RelationCount,
    [property: JsonPropertyName("top_entities")] List<string>? TopEntities,
    [property: JsonPropertyName("last_updated")] string? LastUpdated
);

public record ReflectResult(
    [property: JsonPropertyName("query")] string? Query,
    [property: JsonPropertyName("synthesis")] string? Synthesis,
    [property: JsonPropertyName("supporting_chunk_ids")] List<string>? SupportingChunkIds,
    [property: JsonPropertyName("cache_hit")] bool CacheHit,
    [property: JsonPropertyName("generated_at")] string? GeneratedAt
);

public record Procedure(
    [property: JsonPropertyName("id")] int Id,
    [property: JsonPropertyName("title")] string Title,
    [property: JsonPropertyName("steps")] List<string> Steps,
    [property: JsonPropertyName("agent")] string? Agent,
    [property: JsonPropertyName("tags")] List<string>? Tags,
    [property: JsonPropertyName("created_at")] string? CreatedAt
);

public record CrystallizeRequest(
    [property: JsonPropertyName("title")] string Title,
    [property: JsonPropertyName("steps")] List<string> Steps,
    [property: JsonPropertyName("agent")] string? Agent = null,
    [property: JsonPropertyName("tags")] List<string>? Tags = null
);

public record CrystallizeResult(
    [property: JsonPropertyName("id")] int Id,
    [property: JsonPropertyName("ok")] bool Ok
);

public record CrystallizeValidateRequest(
    [property: JsonPropertyName("outcome")] string? Outcome = null,
    [property: JsonPropertyName("agent")] string? Agent = null,
    [property: JsonPropertyName("notes")] string? Notes = null
);

// ── Search ────────────────────────────────────────────────────────────────────

public record SearchResult(
    [property: JsonPropertyName("chunk_id")] int ChunkId,
    [property: JsonPropertyName("content")] string Content,
    [property: JsonPropertyName("score")] double Score,
    [property: JsonPropertyName("source_path")] string? SourcePath,
    [property: JsonPropertyName("section")] string? Section,
    [property: JsonPropertyName("chunk_type")] string? ChunkType,
    [property: JsonPropertyName("created_at")] string? CreatedAt
);

public record SearchRequest(
    [property: JsonPropertyName("q")] string Q,
    [property: JsonPropertyName("limit")] int? Limit = null,
    [property: JsonPropertyName("as_of")] string? AsOf = null,
    [property: JsonPropertyName("changed_since")] string? ChangedSince = null
);

// ── Knowledge Graph ───────────────────────────────────────────────────────────

public record KgResponse(
    [property: JsonPropertyName("entities")] List<KgEntity> Entities,
    [property: JsonPropertyName("relations")] List<KgRelation> Relations
);

public record KgEntity(
    [property: JsonPropertyName("id")] int Id,
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("type")] string? Type,
    [property: JsonPropertyName("mentions")] int Mentions
);

public record KgRelation(
    [property: JsonPropertyName("source")] string Source,
    [property: JsonPropertyName("relation")] string Relation,
    [property: JsonPropertyName("target")] string Target,
    [property: JsonPropertyName("confidence")] double Confidence
);

public record KgPathResponse(
    [property: JsonPropertyName("path")] List<string>? Path
);

public record CrossKgResponse(
    [property: JsonPropertyName("entities")] List<KgEntity> Entities,
    [property: JsonPropertyName("relations")] List<KgRelation> Relations,
    [property: JsonPropertyName("agents")] List<string>? Agents
);

// ── Answer (P1) ───────────────────────────────────────────────────────────────

public record AnswerRequest(
    [property: JsonPropertyName("question")] string Question,
    [property: JsonPropertyName("top_k")] int? TopK = null,
    [property: JsonPropertyName("max_tokens")] int? MaxTokens = null,
    [property: JsonPropertyName("provider")] string? Provider = null,
    [property: JsonPropertyName("model")] string? Model = null,
    [property: JsonPropertyName("temperature")] double? Temperature = null,
    [property: JsonPropertyName("no_citations")] bool? NoCitations = null,
    [property: JsonPropertyName("trace_id")] string? TraceId = null
);

public record AnswerSuccess(
    [property: JsonPropertyName("answer")] string Answer,
    [property: JsonPropertyName("citations")] List<Citation> Citations,
    [property: JsonPropertyName("metadata")] AnswerMetadata? Metadata,
    [property: JsonPropertyName("trace_id")] string? TraceId
);

public record Citation(
    [property: JsonPropertyName("chunk_id")] int ChunkId,
    [property: JsonPropertyName("marker_id")] string MarkerId,
    [property: JsonPropertyName("file_path")] string? FilePath,
    [property: JsonPropertyName("line_range")] string? LineRange,
    [property: JsonPropertyName("snippet")] string? Snippet
);

public record AnswerMetadata(
    [property: JsonPropertyName("latency_ms")] int LatencyMs,
    [property: JsonPropertyName("tokens_in")] int TokensIn,
    [property: JsonPropertyName("tokens_out")] int TokensOut,
    [property: JsonPropertyName("provider")] string? Provider,
    [property: JsonPropertyName("model")] string? Model,
    [property: JsonPropertyName("retrieval_count")] int RetrievalCount,
    [property: JsonPropertyName("fallback_used")] bool FallbackUsed,
    [property: JsonPropertyName("retry_count")] int RetryCount
);

// ── Export / Import (A2) ──────────────────────────────────────────────────────

public record ExportRequest(
    [property: JsonPropertyName("project")] string? Project = null,
    [property: JsonPropertyName("since")] string? Since = null,
    [property: JsonPropertyName("format")] string? Format = null,
    [property: JsonPropertyName("exclude_embeddings")] bool? ExcludeEmbeddings = null,
    [property: JsonPropertyName("encrypt")] bool? Encrypt = null,
    [property: JsonPropertyName("passphrase")] string? Passphrase = null
);

public record ImportResult(
    [property: JsonPropertyName("op_id")] string? OpId,
    [property: JsonPropertyName("schema_version_archive")] int SchemaVersionArchive,
    [property: JsonPropertyName("schema_version_target")] int SchemaVersionTarget,
    [property: JsonPropertyName("migration_applied")] List<string>? MigrationApplied,
    [property: JsonPropertyName("chunks_inserted")] int ChunksInserted,
    [property: JsonPropertyName("chunks_skipped_dedup")] int ChunksSkippedDedup,
    [property: JsonPropertyName("kg_entities_inserted")] int KgEntitiesInserted,
    [property: JsonPropertyName("kg_entities_merged")] int KgEntitiesMerged,
    [property: JsonPropertyName("ops_audit_appended")] int OpsAuditAppended,
    [property: JsonPropertyName("embeddings_skipped")] int EmbeddingsSkipped,
    [property: JsonPropertyName("duration_ms")] long DurationMs,
    [property: JsonPropertyName("warnings")] List<string>? Warnings
);

// ── SSE / Viewer (P5) ─────────────────────────────────────────────────────────

public record ViewerEvent(
    [property: JsonPropertyName("kind")] string Kind,
    [property: JsonPropertyName("ts")] long Ts,
    [property: JsonPropertyName("payload")] Dictionary<string, object?>? Payload
);

// ── Conflict Detection (L2) ───────────────────────────────────────────────────

public record KgConflict(
    [property: JsonPropertyName("id")] int Id,
    [property: JsonPropertyName("conflict_type")] string? ConflictType,
    [property: JsonPropertyName("source_entity_id")] int SourceEntityId,
    [property: JsonPropertyName("source_entity_name")] string? SourceEntityName,
    [property: JsonPropertyName("predicate")] string? Predicate,
    [property: JsonPropertyName("status")] string? Status,
    [property: JsonPropertyName("detected_at")] string? DetectedAt,
    [property: JsonPropertyName("relation_ids")] List<int>? RelationIds
);

public record KgConflictDetail(
    [property: JsonPropertyName("id")] int Id,
    [property: JsonPropertyName("conflict_type")] string? ConflictType,
    [property: JsonPropertyName("source_entity")] KgEntity? SourceEntity,
    [property: JsonPropertyName("predicate")] string? Predicate,
    [property: JsonPropertyName("conflicting_relations")] List<KgRelation>? ConflictingRelations,
    [property: JsonPropertyName("evidence_chunks")] List<SearchResult>? EvidenceChunks,
    [property: JsonPropertyName("status")] string? Status,
    [property: JsonPropertyName("detected_at")] string? DetectedAt,
    [property: JsonPropertyName("resolved_at")] string? ResolvedAt,
    [property: JsonPropertyName("notes")] string? Notes
);

public record ConflictsResponse(
    [property: JsonPropertyName("conflicts")] List<KgConflict> Conflicts,
    [property: JsonPropertyName("total")] int Total
);

public record ScanConflictsRequest(
    [property: JsonPropertyName("subject")] string? Subject = null,
    [property: JsonPropertyName("dry_run")] bool? DryRun = null
);

public record ScanConflictsResult(
    [property: JsonPropertyName("conflicts_found")] int ConflictsFound,
    [property: JsonPropertyName("conflicts_written")] int ConflictsWritten,
    [property: JsonPropertyName("dry_run")] bool DryRun,
    [property: JsonPropertyName("duration_ms")] int DurationMs
);

public record ResolveConflictRequest(
    [property: JsonPropertyName("keep")] string Keep,  // int as string or "both"
    [property: JsonPropertyName("note")] string? Note = null
);

public record ResolveConflictResult(
    [property: JsonPropertyName("ok")] bool Ok,
    [property: JsonPropertyName("conflict_id")] int ConflictId,
    [property: JsonPropertyName("resolution")] string? Resolution
);

public record DismissConflictResult(
    [property: JsonPropertyName("ok")] bool Ok,
    [property: JsonPropertyName("conflict_id")] int ConflictId
);

// ── Confidence / Mark (L3) ────────────────────────────────────────────────────

public record MarkRequest(
    [property: JsonPropertyName("kind")] string Kind,
    [property: JsonPropertyName("notes")] string? Notes = null
);

public record MarkResult(
    [property: JsonPropertyName("ok")] bool Ok,
    [property: JsonPropertyName("chunk_id")] int ChunkId,
    [property: JsonPropertyName("applied")] MarkApplied? Applied,
    [property: JsonPropertyName("audit_id")] int AuditId
);

public record MarkApplied(
    [property: JsonPropertyName("confidence")] double Confidence,
    [property: JsonPropertyName("provenance_kind")] string? ProvenanceKind
);

public record SupersedeRequest(
    [property: JsonPropertyName("by_chunk_id")] int ByChunkId,
    [property: JsonPropertyName("notes")] string? Notes = null,
    [property: JsonPropertyName("reason")] string? Reason = null
);

// ── Hooks (P2) ────────────────────────────────────────────────────────────────

public record HooksStatus(
    [property: JsonPropertyName("enabled")] bool Enabled,
    [property: JsonPropertyName("queue_depth")] int QueueDepth,
    [property: JsonPropertyName("active_hooks")] List<string>? ActiveHooks,
    [property: JsonPropertyName("config")] Dictionary<string, object?>? Config
);

public record HookEventMeta(
    [property: JsonPropertyName("event_id")] string? EventId,
    [property: JsonPropertyName("hook_name")] string? HookName,
    [property: JsonPropertyName("received_at")] string? ReceivedAt,
    [property: JsonPropertyName("status")] string? Status,
    [property: JsonPropertyName("retries")] int Retries
);

public record HooksDryrunRequest(
    [property: JsonPropertyName("text")] string Text,
    [property: JsonPropertyName("hook_name")] string? HookName = null
);

public record HooksDryrunResult(
    [property: JsonPropertyName("matched_hooks")] List<string>? MatchedHooks,
    [property: JsonPropertyName("pipeline_steps")] List<Dictionary<string, object?>>? PipelineSteps,
    [property: JsonPropertyName("would_ingest")] bool WouldIngest,
    [property: JsonPropertyName("estimated_chunks")] int EstimatedChunks
);

// ── Errors ────────────────────────────────────────────────────────────────────

public record ErrorResponse(
    [property: JsonPropertyName("error")] string? Error
);

public record FeatureDisabledError(
    [property: JsonPropertyName("error")] string? Error,
    [property: JsonPropertyName("env_var")] string? EnvVar
);
