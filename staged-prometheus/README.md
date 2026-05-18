# staged-prometheus — Wave J

Prometheus / OpenMetrics exporter + cross-pillar instrumentation for nox-mem.

## What ships

- `edits/src/observability/` — TypeScript ESM, zero runtime deps
  - `types.ts` — Counter, Gauge, Histogram primitives + label helpers
  - `registry.ts` — singleton MetricsRegistry
  - `metrics.ts` — 28 metric catalog
  - `cardinality.ts` — per-metric maxSeries + allowlist/denylist guard
  - `privacy-guard.ts` — PII strip (A1 / A1.1 patterns) + label sanitization
  - `record.ts` — fire-and-forget recording API
  - `exporter.ts` — `/metrics` handler (OpenMetrics text, gzip, bearer auth, ?names filter)
  - `collectors/` — process / db-stats / search-telemetry / provider-telemetry / eventbus
  - `adapters/` — p1 (answer) / a3 (provider) / p5 (viewer)
  - `index.ts` — public barrel
  - `__tests__/` — node:test suites (54 cases across 8 files)
- `edits/docs/PROMETHEUS-METRICS.md` — 765-line operator + dev reference

## Wiring (when merged)

1. Move `edits/src/observability/` → `src/observability/`.
2. Move `edits/docs/PROMETHEUS-METRICS.md` → `docs/PROMETHEUS-METRICS.md`.
3. Register `/metrics` route in API server (see doc §10.1).
4. Bootstrap collectors at startup (see doc §6).
5. Apply adapters at integration points (P1, A3, P5).

## Tests

```bash
# When tsx is available
npx tsx --test src/observability/__tests__/*.test.ts
# Or after tsc compile
node --test dist/src/observability/__tests__/*.test.js
```

## Invariants (non-negotiable)

- No PII in labels.
- No unbounded cardinality.
- Fire-and-forget recording (never blocks hot path).
- OpenMetrics text format.

See `edits/docs/PROMETHEUS-METRICS.md` for full operator guide.
