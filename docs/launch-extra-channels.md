# Launch Extra Channels — Wed 2026-06-03

> Complementary to `docs/launch-social-copy.md` (PR #224).
> Covers: Trendshift · IndieHackers · Lobsters · HN variants · LinkedIn.
> All copy in English. Meta-notes in PT-BR.

---

## §1 Trendshift Submission

**URL:** https://trendshift.io/submit  
**Slot:** 10h BRT (ver `docs/launch-day-checklist-2026-06-03.md`)

**Project name:** nox-mem

**Description (~200 chars):**
```
nox-mem: open-source, MIT-licensed memory layer for LLM agents. Hybrid search (FTS5 + semantic + RRF) beats pure-dense baselines on published Q4 benchmarks. Self-hostable. No vendor lock-in.
```
*(192 chars — within limit)*

**Tags:** `AI tools` · `Open Source` · `Developer Tools` · `LLM` · `Memory`

**GitHub URL:** https://github.com/totobusnello/nox-mem

**Hunter bio (Toto submits self):**
> Builder & board advisor. Built nox-mem solo over 6 months — open-source hybrid memory for AI agents, MIT licensed.

**Nota interna:** Trendshift exige conta com atividade prévia. Se conta nova, criar 48h antes (Seg 2026-06-01) e dar star em 3 repos trending pra não parecer bot.

---

## §2 IndieHackers Post

**Title:** I built open-source memory for LLM agents (MIT) — 6 months solo, benchmarks published

**Tags:** `AI` · `Open Source` · `Solo Founder`

**Schedule:** Wed 2026-06-03 09h BRT (right after HN post goes live)

**Body:**

---

Six months ago I started noticing that every AI agent I built suffered from the same problem: they forgot things in ways that felt random and frustrating. Not just "out of context window" forgetting — more like forgetting the *important* stuff while retaining trivia.

So I built nox-mem.

**What it is**

nox-mem is an open-source, MIT-licensed memory layer for LLM agents. It runs locally (SQLite under the hood), requires zero cloud dependencies, and ships with a hybrid search engine that combines:

- **FTS5 BM25** — classic keyword ranking
- **Gemini semantic embeddings** — dense vector search via sqlite-vec
- **RRF fusion** (Reciprocal Rank Fusion) — merges the two signals without hyperparameter hell

The system also maintains a knowledge graph (entities + relations) extracted incrementally via Gemini 2.5 Flash.

**The benchmark result that changed how I think about this**

After publishing internal Q4 results (nDCG@10 on our LongMemEval-style harness), the hybrid approach beat pure-dense retrieval by +14.2% on a 69k-chunk corpus. That gap matters: most "memory for agents" tools I've seen just throw embeddings at the problem and call it done.

**What "pain-weighted" means**

Every memory chunk carries a `pain` score (0.1 trivial → 1.0 production outage). The salience formula (`recency × pain × importance`) surfaces the *consequential* memories first. A bug that took 3 hours to fix ranks above a fleeting preference — even if the preference was ingested more recently.

**Why MIT and self-hostable**

I've been burned by vendor lock-in enough times. nox-mem stores everything in a single SQLite file you own. No API keys required for search. Gemini embeddings are optional (BM25 fallback works fine for many workloads).

**Honest ask**

I'm at the "shipped, validated internally, now figuring out positioning" stage. If you're building AI agents and wrestling with memory, I'd genuinely love your feedback — does the pain-weighted angle resonate? Is hybrid retrieval overkill for your use case? What would make this an obvious choice for your stack?

GitHub: https://github.com/totobusnello/nox-mem

---

## §3 Lobsters Submission

**Title:** nox-mem: pain-weighted hybrid memory for LLM agents [open source]

**Tags:** `ai` · `infrastructure` · `open-source`

**Schedule:** Wed 2026-06-03 14h BRT (after HN heat settles, Lobsters afternoon crowd)

**URL to submit:** https://github.com/totobusnello/nox-mem

**Body / comment to post alongside:**

---

nox-mem is a self-hostable memory layer for LLM agents, built on SQLite (FTS5 + sqlite-vec). MIT licensed, no cloud required.

**Search architecture:**

1. FTS5 BM25 keyword ranking
2. Gemini semantic embeddings (3072d, sqlite-vec) — swappable to any embedder
3. RRF fusion (k=60) combining both signals

On a 69k-chunk corpus with a LongMemEval-style eval harness (n=100 golden queries), hybrid search beats pure-dense by +14.2% nDCG@10. The eval code and methodology are in the repo.

**Pain weighting:** each chunk carries a `pain` float (0.1–1.0) representing severity. Salience = `recency × pain × importance`. Production incidents outrank trivia even when the trivia is fresher.

**Knowledge graph:** entities and relations extracted incrementally via Gemini 2.5 Flash, stored in `kg_entities` / `kg_relations` tables. Used for cross-session path queries.

**Stack:** TypeScript, better-sqlite3, FTS5, sqlite-vec, optional Gemini embeddings. Single-file DB, no daemon required beyond the MCP server or HTTP API on port 18802.

The retrieval design was informed by LightRAG (EMNLP 2025) and LongMemEval benchmarks, though the implementation is independent. Happy to discuss the RRF parameterization or embedding strategy in comments.

---

## §4 HN Show HN — Variant Ladder

> V1 is the canonical post from PR #224 `docs/launch-social-copy.md`.
> V2 and V3 are fallback variants if V1 is flagged or sinks within the first 4 hours.

| Variant | Title |
|---------|-------|
| **V1** (canonical) | `Show HN: nox-mem — pain-weighted hybrid memory (FTS5+sqlite-vec+RRF, MIT)` |
| **V2** (fallback) | `Show HN: An open-source memory layer for LLM agents (with published benchmarks)` |
| **V3** (nuclear) | `Show HN: Hybrid memory for AI agents — keyword + semantic + KG, in 50k lines` |

**Decision rule:**

1. Post V1 at 07h15 BRT Wed 2026-06-03 (peak US morning traffic).
2. Monitor for 4 hours (check at 11h15 BRT).
3. If V1 has < 5 points or is flagged: repost V2 the next morning (Thu 2026-06-04 07h BRT).
4. If V2 also sinks within 4h: repost V3 the following morning (Fri 2026-06-05).
5. Do NOT repost same day — HN penalizes same-day reposts on similar titles.

**V2 body:**
> nox-mem stores agent memories in SQLite (FTS5 + sqlite-vec). Hybrid BM25+semantic+RRF retrieval. On a 100-query LongMemEval harness, hybrid beats pure-dense by +14.2% nDCG@10. MIT, self-hostable, zero cloud deps.

**V3 body:**
> nox-mem is ~50k LOC of TypeScript. It combines keyword search (FTS5 BM25), semantic search (Gemini embeddings via sqlite-vec), and a knowledge graph (entity+relation extraction). Hybrid RRF fusion outperforms pure-dense on published eval. MIT license, single-file SQLite, runs anywhere.

---

## §5 LinkedIn Personal Post

**Schedule:** Wed 2026-06-03 08h30 BRT  
**Tone:** professional but human, not a sales pitch  
**Hashtags (4 max):** `#OpenSource` `#LLM` `#AIInfra` `#SoloFounder`

**Post:**

---

After 6 months of nights and weekends, I shipped something I'm genuinely proud of.

nox-mem is an open-source memory layer for LLM agents — MIT licensed, runs entirely on SQLite, no cloud required. The core idea: AI agents forget things in frustratingly arbitrary ways. I wanted memory that remembers what actually *mattered*, not just what was most recent.

The technical approach ended up more interesting than I expected. Hybrid search — combining keyword BM25 (FTS5), dense semantic vectors (sqlite-vec), and Reciprocal Rank Fusion — outperformed pure-embedding retrieval by 14% on a 100-query benchmark. That gap surprised me. The embedding-only path that "just works" in demos often breaks on real, noisy, multi-session agent memory.

We also added what I call pain weighting: every memory chunk carries a severity score. A production incident ranks above a UI preference, even if the preference is newer. It sounds obvious once you say it out loud, but almost nothing in the space does it.

Six months solo. A lot of SQLite internals learned the hard way. The eval harness wrote itself three times before it stuck.

The repo is live: github.com/totobusnello/nox-mem

If you're building AI agents and thinking seriously about memory architecture — or if you're an advisor/researcher interested in the retrieval design — I'd love to connect. Open to technical collaboration, benchmark comparisons, or just a conversation about where this space is heading.

#OpenSource #LLM #AIInfra #SoloFounder

---

## §6 Coordinated Timing — Wed 2026-06-03

| Hora BRT | Canal | Ação | Responsável |
|----------|-------|------|-------------|
| 05:01 | Product Hunt | Auto-scheduled (sistema agenda na virada do dia PT) | system |
| 07:00 | Twitter T1 | Thread manual (ver PR #224) | Toto |
| 07:15 | HN Show HN — V1 | Post manual | Toto |
| 07:30 | Reddit r/ML | Post manual (ver PR #224) | Toto |
| 08:30 | LinkedIn | Post manual (§5 acima) | Toto |
| 09:00 | IndieHackers | Post manual (§2 acima) | Toto |
| 10:00 | Trendshift | Submission manual (§1 acima) | Toto |
| 14:00 | Lobsters | Submission manual (§3 acima) | Toto |
| 11:15 | HN V1 check | Monitorar pontos e flags | Toto |
| 22:00 Thu (se V1 afundar) | HN V2 repost | Post manual | Toto |

**Nota:** Todos os canais internacionais em inglês. Não misturar idiomas em posts públicos.
