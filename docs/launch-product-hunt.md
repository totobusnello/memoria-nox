# nox-mem — Product Hunt Launch Brief

> **Schedule:** Tue 2026-06-02 at 23:55 PST (Wed 2026-06-03 at 03:55 BRT)
> **Categories:** Artificial Intelligence / Developer Tools / Open Source
> **Topics:** ai-agents, llm, memory, rag, sqlite, open-source

---

## Listing copy

### Title (57 chars)

```
nox-mem: Pain-weighted hybrid memory for AI agents
```

**Alternates (all under 60 chars):**

```
nox-mem — Hybrid memory for LLM agents. Your SQLite.
nox-mem: Open-source agent memory. FTS5+Gemini+RRF.
```

---

### Tagline (52 chars — within 60-char limit)

```
Hybrid LLM memory. Your SQLite. Your provider. MIT.
```

**Alternates:**

```
Open-source, pain-weighted, FTS5+Gemini+RRF. MIT.    (51 chars)
Hybrid agent memory. Local SQLite. Zero vendor lock.  (53 chars)
```

---

### Description (~400 words)

LLM agents have a memory problem: every session ends with amnesia. The fix the industry offers is usually one of two bad trades — send your data to a vendor's cloud, or self-host a vector store and discover it fails on natural-language queries.

**nox-mem** is a third path.

It stores everything in a single SQLite file on your disk. You can `cp nox-mem.db backup.db` and that's your backup. No daemon, no cloud dependency, no vendor in the middle.

**The retrieval stack is three-layer hybrid:**

1. FTS5 BM25 — keyword recall, fast, no embedding call needed
2. Gemini dense embeddings (3072d, stored in sqlite-vec) — semantic recall, multilingual
3. RRF fusion (k=60, language-aware weights) — fuses both without noise amplification

On top sits a pain-weighted salience formula: `salience = recency × pain × importance`. Each chunk carries a `pain` field (0.1 trivial → 1.0 production outage). High-pain memories rank higher and decay more slowly. A critical incident stays retrievable years later, even when it's no longer recent.

Every ranking change ships in shadow-mode first — at least 7 days of baseline observation before it influences any real query. The G-series ablation log (G3 through G12, 10 gated experiments) is published in DECISIONS.md, including the changes that were cut.

**Benchmark numbers (eval-isolated, public harness):**

- LoCoMo nDCG@10: **0.6380** (+78.8% vs G3 baseline)
- LongMemEval n=100: nDCG@10 = **0.9126**, MRR = **0.9162**
- p50 latency: **8ms** (FTS5-hybrid path on eval corpus)
- Cross-system partial (Sat 2026-05-24): nox-mem 65% hit-rate / 8ms p50 vs mem0 15% hit-rate / 273ms p50 at full corpus (different corpus sizes — honest disclosure in COMPARISON.md)

The full 6-system canonical comparison (LoCoMo + LongMemEval × 6 systems, uniform corpus) ships in COMPARISON.md before launch. Every result, including unfavorable rows, will be in that table.

**What you get:**

- 26-command CLI (`nox-mem search`, `nox-mem answer`, `nox-mem ingest-entity`, ...)
- 16-tool MCP server for Claude Code / Cursor
- HTTP API (port 18802) with `/api/answer`, `/api/search`, `/api/kg/path`, `/api/health`
- Knowledge graph: 15,646 entities, 21,533 typed edge relations (incremental, nightly)
- MIT license. No telemetry. No call-home.

```bash
npm install -g nox-mem
export GEMINI_API_KEY=sk-...
nox-mem init ~/my-memory
nox-mem search "what did I decide about auth last month?"
```

Requires Node 20+. SQLite bundled. Bring your own embedding provider (Gemini default; OpenAI and Ollama adapters available).

arXiv paper (cs.IR, v1.1): submitted Tue 2026-06-02, available Wed 2026-06-03.

---

## Maker first comment

> Posted by Toto Busnello within 5 minutes of launch. Target: under 800 chars.

---

**Draft:**

Hey — I'm Toto, the solo author. Happy to answer anything.

Quick context on why this exists: I run 6 LLM agent personas simultaneously on a Hostinger VPS, all sharing the same memory index. After several months of watching agents fail to retrieve critical lessons from incidents — not because the retrieval was wrong, but because "recency" isn't the right signal for high-stakes decisions — I built a `pain` field into the schema and a salience formula to go with it.

The "shadow discipline" piece came from a bad experience: a ranking change I deployed directly caused a -32.29% regression before I caught it (PR #176, reverted). Now every scoring change runs against a production baseline for at least 7 days before activation, with metrics exposed at `/api/health`. The G-series ablation log (10 rounds) is published in DECISIONS.md — including the experiments I killed.

The benchmark methodology is open: eval harness in `eval/q4-comparison/runner.py`, golden queries in `eval/golden-queries.jsonl`, isolation enforced via `NOX_DB_PATH` guard. Run it yourself. I'd genuinely like to know if your setup produces different numbers.

What would be most useful to you — feedback on the retrieval design, the salience formula, the MCP integration, or something else?

---

## Gallery plan (4 slides, 1270×760 PNG)

All source screenshots are in `docs/press-kit/05-screenshots/`.

| Slide | File | Caption |
|---|---|---|
| 1 | `f10-phase-a-health.png` | `/api/health` — real-time observability: vector coverage, ops_audit status, G-series boost stack |
| 2 | `f10-phase-b-evals.png` | Eval dashboard — nDCG@10 = 0.6380, p50 = 8ms, 65% gold-hit (LoCoMo + LongMemEval combined) |
| 3 | `f10-phase-c-telemetry.png` | Search telemetry — per-query breakdown: BM25 / semantic / RRF fusion / salience trace |
| 4 | `f10-phase-d-shadow.png` | Shadow discipline — ranking change held in shadow for 7 days, metrics live before activation |

**Additional assets needed (fill by Sat 2026-05-30):**

- [ ] **Logo (240×240 PNG):** crop from README hero SVG or use `docs/press-kit/06-logo-and-brand.md` spec
- [ ] **Thumbnail / OG image (630×400 PNG):** hero with tagline overlay
- [ ] **Demo GIF:** `nox-mem search` + `nox-mem answer` in one 30-second terminal recording (plan in `docs/launch-demo-plan.md`)
- [ ] **Animated header video (optional):** defer to Sun 2026-06-01

---

## Scheduling checklist

```
Tue 2026-06-02
  09:00 BRT — arXiv submission (must be before 14:00 UTC for Wed listing)
  20:00 BRT — Twitter tease thread (T1 + T2, no PH link yet)
  22:00 BRT — HN/Reddit heads-up ("Show HN going live in ~6h")
  23:00 BRT — Final asset check: logo, gallery, GIF, description copy
  23:55 PST  ←  PH scheduled publish (= Wed 03:55 BRT)

Wed 2026-06-03
  03:55 BRT — PH goes live (verify immediately)
  04:00 BRT — Post Maker first comment (within 5 min)
  04:00 BRT — Post Show HN thread
  04:15 BRT — Personal network rally message (email/WhatsApp, see §Rally script)
  07:15 BRT — LinkedIn post + Twitter thread links (peak BR professional hour)
  10:00 BRT — Check PH ranking; decide whether to push extra rally wave
  13:55 BRT — 10h mark: assess daily ranking position
```

**PH scheduling note:** PH resets daily rankings at 00:00 PST. Scheduling at 23:55 PST on Tue gives ~24h of full vote window starting at the very top of the Wed cycle. Do NOT schedule at 00:05 PST — the 5-min gap matters for first-mover placement in the daily feed.

---

## Vote rallying script (PH ToS compliant)

PH prohibits vote-begging ("please upvote"). What is allowed: genuine sharing, feedback asks, community engagement.

**Personal network message (WhatsApp/Telegram, ~100 words):**

```
Hey — launching nox-mem today on Product Hunt.

It's an open-source hybrid memory system for LLM agents — stores
everything in a local SQLite file, no vendor dependency.

If it's useful, I'd love feedback more than upvotes. Comments
on the PH thread help a lot (even critical ones).

→ [PH link]

If you've been using it or thinking about this problem, would
appreciate your honest take — positive or negative.
```

**Email to technical contacts (~50 words):**

```
Subject: nox-mem on Product Hunt — feedback appreciated

Launching nox-mem today: open-source hybrid memory for LLM agents
(FTS5 + Gemini + RRF, MIT, local SQLite).

Would appreciate your honest feedback more than upvotes.
→ [PH link]

Happy to discuss the retrieval design or benchmark methodology.
```

**Twitter launch tweet (Tue 20:00 BRT tease):**

```
Pain-weighted hybrid memory for LLM agents — launching Wed on Product Hunt.

SQLite on your disk. Provider your choice. Zero vendor lock-in.
MIT license.

→ github.com/totobusnello/memoria-nox

(nDCG@10 0.6380, p50 8ms, 65% gold-hit on Q4 smoke — details in thread)
```

**LinkedIn (Wed 07:15 BRT, more context):**

```
Launching nox-mem today — hybrid memory for LLM agents.

Built this after 6 months of running 6 agent personas simultaneously
on a VPS, watching them fail to retrieve critical lessons from
high-severity incidents. The problem wasn't recall — it was that
recency alone is the wrong signal for pain-weighted decisions.

Three pillars:
→ Quality: FTS5 BM25 + Gemini 3072d + RRF fusion. Benchmark harness public.
→ Autonomy: local SQLite, your provider, MIT license.
→ Product: 26-cmd CLI, MCP server, HTTP API, answer primitive.

Numbers: nDCG@10 0.6380, p50 8ms (Q4 smoke, eval-isolated).
Cross-system comparison (mem0, Letta, agentmemory): docs/COMPARISON.md.

Product Hunt: [link]
Repo: github.com/totobusnello/memoria-nox
Paper (arXiv cs.IR): [link]
```

**4-hour vote rally blocks:**

| Block | Action | Channel |
|---|---|---|
| Tue PM 20:00 BRT | Tease tweet thread (T1+T2) | Twitter |
| Wed 04:00 BRT | Launch + Maker comment | PH |
| Wed 04:15 BRT | Personal network message | WhatsApp/Telegram/Email |
| Wed 07:15 BRT | LinkedIn post + Twitter full thread | LinkedIn/Twitter |
| Wed 10:00 BRT | Assess ranking — second wave if <15th place | Discord/Slack communities |
| Wed 13:00 BRT | HN Show HN thread live | HN |
| Wed 16:00 BRT | Reddit r/MachineLearning | Reddit |

---

## Response readiness — Top 10 PH anticipated comments

These are pulled from `docs/launch-hn-comments-prep.md` (18-comment deep prep) — adapted for PH tone (less hostile than HN, but same technical depth).

| # | Comment pattern | Key response |
|---|---|---|
| 1 | "How is this different from Mem0/Zep?" | 3 concrete differences: open benchmarks, MIT+local, triple-stack retrieval. Link COMPARISON.md. |
| 2 | "Why SQLite? Doesn't scale." | Deliberate tradeoff: single-file, zero ops, exact search. Documented ceiling ~500k chunks. ROADMAP.md. |
| 3 | "Pain-weighted is a gimmick / overfitting." | G7 ablation: formula is NEUTRAL on eval corpus (+0.5% noise). Value is structured signal + interpretability, not dramatic re-rank. |
| 4 | "Your benchmarks are rigged / self-reported." | Run them yourself: `eval/q4-comparison/runner.py`. Golden queries in repo. EverMemBench: Lab Q1. |
| 5 | "Bus factor = 1 / solo project risk." | MIT: anyone can fork. Architecture documented (paper + ADRs). Commercial track (nox-supermem) is the economic incentive. Honest state. |
| 6 | "Gemini dependency = vendor lock-in too." | Provider is configurable via .env — OpenAI + Ollama adapters exist. DB format and KG are provider-agnostic. |
| 7 | "mem0 beats you in the apples-cap comparison." | Yes — we published both rows because either alone misleads. mem0 wins concentration at small corpora (LLM rewriting is real). nox-mem wins coverage+speed+cost at scale. |
| 8 | "MIT license today, commercial clause later?" | MIT in git history. Commercial track is a separate product (nox-supermem). nox-mem stays MIT. |
| 9 | "Latency p99 2.5s is terrible." | Context: 2.5s p99 = Gemini API call. FTS5-only is 7-12ms p50. Async memory consolidation (primary use case) tolerates hybrid latency. Local Ollama drops to ~100-200ms. |
| 10 | "How does the pain field get assigned? Manual?" | Can be manual (frontmatter at ingest) or inferred (default 0.2). LLM-assisted estimator at ingest is P-roadmap, gated on Q4 wins first. |

**Full prep with verbatim replies:** `docs/launch-hn-comments-prep.md`

---

## Toto's bandwidth note

**6h block reserved Wed 2026-06-03:** 04:00–10:00 BRT for live PH thread responses.

Priority triage:
- Reply within 30 min: any top-level comment with 3+ upvotes
- Reply within 2h: valid technical critique
- Reply within 4h: comparison/benchmark challenge
- Single reply max or ignore: clear troll / no engagement

**Tone:** terse + technical. Cite specific evidence. Acknowledge real limitations early. "Fair point — here's the honest tradeoff" beats defensive spin every time.

---

## Asset status (as of 2026-05-23)

| Asset | Status | Action needed |
|---|---|---|
| Gallery 1: `f10-phase-a-health.png` | Ready | Verify 1270×760 crop |
| Gallery 2: `f10-phase-b-evals.png` | Ready | Verify 1270×760 crop |
| Gallery 3: `f10-phase-c-telemetry.png` | Ready | Verify 1270×760 crop |
| Gallery 4: `f10-phase-d-shadow.png` | Ready | Verify 1270×760 crop |
| Logo (240×240 PNG) | Needed | Crop from README hero — Sat 2026-05-30 |
| Thumbnail OG (630×400 PNG) | Needed | Hero + tagline overlay — Sat 2026-05-30 |
| Demo GIF | Needed | Terminal recording — Sat 2026-05-30 |
| Animated header video | Optional | Defer to Sun 2026-06-01 |
| COMPARISON.md final numbers | Pending | Canonical 6-system run (4 adapters still in setup as of Sat 2026-05-24) |

---

## PH submission form values

| Field | Value |
|---|---|
| Product name | nox-mem |
| Tagline | Hybrid LLM memory. Your SQLite. Your provider. MIT. |
| Website | https://github.com/totobusnello/memoria-nox |
| Categories | Artificial Intelligence, Developer Tools, Open Source |
| Topics | ai-agents, llm, memory, rag, sqlite, open-source |
| Maker | Toto Busnello |
| Launch date | Wed 2026-06-03 (schedule: Tue 2026-06-02 23:55 PST) |
| Social preview | Press kit README hero image |

---

*Internal refs: `docs/launch-social-copy.md §3` (PH copy source) · `docs/launch-hn-comments-prep.md` (18-comment response prep) · `docs/press-kit/05-screenshots/` (gallery source files) · `docs/launch-blog-v0-draft.md` (narrative source) · `docs/launch-day-checklist-2026-06-03.md` (day-of ops)*
