# Twitter Thread — Visual Assets Spec
## 6 Images for Launch Thread (2026-05-21 09:00 ET)

> Thread: "The Pain Diary and Shadow Discipline" — 11 tweets
> Canonical palette: indigo `#4F46E5` / slate `#0F172A` / amber `#D97706` / emerald `#059669` / rose `#E11D48`
> Typography system: Syne (display/numbers) + DM Mono (code/terminal)
> All exports: PNG 2× (2400×1350 px), compressed < 900 KB via TinyPNG
> WCAG AA minimum (4.5:1 text on bg) required on every image

---

## Status overview

| # | Tweet | Status | ETA |
|---|-------|--------|-----|
| 1 | Hook — Terminal incident log | NEED CREATE | ~15 min |
| 2 | Chart hero — FTS/BM25/Hybrid bars | ✅ AVAILABLE (render_twitter_chart.py) | 0 min |
| 3 | Stats card — scale/context | NEED CREATE | ~15 min |
| 4 | System architecture — Figure 1 | ✅ AVAILABLE (needs reframe) | ~10 min |
| 5 | Incident timeline — scars as features | NEED CREATE | ~20 min |
| 6 | Quote card — closing tagline | NEED CREATE | ~15 min |

**Already available:** 2 images (chart hero runnable via Python, figure1.png rendered)
**Need to create:** 4 images (~75 min total in Figma)
**ETA total:** ~85 min production-ready (chart Python run + 4 Figma + figure1 reframe)

**Priority creation order:** 6 → 3 → 1 → 5 → (4 reframe) → (2 already done)
Rationale: Quote card (6) and stats card (3) are fastest wins with highest scroll-stop ROI. Terminal image (1) is the thread opener — most critical. Timeline (5) is most complex, build last.

---

## Image 1 — Terminal Incident Log
**Tweet:** 1 (hook)
**Concept:** Faux terminal screenshot showing the exact moment of the April 25 incident — timestamp, command, silent data loss. No error. No alert. Just obedience.

### Dimensions
1200 × 675 px (16:9 Twitter card)

### Composition
```
┌──────────────────────────────────────────────────────────────────────┐
│  ● ● ●  nox-mem — zsh — 80×24                [#1E293B window chrome]│
├──────────────────────────────────────────────────────────────────────┤
│                                                          [#0F172A bg]│
│  [22:03:14] cron: running scheduled task nox-mem-eod            [1] │
│  [22:03:15] $ nox-mem reindex --all                             [2] │
│  [22:03:15]   → scanning 62,836 chunks...                       [3] │
│  [22:03:16]   → reindexing FTS5...                              [4] │
│  [22:03:17]   → done. 62,836 processed.                         [5] │
│                                                                      │
│  [22:03:17] ✓  reindex complete.                                [6] │
│                                                                      │
│  _                                     ← blinking cursor            │
│                                                                      │
│                                                                      │
│  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ │
│  183 entities silently lost section, retention, and boost.          │
│  No error. No alert. The database just... obeyed.                   │
└──────────────────────────────────────────────────────────────────────┘
```

### Color roles
| Element | Hex | Rationale |
|---------|-----|-----------|
| Window chrome | `#1E293B` | Slate-800, realistic dark terminal |
| Background | `#0F172A` | Near-black, depth |
| Traffic lights (●●●) | `#E11D48` / `#D97706` / `#059669` | Rose/amber/emerald — macOS dots signal real incident |
| Timestamp `[22:03:14]` | `#475569` | Slate, recessive |
| Command `nox-mem reindex` | `#F8FAFC` | White, dominant |
| `→ scanning` progress | `#94A3B8` | Slate-400, process noise |
| `✓  reindex complete.` | `#059669` | Emerald — false success is the horror |
| Divider `┄` | `#1E293B` | Separation from editorial footer |
| Editorial footer text | `#CBD5E1` | Slate-300, italic, human voice |
| Footer amber accent | `#D97706` | Single word "silently" in amber to land the horror |

### Typography
| Element | Font | Weight | Size |
|---------|------|--------|------|
| Terminal text (all lines) | DM Mono | Regular 400 | 13px |
| `nox-mem reindex` (command) | DM Mono | Bold 700 | 13px |
| Editorial footer | Syne | Regular 400 | 15px italic |
| "silently" | Syne | Bold 700 | 15px, amber |
| Window title bar | DM Mono | Regular 400 | 11px |

### Details
- Window chrome has 6px border-radius (realistic macOS Terminal)
- Cursor `_` blinks — in PNG, render as solid amber `#D97706` block cursor (no animation, creates tension)
- Terminal font size renders at minimum 11px CSS-equivalent on mobile 375px width (export 2×)
- The `✓ reindex complete.` in emerald is intentionally dissonant against the editorial footer — the system reported success

### Tool
**Figma** — create frame 1200×675, place dark rectangle for window, use auto-layout for terminal lines, install DM Mono + Syne from Google Fonts plugin, export PNG 2× → compress TinyPNG

**ETA:** 15 min

### Alt text
`Terminal output showing nox-mem reindex completing at 22:03:17 with a green check mark. Below a divider, editorial text reads: "183 entities silently lost section, retention, and boost. No error. No alert. The database just... obeyed."`

---

## Image 2 — Chart Hero (FTS5 / BM25 / Hybrid)
**Tweet:** 6 (chart)
**Status:** ✅ AVAILABLE — `render_twitter_chart.py` in this directory

### Run command
```bash
cd /Users/lab/Claude/Projetos/memoria-nox/paper/publication/distribution
python3 render_twitter_chart.py
# Output: twitter-chart-hero.png (1200×675 px, ~150 KB)
```

### Existing spec
Full visual spec documented in `twitter-chart-hero-spec.md`.
Renders 3-bar comparison: FTS5 ghost (0.0123) / BM25 slate (0.1475) / nox-mem hybrid indigo (0.5213).
White background variant chosen for light-mode legibility at launch time.

### Alt text
`Bar chart comparing nDCG@10 scores: FTS5 vanilla 0.0123 (ghost bar, near-zero), BM25 Pyserini 0.1475 (slate bar), nox-mem hybrid 0.5213 (indigo bar, checkmark). Title: "FTS5 vs BM25 vs nox-mem hybrid (n=60 queries), nDCG@10, 3-run mean." Footer: "FTS5 alone contributes ~0% to hybrid score on full-sentence NL queries — structural constraint, not tunable."`

---

## Image 3 — Stats Card
**Tweet:** 7 (scale and context)
**Concept:** Dense, precise data card. Six metrics in two columns, each with a large number and a label. The aesthetic is deliberately editorial — a newspaper pullquote card, not a dashboard.

### Dimensions
1200 × 675 px (16:9)

### Composition
```
┌──────────────────────────────────────────────────────────────────────┐
│                                               [#0F172A dark bg]      │
│                                                                      │
│   ┌────────────────────────────────────────────────────────────┐    │
│   │                                                            │    │
│   │   4          ×    6           ×    61,257                 │    │
│   │   months         agents           chunks                   │    │
│   │                                                            │    │
│   │   ─────────────────────────────────────────────────        │    │
│   │                                                            │    │
│   │   12              99.97%           < 1s                    │    │
│   │   schema           vector           p95                    │    │
│   │   versions         coverage         latency                │    │
│   │                                                            │    │
│   │   ─────────────────────────────────────────────────        │    │
│   │                                                            │    │
│   │   Solo. No funding. $20/mo VPS.                            │    │
│   │   Production corpus. Not synthetic.                        │    │
│   │                                                            │    │
│   └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│   The Pain Diary and Shadow Discipline   github.com/totobusnello/…  │
└──────────────────────────────────────────────────────────────────────┘
```

### Color roles
| Element | Hex | Note |
|---------|-----|------|
| Background | `#0F172A` | Full bleed |
| Card surface | `#0F172A` | No inner card — borderless, metrics float |
| Large numbers (row 1) | `#F8FAFC` | White, maximum contrast |
| `4` months — highlight | `#D97706` | Amber, time = earned |
| `6` agents | `#4F46E5` | Indigo, the agents |
| `61,257` | `#34D399` | Emerald-400, the corpus |
| `12` schema versions | `#94A3B8` | Slate — complexity, not pride |
| `99.97%` | `#34D399` | Emerald — coverage achievement |
| `< 1s` | `#F8FAFC` | White — speed as fact |
| `×` multiplier operators | `#475569` | Slate-600, recessive |
| Labels below numbers | `#475569` | Slate, uppercase 11px tracked |
| Horizontal rules | `#1E293B` | Slate-800, delicate separator |
| Footer tagline | `#94A3B8` | Slate-400 |
| Footer URL | `#818CF8` | Indigo-400 |

### Typography
| Element | Font | Weight | Size | Tracking |
|---------|------|--------|------|----------|
| Large metrics (4, 6, 61,257) | Syne | Black 900 | 72px | -0.03em |
| Row 2 metrics (12, 99.97%, < 1s) | Syne | Bold 700 | 56px | -0.02em |
| Metric labels | Syne | Regular 400 | 12px uppercase | +0.1em |
| `×` operators | Syne | Regular 400 | 36px | 0 |
| Tagline "Solo. No funding…" | DM Mono | Regular 400 | 14px | 0 |
| Footer attribution | Syne | Regular 400 | 11px | +0.05em |

### Spatial notes
- Three-column equal-width grid for row 1 metrics with `×` between columns
- Row 2 metrics share the same three-column grid but use tighter number sizes to avoid crowding `99.97%`
- Mobile crop zone (safe area ≈ central 80% width): all six metrics within zone
- Negative space on left/right edges (≥ 60px each) gives breathing room

### Tool
**Figma** — Auto-layout columns + rows, Syne Black (install via Google Fonts plugin), export 2×

**ETA:** 15 min

### Alt text
`Stats card on dark background: 3 months, 6 agents, 61,257 chunks in first row. 12 schema versions, 99.97% vector coverage, less than 1 second p95 latency in second row. Tagline: "Solo. No funding. $20/mo VPS. Production corpus. Not synthetic."`

---

## Image 4 — System Architecture (Figure 1)
**Tweet:** 8 (where to find it)
**Status:** ✅ AVAILABLE with reframe needed

### Source file
`/Users/lab/Claude/Projetos/memoria-nox/paper/publication/diagrams/rendered/figure1.png`
Current dimensions: **475 × 2214 px** (tall portrait Mermaid render)

### Problem
Twitter card is 1200×675 landscape. figure1.png is portrait and would be auto-cropped to show only the top portion — missing the Storage and Cross-cutting subgraphs.

### Reframe spec (10 min task)
Create a 1200×675 Figma frame with `#0F172A` background. Import figure1.png scaled to fit height: 675px → width proportional ≈ 145px. Place diagram centered-left at x=80. Add right-side annotation panel:

```
LEFT (x: 80, w: 180px)    |    RIGHT (x: 320, w: 740px)
─────────────────────────────────────────────────────────
[Figure 1 PNG, scaled]         HEADER: "System Architecture"
                                [Syne Bold 28px, white]

                                Four labeled callout rows:
                                  ■ AGENTS (indigo)   6 shared-canonical agents
                                  ■ SEARCH (slate)    3-layer fusion (FTS5+Gemini+RRF)
                                  ■ STORE  (rose)     Single SQLite, 61K chunks
                                  ■ CROSS  (emerald)  Shadow-mode + op-audit discipline

                                FOOTER: paper title + github URL
```

Alternatively: Re-render figure1.mmd with `mmdc -w 900 -H 600` to get a landscape-native render that fits directly. Mermaid CLI command:
```bash
mmdc -i /Users/lab/Claude/Projetos/memoria-nox/paper/publication/diagrams/figure1.mmd \
     -o /Users/lab/Claude/Projetos/memoria-nox/paper/publication/diagrams/rendered/figure1-landscape.png \
     -w 900 -H 550 --backgroundColor "#0F172A" --theme dark
```
Then place on 1200×675 canvas with header/footer zones. Preferred approach — single source, no manual redraw.

### Color roles (header/footer overlay)
| Element | Hex |
|---------|-----|
| Canvas background | `#0F172A` |
| Section header | `#F8FAFC` |
| Callout: AGENTS | `#818CF8` (indigo-400) |
| Callout: SEARCH | `#94A3B8` (slate-400) |
| Callout: STORE | `#FB7185` (rose-400) |
| Callout: CROSS | `#34D399` (emerald-400) |
| Footer URL | `#818CF8` |

### Typography
| Element | Font | Size |
|---------|------|------|
| "System Architecture" | Syne Bold | 28px |
| Callout labels | Syne Regular | 13px uppercase |
| Callout descriptions | DM Mono Regular | 12px |
| Footer | Syne Regular | 11px |

**ETA:** 10 min (Mermaid re-render preferred path) or 15 min (Figma reframe)

### Alt text
`System architecture diagram showing 5 subgraphs: 6 agents at top sharing canonical corpus, interface layer with CLI/MCP/HTTP API, hybrid search engine with FTS5, Gemini semantic, and RRF fusion layers, canonical SQLite storage with 61K chunks and KG, and cross-cutting discipline with shadow-mode pipeline and op-audit snapshots.`

---

## Image 5 — Incident Timeline
**Tweet:** 10 (lesson / eval methodology context)
**Concept:** Horizontal timeline of scars. Each incident becomes a named rule in the schema. Visual language: scar tissue turned into structural calluses — amber dates, rose incident labels, emerald rule outcomes.

> Note: Tweet 10 is about eval reproducibility ("I can't tell if they're right"), but the image serves as visual proof of operational depth — the scars that the paper emerges from. Reinforces the thread's core argument without requiring text comprehension of the image alone.

### Dimensions
1200 × 675 px (16:9)

### Composition
```
┌──────────────────────────────────────────────────────────────────────┐
│  HEADER [#0F172A]                                                    │
│  "Each scar became a rule."           [Syne Bold 32px, white]       │
│  "The incidents are in the log. The log is in the schema."          │
│  [DM Mono Regular 14px, slate]                                      │
│                                                                      │
│  ─────────────────────────────────────────────────────────────      │
│  TIMELINE RAIL (horizontal, centered vertically)                    │
│                                                                      │
│    APR 25        MAY 1         [future node — dimmed]               │
│      ●             ●                  ○                             │
│      │             │                  │                             │
│   ╔══╧══╗       ╔══╧══╗         ┌────┴────┐                        │
│   ║ F02 ║       ║  R7 ║         │  …     │                         │
│   ╚══╤══╝       ╚══╤══╝         └────┬────┘                        │
│      │             │                  │                             │
│   reindex       sed -i .db        [next one                        │
│   wiped 183     corrupted 1GB     is forming]                      │
│   entities      8 backups                                           │
│                                                                     │
│   → F02 op-audit  → Rule 7:                                        │
│     withOpAudit()   never sed                                       │
│     snapshot        binary files                                    │
│     before ops                                                      │
│  ─────────────────────────────────────────────────────────────     │
│  FOOTER: "The Pain Diary and Shadow Discipline"  github…           │
└──────────────────────────────────────────────────────────────────────┘
```

### Color roles
| Element | Hex | Meaning |
|---------|-----|---------|
| Background | `#0F172A` | Dark, weight of incidents |
| Timeline rail (horizontal line) | `#1E293B` | Slate-800, recessive |
| Node APR 25 (●) | `#E11D48` | Rose — incident |
| Node MAY 1 (●) | `#E11D48` | Rose — incident |
| Future node (○) | `#1E293B` | Dimmed, open circle, next one |
| Incident label "F02" | `#FB7185` | Rose-400 |
| Incident label "R7" | `#FB7185` | Rose-400 |
| Date labels "APR 25", "MAY 1" | `#D97706` | Amber — timestamps earned |
| Rule outcome text | `#34D399` | Emerald — healing into structure |
| Incident description text | `#94A3B8` | Slate-400 |
| Card border (incident cards) | `#E11D48` 1px | Rose outline |
| Header text main | `#F8FAFC` | White |
| Header subtext | `#94A3B8` | Slate-400, DM Mono |
| Footer | `#475569` / `#818CF8` | Slate / Indigo URL |

### Typography
| Element | Font | Weight | Size |
|---------|------|--------|------|
| "Each scar became a rule." | Syne | Bold 700 | 32px |
| Header subtext | DM Mono | Regular 400 | 13px |
| Date labels (APR 25, MAY 1) | Syne | Bold 700 | 14px uppercase |
| Feature code (F02, R7) | DM Mono | Bold 700 | 18px |
| Incident description | DM Mono | Regular 400 | 11px |
| Rule outcome | Syne | Regular 400 | 12px |
| Footer | Syne | Regular 400 | 11px |

### Spatial notes
- Timeline rail centered vertically at y≈380px (slightly below center for optical balance with header)
- Two incident nodes visible, third node dimmed/open circle at far right — signals ongoing process
- Cards hang below the rail on alternating sides would crowd at 1200px; keep all cards below for clean readability at mobile crop
- Node dots: 14px diameter circles with 3px rose border + rose fill; future node: 12px empty circle with slate border

### Tool
**Figma** — Frame 1200×675, draw horizontal line (rail), place circles with auto-layout cards below, DM Mono for code elements, Syne for editorial text

**ETA:** 20 min (most complex of the 4 need-creates)

### Alt text
`Horizontal incident timeline with two nodes. April 25: incident F02 — reindex wiped 183 entities; outcome is withOpAudit() snapshot before ops. May 1: Rule 7 — sed -i corrupted 1 GB SQLite, 8 backups; outcome is never sed binary files. A third dimmed node on the right suggests ongoing learning. Header reads: "Each scar became a rule."`

---

## Image 6 — Quote Card (Closing Tagline)
**Tweet:** 11 (CTA / close)
**Concept:** Pure typography. The closing triplet from the thread — three lines of escalating specificity — centered on a dark field with a single amber accent line. Nothing competes with the words.

### Dimensions
1200 × 675 px (16:9) — note: also works as 1080×1080 square for Instagram Stories repurpose

### Composition
```
┌──────────────────────────────────────────────────────────────────────┐
│                                               [#0F172A full bleed]   │
│                                                                      │
│                                                                      │
│                                                                      │
│         The incidents are in the log.                               │
│         The log is in the schema.                                   │
│         The schema is in the paper.                                 │
│                                                                      │
│         ────────                                                     │
│                                                                      │
│         The Pain Diary and Shadow Discipline                        │
│         github.com/totobusnello/memoria-nox                         │
│                                                                      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Color roles
| Element | Hex | Rationale |
|---------|-----|-----------|
| Background | `#0F172A` | Near-black, maximal contrast, focus on text |
| "The incidents are in the log." | `#F8FAFC` | White |
| "The log is in the schema." | `#CBD5E1` | Slate-300, slightly recessive — builds toward the peak |
| "The schema is in the paper." | `#F8FAFC` | White again — the payoff returns to full brightness |
| Single word "paper" | `#D97706` | Amber — the one destination, the release |
| Amber accent rule `────────` | `#D97706` | 2px height, 80px width, centered |
| Attribution: paper title | `#475569` | Slate-600 |
| Attribution: github URL | `#818CF8` | Indigo-400 |

### Typography
| Element | Font | Weight | Size | Line height |
|---------|------|--------|------|-------------|
| Three quote lines | Syne | Bold 700 | 34px | 1.5 |
| Word "paper" (amber) | Syne | Bold 700 | 34px | 1.5 |
| Attribution — paper title | Syne | Regular 400 | 13px uppercase | — |
| Attribution — github URL | Syne | Regular 400 | 13px | — |
| Amber rule | Rectangle | — | 2px × 80px | — |

### Spatial notes
- Three quote lines centered horizontally and vertically (optical center: y ≈ 45% of canvas)
- Inter-line tracking: 1.5em line height creates breathing room between the three statements
- Attribution block sits 48px below amber rule, centered
- No logo, no icon, no decorative elements — restraint IS the design
- Amber accent `────────` is a 2×80px rectangle, not an em-dash — crisp rule, not a character

### Constraint
The word "paper" in amber must not bleed into surrounding words — it is inline within the third line. Figma implementation: three text frames stacked, with the third line split into "The schema is in the " + "paper" (amber) as separate text layers, positioned to align optically.

### Tool
**Figma** — Frame 1200×675, background fill `#0F172A`, three text blocks center-aligned, rectangle for amber rule, Syne Bold from Google Fonts plugin

**ETA:** 15 min (simplest of the four — pure typography, no illustration)

### Alt text
`Dark quote card with three lines of white text centered: "The incidents are in the log. The log is in the schema. The schema is in the paper." The word "paper" is highlighted in amber. Below a short amber rule, attribution reads: "The Pain Diary and Shadow Discipline — github.com/totobusnello/memoria-nox."`

---

## Production checklist (all 6 images)

- [ ] Export all as PNG 2× (2400×1350 px) from Figma
- [ ] Compress each < 900 KB via TinyPNG (Twitter hard limit 5 MB, performs best < 1 MB)
- [ ] Verify dark mode on Twitter mobile app before scheduling (images 1, 3, 5, 6 are dark-bg; Image 2 is light-bg — confirm visibility in both modes)
- [ ] Add alt text to every tweet when scheduling in Typefully
- [ ] Test safe crop zone: Twitter crops 16:9 to ~16:7 in feed — all critical content must sit within central 80% height (≈ y: 67px to 608px)
- [ ] Image 4 only: verify Mermaid re-render includes all 5 subgraphs before placing on canvas

## Figma setup (shared across all images)

1. New file: 6 frames, each 1200×675, named by image number
2. Color styles: create shared palette from canonical hex values above
3. Text styles: Syne Bold/Regular, DM Mono Regular/Bold — install both via Google Fonts plugin
4. Component: footer strip (paper title + github URL) — reuse across images 1, 3, 5, 6 for consistency
5. Export setting: PNG, 2× scale, remove prefix

---

*Spec created: 2026-05-03. Assets for launch 2026-05-21.*
