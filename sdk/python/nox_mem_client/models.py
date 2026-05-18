"""
Pydantic models derived from docs/openapi/openapi.yaml (1.0.0-wave-d).

All models use `model_config = ConfigDict(extra="allow")` to future-proof
against new fields added server-side without breaking existing clients.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ─── Shared config ────────────────────────────────────────────────────────────

class _Base(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


# ─── Primitives ───────────────────────────────────────────────────────────────

class ErrorResponse(_Base):
    error: str
    code: str | None = None
    details: dict[str, Any] | None = None


class FeatureDisabledError(_Base):
    error: Literal["feature disabled"]
    env_var: str


# ─── Health ───────────────────────────────────────────────────────────────────

class ChunkTypeStat(_Base):
    chunk_type: str | None = None
    c: int | None = None


class ChunkStats(_Base):
    total: int | None = None
    types: list[ChunkTypeStat] | None = None


class ConsolidationStats(_Base):
    done: int | None = None
    failed: int | None = None
    last: str | None = None


class VectorCoverage(_Base):
    embedded: int | None = None
    total: int | None = None
    orphans: int | None = None


class KgStats(_Base):
    entities: int | None = None
    relations: int | None = None


class ReflectCacheTopQuery(_Base):
    query: str | None = None
    hits: int | None = None
    last_hit_at: str | None = None


class ReflectCacheStats(_Base):
    entries: int | None = None
    total_hits: int | None = None
    top_queries: list[ReflectCacheTopQuery] | None = None


class SearchTelemetry(_Base):
    count_24h: int | None = None
    avg_results: float | None = None
    semantic_ratio: float | None = None
    p95_latency_ms: float | None = None
    expansion_enabled: bool | None = None
    skip_reasons: dict[str, int] | None = None


class RankingMode(str, Enum):
    disabled = "disabled"
    shadow = "shadow"
    active = "active"


class ProvenanceStats(_Base):
    observed: int | None = None
    declared: int | None = None
    inferred: int | None = None
    derived: int | None = None
    user_marked: int | None = Field(None, alias="user-marked")
    null: int | None = None


class ConfidenceDistribution(_Base):
    mean: float | None = None
    p25: float | None = None
    p50: float | None = None
    p75: float | None = None
    p95: float | None = None
    stddev: float | None = None


class ConfidenceHealthSlice(_Base):
    ranking_mode: RankingMode | None = None
    provenance: ProvenanceStats | None = None
    confidence_distribution: ConfidenceDistribution | None = None
    superseded_count: int | None = None


class HealthResponse(_Base):
    chunks: ChunkStats | None = None
    consolidation: ConsolidationStats | None = None
    vector_coverage: VectorCoverage | None = Field(None, alias="vectorCoverage")
    knowledge_graph: KgStats | None = Field(None, alias="knowledgeGraph")
    reflect_cache: ReflectCacheStats | None = Field(None, alias="reflectCache")
    procedures: int | None = None
    search_telemetry: SearchTelemetry | None = Field(None, alias="searchTelemetry")
    services: dict[str, bool] | None = None
    db_size_mb: float | None = Field(None, alias="dbSizeMB")
    confidence: ConfidenceHealthSlice | None = None


# ─── Search ───────────────────────────────────────────────────────────────────

class SearchRequest(_Base):
    q: str
    limit: int | None = Field(None, ge=1, le=100)
    as_of: str | None = None
    changed_since: str | None = None


class SectionKind(str, Enum):
    compiled = "compiled"
    frontmatter = "frontmatter"
    timeline = "timeline"


class SearchResult(_Base):
    chunk_id: int | None = None
    content: str | None = None
    score: float | None = None
    source_path: str | None = None
    section: SectionKind | None = None
    chunk_type: str | None = None
    created_at: str | None = None


# ─── Agents ───────────────────────────────────────────────────────────────────

AgentProfile = dict[str, Any]


# ─── KG ───────────────────────────────────────────────────────────────────────

class KgEntity(_Base):
    id: int | None = None
    name: str | None = None
    type: str | None = None
    mentions: int | None = None


class KgRelation(_Base):
    source: str | None = None
    relation: str | None = None
    target: str | None = None
    confidence: float | None = None


class KgResponse(_Base):
    entities: list[KgEntity] | None = None
    relations: list[KgRelation] | None = None


CrossKgResponse = dict[str, Any]

# ─── Reflect / Procedures ─────────────────────────────────────────────────────

ReflectResult = dict[str, Any]


class Procedure(_Base):
    id: int | None = None
    title: str | None = None
    steps: list[str] | None = None
    agent: str | None = None
    tags: list[str] | None = None
    created_at: str | None = None


class CrystallizeRequest(_Base):
    title: str
    steps: list[str] = Field(..., min_length=1)
    agent: str | None = None
    tags: list[str] | None = None
    preconditions: list[str] | None = None


class CrystallizeValidateRequest(_Base):
    outcome: Literal["success", "failure", "partial"] | None = None
    agent: str | None = None
    notes: str | None = None


# ─── Answer (P1) ──────────────────────────────────────────────────────────────

class AnswerRequest(_Base):
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int | None = Field(None, ge=1, le=20)
    max_tokens: int | None = Field(None, ge=64, le=8192)
    provider: str | None = None
    model: str | None = None
    temperature: float | None = Field(None, ge=0, le=1)
    no_citations: bool | None = None
    trace_id: str | None = Field(None, max_length=64)


class Citation(_Base):
    chunk_id: int | None = None
    marker_id: str | None = None
    file_path: str | None = None
    line_range: str | None = None
    snippet: str | None = Field(None, max_length=200)


class AnswerFailedReason(str, Enum):
    hallucinated_citation = "hallucinated_citation"
    hallucination_after_retry = "hallucination_after_retry"
    retrieval_empty = "retrieval_empty"
    llm_error = "llm_error"
    llm_timeout = "llm_timeout"
    invalid_input = "invalid_input"


class AnswerMetadata(_Base):
    latency_ms: int | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    provider: str | None = None
    model: str | None = None
    retrieval_count: int | None = None
    fallback_used: bool | None = None
    failed_reason: AnswerFailedReason | None = None
    retry_count: int | None = None


class AnswerSuccess(_Base):
    answer: str
    citations: list[Citation]
    metadata: AnswerMetadata
    trace_id: str


class AnswerErrorReason(str, Enum):
    invalid_body = "invalid_body"
    unauthorized = "unauthorized"
    retrieval_empty = "retrieval_empty"
    hallucinated_citation = "hallucinated_citation"
    hallucination_after_retry = "hallucination_after_retry"
    llm_error = "llm_error"
    llm_timeout = "llm_timeout"
    internal_error = "internal_error"


class AnswerError(_Base):
    error: Literal[True]
    reason: AnswerErrorReason
    message: str
    trace_id: str


# ─── Export / Import (A2) ─────────────────────────────────────────────────────

class ExportFormat(str, Enum):
    tar = "tar"
    zip = "zip"
    sqlite_dump = "sqlite-dump"


class ExportRequest(_Base):
    project: str | None = None
    since: str | None = None
    until: str | None = None
    format: ExportFormat | None = None
    exclude_embeddings: bool | None = None
    exclude_kg: bool | None = None
    exclude_audit: bool | None = None
    encrypt: bool | None = None
    compression_level: int | None = Field(None, ge=0, le=9)


class ImportResult(_Base):
    op_id: str | None = None
    schema_version_archive: int | None = None
    schema_version_target: int | None = None
    migration_applied: list[str] | None = None
    chunks_inserted: int | None = None
    chunks_skipped_dedup: int | None = None
    kg_entities_inserted: int | None = None
    kg_entities_merged: int | None = None
    ops_audit_appended: int | None = None
    embeddings_skipped: int | None = None
    duration_ms: int | None = None
    warnings: list[str] | None = None


class ImportErrorCode(str, Enum):
    schema_downgrade = "schema_downgrade"
    bad_passphrase = "bad_passphrase"
    tampered_archive = "tampered_archive"
    missing_aad = "missing_aad"
    manifest_error = "manifest_error"
    archive_format_error = "archive_format_error"


class ImportError(_Base):
    error_code: ImportErrorCode
    message: str
    archive_schema: int | None = None
    target_schema: int | None = None


# ─── Viewer / SSE (P5) ────────────────────────────────────────────────────────

class SseEventKind(str, Enum):
    chunk_created = "chunk.created"
    chunk_deleted = "chunk.deleted"
    kg_entity_created = "kg.entity.created"
    kg_relation_created = "kg.relation.created"
    search_executed = "search.executed"
    provider_call = "provider.call"
    op_audit_started = "op_audit.started"
    op_audit_completed = "op_audit.completed"
    health_warning = "health.warning"


class ViewerEvent(_Base):
    kind: SseEventKind
    ts: str
    payload: dict[str, Any] = Field(default_factory=dict)


# ─── Conflict Detection (L2) ──────────────────────────────────────────────────

class ConflictType(str, Enum):
    direct = "direct"
    temporal = "temporal"
    logical = "logical"
    transitive = "transitive"


class ConflictStatus(str, Enum):
    unresolved = "unresolved"
    resolved = "resolved"
    auto_resolved = "auto_resolved"
    dismissed = "dismissed"


class KgConflict(_Base):
    id: int | None = None
    conflict_type: ConflictType | None = None
    source_entity_id: int | None = None
    source_entity_name: str | None = None
    predicate: str | None = None
    status: ConflictStatus | None = None
    detected_at: str | None = None
    relation_ids: list[int] | None = None


class EvidenceSnippet(_Base):
    chunk_id: int | None = None
    snippet: str | None = None


class KgConflictDetail(KgConflict):
    entities: list[dict[str, Any]] | None = None
    relations: list[dict[str, Any]] | None = None
    evidence_snippets: list[EvidenceSnippet] | None = None


# ─── Confidence (L3) ──────────────────────────────────────────────────────────

class ProvenanceKind(str, Enum):
    observed = "observed"
    declared = "declared"
    inferred = "inferred"
    derived = "derived"
    user_marked = "user-marked"


class MarkKind(str, Enum):
    canonical = "canonical"
    refuted = "refuted"
    stale = "stale"


class SupersedeReason(str, Enum):
    auto_supersede_temporal = "auto_supersede_temporal"
    manual_resolution = "manual_resolution"
    stale_link_reconciliation = "stale_link_reconciliation"
    dismiss = "dismiss"


class MarkRequest(_Base):
    kind: MarkKind
    notes: str | None = None


class SupersedeRequest(_Base):
    by_chunk_id: int = Field(..., ge=1)
    notes: str | None = None
    reason: SupersedeReason | None = None


class MarkApplied(_Base):
    confidence: float | None = Field(None, ge=0, le=1)
    provenance_kind: ProvenanceKind | None = None
    superseded_by: int | None = None


class MarkResult(_Base):
    ok: Literal[True]
    chunk_id: int
    applied: MarkApplied
    audit_id: int


class MarkErrorCode(str, Enum):
    bad_id = "bad_id"
    bad_body = "bad_body"
    bad_kind = "bad_kind"
    bad_by_id = "bad_by_id"
    not_found = "not_found"
    runtime = "runtime"


class MarkError(_Base):
    ok: Literal[False]
    error: str
    code: MarkErrorCode


# ─── Hooks (P2) ───────────────────────────────────────────────────────────────

class HooksConfig(_Base):
    enabled: bool | None = None
    allowed_sources: list[str] | None = None
    rate_limit_per_min: int | None = None
    dedup_threshold: float | None = None
    llm_classify: bool | None = None
    dry_run: bool | None = None
    queue_size: int | None = None
    min_length: int | None = None
    pii_policy: str | None = None


class HooksStatus(_Base):
    config: HooksConfig | None = None
    queue_depth: int | None = Field(None, alias="queueDepth")
    rate_limit_tokens: int | None = Field(None, alias="rateLimitTokens")


class HookEventMeta(_Base):
    event_uuid: str | None = None
    session_id: str | None = None
    project_slug: str | None = None
    kind: str | None = None
    timestamp: str | None = None
    redaction_count: int | None = None


class HooksDryrunRequest(_Base):
    text: str = Field(..., min_length=1)
    source: str | None = None
    role: str | None = None


class DryrunTraceLayer(_Base):
    layer: str | None = None
    reason: str | None = None
    redaction_count: int | None = None
    kind: str | None = None


class HooksDryrunResponse(_Base):
    result: dict[str, Any] | None = None
    trace: list[DryrunTraceLayer] | None = None
