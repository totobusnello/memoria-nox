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
- [x] Voices, chosen by the owner (2026-11-27 18:24, «codex e grok»), challenge on the manuscript against
      S1: Codex (exit 0, 115 s) and Grok 4.7 (exit 0, 470 s, attach_bytes 253099 = manuscript + S1).
      Raw outputs in `voices/`. Every finding was checked against S1 before the text changed; all were
      sentences stronger than the report (the embedder named as the cause of the reversal, "five
      systems" without the limits, the 4 B re-ranker as a requirement, the full-context baseline outside
      Gemini-3-flash, documented stacks read as measured, MuSiQue across splits, the clustering of
      LoCoMo queries in ten conversations). Rewritten without new numbers; abstract still 249 words;
      provenance and PDF gates pass.

## Left

1. **Anonymous code for reviewers** (optional, but both voices flag that reviewers cannot reach
   the code while the links sit on the title page). Without it, the data statement stands as written.
   The owner asked for it on 27/11. The session ended at its context limit after scoping it and before
   building it. The scoping decided the following:
   - **Form:** an anonymized `S4-code.zip`, uploaded as supplementary material next to S1–S3, so reviewers
     receive it with no external service and no login.
   - **Rejected:** anonymous.4open.science. It needs the owner's GitHub login. It would also mirror this
     whole repository with term replacement, and identifying text sits in hundreds of files.
   - **Contents** (all three were checked on 27/11):
     - The tracked files of `eval/q4-comparison`, without `output*/`, `cache/` and `ambiente-congelado/`.
       The untracked cache reaches 1.7 GB. `adapters/nox_mem.py` is the Python hybrid pipeline that
       Section 4 measured.
     - The tracked files of `eval/evermembench`, the harness of Section 5. Together with the first item:
       99 MB, before the exclusions.
     - The engine, from the separate public repository at a release tag. It was 3.4 MB on 27/11, with tags
       up to v3.11.1. Pick the tag nearest to the runs.
     - A short `README-REVIEW.md` that maps each folder to the manuscript section it backs.
   - **Anonymization:**
     - Replace the author's name and handle, the repository name, host names and addresses, e-mails,
       ORCID and the author's Zenodo DOIs.
     - Re-scan until nothing matches. Scan a list that excludes `@`, because `nDCG@10` is a false hit.
     - Edit only text files. Never use `sed` on a binary or a `.db`.
   - **Then:**
     - Change the Data availability sentence to name S4.
     - Add S4 to "Supplementary material".
     - Rebuild the PDF and run the gates, through a PR.
     - Copy the zip to `~/Desktop/IPM-submissao/`.
2. Not fixable by text, declared in the manuscript: a paired run that changes only the embedder, and
   intervals that account for the ten LoCoMo conversations.
3. **Owner submits** through Elsevier's system: `latex/manuscript.pdf` (or `manuscript.tex` with
   `figures/figure1.pdf`), `latex/highlights.txt`, `latex/title-page.pdf`, `cover-letter.md` as text,
   `supplement/S1-S3`, and the declarations the form asks for.
