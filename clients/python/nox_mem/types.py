"""Type definitions for the nox-mem Python client."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class HealthSnapshot:
    """Snapshot of nox-mem API health state."""

    chunks_total: int
    vec_coverage: float
    salience_mode: str
    kg_entities: int
    kg_relations: int
    uptime: str
    indicators: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HealthSnapshot":
        return cls(
            chunks_total=data.get("chunksTotal", data.get("chunks_total", 0)),
            vec_coverage=data.get("vectorCoverage", data.get("vec_coverage", 0.0)),
            salience_mode=data.get("salienceMode", data.get("salience_mode", "unknown")),
            kg_entities=data.get("kgEntities", data.get("kg_entities", 0)),
            kg_relations=data.get("kgRelations", data.get("kg_relations", 0)),
            uptime=data.get("uptime", ""),
            indicators=data.get("indicators", {}),
        )


@dataclass
class SearchResult:
    """A single result from a hybrid memory search."""

    id: str
    score: float
    source_file: str
    snippet: str
    section: Optional[str] = None
    pain: Optional[float] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SearchResult":
        return cls(
            id=str(data.get("id", "")),
            score=float(data.get("score", 0.0)),
            source_file=data.get("sourceFile", data.get("source_file", "")),
            snippet=data.get("snippet", data.get("content", "")),
            section=data.get("section"),
            pain=data.get("pain"),
        )


@dataclass
class AnswerResponse:
    """Response from the /api/answer endpoint."""

    answer: str
    citations: list[SearchResult]
    session_id: Optional[str]
    latency_ms: Optional[int]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnswerResponse":
        raw_citations = data.get("citations", data.get("sources", []))
        return cls(
            answer=data.get("answer", ""),
            citations=[SearchResult.from_dict(c) for c in raw_citations],
            session_id=data.get("sessionId", data.get("session_id")),
            latency_ms=data.get("latencyMs", data.get("latency_ms")),
        )


@dataclass
class KgEntity:
    """A knowledge graph entity."""

    id: int
    name: str
    type: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KgEntity":
        return cls(
            id=int(data.get("id", 0)),
            name=data.get("name", ""),
            type=data.get("type", ""),
        )


@dataclass
class KgRelation:
    """A knowledge graph relation between two entities."""

    source: str
    target: str
    kind: str
    weight: float = 1.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KgRelation":
        return cls(
            source=data.get("source", ""),
            target=data.get("target", ""),
            kind=data.get("kind", data.get("relation", "")),
            weight=float(data.get("weight", 1.0)),
        )
