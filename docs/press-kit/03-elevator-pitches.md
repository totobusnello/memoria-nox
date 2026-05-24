# Elevator Pitches — nox-mem

Three timed variants for different contexts. All are in first-person and
pre-approved for use by Toto Busnello in interviews, panels, and podcasts.

---

## 15-Second Pitch (cold intros, hallway conversations)

*Target: ~30 words / 15 seconds at natural speaking pace.*

"nox-mem is open-source, pain-weighted memory for LLM agents — three retrieval
layers, MIT-licensed, single-file SQLite deploy, benchmarks published with runner
code. Agents finally remember what it hurt to forget."

---

## 60-Second Pitch (podcast intros, conference lightning rounds)

*Target: ~150 words / 60 seconds.*

"Every LLM agent has the same problem: it forgets. Not randomly — it forgets the
incident that cost three hours to recover from. It forgets the decision that
disqualified a vendor. It remembers trivia and loses the weight of experience.

nox-mem is my answer to that. It's a three-layer hybrid retrieval system — BM25
full-text, Gemini semantic embeddings, and a knowledge graph — fused together with
Reciprocal Rank Fusion. On top of that is a pain-weighted salience formula:
memories carry a severity score, so the things that hurt to forget rise to the
surface first.

Every design decision is backed by published ablation studies. Eleven experiments,
each with runner code attached, before I declared a parameter production-ready.

It runs on a single VPS. MIT-licensed. No MLOps infrastructure required.

github.com/totobusnello/memoria-nox — try it, star it, break it. I want to know
what hurts in your stack."

---

## 5-Minute Pitch (technical podcasts, conference talks, deep-dive intros)

*Target: ~500 words / 5 minutes at deliberate technical speaking pace.*

### The Problem

LLM agents have a memory problem that nobody talks about honestly.

The standard solution is RAG: embed your documents, retrieve by cosine similarity,
stuff the context window. It works for document search. It does not work for
*experiential memory* — the kind of memory an experienced colleague has. That
colleague doesn't just retrieve the most semantically similar note. They retrieve
the thing that mattered. The incident. The hard-won decision. The person who knows
the real answer.

Cosine similarity doesn't know what mattered. It knows what was similar.

### The Approach

nox-mem addresses this with three ideas working in combination.

**First: three-layer hybrid retrieval.** BM25 full-text search for keyword
precision. Gemini semantic embeddings at 3072 dimensions for conceptual
similarity. A knowledge graph of entities and relations for multi-hop reasoning.
These three signals are fused with Reciprocal Rank Fusion — a robust, proven
method that handles the failure modes of each layer independently.

**Second: pain-weighted salience.** Every chunk ingested into nox-mem carries a
pain score — a severity rating from 0.1 (trivial) to 1.0 (production outage).
The salience formula is `salience = recency × pain × importance`. Memories that
were painful to acquire stay salient longer. An agent running on nox-mem does not
forget the outage that took three hours to diagnose. It weights that memory
differently from a routine note.

**Third: shadow-mode validation.** Scoring changes don't go live until they've
been validated in shadow mode against the production corpus. No blind deploys. No
"this should be better" intuitions shipping to users. The shadow mode runs in
parallel, emitting metrics to `/api/health`, and a new scoring variant only
graduates to active after ≥7 days of measured improvement.

### The Evidence

I ran eleven pre-registered ablation experiments before launch — the G-series,
from G3 to G10d. Each one had a pre-stated hypothesis, an isolated evaluation
database (never the production DB), and runner code published alongside results.
No hidden methodology. No cherry-picked numbers.

The pain-weighted Hard Mutex configuration — ablation G10d — won on multi-hop
queries (+1.58% nDCG) and adversarial queries (+3.04% nDCG) over the baseline.
Those are the two query types where memory systems most commonly fail. That's the
configuration running in production today.

The Q4 cross-system comparison (Sat 2026-05-24 + PR #318) produced three rows that matter.
At full corpus (6,830 chunks), nox-mem hybrid scores nDCG@10 0.6380, 8ms p50, 65%
gold-hit rate — 30× faster than mem0's 273ms, 4× more coverage. At the same 500-chunk
cap, per-dataset breakdown: on LoCoMo conversational memory, nox-mem Gemini hybrid@500
(0.1835) outperforms mem0@500 (0.1315) by +40% at equal corpus size. The aggregate
@500 (0.0918) dips below mem0 due to a corpus-ordering artifact — LoCoMo's 5,882 chunks
exhaust the cap before LongMemEval is ingested, scoring those queries at zero. FTS5-only@500
= 0.0466 (H2 confirmed): FTS5 alone cannot match LLM-rewriting at sparse coverage, but the
full hybrid stack reverses that on conversational scope. All three rows are published in
`benchmark/COMPARISON.md`. This is what honest benchmarking looks like — you report every
row, explain every confound, and let the data speak.

### The Deployment Reality

nox-mem runs on a single Hostinger VPS. SQLite database. Node.js 20. A Gemini
API key. No vector database service. No message queue. No orchestration layer.
68,995 chunks, 100% vector coverage. FTS5-only p50: 7–12ms. Full hybrid p50:
~940ms. Full methodology and disclosure: `benchmark/COMPARISON.md`.

The single-file SQLite design is not an accident. It's a statement: you should
own your memory. Not a cloud vendor's memory service. Yours.

### Call to Action

The code is MIT-licensed. The paper is CC BY 4.0. The evaluation harness is
public. The ablation results are in `audits/`. There is nothing hidden.

github.com/totobusnello/memoria-nox — launch is 2026-06-03. Try it before then
if you want to be the first to tell me what's wrong.
