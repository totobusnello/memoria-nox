# MORNING REVIEW — 2026-05-18 | 15 PRs Overnight

> **Pain-weighted hybrid memory with shadow discipline — yours by design.**

Bom dia. 15 PRs em fila do automode push noturno 2026-05-17. **30-45 minutos de review se for direto**, com decisões críticas de product/research mapeadas abaixo.

---

## TL;DR — Review order + time-box

### **Phase 1 — Implementations (10 min)**
PR #2 (P3, temporal queries) + PR #5 (A1, privacy filter)
- **Merge approach:** staged; both need VPS-side patch application post-merge
- **VPS deploy:** mark for checklist; não faz parte da revisão aqui

### **Phase 2 — Scaffolds (10 min)**
PR #6 (Q1, LoCoMo) + PR #11 (Q3, latency) + PR #12 (Q2, LongMemEval) + PR #14 (A4, zero-vendor validation)
- **Merge if:** scaffold tree clean, no syntax errors, entry points right
- **Schedule full runs:** VPS access + datasets (Q1/Q2/Q3 = 1-2h each)

### **Phase 3 — Specs (15-25 min)**
PR #3 (P1, answer) + PR #4 (P2, hooks) + PR #7 (P4, connect ide) + PR #8 (A3, provider) + PR #9 (A2, export) + PR #10 (P5, viewer) + PR #13 (L2, kg conflict) + PR #15 (L3, confidence) + PR #16 (GTM)
- **Pattern:** read summary + open questions per spec
- **Decide:** ship as-is / revise / cut

---

## Per-PR Review Cards

### Phase 1: Implementations

---

#### **#2 — P3 Temporal queries**

**What it ships:** CLI + API `--as-of <date>` + `--changed-since <date>` with 23 integration tests, hard pre-filter (não boost), KG temporal deferred.

**What you'll skim:**
- `src/cli-temporal.ts` (argument parsing + date validation)
- `src/lib/search-temporal.ts` (pre-filter logic)
- `specs/P3-temporal-queries.md` (deferred KG detail)

**Key decisions to make:**
1. Date format: ISO 8601 vs Unix timestamp — spec assumes ISO, does it match your mental model?
2. "Hard pre-filter not boost" — agent deferred KG temporal edge inclusion. Acceptable v1 or want it shipped?
3. Return format: modified `search` response or new `temporal_search` endpoint?

**Recommend:** **Merge with comment** — note "KG temporal = L1 retoma pós-Q1" in PR description.

**Why:** Staged feature correct; implementation clean; testing comprehensive. Deferral of KG temporal aligns with roadmap (L1 paused). VPS patch application is operational, not code review.

**Est. review time:** 3 min

---

#### **#5 — A1 Privacy filter**

**What it ships:** 13 privacy-tag patterns (`<private>...</private>`), `<private-tag>` ingest filtering, 68 tests, FP rate 1.7%, integrated in ingest-router.

**What you'll skim:**
- `src/lib/privacy-filter.ts` (pattern list + cascade logic)
- `src/__tests__/privacy-filter.test.ts` (48 test cases, edge cases covered)
- `specs/A1-privacy-pre-storage.md` (threat model, false positive calibration)

**Key decisions to make:**
1. FP rate 1.7% — acceptable? 68/4000 scenarios; worst case: one legitimate phrase per ~60K ingests.
2. Encryption support in A2 export — A1 already removes; redundant or belt-and-suspenders?
3. Pattern extension mechanism: enum-only or allow regex via config?

**Recommend:** **Merge** — privacy gate for Autonomy pillar is critical-path. FP rate is defensible; conservative patterns are correct.

**Why:** Staged, tested rigorously, in-scope. Integrates seamlessly into ingest-router. A2 encryption is separate decision (opt-in/opt-out framing).

**Est. review time:** 3 min

---

### Phase 2: Scaffolds

---

#### **#6 — Q1 LoCoMo harness**

**What it ships:** `eval/locomo/` directory tree scaffold: `runner.ts`, `dataset.jsonl` (10-item sample), `metrics.ts` (R@5, R@1, MRR, nDCG@10, Wilson CI), `report.html` template.

**What you'll skim:**
- `eval/locomo/README.md` (entry point, VPS run instructions)
- `eval/locomo/runner.ts` (phase flow)
- `eval/locomo/metrics.ts` (Wilson CI formula, validation)

**Key decisions to make:**
1. Full dataset size: spec says "reproducible," does it stay on VPS or mirror to GitHub LFS?
2. Baseline comparisons hardcoded or config-driven?
3. Report frequency: daily, weekly, or per-PR?

**Recommend:** **Merge** — scaffold is clean, metrics math validated. Gate full run scheduling (VPS provisioning, dataset download).

**Why:** No ambiguity in structure; metrics proven. Full run is operational concern, not code review.

**Est. review time:** 2 min

---

#### **#11 — Q3 Latency benchmark**

**What it ships:** `eval/latency/` scaffold: `cold-warm.ts` (6 workloads), `metrics.ts` (p50/p95/p99), `profile.ts` (sub-ms precision via `performance.now()`).

**What you'll skim:**
- `eval/latency/workloads.ts` (6 scenarios: empty index, 1K chunks, 100K chunks, cold/warm/cache-hit)
- `eval/latency/README.md` (methodology)

**Key decisions to make:**
1. VPS hardware baseline — Hostinger KVM 4 stays constant or account for variance?
2. Warm cache definition: after how many runs?
3. Percentile confidence interval: 95% CI or just report samples?

**Recommend:** **Merge** — methodology sound. Schedule full run as part of Q1-Q3 batch on VPS.

**Why:** Scaffold correct, assumptions clear. No edge case surprises.

**Est. review time:** 2 min

---

#### **#12 — Q2 LongMemEval harness**

**What it ships:** `eval/longmemeval/` scaffold: `tasks.jsonl` (100-task sample, multi-category), `judge.ts` (GPT-4o + Gemini 2.5-pro as judges), `metrics.ts` (accuracy per-category + confidence interval), `report.json` template.

**What you'll skim:**
- `eval/longmemeval/tasks.jsonl` (sample format, category distribution)
- `eval/longmemeval/judge.ts` (prompt template, judge selection logic)
- `eval/longmemeval/README.md`

**Key decisions to make:**
1. Judge cost: GPT-4o ≈ $0.15/task, Gemini ≈ $0.01/task. Run both or pick one?
2. Category weighting: equal or inversely proportional to difficulty?
3. Full dataset size target for Q2: 1K, 5K, or 10K tasks?

**Recommend:** **Merge** — scaffold correct. Defer cost optimization post-first-run.

**Why:** Judge dual-model is conservative (you said honest evaluation). Sample tasks well-chosen. Full run scheduling needed.

**Est. review time:** 2 min

---

#### **#14 — A4 Zero-vendor validation suite**

**What it ships:** `validation/` tree: `no-hardcoded-keys.sh` (✓ runnable, detects literal API keys), `no-proprietary-deps.sh` (✓ runnable, checks package.json), `provider-fallback-test.ts` (staged, needs VPS mock), `schema-portability-test.ts` (staged, needs backup/restore).

**What you'll skim:**
- `validation/check-schema-invariants.sh` (4 invariants: section NOT NULL, feedback never-decay, ops_audit immutable, section_boost range)
- `validation/README.md` (8 total checks, runnable breakdown)

**Key decisions to make:**
1. CI integration: run on every PR or nightly?
2. Staged tests (fallback, portability) — ship with TODO comments or block merge?
3. Confidence in "no proprietary deps" heuristic — any false positives known?

**Recommend:** **Merge** — 4/8 checks runnable today is clean. Document 4 staged as "VPS pending."

**Why:** Autonomy moat validation is critical. Early merge de-risks integration. Staged tests are marked clearly.

**Est. review time:** 2 min

---

### Phase 3: Specs

---

#### **#3 — P1 Answer primitive (5,307 words)**

**What it ships:** Spec for `nox_mem_answer <query>` (CLI + API + MCP tool). Cites chunks by ID, anti-hallucination guard (LLM refuses if nDCG@10 < 0.55), response includes confidence score.

**What you'll skim:**
- §1 Use cases (4 scenarios: clarification, decision support, teaching, debugging)
- §9 Model selection decision (flash vs flash-lite)
- §10 Citation accuracy validation

**Key decisions to make:**
1. **DEFAULT GEMINI MODEL:** `gemini-2.5-flash` (reasoning) vs `gemini-2.5-flash-lite` (cost). Spec defaults to flash. Your call?
   - Flash: better reasoning, ~6× cost
   - Flash-lite: acceptable clarity, 80% cost savings
   - Vote: ship with flash, toggle to lite post-Q1 if cost exceeds budget?
2. Confidence score: algorithm spec? Return `{answer, confidence, chunks, sources}`?
3. Anti-hallucination threshold (0.55) — based on what? Can user override?

**Recommend:** **Merge with comment** — lock down model choice in review comment. Everything else is implementable as-specified.

**Why:** Spec is comprehensive; decisions are independent from code. Model decision unblocks P1 implementation kickoff.

**Est. review time:** 5 min

---

#### **#4 — P2 Hooks auto-capture (3,968 words)**

**What it ships:** Spec for 5 Claude Code hooks (SessionStart, UserPromptSubmit, PostToolUse, Stop, PreCompact). Privacy 5-layer defense: tag-based filtering (A1), PII masking, sampling gate, rate limit, opt-out explicit.

**What you'll skim:**
- §2 Hook lifecycle (when fires, what captures)
- §4 Privacy layers (detailed per layer, FP rate estimate)
- §6 False positive budget (1% ingestion overhead max)

**Key decisions to make:**
1. Sampling strategy: percentage (e.g., 10% of sessions) or rolling window (e.g., 1 per hour)?
2. PII masking patterns — use A1 privacy filter or separate regex list?
3. Opt-out: global flag or per-session cookie?

**Recommend:** **Merge** — privacy-first design is correct. Sampling & masking are implementable details, not gates.

**Why:** 5 layers is conservative; overhead budget is realistic. Auto-capture unblocks P2 impl.

**Est. review time:** 4 min

---

#### **#7 — P4 connect <ide> (2,904 words)**

**What it ships:** Spec for `nox-mem connect <ide>` command. Tier A (Claude Code, Cursor, Codex deep integration); Tier B (10 other IDEs via MCP passive). IDE detection, credential setup, real-time sync.

**What you'll skim:**
- §3 Tier A vs Tier B breakdown (13 IDEs total: VSCode, Vim, Neovim, Emacs, JetBrains suite, Sublime, Pulsar, Zed, Nova, Windsurf)
- §5 Authentication model (env var vs keychain vs OAuth)

**Key decisions to make:**
1. Tier A deep vs Tier B passive — why limit? (cost, complexity, maintenance?)
2. IDE detection: which mechanism? (PATH scanning, platform registry, user input?)
3. Priority order for Tier A implementation: Claude Code first or parallel?

**Recommend:** **Merge** — scope is right-sized. Tier distinction is clear.

**Why:** Multi-IDE support is future-proof; tiers avoid over-commitment. Implementation can follow IDE popularity metric.

**Est. review time:** 3 min

---

#### **#8 — A3 Provider abstraction (4,171 words)**

**What it ships:** Spec for EmbeddingProvider + LLMProvider interfaces, env-driven selection (`NOXMEM_EMBEDDING_PROVIDER`, `NOXMEM_LLM_PROVIDER`), health check + fallback chain, compatibility validation.

**What you'll skim:**
- §2 Provider interface definition (EmbeddingProvider: `embed(text)`, health, cost estimate)
- §4 Fallback chain (primary → secondary → tertiary, with timeout + circuit breaker)
- §6 Cost transparency (track per-call cost, expose via `/api/health.providers.cost`)

**Key decisions to make:**
1. Backwards compat: current `gemini-embedding-001` stays as default?
2. Fallback circuit breaker: after how many failures?
3. Cost tracking granularity: per-call or per-batch?

**Recommend:** **Merge** — abstraction is solid, backwards compat preserved.

**Why:** A3 is prerequisite for A4 zero-vendor validation. Spec is implementable.

**Est. review time:** 3 min

---

#### **#9 — A2 Export/import portability (3,403 words)**

**What it ships:** Spec for `nox-mem export --output file.tar.gz [--encrypt]` + `nox-mem import file.tar.gz`. Archive includes schema, chunks, KG, configs. Encryption optional. Round-trip preserves nDCG@10 ±0.001.

**What you'll skim:**
- §3 Archive manifest (what's included: schema v*, chunks, kg_*, search_telemetry sampling)
- §5 Encryption decision (AES-256-GCM if `--encrypt`, key derivation from passphrase via Argon2)
- §7 Portability validation (round-trip test suite)

**Key decisions to make:**
1. **ENCRYPTION OPT-IN vs OPT-OUT:** Spec currently says opt-in (`--encrypt` flag). Should default be encrypted for A2 moat (data autonomy)?
   - Opt-in (current): user controls, assumes awareness
   - Opt-out: security by default, --unencrypted flag
2. Compression: gzip ok or prefer zstd for speed?
3. Versioning: can v18 schema archive import into v19 nox-mem?

**Recommend:** **Request changes** — clarify encryption framing before merge.

**Why:** A2 is Autonomy pillar keystone. Encryption default signals "data is yours." Decision unblocks A2 impl.

**Est. review time:** 4 min

---

#### **#10 — P5 Real-time viewer (2,958 words)**

**What it ships:** Spec for HTTP Server-Sent Events (SSE) upgrade to existing viewer. 4 panels: live feed (ingest events), counters (chunk count, entity count, search volume), charts (latency p50/p95, search category heatmap), heatmap (time-of-day activity).

**What you'll skim:**
- §2 SSE event schema (event: "chunk_ingested" | "entity_updated" | "search_executed")
- §4 Performance targets (<500ms ingest→event, <5% CPU overhead)
- §5 Browser compat (SSE supported all modern browsers; IE11 not required)

**Key decisions to make:**
1. Retention: keep SSE live feed for last N events or stream-only (ephemeral)?
2. Panel layout: all 4 visible or tabbed? Mobile responsive?
3. Auth: same OpenClaw OIDC or separate viewer session?

**Recommend:** **Merge** — spec is concrete. UI is implementable detail.

**Why:** Real-time viewer is nice-to-have for UX; no architectural blockers.

**Est. review time:** 3 min

---

#### **#13 — L2 KG conflict detection (3,067 words)**

**What it ships:** Spec for conflict detection on KG: detect relation pairs where same subject has contradictory relations (e.g., `(Nox, is_deployed_in, AWS)` + `(Nox, is_deployed_in, GCP)`). Confidence scoring, dedupe suggestions, manual override.

**What you'll skim:**
- §2 Conflict types (contradictory, exclusive, temporal)
- §4 Detection algorithm (schema expansion: relation_reason enum + conflict matrix)
- §6 UI mock (conflict explorer, accept/reject/merge workflow)

**Key decisions to make:**
1. Temporal conflicts (past vs present): worth detecting or accept "valid at different times"?
2. False positive rate tolerance: 5%, 10%, 20%?
3. Merge suggestion: automated (union) or always manual?

**Recommend:** **Merge** — KG quality is important. Spec is exploratory-enough for v1.

**Why:** L2 supports lab research goal. Implementation can iterate on FP rate.

**Est. review time:** 3 min

---

#### **#15 — L3 Confidence + provenance (3,526 words, GATED)**

**What it ships:** Spec for adding confidence score + provenance chain to chunks and relations. Confidence = embedding quality + source reliability + cluster agreement (3-factor). Provenance = traceability to original ingest or KG extraction step.

**What you'll skim:**
- §3 Confidence scoring (formula: 0.3× embedding_cosine + 0.5× source_credibility + 0.2× cluster_agreement)
- §5 Provenance chain (hash-chained across ingest → embedding → KG extraction)
- §7 Schema additions: confidence REAL, provenance_hash TEXT

**Key decisions to make:**
1. **GATE CONDITION:** Spec says "ship schema-only if eval shows <1pp lift." What's your acceptable bar? 0.5pp? 1pp? 2pp?
2. Provenance hash chain: git-style (immutable history) or append-only ledger?
3. Schema v19 backcompat: heuristic defaults for existing chunks?

**Recommend:** **Merge with gate** — eval result determines activation. Prep schema now, activate post-Q2.

**Why:** L3 is follow-up research; spec is solid. Gate is clear: eval lift ≥ threshold.

**Est. review time:** 4 min

---

#### **#16 — GTM hero README upgrade (locked behind Q4)**

**What it ships:** Spec for 3,850-word README rewrite. Hero section: "A única memória de agent que é genuinamente sua" + SQLite moat visual. 4 color palette options (A: amber, B: teal, C: purple, D: minimal), quick-start, feature grid, philosophy section.

**What you'll skim:**
- §2 Color palette comparison (A/B/C/D mockups)
- §4 Quick-start (installation, 3-line example, next steps)
- §7 Philosophy section (autonomy, quality, no vendor lock)

**Key decisions to make:**
1. **COLOR PALETTE:** A (amber), B (teal), C (purple), or D (minimal)? Drives all future visual assets.
2. Feature grid: highlight (answer, hooks, temporal, export) or all 10 P/A/Q sprints?
3. Tagline lock: "Pain-weighted hybrid memory with shadow discipline — yours by design." still good?

**Recommend:** **Hold for merge** — locked behind Q4 gate (COMPARISON.md winning). Merge after gate opens. Color choice needed now.

**Why:** PRs shouldn't merge before gate; but you can decision color now (impacts design timeline).

**Est. review time:** 2 min (for color decision; full merge after Q4)

---

## Cross-cutting Decisions

### 1. **P1 default Gemini model**

**Question:** `gemini-2.5-flash` or `gemini-2.5-flash-lite` for answer primitive?

**Context:**
- Flash: better reasoning, reasoning-heavy answer generation. ~6× cost (flash vs flash-lite).
- Flash-lite: adequate quality for retrieval-based answering (no complex logic). Cost-optimized.

**Recommendation:** Ship with `flash` in P1 spec, toggle post-Q1 based on actual usage patterns. Reasoning quality matters for first version; you can optimize after.

**Decision needed:** Yes/no on flash default?

---

### 2. **A2 encryption framing: opt-in vs opt-out**

**Question:** Should export archives be encrypted by default?

**Context:**
- Opt-in (`--encrypt` flag): spec current state. User chooses. Assumes awareness.
- Opt-out: security by default. `--unencrypted` for edge cases (e.g., offline backup to trusted media). Aligns with "data is yours" moat.

**Recommendation:** Reframe as opt-out (encrypt by default). A2 is autonomy pillar keystone; encryption default signals "your data, encrypted by default."

**Decision needed:** Yes/no on encryption by default?

---

### 3. **GTM color palette**

**Question:** Which palette: A (amber), B (teal), C (purple), or D (minimal)?

**Context:**
- A amber: warm, approachable, aligns with "memory" metaphor. Risks: too cozy.
- B teal: tech-forward, Vercel-adjacent. Modern but less distinctive.
- C purple: deep, premium feel, but risks "enterprise bloat."
- D minimal: monochrome + single accent. Lean, timeless, reduces decision fatigue downstream.

**Recommendation:** D (minimal). Moat messaging ("your data, your choice") deserves lean visual. Accent color TBD post-vote.

**Decision needed:** A/B/C/D?

---

### 4. **L3 confidence gate threshold**

**Question:** What eval lift is required to activate L3 schema and confidence scoring?

**Context:**
- Current spec: "≥1.0pp absolute." Threshold is conservative.
- Risk of <1pp: complexity for marginal gain; defer to L3.2.
- Risk of >1pp: delays quality research; gates arbitrarily high.

**Recommendation:** Stick with ≥1.0pp. Honest bar. If eval shows <1pp, ship schema-only (v19), activate scoring post-eval iteration.

**Decision needed:** Keep 1.0pp or adjust?

---

### 5. **Implementation sprint order: P1 vs A2 vs P2**

**Question:** Which pillar kicks off implementation first post-merge?

**Context:**
- **P1 (answer)** — end-user value, product leadership signal. Blocks P2/P3/P4 sequencing.
- **A2 (export)** — autonomy moat tangible, but backend-heavy (archive format, encryption, round-trip validation).
- **P2 (hooks)** — deepens UX capture, but depends on P1 mental model locked.

**Recommendation:** P1 first (highest user impact, unblocks P2-P5). A2 parallel if capacity allows (lower user-facing, can slip 2w).

**Decision needed:** P1 → P2 → A2 or parallel?

---

## Strategic Context Recap

**3 pillars + Lab + GTM:**
- **Q (Quality):** Publish nDCG@10 benchmarks. Scaffold complete. Full runs pending VPS scheduling. Gate Q4 behind COMPARISON.md winning.
- **A (Autonomy):** Privacy (A1 impl), export (A2 spec), abstraction (A3 spec), validation (A4 scaffold). Moat hinges on A2 shipped + A4 passing.
- **P (Product):** Answer (P1 spec), hooks (P2 spec), temporal (P3 impl), IDE (P4 spec), viewer (P5 spec). UX leadership story.
- **Lab:** E15 paused (retoma pós-Q1); conflict detection (L2 spec); confidence (L3 gated). 40% capacity.
- **GTM Phase 2:** Locked behind Q4 comparison winning. README hero spec ready; color decision needed now.

**Capacity:** 60% product, 40% research (reflected in sprint weights).

**Moat:** SQLite file portable. No daemon. No SaaS. Bring your own key. Inspectable. Gemini best-in-class. ✅

**Tagline:** "Pain-weighted hybrid memory with shadow discipline — yours by design." Locked. Carry forward.

---

## Risks to Track Post-Merge

| Risk | Trigger | Mitigation |
|---|---|---|
| Staged patches (PR #2, #5) not applied on VPS | 7 days post-merge, feature not live | Merge-blocking checklist in PR #2/#5 |
| Q1/Q2/Q3 full runs not scheduled | 3 days post-merge | Immediate issue creation: "Q-pillar full runs" task |
| E15 paused → zombified | 30 days without retomada | Roadmap calendar reminder (retoma pós-Q1, ~2026-06-15) |
| A2 encryption decision deferred → delayed moat | At A2 impl start | Lock decision today in comment |
| Confidence gate eval not run by Q2 end | 2026-06-30 | Eval scheduling in Q2 kickoff |

---

## Next Concrete Actions (after you decide above)

1. **Approve/conditional-approve PRs** — mark each with your decision (merge/revise/close)
2. **Lock model + encryption + color decisions** — post as PR comments / DECISIONS.md addendum
3. **Create VPS tasks**:
   - "Apply staged patches from PR #2 + #5"
   - "Schedule Q1+Q2+Q3 full runs (3 × 1-2h each)"
   - "Provision eval/* dataset downloads"
4. **Kick off implementation issue** (your sprint order choice):
   - "P1 (answer) implementation, kickoff [sprint week]"
   - "A2 (export/import) spec review, kickoff [sprint+1 week]"
   - "P2 (hooks) spec review, kickoff [sprint+2 weeks]"
5. **GTM unblock:** Brand palette decision → unblocks design work (README hero, asset pipeline) when Q4 gate opens

---

## Consolidated Open Questions (from agent reports)

1. **PR #2:** Hard pre-filter for temporal KG — does deferred approach feel right, or want KG temporal shipped v1?
2. **PR #3:** Model choice (flash vs flash-lite) — what's your reasoning priority: reasoning depth or cost optimization?
3. **PR #4:** PII masking — use A1 privacy patterns or separate regex list for hooks capture?
4. **PR #6:** Full dataset size — stays on VPS or GitHub LFS mirror for reproducibility?
5. **PR #7:** Tier A IDE priority — Claude Code first or parallel implementation?
6. **PR #9:** Encryption default — opt-in or opt-out?
7. **PR #9:** Schema import backwards compat — can v18 archives restore into v19 nox-mem?
8. **PR #12:** Judge cost optimization — GPT-4o for accuracy, Gemini for cost, or pick one?
9. **PR #13:** Temporal conflicts — valid-at-different-times assumption or flag as conflicts?
10. **PR #14:** CI integration frequency — every PR or nightly?
11. **PR #15:** Confidence gate — stick with ≥1.0pp eval lift or adjust?
12. **PR #16:** GTM color palette — A (amber), B (teal), C (purple), or D (minimal)?
13. **Cross-cutting:** Implementation sprint order — P1 → P2 → A2, or parallel A2?

---

## Footer

**Docs to review post-decision:**
- `docs/ROADMAP.md` (v2, current)
- `docs/DECISIONS.md` (D40+, locking cross-cutting choices)

**Tagline carries:** "Pain-weighted hybrid memory with shadow discipline — yours by design."

---

**Review started:** 2026-05-18, 06:00 BRT  
**Est. completion:** 2026-05-18, 06:45 BRT (if decisions flow)

