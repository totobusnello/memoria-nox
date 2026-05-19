---
title: Q/A/P Pillars
description: Strategic architecture organized around Quality, Autonomy, and Product.
sidebar:
  order: 2
---

> *"Pain-weighted hybrid memory with shadow discipline — yours by design."*

The Q/A/P pivot (D40, 2026-05-17) reorganizes all roadmap work into three strategic pillars plus a research Lab track.

## Quality (Q) — Numbers #1

The primary differentiator is retrieval quality. Every ranking change ships in shadow mode for ≥7 days before it affects real queries.

| Sprint | Description | Status |
|---|---|---|
| Q1 | LoCoMo benchmark harness | Scaffold ready |
| Q2 | LongMemEval harness | Scaffold ready |
| Q3 | Latency benchmark (p50/p95/p99) | Active |
| Q4 | Public COMPARISON matrix | Framework live |

Key numbers (live corpus):
- **69,298 chunks** ingested
- **15,646 entities / 21,533 relations** in knowledge graph
- **Monthly OPEX < $11**
- **E14 retrieval improvement:** +1.92pp nDCG, zero regression

## Autonomy (A) — Your data, your provider

Zero vendor lock-in. The memory store is a single SQLite file. Copy it and you copy the memory. Switch the embedding provider and the store does not care.

| Sprint | Description | Status |
|---|---|---|
| A1 | Privacy filter (13 patterns, 68 tests, FP 1.7%) | Done |
| A1.1 | BR PII patterns extension | Done |
| A2 | Export / import (portable archive) | Done (staged) |
| A3 | Provider abstraction (Gemini / OpenAI / local swap) | In progress |
| A4 | Zero-vendor validation (8 invariants, CI <1s) | Done |

The encryption stack (A2): AES-256-GCM + scrypt + AAD.

## Product (P) — UX that wins

| Sprint | Description | Status |
|---|---|---|
| P1 | Answer primitive (grounded responses with citations) | Done |
| P2 | Hooks + autocapture | Done (T1–T15) |
| P3 | Temporal queries | Done |
| P4 | IDE connect (14 IDEs) | Stub ready |
| P5 | Viewer realtime | Done (T1–T15) |
| P5a | Event bus refactor | In progress |
| P6 | Mobile | Specced |
| P7 | Browser extension | Specced |

## Lab (Research — 40% capacity)

Research track exploring ideas before committing them to product.

| Sprint | Description | Status |
|---|---|---|
| L2 | Conflict detection (Type 1 done, T2–T4 pending) | T1 done |
| L3 | Confidence field | Done (T1–T13) |
| L4 | Regex-first extraction (parse failure 19.7% → 0%) | Done |

## GTM Phase 2

Gated behind Q4 COMPARISON win. The README hero upgrade and public positioning flip only activate after standardized benchmarks confirm superiority over memanto, agentmemory, and gbrain.

See [Competitive Positioning](/memoria-nox/strategy/competitive-positioning) for the Six Gaps analysis.
