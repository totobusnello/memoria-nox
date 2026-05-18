# Architecture Decision Records (ADRs)

This directory contains formal Architecture Decision Records (ADRs) using the [Michael Nygard template](https://github.com/joelparkerhenderson/architecture-decision-record/blob/main/templates/decision-record-template-by-michael-nygard/index.md).

## Index

| ADR | Title | Status | Date |
|---|---|---|---|
| [001](ADR-001-hybrid-search.md) | Hybrid search (BM25 + sqlite-vec + RRF) | Accepted | 2024-04-01 |
| [002](ADR-002-append-only-audit.md) | Append-only audit logs | Accepted | 2026-04-25 |
| [003](ADR-003-shadow-discipline.md) | Shadow discipline for ranking changes | Accepted | 2026-04-27 |
| [004](ADR-004-qap-pillars-pivot.md) | Q/A/P pillars strategic pivot | Accepted | 2026-05-17 |
| [005](ADR-005-data-autonomy-moat.md) | Data autonomy as primary moat | Accepted | 2026-05-17 |
| [006](ADR-006-d41-cross-cutting.md) | D41 5 cross-cutting decisions | Accepted | 2026-05-18 |
| [007](ADR-007-threat-model-quarterly.md) | Threat-model recursive iteration | Accepted | 2026-05-18 |
| [008](ADR-008-provider-abstraction.md) | Provider abstraction over vendor lock-in | Accepted | 2026-05-17 |

## How to add a new ADR

1. Copy [ADR-TEMPLATE.md](ADR-TEMPLATE.md)
2. Number sequentially (next available)
3. Status starts "Proposed"; after team review → "Accepted"
4. If superseding an earlier ADR, mark the old one "Superseded by ADR-XXX"
5. ADRs are immutable — never edit accepted ones, write a new ADR

## Why ADRs?

- **Searchable:** uniform format makes decision archaeology easier
- **Stable:** immutable history prevents revisionism
- **Self-contained:** each ADR readable in isolation
- **Onboarding:** new contributors can read the top 5 ADRs to understand the "why" behind key decisions

## Relationship to DECISIONS.md

`docs/DECISIONS.md` is the chronological narrative log (D1, D2, … Dn) — kept for historical context and append-only operational notes.

ADRs are formalized decisions with stable structure — derived from DECISIONS.md entries but self-contained enough to be read without that file.

ADRs are added retrospectively as needed; not every DECISIONS entry warrants an ADR.

## Quick start: how to use this

- **"Why X over Y?"** — search ADRs first
- **Proposing a change that conflicts with an ADR** — write a new ADR superseding the old one; never edit in place
- **Onboarding a new contributor** — point them to this index first
