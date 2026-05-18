"""
nox_mem_client — Async Python client for the memoria-nox HTTP API.

Generated from docs/openapi/openapi.yaml (version 1.0.0-wave-d).
Uses httpx for async HTTP and Pydantic for type-safe models.

Usage::

    from nox_mem_client import NoxMemClient

    async with NoxMemClient() as client:
        results = await client.search("Gemini quota exceeded")
        for r in results:
            print(r.content, r.score)
"""

from .client import NoxMemClient, NoxMemApiError
from .models import (
    HealthResponse,
    SearchResult,
    SearchRequest,
    AgentProfile,
    KgResponse,
    CrossKgResponse,
    ReflectResult,
    Procedure,
    CrystallizeRequest,
    CrystallizeValidateRequest,
    AnswerRequest,
    AnswerSuccess,
    AnswerError,
    Citation,
    AnswerMetadata,
    ExportRequest,
    ImportResult,
    ImportError,
    ViewerEvent,
    SseEventKind,
    KgConflict,
    KgConflictDetail,
    MarkKind,
    MarkRequest,
    MarkResult,
    MarkError,
    SupersedeRequest,
    SupersedeReason,
    HooksStatus,
    HookEventMeta,
    HooksDryrunRequest,
    HooksDryrunResponse,
    ErrorResponse,
    FeatureDisabledError,
)

__all__ = [
    "NoxMemClient",
    "NoxMemApiError",
    "HealthResponse",
    "SearchResult",
    "SearchRequest",
    "AgentProfile",
    "KgResponse",
    "CrossKgResponse",
    "ReflectResult",
    "Procedure",
    "CrystallizeRequest",
    "CrystallizeValidateRequest",
    "AnswerRequest",
    "AnswerSuccess",
    "AnswerError",
    "Citation",
    "AnswerMetadata",
    "ExportRequest",
    "ImportResult",
    "ImportError",
    "ViewerEvent",
    "SseEventKind",
    "KgConflict",
    "KgConflictDetail",
    "MarkKind",
    "MarkRequest",
    "MarkResult",
    "MarkError",
    "SupersedeRequest",
    "SupersedeReason",
    "HooksStatus",
    "HookEventMeta",
    "HooksDryrunRequest",
    "HooksDryrunResponse",
    "ErrorResponse",
    "FeatureDisabledError",
]
