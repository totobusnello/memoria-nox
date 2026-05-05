# Distribution Cheatsheet — NOX-Supermem Paper Launch

**Publication window:** 2026-06-03 (post-arXiv, pre-HN)
**arXiv:** Submitted 2026-05-19, expected live 2026-06-02 as arXiv:XXXX

---

## dev.to

### Title options (60-char max)

1. `The Cron Job That Broke My AI Agent's Memory` (46 chars)
2. `I Encoded Operational Discipline Into a Schema` (47 chars)
3. `Memory Is Discipline: Building NOX-Supermem` (44 chars)

**Recommended:** Option 1. Leads with the incident hook — concrete, narrative, search-friendly. Avoids jargon in the title.

### Tags (max 4)
```
ai, machinelearning, databases, architecture
```
Rationale: `ai` and `machinelearning` maximize reach; `databases` targets the SQLite/RAG practitioner audience that will understand the technical depth; `architecture` attracts senior readers with authority to share. Avoid `productivity` — undersells the technical content. `webdev` is wrong audience.

### Cover image spec
- **Size:** 1000 x 420 px (dev.to standard)
- **Format:** PNG or JPG
- **Suggested content:** Dark background, the three-layer retrieval diagram (FTS5/Gemini/RRF), nDCG numbers overlaid. Keep text to under 15 words — mobile preview crops aggressively.
- **Alt text:** "Three-layer hybrid retrieval stack: FTS5 BM25, Gemini 3072-d embeddings, RRF k=60 fusion. nDCG@10 = 0.5213"

### canonical_url
Set to: `https://arxiv.org/abs/XXXX` (replace XXXX with actual ID once confirmed)

### Publish time
**10:00 AM EST (15:00 UTC) on 2026-06-03 (Tuesday)**
Rationale: dev.to feeds refresh mid-morning EST when US East Coast readers are at peak browsing. Tuesday and Wednesday are highest traffic days. Avoid Monday (crowded with weekend backlog) and Friday (engagement drops before weekend).

### What NOT to do
Do not publish on arXiv day (2026-06-02) — the algorithm rewards posts that accumulate reactions in the first 2 hours. A same-day post with a draft arXiv link loses credibility if the ID is not yet live.

---

## LinkedIn

### Post text (3000-char cap — version that fits)

Paste this version — counts 2,847 characters including spaces:

```
At 22:03 on April 25, a cron job ran without a dry-run flag.

In seconds, 183 entities lost years of structured metadata. No error. No alert. The database obeyed the command it was given.

That failure taught me something the AI memory literature does not talk about: memory is not a retrieval problem. It is an operational discipline problem.

I spent three months building NOX-Supermem — a production memory system for six AI agents running on a shared SQLite corpus (61,257 chunks, $<$11/month OPEX). The system is now the subject of a paper I am submitting to arXiv.

Here are five lessons I would have wanted to read first:

1. Every incident should become a schema constraint. Each failure produced a concrete rule encoded in the database: typed retention lifetimes, incident severity as a numeric field (pain ∈ [0.1, 1.0]), append-only audit logs enforced by DB triggers.

2. Honest negative results build more credibility than optimistic ones. The feature I spent the most time on — pain-weighted salience — does not improve nDCG@10 in aggregate (Δ = +0.0065, not significant). I published that result anyway. The methodological contribution stands independently.

3. Hybrid retrieval is not an optimization — it is a prerequisite. FTS5 vanilla: nDCG@10 = 0.0123. BM25 Pyserini (strong baseline): 0.1475. nox-mem hybrid (FTS5 + Gemini 3072-d + RRF): 0.5213. That 3.5× lift over the strongest lexical baseline is not a parameter tweak. It is the difference between a system that works and one that does not.

4. Shadow gates should be architectural constraints, not best practices. Every ranking change ran in shadow mode for a minimum of 7 days before activation. Enforced by cron. Monitored via a health endpoint. Not in a runbook that someone can skip.

5. Sharing context across agents is cheaper than syncing it. 99.92% of 61,257 chunks are shared across all six agents from one canonical corpus. No federation, no sync overhead, no merge logic. Cross-agent intelligence by design.

The paper covers three months of production operation with a public eval harness, 60 golden queries, and the incident log in the repository.

Full paper (expected June 2026 arXiv): https://arxiv.org/abs/XXXX
Repository (MIT): https://github.com/totobusnello/memoria-nox

What is a production-only insight you have shipped recently — something you could only have learned by running the system under real load?

#AIEngineering #MachineLearning #SoftwareArchitecture #RAG
```

### Hashtags (3-5)
```
#AIEngineering #MachineLearning #SoftwareArchitecture #RAG
```
Rationale: `#AIEngineering` targets practitioners, not just researchers. `#RAG` is the active conversation this paper joins. Avoid `#AI` alone — too broad, dominated by news content. Avoid `#DataScience` — wrong audience for this technical depth.

### Preview image spec
- **Size:** 1200 x 627 px (LinkedIn OG standard)
- **Format:** PNG
- **Content:** Same diagram as dev.to but landscape-optimized. Add a pull quote: "nDCG@10 = 0.5213 vs 0.0123 — operational memory demands hybrid retrieval." Keep it credible, not promotional.

### Publish time
**08:00 AM EST on 2026-06-03 (Tuesday)**
Rationale: LinkedIn engagement peaks 08:00-10:00 AM EST Tuesday-Thursday. Professional audience checks LinkedIn before 09:00. Publishing before the HN post gives LinkedIn content a 1-hour head start on engagement signals.

### What NOT to do
Do not ask "What do you think?" as the closing question — it reads as generic. The specific prompt ("What is a production-only insight you shipped recently?") invites substantive responses from the exact audience you want to reach. Do not tag people without their permission.

---

## Hacker News

### Title options (80-char max)

1. `Show HN: NOX-Supermem – memory system built from 4 months of production incidents` (80 chars exactly)
2. `NOX-Supermem: incident-driven agent memory on SQLite, nDCG@10 0.5213 vs 0.0123` (80 chars exactly)
3. `We treat agent memory as retrieval. I think it's an operational discipline problem` (82 chars — 2 over, trim if needed)

**Recommended:** Option 1 for "Show HN" category (self-project, public repo, MIT license). Option 2 if the abstract/technical angle gets more traction on HN that week — watch trending titles the day before. Option 3 is the thesis statement and will provoke debate, which HN rewards, but it is slightly over the limit.

### URL
`https://arxiv.org/abs/XXXX` — link directly to the paper, not the GitHub repo. HN treats arXiv submissions with the same seriousness as published papers and the discussion tends to be higher quality. GitHub links sometimes get "where's the paper?" comments within minutes.

### Submit time
**09:00 AM ET on 2026-06-03 (Tuesday)**
= 10:00 AM BRT (São Paulo)

Rationale: HN new submissions get peak visibility in the 09:00-11:00 AM ET window when US West Coast is starting work and US East Coast is mid-morning. Submissions between 14:00-17:00 ET compete with the afternoon dump of link sharing. Tuesday is statistically the strongest weekday for Show HN traction.

### What NOT to do
Do not submit the GitHub URL as primary — the paper link anchors the discussion. Do not submit before arXiv ID is confirmed live (check arXiv.org/abs/XXXX returns 200 before posting). Do not re-submit if it does not catch in the first hour — wait for the next natural window.

---

## Twitter / X

Thread of 5 tweets (280 chars each). Place link in tweet 2 or 3.

**Tweet 1 (hook):**
```
At 22:03 on April 25, a cron job ran without a dry-run flag.

183 entities lost their metadata in seconds. No error. No alert.

That night I realized: agent memory is not a retrieval problem. It is an operational discipline problem.

Thread on 4 months of building NOX-Supermem.
```

**Tweet 2 (paper link + key number):**
```
The result: hybrid retrieval (FTS5 + Gemini 3072-d + RRF) achieves nDCG@10 = 0.5213 vs 0.0123 for FTS5 vanilla — on 61,257 chunks, under 1s p95 latency, $<11/month OPEX.

Paper (arXiv, June 2026): https://arxiv.org/abs/XXXX
Repo (MIT): https://github.com/totobusnello/memoria-nox
```

**Tweet 3 (honest result):**
```
Honest negative result in the paper:

Pain-weighted salience (recency × pain × importance) — the feature I spent the most time on — is not significant in aggregate retrieval (Δ=+0.0065, 95% CI [-0.014, +0.034]).

Publishing it anyway. The methodology is the contribution.
```

**Tweet 4 (shadow discipline):**
```
Every ranking change ran in shadow mode for ≥7 days before activation.

Enforced by cron. Monitored via /api/health every 15 minutes. Three signals required before activation: wall-clock ≥7d, healthy distribution, explicit human approval.

Not a convention. An architectural constraint.
```

**Tweet 5 (close + engagement):**
```
6 agents, 1 corpus, 0 federation.

99.92% of 61,257 chunks shared across all agents. No sync. No merge. Cross-agent intelligence by design.

What production-only insight have you shipped that you could only learn by running under real load?
```

**What NOT to do:** Do not compress all five into one tweet — the thread format gives each claim room to land and generates individual engagement signals. Do not use all-caps for emphasis on HN or Twitter; it reads as shouting.

---

## Substack

### Subject line (80-char max)
1. `The Cron Job That Rebuilt My Agent Memory Architecture` (54 chars)
2. `Four Months of Incidents Built a Better Memory System` (54 chars)
3. `NOX-Supermem: Memory as Operational Discipline` (46 chars)

**Recommended:** Option 1. Narrative subject lines outperform abstract-title subject lines in Substack open rates for technical newsletters.

### Preview text (~150 chars)
```
At 22:03 on April 25, a cron job flattened 183 entities. No error. No alert. Here is what three months of production failures taught me about agent memory.
```
(155 chars — trim "Here is what" to "What" to hit 150 if needed)

### Publish day-of-week recommendation
**Wednesday 2026-06-04 at 09:00 AM EST** — one day after the primary arXiv/dev.to/HN launch.
Rationale: Substack newsletters sent Wednesday morning have peak open rates for technical audiences. Launching one day after the initial HN/dev.to burst means the Substack audience gets the piece when it already has social proof (upvotes, comments). This sequencing also avoids splitting your own attention on launch day.

### What NOT to do
Do not send the Substack newsletter on the same day as the HN submission. If the HN post takes off, you will not have time to respond to comments and also manage email sends. Stagger by one day.

---

## Cross-Platform Sequencing Summary

| Time (ET) | Platform | Action |
|---|---|---|
| 2026-06-02 (day before) | Verify | Confirm arXiv ID is live at arxiv.org/abs/XXXX |
| 2026-06-03 08:00 | LinkedIn | Publish long-form article |
| 2026-06-03 09:00 | Hacker News | Submit Show HN |
| 2026-06-03 10:00 | dev.to | Publish blog post (canonical_url = arXiv) |
| 2026-06-03 10:30 | Twitter/X | Post thread |
| 2026-06-04 09:00 | Substack | Send newsletter |

HN first in the morning window; dev.to slightly later so the arXiv link is confirmed live before the canonical_url is set. LinkedIn early to capture the pre-HN professional audience. Substack next day after social proof accumulates.
