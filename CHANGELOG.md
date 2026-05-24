# Changelog

All notable changes to memoria-nox are documented in this file.

The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
