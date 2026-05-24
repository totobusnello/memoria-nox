# arXiv Submission Guide — Ready to Submit
**Paper:** nox-mem: Pain-Weighted Hybrid Memory for LLM Agents  
**Submission target:** Tue 2026-06-02, before 14h00 ET (11h00 BRT)  
**Prepared:** 2026-05-24  
**Package location:** `paper/arxiv-package-2026-05-24/`

---

## Pre-flight Checklist (Mon 2026-06-01)

- [ ] **Q4 abstract numbers finalized** — replace smoke figures in abstract with canonical run results if complete (ref: `specs/2026-05-23-Q4-comparison-execution-plan.md`)
- [ ] **arXiv account active** — create at https://arxiv.org/user/register if not yet done
- [ ] **Email verified** — arXiv requires email verification before first submission
- [ ] **Endorsement check** — visit `https://arxiv.org/auth/show-endorsers?archive=cs&subject_class=IR`. If endorsement required: send email to candidate endorsers (see §5 below)
- [ ] **PDF visual check** — open `paper/arxiv-package-2026-05-24/paper.pdf`, verify: title correct, abstract matches §1 below, no garbled math, tables readable
- [ ] **git tag v1.0.0-rc1** — `git tag v1.0.0-rc1 && git push origin v1.0.0-rc1` (2-min task)

---

## §1 Submission Form — Copy-Paste Fields

### Title (copy exactly — no trailing period)
```
nox-mem: Pain-Weighted Hybrid Memory for LLM Agents
```

### Authors (one per line in arXiv form)
```
Luiz Antonio Busnello
```
**Affiliation field:** `Independent Researcher, São Paulo, Brazil`  
**Email:** `lab@nuvini.com.br`  
**ORCID:** (optional — register at orcid.org if desired before submit)

### Abstract (paste verbatim — 241 words, well under 1920 char limit)

> **IMPORTANT:** Before pasting, fill in `[Q4 NUMBERS]` if canonical run is complete.  
> If not complete: use the smoke-run version below (already filled, disclosure in paper).

```
Memory systems for LLM agents typically optimize for developer ergonomics, sacrificing retrieval quality or imposing vendor lock-in. Standardized cross-system benchmarks are scarce, making per-system accuracy claims difficult to reproduce or compare.

We present nox-mem, an open-source hybrid memory layer that combines FTS5 keyword retrieval, sqlite-vec dense retrieval, and Reciprocal Rank Fusion (RRF) over a zero-dependency SQLite database. We introduce a pain-weighted salience formula -- salience = recency x pain x importance x access_count -- where pain encodes incident severity on a continuous scale (0.1 trivial to 1.0 production outage), enabling retrieval to surface high-stakes memories even when recency is low. We further propose a Conditional Hard Mutex (G10d), which gates section and source-type boosts on query entity count (threshold t=2), recovering multi-hop retrieval accuracy (+1.58% nDCG@10, +3.04% MRR on adversarial queries) without sacrificing single-hop precision.

We pre-register our methodology and report ten ablation studies (G3 through G10d) on LongMemEval (n=100) and LoCoMo, benchmarking against five production-grade memory systems (Mem0, Zep, Letta, agentmemory, EverMind-AI). Per-category breakdowns expose tradeoffs across multi-hop, temporal, and adversarial query types. All evaluation harnesses and raw results are published alongside the code.

Contributions: (i) pain-weighted salience formula that incorporates incident severity into memory scoring; (ii) Conditional Hard Mutex ablation protocol for boost interaction; (iii) open benchmark methodology reproducible against five competitors; (iv) production-stable single-file deployment (SQLite + FTS5 + sqlite-vec, zero external services). Code (MIT) and full evaluation harness: https://github.com/totobusnello/memoria-nox.
```

> **Note:** arXiv abstract field is plain text — no LaTeX markup. The version above has all math notation replaced with ASCII equivalents (× → x, ≤ → <=, τ → t, × → x, etc.).

### Primary Category
```
cs.IR
```

### Cross-list Categories (select all three)
```
cs.LG
cs.AI
```

### License
```
Creative Commons Attribution 4.0 International (CC BY 4.0)
```

### Comments field (optional but recommended)
```
Code: https://github.com/totobusnello/memoria-nox · MIT license
```

---

## §2 File Upload — Step by Step

arXiv accepts either:
- **(A) PDF only** — simplest, faster review. Upload `paper/arxiv-package-2026-05-24/paper.pdf` directly.
- **(B) LaTeX source** — preferred by arXiv for reproducibility. Upload `paper.tex` + `refs.bib` as a `.tar.gz`.

**Recommendation: start with option (A) PDF-only** to avoid LaTeX compilation issues on arXiv's server (unicode-math/fontspec require XeLaTeX which arXiv supports but may need a `%!TEX program = xelatex` directive).

### Option A — PDF Only (recommended for Tue submit)

1. In arXiv submission form, select "Upload files"
2. Upload `paper/arxiv-package-2026-05-24/paper.pdf`
3. Select "I am uploading a PDF directly" (not LaTeX source)
4. Proceed to metadata entry

### Option B — LaTeX Source (fallback if PDF-only rejected)

Create tar.gz from `paper/arxiv-package-2026-05-24/`:
```bash
cd paper/arxiv-package-2026-05-24
tar -czf ../arxiv-submit-2026-06-02.tar.gz paper.tex refs.bib figures/
```

Then upload `arxiv-submit-2026-06-02.tar.gz` in the "Upload files" step.

**If using LaTeX source:** Add this line at the very top of `paper.tex` before `\PassOptionsToPackage`:
```latex
%!TEX program = xelatex
```
This tells arXiv's AutoTeX to use XeLaTeX. Without it, AutoTeX may try pdflatex and fail on `unicode-math`.

---

## §3 Submission Flow (step by step on arxiv.org)

1. Login at https://arxiv.org/login
2. Click "Start new submission"
3. Select subject area: **Computer Science**
4. Select primary category: **cs.IR**
5. Add cross-list: **cs.LG**, **cs.AI**
6. Upload file (option A or B per §2)
7. Verify preview — check title renders, first page of PDF visible
8. Fill metadata form:
   - Title: copy from §1
   - Authors: `Luiz Antonio Busnello` + affiliation
   - Abstract: paste from §1 (plain text, no LaTeX)
   - Comments: `Code: https://github.com/totobusnello/memoria-nox · MIT license`
9. Select license: **CC BY 4.0**
10. Review submission summary — check all fields
11. Click "Submit" — arXiv will queue for moderation
12. Receive confirmation email with submission ID (format `2606.XXXXX`)

---

## §4 After Submission (Tue 2026-06-02 afternoon)

| Task | Action |
|---|---|
| Receive arXiv ID | Note `2606.XXXXX` from confirmation email |
| Update CITATION.cff | `arxiv_id: 2606.XXXXX` + `url: https://arxiv.org/abs/2606.XXXXX` |
| Update README badge | `[![arXiv](https://img.shields.io/badge/arXiv-2606.XXXXX-b31b1b)](https://arxiv.org/abs/2606.XXXXX)` |
| Update launch social copy | Replace `[arXiv link TBD]` in `docs/launch-social-copy.md` |
| Create GitHub Release | `gh release create v1.0.0-rc1 --notes-file docs/releases/v1.0.0-rc1.md` |
| Paper appears publicly | Wed morning ET (if submitted before 14h ET Tue) |

---

## §5 Endorsement — Action if Required

arXiv cs.IR requires endorsement for first-time submitters with no prior cs.* papers.

**Check first:** `https://arxiv.org/auth/show-endorsers?archive=cs&subject_class=IR`

If endorsement is needed, use this email template:

```
Subject: arXiv endorsement request — cs.IR submission

Dear [Name],

I am submitting a paper titled "nox-mem: Pain-Weighted Hybrid Memory for LLM Agents"
to arXiv cs.IR on 2026-06-02. Your work [cite their paper referenced in refs.bib]
is directly cited in our evaluation section.

I am a first-time arXiv submitter in cs.IR and would be grateful for an endorsement.
The paper is available at: https://github.com/totobusnello/memoria-nox
(paper/paper-tecnico-nox-mem.md or the compiled PDF in paper/build/).

Endorsement takes only a few minutes via arXiv's automated system — you will
receive a link from arXiv after I initiate the endorsement request in my submission.

Thank you,
Luiz Antonio Busnello
lab@nuvini.com.br
Independent Researcher, São Paulo, Brazil
```

**Best candidates (authors with verified arXiv presence, cited in refs.bib):**
1. Gordon Cormack (`cormack2009rrf`) — University of Waterloo — RRF paper author
2. Di Wu (`wu2024longmemeval`) — LongMemEval ICLR 2025 lead author
3. Adyasha Maharana (`maharana2024locomo`) — LoCoMo ACL 2024 first author

**Timeline:** endorsement can take 24-48h. Request by **Sun 2026-06-01 at latest** (ideally Sat 2026-05-31).

---

## §6 Build Reproducibility

To rebuild the PDF from scratch:
```bash
# From repo root
rm -f paper/build/paper-tecnico-nox-mem.pdf
bash scripts/build-paper.sh
# Output: paper/build/paper-tecnico-nox-mem.pdf (35 pages, ~140 KB)
```

**Dependencies:** pandoc ≥ 3.x + TeX Live 2026 with xelatex + xdvipdfmx

Build warnings (expected, non-blocking):
- `Missing character: There is no ∈/≈/≤/≥/↔ in font [lmmono10-regular]` — Unicode chars in code blocks fallback to blank in monospace. Math mode chars render correctly in prose.

---

## §7 Parallel LaTeX Option (NeurIPS format, richer figures)

The repo also has a NeurIPS-formatted LaTeX paper at `paper/publication/latex/main.tex` with 4 architecture figures. This version has 8 TBD cells in Table 8 (per-category entity breakdown from G12 R01b audit). If time permits before Tue submit:

1. Fill Table 8 from `audits/2026-05-21-G12-frontmatter-retrieval-audit.md`
2. Run `make` in `paper/publication/latex/` to rebuild `paper.pdf`
3. Use this version for arXiv (better figures, NeurIPS professional format)
4. Include `figures/*.pdf` in the tar.gz upload

Estimated effort: 1-2h to fill Table 8 + rebuild + visual QA.

**If choosing this path:** the submission metadata (§1) stays identical — only the source files change.
