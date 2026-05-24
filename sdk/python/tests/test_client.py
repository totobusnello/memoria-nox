"""
Tests for NoxMemClient (Python SDK).

Uses respx to mock httpx requests without a real server.
"""

from __future__ import annotations

import json
import pytest
import respx
import httpx

from nox_mem_client import (
    NoxMemClient,
    NoxMemApiError,
    HealthResponse,
    SearchResult,
    AnswerSuccess,
    MarkResult,
    HooksStatus,
    HooksDryrunResponse,
    ImportResult,
    KgConflict,
    Procedure,
    CrystallizeRequest,
    HooksDryrunRequest,
    ExportRequest,
    MarkKind,
    SupersedeReason,
)


BASE_URL = "http://127.0.0.1:18802"


# ─── Fixtures ─────────────────────────────────────────────────────────────────

HEALTH_FIXTURE = {
    "chunks": {"total": 62836, "types": [{"chunk_type": "decision", "c": 1200}]},
    "vectorCoverage": {"embedded": 62836, "total": 62836, "orphans": 0},
    "knowledgeGraph": {"entities": 402, "relations": 544},
    "procedures": 28,
    "dbSizeMB": 487.3,
    "services": {"openclaw-gateway": True, "nox-mem-watch": True},
}

SEARCH_FIXTURE = [
    {
        "chunk_id": 41203,
        "content": "Gemini 2.5 Flash Lite is the default model...",
        "score": 0.913,
        "source_path": "memory/entities/decision/model-selection.md",
        "section": "compiled",
        "chunk_type": "decision",
        "created_at": "2026-04-22T14:30:00Z",
    },
    {
        "chunk_id": 41204,
        "content": "Never hardcode API keys...",
        "score": 0.872,
        "source_path": "memory/entities/lesson/secrets.md",
        "section": "frontmatter",
        "chunk_type": "lesson",
        "created_at": "2026-04-21T10:00:00Z",
    },
]

ANSWER_FIXTURE = {
    "answer": "After upgrading, run /root/reapply-monkey-patch.sh [chunk_1].",
    "citations": [
        {
            "chunk_id": 41203,
            "marker_id": "chunk_1",
            "file_path": "memory/entities/lesson/openclaw-upgrade.md",
            "line_range": "L12-L18",
            "snippet": "After any npm upgrade, immediately reapply the monkey-patch...",
        }
    ],
    "metadata": {
        "latency_ms": 1847,
        "tokens_in": 2341,
        "tokens_out": 198,
        "provider": "gemini",
        "model": "gemini-2.5-flash-lite",
        "retrieval_count": 8,
        "fallback_used": False,
        "retry_count": 0,
    },
    "trace_id": "f3a9c812-1b2e-4d7f-9a03-c1e8b5d60a22",
}

MARK_FIXTURE = {
    "ok": True,
    "chunk_id": 41203,
    "applied": {"confidence": 0.95, "provenance_kind": "user-marked"},
    "audit_id": 1047,
}

HOOKS_STATUS_FIXTURE = {
    "config": {
        "enabled": True,
        "allowed_sources": ["mcp", "api", "cli"],
        "rate_limit_per_min": 60,
        "dedup_threshold": 0.85,
        "pii_policy": "redact",
    },
    "queueDepth": 3,
    "rateLimitTokens": 47,
}


# ─── Health ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_returns_chunk_count():
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/api/health").mock(return_value=httpx.Response(200, json=HEALTH_FIXTURE))
        async with NoxMemClient(base_url=BASE_URL) as client:
            h = await client.health()
    assert h.chunks is not None
    assert h.chunks.total == 62836
    assert h.knowledge_graph is not None
    assert h.knowledge_graph.entities == 402


@pytest.mark.asyncio
async def test_health_vector_coverage():
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/api/health").mock(return_value=httpx.Response(200, json=HEALTH_FIXTURE))
        async with NoxMemClient(base_url=BASE_URL) as client:
            h = await client.health()
    assert h.vector_coverage is not None
    assert h.vector_coverage.embedded == 62836
    assert h.vector_coverage.orphans == 0


# ─── Search ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_returns_results():
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/api/search").mock(return_value=httpx.Response(200, json=SEARCH_FIXTURE))
        async with NoxMemClient(base_url=BASE_URL) as client:
            results = await client.search("gemini quota")
    assert len(results) == 2
    assert results[0].chunk_id == 41203
    assert results[0].score == pytest.approx(0.913)


@pytest.mark.asyncio
async def test_search_section_field():
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/api/search").mock(return_value=httpx.Response(200, json=SEARCH_FIXTURE))
        async with NoxMemClient(base_url=BASE_URL) as client:
            results = await client.search("secrets")
    assert results[1].section is not None
    assert results[1].section.value == "frontmatter"


@pytest.mark.asyncio
async def test_search_post():
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/api/search").mock(return_value=httpx.Response(200, json=SEARCH_FIXTURE))
        from nox_mem_client.models import SearchRequest
        async with NoxMemClient(base_url=BASE_URL) as client:
            results = await client.search_post(SearchRequest(q="monkey patch", limit=5))
    assert len(results) == 2


# ─── Answer ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_answer_returns_citations():
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/api/answer").mock(return_value=httpx.Response(200, json=ANSWER_FIXTURE))
        async with NoxMemClient(base_url=BASE_URL) as client:
            ans = await client.answer("How to reapply monkey-patch?")
    assert "[chunk_1]" in ans.answer
    assert len(ans.citations) == 1
    assert ans.citations[0].chunk_id == 41203
    assert ans.trace_id == "f3a9c812-1b2e-4d7f-9a03-c1e8b5d60a22"


@pytest.mark.asyncio
async def test_answer_metadata_model():
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/api/answer").mock(return_value=httpx.Response(200, json=ANSWER_FIXTURE))
        async with NoxMemClient(base_url=BASE_URL) as client:
            ans = await client.answer("test")
    assert ans.metadata.model == "gemini-2.5-flash-lite"
    assert ans.metadata.latency_ms == 1847


# ─── Mark chunk ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mark_chunk_canonical():
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/api/chunk/41203/mark").mock(return_value=httpx.Response(200, json=MARK_FIXTURE))
        async with NoxMemClient(base_url=BASE_URL) as client:
            result = await client.mark_chunk(41203, MarkKind.canonical, "Verified")
    assert result.ok is True
    assert result.applied.confidence == pytest.approx(0.95)
    assert result.applied.provenance_kind is not None
    assert result.applied.provenance_kind.value == "user-marked"
    assert result.audit_id == 1047


# ─── Supersede chunk ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_supersede_chunk():
    fixture = {
        "ok": True,
        "chunk_id": 40123,
        "applied": {"confidence": 0.1, "provenance_kind": "user-marked", "superseded_by": 41203},
        "audit_id": 1048,
    }
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/api/chunk/40123/supersede").mock(return_value=httpx.Response(200, json=fixture))
        async with NoxMemClient(base_url=BASE_URL) as client:
            result = await client.supersede_chunk(
                40123, 41203, reason=SupersedeReason.manual_resolution
            )
    assert result.applied.superseded_by == 41203
    assert result.applied.confidence == pytest.approx(0.1)


# ─── Hooks ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hook_status():
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/api/hooks/status").mock(return_value=httpx.Response(200, json=HOOKS_STATUS_FIXTURE))
        async with NoxMemClient(base_url=BASE_URL) as client:
            status = await client.hook_status()
    assert status.config is not None
    assert status.config.enabled is True
    assert status.queue_depth == 3
    assert "mcp" in (status.config.allowed_sources or [])


@pytest.mark.asyncio
async def test_hook_recent():
    fixture = {
        "rows": [
            {
                "event_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "session_id": "sess_abc123",
                "project_slug": "memoria-nox",
                "kind": "message_captured",
                "timestamp": "2026-05-18T08:14:22Z",
                "redaction_count": 0,
            }
        ]
    }
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/api/hooks/recent").mock(return_value=httpx.Response(200, json=fixture))
        async with NoxMemClient(base_url=BASE_URL) as client:
            rows = await client.hook_recent(20)
    assert len(rows) == 1
    assert rows[0].kind == "message_captured"


@pytest.mark.asyncio
async def test_hook_dryrun():
    fixture = {
        "result": {"accepted": True, "content": "[PERSON] from Nuvini called", "redacted": True},
        "trace": [{"layer": "pii_redact", "reason": "name_pattern_matched", "redaction_count": 1, "kind": "pii"}],
    }
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/api/hooks/dryrun").mock(return_value=httpx.Response(200, json=fixture))
        async with NoxMemClient(base_url=BASE_URL) as client:
            resp = await client.hook_dryrun(HooksDryrunRequest(text="John Smith from Nuvini"))
    assert resp.trace is not None
    assert len(resp.trace) == 1
    assert resp.trace[0].layer == "pii_redact"
    assert resp.trace[0].redaction_count == 1


# ─── KG ───────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_kg_snapshot():
    fixture = {
        "entities": [{"id": 12, "name": "openclaw-gateway", "type": "service", "mentions": 847}],
        "relations": [{"source": "openclaw-gateway", "relation": "depends_on", "target": "nox-mem-api", "confidence": 0.92}],
    }
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/api/kg").mock(return_value=httpx.Response(200, json=fixture))
        async with NoxMemClient(base_url=BASE_URL) as client:
            kg = await client.kg()
    assert kg.entities is not None
    assert len(kg.entities) == 1
    assert kg.relations is not None
    assert kg.relations[0].confidence == pytest.approx(0.92)


@pytest.mark.asyncio
async def test_kg_path_found():
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/api/kg/path").mock(return_value=httpx.Response(
            200, json={"path": ["nox-mem-api", "vectorize", "gemini-embedding-001"]}
        ))
        async with NoxMemClient(base_url=BASE_URL) as client:
            path = await client.kg_path("nox-mem-api", "gemini-embedding-001")
    assert path == ["nox-mem-api", "vectorize", "gemini-embedding-001"]


@pytest.mark.asyncio
async def test_kg_path_not_found():
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/api/kg/path").mock(return_value=httpx.Response(200, json={"path": None}))
        async with NoxMemClient(base_url=BASE_URL) as client:
            path = await client.kg_path("a", "z")
    assert path is None


# ─── Conflicts ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_conflicts():
    fixture = {
        "conflicts": [
            {
                "id": 1,
                "conflict_type": "direct",
                "source_entity_name": "openclaw-gateway",
                "predicate": "version",
                "status": "unresolved",
                "detected_at": "2026-05-18T10:00:00Z",
            }
        ],
        "total": 1,
    }
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/api/kg/conflicts").mock(return_value=httpx.Response(200, json=fixture))
        async with NoxMemClient(base_url=BASE_URL) as client:
            from nox_mem_client.models import ConflictStatus
            result = await client.list_conflicts(status=ConflictStatus.unresolved)
    assert result["total"] == 1
    conflicts = result["conflicts"]
    assert conflicts[0].conflict_type is not None
    assert conflicts[0].conflict_type.value == "direct"


# ─── Procedures ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_procedures():
    fixture = {
        "procedures": [
            {
                "id": 88,
                "title": "Reapply monkey-patch",
                "steps": ["SSH", "Run script", "Verify"],
                "agent": "forge",
            }
        ]
    }
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/api/procedures").mock(return_value=httpx.Response(200, json=fixture))
        async with NoxMemClient(base_url=BASE_URL) as client:
            procs = await client.procedures()
    assert len(procs) == 1
    assert procs[0].id == 88
    assert procs[0].agent == "forge"


@pytest.mark.asyncio
async def test_crystallize():
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/api/crystallize").mock(return_value=httpx.Response(200, json={"id": 88, "ok": True}))
        async with NoxMemClient(base_url=BASE_URL) as client:
            result = await client.crystallize(
                CrystallizeRequest(title="Test proc", steps=["Step 1", "Step 2"])
            )
    assert result["id"] == 88
    assert result["ok"] is True


# ─── Error handling ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_raises_nox_mem_api_error_on_500():
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/api/health").mock(return_value=httpx.Response(
            500, json={"error": "SQLITE_ERROR: no such table"}
        ))
        async with NoxMemClient(base_url=BASE_URL) as client:
            with pytest.raises(NoxMemApiError) as exc_info:
                await client.health()
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_is_feature_disabled():
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/api/answer").mock(return_value=httpx.Response(
            503, json={"error": "feature disabled", "env_var": "NOX_ANSWER_ENABLED"}
        ))
        async with NoxMemClient(base_url=BASE_URL) as client:
            with pytest.raises(NoxMemApiError) as exc_info:
                await client.answer("test")
    assert exc_info.value.is_feature_disabled is True


@pytest.mark.asyncio
async def test_is_unauthorized():
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/api/reflect").mock(return_value=httpx.Response(
            401, json={"error": "unauthorized"}
        ))
        async with NoxMemClient(base_url=BASE_URL) as client:
            with pytest.raises(NoxMemApiError) as exc_info:
                await client.reflect("test")
    assert exc_info.value.is_unauthorized is True


# ─── Auth header ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auth_header_sent():
    with respx.mock(base_url=BASE_URL) as mock:
        def check_auth(request: httpx.Request) -> httpx.Response:
            assert request.headers.get("authorization") == "Bearer test-token"
            return httpx.Response(200, json=HEALTH_FIXTURE)
        mock.get("/api/health").mock(side_effect=check_auth)
        async with NoxMemClient(base_url=BASE_URL, auth_token="test-token") as client:
            await client.health()


# ─── Import result shape ──────────────────────────────────────────────────────

def test_import_result_model():
    data = {
        "op_id": "import-2026-05-18-001",
        "schema_version_archive": 18,
        "schema_version_target": 19,
        "chunks_inserted": 12455,
        "chunks_skipped_dedup": 873,
        "duration_ms": 47832,
        "warnings": [],
    }
    result = ImportResult.model_validate(data)
    assert result.chunks_inserted == 12455
    assert result.warnings == []


# ─── SSE stream ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stream_events_parses_sse():
    event1 = {"kind": "chunk.created", "ts": "2026-05-18T10:00:00Z", "payload": {"chunk_id": 41203}}
    event2 = {"kind": "search.executed", "ts": "2026-05-18T10:00:01Z", "payload": {"query": "test"}}

    sse_body = (
        f"id: 1\nevent: chunk.created\ndata: {json.dumps(event1)}\n\n"
        f"id: 2\nevent: search.executed\ndata: {json.dumps(event2)}\n\n"
    )

    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/api/events/stream").mock(return_value=httpx.Response(
            200,
            content=sse_body.encode(),
            headers={"Content-Type": "text/event-stream"},
        ))
        async with NoxMemClient(base_url=BASE_URL) as client:
            events = []
            async for ev in client.stream_events():
                events.append(ev)

    assert len(events) >= 1
    assert events[0].kind.value == "chunk.created"
    assert events[0].payload.get("chunk_id") == 41203
