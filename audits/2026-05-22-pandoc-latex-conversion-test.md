# Pandoc / LaTeX Conversion Test — pre-arXiv audit

**Date:** 2026-05-21 (Fri night)
**arXiv target:** Tue 2026-06-02 (D27 sequencing, PR #228)
**Tester:** agent-ae96a451fc53392aa (worktree)
**Paper source:** `paper/paper-tecnico-nox-mem.md` (DO NOT EDIT — PR #226 open)

---

## §1 Tool availability

| Tool | Status | Version |
|---|---|---|
| pandoc | INSTALLED | 3.9.0.2 |
| pdflatex | INSTALLED | pdfTeX 3.141592653-2.6-1.40.29 (TeX Live 2026) |

Both tools available on local Mac — no install required.

---

## §2 Conversion results

### .md → .tex (pandoc)

**Command:**
```
pandoc paper/paper-tecnico-nox-mem.md -o /tmp/paper-test.tex --standalone
```

**Result: PASS**
- Exit code: 0
- No warnings in stderr (clean conversion)
- Output: `/tmp/paper-test.tex` — 1,521 lines
- Preamble: standard `article` class with `xcolor`, `amsmath`, `amssymb`, `lmodern`, `longtable`, `booktabs`, `hyperref`
- Structure: proper `\begin{document}` ... `\end{document}` with all 13 sections

### .tex → .pdf (pdflatex)

**Command:**
```
cd /tmp && pdflatex -interaction=nonstopmode paper-test.tex
```

**Pass 1 result: PASS (with non-fatal warnings)**
- Exit code: 0 (PDF produced)
- Output: `/tmp/paper-test.pdf` — **22 pages, 229 KB**
- Warnings (non-fatal): multiple `Overfull \hbox` on long inline code tokens (e.g., `nox_mem_cross_kg`, `/api/search?q=QUERY&limit=N`) — cosmetic only
- Warning: `longtable` table widths changed → rerun needed (standard)
- Warning: labels may have changed → rerun needed (standard)

**Pass 2 result: PASS (PDF updated) + UNICODE ERRORS**
- PDF re-generated successfully (229 KB, cross-refs resolved)
- **Non-fatal Unicode errors fired** (pdflatex engine limitation with Unicode math outside `$...$`):

| Character | Unicode | Occurrences |
|---|---|---|
| Σ | U+03A3 | 1 |
| Δ | U+0394 | ~15+ |
| ∈ | U+2208 | 2 |
| ≈ | U+2248 | 1 |
| − | U+2212 | ~10+ |
| ≤ | U+2264 | 1 |
| ≥ | U+2265 | 1 |

**Severity:** These are errors in strict mode but pdflatex continued and produced output. However, on arXiv's LaTeX server (which may use a stricter compilation profile), these **could cause compilation failure**. Must fix before submission.

---

## §3 Known issues to fix Mon 2026-05-26

### CRITICAL — Unicode math outside `$...$` (7 character types, ~30+ occurrences)

**Root cause:** `paper-tecnico-nox-mem.md` uses raw Unicode math symbols inline in prose and tables (e.g., `Δ vs G3`, `recency ∈ [7, 30]`, `−9.5%`, `≈ 2,307 chunks`). pdflatex with T1 encoding cannot render these.

**Fix options (pick one):**

1. **Wrap in math mode (recommended):** Replace inline unicode with LaTeX math:
   - `Δ` → `$\Delta$`
   - `Σ` → `$\Sigma$`
   - `∈` → `$\in$`
   - `≈` → `$\approx$`
   - `−` (U+2212, minus sign) → `$-$` or just ASCII `-`
   - `≤` → `$\leq$`
   - `≥` → `$\geq$`

2. **Switch compiler to XeLaTeX or LuaLaTeX:** These support Unicode natively. Change pandoc command to `pandoc --pdf-engine=xelatex`. Requires `fontspec` package (already in pandoc default template for non-pdflatex path).
   - **Faster fix** since no source edits needed
   - Command: `pandoc paper.md -o paper.tex --standalone --pdf-engine=xelatex`
   - arXiv supports XeLaTeX — TeX Live 2023+ required (arXiv runs TL2023 as of 2026)

3. **Add `--from markdown+tex_math_dollars`** and ensure all math is inside `$...$` in the .md source (requires editing the paper).

**Recommendation:** Fix (2) for the conversion test (fast validation); fix (1) in the paper source for final arXiv submission (cleaner, engine-agnostic).

### LOW — `Overfull \hbox` on long identifiers

MCP tool names (`nox_mem_cross_kg`, `nox_mem_self_improve`) and API paths (`/api/search?q=QUERY&limit=N`) overflow the line width. Cosmetic only — does not affect PDF generation or arXiv acceptance.

**Fix:** Wrap in `\path{...}` in the .tex or use line-break hints (`\allowbreak`) — or shorten identifiers in the paper source.

### LOW — No `refs.bib` bibliography

No `--bibliography` flag was passed because `paper/refs.bib` does not exist yet. The paper has no `[@cite]` markers currently. If citations are added for arXiv version, create `paper/refs.bib` and add `--bibliography=paper/refs.bib --citeproc` to the pandoc command.

### INFO — `longtable` + `booktabs` dependency

The converted .tex uses `longtable` and `booktabs` packages for tables. Both are standard TeX Live packages — no issue on arXiv. Tables with many columns (e.g., the ablation result tables) render correctly.

### INFO — No figures/images in current paper

No `![](...)` image references found in the paper source. When diagrams are added (arch diagram, comparison chart from PR #130), they must be embedded as PNG or PDF, not remote URLs, and included with the .tex source in the arXiv upload zip.

---

## §4 Pre-Tue 06-02 LaTeX prep checklist

- [ ] Fix Unicode math chars (7 types, ~30 occurrences) — either wrap `$...$` in source or switch to XeLaTeX
- [ ] Validate fix with `pandoc --pdf-engine=xelatex paper.md -o paper.pdf` (direct PDF, skip intermediate .tex)
- [ ] Run conversion test again post-Q4 numbers fill (Sat 2026-05-24 ~18h BRT)
- [ ] Generate `paper/refs.bib` if citations will be added for arXiv version (PR TBD)
- [ ] Confirm any figures are embedded as local PNG/PDF (no remote URLs)
- [ ] Verify title page metadata: title, authors, affiliations, date in paper YAML frontmatter
- [ ] Verify arXiv abstract <300 words (check `paper/paper-tecnico-nox-mem.md` abstract section)
- [ ] Confirm `.tex` file size reasonable (<10 MB) — current at 1,521 lines / ~70 KB, well within limits
- [ ] arXiv submission: upload as `.tex` + `.bib` (if any) + figures ZIP — NOT just PDF
- [ ] Test full compile on clean TeX Live install (or arXiv's overleaf preview tool) before submitting

---

## §5 Sat 2026-05-24 evening followup

After Q4 numbers are cravados (Sat ~18h BRT):

1. Re-run conversion with XeLaTeX fix:
   ```
   pandoc paper/paper-tecnico-nox-mem.md -o /tmp/paper-test-xelatex.pdf \
     --standalone --pdf-engine=xelatex 2>&1
   ```
2. Verify 0 errors (not just warnings)
3. Check page count and PDF size
4. If refs.bib exists: add `--bibliography=paper/refs.bib --citeproc`
5. If figures added: confirm they resolve locally before arXiv upload

---

## §6 Summary verdict

| Stage | Status |
|---|---|
| pandoc .md → .tex | **PASS** (exit 0, clean) |
| pdflatex pass 1 (.tex → .pdf) | **PASS** (22 pages, 229 KB produced) |
| pdflatex pass 2 (cross-refs) | **PASS with errors** (PDF updated but 7 Unicode char types fail) |
| arXiv-ready (strict LaTeX) | **NOT YET** — Unicode math fix required |

**Blockers before Tue 06-02:** 1 (Unicode math chars). Estimated fix time: 30-60 min (XeLaTeX switch = 5 min; source fix = 30-60 min depending on scope of Q4 additions).

**No panic needed.** The pipeline works end-to-end. One well-scoped fix Mon 2026-05-26 clears the path.
