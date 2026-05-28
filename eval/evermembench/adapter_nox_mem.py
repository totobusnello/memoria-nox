"""
nox-mem Adapter for EverMemBench — Phase C (2026-05-28).

Connects nox-mem (CLI ingest + HTTP search API) to the EverMemBench
evaluation harness.

Iteration history (Sat 2026-05-28 Q4 cross-system experiment):
  - Phase A (PR #363, batch 004 = 56.07%): flat-paragraph markdown with
    inline [Group][Speaker][Time] prefixes. Multi-hop 4% / Temporal 10%.
  - Phase B (batch 004 = 57.19%): one H2 block per message + per-turn
    context window. Multi-hop COLLAPSED to 0% (still atomic per-turn);
    Temporal climbed to 23.33%; Updating dropped 84%->74%.
  - Phase C (THIS file, batch 004 = 53.83%): one chunk per (date, group)
    containing all turns from all speakers in that group on that day.
    Hypothesis: multi-hop reasoning requires the answer LLM to see multiple
    turns in the SAME chunk so it can stitch partial evidence (paper §4.2).
    RESULT: Hypothesis FALSIFIED. Multi-hop stayed at 0% AND single-hop
    collapsed 86%->49%, temporal collapsed 23%->3%, updating dropped
    74%->64%. Profile gained +2%, hard-linked gained +8%. NET -3.36 vs B.

Gate verdict (Phase 3 / full 5 batches): use Phase B variant.
NOX_ADAPTER_MODE default REMAINS "phaseB" to keep Phase 3 on the best
known variant. Phase C is selectable via NOX_ADAPTER_MODE=phaseC for
future re-analysis.

Chunk format (Phase C):
    ## [YYYY-MM-DD | Group N] Conversation
    date: YYYY-MM-DD
    group: N
    participants: alice, bob, carol
    message_count: 12
    transcript:
    [HH:MM] alice: <message>
    [HH:MM] bob: <message>
    [HH:MM] carol: <message>
    ...

Usage (from EverMemBench root after installing harness):
    cp eval/evermembench/adapter_nox_mem.py \\
        benchmarks/EverMemBench/eval/src/adapters/nox_mem_adapter.py

Environment variables:
    NOX_API_BASE     — nox-mem API base URL (default: http://127.0.0.1:18802)
    NOX_DB_PATH      — per-batch DB path override (REQUIRED for isolation)
    NOX_MEM_BIN      — path to nox-mem CLI binary (default: "nox-mem" on PATH)
    NOX_ADAPTER_MODE — "phaseB" (DEFAULT, best variant) / "phaseC" / "baseline"
"""
import asyncio
import os
import shlex
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

# ---------------------------------------------------------------------------
# BaseAdapter import: adjust path when placed inside EverMemBench tree
# ---------------------------------------------------------------------------
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

# Phase C chunking strategy (2026-05-28) — one chunk per (date, group)
PHASEC_DAY_GROUP_BLOCK_HEADER = (
    "## [{date} | {group}] Conversation\n"
    "date: {date}\n"
    "group: {group}\n"
    "participants: {participants}\n"
    "message_count: {message_count}\n"
    "transcript:\n"
)

# Phase B (kept as default — best known variant)
PHASEB_MESSAGE_BLOCK = (
    "## [{time} | {group} | {speaker}]\n"
    "speaker: {speaker}\n"
    "group: {group}\n"
    "date: {date}\n"
    "time: {time}\n"
    "context: {context}\n"
    "content: {content}\n"
)

PHASEB_DAY_GROUP_ROLLUP = (
    "## Day {date} -- {group} digest\n"
    "group: {group}\n"
    "date: {date}\n"
    "participants: {participants}\n"
    "message_count: {message_count}\n"
    "summary: Conversation on {date} in {group} between {participants_short}. "
    "First line: {first_line}\n"
)

# Phase A baseline (kept for ablation)
MESSAGE_TEMPLATE = "[Group: {group}][Speaker: {speaker}][Time: {time}] {content}"

DEFAULT_INGEST_BATCH_SIZE = 50
INGEST_SUBPROCESS_TIMEOUT = 180
# IMPORTANT: default REMAINS phaseB — Phase C results showed regression.
DEFAULT_ADAPTER_MODE = "phaseB"
PHASEB_CONTEXT_WINDOW = 2


class NoxMemAdapter(BaseAdapter):
    """nox-mem adapter for EverMemBench multi-person group chat eval."""

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
        self.adapter_mode = (
            config.get("adapter_mode", "")
            or os.environ.get("NOX_ADAPTER_MODE", DEFAULT_ADAPTER_MODE)
        )
        self.context_window = int(
            config.get("phaseb_context_window", PHASEB_CONTEXT_WINDOW)
        )
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.search_timeout)
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def add(self, dataset, user_id, days_to_process=None, **kwargs):
        start_ms = time.monotonic() * 1000
        errors: List[str] = []

        db_path = os.environ.get("NOX_DB_PATH", "")
        if not db_path:
            errors.append("NOX_DB_PATH env var is required for isolated run")
            return AddResult(
                success=False, days_processed=0, messages_sent=0,
                errors=errors,
                metadata={"isolation_check": "failed", "user_id": user_id},
            )
        if "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db" in db_path:
            errors.append(f"NOX_DB_PATH={db_path} points at prod DB; refusing.")
            return AddResult(
                success=False, days_processed=0, messages_sent=0,
                errors=errors,
                metadata={"isolation_check": "prod_path_blocked", "user_id": user_id},
            )

        messages = self._collect_messages(dataset, days_to_process)
        if not messages:
            return AddResult(
                success=True, days_processed=0, messages_sent=0,
                errors=[], metadata={"reason": "no_messages_after_filter"},
            )

        days_seen = {getattr(m, "date", None) or self._date_of(m) for m in messages}
        total_sent = 0

        # Build day-group cache (used by both Phase B and Phase C)
        self._day_group_cache: Dict[Tuple[str, str], List[Any]] = {}
        for m in messages:
            key = (self._date_of(m), str(getattr(m, "group", "?")))
            self._day_group_cache.setdefault(key, []).append(m)
        self._digest_emitted: set = set()

        # ------------------------------------------------------------------
        # Phase C: one chunk per (date, group) — ingest day-group BLOCKS
        # ------------------------------------------------------------------
        if self.adapter_mode == "phaseC":
            day_group_keys = list(self._day_group_cache.keys())
            day_group_blocks: List[Tuple[Tuple[str, str], str]] = []
            for key in day_group_keys:
                block_text = self._format_day_group_block(key, self._day_group_cache[key])
                if block_text:
                    day_group_blocks.append((key, block_text))

            blocks_per_file = max(1, self.ingest_batch_size // 2)
            for batch_idx, batch_start in enumerate(
                range(0, len(day_group_blocks), blocks_per_file)
            ):
                batch = day_group_blocks[batch_start:batch_start + blocks_per_file]
                try:
                    sent_msgs = sum(
                        len(self._day_group_cache[k]) for k, _ in batch
                    )
                    await self._ingest_phasec_batch(batch, user_id, batch_idx)
                    total_sent += sent_msgs
                except Exception as exc:
                    errors.append(
                        f"phaseC batch {batch_idx} ({len(batch)} day-groups) "
                        f"failed: {type(exc).__name__}: {exc}"
                    )
                if self.ingest_delay_ms:
                    await asyncio.sleep(self.ingest_delay_ms / 1000.0)

            elapsed_ms = time.monotonic() * 1000 - start_ms
            success = (total_sent == len(messages)) and not errors
            return AddResult(
                success=success, days_processed=len(days_seen),
                messages_sent=total_sent, errors=errors,
                metadata={
                    "user_id": user_id, "db_path": db_path,
                    "ingest_batch_size": self.ingest_batch_size,
                    "adapter_mode": self.adapter_mode,
                    "elapsed_ms": elapsed_ms,
                    "messages_total": len(messages),
                    "day_group_count": len(self._day_group_cache),
                    "blocks_per_file": blocks_per_file,
                },
            )

        # ------------------------------------------------------------------
        # Phase B / baseline path (legacy per-message batching)
        # ------------------------------------------------------------------
        for batch_start in range(0, len(messages), self.ingest_batch_size):
            batch = messages[batch_start:batch_start + self.ingest_batch_size]
            batch_idx = batch_start // self.ingest_batch_size
            try:
                sent = await self._ingest_batch(batch, user_id, batch_idx, batch_start)
                total_sent += sent
            except Exception as exc:
                errors.append(
                    f"batch {batch_idx} ({len(batch)} msgs) failed: {type(exc).__name__}: {exc}"
                )
            if self.ingest_delay_ms:
                await asyncio.sleep(self.ingest_delay_ms / 1000.0)

        elapsed_ms = time.monotonic() * 1000 - start_ms
        success = (total_sent == len(messages)) and not errors
        return AddResult(
            success=success, days_processed=len(days_seen),
            messages_sent=total_sent, errors=errors,
            metadata={
                "user_id": user_id, "db_path": db_path,
                "ingest_batch_size": self.ingest_batch_size,
                "adapter_mode": self.adapter_mode,
                "context_window": self.context_window,
                "elapsed_ms": elapsed_ms,
                "messages_total": len(messages),
                "day_group_count": len(self._day_group_cache),
            },
        )

    async def _ingest_phasec_batch(self, batch, user_id, batch_idx):
        """Write N day-group blocks to one markdown file and ingest."""
        lines = [
            f"# EverMemBench user_id={user_id} batch={batch_idx} "
            f"mode=phaseC day_groups={len(batch)}\n"
        ]
        for key, block_text in batch:
            lines.append(block_text)
            lines.append("")
        content = "\n".join(lines)

        tmp = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".md",
            prefix=f"evermembench-phc-{user_id}-b{batch_idx:04d}-",
            delete=False,
        )
        tmp_path = tmp.name
        try:
            tmp.write(content)
            tmp.close()

            argv = [self.nox_mem_bin, "ingest", tmp_path]
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy(),
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=INGEST_SUBPROCESS_TIMEOUT
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise RuntimeError(
                    f"nox-mem ingest timed out after {INGEST_SUBPROCESS_TIMEOUT}s "
                    f"(phaseC batch {batch_idx}, {len(batch)} day-groups)"
                )

            if proc.returncode != 0:
                err_text = (stderr or b"").decode("utf-8", errors="replace")[:500]
                raise RuntimeError(
                    f"nox-mem ingest exited {proc.returncode}: {err_text}"
                )
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    async def _ingest_batch(self, batch, user_id, batch_idx, batch_start):
        """Per-message ingest (Phase B default + baseline)."""
        lines = [f"# EverMemBench user_id={user_id} batch={batch_idx} mode={self.adapter_mode}\n"]

        if self.adapter_mode == "baseline":
            for m in batch:
                lines.append(self._format_message_baseline(m))
                lines.append("")
        else:
            for i, m in enumerate(batch):
                lines.append(self._format_message_phaseb(m, batch_start + i))
                lines.append("")
                key = (self._date_of(m), str(getattr(m, "group", "?")))
                if key in self._digest_emitted:
                    continue
                day_group_msgs = self._day_group_cache.get(key, [])
                if day_group_msgs and m is day_group_msgs[-1]:
                    digest = self._format_day_group_digest(key, day_group_msgs)
                    if digest:
                        lines.append(digest)
                        lines.append("")
                        self._digest_emitted.add(key)

        content = "\n".join(lines)

        tmp = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".md",
            prefix=f"evermembench-{user_id}-b{batch_idx:04d}-",
            delete=False,
        )
        tmp_path = tmp.name
        try:
            tmp.write(content)
            tmp.close()

            argv = [self.nox_mem_bin, "ingest", tmp_path]
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy(),
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=INGEST_SUBPROCESS_TIMEOUT
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise RuntimeError(
                    f"nox-mem ingest timed out after {INGEST_SUBPROCESS_TIMEOUT}s "
                    f"(batch {batch_idx}, {len(batch)} msgs)"
                )

            if proc.returncode != 0:
                err_text = (stderr or b"").decode("utf-8", errors="replace")[:500]
                raise RuntimeError(f"nox-mem ingest exited {proc.returncode}: {err_text}")
            return len(batch)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    # ---------------------------------------------------------------------
    # Phase C formatter
    # ---------------------------------------------------------------------
    def _format_day_group_block(self, key, day_group_msgs):
        """
        Emit a single H2-block markdown chunk containing the entire
        conversation for a (date, group) pair. All turns inlined as
        `[HH:MM] speaker: message`. Sorted by time within the block.
        """
        if not day_group_msgs:
            return ""
        date, group = key

        ordered = sorted(
            day_group_msgs,
            key=lambda m: getattr(m, "timestamp", None) or getattr(m, "time", "") or "",
        )

        speakers: List[str] = []
        seen_speakers: set = set()
        for m in ordered:
            sp = str(getattr(m, "speaker", "?"))
            if sp not in seen_speakers:
                seen_speakers.add(sp)
                speakers.append(sp)
        participants = ", ".join(speakers) if speakers else "?"

        header = PHASEC_DAY_GROUP_BLOCK_HEADER.format(
            date=date, group=group,
            participants=participants, message_count=len(ordered),
        )

        transcript_lines: List[str] = []
        for m in ordered:
            speaker = str(getattr(m, "speaker", "?"))
            content = str(getattr(m, "content", "")).strip()
            time_raw = (
                getattr(m, "time", None)
                or getattr(m, "timestamp", None)
                or ""
            )
            time_str = str(time_raw)
            if "T" in time_str:
                tpart = time_str.split("T", 1)[1]
                time_str = tpart[:5] if len(tpart) >= 5 else tpart
            elif len(time_str) >= 5 and time_str[2] == ":":
                time_str = time_str[:5]
            safe_content = content.replace("\n", " ").strip()
            transcript_lines.append(f"[{time_str}] {speaker}: {safe_content}")

        return header + "\n".join(transcript_lines) + "\n"

    def _format_message_phaseb(self, msg, global_idx):
        group = str(getattr(msg, "group", "?"))
        speaker = str(getattr(msg, "speaker", "?"))
        content = str(getattr(msg, "content", "")).strip()
        time_str = str(
            getattr(msg, "time", None)
            or getattr(msg, "timestamp", None)
            or "?"
        )
        date = self._date_of(msg)

        key = (date, group)
        day_group_msgs = self._day_group_cache.get(key, [])
        try:
            pos = day_group_msgs.index(msg)
        except ValueError:
            pos = -1
        context_parts: List[str] = []
        if pos > 0:
            start = max(0, pos - self.context_window)
            for prev in day_group_msgs[start:pos]:
                prev_speaker = str(getattr(prev, "speaker", "?"))
                prev_content = str(getattr(prev, "content", "")).strip()
                prev_snip = prev_content[:120].replace("\n", " ")
                if len(prev_content) > 120:
                    prev_snip += "..."
                context_parts.append(f"{prev_speaker}: {prev_snip}")
        context_str = " | ".join(context_parts) if context_parts else "(start of conversation)"

        return PHASEB_MESSAGE_BLOCK.format(
            time=time_str, group=group, speaker=speaker,
            date=date, context=context_str, content=content,
        )

    def _format_message_baseline(self, msg):
        group = str(getattr(msg, "group", "?"))
        speaker = str(getattr(msg, "speaker", "?"))
        content = str(getattr(msg, "content", "")).strip()
        time_str = str(
            getattr(msg, "time", None)
            or getattr(msg, "timestamp", None)
            or "?"
        )
        return MESSAGE_TEMPLATE.format(
            group=group, speaker=speaker, time=time_str, content=content,
        )

    def _format_day_group_digest(self, key, day_group_msgs):
        date, group = key
        speakers: List[str] = []
        seen_speakers: set = set()
        for m in day_group_msgs:
            sp = str(getattr(m, "speaker", "?"))
            if sp not in seen_speakers:
                seen_speakers.add(sp)
                speakers.append(sp)
        participants = ", ".join(speakers)
        if len(speakers) <= 3:
            participants_short = ", ".join(speakers)
        else:
            participants_short = ", ".join(speakers[:3]) + f", and {len(speakers)-3} others"
        first_line = ""
        if day_group_msgs:
            first_content = str(getattr(day_group_msgs[0], "content", "")).strip()
            first_line = first_content[:180].replace("\n", " ")
            if len(first_content) > 180:
                first_line += "..."
        return PHASEB_DAY_GROUP_ROLLUP.format(
            date=date, group=group, participants=participants,
            message_count=len(day_group_msgs),
            participants_short=participants_short, first_line=first_line,
        )

    def _date_of(self, msg):
        d = getattr(msg, "date", None)
        if d:
            return str(d)
        ts = getattr(msg, "time", None) or getattr(msg, "timestamp", None) or ""
        if isinstance(ts, str) and "T" in ts:
            return ts.split("T", 1)[0]
        return str(ts)[:10] if ts else "?"

    def _collect_messages(self, dataset, days_to_process):
        messages: List[Any] = []
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
                if day_date:
                    for m in sorted_msgs:
                        if not getattr(m, "date", None):
                            try:
                                setattr(m, "date", day_date)
                            except Exception:
                                pass
                messages.extend(sorted_msgs)
        return messages

    async def search(self, query, user_id, top_k=10, **kwargs):
        start_ms = time.monotonic() * 1000
        session = await self._get_session()
        payload = {"query": query, "limit": top_k, "hybrid": True}

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
                query=query, retrieved_memories=[],
                context="[nox-mem search failed: " + str(exc) + "]",
                search_duration_ms=time.monotonic() * 1000 - start_ms,
                metadata={"error": str(exc)},
            )

        if isinstance(data, list):
            raw_results = data
        elif isinstance(data, dict):
            raw_results = data.get("results", [])
        else:
            return SearchResult(
                question_id=kwargs.get("question_id", "unknown"),
                query=query, retrieved_memories=[],
                context="[nox-mem returned unexpected shape]",
                search_duration_ms=time.monotonic() * 1000 - start_ms,
                metadata={"raw": str(data)[:200]},
            )

        memories: List[str] = []
        for item in raw_results:
            if isinstance(item, dict):
                content = item.get("chunk_text") or item.get("content") or ""
                if content:
                    memories.append(content)

        context_lines = [f"{i + 1}. {m}" for i, m in enumerate(memories)]
        context = "\n".join(context_lines) if context_lines else "[No memories retrieved]"
        elapsed_ms = time.monotonic() * 1000 - start_ms
        return SearchResult(
            question_id=kwargs.get("question_id", "unknown"),
            query=query, retrieved_memories=memories,
            context=context, search_duration_ms=elapsed_ms,
            metadata={
                "api_base": self.api_base, "top_k": top_k,
                "returned": len(memories),
                "took_ms_api": data.get("took_ms", None) if isinstance(data, dict) else None,
            },
        )

    def get_system_info(self):
        return {
            "name": "nox_mem", "type": "NoxMemAdapter",
            "api_base": self.api_base, "nox_mem_bin": self.nox_mem_bin,
            "search_top_k": self.search_top_k,
            "adapter_mode": self.adapter_mode,
            "phaseb_context_window": self.context_window,
            "version": "phase-c-0.1-mode-default-phaseB",
        }
