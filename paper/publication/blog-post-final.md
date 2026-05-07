---
title: "FTS5 is 97.7% useless for natural language queries on production memory"
published: false
description: "I built a 3-layer hybrid memory system for 6 AI agents. Here's what 4 months of production, two catastrophic incidents, and an eval harness taught me about why keyword search is not enough — and why discipline matters more than algorithms."
tags: ["ai", "sqlite", "rag", "agentmemory"]
canonical_url:
cover_image:
---

# FTS5 is 97.7% useless for natural language queries on production memory

*Or: how two production incidents rewrote a schema, and why the incident log is now a first-class architectural input.*

---

It was 22:03 on April 25, 2026. A scheduled end-of-day cron job ran `nox-mem reindex` without a dry-run flag. No error. No alert. No indication that anything was wrong.

183 entities lost their `section`, `retention`, and `section_boost` fields. Months of carefully structured context — lessons from outages, architectural decisions, team-specific retention rules — flattened into generic chunks indistinguishable from any other document.

The database obeyed. That was the problem.

I sat there watching the health endpoint confirm what the logs would never tell me: `/api/health.sectionDistribution.compiled` went from 183 to 0. The system had no concept of "this kind of change is dangerous." It had no memory of why those fields existed in the first place.

That night I understood something that hadn't clicked in four months of building: **agent memory is not a retrieval problem. It's an operational discipline problem.**

This post is about what I built, what broke it, and why the three ideas that came out of those failures don't exist anywhere else in the literature.

---

## Why I built this at all

Four months ago, I had six AI agents running in production: Atlas, Boris, Cipher, Forge, Lex, and Nox. Each specialized. Each isolated. Each rediscovering context the others had already learned.

Forge would learn something about a deployment quirk. Atlas would ask the same question three weeks later. Nox would document an incident. Boris would have no idea it happened. Every conversation started from scratch in ways that had real costs — not just frustrating UX, but wrong decisions made without institutional memory.

I looked at the existing solutions. LangChain Memory is key-value with session_id. MemGPT (now Letta) does per-agent isolated state with OS-inspired paging. Mem0 partitions by user_id with LLM-edited self-improving memories. All reasonable designs for their intended use cases. None of them ask a question I couldn't stop thinking about:

*Did this lesson cost a production outage or was it a footnote?*

Because those should be ranked differently. A hard-won lesson from a 1am incident that took down a service for two hours should surface more readily than a documentation update from yesterday about a minor config option. Human memory works this way. Our systems don't.

So I built something. Four days to a working prototype, four months to 64,180+ chunks in production, five OpenClaw platform upgrades survived, two incidents that rewrote the schema, and an eval harness that makes silent regression structurally impossible.

---

## The architecture (briefly)

Three-layer hybrid retrieval over SQLite:

1. **FTS5 (BM25)** — fast lexical pass, eliminates obvious misses
2. **Gemini embeddings (3072d)** — semantic understanding for natural language queries
3. **RRF fusion (k=60)** — Reciprocal Rank Fusion merges both ranked lists

Plus an LLM-extracted Knowledge Graph with 7 closed-enum edge types (`depends_on`, `replaces`, `extends`, `mentions`, etc.) backed by a 24-entry defensive normalization map covering PT-BR + EN aliases, 402 entities, 544 relations. Salience scoring. Section-aware chunk ingestion. And a production eval harness with 50 curated golden queries.

The hybrid layer is not optional. Here's the measurement that made that concrete.

---

## The 97.7% finding

A few months in, I wanted to cut costs. Gemini embeddings aren't free. What if I disabled semantic search and fell back to FTS5-only for a while?

I had an eval harness. I ran it.

| Approach | nDCG@10 |
|---|---|
| FTS5 vanilla (BM25 only) | 0.0000 |
| nox-mem hybrid (FTS + Gemini + RRF) | 0.5831 |

*(n=60 queries R01c-v1.1 post-cure, 3-run mean ± std: Hybrid 0.5831 ± 0.0046, FTS 0.0000 ± 0.0000 — after 3 independent runs of the n=60 internally-curated golden query set, E13/E05b held off)*

**Exactly zero.** Not near-zero. Not somewhat degraded. On the post-cure n=60 corpus FTS5 returns *no* useful results for natural language operational queries — 0.0000 is the structural floor, not a tunable parameter.

This is not a bug in my FTS5 implementation. It's a structural property: FTS5 uses AND-strict tokenized matching. A query like `"why does the reindex command lose section data"` doesn't match any document that contains the answer, because the answer is spread across technical terms that appear in none of those exact tokens together. The semantic layer isn't a "nice to have" for my use case — it's load-bearing.

The gap: 100% relative loss in nDCG@10 (58.3 pp absolute — FTS returns zero, hybrid is the entire signal). The experiment took 20 minutes to run. The cost savings plan was abandoned in 25.

Three-run validation (runs #10/#11/#12): std=0.0004 for hybrid (0.08% relative variance) — the result is operationally deterministic. The result is stable.

---

## Three ideas no one else had

### 1. Pain-weighted salience

Most retrieval systems weight by recency and term frequency. Some add importance signals like PageRank or mention counts. Here's what none of them do: **ask how much an experience cost.**

The salience formula:

```typescript
function computeSalience(chunk: Chunk): number {
  const recency = Math.exp(-daysSince(chunk.last_seen) / DECAY_HALF_LIFE);
  const pain    = chunk.pain ?? 0.2;  // 0.1 trivial → 1.0 prod-outage
  const importance = mentionCountNorm(chunk);
  return recency * pain * importance;
}
```

`pain` is a field on every chunk, ranging from 0.1 (trivial note) to 1.0 (production outage). It's set manually in entity files with a simple annotation. When a chunk is created from an incident post-mortem, it gets a high pain score. When it's a minor config note, it gets the default 0.2.

The result: a lesson from a prod-outage six months ago outranks documentation updated yesterday on a minor topic. Not because it's newer. Because it cost more.

GraphRAG, Mem0, A-MEM, HiRAG, and Cognee all model structure and recency. I checked — none of them ask "how much did this cost?" Zero coverage in the literature for pain as a retrieval signal in agent memory systems.

The obvious objection: pain annotation is manual. Yes. That's a real limitation, documented honestly. For an operational system with a small number of agents under one operator, the annotation overhead is low and the payoff in retrieval quality is high. It's not a claim about automatic pain inference — it's a claim that the dimension itself is worth having.

### 2. Shadow discipline — ranking changes need seven days of evidence

After the April 25 incident, I didn't just fix the bug. I asked: what systemic property would have caught this before it reached production?

The answer wasn't better testing. It was a constraint: **any change that affects ranking must run in shadow mode for at least seven days before activation.**

Here's how shadow mode works:

```typescript
// Every ranking-affecting feature checks this env var:
const mode = process.env.NOX_SALIENCE_MODE ?? 'shadow';

if (mode === 'active') {
  results = applySalienceBoost(results);
} else {
  // Shadow: compute the boost, log the delta, don't mutate ranking
  const shadow = applySalienceBoost([...results]);
  logShadowDelta(results, shadow, query, 'salience');
}
```

It's enforced via:
- Environment variable that defaults to `shadow` (you have to explicitly set `active`)
- A cron job that checks the health endpoint and alerts if shadow telemetry is missing
- The `/api/health` endpoint that exposes shadow vs active status to any observer

This is not a "best practice we document and hope people follow." It's a structural constraint. You cannot accidentally activate a ranking change — you have to explicitly flip the environment variable, and the health endpoint will tell you whether you have enough data to justify that.

The salience activation (Phase 1.7b-b) ran seven days of shadow telemetry: 191 promote candidates, 16,608 review-needed, 45,743 archive candidates. Only after analyzing that distribution did it activate.

The counterfactual: the April 25 incident was exactly the kind of silent regression shadow mode would have caught. The reindex changed ranking behavior with no validation period. Shadow discipline, had it been in place for the reindex operation, would have shown the distribution shift in the telemetry before anything was permanently modified.

I've read a lot of papers on agent memory. Shadow discipline as an architectural constraint — not a suggestion, not a deployment pattern, a codified rule with automation backing it — is nowhere in the literature.

### 3. Shared-canonical multi-agent — one corpus, six agents, zero federation

The standard approaches to multi-agent memory:

- **MemGPT/Letta**: each agent has its own isolated state. Cross-agent knowledge requires explicit handoff.
- **Mem0**: user_id partitioning. Designed for B2C isolation where agents serve different users.

My six agents read from the **same canonical `chunks` table**. No synchronization. No merge. No federation overhead. Agent scoping happens via `source_file` prefixes (`agents/forge/...`, `agents/atlas/...`, `shared/...`) and SQL filtering at query time.

```sql
-- Cross-agent search: what does Forge know that's relevant to Atlas's query?
SELECT c.id, c.chunk_text, c.pain, c.source_file
FROM chunks c
WHERE (source_file LIKE 'agents/forge/%' OR source_file LIKE 'shared/%')
  AND c.id IN (
    SELECT chunk_id FROM vec_chunk_map
    ORDER BY vec_distance_L2(embedding, ?) LIMIT 20
  )
ORDER BY (c.mention_count * (c.pain ?? 0.2)) DESC
LIMIT 10;
```

When Forge learns something about a deployment pattern, Atlas retrieves it directly on the next relevant query. Not because anyone synchronized — because there was never a separation to begin with.

The trade-off is real and I document it honestly: this design assumes a trusted context. All six agents serve the same operator. For a SaaS product with user isolation requirements, this design is wrong. The shared-canonical approach works because the trust boundary is the operator, not the agent.

The practical result: 1GB SQLite serving 6 agents, zero federation overhead, cross-agent intelligence by default.

---

## The numbers that destroy doubt

**Hybrid vs FTS — the core finding:**

| Approach | nDCG@10 | Δ vs hybrid |
|---|---|---|
| FTS5 vanilla (BM25) | 0.0000 | −58.3 pp |
| nox-mem hybrid (FTS + Gemini + RRF) | 0.5831 | baseline |

*(n=60 R01c-v1.1 post-cure, 3-run mean ± std — gap relativo 100%, FTS é exatamente zero)*

**Edge typing precision — before and after:**

KG extraction with an optional type field and a naive prompt correctly classified only **14%** of relation types — 86% fell through to `unknown`. After a defensive normalization map in code (24 PT-BR + EN input aliases collapsing to 7 closed-enum reasons) plus a revised prompt (validated on n=100): **classification rate 56%, unknown rate 44%**. **4× improvement in classification coverage** on blast-radius queries — knowing *what kind of relationship* exists, not just that a relationship exists.

```bash
$ nox-mem impact "reindex"
## impact: "reindex" [operation, 89 mentions]
Total neighbors: 23 | Blast radius score: 4821.3 | Duration: 1ms

### depends_on (8, priority=5)
   ← [operation] reindex → [schema] section
   ← [operation] reindex → [schema] retention_days
   → [config] NOX_ALLOW_NO_SNAPSHOT env override
```

**Feature parity against alternatives:**

| System | KG native | Hybrid retrieval | Eval harness | Multi-agent | Shadow discipline | Score |
|---|---|---|---|---|---|---|
| **nox-mem** | closed-enum 7 reasons (24-entry map) | FTS5+Gemini+RRF | nDCG/MRR/Recall | shared canonical | enforced ≥7d | **5/5** |
| GraphRAG | + community detection | via KG queries | none | none | none | 1.5/5 |
| MemGPT/Letta | none | embedding-first | none | per-agent | none | 1.5/5 |
| Mem0 | optional v2 | vector-only | LOCOMO only | user_id partition | none | 1.5/5 |
| HiRAG | hierarchical | multi-level | task-specific | none | none | 2.5/5 |
| Cognee | ECL pipeline | hybrid | ad-hoc | optional | none | 3.0/5 |

The closest competitor (Cognee) covers 3 of 5 dimensions. No system in this comparison has shadow discipline as an architectural constraint.

**Production latency on real data:**

- p95 search: < 1 second on 64,180+ chunks
- Vector coverage: 99.97%
- Schema migrations without downtime: 12 versions over 4 months

Not emulation. Not a benchmark environment. A live system that has survived five platform upgrades and two data-loss incidents.

**Strong baselines (in execution):** BM25 via Pyserini, BGE-M3 dense retrieval, and E5-mistral-7b-instruct on BEIR-COVID and StackExchange are running in parallel. Pre-registered hypothesis: hybrid maintains ≥10% nDCG advantage over BGE-M3 dense on operational corpus. Full results in the arXiv paper.

---

## What I'm not claiming

HN will ask, so I'll say it here first:

I'm not claiming a new ML technique. There's no fine-tuning, no novel encoder, no GNN.

I'm not claiming SOTA in the academic sense. The strong baseline comparisons (BGE-M3, E5-mistral) are in execution, not yet in the paper.

The pain dimension has been validated on queries from my own corpus. The sample is real and in production, but it's one operator's operational memory. Pain annotation viability on public corpora is an open question I document honestly.

The shared-canonical multi-agent design works for trusted contexts. It would be a security mistake in a multi-tenant SaaS.

**What I am claiming:**

- Hybrid retrieval is structurally load-bearing for natural language operational queries. The 100% relative gap (58.3 pp absolute, n=60 R01c-v1.1 3-run mean — FTS5 returns exactly zero) is a measurement, not an opinion.
- Shadow discipline prevents silent regression. The April 25 incident is a documented case study. The counterfactual is explicit.
- Shared-canonical multi-agent works for the stated trust model and has been in production for four months.
- An eval harness with curated queries makes silent regression structurally impossible — vibe-checking doesn't.

---

## Why the incidents are in the schema

The April 25 reindex incident gave me shadow discipline and the `section` + `retention_days` fields in the schema. A May 1 incident where a `sed -i` command ran on SQLite binary files corrupted 1GB of data across nine files. That gave me a hard rule — codified as a system constraint, not a documented lesson — that file-modifying operations filter by extension before running.

The pattern: every catastrophic failure became a structural property of the system. Not a post-mortem document that decays. Not a team norm that new members have to learn. A constraint that the code enforces automatically.

This is the part that doesn't appear in papers about agent memory. The papers talk about architecture at the moment of design. The system I built was shaped by what broke.

The incidents are in the incident log (`docs/INCIDENTS.md`). The incident log informed the schema. The schema is in the paper. The paper explains why the schema looks the way it does.

That's the feedback loop no benchmark captures.

---

## Where to find it

- **arXiv preprint** (*The Pain Diary and Shadow Discipline: A Memory System That Learns from Its Own Incidents*): publishing 2026-05-19 — link in bio when live
- **GitHub**: [github.com/totobusnello/memoria-nox](https://github.com/totobusnello/memoria-nox) (MIT)
- **This paper's companion eval harness**: 50 curated queries, 8 categories, 12% negative cases, nDCG/MRR/Recall metrics — all in the repo

If you're building agent memory and have queries from a domain I haven't covered, I'd genuinely like them as held-out test data. Open an issue or reach out directly.

The system runs on one developer's operational corpus. It gets more useful as the query distribution grows.

---

## The closing I keep coming back to

Built solo by a developer in São Paulo. Four months in production. Zero funding. Two catastrophic incidents that rewrote the schema rather than breaking the project.

*The incidents are in the log. The log is in the schema. The schema is in the paper.*

That's the architecture. Not just of the system — of the methodology.
