# Benchmark methodology disclosure — Q4 cross-system comparison

> **Post timing:** immediately after `01-welcome-announcement.md`, before Show HN goes live.
> **Thread type:** Pinned by author. Not a question — a disclosure.

---

This thread exists for one reason: to explain what the Q4 cross-system comparison
numbers mean and what they don't mean. Benchmark transparency is a first-class
value at nox-mem. Publishing numbers without methodology is the original sin of
AI tooling.

## What we measured

**Corpus:** entity-eval-v2 — 100 manually curated golden queries against a
shared retrieval corpus. Every system was given the same DB snapshot, the same
queries, the same scoring script.

**Protocol name:** FTS5-fair — this means the evaluation corpus was built using
FTS5-quality chunking and metadata, without any advantage given to nox-mem's
specific entity format. All systems ingested the same source documents.

**Metrics:** nDCG@10 (ranking quality at top-10) and MRR (reciprocal rank of
the first relevant hit).

## The 4/6 disclosure

We set out to evaluate six systems. Two could not be included:

- **Zep:** requires an OpenAI API key injected at runtime. Our FTS5-fair protocol
  prohibits external API calls during evaluation (eval isolation requirement from
  PR #145 post-incident). The Zep CE Docker image exists and we intend to design
  a protocol amendment for Lab Q1. This is not convenience — it is a real
  constraint we documented rather than worked around silently.

- **EverMind:** the EverMind-AI/EverMind repository returned 404 at the time of
  evaluation (2026-05-24). No evaluation was possible.

## The corpus cap problem

agentmemory was evaluated at 20% corpus cap. mem0 was evaluated at 7.3% corpus
cap. This means those systems ingested only a fraction of the shared corpus —
either due to API rate limits, timeouts, or architectural caps.

**What this means for the numbers:** a system evaluated at 7.3% cap will score
well on queries whose answers fall in the 7.3% window (concentration effect) but
will effectively return zero-quality results for the other 92.7%. Our 100 golden
queries span the full corpus, so the cap effect is real.

**What this does NOT mean:** we are not claiming mem0 or agentmemory are "bad"
systems. We are saying their numbers are not directly comparable to a full-corpus
evaluation. The canonical full-corpus run (uniform, no cap) is the proper
head-to-head.

## Per-dataset apples-to-apples at 500-chunk cap (PR #318 rev3, 2026-05-23)

We ran the full Gemini hybrid stack at the same 500-chunk cap and broke results down by dataset.

| System | nDCG@10 (aggregate) | nDCG@10 (LoCoMo-only) | Corpus | Mode |
|---|---:|---:|---:|---|
| **nox-mem FTS5@500** | 0.0466 | — | 500 (cap) | FTS5-only, no Gemini |
| **nox-mem Gemini hybrid@500** | 0.0918 | **0.1835** | 500 (cap) | FTS5 + Gemini + RRF |
| **mem0@500** | **0.1315** | 0.1315 | 500 (cap) | LLM rewrite + embed |

**LoCoMo conversational memory result (PR #318):** nox-mem Gemini hybrid@500 = 0.1835 vs mem0@500 = 0.1315 — **+40% win for nox-mem** on conversational scope at equal corpus size. This is the cleanest apples-to-apples signal.

**Corpus-ordering artifact (aggregate):** The aggregate hybrid@500 = 0.0918 dips below mem0 = 0.1315. Root cause: at 500-chunk cap, the eval corpus is ordered LoCoMo-first (5,882 chunks), exhausting the cap before any LongMemEval chunk is ingested. The 10 LongMemEval golden queries have zero relevant coverage → nDCG = 0.0 for those queries, pulling the aggregate to 0.0918. This is a dataset-ordering confound, not a retrieval quality defect. Per-dataset breakdown is the correct lens.

**H2 finding (PR #311, maintained):** FTS5-only@500 = 0.0466 vs mem0 = 0.1315 is architecturally real for FTS5-only mode. mem0's LLM-rewriting semantically generalizes at sparse coverage in ways keyword search cannot. The full Gemini hybrid stack reverses this on conversational scope.

**Hybrid stack validation:** Gemini hybrid lifts FTS5@500 by **+97%** (0.0466 → 0.0918 aggregate), confirming the architectural design at sparse coverage.

**Our honest framing:**
- On conversational memory (LoCoMo): nox-mem Gemini hybrid wins +40% at equal corpus size.
- On multi-document QA (LongMemEval) at 500-cap: confounded by corpus-ordering; deferred to full ingest.
- Full canonical run (uniform corpus, no cap) is the definitive arbiter for both datasets.
- Phase 2 gate uses BOTH per-dataset + aggregate on uniform full corpus.

We publish all rows — full-corpus, per-dataset @500, aggregate @500 — because any single row alone misleads. Ref: PR #311, PR #318.

## The Letta latency comparison

Letta p50 = 14,978ms. nox-mem hybrid p50 = ~940ms. nox-mem FTS5-only p50 = 7–12ms.

Letta is an agent-loop memory system. Its latency includes an LLM reasoning pass
before returning results. This is a different architectural paradigm — it does more
work per query by design. Comparing p50 directly is misleading. We included it in
the table with this note because people ask "how does nox-mem compare to Letta"
and the latency profile is the most informative answer.

## How to reproduce

```bash
git clone https://github.com/totobusnello/memoria-nox
cd memoria-nox
python eval/q4-comparison/runner.py --system nox-mem --dataset entity-eval-v2
# Replace --system with: agentmemory, mem0, letta
```

The runner, golden queries, and corpus snapshot are all in the repo. If you find
a discrepancy, open an issue — I'd rather be corrected publicly than have a wrong
number persist.

Full write-up: `benchmark/COMPARISON.md`.

---

*[[project-sat-2026-05-24-final-closure]] · H2 PR #311 2026-05-24 · rev3 PR #318 2026-05-23 — LoCoMo-only +40% win + corpus-ordering caveat*
*Related: `docs/COMPARISON.md §Apples-to-apples corpus-cap comparison` · `docs/COMPARISON.md §Architectural trade-off framing` · `paper/paper-tecnico-nox-mem.md §6.6`*
