# nox-mem — Concrete Agent Memory Patterns

> If you landed from the README and thought _"interesting, but how would I actually use this?"_ — this doc is for you.

Ten patterns below. Each follows the same structure: **scenario → ingestion → search → why it works**. Code snippets are CLI/curl — no Python required to follow along. Set up first via [QUICKSTART.md](QUICKSTART.md).

Jump to any pattern:

| # | Pattern | Sweet spot |
|---|---|---|
| 1 | [Conversational agent with long-term memory](#1-conversational-agent-with-long-term-memory) | Customer support, chat assistants |
| 2 | [Personal knowledge assistant (second brain)](#2-personal-knowledge-assistant-second-brain) | Researchers, writers, note-takers |
| 3 | [Code-aware agent with architecture context](#3-code-aware-agent-with-architecture-context) | AI pair programmers, PR reviewers |
| 4 | [Multi-agent shared memory](#4-multi-agent-shared-memory) | Research swarms, parallelized agents |
| 5 | [Decision audit trail](#5-decision-audit-trail) | Compliance, post-mortems, governance |
| 6 | [Project-aware standup helper](#6-project-aware-standup-helper) | Engineering teams, solo builders |
| 7 | [Customer success agent](#7-customer-success-agent) | SaaS support, account management |
| 8 | [Research literature manager](#8-research-literature-manager) | Academic research, competitive intel |
| 9 | [Personal CRM](#9-personal-crm) | Founders, account execs, advisors |
| 10 | [Game / simulation agent memory](#10-game--simulation-agent-memory) | Game masters, interactive fiction |

---

## 1. Conversational agent with long-term memory

**Scenario.** A customer-support agent serves the same user across dozens of sessions spanning weeks. Without persistent memory, every session starts blind: the agent re-asks for context the user already gave, misses patterns, and loses trust.

### Ingestion

After each conversation turn, append to the user's memory file and ingest:

```bash
# Each turn is a markdown file: user_id + timestamp + content
nox-mem ingest \
  --type=conversation \
  --source="support-chat" \
  conversations/user_abc123/2026-05-21T14-32.md
```

Or via HTTP if your agent runtime speaks REST:

```bash
curl -X POST http://localhost:18802/api/ingest \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "User reported checkout fails with error E_PAYMENT_TIMEOUT on plan Pro.",
    "source_file": "support/user_abc123/2026-05-21.md",
    "type": "conversation",
    "pain": 0.7
  }'
```

`pain: 0.7` flags this as a high-severity complaint — it will score higher in future retrievals.

### Search (session start)

When a new session opens, pull the 5 most relevant past chunks before the agent replies:

```bash
curl 'http://localhost:18802/api/search?q=checkout+payment+error&limit=5&source_prefix=support/user_abc123'
```

Your agent uses the returned snippets as context window prefix. The user never re-explains their problem.

### Why it works

- **BM25** catches exact matches: account numbers, error codes (`E_PAYMENT_TIMEOUT`), plan names (`Pro`)
- **Gemini semantic** catches intent: "I'm frustrated" ≈ "this is unacceptable" ≈ "still broken"
- **Pain-weighted scoring** surfaces the angry/critical moments first — the agent knows what hurt before reading 50 turns

---

## 2. Personal knowledge assistant (second brain)

**Scenario.** You write markdown notes constantly — meetings, ideas, reading notes, decisions. Six months later you ask "what did I learn about X?" and can't find it in a folder tree.

### Ingestion (nightly cron)

```bash
# Entity files get section-aware chunking (compiled / timeline / frontmatter sections)
nox-mem ingest-entity ~/notes/entities/*.md

# Plain markdown notes ingest normally
nox-mem ingest ~/notes/daily/*.md ~/notes/reading/*.md

# Or point at a directory and let nox-mem route automatically
nox-mem ingest ~/notes
```

Add to cron for nightly runs:

```cron
0 2 * * * set -a; source ~/.env; set +a && nox-mem ingest ~/notes >> ~/logs/nox-ingest.log 2>&1
```

### Search

```bash
# Natural language queries work — hybrid handles both keyword and semantic
nox-mem search "what did I learn about RAG retrieval tradeoffs?"
nox-mem search "decisions I made about database choice"
nox-mem search "meeting notes about investor X"
```

### Entity file format

For people, projects, concepts you want rich tracking, use entity files (`memory/entities/<type>/<slug>.md`):

```markdown
---
name: rag-retrieval-tradeoffs
type: concept
tags: [retrieval, ai, architecture]
---

## compiled
Dense-only retrieval misses keyword queries. BM25 alone misses paraphrase.
Hybrid (BM25 + dense + RRF) consistently outperforms either alone in ablation.
Latency cost: ~800ms for embedding call.

## timeline
- 2026-05-10: Read LightRAG paper, confirmed hybrid hypothesis
- 2026-05-15: Ran ablation, Gemini dense was full driver on entity-eval
```

Entity files produce N+2 chunks with `section_boost` — compiled sections rank higher than timeline events, so the most distilled knowledge surfaces first.

---

## 3. Code-aware agent with architecture context

**Scenario.** An AI coding agent suggests replacing a library. It doesn't know you tried that library two years ago, it broke production, and you explicitly decided never again. Without memory, the agent confidently repeats a mistake.

### Ingestion

```bash
# Ingest your architecture docs and decision files
nox-mem ingest docs/ARCHITECTURE.md docs/DECISIONS.md docs/INCIDENTS.md

# Ingest key file headers (extract via awk or a preprocess step)
nox-mem ingest src/lib/*.md  # companion docs if you keep them

# Tag high-pain incidents explicitly
nox-mem ingest docs/INCIDENTS.md --type=lesson --pain=0.9
```

### Search (before agent responds)

Your agent wrapper calls this before generating any suggestion:

```bash
# Agent is about to suggest changing the DB driver — check memory first
nox-mem search "why did we choose better-sqlite3 over alternatives?"
nox-mem search "incidents with database layer"
nox-mem search "decisions we will not revisit"
```

Via MCP (if your agent framework supports MCP tools):

```json
{
  "tool": "nox_mem_search",
  "arguments": {
    "query": "why did we reject library X",
    "limit": 5,
    "type_filter": ["decision", "lesson", "incident"]
  }
}
```

### Why it works

Pain-weighted scoring puts "we tried X, it crashed prod at 2am, switched to Y" at the top. The agent sees the lesson before suggesting the rollback.

---

## 4. Multi-agent shared memory

**Scenario.** Three agents work in parallel on a research task — one scans papers, one interviews subject matter experts, one writes the synthesis. Without shared memory, they duplicate work and contradict each other.

### Pattern

Each agent tags its outputs with `agent_id` before ingesting:

```bash
# Agent A — literature scanner
nox-mem ingest outputs/agent-a/papers-summary.md \
  --type=research \
  --source="agent-a/papers"

# Agent B — interview notes
nox-mem ingest outputs/agent-b/expert-interviews.md \
  --type=research \
  --source="agent-b/interviews"
```

Before each agent starts a new sub-task, it queries what others have found:

```bash
# Agent C (synthesis) — check before writing section on topic X
curl 'http://localhost:18802/api/search?q=neural+reranker+cross-encoder&limit=10'
```

### Cross-KG for entity overlap

When agents work on related domains, the KG layer reveals shared concepts:

```bash
# Find all entities connected to "retrieval"
curl 'http://localhost:18802/api/kg?entity=retrieval&depth=2'

# Cross-search across multiple topics
curl -X POST http://localhost:18802/api/cross-kg \
  -H 'Content-Type: application/json' \
  -d '{"entities": ["BM25", "dense-retrieval", "RRF"], "depth": 2}'
```

Agent B found a paper about RRF. Agent C's cross-KG call surfaces that finding automatically — no explicit handoff message required.

### Two-agent dialog example

```
Agent-A ingest → "RRF fusion with k=60 consistently wins on LongMemEval (source: paper §3.2)"
Agent-B query  → search "RRF fusion performance" → returns Agent-A's chunk
Agent-B now knows → skips re-running the same experiment
```

---

## 5. Decision audit trail

**Scenario.** A compliance-sensitive workflow requires every AI-generated decision to be traceable: what context informed it, when it was made, and what severity it carried. Post-incident, someone must be able to reconstruct the reasoning chain.

### Ingestion

```bash
# Each decision is a chunk with explicit type + pain score
nox-mem ingest decisions/2026-05-21-pricing-model.md \
  --type=decision \
  --pain=0.8

# Lower-stakes operational decisions
nox-mem ingest decisions/2026-05-21-deploy-order.md \
  --type=decision \
  --pain=0.3
```

`type=decision` gets 365-day retention (vs 90-day default). High-pain decisions surface first in audits.

### Post-incident search

```bash
# Audit: what did we decide about pricing before the contract dispute?
nox-mem search "decisions about pricing model before 2026-05-01"

# Incident review: what led to the deploy failure?
nox-mem search "decisions about deploy order auth service"
```

### Why the ops_audit table matters

Every destructive operation (reindex, consolidate, crystallize) is wrapped in `withOpAudit()` — an append-only audit table with status enum validation via DB triggers. Rows in terminal states (`success`, `failed`, `crashed`) cannot be modified. The memory system audits itself.

---

## 6. Project-aware standup helper

**Scenario.** An AI agent drafts your daily standup by recalling what you actually did — commits, meeting decisions, blockers noted — rather than asking you to remember.

### Ingestion (nightly / post-commit hook)

```bash
# Ingest last 24h git log as a chunk
git log --since="24 hours ago" --oneline --no-walk=sorted > /tmp/git-log.md
nox-mem ingest /tmp/git-log.md --type=daily --pain=0.2

# Meeting notes from today
nox-mem ingest meetings/2026-05-21-*.md --type=daily
```

### Morning query (standup generation)

```bash
# The agent queries yesterday's activity
curl 'http://localhost:18802/api/search?q=what+did+I+work+on+yesterday&limit=10&type=daily'

# Or via /api/answer for a grounded natural-language response
curl -X POST http://localhost:18802/api/answer \
  -H 'Content-Type: application/json' \
  -d '{"query": "What did I accomplish yesterday and what blockers came up?"}'
```

Sample output from `/api/answer`:

```
Yesterday: Shipped PR #182 (Hard Mutex), ran G10 ablation (+0.79% nDCG),
investigated ops_audit timestamp chaos. Blocker: VPS IP swap caused
healthcheck false positives — patched via PR #186.
```

---

## 7. Customer success agent

**Scenario.** A SaaS support agent opens a new ticket. The customer is enterprise tier, has had three escalations in 90 days, and is currently in an upsell conversation. That context must be available before the agent types a single word.

### Ingestion

```bash
# Emails, chat transcripts, product events all go in
nox-mem ingest crm/customers/acme-corp/emails/*.md --type=conversation --pain=0.5
nox-mem ingest crm/customers/acme-corp/escalations/*.md --type=incident --pain=0.9
nox-mem ingest crm/customers/acme-corp/product-events.md --type=daily --pain=0.1
```

### Ticket open — agent context load

```bash
# Pull the 20 most relevant chunks for this customer
curl 'http://localhost:18802/api/search?q=acme+corp+billing+escalation&limit=20&source_prefix=crm/customers/acme-corp'
```

### Why pain-weighted helps here

The angry renewal email (`pain=0.9`) surfaces before routine product pings (`pain=0.1`). The agent leads with empathy for the known frustration, not a generic greeting.

---

## 8. Research literature manager

**Scenario.** A researcher ingests 200 paper abstracts + their own reading notes. Later they ask domain questions, look for contradictions across papers, or find all papers that cited a specific technique.

### Ingestion pipeline

```bash
# Convert PDFs to markdown (markitdown or similar), then ingest
for pdf in papers/*.pdf; do
  markitdown "$pdf" > /tmp/paper.md
  nox-mem ingest /tmp/paper.md --type=research --source="papers/$(basename $pdf .pdf)"
done

# Own reading notes as entity files (richer chunking)
nox-mem ingest-entity notes/entities/concept/*.md
```

### Cross-paper queries

```bash
# Find all mentions of a technique across all ingested papers
nox-mem search "cross-encoder reranker performance"

# Ask a synthesized question — /api/answer returns grounded response with citations
curl -X POST http://localhost:18802/api/answer \
  -H 'Content-Type: application/json' \
  -d '{"query": "Which papers contradict each other on the value of BM25 for recall?"}'
```

### KG layer reveals connections

```bash
# See all entities (authors, techniques, datasets) connected to a concept
curl 'http://localhost:18802/api/kg?entity=retrieval-augmented-generation&depth=2'
```

The KG builds incrementally via `nox-mem kg-extract` (Gemini 2.5 Flash). After ingesting 50 papers, the entity graph links authors to techniques to datasets — connections you didn't explicitly annotate.

---

## 9. Personal CRM

**Scenario.** You meet 30 people a month at board meetings, investor dinners, portfolio reviews. Before a follow-up call, you want: last interaction summary, what you promised, their current role, and any shared context.

### Entity files for people

```markdown
# memory/entities/person/ana-lima.md
---
name: ana-lima
type: person
tags: [investor, LP, biotech]
---

## compiled
Ana Lima — Managing Partner at Vortex Ventures. Focus: Series B healthtech.
Met at Galapagos AI Committee 2026-03. Introduced by Renata. Interested in nox-mem for
portfolio company diagnostic memory layer.

## timeline
- 2026-03-15: First meeting, Galapagos committee. Exchanged decks.
- 2026-04-02: Follow-up email. She asked about multi-tenant roadmap.
- 2026-05-10: Dinner ESPM. Committed to intro with Dr. Ferreira at Einstein.
```

### Ingestion

```bash
nox-mem ingest-entity memory/entities/person/*.md
```

### Pre-meeting recall

```bash
# 10 minutes before the call
nox-mem search "Ana Lima last interaction commitments"

# Or via /api/answer for natural language
curl -X POST http://localhost:18802/api/answer \
  -H 'Content-Type: application/json' \
  -d '{"query": "What did I promise Ana Lima and when did we last speak?"}'
```

---

## 10. Game / simulation agent memory

**Scenario.** A tabletop RPG game master assistant runs a 20-session campaign. Each session adds plot events, NPC actions, character developments. The GM assistant must recall what happened in session 5 to avoid contradictions in session 20.

### Ingestion

```bash
# Session notes after each game
nox-mem ingest sessions/session-05-notes.md --type=daily --pain=0.3

# Player character deaths score much higher — memorable, plot-relevant
nox-mem ingest sessions/session-08-pc-death-thorin.md --type=incident --pain=0.9

# NPC entity files for recurring characters
nox-mem ingest-entity entities/npc/lord-castellan-voss.md
```

### GM assistant queries

```bash
# Before session 12 — what happened with the artifact plotline?
nox-mem search "artifact Thornhelm session history"

# What were the consequences of the PC death?
nox-mem search "Thorin death consequences party morale"

# Full session summary via /api/answer
curl -X POST http://localhost:18802/api/answer \
  -H 'Content-Type: application/json' \
  -d '{"query": "Summarize all interactions between the party and Lord Castellan Voss."}'
```

Pain-weighted scoring means the PC death (pain=0.9) surfaces before minor encounters (pain=0.2), keeping plot-critical moments at the top of the GM's context.

---

## What nox-mem is NOT a fit for

Honest limitations — if your use case fits one of these, a different tool will serve you better.

| Scenario | Why nox-mem isn't ideal | Better fit |
|---|---|---|
| **Real-time streaming** (sub-100ms) | Hybrid search latency is p50=940ms, p95=2.3s | Redis, in-memory vector store |
| **>500k chunks** | Sweet spot is 10k–200k; large-corpus is Lab Q1 roadmap | pgvector, Qdrant, Weaviate |
| **Multi-tenant SaaS** | v1.0 is single-tenant by design; multi-tenant is on the product roadmap | Cloud vector DBs with namespace isolation |
| **Heavy structured / tabular data** | nox-mem is document-chunk oriented, not row-oriented | Postgres + pgvector |
| **HIPAA / SOC2 regulated data** | No certifications yet; single-machine SQLite | Managed services with compliance certs |
| **Shared write from 50+ concurrent agents** | SQLite WAL handles moderate concurrency; heavy parallel writes contend | Postgres |

---

## Getting started

1. **Install + first search:** [QUICKSTART.md](QUICKSTART.md) — 5 minutes, zero prior context needed
2. **Real eval examples:** [`eval/q4-comparison/`](../eval/q4-comparison/) — n=100 golden set, all query types
3. **FAQ:** [FAQ.md](FAQ.md) — "why SQLite?", "which embedding providers?", "how is pain_score set?"
4. **Architecture internals:** [ARCHITECTURE.md](ARCHITECTURE.md) — schema, search pipeline, KG layer

Have a use case not listed here? [Open an issue](https://github.com/totobusnello/memoria-nox/issues/new) — patterns that get traction get promoted to dedicated guides.
