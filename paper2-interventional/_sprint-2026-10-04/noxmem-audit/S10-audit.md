# S10 audit — §6.4 to §6.9 (paper-tecnico-nox-mem.md lines 1133–1251)

Date: 2026-10-04. No git, no Zenodo, no contact. All numbers recomputed with
`eval/q4-comparison/aggregate.py::ndcg_at_k` (reproduces the published rc4 per-category cells exactly).

## Verified OK
- §6.4 cells (old mapping) == `output/rc4/_aggregate.md` (0.4370/0.2955, 0.5481/0.4699, 0.5991/0.5649, 0.3969/0.3908, 0.3940/0.2760; n sums to 2,482).
- Ablation cells == `output/rc4-ablation/_aggregate.md` (0.4573, 0.5561, 0.5792, 0.3924, 0.3765). Ablation per-dataset margins: LoCoMo 0.4920-0.4407=+0.051, LME 0.5215-0.4061=+0.115 → "at least +0.05" OK.
- §6.6 latency bullet numbers == §5.7.1 table (2.5/6.1; 529/698; ~940/~2,342).
- §6.9 orders of magnitude: 960,000 ms / 529 = 1,815 (10^3.26); /940 = 1,021 (10^3.01); /2.5 = 384,000 (10^5.58). OK.
- §6.8 ~12×: 4,096/341 = 12.0 (but see M6/M7 on which RSS).
- BEIR arXiv:2104.08663, MTEB arXiv:2210.07316 — IDs correct (known), not re-opened.

## HIGH
H1. LoCoMo native category → bucket mapping is permuted (lib/category_labeler.py; docs/rc2-per-category-mapping.md §2.1).
 Evidence from cache/raw/locomo10.json:
   cat 1 n=282: 277/282 have >=2 evidence ids  → multi-hop (mapped single-hop)
   cat 2 n=321: 246/321 start with "When"      → temporal (mapped multi-hop); e.g. "When did Caroline go to the LGBTQ support group?" labelled multi-hop in output/rc4/nox_mem.json
   cat 3 n=96 : 37/96 contain would/likely/might, 0 "When" → open-domain/commonsense (mapped temporal)
   cat 4 n=841: 46/841 multi-evidence          → single-hop (mapped open-domain)
 Recomputed with corrected LoCoMo map (LME map unchanged):
   rc4      nox / mem0: single-hop 997 0.5922/0.5607; multi-hop 415 0.3641/0.3218; temporal 454 0.5502/0.4570; adversarial 524 0.4370/0.2955; open-domain 92 0.2592/0.2351
   ablation nox / mem0: single-hop 0.5773/0.5607; multi-hop 0.3515/0.3218; temporal 0.5571/0.4570; adversarial 0.4573/0.2955; open-domain 0.2365/0.2351
 nox-mem still leads all five; narrowest becomes open-domain (+0.024, n=92), not single-hop.
H2. §6.6 "LoCoMo-only" row: mem0@500 LoCoMo-only is NOT 0.1315. output/mem0.json (2026-05-23, n=20, 500 cap): LoCoMo 10 q nDCG = [0,0,1,0,0,0,0,0.631,1,0] → 0.2631; LME 10 q all 0 → aggregate 0.1315. The corpus-ordering artifact zeroes LME for mem0 too. Like-for-like LoCoMo-only: 0.1835 vs 0.2631 → nox-mem −30%, not +40%.
H3. §6.7 smoke numbers. output/mem0.json: nDCG 0.1315, gold-hit 3/20, p50 263 ms. "nDCG@10=0.8569 ... gold-hit 3/20" is arithmetically impossible (3 hits/20 ⇒ mean nDCG ≤ 0.15). 0.8569 appears in docs/COMPARISON.md only. nox-mem 20-q eval-isolated artifact output/nox_mem.json (2026-05-24T02:52Z): nDCG 0.4509, 13/20, p50 466 ms; 0.6380 / 8 ms are not in any eval artifact (docs/ROADMAP.md:9 attributes 0.6380 to "prod instance, LoCoMo n=100").

## MEDIUM
M4. "open-domain is likewise LongMemEval-only": rc2 mapping doc §5 — open-domain 841 LoCoMo / n/a LME → LoCoMo-only.
M5. §6.5 principle 6 "Same VPS (Hostinger 8 cores / 16 GB RAM)": canonical = RunPod pod (§6.3, §6.7); rc4 log output/rc4-run.log paths under /Users/lab (local Mac), dated 2026-06-29; EverOS/Zep 2026-09-10 on other hosts; §2.1 calls the VPS "KVM4".
M6. Table 2 / caveat / [^nox-mem-rss] "6830 chunks live": benchmark/latency-cost/results/RESULTS-PRODUCTION-SOTA.json "note_341mb_paper": "...corpus growth (62k → 69k chunks)" → 341 MB was on a ~62k prod corpus; 6,830 is the eval corpus.
M7. §6.9 "415 MB RSS on the 70.7k-chunk production corpus on 2026-06-15": no artifact found; §5.7.1 retracts the unarchived 2026-06-15 70.7k re-check. Archived: rss_idle_mb 399 (2026-05-29, 69,135 chunks).
M8. §6.7 success criterion: never evaluated in text; latency not captured cross-system (§6.6); with only 3 systems scored in canonical, "top three" is met by construction. Also §6.6 states a different criterion ("uses BOTH per-dataset + aggregate").
M9. §6.6 "LongMemEval n=100 + LoCoMo full": canonical was n=100/dataset; rc4 full both.

## LOW
L10. §6.4 cross-ref "§5.1.4 (temporal n/a in G10b ...)": §5.1.4 no longer contains this; supplement mentions G10b only in a trajectory list (supplement line 361); internal label.
L11. §6.4 "consistent with the §5 ablations attributing ... multi-signal fusion": §5.1.3 attributes the dominant effect to section_boost (single signal), measured on EverMemBench; no §5 ablation on this corpus.
L12. §6.6 "exposes every combination": only nox-mem and Mem0 in §6.4.
L13. §6.9 "On the 2026-06-15 pod ... retained the 6,822 (§6.3.2)": 6,822 measured on rc4 artifacts; rc4 ran 2026-06-29 (meta.started_at).

## Not verified (time)
Letta ~16 min/query; Mem0 PID-limit ×3; agentmemory contamination; Hostinger plan specs; Table 2 competitor estimates.
