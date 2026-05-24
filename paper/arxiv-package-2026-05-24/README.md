# arXiv Submission Package — nox-mem
**Prepared:** 2026-05-24  
**Target submission:** Tue 2026-06-02 ~09h ET (06h BRT)  
**arXiv deadline for same-day processing:** 14h00 ET

---

## Submission Metadata

| Field | Value |
|---|---|
| **Title** | nox-mem: Pain-Weighted Hybrid Memory for LLM Agents |
| **Authors** | Luiz Antonio Busnello |
| **Affiliation** | Independent Researcher, São Paulo, Brazil |
| **Email** | lab@nuvini.com.br |
| **Primary category** | cs.IR — Information Retrieval |
| **Cross-list** | cs.LG — Machine Learning; cs.AI — Artificial Intelligence |
| **License** | CC BY 4.0 (paper) / MIT (code) |
| **Comments field** | Code: https://github.com/totobusnello/memoria-nox · MIT license |
| **Keywords** | agent memory; hybrid retrieval; pain-weighted salience; FTS5; sqlite-vec; RRF; LLM agents |

---

## Package Contents

| File | Description |
|---|---|
| `paper.pdf` | Compiled PDF — 35 pages, 140 KB, xelatex via pandoc 3.9.0.2 |
| `paper.tex` | LaTeX source — pandoc-generated from `paper/paper-tecnico-nox-mem.md` |
| `refs.bib` | BibTeX references — 14 entries, all URLs verified 2026-05-22 |
| `figures/` | Figures directory — empty (no inline figures in this version; text-only paper) |

---

## Build Provenance

- **Source:** `paper/paper-tecnico-nox-mem.md` (777 lines, 0 TBD placeholders)
- **Build command:** `bash scripts/build-paper.sh` (xelatex wrapper, PR #238)
- **Build engine:** pandoc 3.9.0.2 + XeTeX 3.141592653-2.6-0.999998 (TeX Live 2026)
- **PDF engine:** xelatex (required for Unicode math: ∈ ≈ ≤ ≥ Δ)
- **Build warnings:** Unicode chars (∈ ≈ ≤ ≥ ↔) fallback in lmmono10/lmroman10 fonts — rendered as blank in monospace code blocks; non-critical (chars appear in prose blocks with correct font)
- **PDF metadata:** Creator = "LaTeX via pandoc", Producer = xdvipdfmx, 35 pages, PDF 1.7

---

## Abstract (241 words, ≤300 limit)

Memory systems for LLM agents typically optimize for developer ergonomics, sacrificing retrieval quality or imposing vendor lock-in. Standardized cross-system benchmarks are scarce, making per-system accuracy claims difficult to reproduce or compare.

We present **nox-mem**, an open-source hybrid memory layer that combines FTS5 keyword retrieval, sqlite-vec dense retrieval, and Reciprocal Rank Fusion (RRF) over a zero-dependency SQLite database. We introduce a *pain-weighted salience* formula — `salience = recency × pain × importance × access_count` — where `pain` encodes incident severity on a continuous scale (0.1 trivial → 1.0 production outage), enabling retrieval to surface high-stakes memories even when recency is low. We further propose a **Conditional Hard Mutex** (G10d), which gates section and source-type boosts on query entity count (threshold τ=2), recovering multi-hop retrieval accuracy (+1.58% nDCG@10, +3.04% MRR on adversarial queries) without sacrificing single-hop precision.

We pre-register our methodology and report ten ablation studies (G3 through G10d) on LongMemEval (n=100) and LoCoMo, benchmarking against five production-grade memory systems (Mem0, Zep, Letta, agentmemory, EverMind-AI). Per-category breakdowns expose tradeoffs across multi-hop, temporal, and adversarial query types. All evaluation harnesses and raw results are published alongside the code.

Contributions: (i) pain-weighted salience formula that incorporates incident severity into memory scoring; (ii) Conditional Hard Mutex ablation protocol for boost interaction; (iii) open benchmark methodology reproducible against five competitors; (iv) production-stable single-file deployment (SQLite + FTS5 + sqlite-vec, zero external services). Code (MIT) and full evaluation harness: https://github.com/totobusnello/memoria-nox.

---

## Endorsement Status

arXiv cs.IR first-time submitter requires endorsement. Check account status at:
`https://arxiv.org/auth/show-endorsers?archive=cs&subject_class=IR`

**Action required Mon 2026-06-01:** Verify endorsement. If needed, request 48h before submit deadline (i.e., by Sun 2026-06-01 latest).

Best candidates for endorser request (authors cited in refs.bib):
- Gordon Cormack (RRF paper — cormack2009rrf) — University of Waterloo
- Di Wu et al. (LongMemEval — wu2024longmemeval)

---

## Known Issues / Caveats

1. **Abstract placeholders:** The abstract in `paper/abstract.md` contains `[Q4 NUMBERS]` placeholders for the final canonical benchmark run (100q × 2-dataset). These are NOT in the compiled paper — the paper uses the smoke run figures (nDCG@10 = 0.6380, MRR = 0.3700). Update abstract before submission once Q4 canonical run completes (target: Mon 2026-06-01).

2. **Font warnings:** Unicode chars ∈ ≈ ≤ ≥ ↔ in `lmmono10` monospace font blocks fallback silently. These appear in inline code samples. Visible in PDF as blank — minor cosmetic issue in code display. Does not affect the mathematical equations which use proper math mode.

3. **arXiv XeLaTeX:** The paper uses `unicode-math` / `fontspec` which signals XeLaTeX to arXiv's compiler. arXiv supports XeLaTeX via TeX Live 2023+. No action needed.

4. **No figures:** This version of the paper (MD→pandoc→xelatex path) does not include the 4 architecture figures from `paper/publication/latex/figures/`. For a richer submission, consider migrating to the NeurIPS LaTeX version at `paper/publication/latex/main.tex` (requires filling 8 TBD cells in Table 8 first).
