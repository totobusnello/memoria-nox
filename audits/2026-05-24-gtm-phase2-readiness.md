# GTM Phase 2 — Launch Readiness Audit
**Date:** 2026-05-24 (Sat EOD)  
**Auditor:** Sisyphus-Junior (executor agent)  
**Launch target:** Wed 2026-06-03 10h BRT  
**Days remaining:** 10  
**Gate status:** D43 VERIFIED — nDCG@10 0.6380 (+83.0% vs G3 baseline 0.3487; threshold ≥+15% cleared by 68pp)

---

## Executive Summary

GTM Phase 2 is **GO-WITH-GAPS**. The technical gate (D43) is firmly cleared. The launch day checklist, social copy, blog post, HN prep, press kit, outreach templates, FOSS hygiene, GitHub repo metadata, and CI are substantially complete. **Three material gaps block a clean launch:** (1) demo GIF not recorded, (2) COMPARISON.md has 10+ `[PENDENTE Sat full run]` cells — competitor cross-system numbers are smoke-only, not canonical, (3) arXiv paper has 8 TBD cells in Table 8 (per-category breakdown) and the LaTeX build needs a clean PDF submit package. A fourth gap — `v1.0.0-rc1` git tag not pushed — is a 2-minute fix.

All other launch-day assets exist as drafts with real numbers embedded. Crisis plans, timing runbook, and outreach templates are publication-quality.

---

## §1 Inventory — GTM-Readiness Artifacts

### A. Core content (PRs merged)

| Asset | PR | Status | Notes |
|---|---|---|---|
| Blog post v0 draft (`docs/launch-blog-v0-draft.md`) | #221 | ✅ READY | Real Q4 smoke numbers embedded (0.6380, 12ms); honesty disclosure on run status included |
| Social copy — Twitter T1-T8, HN body, Reddit, PH (`docs/launch-social-copy.md`) | #224 | ✅ READY | arXiv link placeholder only (expected — needs Tue ID); all other copy final |
| Paper §5+§6 skeleton | #226 | ✅ READY | §5 cravado; §6 per-category cells TBD (8 rows, see §3B) |
| Launch day checklist hour-by-hour (`docs/launch-day-checklist-2026-06-03.md`) | #227 | ✅ READY | Comprehensive §1-§7: pre-flight, timeline, crisis plans, verification, retrospectiva |
| HN combative comments prep (`docs/launch-hn-comments-prep.md`) | #244 | ✅ READY | 15 hostile questions + tone calibration |
| Outreach templates (`docs/outreach-templates.md`) | #246 | ✅ READY | §2 journalist (TechCrunch/Verge, AI/ML press) + §3 podcast + §4 newsletter |
| Press kit 9 files (`docs/press-kit/`) | #248 | ✅ READY | fact-sheet, bio, elevator pitches, quotes, logo+brand, tech deep dive, interview Qs, investor one-pager; screenshot placeholder note |
| Use cases (`docs/USE-CASES.md`) | #245 | ✅ READY | 10 concrete agent memory patterns |
| QUICKSTART.md | #236 | ✅ READY | 5-min install + try guide |
| TUTORIAL.md | #250 | ✅ READY | Step-by-step build first agent |
| ARCHITECTURE.md | #240 | ✅ READY | HN technical audience |
| COMPARISON.md skeleton (`docs/COMPARISON.md`) | #279 | ⚠️ INCOMPLETE | nox_mem smoke numbers filled; 10+ competitor cells `[PENDENTE Sat full run]` |
| README hero | #297 (open) | ⚠️ INCOMPLETE | PR open; hero updated with 0.6380 + 8ms p50; demo GIF slot still placeholder |
| arXiv submit checklist (`docs/arxiv-submit-checklist.md`) | direct | ✅ READY | Full §1-§3 runbook; submit Tue 06-02 sequence clear |
| arXiv abstract (`paper/abstract.md`) | #239 | ✅ READY | ≤300 words, cs.IR target |

### B. Infrastructure / CI / Security

| Asset | PR | Status | Notes |
|---|---|---|---|
| GitHub Actions workflows (lint/typecheck/eval/security/release) | #251 | ✅ READY | All green per `audits/2026-05-22-pre-launch-security-review.md` |
| Pre-launch checker script (`scripts/check-pre-launch.sh`) | #258 | ✅ READY | 10-check battery; exit 0/1/2 |
| Pre-launch security review (CLEAN verdict) | #242 | ✅ READY | `audits/2026-05-22-pre-launch-security-review.md` — GO verdict |
| VPS healthcheck cron 15min | #164 | ✅ READY | Tailscale-aware; current IP 187.77.234.79 |
| Docker / Codespaces | #68/#256 | ✅ READY | Dockerfile + devcontainer |
| OpenAPI spec | #252 | ✅ READY | OpenAPI 3.1 |
| Postman collection | #264 | ✅ READY | v2.1.0 |
| Self-host guide | #263 | ✅ READY | Production deployment |
| FOSS hygiene (LICENSE / CONTRIBUTING / CODE_OF_CONDUCT / SECURITY / CITATION.cff) | #222 | ✅ READY | All 5 present on disk |
| F10 Observability (Phase A+B+C+D) | #206+#207+#267+#283+#291 | ✅ READY | Telemetry LIVE prod (5/5 smoke); Phase D shadow tracker merged |
| OpenSSF Best Practices badge | — | ✅ READY | Badge in README (project #12896) |

### C. Paper / arXiv

| Asset | Status | Notes |
|---|---|---|
| Paper MD (`paper/paper-tecnico-nox-mem.md`) | ✅ READY (0 TBD markers) | Full prose; canonical G5 V3 0.6237 + G10d numbers |
| LaTeX main.tex (`paper/publication/latex/main.tex`) | ⚠️ INCOMPLETE | 8 TBD cells in Table 8 (per-category entity breakdown from G12 R01b); PDF compiles |
| refs.bib | ✅ READY | LightRAG authorship corrected (PR #243 rescue c516cc5) |
| PDF artifact | ✅ READY | `paper/publication/latex/pain-shadow-memory-2026.pdf` + `paper.pdf` exist |
| arXiv metadata | ✅ READY | `paper/publication/arxiv-submit-metadata.md` — all fields filled; ORCID optional |
| xelatex wrapper script | ✅ READY | PR #238 |

### D. GitHub / Social / Distribution

| Asset | Status | Notes |
|---|---|---|
| Repo description | ✅ READY | "Pain-weighted hybrid memory for LLM agents. FTS5 + sqlite-vec + RRF + KG. MIT, open source. Published benchmarks." |
| Repo topics | ✅ READY | 20 topics (llm, memory-system, sqlite, typescript, hybrid-search, kg, ai-agents, fts5, etc.) |
| Discussions | ✅ READY | Enabled (`hasDiscussionsEnabled: true`) |
| Discussion seed posts | ✅ READY | 5 files in `docs/discussions-seed/` (welcome, roadmap, RFC template, show-and-tell, Q&A) |
| git tag v1.0.0 | ✅ EXISTS | (v1.0.0 and v1.0.0-paper-draft pushed; `v1.0.0-rc1` tag NOT pushed) |
| GitHub Release v1.0.0-rc1 | ❌ MISSING | Release notes exist in `docs/releases/v1.0.0-rc1.md` but GH Release not created |
| Trendshift submission | ❌ NOT DONE | Manual: `https://trendshift.io/` (5-min task; not blockable) |
| Product Hunt draft | ❌ NOT DONE | Checklist requires: draft + gallery + maker + schedule Tue before midnight PST |
| Blog post published URL | ❌ NOT DONE | Draft in repo; posting to personal site / dev.to deferred to launch day |

### E. Demo assets

| Asset | Status | Notes |
|---|---|---|
| asciinema script (`docs/launch-assets/scripts/demo-record.sh`) | ✅ READY | Full CLI demo flow scripted |
| cast-to-gif pipeline script | ✅ READY | `docs/launch-assets/scripts/cast-to-gif.sh` |
| preflight check script | ✅ READY | `docs/launch-assets/scripts/preflight-check.sh` |
| CLI demo .cast file | ❌ NOT RECORDED | `docs/launch-assets/cast/` is EMPTY |
| CLI demo GIF (`docs/assets/demo-cli.gif`) | ❌ NOT RECORDED | Placeholder `docs/assets/demo-placeholder.png` in README |
| F10 dashboard GIF | ❌ NOT RECORDED | Scheduled for Sat 2026-05-30 per README |
| Narration script | ✅ READY | `docs/launch-demo-narration.md` |
| Demo plan | ✅ READY | `docs/launch-demo-plan.md` |

### F. Q4 Comparison / COMPARISON.md

| Item | Status | Notes |
|---|---|---|
| nox_mem prod numbers | ✅ READY | 0.6380 nDCG@10, MRR 0.3700, R@10 0.5417, p50 12ms (Sat 2026-05-24 live prod) |
| mem0 adapter | ✅ VALIDATED | gold_hits unlocked; PR #285 canonical; 281ms avg |
| zep adapter | ✅ VALIDATED | partial smoke 3/5; session-aware gated |
| agentmemory adapter | ✅ VALIDATED | REST adapter OSS-ready; 1/13 smoke (52min full ingest pending) |
| letta adapter | ⚠️ GATED | SDK missing; graceful fallback structure sound |
| evermind | ❌ SKIPPED | Repo 404 confirmed PR #281; excluded from COMPARISON.md |
| Canonical 100-query × 2-dataset × 6-system run | ❌ NOT COMPLETE | nox_mem alone ran 100q; competitors need full ingest + 100q run |
| COMPARISON.md competitor numbers | ❌ MISSING | 10 `[PENDENTE Sat full run]` cells in headline table + per-category |

---

## §2 Gap Analysis — READY / INCOMPLETE / MISSING / BLOCKED

### READY (no action needed)
- D43 gate: VERIFIED (0.6380 > 0.3487 × 1.15)
- Launch day checklist: production-quality, covers minute-by-minute Wed 06-03
- FOSS hygiene: all 5 community files present
- GitHub repo: description + 20 topics + Discussions enabled
- Social copy: all channels (Twitter T1-T8, HN, Reddit, PH) — arXiv link intentionally blank (Tue)
- Blog post: numbers embedded from smoke run; honesty disclaimer present
- HN defense prep: 15 hostile Q+A variants
- Outreach templates: journalist, podcast, newsletter — personalization slots marked
- Press kit: 9 documents (bio, pitches, quotes, logo, tech deep dive, investor one-pager)
- Paper MD: 0 placeholders; canonical G5 V3 + G10d numbers
- arXiv metadata + abstract: ready to paste into submission form
- LaTeX PDF: compiles; two PDF artifacts exist
- CI workflows: all green (lint, typecheck, eval, security, release)
- Pre-launch checker: 10 checks; secrets clean check included
- VPS observability: F10 Phase A+B+C+D LIVE; healthcheck cron 15min
- Pre-launch security review: CLEAN verdict 2026-05-22

### INCOMPLETE (exists but needs work before Wed)

| Gap | Current state | What's needed | Effort |
|---|---|---|---|
| **README hero** (PR #297 open) | PR open with real numbers + 2-row comparison table | Merge PR #297; insert demo GIF once recorded | 5 min + depends on GIF |
| **COMPARISON.md** | nox_mem 0.6380 smoke; 10+ `[PENDENTE]` cells for competitors | Run agentmemory full ingest (52min) + 100q canonical run; fill cells | 4-8h compute + 1h write-up |
| **LaTeX paper Table 8** | 8 TBD rows (per-category entity breakdown G12 R01b) | Fill from G12 audit data in `audits/2026-05-21-G12-frontmatter-retrieval-audit.md` | 1-2h |
| **Blog post** | 4 references to "run canônico" pending / smoke disclaimer | Optionally update when canonical COMPARISON.md finalizes; honest as-is | 30min after COMPARISON.md |
| **Release notes v1.0.0-rc1** | File exists in `docs/releases/v1.0.0-rc1.md` with arXiv/PH/blog links as `[PENDENTE]` | Update links post-arXiv (Tue); create GH Release | Tue: 15min |

### MISSING (artifact does not exist yet)

| Gap | What's needed | Effort | Deadline |
|---|---|---|---|
| **Demo GIF CLI** | Run `demo-record.sh`, convert via `cast-to-gif.sh`, commit to `docs/assets/demo-cli.gif` | 1-2h | Sat 2026-05-30 (planned) |
| **Demo GIF F10 dashboard** | Screen-record F10 dashboard UI (Tailscale tunnel), compress, commit | 1h | Sat 2026-05-30 (planned) |
| **git tag v1.0.0-rc1** | `git tag v1.0.0-rc1 && git push origin v1.0.0-rc1` | 2 min | Before Mon checklist |
| **GitHub Release** | `gh release create v1.0.0-rc1` with release notes from `docs/releases/v1.0.0-rc1.md` | 15 min | Tue 06-02 (post-arXiv) |
| **Product Hunt draft** | Create PH draft: title, tagline, description, gallery (3+ images/GIFs), maker first comment; schedule 2026-06-03 00:01 PST | 2-3h | Tue 06-02 (must schedule 24h in advance) |
| **Recipient list for outreach** | Templates exist; named journalists/podcasters/newsletter authors not compiled | 1-2h research | Mon 06-01 |
| **Trendshift submission** | Single-page form at trendshift.io | 5 min | Wed launch day |
| **arXiv submission (account + endorsement)** | Account creation + endorser check for cs.IR (may need endorsement for first-time submitter) | 1-3h | Seg 06-01 EOD |

### BLOCKED

| Gap | Blocker | Mitigation |
|---|---|---|
| **arXiv endorsement** | First-time submitter to cs.IR may need endorser; process can take 24-48h | Check endorsement requirement **Mon 06-01** — if needed, request immediately. CS.IR sub-field: endorsers directory at arxiv.org/auth/show-endorsers |
| **Canonical competitor Q4 numbers** | agentmemory full ingest ~52min; letta Docker Postgres setup; zep full session corpus | Run when VPS capacity available Sun/Mon; letta skip acceptable (flagged as GATED in COMPARISON.md) |
| **GEMINI_API_KEY in git history** | `check-pre-launch.sh` flagged potential key pattern; unverified | Run manual check: `git log --all -p -S GEMINI_API_KEY | grep '^+' | grep -v 'YOUR_\|your-key\|\.env'`; if real key: revoke + BFG clean |

---

## §3 Critical Path — What Blocks Launch

These items, if undone by Tue 2026-06-02 23h, cause the checklist to fail or the launch to carry material credibility risk:

### Hard blockers (launch fails without these)

1. **arXiv endorsement check** — if first-time submitter to cs.IR needs endorser, 24-48h turnaround. Must confirm Mon 06-01 EOD. If blocked: contingency is launching without arXiv badge (checklist §6 covers this scenario: "Lançar sem badge arXiv — aceitável como contingência").

2. **Product Hunt draft + schedule** — PH allows scheduling 24h in advance. Must be configured Tue 06-02 before midnight PST (= Wed 03h BRT). Without this, PH launch day 1 votes are lost (votes in first 6h are most valuable for daily ranking).

3. **Demo GIF** — README hero has `<!-- PENDENTE Sat 2026-05-30 -->` placeholder. An image embed that shows a placeholder PNG is a credibility hit on HN. Planned recording date is Sat 2026-05-30 (7 days out). This is the single most visible gap on the repo page.

### Soft blockers (credibility risk if unresolved)

4. **COMPARISON.md canonical numbers** — currently 10+ cells `[PENDENTE Sat full run]`. The blog post explicitly promises "run canônico…completa `benchmark/COMPARISON.md` antes do launch." If HN audience sees the COMPARISON.md skeleton on Wed, it will be flagged. Minimum viable: fill mem0 canonical numbers (full 100-query run); mark letta/evermind explicitly as "not evaluated" rather than `[PENDENTE]`. 

5. **LaTeX Table 8 TBD rows** — 8 rows in the per-category entity breakdown. Paper should not have `TBD` in a published arXiv preprint. Source data exists in `audits/2026-05-21-G12-frontmatter-retrieval-audit.md`. Fill Mon 06-01.

6. **GEMINI_API_KEY git history check** — unresolved security flag from `check-pre-launch.sh`. If a real key exists in history: (a) it's already compromised and should be revoked, (b) it would be discoverable post-launch. 5-min check.

---

## §4 Action Items Prioritized

### P0 — Must-do pre-Wed (blocks or materially damages launch)

| # | Item | Owner | Deadline | Effort |
|---|---|---|---|---|
| P0-1 | **arXiv endorsement check + request** — login/create account at arxiv.org, check if cs.IR endorsement required, request if needed | Toto | Mon 06-01 09h | 30min-3h |
| P0-2 | **Demo GIF CLI + F10 dashboard** — run `demo-record.sh`, convert, commit `docs/assets/demo-cli.gif` + `demo-dashboard.gif`, merge PR #297 with GIFs wired | Toto (manual, VPS) | Sat 2026-05-30 | 2-3h |
| P0-3 | **Product Hunt draft + schedule** — create PH product page, gallery (3+ screenshots/GIFs), maker first comment; schedule Wed 06-03 00:01 PST | Toto | Tue 06-02 22h BRT | 2-3h |
| P0-4 | **GEMINI_API_KEY git history verify** — run `git log --all -p -S GEMINI_API_KEY | grep '^+' | grep -v 'YOUR_\|your-key\|\.env'`; if real key found, revoke + BFG | Toto | Mon 06-01 | 5-15min |
| P0-5 | **git tag v1.0.0-rc1 push** — `git tag v1.0.0-rc1 && git push origin v1.0.0-rc1` | Toto or executor | Sun 2026-05-25 | 2 min |

### P1 — High-value pre-Wed (improves launch quality materially)

| # | Item | Owner | Deadline | Effort |
|---|---|---|---|---|
| P1-1 | **COMPARISON.md mem0 canonical run** — run full 100-query LoCoMo+LongMemEval via mem0 adapter; fill headline table + per-category rows; replace `[PENDENTE]` | executor / VPS | Mon-Tue 06-01 | 4-6h compute + 1h |
| P1-2 | **LaTeX Table 8 fill** — fill 8 TBD rows from `audits/2026-05-21-G12-frontmatter-retrieval-audit.md`; recompile PDF; update arXiv package | executor | Mon 06-01 | 1-2h |
| P1-3 | **Recipient list for outreach** — compile 10-15 named journalists/podcasters from templates §2-§4 with specific article/episode references | Toto or research agent | Mon 06-01 | 1-2h |
| P1-4 | **arXiv submission (Tue 06-02)** — follow `docs/arxiv-submit-checklist.md` §2: login, upload LaTeX package, fill metadata, confirm, note ID | Toto | Tue 06-02 09h ET | 1-2h |
| P1-5 | **GH Release v1.0.0-rc1** — `gh release create v1.0.0-rc1 --notes-file docs/releases/v1.0.0-rc1.md`; update arXiv/PH links in release body post-arXiv | executor | Tue 06-02 post-arXiv | 15min |

### P2 — Nice-to-have pre-Wed

| # | Item | Notes |
|---|---|---|
| P2-1 | **agentmemory + zep canonical run** — full 100-query run after full corpus ingest; fills more COMPARISON.md cells | ~52min ingest + run time; letta skip acceptable |
| P2-2 | **Blog post update with canonical numbers** — replace "run canônico em execução" disclaimers; currently honest as-is | 30min after COMPARISON.md fills |
| P2-3 | **Trendshift submission** — single form; 5 min; can do Wed launch day morning | Low ROI vs effort; defer to Wed 10h |
| P2-4 | **LinkedIn announcement draft** — optional per checklist (§2 11h BRT); different audience than HN/Twitter | 30min; draft can be improvised |
| P2-5 | **Worktree hardening** (Sun 06h per HANDOFF) | Infrastructure health; 7 leaks Sat; not GTM critical but reduces risk during Tue-Wed crunch |

---

## §5 Cross-Reference to PRs / Specs / Runbooks

| Area | Reference |
|---|---|
| Launch day hour-by-hour | `docs/launch-day-checklist-2026-06-03.md` §2 |
| Crisis plans | `docs/launch-day-checklist-2026-06-03.md` §3 |
| Pre-launch final check | `docs/launch-day-checklist-2026-06-03.md` §1 |
| arXiv submission sequence | `docs/arxiv-submit-checklist.md` |
| Demo recording | `docs/launch-assets/scripts/demo-record.sh` + `docs/launch-demo-plan.md` |
| COMPARISON.md canonical run | `eval/q4-comparison/runner.py --systems all --datasets locomo,longmemeval --limit 100` |
| Outreach | `docs/outreach-templates.md` |
| HN defense | `docs/launch-hn-comments-prep.md` |
| Pre-launch script | `scripts/check-pre-launch.sh` |
| Press kit | `docs/press-kit/` (9 docs) |
| Security review (pre-launch CLEAN verdict) | `audits/2026-05-22-pre-launch-security-review.md` |
| Q4 validation numbers | HANDOFF §Sat 2026-05-24 closure (nDCG@10 0.6380, p50 12ms) |
| D43 gate record | `docs/DECISIONS.md` §D43 |
| Social copy all channels | `docs/launch-social-copy.md` |
| Blog post | `docs/launch-blog-v0-draft.md` |
| Pricing strategy | `docs/gtm/PRICING-STRATEGY.md` (Stripe-first, D44) |

---

## §6 Risk Register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| arXiv endorsement blocks Tue submit | Medium (first-time submitter cs.IR) | High — no arXiv badge for launch | Check Mon 06-01 09h; contingency = launch without badge (checklist §6 covers) |
| Demo GIF not ready by Wed | Low (planned Sat 05-30) | High — README shows placeholder PNG on launch day | Record Sat 05-30; no other dependency |
| COMPARISON.md has `[PENDENTE]` on launch day | Medium (canonical run needs compute time) | High — HN community will notice; "comparison" in README with empty cells damages credibility | P1-1: run mem0 canonical Mon-Tue; mark letta/evermind as "excluded" explicitly |
| PH draft not created by Tue midnight PST | Low (Toto aware) | High — loses PH daily ranking (first-6h votes critical) | Calendar reminder Tue 06-02 19h BRT |
| Paper Table 8 TBD rows in arXiv preprint | Low (data in G12 audit) | Medium — reviewers/HN audience may cite unfinished paper | P1-2: 1-2h to fill from audit data |
| VPS outage during launch | Low (healthcheck cron active; 1 outage last 20 days) | High — demo offline on launch day fatal for credibility | Checklist §3 covers: redirect to screenshots/Loom |
| Real API key in git history | Low (flagged as "potential" by grep heuristic) | Critical if real — immediate revocation + BFG needed | P0-4: verify Mon 06-01; 5-min check |

---

*Audit generated 2026-05-24. Cross-referenced: HANDOFF.md, ROADMAP.md §7, DECISIONS.md D43, docs/launch-day-checklist-2026-06-03.md, docs/COMPARISON.md, paper/publication/latex/main.tex, docs/launch-assets/README.md, audits/2026-05-24-afternoon-prelaunch-recheck.md.*
