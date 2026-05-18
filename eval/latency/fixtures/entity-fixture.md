---
type: concept
slug: latency-benchmark-fixture
title: Latency Benchmark Fixture Entity
tags: [benchmark, fixture, eval]
created: 2026-05-17
retention_days: 30
pain: 0.1
importance: 0.3
---

## compiled

This is a fixture entity file used exclusively by the latency benchmark harness.
It is NOT a real nox-mem knowledge entity and should never appear in production
search results.

The entity represents a hypothetical concept: the measurement of end-to-end
latency in a hybrid memory retrieval system. Hybrid search combines BM25 full-text
search with vector semantic search and knowledge graph traversal, fused via
Reciprocal Rank Fusion (RRF).

Key properties of a well-designed latency benchmark:
- Uses process.hrtime.bigint() for nanosecond-accurate wall-clock measurement.
- Separates warmup iterations (discarded) from measured iterations (counted).
- Reports p50, p95, and p99 separately — p50 is steady-state, p99 captures GC.
- Documents cold vs warm OS page cache as separate measurement conditions.
- Does not trim outliers in v1; tail behavior is intentionally preserved.

The goal is to produce defensible numbers that can be compared against competitor
claims such as "sub-90ms retrieval" — requiring that our measurement methodology
is clearly documented and reproducible.

Statistical note: at n=100, the 95% confidence interval half-width is
approximately ±2σ/√n. For σ~20ms, this gives ±4ms — acceptable for v1.

## timeline

- 2026-05-17: Fixture created for overnight Q3 latency benchmark scaffold.
- This entity is safe to re-ingest repeatedly (each run uses unique slug suffix
  via NOX_INGEST_SLUG_SUFFIX env var injected by the harness runner).
