"""
adapter_nox_mem.py — MuSiQue bench adapter for nox-mem.

MuSiQue (Trivedi et al. TACL 2022, arxiv:2108.00573) is the extreme
multi-hop QA benchmark: 2-4 sequential reasoning hops, hard distractor
paragraphs (~20 per question, selected to confuse single-shot RAG).

Per-question ingestion pattern (mirrors LongMemEval crossbench PR #378, NOT
LoCoMo per-conversation):
  - Each MuSiQue question has its OWN 20-paragraph corpus, disjoint from
    other questions.
  - We bootstrap a FRESH isolated DB per question, ingest its 20 paragraphs,
    vectorize, run hybrid search, generate answer, then drop DB.

Pipeline per question:
  1. Build fresh isolated DB at `${WORKDIR}/q-{qid}.db`.
  2. Render each paragraph as markdown via lib/corpus_loader.write_question_md_files.
  3. `nox-mem ingest` each paragraph .md.
  4. `nox-mem vectorize` once.
  5. Start nox-mem-api on isolated port pointed at this DB.
  6. POST /api/search with the question (top-k=20).
  7. Build context from top-K chunks.
  8. Call gpt-4.1-mini generator with context + question.
  9. Stop API server, delete DB.

Safety (op-audit ALLOWED_PREFIXES):
  - NOX_DB_PATH must NOT resolve to prod /root/.openclaw/workspace/tools/nox-mem/nox-mem.db
  - API port must NOT be 18802 (prod)
  - Workdir must start with /root/.openclaw/ or /var/backups/

CLI:
  python3 adapter_nox_mem.py \\
      --musique-jsonl /tmp/musique-repo/data/musique_ans_v1.0_dev.jsonl \\
      --workdir /root/.openclaw/musique-bench-<uuid>/work \\
      --out results-smoke-100.jsonl \\
      --api-port 18890 \\
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
import re as _re
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

# Allow local lib/ import
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

from corpus_loader import (  # type: ignore[import-not-found]
    Question,
    load_questions,
    write_question_md_files,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_API_PORT = 18890
DEFAULT_TOP_K = 20
DEFAULT_INGEST_TIMEOUT = 60
DEFAULT_VECTORIZE_TIMEOUT = 180
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
class QResult:
    qid: str
    hop_prefix: str
    hop_count: int
    question: str
    gold_answers: list[str]          # answer + answer_aliases
    gold_support_idxs: list[int]     # paragraph idxs marked is_supporting
    n_paragraphs: int                # always 20 for MuSiQue
    retrieved_chunk_ids: list[str] = field(default_factory=list)
    retrieved_scores: list[float] = field(default_factory=list)
    retrieved_texts: list[str] = field(default_factory=list)
    retrieved_para_idxs: list[int] = field(default_factory=list)
    # predicted supports = unique top-K paragraph idxs after dedup
    predicted_support_idxs: list[int] = field(default_factory=list)
    retrieval_ms: float = 0.0
    generation_ms: float = 0.0
    ingest_ms: float = 0.0
    vectorize_ms: float = 0.0
    generated_answer: str = ""
    generator_model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    embed_tokens: int = 0
    error: str | None = None


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------

def refuse_if_prod(db_path: str, api_port: int) -> None:
    norm = os.path.realpath(db_path)
    if norm == PROD_DB_PATH or norm.endswith("/workspace/tools/nox-mem/nox-mem.db"):
        raise SystemExit(f"refuse to use production DB: {norm}")
    if api_port == 18802:
        raise SystemExit("refuse to use production API port 18802")
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
        proc = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as e:
        return 124, e.stdout or "", e.stderr or "TIMEOUT"


# ---------------------------------------------------------------------------
# Schema patcher (same pattern as LongMemEval / LoCoMo)
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
    db_path: str,
    nox_mem_bin: str,
    env_base: dict[str, str],
    workdir: Path,
    qid: str,
) -> str | None:
    env = dict(env_base)
    env["NOX_DB_PATH"] = db_path
    env["OPENCLAW_WORKSPACE"] = str(workdir / f"q-{qid}")
    rc, _out, err = _run([nox_mem_bin, "stats"], env=env, timeout=30)
    if rc != 0:
        return f"bootstrap rc={rc} err={err[:300]}"
    return patch_schema_v8_v18(db_path)


# ---------------------------------------------------------------------------
# Ingest + Vectorize (per question — fast, ~20 paragraphs)
# ---------------------------------------------------------------------------

def ingest_question(
    question: Question,
    db_path: str,
    workdir: Path,
    nox_mem_bin: str,
    env_base: dict[str, str],
) -> tuple[float, str | None]:
    t0 = time.time()
    qdir = workdir / f"q-{question.qid}"
    qdir.mkdir(parents=True, exist_ok=True)
    err = bootstrap_db(db_path, nox_mem_bin, env_base, workdir, question.qid)
    if err:
        return (time.time() - t0) * 1000.0, err
    md_paths = write_question_md_files(question, qdir)
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


def vectorize_question(
    db_path: str,
    nox_mem_bin: str,
    env_base: dict[str, str],
    workdir: Path,
    qid: str,
) -> tuple[float, str | None]:
    t0 = time.time()
    env = dict(env_base)
    env["NOX_DB_PATH"] = db_path
    env["OPENCLAW_WORKSPACE"] = str(workdir / f"q-{qid}")
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


def start_api_server(
    db_path: str, port: int, env_base: dict[str, str]
) -> subprocess.Popen:
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

# Regex for embedded para_idx markers (rendered by corpus_loader)
_PARA_IDX_RE = _re.compile(r"para_idx:\s*(\d+)\s*\|\s*qid:")
_PARA_IDX_FALLBACK_RE = _re.compile(r"paragraph_idx:\s*(\d+)")


def extract_para_idx(text: str) -> int | None:
    if not text:
        return None
    m = _PARA_IDX_RE.search(text)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    m = _PARA_IDX_FALLBACK_RE.search(text)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None


def search_api(
    api_base: str, query: str, limit: int, timeout: int
) -> tuple[list[dict], float, str | None]:
    url = api_base.rstrip("/") + "/api/search"
    body = json.dumps(
        {"query": query, "limit": limit, "hybrid": True}
    ).encode("utf-8")
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
    max_tokens: int = 64,
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


def build_prompt(question: str, top_chunks: list[str]) -> str:
    """
    MuSiQue-specific answer prompt.

    - Force short factoid answer (MuSiQue answers are typically 1-5 tokens).
    - Force "ONLY from context", no parametric guessing.
    - No CoT reasoning emitted (we ask for the answer span only).
    """
    ctx = "\n\n".join(
        f"--- chunk {i+1} ---\n{c[:1800]}" for i, c in enumerate(top_chunks[:15])
    )
    return (
        "You are answering a multi-hop question about Wikipedia paragraphs.\n"
        "Use ONLY the retrieved paragraphs below as evidence; do not invent "
        "facts; do not use external knowledge.\n\n"
        f"Retrieved paragraphs:\n{ctx or '[no context retrieved]'}\n\n"
        f"Question: {question}\n\n"
        "Answer with the SHORT factoid span ONLY (1-5 words, no full sentences, "
        "no explanations, no quotes, no punctuation other than what is in the "
        "name itself). If the answer is a date, output the date as it appears "
        "in the paragraph. If the paragraphs do not contain the answer, output: "
        "Not in context.\n\n"
        "Answer:"
    )


# ---------------------------------------------------------------------------
# Preflight (billing path)
# ---------------------------------------------------------------------------

def preflight(openai_key: str, model: str) -> str | None:
    """
    Exercise OpenAI billing path with a 5-token completion.
    Catches 'key valid but billing disabled' which /v1/models would NOT catch
    (lesson cravada Phase H v1 fail → v2 fix).
    """
    txt, _ms, in_t, out_t, err = call_openai_generator(
        "Say 'ok' (2 letters)", model, openai_key, timeout=15, max_tokens=5
    )
    if err:
        return f"openai preflight failed: {err}"
    if not txt:
        return f"openai preflight returned empty text (in={in_t} out={out_t})"
    return None


# ---------------------------------------------------------------------------
# Stratified sampling (by hop_prefix)
# ---------------------------------------------------------------------------

def stratified_sample(
    questions: list[Question], max_n: int, seed: int = 42
) -> list[Question]:
    """
    Stratify across the 6 hop variants (2hop / 3hop1 / 3hop2 / 4hop1 / 4hop2 / 4hop3).
    Equal-per-bucket sampling; capped at max_n.
    """
    by_hop: dict[str, list[Question]] = {}
    for q in questions:
        by_hop.setdefault(q.hop_prefix, []).append(q)
    rng = random.Random(seed)
    hops = sorted(by_hop.keys())
    per_hop = max(1, max_n // max(1, len(hops)))
    selected: list[Question] = []
    for h in hops:
        pool = list(by_hop[h])
        rng.shuffle(pool)
        selected.extend(pool[:per_hop])
    rng.shuffle(selected)
    if len(selected) > max_n:
        selected = selected[:max_n]
    return selected


# ---------------------------------------------------------------------------
# Per-question driver
# ---------------------------------------------------------------------------

def run_question(
    question: Question,
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
) -> tuple[int, int]:
    """
    Ingest + run ONE MuSiQue question end-to-end.
    Writes one JSONL line.
    Returns (n_done, n_errors) — always (1,0) on success, (1,1) on error.
    """
    qdir = workdir / f"q-{question.qid}"
    shutil.rmtree(qdir, ignore_errors=True)
    qdir.mkdir(parents=True, exist_ok=True)
    if Path(db_path).exists():
        Path(db_path).unlink()
    refuse_if_prod(db_path, api_port)

    res = QResult(
        qid=question.qid,
        hop_prefix=question.hop_prefix,
        hop_count=question.hop_count,
        question=question.question,
        gold_answers=list(question.all_answers),
        gold_support_idxs=list(question.supporting_idxs),
        n_paragraphs=len(question.paragraphs),
        generator_model=generator,
    )

    api_base = f"http://127.0.0.1:{api_port}"

    # Ingest
    ingest_ms, ierr = ingest_question(
        question, db_path, workdir, nox_mem_bin, env_base
    )
    res.ingest_ms = ingest_ms
    if ierr:
        res.error = f"ingest: {ierr[:300]}"
        out_fh.write(json.dumps(asdict(res)) + "\n")
        out_fh.flush()
        shutil.rmtree(qdir, ignore_errors=True)
        return 1, 1

    # Vectorize
    if not no_vectorize:
        vec_ms, verr = vectorize_question(
            db_path, nox_mem_bin, env_base, workdir, question.qid
        )
        res.vectorize_ms = vec_ms
        if verr:
            # FTS5 still works; continue, but log
            progress_log(
                f"[q {question.qid}] vectorize WARN: {verr[:200]}"
            )

    # Start API
    proc = None
    try:
        proc = start_api_server(db_path, api_port, env_base)
        try:
            hits, sms, serr = search_api(
                api_base, question.question, top_k, DEFAULT_SEARCH_TIMEOUT
            )
            res.retrieval_ms = sms
            if serr:
                raise RuntimeError(f"search: {serr}")
            top_chunks: list[str] = []
            seen_para_idxs: list[int] = []
            for h in hits:
                if not isinstance(h, dict):
                    continue
                res.retrieved_chunk_ids.append(
                    str(h.get("chunk_id") or h.get("id") or "")
                )
                res.retrieved_scores.append(
                    float(h.get("score") or h.get("relevance") or 0.0)
                )
                txt = str(
                    h.get("chunk_text")
                    or h.get("text")
                    or h.get("snippet")
                    or ""
                )
                res.retrieved_texts.append(txt[:1800])
                top_chunks.append(txt)
                pidx = extract_para_idx(txt)
                if pidx is not None:
                    res.retrieved_para_idxs.append(pidx)
                    if pidx not in seen_para_idxs:
                        seen_para_idxs.append(pidx)
            # predicted_support_idxs = unique top-K paragraph idxs.
            # For MuSiQue's support_f1 metric we follow the canonical
            # approach (cap to number-of-gold-supports or top-5, whichever
            # is smaller). We use min(len(gold), 5) — matches HotpotQA-style
            # support eval intuition.
            cap = max(2, min(5, len(res.gold_support_idxs) or 2))
            res.predicted_support_idxs = seen_para_idxs[:cap]

            # Generate
            if no_generator:
                res.generated_answer = ""
                res.generation_ms = 0.0
            else:
                prompt = build_prompt(question.question, top_chunks)
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
            out_fh.write(json.dumps(asdict(res)) + "\n")
            out_fh.flush()
            return 1, 1
    finally:
        if proc is not None:
            stop_api_server(proc)
        shutil.rmtree(qdir, ignore_errors=True)

    out_fh.write(json.dumps(asdict(res)) + "\n")
    out_fh.flush()
    return 1, 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--musique-jsonl", required=True,
        help="path to musique_ans_v1.0_dev.jsonl",
    )
    p.add_argument("--workdir", required=True,
                   help="must be under /root/.openclaw/...")
    p.add_argument("--out", required=True,
                   help="output JSONL path")
    p.add_argument("--api-port", type=int, default=DEFAULT_API_PORT)
    p.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    p.add_argument(
        "--max-questions", type=int, default=100,
        help="0 = full dev (~2417 for musique_ans)",
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--generator", default="gpt-4.1-mini")
    p.add_argument("--nox-mem-bin", default=DEFAULT_NOX_MEM_BIN)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--no-vectorize", action="store_true")
    p.add_argument(
        "--no-preflight", action="store_true",
        help="skip OpenAI preflight (faster iteration)",
    )
    p.add_argument(
        "--no-generator", action="store_true",
        help=(
            "retrieval-only mode (skip gpt-4.1-mini answer generation; useful "
            "when OpenAI quota exhausted). Outputs retrieved_para_idxs; "
            "scorer computes support_hit_at_k."
        ),
    )
    p.add_argument(
        "--stratified", action="store_true", default=True,
        help="stratified sample across hop variants (default: True)",
    )
    p.add_argument(
        "--first-n", action="store_true",
        help="take first-N in dataset order (overrides --stratified)",
    )
    args = p.parse_args(argv)

    # Env
    env_base = dict(os.environ)
    env_file = env_from_file(ENV_FILE)
    for k, v in env_file.items():
        env_base.setdefault(k, v)
    openai_key = env_base.get("OPENAI_API_KEY", "")
    if not openai_key and not args.no_generator:
        return _die(
            "OPENAI_API_KEY not set in env or .env file "
            "(pass --no-generator for retrieval-only mode)"
        )
    if not env_base.get("GEMINI_API_KEY"):
        return _die(
            "GEMINI_API_KEY not set in env or .env file (needed for nox-mem vectorize)"
        )

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
        print(
            f"[adapter] preflight OK (generator={args.generator})",
            file=sys.stderr,
        )
    elif args.no_generator:
        print(
            "[adapter] retrieval-only mode (no generator preflight)",
            file=sys.stderr,
        )

    # Load MuSiQue
    questions = load_questions(args.musique_jsonl)
    print(
        f"[adapter] loaded {len(questions)} questions from "
        f"{args.musique_jsonl}",
        file=sys.stderr,
    )

    # Sample
    if args.max_questions <= 0:
        sample = questions
    elif args.first_n:
        sample = questions[: args.max_questions]
    else:
        sample = stratified_sample(questions, args.max_questions, args.seed)
    print(f"[adapter] sample n={len(sample)} questions", file=sys.stderr)

    # Resume
    done_qids: set[str] = set()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if args.resume and out_path.exists():
        with out_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    j = json.loads(line)
                    done_qids.add(str(j.get("qid", "")))
                except Exception:
                    pass
        print(
            f"[adapter] resume: {len(done_qids)} questions already done",
            file=sys.stderr,
        )

    n_done = 0
    n_err = 0
    t_start = time.time()
    open_mode = "a" if args.resume and out_path.exists() else "w"

    db_path = str(workdir / "musique-bench.db")

    def _log(msg: str) -> None:
        elapsed = time.time() - t_start
        print(
            f"[adapter t={elapsed:.0f}s] {msg}",
            file=sys.stderr,
            flush=True,
        )

    with out_path.open(open_mode, encoding="utf-8") as fh:
        for qi, q in enumerate(sample):
            if q.qid in done_qids:
                continue
            _log(
                f"[q {qi+1}/{len(sample)} {q.qid} hop={q.hop_prefix}] start"
            )
            d, e = run_question(
                q, workdir, db_path, args.api_port, args.nox_mem_bin,
                env_base, args.generator, openai_key, args.top_k,
                _log, fh,
                no_vectorize=args.no_vectorize,
                no_generator=args.no_generator,
            )
            n_done += d
            n_err += e
            if n_done % 10 == 0:
                _log(
                    f"[progress] done={n_done} errs={n_err} "
                    f"(elapsed={time.time()-t_start:.0f}s)"
                )

    elapsed = time.time() - t_start
    print(
        f"[adapter] DONE n_done={n_done} n_err={n_err} "
        f"elapsed={elapsed:.0f}s out={out_path}",
        file=sys.stderr,
    )
    return 0


def _die(msg: str) -> int:
    print(f"[adapter] FATAL: {msg}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
