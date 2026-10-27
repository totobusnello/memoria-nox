# v3 scored: 0.2428 → 0.2567 (+5.7%), and my own +37.5% prediction is refuted — 2026-10-27

Ruler v3 scored on the production search path with the database isolated. **Cost zero** — the strict
arm needs no LLM.

| | v2 | **v3** |
|---|---|---|
| queries scored | 55 | **57** (56 strict + 1 marginal) |
| **nDCG@10 strict** | **0.2428** | **0.2567** (+5.7%) · 0.2613 without the marginal |
| recall@10 | 0.35 | 0.3684 |
| MRR | — | 0.2478 |
| zero-hit | 29/55 = 52.7% | **32/57 = 56.1%** — it **rose** |
| median latency | — | 3,769 ms |

By category (strict, so not comparable to v2's pooled table): security 0.4542 · concept 0.3671 ·
procedure 0.2740 · entity 0.2377 · temporal 0.1722 · cross-agent 0.1667 · **decision 0.0511**.

## 🔴 The correction: the ruler was not materially deflated

This afternoon's audit, `2026-10-27-the-ruler-is-deflated-not-inflated.md`, said the published figure
was **deflated by +25 to +37.5%**. The arithmetic behind it was `0.2428 × 55/40` — and it assumed the
15 queries with invalid gold were being **unfairly** zeroed, so that discounting them would lift the
mean.

Repairing them instead of discounting them tests that assumption directly, and it fails:

| | nDCG@10 | zero-hit |
|---|---|---|
| the 14 repaired queries | **0.1679** | 10 of 14 |
| the other 43 | 0.2856 | 22 of 43 |

**The retriever misses their real answer too.** So the invalid gold was **measuring the wrong thing,
not depressing a score the system deserved** — and the zero-hit rate rising from 52.7% to 56.1%
is the same fact seen from the other side: there are now more scorable queries whose answer the
system does not find.

| | |
|---|---|
| my published prediction | 0.2428 × 55/40 = **0.3338 (+37.5%)** |
| measured | **0.2567 (+5.7%)** |

⇒ **The +25 to +37.5% range is withdrawn.** The three facts from that audit stand — 60.0% of gold
entries did not answer their question, 15 of 55 queries had none valid, Q99's gold is invalid — but
the inference I drew from them about the score does not. A count of broken gold does not predict the
direction or size of the score change, because a query can be mis-measured and also genuinely missed.

🔑 And that is the general form: **repairing a ruler tells you what the system does, not that the
system does better.** I had the first and asserted the second.

## The run, and the mistake inside it that had to be fixed first

The first scoring run returned nDCG **0.0113** with a **median latency of 6 ms**. That is not a
retrieval result — `searchHybrid` with Gemini embeddings does not answer in 6 ms — and the log said
so on every query:

```
[WARN] Semantic search failed, falling back to FTS: GEMINI_API_KEY not set
```

CLAUDE.md rule 1, and the omission was mine: a script that runs the CLI over SSH must
`set -a; source /root/.openclaw/.env; set +a` or the semantic arm fails **silently** into FTS-only.
With the env sourced, median latency went 6 ms → 3,769 ms and the score 0.0113 → 0.2567. **A number
produced by a half-disabled pipeline reads exactly like a bad retrieval result.**

Isolation, both layers the harness documents: `NOX_DB_PATH` points at a `VACUUM INTO` copy
(1,581,420,544 bytes) so every write lands there, and `trackAccess=false` so `access_count` — which
feeds salience, part of what is being scored — is not bumped even inside the copy. Gold was resolved
**on that copy**, because ids minted in one database do not match another.

## One harness change, declared

`run-gold-eval.mjs` skipped anything whose status was not exactly `accepted`, which would have
dropped v3's single `accepted_marginal` (Q52). It is now scored **and tagged**, and the summary
reports the aggregate both with it (0.2567) and without (0.2613): folding a declaredly weak gold into
the aggregate silently would make the number depend on a judgement the number does not disclose.

**Artifacts.** `audits/2026-10-27-score-v3.sh`, `audits/2026-10-27-why-not-37-percent.py`, and
`eval/run-gold-eval.mjs`. Per-query rows stay on the host under `/var/tmp/score-v3-161128/out.json`.
