# Hacker News Submission Plan — NOX-Supermem

> **Submission window:** Tuesday or Wednesday, 09:00 ET (Brasília 10:00). HN frontpage decay = 2-3h, melhor pickup pra US tech crowd.
> **Submission target:** blog post URL (NOT arXiv — HN crowd prefers narrative blog) + arXiv link em first comment.

---

## Title variants (5 options — pick best after blog views first 24h)

### Variants ranked by predicted CTR (HN audience)

1. **"FTS5 is 97.7% useless for natural language queries on production memory"** ⭐ TOP PICK
   - Counterintuitive (HN loves)
   - Specific number (HN loves)
   - Targets misconception devs hold
   - Short (8 words)

2. "Show HN: NOX-Supermem – memory system for 6 AI agents (4 months production)"
   - Show HN tag = visibility boost
   - Multi-agent angle differentiates
   - Production duration = credibility signal
   - Long (15 words — okay limit)

3. "Pain-weighted salience: a missing dimension in agent memory systems"
   - Novel-claim angle
   - Targets paper readers
   - Risky if blog post is more about engineering than novel claim

4. "I tested 5 memory systems for AI agents in production. Here's what failed."
   - Comparison angle (HN loves)
   - "What failed" = honest, anti-hype
   - But: I haven't really tested 5 — only studied them. Honest disclosure needed.

5. "Why your RAG eval matters more than your embedding model"
   - Eval-first angle
   - Specific takeaway

**Recommended sequence:**
- Day 1: Submit Variant #1 (highest predicted CTR)
- If miss frontpage by hour 6 → repost with Variant #2 (Show HN)
- If frontpage hits → no repost, ride engagement

---

## First comment template (HN convention — author posts first)

```
Author here. Some context for HN crowd:

This is a personal project that grew into something useful. I'm running 7 AI
agents (Maestro + 5 specialized (= 6 working agents): code review, customer success, security,
legal, content, ops). Each loses context every conversation. Standard solutions
didn't fit:

- mem0: vector-only, no KG (I needed both)
- MemGPT: per-agent isolated state (I want cross-agent learning)
- LangChain Memory: too primitive for production
- GraphRAG: too summary-focused for operational queries

So I built something that combines: SQLite FTS5 + Gemini embeddings + RRF
fusion + LLM-extracted KG + closed-enum edge typing. Multi-agent share the
same chunks table (works for trusted contexts, NOT for SaaS multi-tenant).

Three things I'm genuinely uncertain about and would love HN feedback:

1. **Pain-weighted salience** (severity × recency × importance) — I think
   modeling incident pain as retrieval signal is novel, but happy to be
   pointed at prior work I missed.

2. **Shadow-mode discipline** (any ranking change must shadow ≥7d before
   activate) — feels obvious in hindsight but I haven't seen it codified
   in other memory systems.

3. **Shared-canonical multi-agent** — controversial, since most papers
   advocate isolation. My take: trust assumption is what matters, not the
   federation pattern.

Code: https://github.com/totobusnello/memoria-nox
arXiv preprint: [link when published]
Eval harness + 50 golden queries: in repo

Happy to answer questions, accept criticism, take query suggestions for
held-out evaluation. Thanks!
```

---

## Common HN objections + preemptive responses

### Objection: "This is just hybrid retrieval, not novel"
**Response (in comment):** "Agreed on hybrid retrieval — that part is industry standard since Pinecone Sparse-Dense. The novel parts are pain dimension in salience and enforced shadow discipline. Section §3 of the paper isolates these. Happy to be pointed at prior work for either."

### Objection: "n=50 is way too small for benchmark"
**Response:** "Agreed for academic benchmarks. We added BEIR-COVID (50 queries from independent curator) and StackExchange 10K subset for cross-corpus validation. See §5.3-§5.4 of paper. The 50 internal queries serve as primary because they reflect actual production use — generalization is shown via the other 2 corpora."

### Objection: "Why not use Voyage/OpenAI/etc embeddings?"
**Response:** "Honest answer: didn't measure. We used BGE-M3 as a proxy alternative provider in §5 — performance was within 8% of Gemini, suggesting provider is replaceable. Voyage trial would close this — it's a known gap (paper §1.5 Step 3)."

### Objection: "SQLite for production memory? Really?"
**Response:** "Yes, with sqlite-vec extension. 64K chunks, 1GB DB, 100% embedded, production for 4 months. Tradeoff: single-writer model (fine for personal multi-agent) vs PostgreSQL+pgvector for multi-tenant. Future P01 productization will move to Postgres."

### Objection: "Multi-agent without isolation is dangerous"
**Response:** "Agreed for multi-tenant SaaS. nox-mem assumes single user with N trusted agents (your own personal agents). For SaaS, look at mem0 paid tier or Letta Cloud."

---

## Cross-post strategy

| Channel | Time relative to HN | Content variant |
|---|---|---|
| **HN** | T+0 (Tuesday 09:00 ET) | Blog post URL |
| **Twitter/X** | T+0 (parallel post) | 1-line + chart screenshot + thread 5 tweets |
| **LinkedIn** | T+2h | Same content as HN comment, more business framing |
| **dev.to** | T-1day (blog must be live first) | Full blog post cross-post |
| **r/MachineLearning** | T+1day | If frontpage HN works, post to subreddit; otherwise skip |
| **r/LocalLLaMA** | T+1day | Different framing: focus on cost ($0 OpenClaw zero-cost backend angle) |

---

## Success metrics monitoring (first 48h)

| Metric | Conservador | Ambicioso | Action if hit |
|---|---|---|---|
| HN frontpage rank top 30 | ≥ rank 30 | ≥ rank 10 | Engage every comment first 6h |
| HN points after 1h | ≥ 5 | ≥ 30 | If <5 → consider relocate (rare) |
| HN comments after 4h | ≥ 10 | ≥ 50 | Respond to all critical objections |
| Blog views first 24h | ≥ 1k | ≥ 10k | Pin on dev.to feed |
| GitHub repo stars first 48h | ≥ 20 | ≥ 200 | Pin "good first issue" labels prep |
| arXiv paper downloads first week | ≥ 50 | ≥ 500 | Cross-post Twitter ML community |
| NOX-Supermem product inbound | ≥ 5 emails | ≥ 30 | Slack workflow ready pra triage |

---

## Risk mitigation

### Risk: HN crowd is hostile to "show HN" if too commercial
- Mitigation: title #1 (data-driven) NOT #2 (Show HN) for first attempt; keep blog post 90% engineering 10% product mention

### Risk: Reviewers find error in 97.7% claim
- Mitigation: paper §1.4 documents methodology limitations; absolute Δ (0.504 nDCG) is invariant to baseline

### Risk: Anti-LLM crowd dismisses entire approach
- Mitigation: emphasize SQLite + open-source + reproducibility; not just "I asked GPT to extract entities"

### Risk: Voyage/proprietary embedding crowd attacks Gemini choice
- Mitigation: BGE-M3 baseline shows interchangeable; Voyage explicitly addressed em §1.5
