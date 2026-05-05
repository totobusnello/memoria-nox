---
platform: linkedin
type: long-form article
tone: builder/founder, lessons learned
target_length: 900-1100 words
---

# I Built a Memory System for AI Agents. The Cron Job Broke It First.

At 22:03 on April 25, a scheduled job ran without a dry-run flag. In seconds, 183 entities lost years of structured context. No error. No alert. The system simply obeyed the command it was given.

That failure — and five others like it over three months — is the reason I am now submitting a paper to arXiv.

---

I have been running six AI agents in production (Atlas, Boris, Cipher, Forge, Lex, Nox) on a shared memory system built on SQLite. The corpus holds 61,257 chunks of markdown, PDF, and code. Every agent reads from the same source. No partitioning, no federation, no sync overhead.

The system is called NOX-Supermem. I built it alone in São Paulo, without external funding, using off-the-shelf infrastructure that costs less than $11 per month in total OPEX.

The paper is titled *The Pain Diary and Shadow Discipline: A Memory System That Learns from Its Own Incidents.* Here are the lessons I would have wanted to read before I started.

---

## Lesson 1: Memory is an operational discipline problem, not a retrieval problem.

Every existing agent memory framework treats memory as a retrieval engineering challenge. Encode well, index well, retrieve well.

What none of them models is what happens when a cron job silently corrupts your metadata at 22:03. Or when a developer runs `sed -i` on a 1 GB SQLite file and corrupts it plus eight backups (that happened on May 1). Or when a ranking change is shipped without validation and silently degrades recall for two weeks.

The retrieval problem is mostly solved — or at least solvable with a layered stack. The operational discipline problem is not.

The architecture I ended up with encodes discipline into the schema itself: typed retention lifetimes, incident severity as a numeric field, append-only audit logs enforced by database triggers, and atomic pre-operation snapshots before any destructive command runs.

---

## Lesson 2: The numbers that look impressive hide the one that matters.

The retrieval comparison is striking on its face:

- FTS5 vanilla: nDCG@10 = 0.0123
- BM25 Pyserini (strong baseline): nDCG@10 = 0.1475
- nox-mem hybrid (FTS5 + Gemini embeddings + RRF fusion): nDCG@10 = 0.5213

That is a 3.5x lift over the strongest lexical baseline. It validates that hybrid retrieval — not better embeddings alone — is what moves the needle in operational memory systems with identifier-dense, non-conversational text.

The number I almost buried in the paper: the pain-weighted salience feature — the one I spent the most time on — does not produce a significant aggregate retrieval improvement. Δ = +0.0065, 95% CI [-0.014, +0.034]. Not significant.

Publishing that result anyway was a deliberate choice. The methodological contribution — treating incident severity as a typed schema field with an annotation pipeline, so a prod-outage lesson mathematically outranks a trivial note from yesterday — is valid regardless of the aggregate retrieval metric. The lift was observable in 1 of 31 queries (Q55, Δ = +0.349, where two candidates had near-identical semantic scores); the other 29 were unaffected because the semantic layer already separated them. But I am not going to claim what the data does not support.

Honest negative results are table stakes for engineering credibility.

---

## Lesson 3: Shadow gates save you from yourself.

Every ranking change the system has ever shipped — including the pain-weighted salience feature — ran in shadow mode for a minimum of seven days before activating in production.

Shadow mode is not a convention or a note in a runbook. It is an architectural constraint enforced by a cron job that monitors the `/api/health` endpoint every 15 minutes and alerts if the mode drifts. Three signals must be present simultaneously before activation: wall-clock time >= 7 days, healthy distribution confirmed by telemetry, and explicit human approval.

Phase 1.7b-b validation of the salience feature collected 191 promotions, 16,608 reviews, and 45,743 archived events over seven days before the feature activated. That is the gate.

If shadow discipline had been in place before April 25, the cron incident would have been caught in the preview run. It was not in place. Now it is.

---

## Lesson 4: Sharing context across agents is not a sync problem.

The standard approach in multi-agent memory systems (MemGPT, Mem0) is per-agent or per-user partitioning. Each agent owns its context. Retrieval is isolated.

The problem with this approach: when Forge learns something about a critical architectural decision, Atlas has no access to that knowledge without an explicit sync mechanism.

The alternative I built: one shared canonical corpus. 61,207 of 61,257 chunks — 99.92% — are accessible to all six agents simultaneously without partitioning, synchronization, or merge logic. Cross-agent intelligence by design, not by integration.

The cost of this approach is also low: single-file SQLite, atomic backup via `cp`, zero infrastructure overhead. The knowledge graph layer (1,107 typed relations across a closed enum of seven relation types) provides the structural index that makes cross-agent retrieval useful rather than just possible.

---

## Lesson 5: The incidents are the documentation.

The most useful reference document in the repository is not the README. It is the incident log.

Each operational failure — the April 25 reindex without dry-run, the May 1 sed-on-SQLite corruption, the cron job that spawned a duplicate process loop — produced a concrete schema constraint, a governance rule, or an operational gate. The architecture is a materialized incident log.

This is the claim I am most confident in: any team running AI agents in production long enough will encounter these failure modes. Encoding the lessons in schema rather than in documentation is the difference between a memory system and a memory system that stays consistent under pressure.

---

The paper covers three months of production operation with reproducibility as a first-class constraint: a public 60-query eval harness, versioned schema from v1 to v12, and the incident log in the repository.

Full paper available at arXiv (expected June 2026): [https://arxiv.org/abs/XXXX](https://arxiv.org/abs/XXXX)

Repository (MIT license): [https://github.com/totobusnello/memoria-nox](https://github.com/totobusnello/memoria-nox)

---

What is a production-only insight you have shipped recently — something you could only have learned by running the system under real load, not in a benchmark?
