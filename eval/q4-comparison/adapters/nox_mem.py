"""
nox-mem adapter — HTTP /api/search on port 18802 (prod) OR local eval DB.

Q4 EVAL MODE (default when NOX_EVAL_MODE is unset or "eval"):
  - setup()  : Downloads LoCoMo + LongMemEval corpus via corpus_loader, builds
               an isolated SQLite FTS5 DB at $NOX_EVAL_DB_PATH
               (default `eval/q4-comparison/cache/nox-mem-eval.db`).
               Idempotent — re-runs skip already-loaded rows.
  - search() : Queries local FTS5 DB; returns chunk IDs in gold format
               (e.g. "conv-48::D2:13") so the runner nDCG works correctly.
  - teardown(): Closes DB connection; keeps DB on disk for subsequent runs.

HYBRID MODE (set NOX_EVAL_MODE=hybrid):
  - setup()  : Ingest corpus into isolated SQLite DB *with* Gemini embeddings
               (models/gemini-embedding-001, 768d) stored via sqlite-vec (vec0).
               Uses NOX_MEM_INGEST_LIMIT to cap chunks (cost control).
               GEMINI_API_KEY must be set.
  - search() : RRF k=60 fusion of FTS5 BM25 results + Gemini dense retrieval
               (same pipeline as prod nox-mem). Returns gold-format IDs.

PROD MODE (set NOX_EVAL_MODE=prod):
  - Falls through to HTTP /api/search. Use when benchmarking the full nox-mem
    stack (Gemini hybrid) rather than just FTS5 recall parity.
  - Assumes nox-mem-api is already running externally.

CRITICAL ISOLATION RULE (memory [[eval-harness-must-explicit-isolate-db]]):
  NEVER ingest LoCoMo or LongMemEval data into the prod nox-mem.db.
  The eval DB is wholly separate. NOX_DB_PATH for prod is never touched here.

Env vars:
  NOX_EVAL_MODE      "eval" (default) | "hybrid" | "prod"
  NOX_EVAL_DB_PATH   path to isolated SQLite eval DB
                     (default: <q4-comparison>/cache/nox-mem-eval.db)
  NOX_HYBRID_DB_PATH path to isolated SQLite hybrid eval DB
                     (default: <q4-comparison>/cache/nox-mem-hybrid.db)
  NOX_MEM_INGEST_LIMIT  max chunks to ingest (hybrid+eval modes; cost control)
  GEMINI_API_KEY     required for hybrid mode
  NOX_API_BASE       override prod HTTP base URL (prod mode only)
  NOX_API_PORT       override prod port — default 18802 (prod mode only)
"""

from __future__ import annotations

import os
import re
import sqlite3
import struct
import sys
import time
from pathlib import Path
from typing import Any

NAME = "nox-mem"
VERSION_PIN = "git-sha (resolve at runtime via `git rev-parse HEAD`)"
REQUIRES_ENV: list[str] = []  # all env vars optional; defaults cover all modes
INSTALL_HINT = (
    "Already in this repo. Eval mode: no extra install — uses stdlib sqlite3. "
    "Hybrid mode: pip install google-generativeai sqlite-vec; set GEMINI_API_KEY. "
    "Prod mode: `npm run build && node dist/index.js api` on VPS, "
    "or set NOX_API_BASE to an existing endpoint."
)

_DEFAULT_PROD_PORT = "18802"
_TIMEOUT_S = 30
_GEMINI_EMBED_MODEL = "models/gemini-embedding-001"  # gemini-embedding-001 (768d output)
_RRF_K = 60

# Paths — _HERE is eval/q4-comparison/
_HERE = Path(__file__).resolve().parent.parent
_DEFAULT_EVAL_DB = _HERE / "cache" / "nox-mem-eval.db"
_DEFAULT_HYBRID_DB = _HERE / "cache" / "nox-mem-hybrid.db"

# Module-level state (singleton per process)
_eval_db_path: Path | None = None
_eval_con: sqlite3.Connection | None = None

# Hybrid state
_hybrid_db_path: Path | None = None
_hybrid_con: sqlite3.Connection | None = None
_hybrid_dim: int | None = None


# ---------------------------------------------------------------------------
# Mode detection helpers
# ---------------------------------------------------------------------------


def _get_mode() -> str:
    """Return active mode: 'eval' | 'hybrid' | 'prod'."""
    raw = os.environ.get("NOX_EVAL_MODE", "eval").lower()
    if raw in ("hybrid", "prod"):
        return raw
    return "eval"


def _eval_mode() -> bool:
    """True → use local FTS5 eval DB; False → hit prod HTTP or hybrid."""
    return _get_mode() == "eval"


def _hybrid_mode() -> bool:
    return _get_mode() == "hybrid"


def _eval_db_file() -> Path:
    raw = os.environ.get("NOX_EVAL_DB_PATH", str(_DEFAULT_EVAL_DB))
    return Path(raw)


def _hybrid_db_file() -> Path:
    raw = os.environ.get("NOX_HYBRID_DB_PATH", str(_DEFAULT_HYBRID_DB))
    return Path(raw)


def _prod_base_url() -> str:
    base = os.environ.get("NOX_API_BASE")
    if base:
        return base.rstrip("/")
    port = os.environ.get("NOX_API_PORT", _DEFAULT_PROD_PORT)
    return f"http://127.0.0.1:{port}"


def _ingest_limit() -> int | None:
    """Return NOX_MEM_INGEST_LIMIT as int, or None (no cap)."""
    raw = os.environ.get("NOX_MEM_INGEST_LIMIT", "")
    if raw.strip().isdigit():
        return int(raw.strip())
    return None


# ---------------------------------------------------------------------------
# Eval DB helpers (FTS5 only)
# ---------------------------------------------------------------------------


def _fts5_escape(q: str) -> str:
    """Convert natural-language query → FTS5 OR-token expression."""
    cleaned = re.sub(r"[^\w\s\-]", " ", q, flags=re.UNICODE)
    tokens = [t for t in cleaned.split() if len(t) >= 2]
    if not tokens:
        return '""'
    return " OR ".join(f'"{t}"' for t in tokens[:20])


def _open_db(db_path: Path) -> sqlite3.Connection:
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


def _ingest_corpus_into_eval_db(con: sqlite3.Connection, datasets: list[str]) -> int:
    """Download + parse corpus chunks and bulk-INSERT into eval_chunks.

    Uses INSERT OR IGNORE → idempotent (re-runs skip existing rows).
    Respects NOX_MEM_INGEST_LIMIT for cost-controlled test runs.
    Returns total number of newly inserted rows.
    """
    if str(_HERE) not in sys.path:
        sys.path.insert(0, str(_HERE))

    from lib.corpus_loader import load_locomo_corpus, load_longmemeval_corpus

    batch: list[tuple[str, str, str, int, str]] = []
    inserted_total = 0
    limit = _ingest_limit()
    global_count = 0

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

    def add_chunk(chunk) -> bool:
        nonlocal global_count
        if limit is not None and global_count >= limit:
            return False
        batch.append(
            (chunk.id, chunk.dataset, chunk.conversation_id, chunk.day, chunk.text)
        )
        global_count += 1
        flush()
        return True

    if "locomo" in datasets:
        print("[nox_mem/eval] ingesting LoCoMo corpus...", file=sys.stderr)
        before = inserted_total
        for chunk in load_locomo_corpus():
            if not add_chunk(chunk):
                break
        flush(force=True)
        print(
            f"[nox_mem/eval] LoCoMo: {inserted_total - before:,} rows inserted",
            file=sys.stderr,
        )

    if "longmemeval" in datasets and (limit is None or global_count < limit):
        print(
            "[nox_mem/eval] ingesting LongMemEval (oracle split)...", file=sys.stderr
        )
        before = inserted_total
        for chunk in load_longmemeval_corpus("oracle"):
            if not add_chunk(chunk):
                break
        flush(force=True)
        print(
            f"[nox_mem/eval] LongMemEval: {inserted_total - before:,} rows inserted",
            file=sys.stderr,
        )

    if limit is not None:
        print(
            f"[nox_mem/eval] NOX_MEM_INGEST_LIMIT={limit}: {global_count} chunks total",
            file=sys.stderr,
        )

    return inserted_total


# ---------------------------------------------------------------------------
# Hybrid mode helpers — Gemini embeddings + sqlite-vec + RRF
# ---------------------------------------------------------------------------


def _check_gemini_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY not set — required for NOX_EVAL_MODE=hybrid. "
            "source /tmp/q4-gemini-env.sh before running."
        )
    return key


def _get_genai():
    import google.generativeai as genai  # type: ignore
    key = _check_gemini_key()
    genai.configure(api_key=key)
    return genai


def _embed_text(genai, text: str) -> list[float]:
    """Embed a single text with Gemini embedding-001."""
    result = genai.embed_content(
        model=_GEMINI_EMBED_MODEL,
        content=text,
        task_type="RETRIEVAL_DOCUMENT",
    )
    return result["embedding"]


def _embed_query(genai, text: str) -> list[float]:
    result = genai.embed_content(
        model=_GEMINI_EMBED_MODEL,
        content=text,
        task_type="RETRIEVAL_QUERY",
    )
    return result["embedding"]


def _create_hybrid_schema(con: sqlite3.Connection, dim: int) -> None:
    """Create eval_chunks + FTS5 + sqlite-vec vec0 table + meta (idempotent)."""
    import sqlite_vec  # type: ignore
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)

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
        CREATE TRIGGER IF NOT EXISTS trg_hybrid_ai
            AFTER INSERT ON eval_chunks BEGIN
                INSERT INTO eval_chunks_fts(rowid, text) VALUES (new.rowid, new.text);
            END;
        CREATE TRIGGER IF NOT EXISTS trg_hybrid_ad
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


def _load_sqlite_vec_ext(con: sqlite3.Connection) -> None:
    import sqlite_vec  # type: ignore
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)


def _hybrid_schema_ready(con: sqlite3.Connection) -> bool:
    try:
        row = con.execute("SELECT COUNT(*) FROM eval_chunks LIMIT 1").fetchone()
        if row is None or row[0] == 0:
            return False
        row2 = con.execute("SELECT COUNT(*) FROM eval_vecs LIMIT 1").fetchone()
        return row2 is not None and row2[0] > 0
    except sqlite3.OperationalError:
        return False


def _ingest_corpus_hybrid(
    con: sqlite3.Connection,
    genai,
    datasets: list[str],
) -> int:
    """Ingest corpus with Gemini embeddings into hybrid DB. Idempotent by chunk_id."""
    if str(_HERE) not in sys.path:
        sys.path.insert(0, str(_HERE))

    from lib.corpus_loader import load_locomo_corpus, load_longmemeval_corpus

    limit = _ingest_limit()
    global_count = 0
    embed_errors = 0
    inserted_total = 0

    # Gemini embedding-001 free tier: ~1500 RPM. 50ms between calls = ~20 RPS.
    _RATE_DELAY = 0.05

    def process_chunk(chunk) -> bool:
        nonlocal global_count, embed_errors, inserted_total

        if limit is not None and global_count >= limit:
            return False

        chunk_id = chunk.id
        # Idempotent: skip if already vectorized
        existing = con.execute(
            "SELECT 1 FROM eval_chunk_rowids WHERE chunk_id=?", (chunk_id,)
        ).fetchone()
        if existing:
            global_count += 1
            return True

        # Embed
        try:
            time.sleep(_RATE_DELAY)
            vec = _embed_text(genai, chunk.text[:2000])
        except Exception as e:
            embed_errors += 1
            if embed_errors <= 5:
                print(
                    f"[nox_mem/hybrid] embed error for {chunk_id}: {e}",
                    file=sys.stderr,
                )
            global_count += 1
            return True  # skip vector, continue corpus

        # Insert chunk text (trigger populates FTS)
        con.execute(
            "INSERT OR IGNORE INTO eval_chunks(id, dataset, conv_id, day, text) "
            "VALUES (?, ?, ?, ?, ?)",
            (chunk_id, chunk.dataset, chunk.conversation_id, chunk.day, chunk.text),
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
                "INSERT OR REPLACE INTO eval_chunk_rowids(chunk_id, rowid) VALUES (?, ?)",
                (chunk_id, rowid),
            )
        con.commit()
        inserted_total += 1
        global_count += 1

        if global_count % 50 == 0:
            print(
                f"[nox_mem/hybrid] embedded {global_count} chunks "
                f"({embed_errors} errors, {inserted_total} new)...",
                file=sys.stderr,
            )
        return True

    if "locomo" in datasets:
        print("[nox_mem/hybrid] ingesting LoCoMo with Gemini embeddings...", file=sys.stderr)
        for chunk in load_locomo_corpus():
            if not process_chunk(chunk):
                break

    if "longmemeval" in datasets and (limit is None or global_count < limit):
        print("[nox_mem/hybrid] ingesting LongMemEval with Gemini embeddings...", file=sys.stderr)
        for chunk in load_longmemeval_corpus("oracle"):
            if not process_chunk(chunk):
                break

    if limit is not None:
        print(
            f"[nox_mem/hybrid] NOX_MEM_INGEST_LIMIT={limit}: {global_count} total, "
            f"{inserted_total} new, {embed_errors} embed errors",
            file=sys.stderr,
        )
    return inserted_total


def _rrf_score(rank: int, k: int = _RRF_K) -> float:
    return 1.0 / (k + rank)


def _search_hybrid_local(query: str, k: int) -> list[dict]:
    """RRF fusion of FTS5 + Gemini dense search on local hybrid DB."""
    global _hybrid_con

    if _hybrid_con is None:
        raise RuntimeError("hybrid DB not initialised — call setup() first")

    _load_sqlite_vec_ext(_hybrid_con)

    # --- FTS5 leg ---
    fq = _fts5_escape(query)
    fts_rows: list[tuple] = []
    try:
        fts_rows = _hybrid_con.execute(
            """
            SELECT c.id, bm25(eval_chunks_fts) AS score
            FROM eval_chunks c
            JOIN eval_chunks_fts f ON f.rowid = c.rowid
            WHERE eval_chunks_fts MATCH ?
            ORDER BY score
            LIMIT ?
            """,
            (fq, k * 3),
        ).fetchall()
    except sqlite3.OperationalError:
        pass

    # --- Dense leg ---
    genai = _get_genai()
    dense_rows: list[tuple] = []
    try:
        q_vec = _embed_query(genai, query)
        q_bytes = struct.pack(f"{len(q_vec)}f", *q_vec)
        dense_rows = _hybrid_con.execute(
            """
            SELECT r.chunk_id, v.distance
            FROM eval_vecs v
            JOIN eval_chunk_rowids r ON r.rowid = v.rowid
            WHERE v.embedding MATCH ?
              AND k = ?
            ORDER BY v.distance
            """,
            (q_bytes, k * 3),
        ).fetchall()
    except Exception as e:
        print(f"[nox_mem/hybrid] dense search error: {e}", file=sys.stderr)

    # --- RRF fusion ---
    scores: dict[str, float] = {}
    for rank, (chunk_id, _) in enumerate(fts_rows, 1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + _rrf_score(rank)
    for rank, (chunk_id, _) in enumerate(dense_rows, 1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + _rrf_score(rank)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]

    results: list[dict] = []
    for chunk_id, rrf in ranked:
        row = _hybrid_con.execute(
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


# ---------------------------------------------------------------------------
# Adapter contract
# ---------------------------------------------------------------------------


def validate() -> dict:
    """Static validation — no network calls, no quota burn."""
    mode = _get_mode()
    if mode == "eval":
        db_path = _eval_db_file()
        return {
            "ok": True,
            "error": None,
            "version": VERSION_PIN,
            "notes": (
                f"eval mode — local FTS5 DB at {db_path}. "
                "setup() downloads corpus on first run (LoCoMo + LongMemEval oracle). "
                "Set NOX_EVAL_MODE=hybrid for Gemini dense+RRF mode."
            ),
        }
    if mode == "hybrid":
        db_path = _hybrid_db_file()
        has_key = bool(os.environ.get("GEMINI_API_KEY"))
        limit = _ingest_limit()
        return {
            "ok": has_key,
            "error": None if has_key else "GEMINI_API_KEY not set",
            "version": VERSION_PIN,
            "notes": (
                f"hybrid mode — FTS5+dense+RRF, DB at {db_path}. "
                f"NOX_MEM_INGEST_LIMIT={limit}. "
                "Requires: pip install google-generativeai sqlite-vec + GEMINI_API_KEY."
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
      Opens (or creates) isolated SQLite FTS5 DB, downloads corpus if needed.
      Idempotent: already-loaded rows are skipped.
      Respects NOX_MEM_INGEST_LIMIT env var to cap chunk count.

    Hybrid mode (NOX_EVAL_MODE=hybrid):
      Opens (or creates) isolated SQLite DB with FTS5 + sqlite-vec embeddings.
      Ingests corpus with Gemini gemini-embedding-001 (768d), then enables
      RRF k=60 fusion search. Idempotent by chunk_id. GEMINI_API_KEY required.

    Prod mode (NOX_EVAL_MODE=prod):
      No-op — assumes nox-mem-api running externally.

    Parameters
    ----------
    datasets : list[str] | None
        Datasets to ingest. Default: ["locomo", "longmemeval"].
    """
    global _eval_db_path, _eval_con, _hybrid_db_path, _hybrid_con, _hybrid_dim

    mode = _get_mode()

    if mode == "prod":
        return

    if datasets is None:
        datasets = ["locomo", "longmemeval"]

    # -----------------------------------------------------------------------
    # HYBRID mode
    # -----------------------------------------------------------------------
    if mode == "hybrid":
        _check_gemini_key()
        genai = _get_genai()

        db_path = _hybrid_db_file()
        _hybrid_db_path = db_path

        print(f"[nox_mem/hybrid] opening hybrid DB: {db_path}", file=sys.stderr)
        con = _open_db(db_path)
        _hybrid_con = con

        # Load sqlite-vec extension on the connection
        _load_sqlite_vec_ext(con)

        limit = _ingest_limit()

        if _hybrid_schema_ready(con):
            total = con.execute("SELECT COUNT(*) FROM eval_chunks").fetchone()[0]
            vec_total = con.execute("SELECT COUNT(*) FROM eval_vecs").fetchone()[0]
            if limit is not None and total >= limit:
                print(
                    f"[nox_mem/hybrid] already loaded: {total:,} chunks / "
                    f"{vec_total:,} vectors (at/above cap {limit}). Skipping ingest.",
                    file=sys.stderr,
                )
                return
            print(
                f"[nox_mem/hybrid] partial: {total:,} chunks / {vec_total:,} vectors. "
                "Resuming ingest...",
                file=sys.stderr,
            )
        else:
            # Probe dim before creating schema
            print("[nox_mem/hybrid] probing embedding dim...", file=sys.stderr)
            sample_vec = _embed_text(genai, "hello world")
            dim = len(sample_vec)
            _hybrid_dim = dim
            print(f"[nox_mem/hybrid] embedding dim={dim}", file=sys.stderr)
            _create_hybrid_schema(con, dim)

        t0 = time.time()
        _ingest_corpus_hybrid(con, genai, datasets)
        elapsed = time.time() - t0
        total = con.execute("SELECT COUNT(*) FROM eval_chunks").fetchone()[0]
        vec_total = con.execute("SELECT COUNT(*) FROM eval_vecs").fetchone()[0]
        print(
            f"[nox_mem/hybrid] setup complete: {total:,} chunks / {vec_total:,} vectors "
            f"({elapsed:.1f}s)",
            file=sys.stderr,
        )
        return

    # -----------------------------------------------------------------------
    # EVAL mode (FTS5 only)
    # -----------------------------------------------------------------------
    db_path = _eval_db_file()
    _eval_db_path = db_path

    print(f"[nox_mem/eval] opening eval DB: {db_path}", file=sys.stderr)
    con = _open_db(db_path)
    _eval_con = con

    if _schema_ready(con):
        for ds in datasets:
            cnt = con.execute(
                "SELECT COUNT(*) FROM eval_chunks WHERE dataset=?", (ds,)
            ).fetchone()[0]
            limit = _ingest_limit()
            if cnt == 0:
                print(
                    f"[nox_mem/eval] dataset '{ds}' missing — ingesting...",
                    file=sys.stderr,
                )
                _ingest_corpus_into_eval_db(con, [ds])
            else:
                print(
                    f"[nox_mem/eval] dataset '{ds}' already loaded ({cnt:,} chunks)",
                    file=sys.stderr,
                )
        return

    print("[nox_mem/eval] first-time setup — creating schema + ingesting...", file=sys.stderr)
    _create_eval_schema(con)
    t0 = time.time()
    _ingest_corpus_into_eval_db(con, datasets)
    elapsed = time.time() - t0
    total = con.execute("SELECT COUNT(*) FROM eval_chunks").fetchone()[0]
    print(
        f"[nox_mem/eval] setup complete: {total:,} chunks in DB ({elapsed:.1f}s)",
        file=sys.stderr,
    )


def teardown() -> None:
    """Close eval/hybrid DB connections (keeps DBs on disk for subsequent runs)."""
    global _eval_con, _hybrid_con
    for attr, con in [("_eval_con", _eval_con), ("_hybrid_con", _hybrid_con)]:
        if con is not None:
            try:
                con.close()
            except Exception:
                pass
    _eval_con = None
    _hybrid_con = None


def search(query: str, k: int = 10) -> list[dict]:
    """Retrieve top-k chunks for a query.

    Eval mode: FTS5 BM25 search on local DB — returns gold-format IDs.
    Hybrid mode: RRF fusion (FTS5 + Gemini dense) — returns gold-format IDs.
    Prod mode: HTTP GET /api/search against running nox-mem-api.

    Returns
    -------
    list[dict]
        [{id, score, text, source}, ...] — id matches gold_chunk_ids format
        (e.g. "conv-48::D2:13") in eval/hybrid modes.
    """
    mode = _get_mode()
    if mode == "eval":
        return _search_eval(query, k)
    if mode == "hybrid":
        return _search_hybrid_local(query, k)
    return _search_prod(query, k)


# ---------------------------------------------------------------------------
# Eval search — local FTS5
# ---------------------------------------------------------------------------


def _search_eval(query: str, k: int) -> list[dict]:
    global _eval_con

    if _eval_con is None:
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
