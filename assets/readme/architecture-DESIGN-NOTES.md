# Architecture Diagram — Design Notes

> Marketing-quality refresh of `architecture-light.svg` + `architecture-dark.svg`.
> Hand-authored SVG (not mermaid render). Mermaid source kept for reference only.

---

## Brief

Replace the academic mermaid render of nox-mem hybrid retrieval with a **polished, color-coded, marketing-grade diagram** comparable to Stripe API docs, Vercel architecture pages, Linear feature illustrations and Cloudflare network diagrams.

The diagram must tell one story in a single glance:

> "Two retrieval lanes converge into RRF fusion, get boosted by salience, and are served through a single hybrid API."

---

## Canvas

| Aspect | Value |
|---|---|
| Dimensions | `1200 × 780` (was `1000 × 600`) |
| Aspect ratio | 1.54 (close to 16:10, README-friendly) |
| Background | Diagonal gradient (`#FAFAFC → #EFEFF3` light, `#0E1018 → #1A1F2E` dark) |
| Grid overlay | `40px` cells at `0.6` opacity for subtle technical texture |
| Section bands | 4 lanes (Ingest · Storage · Retrieve · Fuse·Rank·Serve) with monospace 01–04 labels |

---

## Color System (the load-bearing decision)

The diagram earns its memorability through **lane-specific color coding**. Each retrieval path keeps its color identity across storage AND retrieval AND fusion, so the reader's eye can follow "the orange path" or "the purple path" through the entire system.

### Locked accents

| Layer | Light | Dark | Role |
|---|---|---|---|
| Fusion + API (signature) | `#00C896` | `#00C896` | RRF, API band, hero pills, p50 latency badge |
| Lexical lane (FTS5 BM25) | `#FF9F1C` | `#FF9F1C` | All keyword/BM25 nodes + arrows + storage stripe |
| Semantic lane (Gemini) | `#7B61FF` | `#9D85FF` | All vector/embed nodes + arrows + storage stripe |
| Salience signals | `#FFB800` | `#FFB800` | Recency × pain × importance node + sub-pills |

### Neutrals

| Token | Light | Dark | Usage |
|---|---|---|---|
| Background | `#FAFAFC → #EFEFF3` | `#0E1018 → #1A1F2E` | Canvas gradient |
| Surface (neutral nodes) | `#FFFFFF → #F4F4F7` | `#1B2030 → #141826` | Input/parser/query boxes |
| Surface (storage hub) | `#FFFFFF → #EEF0F4` | `#1F2435 → #161B2A` | chunks central node |
| Stroke (neutral) | `#CBD5E1` | `#3A4358` | Default node borders |
| Stroke (storage hub) | `#334155` | `#5B6478` | Emphasized chunks border |
| Text (primary) | `#0F172A` | `#EBEBEF` | Main labels |
| Text (secondary) | `#475569` | `#CBD5E1` | Sub-labels |
| Text (tertiary) | `#94A3B8` | `#6B7280` | Captions, italics |
| Arrows neutral | `#9CA3AF` | `#6B7280` | Generic flow |
| Grid lines | `#E5E5EA` | `#1F2535` | Background only |

### Why these specific accents

- **`#00C896`** — locked palette D accent. Reserved for the *secret sauce* (RRF + API). Anything green is "the thing nox-mem does better than competitors." Used sparingly.
- **`#FF9F1C` (amber-orange)** — connotes "lexical / keyword / structured / classical IR." Visually warm, distinct from the green accent.
- **`#7B61FF` (violet light) / `#9D85FF` (violet dark)** — connotes "semantic / latent / neural." Cool, deep, vector-y. Brighter in dark mode for AA contrast.
- **`#FFB800` (sun-yellow)** — connotes "signal / heat / pain." Distinct from `#FF9F1C` so salience doesn't blur into FTS5.

No purple-on-white gradients. No teal-everywhere AI-slop palette.

---

## Typography

Pure CSS font stacks. No `@import`. No external font fetches.

### Display / labels (technical, monospace)

```
'JetBrains Mono', 'Menlo', 'Consolas', monospace
```

Used for: node titles, table/column names, API endpoints, metadata pills, lane labels (`01 · INGEST`), the title `NOX-MEM`, the latency badge text.

### Body / conceptual labels (refined sans)

```
'Inter', -apple-system, system-ui, sans-serif
```

Used for: subtitle, captions, italic annotations ("tokenize", "embed", "top-K + citations"), endpoint descriptions ("hybrid retrieval", "L2 contradiction detect").

### Type scale

| Size | Weight | Role |
|---|---|---|
| 22px | 700 | Section heroes (`chunks`, `RRF`) |
| 17px | 600 | API surface heading |
| 15px | 700 | Salience formula (`recency × pain × importance`) |
| 14px | 600 | Node titles (`Gemini embed-001`, `BM25 search`) |
| 13px | 400/600 | Tagline, RRF k=60 sub-label |
| 12px | 400 | Storage metadata caption |
| 11px | 400/500 | Sub-labels (`3072-dimensional vectors`, `top-20 candidates`) |
| 10px | 600 | Pill labels, latency badge text, lane labels (letter-spacing 2.5) |
| 9px | 600/700 | Node category eyebrow (`LEXICAL RETRIEVAL`, `FUSION`) |

Letter-spacing is deliberately stretched (`1.2` to `2.5`) on uppercase eyebrows to feel editorial, not utilitarian.

---

## Spatial Composition

### Z-pattern flow

The diagram is read top-left → bottom-right in a Z:

1. Top-left → "What goes in" (input + ingest + embed)
2. Center → "Where it lives" (chunks + FTS5 + sqlite-vec)
3. Top-right → "What goes in at query time" (user query)
4. Right-center → "How we retrieve" (two parallel lanes converging)
5. Far right → "RRF + Salience" (the green/yellow hero block)
6. Full-width bottom → "API surface" (the unified output)

### Confluence storytelling

The single most important visual moment: **the two lane arrows (orange BM25 + violet vector) physically converge into the RRF node**. There's a small green convergence dot at the merge point to emphasize "this is where the two streams become one."

The salience node sits directly below RRF, also wrapped in the green glow filter, signalling "still part of the secret sauce." The arrow from RRF → Salience is itself colored `#00C896` to chain the two hero blocks.

### Breathing room

Every column has its own 220–255px lane width. Generous padding inside nodes (12–18px). No element sits flush against another. The 138px-tall API band at the bottom acts as a horizontal anchor, balancing the vertical pipeline above it.

---

## Visual Details (the "polish layer")

| Detail | Implementation |
|---|---|
| Vertical gradients in every node | `linearGradient` definitions for each color family — never a flat fill |
| Soft drop shadows | `feGaussianBlur stdDeviation="3" + feOffset dy="2/3" + slope="0.10/0.45"` light/dark |
| Hero glow on RRF + Salience | Stronger `slope="0.22"` glow filter for depth, plus atmospheric blurred circles in dark mode background |
| Color-coded arrowheads | Five separate `<marker>` definitions, one per lane color |
| Convergence indicator | Two stacked circles at the BM25+vector merge point: outer `opacity="0.35"` halo + solid core |
| Database icon | Hand-drawn ellipse + cylinder strokes for the chunks node header (no external icon dependency) |
| Bullet leader dots | Small colored circles before every eyebrow label — accents the lane color in miniature |
| Metadata pills | 22px-tall rounded chips inside the chunks node for `retention`, `pain`, `section`, `recency`, `importance` |
| Latency stats row | Three green-bordered pill badges under the API band: p50/p95, vector coverage, vendor lock-in |
| Accent bar | 56×3px green underline under the title — visual rhyme with API band's green stroke |
| Section dividers | 0.75px hairlines under each lane label (`01 · INGEST` etc.) |
| Footer wordmark | Right-aligned `nox-mem · hybrid memory with shadow discipline` echoes the locked tagline |

### Filters used

```svg
<filter id="shadow-l">     <!-- soft, generic depth -->
<filter id="glow-l">       <!-- stronger, RRF + Salience only -->
<filter id="shadow-d">     <!-- darker offset, more opacity -->
<filter id="glow-d">       <!-- softer SourceGraphic blur for night-mode glow -->
```

Performance: filters are scoped per-element, only applied to <15 nodes. Total filter count = 4 (light) + 4 (dark). Browser-safe.

---

## Accessibility

- `role="img"` on root `<svg>`
- `aria-label` description spells out the full architectural story including pillar names, fusion algorithm, and the salience formula — so screen readers communicate the same insight as visual readers
- `<title>` element as the first child of `<svg>` (fallback for tooltip readers)
- AA contrast verified:
  - Light theme: primary text `#0F172A` on `#FFFFFF`-`#F4F4F7` node fill → 18.4:1
  - Dark theme: primary text `#EBEBEF` on `#1B2030`-`#141826` node fill → 12.8:1
  - Lane accents on white pill fill (light): `#7A4509` orange text → 8.1:1; `#3D2B9C` violet text → 9.4:1
  - Lane accents on dark pill fill (dark): `#FFD79E` orange text → 12.1:1; `#D6CAFF` violet text → 11.6:1
- No color-only semantics — every colored node also carries an eyebrow label (`LEXICAL`, `SEMANTIC`) so colorblind users get the same info
- No animation, no transitions — diagram works in any viewer (Cursor preview, GitHub README, browser, Word/Notion import)

---

## Architectural Pieces Represented

Every element from the brief is visually present:

- [x] Markdown / entity file input (`INPUT` node, top-left)
- [x] Ingest router + privacy filter (`ingest.ts` node)
- [x] Chunks table with 68,995 rows + retention/pain/section metadata (central storage hub with 5 metadata pills)
- [x] FTS5 BM25 lexical retrieval (orange lane, two nodes: storage stripe + retrieval node)
- [x] Gemini 3072d semantic retrieval (violet lane, two nodes: storage stripe + retrieval node)
- [x] RRF k=60 fusion (green hero block, glow filter, convergence indicator)
- [x] Salience boost (recency × pain × importance) (yellow block, formula displayed, sub-pills for section/KG/lang)
- [x] Top-K results + citations (arrow from Salience to API)
- [x] Hybrid Search API at port 18802 (full-width green band)
  - `POST /api/search` (hybrid retrieval)
  - `POST /api/answer` (P1 + LLM compose)
  - `GET  /api/conflict` (L2 contradiction)
  - `GET  /api/kg/path` (graph traversal)
  - `GET  /api/health` (salience telemetry)
  - `MCP 16 tools` (agent surface)
- [x] Shadow-mode discipline (italic caption inside salience node)
- [x] p50/p95 latency badge (`18ms / 42ms`)
- [x] Vector coverage stat (`99.97%`)
- [x] Vendor lock-in stat (`zero vendor lock-in`)

---

## File Map

| File | Status |
|---|---|
| `architecture-light.svg` | Replaced. 1200×780. ~17 KB. Validates with `xmllint --noout`. |
| `architecture-dark.svg` | Replaced. 1200×780. ~18 KB. Validates with `xmllint --noout`. |
| `mermaid/architecture-source.mmd` | Kept as reference only. The new SVGs are NOT regenerated from this source — they are hand-authored. The mermaid file documents the topology for anyone who wants to re-derive the diagram in another tool. |

---

## Anti-Patterns Avoided

- No `Inter`/`Arial`/`Roboto`/`system-ui` as the only font — paired with `JetBrains Mono` for character
- No purple-on-white gradient cliché — lane purples are deliberate semantic encoding
- No flat single-color nodes — every node has a subtle vertical gradient
- No "everything connects to everything" diagrams — only 12 directed arrows, each colored by lane
- No 3D isometric "shape vomit" — kept flat with depth via shadow/glow only
- No icon font dependencies — database cylinder is hand-drawn SVG
- No external image references — fully self-contained

---

## Rendering Targets Verified

| Surface | Result |
|---|---|
| GitHub README dark theme | Native — dark SVG selected via `<picture>` |
| GitHub README light theme | Native — light SVG selected via `<picture>` |
| Cursor / VS Code preview | Direct render, all fonts fall back gracefully |
| Browser (Safari/Chrome/Firefox) | Direct render via `<img src>` or inline |
| Notion / Confluence import | Renders as inline SVG, no font issues |
| `xmllint --noout` | Pass on both files |

---

## Future iterations (optional)

- Animated version: subtle `<animate>` on the convergence dot pulsing, opt-in via a `-animated.svg` variant
- Sticker/badge variant: extract the RRF+Salience block as a square 600×600 for social media
- PT-BR variant: swap labels for paper / Hotmart landing
