# assets/readme/ — Visual Asset Registry

**Palette D — Minimal mono + accent**
**Accent chosen:** `#00C896` (success green, dark) / `#00A87A` (darkened 15% for light bg)
**Decision date:** 2026-05-18

## Why success green (#00C896)?

Three options were considered: green (#00C896), yellow-SQLite (#FFBE00), cyan-Gemini (#00B4D8).

Green wins because it carries the "memory is healthy / your data is safe" semantic that aligns directly with nox-mem's core value proposition of shadow-mode discipline and production stability. Yellow maps too closely to warnings/SQLite-vendor branding, risking confusion. Cyan maps to Gemini — the embedding provider — which is accurate but understates nox-mem's provider-agnostic positioning ("yours by design, not Google's"). Green is the sole high-contrast accent that works cleanly on both `#0E0E10` dark and `#F5F5F7` light backgrounds without requiring opacity adjustments. It differentiates nox-mem from the purple-gradient AI slop aesthetic and the orange/amber that clutters the competitive space (memanto, agentmemory both use orange).

## Color tokens

| Token | Dark | Light |
|-------|------|-------|
| Background | `#0E0E10` | `#F5F5F7` |
| Text primary | `#EBEBEB` | `#111111` |
| Text secondary | `#888888` | `#666666` |
| Accent | `#00C896` | `#00A87A` |
| Stroke/border | `#2A2A2E` | `#D8D8DC` |

## Asset inventory

| File | Dimensions | Bytes | Notes |
|------|-----------|-------|-------|
| banner-dark.svg | 720x200 | ~4.4KB | Graph nodes + tagline, dark bg |
| banner-light.svg | 720x200 | ~4.4KB | Graph nodes + tagline, light bg |
| logo-dark.svg | 256x256 | ~2.9KB | [m] monogram concept C, dark |
| logo-light.svg | 256x256 | ~2.8KB | [m] monogram concept C, light |
| stat-locomo-dark.svg | 180x38 | <1KB | 95.X% LoCoMo R@5 (placeholder) |
| stat-locomo-light.svg | 180x38 | <1KB | |
| stat-longmemeval-dark.svg | 180x38 | <1KB | 9X.X% LongMemEval (placeholder) |
| stat-longmemeval-light.svg | 180x38 | <1KB | |
| stat-latency-dark.svg | 180x38 | <1KB | &lt;XXms p95 (placeholder) |
| stat-latency-light.svg | 180x38 | <1KB | |
| stat-scale-dark.svg | 180x38 | <1KB | 69k chunks · 21k relations (live) |
| stat-scale-light.svg | 180x38 | <1KB | |
| stat-opex-dark.svg | 180x38 | <1KB | &lt;$11/mo all-in (live) |
| stat-opex-light.svg | 180x38 | <1KB | |
| stat-tests-dark.svg | 180x38 | <1KB | 950+ tests passing (placeholder) |
| stat-tests-light.svg | 180x38 | <1KB | |
| mermaid/architecture-source.mmd | — | ~2.4KB | Mermaid source for arch diagram |
| architecture-dark.svg | 1000x600 | ~17KB | SVG fallback (mmdc unavailable) |
| architecture-light.svg | 1000x600 | ~16KB | SVG fallback (mmdc unavailable) |

## Render instructions (architecture PNG when mmdc available)

```bash
npm install -g @mermaid-js/mermaid-cli

mmdc -i assets/readme/mermaid/architecture-source.mmd \
     -o assets/readme/architecture-light.png \
     -t default -w 1000 -H 600

mmdc -i assets/readme/mermaid/architecture-source.mmd \
     -o assets/readme/architecture-dark.png \
     -t dark -w 1000 -H 600
```

SVG fallbacks are production-ready and used until PNG renders are committed.

## Design decisions

1. **Icon concept C (`[m]`)** — bracket monogram chosen over option A (n·m monogram).
   Brackets evoke "memory in a box you own" — direct semantic fit for self-hosted, zero lock-in.
   The `[m]` reads instantly at 32x32 favicon scale; dot patterns dissolve at small sizes.

2. **Typography** — labels use `'JetBrains Mono', 'Courier New', monospace` (system-local);
   tagline uses `'Inter', 'Helvetica Neue', sans-serif`. No external CDN — renders in any
   context including GitHub's sanitized Markdown engine.

3. **Stroke weight 1.5px, zero fill on graph edges** — thin strokes signal precision.
   Accent (#00C896) appears only on primary nodes and numbers; connective tissue stays mono.
   Structure in grey, meaning in green.

## Placeholder stats — update when Q4 gate opens

| Stat | Placeholder | Source when real |
|------|-------------|-----------------|
| LoCoMo R@5 | 95.X% | Q1 harness results |
| LongMemEval | 9X.X% | Q2 harness results |
| Latency p95 | &lt;XXms | Q3 benchmark results |
| Tests | 950+ | CI badge count |

Stats `69k chunks / 21k relations` and `<$11/mo` are live and accurate as of 2026-05-18.
