# IP&M submission: what is done and what is left

Plan: `../ipm-submission-plan.md`. The owner submits; no script here submits anything.

## Done (2026-11-27)

- [x] Title without "Pain-Weighted" (owner, 2026-11-26 21:19).
- [x] Condensed manuscript, `manuscript.md`: 8,335 words before references (report: 28,256), abstract 249
      words, five highlights of at most 85 characters, keywords, Elsevier generative-AI declaration,
      data availability, competing interest, funding.
- [x] Comparison at the centre (Section 4); system in Section 3; ablation, EverMemBench, LongMemEval and
      the operational profile in Section 5. Classical multi-hop QA, LoCoMo cross-bench, the multi-hop
      analysis, orchestration and the five-batch protocol detail are summarized and pointed to S1.
- [x] Related work rebuilt with 2025–2026 studies (`related-work-2025-2026.md`), every arXiv id and
      author list read from the arXiv API.
- [x] Provenance: `build_provenance.py` writes `PROVENANCE.json`; every decimal number and percentage of
      the manuscript occurs verbatim in the report at a commit on `main`; the CI gate checks it. Negative
      test: one value changed (0.6455 → 0.6465) fails both `build_provenance.py --check` and
      `tools/provenance.py --check`.
- [x] avoid-ai-writing pass: no em dashes, no listed vocabulary; repeated "X, not Y" contrasts thinned.
- [x] Anonymization of the manuscript text: no name, ORCID, e-mail, repository URL, Zenodo DOI or agent
      names; identity only in `title-page.md`.

## Left, in order

1. **Owner reads `manuscript.md`.**
2. **Decision: system name in the anonymized version.** Keeping "nox-mem" lets a reviewer find the Zenodo
   report and its author by search. IP&M allows preprints, and naming the system is common; the
   alternative is a placeholder name in the review copy only. Recommendation: keep the name.
3. **Re-read in the PDF** the abstract and the cited result of each 2025–2026 paper in Section 2.3–2.4
   (the sweep read them through a summarizer).
4. **Figure 1:** check `../latex/figures/figure1-system-overview.pdf` against Section 3 (it predates
   the additive salience) and for identifying text; redraw if needed.
5. **Supplementary S1:** anonymized copy of the report (strip name, ORCID, e-mail, DOIs, repository
   URLs, host details and agent names); S2 and S3 from `../supplement-*.md`, anonymized the same way.
6. **Anonymous code link for reviewers** (an anonymizing mirror of the repository), if the owner wants
   reviewers to have code during review; otherwise the data statement stands as written.
7. **Elsevier CAS LaTeX** (`els-cas-templates`, `cas-sc`): convert `manuscript.md`, build the anonymized
   PDF, the highlights file and the title page; rerun the provenance gate on the converted text.
8. **Cover letter** (states the preprint, the pre-specification, and that no number is new).
9. Voices only if the owner asks.
10. **Owner submits** through Elsevier's system.
