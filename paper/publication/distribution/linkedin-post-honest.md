# LinkedIn Post — Honest Results (Ablation Variant)

> Post 2h after HN submission. Same timing as original. Use this variant as primary if ablation is disclosed publicly, or as a standalone "methodology leadership" post before launch day. Tone: practitioner humility, not academic retreat.

---

## POST COPY

I shipped a feature for 4 months that I thought was my main contribution.

Last week I ran the ablation.

I was wrong. Here's what I learned — and why I'm publishing it anyway.

---

The feature: pain-weighted salience.

The idea: encode incident severity directly into retrieval scoring.

salience = recency × pain × importance

A prod-outage lesson from 6 months ago should outrank a minor note from yesterday. That's how human operational memory works. I built the intuition into the schema, ran it in production for 4 months across 6 AI agents and 64,000+ chunks, and was ready to lead the paper with it.

---

Then I ran the ablation study.

n=31 post-incident queries. Bootstrap confidence intervals. 1000 iterations.

Delta nDCG@10 = +0.0065.

95% CI: [-0.014, +0.034].

NOT significant.

---

The hybrid retrieval stack — FTS5 + Gemini semantic embeddings + RRF fusion — dominates 29 of 31 queries before pain gets a chance to matter.

Pain-weighted salience is a secondary modulator. Not the primary driver I thought it was.

---

There is one case where it works exactly as designed.

Query Q55: a retrieval test for atomic pre-op backup procedures, surfaced during an April 25 incident where a cron job silently wiped 183 structured memories.

Two chunks with nearly identical semantic similarity. One routine note. One prod-incident lesson.

Pain broke the tie correctly. Delta nDCG@10 = +0.349.

That's the tied-semantic regime. Narrow. Real. Operationally important.

---

Here's the leadership insight I want to share with the CTOs and engineering managers in my network:

**Shipping the negative result is the contrarian play that earns trust.**

When we only publish the features that worked, we create a literature full of victories that nobody can reproduce. Other teams try to implement "pain-weighted salience" because they read it in a paper and don't know it only moves the needle in one narrow edge case.

Publishing the ablation honest — with the CI, with the regime where it does work, with the case study — is more useful than a clean abstract with a missing limitation section.

---

What survives the ablation:

**1. Shadow discipline** — any change affecting retrieval ranking runs silent for 7 days before activating, enforced via cron and a health endpoint. Not documented and hoped for. Architecturally constrained.

**2. Incident-shaped schema design** — every schema version from v1 to v12 has a corresponding incident in the log. The April 25 event that wiped 183 entities at 22:03 is in the incident log. The incident log shaped the retention fields. The retention fields are in the paper.

**3. The Q55 case study** — one query, one regime, real operational stakes. The negative result and the case study together tell a more complete story than either alone.

---

The paper publishes May 19 on arXiv.

The ablation is in the paper. The negative result is in the abstract. The case study is the lesson.

If you're building AI agent memory in production and want to talk through what actually moves retrieval quality — not what sounds good in a pitch — I'd like to hear from you.

Repo + eval harness + ablation data: github.com/totobusnello/memoria-nox

---

## Posting notes

- Remove the "## POST COPY" header — paste only the body
- Hashtags: #AIEngineering #AgentMemory #HonestML #ProductionAI #SoloBuilder
- First comment (within 10 min): paste the direct arXiv link + "Full ablation data in repo — CI included"
- Engage every comment in the first 4h
- If a CTO/VP Eng engages: DM with the NOX-Supermem interest framing ("operational teams who need memory that survives incidents")
- Tone check: reads like someone who ran the experiment and respected what it found — not defensive, not performatively humble
- This variant pairs better with a technical audience than the original; original is better for a broader founder/operator audience
