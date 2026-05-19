#!/usr/bin/env python3
"""LongMemEval Hybrid retrieval evaluation (FTS5 + Gemini dense + RRF k=60).

Self-contained Python re-implementation of memoria-nox's hybrid retrieval
architecture, evaluated on a stratified 100-question subset of the
LongMemEval-cleaned `oracle` split (Di Wu et al., ICLR 2025, arXiv:2410.10813).

⚠️  Python re-implementation, NOT production nox-mem code path. Validates the
    *retrieval shape* of FTS5 + Gemini dense + RRF k=60. Does NOT execute
    nox-mem's TypeScript pipeline. Production-path validation requires
    `npx tsx eval/longmemeval/run.ts` against the real CLI on the VPS.

Q1 LoCoMo (turn-level evidence) vs Q2 LongMemEval (session-level evidence):
    - Gold relevance unit:  turn `dia_id` (LoCoMo) → session id (LongMemEval).
    - Chunk granularity:    per-turn (LoCoMo) → per-session (LongMemEval D4).
    - Categories:           5 LoCoMo cats → 6 LongMemEval cats (abstention
                            variants `_abs` folded into parent for sampling,
                            tracked separately on output).
    - Same metrics:         nDCG@10, MRR, Recall@10, Precision@5.

Components:
    1. FTS5 BM25  : SQLite virtual table, unicode61 remove_diacritics 2
    2. Dense      : Gemini `gemini-embedding-001` (3072d), L2-normed cosine
    3. Fusion     : Reciprocal Rank Fusion, k=60, top-10 after fusion

Usage:
    export GEMINI_API_KEY=AIza...
    python3 longmemeval_hybrid_eval.py download   # fetch oracle split (~MB)
    python3 longmemeval_hybrid_eval.py index      # FTS5 + per-session chunks
    python3 longmemeval_hybrid_eval.py embed      # Gemini doc embeddings
    python3 longmemeval_hybrid_eval.py eval       # n=100 stratified eval
    python3 longmemeval_hybrid_eval.py full       # all of the above

Output:
    /tmp/longmemeval-oracle.json                          (dataset cache)
    /tmp/longmemeval-hybrid-eval.db                       (FTS5 + embed cache)
    paper/publication/results/longmemeval-hybrid-results.jsonl
    paper/publication/results/longmemeval-hybrid-summary.md

Target cost: < $0.20 for n=100 (per-question haystacks → ~1-2k session
embeddings + 100 query embeddings on `gemini-embedding-001` free tier).
Target wall clock: < 15 min first run, < 30 s cached.

Reproducibility: seed=42, LCG-style stratified shuffle on `(category, _abs)`.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import sqlite3
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

try:
    import numpy as np
except ImportError:
    print("[fatal] `numpy` not installed. Run: pip install numpy", file=sys.stderr)
    sys.exit(2)

# ── Dataset config (HuggingFace, MIT license) ────────────────────────────────
HF_REPO = "xiaowu0162/longmemeval-cleaned"
HF_REVISION = "98d7416c24c778c2fee6e6f3006e7a073259d48f"  # pinned 2026-05-17
VALID_SPLITS = ("oracle", "s_cleaned", "m_cleaned")
DEFAULT_SPLIT = "oracle"  # cheap plumbing; switch to s_cleaned for headline
LICENSE = "MIT (xiaowu0162/longmemeval-cleaned)"
CITATION = (
    "Di Wu et al. LongMemEval: Benchmarking Chat Assistants on Long-Term "
    "Interactive Memory. ICLR 2025. arXiv:2410.10813."
)

# These are set at runtime by configure_split(). Sentinels here for static analysis.
SPLIT: str = DEFAULT_SPLIT
HF_FILENAME: str = f"longmemeval_{DEFAULT_SPLIT}.json"
HF_URL: str = f"https://huggingface.co/datasets/{HF_REPO}/resolve/{HF_REVISION}/{HF_FILENAME}"
CACHE: Path = Path(f"/tmp/longmemeval-{DEFAULT_SPLIT}.json")
DB_PATH: Path = Path(f"/tmp/longmemeval-hybrid-eval-{DEFAULT_SPLIT}.db")
RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"
RESULTS: Path = RESULTS_DIR / f"longmemeval-hybrid-results.jsonl"
SUMMARY: Path = RESULTS_DIR / f"longmemeval-hybrid-summary.md"
LOCAL_FALLBACK = Path(__file__).resolve().parents[2] / "eval" / "longmemeval" / "dry-run-sample.json"


def configure_split(split: str) -> None:
    """Set per-split paths globally. Idempotent."""
    global SPLIT, HF_FILENAME, HF_URL, CACHE, DB_PATH, RESULTS, SUMMARY
    if split not in VALID_SPLITS:
        raise ValueError(f"unknown split {split!r}; valid: {VALID_SPLITS}")
    SPLIT = split
    HF_FILENAME = f"longmemeval_{split}.json"
    HF_URL = f"https://huggingface.co/datasets/{HF_REPO}/resolve/{HF_REVISION}/{HF_FILENAME}"
    CACHE = Path(f"/tmp/longmemeval-{split}.json")
    DB_PATH = Path(f"/tmp/longmemeval-hybrid-eval-{split}.db")
    suffix = "" if split == "oracle" else f"-{split}"
    RESULTS = RESULTS_DIR / f"longmemeval-hybrid-results{suffix}.jsonl"
    SUMMARY = RESULTS_DIR / f"longmemeval-hybrid-summary{suffix}.md"

# ── Categories (paper §3, 6 base; `_abs` folded for sampling, kept on output) ─
BASE_CATEGORIES = [
    "single-session-user",
    "single-session-assistant",
    "single-session-preference",
    "temporal-reasoning",
    "knowledge-update",
    "multi-session",
]

SUBSET_TOTAL = 100  # stratified n=100, distributed across 6 categories
SEED = 42

# ── Hybrid retrieval config (matches production nox-mem) ─────────────────────
GEMINI_MODEL = "gemini-embedding-001"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:embedContent"
)
EMBED_DIM = 3072
RRF_K = 60
TOP_K_FTS = 20
TOP_K_DENSE = 20
TOP_K_FINAL = 10

# Sequential pacing (kept for eval loop only; corpus embed uses parallel batch).
BATCH_SLEEP = 0.05
MAX_RETRIES = 5

# Parallel batch embed config (added 2026-05-19 — perf/q2-batch-parallel-embedding).
# Target rate: ~10 embed/s. Gemini free-tier embedding RPM ≈ 1500 (~25/s),
# so BATCH_PARALLEL=10 stays at ~40% of the headroom. Override via env
# LONGMEMEVAL_BATCH_PARALLEL=N for tuning during the s_cleaned full run.
BATCH_PARALLEL = max(1, int(os.environ.get("LONGMEMEVAL_BATCH_PARALLEL", "10")))
# Per-item retries inside the parallel pool (exponential backoff w/ jitter).
ITEM_MAX_RETRIES = 5
# Per-batch top-level retries (refeed the whole failed batch up to N times).
BATCH_MAX_RETRIES = 3
# Base backoff for item-level 429/5xx: delay_ms = BACKOFF_BASE_MS * 2^attempt + jitter.
BACKOFF_BASE_MS = 100


# ─────────────────────────────────────────────────────────────────────────────
# API-key gate
# ─────────────────────────────────────────────────────────────────────────────
def check_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        print(
            "\n"
            "  ╭─────────────────────────────────────────────────────────────╮\n"
            "  │ GEMINI_API_KEY is not set.                                  │\n"
            "  │                                                             │\n"
            "  │ This evaluation requires Gemini embeddings to compute the   │\n"
            "  │ dense-retrieval branch of the hybrid pipeline.              │\n"
            "  │                                                             │\n"
            "  │ Fix:                                                        │\n"
            "  │     export GEMINI_API_KEY=AIza...                           │\n"
            "  │     python3 longmemeval_hybrid_eval.py full                 │\n"
            "  │                                                             │\n"
            "  │ Get a key: https://aistudio.google.com/app/apikey           │\n"
            "  │ Cost estimate for this run: < $0.20                         │\n"
            "  ╰─────────────────────────────────────────────────────────────╯\n",
            file=sys.stderr,
        )
        sys.exit(3)
    return key


# ─────────────────────────────────────────────────────────────────────────────
# Dataset download (HF resolve URL → /tmp cache)
# ─────────────────────────────────────────────────────────────────────────────
def download(force: bool = False) -> Path:
    if CACHE.exists() and not force:
        print(f"[download] cached: {CACHE} ({CACHE.stat().st_size:,} bytes)", file=sys.stderr)
        return CACHE
    print(f"[download] {HF_URL}", file=sys.stderr)
    req = urllib.request.Request(
        HF_URL,
        headers={"User-Agent": "memoria-nox-longmemeval-hybrid-eval/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            CACHE.write_bytes(r.read())
    except urllib.error.HTTPError as e:
        print(f"[download] HTTP {e.code} fetching HF dataset", file=sys.stderr)
        print(f"[download] falling back to local dry-run-sample.json", file=sys.stderr)
        if LOCAL_FALLBACK.exists():
            CACHE.write_bytes(LOCAL_FALLBACK.read_bytes())
        else:
            raise RuntimeError(
                f"HF fetch failed ({e.code}) and no local fallback at {LOCAL_FALLBACK}"
            ) from e
    except urllib.error.URLError as e:
        print(f"[download] URLError fetching HF dataset: {e.reason}", file=sys.stderr)
        if LOCAL_FALLBACK.exists():
            print(f"[download] falling back to local dry-run-sample.json", file=sys.stderr)
            CACHE.write_bytes(LOCAL_FALLBACK.read_bytes())
        else:
            raise
    print(f"[download] saved: {CACHE} ({CACHE.stat().st_size:,} bytes)", file=sys.stderr)
    return CACHE


def load_corpus() -> list[dict[str, Any]]:
    """Load the LongMemEval split. Returns list of question records.

    The HF file is a JSON array of question objects (one per question), each
    with its own `haystack_session_ids`, `haystack_dates`, `haystack_sessions`.
    The local dry-run-sample.json is a different shape ({meta, records}) — we
    handle both for resilience.
    """
    raw = json.loads(CACHE.read_text())
    if isinstance(raw, dict) and "records" in raw:
        # Dry-run-sample shape: meta+records, no haystack_sessions present.
        # Mark each record so callers know they cannot ingest haystacks.
        print("[corpus] WARNING: loaded dry-run-sample shape — no haystack text", file=sys.stderr)
        return [{"_dry_run_only": True, **r} for r in raw.get("records", [])]
    if not isinstance(raw, list):
        raise RuntimeError(f"unexpected dataset shape: {type(raw).__name__}")
    return raw


# ─────────────────────────────────────────────────────────────────────────────
# Per-question session-chunk extraction (D4: per-session, not per-turn)
# ─────────────────────────────────────────────────────────────────────────────
def derive_base_category(question_type: str, question_id: str) -> tuple[str, bool]:
    """Split LongMemEval question_type/question_id into (base_cat, is_abstention).

    Per parser.ts: in `longmemeval-cleaned`, abstention is signalled by
    question_id suffix `_abs` (NOT by question_type). We accept either
    source for forward compat.
    """
    is_abs = question_id.endswith("_abs") or question_type.endswith("_abs")
    stripped = question_type[:-len("_abs")] if question_type.endswith("_abs") else question_type
    return stripped, is_abs


def iter_session_chunks(corpus: list[dict]) -> list[tuple[str, str, str, str, str, bool]]:
    """Yield (chunk_id, question_id, session_id, session_date, text, is_answer).

    chunk_id = f"{question_id}::{session_id}" — unique per question so that
    the same session_id reused across questions doesn't collide.

    Text format mirrors parser.ts D4: header `[session_id=<sid> date=<date>]`
    followed by newline-joined `<role>: <content>` per turn.

    Dedup note (s_cleaned fix, 2026-05-18): in larger LongMemEval splits
    (s_cleaned, m_cleaned) the same `session_id` can legitimately appear
    multiple times inside a single question's `haystack_session_ids` array —
    the distractor design re-cites filler sessions to inflate haystack size.
    Because gold matching uses `f"{qid}::{sid}"` (set-based), the first
    occurrence is canonical and subsequent occurrences are redundant data.
    Skipping them in Python preserves the PRIMARY KEY invariant on
    `chunks.chunk_id` and keeps gold matching intact. Composite-with-turn-idx
    keys were rejected because they would break gold matching at line ~441
    (`gold_chunk_ids = [f"{qid}::{sid}" for sid in gold_set]`).
    """
    out: list[tuple[str, str, str, str, str, bool]] = []
    total_dup_count = 0
    questions_with_dups = 0
    for q in corpus:
        if q.get("_dry_run_only"):
            continue  # dry-run sample has no haystack_sessions field
        qid = q.get("question_id")
        sids = q.get("haystack_session_ids") or []
        dates = q.get("haystack_dates") or []
        sessions = q.get("haystack_sessions") or []
        answer_set = set(q.get("answer_session_ids") or [])
        if not qid or not isinstance(sessions, list):
            continue
        n = min(len(sids), len(sessions))
        seen_sids: set[str] = set()
        q_dup_count = 0
        for i in range(n):
            sid = sids[i]
            if sid in seen_sids:
                # Duplicate session_id within this question's haystack — skip.
                # First occurrence already captured the canonical chunk;
                # gold matching is set-based on f"{qid}::{sid}", so the
                # second occurrence cannot add new relevance signal.
                q_dup_count += 1
                continue
            seen_sids.add(sid)
            date = dates[i] if i < len(dates) else ""
            turns = sessions[i] or []
            lines = [f"[session_id={sid} date={date}]"]
            for t in turns:
                if not isinstance(t, dict):
                    continue
                role = str(t.get("role", ""))
                content = str(t.get("content", "")).replace("\r", " ").replace("\n", " ")
                if not role and not content:
                    continue
                lines.append(f"{role}: {content}")
            chunk_id = f"{qid}::{sid}"
            is_answer = sid in answer_set
            out.append((chunk_id, qid, sid, str(date), "\n".join(lines), is_answer))
        if q_dup_count:
            total_dup_count += q_dup_count
            questions_with_dups += 1
    if total_dup_count:
        print(
            f"[chunks] deduped {total_dup_count} duplicate session_id entries "
            f"across {questions_with_dups} questions (expected on s_cleaned/m_cleaned)",
            file=sys.stderr,
        )
    return out


# ─────────────────────────────────────────────────────────────────────────────
# SQLite index (FTS5 + embedding BLOB cache)
# ─────────────────────────────────────────────────────────────────────────────
def open_db() -> sqlite3.Connection:
    con = sqlite3.connect(str(DB_PATH))
    con.execute("PRAGMA journal_mode=WAL")
    return con


def build_index(corpus: list[dict]) -> int:
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = open_db()
    con.execute(
        "CREATE TABLE chunks ("
        " chunk_id TEXT PRIMARY KEY,"
        " question_id TEXT,"
        " session_id TEXT,"
        " session_date TEXT,"
        " text TEXT,"
        " is_answer_session INTEGER,"
        " embedding BLOB)"
    )
    con.execute(
        "CREATE INDEX idx_chunks_qid ON chunks(question_id)"
    )
    con.execute(
        "CREATE VIRTUAL TABLE chunks_fts USING fts5("
        " text, content='chunks', content_rowid='rowid', "
        " tokenize='unicode61 remove_diacritics 2')"
    )
    rows = []
    for chunk_id, qid, sid, date, text, is_ans in iter_session_chunks(corpus):
        rows.append((chunk_id, qid, sid, date, text, int(is_ans)))
    con.executemany(
        "INSERT INTO chunks(chunk_id,question_id,session_id,session_date,text,is_answer_session) "
        "VALUES(?,?,?,?,?,?)",
        rows,
    )
    con.execute("INSERT INTO chunks_fts(rowid,text) SELECT rowid,text FROM chunks")
    con.commit()
    n = con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    con.close()
    print(f"[index] {n:,} session-chunks in {DB_PATH}", file=sys.stderr)
    return n


# ─────────────────────────────────────────────────────────────────────────────
# Gemini embedding (single-call API; stdlib urllib for zero pip deps beyond np)
# ─────────────────────────────────────────────────────────────────────────────
def _backoff_seconds(attempt: int) -> float:
    """Exponential backoff with full jitter: BACKOFF_BASE_MS * 2^attempt + jitter.

    `attempt` is 0-based on the FIRST retry (i.e. delay before retry #1 after
    the original failure). Caps at ~16 s so 429 storms don't stall the run
    past the batch budget.
    """
    base = (BACKOFF_BASE_MS / 1000.0) * (2 ** attempt)
    jitter = random.random() * (BACKOFF_BASE_MS / 1000.0)  # 0..BASE_MS jitter
    return min(16.0, base + jitter)


def embed_one(
    text: str,
    api_key: str,
    *,
    task_type: str = "RETRIEVAL_DOCUMENT",
    max_retries: int = ITEM_MAX_RETRIES,
    quiet: bool = False,
) -> list[float]:
    """Call Gemini embedContent once. Retries on 429/5xx with exponential backoff + jitter.

    `quiet=True` silences per-retry stderr logs (used in parallel batch path,
    where the batch coordinator already logs an aggregate).
    """
    body = json.dumps(
        {
            "model": f"models/{GEMINI_MODEL}",
            "content": {"parts": [{"text": text}]},
            "taskType": task_type,
            "outputDimensionality": EMBED_DIM,
        }
    ).encode("utf-8")
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    last_err: str = ""
    for attempt in range(0, max_retries + 1):
        req = urllib.request.Request(GEMINI_URL, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                j = json.loads(r.read())
                vals = j.get("embedding", {}).get("values") or j.get("embedding", {}).get("value")
                if not vals or len(vals) != EMBED_DIM:
                    raise RuntimeError(
                        f"embedding shape mismatch: got {len(vals) if vals else 0}, want {EMBED_DIM}"
                    )
                return vals
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code} {e.reason}"
            if e.code in (429, 500, 502, 503, 504) and attempt < max_retries:
                delay = _backoff_seconds(attempt)
                if not quiet:
                    print(
                        f"[embed retry {attempt + 1}/{max_retries}] {last_err}; backoff {delay:.2f}s",
                        file=sys.stderr,
                    )
                time.sleep(delay)
                continue
            raise RuntimeError(f"Gemini API error: {last_err}") from e
        except urllib.error.URLError as e:
            last_err = f"URLError {e.reason}"
            if attempt < max_retries:
                delay = _backoff_seconds(attempt)
                if not quiet:
                    print(
                        f"[embed retry {attempt + 1}/{max_retries}] {last_err}; backoff {delay:.2f}s",
                        file=sys.stderr,
                    )
                time.sleep(delay)
                continue
            raise
    raise RuntimeError(f"Gemini API exhausted retries: {last_err}")


def embed_batch_parallel(
    items: list[tuple[Any, str]],
    api_key: str,
    *,
    task_type: str = "RETRIEVAL_DOCUMENT",
    parallel: int = BATCH_PARALLEL,
) -> tuple[dict[Any, list[float]], dict[Any, str]]:
    """Embed a batch of (key, text) pairs in parallel via thread pool.

    Returns ({key: vector}, {key: error_msg}). Two separate dicts so callers
    can decide what to do with failures (retry the whole batch, skip, or
    abort). Determinism: result order is irrelevant because callers map
    back by `key`, so non-deterministic completion order from the pool does
    NOT alter the final corpus → embedding mapping or any downstream ranking.

    Uses `as_completed` to surface per-item failures eagerly, mirroring
    Promise.allSettled semantics (we want to know which items failed rather
    than failing the whole batch on first error).

    Each worker uses urllib (blocking I/O) — Python threads are fine for
    I/O-bound HTTP and bypass the GIL during the syscall.
    """
    if not items:
        return {}, {}
    n = len(items)
    workers = max(1, min(parallel, n))
    successes: dict[Any, list[float]] = {}
    errors: dict[Any, str] = {}

    def _run(key: Any, text: str) -> tuple[Any, list[float] | None, str | None]:
        try:
            v = embed_one(text, api_key, task_type=task_type, quiet=True)
            return key, v, None
        except Exception as e:  # noqa: BLE001 — surface any embed failure
            return key, None, f"{type(e).__name__}: {e}"

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(_run, k, t) for k, t in items]
        for f in as_completed(futures):
            key, vec, err = f.result()
            if vec is not None:
                successes[key] = vec
            else:
                errors[key] = err or "unknown error"
    return successes, errors


def pack_vec(v: list[float]) -> bytes:
    arr = np.asarray(v, dtype=np.float32)
    n = float(np.linalg.norm(arr))
    if n > 0:
        arr = arr / n
    return arr.tobytes()


def unpack_vec(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32)


def embed_corpus(api_key: str) -> int:
    """Embed corpus chunks via parallel batched Gemini calls.

    Refactor (2026-05-19, perf/q2-batch-parallel-embedding):
      - Batches of N=BATCH_PARALLEL (default 10) issued concurrently via
        ThreadPoolExecutor — Promise.allSettled-style: per-item failures
        are captured, not fatal.
      - Per-item exponential backoff w/ jitter on 429/5xx (ITEM_MAX_RETRIES).
      - Per-batch retry: any items that fail the entire item-retry budget
        are refed into a fresh batch up to BATCH_MAX_RETRIES times.
      - Progress log every batch flush w/ effective rate + ETA.

    Rationale: pre-refactor was a serial `for row in rows: embed_one(...)`
    loop + 50 ms `BATCH_SLEEP`, measured ~1.6 embed/s end-to-end. At
    parallel=10 the effective rate sits ~10 embed/s (target), 6× speedup,
    while staying under Gemini free-tier RPM (1500/min ≈ 25/s).

    Determinism: results are written back to SQLite keyed by `chunk_id`,
    so non-deterministic completion order from the thread pool does not
    change the final corpus → embedding mapping. Downstream retrieval
    (FTS5 BM25 + cosine + RRF k=60) is fully order-invariant.
    """
    con = open_db()
    rows = con.execute(
        "SELECT chunk_id, text FROM chunks WHERE embedding IS NULL"
    ).fetchall()
    if not rows:
        cnt = con.execute("SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL").fetchone()[0]
        print(f"[embed] all {cnt:,} chunks already embedded", file=sys.stderr)
        con.close()
        return cnt
    total = len(rows)
    print(
        f"[embed] embedding {total:,} session chunks via {GEMINI_MODEL} "
        f"(parallel={BATCH_PARALLEL}, item_retries={ITEM_MAX_RETRIES}, "
        f"batch_retries={BATCH_MAX_RETRIES})…",
        file=sys.stderr,
    )
    t0 = time.time()
    done = 0
    failed_total = 0
    # Chunk `rows` into BATCH_PARALLEL-sized slices. Each slice is dispatched
    # in parallel, then refed on failure up to BATCH_MAX_RETRIES times.
    for i in range(0, total, BATCH_PARALLEL):
        batch = rows[i : i + BATCH_PARALLEL]
        items: list[tuple[Any, str]] = [(cid, txt) for cid, txt in batch]
        succeeded: dict[Any, list[float]] = {}
        errors: dict[Any, str] = {}
        for batch_attempt in range(BATCH_MAX_RETRIES + 1):
            if not items:
                break
            partial_ok, partial_err = embed_batch_parallel(
                items, api_key, task_type="RETRIEVAL_DOCUMENT", parallel=BATCH_PARALLEL
            )
            succeeded.update(partial_ok)
            errors = partial_err  # last attempt's errors are the survivors
            if not partial_err:
                break
            # Refeed only the failed items for the next batch attempt.
            failed_keys = set(partial_err.keys())
            items = [(cid, txt) for cid, txt in items if cid in failed_keys]
            if batch_attempt < BATCH_MAX_RETRIES:
                delay = _backoff_seconds(batch_attempt)
                print(
                    f"[embed batch-retry {batch_attempt + 1}/{BATCH_MAX_RETRIES}] "
                    f"{len(items)} item(s) failed; refeeding after {delay:.2f}s",
                    file=sys.stderr,
                )
                time.sleep(delay)

        # Persist whatever succeeded for this batch (one transaction per batch).
        for chunk_id, vec in succeeded.items():
            con.execute(
                "UPDATE chunks SET embedding = ? WHERE chunk_id = ?",
                (pack_vec(vec), chunk_id),
            )
        con.commit()
        done += len(succeeded)
        failed_total += len(errors)

        if errors:
            # Log failed chunk_ids so the operator can re-run `embed` to retry —
            # leftover NULL embeddings will be picked up on the next invocation.
            for cid, msg in list(errors.items())[:3]:
                print(f"[embed] FAILED chunk_id={cid}: {msg}", file=sys.stderr)
            if len(errors) > 3:
                print(f"[embed] … plus {len(errors) - 3} more failures in this batch", file=sys.stderr)

        # Progress log every 10 batches (or at end). Cadence matches the
        # ~10-batch target so an operator watching tmux sees a tick ~every
        # 10 s at the target rate.
        batches_done = (i // BATCH_PARALLEL) + 1
        if batches_done % 10 == 0 or (i + BATCH_PARALLEL) >= total:
            elapsed = time.time() - t0
            rate = done / elapsed if elapsed > 0 else 0
            remaining = max(0, total - done - failed_total)
            eta = remaining / rate if rate else 0
            print(
                f"[Q2-eval] processed={done}/{total} failed={failed_total} "
                f"elapsed={elapsed:.0f}s rate={rate:.2f} embed/s eta={eta:.0f}s",
                file=sys.stderr,
            )

    con.close()
    elapsed = time.time() - t0
    rate = done / elapsed if elapsed > 0 else 0
    print(
        f"[embed] done {done}/{total} chunks in {elapsed:.1f}s "
        f"(rate={rate:.2f} embed/s, failed={failed_total})",
        file=sys.stderr,
    )
    if failed_total:
        print(
            f"[embed] {failed_total} chunks remain unembedded — re-run "
            f"`embed` to pick up survivors (NULL embeddings auto-refed).",
            file=sys.stderr,
        )
    return done


# ─────────────────────────────────────────────────────────────────────────────
# Stratified query selection (n=100, 6 base cats, _abs folded for sampling)
# ─────────────────────────────────────────────────────────────────────────────
def lcg_shuffle(items: list, seed: int) -> list:
    """Deterministic shuffle matching the seededShuffle LCG pattern from
    Q1 LoCoMo eval/run.ts. Pure-Python re-impl for cross-language reproducibility.

    Uses Numerical Recipes LCG: state = (state * 1664525 + 1013904223) & 0xffffffff.
    """
    out = items[:]
    state = seed & 0xFFFFFFFF
    for i in range(len(out) - 1, 0, -1):
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        j = state % (i + 1)
        out[i], out[j] = out[j], out[i]
    return out


def select_queries(corpus: list[dict]) -> list[dict]:
    """Stratified n=100 across 6 base categories (≈16-17 per cat), seed=42.

    `_abs` variants are folded into their parent category for sampling but
    tracked on output via `is_abstention`. If a category has fewer questions
    than the target, take all of them — never duplicate.
    """
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for q in corpus:
        qid = q.get("question_id")
        qtype = q.get("question_type", "")
        if not qid or not qtype:
            continue
        base, is_abs = derive_base_category(qtype, qid)
        gold_set = set(q.get("answer_session_ids") or [])
        if not gold_set:
            continue
        gold_chunk_ids = [f"{qid}::{sid}" for sid in gold_set]
        by_cat[base].append(
            {
                "category": base,
                "is_abstention": is_abs,
                "question_id": qid,
                "question_type": qtype,
                "question": q.get("question", ""),
                "gold_answer": str(q.get("answer", "")),
                "question_date": q.get("question_date", ""),
                "gold_chunk_ids": gold_chunk_ids,
            }
        )

    # Even split: 100 / 6 = 16 with 4 cats getting one extra (round-robin).
    per_cat_base = SUBSET_TOTAL // len(BASE_CATEGORIES)
    extras = SUBSET_TOTAL - per_cat_base * len(BASE_CATEGORIES)
    selected: list[dict] = []
    for idx, cat in enumerate(BASE_CATEGORIES):
        target = per_cat_base + (1 if idx < extras else 0)
        pool = by_cat.get(cat, [])
        if not pool:
            print(f"[queries] WARNING: category {cat!r} has 0 questions in corpus", file=sys.stderr)
            continue
        # LCG-shuffle with per-category seed offset for cross-cat independence
        cat_seed = (SEED + sum(ord(c) for c in cat)) & 0xFFFFFFFF
        shuffled = lcg_shuffle(pool, cat_seed)
        picked = shuffled[:target]
        selected.extend(picked)
        print(
            f"[queries] {cat}: target={target} available={len(pool)} picked={len(picked)}",
            file=sys.stderr,
        )

    print(
        f"[queries] total selected={len(selected)} (target={SUBSET_TOTAL})",
        file=sys.stderr,
    )
    return selected


# ─────────────────────────────────────────────────────────────────────────────
# Retrieval (FTS5 + dense, scoped to each question's haystack chunks)
# ─────────────────────────────────────────────────────────────────────────────
def fts5_escape(q: str) -> str:
    """Escape FTS5 special chars + tokenise to OR-join. Same as locomo_eval.py."""
    cleaned = re.sub(r"[^\w\s\-]", " ", q, flags=re.UNICODE)
    tokens = [t for t in cleaned.split() if len(t) >= 2]
    if not tokens:
        return '""'
    return " OR ".join(f'"{t}"' for t in tokens[:20])


def search_fts5(con: sqlite3.Connection, question_id: str, query: str, k: int) -> list[str]:
    """FTS5 BM25 over the haystack of one specific question."""
    fq = fts5_escape(query)
    try:
        rows = con.execute(
            "SELECT t.chunk_id FROM chunks t JOIN chunks_fts f ON f.rowid=t.rowid "
            "WHERE chunks_fts MATCH ? AND t.question_id = ? "
            "ORDER BY bm25(chunks_fts) LIMIT ?",
            (fq, question_id, k),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    return [r[0] for r in rows]


def load_question_dense(
    con: sqlite3.Connection, question_id: str
) -> tuple[list[str], np.ndarray]:
    rows = con.execute(
        "SELECT chunk_id, embedding FROM chunks "
        "WHERE question_id = ? AND embedding IS NOT NULL",
        (question_id,),
    ).fetchall()
    ids = [r[0] for r in rows]
    mat = (
        np.stack([unpack_vec(r[1]) for r in rows])
        if rows
        else np.zeros((0, EMBED_DIM), dtype=np.float32)
    )
    return ids, mat


def search_dense(
    query: str,
    api_key: str,
    ids: list[str],
    mat: np.ndarray,
    k: int,
) -> list[str]:
    """Single-query dense search (legacy helper).

    NOTE (2026-05-19): `evaluate()` no longer calls this — it pre-embeds all
    queries in parallel via `embed_batch_parallel` before the FTS5/RRF loop.
    Kept for ad-hoc debugging and external notebook callers that import the
    module directly. New code should use `embed_batch_parallel(...)` instead.
    """
    if not ids:
        return []
    qv = np.asarray(
        embed_one(query, api_key, task_type="RETRIEVAL_QUERY"), dtype=np.float32
    )
    n = float(np.linalg.norm(qv))
    if n > 0:
        qv = qv / n
    sims = mat @ qv
    k_eff = min(k, len(sims))
    if k_eff >= len(sims):
        order = np.argsort(-sims)
    else:
        idx = np.argpartition(-sims, k_eff)[:k_eff]
        order = idx[np.argsort(-sims[idx])]
    return [ids[i] for i in order[:k_eff]]


def rrf_fuse(rankings: list[list[str]], k: int = RRF_K, top: int = TOP_K_FINAL) -> list[str]:
    """Reciprocal-Rank Fusion. score(doc) = Σ 1/(k + rank_i+1)."""
    scores: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] += 1.0 / (k + rank + 1)
    fused = sorted(scores.items(), key=lambda kv: -kv[1])
    return [d for d, _ in fused[:top]]


# ─────────────────────────────────────────────────────────────────────────────
# Metrics (same definitions as Q1 LoCoMo for apples-to-apples)
# ─────────────────────────────────────────────────────────────────────────────
def ndcg_at_k(retrieved: list[str], gold: set[str], k: int = 10) -> float:
    dcg = 0.0
    for i, rid in enumerate(retrieved[:k]):
        if rid in gold:
            dcg += 1.0 / math.log2(i + 2)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(gold), k)))
    return dcg / idcg if idcg else 0.0


def mrr(retrieved: list[str], gold: set[str]) -> float:
    for i, rid in enumerate(retrieved):
        if rid in gold:
            return 1.0 / (i + 1)
    return 0.0


def recall_at_k(retrieved: list[str], gold: set[str], k: int = 10) -> float:
    if not gold:
        return 0.0
    hit = sum(1 for r in retrieved[:k] if r in gold)
    return hit / len(gold)


def precision_at_k(retrieved: list[str], gold: set[str], k: int = 5) -> float:
    if not retrieved:
        return 0.0
    hit = sum(1 for r in retrieved[:k] if r in gold)
    return hit / k


# ─────────────────────────────────────────────────────────────────────────────
# Eval driver
# ─────────────────────────────────────────────────────────────────────────────
def evaluate(queries: list[dict], api_key: str) -> dict[str, Any]:
    """Run hybrid retrieval over selected queries and compute metrics.

    Optimisation (2026-05-19, perf/q2-batch-parallel-embedding):
      Pre-embed all query strings in parallel (BATCH_PARALLEL workers) BEFORE
      entering the FTS5/RRF loop. Each query needs exactly one
      `embedContent(RETRIEVAL_QUERY)` call — batching all of them up front
      collapses n_queries × ~625 ms latency into ⌈n_queries / parallel⌉ ×
      ~625 ms. At n=100, parallel=10 that drops the query-embed leg from
      ~62 s serial to ~6 s parallel. Metrics are unchanged: same vectors,
      same FTS5 SQL, same RRF fusion. Order-invariant by `question_id`.
    """
    con = open_db()
    per_query: list[dict] = []
    t0 = time.time()

    # ── Pre-embed all queries in parallel ─────────────────────────────────
    t_qembed_0 = time.time()
    query_items: list[tuple[Any, str]] = [(q["question_id"], q["question"]) for q in queries]
    print(
        f"[eval] pre-embedding {len(query_items)} queries (parallel={BATCH_PARALLEL})…",
        file=sys.stderr,
    )
    query_vecs, query_errs = embed_batch_parallel(
        query_items, api_key, task_type="RETRIEVAL_QUERY", parallel=BATCH_PARALLEL
    )
    # Retry any query-embed failures with item-level backoff before the
    # eval loop starts — we don't want a partial run where queries silently
    # fall back to FTS-only retrieval (would skew nDCG@10 downward and
    # invalidate the headline).
    for retry in range(BATCH_MAX_RETRIES):
        if not query_errs:
            break
        retry_items = [(qid, q["question"]) for q in queries for qid in [q["question_id"]] if qid in query_errs]
        print(
            f"[eval] query-embed retry {retry + 1}/{BATCH_MAX_RETRIES} "
            f"for {len(retry_items)} failed queries",
            file=sys.stderr,
        )
        time.sleep(_backoff_seconds(retry))
        more_ok, more_err = embed_batch_parallel(
            retry_items, api_key, task_type="RETRIEVAL_QUERY", parallel=BATCH_PARALLEL
        )
        query_vecs.update(more_ok)
        query_errs = more_err
    if query_errs:
        print(
            f"[eval] WARNING: {len(query_errs)} query embeddings failed after "
            f"{BATCH_MAX_RETRIES} batch retries; those queries will use FTS-only retrieval",
            file=sys.stderr,
        )
        for qid, msg in list(query_errs.items())[:3]:
            print(f"[eval] FAILED query qid={qid}: {msg}", file=sys.stderr)
    t_qembed = time.time() - t_qembed_0
    q_rate = len(query_vecs) / t_qembed if t_qembed > 0 else 0
    print(
        f"[eval] query pre-embed done: {len(query_vecs)}/{len(queries)} in "
        f"{t_qembed:.1f}s (rate={q_rate:.2f} embed/s)",
        file=sys.stderr,
    )

    for i, q in enumerate(queries, 1):
        qid = q["question_id"]
        ids, mat = load_question_dense(con, qid)
        if not ids:
            print(
                f"[eval] WARNING qid={qid}: no embeddings; skipping dense branch",
                file=sys.stderr,
            )
        fts_top = search_fts5(con, qid, q["question"], k=TOP_K_FTS)
        # Use the pre-computed query vector when available; fall back to
        # FTS-only if pre-embed failed (rare, already logged above).
        if ids and qid in query_vecs:
            qv = np.asarray(query_vecs[qid], dtype=np.float32)
            qn = float(np.linalg.norm(qv))
            if qn > 0:
                qv = qv / qn
            sims = mat @ qv
            k_eff = min(TOP_K_DENSE, len(sims))
            if k_eff >= len(sims):
                order = np.argsort(-sims)
            else:
                idx = np.argpartition(-sims, k_eff)[:k_eff]
                order = idx[np.argsort(-sims[idx])]
            dense_top = [ids[idx_i] for idx_i in order[:k_eff]]
        else:
            dense_top = []
        fused = rrf_fuse([fts_top, dense_top], k=RRF_K, top=TOP_K_FINAL)
        gold = set(q["gold_chunk_ids"])
        per_query.append(
            {
                "question_id": qid,
                "query": q["question"][:120],
                "category": q["category"],
                "question_type": q["question_type"],
                "is_abstention": q["is_abstention"],
                "ndcg_at_10": ndcg_at_k(fused, gold, 10),
                "mrr": mrr(fused, gold),
                "recall_at_10": recall_at_k(fused, gold, 10),
                "precision_at_5": precision_at_k(fused, gold, 5),
                "n_gold": len(gold),
                "n_retrieved": len(fused),
                "n_haystack_chunks": len(ids) if ids else 0,
            }
        )
        if i % 10 == 0:
            print(f"[eval] {i}/{len(queries)} ({(time.time()-t0):.1f}s)", file=sys.stderr)
    con.close()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in per_query) + "\n"
    )

    def mean(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    aggregate = {
        "system": "hybrid_fts5_gemini_rrf_longmemeval",
        "dataset": HF_REPO,
        "dataset_revision": HF_REVISION,
        "split": SPLIT,
        "seed": SEED,
        "n_queries": len(per_query),
        "rrf_k": RRF_K,
        "embedding_model": GEMINI_MODEL,
        "embedding_dim": EMBED_DIM,
        "top_k_fts": TOP_K_FTS,
        "top_k_dense": TOP_K_DENSE,
        "top_k_final": TOP_K_FINAL,
        "ndcg_at_10": mean([r["ndcg_at_10"] for r in per_query]),
        "mrr": mean([r["mrr"] for r in per_query]),
        "recall_at_10": mean([r["recall_at_10"] for r in per_query]),
        "precision_at_5": mean([r["precision_at_5"] for r in per_query]),
    }

    # Per-category (base) breakdown
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for r in per_query:
        by_cat[r["category"]].append(r)
    per_category: list[dict] = []
    for cat in BASE_CATEGORIES:
        rs = by_cat.get(cat, [])
        if not rs:
            continue
        per_category.append(
            {
                "category": cat,
                "n": len(rs),
                "ndcg_at_10": mean([r["ndcg_at_10"] for r in rs]),
                "mrr": mean([r["mrr"] for r in rs]),
                "recall_at_10": mean([r["recall_at_10"] for r in rs]),
                "precision_at_5": mean([r["precision_at_5"] for r in rs]),
            }
        )

    # Abstention vs answer split (orthogonal to category)
    abs_rs = [r for r in per_query if r["is_abstention"]]
    ans_rs = [r for r in per_query if not r["is_abstention"]]
    by_variant = [
        {
            "variant": "answer",
            "n": len(ans_rs),
            "ndcg_at_10": mean([r["ndcg_at_10"] for r in ans_rs]),
            "mrr": mean([r["mrr"] for r in ans_rs]),
            "recall_at_10": mean([r["recall_at_10"] for r in ans_rs]),
        },
        {
            "variant": "abstention",
            "n": len(abs_rs),
            "ndcg_at_10": mean([r["ndcg_at_10"] for r in abs_rs]),
            "mrr": mean([r["mrr"] for r in abs_rs]),
            "recall_at_10": mean([r["recall_at_10"] for r in abs_rs]),
        },
    ]
    return {
        "aggregate": aggregate,
        "per_category": per_category,
        "per_variant": by_variant,
        "per_query": per_query,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Summary writer (markdown) — caveats up top, methodology at bottom
# ─────────────────────────────────────────────────────────────────────────────
def ci95(xs: list[float]) -> tuple[float, float, float]:
    if not xs:
        return 0.0, 0.0, 0.0
    m = statistics.fmean(xs)
    if len(xs) < 2:
        return m, m, m
    sd = statistics.stdev(xs)
    se = sd / math.sqrt(len(xs))
    h = 1.96 * se
    return m, m - h, m + h


def write_summary(results: dict, dry_run_only: bool) -> None:
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    agg = results["aggregate"]
    per_cat = results["per_category"]
    per_var = results["per_variant"]
    per_q = results["per_query"]
    n_q = len(per_q)

    h_m, h_lo, h_hi = ci95([r["ndcg_at_10"] for r in per_q])
    mrr_m, mrr_lo, mrr_hi = ci95([r["mrr"] for r in per_q])

    lines: list[str] = []
    lines.append("# Q2 LongMemEval — Hybrid (FTS5 + Gemini + RRF) — Python self-contained\n")
    lines.append(f"**Run date:** {time.strftime('%Y-%m-%d %H:%M %Z')}")
    lines.append(f"**Dataset:** `{HF_REPO}` ({LICENSE})")
    lines.append(f"**Revision:** `{HF_REVISION[:10]}...`")
    lines.append(f"**Split:** `oracle` (evidence-only, smallest)")
    lines.append(f"**Subset:** stratified n={n_q} over {len(BASE_CATEGORIES)} base categories, seed={SEED}")
    lines.append(f"**Embedding model:** `{GEMINI_MODEL}` ({EMBED_DIM}d, L2-normed)")
    lines.append(f"**Fusion:** RRF with k={RRF_K}, top-{TOP_K_FINAL} after fusion")
    lines.append(f"**Per-branch candidates:** FTS5 top-{TOP_K_FTS}, dense top-{TOP_K_DENSE}\n")

    lines.append("## ⚠️ Caveats (read before citing)\n")
    lines.append(
        "1. **Python re-implementation, NOT production nox-mem code path.** "
        "This script reproduces the *architectural shape* of memoria-nox's "
        "hybrid retrieval (FTS5 BM25 + Gemini 3072d dense + RRF k=60). It "
        "does NOT execute nox-mem's TypeScript pipeline. Production-path "
        "validation requires running `npx tsx eval/longmemeval/run.ts` on "
        "the VPS — separate work item per Q2 spec."
    )
    lines.append(
        "2. **Retrieval-only metric, not task-accuracy.** The Q2 LongMemEval "
        "harness in `eval/longmemeval/` is designed for end-to-end task-"
        "accuracy via LLM-as-judge (paper standard). This script measures "
        "the *retrieval substrate* only (nDCG/MRR/Recall/Precision against "
        "`answer_session_ids` as binary relevance). Use it to validate the "
        "retrieval pipeline shape; use `run.ts` + `score.ts` for headline "
        "task-accuracy."
    )
    lines.append(
        "3. **Gold relevance is session-level (`answer_session_ids`), not "
        "turn-level.** A retrieved chunk is correct iff its `session_id` "
        "appears in `answer_session_ids`. This matches the paper's gold "
        "encoding and the harness D4 decision (per-session ingestion)."
    )
    lines.append(
        "4. **Per-question scoping.** Each question has its own isolated "
        "haystack — retrieval is scoped to that question's `haystack_session_ids` "
        "only. This is the LongMemEval-correct setup (the paper measures "
        "needle-in-haystack within the bundled history), and differs from "
        "Q1 LoCoMo where the corpus is shared across questions of the same "
        "conversation."
    )
    lines.append(
        f"5. **Sample n={n_q}, not full 500 questions.** The oracle split has "
        f"~500 questions across {len(BASE_CATEGORIES)} categories + abstention "
        f"variants. n=100 is the same stratification target as Q1 LoCoMo for "
        f"cross-benchmark cost/time parity. Multi-seed CI is a follow-up.\n"
    )

    if dry_run_only:
        lines.append("> **⚠️ This summary was generated against the local "
                     "`eval/longmemeval/dry-run-sample.json` fallback (HF "
                     "dataset unreachable). The dry-run sample contains "
                     "metadata only — no `haystack_sessions` text — so "
                     "retrieval numbers will be all zeros. Re-run with HF "
                     "access for real numbers.**\n")

    lines.append("## Aggregate metrics\n")
    lines.append("| Metric | Value | 95% CI |")
    lines.append("|---|---|---|")
    lines.append(f"| nDCG@10 | **{agg['ndcg_at_10']:.4f}** | [{h_lo:.4f}, {h_hi:.4f}] |")
    lines.append(f"| MRR | **{agg['mrr']:.4f}** | [{mrr_lo:.4f}, {mrr_hi:.4f}] |")
    lines.append(f"| Recall@10 | **{agg['recall_at_10']:.4f}** | — |")
    lines.append(f"| Precision@5 | **{agg['precision_at_5']:.4f}** | — |")
    lines.append("")

    if per_cat:
        lines.append("## Per-category breakdown\n")
        lines.append("| Category | n | nDCG@10 | MRR | Recall@10 | Precision@5 |")
        lines.append("|---|---|---|---|---|---|")
        for c in per_cat:
            lines.append(
                f"| {c['category']} | {c['n']} | "
                f"{c['ndcg_at_10']:.4f} | {c['mrr']:.4f} | "
                f"{c['recall_at_10']:.4f} | {c['precision_at_5']:.4f} |"
            )
        lines.append("")

    if per_var:
        lines.append("## Answer vs Abstention split\n")
        lines.append("| Variant | n | nDCG@10 | MRR | Recall@10 |")
        lines.append("|---|---|---|---|---|")
        for v in per_var:
            lines.append(
                f"| {v['variant']} | {v['n']} | "
                f"{v['ndcg_at_10']:.4f} | {v['mrr']:.4f} | {v['recall_at_10']:.4f} |"
            )
        lines.append("")
        lines.append(
            "Note: for `_abs` (abstention) questions the gold is still a "
            "session id, so retrieval can still match. The semantic "
            "interpretation differs (the *generator* should refuse to answer "
            "even when the right session is retrieved), but for a retrieval-"
            "only metric this orthogonal split is informational rather than "
            "directly comparable.\n"
        )

    lines.append("## Methodology\n")
    lines.append(
        "**FTS5 branch:** SQLite virtual table with `unicode61 remove_diacritics 2` "
        f"tokenizer, BM25 ranking, OR-joined phrase tokens, top-{TOP_K_FTS} candidates. "
        "Scoped to one question's haystack via `WHERE question_id = ?`.\n"
    )
    lines.append(
        f"**Dense branch:** Gemini `{GEMINI_MODEL}` with `outputDimensionality={EMBED_DIM}`. "
        "Document embeddings use `taskType=RETRIEVAL_DOCUMENT`; query embeddings "
        f"use `RETRIEVAL_QUERY`. Embeddings L2-normed at write time so cosine = dot product. Top-{TOP_K_DENSE} by cosine.\n"
    )
    lines.append(
        f"**Fusion:** Reciprocal Rank Fusion (Cormack et al., 2009) with k={RRF_K}. "
        f"score(doc) = Σ 1/(k + rank_i + 1) across both rankings. "
        f"Top-{TOP_K_FINAL} after fusion → metrics.\n"
    )
    lines.append(
        "**Sampling:** stratified by base category (6 levels), `_abs` variants "
        "folded into their parent for sampling and tracked separately on output. "
        f"Per-category LCG shuffle (Numerical Recipes constants) with seed "
        f"`SEED + sum(ord(c) for c in cat)` for cross-category independence. "
        "Target n=100 distributed evenly (16-17 per cat).\n"
    )
    lines.append(
        f"**Gold encoding:** chunk `c` is relevant iff "
        f"`c.session_id ∈ answer_session_ids` for that question. Multiple gold "
        f"sessions per question are typical for multi-session and "
        f"temporal-reasoning categories.\n"
    )
    lines.append(f"**Citation:** {CITATION}\n")

    lines.append("## Reproducibility\n")
    lines.append(
        "```bash\n"
        "export GEMINI_API_KEY=AIza...\n"
        "cd paper/publication/baselines\n"
        "python3 longmemeval_hybrid_eval.py full\n"
        "```\n"
    )
    lines.append(
        "Output JSONL (one row per question):\n"
        f"`{RESULTS.relative_to(RESULTS_DIR.parent.parent)}`\n"
    )

    SUMMARY.write_text("\n".join(lines))
    print(f"[summary] wrote {SUMMARY}", file=sys.stderr)


# ─────────────────────────────────────────────────────────────────────────────
# Pretty stdout
# ─────────────────────────────────────────────────────────────────────────────
def print_table(results: dict) -> None:
    agg = results["aggregate"]
    print("\n" + "=" * 72)
    print(f"LongMemEval n={agg['n_queries']} — Hybrid (FTS5 + Gemini {EMBED_DIM}d + RRF k={RRF_K})")
    print("=" * 72)
    print(f"  nDCG@10      = {agg['ndcg_at_10']:.4f}")
    print(f"  MRR          = {agg['mrr']:.4f}")
    print(f"  Recall@10    = {agg['recall_at_10']:.4f}")
    print(f"  Precision@5  = {agg['precision_at_5']:.4f}")
    print("-" * 72)
    print(f"{'Category':<28}{'n':>5}{'nDCG@10':>12}{'MRR':>10}{'R@10':>10}")
    for c in results["per_category"]:
        print(
            f"{c['category']:<28}{c['n']:>5}{c['ndcg_at_10']:>12.4f}"
            f"{c['mrr']:>10.4f}{c['recall_at_10']:>10.4f}"
        )
    print("=" * 72 + "\n")


def main() -> int:
    p = argparse.ArgumentParser(
        description="LongMemEval hybrid retrieval eval (FTS5 + Gemini + RRF)."
    )
    p.add_argument("cmd", choices=["download", "index", "embed", "eval", "full"])
    p.add_argument(
        "--split",
        choices=VALID_SPLITS,
        default=DEFAULT_SPLIT,
        help=(
            "Which LongMemEval split to evaluate. oracle (default) = evidence-only, "
            "smallest, cheap plumbing — but contains ~0 distractors so nDCG/MRR/R@10 "
            "saturate near 1.0; s_cleaned = paper headline (~115k-token haystacks, "
            "~40 sessions per question) — produces meaningful comparison numbers but "
            "costs ~$0.05-0.20 in embedding calls + ~10-15 min wall clock; "
            "m_cleaned = frontier track (~500 sessions per question, deferred)."
        ),
    )
    args = p.parse_args()
    configure_split(args.split)

    dry_run_only = False

    if args.cmd in ("download", "full"):
        download()
    if args.cmd in ("index", "full"):
        corpus = load_corpus()
        dry_run_only = any(q.get("_dry_run_only") for q in corpus)
        build_index(corpus)
    if args.cmd in ("embed", "full"):
        api_key = check_api_key()
        if not DB_PATH.exists():
            print("[fatal] DB missing — run `index` first", file=sys.stderr)
            return 4
        embed_corpus(api_key)
    if args.cmd in ("eval", "full"):
        api_key = check_api_key()
        corpus = load_corpus()
        dry_run_only = any(q.get("_dry_run_only") for q in corpus)
        queries = select_queries(corpus)
        if not queries:
            print(
                "[eval] FATAL: no queries selected. The dry-run-sample.json fallback "
                "lacks `answer_session_ids` on records → cannot evaluate. Re-run "
                "with HF access to fetch the full oracle split.",
                file=sys.stderr,
            )
            # Still write a summary with caveat so the artifact exists for the PR.
            empty_results = {
                "aggregate": {
                    "system": "hybrid_fts5_gemini_rrf_longmemeval",
                    "dataset": HF_REPO,
                    "dataset_revision": HF_REVISION,
                    "split": SPLIT,
                    "seed": SEED,
                    "n_queries": 0,
                    "rrf_k": RRF_K,
                    "embedding_model": GEMINI_MODEL,
                    "embedding_dim": EMBED_DIM,
                    "top_k_fts": TOP_K_FTS,
                    "top_k_dense": TOP_K_DENSE,
                    "top_k_final": TOP_K_FINAL,
                    "ndcg_at_10": 0.0,
                    "mrr": 0.0,
                    "recall_at_10": 0.0,
                    "precision_at_5": 0.0,
                },
                "per_category": [],
                "per_variant": [],
                "per_query": [],
            }
            RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            RESULTS.write_text("")
            write_summary(empty_results, dry_run_only=True)
            print(json.dumps(empty_results["aggregate"], indent=2, ensure_ascii=False))
            return 0
        results = evaluate(queries, api_key)
        print(json.dumps(
            {"aggregate": results["aggregate"],
             "per_category": results["per_category"],
             "per_variant": results["per_variant"]},
            indent=2,
            ensure_ascii=False,
        ))
        print_table(results)
        write_summary(results, dry_run_only=dry_run_only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
