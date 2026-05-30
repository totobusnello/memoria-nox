"""
adapter_nox_mem.py — LoCoMo bench adapter for nox-mem.

Mirrors eval/longmemeval/run_crossbench.py (LongMemEval crossbench pattern,
PR #378). Differences specific to LoCoMo:

  - LoCoMo is **per-CONVERSATION** ingest (10 isolated DBs total, ~588 turns
    each), not per-question ingest. All ~199 QA pairs of a conversation share
    the same in-memory corpus. This is dramatically faster than LongMemEval's
    per-question pattern.
  - Categories are numeric 1..5 (mapped via lib/corpus_loader.CATEGORY_NAMES).
  - Scoring is QA-accuracy F1 (LoCoMo paper §5.2), NOT retrieval nDCG.
  - Cat 5 (adversarial) QA pairs have empty gold answers and require refusal.

Pipeline per conversation:
  1. Build fresh isolated DB at `${WORKDIR}/conv-{sample_id}.db`.
  2. Render each session as markdown via lib/corpus_loader.write_conversation_md_files.
  3. `nox-mem ingest` each session .md (inherits NOX_DB_PATH).
  4. `nox-mem vectorize` once at conversation end.
  5. Start nox-mem-api on isolated port pointed at this DB.
  6. For each QA pair in the conversation:
     a. POST /api/search with the augmented question (top-k=20).
     b. Build context from top-K chunks.
     c. Call gpt-4.1-mini generator with context + question.
     d. Record record (jsonl line).
  7. Stop API server, delete DB.

Safety:
  - NOX_DB_PATH must NOT resolve to prod /root/.openclaw/workspace/tools/nox-mem/nox-mem.db
  - API port must NOT be 18802 (prod)
  - Workdir under /root/.openclaw/locomo-bench-*  (op-audit ALLOWED_PREFIXES)

CLI:
  python3 adapter_nox_mem.py \\
      --locomo-json data/locomo10.json \\
      --workdir /root/.openclaw/locomo-bench-<uuid>/work \\
      --out results-smoke-100.jsonl \\
      --api-port 18840 \\
      --max-questions 100 \\
      --seed 42 \\
      --generator gpt-4.1-mini \\
      [--resume] \\
      [--no-vectorize]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Allow local lib/ import
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

from corpus_loader import (  # type: ignore[import-not-found]
    CATEGORY_NAMES,
    Conversation,
    QAPair,
    load_conversations,
    write_conversation_md_files,
)
from temporal_normalizer import (  # type: ignore[import-not-found]
    build_session_date_map,
    normalize_predicted_date,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_API_PORT = 18840
DEFAULT_TOP_K = 20
DEFAULT_INGEST_TIMEOUT = 240
DEFAULT_VECTORIZE_TIMEOUT = 900
DEFAULT_SEARCH_TIMEOUT = 30
DEFAULT_GENERATION_TIMEOUT = 40

PROD_DB_PATH = "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db"
API_SERVER_JS = "/root/.openclaw/workspace/tools/nox-mem/dist/api-server.js"
NODE_BIN = "/usr/bin/node"
ENV_FILE = "/root/.openclaw/.env"
DEFAULT_NOX_MEM_BIN = "/usr/local/bin/nox-mem"

OPENAI_URL = "https://api.openai.com/v1/chat/completions"


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------

@dataclass
class QAResult:
    sample_id: str            # conv id
    qa_index: int             # 0-based within conversation
    category: int             # 1..5
    category_name: str
    question: str
    augmented_question: str
    answer: str               # gold (may be empty for adversarial)
    evidence: list[str]       # gold dia_ids
    retrieved_chunk_ids: list[str] = field(default_factory=list)
    retrieved_scores: list[float] = field(default_factory=list)
    retrieved_texts: list[str] = field(default_factory=list)
    retrieved_dia_ids: list[str] = field(default_factory=list)
    retrieval_ms: float = 0.0
    generation_ms: float = 0.0
    generated_answer: str = ""
    generator_model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    embed_tokens: int = 0
    error: str | None = None
    # Backfilled later by aggregate (not by adapter):
    ingest_ms: float = 0.0
    vectorize_ms: float = 0.0


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------

def refuse_if_prod(db_path: str, api_port: int) -> None:
    norm = os.path.realpath(db_path)
    if norm == PROD_DB_PATH or norm.endswith("/workspace/tools/nox-mem/nox-mem.db"):
        raise SystemExit(f"refuse to use production DB: {norm}")
    if api_port == 18802:
        raise SystemExit(f"refuse to use production API port 18802")
    allowed = ("/var/backups/", "/root/.openclaw/")
    if not any(norm.startswith(p) for p in allowed):
        raise SystemExit(
            f"refuse db_path '{norm}': must start with one of {allowed} "
            f"(op-audit P1 safety guard)"
        )


# ---------------------------------------------------------------------------
# Env loading
# ---------------------------------------------------------------------------

def env_from_file(path: str) -> dict[str, str]:
    env: dict[str, str] = {}
    if not os.path.exists(path):
        return env
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], env: dict[str, str], timeout: int) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as e:
        return 124, e.stdout or "", e.stderr or "TIMEOUT"


# ---------------------------------------------------------------------------
# Schema patcher (same pattern as LongMemEval; dist is stale on V8-V18)
# ---------------------------------------------------------------------------

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


def patch_schema_v8_v18(db_path: str) -> str | None:
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
        cur.executescript(_KG_BOOTSTRAP_SQL)
        conn.commit()
        conn.close()
    except Exception as e:
        return f"sqlite open/exec failed: {type(e).__name__}: {e}"
    return None


def bootstrap_db(
    db_path: str, nox_mem_bin: str, env_base: dict[str, str], workdir: Path, conv_id: str
) -> str | None:
    env = dict(env_base)
    env["NOX_DB_PATH"] = db_path
    env["OPENCLAW_WORKSPACE"] = str(workdir / f"conv-{conv_id}")
    rc, out, err = _run([nox_mem_bin, "stats"], env=env, timeout=30)
    if rc != 0:
        return f"bootstrap rc={rc} err={err[:300]}"
    return patch_schema_v8_v18(db_path)


# ---------------------------------------------------------------------------
# Ingest + Vectorize
# ---------------------------------------------------------------------------

def ingest_conversation(
    conv: Conversation,
    db_path: str,
    workdir: Path,
    nox_mem_bin: str,
    env_base: dict[str, str],
) -> tuple[float, str | None]:
    t0 = time.time()
    qdir = workdir / f"conv-{conv.sample_id}"
    qdir.mkdir(parents=True, exist_ok=True)
    err = bootstrap_db(db_path, nox_mem_bin, env_base, workdir, conv.sample_id)
    if err:
        return (time.time() - t0) * 1000.0, err
    md_paths = write_conversation_md_files(conv, qdir)
    env = dict(env_base)
    env["NOX_DB_PATH"] = db_path
    env["OPENCLAW_WORKSPACE"] = str(qdir)
    for p in md_paths:
        rc, _out, errstr = _run(
            [nox_mem_bin, "ingest", str(p), "--allow-prod"],
            env=env, timeout=DEFAULT_INGEST_TIMEOUT,
        )
        if rc != 0:
            return (time.time() - t0) * 1000.0, (
                f"ingest rc={rc} file={p.name} err={errstr[:400]}"
            )
    return (time.time() - t0) * 1000.0, None


def vectorize_conversation(
    db_path: str, nox_mem_bin: str, env_base: dict[str, str], workdir: Path, conv_id: str
) -> tuple[float, str | None]:
    t0 = time.time()
    env = dict(env_base)
    env["NOX_DB_PATH"] = db_path
    env["OPENCLAW_WORKSPACE"] = str(workdir / f"conv-{conv_id}")
    rc, _out, err = _run(
        [nox_mem_bin, "vectorize"], env=env, timeout=DEFAULT_VECTORIZE_TIMEOUT
    )
    if rc != 0:
        return (time.time() - t0) * 1000.0, f"vectorize rc={rc} err={err[:400]}"
    return (time.time() - t0) * 1000.0, None


# ---------------------------------------------------------------------------
# API server lifecycle
# ---------------------------------------------------------------------------

def _wait_for_port(host: str, port: int, timeout: float = 25.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def _wait_for_health(api_base: str, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    url = api_base.rstrip("/") + "/api/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2.0) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def start_api_server(db_path: str, port: int, env_base: dict[str, str]) -> subprocess.Popen:
    env = dict(env_base)
    env["NOX_DB_PATH"] = db_path
    env["NOX_API_PORT"] = str(port)
    env["NOX_RERANKER_ENABLED"] = "0"     # Phase H v2 baseline
    env.setdefault("NOX_TEMPORAL_PATH", "shadow")
    env.setdefault("NOX_SALIENCE_MODE", "shadow")
    proc = subprocess.Popen(
        [NODE_BIN, "--no-warnings", API_SERVER_JS],
        cwd=os.path.dirname(API_SERVER_JS),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    if not _wait_for_port("127.0.0.1", port, timeout=25.0):
        _stop(proc)
        raise RuntimeError(f"API server failed to bind port {port} within 25s")
    if not _wait_for_health(f"http://127.0.0.1:{port}", timeout=20.0):
        _stop(proc)
        raise RuntimeError("API server bound port but /api/health unhealthy")
    return proc


def _stop(proc: subprocess.Popen) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass
    try:
        proc.wait(timeout=5)
    except Exception:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def stop_api_server(proc: subprocess.Popen) -> None:
    _stop(proc)


# ---------------------------------------------------------------------------
# Search + Generation
# ---------------------------------------------------------------------------

import re as _re
_DIA_ID_RE = _re.compile(r"dia_id:\s*(D\d+:\d+)")
_DIA_ID_HEAD_RE = _re.compile(r"\(dia_id:\s*(D\d+:\d+)\)")


def extract_dia_ids(text: str) -> list[str]:
    if not text:
        return []
    out = set(_DIA_ID_RE.findall(text))
    out.update(_DIA_ID_HEAD_RE.findall(text))
    return sorted(out)


def search_api(
    api_base: str, query: str, limit: int, timeout: int
) -> tuple[list[dict], float, str | None]:
    url = api_base.rstrip("/") + "/api/search"
    body = json.dumps({"query": query, "limit": limit, "hybrid": True}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"content-type": "application/json"}, method="POST"
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            j = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return [], (time.time() - t0) * 1000.0, f"{type(e).__name__}: {e}"
    ms = (time.time() - t0) * 1000.0
    if isinstance(j, list):
        return j, ms, None
    if isinstance(j, dict):
        hits = j.get("results") or j.get("hits") or []
        return hits if isinstance(hits, list) else [], ms, None
    return [], ms, None


def call_openai_generator(
    prompt: str,
    model: str,
    openai_key: str,
    timeout: int = DEFAULT_GENERATION_TIMEOUT,
    max_tokens: int = 256,
) -> tuple[str, float, int, int, str | None]:
    body = json.dumps({
        "model": model,
        "temperature": 0,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        OPENAI_URL,
        data=body,
        headers={
            "content-type": "application/json",
            "authorization": f"Bearer {openai_key}",
        },
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            j = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_str = ""
        try:
            body_str = e.read().decode("utf-8")[:400]
        except Exception:
            pass
        return "", (time.time() - t0) * 1000.0, 0, 0, f"HTTPError {e.code}: {body_str}"
    except Exception as e:
        return "", (time.time() - t0) * 1000.0, 0, 0, f"{type(e).__name__}: {e}"
    ms = (time.time() - t0) * 1000.0
    txt = (j.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
    usage = j.get("usage") or {}
    return (
        txt.strip(),
        ms,
        int(usage.get("prompt_tokens") or 0),
        int(usage.get("completion_tokens") or 0),
        None,
    )


def build_prompt(
    augmented_question: str, top_chunks: list[str], speaker_a: str, speaker_b: str
) -> str:
    ctx = "\n\n".join(
        f"--- chunk {i+1} ---\n{c[:1800]}" for i, c in enumerate(top_chunks[:10])
    )
    return (
        "You are answering a question about a very long-term conversation "
        f"between two people ({speaker_a} and {speaker_b}).\n"
        "Use ONLY the retrieved memory chunks below as evidence; do not "
        "invent facts.\n\n"
        f"Retrieved memory:\n{ctx or '[no context retrieved]'}\n\n"
        f"Question: {augmented_question}\n\n"
        "Answer in 1-5 words ONLY. Do not include explanations, justifications, "
        "or full sentences. Just the answer. "
        "If the memory does not contain the answer, say: Not mentioned\n\n"
        "Answer:"
    )


def build_prompt_sota(
    augmented_question: str,
    top_chunks: list[str],
    speaker_a: str,
    speaker_b: str,
    session_date_map: dict[str, str] | None,
    category_name: str,
) -> str:
    """
    SOTA push prompt (Variant A — LoCoMo F1 SOTA push 2026-05-29):

    1. Inject session_date_map ONLY for temporal questions (category 2).
    2. Explicit 'D Month YYYY' date format hint.
    3. Same 1-5 word constraint.

    Smoke 100q result: F1 51.79% vs constrained 50.38% (+1.41pp overall);
    temporal F1 51.54% vs 28.27% baseline (+23.27pp lift).
    """
    ctx = "\n\n".join(
        f"--- chunk {i+1} ---\n{c[:1800]}" for i, c in enumerate(top_chunks[:10])
    )

    date_block = ""
    if category_name == "temporal" and session_date_map:
        def sortkey(sid: str) -> int:
            try:
                return int(sid.split("_")[1])
            except Exception:
                return 0
        sorted_sids = sorted(session_date_map.keys(), key=sortkey)
        date_lines = ["Session dates (use these to anchor temporal answers):"]
        for sid in sorted_sids:
            date_lines.append(f"  - {sid}: {session_date_map[sid]}")
        date_block = "\n".join(date_lines) + "\n\n"

    return (
        "You are answering a question about a very long-term conversation "
        f"between two people ({speaker_a} and {speaker_b}).\n"
        "Use ONLY the retrieved memory chunks below as evidence; do not "
        "invent facts.\n\n"
        f"{date_block}"
        f"Retrieved memory:\n{ctx or '[no context retrieved]'}\n\n"
        f"Question: {augmented_question}\n\n"
        "Answer in 1-5 words ONLY. Format dates as 'D Month YYYY' (e.g. '7 May 2023'). "
        "Do not include explanations, justifications, or full sentences. "
        "Just the answer. If the memory does not contain the answer, say: Not mentioned\n\n"
        "Answer:"
    )


# Few-shot examples per category (LoCoMo).
# Design rationale: examples show the exact output format for each category
# type so the model internalises the 1-5 word constraint before seeing the
# real question. Three examples chosen to cover:
#   - temporal (date extraction task)
#   - single-hop entity recall
#   - multi-hop chained recall
# Adversarial / commonsense reuse the single-hop example (format identical).

_FEW_SHOT_TEMPORAL = """\
Example 1:
Q: When did Caroline move to Seattle?
A: 7 May 2019

Example 2:
Q: What month did Alex start his new job?
A: March 2021

Example 3:
Q: When was the last time they went hiking together?
A: 14 August 2022"""

_FEW_SHOT_SINGLE_HOP = """\
Example 1:
Q: What city was the meeting held in?
A: Tokyo

Example 2:
Q: What was the project codename?
A: Atlas

Example 3:
Q: What did Jordan bring as a gift?
A: cookbook"""

_FEW_SHOT_MULTI_HOP = """\
Example 1:
Q: Who introduced Alex to his current employer?
A: Sarah

Example 2:
Q: What language does the friend that Jordan met in Madrid speak natively?
A: Spanish

Example 3:
Q: Which city is home to the restaurant Caroline recommended to her sister?
A: Chicago"""

_FEW_SHOT_ADVERSARIAL = """\
Example 1:
Q: Did Jordan ever mention owning a helicopter?
A: Not mentioned

Example 2:
Q: What was the secret ingredient in the recipe Alex shared?
A: Not mentioned

Example 3:
Q: Where did they go on their Mars vacation?
A: Not mentioned"""

_FEW_SHOT_BY_CATEGORY: dict[str, str] = {
    "temporal": _FEW_SHOT_TEMPORAL,
    "single_hop": _FEW_SHOT_SINGLE_HOP,
    "multi_hop": _FEW_SHOT_MULTI_HOP,
    "adversarial": _FEW_SHOT_ADVERSARIAL,
    "commonsense": _FEW_SHOT_SINGLE_HOP,  # format identical
}


def build_prompt_few_shot(
    augmented_question: str,
    top_chunks: list[str],
    speaker_a: str,
    speaker_b: str,
    session_date_map: dict[str, str] | None,
    category_name: str,
) -> str:
    """
    Few-shot prompt (PR feat/few-shot-cross-bench, 2026-05-30).

    Builds on SOTA-push Variant A (session_date_map for temporal) and adds
    3 in-context examples per category before the real question.

    Gate prediction: +3-8pp F1 on extraction tasks via format anchoring.
    No additional LLM calls — prompt-only modification, latency neutral.
    """
    ctx = "\n\n".join(
        f"--- chunk {i+1} ---\n{c[:1800]}" for i, c in enumerate(top_chunks[:10])
    )

    date_block = ""
    if category_name == "temporal" and session_date_map:
        def sortkey(sid: str) -> int:
            try:
                return int(sid.split("_")[1])
            except Exception:
                return 0
        sorted_sids = sorted(session_date_map.keys(), key=sortkey)
        date_lines = ["Session dates (use these to anchor temporal answers):"]
        for sid in sorted_sids:
            date_lines.append(f"  - {sid}: {session_date_map[sid]}")
        date_block = "\n".join(date_lines) + "\n\n"

    examples = _FEW_SHOT_BY_CATEGORY.get(category_name, _FEW_SHOT_SINGLE_HOP)

    return (
        "You are answering a question about a very long-term conversation "
        f"between two people ({speaker_a} and {speaker_b}).\n"
        "Use ONLY the retrieved memory chunks below as evidence; do not "
        "invent facts.\n\n"
        f"{date_block}"
        f"Retrieved memory:\n{ctx or '[no context retrieved]'}\n\n"
        "Answer in 1-5 words ONLY. Format dates as 'D Month YYYY' (e.g. '7 May 2023'). "
        "Do not include explanations or full sentences. "
        "If the memory does not contain the answer, say: Not mentioned\n\n"
        f"{examples}\n\n"
        f"Q: {augmented_question}\n"
        "A:"
    )


# ---------------------------------------------------------------------------
# Preflight (billing path)
# ---------------------------------------------------------------------------

def preflight(openai_key: str, model: str) -> str | None:
    """
    Exercise the OpenAI billing path with a 5-token completion.
    Catches 'key valid but billing disabled' which a /v1/models 200 OK would
    NOT catch (lesson cravada Phase H v1 fail → v2 fix).
    """
    txt, ms, in_t, out_t, err = call_openai_generator(
        "Say 'ok' (2 letters)", model, openai_key, timeout=15, max_tokens=5
    )
    if err:
        return f"openai preflight failed: {err}"
    if not txt:
        return f"openai preflight returned empty text (in={in_t} out={out_t})"
    return None


# ---------------------------------------------------------------------------
# QA selection (stratified or first-N)
# ---------------------------------------------------------------------------

def stratified_qa_sample(
    convs: list[Conversation], max_n: int, seed: int = 42
) -> list[tuple[Conversation, QAPair]]:
    """
    Build a flat list of (conv, qa) pairs, stratify across 5 categories.

    Strategy: equal-per-category subsampling. If max_n=100 and 5 cats, take 20
    per cat. If a cat has fewer, take all available.

    Preserves conversation grouping order (so adapter can ingest each conv
    once and iterate QA pairs in-conv before moving on).
    """
    by_cat: dict[int, list[tuple[Conversation, QAPair]]] = {}
    for conv in convs:
        for qa in conv.qa_pairs:
            by_cat.setdefault(qa.category, []).append((conv, qa))
    rng = random.Random(seed)
    cats = sorted(by_cat.keys())
    per_cat = max(1, max_n // max(1, len(cats)))
    selected: list[tuple[Conversation, QAPair]] = []
    for c in cats:
        pool = list(by_cat[c])
        rng.shuffle(pool)
        selected.extend(pool[:per_cat])
    rng.shuffle(selected)
    if len(selected) > max_n:
        selected = selected[:max_n]
    # Group by conversation order to minimize ingest cycles
    selected.sort(key=lambda x: x[0].sample_id)
    return selected


def all_qa(convs: list[Conversation]) -> list[tuple[Conversation, QAPair]]:
    out: list[tuple[Conversation, QAPair]] = []
    for conv in convs:
        for qa in conv.qa_pairs:
            out.append((conv, qa))
    return out


# ---------------------------------------------------------------------------
# Per-conversation driver
# ---------------------------------------------------------------------------

def run_conversation(
    conv: Conversation,
    qa_subset: list[QAPair],
    workdir: Path,
    db_path: str,
    api_port: int,
    nox_mem_bin: str,
    env_base: dict[str, str],
    generator: str,
    openai_key: str,
    top_k: int,
    progress_log,
    out_fh,
    no_vectorize: bool = False,
    no_generator: bool = False,
    sota_push: bool = False,
    session_date_map: dict[str, str] | None = None,
    few_shot: bool = False,
) -> tuple[int, int]:
    """
    Ingest + run ALL qa_subset items for one conversation.
    Writes one JSONL line per QA to out_fh.
    Returns (n_done, n_errors) for the conversation.
    """
    n_done = 0
    n_err = 0
    api_base = f"http://127.0.0.1:{api_port}"

    # Clean DB workspace
    qdir = workdir / f"conv-{conv.sample_id}"
    shutil.rmtree(qdir, ignore_errors=True)
    qdir.mkdir(parents=True, exist_ok=True)
    if Path(db_path).exists():
        Path(db_path).unlink()
    refuse_if_prod(db_path, api_port)

    # Ingest
    progress_log(f"[conv {conv.sample_id}] ingesting {len(conv.sessions)} sessions...")
    ingest_ms, ierr = ingest_conversation(conv, db_path, workdir, nox_mem_bin, env_base)
    if ierr:
        progress_log(f"[conv {conv.sample_id}] INGEST ERROR: {ierr[:300]}")
        # Mark all QA as errored
        for qa in qa_subset:
            res = QAResult(
                sample_id=conv.sample_id, qa_index=qa.qa_index,
                category=qa.category, category_name=qa.category_name,
                question=qa.question, augmented_question=qa.augmented_question,
                answer=qa.answer, evidence=list(qa.evidence),
                ingest_ms=ingest_ms, error=f"ingest: {ierr[:200]}",
            )
            out_fh.write(json.dumps(asdict(res)) + "\n")
            out_fh.flush()
            n_err += 1
            n_done += 1
        return n_done, n_err

    # Vectorize
    vec_ms = 0.0
    if not no_vectorize:
        progress_log(f"[conv {conv.sample_id}] vectorizing...")
        vec_ms, verr = vectorize_conversation(
            db_path, nox_mem_bin, env_base, workdir, conv.sample_id
        )
        if verr:
            progress_log(f"[conv {conv.sample_id}] vectorize WARN: {verr[:200]}")
            # FTS5 still works; continue

    # Start API
    progress_log(f"[conv {conv.sample_id}] starting API server on :{api_port}...")
    proc = None
    try:
        proc = start_api_server(db_path, api_port, env_base)
        progress_log(f"[conv {conv.sample_id}] API up, running {len(qa_subset)} QA pairs")

        for qi, qa in enumerate(qa_subset):
            res = QAResult(
                sample_id=conv.sample_id, qa_index=qa.qa_index,
                category=qa.category, category_name=qa.category_name,
                question=qa.question, augmented_question=qa.augmented_question,
                answer=qa.answer, evidence=list(qa.evidence),
                ingest_ms=ingest_ms, vectorize_ms=vec_ms,
                generator_model=generator,
            )
            try:
                # Retrieve
                hits, sms, serr = search_api(
                    api_base, qa.augmented_question, top_k, DEFAULT_SEARCH_TIMEOUT
                )
                res.retrieval_ms = sms
                if serr:
                    raise RuntimeError(f"search: {serr}")
                top_chunks: list[str] = []
                for h in hits:
                    if not isinstance(h, dict):
                        continue
                    res.retrieved_chunk_ids.append(str(h.get("chunk_id") or h.get("id") or ""))
                    res.retrieved_scores.append(
                        float(h.get("score") or h.get("relevance") or 0.0)
                    )
                    txt = str(h.get("chunk_text") or h.get("text") or h.get("snippet") or "")
                    res.retrieved_texts.append(txt[:1800])
                    top_chunks.append(txt)
                    for did in extract_dia_ids(txt):
                        if did not in res.retrieved_dia_ids:
                            res.retrieved_dia_ids.append(did)

                # Generate (skipped in retrieval-only mode)
                if no_generator:
                    res.generated_answer = ""
                    res.generation_ms = 0.0
                else:
                    if few_shot:
                        prompt = build_prompt_few_shot(
                            qa.augmented_question, top_chunks,
                            conv.speaker_a, conv.speaker_b,
                            session_date_map, qa.category_name,
                        )
                    elif sota_push:
                        prompt = build_prompt_sota(
                            qa.augmented_question, top_chunks,
                            conv.speaker_a, conv.speaker_b,
                            session_date_map, qa.category_name,
                        )
                    else:
                        prompt = build_prompt(
                            qa.augmented_question, top_chunks,
                            conv.speaker_a, conv.speaker_b,
                        )
                    gen_txt, gms, in_t, out_t, gerr = call_openai_generator(
                        prompt, generator, openai_key
                    )
                    res.generation_ms = gms
                    res.input_tokens = in_t
                    res.output_tokens = out_t
                    if gerr:
                        raise RuntimeError(f"gen: {gerr}")
                    res.generated_answer = gen_txt
            except Exception as e:
                res.error = f"{type(e).__name__}: {e}"
                n_err += 1
            finally:
                out_fh.write(json.dumps(asdict(res)) + "\n")
                out_fh.flush()
                n_done += 1
                if n_done % 10 == 0:
                    progress_log(
                        f"[conv {conv.sample_id}] {n_done}/{len(qa_subset)} qa done "
                        f"(errs={n_err})"
                    )
    finally:
        if proc is not None:
            stop_api_server(proc)
        # Clean per-conv md files; keep DB until next conv overwrites
        shutil.rmtree(qdir, ignore_errors=True)

    return n_done, n_err


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--locomo-json", required=True,
                   help="path to data/locomo10.json")
    p.add_argument("--workdir", required=True,
                   help="must be under /root/.openclaw/...")
    p.add_argument("--out", required=True,
                   help="output JSONL path")
    p.add_argument("--api-port", type=int, default=DEFAULT_API_PORT)
    p.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    p.add_argument("--max-questions", type=int, default=100,
                   help="0 = full bench (~1986)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--generator", default="gpt-4.1-mini")
    p.add_argument("--nox-mem-bin", default=DEFAULT_NOX_MEM_BIN)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--no-vectorize", action="store_true")
    p.add_argument("--no-preflight", action="store_true",
                   help="skip OpenAI/Gemini preflight (faster iteration)")
    p.add_argument("--max-conversations", type=int, default=0,
                   help="cap number of conversations (0 = all 10)")
    p.add_argument("--no-generator", action="store_true",
                   help="retrieval-only mode (skip gpt-4.1-mini answer "
                        "generation; useful when OpenAI quota exhausted). "
                        "Outputs retrieved_chunk_ids, retrieved_dia_ids; "
                        "scorer computes evidence-hit-rate.")
    p.add_argument("--sota-push", action="store_true",
                   help="enable LoCoMo F1 SOTA push (variant A): inject "
                        "session_date_map into temporal prompts + 'D Month YYYY' "
                        "date format hint. Smoke 100q: +1.41pp F1, +23pp temporal.")
    p.add_argument("--few-shot", action="store_true",
                   help="enable few-shot prompting: adds 3 in-context examples per "
                        "category (temporal/single_hop/multi_hop/adversarial) BEFORE "
                        "the real question. Builds on SOTA-push variant A (session_date_map "
                        "for temporal). No additional LLM calls — prompt-only. "
                        "Predicted F1 lift +3-8pp on extraction tasks. "
                        "Gate: F1 lift >=+3pp, no category regression >=-5pp.")
    args = p.parse_args(argv)

    # Env
    env_base = dict(os.environ)
    env_file = env_from_file(ENV_FILE)
    for k, v in env_file.items():
        env_base.setdefault(k, v)
    openai_key = env_base.get("OPENAI_API_KEY", "")
    if not openai_key and not args.no_generator:
        return _die("OPENAI_API_KEY not set in env or .env file "
                    "(pass --no-generator for retrieval-only mode)")
    if not env_base.get("GEMINI_API_KEY"):
        return _die("GEMINI_API_KEY not set in env or .env file (needed for nox-mem vectorize)")

    # Force baseline config
    env_base["NOX_RERANKER_ENABLED"] = "0"
    env_base["NOX_API_PORT"] = str(args.api_port)
    env_base["OPENAI_API_KEY"] = openai_key
    env_base.setdefault("NOX_TEMPORAL_PATH", "shadow")
    env_base.setdefault("NOX_SALIENCE_MODE", "shadow")

    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    refuse_if_prod(str(workdir / "any.db"), args.api_port)

    # Preflight (skip if no-generator)
    if not args.no_preflight and not args.no_generator:
        err = preflight(openai_key, args.generator)
        if err:
            return _die(err)
        print(f"[adapter] preflight OK (generator={args.generator})", file=sys.stderr)
    elif args.no_generator:
        print("[adapter] retrieval-only mode (no generator preflight)", file=sys.stderr)

    # Load LoCoMo
    convs = load_conversations(args.locomo_json)
    print(f"[adapter] loaded {len(convs)} conversations, "
          f"{sum(len(c.qa_pairs) for c in convs)} qa pairs", file=sys.stderr)
    if args.max_conversations > 0:
        convs = convs[: args.max_conversations]
        print(f"[adapter] capped to {len(convs)} conversations", file=sys.stderr)

    # Sample
    if args.max_questions <= 0:
        pairs = all_qa(convs)
    else:
        pairs = stratified_qa_sample(convs, args.max_questions, args.seed)
    print(f"[adapter] sample n={len(pairs)} qa pairs", file=sys.stderr)

    # Group by conversation order
    by_conv: dict[str, tuple[Conversation, list[QAPair]]] = {}
    for conv, qa in pairs:
        if conv.sample_id not in by_conv:
            by_conv[conv.sample_id] = (conv, [])
        by_conv[conv.sample_id][1].append(qa)
    n_convs_to_run = len(by_conv)
    print(f"[adapter] grouped into {n_convs_to_run} conversations", file=sys.stderr)

    # Resume: skip already-recorded (conv_id, qa_index) tuples
    done_keys: set[tuple[str, int]] = set()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if args.resume and out_path.exists():
        with out_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    j = json.loads(line)
                    done_keys.add((j["sample_id"], int(j["qa_index"])))
                except Exception:
                    pass
        print(f"[adapter] resume: {len(done_keys)} qa already done", file=sys.stderr)

    n_done = 0
    n_err = 0
    t_start = time.time()
    open_mode = "a" if args.resume and out_path.exists() else "w"

    db_path = str(workdir / "locomo-bench.db")

    # Build session_date_maps for SOTA push and few-shot (Improvement A: temporal anchor)
    session_date_maps: dict[str, dict[str, str]] = {}
    if args.sota_push or args.few_shot:
        with open(args.locomo_json, "r", encoding="utf-8") as fh:
            _raw = json.load(fh)
        for _item in _raw if isinstance(_raw, list) else []:
            if not isinstance(_item, dict):
                continue
            _sid = str(_item.get("sample_id", "?"))
            _conv = _item.get("conversation") or {}
            session_date_maps[_sid] = build_session_date_map(_conv)
        mode_label = "few-shot" if args.few_shot else "SOTA push"
        print(f"[adapter] {mode_label} ON: session_date_maps for "
              f"{len(session_date_maps)} conversations", file=sys.stderr)

    def _log(msg: str) -> None:
        elapsed = time.time() - t_start
        print(f"[adapter t={elapsed:.0f}s] {msg}", file=sys.stderr, flush=True)

    with out_path.open(open_mode, encoding="utf-8") as fh:
        for ci, conv_id in enumerate(sorted(by_conv.keys())):
            conv, qa_list = by_conv[conv_id]
            # Filter resume
            qa_list_run = [q for q in qa_list if (conv.sample_id, q.qa_index) not in done_keys]
            if not qa_list_run:
                _log(f"[conv {conv_id} {ci+1}/{n_convs_to_run}] all done (resume)")
                continue
            _log(f"[conv {conv_id} {ci+1}/{n_convs_to_run}] starting "
                 f"({len(qa_list_run)} qa pending)")
            cd, ce = run_conversation(
                conv, qa_list_run, workdir, db_path, args.api_port,
                args.nox_mem_bin, env_base, args.generator, openai_key, args.top_k,
                _log, fh, no_vectorize=args.no_vectorize,
                no_generator=args.no_generator,
                sota_push=args.sota_push,
                session_date_map=session_date_maps.get(conv.sample_id, {}),
                few_shot=args.few_shot,
            )
            n_done += cd
            n_err += ce
            _log(f"[conv {conv_id}] done={cd} errs={ce} (cum: done={n_done} errs={n_err})")

    elapsed = time.time() - t_start
    print(
        f"[adapter] DONE n_done={n_done} n_err={n_err} elapsed={elapsed:.0f}s "
        f"out={out_path}",
        file=sys.stderr,
    )
    return 0


def _die(msg: str) -> int:
    print(f"[adapter] FATAL: {msg}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
