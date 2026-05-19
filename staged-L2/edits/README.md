# staged-L2 — KG conflict detection (memanto Gap #5 differentiator)

> *"Pain-weighted hybrid memory with shadow discipline — yours by design."*

Wave C overnight 2026-05-18 — Type 1 (direct contradiction) detection
end-to-end, shadow-first, append-only audit. Spec:
`specs/2026-05-17-L2-conflict-detection.md`.

Full operator docs: [`docs/CONFLICT-DETECTION.md`](docs/CONFLICT-DETECTION.md).

## Quick start

```bash
cd staged-L2
npm install
npm test
```

## What's in here

| Task | Artifact |
|---|---|
| T1 | `edits/migrations/v21-conflict-audit.sql` — additive, append-only |
| T2 | `edits/src/lib/conflict/types.ts` — type system |
| T3 | `edits/src/lib/conflict/detector-direct.ts` — Type 1 SQL detector |
| T4 | `edits/src/lib/conflict/evidence.ts` — chunk-joined evidence |
| T5 | `edits/src/lib/conflict/audit-writer.ts` — append-only writer |
| T6 | `edits/src/lib/conflict/shadow.ts` — env-gated mode wrapper |
| T7 | `edits/src/cli/conflict.ts` — CLI subcommands |
| T8 | `edits/src/api/conflict.ts` — HTTP handlers |
| T9 | `edits/src/mcp/tools/conflict.ts` — MCP tools |
| T10 | `edits/src/lib/conflict/scheduler.ts` — cron scaffold |
| T11 | `edits/src/lib/conflict/__tests__/integration.test.ts` |
| T12 | `edits/docs/CONFLICT-DETECTION.md` — operator + dev docs |

## Iron laws (per spec)

1. **Shadow-first** — default `NOX_CONFLICT_MODE=disabled`.
2. **No auto-resolution** — v1 NEVER mutates `kg_relations`.
3. **Append-only audit** — DB triggers prevent DELETE/UPDATE on raw cols.
4. **Confidence threshold gate** — default 0.5.
5. **PT-BR** — "você" não "tu".

## Test inventory

100 tests across 11 files (all green). See `docs/CONFLICT-DETECTION.md §13`.
