# S11 audit — §7, §8, Disclosure, Appendices pointer, all footnotes

Manuscript: `paper/paper-tecnico-nox-mem.md` (identical to scratchpad `base-audit.md`, `diff` empty).
Slice lines 1253–1493. Read for context: Abstract, §1.1–1.3, §5.1.1–5.1.9, §5.7, §6.3, §6.3.4, §6.7, §6.8.

## Method
- arXiv API (export.arxiv.org, fetched 2026-10-04) for all 51 arXiv IDs in the footnotes + 2404.06976 (Quati), 2503.07891 (Gemini Embedding), 2604.08256 (HyperMem). EverMemOS numbers checked in https://arxiv.org/html/2601.02163v2 (Table 1 LoCoMo 93.05; Table 2 LongMemEval 83.00).
- HF API `cross-encoder/ms-marco-MiniLM-L-6-v2`: model.safetensors 90,870,598 B; 22,714,113 params.
- Every "Used in / Cited in §X" pointer checked against the lines where the marker / name occurs.
- Artifacts read: `benchmark/latency-cost/results/RESULTS-PRODUCTION-SOTA.json`, `paper/measurement/out/censo-corpus-2026-09-09.json`, `paper/publication/results/E10-pain-ablation-hybrid-results.md`, `.../E10-pain-calibration-test.md`, `docs/INCIDENTS.md` (2026-06-02 entry), `specs/2026-05-24-A2-tier3-crypto-audit-RECON.md`, `docs/ROADMAP.md`, `staged/1.7a/edits/{db.ts,salience.ts}`, `staged/1.6/edits/api-server.ts`, `paper/CHANGELOG.md`, `paper/publication/supplement-*.md`, `../openclaw-vps/infra/CLAUDE.md`, `eval/q4-comparison/output/nox_mem.json`.
- No git command run (hard rule) — so "most commits record a Claude co-author" is NOT VERIFIABLE here.

## Verified OK (not reported)
- L3 corpus: 67,724 main + 3,610+3,090+1,894+1,422+1,054+426 = 79,220 across 7 DBs (censo-corpus-2026-09-09.json). OK.
- L5 smoke n=20 (nox_mem.json meta.n_queries=20). OK. 0.6380 matches §6.7.
- L7 latencies 2.5 ms / 529 ms (SOTA json kg_path_only p50 2.53, standard_hybrid p50 529.21). OK.
- L8 Δ=+0.0065, CI [−0.0143,+0.0338], n=31 (E10 hybrid results lines 309–319). OK.
- L6 Letta ~16 min/query consistent with §6.3 table.
- [^nogueira] ~180× (4e9 / 22.7e6 ≈ 176). OK.
- Author lists / IDs / venues of mem0, zep, letta (MemGPT), hipporag2, everos, memos, longhorizon, memsearcher (ACL 2026), selfevolsurvey (TMLR), memagent (ICLR 2026), beamretrieval, all classical refs: match arXiv.
- Quati (Bueno et al. 2024, 2404.06976): matches.
- HyperMem 92.73% LoCoMo LLM-judge: arXiv 2604.08256v2 abstract. EverMemOS 93.05 / 83.00: arXiv HTML tables.
- Internal footnotes: salience.ts DEFAULT_RETENTION_BY_TYPE (feedback 0, person 0, lesson 180 …), NOX_SALIENCE_MODE default "shadow" (line 34), api-server.ts:12 imports reflect, crystallize handlers ~253–273. OK.
- Disclosure reviewer families (GLM, Grok, Kimi, Codex) all appear in CHANGELOG.

## Defects found (detail in StructuredOutput)
1. F5 presents cross-encoder rerank as future work although §5.1.7 measured it (MiniLM-L-6-v2, −0.96 pp Overall, REJECT as default, shipped opt-in). Also Nogueira & Cho misattributed: their result is +27% relative MRR@10 vs previous SOTA on MS MARCO (abstract), baseline BM25 — not "+3–8% nDCG@10 over bi-encoder baselines".
2. §8 "consistently outperforms single-method retrieval across the evaluated corpora (§5.1, §6.3)": neither section contains a single-method baseline; only §4.2 (3 anecdotal queries) and §6.6 (capped n=20 smoke, FTS5@500 0.0466 vs hybrid 0.0918).
3. L5 attributes the 51–97% CPU-steal abort (batch 005 0/50 in 23 h) to "the first canonical attempt" of the cross-system run; docs/INCIDENTS.md 2026-06-02 and §5.5.8 attribute exactly these numbers to the Wave 2 capstone EverMemBench bench (dispatched 2026-05-31). CHANGELOG l.406: "o pod 06-15 era só anti-CPU-steal da VPS". No record of a Q4 canonical attempt being aborted. §8 "an infrastructure abort (§7.1 L5)" and §6.7 inherit it.
4. L3 host "4-vCPU / 8GB KVM4, as of 2026-09-09": infra CLAUDE.md l.28 says production = KVM2, 2 vCPU / 7.8 GB since 2026-08-23; SOTA json (2026-05-29) records vcpus 4, ram_total_mb 15,987. Neither host was 4 vCPU/8 GB. Also "KVM4" is a hosting-plan name, against the front matter's promise to omit hosting details. (Front matter and §1.3 carry the same "4 vCPU / 8 GB" — outside slice.)
5. L8: (a) 91.74% has no artifact (only grep hit: patch-plan quoting the paper); E10 artifacts say 89%, §5.1.2 says 90.67%. (b) the remedy "requires a corpus where pain spans [0.1,1.0]" contradicts E10-pain-calibration-test.md (wider spreads did not beat real; H1–H3 refuted; FTS recall 8.3%). (c) "See §5.7" points to the operations section. (d) cites a draft (`paper-draft-sec4-7.md`) instead of the results artifact.
6. [^nox-mem-rss] "6830 chunks live" on the production VPS: 6,830 is the Q4 eval corpus (audits/2026-05-24-nox-hybrid-full-corpus.md). SOTA json footprint.note_341mb_paper: the 341 MB was measured at ~62k chunks; 399 MB re-measured at 69,135.
7. F1: spec phase table says P5 = "`nox-mem audit verify` standalone CLI + offline mode"; SQLCipher wire-up is P1, migration P2, checkpoints P4. Paper describes P5 as the encrypted store + key management. Internal labels (A2 Tier 3 P5).
8. F2: ROADMAP l.241–242 defines F10 Phase C = telemetry + shadow visualization, Phase D = ops timeline + KG growth charts; l.21 says Phase C live, repo CLAUDE.md says Phase D delivered (#291). Paper redefines C/D as an undeployed shadow-eval gate. Also tension with abstract's "mandatory shadow phase".
9. F3 + §8 cross-refs "(G10c §5.1.4)", "(G10b §5.1.4)", "G10d … (§5.1.4)": §5.1.4 is now two sentences with none of these; S5.1.4 mentions G10d but G10b/G10c only by name. Artifacts: audits/2026-05-21-G10b-per-category-mutex-ablation.md, -G10c-per-style-mutex-ablation.md.
10. F4 "EverCore" undefined (internal doc maps it to arXiv 2601.02163 = EverMemOS) and HyperMem uncited.
11. F6 "(retention-based pruning)": no artifact; documented removals are cleanup ops. "~100k-vector threshold" unsourced.
12. F7 tokenizer: V5 migration (`staged/1.7a/edits/db.ts` migrateToV5) replaced `porter unicode61` with `unicode61 remove_diacritics 2`. Measured in sqlite3: porter unicode61 gives "decisao" (not "decisa"); current tokenizer gives "decisao"/"decisoes". (§2.2 l.246 and §4.1 l.429 also say porter — outside slice.)
13. §8 "validated by the active > shadow reversal": 0.6237 vs 0.6155, single n=100 run, no CI.
14. §8 success criterion "is met": in the canonical run only 3 systems produced numbers, so top-3 was guaranteed.
15. L6 "reported in §6.3.3" for EverOS and Zep — Zep is §6.3.4.
16. L2 product jargon ("BYOK partial autonomy"), unsourced "30–40 minutes", free-tier framing contradicts §5.7.2 per-query price.
17. [^memo] wrong title (arXiv: "MeMo: Memory as a Model", Quek et al.), wrong description (MeMo keeps LLM params unchanged, trains a separate memory model), wrong "abstract" usage. §1.4 l.43 has the same mischaracterization (outside slice).
18. [^qwen3embed] 5th author is Lin, not Xie.
19. [^geminiembed] dated 2024 (tech report arXiv:2503.07891, 2025-03-10) and "Cited in §3.3" (used at l.438, §4.1).
20. Section pointers wrong: [^rrf] §3.2 (used §1.5, §2.5); [^bm25] §3.1 (used §1.5, §2.2); [^sqlitevec] §3.1 (§1.5, §2.2); [^hnsw] §7.1 (not cited there; exact-search limit is in §7.2 F6); [^locomo] §5.5 (LoCoMo is §5.3); [^lightrag] §3.4 (LightRAG absent from §3.4); [^mirix] §2.4, [^treemem] §2.3, [^reasoningbank]/[^rmm] §3.4, [^goldfish] §6, [^minilm] §5.1.9 — none of these sections mention the work.
21. F5 "~66MB": HF file 90.9 MB.
22. Disclosure "records two such rounds": CHANGELOG has rounds in v1.0.0 (GLM+Codex+Kimi), v1.0.2 (Grok, Kimi), v1.0.3 (B) (Kimi, Codex), v1.0.3 (D) (Kimi k3 + Codex).
23. Appendices "anonymized supplementary material": supplement-operational-appendices.md l.113 names "TotoClaw Command Center"; the manuscript itself is signed. Same phrase recurs at l.538, 602, 653, 743, 793, 797 (outside slice).
24. [^hipporag2] "the manuscript's 32 arXiv-bearing footnotes": 51 today.

## Not verifiable
- Disclosure "Most commits that changed the manuscript source record a Claude model as co-author" (git forbidden in this task).
- L4 "two concurrent ingest calls … produce non-deterministic chunk counts" (no artifact found).
- F8 "< 20 words that the current chunker merges" (no artifact found).
- [^lightrag] "EMNLP 2025" venue (arXiv record has no journal_ref).
