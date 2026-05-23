"""
Q4 COMPARISON shared library — corpus loaders and helpers.

The corpus loaders in `corpus_loader` produce ChunkRecord generators with
stable IDs that match the gold_chunk_ids encoding used by the runner. Adapters
consume them to populate their respective stores BEFORE runner.py drives the
retrieval comparison.

Public API:
    from lib.corpus_loader import (
        ChunkRecord,
        load_locomo_corpus,
        load_longmemeval_corpus,
    )

Design contract (per `specs/2026-05-23-Q4-comparison-execution-plan.md` §5):
    "competitors get IDENTICAL chunk corpus that nox-mem uses"

The loaders are the canonical source of that corpus. Cache lives at
`eval/q4-comparison/cache/` (gitignored, regenerable on demand).
"""

from __future__ import annotations

from .corpus_loader import (
    ChunkRecord,
    load_locomo_corpus,
    load_longmemeval_corpus,
)

__all__ = [
    "ChunkRecord",
    "load_locomo_corpus",
    "load_longmemeval_corpus",
]
