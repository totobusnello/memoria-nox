# HN Show HN — Final Content + Timing Decision

> **Launch: Wed 2026-06-03**  
> Status: FINAL — copy-paste ready for launch day  
> Last updated: 2026-05-23

---

## §1 — Title decision

### Candidates evaluated

| # | Title | Character count | Assessment |
|---|---|---|---|
| A | `Show HN: nox-mem – Pain-weighted hybrid memory for AI agents (MIT, open benchmarks)` | 84 | "pain-weighted" needs explanation; "AI agents" is broad; "open benchmarks" is good signal |
| B | `Show HN: nox-mem – LoCoMo conversational memory +40% vs mem0 at same corpus size` | 81 | Specific + honest + reproducible; BUT % claims in titles attract "show me the methodology" heat; needs immediate maker comment to pre-empt |
| C | `Show HN: nox-mem – Open-source SQLite+FTS5+Gemini agent memory (8ms p50, 65% hit-rate)` | 90 | Stack-technical (HN respects this); latency number is concrete; hit-rate needs definition in body |
| D | `Show HN: nox-mem – Hybrid memory layer for AI agents (BM25 + semantic + KG, MIT)` | 80 | Technically accurate + concise; no benchmark claim; stack is the hook; HN-safe |
| E | `Show HN: nox-mem – SQLite-based hybrid memory for LLM agents (FTS5 + vec0 + RRF)` | 80 | Most technically precise; targets engineers who know what RRF means; no marketing |

### WINNER: **Title E** (recommended) + **Title D** as fallback

**Rationale:**

`Show HN: nox-mem – SQLite-based hybrid memory for LLM agents (FTS5 + vec0 + RRF)`

- HN's best-performing Show HN titles are **technical nouns, not claims**. "FTS5 + vec0 + RRF" signals serious retrieval engineering to the audience that matters.
- No benchmark % in the title prevents the "misleading headline" flag before the thread even starts.
- SQLite signals autonomy + simplicity — deliberate architecture, not naivety.
- LLM agents is the precise use case (not "AI" which is noise).
- 80 chars — HN renders up to ~100 without truncation; this is safe.

**Fallback (if E feels too jargon-heavy):**

`Show HN: nox-mem – Hybrid memory layer for LLM agents (BM25 + semantic + KG, MIT, open evals)`

This variant adds "open evals" to signal reproducibility. MIT signals license without needing a separate badge.

**Do NOT use Title B as the main title.** "+40% vs mem0" in the title invites the full benchmark scrutiny before the maker comment is posted. The number is honest but needs the corpus-ordering caveat immediately adjacent. Title + maker comment is the correct pairing.

---

## §2 — URL

**Submission URL:** `https://github.com/totobusnello/nox-mem`

HN convention for code launches: link to the GitHub repo, not the blog post. The blog post / arXiv link goes in the body (text box below the URL). HN's own Show HN guidelines confirm: "link to the project itself."

Do not link to the arXiv paper as primary — it reads as "this is an academic submission" not "this is a tool you can use today."

---

## §3 — Submission body (HN text box, optional)

HN's text field is plain text, no Markdown. Keep it short — HN doesn't surface long bodies well; the maker comment is where detail goes.

```
nox-mem is a hybrid memory layer for LLM agents: BM25 (FTS5) + dense semantic search (Gemini/Ollama) + knowledge graph (RRF fusion), all inside a single SQLite file. No hosted backend, no daemon, no vendor lock-in.

Stack: TypeScript, better-sqlite3, sqlite-vec (vec0 extension), FTS5, Gemini embeddings (or any OpenAI-compatible provider). MIT licensed.

Motivation: I needed agent memory that works fully offline, on a 1 vCPU VPS, where I own the SQLite file. All existing tools either required a cloud backend or were vector-only.

Benchmarks (open, reproducible): nDCG@10 = 0.6237 on our production corpus (68k chunks), +40% vs mem0 on LoCoMo conversational memory at matched corpus size. Full methodology + eval harness in benchmark/. Happy to be challenged on the numbers — runner.py is in the repo.

Paper: [arXiv link — to be filled Wed morning]

Would love feedback on: (1) the FTS5 + vec0 + RRF fusion approach vs alternatives, (2) whether the open benchmark protocol is sound, (3) what use cases you'd want this to cover that it doesn't today.
```

**Note:** Fill the arXiv link before submitting. If arXiv ID hasn't arrived by 07:00 BRT, submit without it and edit the maker comment to add it when available (HN allows edits within ~1 hour of posting).

---

## §4 — Maker first comment (POST WITHIN 60 SECONDS of submission)

This is the most important piece. It sets tone, pre-empts the main objections, and gives HN the maker's honest framing before anyone else frames the project.

**Target length:** 180–220 words. Dense, no fluff.

---

### FINAL MAKER COMMENT COPY

```
Author here. Happy to go deep on any of this.

A bit of context: I started nox-mem because I was running LLM agents on a 1 vCPU / 2GB VPS and every memory tool I tried either phoned home, required a Docker stack, or was vector-only. I wanted memory that's a SQLite file — yours, portable, zero ops.

The retrieval architecture is the interesting part: three layers (BM25 via FTS5, dense via sqlite-vec/Gemini, knowledge graph via sqlite entity relations), fused with RRF (k=60). The intuition is that BM25 handles exact keyword recall that dense misses, dense handles paraphrase, and KG handles entity-hop queries. None of the three is consistently best alone.

On benchmarks — I want to be upfront: the +40% vs mem0 on LoCoMo is at matched corpus size (500 chunks), conversational queries only. The aggregate number (all query types, same 500-chunk cap) is 0.0918 vs mem0's 0.1315 — a loss — because of a corpus-ordering artifact explained in benchmark/COMPARISON.md. I publish both rows because either alone misleads. Run it yourself: benchmark/runner.py.

What I'd most value feedback on:
- Is the FTS5 + vec0 + RRF approach the right tradeoff, or am I missing something obvious?
- Is the eval protocol sound? Full methodology in benchmark/README.md.
- What would need to change for you to actually use this?

Paper (full methodology + ablations): [arXiv link]
```

**Word count:** ~210 words. Within target.

**Why each section earns its place:**

- *"1 vCPU / 2GB VPS"* — immediately concrete. HN respects operational specificity.
- *"SQLite file — yours, portable, zero ops"* — Autonomy pillar in plain English. No jargon.
- *"BM25 / dense / KG / RRF"* — technical signal. Engineers who know RRF will lean in. Engineers who don't will learn something.
- *The benchmark caveat paragraph* — this is the critical one. Posting the 0.0918 vs 0.1315 aggregate loss alongside the LoCoMo win before anyone challenges it is the move. It reads as intellectual honesty, not weakness. The alternative (waiting to be called out) reads as hiding.
- *"Run it yourself"* — reproducibility is the Autonomy pillar operationalized.
- *"What I'd most value feedback on"* — three specific asks, not "what do you think?" HN readers like specific prompts.

---

## §5 — Timing analysis and decision

### Current plan (from playbook)
`07:15 BRT = 06:15 ET` — HN submission

### HN peak windows (ET)
- **Best:** 09:00–12:00 ET (HN front page at full velocity)
- **Good:** 07:00–09:00 ET (engineers on East Coast starting day — less competition, can ride to peak)
- **Weak:** 05:00–07:00 ET (too early; West Coast asleep; East Coast commuting)
- **Dead:** 00:00–05:00 ET

### 06:15 ET assessment
06:15 ET is **weak** — East Coast is commuting, West Coast is asleep or just waking. Posts at 06:15 ET that don't immediately accumulate votes can slip off the "new" queue before the HN peak audience sees them. Show HN has a separate "new" feed, but velocity in the first 30–60 minutes still matters for front page placement.

### Channel sequencing constraint
| Time BRT | Channel | Notes |
|---|---|---|
| 05:01 | Product Hunt live | Votes count from 00:01 PST; 06:00 BRT is critical window |
| 07:00 | Twitter thread | East Coast US morning; optimal |
| 07:15 | **HN (current)** | 06:15 ET — weak window |
| 07:30 | Reddit r/ML | Post-HN cross-channel |
| 11:00 | LinkedIn | Different audience |

### Option A: Keep 07:15 BRT (current plan)
- **Pro:** Minimal schedule change. Within the "acceptable" 06:00–08:00 ET window cited in the playbook.
- **Pro:** 7h gap to LinkedIn; doesn't dilute cross-posting signal.
- **Con:** 06:15 ET is sub-optimal vs 09:00 ET peak. 
- **Con:** If first 45 minutes yield <5 points, post may not catch the peak wave.

### Option B: Shift HN to 10:00 BRT (09:00 ET) — RECOMMENDED
- **Pro:** 09:00 ET = engineers at desk, coffee in hand, HN tab open. Highest Show HN velocity window.
- **Pro:** 5h gap since PH launch — enough PH momentum is established before HN.
- **Pro:** Twitter thread at 07:00 BRT warms the audience; HN 3h later benefits from any Twitter traffic.
- **Con:** 2h45min gap between Twitter and HN could feel like a slow burn. Minor.
- **Con:** If HN accumulates points quickly, you'll be responding to comments at 11:00–14:00 BRT, overlapping with LinkedIn post at 11:00.

### Option C: Shift HN to 11:00 BRT (10:00 ET)
- **Pro:** 10:00 ET is the statistical sweet spot for maximum concurrent HN users.
- **Pro:** Blog post at 09:00 BRT → HN at 11:00 BRT creates a content wave.
- **Con:** By 11:00 BRT you'll have been responding to PH comments for 5h. Cognitive load risk for a solo operator.
- **Con:** HN comment replies will now run to 18:00+ BRT, long day.

### DECISION: **Option B — HN at 10:00 BRT (09:00 ET)**

**Updated timeline:**

| Hora BRT | Hora ET | Ação |
|---|---|---|
| 05:01 | 04:01 | Product Hunt live (auto) |
| 06:00 | 05:00 | Confirm PH live + first maker comment |
| 06:30 | 05:30 | VPS health check |
| 07:00 | 06:00 | Twitter thread T1 |
| 07:05 | 06:05 | T2–T9 in sequence |
| 07:30 | 06:30 | Reddit r/ML |
| 07:45 | 06:45 | Reddit r/LocalLLaMA (if applicable) |
| **10:00** | **09:00** | **HN Show HN submitted ← SHIFTED from 07:15** |
| 10:01 | 09:01 | **Maker first comment posted (within 60s)** |
| 10:30 | 09:30 | First HN replies (top comments by this point) |
| 11:00 | 10:00 | LinkedIn announcement |
| 11:00–18:00 | 10:00–17:00 | Active reply window: HN / Twitter / Reddit |

**Rationale for 10:00 BRT vs 11:00 BRT:** solo operator — 10:00 BRT gives 2h to warm up before LinkedIn at 11:00, and the peak HN response window (10:00–14:00 BRT) aligns with full alertness. 11:00 BRT would push the active reply window to late afternoon with 6h of PH fatigue already accrued.

---

## §6 — Pre-post checklist (execute Tue 2026-06-02 night)

### GitHub repo
- [ ] GitHub repo loads at < 2s in incognito tab (no 500s, no redirect loops)
- [ ] README hero visible without scrolling: title + tagline + badge (license) + demo GIF or screenshot
- [ ] LICENSE file visible in repo root (MIT confirmed)
- [ ] CONTRIBUTING.md accessible from README
- [ ] At least 3 GitHub Discussions seeded and interesting (not empty "welcome" stub)
- [ ] Issues tab: at least 3 pinned issues that are interesting engineering questions, not bug reports

### Benchmark / eval
- [ ] `benchmark/COMPARISON.md` has both the LoCoMo-only row (+40%) AND the aggregate@500 row (0.0918 vs 0.1315) — both rows must be present, neither buried
- [ ] `benchmark/runner.py` runs without errors on a clean `pip install` (test locally)
- [ ] `eval/README.md` explains the protocol (FTS5-fair isolation, NOX_DB_PATH guard)
- [ ] arXiv link correct in README badge (test in incognito — must resolve)

### Content
- [ ] HN submission body saved locally (copy from §3 above)
- [ ] Maker first comment saved locally (copy from §4 above), arXiv link filled in
- [ ] `docs/launch-hn-comments-prep.md` reviewed — Q1, Q2, Q4, Q16, Q19, Q20 replies ready for copy-paste

### Infra
- [ ] VPS: `curl http://127.0.0.1:18802/api/health | jq .vectorCoverage` — embedded == total
- [ ] `/api/answer` smoke test: one query, < 3s, returns real content
- [ ] F10 dashboard screenshots visible in README or linked from press kit

### Day-of execution
- [ ] 10:00:00 BRT — open `https://news.ycombinator.com/submit` in browser, paste title + URL + body
- [ ] 10:00:30 BRT — submit
- [ ] 10:01:00 BRT — immediately post maker comment (§4 copy) on the new thread
- [ ] 10:05:00 BRT — verify comment appeared; refresh thread
- [ ] Set 30-min timer to check first comments; set 2h timer for full reply sweep

---

## §7 — Crisis protocols (HN-specific)

| Scenario | Response |
|---|---|
| Post flagged within first hour | Wait 30min (auto-unflag sometimes). Contact `hn@ycombinator.com` with subject "Show HN flag review" + link. Do NOT resubmit same day. |
| Post gets 0 points in first 30min | Not unusual — HN new queue moves fast. Post maker comment. Share HN link in Twitter replies (T-thread has the audience). |
| Aggregate 0.0918 number gets aggressive challenge | Use Q20 reply from `docs/launch-hn-comments-prep.md` verbatim — it's calibrated. Do not improvise. |
| LoCoMo +40% challenged as cherry-pick | Use Q19 reply. Say "both rows are in COMPARISON.md" and link. Never delete the reply. |
| Maker comment doesn't appear (HN delay) | Reload the thread. HN comments sometimes delay 30–60s. If still missing after 2min, repost (same text). |

---

## §8 — What NOT to include in the submission

- No "revolutionary" / "state-of-the-art" / "best" language
- No comparison to competitors in the title
- No percentage claims in the title (save for maker comment where context is adjacent)
- No emojis (HN strips or penalizes visual noise)
- No "🚀 launching today" in the body text
- Do not link to a landing page or marketing site as primary URL — GitHub repo only

---

*Última atualização: 2026-05-23 · Decisão timing: HN shifted 07:15 → 10:00 BRT (09:00 ET) · Title winner: E (SQLite-based hybrid memory for LLM agents FTS5+vec0+RRF) · Maintainer: Toto Busnello*
