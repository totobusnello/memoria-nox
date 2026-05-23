"""
Shared corpus loader for the Q4 COMPARISON harness.

Produces a stable, deduplicated chunk stream for two benchmarks:

  - LoCoMo (snap-research/locomo, CC BY-NC 4.0).
    chunk.id = f"{sample_id}::{dia_id}"  — matches the gold_chunk_ids
    encoding in `eval/locomo/dry-run-sample.json` and `parser.ts`.

  - LongMemEval (xiaowu0162/longmemeval-cleaned, MIT).
    chunk.id = session_id  — matches the runner's gold extraction
    fallback (`gold_chunk_ids = answer_session_ids` when explicit
    gold_chunk_ids is absent on the query record, per `runner.py::_to_record`).

Why this exists
---------------
Pre-2026-05-23 the Q4 adapters had no canonical corpus source: each `setup()`
was a NO-OP, the gold IDs in dry-run-sample.json reference chunks that no
adapter had loaded, and validation produced 0/20 gold hits even on a baseline
that should retrieve them all. This loader fixes the root cause by yielding
the FULL corpus with the IDs the gold sets already use.

Design choices
--------------
1. Streaming generators. The full LongMemEval s_cleaned split is ~115k tokens
   per question × 500 questions ≈ tens of millions of tokens; loading into a
   single Python list would blow up RAM for the smaller-memory adapters.

2. JSONL cache at `eval/q4-comparison/cache/{locomo,longmemeval}.jsonl`.
   First call downloads the raw dataset from upstream and writes the parsed
   chunks. Subsequent calls iterate the cache line-by-line. Cache is gitignored
   (large, regenerable, license-restricted in LoCoMo's case).

3. Dedupe matches `paper/publication/baselines/longmemeval_hybrid_eval.py`
   semantics: within a single LongMemEval question, the same session_id can
   appear multiple times in the haystack (distractor design); we keep the
   first occurrence and skip the rest so the chunk corpus has unique IDs
   without losing gold matchability. Across questions, distinct chunks per
   distinct (qid, sid) — see `longmemeval_split` parameter for splits where
   IDs may collide across questions.

4. Adapter-friendly metadata. Each ChunkRecord exposes the source row data
   under `.metadata` so adapters that need timestamps, speaker roles, or
   question context can pull them without re-parsing the raw dataset.

5. No GEMINI_API_KEY required. The loader is corpus-only — embeddings are
   the adapter's job.

References:
  - paper/publication/baselines/locomo_eval.py   (LoCoMo parser source)
  - paper/publication/baselines/longmemeval_hybrid_eval.py  (LongMemEval)
  - eval/locomo/parser.ts                         (TS reference impl)
  - eval/longmemeval/parser.ts                    (TS reference impl)
  - specs/2026-05-23-Q4-comparison-execution-plan.md §5  (corpus parity)
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator


# ---------------------------------------------------------------------------
# Paths + dataset config (single source of truth pinned to the Python eval)
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
Q4_DIR = HERE.parent
CACHE_DIR = Q4_DIR / "cache"
RAW_DIR = CACHE_DIR / "raw"

# LoCoMo --------------------------------------------------------------------
LOCOMO_RAW_URL = (
    "https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json"
)
LOCOMO_RAW_FILE = RAW_DIR / "locomo10.json"
LOCOMO_CACHE = CACHE_DIR / "locomo.jsonl"
LOCOMO_LICENSE = "CC BY-NC 4.0 (snap-research/locomo)"

# LongMemEval ---------------------------------------------------------------
LONGMEMEVAL_REPO = "xiaowu0162/longmemeval-cleaned"
# Same revision pin used by the Python baseline so the corpus is bit-identical.
LONGMEMEVAL_REVISION = "98d7416c24c778c2fee6e6f3006e7a073259d48f"
LONGMEMEVAL_VALID_SPLITS = ("oracle", "s_cleaned", "m_cleaned")
LONGMEMEVAL_DEFAULT_SPLIT = "oracle"
LONGMEMEVAL_LICENSE = "MIT (xiaowu0162/longmemeval-cleaned)"


def _longmemeval_url(split: str) -> str:
    return (
        f"https://huggingface.co/datasets/{LONGMEMEVAL_REPO}"
        f"/resolve/{LONGMEMEVAL_REVISION}/longmemeval_{split}.json"
    )


def _longmemeval_raw_file(split: str) -> Path:
    return RAW_DIR / f"longmemeval_{split}.json"


def _longmemeval_cache(split: str) -> Path:
    # Default split uses the unsuffixed name so callers that don't care about
    # splits can iterate `longmemeval.jsonl` directly.
    suffix = "" if split == LONGMEMEVAL_DEFAULT_SPLIT else f"-{split}"
    return CACHE_DIR / f"longmemeval{suffix}.jsonl"


# ---------------------------------------------------------------------------
# Record schema
# ---------------------------------------------------------------------------


@dataclass
class ChunkRecord:
    """Canonical chunk record consumed by every Q4 adapter.

    Fields
    ------
    id : str
        Stable chunk identifier matching the gold_chunk_ids encoding in
        `eval/<dataset>/dry-run-sample.json`. Adapters MUST preserve this
        string when returning results from `search()` so the runner's gold
        matching works.
    text : str
        The chunk body. For LoCoMo: f"{speaker}: {text}" per turn. For
        LongMemEval: a session header + newline-joined "<role>: <content>"
        per turn, matching `extractSessionChunks` in parser.ts (and
        Python's `iter_session_chunks`).
    dataset : str
        "locomo" or "longmemeval".
    conversation_id : str
        LoCoMo sample_id (e.g. "conv-48") or LongMemEval question_id
        (e.g. "6aeb4375") — i.e. the grouping key that identifies which
        haystack the chunk belongs to.
    day : int
        Best-effort temporal index within the conversation. For LoCoMo we
        parse the trailing N from `session_N`. For LongMemEval there is no
        canonical day number; we use the position of the session inside the
        question's haystack (0-indexed). Adapters that ignore time can ignore
        this field.
    metadata : dict[str, Any]
        Free-form passthrough for source-row fields not promoted above.
        Adapters that need raw timestamps, role tags, session dates, or
        `is_answer_session` flags should read them from here.
    """

    id: str
    text: str
    dataset: str
    conversation_id: str
    day: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_jsonl(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_jsonl(cls, line: str) -> "ChunkRecord":
        row = json.loads(line)
        return cls(
            id=row["id"],
            text=row["text"],
            dataset=row["dataset"],
            conversation_id=row["conversation_id"],
            day=int(row["day"]),
            metadata=row.get("metadata") or {},
        )


# ---------------------------------------------------------------------------
# Small download helper (stdlib urllib only — keeps `requests` optional)
# ---------------------------------------------------------------------------


def _ensure_dirs() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)


def _download(url: str, target: Path, *, force: bool = False, timeout: int = 120) -> Path:
    _ensure_dirs()
    if target.exists() and not force:
        return target
    print(f"[corpus_loader] downloading {url}", file=sys.stderr)
    req = urllib.request.Request(
        url, headers={"User-Agent": "memoria-nox-q4-corpus-loader/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            target.write_bytes(r.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"download failed: HTTP {exc.code} for {url}. "
            "Network blocked? Re-run from a host with outbound HTTPS access."
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"download failed: {exc.reason} for {url}. "
            "Network unreachable? Re-run from a host with outbound HTTPS access."
        ) from exc
    print(
        f"[corpus_loader] saved {target} ({target.stat().st_size:,} bytes)",
        file=sys.stderr,
    )
    return target


# ---------------------------------------------------------------------------
# LoCoMo
# ---------------------------------------------------------------------------


_SESSION_DAY_RE = re.compile(r"session_(\d+)")


def _parse_locomo_day(session_key: str) -> int:
    """Extract integer N from `session_N`. Returns 0 if the key is malformed
    (we never want a corpus chunk dropped just because the day index is odd).
    """
    m = _SESSION_DAY_RE.match(session_key)
    return int(m.group(1)) if m else 0


def _iter_locomo_chunks_from_raw(raw_path: Path) -> Iterator[ChunkRecord]:
    """Stream ChunkRecords from the raw locomo10.json. Mirrors `iter_turns`
    in `paper/publication/baselines/locomo_eval.py` and `extractTurns` in
    `eval/locomo/parser.ts`.
    """
    payload = json.loads(raw_path.read_text())
    if not isinstance(payload, list):
        raise RuntimeError(
            f"unexpected LoCoMo shape: {type(payload).__name__} (expected list)"
        )
    for conv in payload:
        if not isinstance(conv, dict):
            continue
        sample_id = conv.get("sample_id")
        convo = conv.get("conversation") or {}
        if not sample_id or not isinstance(convo, dict):
            continue
        for k, v in convo.items():
            if not isinstance(k, str):
                continue
            if not k.startswith("session_") or k.endswith("_date_time"):
                continue
            if not isinstance(v, list):
                continue
            day = _parse_locomo_day(k)
            session_date = convo.get(f"{k}_date_time", "") if isinstance(
                convo.get(f"{k}_date_time", ""), str
            ) else ""
            for turn in v:
                if not isinstance(turn, dict):
                    continue
                dia_id = turn.get("dia_id")
                text = turn.get("text")
                speaker = turn.get("speaker") or ""
                if not dia_id or not text:
                    continue
                chunk_id = f"{sample_id}::{dia_id}"
                payload_text = f"{speaker}: {text}" if speaker else str(text)
                yield ChunkRecord(
                    id=chunk_id,
                    text=payload_text,
                    dataset="locomo",
                    conversation_id=str(sample_id),
                    day=day,
                    metadata={
                        "dia_id": str(dia_id),
                        "session_key": k,
                        "session_date": session_date,
                        "speaker": str(speaker),
                    },
                )


def _build_locomo_cache(raw_path: Path, cache_path: Path) -> int:
    """Parse raw → write JSONL cache. Returns chunk count."""
    _ensure_dirs()
    n = 0
    tmp = cache_path.with_suffix(cache_path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for rec in _iter_locomo_chunks_from_raw(raw_path):
            fh.write(rec.to_jsonl() + "\n")
            n += 1
    tmp.replace(cache_path)
    print(
        f"[corpus_loader] built LoCoMo cache: {cache_path} ({n:,} chunks)",
        file=sys.stderr,
    )
    return n


def load_locomo_corpus(*, force_refresh: bool = False) -> Iterable[ChunkRecord]:
    """Stream all LoCoMo turn-level chunks.

    Parameters
    ----------
    force_refresh : bool
        Re-download upstream and rebuild the cache even if it exists.

    Yields
    ------
    ChunkRecord
        One per conversational turn, with stable id `{sample_id}::{dia_id}`.

    Notes
    -----
    LoCoMo has ~10 conversations × ~300-1000 turns each ≈ 9k-10k chunks in
    total per the snap-research/locomo `locomo10.json` schema verified on
    2026-05-04. Anything < 5k or > 20k indicates upstream schema drift.

    License: see `paper/publication/baselines/locomo_eval.py` (CC BY-NC 4.0).
    Do NOT redistribute the raw file or the cache; both are gitignored.
    """
    _ensure_dirs()
    if force_refresh or not LOCOMO_CACHE.exists():
        # Only fetch if the raw upstream JSON is missing — tests can seed it
        # directly to stay offline.
        if force_refresh or not LOCOMO_RAW_FILE.exists():
            _download(LOCOMO_RAW_URL, LOCOMO_RAW_FILE, force=force_refresh)
        _build_locomo_cache(LOCOMO_RAW_FILE, LOCOMO_CACHE)
    with LOCOMO_CACHE.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            yield ChunkRecord.from_jsonl(line)


# ---------------------------------------------------------------------------
# LongMemEval
# ---------------------------------------------------------------------------


def _iter_longmemeval_chunks_from_raw(
    raw_path: Path,
) -> Iterator[ChunkRecord]:
    """Stream ChunkRecords from a raw LongMemEval split JSON.

    Each question's haystack contributes one chunk per *unique* session_id
    (first occurrence wins — mirrors the dedup logic in
    `paper/publication/baselines/longmemeval_hybrid_eval.py::iter_session_chunks`
    and `eval/longmemeval/parser.ts::extractSessionChunks`).

    Chunk id is the bare `session_id` so that the Q4 runner's gold extraction
    (`gold_chunk_ids = answer_session_ids` per `runner.py::_to_record`)
    matches without per-question prefixing.

    BUT: across DIFFERENT questions, the same session_id can correspond to
    different content (LongMemEval reuses session_id namespaces). To keep IDs
    unique across the corpus, we **scope** by (question_id, session_id) and
    yield distinct chunks. The runner's `_to_record` returns gold without
    question prefix, so adapters MUST filter to the current question's
    haystack via metadata.question_id when applying gold. The runner does
    this implicitly by only sending one question's query at a time.
    """
    payload = json.loads(raw_path.read_text())
    if isinstance(payload, dict) and "records" in payload:
        # dry-run-sample shape — no haystack_sessions text, no chunks to yield.
        print(
            "[corpus_loader] WARNING: dry-run-sample shape detected — "
            "no haystack_sessions field, yielding 0 chunks. Re-run with "
            "full HF data for a real corpus.",
            file=sys.stderr,
        )
        return
    if not isinstance(payload, list):
        raise RuntimeError(
            f"unexpected LongMemEval shape: {type(payload).__name__} (expected list)"
        )
    for q in payload:
        if not isinstance(q, dict):
            continue
        qid = q.get("question_id")
        sids = q.get("haystack_session_ids") or []
        dates = q.get("haystack_dates") or []
        sessions = q.get("haystack_sessions") or []
        answer_set = set(q.get("answer_session_ids") or [])
        if not qid or not isinstance(sessions, list) or not isinstance(sids, list):
            continue
        n = min(len(sids), len(sessions))
        seen: set[str] = set()
        for i in range(n):
            sid = sids[i]
            if not isinstance(sid, str) or not sid:
                continue
            if sid in seen:
                # Duplicate within the haystack — first occurrence canonical.
                continue
            seen.add(sid)
            date = dates[i] if i < len(dates) and isinstance(dates[i], str) else ""
            turns = sessions[i] if isinstance(sessions[i], list) else []
            lines: list[str] = [f"[session_id={sid} date={date}]"]
            for t in turns:
                if not isinstance(t, dict):
                    continue
                role = str(t.get("role", ""))
                content = str(t.get("content", "")).replace("\r", " ").replace("\n", " ")
                if not role and not content:
                    continue
                lines.append(f"{role}: {content}")
            yield ChunkRecord(
                id=str(sid),
                text="\n".join(lines),
                dataset="longmemeval",
                conversation_id=str(qid),
                day=i,
                metadata={
                    "question_id": str(qid),
                    "session_id": str(sid),
                    "session_date": date,
                    "is_answer_session": sid in answer_set,
                    "haystack_index": i,
                },
            )


def _build_longmemeval_cache(
    raw_path: Path, cache_path: Path
) -> int:
    """Parse raw → write JSONL cache. Returns chunk count."""
    _ensure_dirs()
    n = 0
    tmp = cache_path.with_suffix(cache_path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for rec in _iter_longmemeval_chunks_from_raw(raw_path):
            fh.write(rec.to_jsonl() + "\n")
            n += 1
    tmp.replace(cache_path)
    print(
        f"[corpus_loader] built LongMemEval cache: {cache_path} ({n:,} chunks)",
        file=sys.stderr,
    )
    return n


def load_longmemeval_corpus(
    split: str = LONGMEMEVAL_DEFAULT_SPLIT,
    *,
    force_refresh: bool = False,
) -> Iterable[ChunkRecord]:
    """Stream all LongMemEval session-level chunks for a given split.

    Parameters
    ----------
    split : str
        One of "oracle" (default, smallest, evidence-only), "s_cleaned"
        (paper headline split), or "m_cleaned" (frontier track, deferred).
    force_refresh : bool
        Re-download upstream and rebuild the cache even if it exists.

    Yields
    ------
    ChunkRecord
        One per unique (question_id, session_id) pair. Chunk id is the bare
        session_id; question scoping is preserved in metadata["question_id"].

    Notes
    -----
    Ballpark sizes (HF revision 98d7416c…):
        oracle      ~3,000-5,000 chunks   (~500 questions × few sessions)
        s_cleaned   ~50,000-60,000 chunks (~500 questions × ~40 sessions)
        m_cleaned   ~250,000 chunks       (~500 questions × ~500 sessions)

    License: MIT (xiaowu0162/longmemeval-cleaned). Cache gitignored.
    """
    if split not in LONGMEMEVAL_VALID_SPLITS:
        raise ValueError(
            f"unknown split {split!r}; valid: {LONGMEMEVAL_VALID_SPLITS}"
        )
    _ensure_dirs()
    cache_path = _longmemeval_cache(split)
    raw_path = _longmemeval_raw_file(split)
    if force_refresh or not cache_path.exists():
        # Only fetch if the raw upstream JSON is missing — tests can seed it
        # directly to stay offline.
        if force_refresh or not raw_path.exists():
            _download(_longmemeval_url(split), raw_path, force=force_refresh)
        _build_longmemeval_cache(raw_path, cache_path)
    with cache_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            yield ChunkRecord.from_jsonl(line)


# ---------------------------------------------------------------------------
# CLI entry — `python -m lib.corpus_loader stats` for quick smoke
# ---------------------------------------------------------------------------


def _cli() -> int:
    """Minimal CLI: counts chunks in each dataset. Useful for manual smoke
    against a fresh checkout: `python -m lib.corpus_loader stats`.
    """
    import argparse

    p = argparse.ArgumentParser(description="Q4 corpus loader CLI")
    p.add_argument(
        "cmd",
        choices=["stats", "build", "head"],
        help="stats=count; build=force download+parse; head=first 3 chunks per dataset",
    )
    p.add_argument(
        "--split",
        default=LONGMEMEVAL_DEFAULT_SPLIT,
        choices=LONGMEMEVAL_VALID_SPLITS,
        help="LongMemEval split (default oracle)",
    )
    p.add_argument(
        "--force-refresh",
        action="store_true",
        help="Re-download upstream + rebuild cache",
    )
    args = p.parse_args()

    if args.cmd == "build":
        # Just iterate to trigger the cache build; discard results.
        n_loc = sum(1 for _ in load_locomo_corpus(force_refresh=args.force_refresh))
        n_lme = sum(
            1
            for _ in load_longmemeval_corpus(
                args.split, force_refresh=args.force_refresh
            )
        )
        print(f"locomo: {n_loc:,} chunks")
        print(f"longmemeval[{args.split}]: {n_lme:,} chunks")
        return 0

    if args.cmd == "stats":
        n_loc = sum(1 for _ in load_locomo_corpus(force_refresh=args.force_refresh))
        n_lme = sum(
            1
            for _ in load_longmemeval_corpus(
                args.split, force_refresh=args.force_refresh
            )
        )
        print(f"locomo: {n_loc:,} chunks")
        print(f"longmemeval[{args.split}]: {n_lme:,} chunks")
        return 0

    if args.cmd == "head":
        for i, c in enumerate(load_locomo_corpus()):
            print(json.dumps(asdict(c), ensure_ascii=False)[:300])
            if i >= 2:
                break
        print("---")
        for i, c in enumerate(load_longmemeval_corpus(args.split)):
            print(json.dumps(asdict(c), ensure_ascii=False)[:300])
            if i >= 2:
                break
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(_cli())
