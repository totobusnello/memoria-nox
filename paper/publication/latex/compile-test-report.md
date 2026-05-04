# Compile Test Report — NOX-Supermem Paper (main.tex)

**Date:** 2026-05-03
**Tester:** build-fixer agent
**Status:** COMPILE NOT ATTEMPTED — pdflatex not installed

---

## 1. Environment

| Item | Status |
|---|---|
| `pdflatex` | NOT INSTALLED |
| `xelatex` | NOT INSTALLED |
| `lualatex` | NOT INSTALLED |
| `latex` | NOT INSTALLED |
| `bibtex` | NOT INSTALLED |
| BasicTeX (brew cask) | Available — not installed |
| MacTeX (brew cask) | Available — not installed |

No TeX distribution is present on this machine. The compile was not attempted.

---

## 2. What Was Created

### `neurips_2024.sty` (stub)

Created at `paper/publication/latex/neurips_2024.sty`.

The stub implements:
- `\if@final` boolean (`final` option = true, `preprint` = false)
- `geometry` page layout (letter paper, 1in/1.25in margins — approximates NeurIPS single-column)
- `titlesec` section formatting
- `natbib` bibliography support (matches `\bibliographystyle{unsrt}`)
- `fancyhdr` header/footer with page numbers
- Stub `abstract` environment override
- `caption` package for figure/table captions
- `hyperref` color defaults (links black, URLs blue)
- Accepts unknown options silently (`nonatbib`, `longtitle`)
- No custom font requirements — uses LaTeX Computer Modern defaults

The stub does NOT load Times Roman / Helvetica / Palatino (the real NeurIPS .sty does).
Visual output will differ from the official template; content will be identical.

### Figure symlinks

The figures directory contains `figure1.pdf` through `figure4.pdf`, but `main.tex` references
the full descriptive names expected by the Makefile (`figure1-system-overview.pdf`, etc.).
Symlinks created:

```
figures/figure1-system-overview.pdf -> figure1.pdf
figures/figure2-salience-pipeline.pdf -> figure2.pdf
figures/figure3-shadow-state-machine.pdf -> figure3.pdf
figures/figure4-kg-edge-typing.pdf -> figure4.pdf
```

No modification to `main.tex`.

---

## 3. Static Analysis of main.tex

**Total lines:** 1,388
**Document class:** `article` + `\usepackage[final]{neurips_2024}`

### Packages used

All packages below are standard TeX Live / BasicTeX packages — none are exotic or require
manual installation beyond the base distribution.

| Package | Available in BasicTeX | Notes |
|---|---|---|
| `inputenc` (utf8) | Yes | Standard |
| `fontenc` (T1) | Yes | Standard |
| `hyperref` | Yes | Standard |
| `url` | Yes | Standard |
| `booktabs` | Yes | Required for `\toprule/\midrule/\bottomrule` |
| `amsfonts` | Yes | Math blackboard bold |
| `amsmath` | Yes | Math environments |
| `nicefrac` | Yes | Inline fractions |
| `microtype` | Yes | Margin kerning (auto-disabled if not available) |
| `xcolor` | Yes | Color support |
| `graphicx` | Yes | Figure inclusion |
| `verbatim` | Yes | Code verbatim blocks |
| `geometry` | Yes | Loaded by stub |
| `fancyhdr` | Yes | Loaded by stub |
| `titlesec` | Yes | Loaded by stub |
| `caption` | Yes | Loaded by stub |
| `natbib` | Yes | Loaded by stub |

**Verdict:** After installing BasicTeX, `tlmgr install booktabs titlesec natbib caption nicefrac microtype` covers any gaps. All packages ship with TeX Live 2026 base.

### Bibliography

- Style: `unsrt` (numbered, unsorted by appearance order)
- File: `../refs.bib` (relative path from `latex/` → `publication/refs.bib`)
- Entries in `refs.bib`: 21 references
- All keys cited in main.tex are present in refs.bib (verified by grep):

| Cite key | In refs.bib |
|---|---|
| `lewis2020rag` | Yes |
| `packer2023memgpt` | Yes |
| `chhikara2025mem0` | Yes |
| `xu2025amem` | Yes |
| `edge2024graphrag` | Yes |
| `huang2025hirag` | Yes |
| `guo2024hipporag` | Yes |
| `topoteretes2024cognee` | Yes |
| `cormack2009rrf` | Yes |
| `rogers2021just` | Yes |
| `manning2008introduction` | Yes |
| `fuhr2018some` | Yes |
| `muennighoff2022mteb` | Yes |
| `yang2018anserini` | Yes |
| `chen2024bge` | Yes |
| `wang2023improving` | Yes |

**No unresolved bibliography entries detected (static analysis).**

### Figure inclusion

| Expected filename | Symlink | Source file | Size |
|---|---|---|---|
| `figures/figure1-system-overview.pdf` | Yes | `figure1.pdf` | 58,564 bytes |
| `figures/figure2-salience-pipeline.pdf` | Yes | `figure2.pdf` | 40,679 bytes |
| `figures/figure3-shadow-state-machine.pdf` | Yes | `figure3.pdf` | 51,100 bytes |
| `figures/figure4-kg-edge-typing.pdf` | Yes | `figure4.pdf` | 53,155 bytes |

All four figures present and mapped. No placeholder needed.

Note: `figure2-salience-pipeline.pdf` is referenced only in Appendix A (line 1246 of main.tex).
The main body (line 498) references `figure3-shadow-state-machine.pdf`. Cross-check confirmed.

### Custom commands

None. `main.tex` uses only built-in LaTeX macros. No `\newcommand` or `\renewcommand`
definitions in the document body.

### Known potential warnings (not errors)

- `microtype` may emit "Could not auto-expand font" warnings on minimal installs — non-fatal.
- `hyperref` loaded after `natbib` in main.tex; this is the correct order and avoids conflicts.
- The `\if@final` branch in the stub adds a "Preprint. Under review." header — this is cosmetic.
- `nicefrac` may warn about `units` package conflict if `units` is loaded elsewhere — it is not.

---

## 4. Install Instructions

### Option A — BasicTeX (recommended, ~100 MB)

```bash
brew install --cask basictex
# After install, open a NEW terminal (PATH is updated by the pkg installer):
sudo tlmgr update --self
sudo tlmgr install booktabs titlesec natbib caption nicefrac microtype \
     latexmk collection-fontsrecommended
```

Then compile:

```bash
cd /Users/lab/Claude/Projetos/memoria-nox/paper/publication/latex
make draft        # single-pass, no bibliography (fast, ~10s)
make              # full build: pdflatex × 3 + bibtex (produces paper.pdf)
```

### Option B — MacTeX (full distribution, ~5 GB)

```bash
brew install --cask mactex
# Restart terminal, then:
cd /Users/lab/Claude/Projetos/memoria-nox/paper/publication/latex
make              # everything pre-installed, no tlmgr needed
```

### Option C — Overleaf (no install)

1. Zip the following files:
   ```
   latex/main.tex
   latex/neurips_2024.sty
   latex/figures/figure1.pdf  (and figures 2-4)
   publication/refs.bib
   ```
2. Upload zip to https://overleaf.com → New Project → Upload Project.
3. Set compiler to `pdflatex`, main document to `main.tex`.
4. Overleaf has all required packages pre-installed.

**Note:** On Overleaf, rename `figures/figure1.pdf` → `figure1-system-overview.pdf` etc.,
OR update the `\includegraphics` paths in main.tex (4 lines), OR keep the symlinks if
uploading the full directory.

### Option D — latexonline.cc API (CLI, no account)

```bash
# Requires internet; sends source to remote compiler
curl -O https://latexonline.cc/compile?url=... # not suited for local files
```

Not practical for local files with custom .sty and figures. Skip; use Overleaf instead.

---

## 5. Assessment

| Check | Result |
|---|---|
| `neurips_2024.sty` stub created | DONE |
| Figure symlinks created | DONE |
| All packages standard (BasicTeX-compatible) | PASS |
| Bibliography keys all resolved | PASS (static) |
| All 4 figures present | PASS |
| pdflatex available locally | FAIL — not installed |
| draft-preview.pdf generated | NOT GENERATED |

**Recommendation: "stub works for draft preview"** — once pdflatex is installed via
`brew install --cask basictex` + 5 minutes of `tlmgr` setup, the paper should compile
to a readable draft PDF on first pass. No real `neurips_2024.sty` needed for local
preview; only required for camera-ready submission to NeurIPS.

The real `neurips_2024.sty` must be downloaded from
`https://media.neurips.cc/Conferences/NeurIPS2024/Styles.zip` before final submission.
Replace the stub file in `paper/publication/latex/` with the official version.

---

## 6. `draft-preview.pdf`

Not generated — pdflatex is not installed. Run `make draft` after installing BasicTeX
to produce `main.pdf` (single-pass draft, no bibliography resolution).
