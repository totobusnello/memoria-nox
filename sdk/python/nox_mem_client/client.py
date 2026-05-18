"""
NoxMemClient — async Python client for the memoria-nox HTTP API.

Requires httpx >= 0.27.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from .models import (
    AgentProfile,
    AnswerRequest,
    AnswerSuccess,
    ConflictStatus,
    CrystallizeRequest,
    CrystallizeValidateRequest,
    CrossKgResponse,
    ErrorResponse,
    ExportRequest,
    FeatureDisabledError,
    HealthResponse,
    HookEventMeta,
    HooksDryrunRequest,
    HooksDryrunResponse,
    HooksStatus,
    ImportResult,
    KgConflict,
    KgConflictDetail,
    KgResponse,
    MarkKind,
    MarkRequest,
    MarkResult,
    Procedure,
    ReflectResult,
    SearchRequest,
    SearchResult,
    SseEventKind,
    SupersedeReason,
    SupersedeRequest,
    ViewerEvent,
)


class NoxMemApiError(Exception):
    """Raised when the servidor returns a non-2xx response."""

    def __init__(self, status_code: int, body: dict[str, Any], url: str) -> None:
        self.status_code = status_code
        self.body = body
        self.url = url
        msg = body.get("error", str(body))
        super().__init__(f"NoxMem API error {status_code} on {url}: {msg}")

    @property
    def is_feature_disabled(self) -> bool:
        return (
            self.body.get("error") == "feature disabled"
            and "env_var" in self.body
        )

    @property
    def is_unauthorized(self) -> bool:
        return self.status_code == 401


class NoxMemClient:
    """
    Async Python client for the memoria-nox HTTP API.

    Supports all endpoints from openapi.yaml 1.0.0-wave-d.

    Use as an async context manager or manage the lifecycle manually via
    ``aclose()``.

    Example::

        async with NoxMemClient() as client:
            results = await client.search("Gemini quota exceeded")
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:18802",
        auth_token: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        headers: dict[str, str] = {"Accept": "application/json"}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
        )
        self._auth_token = auth_token

    async def __aenter__(self) -> "NoxMemClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        content: bytes | None = None,
        content_type: str | None = None,
        accept: str = "application/json",
    ) -> Any:
        headers: dict[str, str] = {"Accept": accept}
        if content_type:
            headers["Content-Type"] = content_type
        elif json_body is not None:
            headers["Content-Type"] = "application/json"

        # Strip None params
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}

        res = await self._client.request(
            method,
            path,
            params=clean_params or None,
            json=json_body,
            content=content,
            headers=headers,
        )

        if not res.is_success:
            try:
                err_body = res.json()
            except Exception:
                err_body = {"error": res.text}
            raise NoxMemApiError(res.status_code, err_body, str(res.url))

        return res.json()

    # ── Core ──────────────────────────────────────────────────────────────────

    async def health(self) -> HealthResponse:
        """GET /api/health — system health, chunk counts, vector coverage."""
        data = await self._request("GET", "/api/health")
        return HealthResponse.model_validate(data)

    async def agents(self) -> list[AgentProfile]:
        """GET /api/agents — agent profiles from cross-agent KG."""
        data = await self._request("GET", "/api/agents")
        return list(data)  # type: ignore[no-any-return]

    async def reflect(self, q: str, *, nocache: bool = False) -> ReflectResult:
        """GET /api/reflect — synthesize a reflection over memory."""
        params: dict[str, Any] = {"q": q}
        if nocache:
            params["nocache"] = "1"
        data = await self._request("GET", "/api/reflect", params=params)
        return dict(data)  # type: ignore[no-any-return]

    async def procedures(self) -> list[Procedure]:
        """GET /api/procedures — list crystallized procedures."""
        data = await self._request("GET", "/api/procedures")
        return [Procedure.model_validate(p) for p in data.get("procedures", [])]

    async def crystallize(self, req: CrystallizeRequest) -> dict[str, Any]:
        """POST /api/crystallize — store a new procedure. Returns {id, ok}."""
        return await self._request(  # type: ignore[no-any-return]
            "POST", "/api/crystallize", json_body=req.model_dump(exclude_none=True)
        )

    async def crystallize_validate(
        self,
        id: int,
        req: CrystallizeValidateRequest | None = None,
    ) -> dict[str, Any]:
        """POST /api/crystallize/validate — record execution outcome."""
        body = req.model_dump(exclude_none=True) if req else None
        return await self._request(  # type: ignore[no-any-return]
            "POST", "/api/crystallize/validate",
            params={"id": id},
            json_body=body,
        )

    # ── Search ────────────────────────────────────────────────────────────────

    async def search(
        self,
        q: str,
        *,
        limit: int | None = None,
        as_of: str | None = None,
        changed_since: str | None = None,
    ) -> list[SearchResult]:
        """GET /api/search — hybrid search (FTS5 + Gemini semantic + RRF)."""
        data = await self._request(
            "GET", "/api/search",
            params={"q": q, "limit": limit, "as_of": as_of, "changed_since": changed_since},
        )
        return [SearchResult.model_validate(r) for r in data]

    async def search_post(self, req: SearchRequest) -> list[SearchResult]:
        """POST /api/search — hybrid search via POST body."""
        data = await self._request(
            "POST", "/api/search",
            json_body=req.model_dump(exclude_none=True),
        )
        return [SearchResult.model_validate(r) for r in data]

    # ── Knowledge Graph ───────────────────────────────────────────────────────

    async def kg(self) -> KgResponse:
        """GET /api/kg — KG snapshot: top entities and relations."""
        data = await self._request("GET", "/api/kg")
        return KgResponse.model_validate(data)

    async def kg_path(self, from_entity: str, to_entity: str) -> list[str] | None:
        """GET /api/kg/path — shortest path between two entities."""
        data = await self._request(
            "GET", "/api/kg/path",
            params={"from": from_entity, "to": to_entity},
        )
        return data.get("path")  # type: ignore[no-any-return]

    async def cross_kg(self) -> CrossKgResponse:
        """GET /api/cross-kg — merged cross-agent KG."""
        return await self._request("GET", "/api/cross-kg")  # type: ignore[no-any-return]

    # ── Answer (P1) ───────────────────────────────────────────────────────────

    async def answer(
        self,
        question: str,
        *,
        top_k: int | None = None,
        max_tokens: int | None = None,
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        no_citations: bool | None = None,
        trace_id: str | None = None,
    ) -> AnswerSuccess:
        """POST /api/answer — RAG-style question answering with citations.

        Requires ``NOX_ANSWER_ENABLED=1`` on the server.
        """
        req = AnswerRequest(
            question=question,
            top_k=top_k,
            max_tokens=max_tokens,
            provider=provider,
            model=model,
            temperature=temperature,
            no_citations=no_citations,
            trace_id=trace_id,
        )
        data = await self._request(
            "POST", "/api/answer",
            json_body=req.model_dump(exclude_none=True),
        )
        return AnswerSuccess.model_validate(data)

    # ── Export / Import (A2) ──────────────────────────────────────────────────

    async def export(self, opts: ExportRequest | None = None) -> bytes:
        """POST /api/export — export memory to a gzip tar archive.

        Requires ``NOX_ARCHIVE_ENABLED=1``.
        Returns raw bytes of the archive. Pipe directly to a file for
        large corpora to avoid buffering the full response in memory.
        """
        body = opts.model_dump(exclude_none=True) if opts else {}
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/gzip, application/octet-stream",
        }
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"

        res = await self._client.post(
            "/api/export",
            json=body,
            headers=headers,
        )
        if not res.is_success:
            try:
                err_body = res.json()
            except Exception:
                err_body = {"error": res.text}
            raise NoxMemApiError(res.status_code, err_body, str(res.url))
        return res.content

    async def import_archive(
        self,
        archive: bytes,
        *,
        mode: str = "merge",
        dry_run: bool = False,
        force: bool = False,
        skip_embeddings: bool = False,
    ) -> ImportResult:
        """POST /api/import — import a portable archive into the database.

        Requires ``NOX_ARCHIVE_ENABLED=1``.
        """
        params: dict[str, Any] = {
            "mode": mode,
            "dry_run": dry_run,
            "force": force,
            "skip_embeddings": skip_embeddings,
        }
        headers: dict[str, str] = {
            "Content-Type": "application/gzip",
            "Accept": "application/json",
        }
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"

        res = await self._client.post(
            "/api/import",
            params={k: str(v).lower() if isinstance(v, bool) else v for k, v in params.items()},
            content=archive,
            headers=headers,
        )
        if not res.is_success:
            try:
                err_body = res.json()
            except Exception:
                err_body = {"error": res.text}
            raise NoxMemApiError(res.status_code, err_body, str(res.url))
        return ImportResult.model_validate(res.json())

    # ── Viewer / SSE (P5) ─────────────────────────────────────────────────────

    async def stream_events(self) -> AsyncIterator[ViewerEvent]:
        """GET /api/events/stream (SSE) — real-time event bus stream.

        Requires ``NOX_VIEWER_ENABLED=1``.

        Yields :class:`ViewerEvent` objects until the connection closes.

        Example::

            async for event in client.stream_events():
                print(event.kind, event.ts, event.payload)
        """
        headers: dict[str, str] = {"Accept": "text/event-stream"}
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"

        async with self._client.stream("GET", "/api/events/stream", headers=headers) as res:
            if not res.is_success:
                body_text = await res.aread()
                try:
                    err_body = json.loads(body_text)
                except Exception:
                    err_body = {"error": body_text.decode()}
                raise NoxMemApiError(res.status_code, err_body, str(res.url))

            current_data = ""
            current_event = ""

            async for line in res.aiter_lines():
                if line.startswith("data:"):
                    current_data += line[5:].strip()
                elif line.startswith("event:"):
                    current_event = line[6:].strip()
                elif line == "":
                    # End of event block
                    if current_data:
                        try:
                            parsed = json.loads(current_data)
                            if current_event:
                                parsed["kind"] = current_event
                            yield ViewerEvent.model_validate(parsed)
                        except Exception:
                            pass  # skip malformed events
                    current_data = ""
                    current_event = ""

    # ── Conflict Detection (L2) ───────────────────────────────────────────────

    async def list_conflicts(
        self,
        *,
        status: ConflictStatus | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, Any]:
        """GET /api/kg/conflicts — list KG conflicts.

        Requires ``NOX_KG_CONFLICTS_ENABLED=1``.

        Returns ``{"conflicts": [...], "total": N}``.
        """
        data = await self._request(
            "GET", "/api/kg/conflicts",
            params={"status": status.value if status else None, "limit": limit, "offset": offset},
        )
        return {  # type: ignore[return-value]
            "conflicts": [KgConflict.model_validate(c) for c in data.get("conflicts", [])],
            "total": data.get("total", 0),
        }

    async def scan_conflicts(self) -> dict[str, Any]:
        """POST /api/kg/conflicts/scan — trigger a conflict detection scan.

        Requires ``NOX_KG_CONFLICTS_ENABLED=1``.
        """
        return await self._request("POST", "/api/kg/conflicts/scan")  # type: ignore[no-any-return]

    async def get_conflict(self, id: int) -> KgConflictDetail:
        """GET /api/kg/conflicts/{id} — get conflict detail with evidence.

        Requires ``NOX_KG_CONFLICTS_ENABLED=1``.
        """
        data = await self._request("GET", f"/api/kg/conflicts/{id}")
        return KgConflictDetail.model_validate(data)

    async def resolve_conflict(
        self, id: int, keep_relation_id: int, notes: str | None = None
    ) -> dict[str, Any]:
        """POST /api/kg/conflicts/{id}/resolve — resolve by keeping one relation.

        Requires ``NOX_KG_CONFLICTS_ENABLED=1``.
        """
        body: dict[str, Any] = {"keep_relation_id": keep_relation_id}
        if notes:
            body["notes"] = notes
        return await self._request("POST", f"/api/kg/conflicts/{id}/resolve", json_body=body)  # type: ignore[no-any-return]

    async def dismiss_conflict(
        self, id: int, notes: str | None = None
    ) -> dict[str, Any]:
        """POST /api/kg/conflicts/{id}/dismiss — dismiss a conflict.

        Requires ``NOX_KG_CONFLICTS_ENABLED=1``.
        """
        body: dict[str, Any] = {}
        if notes:
            body["notes"] = notes
        return await self._request("POST", f"/api/kg/conflicts/{id}/dismiss", json_body=body or None)  # type: ignore[no-any-return]

    # ── Confidence / Marking (L3) ─────────────────────────────────────────────

    async def mark_chunk(
        self, id: int, kind: MarkKind, notes: str | None = None
    ) -> MarkResult:
        """POST /api/chunk/{id}/mark — mark a chunk as canonical, refuted, or stale."""
        req = MarkRequest(kind=kind, notes=notes)
        data = await self._request(
            "POST", f"/api/chunk/{id}/mark",
            json_body=req.model_dump(exclude_none=True),
        )
        return MarkResult.model_validate(data)

    async def supersede_chunk(
        self,
        id: int,
        by_chunk_id: int,
        *,
        notes: str | None = None,
        reason: SupersedeReason | None = None,
    ) -> MarkResult:
        """POST /api/chunk/{id}/supersede — mark a chunk as superseded."""
        req = SupersedeRequest(by_chunk_id=by_chunk_id, notes=notes, reason=reason)
        data = await self._request(
            "POST", f"/api/chunk/{id}/supersede",
            json_body=req.model_dump(exclude_none=True),
        )
        return MarkResult.model_validate(data)

    # ── Hooks (P2) ────────────────────────────────────────────────────────────

    async def hook_status(self) -> HooksStatus:
        """GET /api/hooks/status — hooks pipeline config and queue depth.

        Requires ``NOX_HOOKS_ENABLED=1``.
        """
        data = await self._request("GET", "/api/hooks/status")
        return HooksStatus.model_validate(data)

    async def hook_recent(self, limit: int | None = None) -> list[HookEventMeta]:
        """GET /api/hooks/recent — recent event metadata (no payloads).

        Requires ``NOX_HOOKS_ENABLED=1``.
        """
        data = await self._request(
            "GET", "/api/hooks/recent",
            params={"limit": limit} if limit is not None else None,
        )
        return [HookEventMeta.model_validate(r) for r in data.get("rows", [])]

    async def hook_dryrun(self, req: HooksDryrunRequest) -> HooksDryrunResponse:
        """POST /api/hooks/dryrun — dry-run text through hooks pipeline.

        Requires ``NOX_HOOKS_ENABLED=1``.
        """
        data = await self._request(
            "POST", "/api/hooks/dryrun",
            json_body=req.model_dump(exclude_none=True),
        )
        return HooksDryrunResponse.model_validate(data)
