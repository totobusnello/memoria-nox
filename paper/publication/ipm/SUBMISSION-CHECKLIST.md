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

- [x] **S4, anonymous code for reviewers** (owner's request, 27/11; scope decided the same day:
      a zip uploaded with S1–S3, no external service; anonymous.4open.science rejected because it needs
      the owner's GitHub login and would mirror the whole repository).
      `build_s4_code.py` -> `supplement/S4-code-and-evidence.zip` (406 files, 4.85 MB, deterministic):
      the engine at tag v3.4.0 (the first tag, nearest to the runs), `eval/q4-comparison` without
      `output*/`, `cache/` and `ambiente-congelado/`, `eval/evermembench`, the execution plan, the
      published evidence record (md5 pinned to the Zenodo copy) and `README-REVIEW.md` mapping each folder
      to its section. Text files only are edited; the engine's tests pass unchanged on the anonymized copy
      (638 pass, 0 fail, the same as the original tag); `verify_dataset.py` passes 135/135 on the
      anonymized evidence; no EverMemBench result file changes. Negative tests: a planted e-mail,
      handle and address fail the build and nothing is written; a different evidence zip is refused; a
      stale zip fails `--check`. Data availability and "Supplementary material" name S4; PDF rebuilt.
- [x] S4 text through avoid-ai-writing (owner, 27/11 20h45). Three sentences did not match the zip and
      were fixed: the README said "no other line is changed" while `package.json` loses four fields; the
      S4 list item omitted the EverMemBench harness; the data statement and the cover letter said "the
      harness" for two. Widened scan (project names, companies, fund names, e-mail domains, phones,
      Portuguese personal names): a test fixture in `brief.test.ts` carried a real contract line and
      vendor names, and a comment in `kg-llm.ts` described the author's work. Both now go through
      file-scoped rules, the names are in the gate, and the engine's tests still pass (638/0).

## Left

1. Not fixable by text, declared in the manuscript: a paired run that changes only the embedder, and
   intervals that account for the ten LoCoMo conversations.
2. **Owner submits** through Elsevier's system: `latex/manuscript.pdf` (or `manuscript.tex` with
   `figures/figure1.pdf`), `latex/highlights.txt`, `latex/title-page.pdf`, `cover-letter.md` as text,
   `supplement/S1-S3` and `supplement/S4-code-and-evidence.zip`, and the declarations the form asks for.
