#!/usr/bin/env python3
"""
Q4 COMPARISON runner — single dispatcher across 6 systems.

Drives every adapter against LongMemEval + LoCoMo and writes per-system JSON
output. Latency is timed externally (around each adapter call) so each system
is measured the same way regardless of in-process vs subprocess vs HTTP.

Usage (Saturday morning):

    python runner.py --dry-run            # validate config + adapter list only
    python runner.py --systems nox_mem,mem0 --datasets locomo --limit 10
    python runner.py --systems all --datasets locomo,longmemeval --limit 100

Output schema (per system, written to output/<system>.json):

    {
      "meta": {
        "system": "mem0",
        "version": "0.1.114",
        "datasets": ["locomo", "longmemeval"],
        "limit": 100,
        "k": 10,
        "started_at": "2026-05-24T09:32:11Z",
        "finished_at": "2026-05-24T10:14:33Z",
        "runner_commit": "<git sha>",
        "harness_version": "1.0"
      },
      "queries": [
        {
          "dataset": "locomo",
          "category": "single-hop",
          "question_id": "conv-48::q13",
          "query": "What places give Deborah peace?",
          "gold_chunk_ids": ["conv-48::D2:13", ...],
          "k": 10,
          "results": [{"id": "...", "score": 0.91, "text": "...", "source": "..."}, ...],
          "latency_ms": 412.7,
          "error": null
        }
      ]
    }

Datasets live in `eval/longmemeval/` and `eval/locomo/`. The runner reads the
dry-run-sample.json files to find query metadata (question_id, gold_chunk_ids,
category). Real Q4 datasets should be N=100 stratified samples — Toto can
override --queries-file to point at custom JSONL.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Local imports
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from adapters import ALL_ADAPTERS  # noqa: E402


# ---------------------------------------------------------------------------
# Dataset loaders
# ---------------------------------------------------------------------------

REPO_ROOT = HERE.parent.parent  # eval/q4-comparison → repo root

DATASET_PATHS = {
    "locomo": REPO_ROOT / "eval" / "locomo" / "dry-run-sample.json",
    "longmemeval": REPO_ROOT / "eval" / "longmemeval" / "dry-run-sample.json",
}


@dataclass
class QueryRecord:
    dataset: str
    question_id: str
    query: str
    gold_chunk_ids: list[str] = field(default_factory=list)
    category: str | None = None


def load_dataset(name: str, queries_file: Path | None, limit: int | None) -> list[QueryRecord]:
    """
    Load query records for a dataset. Supports:
      - default: eval/<name>/dry-run-sample.json (small sample)
      - --queries-file: explicit JSONL with one record per line

    JSONL record shape (minimal): {"question_id", "question", ...}
    """
    if queries_file is not None and queries_file.exists():
        return _load_jsonl(queries_file, name, limit)

    path = DATASET_PATHS.get(name)
    if path is None or not path.exists():
        raise FileNotFoundError(
            f"dataset {name!r} not found — expected at {path}. "
            "Override with --queries-file <path>."
        )
    return _load_dryrun_sample(path, name, limit)


def _load_jsonl(path: Path, dataset: str, limit: int | None) -> list[QueryRecord]:
    records: list[QueryRecord] = []
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            records.append(_to_record(row, dataset))
            if limit is not None and len(records) >= limit:
                break
    return records


def _load_dryrun_sample(path: Path, dataset: str, limit: int | None) -> list[QueryRecord]:
    """Read the existing dry-run-sample.json (Q2/Q1 format)."""
    payload = json.loads(path.read_text())
    rows = payload.get("records", [])
    records = [_to_record(row, dataset) for row in rows]
    if limit is not None:
        records = records[:limit]
    return records


def _to_record(row: dict[str, Any], dataset: str) -> QueryRecord:
    return QueryRecord(
        dataset=dataset,
        question_id=str(row.get("question_id") or row.get("id") or ""),
        query=row.get("question") or row.get("query") or "",
        gold_chunk_ids=list(
            row.get("gold_chunk_ids")
            or row.get("answer_session_ids")
            or []
        ),
        category=row.get("category_name") or row.get("question_type") or None,
    )


# ---------------------------------------------------------------------------
# Adapter loading
# ---------------------------------------------------------------------------


def load_adapter(name: str):
    module_name = f"adapters.{name}"
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        raise SystemExit(f"failed to load adapter {name!r}: {exc}") from exc


def resolve_systems(raw: str) -> list[str]:
    if raw == "all":
        return list(ALL_ADAPTERS)
    requested = [s.strip() for s in raw.split(",") if s.strip()]
    invalid = [s for s in requested if s not in ALL_ADAPTERS]
    if invalid:
        raise SystemExit(
            f"unknown systems: {invalid}. Valid: {ALL_ADAPTERS}"
        )
    return requested


# ---------------------------------------------------------------------------
# Runner core
# ---------------------------------------------------------------------------


def load_corpus(corpus_file: Path | None) -> list[dict[str, Any]]:
    """
    Load corpus chunks from a JSONL file for ingest_corpus() adapters.

    Each line: {"id": ..., "text": ..., ...}
    Returns [] if corpus_file is None or does not exist.
    """
    if corpus_file is None or not corpus_file.exists():
        return []
    chunks: list[dict[str, Any]] = []
    with corpus_file.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def run_system(
    system: str,
    queries: list[QueryRecord],
    k: int,
    output_dir: Path,
    dry_run: bool,
    corpus_chunks: list[dict[str, Any]] | None = None,
    skip_ingest: bool = False,
) -> Path:
    """Drive a single adapter through all queries; persist JSON."""
    adapter = load_adapter(system)
    started_at = _now_iso()

    if dry_run:
        validation = adapter.validate()
        meta: dict[str, Any] = {
            "system": adapter.NAME,
            "version": adapter.VERSION_PIN,
            "validate": validation,
            "n_queries": len(queries),
            "k": k,
            "dry_run": True,
            "started_at": started_at,
        }
        out_path = output_dir / f"{system}.dry-run.json"
        out_path.write_text(json.dumps(meta, indent=2))
        print(f"[{system}] DRY RUN — would run {len(queries)} queries @ k={k}. → {out_path}")
        return out_path

    print(f"[{system}] SETUP")
    adapter.setup()

    # Ingest corpus if the adapter exposes ingest_corpus() and we have chunks.
    # Systems like Zep/Letta/EverMind need corpus pre-loaded before search.
    # nox_mem/mem0/agentmemory manage their own persistent stores.
    ingest_fn = getattr(adapter, "ingest_corpus", None)
    if ingest_fn is not None and corpus_chunks and not skip_ingest:
        print(f"[{system}] INGEST {len(corpus_chunks)} corpus chunks …")
        t_ingest = time.perf_counter()
        try:
            ingest_stats = ingest_fn(corpus_chunks)
            ingest_ms = (time.perf_counter() - t_ingest) * 1000
            print(f"[{system}] INGEST done in {ingest_ms:.0f}ms: {ingest_stats}")
        except Exception as exc:
            print(f"[{system}] INGEST ERROR: {exc}", file=sys.stderr)
    elif ingest_fn is not None and not corpus_chunks and not skip_ingest:
        print(
            f"[{system}] WARNING: adapter has ingest_corpus() but no --corpus-file provided. "
            "Search results may be empty. Pass --corpus-file cache/locomo.jsonl (or combined)."
        )
    results: list[dict[str, Any]] = []
    errors = 0
    try:
        for i, record in enumerate(queries, start=1):
            entry: dict[str, Any] = {
                "dataset": record.dataset,
                "category": record.category,
                "question_id": record.question_id,
                "query": record.query,
                "gold_chunk_ids": record.gold_chunk_ids,
                "k": k,
            }
            t0 = time.perf_counter()
            try:
                ranked = adapter.search(record.query, k=k)
                latency_ms = (time.perf_counter() - t0) * 1000
                entry["results"] = ranked
                entry["latency_ms"] = latency_ms
                entry["error"] = None
            except Exception as exc:
                latency_ms = (time.perf_counter() - t0) * 1000
                errors += 1
                entry["results"] = []
                entry["latency_ms"] = latency_ms
                entry["error"] = f"{type(exc).__name__}: {exc}"
                # Don't dump full traceback in the JSON — keep it terse
            results.append(entry)
            if i % 25 == 0 or i == len(queries):
                print(f"[{system}] {i}/{len(queries)} ({errors} errors)")
    finally:
        adapter.teardown()

    finished_at = _now_iso()
    payload = {
        "meta": {
            "system": adapter.NAME,
            "version": adapter.VERSION_PIN,
            "k": k,
            "n_queries": len(queries),
            "n_errors": errors,
            "datasets": sorted({r.dataset for r in queries}),
            "started_at": started_at,
            "finished_at": finished_at,
            "harness_version": "1.0",
        },
        "queries": results,
    }
    out_path = output_dir / f"{system}.json"
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"[{system}] WROTE {out_path} ({errors} errors)")
    return out_path


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="runner.py",
        description="Q4 COMPARISON runner — drives 6 adapters against LongMemEval + LoCoMo.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--systems",
        default="all",
        help="comma-separated subset of: " + ",".join(ALL_ADAPTERS) + " (or 'all')",
    )
    p.add_argument(
        "--datasets",
        default="locomo,longmemeval",
        help="comma-separated dataset names",
    )
    p.add_argument("--limit", type=int, default=100, help="max queries per dataset")
    p.add_argument("--k", type=int, default=10, help="ranking cutoff")
    p.add_argument(
        "--output",
        default=str(HERE / "output"),
        help="output directory (default: ./output)",
    )
    p.add_argument(
        "--queries-file",
        default=None,
        help="optional JSONL with explicit query records (overrides dry-run samples)",
    )
    p.add_argument(
        "--corpus-file",
        default=None,
        help=(
            "JSONL file with corpus chunks to ingest before search (used by adapters with "
            "ingest_corpus(), e.g. zep, letta). Each line: {id, text, ...}. "
            "Defaults to cache/<dataset>.jsonl when --datasets is a single dataset. "
            "For multi-dataset runs, pass a combined JSONL or use --skip-ingest."
        ),
    )
    p.add_argument(
        "--skip-ingest",
        action="store_true",
        help="skip ingest_corpus() call even if adapter has it (reuse previously ingested data)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="validate adapters + print plan without making search calls",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    systems = resolve_systems(args.systems)
    datasets = [d.strip() for d in args.datasets.split(",") if d.strip()]
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load all datasets up front (fail fast if missing)
    queries: list[QueryRecord] = []
    queries_file = Path(args.queries_file) if args.queries_file else None
    for ds in datasets:
        qs = load_dataset(ds, queries_file, args.limit)
        print(f"[load] {ds}: {len(qs)} queries (limit={args.limit})")
        queries.extend(qs)

    # Resolve corpus file for ingest_corpus() adapters (zep, letta, evermind).
    # Auto-detect from cache/<dataset>.jsonl when a single dataset is requested
    # and no explicit --corpus-file was given.
    corpus_file: Path | None = None
    if args.corpus_file:
        corpus_file = Path(args.corpus_file)
    elif not args.skip_ingest and len(datasets) == 1:
        candidate = HERE / "cache" / f"{datasets[0]}.jsonl"
        if candidate.exists():
            corpus_file = candidate
            print(f"[corpus] auto-detected: {corpus_file} ({candidate.stat().st_size // 1024}KB)")

    corpus_chunks = load_corpus(corpus_file) if corpus_file else []
    if corpus_chunks:
        print(f"[corpus] loaded {len(corpus_chunks)} chunks from {corpus_file}")

    if args.dry_run:
        print(
            f"[plan] systems={systems} datasets={datasets} k={args.k} "
            f"limit={args.limit} total_queries={len(queries)}"
        )

    for sys_name in systems:
        try:
            run_system(
                sys_name,
                queries,
                args.k,
                output_dir,
                args.dry_run,
                corpus_chunks=corpus_chunks,
                skip_ingest=args.skip_ingest,
            )
        except Exception:
            print(f"[{sys_name}] FATAL", file=sys.stderr)
            traceback.print_exc()
            # Continue to next system rather than abort entire run
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
