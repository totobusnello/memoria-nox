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

- [x] Owner read the draft (2026-11-27) and kept the system name in the anonymized version.
- [x] Related work re-read in the papers' own text (`related-work-check-2026-11-27.md`): 31 papers,
      26 supported, 5 overreaching; the 5 sentences were reworded as the check proposed, and three
      reference entries fixed (Nemori cited as the arXiv v4 preprint, SimpleMem without the unconfirmed
      venue, LightRAG without the unchecked page range).
- [x] Figure 1 redrawn from Section 3 (`figures/make_figure1.py`): the old figure named the six agents
      and carried stale counts. No agent names, no counts.
- [x] Supplementary S1-S3 (`build_supplements.py` -> `supplement/`): report and both supplements
      copied as they stand, with only author, ORCID, e-mail, DOIs, repository links, host paths and
      agent names replaced; `--check` fails on any identifier left (negative test: a planted e-mail
      address fails it).
- [x] Elsevier CAS LaTeX (`latex/build_latex.py`): anonymized `manuscript.pdf`, `highlights.txt`,
      `title-page.pdf`; the build checks that the PDF prints exactly the manuscript's numbers
      (negative test: 0.6455 changed to 0.6465 in the Markdown fails it).
- [x] Cover letter (`cover-letter.md`): preprint, pre-specification, no new number.

## Left

1. **Anonymous code link for reviewers** (optional). Without it, the data statement stands as written.
2. Voices only if the owner asks.
3. **Owner submits** through Elsevier's system: `latex/manuscript.pdf` (or `manuscript.tex` with
   `figures/figure1.pdf`), `latex/highlights.txt`, `latex/title-page.pdf`, `cover-letter.md` as text,
   `supplement/S1-S3`, and the declarations the form asks for.
