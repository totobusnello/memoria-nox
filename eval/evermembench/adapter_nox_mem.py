"""
nox-mem Adapter for EverMemBench.

Connects nox-mem HTTP search API to the EverMemBench evaluation harness.

Usage (from EverMemBench root after installing harness):
    cp eval/evermembench/adapter_nox_mem.py benchmarks/EverMemBench/eval/src/adapters/nox_mem_adapter.py
    # then register in eval/src/adapters/__init__.py and eval/cli.py

Environment variables:
    NOX_API_BASE     — nox-mem API base URL (default: http://127.0.0.1:18802)
    NOX_DB_PATH      — per-batch DB path override (REQUIRED for isolation)

Status: SKELETON — Add and Search stubs need implementation.
"""
import asyncio
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

# ---------------------------------------------------------------------------
# BaseAdapter import: adjust path when placed inside EverMemBench tree
# ---------------------------------------------------------------------------
# When copied to benchmarks/EverMemBench/eval/src/adapters/:
#   from eval.src.adapters.base import BaseAdapter
#   from eval.src.core.data_models import Dataset, GroupChatMessage, AddResult, SearchResult
#
# For local development / testing outside EverMemBench tree:
try:
    from eval.src.adapters.base import BaseAdapter
    from eval.src.core.data_models import Dataset, GroupChatMessage, AddResult, SearchResult
except ImportError:
    # Stub imports for skeleton validation without EverMemBench installed
    from typing import Protocol
    class BaseAdapter(Protocol):  # type: ignore[no-redef]
        pass
    Dataset = Any  # type: ignore[assignment,misc]
    AddResult = Any  # type: ignore[assignment,misc]
    SearchResult = Any  # type: ignore[assignment,misc]
    GroupChatMessage = Any  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_NOX_API_BASE = "http://127.0.0.1:18802"

# Message format injected into nox-mem chunks during Add stage.
# Mirrors the `[Group: X][Speaker: Y]content` convention used by other adapters.
MESSAGE_TEMPLATE = "[Group: {group}][Speaker: {speaker}] {content}"


class NoxMemAdapter(BaseAdapter):
    """
    nox-mem adapter for EverMemBench multi-person group chat evaluation.

    Add stage:
        Ingests group chat messages as plain-text chunks via nox-mem HTTP
        POST /api/ingest (or nox-mem CLI ingest).

        ISOLATION REQUIREMENT: each batch must use a separate nox-mem DB.
        Set NOX_DB_PATH env var before spawning nox-mem API per batch, or
        use separate systemd instances on different ports.

    Search stage:
        Calls POST /api/search with the QA question text and returns
        top_k results formatted as context string for LLM answer stage.

    Config YAML example (nox_mem.yaml):
    ```yaml
    name: "nox_mem"
    api_base: "${NOX_API_BASE}"   # default http://127.0.0.1:18802
    search_top_k: 10
    search_timeout: 30
    ingest_batch_size: 50
    ingest_delay_ms: 0
    ```
    """

    def __init__(self, config: Dict[str, Any], output_dir: Optional[Path] = None):
        super().__init__(config, output_dir)

        self.api_base = config.get("api_base", "").rstrip("/") or os.environ.get(
            "NOX_API_BASE", DEFAULT_NOX_API_BASE
        )
        self.search_top_k = config.get("search_top_k", 10)
        self.search_timeout = config.get("search_timeout", 30)
        self.ingest_batch_size = config.get("ingest_batch_size", 50)
        self.ingest_delay_ms = config.get("ingest_delay_ms", 0)

        # HTTP session — created lazily to allow use in async context
        self._session: Optional[aiohttp.ClientSession] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.search_timeout)
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    # ------------------------------------------------------------------
    # Add stage
    # ------------------------------------------------------------------

    async def add(
        self,
        dataset: Dataset,
        user_id: str,
        days_to_process: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> AddResult:
        """
        Ingest group chat messages into nox-mem.

        TODO: Implement one of the two options below.

        Option A — HTTP ingest (preferred if nox-mem exposes POST /api/ingest):
            POST http://127.0.0.1:18802/api/ingest
            Body: {"content": "<formatted message>", "source": "evermembench",
                   "metadata": {"speaker": ..., "group": ..., "date": ..., "user_id": ...}}
            Batch messages in groups of `ingest_batch_size` to avoid overwhelming the API.

        Option B — CLI ingest (fallback):
            Write messages to a temp .md file, then call:
            `nox-mem ingest <tempfile> --source evermembench`
            Requires NOX_DB_PATH to be set in subprocess env for isolation.

        ISOLATION: Before calling add(), ensure nox-mem API is running against
        the correct isolated DB for this user_id batch:
            NOX_DB_PATH=/tmp/evermembench-{user_id}.db nox-mem serve &

        Current state: raises NotImplementedError (skeleton).
        """
        raise NotImplementedError(
            "NoxMemAdapter.add() is not yet implemented.\n"
            "See TODO comments in this method for implementation options.\n"
            "Implement Option A (HTTP ingest) or Option B (CLI ingest)."
        )

    def _format_message(self, msg: GroupChatMessage) -> str:
        """Format a GroupChatMessage into the nox-mem chunk text."""
        return MESSAGE_TEMPLATE.format(
            group=msg.group,
            speaker=msg.speaker,
            content=msg.content.strip(),
        )

    def _collect_messages(
        self,
        dataset: Dataset,
        days_to_process: Optional[List[str]],
    ) -> List[GroupChatMessage]:
        """
        Flatten dataset into ordered list of GroupChatMessage objects.

        Respects `days_to_process` filter (None = all days).
        Messages within each day are sorted by timestamp.
        """
        messages: List[GroupChatMessage] = []
        for day in dataset.days:
            if days_to_process and day.date not in days_to_process:
                continue
            for group_name, group_msgs in day.groups.items():
                sorted_msgs = sorted(group_msgs, key=lambda m: m.timestamp)
                messages.extend(sorted_msgs)
        return messages

    # ------------------------------------------------------------------
    # Search stage
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 10,
        **kwargs: Any,
    ) -> SearchResult:
        """
        Retrieve memories from nox-mem for a QA question.

        Calls POST /api/search with hybrid mode (BM25 + Gemini semantic + RRF).

        TODO: Validate response shape before .get() access.
              nox-mem /api/search returns:
              {
                "results": [
                  {"content": "...", "score": 0.xx, "metadata": {...}},
                  ...
                ],
                "query": "...",
                "took_ms": N
              }

        Current state: partially implemented — HTTP call wired, response
        parsing needs validation against live /api/search schema.
        """
        start_ms = time.monotonic() * 1000
        session = await self._get_session()

        payload = {
            "query": query,
            "limit": top_k,
            "hybrid": True,
        }

        # TODO: Add user_id filtering if nox-mem supports multi-tenant namespacing.
        # Currently nox-mem is single-tenant; isolation is via separate DB per batch.

        try:
            async with session.post(
                f"{self.api_base}/api/search",
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except aiohttp.ClientError as exc:
            # Return empty result rather than crashing the pipeline.
            # Harness will generate an incorrect answer, evaluate as wrong.
            return SearchResult(
                question_id=kwargs.get("question_id", "unknown"),
                query=query,
                retrieved_memories=[],
                context="[nox-mem search failed: " + str(exc) + "]",
                search_duration_ms=time.monotonic() * 1000 - start_ms,
                metadata={"error": str(exc)},
            )

        # TODO: Validate `data` is a dict before .get() (see feedback_adapter_response_shape_validation.md)
        if not isinstance(data, dict):
            return SearchResult(
                question_id=kwargs.get("question_id", "unknown"),
                query=query,
                retrieved_memories=[],
                context="[nox-mem returned unexpected shape]",
                search_duration_ms=time.monotonic() * 1000 - start_ms,
                metadata={"raw": str(data)[:200]},
            )

        raw_results = data.get("results", [])
        memories: List[str] = []
        for item in raw_results:
            if isinstance(item, dict):
                content = item.get("content", "")
                if content:
                    memories.append(content)

        # Format context string for LLM answer stage
        # Convention mirrors other adapters: numbered list
        context_lines = [f"{i + 1}. {m}" for i, m in enumerate(memories)]
        context = "\n".join(context_lines) if context_lines else "[No memories retrieved]"

        elapsed_ms = time.monotonic() * 1000 - start_ms
        return SearchResult(
            question_id=kwargs.get("question_id", "unknown"),
            query=query,
            retrieved_memories=memories,
            context=context,
            search_duration_ms=elapsed_ms,
            metadata={
                "api_base": self.api_base,
                "top_k": top_k,
                "returned": len(memories),
                "took_ms_api": data.get("took_ms", None),
            },
        )

    # ------------------------------------------------------------------
    # System info
    # ------------------------------------------------------------------

    def get_system_info(self) -> Dict[str, Any]:
        return {
            "name": "nox_mem",
            "type": "NoxMemAdapter",
            "api_base": self.api_base,
            "search_top_k": self.search_top_k,
            "version": "skeleton-0.1",
        }
