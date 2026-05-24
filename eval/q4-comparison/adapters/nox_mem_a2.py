"""
nox-mem A2 adapter — Gemini Flash chunk summarizer corpus + hybrid retrieval.

This is the third attempt at closing the -0.0397 nDCG@10 gap vs mem0@500
on the Q4 capped@500 benchmark. Two prior query-side paths failed:

  - PR #337 query rewrite: -11.8% nDCG@10
  - PR #339 E+F+H combo:    +2.4% only (gap persists)

A2 is INGEST-SIDE concentration — replicates mem0's LLM fact-extraction
mechanism using Gemini Flash Lite (instead of OpenAI; preserves Q/A/P pillar
3 "Autonomy"). Summaries replace raw chunks, ids are PRESERVED so the gold
matching survives.

Architecture
------------
Same hybrid pipeline as `nox_mem.py` (FTS5 + Gemini gemini-embedding-001
+ RRF k=60), except setup() loads from a pre-summarized JSONL at
`cache/summarized-A.jsonl` (built once by `lib/chunk_summarizer.py`).

Why a new adapter (not a flag on nox_mem.py)
--------------------------------------------
- Distinct DB path (`cache/nox-mem-a2.db`) keeps both runs co-resident on
  disk for apples-to-apples re-measurement.
- Distinct module name appears explicitly in run output JSON so downstream
  aggregate scripts can stack A2 vs hybrid vs prod side-by-side.
- Avoids invasive surgery on the canonical adapter that ships PR #338.

Env vars
--------
  GEMINI_API_KEY           required for embedding generation (RETRIEVAL_*).
  NOX_A2_DB_PATH           override hybrid DB path
                           (default: cache/nox-mem-a2.db).
  NOX_A2_SUMMARIZED_PATH   override summarized JSONL path
                           (default: cache/summarized-A.jsonl).
  NOX_MEM_INGEST_LIMIT     cap chunks (cost control; matches sibling adapter).
"""

from __future__ import annotations

import os
import sqlite3
import struct
import sys
import time
from pathlib import Path
from typing import Any

# Reuse helpers from canonical nox_mem adapter where safe.
_HERE = Path(__file__).resolve().parent.parent  # eval/q4-comparison/
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

NAME = "nox-mem-a2"
VERSION_PIN = "a2-summarized-corpus-v1"
REQUIRES_ENV: list[str] = ["GEMINI_API_KEY"]
INSTALL_HINT = (
    "Pre-requisite: pip install google-generativeai sqlite-vec; "
    "run `python -m lib.chunk_summarizer summarize --template A "
    "--output cache/summarized-A.jsonl` once to generate the summarized "
    "JSONL before invoking this adapter."
)

_GEMINI_EMBED_MODEL = "models/gemini-embedding-001"  # 768d
_RRF_K = 60

_DEFAULT_DB = _HERE / "cache" / "nox-mem-a2.db"
_DEFAULT_SUMMARIZED = _HERE / "cache" / "summarized-A.jsonl"

# Module-level state
_con: sqlite3.Connection | None = None
_db_path: Path | None = None
_dim: int | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ingest_limit() -> int | None:
    raw = os.environ.get("NOX_MEM_INGEST_LIMIT", "")
    return int(raw.strip()) if raw.strip().isdigit() else None


def _db_file() -> Path:
    raw = os.environ.get("NOX_A2_DB_PATH", str(_DEFAULT_DB))
    return Path(raw)


def _summarized_path() -> Path:
    raw = os.environ.get("NOX_A2_SUMMARIZED_PATH", str(_DEFAULT_SUMMARIZED))
    return Path(raw)


def _check_gemini_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY not set — required by adapter nox_mem_a2. "
            "source /tmp/q4-gemini-env.sh before running."
        )
    return key


def _get_genai():
    import google.generativeai as genai  # type: ignore
    genai.configure(api_key=_check_gemini_key())
    return genai


def _embed_doc(genai, text: str) -> list[float]:
    return genai.embed_content(
        model=_GEMINI_EMBED_MODEL,
        content=text,
        task_type="RETRIEVAL_DOCUMENT",
    )["embedding"]


def _embed_query(genai, text: str) -> list[float]:
    return genai.embed_content(
        model=_GEMINI_EMBED_MODEL,
        content=text,
        task_type="RETRIEVAL_QUERY",
    )["embedding"]


def _load_sqlite_vec(con: sqlite3.Connection) -> None:
    import sqlite_vec  # type: ignore
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)


def _open_db(p: Path) -> sqlite3.Connection:
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p), check_same_thread=False)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


def _create_schema(con: sqlite3.Connection, dim: int) -> None:
    _load_sqlite_vec(con)
    con.executescript(f"""
        CREATE TABLE IF NOT EXISTS eval_meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS eval_chunks (
            id      TEXT PRIMARY KEY,
            dataset TEXT NOT NULL,
            conv_id TEXT NOT NULL,
            day     INTEGER NOT NULL DEFAULT 0,
            text    TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS eval_chunks_fts
            USING fts5(
                text,
                content='eval_chunks',
                content_rowid='rowid',
                tokenize='unicode61 remove_diacritics 2'
            );
        CREATE TRIGGER IF NOT EXISTS trg_a2_ai
            AFTER INSERT ON eval_chunks BEGIN
                INSERT INTO eval_chunks_fts(rowid, text) VALUES (new.rowid, new.text);
            END;
        CREATE TRIGGER IF NOT EXISTS trg_a2_ad
            AFTER DELETE ON eval_chunks BEGIN
                INSERT INTO eval_chunks_fts(eval_chunks_fts, rowid, text)
                    VALUES ('delete', old.rowid, old.text);
            END;
        CREATE TABLE IF NOT EXISTS eval_chunk_rowids (
            chunk_id TEXT PRIMARY KEY,
            rowid    INTEGER NOT NULL
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS eval_vecs USING vec0(embedding float[{dim}]);
    """)
    con.execute(
        "INSERT OR REPLACE INTO eval_meta(key, value) VALUES ('embed_dim', ?)",
        (str(dim),),
    )
    con.commit()


def _schema_ready(con: sqlite3.Connection) -> bool:
    try:
        n = con.execute("SELECT COUNT(*) FROM eval_chunks LIMIT 1").fetchone()
        if not n or n[0] == 0:
            return False
        v = con.execute("SELECT COUNT(*) FROM eval_vecs LIMIT 1").fetchone()
        return v is not None and v[0] > 0
    except sqlite3.OperationalError:
        return False


def _fts5_escape(q: str) -> str:
    import re
    cleaned = re.sub(r"[^\w\s\-]", " ", q, flags=re.UNICODE)
    tokens = [t for t in cleaned.split() if len(t) >= 2]
    if not tokens:
        return '""'
    return " OR ".join(f'"{t}"' for t in tokens[:20])


def _rrf_score(rank: int) -> float:
    return 1.0 / (_RRF_K + rank)


# ---------------------------------------------------------------------------
# Ingest summarized corpus
# ---------------------------------------------------------------------------


def _ingest_summarized(con: sqlite3.Connection, genai, path: Path) -> int:
    """Load summarized JSONL → eval_chunks + Gemini embeddings + vec0.

    Idempotent by chunk_id. Honours NOX_MEM_INGEST_LIMIT for cost control
    (caps embedding calls; the JSONL stays on disk in full).
    """
    from lib.chunk_summarizer import load_summarized_corpus

    if not path.exists():
        raise FileNotFoundError(
            f"summarized JSONL not found: {path}. "
            f"Run `python -m lib.chunk_summarizer summarize --template A` first."
        )

    limit = _ingest_limit()
    processed = 0
    inserted = 0
    embed_errors = 0
    _RATE_DELAY = 0.05  # ~20 RPS, well under embedding-001 free tier 1500 RPM

    for rec in load_summarized_corpus(path):
        if limit is not None and processed >= limit:
            break
        chunk_id = rec.id

        # Idempotent: skip if already vectorized
        existing = con.execute(
            "SELECT 1 FROM eval_chunk_rowids WHERE chunk_id=?", (chunk_id,)
        ).fetchone()
        if existing:
            processed += 1
            continue

        # Embed (summary text — short, so embedding is cheap and dense)
        try:
            time.sleep(_RATE_DELAY)
            vec = _embed_doc(genai, rec.text[:2000])
        except Exception as e:  # noqa: BLE001
            embed_errors += 1
            if embed_errors <= 5:
                print(
                    f"[nox_mem_a2] embed error for {chunk_id}: {e}",
                    file=sys.stderr,
                )
            processed += 1
            continue

        con.execute(
            "INSERT OR IGNORE INTO eval_chunks(id, dataset, conv_id, day, text) "
            "VALUES (?, ?, ?, ?, ?)",
            (chunk_id, rec.dataset, rec.conversation_id, rec.day, rec.text),
        )
        row = con.execute(
            "SELECT rowid FROM eval_chunks WHERE id=?", (chunk_id,)
        ).fetchone()
        if row:
            rowid = row[0]
            vec_bytes = struct.pack(f"{len(vec)}f", *vec)
            con.execute(
                "INSERT OR REPLACE INTO eval_vecs(rowid, embedding) VALUES (?, ?)",
                (rowid, vec_bytes),
            )
            con.execute(
                "INSERT OR REPLACE INTO eval_chunk_rowids(chunk_id, rowid) "
                "VALUES (?, ?)",
                (chunk_id, rowid),
            )
        con.commit()
        inserted += 1
        processed += 1

        if processed % 50 == 0:
            print(
                f"[nox_mem_a2] embedded {processed} chunks "
                f"({embed_errors} errors, {inserted} new)...",
                file=sys.stderr,
            )

    print(
        f"[nox_mem_a2] ingest done: processed={processed}, inserted={inserted}, "
        f"embed_errors={embed_errors}",
        file=sys.stderr,
    )
    return inserted


# ---------------------------------------------------------------------------
# Adapter contract
# ---------------------------------------------------------------------------


def validate() -> dict:
    has_key = bool(os.environ.get("GEMINI_API_KEY"))
    db = _db_file()
    summ = _summarized_path()
    return {
        "ok": has_key and summ.exists(),
        "error": (
            None
            if (has_key and summ.exists())
            else (
                "GEMINI_API_KEY missing" if not has_key
                else f"summarized JSONL missing: {summ}"
            )
        ),
        "version": VERSION_PIN,
        "notes": (
            f"A2 ingest-side concentration. DB={db}, summarized={summ}. "
            f"NOX_MEM_INGEST_LIMIT={_ingest_limit()}."
        ),
    }


def setup(datasets: list[str] | None = None) -> None:
    """Ingest the summarized JSONL into an isolated hybrid DB.

    Idempotent: re-runs skip already-embedded chunk_ids. Respects
    NOX_MEM_INGEST_LIMIT for capped@N benchmarks.
    """
    global _con, _db_path, _dim
    _check_gemini_key()
    genai = _get_genai()

    db_path = _db_file()
    summ = _summarized_path()
    _db_path = db_path

    print(f"[nox_mem_a2] opening DB: {db_path}", file=sys.stderr)
    con = _open_db(db_path)
    _con = con
    _load_sqlite_vec(con)

    limit = _ingest_limit()

    if _schema_ready(con):
        total = con.execute("SELECT COUNT(*) FROM eval_chunks").fetchone()[0]
        if limit is not None and total >= limit:
            print(
                f"[nox_mem_a2] already loaded: {total:,} chunks (≥ cap {limit}). "
                "Skipping ingest.",
                file=sys.stderr,
            )
            return
        print(
            f"[nox_mem_a2] partial: {total:,} chunks. Resuming ingest...",
            file=sys.stderr,
        )
    else:
        # Probe dim before creating schema
        print("[nox_mem_a2] probing embedding dim...", file=sys.stderr)
        sample_vec = _embed_doc(genai, "hello world")
        dim = len(sample_vec)
        _dim = dim
        print(f"[nox_mem_a2] embedding dim={dim}", file=sys.stderr)
        _create_schema(con, dim)

    t0 = time.time()
    _ingest_summarized(con, genai, summ)
    elapsed = time.time() - t0
    total = con.execute("SELECT COUNT(*) FROM eval_chunks").fetchone()[0]
    vec_total = con.execute("SELECT COUNT(*) FROM eval_vecs").fetchone()[0]
    print(
        f"[nox_mem_a2] setup complete: {total:,} chunks / {vec_total:,} vectors "
        f"({elapsed:.1f}s)",
        file=sys.stderr,
    )


def teardown() -> None:
    global _con
    if _con is not None:
        try:
            _con.close()
        except Exception:
            pass
        _con = None


def search(query: str, k: int = 10) -> list[dict]:
    """RRF k=60 fusion of FTS5 + Gemini dense over the summarized corpus."""
    global _con
    if _con is None:
        setup()
    assert _con is not None, "A2 DB not initialised after setup()"

    _load_sqlite_vec(_con)
    genai = _get_genai()

    k_fetch = k * 3

    # FTS5 leg
    fts_rows: list[tuple] = []
    try:
        fts_rows = _con.execute(
            """
            SELECT c.id, bm25(eval_chunks_fts) AS score
            FROM eval_chunks c
            JOIN eval_chunks_fts f ON f.rowid = c.rowid
            WHERE eval_chunks_fts MATCH ?
            ORDER BY score
            LIMIT ?
            """,
            (_fts5_escape(query), k_fetch),
        ).fetchall()
    except sqlite3.OperationalError:
        pass

    # Dense leg
    dense_rows: list[tuple] = []
    try:
        q_vec = _embed_query(genai, query)
        q_bytes = struct.pack(f"{len(q_vec)}f", *q_vec)
        dense_rows = _con.execute(
            """
            SELECT r.chunk_id, v.distance
            FROM eval_vecs v
            JOIN eval_chunk_rowids r ON r.rowid = v.rowid
            WHERE v.embedding MATCH ?
              AND k = ?
            ORDER BY v.distance
            """,
            (q_bytes, k_fetch),
        ).fetchall()
    except Exception as e:  # noqa: BLE001
        print(f"[nox_mem_a2] dense search error: {e}", file=sys.stderr)

    # RRF fusion
    scores: dict[str, float] = {}
    for rank, (chunk_id, _) in enumerate(fts_rows, 1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + _rrf_score(rank)
    for rank, (chunk_id, _) in enumerate(dense_rows, 1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + _rrf_score(rank)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]
    results: list[dict] = []
    for chunk_id, rrf in ranked:
        row = _con.execute(
            "SELECT text, dataset, conv_id FROM eval_chunks WHERE id=?", (chunk_id,)
        ).fetchone()
        if row:
            results.append({
                "id": chunk_id,
                "score": rrf,
                "text": str(row[0])[:500],
                "source": f"{row[1]}/{row[2]}",
            })
    return results
