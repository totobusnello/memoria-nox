# Number parity — paper v1.0.2 → v1.0.3 (after part E, 2026-10-04)

Base: copy of v1.0.2 at `scratchpad/v102/paper-tecnico-nox-mem.md`; intermediate: v1.0.3 parts A–D (backup taken before part E); now: `paper/paper-tecnico-nox-mem.md`.

## 1. Part E (audit) — every changed number, old → new, reason

| Where | Old | New | Reason / source |
|---|---|---|---|
| Abstract, §5.4, §5.8.6, headline | F_MH 3–7% (any backbone) vs 18.88% | 6.02% Gemini-3-flash (4–8% per batch) vs 10.84% MemOS same backbone; 3.21% gpt-4.1-mini vs 18.88% | S01/S12: 18.88% is the GPT-4.1-mini column; `RESULTS-BACKBONE-MATRIX.json` F_MH weighted 6.0241 / 3.2129; Table 4 arXiv:2602.01313v3 (auditor opened) |
| §5.1.6 table, §5.4 | F_MH gap −13 to −16 pp | −15.67 pp (gpt-4.1-mini); −4.82 pp (Gemini-3-flash) | S05/S01: 18.88−3.21; 6.02−10.84 |
| §5.1.6 table | F_MH ~3–5%, CI 'wide' | 3.21% (8/249), CI [−1.64, 8.04] | S05: `RESULTS-BACKBONE-MATRIX.json` gpt-4.1-mini F_MH |
| §5.1.6, §5.1.10, headline | CI [49.88, 53.49]; lower bound 49.88% | [49.87, 53.48]; 49.87% | S05: `RESULTS-PHASEH-v2-5BATCH.md` l.28/53 and JSON ci95 49.8736/53.4834 |
| §5.1.7 table | MA_C/P/U 'significant regression' | not significant / borderline; paired CIs ~[−11.0,+3.0], [−5.5,−0.1], [−8.8,+1.4] | S05: per-batch analysis files, paired t (df=4) |
| §5.1.7 text | −0.96 pp 'real across all 5 batches' | 4 of 5 batches; batch 005 +2.13 pp; CI ~[−3.4, +1.5] | S05: Phase D vs Phase G per batch |
| §5.1.7 F_MH row | CI [3.97, 9.69] presented as Δ CI | Phase G level 6.83%, CI [3.97, 9.69] contains 5.22% | S05: `RESULTS-PHASEG-5BATCH.md` |
| §5.1.7 verdict | latency +3.7 s p50 | p50 ~1.1 s → 4.8 s on batch 004 (+3.7 s) | S05/S08: `RESULTS-PHASEG.md` l.179 (1109 → 4783 ms) |
| §5.7.1 rerank row | +3,700 ms p50; p95/p99 '—'; 'no archived artifact' | +3,674 ms (1,109 → 4,783); p95 6,784; p99 8,696 | S08: `RESULTS-PHASEG.md` l.125/179 |
| §5.1.1 | +78.8% 'decomposed by sub-claims' | adds 0.5126 (hybrid, no boosts), +21.7% (Wave A stack), 0.4059 (tier only) | S05: archived handoff G5 V3 matrix |
| §5.1.2 | (no number) | +0.0082 nDCG@10 (0.6237 vs 0.6155) | S05 |
| §5.1.3 | 'majority of the headline' | 0.5126 → 0.6228 vs 0.5126 → 0.6237; A11 0.5646 | S05 |
| §5.2.1, §5.4, headline | EX(SA) 49.70%, Δ −8.92 pp | 49.80%, Δ −8.82 pp | S13: arXiv:2108.00573 Table 4 (An 49.8 dev) |
| §5.2.1, §5.4, headline | IRCoT 35.80%, Δ −22.82 pp | 36.50%, Δ −22.12 pp | S13: arXiv:2212.10509 Table 4 (GPT3 CoT reader 36.5) |
| §5.2.1 | Beam Retrieval dev EM/F1 77.37/79.31 | 77.37/89.77 (beam 1), 79.31/90.51 (beam 2) | S13: arXiv:2308.08973 Table 3 |
| §5.2.2, §5.4, headline | DPR+FiD 65–72%, −1.37 to −8.37 pp | row deleted (no source) | S13: 'hotpot' absent from both PDFs |
| §5.2.2 | BERT reader ~58%, −15+ pp | Clark & Gardner reimplementation 58.28%, −15.09 pp | S13: arXiv:1809.09600 |
| §5.3 | Mem0 'SOTA F1 66.88%' | 66.88% J (68.44% Mem0^g; full context 72.90%) | S13: arXiv:2504.19413v1 html |
| §5.3.2 | ranking table (Mem0 ~60, OpenAI ~55, LangGraph ~52, Zep 50.40, LangMem 50.21), 'rank-5' | withdrawn; J values Zep 65.99, LangMem 58.10, OpenAI 52.90 quoted as different metric | S13 |
| §5.5.1 table | F_MH '~ baseline'; Overall 'mixed'; cost '$0.0015/q + 2× LLM call' | F_MH 2.81%; F_SH 70.89 vs 80.97 (−10.08); MA 68.98 vs 73.34 (−4.36); Overall 53.13 (+1.45); 1+~3+1 calls, p95 3,688 ms | S07: `RESULTS-Q3-ITERC-POC.*` |
| §5.5.2 | (no MA figure) | MA −3.53 pp (88.42 → 84.89), Overall −0.58 pp | S07: `RESULTS-Q3-ITERB-POC-GEMINI.md` |
| §5.5.4, headline | '24% of the projection of +8.43' | 24% of the +8.43 pp gpt-4.1-mini sum (2.01/8.43) | S07 |
| §5.6 table | nDCG Wilson lower 0.9872 (as nDCG CI) | session_hit@10 Wilson 0.9872; n=297 scored | S07: `RESULTS-CROSSBENCH-2026-05-29.md` |
| §5.6 table | task accuracy n=201 (no exclusions stated) | n=201; 96 judge errors + 3 generator failures excluded | S07 |
| §5.6 table | abstention as category | _abs variant, n=23 | S07 |
| §5.7.1 text | Zep '<100 ms p50'; Mem0/MemOS '100–500 ms' | Zep '<100 ms' (no percentile); Mem0 '<200 ms'; MemOS none | S08: `RESULTS-PRODUCTION-SOTA.json` competitor_comparison |
| §5.7.1 text | (no figure) | long-query p50 1,017 vs 624 ms (~390 ms) | S08: latency-benchmark-summary.json / RESULTS-PRODUCTION-SOTA.json |
| §5.7.1 text | network overhead 'eliminated entirely' | localhost 1–3 ms; hybrid embedding call ~400–600 ms | S08 |
| §5.7.2 | Gemini $0.15/1M 'Feb-2026 increase from $0.13' | $0.15 listed now; artifact recorded $0.13 ($0.0000013/query) | S08 |
| §5.7.3 | 10× concurrent +15 MB (= ~414 MB) | 423 MB peak (+24 MB; delta field 15 MB) | S08/S12 |
| §5.7.3 | '$5/month VPS'; '>=3 services, 1.5–3 GB' | measured on 4-vCPU/16 GB; Table 2 estimates 2–3 services, ~0.8–1.5 GB | S08/S12 |
| §5.8.2, headline | overstatement 3–6× | 1.27–5.8× (1.3–5.8× in heading) | S05/S08 |
| §5.8.2 table | Lab Q1 #4 +6.78 pp / 2.4× | row deleted (paired batch-004 Δ = 0.00 pp) | S08 |
| §5.8.2 text | σ F_MH ~2.3, F_HL ~5, MA ~3; outlier +1.40σ to +1.70σ | Phase G 2.30/5.76/6.23/2.77/5.46; Phase H v2 MA_U 9.54; +1.4 SD (G, F_MH), +1.7 SD (H v2, Overall) | S08 |
| §5.8.5 | (no figure) | Table 4 GPT-4.1-mini FC 37.44%; MemOS +5.11, Zep +2.52, MemoBase −3.18, Mem0 −0.36 | S08: `INVESTIGATION.md` §11.1 |
| §6.3, §6.7, L5 | smoke nox-mem nDCG@10 0.6380, p50 8 ms | 0.4509 (rescored), p50 dropped | S09/S10: `output/nox_mem.json` via aggregate.py |
| §6.7 | smoke mem0 nDCG@10 0.8569, p50 273 ms | 0.1315, p50 263 ms | S10/S12: `output/mem0.json` |
| §6.3 tables | nox-mem cost $0 (local); Mem0 'subscription' | ~$0.0000015/query; OpenAI embed per query | S09 |
| §6.3.2 (e) | Mem0 store 6,830 at query time; 'dropped 4 of 6,822' | 6,826 rows (6,818 ids) at query time; 4 back-filled after | S09: `rc4-run.log`, chroma.sqlite3 created_at |
| §6.3.2 | 'a fourth' confound (task type) | 'a fifth' | S09/S12 |
| §6.4 table | single-hop 438 0.3969/0.3908 +0.006; multi-hop 454 0.5481/0.4699 +0.078; temporal 225 0.3940/0.2760 +0.118; open-domain 841 0.5991/0.5649 +0.034 | single-hop 997 0.5922/0.5607 +0.031; multi-hop 415 0.3641/0.3218 +0.042; temporal 454 0.5502/0.4570 +0.093; open-domain 92 0.2592/0.2351 +0.024 | S10: LoCoMo category map permuted; recomputed from `output/rc4/*.json` |
| §6.4 ablation | multi-hop 0.5561, open-domain 0.5792, single-hop 0.3924, temporal 0.3765 (vs 0.4699/0.5649/0.3908/0.2760) | temporal 0.5571/0.4570, single-hop 0.5773/0.5607, multi-hop 0.3515/0.3218, open-domain 0.2365/0.2351 | S10: `output/rc4-ablation/` |
| §6.6 | mem0@500 LoCoMo-only 0.1315; nox-mem '+40%' | 0.2631; nox-mem −30% | S10: `output/mem0.json` per-query |
| §6.8 Table 2, footnote | ~341 MB (2026-05-24, '6830 chunks live'); ~12× | ~399 MB (2026-05-29, 69,135 chunks); ~10×; 341 MB at ~62k chunks | S10/S11/S12: `RESULTS-PRODUCTION-SOTA.json` |
| §6.9 | 415 MB on 70.7k chunks (2026-06-15) | 399 MB on 69,135 (2026-05-29) | S10/S12: 415 has no artifact |
| §2.1 | nox-mem-api port 18800 | 18802 | S04 |
| §2.5 | answer p95 101.74 ms '42× under budget'; live 1.5–2.5 s | ~1.7 ms overhead at p95 (101.74 total, 100 ms mock); live dropped | S04 |
| §3.3 | keyword-overlap fallback 60% | 70% | S04: dedup.ts:85 |
| §4.1 | boosts 2.0×/1.5× (FTS), 1.5×/1.2× (semantic) | +1.0/+0.5 type, +0.5/+0.2 recency (additive) | S04: search.ts:39-42 |
| §7.1 L2 | re-vectorization 30–40 min | no timed run archived | S11 |
| §7.1 L3, §1.3, preamble | 4-vCPU / 8 GB | 4-vCPU / 16 GB (measurement host); 2-vCPU / ~8 GB (current) | S01/S11 |
| §7.1 L8 | 91.74% at default pain | 89% (E10 snapshot); 8.3% gold in BM25 pool | S11: `E10-pain-calibration-test.md` |
| §7.2 F4 | vendor 83% LME / 93% LoCoMo | EverMemOS 83.00 / 93.05; HyperMem 92.73 LoCoMo | S11: arXiv:2601.02163v2, 2604.08256v2 |
| §7.2 F5 | +3–8% nDCG@10 from cross-encoders; MiniLM ~66 MB | 27% relative MRR@10 (Nogueira & Cho); measured −0.96 pp; ~91 MB | S11: arXiv:1901.04085v5; HF API blobs |
| §7.2 F7 | 'decisão' → 'decisa' | indexed as 'decisao' / 'decisoes' | S11: fts5vocab run by auditor |
| Abstract, §8 | (no EverOS figure) | EverOS 0.646 vs 0.501 (0.6455 vs 0.5013) | S01/S12: `output-2026-09-10/_aggregate.json` |
| §5.1.1 | source_type boost effect (implicit) | inert: A10 = A8 = 0.6237 | S05 |

## 2. Mechanical census of numeric tokens (completeness check)

Regex over numeric tokens (with %, pp, ms, MB, × suffixes). Counts are occurrences; section numbers and dates are included, so not every entry is a result. Reasons for part A–D changes are in `paper/CHANGELOG.md` v1.0.3 (C) and (D).

### 2a. v1.0.2 → v1.0.3 parts A–D

Removed (45): `-10.54 pp`×1, `-16.72 pp`×1, `0.78 pp`×2, `05`×1, `09`×1, `1.06`×1, `1.6×`×1, `10`×1, `10 pp`×1, `10,`×2, `100 ms`×1, `11.7%`×1, `120`×1, `1536`×1, `17`×1, `17 pp`×1, `18 pp`×1, `18.94%`×1, `2`×5, `20.73 pp`×1, `24`×1, `25`×1, `25 pp`×2, `250`×1, `3.93 pp`×1, `30`×1, `31 pp`×1, `32.74 pp`×2, `4.04 pp`×1, `42 pp`×1, `5.4`×1, `5.6`×1, `5.7`×2, `529`×2, `6.8`×1, `7%`×1, `7.2`×5, `7.25 pp`×8, `83%`×1, `87%`×1, `9.39`×1, `9.6 pp`×2, `90.8%`×1, `940 ms`×2, `99.85%`×4

Added (134): `-0.06 pp`×4, `-0.74`×1, `-4.61 pp`×1, `-5.02 pp`×1, `0`×2, `0.25`×1, `0.4092`×2, `0.4749`×2, `0.48`×1, `0.5 pp`×1, `0.5852`×2, `0.6656`×2, `03`×1, `06`×5, `08`×1, `1.72 pp`×5, `10.44 pp`×2, `100,`×1, `11.60 pp`×3, `11.8%`×1, `12.12 pp`×3, `12.27`×1, `15`×6, `15.08 pp`×1, `15.21`×1, `16`×1, `16 pp`×1, `16.03 pp`×1, `16.72 pp`×2, `169,`×1, `17.66 pp`×2, `176,`×1, `18%`×1, `18.88%`×1, `181`×1, `19.30 pp`×1, `196`×1, `2%`×1, `2,400`×2, `2,733`×2, `2.2`×1, `2.20`×1, `2.41 pp`×1, `2.41%`×1, `2.5`×6, `2.95`×1, `2.95 pp`×1, `20`×2, `2026`×5, `21.22 pp`×1, `213,`×1, `221`×1, `24%`×1, `24.60 pp`×1, `247`×1, `248`×1, `249`×3, `26%`×1, `26.51%`×1, `268,`×1, `287`×1, `3`×4, `3,121`×1, `3.21%`×1, `3.5`×1, `3.76`×1, `300`×1, `31`×1, `349.8 ms`×2, `38.01 pp`×1, `388`×1, `4`×17, `4,`×3, `4.01 pp`×5, `4.02 pp`×3, `4.04`×1, `4.1`×13, `4.50 pp`×4, `4.60 pp`×1, `4.81 pp`×2, `40.91 pp`×1, `402,`×1, `42.55`×1, `42.55%`×4, `427,`×1, `5`×1, `5.1`×19, `5.8`×2, `50`×2, `500`×2, `51.65%`×2, `51.68%`×1, `515.6 ms`×2, `55.68%`×1, `59.21%`×2, `59.27`×1, `59.27%`×7, `6.02%`×2, `6.27`×1, `6.3`×2, `6.42 pp`×1, `6.7`×2, `6.83 pp`×2, `610`×1, `63.28%`×1, `63.77%`×3, `633`×1, `7`×1, `7.22%`×1, `7.23%`×1, `7.25%`×1, `7.36 pp`×1, `72.61%`×3, `73.34%`×1, `8`×2, `8%`×3, `8.02%`×5, `8.03%`×1, `8.74 pp`×1, `81.84%`×1, `83.40%`×1, `86.06%`×1, `86.70%`×2, `87.59%`×1, `89.20%`×1, `9.10 pp`×2, `9.6%`×1, `9.79`×1, `90.00%`×1, `90.67%`×1, `91.4%`×1, `97.99%`×1, `99.3%`×2, `99.86%`×4

### 2b. v1.0.3 parts A–D → part E (this audit)

Removed (123): `-1.37`×1, `-1.38`×1, `-13`×2, `-15`×1, `-16 pp`×2, `-22.82 pp`×1, `-8.37 pp`×1, `-8.92 pp`×1, `0`×3, `0.0015`×1, `0.006`×2, `0.034`×1, `0.0466`×1, `0.078`×1, `0.0918`×2, `0.1`×1, `0.118`×2, `0.1315`×2, `0.15`×2, `0.1835`×1, `0.2760`×2, `0.3765`×1, `0.3908`×2, `0.3924`×1, `0.3940`×1, `0.3969`×1, `0.4699`×2, `0.5481`×1, `0.5561`×1, `0.5649`×2, `0.5792`×1, `0.5991`×1, `0.6380`×1, `0.7`×2, `0.8569`×1, `0.9`×1, `1.0`×1, `1.2`×1, `1.40`×1, `1.70`×1, `100%`×1, `12×`×1, `14,`×1, `15%`×1, `180`×1, `189`×1, `190`×2, `2,000`×1, `2.3`×4, `2.3 pp`×1, `2.4×`×1, `2.81 pp`×1, `2004.04906`×1, `2007.01282`×1, `2018`×1, `2020`×1, `2021`×1, `2024,`×1, `2026,`×1, `22.82 pp`×1, `225`×1, `24`×7, `27,`×1, `273 ms`×1, `2×`×1, `3 pp`×1, `3,700 ms`×1, `3.1`×2, `30`×3, `35.80%`×3, `365`×1, `4.3`×1, `40`×1, `40%`×1, `414 MB`×1, `415 MB`×1, `42×`×1, `438`×1, `48`×1, `49.70`×1, `49.70%`×3, `49.88`×3, `49.88%`×1, `5`×7, `5 pp`×1, `5%`×1, `5,`×2, `5,882`×1, `50.21%`×1, `50.40%`×1, `500`×8, `500 ms`×1, `52%`×1, `53.49`×3, `55%`×1, `58%`×2, `6`×3, `6,822`×1, `6,830,`×1, `6.7`×1, `6.78 pp`×1, `60%`×2, `65`×3, `66.88%`×1, `66MB`×1, `6830`×3, `6×`×2, `7`×1, `7%`×6, `7,`×1, `7.1`×1, `70.7`×1, `72`×3, `72%`×3, `8 ms`×1, `8.92 pp`×2, `80`×1, `83%`×1, `841`×1, `9`×2, `91.74%`×1, `93%`×1, `97%`×1

Added (234): `-0.1`×1, `-0.36 pp`×1, `-0.96 pp`×1, `-1.38 pp`×1, `-1.64`×1, `-10.08 pp`×1, `-11.0`×1, `-15.09 pp`×1, `-15.67`×1, `-15.67 pp`×1, `-2 pp`×1, `-2.80`×1, `-22.12 pp`×1, `-3 pp`×2, `-3.18 pp`×1, `-3.4`×1, `-4.00 pp`×1, `-4.36 pp`×1, `-4.82 pp`×1, `-5.5`×1, `-8.8`×1, `-8.82 pp`×1, `0.0000013`×1, `0.0000015`×2, `0.0082`×1, `0.024`×2, `0.031`×1, `0.042`×1, `0.093`×2, `0.2`×3, `0.20`×1, `0.2351`×2, `0.2365`×1, `0.2592`×1, `0.2631`×1, `0.27`×1, `0.3218`×2, `0.3515`×1, `0.3641`×1, `0.40`×1, `0.4059`×1, `0.4509`×3, `0.4570`×2, `0.5`×4, `0.501`×1, `0.5013`×1, `0.5126`×5, `0.5502`×1, `0.5571`×1, `0.5607`×2, `0.5646`×1, `0.5773`×1, `0.58 pp`×1, `0.5922`×1, `0.6155`×1, `0.6228`×1, `0.6237`×4, `0.6455`×1, `0.646`×1, `0.8`×1, `005`×1, `02`×1, `04`×1, `05`×9, `06`×2, `07`×1, `08`×2, `09`×4, `1`×5, `1,`×1, `1,017`×1, `1,109`×1, `1,982`×1, `1.0000`×2, `1.1`×1, `1.27×`×1, `1.2×`×1, `1.3`×1, `1.3%`×1, `1.4`×3, `1.45 pp`×1, `1.5`×1, `1.5×`×2, `1.7 ms`×1, `10`×7, `10,`×2, `10.84%`×5, `100 ms`×1, `100,`×1, `10746`×1, `10761`×1, `14`×2, `15`×2, `16`×3, `1710.10723`×1, `18802`×1, `19`×1, `19,`×1, `2`×13, `2 pp`×1, `2,482`×4, `2.0×`×1, `2.13 pp`×1, `2.2`×3, `2.30 pp`×1, `2.5`×4, `2.52 pp`×1, `2.77 pp`×1, `2.81%`×1, `20`×1, `20,`×1, `200 ms`×1, `2017`×2, `2025, pp`×1, `2026`×21, `21`×2, `21.7%`×1, `22`×1, `22.12 pp`×1, `229`×1, `23`×1, `232`×1, `24 MB`×1, `249`×1, `2503.07891`×1, `2604.08256`×1, `263 ms`×1, `27`×2, `27%`×1, `28`×1, `29`×6, `29,`×3, `297`×1, `3`×1, `3 ms`×1, `3,674 ms`×1, `3,688 ms`×1, `3.0`×1, `3.2`×1, `3.21%`×4, `3.4`×4, `3.53 pp`×1, `3.7`×1, `31`×1, `36.50%`×3, `37.44%`×1, `390 ms`×1, `399 MB`×4, `4`×14, `4,783 ms`×1, `4.1`×16, `4.2`×1, `4.8`×1, `400`×1, `415`×1, `42`×1, `423 MB`×1, `49.0`×1, `49.80`×1, `49.80%`×3, `49.87`×3, `49.87%`×1, `5.1`×6, `5.11 pp`×1, `5.2`×1, `5.22%`×1, `5.3`×1, `5.46 pp`×1, `5.5`×4, `5.6`×2, `5.7`×9, `5.76 pp`×1, `5.8`×3, `5.8×`×2, `503`×1, `52.90`×1, `53.13%`×1, `53.48`×3, `56`×1, `57`×1, `58.10`×1, `58.28%`×4, `6%`×2, `6,`×1, `6,784 ms`×1, `6,818`×1, `6,826`×2, `6.02%`×5, `6.23 pp`×1, `6.3`×12, `6.5`×1, `6.6`×2, `6.8`×1, `6.83%`×1, `6.9`×2, `60,`×1, `600 ms`×1, `62`×3, `624 ms`×1, `65.99`×1, `66.88`×1, `67,724`×1, `68%`×1, `68.44`×1, `68.44%`×1, `68.98%`×1, `69,135`×5, `7.2`×4, `70`×2, `70%`×1, `70.89%`×1, `72.90`×1, `73.34%`×1, `78.8%`×3, `8,696 ms`×1, `8.04`×1, `8.3%`×1, `8.82 pp`×2, `80%`×1, `80.97%`×1, `83.00%`×1, `84.89%`×1, `88.42%`×1, `89%`×1, `89.77`×1, `9.54 pp`×1, `90.51`×1, `91 MB`×1, `92`×2, `93.05%`×1, `95%`×7, `96`×1, `99.7%`×1, `997`×1
