"""MemoryBank Benchmark Adapter for nox-mem Conversational Memory Evaluation (W2).

WHAT THIS SCRIPT DOES
---------------------
Bridges the MemoryBank-SiliconFriend benchmark (Zhong et al., 2023,
arXiv:2305.10250) and the nox-mem hybrid retrieval system to produce the
"Conversational episodic memory" results for paper §5.2 Table 5.

MemoryBank is a long-horizon conversational memory benchmark simulating a
personal AI companion over many days.  Unlike BEIR (static document retrieval)
and LOCOMO (Stanford human dialogues), MemoryBank tests synthetic episodic
memory: a daily conversation history with explicit QA annotation covering
factual recall, temporal reasoning, sentiment analysis, preference inference,
and event summarisation.

Dataset source: github.com/zhongwanjun/MemoryBank-SiliconFriend
  Path: data/silicon_friend_memory_bank/
  Fallback: Parquet snapshots on HuggingFace (see _MEMORYBANK_HF_DATASET)
  ~40 synthetic sessions × 5 question types × variable QA pairs per session

Pipeline (5 stages):
  1. Clone / download MemoryBank from GitHub (git clone, ~5 MB).
     Fallback: HuggingFace datasets load.
     Writes manifest on --download-only (smoke test, <60 s target).
  2. Chunk each session's daily conversation into ~2000-char segments
     (paragraph-boundary preferred, matching nox-mem chunking strategy).
  3. Index chunks into a TEMP SQLite DB with FTS5 (CPU-only, BM25 baseline +
     dry-run without vectors; vectorize separately before full eval).
  4. Select 100-query stratified subset: up to 20 per question type across
     5 types (factual_recall, temporal_reasoning, sentiment_analysis,
     preference_inference, event_summary).  Seed=42 for reproducibility.
  5. Compute nDCG@10, MRR, Recall@10, Precision@5 via nox-mem HTTP API
     and write results JSONL compatible with existing results/ aggregator.

MemoryBank data structure
--------------------------
Dataset root: data/silicon_friend_memory_bank/
  Each session is a JSON file with:
    {
      "session_id": "session_001",
      "date": "2023-01-01",
      "conversations": [
        {"role": "user"|"assistant", "content": "...", "timestamp": "..."},
        ...
      ],
      "memory_items": [
        {
          "memory_id": "m001",
          "content": "...",       # memory snippet to retrieve
          "created_at": "..."
        },
        ...
      ],
      "qa_pairs": [
        {
          "question": "...",
          "answer": "...",
          "question_type": "factual_recall"|"temporal_reasoning"|...
          "memory_ids": ["m001", ...]   # gold memory IDs for relevance
        },
        ...
      ]
    }

Alternative layout (if GitHub uses flat JSON lines per session):
  The adapter handles both dict-of-sessions (single JSON) and
  directory of per-session JSON files.

Evidence linking:
  Gold docs = memory_items whose memory_id is in qa_pair.memory_ids.
  A chunk is relevant if it contains the full text of any gold memory_item
  content (substring match, case-insensitive, ≥20 chars).
  Secondary fallback: substring match on gold memory content in conversation.

HOW TO RUN
----------
# 0. Create venv (separate from nox-mem TypeScript toolchain):
python3.11 -m venv /tmp/memorybank-adapter-venv
source /tmp/memorybank-adapter-venv/bin/activate
pip install "requests>=2.31"
# Optional (HuggingFace fallback only):
pip install "datasets>=2.19"

# 1. Smoke test — download + build DB + manifest (<60 s):
python memorybank_adapter.py download-only \\
    --clone-dir /tmp/memorybank-repo \\
    --db        /tmp/nox-mem-memorybank.db \\
    --manifest  /tmp/memorybank-manifest.json

# 2. Build TEMP DB (chunk + FTS5):
python memorybank_adapter.py build-db \\
    --clone-dir /tmp/memorybank-repo \\
    --db        /tmp/nox-mem-memorybank.db

# 3. Convert to eval queries JSONL (100-query stratified subset):
python memorybank_adapter.py convert-queries \\
    --clone-dir /tmp/memorybank-repo \\
    --db        /tmp/nox-mem-memorybank.db \\
    --output    /tmp/memorybank-eval-queries.jsonl

# 4. Start nox-mem API pointing at TEMP DB (separate shell):
#    NOX_DB_PATH=/tmp/nox-mem-memorybank.db nox-mem vectorize --all
#    NOX_DB_PATH=/tmp/nox-mem-memorybank.db node dist/index.js serve

# 5. Run evaluation (100 queries → per-query JSONL, <3 min):
python memorybank_adapter.py eval \\
    --queries /tmp/memorybank-eval-queries.jsonl \\
    --output  /tmp/memorybank-results.jsonl \\
    --api-url http://localhost:18802

# 6. Compare with baselines:
python memorybank_adapter.py compare \\
    --nox  /tmp/memorybank-results.jsonl \\
    --csv  /tmp/memorybank-comparison.csv

# End-to-end (download + build-db + convert-queries, no eval step):
python memorybank_adapter.py full \\
    --clone-dir /tmp/memorybank-repo \\
    --db        /tmp/nox-mem-memorybank.db \\
    --queries-output /tmp/memorybank-eval-queries.jsonl

EXPECTED OUTPUTS
----------------
- /tmp/nox-mem-memorybank.db           — TEMP SQLite DB (chunks + FTS5)
- /tmp/memorybank-manifest.json        — Dataset manifest (session count, QA stats)
- /tmp/memorybank-eval-queries.jsonl   — 100-query stratified eval set
- /tmp/memorybank-results.jsonl        — nox-mem per-query results
- /tmp/memorybank-comparison.csv       — Cross-system table

INTEGRATION WITH PAPER §5.2 TABLE 5
-------------------------------------
Citation: "n=100 MemoryBank questions (20 per type, 5 types), session-chunked
corpus (2000-char segments, paragraph-boundary), evidence-memory relevance,
seed=42."
Reference: Zhong et al. (2023). MemoryBank: Enhancing Large Language Models
with Long-Term Memory. arXiv:2305.10250.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import os
import random
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterator

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("memorybank_adapter")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MEMORYBANK_GITHUB_URL = "https://github.com/zhongwanjun/MemoryBank-SiliconFriend"
_MEMORYBANK_DATA_SUBPATH = "data/silicon_friend_memory_bank"

# HuggingFace fallback (searched as of 2026-05-04 — may need updating)
_MEMORYBANK_HF_CANDIDATES = [
    "zhongwanjun/MemoryBank",
    "zhongwanjun/silicon-friend",
    "wanjun-zhong/MemoryBank",
]

# Chunking: ~2000-char target, matching nox-mem default chunk size
_CHUNK_TARGET_CHARS = 2_000
_CHUNK_OVERLAP_CHARS = 200

# Stratified subset: 20 per question type × 5 types = 100 queries
_SUBSET_PER_TYPE = 20
_TOTAL_SUBSET = 100

# MemoryBank question types (as observed in the paper / repo)
_QUESTION_TYPE_MAP: dict[str, str] = {
    "factual_recall": "factual_recall",
    "factual recall": "factual_recall",
    "factual": "factual_recall",
    "temporal_reasoning": "temporal_reasoning",
    "temporal reasoning": "temporal_reasoning",
    "temporal": "temporal_reasoning",
    "sentiment_analysis": "sentiment_analysis",
    "sentiment analysis": "sentiment_analysis",
    "sentiment": "sentiment_analysis",
    "preference_inference": "preference_inference",
    "preference inference": "preference_inference",
    "preference": "preference_inference",
    "event_summary": "event_summary",
    "event summary": "event_summary",
    "event": "event_summary",
    "summary": "event_summary",
    # Additional variants seen in some versions
    "single_hop": "factual_recall",
    "multi_hop": "temporal_reasoning",
    "open_domain": "event_summary",
}

_CANONICAL_TYPES: list[str] = [
    "factual_recall",
    "temporal_reasoning",
    "sentiment_analysis",
    "preference_inference",
    "event_summary",
]

# Evidence span relevance: substring must be >=20 chars to be non-trivial
_MIN_EVIDENCE_LEN = 20

# HTTP API
_DEFAULT_API_URL = "http://localhost:18802"
_DEFAULT_TEMP_DB = "/tmp/nox-mem-memorybank.db"
_DEFAULT_CLONE_DIR = "/tmp/memorybank-repo"
_DEFAULT_MANIFEST = "/tmp/memorybank-manifest.json"
_DEFAULT_K = 10
_DEFAULT_SEED = 42

# nox-mem API search payload keys (matches locomo_adapter.py convention)
_NOX_SEARCH_PAYLOAD_QUERY = "query"
_NOX_SEARCH_PAYLOAD_LIMIT = "limit"
_NOX_SEARCH_PAYLOAD_HYBRID = "hybrid"

# Load guard threshold: abort if 5-min load avg exceeds this
_LOAD_AVG_LIMIT = 3.5

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

QARecord = dict[str, Any]       # {qa_id, session_id, question, answer, type, evidence, relevant_chunk_ids, n_relevant}
ChunkRecord = dict[str, Any]    # {chunk_id, session_id, chunk_index, chunk_text, turn_start, turn_end}
SearchHit = tuple[str, float]   # (chunk_id_str, score)
EvalQuery = dict[str, Any]      # {query_id, query_text, expected_chunk_ids, type, ...}
MemoryItem = dict[str, Any]     # {memory_id, content, created_at}
SessionData = dict[str, Any]    # normalised session dict


# ---------------------------------------------------------------------------
# Load-avg guard (abort if BEIR is being crowded out)
# ---------------------------------------------------------------------------


def _check_load_avg(limit: float = _LOAD_AVG_LIMIT) -> None:
    """Check system 5-minute load average and abort if above limit.

    Args:
        limit: Load average threshold.

    Raises:
        SystemExit: If 5-min load avg exceeds limit.
    """
    try:
        with open("/proc/loadavg", encoding="ascii") as fh:
            parts = fh.read().split()
        load5 = float(parts[1])
        logger.info("5-min load avg: %.2f (limit: %.1f)", load5, limit)
        if load5 > limit:
            logger.error(
                "ABORT: 5-min load avg %.2f > %.1f — BEIR session has priority. "
                "Kill memorybank-eval and wait for load to drop.",
                load5, limit,
            )
            sys.exit(1)
    except FileNotFoundError:
        # Not Linux (macOS) — try uptime
        try:
            result = subprocess.run(
                ["uptime"], capture_output=True, text=True, timeout=5
            )
            m = re.search(r"load averages?:\s*([\d.]+)[,\s]+([\d.]+)", result.stdout)
            if m:
                load5 = float(m.group(2))
                logger.info("5-min load avg: %.2f (limit: %.1f)", load5, limit)
                if load5 > limit:
                    logger.error(
                        "ABORT: 5-min load avg %.2f > %.1f — halting to protect BEIR.",
                        load5, limit,
                    )
                    sys.exit(1)
        except Exception:
            logger.warning("Could not determine load avg — proceeding without guard.")


# ---------------------------------------------------------------------------
# Stage 1 — Acquire MemoryBank dataset
# ---------------------------------------------------------------------------


def _git_clone(url: str, dest: Path, timeout_s: int = 120) -> bool:
    """Shallow-clone a GitHub repo to dest.

    Args:
        url: HTTPS clone URL.
        dest: Destination directory.
        timeout_s: Clone timeout in seconds.

    Returns:
        True if clone succeeded, False otherwise.
    """
    if dest.exists() and (dest / ".git").exists():
        logger.info("Repo already cloned at %s — pulling latest.", dest)
        try:
            subprocess.run(
                ["git", "-C", str(dest), "pull", "--ff-only", "--quiet"],
                check=True, capture_output=True, timeout=60,
            )
            return True
        except subprocess.SubprocessError as exc:
            logger.warning("git pull failed (%s) — using existing clone.", exc)
            return True

    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Cloning %s → %s …", url, dest)
    try:
        subprocess.run(
            ["git", "clone", "--depth=1", "--quiet", url, str(dest)],
            check=True, capture_output=True, timeout=timeout_s,
        )
        logger.info("Clone complete: %s", dest)
        return True
    except FileNotFoundError:
        logger.warning("git not found in PATH — will try HuggingFace fallback.")
        return False
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
        logger.warning("git clone failed: %s — stderr: %s", exc, stderr[:200])
        return False
    except subprocess.TimeoutExpired:
        logger.warning("git clone timed out after %d s.", timeout_s)
        return False


def _load_session_from_json(path: Path) -> SessionData | None:
    """Load and normalise a single session JSON file.

    Handles both dict-of-sessions format and single-session format.

    Args:
        path: Path to a .json session file.

    Returns:
        Normalised SessionData dict or None if parsing fails.
    """
    try:
        with path.open(encoding="utf-8") as fh:
            raw = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load %s: %s", path, exc)
        return None

    if not isinstance(raw, dict):
        logger.warning("Unexpected JSON type in %s: %s", path, type(raw).__name__)
        return None

    # Normalise: ensure required keys exist with sensible defaults
    session: SessionData = {
        "session_id": str(raw.get("session_id") or path.stem),
        "date": str(raw.get("date") or ""),
        "conversations": raw.get("conversations") or raw.get("dialogue") or [],
        "memory_items": raw.get("memory_items") or raw.get("memories") or [],
        "qa_pairs": raw.get("qa_pairs") or raw.get("QA") or raw.get("questions") or [],
    }

    # Ensure conversations is a list
    if not isinstance(session["conversations"], list):
        session["conversations"] = []

    # Ensure memory_items is a list
    if not isinstance(session["memory_items"], list):
        session["memory_items"] = []

    # Ensure qa_pairs is a list
    if not isinstance(session["qa_pairs"], list):
        session["qa_pairs"] = []

    return session


def _discover_session_files(data_dir: Path) -> list[Path]:
    """Recursively discover JSON session files in the MemoryBank data directory.

    Args:
        data_dir: Root directory of the MemoryBank data.

    Returns:
        Sorted list of JSON file paths.
    """
    json_files: list[Path] = sorted(data_dir.rglob("*.json"))
    # Filter out obvious non-session files (README, schema, index)
    session_files = [
        p for p in json_files
        if p.stat().st_size > 100  # skip empty/tiny files
        and p.name.lower() not in ("readme.json", "schema.json", "index.json")
    ]
    logger.info(
        "Found %d JSON files in %s", len(session_files), data_dir
    )
    return session_files


def _load_from_eval_data(eval_data_dir: Path) -> list[SessionData] | None:
    """Load MemoryBank sessions from the actual eval_data/ directory layout.

    The real MemoryBank repo layout (as of 2026-05-04) uses eval_data/<lang>/
    rather than the per-session JSON format assumed by the original adapter.

    Schema found in eval_data/en/:
      memory_bank_en.json   — dict keyed by user name, each value is a dict with:
                               "history": {date_str: [{query, response}, ...]},
                               "meta_information": {name, personality, hobbies, ...}
      probing_questions_en.jsonl — one JSON object per line: {username: [q1, q2, ...]}
                               Questions are plain strings; NO gold answers or memory_ids.

    IMPORTANT LIMITATION: probing_questions have no gold answer or relevance labels.
    This means nDCG/MRR/Recall cannot be computed without an oracle or LLM judge.
    The loader builds SessionData with qa_pairs whose answer="[UNLABELED]" and
    gold_memory_ids=[] so the pipeline can chunk + index; eval metrics will be N/A.

    Args:
        eval_data_dir: Path to eval_data/ root (contains en/, cn/ subdirs).

    Returns:
        List of SessionData dicts or None if required files not found.
    """
    # Prefer English; fall back to Chinese if en/ missing
    for lang_dir in (eval_data_dir / "en", eval_data_dir / "cn"):
        mb_path = lang_dir / f"memory_bank_{lang_dir.name}.json"
        pq_path = lang_dir / f"probing_questions_{lang_dir.name}.jsonl"
        if mb_path.exists() and pq_path.exists():
            break
    else:
        logger.warning("No memory_bank_*.json + probing_questions_*.jsonl found in %s", eval_data_dir)
        return None

    logger.info("Loading eval_data layout from %s", lang_dir)

    try:
        memory_bank: dict[str, Any] = json.loads(mb_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to parse %s: %s", mb_path, exc)
        return None

    # Parse probing questions: one JSON object per line keyed by user name
    probing_qs: dict[str, list[str]] = {}
    try:
        for raw_line in pq_path.read_text(encoding="utf-8").splitlines():
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            obj = json.loads(raw_line)
            if isinstance(obj, dict):
                for user, qs in obj.items():
                    probing_qs[user.strip()] = [str(q) for q in qs] if isinstance(qs, list) else []
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to parse %s: %s", pq_path, exc)
        probing_qs = {}

    logger.info(
        "eval_data: %d users in memory_bank, %d users with probing questions",
        len(memory_bank), len(probing_qs),
    )

    sessions: list[SessionData] = []
    for raw_user, user_data in memory_bank.items():
        user = raw_user.strip()
        if not isinstance(user_data, dict):
            continue

        history: dict[str, list[dict[str, Any]]] = user_data.get("history") or {}
        meta: dict[str, Any] = user_data.get("meta_information") or {}

        # Flatten history into a single conversations list with date tags
        conversations: list[dict[str, Any]] = []
        for date_str, turns in sorted(history.items()):
            if not isinstance(turns, list):
                continue
            for turn in turns:
                q = (turn.get("query") or "").strip()
                r = (turn.get("response") or "").strip()
                if q:
                    conversations.append({"role": "user", "content": q, "date": date_str})
                if r:
                    conversations.append({"role": "assistant", "content": r, "date": date_str})

        # Build qa_pairs from probing questions (no gold answers — mark as UNLABELED)
        user_qs = probing_qs.get(user, [])
        qa_pairs: list[dict[str, Any]] = [
            {
                "question": q,
                "answer": "[UNLABELED]",
                "question_type": "factual_recall",  # default; type labels absent
                "memory_ids": [],
                "_no_gold_labels": True,
            }
            for q in user_qs
            if q.strip()
        ]

        sessions.append({
            "session_id": user.replace(" ", "_").lower(),
            "date": sorted(history.keys())[0] if history else "",
            "conversations": conversations,
            "memory_items": [],  # eval_data has no discrete memory items
            "qa_pairs": qa_pairs,
            "_meta": meta,
            "_source": "eval_data",
            "_n_days": len(history),
            "_no_gold_labels": True,
        })

    if not sessions:
        logger.warning("eval_data parse produced 0 sessions — unexpected.")
        return None

    total_qs = sum(len(s["qa_pairs"]) for s in sessions)
    logger.warning(
        "eval_data schema loaded: %d sessions, %d questions, NO gold labels. "
        "IR metrics (nDCG/MRR/Recall) require an external judge — cannot be computed from this data.",
        len(sessions), total_qs,
    )
    return sessions


def _load_from_hf_fallback(
    cache_dir: str | Path | None = None,
) -> list[SessionData] | None:
    """Attempt to load MemoryBank data from HuggingFace Hub (fallback path).

    Tries multiple known HF dataset IDs in sequence.

    Args:
        cache_dir: HuggingFace dataset cache directory.

    Returns:
        List of SessionData dicts or None if all attempts fail.
    """
    try:
        import datasets  # type: ignore[import-untyped]
    except ImportError:
        logger.warning(
            "datasets not installed — HF fallback unavailable. "
            "Run: pip install 'datasets>=2.19'"
        )
        return None

    for hf_id in _MEMORYBANK_HF_CANDIDATES:
        logger.info("Trying HuggingFace: %s", hf_id)
        try:
            ds_dict = datasets.load_dataset(
                hf_id,
                cache_dir=str(cache_dir) if cache_dir else None,
                trust_remote_code=False,
            )
            # Take first available split
            if not ds_dict:
                continue
            split = list(ds_dict.keys())[0]
            ds = ds_dict[split]
            logger.info("Loaded HF dataset %s split=%s, %d rows", hf_id, split, len(ds))

            sessions: list[SessionData] = []
            for idx, row in enumerate(ds):
                row_dict = dict(row)
                session: SessionData = {
                    "session_id": str(row_dict.get("session_id") or idx),
                    "date": str(row_dict.get("date") or ""),
                    "conversations": row_dict.get("conversations") or [],
                    "memory_items": row_dict.get("memory_items") or [],
                    "qa_pairs": row_dict.get("qa_pairs") or [],
                }
                sessions.append(session)
            return sessions if sessions else None

        except Exception as exc:
            logger.warning("HF load failed for %s: %s", hf_id, exc)

    return None


def download_memorybank(
    clone_dir: str | Path | None = None,
    cache_dir: str | Path | None = None,
) -> tuple[list[SessionData], str]:
    """Download MemoryBank and return sessions plus the acquisition method used.

    Acquisition order:
    1. git clone github.com/zhongwanjun/MemoryBank-SiliconFriend
       → read JSON files from data/silicon_friend_memory_bank/
    2. HuggingFace datasets.load_dataset() (multiple ID candidates)
    3. Raise RuntimeError with full diagnostic

    Args:
        clone_dir: Directory for git clone (default: /tmp/memorybank-repo).
        cache_dir: HuggingFace dataset cache (for fallback).

    Returns:
        Tuple of (sessions list, acquisition_method string).

    Raises:
        RuntimeError: If all acquisition strategies fail.
    """
    clone_dir = Path(clone_dir or _DEFAULT_CLONE_DIR)

    # --- Strategy 1: git clone ---
    cloned = _git_clone(_MEMORYBANK_GITHUB_URL, clone_dir)
    if cloned:
        # --- Strategy 1a: eval_data/ layout (actual repo as of 2026-05-04) ---
        # The repo contains eval_data/{en,cn}/ with memory_bank_*.json +
        # probing_questions_*.jsonl — NOT per-session JSON files under
        # data/silicon_friend_memory_bank/ (that path does not exist in the repo).
        # Prefer eval_data/ explicitly before falling through to glob discovery
        # which incorrectly selected SiliconFriend-ChatGLM-BELLE/train/BELLE/run_config/
        # (only 2 training config JSONs) as the data directory.
        eval_data_dir = clone_dir / "eval_data"
        if eval_data_dir.is_dir():
            eval_sessions = _load_from_eval_data(eval_data_dir)
            if eval_sessions:
                logger.info(
                    "Loaded %d sessions from eval_data/ layout (%s)",
                    len(eval_sessions), eval_data_dir,
                )
                return eval_sessions, "github_clone_eval_data"

        # --- Strategy 1b: legacy per-session JSON layout ---
        data_dir = clone_dir / _MEMORYBANK_DATA_SUBPATH
        if not data_dir.exists():
            # Try finding data dir by globbing — but skip training/config dirs
            # to avoid picking up non-session JSON files (run_config, finetune configs)
            json_dirs = [
                p.parent for p in clone_dir.rglob("*.json")
                if p.stat().st_size > 500  # raise threshold to skip tiny config files
                and "train" not in p.parts
                and "run_config" not in p.parts
            ]
            if json_dirs:
                data_dir = sorted(set(json_dirs))[0]
                logger.info("Data dir discovered: %s", data_dir)
            else:
                logger.warning(
                    "Expected data dir not found: %s — scanning all JSON in clone.", data_dir
                )
                data_dir = clone_dir

        session_files = _discover_session_files(data_dir)

        if session_files:
            sessions: list[SessionData] = []
            for fpath in session_files:
                s = _load_session_from_json(fpath)
                if s is not None:
                    sessions.append(s)

            if sessions:
                logger.info(
                    "Loaded %d sessions from GitHub clone (%s)", len(sessions), data_dir
                )
                return sessions, "github_clone"
            else:
                logger.warning("GitHub clone found %d JSON files but parsed 0 sessions.", len(session_files))
        else:
            logger.warning("No JSON session files found after clone — trying HF fallback.")

    # --- Strategy 2: HuggingFace fallback ---
    hf_sessions = _load_from_hf_fallback(cache_dir=cache_dir)
    if hf_sessions:
        logger.info("Loaded %d sessions from HuggingFace fallback.", len(hf_sessions))
        return hf_sessions, "huggingface"

    # --- All strategies failed ---
    raise RuntimeError(
        "MemoryBank acquisition failed — all strategies exhausted.\n\n"
        "Strategies tried:\n"
        f"  1. git clone {_MEMORYBANK_GITHUB_URL} → {clone_dir}\n"
        f"     data subpath: {_MEMORYBANK_DATA_SUBPATH}\n"
        "  2. HuggingFace datasets.load_dataset for IDs:\n"
        + "\n".join(f"     - {hf_id}" for hf_id in _MEMORYBANK_HF_CANDIDATES) + "\n\n"
        "Diagnostic steps:\n"
        "  curl -sI https://github.com/zhongwanjun/MemoryBank-SiliconFriend\n"
        "  python -c \"import datasets; datasets.load_dataset('zhongwanjun/MemoryBank')\"\n\n"
        "If GitHub is private/deleted:\n"
        "  Alternative 1: FRAMES (Google DeepMind, 2024) — HF: google/frames-benchmark\n"
        "  Alternative 2: DialFact (conversational fact-checking) — search HF for 'dialfact'\n"
    )


# ---------------------------------------------------------------------------
# Stage 2 — Chunk conversation sessions
# ---------------------------------------------------------------------------


def _extract_turn_text(turn: dict[str, Any]) -> str:
    """Extract flat text from a single MemoryBank conversation turn.

    Handles multiple schema variants: role/content, speaker/text,
    user/assistant alternating.

    Args:
        turn: Turn dict from MemoryBank session.

    Returns:
        Flat string representation of the turn.
    """
    role: str = (
        turn.get("role")
        or turn.get("speaker")
        or turn.get("from")
        or ""
    ).strip()
    content: str = (
        turn.get("content")
        or turn.get("text")
        or turn.get("value")
        or ""
    ).strip()
    timestamp: str = (turn.get("timestamp") or turn.get("time") or "").strip()

    if not content:
        return ""

    if role and timestamp:
        return f"[{timestamp}] {role}: {content}"
    elif role:
        return f"{role}: {content}"
    else:
        return content


def _extract_memory_text(item: MemoryItem) -> str:
    """Extract flat text from a MemoryBank memory item.

    Args:
        item: MemoryItem dict.

    Returns:
        Text representation of the memory item.
    """
    content: str = (item.get("content") or item.get("text") or "").strip()
    created: str = (item.get("created_at") or item.get("date") or "").strip()

    if created and content:
        return f"[memory:{created}] {content}"
    return content


def _chunk_session(
    session_id: str,
    conversations: list[dict[str, Any]],
    memory_items: list[MemoryItem],
    target_chars: int = _CHUNK_TARGET_CHARS,
    overlap_chars: int = _CHUNK_OVERLAP_CHARS,
) -> list[ChunkRecord]:
    """Chunk a session's conversations + memory items into overlapping segments.

    Chunking strategy:
    1. Memory items are prepended as a special "memory block" chunk because
       they are the ground-truth retrieval targets.  Each memory item gets its
       own micro-chunk plus appears within the conversation chunks it came from.
    2. Conversation turns are accumulated into ~2000-char chunks with overlap.
    3. Paragraph boundaries (double newline) are preferred break points.

    Args:
        session_id: String session identifier.
        conversations: List of turn dicts from the session.
        memory_items: List of memory item dicts.
        target_chars: Target character length per chunk.
        overlap_chars: Overlap character count between consecutive chunks.

    Returns:
        List of ChunkRecord dicts.
    """
    chunks: list[ChunkRecord] = []
    chunk_index = 0

    # --- Memory item chunks (one per item, for direct evidence retrieval) ---
    for m_idx, mem in enumerate(memory_items):
        mem_text = _extract_memory_text(mem)
        if not mem_text or len(mem_text) < 5:
            continue
        mem_id = str(mem.get("memory_id") or f"m{m_idx:04d}")
        chunks.append({
            "chunk_id": f"{session_id}_mem_{mem_id}",
            "session_id": session_id,
            "chunk_index": chunk_index,
            "chunk_text": mem_text,
            "turn_start": -1,  # sentinel: memory item, not a conversation turn
            "turn_end": -1,
            "memory_ids": [mem_id],
        })
        chunk_index += 1

    if not conversations:
        return chunks

    # --- Conversation chunks (sliding window over turns) ---
    turn_texts: list[str] = [_extract_turn_text(t) for t in conversations]
    turn_texts = [t for t in turn_texts if t]  # drop empty turns

    i = 0
    overlap_seed: str = ""

    while i < len(turn_texts):
        buf: list[str] = []
        turn_start = i

        if overlap_seed:
            buf.append(overlap_seed)

        while i < len(turn_texts):
            turn_text = turn_texts[i]
            candidate = "\n\n".join(buf + [turn_text])
            if len(candidate) > target_chars and buf:
                current_text = "\n\n".join(buf)
                break_pos = current_text.rfind("\n\n", max(0, len(current_text) - 300))
                if break_pos > len(current_text) // 2:
                    chunk_text = current_text[:break_pos].strip()
                    overlap_seed = current_text[break_pos:].strip()[-overlap_chars:]
                    if chunk_text:
                        chunks.append({
                            "chunk_id": f"{session_id}_c{chunk_index:04d}",
                            "session_id": session_id,
                            "chunk_index": chunk_index,
                            "chunk_text": chunk_text,
                            "turn_start": turn_start,
                            "turn_end": max(i - 1, turn_start),
                            "memory_ids": [],
                        })
                        chunk_index += 1
                    break
                else:
                    break
            buf.append(turn_text)
            i += 1

        if buf and i == len(turn_texts):
            chunk_text = "\n\n".join(buf).strip()
            if chunk_text:
                chunks.append({
                    "chunk_id": f"{session_id}_c{chunk_index:04d}",
                    "session_id": session_id,
                    "chunk_index": chunk_index,
                    "chunk_text": chunk_text,
                    "turn_start": turn_start,
                    "turn_end": len(turn_texts) - 1,
                    "memory_ids": [],
                })
                chunk_index += 1
            break
        elif buf:
            chunk_text = "\n\n".join(buf).strip()
            overlap_seed = chunk_text[-overlap_chars:] if chunk_text else ""
            if chunk_text:
                chunks.append({
                    "chunk_id": f"{session_id}_c{chunk_index:04d}",
                    "session_id": session_id,
                    "chunk_index": chunk_index,
                    "chunk_text": chunk_text,
                    "turn_start": turn_start,
                    "turn_end": max(i - 1, turn_start),
                    "memory_ids": [],
                })
                chunk_index += 1

    return chunks


def chunk_all_sessions(
    sessions: list[SessionData],
    target_chars: int = _CHUNK_TARGET_CHARS,
    overlap_chars: int = _CHUNK_OVERLAP_CHARS,
) -> list[ChunkRecord]:
    """Chunk all MemoryBank sessions into a flat list of ChunkRecords.

    Args:
        sessions: List of SessionData dicts (from download_memorybank).
        target_chars: Target chunk size in characters.
        overlap_chars: Overlap between consecutive chunks.

    Returns:
        Flat list of ChunkRecord dicts across all sessions.
    """
    all_chunks: list[ChunkRecord] = []
    for session in sessions:
        sid = session["session_id"]
        convs = session.get("conversations") or []
        mems = session.get("memory_items") or []

        chunks = _chunk_session(
            sid,
            list(convs) if not isinstance(convs, list) else convs,
            list(mems) if not isinstance(mems, list) else mems,
            target_chars,
            overlap_chars,
        )
        all_chunks.extend(chunks)
        logger.debug(
            "Session %s: %d turns + %d mem items → %d chunks",
            sid, len(convs), len(mems), len(chunks),
        )

    logger.info(
        "Total chunks across %d sessions: %d", len(sessions), len(all_chunks)
    )
    return all_chunks


# ---------------------------------------------------------------------------
# Stage 3 — Build TEMP SQLite DB
# ---------------------------------------------------------------------------


def build_temp_db(
    chunks: list[ChunkRecord],
    db_path: str | Path,
    force: bool = False,
) -> Path:
    """Write chunks to a nox-mem–compatible SQLite TEMP DB with FTS5 index.

    Schema mirrors nox-mem schema v10 subset (same columns, same defaults),
    so the existing nox-mem API and vectorize pipeline can operate on this DB
    with the NOX_DB_PATH override.

    The doc_id column stores the string chunk_id for direct evidence matching
    (e.g. "session_001_mem_m002" or "session_001_c0003").

    Args:
        chunks: Flat list of ChunkRecord dicts (from chunk_all_sessions).
        db_path: Path for the output SQLite DB.
        force: If True, delete and recreate even if DB exists.

    Returns:
        Path to the created (or existing) SQLite DB.

    Raises:
        AssertionError: If no chunks are written.
    """
    db_path = Path(db_path)

    if db_path.exists() and not force:
        try:
            with sqlite3.connect(str(db_path)) as conn_check:
                (existing,) = conn_check.execute("SELECT COUNT(*) FROM chunks").fetchone()
            if existing == len(chunks):
                logger.info(
                    "TEMP DB already exists with %d rows — skipping recreate.", existing
                )
                return db_path
            else:
                logger.info(
                    "TEMP DB exists but has %d rows (expected %d) — recreating.",
                    existing, len(chunks),
                )
        except sqlite3.OperationalError:
            logger.info("TEMP DB exists but lacks chunks table — recreating.")

    if db_path.exists():
        db_path.unlink()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Creating TEMP DB: %s (%d chunks)", db_path, len(chunks))

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id          TEXT    NOT NULL,
            chunk_text      TEXT    NOT NULL,
            source_file     TEXT,
            chunk_index     INTEGER DEFAULT 0,
            importance      REAL    DEFAULT 0.5,
            pain            REAL    DEFAULT 0.2,
            section         TEXT    DEFAULT NULL,
            section_boost   REAL    DEFAULT 1.0,
            retention_days  INTEGER DEFAULT 90,
            created_at      TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            updated_at      TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);

        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            chunk_text,
            content='chunks',
            content_rowid='id'
        );
        """
    )

    BATCH_SIZE = 500
    count = 0
    batch: list[tuple[str, str, str, int]] = []

    for chunk in chunks:
        provenance = json.dumps(
            {
                "session_id": chunk["session_id"],
                "turn_start": chunk["turn_start"],
                "turn_end": chunk["turn_end"],
                "memory_ids": chunk.get("memory_ids", []),
                "corpus": "memorybank",
            },
            ensure_ascii=False,
        )
        batch.append(
            (chunk["chunk_id"], chunk["chunk_text"], provenance, chunk["chunk_index"])
        )
        count += 1

        if len(batch) >= BATCH_SIZE:
            conn.executemany(
                "INSERT INTO chunks (doc_id, chunk_text, source_file, chunk_index) "
                "VALUES (?, ?, ?, ?)",
                batch,
            )
            conn.commit()
            batch = []

    if batch:
        conn.executemany(
            "INSERT INTO chunks (doc_id, chunk_text, source_file, chunk_index) "
            "VALUES (?, ?, ?, ?)",
            batch,
        )
        conn.commit()

    logger.info("Building FTS5 index on %d chunks…", count)
    conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
    conn.commit()
    conn.close()

    assert count > 0, f"No chunks written to TEMP DB {db_path}."
    logger.info("TEMP DB created: %d chunks → %s", count, db_path)
    return db_path


# ---------------------------------------------------------------------------
# Stage 4 — QA extraction + stratified subset selection
# ---------------------------------------------------------------------------


def _normalise_type(raw_type: str) -> str:
    """Normalise a raw MemoryBank question type to a canonical key.

    Args:
        raw_type: Raw type string from the MemoryBank dataset.

    Returns:
        Canonical type string (one of the 5 canonical types) or
        the lowercased normalised input if no mapping found.
    """
    normalised = raw_type.strip().lower().replace(" ", "_").replace("-", "_")
    return _QUESTION_TYPE_MAP.get(normalised, normalised)


def _find_relevant_chunks(
    qa_pair: dict[str, Any],
    session_chunks: list[ChunkRecord],
    memory_items: list[MemoryItem],
) -> list[str]:
    """Find chunk IDs relevant to a QA pair.

    Relevance is determined by two paths (in priority order):
    1. Gold memory IDs: if qa_pair has "memory_ids", find all chunks whose
       chunk_id ends with one of those memory IDs (direct memory chunk match).
    2. Content substring: find chunks whose text contains the content of any
       gold memory item (case-insensitive, >=_MIN_EVIDENCE_LEN chars).
    3. Answer substring fallback: if answer is long enough (>=30 chars), find
       chunks containing the answer text.

    Args:
        qa_pair: QA pair dict from MemoryBank session.
        session_chunks: All chunks belonging to this session.
        memory_items: Memory items for this session.

    Returns:
        List of relevant chunk_id strings (deduplicated, preserving order).
    """
    relevant_ids: list[str] = []
    seen: set[str] = set()

    def _add(cid: str) -> None:
        if cid not in seen:
            seen.add(cid)
            relevant_ids.append(cid)

    # Path 1: direct memory_id match
    gold_mem_ids: list[str] = []
    raw_mem_ids = qa_pair.get("memory_ids") or qa_pair.get("evidence_ids") or []
    if isinstance(raw_mem_ids, list):
        gold_mem_ids = [str(x) for x in raw_mem_ids if x]
    elif isinstance(raw_mem_ids, str) and raw_mem_ids:
        gold_mem_ids = [raw_mem_ids]

    if gold_mem_ids:
        for chunk in session_chunks:
            chunk_mem_ids = chunk.get("memory_ids", [])
            for gid in gold_mem_ids:
                if gid in chunk_mem_ids or chunk["chunk_id"].endswith(f"_{gid}"):
                    _add(chunk["chunk_id"])
                    break

    # Path 2: content substring match against gold memory items
    gold_memory_texts: list[str] = []
    if gold_mem_ids:
        mem_by_id = {
            str(m.get("memory_id") or f"m{i:04d}"): m
            for i, m in enumerate(memory_items)
        }
        for gid in gold_mem_ids:
            mem = mem_by_id.get(gid)
            if mem:
                content = (mem.get("content") or mem.get("text") or "").strip()
                if len(content) >= _MIN_EVIDENCE_LEN:
                    gold_memory_texts.append(content)
    else:
        # No explicit memory_ids — use all memory items as candidate evidence
        gold_memory_texts = [
            (m.get("content") or m.get("text") or "").strip()
            for m in memory_items
            if len((m.get("content") or m.get("text") or "").strip()) >= _MIN_EVIDENCE_LEN
        ]

    if gold_memory_texts:
        for chunk in session_chunks:
            chunk_lower = chunk["chunk_text"].lower()
            for mem_text in gold_memory_texts:
                if mem_text.lower() in chunk_lower:
                    _add(chunk["chunk_id"])
                    break

    # Path 3: answer substring fallback
    if not relevant_ids:
        answer = (qa_pair.get("answer") or "").strip()
        if len(answer) >= 30:
            for chunk in session_chunks:
                if answer.lower() in chunk["chunk_text"].lower():
                    _add(chunk["chunk_id"])

    return relevant_ids


def extract_qa_records(
    sessions: list[SessionData],
    chunks: list[ChunkRecord],
) -> list[QARecord]:
    """Extract all QA pairs from MemoryBank sessions with evidence-linked chunk IDs.

    Args:
        sessions: List of SessionData dicts (from download_memorybank).
        chunks: Flat list of ChunkRecord dicts (from chunk_all_sessions).

    Returns:
        List of QARecord dicts with keys:
        - qa_id: str (f"{session_id}_q{qa_index:04d}")
        - session_id: str
        - question: str
        - answer: str
        - type: str (normalised canonical type)
        - gold_memory_ids: list[str]
        - relevant_chunk_ids: list[str] (chunks containing evidence)
        - n_relevant: int
    """
    # Build session → chunks lookup
    session_chunks: dict[str, list[ChunkRecord]] = {}
    for chunk in chunks:
        sid = chunk["session_id"]
        session_chunks.setdefault(sid, []).append(chunk)

    # Build session → memory items lookup
    session_memories: dict[str, list[MemoryItem]] = {
        s["session_id"]: list(s.get("memory_items") or [])
        for s in sessions
    }

    qa_records: list[QARecord] = []
    total_qa = 0
    zero_evidence = 0

    for session in sessions:
        sid = session["session_id"]
        qa_list = session.get("qa_pairs") or []
        if not isinstance(qa_list, list):
            qa_list = list(qa_list)

        s_chunks = session_chunks.get(sid, [])
        s_mems = session_memories.get(sid, [])

        for q_idx, qa in enumerate(qa_list):
            if not isinstance(qa, dict):
                continue

            question = (qa.get("question") or "").strip()
            if not question:
                continue

            answer = (qa.get("answer") or "").strip()
            raw_type = (qa.get("question_type") or qa.get("type") or "").strip()
            q_type = _normalise_type(raw_type) if raw_type else "factual_recall"

            gold_mem_ids_raw = qa.get("memory_ids") or qa.get("evidence_ids") or []
            gold_mem_ids = (
                [str(x) for x in gold_mem_ids_raw if x]
                if isinstance(gold_mem_ids_raw, list)
                else [str(gold_mem_ids_raw)] if gold_mem_ids_raw else []
            )

            relevant_chunk_ids = _find_relevant_chunks(qa, s_chunks, s_mems)

            total_qa += 1
            if not relevant_chunk_ids:
                zero_evidence += 1

            qa_records.append({
                "qa_id": f"{sid}_q{q_idx:04d}",
                "session_id": sid,
                "question": question,
                "answer": answer,
                "type": q_type,
                "gold_memory_ids": gold_mem_ids,
                "relevant_chunk_ids": relevant_chunk_ids,
                "n_relevant": len(relevant_chunk_ids),
            })

    logger.info(
        "Extracted %d QA records (%d with zero evidence chunks)",
        total_qa, zero_evidence,
    )
    if total_qa > 0 and zero_evidence > total_qa * 0.4:
        logger.warning(
            "%.0f%% QA records have no evidence-linked chunks — "
            "check memory_ids field and chunk coverage.",
            100 * zero_evidence / total_qa,
        )
    return qa_records


def select_stratified_subset(
    qa_records: list[QARecord],
    n_per_type: int = _SUBSET_PER_TYPE,
    seed: int = _DEFAULT_SEED,
    require_evidence: bool = False,
) -> list[QARecord]:
    """Select a stratified 100-query subset: n_per_type per question type.

    Selection strategy:
    - Shuffle within each type bucket using seed=42 for reproducibility.
    - For each of the 5 canonical types: take min(n_per_type, available).
    - If a type has 0 examples, log a warning (MemoryBank may have fewer types).
    - If require_evidence is True, skip QA pairs with no relevant chunks.

    Args:
        qa_records: Full list of extracted QARecords.
        n_per_type: Target count per question type (default: 20).
        seed: Random seed for within-type shuffling.
        require_evidence: If True, skip QA pairs with zero evidence chunks.

    Returns:
        Stratified subset, length <= n_per_type * len(_CANONICAL_TYPES).
    """
    rng = random.Random(seed)

    by_type: dict[str, list[QARecord]] = {t: [] for t in _CANONICAL_TYPES}
    overflow: list[QARecord] = []  # unknown types

    for qa in qa_records:
        q_type = qa["type"]
        if require_evidence and qa["n_relevant"] == 0:
            continue
        if q_type in by_type:
            by_type[q_type].append(qa)
        else:
            overflow.append(qa)

    # Shuffle within each type for representative sampling
    for q_type in by_type:
        rng.shuffle(by_type[q_type])

    subset: list[QARecord] = []
    for q_type in _CANONICAL_TYPES:
        bucket = by_type[q_type][:n_per_type]
        subset.extend(bucket)
        available = len(by_type[q_type])
        logger.info(
            "Type '%s': %d selected / %d available", q_type, len(bucket), available
        )
        if available == 0:
            logger.warning(
                "Type '%s' has 0 QA pairs — consider remapping unknown types.", q_type
            )

    # If total < n_per_type * 5, backfill from overflow
    deficit = _TOTAL_SUBSET - len(subset)
    if deficit > 0 and overflow:
        rng.shuffle(overflow)
        backfill = overflow[:deficit]
        subset.extend(backfill)
        logger.info("Backfilled %d queries from unknown types.", len(backfill))

    logger.info("Stratified subset: %d queries total (seed=%d)", len(subset), seed)
    return subset


def write_eval_queries(
    qa_subset: list[QARecord],
    output_path: str | Path,
) -> Path:
    """Write the stratified subset to a JSONL eval queries file.

    Output format (one JSON object per line):

    .. code-block:: json

        {
          "query_id": "session_001_q0003",
          "query_text": "What does Alice prefer to eat for breakfast?",
          "session_id": "session_001",
          "type": "preference_inference",
          "expected_chunk_ids": ["session_001_mem_m002", "session_001_c0003"],
          "n_relevant": 2,
          "gold_memory_ids": ["m002"]
        }

    Args:
        qa_subset: Selected QA records (from select_stratified_subset).
        output_path: Destination path for the output JSONL file.

    Returns:
        Path to the written JSONL file.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", encoding="utf-8") as fh:
        for qa in qa_subset:
            record: dict[str, Any] = {
                "query_id": qa["qa_id"],
                "query_text": qa["question"],
                "session_id": qa["session_id"],
                "type": qa["type"],
                "expected_chunk_ids": qa["relevant_chunk_ids"],
                "n_relevant": qa["n_relevant"],
                "gold_memory_ids": qa["gold_memory_ids"],
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info("Eval queries written: %d → %s", len(qa_subset), out)
    return out


# ---------------------------------------------------------------------------
# Stage 5 — nox-mem search via HTTP API
# ---------------------------------------------------------------------------


def run_nox_mem_search(
    query_text: str,
    k: int = _DEFAULT_K,
    api_url: str = _DEFAULT_API_URL,
) -> list[SearchHit]:
    """Search nox-mem via the HTTP API and return ranked (doc_id, score) pairs.

    The nox-mem HTTP API must be running on api_url with NOX_DB_PATH pointing
    at the MemoryBank TEMP DB (not the production DB).

    Args:
        query_text: Natural-language question from MemoryBank QA pair.
        k: Number of results to retrieve.
        api_url: Base URL of the nox-mem HTTP API.

    Returns:
        List of (doc_id_str, score) tuples sorted by score descending, length <= k.

    Raises:
        RuntimeError: If the HTTP request fails.
        ImportError: If requests is not installed.
    """
    try:
        import requests  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError("requests is not installed. Run: pip install requests") from exc

    payload: dict[str, Any] = {
        _NOX_SEARCH_PAYLOAD_QUERY: query_text,
        _NOX_SEARCH_PAYLOAD_LIMIT: k,
        _NOX_SEARCH_PAYLOAD_HYBRID: True,
    }

    try:
        response = requests.post(
            f"{api_url.rstrip('/')}/api/search",
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
    except Exception as exc:
        raise RuntimeError(
            f"nox-mem API request failed for query '{query_text[:60]}': {exc}\n"
            f"Is the API running at {api_url} with NOX_DB_PATH=/tmp/nox-mem-memorybank.db?"
        ) from exc

    data: dict[str, Any] = response.json()
    results: list[dict[str, Any]] = data.get("results", [])

    hits: list[SearchHit] = []
    for item in results[:k]:
        doc_id_str: str = str(item.get("doc_id") or item.get("id", ""))
        score: float = float(item.get("score", 0.0))
        if doc_id_str:
            hits.append((doc_id_str, score))

    return hits


# ---------------------------------------------------------------------------
# Dry-run FTS5 search (CPU-only, no API needed)
# ---------------------------------------------------------------------------


def run_fts5_search(
    query_text: str,
    db_path: str | Path,
    k: int = _DEFAULT_K,
) -> list[SearchHit]:
    """Search the TEMP DB via FTS5 BM25 directly (no API, no vectors required).

    Used for the dry-run smoke test.

    Args:
        query_text: Natural-language query string.
        db_path: Path to the MemoryBank TEMP SQLite DB.
        k: Number of results to return.

    Returns:
        List of (chunk_id_str, bm25_score) tuples, sorted by score descending.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"TEMP DB not found: {db_path}")

    tokens = re.findall(r'\w+', query_text.lower())
    if not tokens:
        return []

    fts_query = " OR ".join(f'"{t}"' for t in tokens[:10])

    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        try:
            rows = conn.execute(
                """
                SELECT c.doc_id, bm25(chunks_fts) AS score
                FROM chunks_fts
                JOIN chunks c ON c.id = chunks_fts.rowid
                WHERE chunks_fts MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (fts_query, k),
            ).fetchall()
        except sqlite3.OperationalError as exc:
            logger.warning("FTS5 query failed (%s) — retrying with simpler form.", exc)
            simple_query = tokens[0] if tokens else "*"
            rows = conn.execute(
                """
                SELECT c.doc_id, bm25(chunks_fts) AS score
                FROM chunks_fts
                JOIN chunks c ON c.id = chunks_fts.rowid
                WHERE chunks_fts MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (simple_query, k),
            ).fetchall()

    # bm25() returns negative values in SQLite FTS5; negate for ranking
    return [(row[0], -row[1]) for row in rows]


# ---------------------------------------------------------------------------
# Metric helpers (binary relevance — same formulae as locomo_adapter.py)
# ---------------------------------------------------------------------------


def _ndcg_at_k(retrieved: list[str], gold: set[str], k: int = 10) -> float:
    """Compute nDCG@k with binary relevance.

    Args:
        retrieved: Ordered list of retrieved chunk IDs (rank 1 = index 0).
        gold: Set of relevant chunk IDs.
        k: Cutoff rank.

    Returns:
        nDCG@k in [0.0, 1.0].
    """
    if not gold:
        return 0.0
    dcg = sum(
        1.0 / math.log2(rank + 2)
        for rank, cid in enumerate(retrieved[:k])
        if cid in gold
    )
    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(gold), k)))
    return dcg / idcg if idcg > 0.0 else 0.0


def _mrr(retrieved: list[str], gold: set[str]) -> float:
    """Compute MRR for a single query.

    Args:
        retrieved: Ordered list of retrieved chunk IDs.
        gold: Set of relevant chunk IDs.

    Returns:
        Reciprocal rank of first relevant result, or 0.0 if none.
    """
    for rank, cid in enumerate(retrieved, start=1):
        if cid in gold:
            return 1.0 / rank
    return 0.0


def _recall_at_k(retrieved: list[str], gold: set[str], k: int = 10) -> float:
    """Compute Recall@k.

    Args:
        retrieved: Ordered list of retrieved chunk IDs.
        gold: Set of relevant chunk IDs.
        k: Cutoff rank.

    Returns:
        Fraction of gold chunks found in top-k.
    """
    if not gold:
        return 0.0
    return sum(1 for cid in retrieved[:k] if cid in gold) / len(gold)


def _precision_at_k(retrieved: list[str], gold: set[str], k: int = 5) -> float:
    """Compute Precision@k.

    Args:
        retrieved: Ordered list of retrieved chunk IDs.
        gold: Set of relevant chunk IDs.
        k: Cutoff rank.

    Returns:
        Fraction of top-k results that are relevant.
    """
    if k == 0:
        return 0.0
    return sum(1 for cid in retrieved[:k] if cid in gold) / k


# ---------------------------------------------------------------------------
# Stage 5 — Full evaluation loop
# ---------------------------------------------------------------------------


def evaluate_all(
    eval_queries_jsonl: str | Path,
    output_results_jsonl: str | Path,
    k: int = _DEFAULT_K,
    api_url: str = _DEFAULT_API_URL,
) -> dict[str, float]:
    """Run nox-mem search over all eval queries and compute aggregate metrics.

    Output format (per-query, compatible with results/ aggregator):

    .. code-block:: json

        {
          "query_id": "session_001_q0003",
          "query_text": "What does Alice prefer for breakfast?",
          "session_id": "session_001",
          "type": "preference_inference",
          "variant": "nox-hybrid-memorybank",
          "retrieved_chunk_ids": ["session_001_mem_m002"],
          "retrieved_scores": [0.852],
          "ndcg_at_10": 1.000,
          "mrr": 1.000,
          "recall_at_10": 1.000,
          "precision_at_5": 0.200,
          "n_relevant": 1,
          "duration_ms": 74
        }

    Args:
        eval_queries_jsonl: Path to eval queries JSONL (from write_eval_queries).
        output_results_jsonl: Destination path for per-query results JSONL.
        k: Number of results per query.
        api_url: nox-mem HTTP API base URL.

    Returns:
        Dict with aggregate metrics: ndcg_at_10, mrr, recall_at_10, precision_at_5,
        n_queries, plus per-type breakdown as ndcg_{type}.

    Raises:
        FileNotFoundError: If eval_queries_jsonl does not exist.
        AssertionError: If zero queries are evaluated.
    """
    eval_path = Path(eval_queries_jsonl)
    if not eval_path.exists():
        raise FileNotFoundError(f"Eval queries JSONL not found: {eval_path}")

    output_path = Path(output_results_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ndcg_sum = mrr_sum = recall_sum = prec_sum = 0.0
    n_queries = 0
    type_metrics: dict[str, dict[str, list[float]]] = {}

    with (
        eval_path.open(encoding="utf-8") as qfh,
        output_path.open("w", encoding="utf-8") as ofh,
    ):
        for raw in qfh:
            raw = raw.strip()
            if not raw:
                continue
            q: EvalQuery = json.loads(raw)

            query_id: str = str(q["query_id"])
            query_text: str = q["query_text"]
            gold: set[str] = set(str(c) for c in q.get("expected_chunk_ids", []))
            q_type: str = q.get("type", "unknown")

            t0 = time.monotonic()
            try:
                hits = run_nox_mem_search(query_text, k=k, api_url=api_url)
            except RuntimeError as exc:
                logger.error("Search failed for query %s: %s", query_id, exc)
                hits = []
            duration_ms = int((time.monotonic() - t0) * 1_000)

            retrieved_ids = [doc_id for doc_id, _ in hits]
            retrieved_scores = [score for _, score in hits]

            ndcg = _ndcg_at_k(retrieved_ids, gold, k=10)
            mrr_ = _mrr(retrieved_ids, gold)
            recall = _recall_at_k(retrieved_ids, gold, k=10)
            prec5 = _precision_at_k(retrieved_ids, gold, k=5)

            ndcg_sum += ndcg
            mrr_sum += mrr_
            recall_sum += recall
            prec_sum += prec5
            n_queries += 1

            type_metrics.setdefault(q_type, {
                "ndcg": [], "mrr": [], "recall": [], "prec": [],
            })
            type_metrics[q_type]["ndcg"].append(ndcg)
            type_metrics[q_type]["mrr"].append(mrr_)
            type_metrics[q_type]["recall"].append(recall)
            type_metrics[q_type]["prec"].append(prec5)

            record: dict[str, Any] = {
                "query_id": query_id,
                "query_text": query_text,
                "session_id": q.get("session_id", ""),
                "type": q_type,
                "variant": "nox-hybrid-memorybank",
                "retrieved_chunk_ids": retrieved_ids,
                "retrieved_scores": [round(s, 6) for s in retrieved_scores],
                "ndcg_at_10": round(ndcg, 6),
                "mrr": round(mrr_, 6),
                "recall_at_10": round(recall, 6),
                "precision_at_5": round(prec5, 6),
                "n_relevant": len(gold),
                "duration_ms": duration_ms,
            }
            ofh.write(json.dumps(record, ensure_ascii=False) + "\n")

            if n_queries % 25 == 0:
                logger.info(
                    "Progress: %d queries — nDCG@10=%.3f MRR=%.3f",
                    n_queries, ndcg_sum / n_queries, mrr_sum / n_queries,
                )

    assert n_queries > 0, "No queries evaluated — check eval_queries_jsonl."

    aggregates: dict[str, float] = {
        "ndcg_at_10": round(ndcg_sum / n_queries, 6),
        "mrr": round(mrr_sum / n_queries, 6),
        "recall_at_10": round(recall_sum / n_queries, 6),
        "precision_at_5": round(prec_sum / n_queries, 6),
        "n_queries": float(n_queries),
    }

    for q_type, m in type_metrics.items():
        n_t = len(m["ndcg"])
        if n_t:
            aggregates[f"ndcg_{q_type}"] = round(sum(m["ndcg"]) / n_t, 6)
            aggregates[f"mrr_{q_type}"] = round(sum(m["mrr"]) / n_t, 6)

    logger.info(
        "Eval complete — %d queries | nDCG@10=%.4f | MRR=%.4f | "
        "Recall@10=%.4f | Prec@5=%.4f",
        n_queries,
        aggregates["ndcg_at_10"],
        aggregates["mrr"],
        aggregates["recall_at_10"],
        aggregates["precision_at_5"],
    )
    logger.info("Results written → %s", output_path)
    return aggregates


# ---------------------------------------------------------------------------
# Comparison table
# ---------------------------------------------------------------------------


def compare_with_baselines(
    nox_results_jsonl: str | Path,
    bm25_results_jsonl: str | Path | None = None,
    output_csv: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Generate cross-system comparison table for paper §5.2 Table 5.

    Args:
        nox_results_jsonl: Path to nox-mem hybrid results JSONL.
        bm25_results_jsonl: Optional BM25 results JSONL on same subset.
        output_csv: Optional output CSV path.

    Returns:
        List of per-system metric dicts.
    """
    def _load(path: Path) -> dict[str, Any]:
        metrics: dict[str, list[float]] = {
            "ndcg_at_10": [], "mrr": [], "recall_at_10": [], "precision_at_5": [],
        }
        variant = path.stem
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if "variant" in rec:
                    variant = rec["variant"]
                for key in metrics:
                    metrics[key].append(float(rec.get(key, 0.0)))
        n = len(metrics["ndcg_at_10"])
        return {
            "variant": variant,
            "ndcg_at_10": round(sum(metrics["ndcg_at_10"]) / n, 4) if n else 0.0,
            "mrr": round(sum(metrics["mrr"]) / n, 4) if n else 0.0,
            "recall_at_10": round(sum(metrics["recall_at_10"]) / n, 4) if n else 0.0,
            "precision_at_5": round(sum(metrics["precision_at_5"]) / n, 4) if n else 0.0,
            "n_queries": n,
        }

    rows: list[dict[str, Any]] = [_load(Path(nox_results_jsonl))]

    if bm25_results_jsonl is not None:
        p = Path(bm25_results_jsonl)
        if p.exists():
            rows.append(_load(p))
        else:
            logger.warning("BM25 results not found at %s — skipping.", p)

    rows.sort(key=lambda r: r["ndcg_at_10"], reverse=True)

    header = (
        f"{'System':<32} | {'nDCG@10':>8} | {'MRR':>8} | "
        f"{'R@10':>8} | {'P@5':>7} | {'N':>5}"
    )
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)
    for row in rows:
        print(
            f"{row['variant']:<32} | {row['ndcg_at_10']:>8.4f} | "
            f"{row['mrr']:>8.4f} | {row['recall_at_10']:>8.4f} | "
            f"{row['precision_at_5']:>7.4f} | {row['n_queries']:>5}"
        )
    print(sep)

    if output_csv is not None:
        csv_path = Path(output_csv)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "variant", "ndcg_at_10", "mrr", "recall_at_10", "precision_at_5", "n_queries",
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as csvf:
            writer = csv.DictWriter(csvf, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        logger.info("Comparison CSV → %s", csv_path)

    return rows


# ---------------------------------------------------------------------------
# Manifest writer (smoke-test artifact for --download-only)
# ---------------------------------------------------------------------------


def write_manifest(
    sessions: list[SessionData],
    chunks: list[ChunkRecord],
    qa_records: list[QARecord],
    subset: list[QARecord],
    manifest_path: str | Path,
    acquisition_method: str = "github_clone",
) -> Path:
    """Write a JSON manifest summarising the downloaded dataset.

    Args:
        sessions: List of MemoryBank sessions.
        chunks: All chunks across all sessions.
        qa_records: All extracted QA records.
        subset: Stratified 100-query subset.
        manifest_path: Output path for the JSON manifest.
        acquisition_method: How the data was obtained (github_clone/huggingface).

    Returns:
        Path to the written manifest.
    """
    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    type_counts: dict[str, int] = {}
    for qa in qa_records:
        type_counts[qa["type"]] = type_counts.get(qa["type"], 0) + 1

    subset_type_counts: dict[str, int] = {}
    for qa in subset:
        subset_type_counts[qa["type"]] = subset_type_counts.get(qa["type"], 0) + 1

    avg_chunk_chars = (
        sum(len(c["chunk_text"]) for c in chunks) / len(chunks) if chunks else 0
    )
    coverage = sum(1 for qa in qa_records if qa["n_relevant"] > 0)

    mem_chunks = sum(1 for c in chunks if c.get("memory_ids"))
    conv_chunks = len(chunks) - mem_chunks

    manifest = {
        "dataset": "MemoryBank-SiliconFriend",
        "paper": "Zhong et al. (2023) arXiv:2305.10250",
        "acquisition_method": acquisition_method,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sessions": {
            "total": len(sessions),
            "session_ids": [s["session_id"] for s in sessions[:20]],  # cap for manifest size
        },
        "chunks": {
            "total": len(chunks),
            "memory_item_chunks": mem_chunks,
            "conversation_chunks": conv_chunks,
            "avg_chars": round(avg_chunk_chars),
            "target_chars": _CHUNK_TARGET_CHARS,
            "overlap_chars": _CHUNK_OVERLAP_CHARS,
        },
        "qa_records": {
            "total": len(qa_records),
            "with_evidence_chunks": coverage,
            "evidence_coverage_pct": round(100 * coverage / len(qa_records)) if qa_records else 0,
            "by_type": type_counts,
        },
        "subset": {
            "total": len(subset),
            "n_per_type_target": _SUBSET_PER_TYPE,
            "by_type": subset_type_counts,
        },
        "params": {
            "min_evidence_len": _MIN_EVIDENCE_LEN,
            "seed": _DEFAULT_SEED,
            "canonical_types": _CANONICAL_TYPES,
        },
    }

    with manifest_path.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)

    logger.info("Manifest written → %s", manifest_path)
    return manifest_path


# ---------------------------------------------------------------------------
# Dry-run: download + build DB + FTS5 search on n_queries (no API)
# ---------------------------------------------------------------------------


def run_dry_run(
    clone_dir: str | Path,
    db_path: str | Path,
    manifest_path: str | Path,
    n_queries: int = 3,
    cache_dir: str | Path | None = None,
) -> None:
    """Smoke test: download, chunk, index, FTS5 search on n_queries, write manifest.

    Args:
        clone_dir: Git clone directory for MemoryBank repo.
        db_path: Path for the TEMP SQLite DB.
        manifest_path: Path for the JSON manifest.
        n_queries: Number of queries to run FTS5 search on.
        cache_dir: HuggingFace cache dir (for fallback).
    """
    t_start = time.monotonic()
    _check_load_avg()

    logger.info("=== DRY RUN — download + chunk + index + %d FTS5 queries ===", n_queries)

    sessions, method = download_memorybank(clone_dir=clone_dir, cache_dir=cache_dir)
    logger.info("Acquired %d sessions via %s", len(sessions), method)

    chunks = chunk_all_sessions(sessions)
    build_temp_db(chunks, db_path=db_path)

    qa_records = extract_qa_records(sessions, chunks)
    subset = select_stratified_subset(qa_records)

    write_manifest(sessions, chunks, qa_records, subset, manifest_path, method)

    logger.info("Running FTS5 dry-run on %d queries…", min(n_queries, len(subset)))
    for i, qa in enumerate(subset[:n_queries]):
        t0 = time.monotonic()
        try:
            hits = run_fts5_search(qa["question"], db_path=db_path)
        except Exception as exc:
            logger.warning("FTS5 search failed for query %s: %s", qa["qa_id"], exc)
            hits = []
        duration_ms = int((time.monotonic() - t0) * 1_000)

        retrieved_ids = [h[0] for h in hits]
        gold = set(qa["relevant_chunk_ids"])
        ndcg = _ndcg_at_k(retrieved_ids, gold)

        logger.info(
            "  [%d/%d] %s (%s) — hits=%d nDCG@10=%.3f gold_chunks=%d [%d ms]",
            i + 1, n_queries,
            qa["qa_id"], qa["type"],
            len(hits), ndcg, len(gold), duration_ms,
        )
        logger.info("    Q: %s", qa["question"][:80])
        if hits:
            logger.info("    Top-1: %s (score=%.3f)", hits[0][0], hits[0][1])

    elapsed = time.monotonic() - t_start
    logger.info(
        "Dry run complete in %.1f s. Manifest: %s, DB: %s",
        elapsed, manifest_path, db_path,
    )
    logger.info(
        "Next: vectorize TEMP DB, then start nox-mem API:\n"
        f"  NOX_DB_PATH={db_path} nox-mem vectorize --all\n"
        f"  NOX_DB_PATH={db_path} node dist/index.js serve\n"
        "  curl http://localhost:18802/api/health | jq .vectorCoverage"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for all sub-commands.

    Returns:
        Configured ArgumentParser with sub-commands: download-only, build-db,
        convert-queries, eval, compare, dry-run, full.
    """
    parser = argparse.ArgumentParser(
        prog="memorybank_adapter",
        description=(
            "MemoryBank benchmark adapter for nox-mem conversational memory eval (W2). "
            "Pipeline: download-only → build-db → convert-queries → "
            "[vectorize+serve] → eval → compare."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def _add_clone(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--clone-dir",
            default=_DEFAULT_CLONE_DIR,
            metavar="DIR",
            help=f"Git clone directory for MemoryBank repo (default: {_DEFAULT_CLONE_DIR}).",
        )
        p.add_argument(
            "--cache-dir",
            default=None,
            metavar="DIR",
            help="HuggingFace dataset cache directory (for fallback if git fails).",
        )

    def _add_db(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--db",
            default=os.environ.get("MEMORYBANK_TEMP_DB", _DEFAULT_TEMP_DB),
            metavar="PATH",
            help=f"TEMP SQLite DB path (default: {_DEFAULT_TEMP_DB} or $MEMORYBANK_TEMP_DB).",
        )

    # ---- download-only / dry-run -------------------------------------------
    for cmd_name in ("download-only", "dry-run"):
        dl = sub.add_parser(
            cmd_name,
            help=(
                "Smoke test: clone MemoryBank, chunk, index, run 3 FTS5 queries, "
                "write manifest. Target: <60 s."
            ),
        )
        _add_clone(dl)
        _add_db(dl)
        dl.add_argument(
            "--manifest",
            default=_DEFAULT_MANIFEST,
            metavar="PATH",
            help=f"Output manifest JSON path (default: {_DEFAULT_MANIFEST}).",
        )
        dl.add_argument(
            "--n",
            type=int,
            default=3,
            metavar="N",
            help="Number of FTS5 queries to dry-run (default: 3).",
        )

    # ---- build-db -----------------------------------------------------------
    bdb = sub.add_parser(
        "build-db",
        help="Chunk all MemoryBank sessions and build TEMP SQLite DB with FTS5.",
    )
    _add_clone(bdb)
    _add_db(bdb)
    bdb.add_argument(
        "--force",
        action="store_true",
        help="Force DB recreation even if it already exists.",
    )

    # ---- convert-queries ----------------------------------------------------
    cq = sub.add_parser(
        "convert-queries",
        help="Extract stratified 100-query subset and write eval JSONL.",
    )
    _add_clone(cq)
    _add_db(cq)
    cq.add_argument(
        "--output",
        default="/tmp/memorybank-eval-queries.jsonl",
        metavar="PATH",
        help="Output eval queries JSONL (default: /tmp/memorybank-eval-queries.jsonl).",
    )
    cq.add_argument(
        "--n-per-type",
        type=int,
        default=_SUBSET_PER_TYPE,
        metavar="N",
        help=f"Queries per question type (default: {_SUBSET_PER_TYPE}).",
    )
    cq.add_argument(
        "--require-evidence",
        action="store_true",
        help="Skip QA pairs with no evidence-linked chunks.",
    )
    cq.add_argument(
        "--seed",
        type=int,
        default=_DEFAULT_SEED,
        help=f"Random seed for within-type shuffling (default: {_DEFAULT_SEED}).",
    )

    # ---- eval ---------------------------------------------------------------
    ev = sub.add_parser(
        "eval",
        help="Run nox-mem search over all eval queries and compute metrics.",
    )
    ev.add_argument("--queries", required=True, metavar="PATH",
                    help="Path to eval queries JSONL (from 'convert-queries').")
    ev.add_argument("--output", default="/tmp/memorybank-results.jsonl", metavar="PATH",
                    help="Output results JSONL.")
    ev.add_argument("--api-url", default=_DEFAULT_API_URL, metavar="URL",
                    help=f"nox-mem HTTP API base URL (default: {_DEFAULT_API_URL}).")
    ev.add_argument("--k", type=int, default=_DEFAULT_K, metavar="N",
                    help=f"Results per query (default: {_DEFAULT_K}).")

    # ---- compare ------------------------------------------------------------
    cmp = sub.add_parser(
        "compare",
        help="Generate cross-system comparison table for paper §5.2 Table 5.",
    )
    cmp.add_argument("--nox", required=True, metavar="PATH",
                     help="nox-mem results JSONL.")
    cmp.add_argument("--bm25", metavar="PATH",
                     help="BM25 results JSONL (optional).")
    cmp.add_argument("--csv", metavar="PATH",
                     help="Optional output CSV path.")

    # ---- full (end-to-end prep, no eval) ------------------------------------
    fl = sub.add_parser(
        "full",
        help="End-to-end: clone → build-db → convert-queries (no eval step).",
    )
    _add_clone(fl)
    _add_db(fl)
    fl.add_argument("--queries-output", default="/tmp/memorybank-eval-queries.jsonl",
                    metavar="PATH", help="Output eval queries JSONL.")
    fl.add_argument("--n-per-type", type=int, default=_SUBSET_PER_TYPE,
                    metavar="N", help=f"Queries per question type (default: {_SUBSET_PER_TYPE}).")
    fl.add_argument("--force", action="store_true", help="Force DB recreation.")
    fl.add_argument("--seed", type=int, default=_DEFAULT_SEED,
                    help=f"Random seed (default: {_DEFAULT_SEED}).")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the MemoryBank adapter CLI.

    Args:
        argv: Argument list (defaults to sys.argv[1:] when None).

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command in ("download-only", "dry-run"):
            _check_load_avg()
            run_dry_run(
                clone_dir=args.clone_dir,
                db_path=args.db,
                manifest_path=args.manifest,
                n_queries=args.n,
                cache_dir=getattr(args, "cache_dir", None),
            )

        elif args.command == "build-db":
            _check_load_avg()
            sessions, method = download_memorybank(
                clone_dir=args.clone_dir,
                cache_dir=getattr(args, "cache_dir", None),
            )
            chunks = chunk_all_sessions(sessions)
            db = build_temp_db(chunks, db_path=args.db, force=args.force)
            print(f"TEMP DB: {db}")
            print(
                "\nNext step: vectorize the TEMP DB, then start nox-mem API:\n"
                f"  NOX_DB_PATH={db} nox-mem vectorize --all\n"
                f"  NOX_DB_PATH={db} node dist/index.js serve\n"
                f"  curl http://localhost:18802/api/health | jq .vectorCoverage"
            )

        elif args.command == "convert-queries":
            sessions, _ = download_memorybank(
                clone_dir=args.clone_dir,
                cache_dir=getattr(args, "cache_dir", None),
            )
            chunks = chunk_all_sessions(sessions)
            qa_records = extract_qa_records(sessions, chunks)
            subset = select_stratified_subset(
                qa_records,
                n_per_type=args.n_per_type,
                seed=args.seed,
                require_evidence=args.require_evidence,
            )
            out = write_eval_queries(subset, output_path=args.output)
            print(f"Eval queries: {out}")
            print(f"Total: {len(subset)} queries")

        elif args.command == "eval":
            _check_load_avg()
            aggregates = evaluate_all(
                eval_queries_jsonl=args.queries,
                output_results_jsonl=args.output,
                k=args.k,
                api_url=args.api_url,
            )
            print("\n=== AGGREGATE METRICS (nox-mem hybrid, MemoryBank) ===")
            for metric, value in aggregates.items():
                if isinstance(value, float):
                    print(f"  {metric:<30} {value:.4f}")

        elif args.command == "compare":
            compare_with_baselines(
                nox_results_jsonl=args.nox,
                bm25_results_jsonl=getattr(args, "bm25", None),
                output_csv=getattr(args, "csv", None),
            )

        elif args.command == "full":
            _check_load_avg()
            sessions, method = download_memorybank(
                clone_dir=args.clone_dir,
                cache_dir=getattr(args, "cache_dir", None),
            )
            logger.info("Acquired %d sessions via %s", len(sessions), method)
            chunks = chunk_all_sessions(sessions)
            db = build_temp_db(chunks, db_path=args.db, force=args.force)
            qa_records = extract_qa_records(sessions, chunks)
            subset = select_stratified_subset(
                qa_records,
                n_per_type=args.n_per_type,
                seed=args.seed,
            )
            out = write_eval_queries(subset, output_path=args.queries_output)
            print(f"TEMP DB: {db}")
            print(f"Eval queries: {out} ({len(subset)} queries)")
            print(
                "\nNext: vectorize + start API, then eval:\n"
                f"  NOX_DB_PATH={db} nox-mem vectorize --all\n"
                f"  NOX_DB_PATH={db} node dist/index.js serve\n"
                f"  python memorybank_adapter.py eval \\\n"
                f"      --queries {out} \\\n"
                f"      --output /tmp/memorybank-results.jsonl \\\n"
                f"      --api-url http://localhost:18802"
            )

        return 0

    except RuntimeError as exc:
        logger.error("FATAL: %s", exc)
        return 1
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
