# Twitter/X Thread — Launch Day (Tuesday 2026-06-02)

> Post at 09:00 ET (10:00 BRT) simultaneous with HN submission. Schedule tweets 2-3 min apart to hit the timeline feed in sequence. All tweets ≤280 chars. Numbering uses 1/11 format.

---

## Tweet 1 — Hook (incident narrative)

1/11

At 22:03 on April 25, a cron job ran `nox-mem reindex` without dry-run.

183 entities lost section, retention, and boost in seconds. No error. No alert. The database just... obeyed.

That night changed how I think about agent memory.

[~240 chars]

---

## Tweet 2 — Thesis

2/11

The real problem with AI agent memory isn't retrieval quality.

It's operational discipline.

Systems fail silently because nobody encoded the hard lessons into the schema.

So I did.

[~180 chars]

---

## Tweet 3 — Differential 1: Pain-Weighted Salience

3/11

Every memory system models recency. None model severity.

nox-mem: salience = recency × pain × importance

pain ∈ [0.1, 1.0] — from trivial note to prod-outage.

A 6-month-old incident lesson beats today's minor update. Like human memory should work.

[~257 chars]

---

## Tweet 4 — Differential 2: Shadow Discipline

4/11

Any ranking change in nox-mem must run in shadow mode for ≥7 days before activating.

Not a best practice in a doc. An enforced architectural constraint via cron + /api/health endpoint.

The April 25 incident would have been caught in shadow. It wasn't. Now it's codified.

[~275 chars]

---

## Tweet 5 — Differential 3: Shared-Canonical Multi-Agent

5/11

MemGPT uses per-agent state. Mem0 partitions by user_id.

6 agents in nox-mem read from the same canonical corpus. No sync. No merge. No federation overhead.

When Forge learns something, Atlas retrieves it. Because they were never separated.

[~242 chars]

---

## Tweet 6 — Chart Hero

6/11

[IMAGE: Two-bar chart. Left bar labeled "FTS5 vanilla (BM25-only)" at nDCG@10 = 0.0123, colored red. Right bar labeled "nox-mem hybrid (FTS5 + Gemini + RRF)" at nDCG@10 = 0.5213, colored green. Title: "Natural language queries on production memory. 50 internal queries, 3-run mean, 3-month corpus." Caption below: "FTS5 alone contributes ~2% to hybrid score on full-sentence queries."]

BM25-only on natural language queries: nDCG@10 = 0.0123 (near-zero).

Hybrid: 0.5213 (n=50, 3-run mean).

This is not a tuning problem. It's a structural constraint of FTS5 on full-sentence input. Hybrid is the floor, not a premium option.

[~274 chars]

---

## Tweet 7 — Scale and context

7/11

3 months. 6 AI agents. 61,257 chunks. 12 schema versions. 99.97% vector coverage.

p95 search latency: <1s.

External validation: on BEIR TREC-COVID, e5 reaches nDCG@10=0.8335 — 3x its score on our corpus. Difficulty is corpus-dependent.

Built solo. <$11/mo total OPEX.

[~278 chars]

---

## Tweet 8 — Where to find it

8/11

Paper: arxiv.org/[link when live — 2026-06-02]

Blog post (full engineering breakdown): dev.to/totobusnello + Substack

Repo + eval harness + 60 golden queries (50 main + 10 held-out): github.com/totobusnello/memoria-nox

HN thread for technical discussion: [link after submission]

[~270 chars]

---

## Tweet 9 — Incident lesson story (bonus)

9/11

On May 1st, a `sed -i` sweep accidentally ran on .db files.

1 GB of SQLite. 8 backups. All corrupted.

sed rewrites file streams. SQLite stores data in binary page boundaries. The two do not mix.

It's Rule 7 in the CLAUDE.md now. The schema knows what the incident log learned.

[~278 chars]

---

## Tweet 10 — The methodology that nobody writes about

10/11

6 of 7 competing systems analyzed in this paper don't publish a reproducible eval harness.

I'm not saying they're wrong. I'm saying I can't tell if they're right.

The eval, the queries, the golden labels, the baseline runs — all in the repo. Refute or confirm. Your call.

[~272 chars]

---

## Tweet 11 — CTA + Tagline closing

11/11

If you're building memory for AI agents in production, this paper has something for you.

Not benchmarks. Scars.

github.com/totobusnello/memoria-nox

The incidents are in the log. The log is in the schema. The schema is in the paper.

[~235 chars]

---

## Posting notes

- Schedule Tweet 1 at T+0 (HN submission time, 09:00 ET)
- Tweets 2-11: 2-3 min apart via scheduler (Buffer/Typefully)
- Pin Tweet 1 on profile for 48h
- Reply to any technical question directly in the thread
- If HN hits frontpage: quote-tweet the HN submission link from Tweet 8's slot
- Honest disclosure in thread: "solo project, internal corpus, 50 curated queries — bias acknowledged, reproducible by design"
