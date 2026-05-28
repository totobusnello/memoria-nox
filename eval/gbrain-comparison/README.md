# eval/gbrain-comparison — stub

> **Status:** Planning only. No runner code yet. **Do not run anything from this directory** until Phase A lands.

This directory hosts the head-to-head comparison harness between nox-mem and
**gbrain v0.40.6.0** (Garry Tan, https://github.com/garrytan/gbrain) on the
**LongMemEval `_s` retrieval-recall** benchmark.

gbrain published **97.60% R@5** on the public `_s` split (full n=500, top-K=5,
no LLM in the retrieval loop). Methodology is fully documented in their repo
under `docs/benchmarks/2026-05-07-longmemeval-s.md`; the v0.40.6.0 snapshot
(2026-05-23) confirms the number held across 20 releases.

This is **task #17 (Lab Q1 Parte C)** — a planned Q1 deliverable for the
comparison surface (Phase 2 GTM gate methodology).

---

## Contents

- **`PLAN.md`** — research findings, reproduction recipe, integration approach,
  cost estimate, phased execution plan, honest-comparison considerations.
  **Read this first.**
- **`README.md`** — this file. Will expand to runner usage once Phase A code
  lands.

## What this directory will hold (post Phase A)

```
eval/gbrain-comparison/
├── PLAN.md                       # research + protocol (this PR)
├── README.md                     # usage docs (this PR — stub form)
├── runners/
│   ├── longmemeval-s.ts          # Phase A: adapt eval/longmemeval/run.ts to _s + gbrain output shape
│   └── aggregate.ts              # nDCG@10 + MRR + R@5 + per-type breakdown
├── adapters/
│   ├── nox-fts5.ts               # mirrors gbrain-keyword
│   ├── nox-vector.ts             # mirrors gbrain-vector
│   ├── nox-hybrid.ts             # mirrors gbrain-hybrid (headline)
│   └── nox-hybrid-rewrite.ts     # mirrors gbrain-hybrid+expansion
├── cache/                        # gitignored embedding cache (SHA-256 keyed, ~150MB)
├── scripts/
│   ├── download-embed-cache.sh   # populate cache from VPS or local seed
│   └── download-dataset.sh       # fetch xiaowu0162/longmemeval._s split
└── results/
    └── longmemeval-s-<date>.ndjson
```

## Cross-references

- Sister harness: `../longmemeval/` (existing scaffold, no published numbers).
- Cross-system harness: `../q4-comparison/` (Mem0 / Letta / Zep / nox-mem against LongMemEval + LoCoMo).
- Comparison surface: `docs/COMPARISON.md` (will gain a gbrain row in Phase D).

## Quick links

- Plan: [`PLAN.md`](./PLAN.md)
- gbrain published report: https://github.com/garrytan/gbrain-evals/blob/main/docs/benchmarks/2026-05-07-longmemeval-s.md
- LongMemEval dataset: https://huggingface.co/datasets/xiaowu0162/longmemeval

## Status

| Phase | What | Status |
|---|---|---|
| A | Smoke n=30 stratified | not started |
| B | Small n=100 4-adapter sweep | not started |
| C | Full n=500 publish report | not started |
| D | Comparison surface + decision doc | not started |
| E | OpenAI-embedding parity run (stretch) | not started |

Phases gated on Toto sign-off (see PLAN.md §10 decision list).
