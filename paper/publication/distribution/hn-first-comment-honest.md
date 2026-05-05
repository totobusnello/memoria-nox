# HN First Comment — Honest Results (Ablation Variant)

> Use this variant if the ablation result is public before launch, or as the primary comment if you want to lead with intellectual honesty. Plain text, no markdown. Post within 5 minutes of submission.

---

Author here. I want to front-load something that isn't in the abstract yet.

I shipped pain-weighted salience as a core differentiator. Severity encoded directly into retrieval: salience = recency x pain x importance. The idea is that a prod-outage lesson from six months ago should outrank a minor note from yesterday. I spent three months building that intuition into the schema. I was confident it was the main contribution.

Then I ran the ablation.

n=31 post-incident queries (bootstrap CI, 1000 iterations). Pain ablation: pain held constant at 0.5 vs. calibrated [0.1, 1.0] range. Delta nDCG@10 = +0.0065. 95% CI [-0.014, +0.034]. NOT significant.

The hybrid stack drowns it. Gemini semantic retrieval dominates 29 of 31 queries. Pain doesn't move the needle when semantic similarity already surfaces the right chunk.

There is one regime where it matters. Query Q55 — "backup atomico pre-op, o que devo fazer?" — showed delta nDCG@10 = +0.349. That's the tied-semantic regime: two chunks surface with nearly identical cosine similarity, one from a routine note, one from the April 25 prod incident. Pain breaks the tie correctly. The FTS-only ablation is running now to see if this generalizes without the semantic layer.

So the honest answer is: pain-weighted salience is a secondary modulator, not a primary driver. It matters in edge cases that are operationally important. I'm not downgrading the contribution — I'm right-sizing it. The case study is the lesson.

What I'm keeping as the primary methodology contribution: shadow discipline (any ranking change runs silent for 7 days, enforced architecturally, not documented and hoped for) and the incident-shaped schema design pattern. The April 25 event that wiped 183 entities at 22:03 — that's in the incident log, the log shaped the schema, the schema is in the paper.

I'd rather ship a negative result with a real case study than market a feature that doesn't generalize.

FTS-only ablation data incoming. If you've seen pain or severity signals work in retrieval, I want to know what regime and what corpus.

Code: https://github.com/totobusnello/memoria-nox
arXiv: live 2026-05-19
Eval harness + golden queries + ablation data: in repo under /eval

Critical questions preferred over upvotes.
