# Twitter Thread Images — Export Guide

4 SVG files ready for PNG export at 2× (2400×1350 px).

## Files

| File | Tweet | Concept |
|------|-------|---------|
| `img1-terminal-hook.svg` | 1 (hook) | Terminal incident log — April 25 22:03 |
| `img3-stats-card.svg` | 7 (stats) | 4 months × 6 agents × 64,180+ chunks |
| `img5-lesson-timeline.svg` | 10 (lesson) | APR 25 F02 → MAY 1 Rule 7 incident timeline |
| `img6-quote-card.svg` | 11 (close) | "The incidents are in the log..." |

---

## Export to PNG

### Option A: rsvg-convert (best quality, no dependencies)

```bash
brew install librsvg   # if not installed

cd /Users/lab/Claude/Projetos/memoria-nox/paper/publication/distribution/images

for f in img1-terminal-hook img3-stats-card img5-lesson-timeline img6-quote-card; do
  rsvg-convert -w 2400 -h 1350 "${f}.svg" -o "${f}.png"
done
```

### Option B: Inkscape CLI

```bash
brew install --cask inkscape   # if not installed

for f in img1-terminal-hook img3-stats-card img5-lesson-timeline img6-quote-card; do
  inkscape --export-type=png --export-width=2400 --export-height=1350 \
    --export-filename="${f}.png" "${f}.svg"
done
```

### Option C: Chrome/Safari screenshot (quickest, no install)

1. Open each SVG in browser (drag into Chrome)
2. DevTools > Device toolbar > set 1200×675
3. Cmd+Shift+P > "Capture screenshot" (full size)
4. Rename to match naming convention

### Option D: Python + cairosvg

```bash
pip install cairosvg

python3 -c "
import cairosvg, glob
for f in glob.glob('img*.svg'):
    cairosvg.svg2png(url=f, write_to=f.replace('.svg','.png'), output_width=2400, output_height=1350)
"
```

---

## Compress after export

Twitter performs best under 900 KB. After PNG export:

```bash
# Via TinyPNG CLI (requires API key)
npm install -g tinypng-cli
tinypng *.png

# Or open https://tinypng.com and drag all 4 files
```

---

## Alt text (copy-paste for Typefully)

**img1:** Terminal output showing nox-mem reindex completing at 22:03:17 with a green check mark. Below a divider, editorial text reads: "183 entities silently lost section, retention, and boost. No error. No alert. The database just... obeyed."

**img3:** Stats card on dark background: 4 months × 6 agents × 64,180+ chunks in first row. 12 schema versions, 99.97% vector coverage, less than 1 second p95 latency in second row. Tagline: "Solo. No funding. $20/mo VPS. Production corpus. Not synthetic."

**img5:** Horizontal incident timeline with two nodes. April 25: incident F02 — reindex wiped 183 entities; outcome is withOpAudit() snapshot before ops. May 1: Rule 7 — sed -i corrupted 1 GB SQLite, 8 backups; outcome is never sed binary files. A third dimmed node on the right suggests ongoing learning. Header reads: "Each scar became a rule."

**img6:** Dark quote card with three lines of white text centered: "The incidents are in the log. The log is in the schema. The schema is in the paper." The word "paper" is highlighted in amber. Below a short amber rule, attribution reads: "The Pain Diary and Shadow Discipline — github.com/totobusnello/memoria-nox."

---

*Assets for launch 2026-05-21 09:00 ET. Spec: `../twitter-images-spec.md`*
