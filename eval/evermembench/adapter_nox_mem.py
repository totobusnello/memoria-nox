"""
nox-mem Adapter for EverMemBench.

Connects nox-mem (CLI ingest + HTTP search API) to the EverMemBench
evaluation harness.

Usage (from EverMemBench root after installing harness):
    cp eval/evermembench/adapter_nox_mem.py benchmarks/EverMemBench/eval/src/adapters/nox_mem_adapter.py
    # then register in eval/src/adapters/__init__.py and eval/cli.py

Environment variables:
    NOX_API_BASE     — nox-mem API base URL (default: http://127.0.0.1:18802)
    NOX_DB_PATH      — per-batch DB path override (REQUIRED for isolation;
                       points the CLI subprocess at an isolated DB)
    NOX_MEM_BIN      — path to nox-mem CLI binary (default: "nox-mem" on PATH)

Implementation: Option B (CLI subprocess).

The Add stage writes group-chat messages to a temp markdown file and
invokes `nox-mem ingest <tempfile>` with NOX_DB_PATH pointing at an isolated
per-batch DB. This sidesteps the HTTP API (which is single-tenant against
the live DB) and avoids any contention with a running production instance.

The Search stage uses the HTTP API (`POST /api/search`) — but the API must
be started with the SAME NOX_DB_PATH that the CLI ingested into. See
`eval/evermembench/README.md` step 5 for the wiring pattern.
"""
import asyncio
import os
import shlex
import tempfile
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
DEFAULT_NOX_MEM_BIN = "nox-mem"

# Message format injected into nox-mem chunks during Add stage.
# Mirrors the `[Group: X][Speaker: Y]content` convention used by other adapters.
MESSAGE_TEMPLATE = "[Group: {group}][Speaker: {speaker}][Time: {time}] {content}"

# How many messages per batched ingest subprocess call.
# Each call writes a temp .md file with N messages separated by blank lines
# (one chunk per message after nox-mem ingest segmentation).
DEFAULT_INGEST_BATCH_SIZE = 50

# Timeout (seconds) per `nox-mem ingest` subprocess call.
INGEST_SUBPROCESS_TIMEOUT = 180


class NoxMemAdapter(BaseAdapter):
    """
    nox-mem adapter for EverMemBench multi-person group chat evaluation.

    Add stage:
        Writes group-chat messages to a temp markdown file, then invokes
        `nox-mem ingest <tempfile>` via subprocess. The subprocess inherits
        NOX_DB_PATH from the caller's environment, so isolation is achieved
        by setting NOX_DB_PATH=/tmp/evermembench-{user_id}.db before invoking
        the harness.

        ISOLATION REQUIREMENT: each batch must use a separate nox-mem DB.
        The caller is responsible for setting NOX_DB_PATH per batch.

    Search stage:
        Calls POST /api/search with the QA question text. The HTTP API must
        be started against the SAME NOX_DB_PATH that Add ingested into.

    Config YAML example (nox_mem.yaml):
    ```yaml
    name: "nox_mem"
    api_base: "${NOX_API_BASE}"   # default http://127.0.0.1:18802
    nox_mem_bin: "${NOX_MEM_BIN}"  # default "nox-mem" on PATH
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
        self.nox_mem_bin = config.get("nox_mem_bin", "") or os.environ.get(
            "NOX_MEM_BIN", DEFAULT_NOX_MEM_BIN
        )
        self.search_top_k = config.get("search_top_k", 10)
        self.search_timeout = config.get("search_timeout", 30)
        self.ingest_batch_size = config.get("ingest_batch_size", DEFAULT_INGEST_BATCH_SIZE)
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
    # Add stage — Option B (CLI subprocess)
    # ------------------------------------------------------------------

    async def add(
        self,
        dataset: Dataset,
        user_id: str,
        days_to_process: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> AddResult:
        """
        Ingest group chat messages into nox-mem via CLI subprocess.

        Strategy:
            1. Flatten dataset → ordered list of GroupChatMessage
            2. Chunk into batches of `ingest_batch_size`
            3. For each batch: write to NamedTemporaryFile (.md), then
               `nox-mem ingest <tempfile> --source evermembench-{user_id}`
            4. Subprocess inherits NOX_DB_PATH from caller's environment.

        Returns:
            AddResult with success, days_processed, messages_sent, errors.

        Required env in caller:
            NOX_DB_PATH=/tmp/evermembench-{user_id}.db
            NOX_MEM_BIN=/path/to/nox-mem (optional, default = "nox-mem" on PATH)
        """
        start_ms = time.monotonic() * 1000
        errors: List[str] = []

        # Sanity-check isolation: refuse to run if NOX_DB_PATH is unset OR
        # points at a production-looking path. This is a defense against
        # accidentally writing into the live prod DB.
        db_path = os.environ.get("NOX_DB_PATH", "")
        if not db_path:
            errors.append(
                "NOX_DB_PATH env var is required for isolated EverMemBench run "
                "(set to e.g. /tmp/evermembench-{user_id}.db before invoking harness)"
            )
            return AddResult(
                success=False,
                days_processed=0,
                messages_sent=0,
                errors=errors,
                metadata={"isolation_check": "failed", "user_id": user_id},
            )
        if "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db" in db_path:
            errors.append(
                f"NOX_DB_PATH={db_path} points at production DB; refusing to ingest "
                "EverMemBench data into prod. Use /tmp/evermembench-{user_id}.db."
            )
            return AddResult(
                success=False,
                days_processed=0,
                messages_sent=0,
                errors=errors,
                metadata={"isolation_check": "prod_path_blocked", "user_id": user_id},
            )

        messages = self._collect_messages(dataset, days_to_process)
        if not messages:
            return AddResult(
                success=True,
                days_processed=0,
                messages_sent=0,
                errors=[],
                metadata={"reason": "no_messages_after_filter", "user_id": user_id},
            )

        days_seen = {getattr(m, "date", None) or self._date_of(m) for m in messages}
        total_sent = 0

        # Batch ingest
        for batch_start in range(0, len(messages), self.ingest_batch_size):
            batch = messages[batch_start:batch_start + self.ingest_batch_size]
            batch_idx = batch_start // self.ingest_batch_size
            try:
                sent = await self._ingest_batch(batch, user_id, batch_idx)
                total_sent += sent
            except Exception as exc:  # noqa: BLE001 — surface all failures
                errors.append(
                    f"batch {batch_idx} ({len(batch)} msgs) failed: {type(exc).__name__}: {exc}"
                )

            if self.ingest_delay_ms:
                await asyncio.sleep(self.ingest_delay_ms / 1000.0)

        elapsed_ms = time.monotonic() * 1000 - start_ms
        success = (total_sent == len(messages)) and not errors
        return AddResult(
            success=success,
            days_processed=len(days_seen),
            messages_sent=total_sent,
            errors=errors,
            metadata={
                "user_id": user_id,
                "db_path": db_path,
                "ingest_batch_size": self.ingest_batch_size,
                "elapsed_ms": elapsed_ms,
                "messages_total": len(messages),
            },
        )

    async def _ingest_batch(
        self,
        batch: List["GroupChatMessage"],
        user_id: str,
        batch_idx: int,
    ) -> int:
        """
        Write batch to temp .md file, invoke `nox-mem ingest <file>`,
        return count of messages dispatched (NOT post-ingest chunk count —
        nox-mem may split per its own segmenter).
        """
        # Build markdown content. Each message on its own paragraph so
        # nox-mem's segmenter treats it as a chunk (or close to one).
        lines = [f"# EverMemBench user_id={user_id} batch={batch_idx}\n"]
        for m in batch:
            lines.append(self._format_message(m))
            lines.append("")  # blank line separator

        content = "\n".join(lines)

        # Write to NamedTemporaryFile with .md suffix.
        # delete=False so subprocess can read it; we clean up in finally.
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".md",
            prefix=f"evermembench-{user_id}-b{batch_idx:04d}-",
            delete=False,
        )
        tmp_path = tmp.name
        try:
            tmp.write(content)
            tmp.close()

            # Invoke `nox-mem ingest <tempfile> --source evermembench-{user_id}`
            # via execvp-style argv (NOT shell) to avoid injection.
            # NOTE: `--source` flag intentionally removed (2026-05-28 batch 004 run).
            # The current nox-mem CLI (v3.8) does not accept --source on `ingest`;
            # passing it caused all 205 ingests to fail with exit code 1. If a future
            # nox-mem release re-adds --source, restore the two extra argv items here.
            argv = [
                self.nox_mem_bin,
                "ingest",
                tmp_path,
            ]

            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy(),  # propagate NOX_DB_PATH, OPENCLAW_WORKSPACE, etc
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=INGEST_SUBPROCESS_TIMEOUT
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise RuntimeError(
                    f"nox-mem ingest subprocess timed out after {INGEST_SUBPROCESS_TIMEOUT}s "
                    f"(batch {batch_idx}, {len(batch)} messages)"
                )

            if proc.returncode != 0:
                err_text = (stderr or b"").decode("utf-8", errors="replace")[:500]
                raise RuntimeError(
                    f"nox-mem ingest exited {proc.returncode}: {err_text}"
                )

            return len(batch)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _format_message(self, msg: "GroupChatMessage") -> str:
        """Format a GroupChatMessage into a single nox-mem chunk paragraph."""
        # Defensive attribute extraction — GroupChatMessage may have varying
        # field names depending on EverMemBench version.
        group = getattr(msg, "group", "?")
        speaker = getattr(msg, "speaker", "?")
        content = getattr(msg, "content", "").strip()
        time_str = (
            getattr(msg, "time", None)
            or getattr(msg, "timestamp", None)
            or "?"
        )
        return MESSAGE_TEMPLATE.format(
            group=group,
            speaker=speaker,
            time=time_str,
            content=content,
        )

    def _date_of(self, msg: "GroupChatMessage") -> str:
        """Extract date string from message (best effort)."""
        ts = getattr(msg, "time", None) or getattr(msg, "timestamp", None) or ""
        if isinstance(ts, str) and "T" in ts:
            return ts.split("T", 1)[0]
        return str(ts)[:10] if ts else "?"

    def _collect_messages(
        self,
        dataset: "Dataset",
        days_to_process: Optional[List[str]],
    ) -> List["GroupChatMessage"]:
        """
        Flatten dataset into ordered list of GroupChatMessage objects.

        Respects `days_to_process` filter (None = all days).
        Messages within each day are sorted by timestamp.
        """
        messages: List[GroupChatMessage] = []
        for day in getattr(dataset, "days", []):
            day_date = getattr(day, "date", None)
            if days_to_process and day_date not in days_to_process:
                continue
            groups = getattr(day, "groups", {}) or {}
            for _group_name, group_msgs in groups.items():
                sorted_msgs = sorted(
                    group_msgs,
                    key=lambda m: getattr(m, "timestamp", None) or getattr(m, "time", ""),
                )
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
        The API server must be running against the SAME isolated NOX_DB_PATH
        that Add stage ingested into.
        """
        start_ms = time.monotonic() * 1000
        session = await self._get_session()

        payload = {
            "query": query,
            "limit": top_k,
            "hybrid": True,
        }

        try:
            async with session.post(
                f"{self.api_base}/api/search",
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except aiohttp.ClientError as exc:
            return SearchResult(
                question_id=kwargs.get("question_id", "unknown"),
                query=query,
                retrieved_memories=[],
                context="[nox-mem search failed: " + str(exc) + "]",
                search_duration_ms=time.monotonic() * 1000 - start_ms,
                metadata={"error": str(exc)},
            )

        # Validate shape before .get() access
        # (see feedback_adapter_response_shape_validation.md)
        # nox-mem prod API returns a top-level JSON array of result dicts (not
        # `{"results": [...]}`). Accept both shapes for forward-compatibility
        # in case future API revisions wrap the array.
        if isinstance(data, list):
            raw_results = data
        elif isinstance(data, dict):
            raw_results = data.get("results", [])
        else:
            return SearchResult(
                question_id=kwargs.get("question_id", "unknown"),
                query=query,
                retrieved_memories=[],
                context="[nox-mem returned unexpected shape]",
                search_duration_ms=time.monotonic() * 1000 - start_ms,
                metadata={"raw": str(data)[:200]},
            )

        memories: List[str] = []
        for item in raw_results:
            if isinstance(item, dict):
                # nox-mem API returns `chunk_text`; some search variants may use `content`.
                content = item.get("chunk_text") or item.get("content") or ""
                if content:
                    memories.append(content)

        # Format context string for LLM answer stage
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
                "took_ms_api": data.get("took_ms", None) if isinstance(data, dict) else None,
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
            "nox_mem_bin": self.nox_mem_bin,
            "search_top_k": self.search_top_k,
            "version": "option-b-cli-0.2",
        }
