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

## Apples-to-apples corpus-cap comparison (H2 finding — PR #311, 2026-05-24)

To answer the obvious objection — "aren't you just comparing against a capped system to
inflate your numbers?" — we ran nox-mem at the same 500-chunk corpus cap used by mem0 and
measured nDCG@10 on identical queries.

| System | Corpus | nDCG@10 | Mode |
|---|---|---:|---|
| **mem0@500** | 500 chunks (cap) | **0.1315** | LLM rewrite + embed |
| **nox-mem FTS5@500** | 500 chunks (cap) | 0.0466 | FTS5-only, no Gemini |

**H2 confirmed:** mem0's concentration advantage is **architecturally real**, not a
corpus-cap artifact. mem0's LLM-rewriting step semantically generalizes across sparse
corpora in ways FTS5 alone cannot. This is a genuine architectural difference.

**Our honest framing:** two architectures, two use cases.
- mem0 — concentration: best per-result quality at small corpora, at LLM ingest cost.
- nox-mem — coverage + speed + cost: full corpus at zero marginal cost, 30× faster.

We publish both the full-corpus row AND the apples-cap row because either alone misleads.
The full-corpus row favors nox-mem. The apples-cap row favors mem0. Both are true.

**Open question (Lab Q1 E1 — Gemini hybrid@500):** The apples-cap experiment used
nox-mem FTS5-only, not the full Gemini hybrid stack. Gemini dense embeddings at 500 chunks
may close some or all of the concentration gap. This experiment is queued for Lab Q1.
Results will be posted here when available — no speculation in advance.

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

*[[project-sat-2026-05-24-final-closure]] · H2 finding PR #311 added 2026-05-24 · numbers definitive as of 2026-05-24*
*Related: `docs/COMPARISON.md §Apples-to-apples corpus-cap comparison` · `docs/COMPARISON.md §Architectural trade-off framing` · `paper/paper-tecnico-nox-mem.md §6.6`*
