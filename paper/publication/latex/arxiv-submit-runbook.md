# arXiv Submission Runbook — nox-mem paper

Target venue: arXiv cs.IR / cs.AI (cross-list)
Metadata source: `../04-paper-arxiv-draft.md` (abstract, authors, categories)

---

## 1. Pre-flight checklist

Run these before packaging. All items must pass.

**Compile**

```bash
cd paper/publication/latex
make clean && make
```

Expected: `paper.pdf` generated with zero errors in the final pdflatex pass.
Warnings about overfull hboxes are acceptable; `! Fatal error` is not.

**Citations**

```bash
grep "?" paper.pdf 2>/dev/null || bibtex main && grep "\[?\]" main.blg
```

No `[?]` citations in the PDF. If bibtex reports missing references, add them
to `../refs.bib` and rebuild.

**Figures**

```bash
ls -lh figures/figure{1,2,3,4}.pdf
```

All four files present, each > 5 KB (a stub/corrupt file is smaller).
Open `paper.pdf` and visually confirm the figures render — not blank boxes.

**File sizes**

```bash
du -sh figures/*.pdf ../refs.bib main.tex neurips_2024.sty
```

No single file should exceed 10 MB. Total uncompressed should be under 5 MB.

---

## 2. Run arxiv-package.sh

```bash
cd paper/publication/latex
./arxiv-package.sh
```

Default output: `arxiv-submission.tar.gz` in the same directory.

Optional custom name:

```bash
./arxiv-package.sh nox-mem-v1.0.tar.gz
```

Verify the archive contents before uploading:

```bash
tar -tzf arxiv-submission.tar.gz
```

Expected listing:

```
arxiv-pkg/
arxiv-pkg/main.tex
arxiv-pkg/neurips_2024.sty
arxiv-pkg/refs.bib
arxiv-pkg/figures/figure1.pdf
arxiv-pkg/figures/figure2.pdf
arxiv-pkg/figures/figure3.pdf
arxiv-pkg/figures/figure4.pdf
arxiv-pkg/figures/figure1-system-overview.pdf
arxiv-pkg/figures/figure2-salience-pipeline.pdf
arxiv-pkg/figures/figure3-shadow-state-machine.pdf
arxiv-pkg/figures/figure4-kg-edge-typing.pdf
```

---

## 3. Login arXiv and start submission

1. Go to https://arxiv.org/login
2. Log in with your arXiv account (register at https://arxiv.org/register if first time).
3. Click **Submit** in the top menu.
4. Select **New submission**.

---

## 4. Upload the archive

1. On the "Upload Files" step, select **Upload a .tar.gz or .zip**.
2. Browse to `paper/publication/latex/arxiv-submission.tar.gz` and upload.
3. arXiv will unpack the archive and show the detected files.
4. Confirm `main.tex` is listed as the main file. If arXiv picks the wrong root,
   use the file-selector dropdown to set it manually.
5. Click **Process** and wait for arXiv's pdflatex to complete (~30 seconds).

---

## 5. Fill in submission metadata

Fields to complete (values in `../04-paper-arxiv-draft.md` and `../paper-abstract.md`):

| Field | Value |
|---|---|
| Title | From the paper abstract file |
| Authors | Full names, no affiliations required for initial submission |
| Abstract | Verbatim from `../paper-abstract.md` (plain text, no LaTeX math) |
| Primary category | cs.IR (Information Retrieval) |
| Cross-list | cs.AI, cs.CL |
| Comments | "9 pages, 4 figures" (adjust if page count changes) |
| License | CC BY 4.0 (recommended for open-access) |

Do not include journal/conference references in Comments until accepted.

---

## 6. Preview the generated PDF

1. After processing, click **View PDF**.
2. Spot-check:
   - All four figures render (not blank boxes)
   - No `[?]` citation placeholders
   - Title, authors, abstract on page 1 match what you typed in metadata
   - Page count looks right (~9 pages)
3. If anything is wrong, click **Back** and fix the source before submitting.

---

## 7. Submit and monitor

1. Click **Submit** on the final confirmation page.
2. arXiv sends a confirmation email immediately to your registered address.
3. The submission enters the moderation queue.

**Timeline:**

| Time | Event |
|---|---|
| Submission day 14:00 ET | Submission deadline for next-day appearance |
| Next business day ~20:00 ET | Announcement email with arXiv ID |
| ~2 hours after announcement | Paper live at https://arxiv.org/abs/YYMM.NNNNN |

---

## 8. Day-1 actions after arXiv assigns an ID

1. **Record the ID** in `docs/HANDOFF.md` and `docs/ROADMAP.md`.
2. **Update the paper PDF header** (optional): add `\arxivid{YYMM.NNNNN}` if the
   template supports it, or note in `\thanks{}`.
3. **Canonical URL**: https://arxiv.org/abs/YYMM.NNNNN — use this in all posts.
4. **Distribution sequence** (see `08-launch-strategy.md`):
   - Tweet the arXiv link with the thread draft in `distribution/twitter-thread.md`
   - LinkedIn post from `distribution/linkedin-post.md`
   - HN submission title from `06-hn-titles-ABtest-results.md` (use the winning variant)
   - Blog post from `blog-post-final.md` (add arXiv link at top)
5. **Submit to cs.IR mailing list** if you haven't already (auto-announced via arXiv).

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| arXiv pdflatex fails on `\usepackage{neurips_2024}` | Confirm `neurips_2024.sty` is in the archive root (it should be) |
| Blank figure boxes | arXiv could not find the PDF. Check filenames match `\includegraphics{}` paths exactly |
| "Cannot determine size of graphic" | Figure PDF is corrupt. Rebuild from `.mmd` source (see `figures/README.md`) |
| Archive > 50 MB | Figures are too large. Re-export as compressed PDF from mermaid-cli |
| Missing citation `[?]` | `refs.bib` entry missing or key typo — fix locally, rebuild, repackage |
