# nox-mem FAQ

Pre-launch FAQ for HN / Twitter / Reddit / Product Hunt (launch Wed 2026-06-03).

---

## §1 — What is this / who is it for

**Q: What problem does nox-mem solve?**

LLM agents forget everything between sessions. Existing solutions either force vendor lock-in, rely on vector-only retrieval (poor keyword recall), or treat all memories as equally important. nox-mem provides a persistent, locally-owned hybrid memory layer with pain-weighted salience — so agents remember what actually mattered, not just what was recent.

---

**Q: Who should use this?**

- Solo developers building personal agents or AI assistants who want full data ownership
- Small teams worried about vendor lock-in with hosted memory APIs
- Researchers who need transparent, reproducible benchmarks instead of black-box evals

Not targeting large-scale enterprise deployments (yet — see Roadmap).

---

**Q: Is this production-ready?**

Yes, for personal and small-team use. A reference VPS instance has run continuously since April 2026 with 68k+ chunks, serving a live AI assistant. No SLA; single-author project. If you need SLA guarantees, watch nox-supermem (separate commercial track in development).

---

**Q: What does "pain-weighted" mean?**

Each memory chunk carries a `pain` score (0.1 trivial → 1.0 production outage). Salience is computed as:

```
salience = recency × pain × importance
```

This means a critical incident from three weeks ago ranks higher than a trivial note from yesterday. The formula runs in shadow mode by default so you can observe its effect before activating it.

---

## §2 — Comparison with alternatives

**Q: How is this different from Mem0 / Zep / Letta?**

Three core differences: (1) **open methodology** — benchmarks are pre-registered and reproducible, not marketing claims; (2) **MIT licensed** with no hosted dependency; (3) **triple-stack retrieval** (BM25 + semantic + KG) vs. vector-only or single-strategy approaches. See `docs/COMPARISON.md` for per-feature breakdown.

---

**Q: Why not just use a vector DB?**

Vector-only search loses keyword precision. A query like "error code 403" returns semantically-similar results instead of the exact match. BM25 + vector + KG via Reciprocal Rank Fusion (k=60) consistently outperforms any single strategy on our eval set. See the paper §4 for ablation results.

---

**Q: Why SQLite and not Postgres / Pinecone?**

Single-file deployment, zero ops, works offline for the BM25 layer. SQLite + FTS5 + sqlite-vec (vector extension) gives you full hybrid search in one dependency-free file you can copy anywhere. Postgres adds network ops and a daemon; Pinecone adds vendor dependency. Tradeoff: vertical scale caps around a few million chunks.

---

**Q: Will this scale beyond X chunks?**

Current production instance has 68k chunks with sub-second p50 latency. Lab Q1 priority is benchmarking at 250k+ chunks. SQLite WAL mode + proper indexing should handle 500k+ comfortably; beyond that, Postgres migration is documented as a future path.

---

## §3 — Technical questions

**Q: Why Gemini embeddings (3072d)?**

Best quality/cost ratio available in 2026 for 3072-dimensional dense embeddings. The provider is configurable via `.env` — set `NOX_EMBEDDING_PROVIDER=openai` or point to a local Ollama instance. No code changes needed; the adapter pattern in `src/embeddings/` handles the swap.

---

**Q: Does this work offline?**

Partially. FTS5 BM25 keyword search works fully offline. Semantic search and KG extraction require an embedding API call. For fully local operation, configure Ollama as the embedding provider — quality will depend on your local model.

---

**Q: What's the latency?**

Measured on the live VPS instance (1 vCPU, 2GB RAM):

| Percentile | Latency |
|---|---|
| p50 | ~940 ms |
| p95 | ~2.3 s |
| p99 | ~2.5 s |

The dominant cost (~800ms) is the Gemini embedding API call. With a local embedding model, p50 should drop to ~100–200ms.

---

**Q: Can I use my own embedding model?**

Yes. See `src/embeddings/` — the adapter interface is minimal. Implement `embed(texts: string[]): Promise<number[][]>` and register the provider. Existing adapters cover Gemini and OpenAI; Ollama adapter is documented in the README.

---

**Q: Why MIT and not GPL / Apache?**

MIT is permissive enough for commercial adoption without forcing license propagation. Consistent with the majority of LLM tooling ecosystem (LangChain, LlamaIndex, etc.). Apache 2.0 would also be fine; MIT is simpler.

---

## §4 — Methodology / benchmarks

**Q: How were the benchmarks run?**

Identical corpus ingested into each system using native defaults. Queries drawn from two datasets (LongMemEval-style + entity eval). Metrics: nDCG@10 and MRR. Full methodology in `docs/COMPARISON.md`, paper §6, and `docs/Q4-COMPARISON-METHODOLOGY.md`. Eval runner is in `eval/q4-comparison/`.

---

**Q: Are the benchmarks rigged?**

No. Methodology was pre-registered before running (spec PR #218 merged before any results). All 6 query categories are reported including categories where nox-mem underperforms. Both datasets (in-distribution and cross-domain) are reported. We want this to be reproducible and falsifiable — that's the point.

---

**Q: Can I reproduce the benchmarks?**

Yes. `eval/q4-comparison/` contains the runner and per-system adapters. `docs/Q4-COMPARISON-METHODOLOGY.md` has the full setup guide (corpus preparation, ingestion, query execution, scoring). If you find a discrepancy, open an issue.

---

**Q: What if my use case differs from your eval?**

The eval set is a starting point, not a claim of universal superiority. We publish the runner so you can swap in your own query set. Different corpora and query distributions will produce different rankings — we encourage you to run it on your data.

---

## §5 — Project / sustainability

**Q: Is this a startup?**

No. Open-source side project, MIT licensed, no commercial monetization in this repo. A separate commercial product (nox-supermem) is in a separate repo and a separate track — this repo stays open regardless of what happens there.

---

**Q: Why are you giving this away?**

Autonomy is one of the three Q/A/P pillars. Lock-in is the problem we're solving, not creating. Publishing the full system with reproducible benchmarks is consistent with that commitment.

---

**Q: How do I contribute?**

See CONTRIBUTING.md. Bugs, features, adapters, and PRs are all welcome. Highest-value contributions right now: new embedding provider adapters, eval set additions, and scale testing reports (250k+ chunks).

---

**Q: Who's behind this?**

Luiz Antonio (Toto) Busnello — independent operator (advisor and board-level, not CTO of any company). Built nox-mem as a personal tool that grew into something worth publishing. See CITATION.cff for formal attribution.

---

## §6 — Common concerns

**Q: What about privacy? Does my data go to Google?**

Your data lives in a local SQLite file — nothing is sent to any cloud storage. The only external call is the embedding API (text content of chunks sent to Gemini). For fully private operation, use the Ollama embedding provider; zero data leaves your machine. Gemini API calls are subject to Google's data processing terms.

---

**Q: What about hallucinations?**

nox-mem is retrieval, not generation. It returns ranked chunks from your own data — it does not generate text. Hallucinations are a generation problem; pair nox-mem with whatever LLM you trust for generation. The retrieval layer stays factual by design.

---

**Q: What's the catch?**

Three honest ones: (1) Gemini API costs (~$0.0001/query at current rates, negligible at personal scale but non-zero); (2) single-author project, so support is best-effort with no SLA; (3) vertical scale caps in the hundreds-of-thousands range with SQLite. None of these are blockers for the target audience.

---

## §7 — Roadmap

**Q: What's next?**

Lab Q1 priorities: EverMemBench evaluation (closes benchmark gap with EverMind-AI), scale testing to 250k+ chunks, and neural reranker exploration (cross-encoder rerank typically adds +3–8% nDCG). Full roadmap in `docs/ROADMAP.md`.

---

**Q: Will you accept PRs?**

Yes. See CONTRIBUTING.md. Code review cadence is best-effort (solo project), but PRs are actively reviewed. Clean PRs with tests merge faster.

---

**Q: Production support?**

Best-effort, no SLA. For production SLA needs, watch nox-supermem — the separate commercial track currently in development. This repo will stay MIT open-source regardless.

---

*Last updated: 2026-05-21. Launch date: 2026-06-03.*
