"""
nox-mem Adapter for EverMemBench.

Connects nox-mem HTTP search API to the EverMemBench evaluation harness.

Usage (from EverMemBench root after installing harness):
    cp eval/evermembench/adapter_nox_mem.py benchmarks/EverMemBench/eval/src/adapters/nox_mem_adapter.py
    # then register in eval/src/adapters/__init__.py and eval/cli.py

Environment variables:
    NOX_API_BASE     — nox-mem API base URL (default: http://127.0.0.1:18802)
    NOX_DB_PATH      — per-batch DB path override (REQUIRED for isolation)
    NOX_MEM_BIN      — path to nox-mem CLI entry (default: nox-mem on PATH;
                       on VPS: node /root/.openclaw/workspace/tools/nox-mem/dist/index.js)

Status: WIREABLE SKELETON — Add stage uses CLI subprocess (Option B, the only
        real path given nox-mem has no POST /api/ingest); Search stage uses
        HTTP /api/search. Both code-paths are present; run against a live
        nox-mem instance to validate end-to-end.
"""
import asyncio
import json
import os
import shlex
import shutil
import subprocess
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
        Ingest group chat messages into nox-mem via CLI subprocess.

        Strategy (Option B — CLI ingest):
            1. Collect messages from dataset (respecting days_to_process filter).
            2. Write a single markdown file containing all formatted messages,
               grouped by day with date headers, to a temp path.
            3. Invoke `nox-mem ingest <tempfile> --source evermembench-<uid>`
               via asyncio subprocess. Env carries NOX_DB_PATH for isolation.

        Rationale: nox-mem does not expose POST /api/ingest. The HTTP API is
        read-mostly (search/kg/health/crystallize). Writes go through the CLI
        which routes to ingestFile()/ingestEntityFile() with full schema
        guarantees (FTS5 + sqlite-vec + section_boost + retention_days).

        ISOLATION REQUIREMENT: caller must set NOX_DB_PATH=/tmp/evermembench-
        <user_id>.db in the environment BEFORE invoking this adapter. The
        env-var is propagated to the subprocess. Failure to isolate will
        cross-contaminate batches and pollute production memory if the host
        is the VPS.

        Returns:
            AddResult with success status + messages_sent count + errors list.
        """
        nox_bin = os.environ.get("NOX_MEM_BIN", shutil.which("nox-mem"))
        if not nox_bin:
            return AddResult(
                success=False,
                days_processed=0,
                messages_sent=0,
                errors=[
                    "nox-mem CLI not found. Set NOX_MEM_BIN env var or "
                    "add nox-mem to PATH. On VPS: NOX_MEM_BIN='node "
                    "/root/.openclaw/workspace/tools/nox-mem/dist/index.js'"
                ],
            )

        # Isolation guard — refuse to ingest into the default/prod DB.
        # NOX_DB_PATH must be set explicitly to a per-batch path.
        db_path = os.environ.get("NOX_DB_PATH", "")
        if not db_path or "/evermembench-" not in db_path:
            return AddResult(
                success=False,
                days_processed=0,
                messages_sent=0,
                errors=[
                    "NOX_DB_PATH not set or does not match isolation pattern "
                    "'/evermembench-<user_id>.db'. Refusing to ingest to avoid "
                    "prod-DB cross-contamination. Set explicitly: "
                    f"export NOX_DB_PATH=/tmp/evermembench-{user_id}.db"
                ],
            )

        messages = self._collect_messages(dataset, days_to_process)
        if not messages:
            return AddResult(
                success=True,
                days_processed=0,
                messages_sent=0,
                errors=[],
                metadata={"note": "no messages matched filter"},
            )

        # Build a single markdown file grouped by day.
        # Each day becomes a section; each message a paragraph with attribution.
        lines: List[str] = [f"# EverMemBench batch {user_id}", ""]
        last_date: Optional[str] = None
        days_seen: set = set()
        for msg in messages:
            if msg.date != last_date:
                lines.append("")
                lines.append(f"## {msg.date}")
                lines.append("")
                last_date = msg.date
                days_seen.add(msg.date)
            lines.append(self._format_message(msg))
            lines.append("")

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=f"-evermembench-{user_id}.md",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp.write("\n".join(lines))
            tmp_path = tmp.name

        # Build command. Support both "nox-mem" binary and "node /path/to/index.js".
        # shutil.which can return shebang-script paths; CLI binary takes positional file.
        if " " in nox_bin:
            # Multi-token like "node /path/to/index.js" — split on whitespace
            cmd = shlex.split(nox_bin) + [
                "ingest", tmp_path,
                "--source", f"evermembench-{user_id}",
            ]
        else:
            cmd = [
                nox_bin, "ingest", tmp_path,
                "--source", f"evermembench-{user_id}",
            ]

        env = os.environ.copy()
        # NOX_DB_PATH already in env (we checked above)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=kwargs.get("add_timeout", 3600),  # 1h default for full batch
            )
        except asyncio.TimeoutError:
            return AddResult(
                success=False,
                days_processed=len(days_seen),
                messages_sent=0,
                errors=[f"nox-mem ingest timed out after {kwargs.get('add_timeout', 3600)}s"],
            )
        except Exception as exc:
            return AddResult(
                success=False,
                days_processed=len(days_seen),
                messages_sent=0,
                errors=[f"subprocess error: {type(exc).__name__}: {exc}"],
            )
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        stdout_text = stdout.decode("utf-8", errors="replace") if stdout else ""
        stderr_text = stderr.decode("utf-8", errors="replace") if stderr else ""

        success = proc.returncode == 0
        errors: List[str] = []
        if not success:
            errors.append(
                f"nox-mem ingest exited {proc.returncode}; stderr tail: "
                + stderr_text[-500:]
            )

        # Note: nox-mem CLI prints "Done: N embedded, M errors" on last line.
        # Per CLAUDE.md rule #2, never trust that line — caller should validate
        # via /api/health.vectorCoverage post-add. We surface the raw counts only.
        return AddResult(
            success=success,
            days_processed=len(days_seen),
            messages_sent=len(messages),
            errors=errors,
            metadata={
                "cli_stdout_tail": stdout_text[-500:],
                "tmp_input_size_bytes": len("\n".join(lines).encode("utf-8")),
                "validate_via": (
                    f"curl {self.api_base}/api/health | jq "
                    ".vectorCoverage  # confirm embedded==total"
                ),
            },
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
