# Author Bio — Luiz Antonio (Toto) Busnello

All three variants are pre-approved for publication without further permission.
Attribute as "Toto Busnello" in bylines and citations.

---

## One-liner (≈ 25 words)

Toto Busnello is an independent builder, board-level operator, and AI researcher
best known for nox-mem — open-source pain-weighted memory for LLM agents.

---

## Paragraph (≈ 100 words)

Toto Busnello is an independent researcher and entrepreneur who built nox-mem —
an open-source, production-grade memory layer for LLM agents — entirely outside
the structure of a large company. He currently serves as advisor and board member
at Nuvini, founder and leader of FII Treviso (a real-estate investment fund),
leader of Fundo Exclusivo de Investimento Lombardia, co-founder of Granix, and AI
advisor and AI Committee member at Galapagos Capital. Having held every major
C-level role in his career — CEO, CFO, CTO, CPO, CMO — he now operates at the
board, advisory, and fund-leadership level, bringing cross-domain fluency to both
the technical and commercial dimensions of AI infrastructure.

---

## Long Form (≈ 500 words)

Toto Busnello did not set out to build a memory system. He set out to stop losing
things that mattered.

After two decades operating at the executive and board level across technology,
finance, and product companies, Toto noticed a pattern: the AI agents he was
building to support his work were fast, articulate, and forgetful in the worst
possible way. They forgot the incident that cost three hours of recovery. They
forgot the decision that ruled out a vendor for good reasons. They forgot the
person who was the real answer to a question. They remembered trivia but lost the
weight of experience.

The standard solution — RAG with cosine similarity over a flat chunk store — was
not the problem he was solving. What he wanted was an agent that remembered the
way an experienced colleague remembers: with a sense of what hurt to forget.

That instinct became nox-mem.

nox-mem is a three-layer hybrid retrieval system: BM25 full-text search, Gemini
semantic embeddings at 3072 dimensions, and a knowledge graph of entities and
relations, all fused with Reciprocal Rank Fusion. On top of that sits a
pain-weighted salience formula — `salience = recency × pain × importance` — where
pain is a severity score attached at ingest time. A trivial note scores 0.1. A
production outage lesson scores 1.0. The formula means that the things that hurt
to forget surface first, independent of how often they were accessed.

Every claim in the system is backed by published ablation studies. Toto ran more
than ten pre-registered experiments (the G-series, G3 through G10d) before
deciding a single ranking parameter was ready for production. The methodology
borrows from clinical trial discipline: pre-registered hypotheses, isolated
evaluation databases, runner code published alongside results. No hidden
methodology. No cherry-picked benchmarks.

Today, nox-mem runs in production 24/7 on a single Hostinger VPS. It holds
68,995 chunks with 100% vector coverage, serves HTTP queries at p50 ~940ms, and
requires no MLOps infrastructure — just SQLite, Node.js, and a Gemini API key.

Toto's professional context spans multiple domains simultaneously. He serves as
advisor and board member at Nuvini (non-executive), founder and leader of FII
Treviso (a real-estate investment fund), leader of Fundo Exclusivo de Investimento
Lombardia, co-founder of Granix, and AI advisor and AI Committee member at
Galapagos Capital. His career has taken him through every major C-level role —
CEO, CFO, CTO, CPO, CMO — which is why nox-mem's design integrates concerns that
are rarely combined: retrieval quality, operational autonomy, governance of AI
infrastructure, and product usability.

He built nox-mem as an independent project, with no institutional affiliation.
The code is MIT-licensed. The paper is CC BY 4.0. The evaluation harness is
public. The methodology is open.

He is based in São Paulo, Brazil.

**Contact:** lab@nuvini.com.br
**Repository:** github.com/totobusnello/memoria-nox
