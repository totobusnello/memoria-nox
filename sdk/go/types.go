// Package noxmem provides a Go client for the memoria-nox HTTP API
// (openapi 1.0.0-wave-d). Zero external dependencies — standard library only.
package noxmem

// ─── Shared primitives ────────────────────────────────────────────────────────

// ErrorResponse is the standard error envelope returned by the API on non-2xx
// responses.
type ErrorResponse struct {
	Error   string      `json:"error"`
	Code    string      `json:"code,omitempty"`
	Details interface{} `json:"details,omitempty"`
}

// FeatureDisabledError is returned (HTTP 503) when an optional feature is not
// enabled on the server.
type FeatureDisabledError struct {
	Error  string `json:"error"` // always "feature disabled"
	EnvVar string `json:"env_var"`
}

// ─── Health ───────────────────────────────────────────────────────────────────

// ChunkTypeStat holds the count for a single chunk type.
type ChunkTypeStat struct {
	ChunkType string `json:"chunk_type"`
	C         int64  `json:"c"`
}

// ChunksStat aggregates chunk statistics.
type ChunksStat struct {
	Total int64           `json:"total"`
	Types []ChunkTypeStat `json:"types"`
}

// ConsolidationStat holds consolidation run counters.
type ConsolidationStat struct {
	Done   int64  `json:"done"`
	Failed int64  `json:"failed"`
	Last   string `json:"last,omitempty"`
}

// VectorCoverage holds embedding coverage counts.
type VectorCoverage struct {
	Embedded int64 `json:"embedded"`
	Total    int64 `json:"total"`
	Orphans  int64 `json:"orphans"`
}

// KgStat holds knowledge graph entity and relation counts.
type KgStat struct {
	Entities  int64 `json:"entities"`
	Relations int64 `json:"relations"`
}

// ReflectCacheTopQuery is a single entry in the reflect cache query leaderboard.
type ReflectCacheTopQuery struct {
	Query     string `json:"query"`
	Hits      int64  `json:"hits"`
	LastHitAt string `json:"last_hit_at,omitempty"`
}

// ReflectCacheStat holds reflect cache counters.
type ReflectCacheStat struct {
	Entries    int64                  `json:"entries"`
	TotalHits  int64                  `json:"total_hits"`
	TopQueries []ReflectCacheTopQuery `json:"top_queries"`
}

// SearchTelemetry holds aggregated search telemetry over the last 24 hours.
type SearchTelemetry struct {
	Count24h          int64              `json:"count_24h"`
	AvgResults        float64            `json:"avg_results"`
	SemanticRatio     float64            `json:"semantic_ratio"`
	P95LatencyMs      float64            `json:"p95_latency_ms"`
	ExpansionEnabled  bool               `json:"expansion_enabled"`
	SkipReasons       map[string]int64   `json:"skip_reasons"`
}

// ConfidenceDistribution holds confidence score quantiles.
type ConfidenceDistribution struct {
	Mean   float64 `json:"mean"`
	P25    float64 `json:"p25"`
	P50    float64 `json:"p50"`
	P75    float64 `json:"p75"`
	P95    float64 `json:"p95"`
	Stddev float64 `json:"stddev"`
}

// ConfidenceProvenance holds counts per provenance kind.
type ConfidenceProvenance struct {
	Observed   int64 `json:"observed"`
	Declared   int64 `json:"declared"`
	Inferred   int64 `json:"inferred"`
	Derived    int64 `json:"derived"`
	UserMarked int64 `json:"user-marked"`
	Null       int64 `json:"null"`
}

// ConfidenceHealthSlice is the optional confidence sub-object in HealthResponse.
// Present only when NOX_RANKING_CONFIDENCE=shadow or active.
type ConfidenceHealthSlice struct {
	RankingMode              string                  `json:"ranking_mode,omitempty"`
	Provenance               *ConfidenceProvenance   `json:"provenance,omitempty"`
	ConfidenceDistribution   *ConfidenceDistribution `json:"confidence_distribution,omitempty"`
	SupersededCount          int64                   `json:"superseded_count"`
}

// HealthResponse is the full response body from GET /api/health.
type HealthResponse struct {
	Chunks          *ChunksStat            `json:"chunks,omitempty"`
	Consolidation   *ConsolidationStat     `json:"consolidation,omitempty"`
	VectorCoverage  *VectorCoverage        `json:"vectorCoverage,omitempty"`
	KnowledgeGraph  *KgStat                `json:"knowledgeGraph,omitempty"`
	ReflectCache    *ReflectCacheStat      `json:"reflectCache,omitempty"`
	Procedures      *int64                 `json:"procedures,omitempty"`
	SearchTelemetry *SearchTelemetry       `json:"searchTelemetry,omitempty"`
	Services        map[string]bool        `json:"services,omitempty"`
	DbSizeMB        *float64               `json:"dbSizeMB,omitempty"`
	Confidence      *ConfidenceHealthSlice `json:"confidence,omitempty"`
}

// ─── Search ───────────────────────────────────────────────────────────────────

// SearchRequest is the body for POST /api/search.
type SearchRequest struct {
	Q            string `json:"q"`
	Limit        *int   `json:"limit,omitempty"`
	AsOf         string `json:"as_of,omitempty"`
	ChangedSince string `json:"changed_since,omitempty"`
}

// SearchResult is a single ranked result from /api/search.
type SearchResult struct {
	ChunkID    int64   `json:"chunk_id"`
	Content    string  `json:"content"`
	Score      float64 `json:"score"`
	SourcePath string  `json:"source_path,omitempty"`
	Section    string  `json:"section,omitempty"`
	ChunkType  string  `json:"chunk_type,omitempty"`
	CreatedAt  string  `json:"created_at,omitempty"`
}

// ─── KG ───────────────────────────────────────────────────────────────────────

// KgEntity is a knowledge graph entity.
type KgEntity struct {
	ID         int64  `json:"id"`
	Name       string `json:"name"`
	EntityType string `json:"type,omitempty"`
	Mentions   int64  `json:"mentions"`
}

// KgRelation is a knowledge graph relation (source→predicate→target).
type KgRelation struct {
	Source     string  `json:"source"`
	Relation   string  `json:"relation"`
	Target     string  `json:"target"`
	Confidence float64 `json:"confidence,omitempty"`
}

// KgResponse is the body of GET /api/kg.
type KgResponse struct {
	Entities  []KgEntity  `json:"entities"`
	Relations []KgRelation `json:"relations"`
}

// ─── Reflect / Procedures ─────────────────────────────────────────────────────

// Procedure is a crystallized step-by-step runbook stored in memory.
type Procedure struct {
	ID        int64    `json:"id"`
	Title     string   `json:"title"`
	Steps     []string `json:"steps"`
	Agent     string   `json:"agent,omitempty"`
	Tags      []string `json:"tags,omitempty"`
	CreatedAt string   `json:"created_at,omitempty"`
}

// CrystallizeRequest is the body for POST /api/crystallize.
type CrystallizeRequest struct {
	Title        string   `json:"title"`
	Steps        []string `json:"steps"`
	Agent        string   `json:"agent,omitempty"`
	Tags         []string `json:"tags,omitempty"`
	Preconditions []string `json:"preconditions,omitempty"`
}

// CrystallizeResult is the response from POST /api/crystallize.
type CrystallizeResult struct {
	ID int64 `json:"id"`
	OK bool  `json:"ok"`
}

// CrystallizeValidateRequest is the optional body for POST /api/crystallize/validate.
type CrystallizeValidateRequest struct {
	Outcome string `json:"outcome,omitempty"` // success|failure|partial
	Agent   string `json:"agent,omitempty"`
	Notes   string `json:"notes,omitempty"`
}

// ─── Answer (P1) ──────────────────────────────────────────────────────────────

// AnswerRequest is the body for POST /api/answer.
type AnswerRequest struct {
	Question   string  `json:"question"`
	TopK       *int    `json:"top_k,omitempty"`
	MaxTokens  *int    `json:"max_tokens,omitempty"`
	Provider   string  `json:"provider,omitempty"`
	Model      string  `json:"model,omitempty"`
	Temperature *float64 `json:"temperature,omitempty"`
	NoCitations *bool   `json:"no_citations,omitempty"`
	TraceID    string  `json:"trace_id,omitempty"`
}

// Citation is a source chunk reference returned alongside an answer.
type Citation struct {
	ChunkID   int64  `json:"chunk_id"`
	MarkerID  string `json:"marker_id"`
	FilePath  string `json:"file_path"`
	LineRange string `json:"line_range,omitempty"`
	Snippet   string `json:"snippet"`
}

// AnswerMetadata holds telemetry for the answer generation call.
type AnswerMetadata struct {
	LatencyMs     int64   `json:"latency_ms"`
	TokensIn      int64   `json:"tokens_in"`
	TokensOut     int64   `json:"tokens_out"`
	Provider      string  `json:"provider"`
	Model         string  `json:"model"`
	RetrievalCount int64  `json:"retrieval_count"`
	FallbackUsed  bool    `json:"fallback_used"`
	FailedReason  string  `json:"failed_reason,omitempty"`
	RetryCount    int64   `json:"retry_count"`
}

// AnswerSuccess is the successful response from POST /api/answer.
type AnswerSuccess struct {
	Answer    string         `json:"answer"`
	Citations []Citation     `json:"citations"`
	Metadata  AnswerMetadata `json:"metadata"`
	TraceID   string         `json:"trace_id"`
}

// ─── Export / Import (A2) ────────────────────────────────────────────────────

// ExportRequest is the optional body for POST /api/export.
type ExportRequest struct {
	Project           string `json:"project,omitempty"`
	Since             string `json:"since,omitempty"`
	Format            string `json:"format,omitempty"` // "tar"
	ExcludeEmbeddings *bool  `json:"exclude_embeddings,omitempty"`
	Encrypt           *bool  `json:"encrypt,omitempty"`
}

// ImportResult is the response from POST /api/import.
type ImportResult struct {
	OpID                 string   `json:"op_id"`
	SchemaVersionArchive int64    `json:"schema_version_archive"`
	SchemaVersionTarget  int64    `json:"schema_version_target"`
	MigrationApplied     []string `json:"migration_applied"`
	ChunksInserted       int64    `json:"chunks_inserted"`
	ChunksSkippedDedup   int64    `json:"chunks_skipped_dedup"`
	KgEntitiesInserted   int64    `json:"kg_entities_inserted"`
	KgEntitiesMerged     int64    `json:"kg_entities_merged"`
	OpsAuditAppended     int64    `json:"ops_audit_appended"`
	EmbeddingsSkipped    int64    `json:"embeddings_skipped"`
	DurationMs           int64    `json:"duration_ms"`
	Warnings             []string `json:"warnings"`
}

// ImportMode controls how a POST /api/import merges the archive.
type ImportMode string

const (
	ImportModeMerge   ImportMode = "merge"
	ImportModeReplace ImportMode = "replace"
)

// ─── Conflict Detection (L2) ─────────────────────────────────────────────────

// KgConflict is a conflict record in the knowledge graph.
type KgConflict struct {
	ID               int64    `json:"id"`
	ConflictType     string   `json:"conflict_type"`
	SourceEntityID   int64    `json:"source_entity_id"`
	SourceEntityName string   `json:"source_entity_name"`
	Predicate        string   `json:"predicate"`
	Status           string   `json:"status"`
	DetectedAt       string   `json:"detected_at"`
	RelationIDs      []int64  `json:"relation_ids"`
}

// ConflictStatus filter values for GET /api/kg/conflicts.
type ConflictStatus string

const (
	ConflictStatusUnresolved   ConflictStatus = "unresolved"
	ConflictStatusResolved     ConflictStatus = "resolved"
	ConflictStatusAutoResolved ConflictStatus = "auto_resolved"
	ConflictStatusDismissed    ConflictStatus = "dismissed"
)

// ─── Confidence / Marking (L3) ───────────────────────────────────────────────

// MarkKind is the mark to apply to a chunk.
type MarkKind string

const (
	MarkKindCanonical MarkKind = "canonical"
	MarkKindRefuted   MarkKind = "refuted"
	MarkKindStale     MarkKind = "stale"
)

// MarkRequest is the body for POST /api/chunk/{id}/mark.
type MarkRequest struct {
	Kind  MarkKind `json:"kind"`
	Notes string   `json:"notes,omitempty"`
}

// MarkApplied contains the values applied by a mark/supersede operation.
type MarkApplied struct {
	Confidence     *float64 `json:"confidence,omitempty"`
	ProvenanceKind string   `json:"provenance_kind,omitempty"`
	SupersededBy   *int64   `json:"superseded_by,omitempty"`
}

// MarkResult is the response from POST /api/chunk/{id}/mark and
// POST /api/chunk/{id}/supersede.
type MarkResult struct {
	OK      bool        `json:"ok"`
	ChunkID int64       `json:"chunk_id"`
	Applied MarkApplied `json:"applied"`
	AuditID int64       `json:"audit_id"`
}

// SupersedeReason is the optional reason for a supersede operation.
type SupersedeReason string

const (
	SupersedeReasonAutoTemporal            SupersedeReason = "auto_supersede_temporal"
	SupersedeReasonManualResolution        SupersedeReason = "manual_resolution"
	SupersedeReasonStaleLinkReconciliation SupersedeReason = "stale_link_reconciliation"
	SupersedeReasonDismiss                 SupersedeReason = "dismiss"
)

// SupersedeRequest is the body for POST /api/chunk/{id}/supersede.
type SupersedeRequest struct {
	ByChunkID int64           `json:"by_chunk_id"`
	Notes     string          `json:"notes,omitempty"`
	Reason    SupersedeReason `json:"reason,omitempty"`
}

// ─── Hooks (P2) ──────────────────────────────────────────────────────────────

// HooksConfig holds the hooks pipeline configuration.
type HooksConfig struct {
	Enabled           bool     `json:"enabled"`
	AllowedSources    []string `json:"allowed_sources"`
	RateLimitPerMin   int64    `json:"rate_limit_per_min"`
	DedupThreshold    float64  `json:"dedup_threshold"`
	LLMClassify       bool     `json:"llm_classify"`
	DryRun            bool     `json:"dry_run"`
	QueueSize         int64    `json:"queue_size"`
	MinLength         int64    `json:"min_length"`
	PIIPolicy         string   `json:"pii_policy"`
}

// HooksStatus is the response from GET /api/hooks/status.
type HooksStatus struct {
	Config           *HooksConfig `json:"config,omitempty"`
	QueueDepth       int64        `json:"queueDepth"`
	RateLimitTokens  int64        `json:"rateLimitTokens"`
}

// HookEventMeta is a single sanitized hook event metadata row.
type HookEventMeta struct {
	EventUUID      string `json:"event_uuid"`
	SessionID      string `json:"session_id"`
	ProjectSlug    string `json:"project_slug"`
	Kind           string `json:"kind"`
	Timestamp      string `json:"timestamp"`
	RedactionCount int64  `json:"redaction_count"`
}

// HooksDryrunRequest is the body for POST /api/hooks/dryrun.
type HooksDryrunRequest struct {
	Text   string `json:"text"`
	Source string `json:"source,omitempty"`
	Role   string `json:"role,omitempty"`
}
