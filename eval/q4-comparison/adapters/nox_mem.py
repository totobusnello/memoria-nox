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

QUERY REWRITE LAYER (set NOX_QUERY_REWRITE=1 on top of hybrid mode):
  - Pre-search: call Gemini Flash Lite to expand the user query into 3
    semantically related variants (synonyms, expansions, paraphrases).
  - For original + each variant (4 passes total), run the hybrid FTS5+dense
    +RRF pipeline. Merge by summing per-chunk RRF contributions across the
    4 passes; rerank descending and return top-k.
  - Rationale: matches mem0's LLM concentration mechanism that wins at sparse
    coverage (hybrid@500: 0.0918 vs mem0@500: 0.1315). See memory
    [[concentration-vs-coverage]] and Lab Q1 P1.
  - Cost: ~$0.00005 per query (Gemini Flash Lite, ~150 input tokens, ~80 output).
    20 queries smoke ≈ $0.001. Gated on NOX_QUERY_REWRITE=1 so it never
    burns quota by accident.

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
  NOX_QUERY_REWRITE  "1" enables LLM query rewrite layer (hybrid mode only).
                     Default off. Adds ~$0.00005/query via Gemini Flash Lite.
  NOX_QUERY_REWRITE_MODEL  override rewrite model
                           (default: gemini-2.5-flash-lite)
  NOX_QUERY_REWRITE_N      number of variants to generate (default: 3)
"""

from __future__ import annotations

import json
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
_RRF_K_DEFAULT = 60

# Query rewrite layer defaults
_REWRITE_MODEL_DEFAULT = "gemini-2.5-flash-lite"
_REWRITE_N_DEFAULT = 3
_REWRITE_TIMEOUT_S = 15
_REWRITE_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)

# Path E+F+H — KG traversal + RRF tune + top-k expansion (mission 2026-05-24).
# All three behaviours are env-gated; baseline (all unset) replays PR #318
# hybrid@500 unchanged.
_TOP_K_EXPAND_DEFAULT = 30      # internal candidate pool size (H: pre-rerank cap)
_KG_BOOST_FACTOR_DEFAULT = 1.5  # multiplicative bump for KG-related chunks
_KG_QUERY_MODEL_DEFAULT = "gemini-2.5-flash-lite"
_KG_QUERY_TIMEOUT_S = 12
_KG_ENTITY_EXTRACTION_PROMPT = (
    "Extract canonical entity names from the user query. Return JSON only — "
    "an array of 1-6 entity names (people, places, objects, events, concepts). "
    "Skip pronouns and generic words. If no clear entity, return [].\n\n"
    "Query: {q}\n\nJSON array:"
)

# Caches for KG path (per-process)
_kg_query_entities_cache: dict[str, list[str]] = {}
_kg_query_calls: int = 0
_kg_query_errors: int = 0

# Counters for cost / observability tracking
_rewrite_calls: int = 0
_rewrite_errors: int = 0
_rewrite_cache: dict[str, list[str]] = {}

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


def _rrf_k() -> int:
    """F: RRF fusion constant — env override NOX_RRF_K (default 60)."""
    raw = os.environ.get("NOX_RRF_K", "").strip()
    if raw.isdigit():
        n = int(raw)
        return max(1, min(n, 200))  # safety cap 1..200
    return _RRF_K_DEFAULT


def _top_k_expand() -> int:
    """H: internal candidate pool size — env override NOX_TOP_K_EXPAND."""
    raw = os.environ.get("NOX_TOP_K_EXPAND", "").strip()
    if raw.isdigit():
        n = int(raw)
        return max(10, min(n, 500))
    return _TOP_K_EXPAND_DEFAULT


def _kg_retrieval_enabled() -> bool:
    raw = os.environ.get("NOX_RETRIEVAL_KG", "0").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _kg_boost_factor() -> float:
    raw = os.environ.get("NOX_KG_BOOST", "").strip()
    try:
        v = float(raw)
        if 1.0 <= v <= 5.0:
            return v
    except ValueError:
        pass
    return _KG_BOOST_FACTOR_DEFAULT


def _kg_query_model() -> str:
    return os.environ.get("NOX_KG_QUERY_MODEL", _KG_QUERY_MODEL_DEFAULT)


def _rrf_score(rank: int, k: int | None = None) -> float:
    if k is None:
        k = _rrf_k()
    return 1.0 / (k + rank)


def _hybrid_single_pass(
    query: str,
    k_fetch: int,
    genai,
) -> dict[str, float]:
    """Run a single FTS5+dense+RRF pass for `query`.

    Returns a per-chunk RRF score dict (chunk_id → score). Used both for
    the baseline hybrid path and for each query-rewrite variant pass.
    `k_fetch` controls how deep each leg fetches (we use k * 3 = 30 by
    default to give RRF good fusion material).
    """
    global _hybrid_con
    assert _hybrid_con is not None

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
            (fq, k_fetch),
        ).fetchall()
    except sqlite3.OperationalError:
        pass

    # --- Dense leg ---
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
            (q_bytes, k_fetch),
        ).fetchall()
    except Exception as e:
        print(f"[nox_mem/hybrid] dense search error: {e}", file=sys.stderr)

    # --- RRF fusion (within this single pass) ---
    scores: dict[str, float] = {}
    for rank, (chunk_id, _) in enumerate(fts_rows, 1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + _rrf_score(rank)
    for rank, (chunk_id, _) in enumerate(dense_rows, 1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + _rrf_score(rank)
    return scores


def _search_hybrid_local(query: str, k: int) -> list[dict]:
    """RRF fusion of FTS5 + Gemini dense search on local hybrid DB.

    When NOX_QUERY_REWRITE=1, additionally generates N semantic variants
    of the query via Gemini Flash Lite and merges their RRF scores into
    the result set. See `_rewrite_query`.

    Path E+F+H (mission 2026-05-24) — opt-in via env flags:
      F: NOX_RRF_K=<int>           # override RRF k (default 60)
      H: NOX_TOP_K_EXPAND=<int>    # internal candidate pool size; final cut
                                   # happens after KG rerank. Default 30 ≡ k*3
                                   # at k=10 so baseline is byte-identical.
      E: NOX_RETRIEVAL_KG=1        # detect query entities → multiply scores
                                   # of chunks sharing 1-hop KG neighbours.
                                   # Requires kg_entities/kg_relations/
                                   # kg_chunk_entities tables in the DB.
    """
    global _hybrid_con

    if _hybrid_con is None:
        raise RuntimeError("hybrid DB not initialised — call setup() first")

    _load_sqlite_vec_ext(_hybrid_con)
    genai = _get_genai()

    # H: candidate pool size. Each leg (FTS5, dense) fetches `k_fetch`; the
    # union is then re-ranked. Baseline k=10 → k_fetch=30 (== k*3 legacy).
    k_fetch = _top_k_expand()

    # --- Baseline pass (original query) ---
    scores: dict[str, float] = _hybrid_single_pass(query, k_fetch, genai)

    # --- Query rewrite layer (opt-in) ---
    if _query_rewrite_enabled():
        variants = _rewrite_query(query)
        for variant in variants:
            v = (variant or "").strip()
            if not v or v.lower() == query.strip().lower():
                continue
            try:
                variant_scores = _hybrid_single_pass(v, k_fetch, genai)
            except Exception as e:
                print(
                    f"[nox_mem/hybrid] variant search error: {e}",
                    file=sys.stderr,
                )
                continue
            for chunk_id, s in variant_scores.items():
                scores[chunk_id] = scores.get(chunk_id, 0.0) + s

    # --- E: KG traversal boost (opt-in) -----------------------------------
    # Multiply per-chunk RRF score by NOX_KG_BOOST if the chunk is linked
    # (via kg_chunk_entities) to any entity in the 1-hop KG neighbourhood
    # of the query's entities. The boost is applied ONCE per chunk even if
    # multiple matches — this preserves the RRF order amongst non-matched
    # candidates while lifting matched ones uniformly. Avoids the
    # temporal-spike PATCH 2 self-reinforcing pattern (G regressed -32%
    # via stacked anchor inference, memory
    # [[temporal-spike-patched-regressed-2026-05-20]]).
    if _kg_retrieval_enabled() and scores:
        try:
            query_ents = _extract_query_entities(query)
            related_entity_ids = _kg_one_hop(query_ents)
            if related_entity_ids:
                boosted = _kg_boost_factor()
                candidate_ids = list(scores.keys())
                matched_chunks = _kg_chunks_for_entities(
                    candidate_ids, related_entity_ids
                )
                for cid in matched_chunks:
                    if cid in scores:
                        scores[cid] *= boosted
        except Exception as e:
            print(f"[nox_mem/hybrid] KG boost error: {e}", file=sys.stderr)

    # Final cut to user's requested k (after all boosts applied).
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
# Path E — KG traversal helpers
# ---------------------------------------------------------------------------


def _extract_query_entities(query: str) -> list[str]:
    """Extract canonical entity names from `query` via Gemini Flash Lite.

    Returns lowercase canonical strings (matching kg_entities lower(name)).
    Cached per-process by exact query string. On any error returns [].
    """
    global _kg_query_calls, _kg_query_errors

    q_clean = (query or "").strip()
    if not q_clean:
        return []

    if q_clean in _kg_query_entities_cache:
        return _kg_query_entities_cache[q_clean]

    try:
        import requests
    except ImportError:
        _kg_query_entities_cache[q_clean] = []
        return []

    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        _kg_query_entities_cache[q_clean] = []
        return []

    url = _REWRITE_ENDPOINT.format(model=_kg_query_model())
    payload = {
        "contents": [
            {"parts": [{"text": _KG_ENTITY_EXTRACTION_PROMPT.format(q=q_clean)}]}
        ],
        "generationConfig": {
            "temperature": 0.0,
            "topP": 0.95,
            "maxOutputTokens": 128,
            "responseMimeType": "application/json",
        },
    }
    try:
        _kg_query_calls += 1
        resp = requests.post(
            url,
            params={"key": key},
            json=payload,
            timeout=_KG_QUERY_TIMEOUT_S,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            _kg_query_entities_cache[q_clean] = []
            return []
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts)
        names = _parse_rewrite_response(text, 6)  # reuse robust JSON-array parser
        out = []
        for n in names:
            n = n.strip().lower()
            if n and len(n) >= 2:
                out.append(n)
        _kg_query_entities_cache[q_clean] = out
        return out
    except Exception as e:
        _kg_query_errors += 1
        if _kg_query_errors <= 5:
            msg = str(e)
            msg = re.sub(r"key=[A-Za-z0-9_\-]+", "key=<REDACTED>", msg)
            msg = re.sub(r"AIza[A-Za-z0-9_\-]{10,}", "AIza<REDACTED>", msg)
            print(
                f"[nox_mem/kg] query entity extract error (#{_kg_query_errors}): "
                f"{type(e).__name__}: {msg}",
                file=sys.stderr,
            )
        _kg_query_entities_cache[q_clean] = []
        return []


def _kg_one_hop(entity_names: list[str]) -> set[int]:
    """Resolve `entity_names` → entity IDs → 1-hop neighbours.

    Returns the union of {seed entity IDs} ∪ {neighbours via kg_relations}.
    Returns empty set if no seeds match or KG tables missing.
    """
    global _hybrid_con
    assert _hybrid_con is not None

    if not entity_names:
        return set()

    # Step 1: resolve seeds (case-insensitive name match)
    seed_ids: set[int] = set()
    try:
        placeholders = ",".join("?" for _ in entity_names)
        rows = _hybrid_con.execute(
            f"SELECT id FROM kg_entities WHERE LOWER(name) IN ({placeholders})",
            tuple(n.lower() for n in entity_names),
        ).fetchall()
        for (eid,) in rows:
            seed_ids.add(eid)
    except sqlite3.OperationalError:
        return set()

    if not seed_ids:
        return set()

    # Step 2: 1-hop neighbours via kg_relations
    seed_list = list(seed_ids)
    p2 = ",".join("?" for _ in seed_list)
    try:
        neighbour_rows = _hybrid_con.execute(
            f"SELECT DISTINCT target_id FROM kg_relations WHERE source_id IN ({p2}) "
            f"UNION "
            f"SELECT DISTINCT source_id FROM kg_relations WHERE target_id IN ({p2})",
            tuple(seed_list) + tuple(seed_list),
        ).fetchall()
        for (eid,) in neighbour_rows:
            seed_ids.add(eid)
    except sqlite3.OperationalError:
        pass

    return seed_ids


def _kg_chunks_for_entities(
    candidate_chunk_ids: list[str],
    entity_ids: set[int],
) -> set[str]:
    """Return subset of `candidate_chunk_ids` linked to any of `entity_ids`."""
    global _hybrid_con
    assert _hybrid_con is not None

    if not candidate_chunk_ids or not entity_ids:
        return set()

    # SQLite has a default 999-parameter limit; chunk-up if needed.
    matched: set[str] = set()
    eid_list = list(entity_ids)
    cids = list(candidate_chunk_ids)
    CHUNK = 400  # keep total params well under 999

    for i in range(0, len(cids), CHUNK):
        batch = cids[i : i + CHUNK]
        p_ent = ",".join("?" for _ in eid_list)
        p_ck = ",".join("?" for _ in batch)
        try:
            rows = _hybrid_con.execute(
                f"SELECT DISTINCT chunk_id FROM kg_chunk_entities "
                f"WHERE entity_id IN ({p_ent}) AND chunk_id IN ({p_ck})",
                tuple(eid_list) + tuple(batch),
            ).fetchall()
            for (cid,) in rows:
                matched.add(cid)
        except sqlite3.OperationalError:
            continue
    return matched


def get_kg_stats() -> dict:
    """Return KG-layer counters for cost auditing."""
    return {
        "enabled": _kg_retrieval_enabled(),
        "boost_factor": _kg_boost_factor(),
        "model": _kg_query_model(),
        "calls": _kg_query_calls,
        "errors": _kg_query_errors,
        "cache_entries": len(_kg_query_entities_cache),
    }


# ---------------------------------------------------------------------------
# Query rewrite layer — Gemini Flash Lite
# ---------------------------------------------------------------------------


def _query_rewrite_enabled() -> bool:
    raw = os.environ.get("NOX_QUERY_REWRITE", "0").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _rewrite_model() -> str:
    return os.environ.get("NOX_QUERY_REWRITE_MODEL", _REWRITE_MODEL_DEFAULT)


def _rewrite_n() -> int:
    raw = os.environ.get("NOX_QUERY_REWRITE_N", "").strip()
    if raw.isdigit():
        n = int(raw)
        return max(1, min(n, 6))  # safety cap 1..6
    return _REWRITE_N_DEFAULT


_REWRITE_PROMPT = (
    "You expand user queries for memory retrieval. Given the user query "
    "below, output exactly {n} semantically related variants. Variants "
    "should rephrase, expand acronyms, swap synonyms, or surface implicit "
    "entities — but stay faithful to the original intent. Do NOT answer "
    "the question. Output JSON only: an array of {n} strings.\n\n"
    "User query: {q}\n\n"
    "Output JSON array:"
)


def _parse_rewrite_response(raw: str, expected_n: int) -> list[str]:
    """Robustly parse JSON array from LLM response (with fallbacks)."""
    if not raw:
        return []
    # Strip code fences if model wraps output
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    # Try direct JSON parse first
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()][:expected_n]
    except json.JSONDecodeError:
        pass
    # Fallback: regex-extract first JSON array in the text
    m = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if m:
        try:
            parsed = json.loads(m.group(0))
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()][:expected_n]
        except json.JSONDecodeError:
            pass
    # Last-ditch: newline-split. Require at least one alphabetic char per line
    # so pure-punctuation noise (e.g. "?????") is rejected instead of being
    # treated as a "variant" — punctuation-only queries would hit the FTS
    # sanitizer and produce empty searches anyway.
    lines = [
        ln.strip(" \"',-*")
        for ln in cleaned.splitlines()
        if ln.strip() and not ln.strip().startswith(("{", "}", "[", "]"))
    ]
    return [ln for ln in lines if ln and re.search(r"[A-Za-z]", ln)][:expected_n]


def _rewrite_query(query: str) -> list[str]:
    """Generate N semantic variants of `query` via Gemini Flash Lite.

    Cached per-process by exact query string. Returns at most N variants.
    On any error (network, parse, auth) returns an empty list — caller
    treats this as graceful degradation to baseline hybrid.
    """
    global _rewrite_calls, _rewrite_errors

    n = _rewrite_n()
    q_clean = query.strip()
    if not q_clean:
        return []

    cache_key = f"{_rewrite_model()}::{n}::{q_clean}"
    cached = _rewrite_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        import requests
    except ImportError:
        print(
            "[nox_mem/rewrite] `requests` not installed — disabling rewrite",
            file=sys.stderr,
        )
        _rewrite_cache[cache_key] = []
        return []

    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        _rewrite_cache[cache_key] = []
        return []

    url = _REWRITE_ENDPOINT.format(model=_rewrite_model())
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": _REWRITE_PROMPT.format(q=q_clean, n=n)}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.4,
            "topP": 0.95,
            "maxOutputTokens": 256,
            "responseMimeType": "application/json",
        },
    }
    try:
        _rewrite_calls += 1
        resp = requests.post(
            url,
            params={"key": key},
            json=payload,
            timeout=_REWRITE_TIMEOUT_S,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            _rewrite_cache[cache_key] = []
            return []
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts)
        variants = _parse_rewrite_response(text, n)
        # De-duplicate against original query (case-insensitive)
        out: list[str] = []
        seen = {q_clean.lower()}
        for v in variants:
            vl = v.lower()
            if vl in seen:
                continue
            seen.add(vl)
            out.append(v)
        _rewrite_cache[cache_key] = out
        return out
    except Exception as e:
        _rewrite_errors += 1
        if _rewrite_errors <= 5:
            # CRITICAL: requests.HTTPError.__str__ embeds the full request URL,
            # which contains the `?key=AIza...` query param. Redact aggressively
            # before printing so smoke logs / CI artefacts never leak the key.
            msg = str(e)
            msg = re.sub(r"key=[A-Za-z0-9_\-]+", "key=<REDACTED>", msg)
            msg = re.sub(r"AIza[A-Za-z0-9_\-]{10,}", "AIza<REDACTED>", msg)
            print(
                f"[nox_mem/rewrite] error (#{_rewrite_errors}): {type(e).__name__}: {msg}",
                file=sys.stderr,
            )
        _rewrite_cache[cache_key] = []
        return []


def get_rewrite_stats() -> dict:
    """Return rewrite-layer counters for cost auditing."""
    return {
        "enabled": _query_rewrite_enabled(),
        "model": _rewrite_model(),
        "variants_per_query": _rewrite_n(),
        "calls": _rewrite_calls,
        "errors": _rewrite_errors,
        "cache_entries": len(_rewrite_cache),
    }


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
        rewrite_on = _query_rewrite_enabled()
        rewrite_note = (
            f" + query-rewrite ON ({_rewrite_model()}, N={_rewrite_n()})"
            if rewrite_on else ""
        )
        return {
            "ok": has_key,
            "error": None if has_key else "GEMINI_API_KEY not set",
            "version": VERSION_PIN,
            "notes": (
                f"hybrid mode — FTS5+dense+RRF, DB at {db_path}. "
                f"NOX_MEM_INGEST_LIMIT={limit}.{rewrite_note} "
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
