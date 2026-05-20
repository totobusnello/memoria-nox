# Stat Cards — Design Notes

> Redesign 2026-05-18. From flat 180×38 strips → premium 220×80 cards with icon + big-number + label.

## Direction

**Tom**: technical-editorial. Reference: dashboards de observability (Grafana, Linear) + paper técnico. Blueprint feel — não tech-bro purple gradients.

**Differentiator memorável**: corner crosshair micro-mark (`+`) no canto superior direito de cada card + monoline schema-style icons. Vibe blueprint condizente com tagline "Hybrid memory with shadow discipline — yours by design."

## Dimensions

| Attr | Old | New |
|---|---|---|
| Width | 180 | 220 |
| Height | 38 | 80 |
| Padding (left) | 14 | 20 |
| Border radius | 6 | 8 |
| Accent bar | 3×38 | 3×80 |

Mais alto permite respiração + 3 níveis hierárquicos (big number / sub-label / micro-label uppercase).

## Layout (cada card)

```
┌─────────────────────────────────┐
│ ▌ ┌────┐  BIG NUMBER         + │ ← corner crosshair micro-mark
│ ▌ │icon│  sub-label              │
│ ▌ └────┘                         │
│ ▌ CATEGORY                       │ ← micro-label uppercase
└─────────────────────────────────┘
```

- **Accent bar** (3px) à esquerda — continuity com cards antigos
- **Icon** 24×24 monoline stroke 1.5px à esquerda (x=20, y=28)
- **Big number** 22px font-weight 700 mono (x=56, y=38)
- **Sub-label** 11px Inter regular (x=56, y=56)
- **Micro-label** 9px mono uppercase letter-spacing 1.4 (x=20, y=70) — categoria
- **Crosshair** 8px hairline canto superior direito (x≈209, y≈8)

## Palette

Mantém locked locked #00C896 primary + variants.

| Token | Dark | Light |
|---|---|---|
| Background gradient top | `#1A1F2E` | `#FFFFFF` |
| Background gradient bottom | `#0E0E10` | `#F5F5F7` |
| Border | `#2A2F3E` | `#D8D8DC` |
| Accent (bar + icon + number) | `#00C896` | `#007458` |
| Sub-label text | `#A0A4B0` | `#5A5F6E` |
| Micro-label text | `#5A5F6E` | `#9094A0` |
| Crosshair | `#3A3F4E` | `#C8CBD4` |

Light variant ganha `feGaussianBlur` drop-shadow leve (`stdDeviation=1.2`, opacity 8%) pra dar lift. Dark já tem depth via gradient.

## Typography

- **Big number**: `'JetBrains Mono', 'SFMono-Regular', ui-monospace, monospace` — 22px / 700 / letter-spacing -0.5
- **Sub-label**: `'Inter', ui-sans-serif, system-ui, sans-serif` — 11px / 500
- **Micro-label**: mono / 9px / 500 / letter-spacing 1.4

Zero remote font dep. Browser cai em system stack se JetBrains Mono e Inter não estiverem instalados — renderiza em system mono / system sans, ainda lê bem.

## Icons (custom paths, monoline)

| Card | Icon | Path semantics |
|---|---|---|
| `stat-scale` | database stack (3 discs) | ellipse + 2 cylinder sides |
| `stat-opex` | coin with $ | circle + S-curve $ glyph |
| `stat-tests` | shield with checkmark | shield outline + check stroke |
| `stat-latency` | stopwatch | circle + hour/min hand + top tab |
| `stat-locomo` | trending-up arrow | zigzag line + arrowhead |
| `stat-longmemeval` | bullseye target | 3 concentric circles + center dot |

Todos monoline stroke 1.5 round-cap/round-join. Escolhidos por **relação direta com a métrica** — não cliparts genéricos.

## Numbers (atualizados 2026-05-19 — G5 V3 A8 canonical)

| Card | Big | Sub-label | Category |
|---|---|---|---|
| `stat-scale` | `69k` | chunks · 21k relations | SCALE |
| `stat-opex` | `<$11/mo` | all-in OPEX | COST |
| `stat-tests` | `535+` | tests passing | QUALITY |
| `stat-latency` | `940ms` | p50 latency | SPEED |
| `stat-locomo` | `+78.8%` | nDCG@10 vs baseline | LOCOMO |
| `stat-longmemeval` | `1.0` | oracle validated | LONGMEMEVAL |

## Accessibility

- `role="img"` + `aria-label` preservado em cada arquivo (Unicode-safe text, decoded `<`/`>`)
- `<title>` element pra screen readers que ignoram aria-label
- Contrast checked: big number sobre background dark = 7.2:1 (AAA); light = 8.4:1 (AAA)
- Sem text-on-image — texto é SVG real, indexável e zoomable

## File listing

12 files total (6 cards × {dark,light}):

```
stat-scale-{dark,light}.svg
stat-opex-{dark,light}.svg
stat-tests-{dark,light}.svg
stat-latency-{dark,light}.svg
stat-locomo-{dark,light}.svg
stat-longmemeval-{dark,light}.svg
```

## Future ideas (not shipped)

- SVG `<animate>` count-up on load (current: static for GitHub README compat — GH strips `<script>` mas aceita `<animate>` declarativo)
- Hover variant com bar bloom (precisa CSS embedded, GitHub-hostile)
- Sparkline atrás do big number pra cards com series (latency p50/p95/p99 trend)
