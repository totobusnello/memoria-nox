# nox-mem — Twitter Thread + Tue Tease (launch Wed 2026-06-03)

**Status:** Ready for posting | **Thread count:** 1 tease + 12 launch tweets + 4 reply templates | **Hashtags:** #AIagents #LLM #openSource #RAG

---

## §1 — Tuesday June 2 (Tease)

**Tue 2026-06-02 morning (~08:00 BRT)**

```
Shipping tomorrow: open-source memory for AI agents. 

Honest benchmarks (LoCoMo +40% vs mem0 at 500-chunk apples-to-apples), 
8ms FTS5 latency, MIT licensed. 

Sneak peek incoming → 7am BRT Wed.

[Image: F10 Phase A dashboard screenshot]
```

**Character count:** 187 chars (within 280 limit)

---

## §2 — Wednesday June 3 (Launch Thread)

**Wed 2026-06-03 at 07:00 BRT sharp**

**Tweet 1/12 (Hook)**

```
We just open-sourced nox-mem: pain-weighted hybrid memory for AI agents.

SQLite on your disk. Provider your choice. Zero vendor lock-in.

→ github.com/totobusnello/memoria-nox

1/12

[Image: README hero SVG + logo]
```

**Character count:** 167 chars

---

**Tweet 2/12 (Problem)**

```
LLM agents forget everything between sessions.

The solutions on the market either:
• Lock your data in someone else's cloud
• Tie you to a proprietary runtime
• Skip the benchmark question entirely

You shouldn't have to choose between capability and ownership.

2/12
```

**Character count:** 247 chars

---

**Tweet 3/12 (Solution pillars)**

```
nox-mem is built on 3 pillars:

Quality — retrieval numbers that actually lead, measured honestly
Autonomy — your SQLite file, your embedding provider, inspectable with sqlite3
Product — answer primitive, MCP tools, CLI, HTTP API

3/12
```

**Character count:** 226 chars

---

**Tweet 4/12 (Architecture under hood)**

```
Under the hood:

FTS5 BM25 (keyword)
+ Gemini embeddings 3072d (semantic)
→ RRF fusion k=60 (language-aware weights)
+ pain-weighted salience (recency × pain × importance)
+ KG entity graph (15k+ entities)

Every ranking change ships shadow-mode first. ≥7d baseline.

4/12
```

**Character count:** 259 chars

---

**Tweet 5/12 (Numbers — internal eval)**

```
Internal eval on production corpus (68,995 chunks, 100% vector coverage):

nDCG@10 = 0.6237 (G5 V3, full boost stack)
Δ vs baseline: +78.8%
LongMemEval n=100: nDCG@10=0.9126, MRR=0.9162

Q4 broader smoke (Sat 2026-05-24, eval-isolated):
nDCG@10 = 0.6380
p50 latency = 8ms
Gold hits: 13/20 (65%)

5/12
```

**Character count:** 271 chars

---

**Tweet 6/12 (Apples-to-apples LoCoMo comparison)**

```
Per-dataset apples-to-apples @500 chunks:

LoCoMo conversational memory:
nox-mem Gemini hybrid: 0.1835 nDCG@10
mem0: 0.1315 nDCG@10
→ nox-mem wins +40% on conversational scope

Honest caveat: aggregate diluted by corpus-ordering. 
Full corpus eval published in COMPARISON.md.

6/12
```

**Character count:** 267 chars

---

**Tweet 7/12 (Autonomy literal)**

```
"Autonomy" here is literal:

cp nox-mem.db ~/backup.db   ← that's your backup
sqlite3 nox-mem.db "SELECT * FROM chunks"   ← that's your data
GEMINI_API_KEY=... or OPENAI_API_KEY=...   ← your provider, one env var

No daemon. No cloud sync. MIT license.

7/12
```

**Character count:** 224 chars

---

**Tweet 8/12 (G-series ablation gauntlet)**

```
Every major retrieval decision was ablated before shipping:

G3 → G5 (+78.8% nDCG@10)
G7 salience isolation
G8 source_type_boost
G9 redundancy confirmation
G10 Hard Mutex deployed
G10b per-category
G10c per-style
G10d ACTIVE-T2
G12 dedup

Each published in DECISIONS.md. Zero results suppressed.

8/12
```

**Character count:** 269 chars

---

**Tweet 9/12 (Speed comparison)**

```
Latency trade-off:

Local FTS5 path: 8ms p50
Gemini hybrid: 940ms p50

Choose your trade-off. Both live, switchable via env var.

Hybrid lifts FTS5-only from 0.0466 → 0.0918 nDCG@10 (+97% gain).

9/12
```

**Character count:** 183 chars

---

**Tweet 10/12 (Observability + F10)**

```
Production-ready F10 observability suite live: 4 dashboards

Health: vector coverage, section distribution, salience mode, ops_audit status
Evals: per-category nDCG@10 breakdowns
Telemetry: query latency p50/p95/p99
Shadow: baseline vs active comparison

Live at /api/health

10/12
```

**Character count:** 271 chars

---

**Tweet 11/12 (Paper + transparency)**

```
Technical paper on arXiv (submitted Tue Jun 2, available Wed Jun 3):

Pain-weighted hybrid retrieval: salience formula, shadow discipline, G-series ablation methodology

Methodology disclosed end-to-end. No black boxes.

→ [arXiv link live Wed 2026-06-03]

11/12
```

**Character count:** 244 chars

---

**Tweet 12/12 (Call to action + links)**

```
MIT licensed. Star → ⭐ Issues → 🐛 PRs welcome → 🤝 Discussions → 💬

Repo: github.com/totobusnello/memoria-nox
Paper: [arXiv link]
Comparison: github.com/totobusnello/memoria-nox/blob/main/docs/COMPARISON.md
Blog: [launch-blog-v0-draft.md]

Happy to answer technical Qs.

12/12

[Image: Repo architecture diagram]
```

**Character count:** 276 chars

---

## §3 — Reply Schedule (1 hour after Tweet 1/12 @ 08:00 BRT)

**Reply 1 — Q: How does nox-mem compare to Letta/LangChain memory?**

```
Letta is an agent framework; nox-mem is a memory layer that can sit inside or outside it.

Key difference: nox-mem's pain-weighted salience + shadow discipline. You attach semantic metadata (0.1 trivial → 1.0 prod-outage) at ingest time. High-pain memories rank higher and decay slower.

Letta handles agent state; nox-mem handles memory retrieval.

Both are composable. Use together.
```

**Thread:** reply to Tweet 2/12 (Problem statement)

---

**Reply 2 — Q: Why not use a proper vector DB (Qdrant, Weaviate, Chroma)?**

```
Two reasons:

1. sqlite-vec gives exact nearest-neighbor search — no approximation errors, no ANN tuning, reproducible evals. For <500k chunks on local hardware, perf difference is negligible.

2. Portability: entire memory store is one .db file. `cp nox-mem.db backup.db` is the backup story.

That matters more than p99 ANN latency at this scale.
```

**Thread:** reply to Tweet 4/12 (Architecture)

---

**Reply 3 — Q: How is "pain" assigned? Is this manual?**

```
Both manual and inferrable.

`ingest-entity` command accepts a `pain:` frontmatter field (0.0–1.0).
Plain markdown ingest defaults to 0.2 (low severity).

Vision for P6: LLM-assisted pain estimator at ingest time — not shipped yet, gated on Q4 COMPARISON winning first.

For now: you assign pain based on domain knowledge.
```

**Thread:** reply to Tweet 7/12 (Autonomy)

---

**Reply 4 — Q: What's the operational cost?**

```
Under $11/month all-in on Hostinger VPS (2 vCPU, 8GB RAM), running 7 agents simultaneously.

Gemini embedding calls dominate (~800ms p50).
`gemini-2.5-flash-lite` tier keeps KG extraction + LLM inference within quota.
FTS5 search is free once vectors are built.

Total cost: provider API + compute. No SaaS tax.
```

**Thread:** reply to Tweet 12/12 (CTA)

---

## §4 — Hashtag Strategy

**Primary hashtags (all 12 tweets):**
- `#AIagents`
- `#LLM`
- `#openSource`
- `#RAG`

**Optional tweet-specific tags (selective — max 2 per tweet to avoid noise):**

- Tweet 1 (hook): `#AIagents #openSource`
- Tweet 5 (numbers): `#benchmarks` (optional)
- Tweet 11 (paper): `#arXiv #research` (optional)

**Mentions (only in directly relevant tweets, no astroturf):**
- Tweet 6 (mem0 comparison): mention `@mem0` ONLY if direct conversation thread exists; otherwise skip
- Do NOT mention other projects unless directly asked or compared in tweet body

---

## §5 — Visual Assets

| Tweet | Asset | Format | Alt-text |
|---|---|---|---|
| Tue tease | F10 Phase A dashboard | PNG/JPG | "nox-mem health dashboard showing vector coverage 99.97%, salience formula active, G10 Hard Mutex deployed" |
| 1/12 hook | README hero SVG + logo | PNG/SVG | "nox-mem logo: pain-weighted hybrid memory for AI agents" |
| 4/12 arch | Architecture diagram | PNG | "nox-mem retrieval pipeline: FTS5 BM25 → Gemini 3072d → RRF fusion → salience ranking" |
| 5/12 numbers | Eval results table | PNG screenshot | "Eval results: nDCG@10 0.6237 vs baseline +78.8%, LongMemEval 0.9126 MRR" |
| 6/12 apples | Comparison table | PNG screenshot | "Per-dataset comparison: nox-mem 0.1835 vs mem0 0.1315 on LoCoMo 500-chunk corpus" |
| 12/12 CTA | Repo architecture diagram | PNG | "nox-mem stack: CLI (26+ cmds) + MCP server (16 tools) + HTTP API from one npm package" |

**Storage location:** `docs/launch-assets/`

---

## §6 — Posting Checklist

**Tue 2026-06-02 (08:00 BRT)**
- [ ] Verify arXiv submission accepted + paper link live
- [ ] Confirm F10 dashboard screenshot ready
- [ ] Post tease tweet
- [ ] Like/RT emerging agent discourse if relevant

**Wed 2026-06-03 (06:50 BRT — pre-launch 10min buffer)**
- [ ] Verify all 12 tweets loaded in Twitter scheduler (or native app)
- [ ] Double-check character counts (all <280)
- [ ] Confirm image assets attached to correct tweets
- [ ] Test each hyperlink (arXiv, GitHub, COMPARISON.md, blog)

**Wed 2026-06-03 (07:00 BRT — LAUNCH)**
- [ ] Post Tweet 1/12 (hook)
- [ ] Monitor engagement (like, RT, reply rate)
- [ ] Thread posts auto (staggered ~2-3min between tweets, Twitter's native thread mode)

**Wed 2026-06-03 (08:00 BRT — Reply window)**
- [ ] Post Reply 1 (Letta comparison)
- [ ] Post Reply 2 (vector DB comparison)
- [ ] Post Reply 3 (pain assignment)
- [ ] Post Reply 4 (operational cost)
- [ ] Pin main thread (Tweet 1/12) if available

**Wed 2026-06-03 (09:00+ BRT — Monitoring)**
- [ ] Track HN discussion (if Show HN post live)
- [ ] Engage in substantive replies (avoid defensive tone)
- [ ] Reply to technical Qs with links to DECISIONS.md, paper, COMPARISON.md
- [ ] Retweet relevant agent/RAG discourse

---

## §7 — CTA Messaging Variants

**If asked "Why is nox-mem better?"**

```
Not "better" — different.

nox-mem optimizes for ownership, honesty, reproducibility:
- Your SQLite file on your disk
- Zero vendor lock-in (bring your own embedding provider)
- Every ranking decision ablated and published
- Shadow discipline (≥7d baseline before production change)

If you want SaaS + managed infrastructure, that's a valid choice too. 
This is for teams who want to own their memory.
```

**If asked "When is Tier 2 (encrypted SQLCipher) shipping?"**

```
Tier 2 (A2, SQLCipher + Ed25519 audit checkpoints) is gated on Q4 COMPARISON winning.

Current status: Q4 smoke (Sat 2026-05-24) nDCG@10 0.6380 → above D43 gate (+18.8%).
Full 6-system canonical run in progress; numbers ship before end Q4.

If you need encryption now, you can layer it externally (cp to encrypted volume, etc).
```

---

## §8 — Internal Notes

**Why this framing:**
1. **Tue tease** establishes "honest benchmarks" tone 24h before launch — primes for comparison table reveal
2. **Thread 1/12** leads with pain-weighted + autonomy (differentiators vs commoditized memory solutions)
3. **Tweet 4/12** architecture details justify the complexity (pre-empts "why not simpler solution?")
4. **Tweet 6/12** apples-to-apples comparison answers Q18/Q19 directly, with caveat (builds trust)
5. **Replies** address Q18 (vector DB), Q19 (pain), Q20 (cost) — three most-likely technical objections

**Tone throughout:**
- Matter-of-fact (ship-focused, not hype)
- Transparent about trade-offs (local FTS5 vs Gemini latency; aggregate vs per-dataset)
- Credibility markers: "shadow discipline", "≥7d baseline", "DECISIONS.md", "published ablations"
- No superlatives; numbers speak

**Timing logic:**
- Tue tease 08:00 BRT gives ~23h runway for retweets/discourse
- Wed 07:00 BRT launch aligns with Toto's typical working hours (Brazil timezone)
- 1h gap before replies (08:00) gives early traction time, replies show up as thread is gaining momentum
- Reply window closes gracefully by 10:00 BRT (agent goes to other work)

---

