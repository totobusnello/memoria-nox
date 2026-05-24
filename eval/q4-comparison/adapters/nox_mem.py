"""
nox-mem adapter — HTTP /api/search on port 18802 (prod) OR local FTS5 eval DB.

Q4 EVAL MODE (default when NOX_EVAL_MODE is unset or "eval"):
  - setup()  : Downloads LoCoMo + LongMemEval corpus via corpus_loader, builds
               an isolated SQLite FTS5 DB at $NOX_EVAL_DB_PATH
               (default `eval/q4-comparison/cache/nox-mem-eval.db`).
               Idempotent — re-runs skip already-loaded rows.
  - search() : Queries local FTS5 DB; returns chunk IDs in gold format
               (e.g. "conv-48::D2:13") so the runner nDCG works correctly.
  - teardown(): Closes DB connection; keeps DB on disk for subsequent runs.

PROD MODE (set NOX_EVAL_MODE=prod):
  - Falls through to HTTP /api/search. Use when benchmarking the full nox-mem
    stack (Gemini hybrid) rather than just FTS5 recall parity.
  - Assumes nox-mem-api is already running externally.

CRITICAL ISOLATION RULE (memory [[eval-harness-must-explicit-isolate-db]]):
  NEVER ingest LoCoMo or LongMemEval data into the prod nox-mem.db.
  The eval DB is wholly separate. NOX_DB_PATH for prod is never touched here.

Env vars:
  NOX_EVAL_MODE      "eval" (default) | "prod"
  NOX_EVAL_DB_PATH   path to isolated SQLite eval DB
                     (default: <q4-comparison>/cache/nox-mem-eval.db)
  NOX_MEM_INGEST_LIMIT  integer cap on total corpus chunks to load (default: full corpus).
                     When set, automatically uses a separate DB path suffixed
                     with the cap (e.g. nox-mem-eval-cap500.db) to avoid
                     contaminating the full-corpus eval DB. Matches mem0's
                     MEM0_INGEST_LIMIT pattern for apples-to-apples comparison.
  NOX_API_BASE       override prod HTTP base URL (prod mode only)
  NOX_API_PORT       override prod port — default 18802 (prod mode only)
"""

from __future__ import annotations

import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

NAME = "nox-mem"
VERSION_PIN = "git-sha (resolve at runtime via `git rev-parse HEAD`)"
REQUIRES_ENV: list[str] = []  # all env vars optional; defaults cover both modes
INSTALL_HINT = (
    "Already in this repo. Eval mode: no extra install — uses stdlib sqlite3. "
    "Prod mode: `npm run build && node dist/index.js api` on VPS, "
    "or set NOX_API_BASE to an existing endpoint."
)

_DEFAULT_PROD_PORT = "18802"
_TIMEOUT_S = 30

# Paths — _HERE is eval/q4-comparison/
_HERE = Path(__file__).resolve().parent.parent
_DEFAULT_EVAL_DB = _HERE / "cache" / "nox-mem-eval.db"

# Module-level state (singleton per process)
_eval_db_path: Path | None = None
_eval_con: sqlite3.Connection | None = None


# ---------------------------------------------------------------------------
# Mode detection helpers
# ---------------------------------------------------------------------------


def _eval_mode() -> bool:
    """True → use local FTS5 eval DB; False → hit prod HTTP endpoint."""
    return os.environ.get("NOX_EVAL_MODE", "eval").lower() != "prod"


def _ingest_limit() -> int | None:
    """Return integer cap from NOX_MEM_INGEST_LIMIT, or None (no cap)."""
    raw = os.environ.get("NOX_MEM_INGEST_LIMIT", "")
    if raw.strip().isdigit():
        return int(raw.strip())
    return None


def _eval_db_file() -> Path:
    """Return the eval DB path, auto-suffixed with cap when NOX_MEM_INGEST_LIMIT is set.

    The suffix keeps capped runs isolated from the full-corpus DB so repeated
    runs at different caps don't overwrite each other and the full-corpus DB
    is never contaminated by a capped ingest.

    Examples:
      no cap  → cache/nox-mem-eval.db
      cap=500 → cache/nox-mem-eval-cap500.db
    """
    limit = _ingest_limit()
    # If caller explicitly set NOX_EVAL_DB_PATH, honour it as-is.
    explicit = os.environ.get("NOX_EVAL_DB_PATH", "")
    if explicit:
        return Path(explicit)
    if limit is not None:
        return _DEFAULT_EVAL_DB.parent / f"nox-mem-eval-cap{limit}.db"
    return _DEFAULT_EVAL_DB


def _prod_base_url() -> str:
    base = os.environ.get("NOX_API_BASE")
    if base:
        return base.rstrip("/")
    port = os.environ.get("NOX_API_PORT", _DEFAULT_PROD_PORT)
    return f"http://127.0.0.1:{port}"


# ---------------------------------------------------------------------------
# Eval DB helpers
# ---------------------------------------------------------------------------


def _fts5_escape(q: str) -> str:
    """Convert natural-language query → FTS5 OR-token expression."""
    cleaned = re.sub(r"[^\w\s\-]", " ", q, flags=re.UNICODE)
    tokens = [t for t in cleaned.split() if len(t) >= 2]
    if not tokens:
        return '""'
    return " OR ".join(f'"{t}"' for t in tokens[:20])


def _open_eval_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path), check_same_thread=False)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


def _schema_ready(con: sqlite3.Connection) -> bool:
    """True if eval_chunks table exists and has at least one row."""
    try:
        row = con.execute("SELECT COUNT(*) FROM eval_chunks LIMIT 1").fetchone()
        return row is not None and row[0] > 0
    except sqlite3.OperationalError:
        return False


def _create_eval_schema(con: sqlite3.Connection) -> None:
    """Create eval_chunks + FTS5 virtual table + triggers (idempotent)."""
    con.executescript("""
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
        CREATE TRIGGER IF NOT EXISTS trg_eval_ai
            AFTER INSERT ON eval_chunks BEGIN
                INSERT INTO eval_chunks_fts(rowid, text) VALUES (new.rowid, new.text);
            END;
        CREATE TRIGGER IF NOT EXISTS trg_eval_ad
            AFTER DELETE ON eval_chunks BEGIN
                INSERT INTO eval_chunks_fts(eval_chunks_fts, rowid, text)
                    VALUES ('delete', old.rowid, old.text);
            END;
    """)
    con.commit()


def _ingest_corpus_into_eval_db(
    con: sqlite3.Connection,
    datasets: list[str],
    limit: int | None = None,
) -> int:
    """Download + parse corpus chunks and bulk-INSERT into eval_chunks.

    Uses INSERT OR IGNORE → idempotent (re-runs skip existing rows).
    Returns total number of newly inserted rows.

    Parameters
    ----------
    limit : int | None
        If set, caps the TOTAL number of corpus chunks ingested across all
        datasets (LoCoMo first, then LongMemEval). Mirrors MEM0_INGEST_LIMIT
        semantics for apples-to-apples corpus-cap comparison.
        None (default) = full corpus, no cap.
    """
    # lib/ lives alongside adapters/ under eval/q4-comparison/
    if str(_HERE) not in sys.path:
        sys.path.insert(0, str(_HERE))

    from lib.corpus_loader import load_locomo_corpus, load_longmemeval_corpus

    batch: list[tuple[str, str, str, int, str]] = []
    inserted_total = 0
    global_count = 0  # total chunks yielded (capped against limit)

    def flush(force: bool = False) -> None:
        nonlocal inserted_total
        if not batch or (not force and len(batch) < 500):
            return
        con.executemany(
            "INSERT OR IGNORE INTO eval_chunks(id, dataset, conv_id, day, text) "
            "VALUES (?, ?, ?, ?, ?)",
            batch,
        )
        con.commit()
        inserted_total += len(batch)
        batch.clear()

    def _cap_reached() -> bool:
        return limit is not None and global_count >= limit

    if "locomo" in datasets:
        print(
            f"[nox_mem/eval] ingesting LoCoMo corpus"
            f"{f' (cap={limit})' if limit else ''}...",
            file=sys.stderr,
        )
        before = inserted_total
        for chunk in load_locomo_corpus():
            if _cap_reached():
                break
            batch.append(
                (chunk.id, chunk.dataset, chunk.conversation_id, chunk.day, chunk.text)
            )
            global_count += 1
            flush()
        flush(force=True)
        print(
            f"[nox_mem/eval] LoCoMo: {inserted_total - before:,} rows inserted",
            file=sys.stderr,
        )

    if "longmemeval" in datasets and not _cap_reached():
        print(
            f"[nox_mem/eval] ingesting LongMemEval (oracle split)"
            f"{f' (cap={limit}, remaining={limit - global_count})' if limit else ''}...",
            file=sys.stderr,
        )
        before = inserted_total
        for chunk in load_longmemeval_corpus("oracle"):
            if _cap_reached():
                break
            batch.append(
                (chunk.id, chunk.dataset, chunk.conversation_id, chunk.day, chunk.text)
            )
            global_count += 1
            flush()
        flush(force=True)
        print(
            f"[nox_mem/eval] LongMemEval: {inserted_total - before:,} rows inserted",
            file=sys.stderr,
        )

    if limit is not None:
        print(
            f"[nox_mem/eval] corpus cap applied: {global_count}/{limit} chunks yielded",
            file=sys.stderr,
        )

    return inserted_total


# ---------------------------------------------------------------------------
# Adapter contract
# ---------------------------------------------------------------------------


def validate() -> dict:
    """Static validation — no network calls, no quota burn."""
    if _eval_mode():
        db_path = _eval_db_file()
        limit = _ingest_limit()
        cap_note = f" NOX_MEM_INGEST_LIMIT={limit} (capped run)." if limit else ""
        return {
            "ok": True,
            "error": None,
            "version": VERSION_PIN,
            "notes": (
                f"eval mode — local FTS5 DB at {db_path}.{cap_note} "
                "setup() downloads corpus on first run (LoCoMo + LongMemEval oracle). "
                "Set NOX_EVAL_MODE=prod to use HTTP endpoint instead."
            ),
        }
    # prod mode
    try:
        import requests  # noqa: F401
    except ImportError as exc:
        return {
            "ok": False,
            "error": f"requests not installed: {exc}",
            "version": None,
            "notes": "pip install requests",
        }
    return {
        "ok": True,
        "error": None,
        "version": VERSION_PIN,
        "notes": f"prod mode — endpoint: {_prod_base_url()}/api/search",
    }


def setup(datasets: list[str] | None = None) -> None:
    """Prepare the retrieval backend for Q4 queries.

    Eval mode (default):
      Opens (or creates) isolated SQLite FTS5 DB, downloads corpus if needed,
      and ingests chunks with stable IDs matching gold_chunk_ids format.
      Idempotent: already-loaded rows are skipped.

      When NOX_MEM_INGEST_LIMIT is set, only the first N chunks are loaded
      (LoCoMo first, then LongMemEval) and the DB is stored at a cap-specific
      path (e.g. nox-mem-eval-cap500.db) to avoid contaminating the full DB.
      Each unique cap value gets its own persistent DB — subsequent runs at
      the same cap reuse the existing capped DB without re-ingesting.

    Prod mode (NOX_EVAL_MODE=prod):
      No-op — assumes nox-mem-api running externally.

    Parameters
    ----------
    datasets : list[str] | None
        Datasets to ingest. Default: ["locomo", "longmemeval"].
    """
    global _eval_db_path, _eval_con

    if not _eval_mode():
        return  # prod mode — external API

    if datasets is None:
        datasets = ["locomo", "longmemeval"]

    limit = _ingest_limit()
    db_path = _eval_db_file()
    _eval_db_path = db_path

    if limit is not None:
        print(
            f"[nox_mem/eval] NOX_MEM_INGEST_LIMIT={limit} → capped DB: {db_path}",
            file=sys.stderr,
        )
    else:
        print(f"[nox_mem/eval] opening eval DB: {db_path}", file=sys.stderr)

    con = _open_eval_db(db_path)
    _eval_con = con

    if _schema_ready(con):
        total = con.execute("SELECT COUNT(*) FROM eval_chunks").fetchone()[0]
        if limit is not None:
            # Capped DB: if total matches or exceeds limit, already ready.
            # If < limit and < full corpus, still usable — don't re-ingest partial.
            print(
                f"[nox_mem/eval] capped DB already loaded ({total:,} chunks, cap={limit})",
                file=sys.stderr,
            )
            return
        # Full DB: check each dataset individually
        for ds in datasets:
            cnt = con.execute(
                "SELECT COUNT(*) FROM eval_chunks WHERE dataset=?", (ds,)
            ).fetchone()[0]
            if cnt == 0:
                print(
                    f"[nox_mem/eval] dataset '{ds}' missing — ingesting...",
                    file=sys.stderr,
                )
                _ingest_corpus_into_eval_db(con, [ds], limit=None)
            else:
                print(
                    f"[nox_mem/eval] dataset '{ds}' already loaded ({cnt:,} chunks)",
                    file=sys.stderr,
                )
        return

    # First-time setup: create schema + ingest all (or up to limit)
    print(
        f"[nox_mem/eval] first-time setup — creating schema + ingesting"
        f"{f' (cap={limit})' if limit else ''}...",
        file=sys.stderr,
    )
    _create_eval_schema(con)
    t0 = time.time()
    _ingest_corpus_into_eval_db(con, datasets, limit=limit)
    elapsed = time.time() - t0
    total = con.execute("SELECT COUNT(*) FROM eval_chunks").fetchone()[0]
    print(
        f"[nox_mem/eval] setup complete: {total:,} chunks in DB ({elapsed:.1f}s)",
        file=sys.stderr,
    )


def teardown() -> None:
    """Close eval DB connection (keeps DB on disk for subsequent runs)."""
    global _eval_con
    if _eval_con is not None:
        try:
            _eval_con.close()
        except Exception:
            pass
        _eval_con = None


def search(query: str, k: int = 10) -> list[dict]:
    """Retrieve top-k chunks for a query.

    Eval mode: FTS5 BM25 search on local DB — returns gold-format IDs.
    Prod mode: HTTP GET /api/search against running nox-mem-api.

    Returns
    -------
    list[dict]
        [{id, score, text, source}, ...] — id matches gold_chunk_ids format
        (e.g. "conv-48::D2:13") in eval mode.
    """
    if _eval_mode():
        return _search_eval(query, k)
    return _search_prod(query, k)


# ---------------------------------------------------------------------------
# Eval search — local FTS5
# ---------------------------------------------------------------------------


def _search_eval(query: str, k: int) -> list[dict]:
    global _eval_con

    if _eval_con is None:
        # Lazy setup (runner may call search() without setup() in edge cases)
        setup()

    assert _eval_con is not None, "eval DB not initialised after setup()"

    fq = _fts5_escape(query)
    try:
        rows = _eval_con.execute(
            """
            SELECT c.id, c.dataset, c.conv_id, c.text,
                   bm25(eval_chunks_fts) AS score
            FROM eval_chunks c
            JOIN eval_chunks_fts f ON f.rowid = c.rowid
            WHERE eval_chunks_fts MATCH ?
            ORDER BY score
            LIMIT ?
            """,
            (fq, k),
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []

    results: list[dict] = []
    for chunk_id, dataset, conv_id, text, bm25_score in rows:
        # bm25() in SQLite FTS5 returns negative values (more negative = better)
        score = -float(bm25_score) if bm25_score is not None else 0.0
        results.append(
            {
                "id": str(chunk_id),
                "score": score,
                "text": str(text)[:500],
                "source": f"{dataset}/{conv_id}",
            }
        )
    return results


# ---------------------------------------------------------------------------
# Prod search — HTTP endpoint
# ---------------------------------------------------------------------------


def _search_prod(query: str, k: int) -> list[dict[str, Any]]:
    import requests

    resp = requests.get(
        f"{_prod_base_url()}/api/search",
        params={"q": query, "limit": k, "format": "json"},
        timeout=_TIMEOUT_S,
    )
    resp.raise_for_status()
    payload = resp.json()

    # /api/search returns array directly (verified 2026-05-24 via tunnel against prod VPS).
    # Defensive fallback for dict-wrapped variants kept for forward-compat.
    if isinstance(payload, list):
        items_raw: list[dict[str, Any]] = payload
    elif isinstance(payload, dict):
        items_raw = payload.get("results") or payload.get("items") or []
    else:
        items_raw = []

    return [
        {
            "id": str(item.get("id") or item.get("chunk_id") or ""),
            "score": float(item.get("score") or item.get("rrf_score") or 0.0),
            "text": item.get("chunk_text") or item.get("text") or "",
            "source": item.get("source_file") or item.get("source") or None,
        }
        for item in items_raw[:k]
    ]
