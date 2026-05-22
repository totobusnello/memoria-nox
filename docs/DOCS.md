# Documentation hub

> One-page navigation for ~60 docs accumulated across memoria-nox.
> If you cannot find it here, check [ROADMAP.md](ROADMAP.md) or [DECISIONS.md](DECISIONS.md).
>
> Status legend: no badge = live in main · `[pending]` = PR open, not merged yet

---

## By role

### New to nox-mem? Start here

- [../README.md](../README.md) — 5-min overview: what it is, numbers, quick install
- [VISION.md](VISION.md) — long-term strategic positioning (v15, Q/A/P pillars)
- [ARCHITECTURE.md](ARCHITECTURE.md) — schema V10, hybrid search stack, interfaces
- `docs/QUICKSTART.md` `[pending]` — install + first query (PR #54)
- `docs/CONFIGURATION.md` `[pending]` — env vars reference (PR #54)

### Contributing?

- [CONTRIBUTING.md](CONTRIBUTING.md) — how to open issues, submit PRs, run tests
- [CONVENTIONS.md](CONVENTIONS.md) — code style, commit format, naming rules
- [DEPLOY-WAVE-B.md](DEPLOY-WAVE-B.md) — VPS deploy steps for staged-* patches
- [openapi.yaml](openapi.yaml) — OpenAPI 3.1 spec for all HTTP endpoints (canonical, v1.0.0-rc1)
- [openapi/README.md](openapi/README.md) — API spec generation guide

### Doing security review?

- `docs/security/THREAT-MODEL.md` `[pending]` — STRIDE matrix + 10 gaps + control matrix (PR #55)
- `SECURITY.md` `[pending]` — vuln reporting policy (PR #56)
- Memory: `feedback_no_secrets_in_git` — API keys never in git
- Memory: `feedback_execfilesync_over_execsync_for_user_input` — command injection defense
- Memory: `feedback_audit_critical_modules_same_session` — adversarial review pattern
- [audits/](../audits/) — historical code + security audits (2026-04-18 through 2026-04-29)

### Operating in prod?

- [HANDOFF.md](HANDOFF.md) — current state, next action (start here after any break)
- [RUNBOOKS.md](RUNBOOKS.md) — incident runbooks index (nox-mem scope)
- [../runbooks/recovery-from-snapshot.md](../runbooks/recovery-from-snapshot.md) — DB restore via op-audit snapshot
- [../runbooks/rollback-schema-migration.md](../runbooks/rollback-schema-migration.md) — schema rollback procedure
- [../runbooks/rollback-nox-mem-version.md](../runbooks/rollback-nox-mem-version.md) — binary version rollback
- [../runbooks/dr-drill-quarterly.md](../runbooks/dr-drill-quarterly.md) — DR drill checklist
- CLAUDE.md rule #6 — destructive ops gated by `withOpAudit()` + `--dry-run`
- Memory: `reference_a1_op_audit_module` — op-audit snapshot lifecycle
- Memory: `feedback_validate_features_with_db_not_logs` — always verify DB state, not logs

### Strategic / GTM?

- [VISION.md](VISION.md) — long-term: autonomy moat, Q/A/P competitive thesis
- [ROADMAP.md](ROADMAP.md) — Q/A/P pillars + Lab + GTM Phase 2, sprint order, gates
- [COMPETITIVE-POSITIONING.md](COMPETITIVE-POSITIONING.md) — Six Gaps matrix + memanto/agentmemory/gbrain comparison
- [../benchmark/README.md](../benchmark/README.md) — Q4 COMPARISON public framework
- `../benchmark/COMPARISON.md` — competitor comparison matrix (generated, requires `GATE_VERIFIED=1`)
- Memory: `project_qap_pillars_strategic_decision` — D40 pivot rationale + tagline

### Academic / paper?

- [../paper/paper-tecnico-nox-mem.md](../paper/paper-tecnico-nox-mem.md) — primary technical paper (PT-BR)
- [../paper/publication/00-INDEX.md](../paper/publication/00-INDEX.md) — publication pipeline index
- [../paper/publication/04-paper-arxiv-draft.md](../paper/publication/04-paper-arxiv-draft.md) — arXiv draft
- [../paper/publication/RESUMO-EXECUTIVO.md](../paper/publication/RESUMO-EXECUTIVO.md) — executive summary (PT-BR)
- [../paper/publication/SUBMIT-DAY-RUNBOOK.md](../paper/publication/SUBMIT-DAY-RUNBOOK.md) — submission day checklist

---

## By topic

### Architecture

| Doc | Purpose |
|---|---|
| [VISION.md](VISION.md) | Strategic direction, competitive moat, long-term |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Schema V10, search stack, CLI/HTTP/MCP interfaces |
| [CONVENTIONS.md](CONVENTIONS.md) | Code patterns, scoring rules, naming |
| [DECISIONS.md](DECISIONS.md) | D1–D41: every architectural pivot + rationale + rejected alternatives |
| [EVOLUTION.md](EVOLUTION.md) | Version history v1.0→v3.7, schema timeline |
| [../specs/](../specs/) | Sprint specs (20+ files, 2026-04-12 → 2026-05-18) |

### Q/A/P Pillars

| Pillar | Specs | Impl / PRs |
|---|---|---|
| **Q — Quality** | [Q1 LoCoMo](../eval/locomo/README.md), [Q2 LongMemEval](../eval/longmemeval/README.md), [Q3 Latency](../eval/latency/README.md) | scaffolds + PR #47 Q4 matrix |
| **A — Autonomy** | [A2 export/import](../specs/2026-05-17-A2-export-import.md), [A3 providers](../specs/2026-05-18-A3-implementation-kickoff.md) | PRs #35–#37, #39–#41 + staged-A2/A3 |
| **P — Product** | [P1 answer](../specs/2026-05-17-P1-answer-primitive.md), [P2 hooks](../specs/2026-05-17-P2-hooks-autocapture.md), [P3 temporal](../specs/2026-05-18-P1-implementation-kickoff.md), [P4 IDE](../specs/2026-05-17-P4-connect-ide.md), [P5 viewer](../specs/2026-05-17-P5-viewer-realtime.md) | PRs #2, #31, #34, #40, #42, #43 + staged-P1/P3/P5a |
| **Lab** | [L2 conflict](../specs/2026-05-17-L2-conflict-detection.md), [L3 confidence](../specs/2026-05-17-L3-confidence-field.md), [L4 regex extract](../specs/2026-05-18-L4-regex-first-extraction.md) | PRs #35, #38, #48, #51 |
| **GTM Phase 2** | [spec](../specs/2026-05-17-GTM-readme-hero-upgrade.md), [assets](../README-DRAFT.md) | locked behind Q4 gate |

### Security

- `docs/security/THREAT-MODEL.md` `[pending]` — STRIDE + 10 gaps + Wave B controls (PR #55)
- `SECURITY.md` `[pending]` — vuln reporting (PR #56)
- A1 privacy filter — `staged-privacy/edits/` (13 patterns, 68 tests, FP 1.7%)
- A2 encryption — AES-256-GCM + scrypt + AAD, in `staged-A2/edits/src/lib/archive/`
- A3 secret redaction — `redactSecrets` on error paths, in `staged-A3/edits/`
- Memory: `feedback_no_secrets_in_git` — secrets never in git (hard rule)
- Memory: `feedback_execfilesync_over_execsync_for_user_input` — command injection defense
- Memory: `feedback_buffer_pool_aliasing_in_typed_arrays` — GC aliasing semantic bug
- Memory: `feedback_audit_must_check_prod_state_not_only_code` — code fixes != prod fixes

### Schema

- [ARCHITECTURE.md](ARCHITECTURE.md) — schema V10 overview + `chunks`, `vec_chunks`, `kg_entities`, `kg_relations`
- [DECISIONS.md](DECISIONS.md) — D1–D41 includes schema pivots (v8 retention, v9 pain, v10 section)
- Schema migrations: v11 telemetry (`search_telemetry`), v19 confidence + provenance, v20 viewer (`viewer_events`), v21 `conflict_audit`, v22 `confidence_eval_log` — all in `staged-migrations/`
- [../staged-migrations/README.md](../staged-migrations/README.md) — migration application guide

### Search

- [ARCHITECTURE.md](ARCHITECTURE.md) §Hybrid Search — 3-layer pipeline: FTS5 BM25 → Gemini semantic → RRF (k=60)
- [../specs/2026-05-10-E14-retrieval-evolution.md](../specs/2026-05-10-E14-retrieval-evolution.md) — E14 language-aware RRF (+1.92pp, no regression)
- Memory: `feedback_fts5_vanilla_and_strict_explains_zero_recall` — FTS5 AND-strict design, always compare to hybrid
- Memory: `feedback_shadow_mode_for_ranking_changes` — ship ranking changes in shadow-mode first

### Operations

- [HANDOFF.md](HANDOFF.md) — current state + next action (always start here)
- CLAUDE.md — 6 critical operational rules (destructive ops, snapshot, models, ports, scoring, sed)
- [DEPLOY-WAVE-B.md](DEPLOY-WAVE-B.md) — VPS apply guide for staged patches
- [RUNBOOKS.md](RUNBOOKS.md) — runbook index
- [../runbooks/](../runbooks/) — 5 runbooks: recovery, rollback-schema, rollback-version, DR drill, cost projection
- [INCIDENTS.md](INCIDENTS.md) — incident log (memoria scope)
- [post-mortems/WAVE-B-2026-05-18.md](post-mortems/WAVE-B-2026-05-18.md) — Wave B post-mortem
- [post-mortems/WAVE-CD-2026-05-18.md](post-mortems/WAVE-CD-2026-05-18.md) — Wave C+D post-mortem

### Evaluation

- [../eval/locomo/README.md](../eval/locomo/README.md) — Q1 LoCoMo harness (scaffold, pending full run)
- [../eval/longmemeval/README.md](../eval/longmemeval/README.md) — Q2 LongMemEval harness (scaffold, pending full run)
- [../eval/latency/README.md](../eval/latency/README.md) — Q3 latency benchmark (p50/p95/p99)
- [../benchmark/README.md](../benchmark/README.md) — Q4 COMPARISON framework (public)
- Memory: `project_benchmark_gap_longmemeval_locomo` — why standardized benchmarks matter

### Integrations

All `integrations/` docs are `[pending]` (PR #57, not yet merged):
- `integrations/README.md` — overview + quick-start by integration type
- `integrations/ide/` — 13 IDE guides (Claude Code, Cursor, Cline, Continue, Aider, etc.)
- `integrations/mcp/` — MCP server + 16 tools reference
- `integrations/cli/` — CLI recipes + scripting guide

### Audits

- [../audits/](../audits/) — historical code + security audits
  - `2026-04-18`: DB gaps remediation, perf baseline, SRE deepening
  - `2026-04-25`: A1+A2 review, 7-highs followup
  - `2026-04-26`: A1v2+A3-A5 review, W2 cleanup, B1-B2 zombie fix
  - `2026-04-29`: code review A1–A6
  - `reviews-phase-1.8/`: architect + SRE + security + product + baselines

### Paper / publication

- [../paper/publication/00-INDEX.md](../paper/publication/00-INDEX.md) — full pipeline index
- [../paper/publication/04-paper-arxiv-draft.md](../paper/publication/04-paper-arxiv-draft.md) — arXiv draft (Path B, English)
- [../paper/publication/RESUMO-EXECUTIVO.md](../paper/publication/RESUMO-EXECUTIVO.md) — executive summary PT-BR
- [../paper/publication/SUBMIT-DAY-RUNBOOK.md](../paper/publication/SUBMIT-DAY-RUNBOOK.md) — submission checklist
- [../paper/publication/07-publication-checklist.md](../paper/publication/07-publication-checklist.md) — pre-publish checklist
- [../paper/publication/08-launch-strategy.md](../paper/publication/08-launch-strategy.md) — launch + distribution plan

### Reference

- `docs/CONFIGURATION.md` `[pending]` — env vars (28+ vars, PR #54)
- [openapi.yaml](openapi.yaml) — formal HTTP API spec (OpenAPI 3.1, canonical v1.0.0-rc1)
- [openapi/README.md](openapi/README.md) — how to regenerate + validate spec
- [../validation/zero-vendor/README.md](../validation/zero-vendor/README.md) — A4 zero-vendor checks (8 invariants, CI <1s)
- CLAUDE.md — per-project rules (nox-mem entry point for VPS credentials + critical rules)

---

## By status

### Live in main (HEAD: #53)

| Category | Docs |
|---|---|
| Core docs | README.md, CLAUDE.md, ARCHITECTURE.md, VISION.md, ROADMAP.md, DECISIONS.md, HANDOFF.md, CONVENTIONS.md, EVOLUTION.md, INCIDENTS.md, RUNBOOKS.md |
| Wave docs | CONTRIBUTING.md, DEPLOY-WAVE-B.md, COMPETITIVE-POSITIONING.md, QA-MATRIX-WAVE-B.md, openapi.yaml+openapi/README.md, post-mortems/WAVE-B + WAVE-CD |
| Specs | 20 spec files (2026-04-12 through 2026-05-18) |
| Evals | eval/locomo, eval/longmemeval, eval/latency (scaffolds) |
| Benchmark | benchmark/README + COMPARISON template |
| Runbooks | 5 VPS runbooks |
| Staged | staged-A2, staged-A3, staged-L4, staged-P1, staged-P3, staged-P5a, staged-privacy, staged-migrations (pending VPS deploy) |

### Pending merge

| PR | Contents | Key docs |
|---|---|---|
| #54 | Wave E docs fill | `docs/QUICKSTART.md`, `docs/CONFIGURATION.md` |
| #55 | THREAT-MODEL | `docs/security/THREAT-MODEL.md` |
| #56 | GitHub hygiene | `SECURITY.md`, `CHANGELOG.md`, `CODE_OF_CONDUCT.md`, issue/PR templates |
| #57 | Integrations scaffold | `integrations/` (13 IDEs + MCP + CLI) |

### Pending VPS deploy

All `staged-*/edits/` patches are in main but not yet applied to VPS `/root/.openclaw/workspace/tools/nox-mem/src/`.
Apply via [DEPLOY-WAVE-B.md](DEPLOY-WAVE-B.md).

### Future (specced, not started)

- P3 real IDE plugin implementations (Tier A — beyond stub)
- Q1 LoCoMo full run (requires VPS)
- Q2 LongMemEval full run (requires VPS)
- L3 ranking activation (gated: requires ≥1.0pp eval lift)
- L2 Type 2+3+4 conflict detection (T2+ extend existing T1)
- GTM Phase 2 README flip (gated: requires Q4 COMPARISON win)

---

## By recency

| Date | Event | Docs added/updated |
|---|---|---|
| 2026-05-18 | Wave B–D + PRs #38–#53 | DEPLOY-WAVE-B, COMPETITIVE-POSITIONING, QA-MATRIX, post-mortems, openapi, HANDOFF |
| 2026-05-18 | Wave F (this session) | docs/DOCS.md (this file), docs/MEMORY-REVIEW-2026-05-18.md |
| 2026-05-17 | D40 Q/A/P pivot + overnight | ROADMAP v2, DECISIONS D40, VISION v15, MORNING-REVIEW-2026-05-18 |
| 2026-05-15 | op-audit gaps review | plans/2026-05-15-op-audit-gaps-review |
| 2026-05-10 | E14 retrieval evolution | specs/2026-05-10-E14 |
| 2026-05-07 | D01 cross-encoder (CUT), E12 OCR | specs/2026-05-07-* |
| 2026-05-06 | E05b/E13 specs | specs/2026-05-06-* |
| 2026-05-01 | E03a SPO injection, F10 observability | specs/2026-05-01-* |
| 2026-04-29 | Code review A1–A6 | audits/2026-04-29 |
| 2026-04-27 | R01a eval harness spec | specs/2026-04-27-R01a |
| 2026-04-26 | op-audit B1/B2/W2 fixes | audits/2026-04-26-* |
| 2026-04-25 | A1–A5 audits | audits/2026-04-25 |

Full version timeline: [EVOLUTION.md](EVOLUTION.md).

---

## Session logs (historical)

Verbatim logs of key working sessions — useful for archaeology but not for day-to-day:

- `docs/SESSION-2026-05-04-FULL-LOG.md`
- `docs/SESSION-2026-05-05-FULL-LOG.md`
- `docs/SESSION-LOG-2026-05-06.md`
- `docs/MORNING-REVIEW-2026-05-18.md` — morning review playbook (2026-05-18)

---

## How this doc is maintained

- Add new docs here in the same PR that creates them.
- Link new specs under the relevant pillar row in the Q/A/P table above.
- Quarterly: check for dead links (`find docs/ -name "*.md" | xargs grep -h '\[.*\](.*\.md)' | grep -v http`).
- Maintainer guidance: see [CONTRIBUTING.md](CONTRIBUTING.md).
