# Pre-Submit Checklist — NOX-Supermem Paper

> **Target submit:** 2026-06-02 before 14:00 ET (17:00 BRT)
> **Paper version:** v1.0.0-paper-draft | **Tag:** f75d186
> **Run this checklist:** day before submit (2026-06-01), not morning of.

---

## BLOCKERS (must resolve before submit)

| # | Blocker | Owner | Est. time | Hard dependency |
|---|---------|-------|-----------|----------------|
| B1 | md→tex full conversion | Toto | 2–3h | arXiv requires .tex source, not .md |
| B2 | pdflatex compile + zero errors | Toto | 1h | Confirms citations, figures, page count |
| B3 | arXiv account active + cs.IR endorsement secured | Toto | async (contact endorser by 2026-05-28) | Cannot submit without endorsement if account is new |

---

## LaTeX / PDF

| Check | Status | Evidence / Note |
|-------|--------|-----------------|
| PDF compiles cleanly (`pdflatex main.tex` twice + `bibtex main` + twice more) | ❌ | md→tex conversion in progress; pdflatex not installed locally |
| No `?` citation markers in compiled PDF | 🟡 | Pending compile. All BibTeX keys verified in source; 0 orphans found in audit 2026-05-04 |
| No `??` figure reference markers | 🟡 | Pending compile |
| All figures embedded as PDF/EPS (not PNG raster) | ✅ | 4 PDFs confirmed in `latex/figures/`: fig-salience-formula.pdf, fig-architecture-overview.pdf, fig-hybrid-search-pipeline.pdf, fig-shadow-discipline-flow.pdf |
| Page count 18–22 (`pdfinfo main.pdf \| grep Pages`) | 🟡 | Pending compile |

---

## Metadata Limits

| Check | Status | Evidence / Note |
|-------|--------|-----------------|
| Abstract < 1920 characters (count without LaTeX markup) | 🟡 | Current prose ~2260 chars with LaTeX math notation. Renders shorter post-compile. Verify with `wc -m` on stripped text post-compile. |
| Title < 250 characters | ✅ | 90 chars: "The Pain Diary and Shadow Discipline: A Memory System That Learns from Its Own Incidents" |
| Comments < 1024 characters | ✅ | ~280 chars (confirmed in arxiv-submit-metadata.md §4) |

---

## Content Integrity

| Check | Status | Evidence / Note |
|-------|--------|-----------------|
| nDCG@10 values consistent across abstract, body, and tables | ✅ | Audited 2026-05-04: 0.5213 ± 0.0004 (abstract + §5.1 + Table 5 agree) |
| Author name spelled identically everywhere: "Luiz Antonio Busnello" | ✅ | Verified in abstract, §1, CITATION.cff |
| Repository URL live and public: github.com/totobusnello/memoria-nox | ✅ | Confirmed public; appears in abstract + §1 footnote |
| CITATION.cff version field matches tag | ✅ | version: "1.0.0-paper-draft" matches git tag f75d186 |
| Chunk count consistent across all 5 citation sites | ✅ | 61,257 verified in: abstract, §1.2, §3.2, §5.1, CITATION.cff (audited 2026-05-04) |

---

## Citation / Bibliography

| Check | Status | Evidence / Note |
|-------|--------|-----------------|
| Citation graph orphans | ✅ | 0 orphans; 25 cited / 29 defined (audit 2026-05-04) |
| Appendix D inline keys match refs.bib | ✅ | Aligned to `packer2023memgpt`, `chhikara2025mem0`, `xu2025amem` |
| BEIR Thakur 2021 in refs.bib | ✅ | Added as `thakur2021beir` |
| Kohavi 2020 + Chapelle 2012 in refs.bib | ✅ | Added; cited in §1.2 for shadow deployment prior art |
| RAPTOR removed from refs.bib | ✅ | Removed (was unused) |

---

## Experiments / Results

| Check | Status | Evidence / Note |
|-------|--------|-----------------|
| E10 pain ablation executed and integrated in §5.5 | ✅ | Δ nDCG@10 = +0.0065, 95% CI [-0.0143, +0.0338], DIRECTIONAL verdict. Results in `results/E10-pain-ablation-hybrid-results.md` |
| LOCOMO results integrated in §5.3 | ✅ | nDCG@10 = 0.2810 (FTS5 + hybrid), n=100, integrated in Table 5 |
| E5 multilingual-base result in Table 5 §5.2 | ✅ | Baseline populated; closes [PENDING] gap from critic review |
| BEIR TREC-COVID result | ❌ | Running on VPS (tmux `beir-trec`); ETA 2026-05-05. Check: `ssh root@187.77.234.79 'tmux capture-pane -p -t beir-trec 2>/dev/null \| tail -20'` |
| Pain claim downgraded to "directional" throughout | ✅ | Abstract + §1.3 + §5.5 updated; no "demonstrates" language remains |

---

## Submission Logistics

| Check | Status | Evidence / Note |
|-------|--------|-----------------|
| arXiv account active and email verified | 🟡 | Toto's action |
| Endorsement secured (cs.IR) | 🟡 | Toto's action. Contact endorser by 2026-05-28 (4-day buffer). Best candidates: Patrick Lewis (RAG paper), Gordon Cormack (RRF paper). |
| License decision locked: CC BY 4.0 (paper) + MIT (code) | ✅ | LICENSE file in repo; declared in arxiv-submit-metadata.md §8 |
| Source tar.gz prepared | ❌ | md→tex pending; use `scripts/arxiv-tar.sh` once .tex ready |

---

## Today's Work — New Checks (2026-05-04)

| Check | Status | Evidence |
|-------|--------|---------|
| Citation graph orphans: 0 | ✅ | 25 cited / 29 defined audit |
| Chunk count 61,257 consistent across all 5 sites | ✅ | Cross-site audit complete |
| Git tag v1.0.0-paper-draft created | ✅ | Commit f75d186 |
| LOCOMO results integrated §5.3 | ✅ | Table 5 row populated |
| E5 multilingual-base integrated Table 5 | ✅ | Dense baseline gap closed |
| Abstract tightened 367→279 prose words | ✅ | M1 resolved |
| Self-graded rubric reframed (added 2 nox-mem ❌ cells) | ✅ | C3 resolved |
| §6.4 cost analysis added | ✅ | H5 resolved |
| DECISIONS.md current | ✅ | Reflects all paper decisions taken today |
| HANDOFF.md current | ✅ | Updated end-of-day 2026-05-04 |

---

## Source Upload

Files to include in tar.gz (from `paper/latex/` directory):

```bash
tar -czf arxiv-submit-$(date +%Y%m%d).tar.gz \
  main.tex refs.bib neurips_2024.sty figures/*.pdf
```

Or via script:

```bash
bash scripts/arxiv-tar.sh
```

---

## Next-Session Actions (first thing 2026-05-05 morning)

1. Check BEIR TREC-COVID result:
   ```bash
   ssh root@187.77.234.79 'tmux capture-pane -p -t beir-trec 2>/dev/null | tail -30'
   ```
   If complete: integrate result in §5.2 Table 5 BEIR row, update abstract if materially different from expected range.

2. Run md→tex conversion script and attempt first pdflatex compile on VPS:
   ```bash
   ssh root@187.77.234.79 'which pdflatex || apt-get install -y texlive-full'
   ```

3. Hand `critic-rereview-2-prep.md` to a `critic` agent (Opus, adversarial mode) with instructions to verify each ✅ claim by reading the referenced paper sections.

4. After critic review #2 clears: prepare tar.gz + begin arXiv endorsement outreach.
