---
title: Product Pillar (P)
description: Answer primitive, hooks, temporal queries, IDE connect, viewer, mobile, and browser extension.
sidebar:
  order: 3
---

> UX that wins. Features that make memory feel like memory, not like a search engine.

## P1 — Answer primitive

Source: [`specs/2026-05-17-P1-answer-primitive.md`](https://github.com/totobusnello/memoria-nox/blob/main/specs/2026-05-17-P1-answer-primitive.md)

Grounded answers with citations. Every claim is backed by a source chunk ID and score — you can verify every answer from the SQL up.

```bash
nox-mem answer "what is the salience formula?"
```

```
The salience formula is: salience = recency × pain × importance

Where:
- recency: exponential decay from creation timestamp
- pain: chunk severity (0.1 trivial → 1.0 prod-outage)
- importance: ingest-time or inferred importance score

Currently in shadow mode (NOX_SALIENCE_MODE=shadow).

Sources:
  [1] chunks#1847 (score 0.912): docs/ARCHITECTURE.md §Salience
  [2] chunks#2103 (score 0.887): specs/2026-05-17-P1...
```

## P2 — Hooks + autocapture

Source: [`specs/2026-05-17-P2-hooks-autocapture.md`](https://github.com/totobusnello/memoria-nox/blob/main/specs/2026-05-17-P2-hooks-autocapture.md)

Event hooks that fire before/after ingest, search, and answer operations. Enables:
- Autocapture from clipboard, file watchers, shell history
- Webhook notifications on memory events
- Custom processing pipelines (e.g., summarize before storing)

T1–T15 complete.

## P3 — Temporal queries

Temporal-aware queries using the `created_at` + `retention_days` fields:

```bash
nox-mem search "deployment issues" --since 7d
nox-mem search "project decisions" --type decision --before 2026-04-01
```

## P4 — IDE connect

Source: [`specs/2026-05-17-P4-connect-ide.md`](https://github.com/totobusnello/memoria-nox/blob/main/specs/2026-05-17-P4-connect-ide.md)

Native integrations for 14 editors. See [IDE Plugins](/memoria-nox/integrations/ide) for current status.

MCP integration works in all supported editors today. Native plugins (autocomplete, sidebar) are in active development (Tier A).

## P5 — Viewer realtime

Source: [`specs/2026-05-17-P5-viewer-realtime.md`](https://github.com/totobusnello/memoria-nox/blob/main/specs/2026-05-17-P5-viewer-realtime.md)

Realtime memory viewer — a web UI showing live corpus state, recent ingests, search activity, and KG visualization. T1–T15 complete.

Access at: `http://127.0.0.1:18802/viewer` (when `nox-mem serve` is running)

## P5a — Event bus refactor

Decouples the viewer and hook system from direct DB polling via an in-process event bus. Enables multiple consumers without N×polling overhead. In progress.

## P6 — Mobile (specced)

iOS and Android native apps for on-the-go memory capture and search. Spec: [`specs/2026-05-17-P6-mobile.md`](https://github.com/totobusnello/memoria-nox/blob/main/specs/2026-05-17-P6-mobile.md)

Connects to the HTTP API over local network or VPN. Push notifications for memory events.

## P7 — Browser extension (specced)

Capture and search from any web page. Right-click to send selection to memory. Keyboard shortcut to open search overlay. Spec in progress.
