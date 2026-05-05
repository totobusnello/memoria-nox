# HN First Comment — Author Post

> Post within the first 5 minutes of submission. Plain text, no markdown. HN renders asterisks and backticks as literal characters in comments.

---

Author here. Some context before the inevitable "but FTS5 works fine for me" comments.

The 97.7% figure comes from this baseline: nDCG@10 of FTS5-vanilla (BM25-only) on 50 internal queries written in natural language = 0.0123 (effectively zero). Hybrid (FTS5 + Gemini semantic + RRF) = 0.5213. The absolute gap is 50.9 percentage points; the relative contribution of FTS5-alone to the hybrid score is ~2.4% — essentially nothing when queries are full sentences rather than keyword bags. 3-run mean ± std: Hybrid 0.5213 ± 0.0004, FTS 0.0123 ± 0.0000. If you run BM25 with keyword queries you extracted first, it performs differently. That's not what production agent memory does.

Three objections I expect and want to address upfront:

1. "n=50 is too small." Fair. The 50 queries were internally curated by me, which introduces selection bias. I added 10 held-out queries (R01c) and ran external validation: on BEIR TREC-COVID (50 NIST queries, 171K docs), multilingual-e5-base reached nDCG@10=0.8335 versus 0.3070 on our internal corpus, and FTS5 BM25 reached 0.1007 versus 0.0123 internal. Three orders of magnitude — confirms our domain (identifier-dense operational knowledge) is structurally harder than BEIR's biomedical text. Full numbers in the paper. I'd rather name the limitation now than have you find it in comment #4.

2. "Single corpus, single curator." Yes. This is a single-operator, 3-month production system (6 agents, 61K chunks). It is not a benchmark paper. The eval harness and golden queries are in the repo — if your corpus shows different results, I genuinely want to know. That's why it's reproducible.

3. "Why not just preprocess queries into keywords before FTS5?" Because that's adding a layer to fix the layer. Hybrid retrieval handles this correctly. The point is that FTS5-alone is often the default recommendation and it silently zeros out on natural language input. Developers deserve to know this before they ship it.

The deeper contribution isn't the FTS5 finding — it's two things I haven't seen codified anywhere: pain-weighted salience (treating incident severity as a retrieval signal, not just a log field) and shadow discipline (any ranking change is enforced to run in shadow mode for 7 days before activating, via cron + health endpoint, not just documentation).

I'm a developer building this solo in São Paulo. The system runs my personal AI agent infrastructure. The incidents are real — including the April 25 event that wiped 183 entities at 22:03 from a cron job that ran reindex without dry-run. That incident is in the incident log, the incident log shaped the schema, and the schema is in the paper.

Code: https://github.com/totobusnello/memoria-nox
arXiv: link live 2026-06-02
Eval harness + golden queries: in repo under /eval

Happy to go deep on any of the technical decisions. Critical questions preferred over upvotes.
