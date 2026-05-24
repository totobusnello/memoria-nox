"""
Chunk summarizer — Gemini Flash Lite condenser for the Q4 A2 path.

Replicates the mem0 INGEST-SIDE concentration mechanism by passing each raw
corpus chunk through Gemini Flash Lite, asking for an atomic-fact rewrite,
and writing a new JSONL with the SAME chunk id (so gold matching survives).

Why this exists
---------------
Two earlier query-side paths failed to close the -0.0397 nDCG@10 gap vs
mem0@500 on the Q4 capped@500 benchmark:

  - PR #337 (query rewrite, -11.8%): more lexical noise, no concentration.
  - PR #339 (E+F+H combo, +2.4% only): partial; gap persists.

Both negatives confirmed mem0's win is INGEST-SIDE — its LLM extracts facts
during ingest, condensing 500-2000 char raw turns into ~80-150 char fact
sentences. That density boost helps recall at sparse coverage (cap=500).

A2 replicates this with Gemini only (no OpenAI dependency, per Q/A/P pillar
3 "Autonomy"). Same model family used elsewhere in the stack; no vendor
expansion.

Pipeline
--------
    raw corpus chunk (id, text, ...)
            │
            ▼
    Gemini Flash Lite (prompt template A/B/C)
            │
            ▼
    summarized text (1-3 atomic facts, ~80-150 chars)
            │
            ▼
    new ChunkRecord (id PRESERVED, text REPLACED, metadata.original_len added)

Cost model
----------
- gemini-2.5-flash-lite: $0.075/M input, $0.30/M output (2026-05-24 pricing).
- Mean raw chunk: ~144 chars (LoCoMo turn) up to ~2070 chars (LongMemEval session).
- Output target: ~80-150 tokens (mem0-style atomic fact).
- 500-chunk run cost est: ~$0.01. Full 6830-chunk run: ~$0.43.

Concurrency
-----------
Single-threaded with adaptive rate-limit (50ms between calls). Gemini Flash
Lite free tier ~1500 RPM → 25 RPS theoretical; we stay under 20 RPS for safety.
Failure mode: on per-chunk error, log + skip (keep original text fallback);
record in cost-tracking.jsonl. Hard $5 cost cap halts the run.

Idempotency
-----------
Persistent cache at the output path. If a chunk_id already exists in the
output JSONL, we skip the API call and reuse the cached summary. Allows
resuming after Ctrl+C / crash without burning $$ again.

CLAUDE.md compliance
--------------------
- PT-BR docstrings: not user-facing; module comments in English.
- No GEMINI_API_KEY echo or commit (env-only).
- Use only stdlib + `requests` (already installed). No deprecated genai SDK.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Iterator

# Local import (corpus_loader is canonical, never reimplement)
HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from lib.corpus_loader import (  # noqa: E402
    ChunkRecord,
    load_locomo_corpus,
    load_longmemeval_corpus,
)

# ---------------------------------------------------------------------------
# Config + constants
# ---------------------------------------------------------------------------

_DEFAULT_MODEL = "gemini-2.5-flash-lite"
_GENERATE_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)
_REQUEST_TIMEOUT_S = 30
_RATE_DELAY_S = 0.05  # ~20 RPS, well under the Flash Lite RPM limits
_MAX_RETRIES = 3
_RETRY_BACKOFF_S = 1.5

# Pricing (USD per 1M tokens, 2026-05-24)
_PRICING = {
    "gemini-2.5-flash-lite": {"in": 0.075, "out": 0.30},
    "gemini-2.5-flash":      {"in": 0.30,  "out": 2.50},
}

# Hard cost cap — abort the run if exceeded
_HARD_COST_CAP_USD = 5.0


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

# Template A — Fact extraction (mem0-style atomic facts).
TEMPLATE_A_FACTS = (
    "Extract 1-3 atomic facts from the passage below. Each fact must be a "
    "single sentence under 25 words. Focus on names, dates, numbers, "
    "decisions, relationships, places. Drop greetings, filler, and emotional "
    "commentary. Output ONLY the facts, one per line, no numbering, no "
    "preamble.\n\n"
    "Passage:\n{chunk}\n\n"
    "Facts:"
)

# Template B — TL;DR concentration (single dense sentence pair).
TEMPLATE_B_TLDR = (
    "Summarize the passage into 1-2 dense sentences capturing the most "
    "retrieval-relevant information: entities (people, places), events, "
    "numbers, decisions, dates. Drop conversational filler. Output ONLY "
    "the summary.\n\n"
    "Passage:\n{chunk}\n\n"
    "Summary:"
)

# Template C — Hybrid (facts + contextual anchor).
TEMPLATE_C_HYBRID = (
    "Write a dense 2-sentence summary of the passage:\n"
    "- Sentence 1: core facts (who/what/when/where/numbers).\n"
    "- Sentence 2: one contextual anchor (why it matters, what it connects to).\n"
    "Drop filler. Output ONLY the 2 sentences, no labels.\n\n"
    "Passage:\n{chunk}\n\n"
    "Summary:"
)

TEMPLATES: dict[str, str] = {
    "A": TEMPLATE_A_FACTS,
    "B": TEMPLATE_B_TLDR,
    "C": TEMPLATE_C_HYBRID,
}


# ---------------------------------------------------------------------------
# Cost accounting
# ---------------------------------------------------------------------------


def _estimate_tokens(text: str) -> int:
    """Cheap heuristic — Gemini doesn't return usage by default in older REST.

    Mirrors the ~4 chars/token rule of thumb. Close enough for cost guardrails
    (we err high). When `usageMetadata` is present in the response, that wins.
    """
    return max(1, len(text) // 4)


def _cost_for(model: str, in_tokens: int, out_tokens: int) -> float:
    p = _PRICING.get(model) or _PRICING[_DEFAULT_MODEL]
    return (in_tokens * p["in"] + out_tokens * p["out"]) / 1_000_000.0


# ---------------------------------------------------------------------------
# Gemini caller
# ---------------------------------------------------------------------------


def _gemini_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY not set. source /tmp/q4-gemini-env.sh before running."
        )
    return key


def _redact(msg: str) -> str:
    """Strip any API key fragment from log/error strings (defence in depth)."""
    msg = re.sub(r"key=[A-Za-z0-9_\-]+", "key=<REDACTED>", msg)
    msg = re.sub(r"AIza[A-Za-z0-9_\-]{10,}", "AIza<REDACTED>", msg)
    return msg


def _call_gemini(
    *,
    prompt: str,
    model: str,
    max_output_tokens: int = 200,
    temperature: float = 0.2,
) -> tuple[str, int, int]:
    """Single Gemini call with retry. Returns (text, in_tokens, out_tokens).

    Raises after _MAX_RETRIES on persistent failure.
    """
    import requests

    url = _GENERATE_ENDPOINT.format(model=model)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "topP": 0.95,
            "maxOutputTokens": max_output_tokens,
        },
    }

    last_err: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = requests.post(
                url,
                params={"key": _gemini_api_key()},
                json=payload,
                timeout=_REQUEST_TIMEOUT_S,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates") or []
            if not candidates:
                # Empty completion (safety filter or model refused).
                return "", _estimate_tokens(prompt), 0
            parts = (candidates[0].get("content") or {}).get("parts") or []
            text = "".join(p.get("text", "") for p in parts).strip()

            usage = data.get("usageMetadata") or {}
            in_tok = int(usage.get("promptTokenCount") or _estimate_tokens(prompt))
            out_tok = int(usage.get("candidatesTokenCount") or _estimate_tokens(text))
            return text, in_tok, out_tok
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_BACKOFF_S * attempt)
            else:
                raise RuntimeError(
                    f"gemini call failed after {_MAX_RETRIES} attempts: "
                    f"{type(exc).__name__}: {_redact(str(exc))}"
                ) from last_err
    raise RuntimeError("unreachable")  # pragma: no cover


# ---------------------------------------------------------------------------
# Summarizer pipeline
# ---------------------------------------------------------------------------


def summarize_chunk(
    chunk: ChunkRecord,
    *,
    template: str = "A",
    model: str = _DEFAULT_MODEL,
    max_output_tokens: int = 200,
) -> tuple[str, int, int]:
    """Summarize one chunk. Returns (summary_text, in_tokens, out_tokens).

    Falls back to the original chunk text if the LLM returns an empty string
    (safety-filter, empty response, etc.). This keeps gold-id retrieval
    minimally viable even on rare failures.
    """
    tmpl = TEMPLATES.get(template.upper())
    if tmpl is None:
        raise ValueError(f"unknown template {template!r}; valid: {sorted(TEMPLATES)}")
    prompt = tmpl.format(chunk=chunk.text)
    summary, in_tok, out_tok = _call_gemini(
        prompt=prompt,
        model=model,
        max_output_tokens=max_output_tokens,
    )
    if not summary.strip():
        # Fallback: keep original text — better to be a dud chunk than to
        # erase a row entirely.
        return chunk.text, in_tok, 0
    return summary.strip(), in_tok, out_tok


def _existing_ids(output_path: Path) -> set[str]:
    """Read prior summarized JSONL and collect chunk ids already processed.

    Enables resumable runs: pass the same output path, skip ids we already
    wrote. Cost cap is honoured per fresh session (not cumulative across runs).
    """
    if not output_path.exists():
        return set()
    out: set[str] = set()
    with output_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and isinstance(row.get("id"), str):
                out.add(row["id"])
    return out


def summarize_corpus_stream(
    *,
    output_path: Path,
    cost_log_path: Path,
    template: str = "A",
    model: str = _DEFAULT_MODEL,
    datasets: list[str] | None = None,
    limit: int | None = None,
    max_output_tokens: int = 200,
    rate_delay_s: float = _RATE_DELAY_S,
    concurrency: int = 1,
) -> dict[str, Any]:
    """Stream raw corpus → summarized JSONL. Returns a summary dict.

    Parameters
    ----------
    output_path: where to write summarized chunk JSONL.
    cost_log_path: append-only JSONL of cost batches (every 100 chunks).
    template: 'A' | 'B' | 'C' — prompt strategy.
    model: Gemini model id (default flash-lite).
    datasets: which corpora to include. Default: ['locomo', 'longmemeval'].
    limit: cap total chunks (matches NOX_MEM_INGEST_LIMIT cap protocol).
    max_output_tokens: hard limit per Gemini call.
    rate_delay_s: sleep between calls (rate limiting).
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cost_log_path = Path(cost_log_path)
    cost_log_path.parent.mkdir(parents=True, exist_ok=True)

    datasets = datasets or ["locomo", "longmemeval"]
    seen = _existing_ids(output_path)

    fh_out = output_path.open("a", encoding="utf-8")
    fh_cost = cost_log_path.open("a", encoding="utf-8")

    total_in = 0
    total_out = 0
    total_cost = 0.0
    processed = 0
    skipped = 0
    errors = 0
    batch_in = 0
    batch_out = 0
    batch_count = 0
    batch_started = time.time()

    def log_batch(force: bool = False) -> None:
        nonlocal batch_in, batch_out, batch_count, batch_started
        if not force and batch_count < 100:
            return
        if batch_count == 0:
            return
        elapsed = time.time() - batch_started
        cost = _cost_for(model, batch_in, batch_out)
        row = {
            "ts": int(time.time()),
            "model": model,
            "template": template,
            "batch_size": batch_count,
            "in_tokens": batch_in,
            "out_tokens": batch_out,
            "cost_usd": round(cost, 6),
            "elapsed_s": round(elapsed, 2),
        }
        fh_cost.write(json.dumps(row) + "\n")
        fh_cost.flush()
        print(
            f"[summarizer] batch n={batch_count} cost=${cost:.4f} "
            f"({batch_in} in / {batch_out} out tok, {elapsed:.1f}s)",
            file=sys.stderr,
        )
        batch_in = batch_out = batch_count = 0
        batch_started = time.time()

    def chunk_streams() -> Iterator[ChunkRecord]:
        # IMPORTANT: matches the canonical ingest order used by the cap
        # protocol (LoCoMo first then LongMemEval). Cap=500 = 500 LoCoMo turns.
        if "locomo" in datasets:
            for c in load_locomo_corpus():
                yield c
        if "longmemeval" in datasets:
            for c in load_longmemeval_corpus("oracle"):
                yield c

    def process_one(chunk: ChunkRecord) -> tuple[ChunkRecord, str, int, int, Exception | None]:
        """Pure function — safe to run in a worker thread."""
        try:
            s, in_t, out_t = summarize_chunk(
                chunk,
                template=template,
                model=model,
                max_output_tokens=max_output_tokens,
            )
            return chunk, s, in_t, out_t, None
        except Exception as exc:  # noqa: BLE001
            return chunk, chunk.text, _estimate_tokens(chunk.text), 0, exc

    def commit_result(
        chunk: ChunkRecord, summary: str, in_tok: int, out_tok: int,
        exc: Exception | None,
    ) -> bool:
        """Write one summarized row to disk; update counters; return False to halt."""
        nonlocal total_in, total_out, total_cost
        nonlocal batch_in, batch_out, batch_count, processed, errors
        if exc is not None:
            errors += 1
            if errors <= 5:
                print(
                    f"[summarizer] error chunk {chunk.id}: "
                    f"{type(exc).__name__}: {_redact(str(exc))}",
                    file=sys.stderr,
                )
        new_meta = dict(chunk.metadata or {})
        new_meta["a2_original_len"] = len(chunk.text)
        new_meta["a2_template"] = template
        new_meta["a2_model"] = model
        new_meta["a2_in_tokens"] = in_tok
        new_meta["a2_out_tokens"] = out_tok
        row = ChunkRecord(
            id=chunk.id,
            text=summary,
            dataset=chunk.dataset,
            conversation_id=chunk.conversation_id,
            day=chunk.day,
            metadata=new_meta,
        )
        fh_out.write(row.to_jsonl() + "\n")
        fh_out.flush()
        total_in += in_tok
        total_out += out_tok
        total_cost = _cost_for(model, total_in, total_out)
        batch_in += in_tok
        batch_out += out_tok
        batch_count += 1
        processed += 1
        if total_cost > _HARD_COST_CAP_USD:
            print(
                f"[summarizer] HARD COST CAP {_HARD_COST_CAP_USD} USD HIT "
                f"(spent ${total_cost:.4f}). Halting.",
                file=sys.stderr,
            )
            return False
        log_batch(force=False)
        return True

    try:
        if concurrency <= 1:
            # Serial path — preserves prior behaviour (rate_delay_s respected).
            for chunk in chunk_streams():
                if limit is not None and processed + skipped >= limit:
                    break
                if chunk.id in seen:
                    skipped += 1
                    continue
                c, s, in_t, out_t, exc = process_one(chunk)
                if not commit_result(c, s, in_t, out_t, exc):
                    break
                if rate_delay_s > 0:
                    time.sleep(rate_delay_s)
        else:
            # Parallel path — ThreadPoolExecutor (HTTP I/O bound).
            # Gemini Flash Lite free tier ≈ 1500 RPM (25 RPS); cap concurrency
            # at min(requested, 20) for safety.
            from concurrent.futures import ThreadPoolExecutor, as_completed
            workers = max(1, min(concurrency, 20))
            print(
                f"[summarizer] parallel mode, concurrency={workers}",
                file=sys.stderr,
            )
            pending: list[Any] = []
            iterator = chunk_streams()

            def maybe_submit(executor) -> bool:
                """Pull next chunk respecting `seen` and `limit`; submit. False=stop."""
                while True:
                    try:
                        chunk = next(iterator)
                    except StopIteration:
                        return False
                    if chunk.id in seen:
                        nonlocal_skipped()
                        continue
                    if limit is not None and (processed + nonlocal_skipped.value + len(pending)) >= limit:
                        return False
                    pending.append(executor.submit(process_one, chunk))
                    return True

            class _Counter:
                value = 0
                def __call__(self) -> None:
                    self.value += 1
            nonlocal_skipped = _Counter()

            with ThreadPoolExecutor(max_workers=workers) as executor:
                # Prime the pool
                for _ in range(workers * 2):
                    if not maybe_submit(executor):
                        break
                halt = False
                while pending and not halt:
                    # Wait for any future; this iteration we drain whatever finishes first.
                    done = None
                    for i, fut in enumerate(pending):
                        if fut.done():
                            done = i
                            break
                    if done is None:
                        # Block on first
                        fut = pending[0]
                        c, s, in_t, out_t, exc = fut.result()
                        pending.pop(0)
                    else:
                        c, s, in_t, out_t, exc = pending.pop(done).result()
                    if not commit_result(c, s, in_t, out_t, exc):
                        halt = True
                        break
                    # Top up the pool
                    if not maybe_submit(executor):
                        # Stream exhausted — let remaining pending drain
                        pass
            skipped += nonlocal_skipped.value
    finally:
        log_batch(force=True)
        fh_out.close()
        fh_cost.close()

    summary_stats = {
        "processed": processed,
        "skipped_already_done": skipped,
        "errors": errors,
        "in_tokens": total_in,
        "out_tokens": total_out,
        "cost_usd": round(total_cost, 6),
        "template": template,
        "model": model,
        "output_path": str(output_path),
        "cost_log_path": str(cost_log_path),
    }
    print(f"[summarizer] DONE: {json.dumps(summary_stats)}", file=sys.stderr)
    return summary_stats


def load_summarized_corpus(path: Path | str) -> Iterable[ChunkRecord]:
    """Iterate summarized JSONL → ChunkRecord stream (mirrors corpus_loader)."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"summarized corpus not found: {p}")
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            yield ChunkRecord.from_jsonl(line)


# ---------------------------------------------------------------------------
# Mini-ablation harness — n=10 chunks × 3 templates × 5 gold queries
# ---------------------------------------------------------------------------


def mini_ablation(
    *,
    n_chunks: int = 10,
    output_dir: Path,
    model: str = _DEFAULT_MODEL,
) -> dict[str, Any]:
    """Run all 3 templates on a small chunk batch to pick the winner.

    Writes 3 separate summarized JSONLs and prints character compression /
    cost per template. Caller separately scores them against gold queries.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, Any] = {}
    for tmpl in ["A", "B", "C"]:
        out_p = output_dir / f"ablation-template-{tmpl}.jsonl"
        cost_p = output_dir / f"ablation-template-{tmpl}-cost.jsonl"
        # Force regenerate per template — clear file first
        if out_p.exists():
            out_p.unlink()
        if cost_p.exists():
            cost_p.unlink()
        print(f"\n[ablation] === template {tmpl} ===", file=sys.stderr)
        stats = summarize_corpus_stream(
            output_path=out_p,
            cost_log_path=cost_p,
            template=tmpl,
            model=model,
            limit=n_chunks,
            datasets=["locomo"],  # LoCoMo first turns — small, fast
        )
        # Char compression ratio
        rows = list(load_summarized_corpus(out_p))
        orig = sum(int(r.metadata.get("a2_original_len", len(r.text))) for r in rows)
        new = sum(len(r.text) for r in rows)
        compression = (orig - new) / orig if orig else 0.0
        stats["original_total_chars"] = orig
        stats["summarized_total_chars"] = new
        stats["compression_ratio"] = round(compression, 4)
        results[tmpl] = stats
        print(
            f"[ablation] template {tmpl}: {n_chunks} chunks, "
            f"orig={orig} chars → new={new} chars "
            f"(compression={compression:.1%}), cost=${stats['cost_usd']:.4f}",
            file=sys.stderr,
        )
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cli() -> int:
    import argparse

    p = argparse.ArgumentParser(description="Q4 A2 chunk summarizer")
    p.add_argument(
        "cmd",
        choices=["ablation", "summarize"],
        help="ablation=3 templates on n chunks; summarize=full corpus run",
    )
    p.add_argument("--template", default="A", choices=["A", "B", "C"])
    p.add_argument("--model", default=_DEFAULT_MODEL)
    p.add_argument("--limit", type=int, default=None, help="cap chunks")
    p.add_argument("--output", default="cache/summarized.jsonl")
    p.add_argument("--cost-log", default="cache/summarized-cost.jsonl")
    p.add_argument("--n-ablation", type=int, default=10)
    p.add_argument(
        "--concurrency", type=int, default=1,
        help="Parallel Gemini calls (max 20). Default 1=serial.",
    )
    p.add_argument(
        "--ablation-dir", default="cache/ablation",
        help="where to write per-template ablation JSONLs",
    )
    p.add_argument(
        "--datasets",
        default="locomo,longmemeval",
        help="comma-separated subset of {locomo,longmemeval}",
    )
    args = p.parse_args()

    base = Path(__file__).resolve().parent.parent  # eval/q4-comparison/

    if args.cmd == "ablation":
        mini_ablation(
            n_chunks=args.n_ablation,
            output_dir=base / args.ablation_dir,
            model=args.model,
        )
        return 0

    if args.cmd == "summarize":
        datasets = [d.strip() for d in args.datasets.split(",") if d.strip()]
        summarize_corpus_stream(
            output_path=base / args.output,
            cost_log_path=base / args.cost_log,
            template=args.template,
            model=args.model,
            datasets=datasets,
            limit=args.limit,
            concurrency=args.concurrency,
        )
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(_cli())
