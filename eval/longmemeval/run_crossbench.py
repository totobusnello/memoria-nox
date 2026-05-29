"""
run_crossbench.py — per-question API restart orchestrator for LongMemEval
cross-bench validation.

For each stratified sample question:
    1. Build fresh isolated DB.
    2. Ingest haystack sessions into that DB via `nox-mem ingest` subprocess.
    3. Run `nox-mem vectorize` to populate the vector index.
    4. Start a fresh nox-mem API server on isolated port pointed at THAT DB.
    5. Wait for /api/health to respond.
    6. POST /api/search with the question.
    7. Record retrieval result (chunk_ids → session_ids), latencies, gold.
    8. Stop API server, clean DB.
    9. Optional task-accuracy: call gpt-4.1-mini with top-K context.

This is a SLOW path (~15-25s/question incl. API spinup), but it preserves
the LongMemEval-paper isolation requirement (no haystack cross-contamination
between questions). Total wall-clock for n=300 ≈ 75-125 minutes.

Phase D config (matches Phase H v2 cross-backbone WIN configuration):
    - top_k=20
    - rerank OFF (NOX_RERANKER_ENABLED=0)
    - hybrid search ON (default; FTS5 + Gemini dense + RRF)
    - generator: gpt-4.1-mini (cross-backbone parity)
    - judge: gemini-2.5-flash (cheap, dry-run-grade; explicit caveat in report)

Safety:
    - Refuses if NOX_DB_PATH resolves to /root/.openclaw/workspace/tools/nox-mem/nox-mem.db
    - API port must be 18835 (not 18802 prod)
    - All temp dirs under /tmp/longmemeval-<uuid>

Usage:
    python3 run_crossbench.py \\
        --split-path /tmp/longmemeval-X/data/longmemeval_oracle.json \\
        --n 300 --seed 42 \\
        --top-k 20 \\
        --api-port 18835 \\
        --workdir /tmp/longmemeval-X/work \\
        --out /tmp/longmemeval-X/results.jsonl \\
        [--task-accuracy --generator gpt-4.1-mini]
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
from dataclasses import asdict, dataclass
from pathlib import Path

# Reuse adapter helpers
sys.path.insert(0, str(Path(__file__).resolve().parent))
from adapter_lme import (  # type: ignore[import-not-found]
    DEFAULT_NOX_MEM_BIN,
    DEFAULT_SEARCH_TIMEOUT,
    DEFAULT_TOP_K,
    PROD_DB_PATH,
    QARecord,
    RetrievalResult,
    ingest_question,
    load_split,
    refuse_if_prod,
    search_api,
    stratified_sample,
    vectorize_question,
)


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------

API_SERVER_JS = "/root/.openclaw/workspace/tools/nox-mem/dist/api-server.js"
NODE_BIN = "/usr/bin/node"
ENV_FILE = "/root/.openclaw/.env"


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


def _wait_for_port(host: str, port: int, timeout: float = 20.0) -> bool:
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
        except Exception:
            time.sleep(0.3)
    return False


def start_api_server(db_path: str, port: int, env_base: dict[str, str]) -> subprocess.Popen:
    env = dict(env_base)
    env["NOX_DB_PATH"] = db_path
    env["NOX_API_PORT"] = str(port)
    env["NOX_RERANKER_ENABLED"] = "0"  # Phase D config
    # Disable temporal/spike features that might index-prime: keep Phase D-like
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
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        raise RuntimeError(f"API server failed to bind port {port} within 25s")
    if not _wait_for_health(f"http://127.0.0.1:{port}", timeout=15.0):
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        raise RuntimeError(f"API server bound port but /api/health unhealthy")
    return proc


def stop_api_server(proc: subprocess.Popen) -> None:
    try:
        # Stop the whole process group (in case nox-mem spawns workers).
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


# ---------------------------------------------------------------------------
# Optional gpt-4.1-mini generator (cross-backbone task-accuracy)
# ---------------------------------------------------------------------------

OPENAI_URL = "https://api.openai.com/v1/chat/completions"


def call_openai_generator(prompt: str, model: str, openai_key: str, timeout: int = 30) -> tuple[str, float, str | None]:
    body = json.dumps({
        "model": model,
        "temperature": 0,
        "max_tokens": 256,
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
    except Exception as e:
        return "", (time.time() - t0) * 1000.0, f"{type(e).__name__}: {e}"
    ms = (time.time() - t0) * 1000.0
    txt = (j.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
    return txt.strip(), ms, None


def build_prompt(question: str, question_date: str, top_chunks: list[str], is_abstention: bool) -> str:
    ctx = "\n\n".join(
        f"--- chunk {i+1} ---\n{c[:2000]}" for i, c in enumerate(top_chunks[:10])
    )
    abstain_hint = (
        "\nIMPORTANT: if the retrieved context does not contain a confident answer, "
        "reply with exactly: I don't know."
        if is_abstention else ""
    )
    return (
        "You are answering a question based ONLY on the retrieved long-term memory context below.\n"
        f"Today's date (the user is asking on this date): {question_date}\n"
        f"{abstain_hint}\n\n"
        "Retrieved context:\n"
        f"{ctx or '[no context retrieved]'}\n\n"
        f"Question: {question}\n"
        "Answer concisely:"
    )


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--split-path", required=True)
    p.add_argument("--n", type=int, default=300)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    p.add_argument("--api-port", type=int, default=18835)
    p.add_argument("--workdir", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--nox-mem-bin", default=os.environ.get("NOX_MEM_BIN", DEFAULT_NOX_MEM_BIN))
    p.add_argument("--task-accuracy", action="store_true",
                   help="also call generator + judge for end-to-end task accuracy")
    p.add_argument("--generator", default="gpt-4.1-mini")
    p.add_argument("--progress-every", type=int, default=5)
    p.add_argument("--max-questions", type=int, default=0, help="hard cap (0 = no cap)")
    p.add_argument("--resume", action="store_true",
                   help="skip question_ids already present in --out (JSONL)")
    args = p.parse_args(argv)

    if args.api_port == 18802:
        raise SystemExit("refuse to use prod port 18802")

    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    # Env: load /root/.openclaw/.env BUT override the dangerous bits.
    env_base = dict(os.environ)
    env_file = _env_from_file(ENV_FILE)
    for k, v in env_file.items():
        env_base.setdefault(k, v)
    # CRITICAL: re-export the overrides AFTER source
    env_base["NOX_RERANKER_ENABLED"] = "0"
    env_base["NOX_API_PORT"] = str(args.api_port)
    openai_key = env_base.get("OPENAI_API_KEY", "")
    if args.task_accuracy and not openai_key:
        raise SystemExit("--task-accuracy needs OPENAI_API_KEY in env or .env file")

    # Load + sample
    records = load_split(Path(args.split_path))
    print(f"[run] loaded {len(records)} records from {args.split_path}", file=sys.stderr)
    sample = stratified_sample(records, args.n, args.seed)
    if args.max_questions > 0:
        sample = sample[: args.max_questions]
    print(f"[run] sample n={len(sample)}", file=sys.stderr)

    # Resume: skip qids already in out
    done_ids: set[str] = set()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if args.resume and out_path.exists():
        with out_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                    qid = rec.get("question_id")
                    if qid:
                        done_ids.add(qid)
                except Exception:
                    pass
        print(f"[run] resume: skipping {len(done_ids)} already-done ids", file=sys.stderr)

    by_cell: dict[str, int] = {}
    for r in sample:
        cell = f"{r.base_category}{'_abs' if r.is_abstention else ''}"
        by_cell[cell] = by_cell.get(cell, 0) + 1
    print(f"[run] by cell: {by_cell}", file=sys.stderr)

    n_done = 0
    n_err = 0
    n_skip = 0
    t_start = time.time()
    api_base = f"http://127.0.0.1:{args.api_port}"

    open_mode = "a" if args.resume and out_path.exists() else "w"
    with out_path.open(open_mode, encoding="utf-8") as fh:
        for i, rec in enumerate(sample):
            if rec.question_id in done_ids:
                n_skip += 1
                continue

            # Per-question fresh DB
            qdir = workdir / f"q-{rec.question_id}"
            shutil.rmtree(qdir, ignore_errors=True)
            qdir.mkdir(parents=True, exist_ok=True)
            db_path = str(qdir / "lme.db")
            refuse_if_prod(db_path, api_base)

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
            proc: subprocess.Popen | None = None
            try:
                # Ingest haystack
                ingest_ms, ierr = ingest_question(rec, db_path, workdir, args.nox_mem_bin, env_base)
                result.ingest_ms = ingest_ms
                if ierr:
                    raise RuntimeError(f"ingest: {ierr}")
                # Vectorize
                vec_ms, verr = vectorize_question(db_path, args.nox_mem_bin, env_base, workdir, rec.question_id)
                result.vectorize_ms = vec_ms
                if verr:
                    # don't abort — FTS5 search still works
                    print(f"[run] q={rec.question_id} vectorize warn: {verr}", file=sys.stderr)

                # Start API server pointed at this DB
                proc = start_api_server(db_path, args.api_port, env_base)

                # Search
                hits, search_ms, serr = search_api(api_base, rec.question, args.top_k, DEFAULT_SEARCH_TIMEOUT)
                result.retrieval_ms = search_ms
                if serr:
                    raise RuntimeError(f"search: {serr}")
                # Parse hits (api-server.js shape: id, score, chunk_text, ...)
                for h in hits:
                    if not isinstance(h, dict):
                        continue
                    result.retrieved_chunk_ids.append(str(h.get("chunk_id") or h.get("id") or ""))
                    result.retrieved_scores.append(float(h.get("score") or h.get("relevance") or 0.0))
                    # Session id parse from chunk text (markdown "session_id: <id>")
                    from adapter_lme import session_id_from_chunk  # type: ignore[import-not-found]
                    result.retrieved_session_ids.append(session_id_from_chunk(h))
                    result.retrieved_texts.append(
                        str(h.get("chunk_text") or h.get("text") or h.get("snippet") or "")[:1500]
                    )

                # Optional generator
                if args.task_accuracy:
                    prompt = build_prompt(
                        rec.question, rec.question_date, result.retrieved_texts, rec.is_abstention,
                    )
                    txt, gms, gerr = call_openai_generator(prompt, args.generator, openai_key)
                    # Stash generator output in a side-channel field (extend record dict)
                    setattr(result, "generated_answer", txt)
                    setattr(result, "generation_ms", gms)
                    setattr(result, "generator_model", args.generator)
                    if gerr:
                        result.error = (result.error or "") + f"; gen: {gerr}"
            except Exception as e:
                result.error = f"{type(e).__name__}: {e}"
                n_err += 1
            finally:
                if proc is not None:
                    stop_api_server(proc)
                # Clean per-q DB + md (keep results JSONL only)
                shutil.rmtree(qdir, ignore_errors=True)

            rec_dict = asdict(result)
            # Pick up the dynamically-added task-accuracy fields if present
            for k in ("generated_answer", "generation_ms", "generator_model"):
                if hasattr(result, k):
                    rec_dict[k] = getattr(result, k)
            fh.write(json.dumps(rec_dict) + "\n")
            fh.flush()
            n_done += 1

            if n_done % args.progress_every == 0:
                elapsed = time.time() - t_start
                rate = n_done / elapsed if elapsed > 0 else 0.0
                eta = (len(sample) - n_done - n_skip) / rate if rate > 0 else 0.0
                print(
                    f"[run] {n_done}/{len(sample) - n_skip} "
                    f"({100*n_done/max(1,len(sample)-n_skip):.1f}%) "
                    f"errs={n_err} elapsed={elapsed:.0f}s rate={rate:.2f}q/s ETA={eta:.0f}s",
                    file=sys.stderr,
                )

    elapsed = time.time() - t_start
    print(
        f"[run] DONE n_done={n_done} n_err={n_err} n_skip={n_skip} "
        f"elapsed={elapsed:.0f}s out={out_path}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
