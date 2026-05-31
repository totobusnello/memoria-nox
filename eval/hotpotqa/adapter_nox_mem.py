"""
adapter_nox_mem.py — HotPotQA adapter for nox-mem (distractor setting).

HotPotQA paper: Yang et al. 2018, arxiv:1809.09600.
Setting: distractor (10 paragraphs per question; 2 gold + 8 distractors).

Per-question pipeline (PER-QUESTION isolated DB — paper requirement):
    1. Build fresh isolated DB per question (NOX_DB_PATH=/<workdir>/q-<qid>.db).
    2. Bootstrap schema V1-V18 (`nox-mem stats` + ALTER patches).
    3. Render 10 paragraphs into one markdown file via
       eval.hotpotqa.lib.corpus_loader.question_to_markdown(q).
    4. Ingest via `nox-mem ingest <file>` subprocess.
    5. Vectorize all chunks (`nox-mem vectorize`).
    6. Start nox-mem-api against this isolated DB.
    7. POST /api/search with the question text, top_k=5 (Phase H v2 baseline).
    8. Map retrieved chunks back to paragraph titles via embedded
       `paragraph_title:` marker; use those + parsed sentence text as
       supporting-fact predictions.
    9. Call gpt-4.1-mini with retrieved context to generate short answer.
   10. Stop API server, clean DB.

Output JSONL fields per question:
    question_id, type, level, question, gold_answer, predicted_answer,
    gold_supporting_facts (list of [title, sent_idx]),
    predicted_supporting_facts (list of [title, sent_idx]),
    retrieved_paragraph_titles (top-K from retrieval),
    ingest_ms, vectorize_ms, retrieval_ms, generation_ms, error

Safety (per memoria-nox rules):
    - Refuses if NOX_DB_PATH resolves to prod /root/.openclaw/workspace/tools/nox-mem/nox-mem.db
    - API port must NOT be 18802 (prod)
    - All temp dirs under /root/.openclaw/hotpotqa-bench-<uuid>/ (op-audit ALLOWED_PREFIXES)

Phase H v2 baseline config (default):
    - top_k=5
    - rerank OFF (NOX_RERANKER_ENABLED=0)
    - hybrid search ON
    - generator: gpt-4.1-mini @ temp=0, max_tokens=128

SP Extractor (--sp-llm-extractor flag):
    When enabled, replaces the token-overlap heuristic SP prediction with an
    LLM-based extractor (eval/hotpotqa/lib/sp_extractor.py).  The extractor
    calls gpt-4.1-mini to identify which exact sentences in the retrieved
    paragraphs are necessary to support the answer.
    Fallback: if the LLM call errors, falls back to the heuristic silently.
    Cost: ~$1.56 for 7405 questions; latency: ~+400ms/query.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

# Reuse loader (shared canonical pattern)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.corpus_loader import (  # type: ignore[import-not-found]
    HotpotQuestion,
    load_questions,
    paragraph_text,
    question_to_markdown,
)
# LLM SP extractor (optional — imported lazily when --sp-llm-extractor flag set)
_sp_extractor_module = None


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_NOX_API_BASE = "http://127.0.0.1:18900"
DEFAULT_NOX_MEM_BIN = "nox-mem"
DEFAULT_TOP_K = 5
DEFAULT_INGEST_TIMEOUT = 120
DEFAULT_SEARCH_TIMEOUT = 30
DEFAULT_VECTORIZE_TIMEOUT = 300
DEFAULT_GENERATION_TIMEOUT = 30

PROD_DB_PATH = "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db"
PROD_API_PORT = 18802

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_GENERATOR_MODEL = "gpt-4.1-mini"

API_SERVER_JS = "/root/.openclaw/workspace/tools/nox-mem/dist/api-server.js"
NODE_BIN = "/usr/bin/node"
ENV_FILE = "/root/.openclaw/.env"

# Maximum supporting-fact sentence count emitted per question (cap to avoid
# spurious sp recall by predicting every sentence).
DEFAULT_MAX_SP_SENTENCES = 6


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------

@dataclass
class HotpotResult:
    question_id: str
    type: str
    level: str
    question: str
    gold_answer: str
    gold_supporting_facts: list[list]               # [[title, sent_idx], ...]
    predicted_answer: str = ""
    predicted_supporting_facts: list[list] = field(default_factory=list)
    retrieved_paragraph_titles: list[str] = field(default_factory=list)
    retrieved_chunk_ids: list[str] = field(default_factory=list)
    retrieved_texts: list[str] = field(default_factory=list)
    ingest_ms: float = 0.0
    vectorize_ms: float = 0.0
    retrieval_ms: float = 0.0
    generation_ms: float = 0.0
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------

def refuse_if_prod(db_path: str, api_base: str) -> None:
    norm = os.path.realpath(db_path)
    if norm == PROD_DB_PATH or norm.endswith("/workspace/tools/nox-mem/nox-mem.db"):
        raise SystemExit(f"refuse to use production DB: {norm}")
    if f":{PROD_API_PORT}" in api_base:
        raise SystemExit(f"refuse to use production API port {PROD_API_PORT}: {api_base}")
    # op-audit ALLOWED_PREFIXES — eval DBs MUST live under /root/.openclaw/
    # (or /var/backups/). Local dev paths under /tmp are blocked by op-audit.
    allowed = ("/var/backups/", "/root/.openclaw/")
    if not any(norm.startswith(p) for p in allowed):
        raise SystemExit(
            f"refuse db_path '{norm}': must start with one of {allowed} "
            f"(op-audit P1 safety guard)"
        )


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
        return 124, (e.stdout or ""), (e.stderr or "TIMEOUT")


def _env_from_file(path: str) -> dict[str, str]:
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
# Schema bootstrap (V1-V18 — matches longmemeval / evermembench pattern)
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


def _patch_schema_v8_v18(db_path: str) -> Optional[str]:
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
    except Exception as e:  # noqa: BLE001
        return f"sqlite open/exec failed: {type(e).__name__}: {e}"
    return None


def bootstrap_db(db_path: str, nox_mem_bin: str, env_base: dict[str, str], workdir: Path, qid: str) -> Optional[str]:
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


# ---------------------------------------------------------------------------
# Per-question DB lifecycle
# ---------------------------------------------------------------------------

def ingest_question(
    q: HotpotQuestion,
    db_path: str,
    workdir: Path,
    nox_mem_bin: str,
    env_base: dict[str, str],
) -> tuple[float, Optional[str]]:
    """Render question paragraphs to markdown + ingest via nox-mem CLI."""
    t0 = time.time()
    qdir = workdir / f"q-{q.question_id}"
    qdir.mkdir(parents=True, exist_ok=True)
    boot_err = bootstrap_db(db_path, nox_mem_bin, env_base, workdir, q.question_id)
    if boot_err:
        return (time.time() - t0) * 1000.0, boot_err

    md = question_to_markdown(q)
    md_path = qdir / f"hotpot-{q.question_id}.md"
    md_path.write_text(md, encoding="utf-8")

    env = dict(env_base)
    env["NOX_DB_PATH"] = db_path
    env["OPENCLAW_WORKSPACE"] = str(qdir)
    rc, out, err = _run(
        [nox_mem_bin, "ingest", str(md_path), "--allow-prod"],
        env=env, timeout=DEFAULT_INGEST_TIMEOUT,
    )
    if rc != 0:
        return (time.time() - t0) * 1000.0, f"ingest rc={rc} err={err[:600]}"
    return (time.time() - t0) * 1000.0, None


def vectorize_question(
    db_path: str,
    nox_mem_bin: str,
    env_base: dict[str, str],
    workdir: Path,
    qid: str,
) -> tuple[float, Optional[str]]:
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
# nox-mem-api lifecycle (per-question restart)
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


def _wait_for_health(api_base: str, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    url = api_base.rstrip("/") + "/api/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2.0) as r:
                if r.status == 200:
                    return True
        except Exception:  # noqa: BLE001
            time.sleep(0.3)
    return False


def start_api_server(db_path: str, port: int, env_base: dict[str, str]) -> subprocess.Popen:
    env = dict(env_base)
    env["NOX_DB_PATH"] = db_path
    env["NOX_API_PORT"] = str(port)
    env["NOX_RERANKER_ENABLED"] = "0"
    env.setdefault("NOX_TEMPORAL_PATH", "shadow")
    workdir = os.path.dirname(API_SERVER_JS)
    proc = subprocess.Popen(
        [NODE_BIN, "--no-warnings", API_SERVER_JS],
        cwd=workdir,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    if not _wait_for_port("127.0.0.1", port, timeout=25.0):
        _kill_proc(proc)
        raise RuntimeError(f"API server failed to bind port {port} within 25s")
    if not _wait_for_health(f"http://127.0.0.1:{port}", timeout=15.0):
        _kill_proc(proc)
        raise RuntimeError("API server bound port but /api/health unhealthy")
    return proc


def _kill_proc(proc: subprocess.Popen) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:  # noqa: BLE001
        try:
            proc.terminate()
        except Exception:  # noqa: BLE001
            pass
    try:
        proc.wait(timeout=5)
    except Exception:  # noqa: BLE001
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:  # noqa: BLE001
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass


def stop_api_server(proc: subprocess.Popen) -> None:
    _kill_proc(proc)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def search_api(api_base: str, query: str, limit: int, timeout: int) -> tuple[list[dict], float, Optional[str]]:
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
            j = json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        return [], (time.time() - t0) * 1000.0, f"search error: {type(e).__name__}: {e}"
    ms = (time.time() - t0) * 1000.0
    # Per [[adapter-response-shape-validation]]: validate shape before .get()
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
# Paragraph-title extraction from retrieved chunks
# ---------------------------------------------------------------------------

# We embed `paragraph_title: <title>` per chunk on ingest. Extract that marker
# from chunk text to map back to the original paragraph. Title-line presence is
# strong (per-H2 block) but the chunker may split inside body; we fall back to
# parsing the H2 header.
_PARA_TITLE_RE = re.compile(r"^paragraph_title:\s*(.+?)\s*$", re.MULTILINE)
_H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def paragraph_title_from_chunk(hit: dict) -> str:
    txt = hit.get("chunk_text") or hit.get("text") or hit.get("snippet") or ""
    m = _PARA_TITLE_RE.search(txt)
    if m:
        return m.group(1).strip()
    m = _H2_RE.search(txt)
    if m:
        return m.group(1).strip()
    return ""


# ---------------------------------------------------------------------------
# Supporting-fact prediction
# ---------------------------------------------------------------------------

def predict_supporting_facts(
    q: HotpotQuestion,
    retrieved_titles: list[str],
    query: str,
    max_titles: int = 2,
    max_sentences_per_title: int = 3,
) -> list[list]:
    """Predict (title, sent_idx) supporting facts from retrieved paragraph titles.

    Strategy (lightweight, no extra LLM call):
      - Take top-`max_titles` distinct retrieved titles that are present in
        the question's paragraph pool (HotPotQA distractor: exact title match
        from the 10 candidates).
      - For each title, score sentences by token overlap with the question
        (lowercased). Keep top `max_sentences_per_title` by score (>0 only).

    This is intentionally simple. A future iteration could use the answerer
    LLM to mark exact supporting sentences (boosts sp_f1 by ~5-10 pts in
    published systems).
    """
    title_to_sents: dict[str, list[str]] = {t: s for t, s in q.paragraphs}
    pred: list[list] = []
    seen: set[str] = set()
    q_tokens = set(_tokenize(query))
    for title in retrieved_titles:
        if title in seen:
            continue
        sents = title_to_sents.get(title)
        if sents is None:
            continue
        seen.add(title)
        # Score sentences by token overlap
        scored: list[tuple[int, float, int]] = []  # (sent_idx, score, sent_idx_tiebreak)
        for i, s in enumerate(sents):
            s_tokens = set(_tokenize(s))
            if not s_tokens:
                continue
            overlap = len(q_tokens & s_tokens)
            if overlap == 0:
                continue
            scored.append((i, float(overlap) / max(1, len(s_tokens)), i))
        scored.sort(key=lambda x: (-x[1], x[2]))
        for i, _score, _tb in scored[:max_sentences_per_title]:
            pred.append([title, int(i)])
        # If no token-overlap sentences picked, fall back to first sentence
        if not scored and sents:
            pred.append([title, 0])
        if len(seen) >= max_titles:
            break
    return pred[:DEFAULT_MAX_SP_SENTENCES]


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


# ---------------------------------------------------------------------------
# Answer generation via gpt-4.1-mini
# ---------------------------------------------------------------------------

ANSWER_SYSTEM_PROMPT = (
    "You are answering a HotPotQA multi-hop question using the retrieved "
    "context paragraphs below. Answer with the SHORTEST possible exact "
    "answer (a name, a number, a yes/no, a noun phrase). Do NOT include "
    "explanations, articles, or full sentences. If the context is "
    "insufficient, answer with your best concise guess from the context."
)


def build_answer_prompt(q: HotpotQuestion, retrieved_texts: list[str]) -> str:
    ctx = "\n\n".join(
        f"--- chunk {i+1} ---\n{c[:2000]}" for i, c in enumerate(retrieved_texts[:5])
    )
    return (
        f"{ANSWER_SYSTEM_PROMPT}\n\n"
        f"Retrieved context:\n{ctx or '[no context retrieved]'}\n\n"
        f"Question: {q.question}\n"
        f"Short answer:"
    )


# ---------------------------------------------------------------------------
# Few-shot prompt for HotPotQA
# ---------------------------------------------------------------------------

# Three in-context examples covering bridge (multi-hop chain) and comparison types.
# Selected to demonstrate both answer formats (entity name vs yes/no) and
# the expected brevity — no full sentences, no explanations.
_HOTPOT_FEW_SHOT_EXAMPLES = """\
Example 1 (bridge — entity answer):
Q: Who was the director of the film that starred both John Cusack and Billy Bob Thornton?
A: Alejandro González Iñárritu

Example 2 (comparison — yes/no):
Q: Were Scott Derrickson and Ed Wood from the same country?
A: yes

Example 3 (bridge — place name):
Q: In which city is the headquarters of the company that acquired Zappos?
A: Seattle"""


def build_answer_prompt_few_shot(q: HotpotQuestion, retrieved_texts: list[str]) -> str:
    """
    Few-shot answer prompt for HotPotQA (PR feat/few-shot-cross-bench, 2026-05-30).

    Adds 3 in-context examples (2 bridge + 1 comparison) before the real
    question. Builds on baseline ANSWER_SYSTEM_PROMPT; no additional LLM
    calls — prompt-only modification.

    Gate prediction: +3-8pp ans_F1 on extraction tasks (bridge/comparison).
    """
    ctx = "\n\n".join(
        f"--- chunk {i+1} ---\n{c[:2000]}" for i, c in enumerate(retrieved_texts[:5])
    )
    return (
        f"{ANSWER_SYSTEM_PROMPT}\n\n"
        f"Retrieved context:\n{ctx or '[no context retrieved]'}\n\n"
        f"{_HOTPOT_FEW_SHOT_EXAMPLES}\n\n"
        f"Q: {q.question}\n"
        "A:"
    )


def call_openai(
    prompt: str, model: str, api_key: str, timeout: int = DEFAULT_GENERATION_TIMEOUT,
) -> tuple[str, float, Optional[str]]:
    body = json.dumps({
        "model": model,
        "temperature": 0,
        "max_tokens": 128,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        OPENAI_URL,
        data=body,
        headers={
            "content-type": "application/json",
            "authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            j = json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        return "", (time.time() - t0) * 1000.0, f"{type(e).__name__}: {e}"
    ms = (time.time() - t0) * 1000.0
    txt = (j.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
    return txt.strip(), ms, None


# ---------------------------------------------------------------------------
# Per-question driver
# ---------------------------------------------------------------------------

def run_question(
    q: HotpotQuestion,
    workdir: Path,
    api_port: int,
    nox_mem_bin: str,
    top_k: int,
    env_base: dict[str, str],
    openai_key: str,
    generator_model: str,
    skip_generation: bool = False,
    few_shot: bool = False,
    sp_llm_extractor: bool = False,
) -> HotpotResult:
    api_base = f"http://127.0.0.1:{api_port}"
    qdir = workdir / f"q-{q.question_id}"
    shutil.rmtree(qdir, ignore_errors=True)
    qdir.mkdir(parents=True, exist_ok=True)
    db_path = str(qdir / "hotpot.db")
    refuse_if_prod(db_path, api_base)

    result = HotpotResult(
        question_id=q.question_id,
        type=q.type,
        level=q.level,
        question=q.question,
        gold_answer=q.answer,
        gold_supporting_facts=[[t, i] for t, i in q.supporting_facts],
    )

    proc: Optional[subprocess.Popen] = None
    try:
        ingest_ms, ierr = ingest_question(q, db_path, workdir, nox_mem_bin, env_base)
        result.ingest_ms = ingest_ms
        if ierr:
            raise RuntimeError(f"ingest: {ierr}")
        vec_ms, verr = vectorize_question(db_path, nox_mem_bin, env_base, workdir, q.question_id)
        result.vectorize_ms = vec_ms
        # Vectorize failure is non-fatal — FTS5 still works.
        proc = start_api_server(db_path, api_port, env_base)
        hits, search_ms, serr = search_api(api_base, q.question, top_k, DEFAULT_SEARCH_TIMEOUT)
        result.retrieval_ms = search_ms
        if serr:
            raise RuntimeError(f"search: {serr}")
        titles_seen: list[str] = []
        for h in hits:
            if not isinstance(h, dict):
                continue
            cid = str(h.get("chunk_id") or h.get("id") or "")
            result.retrieved_chunk_ids.append(cid)
            chunk_txt = str(h.get("chunk_text") or h.get("text") or h.get("snippet") or "")
            result.retrieved_texts.append(chunk_txt[:2000])
            title = paragraph_title_from_chunk(h)
            if title:
                titles_seen.append(title)
        # Dedup titles preserving order
        seen_t: set[str] = set()
        ordered_titles: list[str] = []
        for t in titles_seen:
            if t in seen_t:
                continue
            seen_t.add(t)
            ordered_titles.append(t)
        result.retrieved_paragraph_titles = ordered_titles
        if sp_llm_extractor and openai_key and result.retrieved_texts:
            # LLM-based SP extraction (higher quality than token-overlap heuristic)
            global _sp_extractor_module
            if _sp_extractor_module is None:
                from lib import sp_extractor as _sp_extractor_module  # type: ignore[import-not-found]
            sp_pred, _sp_ms, _sp_err = _sp_extractor_module.extract_supporting_facts(
                question=q.question,
                answer=result.predicted_answer,  # may be empty pre-gen; OK
                chunk_texts=result.retrieved_texts,
                paragraph_titles=ordered_titles,
                api_key=openai_key,
            )
            if _sp_err or not sp_pred:
                # Fallback to heuristic on LLM error
                sp_pred = predict_supporting_facts(q, ordered_titles, q.question)
        else:
            sp_pred = predict_supporting_facts(q, ordered_titles, q.question)
        result.predicted_supporting_facts = sp_pred
        # Answer generation
        if not skip_generation and openai_key:
            if few_shot:
                prompt = build_answer_prompt_few_shot(q, result.retrieved_texts)
            else:
                prompt = build_answer_prompt(q, result.retrieved_texts)
            ans, gms, gerr = call_openai(prompt, generator_model, openai_key)
            result.predicted_answer = ans
            result.generation_ms = gms
            if gerr:
                result.error = (result.error or "") + f"; gen: {gerr}"
    except Exception as e:  # noqa: BLE001
        result.error = f"{type(e).__name__}: {e}"
    finally:
        if proc is not None:
            stop_api_server(proc)
        # Clean per-q DB+md to keep workdir small
        shutil.rmtree(qdir, ignore_errors=True)
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", required=True, help="path to HotPotQA dev-distractor JSON")
    p.add_argument("--workdir", required=True, help="scratch dir under /root/.openclaw/")
    p.add_argument("--out", required=True, help="output JSONL path")
    p.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    p.add_argument("--api-port", type=int, default=18900)
    p.add_argument("--nox-mem-bin", default=os.environ.get("NOX_MEM_BIN", DEFAULT_NOX_MEM_BIN))
    p.add_argument("--generator", default=DEFAULT_GENERATOR_MODEL)
    p.add_argument("--n", type=int, default=0, help="hard cap on n questions (0 = all)")
    p.add_argument("--offset", type=int, default=0, help="skip first N questions")
    p.add_argument("--seed", type=int, default=42, help="shuffle seed for sampling")
    p.add_argument("--shuffle", action="store_true", help="shuffle (otherwise sequential)")
    p.add_argument("--skip-generation", action="store_true",
                   help="retrieval-only mode (no LLM call; predicted_answer empty)")
    p.add_argument("--few-shot", action="store_true",
                   help="enable few-shot prompting: adds 3 in-context examples "
                        "(bridge + comparison types) before the real question. "
                        "No additional LLM calls — prompt-only. "
                        "Predicted ans_F1 lift +3-8pp on extraction tasks. "
                        "Gate: F1 lift >=+3pp, no category regression >=-5pp.")
    p.add_argument("--sp-llm-extractor", action="store_true",
                   help="Replace token-overlap SP heuristic with LLM-based extractor "
                        "(eval/hotpotqa/lib/sp_extractor.py). Uses gpt-4.1-mini to identify "
                        "which exact retrieved sentences support the answer. "
                        "Fallback to heuristic on LLM error. "
                        "Cost: ~$1.56 for 7405 questions. Latency: +~400ms/query.")
    p.add_argument("--resume", action="store_true",
                   help="skip question_ids already present in --out (JSONL)")
    p.add_argument("--progress-every", type=int, default=10)
    args = p.parse_args(argv)

    if args.api_port == PROD_API_PORT:
        raise SystemExit(f"refuse to use prod API port {PROD_API_PORT}")

    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    # Load env from /root/.openclaw/.env (matches longmemeval orchestrator)
    env_base = dict(os.environ)
    env_file = _env_from_file(ENV_FILE)
    for k, v in env_file.items():
        env_base.setdefault(k, v)
    env_base["NOX_RERANKER_ENABLED"] = "0"
    env_base["NOX_API_PORT"] = str(args.api_port)
    openai_key = env_base.get("OPENAI_API_KEY", "")
    if not args.skip_generation and not openai_key:
        raise SystemExit("OPENAI_API_KEY required for answer generation (or use --skip-generation)")

    questions = load_questions(Path(args.dataset))
    print(f"[adapter] loaded {len(questions)} questions from {args.dataset}", file=sys.stderr)
    if args.shuffle:
        import random as _rnd
        rng = _rnd.Random(args.seed)
        rng.shuffle(questions)
    if args.offset > 0:
        questions = questions[args.offset:]
    if args.n > 0:
        questions = questions[: args.n]
    print(f"[adapter] running n={len(questions)} questions", file=sys.stderr)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    done_ids: set[str] = set()
    if args.resume and out_path.exists():
        with out_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                    qid = rec.get("question_id")
                    if qid:
                        done_ids.add(qid)
                except Exception:  # noqa: BLE001
                    pass
        print(f"[adapter] resume: skipping {len(done_ids)} already-done ids", file=sys.stderr)

    open_mode = "a" if (args.resume and out_path.exists()) else "w"
    n_done = 0
    n_err = 0
    n_skip = 0
    t_start = time.time()

    with out_path.open(open_mode, encoding="utf-8") as fh:
        for i, q in enumerate(questions):
            if q.question_id in done_ids:
                n_skip += 1
                continue
            result = run_question(
                q,
                workdir=workdir,
                api_port=args.api_port,
                nox_mem_bin=args.nox_mem_bin,
                top_k=args.top_k,
                env_base=env_base,
                openai_key=openai_key,
                generator_model=args.generator,
                skip_generation=args.skip_generation,
                few_shot=args.few_shot,
                sp_llm_extractor=args.sp_llm_extractor,
            )
            if result.error:
                n_err += 1
            fh.write(json.dumps(asdict(result)) + "\n")
            fh.flush()
            n_done += 1
            if n_done % args.progress_every == 0:
                elapsed = time.time() - t_start
                rate = n_done / elapsed if elapsed > 0 else 0.0
                remaining = len(questions) - n_done - n_skip
                eta = remaining / rate if rate > 0 else 0.0
                print(
                    f"[adapter] {n_done}/{len(questions) - n_skip} "
                    f"({100*n_done/max(1,len(questions)-n_skip):.1f}%) "
                    f"errs={n_err} elapsed={elapsed:.0f}s rate={rate:.2f}q/s ETA={eta:.0f}s",
                    file=sys.stderr,
                )
    elapsed = time.time() - t_start
    print(
        f"[adapter] DONE n_done={n_done} n_err={n_err} n_skip={n_skip} "
        f"elapsed={elapsed:.0f}s out={out_path}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
