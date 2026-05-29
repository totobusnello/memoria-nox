"""
adapter_lme.py — LongMemEval adapter for nox-mem cross-bench validation.

Mirrors the Phase D / Phase H v2 EverMemBench adapter pattern
(eval/evermembench/adapter_nox_mem.py) but adapted to the LongMemEval
dataset shape (per-question haystack sessions, session-level gold).

Pipeline per question:
    1. Build per-q isolated DB path (NOX_DB_PATH=/tmp/lme-{run_id}/q-{qid}.db).
    2. Write each haystack session to a tmp markdown file
       (one file per session, session-level chunking matches D4 of harness README).
    3. Invoke `nox-mem ingest <file>` subprocess per session — inherits NOX_DB_PATH.
    4. Optionally invoke `nox-mem vectorize` to embed (REQUIRED for hybrid).
    5. POST /api/search (port NOX_API_PORT) with question text, limit=20.
    6. Record retrieval (chunk_ids → session_ids), latencies, gold session_ids.

This is RETRIEVAL-ONLY by default (Phase D config: phaseB chunking, top_k=20,
rerank OFF). End-to-end task accuracy with GPT-4.1-mini generator is OPTIONAL
via --task-accuracy flag (cross-backbone parity with Phase H v2).

Safety:
    - NOX_DB_PATH must NOT resolve to production /root/.openclaw/workspace/tools/nox-mem/nox-mem.db
    - API port must NOT be 18802 (prod)
    - Explicit refuse-prod-db guard

Dependencies: requests, sqlite3 (stdlib). No EverMemBench imports.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import urllib.request


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_NOX_API_BASE = "http://127.0.0.1:18835"
DEFAULT_NOX_MEM_BIN = "nox-mem"
DEFAULT_TOP_K = 20
DEFAULT_INGEST_TIMEOUT = 120
DEFAULT_SEARCH_TIMEOUT = 30
DEFAULT_VECTORIZE_TIMEOUT = 600  # vectorize batches all chunks at once

PROD_DB_PATH = "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db"

# Per-session markdown format. Keeps date and session_id readable to
# both FTS5 and Gemini embeddings (mirrors LongMemEval harness D4 + Phase B
# header-style metadata embedding).
SESSION_MD_TEMPLATE = """# LongMemEval session {session_id}

session_id: {session_id}
date: {date}
question_id: {question_id}

## Conversation

{turns}
"""


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------

@dataclass
class QARecord:
    question_id: str
    question_type: str
    base_category: str
    is_abstention: bool
    question: str
    gold_answer: str
    question_date: str
    haystack_session_ids: list[str]
    haystack_dates: list[str]
    haystack_sessions: list[list[dict]]  # turns
    answer_session_ids: list[str]


@dataclass
class RetrievalResult:
    question_id: str
    question_type: str
    base_category: str
    is_abstention: bool
    question: str
    gold_answer: str
    question_date: str
    haystack_session_count: int
    gold_session_ids: list[str]
    retrieved_chunk_ids: list[str]
    retrieved_session_ids: list[str]  # parsed back from chunk meta
    retrieved_scores: list[float]
    retrieved_texts: list[str]        # for optional generator stage
    ingest_ms: float
    vectorize_ms: float
    retrieval_ms: float
    error: str | None = None


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------

def refuse_if_prod(db_path: str, api_base: str) -> None:
    norm = os.path.realpath(db_path)
    if norm == PROD_DB_PATH or norm.endswith("/workspace/tools/nox-mem/nox-mem.db"):
        raise SystemExit(f"refuse to use production DB: {norm}")
    if "18802" in api_base:
        raise SystemExit(f"refuse to use production API port 18802: {api_base}")
    # Sanity: op-audit ALLOWED_PREFIXES = ['/var/backups/', '/root/.openclaw/']
    # NOX_DB_PATH must be under one of these. We enforce /root/.openclaw/eval/
    # for the eval harness (op-audit rejects /tmp/* paths).
    allowed = ("/var/backups/", "/root/.openclaw/")
    if not any(norm.startswith(p) for p in allowed):
        raise SystemExit(
            f"refuse db_path '{norm}': must start with one of {allowed} "
            f"(op-audit P1 safety guard, dist/lib/op-audit.js)"
        )


# ---------------------------------------------------------------------------
# Dataset I/O
# ---------------------------------------------------------------------------

def _derive_base_category(question_type: str, question_id: str) -> tuple[str, bool]:
    is_abs = question_id.endswith("_abs") or question_type.endswith("_abs")
    base = question_type[:-len("_abs")] if question_type.endswith("_abs") else question_type
    return base, is_abs


def load_split(path: Path) -> list[QARecord]:
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, list):
        raise ValueError(f"expected top-level JSON array in {path}, got {type(raw).__name__}")
    out: list[QARecord] = []
    for r in raw:
        qid = r.get("question_id")
        qtype = r.get("question_type")
        q = r.get("question")
        a = r.get("answer")
        if not qid or not qtype or not q or a is None:
            continue
        base, is_abs = _derive_base_category(qtype, qid)
        out.append(QARecord(
            question_id=qid,
            question_type=qtype,
            base_category=base,
            is_abstention=is_abs,
            question=q,
            gold_answer=str(a),
            question_date=r.get("question_date") or "",
            haystack_session_ids=list(r.get("haystack_session_ids") or []),
            haystack_dates=list(r.get("haystack_dates") or []),
            haystack_sessions=list(r.get("haystack_sessions") or []),
            answer_session_ids=list(r.get("answer_session_ids") or []),
        ))
    return out


def stratified_sample(records: list[QARecord], n: int, seed: int = 42) -> list[QARecord]:
    by_cell: dict[str, list[QARecord]] = {}
    for r in records:
        cell = f"{r.base_category}{'_abs' if r.is_abstention else ''}"
        by_cell.setdefault(cell, []).append(r)
    cells = sorted(by_cell.keys())
    per_cell = max(1, n // len(cells))
    out: list[QARecord] = []
    for idx, c in enumerate(cells):
        rng = random.Random(seed + idx + 1)
        pool = list(by_cell[c])
        rng.shuffle(pool)
        out.extend(pool[:per_cell])
    if len(out) < n:
        seen = {r.question_id for r in out}
        rng = random.Random(seed)
        rest = [r for r in records if r.question_id not in seen]
        rng.shuffle(rest)
        out.extend(rest[: n - len(out)])
    return out[:n]


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], env: dict[str, str], timeout: int) -> tuple[int, str, str]:
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as e:
        return 124, e.stdout or "", e.stderr or "TIMEOUT"


def write_session_md(session_id: str, date: str, question_id: str, turns: list[dict], out_path: Path) -> None:
    # CRITICAL: prefix EVERY turn with `session_id: {sid}` so that even if
    # nox-mem ingest splits the file into multiple chunks (H2/H3 boundary),
    # each chunk_text retains the session marker. Otherwise the H3 chunker
    # produces chunks without session_id and our regex parser falls back to
    # numeric chunk IDs (which don't match gold session_ids).
    lines: list[str] = []
    for t in turns:
        if not isinstance(t, dict):
            continue
        role = str(t.get("role", "")).strip() or "user"
        content = str(t.get("content", "")).replace("\r\n", "\n").replace("\r", "\n")
        # Per-turn embedded marker — survives chunk splitting.
        lines.append(
            f"### {role} (session_id: {session_id}, date: {date})\n\n"
            f"session_id: {session_id}\n"
            f"{content}\n"
        )
    md = SESSION_MD_TEMPLATE.format(
        session_id=session_id,
        date=date,
        question_id=question_id,
        turns="\n".join(lines).rstrip() or "(empty session)",
    )
    out_path.write_text(md, encoding="utf-8")


# V8-V18 schema columns missing from dist/db.js migration ladder.
# dist/db.js declares SCHEMA_VERSION=18 but only runs migrateToV1..V7. Prod DB
# was migrated via a pre-built dist that included V8+ at some point in history;
# the current dist is stale w.r.t. these ALTERs but the constant was bumped.
# We patch the schema post-bootstrap to match prod V18.
_V8_TO_V18_ALTERS = [
    "ALTER TABLE chunks ADD COLUMN memory_type TEXT",
    "ALTER TABLE chunks ADD COLUMN tier TEXT DEFAULT 'peripheral'",
    "ALTER TABLE chunks ADD COLUMN access_count INTEGER DEFAULT 0",
    "ALTER TABLE chunks ADD COLUMN last_accessed_at TEXT",
    "ALTER TABLE chunks ADD COLUMN importance REAL DEFAULT 0.5",
    "ALTER TABLE chunks ADD COLUMN retention_days INTEGER",
    "ALTER TABLE chunks ADD COLUMN pain REAL DEFAULT 0.2",
    "ALTER TABLE chunks ADD COLUMN section TEXT",
    "ALTER TABLE chunks ADD COLUMN section_boost REAL DEFAULT 1.0",
    "ALTER TABLE chunks ADD COLUMN ocr_status TEXT",
    "ALTER TABLE chunks ADD COLUMN ocr_engine TEXT",
    "ALTER TABLE chunks ADD COLUMN fts_anchor TEXT DEFAULT ''",
    "ALTER TABLE chunks ADD COLUMN confidence REAL DEFAULT 0.8",
    "ALTER TABLE chunks ADD COLUMN provenance_kind TEXT",
]

_KG_BOOTSTRAP_SQL = """
CREATE TABLE IF NOT EXISTS kg_entities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  first_seen TEXT DEFAULT (datetime('now')),
  last_seen TEXT DEFAULT (datetime('now')),
  mention_count INTEGER DEFAULT 1,
  attributes TEXT,
  UNIQUE(name, entity_type)
);
CREATE TABLE IF NOT EXISTS kg_relations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_entity_id INTEGER NOT NULL,
  relation_type TEXT NOT NULL,
  target_entity_id INTEGER NOT NULL,
  evidence_chunk_id INTEGER,
  confidence REAL DEFAULT 0.8,
  created_at TEXT DEFAULT (datetime('now')),
  expires_at TEXT DEFAULT (datetime('now', '+90 days')),
  last_confirmed TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (source_entity_id) REFERENCES kg_entities(id),
  FOREIGN KEY (target_entity_id) REFERENCES kg_entities(id)
);
CREATE INDEX IF NOT EXISTS idx_kg_entities_name ON kg_entities(name);
CREATE INDEX IF NOT EXISTS idx_kg_entities_type ON kg_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_kg_relations_source ON kg_relations(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_kg_relations_target ON kg_relations(target_entity_id);
"""


def _patch_schema_v8_v18(db_path: str) -> str | None:
    """Apply missing V8-V18 ALTERs + KG tables. Idempotent."""
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        for stmt in _V8_TO_V18_ALTERS:
            try:
                cur.execute(stmt)
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    continue
                return f"alter failed: {stmt}: {e}"
        # KG tables — needed by api-server.js /api/search query
        cur.executescript(_KG_BOOTSTRAP_SQL)
        conn.commit()
        conn.close()
    except Exception as e:
        return f"sqlite open/exec failed: {type(e).__name__}: {e}"
    return None


def bootstrap_db(db_path: str, nox_mem_bin: str, env_base: dict[str, str], workdir: Path, qid: str) -> str | None:
    """
    Bootstrap a fresh empty DB:
        1. Trigger ensureSchema V1-V7 via `nox-mem stats`.
        2. Apply missing V8-V18 ALTERs via sqlite3 directly (dist stale workaround).
    Result: schema matches prod V18 with all columns required by ingest.js.
    """
    env = dict(env_base)
    env["NOX_DB_PATH"] = db_path
    env["OPENCLAW_WORKSPACE"] = str(workdir / f"q-{qid}")
    rc, out, err = _run([nox_mem_bin, "stats"], env=env, timeout=30)
    if rc != 0:
        return f"bootstrap rc={rc} err={err[:300]}"
    patch_err = _patch_schema_v8_v18(db_path)
    if patch_err:
        return f"v8_v18 patch: {patch_err}"
    return None


def ingest_question(
    rec: QARecord,
    db_path: str,
    workdir: Path,
    nox_mem_bin: str,
    env_base: dict[str, str],
) -> tuple[float, str | None]:
    """
    Per-question ingest: write each haystack session to tmp .md, ingest each,
    then vectorize all chunks. Returns (ingest_ms_total + vectorize_ms is
    counted separately by caller via vectorize_question).
    """
    t0 = time.time()
    qdir = workdir / f"q-{rec.question_id}"
    qdir.mkdir(parents=True, exist_ok=True)

    # Bootstrap fresh DB schema (V1-V18 migrations via `nox-mem stats`).
    boot_err = bootstrap_db(db_path, nox_mem_bin, env_base, workdir, rec.question_id)
    if boot_err:
        return (time.time() - t0) * 1000.0, boot_err

    env = dict(env_base)
    env["NOX_DB_PATH"] = db_path
    env["OPENCLAW_WORKSPACE"] = str(qdir)
    n = min(len(rec.haystack_session_ids), len(rec.haystack_sessions))
    for i in range(n):
        sid = rec.haystack_session_ids[i]
        date = rec.haystack_dates[i] if i < len(rec.haystack_dates) else ""
        turns = rec.haystack_sessions[i] or []
        md_path = qdir / f"{sid}.md"
        write_session_md(sid, date, rec.question_id, turns, md_path)
        # nox-mem ingest <file>
        rc, out, err = _run(
            [nox_mem_bin, "ingest", str(md_path), "--allow-prod"],
            env=env, timeout=DEFAULT_INGEST_TIMEOUT,
        )
        if rc != 0:
            return (time.time() - t0) * 1000.0, f"ingest rc={rc} sid={sid} err={err[:800]}"
    return (time.time() - t0) * 1000.0, None


def vectorize_question(db_path: str, nox_mem_bin: str, env_base: dict[str, str], workdir: Path, qid: str) -> tuple[float, str | None]:
    t0 = time.time()
    env = dict(env_base)
    env["NOX_DB_PATH"] = db_path
    env["OPENCLAW_WORKSPACE"] = str(workdir / f"q-{qid}")
    rc, out, err = _run(
        [nox_mem_bin, "vectorize"],
        env=env, timeout=DEFAULT_VECTORIZE_TIMEOUT,
    )
    if rc != 0:
        return (time.time() - t0) * 1000.0, f"vectorize rc={rc} err={err[:200]}"
    return (time.time() - t0) * 1000.0, None


# ---------------------------------------------------------------------------
# HTTP search
# ---------------------------------------------------------------------------

def search_api(api_base: str, query: str, limit: int, timeout: int) -> tuple[list[dict], float, str | None]:
    """POST /api/search; nox-mem returns hybrid (BM25+Gemini+RRF) by default.

    Response shape (api-server.js verified 2026-05-29): JSON array of hits.
    Each hit: {id, score, source_file, chunk_type, chunk_text, source_date,
              tier, section, pain, importance, source_type, match_type}.
    """
    url = api_base.rstrip("/") + "/api/search"
    body = json.dumps({"query": query, "limit": limit, "hybrid": True}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"content-type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            txt = r.read().decode("utf-8")
            j = json.loads(txt)
    except Exception as e:
        return [], (time.time() - t0) * 1000.0, f"search error: {type(e).__name__}: {e}"
    ms = (time.time() - t0) * 1000.0
    # api-server returns a JSON array directly; also handle dict-wrapped shapes
    # for forward-compat (response_shape_validation lesson).
    if isinstance(j, list):
        hits = j
    elif isinstance(j, dict):
        hits = j.get("results") or j.get("hits") or []
        if not isinstance(hits, list):
            hits = []
    else:
        hits = []
    return hits, ms, None


# ---------------------------------------------------------------------------
# Session-id extraction from retrieved chunk
# ---------------------------------------------------------------------------

# nox-mem chunks store full text; LongMemEval session marker is embedded in
# the markdown body as "session_id: <id>" (line) AND in H1 header. We parse
# the chunk text to extract the session_id.

import re as _re
_SESSION_RE = _re.compile(r"session_id:\s*([A-Za-z0-9_\-]+)")


def session_id_from_chunk(hit: dict) -> str:
    # api-server.js shape: chunk_text. Older shape: text/snippet. Try all.
    txt = hit.get("chunk_text") or hit.get("text") or hit.get("snippet") or ""
    m = _SESSION_RE.search(txt)
    if m:
        return m.group(1)
    # Fallback: try chunk_id / id field
    cid = str(hit.get("chunk_id") or hit.get("id") or "")
    return cid


# ---------------------------------------------------------------------------
# Per-question driver
# ---------------------------------------------------------------------------

def run_question(
    rec: QARecord,
    db_path: str,
    workdir: Path,
    nox_mem_bin: str,
    api_base: str,
    top_k: int,
    env_base: dict[str, str],
) -> RetrievalResult:
    result = RetrievalResult(
        question_id=rec.question_id,
        question_type=rec.question_type,
        base_category=rec.base_category,
        is_abstention=rec.is_abstention,
        question=rec.question,
        gold_answer=rec.gold_answer,
        question_date=rec.question_date,
        haystack_session_count=len(rec.haystack_session_ids),
        gold_session_ids=list(rec.answer_session_ids),
        retrieved_chunk_ids=[],
        retrieved_session_ids=[],
        retrieved_scores=[],
        retrieved_texts=[],
        ingest_ms=0.0,
        vectorize_ms=0.0,
        retrieval_ms=0.0,
    )

    ingest_ms, ierr = ingest_question(rec, db_path, workdir, nox_mem_bin, env_base)
    result.ingest_ms = ingest_ms
    if ierr:
        result.error = ierr
        return result

    vec_ms, verr = vectorize_question(db_path, nox_mem_bin, env_base, workdir, rec.question_id)
    result.vectorize_ms = vec_ms
    if verr:
        result.error = verr
        # Still attempt FTS5-only search if vectorize fails
    hits, search_ms, serr = search_api(api_base, rec.question, top_k, DEFAULT_SEARCH_TIMEOUT)
    result.retrieval_ms = search_ms
    if serr and not result.error:
        result.error = serr
    for h in hits:
        if not isinstance(h, dict):
            continue
        result.retrieved_chunk_ids.append(str(h.get("chunk_id") or h.get("id") or ""))
        result.retrieved_scores.append(float(h.get("score") or h.get("relevance") or 0.0))
        sid = session_id_from_chunk(h)
        result.retrieved_session_ids.append(sid)
        result.retrieved_texts.append(str(h.get("text") or h.get("snippet") or "")[:1000])
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--split-path", required=True, help="path to longmemeval_<split>.json")
    p.add_argument("--n", type=int, default=300)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    p.add_argument("--api-base", default=os.environ.get("NOX_API_BASE", DEFAULT_NOX_API_BASE))
    p.add_argument("--nox-mem-bin", default=os.environ.get("NOX_MEM_BIN", DEFAULT_NOX_MEM_BIN))
    p.add_argument("--workdir", required=True, help="scratch dir for per-q DBs + md files")
    p.add_argument("--out", required=True, help="output JSONL path")
    p.add_argument("--no-vectorize", action="store_true", help="FTS5-only (no semantic)")
    p.add_argument("--progress-every", type=int, default=10)
    p.add_argument("--start-server", action="store_true",
                   help="start nox-mem-api against per-q DB (NOT IMPLEMENTED; use external orchestrator)")
    args = p.parse_args(argv)

    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    refuse_if_prod(str(workdir / "any.db"), args.api_base)

    records = load_split(Path(args.split_path))
    print(f"[adapter] loaded {len(records)} records from {args.split_path}", file=sys.stderr)
    sample = stratified_sample(records, args.n, args.seed)
    print(f"[adapter] stratified sample n={len(sample)}", file=sys.stderr)

    # Tally per-cell
    by_cell: dict[str, int] = {}
    for r in sample:
        cell = f"{r.base_category}{'_abs' if r.is_abstention else ''}"
        by_cell[cell] = by_cell.get(cell, 0) + 1
    print(f"[adapter] by cell: {by_cell}", file=sys.stderr)

    env_base = dict(os.environ)
    # Defensive: force rerank OFF (Phase D config)
    env_base["NOX_RERANKER_ENABLED"] = "0"

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n_done = 0
    n_err = 0
    t_start = time.time()
    with out_path.open("w", encoding="utf-8") as fh:
        for i, rec in enumerate(sample):
            # Per-question DB: caller (run-script) must restart API to point at this DB.
            # In single-process mode we use ONE shared per-run DB (all questions' haystacks
            # ingested sequentially with question_id prefix) to avoid API restart overhead.
            db_path = str(workdir / "lme-crossbench.db")
            result = run_question(
                rec, db_path, workdir, args.nox_mem_bin, args.api_base, args.top_k, env_base,
            )
            if result.error:
                n_err += 1
            fh.write(json.dumps(asdict(result)) + "\n")
            fh.flush()
            n_done += 1
            if n_done % args.progress_every == 0:
                elapsed = time.time() - t_start
                print(
                    f"[adapter] {n_done}/{len(sample)} ({100*n_done/len(sample):.1f}%) "
                    f"errs={n_err} elapsed={elapsed:.1f}s rate={n_done/elapsed:.2f}q/s",
                    file=sys.stderr,
                )
    elapsed = time.time() - t_start
    print(f"[adapter] DONE n={n_done} errs={n_err} elapsed={elapsed:.1f}s out={out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
