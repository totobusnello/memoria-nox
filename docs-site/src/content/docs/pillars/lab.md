---
title: Lab (Research)
description: Experimental features — conflict detection, confidence, and regex-first extraction.
sidebar:
  order: 4
---

> Lab runs at 40% capacity. Ideas ship here before they earn a pillar slot.

The Lab track hosts research ideas that need more evidence before committing to product. Lab features run in shadow or behind feature flags — they never affect prod retrieval until they prove their worth.

## L2 — Conflict detection

Source: [`specs/2026-05-17-L2-conflict-detection.md`](https://github.com/totobusnello/memoria-nox/blob/main/specs/2026-05-17-L2-conflict-detection.md)

Detects when two chunks contain contradictory information.

**Type 1 (done):** Direct semantic negation — "X is Y" vs "X is not Y". Detection via embedding cosine + negation pattern matching.

**Types 2–4 (specced):** Temporal conflicts (older claim superseded), attribution conflicts (different agents claim different facts), structural conflicts (schema-level contradictions).

Conflicts are logged to `conflict_audit` table (schema v21) and surfaced via `/api/health`.

## L3 — Confidence field

Source: [`specs/2026-05-17-L3-confidence-field.md`](https://github.com/totobusnello/memoria-nox/blob/main/specs/2026-05-17-L3-confidence-field.md)

T1–T13 complete. Every chunk can carry a `confidence` score (0.0–1.0) reflecting extraction certainty. Affects ranking when `NOX_SALIENCE_MODE=active` (gated: requires ≥1.0pp eval lift in shadow).

Schema v19 adds `confidence` + `provenance` fields.

## L4 — Regex-first extraction

Source: [`specs/2026-05-18-L4-regex-first-extraction.md`](https://github.com/totobusnello/memoria-nox/blob/main/specs/2026-05-18-L4-regex-first-extraction.md)

**Problem:** LLM-based KG extraction was failing to parse 19.7% of responses when the model returned malformed JSON inside markdown code blocks.

**Solution:** Bracket-balance matcher as a first pass before JSON.parse. Handles cases where the model wraps JSON in \`\`\`json...\`\`\` with trailing text.

**Result:** Parse failure rate 19.7% → 0%.

Commit: `1b4f7ec fix(graph-memory): parse failure 19.7% → 0% via bracket-balance matcher`

## Lab graduation criteria

A Lab feature graduates to a product pillar when:
1. Shadow mode shows ≥1.0pp eval improvement on the golden set
2. No regression on any existing metric
3. Implementation passes security reviewer audit
4. Feature is gated behind a clean env var flag

Features that stagnate in Lab for >90 days are reconsidered for CUT.
