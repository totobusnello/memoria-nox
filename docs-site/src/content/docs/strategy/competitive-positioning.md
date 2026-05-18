---
title: Competitive Positioning
description: Six Gaps analysis versus memanto, agentmemory, and gbrain.
sidebar:
  order: 1
---

Full source: [`docs/COMPETITIVE-POSITIONING.md`](https://github.com/totobusnello/memoria-nox/blob/main/docs/COMPETITIVE-POSITIONING.md)

## The trade you should not have to make

Most agent memory systems force a binary choice:

- **Vendor SaaS** (memanto, mem0): convenient, managed, fast to set up — but your data lives in their cloud, vendor lock-in is total, and pricing scales with volume.
- **Self-hosted primitives** (agentmemory, basic vector DBs): free, but retrieval quality is poor — no hybrid search, no knowledge graph, no shadow discipline.

**memoria-nox refuses the trade.** Self-hosted with retrieval quality that competes with managed services.

## Six Gaps matrix

| Gap | memanto | agentmemory | gbrain | memoria-nox |
|---|---|---|---|---|
| 1. Data portability | Closed (vendor) | SQLite ✓ | Proprietary | SQLite single-file ✓✓ |
| 2. Provider lock-in | Managed only | OpenAI only | Managed only | Gemini/OpenAI/local swap ✓✓ |
| 3. Retrieval quality | Unknown (private) | BM25 only | Unknown | FTS5 + vec + RRF +1.92pp ✓✓ |
| 4. Shadow discipline | None | None | None | 7-day shadow mode ✓✓ |
| 5. Knowledge graph | Planned | None | Partial | 15K entities / 21K relations ✓✓ |
| 6. Transparency | Closed | Open | Closed | Open source + paper ✓✓ |

## Autonomy moat

The autonomy moat is not just portability. It is the combination of:
1. **Single-file store** — copy the file, copy the memory
2. **Provider swap** — switch embedding providers without migrating data
3. **Open retrieval** — every score is auditable from SQL up
4. **Shadow discipline** — no ranking regression ships without evidence

Competitors can copy individual features. The moat is the combination.

## GTM Phase 2 gate

The hero positioning flip (GTM Phase 2) is gated behind the **Q4 COMPARISON** win: standardized benchmarks (LoCoMo, LongMemEval) must confirm retrieval superiority over the competition with public, reproducible numbers.

Until that gate opens, the positioning remains conservative. See [ROADMAP.md](https://github.com/totobusnello/memoria-nox/blob/main/docs/ROADMAP.md) for gate criteria.
