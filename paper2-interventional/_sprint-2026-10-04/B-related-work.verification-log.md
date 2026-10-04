# Verification log — `B-related-work.bib` / `B-related-work.md`

Sprint 2026-10-04, task: Paper B related work (working-list item 7). All checks run 2026-10-03/04 (BRT) by the
drafting agent. Nothing here was written from memory: each row names the URL or API call that returned the
metadata. **Reading depth** is `FULL` (PDF fetched, relevant sections read, strings counted), `PART` (PDF/HTML
fetched, key sections and limitations read, strings counted), `ABS` (abstract + metadata only), `META`
(bibliographic record only: title/authors/venue/pages, no abstract seen).

Resolution methods used:

- **arXiv API** `https://export.arxiv.org/api/query?id_list=<id>` → title, authors, v1/updated dates, abstract.
- **Crossref API** `https://api.crossref.org/works/<doi>` → title, subtitle, authors, venue, volume/issue/pages, dates.
- **Publisher / archive pages** opened with WebFetch or Firecrawl where the table says so.
- **PDF + `pdftotext`** for the full-text rows; sha256 prefixes below are of the PDFs fetched.

A reference was dropped rather than kept when it could not be resolved. Dropped on purpose: the existing
`paper/publication/refs.bib` entries for Mem0, MemGPT, A-Mem, HippoRAG, etc. (not needed here, and not
re-verified); the `munafosystematic2017`, `kohavi2020trustworthy` and `chapelle2012interleaved` entries of that
file were **re-resolved from scratch** (Crossref) rather than copied.

## 1. Agent-memory literature (rows i and iv)

| Key | URL / call opened | What was checked | Depth |
|---|---|---|---|
| huang2026survey | `openreview.net/forum?id=XycbogUAeJ` (Firecrawl, 200); `arxiv.org/pdf/2602.06052v4` (sha256 `497e9549…` = the pin recorded in `RELATED-WORK.md`); arXiv API | OpenReview: "Accepted by TMLR", "Survey Certification", "Published: 04 Aug 2026", 60 authors (OpenReview shows 20 and "40 additional authors not shown"). PDF header "Published in TMLR (07/2026)", "arXiv:2602.06052v4 [cs.CL] 4 Aug 2026". §9.6 read in full and quoted; counts: `random*` 0, `pre-regist*` 0, `A/B` 1 (user-simulator paragraph), `interventional` 1 (same paragraph), `counterfactual` 1, `causal` 4 | FULL (§9.6 + counts) |
| omri2026agentmemory | arXiv API; `arxiv.org/pdf/2606.06448v2` (sha256 `aac48e11…`) | Title/authors (9, Stanford/KU Leuven/MIT), v1 2026-06-04, v2 2026-09-22. Abstract: "phase-aware profiling harness attributing cost to construction, retrieval, and generation", "ten representative systems across two benchmark suites". §2.1 quote "Existing benchmarks evaluate these systems purely on downstream accuracy"; §3.3 harness text (token volume, call structure, latency, utilization, energy); Rec. 9; benchmarks named: LongMemEval_S_*, EventQA. Counts `random` 0, `A/B` 0, `counterfactual` 0, `causal` 0, `pre-regist*` 0, `bootstrap/confidence interval` 0 | PART |
| zhang2024memorysurvey | arXiv API; PDF `s_2404.13501` (sha256 `aae2f953…`) | title/authors/date; counts `randomi[sz]ed` 0, `A/B` 0, `pre-?regist` 0, `counterfactual` 0, `causal` 0 (plain `pdftotext`, hyphenation not stitched ⇒ lower bounds) | ABS + counts |
| hu2025memoryage | arXiv API; PDF (sha256 `10de3c05…`) | same; `randomi[sz]ed` 0, `A/B` 0, `pre-?regist` 0, `counterfactual` 1, `causal` 7 | ABS + counts |
| du2026memoryautonomous | arXiv API; PDF (sha256 `ca7d6c5d…`) | same; `randomi[sz]ed` 0, `A/B` 0, `pre-?regist` 0, `counterfactual` 2, `causal` 10 | ABS + counts |
| he2026memoryarena | arXiv API; `arxiv.org/pdf/2602.16313v2` (sha256 `7478c3b9…`) | v1 2026-02-18, **v2 2026-09-17**, 14 authors. v2 text: `A/B` 0, `counterfactual` 0, `pre-regist*` 0, `bootstrap` 0, `random` 4 lines (VC-bound, preference selection; none about memory-policy assignment). The full read behind `RELATED-WORK.md` §4 is of an earlier version (2026-08-15) — **not redone** | ABS + counts (v2); FULL (earlier version, not by this sprint) |
| wei2025evomemory | arXiv API; `arxiv.org/pdf/2511.20857v2` (sha256 `ab99bebb…`) | v1 2025-11-25, v2 2026-05-18. Verbatim re-found: "we maintain a unified task sequence ordering within each dataset" (§A.2) and §4.2.3 "highlight the importance of task sequence design for fair evaluation and effective learning". Table 2: ExpRAG avg success 0.57 (Easy→Hard) vs 0.69 (Hard→Easy). `random`, `A/B`, `counterfactual`, `causal`, `pre-regist*` all 0 | PART |
| zheng2025lifelongagentbench | arXiv API | title, 8 authors, v1 2025-05-17 | ABS |
| zou2026interruptbench | arXiv API | title, authors (19; first Henry Peng Zou, last Philip S. Yu), 2026-04-01 | ABS |
| hu2025memoryagentbench | arXiv API (v4 2026-06-28); a proceedings URL (`proceedings.iclr.cc/…2026…`) appeared in a search result but was **not opened** ⇒ no venue asserted | title/authors/dates/abstract | ABS |
| maharana2024locomo | Crossref `10.18653/v1/2024.acl-long.747`; arXiv API 2402.17753 | ACL 2024 long papers, pp. 13851–13870 | META |
| wu2025longmemeval | arXiv API 2410.10813 | title/authors/dates | ABS |
| xiong2025memorymanagement | arXiv API 2505.16067 | title, 8 authors, abstract ("controlled experiments across four distinct agents" from search excerpt; "through controlled experiments" in abstract) | ABS |
| feng2026memorytransplants | `openreview.net/forum?id=AIJsjIqfsp` (Firecrawl 200) and `openreview.net/attachment?id=AIJsjIqfsp&name=pdf` (Firecrawl markdown, 50 kB) | Venue "ICLR 2026 Workshop MemAgents", published 03 Mar 2026, 3 authors; abstract (2×2 factorial, 7 conditions, 5 systems, "six pre-registered validation gates"); body: "pre-registered experimental design … six validation gates, and four negative control types", "3 seeds", "360+ evaluation runs", negative controls "(random retrieval, placebo, write-only, frozen-store MU)" reported in supplementary analysis. No OSF/registry link or timestamp found in the text ⇒ the registration is the authors' statement, not an independently dated record | PART |
| behnam2026cmp | arXiv API; `arxiv.org/pdf/2610.02070` (sha256 `5b298624…`) | v1 **2026-10-01**, 2 authors. Read: abstract, §1, §2 Theorem 1 (quote verified), §3 design (balanced exposure, known propensities, self-normalised IPW), §4 setup (LongMemEval 51 multi-evidence items; LoCoMo; HotpotQA/MuSiQue; Mem0 v2.0.18 replay), appendix F.1, Limitations (exposure cost −0.026 F1; pool built with knowledge of required memories). `pre-regist*` 0; `A/B` none relevant | PART |
| srivastava2026cmi | arXiv API 2605.17641; cross-checked against the reference list of CMP | title, single author, 2026-05-17, abstract (Causal-LoCoMo; no-memory/with-memory/perturbed-memory) ; "87 filtered examples" from a search excerpt of the HTML | ABS |
| sun2026experienceserving | arXiv API 2606.11806 + search excerpt of HTML | title, 3 authors, 2026-06-10; "no-experience baselines, random experience controls, global prompt injection, retrieval-based selective injection"; production moderation workload; "risk-focused moderation benchmark constructed from human-labeled production data" | ABS + excerpt |
| tablan2026learningonthejob | arXiv API 2607.22157; WebFetch of `arxiv.org/abs/2607.22157` | title, 3 authors, 2026-07-24; τ-bench banking; "static-RAG control"; paired contrasts with CIs (search excerpt) | ABS + excerpt |
| frauen2026causalmethods | arXiv API 2605.25998; Crossref `10.1145/3770855.3818647` | KDD 2026 V.2 pp. 13170–13177, 13 authors; abstract says causal methods are "potentially underutilized" | ABS |
| peng2023copilot | arXiv API 2302.06590 | title, 4 authors, abstract (controlled experiment, 55.8% faster) | ABS |
| becker2025metr | arXiv API 2507.09089 | title, 4 authors; abstract: RCT, 16 developers, 246 tasks, forecast −24%, observed +19% completion time | ABS |
| bean2026llmmedical | Crossref `10.1038/s41591-025-04074-y` | Nat Med 32(2):609–615, 2026; title contains "randomized preregistered study" | META |

## 2. Online experimentation, interference, switchback, inference (row ii)

| Key | URL / call opened | What was checked | Depth |
|---|---|---|---|
| kohavi2020trustworthy | Crossref `10.1017/9781108653985` (title, subtitle "A Practical Guide to A/B Testing", CUP, 2020-03-13); `doi.org` → Cambridge **HTTP 429**; Cambridge page **HTTP 429** | record only; table of contents **not inspected**; no ISBN asserted | META |
| kohavi2009controlled | Crossref `10.1007/s10618-008-0114-1` | DMKD 18(1):140–181; online 2008-07-30, print Feb 2009 ⇒ cited as 2009 | META |
| kohavi2012puzzling | Crossref `10.1145/2339530.2339653` | KDD'12, pp. 786–794, 6 authors | META |
| deng2013cuped | Crossref `10.1145/2433396.2433413` | WSDM'13, pp. 123–132 | META |
| fabijan2019srm | Crossref `10.1145/3292500.3330722`; Semantic Scholar abstract | KDD'19 pp. 2156–2164; abstract defines SRM ("the observed sample ratio … is different from the expected") as an indicator of data-quality issues | ABS |
| hofmann2016online | Crossref `10.1561/1500000051`; PDF excerpt via search (microsoft.com) | FnTIR 10(1):1–117; the "one to two orders of magnitude of improved sensitivity" sentence read in an excerpt | META + excerpt |
| radlinski2008clickthrough | Crossref `10.1145/1458082.1458092`; Semantic Scholar abstract | CIKM'08 pp. 43–52; abstract: paired comparison tests on interleaved rankings more accurate and sensitive than absolute metrics | ABS |
| chapelle2012interleaved | Crossref `10.1145/2094072.2094078` | TOIS 30(1), pp. 1–41 (article 6) | META |
| blake2014marketplace | Crossref `10.1145/2600057.2602837`; Semantic Scholar (subtitle) | EC'14 pp. 567–582 | META |
| johari2022twosided | Crossref `10.1287/mnsc.2021.4247` | Mgmt Sci 68(10):7069–7089 | META |
| saveski2017network | Crossref `10.1145/3097983.3098192` | KDD'17 pp. 1027–1035; subtitle "Randomizing Over Randomized Experiments" | META |
| aronow2017interference | Crossref `10.1214/16-AOAS1005`; Semantic Scholar abstract | AoAS 11(4); abstract: randomisation-based framework for effects under interference, IPW estimators | ABS |
| bojinov2023switchback | Crossref `10.1287/mnsc.2022.4583`; WebFetch `arxiv.org/abs/2009.00148` (v4 2025-09-17) | Mgmt Sci 69(7):3759–3777; abstract: carryover of order m, minimax design, randomisation p-values, finite-population CLT, misspecified order, data-driven identification | ABS |
| hu2022switchback | arXiv API 2209.00197 (v5 2026-09-21); Crossref title search returned no match | title/authors/abstract opening ("overcome cross-unit spillover effects; however, they are vulnerab…"); journal publication **not established** | ABS |
| basse2023minimax | Crossref title search → `10.1093/biomet/asac024` (a first guessed DOI resolved to an unrelated paper and was discarded); Semantic Scholar abstract; arXiv API 1908.03531 | Biometrika 110:155–168, online 2022-05-05; abstract: habituation (effect attenuates after repeated exposure), minimax designs | ABS |
| bojinov2019timeseries | Crossref `10.1080/01621459.2018.1527225`; Semantic Scholar abstract | JASA 114(528):1665–1682; abstract: exact randomisation p-values, single time series | ABS |
| lewis2015unfavorable | Crossref `10.1093/qje/qjv023` (abstract returned) | QJE 130(4):1941–1973; quotes "median confidence interval … over 100 percentage points wide" and "more than 10 million person-weeks" verified in the abstract | ABS |
| gordon2019comparison | Crossref `10.1287/mksc.2018.1135`; Semantic Scholar one-sentence summary | Marketing Sci 38(2):193–225; "Observational methods often fail to accurately recover the treatment effects generated from randomized advertising experiments on Facebook" (summary only; publisher page unavailable) | META + summary |
| johnson2017ghost | Crossref `10.1509/jmr.15.0297`; NBER conference draft `conference.nber.org/confer/2016/EoDs16/Johnson_Lewis_Nubbemeyer.pdf` (search result, abstract + intro read); SAGE page **HTTP 403** | JMR 54(6):867–884. Method description ("identifying the control-group counterparts of the exposed consumers in a randomized experiment"; simulated second auction logs ghost impressions) is from the 2016 **draft**, not the published version | ABS (draft) |
| garcin2014offline | Crossref `10.1145/2645710.2645745` | RecSys'14 pp. 169–176; abstract not retrieved ⇒ cited for topic only | META |
| rossetti2016contrasting | Crossref `10.1145/2959100.2959176` | RecSys'16 pp. 31–34; abstract not retrieved ⇒ cited for topic only | META |
| li2011unbiased | Crossref `10.1145/1935826.1935878`; Semantic Scholar abstract | WSDM'11 pp. 297–306; abstract introduces a replay methodology | ABS |
| cameron2008bootstrap | Crossref `10.1162/rest.90.3.414`; text of the paper via a search excerpt | REStat 90(3):414–427 | META + excerpt |
| cameron2015practitioner | Crossref `10.3368/jhr.50.2.317`; PDF excerpt (cameron.econ.ucdavis.edu) via search | JHR 50(2):317–372; "with less than ten clusters the wild cluster bootstrap should use the six-point version of Webb (2013)" read in the excerpt | META + excerpt |
| webb2014reworking | Firecrawl scrape of `qed.econ.queensu.ca/working_papers/papers/qed_wp_1315.pdf` (HTTPS fetch by WebFetch failed on a certificate error) | QED Working Paper No. 1315, Nov 2014, single author Matthew D. Webb; abstract: "these bootstrap procedures perform poorly with fewer than eleven clusters", "6-point bootstrap weight distribution improves the reliability of inference" | ABS |
| imbens2015causal | Crossref `10.1017/CBO9781139025751` | title, subtitle "An Introduction", CUP, 2015-04-06; book not opened | META |

## 3. Pre-registration, power, null results (row iii)

| Key | URL / call opened | What was checked | Depth |
|---|---|---|---|
| bertinetto2020prereg | `neurips.cc/virtual/2020/workshop/16158` (WebFetch) | workshop title, 5 organizers (Bertinetto, Henriques, Albanie, Paganini, Varol), "follows a successful small-scale trial of pre-registration in computer vision" | ABS |
| albanie2022prereg | `proceedings.mlr.press/v181/` and `…/v181/albanie22a.html`; PDF `…/albanie22a/albanie22a.pdf` (sha256 `bffa29f2…`) | PMLR vol. 181, "NeurIPS 2021 Workshop on Pre-registration in Machine Learning", editors Albanie, Henriques, Bertinetto, Hernández-García, Doughty, Varol; Preface text: 22 proposals, 10 accepted (45%), 3 results papers, all 3 judged to have followed protocol | FULL (preface) |
| vanmiltenburg2021prereg | `aclanthology.org/2021.naacl-main.51/`; `doi.org` → 200 | title, 3 authors, NAACL 2021, DOI | ABS |
| sogaard2023twosided | `aclanthology.org/2023.eacl-main.6/`; PDF (sha256 `083e42bf…`); `doi.org` → 200 | title, 3 authors (Søgaard, Hershcovich, de Lhoneux), EACL 2023; abstract listing pros and cons; footnote verified: workshops "seemingly did not lead to publications or a change in practice yet" | PART |
| hofman2023prereg | arXiv API 2311.18807 | title, 5 authors, 2023-11-30 | ABS |
| vaccaro2026prereg | arXiv API 2606.11217; PDF (sha256 `24fef10f…`) | single author; PDF stamp "arXiv:2606.11217v1 [cs.CY] 3 May 2026" (identifier range and date disagree — recorded as given). Table 1 (Appendix A) "Memory settings: Enabling or disabling conversation memory, adjusting context window usage, or clearing state between trials based on which configuration yields favorable results" verified | PART |
| wilder2025evaluation | arXiv API 2510.18238; the preregistration passage read in a search excerpt of the PDF | title, 2 authors, 2025-10-21; "We propose that machine learning publication venues should require that authors declare whether field experiments and analyses were preregistered or not" | ABS + excerpt |
| bauer2023dagstuhl | arXiv API 2305.01509; PDF (sha256 `60967513…`); `doi.org/10.4230/DagRep.13.1.68` → 200; DataCite record | Dagstuhl Reports 13(1):68–154, 2023; text verified: "We propose to introduce a results-blind reviewing process…"; "embrace a results-blind reviewing approach, we also recommend that they consider piloting a conference track or article type in which the study protocol undergoes peer review" | PART |
| nosek2018prereg | Crossref `10.1073/pnas.1708274114`; Semantic Scholar abstract | PNAS 115(11):2600–2606 | ABS |
| munafo2017manifesto | Crossref `10.1038/s41562-016-0021` | Nat Hum Behav 1(1):0021 (same as the existing `refs.bib` entry; re-resolved) | META |
| chambers2022registeredreports | Crossref `10.1038/s41562-021-01193-7`; Semantic Scholar abstract | Nat Hum Behav 6(1):29–42, online 2021 | ABS |
| kaplan2015nullnhlbi | Crossref `10.1371/journal.pone.0132382`; WebFetch of the PLOS article page | PLOS ONE 10(8):e0132382; "17 of 30" (57%) before 2000 vs "2 of 25" (8%) after; registration coincides | ABS |
| ioannidis2005false | Crossref; Europe PMC abstract | PLoS Med 2(8):e124 | ABS |
| button2013power | Crossref; Europe PMC abstract | Nat Rev Neurosci 14(5):365–376; quote "low power also reduces the likelihood that a statistically significant result reflects a true effect" verified | ABS |
| gelman2014beyond | Crossref; Europe PMC abstract | Perspect Psychol Sci 9(6):641–651; quote "In noisy, small-sample settings, statistically significant results can often be misleading" verified | ABS |
| hoenig2001abuse | Crossref `10.1198/000313001300339897`; excerpt via search (UCF-hosted PDF + OpenAIRE record) | Am Stat 55(1):19–24; full title "The Abuse of Power: The Pervasive Fallacy of Power Calculations for Data Analysis"; abstract: power calculations "valuable in planning", post-experiment ones "fundamentally flawed"; "observed power is determined completely by the p value" | ABS + excerpt |
| urbano2019significance | Crossref `10.1145/3331184.3331259`; Semantic Scholar abstract | SIGIR'19 pp. 505–514; subtitle "An Empirical Analysis of Type I, Type II and Type III Errors"; abstract on tests (t, Wilcoxon, bootstrap, permutation) in IR | ABS |

## 4. Searches run (so that "not found" can be read as "searched", not "not looked")

All via Perplexity `perplexity_search` or Firecrawl `firecrawl_search`, 2026-10-03/04; each returned ≤10 results.

1. `randomized controlled trial A/B test of memory feature in deployed LLM agent production causal effect` → Xiong et al.; practitioner posts; no live-memory trial.
2. `preregistration in machine learning research registered reports NeurIPS pre-registration experiment` → NeurIPS 2020/2021 workshops, van Miltenburg, Søgaard, Hofman, Wilder–Zhou.
3. `pre-registration information retrieval experiments registered reports ECIR SIGIR` → Dagstuhl report (results-blind review); **no IR registered-report track found**.
4. `online A/B testing LLM agents memory randomized experiment agentic systems evaluation in production arXiv` → AgentA/B (simulated users; not memory), industrial RAG A/B reports; no memory-policy trial.
5. `field experiment randomized memory personalization LLM assistant users randomly assigned memory enabled vs disabled` → observational/benchmark studies of memory on/off; no field RCT of memory.
6. `switchback experiments carryover effects time-based randomization design and analysis` → Bojinov et al., Hu–Wager, Basse et al., empirical-Bayes switchback design (SSRN), carryover detection (OpenReview, not cited), spectral designs (arXiv 2609.13698, not cited).
7. `interleaving online evaluation information retrieval survey Hofmann Li Radlinski` → Hofmann et al., Radlinski/Craswell, Chapelle et al.
8. `bootstrap inference few clusters wild cluster bootstrap Cameron Gelbach Miller undercoverage` → CGM, MacKinnon–Webb, Cameron–Miller, Webb.
9. `"randomized" experiment live deployment memory retrieval augmented agents production traffic causal effect of memory policy` (Firecrawl, research category) → **Behnam & Wang (CMP)**, Sun et al.
10. `online A/B test retrieval-augmented generation production deployment randomized user-level assignment …` → industrial RAG papers reporting A/B tests of whole systems (not memory policies; not cited).
11. `non-stationary agent evaluation paired design memory ablation statistical power number of seeds …` → seed-pairing and benchmark-variance material (not cited; not about live traffic).
12. `causal effect of memory on LLM agent decisions interventional evaluation counterfactual memory ablation deployed agent 2026` → CMI, CICL, MemAudit, counterfactual memory attacks, spurious-correlation benchmark (the latter four not cited: security / benchmark settings).
13. `memory agents evaluation "pre-registered" OR "preregistered" randomized trial LLM agent memory` → Feng et al. (memory transplants), Vaccaro, a poisoning-detection paper with a preregistered follow-up (arXiv 2606.30566; security, not cited), clinical-AI reviews.
14. Targeted lookups for individual bibliographic records (Ghost Ads, Hoenig–Heisey, Hofmann/Radlinski excerpts).

**Not cited although seen** (so a reviewer's "did you see X" has an answer): Agent A/B (2504.09723; LLM agents simulating
A/B tests, not about memory), PILOT (2608.18637; agentic experiment manager on Taobao, not about memory evaluation),
memory-poisoning attack/audit papers (MemAudit, counterfactual memory attacks), CICL (decision-aware memory cards), industrial RAG A/B reports, and `2512.24145` (seed pairing). A
paper titled *"Forensic trajectory signatures for agent memory poisoning detection"* (2606.30566) has a
preregistered follow-up but is a security study.

## 5. Known gaps (what was NOT checked)

- **No book was opened** (Kohavi et al. 2020, Imbens–Rubin 2015). Cambridge returned HTTP 429.
- **Paywalled publisher pages** (SAGE, INFORMS, T&F, ACM) returned 403 or redirected; abstracts for those came from Crossref,
  Semantic Scholar or Europe PMC, or are absent (Chapelle, Deng, Kohavi 2009/2012, Blake–Coey, Johari, Garcin, Rossetti):
  those are cited for the topic their titles carry, not for a finding.
- **OpenReview API** (`api2.openreview.net`) returned a 403 challenge to scripted access; the two OpenReview records
  used were obtained through Firecrawl.
- **MemoryArena v2** (17 Sep 2026) not re-read in full (see main text, open items).
- **Venue/publication status** not established for: Omri et al., Zhang 2024, Hu 2025 (both), Du 2026, Zheng 2025, Zou 2026,
  Wu 2025, Xiong 2025, Srivastava, Sun, Tablan, Behnam–Wang, Hu–Wager, Peng, Becker, Hofman, Vaccaro, Wilder–Zhou. They are cited as arXiv
  preprints, which is what was verified.
- **Page-level locators** (section numbers inside cited works) are given only for: survey §9.6; Evo-Memory §4.2.3, §A.2,
  Table 2; CMP Theorem 1 and the Limitations appendix (J); Vaccaro Table 1.
- Counts of strings are over `pdftotext` output; for the survey the extraction matches the method of
  `measurement/survey-string-count.py` only in spirit (the 2026-08-28 recompute stitched hyphenation; this sprint's
  counts of the three other surveys did not), so the three-survey counts are lower bounds.
