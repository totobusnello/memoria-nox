# Honest cross-system framing — never silently fill competitor numbers

**Timeline:** PR #296 (2026-05-24) — Q4 comparison discovery: mem0 corpus-cap drives apparent nDCG superiority.

**Context:** nox-mem vs mem0 preliminary smoke numbers for Q4 COMPARISON gate (Phase 2). Toto's Q/A/P pivot gates Phase 2 on "≥+15% nDCG@10 threshold" vs competitors.

**Discovery (Saturday morning):** mem0's published benchmark numbers are 0.92+ nDCG@10. nox-mem v3.6 is 0.88 nDCG@10. Gap appears to favor mem0 by ~4.4%.

**But:** Deeper investigation revealed:
- mem0's corpus is **capped at 1k entities** (Pinecone free tier limit)
- nox-mem's corpus is **69.5k entities** (real Toto data, incremental ingestion)
- **Corpus-size concentration effect:** smaller corpus = tighter clustering → higher nDCG@10 naturally. Trade-off is **coverage** (what % of queries have *any* relevant doc).

**nox-mem vs mem0 trade-off matrix:**
| Metric | mem0 (1k) | nox-mem (69.5k) |
|---|---|---|
| nDCG@10 | 0.92+ | 0.88 |
| Coverage (≥1 relevant doc) | 45% (dense subset) | 87% (sparse full corpus) |
| Cold-start latency | 800ms | 1400ms (Gemini embed dominates) |
| Per-query cost | $0.001 | $0.008 (embed + RRF) |

**Honest framing rule:** When comparing systems with different corpus sizes or architectures:
1. **Disclose the trade-off explicitly.** "mem0 gets +4.4% nDCG@10 due to 1k-entity concentration. nox-mem trades concentration for coverage: 87% vs 45%."
2. **Never silently fill numbers.** Don't claim "nox-mem=0.92 on full corpus" without validation.
3. **Publish methodology.** Corpus source, evaluation harness, golden-set construction, inclusion/exclusion criteria.
4. **Benchmark both systems on same corpus.** Run mem0 on 69.5k entities (Pinecone premium tier). Compare apples-to-apples.

**Status:** PR #296 appended honest disclosure to Q4 report. Phase 2 gate logic updated: **both** nDCG@10 AND coverage must meet threshold. Prevents gaming via concentration.

**Implication for GTM:** nox-mem's **Autonomy pillar** (data yours, provider yours) justifies coverage+scale trade-off. Messaging: "Not fastest, not cheapest — yours, forever."

**Reference:** `[[q4-cross-system-fill]]`. Phase 2 gate decision pending post-Q4 run full (late May 2026).
