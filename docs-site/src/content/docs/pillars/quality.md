---
title: Quality Pillar (Q)
description: Retrieval benchmarks, eval harnesses, and the shadow discipline that keeps ranking honest.
sidebar:
  order: 1
---

> Q is the gating constraint. Numbers must be demonstrably better before GTM Phase 2 activates.

## Philosophy

Every ranking change ships in **shadow mode** (exposed via `/api/health.salience`) for ≥7 days before it affects real queries. If the numbers do not improve in shadow, the change does not ship to prod.

This is the shadow discipline. It applies to salience formula changes, RRF parameter tuning, section boost adjustments — everything that touches scoring.

## Current numbers

| Metric | Value | Baseline |
|---|---|---|
| Hybrid nDCG (golden set) | 0.699 | FTS-only = 0.000 |
| E14 language-aware RRF improvement | +1.92pp | Zero regression |
| Vector coverage | 99.99% | — |
| Monthly OPEX | < $11 | — |

## Q1 — LoCoMo benchmark

Source: [`eval/locomo/README.md`](https://github.com/totobusnello/memoria-nox/tree/main/eval/locomo)

LoCoMo is a conversational memory benchmark measuring retrieval precision on long-term dialogue. Harness scaffold is live; full run requires VPS with live corpus.

```bash
cd eval/locomo
npm run eval -- --limit 100   # run 100 queries
npm run report                # generate comparison report
```

## Q2 — LongMemEval benchmark

Source: [`eval/longmemeval/README.md`](https://github.com/totobusnello/memoria-nox/tree/main/eval/longmemeval)

LongMemEval tests single-session and multi-session memory over long horizons. Standardized benchmark enabling direct comparison with competitors.

```bash
cd eval/longmemeval
npm run eval -- --sessions 50
```

## Q3 — Latency benchmark

Source: [`eval/latency/README.md`](https://github.com/totobusnello/memoria-nox/tree/main/eval/latency)

p50/p95/p99 latency for hybrid search at corpus sizes 10K / 70K / 200K chunks.

Target: p50 < 200ms at 70K chunks on VPS hardware.

## Q4 — Public COMPARISON matrix

Source: [`benchmark/README.md`](https://github.com/totobusnello/memoria-nox/tree/main/benchmark)

Public reproducible comparison framework. Generated via `GATE_VERIFIED=1 npm run comparison`.

The COMPARISON matrix is the GTM Phase 2 gate. Until it shows superiority on LoCoMo and LongMemEval, the hero positioning stays conservative.

## Eval harness design

The harness (`eval/`) uses a golden set of ~10 curated queries with known-good chunk IDs. nDCG@10 is the primary metric. All queries are stored in `eval/golden/` and versioned with the harness.

:::tip[Baseline first]
Always establish a baseline before any search tuning. Commit `eval/results/baseline-<date>.json` before the change, then compare against it. No baseline = no valid comparison.
:::
