# Changelog

All notable changes to memoria-nox are documented in this file.

The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — 2026-06-02 — Wave 2 closure + docs final sync

- **PR #427 (closure bundle)** — D75 + D76 cravados + paper §5 v5 + ROADMAP v5.1 + HANDOFF Tue. Wave 2 formally closed.
  - **D75:** Wave 2 Phase 1.5 retrieval-stage composability CLOSED on Gemini-3-flash. 3-knob NO-REPLICATE pattern confirmed (KG 0% transfer / AC ~40% transfer / MQ ~34% transfer from gpt-4.1-mini). D74 composability projection substantially refuted at single-stage retrieval layer. IterB ReAct (+2.01pp, PR #419) remains the only validated F_MH lever on Gemini-3-flash.
  - **D76:** Wave 2 Phase 2 Capstone (PR #426) ABORTED — Hostinger CPU steal 51-97% sustained (48h, batch 005 0/50 questions in 23h, ~$20-25 spent). Infrastructure constraint, NOT scientific failure. Architectural lock finding (`[[iterB-architectural-lock-short-circuits-wave-a-knobs]]`) documented. Capstone deferred to stable infrastructure.
  - **Paper §5 v5:** 5 new/replaced sections — §5.5.4 empirical NO-REPLICATE matrix (replaces D74 projection) + §5.5.5 backbone-portability + §5.5.6 MQ MA flip + §5.5.7 architectural composability + §5.5.8 D76 infra abort. PDF + TEX clean rebuild.
  - **ROADMAP v5.1:** Q1 priorities updated (HyDE bench + Claude Sonnet 4.6 / Opus 4.7 backbone bench). Q2/Q3 capstone parked pending stable infrastructure.
  - **HANDOFF Tue:** Mon AM pickup actions + Wave 2 state committed.
- **PR #423** — R0 sanity KG path standalone Gemini-3-flash 5-batch: F_MH -0.01pp (NO-REPLICATE, KG 0% transfer). Cravado `[[kg-path-backbone-dependent-no-replicate-gemini-3-flash]]`.
- **PR #424** — AC standalone Gemini-3-flash 5-batch: F_MH +0.81pp (gate FAIL, ~40% transfer). Cravado `[[adaptive-classifier-backbone-dependent-no-replicate-gemini-3-flash]]`.
- **PR #425** — MQ standalone Gemini-3-flash 5-batch: F_MH +1.21pp (gate FAIL borderline, ~34% transfer; sub-finding: MA_U +3.10pp PRESERVED on Gemini-3-flash). Cravado `[[multi-query-backbone-dependent-no-replicate-gemini-3-flash]]`.
- **PR #426 (closed)** — Wave 2 Phase 2 Capstone bench closed via abandon comment (D76 infra abort). Architectural lock finding documented for future composability work.
- **6 memory findings crystallized:** `[[kg-path-backbone-dependent-no-replicate-gemini-3-flash]]` + `[[adaptive-classifier-backbone-dependent-no-replicate-gemini-3-flash]]` + `[[multi-query-backbone-dependent-no-replicate-gemini-3-flash]]` + `[[iterB-architectural-lock-short-circuits-wave-a-knobs]]` + `[[capstone-aborted-hostinger-throttling-indeterminate]]` + `[[ort-num-threads-cap-during-capstone]]`.
- **Docs final sync (this PR):** README.md + COMPARISON.md (rev8) + COMPETITIVE-POSITIONING.md (rev4) + INCIDENTS.md (D76 entry) + CHANGELOG.md — Wave 2 closure honest framing propagated. 12 SOTA dims canonical confirmed (no 13th). Infrastructure abort distinguished from scientific failure across all public-facing docs.

### Added — 2026-05-31 evening — Wave 2 composability matrix empirical validation

- **PR #423** — R0 sanity KG path standalone Gemini-3-flash 5-batch (n=3,121, batches 004/005/010/011/016). F_MH delta **-0.01pp** vs D70 bare baseline (95% CI [3.00, 9.04] includes baseline). KG path mechanism fired 100% of queries (84k vault tokens injected) but provided zero net F_MH lift on Gemini-3-flash backbone. Refutes D74 composability projection IterB+KG ~10.8% F_MH. Cravado `[[kg-path-backbone-dependent-no-replicate-gemini-3-flash]]`.

- **PR #424** — Wave 2 Phase 1.5 AC (Adaptive Classifier threshold=5) standalone re-baseline Gemini-3-flash 5-batch. F_MH **+0.81pp** (95% CI [4.62, 9.03] overlaps baseline). Gate +1.5pp **FAIL**. Cross-baseline: gpt-4.1-mini +2.01pp (PR #381) → Gemini-3-flash +0.81pp = ~40% transfer rate. Cravado `[[adaptive-classifier-backbone-dependent-no-replicate-gemini-3-flash]]`.

- **PR #425** — Wave 2 Phase 1.5 MQ (Multi-Query expansion) standalone re-baseline Gemini-3-flash 5-batch. F_MH **+1.21pp** (95% CI [4.99, 9.48] overlaps baseline). Gate +1.5pp **FAIL borderline by 0.29pp**. Cross-baseline: gpt-4.1-mini +3.61pp (PR #385) → Gemini-3-flash +1.21pp = ~34% transfer. **Sub-finding (MA backbone flip):** MA composite +0.12pp PRESERVED on Gemini-3-flash (vs -1.38pp regression on gpt-4.1-mini) + MA_U +3.10pp (strongest MA gain Wave 2). Multi-axis backbone-conditional behavior. Cravado `[[multi-query-backbone-dependent-no-replicate-gemini-3-flash]]`.

- **PR #426 (draft)** — Wave 2 Phase 2 Capstone IterB ReAct + Wave C triple (KG+rerank, MQ subsumed by ReAct sub-queries) Gemini-3-flash 5-batch n=3,121. Bench autonomous in tmux `wave2-capstone-7a1cadf2` on VPS (PID 2194486, ETA 24-36h). Cost cap $30 enforced. **Architectural lock discovered:** PR #419 IterB adapter explicit guards at `eval/evermembench/adapter_nox_mem.py` lines 2736 (MQ) / 2906 (KG) / 3063 (rerank) `if not iterb_used_path:` short-circuit Wave A knobs by design. Composability requires explicit 2-guard removal patch. Cravado `[[iterB-architectural-lock-short-circuits-wave-a-knobs]]`.

- **3-knob NO-REPLICATE pattern:** Wave A retrieval-stage knobs measured on gpt-4.1-mini transfer at only ~24-40% to Gemini-3-flash backbone. KG (0%) + AC (40%) + MQ (34%) standalone sum = **+2.01pp = 24% of D74 pessimistic projection +8.43pp**. Composability matrix from D74 substantially refuted at single-stage retrieval layer. **IterB ReAct (+2.01pp clean lift, PR #419) remains the only validated F_MH lever on Gemini-3-flash** as of Sun 2026-05-31. Capstone test of orchestration-stage composability in flight.

- **`docs/HANDOFF.md`** — Sun 2026-05-31 evening section prepended with Wave 2 closure state + Mon AM pickup actions.
- **`docs/DECISIONS.md`** — D74 composability projection annotated with R0 sanity counter-evidence caveat.
- **`docs/ROADMAP.md`** — Wave 2 Phase 1.5 + Capstone rows added to Lab table.
- **`README.md`** — F_MH ceiling break section updated with Wave 2 empirical caveat (research integrity over inflated claims).

### Added — 2026-05-24 evening — 3-primitives canonical documentation

- **`docs/PRIMITIVES.md`** (NEW) — canonical operator-facing reference for the three user-facing primitives (`search` / `answer` / temporal filter `--as-of` / `--changed-since`). Full CLI + HTTP API + MCP surface coverage, env vars, composition examples. Anchors the "3 primitives, 1 file, any LLM" tagline.
- **`paper/paper-tecnico-nox-mem.md` §2.5 "User-Facing Primitives"** (NEW) — inserted between §2.4 Multi-Agent Memory Architecture and §3 Memory Pipeline. Documents the three primitives with semantics, latency claims (p95 = 101.74ms offline answer), and the temporal filter as the closure for Gap #2 (temporal decay) of the Six Gaps reframe.
- **`README.md`** — new "3 primitives, 1 file, any LLM" section after Quick Start with primitive comparison table + composition examples. Step 7 of Quick Start now demonstrates `--as-of` / `--changed-since`.
- **Underlying implementations unchanged** — P1 `answer` (PRs #3, #18, #31, #34, #40, #114, #283) and P3 temporal filter (PRs #2, #167) are LIVE in prod since well before this doc PR. This entry is documentation work only.

### Added — 2026-05-21 morning burst (9 PRs landed em ~3h)

- **vec0 reindex fix** — sqlite-vec load defensive em `_reindexImpl` (`staged-1.7a/edits/reindex.ts`); fixes 6× retry loop em CLI reindex; api-server unaffected (vec0 bundle commit `9ad77eb`)
- **opsAudit hygiene** — table rebuild para `started_at` INTEGER + 2 enforcement triggers + test-% row cleanup; `/api/health.opsAudit.total_24h` went 48 phantom → 1 real (#193)
- **GTM README hero upgrade** — Q/A/P pillar badges + 6 stat cards + headline numbers + Quick-start promoted; D43 Q4 gate dispatched (#190)
- **Per-method benchmark spec** — 520 LOC plan pra comparison nox-mem vs Mem0/Zep/EverCore/HyperMem em LongMemEval + EverMemBench (#191)
- **G10b/G10c/G10d/D51** — per-category + per-style + conditional mutex spec + decision template (#188, #189, #192, #198)
- **Memory cross-link audit + normalization** — 39 broken refs identified → 1 → 0 (#194, #197)
- **L4 regex-first extraction** — shadow-mode default; Tier 1 regex + Gemini fallback orchestration via `NOX_KG_EXTRACT_MODE` (#195)
- **A2 export/import T1** — AES-256-GCM + scrypt KDF + AAD-bound manifest; 11 tests including tamper + 2-instance roundtrip (Autonomy pillar, #196)
- **G10c paper §5.5 addendum** — natural-language win / keyword drag breakdown

### Defense

- **Pre-commit hook global** — `~/.git-hooks-global/pre-commit` blocks non-main branch commits do parent path; recovers from agent worktree contamination automatically; override `COMMIT_TO_NON_MAIN_OK=1`

### Pending Wave F
- A1.1 Brazilian PII patterns (CPF/CNPJ/pix/CEP/RG)
- G1 passphrase entropy enforcement (zxcvbn)
- G5 central error response sanitizer (strip stack traces)
- G4/G6/G7/G8/G10 security audit followups bundle
- Threat-model Wave-E.1 follow-up (P5/L2/P2/A2 sections)
- GitHub project hygiene (this file)
- MEMORY review + DOCS.md navigation hub

---

## [1.0.0-wave-e] — 2026-05-18

### Added — Wave E

- OpenAPI 3.1 spec for all HTTP endpoints (#53)
- CONTRIBUTING.md + QUICKSTART.md + CONFIGURATION.md (#54)
- THREAT-MODEL.md — STRIDE analysis + 10 gaps identified (#55)
- integrations/ scaffold — 13 IDEs + MCP tools reference + CLI recipes (#56)
- Wave C+D post-mortem documentation (#52)

### Added — Wave D

- README.md final — replaces 752-line DRAFT (#46)
- Q4 COMPARISON.md populated with Wave B real numbers + competitor positioning (#47)
- COMPETITIVE-POSITIONING.md — Six Gaps × nox-mem + agentmemory + gbrain matrix (#49)
- QA matrix — typecheck + tests across 13 staged-* dirs, 6/6 packages green (#50)
- 8 new auto-memories (local) capturing Wave B operational lessons

### Added — Wave C

- L3 confidence + provenance field — write paths + mark workflow (#48). Ranking integration **gated** by eval lift ≥1.0pp.
- L2 KG conflict detection — Type 1 (direct contradiction) end-to-end (#51). Differentiator vs memanto Gap #5.
- DEPLOY-WAVE-B.md — VPS deployment guide for all staged patches (#45)
- HANDOFF.md update + Wave B post-mortem (#44)

### Added — Wave B

- P2 hooks auto-capture — 5 privacy layers ordered, content NEVER in telemetry (#43)
- P5 viewer real-time SSE — 11.7KB bundle (4× under 50KB target) (#42)
- A2 export/import T10-T18 — CLI + HTTP + MCP + round-trip + docs + bench (#41); AAD chain bug caught via integration test
- P1 answer T11-T14 — integration tests + E2E Gemini + docs + latency bench (#40); p95 ~101ms (42× under 4.3s budget)
- A3 provider abstraction T9-T16 — fallback chain + cost cap + 15 refactor sites + telemetry (#39); overhead ~0.0025ms abs
- L4 regex-first T7-T9 — stale-link reconcile + eval + production wire (#38); 95.8% precision, 80% Gemini calls saved

### Added — Pre-Wave B (overnight 2026-05-17 + morning 2026-05-18)

#### Specs / kickoffs
- A1 privacy filter spec (#5), A2 export/import spec (#9), A3 provider abstraction spec (#8)
- P1 answer primitive spec (#3), P2 hooks spec (#4), P4 connect IDE spec (#7), P5 viewer spec (#10)
- Q1 LoCoMo harness scaffold (#6), Q2 LongMemEval scaffold (#11 + #29 CLI)
- L4 regex-first KG extraction spec (#27)
- L2 + L3 specs (existing pre-Wave B)
- Implementation kickoffs: A2 (#17), A3 (#25), P1 (#18), P2 (#24), P5 (#26)
- VISION v15 update integrating Q/A/P pivot (#32)

#### Implementations (Wave B precursors)
- P1 answer T1-T4 core (#31) + T5-T10 CLI/HTTP/MCP/telemetry (#34)
- A2 archive + AES-256-GCM encryption T1-T9 (#37)
- A3 provider abstraction core T1-T8 (#36)
- L4 regex-first extraction T1-T6 (#35)
- P5a event bus refactor (#33) — prerequisite for P5
- Schema migrations v11 + v19 additive (#28)

#### Infrastructure
- CI workflows — eval harnesses + privacy filter + zero-vendor + typecheck (#30)
- README-DRAFT + assets (palette D minimal + #00C896 accent) (#22 + #19)

### Schema migrations

| Version | What | PR / sprint |
|---|---|---|
| v11 | answer_telemetry + agent_events + provider_telemetry | #28 |
| v19 | chunks.confidence + provenance_kind + kg_relations.confidence + superseded_by + extraction_method | #28 |
| v20 | viewer_telemetry | P5 (#42) |
| v21 | conflict_audit with append-only triggers | L2 (#51) |
| v22 | confidence_eval_log | L3 (#48) |

### Security

- AES-256-GCM at rest for archives (A2) with scrypt KDF (N=2^17)
- PII redaction via 13-pattern regex filter (A1) — FP rate 1.7%
- Provider abstraction prevents vendor lock-in (A3) — Gemini default, OpenAI/Anthropic/Voyage stubs
- Append-only audit logs (ops_audit, conflict_audit, viewer_telemetry, agent_events) — DB triggers prevent DELETE
- Privacy-by-default for SSE viewer (`NOX_VIEWER_SHOW_QUERY` opt-in, queries redacted by default)
- Shadow discipline (CLAUDE.md regra #5) — no ranking change without ≥7d shadow validation

### Architectural decisions

- D40 — Q/A/P pillars strategic pivot (2026-05-17)
- D41 — 5 cross-cutting decisions resolved + 5 polish bonus (2026-05-18)
- Tagline locked: *"Pain-weighted hybrid memory with shadow discipline — yours by design."* (D45 — supersedes D40)

### Documentation

- VISION.md v15 (post-D40 + D41 pivot)
- ROADMAP.md restructured into Q/A/P + Lab + GTM
- CLAUDE.md regras críticas (6 operational rules)
- INDEX.md catálogo

---

## [0.x] — Pre-Wave-B history

See `docs/EVOLUTION.md` for full version history v1.0 → v3.7.

Key milestones:
- v3.7 — Schema v10 (section_boost) + salience formula
- v3.6 — Cross-search + reflect
- v3.5 — Hybrid search (BM25 + sqlite-vec + RRF)
- v3.4 — KG entities + relations
- v3.0 — sqlite-vec integration
- v2.x — FTS5 search
- v1.x — initial chunks + retention

---

## How this changelog is maintained

- New PRs are added under `[Unreleased]` until next release
- Releases are tagged via `git tag v<version>`
- Wave-grouped releases (Wave A through F) follow this session's autonomous push pattern
- Maintainer: see CONTRIBUTING.md

## Cross-references

- [README.md](README.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [docs/HANDOFF.md](docs/HANDOFF.md) — current state
- [docs/DECISIONS.md](docs/DECISIONS.md) — D40 + D41 + history
- [docs/EVOLUTION.md](docs/EVOLUTION.md) — full version history
