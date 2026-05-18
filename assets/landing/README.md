# assets/landing — Static GTM landing page

Vanilla HTML + CSS + minimal JS. No framework, no tracker.

Deploys to GitHub Pages or Vercel without a backend.

## Files

| File | Purpose |
|---|---|
| `index.html` | One-page landing (EN, international) |
| `style.css` | Palette D — dark/light via `prefers-color-scheme` |
| `app.js` | Scroll-reveal only — no analytics, no external calls |
| `screenshots/` | Placeholder for demo screenshots (populate before GTM launch) |

## Design constraints

- **Palette D:** `#0d1117` / `#fafafa` bg, `#00C896` accent
- **No tracking** — no Google Analytics, no Plausible (gate: GTM Phase 2)
- **<50 KB total** — matches P5 viewer bundle constraint
- **Static** — no server-side rendering required

## Status

GTM Phase 2 is gated on Q4 COMPARISON result per `docs/ROADMAP.md`.
This mockup is ready for review; activation follows gate decision.

## Updating numbers

All displayed metrics come from verified benchmarks. Before updating any stat:
1. Confirm the number in the relevant eval harness output or PR
2. Do not add numbers that are pending or estimated
3. Update `index.html` only — numbers are inline, not pulled from a config file

## Adding screenshots

Drop PNG/WebP files into `screenshots/` and reference them via `<picture>` elements
in `index.html`. Use the same dark/light pattern as the banner and architecture diagrams.

## Local preview

```bash
# Any static file server works
npx serve assets/landing
# or
python3 -m http.server --directory assets/landing 8080
```
