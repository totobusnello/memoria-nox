/// Types transcribed from openapi.yaml 1.0.0-wave-d.
///
/// All structs use `#[serde(default)]` where the field is optional in the spec
/// so partial responses (e.g. gated features) deserialise cleanly.
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;

// ─── Shared primitives ────────────────────────────────────────────────────────

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ErrorResponse {
    pub error: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub code: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub details: Option<Value>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct FeatureDisabledError {
    pub error: String,
    pub env_var: String,
}

// ─── Health ───────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct ChunkTypeStat {
    pub chunk_type: String,
    pub c: i64,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct ChunksStat {
    #[serde(default)]
    pub total: i64,
    #[serde(default)]
    pub types: Vec<ChunkTypeStat>,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct ConsolidationStat {
    #[serde(default)]
    pub done: i64,
    #[serde(default)]
    pub failed: i64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct VectorCoverage {
    #[serde(default)]
    pub embedded: i64,
    #[serde(default)]
    pub total: i64,
    #[serde(default)]
    pub orphans: i64,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct KgStat {
    #[serde(default)]
    pub entities: i64,
    #[serde(default)]
    pub relations: i64,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct ReflectCacheTopQuery {
    #[serde(default)]
    pub query: String,
    #[serde(default)]
    pub hits: i64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last_hit_at: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct ReflectCacheStat {
    #[serde(default)]
    pub entries: i64,
    #[serde(default)]
    pub total_hits: i64,
    #[serde(default)]
    pub top_queries: Vec<ReflectCacheTopQuery>,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct SearchTelemetry {
    #[serde(default)]
    pub count_24h: i64,
    #[serde(default)]
    pub avg_results: f64,
    #[serde(default)]
    pub semantic_ratio: f64,
    #[serde(default)]
    pub p95_latency_ms: f64,
    #[serde(default)]
    pub expansion_enabled: bool,
    #[serde(default)]
    pub skip_reasons: HashMap<String, i64>,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct ConfidenceDistribution {
    #[serde(default)]
    pub mean: f64,
    #[serde(default)]
    pub p25: f64,
    #[serde(default)]
    pub p50: f64,
    #[serde(default)]
    pub p75: f64,
    #[serde(default)]
    pub p95: f64,
    #[serde(default)]
    pub stddev: f64,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct ConfidenceProvenance {
    #[serde(default)]
    pub observed: i64,
    #[serde(default)]
    pub declared: i64,
    #[serde(default)]
    pub inferred: i64,
    #[serde(default)]
    pub derived: i64,
    #[serde(rename = "user-marked", default)]
    pub user_marked: i64,
    #[serde(rename = "null", default)]
    pub null_count: i64,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct ConfidenceHealthSlice {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ranking_mode: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub provenance: Option<ConfidenceProvenance>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub confidence_distribution: Option<ConfidenceDistribution>,
    #[serde(default)]
    pub superseded_count: i64,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct HealthResponse {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub chunks: Option<ChunksStat>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub consolidation: Option<ConsolidationStat>,
    #[serde(rename = "vectorCoverage", skip_serializing_if = "Option::is_none")]
    pub vector_coverage: Option<VectorCoverage>,
    #[serde(rename = "knowledgeGraph", skip_serializing_if = "Option::is_none")]
    pub knowledge_graph: Option<KgStat>,
    #[serde(rename = "reflectCache", skip_serializing_if = "Option::is_none")]
    pub reflect_cache: Option<ReflectCacheStat>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub procedures: Option<i64>,
    #[serde(rename = "searchTelemetry", skip_serializing_if = "Option::is_none")]
    pub search_telemetry: Option<SearchTelemetry>,
    #[serde(default)]
    pub services: HashMap<String, bool>,
    #[serde(rename = "dbSizeMB", skip_serializing_if = "Option::is_none")]
    pub db_size_mb: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub confidence: Option<ConfidenceHealthSlice>,
}

// ─── Search ───────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Default)]
pub struct SearchRequest {
    pub q: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub limit: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub as_of: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub changed_since: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct SearchResult {
    #[serde(default)]
    pub chunk_id: i64,
    #[serde(default)]
    pub content: String,
    #[serde(default)]
    pub score: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub source_path: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub section: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub chunk_type: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub created_at: Option<String>,
}

// ─── KG ───────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct KgEntity {
    #[serde(default)]
    pub id: i64,
    #[serde(default)]
    pub name: String,
    #[serde(rename = "type", skip_serializing_if = "Option::is_none")]
    pub entity_type: Option<String>,
    #[serde(default)]
    pub mentions: i64,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct KgRelation {
    #[serde(default)]
    pub source: String,
    #[serde(default)]
    pub relation: String,
    #[serde(default)]
    pub target: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub confidence: Option<f64>,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct KgResponse {
    #[serde(default)]
    pub entities: Vec<KgEntity>,
    #[serde(default)]
    pub relations: Vec<KgRelation>,
}

/// Merged cross-agent KG — shape mirrors KgResponse with agent attribution.
pub type CrossKgResponse = Value;

// ─── Reflect / Procedures ─────────────────────────────────────────────────────

pub type ReflectResult = Value;

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct Procedure {
    #[serde(default)]
    pub id: i64,
    #[serde(default)]
    pub title: String,
    #[serde(default)]
    pub steps: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub agent: Option<String>,
    #[serde(default)]
    pub tags: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub created_at: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct CrystallizeRequest {
    pub title: String,
    pub steps: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub agent: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tags: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub preconditions: Option<Vec<String>>,
}

#[derive(Debug, Clone, Serialize, Default)]
pub struct CrystallizeValidateRequest {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub outcome: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub agent: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub notes: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct CrystallizeResult {
    pub id: i64,
    pub ok: bool,
}

// ─── Answer (P1) ──────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Default)]
pub struct AnswerRequest {
    pub question: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub top_k: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_tokens: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub provider: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub model: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub temperature: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub no_citations: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub trace_id: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct Citation {
    #[serde(default)]
    pub chunk_id: i64,
    #[serde(default)]
    pub marker_id: String,
    #[serde(default)]
    pub file_path: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub line_range: Option<String>,
    #[serde(default)]
    pub snippet: String,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct AnswerMetadata {
    #[serde(default)]
    pub latency_ms: i64,
    #[serde(default)]
    pub tokens_in: i64,
    #[serde(default)]
    pub tokens_out: i64,
    #[serde(default)]
    pub provider: String,
    #[serde(default)]
    pub model: String,
    #[serde(default)]
    pub retrieval_count: i64,
    #[serde(default)]
    pub fallback_used: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub failed_reason: Option<String>,
    #[serde(default)]
    pub retry_count: i64,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct AnswerSuccess {
    pub answer: String,
    pub citations: Vec<Citation>,
    pub metadata: AnswerMetadata,
    pub trace_id: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct AnswerError {
    pub error: bool,
    pub reason: String,
    pub message: String,
    pub trace_id: String,
}

// ─── Export / Import (A2) ────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Default)]
pub struct ExportRequest {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub project: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub since: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub format: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub exclude_embeddings: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub encrypt: Option<bool>,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct ImportResult {
    #[serde(default)]
    pub op_id: String,
    #[serde(default)]
    pub schema_version_archive: i64,
    #[serde(default)]
    pub schema_version_target: i64,
    #[serde(default)]
    pub migration_applied: Vec<String>,
    #[serde(default)]
    pub chunks_inserted: i64,
    #[serde(default)]
    pub chunks_skipped_dedup: i64,
    #[serde(default)]
    pub kg_entities_inserted: i64,
    #[serde(default)]
    pub kg_entities_merged: i64,
    #[serde(default)]
    pub ops_audit_appended: i64,
    #[serde(default)]
    pub embeddings_skipped: i64,
    #[serde(default)]
    pub duration_ms: i64,
    #[serde(default)]
    pub warnings: Vec<String>,
}

/// Import mode.
#[derive(Debug, Clone, Copy, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum ImportMode {
    Merge,
    Replace,
}

impl Default for ImportMode {
    fn default() -> Self {
        ImportMode::Merge
    }
}

// ─── SSE / Viewer (P5) ───────────────────────────────────────────────────────

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ViewerEvent {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub kind: Option<String>,
    #[serde(flatten)]
    pub payload: Value,
}

// ─── Conflict Detection (L2) ─────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ConflictStatus {
    Unresolved,
    Resolved,
    AutoResolved,
    Dismissed,
}

impl Default for ConflictStatus {
    fn default() -> Self {
        ConflictStatus::Unresolved
    }
}

#[derive(Debug, Clone, Copy, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ConflictType {
    Direct,
    Temporal,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct KgConflict {
    #[serde(default)]
    pub id: i64,
    #[serde(default)]
    pub conflict_type: String,
    #[serde(default)]
    pub source_entity_id: i64,
    #[serde(default)]
    pub source_entity_name: String,
    #[serde(default)]
    pub predicate: String,
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub detected_at: String,
    #[serde(default)]
    pub relation_ids: Vec<i64>,
}

pub type KgConflictDetail = Value;

// ─── Confidence / Marking (L3) ───────────────────────────────────────────────

#[derive(Debug, Clone, Copy, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum MarkKind {
    Canonical,
    Refuted,
    Stale,
}

#[derive(Debug, Clone, Serialize)]
pub struct MarkRequest {
    pub kind: MarkKind,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub notes: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct MarkApplied {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub confidence: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub provenance_kind: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub superseded_by: Option<i64>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct MarkResult {
    pub ok: bool,
    pub chunk_id: i64,
    pub applied: MarkApplied,
    pub audit_id: i64,
}

#[derive(Debug, Clone, Copy, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SupersedeReason {
    AutoSupersedeTemoral,
    ManualResolution,
    StaleLinkReconciliation,
    Dismiss,
}

#[derive(Debug, Clone, Serialize)]
pub struct SupersedeRequest {
    pub by_chunk_id: i64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub notes: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reason: Option<SupersedeReason>,
}

// ─── Hooks (P2) ──────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct HooksConfig {
    #[serde(default)]
    pub enabled: bool,
    #[serde(default)]
    pub allowed_sources: Vec<String>,
    #[serde(default)]
    pub rate_limit_per_min: i64,
    #[serde(default)]
    pub dedup_threshold: f64,
    #[serde(default)]
    pub llm_classify: bool,
    #[serde(default)]
    pub dry_run: bool,
    #[serde(default)]
    pub queue_size: i64,
    #[serde(default)]
    pub min_length: i64,
    #[serde(default)]
    pub pii_policy: String,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct HooksStatus {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub config: Option<HooksConfig>,
    #[serde(rename = "queueDepth", default)]
    pub queue_depth: i64,
    #[serde(rename = "rateLimitTokens", default)]
    pub rate_limit_tokens: i64,
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub struct HookEventMeta {
    #[serde(default)]
    pub event_uuid: String,
    #[serde(default)]
    pub session_id: String,
    #[serde(default)]
    pub project_slug: String,
    #[serde(default)]
    pub kind: String,
    #[serde(default)]
    pub timestamp: String,
    #[serde(default)]
    pub redaction_count: i64,
}

#[derive(Debug, Clone, Serialize)]
pub struct HooksDryrunRequest {
    pub text: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub source: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub role: Option<String>,
}

pub type HooksDryrunResponse = Value;

// ─── Agent profiles ───────────────────────────────────────────────────────────

pub type AgentProfile = Value;
