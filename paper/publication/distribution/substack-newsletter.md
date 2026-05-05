---
title: "I built memory for 6 AI agents. Here's the night it almost fell apart."
subtitle: "On pain weights, shadow discipline, and why the incident log is now architecture."
publication_date: 2026-05-20
format: substack-newsletter
word_target: 1200-1500
audience: engineering-managers, CTOs, indie-hackers, founders
---

# I built memory for 6 AI agents. Here's the night it almost fell apart.

It was 22:03 on April 25.

A scheduled cron job ran a single command: `nox-mem reindex`. No flags. No dry-run. No confirmation prompt. The job completed successfully — exit 0, no errors, no alerts.

Then I checked the health endpoint.

183 entities had lost their `section`, `retention_days`, and `section_boost` fields. Three months of carefully annotated context — architectural decisions, incident post-mortems, team-specific retention rules, hard-won lessons from 1am outages — had been flattened into generic, unstructured chunks indistinguishable from any other document in the database.

The database obeyed the command perfectly. That was exactly the problem.

I sat there for a while. Then I wrote the constraint into the schema and started building what would become the paper I'm publishing next week.

---

*This is the Weekly Digest. If someone forwarded this to you and you build with AI agents, [subscribe here](#) — I write about the operational realities nobody documents.*

---

## Why six agents sharing memory is harder than it sounds

Three months ago, I had six AI agents running in production: Atlas, Boris, Cipher, Forge, Lex, and Nox. Each specialized. Each isolated. Each rediscovering context the others had already learned.

Forge would learn something about a deployment quirk. Atlas would ask the same question three weeks later. Nox would document an incident. Boris would have no idea it happened. Every conversation started from scratch in ways that had real costs — not just bad UX, but wrong decisions made without institutional memory.

I looked at the existing tools. **LangChain Memory** is essentially key-value with session IDs — works for isolated sessions, not for cross-agent institutional knowledge. **MemGPT (now Letta)** does per-agent isolated state with OS-inspired memory paging — elegant design, but each agent lives in its own silo. **Mem0** partitions by `user_id` with LLM-edited self-improving memories — built for B2C, where isolation is a feature, not a problem.

All reasonable for their intended use cases. None of them asked the question I couldn't stop thinking about:

*Did this lesson cost a production outage, or was it just a footnote?*

Because those should be ranked differently.

---

## The three ideas that came out of the failures

### 1. Pain weighting: "what if a six-month-old incident mattered more than yesterday's note?"

Most retrieval systems rank by recency and term frequency. Some add importance signals. Here's what none of them do: **ask how much an experience cost.**

Every chunk in my system has a `pain` field — a number from 0.1 (trivial note) to 1.0 (production outage). When a chunk is created from an incident post-mortem, it gets a high pain score. When it's a minor config update, it gets the default 0.2.

The result: a lesson from a prod-outage six months ago outranks documentation updated yesterday on a minor topic. Not because it's newer. Because it cost more.

I checked the literature — GraphRAG, Mem0, A-MEM, HiRAG, Cognee all model structure and recency. Zero papers treat incident severity as a retrieval signal. The dimension just... doesn't exist in the field yet.

### 2. Shadow discipline: "no ranking change ships without seven days of waiting"

After the April 25 incident, I didn't just fix the bug. I asked: what systemic property would have caught this *before* it reached production?

The answer wasn't better tests. It was a constraint: any change that affects ranking must run in shadow mode for at least seven days before activation. The system computes the new ranking in parallel, logs the delta, but doesn't mutate the actual results. After seven days, you look at the distribution and decide.

This isn't a best practice I document and hope people follow. It's a structural constraint enforced by environment variable, cron monitoring, and the health endpoint. You cannot accidentally activate a ranking change — you have to deliberately flip the switch, and the telemetry has to justify it.

The salience feature ran seven days of shadow: 191 promote candidates, 16,608 review-needed, 45,743 archive candidates. Only after analyzing that distribution did it go live.

The April 25 incident — a silent regression with no error, no alert, no log entry — is exactly what shadow discipline is designed to catch.

### 3. Shared canonical: "all agents read the same library, no federation, no overhead"

The standard approach to multi-agent memory: give each agent its own isolated state. Cross-agent knowledge requires explicit handoff, synchronization, or federation infrastructure.

My six agents read from the **same canonical table**. No synchronization. No merge. No federation overhead. Agent scoping happens via `source_file` prefixes and SQL filtering at query time.

When Forge learns something about a deployment pattern, Atlas retrieves it directly on the next relevant query. Not because anyone synchronized — because there was never a separation to begin with.

The practical result: 1 GB of SQLite serving 6 agents, zero federation overhead, 99.92% shared corpus by measurement.

---

## The numbers that made the decision obvious

At some point I wanted to cut costs. Gemini embeddings aren't free. What if I disabled semantic search and fell back to keyword-only for a while?

I had an eval harness. I ran it.

| Approach | nDCG@10 |
|---|---|
| FTS5 keyword-only | 0.0123 |
| Strong BM25 baseline (Pyserini) | 0.1475 |
| nox-mem hybrid (FTS + Gemini + RRF) | 0.5213 |

The keyword-only score isn't just lower. It's near-zero. A natural language query like "why does the reindex command lose section data" doesn't match any document containing the answer, because the answer is spread across technical terms that don't appear together as exact tokens. The semantic layer isn't a nice-to-have — it's structurally load-bearing.

The hybrid system delivers **3.5× over the strong BM25 baseline** and **97.6% relative improvement over vanilla keyword search**. The experiment took 20 minutes to run. The cost savings plan was abandoned in 25.

> **[Image suggestion: Twitter chart hero — bar chart showing 0.0123 / 0.1475 / 0.5213 nDCG@10, three bars, stark visual contrast. Caption: "This is why we can't turn off semantic search."]**

Three months in production. 61,257 chunks. 6 agents. 12 schema versions. Two data-loss incidents that rewrote the architecture instead of breaking the project. Solo, no funding, São Paulo.

---

## What this paper is really about

I've read a lot of research on agent memory. The papers talk about architecture at the moment of design — clean diagrams, synthetic benchmarks, controlled evaluations.

The system I built was shaped by what broke.

The April 25 reindex gave me shadow discipline and the `section` field. A May 1 incident where a `sed -i` command ran accidentally on SQLite binary files corrupted 1 GB of data across nine files. That gave me a hard rule — codified in the code, not in a wiki page — that file-modifying operations must filter by extension before running.

Every catastrophic failure became a structural property of the system. Not a post-mortem document that decays. Not a team norm that new members have to learn. A constraint the code enforces automatically.

**Operational discipline beats algorithmic novelty.** Production scars are more useful than synthetic benchmarks. Solo + open + reproducible is more valuable than closed-source excellence.

These aren't conclusions I came in with. They're what three months of incidents taught me.

---

## Where to find it

The paper publishes on arXiv on **May 19** — I'll send a dedicated issue with the link and a breakdown of the methodology. The full technical blog post (2,500 words, code snippets, comparison tables) goes live on **dev.to on May 20**.

Here's what's available now:

- **GitHub**: [github.com/totobusnello/memoria-nox](https://github.com/totobusnello/memoria-nox) — MIT licensed, eval harness included, 50 curated golden queries, reproducible by any reviewer
- **The eval harness**: 8 categories of queries, 12% negative cases, nDCG/MRR/Recall metrics — all in the repo, not just described

If you're building agent memory and want to share queries from your domain, I'd genuinely like them as held-out test data. Open an issue or reply to this email.

If someone forwarded this to you: **[subscribe here](#)** — this newsletter goes out weekly, focused on what it actually takes to build AI agents in production.

---

*The incidents are in the log. The log is in the schema. The schema is in the paper.*

---

**P.S.** — The paper is about memory architecture. The next thing I'm building is the product layer on top of it: NOX-Supermem, a packaged memory system for teams running multiple agents who need institutional knowledge that actually persists. If you're interested in being an early tester, reply with "supermem" — I'll reach out before the public launch.
