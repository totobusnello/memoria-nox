# Figures — Generation Guide

Four figures are required for `main.tex`. The Mermaid source for all four lives in
`../diagrams/system-architecture.md`. This guide covers two conversion paths and lists
the expected output filenames.

---

## Expected files (must exist before `make` succeeds)

| File | Figure in paper | Caption summary |
|---|---|---|
| `figures/figure1-system-overview.pdf` | Fig. 1 (§3.1) | Six-agent system overview — interface / search / storage / discipline layers |
| `figures/figure2-salience-pipeline.pdf` | Fig. 2 (Appendix B) | Salience pipeline — ingest → annotate → shadow → activate gate |
| `figures/figure3-shadow-state-machine.pdf` | Fig. 3 (§3.6) | Shadow discipline state machine — Implement → Shadow → ActivateEligible → Activate |
| `figures/figure4-kg-edge-typing.pdf` | Fig. 4 (§4.4) | KG edge typing flow — LLM extraction → 3-path defensive normalization → enum-7 |

All `\includegraphics` calls in `main.tex` reference these exact paths relative to the
`latex/` directory. PDF is preferred over PNG for vector quality in arXiv submission.

---

## Option 1 — mermaid-cli (recommended, scriptable)

### Install

```bash
npm install -g @mermaid-js/mermaid-cli
# verify
mmdc --version
```

### Extract source blocks and render

Copy each Mermaid block from `../diagrams/system-architecture.md` into a standalone
`.mmd` file, then run `mmdc`:

```bash
# Figure 1 — flowchart TB (system overview)
mmdc -i figure1-system-overview.mmd -o figures/figure1-system-overview.pdf -b transparent

# Figure 2 — flowchart LR (salience pipeline)
mmdc -i figure2-salience-pipeline.mmd -o figures/figure2-salience-pipeline.pdf -b transparent

# Figure 3 — stateDiagram-v2 (shadow state machine)
mmdc -i figure3-shadow-state-machine.mmd -o figures/figure3-shadow-state-machine.pdf -b transparent

# Figure 4 — flowchart TB (KG edge typing)
mmdc -i figure4-kg-edge-typing.mmd -o figures/figure4-kg-edge-typing.pdf -b transparent
```

For PNG output (lower quality, acceptable for draft review):

```bash
mmdc -i figure1-system-overview.mmd -o figures/figure1-system-overview.png -w 1600 -H 900
```

If `mmdc` produces a white-on-white artefact, add `-b white` or override the Mermaid
theme with `-t neutral`.

---

## Option 2 — mermaid.live (no install required)

1. Open [https://mermaid.live](https://mermaid.live).
2. Paste the Mermaid block from `../diagrams/system-architecture.md` (one figure at a time).
3. Click **Export** → **SVG** or **PNG**.
4. Convert SVG to PDF with Inkscape or `rsvg-convert`:

```bash
# using Inkscape (CLI)
inkscape --export-type=pdf --export-filename=figures/figure1-system-overview.pdf figure1.svg

# using rsvg-convert (lighter)
rsvg-convert -f pdf -o figures/figure1-system-overview.pdf figure1.svg
```

---

## Option 3 — Puppeteer / playwright (CI-friendly)

`mmdc` internally uses Puppeteer. For headless CI environments without a display server,
pass the `--puppeteerConfigFile` option:

```bash
# puppeteer-config.json
{ "args": ["--no-sandbox", "--disable-setuid-sandbox"] }

mmdc -i figure1-system-overview.mmd \
     -o figures/figure1-system-overview.pdf \
     --puppeteerConfigFile puppeteer-config.json
```

---

## Color convention (from source file)

| Color | Hex | Represents |
|---|---|---|
| Indigo | `#4F46E5` | Agents / consumers |
| Slate | `#475569` | Neutral infrastructure |
| Amber | `#D97706` | Pain dimension (Contribution 1) |
| Emerald | `#059669` | Shadow-mode discipline (Contribution 2) |
| Rose | `#E11D48` | Shared canonical corpus (Contribution 3) |

White text on dark fills throughout (WCAG AA compliant).

---

## arXiv submission notes

- arXiv accepts PDF, PNG, JPEG, and EPS figures. PDF vector is preferred.
- Maximum individual file size: 10 MB. Mermaid-generated PDFs are typically under 100 KB.
- If `pdflatex` fails with `! LaTeX Error: Cannot determine size of graphic`, the figure
  file is missing or corrupt. Verify with `file figures/figure1-system-overview.pdf`.
- For `\includegraphics[width=\linewidth]{figures/figure1-system-overview.pdf}` to work,
  the `graphicx` package must be loaded (it is, in `main.tex` preamble).
