"""nox-mem Python client implementation."""
from __future__ import annotations

import time
from typing import Any, Optional

import requests
from requests import Session

from .types import AnswerResponse, HealthSnapshot, SearchResult

_DEFAULT_BASE_URL = "http://187.77.234.79:18802"
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 0.5  # seconds


class NoxMemError(Exception):
    """Raised when the nox-mem API returns an error response."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")


class NoxMemClient:
    """
    Client for the nox-mem hybrid memory API.

    Usage::

        client = NoxMemClient()
        results = client.search("pain-weighted retrieval")
        print(results[0].snippet)

    Context manager::

        with NoxMemClient() as c:
            snap = c.health()
            print(snap.chunks_total)
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: int = 30,
        session: Optional[Session] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = session or Session()
        self._owns_session = session is None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "NoxMemClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def close(self) -> None:
        """Release the underlying HTTP session (no-op if externally provided)."""
        if self._owns_session:
            self._session.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
    ) -> Any:
        url = self._url(path)
        last_exc: Optional[Exception] = None

        for attempt in range(_MAX_RETRIES):
            try:
                resp = self._session.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    timeout=self.timeout,
                )
                if resp.status_code >= 500:
                    if attempt < _MAX_RETRIES - 1:
                        time.sleep(_RETRY_BACKOFF_BASE * (2**attempt))
                        continue
                    raise NoxMemError(resp.status_code, resp.text[:200])
                if not resp.ok:
                    raise NoxMemError(resp.status_code, resp.text[:200])
                return resp.json()
            except NoxMemError:
                raise
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_RETRY_BACKOFF_BASE * (2**attempt))

        raise NoxMemError(0, f"Request failed after {_MAX_RETRIES} attempts: {last_exc}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def health(self) -> HealthSnapshot:
        """Return a snapshot of API health metrics."""
        data = self._request("GET", "/api/health")
        return HealthSnapshot.from_dict(data)

    def search(
        self,
        query: str,
        limit: int = 5,
        user_id: Optional[str] = None,
    ) -> list[SearchResult]:
        """
        Hybrid BM25 + semantic search over memory chunks.

        Args:
            query: Natural-language search string.
            limit: Maximum number of results (default 5).
            user_id: Optional user scoping identifier.

        Returns:
            List of SearchResult ranked by RRF score.
        """
        params: dict[str, Any] = {"q": query, "limit": limit}
        if user_id is not None:
            params["userId"] = user_id
        data = self._request("GET", "/api/search", params=params)
        raw = data if isinstance(data, list) else data.get("results", [])
        return [SearchResult.from_dict(r) for r in raw]

    def answer(
        self,
        query: str,
        session_id: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> AnswerResponse:
        """
        Generate a grounded answer from memory.

        Args:
            query: The question to answer.
            session_id: Conversation session for multi-turn context.
            options: Extra options passed to the API.

        Returns:
            AnswerResponse with answer text + cited sources.
        """
        body: dict[str, Any] = {"query": query}
        if session_id is not None:
            body["sessionId"] = session_id
        if options:
            body.update(options)
        data = self._request("POST", "/api/answer", json=body)
        return AnswerResponse.from_dict(data)

    def kg_search(
        self,
        entity: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search knowledge graph entities by name."""
        params: dict[str, Any] = {"q": entity, "limit": limit}
        data = self._request("GET", "/api/kg", params=params)
        return data if isinstance(data, list) else data.get("entities", [])

    def kg_path(self, source: str, target: str) -> list[dict[str, Any]]:
        """Find shortest path between two KG entities."""
        params = {"source": source, "target": target}
        data = self._request("GET", "/api/kg/path", params=params)
        return data if isinstance(data, list) else data.get("path", [])

    def observability_health(self) -> dict[str, Any]:
        """Return raw observability/health JSON (F10 dashboard data)."""
        return self._request("GET", "/api/health")
