---
title: Changelog
description: Release history and notable changes for memoria-nox.
sidebar:
  order: 3
---

Full source: [`CHANGELOG.md`](https://github.com/totobusnello/memoria-nox/blob/main/CHANGELOG.md)

## v3.7 (2026-05-18)

### Q/A/P Pillars (D40 pivot)

- Roadmap reorganized into Quality / Autonomy / Product + Lab + GTM Phase 2
- Tagline locked: *"Pain-weighted hybrid memory with shadow discipline — yours by design."* (D45 — supersedes D40)

### Quality

- **E14 language-aware RRF** — +1.92pp nDCG, zero regression (Wave 1)
- **graph-memory parse failure** — 19.7% → 0% via bracket-balance matcher (fix #1b4f7ec)
- **Q1 LoCoMo / Q2 LongMemEval** — eval harness scaffolds live
- **Q4 COMPARISON** — public benchmark framework published

### Autonomy

- **A2 export/import** — portable archive with AES-256-GCM + scrypt encryption
- **A3 provider abstraction** — Gemini/OpenAI/local swap layer
- **A4 zero-vendor validation** — 8 invariants, CI <1s
- **A1.1 BR PII patterns** — 13 patterns, 68 tests, FP 1.7%

### Product

- **P1 answer primitive** — grounded responses with citations
- **P2 hooks + autocapture** — T1–T15 complete
- **P3 temporal queries** — complete
- **P5 viewer realtime** — T1–T15 complete
- **P5a event bus refactor** — in progress

### Lab

- **L2 conflict detection** — Type 1 done
- **L3 confidence field** — T1–T13 done
- **L4 regex-first extraction** — parse failure 19.7% → 0%

### Infrastructure

- OpenAPI 3.1 spec published (`docs/openapi/openapi.yaml`)
- Prometheus metrics endpoint (F10)
- 6 SDK scaffolds (TypeScript, Python, Rust, Go, Java, .NET)
- 14 IDE integration specs
- Threat model + STRIDE matrix
- OpenSSF path documentation

---

## v3.6d (2026-04-29)

- A1–A6 code review + 7 CRITICAL security fixes
- op-audit B1/B2 zombie fix
- W2 cleanup (append-only triggers hardened)

## v3.6 (2026-04-27)

- Corpus tripled in 1 day: 20,831 → 62,836 chunks
- A1–A5 + A6 batch + R01a eval spec

## v3.5 (2026-04-25)

- `withOpAudit()` destructive ops guard
- Snapshot creation + `safeRestore()`
- `ops_audit` append-only triggers

## v3.4 (2026-04-23)

- Schema v10: `section` + `section_boost`
- Entity file ingest router
- Incident v3.4: multiplicative boost removed (additive only)

See [`docs/EVOLUTION.md`](https://github.com/totobusnello/memoria-nox/blob/main/docs/EVOLUTION.md) for full version history v1.0 → current.
