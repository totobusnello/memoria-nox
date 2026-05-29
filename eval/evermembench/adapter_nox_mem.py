"""
nox-mem Adapter for EverMemBench — Phase F + Phase KG (Lab Q1 #4, 2026-05-29).

Connects nox-mem (CLI ingest + HTTP search API) to the EverMemBench
evaluation harness.

Phase A (PR #363, batch 004 = 56.07%) used flat-paragraph markdown with
inline `[Group][Speaker][Time]` prefixes. The nox-mem segmenter coalesced
~9 messages per chunk (10,222 msgs -> 1,140 chunks), diluting per-message
metadata. Multi-hop scored 4% / Temporal 10%.

Phase B introduced H2-per-message chunks + structured prefix + day-group
digests. Phase D added a search-time over-fetch (top_k=20 from API) that
won the 5-batch aggregate at 62.22% (beat MemOS 59.27%). But multi-hop
remained weak (5.22% 5-batch avg).

Phase F (this version) attacks the multi-hop bottleneck with cross-encoder
reranking on top of Phase D's retrieval. Pipeline:
  1. Request top-50 from nox-mem hybrid search (over-fetch).
  2. Pass (query, chunk_text) pairs through BAAI/bge-reranker-v2-m3
     CrossEncoder which sees the full context together and can score
     "bridge facts" that bi-encoder retrieval misses.
  3. Re-sort by rerank score, take top_k for the harness.

Cross-encoder rerank adds local compute cost (~50-300ms per query on CPU,
faster on GPU). For end-user latency-sensitive paths this would be a
trade-off; for offline benchmark eval it is acceptable.

Phase KG (Lab Q1 #4, 2026-05-29) — KG path retrieval (Approach A, 1-hop):
  1. Extract candidate entity mentions from the query via regex against
     `kg_entities.name` (cheapest path per spec §3.A).
  2. Look up 1-hop neighbors via SQL JOIN over `kg_relations` (FK ids,
     not inline strings — per [[kg-relations-uses-fk-ids-not-inline-strings]]).
  3. Use `kg_relations.evidence_chunk_id` (direct FK to chunks) to find
     "evidence chunks" for the neighbor entities — much cleaner than
     `source_path LIKE '%slug%'` matching.
  4. Apply ADDITIVE score delta to evidence chunks already present in
     the hybrid search top-N. Per memoria-nox rule §5 (boost multiplicativo
     empilhável é veneno), the delta is added to RRF score, not multiplied.

Phase MAP (Lab Q1 #2, 2026-05-29) — MA-protection via bypass-entity (Approach A):
  Cross-encoder rerank (Phase G / Phase F) causes a structural -3 to -4pp
  regression in Memory Awareness dimensions (MA_C / MA_P / MA_U) because the
  reranker scores chunks by query-chunk semantic relevance and downgrades
  entity-formatted chunks (compiled/frontmatter) that *encode the answer*
  without lexically overlapping the query.

  Approach A — bypass-entity:
    1. Partition the pre-rerank candidate pool into:
       - Set E (entity chunks): section IN ('compiled', 'frontmatter')
       - Set R (regular chunks): all others (NULL section, timeline, etc.)
    2. Score only Set R via cross-encoder. Set E retains bi-encoder rank
       (which already respects section_boost from RRF).
    3. Merge so that entity chunks survive at their original bi-encoder
       positions; reranked regular chunks fill the remaining slots, capped
       at top_k.

  Default OFF — opt-in via NOX_MA_PROTECTION_ENABLED=1 (env override on top
  of any mode) OR by selecting NOX_ADAPTER_MODE=phaseMAP (default-on for
  that mode + reranker auto-enabled).

Modes:
    NOX_ADAPTER_MODE=baseline  -> PR #363 flat-paragraph ingest format
    NOX_ADAPTER_MODE=phaseB    -> H2-per-message + digest (default)
    NOX_ADAPTER_MODE=phaseF    -> phaseB ingest + cross-encoder rerank in search
    NOX_ADAPTER_MODE=phaseKG   -> phaseB ingest + KG 1-hop entity boost in search
    NOX_ADAPTER_MODE=phaseMAP  -> phaseB ingest + cross-encoder rerank + MA protection
                                  (Approach A: bypass entity chunks from rerank)

Environment variables:
    NOX_API_BASE              — nox-mem API base URL (default: http://127.0.0.1:18802)
    NOX_DB_PATH               — per-batch DB path override (REQUIRED for isolation)
    NOX_MEM_BIN               — path to nox-mem CLI binary (default: "nox-mem" on PATH)
    NOX_ADAPTER_MODE          — "phaseB" (default) / "baseline" / "phaseF" / "phaseKG" / "phaseMAP"
    NOX_RERANKER_ENABLED      — "1" to force cross-encoder rerank in phaseF
    NOX_RERANKER_MODEL        — HF model id (default: BAAI/bge-reranker-v2-m3)
    NOX_RERANKER_OVERFETCH    — int top-N to pull from API before rerank (default: 50)
    NOX_RERANKER_BATCH_SIZE   — CrossEncoder.predict batch_size (default: 32)
    NOX_KG_PATH_ENABLED       — "1" to force KG 1-hop boost (env override on any mode)
    NOX_KG_BOOST_MAGNITUDE    — float, additive delta applied to RRF score (default: 0.05)
    NOX_KG_DIRECT_MULTIPLIER  — float, multiplier of base delta for chunks containing
                                directly-mentioned entities (default: 1.5)
    NOX_KG_MAX_NEIGHBORS      — int, max neighbors per mentioned entity (default: 20)
    NOX_KG_MIN_NAME_LEN       — int, minimum entity name length to use in regex
                                extraction (default: 3) — avoids matching common tokens
                                like "a", "of", "is" that may be entity names in noisy KGs.
    NOX_MA_PROTECTION_ENABLED — "1" to force MA-protection bypass-entity (env override
                                on top of any mode). Default OFF (Phase G behavior).
                                When ON, cross-encoder skips chunks with
                                section IN ('compiled', 'frontmatter') — they keep
                                bi-encoder rank to prevent MA dim regression.
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

# ---------------------------------------------------------------------------
# Phase B chunking strategy (2026-05-28)
# ---------------------------------------------------------------------------
# Per-message H2 block. Metadata in header + structured lead lines so both
# BM25 (FTS5) and Gemini-embedding retrieval bind to speaker / group / time
# / preceding context.
PHASEB_MESSAGE_BLOCK = (
    "## [{time} | {group} | {speaker}]\n"
    "speaker: {speaker}\n"
    "group: {group}\n"
    "date: {date}\n"
    "time: {time}\n"
    "context: {context}\n"
    "content: {content}\n"
)

# Daily group rollup -- emitted once per (date, group) tuple after all
# messages of that day-group are written. Helps temporal queries.
PHASEB_DAY_GROUP_ROLLUP = (
    "## Day {date} -- {group} digest\n"
    "group: {group}\n"
    "date: {date}\n"
    "participants: {participants}\n"
    "message_count: {message_count}\n"
    "summary: Conversation on {date} in {group} between {participants_short}. "
    "First line: {first_line}\n"
)

# Legacy baseline template (kept for ablation fallback via NOX_ADAPTER_MODE=baseline)
MESSAGE_TEMPLATE = "[Group: {group}][Speaker: {speaker}][Time: {time}] {content}"

# How many messages per batched ingest subprocess call.
DEFAULT_INGEST_BATCH_SIZE = 50

# Timeout (seconds) per `nox-mem ingest` subprocess call.
INGEST_SUBPROCESS_TIMEOUT = 180

# Adapter mode default.
DEFAULT_ADAPTER_MODE = "phaseB"

# How many preceding turns (same group) to embed as "context" per chunk.
PHASEB_CONTEXT_WINDOW = 2

# Phase F cross-encoder reranker defaults.
DEFAULT_RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
DEFAULT_RERANKER_OVERFETCH = 50
DEFAULT_RERANKER_BATCH_SIZE = 32
DEFAULT_RERANKER_MAX_LENGTH = 512

# Phase KG (Lab Q1 #4) — KG 1-hop boost defaults.
#
# BASE_DELTA = 0.05 per spec §8.6 — scaled to typical RRF score range (0.01-0.1).
# DIRECT_MULTIPLIER = 1.5 → directly-mentioned entities get 1.5× neighbor boost
# per spec §3.A. MAX_NEIGHBORS prevents pathological cases where a high-degree
# entity (e.g. a hub person in the chat) floods the boost candidate set.
# MIN_NAME_LEN = 3 avoids regex false positives on short tokens like "i", "of".
DEFAULT_KG_BOOST_MAGNITUDE = 0.05
DEFAULT_KG_DIRECT_MULTIPLIER = 1.5
DEFAULT_KG_MAX_NEIGHBORS = 20
DEFAULT_KG_MIN_NAME_LEN = 3
DEFAULT_KG_OVERFETCH = 50  # pull top-50 from API so KG can re-rank within

# Phase MAP (Lab Q1 #2) — MA-protection bypass-entity defaults.
#
# Per spec §6.1 recommendation: use `section IN ('compiled', 'frontmatter')`
# as the entity-chunk identity signal — explicit semantic marker, avoids float
# comparison on section_boost, more readable in logs. Schema v10 (2026-04-23)
# guarantees the column is populated when ingest goes through
# `ingestEntityFile` (memory/entities/<type>/<slug>.md format). Chat-corpus
# chunks (EverMemBench dataset/<batch>/dialogue.json) have section=NULL and
# are therefore in Set R (regular) — always reranked.
ENTITY_SECTION_NAMES = frozenset({"compiled", "frontmatter"})


# ---------------------------------------------------------------------------
# Reranker singleton loader
# ---------------------------------------------------------------------------
#
# Cached so each Python process loads the model once (~600MB on disk, ~2-3GB
# resident). Lazy: only imported when phaseF actually runs.
# Returns (model_or_None, error_or_None). On failure (missing package,
# download error, OOM), error is a string and the caller falls back to
# non-reranked results gracefully.
# ---------------------------------------------------------------------------
import functools as _functools  # noqa: E402  — local-only alias


# ---------------------------------------------------------------------------
# Phase MAP (Lab Q1 #2) — merge helper for bypass-entity
# ---------------------------------------------------------------------------
#
# Given:
#   entity_indexed:    [(orig_idx, cand), ...]  Set E in original bi-encoder order
#   reranked_regular:  [(orig_idx, cand), ...]  Set R in cross-encoder rank order
#   total_slots:       int (typically len(candidates) pre-truncate, then top_k cap applied later)
#
# Produce a merged list where:
#   1. Each entity chunk lands at its *original* bi-encoder position (orig_idx).
#   2. Reranked regular chunks fill the remaining slots in rerank order
#      (rank 0 = highest rerank score gets the lowest still-empty position).
#   3. If entity_indexed is so large it would overflow total_slots, we take
#      the first total_slots entities (lowest orig_idx) and drop reranked Set R
#      entirely — RRF already respects section_boost for them.
#
# Returned list contains candidate tuples (chunk_text, item_dict), preserving
# the original tuple shape the rest of the adapter expects.
def _merge_preserving_entity_positions(
    entity_indexed: List[Tuple[int, Tuple[str, Dict[str, Any]]]],
    reranked_regular: List[Tuple[int, Tuple[str, Dict[str, Any]]]],
    total_slots: int,
) -> List[Tuple[str, Dict[str, Any]]]:
    if total_slots <= 0:
        return []

    # Build empty slot list and place entities at original positions.
    merged: List[Optional[Tuple[str, Dict[str, Any]]]] = [None] * total_slots
    placed_entity = 0
    for orig_idx, cand in entity_indexed:
        if orig_idx < total_slots:
            merged[orig_idx] = cand
            placed_entity += 1
        # Entities with orig_idx >= total_slots are dropped — there's no slot
        # for them. Should not happen given total_slots = len(candidates) at
        # merge time, but defended against off-by-one.

    # Fill remaining empty slots with reranked regular in rerank order.
    reranked_iter = iter(reranked_regular)
    for slot in range(total_slots):
        if merged[slot] is None:
            try:
                _orig, cand = next(reranked_iter)
                merged[slot] = cand
            except StopIteration:
                # Set R exhausted before all slots filled — leave empty slots
                # behind. We compact below.
                break

    # Compact: drop any trailing None slots (happens when reranked < non-entity gap).
    return [c for c in merged if c is not None]


@_functools.lru_cache(maxsize=1)
def _load_reranker(model_id: str, max_length: int) -> Tuple[Any, Optional[str]]:
    try:
        from sentence_transformers import CrossEncoder  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        return None, f"sentence_transformers import failed: {type(exc).__name__}: {exc}"

    try:
        model = CrossEncoder(model_id, max_length=max_length)
    except Exception as exc:  # noqa: BLE001
        return None, f"CrossEncoder({model_id}) load failed: {type(exc).__name__}: {exc}"

    return model, None


# ---------------------------------------------------------------------------
# Phase KG (Lab Q1 #4) — KG path retrieval helpers
# ---------------------------------------------------------------------------
#
# These helpers run direct SQLite queries against the same DB the api-server
# is using. They are read-only (SELECT only) and use the FK schema documented
# in `[[kg-relations-uses-fk-ids-not-inline-strings]]`:
#
#   kg_entities (id, name, entity_type, mention_count, attributes, ...)
#   kg_relations (id, source_entity_id, relation_type, target_entity_id,
#                 evidence_chunk_id, confidence, ...)
#
# Important: SQLite WAL mode + concurrent readers are SAFE — the api-server
# holds its own connection, and our read-only connection sees a snapshot.
# We open and cache a single read-only connection per (db_path, process).


@_functools.lru_cache(maxsize=4)
def _kg_open_db(db_path: str) -> Tuple[Any, Optional[str]]:
    """Open a read-only SQLite connection to the KG DB. Cached per path."""
    import sqlite3 as _sqlite3
    try:
        # URI mode + mode=ro = read-only, will not interfere with api-server.
        conn = _sqlite3.connect(
            f"file:{db_path}?mode=ro",
            uri=True,
            check_same_thread=False,
            timeout=5.0,
        )
        # Confirm KG tables exist
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('kg_entities','kg_relations')"
        ).fetchall()
        if len(row) < 2:
            return None, f"KG tables missing in {db_path} (found {[r[0] for r in row]})"
    except Exception as exc:  # noqa: BLE001
        return None, f"sqlite3.connect failed: {type(exc).__name__}: {exc}"
    return conn, None


@_functools.lru_cache(maxsize=8)
def _kg_load_entity_names(db_path: str, min_name_len: int) -> Tuple[Tuple[Tuple[int, str], ...], Optional[str]]:
    """Load all (id, name) pairs from kg_entities with len(name) >= min_name_len.

    Cached as tuple-of-tuples so the lru_cache key is hashable. Names are
    lowercased here once so per-query regex matching is cheap.
    """
    conn, err = _kg_open_db(db_path)
    if err is not None or conn is None:
        return (), err

    try:
        rows = conn.execute(
            "SELECT id, LOWER(name) FROM kg_entities "
            "WHERE LENGTH(name) >= ? "
            "ORDER BY mention_count DESC",
            (min_name_len,),
        ).fetchall()
    except Exception as exc:  # noqa: BLE001
        return (), f"kg_entities query failed: {type(exc).__name__}: {exc}"

    return tuple((int(r[0]), str(r[1])) for r in rows), None


def _kg_extract_query_entities(
    query: str,
    entity_pool: Tuple[Tuple[int, str], ...],
    max_entities: int = 10,
) -> List[Tuple[int, str]]:
    """Regex-extract entity mentions from query against KG entity pool.

    Approach A (cheapest): substring match. Lowercases query once, then
    iterates entity_pool (already lowercased) checking presence. Returns
    list of (entity_id, entity_name) tuples in pool order (which is
    mention_count DESC) up to `max_entities`.

    Why substring (not word boundary): EverMemBench entity names are
    multi-token person/group names (e.g. "Weihua Zhang", "Group 1") and
    Unicode word boundary regex `\b` is unreliable in PT-BR / accented
    contexts — per [[js-regex-unicode-word-boundary-fails]], same caveat
    applies to Python `re` with `\b`. We use substring containment with a
    `min_name_len` >= 3 filter to control false positives.
    """
    import re as _re

    q_lower = query.lower()
    matched: List[Tuple[int, str]] = []
    seen: set = set()
    for ent_id, ent_name_lc in entity_pool:
        if ent_id in seen:
            continue
        # Whole-word-ish match: name surrounded by non-alphanumeric or string edges.
        # This is more robust than naive `in` (e.g. avoids matching "al" inside "alpha").
        # We still avoid `\b` because non-ASCII unicode breaks JS regex; in Python
        # `re.UNICODE` works but we prefer explicit boundary chars for portability.
        pattern = r'(?:^|[^a-z0-9])' + _re.escape(ent_name_lc) + r'(?:$|[^a-z0-9])'
        if _re.search(pattern, q_lower):
            matched.append((ent_id, ent_name_lc))
            seen.add(ent_id)
            if len(matched) >= max_entities:
                break
    return matched


def _kg_get_1hop_neighbors(
    db_path: str,
    entity_ids: List[int],
    max_neighbors_per_entity: int,
) -> List[Tuple[int, int, float, int]]:
    """Return 1-hop neighbors of given entity_ids.

    Returns list of tuples: (neighbor_entity_id, evidence_chunk_id, confidence,
    source_entity_id). evidence_chunk_id may be 0 if not set on the relation
    (we filter those out at boost time — they don't contribute to chunk boost).

    Walks both directions: relations where source IS the seed AND relations
    where target IS the seed. The "neighbor" is always the other end of the
    edge from the seed.

    Per [[kg-relations-uses-fk-ids-not-inline-strings]]: use FK ids, not names.
    """
    conn, err = _kg_open_db(db_path)
    if err is not None or conn is None or not entity_ids:
        return []

    placeholders = ",".join("?" * len(entity_ids))
    # Outbound edges: seed = source_entity_id, neighbor = target_entity_id
    # Inbound edges:  seed = target_entity_id, neighbor = source_entity_id
    sql = f"""
        SELECT target_entity_id AS neighbor, evidence_chunk_id, confidence, source_entity_id
        FROM kg_relations
        WHERE source_entity_id IN ({placeholders})
          AND target_entity_id NOT IN ({placeholders})
          AND target_entity_id IS NOT NULL
        UNION ALL
        SELECT source_entity_id AS neighbor, evidence_chunk_id, confidence, target_entity_id
        FROM kg_relations
        WHERE target_entity_id IN ({placeholders})
          AND source_entity_id NOT IN ({placeholders})
          AND source_entity_id IS NOT NULL
    """
    try:
        rows = conn.execute(sql, entity_ids * 4).fetchall()
    except Exception:  # noqa: BLE001
        return []
    # Cap per-seed neighbor count to avoid hub flooding
    by_seed: Dict[int, List[Tuple[int, int, float, int]]] = {}
    for n, ev, conf, seed in rows:
        bucket = by_seed.setdefault(int(seed), [])
        if len(bucket) < max_neighbors_per_entity:
            bucket.append((int(n), int(ev or 0), float(conf or 0.0), int(seed)))
    out: List[Tuple[int, int, float, int]] = []
    for bucket in by_seed.values():
        out.extend(bucket)
    return out


def _kg_get_direct_chunk_ids(
    db_path: str,
    entity_ids: List[int],
) -> set:
    """Return chunk_ids that are direct evidence for the given (directly-mentioned) entities.

    A chunk is "direct evidence" for an entity if any relation where the entity
    appears as source OR target lists that chunk in evidence_chunk_id.
    """
    conn, err = _kg_open_db(db_path)
    if err is not None or conn is None or not entity_ids:
        return set()

    placeholders = ",".join("?" * len(entity_ids))
    sql = f"""
        SELECT DISTINCT evidence_chunk_id FROM kg_relations
        WHERE (source_entity_id IN ({placeholders}) OR target_entity_id IN ({placeholders}))
          AND evidence_chunk_id IS NOT NULL
    """
    try:
        rows = conn.execute(sql, entity_ids * 2).fetchall()
    except Exception:  # noqa: BLE001
        return set()
    return {int(r[0]) for r in rows if r[0]}


class NoxMemAdapter(BaseAdapter):
    """
    nox-mem adapter for EverMemBench multi-person group chat evaluation.

    Add stage:
        Writes group-chat messages to a temp markdown file (Phase B format
        when NOX_ADAPTER_MODE != "baseline"), then invokes `nox-mem ingest`
        via subprocess. Subprocess inherits NOX_DB_PATH for isolation.

    Search stage:
        Calls POST /api/search with the QA question text. The HTTP API must
        be started against the SAME NOX_DB_PATH that Add ingested into.

    Config YAML example (nox_mem.yaml):
    ```yaml
    name: "nox_mem"
    api_base: "${NOX_API_BASE}"
    nox_mem_bin: "${NOX_MEM_BIN}"
    search_top_k: 10
    search_timeout: 30
    ingest_batch_size: 50
    ingest_delay_ms: 0
    adapter_mode: "phaseB"
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
        self.adapter_mode = (
            config.get("adapter_mode", "")
            or os.environ.get("NOX_ADAPTER_MODE", DEFAULT_ADAPTER_MODE)
        )
        self.context_window = int(
            config.get("phaseb_context_window", PHASEB_CONTEXT_WINDOW)
        )

        # Phase F cross-encoder rerank config (only consumed when
        # adapter_mode == "phaseF" AND NOX_RERANKER_ENABLED resolves truthy).
        self.reranker_model_id = config.get("reranker_model", "") or os.environ.get(
            "NOX_RERANKER_MODEL", DEFAULT_RERANKER_MODEL
        )
        self.reranker_overfetch = int(
            config.get("reranker_overfetch", 0)
            or os.environ.get("NOX_RERANKER_OVERFETCH", "")
            or DEFAULT_RERANKER_OVERFETCH
        )
        self.reranker_batch_size = int(
            config.get("reranker_batch_size", 0)
            or os.environ.get("NOX_RERANKER_BATCH_SIZE", "")
            or DEFAULT_RERANKER_BATCH_SIZE
        )
        self.reranker_max_length = int(
            config.get("reranker_max_length", 0)
            or DEFAULT_RERANKER_MAX_LENGTH
        )
        # Reranker is enabled either by being in phaseF/phaseMAP mode
        # (default-on for those modes) OR by explicit env override on top of
        # any other mode.
        # Phase MAP needs rerank ON by definition — bypass-entity only makes
        # sense when the cross-encoder is actually running.
        env_enable = os.environ.get("NOX_RERANKER_ENABLED", "").strip().lower()
        env_enable_truthy = env_enable in ("1", "true", "yes", "on")
        env_enable_falsy = env_enable in ("0", "false", "no", "off")
        if env_enable_falsy:
            self.reranker_enabled = False
        elif env_enable_truthy:
            self.reranker_enabled = True
        else:
            self.reranker_enabled = (
                self.adapter_mode in ("phaseF", "phaseMAP")
            )

        # Phase MAP (Lab Q1 #2) — MA-protection: entity chunks bypass rerank.
        # Default-on for phaseMAP mode + explicit env override
        # (NOX_MA_PROTECTION_ENABLED=1) on top of any other mode. Default OFF
        # for phaseF / phaseB so Phase G behavior is preserved unchanged.
        env_map = os.environ.get("NOX_MA_PROTECTION_ENABLED", "").strip().lower()
        env_map_truthy = env_map in ("1", "true", "yes", "on")
        env_map_falsy = env_map in ("0", "false", "no", "off")
        if env_map_falsy:
            self.ma_protection_enabled = False
        elif env_map_truthy:
            self.ma_protection_enabled = True
        else:
            self.ma_protection_enabled = (self.adapter_mode == "phaseMAP")

        # Phase KG (Lab Q1 #4) — entity 1-hop boost config.
        # Enabled by phaseKG mode (default-on for that mode) OR by explicit
        # NOX_KG_PATH_ENABLED env override on top of any other mode.
        env_kg = os.environ.get("NOX_KG_PATH_ENABLED", "").strip().lower()
        env_kg_truthy = env_kg in ("1", "true", "yes", "on")
        env_kg_falsy = env_kg in ("0", "false", "no", "off")
        if env_kg_falsy:
            self.kg_enabled = False
        elif env_kg_truthy:
            self.kg_enabled = True
        else:
            self.kg_enabled = (self.adapter_mode == "phaseKG")

        self.kg_boost_magnitude = float(
            os.environ.get("NOX_KG_BOOST_MAGNITUDE", "")
            or DEFAULT_KG_BOOST_MAGNITUDE
        )
        self.kg_direct_multiplier = float(
            os.environ.get("NOX_KG_DIRECT_MULTIPLIER", "")
            or DEFAULT_KG_DIRECT_MULTIPLIER
        )
        self.kg_max_neighbors = int(
            os.environ.get("NOX_KG_MAX_NEIGHBORS", "")
            or DEFAULT_KG_MAX_NEIGHBORS
        )
        self.kg_min_name_len = int(
            os.environ.get("NOX_KG_MIN_NAME_LEN", "")
            or DEFAULT_KG_MIN_NAME_LEN
        )
        self.kg_overfetch = int(
            os.environ.get("NOX_KG_OVERFETCH", "")
            or DEFAULT_KG_OVERFETCH
        )
        # The DB path is the same one the api-server is bound to; we open a
        # separate read-only conn for KG queries.
        self.kg_db_path = os.environ.get("NOX_DB_PATH", "")

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

        Strategy (Phase B):
            1. Flatten dataset -> ordered list with stable (date, group) keys
            2. Chunk into batches of `ingest_batch_size` (preserving order)
            3. For each batch: write H2-per-message markdown + day-group digest
               blocks, invoke `nox-mem ingest <tmpfile>`.
            4. Subprocess inherits NOX_DB_PATH from caller env for isolation.

        Returns:
            AddResult with success, days_processed, messages_sent, errors.

        Required env in caller:
            NOX_DB_PATH=/tmp/evermembench-{user_id}.db (or /root/.openclaw/... per op-audit)
            NOX_MEM_BIN=/path/to/nox-mem (optional, default = "nox-mem" on PATH)
        """
        start_ms = time.monotonic() * 1000
        errors: List[str] = []

        db_path = os.environ.get("NOX_DB_PATH", "")
        if not db_path:
            errors.append(
                "NOX_DB_PATH env var is required for isolated EverMemBench run "
                "(set to e.g. /root/.openclaw/evermembench-runs/X.db before invoking harness)"
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
                f"NOX_DB_PATH={db_path} points at production DB; refusing to ingest."
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

        # Build day-group context cache (used for digest blocks + context window)
        # Map (date, group) -> ordered list of messages
        self._day_group_cache: Dict[Tuple[str, str], List[GroupChatMessage]] = {}
        for m in messages:
            key = (self._date_of(m), str(getattr(m, "group", "?")))
            self._day_group_cache.setdefault(key, []).append(m)
        # Track which (date, group) digests have been emitted
        self._digest_emitted: set = set()

        # Batch ingest
        for batch_start in range(0, len(messages), self.ingest_batch_size):
            batch = messages[batch_start:batch_start + self.ingest_batch_size]
            batch_idx = batch_start // self.ingest_batch_size
            try:
                sent = await self._ingest_batch(batch, user_id, batch_idx, batch_start)
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
                "adapter_mode": self.adapter_mode,
                "context_window": self.context_window,
                "elapsed_ms": elapsed_ms,
                "messages_total": len(messages),
                "day_group_count": len(self._day_group_cache),
            },
        )

    async def _ingest_batch(
        self,
        batch: List["GroupChatMessage"],
        user_id: str,
        batch_idx: int,
        batch_start: int,
    ) -> int:
        """
        Write batch to temp .md file (Phase B or baseline format), invoke
        `nox-mem ingest <file>`, return count of messages dispatched.
        """
        lines = [f"# EverMemBench user_id={user_id} batch={batch_idx} mode={self.adapter_mode}\n"]

        if self.adapter_mode == "baseline":
            # PR #363 paragraph format (for ablation)
            for m in batch:
                lines.append(self._format_message_baseline(m))
                lines.append("")
        else:
            # Phase B: H2-per-message with structured metadata + context window
            for i, m in enumerate(batch):
                lines.append(self._format_message_phaseb(m, batch_start + i))
                lines.append("")

                # Emit digest once per (date, group) when the LAST message of
                # that day-group appears (within this batch). Same-batch
                # digests cluster near their messages; cross-batch digests
                # land in whichever batch contains the day-group's last msg.
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

        # Write to NamedTemporaryFile with .md suffix.
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

            # Invoke `nox-mem ingest <tempfile>` via execvp-style argv.
            # NOTE: `--source` flag removed (2026-05-28); nox-mem v3.8 rejects it.
            argv = [
                self.nox_mem_bin,
                "ingest",
                tmp_path,
            ]

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

    # ------------------------------------------------------------------
    # Phase B helpers
    # ------------------------------------------------------------------

    def _format_message_phaseb(
        self,
        msg: "GroupChatMessage",
        global_idx: int,
    ) -> str:
        """Phase B: H2 block with structured metadata + preceding-context window."""
        group = str(getattr(msg, "group", "?"))
        speaker = str(getattr(msg, "speaker", "?"))
        content = str(getattr(msg, "content", "")).strip()
        time_str = str(
            getattr(msg, "time", None)
            or getattr(msg, "timestamp", None)
            or "?"
        )
        date = self._date_of(msg)

        # Build "context" snippet: last N messages from the SAME (date, group)
        # preceding this message. This gives multi-hop retrieval a local anchor.
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
                # Shorten preceding context to avoid blowing up chunk size
                prev_snip = prev_content[:120].replace("\n", " ")
                if len(prev_content) > 120:
                    prev_snip += "..."
                context_parts.append(f"{prev_speaker}: {prev_snip}")
        context_str = " | ".join(context_parts) if context_parts else "(start of conversation)"

        return PHASEB_MESSAGE_BLOCK.format(
            time=time_str,
            group=group,
            speaker=speaker,
            date=date,
            context=context_str,
            content=content,
        )

    def _format_message_baseline(self, msg: "GroupChatMessage") -> str:
        """PR #363 baseline format (one paragraph)."""
        group = str(getattr(msg, "group", "?"))
        speaker = str(getattr(msg, "speaker", "?"))
        content = str(getattr(msg, "content", "")).strip()
        time_str = str(
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

    # Public alias kept for backwards compat
    def _format_message(self, msg: "GroupChatMessage") -> str:
        if self.adapter_mode == "baseline":
            return self._format_message_baseline(msg)
        # Phase B path: cannot include preceding context without batch context;
        # callers should prefer _format_message_phaseb directly.
        return self._format_message_baseline(msg)

    def _format_day_group_digest(
        self,
        key: Tuple[str, str],
        day_group_msgs: List["GroupChatMessage"],
    ) -> str:
        """Build the per-(date, group) digest block."""
        date, group = key
        speakers: List[str] = []
        seen_speakers: set = set()
        for m in day_group_msgs:
            sp = str(getattr(m, "speaker", "?"))
            if sp not in seen_speakers:
                seen_speakers.add(sp)
                speakers.append(sp)
        participants = ", ".join(speakers)
        # Short form for natural-language summary line
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
            date=date,
            group=group,
            participants=participants,
            message_count=len(day_group_msgs),
            participants_short=participants_short,
            first_line=first_line,
        )

    def _date_of(self, msg: "GroupChatMessage") -> str:
        """Extract date string from message (best effort)."""
        # Prefer explicit `date` attr if present (some Dataset versions add it)
        d = getattr(msg, "date", None)
        if d:
            return str(d)
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
                # Annotate date on each message for context lookups even
                # when GroupChatMessage doesn't carry .date natively.
                if day_date:
                    for m in sorted_msgs:
                        if not getattr(m, "date", None):
                            try:
                                setattr(m, "date", day_date)
                            except Exception:
                                pass
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

        Phase F: if `self.reranker_enabled` is True, request top-N (default 50)
        from the API and rerank with BAAI/bge-reranker-v2-m3 CrossEncoder
        before truncating to `top_k`. Falls back to plain top_k on any
        reranker failure (logged in metadata.rerank_error).
        """
        start_ms = time.monotonic() * 1000
        session = await self._get_session()

        # Decide how many results to request from the API.
        # Phase F: overfetch then rerank locally. Other modes: request top_k.
        # Phase KG: also needs overfetch so we have a pool to re-rank within
        # via KG boost. If both KG and rerank are on, take the max overfetch.
        api_limit = top_k
        if self.reranker_enabled:
            api_limit = max(api_limit, self.reranker_overfetch)
        if self.kg_enabled:
            api_limit = max(api_limit, self.kg_overfetch)

        payload = {
            "query": query,
            "limit": api_limit,
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

        # Extract candidate (chunk_text, item) pairs in API rank order.
        candidates: List[Tuple[str, Dict[str, Any]]] = []
        for item in raw_results:
            if isinstance(item, dict):
                content = item.get("chunk_text") or item.get("content") or ""
                if content:
                    candidates.append((content, item))

        api_returned = len(candidates)

        # ------------------------------------------------------------------
        # Phase KG (Lab Q1 #4) — 1-hop entity boost (post-RRF, pre-rerank)
        # ------------------------------------------------------------------
        kg_error: Optional[str] = None
        kg_ms: Optional[float] = None
        kg_applied = False
        kg_meta: Dict[str, Any] = {}

        if self.kg_enabled and candidates and self.kg_db_path:
            kg_start = time.monotonic() * 1000
            try:
                # 1. Load entity pool (cached per DB after first call)
                entity_pool, load_err = _kg_load_entity_names(
                    self.kg_db_path, self.kg_min_name_len
                )
                if load_err is not None:
                    kg_error = load_err
                elif not entity_pool:
                    kg_meta["status"] = "empty_kg"
                else:
                    # 2. Extract entity mentions from query (regex)
                    matched = _kg_extract_query_entities(query, entity_pool)
                    matched_ids = [m[0] for m in matched]
                    if not matched_ids:
                        kg_meta["status"] = "no_entities_in_query"
                    else:
                        # 3a. Get direct evidence chunks (chunks tied to the
                        #     mentioned entity itself — strongest signal)
                        direct_chunks = _kg_get_direct_chunk_ids(
                            self.kg_db_path, matched_ids
                        )
                        # 3b. Get 1-hop neighbors and their evidence chunks
                        neighbors = _kg_get_1hop_neighbors(
                            self.kg_db_path,
                            matched_ids,
                            self.kg_max_neighbors,
                        )
                        # Map: chunk_id → (best_confidence, hop_type)
                        # hop_type: "direct" (1.5×) or "neighbor" (1.0×)
                        chunk_boost_score: Dict[int, Tuple[float, str]] = {}
                        for cid in direct_chunks:
                            if cid <= 0:
                                continue
                            chunk_boost_score[cid] = (1.0, "direct")
                        for n_eid, ev_cid, conf, _seed in neighbors:
                            if ev_cid <= 0:
                                continue
                            if ev_cid in chunk_boost_score and chunk_boost_score[ev_cid][1] == "direct":
                                continue  # direct trumps neighbor
                            prev = chunk_boost_score.get(ev_cid)
                            if prev is None or conf > prev[0]:
                                chunk_boost_score[ev_cid] = (conf, "neighbor")

                        # 4. Apply ADDITIVE boost to candidates whose
                        #    chunk_id matches the boost map.
                        #    Per memoria-nox rule §5 (multiplicative empilhável
                        #    é veneno), we use additive delta.
                        boost_count = 0
                        for idx, (content, item) in enumerate(candidates):
                            cid = item.get("id") or item.get("chunk_id") or item.get("rowid")
                            try:
                                cid_int = int(cid) if cid is not None else None
                            except (TypeError, ValueError):
                                cid_int = None
                            if cid_int is None or cid_int not in chunk_boost_score:
                                continue
                            conf, hop_type = chunk_boost_score[cid_int]
                            multiplier = (
                                self.kg_direct_multiplier
                                if hop_type == "direct"
                                else 1.0
                            )
                            delta = self.kg_boost_magnitude * multiplier * conf
                            # Record the delta on the item so downstream
                            # sorting (after rerank, if enabled) uses it.
                            item["_kg_boost"] = delta
                            item["_kg_hop_type"] = hop_type
                            boost_count += 1

                        # Re-sort candidates: API rank position + kg delta.
                        # We use a synthetic score = (rrf_score or 1/(rank+1)) + delta.
                        # Most APIs do not return rrf_score so we approximate
                        # with 1/(rank+1) which is the RRF k=0 form.
                        def _kg_sort_key(rank_item: Tuple[int, Tuple[str, Dict[str, Any]]]) -> float:
                            rank, (_c, it) = rank_item
                            base_score = (
                                float(it.get("rrf_score") or it.get("score") or 0.0)
                                or 1.0 / (rank + 1)
                            )
                            return -(base_score + float(it.get("_kg_boost") or 0.0))

                        candidates = [
                            c for _, c in sorted(
                                enumerate(candidates),
                                key=_kg_sort_key,
                            )
                        ]
                        kg_applied = True
                        kg_meta.update(
                            status="applied",
                            entities_in_query=len(matched_ids),
                            entity_names_matched=[m[1] for m in matched],
                            neighbors_found=len(neighbors),
                            direct_chunks=len(direct_chunks),
                            chunks_boosted=boost_count,
                        )
            except Exception as exc:  # noqa: BLE001
                kg_error = f"KG boost failed: {type(exc).__name__}: {exc}"
            kg_ms = time.monotonic() * 1000 - kg_start

        # ------------------------------------------------------------------
        # Phase F: cross-encoder rerank (graceful fallback)
        # Phase MAP: bypass-entity protection wraps the rerank step — entity
        # chunks (section IN ('compiled', 'frontmatter')) skip cross-encoder
        # scoring and retain their bi-encoder rank. Reranked Set R fills the
        # remaining slots via merge_preserving_entity_positions().
        # ------------------------------------------------------------------
        rerank_error: Optional[str] = None
        rerank_ms: Optional[float] = None
        rerank_applied = False
        # Phase MAP telemetry
        map_applied = False
        map_entity_count = 0
        map_regular_count = 0

        if self.reranker_enabled and candidates:
            rerank_start = time.monotonic() * 1000
            model, err = _load_reranker(
                self.reranker_model_id, self.reranker_max_length
            )
            if err is not None:
                rerank_error = err
            else:
                try:
                    if self.ma_protection_enabled:
                        # Phase MAP — Approach A (bypass-entity).
                        # Partition by section. We carry the original index so
                        # we can stably preserve bi-encoder positions for Set E
                        # at merge time.
                        entity_indexed: List[Tuple[int, Tuple[str, Dict[str, Any]]]] = []
                        regular_indexed: List[Tuple[int, Tuple[str, Dict[str, Any]]]] = []
                        for idx, cand in enumerate(candidates):
                            sec = cand[1].get("section")
                            if sec in ENTITY_SECTION_NAMES:
                                entity_indexed.append((idx, cand))
                            else:
                                regular_indexed.append((idx, cand))
                        map_entity_count = len(entity_indexed)
                        map_regular_count = len(regular_indexed)

                        # Score only Set R via cross-encoder. If Set R is empty
                        # (pathological: every candidate is entity), skip rerank
                        # entirely and keep bi-encoder order.
                        if regular_indexed:
                            pairs = [(query, c[1][0]) for c in regular_indexed]
                            scores = await asyncio.to_thread(
                                model.predict,
                                pairs,
                                batch_size=self.reranker_batch_size,
                                show_progress_bar=False,
                            )
                            scored_r = list(zip(regular_indexed, scores))
                            scored_r.sort(key=lambda x: float(x[1]), reverse=True)
                            reranked_regular = [pair[0] for pair in scored_r]
                        else:
                            reranked_regular = []

                        candidates = _merge_preserving_entity_positions(
                            entity_indexed,
                            reranked_regular,
                            len(candidates),
                        )
                        rerank_applied = True
                        map_applied = True
                    else:
                        # Phase G / Phase F default — score every candidate.
                        pairs = [(query, c[0]) for c in candidates]
                        # CrossEncoder.predict is sync CPU/GPU work — run in a
                        # thread to avoid blocking the asyncio loop entirely.
                        scores = await asyncio.to_thread(
                            model.predict,
                            pairs,
                            batch_size=self.reranker_batch_size,
                            show_progress_bar=False,
                        )
                        scored = list(zip(candidates, scores))
                        scored.sort(key=lambda x: float(x[1]), reverse=True)
                        candidates = [c for c, _ in scored]
                        rerank_applied = True
                except Exception as exc:  # noqa: BLE001 — fall back gracefully
                    rerank_error = (
                        f"rerank predict failed: {type(exc).__name__}: {exc}"
                    )
            rerank_ms = time.monotonic() * 1000 - rerank_start

        # Truncate to top_k after optional rerank.
        candidates = candidates[:top_k]
        memories: List[str] = [c[0] for c in candidates]

        # Format context string for LLM answer stage
        context_lines = [f"{i + 1}. {m}" for i, m in enumerate(memories)]
        context = "\n".join(context_lines) if context_lines else "[No memories retrieved]"

        elapsed_ms = time.monotonic() * 1000 - start_ms
        meta: Dict[str, Any] = {
            "api_base": self.api_base,
            "top_k": top_k,
            "api_limit": api_limit,
            "returned": len(memories),
            "api_returned": api_returned,
            "took_ms_api": data.get("took_ms", None) if isinstance(data, dict) else None,
            "rerank_enabled": self.reranker_enabled,
            "rerank_applied": rerank_applied,
            "rerank_model": self.reranker_model_id if self.reranker_enabled else None,
            "rerank_ms": rerank_ms,
            "rerank_error": rerank_error,
            "kg_enabled": self.kg_enabled,
            "kg_applied": kg_applied,
            "kg_ms": kg_ms,
            "kg_error": kg_error,
            "kg_meta": kg_meta,
            # Phase MAP (Lab Q1 #2) telemetry — enabled?, applied?, partition sizes.
            # `entity_count` = chunks bypassed from rerank (Set E size).
            # `regular_count` = chunks scored by rerank (Set R size).
            # The two sum to api_returned when MAP applies; if rerank failed
            # (rerank_error set), map_applied stays False and counts are 0.
            "ma_protection_enabled": self.ma_protection_enabled,
            "ma_protection_applied": map_applied,
            "ma_protection_entity_count": map_entity_count,
            "ma_protection_regular_count": map_regular_count,
        }
        return SearchResult(
            question_id=kwargs.get("question_id", "unknown"),
            query=query,
            retrieved_memories=memories,
            context=context,
            search_duration_ms=elapsed_ms,
            metadata=meta,
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
            "adapter_mode": self.adapter_mode,
            "phaseb_context_window": self.context_window,
            "reranker_enabled": self.reranker_enabled,
            "reranker_model": self.reranker_model_id,
            "reranker_overfetch": self.reranker_overfetch,
            "reranker_batch_size": self.reranker_batch_size,
            "reranker_max_length": self.reranker_max_length,
            "kg_enabled": self.kg_enabled,
            "kg_boost_magnitude": self.kg_boost_magnitude,
            "kg_direct_multiplier": self.kg_direct_multiplier,
            "kg_max_neighbors": self.kg_max_neighbors,
            "kg_min_name_len": self.kg_min_name_len,
            "kg_overfetch": self.kg_overfetch,
            "kg_db_path": self.kg_db_path,
            "ma_protection_enabled": self.ma_protection_enabled,
            "version": "phase-map-0.1",
        }
