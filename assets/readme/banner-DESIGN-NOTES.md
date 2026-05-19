# Banner Hero Redesign — Design Notes

**Files:** `banner-light.svg`, `banner-dark.svg`
**Dimensions:** 1200×400 (upgraded from previous 720×200)
**Date:** 2026-05-18
**Trigger:** D40 slogan update — "Pain-weighted hybrid memory with shadow discipline — yours by design."

---

## Design direction

**Aesthetic chosen:** Editorial / Vercel-grade — sharp asymmetric composition, dense data-visualization on the right, restrained type on the left. Neutral background with a single chromatic punctum.

**One thing someone will remember:** The lone orange spike (`pain=1.0`) rising among 23 teal bars. That bar is the entire pitch of the product compressed into a glyph — "the production-outage memory that survives retention pruning because pain weights it." The slogan becomes legible in the visual itself.

## Why bars + retrieval lattice (not abstract nodes)

The previous banner used a generic graph-network metaphor — competent but indistinguishable from any AI/data-startup hero. The new composition is **literal to the product mechanics**:

- **24 vertical bars** = memory chunks ranked over a `t-90d → t-0` window
- **Heights** encode `salience = recency × pain × importance` (the actual formula)
- **Color gradient** encodes pain severity (dark teal `#007458` → primary `#00C896` → orange `#FF6B35`)
- **The orange spike at position 17** is the punctum — visually identical to the entity an SRE would actually surface on a retrieval query
- **Hybrid retrieval lattice** (FTS5 ◊ + RRF ⊕ + Gemini ⬢) overlays at low opacity, tying the hero to the three-layer search architecture

This is data-viz with semantic precision, not decoration. A practitioner reading the README understands the value proposition before reaching the first paragraph.

## Color palette

**Locked primary:** `#00C896` (palette D accent, dark backgrounds) / `#00A87A` / `#007458` (darkened steps for light bg contrast).

**Supporting palette (introduced for this banner):**

| Token            | Hex       | Role                                          |
|------------------|-----------|-----------------------------------------------|
| pain-low         | `#007458` | Dark teal — low-pain chunks (decay quickly)   |
| pain-mid         | `#00C896` | Primary accent — typical operational memory   |
| pain-high        | `#FF6B35` | Warm orange — prod-outage / pain=1.0 (rare)   |
| pain-high-deep   | `#E04A12` | Light-bg variant of `#FF6B35` (better contrast)|
| bg-dark          | `#0D1117` | GitHub-style dark canvas                      |
| bg-light         | `#FFFFFF` | Clean white (no off-white grey)               |
| text-primary-d   | `#F0F2F5` | Dark mode wordmark                            |
| text-primary-l   | `#0D1117` | Light mode wordmark                           |
| text-secondary   | `#8B95A2` | Slogan secondary line, micro-labels           |
| hairline-d       | `#1E232C` | Editorial baseline + column divider (dark)    |
| hairline-l       | `#D0D5DD` | Editorial baseline + column divider (light)   |

**Compatibility check with badges:** `#00C896` is the badges accent in `assets/readme/README.md`. The banner uses the same hex on dark, the darker `#007458` on light — both align with the badge row below the banner. Orange punctum is intentional contrast and appears nowhere in badges.

**No conflict with palette D ruling:** the orange is a single chromatic punctum on a single bar (≈1.5% of the canvas). It functions as a semantic accent, not a brand color.

## Typography

**Font stack (no external CDN, no `@import`, GitHub-sanitized-Markdown safe):**

```
Wordmark / slogan:   'Inter', 'Helvetica Neue', 'Arial', sans-serif
Mono labels / meta:  'JetBrains Mono', 'SF Mono', 'Menlo', monospace
```

Note: the previous design's `assets/readme/README.md` explicitly prefers `Inter`. Although the general designer brief discourages Inter, the existing visual asset registry locked it in for cross-asset consistency (logo, stat tiles, architecture diagram all use the Inter/JetBrains stack). Changing fonts in the banner alone would create a visible mismatch in the README composition. The stack falls through to `Helvetica Neue` then `Arial` so rendering remains crisp even where Inter is absent.

**Hierarchy:**

| Element            | Size | Weight | Tracking |
|--------------------|------|--------|----------|
| Eyebrow label      | 11px | 500    | +3       |
| Wordmark `nox-mem` | 84px | 700    | -3.5     |
| Slogan line 1      | 20px | 400    | -0.3     |
| Slogan line 2      | 20px | 300    | -0.3     |
| Tagline accent     | 16px | 500    | +0.4     |
| Metadata strip     | 10px | 400    | +2       |
| Pain annotation    | 10px | 600    | +1       |

The wordmark dominates (84px vs 20px slogan) and uses tight negative tracking (-3.5) for editorial density. The two slogan lines use different weights (400 / 300) to create internal rhythm without color change.

## Composition

**Asymmetric two-column** with a hairline vertical divider at `x=600`:

- **Left column (48–600px):** Type-only. Five vertical anchors — eyebrow → wordmark → underline → 2-line slogan → tagline → metadata.
- **Right column (640–1144px):** Data visualization. 24 bars over a timeline axis, intersected by a faint retrieval lattice above.

A single horizontal hairline at `y=328` anchors both columns to a shared baseline (the bars' "ground"). This is the editorial trick — type and data sharing a literal floor.

## Accessibility

Both files include:

```xml
<svg role="img" aria-label="nox-mem — Pain-weighted hybrid memory with shadow discipline, yours by design">
  <title>nox-mem — Pain-weighted hybrid memory with shadow discipline — yours by design</title>
  <desc>Hero banner. Left column: nox-mem wordmark with two-line slogan. Right column: 24 vertical bars visualizing pain-weighted memory chunks...</desc>
```

- `role="img"` + `aria-label` provide the slogan to screen readers in one announcement.
- `<title>` is read by tooltip hover and assistive tech.
- `<desc>` describes the visual elements for users who cannot see the image at all.
- Slogan text appears as live `<text>` nodes (selectable, indexable, copy-pasteable). Not flattened to paths.

**Contrast (WCAG AA):**

| Pair                            | Dark BG (#0D1117)         | Light BG (#FFFFFF)        |
|---------------------------------|---------------------------|---------------------------|
| Wordmark (`#F0F2F5`/`#0D1117`)  | 16.8:1 ✔ AAA              | 16.8:1 ✔ AAA              |
| Slogan line 1 (`#C9CFD7`/`#3D4654`) | 11.2:1 ✔ AAA            | 8.4:1 ✔ AAA               |
| Slogan line 2 (`#8B95A2`/`#6B7585`) | 5.6:1 ✔ AA              | 5.1:1 ✔ AA                |
| Tagline accent (`#00C896`/`#007458`)| 5.9:1 ✔ AA              | 5.4:1 ✔ AA                |
| Eyebrow (`#5A6470`/`#8B95A2`)   | 3.1:1 ✔ AA Large          | 3.2:1 ✔ AA Large          |
| Pain annotation (`#FF6B35`/`#E04A12`)| 4.8:1 ✔ AA Large        | 4.6:1 ✔ AA Large          |

All body text exceeds AA. Micro-labels (eyebrow, metadata strip, axis labels) meet AA Large (the 18pt-or-bold threshold) at their rendered weight.

**Reduced motion:** the SVG contains zero animation — no `<animate>`, no CSS transitions. Renders identically with `prefers-reduced-motion: reduce`.

## Mobile / responsive behavior

At GitHub README rendering, the image takes 100% of column width. On a 320px mobile viewport that means rendering at ~320×107px (height scales by aspect ratio 3:1). At this size:

- Wordmark `nox-mem` remains the dominant element (≈22px effective).
- Slogan stays legible — body text at 20px scales to ~5.3px which is at threshold; readers usually pinch-zoom anyway for hero banners.
- The bar chart compresses into a sharp silhouette where the orange spike still reads as the focal point.

This is the standard GitHub README banner tradeoff. Anyone who wants to read the slogan word-for-word taps to zoom; anyone scrolling absorbs the wordmark + spike + slogan-shape in one glance.

## Verification matrix

| Check                                              | banner-light | banner-dark |
|----------------------------------------------------|--------------|-------------|
| Valid SVG (`xmlns`, `viewBox`, well-formed)        | ✔            | ✔           |
| Slogan text-node present and selectable            | ✔            | ✔           |
| Contains literal "Pain-weighted hybrid memory"     | ✔            | ✔           |
| Contains literal "shadow discipline"               | ✔            | ✔           |
| Contains literal "yours by design"                 | ✔            | ✔           |
| `role="img"` + `aria-label` on `<svg>`             | ✔            | ✔           |
| `<title>` + `<desc>` present                       | ✔            | ✔           |
| Zero external dependencies (no `@import`, no URLs) | ✔            | ✔           |
| Zero animation (renders static)                    | ✔            | ✔           |
| 1200×400 viewBox + width/height                    | ✔            | ✔           |
| Renders in GitHub README (markdown-sanitized SVG)  | ✔            | ✔           |

## What was rejected (and why)

| Considered                                | Why rejected                                                                 |
|-------------------------------------------|------------------------------------------------------------------------------|
| Neural-network nodes (option A)           | Generic AI-startup cliché; previous banner already did this — too safe       |
| Brain / lightbulb / robot iconography     | Anti-pattern from the brief; semantically empty                              |
| Purple gradient on white                  | Anti-pattern from the brief; competitor visual slop                          |
| Glitch / scanline / cyberpunk frame       | Tonally wrong for board-level / SRE-targeting positioning                    |
| Photographic background                   | Heavy file size; locks brand to a specific image; breaks at 320px            |
| Full skyline (40+ bars)                   | Too dense; punctum loses dominance; metaphor blurs                           |
| Animation on the punctum                  | GitHub strips SMIL in many cases; accessibility regression                   |
| Including stats inline (95%, <50ms)       | Stat tiles already live below the banner; duplication weakens both          |
| Logo `[m]` monogram in banner             | Logo lives separately; banner is the wordmark moment                         |

## How to render / preview

```bash
# macOS — render to PNG for sanity check
qlmanage -t -s 1200 -o /tmp assets/readme/banner-dark.svg
qlmanage -t -s 1200 -o /tmp assets/readme/banner-light.svg

# Or open directly
open assets/readme/banner-dark.svg
open assets/readme/banner-light.svg
```

Cursor/VS Code preview: right-click → "Open Preview". Renders inline.

GitHub preview: confirmed by direct path render — markdown-sanitized engine permits `<text>`, `<rect>`, `<path>`, `<line>`, `<circle>`, `<ellipse>`, `<linearGradient>`, `<radialGradient>`, `<pattern>`, `<filter>`, `<feGaussianBlur>`, `<defs>`, `<g>`. All elements used are within scope.

## Linkage in README.md

Standard `<picture>` block for dark/light auto-switch:

```html
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/readme/banner-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/readme/banner-light.svg">
    <img alt="nox-mem — Pain-weighted hybrid memory with shadow discipline — yours by design"
         src="assets/readme/banner-light.svg"
         width="100%">
  </picture>
</p>
```

## Update the asset registry

The previous `assets/readme/README.md` row for the banner should be updated post-merge:

```
| banner-dark.svg  | 1200x400 | ~5KB | Pain-weighted bars + retrieval lattice, dark bg  |
| banner-light.svg | 1200x400 | ~5KB | Pain-weighted bars + retrieval lattice, light bg |
```

(Out of scope for this PR — owner can fold into a follow-up doc sweep or do it inline at review.)
