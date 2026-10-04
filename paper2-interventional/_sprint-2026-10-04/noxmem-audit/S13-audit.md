# S13 — External citations audit (paper-tecnico-nox-mem.md, 2026-10-04)

Scope: footnote bibliography (lines 1360–1491) + refs.bib + every number attributed to another system/paper.
Sources were downloaded with curl into the session scratchpad and searched as text (arXiv HTML/abs, ACL Anthology).

## Verified OK (no action)
- EverMemBench arXiv:2602.01313v3: title, 11 authors, v3 (11 Mar 2026). Table 4 MemOS: GPT-4.1-mini Overall 42.55, F_MH 18.88±4.8; Gemini-3-Flash Overall 59.27; Full Context Gemini-3-Flash 72.61±1.6. Table 5 oracle GPT-4.1-mini Multi 97.99. https://arxiv.org/html/2602.01313v3
- EverMemOS arXiv:2601.02163v2: authors match; Table 1 LoCoMo 93.05, Table 2 LongMemEval 83.00. https://arxiv.org/html/2601.02163
- Beam Retrieval arXiv:2308.08973: authors Zhang, Zhang, Zhang, Liu, Huang; Table 4 MuSiQue-Ans test An 69.2; Table 5 HotpotQA blind test Ans F1 85.04, FE2H 84.44. https://arxiv.org/html/2308.08973
- MemOS 2507.03724, Zep 2501.13956, LoCoMo 2402.17753, LongMemEval 2410.10813, HippoRAG 2 2502.14802, A-Mem 2502.12110, HaluMem 2511.03506: titles/first authors match arXiv abs metadata.
- EverMemBench population 2,400 vs our 2,733/3,121 is already disclosed (lines 645, 949).

## Defects
1. Mem0 66.88% is the LLM-as-a-Judge (J) overall score, not F1 (Mem0 arXiv:2504.19413v1, latency table: "Mem0 ... 66.88 ± 0.15%", "Mem0g ... 68.44 ± 0.17%"; Table 1 reports F1/B1/J per category only, no overall F1). Mem0g (68.44) is higher, so "Mem0 SOTA rank 1" is also wrong within that source. Only v1 exists.
2. §5.3.2 rank table: Zep 50.40 / LangMem 50.21 are labelled "Internal measurement" in the manuscript but eval/locomo/RESULTS-LOCOMO-SOTA-PUSH.md:151-153 and RESULTS-LOCOMO.md:106-107 attribute them to "Chhikara et al. 2025". grep of the Mem0 paper HTML: 50.40 -> 0 hits, 50.21 -> 0, 56.10 -> 0. Mem0 paper overall J: Zep 65.99, LangMem 58.10, OpenAI 52.90. "OpenAI-memory ~55% estimated" and "LangGraph ~52% estimated" have no source. The table compares nox-mem token F1 (51.85, RESULTS-LOCOMO-SOTA-PUSH.md:14) with a J score; "rank-5, above Zep/LangMem" is not supported.
3. MeMo arXiv:2605.15156v2 title is "MeMo: Memory as a Model" (abs v1 and v2), not "Towards Language Models with Associative Memory Mechanisms". Abstract: "encodes new knowledge into a dedicated memory model while keeping the LLM parameters unchanged" -> "folds reflections into model weights via continued pretraining" misdescribes it. Not in refs.bib (grep 2605.15156 -> 0).
4. IRCoT 35.80% does not appear in arXiv:2212.10509 (HTML search "35.8" -> 0 hits). IRCoT QA MuSiQue answer F1: GPT3 36.5±1.2 (CoT reader, the main-paper choice; Table 4/6), 36.0 Direct; Flan-T5-XXL 30.8. Table 1 (cited in RESULTS-MUSIQUE.md:72) has only MQ-2H 34.2/43.8 EM/F1. IRCoT evaluates on 500-question subsets sampled from dev. Delta becomes 58.62-36.5 = +22.12 pp.
5. EX(SA) 49.70%: MuSiQue arXiv:2108.00573 Table 4 (validation) gives EX(SA) on MuSiQue-Ans An 49.8 / Sp 79.2; Table 5 (test) gives 49.0 / 80.6. 49.70 is in neither (RESULTS-MUSIQUE.md:70 says "Table 5", 49.70/79.20 — Sp matches Table 4). Delta becomes 58.62-49.8 = +8.82 pp.
6. Beam Retrieval Table 3 (MuSiQue-Ans dev retrieval): 77.37 and 79.31 are the EM of beam size 1 and beam size 2; F1 is 89.77 / 90.51. "EM/F1 (77.37/79.31)" misreads the table.
7. "DPR+FiD reader range 65–72%" on HotpotQA dev is sourced to DPR (2004.04906) and FiD (2007.01282). Full-text search of both PDFs: "hotpot" -> 0 hits each. The band comes from an uncited hand table in eval/hotpotqa/RESULTS-HOTPOTQA.md:55.
8. HotpotQA original baseline is not a BERT reader: arXiv:1809.09600 §5.1 "we reimplemented the architecture described in Clark and Gardner (2017) as our baseline model"; distractor dev answer F1 58.28 (test 58.99).
9. §1.4 says only Mem0 and agentmemory reached a same-corpus comparison; the abstract and §6.3.3–§6.3.4 say EverOS and Zep did too, and agentmemory is not a Table 1 column.
10. "roughly three families" followed by (i)–(iv).
11. LightRAG is in Findings of EMNLP 2025 (aclanthology 2025.findings-emnlp.568), not the main EMNLP 2025 proceedings.
12. LoCoMo footnote "used in §5.5 and §6": LoCoMo is §5.3; §5.5 (Q3 orchestration) never mentions LoCoMo.
13. "(Table 5: GPT-4.1-mini 2.41% → 97.99%)": 2.41 is Table 4 (GPT-4.1-mini Full Context, Multi 2.41±1.8); only 97.99 is Table 5. The source's own §text conflates them too.
14. refs.bib: hu_2026 and hu_2026_evermemos are identical entries (2601.02163).

## Not verifiable here
- FE2H leaderboard listing at hotpotqa.github.io (value 84.44 confirmed via Beam Table 5).
- "Mem0 (replication) ~60%" / "Range from internal estimate": no artifact found.
