# Blog Post Draft — "I built a memory system for 6 AI agents. Here's what 4 months of production taught me."

> **Channel:** dev.to + Substack pessoal + cross-post LinkedIn
> **Length target:** ~2500 words / 12 min read
> **Tone:** story-driven, code-first, honest about limitations
> **Audience:** devs building RAG/agent systems, technical PMs evaluating memory tooling
> **Goal:** dev credibility + product credibility (NOX-Supermem P01) + arXiv paper distribution

---

## Title (5 variants — A/B test before HN submission)

1. **"FTS5 vs Hybrid retrieval: I measured a 97.7% gap on natural language queries"** (counterintuitive, data-driven)
2. "What 4 months of production memory taught me about agent systems" (story angle)
3. "I built a memory system for 6 AI agents. Here's the architecture." (engineering angle)
4. "Why your RAG system needs an eval harness (and 5 lessons from production)" (problem-first)
5. "Pain-weighted salience: a missing dimension in agent memory" (novel-claim angle)

**Pick:** #1 for HN (data-driven titles win on HN), #2 for blog/LinkedIn (story angle has higher engagement on those), #5 if pivoting toward academic crowd.

---

## Hook (first 3 paragraphs)

> Last month I tested an obvious-sounding hypothesis: "if I disable semantic embeddings and use only SQLite FTS5 keyword search, how much worse does my agent memory get?"
>
> The answer was uncomfortable: **97.7% loss in nDCG@10 on natural language queries**. FTS5 returned the right chunks for 1 out of 50 questions. The semantic layer wasn't a "nice to have" — it was load-bearing.
>
> This wasn't a benchmark paper. It was production engineering: a memory system I built over 4 months for a nerd entrepreneur running 7 specialized AI agents (code, infra, business, personal). And the experiment was forced — I needed to know if I could cut Gemini API costs by removing semantic embedding. The answer: no, I'd be cutting the system in half.
>
> This post explains: the architecture (3-layer hybrid + KG), three things I did differently than mem0/MemGPT/A-MEM, and what production taught me that no benchmark paper covers.

---

## Section structure (~2500 words total)

### 1. Why I built this (~300 words)
- 6 agents losing context every conversation
- Specialized roles (Maestro coordenador, Nox memory keeper, Forge code reviewer, Boris content, Atlas customer success, Cipher security, Lex legal)
- Existing solutions: mem0 too vector-only, MemGPT too per-agent isolated, LangChain Memory too primitive
- Decision: build minimum that works for me, ship in 4 days, iterate from there
- Today: 64K chunks 100% embedded, 4 months production, 5 OpenClaw upgrades survived

### 2. The architecture (~600 words)
- ASCII diagram (use the README one)
- 3-layer hybrid: FTS5 → Gemini embeddings → RRF
- Why each layer matters (the 97.7% experiment justifies semantic, RRF justifies fusion)
- LLM-extracted KG with closed-enum edge typing (depends_on / replaces / extends / mentions / etc)
- Multi-agent: shared canonical chunks table, NOT per-agent silos (controversial choice — explain)

### 3. Three things I did differently (~700 words) ⭐
**3.1 Pain-weighted salience formula**
- `salience = recency × pain × importance`
- Pain = severity bookmark from past incidents (0.1 trivial → 1.0 prod outage)
- Manual annotation in entity files: `<!-- pain: 0.8 -->`
- Why: queries about post-incident lessons get boosted automatically
- Code snippet (~10 lines)

**3.2 Shadow-mode discipline (enforced, not optional)**
- Codified rule: any change that touches ranking must shadow ≥7d antes activate
- Implementation: env vars + telemetry + cron daily Discord alert + automated GitHub Issue verdict
- Story: incident 2026-04-25 que causou regra (reindex sem dry-run quebrou 183 entities) → resposta foi codificar a regra, não memorizar a lição

**3.3 Shared-canonical multi-agent (not per-agent silos)**
- 6 agents share the same chunks table, distinguished by source_file prefix
- Cross-agent search/KG/insights via SQL join, not federation
- Trade-off: trust assumption (all agents same user — works for personal use, NOT for SaaS)

### 4. Eval harness — measuring before changing (~500 words)
- 50 curated golden queries (8 categories, 12% negative cases)
- nDCG@10 / MRR / Recall@10 / Precision@5
- 3-run mean ± std (system is operationally deterministic — std < 0.001 for FTS, 0.0004 for hybrid)
- Held-out 10 queries from naive-user perspective: zero hallucination on 5/5 negatives ⭐
- Why this matters: any feature change tests against same baseline → silent regression impossible

### 5. What production taught me (~300 words)
- 24 lessons accumulated em `MEMORY.md` (secrets em git, monkey-patch grep false positive, sed em SQLite corrompe binary, etc)
- Most insights aren't algorithmic — they're operational discipline
- Snippet de 3-4 lessons most universal (NOT project-specific)

### 6. What's next (~150 words)
- arXiv preprint (link)
- Productization NOX-Supermem (Hotmart Brasil, P01 elegível 2026-05-26)
- Open invitation: try it, file issues, suggest queries for held-out subset
- Repo link: https://github.com/totobusnello/memoria-nox

---

## Code snippets to include (4 max — keep brief)

### Snippet 1 — Salience formula
```typescript
function computeSalience(chunk: Chunk): number {
  const recency = Math.exp(-daysSince(chunk.last_seen) / DECAY_HALF_LIFE);
  const pain = chunk.pain ?? 0.2;        // default low if not annotated
  const importance = mention_count_norm(chunk);
  return recency * pain * importance;
}
```

### Snippet 2 — Shadow-mode toggle
```typescript
// All ranking-affecting features check this:
if (process.env.NOX_FOCUS_MODE === 'active') {
  results = applyFocusBoost(results, query);
} else {
  // shadow: log delta but don't mutate ranking
  logShadowDelta(results, query, 'focus');
}
```

### Snippet 3 — Multi-agent canonical query
```sql
-- All 6 agents query the same table, scoped by source_file:
SELECT id, chunk_text FROM chunks
WHERE source_file LIKE 'agents/forge/%' OR source_file LIKE 'shared/%'
ORDER BY salience DESC LIMIT 10;
```

### Snippet 4 — CLI demo (terminal screenshot via fenced code)
```bash
$ nox-mem impact "Forge"
## impact: "Forge" [agent, 1306 mentions]
Total neighbors: 54 | Blast radius score: 13251.4 | Duration: 1ms

### 🔴 depends_on (12, priority=5)
   ← [agent] Nox (1366 m)
   → [project] nox-mem (1269 m)
   ...
```

---

## Honest disclosure section (mandatory — preempts HN criticism)

**What I'm NOT claiming:**
- I'm not claiming new ML technique (no GNN, no fine-tuning, no novel encoder)
- I'm not claiming SOTA in academic sense (haven't run BEIR/MTEB extensively)
- I'm not claiming this works for every use case (multi-tenant SaaS users should look elsewhere)
- Pain dimension validation is on N=15 post-incident queries — sample is small

**What I AM claiming:**
- Hybrid pipeline is load-bearing for natural language operational queries (97.7% gap data)
- Shadow discipline prevents silent regression (case study from my own incident)
- Shared-canonical multi-agent works for trusted contexts (1 user + N agents)
- Eval-first culture catches regression that vibe-checking doesn't

---

## Footer / call to action

> Code: github.com/totobusnello/memoria-nox (MIT)
> Paper (arXiv): [link when published]
> Product (coming): NOX-Supermem (Brasil/Hotmart, 2026-Q3)
>
> If you're building agent memory and have queries from a context I haven't covered, I'd love them as held-out test data — open an issue or DM.
