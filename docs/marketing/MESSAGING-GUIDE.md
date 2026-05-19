# nox-mem — Messaging guide

> Version: v1.0 (2026-05-18, Wave G)
> Cross-ref: `docs/VISION.md` v15, `docs/COMPETITIVE-POSITIONING.md`
> Purpose: voice + tone consistency for GTM, README, video, social, investor conversations

---

## Core positioning

**Tagline (exact — no variants, no abbreviations):**

> Pain-weighted hybrid memory with shadow discipline — yours by design.

Every other headline, tweet, elevator pitch, or README subtitle must be derived from or consistent with this tagline. Never shorten it to "hybrid memory" alone (loses the "yours" moat). Never shorten to "yours by design" alone (loses the retrieval quality claim). The three parts are inseparable.

---

## The three pillars in one sentence each

Use these when space is limited:

| Pillar | One sentence |
|---|---|
| Quality | "Numbers that lead the market — or we don't publish them." |
| Autonomy | "Your data, your disk, your provider, your rules — no exceptions." |
| Product | "Memory that shows up where you already work, without forcing you to switch runtimes." |

---

## 1. Headlines that work

### Value-first (lead with the claim)

- "Pain-weighted hybrid memory with shadow discipline — yours by design."
- "Your memory should be yours."
- "Where others guess, we prove."
- "The only agent memory layer where `cp` is your backup."
- "69k chunks. <$11/mo. Your disk."
- "Shadow discipline: ranking changes earn activation. They don't just ship."
- "Portable memory. Auditable retrieval. No lock-in."

### Evidence-first (lead with the number)

- "4× better recall than BM25. Verified. [PR #source]"
- "p95 = 101ms. 42× under budget. Local, no network hop."
- "0.0025ms provider abstraction overhead. Swap Gemini for OpenAI in one flag."
- "535+ tests. Every ranking change earns 7 days of shadow baseline."
- "nDCG@10 = 0.6813 on honest golden set (n=78)."

### Problem-first (lead with the pain)

- "SaaS memory means their cloud sees your agent's memory. We refuse that trade."
- "Runtime lock-in means your data is only yours until you want to switch. We don't do that."
- "Most memory systems ship ranking changes and hope. We shadow-mode first."
- "Your agent's memory lives in a file. Your file. Not their API."

---

## 2. Headlines to avoid

| Avoid | Why |
|---|---|
| "10× better than X" | Requires specific benchmark methodology; sounds like marketing |
| "The fastest memory layer" | Not verified against live corpus; p95 is mock-LLM, not prod latency |
| "Revolutionary" | Marketing speak; says nothing |
| "Game-changing" | Marketing speak; says nothing |
| "The best AI memory" | Superlative without citation; not our style |
| "Better than memanto" | Allowed only after COMPARISON.md publishes; adjective without data |
| "memanto is bad" | Not honest, not evidence-based, not useful |
| "State of the art" | Academic term; only use if citing a paper that calls it that |
| "Production-ready at scale" | Vague; and we haven't run load tests at >1M chunks |
| Any pending-Q-gate number presented as fact | Misleading; LoCoMo/LongMemEval runs are pending |

---

## 3. Comparison phrasing

### When comparisons are allowed

Comparisons are allowed when backed by code in the repo, a PR, or `benchmark/COMPARISON.md` (after Q4 gate fills it).

| Comparison | Correct phrasing | Source |
|---|---|---|
| memanto conflict detection | "Where memanto detects conflicts at the text embedding level, we detect them at the typed relation level — `source_entity_id` + `target_entity_id` FK, not cosine similarity." | `docs/COMPETITIVE-POSITIONING.md` §2 |
| agentmemory runtime lock-in | "agentmemory auto-capture is compelling. Their data stays in the iii-engine runtime. Ours stays in a SQLite file you own." | `docs/COMPETITIVE-POSITIONING.md` §3 |
| gbrain regex extraction | "gbrain shipped regex-first typed-link extraction. We adopted the pattern (L4) and added a confidence gate — regex ≥0.90 confidence skips LLM; below that falls through to Gemini." | README §Lab |
| mem0 quality | "mem0 is a quality-of-whatever-you-plug-in layer. nox-mem is a quality-first layer — we chose Gemini 3072d over 768d embeddings and hybrid RRF over single-retriever because the number mattered." | VISION.md §Competition |
| Letta/MemGPT | "Letta ships the full agent runtime. If you want the memory without the runtime, that's nox-mem." | VISION.md §Competition |

### Comparison format rule

Every comparison must follow:
> "Where [competitor] does X, nox-mem does Y — [evidence: PR #N or benchmark file]."

This structure is honest (acknowledges what the competitor does), factual (describes the approach without insulting), and evidence-linked (reader can verify).

### What NOT to say about competitors

- Never: "[competitor] is bad / weak / broken"
- Never: "[competitor] doesn't work"
- Never: "[competitor] is inferior" (without a specific measurable dimension)
- Allowed: "[competitor] does not ship [specific feature]. nox-mem ships it. See [PR]."

---

## 4. Number citation policy

### Every number must carry its source

Format: `NUMBER (context, source: LINK)`

Examples:
- `101ms p95 (mock LLM @ 100ms, search.medium workload; P1 bench, PR #40)` — correct
- `101ms p95` — incomplete (no context, no source)
- `fastest p95 ever` — not a number, not allowed

### Pending vs verified

Use explicit labels:

| Status | Label to use |
|---|---|
| Shipped, code in repo | *(no label needed; link to PR or file)* |
| Run but not in official gate | `(internal run, n=N, not yet in gate)` |
| Pending full benchmark run | `(pending Q1/Q2/Q3 gate)` |
| Competitor number (self-reported) | `(competitor self-reported; not independently verified)` |
| Competitor number (our run) | `(our run of [competitor] on [dataset]; see benchmark/)` |

### Numbers verified as of Wave B (2026-05-18)

These numbers can be stated without a pending label:

| Number | Label |
|---|---|
| 69,298 chunks (99.97% embedded) | live corpus 2026-05-17 |
| 15,646 entities / 21,533 relations | live corpus 2026-05-17 |
| nDCG@10 = 0.6813 (+9.8pp over paper baseline 0.5831) | run 85, post-cure golden, R01c-v1.1 |
| 4.0× over Anserini-tuned BM25 (nDCG 0.1475) | paper v1.1 baseline |
| 1.9× over multilingual-e5-base (nDCG 0.3070) | paper v1.1 baseline |
| p95 = 101.74ms (42× under 4.3s budget) | P1 bench, PR #40, mock LLM |
| 0.0025ms provider abstraction overhead | A3 bench, PR #39 |
| 95.8% precision/recall on L4 regex extraction | synthetic n=20, PR #38 |
| 80% Gemini calls eliminated by confidence gate | synthetic n=20, PR #38 |
| 11.7 KB viewer frontend bundle | P5, PR #42 |
| 535+ tests passing | Wave B CI |
| <$11/mo OPEX | actuals Mar–May 2026 |
| AES-256-GCM export, scrypt KDF | A2, PR #35 |
| 1.7% privacy filter false-positive rate, 68 tests | A1 shipped |
| +1.92pp nDCG from language-aware RRF | E14, Wave 1 D |

Numbers that require Q-gate (do NOT state as fact):

- LoCoMo R@5 (pending Q1)
- LongMemEval task accuracy (pending Q2)
- p95 against live corpus (pending Q3)
- Head-to-head competitor comparison (pending Q4)

---

## 5. Audience-specific framing

### Engineer-first (GitHub, HN, r/MachineLearning)

Lead with code and reproducibility.

Sequence:
1. One sentence: the specific technical problem
2. Two sentences: the technical approach (hybrid RRF, shadow mode, typed KG)
3. Numbers table (verified only, with sources)
4. Quick start code block
5. CTA: "Run the eval harness; disagreements welcome"

Avoid: investor framing, TAM, "market opportunity". Engineers hate this.

Example opener:
> "nox-mem is a hybrid memory engine for AI agents — FTS5 BM25 + Gemini 3072d vector + typed KG, RRF fused, local SQLite, provider-agnostic. Shadow discipline means every ranking change runs ≥7d baseline before activation. Internal nDCG@10 = 0.6813. LoCoMo full run pending."

### Founder-first (ProductHunt, LinkedIn, advisory conversations)

Lead with the moat and the positioning gap.

Sequence:
1. One sentence: the trade-off others force you to make
2. One sentence: how nox-mem refuses that trade
3. Three-bullet moat: (data autonomy, shadow discipline, transparent benchmarks)
4. Competitive map (one-line on each: memanto SaaS lock-in / agentmemory runtime lock-in / nox-mem neither)
5. CTA: "MIT license. Your data."

Avoid: deep benchmark methodology; low-level code. Founders want the positioning story.

Example opener:
> "Every agent memory system today forces a choice: SaaS lock-in (memanto, mem0 managed) or runtime lock-in (agentmemory/iii-engine, Letta). nox-mem is a SQLite file you own, portable across providers, with ranking changes that earn their way in via shadow discipline. MIT. No SaaS. No daemon."

### Investor-first (Galapagos conversations, advisory framing)

Lead with the category thesis and defensibility.

Sequence:
1. Category: "We are in the agent memory infrastructure category"
2. Timing: "Agents are the new applications. Memory is the new storage layer."
3. Moat: data autonomy + shadow discipline + transparent benchmarks = defensible differentiation
4. Competitive gap: "gbrain 16k stars but personal-brain focus / agentmemory 11k but runtime lock-in / memanto SaaS / nox-mem quality+autonomy gap"
5. Numbers: corpus, cost, verified benchmarks
6. Roadmap: Q/A/P pillars + Lab + GTM Phase 2 gate

Avoid: deep technical implementation. Investors want to understand the moat and the timing bet.

Example opener:
> "Memory infrastructure for AI agents. Every agent needs retrieval — most teams bolt on a half-baked solution or hand data to a SaaS. We think the market wants a local-first, auditable, provider-agnostic store that gets smarter without surprise regressions. We built one. The moat is shadow discipline: ranking changes don't ship until they prove it."

---

## 6. Social media specifics

### Twitter/X

- Lead tweet ≤ 280 chars: value claim + number + CTA
- No thread longer than 6 posts for launch content
- Avoid: tweetstorms that go nowhere. If the thread isn't building to a reveal, don't thread.
- Hashtags: `#LLM`, `#AIagents`, `#OpenSource` — max 2, never block text with hashtags

Template (verified numbers launch):
```
nox-mem: hybrid memory for AI agents.
Local SQLite · p95 = 101ms · <$11/mo
Shadow discipline: 7d baseline before any ranking change activates.

github.com/totobusnello/memoria-nox
```

### LinkedIn

- First sentence: bold claim (not a question — questions underperform)
- Max 150 words before "see more" fold
- One stat per paragraph, never more than 3 stats total
- End with CTA: GitHub link or "link in comments"
- No emoji storms; 0–2 emojis total is the ceiling

### GitHub README badges

- Only badges for verified, real-time data: license, CI status, star count, paper version
- No badges for pending-gate numbers
- No "made with AI" or similar process badges

---

## 7. What the brand is not

Maintain these negatives explicitly — the brand is defined as much by what it refuses as what it claims:

| NOT this | IS this |
|---|---|
| "Ship fast, fix later" | "Shadow discipline: measure first" |
| "AI-powered [everything]" | "Hybrid retrieval with verifiable methodology" |
| "Enterprise ready" (without a customer) | "MIT open-source, production-disciplined" |
| "The memory layer for your LLM" (generic) | "The memory layer for your agent — your data, your disk" |
| Comparison without evidence | Evidence before comparison |
| Features without numbers | Numbers before features |
| Numbers without sources | Every number cites a PR or file |
| "We will" / "coming soon" | "Shipped" / "specced" / "pending Q-gate" (explicit status) |

---

## 8. The honesty contract

nox-mem's brand authority rests on being the project that says what it actually measures. Break this once in public and the trust takes years to rebuild. The rules:

1. Pending-Q-gate numbers are labeled every time they appear in public content
2. Competitor comparisons wait for COMPARISON.md to be filled with real data (Q4 gate)
3. "Winning" a benchmark means publishing; "losing" means internal work only
4. If a number changes, update all public content within one business day
5. "We don't know yet" is always allowed and always preferred over a fabricated estimate

This is not caution. It is the competitive advantage. Hacker News, arXiv reviewers, and technical founders are good at detecting inflated claims. The team that says "here is what we measured, here is the methodology, here is where we are not sure" wins their trust permanently.

---

## 9. Quick reference card

Paste this wherever copy is being written:

```
TAGLINE (exact): Pain-weighted hybrid memory with shadow discipline — yours by design.

PILLARS:
  Q: Numbers that lead
  A: Data is yours, completely
  P: Memory that shows up where you work

NUMBERS (verified, cite PR when using):
  69k chunks · 15k entities · 21k relations
  nDCG@10 = 0.6813 (+9.8pp baseline)
  p95 = 101ms (mock LLM, P1 bench)
  provider overhead = 0.0025ms (A3 bench)
  <$11/mo OPEX (actuals)
  535+ tests (Wave B)
  11.7KB viewer bundle (P5)

PENDING (do NOT state as fact):
  LoCoMo R@5, LongMemEval accuracy,
  live-corpus p95, competitor comparison table

COMPARISON RULE:
  "Where X does [A], nox-mem does [B] — [evidence]."
  Never: "X is bad/inferior/broken."

AUDIENCE LEAD:
  Engineer: code + numbers
  Founder: moat + positioning gap
  Investor: category thesis + defensibility
```
